---
lens: rubric-walker
target: ARCHITECTURE-SPINE.md (QMA, 2026-08-28, status draft)
reviewer_gate: architecture reviewer gate
date: 2026-08-28
---

# Rubric Walker — QMA Architecture Spine

## Verdict

**Does not pass as-is; one revision round, mostly editor-applicable.** This is a strong spine — the divergence points that matter for epics are almost all fixed, the cut list is real law rather than a note, and the vocabulary discipline (Graph Template vs Task Graph, Quant vs Bot, journal vs ledger, `evidence_confidence` vs `promotion_confidence`) is the kind of thing that actually stops two epics from diverging. But it fails four rubric bars: **(a)** AD-21 weakens an inherited invariant (parent AD-20's migration discipline) and the backup obligation the parent explicitly hands to the application is discharged nowhere; **(b)** the daemon's own store lifecycle — schema migration, upgrade, restore — is a silent dimension, not a decision, a deferral or an open question; **(c)** the wire's network/security envelope is silent while AD-25 makes cross-machine deployment first-class from v1; **(d)** the spine asserts an operator ratification (lifting the parent's `kernel`/`plugin` vocabulary ban) that the memlog does not record.

No template comments, no empty sections, no placeholder text. All four mermaid blocks parse and are meaningful, not decorative. Rationale bloat is low for a spine this dense — the Rules are long but every clause is doing enforcement work, not narrating. Verified stack rows check out against `research/daemon-stack-options.md` (SQLite 3.51.3 at line 86; JSON-RPC 2.0 at 117; MCP revision 2026-07-28 at 134).

---

## Critical

### C-1 — AD-21 weakens inherited parent AD-20, and the daemon's own store has no migration path and no backup owner

**Where:** AD-21; Inherited Invariants row "Migrations, retention, backup discipline | parent AD-20 | AD-21, AD-23"; Deferred table.

Three failures stack here, and they compound.

**1. The inherited rule is weakened, not ratified.** Parent AD-20 reads: *"migrations run preflight checks → backup first → dry-run → migrate → verify, with a documented restore path; never in-place mutation of the only copy."* AD-21's migration rule is *"migrations run inside a daemon-held transaction preceded by a recorded journal checkpoint."* A transaction plus a journal checkpoint is not a backup, and there is no preflight, no dry-run, no verify step, and no documented restore path. The spine's own Inherited Invariants preamble says *"A local decision that would weaken one is a conflict to surface, not an override"* — this one was neither surfaced nor reconciled.

**2. The backup obligation lands on QMA and is dropped.** Parent AD-20 explicitly splits it: *"QMF provides the backup/restore/verify primitives (CT-14/CT-26); the schedule and execution are application/ops-owned."* QMA is an application. The claimed binding targets (AD-21, AD-23) cover plugin migrations and a retention *exemption* — neither is a backup rule. Meanwhile AD-6 makes the daemon journal the sole durable record of every mission, task ledger, quant ledger and experiment ledger in the system, and AD-25 puts it on a workstation by default. There is no rule that it is ever copied off that machine. L18 does not rescue this: it is scoped to `qmf-data`, not to the QMA store.

**3. The daemon's own schema/journal migration is unowned.** AD-21 governs *plugin* migrations only ("A PluginManifest declares ... migrations and rollback mode"). Nothing governs what happens when `qma-daemon` itself ships a new journal record shape or SQLite schema. AD-5 versions the wire; AD-21 versions plugin data; the daemon's own durable state is versioned by nobody. This is a whole owned dimension left silent, and two epics will diverge on it immediately — one will add an Alembic-style migration table, another will hand-roll a `schema_version` row in SQLite, a third will assume forward-compatible readers.

**Fix (editor-applicable):** mint **AD-27 — Daemon store lifecycle: versioning, migration, backup, restore**, and add it to `binds` under a D-row (either extend D4 or mint D23). Its Rule must, at minimum: (i) ratify parent AD-20's five-step order verbatim for any migration of the journal, the SQLite metadata store or the artifact store, with a documented restore path — the AD-21 journal checkpoint becomes an *addition* to that order, never a substitute for backup-first; (ii) stamp a `store_schema_version` on the journal and the SQLite store, with the daemon refusing to open a store whose version it does not know rather than reading it optimistically; (iii) bind QMA to the parent's already-ratified backup design (nightly, encrypted, versioned, off-machine) as the *execution* half AD-20 assigns to the application, naming the daemon store, the artifact store and the retention-exempt trajectory streams (AD-23) as its contents; (iv) leave encryption-key custody deferred exactly as the parent left it, with the revisit condition copied. Then correct the Inherited Invariants row's "Binds here" column to point at AD-27 alongside AD-21/AD-23.

No operator ruling is required — the backup design is already ratified upstream; this is discharging an inherited obligation, not minting a new one.

---

## High

### H-1 — The wire has no network or transport-security envelope, while AD-25 makes cross-machine deployment first-class in v1

**Where:** AD-5 (transport), AD-24 (last sentence), AD-25, deployment diagram.

AD-5 fixes the transport as *"JSON-RPC 2.0 over WebSocket with HTTP GET for queries."* AD-24 contributes exactly one sentence: *"The daemon authenticates before protocol bytes and never offers an unauthenticated bind."* That is the entire security envelope for the system's only cross-boundary contract. Nothing states:

- what interface the daemon binds (loopback-only vs routable) — the options sheet's D19 explicitly *rejects* "unauthenticated loopback binding with a `0.0.0.0` escape hatch", but the spine carries neither half of that ruling;
- whether the transport is TLS-protected — the options sheet D20 says "attaching over WS/TLS", the spine says `ws` with no `wss`;
- what the client credential *is* (token, mTLS, OS-user) or where it is custodied — AD-24 governs *model-provider* secrets, not wire-client credentials;
- how a remote worker or a deployed Quant on a sandbox provider reaches a daemon sitting on a home workstation behind NAT (dial-out, reverse tunnel, relay), when AD-20 forbids an external relay and the deployment diagram draws `D --> RN` and `D --> SBX` over `qma-wire`.

This is not a UI-session concern that the deferral covers: the Deferred row defers *UI presentation* and explicitly says "the wire contract (AD-5) ... is **not** deferred and binds now." AD-25 makes remote deployment "a first-class, UI-driven capability of the wire contract from v1." So v1 ships a contract that crosses machines with no stated network posture. Two epics will diverge on the first day — one builds `127.0.0.1` + a local token file, another builds a public WSS listener with a bearer token, and neither is wrong against this text.

**Fix (editor-applicable):** extend AD-5's Rule with a transport-posture clause and AD-24 with the matching custody clause: the daemon binds loopback by default; any non-loopback bind requires TLS (`wss://`, HTTPS for queries) and is an explicit, recorded operator configuration, never a default or a flag default; every client authenticates with a credential resolved through the Credential Broker (AD-24) before protocol bytes, and an unauthenticated or plaintext non-loopback bind is a hard startup refusal rather than a warning; the reachability mechanism for remote workers (dial-out from the remote to the daemon vs inbound to the daemon) is named as the decided direction, with the provider-specific plumbing riding the already-deferred sandbox-vendor row. If the reachability direction is genuinely open, it belongs in **Deferred with a revisit condition**, not in silence.

### H-2 — `PluginManifest` and the plugin context type have no owning package, and AD-2's default-deny makes every candidate home illegal

**Where:** AD-1 (port list), AD-2 (diagram + default-deny), AD-21, AD-24, Structural Seed.

AD-21 names `PluginManifest` and *"a scoped plugin context"*; AD-24 names *"the hook and plugin context type."* Neither is in AD-1's port list (MemoryProvider, ModelDeployment, ExecutionEnvironment, KnowledgeSource, ToolAdapter, ComputeProvider, ContextCompiler), neither appears in the Structural Seed's `qma-core/src/qma/core/` tree (`ontology/`, `ports/`, `refusals/` only), and the seed puts `plugins/` inside `qma-daemon/src/qma/daemon/`.

AD-2 then closes the trap: the diagram draws `PLUGIN --> WIRE` and `PLUGIN --> CORE` and states *"an edge not drawn here is default-deny until ratified in this spine."* So a plugin author cannot import the manifest or context type from `qma-daemon` without violating AD-2, and cannot import it from `qma-core` because `qma-core` does not define it. Every desk plugin in the Structural Seed (`research-corpus/`, `analysis-backtest/`, `dev-factory/`, `trading-readonly/`, `pm-coordination/`) hits this on its first line of code.

Same gap for the `HookResult` tagged union (AD-10) and the registration signatures (`register_tool`, `register_hook`, …) that plugins must type against.

**Fix (editor-applicable):** in AD-1, add the plugin contribution surface to `qma-core`'s definitions — `PluginManifest`, the `PluginContext` protocol carrying the cardinality-typed registration methods, `HookEvent`/`HookResult`, and the `credential_ref` string type AD-24 requires the context to expose. Add a `plugins/` (or `extension/`) directory beside `ports/` in the `qma-core` seed tree. State that `qma-daemon` *implements* the context and owns the loader, while `qma-core` *defines* it — the same definitions-vs-runtime split the paradigm already uses everywhere else. AD-2's diagram then needs no new edge, which is the tell that this is the right home.

### H-3 — AD-15's eligibility rule contradicts AD-15's stated Prevents

**Where:** AD-15.

AD-15 declares it prevents *"a silent capability downgrade breaking the context budget."* Its Rule then says: *"`ModelClass` ... is a pure cost and difficulty tier. Eligibility is encoded once: the request's `needs` flags (tools, vision, reasoning_effort, parallel_tool_calls) plus `min_context_tokens` are the **sole** eligibility input."*

Read literally, `ModelClass` is excluded from eligibility. A `REASONING_HIGH` request whose `needs` are satisfiable by a `FAST_CHEAP` deployment has no rule stopping the router from placing it there — which is precisely the silent capability downgrade the AD claims to prevent. The `NoEligibleDeployment` refusal only fires when *no* deployment satisfies the flags, so under the literal reading it can barely ever fire. The intent is obvious (class selects the pool, `needs` filters within it) but the spine says the opposite, and an epic implementing the sentence as written ships the bug.

**Fix (editor-applicable):** rewrite as a two-stage rule — *the requested `ModelClass` selects the candidate pool (the deployments registered under that class, and only those); within that pool, the request's `needs` flags plus `min_context_tokens` are the sole eligibility filter; the router never crosses class boundaries in either direction, and an empty filtered pool returns `NoEligibleDeployment` naming the class and the unmet constraint.* This keeps "eligibility encoded once" true of the filter while restoring the class as a hard boundary.

### H-4 — The parent's `kernel` / `plugin` vocabulary ban is overridden on a ratification the memlog does not record

**Where:** Consistency Conventions (Naming row); Vocabulary table last row; Inherited Invariants last row.

The parent spine's Naming convention reads: *banned vocabulary honored (no "kernel", "plugins", "engine" for backtesting, "exam")* — `kernel` and `plugins` are banned generally there, with only `engine` scoped to backtesting. The QMA spine overrides both, three times, each tagged as settled: *"the parent's banned vocabulary is honored **except `plugin` and `kernel`**, deliberately adopted for the agentic layer (D1, D3, operator-ratified 2026-08-28)"*, and the Vocabulary row *"Plugin / RLM kernel | the two parent-banned words QMA adopts."*

`.memlog.md` records no such ruling. The closest lines are (15) *"engine/kernel banned for QMB"* — which restates the ban in a narrower form than the parent actually wrote, and is the reviewer's own paraphrase, not an operator ruling; and the D1/D3 decision lines (36, 37), which are operator ratifications of the *paradigm* and the *daemon language* and happen to contain the words. Ratifying a decision that uses a word is not ratifying the lifting of a ban on it.

This matters beyond pedantry: the spine's own Inherited Invariants preamble says a decision that weakens an inherited item is *"a conflict to surface, not an override"*, and the operator's meta-ruling reserves **vocabulary he cares about** as one of the few categories that must still reach him. Vocabulary is exactly the category the ban lives in. The words are also now load-bearing — `plugin` is in the package layout, the manifest name, five directory prefixes and D16; retracting later is expensive.

**Fix (needs the operator):** downgrade the three claims from `operator-ratified 2026-08-28` to an explicit surfaced conflict — a one-line entry in the review packet reading *"the parent bans `kernel` and `plugins`; QMA proposes adopting both for the agentic layer only, with `engine` staying banned for backtesting and `exam` banned outright; ruling requested"* — and hold the tag until he rules. If he ratifies, record the ruling as a `(decision)` line in `.memlog.md` before restoring the tag. Do not silently keep the current wording: it is the one place in the spine where a provenance claim is not backed by its cited source.

### H-5 — Desk consolidation is deferred while desk identity is made permanent and load-bearing

**Where:** Deferred row "Desk consolidation (five desks vs three vs two)"; AD-7; AD-1; AD-8; AD-9.

The Deferred row's rationale — *"roles are settled, desks are presentation"* — directly contradicts AD-7, which says *"Desk is the organizational and workspace unit; Profile is presentation only and may collapse desks."* One of the two is wrong, and the disagreement is not cosmetic, because between them the ADs make `desk` permanently structural in four places:

- AD-7: `ActorId` is `quant:<desk_slug>/<quant_slug>`, *"operator-minted, stable, never reused"*;
- AD-1: plugin ids and ledger views are desk-prefixed (`research-*`, `trading-*`, `dev-*`, `analysis-*`, `pm-*`), with five plugin directories seeded;
- AD-8: memory is *"scoped per desk and role"*;
- AD-9: ledger views are indexed by desk and *"ledger names are desk-scoped."*

So a later consolidation from five desks to two would rename every minted `ActorId` (which the spine says can never be reused), re-key memory scopes, and re-prefix plugin packages. The deferral is written as if it were free; it is not, and an epic builder reading only the Deferred row could reasonably treat `desk_slug` as provisional and skip it in an id.

**Fix (editor-applicable):** correct the Deferred row's rationale to match AD-7 (*"roles are settled; **Profile** is presentation and may collapse desks for display"*), and add one clause to AD-7's Rule: *a desk consolidation is a Profile-level collapse only; it never renames or retires an existing `desk_slug`, `ActorId`, plugin prefix, memory scope or ledger index key, and no minted `ActorId` is ever rewritten.* That makes the deferral genuinely free and closes the divergence.

---

## Medium

### M-1 — AD-10's universal before/after rule is violated by AD-10's own v1 set

**Where:** AD-10.

The Rule says *"**Every daemon-owned primitive ships with its own before/after hook events**; a primitive added without them is incomplete."* The enumerated v1 registry then ships almost no pairs: `task_created` has no `before_`; `subagent_spawn`, `graph_transition`, `env_create`, `env_remove` have neither prefix; `message_send`, `before_ledger_append`, `before_memory_write`, `before_skill_write` have no `after_`; `agent_stop` has no `agent_start`. Only `before_tool`/`after_tool` and `mission_start`/`mission_complete` pair.

Since the registry is *closed-and-addable*, a builder adding a primitive faces a genuine fork: follow the letter (mint two events, which requires a ratified registry addition) or mirror the shipped set (mint one). Two epics will answer differently, and the rule as written also declares v1 itself incomplete.

**Fix (editor-applicable):** restate the rule to match what the ratified set actually encodes and what the operator's standing principle asks for (memlog line 30: deterministic guards must be able to *stop* an agent) — *every new daemon-owned primitive ships at minimum a `before_<verb>` gate event, plus an `after_<verb>` wherever the outcome is observable and worth intercepting; the sixteen events above are the ratified v1 set and are complete as listed.* This preserves the enforcement intent (nothing ships ungated) without declaring the shipped registry defective.

### M-2 — Six `P-*` citations resolve to nothing inside this document

**Where:** Design Paradigm (`P-3`), AD-10 (`P-2`), AD-12 (`P-5`), AD-22 (`P-9`), AD-16 (`P-10`), AD-23 (`P-12`), Vocabulary (`P-5`).

`P-9 binds` is the entire justification clause opening AD-22's Rule, and `P-10` carries the capability-ladder ordering. The spine never says what `P-` is. It resolves to the numbered sections of `inputs/packet/QMX_AGENTIC_ARCHITECTURE_PACKET_v0.1/01_QMX_CONSTITUTION.md` (§2 deterministic infrastructure, §3 QMX owns its contracts, §5 extensibility, §9 self-improvement gated, §10 lowest-level capable environment, §12 observability is not the ledger) — but nothing in the Inherited Invariants table, the frontmatter `sources` list or the conventions establishes that mapping. Every other citation class in this spine (`L*`, `DEC-*`, `parent AD-*`) is grounded; this one is not, and an epic builder cannot check a rule against a reference it cannot resolve.

**Fix (editor-applicable):** add a line under the Inherited Invariants heading — *"`P-N` cites section N of the packet constitution (`inputs/packet/QMX_AGENTIC_ARCHITECTURE_PACKET_v0.1/01_QMX_CONSTITUTION.md`), an input rather than a ratified law; where a `P-` and an `L-` disagree, the `L-` governs"* — and add the six cited sections as rows in the Inherited Invariants table with their one-line content, so the reader never has to open the packet to check a rule.

### M-3 — Stack table: one row marked `[UNVERIFIED]` that the research verified; the one v1-load-bearing row genuinely unpinned

**Where:** Stack table.

`Hindsight (deferred first memory backend) | [UNVERIFIED]` is wrong — `research/memory-providers.md:93` pins it: `ghcr.io/vectorize-io/hindsight:0.4.9`, with the Postgres 14+ / pgvector dependency the spine's AD-18 already cites. The spine's own stack preamble promises a verified source is used where one exists.

Separately: `Docker (default worker isolation) | [UNVERIFIED]` is the only unpinned row that v1 actually depends on. AD-17 makes Docker-per-worker the default execution environment and AD-14 puts the RLM kernel inside a Docker container; the other three unpinned rows (OTel, Hindsight, OpenCodex) are deferred or adapter-side. Leaving it unpinned is honest under the spine's own rule but is a live gate item, not a footnote — no research companion studied it.

**Fix (editor-applicable):** set the Hindsight row to `0.4.9 (research/memory-providers.md, verified 2026-08-28)`. For Docker, either verify and pin the Engine version now, or move it to an explicit line under the Stack table naming it as the single v1-load-bearing unpinned dependency to be verified at the implementation gate — so it is a tracked item rather than a row that reads like the deferred ones.

### M-4 — AD-24 names a Windows-only secret store as the rule, against the parent's planned Linux workstation migration

**Where:** AD-24; AD-15; parent Structural Seed ("operator workstation Windows 11 → planned Linux").

The paradigm states the house rule: *"every third-party thing sits behind a QMX-owned interface (P-3, L10)."* AD-24 and AD-15 both name Windows Credential Manager directly as where credentials resolve from. The Credential Broker is named as the port, so the intent is right, but the text reads as a fixed rule rather than as a first backend — and the parent spine's deployment seed plans a Linux workstation. An epic will hardcode the Windows API into the broker rather than behind a backend, and the migration the parent already declared breaks it.

**Fix (editor-applicable):** in AD-24, restate as *"the Credential Broker resolves references from an OS secret store behind a backend interface; Windows Credential Manager is the first and only v1 backend (L34, the operator's existing custody), and a second backend is admitted when the host OS changes"* — mirroring exactly how AD-18 treats Hindsight and AD-15 treats OpenCodex. One sentence, and the pattern is already the spine's own.

---

## Low

### L-1 — The container diagram places the Agent Runtime inside the daemon; AD-14 places the RLM kernel in the worker's container

**Where:** Structural Seed, system-containers mermaid (`RT["Agent Runtime: Dialogue or RLM"]` inside `subgraph DAEMON`); AD-14.

AD-14 says the RLM Runtime is *"a persistent Python kernel inside the worker's Docker container, a typed `host_request` bridge."* The diagram draws the Runtime — both implementations — inside the daemon box, which reads as the RLM kernel living in the daemon process. A reader building from the diagram gets the isolation boundary wrong.

**Fix (editor-applicable):** split the node, or annotate it — e.g. `RT["Agent Runtime: Dialogue (in-daemon) or RLM (supervises a kernel in the worker container)"]`, and draw the `host_request` bridge as an edge from the Docker workers node back to `RT`. One label change plus one edge.

### L-2 — AD-8's crossing-rule column says "id reference" where the conventions mandate `_ref`

**Where:** AD-8 table (Mission / Task Graph row, "Crossing rule" = `id reference`); Consistency Conventions.

The conventions are explicit: *"cross-references carry a `_ref` suffix, never `_id` — the suffix is what says reference rather than join."* The AD-8 table then uses "id reference" for the Mission/Task Graph row and "ref only" for Artifacts, in a table whose whole purpose is to fix how state crosses ownership boundaries. Small, but this is the exact table an epic reads when deciding a field name.

**Fix (editor-applicable):** change the Mission / Task Graph crossing rule to `_ref` only, matching the other five rows and the convention.

---

## Checked and clean

Recording these so the next lens does not re-walk them.

- **Levels below are fixed.** The divergence points an epic set actually needs — package boundaries and cardinality (AD-1), dependency direction with default-deny (AD-2), the wire envelope and compatibility law (AD-5), the one-journal/one-writer/one-clock law (AD-6), the state-ownership table (AD-8), hook precedence with fail-closed timeouts (AD-10), compilation law for graph templates (AD-13), the no-execution-tool registry prohibition (AD-16), UNKNOWN-is-mandatory (AD-17) — are all stated as enforceable rules with named refusals, not as preferences.
- **`Prevents` clauses generally hold.** Spot-checked AD-1, AD-6, AD-9, AD-10, AD-13, AD-16, AD-17, AD-20, AD-22, AD-25: in each, the Rule contains a mechanism that would actually fire (a hard startup error, a registry-level absence, a typed refusal, a refused completion). AD-15 (H-3) is the exception found.
- **Deferred rows carry live revisit conditions** and none of the remaining ones leaves a v1 unit undefined — the memory backend, knowledge indexing, evaluation gates, sandbox vendors, external A2A transport and RLM-beyond-Analyst all sit behind contracts that ship complete. The one deferral with a real edge (desk consolidation) is H-5; the browser-stack deferral is survivable because no browser tool ships in v1, though AD-25's "single computer-use agent" on the Windows VPS sits close to that line and is worth a sentence at implementation time.
- **Brownfield ratification is otherwise sound.** L10, L17, L27, L31, L33, L34, L35, L36, L38, L39 and parent AD-7/8/9/10/11/16/18/19/21 are each carried forward with a named binding target, and AD-16's registry-level execution-tool prohibition and AD-25's live-boundary clause are *stronger* than the inherited minimum rather than weaker. The two weakenings found are C-1 (parent AD-20) and H-4 (parent naming convention).
- **Verified stack rows are genuinely cited.** SQLite 3.51.3, JSON-RPC 2.0 and MCP revision 2026-07-28 all trace to `research/daemon-stack-options.md` (lines 86, 117, 134). Python 3.14 and the toolchain rows correctly inherit the parent's verification date rather than claiming a fresh one.
- **Hygiene.** No template comments, no `TODO`/`TBD`/placeholder tokens, no empty sections. All four mermaid blocks parse. `binds: [D1..D22]` reconciles exactly with the Capability → Architecture Map. Rationale bloat is minimal — the length is carried by enumerated law, not by justification prose.
