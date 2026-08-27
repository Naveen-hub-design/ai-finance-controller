"""Shared data-only contracts for the M4 AI Finance Controller.

These contracts are lightweight, typed structures that later M4 milestones
(anomaly/fraud intelligence, recommendations, the AI controller, audit
trail, and background processing) build their results on top of.

Design rules enforced here:

- **Data only.** No business logic, no financial calculations, no service
  or AI calls, no database access.
- **Standard library only.** No Flask, SQLAlchemy, OpenAI, or Celery imports;
  the module must remain importable in complete isolation.
- **Monetary values are strings.** Following the project convention
  (ADR 004 / ``financial_intelligence``), monetary source facts are
  represented as Decimal-safe strings, never floats, so precision is never
  lost. Nothing here converts them to float.
- **Serialization-friendly.** A deterministic ``to_dict`` makes the report
  easy to expose over HTTP and to persist in later milestones.

The contracts introduced here do not mutate financial records and know
nothing about the rest of the application.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

# Monetary values are carried as strings throughout M4 to preserve exact
# decimal precision without importing Decimal here. This mirrors the
# convention used by the M2 deterministic intelligence layer.
Money = str


@dataclass(frozen=True)
class SourceFacts:
    """Verified financial facts that ground a controller report.

    ``money_values`` holds the deterministic, Decimal-safe string amounts
    (e.g. total income, net cash flow, per-category spend) that the rest of
    the system computed. They are preserved verbatim and never cast to
    float.
    """

    money_values: Dict[str, Money] = field(default_factory=dict)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControllerAction:
    """A proposed, never-executed action surfaced by the controller.

    Actions are recommendations only. The controller never mutates financial
    records directly.
    """

    action_type: str
    description: str
    severity: str = "info"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FinancialControllerReport:
    """The top-level, immutable result of an AI finance controller run.

    It captures who the report is for (``user_id``), what the run was asked
    to do (``intent``), the deterministic facts it was grounded on
    (``source_facts``), the controller's decision and rationale, a
    confidence value, any proposed actions, and a creation timestamp.
    """

    user_id: str
    intent: str
    source_facts: SourceFacts
    decision: str
    rationale: str
    confidence: float
    actions: List[ControllerAction] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Serialize the datetime to ISO-8601 so the dict is JSON-friendly
        # and fully deterministic for persistence / HTTP.
        data["created_at"] = self.created_at.isoformat()
        return data


__all__ = [
    "ControllerAction",
    "FinancialControllerReport",
    "Money",
    "SourceFacts",
]
