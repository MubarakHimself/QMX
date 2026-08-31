# Hermes Agent (Nous Research) — Reference Extraction

Transcript role: PRIMARY INTEGRATED-HARNESS reference. Operator ruling: "Hermes
provides mental models. Let me be clear there. Mental models." (register §5) —
never the base SDK. Filter = QMX Constitution (single-operator, deterministic
infra, QMX owns contracts, memory selective, self-improvement gated, context
compiled).

Source map (all checked 2026-08-28):
[ctx] https://hermes-agent.nousresearch.com/docs/developer-guide/context-engine-plugin
[mem] https://hermes-agent.nousresearch.com/docs/developer-guide/memory-provider-plugin (+ NotebookLM notebook 5cffee86, agent/memory_provider.py)
[prompt] https://hermes-agent.nousresearch.com/docs/developer-guide/prompt-assembly
[compress] https://hermes-agent.nousresearch.com/docs/developer-guide/context-compression-and-caching
[tools] https://hermes-agent.nousresearch.com/docs/developer-guide/adding-tools
[skills] https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills + /docs/user-guide/features/skills
[hooks] https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks
[prof] https://hermes-agent.nousresearch.com/docs/user-guide/profiles
[deleg] https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation

## Q1. Target mental model
A single-process "integrated harness" where **every LLM invocation is an
assembled prompt over single-select, pluggable cognitive backends**. The harness
owns lifecycle; the model reasons inside it. Four ideas the transcript wants:
1. **Compiled, cache-stable prompt** in ordered tiers (stable→context→volatile);
   ephemeral additions live off-prompt so the cache prefix never mutates [prompt].
2. **Memory ≠ Context Engine ≠ Compaction** — deliberately separate components
   (register dec-46: "Hermes' memory-provider vs context-engine split is the model").
3. **Runtime-checked capability surface** — tools/skills are filtered by
   availability BEFORE their schemas ever reach the model [tools][skills].
4. **Deterministic lifecycle interception via Hooks** across the whole loop [hooks].
Everything is scoped by a **Profile** = one whole home directory (config, keys,
memory, sessions, skills, cron) [prof].

## Q2. Concrete runtime/API structures (real names, signatures, config keys)

**ContextEngine ABC** (`agent/context_engine.py`; one active; `context.engine` in
config.yaml; directory `plugins/context_engine/<name>/`) [ctx][compress]:
- Required: `name` (property), `update_from_response(usage:dict)`,
  `should_compress(prompt_tokens=None)->bool`, `compress(messages, current_tokens=None, focus_topic=None)->list`.
- Attrs it must keep: `last_prompt_tokens/last_completion_tokens/last_total_tokens,
  threshold_tokens, context_length, compression_count`.
- Optional: `on_session_start/end/reset`, `update_model(model, context_length)`,
  `get_tool_schemas()/handle_tool_call()` (engine can expose tools e.g. `lcm_grep`),
  `should_compress_preflight(messages)`, `get_status()`,
  **`select_context(request_messages, *, conversation_messages, incoming_message, budget_tokens)->list|None`** (the ONLY verb that can REPLACE per-request context — RAG/routing; request-only, never mutates history; fail-open),
  `on_turn_complete(messages, usage)`.
- Config: `compression.model_thresholds` is the one shared key (`"claude-sonnet":0.35`, longest-substring match); rest of `compression.*` is compressor-specific.
- Thread contract: compaction runs on a **pooled daemon thread** with host timeout when `compression.context_timeout_seconds>0`; must be thread-safe, no thread affinity.

**MemoryProvider ABC** (`agent/memory_provider.py`; `memory.provider` key) [mem]:
- Required: `name`(prop), `is_available()->bool` (**no network calls**),
  `initialize(session_id, **kw)`, `get_tool_schemas()->list`,
  `handle_tool_call(tool_name, args, **kw)`, `get_config_schema()`, `save_config(values, hermes_home)`.
- Optional hooks: `system_prompt_block()->str` (static volatile block),
  **`prefetch(query, *, session_id="")->str`** (before each API call → recall injected into user msg),
  `queue_prefetch(query,...)` (after turn, warm cache),
  **`sync_turn(user, assistant, *, session_id="", messages=None)`** (persist turn; **MUST be non-blocking → background daemon thread**),
  `on_session_end(messages)`, **`on_pre_compress(messages)`** (deep snapshot BEFORE compaction prunes — extract durable insight first),
  `on_memory_write(action, target, content)`, `shutdown()`.
- **Single-active-provider rule**: only one external provider at a time; `MemoryManager` rejects a second registration + logs a warning. Rationale: avoid conflicting writes + tool-schema bloat.

**Prompt assembly** (`agent/system_prompt.py`, `prompt_builder.py`) [prompt]:
- Cached system prompt = 3 tiers joined `stable → context → volatile`:
  stable = identity(SOUL.md/default) + tool/model guidance + **skills index** + env/platform hints;
  context = caller `system_message` + ONE project file (`.hermes.md`>AGENTS.md>CLAUDE.md>.cursorrules, first match wins);
  volatile = `MEMORY.md` + `USER.md` snapshots + external memory-provider block + timestamp/session line.
- **API-call-time-only (never cached)**: `ephemeral_system_prompt`, prefill, gateway overlays, and `pre_llm_call` context → appended to the current **user message**, not the system prompt. This is what keeps the cache prefix byte-stable.

**Tools runtime** (`tools/*.py` + `toolsets.py`) [tools]:
- `registry.register(name, toolset, schema, handler=lambda args,**kw:..., check_fn, requires_env=[...], is_async=False)`. Auto-discovered by any top-level `registry.register()` call.
- **`check_fn()->bool` preflight**: called when building tool definitions; if False the tool is **silently excluded** — the model never sees a tool it can't use.
- Handlers MUST return a JSON string; errors as `{"error":...}`, never raised.
- Toolsets = named bundles `{description, tools:[...], includes:[...]}`; `_HERMES_CORE_TOOLS` = default-everywhere set. Intercepted stateful tools: `todo, memory, session_search, delegate_task`.

**Skills** (SKILL.md; `~/.hermes/skills/`) [skills]:
- Frontmatter: `name, description, version, author, license, platforms:[macos|linux|windows]`,
  `metadata.hermes.{tags, related_skills, requires_toolsets, requires_tools, fallback_for_toolsets, fallback_for_tools, config:[{key,description,default,prompt}], blueprint:{schedule,deliver,prompt,no_agent}}`,
  `required_environment_variables:[{name,prompt,help,required_for}]`, `required_credential_files:[{path,description}]`.
- **Progressive disclosure**: index (name+description) sits in the stable prompt tier; body loaded on demand via `skill_view(name)`; common workflow first, edge cases last; `${HERMES_SKILL_DIR}`/`${HERMES_SESSION_ID}` token substitution.
- **Conditional activation**: `requires_*` hide when tool/toolset absent; `fallback_for_*` hide when a better tool IS present.
- **Self-authoring** via `skill_manage` tool (actions: create/patch/edit/delete/write_file/remove_file) = the agent's procedural memory.

**Self-authoring gates** [skills]:
- **`skills.write_approval`** (default **false = write freely**): when true, every `skill_manage` write is STAGED under `~/.hermes/pending/skills/`, survives restart, reviewed via `/skills pending|diff|approve|reject`. Same gate for memory via `memory.write_approval`.
- **`skills.guard_agent_created`**: an independent **content scanner** (dangerous-pattern heuristics), NOT an approval gate.
- **Curator** = autonomous skill maintenance; NEVER modifies repo-owned/project/external dirs; new agent skills always land in `~/.hermes/skills/`.
- Hub installs pass a security scanner → trust levels `builtin|official|trusted|community`; dangerous verdicts quarantined/blocked.

**Hook vocabulary** (`config.yaml hooks:` shell + Python plugin `ctx.register_hook`) [hooks]:
- Categories: **observer** (return ignored), **transform** (first string replaces content), **directive/control** (consumes documented return).
- `pre_llm_call` (directive) — once/turn; all `str` or `{"context":...}` returns joined and injected into the user message. Payload: user_message, conversation_history, is_first_turn, model, platform, session/turn/task ids.
- `pre_tool_call` (directive) — first valid **`block`** or **`approve`** wins; `modify` returns shallow-merged into tool args; **fails CLOSED** on timeout (blocks the tool). Payload: tool_name, args, tool_call_id, turn_id, api_request_id.
- `post_tool_call` (observer), `transform_tool_result`/`transform_terminal_output` (transform), `pre_verify` (directive — edited-code verify gate), `post_llm_call`, `pre/post_api_request`, `on_stream_*`, `on_interim_message`.
- Lifecycle: `on_session_start/end/reset/finalize`, `on_skill_lifecycle`, `subagent_start`, `subagent_stop`, `pre_gateway_dispatch`, `pre_command`, `pre_approval_request`, plus Kanban lifecycle hooks (`kanban_task_blocked/updated`, `on_kanban_worker_spawned/exited/stale_claim`, `on_kanban_dispatch_tick`).
- Bounded hooks abandoned past `plugins.hook_callback_timeout` (30s default).

**Profiles** [prof]: each = a separate `HERMES_HOME` dir (`~/.hermes/profiles/<name>/`) with own `config.yaml, .env, SOUL.md, memory, sessions, skills, cron, state.db, gateway`. Auto command alias. Rule: **never two processes on one home** (both write memory, compound state) → shared memory needs an external provider. `--description` tags a profile for kanban routing. Distributions = a profile shared as a git repo. (Note: Hermes "Bot Mode" turns profiles into a named-bot roster.)

**Delegation** (`delegate_task`) [deleg]: spawns child AIAgent with **fresh isolated context** ("subagents know nothing" — only `goal`+`context` args + the workspace's project files reach them); only the child's final summary re-enters the parent. **Narrowing rules**: child **inherits parent toolsets and cannot widen** (`delegate_task` has no model-facing toolsets param); leaf children are BLOCKED from `delegate_task, clarify, memory, send_message, cronjob` (both keep `execute_code`). Flat by default: `role="orchestrator"` + `delegation.max_spawn_depth` (default 1) needed to nest; `orchestrator_enabled:false` kills it. `delegation.model/provider` = cheap-worker override. Stall monitor + `/agents` overlay; `steer`/`stop` actions.

## Q3. Failure modes Hermes solved
- **Prompt-cache thrash** from mutating the system prompt mid-turn → tiered cache-stable prefix + off-prompt ephemeral layer [prompt].
- **Context overflow in long/overnight sessions** → dual compression: in-loop compressor at 50% + gateway hygiene safety net at 85%; `lean` tail keeps ~2.5% window but carries anchors (SHAs/paths/errors, verbatim user turns) + `session_search` recovery pointer; **compacted turns soft-archived (`active=0,compacted=1`), never deleted** — the full local transcript stays recoverable [compress].
- **Tool bloat / model calling unusable tools** → `check_fn` preflight exclusion + conditional-skill activation + `tool_search` [tools][skills].
- **Two agents corrupting shared state** → profile isolation (one home per agent) + single-active memory provider [prof][mem].
- **Runaway recursion / subagent context blowup** → flat-by-default delegation, depth cap, isolated child context, summary-only return [deleg].
- **Self-improvement writing junk / untrusted skills** → write_approval staging + guard scanner + curator scoping + hub security scan/quarantine [skills].
- **Memory backend blocking the chat loop** → `sync_turn` non-blocking + compaction on pooled daemon thread [mem][ctx].

## Q4. What QMX should REUSE conceptually
- The **Memory / Context Engine / Compaction / Knowledge** four-way split as the cognition backbone (register dec-46). Adopt as QMX-owned contracts.
- **`select_context()` as a first-class verb** — it operationalizes Constitution §7 "context is compiled, not accumulated": per-request retrieval/routing that REPLACES the message list, distinct from lossy compaction. This is QMX's Context Compiler.
- **`check_fn` availability preflight** for the Tool Registry + **conditional (requires/fallback) activation** for skills → QMX Capability Registry narrowing per Role/Mission (register dec-59).
- **Cache-stable stable-prefix vs volatile-overlay** prompt discipline for every QMX model invocation.
- **`on_pre_compress` escape hatch** — lets memory/ledger extract durable state before a session is reduced (feeds QMX ledger + memory candidates).
- **Hook categories (observer/transform/directive)** with `pre_tool_call` fail-closed and `pre_llm_call` cache-safe injection → the QMX Hook vocabulary (register dec-29); add QMX's deterministic `before_task_complete` verifier (dec-30) and `ReviewPolicy` (dec-31) as directive hooks.
- **SKILL.md progressive disclosure** (index in prompt, body on demand) and **staged self-authoring** — but with QMX defaults flipped (gate ON).
- **Delegation narrowing** (child ≤ parent capabilities; blocked-tool set; depth cap) → QMX worker-template spawning + Docker-per-worker isolation.
- **Memory single-active-per-scope** and **non-blocking sync** engineering constraints.

## Q5. What QMX should REJECT
- **Base-SDK status** — operator: mental models only; QMX owns runtime bottom-up (Constitution §3). Do not depend on Hermes.
- **`write_approval:false` default** — QMX gates self-improvement by default (Constitution §9). Invert: staging ON, deterministic validation before promotion (register dec-49).
- **MEMORY.md/USER.md flat-markdown "memory"** snapshotted into the prompt = arbitrary agent text becoming trusted memory. QMX requires provenance/confidence/scope-gated candidates (dec-45); memory is selective, not a notes file (Constitution §8).
- **Lossy summarize-the-middle as the default compaction** (silently drops turns if the summary model is undersized). QMX Analyst load (800 strategy variants, 40 MC reports) needs RLM handles + Knowledge corpus, not prompt-stuffing then summarizing (dec-48).
- **Single global active memory provider** — QMX has per-desk ledgers/memory scopes; make it single-active-**per-scope**, not one process-wide provider.
- **Hermes' Profile==home==agent conflation + Bot Mode roster** — collides with QMX ontology where Profile = presentation only and Bot/Role are distinct durable objects (dec-10,16). Borrow the isolation, reject the naming.
- **Computer use** — operator: Hermes not best at it; use Codex (dec-16 open-Q, §5).
- Provider/model config baked into the profile — QMX separates Model Router + Credential Broker (dec-51,53).

INHERITED FASHION (exists because Hermes serves the general public / a marketplace / many messaging tenants — single-operator QMX does not need):
- **Skills Hub / taps / `hermes skills publish` / trust levels / community-skill scanning / blueprints-as-shareable-automations** — a publisher marketplace. QMX has no third-party publishers.
- **Profile distributions as git repos** + `--clone-all` sharing — multi-user distribution.
- **15+ messaging-platform gateways** (Telegram/Discord/Slack/WhatsApp/Signal/Teams/LINE/DingTalk/WeChat…), `deliver:` targets, deliverable-mode attachments — consumer reach QMX replaces with its own daemon wire contract + terminal UI.
- **SOUL.md persona/personality system, bot avatars, voice/TTS** — consumer personalization.
- **Secret-manager plugin fleet** (Bitwarden/command-helper) and per-platform pairing — one operator's creds already live in Windows Credential Manager.

## Q6. Contracts QMX should OWN instead (see structured `qmx_contract`)
Rename ContextEngine → **Context Compiler** (make `select_context` the primary
verb); keep MemoryProvider but scope per-Desk/Bot; Tool Registry + Capability
Registry with `check_fn` gating; QMX SKILL format with self-authoring gated ON;
QMX Hook vocabulary extended with deterministic verifier + ReviewPolicy +
ledger-write hooks. Details in the structured return.

## Open questions this reference cannot settle
- Daemon language (Hermes is Python/monolith; QMX daemon TS-vs-Python still open, register §3 Q1).
- How QMX's per-desk ledger + agent bus map onto a harness that assumes one profile/one process.
- Whether QMX Compaction should be lossless-by-default (LCM-style) vs Hermes' lossy default — transcript pushed this to this architecture step (register §3 Q18).
- Graph engine, memory backend choice (Hindsight vs Mem0), and multi-model routing sit outside Hermes' scope.
