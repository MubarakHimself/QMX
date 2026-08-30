# Reference Extract: prime-agent-rlm (Prime Agent + Recursive Language Models)

Reference for QMX's **RLM Runtime** (persistent Python control env, programmatic recursive
subagents) and **gated harness refinement** (Continual Harness / `/refine`, snapshot+rollback).
All facts carry source + (checked 2026-08-28). Filter = QMX Constitution (12 principles).
Sources: arxiv.org/abs/2512.24601 (paper); alexzhang13.github.io/blog/2025/rlm (blog);
github.com/PrimeIntellect-ai/prime-agent docs `rlm.md`/`rlm-runtime.md`/`architecture.md`/
`long-running-agents.md` and `src/core/refinement/refinement.ts` (raw main).

## Q1 — Target mental model

RLM (Zhang/Kraska/Khattab): "a general inference paradigm that treats long prompts as part of an
**external environment** and allows the LLM to programmatically examine, decompose, and recursively
call itself over snippets" (arxiv.org/abs/2512.24601, checked 2026-08-28). The root LM (depth=0)
**never sees the whole context** — only its size — and peeks/greps/partitions/maps over it via a
Python REPL that holds the context as a variable, spawning sub-LM calls over chunks
(alexzhang13.github.io/blog/2025/rlm, checked 2026-08-28). Decomposition is **context-centric**
(the LM decides how to split its context), explicitly *not* problem-centric like agent scaffolds
(same blog). Maps 1:1 to transcript #48 "RLM turns context from a payload into a programmable
environment" and Constitution #7 (context compiled, not accumulated).

Prime Agent operationalizes this: "the model works inside a persistent Python control environment
and composes capabilities as code. Provider calls, session persistence, child lifecycles,
scheduling, and safety policy remain in the TypeScript host; the Python REPL is the model-facing
programming surface" (prime `rlm.md`, checked 2026-08-28). Mental model for QMX: **a quant at a
Python console holding huge state in variables (handles) and dispatching focused sub-workers, its
own attention window staying small** — exactly the Analyst desk load (3yr backtests, 800 variants,
40 MC reports; transcript §6).

## Q2 — Concrete runtime/API structures

**Daemon / worker / kernel split** (prime `architecture.md`, checked 2026-08-28):
- Client (interactive TUI | print/JSON/RPC) — owns rendering/input only, not execution.
- **Daemon supervisor** — discovery, routing, attachments, worker health, cross-agent message
  delivery, saved-session catalog, crash recovery, leases/backpressure.
- **Session worker** = one root session tree: `AgentSessionRuntime` → root `AgentSession` +
  `Scheduler` + root Python kernel + RLM child runtimes. "Workers and kernels are separate
  processes for lifecycle and failure containment, **not security sandboxes**."
- `AgentSession` owns provider calls, queues, tools, compaction, goals, child lifecycles,
  transcript writes.

**Component ownership** (prime `rlm-runtime.md`, checked 2026-08-28):
`repl-manager.ts` (runtime process, stdio protocol, execution, host-request dispatch, interrupt,
shutdown) · `ipython.ts` (agent tool wrapper, lazy kernel, namespace bootstrap) ·
`agent-session.ts` (RLM policy, child creation, registry, usage attribution, goals) ·
`rlm-runtime.ts` (typed `rlm.run` validation, model discovery, list/delete) ·
`prime-agent-runtime/src/rlm/` (Python shim; "does not call providers or implement an agent loop").

**One built-in model tool: `ipython`.** File edits, project commands, skills, delegation all begin
from the persistent kernel. "Python state survives across tool calls and compaction" — variables,
imports, task handles remain on later turns. `await bash("npm run check")` — each call its own
process; `os.chdir`/`os.environ` changes persist in the kernel (prime `rlm.md`).

**Recursive subagents are native kernel calls** (prime `rlm.md`, `rlm-runtime.md`):
```python
handle = await rlm("Review the auth flow", name="auth-reviewer", model=..., thinking=...)
# RLMSpawnHandle{rlm_child_id, name, session_dir, model} — returned on ADMISSION only
```
The call "returns immediately after task admission with a child handle; it **never waits for or
returns the child's answer**." Results arrive **only** via explicit `agent_message.send(msg,
receiver_role="parent")` or files. Python API (`prime-agent-runtime`): `rlm` / `run` /
`find_models` / `list_subagents` / `delete_subagent` / `host_request` / `RLMSpawnHandle`.
Depth: `RLM_DEPTH < RLM_MAX_DEPTH`, **default max depth 2** (root→child→grandchild; grandchild may
not recurse). Determinism guards: unknown options **fail** (not ignored); requested model
unavailable → **spawn fails**, no silent fallback; child otherwise inherits parent model/skills/
tools/retry/loader.

**Host-request bridge** (prime `rlm-runtime.md`): Python skills (`goal`, `agent_message`,
`rlm_heartbeat`, `compact`) call `rlm.host_request(type, payload)`; the TS host validates the
request and **owns the state transition** — "keeps credentials, provider execution, transcript
writes, worker routing, and scheduling out of Python." Transport = newline-delimited JSON over
stdio: requests `execute|interrupt|host_reply|snapshot|restore|list_names|shutdown`; events
`ready|stdout|stderr|result|display|host_request|error|done`. `execute()` calls serialized (one
namespace, no two concurrent cells); child agents still run concurrently (each a distinct host
request + child runtime).

**Kernel lifecycle** (prime `rlm-runtime.md`): lazy on first REPL use. Python resolution order:
`PRIME_AGENT_KERNEL_PYTHON` (with current `prime-agent-runtime`) → `~/.prime/agent/kernel-venv/
bin/python` (bootstrapped via `uv`) → XDG. Managed env = Python 3.11 + `prime-agent-runtime` +
`dill`. Startup `python -m rlm.repl`. Persistent sessions **snapshot the kernel namespace** into
the session artifact dir for revival. Registry is parent-scoped, survives compaction/kernel-
restart/parent-restore; `child_usage_attributed` folds child cost into the launching parent turn.
Artifacts: `session-artifacts/<id>/{kernel-state.dill, kernel-state.json, scheduled-jobs.json,
harness/harness_state.json, sub-xxxxxxxx/...}`.

**Long-running surface** (prime `long-running-agents.md`, checked 2026-08-28): daemon-backed
workers survive client detach; user `/heartbeat` + agent `rlm_heartbeat.create(interval=...)`;
`prime-agent schedule add worker "0 9 * * 1-5" -- "..."` (cron, per-session, due ticks **claimed
before delivery** so a crash doesn't replay, missed ticks coalesced); persistent goals
`/goal --budget 200000` + `goal.complete()` (records token/wall-clock/continuation counts);
autonomous mode `--autonomous-gate "npm run check" --autonomous-max-turns 20` (gate runs before
finish; failed gate returns bounded output for another attempt; won't rerun an unchanged failed
gate). `agent_message` delivery modes `auto|steer|follow_up`, receipt `delivered|queued`,
broadcast only within the family roster; daemon derives sender identity, enforces size/rate/queue
limits.

**Cost/latency (paper's own limits, honest):** "comparable cost" to vanilla frontier at quality
that beats GPT-5 by median 26% vs compaction, 130% vs CodeAct sub-calls, 13% vs Claude Code
(arxiv.org/abs/2512.24601). Processes inputs "up to two orders of magnitude beyond model context
windows" (10M+ tokens) with no retriever. BUT implementation is **blocking, no async, no prefix
cache**; "each query [ranges] from a few seconds to several minutes"; **no guarantees on total API
cost or runtime**; experiments use **recursive depth 1** (blog, checked 2026-08-28).

## Q3 — Failure modes it solved

1. **Context rot** — recall degrades as the window fills; RLM keeps the root window small so it
   never happens (blog). Directly answers the Analyst overload transcript §6.
2. **Context-window ceiling** — aggregates 10M+ tokens without a retriever (paper).
3. **Long-output tasks** (bibtex-for-all, git-diff replay) — solved programmatically in one shot
   rather than token-by-token (blog).
4. **State evaporating at turn/UI boundary** — kernel state persists through compaction;
   daemon-backed workers survive detach; registries survive restart (prime `rlm.md` invariant 4).
5. **Self-review mess** — `/refine` is a separate gated subsystem, not live self-rewriting
   (refinement.ts). Matches operator's fear of "agents iterate/review their own work → mess" (#30).

## Q4 — What QMX should reuse conceptually

- **The core RLM bet for the Analyst desk**: genuine mass-backtest aggregation is a *programmable
  environment over handles*, not context stuffing. Transcript #41/#48, Constitution #7. Load-bearing.
- **Handle/variable pattern**: huge objects held as REPL variables the model manipulates; only
  results/handles cross into context (blog; prime `rlm.md`).
- **Daemon owns authoritative state; Python REPL is model-facing only** — clean fit to QMX
  daemon/UI split (Constitution #4) and "deterministic infra, probabilistic reasoning" (#2).
- **`host_request` typed bridge**: credentials, provider calls, ledger/transcript writes,
  scheduling stay in the daemon; Python is a thin shim that cannot touch the auth store. This is
  Constitution #2/#3 made concrete — reuse the shape wholesale.
- **Async subagent-via-mailbox**: `rlm()` returns an admission handle; answers return through
  `agent_message`. Matches transcript Agent Bus (identity+mailbox+durable transport+async wakeup,
  #34) and "Ledger=truth, Messages=collaboration" (#33). Fire-and-forget + registry, not awaiting.
- **Deterministic spawn guards**: depth cap, exact-model-or-fail, unknown-option-fail,
  admission-before-execution, usage attribution (#2, #6).
- **Kernel snapshot/restore** → QMX session replay as an architectural capability (transcript #39).
- **Continual Harness as the *template* for gated refinement** (refinement.ts, checked 2026-08-28):
  `RefinementProposal{summary, rationale, edits[], expectedOutcome}`; edit =
  `{action: create|update|delete, kind: prompt|memory|skill|subagent, id, title, content,
  reference, arguments}`; **base system prompt immutable** ("MUST NOT be rewritten"), refinements
  are *supplemental* state; **before/after snapshots per applied edit → deterministic rollback**
  (`rollbackProposal` reverses applied edits); `validateEdit()` deterministic schema/immutability
  checks; conflict guard "entry changed during refinement planning" (optimistic concurrency);
  local (session) vs global (cross-session) scope; atomic temp-file+rename state writes; and a
  separate **auto-refine review gate** (`reviewAutoRefine` → `{shouldRefine, rationale,
  instructions}`) that decides whether `/refine` even runs. Reuse the whole edit/rollback/scope
  shape and the immutable-base invariant.

## Q5 — What QMX should reject (INHERITED FASHION flagged)

- **RLM as the *only* execution model.** Prime exposes a single `ipython` tool and makes everything
  RLM. Transcript #41 is explicit: **two runtimes, Dialogue AND RLM, a clean split**. Do not force
  RLM onto dialogue-shaped work (Trader, PM, quick research). The paper itself: depth-1 suffices for
  most tasks. RLM is the Analyst's engine, not the platform's.
- **"Durable control environment, not a security sandbox"** (prime `rlm.md`/`rlm-runtime.md` trust
  model): Prime runs model-generated Python with the worker's OS permissions and trusts installed
  skills. QMX explicitly wants **Docker-per-worker isolation** (transcript L3976, #62). REJECT
  Prime's trust posture; put the QMX kernel *inside* the container. Prime's stance exists because it
  is a general-public coding CLI — INHERITED FASHION.
- **The coding-agent framing itself** — ACP mode, provider auto-discovery of the user's API keys
  (their own issues #1064/#1207), model-catalog regeneration, `oh-my-pi`-style plugin ecosystem —
  all serve a public developer audience. QMX is single-operator quant (Constitution #1). INHERITED.
- **LLM-only refinement gate.** Prime's promotion is gated by *one LLM review* (`reviewAutoRefine`)
  and auto-fires on `turn_interval`/`compact`. Operator wants **harder, deterministic-first** gates
  (#49, #30): deterministic validation → evaluation (backtest/test replay) → staged → approval, and
  "verifier scripts instead of LLMs judging themselves." Also note their live defect: refiner sees
  entries truncated to 240 chars in a single `completeSimple` call (issue #1290). Reject the naive
  single-call auto-refiner; keep only the edit/rollback data model.
- **No cost/runtime guarantees** (blog limitation). QMX Mission contract mandates budget +
  termination criteria (#21); RLM calls must run under a daemon-enforced budget, unlike Prime.
- **Auto-promotion to durable state.** Prime writes local harness state automatically. QMX: "we
  don't let the harness engineer itself into loops… we do that eventually" (#28) — promotion is an
  explicit, gated, later step. No live self-rewriting.

## Q6 — QMX-owned RLM Runtime contract (proposed)

**Daemon owns (authoritative, deterministic):** kernel lifecycle *inside the worker's Docker
container*; snapshot/restore (→ session replay); recursive-spawn admission (depth check → model
resolution via QMX Model Router → **budget/termination check** → registry write → return handle);
typed `host_request` dispatch for every authoritative op (provider calls via Model Proxy +
Credential Broker, desk-ledger writes, artifact writes, Mission/Task-Graph transitions, scheduler,
Memory/Knowledge queries); usage/cost attribution; cancellation/teardown; Agent-Bus delivery of
child→parent messages.

**Python control environment owns (model-facing, non-authoritative):** working state as variables/
handles; programmatic peek/grep/partition/map over handle contents; composing subtasks and calling
`qmx_rlm(...)`; invoking Python-backed skills. Cannot reach credentials or the auth store.

**Handle types** (the concrete QMX contribution — transcript §6, L1364–1404, L2832–2879):
- `BacktestHandle{run_id, strategy_version, data_snapshot_ref, engine, harness_version, status}`
  → `.metrics() .trades() .equity_curve() .compare(other)`
- `ExperimentHandle{spec_id (content-addressed), params, seed, lineage}` → `.results() .reproduce()`
- `TradeLogHandle{...}` → `.filter(session=...) .pnl()`
- `StrategyHandle{components:[EntryMechanism|ExitMechanism|Filter|SessionRule|...], provenance}`
  → `.mutate(component) .variants()` (typed strategy-component mutation, transcript §6)
- `PaperHandle`/`KnowledgeHandle{corpus_ref, provenance}` → `.sections() .grep() .cite()` (Delphi-shaped)
- `MarketDataHandle` (over `ctx.market`) → `.window() .resample(session_preserving=True)`
Each handle is a daemon-resolved reference; the underlying object **never enters the context window**.

**Promotion-gate contract (harness refinement):** agent emits `RefinementProposal` (Prime's shape);
gate pipeline = (1) deterministic `validateEdit` (schema + immutable base + optimistic-concurrency
conflict) → (2) **deterministic verification / evaluation** (verifier script, backtest/test replay —
not an LLM judging itself) → (3) optional cross-model review (`ReviewPolicy author_family !=
reviewer_family`, #31) → (4) **staged candidate** state (never live) → (5) operator/policy approval →
promotion into durable runtime state. Rollback via recorded before/after snapshots (reuse verbatim).
Kinds extend Prime's to `prompt|memory|skill|subagent|hook|loop|role`; base role prompt immutable.

**Honest v1-vs-deferred read:** Operator wants agents working overnight *soon* (L1896). Split the
verdict:
- **RLM Runtime = v1, but scoped to the Analyst desk only.** The persistent Python kernel + handle
  contract + async `qmx_rlm` spawn + `host_request` bridge is genuinely load-bearing for mass
  backtesting (the stated OG use case, L3976). Ship the *engineering* (Prime-style depth-1/2
  kernel), **not** the research paradigm (RL-trained recursive trajectories, unbounded depth — not
  needed). Dialogue Runtime ships first for Trader/PM/quick research; RLM need not block them.
- **Continual Harness / gated refinement = defer to v2.** Transcript overcooked-analysis #12 is
  right: there is **no trajectory corpus yet**, so the promotion pipeline gates evidence that does
  not exist. v1 ships only the *invariants* (immutable base prompt; proposals written to a staging
  ledger, never auto-promoted) and the edit/rollback data model. Gates go live once real
  trajectories accumulate — matching "we do that eventually… first stable version" (#28).

## Open questions this reference cannot settle
- Daemon language (open Q1): Prime is a **hybrid** — TS host + Python kernel — which is itself an
  argument against forcing one language; QMX could mirror it but the wire contract must be defined
  first (#9). Not resolvable from this reference.
- Is the kernel inside Docker performant enough for QMX's parallel-backtest fan-out? Prime never
  sandboxes, so it gives no evidence either way.
- `dill` namespace snapshots for QMX's very large handles — adequacy/safety unverified.
- Whether RLM depth >1 is ever needed for quant work (paper says depth-1 usually enough).
- The cost/runtime-budget mechanism (Prime has none) must be QMX-designed; no pattern to borrow.
