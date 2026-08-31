---
review: adversary
target: ARCHITECTURE-SPINE.md (QMX Agentic System / QMA)
date: 2026-08-28
lens: 'Attack the spine. For every AD, build two units one level down that obey every AD to the letter and still build incompatibly.'
---

# Adversary review — QMA architecture spine

## Method

For each AD I built **two conforming units one level down** — the kind of thing an epic or a
factory lane would actually produce — and asked whether both can obey every written Rule and
still be unable to work together. Only pairs where **both readings are literal** are reported.
Every finding ends with the exact tightened Rule text, so the editor can paste it.

I also ran the Deferred table as an attack surface: a deferred row is a hole when two units
must *already* commit to incompatible shapes to build v1 at all.

---

## Verdict

**Return for amendment — do not freeze the wire or the persistence law yet.** The AD set is
unusually tight at the level of intent; it fails at the joints. Four load-bearing joints let two
conforming units build incompatibly today — the persistence law (AD-6 declares one append target
while the spine names six stores), hook phase (a `deny` is a gate in one unit and a notification
in another, so AD-24's "single enforcement point" is not one), Loop-to-Task expansion (two legal
Task Graphs from one Graph Template), and Task Ledger ownership (AD-9's single-author rule makes
AD-12's headline resumable Task unbuildable). Six more are high-severity, three of them in
`qma-wire` — the one contract the spine says must be fixed now because a second product will be
built against it. Two Deferred rows (UI presentation, desk consolidation) force divergence
**today** rather than later. Every fix but one is a contract tightening the editor can apply
without the operator; the exception is the word **promote**, which now carries three meanings,
one of them inherited from L17.

| Tier | Count |
| --- | --- |
| Critical | 4 |
| High | 6 |
| Medium | 14 |
| Low | 3 |

---

## CRITICAL

### C-1 — AD-6: "the only durable append target" is contradicted by the spine's own six stores

**Unit A (ledgers epic).** Reads AD-6 literally: the journal is *the only durable append target*,
so a Task Ledger entry is a journal record of kind `ledger.appended` and AD-9's "three stores"
are read-time projections. It inherits `journal_seq` ordering, replay through
`attach(since_seq=0)`, `fp1` identity and the deferred journal-retention rule.

**Unit B (ledgers epic, other lane).** Reads AD-8 and AD-9 literally — "Three stores exist",
"daemon store", and AD-23's explicit precedent that telemetry "lives in a separate store with
separate contracts" — and builds SQLite ledger tables written by the daemon behind
`before_ledger_append`.

Both obey every AD. What diverges: whether a ledger entry appears in the event stream a client
attaches to; whether AD-9's desk ledger *views* are folds over the journal or SQL queries;
whether a ledger append is ordered against the task transition it gates; whether ledger entries
survive a journal trim; whether they are fingerprinted. A third unit that folds the journal to
build the desk view returns a **complete** view against A and an **empty** one against B, with no
error anywhere. This is the load-bearing sentence of the whole spine and it is false as written —
AD-8 alone names six owners, and AD-18, AD-22 and AD-23 each name a further store.

**Tightened Rule (replace the AD-6 clause).**

> A single append-only journal with a global monotonic `journal_seq` is the only durable append
> target **for daemon-owned events**. Every other durable store is declared here, exhaustively,
> as one of two kinds. **Journal-derived projections** — rebuildable, never independently
> appended: per-scope event streams, mailboxes and delivery state, Task Graph state, desk ledger
> views. **Declared independent stores**, each with one named writer, its own retention rule and
> a stated rebuild status: the three ledgers (writer: the daemon on behalf of the authoring
> agent, through `before_ledger_append`; every append also emits a `ledger.appended` journal
> event carrying the entry's content hash, so ordering and replay stay journal-authoritative and
> the store stays rebuildable), the content-addressed artifact store, the telemetry store
> (AD-23), the AD-22 staging store, and the MemoryProvider's own store (AD-18). A store not on
> this list may not be created; adding one is a spine amendment.

---

### C-2 — AD-10: hook events carry no phase, so the same event is a gate in one unit and a notice in another

**Unit A (task graph / runtime).** Fires `subagent_spawn` after the Subagent record exists — the
name is phase-neutral and no AD says otherwise — and treats the `HookResult` as advisory.

**Unit B (permissions, AD-24).** Registers a `deny` handler on `subagent_spawn` to enforce
"a Subagent inherits no more than its parent" and to stop runaway spawning, because AD-24 names
hooks "the single enforcement point in the agent path" and AD-10 exists so agents are not "too
agentic".

Both conform. The deny is recorded and ignored. The same construction breaks `message_send`
(AD-20: "every send passes `message_send`" — does a deny stop delivery or annotate it after the
fact?), `env_create` / `env_remove`, `graph_transition` and `task_created`.

Worse, AD-10's own governing rule — *"every daemon-owned primitive ships with its own
before/after hook events; a primitive added without them is incomplete"* — is violated by AD-10's
own v1 registry: there is no `after_ledger_append`, no `after_memory_write`, no
`before_task_created`, and `mission_start` / `mission_complete` are unpaired. The registry that
is meant to be the closed enforcement surface is not conformant with the rule printed beside it.

**Tightened Rule (replace the AD-10 event-set clause).**

> Every hook event declares its phase in its name. `before_<primitive>` fires before the effect
> and is the only phase that may return a blocking decision (`deny`, `ask`, `defer`,
> `block_stop`) or `updated_input`. `after_<primitive>` fires only once the effect is durable and
> may return only `observe` or `updated_output`. The v1 registry is restated as pairs —
> before/after for: tool, task_create, task_complete, ledger_append, memory_write, skill_write,
> env_create, env_remove, subagent_spawn, message_send, graph_transition, mission_start,
> mission_complete — plus exactly two declared phase-less controls, `agent_stop` and
> `review_required`, both blocking. A handler whose decision value is not legal for its event's
> phase is refused **at registration**, not at run time.

---

### C-3 — AD-13: a Loop has no iteration law, so two conforming compilers emit two different Task Graphs

**Unit A (graph compiler).** Expands a `loop` node lazily: one Task per iteration, minted at
iteration time, each with its own Task Ledger. Legal — instantiation emitted Tasks and only
Tasks, the template was not mutated, no back-edge exists.

**Unit B (graph compiler, other lane).** Expands the loop body once and attaches the runtime-owned
`stopping_condition` to the emitted Task, so the *same Task re-executes* until the condition
holds. Legal by exactly the same three sentences.

Consequence: a 40-iteration loop is 40 Tasks / 40 ledgers / 40 independently resumable units in A,
and one Task whose single ledger accumulates 40 attempts in B — at which point AD-9's Task Ledger
("what happened, when, what failed and why") silently becomes the append log AD-9 exists to
prevent, and AD-12's "another Agent can be assigned it or resume it" means *resume at iteration
N* in A and *restart from zero* in B. Any mission-level count, budget or progress view is off by
an order of magnitude between the two. The same silence governs retry: no AD says whether a
failed Task is re-dispatched or superseded. AD-13 is already tagged `[ASSUMPTION] no graph-engine
implementation was studied`, which makes divergence more likely, not less.

**Tightened Rule (add to AD-13, cross-referenced from AD-12).**

> A `loop` node emits exactly one Task per iteration, minted at iteration time by the daemon.
> Iteration count, `stopping_condition` evaluation, `budget` consumption and `escalation` are
> **Task Graph node state** and are never Task fields. A Task is never a repeating unit: it is
> emitted once per iteration and reaches exactly one terminal state. Emitted Task ids are
> deterministic from `(task_graph_id, node_id, iteration, attempt)`, so replaying a run rebuilds
> the same graph. A retry after a terminal failure mints a **new** Task carrying `attempt_of` the
> predecessor's ref; re-dispatch of a still-open Task to a different Agent is a reassignment
> (C-4), not a retry.

---

### C-4 — AD-9 vs AD-12: "never shared between agents" makes the transcript-independent Task unbuildable

**Unit A (dispatcher).** Implements AD-12: on agent loss the Task is assigned to another Agent
and handed the Task's ledger ref — AD-12 says the Task *carries* its Task Ledger, and that is
precisely what makes it transcript-independent.

**Unit B (`before_ledger_append` gate).** Implements AD-9: the Task Ledger is "authored by the
worker agent executing it … never shared between agents", so it binds the ledger to its first
author and refuses a second agent's append — or mints a second ledger, breaking "one per Task".

With B in place, every resumed Task fails its own completion gate (AD-9: "a task-completion
transition requires a structured ledger append … or the completion is refused"), so the
operator's overnight resume story deadlocks. Without B, "never shared between agents" is dead
text and two agents interleave into one ledger with no attribution rule at all — and AD-9's own
requirement to record "which model and agent did what" has nowhere to live.

**Tightened Rule (replace the AD-9 Task Ledger clause).**

> The Task Ledger is owned by the **Task**, not by an Agent: exactly one per Task, for the Task's
> whole life, across every Agent that executes it. "Never shared between agents" is restated as:
> no ledger is ever shared between two **Tasks**, and no Agent may append to a Task it does not
> hold. Append rights follow a single dispatch lease — at any instant exactly one Agent holds the
> Task and may append. Every entry carries `attempt_no`, `authored_by` (the executing Agent ref
> plus its owning Quant's ActorId) and the model deployment that produced it. Reassignment or
> resume is itself a daemon-written entry (`kind: reassigned`, carrying outgoing agent, reason,
> incoming agent) and increments `attempt_no`. `before_ledger_append` refuses any append from an
> actor not holding the current lease, with a typed refusal.

---

## HIGH

### H-1 — AD-1: the law that prevents two owners has no scope key, does not cover every port, and ignores multi collisions

Three constructions, all against the one AD whose stated purpose is "prevents: two owners of one
port".

**(a) No scope key.** `research-corpus` registers a MemoryProvider with no scope; AD-8 says memory
is "scoped per desk and role", AD-1 says "singleton-per-scope" and never names the scope.
`analysis-backtest` registers one for its own desk. Is that a second binding of a singleton (a
hard startup error) or two legal bindings at different scopes? Both readings are literal — one
daemon boots and one refuses to boot on the same plugin set. `ContextCompiler`'s scope is never
named at all.

**(b) Uncovered ports.** `ComputeProvider` is in AD-1's port roster and in **neither** cardinality
list; so is `ToolAdapter`. Two plugins bind a docker ComputeProvider: the hard-error rule fires
only for declared singletons, so it does not fire, and AD-17's Compute Router now has two placers
for one environment kind — each unaware of the other's in-flight lease.

**(c) Multi collisions.** `graph`, `tool`, `skill` and `mission_template` are "multi", so nothing
stops two plugins registering `act-observe-verify` or a `backtest` tool. Roles grant toolsets *by
name*; Mission Templates reference graphs *by name*. Two conforming plugins, one resolved name,
and the Mission Compiler instantiates whichever registered last — silently.

**Tightened Rule (replace AD-1's cardinality sentence).**

> Every port and contribution point in the roster declares a **cardinality** and, when singleton,
> an explicit **scope key**; anything in the roster and absent from this table is a startup error.
> Singletons and keys: MemoryProvider per `desk`; KnowledgeSource per `source_id`;
> ExecutionEnvironment per `kind`; ComputeProvider per `kind`; ContextCompiler per daemon (one,
> global). Multi: tool, tool_adapter, hook, skill, **graph_template**, mission_template,
> model_deployment, command. Two bindings with equal singleton keys are a hard startup error
> naming both plugin ids, the port and the key. Every multi contribution is identified as
> `<plugin_id>:<local_id>`, unique across the daemon; a duplicate fully-qualified id is the same
> hard startup error; toolsets, Graph Templates, Mission Templates and Role grants reference
> fully-qualified ids only — a bare local id never resolves. `ui_view` is removed from the roster
> for v1 (H-6).

---

### H-2 — AD-5: `seq` has two possible referents, and a reattach silently loses events

**Unit A (query handler).** Stamps snapshots with `journal_seq` — AD-6 names the global monotonic
sequence as the authoritative one, and it is the only sequence AD-6 calls durable. The client
resumes with `attach(scope, since_seq=<that number>)`.

**Unit B (projection).** Resolves `since_seq` against the per-scope derived index, exactly as
AD-6 describes it ("a per-scope stream is a filtered projection whose `seq` is a derived index").

Both literal. The numbers are unrelated: a desk stream 40 events deep after 9,000 global events
resumes at 40 and the client believes it is caught up. **No error is raised in either direction** —
this is the silent-loss class, in the one contract the spine says must be frozen now because a
separately built UI will bind to it.

Second construction, same AD: `scope_path` has no pinned shape. Unit A serializes an ordered array
of `{kind, id}` segments; Unit B uses the options sheet's mapping `{desk, mission?, task?, …}`.
Both are "the full scope path". `fp1` canonical JSON is shape-sensitive, projection filters are
prefix-sensitive, and neither unit can consume the other's events.

**Tightened Rule (add to AD-5).**

> `seq` on the wire is always the per-scope projection index of the scope named in that message's
> `scope_path`, and `attach(scope, since_seq)` interprets `since_seq` in that same scope. A cursor
> is valid only for the scope that issued it; the daemon refuses an `attach` whose cursor scope
> does not match, with a typed refusal. The global `journal_seq` never appears on the wire under
> the name `seq`; where a snapshot must be positioned it carries `journal_seq` under that name and
> it is opaque to clients. `scope_path` is an ordered array of `{kind, id}` segments in the fixed
> order desk, quant, session, mission, task, agent, subagent, carrying every ancestor that exists
> for the record; filters match on prefix; the order is part of canonical JSON and never varies.

---

### H-3 — AD-10 / AD-11: a hook's source bounds nothing, so a mission-authored hook reaches another mission

AD-11 lets an agent author a hook from an approved template under six constraints. Every one of
them is about permissions, visibility, auditability and lifetime — **none is about which events
the hook can see**. AD-10 keys the registry by `(event, matcher, source)` and never says the
matcher is bounded by the source.

**Unit A (hook registry).** Treats the matcher as a pattern over tool names — the natural reading
of "matcher", and the Claude-surface precedent the whole hook design is modelled on.

**Unit B (mission runtime).** Assumes a mission-sourced hook only ever fires inside its own
mission, so it filters nothing itself.

Result: a hook authored by Mission M1's agent, permission-bounded to M1's permissions, fires on
Mission M2's `before_tool` and returns `injected_context` — which AD-10 routes straight to the
Context Compiler. That is one mission's agent writing into another mission's prompt, and it
satisfies all six of AD-11's constraints as written. The same shape yields cross-mission denial
(a DoS on another desk's work) and a read of another desk's tool inputs. This is the sharpest
security consequence in the review.

**Tightened Rule (add to AD-10; cross-reference AD-11 and AD-24).**

> A hook's `source` bounds the events it can ever receive. `mission` hooks receive only events
> whose `scope_path` contains that mission; `role` hooks only events of Agents instantiated from
> that Role; `desk` hooks only events under that desk; `plugin` hooks only the scopes its manifest
> declares and its permissions allow. The daemon applies the source bound **before** the matcher,
> and a registration whose matcher could resolve outside its source bound is refused at
> registration with a typed refusal. `injected_context` and `updated_input` from a `mission`-sourced
> hook may only reach an invocation inside that same mission.

---

### H-4 — Human-in-the-loop is minted five times with no shared contract, and `ask` has no resolution in an autonomous run

Five separate human gates exist and no AD says they are one mechanism: `ask` and `defer` as
`HookResult` decisions (AD-10, ordered but undefined), `approval gate` and `human gate` node kinds
(AD-13), the `approval_request` MessageKind (AD-20), the in-session operator confirmation for a
forward-only migration (AD-21), and operator-or-policy approval in the promotion pipeline (AD-22).
The surface that would carry any of them is deferred.

**Sharpest failure.** A Session with autonomy `autonomous` (AD-14) runs overnight with no client
attached — AD-5 explicitly permits this and AD-25 calls it the point of the system. A `before_tool`
hook returns `ask`. **Unit A** suspends the invocation waiting for a human; under AD-17 the job
holds its environment lease, so the environment is blocked "until an explicit recorded resolution"
that arrives at breakfast. **Unit B** resolves `ask` to `deny` after a timeout, consistent with
AD-10's fail-closed rule, and the mission takes a fallback path. Both conform; the operator's
stated primary use case works in one and stalls in the other.

`defer` is worse — it has a precedence position and zero semantics. Unit A parks the action and
performs it later *without re-running the hook chain*; Unit B treats it as "not now" and never
performs it. One of those silently executes, minutes or hours later, an action a subsequent policy
would deny.

**Tightened Rule (add to AD-10; cross-reference AD-13, AD-20, AD-21, AD-22).**

> `ask` and `defer` are defined here and nowhere else. `ask` suspends the invocation and emits one
> `approval_request` envelope to the owning Quant's mailbox (AD-20) — **the single human-approval
> channel**: AD-13's `approval gate` and `human gate` node kinds, AD-21's migration confirmation
> and AD-22's promotion approval all raise that same envelope kind and are answered by the same
> wire command. `ask` carries a required `ask_timeout` (registered configurable, AD-26) and a
> required `on_timeout` of `deny` or `escalate`. A Session whose autonomy is `autonomous` resolves
> `ask` to `deny` with reason `no_interactive_authority` unless its Mission names an approval route
> and a timeout. `defer` parks the request durably, **releases every lease it holds**, and re-runs
> the full hook chain from the start on resume; a deferred request is never performed on the
> strength of its original evaluation. An unresolved `ask` or `defer` never holds an environment
> lease.

---

### H-5 — AD-7: ActorId is parseable, desk consolidation is deferred, and the divergence is today's

AD-7 fixes `ActorId` as `quant:<desk_slug>/<quant_slug>`, "stable, never reused"; AD-20 stamps it
on every envelope, AD-9 on every ledger entry, AD-17 on every JobHandle owner.

**Unit A.** Stores ActorId strings as durable references and never parses them.
**Unit B.** Builds AD-9's desk ledger view by parsing `desk_slug` out of the ActorId — legal (the
grammar is fixed and published) and by far the cheapest index.

The Deferred table then revisits "Desk consolidation (five desks vs three vs two)… after the first
missions run". On the day two desks merge: B's index silently re-buckets or breaks; A's stored ids
resolve only if the retired desk slug is kept alive forever; and AD-7 forbids renaming, so the
only conforming move is to retire every Quant and mint new ones — abandoning every mailbox,
ledger and JobHandle owner reference in the system. The deferred row is cheap to keep open **only
if nothing parses the id**, and nothing says so.

**Tightened Rule (add to AD-7).**

> `ActorId` is **opaque to every consumer**. Desk membership is a field on the Quant record
> resolved through the registry and is never parsed out of an ActorId; no index, view, filter,
> permission check or route may read the slug substring. The desk slug inside an ActorId is
> historical identity only. A Quant's desk membership is mutable through an operator command that
> records a `desk_moved` journal event; the ActorId never changes. Desk slugs are never reused,
> and a retired desk keeps an alias row so historical ids remain resolvable.

---

### H-6 — Three v1 obligations are written against a UI the Deferred table says will not exist

**(a) `ui_view`.** AD-1 makes it a live multi contribution point while the Deferred row defers
"UI SDK surfaces, contribution points, UI plugin packaging, and the `qma-ui-contract` package
beyond a stub", and AD-5's closed vocabulary (9 commands, 7 queries, 10 events) has nothing for a
view. Plugin A ships a `ui_view` with an invented payload; Plugin B ships another with a different
one. Both conform; neither is describable by a schema `qma-wire` owns; and AD-5's "additive-only
within a major" compatibility authority has nothing to be compatible with.

**(b) "visible in the UI".** AD-11 makes UI visibility one of the six constraints that make an
agent-authored hook legal. **Unit A** treats it as satisfied by exposing the data over the wire and
ships the feature; **Unit B** treats agent-authored hooks as unavailable in v1 because a stated
constraint cannot be met. Both literal — one ships a privilege surface the other refuses.

**(c) AD-21's "the UI must show which of the two applies before install"** has the identical split
for forward-only plugin upgrades — the single genuinely irreversible operation in the spine.

**Tightened Rule.**

> Every v1 obligation is stated against `qma-wire`, never against a UI that does not exist.
> AD-11's visibility constraint reads *exposed through a named `qma-wire` query and included in
> the Mission's audit record*. AD-21's disclosure reads *the rollback mode is returned by the
> plugin-install command's preflight query, and the operator's confirmation is recorded as
> evidence with its `correlation_id`*. `ui_view` is removed from AD-1's roster for v1; UI
> contribution points are minted in the UI session together with their wire schemas. A
> contribution point with no `qma-wire` schema may not be registered.

---

## MEDIUM

### M-1 — "Promote" now means three things, one of them an inherited safety word

AD-18 gives MemoryProvider a `promote` method; AD-22 is the "promotion gate" for refinement
proposals; AD-25 and inherited **L17** reserve promotion for the act only a human may perform —
moving a registered artifact into the live zone; AD-14 adds registry "candidates". Two units: an
audit view filters journal events named `*.promoted` to prove the live-zone gate was honored and
collects memory promotions; a UI label reading "3 items promoted" cannot say which boundary was
crossed. Collapsing a money-path word into two agentic-layer verbs is exactly the collision class
the Conventions guard for Bot, Seat, Book and BMS.

**Tightened Rule.** Reserve *promote / promotion* for L17's live-zone act. Memory candidates are
**admitted** (`MemoryProvider.admit`, event `memory.admitted`); refinement proposals are
**applied** (`refinement.applied`) out of the **staging store**; only `artifact.promoted` carries
the inherited meaning. *(Vocabulary — operator's call, not the editor's.)*

### M-2 — Mailbox "bounded retention" vs the journal's retention exemption: one fact, two lifetimes

AD-20 says the bus has "bounded retention — the bus is not institutional memory". AD-6 says
mailboxes live in the daemon's store and the journal is the only append target; AD-23 and the
Deferred table say journal trimming is undecided and replay is exempt. Unit A trims envelopes at
the bound — deleting journal records and breaking `attach(since_seq=0)`. Unit B never trims,
because trimming is deferred, and the mailbox becomes the institutional memory AD-20 forbids.

**Tightened Rule.** The Mailbox is a projection over journal `message.*` events. AD-20's bounded
retention governs the **delivery projection only** — queue depth, ack cursor, redelivery window —
and never deletes a journal record. No journal record is trimmed until the deferred retention row
is decided under AD-23's exemptions.

### M-3 — ReviewPolicy's `author_family != reviewer_family` names a field that exists nowhere

AD-10 enforces it as a required gate. AD-15 defines Deployments with "a QMA-owned capability
record" whose named fields are `needs` flags, context, health, quota and cost — no family. Unit A
defines family as vendor; Unit B as ModelClass; Unit C as a model-name prefix. Under B a
`WORKHORSE_GENERAL` model reviewing its own output **passes**, and two different vendors' high
reasoning models are refused. The anti-self-review control — the operator's stated reason for
cross-model review — resolves by coin flip.

**Tightened Rule.** `model_family` is a required, operator-assigned field on every Deployment
record in the Deployment Registry (AD-15), independent of ModelClass and of provider account. The
ReviewPolicy check compares that field and returns the typed refusal `NoEligibleReviewer` when no
eligible deployment exists. It is a registered configurable variable (AD-26).

### M-4 — "The Analyst desk": a Role name used as a Desk name, gating the most expensive runtime

AD-7 makes Analyst one of the five **Roles**; AD-14 and AD-19 scope the RLM Runtime and the RLM
knowledge path to "the Analyst **desk**"; the plugin roster names the desk `analysis-*`. Unit A
gates the RLM ExecutionEnvironment on `desk == analysis`; Unit B gates it on the executing Quant's
Role being Analyst — and since Role:Quant is 1:N, that puts a persistent Python kernel on the
Research desk. The same paragraph also writes "the five **quant** roles", where `quant` is
simultaneously the spine's ratified actor noun and a scope value in AD-5.

**Tightened Rule.** The desk is **Analysis** (plugin prefix `analysis-*`); the Role is **Analyst**.
RLM Runtime v1 is scoped **by desk** to the Analysis desk, never by Role. The spine never writes
"the Analyst desk". "quant" is barred as an adjective — write "the five Roles", never "the five
quant roles" — because Quant is a distinct entity and an AD-5 scope value.

### M-5 — The single-in-flight lease is relied on by three ADs and defined by none

AD-17 mentions "its environment's single-in-flight lease" only inside the UNKNOWN sentence; AD-26
registers "single-in-flight lease overrides" as a configurable; no AD ever states the rule. Unit A
places many concurrent jobs per ExecutionEnvironment — nothing forbids it, and Docker-per-worker
implies many workers. Unit B enforces one and queues. AD-17's UNKNOWN blocking behavior is
meaningless in A.

**Tightened Rule.** An ExecutionEnvironment instance holds at most one in-flight job unless its
declaration sets `max_in_flight` (registered configurable, default 1); the Compute Router queues
the rest. `remote-host` and `desktop` kinds may not raise it above 1. An UNKNOWN job holds the
lease until an explicit recorded resolution.

### M-6 — The Quant Ledger has no schema and no boundary against the deferred Mission report

AD-9 gives the Task Ledger a precise content contract and a gate; the Quant Ledger is "a desk's
lead Quant keeps its own larger work ledger" — no fields, no writer rule (its own Agents? the
daemon? other Quants on the desk?), no boundary. Unit A writes mission-level synthesis there
(nothing forbids it, and the Deferred row only says no live *mission* ledger exists — which is
precisely how a deferred item becomes silent scope). Unit B builds the desk view expecting
quant-scoped work entries and cannot index A's records by task or experiment.

**Tightened Rule.** The Quant Ledger records desk-level work the lead Quant performs itself —
mission opened and closed, delegation, escalation, standing decisions — under one declared entry
schema, appended only through `before_ledger_append` by an Agent of that Quant under C-4's lease.
While Mission reports are deferred, a Quant Ledger entry never restates or synthesizes another
Task's ledger. The ledger belongs to the Quant and survives movement of the desk `lead` flag.

### M-7 — `_ref` vs `_id` is stated as law and broken by the spine's own contracts

Conventions: "cross-references carry a `_ref` suffix, never `_id` — the suffix is what says
reference rather than join". AD-19's Citation carries `source_id` and `snapshot_id` and its
KnowledgeSource "declares kind, source id"; AD-17's JobHandle "carries a job id"; AD-20's Envelope
carries "msg id". Two units disagree on whether the Citation field is `snapshot_id` or
`snapshot_ref` — and canonical JSON identity, hence `fp1`, differs between them.

**Tightened Rule.** A field naming a record's **own** identity is `id` or `<noun>_id`; a field
pointing at **another** record is `<noun>_ref`. Under that rule the Citation triple becomes
`source_ref`, `snapshot_ref`, `locator`; JobHandle carries `job_id` (its own) plus
`environment_ref` and `spec_ref`; the Envelope carries `msg_id` plus `mission_ref` / `task_ref`.

### M-8 — AD-14 invents a registry zone the parent owns

"QMA-zone candidate artifacts in the registry's dev zone" is either a new zone in a
`qmf-registry`-owned vocabulary — which AD-3 forbids — or redundant. Unit A registers to `dev`
with an `origin: qma` tag; Unit B mints a `qma` zone value and the parent's zone checks stop
recognizing it.

**Tightened Rule.** Delete "QMA-zone". Candidates are registered in the parent registry's existing
`dev` zone carrying a QMA-owned `origin` field; no QMA unit mints or extends a zone value.

### M-9 — No QMA-wide stop exists, so the first unit that needs one will reach for the platform's word

The operator's stated reason for hooks is stopping agents that get "too agentic". AD-10 has
`block_stop` (one invocation) and `agent_stop` (one agent). Nothing stops a desk, a Quant or the
daemon. AD-5's command vocabulary is closed-**and-addable**, so the first unit that needs it adds
one — and the natural English for it is the term the Conventions reserve to the platform (L36/L39).

**Tightened Rule.** Mint it here, named apart: `quiesce(scope)` — a wire command stopping new
dispatch at a scope of daemon, desk, quant or mission; running Tasks reach their own terminal
state; it never blocks a ledger append, a telemetry write, an evidence record or any risk-reducing
act, and it never touches the money path. **kill switch** stays the platform's word; no QMA
command, event, hook or control may use it.

### M-10 — Two record shapes in one staging store

AD-18: "candidates stage in the AD-22 promotion store". AD-22's store holds RefinementProposals
with `edits[]`. Unit A writes bare MemoryCandidates; Unit B refuses anything that is not a
proposal. The approval surface — already thin with the UI deferred — must render both.

**Tightened Rule.** A MemoryCandidate enters the staging store wrapped in a RefinementProposal
carrying exactly one `memory` edit. The staging store has exactly one record type.

### M-11 — AD-19's `search` lost its semantics between the options sheet and the spine

The sheet fixed `search` as literal/locator, grep-class, no index, no ranking. The spine says only
"v1 guarantees snapshot and locator reproducibility, not ranking, and ships no index". Unit A
implements substring/locator search; Unit B computes embeddings per call and ranks — no persisted
index, so still "ships no index". Citations differ per implementation and P11 reproducibility is
gone.

**Tightened Rule.** `search` is literal and locator-based over the CorpusSnapshot, grep-class
semantics, no ranking and no embedding. Any ranked or semantic retrieval is unavailable until the
deferred indexing row is decided.

### M-12 — Effective capability has four narrowing layers, no resolver, and a mid-run widening path

Role toolset ∩ `role.overlay` narrowing (AD-22) ∩ Mission narrowing (AD-16) ∩ subagent inheritance
(AD-16/AD-24). Unit A recomputes on every tool call — so promoting an overlay changes a **running**
Agent's capabilities mid-mission, which is a live privilege change through the very pipeline AD-22
exists to prevent. Unit B snapshots at spawn. Both "never widen" as written.

**Tightened Rule.** The effective capability set is computed once by the daemon at Agent spawn as
an ordered intersection — `role.base` ∩ `role.overlay` ∩ Mission ∩ parent, in that order —
recorded verbatim on the Agent record, and never recomputed for a running Agent. A promoted
overlay binds only Agents spawned after it.

### M-13 — Mission ownership is stored twice and can disagree

AD-7 and AD-12 both say a Mission is "owned by a Desk **and** a Quant", while AD-7 fixes a Quant's
desk in its identity and the ER diagram draws only `QUANT ||--o{ MISSION`. One fact, two fields:
Unit A keys missions under `desk_slug` and lets any Quant on that desk mutate them; Unit B treats
the owning Quant as sole mutator. Both conform, and nothing forbids `mission.desk` from
disagreeing with the owner's desk.

**Tightened Rule.** A Mission has exactly one owner, its Quant. The owning desk is derived from
the Quant record and is never stored on the Mission.

### M-14 — The Experiment Ledger has no writer rule for a multi-task experiment

The ER diagram lets any Task register an Experiment; AD-8 says ledgers are written by "the
executing agent". Two Tasks registering against one Experiment give two authors and no lease —
the same failure C-4 closes for Tasks, left open here.

**Tightened Rule.** An Experiment is owned by the Quant that registered it; its ledger follows
C-4's lease rule, with the owning Quant holding the lease and granting per-append rights to the
Agent of a registering Task.

---

## LOW

### L-1 — AD-1 and AD-21 name the contribution point `graph`, which the Conventions forbid

The Conventions say **Graph Template** (authored, stateless) and **Task Graph** (runtime state)
are "never interchanged", and then AD-1 and AD-21 register the contribution point as `graph`. That
bare word is exactly the ambiguity the name split was minted to kill. Rename to `graph_template`
in AD-1, AD-13 and AD-21 (already folded into H-1's rule text). AD-21 also omits
`register_mission_template` from its contribution roster although AD-1 and AD-12 both require it.

### L-2 — The Deferred row "Graph engine implementation choice" names a thing AD-13 forbids

AD-13 says a graph plugin "never owns the scheduler and never holds node state", so no "graph
engine" can exist; the row also uses the parent's banned-for-backtesting word. Rename the row to
**"Graph Template compiler/validator implementation choice"** and state that the compiler is a
pure, stateless, in-daemon function from `(template, bindings)` to Tasks.

### L-3 — Docker is `[UNVERIFIED]` while being the only isolation mechanism in the spine

AD-17 makes Docker-per-worker the default, AD-25 puts every worker in it, and AD-24 names the
container as the single isolation mechanism — against a Stack row with no verified pin. Verify and
pin it at the implementation gate, or state explicitly that isolation ships unpinned.

---

## Deferred table — divergence test

| Deferred row | Can two units diverge **today**? |
| --- | --- |
| UI presentation / `qma-ui-contract` | **Yes — H-6.** `ui_view` is a live contribution point with no schema, and two v1 obligations are written against a non-existent UI. |
| Desk consolidation | **Yes — H-5.** Anything that parses `desk_slug` out of an ActorId commits today to a shape consolidation breaks. |
| Mission reports | **Yes — M-6.** With no Quant Ledger schema, mission synthesis lands there by default and the deferral becomes silent scope. |
| Graph engine implementation choice | **Yes — L-2 + C-3.** The row names an artifact AD-13 forbids, and the loop-expansion hole is where it would be built. |
| Journal retention / replay window | **Yes — M-2.** AD-20's bounded mailbox retention already authorizes a trim the exemption forbids. |
| Knowledge indexing | **Yes — M-11.** "Ships no index" does not exclude per-call ranking; two retrieval semantics are legal now. |
| External memory backend | No. AD-18 makes `recall` unavailable until a provider is admitted; the staging path is stated (see M-10 for the shape fix). |
| Sandbox / compute vendors | No, once M-5's lease rule is stated — the ExecutionEnvironment singleton-per-kind rule holds the seam. |
| Browser stack | No. `ExecutionEnvironment` is singleton per `kind`, so a second browser binding is a startup error. |
| RLM beyond Analyst / depth > 2 | No, once M-4 fixes desk-vs-Role scoping; the depth cap is a registered variable. |
| Self-improvement evaluation gates | No. AD-22 ships invariants plus staging and names the switch-on condition. |
| Interactive walkthrough artifact | No. |

---

## What I did not find

Worth recording, because it bounds the review. I could not construct a conforming pair that
breaks: the money-path boundary (AD-16's registry-level prohibition plus AD-25 is genuinely
airtight — a `check_fn` cannot conjure an entry that does not exist); the secret egress rule
(AD-24's adapter-only `resolve` plus reference-only context types is structural, not
conventional — its only soft edge is M-7-adjacent naming); the `correlation_id` law (AD-5's
mint-once/copy-verbatim/refuse-at-the-gate leaves no legal second reading); AD-3's no-parallel-base
rule (M-8 is a violation *of* it, not a hole *in* it); and the `NoEligibleDeployment` no-substitution
rule in AD-15. Those five are the strongest contracts in the document.
