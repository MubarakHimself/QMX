# Model Proxy, Tools, MCP, Browser/Computer, and Compute

## Model Proxy / Router

Primary reference: OpenCodex.

The first objective is not intelligent task classification. It is deterministic provider/account/deployment routing.

Responsibilities:

- provider translation/adapters
- multiple accounts/deployments
- auth integration
- health
- quotas
- rate-limit state
- cooldown
- load balancing
- failover
- thread/session affinity
- model aliases
- virtual model groups/combos
- optional future rankings/defaults

The harness/Role decides the model class/capability required.

The Proxy chooses a healthy eligible deployment.

## Cross-model review

Use policy/hooks rather than bespoke orchestration.

Example policy:

- Author model family != Reviewer model family for critical tasks.
- Workhorse outputs may require frontier review.
- Review result updates Mission/Task state or sends structured message back to authoring Bot/Agent.

## Tools

QMX owns the Tool Registry.

Tool sources may include:

- native tools
- CLI tools
- plugin tools
- MCP tools
- browser tools
- computer-use tools
- backtesting tools
- scientific/analysis tools

MCP is an adapter/protocol source of tools, not the QMX tool system itself.

## Tool assignment

Roles/Agents should receive only relevant capabilities.

Example:

Research:
- browser/search
- knowledge retrieval
- filesystem
- analysis
- research MCPs

Developer:
- filesystem
- git
- shell
- tests
- backtesting-framework tools

Trading:
- market
- portfolio
- execution
- risk-related tools

Plugins may add tools/MCPs later through settings without rewriting the Role core.

## Environment hierarchy

Use the minimum sufficient environment:

1. native/API
2. CLI
3. local process
4. Docker/container
5. remote container/host
6. browser
7. computer/desktop

Computer use is exceptional, not default.

## Persistent computer

A persistent Windows/Linux VPS can be registered as a capability/provider for tasks that truly require desktop/computer interaction.

Not every Agent should have access.

## Distributed compute

Primary use case: backtesting and research workloads.

The final provider decision is intentionally deferred.

QMX should first define a provider-neutral Compute/Environment contract.

Candidate execution targets:

- local
- Docker
- SSH/VPS
- Kubernetes/Slurm if ever needed
- inexpensive sandbox/compute vendors selected later
- dedicated backtest workers

## QMX Backtesting Framework

Use this exact name in later packets.

The framework should expose a stable service/API/CLI surface consumable by Agents.

Do not reduce the framework to the CLI.

CLI is one client surface over the same contract.
