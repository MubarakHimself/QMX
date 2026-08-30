# Re-gate review — RUBRIC WALKER + AMBIGUITY HUNT

**Target:** `ARCHITECTURE-SPINE.md` (950 lines, TN-1..TN-25, `status: draft`), as it stands AFTER
fix-pass-1 (150 findings from six lenses) and AFTER the four operator rulings of 2026-08-28.
**Lens:** good-spine rubric walk + sentence-level ambiguity hunt.
**Method:** spine read in full; `.memlog.md` read in full (50 entries); `inputs/parts-bin.md` §3
seams and its do-not-default list checked row by row against the spine's Ports table, TN-18's
blank list and the mint table; `reviews/fix-pass-1.md` read so nothing already closed is
re-reported. Every finding below names the spine sentence it is against.
**Reviewer stance:** this lens certifies the CURRENT text. Nothing the first gate found and the fix
pass closed is restated.

**Verdict: CONDITIONAL PASS — changes requested before ratification.**
4 critical, 10 high, 14 medium, 7 low. Nothing here needs the operator: every finding is closable
at desk from text already in the spine. No finding contradicts an operator ruling.

---

## 1. What the re-gate CONFIRMS (the rubric's pass rows)

These were checked and are clean; they are recorded so the next gate does not re-walk them.

**Operator rulings applied faithfully.** The "Operator rulings 2026-08-28" section (lines 892-904)
was diffed sentence-by-sentence against `.memlog.md` entry 48. All eleven quoted fragments —
"there is nothing like commands or anything… it's a user interface on the desktop application as
per the overall architecture", "the same setting or the same logic behind even the agentic system",
"might have its own page… I'm not certain yet", "first, make the trading node work, make sure it
can execute", "a very separate system, like how big tech teams work", "that question is not for
this layer", "two days to a week… I think a week is enough and sufficient", "I know what you're
talking about", "a simple click on the user interface… two separate acts", "doesn't concern you…
focus on live trading", "I will not pay for news", "later versions, yes, we're going to iterate",
"if we haven't, leave it for now" — reproduce the memlog verbatim, in the right ruling, with the
right consequence. R1-R4 and the "also ruled" paragraph carry every consequence entry 49 lists.
No paraphrase inflates a ruling.

**No operator command line survives anywhere.** Grep for `CLI`, `command line`, `qmn <verb>` finds
only (a) the ruling itself, (b) the withdrawal of the old reconciliation note, (c) the `click`
stack row explicitly marked NOT TAKEN. Every former command is a `just node-…` recipe (TN-1:130,
TN-12:405, TN-13:417-418, TN-15:455, TN-16:471, TN-17:496-497, TN-21:554) and each is stated to be
DevOps tooling that acts only through the doors. The Structural Seed's `doors/` carries `api/` and
`http/` and no `cli/`.

**Banned vocabulary honoured.** No "engine", "kernel", "plugins", "exam", "minimal core", "paper
node", "timeframe", bare "calendar", bare "stop-out". The asyncio loop is called the event loop.
"One product, two modes `paper | live`" is stated in the paradigm, TN-1, and the conventions row.

**Structure and mechanics.** Frontmatter present and complete (name/type/purpose/altitude/scope/
status/created/updated/binds/parent/siblings/sources/companions/provenance); no template comment
or placeholder anywhere (zero `<!--` in the file); six fenced mermaid blocks, all balanced, all
with a valid header (`graph TD` ×3, `graph LR` ×2, `sequenceDiagram` ×1), every one carrying at
least one edge, and no label containing a parenthesis, a pipe or a quote — all six parse.

**Every parts-bin §3 seam is homed.** All 25 rows of `inputs/parts-bin.md` §3 appear in the spine's
"Ports the node implements" table with the same file:line citation, plus two additions the
inventory justifies (`ConnectionManager` as a qmf-venue increment, `qmn.venue.VenueClientPort` as
node-minted). No TN assumes a port that does not exist without minting it — with one exception,
`NotificationChannel` (M4 below).

**Dimensions the altitude owns.** Deployment (TN-16), environments — **one environment, decided,
with compensating controls named** (TN-16:473) — infra/provider (bucket = deployment config; VPS
plane declared), operations (TN-1 toolkit, TN-16), upgrade/rollback (TN-16:471, deployment-record
pair), secrets (TN-12), monitoring (TN-15 + the ruled observability stack), alerting (TN-15's three
classes + dead-man's switch), backup/restore (TN-13, three drills, two RTOs), time (TN-14),
capacity (TN-13:425), door authentication (TN-17 `SO_PEERCRED` — partially, see M5), MIS training
(Deferred, named epic), UI seam (TN-17:486, 498; Deferred row). All decided, deferred or open with
a consequence stated.

**Assumption register hygiene.** Every inline `[ASSUMPTION Ax]` tag has a register row and every
register row A1-A39 has an owning TN that mentions it; A8 is correctly marked RETIRED and no longer
appears inline. No assumption BLOCKS a builder: each states a recommendation the builder proceeds
on. (One numeric error in the frontmatter, M14.)

**Deferred rows** were tested for "does this let two units diverge". Only one does (M10).

---

## 2. CRITICAL

### C1 — "Anything the soak checklist exercises is soak-blocking" is a rule whose own enumeration is narrower than the checklist, so the soak can run with the UNKNOWN machinery inert

**Sentence (TN-18:514):** "**Anything the TN-23 soak checklist EXERCISES is SOAK-BLOCKING, not merely
live-blocking:** `ksa_effect_matrix`, the clock bands, `kill_line_capital_floor`, the window widths
and the SQS keys must each hold at least a `provisional-evidence` value, ruled as a recorded config
version **before the soak**, or the checklist runs against inert mechanisms and cannot pass."

Two builders read this two ways: as a RULE (everything the checklist touches must be valued) with an
illustrative list, or as the ENUMERATION of five keys the rule covers. The enumeration is much
smaller than the checklist. TN-23:585 exercises, at minimum: the **submission deadline** ("a forced
disconnect mid-order mints UNKNOWN"), the **reconciliation lookback and cadence** ("reconciliation
runs with four verdicts"), **crash-loop K and T** ("a crash-loop … boots into stand-down"), the
**backup numerics and `restore_verification_cadence`** (nightly/monthly/host-loss drills), the
**seat-callback deadline** (implicitly, seat quarantine), `disk_headroom_min` (the clock/headroom
push class), and the **dead-man's-switch cadence**. None is in TN-18's five.

Under the second reading the consequence is concrete and unsafe: TN-6:251 lists the submission
deadline among values whose blank "blocks `role = live` bindings" — and TN-18:512 says "A blank that
gates live money blocks `role = live` bindings only — paper runs." So the whole one-week unattended
soak can legally run on a demo binding with a BLANK submission deadline, in which case no UNKNOWN is
ever minted on a timeout, L35's stream block never engages, and the checklist item that proves it
cannot pass — yet nothing refuses the soak.

The same reading gap makes `max_slice_latency`, `accumulator_bound`, `local_queue_bound` and
`protective_reserve_capacity` ambiguous in a second way: the spine never says what a blank does to a
value that is mechanically required to RUN (an unbounded accumulator, a latency check with no
threshold) rather than to gate money. Blank-blocks-live does not answer it.

**Fix.** Rewrite TN-18:514 as a generated rule, not a list: "every variable named by any TN-23
checklist item is SOAK-BLOCKING and must hold at least `provisional-evidence` in the pre-soak config
version; the soak gate refuses to start otherwise." Then add one sentence to TN-18:512 partitioning
blanks into three effects — **blocks boot** (values without which a declared mechanism cannot run at
all: `submission_deadline`, `accumulator_bound`, `max_slice_latency`, `local_queue_bound`, the
crash-loop K/T), **blocks `role = live`** (money gates), **blocks the soak** (checklist-exercised) —
and tag each row of the mint table with which it is.

### C2 — A protective act that cannot be journaled has no durable home: TN-4 says it is "held in the fold", TN-7 says a standing intent is "journaled before dispatch"

**Sentence (TN-4:214):** "**Under a full disk** the block-on-unpersistable rule and L39 compose rather
than collide: … a protective act that cannot be journaled becomes a standing protection intent held
in the fold and re-decided when storage returns".
**Against (TN-7:291):** the standing-intent machinery is "**Journaled before dispatch**, resolved as
a read-time fold, re-decided rather than retried, never time-expiring".
**And (TN-6:250):** "a control action is journaled before dispatch, so the dispatcher must see the
sink refusal — a `storage failure` blocks the dispatch rather than losing the intent, and the intent
stands as a protection intent."

A fold is derived from records. If the record cannot be written, there is no fold entry — so "held in
the fold" can only mean held in memory, which dies with the process, contradicting "restart-proof"
and "never time-expiring". Two builders: one keeps an in-memory queue (a protective flatten silently
lost across the restart that a full disk usually causes); one refuses to dispatch and alarms, leaving
the position uncovered. Both are defensible from this text, and this is the money path.

**Fix.** State the durability rule explicitly in TN-4 and cite it from TN-7: reserve a small
pre-allocated protection-intent area outside the room trees (or a bounded reserved extent inside
`/var/lib/qmx/state`, sized by `disk_headroom_min` so the headroom block trips first), declare that
a protection intent is journaled there when the journal room is unpersistable, and state that if
even that write fails the node alarms on the silent-degradation class, leaves the venue-resident
protective stop carrying the position, and records the intent as UNDELIVERABLE rather than as held.

### C3 — `value-status` is declared to live in the registry, but the only act that can change it edits the config artifact

**Sentence (TN-18:510):** "**THE VALUE-HOME RULE: `docs/registry/variables.yaml` declares a variable's
SCHEMA and nothing else** — unit-kind, `ui-editable` or `uneditable` flag, owner scope,
`admission_impact`, **`value-status`**, and recorded evidence values … **The resolved node-config
artifact is the sole home of a resolved value** … the powers channel and the toolkit's authoring
recipes **edit the config artifact only**."
**Against (TN-18:511):** "a `provisional-evidence` value that gates live money blocks `role = live` …
**until an operator countersign through the powers channel flips it to `ratified`**."

`value-status` is a property of a resolved value, not of a schema. As written, the countersign is a
powers call that may only touch the config artifact, but the field it must flip lives in a repo file
the running node cannot write. Two builders: one puts `value-status` on the config-artifact row and
treats the registry field as documentation (then TN-18:510's "and nothing else" is violated and the
mint table's "all with … a `value-status`" is wrong); the other implements the countersign as a
git edit to `variables.yaml` plus a deploy, which is not a powers call, is not journaled as a control
action, and cannot be "server-side revalidated against fresh state at click time" (TN-17:493). Since
TN-20:543's promotion battery gates live money on `value-status = ratified`, the ambiguity can make
the live gate unenforceable or unreachable.

**Fix.** Split the field in one sentence: the registry row declares `value_status_required` (whether
this variable may ever be `provisional-evidence`) as schema; the **resolved config artifact carries
the per-value `value-status`**, and the countersign mints a new config version like every other
settings edit (TN-18:515), journaled as a control action. Correct TN-18:510's field list, the mint
table preamble (line 661) and the parent-annotation mint (line 657) to match.

### C4 — The seat-callback deadline is enforced by a cooperative token at slice boundaries, so a callback that never returns cannot be stopped — and the watchdog is deliberately decoupled from the loop

**Sentence (TN-19:524):** "Every callback runs under a **per-callback deadline** (node value,
do-not-default, UI-editable) enforced by the slice driver **through the `CancelToken` at slice
boundaries**."
**Context that makes it fatal:** `CancelToken` is "cooperative abort at slice boundaries"
(`qmb/src/qmb/runloop/observe.py:60`, Ports table line 815); TN-4:206 puts the domain loop
"synchronously on that loop's thread per slice" with no threads for domain work; TN-4:205 puts the
watchdog keepalive in the door layer "so it continues through stand-down **while the loop is
quiescent**"; TN-19:524 accepts that "admitted bot code runs in-process".

A seat callback that loops, blocks on a syscall, or ignores the token never reaches a slice boundary.
The deadline therefore cannot fire, quarantine cannot fire, the slice never completes, the
accumulator backs up to `accumulator_bound`, and — because the keepalive was deliberately moved off
the loop — `WATCHDOG=1` keeps arriving, systemd is content, `/health` may still answer, and the node
looks alive while every open position is unmanaged. This is the one failure mode where the
supervision design and the containment design cancel each other out, and the spine states neither
the limit nor a detector.

**Fix.** Add to TN-19:524 a liveness detector that does not depend on the callback returning: the
door layer already owns the keepalive, so give it a **slice-progress watch** — the driver publishes a
monotonic slice-start stamp; if `now − slice_start` exceeds the callback deadline by a declared
factor, the door layer stops sending `WATCHDOG=1` (or notifies `WATCHDOG=trigger`), pushes on the
silent-degradation class, and lets systemd restart the node, which is safe because a restart never
flattens and standing intents survive. Then state plainly in the accepted-consequence sentence that
V1 cannot interrupt a non-cooperative callback and that supervised restart is the containment of
last resort until OS confinement ships.

---

## 3. HIGH

### H1 — The KSA level has no declared SCOPE, yet the text calls it both global and per-stream

TN-7:285 "The KSA level is a **read-time fold** over the control-action stream"; TN-7:286 the fold
"lowers only on an operator `resume` record, **which opens a new level epoch**"; TN-7:288
"`connectivity` and `unknown_state` are market-risk blocks **on the affected stream**"; TN-7:289
"the **kill switch IS the KSA at its blocking levels: global**". TN-15:449 exports "KSA level"
(singular). Nothing says whether there is one level for the node, one per `(VenueId, account)`
stream, or one per binding. Two builders build two different systems, and the monotonicity rule is
not even well-formed without a scope (does one operator `resume` open a new level epoch everywhere,
or only on the stream that escalated?). This also decides whether a connectivity escalation on one
connection blocks trading on the other.
**Fix.** Declare in TN-7:285 that the KSA level is folded **per enforcement scope**, the scope being
a component of the level's identity and of the level epoch: a global level plus a per-stream level,
with the effective level at any decision point the most restrictive of the scopes covering it, and
an operator `resume` naming the scope whose epoch it opens. Add "level scope" to the conventions
row's epoch list.

### H2 — A preflight failure both stays alive in stand-down and loops through systemd restarts

TN-2:141 "Fail-closed with a typed failure id, journaled, and **the node stays alive in stand-down
with the doors serving — it does not exit into a restart loop**."
TN-4:211 "**The crash-loop fold counts BOOT ATTEMPTS BY STAGE** … **A loop in preflight therefore
trips `(K, T)` exactly as a loop in compose does.**"
Both cannot hold: if a preflight failure never exits, there is no second preflight attempt to count,
and the `StartLimitBurst > K` machinery TN-4:211 makes mandatory has nothing to do. A builder taking
TN-2 literally never exits on preflight and can set `StartLimitBurst` anywhere; a builder taking
TN-4 literally exits non-zero on preflight refusals and relies on systemd to carry it to the
self-detecting boot.
**Fix.** Distinguish a **detected preflight refusal** (typed, journaled, → stand-down alive, no exit)
from an **undetected preflight-stage crash** (exception, OOM, exit) and say only the second feeds the
crash-loop fold. State the same distinction for compose. Then say explicitly which stages can exit
at all, given TN-2:140's "Only a failure that prevents the doors themselves from binding exits
non-zero".

### H3 — The boot-attempt record is the first durable write, but every `WriterId` is allocated later, at Compose

TN-2:140 "a **boot-attempt record** is written as the first durable write, carrying the boot epoch
id, the unit role and the stage reached."
TN-2:145 "**`WriterId` allocation is the root's, exclusively.** Every `WriterId` is allocated at
Compose from a declared namespace and handed to its writer; **no component derives its own**."
The first durable write happens two acts before any `WriterId` exists, and CT-13 makes journal
sequence gapless per `(writer, boot epoch)`. The spine never says which writer owns the
boot-attempt stream, where it lands, or whether it is a journal stream at all. TN-4:211's crash-loop
fold reads these records, so they must be durable and readable across boots by a component that has
not yet composed.
**Fix.** Name a **supervisor writer** in TN-2 whose `WriterId` is a constant of the unit role rather
than an allocation (it is the one writer that must exist before Compose), state that its stream
carries only boot-attempt and lifecycle records, add it to the allocation-proof set as a reserved id
that Compose may not re-issue, and name its room placement in TN-3's writable-tree list.

### H4 — Nothing in any Rule defines the inbox→published step the TN-3 diagram asserts an operator performs

TN-3:159 splits the hub into "a **write-only inbox** that sandboxes push `WriterId`-scoped fragments
into, and a **read-only published area** holding as-of sets". The topology diagram (line 193) draws
`HIN -- operator publish step --> HPB`. No rule anywhere describes that step: it is not a powers-
channel capability (TN-17:492's list ends at promotion sign and activate), not a `just node-…`
recipe (TN-1:130's enumeration), and not a scheduled unit (TN-3:154's three timers). TN-20:544 then
depends on it — "a node-initiated pull of the registry as-of set **from the hub's published area**"
— so the promotion path begins at an artifact nothing is specified to produce. A diagram asserting a
step no Rule defines is exactly the divergence this gate exists to catch.
**Fix.** Either add the publish step to TN-17's powers list (an operator act, signed, journaled,
verifying each fragment's `fp1` and refusing `provenance = sandbox` **at publish** as well as at
pull), or make it a `just node-hub-publish` recipe that calls that same power. Then say so in TN-3
and keep the diagram edge.

### H5 — The replay import port reads from the evidence tier, whose declared room roles do not include the observation or journal rooms it must read

TN-21:555 "A replay run reads sealed live-world observations through a **named one-way REPLAY IMPORT
PORT** … reading from the **evidence tier** so a hot-room purge past `hot_room_retention_window`
never orphans a replay."
TN-3:161 "ingest door, immutable raw archive, processed and journal rooms live under
`rooms/<world>/`; **the split-governed research door and the registry room live under
`evidence/<world>/`**".
So the evidence tier holds two room roles, neither of which is where observations or journals live.
TN-3:154 says the sync is "one-way, watermarked, idempotent and resumable under verify-before-purge"
but never says WHAT is synced or into which role it lands. A builder implementing TN-21 has no
addressable source; a builder implementing TN-3's purge rule has no idea what must exist in the
evidence tier before a hot room may be purged.
**Fix.** In TN-3:161, state which room roles the evidence tier instantiates per world for synced
content (name it: the research door receives the sealed observation and journal content under its
split governance), or add the sealed-archive role explicitly. Then have TN-21:555 and TN-13:421 cite
that role by name, and make `hot_room_retention_window`'s purge precondition "a verified copy in
that named role AND a verified off-host copy".

### H6 — `SessionTopology` requires two connections, but the live account is a deferred human step and the soak is a demo-only week

TN-11:386 "`SessionTopology` declares `required_connection_count = 2` and the shape models N." The
inventory confirms this is a `ClassVar` in shipped code (`inputs/code-qmf-venue.md:80`). Meanwhile
TN-9:322 rules the soak is "one full unattended week … **on the demo account**", and the Deferred
table (line 873) still carries "Spotware app approval, **live KYC**" as human-only steps that gate
the live milestone. A topology that requires exactly one demo plus one live endpoint cannot be
satisfied during the week that must run before live KYC completes, and TN-3's diagram draws both
connections as always present.
**Fix.** State in TN-11 that connection count is **derived from the roster** — one connection per
`(venue, environment)` pair the roster names — and record `required_connection_count = 2` as a
`qmf-venue` increment item to relax (it belongs in the same increment as the transport, A37). Add
one sentence to TN-9 saying the soak roster declares the demo binding only and that the live
connection is opened for the first time at the warm-up week's end, which is also when the live SQS
baseline (TN-8:305) begins minting.

### H7 — TN-20 binds `qmn/promotion` and TN-22 binds `qmn/roster`; neither module exists in the Structural Seed, and promotion and seat hosting have no Capability-map row

TN-20:539 "**Binds:** `qmn/promotion`; the doors". TN-22:563 "**Binds:** `qmn/roster`". The
Structural Seed (lines 737-781) lists host, loop, venue, orderpath, protection, ledger, paper,
reconcile, seats, mis, data, time, secrets, config, observability, doors, replay, bench — no
`promotion/`, no `roster/`. The Capability → Architecture Map (lines 842-864) has no row for
promotion/activation at all, and no row for seat hosting; it places the roster in "`config/`
roster", contradicting TN-22's Binds line. Epics are cut from these three surfaces, so a row with no
owning module and a Binds line with no module produce two different work breakdowns.
**Fix.** Add `promotion/` to the seed (promotion card mint, precondition battery, the hub pull,
activation) and either add `roster/` or change TN-22's Binds to `qmn/config` roster. Add two map
rows: "Promotion and activation → `promotion/`, `doors/` → TN-20" and "Bot seats and registration →
`seats/` → TN-19".

### H8 — Every deployment path is a `just` recipe, but the declared day-one bootstrap never installs `just` and no version is pinned for it

TN-16:468 "**The pre-`qmn` bootstrap is a declared day-one step of its own** — install uv, provision
CPython, clone at the pinned commit — performed by a stand-alone script in the checkout before `qmn`
exists to run anything." TN-16:471 then makes the very first act after that `just node-install`.
`just` is absent from the bootstrap list, and its Stack row (line 719) carries no version and no
verification date although it is now load-bearing DevOps tooling on both hosts ("the repo's existing
recipe runner, already a project tool and not a node-minted dependency").
**Fix.** Add `just` to the bootstrap step in TN-16:468 (or state that the stand-alone script is
invoked directly and `just` is only a convenience wrapper). Pin a `just` version with a
verification date in the Stack table and register it as an external tool in the AD-6 register
alongside `rclone`, since the ruling made it the only path to install, switch and roll back the node.

### H9 — The node "adds" journaled observation kinds while TN-15 forbids a second event catalog, and no parent annotation is proposed

TN-13:416 "**Position and balance events are first-class journaled observation kinds the node adds**
(the CT-20 seven-journaled-types gap)".
TN-15:450 "The legacy five Records streams survive **as CT-25 PROJECTION NAMES ONLY**, mapped onto
**AD-21's seven journal event types** by CT-25's one versioned mapping table; **no second event
catalog is minted**."
Adding first-class journaled kinds either extends the parent's fixed seven (a parent amendment a
child may not make by assertion — the spine's own rule, line 50: "A local decision that contradicts
one is a conflict to surface, never an override") or maps onto an existing type, in which case
"adds" is the wrong word and the mapping must be named. The "Parent annotations and mints proposed
by this sitting" section (lines 647-696) does not carry this one, though it carries four others.
**Fix.** Decide and say which: if position and balance observations map onto an existing AD-21 type,
name the type and the discriminator in TN-13:416 and add the row to TN-15's mapping table; if they
are genuinely new kinds, add a fifth parent annotation to the section proposing the AD-21/CT-20
extension, exactly as the AD-28 candidate is handled.

### H10 — Two load-bearing operational values — the drain window and `WatchdogSec` — appear in no do-not-default list and no registry row

TN-4:212 "Reaching a safe point is bounded by **the declared drain window** (`TimeoutStopSec` at
least that window); a breach is a typed refusal". TN-16:470 "**`TimeoutStopSec` at least the declared
drain window**, **an explicit `WatchdogSec` value**". TN-4:213 makes the drain window decide when
shutdown mints UNKNOWNs for the remainder and exits non-zero — a money-path effect. Neither value
appears in TN-18:512's blank list nor in the mint table (lines 663-688), so neither is UI-editable,
neither carries a unit-kind, and neither has a `value-status`. Two builders hard-code two different
windows in two unit files, which is precisely what TN-18 exists to prevent ("a hidden constant").
**Fix.** Mint `drain_window` and `watchdog_interval` as `configurable: true` node rows with duration
unit-kinds in the mint table, add both to TN-18:512's do-not-default list, and state in TN-16 that
the unit file's `TimeoutStopSec` and `WatchdogSec` are RENDERED from the resolved config artifact by
`just node-install` rather than authored by hand — otherwise a config change and a unit file can
disagree.

---

## 4. MEDIUM

**M1 — Where is AD-37's "one arbitration point per stream"?** The TN-6 diagram (line 275) draws the
arbitration loser leaving the **protection gate** (`GATE -. arbitration loser .-> SUP`), while
TN-6:249 places arbitration in the "Observations then read-time folds" bullet, among already-
authorized control actions, and TN-5:229 only says the loop instance "is the same unit as AD-37's
one arbitration point per stream" without naming the component. Two builders site it in two places,
which changes whether a veto and a suppression can both occur for one intent. *Fix:* name the owning
component once (the control-action dispatcher in `protection/`), say the protection gate consumes
its result rather than performing it, and redraw the diagram edge from that component.

**M2 — The compound-command "meet" is undefined for the all-rejected case.** TN-6:245: "the **parent
outcome is the meet of its children** (any child UNKNOWN makes the parent UNKNOWN; any child rejected
makes the parent `partially-executed`)". If every child is rejected, nothing executed, yet the stated
rule yields `partially-executed`. "Meet" also implies a lattice over the four outcomes that is never
defined. *Fix:* state the full table — all accepted → accepted; any UNKNOWN → UNKNOWN; else any
accepted and any rejected → `partially-executed`; all rejected → rejected — and drop the word "meet"
or define the order.

**M3 — The interpretation cursor has no declared commit point and no idempotency statement.**
TN-5:225 "The accumulator maintains a **durable interpretation cursor** in the journal"; TN-10:333
re-folds "every observation recorded after the accumulator's last committed cursor position". When
the cursor advances (per observation, per slice, per flush) decides how much is re-folded, and
nothing says re-folding is idempotent for the derived folds (AD-10's idempotent split covers
observation intake, not fold application). Two builders double-count a fill on a restart or lose
one. *Fix:* state that the cursor commits at slice end, after the slice's sinks flush, and that
every fold the re-fold touches is idempotent by observation identity — or that the re-fold rebuilds
folds from scratch rather than appending.

**M4 — `NotificationChannel` is a port the spine uses but never mints.** TN-15:455 "ONE push channel
through a `NotificationChannel` port with a generic HTTPS-webhook implementation". The name appears
nowhere in `inputs/parts-bin.md` (§3 or the tables) or in the spine's "Ports the node implements"
table, unlike `VenueClientPort` and the replay import port, both of which are explicitly declared
node-minted. *Fix:* add a row to the Ports table marking `qmn.observability.NotificationChannel` as
node-minted with its two V1 implementations (webhook, console/file sink), the way TN-11 handles
`VenueClientPort`.

**M5 — The evidence channel's authentication is unstated and "budgeted" is undefined.** TN-17:488
"the **LOCALHOST HTTP EVIDENCE CHANNEL** … publish-never-act, **budgeted**, authority-free". The
powers channel gets a precise gate (`SO_PEERCRED`, declared operator principal); the evidence channel
gets nothing — any local process, including the observability stack's exporters and any future
agent-adjacent tooling, can read every journal projection, drift component and outstanding UNKNOWN.
"Budgeted" names a limit with no value, no unit-kind and no registry row. *Fix:* state the evidence
channel's access rule in one sentence (localhost binding plus the same peer check, or an explicit
"no authentication beyond the loopback binding, accepted because the VPS is single-tenant and the
channel cannot act"), and mint `evidence_channel_budget` with a unit-kind in the mint table.

**M6 — The provisioning wizard is a fourth in-memory secret holder.** TN-12:406 "**Three named secret
holders, and no fourth** … **no other component holds any secret value**". TN-12:405 has the wizard
"read each `qmx/*` entry and stream the value over an SSH session's stdin" — it demonstrably holds
plaintext secret values in memory on the workstation. *Fix:* carve it out explicitly — "the
provisioning wizard is a transient fourth holder, on the workstation only, for the duration of one
provisioning run, and never on the VPS" — so the invariant stays checkable.

**M7 — `holdout_months` is stated as 12 in one rule and as blank in another.** TN-13:420 "`holdout_months
= 12`, do-not-default, enforced on restored reads too (`ct-14:18`)"; TN-18:512 lists `holdout_months`
among "Do-not-default values … **BLANK until ruled**". One builder ships 12, the other blocks live on
a blank. The 12-month seal is corpus-ratified, so the second is wrong. *Fix:* remove `holdout_months`
from TN-18:512's blank list and mark it in the registry as an inherited ratified value the node does
not mint.

**M8 — "Refused" is used for the held case that TN-8 forbids refusing.** TN-8:306 "**No node component
on the command path may refuse a risk-non-increasing `amend_protection`**"; TN-23:585 requires
"**a protective `amend_protection` refused under an outstanding UNKNOWN is re-decided rather than
lost**". The mechanism is TN-6:243's hold-as-standing-intent, which is not a refusal. On a money-path
rule the same word must not mean both. *Fix:* change TN-23's item to "held under an outstanding
UNKNOWN as a standing protection intent and re-decided when the block clears", and add
held ≠ refused to the conventions row.

**M9 — The "only reverse crossing" claim is contradicted by its own next bullet and its own diagram.**
TN-3:158 "Flows are ONE-WAY node to evidence tier to workstation, and node to bucket. **The only
reverse crossing is the click-gated promotion pull**"; TN-3:159 then has sandboxes pushing fragments
INTO the VPS inbox, and the diagram draws `SB -- WriterId-scoped fragments --> HIN`. TN-16:474's ufw
posture (default-deny inbound except SSH) gives no path or identity for that write. *Fix:* rewrite
the sentence as "two inbound crossings exist and no others: the click-gated promotion pull and the
sandbox fragment push into the write-only inbox", and name the inbox write path (a restricted
key-only SSH identity confined to `/var/lib/qmx/hub-inbox`, distinct from the operator key and from
the provisioning identity of TN-12:405).

**M10 — Two Deferred rows for hardened OS confinement give two different compensating controls.**
Line 872: "TN-19's callback deadline plus seat quarantine carry the line meanwhile". Line 879:
"static scan, capability starvation and process isolation carry the line". Capability starvation and
process isolation are described nowhere in TN-19. Two units read the two rows and build two
containment stories. *Fix:* delete line 879 and keep the row that cites TN-19's mechanism, or merge
them and state which controls actually exist in V1.

**M11 — A VPS tuple migration's effect on live bindings is unstated.** TN-19:530 says "a tuple
migration leaves a **provisional light claim** that alarms rather than hard-blocking", and TN-14:435
names VPS live migration as a real event. But CT-28's bind-time rung baseline is scoped to the
declared `(OS, CPU-class)` tuple (TN-10:339, TN-23:584), and nothing says what happens to an
already-live binding when the tuple changes under it. *Fix:* state it in TN-10:339 — a tuple change
invalidates the rung baseline, blocks NEW live bindings entry-side, alarms on the silent-degradation
class, and requires a re-recorded baseline; existing bindings keep exits and protection per L39.

**M12 — "Counts boot attempts BY STAGE" does not say whether the count is per stage or across
stages.** TN-4:211. If per stage, alternating preflight/compose failures never trip `(K, T)`; if
across stages, "by stage" is only a label on the record. *Fix:* say "counts every boot attempt within
T seconds regardless of the stage reached; the stage is recorded for diagnosis, not for bucketing".

**M13 — Which unit runs the nightly sample restore is unstated.** TN-13:422 declares three drills
(nightly sample, monthly full, host-loss rehearsal) but TN-16:470 checks in exactly one
`qmn-restore-drill.timer`/`.service` pair, and TN-3:154 names "the nightly backup and the restore
drill" as two units. The nightly sample "right after the backup" may belong to the backup unit or to
the drill unit; each choice changes the `WriterId` allocation TN-2:145 must enumerate. *Fix:* assign
the nightly sample restore to the backup unit explicitly (it shares the run's payload key per
TN-12:406) and leave the monthly full to the drill timer.

**M14 — The frontmatter's assumption range is stale.** Line 16: "every without-operator call is
tagged **A1-A37**", while the register is titled "Assumption register (A1–A39)" and A38/A39 exist.
*Fix:* change to A1-A39.

---

## 5. LOW

**L1** — The warm-up rider is attributed to two different sources: TN-9:322 cites "`runbook.md:80`,
DEC-0135" while the conventions row (line 702) credits "AD-39's ratified pre-live rider". Pick one
attribution.
**L2** — TN-1:127 calls `qmn` "the distribution and import **name**" while A1, the ruling section and
the conventions row all say "**CODE NAME** only". Align the wording so no reader takes TN-1 as
settling the name the operator declined to rule.
**L3** — TN-24:604 writes "a venue stop-out or margin liquidation" one clause before ruling that "the
bare phrase is never used". It is not bare, so it passes, but the sentence reads as violating itself;
prefer "a venue-initiated liquidation".
**L4** — `seat_memory_ceiling` has a mint-table row (line 686) but no TN sentence naming it; TN-19:524
only says "a `LimitProbe` memory breach". Name the variable where the mechanism is stated.
**L5** — The VPS provider is never declared to be deployment configuration, although the bucket
provider and the broker both are. One clause in TN-3 closes it.
**L6** — "Provisional" carries two senses: `value-status = provisional-evidence` (TN-18:511) and a
"provisional light claim" (TN-19:530). Add the distinction to the conventions row or rename the
latter.
**L7** — `status: draft` is correct for a re-gate, but the frontmatter's `updated` should move and the
status should flip in the same edit that closes these findings, so the ratified artifact is not
distinguishable from the draft only by its length.

---

## 6. Rubric ledger (what was walked, and the result)

| Rubric row | Result |
|---|---|
| Divergence points fixed, none missed | PASS — the ruled four are applied; no new divergence from a ruling |
| Every Rule enforceable | CONDITIONAL — C4, H2, H3 name Rules that cannot be enforced as written |
| Every "Prevents" actually prevented | CONDITIONAL — TN-19's "a bot reading a clock" holds; TN-4's "a shutdown that loses an intent" is defeated by C2 |
| Nothing under Deferred lets two units diverge | ONE — M10 |
| Named tech verified-current with dates | PASS except `just` (H8) |
| Brownfield ratified: parts-bin §3 seams all homed | PASS (25/25) |
| No TN assumes an unminted port | ONE — M4 (`NotificationChannel`) |
| Every altitude dimension decided/deferred/open | PASS, with door authentication thin (M5) |
| Do-not-default values in TN-18 ∪ mint table | TWO GAPS — H10 (drain window, WatchdogSec), M7 (`holdout_months` in the wrong list) |
| Every assumption tag has a register row | PASS (A1-A39, A8 retired correctly) |
| No `[ASSUMPTION]` blocks a builder | PASS |
| Every Capability-map row has an owning TN | PASS — but two TNs have no map row and two Binds have no module (H7) |
| No diagram contradicts a Rule | ONE — H4 (the operator publish step); ONE partial — M1 (arbitration siting) |
| Frontmatter complete, no template comment | PASS (M14 is a stale number, not a gap) |
| Mermaid valid | PASS (6/6) |
| Operator-rulings section quotes the memlog faithfully | PASS (13/13 quoted fragments verbatim) |
