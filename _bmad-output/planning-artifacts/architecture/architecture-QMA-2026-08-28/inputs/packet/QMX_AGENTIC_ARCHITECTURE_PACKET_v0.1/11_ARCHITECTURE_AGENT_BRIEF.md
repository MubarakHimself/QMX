# Architecture Agent Brief

## Objective

Turn this working packet plus the exported architecture transcript into an implementation-ready architecture packet for QMX.

Do **not** start coding immediately.

First perform structured reference analysis and resolve the open contracts.

## Required approach

### Phase 1 — Normalize decisions

Read the transcript chronologically, but extract only:

- latest decisions
- superseded ideas
- unresolved disagreements
- explicit user constraints
- named reference projects
- QMX-specific domain requirements

Build a decision register.

### Phase 2 — Reference fan-out

Spawn focused research/reverse-engineering agents per subsystem.

Each agent should inspect current source/docs and answer:

1. What is the target mental model?
2. What concrete runtime/API structures implement it?
3. What failure modes were solved?
4. What should QMX reuse conceptually?
5. What should QMX reject?
6. What contract should QMX own?

Do not produce generic summaries of repositories.

### Phase 3 — Contract design

Design QMX-owned interfaces for:

- daemon protocol
- plugin manifest/lifecycle
- Role/Bot/Agent
- sessions
- missions/tasks
- graphs
- loops
- hooks
- skills
- prompts
- model proxy
- tools/MCP
- memory providers
- context engine
- knowledge
- RLM runtime
- mailbox/agent communication
- ledger
- observability
- artifacts
- compute/environment
- UI extension SDK

### Phase 4 — Architecture options

Where unresolved, produce 2–3 concrete options with trade-offs rather than guessing.

Important open questions:

- daemon implementation language: TypeScript vs Rust vs hybrid
- true Rust-native UI vs Rust/Tauri/web/WASM extension surface
- internal persistence/event model
- agent communication transport and durability
- graph engine implementation
- memory provider contract and first backend
- context/compaction architecture
- plugin trust/sandbox model
- remote worker protocol
- initial compute provider
- UI plugin packaging/versioning

### Phase 5 — Produce implementation packet

Suggested final packet:

1. Architecture Decision Record index
2. System Context
3. Daemon Architecture
4. UI Architecture
5. Protocol/API Contracts
6. SDK Specification
7. Plugin System Specification
8. Agent Ontology & Runtime
9. Mission/Task/Graph/Loop/Hook System
10. Context/Memory/Knowledge/RLM
11. Model Proxy & Provider Layer
12. Tool/MCP System
13. Distributed Compute & Backtesting Integration
14. Ledger/Observability/Evals
15. Persistence/Data Model
16. Security/Permissions/Trust
17. Deployment/Operations
18. UI Extension SDK
19. Reference Extraction Appendix
20. Implementation Phases / Epics

## Rules

- QMX is purpose-built for quant workflows, not general consumer agents.
- Prefer deterministic infrastructure.
- Do not adopt a framework solely because it already implements a concept.
- Do not clone blindly.
- Preserve extensibility.
- Preserve daemon/UI separation.
- Treat external SDKs as reference implementations.
- Explicitly identify where a proposed abstraction exists because of QMX needs versus inherited fashion.
