---
id: SCN-0007
title: An Agent Cannot Promote an Artifact to Live
type: scenario
status: provisional
component: COMP-QMF-REGISTRY
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0003, DEC-0004, DEC-0033, DEC-0038, DEC-0041, DEC-0108, DEC-0116, DEC-0121, DEC-0146, DEC-0155, DEC-0158]
sources: [docs/constitution.md, docs/components/qmf-registry.md, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-08-gate-evidence.yaml, _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md]
generated: 2026-08-18
verified: 2026-08-20
stale_after: 30d
---

# SCN-0007: An Agent Cannot Promote an Artifact to Live

This scenario makes the human-only promotion boundary observable, now backed by a ratified promotion-record skeleton. The architecture sitting reserved a promotion-occurrence card kind: a human-only signer, a signed immutable record, and a mandatory plain-words summary field explicitly declared an identity field — so the signature attests the exact words the human read. Canonical identity is ratified (`fp1`), the promotion card now carries the Book-definition fingerprint as an identity field, and the risk slot of the evidence checklist has landed — while the causality gate and attempt accounting remain deferred to the backtesting sitting. Execution status: **human-only boundary ratified as skeleton; risk slot landed; causality gate deferred**. [DEC-0116] [DEC-0158] [DEC-0146]

## Given

A research artifact has a proposed `fp1` fingerprint and lineage, and an agent reports that its checks passed. The `fp1` recipe and its single qmf-core implementation are ratified (DEC-0108). The registry reserves a promotion-occurrence card kind whose V1 signing is the operator's recorded approval attesting the record's `fp1` string (reviewer identity plus instant), with no cryptographic dependency; the card is canonical and the journal's `promotion` event carries only the card's fingerprint plus `correlation_id`. The card additionally carries the **Book-definition (or BMS-definition) fingerprint as an identity field**, so a signature can never attest a superseded template. The **risk slot of the promotion evidence checklist has landed:** it is the three-layer admission packet — Layer 1 registration linters (completeness, a unit on every parameter, exact-rational or scaled-integer numbers, worked-example arithmetic recomputed by invoking the cited producer contracts, control-rank uniqueness, the prediction linter as a pending slot), Layer 2 a technical demo/paper shakedown, and Layer 3 one operator signature on one assembled page — plus the CT-32 performance evidence, with **no trial period, probation window, or paper-performance gate** and no paper role permitted to gate live money. An agent's research or recommendation is not an operator ruling. [DEC-0003] [DEC-0033] [DEC-0108] [DEC-0116] [DEC-0158] [DEC-0146] [DEC-0155]

`GAP(GAP-0016): Ratify the causality gate and evidence (deferred to the backtesting sitting, DEC-0121) — the promotion evidence checklist's causality slot stays unfilled; consequence knowingly accepted.`

`GAP(GAP-0017): Ratify attempt accounting (deferred to the backtesting sitting, DEC-0121).`

## When

The agent attempts to change the artifact from lab or research status into a live zone.

## Then

The status does not change and no live capability is granted. The attempt may be recorded as evidence, but only a human-controlled, signed promotion occurrence — the operator's recorded approval attesting the card's `fp1`, carrying the mandatory plain-words summary **and the Book-definition (or BMS-definition) fingerprint** as identity fields — can authorize the boundary crossing. Because the attested template fingerprint is an identity field, the signature can never attest a superseded template; a typo fix to the summary or a change to the attested fingerprint mints a new record with a `supersedes` edge, since the signature attests the exact words read against the exact template. [DEC-0003] [DEC-0004] [DEC-0041] [DEC-0116] [DEC-0158]

## Worked numbers

There is no ratified attempt budget or evidence-count threshold: attempt accounting is deferred to the backtesting sitting (DEC-0121), so `registry:registry_attempt_budget` remains null, and passing any number of agent-run checks cannot substitute for human authorization. The evidence checklist accretes from the data, backtesting, and risk sittings; the risk slot has landed (the three-layer admission packet plus CT-32 performance evidence), while the causality slot (GAP-0016) and attempt accounting (GAP-0017) remain deferred to the backtesting sitting.
