# Agent Ontology

## Desk / Profile

A Desk is an organizational and UI boundary.

Candidate desks may include:

- Research
- Trading
- Development
- Analysis
- PM/Coordination

The final UI may merge/split desks without changing the underlying runtime ontology.

## Role

A Role is a **declarative behavioral contract**.

It is conceptually close to a system/harness specification.

A Role may define:

- identity
- responsibilities
- default instructions
- default prompt sections
- skills
- toolsets/capabilities
- permission defaults
- model class/default
- memory policy
- context policy
- hook policy
- review policy
- allowed mission types
- agent/subagent policy

A Role is not a running process.

## Bot

A Bot is a **persistent named organizational actor** instantiated from a Role.

A Bot may own:

- name/identity
- Role reference
- Desk membership
- active and historical missions
- durable memory scope
- bot/desk ledger
- routines/schedules
- preferences
- configured capabilities
- mailbox/address
- long-lived relationships
- continuity across sessions

This is the persistent-teammate layer.

## Agent

An Agent is a **running reasoning/execution instance**.

An Agent may be:

- Dialogue-runtime agent
- RLM-runtime agent
- interactive
- autonomous
- semi-autonomous
- attached
- detached
- foreground
- background
- local
- remote

These should be runtime properties rather than separate ontology classes.

## Subagent

A Subagent is an Agent spawned/delegated by another Agent.

Subagent architecture should primarily study Claude Code / Claude Agent SDK, with Hermes and Prime Agent as secondary references.

## Worker

"Worker" should be treated cautiously.

Recommendation: use Worker primarily as an **execution/deployment concept**, not an organizational identity.

Example:

- Research Bot spawns Agent A.
- Agent A is placed on remote Worker W-17.
- Worker W-17 is a Docker/container/remote execution slot.

This prevents "Worker" from duplicating Agent semantics.

## Mission

A Mission is an executable organizational contract broader than a task.

Mission fields should include:

- intent
- scope
- non-goals
- success criteria
- evidence requirements
- available capabilities
- allowed models/compute
- budgets
- expected artifacts
- verification policy
- escalation rules
- stopping/termination conditions

A Mission Lead may use meta-prompting to decompose the Mission.

## Task

A Task is a bounded executable unit inside a Mission.

Tasks are persisted independently of agent conversations.

A task may be reassigned or resumed by another Agent without requiring the previous Agent's full transcript.

## Session

A Session is a runtime interaction/history container.

Two core execution models:

1. Dialogue runtime
2. RLM runtime

Independent dimensions:

- attached / detached
- interactive / semi-autonomous / autonomous

Do not equate "background" with "RLM".
