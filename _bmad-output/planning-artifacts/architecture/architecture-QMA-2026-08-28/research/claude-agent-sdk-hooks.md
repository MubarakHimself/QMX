# Reference extract: claude-agent-sdk-hooks

Study of the Claude Agent SDK / Claude Code hook + subagent + permission surface as the model for QMX's **Hooks** primitive (register decision #29) and primary subagent reference. All facts fetched live 2026-08-28. Transcript row: section 5 "Claude Code / Claude Agent SDK" — borrow the hook lifecycle + subagent/permission clarity; QMX owns the contract (decisions #2, #29, #30, #31). Constitution filter: P2 deterministic infra, P3 QMX owns contracts, P1 purpose-built, P5 extensibility, P12 observability≠ledger.

## The six questions

**1. Target mental model.** A hook is a *deterministic callback fired at a named point in the agent lifecycle* that can observe, veto, rewrite, or annotate what the runtime is about to do — the runtime, not the LLM, owns the decision. Permissions are a fixed 6-step evaluation pipeline (hooks run first). Subagents are separate agent instances with isolated context whose only channel to the parent is a final message. Together: the harness is a deterministic state machine; the model reasons *inside* gates it cannot bypass. This is exactly QMX Constitution P2.

**2. Concrete structures (verified names/signatures).** See tables below. Core: `HookEvent` union, `HookCallback` signature, `HookMatcher{matcher,hooks,timeout}`, `hookSpecificOutput{hookEventName,permissionDecision,permissionDecisionReason,updatedInput,additionalContext}`, universal `{continue,stopReason,systemMessage}`, `AgentDefinition`, `PermissionMode`, `canUseTool`→`PermissionResult`.

**3. Failure modes it solved.** (a) Agents doing irreversible/dangerous actions with no chokepoint → `PreToolUse` deny + deny-rules-before-bypass. (b) Self-judging agents → deterministic `TaskCompleted`/`Stop`/`TeammateIdle` gates that run real scripts (tests) and refuse completion. (c) Agents stopping before done → `Stop` hook `decision:"block"` keeps them working ("`/goal`", Ralph loop). (d) Context blow-up from delegation → subagent context isolation. (e) Runaway subagent trees → depth/concurrency/spend caps. (f) Human-in-loop without a terminal → `defer` + resume.

**4. What QMX should reuse (conceptually).** The event-fires→collect→match→callback→decision pipeline; the four verbs (observe/block/modify/inject) + ask/defer; precedence `deny>defer>ask>allow`; most-restrictive-wins across parallel hooks; the deterministic **before-complete gate** (decision #30 — verifier scripts at `before_task_complete`); Stop-block as the "keep working toward a condition" engine (open decision #13, #31 ReviewPolicy); subagent lifecycle events carrying `agent_id`/`agent_type`; `additionalContext` as the context-injection channel (feeds QMX Context Engine, never the Ledger).

**5. What QMX should reject.** The ~21-event TS-only sprawl is **INHERITED FASHION** (see tag list). Reject: settings-file precedence sprawl (user/project/local/policy), the auto-mode LLM classifier + `PermissionDenied` (an LLM judging permissions — violates P2 and decision #51/#30), `terminalSequence`/desktop `Notification` plumbing, `MessageDisplay`/display-redaction, `Elicitation`/`ElicitationResult` MCP-UI round-trips, `UserPromptExpansion` (slash-command marketplace), connector "organization set to ask" multi-tenant governance, `ConfigChange`/`CwdChanged`/`DirectoryAdded`/`InstructionsLoaded`, deprecated `approve`/`block` aliases, and the magic 8-consecutive-block cap. Also reject prompt-type and agent-type hook handlers (LLM-in-the-hook) — QMX hooks must be deterministic Python.

**6. Contract QMX should own.** A closed-and-addable `HookEvent` vocabulary mapped to the QMX ontology (Bot/Agent/Mission/Task/Loop) and a single `HookResult` tagged-union a Python daemon implements natively with zero Claude-SDK dependency. Defined at bottom.

## Verified fact A — complete hook event list per SDK (must-answer)

Source: https://code.claude.com/docs/en/agent-sdk/hooks (per-language "Available hooks" table) and https://code.claude.com/docs/en/agent-sdk/python (`HookEvent` Literal, verbatim). Both checked 2026-08-28.

**Python `HookEvent` — exactly 10, verbatim from python.md:** `PreToolUse, PostToolUse, PostToolUseFailure, UserPromptSubmit, Stop, SubagentStop, PreCompact, Notification, SubagentStart, PermissionRequest`.

**TypeScript adds (Python column = No) ~21 more:** `PostToolBatch, UserPromptExpansion, MessageDisplay, StopFailure, PostCompact, PermissionDenied, SessionStart, SessionEnd, Setup, TeammateIdle, TaskCreated, TaskCompleted, Elicitation, ElicitationResult, ConfigChange, InstructionsLoaded, WorktreeCreate, WorktreeRemove, CwdChanged, FileChanged, DirectoryAdded`.

**Transcript claim VERDICT (§5):** claim was that TS-only = SessionStart, SessionEnd, TaskCompleted, WorktreeCreate, WorktreeRemove, TeammateIdle, PostToolBatch. **All 7 CONFIRMED TS-only.** But the claim is *incomplete*: it lists 7 of ~21 TS-only events (missed PermissionDenied, PostCompact, StopFailure, MessageDisplay, UserPromptExpansion, Setup, TaskCreated, Elicitation×2, ConfigChange, InstructionsLoaded, CwdChanged, FileChanged, DirectoryAdded). Note: Python SDK CAN still reach TS-only events as *shell-command hooks* via `setting_sources=["project"]` (e.g. `SessionStart`/`SessionEnd` in `.claude/settings.json`) — it just can't register them as in-process Python callbacks.

## Verified fact B — what a hook may return (per capability)

| Capability | Mechanism | Events |
|---|---|---|
| observe only | return `{}` (or async `{async:true}`) | all |
| block a tool | `hookSpecificOutput.permissionDecision:"deny"` (+reason to Claude); exit-2 routes same | PreToolUse |
| ask user | `permissionDecision:"ask"` / `decision.behavior` | PreToolUse, PermissionRequest |
| defer (pause→resume) | `permissionDecision:"defer"` — **only `-p` headless, single tool call**; emits `deferred_tool_use`, `stop_reason:"tool_deferred"` | PreToolUse |
| modify tool **input** | `hookSpecificOutput.updatedInput` (replaces whole input object) | PreToolUse, PermissionRequest(`decision.updatedInput`) |
| modify tool **output** | `hookSpecificOutput.updatedToolOutput` (any tool, both SDKs; `updatedMCPToolOutput` deprecated) | PostToolUse |
| inject context | `hookSpecificOutput.additionalContext` (wrapped in system-reminder, next model request) | SessionStart, SubagentStart, UserPromptSubmit, PreToolUse, PostToolUse, PostToolBatch, Stop, SubagentStop |
| keep agent working | `{"decision":"block","reason":...}` prevents stop; guarded by `stop_hook_active` + 8-block cap | Stop, SubagentStop |
| gate task completion | exit-2 (feedback to model, task stays open) or `{"continue":false,...}` | TaskCompleted, TeammateIdle, TaskCreated(`decision:"block"`) |
| grant + persist perms | `decision.updatedPermissions[]` = `addRules/replaceRules/removeRules/setMode/addDirectories` × `destination:session|localSettings|projectSettings|userSettings` | PermissionRequest |
| stop everything | universal `{"continue":false,"stopReason":...}` (precedence over event decisions) | all |
| side-effect notify | `terminalSequence` / `Notification` (INHERITED) | Notification, StopFailure, etc. |

Precedence when multiple hooks/rules apply: **`deny > defer > ask > allow`**. All matching hooks run in parallel; any one `deny` wins; write hooks order-independent. Output strings capped 10,000 chars (overflow → file + preview). A `PreToolUse` allow can **never** approve `rm`/`rmdir` on a critical path.

## Verified fact C — I/O JSON shapes, matchers, signatures

- `BaseHookInput`: `{session_id, transcript_path, cwd, permission_mode?, hook_event_name}`. Tool inputs add `tool_name, tool_input, tool_use_id`; subagent inputs add `agent_id, agent_type` (+ `agent_transcript_path, last_assistant_message` on Stop). Stop input also carries `stop_hook_active, last_assistant_message, background_tasks[], session_crons[]`.
- Python `HookCallback = Callable[[HookInput, str|None, HookContext], Awaitable[HookJSONOutput]]`; `HookMatcher{matcher:str|None, hooks:list, timeout:float|None}` (default 600s; 30s UserPromptSubmit; 10s MessageDisplay; 1.5s SessionEnd).
- **Matcher semantics** (https://code.claude.com/docs/en/hooks): `"*"`/`""`/omitted = all; value of only `[A-Za-z0-9_\- ,|]` = exact string or `|`/`,`-separated exact list; **any other char = unanchored JS `RegExp.test`** (wrap `^…$` for whole-string). Matches `tool_name` for tool events, agent-type for subagent events, notification-type for Notification, trigger for compaction. No-matcher events: UserPromptSubmit, PostToolBatch, Stop, TeammateIdle, TaskCreated/Completed, Worktree*, MessageDisplay, CwdChanged. Per-handler `if:"Bash(git *)"`/`"Edit(*.ts)"` filters name+args via permission-rule syntax.

## Verified fact D — subagents (https://code.claude.com/docs/en/agent-sdk/subagents)

`AgentDefinition`: **`description`(req), `prompt`(req)**, `tools[]`, `disallowedTools[]`, `model`(alias/id/`inherit`), `skills[]`, `memory('user'|'project'|'local')`, `mcpServers[]`, `initialPrompt`, `maxTurns`, `background`, `effort`, `permissionMode`. Three sources: programmatic `agents={}`, filesystem `.claude/agents/*.md`, built-in `general-purpose`. Context isolation: fresh window, parent history NOT inherited; the Agent-tool prompt string is the only inbound channel; only the final message returns (scanned for control-tag/turn-marker injection). Lifecycle hooks: `SubagentStart`/`SubagentStop`. Caps: `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`(3), `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`(20), `maxBudgetUsd`. For >dozens of agents the SDK routes to the `Workflow` tool (orchestration in a script outside conversation context) — directly relevant to QMX distributed backtesting fan-out.

## Verified fact E — permissions (https://code.claude.com/docs/en/agent-sdk/permissions)

Evaluation order (fixed): **Hooks → Deny rules → Ask rules → Permission mode → Allow rules → `canUseTool`**. Modes (`PermissionMode`): `default, dontAsk, acceptEdits, bypassPermissions, plan, auto`. `canUseTool` callback returns `PermissionResult`: allow `{behavior:"allow", updatedInput?, updatedPermissions?}` or deny `{behavior:"deny", message?, interrupt?}`. Deny rules + hooks bind even under `bypassPermissions`. Subagents inherit parent mode; `AgentDefinition.permissionMode` overrides EXCEPT when parent is bypass/acceptEdits/auto. **`/goal` = built-in shortcut for a session-scoped prompt-based Stop hook** (https://code.claude.com/docs/en/goal) — the canonical "keep working toward a condition" surface the operator asked about (§5, decision #13).

## INHERITED FASHION (exists because Claude Code serves the general public / multi-surface / marketplace)

`MessageDisplay`, `Elicitation`, `ElicitationResult`, `UserPromptExpansion`, `Notification`/`terminalSequence`/desktop OSC codes, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `DirectoryAdded`, `Setup`, auto-mode LLM classifier + `PermissionDenied`, connector "organization set to `ask`", 4-tier settings-file `destination` precedence, `approve`/`block` deprecated aliases, prompt-type/agent-type LLM hook handlers, `/hooks` interactive menu. QMX is single-operator (Constitution P1): none of the above is required. Keep only the deterministic tool/task/agent-lifecycle spine.

## QMX-owned contract (proposal)

Python daemon, zero Claude-SDK dependency. Vocabulary is **closed for v1, addable via registry** (Constitution P5). Names in QMX ontology, not Claude's.

```python
# Closed core HookEvent vocabulary (v1). Extensible: HookRegistry.register_event(name).
class HookEvent(str, Enum):
    BEFORE_TOOL      = "before_tool"        # ≈PreToolUse   — observe/deny/ask/defer/modify_input/inject
    AFTER_TOOL       = "after_tool"         # ≈PostToolUse  — modify_output/inject
    TOOL_FAILED      = "tool_failed"        # ≈PostToolUseFailure
    AGENT_START      = "agent_start"        # ≈SessionStart+SubagentStart(unified; agent is the unit)
    AGENT_STOP       = "agent_stop"         # ≈Stop/SubagentStop — block→keep_working
    BEFORE_COMPACT   = "before_compact"     # ≈PreCompact — feeds Context Engine/Compaction (decision #46)
    PROMPT_SUBMIT    = "prompt_submit"      # ≈UserPromptSubmit — inject only
    TASK_CREATED     = "task_created"       # deterministic naming/schema gate on Task graph
    BEFORE_TASK_COMPLETE = "before_task_complete"  # THE determinism gate (decision #30): run verifier script; deny→reopen
    MISSION_START    = "mission_start"      # Mission contract activation (decision #20-22)
    MISSION_COMPLETE = "mission_complete"   # Mission termination/verification gate
    REVIEW_REQUIRED  = "review_required"    # ReviewPolicy hook (decision #31): author_family!=reviewer_family
    ENV_CREATE       = "env_create"         # ≈WorktreeCreate, generalized to ExecutionEnvironment (decision #63)
    ENV_REMOVE       = "env_remove"         # ≈WorktreeRemove
    AGENT_IDLE       = "agent_idle"         # ≈TeammateIdle — reassign/gate before a Bot sleeps

@dataclass(frozen=True)
class HookContext:            # what the daemon passes in — deterministic, no LLM
    event: HookEvent
    session_id: str; agent_id: str; agent_type: str
    bot: str | None; desk: str | None; mission_id: str | None; task_id: str | None
    tool_name: str | None; tool_input: dict | None; tool_output: Any | None
    cwd: str; env_id: str | None; payload: dict          # event-specific fields
    idempotency_key: str                                  # replay-safe (Constitution P6/P11)

class Decision(str, Enum):
    OBSERVE="observe"; ALLOW="allow"; DENY="deny"; ASK="ask"; DEFER="defer"; BLOCK_STOP="block_stop"

@dataclass
class HookResult:            # ONE union a Python hook returns; deterministic-first
    decision: Decision = Decision.OBSERVE
    reason: str | None = None                # shown to agent on deny/block_stop; to operator on ask
    updated_input: dict | None = None        # BEFORE_TOOL only (full replace)
    updated_output: Any | None = None        # AFTER_TOOL only
    injected_context: str | None = None      # → Context Engine, NEVER the Ledger (Constitution P12)
    ledger_entry: dict | None = None         # optional agent-authored record (decision #13 fusion, gated)
    stop: bool = False; stop_reason: str | None = None   # universal halt
    emit: list[str] = field(default_factory=list)        # side-effect fire-and-forget (metrics/bus), non-blocking
    verifier_ref: str | None = None          # id of the deterministic script that produced this (audit)
```

Rules QMX keeps from Claude: precedence `DENY > DEFER > ASK > ALLOW`; parallel hooks, most-restrictive wins; matcher = exact-list-or-regex against `tool_name`/`agent_type`; `injected_context` capped + spilled to file. Rules QMX adds: every hook is a pure Python callable or subprocess returning `HookResult` (no prompt/agent hook types — P2); `before_task_complete` and `review_required` are **required deterministic gates**, not optional; hook additions authored by agents go through the P9 promotion gate (candidate→validate→stage), never live. Registry keys by `(event, matcher, source)` where source ∈ {desk, role, mission, plugin} — mirrors Claude's `[settings]/[plugin]/[skill]` provenance labels but per QMX ontology, not per settings file.

## Open questions this reference cannot settle

- **Daemon language (transcript open #1):** Python SDK exposes only 10 in-process events vs TS ~31. If QMX wants native Worktree/Task/Teammate-idle *callbacks* it must either build them itself (recommended — QMX owns the contract anyway) or run a TS daemon. This is evidence for "QMX owns hooks bottom-up", not for adopting the TS SDK.
- **Ledger⇄hooks fusion (decision #13):** Claude offers `additionalContext` (→context) and no agent-authored ledger primitive. QMX's `HookResult.ledger_entry` is a QMX invention; the "keep agents working via to-do lists + task-completed" idea maps cleanly onto `AGENT_STOP` block + `BEFORE_TASK_COMPLETE`, but the semantics (compact, intentional) are QMX's to define.
- **Are graphs/loops hooks or separate (decisions #24-27)?** Claude conflates "keep working" into a Stop hook + `/goal`; QMX has explicit Loop/Graph primitives, so QMX must decide whether `AGENT_STOP`+`BLOCK_STOP` is the Loop engine or a lower gate under it. Unresolved here.
- **canUseTool vs hooks split:** Claude keeps a separate interactive `canUseTool` callback after the hook stage. QMX single-operator may collapse these into one `BEFORE_TOOL` ask-path; not decided.

## Sources (all checked 2026-08-28)
- https://code.claude.com/docs/en/agent-sdk/hooks
- https://code.claude.com/docs/en/hooks
- https://code.claude.com/docs/en/agent-sdk/subagents
- https://code.claude.com/docs/en/agent-sdk/permissions
- https://code.claude.com/docs/en/agent-sdk/python
- https://code.claude.com/docs/en/goal (referenced from hooks reference; not independently fetched)
- Not independently opened: https://code.claude.com/docs/en/agent-sdk/typescript — per-language event split taken from the authoritative Python/TS columns on the hooks SDK page and the python.md `HookEvent` literal.
