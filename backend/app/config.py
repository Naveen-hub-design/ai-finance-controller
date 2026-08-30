"""Application configuration, sourced from environment variables."""

import os
from datetime import timedelta


class Config:
    """Base configuration for the API service.

    All secrets are supplied through environment variables (see .env.example).
    The DATABASE_URL fallback only supports local runs and the test suite;
    real deployments always receive a PostgreSQL URL from Compose.
    """

    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-only-not-for-production")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # JWT signing secret. A dedicated JWT_SECRET_KEY is preferred; it falls
    # back to SECRET_KEY when only SECRET_KEY is supplied so existing local and
    # Compose setups keep working. Production must supply JWT_SECRET_KEY (or
    # SECRET_KEY) via the environment -- the dev-only fallback is never safe
    # for a real deployment.
    JWT_SECRET_KEY: str = (
        os.environ.get("JWT_SECRET_KEY") or os.environ.get("SECRET_KEY") or "dev-only-not-for-production"
    )
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(minutes=15)
    JWT_ALGORITHM: str = "HS256"

    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-5.6-luna")


class TestingConfig(Config):
    """Configuration for the test suite.

    Forces an isolated in-memory SQLite database so tests can never touch
    the database configured via DATABASE_URL (e.g. Dockerized PostgreSQL).

    A deterministic, test-only JWT secret is used so tests never depend on a
    developer's real .env secret. It is a test value only and is never used
    by production configuration.
    """

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-only-deterministic-jwt-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
