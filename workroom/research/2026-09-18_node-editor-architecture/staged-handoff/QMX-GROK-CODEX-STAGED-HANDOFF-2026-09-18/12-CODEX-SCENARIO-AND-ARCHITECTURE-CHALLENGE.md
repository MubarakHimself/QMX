# Codex Stage B: independent scenarios and architecture challenge for QMX

You are the independent behavior/scenario and architecture-challenge lead. The operator selects an available Codex model (they proposed GPT-5.6-sol); do not assume that identifier, browser support or subagent features exist without checking your actual environment. Use available subagents, dynamic workflows, installed CIS and architecture/testing skills as useful. There is no arbitrary scenario or worker-count ceiling.

Your input is Grok's complete Stage A candidate, its hash/revision manifest, the latest full operator transcript, requirements, source evidence, audit delta, internal reviews, existing scenario seeds and optional browser reconnaissance. Your output returns to Grok for reconciliation. Do not rewrite canonical QMX documentation, modify shared code, ratify the architecture, build feature epics or launch implementation.

## 1. Verify inputs and preserve independence

Read `CODEX-CHALLENGE-HANDOFF.md` and `ARCHITECTURE-CANDIDATE-MANIFEST.json`. Validate that the files match. Record exact reviewed candidate ID/hashes, code/worktree refs and tool/runtime availability. Missing key candidate files are a review limitation, not a license to invent them. Create reports in a fresh directory, outside active project files where practical.

Work in two passes. Pass I: derive user goals, behavioral requirements, invariants, edge cases and likely failure sequences from intent/evidence before reading the proposed architecture. Save `INDEPENDENT-SCENARIO-BASELINE.md`. Treat old audit absence claims with the supplied newer-code correction. Pass II: inspect the proposed architecture, contracts and existing test evidence; extend and challenge your scenarios against that actual design. Record what was added after seeing it.

Distinguish user requirements, current implementation, Grok assumptions, reviewer recommendations and optional future opportunities. Preserve the latest operator corrections: QMF is one extensible framework; existing Book/BMS is a default to preserve, not a universal ceiling; general data/ML work need not be a bot; sessions, not visible tabs, own context; app-use cannot edit app implementation; independent authoring has appropriate granted tools; specialists remain; PM means Portfolio Manager in the trading domain.

## 2. Generate broad but meaningful coverage

Use CIS for discovery/user journeys where it fits. Generate as many semantically distinct cases as expose useful coverage. Deduplicate equivalent cases; parameterize families rather than writing thousands of cosmetic variations. Report coverage across actual interactions and missing cases, not a raw scenario-count victory. The supplied 80 opportunities and 24 journeys are neither limits nor all committed scope.

Build a coverage model across:
- participants: human, copilot authoring/app-use, specialist, deterministic operation, scheduled/external caller;
- composition: direct use, node, nested subflow, app output consumption, app operation calls, multi-app workflow, composite app, dependency diamond, bounded cycle;
- payload: small values, immutable files/tables, models, references, jobs, finite events and persistent streams;
- lifecycle: draft, validation, install, configure, activate, execute, cancel, resume, upgrade, remove, export/import;
- state: fresh/stale context, revised data, side-by-side versions, cold/warm/resumed model state, missing provider;
- execution: local CPU/GPU, remote CPU/GPU, disconnected UI, coordinator failure, worker failure, preemption;
- authority: allowed/denied/revoked; caller/app/session grants; authoring/app-use; source read versus account execution;
- markets: providers distinct from broker technology, multiple venues/accounts, same ticker at different venues, currencies/units, historic/live data;
- policy: default Book/BMS, non-Book alternative, optional/no MIS, two intelligence versions, no trading outcome;
- failure: partial write, corrupted artifact, missing dependency, quota, duplicate/out-of-order event, timeout/unknown outcome, stale credential, failed rollback.

Use pairwise or other combinatorial exploration to find interactions where useful, but explicitly examine higher-order high-risk sequences. A generated combination is not a valid scenario until its preconditions are feasible and its expected behavior is justified. Record excluded impossible combinations with reasons. Do not claim exhaustive coverage of all possible sequences.

## 3. Minimum scenario families, not a scope ceiling

Cover current/default and alternative complete trading compositions end to end; general data/ML workflows; dataset recipes across heterogeneous sources/revisions; two MIS/model versions; multi-broker/account selection; app-use-to-authoring handoff; concurrent sessions and deliberate history retrieval; extension install/dependencies/migrations; composite apps/shared services; headless and CLI parity; streamed progress and data backpressure; provider/GPU entitlement preflight; crash/restart/cancellation; flat sequential handover and separately non-flat/uncertain cases; skill authoring/evaluation/activation; and agentic procedure graphs versus general deterministic composition.

Explore traps such as: upgrading one dependency in a composite app while an old run waits; cancellation of one shared-feed consumer; upstream success with lost acknowledgement; app-use session becoming authoring through a nested app; copied app package carrying private paths/credentials; plugin settings leaking to another instance; display-name changes incorrectly invalidating computation; stale source revisions changing old results; unknown external order state incorrectly retried; GPU training return missing pinned weights; and hybrid reviews that call a stub successful.

## 4. Specify observable behavior using BDD where useful

Write readable Given/When/Then scenarios grouped by real behavior. Use Scenario Outlines/Examples for meaningful variants. BDD is a communication/specification method here, not a claim that a `.feature` file executes itself. Do not add a testing framework dependency just to format the report.

Each scenario has a stable ID, user goal, source requirement/assumption, preconditions and exact scope, stimulus, expected observable output/status, forbidden effects, test oracle and evidence needed, involved contracts/owners, failure/recovery variant, and future UI journey link. Keep internal implementation checks in a companion technical trace rather than making all user behavior depend on private fields.

Attach an evidence status: proposed behavioral requirement; statically reasoned against architecture; source-inspected; executed against current implementation; executed against a diagnostic model; blocked/unimplemented. A mental walkthrough is not an executed test. A mocked success is not proof of a production integration. Capture test commands, raw logs, environment, seed, source refs and exit status for actual diagnostics.

Where ambiguity permits several reasonable policies, identify the gap and recommend one with consequences. Do not fail a design merely because it chose a different compatible implementation; do fail unowned transitions or silent semantic substitution.

## 5. Challenge the design, not just document its happy path

Trace each high-risk scenario across public operation → permission/context → execution/owner → persistence/evidence → result → reuse/upgrade/deployment. Name the first unsupported transition and a concrete counterexample. Check safety, progress/liveness and normal usefulness; a system that refuses every useful action is not an adequate solution.

Compare alternative-system semantics without inventing dummy Book/BMS records. Distinguish conserved exact accounting/command correctness from current SQS/MIS/Book policy choices. Challenge both unsafe generalization and requirements being silently narrowed to make the current design pass.

Test cross-app APIs beyond JSON shape: meaning, cardinality, timing, effects, instance and version binding, errors, cancellation, reentrancy and ownership. File output needs completeness/integrity/resolution and source provenance; persistent streams need bounded buffers, ownership, checkpoints and shared-consumer lifetime. An internal API need not be HTTP.

Review the stack against the actual repository: supported OS/runtime, lockfile isolation, schema/wire libraries, process placement, analytical versus transactional storage, source licensing, broker/provider SDK constraints, testing and eventual UI host. Existing code can refute a claimed gap; an imported donor policy must be checked against QMX requirements.

## 6. Appropriate testing mechanisms

Use bounded non-destructive diagnostics against existing behavior if useful and permitted. Property/state-machine tests can exercise action sequences; metamorphic checks can test invariants where a single exact answer is unavailable; failure injection can model dropped messages, partial commits and retries. Keep stochastic/model assessments distinct from deterministic lifecycle guarantees.

Evaluate `mutmut` as Python mutation testing: it can reveal whether existing tests detect small semantic code changes. It does not invent correct requirements, test all races, or certify architectural completeness. Verify the installed version/platform (current docs require fork support; Windows execution needs WSL). Mutate only a disposable copy, never the shared worktree. Do not use `mutmut apply` against canonical files. Run a clean baseline, identify scope/exclusions, preserve surviving/equivalent/invalid/timeout/error classifications and raw results. Missing future implementation gets a mutation-test plan, not imaginary scores.

Use Caliper ideas for skill activation, behavior, ablation and repeated evaluation where the real QMA interfaces support them. Skill text or a model judge must not grant permissions or silently declare its own verifier correct.

## 7. Outputs and stopping rule

Deliver:
1. `CODEX-CHALLENGE-RETURN.md`: concise verdict on architecture completeness in reviewed scope, major findings, files and evidence limits.
2. `INDEPENDENT-SCENARIO-BASELINE.md`: the pre-design pass and its provenance.
3. `SCENARIO-CATALOG.jsonl`: machine-readable scenario records using a documented proposed record schema; do not invent QMX persisted contract IDs.
4. `behavior/` readable `.feature` files or equivalent Given/When/Then specification, preserving IDs.
5. `COVERAGE-AND-GAPS.md`: requirement/scenario/contract/UI/test traceability, combinations explored, uncovered high-risk cells and exclusions.
6. `ARCHITECTURE-FINDINGS.md`: evidence-backed counterexamples with severity, candidate file/decision references, expected/actual-designed behavior, impacts and repair options.
7. `TEST-AND-MUTATION-PLAN.md`: executable checks completed versus later required tests, environments and constraints.
8. `EVIDENCE-MANIFEST.json`: pinned candidate/code versions, hashes, sources and actual diagnostic logs.
9. `GROK-RECONCILIATION-HANDOFF.md`: prioritized findings and exact required inputs; avoid a competing replacement architecture.

Native skill output consolidation is fine if a manifest maps every obligation. End broad generation when every accepted requirement is mapped, defined high-risk interactions have explicit scenario treatment, duplicates are removed, and remaining holes are named. Continue if new high-value failure classes emerge; do not chase infinite counts or claim all theoretical cases covered.

Package the safe reports and artifacts into `QMX-CODEX-CHALLENGE-<timestamp>.zip`. Do not include secrets, caches, large source copies or user browsing history. Return exact paths and a short routing summary; the operator does not need to manually judge each test. Stop for Grok reconciliation. If foundational inputs are missing, deliver the valid portion and a precise missing-input request rather than claiming approval.
