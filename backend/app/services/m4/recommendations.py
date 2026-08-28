"""Deterministic financial recommendation service (M4.2 Step 1).

Produces simple, explainable, rule-based financial recommendations for a
single user. It consumes the M2 deterministic financial facts
(:func:`app.services.financial_intelligence.build_financial_facts`) as the
single source of truth and never re-derives income/expense/balance itself.

Design rules:

- **Money is Decimal.** All monetary arithmetic uses :class:`decimal.Decimal`;
  floats are never used for money.
- **Money out as strings.** Every monetary value in a recommendation is a
  Decimal-safe string, never a float.
- **Explainable.** Each recommendation carries a title/body plus a ``metric``
  describing the rule (name, value, threshold), so a UI or the AI controller
  can explain *why* it exists.
- **Deterministic ordering.** Recommendations are sorted by priority
  (high, medium, low), then type, then title, then grounded amount.
- **No LLM, no OpenAI, no DB access, no logging of financial data.**

Budget-to-spending note: M2 ``budgets`` reference categories via
``category_id`` while ``spending_by_category`` is keyed by category *name*;
M2 facts expose no id-to-name mapping. Matching is therefore done **by
category name**. A budget that resolves to a category name found in
``spending_by_category`` uses that spending; otherwise its spending is
treated as unmatched (no overspend is claimed). This keeps the service
deterministic and free of database access.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from ..financial_intelligence import build_financial_facts

_HIGH_CATEGORY_RATIO = Decimal("0.30")
_LOW_SAVINGS_RATE = Decimal("0.10")
_GOAL_PROGRESS_THRESHOLD = Decimal("50")


class _Recommendation:
    __slots__ = (
        "priority",
        "type",
        "title",
        "body",
        "grounded_amount",
        "metric",
    )

    def __init__(
        self,
        priority: str,
        type_: str,
        title: str,
        body: str,
        grounded_amount: str,
        metric: Dict[str, str],
    ) -> None:
        self.priority = priority
        self.type = type_
        self.title = title
        self.body = body
        self.grounded_amount = grounded_amount
        self.metric = metric

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "type": self.type,
            "title": self.title,
            "body": self.body,
            "grounded_amount": self.grounded_amount,
            "metric": self.metric,
        }


_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _to_decimal(value: Any) -> Decimal | None:
    """Safely convert a value (string/int/Decimal/None) to Decimal."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _fmt(value: Decimal, places: int = 4) -> str:
    """Format a Decimal to a fixed number of decimal places as a string."""
    return format(value.quantize(Decimal("1." + "0" * places)))


def _percent(value: Decimal) -> str:
    """Format a ratio as a percentage string with two decimal places."""
    pct = value * Decimal("100")
    return _fmt(pct.quantize(Decimal("0.01")), places=2) + "%"


def _spending_by_name(facts: dict) -> Dict[str, Decimal]:
    """Map category name -> total spending amount from M2 facts."""
    result: Dict[str, Decimal] = {}
    for entry in facts.get("spending_by_category") or []:
        if not isinstance(entry, dict):
            continue
        amount = _to_decimal(entry.get("amount"))
        if amount is None:
            continue
        name_key = entry.get("category")
        if isinstance(name_key, str) and name_key != "":
            result[name_key] = result.get(name_key, Decimal("0")) + amount
    return result


def _rule_budget_overspend(
    recs: List[_Recommendation],
    facts: dict,
    spending_by_name: Dict[str, Decimal],
) -> None:
    """Rule 1: flag budgets whose category spending exceeds the budget."""
    for budget in facts.get("budgets") or []:
        if not isinstance(budget, dict):
            continue
        amount = _to_decimal(budget.get("amount"))
        if amount is None:
            continue

        cat_name = budget.get("category_name")
        spending = spending_by_name.get(cat_name, Decimal("0"))
        if spending <= amount:
            continue

        overspend = spending - amount
        utilization = (spending / amount) if amount > 0 else Decimal("0")
        recs.append(
            _Recommendation(
                priority="high",
                type_="BUDGET_OVERSPEND",
                title="Budget exceeded",
                body=(
                    f"Spending in {cat_name or 'this category'} exceeded the "
                    f"budget by {_fmt(overspend)} (budget {_fmt(amount)}, "
                    f"actual {_fmt(spending)})."
                ),
                grounded_amount=_fmt(overspend),
                metric={
                    "name": "budget_utilization",
                    "value": _percent(utilization),
                    "threshold": "100%",
                },
            )
        )


def _rule_unused_budget(
    recs: List[_Recommendation],
    facts: dict,
    spending_by_name: Dict[str, Decimal],
) -> None:
    """Rule 4: flag budgets with meaningfully unused capacity (informational)."""
    for budget in facts.get("budgets") or []:
        if not isinstance(budget, dict):
            continue
        amount = _to_decimal(budget.get("amount"))
        if amount is None:
            continue

        cat_name = budget.get("category_name")
        spending = spending_by_name.get(cat_name, Decimal("0"))
        unused = amount - spending
        if unused <= 0:
            continue

        recs.append(
            _Recommendation(
                priority="low",
                type_="UNUSED_BUDGET",
                title="Budget capacity available",
                body=(
                    f"The budget for {cat_name or 'this category'} of "
                    f"{_fmt(amount)} has {_fmt(unused)} still unused "
                    f"({_fmt(spending)} spent). This is informational; no "
                    "transfers are recommended."
                ),
                grounded_amount=_fmt(unused),
                metric={
                    "name": "unused_budget_amount",
                    "value": _fmt(unused),
                    "threshold": ">0",
                },
            )
        )


def _rule_high_category_spend(
    recs: List[_Recommendation],
    facts: dict,
    total_income: Decimal,
) -> None:
    """Rule 2: flag expense categories consuming a large share of income."""
    if total_income <= 0:
        return

    for entry in facts.get("spending_by_category") or []:
        if not isinstance(entry, dict):
            continue
        amount = _to_decimal(entry.get("amount"))
        if amount is None or amount <= 0:
            continue
        cat_name = entry.get("category")
        if not isinstance(cat_name, str) or cat_name == "":
            continue

        ratio = amount / total_income
        if ratio < _HIGH_CATEGORY_RATIO:
            continue

        recs.append(
            _Recommendation(
                priority="medium",
                type_="HIGH_CATEGORY_SPEND",
                title="High spending in a category",
                body=(
                    f"Spending in {cat_name} ({_fmt(amount)}) is "
                    f"{_percent(ratio)} of total income ({_fmt(total_income)}), "
                    f"at or above the {_HIGH_CATEGORY_RATIO:.0%} threshold."
                ),
                grounded_amount=_fmt(amount),
                metric={
                    "name": "category_income_share",
                    "value": _percent(ratio),
                    "threshold": "30%",
                },
            )
        )


def _rule_low_savings_rate(
    recs: List[_Recommendation],
    facts: dict,
    total_income: Decimal,
) -> None:
    """Rule 3: flag a savings rate below 10% (negative cash flow included)."""
    if total_income <= 0:
        return

    net_cash_flow = _to_decimal(facts.get("net_cash_flow"))
    if net_cash_flow is None:
        return

    rate = net_cash_flow / total_income
    if rate >= _LOW_SAVINGS_RATE:
        return

    recs.append(
        _Recommendation(
            priority="medium",
            type_="LOW_SAVINGS_RATE",
            title="Low savings rate",
            body=(
                f"Net cash flow ({_fmt(net_cash_flow)}) represents a savings "
                f"rate of {_percent(rate)} of income, below the 10% target."
            ),
            grounded_amount=_fmt(net_cash_flow),
            metric={
                "name": "savings_rate",
                "value": _percent(rate),
                "threshold": "10%",
            },
        )
    )


def _rule_goal_progress(
    recs: List[_Recommendation],
    facts: dict,
) -> None:
    """Rule 5: nudge active goals below 50% progress that have a target date."""
    for goal in facts.get("financial_goals") or []:
        if not isinstance(goal, dict):
            continue
        if goal.get("status") != "active":
            continue

        target = _to_decimal(goal.get("target_amount"))
        current = _to_decimal(goal.get("current_amount"))
        progress = _to_decimal(goal.get("progress_percent"))
        if target is None or target <= 0 or current is None:
            continue
        if progress is None or progress >= _GOAL_PROGRESS_THRESHOLD:
            continue
        # A target date must be present for this rule to apply.
        target_date = goal.get("target_date")
        if not target_date:
            continue

        remaining = target - current
        if remaining < 0:
            remaining = Decimal("0")

        name = goal.get("name") or "this goal"
        recs.append(
            _Recommendation(
                priority="medium",
                type_="GOAL_PROGRESS",
                title="Goal progress is low",
                body=(
                    f"The active goal '{name}' is {_fmt(progress, 2)}% funded "
                    f"({_fmt(current)} of {_fmt(target)}), below 50%, with a "
                    f"target date of {target_date}. About {_fmt(remaining)} "
                    "remains to reach it."
                ),
                grounded_amount=_fmt(remaining),
                metric={
                    "name": "goal_progress",
                    "value": _fmt(progress, 2),
                    "threshold": "50%",
                },
            )
        )


def run_recommendations(user_id) -> List[dict]:
    """Return deterministic financial recommendations for a user.

    Args:
        user_id: Identifier of the user (UUID, string, or equivalent).

    Returns:
        A list of recommendation dicts, each with the shape::

            {
                "priority": "high" | "medium" | "low",
                "type": str,
                "title": str,
                "body": str,
                "grounded_amount": str,
                "metric": {"name": str, "value": str, "threshold": str},
            }

        Monetary fields are always Decimal-safe strings, never floats.
        Results are sorted by priority (high, medium, low), then type, then
        title, then grounded amount.
    """
    facts = build_financial_facts(user_id)
    if not isinstance(facts, dict):
        return []

    total_income = _to_decimal(facts.get("total_income"))
    if total_income is None:
        total_income = Decimal("0")

    spending_by_name = _spending_by_name(facts)

    recs: List[_Recommendation] = []
    _rule_budget_overspend(recs, facts, spending_by_name)
    _rule_high_category_spend(recs, facts, total_income)
    _rule_low_savings_rate(recs, facts, total_income)
    _rule_unused_budget(recs, facts, spending_by_name)
    _rule_goal_progress(recs, facts)

    recs.sort(
        key=lambda r: (
            _PRIORITY_ORDER[r.priority],
            r.type,
            r.title,
            _sort_amount(r.grounded_amount),
        )
    )

    return [r.to_dict() for r in recs]


def _sort_amount(grounded_amount: str) -> Decimal:
    """Parse a grounded amount for numeric (deterministic) sorting."""
    parsed = _to_decimal(grounded_amount)
    return parsed if parsed is not None else Decimal("0")
