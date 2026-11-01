"""Multi-source reconciliation: external statement line model.

Represents a single record from a second, external financial source (for
example a bank or fintech statement) that the reconciliation agent matches
against the internal ledger (``Transaction`` rows). Persisting this source is
what makes the multi-source reconciliation loop real: the internal ledger is
source A and these lines are source B.

Design rules:

- **External record, not a ledger row.** A ``StatementLine`` is a claim from
  an external source, never an authoritative ledger entry. It is not summed
  into balances or included in M2/M3 financial facts.
- **Mutable match state only.** The agent writes the outcome of a reconcile
  run onto each line (``status`` and ``matched_transaction_id``). The
  monetary/date/description fields are the immutable inputs from the external
  source.
- **User/business scoped** with ``ON DELETE CASCADE`` foreign keys, matching
  the existing models; business scope is optional (NULL => personal).
- **Money as Decimal.** Amounts use :class:`decimal.Decimal` via
  ``Numeric(19, 4)`` and are exposed as Decimal-safe strings, never floats.
"""

import uuid

from ..extensions import db


class StatementLine(db.Model):
    """A single line of an external source awaiting reconciliation."""

    __tablename__ = "statement_lines"

    id = db.Column(
        db.Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("gen_random_uuid()"),
    )
    user_id = db.Column(
        db.Uuid,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Optional business scope (NULL => personal), matching the other models.
    business_id = db.Column(
        db.Uuid,
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=True,
    )
    # Name of the external source (e.g. "bank_statement"). Used to scope the
    # reconcile agent to one source batch.
    source = db.Column(db.String(50), nullable=False, default="bank_statement")
    # Optional stable external reference id (e.g. bank txn reference). When
    # present it is the strongest match key.
    external_reference = db.Column(db.String(255))
    amount = db.Column(db.Numeric(19, 4), nullable=False)
    transaction_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text)
    # Reconcile outcome updated by the agent. "pending" before a run.
    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending",
    )
    # The matched internal ledger transaction, if this line was resolved.
    matched_transaction_id = db.Column(
        db.Uuid,
        db.ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Deterministic exception category for unmatched lines (e.g.
    # "MISSING_LEDGER_RECORD", "AMOUNT_MISMATCH"); None when matched/pending.
    category = db.Column(db.String(40))
    # Human review loop status: "UNRESOLVED" -> "REVIEWED" -> "RESOLVED".
    review_status = db.Column(
        db.String(20),
        nullable=False,
        default="UNRESOLVED",
        server_default="UNRESOLVED",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    def to_dict(self) -> dict:
        """Serialize the line for API responses (money as a string)."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "business_id": str(self.business_id) if self.business_id else None,
            "source": self.source,
            "external_reference": self.external_reference,
            "amount": str(self.amount),
            "transaction_date": self.transaction_date.isoformat(),
            "description": self.description,
            "status": self.status,
            "matched_transaction_id": (
                str(self.matched_transaction_id)
                if self.matched_transaction_id
                else None
            ),
            "category": self.category,
            "review_status": self.review_status,
            "created_at": self.created_at.isoformat(),
        }
