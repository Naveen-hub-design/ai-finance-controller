"""M4.5 Step 2: tests for the asynchronous AI controller Celery task.

The unit tests never require a real Redis broker: the Celery task is invoked
eagerly with ``run_ai_controller.apply(...)`` (in-process, synchronous), and
the external controller boundary is mocked at the task module boundary
(``tasks.ai_controller``).

Database isolation: the task builds its own app via ``create_app(Config)``,
so the tests point ``Config.SQLALCHEMY_DATABASE_URI`` at a disposable file
SQLite database that both the fixture app and the task's internal app share.
This keeps every M4.5 test off PostgreSQL and off any broker.

The worker ``tasks`` package lives in the worker build context. When this
module is executed somewhere that does not contain that source (e.g. the API
image alone), the task cannot be imported and these tests are skipped rather
than failing the untouched backend suite.
"""

import json
import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

try:  # requires the worker source to be on the python path
    import tasks.ai_controller as task_module
    from celery_app import celery as celery_app
except ImportError:
    task_module = None
    celery_app = None

from app import create_app
from app.config import Config
from app.extensions import db
from app.models import AuditRecord, User
from app.services.m4.contracts import (
    ControllerAction,
    FinancialControllerReport,
    SourceFacts,
)
from app.services.openai_provider import AIConfigurationError, AIProviderError

TASK_ID = str(uuid.uuid4())

NEEDS_WORKER = pytest.mark.skipif(
    task_module is None,
    reason="worker task module not available in this test environment",
)


class _RetryRequested(Exception):
    """Sentinel raised from a patched Task.retry to stop eager execution."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def task_env(tmp_path, monkeypatch):
    """An app whose DB (file SQLite) is shared by the fixture and the task."""
    uri = f"sqlite:///{tmp_path / 'task.db'}"
    monkeypatch.setattr(Config, "SQLALCHEMY_DATABASE_URI", uri)
    app = create_app(Config)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def _make_user(app) -> str:
    """Create a user and return its id, captured inside the app context."""
    with app.app_context():
        user = User(email=f"{uuid.uuid4()}@example.com", full_name="Task User")
        db.session.add(user)
        db.session.commit()
        user_id = str(user.id)
    return user_id


def _sample_source_facts() -> SourceFacts:
    return SourceFacts(
        money_values={"total_income": "10000.0000", "net_cash_flow": "4000.0000"},
        extra={"financial_context": {"summary": {"total_income": "10000.0000"}}},
    )


def _sample_report(user_id: str, intent: str) -> FinancialControllerReport:
    return FinancialControllerReport(
        user_id=user_id,
        intent=intent,
        source_facts=_sample_source_facts(),
        decision="Reduce high category spending.",
        rationale="Rent is 40% of income, above the threshold.",
        confidence=0.85,
        actions=[
            ControllerAction(
                action_type="REVIEW_BUDGET",
                description="Review the Food budget.",
                severity="medium",
                metadata={"category": "Food"},
            )
        ],
    )


def _decision_records(app, user_id):
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)
    with app.app_context():
        return AuditRecord.query.filter_by(user_id=user_id, kind="decision").all()


def _run_task(user_id, intent="q"):
    """Eagerly run the task and return its result."""
    return task_module.run_ai_controller.apply(
        args=[user_id, intent], task_id=TASK_ID
    ).get()


# ---------------------------------------------------------------------------
# 1. Success
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_success_calls_controller_once_and_creates_audit(task_env):
    user = _make_user(task_env)
    report = _sample_report(user, "Why did expenses rise?")

    with patch.object(
        task_module, "build_controller_report", return_value=report
    ) as mock_bcr:
        result = _run_task(user, "Why did expenses rise?")

    mock_bcr.assert_called_once()
    called_user, called_intent = mock_bcr.call_args.args
    assert str(called_user) == user
    assert called_intent == "Why did expenses rise?"

    assert isinstance(result, dict)
    assert result == report.to_dict()
    assert result["user_id"] == user

    records = _decision_records(task_env, user)
    assert len(records) == 1
    payload = records[0].payload
    assert payload["task_id"] == TASK_ID
    assert payload["intent"] == "Why did expenses rise?"
    assert payload["result"] == report.to_dict()


# ---------------------------------------------------------------------------
# 2. JSON serialization
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_result_is_plain_json_serializable(task_env):
    user = _make_user(task_env)
    report = _sample_report(user, "q")

    with patch.object(
        task_module, "build_controller_report", return_value=report
    ):
        result = _run_task(user, "q")

    assert isinstance(result, dict)
    assert isinstance(result["created_at"], str)
    assert isinstance(
        result["source_facts"]["money_values"]["total_income"], str
    )

    assert json.loads(json.dumps(result)) == result


# ---------------------------------------------------------------------------
# 3. Invalid UUID
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_invalid_uuid_fails_permanently_no_retry_no_audit(task_env):
    with patch.object(task_module, "build_controller_report") as mock_bcr:
        with pytest.raises(ValueError):
            task_module.run_ai_controller.apply(
                args=["not-a-uuid", "q"], task_id=TASK_ID
            ).get(propagate=True)

    mock_bcr.assert_not_called()
    assert _decision_records(task_env, uuid.uuid4()) == []


# ---------------------------------------------------------------------------
# 4. AI configuration error (no retry)
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_aiconfiguration_error_is_not_retried_and_no_audit(task_env):
    from celery import Task

    user = _make_user(task_env)

    def _fail_retry(*args, **kwargs):
        raise AssertionError("must not retry AIConfigurationError")

    with patch.object(
        task_module,
        "build_controller_report",
        side_effect=AIConfigurationError("not configured"),
    ):
        with patch.object(Task, "retry", side_effect=_fail_retry):
            with pytest.raises(AIConfigurationError):
                task_module.run_ai_controller.apply(
                    args=[user, "q"], task_id=TASK_ID
                ).get(propagate=True)

    assert _decision_records(task_env, user) == []


# ---------------------------------------------------------------------------
# 5. AI provider error (retry requested, no audit before success)
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_aiprovider_error_requests_retry_and_writes_no_audit(task_env):
    from celery import Task

    user = _make_user(task_env)
    retried = []

    def _capture_retry(exc=None, **kwargs):
        retried.append(exc)
        raise _RetryRequested()

    with patch.object(
        task_module,
        "build_controller_report",
        side_effect=AIProviderError("AI request failed"),
    ):
        with patch.object(Task, "retry", side_effect=_capture_retry):
            with pytest.raises(_RetryRequested):
                task_module.run_ai_controller.apply(
                    args=[user, "q"], task_id=TASK_ID
                ).get(propagate=True)

    assert len(retried) == 1
    assert isinstance(retried[0], AIProviderError)

    # Bounded exponential backoff is configured on the task.
    assert task_module.run_ai_controller.max_retries >= 1
    assert task_module.run_ai_controller.retry_backoff is True
    assert task_module.run_ai_controller.retry_backoff_max is not None

    # No audit record is written before a successful completion.
    assert _decision_records(task_env, user) == []


# ---------------------------------------------------------------------------
# 6. Database / audit failure
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_audit_database_error_rolls_back_and_cleansup(task_env):
    user = _make_user(task_env)
    report = _sample_report(user, "q")

    with patch.object(
        task_module, "build_controller_report", return_value=report
    ):
        with patch(
            "tasks.ai_controller.db.session.commit",
            side_effect=SQLAlchemyError("boom"),
        ):
            with pytest.raises(SQLAlchemyError):
                task_module.run_ai_controller.apply(
                    args=[user, "q"], task_id=TASK_ID
                ).get(propagate=True)

    # Rolled back: no partial audit record was left behind.
    assert _decision_records(task_env, user) == []


# ---------------------------------------------------------------------------
# 7. Flask app context exists during controller execution
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_controller_runs_inside_app_context(task_env):
    from flask import current_app

    user = _make_user(task_env)
    report = _sample_report(user, "q")
    observed = []

    def _capture(*args, **kwargs):
        # Accessing current_app.config requires an active app context.
        _ = current_app.config
        observed.append(True)
        return report

    with patch.object(task_module, "build_controller_report", side_effect=_capture):
        _run_task(user, "q")

    assert observed == [True]


# ---------------------------------------------------------------------------
# 8. Session cleanup in finally
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_session_is_removed_after_execution(task_env):
    user = _make_user(task_env)
    report = _sample_report(user, "q")
    removed = []

    with patch(
        "tasks.ai_controller.db.session.remove",
        side_effect=lambda: removed.append(True),
    ):
        with patch.object(
            task_module, "build_controller_report", return_value=report
        ):
            _run_task(user, "q")

    assert removed, "db.session.remove() must be called in finally"


# ---------------------------------------------------------------------------
# 9. Audit idempotency (same task id runs twice -> one audit record)
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_audit_idempotent_for_same_task_id(task_env):
    user = _make_user(task_env)
    report = _sample_report(user, "q")

    with patch.object(
        task_module, "build_controller_report", return_value=report
    ):
        task_module.run_ai_controller.apply(
            args=[user, "q"], task_id=TASK_ID
        ).get()
        task_module.run_ai_controller.apply(
            args=[user, "q"], task_id=TASK_ID
        ).get()

    assert len(_decision_records(task_env, user)) == 1


# ---------------------------------------------------------------------------
# 10. No financial mutation
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_task_does_not_mutate_financial_records(task_env):
    from app.models import Account, Budget, FinancialGoal, Transaction

    user = _make_user(task_env)
    report = _sample_report(user, "q")

    def _count(model):
        with task_env.app_context():
            return db.session.query(model).count()

    before = (
        _count(Transaction), _count(Account), _count(Budget), _count(FinancialGoal)
    )

    with patch.object(
        task_module, "build_controller_report", return_value=report
    ):
        _run_task(user, "q")

    after = (
        _count(Transaction), _count(Account), _count(Budget), _count(FinancialGoal)
    )
    assert after == before


# ---------------------------------------------------------------------------
# 11. Proposal-only actions are never executed
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_proposed_actions_are_not_executed(task_env):
    from app.models import Transaction

    user = _make_user(task_env)
    report = _sample_report(user, "q")
    assert report.actions, "expected proposed actions in fixture report"

    def _count_transactions():
        with task_env.app_context():
            return db.session.query(Transaction).count()

    transactions_before = _count_transactions()

    with patch.object(
        task_module, "build_controller_report", return_value=report
    ):
        result = _run_task(user, "q")

    # Proposed actions appear only as data; no financial record changed.
    assert result["actions"] == [a.to_dict() for a in report.actions]
    assert _count_transactions() == transactions_before


# ---------------------------------------------------------------------------
# 12. Task registration under the existing Celery app
# ---------------------------------------------------------------------------


@NEEDS_WORKER
def test_task_is_registered_with_expected_name():
    assert task_module.run_ai_controller is not None
    # Registered on the shared finance_worker app under the expected name.
    assert celery_app.tasks.get("run_ai_controller") is not None
