"""Shared pytest fixtures for the backend test suite."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.config import TestingConfig
from app.extensions import db


@pytest.fixture()
def app() -> Flask:
    """Return a configured app with a throwaway in-memory schema per test.

    TestingConfig pins the app to in-memory SQLite regardless of any
    DATABASE_URL in the environment, so tests never touch PostgreSQL.
    The production schema is owned by database/schema/*.sql; create_all()
    here only builds a disposable copy inside SQLite.
    """
    application = create_app(TestingConfig)

    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Return a test client bound to the app fixture."""
    return app.test_client()
