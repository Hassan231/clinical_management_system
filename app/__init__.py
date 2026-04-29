# Application package initializer.
# Defines the SQLAlchemy db instance and the create_app() factory function.

from flask import Flask                 # Core Flask class used to create the application
from flask_sqlalchemy import SQLAlchemy  # SQLAlchemy ORM extension for Flask

# Create the db object at module level so all models can import it without circular imports.
# It is not bound to any app yet — that happens inside create_app() via db.init_app(app).
db = SQLAlchemy()


def create_app():
    """Application factory — builds, configures, and returns the Flask app."""

    app = Flask(__name__)
    # __name__ tells Flask where to look for templates and static files (relative to this file)

    # Use a local SQLite database file stored in the auto-created 'instance' folder
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clinical.db"

    # Disable SQLAlchemy's modification-tracking event system — saves memory, not needed here
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Secret key used to cryptographically sign session cookies.
    # In production this should be a long random string stored in an environment variable.
    app.config["SECRET_KEY"] = "clinical-management-secret-key"

    # Bind the shared db object to this specific Flask app instance
    db.init_app(app)

    # Import the blueprint here (deferred import) to avoid circular import issues
    from .routes import main_bp

    # Register all routes defined in routes.py under the 'main' blueprint namespace
    app.register_blueprint(main_bp)

    with app.app_context():
        # Push an application context so that db operations work outside of a request
        from . import models  # Import models so SQLAlchemy is aware of all table definitions

        db.create_all()  # Create all tables in the database if they do not already exist

    return app  # Return the fully configured app to run.py
