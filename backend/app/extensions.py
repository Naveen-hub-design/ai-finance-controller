"""Shared Flask extension instances, bound to the app in create_app()."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
