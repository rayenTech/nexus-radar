from datetime import datetime, timezone

from .extensions import db


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Content(db.Model):
    """A normalized scientific paper or technology/news item."""

    __tablename__ = "content"

    id = db.Column(db.Integer, primary_key=True)
    dedupe_key = db.Column(db.String(512), unique=True, nullable=False, index=True)
    title = db.Column(db.String(1000), nullable=False)
    url = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, default="", nullable=False)
    content_type = db.Column(db.String(20), nullable=False, index=True)  # paper/news
    category = db.Column(db.String(30), nullable=False, default="general", index=True)
    source = db.Column(db.String(120), nullable=False, default="Unknown", index=True)
    published_at = db.Column(db.DateTime(timezone=True), nullable=True, index=True)
    collected_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    doi = db.Column(db.String(255), nullable=True, index=True)
    authors = db.Column(db.JSON, default=list, nullable=False)
    keywords = db.Column(db.JSON, default=list, nullable=False)
    relevance_score = db.Column(db.Float, default=0.0, nullable=False)

    def __repr__(self) -> str:
        return f"<Content {self.id}: {self.title[:50]}>"
