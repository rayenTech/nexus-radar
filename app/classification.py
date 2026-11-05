"""Lightweight, explainable keyword-based classification and relevance scoring."""

from collections import Counter
import re


TAXONOMY = {
    "cybersecurity": [
        "cybersecurity", "cyber security", "information security", "soc",
        "threat intelligence", "malware", "ransomware", "phishing", "vulnerability",
        "vulnerabilities", "cve", "intrusion detection", "ids", "zero trust",
        "devsecops", "application security", "network security", "cryptography",
        "adversarial attack", "incident response", "security operations",
    ],
    "ai": [
        "artificial intelligence", "machine learning", "deep learning", "large language model",
        "llm", "generative ai", "agentic ai", "ai agent", "autonomous agent", "rag",
        "retrieval augmented generation", "explainable ai", "xai", "federated learning",
        "trustworthy ai", "neural network", "transformer", "foundation model",
    ],
    "ngn": [
        "6g", "5g", "beyond 5g", "next generation network", "next-generation network",
        "open ran", "o-ran", "oran", "radio access network", "ran", "sdn", "nfv",
        "network function virtualization", "software defined networking", "network slicing",
        "telecommunications", "wireless network", "network automation", "network intelligence",
        "edge computing", "mobile network",
    ],
}

PRIORITY_TERMS = [
    "6g", "agentic ai", "ai agent", "large language model", "llm", "zero trust",
    "ransomware", "threat intelligence", "federated learning", "open ran",
    "network slicing", "intrusion detection", "trustworthy ai", "cve",
]


def classify_content(title: str, summary: str = "", source_hint: str | None = None) -> str:
    text = f"{title} {summary} {source_hint or ''}".lower()
    scores = {
        category: sum(1 for term in terms if term in text)
        for category, terms in TAXONOMY.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def extract_keywords(title: str, summary: str = "", limit: int = 8) -> list[str]:
    text = f"{title} {summary}".lower()
    candidates = sorted(
        {term for terms in TAXONOMY.values() for term in terms},
        key=len,
        reverse=True,
    )
    found = [term for term in candidates if term in text]
    # Keep longer phrases first and avoid returning a shorter phrase contained in one already selected.
    selected: list[str] = []
    for term in found:
        if not any(term in existing for existing in selected):
            selected.append(term)
        if len(selected) >= limit:
            break
    return selected


def relevance_score(title: str, summary: str = "", category: str | None = None) -> float:
    text = f"{title} {summary}".lower()
    score = 1.0
    score += min(sum(1 for term in PRIORITY_TERMS if term in text) * 0.7, 4.0)
    if category in {"cybersecurity", "ai", "ngn"}:
        score += 1.0
    if len(summary.strip()) > 500:
        score += 0.5
    return round(min(score, 10.0), 2)


def trending_terms(items: list[tuple[str, list[str]]], limit: int = 12) -> list[dict]:
    counts: Counter[str] = Counter()
    for _category, keywords in items:
        counts.update(set(keywords or []))
    return [{"term": term, "count": count} for term, count in counts.most_common(limit)]
