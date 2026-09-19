# Journey and failure-coverage register

> Process update: use `10-STAGED-PROCESS-AND-REVIEW-CONTRACT.md` for the Grok → Codex → Grok handoff and the latest delegation rules. Historical evidence is unchanged.

These are **proposed architecture probes and future acceptance journeys**, not a claim that the software already supports them. `J01`–`J24` are handoff-local IDs. The original audit's `RECON-SCN-*` IDs and reports remain unchanged. Grok may refine, split and add journeys; preserve traceability rather than mechanically implementing one feature for every row.

## Four decisive proofs

1. Two materially different trading compositions pass through honest evaluation and deployment-configuration contracts, with default-system regressions preserved (`J03`, `J10`).
2. A non-trading dataset/ML experiment completes without a fake bot, Book or mandatory trading deployment (`J06`, `J13`).
3. An app-use session produces a scoped change request, and a separate authoring session develops v2 without mutating v1 or broadening authority (`J01`, `J02`).
4. A new user-authored capability is discovered, tested and reused through supported interfaces, including another installation, without recurring core edits (`J08`, `J09`, `J12`, `J24`).

These are design tests and later authorized implementation goals. Architecture diagnostics may use small isolated fixtures. They do not authorize connecting accounts, placing trades, deploying services or running paid GPUs.

## Journey records

### J01 — App-use result → authoring v2

**Goal:** Inspect an app result, query its saved execution or specialist, create a change request and develop v2 in a separate session.

**Required context:** Installed app/version; result and run refs; permitted app operations; independent authoring scope.

**Observable result:** Scoped change-request artifact; new candidate lineage; v1 untouched.

**Failure probes:** App content asks for extra tools; stale result; same-name app; concurrent v1 run; unauthorized source edit.

**Trace source:** RECON-SCN-01.

### J02 — Concurrent session isolation

**Goal:** Work on a workflow, a strategy and an ML experiment concurrently; resume the chosen conversation after reconnect.

**Required context:** Three product sessions; profiles; context revisions; explicit object/account/environment targets.

**Observable result:** Separate histories and runs; deliberate cross-session retrieval with provenance.

**Failure probes:** Tab switch; stale context patch; shared memory leak; expired credentials; command replay after reconnect.

**Trace source:** RECON-SCN-02.

### J03 — Two genuinely different trading systems

**Goal:** Evaluate the existing Book/BMS system and an alternative without fake Book/BMS or compulsory MIS semantics.

**Required context:** Pinned input release and evaluation protocol; distinct declared policy/code/configuration identities.

**Observable result:** Comparable results only where meanings align; explicit non-comparable fields; regression evidence for default.

**Failure probes:** Alternative rejected solely for missing Book fields; dummy compatibility rows; incompatible risk units; hidden runtime assumptions.

**Trace source:** RECON-SCN-03.

### J04 — Two intelligence/model versions

**Goal:** Run v1 and v2 in shadow, or for explicitly different active consumers, without two writers claiming one role.

**Required context:** Model/weights/config/data identity; consumer binding; source stream and deployment.

**Observable result:** Separate outputs, comparisons and activation record.

**Failure probes:** Stale values; unsupported state restore; shadow output used as production; conflicting bindings.

**Trace source:** RECON-SCN-04.

### J05 — Multiple brokers and accounts

**Goal:** Aggregate authorized reads while execution remains explicitly targeted at the right adapter, broker and account.

**Required context:** Broker technology; venue/account/role; instruments; credentials; data provider; app/system instance.

**Observable result:** Per-account command/evidence scope and attributed aggregate views.

**Failure probes:** Same symbol on two venues; stale dashboard filter; netting/shared-account conflict; one credential revoked.

**Trace source:** RECON-SCN-05.

### J06 — Point-in-time data recipe

**Goal:** Build a dataset from prices and non-price facts, preserving past releases after provider/configuration changes.

**Required context:** Sources/revisions; event and known-at times; historical entity mapping; units; transformation/split recipe.

**Observable result:** Pinned dataset release with reproducible lineage and quality report.

**Failure probes:** Revision; stale sector membership; future leakage; inconsistent currency; missing release; provider returns different semantics.

**Trace source:** RECON-SCN-06.

### J07 — GPU and remote placement

**Goal:** Run the same supported model job locally or on authorized remote GPU infrastructure after real preflight.

**Required context:** Compute requirement; entitlement; image/dependency compatibility; data transfer permission; budget.

**Observable result:** Job handle, selected environment, logs, checkpoint and returned artifacts.

**Failure probes:** No GPU; no subscription; revoked key; preemption; image mismatch; insufficient memory; interrupted upload.

**Trace source:** RECON-SCN-07.

### J08 — Install into another QMX installation

**Goal:** Export an extension/mini-app and install it using the recipient installation’s own settings and credentials.

**Required context:** Package/version; dependencies; requested capabilities; migrations; compatibility declaration.

**Observable result:** Usable installed instance and attributable activation outcome, with no author-private data.

**Failure probes:** Partial install; incompatible schema; missing dependency; secret/transcript leak; uninstall with dependants.

**Trace source:** RECON-SCN-08.

### J09 — Direct/tool/CLI/node parity

**Goal:** Invoke one operation through supported direct, tool/CLI and node paths with equivalent deep semantics.

**Required context:** Same typed input/configuration; caller scope; execution environment; expected outputs.

**Observable result:** Equivalent meaningful results/refusals and explicit run provenance where each mode requires it.

**Failure probes:** Shell quoting/injection; missing CLI; differing defaults; duplicate side effect; log lost on reconnect.

**Trace source:** RECON-SCN-09.

### J10 — Sequential system rollout

**Goal:** Develop/test a replacement, validate demo/shadow behavior, then perform deliberate stopped/flat handover.

**Required context:** Old/new deployment and policy versions; account scope; position/order reconciliation; approval.

**Observable result:** New responsible runtime and retained old evidence with an explicit rollback/retirement path.

**Failure probes:** Unknown order; non-flat predecessor; lost supervisor; old process resumes; rollback after actual fills.

**Trace source:** RECON-SCN-10.

### J11 — Skill creation and evaluation

**Goal:** Create a skill, test expected and unwanted activation, save a candidate and register a validated revision.

**Required context:** Skill/dependencies/tools; cases and expected outputs; reviewer/verification policy; version.

**Observable result:** Versioned evaluation and registration result; older installed skill remains recoverable.

**Failure probes:** Self-granted permissions; judge-only false pass; same model writes tests and claims certainty; neighbor skill stolen.

**Trace source:** RECON-SCN-11.

### J12 — App-to-app capability reuse

**Goal:** App B invokes app A’s exported data/operation without controlling its screen; preserve compatible versions.

**Required context:** Exported contract; dependency lock; installed instances; permission and data scopes.

**Observable result:** Attributed cross-app execution and dependency/update plan.

**Failure probes:** Breaking upgrade; removed provider; partial migration; circular dependency; deadlocked call.

**Trace source:** RECON-SCN-12.

### J13 — Non-trading ML/data study

**Goal:** Transform heterogeneous data, train/evaluate a model and publish a dataset/model/report with no bot.

**Required context:** Input recipe; model/feature definitions; split protocol; compute; evaluation criteria.

**Observable result:** Research artifact and diagnostic evidence; no fabricated Book, QML graduation or QMN requirement.

**Failure probes:** Task forced into trading schema; leakage; model mismatch; failed experiment described as successful.

**Trace source:** New cross-domain probe.

### J14 — Mixed long-running research workflow

**Goal:** Research authorized sources, emit structured candidates with unknowns, author selected work, evaluate and iterate.

**Required context:** Research scope/rights; tools/skills; candidate table refs; QML/QMB capabilities; loop bounds.

**Observable result:** Cited candidate artifacts, selected executable candidates, results and honest stop reasons.

**Failure probes:** Unstated exits invented; inaccessible source; duplicate candidate; runaway loop; model swap; unfinished subprocess.

**Trace source:** WF1/WF2-inspired operator scenario.

### J15 — Messy draft and selected execution

**Goal:** Arrange incomplete work; run only a valid selected portion; later parameterize and save a reusable template.

**Required context:** Draft revision; selected subgraph; required inputs; validation and user intent.

**Observable result:** Scoped execution and explicit reusable definition; unrelated notes remain non-executable.

**Failure probes:** Unresolved input; accidental whole-board run; changed dependencies; empty collection; unbounded fan-out.

**Trace source:** Operator Experimentation Board scenario.

### J16 — Parallel study and meaningful joins

**Goal:** Evaluate candidate collections and data slices with declared broadcast/zip/keyed/cartesian behavior.

**Required context:** Collection schemas/cardinality; mapping; expected joins; concurrency and cost bounds.

**Observable result:** Attributable results with completed/failed/skipped partitions and a valid join policy.

**Failure probes:** Missing branch; duplicate keys; order dependence; explosive cross-product; partial failure hidden by average.

**Trace source:** Operator fan-out/reuse scenario.

### J17 — Shared live data subscriptions

**Goal:** Two workflows and an installed app use a source stream; stop one consumer without breaking the others.

**Required context:** Subscription identity; consumers; source/adapter; quality/freshness and retention settings.

**Observable result:** Correct consumer lifetime, ordered accepted data and explicit stream health.

**Failure probes:** Disconnect; late data; repeated events; backpressure; buffer full; canceled board closes trading feed.

**Trace source:** Data lifecycle expansion.

### J18 — Persistence across crashes and restore

**Goal:** Resume durable work and reconstruct views after daemon/worker/storage interruption.

**Required context:** Authoritative stores; run/attempt/checkpoint; writer and reference integrity; backup manifest.

**Observable result:** Reconciled records and explicit missing/unknown outcomes, never guessed completion.

**Failure probes:** Partial cross-store write; corruption; disk full; orphan blob; stale checkpoint; incomplete restored reference.

**Trace source:** Cross-store lifecycle probe.

### J19 — App profile and rich view contract

**Goal:** Open a mini-app or tool view with declared context/actions; inspect selected data without changing its implementation.

**Required context:** App/profile/view spec; host grants; bound results; session/context version; mounted view.

**Observable result:** Validated rendering/actions and explicit selection context; domain operations still owner-controlled.

**Failure probes:** Unregistered component; malicious HTML/context; cross-app tool request; iframe disposal kills durable work.

**Trace source:** JSON Render/MCP Apps candidate probe.

### J20 — Provider/account reconfiguration

**Goal:** Change configured data/broker/provider settings and preflight them without silently changing old studies or trades.

**Required context:** Scoped settings revision; secrets refs; declared capabilities; effective configuration.

**Observable result:** Validated new configuration with old runs/deployments still pinned and intelligible.

**Failure probes:** Missing subscription; broker adapter unsupported; credentials invalid; environment drift; provider switch changes live semantics.

**Trace source:** Settings/provisioning scenario.

### J21 — Extension upgrade during active work

**Goal:** Install a new extension version while runs still reference the predecessor.

**Required context:** Version lock; dependency graph; active consumers; migration/rollback contract; install permissions.

**Observable result:** Safe coexistence, delayed activation or explicit refusal, with accountable state.

**Failure probes:** Conflicting singleton; removed skill; incompatible checkpoint; forward-only migration; half-activated package.

**Trace source:** Versioned extensibility scenario.

### J22 — External files/browser/computer use

**Goal:** Authoring session reads authorized local files or external sources and produces an attributable candidate.

**Required context:** Allowed paths/destinations; credentials references; external environment; source provenance.

**Observable result:** Scoped outputs and evidence; app-use authority not expanded by retrieved text.

**Failure probes:** Prompt injection; symlink/path escape; unrelated private-file retrieval; unsupported browser; external state mutation.

**Trace source:** External access scenario.

### J23 — Scheduled app/department work

**Goal:** Schedule an authorized briefing or model-monitoring workflow and inspect its results through one or more apps.

**Required context:** Trigger/timezone; workflow/version; permissions; budget; recipients; output references.

**Observable result:** Attributable scheduled runs and useful notifications; schedule distinct from agent/workflow definition.

**Failure probes:** DST ambiguity; missed/duplicate trigger; source unavailable; expired permission; notification storm; overlapping work.

**Trace source:** Daily workflow/department scenario.

### J24 — Public-interface proof of a custom contribution

**Goal:** Add a new typed operation and use it directly, as a node, in an app and from a copilot profile without core edits.

**Required context:** Extension template/SDK; operation contract; tests; package; host grants; relevant QMF interfaces.

**Observable result:** One reusable implementation, discovered through supported mechanisms with optional rich presentation.

**Failure probes:** Private import needed; hardcoded selector; schema drift; duplicated logic per door; extension bypasses validation.

**Trace source:** Core maintenance acceptance probe.


## Coverage strategy

Do not promise exhaustive testing of every Cartesian combination. Classify dimensions, use pairwise coverage for broad interaction risks, and explicitly cover higher-order combinations where account authority, external side effects, concurrent versions or recovery interact.

Dimensions include session profile; manual/agent/scheduled initiator; direct/node/app/CLI door; draft/version/installed/run/deployed state; finite/polling/streaming data; local/remote/GPU placement; standalone/shared dependency; account role and venue; deterministic/stochastic step; and fresh/stale/revoked/unknown external state.

For each selected probe, specify preconditions, initial records, action, resulting authoritative records, expected refusal/error, cleanup and what evidence would falsify the design. Derive numeric resource/latency/error tolerances from current contracts, measurements or explicit proposals, not invented universal constants.

## Common invariants to propose and test

- Session navigation is not authority or target mutation.
- Immutable run inputs remain identifiable while drafts and packages evolve.
- Side-effect retries cannot be justified solely by a lost response; reconcile uncertain outcomes.
- Semantic schemas and permissions are validated at runtime boundaries, not only in the UI.
- App documentation, skills and memory guide behavior but cannot grant authority.
- A canceled UI operation must not erase valid evidence or indiscriminately terminate shared resources.
- Private credentials and unrelated authoring context do not enter exported packages or logs.
- Data transformations preserve temporal meaning, provenance and declared gaps.
- Install/upgrade failures leave an explicit state rather than a silently half-working catalogue.
- Replay, shadow observation, broker demo and live operation retain their actual meanings; no cosmetic relabelling.
- Technical conformance and an interesting scientific result are different checks.

## UI handoff fields

For selected journeys supply: entry point, user's question, allowed commands, data displayed, component/widget needs, state transitions, progress, error/recovery affordances, context supplied to the copilot, lineage/handoff links and exit state. These describe requirements for later UX, not a finalized layout.


## September 18 independent campaign

The 24 probes above remain seeds, not an exhaustive test plan or count cap. Codex Stage B independently derives scenario families before reading Grok's solution, then expands them against the frozen design. Use `12-CODEX-SCENARIO-AND-ARCHITECTURE-CHALLENGE.md` for BDD records, high-order interactions, coverage and evidence states. Stage A still needs internal scenario reasoning; Stage B adds independence rather than doing all thinking for the designer. Do not claim architectural explanation as executed software or generated Gherkin as implemented tests.

Additional interactions to examine include multi-app dependency upgrades during a waiting run, shared-feed cancellation, app-call cycles, callback permission propagation, mixed artifact/schema versions, composite-app app-use sessions, expensive nested calls, local file references on remote workers, plugin install versus activation, and missing provider/GPU entitlement. Root outcomes and recovery should remain observable to both headless consumers and the later UI.
