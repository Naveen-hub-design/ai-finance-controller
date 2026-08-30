import uuid

from werkzeug.security import check_password_hash, generate_password_hash

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
    # Stores only the Werkzeug-generated password hash; never a plaintext
    # password. Nullable because users may be created outside the API (e.g.
    # directly via ORM in tests/seeders); the registration route enforces
    # that a password is supplied.
    password_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=db.func.now())

    def set_password(self, password: str) -> None:
        """Hash and store ``password`` using Werkzeug's PBKDF2-based scheme."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Return True if ``password`` matches the stored hash, else False."""
        if self.password_hash is None:
            return False
        return check_password_hash(self.password_hash, password)
