import uuid

from ..extensions import db


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(
        db.Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("gen_random_uuid()"),
    )
    account_id = db.Column(
        db.Uuid,
        db.ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id = db.Column(
        db.Uuid,
        db.ForeignKey("categories.id", ondelete="SET NULL"),
    )
    amount = db.Column(db.Numeric(19, 4), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text)
    transaction_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
