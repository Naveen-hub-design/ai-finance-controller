"""AI Finance Controller API application factory."""

from flask import Flask

from .config import Config
from .extensions import db
from .routes.health import health_bp


def create_app(config_object: type[Config] | None = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_object: Optional configuration class overriding the default.

    Returns:
        A configured Flask application instance.
    """
    app = Flask(__name__)
    app.config.from_object(config_object or Config)
    app.json.sort_keys = False

    db.init_app(app)
    app.register_blueprint(health_bp)

    return app
