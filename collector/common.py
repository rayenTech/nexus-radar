from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import html
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.classification import classify_content, extract_keywords, relevance_score
from app.extensions import db
from app.models import Content


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        result = value
    else:
        raw = str(value).strip()
        try:
            result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                result = parsedate_to_datetime(raw)
            except (TypeError, ValueError, OverflowError):
                return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_url(url: str) -> str:
    value = (url or "").strip()
    if not value:
        return ""
    parts = urlsplit(value)
    # Remove tracking query parameters while preserving meaningful query strings.
    if parts.query:
        kept = [
            piece for piece in parts.query.split("&")
            if not piece.lower().startswith(("utm_", "fbclid=", "gclid="))
        ]
        query = "&".join(kept)
    else:
        query = ""
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def deduplication_key(url: str, doi: str | None = None) -> str:
    normalized_doi = (doi or "").strip().lower().replace("https://doi.org/", "").replace("http://doi.org/", "")
    if normalized_doi:
        return f"doi:{normalized_doi}"
    normalized_url = normalize_url(url)
    if normalized_url:
        return f"url:{normalized_url}"
    return "hash:" + hashlib.sha256((url or "unknown").encode("utf-8")).hexdigest()


def save_records(records: list[dict]) -> dict[str, int]:
    inserted = 0
    skipped = 0
    for record in records:
        title = clean_text(record.get("title"))[:1000]
        url = normalize_url(record.get("url", ""))
        if not title or not url:
            skipped += 1
            continue

        doi = record.get("doi")
        key = deduplication_key(url, doi)
        if db.session.query(Content.id).filter_by(dedupe_key=key).first():
            skipped += 1
            continue

        summary = clean_text(record.get("summary", ""))[:12000]
        content_type = record.get("content_type", "news")
        source = clean_text(record.get("source", "Unknown"))[:120]
        category = record.get("category") or classify_content(title, summary, source)
        keywords = record.get("keywords") or extract_keywords(title, summary)
        authors = record.get("authors") or []

        item = Content(
            dedupe_key=key,
            title=title,
            url=url,
            summary=summary,
            content_type=content_type,
            category=category,
            source=source,
            published_at=parse_datetime(record.get("published_at")),
            doi=(str(doi).strip()[:255] if doi else None),
            authors=authors[:50] if isinstance(authors, list) else [],
            keywords=keywords[:20] if isinstance(keywords, list) else [],
            relevance_score=relevance_score(title, summary, category),
        )
        db.session.add(item)
        inserted += 1

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return {"inserted": inserted, "skipped": skipped}
