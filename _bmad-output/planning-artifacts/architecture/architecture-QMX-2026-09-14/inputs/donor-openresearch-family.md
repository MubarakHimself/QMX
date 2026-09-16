# Donor mechanisms — openresearch-family

Donor family: **OpenResearch** (alphaXiv `orx`), **OpenScience** (Synthetic Sciences workbench), **Delphi** (Synthetic Sciences local MCP indexer). Official docs fetched 2026-09-14. This note extracts transferable *mechanisms* for QMA-directed strategy experimentation. **None is an adopted replacement dependency.** No donor UI, CLI, compute marketplace, literature engine, training loop, or retrieval engine is in scope.

Standing bans that bound every row: no donor engine adoption; QMA never executes the money path (paper included); QMB never imports `qmf-venue`; ordinary Python stays legal; QMF remains a toolbox; QMB is a library+CLI, never an engine.

Evidence level for donor facts: **documented-design** (official README / skill / docs / changelog). QMX homes: **documented-design** from ratified `docs/` (several QMA contracts remain `defined-unwired`).

## Compact table

| # | Mechanism | Donor source | qmx_home | status | QMX adaptation (one line) |
|---|---|---|---|---|---|
| 1 | Experiment lineage tree (stacked bushes, freeze, promote) | OpenResearch experiment tree | QMA | extend | Content-addressed `ExperimentSpec` DAG + Experiment Ledger; never git-branch-per-parameter |
| 2 | Isolated parallel arms (session + worktree) | OpenResearch parallel exploration; OpenScience workers | QMA | connect | One Worker per arm in an ephemeral `ExecutionEnvironment`; QMB process-per-run behind the single `qmb` door |
| 3 | Immutable source snapshot of the recorded commit | OpenResearch compute launch contract | QMA | extend | `ExperimentSpec.code_ref` / `environment_ref` + QMB resolved-config fingerprint; uncommitted work never runs |
| 4 | Evidence archive bound to the producing node | OpenResearch evidence-in-context; OpenScience Saved Results / study files | QMF | connect | CT-11 raw+journal + CT-32 + Experiment Ledger citations; **logs are never evidence** |
| 5 | Study budgets, kill criteria, pause / resume / halt | OpenScience Studies; OpenResearch repair/stop caps | QMA | extend | Mission/Loop budget + Routines + `continuation.*` + `JobHandle.wake`; QMB governor for resource limits |
| 6 | First-completion wait / refill loop | OpenResearch `orx exp wait --project` | QMA | connect | `JobHandle.wait` + mailbox wake; do not collapse onto QMB's generation barrier |
| 7 | Fixed run contract (same command, vary committed config/code) | OpenResearch cardinal rules 2–3 | QMB | reuse | Already one resolved run-config; QMA cites it via `resolved_config_ref` |
| 8 | Idea-queue hill-climb (one run per idea, EV rank, lessons) | OpenScience Autoresearch / `study`+`experiments` tools | QMA | connect | Plugin `graph_template` drives QMB optimize/sweeps; no `study` tool, no wandb shim |
| 9 | Corpus snapshots + cite-copy | Delphi immutable source snapshots; OpenScience literature cache | QMA | reuse | CT-44 `CorpusSnapshot` + `cite` copy-gate already law; v1 search stays literal |
| 10 | Ranked / hybrid retrieval and indexing | Delphi pgvector+BM25; OpenResearch `orx discover` | QMA | undecided | GAP-0073; optional adapter behind `KnowledgeSource`, never a Delphi/orx dependency |
| 11 | Token-budgeted context packs and handoff sessions | Delphi context-sessions; OpenScience `/handoff` | QMA | extend | ContextCompiler + pinned `snapshot_ref` + mailbox `handoff`; deterministic budget, not chat dump |

## Source-linked findings

### Family shape (what was fetched)

- **OpenResearch** — local-first workspace that turns coding agents into research agents. Official product: [openresearch.sh](https://openresearch.sh/), repo [github.com/alphaXiv/OpenResearch](https://github.com/alphaXiv/OpenResearch), skills in-repo (`SKILL.md`, `agent-skills/orx-experiment-tree`, `orx-compute`, `orx-evidence`, `orx-git`, `orx-agent-delegation`, `orx-create`, `orx-lit-review`, `orx-reports`).
- **OpenScience** — research agent + workbench. Official: [github.com/synthetic-sciences/openscience](https://github.com/synthetic-sciences/openscience), [ARCHITECTURE.md](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/ARCHITECTURE.md), [CHANGELOG v2.0.95 Studies/Autoresearch](https://raw.githubusercontent.com/synthetic-sciences/openscience/main/CHANGELOG.md), docs [llms-full.txt](https://www.openscience.sh/docs/llms-full.txt) and MDX `autoresearch.mdx` / `experiment-tracking.mdx` / `jobs.mdx` / `context.mdx`.
- **Delphi** — local MCP indexer for code, papers, datasets. Official: [github.com/synthetic-sciences/delphi](https://github.com/synthetic-sciences/delphi), `docs/architecture.md`, `docs/context-sessions.md`, `docs/atlas-integration.md`, `docs/env-advanced.md`.

These three share a research-agent loop (plan → change → run → inspect evidence → decide next) but **split the product**: OpenResearch owns the git-native experiment tree and isolated worktrees; OpenScience owns studies/budgets/compute-job recovery and a workbench UI; Delphi owns indexing/snapshots/context packs. QMX already split the same concerns across QMA (direct), QMB (run), QMF (evidence), QML (declaration).

---

### 1. Experiment lineage tree — status **extend**, home **QMA**

**Donor (OpenResearch).** A project is a *tree of experiment nodes*. The root (baseline) holds starting code and a single **run command**. Every other node is a child that inherits code and that command. Cardinal rules (`SKILL.md`, `orx-experiment-tree/SKILL.md`):

1. Never edit a node once a run has *answered* it (good, bad, or `nan`). Freeze is permanent. Repair in place only while the node is provisional (crash, OOM, missing dep — “answered nothing”). Repair cap: two consecutive no-answer runs, then ask the user.
2. The run command *and* environment are a fixed contract, identical on every node.
3. Vary committed code/config, never knobs-in-the-command or env-prefixed launches.
4. Grow **stacked bushes**, not a flat fan off the root and not a noodle chain: fan the co-equal options of *one* decision, then **promote the winner** and hang the next round off it. Before making X a child of Y, name what Y established that X builds on.

The auto-research loop is: read baseline → form one round of hypotheses → create siblings under the chosen parent → implement on each `orx/<slug>` branch → launch → per-completion decide repair / refill / promote / stop. Stop after the goal or ~3 consecutive failed/regressed runs. `orx exp desc` is a free-form node notebook.

**QMX already has.** CT-47 (`docs/contracts/ct-47-qma-experiment-spec.yaml`) is a content-addressed `ExperimentSpec` with `code_ref` (only when code changes), `resolved_config_ref` (parameter/config identity), data/environment/seed/harness refs, cost assumptions, and a **lineage DAG of CT-07 edges by fp1**. Explicit Cut: git-branch-per-parameter-mutation lineage (`DEC-0376`). The Experiment Ledger is one per Experiment, appended by the Agent holding the registering Task's `dispatch_lease` (`docs/components/qma-daemon.md` AD-9). QMB already fans co-equal parameter trials as isolated runs with `role = trial` and a generation-stepped sampler (`docs/components/qmb.md` B-8).

**Adapt, do not copy.** Keep OpenResearch's *tree-shape discipline* (one decision per bush, freeze-after-answer, promote-then-descend, repair vs new question) as QMA Mission / `graph_template` law over `ExperimentSpec` nodes. Identity stays fp1, not `orx/<slug>`. A parameter sibling is a new `ExperimentSpec` with a new `resolved_config_ref` and a CT-07 edge to the parent; a code-change child carries `code_ref`. QMB remains the only place those specs *run*. Git branches, if used at all, are an ExecutionEnvironment checkout aid for **code** mutations, never the lineage key.

**Missing:** the stacked-bush / promote / freeze-after-answer loop is not a named QMA graph primitive today (node kinds exist; no v1 `graph_template` ships — `qma-daemon.md` AD-13, GAP-0086). That is missing *function in the plugin graph*, not a missing identity model.

---

### 2. Isolated parallel arms — status **connect**, home **QMA**

**Donor.** OpenResearch: “Give each research direction an independent agent session and isolated git worktree” ([README](https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/README.md); `SYSTEM_PROMPT.md` — working directory is a private worktree). `orx-git`: one branch, one worktree owner; sibling sessions share the clone's refs but not the dirty tree; never merge/rebase a frozen node. `orx-agent-delegation`: helper gets its own worktree and transcript; cannot spawn another helper; CLI caps in-flight helpers; never hand a helper this session's checked-out branch; authorize exactly which `orx exp run` calls it may launch. OpenScience: lead delegates bounded Explore/Execute workers in parallel; workers read the lead workspace and **write only in their own**; a worker is a fresh child per Task call (Fusion persistent-worker was *removed* in v2.0.95). Compute concurrency is an admission limit, not an autonomous queue (`ARCHITECTURE.md`).

**QMX already has.** Ontology: Agent / Subagent (leaf, cannot spawn, capabilities no wider than parent) (`qma-core.md` AD-7). Task Graph `parallel_branch` + `join`; scheduler grants `dispatch_lease` and `environment_lease`; parallel workers synchronize through the graph, never chat (`qma-daemon.md:112`). `ExecutionEnvironment` default is docker-per-worker, ephemeral, **no shared dirty filesystem**; `max_in_flight` queues the rest (`CT-46`). QMB: concurrent runs are separate OS processes with isolated output directories, governor `min(cpu, memory)` (`qmb.md` B-5). QMA places **exactly one `qmb` job per environment**; QMB owns intra-node parallelism (`CT-47`).

**Adapt.** One QMA Worker (or Subagent) per co-equal experiment arm, each with its own `environment_lease` and ephemeral FS. The round's parent Task holds the `dispatch_lease` for the Experiment Ledger. Do **not** productize git worktrees, donor harness multiplex (Claude/Codex/OpenCode/Cursor), or OpenScience's Task-tool UI. Do **not** let QMA fan multiple `qmb` jobs in one environment — the door stays one job; QMB fans trials inside that job if the spec is a sweep/optimize.

**Missing:** wiring from “round of sibling ExperimentSpecs” → N Workers + one qmb door placement. Function exists on both sides; the join is missing.

---

### 3. Immutable source snapshot of the recorded commit — status **extend**, home **QMA**

**Donor.** `orx-compute`: “Each run uses an immutable snapshot of the experiment branch's recorded commit.” Launch only via `orx exp run`; the worktree is for editing. Uncommitted files are excluded. No GitHub push required. `--force` is the only way to run two jobs on one node. Backends (local, SSH, Slurm, k8s, Ray, HF Jobs, Modal, Tinker, managed OpenResearch) all receive that snapshot. `orx-create`: “Runs use an immutable archive of that local commit.”

**QMX already has.** `ExperimentSpec` is content-addressed over fp1; two identical specs collapse (`CT-47`). QMB run-id root is the resolved-config fingerprint; re-running a run id must reproduce the CT-32 fingerprint (`qmb.md` B-3, B-10). CT-11: identity of every stored artifact is fp1; append-only (`docs/contracts/ct-11-evidence-persistence.yaml`).

**Adapt.** Treat “recorded commit” as **the fingerprinted tuple the spec already names** (code_ref when code changes, resolved_config_ref always, data_ref, environment_ref, seed, harness version). A QMA launch that has uncommitted / unfingerprinted bytes is a typed refusal, same spirit as orx excluding dirty files. Do not adopt orx's tarball-of-git-commit as a second archive format, and do not adopt the donor backend catalog (Modal/Tinker/HF/OpenResearch marketplace). Agents declare a `ComputeRequirement`; they never name a vendor (`CT-46`). GAP-0075 already rejected Modal/Daytona/E2B as sandbox vendors.

**Missing:** an explicit “dirty tree / unfingerprinted bytes cannot launch” gate on `before_experiment_register` / Compute Router. That is a small extend of existing identity law.

---

### 4. Evidence archive bound to the producing node — status **connect**, home **QMF**

**Donor.** OpenResearch README: “Keep logs, diffs, files, results, and artifacts tied to the work that produced them.” `orx-evidence` goes further: **run logs are the evidence channel**; print metrics to stdout; `orx logs` is how you judge a node; status alone is not evidence. Session playbook: measured results use `<run id="…"/>` tags after actually reading the log. `orx-reports`: durable artifacts live in a project artifacts directory, grouped by topic. OpenScience: Saved Results are retained copies distinct from working files; experiment-tracking keeps objective, checks, trial outcomes, and lessons tied to concrete outputs; stages ≠ verification checks; lessons only from verified trials. Autoresearch writes `study.md`, `ideas.md`, `results.tsv`, `lessons.md` into the working folder. Compute jobs distinguish “command succeeded” from “outputs delivered” and can retry delivery without rerunning.

**QMX already has — and contradicts the donor log channel.** CT-11: only **raw archive and journal** are evidence-bearing; per-run logs are never evidence (`CT-11` invariant + `qmb.md` B-10). QMB publishes one CT-32 per run plus CT-13 journal streams; the orchestrator appends one ledger line; operational logs are AD-14 only. QMA: artifact store is content-addressed, forever, with lineage (`qma-daemon.md` store table); Experiment Ledger is the scientist notebook; `before_artifact_register` copies cited bytes. Telemetry (job logs, traces) is a separate store; a ledger entry may carry `trace_ref`, never the reverse (`qma-daemon.md` AD-23).

**Adapt.** Keep the donor *binding* (every claim names the producing spec, the CT-32, the journal stream, the artifact refs). Reject “stdout log = evidence.” QMA agents read CT-32 / journal / Experiment Ledger, not `orx logs`. OpenScience's stage-vs-check split maps onto QMA: Task state is not a verification; `before_task_complete` + deterministic verifier script is. Saved Results map onto QMA artifact registration + QMF retain-forever-if-cited, not a second Results product. Job output-recovery (retry delivery without rerun) is a Compute Router concern if remote_host ever retains files — do not copy Modal-specific recovery.

**Missing:** Experiment Ledger entries that *cite* CT-32 fingerprints and CT-13 stream ids (connect QMA ledger ↔ QMB/QMF artifacts). Function exists; the citation join does not.

---

### 5. Study budgets, kill criteria, pause / resume / halt — status **extend**, home **QMA**

**Donor.** OpenScience v2.0.95 Studies: one metric and direction, a baseline, a queue of ideas ranked by expected value, **exactly one run per idea**, verdicts with analysis and lessons, kill criteria in plain words (“1 hour OR val_loss plateaus for 500 steps”), budgets by **runs, hours, spend, or target**, Pause / Resume / Halt / Write up. Budget is agreed **per study**, never inherited. `study start` refuses once the run budget is spent (live runs count, so parallel starts cannot overshoot); refuses to share a GPU when every local GPU has a live run; dispatch failures do not consume the run budget. Steer is a standing directive that wakes the agent and survives many runs. Loop honesty: ask for more ideas when fewer than three queued; change of kind after four runs without progress; step-back review every six. Wake-ups capped per hour. OpenResearch: `orx exp wait --project` is the budget-loop primitive; repair cap; scientific stop ~3 failed/regressed runs; `orx exp wake` resumes the session on `done`/`failed`. Reproduction docs: prompt ceilings are not a substitute for account spending controls.

**QMX already has.** Mission carries budget, escalation, termination criteria (`qma-daemon.md:110`). Loop node owns `stopping_condition`, `budget`, `escalation` as node state (`AD-13`). Continuation: `agent_stop`/`block_stop` returns the Agent to the next ready Task, bounded by `registry:continuation.max_consecutive`, `continuation.budget`, `continuation.escalation_target`; exhausted budget escalates to the Quant mailbox and **never invents work** (`CT-49`, `qma-daemon.md` AD-29). Routines: `max_concurrent`, deterministic fire, machine principal. `WakePolicy` on the Quant (quiet hours, max wakes per window). JobHandle: `wait`, `wake`, `cancel`; `unknown` holds the lease until operator resolution (`CT-46`). QMB: per-run time/memory limits, governor budgets, `stop_study` / optimize resume (integration inventory). Cost assumptions live on `ExperimentSpec`; RLM fan-out has a USD ceiling.

**Adapt.** A QMA “study” is a Mission whose Graph Template is a Loop over ExperimentSpecs, not an OpenScience `study` tool. Encode kill criteria as Loop `stopping_condition` evaluated from **CT-32 / journal measures**, never from training-stdout shims. Split budgets explicitly: Mission budget (runs / wall / spend / target) is QMA; cpu/memory/time per run is QMB governor; model-token continuation is `continuation.budget`. Pause = `defer` (keep `dispatch_lease`, drop `environment_lease`). Halt = cancel in-flight JobHandles then Mission `cancelled`. Do not inherit a previous Mission's budget. Do not copy `openscience_track` / wandb shim (that path makes logs look like metrics evidence).

**Missing:** typed Mission budget dimensions (runs | hours | spend | target) and plain-word kill criteria as daemon-evaluated Loop conditions. Continuation today is Agent-run continuation, not study-run continuation — that is an **AD-sized extend** of AD-12/AD-13/AD-29, not a new product.

---

### 6. First-completion wait / refill loop — status **connect**, home **QMA**

**Donor.** OpenResearch drives a **per-completion** loop, not wait-for-all: `orx exp wait --project` returns on the first completion; re-read `orx runs` as source of truth (a run that finished while you analyzed will not be re-reported); refill the freed slot or promote/stop. Timeout means “nothing changed,” not failure. OpenScience: short runs waited inside the same turn; long runs wake the session; “Study update” batched, hourly cap.

**QMX already has.** `JobHandle.wait` / `wake` / `stream` (`CT-46`). Mailbox `WakePolicy`. QMB optimize instead uses a **generation barrier**: propose a batch, run concurrently, barrier, then condition — same seed must propose identical trials regardless of completion order; parallel `ask` without `tell` is refused for TPE (`qmb.md` B-8).

**Adapt.** Two clocks, do not merge them. QMA's *research round* may refill on first completion (OpenResearch shape) for independent sibling ExperimentSpecs (co-equal LR values, independent code forks). QMB's *adaptive sampler generation* stays barrier-synchronous so TPE is reproducible. A QMA study that *is* a QMB optimize job waits on that one qmb JobHandle, not on inner trials.

**Missing:** an explicit QMA round scheduler that treats JobHandle completions as refill ticks. Wait/wake primitives exist.

---

### 7. Fixed run contract — status **reuse**, home **QMB**

**Donor.** Cardinal rule 2–3: one run command on the baseline, inherited verbatim; never `LR=3e-4 python …`; hyperparameters live in committed files so logged summaries stay comparable.

**QMX already has.** QMB compiles exactly one resolved, read-only, fingerprinted run-config from fixed precedence layers; Book/BMS namespaces disjoint (`qmb.md` B-3). ExperimentSpec uses `resolved_config_ref` as the identity axis for parameter change (`CT-47`). QML owns the declared parameter schema; a sweep override stamps `assignment_is_canonical` false.

**Adapt.** Nothing to borrow but the slogan: *vary the spec, not the door.* QMA's `analysis-backtest` tool invokes the same `qmb` door every time. Ordinary Python research calls that bypass the orchestrator already produce no governed evidence (`qmb.md` B-4) — keep that.

---

### 8. Idea-queue hill-climb — status **connect**, home **QMA**

**Donor.** OpenScience Autoresearch pane (UI — do not copy) plus agent tools `study` (create/status/propose/start/record/drop/conclude) and `experiments` (runs/keys/series/compare). One metric, baseline first, ideas ranked by expected value, exactly one run per idea, kept vs reverted, lessons.md. Write-up reads the ledger. Default review gate: `critique` specialist reads training/eval code before the baseline. Reproduction workflow: preregister plan as a Result before trials; do not keep mutating until the number matches.

**QMX already has.** QMB optimize (TPE-class sampler, trial history from the ledger view, anti-overfit sensitivity) and sweeps (Cartesian isolated runs, aggregation is a read-time view) (`qmb.md` B-8, B-12). QMA Loop + Mission Director may propose decompositions as validated graph transitions. ReviewPolicy: `author_family != reviewer_family`, deterministic verifier, never an LLM judging itself (`qma-daemon.md` AD-10). Experiment Ledger + CT-32 comparison already cover “kept vs reverted” as reader-derived folds (QMB stores no pass/fail).

**Adapt.** QMA Research/Analysis desks *direct* the idea queue (Mission Director proposes child ExperimentSpecs). QMB *executes* trials. Ranking by “expected value” stays an Agent proposal written to the Experiment Ledger, never a hidden sampler state. One-run-per-idea is already QMB's “every trial is a first-class run.” Do not add `study`/`experiments` tools, a SQLite metrics store, or a wandb-compatible tracker. Do not copy the Autoresearch pane; UI, if any, reads QMA/QMB ledgers.

**Missing:** a plugin `graph_template` for Hypothesis-Test-Learn-Mutate-Gate (named in AD-13 as arriving via plugin, not shipped). That is missing function in QMA plugins, not a missing QMB optimizer.

---

### 9. Corpus snapshots + cite-copy — status **reuse**, home **QMA**

**Donor.** Delphi: “Completed indexing runs create immutable source snapshots, so a saved context can point to the exact version it used.” Context sessions store snapshot/locator/content hashes, not unbounded transcripts (`docs/context-sessions.md`). OpenScience literature `read` downloads once into a session paper cache and returns page-addressed text; partial/scanned marked as such (CHANGELOG v2.0.96).

**QMX already has.** CT-44: `snapshot()` returns a content-addressed tree digest; a Mission pins one `snapshot_ref` at start; snapshots form a linear supersedes chain; `cite` copies bytes into the artifact store; retrieval against an uncopied snapshot is `StaleSnapshot` (`docs/contracts/ct-44-qma-knowledge-source.yaml`). Search is literal/locator, no ranking, no embedding; v1 ships no index.

**Adapt.** Keep CT-44 as-is. Delphi snapshots are the same mechanism with a vector store behind them — the store is not transferable. OpenScience paper-cache is a KnowledgeSource adapter concern, not a QMA core type.

---

### 10. Ranked / hybrid retrieval and indexing — status **undecided**, home **QMA**

**Donor.** Delphi default `quality_mode=agent`: hybrid retrieval (vector + BM25 + exact symbol + exact path + trigram), AST chunking, optional cross-encoder rerank, PostgreSQL+pgvector, MCP tools for index/search/call-graph/context-pack. OpenResearch `orx-lit-review`: main agent ranks alphaXiv keyword/embedding + OpenAlex + bioRxiv; **never delegate the retrieval loop**; difficulty-derived follow-up budget (0–2 rounds). OpenScience `literature` tool merges OpenAlex+arXiv by DOI/arXiv id/title.

**QMX already has.** KnowledgeSource port; GAP-0073 defers hybrid/semantic indexing until the corpus has an ingestible file and STRATS layout is ratified (`CT-44` gaps). RLM is an *additional* programmatic retrieval path on the Analysis desk, never the only path.

**Adapt.** If ranked retrieval is ever wanted, it enters **only** as a KnowledgeSource adapter behind CT-44, with citations still resolving to QMA-copied bytes. Do not adopt Delphi, pgvector, or `orx discover` as platform dependencies. Do not stand up a QMA database server for QMA's own stores (inherited no-database-server rule). A provider's internal index sitting behind the port is allowed the same way MemoryProvider backends are (`qma-daemon.md` AD-18). Literature search (alphaXiv/OpenAlex) is not a QMA experiment mechanism; if the Research desk wants it, that is a separate `research-corpus` plugin question, not this sitting's experiment spine.

**Why undecided.** GAP-0073 is already the deferred row. Promoting Delphi-shaped hybrid retrieval to v1 would need an AD; leaving literal search is legal.

---

### 11. Token-budgeted context packs and handoff sessions — status **extend**, home **QMA**

**Donor.** Delphi: build a context pack around a task and a token budget; context sessions are append-only revisions (objective, snapshot refs, accepted/rejected evidence, decisions, unresolved questions, deterministic selection manifest that grows when the budget increases rather than reshuffling); handoff creates a child with `parent_session_id` + `parent_revision_id`; concurrent writers fenced by `write_version`; expired sessions fail closed. OpenScience: `/compact`, `/checkpoint`, `/handoff` write files; project files hold details; compaction must not be the only copy of parameters. OpenResearch playbook: session worktree + `orx` as source of truth; evidence tags in chat.

**QMX already has.** ContextCompiler singleton per daemon; context is per-invocation and **never persisted** (`qma-daemon.md` store table). Memory `recall` is token-budgeted. Mailbox `handoff` kind; a handoff becomes real only when it writes a Task (`AD-20`). Task is transcript-independent (intent, inputs, refs, acceptance, Task Ledger). Mission pins `snapshot_ref`.

**Adapt.** Persistable “context session” is **not** a second QMA context store. The durable objects are already Task + Experiment Ledger + artifact refs + pinned snapshot. Borrow Delphi's *deterministic budgeted selection manifest* (accepted first, rejected excluded, stable order, budget increases extend) as ContextCompiler behavior, and OpenScience's “write a handoff file of paths and decisions” as a mailbox `handoff` payload that names those refs. Do not persist the prompt. Do not copy Delphi `/v2/context-sessions` HTTP or OpenScience slash-command UX.

**Missing:** ContextCompiler algorithm for budgeted evidence packing (extend). Handoff payload schema that carries snapshot/artifact/ExperimentSpec refs (connect CT-48).

---

## Do not copy

Product surfaces and engines (ban):

- OpenResearch local dashboard (`orx up` UI), `orx` CLI as QMX's face, git-branch-per-parameter identity, managed GPU marketplace / billing, Tinker/HF Jobs/Modal/Ray as required backends, alphaXiv literature primitives as core, session playbook HTML tags, nanochat/VPO/MaxRL templates.
- OpenScience SolidJS workbench, Autoresearch pane, Ace wallet / 5.5% fee, `openscience_track` / wandb shim, `study`/`experiments` tools, Harbor adapters, scientific-capability catalog, Fusion persistent-worker (already removed upstream).
- Delphi Next.js dashboard, PostgreSQL+pgvector engine, MCP server product, Atlas graph ingestion (16 extra tools), Firecrawl hosted search, Gemini research jobs.
- Any donor “engine,” “kernel,” or foreign platform contract. QMB remains a library+CLI. QMA remains definitions + daemon + wire.

Mechanism anti-patterns (ban even as shape):

- **Run logs as the evidence channel** (`orx-evidence`) — contradicts CT-11 / DEC-0163.
- **Git branch as experiment identity** — Cut by DEC-0376 / CT-47.
- **QMA placing multiple `qmb` jobs per environment** — CT-47 single door.
- **QMA executing paper or live** — money-path deny-list / AD-28.
- **Inheriting a previous study's budget.**
- **LLM-judging-itself** as the completion gate (OpenScience critique specialist is optional; QMA ReviewPolicy is deterministic + cross-family).
- **Delegating the retrieval-ranking loop** (orx-lit-review) — if literature is ever added, the main Research agent ranks.

## What already exists

- QMA: ontology, Mission/Task Graph, leases, JobHandle wait/wake/cancel/unknown, ExecutionEnvironment isolation, ExperimentSpec + lineage DAG, Experiment Ledger, KnowledgeSource snapshots + cite-copy, ContextCompiler, Routines, continuation ceilings, mailbox handoff, analysis-backtest single `qmb` door, money-path barrier. Contracts: CT-44, CT-46, CT-47, CT-48, CT-49, CT-51. Several remain `defined-unwired` in docs.
- QMB: resolved run-config, process-per-run isolation, governor, CT-32, CT-13 journals, TPE optimize, sweeps, walk-forward, study stop/resume, ordinary-Python research path with no governed evidence.
- QMF: CT-07 lineage, CT-11 evidence persistence (raw+journal only), fp1 identity, rooms per world.
- QML: declared parameter schema and canonical assignment (the thing a child ExperimentSpec's `resolved_config_ref` points at).
- QMN / Trading Node: out of this donor family; QMA must not reach them.

## Missing wiring vs missing function

| Need | Wiring vs function | Owner |
|---|---|---|
| Stacked-bush promote/freeze loop over ExperimentSpecs | Missing **function** (plugin `graph_template` + freeze-after-answer rule) | QMA |
| Sibling arms → N Workers + one qmb job | Missing **wiring** | QMA → QMB door |
| Experiment Ledger cites CT-32 / CT-13 | Missing **wiring** | QMA + QMF/QMB |
| Dirty/unfingerprinted launch refusal | Missing small **function** (hook/router gate) | QMA |
| Mission budget dimensions + kill criteria on CT-32 | Missing **function** (AD-12/13/29 extend) | QMA |
| First-completion refill vs QMB generation barrier | Missing **wiring** (keep both clocks) | QMA + QMB |
| Budgeted ContextCompiler pack | Missing **function** | QMA |
| Ranked retrieval | Deferred **function** (GAP-0073) | QMA |
| Donor UIs, CLIs, engines, marketplaces | Not missing — **banned** | — |

## Recommended architectural ownership

- **QMA** owns the scientist's loop: experiment tree shape, Worker isolation, study Mission/Loop, budgets/kill/pause, wait-refill, ledger notebook, snapshot pin, context packing. Adapts OpenResearch/OpenScience/Delphi *discipline* onto existing ports.
- **QMB** owns running a spec: fixed run-config, process isolation, optimize/sweeps, CT-32. Reuse; QMA does not re-specify.
- **QMF** owns evidence persistence law. Connect ledger citations; do not open a log-as-evidence hole.
- **QML** owns declared spaces that `resolved_config_ref` points at. No new QML mechanism from this family.
- **UI** may later *read* ledgers and CT-32; it must not copy Autoresearch/orx dashboards. Out of this sitting's build.
- **QMN**: no home in this family.

## Open questions

Need an **AD** (do not silently inherit donor defaults):

1. **GAP-0073** — ranked/hybrid retrieval behind KnowledgeSource, or keep literal search for v1?
2. **Study budget dimensions** — promote OpenScience's runs/hours/spend/target + kill-criteria into Mission/Loop as closed vocabularies, or keep a single `continuation.budget` plus QMB governor and leave study-shaped budgets Deferred?
3. **Two wait clocks** — ratify that QMA rounds may refill on first completion while QMB TPE generations remain barrier-synchronous.
4. **Freeze-after-answer** — is “node answered” a daemon-evaluated predicate on CT-32 presence (recommended) or an Agent assertion in the Experiment Ledger?

Can stay **Deferred**:

- Git worktree as an ExecutionEnvironment checkout implementation (docker-per-worker already isolates; worktrees are optional sugar).
- Remote output-delivery retry (OpenScience Modal-specific).
- Literature discovery (`orx discover` / OpenScience `literature`) as a Research-desk plugin.
- Delphi as an optional out-of-process KnowledgeSource adapter (only after GAP-0073).
- Any Autoresearch/orx UI pane.
- CT-47 `defined-unwired` vs integration source existence — reconcile in the QMA/QMB code inventory, not from this donor pass.

## Official sources (fetched)

- https://github.com/alphaXiv/OpenResearch and https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/README.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/SKILL.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/SYSTEM_PROMPT.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-experiment-tree/SKILL.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-compute/SKILL.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-evidence/SKILL.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-git/SKILL.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-agent-delegation/SKILL.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-create/SKILL.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-lit-review/SKILL.md
- https://raw.githubusercontent.com/alphaXiv/OpenResearch/main/agent-skills/orx-reports/SKILL.md
- https://openresearch.sh/ and https://openresearch.sh/docs
- https://github.com/synthetic-sciences/openscience
- https://raw.githubusercontent.com/synthetic-sciences/openscience/main/ARCHITECTURE.md
- https://raw.githubusercontent.com/synthetic-sciences/openscience/main/CHANGELOG.md (v2.0.95 Studies/Autoresearch)
- https://www.openscience.sh/docs/llms-full.txt
- https://raw.githubusercontent.com/synthetic-sciences/openscience/main/frontend/docs/src/content/openscience/autoresearch.mdx
- https://raw.githubusercontent.com/synthetic-sciences/openscience/main/frontend/docs/src/content/openscience/experiment-tracking.mdx
- https://raw.githubusercontent.com/synthetic-sciences/openscience/main/frontend/docs/src/content/openscience/jobs.mdx
- https://raw.githubusercontent.com/synthetic-sciences/openscience/main/frontend/docs/src/content/openscience/context.mdx
- https://github.com/synthetic-sciences/delphi
- https://raw.githubusercontent.com/synthetic-sciences/delphi/master/README.md
- https://raw.githubusercontent.com/synthetic-sciences/delphi/master/docs/architecture.md
- https://raw.githubusercontent.com/synthetic-sciences/delphi/master/docs/context-sessions.md
- https://raw.githubusercontent.com/synthetic-sciences/delphi/master/docs/atlas-integration.md
- https://raw.githubusercontent.com/synthetic-sciences/delphi/master/docs/env-advanced.md
