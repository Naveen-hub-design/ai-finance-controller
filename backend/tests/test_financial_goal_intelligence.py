"""Tests for the M3.6 financial goal intelligence service.

All provider/context dependencies are mocked where the service uses them,
so no real AI call, network request, or API key is ever required.
"""

import ast
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app.services import financial_goal_intelligence
from app.services.financial_goal_intelligence import build_goal_intelligence


def _sample_context():
    return {
        "summary": {"total_income": "5000.5000", "total_expenses": "3000.0000"},
        "activity": {"transaction_count": 3},
        "spending_by_category": [],
        "budgets": [],
        "financial_goals": [
            {
                "name": "Emergency fund",
                "target_amount": "10000.0000",
                "current_amount": "4000.0000",
                "progress_percent": "40.0000",
                "target_date": "2026-12-31",
                "status": "active",
            }
        ],
    }


@contextmanager
def _patched():
    """Enter all dependency patches and yield their mocks."""
    with (
        patch(
            "app.services.financial_goal_intelligence.build_financial_context"
        ) as mock_context,
        patch(
            "app.services.financial_goal_intelligence.send_text_request"
        ) as mock_send,
    ):
        mock_context.return_value = _sample_context()
        mock_send.return_value = "goal reply"
        yield mock_context, mock_send


def _capture_user_prompt(mock_send):
    """Return the user prompt string passed to send_text_request."""
    args, _ = mock_send.call_args
    return args[0]


def test_provider_response_returned_unchanged():
    with _patched() as (_mock_context, mock_send):
        mock_send.return_value = "  Exact goal answer  "
        result = build_goal_intelligence("user-1", "Can I reach my goal?")

    assert result == "  Exact goal answer  "


def test_context_builder_called_once_with_user_id():
    with _patched() as (mock_context, _mock_send):
        build_goal_intelligence("goal-user-42", "How close am I?")

    mock_context.assert_called_once_with("goal-user-42")


def test_goal_user_prompt_contains_financial_context():
    with _patched() as (mock_context, mock_send):
        build_goal_intelligence("user-1", "Question?")

    prompt = _capture_user_prompt(mock_send)
    assert 'Emergency fund' in prompt
    assert '10000.0000' in prompt
    assert 'progress_percent' in prompt


def test_exact_user_question_reaches_prompt_construction():
    question = "Will I hit my target by the deadline?"

    with _patched() as (_mock_context, mock_send):
        build_goal_intelligence("user-1", question)

    prompt = _capture_user_prompt(mock_send)
    assert question in prompt


def test_provider_receives_generated_user_prompt():
    with _patched() as (_mock_context, mock_send):
        build_goal_intelligence("user-1", "Question?")

    args, _ = mock_send.call_args
    assert args[0] == _capture_user_prompt(mock_send)
    assert "financial context" in args[0].lower()
    assert "User goal-related question:" in args[0]


def test_provider_receives_system_prompt():
    with _patched() as (_mock_context, mock_send):
        build_goal_intelligence("user-1", "Question?")

    _, call_kwargs = mock_send.call_args
    assert "system_prompt" in call_kwargs
    assert "goal" in call_kwargs["system_prompt"].lower()


def test_provider_errors_propagate():
    from app.services.openai_provider import AIProviderError

    with _patched() as (_mock_context, mock_send):
        mock_send.side_effect = AIProviderError("AI request failed")
        with pytest.raises(AIProviderError):
            build_goal_intelligence("user-1", "Question?")


def test_configuration_errors_propagate():
    from app.services.openai_provider import AIConfigurationError

    with _patched() as (_mock_context, mock_send):
        mock_send.side_effect = AIConfigurationError(
            "AI provider is not configured"
        )
        with pytest.raises(AIConfigurationError):
            build_goal_intelligence("user-1", "Question?")


def test_context_builder_errors_propagate():
    with _patched() as (mock_context, _mock_send):
        mock_context.side_effect = RuntimeError("context failure")
        with pytest.raises(RuntimeError):
            build_goal_intelligence("user-1", "Question?")


def test_no_database_access_performed_directly():
    source = open(financial_goal_intelligence.__file__).read()

    assert "db.session" not in source
    assert "sqlalchemy" not in source.lower()
    assert "from ..models" not in source
    assert "from ..extensions" not in source


def test_no_openai_sdk_imported_directly():
    tree = ast.parse(open(financial_goal_intelligence.__file__).read())

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)

    assert "openai" not in imported
    assert "financial_intelligence" not in "".join(imported)


def test_context_not_mutated():
    import copy

    with _patched() as (mock_context, mock_send):
        known = _sample_context()
        mock_context.return_value = known
        original = copy.deepcopy(known)

        mock_send.side_effect = None

        def _capture(fc, q):
            return "some answer"

        with patch(
            "app.services.financial_goal_intelligence"
            "._build_goal_user_prompt",
            side_effect=_capture,
        ):
            build_goal_intelligence("user-1", "Question?")

        assert known == original


def test_user_question_preserved_with_special_chars():
    question = 'Reach $10,000 by "Dec" & then \u20b9 \U0001f4b0'

    with _patched() as (_mock_context, mock_send):
        build_goal_intelligence("user-1", question)

    prompt = _capture_user_prompt(mock_send)
    assert question in prompt
