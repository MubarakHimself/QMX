# Missions, Graphs, Loops, Skills, Prompts, and Hooks

## Mission

Mission = organizational contract.

Mission templates should be first-class and may contain meta-prompt instructions used by the Mission Lead to construct the initial task graph.

## Graph

Graph = topology/state/dependency structure of work.

A graph may contain:

- tasks
- conditional nodes
- parallel branches
- joins
- approval gates
- human gates
- deterministic scripts
- loops
- agents/bots
- artifact dependencies

### Graphs as plugins

**Strong candidate: yes.**

Graphs should be registrable as plugins/extension packages.

Example:

```text
graphs/
  research-discovery
  strategy-validation
  backtest-investigation
```

A graph definition should be versioned and validated against stable graph APIs.

Avoid letting graph plugins own the scheduler implementation.

## Loop

Loop = recurring execution/control dynamics inside a graph/node/agent.

Initial explicitly-authored loop registry:

1. **Act -> Observe -> Verify**
2. **Generate -> Critique -> Revise**
3. **Search -> Evaluate Coverage -> Expand or Stop**
4. **Hypothesis -> Test -> Learn -> Mutate -> Gate**
5. **Plan -> Execute -> Verify -> Replan**
6. **Discover -> Extract -> Normalize -> Rank**

Candidate QMX-specific loops to design during domain architecture:

- Research -> Backtest -> Analyze -> Iterate
- Strategy-component synthesis/mutation loops
- Book/BMS construction loops
- Research evidence saturation loops
- Bug reproduction/fix/verification loops

Do not let the system autonomously create production loops in v1.

Future loop-improvement process:

```text
trajectory pattern
 -> candidate loop proposal
 -> deterministic validation
 -> eval/simulation/replay
 -> review/promotion
 -> loop registry
```

## Skill

Skill = reusable capability/procedure/knowledge package.

A Skill can contain:

- instructions
- scripts
- examples
- references
- templates
- hooks
- tool declarations
- evaluation guidance

Skill != Loop.

A Skill may invoke a Loop; a Loop may use multiple Skills.

## Prompt

Prompt = invocation-time instruction/content.

Role instructions may include stable prompt sections, but Role != Prompt.

Prompts are assembled/compiled according to the context/harness architecture.

## Hooks

Hooks are a first-class deterministic interception surface.

Core hooks should be in-house.

Plugins/skills/missions may register scoped hooks subject to policy.

### Candidate in-house lifecycle hooks

- session start/end
- before/after prompt assembly
- before/after model call
- before/after tool call
- tool failure
- permission request
- before/after subagent spawn
- subagent completion
- before/after compaction
- before task complete
- task complete
- agent idle
- agent stop
- before ledger append
- before memory write
- before skill write
- before graph transition
- mission start/end
- workspace create/remove

### Mission-scoped hooks

Agents may be allowed to author **mission-scoped hook definitions** from approved templates/schemas.

Examples:

- Reject task completion unless test script passes.
- On subtask completion, require artifact schema.
- Before sending cross-agent message, validate required fields.
- Prevent backtest promotion unless required validation outputs exist.

Mission-authored hooks must be:

- schema validated
- permission bounded
- visible in UI
- auditable
- removable with the Mission
- incapable of silently escalating privileges

## Hooks + ledger

Hooks can trigger ledger prompts/requirements.

Example:

`TaskCompleted` hook can require the Agent to append a structured summary:

- what was done
- what changed
- evidence/artifacts
- unresolved issues
- next recommendation

This preserves agent-authored ledger semantics while using deterministic lifecycle enforcement.
