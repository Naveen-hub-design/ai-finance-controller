"""Shared pytest fixtures for the backend test suite."""

import pytest
from flask.testing import FlaskClient

from app import create_app


@pytest.fixture()
def client() -> FlaskClient:
    """Return a test client for the real application factory."""
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()
