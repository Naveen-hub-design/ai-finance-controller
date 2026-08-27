"""Financial goal intelligence API endpoint."""

import uuid

from flask import Blueprint, current_app, request
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import User
from ..services.financial_goal_intelligence import build_goal_intelligence
from ..services.openai_provider import AIConfigurationError, AIProviderError


financial_goal_intelligence_bp = Blueprint(
    "financial_goal_intelligence",
    __name__,
    url_prefix="/api/users",
)


@financial_goal_intelligence_bp.post(
    "/<uuid:user_id>/financial-goal-intelligence"
)
def generate_financial_goal_intelligence(user_id: uuid.UUID):
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return {"error": "request body must be valid JSON"}, 400

    question = payload.get("question")

    if not isinstance(question, str) or not question.strip():
        return {"error": "question is required"}, 400

    question = question.strip()

    try:
        user = db.session.get(User, user_id)
    except SQLAlchemyError:
        current_app.logger.exception("user lookup failed")
        return {"error": "internal server error"}, 500

    if user is None:
        return {"error": "user not found"}, 404

    try:
        answer = build_goal_intelligence(user_id, question)
    except AIConfigurationError:
        current_app.logger.exception("AI provider is not configured")
        return {"error": "AI provider is not configured"}, 503
    except AIProviderError:
        current_app.logger.exception("AI request failed")
        return {"error": "AI request failed"}, 502

    return {"answer": answer}, 200
