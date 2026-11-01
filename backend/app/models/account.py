import uuid

from ..extensions import db


class Account(db.Model):
    __tablename__ = "accounts"

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

    # Optional business scope (Milestone F9.x.1). NULL => personal account.
    # When set, the value is validated server-side against the caller's
    # business membership before the account can be created/modified.
    business_id = db.Column(
        db.Uuid,
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=True,
    )

    name = db.Column(db.String(255), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)

    currency = db.Column(
        db.String(3),
        nullable=False,
        server_default="INR",
    )

    current_balance = db.Column(
        db.Numeric(19, 4),
        nullable=False,
        server_default="0",
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )
