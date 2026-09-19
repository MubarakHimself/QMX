# QMX independent scenario baseline (Pass I freeze)

**Candidate later challenged:** `qmx-workflows-arch-2026-09-18-a`  
**Pass-I freeze rule:** This file was derived and frozen before reading `ARCHITECTURE-SPINE.md`, `CONTRACTS.md`, `REQUIREMENTS-ADDENDUM.md`, `JOURNEYS.md`, `CONFLICT-REGISTER.md`, or the candidate reviews.  
**Evidence state:** proposed behavioral requirements and evidence-derived challenge cases; not architecture ratification and not claims of executed behavior.

## 1. Provenance and method

Pass I used only:

- the operator transcript `Explore-Node-Editor-Architecture.md`;
- `RECON-RETURN.md`, treating implementation revision `270e992995c2378ca63cf6343254ef8140a8c97e` as current and the `8510c03` absence claims as stale;
- `inputs/opportunities-journeys.md` as a seed set, never as committed scope or a ceiling;
- the reference-recon return, capability implications, adaptation opportunities, and evidence manifest;
- the operator corrections in the Stage-B launch prompt;
- current public documentation used only to stabilize meanings: MCP Apps (tool plus separately declared UI resource, host mediation, sandboxed view, capability negotiation), OpenBB (provider extensions normalized behind shared models; apps/widgets as declarations over backends), W3C PROV (entities, activities, agents and derivation), CloudEvents (common event envelope), OAuth Security BCP (scope and audience restriction), and mutmut's current platform requirements.

The CIS methods applied were Problem Statement Refinement, Is/Is-Not, Systems Thinking, Failure Mode Analysis, Constraint Identification, and a morphological/pairwise exploration of the requested dimensions. The exercise diagnosed before judging solutions. It did not turn optional product ideas into requirements.

### Refined problem statement

QMX needs a construction kit that lets an operator and granted assistants discover, author, validate, compose, execute, inspect, version, reuse, move, and retire domain capabilities across research, data/ML, and trading without collapsing their meanings, owners, authority, or lifecycles. It must preserve today's useful defaults while making supported alternatives honest. A visually connected or declaratively described composition is not sufficient unless its semantics remain correct through version change, partial failure, disconnect, placement, permission change, and external side effects.

### Success criteria for the architecture challenge

1. Every accepted behavior below has an identifiable contract/owner and an observable oracle.
2. The design supports useful work, not merely safe refusal.
3. Definition, run, result, evidence, authority, and deployment identities are not silently substituted for one another.
4. Default Book/BMS behavior remains regression-protected while at least one complete non-Book alternative is expressible without dummy Book/BMS records.
5. Non-trading data/ML work is first-class and need not be represented as a bot.
6. App-use cannot edit implementation; authoring is separately granted, diffed, validated, and versioned.
7. Session context and grants belong to sessions, not visible tabs.
8. Durable and streaming behavior remains truthful through retries, cancellation, restart, backpressure, and unknown external outcomes.

## 2. Boundaries: what the requested system is and is not

| It is | It is not |
|---|---|
| Composition of owned capabilities into understandable, reusable work | A new universal strategy language |
| An experimentation/storyboard surface plus deliberately executable procedures | A rule that every visible item or edge executes |
| A deterministic workflow system that may invoke agents | A replacement for QMA's agentic procedure graphs or specialists |
| One QMF framework with extension surfaces | A sixth COMP or a second general framework |
| Versioned apps, operations, workflows, widgets, packages and artifacts | A marketplace or mandatory cloud platform |
| Local, remote, supervised and unattended placement profiles | A rule that only agents can run remotely |
| A platform for trading and non-trading data/ML/research work | A bot factory with fake trading wrappers |
| A capability-scoped copilot with authoring and app-use profiles | A single omnipotent assistant or permission encoded in prompt text |
| A public-interface extension model | Permission for app-use or computer-use to edit QMX implementation |
| BDD as human-readable specification | A claim that `.feature` files execute without a runner |

## 3. Participant and ownership model

| Participant | Goal | Boundary that must remain visible |
|---|---|---|
| Human operator | Explore, author, approve, compare, deploy, supervise, recover | Approval is not inferred from opening an app or asking a question |
| Authoring copilot | Propose definitions, code, schemas, workflows, layouts, skills | Changes are diffed/validated/previewed and explicitly saved/published |
| App-use copilot | Explain records and invoke only app/session-granted operations | Cannot edit implementation, acquire authoring, or union component grants |
| Specialist / agent | Perform reasoning or long-running delegated work | Specialists remain; workflow coordination does not erase their ownership |
| Deterministic runtime | Execute typed operations and procedure graphs | Must not improvise authority, semantics, or undeclared retries |
| Scheduler / external caller / CLI | Trigger the same logical operation through another door | Trigger identity and idempotency remain explicit |
| Package/extension owner | Contribute public capabilities and migrations | A manifest requests permissions; it does not grant them |
| Data provider | Supply attributed data under coverage/entitlement rules | Provider is not broker, venue, account, or execution authority |
| Broker/venue adapter | Submit/reconcile explicitly targeted commands | A dashboard filter cannot retarget a command |
| Worker/coordinator | Place and supervise compute | Worker loss, coordinator loss, and UI disconnect are distinct |

Trading-floor `PM` means **Portfolio Manager**. Genuine product-management references elsewhere are not renamed.

## 4. Independent semantic invariants

### 4.1 Identity and version

- Display names are labels, never computational identity.
- Package version, capability version, definition version, installed instance, configured instance, run ID, artifact content identity, model weights, provider revision, account, venue and credential are distinct identities.
- A clone/import receives new local identity while retaining source/version provenance.
- An active or waiting run remains pinned to the versions and instances it started with unless an explicit migration protocol says otherwise.
- Side-by-side versions are allowed; install, activate, grant, invoke, revoke and remove are distinct transitions.

### 4.2 Definition, run, artifact and evidence

- A draft/storyboard can contain notes and evidence relationships that are not executable.
- A runnable definition is validated and versioned; an execution is an immutable attempt over pinned inputs.
- A result can be a small value, durable artifact/file, job handle, finite event sequence, or persistent stream. These result kinds are not interchangeable.
- Durable artifacts include schema/type, provenance, completeness, content identity, authorized resolution and expiry/retention status. A machine-local path is not a portable artifact ID.
- Later source corrections never rewrite an old result. A rerun produces a new run and comparison explains the changed inputs.
- Evidence must distinguish observed interaction, documented capability, vendor claim, source inspection, executed diagnostic and unverified proposal.

### 4.3 Composition

- Direct use, node use, nested subflow, saved-output consumption, exported-operation call, optional multi-app workflow and composite app are distinct composition modes.
- Edge meaning, cardinality and timing are declared. Broadcast, zip, keyed join and Cartesian product are never guessed.
- A nested call carries version, instance, budget, cancellation and grant context; recursion and bounded cycles have explicit policy.
- Shared versus independent dependency instances are explicit. Dependency diamonds resolve compatible versions or refuse.
- Presentation disposal cannot silently cancel durable work or shared resources.

### 4.4 Authority and context

- Host grants, not package/app/skill prose, define available authority.
- Composite authority is an explicit granted set (normally no broader than the intersection of allowed exports), never the union of component wishes.
- Existing sessions do not silently gain tools after install/activation; grants are revised explicitly.
- Retrieved history is evidence/context, not a command target. Commands bind current explicit account/venue/instance identifiers.
- Research, simulation, data access, paid compute, live market data and trading are separate authorities.
- App-use can request a change artifact for authoring; it cannot perform the implementation edit itself.

### 4.5 Data, time and markets

- Provider, broker technology, venue, account, instrument, credential and entitlement are separate.
- The same ticker at different venues is not automatically the same instrument.
- Values include units, currency, timezone/calendar, adjustment policy and source revision where meaningful.
- Preview is bounded and distinct from bulk export. Empty match, unavailable source, denied entitlement and truncated/partial data are not the same state.
- Event time and receive time are distinct. Replay/live phase, cursor, heartbeat, ordering, deduplication, gaps and backpressure are observable.
- A stream subscription is not trading permission.

### 4.6 Trading policy

- Book/BMS/SQS/MIS is the default arrangement to preserve, not the universal ceiling.
- A non-Book alternative is a complete composition with its own honest accounting/risk/command semantics, not dummy Book/BMS fields.
- MIS/model intelligence may be required, optional, shadow, absent, or version-pinned according to the composition; it cannot silently become mandatory or production-active.
- Two versions cannot both own the same command-writing role without an explicit arbitration model.
- Sequential handover distinguishes stopped/flat, known residual, and unknown external order/position state. Software rollback never reverses fills.

### 4.7 Progress, failure and recovery

- Queued, running, awaiting approval, paused, interrupted, unknown, succeeded, failed, cancelled and expired are distinct states.
- Retryability and idempotency are per operation/effect. Lost acknowledgement after upstream success must not be treated as definite failure.
- Cancellation defines its target and propagation. Cancelling one consumer does not destroy a shared feed while another consumer remains.
- Partial outputs remain labelled partial and cannot make a hybrid review appear fully successful.
- Crash/restart restores authoritative state from durable evidence; absence of acknowledgement is not evidence of non-execution.

## 5. Independent behavioral requirement set

The IDs below are local challenge IDs, not QMX persisted contract IDs.

### BR-CAP — contribution and discovery

- **BR-CAP-01:** A package declares typed contributions, owner, compatibility, dependencies, versions, migrations, requested scopes, side-effect class, costs and unavailable states.
- **BR-CAP-02:** Validation/index rebuild is atomic: a bad contribution cannot corrupt or partially replace the last usable index.
- **BR-CAP-03:** Installed capabilities are discoverable by humans, authoring sessions, app-use sessions (grant-filtered), workflows, CLI and other apps.
- **BR-CAP-04:** A headless contribution remains discoverable and reusable without a navigation pane or widget.
- **BR-CAP-05:** Removing or disabling a contribution reports dependants and respects pinned in-flight versions.
- **BR-CAP-06:** Private paths, credentials, chats and environment secrets are excluded from exported/shareable packages unless explicitly rebound.

### BR-OP — logical operation and result lifecycle

- **BR-OP-01:** One versioned logical operation preserves input/output/error/effect semantics across direct Python, CLI, node, app and copilot doors.
- **BR-OP-02:** Owner-side validation and authorization apply at every door; transport is not a bypass.
- **BR-OP-03:** Value, artifact, job, event and stream outputs have different lifecycle operations.
- **BR-OP-04:** Long operations expose stable run ID, state, progress/logs, budget, cancellation, artifacts, partial results and stable failure code.
- **BR-OP-05:** Timeouts with uncertain side effects produce an unknown/reconcile state, not an automatic duplicate retry.

### BR-WF — workflow behavior

- **BR-WF-01:** A storyboard can be messy/non-executable; the author deliberately selects and validates a runnable subgraph.
- **BR-WF-02:** Edges declare semantic type and cardinality; invalid connections fail before execution.
- **BR-WF-03:** Nested subflows preserve version, authority, cost, cancellation, trace and recursion/cycle budget.
- **BR-WF-04:** Fan-out/join policies declare behavior for empty, missing, duplicate, late and failed partitions.
- **BR-WF-05:** Rerun/invalidation follows semantic dependencies, not layout or display-name changes.
- **BR-WF-06:** Human review records decision, evidence, identity and resumption version.
- **BR-WF-07:** Scheduled/webhook triggers are deduplicated and overlapping runs follow declared concurrency policy.

### BR-SES — sessions and copilot

- **BR-SES-01:** A session—not a tab—owns conversation, attached work context, grants, active app/definition versions and history references.
- **BR-SES-02:** Concurrent workflow, strategy and ML sessions do not leak context, tools or command targets.
- **BR-SES-03:** Authoring and app-use are distinct profiles. App-use may create a typed change request; authoring may produce a diff/new version.
- **BR-SES-04:** A nested/composite app cannot transform app-use into authoring or expand grants.
- **BR-SES-05:** Reconnect restores the session's prior context/version without replaying old intent as a new command.
- **BR-SES-06:** Specialists remain discoverable/delegable; one conversational surface does not erase specialist roles.

### BR-DATA — resources, recipes and ML

- **BR-DATA-01:** Data resources expose provider, coverage, schema/semantic roles, units, timezone, freshness, provenance, entitlement, licensing and revision/content identity.
- **BR-DATA-02:** Provider disagreement is attributed; sources are not silently merged.
- **BR-DATA-03:** Recipes pin sources/revisions, transforms, alignment, calendars, leakage-sensitive fields and output schema.
- **BR-DATA-04:** Dataset/model definition, exact data binding, execution, weights and evaluation artifacts remain separate and traceable.
- **BR-DATA-05:** Training placement and inference placement are separate decisions; a successful GPU job must return pinned, complete weights or fail honestly.
- **BR-DATA-06:** Non-trading data/ML artifacts are catalogued and reusable without Book/BMS/QMN wrappers.

### BR-STR — streams

- **BR-STR-01:** Subscribe, acknowledged state, replay, explicit replay-complete boundary, live phase, reconnect and unsubscribe are observable.
- **BR-STR-02:** Duplicate, out-of-order, late and gap conditions have defined handling; event and receive timestamps remain available.
- **BR-STR-03:** Buffers are bounded and backpressure policy is visible; overload cannot silently drop market-driving events.
- **BR-STR-04:** Shared subscription ownership is reference-counted or otherwise explicit; cancelling one consumer preserves the others.

### BR-MKT — trading compositions and deployment

- **BR-MKT-01:** The default Book/BMS composition runs unchanged under regression and comparability checks.
- **BR-MKT-02:** A complete non-Book composition can be validated, simulated and deployed without fake default-policy records.
- **BR-MKT-03:** Every command binds venue, account, role, instrument identity, adapter capability and credential; revocation cannot retarget another account.
- **BR-MKT-04:** Intelligence/model version and consumer binding are explicit; shadow output cannot become production command input silently.
- **BR-MKT-05:** Handover records readiness, predecessor state, unknown orders, positions/residuals, command owner, approval, reconciliation and retirement/rollback.
- **BR-MKT-06:** A no-trading-outcome path is valid; architecture validation must not require profitable or any trading result.

### BR-PLC — placement and continuity

- **BR-PLC-01:** Preflight reports environment, runtime, dependencies, CPU/GPU, provider entitlement, quota, credentials and data locality before dispatch.
- **BR-PLC-02:** A local file sent to a remote worker is staged as an authorized portable artifact or refused before execution.
- **BR-PLC-03:** UI disconnect, coordinator failure, worker failure and preemption have distinguishable effects and recovery.
- **BR-PLC-04:** Restore is verified on disposable state using identities/hashes/lineage before work resumes.
- **BR-PLC-05:** Headless and CLI paths have semantic parity with GUI invocation and expose progress/cancel/result resolution.

### BR-SKL — skill lifecycle and test strength

- **BR-SKL-01:** Skill authoring, evaluation, installation, activation and grant are distinct.
- **BR-SKL-02:** Evaluation includes desired activation, ambiguous requests, neighbor-specialist non-activation, side effects and repeated behavior; author/model-judge claims are not self-verifying.
- **BR-SKL-03:** Mutation testing evaluates whether tests detect small semantic code changes; it does not create requirements or certify trading/architecture quality.
- **BR-SKL-04:** On Windows, current mutmut requires WSL/fork support; any run is isolated from the shared worktree and preserves baseline, scope, survivors/equivalents/invalids/timeouts/errors and raw logs.

## 6. Pass-I scenario families

Each scenario includes the minimum oracle expected later. IDs are stable within this package.

| ID | Scenario / high-risk sequence | Primary observable oracle |
|---|---|---|
| P1-CAP-001 | Install valid headless package; discover operation through catalog, CLI, node and app export | Same owner/version/schema/effects; no UI required |
| P1-CAP-002 | Install package with duplicate ID or incompatible host version | Activation refused; prior index byte/semantic identity retained |
| P1-CAP-003 | Install succeeds, activation fails migration | Installed/active states differ; rollback or precise recovery |
| P1-CAP-004 | Activate package while app-use session is open | Existing tool/grant set unchanged until explicit re-grant |
| P1-CAP-005 | Uninstall provider used by a composite and waiting run | Dependants named; pinned run resolves old instance or stops explicitly |
| P1-CAP-006 | Export/copy app package containing local paths, chat links and credentials | Secrets/private paths removed; required bindings declared |
| P1-OP-001 | Invoke one pure operation through direct, CLI, node and app doors | Equivalent semantics/errors/provenance, allowing presentation differences |
| P1-OP-002 | Upstream succeeds but acknowledgement is lost | Unknown/reconcile; no blind duplicate external effect |
| P1-OP-003 | Job produces one artifact then worker dies | Non-success terminal/unknown plus labelled partial artifact inventory |
| P1-OP-004 | Cancel queued, running, non-cancelable and already-complete jobs | Stable, race-safe result for each state |
| P1-OP-005 | Artifact expires between job completion and consumer read | Explicit expiry and recovery; no fabricated empty result |
| P1-WF-001 | Execute selected valid subgraph on a messy storyboard | Non-selected notes/nodes do not run |
| P1-WF-002 | Connect incompatible semantic types with shape-compatible JSON | Validation refuses semantic substitution |
| P1-WF-003 | Join 3×2 inputs using zip/keyed/Cartesian | Declared cardinality and missing/duplicate key policy |
| P1-WF-004 | Nested subflow calls parent under bounded-cycle policy | Bounded completion or stable cycle-budget refusal |
| P1-WF-005 | Layout/display name changes without semantic change | No invalidation/recompute |
| P1-WF-006 | Transform/provider version changes while run is waiting | Waiting run stays pinned; new run uses new version |
| P1-WF-007 | Overlapping schedule fires after slow prior run | Declared skip/queue/coalesce/parallel behavior; dedupe key recorded |
| P1-SES-001 | Workflow, strategy and ML sessions run concurrently | Context, grants, histories and targets remain isolated |
| P1-SES-002 | Close tab/window and reconnect to session | Session context restored independent of tab identity |
| P1-SES-003 | App-use requests implementation edit | No edit; typed change request can be handed to authoring |
| P1-SES-004 | Nested component asks composite app-use for authoring/trading scope | Host denies; no permission union or prompt self-grant |
| P1-SES-005 | Retrieve old discussion mentioning another account | Citation does not retarget current command |
| P1-SES-006 | Specialist produces result behind one copilot surface | Specialist identity/ownership/evidence preserved |
| P1-DATA-001 | Two providers disagree for same field/window | Separate attributed values/warnings; no silent merge |
| P1-DATA-002 | Same ticker exists on two venues/currencies | Distinct instrument identities, units and targeting |
| P1-DATA-003 | Historical provider revises old data | Old run unchanged; new run and diff link source revisions |
| P1-DATA-004 | Preview row cap reached versus true empty result | Truncation distinct from empty/unavailable/denied |
| P1-DATA-005 | Heterogeneous recipe aligns timezones/calendars and sparse data | Alignment policy, exclusions and leakage checks recorded |
| P1-DATA-006 | Train two model/MIS versions on same pinned recipe | Distinct weights/evaluations/consumer binding; side-by-side comparison |
| P1-DATA-007 | GPU job reports success but weights upload is missing/truncated | Run not promotable; completeness/hash failure visible |
| P1-DATA-008 | Non-trading clustering/report artifact is produced | Catalogued/reusable without bot or trading fields |
| P1-STR-001 | Replay hands over to live | Explicit phase boundary/cursor and provenance on every event |
| P1-STR-002 | Disconnect causes duplicates and a gap | Dedupe identity plus surfaced/replayed gap; no false continuity |
| P1-STR-003 | Slow consumer fills bounded buffer | Declared block/drop/spill/disconnect policy and loss evidence |
| P1-STR-004 | Two consumers share feed; one cancels | Remaining consumer continues; subscription ownership correct |
| P1-STR-005 | Replay event reaches trading-capable consumer | Replay provenance prevents live-command interpretation absent explicit policy |
| P1-MKT-001 | Run current default Book/BMS composition | Regression oracle preserves accounting/command semantics |
| P1-MKT-002 | Run complete non-Book alternative | No dummy Book/BMS; own policy and comparable conserved measures only |
| P1-MKT-003 | Optional MIS absent, shadow and active variants | Each mode explicit; no silent activation or mandatory narrowing |
| P1-MKT-004 | Same symbol, two brokers/accounts, one credential revoked | Every command stays explicitly targeted; other account not substituted |
| P1-MKT-005 | Flat/stopped sequential handover | Exactly one command owner before/after recorded transition |
| P1-MKT-006 | Predecessor has known residual position | Handover records/handles residual; does not assert flat |
| P1-MKT-007 | External order outcome unknown during handover | Reconcile/manual block; no automatic retry or new-owner assumption |
| P1-MKT-008 | New owner fills, then software rollback requested | Rollback cannot unfill; evidence/positions reconciled |
| P1-MKT-009 | Old process restarts after ownership transfer | It cannot regain command authority from stale local state |
| P1-MKT-010 | Two intelligence versions claim same production role | Arbitration/consumer pin required; refuse ambiguous writers |
| P1-PLC-001 | Missing local GPU and remote entitlement | Preflight refuses before scheduling/cost |
| P1-PLC-002 | Local path supplied to remote worker | Stage as content-identified artifact or refuse |
| P1-PLC-003 | Interrupted staging or symlink/path escape | No partial/unauthorized read; clean resumable/refused state |
| P1-PLC-004 | Laptop/UI closes while remote job continues | Server-owned run continues; reconnect observes authoritative state |
| P1-PLC-005 | Coordinator fails while worker completes | Reconcile completion without duplicate run |
| P1-PLC-006 | Restore backup with missing blob or stale index | Verification fails; state not resumed as healthy |
| P1-APP-001 | App B consumes App A saved artifact | Content/version/authorization resolved without private import |
| P1-APP-002 | App B calls App A exported operation | Meaning/cardinality/timing/effects/errors/cancel/reentrancy specified |
| P1-APP-003 | Workflow coordinates multiple independent apps | Each remains independently usable; partial failure attributed |
| P1-APP-004 | Composite pins A and B sharing provider P | Shared/independent instance choice visible and version-compatible |
| P1-APP-005 | Upgrade P for A while B's old run waits | B remains pinned; no cross-instance settings leak |
| P1-APP-006 | Composite component missing/unavailable | Degraded state names missing component; no false whole-app success |
| P1-APP-007 | Widget shared parameter has display value different from identity | Identity field drives computation; label rename is harmless |
| P1-APP-008 | Shared parameter cycle/conflicting writers | Deterministic validation error, not oscillation |
| P1-SKL-001 | Draft skill passes happy prompt but steals neighbor prompt | Activation evaluation fails or scopes are corrected |
| P1-SKL-002 | Skill author/model judge marks own stub success | Independent artifact/tool oracle rejects false green |
| P1-SKL-003 | Activate new skill while old session/run is active | Existing work stays pinned; new activation is explicit |
| P1-SKL-004 | Mutation tool considered on Windows shared worktree | No run there; plan requires WSL disposable copy and clean baseline |

## 7. High-order combinations deliberately explored

The following are not reducible to pairwise parameter coverage:

1. **Waiting run × dependency diamond × single-edge upgrade × shared configured provider:** catches instance/version retargeting.
2. **Composite app-use × nested callback × authoring-capable component × newly activated package:** catches authority union and session grant drift.
3. **Replay-to-live × shared feed × one consumer cancellation × lagging second consumer:** catches lifecycle coupling and backpressure loss.
4. **External order timeout × lost acknowledgement × command-owner handover × old-process restart:** catches duplicate trading and stale authority.
5. **Remote GPU × local file × interrupted staging × missing returned weights:** catches non-portable references and false success.
6. **Provider revision × cached recipe × side-by-side model versions × historical comparison:** catches rewritten evidence and invalid comparability.
7. **Package export × private path/credential × second installation × unavailable provider:** catches leakage and misleading portability.
8. **Hybrid review × one real branch × one stubbed-success branch × aggregate score:** catches false-green completion.

## 8. Excluded or invalid combinations

- A data-only clustering study combined with a required broker order is invalid unless the study explicitly exports a separately authorized trading input; data/ML need not be a bot.
- A market-data provider identifier used as a broker/account target is invalid; those namespaces are not interchangeable.
- An app-use session editing implementation is outside permitted behavior; the valid route is a change-request artifact to authoring.
- A live shared-account handover with unknown positions and no reconciliation/approval is not an acceptable success case; it must block or remain unknown.
- A persistent infinite stream represented as a completed file/job is invalid unless a bounded capture operation is explicitly requested.
- A generated combination that requires both a capability to be unavailable and its production invocation to succeed is infeasible; the valid behavior is a preflight/unavailable state.
- A mutation score for code that does not yet exist is impossible; only a future mutation plan is valid.

## 9. Evidence and oracle requirements

For later executable validation, every scenario record must state environment, revision, seed/input identities, command or interaction, raw output/log location, exit/result status, and evidence classification. Static reasoning against architecture is not execution. Mocked/stubbed success proves only the mock boundary. A UI screenshot proves a visible state, not backend correctness, entitlement, production reliability, or data accuracy.

## 10. Pass-I coverage holes to carry forward

- Exact public QMX contract owners and state transitions are unknown until the candidate is read.
- Current QMA runtime tests at `270e992` were blocked by an invalid virtual environment; source inspection is not execution.
- Whole-system QML→QMB→QMN behavior, live/demo broker behavior, GPU execution and backup/restore remain unexecuted.
- Current repository support for product sessions, app instances, durable jobs, stream ownership, composite dependency resolution and package migrations must be inspected rather than assumed.
- Alternative non-Book accounting/comparability policy and non-flat/unknown handover policy need explicit decisions.
- Which catalog hits are projections versus persisted Artifact Library kinds needs an explicit owner decision; this baseline does not invent kinds or stores.

---

**Freeze declaration:** Subsequent files may cite this baseline, add candidate-specific cases, or report unsupported transitions, but must not retroactively rewrite these Pass-I requirements as if they came from the proposed architecture.
