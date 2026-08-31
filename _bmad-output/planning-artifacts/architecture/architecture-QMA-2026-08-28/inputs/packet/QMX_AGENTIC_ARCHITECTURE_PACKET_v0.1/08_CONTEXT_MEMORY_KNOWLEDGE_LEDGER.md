# Context, Memory, Knowledge, Ledger, and Observability

These systems are related but must remain separate.

## Context Engine

Question answered:

**What should this model invocation see now?**

Inputs may include:

- Role/harness instructions
- Bot state
- Mission
- active Task
- recent trajectory
- selected ledger entries
- recalled memories
- retrieved knowledge
- artifact excerpts
- tool descriptions
- model context budget
- prompt-cache strategy

Hermes is a primary reference for context assembly, compaction, tool/skill progressive disclosure, and prompt-cache stability.

## Compaction

Question answered:

**How do we reduce live conversational/session state without destroying continuity?**

Compaction is close to context and memory but is not identical to either.

Full transcripts may remain durable even when compacted context is used for subsequent model calls.

## Memory

Question answered:

**What learned/adaptive state is worth preserving for future work?**

Candidate memory types:

- episodic
- semantic
- procedural
- decision
- preference/policy
- entity/relationship

Memory providers should be pluggable.

Candidates include Hindsight, Mem0, LangMem, and other systems.

Do not commit to a custom memory backend until the QMX memory contract and evaluation criteria are defined.

## Knowledge

Question answered:

**What external/domain evidence does QMX possess and retrieve?**

Examples:

- papers
- books
- transcripts
- repositories
- broker docs
- strategy reports
- datasets
- market/microstructure research

Knowledge should preserve provenance/versioning.

Delphi/OpenScience are useful references.

## RLM

Question answered:

**How can an Agent operate programmatically over state/corpora larger than its immediate model context?**

RLM does not replace Memory or Knowledge.

RLM may expose handles to:

- papers
- backtests
- experiments
- market data
- repository
- knowledge
- artifacts
- memories

## Ledger

Question answered:

**What does the Agent believe is materially worth recording about its work?**

Ledger is agent-authored semantic institutional state.

Prefer Desk-level naming/organization:

- Research Ledger
- Development Ledger
- Analysis Ledger
- Trading Ledger
- PM Ledger

Entries may be scoped/indexed by:

- Bot
- Agent
- Mission
- Task
- experiment
- date

Hooks may require ledger updates at lifecycle boundaries.

## Observability

Question answered:

**What actually happened in the runtime?**

Harness-authored:

- logs
- traces
- spans
- metrics
- trajectories
- failures
- latency
- cost/tokens
- retries
- tool calls
- model calls

OpenTelemetry-compatible export should be considered.

Langfuse and similar systems are references for developer/evaluation UX.

## Cross-references

Ledger and observability are separate systems but can reference one another.

Example:

Ledger entry:
"Rejected H-81 after verification failure."

Optional links:
- `trace_id`
- `experiment_id`
- `artifact_id`

That enables forensic inspection without turning raw traces into the ledger.
