"""M4 AI Finance Controller service layer.

This package is intentionally additive on top of the M2/M3 architecture.
It contains only lightweight, data-only contracts in this milestone; no
financial calculations, database access, AI calls, or business logic live
here yet.
"""

from .contracts import (
    ControllerAction,
    FinancialControllerReport,
    SourceFacts,
)

__all__ = [
    "ControllerAction",
    "FinancialControllerReport",
    "SourceFacts",
]
