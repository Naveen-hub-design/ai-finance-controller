"""Tests for the M4.3 Step 2 AI Finance Controller HTTP endpoint."""

import ast
import uuid
from unittest.mock import patch

from flask.testing import FlaskClient

from app.services.m4.contracts import (
    ControllerAction,
    FinancialControllerReport,
    SourceFacts,
)


def _create_user(
    client: FlaskClient,
    email: str = "controller-route@example.com",
) -> dict:
    response = client.post(
        "/api/users",
        json={"email": email, "name": "Controller Route User"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _sample_source_facts() -> SourceFacts:
    return SourceFacts(
        money_values={
            "total_income": "10000.0000",
            "net_cash_flow": "4000.0000",
        },
        extra={
            "financial_context": {"summary": {"total_income": "10000.0000"}},
            "risk_signals": [],
            "recommendations": [],
            "cited_facts": ["Rent spending is 4000.0000"],
        },
    )


def _sample_actions():
    return [
        ControllerAction(
            action_type="REVIEW_BUDGET",
            description="Review the Food budget.",
            severity="medium",
            metadata={"category": "Food"},
        )
    ]


def _sample_report(intent: str = "Why did my expenses increase?") -> dict:
    """A realistic to_dict() serialization to compare the response against."""
    report = FinancialControllerReport(
        user_id=str(uuid.uuid4()),
        intent=intent,
        source_facts=_sample_source_facts(),
        decision="Reduce high category spending.",
        rationale="Rent is 40% of income, above the threshold.",
        confidence=0.85,
        actions=_sample_actions(),
    )
    return report.to_dict()


def _report_obj(
    *,
    user_id: str,
    decision: str = "d",
    intent: str = "Question?",
    confidence: float = 0.5,
    actions=None,
) -> FinancialControllerReport:
    return FinancialControllerReport(
        user_id=user_id,
        intent=intent,
        source_facts=_sample_source_facts(),
        decision=decision,
        rationale="r",
        confidence=confidence,
        actions=actions or [],
    )


def _patch_service(return_value=None, side_effect=None):
    return patch(
        "app.routes.m4_controller.build_controller_report",
        return_value=return_value,
        side_effect=side_effect,
    )


# ---------------------------------------------------------------------------
# Success paths
# ---------------------------------------------------------------------------


def test_successful_request(client: FlaskClient) -> None:
    user = _create_user(client, email="success-route@example.com")

    with _patch_service(
        return_value=_report_obj(user_id=user["id"], decision="reduce spend")
    ):
        response = client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": "Why did my expenses increase?"},
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["user_id"] == user["id"]
    assert data["decision"] == "reduce spend"


def test_exact_response_serialization(client: FlaskClient) -> None:
    user = _create_user(client, email="exact-route@example.com")
    serialized = _sample_report()

    report = FinancialControllerReport(
        user_id=user["id"],
        intent=serialized["intent"],
        source_facts=_sample_source_facts(),
        decision=serialized["decision"],
        rationale=serialized["rationale"],
        confidence=serialized["confidence"],
        actions=_sample_actions(),
    )

    with _patch_service(return_value=report):
        response = client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": serialized["intent"]},
        )

    assert response.status_code == 200
    data = response.get_json()
    # to_dict() serializes created_at to ISO string; compare the deterministic
    # fields and structure exactly.
    expected = report.to_dict()
    expected["user_id"] = user["id"]
    assert data == expected


def test_exact_response_shape_from_to_dict(client: FlaskClient) -> None:
    user = _create_user(client, email="shape-route@example.com")

    report = FinancialControllerReport(
        user_id=user["id"],
        intent="intent",
        source_facts=_sample_source_facts(),
        decision="d",
        rationale="r",
        confidence=0.7,
        actions=[],
    )

    with _patch_service(return_value=report):
        response = client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": "intent"},
        )

    data = response.get_json()
    assert set(data.keys()) == {
        "user_id",
        "intent",
        "source_facts",
        "decision",
        "rationale",
        "confidence",
        "actions",
        "created_at",
    }
    assert data["user_id"] == user["id"]
    assert data["intent"] == "intent"
    assert data["decision"] == "d"
    assert data["confidence"] == 0.7


def test_report_data_preserved_exactly(client: FlaskClient) -> None:
    user = _create_user(client, email="preserve-route@example.com")

    report = FinancialControllerReport(
        user_id=user["id"],
        intent="preserve me",
        source_facts=_sample_source_facts(),
        decision="Preserved decision",
        rationale="Preserved rationale",
        confidence=0.99,
        actions=[
            ControllerAction(
                action_type="A",
                description="desc",
                severity="high",
                metadata={"x": "y"},
            )
        ],
    )

    with _patch_service(return_value=report):
        response = client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": "preserve me"},
        )

    data = response.get_json()
    assert data["decision"] == report.decision
    assert data["rationale"] == report.rationale
    assert data["confidence"] == report.confidence
    assert data["actions"] == [
        {
            "action_type": "A",
            "description": "desc",
            "severity": "high",
            "metadata": {"x": "y"},
        }
    ]


# ---------------------------------------------------------------------------
# Argument passing / delegation
# ---------------------------------------------------------------------------


def test_correct_user_id_passed_to_service(client: FlaskClient) -> None:
    user = _create_user(client, email="id-route@example.com")

    with _patch_service(return_value=_report_obj(user_id=user["id"])) as mock_service:
        client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": "Question?"},
        )

    args, _ = mock_service.call_args
    assert str(args[0]) == user["id"]


def test_correct_intent_passed_to_service(client: FlaskClient) -> None:
    user = _create_user(client, email="intent-route@example.com")

    with _patch_service(return_value=_report_obj(user_id=user["id"])) as mock_service:
        client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": "My exact question"},
        )

    args, _ = mock_service.call_args
    assert args[1] == "My exact question"


def test_service_mocked_at_module_boundary(client: FlaskClient) -> None:
    user = _create_user(client, email="boundary-route@example.com")

    with _patch_service(return_value=_report_obj(user_id=user["id"])) as mock_service:
        client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": "Question?"},
        )

    mock_service.assert_called_once()


def test_route_delegates_to_controller_service(client: FlaskClient) -> None:
    user = _create_user(client, email="delegate-route@example.com")

    with _patch_service(return_value=_report_obj(user_id=user["id"])) as mock_service:
        client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": "Question?"},
        )

    mock_service.assert_called_once()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_unknown_user_returns_404(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/ai-controller",
        json={"intent": "Question?"},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_invalid_user_id_returns_404(client: FlaskClient) -> None:
    response = client.post(
        "/api/users/not-a-uuid/ai-controller",
        json={"intent": "Question?"},
    )

    assert response.status_code == 404


def test_missing_json_body_returns_400(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/ai-controller",
        data="",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_invalid_json_body_returns_400(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/ai-controller",
        data="not json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_missing_intent_returns_400(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/ai-controller",
        json={},
    )

    assert response.status_code == 400


def test_null_intent_returns_400(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/ai-controller",
        json={"intent": None},
    )

    assert response.status_code == 400


def test_non_string_intent_returns_400(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/ai-controller",
        json={"intent": 123},
    )

    assert response.status_code == 400


def test_whitespace_intent_returns_400(client: FlaskClient) -> None:
    response = client.post(
        f"/api/users/{uuid.uuid4()}/ai-controller",
        json={"intent": "   "},
    )

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_service_sqlalchemy_error_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    user = _create_user(client, email="svc-err@example.com")

    with _patch_service(side_effect=SQLAlchemyError("boom")):
        response = client.post(
            f"/api/users/{user['id']}/ai-controller",
            json={"intent": "Question?"},
        )

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


def test_user_lookup_error_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    with patch(
        "app.routes.m4_controller.db.session.get",
        side_effect=SQLAlchemyError("boom"),
    ):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller",
            json={"intent": "Question?"},
        )

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


# ---------------------------------------------------------------------------
# Static / AST checks
# ---------------------------------------------------------------------------


def test_route_does_not_import_openai(client: FlaskClient) -> None:
    tree = ast.parse(
        open("app/routes/m4_controller.py", encoding="utf-8").read()
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


def test_route_does_not_perform_direct_financial_queries(
    client: FlaskClient,
) -> None:
    source = open("app/routes/m4_controller.py", encoding="utf-8").read()

    for token in (
        "Transaction",
        "Account",
        "Budget",
        "FinancialGoal",
        "db.session.query",
        "func.sum",
        "Decimal(",
    ):
        assert token not in source, token
    assert "build_controller_report" in source


def test_no_sensitive_logging(client: FlaskClient) -> None:
    source = open("app/routes/m4_controller.py", encoding="utf-8").read()

    # Only generic server-side messages are logged; they never embed the
    # intent, an answer, or financial data.
    matches = [
        line.lstrip()
        for line in source.splitlines()
        if "logger.exception" in line or "logger.error" in line
    ]
    assert matches
    for line in matches:
        assert "intent" not in line.lower()
        assert "question" not in line.lower()

