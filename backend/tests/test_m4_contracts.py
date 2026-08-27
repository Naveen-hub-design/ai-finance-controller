"""Tests for the M4.0 shared controller contracts.

These verify the data-only contract layer: construction, field preservation,
deterministic serialization, monetary values kept as strings (never floats),
and that the module is isolated from Flask/SQLAlchemy/OpenAI and the DB.
"""

import ast
from datetime import datetime, timezone

import pytest

from app.services.m4 import (
    ControllerAction,
    FinancialControllerReport,
    SourceFacts,
)


def _imported_names(tree: ast.AST) -> set[str]:
    """Return the set of imported module names from an AST tree."""
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    return imported


@pytest.fixture()
def sample_facts() -> SourceFacts:
    return SourceFacts(
        money_values={
            "total_income": "5000.2500",
            "total_expenses": "3200.0000",
            "net_cash_flow": "1800.2500",
        },
        extra={"transaction_count": 12},
    )


@pytest.fixture()
def sample_actions() -> list[ControllerAction]:
    return [
        ControllerAction(
            action_type="reduce_spending",
            description="Consider reducing entertainment spend.",
            severity="medium",
        ),
        ControllerAction(
            action_type="increase_savings",
            description="Consider increasing monthly savings.",
        ),
    ]


def test_report_can_be_constructed(sample_facts, sample_actions):
    report = FinancialControllerReport(
        user_id="u-1",
        intent="assess_overall_health",
        source_facts=sample_facts,
        decision="healthy",
        rationale="Net cash flow is positive.",
        confidence=0.85,
        actions=sample_actions,
    )

    assert isinstance(report, FinancialControllerReport)


def test_required_fields_preserved(sample_facts, sample_actions):
    report = FinancialControllerReport(
        user_id="u-1",
        intent="assess_overall_health",
        source_facts=sample_facts,
        decision="healthy",
        rationale="Net cash flow is positive.",
        confidence=0.85,
        actions=sample_actions,
    )

    expected = {
        "user_id": "u-1",
        "intent": "assess_overall_health",
        "decision": "healthy",
        "rationale": "Net cash flow is positive.",
        "confidence": 0.85,
    }
    actual = report.to_dict()
    for key, value in expected.items():
        assert actual[key] == value


def test_user_id_preserved():
    report = FinancialControllerReport(
        user_id="abc-123",
        intent="x",
        source_facts=SourceFacts(),
        decision="d",
        rationale="r",
        confidence=0.5,
    )
    assert report.user_id == "abc-123"


def test_intent_preserved():
    report = FinancialControllerReport(
        user_id="u",
        intent="forecast_next_month",
        source_facts=SourceFacts(),
        decision="d",
        rationale="r",
        confidence=0.5,
    )
    assert report.intent == "forecast_next_month"


def test_source_facts_preserved(sample_facts):
    report = FinancialControllerReport(
        user_id="u",
        intent="x",
        source_facts=sample_facts,
        decision="d",
        rationale="r",
        confidence=0.5,
    )
    assert report.source_facts == sample_facts
    assert report.to_dict()["source_facts"]["money_values"][
        "total_income"
    ] == "5000.2500"


def test_decision_preserved():
    report = FinancialControllerReport(
        user_id="u",
        intent="x",
        source_facts=SourceFacts(),
        decision="needs_attention",
        rationale="r",
        confidence=0.7,
    )
    assert report.decision == "needs_attention"


def test_rationale_preserved():
    report = FinancialControllerReport(
        user_id="u",
        intent="x",
        source_facts=SourceFacts(),
        decision="d",
        rationale="Monthly expenses are above income.",
        confidence=0.7,
    )
    assert report.rationale == "Monthly expenses are above income."


def test_confidence_preserved():
    report = FinancialControllerReport(
        user_id="u",
        intent="x",
        source_facts=SourceFacts(),
        decision="d",
        rationale="r",
        confidence=0.92,
    )
    assert report.confidence == 0.92


def test_actions_preserved(sample_actions):
    report = FinancialControllerReport(
        user_id="u",
        intent="x",
        source_facts=SourceFacts(),
        decision="d",
        rationale="r",
        confidence=0.5,
        actions=sample_actions,
    )
    assert report.actions == sample_actions


def test_created_at_preserved():
    fixed = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    report = FinancialControllerReport(
        user_id="u",
        intent="x",
        source_facts=SourceFacts(),
        decision="d",
        rationale="r",
        confidence=0.5,
        created_at=fixed,
    )
    assert report.created_at == fixed


def test_default_created_at_is_utc():
    report = FinancialControllerReport(
        user_id="u",
        intent="x",
        source_facts=SourceFacts(),
        decision="d",
        rationale="r",
        confidence=0.5,
    )
    assert isinstance(report.created_at, datetime)
    assert report.created_at.tzinfo is not None


def test_to_dict_is_deterministic_and_json_friendly(sample_facts, sample_actions):
    report_a = FinancialControllerReport(
        user_id="u-1",
        intent="assess",
        source_facts=sample_facts,
        decision="healthy",
        rationale="Positive cash flow.",
        confidence=0.8,
        actions=sample_actions,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    report_b = FinancialControllerReport(
        user_id="u-1",
        intent="assess",
        source_facts=sample_facts,
        decision="healthy",
        rationale="Positive cash flow.",
        confidence=0.8,
        actions=sample_actions,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    import json

    expected = json.dumps(report_a.to_dict(), sort_keys=True)
    actual = json.dumps(report_b.to_dict(), sort_keys=True)
    assert expected == actual

    # created_at is serialized as an ISO string
    assert isinstance(report_a.to_dict()["created_at"], str)


def test_monetary_source_facts_remain_strings_not_floats(sample_facts):
    report = FinancialControllerReport(
        user_id="u",
        intent="x",
        source_facts=sample_facts,
        decision="d",
        rationale="r",
        confidence=0.5,
    )

    serialized = report.to_dict()
    money = serialized["source_facts"]["money_values"]["total_income"]
    assert isinstance(money, str)
    assert money == "5000.2500"
    assert not isinstance(money, float)


def test_contract_module_imports_only_stdlib():
    tree = ast.parse(open("app/services/m4/contracts.py").read())
    imported = _imported_names(tree)

    allowed = {"__future__", "dataclasses", "datetime", "typing"}
    assert imported <= allowed, f"Unexpected imports: {imported - allowed}"


def test_contract_module_does_not_import_flask():
    tree = ast.parse(open("app/services/m4/contracts.py").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all("flask" not in a.name.lower() for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.module is None or "flask" not in node.module.lower()


def test_contract_module_does_not_import_sqlalchemy():
    tree = ast.parse(open("app/services/m4/contracts.py").read())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                "sqlalchemy" not in a.name.lower() for a in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            assert (
                node.module is None
                or "sqlalchemy" not in node.module.lower()
            )


def test_contract_module_does_not_import_openai():
    tree = ast.parse(open("app/services/m4/contracts.py").read())
    imported = set(_imported_names(tree))

    assert "openai" not in imported


def test_contract_module_performs_no_database_access():
    source = open("app/services/m4/contracts.py", encoding="utf-8").read()
    assert "db.session" not in source
    assert "session" not in source.lower()
    assert "connect(" not in source


def test_source_facts_default_empty():
    facts = SourceFacts()
    assert facts.money_values == {}
    assert facts.extra == {}
