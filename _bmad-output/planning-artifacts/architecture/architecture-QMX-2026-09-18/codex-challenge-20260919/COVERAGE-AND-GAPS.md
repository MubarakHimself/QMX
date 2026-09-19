# Coverage and gaps

## Coverage statement

The catalog contains **85 deduplicated scenarios**: 65 frozen Pass-I scenarios and 20 additions derived only after the candidate was read. Every catalog ID appears exactly once in `behavior/`; there are no missing, extra or duplicate feature IDs. The feature files are behavioral specification, not a claim that `.feature` files execute.

Coverage here means that an accepted requirement has a scenario and trace. It does **not** mean the behavior exists. Statuses are:

- **Implemented evidence:** bounded behavior observed in the pinned code/tests.
- **Candidate-defined:** the design names an owner and intended rule, but implementation/integration is absent.
- **Partial:** a rule exists, but a transition, schema or oracle remains open.
- **Contradictory:** the candidate explicitly withholds an accepted requirement.

## Requirement-to-design trace

| Baseline family | Scenario IDs | Candidate decisions / proposed contracts | Future UI journey | Evidence status | Principal hole |
|---|---|---|---|---|---|
| BR-CAP — capabilities/packages | P1-CAP-001..006; P2-CAP-007..009 | AD-2, AD-3, AD-13, AD-18; Contracts §§1,2,8 | Search contribution → inspect exact version/instance → install/enable/grant → see refusal/recovery | Partial, design-only for new rail | Atomic install/index/migration/uninstall, invoke-time availability, verified secret-free export |
| BR-OP — operation lifecycle | P1-OP-001..005; P2-OP-006..008 | AD-3, AD-15, AD-21; Contracts §§1,6 | Start → inspect progress/artifacts → cancel/reconcile/expire | Partial | Idempotency, logical run vs attempts, terminal vocabulary, cancel winner, partial completeness |
| BR-WF — workflow semantics | P1-WF-001..007; P2-WF-008..009 | AD-4..7, AD-20; Contract §9 | Author storyboard → validate selected DAG → run → review/retry/resume | Candidate-defined; current QMA refutes adoption | Successor atomicity, joins, partial retry, trigger concurrency, durable edges and full DAG check |
| BR-SES — sessions/copilot | P1-SES-001..006; P2-SES-007..011 | AD-8..10; Contracts §§3,4 | Create authoring/app-use session → select refs/grants → reconnect/change-request handoff | Partial, runtime absent | CAS, reconnect dedupe, structured/versioned grants, stale change requests, backup/restore |
| BR-DATA — data/ML | P1-DATA-001..008; P2-DATA-009..011 | AD-11..13, AD-15; Contract §5 | Select attributed sources → author/pin recipe → preview/export/train/compare | Partial | Pre-run recipe identity, complete temporal/unit/licensing schema, portable staging and model-weight completeness |
| BR-STR — streams | P1-STR-001..005; P2-STR-006 | AD-12; Contract §7 | Subscribe replay → observe cutover → inject gap/backpressure → detach one consumer | Partial | Epoch/sequence, atomic cutover, buffer/gap/late policy, heartbeat, consumer leases |
| BR-MKT — trading composition/deploy | P1-MKT-001..010; P2-MKT-011 | AD-11, AD-14, AD-22; Contract §10 | Compare default and alternative → bind account/venue → handover/reconcile | **Contradictory** for complete non-Book deploy; partial otherwise | L36 decision, alternative accounting/risk path, command fencing, unknown orders/residual positions |
| BR-PLC — placement/recovery | P1-PLC-001..006; P2-PLC-007 | AD-15, AD-16; Contracts §§6,10 | Preflight → stage artifacts → dispatch → lose worker/coordinator/UI → restore | Partial/deferred | Cross-store checkpoint and restore order, coordinator/worker failure matrix, checkpoint/resume |
| BR-SKL — skills/quality | P1-SKL-001..004 | AD-9, AD-19 | Install/activate/evaluate/disable skill → inspect permissions and evidence | Partial | Activation/ablation contract, independent evaluator, repeated/stochastic confidence thresholds |
| BR-APP — app composition/UI | P1-APP-001..008 | AD-10, AD-17, AD-20, AD-21 | Mount native/headless/composite → bind parameters → reconnect/dispose | Partial | Wire DTOs for view lifecycle, shared parameters, stale snapshot/resync, precise door routing |
| Cross-component adoption | P2-INT-001 | AD-1, AD-7, AD-11..16 | Governed QML artifact → QMB compile → QMN paper/conformance | Unsupported integration | No executed QML→QMB→QMN journey at 270e992 |

## Candidate-to-implementation trace

| Candidate claim | Pinned implementation evidence | Classification |
|---|---|---|
| Reuse QMA Task Graph owner and persist edges/successors | `TaskGraphStore` is in-memory; `TaskGraph` has no edges; no successor walk | Proposed connect, not implemented |
| Full DAG validation | Validator checks endpoints and only a direct reverse edge; self-loop and three-cycle remain admissible | Existing behavior refutes full DAG claim; candidate honestly names the hole |
| ContributionHit third rail | Current `FEDERATED_HIT_CLASSES` is `{knowledge, artifact}` and the union is two classes | Proposed amendment, not current capability |
| Product-session wire/daemon commands | No product-session symbol; listener drains bytes without owner dispatch | Design-only |
| QML Stage-0/mill and host store | Types/store exist; 47 focused tests passed in this challenge | Implemented bounded evidence |
| QMF data/risk and QMB default doors | Existing package ownership/tests support the boundary; no full cross-product journey run here | Implemented package evidence only |
| QMN closed venue selection | QMN conformance slice: 5 passed, 1 skipped | Implemented bounded evidence |
| Complete non-Book deployed path | Candidate refuses live/node-paper without Book pending L36 | Not designed/implemented in accepted scope |
| UI host/adapters | Contract prose only; no UI implementation was requested or tested | Design-only |

## High-risk interaction matrix explored

| Interaction | Dimensions combined | Covered scenario(s) | Remaining risk |
|---|---|---|---|
| Discovery-to-use race | package version × instance/config × health × grant × uninstall | P1-CAP-004..006, P2-CAP-007..009, P2-SES-008 | No invoke-time resolution/tombstone contract |
| External retry | timeout × uncertain outcome × retry × cancel × worker restart | P1-OP-002..005, P2-OP-006..008 | No idempotency/reconcile envelope |
| Durable workflow | branch × join × crash × retry × side effect | P1-WF-003..007, P2-WF-008..009 | No atomic successor/outbox or join state machine |
| Session concurrency | two clients × stale revision × reconnect × revoke/upgrade | P1-SES-002..005, P2-SES-007..011 | No CAS or durable command-result replay |
| Data provenance | disagreeing providers × revision × known-at × missing/truncated × placement | P1-DATA-001..008, P2-DATA-009..011 | Recipe schema/identity incomplete |
| Stream cutover | replay × live × gap/duplicate/late × overload × shared consumers | P1-STR-001..005, P2-STR-006 | Protocol state and recovery absent |
| Trading handover | two versions × same account/symbol × residuals × unknown order × rollback/restart | P1-MKT-004..010, P2-MKT-011 | No fencing token/owner epoch or typed residual ledger |
| Distributed recovery | coordinator loss × worker continuation × UI close × store restore | P1-PLC-003..006, P2-PLC-007 | No cross-store consistency point |
| Composite apps | shared/separate instance × permission intersection × partial failure × recursion | P1-APP-003..008 | Invocation envelope and recursion budget not closed |
| Skill assurance | install/activation × permission boundary × stochastic eval × mutation | P1-SKL-001..004 | Evaluation contract and execution evidence absent |

## First unsupported transitions

1. Operation accepted → timeout/unknown result → safe retry or reconcile.
2. Task completion committed → successor eligibility persisted → dispatch published exactly once logically.
3. Package bytes validated → migration/activation → catalog index atomically published or prior version restored.
4. Discovery hit pinned → instance/config resolved → health/grant rechecked → invocation authorized.
5. Session mutation sent → revision conflict or durable result → reconnect without replaying intent.
6. Replay cursor reaches live watermark → atomic cutover → gap/late/backpressure evidence.
7. Old command owner drained → residuals/orders reconciled → new fenced owner activated → old process restarts safely.
8. Multi-store snapshot → ordered restore → orphan/corrupt/external-effect reconciliation.

## Explicit holes requiring decisions rather than more scenario count

- Whether the accepted complete non-Book deployment requirement remains in scope or L36 is amended.
- Recipe-definition identity and versioning before an output release exists.
- Effect-specific idempotency and reconciliation, especially trading/external egress.
- Deployment command-owner fencing and non-flat/unknown handover policy.
- Structured grant identity and scope across package upgrades and multiple instances.
- Cross-store backup/reconstruction without inventing a central evidence database.
- Exact QMA/QMN headless routing that preserves the no-operator-CLI law.

## Exclusions and non-claims

- No QMX code, canonical docs, candidate file or architecture decision was edited or ratified.
- No user-facing app was changed, so Reticle/UI verification was not applicable.
- No live broker, paid provider, secret, real account or destructive command was used.
- No broad QMA suite was claimed green; its selected pinned environment was already recorded blocked.
- No mutation run was attempted. `mutmut` is absent from the Windows PATH and, in any case, must run only in WSL/POSIX on a disposable copy.
- BDD files are specification. They are not executable-evidence claims.
- The scenario catalog is broad but does not claim mathematical exhaustion; remaining high-risk classes are explicitly listed above.
