"""Financial explanation API endpoint."""

import uuid

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import User
from ..services.financial_explanation import explain_financial_question
from ..services.openai_provider import AIConfigurationError, AIProviderError
from ._ownership import require_owner_or


financial_explanation_bp = Blueprint(
    "financial_explanation",
    __name__,
    url_prefix="/api/users",
)


@financial_explanation_bp.post("/<uuid:user_id>/financial-explanation")
@jwt_required()
def generate_financial_explanation(user_id: uuid.UUID):
    forbidden = require_owner_or(user_id)
    if forbidden is not None:
        return forbidden

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
        answer = explain_financial_question(user_id, question)
    except AIConfigurationError:
        current_app.logger.exception("AI provider is not configured")
        return {"error": "AI provider is not configured"}, 503
    except AIProviderError:
        current_app.logger.exception("AI request failed")
        return {"error": "AI request failed"}, 502

    return {"answer": answer}, 200
