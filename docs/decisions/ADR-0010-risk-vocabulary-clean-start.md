---
id: ADR-0010
title: R, the dimensional law, SQS V1, and the bench vocabulary
type: adr
status: ratified
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-DATA, COMP-QMF-REGISTRY]
decisions: [DEC-0153, DEC-0154, DEC-0155]
sources: [DEC-0153, DEC-0154, DEC-0155, DEC-0076, DEC-0077, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 1y
---

# ADR-0010: R, the dimensional law, SQS V1, and the bench vocabulary

Date: 2026-08-20 (rewritten in place; supersedes the 2026-08-18 restart placeholder). status: ratified — corpus signed off by the operator 2026-08-21 (conditional go-ahead in the PRD session; the independent contradiction sweep passed); the underlying rulings AD-39..AD-41 are operator-ratified or corpus-closed under explicit operator delegation.

## Context

The 2026-08-18 restart preserved corrected vocabulary (R as pre-trade risk, SQS as Spread Quality Sensor) and killed the dimensionally broken FORM-0006, but left the formulas, the sensor, the stop-out semantics, and the bench state as gaps. The risk sitting closed GAP-0043, GAP-0044, and GAP-0045.

## Options considered

1. **Implement recovered FORM-0006** — dead (DEC-0077): dimensionally invalid; retained only as the dimensional suite's permanent negative test.
2. **Design SQS fresh** — the standing recommendation; reversed by operator ruling: the old ratio sensor is adopted as V1, with the caveat recorded verbatim. (DEC-0153)
3. **Keep the single overloaded B** — rejected: one symbol read as a count and as an R-depth at once was the defect that motivated the dimensional mandate. (DEC-0154)
4. **Typed three-face R, closed unit-kind vocabulary, ratio SQS, qualifying-loss bench** — selected. (DEC-0153, DEC-0154, DEC-0155)

## Decision

R is one relationship with three typed faces — `original_risk_distance` [price-delta], `original_risk_amount` [money(numeraire)], `r_multiple` [dimensionless] — frozen at admission; every position declares its planned full-loss price before it opens or admission refuses; a strategy with no planned loss point cannot trade in QMX (DEC-0154, elaborating L24/DEC-0076). The numeraire is USD system-wide; non-USD bindings refuse until a rate source is ratified. A closed unit-kind vocabulary (including the minted `value-factor(instrument, currency)`) types every variable and formula; a symbolic checker refuses mismatches; every formula ships an executable worked example; the replacement sizing shape is ratified in units only, with `r_unit_price = period_loss_budget ÷ seat_loss_run_allowance` superseding FORM-0004 and `seat_r_ceiling ≤ seat_loss_run_allowance` re-expressing FORM-0006 in pure R-space. The overloaded B splits into `bench_consecutive_loss_threshold` [count] and `seat_loss_run_allowance` [r_multiple]. SQS V1 is the corpus ratio sensor as a CT-16 configured producer — exact-rational score, declared session-window and baseline-statistic conditioning, a fingerprinted baseline input artifact with refit-series identity, hysteresis, outlier guard, conservative sentinel; every parameter configurable UI-editable with no spine value; the sensor computes, the transport carries, the Book door decides; V1 blocks only (DEC-0153). The bare word "stop-out" is banned: `venue_liquidation` is the broker's margin stop-out; the bench counts `qualifying_loss_exit`s — `realized_r ≤ −q`, q UI-editable defaulting to ~1R; breakevens never count and keep their own metric; the bench counter is a read-time fold over CT-29 exit records bounded by the binding epoch; seat state is `active | benched`, never a Book mode; alpha decay ships as evidence primitives only, and measurement publishes but never acts (DEC-0155).

## Consequences

CT-29 (exit record) and CT-32 (performance result) are minted; the registry gains the SQS, bench, window, ratchet, and paper-balance variables as configurable UI-editable entries whose recorded numbers are evidence, never ratified values; `bench_stopout_threshold` and `bench_reset_boundary` are superseded by the new bench vocabulary. The alpha-decay mathematics stays deferred — the evidence collection it needs starts now because it cannot be back-filled (L26). Dead formulas remain citable only as negative tests and diagnosis, never as live contracts.
