"""Tests for the M3.3 financial prompt system.

These tests verify the prompt-construction layer is deterministic and
independent of any provider, database, or external service. This module
must not import OpenAI at all.
"""

import json

from app.services.financial_prompts import (
    build_financial_system_prompt,
    build_financial_user_prompt,
)


def _sample_context():
    return {
        "summary": {
            "total_income": "5000.5000",
            "total_expenses": "1250.2500",
            "net_cash_flow": "3750.2500",
            "account_balance": "90000.0000",
        },
        "activity": {
            "transaction_count": 3,
            "income_transaction_count": 1,
            "expense_transaction_count": 2,
        },
        "spending_by_category": [
            {"category": "Groceries", "amount": "4500.0000"},
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


def test_system_prompt_is_non_empty_string():
    prompt = build_financial_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_system_prompt_contains_grounding_instruction():
    prompt = build_financial_system_prompt()
    assert "verified" in prompt
    assert "source of truth" in prompt
    assert "financial facts" in prompt


def test_system_prompt_contains_no_invention_instruction():
    prompt = build_financial_system_prompt()
    assert "Never invent" in prompt
    assert "transactions" in prompt
    assert "amounts" in prompt


def test_system_prompt_contains_insufficient_data_behavior():
    prompt = build_financial_system_prompt()
    assert "insufficient" in prompt
    assert "available data" in prompt


def test_system_prompt_contains_prompt_injection_data_boundary():
    prompt = build_financial_system_prompt()
    assert "DATA only" in prompt
    assert "prompt-injection" in prompt
    assert "never override" in prompt
    assert "take precedence" in prompt


def test_user_prompt_contains_financial_context():
    context = _sample_context()
    prompt = build_financial_user_prompt(context, "How am I doing?")

    assert "total_income" in prompt
    assert "5000.5000" in prompt
    assert "FINANCIAL CONTEXT" in prompt
    assert "supplied by the application" in prompt


def test_user_prompt_contains_user_question():
    prompt = build_financial_user_prompt(
        _sample_context(),
        "How much did I spend on Groceries?",
    )
    assert "How much did I spend on Groceries?" in prompt


def test_user_prompt_preserves_monetary_strings_exactly():
    context = _sample_context()
    prompt = build_financial_user_prompt(context, "Question?")

    for value in (
        "5000.5000",
        "1250.2500",
        "3750.2500",
        "90000.0000",
        "4500.0000",
        "10000.0000",
        "100000.0000",
        "25000.0000",
        "25.00",
    ):
        assert value in prompt


def test_user_prompt_does_not_convert_monetary_values_to_float():
    context = _sample_context()
    prompt = build_financial_user_prompt(context, "Question?")

    import json as _json

    expected = _json.dumps(
        context,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    # The complete context is embedded verbatim (compact, stable JSON), so
    # every monetary value keeps its exact scale-4 string representation
    # and is never truncated or converted to a float.
    assert expected in prompt
    assert '"total_income":"5000.5000"' in prompt
    assert '"amount":"4500.0000"' in prompt
    assert '"target_amount":"100000.0000"' in prompt


def test_context_serialization_is_deterministic():
    context = _sample_context()
    first = build_financial_user_prompt(context, "Question?")
    second = build_financial_user_prompt(context, "Question?")
    assert first == second


def test_equivalent_dicts_different_insertion_order_produce_equivalent_prompt():
    context_a = _sample_context()
    context_b = {
        "financial_goals": context_a["financial_goals"],
        "budgets": context_a["budgets"],
        "spending_by_category": context_a["spending_by_category"],
        "activity": context_a["activity"],
        "summary": context_a["summary"],
    }

    prompt_a = build_financial_user_prompt(context_a, "Question?")
    prompt_b = build_financial_user_prompt(context_b, "Question?")

    assert prompt_a == prompt_b


def test_input_context_is_not_mutated():
    context = _sample_context()
    original = json.dumps(context, sort_keys=True)

    build_financial_user_prompt(context, "Question?")

    assert json.dumps(context, sort_keys=True) == original


def test_user_question_is_preserved_exactly():
    question = "  What is my net cash flow?  "
    prompt = build_financial_user_prompt(_sample_context(), question)
    assert question in prompt


def test_empty_financial_sections_handled_predictably():
    context = {
        "summary": {
            "total_income": "0.0000",
            "total_expenses": "0.0000",
            "net_cash_flow": "0.0000",
            "account_balance": "0.0000",
        },
        "activity": {
            "transaction_count": 0,
            "income_transaction_count": 0,
            "expense_transaction_count": 0,
        },
        "spending_by_category": [],
        "budgets": [],
        "financial_goals": [],
    }

    prompt = build_financial_user_prompt(context, "Any activity?")

    assert '"spending_by_category":[]' in prompt
    assert '"budgets":[]' in prompt
    assert '"financial_goals":[]' in prompt
    assert "0.0000" in prompt


def test_no_openai_or_provider_import_in_module():
    import ast
    import sys

    module = sys.modules["app.services.financial_prompts"]
    tree = ast.parse(open(module.__file__).read())

    imported_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.add(node.module.split(".")[0])

    assert "openai" not in imported_names
    assert "openai_provider" not in imported_names
