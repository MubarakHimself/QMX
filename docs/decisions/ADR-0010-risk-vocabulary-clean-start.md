---
id: ADR-0010
title: Risk vocabulary and mathematics restart
type: adr
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0072, DEC-0074, DEC-0076, DEC-0078, DEC-0092]
sources: [DEC-0072, DEC-0074, DEC-0075, DEC-0076, DEC-0078, DEC-0092, DEC-0094]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 1y
---

# ADR-0010: Risk vocabulary and mathematics restart

Date: 2026-08-18. Status: provisional pending operator ratification.

## Context

Recovered risk material contains semantic drift, overloaded symbols, unrecoverable formulas, and legacy mechanisms that conflict with corrected definitions.

## Options considered

1. **Implement recovered FORM-0006** — dead because it is dimensionally invalid under the corrected meaning of R (DEC-0077).
2. **Revive slot, DPR, or PRS machinery** — dead donor-only material (DEC-0079, DEC-0093).
3. **Preserve corrected vocabulary and redesign mathematics** — selected.

## Decision

News controls remain pair-scoped; SQS means Spread Quality Sensor; R uses `registry:original_risk_unit`; roster state, risk allocation, and any surviving legacy capital concept remain distinct. Future alpha-decay and benchmark mathematics start from current definitions. (DEC-0072, DEC-0074, DEC-0076, DEC-0078, DEC-0092)

## Consequences

SQS inputs, formulas, stop-out semantics, benchmark names, and alpha-decay evidence remain gaps. Dead formulas and namespaces may inform diagnosis but may never become live contracts.
