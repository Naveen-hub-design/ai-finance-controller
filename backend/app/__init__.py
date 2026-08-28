"""AI Finance Controller API application factory."""

from flask import Flask

from .config import Config
from .extensions import db
from .routes.health import health_bp
from .routes.users import users_bp
from .routes.accounts import accounts_bp
from .routes.transactions import transactions_bp
from .routes.categories import categories_bp
from .routes.budgets import budgets_bp
from .routes.financial_goals import financial_goals_bp
from .routes.financial_summary import financial_summary_bp
from .routes.financial_facts import financial_facts_bp
from .routes.financial_explanation import financial_explanation_bp
from .routes.financial_goal_intelligence import (
    financial_goal_intelligence_bp,
)
from .routes.m4_risk import m4_risk_bp
from .routes.m4_recommendations import m4_recommendations_bp
from .routes.m4_controller import m4_controller_bp
from .routes.m4_controller_async import m4_controller_async_bp
from .routes.m4_audit import m4_audit_bp
from . import models  # noqa: F401


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    app.json.sort_keys = False

    db.init_app(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(financial_goals_bp)
    app.register_blueprint(financial_summary_bp)
    app.register_blueprint(financial_facts_bp)
    app.register_blueprint(financial_explanation_bp)
    app.register_blueprint(financial_goal_intelligence_bp)
    app.register_blueprint(m4_risk_bp)
    app.register_blueprint(m4_recommendations_bp)
    app.register_blueprint(m4_controller_bp)
    app.register_blueprint(m4_controller_async_bp)
    app.register_blueprint(m4_audit_bp)

    return app
