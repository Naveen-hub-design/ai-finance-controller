"""Tests for the M3.2 financial context builder.

These tests mock :func:`build_financial_facts` so the context builder is
verified in isolation without any database access or financial
calculation.
"""

from decimal import Decimal
from unittest.mock import patch

from app.services.financial_context import build_financial_context


def _sample_facts():
    return {
        "total_income": "5000.5000",
        "total_expenses": "1250.2500",
        "net_cash_flow": "3750.2500",
        "transaction_count": 3,
        "income_transaction_count": 1,
        "expense_transaction_count": 2,
        "account_balance": "90000.0000",
        "spending_by_category": [
            {"category": "Groceries", "amount": "4500.0000"},
            {"category": "Food", "amount": "2000.0000"},
        ],
        "budgets": [
            {
                "id": "budget-1",
                "category_id": "cat-1",
                "amount": "10000.0000",
                "period": "monthly",
                "start_date": "2026-08-01",
                "end_date": "2026-08-31",
            }
        ],
        "financial_goals": [
            {
                "id": "goal-1",
                "name": "Emergency Fund",
                "target_amount": "100000.0000",
                "current_amount": "25000.0000",
                "progress_percent": "25.00",
                "target_date": None,
                "status": "active",
            }
        ],
    }


def test_context_contains_expected_top_level_sections():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ):
        context = build_financial_context("user-1")

    assert set(context.keys()) == {
        "summary",
        "activity",
        "spending_by_category",
        "budgets",
        "financial_goals",
    }
    assert set(context["summary"].keys()) == {
        "total_income",
        "total_expenses",
        "net_cash_flow",
        "account_balance",
    }
    assert set(context["activity"].keys()) == {
        "transaction_count",
        "income_transaction_count",
        "expense_transaction_count",
    }


def test_summary_values_are_preserved_exactly():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ):
        context = build_financial_context("user-1")

    assert context["summary"] == {
        "total_income": "5000.5000",
        "total_expenses": "1250.2500",
        "net_cash_flow": "3750.2500",
        "account_balance": "90000.0000",
    }


def test_activity_counts_are_preserved_exactly():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ):
        context = build_financial_context("user-1")

    assert context["activity"] == {
        "transaction_count": 3,
        "income_transaction_count": 1,
        "expense_transaction_count": 2,
    }


def test_spending_by_category_data_is_preserved():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ):
        context = build_financial_context("user-1")

    assert context["spending_by_category"] == [
        {"category": "Groceries", "amount": "4500.0000"},
        {"category": "Food", "amount": "2000.0000"},
    ]


def test_budget_data_is_preserved():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ):
        context = build_financial_context("user-1")

    assert context["budgets"] == [
        {
            "id": "budget-1",
            "category_id": "cat-1",
            "amount": "10000.0000",
            "period": "monthly",
            "start_date": "2026-08-01",
            "end_date": "2026-08-31",
        }
    ]


def test_financial_goal_data_is_preserved():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ):
        context = build_financial_context("user-1")

    assert context["financial_goals"] == [
        {
            "id": "goal-1",
            "name": "Emergency Fund",
            "target_amount": "100000.0000",
            "current_amount": "25000.0000",
            "progress_percent": "25.00",
            "target_date": None,
            "status": "active",
        }
    ]


def test_m2_builder_called_with_supplied_user_id():
    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=_sample_facts(),
    ) as mock_facts:
        build_financial_context("user-42")

    mock_facts.assert_called_once_with("user-42")


def test_context_builder_does_not_make_database_calls():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ) as mock_facts:
        context = build_financial_context("user-1")

    mock_facts.assert_called_once()
    assert context["summary"]["total_income"] == "5000.5000"


def test_monetary_values_remain_strings():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ):
        context = build_financial_context("user-1")

    for key in (
        "total_income",
        "total_expenses",
        "net_cash_flow",
        "account_balance",
    ):
        assert isinstance(context["summary"][key], str)
        Decimal(context["summary"][key])  # still a valid decimal string

    assert isinstance(context["spending_by_category"][0]["amount"], str)
    assert isinstance(context["budgets"][0]["amount"], str)
    assert isinstance(context["financial_goals"][0]["target_amount"], str)
    assert isinstance(context["financial_goals"][0]["progress_percent"], str)


def test_source_facts_are_not_mutated():
    facts = _sample_facts()

    with patch(
        "app.services.financial_context.build_financial_facts",
        return_value=facts,
    ):
        context = build_financial_context("user-1")

    context["spending_by_category"].append({"category": "Extra", "amount": "1.0000"})
    context["summary"]["total_income"] = "9999.0000"
    context["budgets"].clear()
    context["financial_goals"].clear()

    assert facts == _sample_facts()
