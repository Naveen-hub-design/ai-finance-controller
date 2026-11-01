"""Deterministic, idempotent demo-data seed for a realistic small/medium business.

Builds a coherent synthetic dataset graded into the existing demo business so
the live AI + deterministic financial features have real, non-round,
business-scoped data to reason over.

Design rules:

- **Deterministic.** No randomness, no current-time dependence. Every amount,
  date, and description is fixed so the dataset reproduces exactly.
- **Idempotent.** Each section short-circuits when its rows already exist, so
  re-running demo-login never duplicates data or interferes with existing
  records (including the reconciliation ``bank_statement`` batch).
- **Additive & safe.** Only creates missing categories, accounts, transactions,
  budgets, and goals. Never deletes or mutates existing project data.
- **Business-scoped.** Accounts, budgets, and goals are bound to the demo
  business; transactions are bound to its accounts.
- **AI-signal rich.** The set intentionally embeds patterns the AI and the
  deterministic risk/recommendation layer can observe: rising cloud spend, a
  marketing spike, a duplicate-looking vendor pair, an unusually large vendor
  payout, recurring subscriptions, a large one-time purchase, revenue growth,
  cash-flow pressure, and goal proximity.

This module contains no secrets and never touches the AI provider.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from ..extensions import db
from ..models import (
    Account,
    Budget,
    Business,
    BusinessMember,
    Category,
    FinancialGoal,
    Transaction,
    User,
)

# Year covered by the deterministic dataset.
_YEAR = 2026
# Month labels (1..11 => January..November).
_MONTHS = list(range(1, 12))


def _d(m: int, d: int) -> date:
    return date(_YEAR, m, d)


def _get_or_create(session, model, *, where, defaults):
    """Return an existing row matching ``where`` or create it with ``defaults``.

    ``where`` is a dict of column -> value used to locate an existing row.
    Returns ``(row, created: bool)``.
    """
    existing = session.scalar(select(model).filter_by(**where))
    if existing is not None:
        return existing, False
    row = model(**where, **defaults)
    session.add(row)
    session.flush()
    return row, True


def seed_demo_business(session=None) -> dict:
    """Populate the enterprise business with a realistic deterministic dataset.

    Locates the merchant by email (``merchant@demo.com``) and the enterprise
    business strictly through that merchant's OWNER membership (``Apex Global Technologies``
    or ``Demo Corp``), then adds any missing categories, accounts, transactions, budgets,
    and goals. Safe to call repeatedly (idempotent).

    Returns a dict reporting how many of each row kind were newly created.
    """
    session = session or db.session
    counts = {"categories": 0, "accounts": 0, "transactions": 0, "budgets": 0, "goals": 0}

    merchant = session.scalar(select(User).where(User.email == "merchant@demo.com"))
    if merchant is None:
        return counts
    business = session.scalar(
        select(Business)
        .join(BusinessMember, BusinessMember.business_id == Business.id)
        .where(
            BusinessMember.user_id == merchant.id,
            BusinessMember.role == "OWNER",
            Business.name.in_(["Apex Global Technologies", "Demo Corp"]),
        )
        .order_by(Business.created_at.asc())
        .limit(1)
    )
    if business is None:
        return counts

    # ---------------------------------------------------------------- categories
    category_specs = [
        ("Revenue", "income"),
        ("Sales Revenue", "income"),
        ("Payroll", "expense"),
        ("Salary", "expense"),
        ("Cloud Infrastructure", "expense"),
        ("Software", "expense"),
        ("Software & SaaS", "expense"),
        ("Marketing", "expense"),
        ("Office", "expense"),
        ("Office Rent", "expense"),
        ("Office Supplies", "expense"),
        ("Electricity", "expense"),
        ("Internet", "expense"),
        ("Travel", "expense"),
        ("Food & Meals", "expense"),
        ("Equipment", "expense"),
        ("Utilities", "expense"),
        ("Bank Fees", "expense"),
        ("Vendor Payments", "expense"),
        ("Taxes", "expense"),
        ("Subscriptions", "expense"),
        ("Insurance", "expense"),
        ("Loan Payment", "expense"),
        ("Miscellaneous", "expense"),
    ]
    cats = {}
    for name, ctype in category_specs:
        cat, created = _get_or_create(
            session,
            Category,
            where={"user_id": merchant.id, "name": name},
            defaults={"category_type": ctype},
        )
        if created:
            counts["categories"] += 1
        cats[name.lower()] = cat
    # Also map any legacy categories (created by the earlier demo seed) so the
    # transaction batch stays categorized coherently when they already exist.
    for legacy_name in ("Rent", "Office Supplies", "Salary"):
        legacy = session.scalar(
            select(Category).where(
                Category.user_id == merchant.id,
                Category.name == legacy_name,
            )
        )
        if legacy is not None:
            cats[legacy_name.lower()] = legacy
    session.flush()

    # ---------------------------------------------------------------- accounts
    # Account types must be valid per 001_core_financial_model constraint:
    # bank, cash, credit_card, investment, loan, other (savings/payment are NOT valid).
    account_specs = [
        ("Operating Bank", "bank", "842650.75"),
        ("Business Savings", "bank", "315420.20"),
        ("Corporate Card", "credit_card", "-86340.50"),
        ("Payment Gateway", "other", "128450.00"),
    ]
    accounts = {}
    for name, atype, balance in account_specs:
        acc, created = _get_or_create(
            session,
            Account,
            where={"user_id": merchant.id, "business_id": business.id, "name": name},
            defaults={
                "account_type": atype,
                "currency": "INR",
                "current_balance": Decimal(balance),
            },
        )
        if created:
            counts["accounts"] += 1
        accounts[name] = acc
    session.flush()

    # ------------------------------------------------------------ transactions
    # Idempotency guard: check whether transactions have already been seeded.
    seeded_txn = session.scalar(
        select(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(
            Account.business_id == business.id,
            Transaction.transaction_date >= date(_YEAR, 1, 1),
            Transaction.transaction_date <= date(_YEAR, 11, 30),
        )
        .limit(1)
    )
    if seeded_txn is None:
        batch = _build_transactions(cats, accounts)
        for account, category, ttype, amount, desc, when in batch:
            session.add(
                Transaction(
                    account_id=account.id,
                    category_id=category.id if category else None,
                    amount=amount,
                    transaction_type=ttype,
                    description=desc,
                    transaction_date=when,
                )
            )
        session.flush()
        counts["transactions"] = len(batch)

    # ---------------------------------------------------------------- budgets
    # Monthly budgets over June 2026 (for test compatibility) and current November 2026.
    budget_specs = [
        ("Marketing", "45000.00"),
        ("Cloud Infrastructure", "85000.00"),
        ("Payroll", "160000.00"),
        ("Software", "35000.00"),
        ("Office", "20000.00"),
        ("Travel", "25000.00"),
    ]
    for month_start, month_end in [
        (date(_YEAR, 6, 1), date(_YEAR, 6, 30)),
        (date(_YEAR, 11, 1), date(_YEAR, 11, 30)),
    ]:
        for cname, amount in budget_specs:
            cat = cats.get(cname.lower())
            if cat is None:
                continue
            _, created = _get_or_create(
                session,
                Budget,
                where={
                    "user_id": merchant.id,
                    "business_id": business.id,
                    "category_id": cat.id,
                    "period": "monthly",
                    "start_date": month_start,
                    "end_date": month_end,
                },
                defaults={"amount": Decimal(amount)},
            )
            if created:
                counts["budgets"] += 1

    # ---------------------------------------------------------------- goals
    goal_specs = [
        ("Emergency Cash Reserve", "600000.00", "520000.00", date(_YEAR, 12, 31), "active"),
        ("Tax Reserve", "450000.00", "390000.00", date(_YEAR + 1, 3, 31), "active"),
        ("Equipment Purchase", "600000.00", "580000.00", date(_YEAR, 11, 30), "active"),
        ("Expansion Fund", "1500000.00", "850000.00", date(_YEAR + 1, 6, 30), "active"),
    ]
    for name, target, current, target_date, status in goal_specs:
        _, created = _get_or_create(
            session,
            FinancialGoal,
            where={"user_id": merchant.id, "business_id": business.id, "name": name},
            defaults={
                "target_amount": Decimal(target),
                "current_amount": Decimal(current),
                "target_date": target_date,
                "status": status,
            },
        )
        if created:
            counts["goals"] += 1

    session.commit()
    return counts


def _build_transactions(cats, accounts):
    """Return the deterministic Jan-Nov transaction tuples.

    Each tuple is ``(account, category, type, amount, description, date)``.
    ``cats`` is keyed by lowercase category name; ``accounts`` by account name.
    Falls back to the 'Office' category for any referenced category that is
    absent (never crashes the seed).
    """
    def cat(name):
        return cats.get(name.lower())

    rev = cat("Revenue")
    payroll = cat("Payroll")
    cloud = cat("Cloud Infrastructure")
    software = cat("Software")
    marketing = cat("Marketing")
    office = cat("Office")
    travel = cat("Travel")
    util = cat("Utilities")
    bank_fees = cat("Bank Fees")
    vendors = cat("Vendor Payments")
    taxes = cat("Taxes")
    subs = cat("Subscriptions")
    rent = cat("Rent") or office
    office_supplies = cat("Office Supplies") or office

    operating = accounts["Operating Bank"]
    savings = accounts["Business Savings"]
    card = accounts["Corporate Card"]
    gateway = accounts["Payment Gateway"]

    txs = []
    add = txs.append

    for m in _MONTHS:
        day3 = 3

        # Revenue (growing): 3-4 client invoices per month.
        rev_rows = {
            1: [(80000, "Acme Corp - invoice"), (90000, "Beta Labs - invoice"), (70000, "Globex - retainer")],
            2: [(90000, "Acme Corp - invoice"), (95000, "Beta Labs - invoice"), (75000, "Globex - retainer")],
            3: [(95000, "Acme Corp - invoice"), (90000, "Beta Labs - invoice"), (90000, "Initech - invoice")],
            4: [(100000, "Acme Corp - invoice"), (100000, "Beta Labs - invoice"), (100000, "Initech - invoice")],
            5: [(105000, "Acme Corp - invoice"), (105000, "Beta Labs - invoice"), (110000, "Initech - invoice")],
            6: [(110000, "Acme Corp - invoice"), (115000, "Beta Labs - invoice"), (115000, "Initech - invoice")],
            7: [(120000, "Acme Corp - invoice"), (120000, "Beta Labs - invoice"), (115000, "Initech - invoice")],
            8: [(125000, "Acme Corp - invoice"), (130000, "Beta Labs - invoice"), (120000, "Initech - invoice"), (85000, "Vertex AI - deployment fee")],
            9: [(130000, "Acme Corp - invoice"), (135000, "Beta Labs - invoice"), (125000, "Initech - invoice"), (90000, "Vertex AI - deployment fee")],
            10: [(145000, "Acme Corp - Q4 invoice"), (140000, "Beta Labs - consumption"), (135000, "Initech - ARR renewal"), (95000, "Vertex AI - license")],
            11: [(150000, "Stripe Payout - Enterprise ARR"), (155000, "Beta Labs - monthly usage"), (140000, "Initech - quarterly fee")],
        }[m]
        for i, (amount, desc) in enumerate(rev_rows):
            add((operating, rev, "income", Decimal(amount), desc, _d(m, day3 + i)))

        # Payroll / bonus.
        add((operating, payroll, "expense", Decimal("45000"), "Payroll - senior engineer", _d(m, 5)))
        add((operating, payroll, "expense", Decimal("40000"), "Payroll - product manager", _d(m, 5)))
        add((operating, payroll, "expense", Decimal("35000"), "Payroll - support lead", _d(m, 5)))
        if m in (6, 10):
            add((operating, payroll, "expense", Decimal("15000"), "Payroll - performance bonus", _d(m, 5)))

        # Cloud Infrastructure (rising).
        cloud_rows = {
            1: [(17000, "AWS - compute"), (15000, "AWS - storage")],
            2: [(18000, "AWS - compute"), (16000, "AWS - storage")],
            3: [(19000, "AWS - compute"), (17000, "AWS - storage")],
            4: [(30000, "AWS - kubernetes cluster"), (28000, "AWS - data pipeline")],
            5: [(31000, "AWS - kubernetes cluster"), (30000, "AWS - data pipeline")],
            6: [(33000, "AWS - kubernetes cluster"), (31000, "AWS - data pipeline")],
            7: [(34000, "AWS - kubernetes cluster"), (32000, "AWS - data pipeline")],
            8: [(36000, "AWS - kubernetes cluster"), (33000, "AWS - data pipeline")],
            9: [(38000, "AWS - kubernetes cluster"), (35000, "AWS - data pipeline")],
            10: [(41000, "AWS - kubernetes cluster"), (37000, "AWS - data pipeline")],
            11: [(43000, "AWS - kubernetes cluster"), (39000, "AWS - data pipeline")],
        }[m]
        for i, (amount, desc) in enumerate(cloud_rows):
            add((card, cloud, "expense", Decimal(amount), desc, _d(m, 8 + i)))

        # Marketing.
        mkt_rows = {
            1: [(18000, "Google Ads - campaign")],
            2: [(22000, "Google Ads - campaign")],
            3: [(32000, "Google Ads - product launch"), (23000, "Meta Ads - product launch")],
            4: [(25000, "Google Ads - campaign")],
            5: [(26000, "Google Ads - campaign")],
            6: [(28000, "Google Ads - campaign")],
            7: [(28000, "Google Ads - enterprise campaign")],
            8: [(30000, "Google Ads - enterprise campaign"), (18000, "LinkedIn B2B Sponsored Content")],
            9: [(32000, "Google Ads - enterprise campaign"), (20000, "LinkedIn B2B Sponsored Content")],
            10: [(36000, "Google Ads - Q4 campaign"), (22000, "LinkedIn B2B Sponsored Content")],
            11: [(38000, "Google Ads - Q4 campaign"), (24000, "LinkedIn B2B Sponsored Content")],
        }[m]
        for i, (amount, desc) in enumerate(mkt_rows):
            add((operating, marketing, "expense", Decimal(amount), desc, _d(m, 12 + i)))

        # Software subscriptions (recurring).
        software_tools = [
            ("Figma - seats", 3000),
            ("Linear - seats", 2000),
            ("Notion - workspace", 1500),
            ("Slack - business", 4500),
            ("Github - teams", 8000),
            ("Jira - cloud", 6000),
            ("Datadog - Observability", 7500),
        ]
        for i, (desc, amount) in enumerate(software_tools):
            add((operating, software, "expense", Decimal(amount), desc, _d(m, 15 + (i % 10))))

        # Other subscriptions.
        add((card, subs, "expense", Decimal("1200"), "Zoom - business", _d(m, 4)))
        add((card, subs, "expense", Decimal("1800"), "Dropbox - business", _d(m, 6)))

        # Utilities.
        add((operating, util, "expense", Decimal("5200"), "Electricity - office", _d(m, 9)))
        add((operating, util, "expense", Decimal("1350"), "Internet - office", _d(m, 9)))

        # Rent / Office.
        add((operating, rent, "expense", Decimal("30000"), "Office rent", _d(m, 2)))
        add((operating, office, "expense", Decimal("2200"), "Office supplies - misc", _d(m, 11)))
        add((operating, office_supplies, "expense", Decimal("1800"), "Office stationery", _d(m, 11)))

        # Travel.
        travel_amounts = {1: 14000, 2: 6000, 3: 21000, 4: 8000, 5: 16000, 6: 9000, 7: 12000, 8: 15000, 9: 18000, 10: 24000, 11: 8500}
        add((operating, travel, "expense", Decimal(travel_amounts[m]), "Business travel - flights & hotels", _d(m, 17)))

        # Bank fees.
        add((operating, bank_fees, "expense", Decimal("450"), "Bank service fee", _d(m, 20)))
        add((gateway, bank_fees, "expense", Decimal("612"), "Payment gateway fee", _d(m, 20)))

        # Taxes.
        taxes_amounts = {1: 40000, 2: 0, 3: 45000, 4: 0, 5: 0, 6: 52000, 7: 0, 8: 0, 9: 60000, 10: 0, 11: 0}
        if taxes_amounts[m]:
            add((operating, taxes, "expense", Decimal(taxes_amounts[m]), "GST / income-tax provisional", _d(m, 22)))

    # Vendor payments: regular + distinctive AI-signal rows.
    vendor_rows = [
        ("Northwind Logistics", "36000", _d(1, 16)),
        ("Southgate Supply", "29500", _d(2, 14)),
        ("Brightline Media", "18000", _d(2, 21)),
        ("Helix Components", "48000", _d(3, 18)),
        ("Acme Logistics", "48750", _d(4, 14)),
        ("Acme Logistics", "48750", _d(4, 14)),        # duplicate-looking pair
        ("Beckman Fabrication", "52000", _d(5, 19)),
        ("Northwind Consulting", "380000", _d(5, 26)),  # unusual large payout
        ("Brightline Media", "20000", _d(6, 10)),
        ("Helix Components", "51000", _d(6, 22)),
        ("Brightline Media", "22000", _d(7, 18)),
        ("Helix Components", "53000", _d(8, 20)),
        ("Northwind Logistics", "39000", _d(9, 15)),
        ("Datadog Enterprise", "46000", _d(10, 12)),
        ("Deel Global Payroll Contractor", "64000", _d(10, 25)),
        ("Snowflake Data Cloud", "48000", _d(10, 28)),
        ("Stripe Merchant Settlement", "295000", _d(11, 1)),
    ]
    for desc, amount, when in vendor_rows:
        add((operating, vendors, "expense", Decimal(amount), desc, when))

    # One large one-time expense: equipment purchase (April).
    add((savings, office, "expense", Decimal("220000"), "Office equipment - workstations & monitors", _d(4, 20)))

    return txs
