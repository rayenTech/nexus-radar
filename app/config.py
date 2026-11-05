import os
from pathlib import Path


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    @staticmethod
    def database_uri(instance_path: str) -> str:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if database_url:
            # Some hosting providers still expose the older postgres:// scheme.
            if database_url.startswith("postgres://"):
                database_url = database_url.replace(
                    "postgres://", "postgresql+psycopg://", 1
                )
            elif database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+psycopg://", 1
                )
            return database_url

        db_path = Path(instance_path) / "nexus_radar.db"
        return f"sqlite:///{db_path.as_posix()}"
