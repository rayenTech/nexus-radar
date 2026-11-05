from __future__ import annotations

import logging
import os

from app import create_app
from app.extensions import db
from .common import save_records
from .sources import collect_arxiv, collect_crossref, collect_openalex, collect_rss

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
LOGGER = logging.getLogger("nexus-radar.collector")


def collect_all(app=None) -> dict:
    # Reuse the running Flask app when called from its protected HTTP endpoint.
    # The CLI creates its own app when no instance is supplied.
    app = app or create_app()
    totals = {"inserted": 0, "skipped": 0, "sources": {}}
    collectors = {
        "arxiv": collect_arxiv,
        "openalex": collect_openalex,
        "crossref": collect_crossref,
        "rss": collect_rss,
    }

    with app.app_context():
        for name, collector in collectors.items():
            try:
                records = collector()
                result = save_records(records)
                totals["sources"][name] = {**result, "fetched": len(records)}
                totals["inserted"] += result["inserted"]
                totals["skipped"] += result["skipped"]
                LOGGER.info("%s: fetched=%s inserted=%s skipped=%s", name, len(records), result["inserted"], result["skipped"])
            except Exception:
                db.session.rollback()
                LOGGER.exception("Collector %s failed", name)
                totals["sources"][name] = {"error": "See collector logs"}

    LOGGER.info("Collection complete: %s", totals)
    return totals


if __name__ == "__main__":
    result = collect_all()
    print(result)
    if all("error" in value for value in result["sources"].values()):
        raise SystemExit("All collectors failed. Check the logs and configuration.")
