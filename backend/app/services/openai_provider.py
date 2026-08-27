"""Reusable OpenAI provider integration (Milestone 3.1).

This service is intentionally generic: it only knows how to send a text
request to the configured model through the OpenAI Responses API and
return the model's text reply. It holds no financial or domain context;
M3.2 and later milestones build that on top of this provider.

Configuration comes from the Flask application config (sourced from
environment variables via ``Config``): ``OPENAI_API_KEY`` and
``OPENAI_MODEL``.
"""

from __future__ import annotations

import logging
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """Raised when the configured AI provider cannot complete a request."""


class AIConfigurationError(AIProviderError):
    """Raised when the AI provider is not configured (e.g. key missing)."""


def _client():
    """Return a lazily-created OpenAI client for the current app.

    The client is created on first use so a missing API key does not
    break application startup. Uses the sync client; a single instance
    is cached on the Flask app for reuse across requests.
    """
    from openai import OpenAI

    cached = getattr(current_app, "_openai_client", None)
    if cached is not None:
        return cached

    api_key = current_app.config.get("OPENAI_API_KEY") or ""
    client = OpenAI(api_key=api_key)
    current_app._openai_client = client
    return client


def get_model() -> str:
    """Return the configured OpenAI model name."""
    return current_app.config.get("OPENAI_MODEL", "gpt-5.6-luna")


def is_configured() -> bool:
    """Return True when an OpenAI API key is present in config."""
    return bool(current_app.config.get("OPENAI_API_KEY"))


def send_text_request(
    prompt: str,
    *,
    system_prompt: str | None = None,
    model: str | None = None,
) -> str:
    """Send a text request to the configured model and return its reply.

    Uses the OpenAI Responses API. If no API key is configured, raises
    :class:`AIConfigurationError`. OpenAI and transport failures are
    logged server-side and re-raised as :class:`AIProviderError` with a
    safe message that never contains the secret or request contents.

    Args:
        prompt: The user text to send to the model.
        system_prompt: Optional system instructions for the model.
        model: Override the configured model for this single call.

    Returns:
        The model's text response as a string.
    """
    if not is_configured():
        logger.error("OpenAI API key is not configured")
        raise AIConfigurationError("AI provider is not configured")

    use_model = model or get_model()

    try:
        client = _client()

        params: dict[str, Any] = {
            "model": use_model,
            "input": prompt,
        }
        if system_prompt is not None:
            params["instructions"] = system_prompt

        response = client.responses.create(**params)
    except Exception as exc:  # noqa: BLE001 - surface any failure safely
        logger.exception("OpenAI request failed")
        raise AIProviderError("AI request failed") from exc

    return _extract_text(response)


def _extract_text(response: Any) -> str:
    """Extract the top-level text from a Responses API response object."""
    parts: list[str] = []

    try:
        output = response.output or []
        for item in output:
            if item.type == "message" and item.content:
                for part in item.content:
                    if getattr(part, "type", None) == "output_text":
                        parts.append(part.text or "")
    except AttributeError:
        raise AIProviderError("AI response contained no text")

    text = "\n".join(parts)
    if not text:
        raise AIProviderError("AI response contained no text")

    return text
