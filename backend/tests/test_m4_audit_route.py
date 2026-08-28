"""Tests for the M4.4 audit record API endpoints."""

import ast
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from flask.testing import FlaskClient

from app.extensions import db
from app.models import AuditRecord


def _create_user(
    client: FlaskClient,
    email: str = "audit-route@example.com",
) -> dict:
    response = client.post(
        "/api/users",
        json={"email": email, "name": "Audit Route User"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _valid_body(**overrides) -> dict:
    body = {
        "kind": "decision",
        "payload": {
            "decision": "Reduce high category spending",
            "confidence": 0.85,
        },
    }
    body.update(overrides)
    return body


def _post_record(client: FlaskClient, user_id: str, body=None) -> object:
    return client.post(
        f"/api/users/{user_id}/audit-record",
        json=body if body is not None else _valid_body(),
    )


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------


def test_successful_post_returns_201(client: FlaskClient) -> None:
    user = _create_user(client)

    response = _post_record(client, user["id"])

    assert response.status_code == 201
    data = response.get_json()
    assert data["kind"] == "decision"
    assert data["user_id"] == user["id"]
    assert data["payload"] == _valid_body()["payload"]
    uuid.UUID(data["id"])
    assert isinstance(data["created_at"], str)


def test_post_exact_response_shape(client: FlaskClient) -> None:
    user = _create_user(client)

    response = _post_record(client, user["id"])

    assert response.status_code == 201
    data = response.get_json()
    assert set(data.keys()) == {
        "id",
        "user_id",
        "kind",
        "payload",
        "created_at",
    }


def test_payload_preservation_via_api(client: FlaskClient) -> None:
    user = _create_user(client)
    payload = {
        "signals": ["LARGE_AMOUNT", "ROUND_AMOUNT"],
        "recommendations": ["BUDGET_OVERSPEND"],
        "nested": {"amount": "1234.5678"},
    }

    response = _post_record(
        client, user["id"], _valid_body(kind="risk", payload=payload)
    )

    assert response.status_code == 201
    assert response.get_json()["payload"] == payload


def test_post_unknown_user_returns_404(client: FlaskClient) -> None:
    response = _post_record(client, str(uuid.uuid4()))

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_post_missing_json_body_returns_400(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/audit-record",
        data="",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_post_invalid_json_body_returns_400(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/audit-record",
        data="not json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_post_missing_kind_returns_400(client: FlaskClient) -> None:
    response = _post_record(
        client, str(uuid.uuid4()), {"payload": {}}
    )

    assert response.status_code == 400


def test_post_invalid_kind_returns_400(client: FlaskClient) -> None:
    response = _post_record(client, str(uuid.uuid4()), _valid_body(kind="fraud"))

    assert response.status_code == 400


def test_post_null_kind_returns_400(client: FlaskClient) -> None:
    response = _post_record(client, str(uuid.uuid4()), _valid_body(kind=None))

    assert response.status_code == 400


def test_post_missing_payload_returns_400(client: FlaskClient) -> None:
    response = _post_record(
        client, str(uuid.uuid4()), {"kind": "decision"}
    )

    assert response.status_code == 400


def test_post_non_object_payload_returns_400(client: FlaskClient) -> None:
    response = _post_record(
        client, str(uuid.uuid4()), _valid_body(payload=["a", "b"])
    )

    assert response.status_code == 400


def test_post_string_payload_returns_400(client: FlaskClient) -> None:
    response = _post_record(
        client, str(uuid.uuid4()), _valid_body(payload="not an object")
    )

    assert response.status_code == 400


def test_post_invalid_uuid_returns_404(client: FlaskClient) -> None:
    response = client.post(
        "/api/users/not-a-uuid/audit-record",
        json=_valid_body(),
    )

    assert response.status_code == 404


def test_commit_failure_returns_500_and_rolls_back(
    client: FlaskClient,
) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    user = _create_user(client)

    with patch(
        "app.routes.m4_audit.db.session.commit",
        side_effect=SQLAlchemyError("boom"),
    ):
        response = _post_record(client, user["id"])

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


def test_successful_get_returns_records(client: FlaskClient) -> None:
    user = _create_user(client)
    _post_record(client, user["id"])

    response = client.get(f"/api/users/{user['id']}/audit")

    assert response.status_code == 200
    data = response.get_json()
    assert data["user_id"] == user["id"]
    assert len(data["records"]) == 1


def test_get_unknown_user_returns_404(client: FlaskClient) -> None:
    response = client.get(f"/api/users/{uuid.uuid4()}/audit")

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_get_empty_list(client: FlaskClient) -> None:
    user = _create_user(client)

    response = client.get(f"/api/users/{user['id']}/audit")

    assert response.status_code == 200
    assert response.get_json()["records"] == []


def test_get_user_isolation(client: FlaskClient) -> None:
    user_a = _create_user(client, email="audit-a@example.com")
    user_b = _create_user(client, email="audit-b@example.com")
    _post_record(client, user_a["id"], _valid_body(kind="decision"))
    _post_record(client, user_b["id"], _valid_body(kind="risk"))

    response = client.get(f"/api/users/{user_a['id']}/audit")

    assert response.status_code == 200
    records = response.get_json()["records"]
    assert len(records) == 1
    assert records[0]["user_id"] == user_a["id"]
    assert records[0]["kind"] == "decision"


def test_get_deterministic_ordering(app, client: FlaskClient) -> None:
    user = _create_user(client)

    with app.app_context():
        base = datetime.now(timezone.utc)
        r_old = AuditRecord(
            user_id=uuid.UUID(user["id"]),
            kind="recommendation",
            payload={"tag": "oldest"},
            created_at=base - timedelta(hours=2),
        )
        r_new = AuditRecord(
            user_id=uuid.UUID(user["id"]),
            kind="decision",
            payload={"tag": "newest"},
            created_at=base,
        )
        r_mid = AuditRecord(
            user_id=uuid.UUID(user["id"]),
            kind="risk",
            payload={"tag": "middle"},
            created_at=base - timedelta(hours=1),
        )
        db.session.add_all([r_old, r_mid, r_new])
        db.session.commit()

    response = client.get(f"/api/users/{user['id']}/audit")

    assert response.status_code == 200
    tags = [r["payload"]["tag"] for r in response.get_json()["records"]]
    assert tags == ["newest", "middle", "oldest"]


def test_get_database_failure_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    user = _create_user(client)

    with patch(
        "app.routes.m4_audit.db.session.query",
        side_effect=SQLAlchemyError("boom"),
    ):
        response = client.get(f"/api/users/{user['id']}/audit")

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


# ---------------------------------------------------------------------------
# Append-only / no update or delete
# ---------------------------------------------------------------------------


def test_no_update_route(client: FlaskClient) -> None:
    user = _create_user(client)
    created = _post_record(client, user["id"]).get_json()

    response = client.put(
        f"/api/users/{user['id']}/audit-record/{created['id']}",
        json=_valid_body(),
    )
    assert response.status_code == 404

    response = client.patch(
        f"/api/users/{user['id']}/audit-record/{created['id']}",
        json=_valid_body(),
    )
    assert response.status_code == 404


def test_no_delete_route(client: FlaskClient) -> None:
    user = _create_user(client)
    created = _post_record(client, user["id"]).get_json()

    response = client.delete(
        f"/api/users/{user['id']}/audit-record/{created['id']}"
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Static / AST checks
# ---------------------------------------------------------------------------


def test_route_does_not_import_openai(client: FlaskClient) -> None:
    tree = ast.parse(
        open("app/routes/m4_audit.py", encoding="utf-8").read()
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


def test_route_no_direct_financial_calculations(client: FlaskClient) -> None:
    source = open("app/routes/m4_audit.py", encoding="utf-8").read()
    for token in (
        "Transaction",
        "Budget",
        "FinancialGoal",
        "func.sum",
        "Decimal(",
    ):
        assert token not in source, token


def test_route_no_sensitive_payload_logging(client: FlaskClient) -> None:
    source = open("app/routes/m4_audit.py", encoding="utf-8").read()
    # Every logger message must be a static, generic string with no
    # interpolation, and must never reference payload/user/kind contents.
    for line in source.splitlines():
        stripped = line.strip()
        if "logger." in stripped:
            assert "payload" not in stripped
            assert "user_id" not in stripped
            assert "kind" not in stripped
            assert "f\"" not in stripped
            assert "f'" not in stripped
    assert source.count("logger.exception") >= 2
