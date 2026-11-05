from datetime import datetime, timezone

from flask import Blueprint, abort, render_template, request
from sqlalchemy import func, or_

from .extensions import db
from .models import Content
from .classification import trending_terms

main_bp = Blueprint("main", __name__)
PAGE_SIZE = 20


def _filtered_query(content_type: str | None = None):
    query = Content.query
    if content_type:
        query = query.filter(Content.content_type == content_type)

    category = request.args.get("category", "").strip().lower()
    if category in {"cybersecurity", "ai", "ngn", "general"}:
        query = query.filter(Content.category == category)

    search = request.args.get("q", "").strip()
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Content.title.ilike(like), Content.summary.ilike(like), Content.source.ilike(like))
        )

    return query.order_by(Content.published_at.desc().nullslast(), Content.collected_at.desc())


def _paginate(query):
    page = request.args.get("page", 1, type=int)
    page = max(page, 1)
    return query.paginate(page=page, per_page=PAGE_SIZE, error_out=False)


@main_bp.get("/")
def dashboard():
    total = Content.query.count()
    papers_count = Content.query.filter_by(content_type="paper").count()
    news_count = Content.query.filter_by(content_type="news").count()

    category_counts = {
        category: Content.query.filter_by(category=category).count()
        for category in ("cybersecurity", "ai", "ngn", "general")
    }
    latest_items = Content.query.order_by(
        Content.published_at.desc().nullslast(), Content.collected_at.desc()
    ).limit(8).all()

    latest_collection = db.session.query(func.max(Content.collected_at)).scalar()
    return render_template(
        "dashboard.html",
        total=total,
        papers_count=papers_count,
        news_count=news_count,
        category_counts=category_counts,
        latest_items=latest_items,
        latest_collection=latest_collection,
    )


@main_bp.get("/research")
def research():
    pagination = _paginate(_filtered_query("paper"))
    return render_template("listing.html", title="Research papers", subtitle="Scientific publications and preprints", pagination=pagination, active="research")


@main_bp.get("/news")
def news():
    pagination = _paginate(_filtered_query("news"))
    return render_template("listing.html", title="Technology news", subtitle="Technology, cybersecurity and telecom updates", pagination=pagination, active="news")


@main_bp.get("/trends")
def trends():
    rows = Content.query.with_entities(Content.category, Content.keywords).all()
    top_terms = trending_terms(rows)
    category_counts = {
        category: Content.query.filter_by(category=category).count()
        for category in ("cybersecurity", "ai", "ngn", "general")
    }
    return render_template("trends.html", top_terms=top_terms, category_counts=category_counts)


@main_bp.get("/item/<int:item_id>")
def item_detail(item_id: int):
    item = db.session.get(Content, item_id)
    if item is None:
        abort(404)
    return render_template("detail.html", item=item)


@main_bp.get("/health")
def health():
    # Basic liveness endpoint for hosting-platform health checks.
    return {"status": "ok", "utc": datetime.now(timezone.utc).isoformat()}

