---
id: SCN-0007
title: An Agent Cannot Promote an Artifact to Live
type: scenario
status: provisional
component: COMP-QMF-REGISTRY
depends_on: [COMP-QMF-CORE]
decisions: [DEC-0003, DEC-0004, DEC-0033, DEC-0038, DEC-0041]
sources: [docs/constitution.md, docs/components/qmf-registry.md, docs/contracts/ct-06-registration.yaml, docs/contracts/ct-07-lineage-edge.yaml, docs/contracts/ct-08-gate-evidence.yaml]
generated: 2026-08-18
verified: 2026-08-18
stale_after: 30d
---

# SCN-0007: An Agent Cannot Promote an Artifact to Live

This scenario makes the human-only promotion boundary observable even before the evidence schema is ratified. Execution status: **blocked specification**. [DEC-0041]

## Given

A research artifact has a proposed fingerprint and lineage and an agent reports that its checks passed. CT-06 through CT-08 remain schema placeholders; an agent's research or recommendation is not an operator ruling. [DEC-0003] [DEC-0033] [DEC-0038]

`GAP(GAP-0010): Ratify canonical identity.`

`GAP(GAP-0016): Ratify the causality gate and evidence.`

`GAP(GAP-0017): Ratify attempt accounting.`

`GAP(GAP-0019): Ratify the human-reviewed promotion evidence and immutable sign-off.`

## When

The agent attempts to change the artifact from lab or research status into a live zone.

## Then

The status does not change and no live capability is granted. The attempt may be recorded as evidence after the contracts exist, but only a human-controlled, signed promotion occurrence can authorize the boundary crossing. [DEC-0003] [DEC-0004] [DEC-0041]

## Worked numbers

There is no ratified attempt budget or evidence-count threshold. `registry:registry_attempt_budget` remains null, and passing any number of agent-run checks cannot substitute for human authorization.
