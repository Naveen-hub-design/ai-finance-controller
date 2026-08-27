"""Reusable financial context builder (Milestone 3.2).

This module consumes the already-verified M2 financial facts produced by
:func:`app.services.financial_intelligence.build_financial_facts` and
reorganizes them into a stable, structured, AI-ready context. It performs
no database queries and no financial calculations of its own; it only
arranges the underlying facts into logical sections while preserving the
exact values (monetary amounts remain strings to avoid floating-point
precision loss).

Later milestones (e.g. M3.3 prompt construction) consume this output.
"""

from __future__ import annotations

import copy
from typing import Any

from .financial_intelligence import build_financial_facts


def build_financial_context(user_id) -> dict:
    """Build a structured AI-ready financial context for a user.

    The context is produced deterministically from the user's M2
    financial facts and is organized into logical sections. Monetary
    values are preserved exactly as returned by M2 (decimal-precision
    strings, never floats).

    The returned dictionary is a fresh, deep copy of the underlying
    facts, so mutating it never affects the original facts object or
    any other caller.

    Args:
        user_id: Identifier of the user (UUID, string, or equivalent).

    Returns:
        A dictionary with the following structure::

            {
                "summary": {
                    "total_income": str,
                    "total_expenses": str,
                    "net_cash_flow": str,
                    "account_balance": str,
                },
                "activity": {
                    "transaction_count": int,
                    "income_transaction_count": int,
                    "expense_transaction_count": int,
                },
                "spending_by_category": [ {category, amount}, ... ],
                "budgets": [ {...}, ... ],
                "financial_goals": [ {...}, ... ],
            }
    """
    facts = build_financial_facts(user_id)

    context = {
        "summary": {
            "total_income": facts["total_income"],
            "total_expenses": facts["total_expenses"],
            "net_cash_flow": facts["net_cash_flow"],
            "account_balance": facts["account_balance"],
        },
        "activity": {
            "transaction_count": facts["transaction_count"],
            "income_transaction_count": facts["income_transaction_count"],
            "expense_transaction_count": facts["expense_transaction_count"],
        },
        "spending_by_category": copy.deepcopy(facts["spending_by_category"]),
        "budgets": copy.deepcopy(facts["budgets"]),
        "financial_goals": copy.deepcopy(facts["financial_goals"]),
    }

    return context
