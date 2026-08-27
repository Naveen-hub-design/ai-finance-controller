"""Financial explanation orchestration service (Milestone 3.4).

This module is the first orchestration layer that connects the earlier
services to actually produce a financial explanation. It chains:

    user_id + user_question
        -> M3.2 build_financial_context()
        -> M3.3 build_financial_system_prompt()
        -> M3.3 build_financial_user_prompt()
        -> M3.1 send_text_request()
        -> AI response text

It performs no database queries, no financial calculations, and never
calls the external AI SDK directly. The only interaction with the AI
provider goes through M3.1's :func:`send_text_request`. Provider
configuration and request errors are allowed to propagate to callers
unchanged.
"""

from __future__ import annotations

from .financial_context import build_financial_context
from .financial_prompts import (
    build_financial_system_prompt,
    build_financial_user_prompt,
)
from .openai_provider import send_text_request


def explain_financial_question(user_id, user_question: str) -> str:
    """Explain a user's financial question using the configured AI.

    Builds the user's financial context, constructs the system and user
    prompts, sends them to the configured AI provider, and returns the
    provider's text response unchanged.

    No context, prompt, or provider content is logged here. The user
    question and financial context are passed to the prompt layer exactly
    as supplied and never mutated.

    Errors are intentionally not caught: if context building, prompt
    construction, or the AI provider fails, the underlying exception
    (e.g. ``AIConfigurationError`` or ``AIProviderError``) propagates to
    the caller unchanged rather than being replaced by a fake fallback.

    Args:
        user_id: Identifier of the user (UUID, string, or equivalent).
        user_question: The user's financial question, passed through
            verbatim.

    Returns:
        The AI provider's text response as a string.
    """
    financial_context = build_financial_context(user_id)
    system_prompt = build_financial_system_prompt()
    user_prompt = build_financial_user_prompt(
        financial_context,
        user_question,
    )

    response = send_text_request(
        user_prompt,
        system_prompt=system_prompt,
    )

    return response
