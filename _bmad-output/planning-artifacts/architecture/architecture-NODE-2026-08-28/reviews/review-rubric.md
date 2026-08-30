---
review: RUBRIC WALKER (the good-spine checklist)
target: ARCHITECTURE-SPINE.md — Trading Node (architecture-NODE-2026-08-28)
reviewed: 2026-08-28
reviewer_lens: rubric walker — divergence coverage, Rule-vs-Prevents enforceability, Deferred leakage, tech currency, brownfield ratification (parts-bin §3), operator coverage, inherited-AD consistency (AD-27/28/35/36/40 spot-check), altitude-owned dimensions incl. the operational envelope
verdict: CONDITIONAL PASS — the spine is coherent, well-sourced and honest about its assumptions; 3 critical and 8 high findings must be closed before epics are cut, because each is a point where two independently-built units would diverge on live money.
counts: 3 critical / 8 high / 13 medium / 4 low (28 findings)
---

# Rubric review — Trading Node spine

## What the walk confirmed clean

Recorded so the gate is not re-run on settled ground:

- **Frontmatter** is complete and internally consistent (`type`, `purpose`, `altitude`, `binds`, `parent`, `siblings`, `sources`, `companions`, `provenance`); `status: draft` is correct with the reviewer gate open.
- **No template comment, placeholder, `{{ }}`, TODO or TBD survives** anywhere in the file.
- **Banned vocabulary is honored**: "engine", "kernel", "plugins", "exam", "minimal core" and "paper node" appear only inside their own prohibitions (`:121`, `:571`). "The trading node — ONE product, modes `paper | live`" holds throughout; the asyncio event loop is never renamed.
- **Six mermaid blocks parse** (paradigm, TN-3 topology, TN-6 order path, TN-10 boot sequence, dependency direction, process internals). Subgraph-with-title syntax, `-- label -->` edges, `-. label .->` dotted edges, cylinder nodes and forward-referenced node ids are all legal; 14 fences = 7 blocks, balanced.
- **Every adaptation seam in `inputs/parts-bin.md` §3 has a home.** All 28 seam rows are reproduced in "Ports the node implements" with their file:line anchors intact; the do-not-default roster from §3's closing paragraph is carried into TN-6/TN-18 (one exception, M12).
- **The Capability map covers the memlog's scope line** (composition root, Book/BMS runtime, QML seats, cTrader order path, MIS-Live seam, live data recording, operator doors, logging/monitoring/DevOps envelope) plus the operator's extra coverage rows (trendbars, clock drift, resource footprint, QA debt, time and calendar edge cases). One capability in the scope line has no owning rule — see H1.
- **The adjudicated corrections are carried faithfully** (four reconciliation verdicts, paper as a standing evidence state, `world = replay`, the closed SDK question, the closed SQS formula, the constructed boot ceremony declared as constructed, AD-40 overriding adjudicator B on partial fills).

---

## CRITICAL

### C1 — The kill line has no declared input series and no evaluation cadence
**Where:** TN-8 (kill line bullet, `:259`); TN-11 equity derivation (`:333`); TN-24 (f) (`:509`); against parent AD-40 (`book_capital` … "excluding unrealized P&L on open positions") and AD-36 (kill line = per-Book capital floor whose breach automatically flattens).

**What:** TN-8 fixes the kill line's *value* ("the SAME number as AD-40's `loss_floor`, Book-declared, blank blocks live") and its *effect* (auto-flatten the binding's scope, `close_reason = kill_line_flat`, stand the Book down). It never says **which number the breach test reads, how often, or over which position set**. Two candidate series exist in this very spine and they behave oppositely: TN-11 derives broker equity as *balance plus per-position unrealized P&L* (`converted_by = venue`), while AD-40 defines `book_capital` as the binding's virtual-ledger equity at the period-open instant **excluding** unrealized P&L. The ground-truth inventory records equity derivation as existing *because of* the kill line ("kill line is a capital floor and nothing computes balance + unrealized", memlog-14) — the spine drops that link.

**Why it matters:** this is the only automatic flatten authority on live money, and the one AD-36 designed so "a 3am breach never waits for the operator". An epic that reads the ladder's `book_capital` builds a kill line that cannot fire during a crash (it only moves on realized closes). An epic that reads broker equity builds the one AD-36 intends. Both pass every test in the spine. There is no cadence either: per slice, per fill, per tick, per rollover are all consistent with the text.

**Fix:** in TN-8 state the breach test in one sentence — the kill line is evaluated against the binding's **live equity series** (TN-11's derived broker equity, `converted_by = venue` provenance), on every slice that carries a fill or a mark update and at every accounting rollover; `book_capital` (period-open, excluding unrealized) remains the sizing ladder's input only; both read the same declared `loss_floor` value. Add the two series to the Consistency Conventions naming row so they are never interchanged.

### C2 — The backup encryption key dies with the host it protects
**Where:** TN-12 ("the object-storage/backup encryption key … ride the same store", `:347`; "systemd-creds … host-key sealed", `:344`; "It mints the KEK on the VPS", `:346`); TN-13 (`PayloadCipher` "key from the KEK store", `:360`; monthly full restore "into a scratch directory", `:361`; `backup_key_custody` minted `:363`).

**What:** the KEK is minted **on the VPS** and delivered by `systemd-creds` sealed to the **host key**; the payload-encryption key for the nightly bucket copies rides the same store; the bucket holds ciphertext only. TN-12 rejects TPM2 precisely because "cloud VPS TPMs do not survive migration or rebuild" — but a host key does not survive a rebuild either. So on total host loss, the exact disaster the off-host backup exists for, the only readable copy of the key is gone and every encrypted versioned copy in the bucket is permanently unreadable. The drill cannot catch it: the monthly full restore runs on the same VPS into a scratch directory, and `backup_key_custody` is minted as a registry row with no rule behind it.

**Why it matters:** it silently converts the entire backup programme into theatre, and it converts NFR-06's "evidence retained forever" into "until the VPS dies". It also fails TN-12's own Prevents line, "a rebuild losing every credential".

**Fix:** rule in TN-12 that the **payload/backup key is generated at provisioning on the workstation**, escrowed in Windows Credential Manager under `qmx/*` plus one operator-held offline copy, and delivered to the VPS as a bootstrap credential — never VPS-minted; the VPS-minted KEK protects rotated *session* material only. Give `backup_key_custody` that text as its rule. Add a **host-loss restore rehearsal** to TN-13's drill set and to the TN-23 soak checklist: restore from the bucket onto a clean host holding nothing but the escrowed key, and let that rehearsal be what measures RTO.

### C3 — TN-7 makes `drain` self-clearing, contradicting AD-36 and its own Prevents
**Where:** TN-7 dead-wire bullet (`:250`): "`drain` and `close_all` become STANDING PROTECTION INTENTS — … satisfied only on a `reconciled` verdict"; against AD-36 ("each action kind declares a mandatory satisfaction predicate from a closed vocabulary — `scope-flat-at-reconciled-verdict | no-pending-orders-at-reconciled-verdict | never-auto` — and **`suspend_new` and `drain` are `never-auto` by rule**, clearing only by an operator `resume`").

**What:** AD-36 reserves reconciled-verdict satisfaction for `flatten` alone, and pins `suspend_new` and `drain` as `never-auto` — that pinning is what makes automated de-escalation *unreachable* rather than merely forbidden. TN-7 folds `drain` into the reconciled-verdict predicate, which means a drain issued under a dead wire clears itself the moment the wire comes back. TN-7's own Prevents line reads "an automatic de-escalation".

**Secondary half of the same defect:** AD-36 extends the standing-intent machinery to **every risk-non-increasing act** — naming `amend_protection` and CT-23's `close_full` / `tighten_protective_stop` — "without this the apparatus would cover the four control kinds and leave most actual protective acts to evaporate on the first transient refusal". TN-7 covers `drain` and `close_all` only, so TN-8's breakeven ratchet amend refused under an UNKNOWN block evaporates.

**Why it matters:** a child spine that silently loosens an inherited AD is the exact failure the reviewer gate exists to catch, and this one re-opens automated de-escalation of a protection control.

**Fix:** TN-7 states the predicate per kind verbatim from AD-36 — `suspend_new` and `drain` are `never-auto`, clearing only by an operator `resume`; `flatten`/`close_all` satisfies on `scope-flat-at-reconciled-verdict`; `drift | unknown | out-of-lookback` alarm and hold — and adds one sentence extending the standing-intent machinery to every risk-non-increasing act, `amend_protection` and the CT-23 protective closes included.

---

## HIGH

### H1 — No rule owns the money-accounting boundary or the virtual ledger
**Where:** absent. `ledger`, `book_capital`, `virtual position`, `netting` return **zero hits** in the spine; `sweep` and `re-seed` appear only as a drift component (`:295`) and an alert-allow-list row (`:388`); `rollover` appears only in the reconciliation cadence (`:297`) and the missed-rollover catch-up (TN-10 step 6). No module in the Structural Seed, no Capability-map row.

**What:** the node must run the accounting period: mint the binding's **virtual-ledger equity record** (AD-40's `book_capital` source, AD-29's record), fold fills into **virtual (Book) positions** — the unit of CT-29 exit records, the bench predicate and AD-33's whole-trade attribution, distinct from venue positions with "every risk record naming which of the two it references" — fix `r_unit_price` at period start on a declared cadence, derive `period_loss_budget` and `seat_r_ceiling`, and execute rollover, sweep and re-seed as journaled boundary acts. The spine assumes all of this exists (TN-10 reconstructs "boundary equity" and appends "the sweep"; TN-15 pushes an alert on `sweep`/`re-seed`; TN-6 fires "the budget and sizing ladder" as a door) without any rule minting it or any module holding it.

**Why it matters:** the level below cannot cut an epic for a capability no rule owns, and the pieces will be scattered into `orderpath/` and `reconcile/` by whichever story lands first. It is also the only home for AD-40's mandatory Book declaration of fill-to-virtual-position attribution under a `netting` account, whose absence is a bind-time policy rejection.

**Fix:** mint **TN-25 — the accounting boundary and the virtual ledger** binding a new `qmn/ledger` module: the period calendar identity; the virtual-ledger equity record writer; the virtual-position fold and the venue-position fold named apart with every risk record declaring which; rollover, sweep and re-seed as operator-signed journaled acts that never touch positions (TN-24 (f) then cites it); `r_unit_price` fixed at period start with the declared recompute cadence; the netting attribution declaration as a bind-time check. Add the row to the Capability map and the module to the Structural Seed.

### H2 — Four rules assume a neutral venue port that the code does not have, and the spine says so on its own page
**Where:** TN-21 (`:70` "a REPLAY VENUE ADAPTER behind the same neutral port"); TN-5 (`:202` "differ only in which clock and adapters the root binds"); TN-11/TN-22 ("adapter selection by `VenueId`", "the adapter is selected by `VenueId` at the root"); against the spine's own ports table, `ProbeTransport` row: "**The ONLY Protocol in `qmf-venue`**: there is no `VenuePort`/`OrderPort`/`VenueAdapter` seam, so the live client is composed AROUND the concrete typed values, never injected into them."

**What:** the spine records the brownfield truth in its interface list and then writes four rules that require the seam the interface list says is absent. AD-28's "one neutral port, four contracts" is a *contract* statement (CT-18/19/20/21 shapes), not an injectable Protocol at `ef9bb25`.

**Why it matters:** the replay epic and the venue epic will meet at a seam that nobody was told to build. Either the node mints the Protocol itself (and owns its versioning) or `qmf-venue` gets amended (a parent amendment, not a child's call) — the spine must pick, or two units pick differently.

**Fix:** in TN-11 mint the port explicitly as **node-owned**: name it (e.g. `qmn.venue.VenueClientPort`), define it over the CT-19/CT-20 shapes, state that the cTrader client and TN-21's replay adapter are its two V1 implementations, and state that `qmf-venue` is **not** amended for it. Record the alternative — realizing the seam in `qmf-venue` — as a candidate parent annotation under AD-28 in "Parent annotations and mints proposed by this sitting". Then TN-5/TN-21/TN-22 can say "the port" and mean something.

### H3 — AD-35's routing law arrives incomplete: the mandatory disposition field, the resolution inputs, and seat-state routing are all dropped
**Where:** TN-6 execution-target bullet (`:213`); TN-9 (`:274`); TN-7 trigger classes (`:246`); TN-8 bench (`:265`); against AD-35.

**What:** AD-35 rules three things the child spine does not carry. (1) `trigger_kind` is addable-never-redefined and **every kind declares its disposition, `routes-to-paper | blocks-paper`, as a mandatory field**, under the invariant that market-risk blocks (protection window, kill switch) block paper too while capital/authority blocks (kill-line stand-down, benched seat) route to paper. TN-7 mints four KSA trigger classes with no disposition; TN-8's kill-line stand-down declares none. (2) `execution_target` is resolved "from (Book mode, seat state, active-control set)"; TN-6 reduces it to "the live target or the paired demo target" with the inputs dropped. (3) Per-seat routing lives on the seat record, "which is precisely what lets a Book stay `LIVE` while one seat routes to the paired account" — TN-8 says the bench fold "benches a seat" and stops.

**Why it matters:** an epic reading TN-8 alone implements bench as "the seat stops trading", which destroys the decay evidence paper mode exists to keep flowing, and every new trigger kind the node mints lands undetermined between routing and blocking.

**Fix:** restate the three resolution inputs in TN-6; require a `disposition` on every node-minted trigger kind in TN-7 and TN-8 (with the KSA classes and the kill-line stand-down classified in the text); add one sentence to TN-9: a benched seat and a kill-line stand-down route to the paired target while the Book stays LIVE, and a protection window or the kill switch blocks paper too.

### H4 — The crash-loop fold is blind to exactly the crashes that loop
**Where:** TN-4 (`:190` "the node keeps its own crash-loop fold over boot-epoch records … systemd's `StartLimitBurst`/`StartLimitIntervalSec` are set strictly above `(K, T)`"); TN-2 (`:133` the boot-epoch record carries `composition_fp`, minted in act 3).

**What:** the fold counts **boot-epoch records**, and a boot-epoch record can only exist after act 3 (fingerprint) because `composition_fp` is stamped on it. A crash-loop in act 1 (preflight: store unreachable, `chronyc waitsync` never returns, disk full, credential absent) therefore produces no record to fold, the node never enters stand-down, and systemd's own limiter has been deliberately set **above** `(K, T)` so it will not stop the loop either. TN-4's Prevents line — "a restart loop churning the broker" — fails at the stage most likely to loop.

**Why it matters:** unattended, this is a machine that restarts forever and alerts on nothing (stand-down is on the allow-list; a preflight crash-loop is not).

**Fix:** TN-2 mints a **boot-attempt record at process start, before preflight**, carrying the boot epoch id and the stage reached; `composition_fp` is stamped onto it at act 3 as an amendment. TN-4's fold counts boot **attempts** by stage, so a preflight loop trips `(K, T)` and boots into stand-down with the doors serving.

### H5 — TN-3's workstation credential boundary contradicts TN-12's wizard
**Where:** TN-3 (`:143` "NO live venue credential ever") against TN-12 (`:345-346`: Windows Credential Manager `qmx/*` is the provisioning source; the wizard "reads each `qmx/*` entry" — client id and secret, the initial access and refresh tokens, the cTID account ids — and streams them to the VPS).

**What:** the laptop is where live broker bootstrap credentials are entered and held before provisioning. TN-3 states a boundary that TN-12 must cross to function. TN-3's supporting clause is narrower than its headline ("a workstation tool never refreshes a credential the VPS session owns") and is correct; the headline is not.

**Why it matters:** it is a trust-boundary rule, so it will be implemented as a check. Built to TN-3's headline, that check refuses the wizard TN-12 requires; built to TN-12, TN-3's boundary is unenforced and unaudited.

**Fix:** restate the TN-3 boundary as: the workstation holds **provisioning/bootstrap material only, never rotated live session material**; the VPS session is the only refresher and the only holder of live session state. Have TN-12 name the hygiene that enforces it — the laptop's refresh-token copy is dead the moment the VPS refreshes (already stated), plus an explicit instruction that the wizard reports which `qmx/*` entries are now stale.

### H6 — Six ways the node silently stops trading, none on the push tier
**Where:** TN-15 alerts (`:388-389`); against PRD §3's unattended-operation doctrine (`prd.md:119-127`, inherited at `:90`).

**What:** the allow-list is **closed** and "everything else is console evidence". These stop entries or stop persistence on an unattended node and none is on it: (a) a clock-band `no-new-entry` — and the band alert is explicitly **soak-only**, switched off at go-live (`:389`); (b) an unexplained live drift entry stand-down setting `operator_review` (TN-10); (c) a failed calendar refresh, which blocks entries fail-closed with "no live skip button" (TN-13); (d) a degraded or dead canonical sensing feed (`feed_state`, TN-19) under the no-silent-failover rule; (e) a failed nightly backup or restore drill — TN-13 says failures "alarm", but "alarm" is only defined as an ERROR log level in TN-15; (f) disk headroom exhaustion, which becomes an unpersistable-write block on the command stream.

**Why it matters:** the doctrine is unattended operation. A node that has quietly stopped taking entries for three days, or that cannot write evidence, is indistinguishable from a quiet market on the console-only tier.

**Fix:** add one class to the allow-list — *"the node has stopped accepting entries, or cannot persist evidence, for a reason that is not a KSA escalation"* — enumerating the six members above; delete the go-live switch-off for the clock-band alert (keep the first-connection-check alert soak-only); and state that TN-13's "alarming" means this push class, not merely ERROR.

### H7 — No failure contract for admitted bot code running in-process
**Where:** TN-19 (`:46` seats driven per evaluation instant by `mint_intents`); TN-4 (one domain thread per slice); Deferred ("hardened OS-level confinement … V1 does not wait on it"). `callback`, `deadline`, `raises`, `hang`, `quarantine` produce no rule anywhere in the spine.

**What:** a promoted seat's Python runs **inside the trading process, on the loop's only domain thread**, with confinement deferred. Nothing states what happens when a callback raises, blocks, spins, or allocates without bound. `CancelToken` / `LimitProbe` appear in the ports table ("cooperative abort at slice boundaries", "long-lived RSS watch") with no rule behind them, and E15-F03 already records that there is no OS-enforced memory cap.

**Why it matters:** one badly-behaved seat stalls every command stream on the node; the systemd watchdog then converts the stall into a restart, and (with H4) into a restart loop. This is a live-runtime dimension the level below cannot invent consistently.

**Fix:** TN-19 declares the seat-callback contract: a per-callback **deadline** (node value, do-not-default, UI-editable) enforced by the slice driver through the `CancelToken`; a breach or a raised exception is a typed refusal plus automatic **seat quarantine**, journaled as a seat-state transition, never a stream failure; memory observed through `LimitProbe` with the same disposition. State the accepted V1 consequence in one line: admitted code runs in-process because it passed conformance, and the deadline plus quarantine — not the OS — carry the line until confinement ships.

### H8 — The powers door authenticates nobody, so the human-only live-money gate is asserted rather than enforced
**Where:** TN-17 (`:24` "every powers call is … journaled as a control action, promotion or transition carrying the human signer identity"; `:25` "Remote access is an SSH tunnel only"); TN-20 (`:58` "the signer identity must be a human principal and an agent signer is refused — this proves QMX-F045").

**What:** the powers channel is an unauthenticated localhost HTTP endpoint. Nothing in the spine says how the signer identity is **established** rather than supplied — any process on the VPS, an agent with a shell included, can POST a promotion carrying `signer = <a human's name>`. TN-20 leans on this refusal to prove QMX-F045, which the QA-debt roster records as the unanswered question "can an agent mint a card `authorize_live_promotion` accepts?" — the spine assigns the proof to the node without giving the node a mechanism.

**Why it matters:** L17 ("only a human may promote into the live zone") and TN-20's Prevents ("an agent minting a live promotion") both rest on it, and TN-17's own Prevents line reads "an agent reaching live money". An assertion field is not a gate.

**Fix:** in TN-17, bind the signer to the transport: serve the powers channel over a unix domain socket with `SO_PEERCRED` (or require a per-operator signing key held off-node and verified server-side), record the peer credential alongside the claimed signer on every powers journal record, and refuse any powers call whose peer credential is not the declared operator principal. State that the evidence read channel keeps its localhost HTTP binding unchanged.

---

## MEDIUM

### M1 — Blanks block live only, but the soak checklist needs at least eight of them filled
**Where:** TN-18 (`:429` "a blank that gates live money blocks `role = live` bindings only — paper runs"); TN-23 soak checklist (`:94`); Deferred row 1 ("a **pre-live** operator ratification").
**What:** the soak must prove "a KSA escalation fires the matrix", "a simulated clock-band breach produces `suspend_new`", "a kill-line breach on the paper Book auto-flattens", "a news window and a dead zone block entries". Every one of those reads a blank do-not-default value (`ksa_effect_matrix`, the clock bands, `kill_line_capital_floor`, the window widths). Blanks blocking live only means the soak runs with those mechanisms inert and the checklist cannot pass.
**Fix:** state in TN-18 that any value the TN-23 checklist exercises is **soak-blocking, not merely live-blocking** — ruled provisionally before the soak as a recorded config version — and correct the Deferred row from "pre-live" to "pre-soak".

### M2 — Which machine pushes the bucket copy, and of which rooms
**Where:** TN-3 flows (`:146` "ONE-WAY node to workstation to bucket") and its diagram edge `ARC -- nightly encrypted versioned copies --> BUCKET`, against TN-13 (`qmn-backup.timer` nightly, "local staging plus `rclone`") and TN-16 (the timer unit lives on the VPS).
**What:** two incompatible topologies for the off-host copy. If the workstation pushes, RPO 24 h fails whenever the laptop is off, and the bucket credential lives on the workstation; if the VPS pushes, TN-3's flow sentence and diagram are wrong. The **room scope** of the backup set (which rooms, which worlds) is also never stated.
**Fix:** rule the VPS as the pusher, redraw the TN-3 edge as `EVI --> BUCKET`, keep the workstation pull for the working archive, and name the backed-up room set in TN-13.

### M3 — Compound commands and scope resolution are unowned
**Where:** absent (`compound`, `netting` = zero hits); AD-27 (compound command: children carry parent `fp1` + declared ordinal, ordered by child content fingerprint ascending, parent outcome = the meet) and AD-36 (scope resolved "through a pinned versioned CT-30 resolution table, never implementer judgment"; where the venue position model makes a narrower scope indistinguishable from a wider one, **the action refuses**).
**What:** a kill-line flatten at binding scope and a `close_all` fan out to N submissions. The node owns the sequencer, so child identity derivation, the ordering rule and the meet outcome are node work — and none is named.
**Fix:** one bullet in TN-6 (child identity + ordering + meet) and one in TN-8 (scope resolved through the CT-30 table against the CT-18 position model; an indistinguishable narrower scope refuses, never widens).

### M4 — TN-10's rung-baseline readiness gate is circular on first boot
**Where:** TN-10 step 8 ("a live-path rung baseline on this deployment tuple") against TN-23 ("the first Linux baseline, recorded on the VPS tuple **during the soak**").
**What:** as a boot gate for all bindings, no first boot can pass it, because only a running node can mint it.
**Fix:** scope the gate to `role = live` bindings (which is what CT-28's bind-time check requires anyway) and state that the benchmark harness, not the trading loop, mints the baseline.

### M5 — Maximum slice latency has no consequence; the accumulator has no bound
**Where:** TN-5 (`:200` "a declared maximum slice latency (node value)"; the push-to-pull accumulator).
**What:** a declared maximum with no stated effect on breach is not enforceable — one unit will emit a metric, another a typed refusal. The accumulator sits between an async edge and a synchronous consumer with no bound, no backpressure and no coalescing rule; under a tick storm it grows without limit (and E15-F03 records there is no hard memory cap).
**Fix:** declare the breach effect (a journaled `data quality` event and a band, never a silent skip) and the accumulator's bound with a typed overflow rule that never drops an execution or system observation — market-data coalescing only, journaled.

### M6 — The shutdown contract is unenforceable without declared timeouts
**Where:** TN-4 shutdown (`:191`); TN-16 hardening list (`:7` of the unit-file set: `Restart`, `RestartSec`, `StartLimit*` named; `TimeoutStopSec` and the `WatchdogSec` value absent).
**What:** the flush honours block-on-unpersistable. systemd's default `TimeoutStopSec=90s` then SIGKILLs the node mid-flush — precisely "a shutdown that loses an intent", TN-4's own Prevents.
**Fix:** name `TimeoutStopSec` (≥ the declared drain budget) and the `WatchdogSec` value in TN-16's hardening set, and state in TN-4 what the node does when the flush cannot complete: stay up, alarm on the H6 class, refuse to exit clean.

### M7 — `clientMsgId` mapping leaves an either/or where AD-27 requires a choice
**Where:** TN-6 (`:214` "mapped into `clientMsgId` at 100 characters or fewer, injectively or through a durable command-id-binding record").
**What:** AD-27 requires the mapping to be "injective **and total** over the digest space", and where the field cannot carry one, the durable binding record must persist **before submission** and is named reconciliation evidence. A truncation-based mapping is not provably injective, and only the binding record survives a restart mid-UNKNOWN.
**Fix:** pick the binding record as V1's path (100 chars cannot be a total injection over an `fp1` digest space plus stream qualification), and state the persist-before-submit ordering.

### M8 — The provisioning wizard's host is not a declared deployment target
**Where:** TN-12 (`qmn secrets provision` "runs on the laptop", imports `keyring`/`WinVaultKeyring`); TN-1 ("ONE canonical checkout on the VPS"); TN-16 ("the Windows view remains gated for the workstation products").
**What:** the wizard is part of the `qmn` distribution and runs on Windows, so either `qmn` is installable on the workstation — in which case the tier-1 Windows type gate must cover it and NFR-10's one-checkout claim needs qualifying — or the wizard needs its own delivery. Unstated.
**Fix:** one line in TN-16: `qmn` is installable on the workstation for the wizard and the Python API only; the Windows lane type-gates it; the VPS checkout stays the only *runtime* installation.

### M9 — One environment, and the fact is never decided or deferred
**Where:** TN-16 (`qmn deploy switch` = "preflight, backup-first, `uv sync --frozen`, a dry-run boot in check mode, then `systemctl restart qmn`"); Deferred (no staging row).
**What:** an upgrade is validated by CI plus a check-mode boot **on the production host that holds the live credentials**, with rollback as the only compensating control. That may well be the right call for a one-operator system, but a silent dimension is a finding: the level below cannot tell whether a staging host is expected.
**Fix:** state the one-environment decision explicitly with its compensating controls (CI clean-install boot, check-mode dry run, a replay diff of a recorded day, `deploy switch` rollback), or add a Deferred row for a staging host.

### M10 — Capacity is a silent dimension
**Where:** TN-13 ("evidence itself is retained forever"); TN-3 (the evidence tier is "a second directory tree on the same VPS"); TN-15 (`disk headroom` exists as a metric only).
**What:** the node records live ticks, bars and depth continuously into rooms, syncs hot rooms to an evidence tier **on the same disk** (so verify-before-purge frees nothing at the machine level), and retains evidence forever — with no sizing model, no measured growth figure, no roll-off or off-host-then-purge rule, and no disk-full failure mode beyond the generic unpersistable block that stops the command stream. VPS sizing (disk, RAM, CPU class) is named only as a benchmark tuple.
**Fix:** add a capacity paragraph to TN-13 or TN-16: a declared VPS disk budget; bytes-per-day measured and recorded at the soak; the purge rule (hot rooms purge only after a verified off-host copy exists); and a headroom threshold that mints `no-new-entry` before the disk-full block arrives, on the H6 alert class.

### M11 — The spine cites A1-A30 and Q1-Q4 without defining either
**Where:** frontmatter `provenance`; the `[ASSUMPTION Ax]` lines under every TN; four "operator Qn" citations. No assumption register and no open-questions section exists in the spine — both live only in `.memlog.md`.
**What:** the spine is the artifact the documentation factory and epics-and-stories consume. A reader hitting "[ASSUMPTION A16 …]" gets a label with no register, and "operator Q1" names a question whose text and options are nowhere in the file.
**Fix:** add an **Open questions** section carrying Q1-Q4 verbatim with their options and recommendations, and either an A1-A30 register table or a one-line pointer naming `.memlog.md` as the register's home.

### M12 — Governor CPU/memory budgets: named blank, owned by nobody
**Where:** TN-18 do-not-default list ("the governor budgets"); parts-bin §3 closing paragraph (`qmb/src/qmb/orchestrator/governor.py:2-7`); the "New registry variables" table has no row for them.
**What:** the node spawns isolated work per B-5 (conformance Layer-2 runs, benchmark runs). The budgets that bound those spawns are declared blank and then dropped: no registry row, no owning TN.
**Fix:** add the rows to the mint table with TN-19/TN-23 as owner scope.

### M13 — Stack currency provenance is uneven, and the one live-pin risk is dropped
**Where:** the Stack table. Four rows carry "verified 2026-08-28" (`prometheus_client`, `cryptography`, `rclone`, `keyring`); `click ==8.4.2`, `protobuf ==7.36.0`, proto release tag 91, Ubuntu 24.04, systemd 255.4 and chrony carry no date.
**What:** the memlog records that **click 8.5.0 exists (2026-08-26)** and that the node deliberately reuses QMB's `==8.4.2` because a bump is a contract-versioning event under DEC-0168. The spine's row says only "the same pin as QMB", so a downstream author who checks currency will read the pin as stale and helpfully bump it. `chrony 4.7/4.8 current` is a range, not a pin, on a component that gates live trading.
**Fix:** carry the deliberate-pin note into the click row; mark the inherited rows "inherited at `ef9bb25`, not re-verified this sitting"; state the chrony minimum version rather than a range.

---

## LOW

### L1 — Control-effect vocabulary drift
TN-7 writes CT-30's effects as "`suspend_new | drain | close_all`" (`:248`). AD-36's CT-30 kinds are `suspend_new | drain | flatten | resume`; `close_all` is an AD-27 **command** kind. Use `flatten` for the control effect and `close_all` for the command it executes; the memlog's own "flatten/close_all" shows the ambiguity was live at authoring.

### L2 — The `world` vocabulary is never enumerated
`world = live` (TN-9, TN-13), `world = replay` (TN-21), `provenance = sandbox` (TN-3), and the adjudication's "`world = simulated` unusable" all appear without one enumeration. Add the closed list to the Consistency Conventions naming row.

### L3 — TN-8's dead-zone "posture" carries no number and no force
"this sitting's posture is the wider band around the daily rollover" (`:267`) drops the memlog's ~3 h evidence figure (A8) while the variable is blank do-not-default anyway. Either carry the evidence figure with its unit-kind or delete the sentence; as written it reads as guidance an implementer might treat as a default.

### L4 — "Nothing QMX is published to any index" has no enforcement
TN-1 makes it a Prevents ("a published artifact nobody ratified") with no mechanism — no private classifier, no `publish` job absence check, no CI gate. Name one (a tier-1 check that the workspace members declare no publishable target).

### L5 — TN-11's "19 unfilled CT-18 fields" is a count without a roster
The number is auditable only against the inventory. Since AD-28's risk-gate additions (settlement currency, margin model and stop-out level, value-factor surface, amend atomicity, reconciliation lookback declaration) are all verify-or-refuse and several gate bind time, name them as the roster's load-bearing rows rather than a count.

---

## Rubric verdict by question

| Rubric question | Verdict |
| --- | --- |
| 1. Fixes the real divergence points for epics/stories? | Mostly. 24 rules cover the runtime, the order path, protections, paper, data, time, secrets, ops, doors, config, seats, promotion, replay, roster, QA and position safety. **One whole capability is unowned** (H1 accounting/virtual ledger); two more are half-owned (M3 compound commands, H7 seat containment). |
| 2. Every Rule enforceable; every Prevents actually prevented? | Four Prevents fail against their own Rule: TN-4 "a restart loop churning the broker" (H4), TN-4 "a shutdown that loses an intent" (M6), TN-7 "an automatic de-escalation" (C3), TN-1 "a published artifact nobody ratified" (L4). Two rules are declarative with no consequence (M5). |
| 3. Could anything under Deferred let two units diverge? | Yes, two rows. "KSA matrix values — a pre-live operator ratification" collides with the soak checklist (M1). "Hardened OS confinement — V1 does not wait on it" leaves in-process seat failure undefined (H7). The other twelve rows land safely on a named seam. |
| 4. Named tech verified-current with dates? | Partially — four rows dated 2026-08-28 with primary-source verification recorded in the memlog; six rows undated, and the one active currency risk (click 8.5.0, deliberate pin) is dropped from the spine (M13). |
| 5. Ratifies rather than contradicts `integration@ef9bb25`? | Strongly, with one exception: all 28 parts-bin seams have a home, and every red flag is answered by a rule — but four rules assume a venue port the inventory says does not exist, and the spine's own ports table states the contradiction (H2). |
| 6. Covers the operator's required coverage? | Yes for the memlog scope line and the Capability map, with H1 as the gap (Book/BMS runtime accounting has a map row but no rule). |
| 7. Does any TN weaken an inherited AD? | One does (C3, AD-36's `never-auto`). Two under-carry (H3, AD-35's disposition/routing law; M3, AD-27 compound + AD-36 scope table). AD-27's uncertainty law, AD-28's adapter contract and AD-40's freeze/re-base/numeraire rules are carried faithfully — with C1 as the missing wiring between AD-40's `book_capital` and AD-36's kill line. |
| 8. Every altitude-owned dimension decided, deferred or open? | Deployment ✓, infra/provider ✓, operations ✓, upgrade/rollback ✓, secrets ✓ (with C2), monitoring ✓, alerting ✗ (H6), backup/restore ✓ (with C2, M2), time ✓, **capacity ✗ (M10)**, **environments ✗ (M9)**, **door authentication ✗ (H8)**. |

## Closing order of work

C1, C2, C3 and H3 are text amendments to existing rules and can be made at desk. H1 mints one new rule (TN-25) and one module. H2 and H8 each pick a mechanism the spine currently leaves open — both are node-owned decisions, neither needs the operator. H4, H5, H6 and H7 are one-paragraph additions to TN-2/TN-4, TN-3/TN-12, TN-15 and TN-19 respectively. None of the 28 findings needs a parent amendment; H2 proposes one as an option only. Nothing here overturns an A1-A30 assumption or reopens an operator question.
