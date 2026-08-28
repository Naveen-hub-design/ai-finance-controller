"""Tests for the M4.4 audit record model."""

import ast
import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import AuditRecord, User


def _create_user_via_db() -> User:
    user = User(
        email=f"audit-model-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Audit Model User",
    )
    db.session.add(user)
    db.session.commit()
    return user


def _create_record(
    user_id,
    kind: str = "decision",
    payload: dict | None = None,
) -> AuditRecord:
    record = AuditRecord(
        user_id=user_id,
        kind=kind,
        payload=payload if payload is not None else {"decision": "reduce spend"},
    )
    db.session.add(record)
    db.session.commit()
    return record


def test_model_creation(app) -> None:
    with app.app_context():
        user = _create_user_via_db()
        record = _create_record(user.id)

        assert isinstance(record, AuditRecord)
        assert record.user_id == user.id


def test_uuid_generation(app) -> None:
    with app.app_context():
        user = _create_user_via_db()
        record = _create_record(user.id)

        # Parses as a valid UUID and differs per record.
        assert isinstance(uuid.UUID(str(record.id)), uuid.UUID)
        record2 = _create_record(user.id)
        assert record.id != record2.id


def test_user_foreign_key_required(app) -> None:
    with app.app_context():
        with pytest.raises(IntegrityError):
            record = AuditRecord(
                user_id=uuid.uuid4(),  # unknown user -> FK violation
                kind="decision",
                payload={},
            )
            db.session.add(record)
            db.session.commit()
        db.session.rollback()


def test_kind_storage(app) -> None:
    with app.app_context():
        user = _create_user_via_db()
        record = _create_record(user.id, kind="risk")
        assert record.kind == "risk"


def test_json_payload_storage(app) -> None:
    with app.app_context():
        user = _create_user_via_db()
        payload = {"signals": ["LARGE_AMOUNT"], "score": "0.85"}
        record = _create_record(user.id, payload=payload)
        assert record.payload == payload


def test_created_at(app) -> None:
    with app.app_context():
        user = _create_user_via_db()
        record = _create_record(user.id)
        assert record.created_at is not None


def test_payload_preservation(app) -> None:
    with app.app_context():
        user = _create_user_via_db()
        payload = {"decision": "reduce spend", "confidence": 0.9}
        record = _create_record(user.id, payload=payload)
        assert record.to_dict()["payload"] == payload


def test_immutable_api_design(app) -> None:
    with app.app_context():
        # The model is append-only: no updated_at column, no update/delete API.
        assert not hasattr(AuditRecord, "updated_at")
        assert not hasattr(AuditRecord, "update")
        assert not hasattr(AuditRecord, "delete")


def test_no_financial_calculation(app) -> None:
    source = open("app/models/m4_audit.py", encoding="utf-8").read()
    assert "Decimal" not in source
    assert "func.sum" not in source
    assert "db.session.query" not in source


def test_to_dict_serializes_safely(app) -> None:
    with app.app_context():
        user = _create_user_via_db()
        record = _create_record(user.id, kind="recommendation")
        data = record.to_dict()
        assert set(data.keys()) == {
            "id",
            "user_id",
            "kind",
            "payload",
            "created_at",
        }
        uuid.UUID(data["id"])
        assert data["user_id"] == str(user.id)
        # created_at is an ISO-8601 string.
        assert isinstance(data["created_at"], str)


def test_no_openai_import(app) -> None:
    tree = ast.parse(
        open("app/models/m4_audit.py", encoding="utf-8").read()
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
