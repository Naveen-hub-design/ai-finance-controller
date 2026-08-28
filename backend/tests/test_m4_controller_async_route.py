"""M4.5 Step 3: tests for the asynchronous controller submission + status API.

These tests are pure units: they never contact a real Redis broker, a real
worker, or the OpenAI provider. The Celery producer (``send_task`` /
``AsyncResult``) and the database are mocked at the appropriate boundaries so
every scenario runs in isolation against the in-memory SQLite test app.

TODO (M7): security. These routes (like the rest of the API) are
unauthenticated. The next security milestone must bind a dispatched Celery
task to its owning authenticated user so callers can only observe their own
results.
"""

import os
import uuid
from unittest.mock import patch

from flask.testing import FlaskClient

from app import celery_client
from app.celery_client import dispatch_ai_controller


def _create_user(
    client: FlaskClient,
    email: str = "controller-async-route@example.com",
) -> dict:
    response = client.post(
        "/api/users",
        json={"email": email, "name": "Controller Async Route User"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _sample_success_result(user_id: str) -> dict:
    """A minimal but representative FinancialControllerReport.to_dict() body."""
    return {
        "user_id": user_id,
        "intent": "Why did expenses rise?",
        "source_facts": {
            "money_values": {"total_income": "10000.0000"},
            "extra": {},
        },
        "decision": "Reduce high category spending.",
        "rationale": "Rent is 40% of income, above the threshold.",
        "confidence": 0.85,
        "actions": [],
        "created_at": "2026-08-28T00:00:00+00:00",
    }


class _TaskResult:
    """AsyncResult stand-in that records whether ``.result`` was accessed."""

    def __init__(self, state, result=None):
        self.state = state
        self._result = result
        self.result_accessed = False

    @property
    def result(self):
        self.result_accessed = True
        return self._result


# ---------------------------------------------------------------------------
# Submission — success
# ---------------------------------------------------------------------------


def test_submission_returns_created(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())

    with patch(
        "app.routes.m4_controller_async.dispatch_ai_controller",
        return_value=_TaskResult("PENDING"),
    ) as mock_dispatch:
        mock_dispatch.return_value.id = task_id
        response = client.post(
            f"/api/users/{user['id']}/ai-controller/async",
            json={"intent": "Why did expenses rise?"},
        )

    assert response.status_code == 201
    data = response.get_json()
    assert data["task_id"] == task_id
    assert data["status"] == "PENDING"


def test_submission_returns_a_task_id(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())

    with patch(
        "app.routes.m4_controller_async.dispatch_ai_controller",
        return_value=_TaskResult("PENDING"),
    ) as mock_dispatch:
        mock_dispatch.return_value.id = task_id
        response = client.post(
            f"/api/users/{user['id']}/ai-controller/async",
            json={"intent": "Question?"},
        )

    data = response.get_json()
    assert data["task_id"] == task_id


def test_submission_returns_pending_status(client: FlaskClient) -> None:
    user = _create_user(client)

    with patch(
        "app.routes.m4_controller_async.dispatch_ai_controller",
        return_value=_TaskResult("PENDING"),
    ) as mock_dispatch:
        mock_dispatch.return_value.id = str(uuid.uuid4())
        response = client.post(
            f"/api/users/{user['id']}/ai-controller/async",
            json={"intent": "Question?"},
        )

    assert response.get_json()["status"] == "PENDING"


def test_dispatch_receives_user_id_and_intent(client: FlaskClient) -> None:
    user = _create_user(client)

    with patch(
        "app.routes.m4_controller_async.dispatch_ai_controller"
    ) as mock_dispatch:
        mock_dispatch.return_value.id = str(uuid.uuid4())
        client.post(
            f"/api/users/{user['id']}/ai-controller/async",
            json={"intent": "My exact question"},
        )

    args, _ = mock_dispatch.call_args
    assert str(args[0]) == user["id"]
    assert args[1] == "My exact question"


# ---------------------------------------------------------------------------
# Submission — validation
# ---------------------------------------------------------------------------


def test_submission_missing_json_body_returns_400(client: FlaskClient) -> None:
    with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller/async",
            data="",
            content_type="application/json",
        )
    assert response.status_code == 400


def test_submission_invalid_json_body_returns_400(client: FlaskClient) -> None:
    with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller/async",
            data="not json",
            content_type="application/json",
        )
    assert response.status_code == 400


def test_submission_missing_intent_returns_400(client: FlaskClient) -> None:
    with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller/async",
            json={},
        )
    assert response.status_code == 400


def test_submission_null_intent_returns_400(client: FlaskClient) -> None:
    with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller/async",
            json={"intent": None},
        )
    assert response.status_code == 400


def test_submission_non_string_intent_returns_400(client: FlaskClient) -> None:
    with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller/async",
            json={"intent": 123},
        )
    assert response.status_code == 400


def test_submission_empty_intent_returns_400(client: FlaskClient) -> None:
    with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller/async",
            json={"intent": ""},
        )
    assert response.status_code == 400


def test_submission_whitespace_intent_returns_400(client: FlaskClient) -> None:
    with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller/async",
            json={"intent": "   "},
        )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Submission — user lookup / errors
# ---------------------------------------------------------------------------


def test_submission_unknown_user_returns_404(client: FlaskClient) -> None:
    with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
        response = client.post(
            f"/api/users/{uuid.uuid4()}/ai-controller/async",
            json={"intent": "Question?"},
        )
    assert response.status_code == 404
    assert response.get_json()["error"] == "user not found"


def test_submission_user_lookup_error_returns_500(client: FlaskClient) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    with patch(
        "app.routes.m4_controller_async.db.session.get",
        side_effect=SQLAlchemyError("boom"),
    ):
        with patch("app.routes.m4_controller_async.dispatch_ai_controller"):
            response = client.post(
                f"/api/users/{uuid.uuid4()}/ai-controller/async",
                json={"intent": "Question?"},
            )

    assert response.status_code == 500
    assert response.get_json()["error"] == "internal server error"


# ---------------------------------------------------------------------------
# Status — terminal / intermediate states
# ---------------------------------------------------------------------------


def test_status_pending_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())
    fake = _TaskResult("PENDING")

    with patch("app.routes.m4_controller_async.task_result", return_value=fake):
        response = client.get(
            f"/api/users/{user['id']}/ai-controller/async/{task_id}"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["task_id"] == task_id
    assert data["status"] == "PENDING"


def test_status_retry_returns_200(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())
    fake = _TaskResult("RETRY")

    with patch("app.routes.m4_controller_async.task_result", return_value=fake):
        response = client.get(
            f"/api/users/{user['id']}/ai-controller/async/{task_id}"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["task_id"] == task_id
    assert data["status"] == "RETRY"


def test_status_success_returns_result(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())
    payload = _sample_success_result(user["id"])
    fake = _TaskResult("SUCCESS", result=payload)

    with patch("app.routes.m4_controller_async.task_result", return_value=fake):
        response = client.get(
            f"/api/users/{user['id']}/ai-controller/async/{task_id}"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "SUCCESS"
    assert data["result"] == payload


def test_status_failure_returns_safe_message(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())
    fake = _TaskResult("FAILURE", result=RuntimeError("super secret traceback"))

    with patch("app.routes.m4_controller_async.task_result", return_value=fake):
        response = client.get(
            f"/api/users/{user['id']}/ai-controller/async/{task_id}"
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "FAILURE"
    assert isinstance(data["message"], str)
    assert data["message"]
    assert "traceback" not in data["message"].lower()
    assert "secret" not in data["message"].lower()
    # The underlying exception internals must never be exposed.
    assert "RuntimeError" not in data["message"]


# ---------------------------------------------------------------------------
# Status — result isolation (only retrieved on SUCCESS)
# ---------------------------------------------------------------------------


def test_result_not_retrieved_for_pending(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())
    fake = _TaskResult("PENDING", result={"leak": True})

    with patch("app.routes.m4_controller_async.task_result", return_value=fake):
        response = client.get(
            f"/api/users/{user['id']}/ai-controller/async/{task_id}"
        )

    assert response.get_json()["status"] == "PENDING"
    assert "result" not in response.get_json()
    assert fake.result_accessed is False


def test_result_not_retrieved_for_retry(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())
    fake = _TaskResult("RETRY", result={"leak": True})

    with patch("app.routes.m4_controller_async.task_result", return_value=fake):
        response = client.get(
            f"/api/users/{user['id']}/ai-controller/async/{task_id}"
        )

    assert response.get_json()["status"] == "RETRY"
    assert "result" not in response.get_json()
    assert fake.result_accessed is False


def test_result_retrieved_only_for_success(client: FlaskClient) -> None:
    user = _create_user(client)
    task_id = str(uuid.uuid4())
    payload = _sample_success_result(user["id"])
    fake = _TaskResult("SUCCESS", result=payload)

    with patch("app.routes.m4_controller_async.task_result", return_value=fake):
        response = client.get(
            f"/api/users/{user['id']}/ai-controller/async/{task_id}"
        )

    assert fake.result_accessed is True
    assert response.get_json()["result"] == payload


# ---------------------------------------------------------------------------
# Client contract
# ---------------------------------------------------------------------------


def test_client_uses_registered_task_name() -> None:
    assert celery_client.RUN_AI_CONTROLLER_TASK == "run_ai_controller"


def test_dispatch_sends_to_registered_task_name() -> None:
    with patch("app.celery_client.celery_client.send_task") as mock_send:
        dispatch_ai_controller(str(uuid.uuid4()), "intent")

    mock_send.assert_called_once()
    name = mock_send.call_args.args[0]
    assert name == "run_ai_controller"


def test_dispatch_sends_expected_args() -> None:
    user_id = str(uuid.uuid4())
    with patch("app.celery_client.celery_client.send_task") as mock_send:
        dispatch_ai_controller(user_id, "my intent")

    _, kwargs = mock_send.call_args
    assert kwargs.get("args") == [str(user_id), "my intent"]


def test_client_broker_backend_matches_worker_defaults() -> None:
    # The client honours the same env vars with the same defaults the worker
    # uses, so an API-dispatched message reaches the worker's broker and its
    # result can be read back from the same backend.
    assert celery_client.BROKER_URL == os.environ.get(
        "CELERY_BROKER_URL", "redis://redis:6379/0"
    )
    assert celery_client.RESULT_BACKEND == os.environ.get(
        "CELERY_RESULT_BACKEND", "redis://redis:6379/1"
    )
    # The Celery app itself is wired to those resolved values.
    assert str(celery_client.celery_client.conf.broker_url) == (
        celery_client.BROKER_URL
    )
    assert str(celery_client.celery_client.conf.result_backend) == (
        celery_client.RESULT_BACKEND
    )
    # Same application name as the worker.
    assert celery_client.celery_client.main == "finance_worker"
