# Coverage and gaps (draft)

## Coverage legend

Supported = explicit owner + contract + journey/evidence. Partial = semantic intent exists but transition, integration, or oracle is missing. Unsupported = design-only/absent. Contradictory = candidate refuses frozen scope.

| Baseline family | Status | Covered evidence | Material gap |
|---|---|---|---|
| BR-CAP | Partial | AD-2/3/18 discovery, dependencies, requested scopes | Duplicate/incompatible package, migration failure, open-session grants, uninstall dependants, secret stripping. |
| BR-OP | Partial | AD-3/21 and JobHandle state vocabulary | Partial artifacts, cancel races, expiry, unknown external outcome. |
| BR-WF | Partial | AD-4..6 topology and selected-subgraph intent | Cardinality/join policy, invalidation, review resume, trigger dedupe/concurrency. |
| BR-SES | Mostly supported | AD-8/9, J01, session grant boundary | Reconnect must not replay intent; CAS/context revision absent. |
| BR-DATA | Partial | AD-12/13, J06/J13, CT-07 lineage | Provider disagreement, entitlement/unavailable states, complete weights, placement. |
| BR-STR | Partial | Stream contract and J17 phase/cancel | Ordering, gaps, backpressure, duplicate handling, shared unsubscribe. |
| BR-MKT | Contradictory/partial | Default Book/BMS and venue/risk boundaries | Frozen complete non-Book alternative refused pending L36; command arbitration/handover not executable. |
| BR-PLC | Deferred | AD-15 intent only | Preflight, staging, coordinator/worker/UI failure matrix, restore. |
| BR-SKL | Partial | AD-19 and evaluation principles | Lifecycle and WSL disposable mutation evidence. |
| BR-APP | Partial | AD-10/17 composition and host mediation | Contribution discovery, mount/dispose, reconnect/resync, composite refusal. |

## Implementation evidence gaps

- QMA `TaskGraphStore` is in-memory; no sqlite lifecycle, successor traversal, or durable lease/job evidence.
- Topology validation misses self-loops and longer cycles.
- Daemon listener drains frames but does not dispatch commands to owners.
- Product-session and capability descriptor contracts are not implemented.
- `FederatedHit` intentionally remains `KnowledgeHit | ArtifactHit`; proposed `ContributionHit` is an amendment, not current behavior.
- QML graduation is tested, but QML→QMB→QMN end-to-end execution is not.
- QMF/QMB/QMN package tests prove bounded ownership and doors, not cross-component integration or an alternative live path.
- QMA broad green claims are unsafe: selected tests were blocked by invalid/missing `qmx-agents/.venv` as recorded in `RECON-RETURN`.

## First unsupported transitions

1. Package validation/index rebuild → atomic preservation of prior index (`ARCHITECTURE-SPINE.md:190`).
2. Artifact emitted → worker loss → partial inventory plus unknown terminal (`CONTRACTS.md:98-112`).
3. Fan-out → join with empty/missing/duplicate/late/failed partitions (`CONTRACTS.md:144-146`).
4. Buffer saturation → explicit backpressure/gap/no silent market-event loss (`CONTRACTS.md:114-128`).
5. Placement preflight → portable staging → dispatch (`IMPLEMENTATION-SEQUENCE.md:32-34`).
6. Mutation run → WSL disposable evidence (`STACK-AND-EVALUATION.md:48+`).

## Required corrections to claims

Do not claim QMF is multiple frameworks; it is one framework with extension surfaces. Do not make Book/BMS the universal ceiling. Do not require data/ML to be bots or trading-wrapped. Preserve specialists. Call PM Portfolio Manager in the trading context. Keep session context/grants session-owned. App-use cannot modify implementation. Treat UI adapters as non-authoritative.
