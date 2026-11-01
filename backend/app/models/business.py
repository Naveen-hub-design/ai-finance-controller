"""Business + business membership models (Milestone F9.x.1).

These back the multi-user business architecture. A business is the container
unit; membership records (OWNER / FINANCE_MANAGER) govern who may access it.

Security notes:
- PLATFORM_ADMIN is deliberately NOT a member role. Membership always gates
  business access regardless of platform role.
- A MERCHANT creates a business and becomes its OWNER.
- Authorization is resolved at request time from the database -- business_id
  is never trusted from the JWT (the JWT stays identity-only).
"""

import uuid

from ..extensions import db


class Business(db.Model):
    __tablename__ = "businesses"

    id = db.Column(
        db.Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("gen_random_uuid()"),
    )
    name = db.Column(db.String(255), nullable=False)
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


class BusinessMember(db.Model):
    __tablename__ = "business_members"

    id = db.Column(
        db.Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=db.text("gen_random_uuid()"),
    )
    business_id = db.Column(
        db.Uuid,
        db.ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = db.Column(
        db.Uuid,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = db.Column(db.String(32), nullable=False, default="FINANCE_MANAGER")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
    )
    __table_args__ = (
        db.UniqueConstraint("business_id", "user_id", name="uq_business_member"),
    )
