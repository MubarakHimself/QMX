# QMX Constitution

## 1. Purpose-built, not general-purpose

QMX is designed for a specific quantitative workflow: research, trading, development, analysis, PM/coordination, strategy experimentation, and distributed backtesting.

Do not copy complexity that exists only because a reference product serves the general public.

## 2. Deterministic infrastructure; probabilistic reasoning inside it

LLMs reason, synthesize, propose, critique, and decompose work.

Software should own:

- state transitions,
- validation,
- leases,
- task claiming,
- retries,
- schema validation,
- permissions,
- scheduling,
- routing,
- dependency checks,
- durable queues,
- backpressure,
- deterministic verification where possible.

Avoid making an LLM responsible for things ordinary software can guarantee.

## 3. QMX owns its contracts

QMX should build an in-house SDK/runtime surface.

References are used to extract patterns, not as the authoritative abstraction layer.

Provider adapters, memory providers, model providers, UI plugins, MCP servers, sandbox providers, and external tools should sit behind QMX-owned interfaces.

## 4. Daemon and UI are independent

The daemon is authoritative for agent execution and durable runtime state.

The UI is a client and extension host.

The UI may disappear for hours or days without invalidating running work.

## 5. Extensibility is a first-class requirement

Extensibility applies to:

- models/providers,
- tools/toolsets,
- MCP,
- skills,
- hooks,
- memory providers,
- context strategies,
- agent/role definitions,
- mission templates,
- loops,
- graphs,
- compute providers,
- browser/computer environments,
- artifact renderers,
- UI views,
- settings,
- commands.

## 6. Important state must outlive any single model context

Do not rely on chat history as the system of record.

Persistent state belongs in appropriate systems: missions/tasks, ledgers, artifacts, knowledge, memory, traces, logs, model/session state.

## 7. Context is compiled, not accumulated

Each model invocation receives intentionally assembled context according to role, mission, active task, model capability, memory retrieval, knowledge retrieval, recent trajectory, and available context budget.

## 8. Memory is selective

Memory is not the transcript, not the log, not the ledger, and not the knowledge base.

Memory is durable adaptive state that is expected to improve future work.

## 9. Self-improvement is gated

Agents may propose:

- memory updates,
- skill patches,
- hook additions,
- prompt changes,
- loop changes,
- role/harness changes.

Promotion into durable runtime state should initially require validation, evaluation, staged review, and/or deterministic policy gates.

## 10. Use the lowest-level capable environment

Preferred capability ladder:

1. API / structured tool
2. CLI
3. containerized program
4. browser automation
5. visual browser/computer-use
6. full persistent remote desktop

Do not spawn a computer when a CLI can do the job.

## 11. Reproducibility matters

Experiments and backtests should record immutable or content-addressed inputs where practical:

- code version,
- strategy version,
- configuration,
- data snapshot/reference,
- environment,
- model/harness version where relevant,
- parameters,
- seeds,
- cost assumptions,
- outputs.

## 12. Observability is not the ledger

Logs/traces/metrics are harness-authored telemetry for debugging and evaluation.

Ledgers are agent-authored semantic work records.

They may reference each other, but they are separate systems.
