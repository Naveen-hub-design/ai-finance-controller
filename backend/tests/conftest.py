"""Shared pytest fixtures for the backend test suite."""

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy import event

from app import create_app
from app.config import TestingConfig
from app.extensions import db


def register_and_login(
    client: FlaskClient,
    email: str = "user@example.com",
    password: str = "correct-horse-battery-staple",
) -> dict:
    """Register a user and log in, returning the login body.

    Returns ``{"user": {...}, "access_token": "<jwt>"}``. The token is the
    verified-identity proof used by every protected route (M7.4+).
    """
    created = client.post(
        "/api/users",
        json={"email": email, "full_name": "API Test User", "password": password},
    )
    assert created.status_code == 201, created.get_json()

    login = client.post("/api/users/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.get_json()
    return login.get_json()


def auth_headers(token: str) -> dict[str, str]:
    """Return the ``Authorization: Bearer`` header for ``token``."""
    return {"Authorization": f"Bearer {token}"}


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
