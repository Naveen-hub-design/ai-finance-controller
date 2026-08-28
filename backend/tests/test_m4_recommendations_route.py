"""Tests for the M4.2 financial recommendations API endpoint."""

import ast
import uuid
from unittest.mock import patch

from flask.testing import FlaskClient


def _create_user(
    client: FlaskClient,
    email: str = "rec-route@example.com",
) -> dict:
    response = client.post(
        "/api/users",
        json={"email": email, "name": "Rec Route User"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _patch_service(return_value=None, side_effect=None):
    return patch(
        "app.routes.m4_recommendations.run_recommendations",
        return_value=return_value,
        side_effect=side_effect,
    )


def _sample_recommendations():
    return [
        {
            "priority": "high",
            "type": "BUDGET_OVERSPEND",
            "title": "Budget exceeded",
            "body": "Spending in Food exceeded the budget.",
            "grounded_amount": "1000.0000",
            "metric": {
                "name": "budget_utilization",
                "value": "150.00%",
                "threshold": "100%",
            },
        }
    ]


def test_existing_user_no_recommendations_returns_200(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    with _patch_service(return_value=[]):
        response = client.get(
            f"/api/users/{user['id']}/recommendations"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["user_id"] == user["id"]
    assert data["recommendations"] == []


def test_existing_user_with_recommendations_returns_200_exact(
    client: FlaskClient,
) -> None:
    user = _create_user(client)

    with _patch_service(return_value=_sample_recommendations()):
        response = client.get(
            f"/api/users/{user['id']}/recommendations"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["user_id"] == user["id"]
    assert data["recommendations"] == _sample_recommendations()


def test_unknown_user_returns_404(client: FlaskClient) -> None:
    response = client.get(
        f"/api/users/{uuid.uuid4()}/recommendations"
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_invalid_user_id_returns_404(client: FlaskClient) -> None:
    response = client.get("/api/users/not-a-uuid/recommendations")

    assert response.status_code == 404


def test_service_mocked_at_route_boundary(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service(return_value=[]) as mock_service:
        client.get(f"/api/users/{user['id']}/recommendations")

    mock_service.assert_called_once()


def test_correct_user_id_passed_to_service(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service(return_value=[]) as mock_service:
        client.get(f"/api/users/{user['id']}/recommendations")

    args, _ = mock_service.call_args
    assert str(args[0]) == user["id"]


def test_service_failure_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    user = _create_user(client)

    with _patch_service(side_effect=SQLAlchemyError("boom")):
        response = client.get(
            f"/api/users/{user['id']}/recommendations"
        )

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


def test_user_lookup_failure_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    with patch(
        "app.routes.m4_recommendations.db.session.get",
        side_effect=SQLAlchemyError("boom"),
    ):
        response = client.get(
            f"/api/users/{uuid.uuid4()}/recommendations"
        )

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


def test_response_contains_no_unexpected_fields(client: FlaskClient) -> None:
    user = _create_user(client)

    with _patch_service(return_value=_sample_recommendations()):
        response = client.get(
            f"/api/users/{user['id']}/recommendations"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert set(data.keys()) == {"user_id", "recommendations"}


def test_recommendation_data_preserved_exactly(client: FlaskClient) -> None:
    user = _create_user(client)

    recs = _sample_recommendations()
    with _patch_service(return_value=recs):
        response = client.get(
            f"/api/users/{user['id']}/recommendations"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["recommendations"] == recs
    assert data["recommendations"][0] == recs[0]


def test_route_does_not_import_openai() -> None:
    tree = ast.parse(
        open("app/routes/m4_recommendations.py", encoding="utf-8").read()
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
    source = open(
        "app/routes/m4_recommendations.py", encoding="utf-8"
    ).read()

    assert "Transaction" not in source
    assert "Budget" not in source
    assert "FinancialGoal" not in source
    assert "db.session.query" not in source
    assert "func.sum" not in source
    assert "Decimal" not in source
    assert "run_recommendations" in source


def test_user_isolation_preserved_through_lookup(
    client: FlaskClient,
) -> None:
    user_a = _create_user(client, email="rec-iso-a@example.com")
    user_b = _create_user(client, email="rec-iso-b@example.com")

    with _patch_service(return_value=[]) as mock_service:
        client.get(f"/api/users/{user_a['id']}/recommendations")
        client.get(f"/api/users/{user_b['id']}/recommendations")

    assert mock_service.call_count == 2
    first_args, _ = mock_service.call_args_list[0]
    second_args, _ = mock_service.call_args_list[1]
    assert str(first_args[0]) == user_a["id"]
    assert str(second_args[0]) == user_b["id"]
