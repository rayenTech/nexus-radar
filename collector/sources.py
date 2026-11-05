from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import os
import re
import time
from typing import Any
from urllib.parse import quote

import feedparser
import requests

from .common import clean_text, parse_datetime

LOGGER = logging.getLogger(__name__)
LOOKBACK_DAYS = max(1, int(os.getenv("COLLECTION_LOOKBACK_DAYS", "7")))
COLLECT_LIMIT = max(10, min(100, int(os.getenv("COLLECT_LIMIT", "30"))))
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "nexus-radar@example.com")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY", "").strip()
USER_AGENT = f"NexusRadar/1.0 (mailto:{CONTACT_EMAIL})"
TIMEOUT = 30

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json, application/atom+xml, application/rss+xml, */*"})

ARXIV_CATEGORIES = ["cs.CR", "cs.AI", "cs.LG", "cs.NI", "cs.NS", "eess.SP"]
OPENALEX_QUERIES = ["cybersecurity", "artificial intelligence", "6G networks", "network security"]
CROSSREF_QUERIES = ["cybersecurity", "artificial intelligence", "6G networks"]

RSS_FEEDS = [
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/", "category": "cybersecurity"},
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "category": "cybersecurity"},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "category": "cybersecurity"},
    {"name": "Google Security Blog", "url": "https://security.googleblog.com/feeds/posts/default?alt=rss", "category": "cybersecurity"},
    {"name": "Cloudflare Blog", "url": "https://blog.cloudflare.com/rss/", "category": "ngn"},
    {"name": "OpenAI News", "url": "https://openai.com/news/rss.xml", "category": "ai"},
]


def _get_json(url: str, params: dict | None = None) -> dict:
    response = SESSION.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def collect_arxiv() -> list[dict]:
    """Collect recent papers from selected arXiv categories."""
    records: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    url = "https://export.arxiv.org/api/query"

    for index, category in enumerate(ARXIV_CATEGORIES):
        params = {
            "search_query": f"cat:{category}",
            "start": 0,
            "max_results": COLLECT_LIMIT,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        try:
            response = SESSION.get(url, params=params, timeout=TIMEOUT)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            for entry in parsed.entries:
                published = parse_datetime(entry.get("published"))
                if published and published < cutoff:
                    continue
                authors = [a.get("name", "") for a in entry.get("authors", []) if a.get("name")]
                doi = entry.get("arxiv_doi") or None
                records.append({
                    "title": clean_text(entry.get("title")),
                    "url": entry.get("link", ""),
                    "summary": clean_text(entry.get("summary", "")),
                    "content_type": "paper",
                    "source": "arXiv",
                    "published_at": published,
                    "doi": doi,
                    "authors": authors,
                    "category": _arxiv_category(category),
                })
        except (requests.RequestException, ValueError) as exc:
            LOGGER.warning("arXiv category %s failed: %s", category, exc)
        if index < len(ARXIV_CATEGORIES) - 1:
            # Be polite to arXiv and avoid issuing category queries back-to-back.
            time.sleep(3)
    return records


def _arxiv_category(category: str) -> str:
    if category == "cs.CR":
        return "cybersecurity"
    if category in {"cs.NI", "cs.NS", "eess.SP"}:
        return "ngn"
    return "ai"


def collect_openalex() -> list[dict]:
    """Collect journal articles from OpenAlex for a few focused topic queries."""
    records: list[dict] = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date().isoformat()
    for term in OPENALEX_QUERIES:
        params: dict[str, Any] = {
            "search": term,
            "filter": f"from_publication_date:{cutoff},type:article",
            "per_page": min(COLLECT_LIMIT, 50),
            "sort": "publication_date:desc",
        }
        if OPENALEX_API_KEY:
            params["api_key"] = OPENALEX_API_KEY
        try:
            payload = _get_json("https://api.openalex.org/works", params)
            for work in payload.get("results", []):
                title = work.get("title") or work.get("display_name") or ""
                primary_location = work.get("primary_location") or {}
                landing_page = primary_location.get("landing_page_url")
                url = landing_page or work.get("doi") or work.get("id") or ""
                authors = [
                    (authorship.get("author") or {}).get("display_name", "")
                    for authorship in work.get("authorships", [])
                ]
                records.append({
                    "title": title,
                    "url": url,
                    "summary": _openalex_abstract(work.get("abstract_inverted_index")),
                    "content_type": "paper",
                    "source": "OpenAlex",
                    "published_at": work.get("publication_date"),
                    "doi": work.get("doi"),
                    "authors": [a for a in authors if a],
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            LOGGER.warning("OpenAlex query '%s' failed: %s", term, exc)
    return records


def _openalex_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, indexes in inverted_index.items():
        for index in indexes:
            positions[index] = word
    return " ".join(positions[index] for index in sorted(positions))


def collect_crossref() -> list[dict]:
    """Collect recently published metadata from Crossref."""
    records: list[dict] = []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)).date().isoformat()
    for term in CROSSREF_QUERIES:
        params = {
            "query.bibliographic": term,
            "filter": f"from-pub-date:{cutoff},type:journal-article",
            "rows": min(COLLECT_LIMIT, 30),
            "sort": "published",
            "order": "desc",
        }
        try:
            payload = _get_json("https://api.crossref.org/works", params)
            for work in payload.get("message", {}).get("items", []):
                title_list = work.get("title") or []
                title = title_list[0] if title_list else ""
                abstract = clean_text(work.get("abstract", ""))
                date_parts = (
                    work.get("published", {}).get("date-parts")
                    or work.get("published-print", {}).get("date-parts")
                    or work.get("created", {}).get("date-parts")
                    or []
                )
                published = _date_parts(date_parts)
                authors = [
                    " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
                    for author in work.get("author", [])
                ]
                doi = work.get("DOI")
                url = work.get("URL") or (f"https://doi.org/{doi}" if doi else "")
                records.append({
                    "title": title,
                    "url": url,
                    "summary": abstract,
                    "content_type": "paper",
                    "source": "Crossref",
                    "published_at": published,
                    "doi": doi,
                    "authors": [author for author in authors if author],
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            LOGGER.warning("Crossref query '%s' failed: %s", term, exc)
    return records


def _date_parts(date_parts: list) -> datetime | None:
    try:
        parts = date_parts[0]
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return datetime(year, month, day, tzinfo=timezone.utc)
    except (IndexError, TypeError, ValueError):
        return None


def collect_rss() -> list[dict]:
    """Collect items from the RSS/Atom feeds listed in RSS_FEEDS."""
    records: list[dict] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    for feed_config in RSS_FEEDS:
        try:
            response = SESSION.get(feed_config["url"], timeout=TIMEOUT)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if parsed.bozo and not parsed.entries:
                LOGGER.warning("RSS feed %s could not be parsed", feed_config["name"])
                continue
            for entry in parsed.entries[:COLLECT_LIMIT]:
                published = parse_datetime(entry.get("published") or entry.get("updated"))
                if published and published < cutoff:
                    continue
                summary = clean_text(entry.get("summary") or entry.get("description") or "")
                records.append({
                    "title": clean_text(entry.get("title")),
                    "url": entry.get("link", ""),
                    "summary": summary,
                    "content_type": "news",
                    "source": feed_config["name"],
                    "published_at": published,
                    "category": feed_config.get("category"),
                })
        except (requests.RequestException, ValueError, TypeError) as exc:
            LOGGER.warning("RSS feed %s failed: %s", feed_config["name"], exc)
    return records
