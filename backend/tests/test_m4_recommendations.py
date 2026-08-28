"""Tests for the M4.2 deterministic financial recommendation service."""

import ast
from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.m4.recommendations import run_recommendations


def _facts(**overrides) -> dict:
    """Return a realistic set of M2 financial facts (mocked)."""
    base = {
        "total_income": "10000.0000",
        "total_expenses": "6000.0000",
        "net_cash_flow": "4000.0000",
        "transaction_count": 10,
        "income_transaction_count": 5,
        "expense_transaction_count": 5,
        "account_balance": "50000.0000",
        "spending_by_category": [],
        "budgets": [],
        "financial_goals": [],
    }
    base.update(overrides)
    return base


@contextmanager
def _patched(facts: dict):
    with patch(
        "app.services.m4.recommendations.build_financial_facts",
        return_value=facts,
    ) as mock_facts:
        yield mock_facts


def _types(recs: list[dict]) -> list[str]:
    return [r["type"] for r in recs]


def test_empty_facts_returns_empty():
    with _patched(_facts()):
        assert run_recommendations("user-1") == []


def test_no_facts_returns_empty():
    with _patched(None):
        assert run_recommendations("user-1") == []


def test_budget_overspend():
    facts = _facts(
        spending_by_category=[{"category": "Food", "amount": "3000.0000"}],
        budgets=[
            {
                "id": "b-1",
                "category_id": "c-1",
                "category_name": "Food",
                "amount": "2000.0000",
                "period": "monthly",
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    os = next(r for r in recs if r["type"] == "BUDGET_OVERSPEND")
    assert os["priority"] == "high"
    assert os["grounded_amount"] == "1000.0000"
    assert os["metric"]["name"] == "budget_utilization"
    assert os["metric"]["threshold"] == "100%"


def test_budget_exactly_equal_spending_no_overspend():
    facts = _facts(
        spending_by_category=[{"category": "Food", "amount": "2000.0000"}],
        budgets=[
            {
                "id": "b-1",
                "category_name": "Food",
                "amount": "2000.0000",
                "period": "monthly",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "BUDGET_OVERSPEND" not in _types(recs)


def test_unused_budget():
    facts = _facts(
        spending_by_category=[{"category": "Food", "amount": "500.0000"}],
        budgets=[
            {
                "id": "b-1",
                "category_name": "Food",
                "amount": "2000.0000",
                "period": "monthly",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    ub = next(r for r in recs if r["type"] == "UNUSED_BUDGET")
    assert ub["priority"] == "low"
    assert ub["grounded_amount"] == "1500.0000"


def test_high_category_spending():
    facts = _facts(
        total_income="10000.0000",
        spending_by_category=[{"category": "Rent", "amount": "4000.0000"}],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    hs = next(r for r in recs if r["type"] == "HIGH_CATEGORY_SPEND")
    assert hs["priority"] == "medium"
    assert hs["grounded_amount"] == "4000.0000"
    assert hs["metric"]["threshold"] == "30%"
    # 4000/10000 = 40%
    assert hs["metric"]["value"] == "40.00%"


def test_category_below_threshold():
    facts = _facts(
        total_income="10000.0000",
        spending_by_category=[{"category": "Rent", "amount": "2000.0000"}],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "HIGH_CATEGORY_SPEND" not in _types(recs)


def test_zero_income_skips_category_rule_and_savings():
    facts = _facts(
        total_income="0.0000",
        net_cash_flow="0.0000",
        spending_by_category=[{"category": "Rent", "amount": "4000.0000"}],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "HIGH_CATEGORY_SPEND" not in _types(recs)
    assert "LOW_SAVINGS_RATE" not in _types(recs)


def test_low_savings_rate():
    facts = _facts(
        total_income="10000.0000",
        net_cash_flow="500.0000",
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    ls = next(r for r in recs if r["type"] == "LOW_SAVINGS_RATE")
    assert ls["priority"] == "medium"
    assert ls["grounded_amount"] == "500.0000"
    assert ls["metric"]["name"] == "savings_rate"
    assert ls["metric"]["threshold"] == "10%"
    # 500/10000 = 5%
    assert ls["metric"]["value"] == "5.00%"


def test_healthy_savings_rate():
    facts = _facts(
        total_income="10000.0000",
        net_cash_flow="3000.0000",
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "LOW_SAVINGS_RATE" not in _types(recs)


def test_negative_cash_flow_triggers_low_savings():
    facts = _facts(
        total_income="10000.0000",
        net_cash_flow="-2000.0000",
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    ls = next(r for r in recs if r["type"] == "LOW_SAVINGS_RATE")
    assert ls["grounded_amount"] == "-2000.0000"


def test_active_goal_below_50():
    facts = _facts(
        financial_goals=[
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
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    gp = next(r for r in recs if r["type"] == "GOAL_PROGRESS")
    assert gp["priority"] == "medium"
    # remaining = 100000 - 25000 = 75000
    assert gp["grounded_amount"] == "75000.0000"
    assert gp["metric"]["threshold"] == "50%"


def test_active_goal_above_50_no_recommendation():
    facts = _facts(
        financial_goals=[
            {
                "id": "g-1",
                "name": "Emergency Fund",
                "target_amount": "100000.0000",
                "current_amount": "80000.0000",
                "progress_percent": "80.00",
                "target_date": "2026-12-31",
                "status": "active",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "GOAL_PROGRESS" not in _types(recs)


def test_completed_goal_ignored():
    facts = _facts(
        financial_goals=[
            {
                "id": "g-1",
                "name": "Emergency Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": "2026-12-31",
                "status": "completed",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "GOAL_PROGRESS" not in _types(recs)


def test_paused_goal_ignored():
    facts = _facts(
        financial_goals=[
            {
                "id": "g-1",
                "name": "Emergency Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": "2026-12-31",
                "status": "paused",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "GOAL_PROGRESS" not in _types(recs)


def test_cancelled_goal_ignored():
    facts = _facts(
        financial_goals=[
            {
                "id": "g-1",
                "name": "Emergency Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": "2026-12-31",
                "status": "cancelled",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "GOAL_PROGRESS" not in _types(recs)


def test_goal_without_target_date_ignored():
    facts = _facts(
        financial_goals=[
            {
                "id": "g-1",
                "name": "Emergency Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": None,
                "status": "active",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    assert "GOAL_PROGRESS" not in _types(recs)


def test_multiple_recommendations():
    facts = _facts(
        total_income="10000.0000",
        net_cash_flow="300.0000",
        spending_by_category=[{"category": "Rent", "amount": "4000.0000"}],
        budgets=[
            {
                "id": "b-1",
                "category_name": "Food",
                "amount": "2000.0000",
                "period": "monthly",
            }
        ],
        financial_goals=[
            {
                "id": "g-1",
                "name": "Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": "2026-12-31",
                "status": "active",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    types = set(_types(recs))
    assert "HIGH_CATEGORY_SPEND" in types
    assert "LOW_SAVINGS_RATE" in types
    assert "UNUSED_BUDGET" in types
    assert "GOAL_PROGRESS" in types


def test_deterministic_ordering():
    facts = _facts(
        total_income="10000.0000",
        net_cash_flow="300.0000",
        spending_by_category=[
            {"category": "Rent", "amount": "4000.0000"},
        ],
        budgets=[
            {
                "id": "b-1",
                "category_name": "Food",
                "amount": "2000.0000",
                "period": "monthly",
            }
        ],
        financial_goals=[
            {
                "id": "g-1",
                "name": "Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": "2026-12-31",
                "status": "active",
            }
        ],
    )
    prio = {"high": 0, "medium": 1, "low": 2}
    with _patched(facts):
        a = run_recommendations("user-1")
        b = run_recommendations("user-1")

    assert a == b
    priorities = [r["priority"] for r in a]
    assert priorities == sorted(priorities, key=lambda p: prio[p])
    for lev in ("high", "medium", "low"):
        same = [r["type"] for r in a if r["priority"] == lev]
        assert same == sorted(same)


def test_all_monetary_outputs_are_strings():
    facts = _facts(
        total_income="10000.0000",
        net_cash_flow="300.0000",
        spending_by_category=[{"category": "Rent", "amount": "4000.0000"}],
        budgets=[
            {
                "id": "b-1",
                "category_name": "Food",
                "amount": "2000.0000",
                "period": "monthly",
            }
        ],
        financial_goals=[
            {
                "id": "g-1",
                "name": "Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": "2026-12-31",
                "status": "active",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    for r in recs:
        assert isinstance(r["grounded_amount"], str)
        assert not isinstance(r["grounded_amount"], float)
        assert isinstance(Decimal(r["grounded_amount"]), Decimal)
        for value in r["metric"].values():
            assert isinstance(value, str)
            assert not isinstance(value, float)


def test_no_float_monetary_values():
    facts = _facts(
        total_income="10000.0000",
        net_cash_flow="300.0000",
        spending_by_category=[{"category": "Rent", "amount": "4000.0000"}],
        budgets=[
            {
                "id": "b-1",
                "category_name": "Food",
                "amount": "2000.0000",
                "period": "monthly",
            }
        ],
        financial_goals=[
            {
                "id": "g-1",
                "name": "Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": "2026-12-31",
                "status": "active",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    for r in recs:
        assert not isinstance(r["grounded_amount"], float)
        for value in r["metric"].values():
            assert not isinstance(value, float)


def test_uses_decimal_arithmetic():
    # A large, exact decimal subtraction exercises Decimal math.
    facts = _facts(
        spending_by_category=[
            {"category": "Food", "amount": "3333.3333"},
        ],
        budgets=[
            {
                "id": "b-1",
                "category_name": "Food",
                "amount": "1000.0000",
                "period": "monthly",
            }
        ],
    )
    with _patched(facts):
        recs = run_recommendations("user-1")

    os = next(r for r in recs if r["type"] == "BUDGET_OVERSPEND")
    assert os["grounded_amount"] == "2333.3333"


def test_service_calls_build_financial_facts():
    facts = _facts()
    with _patched(facts) as mock_facts:
        run_recommendations("user-42")

    mock_facts.assert_called_once_with("user-42")


def test_no_openai_import():
    tree = ast.parse(
        open("app/services/m4/recommendations.py", encoding="utf-8").read()
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


def test_no_forbidden_dependencies():
    tree = ast.parse(
        open("app/services/m4/recommendations.py", encoding="utf-8").read()
    )
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    forbidden = {"openai", "flask", "celery", "pandas", "numpy", "sklearn"}
    assert imported.isdisjoint(forbidden), imported & forbidden


def test_no_database_access_directly():
    source = open(
        "app/services/m4/recommendations.py", encoding="utf-8"
    ).read()
    assert "db.session" not in source
    assert "from ..models" not in source
    assert "from ...models" not in source
    assert "from sqlalchemy" not in source
