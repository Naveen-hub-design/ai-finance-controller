import uuid

from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    # Python-side default keeps inserts portable across dialects (the test
    # suite runs on in-memory SQLite); the PostgreSQL server default is kept
    # for inserts made outside the ORM. Both generate UUIDv4 values.
    id = db.Column(
        db.Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("gen_random_uuid()"),
    )
    email = db.Column(db.String(255), nullable=False, unique=True)
    full_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
