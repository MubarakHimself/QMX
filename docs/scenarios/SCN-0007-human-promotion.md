---
id: SCN-0007
title: An Agent Cannot Promote an Artifact to Live
type: scenario
status: provisional
component: COMP-QMF-REGISTRY
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0003, DEC-0004, DEC-0033, DEC-0038, DEC-0041, DEC-0108, DEC-0116, DEC-0121]
sources: [docs/constitution.md, docs/components/qmf-registry.md, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-08-gate-evidence.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0007: An Agent Cannot Promote an Artifact to Live

This scenario makes the human-only promotion boundary observable, now backed by a ratified promotion-record skeleton. The architecture sitting reserved a promotion-occurrence card kind: a human-only signer, a signed immutable record, and a mandatory plain-words summary field explicitly declared an identity field — so the signature attests the exact words the human read. Canonical identity is ratified (`fp1`), while the causality gate and attempt accounting remain deferred to the backtesting sitting. Execution status: **human-only boundary ratified as skeleton; causality gate deferred**. [DEC-0116]

## Given

A research artifact has a proposed `fp1` fingerprint and lineage, and an agent reports that its checks passed. The `fp1` recipe and its single qmf-core implementation are ratified (DEC-0108). The registry reserves a promotion-occurrence card kind whose V1 signing is the operator's recorded approval attesting the record's `fp1` string (reviewer identity plus instant), with no cryptographic dependency; the card is canonical and the journal's `promotion` event carries only the card's fingerprint plus `correlation_id`. An agent's research or recommendation is not an operator ruling. [DEC-0003] [DEC-0033] [DEC-0108] [DEC-0116]

`GAP(GAP-0016): Ratify the causality gate and evidence (deferred to the backtesting sitting, DEC-0121) — the promotion evidence checklist's causality slot stays unfilled; consequence knowingly accepted.`

`GAP(GAP-0017): Ratify attempt accounting (deferred to the backtesting sitting, DEC-0121).`

## When

The agent attempts to change the artifact from lab or research status into a live zone.

## Then

The status does not change and no live capability is granted. The attempt may be recorded as evidence, but only a human-controlled, signed promotion occurrence — the operator's recorded approval attesting the card's `fp1`, carrying the mandatory plain-words summary as an identity field — can authorize the boundary crossing. A typo fix to that summary mints a new record with a `supersedes` edge, because the signature attests the exact words read. [DEC-0003] [DEC-0004] [DEC-0041] [DEC-0116]

## Worked numbers

There is no ratified attempt budget or evidence-count threshold: attempt accounting is deferred to the backtesting sitting (DEC-0121), so `registry:registry_attempt_budget` remains null, and passing any number of agent-run checks cannot substitute for human authorization. The evidence checklist accretes from the data, backtesting, and risk sittings; the causality slot is not yet part of it.
