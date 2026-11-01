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


def build_financial_context(user_id, business_id=None) -> dict:
    """Build a structured AI-ready financial context for a user or business."""
    facts = build_financial_facts(user_id, business_id)

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
