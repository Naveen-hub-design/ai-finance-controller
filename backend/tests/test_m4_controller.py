"""Tests for the M4.3 Step 1 AI Finance Controller service.

These tests mock every external boundary at the controller module level
(``app.services.m4.controller``), so no real financial context, risk,
recommendation, or OpenAI calls are made.
"""

import ast
import json
from unittest.mock import patch

import pytest

from app.services.m4.contracts import (
    ControllerAction,
    FinancialControllerReport,
    SourceFacts,
)
from app.services.m4.controller import build_controller_report


def _sample_context() -> dict:
    """A realistic M3.2 financial context (mocked)."""
    return {
        "summary": {
            "total_income": "10000.0000",
            "total_expenses": "6000.0000",
            "net_cash_flow": "4000.0000",
            "account_balance": "50000.0000",
        },
        "activity": {
            "transaction_count": 10,
            "income_transaction_count": 5,
            "expense_transaction_count": 5,
        },
        "spending_by_category": [
            {"category": "Rent", "amount": "4000.0000"},
        ],
        "budgets": [
            {
                "id": "b-1",
                "category_name": "Food",
                "amount": "2000.0000",
                "period": "monthly",
            }
        ],
        "financial_goals": [
            {
                "id": "g-1",
                "name": "Emergency Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": "2026-12-31",
                "status": "active",
            }
        ],
    }


def _sample_signals() -> list:
    return [
        {
            "type": "ROUND_AMOUNT",
            "severity": "low",
            "summary": "Expense amount is a round number.",
            "reason": "Whole-unit amount.",
            "transaction_ids": ["t-1"],
            "amount": "5000.0000",
        }
    ]


def _sample_recommendations() -> list:
    return [
        {
            "priority": "high",
            "type": "BUDGET_OVERSPEND",
            "title": "Budget exceeded",
            "body": "Spending exceeded the budget.",
            "grounded_amount": "2000.0000",
            "metric": {"name": "budget_utilization", "value": "150.00%"},
        }
    ]


def _sample_response() -> str:
    return json.dumps(
        {
            "decision": "Reduce high category spending.",
            "rationale": "Rent is 40% of income, above the threshold.",
            "confidence": 0.85,
            "cited_facts": [
                "Rent spending is 4000.0000",
                "Budget overspend detected",
            ],
            "actions": [
                {
                    "action_type": "REVIEW_BUDGET",
                    "description": "Review the Food budget.",
                    "severity": "medium",
                    "metadata": {"category": "Food"},
                }
            ],
        }
    )


def _patch_all(send_response=_sample_response()):
    patchers = [
        patch(
            "app.services.m4.controller.build_financial_context",
            return_value=_sample_context(),
        ),
        patch(
            "app.services.m4.controller.run_risk_intelligence",
            return_value=_sample_signals(),
        ),
        patch(
            "app.services.m4.controller.run_recommendations",
            return_value=_sample_recommendations(),
        ),
        patch(
            "app.services.m4.controller.send_text_request",
            return_value=send_response,
        ),
    ]
    for patcher in patchers:
        patcher.start()
    return [p.stop for p in reversed(patchers)]


def _stop(cleanups):
    for cleanup in cleanups:
        cleanup()


# ---------------------------------------------------------------------------
# Success paths
# ---------------------------------------------------------------------------


def test_successful_controller_report():
    cleanups = _patch_all()
    try:
        report = build_controller_report("user-1", "How is my budget?")
    finally:
        _stop(cleanups)

    assert isinstance(report, FinancialControllerReport)
    assert report.user_id == "user-1"
    assert report.intent == "How is my budget?"
    assert report.decision == "Reduce high category spending."
    assert report.rationale == "Rent is 40% of income, above the threshold."
    assert report.confidence == 0.85


def test_context_service_called_with_user_id():
    with patch(
        "app.services.m4.controller.build_financial_context"
    ) as mock_ctx, patch(
        "app.services.m4.controller.run_risk_intelligence", return_value=[]
    ), patch(
        "app.services.m4.controller.run_recommendations", return_value=[]
    ), patch(
        "app.services.m4.controller.send_text_request", return_value=_sample_response()
    ):
        mock_ctx.return_value = _sample_context()
        build_controller_report("u-77", "intent")

    mock_ctx.assert_called_once_with("u-77")


def test_risk_service_called_with_user_id():
    with patch(
        "app.services.m4.controller.build_financial_context",
        return_value=_sample_context(),
    ), patch(
        "app.services.m4.controller.run_risk_intelligence"
    ) as mock_risk, patch(
        "app.services.m4.controller.run_recommendations", return_value=[]
    ), patch(
        "app.services.m4.controller.send_text_request", return_value=_sample_response()
    ):
        mock_risk.return_value = []
        build_controller_report("u-77", "intent")

    mock_risk.assert_called_once_with("u-77")


def test_recommendations_service_called_with_user_id():
    with patch(
        "app.services.m4.controller.build_financial_context",
        return_value=_sample_context(),
    ), patch(
        "app.services.m4.controller.run_risk_intelligence", return_value=[]
    ), patch(
        "app.services.m4.controller.run_recommendations"
    ) as mock_rec, patch(
        "app.services.m4.controller.send_text_request", return_value=_sample_response()
    ):
        mock_rec.return_value = []
        build_controller_report("u-77", "intent")

    mock_rec.assert_called_once_with("u-77")


def test_provider_called_through_send_text_request_boundary():
    with patch(
        "app.services.m4.controller.build_financial_context",
        return_value=_sample_context(),
    ), patch(
        "app.services.m4.controller.run_risk_intelligence", return_value=[]
    ), patch(
        "app.services.m4.controller.run_recommendations", return_value=[]
    ), patch(
        "app.services.m4.controller.send_text_request"
    ) as mock_send:
        mock_send.return_value = _sample_response()
        build_controller_report("u-77", "intent")

    mock_send.assert_called_once()


def test_system_prompt_passed_to_provider():
    from app.services.m4.controller_prompts import (
        build_controller_system_prompt,
    )

    with patch(
        "app.services.m4.controller.build_financial_context",
        return_value=_sample_context(),
    ), patch(
        "app.services.m4.controller.run_risk_intelligence", return_value=[]
    ), patch(
        "app.services.m4.controller.run_recommendations", return_value=[]
    ), patch(
        "app.services.m4.controller.send_text_request"
    ) as mock_send:
        mock_send.return_value = _sample_response()
        build_controller_report("u-77", "intent")

    kwargs = mock_send.call_args.kwargs
    assert kwargs["system_prompt"] == build_controller_system_prompt()


def test_user_prompt_contains_intent_and_context():
    with patch(
        "app.services.m4.controller.build_financial_context",
        return_value=_sample_context(),
    ), patch(
        "app.services.m4.controller.run_risk_intelligence",
        return_value=_sample_signals(),
    ), patch(
        "app.services.m4.controller.run_recommendations",
        return_value=_sample_recommendations(),
    ), patch(
        "app.services.m4.controller.send_text_request"
    ) as mock_send:
        mock_send.return_value = _sample_response()
        build_controller_report("u-77", "Analyze my overspending")

    prompt = mock_send.call_args.args[0]
    assert "Analyze my overspending" in prompt
    assert "<USER_INTENT>" in prompt
    assert "</USER_INTENT>" in prompt
    assert "<FINANCIAL_CONTEXT>" in prompt
    assert "<RISK_SIGNALS>" in prompt
    assert "<RECOMMENDATIONS>" in prompt
    # Deterministic serialized data is present.
    assert "10000.0000" in prompt
    assert "ROUND_AMOUNT" in prompt
    assert "BUDGET_OVERSPEND" in prompt


def test_deterministic_source_facts_preserved():
    cleanups = _patch_all()
    try:
        report = build_controller_report("u-77", "intent")
    finally:
        _stop(cleanups)

    sf = report.source_facts
    assert isinstance(sf, SourceFacts)
    assert sf.money_values["total_income"] == "10000.0000"
    assert sf.money_values["net_cash_flow"] == "4000.0000"
    assert sf.money_values["category_spending_0"] == "4000.0000"
    assert sf.extra["risk_signals"] == _sample_signals()
    assert sf.extra["recommendations"] == _sample_recommendations()
    assert sf.extra["financial_context"] == _sample_context()


def test_cited_facts_stored_in_extra_not_as_field():
    cleanups = _patch_all()
    try:
        report = build_controller_report("u-77", "intent")
    finally:
        _stop(cleanups)

    assert report.source_facts.extra["cited_facts"] == [
        "Rent spending is 4000.0000",
        "Budget overspend detected",
    ]
    # cited_facts must NOT be a field on the report or its dict.
    assert "cited_facts" not in report.to_dict()


def test_decision_preserved():
    cleanups = _patch_all()
    try:
        report = build_controller_report("u-77", "intent")
    finally:
        _stop(cleanups)
    assert report.decision == "Reduce high category spending."


def test_rationale_preserved():
    cleanups = _patch_all()
    try:
        report = build_controller_report("u-77", "intent")
    finally:
        _stop(cleanups)
    assert report.rationale == "Rent is 40% of income, above the threshold."


# ---------------------------------------------------------------------------
# Confidence handling
# ---------------------------------------------------------------------------


def test_confidence_valid_accepted():
    cleanups = _patch_all(
        send_response=json.dumps({"decision": "d", "confidence": 0.75})
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)
    assert report.confidence == 0.75


def test_confidence_below_zero_normalized():
    cleanups = _patch_all(
        send_response=json.dumps({"decision": "d", "confidence": -0.5})
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)
    assert report.confidence == 0.0


def test_confidence_above_one_normalized():
    cleanups = _patch_all(
        send_response=json.dumps({"decision": "d", "confidence": 1.7})
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)
    assert report.confidence == 1.0


@pytest.mark.parametrize(
    "bad_confidence",
    ["abc", None, {"x": 1}, [1], float("nan"), float("inf")],
)
def test_invalid_confidence_fallback(bad_confidence):
    cleanups = _patch_all(
        send_response=json.dumps({"decision": "d", "confidence": bad_confidence})
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)
    assert report.confidence == 0.0


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------


def test_normalized_actions_converted_to_controller_action():
    cleanups = _patch_all()
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert len(report.actions) == 1
    action = report.actions[0]
    assert isinstance(action, ControllerAction)
    assert action.action_type == "REVIEW_BUDGET"
    assert action.description == "Review the Food budget."
    assert action.severity == "medium"
    assert action.metadata == {"category": "Food"}


def test_action_severity_default_and_invalid():
    cleanups = _patch_all(
        send_response=json.dumps(
            {
                "decision": "d",
                "actions": [
                    {"action_type": "A", "description": "x"},
                    {
                        "action_type": "B",
                        "description": "y",
                        "severity": "bogus",
                    },
                ],
            }
        )
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert report.actions[0].severity == "info"
    assert report.actions[1].severity == "info"


def test_action_metadata_handling():
    cleanups = _patch_all(
        send_response=json.dumps(
            {
                "decision": "d",
                "actions": [
                    {
                        "action_type": "A",
                        "description": "x",
                        "metadata": {"k": "v"},
                    },
                    {"action_type": "B", "description": "y"},
                ],
            }
        )
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert report.actions[0].metadata == {"k": "v"}
    assert report.actions[1].metadata == {}


def test_missing_actions():
    cleanups = _patch_all(
        send_response=json.dumps({"decision": "d", "rationale": "r"})
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)
    assert report.actions == []


def test_unsafe_action_normalized_to_proposal_only():
    cleanups = _patch_all(
        send_response=json.dumps(
            {
                "decision": "d",
                "actions": [
                    {
                        "action_type": "EXECUTE_PAYMENT",
                        "description": "Pay the bill now.",
                        "severity": "high",
                    }
                ],
            }
        )
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert len(report.actions) == 1
    action = report.actions[0]
    assert action.action_type == "PROPOSED_ACTION"
    assert action.metadata["proposed_only"] is True
    assert action.metadata["original_action_type"] == "EXECUTE_PAYMENT"


# ---------------------------------------------------------------------------
# Fallback / malformed responses
# ---------------------------------------------------------------------------


def test_malformed_json_falls_back_to_text():
    # JSON object has no decision/confidence/structure -> parsed, falls back.
    cleanups = _patch_all(send_response="Some plain text without JSON.")
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert report.decision == "Some plain text without JSON."[:512]
    assert report.rationale == "Some plain text without JSON."
    assert report.confidence == 0.0
    assert report.actions == []


def test_plain_text_no_json_object():
    cleanups = _patch_all(send_response="No braces here at all")
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert report.decision.startswith("No braces")
    assert report.actions == []


def test_empty_provider_response():
    cleanups = _patch_all(send_response="")
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert report.decision == "No decision provided."
    assert report.rationale == "No decision provided."
    assert report.confidence == 0.0


def test_fenced_json_block_extracted():
    cleanups = _patch_all(
        send_response='```json\n{"decision": "Fenced", "confidence": 0.6}\n```'
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert report.decision == "Fenced"
    assert report.confidence == 0.6


def test_embedded_json_object_extracted():
    cleanups = _patch_all(
        send_response='Prefix text {"decision": "Emb", "confidence": 0.4} suffix'
    )
    try:
        report = build_controller_report("u", "intent")
    finally:
        _stop(cleanups)

    assert report.decision == "Emb"
    assert report.confidence == 0.4


def test_provider_error_propagates():
    from app.services.openai_provider import AIProviderError

    with patch(
        "app.services.m4.controller.build_financial_context",
        return_value=_sample_context(),
    ), patch(
        "app.services.m4.controller.run_risk_intelligence", return_value=[]
    ), patch(
        "app.services.m4.controller.run_recommendations", return_value=[]
    ), patch(
        "app.services.m4.controller.send_text_request",
        side_effect=AIProviderError("AI request failed"),
    ):
        with pytest.raises(AIProviderError):
            build_controller_report("u", "intent")


def test_risk_service_error_propagates():
    with patch(
        "app.services.m4.controller.build_financial_context",
        return_value=_sample_context(),
    ), patch(
        "app.services.m4.controller.run_risk_intelligence",
        side_effect=RuntimeError("risk boom"),
    ):
        with pytest.raises(RuntimeError):
            build_controller_report("u", "intent")


def test_recommendations_service_error_propagates():
    with patch(
        "app.services.m4.controller.build_financial_context",
        return_value=_sample_context(),
    ), patch(
        "app.services.m4.controller.run_risk_intelligence", return_value=[]
    ), patch(
        "app.services.m4.controller.run_recommendations",
        side_effect=RuntimeError("rec boom"),
    ):
        with pytest.raises(RuntimeError):
            build_controller_report("u", "intent")


def test_context_service_error_propagates():
    with patch(
        "app.services.m4.controller.build_financial_context",
        side_effect=RuntimeError("ctx boom"),
    ):
        with pytest.raises(RuntimeError):
            build_controller_report("u", "intent")


# ---------------------------------------------------------------------------
# Serialization / money
# ---------------------------------------------------------------------------


def test_deterministic_to_dict_serialization():
    cleanups = _patch_all()
    try:
        report = build_controller_report("u-9", "intent")
    finally:
        _stop(cleanups)

    data = report.to_dict()
    assert isinstance(data, dict)
    assert data["user_id"] == "u-9"
    assert data["decision"] == "Reduce high category spending."
    assert "created_at" in data
    assert data["source_facts"]["money_values"]["total_income"] == "10000.0000"
    assert "cited_facts" not in data


def test_money_remains_strings():
    cleanups = _patch_all()
    try:
        report = build_controller_report("u-9", "intent")
    finally:
        _stop(cleanups)

    for value in report.source_facts.money_values.values():
        assert isinstance(value, str)
        assert not isinstance(value, float)


# ---------------------------------------------------------------------------
# Static / AST checks
# ---------------------------------------------------------------------------


def _top_level_imports(path: str):
    tree = ast.parse(open(path, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    return imported


def test_no_direct_db_access_in_controller():
    imports = _top_level_imports("app/services/m4/controller.py")
    assert not imports.intersection({"sqlalchemy", "flask"})
    source = open("app/services/m4/controller.py", encoding="utf-8").read()
    assert "db.session" not in source
    assert "from ..models" not in source
    assert "query(" not in source


def test_controller_does_not_import_openai_sdk():
    imports = _top_level_imports("app/services/m4/controller.py")
    assert "openai" not in imports
    # It must use the provider boundary.
    assert "openai_provider" in imports


def test_controller_prompts_have_no_forbidden_imports():
    imports = _top_level_imports("app/services/m4/controller_prompts.py")
    assert imports.isdisjoint({"openai", "flask", "sqlalchemy", "celery"})


def test_controller_uses_send_text_request_boundary():
    from app.services.m4 import controller

    assert hasattr(controller, "send_text_request")
    source = open("app/services/m4/controller.py", encoding="utf-8").read()
    assert "send_text_request(" in source


def test_prompt_injection_data_as_data_boundary_present():
    from app.services.m4.controller_prompts import (
        build_controller_system_prompt,
    )

    prompt = build_controller_system_prompt()
    assert "DATA" in prompt
    assert "not instructions" in prompt.lower() or "UNTRUSTED" in prompt
    assert "authoritative" in prompt.lower()
    assert "verbatim" in prompt.lower()


def test_financial_safety_instructions_present():
    from app.services.m4.controller_prompts import (
        build_controller_system_prompt,
    )

    prompt = build_controller_system_prompt()
    lowered = prompt.lower()
    assert "never invent" in lowered
    assert "never perform" in lowered
    assert "never approve" in lowered
    assert "proposal" in lowered


def test_no_sensitive_financial_logging():
    imports = _top_level_imports("app/services/m4/controller.py")
    assert "logging" not in imports

    tree = ast.parse(
        open("app/services/m4/controller.py", encoding="utf-8").read()
    )
    # No logger usage in executable code (not just the docstring).
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "logger":
            pytest.fail("controller.py uses a logger")


def test_financial_arithmetic_absent():
    source = open("app/services/m4/controller.py", encoding="utf-8").read()
    # The controller must not do monetary arithmetic (no Decimal usage).
    assert "Decimal(" not in source
