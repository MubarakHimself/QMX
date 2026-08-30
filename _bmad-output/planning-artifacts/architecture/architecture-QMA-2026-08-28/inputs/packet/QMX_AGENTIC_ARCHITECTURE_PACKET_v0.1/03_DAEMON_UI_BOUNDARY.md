# Daemon / UI Boundary

## Principle

QMX has two major products:

1. **QMX Daemon / Runtime**
2. **QMX Workbench UI**

They are connected by a versioned protocol.

## Daemon responsibilities

The daemon owns:

- Role/Bot/Agent runtime state
- Dialogue and RLM sessions
- missions and tasks
- graph execution
- loops
- hooks/policies
- skills
- model proxy/router
- provider auth integration
- context compilation
- memory providers
- knowledge/context retrieval
- tool registry and MCP adapters
- subagents
- agent-to-agent communication
- mailboxes
- scheduler/cron/routines
- workspaces
- Docker/remote/sandbox execution
- browser/computer provider adapters
- backtesting-framework integration
- desk/agent ledgers
- logs/traces/metrics/evaluation data
- artifact registry
- durable queues
- detached/background execution

## UI responsibilities

The UI owns:

- navigation
- rendering
- local layout state
- commands/palettes
- views/panels
- artifact visualization
- session inspection
- mission/task views
- ledgers
- trace/log viewers
- model/provider/settings management surfaces
- plugin management UI
- extension rendering
- notifications
- interactive approvals
- editor/terminal/browser display surfaces where appropriate

The UI must not own authoritative execution state.

## Protocol shape

Prefer a contract that supports:

### Commands

Examples:

- start mission
- send message
- steer agent
- stop run
- approve hook action
- install/enable plugin
- update configuration
- launch task
- retry task

### Queries

Examples:

- get bot
- list missions
- get graph state
- inspect ledger
- inspect trace
- list installed plugins
- get provider health

### Event stream

Examples:

- agent.started
- message.delta
- tool.started
- task.completed
- hook.blocked
- ledger.updated
- mission.updated
- worker.detached
- provider.cooldown
- artifact.created

The exact transport is not frozen. HTTP + WebSocket/SSE, local sockets, gRPC, or another transport can be evaluated.

## Attachment is a client state

Attached/detached should not define a different type of agent.

An agent can continue to run when:

- desktop UI closes,
- browser closes,
- laptop sleeps,
- another UI connects,
- the agent moves to a remote worker.

## Language consequence

Do not choose the daemon language based on UI convenience.

Do not choose the UI architecture based on scientific/Python convenience.

The protocol is the decoupling boundary.

## Preliminary stack hypothesis

Not frozen:

- UI host: Rust-based host is acceptable.
- UI extension rendering: likely web/WASM/declarative surface if hot-loadable third-party UI is required.
- Daemon/runtime: TypeScript is a strong candidate due to reference ecosystem and agent/plugin ergonomics.
- Scientific/RLM workers: Python remains a strong specialized runtime.

The architecture agent must compare this against an all-Rust or Rust+Python daemon before implementation.
