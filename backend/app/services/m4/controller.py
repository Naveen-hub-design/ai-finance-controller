"""M4.3 Step 1: The AI Finance Controller orchestration service.

This is the core AI feature of the project. It combines:

    1. M3 financial context (:func:`build_financial_context`)
    2. M4.1 deterministic risk intelligence (:func:`run_risk_intelligence`)
    3. M4.2 deterministic recommendations (:func:`run_recommendations`)
    4. M3 OpenAI provider (:func:`send_text_request`)

into an explainable :class:`FinancialControllerReport`.

Architectural rules honored here:

- **No OpenAI SDK import.** The only AI touchpoint is
  :func:`app.services.openai_provider.send_text_request`.
- **No financial calculations.** The controller never independently queries
  transactions or computes income, expenses, savings, budgets, category
  spending, balances, or risk scores. It only consumes the deterministic
  outputs of the existing M2/M4 services.
- **Deterministic numbers stay verbatim.** Monetary values are passed through
  as Decimal-safe strings and are never cast to float.
- **No sensitive logging.** Financial context, user questions, and AI answers
  are never logged.
- **Safe proposal-only actions.** Actions are proposals only and are never
  executed, approved, or treated as confirmed facts.
- **Error propagation.** Any failure in the context, risk, recommendation, or
  provider services propagates to the caller unchanged rather than being
  replaced by a fabricated financial answer.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Dict, List

from .contracts import (
    ControllerAction,
    FinancialControllerReport,
    SourceFacts,
)
from .controller_prompts import (
    build_controller_system_prompt,
    build_controller_user_prompt,
)
from ..financial_context import build_financial_context
from ..openai_provider import send_text_request
from .anomaly_detection import run_risk_intelligence
from .recommendations import run_recommendations

# Action types that, if proposed, must never be treated as executed. The
# controller only ever records these as proposals.
_EXECUTABLE_ACTION_TOKENS = (
    "execute",
    "transfer",
    "pay",
    "payment",
    "delete",
    "remove",
    "approve",
    "settle",
    "withdraw",
    "deposit",
    "send",
    "refund",
    "reconcile",
)

_UNSAFE_ACTION_CATEGORY = "PROPOSED_ACTION"

# Key under which model-derived cited facts are recorded so audit trail can
# reference them. The report contract has no dedicated field for cited facts,
# so they are carried inside the source facts' ``extra`` (which is not
# modified; a fresh SourceFacts is produced after parsing).
_CITED_FACTS_KEY = "cited_facts"


def _safe_intent_str(intent: Any) -> str:
    if intent is None:
        return ""
    return str(intent)


def _build_context(user_id) -> Dict[str, Any]:
    """Combine the three deterministic inputs into a controller context."""
    return {
        "financial_context": build_financial_context(user_id),
        "risk_signals": run_risk_intelligence(user_id),
        "recommendations": run_recommendations(user_id),
    }


def _collect_money_values(context: Dict[str, Any]) -> Dict[str, str]:
    """Gather deterministic monetary strings from the financial context.

    Monetary amounts remain strings; they are never cast to float.
    """
    summary = context.get("financial_context", {}).get("summary", {})
    money: Dict[str, str] = {}

    for key in (
        "total_income",
        "total_expenses",
        "net_cash_flow",
        "account_balance",
    ):
        value = summary.get(key)
        if isinstance(value, str):
            money[key] = value

    for idx, entry in enumerate(
        context.get("financial_context", {}).get("spending_by_category", [])
    ):
        if isinstance(entry, dict) and isinstance(entry.get("amount"), str):
            label = "category_spending_%d" % idx
            money[label] = entry["amount"]

    return money


def _build_source_facts(context: Dict[str, Any]) -> SourceFacts:
    """Construct source facts from the deterministic controller inputs."""
    return SourceFacts(
        money_values=_collect_money_values(context),
        extra={
            "financial_context": context.get("financial_context", {}),
            "risk_signals": context.get("risk_signals", []),
            "recommendations": context.get("recommendations", []),
        },
    )


def _extract_json(text: str) -> Dict[str, Any] | None:
    """Best-effort extraction of a JSON object from a model response.

    Tries in order:
    1. The entire response is valid JSON.
    2. A fenced JSON block (```json ... ``` or ``` ... ```).
    3. The first balanced top-level ``{ ... }`` object found in the text.

    Returns a parsed dict, or ``None`` if no JSON object could be extracted.
    """
    if not text:
        return None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except (ValueError, TypeError):
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            parsed = json.loads(fenced.group(1))
            if isinstance(parsed, dict):
                return parsed
        except (ValueError, TypeError):
            pass

    start = text.find("{")
    if start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            ch = text[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start : i + 1])
                        if isinstance(parsed, dict):
                            return parsed
                    except (ValueError, TypeError):
                        return None
    return None


def _clamp_confidence(value: Any) -> float:
    """Validate and constrain a confidence value to the closed interval
    [0.0, 1.0].

    Missing, non-numeric, NaN, and infinite values fall back to 0.0.
    """
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0

    if not math.isfinite(number):
        return 0.0
    if number < 0.0:
        return 0.0
    if number > 1.0:
        return 1.0
    return number


def _normalize_action(action: Any) -> ControllerAction | None:
    """Convert a proposed action dict into a safe ControllerAction.

    Returns ``None`` for non-dict or unusable entries. The action is always a
    *proposal*; it is never executed.
    """
    if not isinstance(action, dict):
        return None

    action_type = action.get("action_type")
    description = action.get("description", "")
    if not isinstance(action_type, str) or not action_type.strip():
        return None

    severity = action.get("severity", "info")
    if severity not in ("info", "low", "medium", "high"):
        severity = "info"

    metadata = action.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}

    action_type_upper = action_type.upper()
    is_executable = any(
        token.upper() in action_type_upper
        for token in _EXECUTABLE_ACTION_TOKENS
    )
    if is_executable:
        # Normalize into an explicit proposal-only category so the action is
        # clearly never treated as executed and never bypasses safety.
        metadata = dict(metadata)
        metadata["proposed_only"] = True
        metadata["original_action_type"] = action_type
        action_type = _UNSAFE_ACTION_CATEGORY

    return ControllerAction(
        action_type=action_type,
        description=str(description),
        severity=severity,
        metadata=metadata,
    )


def _parse_actions(raw: Any) -> List[ControllerAction]:
    """Parse the model's proposed actions into safe ControllerAction values."""
    if not isinstance(raw, list):
        return []

    actions: List[ControllerAction] = []
    for action in raw:
        parsed = _normalize_action(action)
        if parsed is not None:
            actions.append(parsed)
    return actions


def _parse_cited_facts(raw: Any) -> List[str]:
    """Extract a list of cited fact strings from the model response."""
    if not isinstance(raw, list):
        return []
    facts: List[str] = []
    for entry in raw:
        if isinstance(entry, str) and entry.strip():
            facts.append(entry)
    return facts


def _trim(text: Any, max_len: int = 512) -> str:
    if not isinstance(text, str):
        return ""
    cleaned = text.strip().strip("`").strip()
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned


def _with_cited_facts(
    source_facts: SourceFacts,
    cited_facts: List[str],
) -> SourceFacts:
    """Reconstruct source facts carrying the model-derived cited facts."""
    extra = dict(source_facts.extra)
    extra[_CITED_FACTS_KEY] = cited_facts
    return SourceFacts(
        money_values=dict(source_facts.money_values),
        extra=extra,
    )


def _report_from_parsed(
    user_id: str,
    intent: str,
    source_facts: SourceFacts,
    parsed: Dict[str, Any],
    raw_text: str,
) -> FinancialControllerReport:
    """Build a report from a successfully parsed model response."""
    decision = _trim(parsed.get("decision"))
    if not decision:
        # Fall back to a leading snippet of the raw text rather than crashing.
        decision = _trim(raw_text, max_len=512) or "No decision provided."

    rationale = _trim(parsed.get("rationale"), max_len=2048)
    if not rationale:
        rationale = _trim(raw_text, max_len=2048) or ""

    confidence = _clamp_confidence(parsed.get("confidence"))

    cited_facts = _parse_cited_facts(parsed.get("cited_facts"))

    return FinancialControllerReport(
        user_id=user_id,
        intent=intent,
        source_facts=_with_cited_facts(source_facts, cited_facts),
        decision=decision,
        rationale=rationale,
        confidence=confidence,
        actions=_parse_actions(parsed.get("actions")),
    )


def _report_from_text(
    user_id: str,
    intent: str,
    source_facts: SourceFacts,
    raw_text: str,
) -> FinancialControllerReport:
    """Fall back to a plain-text rationale when structured parsing fails.

    Never crashes; the decision/rationale are taken safely from the raw text.
    """
    text = _trim(raw_text, max_len=2048) or "No decision provided."
    return FinancialControllerReport(
        user_id=user_id,
        intent=intent,
        source_facts=source_facts,
        decision=text[:512] or "No decision provided.",
        rationale=text,
        confidence=0.0,
        actions=[],
    )


def build_controller_report(user_id, intent: str) -> FinancialControllerReport:
    """Orchestrate the AI finance controller and return an immutable report.

    Args:
        user_id: Identifier of the user (UUID, string, or equivalent).
        intent: The user's intent / question, treated as untrusted content.

    Returns:
        A :class:`FinancialControllerReport` compatible with
        ``to_dict()``.

    Raises:
        Any exception raised by the underlying context, risk, recommendation,
        or provider services is propagated unchanged.
    """
    user_id_str = str(user_id)
    intent_str = _safe_intent_str(intent)

    context = _build_context(user_id)
    source_facts = _build_source_facts(context)

    system_prompt = build_controller_system_prompt()
    user_prompt = build_controller_user_prompt(intent_str, context)

    raw_text = send_text_request(
        user_prompt,
        system_prompt=system_prompt,
    )

    parsed = _extract_json(raw_text)
    if parsed is None:
        return _report_from_text(
            user_id_str, intent_str, source_facts, raw_text
        )

    return _report_from_parsed(
        user_id_str, intent_str, source_facts, parsed, raw_text
    )
