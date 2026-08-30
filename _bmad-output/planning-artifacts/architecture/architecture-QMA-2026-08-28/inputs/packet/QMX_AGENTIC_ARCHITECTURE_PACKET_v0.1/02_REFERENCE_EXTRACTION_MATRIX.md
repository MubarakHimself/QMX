# Reference Extraction Matrix

The architecture agent should inspect the current documentation/code of each reference project and answer:

1. What problem did it solve unusually well?
2. What mental model produced the solution?
3. What are the important contracts/data structures?
4. What trade-offs and failure modes exist?
5. Which parts apply to QMX's specific use case?
6. What should QMX explicitly **not** copy?

| Reference | QMX should study | Do not assume |
|---|---|---|
| **Pi** | Minimal agent loop; extensibility philosophy; sessions; SDK/embed model; resource loading | That QMX should remain terminal-centric |
| **Hermes Agent** | Integrated harness mental models; skills; progressive tool loading; toolsets; MCP; plugins; context engine; compaction; memory provider interface; profiles; cron; browser/computer; self-improvement | That every Hermes implementation choice is optimal for QMX |
| **Claude Code / Claude Agent SDK** | Hooks; deterministic lifecycle interception; subagent lifecycle; permissions; task completion gates; worktree lifecycle | That Claude must be the underlying runtime |
| **Cordis / DeepSeek Harness** | Service dependency injection; reversible effects; plugin lifecycle; isolation; HMR; typed event modes | That Cordis itself must become the QMX framework |
| **BB** | Daemon/server/UI separation; provider bridges; multi-surface control plane; server/app/host plugin entries; UI contribution points | That BB's full-trust plugin model is acceptable unchanged |
| **Prime Agent** | RLM; persistent Python control environment; long-running daemon/worker/kernel separation; continual harness; agent-to-agent communication | That RLM is synonymous with memory |
| **Grok Bot** | Persistent named teammate mental model; routines; autonomous/background operation; team UX; asynchronous handoffs | General-public shared-computer assumptions |
| **Buzz** | Durable identities; relay/mailbox mental model; asynchronous communication independent of clients; auditability | Nostr as a required internal protocol |
| **Eve / agent-as-folder approaches** | Portable role/agent package layout: instructions, tools, skills, config | Exact directory format |
| **OpenCodex** | Local model proxy; provider translation; auth/account pools; quota-aware routing; affinity; cooldown; failover; virtual model combos | Its external policy/compatibility choices |
| **Hindsight** | Candidate memory-provider semantics; retain/recall/reflect; scoped memory banks | That it is the only memory backend |
| **Mem0 / other memory systems** | Retrieval/storage patterns; memory lifecycle; candidate comparison | Generic consumer memory assumptions |
| **OpenResearch CLI** | Distributed experiment execution; reattachment; compute backends; immutable run inputs; experiment lineage | Git branch per every parameter mutation |
| **OpenScience** | Research-loop mental model; bounded internal delegation; research workbench; skill/tool integration | Single-user-facing research agent architecture |
| **Delphi** | Versioned evidence/context engine; source provenance; indexed papers/repos/datasets | That retrieval = memory |
| **LangChain / LangGraph / Deep Agents / LangMem** | SDK surface comparison; graph/state patterns; memory APIs; checkpointing; interrupt/resume | Framework adoption by default |
| **Mastra** | SDK ergonomics; agents/workflows/tools/memory/evals/observability packaging | Product-level assumptions |
| **OpenTelemetry / Langfuse-style systems** | Traces, spans, metrics, trajectories, evaluation metadata | Conflating telemetry with agent ledger |

## Primary reference by subsystem

- Minimal agent runtime: **Pi**
- Integrated harness mental models: **Hermes**
- Hooks and subagents: **Claude Code / Claude Agent SDK**
- Plugin/service lifecycle: **Cordis**
- Backend + UI plugin architecture: **BB**
- RLM / continual harness: **Prime Agent**
- Persistent Bot/team UX: **Grok Bot**
- Agent communication: compare **Grok Bot, Buzz, Claude teams/subagents, Prime Agent**, and relevant A2A protocols
- Model proxy/routing/auth: **OpenCodex**
- Distributed experiments: **OpenResearch**
- Research workflow: **OpenScience**
- Evidence/context engine: **Delphi**
- Memory provider candidates: **Hindsight, Mem0, LangMem, others**
