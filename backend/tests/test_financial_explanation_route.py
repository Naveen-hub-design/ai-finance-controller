"""Tests for the financial explanation API endpoint."""

import uuid
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

from app.services.openai_provider import AIConfigurationError, AIProviderError


def _create_user(client: FlaskClient, email: str = "explain@example.com") -> dict:
    response = client.post(
        "/api/users",
        json={"email": email, "name": "Explain User"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _patch_service(return_value="AI answer"):
    return patch(
        "app.routes.financial_explanation.explain_financial_question",
        return_value=return_value,
    )


def test_successful_request_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service(return_value="The explanation."):
        response = client.post(
            f"/api/users/{user['id']}/financial-explanation",
            json={"question": "How am I doing?"},
        )

    assert response.status_code == 200
    assert response.get_json()["answer"] == "The explanation."


def test_response_contains_answer(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service():
        response = client.post(
            f"/api/users/{user['id']}/financial-explanation",
            json={"question": "How am I doing?"},
        )

    body = response.get_json()
    assert "answer" in body


def test_missing_json_body_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        f"/api/users/{user['id']}/financial-explanation",
        data=None,
        content_type="application/json",
    )

    assert response.status_code == 400


def test_invalid_json_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        f"/api/users/{user['id']}/financial-explanation",
        data="{not valid json",
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "request body must be valid JSON"


def test_missing_question_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        f"/api/users/{user['id']}/financial-explanation",
        json={},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "question is required"


def test_question_not_a_string_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.post(
        f"/api/users/{user['id']}/financial-explanation",
        json={"question": 12345},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "question is required"


def test_blank_question_returns_400(client: FlaskClient) -> None:
    user = _create_user(client)

    for value in ("", "   "):
        response = client.post(
            f"/api/users/{user['id']}/financial-explanation",
            json={"question": value},
        )
        assert response.status_code == 400


def test_nonexistent_user_returns_404(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/financial-explanation",
        json={"question": "How am I doing?"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_service_receives_correct_user_uuid(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service() as mock_service:
        client.post(
            f"/api/users/{user['id']}/financial-explanation",
            json={"question": "How am I doing?"},
        )

    mock_service.assert_called_once()
    args, _ = mock_service.call_args
    assert str(args[0]) == user["id"]


def test_service_receives_stripped_question(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service() as mock_service:
        client.post(
            f"/api/users/{user['id']}/financial-explanation",
            json={"question": "  What is my net cash flow?  "},
        )

    args, _ = mock_service.call_args
    assert args[1] == "What is my net cash flow?"


def test_configuration_error_returns_503(client: FlaskClient) -> None:
    user = _create_user(client)

    with patch(
        "app.routes.financial_explanation.explain_financial_question",
        side_effect=AIConfigurationError("AI provider is not configured"),
    ):
        response = client.post(
            f"/api/users/{user['id']}/financial-explanation",
            json={"question": "How am I doing?"},
        )

    assert response.status_code == 503
    assert (
        response.get_json()["error"] == "AI provider is not configured"
    )


def test_provider_error_returns_502(client: FlaskClient) -> None:
    user = _create_user(client)

    with patch(
        "app.routes.financial_explanation.explain_financial_question",
        side_effect=AIProviderError("AI request failed"),
    ):
        response = client.post(
            f"/api/users/{user['id']}/financial-explanation",
            json={"question": "How am I doing?"},
        )

    assert response.status_code == 502
    assert response.get_json()["error"] == "AI request failed"


def test_sqlalchemy_lookup_failure_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    with patch(
        "app.routes.financial_explanation.db.session.get",
        side_effect=SQLAlchemyError("boom"),
    ):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/financial-explanation",
            json={"question": "How am I doing?"},
        )

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


def test_service_is_mocked_no_real_openai_call(client: FlaskClient) -> None:
    from app.services import openai_provider

    user = _create_user(client)

    with patch.object(
        openai_provider, "send_text_request"
    ) as mock_send, _patch_service() as mock_service:
        response = client.post(
            f"/api/users/{user['id']}/financial-explanation",
            json={"question": "Test question"},
        )

    assert response.status_code == 200
    mock_service.assert_called_once()
    mock_send.assert_not_called()
