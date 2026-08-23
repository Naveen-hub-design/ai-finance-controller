"""Health-check endpoints for the API."""

from flask import Blueprint

health_bp = Blueprint("health", __name__, url_prefix="/api")

SERVICE_NAME = "finance-controller-api"


@health_bp.get("/health")
def health_check() -> tuple[dict[str, str], int]:
    """Report basic service liveness for load balancers and orchestrators."""
    return {"status": "healthy", "service": SERVICE_NAME}, 200
