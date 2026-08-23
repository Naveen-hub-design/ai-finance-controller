"""Shared pytest fixtures for the backend test suite."""

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db


@pytest.fixture()
def app() -> Flask:
    """Return a configured app with a throwaway in-memory schema per test.

    The production schema is owned by database/schema/*.sql; create_all()
    here only builds a disposable copy inside SQLite so tests can run
    without a PostgreSQL server.
    """
    application = create_app()
    application.config.update(TESTING=True)

    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Return a test client bound to the app fixture."""
    return app.test_client()
