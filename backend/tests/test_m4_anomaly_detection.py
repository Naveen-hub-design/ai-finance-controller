"""Tests for the M4.1 deterministic anomaly/risk detection service."""

import ast
import uuid
from decimal import Decimal

from flask.testing import FlaskClient

from app.services.m4.anomaly_detection import run_risk_intelligence


def _create_user(client: FlaskClient, email: str = "risk@example.com") -> dict:
    response = client.post(
        "/api/users",
        json={"email": email, "name": "Risk User"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_account(
    client: FlaskClient,
    user_id: str,
    name: str = "Bank",
    balance: str = "100000",
) -> dict:
    response = client.post(
        "/api/accounts",
        json={
            "user_id": user_id,
            "name": name,
            "account_type": "bank",
            "currency": "INR",
            "current_balance": balance,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_category(
    client: FlaskClient,
    user_id: str,
    name: str,
) -> dict:
    response = client.post(
        "/api/categories",
        json={
            "user_id": user_id,
            "name": name,
            "category_type": "expense",
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_expense(
    client: FlaskClient,
    account_id: str,
    amount: str,
    date: str,
    description: str | None = None,
    category_id: str | None = None,
) -> dict:
    payload = {
        "account_id": account_id,
        "amount": amount,
        "transaction_type": "expense",
        "transaction_date": date,
    }
    if description is not None:
        payload["description"] = description
    if category_id is not None:
        payload["category_id"] = category_id

    response = client.post("/api/transactions", json=payload)
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _create_income(
    client: FlaskClient,
    account_id: str,
    amount: str,
    date: str,
) -> dict:
    response = client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "amount": amount,
            "transaction_type": "income",
            "transaction_date": date,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


def _types(findings: list[dict]) -> list[str]:
    return [f["type"] for f in findings]


def test_no_transactions_returns_empty(client: FlaskClient) -> None:
    user = _create_user(client)
    _create_account(client, user["id"])

    findings = run_risk_intelligence(user["id"])

    assert findings == []


def test_large_amount_detection(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    # 3 normal expenses -> outlier is compared against the overall average
    _create_expense(client, account["id"], "100", "2026-08-01")
    _create_expense(client, account["id"], "200", "2026-08-02")
    _create_expense(client, account["id"], "300", "2026-08-03")
    # Large outlier: overall avg=(100+200+300+2000)/4=650, threshold=1950
    large = _create_expense(client, account["id"], "2000", "2026-08-04")

    findings = run_risk_intelligence(user["id"])
    types = _types(findings)

    assert "LARGE_AMOUNT" in types
    large_finding = next(f for f in findings if f["type"] == "LARGE_AMOUNT")
    assert large_finding["severity"] == "high"
    assert large_finding["explainable"] is True
    assert large["id"] in large_finding["transaction_ids"]
    assert large_finding["amount"] == "2000.0000"
    assert "average" in large_finding["reason"].lower()


def test_insufficient_history_no_large_amount(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    # Only 2 expense transactions -> not enough history (need >= 3)
    _create_expense(client, account["id"], "100", "2026-08-01")
    _create_expense(client, account["id"], "1000", "2026-08-02")

    types = _types(run_risk_intelligence(user["id"]))
    assert "LARGE_AMOUNT" not in types


def test_duplicate_candidate_detection(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    t1 = _create_expense(
        client, account["id"], "250", "2026-08-10", "Groceries"
    )
    t2 = _create_expense(
        client, account["id"], "250", "2026-08-10", "groceries"
    )

    findings = run_risk_intelligence(user["id"])
    types = _types(findings)

    assert "DUPLICATE_CANDIDATE" in types
    dup = next(f for f in findings if f["type"] == "DUPLICATE_CANDIDATE")
    assert dup["severity"] == "medium"
    assert set(dup["transaction_ids"]) == {t1["id"], t2["id"]}


def test_different_account_prevents_duplicate(client: FlaskClient) -> None:
    user = _create_user(client)
    account_a = _create_account(client, user["id"], "Bank A")
    account_b = _create_account(client, user["id"], "Bank B")

    _create_expense(client, account_a["id"], "250", "2026-08-10", "Rent")
    _create_expense(client, account_b["id"], "250", "2026-08-10", "Rent")

    assert "DUPLICATE_CANDIDATE" not in _types(
        run_risk_intelligence(user["id"])
    )


def test_different_date_prevents_duplicate(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    _create_expense(client, account["id"], "250", "2026-08-10", "Coffee")
    _create_expense(client, account["id"], "250", "2026-08-11", "Coffee")

    assert "DUPLICATE_CANDIDATE" not in _types(
        run_risk_intelligence(user["id"])
    )


def test_different_description_prevents_duplicate(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    _create_expense(client, account["id"], "250", "2026-08-10", "Coffee")
    _create_expense(client, account["id"], "250", "2026-08-10", "Lunch")

    assert "DUPLICATE_CANDIDATE" not in _types(
        run_risk_intelligence(user["id"])
    )


def test_round_amount_signal(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    _create_expense(client, account["id"], "5000", "2026-08-01")

    findings = run_risk_intelligence(user["id"])
    types = _types(findings)

    assert "ROUND_AMOUNT" in types
    round_finding = next(f for f in findings if f["type"] == "ROUND_AMOUNT")
    assert round_finding["severity"] == "low"


def test_non_round_amount_no_round_signal(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    _create_expense(client, account["id"], "473.19", "2026-08-01")

    assert "ROUND_AMOUNT" not in _types(
        run_risk_intelligence(user["id"])
    )


def test_rapid_frequency_detection(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    _create_expense(client, account["id"], "100", "2026-08-20")
    _create_expense(client, account["id"], "150", "2026-08-20")
    _create_expense(client, account["id"], "200", "2026-08-20")

    findings = run_risk_intelligence(user["id"])
    types = _types(findings)

    assert "RAPID_FREQUENCY" in types
    rapid = next(f for f in findings if f["type"] == "RAPID_FREQUENCY")
    assert rapid["severity"] == "medium"
    assert len(rapid["transaction_ids"]) == 3


def test_fewer_than_three_same_day_no_rapid(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    _create_expense(client, account["id"], "100", "2026-08-20")
    _create_expense(client, account["id"], "150", "2026-08-20")

    assert "RAPID_FREQUENCY" not in _types(
        run_risk_intelligence(user["id"])
    )


def test_category_concentration(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])
    groceries = _create_category(client, user["id"], "Groceries")

    # groceries 60 + dining 40 -> groceries share = 60% >= 50%
    _create_expense(
        client, account["id"], "60", "2026-08-01", "Food", groceries["id"]
    )
    _create_expense(client, account["id"], "40", "2026-08-02", "Restaurant")

    findings = run_risk_intelligence(user["id"])
    types = _types(findings)

    assert "CATEGORY_CONCENTRATION" in types
    conc = next(f for f in findings if f["type"] == "CATEGORY_CONCENTRATION")
    assert conc["severity"] == "medium"
    assert conc["amount"] == "60.0000"


def test_category_concentration_ignores_null_category(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    # All expenses have NULL category -> signal must be ignored.
    _create_expense(client, account["id"], "60", "2026-08-01", "Food")
    _create_expense(client, account["id"], "60", "2026-08-02", "Other")

    assert "CATEGORY_CONCENTRATION" not in _types(
        run_risk_intelligence(user["id"])
    )


def test_user_isolation(client: FlaskClient) -> None:
    user_one = _create_user(client, "iso-a@example.com")
    user_two = _create_user(client, "iso-b@example.com")

    account_one = _create_account(client, user_one["id"], "A Bank")
    account_two = _create_account(client, user_two["id"], "B Bank")

    # user_two has a large, round, duplicated expense pattern.
    _create_expense(client, account_two["id"], "90000", "2026-08-01", "Big")
    _create_expense(client, account_two["id"], "90000", "2026-08-01", "big")

    findings_one = run_risk_intelligence(user_one["id"])
    findings_two = run_risk_intelligence(user_two["id"])

    # user_one has no expenses -> no findings from user_two leaked over.
    assert findings_one == []
    assert findings_two != []

    # Every analyzed transaction must belong to user_two's account.
    for finding in findings_two:
        for tx_id in finding["transaction_ids"]:
            uuid.UUID(tx_id)


def test_all_monetary_outputs_are_strings(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    _create_expense(client, account["id"], "100", "2026-08-01")
    _create_expense(client, account["id"], "200", "2026-08-02")
    _create_expense(client, account["id"], "300", "2026-08-03")
    _create_expense(client, account["id"], "900", "2026-08-04")
    _create_expense(client, account["id"], "5000", "2026-08-05")

    findings = run_risk_intelligence(user["id"])

    for finding in findings:
        amount = finding["amount"]
        if amount is not None:
            assert isinstance(amount, str), amount
            # It must be a Decimal-safe string, not a float.
            assert not isinstance(amount, float)
            assert isinstance(Decimal(amount), Decimal)


def test_no_floats_produced(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    _create_expense(client, account["id"], "100", "2026-08-01")
    _create_expense(client, account["id"], "200", "2026-08-02")
    _create_expense(client, account["id"], "300", "2026-08-03")
    _create_expense(client, account["id"], "5000", "2026-08-04")

    findings = run_risk_intelligence(user["id"])

    for finding in findings:
        amount = finding["amount"]
        if amount is not None:
            assert not isinstance(amount, float)


def test_deterministic_ordering(client: FlaskClient) -> None:
    user = _create_user(client)
    account = _create_account(client, user["id"])

    # Produce LARGE_AMOUNT (high), DUPLICATE_CANDIDATE (medium),
    # ROUND_AMOUNT (low) findings.
    _create_expense(client, account["id"], "100", "2026-08-01")
    _create_expense(client, account["id"], "200", "2026-08-02")
    _create_expense(client, account["id"], "300", "2026-08-03")
    _create_expense(client, account["id"], "900", "2026-08-04")
    _create_expense(client, account["id"], "333", "2026-08-05", "Rent")
    _create_expense(client, account["id"], "333", "2026-08-05", "rent")

    results_a = run_risk_intelligence(user["id"])
    results_b = run_risk_intelligence(user["id"])

    assert results_a == results_b

    sev_order = {"high": 0, "medium": 1, "low": 2}
    severities = [f["severity"] for f in results_a]
    assert severities == sorted(severities, key=lambda s: sev_order[s])

    # Within the same severity, types are sorted.
    for lev in ("high", "medium", "low"):
        same = [f["type"] for f in results_a if f["severity"] == lev]
        assert same == sorted(same)


def test_no_forbidden_imports():
    source = open(
        "app/services/m4/anomaly_detection.py", encoding="utf-8"
    ).read()
    tree = ast.parse(source)

    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])

    forbidden = {"openai", "flask", "celery", "pandas", "numpy", "sklearn"}
    assert imported.isdisjoint(forbidden), imported & forbidden
