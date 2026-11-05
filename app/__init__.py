import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template

# Load local .env for both Flask CLI and `python -m collector.run`.
load_dotenv()

from .config import Config
from .extensions import db


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    app.config.from_object(Config)
    app.config["SQLALCHEMY_DATABASE_URI"] = Config.database_uri(app.instance_path)

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    # Import models before create_all so SQLAlchemy knows the tables.
    from . import models  # noqa: F401
    from .routes import main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        db.create_all()

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("404.html"), 404

    return app
