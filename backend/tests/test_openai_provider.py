"""Tests for the M3.1 OpenAI provider integration.

These tests never call the real OpenAI API: the OpenAI client is always
mocked, and no real API key is used.
"""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.config import TestingConfig
from app.services.openai_provider import (
    AIProviderError,
    get_model,
    is_configured,
    send_text_request,
)


@pytest.fixture()
def app() -> Flask:
    return create_app(TestingConfig)


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


def _message_part(text: str) -> MagicMock:
    part = MagicMock()
    part.type = "output_text"
    part.text = text
    return part


def _message_output(text: str) -> MagicMock:
    msg = MagicMock()
    msg.type = "message"
    msg.content = [_message_part(text)]
    return msg


def test_model_defaults_to_configured_value(app: Flask) -> None:
    with app.app_context():
        app.config["OPENAI_MODEL"] = "gpt-5.6-luna"
        assert get_model() == "gpt-5.6-luna"


def test_model_is_configurable(app: Flask) -> None:
    with app.app_context():
        app.config["OPENAI_MODEL"] = "custom-model"
        assert get_model() == "custom-model"


def test_is_configured_with_key(app: Flask) -> None:
    with app.app_context():
        app.config["OPENAI_API_KEY"] = "sk-test-not-real"
        assert is_configured() is True


def test_missing_api_key_handled_safely(app: Flask) -> None:
    with app.app_context():
        app.config["OPENAI_API_KEY"] = ""

        assert is_configured() is False

        with pytest.raises(Exception) as err:
            send_text_request("Hello")

        assert "API key" not in str(err.value).lower()


def test_send_text_request_uses_mocked_client(
    app: Flask,
) -> None:
    with app.app_context():
        app.config["OPENAI_API_KEY"] = "sk-test-not-real"

        mock_response = MagicMock()
        mock_response.output = [_message_output("A mocked reply.")]

        with patch("app.services.openai_provider._client") as mock_factory:
            mock_client = MagicMock()
            mock_client.responses.create.return_value = mock_response
            mock_factory.return_value = mock_client

            result = send_text_request("What is 1+1?")

            assert result == "A mocked reply."
            mock_client.responses.create.assert_called_once()
            call_kwargs = mock_client.responses.create.call_args.kwargs
            assert call_kwargs["model"] == "gpt-5.6-luna"
            assert call_kwargs["input"] == "What is 1+1?"


def test_send_text_request_sends_system_prompt(
    app: Flask,
) -> None:
    with app.app_context():
        app.config["OPENAI_API_KEY"] = "sk-test-not-real"

        mock_response = MagicMock()
        mock_response.output = [_message_output("ok")]

        with patch("app.services.openai_provider._client") as mock_factory:
            mock_client = MagicMock()
            mock_client.responses.create.return_value = mock_response
            mock_factory.return_value = mock_client

            send_text_request(
                "Hi",
                system_prompt="You are a finance assistant.",
            )

            call_kwargs = mock_client.responses.create.call_args.kwargs
            assert call_kwargs["instructions"] == "You are a finance assistant."


def test_mocked_successful_response_returns_text(app: Flask) -> None:
    with app.app_context():
        app.config["OPENAI_API_KEY"] = "sk-test-not-real"

        mock_response = MagicMock()
        mock_response.output = [
            _message_output("First line"),
            _message_output("Second line"),
        ]

        with patch("app.services.openai_provider._client") as mock_factory:
            mock_client = MagicMock()
            mock_client.responses.create.return_value = mock_response
            mock_factory.return_value = mock_client

            assert send_text_request("Hi") == "First line\nSecond line"


def test_mocked_api_failure_handled_safely(app: Flask) -> None:
    with app.app_context():
        app.config["OPENAI_API_KEY"] = "sk-test-not-real"

        with patch("app.services.openai_provider._client") as mock_factory:
            mock_client = MagicMock()
            mock_client.responses.create.side_effect = RuntimeError("boom")
            mock_factory.return_value = mock_client

            with pytest.raises(AIProviderError):
                send_text_request("Hi")

            assert "boom" not in str(mock_client.responses.create.call_args)


def test_no_api_call_when_not_configured(app: Flask) -> None:
    with app.app_context():
        app.config["OPENAI_API_KEY"] = ""

        with patch("app.services.openai_provider._client") as mock_factory:
            with pytest.raises(Exception):
                send_text_request("Hi")
            mock_factory.assert_not_called()
