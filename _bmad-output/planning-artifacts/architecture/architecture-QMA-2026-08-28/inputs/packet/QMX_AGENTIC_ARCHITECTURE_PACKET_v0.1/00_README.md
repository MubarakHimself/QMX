# QMX Agentic Architecture Packet — Working Baseline v0.1

## Status

This packet is a **working architecture baseline**, not a final implementation specification.

It captures the latest converged decisions from the architecture discussion and deliberately separates:

- **Agreed principles** — decisions currently treated as architectural constraints.
- **Reference extractions** — ideas to study from external projects, not dependencies to adopt blindly.
- **Candidate designs** — strong proposals that still require technical validation.
- **Open questions** — items the architecture/coding agent should investigate before implementation.

The goal is not to clone Hermes, Pi, Claude Code, Grok Bot, BB, Cordis, OpenResearch, Prime Agent, OpenCodex, or any other framework. QMX is purpose-built for a quantitative research/trading organization. External projects are used to extract mental models, contracts, failure-mode solutions, and proven implementation patterns.

## Core Intent

QMX is a **distributed, extensible quant workbench and agent runtime** built for specific internal workflows rather than the general public.

It should support persistent organizational actors, long-running and detached work, distributed research/backtesting, multiple model providers, deterministic policy/hook gates, extensible tools and UI, strong context management, agent memory, mission/task orchestration, and deep observability.

## Non-negotiable architectural principle

**UI and daemon are separate products connected through a versioned contract.**

Closing the UI must not stop agents. Detached agents must continue to work, communicate, schedule tasks, write ledgers, and use remote compute without a client attached.

## Packet Map

1. `01_QMX_CONSTITUTION.md` — governing design principles.
2. `02_REFERENCE_EXTRACTION_MATRIX.md` — what to study from each external system.
3. `03_DAEMON_UI_BOUNDARY.md` — runtime/UI separation and process boundaries.
4. `04_AGENT_ONTOLOGY.md` — Desk, Role, Bot, Agent, Session, Mission, Task.
5. `05_PLUGIN_ARCHITECTURE.md` — plugin model spanning daemon, UI, worker, skills, tools.
6. `06_RUNTIME_SDK_SURFACES.md` — proposed in-house SDK contracts.
7. `07_MISSIONS_GRAPHS_LOOPS_HOOKS.md` — deterministic orchestration and control-flow primitives.
8. `08_CONTEXT_MEMORY_KNOWLEDGE_LEDGER.md` — critical state-system boundaries.
9. `09_MODEL_PROXY_TOOLS_COMPUTE.md` — model routing, tools, MCP, environments, distributed compute.
10. `10_UI_EXTENSION_MODEL.md` — simple mental model for extensible QMX UI.
11. `11_ARCHITECTURE_AGENT_BRIEF.md` — instructions for the architecture agent that will expand this packet into implementation design.

## Important

When the implementation agent reads the original transcript, it should prefer **latest explicit revisions** over earlier brainstorms. This packet is the first normalization layer over that transcript.
