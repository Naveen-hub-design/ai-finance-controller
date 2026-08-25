"""Application configuration, sourced from environment variables."""

import os


class Config:
    """Base configuration for the API service.

    All secrets are supplied through environment variables (see .env.example).
    The DATABASE_URL fallback only supports local runs and the test suite;
    real deployments always receive a PostgreSQL URL from Compose.
    """

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-only-not-for-production")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False


class TestingConfig(Config):
    """Configuration for the test suite.

    Forces an isolated in-memory SQLite database so tests can never touch
    the database configured via DATABASE_URL (e.g. Dockerized PostgreSQL).
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
