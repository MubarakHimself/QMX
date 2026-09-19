# Independent Codex focused architecture recheck return

Date: 2026-09-19  
Candidate challenged: `qmx-workflows-arch-2026-09-19-c`  
Predecessor reviewed at Stage B: `qmx-workflows-arch-2026-09-18-a`  
Implementation reference: `270e992995c2378ca63cf6343254ef8140a8c97e`  
Disposition: **repairs required; not ratified**

## Executive result

Stage C materially improves the candidate, preserves the operator's closed OD-01 answer, and supplies recognizable machines for AD-23 through AD-31. It is **not yet architecture-complete enough to resume epics as written**. The remaining defects are bounded specification defects: identity and authority are not consistently carried into the representative contracts; several crash/race machines omit the durable keys and observations that make their guarantees decidable; and the folded documentation contains both stale process statements and a few semantic overclaims.

No new Pass-I, operator decision, implementation work, Documentation Factory run, or scenario redesign is needed. Grok can desk-fix the spine/contracts/ledger and the already-folded docs, perform a focused consistency check, and then resume epics.

This is a challenge result, not approval or ratification.

## Scope and preserved constraints

- Reviewed only AD-23..AD-31, their `CONTRACTS.md` payloads, AF-01..AF-20 dispositions, and the already-folded ADR-0024 / SCN-0018..0022 / L36 material.
- OD-01 remains closed exactly as recorded: Book/BMS is the default, not the ceiling; a selected ATC is adopted by QML, QMB, optional MIS, QMN, paper, and live; sensing is not an ATC; dummy Book/PolicyPair is `INVALID_INPUT`; live is sequential paper-then-live plus L17; QMN is the only venue importer (`CODEX-RECHECK-HANDOFF.md:28-32`; `OPERATOR-QUESTIONS.md:21-23`; `ARCHITECTURE-SPINE.md`, AD-23 at lines 222-226).
- The immutable Pass-I baseline was not re-derived. The supplied catalogue still contains 85 unique scenario IDs: 65 Pass-I and 20 Pass-II. Every ID occurs in the BDD corpus; none is missing or extra. BDD remains specification, not execution evidence.
- QMA AD-17 JobHandle vocabulary remains parent law. No `succeeded` or `awaiting_approval` state was introduced (`ARCHITECTURE-SPINE.md:240-244`; `CONTRACTS.md:229-249`).
- No production code or canonical input document was edited; no Documentation Factory, epics, Reticle, live broker, or mutation testing was run.

## Decision

**Do not resume epics yet.** First apply the desk fixes enumerated in `GROK-DESK-FIX-HANDOFF.md`. The architecture can then clear this focused gate without reopening discovery if the corrected documents make every machine's identity, authority, durable state, transition guards, and evidence explicit and mutually consistent.

The highest-risk blockers are:

1. `AlternativeRunConfig` does not carry a stable composition/PolicyPair identity or the command-owner and admission evidence AD-23 requires.
2. Invocation/grant and session/change-request contracts do not specify authoritative revalidation, canonical hashes, dedupe domains, or revocation race semantics.
3. Fencing, outbox/join, checkpoint, and stream contracts omit durable identity or observation fields needed to resolve restart, duplicate, cutover, and partial-failure cases.
4. Package and recipe contracts contradict or under-specify their parent ADs.
5. `CONTRACTS.md` claims schema completeness while its AD-3 descriptor and several new payloads are incomplete.

See `AD23-31-FINDINGS.md` for the evidence-backed findings, `AF-DISPOSITION-RECHECK.md` for the AF ledger, and `DOCS-DRIFT.md` for the fold audit.

## Coverage and holes

| Area | Recheck coverage | Result |
|---|---|---|
| AD-23 ATC | identity, completeness, command target, admission, evidence, adoption | open defects RC-01..RC-02 |
| AD-24 invocation/grants | authoritative binding, retry identity, nested calls, revoke/expiry | open defects RC-03..RC-05 |
| AD-25 fencing | states, keys, evidence, reconcile, restart | open defect RC-06 |
| AD-26 workflow | outbox, receiver dedupe, JobHandle law, join determinism | JobHandle holds; open defects RC-07..RC-08 |
| AD-27 checkpoint | cut, generation, restore, reconciliation | open defect RC-09 |
| AD-28 streams | epoch, cutover, loss evidence, leases/refcount | open defect RC-10 |
| AD-29 session/change request | CAS dedupe, reconnect, immutable request/apply evidence | open defects RC-11..RC-12 |
| AD-30 packages | manifest shape, atomic lifecycle, migration, bytes retention, export oracle | open defects RC-13..RC-14 |
| AD-31 recipes | identity, canonical hash, required schema, lineage | open defect RC-15 |
| Cross-contract conformance | AD-3 descriptor and door matrix | open defects RC-16..RC-17 |
| AF-01..AF-20 | all dispositions rechecked | AF-20 holds; AF-01..19 remain open or partial |
| Folded docs | ADR-0024, SCN-0018..22, L36 references | repairable drift; no direct L36 semantic reversal found |

## Stop point

Return to Grok for reconciliation. Do not infer authorization from this package to implement, ratify, rerun Documentation Factory, or start epics.
