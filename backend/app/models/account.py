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
