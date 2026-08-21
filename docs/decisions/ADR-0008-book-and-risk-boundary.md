---
id: ADR-0008
title: Book, BMS, binding chain, and the risk-control contracts
type: adr
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-CORE, COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-VENUE]
decisions: [DEC-0143, DEC-0144, DEC-0145, DEC-0146, DEC-0147, DEC-0148, DEC-0150, DEC-0151, DEC-0152, DEC-0156, DEC-0157, DEC-0158]
sources: [DEC-0143, DEC-0144, DEC-0145, DEC-0146, DEC-0147, DEC-0148, DEC-0150, DEC-0151, DEC-0152, DEC-0156, DEC-0157, DEC-0158, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 1y
---

# ADR-0008: Book, BMS, binding chain, and the risk-control contracts

Date: 2026-08-20 (rewritten in place; supersedes the 2026-08-18 GAP-defined placeholder). Status: provisional pending corpus-wide operator ratification; the underlying spine rulings AD-29..AD-38 are operator-ratified.

## Context

The risk sitting of 2026-08-20 closed GAP-0039, GAP-0040, GAP-0042, and GAP-0046. The long-standing DEC-0067 exit-ownership conflict and the DEC-0095 BMS-cardinality question are resolved; the reserved contracts CT-22..CT-25 are re-purposed and filled, and six new contracts CT-27..CT-32 are minted. Two standing operator rules bind everything here: corpus precedence for risk content (GitBook + trading-node documentation authoritative; QMX-discussion barred as a risk source — DEC-0156) and configurable-means-UI-editable (DEC-0157).

## Options considered

1. **BMS as a rulebook beside the Book** — the round-1 reading; reversed by the operator's own correction and the corpus-verified authority chain: the BMS, not the Book, connects to the account. (DEC-0143)
2. **One global BMS machine above all Books** — dead: the old single-global-BMS reading was a one-account assumption. (DEC-0143)
3. **Bots owning ordinary exit organs** — rejected for V1: repeated direct corrections place exits in Book territory; bots propose, the Book resolves. (DEC-0147, superseding DEC-0067)
4. **Account-facing BMS, one per account; Book owns exit policy; one control-window and one control-action contract** — selected. (DEC-0143, DEC-0147, DEC-0150, DEC-0152)

## Decision

The authority order is constitutional and verbatim: bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market — bot → book → BMS → operator (L36). One BMS instance per account serves many Books; a Book binds exactly one BMS at a time (dated, swappable); an instance never spans venues; the risk domain is the binding `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)`, aligned with the `(VenueId, account)` command stream. Three identities are minted apart: Book version (fp1), Book instance (BookInstanceId), and binding epoch (binding-record fingerprint). Templates are structured configuration artifacts with inline identity-bearing numbers, per-variable `ui-editable | uneditable` flags, and git-logic versioning on `branches-from` edges (DEC-0144). Entity journals are declared read-time projections over writer-scoped streams, with the venue join pinned in CT-25 (DEC-0145). Admission is three technical layers — linters, demo shakedown, one operator signature — with no probation and no paper-performance gate (DEC-0146). The Book owns exit policy; bots propose risk-monotonic exits through the CT-23 door; every close carries a typed reason; whole-trade attribution credits the opening bot (DEC-0147). `amend_protection` is the minted fifth venue command, never emulated by cancel-then-place; V1 dynamic SL/TP is the breakeven ratchet only (DEC-0148). The kill switch (global, sensor-fed, human de-escalates) and the kill line (per-Book capital floor, auto-flattening) are two different things; flatten authority is assigned (operator always; Book policy through pre-declared triggers; the protection authority where the node's severity policy says so; nobody else); the exit-preservation invariant is law (L39); same-tick priority is one BMS-declared rank table per command stream with collapse and conflict rules (DEC-0150, DEC-0151). One control-window contract serves news, daily dead zone, and session handover buffers — entries-only, live and paper alike, widths configurable with no spine value (DEC-0152).

## Architecture preflight — reuse-or-new

**Verdict: reuse `COMP-QMF-RISK`, `COMP-QMF-DATA`, `COMP-QMF-VENUE`, `COMP-QMF-REGISTRY`, `COMP-QMF-CORE`. No new component.** The inventory (`docs/architecture/dependencies.yaml`) was read against each candidate: `COMP-QMF-RISK` was reserved for exactly this domain — CT-22..CT-25 were placeholders awaiting these rulings, so filling them and adding CT-27..CT-32 is contract completion, not component creation; `COMP-QMF-DATA` carries the AD-31 projection machinery (AD-31 explicitly mints no new writer, stream taxonomy, or package edge); `COMP-QMF-VENUE` carries the fifth command and the CT-18 roster additions; `COMP-QMF-REGISTRY` carries the new record and edge kinds; `COMP-QMF-CORE` carries the shared nouns (Position, Order) and the unit-kind vocabulary. The dependency graph is unchanged — the risk sitting requests no edge; risk records reach registry and data through the composition root. Dead-list check: FORM-0006 stays dead (retained only as the dimensional suite's permanent negative test); the parallel-Bot paper twins (DEC-0069), the blackout simulator (DEC-0071), and DPR/PRS/slot machinery (DEC-0079, DEC-0093) stay dead and nothing here revives them.

## Consequences

CT-22, CT-23, CT-24, CT-25 are filled at version 1; CT-27..CT-32 are minted. The glossary's pre-ruling BMS definition and qmf-risk FM-8's several-BMS framing are superseded by DEC-0143 and regenerated. The 2026-08-18 paper-through-news ruling is superseded by DEC-0152. Blast radius: the qmf-risk spec is rewritten; qmf-data, qmf-venue, qmf-core, and qmf-registry specs absorb their cross-AD amendments; the glossary, constitution (L36..L39), registry variables, gap report, scenarios, and every lens doc citing GAP-0039..0046 are updated. All numeric values remain configurable UI-editable variables with recorded evidence and no ratified constants; admission-bar thresholds stay honestly blank and block live binding. Implementation authority is unchanged: factory pipeline only.
