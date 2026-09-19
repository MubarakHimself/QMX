# Test and mutation plan

## Evidence posture

Tests here establish only the behavior named by each oracle. They do not ratify the architecture. Existing package tests are kept separate from future contract/integration tests, and source inspection is never reported as execution.

## Checks completed in this challenge

| Check | Environment / revision | Result | What it proves | What it does not prove |
|---|---|---|---|---|
| Input archive SHA-256 | Windows host | Matched `4247e7e84eba458a2d73c696dd2783b0635a36379dd9e3144da87a6cba478b87` | Correct challenge input archive | Contents are architecturally sound |
| Candidate manifest verification | Extracted challenge input | All 21 manifest entries matched path, byte count and SHA-256 | Candidate was read without substitution | Candidate claims are true |
| Git revision pins | Docs `b8b4d21…`; implementation `270e992…` | Exact match | Evidence targets the requested baselines | Workspace is globally clean or fully integrated |
| Frozen Pass-I baseline hash | Output file | `1c2c865d1cef50076682a737472174fa307cf1fc8eb3663b122ed04ab6f39fd8` | Pass I was frozen before candidate review | Scenario set is theoretically exhaustive |
| Focused QML mill/store slice | `uv run --frozen --project qml python -m pytest -q -p no:cacheprovider --tb=line` with eight named research/mill test files, implementation `270e992…` | **47 passed in 3.19s** | Stage-0 vocabulary, store, projection/collapse, legal entries and graduation behavior covered by those tests | QML→QMB→QMN integration |
| QML project default test selection | `uv run --frozen --project qml python -m pytest -q -p no:cacheprovider --tb=line` | **4 passed in 1.61s** | Default configured QML collection remains green | The full QML test inventory; explicit focused slice is stronger for this scope |
| QMN conformance slice | `uv run --frozen --project qmn python -m pytest -q -p no:cacheprovider --tb=short qmn/tests/test_qmn_conformance.py` | **5 passed, 1 skipped in 2.72s** | Bounded venue/conformance behavior | Live broker behavior or alternative trading composition |
| QMA review | Source inspection at `270e992…` | `TaskGraphStore` in-memory; edges/successors/product sessions/owner dispatch absent; topology validator incomplete | Current adoption gaps | Runtime race behavior; no QMA green claim |
| Scenario/BDD reconciliation | Final package validation | Required: 85 unique catalog IDs = 85 unique feature IDs, zero missing/extra/duplicates | Behavioral trace integrity | `.feature` execution |

No Reticle run was applicable because no app or user-facing implementation was changed. No live broker/provider, credential, paid account or mutable external system was exercised.

## Required verification gates

Run these in order after reconciliation. A later gate must not paper over an earlier failed safety invariant.

1. **Schema and identity conformance**
   - Validate full AD-3 descriptor schema, including finite `event`, closed effect/placement values and version compatibility.
   - Validate invocation binding to contribution tuple, installed instance/config revision and structured grant.
   - Separate recipe-definition identity from output-release identity and verify CT-07 lineage.
   - Reject provider/venue/account/instrument conflation.

2. **Graph safety and executor semantics**
   - Property-test self-loop, arbitrary directed cycles, duplicate/missing endpoints and disconnected legal DAGs at registration and compile.
   - Test every edge mapping: `one`, `zip`, `broadcast`, `keyed-join`, explicitly authorized Cartesian.
   - State-machine test empty, missing, duplicate, late and failed partitions; retry one failed branch without repeating successful effects.

3. **Task-graph durability and dispatch**
   - Persist graph, edges, mission, leases, attempts and job evidence through the sole daemon writer.
   - Fault-inject crashes before/after predecessor commit, successor eligibility, outbox publish, dispatch acknowledgement and lease release.
   - Assert exactly one logical successor effect and a deterministic reconcile state after restart/backup/restore.

4. **Operation and JobHandle truthfulness**
   - Test logical invocation vs attempt ids, idempotency/reconcile policies, receipts and unknown outcomes.
   - Race cancel, completion, timeout, worker loss and retry; assert the defined winner/terminal law.
   - Verify partial artifact inventory/completeness, expiry and no fabricated empty result.
   - Compare supported direct/library, QMB CLI, node, app and copilot doors for semantic equivalence; assert QMA/QMN operator CLIs remain absent.

5. **Wire, product session and authority**
   - Authenticated command reaches exactly one owning component and produces a durable result/refusal.
   - Expected-revision CAS rejects stale context mutation.
   - Reconnect resumes queries/events but never repeats uncertain intent.
   - Installation/upgrade/revocation cannot mutate old session grants or retarget instance/account.
   - App-use produces a typed change request; working tree/source remains unchanged until a distinct authoring session validates and applies it.

6. **Package lifecycle and discovery**
   - Valid headless package appears in contribution/catalog and supported doors without requiring navigation.
   - Duplicate/incompatible/migration-failed package preserves the last usable roster atomically.
   - Discovery hit pinned before disable/uninstall returns typed unavailable/tombstone at invoke; it never silently resolves another version.
   - Export scanner verifies no secrets, private paths or transcript payloads and requires typed external bindings.

7. **Data, model and placement**
   - Metamorphic tests: source order must not erase disagreement; display rename must not change semantic identity; correction must not mutate old release; future data must not affect earlier known-at result.
   - Verify calendar/timezone/alignment/missing/units/adjustment/licensing fields and complete weight/model/environment pins.
   - Preflight available/configured/authorized/reachable/healthy independently; stage local inputs as content-addressed artifacts or refuse before dispatch.

8. **Stream protocol**
   - Model replay→live cutover with epoch/sequence/watermark, duplicate/late/gap events, bounded buffer and explicit overload policy.
   - Kill/reconnect producer and consumers; verify resumption cursor and health evidence.
   - Remove one of several consumers and prove the shared upstream subscription stays alive.

9. **Trading ownership and handover**
   - Protect the default Book/BMS regression path.
   - Once the foundational decision is resolved, exercise a complete non-Book alternative without dummy records.
   - Bind every command to venue, account, role, instrument, adapter capability, credential ref and owner epoch.
   - Fault-inject unknown orders, non-flat residuals, new-owner fill followed by software rollback, and predecessor restart; assert fencing and reconciliation.

10. **Cross-store recovery and bounded end to end**
    - Snapshot and restore QMA journal/projections, QMB JSONL, QMF registries/evidence, QML blobs and artifact bytes using a checkpoint manifest and defined order.
    - Detect missing/corrupt/orphan/divergent references and external effects; quarantine rather than silently merge.
    - Run one real governed QML artifact through QMB compilation to QMN paper/conformance with complete provenance.

## Test mechanisms by invariant

| Mechanism | Best use here | Required oracle |
|---|---|---|
| Contract/conformance tests | Schemas, state vocabulary, identity, permissions and door parity | Exact accept/refuse payload, owner and version |
| Property-based tests | DAGs, mapping cardinality, grants, source order and partition sets | Invariant holds over generated inputs; minimized counterexample retained |
| State-machine tests | package/session/job/stream/deployment lifecycles | Only legal transitions; durable state and winner law |
| Fault injection | crash windows, dropped messages, disk exhaustion, stale leases, unavailable providers | Recovery/refusal is explicit; no duplicate external effect |
| Metamorphic tests | data revisions, order, display changes, projections vs reruns | Defined transformation preserves or deliberately changes identity/result |
| Integration tests | owner routing and cross-component references | Actual nearest consumer crosses the claimed boundary |
| BDD journeys | Operator-observable intent/refusal/recovery | Scenario ID, visible result, durable evidence and forbidden effects |
| Repeated model/skill evaluation | activation/ablation and stochastic assistant behavior | Fixed corpus, independent evaluator, repetitions/confidence and permission checks |

## Mutation-testing plan

Mutation testing is optional evidence about test sensitivity. It cannot discover the right architecture, certify races or substitute for the gates above.

### Environment and safety

- Windows host observation: `mutmut` is not installed on PATH; WSL2 is available with `docker-desktop` as the default distribution.
- Current mutmut documentation requires fork support; Windows execution therefore belongs inside WSL/POSIX.
- Create a **disposable copy/worktree inside a disposable WSL filesystem**, verify its absolute path, and run a clean test baseline there.
- Never run `mutmut apply` on the shared QMX worktree, the candidate tree or canonical files.
- Pin and record Python, mutmut, dependencies, revision, scope, exclusions, timeout and raw results.

### Targeted semantic mutants

- intersection → union for grants;
- remove contribution version/instance/config binding;
- drop idempotency key or reuse it for another logical operation;
- accept a self-loop or long cycle;
- commit predecessor completion without successor/outbox;
- dispatch successor twice after restart;
- mark a partial artifact complete;
- change cancel/complete winner;
- suppress stream gap/backpressure event or advance cutover cursor early;
- silently substitute provider/revision/venue/account;
- remove deployment fencing/owner-epoch comparison;
- make UI dispose cancel durable server work;
- permit app-use to mutate source or apply its own change request.

Each mutant must be associated with a named test that fails for the intended reason. Preserve classifications: killed, survived, equivalent, invalid, timeout and error. Surviving high-risk mutants become test gaps; an aggregate score alone is not an acceptance criterion.

## False-green controls

- Do not count an import/class/schema-existence assertion as nearest-consumer adoption.
- Do not count CT-07 ExperimentSpec successors as Task Graph control-flow execution.
- Do not claim QMA green while the pinned QMA environment remains blocked.
- Do not treat the two current discovery hit classes as proof that proposed ContributionHit exists.
- Do not treat package-level QML/QMF/QMB/QMN tests as the QML→QMB→QMN journey.
- Do not treat a model’s self-judgment, a skill’s prose, a manifest’s `exports_secrets:false`, or a UI success toast as a deterministic oracle.
- Preserve raw command output and exact revisions for every future result.
