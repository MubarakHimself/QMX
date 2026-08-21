---
id: ADR-0009
title: Book-level paper mode as a standing evidence state
type: adr
status: provisional
component: COMP-QMF-RISK
depends_on: [COMP-QMF-REGISTRY, COMP-QMF-DATA, COMP-QMF-VENUE]
decisions: [DEC-0149, DEC-0143]
sources: [DEC-0149, DEC-0070, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 1y
---

# ADR-0009: Book-level paper mode as a standing evidence state

Date: 2026-08-20 (rewritten in place; supersedes the 2026-08-18 recap-only placeholder). Status: provisional pending corpus-wide operator ratification; the underlying ruling AD-35 is operator-ratified ("You ratify" delegation with riders, 2026-08-20).

## Context

DEC-0070 recorded a Book-level paper direction whose direct operator wording was missing from the original export. The 2026-08-20 risk sitting confirmed it explicitly — "by default the paper is meant to be the Book" — and ratified the full mechanism as AD-35 (DEC-0149), closing GAP-0041.

## Options considered

1. **Parallel Bot paper twins** — dead (DEC-0069): duplicates Bot identity and Book attachment.
2. **Special blackout simulator** — dead (DEC-0071): ordinary recorders continue through blackouts.
3. **A paper target carrying no BMS** — a reviewer proposal, overruled by the operator's binding-chain ruling: an account without a BMS would be an account nothing constrains (filed tension, spine Deferred table).
4. **Paper as a Book-level standing evidence state with a paired BMS instance** — selected. (DEC-0149)

## Decision

Paper is a Book-level mode (DEC-0070 confirmed and subsumed by DEC-0149), expressed as a dated change of the Book's execution binding that mints a new binding epoch, never a new Book. Book modes are `LIVE | PAPER`; `BENCHED` is a bot-seat word only; per-seat routing lives on the seat record, so a Book may run live while one benched seat routes to the paired account. Paper is a standing evidence state: every trigger kind declares `routes-to-paper | blocks-paper` (market-risk controls block paper too; capital and authority controls route to paper); routing is never a way around a control — the blocked decision or suppressed action is journaled, because recording is not trading. One active paper-routing target per live binding; the per-intent `execution_target` is resolved once at intent mint and enters command identity, so one intent can never fire twice. Paper money is frozen evidence: a configurable UI-editable starting balance, never hand-adjusted; a reset mints an operator-signed paper epoch record; paper P&L never becomes Treasury cash and never buys a seat. Return to live is automatic only for clocked mechanical causes; anything touching real money takes an operator signature; paper performance never authorizes a return. Decay is judged in R under a declared cohort key with refusal on mismatch, and the decay-cohort read is an explicitly permitted cross-role read within `world = live`.

## Consequences

CT-24 is filled as the binding-transition contract and CT-28 carries the binding records; the paired demo account holds its own paired BMS instance linked by a typed pairing record (DEC-0143). The paper target is reconciled as its own binding and a silent paper outage alarms like a live one — a corrupted decay series is the failure paper mode exists to avoid. SCN-0006 (Book paper transition) is regenerated from the ratified mechanism.
