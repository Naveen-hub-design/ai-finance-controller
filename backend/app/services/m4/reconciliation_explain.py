"""AI assistance for unresolved reconciliation exceptions (Phase 6).

This service is strictly a *proposal / explanation* layer that runs AFTER the
deterministic reconciliation engine has classified an exception. It never:

- performs or overrides accounting correctness,
- modifies any ledger or statement record,
- marks an exception as resolved,
- executes any financial transaction,
- invents transaction data the engine did not observe.

Deterministic reconciliation (``run_reconciliation``) remains the source of
truth for matching. This module only explains *why* a line was not matched and
suggests a *possible* human resolution, based on the actual exception evidence
produced by the engine.

Like the M4 controller, the only AI touchpoint is
:func:`app.services.openai_provider.send_text_request`. The output is always
tagged as a proposal and never logged with sensitive contents.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..openai_provider import send_text_request
from .reconciliation_contracts import ReconciliationException

logger = logging.getLogger(__name__)

# A curated, factual label for each category so the prompt reports the
# deterministic evidence (never model-invented values).
_CATEGORY_FACTS = {
    "MISSING_LEDGER_RECORD": "No internal ledger entry was found near this "
    "statement line's amount, date, and description.",
    "AMOUNT_MISMATCH": "The internal ledger has an entry on the same date and "
    "description but with a different amount.",
    "DATE_MISMATCH": "The internal ledger has an entry with the same amount and "
    "description but on a different date.",
    "DUPLICATE_RECORD": "This statement line duplicates an exact ledger entry "
    "that was already matched by an identical line in the same batch.",
    "INVALID_RECORD": "The statement line carried an unparseable / invalid "
    "amount that cannot be compared to the ledger.",
    "OTHER": "The statement line could not be classified into a specific "
    "exception category.",
}


def _evidence_lines(exception: ReconciliationException) -> List[str]:
    """Build the factual, deterministic evidence block for the prompt.

    Only values the engine actually saw are included. If an amount/date cannot
    be rendered it is described as such; the model must not invent data.
    """
    lines = [
        f"Category: {exception.category}",
        f"Statement amount: {exception.statement_amount}",
        f"Statement date: {exception.statement_date}",
        f"Statement description: {exception.statement_description or '(none)'}",
        f"Engine reason: {exception.reason or '(none)'}",
    ]
    fact = _CATEGORY_FACTS.get(exception.category)
    if fact:
        lines.append(f"Deterministic evidence: {fact}")
    return lines


def build_explain_system_prompt() -> str:
    """System instructions constraining the model to a proposal-only reply."""
    return (
        "You are a financial operations assistant explaining reconciliation "
        "exceptions for internal finance staff. You may only reason from the "
        "deterministic evidence provided in the prompt. Never invent or "
        "assume transaction amounts, dates, references, or records that were "
        "not given. Your job is to explain why a line was not matched and "
        "suggest a possible next step for a HUMAN to review. Every suggestion "
        "is a proposal only; you never mark records resolved and never execute "
        "financial actions. Clearly separate the factual evidence from your "
        "suggestion."
    )


def build_explain_user_prompt(exception: ReconciliationException) -> str:
    """Build the user prompt containing only the actual exception evidence."""
    evidence = "\n".join(_evidence_lines(exception))
    return (
        "Here is a reconciliation exception that the deterministic engine "
        "could not resolve. Using ONLY this evidence, explain why it is likely "
        "unresolved and propose ONE possible next step a human reviewer could "
        "take (e.g. verify the amount against the bank, look for a missing "
        "ledger entry, or confirm a duplicate).\n\n"
        "Evidence:\n"
        f"{evidence}\n\n"
        "Important: distinguish, in your answer, what is FACT (from the "
        "evidence above) versus what is your SUGGESTION."
    )


def explain_reconciliation_exception(
    exception: ReconciliationException,
) -> Dict[str, Any]:
    """Return a proposal-only explanation for a single exception.

    Args:
        exception: A :class:`ReconciliationException` produced by the
            deterministic engine.

    Returns:
        A dict ``{"explanation", "suggested_resolution", "is_proposal"}``.

    Raises:
        Any error raised by ``send_text_request`` (e.g. the provider not being
        configured) is propagated unchanged so the caller can surface it.
    """
    system_prompt = build_explain_system_prompt()
    user_prompt = build_explain_user_prompt(exception)
    reply = send_text_request(user_prompt, system_prompt=system_prompt)
    return {
        "explanation": reply,
        "suggested_resolution": (
            "Verify the statement line against the bank, then either correct "
            "the internal ledger or confirm the line as a genuine exception. "
            "No record was modified by this AI suggestion."
        ),
        "is_proposal": True,
    }
