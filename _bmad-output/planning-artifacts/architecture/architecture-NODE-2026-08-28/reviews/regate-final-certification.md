# Final certification — ARCHITECTURE-SPINE.md (Trading Node), fresh lens

**Seat:** final certification (third pass, fresh lens). **Target:** `ARCHITECTURE-SPINE.md`, 1048 lines, TN-1..TN-25, `status: draft`.
**Read in full:** the spine; `.memlog.md` (51 entries, through GATE-2 RULINGS 1–34); `reviews/fix-pass-1.md` § "Residual fix pass 2"; the CRITICAL/HIGH sections of all five `reviews/regate-*.md`. Parent `architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md` consulted for AD-19.
**Nothing was edited.** The spine and the memlog are untouched.

---

## VERDICT: **BLOCK**

Four HIGH defects stand. None is architectural — all four are one-sentence text fixes closable at desk in a single short pass with no operator round — but each produces either two divergent builds on the money path or a silent parent amendment, and one of them re-opens a CRITICAL that residual pass 2 was written to close.

Everything else is clean: **all 44 CRITICAL/HIGH findings across the five re-gate reviews are PRESENT** (13C + 31H, zero PARTIAL, zero MISSING), and every mechanical check passes.

---

## 1. REGRESSION — every CRITICAL and HIGH from the five re-gate reviews

### regate-parent-consistency (2C / 8H) — all PRESENT

| Id | Verdict | Closing sentence in the current spine |
| --- | --- | --- |
| RC-1 UNKNOWN block folded into the entry-side law | **PRESENT** | TN-6:249 — *"**THE ONE EXCEPTION, and it is the parent's own: AD-27's per-command UNKNOWN block is NOT a control and NOT an entry-side block.** … While an UNKNOWN is outstanding on a `(VenueId, account)` stream, **every command on that stream is refused, protection commands included** … **Only `resolve_unknown` clears it; a reconciliation verdict never does**."* "an outstanding UNKNOWN" is gone from TN-6:248's enumeration; TN-24 (c):640 and TN-23:628 both corrected |
| RC-2 protective stop never attached | **PRESENT** | TN-6:258 — *"**PROTECTIVE-STOP ATTACHMENT AT PLACEMENT (AD-33 / AD-34), written into the order path rather than left as a capability row.** … every `place_order` carries a venue-resident protective stop at placement … **Where the Book requires attachment and CT-18 does not declare it, placement is an `unsupported capability` refusal — never a silently unprotected order**."* (see LOW-1 on its trigger condition) |
| RH-1 `resurrect` is a control action nobody minted | **PRESENT** | TN-4:224 — *"**`resurrect` is a node LIFECYCLE act, not a CT-30 control action.** It journals as an AD-21 `control action` **event** under the declared node subtype **`node_resurrect`** … and mints no CT-30 record and no CT-30 kind."* Parent annotation at :703 |
| RH-2 `admission_impact` declared, never wired | **PRESENT** | TN-18:548 — *"**`admission_impact` IS ENFORCED, not merely declared (AD-30).** … **A diff touching any `resign` variable … makes the resulting binding INADMISSIBLE to `role = live` until a fresh AD-32 Layer 2 … and Layer 3 … complete**."* Cited from TN-17:536 and TN-20:585 |
| RH-3 advisory stop proposal absent | **PRESENT** | TN-6:251 — *"**The CT-23 v2 entry intent carries the bot's optional `advisory_stop_proposal`** … the door's per-family `ExitLogicRef` **consumes it** … a Book MAY declare the ratified **adopt-the-bot's-advisory-stop module mode**."* Mirrored in TN-19:564 |
| RH-4 TN-2/TN-4 disagree on preflight exit | **PRESENT** | TN-4:218 — *"**THE EXIT MODEL, stated once here and cited from TN-2 and TN-16.** A **detected** refusal at or after preflight … **does not exit** … **The crash-loop fold therefore governs only failures that DO exit**."* TN-2:141 now cites it verbatim |
| RH-5 soak demo-only vs live-conditioned baseline | **PRESENT** (via ruling 32, not the review's own fix — recorded in fix-pass § "Not applied") | TN-9:341 — *"**THE SOAK RUNS THE DEMO BINDING; THE LIVE CONNECTION IS OPENED FOR SENSING AND RECORDING ONLY.**"* Deferred row :963 re-timed. **But see BLOCKER 4 — the roster cannot express it** |
| RH-6 alert allow-list widened past PRD §3 | **PRESENT** | Parent annotations :713 — *"**PRD §3 notification allow-list — PROPOSED WIDENING, surfaced not settled.** … This sitting proposes a **third ratified class** … as a PRD amendment the documentation factory carries."* |
| RH-7 no-scale-in refusal missing | **PRESENT** | TN-6:252 — *"**NO SCALE-IN (AD-40).** An entry intent against an instrument on which the binding already holds an open **virtual position** is a `policy rejection` at the door."* Restated TN-25:659, TN-24 (a):638; checklist item TN-23:628 |
| RH-8 invocation layer has no surface | **PRESENT** | TN-18:544 — *"It is compiled from **FOUR** explicit layers with fixed precedence … **There is NO invocation layer.** … The layer is deleted."* |

### regate-adversarial (7C / 12H) — all PRESENT

| Id | Verdict | Closing sentence in the current spine |
| --- | --- | --- |
| C1 stand-down blocks Book-minted exits | **PRESENT** | TN-4:216 — *"the sequencers refuse and journal **ENTRY intents only — `place_order` and risk-increasing `amend_protection` — whatever their author**. **Every risk-non-increasing act passes whatever its author**."* |
| C2 replay adapter selected by `VenueId` | **PRESENT** | TN-2:142 — *"**`VenueClientPort` implementation selection by the pair `(world, VenueId)` — never by `VenueId` alone**"*; TN-2:142 also — *"A `world = replay` composition … resolves no credential reference, constructs no venue-session `SecretStore` holder and opens no socket; preflight proves all three."* Mirrored TN-5:240, TN-11:412, TN-21:596, TN-22:613 |
| C3 calendar revision shrinks an in-force window | **PRESENT** | TN-8:323 — *"**A CALENDAR REVISION MAY ONLY WIDEN OR ADD A WINDOW AUTOMATICALLY.** … takes effect no earlier than the end of the window the superseded revision declared, and never opens entries the superseded revision blocked."* Cited TN-13:449 |
| C4 retry-after-refresh vs no command retry | **PRESENT** | TN-12:431 — *"**A `place_order`, `amend_protection`, `cancel_order`, `close_position` or `close_all` that meets an authentication failure is NEVER retried** … TN-11's prohibition on command retry has no exception, this one included."* |
| C5 async/session/secret below the root | **PRESENT** | TN-2:145 — *"**ONE IMPURITY IS DELEGATED, named here and nowhere else.** `qmf-venue`'s `ConnectionManager` holds the venue socket, the venue session and the single in-memory venue secret value, running on the loop the node injects … **the QMF async conformance test is amended in the same increment to exempt `qmf.venue.connection` by name** … **the epics may not choose between the two**."* Annotation :705 |
| C6 blended residual, two marks, epsilon 0 | **PRESENT** | TN-10:365–369 — *"**EXPLAINED DRIFT — TWO RESIDUALS, COMPARED SEPARATELY, EACH WITH ITS OWN EPSILON-0 IDENTITY, AND NEVER ONE BLENDED NUMBER.** … **UNREALIZED P&L ENTERS NEITHER RESIDUAL** … **Drift is a non-zero residual in (a) or in (b), and only that sets `operator_review`.**"* **But see BLOCKER 1 — TN-24 (f) and TN-25 still say "drift component"** |
| C7 one principal; agent-signer refusal unverified | **PRESENT** | TN-17:523 — *"**TWO PEER PRINCIPALS ARE DECLARED, both by uid in the resolved config artifact, and NEITHER IS THE `qmx` SERVICE ACCOUNT**"*; :526 — *"**What it does NOT prove: `SO_PEERCRED` proves an account, not a human**."* TN-20:583 rewritten to match |
| H1 `node-switch` mutates the running checkout | **PRESENT** | TN-16:503 — *"**`just node-switch <commit>` MATERIALIZES A NEW TREE BESIDE THE OLD** … then **an atomic flip of the `current` symlink as part of the restart**"*; :500 — *"**`uv sync --frozen` never writes into a tree a running node resolved from**."* |
| H2 restart-at-safe-point under `Restart=on-failure` | **PRESENT** | TN-4:218 — *"A **requested** restart … **exits with the reserved code 75**, with `RestartForceExitStatus=75` and `SuccessExitStatus=75` in the unit … **a requested restart never advances `(K, T)`**."* TN-16:502 pins both |
| H3 observability stack unsupervised/unstored/uncredentialled | **PRESENT** | TN-15:490 — *"**The stack is SUPERVISED, STORED, NETWORKED and CREDENTIALLED explicitly** … its own unit `qmx-observability.service`, under a distinct non-`qmx` service account … `/var/lib/qmx-observability` … its own filesystem quota … `network_mode: host` with every container port bound to `127.0.0.1` … a dedicated read-only journal namespace … the **declared fourth secret holder**."* |
| H4 candidate labeler re-identifies governed evidence | **PRESENT** | TN-19:574 — *"**Its distribution identity and version enter a SEPARATE `shadow_composition_fp`, never the governed `composition_fp`** … the slice driver neither waits on it nor **counts it toward `max_slice_latency`** … **no ambient randomness**."* Carve-out echoed at TN-2:143 |
| H5 replay / toolkit build a second root | **PRESENT** | TN-21:596 — *"a replay run is **a stdlib process-per-job spawn OUTSIDE the node process** … **never inside the trading node process**"*; TN-17:532 — *"**No recipe ever constructs a composition root or imports the Python API in a process other than the node's**."* |
| H6 two Books claim one fill on a netted account | **PRESENT** | TN-22:610 — *"the SET of attribution declarations on one netted account must be **JOINTLY EXHAUSTIVE AND DISJOINT** … proves at bind time that every fill on that account is attributed to exactly one virtual position … **at compile, never a trade-time discovery**."* Restated TN-25:658 |
| H7 calendar sealed yet refreshed; dead timer cannot fail closed | **PRESENT** | TN-13:449 — *"**A calendar's CODE identity is sealed into `composition_fp`; its DATA is not**"*; TN-8:324 — *"**A stale NEWS CALENDAR fails closed by a PRECONDITION, not by a signal from the recorder.** `news_calendar_max_staleness` … **so a silently dead timer fails closed with no signal from the timer**."* |
| H8 timers and node compute `composition_fp` from different versions | **PRESENT** | TN-2:147 — *"**Timer units run an abbreviated ceremony, from the version the RUNNING NODE sealed** … read from the node's boot-epoch record over the evidence channel — **never from the config graph's `current` pointer** … a timer that can neither read … nor establish that the node is down **refuses to write and alarms**."* |
| H9 baseline measured while slices drive; two heavy-snapshot bounds | **PRESENT** | TN-23:627 — *"**The harness NEVER runs concurrently with a slice-driving node process** … **a run recorded while the loop was driving slices is neither a baseline nor a gate**"*; TN-19:572 — *"**the heavy snapshot's maximum age IS the Book's `decision_freshness_bound` — there is no second bound**."* |
| H10 workstation can refresh the live token | **PRESENT** | TN-12:435 — *"**THE WORKSTATION INSTALLATION IS PROVISIONING-ONLY AND ENFORCED, NOT ASSERTED.** … refuses to compose on any host whose declared machine tuple is not the deployment roster's VPS entry … **a tier-1 `check` assertion proves the wizard module imports neither the connection manager nor the refresh duty**."* |
| H11 powers list incomplete; quarantine exit undefined | **PRESENT** | TN-17:527 — *"**The powers list is CLOSED and exhaustive** … **`restore_drill_run`** … **`hub_publish`** … **`config_version_activate`**; **`seat_reinstate`**, the only exit from `quarantined`"*; TN-19:565 — *"**never inferred from a restart, a new boot epoch, a config version or the absence of further breaches**."* |
| H12 a float sanctioned on the money path | **PRESENT** | Conventions :766 — *"**NO FLOAT APPEARS ANYWHERE ON THE MONEY PATH, the venue decode included** … **a money field arriving in a floating form is REFUSED rather than converted**. The sanctioned float crossings are the decode of NON-money venue fields … and the declared comparison-rule quantize."* |

### regate-rubric-ambiguity (4C / 10H) — all PRESENT

| Id | Verdict | Closing sentence in the current spine |
| --- | --- | --- |
| C1 soak-blocking enumeration narrower than the checklist | **PRESENT** | TN-18:552 — *"**`blocks-soak` — a GENERATED rule, not a list: every variable named by any TN-23 checklist item is soak-blocking and must hold at least `provisional-evidence` in the pre-soak config version, and the soak gate REFUSES TO START otherwise.**"* Restated :555 |
| C2 protective act with no durable home | **PRESENT** | TN-4:223 — *"**A protection intent has a DURABLE home even when the journal room cannot take it.** … written instead to **a small reserved protection-intent extent under `/var/lib/qmx/state`, pre-allocated and sized by `disk_headroom_min`** … recorded **UNDELIVERABLE** … **never 'held in memory', and never silently dropped**."* Cited TN-7:310 |
| C3 `value-status` home vs the act that changes it | **PRESENT in the TNs** | TN-18:546 — *"**The resolved node-config artifact is the sole home of a resolved value AND of that value's `value-status`.** `value-status` is a property of a resolved value, not of a schema."* Registry gets `value_status_required` (:546, annotation :701). **But see BLOCKER 2 — register row A34 still says "a new registry field"** |
| C4 cooperative token cannot stop a runaway callback | **PRESENT** | TN-19:566 — *"**The door layer therefore runs a SLICE-PROGRESS WATCH** … **stops the keepalive (`WATCHDOG=trigger`), pushes on the silent-degradation class, and lets systemd restart the node** … **V1 cannot interrupt a non-cooperative callback**."* Diagram :920–921 matches |
| H1 KSA level has no declared scope | **PRESENT** | TN-7:303 — *"**THE LEVEL IS FOLDED PER ENFORCEMENT SCOPE, and the scope is part of the level's identity and of its level epoch.** … **global**, and **per `(VenueId, account)` command stream** … the **effective level … is the most restrictive of the scopes covering it**."* Label on the metric TN-15:479; Conventions :765 |
| H2 preflight failure both alive and looping | **PRESENT** | Same as RH-4 — TN-4:218 |
| H3 boot-attempt record precedes `WriterId` allocation | **PRESENT** | TN-2:146 — *"**One id is RESERVED rather than allocated: the SUPERVISOR `WriterId`, a constant of the unit role, which must exist before Compose** … Compose may never re-issue it; the pairwise-distinctness proof includes it."* |
| H4 inbox→published step undefined | **PRESENT** | TN-3:160 — *"The inbox-to-published step is **an operator act, not a background sweep**: the `hub_publish` power on the powers channel … **refusing `provenance = sandbox` at publish as well as at pull**."* Diagram edge :200 now matches the Rule |
| H5 replay reads roles the evidence tier does not have | **PRESENT** | TN-3:162 — *"a named **`sealed-archive`** role live under `evidence/<world>/`. **The `sealed-archive` role is what the one-way sync writes into**"*; TN-21:597 defines "sealed". **But see BLOCKER 3 — it is an eighth AD-19 role with no annotation** |
| H6 `SessionTopology` requires two connections | **PRESENT** | TN-11:413 — *"**The connection count is DERIVED FROM THE ROSTER … never a fixed requirement** … `SessionTopology`'s shipped `required_connection_count = 2` `ClassVar` is therefore **a `qmf-venue` increment item to relax**."* Annotation :715 |
| H7 `promotion/`, `qmn/roster`, missing map rows | **PRESENT** | Seed :817 carries `promotion/`; TN-22:606 Binds is *"`qmn/config` roster"*; map rows for promotion/activation and for seat hosting present at :941/:940. All 25 TNs appear in the Capability map |
| H8 bootstrap never installs `just`; no pin | **PRESENT** | TN-16:500 — *"**install `just` at its pinned version**"*; Stack :782 — *"**v1.58.0 (released 2026-08-03; verified 2026-08-28)** — pinned and registered as an external tool in the AD-6 register"*; seed :849 |
| H9 node "adds" observation kinds vs no second catalog | **PRESENT** | TN-13:445 — *"The node **adds no journal type**; it proposes the mapping rows"*; annotation :707 adds `(position read-back) → observation` and `(balance read-back) → observation` to CT-20's table |
| H10 drain window and `WatchdogSec` in no list, no row | **PRESENT** | TN-4:220 mints both; mint-table rows :737–:738 tagged **blocks-boot**; TN-16:502 — *"**`TimeoutStopSec` and `WatchdogSec` are RENDERED into the unit file from the resolved config artifact's `drain_window` and `watchdog_interval` by `just node-install`, never authored by hand**."* |

### regate-operator-reconcile (0C / 1H) and regate-fix-regression (0C / 1H) — both PRESENT

| Id | Verdict | Closing sentence |
| --- | --- | --- |
| operator-reconcile H1 egress list vs the stack | **PRESENT** | TN-16:506 — *"**the container image registry (or a vendored image source) the observability stack pulls from**"*; TN-15:490 — *"**Provisioning installs and version-pins a container runtime for this stack alone, and the egress allow-list gains the image registry**."* Stack row :783 |
| fix-regression H-1 stale shadow-lane inherited row | **PRESENT** | Inherited Invariants :96 — *"the **shadow-lane SEAM is explicit V1 node work** (TN-19) … while its **ML and training half is deferred**."* |

**Regression result: 44 / 44 PRESENT. 0 PARTIAL. 0 MISSING.**

---

## 2. BLOCKERS — new contradictions left by residual pass 2 (4 HIGH, 0 CRITICAL)

### BLOCKER 1 (HIGH) — TN-24 (f) and TN-25 still call floating P&L "an explained **drift** component", which residual pass 2 made false in TN-10

Pass 2 redefined drift (ruling 10): TN-10:369 *"**Drift is a non-zero residual in (a) or in (b)**"*, and TN-10:368 *"**UNREALIZED P&L ENTERS NEITHER RESIDUAL** … not a term in a residual."* Two downstream sentences were not updated:

- TN-24 (f):643 — *"Floating P&L is an explained **drift** component, never swept."*
- TN-25:664 — *"**Floating P&L is an explained drift component, never swept** (TN-10, TN-24 (f)): it is **decomposed** and named…"*

`ledger/` is built from TN-25. Its builder reads "drift component" plus the drift-decomposition verb "decomposed" and puts an unrealized term into the residual — the exact behaviour that sets `operator_review` permanently on any open position and gates promotion forever, i.e. adversarial C6 re-opened by the wording pass 2 left behind.

**Exact sentence to add** (replacing the quoted clause in TN-24 (f) and the TN-25 bullet's opening):
> **Floating P&L is an explained, named component of the equity narrative and is never swept — and it is NEVER a term in either reconciliation residual** (TN-10): it is a mark, not a fact, and marks are never reconciled.

### BLOCKER 2 (HIGH) — assumption-register row A34 contradicts TN-18, the parent annotation and its own inline tag

- Register :1035 — *"| A34 | `value-status` minted as **a new registry field** rather than left to the blank-versus-filled split | TN-18 |"*
- Inline A34, TN-18:557 — *"`value-status` minted as a **per-value field on the config artifact** with `value_status_required` as the registry's schema half"*
- TN-18:546 — *"putting it in the registry would make the countersign a git edit plus a deploy — not a powers call, not journaled as a control action, and not revalidatable against fresh state at click time."*

The register declares itself *"the current reconciled view"* (:998), so a builder or the documentation factory reading A34 there lands on the position GATE-2 ruling 22 overturned. This is the two-homes-for-one-value defect rubric C3 raised, re-introduced in the one section that claims to be authoritative.

**Exact sentence to add** (replacing register row A34's assumption cell, and extending its Owning-TN cell to `TN-18, TN-17, TN-20`):
> `value-status` minted as a per-value field on the resolved config artifact — Book-declared values included — with `value_status_required` as the registry's schema half, rather than as a registry field or left to the blank-versus-filled split.

### BLOCKER 3 (HIGH) — `sealed-archive` is an eighth AD-19 room role presented as one of the parent's seven, with no parent annotation

TN-3:162 — *"**Room-role placement, per world** (**AD-19's seven roles**, instantiated for `live` and for `replay`): ingest door, immutable raw archive, processed and journal rooms … the split-governed research door, the registry room and a named **`sealed-archive`** role … the backup role is the bucket."*

The parent (`architecture-QMX-2026-08-19` AD-19:186) declares the seven as *"ingest door, immutable raw archive, processed, journal, split-governed research door, backup, and the **registry room**"*. TN-3 enumerates **eight** under a parenthetical claiming seven — `sealed-archive` is node-added. A44 already knows it is node-minted, but the "Parent annotations and mints proposed by this sitting" section proposes **no** AD-19 annotation, while this spine surfaces an annotation for every other parent-surface addition (CT-20 mapping rows, CT-25 projections, `node_resurrect`, `value_status_required`, the async exemption, the `SessionTopology` relaxation, the PRD §3 widening). The documentation factory will either write an eighth AD-19 role into `docs/` with nothing ratifying it — the silent child amendment TN-1 refused for L30 and TN-11 refused for AD-28 — or bounce the row.

**Exact sentences to add** (correct the parenthetical in TN-3:162, and add one annotation row):
> TN-3:162, replacing the parenthetical: *"(AD-19's seven roles plus one node-minted eighth, `sealed-archive`, all instantiated for `live` and for `replay` — the addition is surfaced as a parent annotation below, never asserted)."*
>
> New row in **Parent annotations and mints proposed by this sitting**: *"**AD-19 `sealed-archive` room-role addition.** AD-19 declares seven room-roles per world. The node's one-way evidence sync needs a named target that is neither a hot room nor the bucket, and the replay import port and the backup read it by name. Record the addition of an eighth role, **`sealed-archive`**, instantiated per world in the evidence tier under the same retention, backup and migration law as the other seven — a parent amendment for the documentation factory, never a child's call (TN-3, TN-13, TN-21, A44)."*

### BLOCKER 4 (HIGH) — the roster cannot express the sensing-only live connection that ruling 32, TN-9, TN-23 and the Deferred row all depend on

- TN-9:341 — *"the live connection is opened for sensing and recording — **no live binding, no command stream open, no live roster binding minted** … **The connection count is derived from the roster** (TN-11): a soak roster naming one `(venue, environment)` pair opens one connection, a roster naming two opens two."*
- TN-11:413 — *"one connection per `(venue, environment)` pair **the roster names**"*
- TN-22:609 / TN-2:142 — the roster is *"account bindings `(VenueId, AccountId, role, world)` with credential references"* and nothing else; `environment` is not a roster field and is reachable only through a binding's `role`.

With no live roster binding minted there is no live-environment entry, so no live connection opens, so the live-conditioned SQS and rung baselines never accumulate — and TN-23:628's acceptance item (*"a LIVE-CONDITIONED SQS baseline and a live-path rung baseline … minted from the sensing-and-recording-only live connection"*) and the Deferred row :963 (*"a late approval therefore delays the live milestone, never the week"*) are both unreachable. Two builders diverge here, and the cheaper reading mints a `role = live` account binding during the soak — precisely what TN-9 forbids.

**Exact sentence to add** (TN-22's roster bullet, cited from TN-9 and TN-11):
> The roster additionally carries **SENSING-ONLY ENTRIES**: a `(VenueId, environment, AccountId, credential reference)` row with **no Book binding, no BMS instance and no command stream**, which opens its `(venue, environment)` connection for subscription, recording and baseline minting and for nothing else. A sensing-only entry mints no AD-29 binding, resolves no `execution_target`, and the composition refuses to open a sequencer against it; it is how the live environment is named during the soak week before any `role = live` binding exists (TN-9, TN-11).

---

## 3. LOW nits (10, one line each — none blocks certification)

1. **TN-6:258 narrows AD-33's trigger.** Attachment fires *"Where the Book's `exit_policy` requires protective-stop attachment"*, while the AD-33 text quoted by RC-2 fires *"Where CT-18 declares protective-stop attachment, every live order attaches"* — so TN-4's full-disk/stand-down/shutdown and TN-7's dead-wire arguments, which the same bullet says *"all rest on it"*, silently do not hold for a Book that requires no attachment.
2. **TN-3 diagram contradicts TN-11's Rule.** Edges :204–205 read *"connection 1 of 2"* / *"connection 2 of 2"*, asserting a fixed count against TN-11:413's *"DERIVED FROM THE ROSTER … never a fixed requirement"*.
3. **Singular "residual" survives in two read surfaces.** TN-15:479 exports *"reconciliation (last verdict, **residual**, age)"* and TN-17:520 serves *"reconciliation status and **residual**"*, where TN-10 now has two separately reported residuals.
4. **The slice-progress watch's trip multiplier is unnamed.** TN-19:566 fires at *"`seat_callback_deadline` by a declared factor"* — no variable name, no mint-table row, no blank-effect tag, though it decides when the node restarts itself.
5. **The shadow lane's own bound is unnamed.** TN-19:574 — *"a candidate that cannot publish inside **the shadow lane's own declared bound**"* — no name, no registry row.
6. **The news-recorder retry policy is unnamed.** TN-13:448 — *"at most **a declared number of attempts** per timer firing with **a declared backoff**"* — neither is a named variable or a mint-table row.
7. **TN-1:130 over-claims the ops principal.** *"recipes run under the powers channel's **ops principal**"*, yet `node-install`, `node-switch` and `node-rollback` write unit files, create service accounts and flip `/opt/qmx` — privileged host acts with no declared privilege path (TN-12:432 declares one only for provisioning). TN-17:532 states the correct, narrower version.
8. **The third `VenueClientPort` implementation has no selection key.** TN-11:412 ships THREE implementations under a rule keyed on `(world, VenueId)`, but no world selects the FEAT-0023 conformance double; its injection path is left to the reader.
9. **One bare "calendar" survives an operational phrase.** TN-2:143 — *"a data revision never requires a restart while **a calendar** code change does"* — against Conventions :765's *"Never bare **'calendar'**, in operational phrases as much as in rules"*.
10. **`r_unit_price`'s alternate cadence has no home.** TN-25:660 — *"unless the Book declares another cadence — **and it must declare one**"* — names no variable, no registry row and no refusal category for its absence.

*(Two further observations, recorded not counted: TN-4:218's list of exiting failures omits TN-4:221's failed-drain non-zero exit, which TN-4:219's boot-attempt-counting rule nonetheless covers; and NFR-10's "no container requirement" is true of the node but false of the soak gate, since TN-23:628 requires the stack's dashboards to render for the full week — the spine names this boundary explicitly at TN-15:489, so it is a declared consequence, not a hidden one.)*

---

## 4. MECHANICAL — ALL GREEN

| Check | Result |
| --- | --- |
| 25 TN blocks, TN-1..TN-25 | **PASS** — 25 `### TN-` headings, 25 `**Binds:**`, 25 `**Prevents:**`, 26 `**Rule:**` (the 26th is the "Dependency direction" block at :689, as prior gates recorded) |
| `<!--` | **PASS** — zero |
| Balanced fences | **PASS** — 14 fence markers, 7 balanced blocks (6 mermaid + 1 `text`) |
| Mermaid validity | **PASS** — 6 blocks, every one with ≥1 edge (19 / 16 / 18 / sequenceDiagram / 15 / 11); no `\|`, parenthesis or quote inside any `[…]` label; brackets balanced. The three `[( … )]` hits are mermaid's cylinder-shape syntax, not characters in a label — label text is clean |
| Banned vocabulary | **PASS** — "engine", "kernel", "plugins", "exam", "minimal core" appear only inside the Conventions prohibition (:765); "paper node" only inside TN-1's prohibition (:127); "timeframe" only inside the `BarSpec` prohibition; **zero** "stop-out", **zero** "minimal core"; one bare "calendar" survives (LOW-9) |
| Operator command forms | **PASS** — zero `Door 2`; zero `` `qmn <verb>` `` command forms anywhere |
| Configurables ↔ mint table | **PASS** — 29 mint-table rows, every one 4 columns with a non-empty blank-effect cell carrying `blocks-boot` / `blocks-role-live` / `blocks-soak`; every configurable named in a TN resolves to a row, `news_calendar_max_staleness`, `drain_window`, `watchdog_interval`, `evidence_channel_budget`, `governor_*`, `seat_*` included. `kill_line_capital_floor` and `holdout_months` are correctly absent as pre-ratified inherited keys (TN-18:546, :553), the former reached by the generated `blocks-soak` rule at TN-18:555. Four unnamed values noted as LOW-4/5/6/10 |
| Frontmatter | **PASS** — all 15 keys present (`name`, `type`, `purpose`, `altitude`, `paradigm`, `scope`, `status`, `created`, `updated`, `binds`, `parent`, `siblings`, `sources`, `companions`, `provenance`); `provenance` records both the operator round and the re-gate; `status: draft` as expected |
| Register A1–A47 ↔ inline tags | **PASS structurally** — 47 register rows, 46 inline ids; the only register row without an inline tag is **A8**, explicitly marked *"RETIRED at the reviewer gate"*; zero inline tags lack a register row. **Content defect at A34 — see BLOCKER 2** |
| Operator-rulings section vs the memlog | **PASS** — all four rulings (R1–R4) and the "Also ruled" paragraph reproduce the memlog's `OPERATOR RULINGS 2026-08-28` entry faithfully; every quoted phrase matches verbatim ("there is nothing like commands or anything…", "the same setting or the same logic behind even the agentic system", "that question is not for this layer", "a very separate system, like how big tech teams work", "two days to a week… I think a week is enough and sufficient", "I know what you're talking about", "a simple click on the user interface… two separate acts", "doesn't concern you… focus on live trading", "I will not pay for news", "later versions, yes, we're going to iterate", "if we haven't, leave it for now", "QMF is portable"). The memlog's "the node is a plug-in to the UI" is rendered as *"the node is one surface inside that UI"* — a deliberate paraphrase honouring the banned-vocabulary rule, with only the operator's own parenthetical quoted |

---

## 5. What to do

Close BLOCKERS 1–4 at desk in one pass (four sentence-level edits, one new parent-annotation row, one register-cell rewrite). No operator round is needed: none of the four changes a ruling, and all four are the spine's own stated positions applied to sentences pass 2 left behind. Optionally sweep the ten LOWs in the same pass — they are all one-line clarifications. Then `status: draft` → `status: final` is safe, and the spine is ready for `/documentation-factory` absorption.
