import uuid

from ..extensions import db


class FinancialGoal(db.Model):
    __tablename__ = "financial_goals"

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
    target_amount = db.Column(db.Numeric(19, 4), nullable=False)
    current_amount = db.Column(db.Numeric(19, 4), nullable=False, server_default="0")
    target_date = db.Column(db.Date)
    status = db.Column(db.String(20), nullable=False, server_default="active")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
