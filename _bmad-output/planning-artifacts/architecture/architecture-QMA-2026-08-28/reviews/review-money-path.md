---
lens: money-path / safety
target: architecture-QMA-2026-08-28/ARCHITECTURE-SPINE.md
reviewer: reviewer-gate lens 'money-path'
date: 2026-08-28
gate: BLOCK — four critical inserts required before the spine leaves draft
---

# Reviewer Gate — Money-Path / Safety Lens

## Verdict

The four laws this lens exists to protect are each bound to a named AD, and the central move is the right one: **AD-16 makes the absence of an execution tool a registry-level fact rather than a permission policy**, and the Cut table refuses "paper only" explicitly. That is better than most systems built beside a live book ever get.

But at four points the boundary is **declarative where it must be mechanical**, and at those four points QMA v1 as specified is *not* structurally incapable of touching the money path:

1. **AD-16 prohibits three verbs** (order submit, amend, cancel) and nothing else. Binding a bot to a book, setting a Book mode or seat state, amending protection, minting a sizing decision, arming a kill switch and transitioning a zone are all money-path acts the parent spine governs (parent AD-29..AD-41) and all of them are unprohibited here. And the prohibition is stated as a fact about the v1 inventory — "no such tool exists" — with **no registration-time refusal** anywhere, while AD-16 simultaneously makes MCP servers "configured per desk and role from settings and upgradeable there."
2. **L17's human gate has no mechanism.** The wire (AD-5) authenticates a connection but never classifies a principal, and workers, plugin worker halves and remote deployments are all wire clients under AD-6's sole-writer rule. Nothing lets the daemon tell an operator's approval from an agent's. AD-22 then writes "operator **or policy** approval" while the Inherited table binds L17 to AD-22.
3. **AD-24's Credential Broker is unscoped over the OS secret store that holds the live venue credentials.** The operator's cTrader Open API credentials live in Windows Credential Manager on the same host the daemon runs on. AD-24 says a hook needing an authenticated call "makes it through a registered tool" — a registered HTTP or CLI tool plus a venue `credential_ref` is an order path that never contains the word "execution".
4. **Three ladder rungs are generic actuation.** AD-16's prohibition binds tool *names*; shell, browser automation and the AD-25 computer-use agent bind *acts*. A `curl` to the broker REST endpoint, or a click in cTrader Web on the Windows VPS, submits an order without any registry entry named for it. `ExecutionEnvironment` (AD-17) declares mounts, env vars and capabilities — it declares **no network boundary**, and `remote-host` is a legal kind with nothing stopping it naming the trading-node VPS.

Each of the four is closed by rule text, not by redesign. Below, every gap carries the exact Rule sentences that close it.

Secondary but material: the `qma-daemon -> qmf-risk, qmf-registry` import edge in AD-2 is unnarrowed (that is the money-path contract module and the zone owner); agent-authored hooks are forbidden from escalating "silently", which is the wrong word and has no validator behind it; the OpenCodex adapter's *value* egress into a third-party process is unaddressed while only its *files* are barred; and AD-10's fail-closed default makes a hook timeout block a ledger append — a literal L39 violation inside QMA today.

**Bindings check (as the lens requires):** L36 -> AD-16, AD-25 (named, present). L17 -> AD-22, AD-25 (named, present, mechanism missing — C2). L39 -> AD-25 (named, present, contradicted internally — H4). L34 -> AD-24, AD-15 (named, present, namespace unbounded — C3). "Paper is an account role on a real venue" appears in AD-16 and the Cut table (present, weakened by AD-25's phrasing — M1).

---

## CRITICAL

### C1 — AD-16's money-path prohibition is too narrow and is never enforced at registration

**Where:** AD-16, and the Cut-outright row "A Trading-desk execution tool, 'paper only' included".

**What is wrong.** Two defects in one rule.

*Scope.* The prohibited set is "order submit, amend or cancel". The parent spine's money path is far wider: bot-to-book **bindings** with `live | paper | stood-down` state (parent AD-29), Book mode `LIVE | PAPER`, seat state `active | benched`, `amend_protection` (parent AD-34), the exit-kind vocabulary (parent AD-33), control actions and the kill switch (parent AD-36), priority ranks (parent AD-37), sizing (parent AD-40), and registry zone transitions (L17). "Bind a bot to a book" is the act the lens names first and it is nowhere prohibited. AD-7 handles those nouns as a **naming** rule — "Bot, Seat, Book, BMS and kill switch are platform terms and never name an agentic actor or artifact" — which forbids QMA from *calling something* a Book and says nothing about QMA *writing one*.

*Enforcement.* "no order submit, amend or cancel tool exists in the registry, so no `check_fn` can make one available" is an assertion about the v1 inventory, not a law the registry executes. Compare AD-13 ("back-edges ... the validator rejects them at registration") and AD-22 ("the validator rejects any edit whose path resolves into a base") — AD-16 has no equivalent. Meanwhile AD-1 makes `tool` a **multi**-cardinality contribution point open to plugins, and AD-16 makes MCP "an adapter inside the registry, configured per desk and role **from settings and upgradeable there**." A broker MCP server named in settings surfaces order tools through a supported, documented path with no code change and no refusal.

**Fix — replace AD-16's prohibition paragraph with:**

> **Money-path prohibition (registry-level, enforced at registration).** No entry in the QMA Tool Registry may, directly or through an adapter, effect any of the following money-path acts at any account role, paper included: submit, amend, cancel or replace an order; open, close, reduce or hedge a position; set or amend protection (stop-loss, take-profit, trailing); size or re-size a position or mint a sizing decision; create, amend, activate, stand down or delete a bot-to-book binding; set or change a Book mode, a seat state, a Book or BMS parameter, a priority rank or a capital floor; arm, disarm or change the effect of a kill switch or any other node control action; or transition any registry artifact between zones. `register_tool` **refuses at registration** with the typed refusal `ProhibitedMoneyPathTool` naming the plugin id, the tool id and the matched act, and the refusal is a startup error, never a runtime deny. The check is a deny-list declared in `qma-core` beside the ladder, applied to every entry regardless of kind — native, CLI, plugin, MCP adapter, browser, computer-use, backtest — and evaluated **before** `check_fn`. An MCP server configured from settings has every tool it advertises passed through the same refusal at adapter registration, and a server advertising a prohibited tool is refused whole rather than partially bound. No `check_fn`, permission policy, Role, Mission, hook, toolset or settings change can lift the refusal: the deny-list is code, not configuration. Trading-desk tools remain read-only market data, read-only portfolio and positions, and risk calculation with no sizing authority (L36; paper validation is an account role on a real venue).

**Editor can apply without the operator:** yes. It tightens an already-ratified prohibition to the surface the constitution already governs; it adds no scope and spends nothing.

---

### C2 — L17's human gate is asserted but has no mechanism: the wire cannot tell an operator from an agent

**Where:** AD-5 (envelope and commands), AD-22 ("operator **or policy** approval"), AD-24 (auth), AD-25 (L17), Inherited row "Only a human may promote ... | L17 | AD-22, AD-25".

**What is wrong.** AD-24 says "the daemon authenticates before protocol bytes and never offers an unauthenticated bind" — that is *authentication*, and it is the whole of the wire's identity model. There is no *authorization* class. Under AD-6, "every write from anywhere else is a wire command", so a Docker worker running agent-authored code, a plugin's worker half, and a Quant deployed to a remote workspace are all authenticated wire clients. Any of them can send any command the envelope permits, including the one that approves an AD-22 promotion. The spine's only defence is that the operator is the one at the keyboard — which is policy, not structure, and it evaporates the moment an overnight mission runs detached (AD-25's own headline capability).

AD-22 then makes it explicit: the pipeline ends "operator **or policy** approval -> promotion." A *policy* approver is a machine approver. Because the Inherited table binds L17 to AD-22, an epic author will read that as the sanctioned implementation of "only a human may promote", and build one.

**Fix — add to AD-24 (and reference from AD-5):**

> **Principal classes.** Every authenticated wire connection carries exactly one principal class, `operator` or `machine`. The `operator` class is obtained only from an interactive human credential presented by a client a human is driving; workers, plugin worker halves, remote deployments, the scheduler, routines and cron, and every daemon-internal caller are `machine`, and no machine principal may acquire, delegate, borrow, cache or impersonate the operator class. The principal class is recorded verbatim on every command, journal entry, ledger entry and promotion record it produces. **Human-gate commands** — approval of an AD-22 promotion, any registry promotion or zone transition, confirmation of a forward-only migration (AD-21), resolution of an UNKNOWN job (AD-17), a retention trim (AD-23), and installation or enablement of a plugin — are accepted **only** from an `operator` principal and are refused from a `machine` principal with the typed refusal `OperatorPrincipalRequired`. There is no headless, scripted, scheduled or agent-initiated path to any of them.

**And amend AD-22's approval step to:**

> Approval is an operator act. `policy` approval exists only for edit kinds whose target lies entirely inside QMA's own definition store — `prompt`, `memory`, `skill`, `worker_template`, `hook`, `graph`, `loop`, `role.overlay` — and never for anything that reaches `qmf-registry`, a registry zone or a money-path record; there, L17 admits no substitute and the approving principal must be `operator` (AD-24 principal classes). Every promotion records the approving principal, the approval time and the artifact digest before and after.

**Editor can apply without the operator:** yes. L17 is inherited and non-negotiable; this supplies the missing mechanism rather than making a new choice.

---

### C3 — The Credential Broker is unscoped over the OS store that holds the live venue credentials

**Where:** AD-24 secrets paragraph; AD-15 ("QMA-owned credentials resolve from Windows Credential Manager (L34)").

**What is wrong.** The spine bars the *wrong* thing well and the *right* thing not at all. It bars plaintext home-directory credential files (Cut table, AD-15) — correct — and then points the QMA Credential Broker at Windows Credential Manager, which on this workstation is exactly where the operator's cTrader Open API credentials live (operator standing rule: broker creds under `qmx/*` labels in Windows Credential Manager, never in chat, repo or `.env`). Nothing in AD-24 scopes *which* references the QMA broker may resolve. The broker is described as resolving "references from the OS secret store" — full stop.

AD-24 then supplies the exploit path in its own words: "a hook needing an authenticated call makes it through a **registered tool**." A registered HTTP or CLI tool (both permitted, both on the ladder) plus a `credential_ref` naming the venue credentials is a complete order path that contains no tool named for execution and therefore survives C1's fix untouched. The egress rule as written is an *in-process object-reachability* rule — the value must not be "reachable from any object handed to a hook, plugin or graph" — and says nothing about *which secrets exist to be resolved at all*.

**Fix — add to AD-24:**

> **Broker namespace is a code-declared allowlist.** The QMA Credential Broker resolves only credential references on an allowlist shipped in `qma-core`: model and inference providers, compute and sandbox providers, corpus and knowledge sources, and telemetry sinks. Venue, broker, exchange, trading-node and platform-registry credentials are outside QMA's namespace and are resolvable by no QMA component under any Role, Mission, plugin or permission mode; a reference not on the allowlist returns the typed refusal `CredentialOutOfScope` naming the reference. The allowlist is source code — never settings, never a plugin contribution, never a UI-editable variable (AD-26), never widened by a Mission. The broker holds no ambient authority over the OS secret store: it resolves by exact reference from the allowlist and never enumerates, searches, lists or globs the store, so a credential QMA was not built to hold cannot be discovered by it.

**Editor can apply without the operator:** yes. It is L34 plus L36 made structural; it removes an authority nobody granted QMA.

---

### C4 — Generic actuation reaches the venue without any registry-named execution tool; environments declare no network boundary

**Where:** AD-16 capability ladder rungs 2–6; AD-17 `ExecutionEnvironment`; AD-25 (Windows VPS computer-use agent, trading-node VPS).

**What is wrong.** C1's prohibition binds tool *names*. The ladder's upper rungs bind *acts*:

- **CLI / containerized program.** A shell tool in a Docker worker can `curl` the broker's REST or Open API endpoint, run the trading node's own CLI, or `import qmf_venue`. AD-17 says the environment "is a declared allowlist, never a control channel" — but the declared fields are provider ref, image, mounts, **environment allowlist** and capabilities. There is no `network` field. Egress is open by omission.
- **Browser automation / visual browser / computer-use.** AD-25 registers a Windows VPS "carrying the single computer-use agent". A computer-use agent with a browser can open cTrader Web or the broker cabinet and click Buy. No tool in the registry is named for it; `computer.click` is the tool.
- **Persistent remote desktop and `remote-host`.** AD-17 lists `remote-host` as a legal environment kind. Nothing forbids registering the trading-node VPS as one. AD-25's "no agent workload runs there" is a statement about placement with no enforcement point, and the deployment diagram carries it only as a dotted negative label.

This is the gap the lens is most concerned with: the prohibition sits at the named-tool layer while three rungs of the ladder are below it.

**Fix — add a new AD, referenced from AD-16, AD-17 and AD-25:**

> ### AD-27 — Money-path reachability boundary
>
> - **Binds:** D11, D12, D15, D20; every ExecutionEnvironment, every ladder rung above the API rung, the computer-use agent, every worker image.
> - **Prevents:** an agent reaching the venue through a shell, a browser or a screen rather than through a named tool; the trading node becoming a QMA compute target.
> - **Rule:** AD-16's prohibition binds the **act**, not the tool name. No QMA agent, subagent, worker, environment, browser session or computer-use session may reach a venue, broker, exchange, trading-node or platform-registry control surface by any means, whether or not a registry entry describes it. `ExecutionEnvironment` carries a required `network` field with exactly two values, `none` and `allowlist` — there is no open default and no third value — and an environment is refused at registration unless an `allowlist` enumerates its reachable hosts. Venue, broker, exchange and trading-node hosts sit on a code-declared deny-list that no allowlist entry may name, directly or by wildcard. No QMA worker image may contain, install or import `qmf-venue`, a broker or exchange SDK, or the trading node's client, and image validation refuses one that does (parent L30: nothing imports `qmf-venue`). The `remote-host` and `desktop` kinds may not name the trading-node VPS or any host that carries a trading credential or a running node; registration refuses it by host identity, not by convention. The single computer-use agent runs on a profile whose browser carries no venue or broker session, cookie, saved password or password-manager binding, whose reachable-host allowlist is enumerated, and which may not be handed a venue login by any means — including one an agent reads out of Knowledge, Memory, a ledger or a tool result. Every violation is a **refusal at placement or registration**, never a hook deny, because a hook is inside the loop the boundary exists to contain.

**Editor can apply without the operator:** yes. Vendors and browser stack stay deferred; this constrains the negative space only.

---

## HIGH

### H1 — AD-2 grants the daemon an unnarrowed import edge to `qmf-risk` and `qmf-registry`

**Where:** AD-2 diagram, `DAEMON --> QMFLIB["qmf-registry, qmf-data, qmf-risk"]`.

**What is wrong.** The diagram is declared to be "the whole rule" and the edge is drawn with no narrowing. `qmf-risk` is the parent's money-path contract module (Book/BMS/binding records, exit contracts, control-action contracts, window contracts, CT-22..CT-32); `qmf-registry` owns the artifacts and the zones L17 protects. Excluding `qmf-venue` was correct and deliberate — but it is the *only* narrowing. AD-14 bounds `StrategyHandle` to dev-zone candidates; nothing bounds what the daemon itself may construct and write through these two libraries, and "bind a bot to a book" is a record write, not an order.

**Fix — add to AD-2's Rule:**

> The `qma-daemon -> qmf-risk` and `qma-daemon -> qmf-registry` edges are **read-and-calculate only**. QMA may import their value types, typed refusals and pure calculation surfaces, and may write only content-addressed dev-zone candidate artifacts through `qmf-registry` (AD-14). QMA may not construct, write, amend or delete a binding record, a Book, BMS or seat record, a control-action record, an exit or protection record, a priority rank or a promotion record, and may not call any zone-transition surface. The permitted surface of each edge is enumerated in `qma-core` and the enumeration is **default-deny**: a surface not listed is not callable, and adding one is a spine amendment, not a code change. `qmf-venue` is importable by no QMA package, worker or plugin (parent L30).

**Editor can apply without the operator:** yes.

---

### H2 — Agent-authored hooks: "silently" is the loophole, and none of the six constraints has a mechanism

**Where:** AD-11; AD-10's `HookResult`.

**What is wrong.** AD-11's sixth constraint is "**incapable of silently escalating privilege**". The adverb concedes that an *audited* escalation is permitted, which is not what the lens or the packet intended. And unlike AD-13 and AD-22, AD-11 names no validator: the six constraints read as authoring guidance, not as a registration-time check.

Worse, an agent-authored hook inherits the full `HookResult` union from AD-10, which includes three channels that are escalation surfaces regardless of the hook's permission bound:

- `updated_input` (before_tool) **replaces the whole tool input object**. A mission hook can silently rewrite the target of an otherwise-permitted call — the account, the symbol, the path, the endpoint — without holding any permission naming that target.
- `injected_context` writes into the Context Compiler, i.e. into *another actor's* context window, including a reviewer's under ReviewPolicy and any human-gate summary the operator reads. That is a prompt-injection channel authored by an agent, aimed at the reviewer and at the human gate C2 exists to protect.
- `ledger_entry` (gated) lets agent-authored code write evidence.

**Fix — replace AD-11's Rule with:**

> An agent may author a hook only from an approved template, only scoped to its own Mission, and only as an **`observe`-or-`deny`** hook: its `HookResult` may carry `decision`, `reason` and `stop` and nothing else, and the validator **rejects at registration** any agent-authored hook whose result type can carry `updated_input`, `updated_output`, `injected_context` or `ledger_entry`. An agent may block its own mission's act and record that it did; it may never rewrite a tool's arguments, a tool's output, another actor's context, or an evidence entry. The six constraints are mechanical, not editorial: the template is schema-validated at registration; the hook's permission set is computed as the **intersection** with the Mission's own and a hook naming a permission the Mission lacks is refused, never narrowed silently; registration writes a UI-visible record and a journal entry carrying the `correlation_id`; the disposer is pushed onto the Mission's exit stack so mission end removes it LIFO; and the hook may not register hooks, tools, plugins or contributions of any kind, may not raise its own registry `source` above `mission`, and may not match an event whose source class is wider than `mission`. The constraint is **cannot escalate privilege**, not "cannot silently escalate": there is no audited escalation path either. A mission-scoped hook becomes durable only through AD-22.

**Editor can apply without the operator:** yes.

---

### H3 — OpenCodex: the spine bars its *files* and not its *process*, and the proxy binds unauthenticated

**Where:** AD-15; AD-24 egress rule; Cut row "Plaintext credential files in a home directory".

**What is wrong.** AD-15 says QMA-owned credentials resolve from Windows Credential Manager "never from a third-party tool's home-directory files". That closes credential *ingest*. It does not close credential *egress*: nothing forbids a QMA Deployment from resolving a secret and **forwarding the value into the OpenCodex process** — the broker contract carries `auth_mode: forward` precisely for that, and OCX persists `usage.jsonl`, `routing-history.sqlite` and `service.log` under a home directory (`research/opencodex-model-proxy.md`, live install inspected 2026-08-28). AD-24's egress rule confines the value to "the model-proxy or provider-adapter egress call frame" — a frame that, for OCX, terminates in someone else's process with its own disk.

Second, from the same study: OCX "binds loopback with no auth by default". A QMA model plane reachable without authentication from anything on the workstation — including a Docker worker running agent code — is an unauthenticated command surface QMA depends on, in direct tension with AD-24's own "never offers an unauthenticated bind" (which binds the daemon only).

**Fix — add to AD-15:**

> No QMA-resolved secret **value** crosses a process boundary into a third-party tool. A provider adapter fronting an external local proxy is a QMA-owned adapter that authenticates **to** that proxy with a QMA-issued credential and forwards no upstream provider secret through it; `auth_mode: forward` is unavailable to any deployment whose endpoint is a third-party process. Provider credentials held by that third party stay its own — QMA neither writes them, reads them, nor treats its configuration or credential files as a QMA registry (AD-24 broker allowlist). QMA refuses to route to a local proxy endpoint that accepts unauthenticated connections: the deployment's health check asserts the endpoint rejects an unauthenticated request, and an endpoint that accepts one is marked unhealthy and excluded from routing rather than used. Any third-party proxy in the model path is one Deployment with a QMA-owned capability record and QMA-emitted routing telemetry, and has no read or write access to the QMA journal, store, artifact registry or Credential Broker.

**Editor can apply without the operator:** **no.** The rule text is straightforward, but the unauthenticated-bind clause can de-select OpenCodex if the operator's install cannot be made to require a bearer token, and D10 already carries "Operator must rule? Yes" on exactly this custody question. Draft the text, flag the consequence, let the operator confirm.

---

### H4 — Fail-closed hooks block the recording of evidence: an L39 violation inside QMA today

**Where:** AD-10 ("Hooks fail closed: a timeout resolves to `deny`"); AD-9 ("Entries are appended only through `before_ledger_append`"); AD-25 (L39 "belongs to the node").

**What is wrong.** L39 is unqualified: "no control action, **of any authority, at any scope**, may block a risk-reducing act **or the recording of evidence**." AD-25 confines it to the node — but AD-10 then mints, inside QMA, a control whose timeout **denies a ledger append**. A slow or crashed hook process therefore destroys the evidence of what an agent just did, which is the exact harm L39 names, in the exact place the spine promised to preserve it (AD-23's retention exemption protects the same records from a *policy* while AD-10 lets a *timeout* prevent them existing). The Inherited-invariants preamble says a local decision that weakens an inherited invariant is "a conflict to surface, not an override" — this one was neither surfaced nor overridden.

**Fix — add to AD-10, and cross-reference from AD-25:**

> **L39 binds inside QMA: no hook decision may block the recording of evidence.** `before_ledger_append` is a **validating** gate, not a blocking control: it may refuse a schema-invalid entry and nothing else. A timeout on `before_ledger_append` resolves to **`allow`**, with the entry annotated `hook_timeout` and a telemetry record carrying the `correlation_id` — never to `deny`; `block_stop` is not a legal decision on that event; and no permission policy, precedence resolution or permissive mode may produce a `deny` on a well-formed evidence append. Fail-closed remains the default on every other hook event, `before_memory_write` included — memory is promotion-gated adaptive state, not evidence, and its gate blocks by design.

**Editor can apply without the operator:** yes.

---

## MEDIUM

### M1 — "QMA runs against dev and paper zones only" reads as an operating grant, not a read boundary

**Where:** AD-25.

AD-16 and the Cut table both say paper is an account role on a real venue; AD-25 then grants QMA the paper zone without saying what QMA may *do* there. A reader building epics will implement "QMA may act in paper" — the exact sandbox reading the lens forbids.

**Fix — replace that sentence in AD-25 with:**

> QMA's access to the dev and paper zones is **read-only**, with one exception: content-addressed candidate artifacts in the dev zone (AD-14). Paper is an account role on a **real venue**, never a sandbox: QMA may read paper market data, paper positions and paper account state and may change none of it, and no QMA rule, tool, environment, permission or test treats a paper account as a place where an act is safe because it is not live. A QMA component needing a writable trading surface uses recorded evidence and QMB replay, never an account of any role.

**Editor can apply without the operator:** yes.

### M2 — Handle kinds are not a closed vocabulary, so a money-path handle is mintable

**Where:** AD-14 handle list; Conventions "State & cross-cutting" closed-and-addable list.

The Conventions row enumerates the closed vocabularies — hook events, message kinds, delivery states, node kinds, ModelClass, JobHandle states, validation states — and **handles are not among them**. A plugin may therefore mint `BookHandle`, `BindingHandle`, `OrderHandle` or `SeatHandle` and hand an agent a daemon-resolved reference onto the authority chain.

**Fix — add handles to the closed-and-addable list and to AD-14:**

> Handle kinds are a closed-and-addable vocabulary owned by `qma-core` — `BacktestHandle`, `ExperimentHandle`, `TradeLogHandle`, `StrategyHandle`, `KnowledgeHandle`, `MarketDataHandle` — extended only in that registry and never by a plugin. A handle over a money-path noun (order, position, binding, Book, seat, BMS, control action, kill switch, venue session) may not be minted at all.

**Editor can apply without the operator:** yes.

### M3 — A candidate artifact may carry risk, sizing and exit values with no diff at the human gate

**Where:** AD-14 `StrategyHandle`; AD-22 promotion; AD-25 "QMA never mints [risk, sizing, live-trading authority]".

`StrategyHandle` is bounded by **zone and mutability** — dev zone, candidates only, lineage edge — and not by **field content**. A candidate strategy necessarily carries fields that are sizing and exit inputs, so AD-25's "QMA never mints them" and AD-14's "may create candidate artifacts" are in tension, and the human who satisfies L17 approves a content-addressed blob with nothing forcing the money-relevant deltas in front of them. The human gate holds, but it holds blind.

**Fix — add to AD-14 and reference from AD-22:**

> A candidate touching a risk, sizing, exit, protection, binding or priority field is flagged `money_path_relevant` at creation, and the human gate refuses to render an approval for it without a field-level diff of exactly those fields against the artifact it descends from. QMA never mints a value for such a field where the ancestor carries none: an unset money-path field stays unset in the candidate and is filled only by a human (AD-25; corpus precedence — GitBook and trading-node documentation are authoritative for risk and sizing).

**Editor can apply without the operator:** yes.

---

## LOW

### L1 — AD-7's platform-term rule is a naming law that reads like a capability law

**Where:** AD-7 final sentence.

"Bot, Seat, Book, BMS and kill switch are platform terms (L36) and never name an agentic actor or artifact" is cited under the L36 banner and will be read by some as the L36 enforcement. It is a vocabulary rule and prohibits nothing.

**Fix — append to AD-7:**

> This is a naming law and confers no capability prohibition; the prohibition on acting on those nouns lives in AD-16 and AD-27. Naming and capability are stated apart so neither is mistaken for the other.

**Editor can apply without the operator:** yes.

### L2 — The deployment diagram carries the money-path boundary as a dotted negative edge

**Where:** Structural Seed, deployment diagram, `D -.->|"no agent workload, no order path"| TN`.

A negative label on a drawn edge is the weakest form the boundary can take, and AD-2 declares "an edge not drawn here is default-deny". Once AD-27 exists, redraw it as a labelled barrier rather than an edge, or annotate it `AD-27: refused at placement`, so the diagram states a refusal instead of a promise.

**Editor can apply without the operator:** yes.

---

## What is already right, and should not be weakened in the fix pass

- **Registry-level, not policy-level.** AD-16's insistence that the prohibition is not a permission policy is the correct instinct and every fix above extends it rather than replacing it.
- **`StrategyHandle` bounded to dev-zone candidates with a lineage edge** (AD-14) is a good, L33-shaped answer to the hardest handle.
- **`qmf-venue` absent from AD-2's dependency diagram** — deliberate and correct under parent L30.
- **UNKNOWN is mandatory and holds its lease** (AD-17) — the L35 discipline adopted honestly, with the adoption-versus-inheritance distinction stated.
- **No prompt-type or agent-type hook handlers** (AD-10, P-2) — the enforcement surface stays deterministic.
- **Cut outright: "A Trading-desk execution tool, 'paper only' included"** with the reason written out — the cut list is doing exactly the job D21 claims for it.
