---
lens: data-integrity
target: ARCHITECTURE-SPINE.md (QMA, architecture-QMA-2026-08-28)
reviewer: reviewer gate — data-integrity lens
date: 2026-08-28
verdict: CHANGES REQUIRED
---

# Reviewer gate — data-integrity lens

## Verdict

**CHANGES REQUIRED — four critical.** The six-store separation itself is the strongest part of
this spine: AD-8's ownership table, AD-9's three-ledger split with desk ledgers demoted to views,
AD-23's telemetry/ledger firewall with a named retention exemption, AD-5's `id`-vs-`correlation_id`
law, AD-6's clock law with explicit IANA zones, AD-17's mandatory UNKNOWN, and AD-19's
`evidence_confidence`-vs-`promotion_confidence` name-split law are all sharper than the parent spine
required. The blur risk between the six stores is genuinely low.

What fails is not the *separation* of the stores but their *durability*. Four holes, each of which
loses or corrupts evidence rather than merely blurring it:

1. **Backup does not exist in this spine.** The word appears exactly once, in an inherited row
   pointing at two ADs that never mention it. L18 (DEC-0045) — a constitutional law, not a parent
   convention — is absent from the Inherited Invariants table. Under D21's spine law, off-machine
   backup is therefore out of scope for v1, and every ledger, journal, artifact, mailbox and staged
   candidate lives on one Windows disk with no second copy.
2. **AD-6 declares one durable append target while the spine operates at least six**, and no
   ordering key spans them — so the desk-ledger view (AD-9), which folds three stores, cannot
   satisfy the fold contract the Conventions row demands of it.
3. **Two control paths are wired to refuse the recording of evidence** — AD-10's fail-closed hook
   timeout on `before_ledger_append`, and AD-5's "a record without one is refused at the gate" for
   daemon-autonomous acts that have no minting origin. Both collide with L39 (DEC-0150) verbatim.
4. **The sole-writer invariant has no answer for a partitioned remote worker.** AD-25 deploys
   Quants, Missions and Workers off-host; AD-6 forbids them to open the store; AD-9 requires their
   Task Ledger to reach the daemon "through the wire". Nothing says what happens when the wire is
   down, and no wire command is idempotent — so the outcome is either lost evidence or duplicated
   evidence in an append-only store.

None of the four requires an operator ruling to close. Every fix below is inside the editor's
authority except the *destination* of the backup (a bucket, a vendor), which the parent spine
already ratified in shape and which can be carried as a Deferred row with the law itself binding now.

---

## Critical

### C1 — Backup and restore do not exist in this spine; L18 (DEC-0045) is not inherited

**Where:** Inherited Invariants row 11 (`Migrations, retention, backup discipline | parent AD-20 |
AD-21, AD-23`); AD-6; AD-21; AD-23; AD-25; Deferred.

The inherited row promises that backup discipline binds AD-21 and AD-23. AD-21 governs plugin
migrations and mentions no backup. AD-23 governs retention and mentions no backup. Grep the whole
spine: `backup` occurs once — in that row. There is no restore path, no second copy, no durability
statement, no Deferred row carrying it.

Two independent consequences:

- **D21 makes the omission binding.** "Anything on neither this table nor the Deferred table, and
  not in D1..D22, is out of scope for v1." Backup is on neither table. So v1 ships with the only
  copy of the event journal, the three ledger stores, the artifact registry, every Mailbox and the
  AD-22 staging store on one workstation disk (AD-25: "The daemon runs on the operator's workstation
  by default … mailboxes and the journal live in the daemon's store wherever it runs"). A disk
  failure ends the evidence corpus that three Deferred rows explicitly depend on (AD-23) and that
  AD-22's promotion pipeline is meant to accumulate.
- **The missing inheritance is a constitutional law, not a convention.** `docs/constitution.md`
  L18: *"qmf-data must retain complete raw evidence locally and maintain an off-machine backup.
  (DEC-0045)"* AD-6 puts QMA's persistence *behind `qmf-data` sinks* — so L18 binds QMA's stores
  directly and by its own words, not by analogy. It is not in the Inherited Invariants table at all.

There is also a **weakening of parent AD-20** that the spine's own rule ("A local decision that
would weaken one is a conflict to surface, not an override") requires be surfaced. Parent AD-20:
*"migrations run preflight checks → backup first → dry-run → migrate → verify, with a documented
restore path; never in-place mutation of the only copy."* AD-21 reduces this to *"migrations run
inside a daemon-held transaction preceded by a recorded journal checkpoint written as evidence with
the `correlation_id`."* A journal checkpoint is a marker inside the thing being migrated; it is not a
backup, there is no dry-run, no verify step and no restore path. A failed migration on a
`forward_only` plugin currently has no recovery at all.

**Fix (editor, no operator needed for the law itself):**

Add L18 to the Inherited Invariants table (`Complete raw evidence retained locally plus an
off-machine backup | L18 (DEC-0045) | AD-6, AD-21, new AD-27`) and mint one rule:

> **AD-27 — Durability, backup and restore [ASSUMPTION].** L18 (DEC-0045) binds QMA: the daemon's
> stores are complete evidence retained locally **and** copied off-machine. `qmf-data` supplies the
> backup/restore/verify primitives (parent CT-14/CT-26); QMA is the application and therefore owns
> the schedule and its execution (parent AD-20's application/ops split). v1: nightly, encrypted,
> versioned, off-machine copies of the event journal, the three ledger stores, the artifact
> registry, the mailboxes, the promotion staging store and the telemetry store, with an automated
> sample-restore test and a documented restore path; the destination bucket, key custody and
> rehearsal cadence are Deferred (they are ops-sitting territory) but the copies are not. A restore
> is a recorded operator act carrying its own `correlation_id`. **Migration law follows parent
> AD-20 unweakened:** preflight → backup → dry-run → migrate → verify, never in-place mutation of
> the only copy; AD-21's journal checkpoint is *in addition to* the backup, never instead of it.

Also add a Deferred row: `Backup destination, encryption key custody, restore rehearsal cadence |
the ops sitting; the AD-27 obligation binds now regardless of where the copies land`.

---

### C2 — "The only durable append target" is false against the spine's own stores, and no ordering key spans them

**Where:** AD-6 ("A single append-only journal with a global monotonic `journal_seq` is the only
durable append target"); AD-8 table; AD-9; AD-18; AD-22; AD-23; Conventions row 3.

The spine names at least six durable append targets:

| Store | Named in | Appended by |
| --- | --- | --- |
| Event journal | AD-6 | daemon |
| Task / Quant / Experiment ledgers ("Three stores exist") | AD-9 | the executing agent via gate hook |
| Artifact registry ("the artifact store") | AD-6, AD-8 | producing agent via the registry |
| Telemetry ("a separate store with separate contracts from the ledgers") | AD-23 | harness |
| Promotion staging store | AD-18, AD-22 | daemon on proposal |
| MemoryProvider store | AD-18 | provider |

So AD-6's sentence is not a rule an implementer can follow. It leaves the load-bearing question
unanswered: **is a ledger entry a journal event that the ledger projects, or a record in its own
store?** AD-6 says the journal "is the only durable append target" (implying projection) and in the
same rule says the journal "is **not** a ledger (AD-9)" (implying separation). AD-9 then says
"Three stores exist." The container diagram files the journal *and* the ledgers together under
`RECORD`. Both readings are defensible from the text, and they produce incompatible schemas,
incompatible retention and incompatible replay.

The integrity consequence is concrete and lands on AD-9's own construct. The Conventions row
requires "every read-time fold declares its fold contract (stream, ordering key, knowledge-time
bound, equal-instant disposition)". The **desk ledger view** is a read-time fold across *three
independent stores* indexed by seven keys. With three independent append targets and no shared
sequence, there is no ordering key and no equal-instant disposition available to declare — the fold
contract is unsatisfiable as specified. The same applies to any view joining a ledger entry to the
journal event that caused it, or to a `trace_ref` in telemetry.

**Fix (editor):** replace the sentence in AD-6 with a scoped version plus a cross-store ordering
law:

> The event journal is the only durable append target **for events**, and its `journal_seq` is the
> system's single total order. Every other durable store — the three ledgers, the artifact registry,
> the promotion staging store, the telemetry store, the provider-owned memory store — has exactly
> one append path, through the daemon, and **every append to any store is announced in the journal
> as an event carrying the appended record's `fp1` and the store id**. A record's `journal_seq` at
> announcement is its ordering key in every cross-store fold; equal instants are disposed by
> ascending `journal_seq`, never by timestamp. Announcement is what makes a cross-store fold
> reproducible; it is not a second copy of the record.

Then add to AD-9: `The desk ledger view declares its fold contract: streams = the three ledger
stores; ordering key = announcement journal_seq; knowledge-time bound = recorded_at (H4);
equal-instant disposition = ascending journal_seq.`

---

### C3 — Two control paths refuse the recording of evidence, against L39 (DEC-0150) verbatim

**Where:** AD-10 (fail-closed rule, `before_ledger_append` in the v1 event set); AD-9 (completion
refusal); AD-5 (`correlation_id` gate); Inherited Invariants row 15.

L39, quoted from `docs/constitution.md`: *"The exit-preservation invariant: no control action, of any
authority, at any scope, may block a risk-reducing act **or the recording of evidence**; the blocking
half of any control is entries only…"* The spine inherits it (row 15) but binds it to AD-25 alone —
i.e. treats it as a money-path rule. Its second clause is a **data-integrity** rule and it is
violated twice in this spine:

**(a) Hook fail-closed on the evidence path.** AD-10: "Hooks fail closed: a timeout resolves to
`deny` with reason `hook_timeout`." The v1 event set includes `before_ledger_append`. Therefore a
slow or hung hook — a subprocess verifier, a plugin hook, a machine under load — *deletes* a ledger
entry. It is not deferred, not quarantined, not retried (AD-17: "no component retries"): the
`deny` simply drops the agent's account of what happened. Then AD-9 compounds it: "a task-completion
transition requires a structured ledger append … or the completion is refused." So one hook timeout
both destroys the record of the work and blocks the task from completing — and the *reason* survives
only as a telemetry record, which AD-23 declares "not evidence." The system's most durable failure
mode is the loss of the exact record that explains a failure.

**(b) The `correlation_id` gate has no minter for daemon-autonomous acts.** AD-5: `correlation_id`
"is minted once at the originating operator command or scheduled trigger … and a record without one
is refused at the gate." Several records that *must* be written have neither origin: crash-recovery
and restart evidence, an AD-17 lease expiry, an UNKNOWN reconciliation, a retention trim (AD-23
requires it be recorded), an AD-21 migration checkpoint fired at load, a hook timeout on the
daemon's own startup path. Under the rule as written the gate refuses them — again, a control
blocking the recording of evidence.

**Fix (editor):**

- In AD-10, carve the evidence-recording path out of fail-closed:
  > Fail-closed binds every hook **except on the evidence-recording path**. On
  > `before_ledger_append`, a hook timeout resolves to `allow`: the entry is recorded and annotated
  > `hook_timeout` with the hook id and `correlation_id`, and the annotation is itself evidence.
  > `deny` on that event remains available only as an explicit deterministic decision, and a denied
  > append is **written to a quarantine stream with its reason**, never discarded — L39 forbids any
  > control, at any authority, from blocking the recording of evidence. Redaction of secrets stays a
  > schema check (AD-24), not a hook, so it is unaffected.
- In AD-9, add: `A refused completion never discards the append; the entry is recorded and the
  transition is what is refused.`
- In AD-5, name the third minting origin:
  > A daemon-internal lifecycle act — startup, crash recovery, lease expiry, UNKNOWN
  > reconciliation, a recorded retention trim, a migration checkpoint — mints its own root
  > `correlation_id` and records the originating reason. The gate never blocks a record for want of
  > an origin (L39).
- Extend Inherited Invariants row 15's "Binds here" from `AD-25` to `AD-25, AD-9, AD-10, AD-5`.

---

### C4 — The sole-writer invariant has no write path for a partitioned remote worker, and no wire command is idempotent

**Where:** AD-6 (sole-writer invariant); AD-9 (Task Ledger "persisted in the daemon store through
the wire so it survives the worker"); AD-25 (remote deployment from v1); AD-5 (commands acked
immediately); AD-17 (UNKNOWN); AD-20 (at-least-once, msg-id dedup).

AD-25 makes deploying a Quant, a Mission or a Worker to a remote workspace, the research node or a
sandbox "a first-class, UI-driven capability of the wire contract from v1." AD-6 forbids any of them
to open the journal, the SQLite file or the artifact store, and confines read-only folds to the
daemon's host. AD-9 requires the remote worker's Task Ledger to reach the daemon over the wire. The
spine then stops. Grep: `partition`, `offline`, `buffer`, `retry`, `reconnect`, `disconnect`,
`crash`, `restart`, `recover` — **zero occurrences.**

So the behaviour of a partitioned remote worker is undefined, and both of the available readings
lose integrity:

- **It buffers nothing.** Sole-writer as written gives the worker no local durable store, so an
  hours-long overnight run on a partitioned node produces no Task Ledger at all when the container
  dies. Evidence is silently lost, and AD-17's UNKNOWN does not cover it: UNKNOWN is a `JobHandle`
  state about the *job*, not about unacked appends.
- **It buffers and replays.** Then duplicates arrive. `at-least-once with idempotent msg-id dedup`
  exists in AD-20 for the **Agent Bus only**. AD-5 gives every message an `id` "minted by its
  producer" but never says the daemon dedups commands on it, and never bounds a dedup window. A
  reconnect after a dropped ack therefore appends the same ledger entry, the same artifact
  registration or the same memory candidate twice into an append-only store, where it cannot be
  removed and where every downstream fold double-counts it.

The same gap applies to remote telemetry: AD-23 declares telemetry harness-authored and AD-6
forbids any non-daemon writer, so a remote worker's tool-call spans must also cross the wire — at
much higher volume — through the same undefined path.

**Fix (editor):**

Add to AD-6, immediately after the sole-writer invariant:

> **Remote-worker durability.** A remote worker never opens a QMA store; it holds a **durable local
> outbox** — an ordered, fsynced spool of pending wire commands, explicitly *not* a journal, never
> read as evidence, never folded, and discarded on ack. On partition the worker keeps working and
> spools; on reconnect it replays the spool in order. **Every wire command is idempotent on
> `(producer_id, id)`**; the daemon holds a dedup cursor per producer whose window is a registered
> AD-26 variable, and a replayed command returns the original ack rather than appending twice. A
> worker's environment lost with a non-empty outbox resolves like AD-17: the affected Task's ledger
> is marked `unknown_tail` with the last acked `id`; nothing writes "no entry", and nothing
> fabricates the missing entries. Outbox depth and spool bytes are registered AD-26 variables and
> exhaustion blocks new work rather than dropping evidence (L39).

Add to AD-23: `Remote telemetry crosses the wire under the same outbox and dedup rule; telemetry
back-pressure is dropped in preference to evidence, and a drop is counted.`

---

## High

### H1 — AD-8's store roster is short by three: the event journal, Context and the promotion staging store have no owner row

**Where:** AD-8 (the inequality names six state kinds; the table has six rows but not the same six).

`MEMORY != LEDGER != KNOWLEDGE != ARTIFACTS != CONTEXT != TELEMETRY` names **CONTEXT**, which has no
row. The table adds Mission/Task Graph, which is not in the inequality. And the two most
consequential omissions are not in either:

- **The event journal** — AD-6's own store, the thing AD-6 says everything appends to, and the
  store this lens must separate from the ledgers. Its owner and write path are stated in AD-6 but
  never in the ownership table that is supposed to be the single place ownership is fixed.
- **The AD-22 promotion staging store** — durable, agent-originated, holding staged prompts,
  memories, skills, worker templates, hooks, graphs, loops and role overlays plus before/after
  snapshots, and doubling (AD-18) as the parking lot for memory candidates "until a provider is
  admitted." It is the one store in the spine whose contents are *agent-authored candidate runtime
  state*, i.e. exactly the material AD-22 exists to keep out of runtime — and it has no declared
  owner, no write path and no crossing rule.

**Fix (editor):** three rows in AD-8's table.

| State | Owner | Who may write | Crossing rule |
| --- | --- | --- | --- |
| Event journal | daemon | daemon only | journal events reference records by `fp1`; no evidence record references a journal entry |
| Promotion staging | daemon store | agent proposes as a command; daemon writes | staged content is never read by a runtime path; promotion emits a new definition record with a lineage edge |
| Context | Context Compiler, per invocation | nobody — never persisted | assembled from Memory recall, Knowledge citations and `injected_context`; discarded with the invocation |

And align the inequality: `JOURNAL != LEDGER != MEMORY != KNOWLEDGE != ARTIFACTS != CONTEXT !=
TELEMETRY != STAGING`.

### H2 — Knowledge snapshot reproducibility is guaranteed over bytes QMA neither owns nor keeps

**Where:** AD-19 ("`snapshot()` returns a CorpusSnapshot whose id is a content-addressed tree digest
with per-file digests"; "no write-back"; "v1 guarantees snapshot and locator reproducibility, not
ranking"); AD-8 Knowledge row (`Citation carrying source_id, locator, snapshot_id`);
`research/knowledge-corpus-boundary.md` line 98.

A tree digest identifies bytes; it does not retain them. The corpus is external, read-only,
operator-owned and (per the research) a live, moving vault. When the operator edits or deletes a
note, every prior Citation pinning that `snapshot_id` becomes unresolvable — and AD-19 forbids the
one remedy that would help (write-back). So the v1 *guarantee* of "snapshot and locator
reproducibility" cannot be honoured by QMA at all: it is a promise about somebody else's filesystem.

Two further unstated mechanics compound it. **When is `snapshot()` taken?** Per query, per mission,
per session? A moving vault yields a new tree digest on every save, so two agents on the same
mission cite different snapshots of the same sentence with no declared relation between them — and
no `supersedes` chain exists for snapshots (the parent's AD-16 linear-supersedes discipline is not
carried over). **What resolves a Citation later?** Nothing: `retrieve(ref, snapshot_id)` against a
snapshot that no longer matches the tree has no defined behaviour — silently returning current bytes
would be the worst outcome, since a memory candidate (AD-18) may have been promoted on the strength
of that citation.

**Fix (editor):**

- Add to AD-19: `On cite, the daemon copies the cited bytes into the artifact registry as a
  content-addressed evidence copy, and the Citation resolves against that copy — never against the
  live corpus. A retrieval against a snapshot whose tree no longer matches returns the typed refusal
  StaleSnapshot and never current bytes.`
- Declare the lifecycle: `A Mission pins exactly one snapshot at start; re-pinning mid-mission is an
  explicit recorded act carrying its reason, and snapshots of one source form a linear supersedes
  chain (parent AD-16).`
- Downgrade the guarantee to what QMA can hold: `v1 guarantees reproducibility of cited content and
  locators through the retained evidence copies; it guarantees nothing about the live corpus, which
  QMA does not own.`

### H3 — UNKNOWN stops at JobHandle; Task and Mission have no state vocabulary at all

**Where:** AD-17 (UNKNOWN mandatory); AD-12 ("the Task Graph is … the only place work state lives");
Conventions row 3 (the closed-and-addable list).

AD-17 forbids fabricating a terminal *job* outcome and does so well. But the discipline is not
carried into the store where work state actually lives. AD-12 never enumerates Task or Mission
states. The Conventions row lists every closed-and-addable vocabulary in the spine — hook events,
message kinds, delivery states, node kinds, ModelClass, JobHandle states, validation states — and
**Task state and Mission state are not among them.** Meanwhile AD-12 puts an LLM Mission Director in
the loop and lets agents "propose transitions as commands."

So the exact failure L35 exists to prevent is open one level up: a job resolves UNKNOWN, and nothing
in the spine stops a proposed transition writing `task.failed` into the Task Graph. That fabricated
terminal state then propagates into the Task Ledger, the desk ledger views, mission completion and
any future evaluation corpus — and it is append-only.

**Fix (editor):** add to AD-12 and to the Conventions closed-vocabulary list:

> Task state and Mission state are closed-and-addable vocabularies owned by the Task Graph:
> `pending | ready | running | blocked | unknown | done | failed | cancelled`. **The daemon refuses
> any proposed transition to a terminal state that is not evidenced**: a Task whose JobHandle is
> UNKNOWN may enter only `unknown`, holds its lease, and blocks its own completion until an explicit
> recorded resolution (AD-17). A Mission is terminal only when every Task is terminal; a Mission
> containing an `unknown` Task is itself `unknown`, never `failed`.

### H4 — No record carries a knowledge time, yet every fold must declare a knowledge-time bound — and not one QMA fold is named

**Where:** Conventions row 3; AD-6 ("Every fold declares its fold contract (parent convention)");
parent AD-19 ("Every external fact carries event-time, known-at, source, and revision"); AD-18
(MemoryCandidate "occurrence time" — the only bitemporal field in the spine).

The Conventions row demands four elements per fold: stream, ordering key, **knowledge-time bound**,
equal-instant disposition. QMA's records carry occurrence time only. There is no `recorded_at`,
no `known-at`, no revision, nothing distinguishing when a fact happened from when the daemon learned
it — so the third element of every fold contract in this spine is undeclarable. The parent spine
built its whole split/embargo law (AD-21) on that distinction; QMA drops it silently while claiming
to inherit "append-only evidence, read-time folds, every fold declares its fold contract."

Compounding it: **the spine names not one fold.** The parent named its folds (Book mode, seat state,
order state, bench counts, structure lifecycle). The options sheet named QMA's ("mission state, task
state, seat state, provider health"). The spine states the obligation and enumerates nothing, so
nobody can tell at build time which reads are folds and which are stored state — which is precisely
how mutable stored state gets introduced by accident.

Also unstated: the **representation**. The parent fixes `int64 UTC ns + per-writer sequence + stored
source resolution`. AD-6 fixes the *source* of time (`qmf-core`'s clock via the daemon) and the zone
law, but never the type — so an implementer may reasonably persist ISO strings and lose ordering.

**Fix (editor):** in AD-6, add:

> Every durable QMA record carries **`occurred_at`** (occurrence time) and **`recorded_at`** (the
> daemon's knowledge time at append), both int64 UTC ns from `qmf-core`'s clock, alongside its
> announcement `journal_seq`. Facts entering QMA from outside — Knowledge citations, QMB results,
> market data reached through a handle — additionally carry the parent's `source` and `revision`
> (parent AD-19); a provider revision is a new record, never an overwrite. **The v1 folds are:** the
> desk ledger views (AD-9), Task and Mission state over the Task Graph (AD-12), Mailbox delivery
> state and ack cursors (AD-20), Deployment and provider health (AD-15), and promotion state over
> the staging store (AD-22). Each declares its four fold-contract elements at implementation, and no
> read outside this list is a fold.

---

## Medium

### M1 — The event journal is classified three different ways

AD-6 and the Vocabulary table call it "infrastructure, never a ledger". The `.memlog.md` (line 34)
records it as "telemetry-side infrastructure". The container diagram files it under **RECORD**
beside the three ledgers, while telemetry sits in its own `TEL` box. AD-21 writes a migration
checkpoint into it "as evidence". Which it is decides three things this lens cares about: whether
L18's "complete raw evidence" obligation covers it, whether AD-23's retention exemption or the
Deferred journal-trim row governs it, and whether AD-5's `attach(since_seq=0)` replay is reading
evidence or telemetry.

**Fix:** one sentence in AD-6 — `The event journal is evidence: append-only, retained under the same
law as the ledgers, backed up under AD-27, and never trimmed while any record cites it. It is
neither a ledger (AD-9) nor telemetry (AD-23).` Correct the memlog line and keep the diagram's
RECORD placement.

### M2 — Retention is declared for two streams and undeclared for six stores, and "session-replay journal" collides with AD-6's journal

AD-23 exempts trajectories and "the session-replay journal". The Deferred table defers "Journal
retention and replay window". AD-20 gives the bus "bounded retention" with no bound and no AD-26
registration. **Nothing states a retention rule for the three ledger stores, the artifact registry,
the memory store, the staging store or the mailboxes** — where the parent is explicit ("Raw
originals and lineage are kept forever", parent AD-20).

Worse, AD-5 defines session replay as `attach(since_seq=0)` over the **AD-6 journal** — so
"the session-replay journal" and "the event journal" are the same store, which is simultaneously
retention-exempt (AD-23) and retention-deferred (Deferred table). An implementer reading only the
Deferred row will trim the exempt stream.

**Fix:** add a retention column to AD-8's table — keep-forever for the journal, the three ledgers,
the artifact registry, promotion decisions and lineage; bounded-and-AD-26-registered for the bus;
exempt for trajectories and replay — and in AD-23 replace "the session-replay journal" with "the
AD-6 event journal, which session replay reads", making the Deferred row read `Journal *trim* window
for non-exempt streams`.

### M3 — Migration law covers plugin-declared schemas only; the daemon's own stores have none

AD-21's `down` / `rollback: forward_only` / checkpoint / operator-confirmation machinery is scoped
to a `PluginManifest`. But `qma-daemon` versions will change the journal schema, the ledger schemas,
the task-graph tables, the mailbox and the staging store — none of which belongs to any plugin. The
Conventions row says "every serialized artifact stamps its contract format version", which covers
artifacts and not records.

**Fix:** in AD-21, add `Daemon-core migrations follow this rule verbatim — a declared down or
forward_only, operator confirmation for forward_only, checkpoint, and parent AD-20's
preflight/backup/dry-run/verify (AD-27).` In the Conventions row, widen the stamp: `every serialized
artifact **and every durable record** stamps its contract format version.`

### M4 — The `_ref` convention is stated and then broken by the spine's own field names

Conventions row 2: "cross-references carry a `_ref` suffix, never `_id` — the suffix is what says
reference rather than join." The spine then writes `Citation carrying source_id, locator,
snapshot_id` (AD-8, AD-19) — both pure cross-store pointers — and gives the Mission/Task Graph row
the crossing rule "**id** reference" (AD-8). AD-20's Envelope carries `msg id … reply-to and
causation ids`. With the discriminator unstated, no validator can enforce the rule and the "_ref
crossings only" invariant degrades to author discipline.

**Fix:** state the discriminator in the Conventions row — `a record's own identity fields are `_id`;
every pointer at a record owned by another store is `_ref`` — then rename the Citation fields to
`source_ref`, `snapshot_ref` (keeping `locator`), and change AD-8's Mission/Task Graph crossing rule
to `_ref`.

---

## Low

- **`causation_id` is never defined against `correlation_id`.** AD-20's Envelope carries both;
  AD-5's law governs only `correlation_id`. State that `causation_id` is the `id` of the record that
  caused this one, is per-record (never copied verbatim like `correlation_id`), and is likewise
  excluded from `fp1` identity — otherwise the two will be conflated in exactly the way AD-5 exists
  to prevent.
- **Three content-addressing schemes are named and never reconciled to `fp1`.** AD-19's "tree digest
  with per-file digests", AD-17's content-addressed `ExperimentSpec`, AD-14's "new content-addressed
  candidate" and AD-8's content-addressed artifact registry. AD-3 forbids re-deriving `fp1`, but a
  Merkle tree over files is not an `fp1` over a canonical JSON value. Declare the construction once —
  `a tree digest is fp1 over a canonical manifest of per-file fp1 values` — so snapshot ids are
  verifiable by the single implementation rather than by three private conventions.

---

## What this lens found sound

Recorded so a later pass does not re-litigate it:

- **Six-store separation holds.** AD-8's inequality plus AD-9's demotion of desk ledgers to views is
  the cleanest part of the spine; the "one global ledger" and "per-desk store" failures the operator
  ruled against are structurally impossible as written.
- **`id` vs `correlation_id`** (AD-5) is airtight on propagation, minting and `fp1` exclusion — the
  only gap is the missing daemon-autonomous minter (C3b).
- **UTC + IANA** (AD-6) is better than the parent required: naming quiet hours, cron, rollups, the
  ledger date index, timeouts and retention individually forecloses the two-hosts-two-meanings bug.
- **Telemetry/ledger firewall** (AD-23), including the one-way `trace_ref` rule and the
  retention exemption tied to named Deferred rows, is exactly the right shape.
- **Knowledge/Memory name-split law** (AD-19) — six opaque dimensions vs one scalar, never derived
  from each other — closes the provenance-collapse failure completely.
- **UNKNOWN at the JobHandle** (AD-17), including the lease hold and the no-retry clause, is a
  faithful adoption of L35; only its propagation into Task state is missing (H3).
- **Migration `down` / `forward_only`** (AD-21) correctly identifies data as the half LIFO cannot
  undo; it needs widening (M3) and un-weakening against parent AD-20 (C1), not replacing.
