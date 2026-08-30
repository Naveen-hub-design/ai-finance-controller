"""M7.5: async controller task ownership security tests.

These tests prove that a Celery ``task_id`` alone cannot authorize reading a
task result: each dispatched task is bound to its authenticated owner at
dispatch time (``ControllerTask``), and the status/result endpoint rejects any
request whose task id is unknown or owned by another user -- before ever
touching the Celery ``AsyncResult``.

Every scenario is a pure unit: Celery dispatch/result are mocked and the
ownership mapping lives in the in-memory SQLite test DB. No real Redis, worker,
or OpenAI involvement.
"""

import uuid
from datetime import timedelta
from unittest.mock import patch

from flask.testing import FlaskClient
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models import ControllerTask


def register_and_login(
    client: FlaskClient,
    email: str,
    password: str = "test-password-123",
) -> dict:
    """Register and log in a throwaway user; return the login body."""
    created = client.post(
        "/api/users",
        json={"email": email, "full_name": "M7.5 Test User", "password": password},
    )
    assert created.status_code == 201, created.get_json()
    login = client.post("/api/users/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.get_json()
    return login.get_json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_owned_task(client: FlaskClient, user_id: str, task_id: str) -> None:
    """Bind ``task_id`` to ``user_id`` in the ownership mapping."""
    with client.application.app_context():
        db.session.add(
            ControllerTask(
                task_id=uuid.UUID(task_id),
                user_id=uuid.UUID(user_id),
            )
        )
        db.session.commit()


def _owned_owner(client: FlaskClient, task_id: str):
    with client.application.app_context():
        return db.session.query(ControllerTask).filter_by(
            task_id=uuid.UUID(task_id)
        ).first()


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


def _register_pair(client: FlaskClient):
    """Register + log in users A and B; return (a, a_token, b, b_token)."""
    a = register_and_login(client, email="m75-a@example.com")
    b = register_and_login(client, email="m75-b@example.com")
    return (
        a["user"],
        a["access_token"],
        b["user"],
        b["access_token"],
    )


# ── Case 1 / 2 : submission ──────────────────────────────────────────────


def test_submit_own_task_is_accepted(client: FlaskClient) -> None:
    a, a_token, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())

    with patch(
        "app.routes.m4_controller_async.dispatch_ai_controller"
    ) as mock_dispatch:
        mock_dispatch.return_value.id = task_id
        r = client.post(
            f"/api/users/{a['id']}/ai-controller/async",
            json={"intent": "Save more"},
            headers=_headers(a_token),
        )

    assert r.status_code == 201
    assert r.get_json()["task_id"] == task_id
    assert r.get_json()["status"] == "PENDING"


def test_submit_for_another_user_is_403(client: FlaskClient) -> None:
    a, a_token, b, _ = _register_pair(client)

    with patch(
        "app.routes.m4_controller_async.dispatch_ai_controller"
    ) as mock_dispatch:
        r = client.post(
            f"/api/users/{b['id']}/ai-controller/async",
            json={"intent": "Save more"},
            headers=_headers(a_token),
        )

    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"
    mock_dispatch.assert_not_called()


# ── Case 3 / 4 / 5 : read authorization ──────────────────────────────────


def test_read_own_task_is_allowed(client: FlaskClient) -> None:
    a, a_token, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())
    _seed_owned_task(client, a["id"], task_id)

    with patch(
        "app.routes.m4_controller_async.task_result",
        return_value=_TaskResult("SUCCESS", result={"user_id": a["id"], "ok": True}),
    ):
        r = client.get(
            f"/api/users/{a['id']}/ai-controller/async/{task_id}",
            headers=_headers(a_token),
        )

    assert r.status_code == 200
    assert r.get_json()["status"] == "SUCCESS"
    assert r.get_json()["result"]["ok"] is True


def test_read_another_users_task_is_403(client: FlaskClient) -> None:
    a, a_token, b, _ = _register_pair(client)
    b_task = str(uuid.uuid4())
    _seed_owned_task(client, b["id"], b_task)

    with patch("app.routes.m4_controller_async.task_result") as mock_result:
        r = client.get(
            f"/api/users/{a['id']}/ai-controller/async/{b_task}",
            headers=_headers(a_token),
        )

    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"
    # Authorization must happen before any Celery result retrieval.
    mock_result.assert_not_called()


def test_wrong_url_owner_cannot_read_task(client: FlaskClient) -> None:
    a, a_token, b, b_token = _register_pair(client)
    a_task = str(uuid.uuid4())
    _seed_owned_task(client, a["id"], a_task)

    # User A's task, but requesting under User B's URL with B's valid JWT.
    with patch("app.routes.m4_controller_async.task_result") as mock_result:
        r = client.get(
            f"/api/users/{b['id']}/ai-controller/async/{a_task}",
            headers=_headers(b_token),
        )

    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"
    mock_result.assert_not_called()


# ── Case 6 : unknown task ────────────────────────────────────────────────


def test_unknown_task_is_safely_rejected(client: FlaskClient) -> None:
    a, a_token, _, _ = _register_pair(client)
    unknown = str(uuid.uuid4())

    with patch("app.routes.m4_controller_async.task_result") as mock_result:
        r = client.get(
            f"/api/users/{a['id']}/ai-controller/async/{unknown}",
            headers=_headers(a_token),
        )

    assert r.status_code == 403
    assert r.get_json()["error"] == "forbidden"
    mock_result.assert_not_called()


# ── Cases 7 / 8 / 9 : JWT 401 behavior ───────────────────────────────────


def test_missing_jwt_is_401(client: FlaskClient) -> None:
    a, _, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())
    _seed_owned_task(client, a["id"], task_id)

    r = client.get(f"/api/users/{a['id']}/ai-controller/async/{task_id}")
    assert r.status_code == 401
    assert r.get_json()["error"] == "authorization required"


def test_malformed_jwt_is_401(client: FlaskClient) -> None:
    a, _, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())

    r = client.get(
        f"/api/users/{a['id']}/ai-controller/async/{task_id}",
        headers=_headers("not-a-real-token"),
    )
    assert r.status_code == 401
    assert r.get_json()["error"] == "authorization required"


def test_tampered_jwt_is_401(client: FlaskClient, app) -> None:
    a, _, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())

    with app.app_context():
        valid = create_access_token(identity=str(a["id"]))
    header, payload, signature = valid.split(".")
    flip = "A" if payload[-1] != "A" else "B"
    tampered = f"{header}.{payload[:-1] + flip}.{signature}"

    r = client.get(
        f"/api/users/{a['id']}/ai-controller/async/{task_id}",
        headers=_headers(tampered),
    )
    assert r.status_code == 401
    assert r.get_json()["error"] == "authorization required"
    assert tampered not in r.get_data(as_text=True)


def test_expired_jwt_is_401(client: FlaskClient, app) -> None:
    a, _, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())

    with app.app_context():
        expired = create_access_token(
            identity=str(a["id"]),
            expires_delta=timedelta(seconds=-30),
        )

    r = client.get(
        f"/api/users/{a['id']}/ai-controller/async/{task_id}",
        headers=_headers(expired),
    )
    assert r.status_code == 401
    assert r.get_json()["error"] == "authorization token expired"


# ── Persistence / ownership-source-of-truth ──────────────────────────────


def test_ownership_recorded_with_authenticated_identity(client: FlaskClient) -> None:
    a, a_token, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())

    with patch(
        "app.routes.m4_controller_async.dispatch_ai_controller"
    ) as mock_dispatch:
        mock_dispatch.return_value.id = task_id
        client.post(
            f"/api/users/{a['id']}/ai-controller/async",
            json={"intent": "Why?"},
            headers=_headers(a_token),
        )

    owned = _owned_owner(client, task_id)
    assert owned is not None
    assert str(owned.user_id) == str(uuid.UUID(a["id"]))


def test_ownership_persistence_failure_does_not_expose_task(
    client: FlaskClient,
) -> None:
    from sqlalchemy.exc import SQLAlchemyError

    a, a_token, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())

    with patch(
        "app.routes.m4_controller_async.dispatch_ai_controller"
    ) as mock_dispatch:
        mock_dispatch.return_value.id = task_id
        with patch(
            "app.routes.m4_controller_async.db.session.commit",
            side_effect=SQLAlchemyError("ownership write failed"),
        ):
            r = client.post(
                f"/api/users/{a['id']}/ai-controller/async",
                json={"intent": "Why?"},
                headers=_headers(a_token),
            )

    # The task was dispatched but is not securely owned: the response is a
    # generic error and no task id is exposed, so the result stays unreadable.
    assert r.status_code == 500
    assert r.get_json()["error"] == "internal server error"
    assert "task_id" not in r.get_json()
    assert _owned_owner(client, task_id) is None


def test_status_requires_owned_record_not_just_url(client: FlaskClient) -> None:
    # Even with a valid JWT for the URL user, a task not in the ownership
    # mapping (e.g. present only in Redis) must be rejected before result access.
    a, a_token, _, _ = _register_pair(client)
    task_id = str(uuid.uuid4())

    with patch("app.routes.m4_controller_async.task_result") as mock_result:
        r = client.get(
            f"/api/users/{a['id']}/ai-controller/async/{task_id}",
            headers=_headers(a_token),
        )

    assert r.status_code == 403
    mock_result.assert_not_called()
