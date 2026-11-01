"""Deterministic multi-source financial reconciliation (finance-ops agent).

Reconciles an external source (source B, ``StatementLine`` rows) against the
internal ledger (source A, ``Transaction`` rows) to close a finance-ops loop.
It reports the match rate across the whole batch and the exceptions it could
not resolve.

Design rules (mirroring the existing M4 services):

- **Deterministic.** No randomness, current time, floats, ML models, pandas,
  or numpy. All monetary math uses :class:`decimal.Decimal`.
- **Explainable.** Every exception carries a ``reason`` stating the exact rule
  that prevented a match.
- **Scoped.** Both sources are strictly scoped to the requested user or
  business; another user's data is never analyzed.
- **Money as strings.** All monetary output values are Decimal-safe strings,
  never floats.
- **Exact-key matching.** A statement line matches an internal ledger
  transaction when the normalized amount, date, and description agree. This
  reuses the exact-grouping approach already proven by
  ``anomaly_detection._duplicate_candidate``.
- **One ledger entry per match.** Each internal transaction is consumed at most
  once, so a single ledger entry cannot satisfy many statement lines.
- **Loop closing.** Each statement line is annotated with its outcome
  (``status`` and ``matched_transaction_id``) so the reconcile result is
  durable and auditable; an immutable audit record is written by the caller.

This service is the reconciliation *agent*: given a batch, it resolves as many
lines as it can and reports the rest as exceptions.
"""

from __future__ import annotations

import time as _time
import uuid
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from sqlalchemy import select

from ...extensions import db
from ...models import StatementLine, Transaction
from .reconciliation_contracts import (
    MatchRecord,
    ReconciliationException,
    ReconciliationReport,
)

StatusPending = "pending"
StatusMatched = "matched"
StatusException = "exception"

# Deterministic human-review statuses (Phase 7).
ReviewUnresolved = "UNRESOLVED"
ReviewReviewed = "REVIEWED"
ReviewResolved = "RESOLVED"
VALID_REVIEW_STATUSES = {ReviewUnresolved, ReviewReviewed, ReviewResolved}

# Deterministic exception categories (Phase 4), each backed by match evidence.
CategoryOther = "OTHER"
CategoryMissingLedger = "MISSING_LEDGER_RECORD"
CategoryDuplicate = "DUPLICATE_RECORD"
CategoryAmountMismatch = "AMOUNT_MISMATCH"
CategoryDateMismatch = "DATE_MISMATCH"
CategoryInvalid = "INVALID_RECORD"


def _to_decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _fmt_amount(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}"


def _match_key(amount: Decimal, iso_date: str, description: str) -> tuple:
    """The exact-match key reusing the duplicate-detector grouping shape."""
    desc = (description or "").strip().lower()
    return (_fmt_amount(amount), iso_date, desc)


def _normalize_business(business_id) -> uuid.UUID | None:
    if business_id is None:
        return None
    return uuid.UUID(str(business_id))


def run_reconciliation(
    user_id,
    business_id=None,
    source: str = "bank_statement",
) -> ReconciliationReport:
    """Reconcile the given source batch against the internal ledger.

    Args:
        user_id: Identifier of the owner (UUID, string, or equivalent).
        business_id: Optional business scope.
        source: The external source label to reconcile.

    Returns:
        A :class:`ReconciliationReport` (with match rate and exceptions).
    """
    user_uuid = uuid.UUID(str(user_id))
    business_uuid = _normalize_business(business_id)

    # Source A: internal ledger transactions in the scope.
    ledger_txs = __transactions_by_scope(user_uuid, business_uuid)

    # Source B: the external statement batch in the scope.
    statement_stmt = select(StatementLine).where(StatementLine.user_id == user_uuid)
    if business_uuid is not None:
        statement_stmt = statement_stmt.where(
            StatementLine.business_id == business_uuid
        )
    else:
        statement_stmt = statement_stmt.where(StatementLine.business_id.is_(None))
    statement_stmt = statement_stmt.where(StatementLine.source == source)
    statement_lines = list(
        db.session.execute(statement_stmt.order_by(StatementLine.created_at, StatementLine.id)).scalars().all()
    )

    # Index internal ledger transactions by exact match key. Each value is a
    # list so identical ledger entries can each satisfy a statement line.
    # Two additional indexes support deterministic near-miss classification:
    #   date_description -> amounts   (to detect AMOUNT_MISMATCH)
    #   amount_description -> dates   (to detect DATE_MISMATCH)
    ledger_by_key: Dict[tuple, List[Transaction]] = defaultdict(list)
    ledger_by_date_desc: Dict[tuple, set] = defaultdict(set)
    ledger_by_amount_desc: Dict[tuple, set] = defaultdict(set)
    ever_keys: set = set()
    for tx in ledger_txs:
        amount = _to_decimal(tx.amount)
        if amount is None:
            continue
        date_iso = tx.transaction_date.isoformat()
        desc = (tx.description or "").strip().lower()
        key = _match_key(amount, date_iso, tx.description)
        ledger_by_key[key].append(tx)
        ever_keys.add(key)
        ledger_by_date_desc[(date_iso, desc)].add(_fmt_amount(amount))
        ledger_by_amount_desc[(_fmt_amount(amount), desc)].add(date_iso)

    start_ts = _time.perf_counter()
    matched: List[MatchRecord] = []
    exceptions: List[ReconciliationException] = []
    matched_ledger_ids: set = set()

    for line in statement_lines:
        amount = _to_decimal(line.amount)
        if amount is None:
            _append_exception(
                exceptions, line, CategoryInvalid,
                "the statement line has an invalid amount",
            )
            _set_line_status(line, StatusException, None, CategoryInvalid)
            continue

        date_iso = line.transaction_date.isoformat()
        desc = (line.description or "").strip().lower()
        key = _match_key(amount, date_iso, line.description)
        pool = ledger_by_key.get(key, [])
        if pool:
            ledger_tx = pool.pop(0)
            matched_ledger_ids.add(str(ledger_tx.id))
            matched.append(
                MatchRecord(
                    statement_line_id=str(line.id),
                    statement_amount=_fmt_amount(amount),
                    statement_date=date_iso,
                    statement_description=line.description,
                    matched_transaction_id=str(ledger_tx.id),
                    match_basis="amount_date_description",
                )
            )
            _set_line_status(line, StatusMatched, ledger_tx.id, None)
        else:
            if key in ever_keys:
                # The exact key exists in the ledger but its entry(s) were
                # already consumed by an identical earlier line: a duplicate
                # claimed against insufficient ledger entries.
                category, reason = CategoryDuplicate, (
                    "the ledger entry for this exact amount/date/description was "
                    "already matched by an identical statement line"
                )
            else:
                category, reason = _classify_exception(
                    amount, date_iso, desc,
                    ledger_by_date_desc, ledger_by_amount_desc,
                )
            _append_exception(
                exceptions, line, category,
                f"no internal ledger transaction matched amount {_fmt_amount(amount)} "
                f"on {date_iso} with description {line.description!r}; {reason}",
            )
            _set_line_status(line, StatusException, None, category)

    elapsed = _time.perf_counter() - start_ts

    batch_size = len(statement_lines)
    matched_count = len(matched)
    exception_count = len(exceptions)
    match_rate = _percent(matched_count, batch_size)
    exception_rate = _percent(exception_count, batch_size)
    throughput = _throughput(batch_size, elapsed)

    db.session.commit()

    return ReconciliationReport(
        user_id=str(user_uuid),
        source=source,
        batch_size=batch_size,
        matched_count=matched_count,
        match_rate=match_rate,
        ledger_matched_count=len(matched_ledger_ids),
        exception_count=exception_count,
        exception_rate=exception_rate,
        processing_duration_seconds=elapsed,
        throughput=throughput,
        matched=matched,
        exceptions=exceptions,
    )


def _append_exception(exceptions, line, category: str, reason: str) -> None:
    amount = _to_decimal(line.amount)
    exceptions.append(
        ReconciliationException(
            statement_line_id=str(line.id),
            statement_amount=(
                _fmt_amount(amount) if amount is not None else str(line.amount)
            ),
            statement_date=line.transaction_date.isoformat(),
            statement_description=line.description,
            category=category,
            reason=reason,
        )
    )


def _classify_exception(
    amount: Decimal,
    date_iso: str,
    desc: str,
    ledger_by_date_desc: Dict[tuple, set],
    ledger_by_amount_desc: Dict[tuple, set],
) -> tuple:
    """Return ``(category, reason)`` for an unmatched statement line.

    Deterministic near-miss rules, each backed by actual ledger evidence:

    - A ledger entry with the same date+description but a different amount
      indicates an ``AMOUNT_MISMATCH``.
    - A ledger entry with the same amount+description but a different date
      indicates a ``DATE_MISMATCH``.
    - Any other unmatched line is a ``MISSING_LEDGER_RECORD``.
    """
    amt_str = _fmt_amount(amount)
    same_date_desc = ledger_by_date_desc.get((date_iso, desc), set())
    if same_date_desc:
        differing = [a for a in sorted(same_date_desc) if a != amt_str]
        if differing:
            return (
                CategoryAmountMismatch,
                f"ledger shows amount {differing[0]} on the same date/description",
            )
    same_amount_desc = ledger_by_amount_desc.get((amt_str, desc), set())
    if same_amount_desc:
        differing = [d for d in sorted(same_amount_desc) if d != date_iso]
        if differing:
            return (
                CategoryDateMismatch,
                f"ledger shows amount {amt_str} on date {differing[0]} (different date)",
            )
    return (
        CategoryMissingLedger,
        "no ledger entry is near this line's amount, date, or description",
    )


def _set_line_status(line: StatementLine, status: str, tx_id, category=None) -> None:
    line.status = status
    line.matched_transaction_id = tx_id
    if category is not None:
        line.category = category


def _percent(part: int, whole: int) -> str:
    if whole <= 0:
        return "0.00%"
    ratio = Decimal(part) / Decimal(whole)
    pct = (ratio * Decimal("100")).quantize(Decimal("0.01"))
    return f"{pct:.2f}%"


def _throughput(records: int, seconds: float) -> float:
    """Records processed per second, precise decimals to avoid float noise."""
    if seconds <= 0:
        return 0.0
    try:
        rate = (Decimal(records) / Decimal(str(seconds))).quantize(Decimal("0.01"))
        return float(rate)
    except (InvalidOperation, ValueError, ArithmeticError):
        return 0.0


def __transactions_by_scope(user_uuid, business_uuid):
    """Load all internal ledger transactions in the user/business scope.

    Joins through Account so business-scoped txns are read without summing
    personal ones, mirroring ``anomaly_detection._user_transactions``.
    """
    from ...models import Account

    if business_uuid is not None:
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.business_id == business_uuid)
        )
    else:
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .where(Account.user_id == user_uuid, Account.business_id.is_(None))
        )
    return list(db.session.execute(stmt).scalars().all())
