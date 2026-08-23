from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Uuid, primary_key=True, server_default=db.text("gen_random_uuid()"))
    email = db.Column(db.String(255), nullable=False, unique=True)
    full_name = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
