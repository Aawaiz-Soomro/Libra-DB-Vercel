import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


def create_app(test_config: dict | None = None) -> Flask:
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Override DB URL from environment (Vercel / Neon)
    # On Vercel, DATABASE_URL will be your Neon Postgres URL.
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url

    # For tests you can still override anything
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    from . import routes  # noqa: WPS433
    app.register_blueprint(routes.bp)

    @app.cli.command("seed")
    def seed_data() -> None:
        """Seed the database with sample data."""
        from .seed import seed_database  # imported lazily so app is ready
        seed_database()

    # Use app context so we can safely import models and query
    with app.app_context():
        # 👇 import here to avoid circular import
        from .models import User

        # This will create tables in your Neon DB on first run
        db.create_all()

        # Ensure there is at least one default librarian
        if not User.query.filter_by(role="librarian").first():
            librarian = User(
                name="Librarian",
                email="librarian@example.com",
                role="librarian",
                approved=True,
            )
            librarian.set_password("admin123")
            db.session.add(librarian)
            db.session.commit()

    return app
