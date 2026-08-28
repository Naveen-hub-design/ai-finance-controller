"""Deterministic, explainable financial risk detection (M4.1 Step 1).

This service performs transaction-level risk analysis for a single user. It
is the first concrete consumer of the M2/M3 data model on the path toward
the AI finance controller.

Design rules:

- **Deterministic.** No randomness, current time, floats, ML models, pandas,
  numpy, or sklearn. All monetary math uses :class:`decimal.Decimal`.
- **Explainable.** Every finding carries an ``explainable: True`` flag and a
  ``reason`` that states the exact deterministic rule applied.
- **User-scoped.** Transactions are strictly scoped to the requested user by
  joining through ``Account.user_id``; another user's data is never analyzed.
- **Candidate signals only.** Findings flag *possible* anomalies/duplicates;
  none of them is proof of fraud.
- **Money as strings.** All monetary output values are Decimal-safe strings,
  never floats.

This service may query ``Transaction``/``Account`` directly via SQLAlchemy
because M4.1 is the transaction-level detection layer. It deliberately does
not reuse M2's aggregation endpoints (no duplicate business logic).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from sqlalchemy import select

from ...extensions import db
from ...models import Account, Transaction

# Severity priority ordering for deterministic sort (higher details first).
_SEVERITY_PRIORITY = {"high": 0, "medium": 1, "low": 2}

_LARGE_AMOUNT_MULTIPLE = Decimal("3")
_LARGE_AMOUNT_MIN_EXPENSES = 3
_DUPLICATE_MIN_MATCHES = 2
_RAPID_FREQUENCY_MIN_SAME_DAY = 3
_CATEGORY_SHARE_THRESHOLD = Decimal("0.50")

# A sentinel used to detect when an amount is non-integral.
_ONE = Decimal("1")


@dataclass
class _Finding:
    """Internal mutable finding used for ordering before serialization."""

    type: str
    severity: str
    summary: str
    reason: str
    transaction_ids: List[str] = field(default_factory=list)
    amount: str | None = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "severity": self.severity,
            "summary": self.summary,
            "reason": self.reason,
            "explainable": True,
            "transaction_ids": list(self.transaction_ids),
            "amount": self.amount,
        }


def _to_decimal(value) -> Decimal | None:
    """Safely convert a DB numeric to Decimal, or None if invalid."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _normalize_description(description: str | None) -> str:
    """Normalize a transaction description for duplicate comparison."""
    if description is None:
        return ""
    return description.strip().lower()


def _user_transactions(user_id) -> List[Transaction]:
    """Fetch all transactions belonging to the requested user."""
    # Coerce to a UUID the same way the M2 intelligence layer does, so the
    # query binds correctly against the Uuid column across dialects.
    user_uuid = uuid.UUID(str(user_id))

    stmt = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Account.user_id == user_uuid)
    )
    return list(db.session.execute(stmt).scalars().all())


def _large_amount(findings: List[_Finding], expenses: List[Transaction]) -> None:
    """Flag expenses that are unusually large relative to expense history."""
    if len(expenses) < _LARGE_AMOUNT_MIN_EXPENSES:
        return

    amounts = [_to_decimal(t.amount) for t in expenses]
    valid = [a for a in amounts if a is not None]
    if len(valid) < _LARGE_AMOUNT_MIN_EXPENSES:
        return

    total = sum(valid, Decimal("0"))
    avg = total / Decimal(len(valid))
    threshold = avg * _LARGE_AMOUNT_MULTIPLE

    for tx, amount in zip(expenses, amounts):
        if amount is None:
            continue
        if amount >= threshold:
            findings.append(
                _Finding(
                    type="LARGE_AMOUNT",
                    severity="high",
                    summary="Unusually large expense detected.",
                    reason=(
                        f"Expense amount ${amount} is at least "
                        f"{_LARGE_AMOUNT_MULTIPLE} times the average expense "
                        f"of ${avg} across {len(valid)} expense transactions."
                    ),
                    transaction_ids=[str(tx.id)],
                    amount=f"{amount:.4f}",
                )
            )


def _duplicate_candidate(
    findings: List[_Finding], expenses: List[Transaction]
) -> None:
    """Flag possible duplicate expenses sharing account/amount/date/desc."""
    grouped: Dict[tuple, List[Transaction]] = defaultdict(list)

    for tx in expenses:
        amount = _to_decimal(tx.amount)
        if amount is None:
            continue
        key = (
            str(tx.account_id),
            f"{amount:.4f}",
            tx.transaction_date.isoformat(),
            _normalize_description(tx.description),
        )
        grouped[key].append(tx)

    for key, members in grouped.items():
        if len(members) < _DUPLICATE_MIN_MATCHES:
            continue
        duplicate = members[0]
        findings.append(
            _Finding(
                type="DUPLICATE_CANDIDATE",
                severity="medium",
                summary="Possible duplicate expense detected.",
                reason=(
                    f"{len(members)} expenses share the same account, amount "
                    f"({key[1]}), date ({key[2]}), and normalized description "
                    f"({key[3]!r}). This is a candidate signal, not proof of "
                    "fraud."
                ),
                transaction_ids=[str(t.id) for t in members],
                amount=key[1],
            )
        )


def _round_amount(findings: List[_Finding], expenses: List[Transaction]) -> None:
    """Flag whole-unit expense amounts as a low-severity risk signal."""
    for tx in expenses:
        amount = _to_decimal(tx.amount)
        if amount is None:
            continue
        if amount == amount.to_integral_value():
            findings.append(
                _Finding(
                    type="ROUND_AMOUNT",
                    severity="low",
                    summary="Expense amount is a round number.",
                    reason=(
                        f"Expense amount ${amount} is a whole monetary unit. "
                        "This is only a low-severity risk signal, not proof "
                        "of fraud."
                    ),
                    transaction_ids=[str(tx.id)],
                    amount=f"{amount:.4f}",
                )
            )


def _rapid_frequency(
    findings: List[_Finding], expenses: List[Transaction]
) -> None:
    """Flag many expenses on the same account and same date."""
    grouped: Dict[tuple, List[Transaction]] = defaultdict(list)

    for tx in expenses:
        key = (str(tx.account_id), tx.transaction_date.isoformat())
        grouped[key].append(tx)

    for key, members in grouped.items():
        if len(members) < _RAPID_FREQUENCY_MIN_SAME_DAY:
            continue
        first = members[0]
        amount = _to_decimal(first.amount)
        findings.append(
            _Finding(
                type="RAPID_FREQUENCY",
                severity="medium",
                summary="Several expenses recorded on the same day.",
                reason=(
                    f"{len(members)} expense transactions were recorded on "
                    f"account {key[0]} on date {key[1]}. This is a frequency "
                    "signal, not proof of fraud."
                ),
                transaction_ids=[str(t.id) for t in members],
                amount=f"{amount:.4f}" if amount is not None else None,
            )
        )


def _category_concentration(
    findings: List[_Finding], expenses: List[Transaction]
) -> None:
    """Flag when one expense category dominates total expenses."""
    total = sum(
        (d for d in (_to_decimal(t.amount) for t in expenses) if d is not None),
        Decimal("0"),
    )
    if total <= 0:
        return

    by_category: Dict[str, List[Transaction]] = defaultdict(list)
    for tx in expenses:
        # NULL category is ignored for this signal.
        if tx.category_id is None:
            continue
        by_category[str(tx.category_id)].append(tx)

    for category_id, members in by_category.items():
        cat_total = sum(
            (
                d
                for d in (
                    _to_decimal(t.amount) for t in members
                )
                if d is not None
            ),
            Decimal("0"),
        )
        share = cat_total / total
        if share >= _CATEGORY_SHARE_THRESHOLD:
            findings.append(
                _Finding(
                    type="CATEGORY_CONCENTRATION",
                    severity="medium",
                    summary="Spending is concentrated in one category.",
                    reason=(
                        f"Category {category_id} represents {share:.2%} of "
                        f"total expenses, at least "
                        f"{_CATEGORY_SHARE_THRESHOLD:.0%}. Spending is "
                        "heavily concentrated in a single category."
                    ),
                    transaction_ids=[str(t.id) for t in members],
                    amount=f"{cat_total:.4f}",
                )
            )


def run_risk_intelligence(user_id) -> List[dict]:
    """Run deterministic risk intelligence for a single user.

    Args:
        user_id: Identifier of the user (UUID, string, or equivalent).

    Returns:
        A list of finding dictionaries, each with a stable structure::

            {
                "type": str,
                "severity": "low" | "medium" | "high",
                "summary": str,
                "reason": str,
                "explainable": True,
                "transaction_ids": [str, ...],
                "amount": str | None,
            }

        Findings are sorted deterministically by severity priority (high,
        medium, low), then ``type``, then the joined ``transaction_ids``
        string. Monetary values are always Decimal-safe strings, never
        floats.
    """
    txns = _user_transactions(user_id)
    expenses = [t for t in txns if t.transaction_type == "expense"]

    findings: List[_Finding] = []

    _large_amount(findings, expenses)
    _duplicate_candidate(findings, expenses)
    _round_amount(findings, expenses)
    _rapid_frequency(findings, expenses)
    _category_concentration(findings, expenses)

    findings.sort(
        key=lambda f: (
            _SEVERITY_PRIORITY[f.severity],
            f.type,
            "|".join(f.transaction_ids),
        )
    )

    return [f.to_dict() for f in findings]
