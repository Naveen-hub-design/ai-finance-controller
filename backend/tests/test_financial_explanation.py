"""Tests for the M3.4 financial explanation orchestration service.

All provider/context/prompt dependencies are mocked where
financial_explanation uses them, so no real AI call, network request, or
API key is ever required.
"""

import ast
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app.services import financial_explanation
from app.services.financial_explanation import explain_financial_question


def _sample_context():
    return {
        "summary": {"total_income": "5000.5000", "total_expenses": "1.0000"},
        "activity": {"transaction_count": 3},
        "spending_by_category": [],
        "budgets": [],
        "financial_goals": [],
    }


@contextmanager
def _patched():
    """Enter all four dependency patches and yield their mocks."""
    with (
        patch(
            "app.services.financial_explanation.build_financial_context"
        ) as mock_context,
        patch(
            "app.services.financial_explanation.build_financial_system_prompt"
        ) as mock_system,
        patch(
            "app.services.financial_explanation.build_financial_user_prompt"
        ) as mock_user,
        patch(
            "app.services.financial_explanation.send_text_request"
        ) as mock_send,
    ):
        mock_context.return_value = _sample_context()
        mock_system.return_value = "system prompt text"
        mock_user.return_value = "user prompt text"
        mock_send.return_value = "provider reply"
        yield mock_context, mock_system, mock_user, mock_send


def test_returns_provider_response_unchanged():
    with _patched() as (_mock_context, _mock_system, _mock_user, mock_send):
        mock_send.return_value = "  Exact provider answer  "
        result = explain_financial_question("user-1", "Question?")

    assert result == "  Exact provider answer  "


def test_context_builder_called_once_with_user_id():
    with _patched() as (mock_context, _mock_system, _mock_user, _mock_send):
        explain_financial_question("user-42", "How am I doing?")

    mock_context.assert_called_once_with("user-42")


def test_system_prompt_builder_called_once():
    with _patched() as (_mock_context, mock_system, _mock_user, _mock_send):
        explain_financial_question("user-1", "Question?")

    mock_system.assert_called_once()


def test_user_prompt_receives_exact_context():
    with _patched() as (_mock_context, _mock_system, mock_user, _mock_send):
        explain_financial_question("user-1", "Question?")

    mock_user.assert_called_once()
    args, _ = mock_user.call_args
    assert args[0] == _sample_context()


def test_user_prompt_receives_exact_user_question():
    question = "What is my spending?"

    with _patched() as (_mock_context, _mock_system, mock_user, _mock_send):
        explain_financial_question("user-1", question)

    args, _ = mock_user.call_args
    assert args[1] == question


def test_send_text_request_receives_generated_user_prompt():
    with _patched() as (_mock_context, _mock_system, mock_user, mock_send):
        mock_user.return_value = "generated user prompt"
        explain_financial_question("user-1", "Question?")

    args, _ = mock_send.call_args
    assert args[0] == "generated user prompt"


def test_send_text_request_receives_system_prompt_via_kwarg():
    with _patched() as (_mock_context, mock_system, _mock_user, mock_send):
        mock_system.return_value = "my system instructions"
        explain_financial_question("user-1", "Question?")

    _, call_kwargs = mock_send.call_args
    assert call_kwargs["system_prompt"] == "my system instructions"


def test_provider_response_returned_unchanged():
    with _patched() as (_mock_context, _mock_system, _mock_user, mock_send):
        mock_send.return_value = "provider text"
        result = explain_financial_question("user-1", "Question?")

    assert result == "provider text"


def test_provider_errors_propagate():
    from app.services.openai_provider import AIProviderError

    with _patched() as (_mock_context, _mock_system, _mock_user, mock_send):
        mock_send.side_effect = AIProviderError("AI request failed")
        with pytest.raises(AIProviderError):
            explain_financial_question("user-1", "Question?")


def test_configuration_errors_propagate():
    from app.services.openai_provider import AIConfigurationError

    with _patched() as (_mock_context, _mock_system, _mock_user, mock_send):
        mock_send.side_effect = AIConfigurationError(
            "AI provider is not configured"
        )
        with pytest.raises(AIConfigurationError):
            explain_financial_question("user-1", "Question?")


def test_context_builder_errors_propagate():
    with _patched() as (mock_context, _mock_system, _mock_user, _mock_send):
        mock_context.side_effect = RuntimeError("context failure")
        with pytest.raises(RuntimeError):
            explain_financial_question("user-1", "Question?")


def test_prompt_builder_errors_propagate():
    with _patched() as (_mock_context, _mock_system, mock_user, _mock_send):
        mock_user.side_effect = ValueError("prompt failure")
        with pytest.raises(ValueError):
            explain_financial_question("user-1", "Question?")


def test_no_database_access_performed_directly():
    source = open(financial_explanation.__file__).read()

    assert "db.session" not in source
    assert "sqlalchemy" not in source.lower()
    assert "from ..models" not in source
    assert "from ..extensions" not in source


def test_no_openai_sdk_imported_directly():
    tree = ast.parse(open(financial_explanation.__file__).read())

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)

    # The M3.1 provider module import is required and allowed, but the
    # OpenAI SDK package itself must never be imported directly here.
    assert "openai" not in imported
    assert "financial_intelligence" not in "".join(imported)


def test_user_question_passed_through_unchanged_with_special_chars():
    question = 'Tell me about $1,234.56 & "quoted" + emoji \u20b9 \U0001f4b0'

    with _patched() as (_mock_context, _mock_system, mock_user, _mock_send):
        explain_financial_question("user-1", question)

    args, _ = mock_user.call_args
    assert args[1] == question


def test_context_not_mutated():
    import copy

    with _patched() as (mock_context, _mock_system, mock_user, mock_send):
        known = _sample_context()
        mock_context.return_value = known
        original = copy.deepcopy(known)

        mock_user.side_effect = lambda fc, q: fc["summary"]["total_income"]
        explain_financial_question("user-1", "Question?")

        assert known == original
