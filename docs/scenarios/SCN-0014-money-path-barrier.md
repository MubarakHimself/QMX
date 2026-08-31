---
id: SCN-0014
title: The Money-Path Reachability Barrier
type: scenario
status: ratified
component: COMP-QMA-DAEMON
depends_on: [COMP-QMA-CORE, COMP-QMA-DAEMON, COMP-QMF-CORE]
decisions: [DEC-0341, DEC-0327, DEC-0315, DEC-0316, DEC-0320, DEC-0324, DEC-0301, DEC-0347, DEC-0306, DEC-0375]
sources: [DEC-0341, DEC-0327, DEC-0315, DEC-0316, DEC-0324, DEC-0347, DEC-0375, _bmad-output/planning-artifacts/architecture/architecture-QMA-2026-08-28/ARCHITECTURE-SPINE.md]
generated: '2026-08-29'
verified: '2026-08-29'
stale_after: 30d
---

# SCN-0014: The Money-Path Reachability Barrier

This scenario pins the money-path reachability barrier end to end: an Agent on the Trading desk, and a plugin loaded for that desk, attempt in turn to reach the market, and every attempt is refused at registration or placement rather than deferred to a runtime hook. A tool that submits an order is refused at tool registration by the act-level deny-list; an unprovisioned `desktop` kind on a `ComputeRequirement` is refused at placement, and a `remote_host` or `desktop` environment naming the trading-node VPS is refused at registration by host identity; a plugin manifest declaring an execution tool fails its load; an `ExecutionEnvironment` without a `network` allowlist, or one naming a deny-listed venue host, is refused at registration; and a worker image importing `qmf-venue` fails image validation. Together AD-16's act-level deny-list and AD-28's reachability boundary are the barrier: nothing above a Bot touches the market, and paper is an account role on a real venue rather than a sandbox (constitution L36; DEC-0341, DEC-0327). QMA's only output into the money path is a candidate artifact a human promotes — never a binding, a sizing decision or an order (DEC-0324). [DEC-0341] [DEC-0327]

## Given

The Trading desk exists with `desk_slug` `trading` and a Quant `quant:trading/<quant_slug>` (DEC-0306). Trading-desk tools are read-only market data, read-only portfolio and positions, and risk calculation with no sizing authority; there is no execution tool at any account role, paper included, and the prohibition is an enumerated act-level deny-list declared in `qma-core` beside the capability ladder, not a permission policy (DEC-0315). The prohibited acts are exactly: submit, amend, cancel or replace an order; open, close, reduce or hedge a position; set or amend protection; size, re-size or mint a sizing decision; create, amend, activate, stand down or delete a bot-to-book binding; set a Book mode, a seat state, a Book or BMS parameter, a priority rank or a capital floor; arm, disarm or change a kill switch or a node control action; and transition any registry artifact between zones (DEC-0315).

The reachability half binds every environment and session: each `ExecutionEnvironment` carries a required `network` field with exactly two values, `none` and `allowlist`, and venue, broker, exchange and trading-node hosts sit on a code-declared deny-list no allowlist may name, directly or by wildcard (DEC-0327). Dependency direction is default-deny: `qma-daemon` reads-and-calculates `qmf-registry` and `qmf-risk` over an enumerated surface, and `qmf-venue` is importable by no QMA package, worker or plugin (DEC-0347, DEC-0301). A Trading-desk execution tool, "paper only" included, was itself rejected as a dead shape at the sitting — paper is an account role on a real venue, and no rule, tool, environment, permission or test treats a paper account as a place where an act is safe because it is not live (DEC-0375 is dead; DEC-0324). The trading-node VPS is untouched: no QMA agent workload runs there (DEC-0324).

## When

Four reaching attempts are made against the barrier, from an Agent of the Trading desk's Quant and from a plugin loaded for that desk — the second probes the compute path twice, an unprovisioned kind at placement and a trading-node host at environment registration:

```
register_tool        trading:submit_order        # attempt 1
compute.place        kind=desktop                                     # attempt 2a
env.declare          kind=remote_host provider_ref=<trading-node-vps>  # attempt 2b
plugin.install       trading-execution@1.0.0     # attempt 3 (manifest declares an execution tool)
env.declare          kind=docker network=allowlist hosts=[<venue>]   # attempt 4
```

None of these is a runtime request an agent can retry; each is a registration or placement the daemon evaluates and refuses.

## Then

**(1) The order tool is refused at registration (`ProhibitedMoneyPathTool`).** `register_tool` for a tool whose act is `submit an order` is refused at registration with the typed refusal `ProhibitedMoneyPathTool` naming the plugin id, the tool id and the matched act. The refusal is a startup error, never a runtime deny; the deny-list is evaluated before the tool's `check_fn`, is applied to every entry regardless of kind, and no `check_fn`, permission policy, Role, Mission, hook, toolset or `tool_adapter` change can lift it, because the deny-list is code, not configuration. An MCP server configured by a `tool_adapter` has every tool it advertises passed through the same refusal at adapter registration, and a server advertising one prohibited tool is refused whole rather than partially bound (DEC-0315, DEC-0341).

**(2) The unprovisioned kind returns `NoEnvironment` at placement; the trading-node environment is refused at registration by host identity.** A `ComputeRequirement` naming a `kind` no registered environment provides returns the typed refusal `NoEnvironment` naming that kind — the unprovisioned `desktop` kind is the v1 case (DEC-0316). A `remote_host` or `desktop` environment may not name the trading-node VPS or any host carrying a trading credential or a running node, refused by host identity rather than by policy; and the `remote_host` and `desktop` kinds may never exceed one lease, their `max_in_flight` pinned to 1 and `uneditable` (`registry:environment.max_in_flight`). Every violation of the reachability boundary is a refusal at placement or registration, never a hook deny at runtime (DEC-0327, DEC-0316).

**(3) The execution-tool plugin fails its load.** A plugin manifest that declares an execution tool is refused at load: the load-time refusal law aborts that plugin's load naming the offending unit, disposes its per-plugin scope LIFO so every contribution disappears together, and leaves the running daemon, every `dispatch_lease` and `environment_lease` it holds, and every running Task untouched; no load-time refusal terminates a running daemon or discards a pending evidence append (L39). The declared execution tool is refused by the same `ProhibitedMoneyPathTool` act-level check that gates a native tool, and a `tool_adapter` desk-and-role binding a manifest tries to declare is refused naming the plugin id and the field (DEC-0320, DEC-0315).

**(4) The venue-reaching environment is refused at registration.** An `ExecutionEnvironment` is refused at registration unless its `network` field enumerates an allowlist; an `allowlist` that names a venue, broker, exchange or trading-node host — directly or by wildcard — is refused because those hosts sit on the code-declared deny-list, and a `network: none` environment reaches nothing outward at all (DEC-0327). Image validation refuses any worker image that contains, installs or imports `qmf-venue`, a broker or exchange SDK, or the trading node's client (DEC-0327, DEC-0347).

## Failure branches

**Branch A — the computer-use agent is offered a venue login.** The single computer-use agent runs on a profile whose browser carries no venue or broker session, cookie or saved credential, whose reachable-host allowlist is enumerated, and which may not be handed a venue login by any means — including one an agent reads out of Knowledge, Memory, a ledger or a tool result. A supplied venue credential is refused at placement or registration, never accepted and deferred to a runtime check (DEC-0327). Until a `desktop` `ExecutionEnvironment` is registered against a provisioned host, every computer-use tool fails its `check_fn` and is excluded before its schema reaches the model, and the Compute Router returns `NoEnvironment` for a `desktop` `ComputeRequirement`; the Windows VPS is planned, not provisioned (DEC-0324, GAP-0070).

**Branch B — an agent tries to write a money-path record through the registry edge.** The `qma-daemon` to `qmf-registry` edge is read-and-calculate only. An attempt to construct, write, amend or delete a binding, a Book, a BMS or seat record, a control-action record, an exit or protection record, a priority rank or a promotion record — or to call any zone-transition surface — is not callable: the permitted surface is enumerated default-deny in `qma-core`, a surface not listed is not callable, and adding one is a spine amendment. The one write the edge permits is a content-addressed candidate artifact in the existing `dev` zone; a candidate touching a risk, sizing, exit, protection, binding or priority field is flagged `money_path_relevant` and its `approval_request` is refused unless it carries a field-level diff of exactly those fields, and QMA never mints a value for such a field where the ancestor carries none (DEC-0347, DEC-0301).

## Worked numbers

This scenario pins a refusal-and-authority flow, not an arithmetic computation, so there is no fixture number to freeze — and none may be invented. The load-bearing facts are refusals and the place each is raised:

- the money-path deny-list is **code, not a configurable** — there is no registry variable, `check_fn`, permission policy, Role, Mission, hook, toolset or `tool_adapter` value that lifts `ProhibitedMoneyPathTool`, which is what makes the prohibition a property of the build rather than of a setting (DEC-0315);
- every reachability violation is a **refusal at placement or registration**, never a runtime hook deny, so the barrier holds even where no tool is named for execution (DEC-0327);
- `paper` is an **account role on a real venue**, never a sandbox, so the barrier does not soften for a paper account (DEC-0324, DEC-0341);
- QMA's only money-path write is a **content-addressed dev-zone candidate a human promotes**; QMA mints no promotion or zone-transition command at all (DEC-0347, DEC-0324).

Two registry-referenced values appear in the walk: `registry:environment.max_in_flight` (default 1, `ui-editable`), the per-slot lease ceiling the `remote_host` and `desktop` kinds may never exceed — pinned to 1 and `uneditable` for those two kinds as a per-kind editability property of that one variable, never a second registry key; `registry:deferred.sandbox_refusal_count` is the AD-26 threshold that, once the Compute Router has recorded that many `NoEnvironment` refusals, opens the Deferred sandbox-and-compute-vendor question (GAP-0075). Both are referenced, never restated. The risk, sizing and live-trading authority named nowhere in this walk stays with the GitBook and trading-node corpus; QMA mints none of it, and this walk exercises none of it (DEC-0324).
