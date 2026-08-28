"""Tests for the M4.1 financial risk intelligence API endpoint."""

import ast
import uuid
from unittest.mock import patch

from flask.testing import FlaskClient


def _create_user(client: FlaskClient, email: str = "risk-route@example.com") -> dict:
    response = client.post(
        "/api/users",
        json={"email": email, "name": "Risk Route User"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _patch_service(return_value=None, side_effect=None):
    return patch(
        "app.routes.m4_risk.run_risk_intelligence",
        return_value=return_value,
        side_effect=side_effect,
    )


def _sample_signals():
    return [
        {
            "type": "ROUND_AMOUNT",
            "severity": "low",
            "summary": "Expense amount is a round number.",
            "reason": "Whole-unit amount.",
            "explainable": True,
            "transaction_ids": ["t-1"],
            "amount": "5000.0000",
        }
    ]


def test_existing_user_no_signals_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service(return_value=[]):
        response = client.get(
            f"/api/users/{user['id']}/risk-intelligence"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["user_id"] == user["id"]
    assert data["signals"] == []


def test_existing_user_with_signals_returns_200_exact(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    with _patch_service(return_value=_sample_signals()):
        response = client.get(
            f"/api/users/{user['id']}/risk-intelligence"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["user_id"] == user["id"]
    assert data["signals"] == _sample_signals()


def test_unknown_user_returns_404(client: FlaskClient) -> None:
    response = client.get(
        f"/api/users/{uuid.uuid4()}/risk-intelligence"
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_invalid_user_id_returns_404(client: FlaskClient) -> None:
    response = client.get("/api/users/not-a-uuid/risk-intelligence")

    assert response.status_code == 404


def test_service_mocked_at_route_boundary(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service(return_value=[]) as mock_service:
        client.get(f"/api/users/{user['id']}/risk-intelligence")

    mock_service.assert_called_once()


def test_correct_user_id_passed_to_service(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service(return_value=[]) as mock_service:
        client.get(f"/api/users/{user['id']}/risk-intelligence")

    args, _ = mock_service.call_args
    assert str(args[0]) == user["id"]


def test_service_failure_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    user = _create_user(client)

    with _patch_service(side_effect=SQLAlchemyError("boom")):
        response = client.get(
            f"/api/users/{user['id']}/risk-intelligence"
        )

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


def test_user_lookup_failure_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    with patch(
        "app.routes.m4_risk.db.session.get",
        side_effect=SQLAlchemyError("boom"),
    ):
        response = client.get(
            f"/api/users/{uuid.uuid4()}/risk-intelligence"
        )

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


def test_response_contains_no_unexpected_fields(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service(return_value=_sample_signals()):
        response = client.get(
            f"/api/users/{user['id']}/risk-intelligence"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert set(data.keys()) == {"user_id", "signals"}


def test_route_does_not_import_openai() -> None:
    tree = ast.parse(
        open("app/routes/m4_risk.py", encoding="utf-8").read()
    )
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    assert "openai" not in imported


def test_route_does_not_perform_direct_transaction_calculations() -> None:
    source = open("app/routes/m4_risk.py", encoding="utf-8").read()

    assert "Transaction" not in source
    assert "db.session.query" not in source
    assert "func.sum" not in source
    assert "Decimal" not in source
    assert "run_risk_intelligence" in source


def test_user_isolation_preserved_through_lookup(client: FlaskClient) -> None:
    user_a = _create_user(client, email="iso-a-route@example.com")
    user_b = _create_user(client, email="iso-b-route@example.com")

    with _patch_service(return_value=[]) as mock_service:
        client.get(f"/api/users/{user_a['id']}/risk-intelligence")
        client.get(f"/api/users/{user_b['id']}/risk-intelligence")

    assert mock_service.call_count == 2
    first_args, _ = mock_service.call_args_list[0]
    second_args, _ = mock_service.call_args_list[1]
    assert str(first_args[0]) == user_a["id"]
    assert str(second_args[0]) == user_b["id"]
