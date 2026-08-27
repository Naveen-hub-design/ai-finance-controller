"""Shared pytest fixtures for the backend test suite."""

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import event

from app import create_app
from app.config import TestingConfig
from app.extensions import db


@event.listens_for(db.Engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


@pytest.fixture()
def app() -> Flask:
    """Return a configured app with a throwaway in-memory schema per test.

    TestingConfig pins the app to in-memory SQLite regardless of any
    DATABASE_URL in the environment, so tests never touch PostgreSQL.
    The production schema is owned by database/schema/*.sql; create_all()
    here only builds a disposable copy inside SQLite.

    ``PRAGMA foreign_keys = ON`` enables SQLite FK enforcement so that
    ``ON DELETE CASCADE`` behaves like PostgreSQL during tests.
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
