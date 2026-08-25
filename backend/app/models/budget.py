import uuid

from ..extensions import db


class Budget(db.Model):
    __tablename__ = "budgets"

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
    category_id = db.Column(
        db.Uuid,
        db.ForeignKey("categories.id", ondelete="SET NULL"),
    )
    amount = db.Column(db.Numeric(19, 4), nullable=False)
    period = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
