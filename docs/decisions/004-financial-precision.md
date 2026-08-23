# ADR 004 — Financial Precision: Decimal and NUMERIC Only

- **Status:** Accepted (M01)
- **Deciders:** Project architecture
- **Date:** 2026-08-23

## Context

The AI Finance Controller stores and computes monetary values for B2B
merchants. Two common sources of financial corruption must be excluded by
design:

1. **Binary floating-point error.** IEEE-754 floats (`float` in Python,
   `FLOAT`/`DOUBLE` in PostgreSQL) cannot represent most decimal fractions
   exactly (e.g. `0.1 + 0.2 == 0.30000000000000004`). Rounding errors
   accumulate silently across ledger entries.
2. **LLM-generated arithmetic.** Language models approximate calculations and
   can hallucinate plausible-looking numbers. Their output is probabilistic
   text, not a deterministic computation, and must never be treated as an
   arithmetic authority for money.

## Decision

1. **Architectural rule (binding for all future milestones):**

   > Financial calculations must never depend on LLM-generated arithmetic.

   LLM output may summarize, explain, or classify — but any monetary figure
   that affects stored data, reports, or decisions must be computed
   deterministically by application code or SQL.

2. **Python layer:** all monetary arithmetic uses `decimal.Decimal`
   (never `float`). Rounding rules will be defined centrally when the first
   financial module lands.

3. **Database layer:** all monetary columns use PostgreSQL `NUMERIC`
   (e.g. `NUMERIC(19,4)`), never `FLOAT`/`DOUBLE PRECISION`.

4. **Boundary hygiene:** values crossing service boundaries (API JSON,
   Celery payloads) are serialized as strings containing exact decimal
   values, to avoid float round-trips.

Note: M01 implements no financial logic; this ADR establishes the rule that
later milestones must follow.

## Consequences

- Slightly more verbose code (`Decimal` construction from strings, explicit
  quantization) — accepted in exchange for correctness.
- PostgreSQL `NUMERIC` is slower than float types — irrelevant at expected
  transaction volumes and required for auditability.
- Review checklist for future PRs: no `float` for money, no `FLOAT`/`DOUBLE`
  columns, no LLM-produced numbers persisted as facts.
