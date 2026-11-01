"""M4.4 decision / audit trail model.

Persists immutable, explainable M4 decisions/signals/recommendations so the
AI Finance Controller has an auditable history.

Design rules:

- **Append-only.** There is no update or delete endpoint/API for audit
  records, and the model carries no ``updated_at`` column. Records are
  created once and never modified.
- **No financial logic.** This model does no financial calculations and does
  not reinterpret stored payload numbers. The JSON payload is stored
  faithfully.
- **No AI calls.** This model never invokes any AI provider.
- **User scoped.** Each record is tied to a user via a foreign key with
  ``ON DELETE CASCADE``, matching the existing models.
- **Optionally business scoped.** Records created for a business-carried
  action carry an optional ``business_id`` so business members can read the
  business-scoped trail; records created without a business stay personal.
"""

import uuid

from sqlalchemy.dialects.postgresql import JSONB

from ..extensions import db


class AuditRecord(db.Model):
    """An immutable, user-scoped audit record for an M4 decision."""

    __tablename__ = "audit_records"

    # Python-side default keeps inserts portable across dialects (the test
    # suite runs on in-memory SQLite); the PostgreSQL server default is kept
    # for inserts made outside the ORM. Both generate UUIDv4 values.
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
    # Optional business scope: NULL means a personal (non-business) record.
    # Records derived from a business-carried action store the business so the
    # business-scoped audit listing can isolate members from personal data.
    business_id = db.Column(
        db.Uuid,
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    kind = db.Column(db.String(50), nullable=False)
    # JSON on all dialects; JSONB on PostgreSQL for durable, queryable audit
    # payloads. SQLite stores it as text but still round-trips the dict.
    payload = db.Column(
        db.JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    def to_dict(self) -> dict:
        """Serialize the record safely for API responses.

        UUIDs and timestamps are serialized to strings so the result is
        JSON-friendly. The payload is returned faithfully, unmodified.
        """
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "kind": self.kind,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
        }
