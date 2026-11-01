"""M4 AI Finance Controller service layer.

This package is intentionally additive on top of the M2/M3 architecture.
It contains lightweight data contracts plus the deterministic finance-ops
agents (risk intelligence, recommendations, and multi-source reconciliation).
Contracts carry no financial calculations, database access, AI calls, or
business logic; the reconciliation service is data-aware by design but
deterministic and money-safe.
"""

from .contracts import (
    ControllerAction,
    FinancialControllerReport,
    SourceFacts,
)
from .reconciliation_contracts import (
    MatchRecord,
    ReconciliationException,
    ReconciliationReport,
)

__all__ = [
    "ControllerAction",
    "FinancialControllerReport",
    "MatchRecord",
    "ReconciliationException",
    "ReconciliationReport",
    "SourceFacts",
]
