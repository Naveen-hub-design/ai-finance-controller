"""Multi-source reconciliation report contracts (data-only).

Lightweight, typed structures for the reconciliation agent output. They build
on the same conventions as the M4 controller contracts:

- **Data only.** No business logic, no financial calculations, no service or
  AI calls, no database access.
- **Standard library only.** No Flask, SQLAlchemy, OpenAI, or Celery imports;
  the module must remain importable in complete isolation.
- **Monetary values are strings.** Amounts are Decimal-safe strings, never
  floats, so precision is never lost.
- **Serialization-friendly.** A deterministic ``to_dict`` per contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Monetary values are carried as strings to preserve exact decimal precision
# without importing Decimal here (mirrors the M4 source-facts convention).
Money = str


@dataclass(frozen=True)
class MatchRecord:
    """One external statement line that was successfully reconciled."""

    statement_line_id: str
    statement_amount: Money
    statement_date: str
    statement_description: str
    matched_transaction_id: str
    # The deterministic rule that resolved the match, e.g. "external_reference"
    # or "amount_date_description".
    match_basis: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReconciliationException:
    """One external statement line the agent could not resolve.

    Carries a deterministic ``category`` so a human can triage the exception
    (missing ledger record, amount/date mismatch, duplicate, invalid record,
    or other), plus a mutable ``review_status`` for the human review loop
    (UNRESOLVED -> REVIEWED -> RESOLVED).
    """

    statement_line_id: str
    statement_amount: Money
    statement_date: str
    statement_description: str
    # Deterministic exception category, e.g. "MISSING_LEDGER_RECORD".
    category: str = "OTHER"
    # Human review status: "UNRESOLVED", "REVIEWED", or "RESOLVED".
    review_status: str = "UNRESOLVED"
    # Explainable reason for the exception (why no internal ledger match).
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReconciliationReport:
    """The immutable result of a multi-source reconciliation run.

    Reports how many external statement lines were matched against the
    internal ledger, the match rate, the resolved matches, and the exceptions
    that could not be resolved.
    """

    user_id: str
    source: str
    batch_size: int
    matched_count: int
    # Match rate as a Decimal-safe percentage string (e.g. "72.00%").
    match_rate: Money
    ledger_matched_count: int
    # Number of external statement lines the agent could not resolve.
    exception_count: int = 0
    # Exception rate as a Decimal-safe percentage string (e.g. "28.00%").
    exception_rate: Money = "0.00%"
    # Measured wall-clock duration of the reconcile run, in seconds.
    processing_duration_seconds: float = 0.0
    # Throughput = batch_size / processing_duration_seconds (records per second).
    throughput: float = 0.0
    matched: List[MatchRecord] = field(default_factory=list)
    exceptions: List[ReconciliationException] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        return data


__all__ = [
    "MatchRecord",
    "Money",
    "ReconciliationException",
    "ReconciliationReport",
]
