# Re-gate review — ADVERSARY lens, second pass

- **Target:** `ARCHITECTURE-SPINE.md` (Trading Node), 951 lines, TN-1..TN-25, status `draft`
- **Read in full:** spine (951 lines) and `.memlog.md` (49 entries)
- **Baseline:** first gate (6 lenses, 150 findings) applied in `reviews/fix-pass-1.md`; operator round 2026-08-28 (R1-R4) applied. This review certifies the CURRENT text. Nothing from the first adversarial pass (C1-C7, H1-H15, M1-M10, L1-L4 there) is re-reported unless it survives in a new form, which is noted where it happens.
- **Method:** construct pairs of units one level down (epics/stories) that obey every TN to the letter and still build incompatibly, concentrating on text ADDED by the fix pass and the operator round; then hunt the money-path classics against the amended text.
- **Verdict:** **DO NOT RATIFY AS-IS — CHANGES REQUIRED.** Seven criticals, all of them created or left open by the fix pass and the operator round. Every one is closable at desk with the Rule sentence given; none needs the operator.

**Counts:** 7 critical / 12 high / 10 medium / 4 low = 33 findings.

---

## The constructed pairs (the method's output, in one table)

Each row is two epics/stories that each satisfy every TN sentence and cannot both ship.

| # | Surface | Unit A builds | Unit B builds | Why they cannot both ship | Finding |
| --- | --- | --- | --- | --- | --- |
| 1 | stand-down vs the entry-side-only law | Sequencer refuses every bot- and Book-minted intent in stand-down (TN-4 verbatim) | Sequencer refuses `place_order` and risk-increasing amends only, whatever the author (TN-6 verbatim, "NOTHING ELSE") | A blocks every Book-owned exit — the `ExitLogicModule` close, the force-flat triggers — during a `halt` band. B does not. Both cite a Rule sentence. | C1 |
| 2 | replay vs live dispatch | Root selects the `VenueClientPort` implementation by `VenueId` (TN-22, TN-2 verbatim) | Root selects it by run mode / clock (TN-5's "differ only in which clock and which implementation") | A's replay of an IC Markets day selects the cTrader client and submits to the live venue | C2 |
| 3 | news refresh cadence vs the in-force window | Recorder supersedes by `(source, id, revision)`, newest revision wins (TN-13 verbatim) | Recorder applies revisions but never narrows an in-force window | A opens entries mid-blackout when Forex Factory downgrades or moves an event; B keeps them shut. Automatic protective de-escalation. | C3 |
| 4 | auth failure on a command | Retry-after-refresh, per TN-12 | Never retry a command, per TN-11 ("command retry is prohibited") | A duplicates a `place_order` across a token rotation | C4 |
| 5 | where the socket lives | The asyncio TLS socket, session and secret value land in `qmf-venue` (TN-11 A37, TN-12's "connection manager") | They land in `qmn` because TN-2 says the node is the ONLY place async, broker sessions and secret values exist | Different distribution, different epic, different CI gate; and QMF's async conformance test bans A today | C5 |
| 6 | the toolkit vs the doors | Recipes import the Python API (TN-17: "the surface the operations toolkit's scripts import") | Recipes call the evidence/powers channels (TN-1: "the same read or act call ... no privileged path of its own") | A composes a SECOND composition root in a second process — ambient time, secrets, `WriterId`s — which TN-2 exists to forbid | H5 |
| 7 | the observability stack's network | `network_mode: host`, scrape `127.0.0.1` | bridge + `host-gateway`, node binds `/metrics` off-loopback | B un-localhosts the evidence channel; A puts Grafana on the host network. The spine says "localhost-bound" and "containers" and never reconciles them | H3 |
| 8 | the shadow lane | Candidate labeler registered at Compose, identity into `composition_fp`, computed inline per instant (TN-19 verbatim) | Candidate computed off the trading path under a separate `shadow_composition_fp` | A makes every governed evidence row's identity depend on an ungoverned experiment, and lets a zero-authority component breach `max_slice_latency` into a `no-new-entry` band | H4 |
| 9 | ledger vs drift vs equity | Residual = venue equity (balance + venue-marked unrealized) − virtual-ledger equity (node-marked unrealized), epsilon 0 | Residual = quantity reconciliation and cash reconciliation, separately, marks excluded | A produces a permanent non-zero residual on any open position, which sets `operator_review`, which gates the NEXT promotion forever | C6 |
| 10 | powers principal | One declared operator principal; the toolkit runs as it | Two principals, the ops one refused for trading powers | A makes "no recipe flattens, promotes or activates" an assertion behind a transport that cannot tell them apart; B breaks the toolkit's own notify-test and drill calls | C7 |
| 11 | the calendar writer | Calendar timer writes calendar observations directly under its own `WriterId` (TN-3) | Calendar timer hands work to the running node through the doors (TN-2's abbreviated-ceremony escape) | The doors have no ingest capability; A is a second first-writer against TN-5's law as TN-13 restates it | H7 |
| 12 | `node-switch` | `uv sync --frozen` into the live `/opt/qmx` while the node runs (TN-16 verbatim order) | Materialize the new tree beside it and flip a `current` pointer at the restart | A lets a mid-switch conformance or benchmark spawn run new code under an old sealed `composition_fp` | H1 |

---

## CRITICAL

### C1 — Node stand-down blocks Book-minted EXITS. TN-4 and TN-6 say opposite things about the same act.

**Spine sentence (TN-4, line 209):** "In stand-down the sequencers refuse and journal **bot-minted and Book-minted intents only**."
**Spine sentence (TN-6, line 238):** "Every block the node can raise on a command stream — ... node stand-down, a clock band, a full disk — refuses `place_order` and any **risk-increasing** `amend_protection` and NOTHING ELSE."

Exits are Book-minted. AD-33 puts exit ownership in the Book's `exit_policy` via `ExitLogicRef`; TN-8 names `hold_time_force_flat`, `boundary_flat`, `window_forced_flat` and `protection_forced_flat` as **declared Book triggers at AD-37 rank 2**. None of them is operator-signed and none is a standing protection intent, so TN-4's rescue clause ("Operator-signed protective commands ... and the standing-intent dispatcher always pass") does not reach them. A clock `halt` band enters node stand-down automatically (TN-14 line 437); under TN-4's reading every automated exit in the system stops while positions stay open behind nothing but the venue-resident stop, and the state is left ONLY by an operator `resurrect`. This is precisely the failure L39 exists to prevent, re-introduced by the fix pass's own stand-down text.

**Rule sentence to add (TN-4, replacing the quoted clause):**
> In stand-down the sequencers refuse and journal ENTRY intents only — `place_order` and risk-increasing `amend_protection` — whatever their author. Every risk-non-increasing act passes whatever its author: a Book-minted protective close, a declared force-flat trigger, an `ExitLogicModule`-derived exit, a bot-proposed risk-non-increasing tighten, the standing-intent dispatcher and every operator-signed protective command. TN-6's entry-side-only law governs this state as it governs every other block; "bot-minted and Book-minted intents" in this rule means the entry half of their output and nothing else.

### C2 — The replay adapter is selected by `VenueId`, so a replay run can submit to the live venue.

**Spine sentence (TN-22, line 570):** "Connections are keyed by `(venue, environment)`; the `VenueClientPort` implementation is selected by **`VenueId`** at the root."
**Spine sentence (TN-2, line 142, Compose):** "`VenueClientPort` implementation selection by `VenueId`".
**Spine sentence (TN-5, line 230):** "Backtest, replay (TN-21) and live differ only in which clock and which `VenueClientPort` implementation the root binds."

A replay of a recorded IC Markets day has `VenueId = IC Markets`. Selection keyed on `VenueId` alone therefore resolves to the cTrader client, and TN-2 states that keying as a composition input verbatim. TN-21's "Commands are NEVER submitted" is a statement about the run, not a constraint on the composition. Two builders read one sentence two ways and one of them wires live credentials into a regression tool. Nothing anywhere says a replay composition is credential-free.

**Rule sentence to add (TN-2, TN-11 and TN-22, replacing every selection sentence):**
> The `VenueClientPort` implementation is selected by the pair `(world, VenueId)`, never by `VenueId` alone: `world = replay` selects the replay implementation for every `VenueId`, and the composition REFUSES to bind any venue-connecting implementation into a replay composition. A replay composition resolves no credential reference, constructs no `SecretStore` venue holder and opens no socket; preflight proves all three and refuses the boot otherwise.

### C3 — A news-calendar revision can automatically shrink, downgrade or delete a protection window that is in force.

**Spine sentence (TN-13, line 418):** "idempotent intake with provider-native `(source, id, revision)` identity and revisions."
**Spine sentence (TN-13, line 419):** "`news_calendar_refresh_cadence` is a `configurable: true` node variable ... evidence: **every 2 h and before each session open**."

Forex Factory revises its weekly file: an event's time moves, its impact label drops from High to Medium, an entry disappears. Under the current text the newest revision simply supersedes. A refresh landing at 13:28 can therefore end a blackout that is protecting a 13:30 release, and entries open. The spine armors the KSA fold against automatic de-escalation (TN-7's monotone level epoch), armors AD-36's satisfaction predicates against clocked clears, and then leaves the protection windows — the most frequently changing protective state in the system — de-escalatable by an unattended twice-hourly fetch of a free file. This is the auto-de-escalation classic, sitting on a path the operator round newly made twice-hourly.

**Rule sentence to add (TN-8's news blackout bullet, cited from TN-13):**
> A calendar revision may only WIDEN or ADD a protection window that is currently in force or that begins within the current trading day. A revision that would narrow, shorten, downgrade the severity of, delay the start of, or remove such a window is ingested and journaled as evidence, takes effect no earlier than the end of the window the superseded revision declared, and never opens entries the superseded revision blocked. Calendar-driven de-escalation is never automatic; shrinking an in-force window is an operator act on the powers channel, journaled with both revisions cited.

### C4 — "Retry-after-refresh" and "command retry is prohibited" collide on the money path.

**Spine sentence (TN-12, line 404):** "An authentication failure attributable to a rotation in flight is a **retry-after-refresh condition, never an UNKNOWN**."
**Spine sentence (TN-11, line 390):** "Command retry is prohibited; session recovery never resubmits (`ct-19:31`)."

Nothing scopes TN-12's sentence to session-level calls. A `place_order` that meets an auth error after wire handoff is exactly "attributable to a rotation in flight", and the remedy TN-12 offers is a retry. The venue may already have accepted it. This is a duplicate-order path minted by a secrets rule, and the "never an UNKNOWN" clause actively removes the L35 protection that would otherwise block the stream.

**Rule sentence to add (TN-12, appended to the quoted sentence):**
> Retry-after-refresh applies ONLY to requests that carry no command identity — session auth, account auth, subscription, heartbeat, gap replay and the reconciliation read-back. A `place_order`, `amend_protection`, `cancel_order`, `close_position` or `close_all` that meets an authentication failure is NEVER retried: it takes the ordinary submission-deadline path, minting UNKNOWN if it has passed wire handoff and a typed refusal on the veto path if it has not. TN-11's prohibition on command retry has no exception, this one included.

### C5 — TN-2's rule sentence and A37 put async, the broker session and the secret value on opposite sides of the library boundary.

**Spine sentence (TN-2, line 140):** "the node is the ONLY place ambient time, broker sessions, secret values, async, threads, processes, schedules and real money exist; **everything below it stays pure**."
**Spine sentence (TN-11, line 383):** the asyncio TLS socket, framing, encoding, submit path, subscription and in-band token refresh "are a **`qmf-venue` INCREMENT that completes that existing component**."
**Spine sentence (TN-12, line 406):** "**Venue session material** ... has exactly one in-memory holder: **the connection manager**" — which TN-11 places inside `qmf-venue`.

So async, the broker session and the in-memory secret value all live in a library below the root, while TN-2 says nothing impure lives below the root. The parts-bin inventory additionally records that the QMF libraries **ban async by conformance test** (memlog entry 14, red flag R1), so the increment as specified may be illegal in its destination package. Two epic authors will split on which distribution the single largest work item in this spine lands in, and there is a Rule sentence supporting each. A37 flags the locus as a cheap veto but the spine never reconciles the two sentences.

**Rule sentence to add (TN-2, immediately after the quoted sentence):**
> One impurity is DELEGATED, named here and nowhere else: `qmf-venue`'s `ConnectionManager` holds the venue socket, the venue session and the single in-memory venue secret value, running on the loop the node injects, under the `Clock` and `SecretStore` the node injects. It owns no event loop, creates no task the node's scheduler did not schedule, reads no ambient clock and holds no money. Every other library stays pure without exception, and the QMF async conformance test is amended in the same increment to exempt `qmf.venue.connection` by name — if that exemption is refused at the parent, the increment lands in `qmn.venue.ctrader` instead, and the epics may not choose between the two.

### C6 — The reconciliation residual mixes a position comparison with cash components and marks the two sides at different instants, under epsilon 0.

**Spine sentence (TN-10, line 343):** "venue-versus-virtual divergence — the **venue position** picture against the **virtual (Book) position** fold (TN-25) — decomposes into named journaled components: swept-but-unwithdrawn cash, re-seed remnants, **open unrealized P&L on positions**, and venue-charged fees or financing not yet journaled. Only the residual is drift; **any non-zero residual sets `operator_review`**."

Three defects in one sentence. (i) The compared quantity is declared as a *position* picture, but three of the four named components are *cash*; a builder cannot tell whether the residual is denominated in instrument quantity or in scaled money integers. (ii) Unrealized P&L is listed as an explained component, so it must be computed on both sides — and TN-11 line 389 marks the venue side with "the venue's own converted figures, `converted_by = venue`" while TN-25 line 617 marks the virtual side "to the latest observed price of its own virtual positions" at the node's frontier. Two marks, two instants, epsilon 0. (iii) The consequence is not cosmetic: TN-10 line 344 says `operator_review` "gates the **next** live promotion or activation on that binding" and clears only on an operator resume. With any open position, the mark difference is non-zero on essentially every reconciliation, so `operator_review` is permanently set and promotion is permanently gated. The fix pass's own exact-integer ruling is what makes this bite, because it removed the tolerance that used to hide it.

**Rule sentence to add (TN-10, replacing the EXPLAINED DRIFT paragraph's opening):**
> Reconciliation compares TWO SERIES SEPARATELY, each with its own epsilon-0 identity, and never one blended residual. (a) QUANTITY: the sum of virtual positions per instrument against the venue's position picture for that account, in exact instrument quantity units, under the account's declared `netting | hedging` model. (b) CASH: the venue's realized balance against the virtual ledger's realized cash plus the named components — swept-but-unwithdrawn cash, re-seed remnants, venue-charged fees and financing not yet journaled — in exact scaled integers at the account money exponent. **Unrealized P&L enters NEITHER residual: it is a mark, not a fact, and marks are never reconciled**; the two equity series of TN-11 and TN-25 are reported side by side with their mark instants and are never differenced. Drift is a non-zero residual in (a) or in (b), and only that sets `operator_review`.

### C7 — The powers channel has one principal, so "the toolkit is never a trading control" is an assertion, and "an agent signer is refused BY THE TRANSPORT" is an unverified claim.

**Spine sentence (TN-17, line 491):** "a call whose peer credential is not the declared operator principal is REFUSED ... **An assertion field is not a gate**: this is what makes L17 and TN-20's agent-signer refusal enforceable rather than asserted."
**Spine sentence (TN-17, line 496):** "The operations toolkit uses THESE DOORS and no other path ... subject to the same `SO_PEERCRED` check and the same journaling."
**Spine sentence (TN-1, line 130):** "no recipe places, cancels, amends, flattens, promotes or activates anything."

If the toolkit's recipes pass the same `SO_PEERCRED` check as the operator, the transport cannot distinguish `just node-notify-test` from `flatten` at global scope, and TN-1's restriction is enforced by nothing but the recipe text — the exact assertion-not-a-gate failure TN-17 congratulates itself on avoiding. If instead the toolkit runs under a different uid, every toolkit powers call is refused and the notify test and drill trigger cannot work. Both branches are supported by the text and neither is stated.

Compounding it: **`SO_PEERCRED` proves a uid, not a human.** TN-20 line 541's "an agent signer is refused BY THE TRANSPORT, not by an assertion field" is an unverified claim — any process running under the operator's uid on the VPS (the Phase-3 backend, an ops script, a cron job, a future MCP wrapper) passes. A32 records the alternative that would have proved it (a per-operator signing key held off-node). Also unstated anywhere: the socket's path, owner, group and mode, and whether the "declared operator principal" is a login account or the `qmx` service account — and if it is `qmx`, the operator must be able to log in as the hardened service account, which unwinds TN-16's hardening.

**Rule sentences to add (TN-17, cited from TN-1 and TN-20):**
> The powers socket lives at `/run/qmn/powers.sock`, owned `qmx:qmxops`, mode 0660, created by the unit's `RuntimeDirectory`. It declares TWO peer principals, both by uid in the resolved config artifact and neither of them the `qmx` service account: the **operator principal**, which may call every power; and the **ops principal**, which may call ONLY `notify_test`, `restore_drill_run`, `config_validate` and the evidence reads. Every trading, protection, promotion, activation, settings-edit, `resurrect`, attestation and countersign power is refused for the ops principal, by the transport, and the refusal is journaled. Preflight refuses to boot if any systemd unit on the host declares an operator-principal uid.
>
> And in TN-20, replacing "refused BY THE TRANSPORT": the transport binds every powers call to a declared principal and refuses any other; it proves an account, not a human. No automated unit ever runs under an operator principal, which preflight asserts; humanity beyond that is asserted by the signer and is a named residual risk (A32), not a proof.

---

## HIGH

### H1 — `just node-switch` mutates the running node's checkout.

TN-16 line 471 orders it "preflight, backup-first, `uv sync --frozen`, a dry-run boot in check mode, then `systemctl restart qmn`". `uv sync --frozen` rewrites `/opt/qmx`'s environment while the node is still running from it. Every stdlib process-per-job the running node spawns during that window — conformance Layer-2 runs, benchmark runs (TN-4 line 206) — executes NEW code under the parent's OLD sealed `composition_fp`, and the dry run validates a tree the running node is not using. TN-2's stated purpose, "one deployment yields one value", fails for the length of the switch, and the rollback recipe has the same shape.

**Add (TN-16):** *"`/opt/qmx` is a canonical ROOT holding one immutable tree per commit plus a `current` symlink; `node-switch` materializes the new tree beside the old, runs the dry-run against the new tree, and flips `current` atomically as part of the restart. The running node, every process it spawns and the dry-run each read exactly one immutable tree, and `uv sync --frozen` never writes into a tree a running node resolved from. Old trees are pruned by a declared depth so a rollback needs no network."*

### H2 — A restart-at-safe-point cannot happen under `Restart=on-failure`.

TN-17 line 492: a settings edit "mints a new config version and schedules a restart at a safe point". TN-4 line 213: reaching the safe point "exits 0". TN-16 line 470 pins `Restart=on-failure`. Exit 0 under `on-failure` means systemd does **not** restart — the node stays down after every settings edit, silently, at the end of a drain. Exiting non-zero instead makes a deliberate edit look like a failure and feeds TN-4's crash-loop fold, so three edits inside T seconds drive the node into stand-down.

**Add (TN-4, cited from TN-16 and TN-18):** *"A requested restart exits with the reserved code 75, with `RestartForceExitStatus=75` and `SuccessExitStatus=75` in the unit, and stamps `reason = requested-restart` on the next boot-attempt record. The crash-loop fold counts UNREQUESTED boot attempts only; a requested restart never advances (K, T)."*

### H3 — The observability stack has no supervising unit, no declared storage, no declared secret home and no declared network path.

TN-15 line 458 ships it as a compose file; TN-16 line 470 names a fixed `qmx` account "for all four units"; TN-3 line 160 names the writable trees "once". The stack is none of those. Consequences, each concrete:

1. Its TSDB, Grafana database and Loki chunks are an unnamed writable tree consuming `vps_disk_budget`, so a system declared zero-authority can drive `disk_headroom_min` below its threshold and mint `no-new-entry` (TN-13 line 425) — a decision-path effect from a component that is supposed to have none. "Losing the whole stack loses visibility and nothing else" is falsified by its own storage.
2. `/metrics` is localhost-bound (TN-15 line 449) and containers are network-namespaced. A builder must pick `network_mode: host` or bridge-plus-`host-gateway` with the node binding off-loopback; the second exposes every journal projection, drift component and KSA level on the evidence channel to any container and to anything ufw does not catch.
3. Grafana's admin credential and any Loki auth token are a fourth secret holder against TN-12 line 406's "three named in-memory holders exist and no fourth".
4. Nothing starts it at boot, yet TN-23 line 585 requires its dashboards to render the exported signals "for the whole unattended week".
5. A Promtail-class shipper reading journald needs the system journal, which carries every unit's output — including the provisioning path's — against TN-15's "never hold a credential the node holds".

**Add (TN-15):** *"The stack is supervised by its own unit `qmx-observability.service` under a distinct non-`qmx` service account; it is not one of the node's units and the unit count is stated accordingly. Its storage lives under `/var/lib/qmx-observability`, sized as a named line item inside `vps_disk_budget` with its own retention caps and its own filesystem quota, so it can never consume the headroom `disk_headroom_min` protects. It runs `network_mode: host` with every container port bound to `127.0.0.1`; the node's evidence channel stays loopback-bound and is never reachable from a container, and only the `/metrics` path is scraped. Its own credentials are a DECLARED FOURTH secret holder, delivered by its own `LoadCredentialEncrypted` line, holding nothing the node holds. It reads the node's log stream through a dedicated read-only journal namespace, never the system journal."*

### H4 — Registering a candidate labeler changes the identity of governed evidence, and a shadow labeler can block live entries.

TN-19 line 532 puts a candidate's "distribution identity and version entering `composition_fp` (TN-2)". `composition_fp` is stamped on the boot-epoch record of every journal stream and every artifact label (TN-2 line 143), so switching a shadow experiment on or off re-identifies all governed live evidence, and evidence either side of the experiment is no longer comparable — the opposite of the traceability the ceremony is for. Separately, a candidate registered at the root and computed per instant runs on the loop's only domain thread (TN-4 line 206 bans threads for domain work), so it consumes slice time and can breach `max_slice_latency`, whose declared effect is a journaled `data quality` record plus a `no-new-entry` band (TN-5 line 227). An explicitly ungoverned diagnostic then stops entries. Nothing binds a candidate to the no-ambient-randomness and no-I/O rules either, though it is registered into the live runtime.

**Add (TN-19):** *"`composition_fp` covers the GOVERNED composition only. Every candidate labeler's identity and version enters a separate `shadow_composition_fp`, stamped on the shadow stream's boot-epoch record alone, so registering, changing or removing a candidate never alters the identity of governed evidence. A candidate labeler is HEAVY by construction and never runs on the slice's synchronous path: it is computed off the trading path from the frontier-stamped inputs, the slice driver neither waits on it nor counts it toward `max_slice_latency`, and a candidate that cannot publish within the shadow lane's own bound is dropped with a journaled `data quality` record and never a band effect. A candidate is bound by every rule a governed labeler is — deterministic, no ambient clock, no ambient randomness, no I/O beyond its declared frontier-bound read surface — and the composition refuses to register one that declares otherwise."*

### H5 — A replay run and the toolkit's Python-API import both construct a second composition root, in a process the spine never sanctions.

TN-21 line 554 starts a replay "from the operations toolkit's `just node-replay <day or range>` recipe or from the Python API"; TN-17 line 487 makes the Python API "the surface the operations toolkit's scripts import rather than shelling anywhere"; TN-4 line 206 permits "stdlib process-per-job only for isolated work (conformance Layer-2 runs, benchmark runs)". Replay is not on that list and neither is the toolkit. A replay run inside the node process drives a second loop on the live thread; a replay run outside it composes a root, allocates `WriterId`s and constructs sinks — all of which TN-2 line 145 makes the running root's exclusive act. The Python API being *in-process* is exactly what makes TN-17's toolkit sentence and TN-1's "through the doors" sentence incompatible for any recipe that needs live state.

**Add (TN-4 and TN-21):** *"A replay run is a stdlib process-per-job spawn OUTSIDE the node process, added here to the sanctioned isolated-work list, composing a replay-scoped root from the same resolved node-config artifact with `world = replay` `WriterId`s drawn from a disjoint namespace, no credential reference and no live sink; it never runs inside the trading node process. No operations-toolkit recipe ever constructs a composition root or imports the Python API in a process other than the node's: the config authoring recipes call pure library functions that compose nothing, and every recipe needing live state uses the evidence or powers channel."*

### H6 — Two Books on a netted account can each claim the same fill, and nothing forbids it.

TN-22 line 567 and TN-25 line 615 make the fill-to-virtual-position attribution rule "a mandatory Book declaration whose absence is a bind-time `policy rejection`" — mandatory but unconstrained. Two Books may each declare 100% attribution, or a rule set may leave a fill unattributed. Then TN-25 line 614's own sentence ("the sum of virtual positions reconciles against the venue's netted position") is arithmetically impossible, and TN-8's kill line marks each binding against exposure the other also owns, so one adverse move breaches both floors and auto-flattens twice on one netted position — with TN-22's shared-flatten signature already conceding that each flatten closes the other Book's exposure.

**Add (TN-22):** *"The set of attribution declarations on one netted account must be jointly EXHAUSTIVE AND DISJOINT: the config compiler proves at bind time that every fill on that account is attributed to exactly one virtual position across all bindings on it, and refuses the roster otherwise. A declaration set that is not a partition is an `invalid input` refusal at compile, never a trade-time discovery."*

### H7 — The news calendar is sealed into `composition_fp` yet refreshed every two hours, and a silently dead timer cannot fail closed.

TN-2 line 143 fingerprints "**every calendar identity in play (market-hours, day-boundary, news) with its version**" and seals it immutable for the boot epoch. TN-13 line 419 refreshes the news calendar every 2 h. A builder reading "version" as the ingested weekly file must restart on every refresh; a builder reading it as code identity must not — and the first reading makes the operator's twice-hourly cadence unimplementable. Separately, TN-13 line 418's "a failed refresh blocks entries fail-closed" is unenforceable as written: the refresh runs in a TIMER unit while the block must be raised in the node process, no powers capability carries a refresh-failure signal, and no staleness threshold variable exists (TN-15 exports "calendar age" but nothing bounds it). A timer that dies silently produces a stale calendar and no block at all.

**Add (TN-2 and TN-13):** *"A calendar's CODE identity and version are sealed into `composition_fp`; its DATA — the dated snapshot records the recorder ingests — are ordinary append-only observations read as of the slice frontier and are never part of the composition. A data revision never requires a restart; a calendar code change does. Mint `news_calendar_max_staleness` (do-not-default, `configurable: true`, unit-kind duration): entries fail closed on every binding holding news-exposed instruments when the newest ingested snapshot's ingestion instant is older than it, evaluated as a per-decision-cycle precondition exactly like a clock band — so a silently dead timer fails closed with no signal from the timer."*

### H8 — Timer units and the node compute `composition_fp` from different config versions after any settings edit.

TN-2 line 146: a timer "composes from the SAME resolved node-config artifact, computes `composition_fp` over **the same inputs as the node process** so one deployment yields one value". But TN-18 line 515 makes an edit take effect "at the next boot epoch", so the running node holds a SEALED older version while the config version graph's `current` pointer has moved. The next timer firing composes from `current` and stamps a different `composition_fp` than the node writing beside it — two composition identities on one deployment in the same window, which is exactly what the ceremony exists to prevent.

**Add (TN-2):** *"A timer unit composes from the config version the RUNNING NODE has sealed, read from the node's boot-epoch record over the evidence channel, never from the `current` pointer. Where the node is not running the timer composes from `current` and stamps `node-absent` on its own boot-epoch record; a timer that can neither read the running node's sealed version nor establish that the node is down refuses to write and alarms on the silent-degradation class."*

### H9 — The benchmark baseline is measured while the node is driving slices, and the AD-24 heavy-snapshot age has two candidate bounds.

TN-23 line 584 records the first baseline "by the harness in the soak's first hours, before the doors open on live bindings", and evaluates the gate "on the VPS and in the nightly window" — 10/40/100/200-seat runs on the same box as a live-connected node, whose `governor_cpu_budget` and `governor_memory_budget` are blank do-not-default (TN-18 line 512). The baseline is contaminated by the node and the node's slice latency is contaminated by the baseline; a `max_slice_latency` breach during the soak mints a `no-new-entry` band, and the nightly repetition does the same during live money hours. Separately, TN-19 line 530 makes every labeler heavy until that baseline exists, "consumed under a declared maximum age", while TN-8 line 309 makes `decision_freshness_bound` "mandatory and non-defaultable" and refuses an SQS input age exceeding it — two bounds for one quantity, and the door's behaviour differs by which a builder picks. Picking the strict one can make SQS permanently `stale` and the soak's "SQS baseline minted and a block observed" item unreachable; picking a looser one puts stale SQS on the live decision path.

**Add (TN-23 and TN-19):** *"The benchmark harness never runs concurrently with a slice-driving node process: it runs before the doors open or from node stand-down, holds `governor_cpu_budget` and `governor_memory_budget` — which are SOAK-BLOCKING, not merely live-blocking — and every baseline and gate run records the node's lifecycle state at measurement; a run recorded while the loop was driving slices is not a baseline and not a gate. The heavy snapshot's declared maximum age IS `decision_freshness_bound` and no second bound exists; a labeler that cannot publish inside it publishes `not_ready` and the door refuses entries on that instrument."*

### H10 — The workstation carries the full node library, and only prose stops it refreshing the live token.

TN-16 line 469: "`qmn` is installable on the WORKSTATION for the provisioning wizard and the Python API only." "Only" is intent, not mechanism: the same distribution carries the `SecretStore`, the composition root and the connection-manager wiring, and Credential Manager holds the bootstrap refresh token. Any workstation script that composes a root refreshes that token and kills the VPS session mid-trade — the named failure in TN-12's own Prevents line ("a laptop tool locking the VPS out mid-trade"), guarded by nothing. TN-12's refresh-by-credential-reference rule binds refreshers *inside one process*; it says nothing across machines.

**Add (TN-12 and TN-16):** *"The workstation installation is provisioning-only and ENFORCED, not asserted: `qmn`'s composition root refuses to compose on any host whose declared machine tuple is not the deployment roster's VPS entry, and the `SecretStore` refuses to construct a venue-session holder off that host. The wizard's code path holds no venue session material and never calls a refresh; a tier-1 `check` assertion proves the wizard module imports neither the connection manager nor the refresh duty."*

### H11 — The powers list omits capabilities the toolkit and the seat lifecycle require, and leaving `quarantined` is undefined.

TN-17 line 492 enumerates powers and reads closed; TN-17 line 496 then names "a restore-drill trigger" as a toolkit powers call that is not on that list, so a builder either extends a closed list or gives the recipe a local privileged path against TN-1. TN-19 line 524 introduces automatic seat quarantine with no exit; TN-20 lines 545-547 enumerate the operator-signed acts and quarantine release is not among them, while TN-20 forbids a restart re-arming exposure. A quarantined seat therefore either stays quarantined forever or is silently re-admitted by the next boot's fold — two builds, one of them re-arming exposure across a restart.

**Add (TN-17 and TN-19):** *"The powers list is CLOSED and exhaustive — a capability not on it does not exist on the powers channel — and it gains `restore_drill_run`, `config_version_activate` and `seat_reinstate`. Leaving `quarantined` is the operator-signed `seat_reinstate` act, journaled as its own CT-24 transition, never inferred from a restart, a new boot epoch, a config version or the absence of further breaches."*

### H12 — A float is still sanctioned on the money path.

Consistency Conventions, line 703: "Money is exact scaled integers; **the sole sanctioned float crossings are the declared venue decode** and the declared comparison-rule quantize." TN-10 line 342 requires that "**no float participates in the sum**" under `reconciliation_epsilon = 0`, and TN-11 line 383 lists "the cents/volume decoder" as node work — so the Conventions row sanctions a float exactly where the epsilon-0 rule forbids one, and a builder following the Conventions row produces spurious drift on every reconciliation. cTrader carries money and volume as int64 with a declared exponent, so no float is needed for either.

**Add (Consistency Conventions, replacing the quoted clause):** *"No float appears anywhere on the money path, the venue decode included: venue money and volume fields decode from their wire integers directly into scaled integers at their declared exponent, and a money field arriving in a floating form is refused rather than converted. The sanctioned float crossings are the decode of non-money venue fields the wire itself carries as floats, and the declared comparison-rule quantize."*

---

## MEDIUM (10)

| # | Finding (with the spine sentence) | Fix |
| --- | --- | --- |
| M1 | Alert allow-list membership has three homes: TN-15 line 452's enumerated three classes, `FAILURES.md`'s `notification tier` column ("the allow-list is GENERATED from" it, line 453), and a minted registry row "the silent-degradation ALERT CLASS membership" (line 684). Generation exists to prevent drift and here creates it. | Declare `FAILURES.md`'s column the SOLE home; TN-15's three classes are that column's closed vocabulary; withdraw the registry membership row. |
| M2 | One `qmn-restore-drill.timer` (TN-16 line 470) must serve two cadences — nightly sample and monthly full (TN-13 line 422) — plus an on-demand host-loss rehearsal. Not expressible in one timer unit. | Name `qmn-restore-sample.timer` (nightly) and `qmn-restore-full.timer` (monthly); the host-loss rehearsal is the `restore_drill_run` power. Correct the "all four units" counts in TN-16. |
| M3 | The nightly backup copies "every journal room" (TN-13 line 421) while the node writes them; no consistency rule, so a restored room can hold a torn record and verify-before-purge verifies the copy against itself. | *"The backup unit copies only journal segments sealed at a committed sequence boundary, reading each stream's last committed sequence from the running node over the evidence channel; an open segment is copied to its last sealed boundary and the boundary is recorded in the backup manifest, so a restored room is always a prefix of a real stream."* |
| M4 | TN-11 line 385 says the port ships "two V1 implementations"; TN-23 line 581 requires a venue conformance double that "both a test double and the live cTrader client must pass" — a third. A builder counting two will not build the double behind the port, and the CI-earned money-path proofs evaporate. | State three V1 implementations: cTrader client, replay adapter, conformance double; the double implements the same port or the suite proves nothing about the port. |
| M5 | TN-1 line 131 makes "the node's composition root" the one sanctioned importer of `qmf-venue`, but TN-11 line 384 puts duty scheduling, the verification-suite runner, the CT-18 fills and the error-map rows in `qmn/venue/ctrader/`, all of which must import it. The L30 default-deny lint has no writable boundary. | *"The sanctioned import boundary is the `qmn.venue` subpackage, not the root module alone; every other `qmn` module receives `VenueClientPort` and CT-19/CT-20 shapes only, and the L30 lint is written against that boundary."* |
| M6 | TN-17 line 500: "a value fixed within an active cycle, such as the kill line, is not editable mid-cycle" — "active cycle" is never defined, and TN-25's accounting period is only a candidate. Two builders pick different windows for the same money variable. | *"An active cycle is the open accounting period of the binding, opened and closed by TN-25's day-boundary calendar; a cycle-fixed value edited during one takes effect at the next period open, and the powers channel says so at the click."* |
| M7 | Where a Book-declared value's `value-status` lives is unstated: TN-8 line 301 makes `kill_line_capital_floor` Book-declared, TN-18 line 510 makes the registry the schema home and the config artifact the value home, and TN-18 line 508 makes Book fragments generated derived artifacts. TN-20's battery must read the status from somewhere. | *"`value-status` lives on the resolved config artifact's row for every value, Book-declared values included; the registry declares the field, the source definition supplies the value, and the compiler propagates the status onto the generated fragment."* |
| M8 | The calendar recorder has no declared retry policy, yet must stay inside "roughly 2 downloads per 5 minutes" (TN-13 line 419) which the compiler checks only against the configured cadence. A retry loop on a failing fetch breaches the provider limit and can get the host blocked — which fail-closes entries indefinitely on the sole V1 source. | *"The recorder's retry policy is declared: at most N attempts per timer firing with a declared backoff, counted against the same 2-per-5-minutes budget; a provider rate-limit or block response is journaled `data quality`, alarmed on the silent-degradation class, and never retried inside the same firing."* |
| M9 | TN-15 line 458's "never hold a credential the node holds" is undermined by any journald-reading log shipper, which sees every unit's output including the provisioning path's stderr. | Covered mechanically by H3's dedicated read-only journal namespace; state it beside the zero-authority claim rather than leaving it implied. |
| M10 | TN-13 line 425 sizes journald `SystemMaxUse`, room retention and backup staging against `vps_disk_budget`, and TN-3 line 160 names the writable trees "once" — neither list includes the observability stack's volumes, nor the per-commit trees H1's fix introduces. | Add both to the named-tree list in TN-3 and to the disk-budget line items in TN-13. |

---

## LOW (4)

| # | Finding | Fix |
| --- | --- | --- |
| L1 | **Vocabulary violation, self-contradicting inside its own sentence.** TN-24 (j), line 604: "a venue **stop-out** or margin liquidation ... (the bare phrase is never used)". The Conventions row bans the bare word. | Replace with "a venue margin liquidation or venue-initiated close". |
| L2 | `qmn-calendar.timer` (TN-3 line 168, TN-13 line 418, TN-16 line 470, structural seed line 770) is a bare "calendar" name against the Conventions row "Never bare **'calendar'**: market-hours, day-boundary and news calendars are three named kinds". | Rename to `qmn-news-calendar.timer` in all four places. |
| L3 | The Stack row for `just` (line 719) says recipe bodies "call `uv run` scripts under `qmn/deploy/` with stdlib `argparse`" — an argument parser in a product ruled to have no command line reads as a re-entry of the deleted surface, and nothing prevents a console-script entry point appearing. | *"...with stdlib `argparse` for recipe arguments only; these scripts are DevOps entry points invoked by `just`, never a product command line and never installed as console scripts"* — plus a tier-1 `check` assertion that `qmn`'s packaging declares no console-script entry point, alongside the existing no-publishable-target assertion. |
| L4 | The structural seed names `deploy/justfile-recipes/` (line 772) while TN-1 line 130 says recipe bodies "live under `qmn/deploy/`" and TN-16 line 471 calls them "an idempotent script in the checkout". Three phrasings, one directory. | Pick one path and use it in all three. |

---

## What I could not fault (second pass)

- The entry-side-only law (TN-6) is stated once and cited consistently everywhere except TN-4's stand-down clause (C1) — that is the only surviving hole in it, and it is a wording collision rather than a design gap.
- AD-36's satisfaction predicates, the monotone KSA level epoch and the `resurrect`/`resume` split survive every de-escalation attack I could construct except the calendar one (C3), which reaches the windows rather than the levels.
- The command-ordinal / journal-sequence split, the durable command-id-binding record persisted before submission, and the wire-handoff deadline start are airtight; I could not construct a duplicate-identity or a timeout-as-rejection path through them. C4 gets in through the secrets rule, not through the order path.
- `state_carry`, `carries-ledger` and `continues-performance` close the silent-money-carry path cleanly, and TN-25's "a boundary act never touches positions and never re-bases a frozen R" survives every compound-command and rollover attack.
- The replay world fencing — `world` as a `BotStateScope` component, provenance-derived rather than caller-declared, a one-way import port off the evidence tier, no write exception — is sound. The only way in is the port-selection ambiguity of C2.
- The promotion / activation split and the sandbox-provenance refusal on the one reverse crossing hold. The countersign's missing evidence predicate is the residual there and is folded into TN-18/TN-20 by way of the value-status fix below.

**One addition worth making even though it is not a defect in the two-builders sense** (record it with the value-status text of TN-18 line 511): a `value-status` countersign is currently a bare operator click with no declared predicate, and TN-9 concentrates every live-gating countersign into one sitting at the end of the soak week. Add: *"A `value-status` countersign is refused unless the powers call carries the variable's EVIDENCE CITATION — the journaled measurement, soak observation or ratified source record the value rests on, by `fp1` — and the plain-words summary rendered to the signer names that citation; a countersign with no citation is an `invalid input` refusal, and a bulk countersign of more than one variable in one call does not exist."*

## Gate recommendation

**CONDITIONAL — apply C1-C7 and H1-H12 at desk, then re-lint.** All nineteen are desk fixes with the sentence supplied; none reopens an operator ruling, none changes a TN id, and none needs the operator. C1, C2, C3, C4 and C6 are money-path defects that would ship as built behaviour if the epics were cut from this text today.
