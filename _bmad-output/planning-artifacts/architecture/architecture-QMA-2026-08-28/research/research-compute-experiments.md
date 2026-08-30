# Reference Extraction — Compute / Experiments / Research-Loop

Reference set: **OpenResearch CLI** (alphaXiv `orx`), **Synthetic Sciences** (OpenScience + Delphi),
**QuantConnect Lean CLI**. Filter = QMX Constitution (single-operator quant lab; deterministic infra,
probabilistic reasoning; QMX owns its contracts). Aligns with QMX's own backtest product **QMB**
(`docs/components/qmb.md`, `ADR-0017`). All facts primary-sourced, checked 2026-08-28.

---

## Q1 — Target mental model

- **OpenResearch (`orx`)**: a *project is a git-native tree of experiment nodes*. Root = baseline
  (code + one fixed run command); every other node = a child branched off a parent, inheriting code
  and command. A node is **provisional** (editable, re-runnable in place) until a run *answers* it,
  then **frozen** forever — its branch is the exact code the result came from. Progress = growing the
  tree *downward* (fan the co-equal options of one decision, then descend onto the winner). "A
  disappointing result is still a result." The daemon owns the tree state; the LLM only proposes moves.
- **OpenScience**: an *AI workbench that runs the whole research loop* — literature → hypothesis →
  code → experiment → analysis → write-up — in one continuous session, over a real browser workspace
  (file tree, editor, terminal). One adaptive Research agent that *delegates* bounded Explore/Execute
  work; runtime, tools, skills, providers, workspace UI are cleanly separated; sessions/artifacts/
  provenance persist on disk.
- **Delphi**: *knowledge is a queryable, provenance-carrying index*, not a document. Local-first MCP
  server that indexes repos, papers, docs, datasets, and local folders; completed indexing runs mint
  **immutable source snapshots** so a saved context points at the exact version it used.
- **Lean CLI**: *the CLI is the stable boundary* over an opaque engine. Uniform verbs (`backtest`,
  `research`, `optimize`, `live`, `data`, `report`) run locally in Docker or in the cloud; the same
  project runs either way. Agents/humans touch the CLI, never the engine internals.

---

## Q2 — Concrete runtime / API structures

**OpenResearch** (README; `AGENTS.md`; `SKILL.md`; `agent-skills/orx-experiment-tree|orx-compute/SKILL.md`; `openresearch.sh/docs/cli`):
- Three id scopes: **project id → experiment id → run id** (never mixed). `orx project view` shows the
  tree; `orx runs <projectId> [--experiment]`; `orx logs <runId>`.
- Node ops: `orx create-experiment <projectId> --parent <id> --title --description` (prints child git
  branch `orx/<slug>`); `orx exp status|run|cancel|wait|wake|desc <expId>`; run command set once via
  `orx project edit <projectId> --run-command '<cmd>'`.
- **Compute backend abstraction**: `orx exp run <expId> --backend <b>` with b ∈ `local, ssh, slurm,
  k8s, ray, hf, modal, tinker, openresearch`. "Launch **all** experiment compute with `orx exp run`.
  Never invoke provider CLIs, schedulers, raw SSH, or the training command directly." One uniform
  launch contract + one required per-backend reference doc. Each run = "an **immutable snapshot of the
  experiment branch's recorded commit**"; "no backend needs a GitHub push"; uncommitted files excluded.
- **Detached submit + reattach (the job handle)**: `orx exp run` *queues and returns immediately*.
  Then: `orx exp wait <expId|--project <id>>` blocks until first state change (`--interval`,
  `--timeout`; "sleep-until-change signal, not the source of truth" → re-read `orx runs` and
  reconcile; `drained: no runs in flight` = done). `orx exp wake <expId>` = go idle, end the turn, be
  woken on `done|failed` (opt-in; waits behind queued user messages; use wait *or* wake, not both).
  `--force` allows a deliberate concurrent run; otherwise a node with a run in flight rejects a launch
  (single-in-flight lease). Failed runs carry a `reason:` line.
- **Delegation**: `orx agent spawn "<task>" [--title] [--no-wake]` delegates an independent helper
  session. State: local SQLite; projects/experiments/runs/logs/artifacts stay local to `orx` (Rust).
- **Auto-research loop** (per completion, four moves): **repair** (run answered nothing → fix same
  node's branch, re-run; cap: 2 answer-nothing runs then ask), **refill** (mediocre → launch next
  sibling), **promote** (clear win → becomes parent for next round), **stop** (goal met or ~3
  consecutive failed/regressed runs). Notes live in `orx exp desc` (whole-document markdown field).

**OpenScience** (README): `npm i -g @synsci/openscience` / `npx synsci`; browser workspace. Delegation
levels **Off / Auto / High** (not a per-turn worker quota); **plan mode is read-only**. Local server
hosts workspace UI + agent runtime + skill library (309 skills) + tool layer (shell, editor, LSP, MCP,
42 scientific DB connectors); **models routed per request**; keys stay local. Config: global
`~/.config/openscience/openscience.json`, project `openscience.json` / `.openscience/`. Layout:
`backend/cli`, `frontend/workspace`, `frontend/docs`, `tooling/sdk/js`, `tooling/plugin`.

**Delphi** (README): install `npx @synsci/delphi` (Docker + Postgres/pgvector); MCP tools —
`search`, `index_source`, `list_sources`, `read_source`, plus `/v1/sources/{id}/{read,grep,tree}`,
section-aware `get_paper`, "build a **context pack** around a task and a **token budget**", "save
**reproducible context sessions** for handoffs", policy-gated research jobs. Sources → context:
Repositories (code, symbols, call graphs, related tests/docs), Papers (sections, citations, equations,
quoted evidence), Documentation (versioned pages), Datasets (HF cards/metadata), Local folders.
"Every index lives in your PostgreSQL database. Completed indexing runs create **immutable source
snapshots**." Deterministic hybrid retrieval (BM25 + pgvector HNSW + cross-encoder rerank; fixed seeds,
per-input caches, total-order tiebreaks → identical query = identical result). Local-first MCP profile;
hosted/graph tools opt-in via env.

**Lean CLI** (README): `lean init` → `lean backtest <PROJECT> [-d/--detach] [--output DIR]` (defaults
`PROJECT/backtests/TIMESTAMP`), runs strategy in a Docker container; `lean research` = Jupyter Lab;
`lean optimize`; `lean live deploy|stop|command`; `lean data download|generate`; `lean report`;
`lean object-store`; cloud mirrors (`lean cloud backtest --push --open`). CLI configs:
`engine-image`, `research-image`, `data provider` flags. `lean private-cloud add-compute`.

---

## Q3 — Failure modes each solved

- **Result contamination / non-comparability** → OpenResearch's *fixed run-command + fixed env
  contract* ("vary code, not knobs-in-the-command"; no `LR=3e-4 python …` env sweeps): every node runs
  the same command over different committed code, so summaries stay comparable. **Directly the QMB
  wind-tunnel law** (DEC-0160: change config variables, never swap the tunnel).
- **Silent overwrite of evidence** → *frozen nodes*: once a run answers a node it can never be edited;
  a new question is a new child. Prevents rewriting the code a number came from.
- **Irreproducibility** → *immutable snapshot of the recorded commit* (OpenResearch) and *immutable
  source snapshots* (Delphi): the exact inputs are content-pinned, not "whatever is on disk now."
- **Detached long jobs orphaned when the client leaves** → *queue-and-return + wait/wake reattach*:
  the supervisor can end its turn entirely and be woken; the durable run id survives. Matches operator
  L1896 ("agents continue working while I'm away") and transcript #7 (attach ≠ network identity).
- **Vendor lock-in / agent knowing the machine** → *uniform `orx exp run --backend`*: one launch
  contract across 9 backends; the agent never invokes a provider CLI. Matches transcript #64.
- **Context-window overload** → Delphi's *context pack around a task + token budget* over an external,
  provenance-carrying corpus, instead of pasting a knowledge base into the prompt (transcript #48/RLM).
- **Monolithic pipeline rigidity** → Lean's *CLI-as-boundary*: swap engine/research/data behind stable
  verbs. QMB already realizes this (`qmb backtest bot --book scalping`, B-1 thin doors).

---

## Q4 — What QMX should reuse (conceptually)

1. **Experiment tree as durable, deterministic state**; LLM proposes moves, infra owns the graph
   (transcript #23/#26). Node lifecycle = provisional → frozen; lineage = the DAG of parents.
2. **Content-pinned inputs**: every run/experiment references an immutable code commit *and/or*
   content-addressed config + data snapshot (Constitution #11; QMB DEC-0160/0167).
3. **Uniform submit contract over many environments**; the agent declares requirements, a router
   places the job; agent never names the vendor (transcript #63/#64).
4. **Detached job handle with wait + async wake**: queue-and-return, reattach by durable id, wake on
   terminal state delivered to the actor's mailbox (transcript #34 bus; operator overnight-autonomy).
5. **Per-completion drive loop** (repair / refill / promote / stop) as an *authored v1 loop* for the
   Researcher/Analyst desks (transcript #28; QMX core loop Hypothesis→Test→Learn→Mutate→Gate).
6. **Delphi shape for QMX Knowledge**: local-first, provenance-carrying, versioned evidence corpus with
   immutable source snapshots, a `search/index/read/list` tool surface, context packs by token budget,
   and reproducible context sessions for handoffs (transcript #47; register §5 Delphi row).
7. **Clean separation** of agent runtime / tools / skills / providers / workspace / durable
   sessions+artifacts+provenance (OpenScience) — mirrors the QMX daemon component split.
8. **CLI as the stable boundary** to the backtest product (Lean → already QMB's `qmb` CLI + MCP door).

---

## Q5 — What QMX should reject

- **Git-branch-per-parameter-mutation** (OpenResearch's only lineage mechanism). At QMX scale a branch
  per param is absurd (register §5 reject; transcript #66). QMB already rules this: content-addressed
  **resolved run-config** for param/config changes; git/worktree *only* when code changes.
- **One adaptive Research agent** (OpenScience product choice) — QMX has genuinely distinct Roles
  (register §5). Reuse the *delegation shape*, not the single-agent model.
- **"Explore/Execute/Review" as three permanent lanes** — the *current* OpenScience surface is
  Explore/Execute delegation with levels Off/Auto/High and a read-only plan mode; "Review" is not a
  delegation lane. QMX's cross-model review is a `ReviewPolicy` enforced by hooks (transcript #31), not
  a spawn lane. Take bounded delegation + read-only planning; drop the three-lane framing.
- **INHERITED FASHION — marketplace/multi-tenant scaffolding**: OpenResearch orgs / managed-compute
  catalog / billing / telemetry; OpenScience Ace wallet + credit routing + accounts; Delphi hosted
  Atlas graph + API keys + magic-link auth. All exist because these serve the public — a single
  operator needs none of it. Keep only the local-first engine.
- **INHERITED FASHION — cloud research service split** (`orx` local vs `openresearch.sh` service).
  QMX has no service tier; the daemon is authoritative and local (Constitution #4).
- **A second governor / second data layer / second registry inside QMA**. QMB *already* owns
  process-per-run, the `min(cpu,memory)` governor, the WriterId ledger, CT-32, data commands, and
  as-of registry delivery. QMA must not re-implement any of it (DEC-0159/0161/0166/0169; ADR-0017).
- **Lean's C#-engine-in-Docker adoption** — already dead in QMB (DEC-0085/0086); reuse only the CLI
  verb ergonomics.
- **Environment variables as a control channel** (OpenResearch forbids env-var behavior switching; the
  env file is fanned to every backend). QMX: env is a declared allowlist, never the sizing/reattach path.

---

## Q6 — Contracts QMX should own

**`ExecutionEnvironment`** — *where* work runs; picked by the capability ladder (Constitution #10),
never by the agent naming a vendor.
```
ExecutionEnvironment {
  kind: local | docker | remote-container | remote-host | browser | desktop
  id, label
  provider_ref            # opaque adapter handle (Docker daemon | SSH alias | sandbox vendor); resolved by a provider adapter
  image?, mounts[], env_allowlist[]        # env is a declared allowlist, not a control channel
  capabilities: set<{cpu, gpu, network, display, browser, persistent_fs}>
  lifecycle: ephemeral | persistent        # per-worker Docker = ephemeral default (op. L3976); the one Windows VPS = persistent
}
```
Default worker isolation = one Docker container per worker (operator L3976); `browser`/`desktop` only
when a task genuinely needs vision (capability ladder rungs 4–6).

**`ComputeRequirement`** — *what the work needs*; the agent declares, the Compute Router places.
```
ComputeRequirement {
  cpu, memory, disk, gpu?: {kind, count}
  capabilities_needed: set<Capability>     # e.g. {gpu, network} or {display}
  timeout, max_memory                      # deadline + peak (QMB parity: qmb_run_time_limit / qmb_run_memory_limit)
  isolation: required | shared             # default required
  environment_hint?: kind                  # advisory only; router chooses actual placement
}
```

**`JobHandle` + `ComputeRouter`/`JobService`** — detached submit + reattach; "attached" ≠ identity
(transcript #7). Durable in daemon state so it survives UI/supervisor exit.
```
JobHandle { job_id; state: queued|running|done|failed|cancelled|aborted; environment_ref; spec_ref; submitted_at; reason? }

submit(spec: ExperimentSpec, req: ComputeRequirement) -> JobHandle   # queues, returns immediately (orx exp run)
attach(job_id) -> EventStream                                        # live view while a client watches (does not change identity)
wait(job_id | scope, {interval, timeout}) -> StateChange            # blocks to first change (orx exp wait --project)
reattach(job_id) -> JobHandle                                       # detached/woken supervisor re-acquires from durable state
wake(job_id, policy)                                                # async wakeup on done|failed → actor mailbox (orx exp wake)
cancel(job_id)                                                      # orx exp cancel
stream(job_id) -> EventStream                                       # operational logs = harness telemetry, NOT the ledger
```
Single-in-flight lease per node unless an explicit `force` (orx `--force`). `wait` is a
sleep-until-change signal, not truth — the durable job store is truth (reconcile after each wake).

**`ExperimentSpec`** — content-addressed; fingerprint = hash of the frozen fields (Constitution #11).
```
ExperimentSpec {                            # fingerprint is the identity + lineage key
  code_ref?:   git_commit | worktree_archive     # REQUIRED only when CODE changes (transcript #66)
  config_ref:  resolved_config_fingerprint       # when only params/config change = QMB resolved run-config (DEC-0160)
  data_ref:    dataset_snapshot | registry_as_of_fp
  env_ref:     ExecutionEnvironment fingerprint
  seed?, model_version?, harness_version?, cost_assumptions?
  lineage: parent_spec_ref[]                     # a DAG of specs, NOT a git branch per mutation
}
```
Git/worktree isolation is required *only* for code changes; parameter/config sweeps are content-
addressed config, never new branches — this is the explicit rejection of OpenResearch's branch-per-param.

**Agent → QMB path** (no re-implementation of anything QMB owns):
```
agent → QMA SDK (backtest tool) → QMX Backtesting Service → `qmb` CLI / MCP door
      → QMB pure library.run(resolved_config) → QMB orchestrator (process-per-run) INSIDE the
        ExecutionEnvironment the QMA Compute Router placed
```
- QMA provides the **environment + JobHandle**; QMB's own orchestrator owns intra-node parallelism
  (`min(cpu,memory)` governor), process spawn, the WriterId-scoped ledger line, and the CT-32 artifact.
- **Avoid a double governor**: QMA places ONE `qmb` job per environment; QMB governs the runs inside
  it. QMA's `JobHandle` wraps the `qmb` invocation; QMB's ledger line is the durable evidence; QMA's
  job `stream` = QMB operational logs (never evidence — CT-11).
- The `qmb` CLI is pinned in every agent workspace (QMB B-1), so QMA reaches backtesting through the
  same stable door the operator uses. QMA MUST NOT re-own: run loop, config compiler, fill/cost/
  financing ports, sampler, run ledger, CT-32 (DEC-0159/0161/0169).

---

## Open questions (this reference set cannot settle)

1. **Graph engine / experiment-tree store** — OpenResearch uses local SQLite + git branches; QMX's
   deterministic task/experiment graph engine is named unresolved in the packet (register §3 #9).
2. **Async wake transport** — `orx exp wake` fires into one CLI session; QMX's mailbox/durable
   transport and the "machine off for days" case are explicitly deferred (register §3 #5/#6).
3. **Sandbox/compute vendor behind `remote-container`/`desktop`** — operator rejects Modal/Daytona/E2B
   as defaults; the environment contract is fixed here, the vendor is not (register §3 #8).
4. **Whether QMX Knowledge (Delphi-shaped) is built at all** — operator never ratified a knowledge base
   (register §3 #10); Delphi gives the shape if/when it is.
5. **Delegation levels vs. QMX Roles** — OpenScience Off/Auto/High delegation maps loosely to QMX's
   Role-Lead-spawns-workers model, but the concrete parallelism policy is undefined.
