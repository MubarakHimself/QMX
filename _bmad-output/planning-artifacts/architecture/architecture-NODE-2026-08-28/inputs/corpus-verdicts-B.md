# Corpus verdicts — Adjudicator B (QB1–QB15)

**Sitting:** trading-node architecture, 2026-08-28. **Adjudicator:** Opus corpus adjudicator B.
**Rule obeyed:** corpus first. Every question answered from the corpus where the corpus answers it;
only corpus-silent residue is written up as an operator question, in plain words.

**Authority order applied:** current operator rulings (`tracker/trading-node-notes.md`, the sitting
memlog, PRD operator-ratified lines) > `docs/` ratified corpus (constitution, DEC ledger, contracts,
ADRs, scenarios, lenses) > architecture spines (AD/B/QL) > PRD `[MINED]` doctrine (direction; binds
nothing until ratified here) > GitBook primer baseline > `archive/recovery` K-rules (evidence only).
QMX-discussion is barred for risk/sizing (L37, DEC-0156).

**Source-set note.** The task named `inputs/dig-spines-and-research.md`; that file does not exist on
disk. The `inputs/` directory holds five `dig-*` dossiers and four `code-*` dossiers. All nine were
read, plus direct verification against the repo for every decisive quote below.

**Vocabulary:** "the trading node" — one product, two modes `paper | live`. Banned words appear only
inside quotations of a cited source.

---

## QB1 — Time-zone / calendar edge cases at the live boundary

**VERDICT: PARTIAL.**

### Settled (with cites)

**The three-calendars ruling is DEC-0106 (AD-8), and it is a naming law, not a preference.**

> "**Three-calendar naming rule.** Never write bare "calendar". Three distinct named concepts exist:
> the **market-hours calendar** (session schedule + accounting rollover, e.g.
> `COMP-QMF-CALENDAR-FOREX`), the **day-boundary calendar** (an account-scoped accounting-boundary
> rule), and the **news calendar** (`COMP-CALENDAR-FEED`, the external event feed). They are never
> substituted for one another. See DEC-0106 (AD-8)."
> — `docs/AGENTS.md:48`

Restated contractually at `docs/contracts/ct-02-time-calendar.yaml:40-42`, including that a
market-hours calendar carries **two separately-named facts, each with its own zone** — an accounting
rollover and a session schedule — and that "session and trading-day length are data no consumer may
assume constant."

**Calendar identity in `TradingDate`** — ratified and already implemented:

> "Calendar identity is the rule set (for example forex-17NY v3), separate from its binding to venues
> or accounts; only the rule set plus tzdata version enter fingerprints, so a venue change that does
> not change the rule set does not change derived-artifact identity (DEC-0106, DEC-0108)."
> — `docs/contracts/ct-02-time-calendar.yaml:39`

In code: `CalendarIdentity(forex-17NY / v1 / verified tzdata_version)` rides **in-band on every
trading date** (`extensions/qmf-calendar-forex/src/qmf/calendar_forex/_provider.py:153`,
`_tzdb.py:100`); splits and the 12-month seal pin exactly one calendar identity and refuse a row
carrying a different one — never a silent rescale (`packages/qmf-data/src/qmf/data/splits.py:19-26`,
`seal.py:28`).

**tz-database version pinning** — ratified and enforced at import:

> "qmf-core embeds no market-hours calendar rule set; calendars ship as separate versioned extensions
> that force the timezone path to their pinned tzdata package and verify at import that the resolved
> tzdb version equals the pin, refusing `unavailable dependency` otherwise so a fingerprint never
> attests a tzdb that was not used (DEC-0106, DEC-0031, DEC-0109)."
> — `docs/contracts/ct-02-time-calendar.yaml:46`

Current pin: `tzdata==2025.2` → IANA tzdb `2025b`, forced via `TZPATH` + `reset_tzpath`, verified by
`qmf.core.verify_tzdb_pin`; a pin change is at least a minor SemVer bump
(`extensions/qmf-calendar-forex/src/qmf/calendar_forex/_tzdb.py:20-27, 83-101`, `__init__.py:90-92`).

**D1 boundary detection — empirical, per-broker, never hardcoded.** Verbatim:

> "The 17:00-New-York venue daily boundary is never hardcoded: the adapter measures the actual
> boundary per broker at first connection and re-verifies it with a continuous monitor, storing the
> result as per-broker configuration; the venue's own broker-supplied non-UTC schedule and holiday
> axes are ratified venue facts stored verbatim and never assumed to align to QMF's forex-17NY
> calendar (DEC-0135, DEC-0141)."
> — `docs/contracts/ct-02-time-calendar.yaml:45`

And once measured it **mints its own identity**, so venue-native bars get a legal anchor:

> "A measured, verified venue daily-bar boundary is minted as a venue-scoped market-hours calendar
> identity … until it is measured and verified, venue-native bars are ungoverned observations, never
> assumed aligned to QMF's forex-17NY calendar (DEC-0141, DEC-0138)."
> — `docs/contracts/ct-02-time-calendar.yaml:44`

The verification is a named contract part with a stated refusal
(`docs/lenses/ops/runbook.md:65-71`, "Daily-boundary measurement" row). `registry:venue_daily_bar_boundary`
is `measured-per-broker` with no value (`docs/registry/variables.yaml:394`).

**Two clocks that must never be merged.** QMF's accounting rollover is 17:00 America/New_York
(`registry:forex_rollover`; `ROLLOVER_ZONE`/`ROLLOVER_HOUR` at `_provider.py:38-40`), and it is
**independent** of the venue's measured D1 boundary. Two calendars, deliberately not aligned.

**DST transitions** are handled by elimination, not by logic:

> "DST invisible BECAUSE no local time is ever stored/keyed/compared — state as enforced invariant.
> Pinned tzdata version recorded as input to every session-calendar resolution and backtest."
> — `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/time-audit-devops.md:22`

Reinforced by the ratified runbook obligation "Linux RTC in UTC, system tz UTC, `TZ=UTC` … No local
time is ever stored, keyed, or compared" (`docs/lenses/ops/runbook.md:113` row).

**Broker timezone axes.** Ratified as venue facts stored verbatim (ct-02:45 above), with an explicit
prohibition: "A session calendar may never be a fixed UTC offset from 'broker server time'
(cTrader-class servers run EET/EEST; feeds GAP-0037)" (`time-audit-devops.md:23`).

**Session handover.** Ratified as one of exactly three control-window kinds:
`news | daily_dead_zone | session_handover_buffer`, each calendar-derived and absent for 24/7 markets;
`session_handover_buffer` carries a **mandatory anchor** `pre-close | post-open | both`; the window is
carried as **two instants, never an offset**; widths and anchors are configurable UI-editable with
**no spine value** (`docs/contracts/ct-31-control-window.yaml:17-19, 22, 43-44`;
`docs/registry/variables.yaml:680, 691`). Effect: blocks new entries on in-scope instruments, live and
paper alike; never an exit, protection amendment, protection action, or observation (ct-31:20, 45).

**Weekend gaps** are modelled by the forex market-hours calendar as Friday 17:00 NY → Sunday 17:00 NY
plus a pinned holiday set of Jan 1 and Dec 25 only; swap-Wednesday is deliberately not modelled
(V1 accounts are swap-free) (`_provider.py:155-180`, `_holidays.py:1-20`; ct-02:43).

### Not settled

1. **Broker weekend / maintenance windows.** `tracker/trading-node-notes.md:10` records as venue fact
   that "weekend maintenance windows exist," but no control-window kind covers a *venue maintenance*
   window, and the forex weekend gap (Fri 17:00 NY → Sun 17:00 NY) is a market-hours fact, not a
   per-broker maintenance schedule. Nothing rules which of the three ratified window kinds a broker
   maintenance window is, or whether it is a fourth kind.
2. **Re-verification cadence for the continuous D1-boundary monitor** — the monitor is ratified, its
   period is not (no registry variable exists).
3. **Leap-second posture.** The time audit says "State posture (smear vs step), one policy across all
   machines" (`time-audit-devops.md:38`) — the posture itself is unstated anywhere.
4. **Prop-firm day-boundary calendar** — the seam is ratified, no prop firm is modelled in V1
   (`docs/lenses/ops/runbook.md:116` row). Not node-blocking.
5. **`daily_dead_zone_width` carries disagreeing evidence** — a one-hour table row vs Flow 9's ~3-hour
   prose, recorded unmerged (`docs/registry/variables.yaml:669`; ct-31:52).

### What the spine should bind

- Three calendar kinds named apart, never a bare "calendar"; the market-hours calendar's rollover and
  session schedule as two separately-zoned facts.
- Calendar identity in-band on every `TradingDate`; only rule set + tzdata version enter fingerprints.
- One pinned tzdata version verified at import, refusing `unavailable dependency` on mismatch; a pin
  change is a versioned event.
- The venue D1 boundary measured per broker at first connection, minted as a venue-scoped market-hours
  calendar identity, re-verified by a continuous monitor, stored as per-broker configuration; venue
  bars are ungoverned until it passes.
- Broker schedule/holiday axes stored verbatim; never a fixed offset from "broker server time".
- No local time ever stored, keyed, or compared; RTC/system tz/`TZ` all UTC — DST becomes invisible by
  construction.
- Session handover as a CT-31 window with a mandatory anchor; widths configurable, no spine value.

### Operator question (residue 1)

**Q-QB1a.** Brokers close the platform for a few hours over the weekend for maintenance, and we need a
rule for what the node does in that window — for example, IC Markets' cTrader servers going down
Saturday night. **Recommended: treat it as one of the "quiet band" windows we already have (a
daily-dead-zone window), discovered by watching the broker rather than typed in by hand** — because it
then reuses machinery that is already ratified and already blocks only new entries, never exits.
Alternatives: (b) invent a new fourth window kind called "venue maintenance"; (c) treat it as part of
the weekend gap in the market-hours calendar. **Cheap-veto ASSUMPTION** — proceeding on (a) creates no
work that would need unwinding if you later prefer (b).

---

## QB2 — Clock drift between the VPS and the broker

**VERDICT: PARTIAL.**

### Settled

**There is no server clock on the Open API; receive-time stamping is mandatory.** Ratified venue fact
(`docs/components/ctrader.md:57-67`; `tracker/trading-node-notes.md:10`), and `server_clock_availability`
is a declared CT-18 capability field (`docs/contracts/ct-18-venue-capabilities.yaml:39-64`).

**How drift is measured — two independent measurements, both ratified in shape:**

1. **Machine-vs-truth (OS clock).** "The VPS OS clock runs chrony with ≥4 sources (iburst, makestep
   boot-only); it is the sole stamper of QMF-owned event times. A travelling Windows laptop is declared
   unfit to stamp authoritative evidence." (`docs/lenses/ops/runbook.md:107-116`, first row.) Exported
   signals are named: "chrony offset, stratum, and sync-age; per-venue clock skew; the clock step
   counter — over a push alert path with no on-call rotation"
   (`docs/lenses/observability/metrics-and-alerts.md:20`).
2. **Node-vs-broker (skew, not drift).**
   > "Rolling per-venue offset series (local_receive − source) min/median/p99; windowed minimum = skew
   > estimate. Alarms push to operator; signal cannot distinguish broker clock error from network-path
   > change — no auto-correction."
   > — `time-audit-devops.md:35`

   And a hard framing rule: "Cross-machine 'latency' is an offset-contaminated estimate, never a
   measured duration" (`time-audit-devops.md:15`). Every foreign event stores **three** times:
   source-as-received (verbatim, with declared zone/offset/resolution), local receive wall, local
   receive monotonic (`time-audit-devops.md:34`).

**The band *shape* is ratified corpus. The numbers are not.** The ratified runbook row reads:

> "Drift bands with typed refusals | Numeric drift bands sized to ~1s decisions (ok / warn /
> no-new-entry / halt); exceeding a band is a typed refusal plus a journal record plus a node state
> change, never silent. Clock health is a per-decision-cycle precondition. | Node/ops sitting"
> — `docs/lenses/ops/runbook.md` (Node/ops time-audit obligations table)

The four names are ratified; the four numbers were deliberately dropped when the audit was absorbed
into `docs/`. The quadruple survives only one layer down, in the architecture spine artifact:

> "Numeric drift bands with actions (ok ≤10ms / warn ≥25ms / no-new-entry ≥100ms / halt ≥250ms —
> sized to ~1s decisions); exceeding a band = typed refusal + journal record + node state change,
> never silent."
> — `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/time-audit-devops.md:9`

**Grade: RECONFIRM. Not ratified.** Three reasons: (i) the docs-corpus row that supersedes it carries
no numbers; (ii) `docs/registry/variables.yaml` contains **no drift-band variable at all** — the node
sitting must mint them; (iii) L38/DEC-0157: "recorded numbers attached to configurable variables are
evidence, never ratified constants" (`docs/constitution.md:92`).

**Also ratified, and it binds the node before the bands do:** no-trade-before-sync (`chronyc waitsync`
after `time-sync.target`); slew-only while live, a step only with the node stopped and observable via a
wall-vs-monotonic divergence detector; a gap record for every unsynchronized/stepped/paused window
including a VPS live-migration or pause (`docs/lenses/ops/runbook.md`, same table).

**What stand-down on drift looks like.** L39 decides the shape:

> "The exit-preservation invariant: no control action, of any authority, at any scope, may block a
> risk-reducing act or the recording of evidence; the blocking half of any control is entries only,
> and no control kind whose effect is a blanket command-pipe block may be minted."
> — `docs/constitution.md:94` (DEC-0150)

So: `no-new-entry` maps onto the ratified `suspend_new` action kind — "no new entries; open/resting
untouched" (`docs/contracts/ct-30-control-action.yaml:18, 39`). `halt` maps onto the fail-closed
stand-down that the PRD's mined doctrine already describes as an **alive** state: "sequencers
refuse-and-journal, adapter connections quiesce and drain, and the operator-powers surface keeps
serving — resurrection stays reachable" (`prd.md:418-422`). `drain` never force-closes anything
(ct-30:18). Exits, protection amendments, protection actions and evidence recording continue through
every band. Nothing about clock drift may ever produce a blanket command-pipe block.

### Not settled

The four numbers, and the registry variables to hold them (none exist).

### What the spine should bind

- Two measurements, named apart: machine-vs-truth (chrony offset/stratum/sync-age/step counter) and
  node-vs-broker skew (rolling per-venue `local_receive − source`, windowed minimum, never
  auto-corrected, never called "latency").
- Four band names `ok | warn | no-new-entry | halt`, evaluated as a **per-decision-cycle
  precondition**, not a startup check; exceeding a band = typed refusal + journal record + node state
  change, never silent.
- Band effects strictly entry-side: `no-new-entry` → `suspend_new`; `halt` → fail-closed stand-down
  (alive, doors reachable, drains, never blocks an exit or an evidence write) per L39.
- Four new registry variables, `configurable: true` (UI-editable), values carried as recorded
  evidence, not spine constants.
- "Unsynchronized" (no NTP source for N minutes) as a **distinct state** from "measured drift".

### Operator question (residue 2)

**Q-QB2a.** The node has to decide how far its clock may drift from real time before it stops taking
new trades — say the VPS clock slips 120 ms behind and a bot wants to enter EURUSD. **Recommended:
start with warn at 25 ms, stop new entries at 100 ms, and stand the node down at 250 ms, all four
numbers editable from the settings screen later** — because these are the numbers our own time audit
arrived at for roughly one-second decisions, and nothing is lost by starting there and adjusting once
we see the real VPS. Alternatives: (b) start stricter (stop entries at 50 ms) and loosen if it proves
noisy; (c) leave the numbers blank until the paper soak measures actual drift, and block live money
until then. **Cheap-veto ASSUMPTION** — the numbers are UI-editable configurables by law, so changing
them later unwinds nothing.

---

## QB3 — Partial fills, requotes, disconnect-mid-order, duplicate fills, position mismatch on restart

**VERDICT: PARTIAL.** The uncertainty law is comprehensively ratified; three accounting questions
underneath it are genuinely open.

### Settled

**The four-outcome law is constitutional (L35):**

> "Every venue submission resolves to accepted-by-venue, rejected-by-venue, denied-locally, or
> UNKNOWN; a timeout is never a rejection, an UNKNOWN blocks its command stream until an explicit
> recorded resolution, and no QMF component retries, assumes an outcome, or invents terminal state."
> — `docs/constitution.md:86` (DEC-0137)

**Disconnect mid-order.** On lost transport the adapter mints an explicit UNKNOWN observation carrying
trigger (`timeout | transport-error | disconnect`), monotonic elapsed, wall receive instant and
submission deadline, recorded and journaled **before any state evaluation**
(`docs/scenarios/SCN-0005-uncertain-venue-submission.md:31`). While the UNKNOWN is outstanding the
adapter refuses new commands on that stream — and, critically:

> "**Protection commands are not exempt from the block — but a protection act the block refuses never
> evaporates:** it stands as a **standing protection intent** (AD-36) and is re-decided when the block
> clears, re-deciding being explicitly not retrying"
> — `SCN-0005:33`

The block clears only through `resolve_unknown(command identity, resolution ∈ observed-accepted |
observed-absent | operator-attested)`, which is the **node's** call, never the adapter's
(`tracker/trading-node-notes.md:46`; `docs/glossary.md`, resolve_unknown entry). Command retry is
prohibited outright and session recovery never resubmits a command
(`docs/contracts/ct-19-venue-command.yaml:31`; `docs/components/ctrader.md:144` FM-1).

**Reconciliation triple.** On-demand complete read-back of orders, fills, positions **and balance**
over a mandatory declared lookback (do-not-default), with a four-term verdict vocabulary:

> "`reconciled | drift | unknown | out-of-lookback` — the fourth term added so that 'I cannot see that
> far back' is NEVER read as 'the position closed'; a standing protection intent (AD-36) re-evaluates
> ONLY against a reconciled verdict, while drift, unknown, and out-of-lookback alarm and hold the
> intent open without dispatching. Reconciliation gates the command pipe only — the sensing pipe never
> blocks on it — and when it runs and what a verdict triggers are node/BMS authority."
> — `docs/contracts/ct-20-venue-event.yaml:26, 44`

**Partial fills are a first-class state, not an exception.** The order-state read-time fold is
`client-submitted | venue-accepted | venue-rejected | UNKNOWN | partially-filled | filled | cancelled |
expired | closed-by-venue` (ct-20:46).

**`isServerEvent` stop-outs.** Server-initiated events are observations of the same shape, never
errors (`trading-node-order-path-study.md:136`). CT-29 gives them their own close reasons —
`venue_liquidation` (reserved for venue margin liquidation; the bare phrase "stop out" is banned) and
`venue_initiated_close` — with `closing_authority = venue`
(`docs/contracts/ct-29-exit-record.yaml:25, 52-53`).

**The node-close-vs-venue-stop race is already resolved** and does **not** become an UNKNOWN:

> superseded-by-fill read-back → `rejected-by-venue (superseded-by-terminal-subject)`, "a named outcome
> never UNKNOWN"
> — `docs/scenarios/SCN-0010-risk-boundary-conflicts.md:33`; `ct-20:21, 51`

**`clientMsgId` idempotency.**

> "every command carries a client-generated identity derived from the command record's `fp1`
> fingerprint (AD-10); the adapter maps it into the venue's client-id field, with the mapping and any
> length bound (cTrader: ≤100 chars) declared in the capability record (CT-18). Re-presenting the same
> command = same identity = idempotent accept … a differing command under a reused identity is refused
> and alarmed."
> — `trading-node-order-path-study.md:134`

A "reused command identity" alarm row already exists in the metrics lens
(`docs/lenses/observability/metrics-and-alerts.md:62-75`).

**Amend atomicity — verify-or-refuse, single-sided only until proven.** cTrader's
`ProtoOAAmendPositionSLTPReq` is one message carrying absolute prices (no cancel-replace), there is no
dedicated response (confirmation rides `ProtoOAExecutionEvent`), absolute placement is **not supported
for MARKET** orders (→ entry-relative placement), and amend atomicity is **undocumented**, so the
ratified posture is single-sided amends only until measured
(`docs/components/ctrader.md:94-100`; `docs/contracts/ct-18-venue-capabilities.yaml:56-60`). AD-34:
`amend_protection` is the fifth command and is **never emulated by cancel-then-place**; it is
risk-non-increasing per protection side, checked against the frozen `original_risk_distance`
(`ct-19:20`).

**OR-11 slippage seed** is a backtest-side ruling, not a live-path one: the seed stays threaded, no
stochastic model is built now (GAP-0048), and the operative live rule is "no ambient randomness — the
invariant binds the live runtime" (`qa/_trace/rulings-corpus-verdicts.md:333-364`).

**Requotes** have no separate vocabulary and need none: a requote is a venue rejection carried through
the versioned per-adapter error map `(venue code, context) → (refusal category, retryability,
after-condition, outcome class)`, with unmapped codes failing closed to `(transient venue failure,
retryable=no, outcome=UNKNOWN)` (`ct-18:29-30`).

### Not settled — three named residues

**(a) Partial-fill accounting into R.** `close_partial` is an `unsupported capability` on the exit side
(ct-19:19, ct-23:24), and R is frozen at admission with three faces (AD-40/DEC-0154). But nothing rules
what happens when the **entry** partially fills: whether R is re-based onto the filled quantity or
stays frozen at the admitted amount. CT-29 carries frozen `original_risk_distance/amount`,
`fill_references` and `realized_r` (ct-29:36-50) — the fields exist; the rule does not.

**(b) Duplicate-fill dedup key.** The corpus gives idempotent *door* intake keyed on `(source,
source-native id, revision)` (`docs/decisions/ADR-0016-data-rooms-splits-journal.md:49`) and a
cardinality law of one journal event per observation/submission/outcome
(`docs/lenses/observability/logging-spec.md:64`), plus correlation by `clientMsgId` and attribution by
label. There is no ratified dedup key for the fill observation itself.

**(c) Position mismatch on restart.** CT-20 states outright that "what a verdict triggers" is node
authority. The GitBook baseline answers it — "Unexplained drift is a technical kill"; "If CT-BMS-03
returns drift, halt trading as a technical kill"
(`workroom/reference/05-trading-node-primer.md:294`) — and "automatic resume after drift/kill" is on
the DROP list (`archive/recovery/trading-node-delta/trading-node-delta.md:193`, D-11). That is
baseline-grade, not `docs/`-grade, so it needs this sitting's ratification.

### What the spine should bind

- The four outcomes, timeout ≠ rejection, UNKNOWN as a state that blocks its `(VenueId, account)`
  stream and clears only through a node-issued `resolve_unknown`.
- Standing protection intents: journaled before dispatch, restart-proof read-time fold, re-decided
  never retried, never time-expiring, satisfied only on `reconciled`.
- The four reconciliation verdicts (the node uses **four**, not the baseline's three).
- Command identity = `fp1` of the command record → `clientMsgId` (≤100 chars, bound declared in
  CT-18); same identity = idempotent accept; different content under a reused identity = refuse +
  alarm.
- Single-sided `amend_protection` only, until amend atomicity is measured at the venue.
- Superseded-by-terminal-subject as a named outcome, never a stream-blocking UNKNOWN.

### Operator questions (residues 3, 4, 5)

**Q-QB3a.** When we ask the broker for 1.0 lot and only 0.6 fills, we have to decide whether the trade's
risk unit "R" shrinks to match. **Recommended: R stays exactly as admitted and is never re-based; the
short fill is recorded as an execution-quality fact on the trade record** — because the whole corpus
already treats R as frozen at admission ("a boundary event never re-bases a frozen R"), and a rule that
lets R move creates a second, quieter way for position size to change. Alternatives: (b) re-base R onto
the filled quantity so reported risk matches reality; (c) refuse the partial fill and flatten the
remainder. **Cheap-veto ASSUMPTION.**

**Q-QB3b.** If the broker sends us the same fill twice (which happens after a reconnect), we need one
rule for spotting the duplicate. **Recommended: match on the broker's own deal/execution id within that
account, keep the first, and raise a data-quality alarm if a second copy arrives with different
contents** — because it reuses the "record it exactly as received, never overwrite" law we already
have. Alternatives: (b) match on our own command id plus quantity; (c) match on a content fingerprint
of the whole message. **Cheap-veto ASSUMPTION.**

**Q-QB3c.** After a restart, if the broker's positions do not match our own books and we cannot explain
the difference, the node has to do something drastic. **Recommended: stop opening new trades, keep
managing and exiting the ones we have, and refuse to resume until you have looked at the reconciliation
yourself — a restart is never permission to resume** — because this is exactly what the GitBook
baseline already says ("unexplained drift is a technical kill", no automatic resume), and the
alternative risks trading on a false picture of the account. Alternatives: (b) auto-resume once a later
reconciliation comes back clean; (c) flatten everything on unexplained drift. **Cheap-veto ASSUMPTION**
(note: (c) would violate nothing, but it converts a bookkeeping fault into a market action, which the
corpus avoids everywhere else).

---

## QB4 — Where live secrets live on the VPS, and how rotation works without code changes

**VERDICT: PARTIAL.** The lifecycle is fully ratified; one deployment mechanic (how a secret gets onto
the VPS) is open.

### Settled

**Constitution L34:**

> "QMF components handle secret references, never values; secret values live only in the adapter's
> connection manager for a session's lifetime, and secrets never appear in repositories, configuration
> artifacts, journals, evidence, fingerprints, or logs."
> — `docs/constitution.md:84` (DEC-0136)

**Store class, verbatim:** values "are injected at the composition root from the deployment
environment's protected store (`systemd-creds`-class on the VPS), and only the adapter's connection
manager holds `SecretValue`s in memory, through an injected `SecretStore` port"
(`docs/lenses/ops/runbook.md:122`; identically `docs/lenses/security/security-model.md:61`). Store
mechanics and key custody are explicitly this sitting's: "Store mechanics and key custody
(systemd-creds-class on the VPS) are deployment concerns landing at the node/ops sitting"
(`docs/contracts/ct-21-venue-secret-session.yaml:28`).

**One refresher, and it is the node.** "One live refresher per credential; a workstation tool never
refreshes a credential a VPS session owns" (`ct-21:21`). Rotation is **store-before-discard**; a failed
store after rotation raises an alarm and blocks the command pipe while sensing continues (`ct-21:22`).

**Token facts (PRIMARY, verified this run):** access token 2,628,000 s ≈ 30 days
(`https://help.ctrader.com/open-api/account-authentication/`); refresh token has **no expiration** —
valid until used to refresh or until the cTID is re-authorised. In-band refresh is
`ProtoOARefreshTokenReq` (`tracker/trading-node-notes.md:13`). The refresh token is therefore the crown
jewel: it is the one credential whose leak is unrecoverable without operator action, and the ratified
compromise drill is exactly that — "cTID re-authorization, application-credential reset, store
replacement, session restart" (`ct-21:23`).

**Rotation without code changes** falls out of the ratified design: the `SecretStore` port exposes only
**read + atomic replace** (`ct-21:20`; `packages/qmf-core/src/qmf/core/secret.py:188`), so a rotation is
a store write and a session restart — never a code change and never a redeploy.

**Today's implementation gap (ground truth):** the only concrete `SecretStore` in the repo is an
in-memory reference store used by examples/tests (`packages/qmf-core/examples/secret_usage.py:50-51`);
`keyring` appears nowhere; there is no `.env` slot for venue credentials and by contract there never
will be. The production store is this sitting's to specify.

**The operator's side is already ruled (memlog, top authority):**

> "CREDENTIALS: never ask for a secret in chat/terminal/.env/file (CT-21); cTrader creds in Windows
> Credential Manager under qmx/* labels; Spotware app QMX-NODE SUBMITTED, tokens do not exist yet;
> this sitting needs NO broker access."
> — `_bmad-output/planning-artifacts/architecture/architecture-NODE-2026-08-28/.memlog.md`

**Web-verified mechanics (PRIMARY):** systemd encrypted credentials arrived in v250;
`LoadCredentialEncrypted=` / `SetCredentialEncrypted=` decrypt at service start; the key may be sealed
to the host key in `/var`, to TPM2, or both (AES256-GCM) — `https://systemd.io/CREDENTIALS/`. Ubuntu
26.04 LTS ships systemd 259, 24.04 ships 255.4, so the feature is fully available on either target.
On the workstation side, `keyring` 25.7.0's `WinVaultKeyring` reads a UI-created generic credential
through `win32cred.CredRead(Type=CRED_TYPE_GENERIC, TargetName=…)` **provided the UI credential's
target name equals the service string the node queries**.

### Not settled

1. **Wizard transport** — how the secret crosses from the operator's Credential Manager to the VPS
   store without ever existing as a file, an argv entry, or terminal scrollback.
2. **Key custody** — host-key sealing vs TPM2 sealing on a cloud VPS.
3. **Object-storage encryption key custody** — named at this sitting by DEC-0118, still unstated.

### What the spine should bind

- References never values, everywhere above the connection manager; the connection manager as sole
  in-memory value holder for a session's lifetime.
- `systemd-creds` `LoadCredentialEncrypted=` as the VPS store; Windows Credential Manager under
  `qmx/*` as the operator-workstation door. **Two different doors, never conflated.**
- Exactly one live refresher per credential, and it is the node's own session. No workstation tool ever
  refreshes a token the VPS owns — the refresh token dies on use.
- Rotation = atomic replace in the store, then session restart; a failed store = alarm + command-pipe
  block, sensing unaffected. No code change, ever.
- Compromise drill anchored on cTID re-authorization.
- A missing or expired credential is an `unavailable dependency` typed refusal carrying the reference
  id, never the value; cold start reports only `is_set: true/false` metadata.

### Operator questions (residues 6, 7)

**Q-QB4a.** We need a safe way to move your cTrader credentials from your laptop's Credential Manager
onto the VPS, once, without the secret ever landing in a file or in your terminal history.
**Recommended: a small wizard that reads the credential from Credential Manager and pipes it straight
into `systemd-creds encrypt` running over SSH on the VPS, so the secret only ever exists inside two
processes' memory and the encrypted blob on the VPS** — because it never writes a plaintext file, never
puts the secret in a command line (which other users on a machine can read), and never echoes it to
screen. Alternatives: (b) you type it once into an interactive prompt on the VPS yourself; (c) you paste
it into the broker's own web console and we fetch tokens fresh each time. **Cheap-veto ASSUMPTION.**

**Q-QB4b.** The VPS can lock its stored credentials either to the machine's own key file or to a
hardware chip (TPM). **Recommended: lock to the machine's key file** — because cloud VPS hardware chips
do not reliably survive a live migration or a rebuild, and if that happens the credentials become
unrecoverable; with the key file, a rebuild just means re-running the wizard. Alternative: (b) TPM
sealing, which is stronger against someone stealing a disk image but risks locking us out. **Cheap-veto
ASSUMPTION.**

---

## QB5 — Backup restore drill as a required scheduled test

**VERDICT: PARTIAL.** The drill is ratified as required; its cadence is explicitly reserved for this
sitting.

### Settled

> "Verification is a first-class primitive: automated sample-restore tests and a periodic full-restore
> rehearsal are part of the ratified design, never optional add-ons (DEC-0118)."
> — `docs/contracts/ct-14-backup-restore.yaml:15`

> "The ratified backup design is nightly, encrypted, versioned, off-machine object-storage copies: the
> primitive produces the encrypted versioned copy and the application/ops cadence runs it nightly
> (DEC-0118)."
> — `ct-14:14`

> "Recoverability is claimed only through the ratified verify primitives — automated sample-restore
> tests plus a periodic full-restore rehearsal (DEC-0118) — never asserted from a snapshot alone."
> — `docs/scenarios/SCN-0004-off-machine-backup.md` (Then)

Two more ratified riders that shape the drill: restored reads still enforce the 12-month seal — "a read
against restored data refuses sealed rows as a policy rejection exactly as a live read does" (ct-14:18)
— and "Backup round-trips preserve stored timestamps as data: int64 UTC nanosecond values are stored
and restored verbatim, never re-derived under a later calendar identity or tzdata version" (ct-14:19).
A recovery or migration never mutates the only copy (SCN-0004).

Topology ratified: "the trading-node VPS records and syncs down, the workstation holds the working
archive, and the bucket catches nightly copies" (ct-14:22).

### Not settled

Cadence and every number. `registry:restore_verification_cadence`,
`registry:backup_recovery_point_objective`, `registry:backup_recovery_time_objective`,
`registry:backup_retention_period` are all `null` and `configurable: true`
(`docs/registry/variables.yaml:258, 270, 282, 294`), and SCN-0004 says outright they "are not filled
from a recommendation; they are measured and set at that sitting." Object-key layout and encryption key
custody likewise (`ct-14:37`).

### What the spine should bind

- Two distinct verification kinds, both required and both scheduled: an **automated sample-restore**
  and a **periodic full-restore rehearsal**.
- Both journal as `data quality` events; a failure alarms and is never silently retried.
- The full rehearsal restores into a scratch location and verifies by fingerprint — never over the only
  copy, never over live evidence.
- The rehearsal is where RTO is **measured**, not declared.
- Four registry variables minted as `configurable: true` with these as recorded evidence.

### Operator question (residue 8)

**Q-QB5a.** Backups are useless unless we regularly prove they restore, so we need to pick how often to
test — for example, restoring one night's journal file and checking it matches. **Recommended: a small
automatic sample restore every week on the VPS, plus one full restore into a scratch folder every month
with a fingerprint check, both written into the evidence log** — because weekly catches a broken backup
before a month of copies are all bad, and monthly is often enough to prove a real disaster recovery
without eating the machine. Alternatives: (b) nightly sample + quarterly full (more noise, slower to
catch a full-restore fault); (c) monthly sample + annual full (cheapest, and the one that quietly fails
you). **Cheap-veto ASSUMPTION.** Recovery-point objective is already effectively 24 hours because the
backup itself is ratified nightly; recovery-time will be a measured number from the first monthly
rehearsal, not a promise.

---

## QB6 — "Explained drift" on day one of paper mode

**VERDICT: PARTIAL.** The live drift check is defined; what paper mode checks *instead* is open.

### Settled

**The decomposition** (PRD mined doctrine, direction-grade until this sitting ratifies it):

> "Broker-vs-virtual divergence decomposes into journaled components (swept-but-unwithdrawn cash,
> re-seed remnants, open unrealized P&L); **only the residual is drift. Verdicts: reconciled | drift |
> unknown. Unexplained live drift halts trading, and restart is not permission to resume — a fresh
> reconciliation review is. The paper/demo binding is excluded from the live drift check**"
> — `_bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/prd.md:406-411`

**Zero tolerance** (GitBook baseline, which L37 makes authoritative for money content):
`registry:reconciliation_epsilon = 0` with `operator_review: true` — "operator review is mandatory
before non-zero use" (`workroom/reference/05-trading-node-primer.md:294`;
`archive/recovery/trading-node-delta/work/gitbook-baseline.md:236`).

**Broker equity is derived, not read.** cTrader supplies no direct equity field; equity = balance +
quote-currency unrealized P&L, with side-correct valuation and per-message money precision as evidence
(`tracker/trading-node-notes.md:15`, K-54). So "broker equity" is itself a computed quantity carrying
its own error sources — the money-exponent decode, the valuation side, and cross-currency conversion.

**The node must use FOUR verdicts, not three.** The baseline's `reconciled | drift | unknown` predates
CT-20's ratified vocabulary, which adds `out-of-lookback` precisely so that "I cannot see that far
back" is never read as "the position closed" (ct-20:26). This is a real correction the node inherits.

**Paper money is frozen evidence.** "a configurable UI-editable starting balance, never hand-adjusted;
a reset mints an operator-signed paper epoch record; paper P&L never becomes Treasury cash and never
buys a seat" (`docs/decisions/ADR-0009-book-level-paper-mode.md:32`).

### Not settled

What the drift monitor *does* on day one, when the only binding is paper. The corpus excludes the
paper/demo binding from the live drift check and then says nothing about what replaces it — but two
things are worth noticing: (i) a paper Book has **no counterparty at all** to reconcile against, only
its own ledger; and (ii) the **paired demo account is a real broker account** — role `demo`, and
`world = live` under the money-reality rule (`ct-21:41`) — so full reconciliation machinery *can* run
against it, and the soak is the only chance to prove that machinery before real money is involved.

### What the spine should bind

- Explained-delta decomposition with named journaled components; only the residual is drift.
- Four verdicts, `reconciliation_epsilon = 0`, `operator_review: true` on any non-zero.
- Unexplained **live** drift → entries stand down, exits and evidence continue, no automatic resume.
- The paper/demo binding excluded from the live drift check — and explicitly given its own two checks
  (below) rather than being left unmonitored.

### Operator question (residue 9)

**Q-QB6a.** In paper mode there is no real money to compare against, so we need to decide what the
"books balance" check actually checks on day one. **Recommended: two checks — (1) the paper ledger must
add up against its own trade records, and (2) we run the full real-money reconciliation against the
demo account anyway, but treat a mismatch as an alarm to investigate rather than a reason to stop** —
because check (1) catches our own accounting bugs, and check (2) is the only way to prove the real
reconciliation machinery works before live money is on it. Alternatives: (b) run no drift check at all
in paper mode (simplest, and leaves the machinery untested until the worst possible moment); (c) treat
a demo mismatch as a full stop like live (safest-sounding, but a demo server's own quirks would keep
halting the soak). **Cheap-veto ASSUMPTION.**

---

## QB7 — Alert fatigue: allow-list for the paper soak vs live

**VERDICT: PARTIAL.** The live allow-list is ratified in substance; no paper-soak profile exists.

### Settled

**The allow-list is closed, and everything else is evidence not a push:**

> notifications fire only on a **closed, ratified event-class allow-list — sweep, re-seed, refund,
> kill-switch/KSA events, and supervision fail-closed; everything else is console evidence, never a
> push**
> — `prd.md:119-127`

Independently corroborated at K-48 (`KEEP` disposition): "Actual notification classes are **sweep,
`re_seed`, refund, KSA/kill-switch, and supervision fail-closed**. Other events are Console
evidence/log." (`archive/recovery/trading-node-delta/trading-node-delta.md:112`), with refund dormant
in V1.

**The two-plane rule:** "authoritative system records (journals, veto ledger, lineage) and operator
notification delivery are **separate layers with separate policies — losing a notification never erases
the underlying evidence, and the notification channel is never a permission path back into live
trading**" (`prd.md:122-127`).

**"An alert is evidence, not permission" is already law, verbatim:**

> "An alert is evidence, not permission. It cannot promote an artifact, authorize an order, flatten
> exposure, invoke an exit, change Book mode, rotate a secret, restore over data, or command an
> external provider. Human-only promotion remains absolute."
> — `docs/lenses/observability/metrics-and-alerts.md:79` (DEC-0041)

**Delivery mechanics are explicitly deferred:** "QMF V1 has no ratified metrics schema, aggregation
window, dashboard, alert threshold, severity tier, notification destination, paging route, or automatic
remediation" (`metrics-and-alerts.md:16`); channels, retries, dedupe, quiet hours and credentials stay
deferred to the node/terminal phases (`prd.md:122-127`; GAP-0002).

**One rule that must survive into the soak:** a paper-stream outage "alarms like a live one"
(`ADR-0009:36`; the metrics alarm table carries "paper-stream outage — same alarm class as a live
outage").

### Not settled

Whether the soak runs the same allow-list, and whether the soak needs anything extra.

### What the spine should bind

- The closed allow-list as the only push tier, live and paper alike; everything else is console
  evidence.
- Two planes kept apart; a lost notification never erases evidence and never authorizes anything.
- No numeric thresholds, no severity tiers, no channels this phase.
- A paper outage alarms in the same class as a live outage.

### Operator question (residue 10)

**Q-QB7a.** During the two-day paper soak we could either push you the same short list of alerts we
would in live, or push more so you can watch it closely. **Recommended: keep exactly the same short
list, add one daily summary of everything else, and add two soak-only alerts that switch off at go-live
— broker checks failing at first connection, and the clock drifting past a band** — because those two
are precisely what the soak exists to discover, and everything else stays readable in the console
rather than buzzing you. Alternatives: (b) identical to live with no additions (cleanest, but you may
miss a first-connection failure for hours); (c) push everything during the soak (guarantees you stop
reading them). **Cheap-veto ASSUMPTION.** Channels stay deferred — for the soak, "push" means the local
console plus a file you can read.

---

## QB8 — A dry-run / replay mode for the node itself

**VERDICT: PARTIAL.** Every piece exists in ratified form; the composition into a node-side regression
tool does not.

### Settled

**One loop, three bindings — this is the decisive sentence:**

> "Backtest, replay, and live differ only by which clock and adapters the run-config binds; the loop
> is never forked"
> — `docs/components/qmb.md:174` (DEC-0169); restated at `_bmad-output/planning-artifacts/epics.md:2890`
> ("backtest, replay, and (deferred) live share identical loop code — the loop is never forked")

**Clock injection is the mechanism:**

> "No component below the composition root reads the system clock … the application's composition root
> injects the real system clock for `world = live`, or a data-driven replay clock … for `world =
> replay`."
> — `docs/architecture/overview.md:46, 50`

**The replay run is already golden.** SCN-0012 pins a `world = replay` binding minted per run, "a
DIFFERENT identity from any live binding of the same Book instance and incomparable to it," advanced by
a frontier clock (`docs/scenarios/SCN-0012-qmb-replay-run.md`, Then §3). Rooms are instantiated **per
world** and a cross-world read is a `policy rejection`
(`docs/decisions/ADR-0016-data-rooms-splits-journal.md:41`).

**The world question the task raised is decided, and the answer is `world = replay`, not `live` with a
provenance tag.** Two rules combine. First, AD-12/DEC-0110: worlds are `live | replay | simulated`, and
"the Account role, not the world label, carries money-reality, so paper and demo runs are `world =
live`" (`docs/components/qmf-data.md:55`) — that rule is about a *real account*, and a replay has no
venue at all. Second, the time audit's blocker: "Every persisted record carries non-nullable
time_domain (live | replay | simulated) participating in identity; **replay may never write into the
live evidence namespace**" (`time-audit-devops.md:44`). A replayed live day is therefore a replay-world
artifact whose *inputs* cite live-world provenance — not a live artifact tagged "replay".

**The shadow lane** already describes the near-real-time variant: "Candidate labeler/model versions run
as near-real-time replay over the captured canonical feed, off the hot path, to their own manifest
prefix, never to live consumers" (`prd.md:424-431`) — mined doctrine, direction-grade.

### Not settled

Whether the node's replay adapter reproduces the **order path** (re-deciding commands and comparing
them against recorded venue answers) or only the **sensing path**. Nothing in the corpus rules it.

### What the spine should bind

- One loop. Replay differs from live only in which clock and which adapters the composition root binds.
- A replay adapter behind the same neutral venue port, feeding recorded observations from the archive;
  the node's own decision path unchanged.
- `world = replay` for every artifact a replay produces; replay never writes into the live rooms;
  cross-world read is a policy rejection; a replay binding can never gate live money.
- The replay clock is a pure function of the data cursor.

### Operator question (residue 11)

**Q-QB8a.** We want to be able to re-run a recorded live day through the node to check a change did not
break anything — the question is how far the replay goes. **Recommended: replay the market data and
re-run every decision, comparing the decisions we would make now against what we actually did, but
never re-send orders — the recorded broker answers are attached as evidence only** — because it catches
the thing we actually care about (did our judgement change?) with no possibility of a replay
accidentally touching a broker. Alternatives: (b) also simulate the fills so the replay produces a full
profit-and-loss figure (more useful, more ways to be wrong); (c) no replay tool at all this phase.
**Cheap-veto ASSUMPTION.**

---

## QB9 — Resource footprint on the VPS at ~40 bots

**VERDICT: RATIFIED-ANSWER** (the method is fully ratified; the only "open" item is that the numbers do
not exist yet by design, and one piece of logistics gates them).

### Settled

> "**Measure-then-budget performance.** QMF invents no performance numbers. Every component ships a
> benchmark harness carrying the same status as its unit tests, measuring speed and peak memory at a
> load ladder … First real measurements are recorded as fingerprinted baselines scoped to a declared
> (OS, CPU-class) tuple; each benchmark's regression threshold is stated when its baseline is recorded
> … thereafter a regression beyond threshold fails the tier-2 merge gate, memory equally with speed.
> One design constraint is stated rather than measured: `qmf-core` imports in well under one second …
> **Server sizing and scaling are node and compute decisions made later with these numbers.**"
> — `docs/decisions/ADR-0014-performance-observability-concurrency.md:37` (DEC-0111, AD-13)

> "Until the first baselines are recorded there are no numeric budgets at all — the gate can only
> compare against a baseline that exists, so early components pass on correctness and record their
> numbers rather than being judged by them."
> — `ADR-0014:45`

`registry:design_bot_concurrency = 40`, `configurable: false`, annotated as a "motivating reference for
benchmark ladders (10/100/200), not an SLO" (`docs/registry/variables.yaml:145`). NFR-04 restates it
(`prd.md:554-556`). GAP-0013 is *answered* by exactly this ruling (`_docwork/gaps.yaml:122-130`).

**And CT-28 already makes the measurement a precondition of live money:**

> "live-path rung baseline: the six-stage live-path rung has a recorded baseline on this deployment's
> declared `(OS, CPU-class)` tuple (AD-13/AD-24/AD-32 Layer 2)"
> — `docs/contracts/ct-28-book-binding.yaml:36`, under `bind_time_capability_check`, where "a shortfall
> refuses at bind time, never at trade time"

**Harness ground truth in code:** `qmf-core` ships a real harness
(`packages/qmf-core/src/qmf/core/_bench.py`); `qmf-venue`'s `_bench.py` is a deliberate 50-LOC
placeholder; and a genuine peak-RSS seam already exists with a Linux path —
`qmb/src/qmb/orchestrator/watch.py` reads child peak memory via `resource.getrusage` on POSIX and
`GetProcessMemoryInfo` on Windows (`watch.py:18-21, 111, 274-309`).

### What the node sitting may rule

VPS sizing is **measured at the paper soak, never invented**. Concretely the spine should bind: the node
ships its own benchmark harness at the same status as its tests, measuring wall-clock and **peak RSS**
at the 10 / 40 / 100 / 200 bot marks against the ~40-bot design reference; the first Linux baseline is
fingerprinted to the VPS's declared `(OS, CPU-class)` tuple; that baseline becomes the regression gate
and satisfies CT-28's bind-time rung requirement. No sizing number enters the spine.

### One genuine blocker, and it is logistics not design

`tracker/map.md:66` records: "**Trading VPS exists by default; procuring it is Mubarak's side**, core is
Claude's." CT-28 refuses a live binding without a rung baseline **on this deployment's tuple** — so the
VPS must exist and the soak must run on it before any live binding is legal. This does not block the
spine or the epics; it blocks the live milestone.

### Operator question (residue 12)

**Q-QB9a.** We cannot say how big a VPS you need until we measure the node running on one — the corpus
forbids inventing the number. **Recommended: pick a modest VPS now (the paper soak is what tells us
whether it is enough), because the design already refuses to let a Book go live until a real speed and
memory baseline has been recorded on that exact machine.** Alternatives: (b) size it generously up
front and pay for headroom we may not need; (c) delay procuring until after the soak — which is
circular, since the soak needs the machine. **BLOCKER for the live milestone** (not for this sitting or
the epics): no VPS, no baseline; no baseline, no legal live binding.

---

## QB10 — Verification debt from the QA phase that touches node territory

**VERDICT: RATIFIED-ANSWER** on the boundary rule, which decides the split without an operator ask.

### The rule that decides it

> "The order path, protection funnel, startup semantics, and flatten-authority assignment are node/risk-
> sitting territory; QMF records only the contract surface AD-26 through AD-28 define and references
> `tracker/trading-node-notes.md` as a pointer, never absorbing it."
> — `docs/decisions/ADR-0007-venue-neutral-integration.md:40` (DEC-0142)

Plus the standing framing on the debt itself: 44 CONFIRMED findings were fixed and PROVEN in Fix Round
1; the **64 UNPROVEN + 23 VERIFICATION-DEBT rows are unverified, not confirmed defects**
(`qa/_trace/proof_map.md:18-19`; `FINAL-REPORT.md:3-6`). And the promotion gate's workflow, UI and
timing are "platform territory outside QMF" (`docs/components/qmf-registry.md:56`) — which is why the
promotion proof lands on the node.

### Becomes a node story (cannot be proven anywhere else)

| Row | Why it is node work |
|---|---|
| **#5 / QMX-F045** human-only promotion signer — "`PromotionCard.sign(signer="agent:…")` never tested"; "can an agent mint a card `authorize_live_promotion` accepts?" is unanswered (`proof_map.md:35`, `findings.csv:47`) | The promotion **door** is the node's; the story is "prove end-to-end through the node's promotion door that a non-human signer is refused, and that the crossing lands ADMITTED with no intents and no ledger" (`prd.md:144-150`) |
| **QMX-F046** CT-13 promotion event entirely unverified (`findings.csv:48`) | Same door; assert the journal event carries card `fp1` + `correlation_id` only, never a second schema |
| **QMX-F062** UNKNOWN block proven on exactly one stream; `(VenueId, account)` granularity untested in **both** directions (`findings.csv:64`) | The command stream is the node's seam; prove it against one demo connection carrying two accounts — a whole-connection block and a submitting-binding-only block currently both pass |
| **QMX-F063** CT-18 amend-atomicity verify-or-refuse has **zero** tests (`findings.csv:65`) | Only provable at the venue; it *is* a first-connection empirical check, and it gates whether dual-sided amends are ever legal |
| **QMX-F064** Spotware/Twisted ban, secret-scan gate, undeclared order-parameter refusal, **boot sequence-reset** (`findings.csv:66`) | Boot semantics are node territory by DEC-0142; the dependency ban is enforceable by the node's own gate |
| **QMX-F067** Layer-2 demo/paper shakedown **never called**; Bot↔Book↔BMS↔account cardinality; colliding-action collapse rank winner; window retro-invalidation (`findings.csv:69`) | All four are first wired in the node; the shakedown is literally AD-32 Layer 2 |
| **QMX-F068** frozen-money-face R at admission proven only on a function the door path is never shown to call (`findings.csv:70`) | The door path is the node's |
| **QMX-F069** storage-failure-blocks-dispatch proven by passing the failure in, with no happens-before observed (`findings.csv:71`) | Journal-before-dispatch is a node ordering guarantee |
| **QMX-F102** RPO/RTO/retention/verification cadence/key custody/provider/object-key layout left at the node/ops sitting (`findings.csv:104`) | Closed by **QB5** and **QB4** above |
| **#10 PARTIAL** venue UNKNOWN stream granularity (`proof_map.md:40`) | Same as F062 |

### Stays foundation debt (does not become a node story)

QMX-F053/F054/F055 (TZPATH never observed; `get_provider`/`register_forex_17ny` not-ready branches
never executed; swap-Wednesday not modelled) — `findings.csv:55-57`. QMX-F056/F057 (backup boundary
refusal-category set silently shrunk; int64-ns-verbatim-through-a-later-calendar-identity round trip
never constructed) — `findings.csv:58-59`. QMX-D005 (8 missed backup clauses), QMX-D006 (7 missed source-
intake clauses, recorder WriterId, bid/ask timestamps) — `findings.csv:115-116`. QMX-F030 / OR-11
(stochastic slippage draw, UNPROVEN by design, GAP-0048-gated) — `findings.csv:32`,
`FINAL-REPORT.md:82-84`. QMX-D008/D010/D002 are *containers* for rows already split above.

**One split row:** QMX-F085 (verify/gap-check never exercised over the rooms; licence gate is an
oracle-from-implementation; the four-state licence taxonomy never pinned) — the **download** half stays
foundation debt; the **recorded-live-data** half becomes a node story, because the node is the first
thing that writes live evidence into the rooms.

### What the spine should bind

- A node story per row above, each naming the finding id so the debt is discharged traceably rather
  than silently.
- Nothing here re-opens a ratified decision; every row is a *proof* obligation, not a design question.

**No operator question.** DEC-0142 decides the split.

---

## QB11 — Are cTrader trendbars BID- or mid-derived?

**VERDICT: PARTIAL.** The *policy* is fully ratified; the *fact* is second-hand and stays that way
until the node measures it.

### Settled

**Policy — never hardcoded, measured per broker.** Verbatim at `ct-02:45` (quoted under QB1), and
`registry:venue_trendbar_price_basis` carries no value, annotated `measured-per-broker`
(`docs/registry/variables.yaml:383`). The corpus already demoted the claim: the 17:00-NY boundary and
BID-derived trendbars are "demoted to 2013-forum-grade and NEVER hardcoded — adapter measures per
broker at first connection + continuous monitor" (`_docwork/gaps.yaml:362-370`, GAP-0037 answered;
`docs/components/ctrader.md:72-73`).

**The first-deploy check is already a named part of the adapter contract**, with its refusal stated:

> "Bar-basis reconciliation | Reconcile trendbar OHLC against explicitly-BID/ASK tick history per broker
> and symbol class; record the verified quote side (DEC-0135). | A failed bar-basis reconciliation
> refuses bar evidence."
> — `docs/lenses/ops/runbook.md:65-71`, first-connection verification suite

### The web finding, graded honestly

Ticket 006 asked the question (`tracker/tickets/006-spotware-broker-setup.md:11-16`). The web-verification
seat found **no official documentation page** stating the basis. The only statement is a Spotware
moderator on the official community forum: *"It is not possible to get trendbars based on ask prices"*,
with the thread confirming the observation that the prices are bid-based
(`https://community.ctrader.com/forum/connect-api-support/41268/`). **Grade: SECONDARY** — vendor
moderator, not a docs page. Consistent with cTrader charts being bid-based by default. It changes
nothing: the corpus already refuses to hardcode it.

### What the backtest-to-live comparison must assume meanwhile

**Nothing.** Until the reconciliation passes, venue-native bars "are ungoverned observations, never
assumed aligned" (ct-02:44) and bar evidence is refused. Backtests run on Dukascopy tick data carrying
both sides, so the honest interim posture is to build every backtest-to-live comparison on **ticks**,
not trendbars, and to treat any trendbar-derived series as provisional until the per-broker basis is
recorded with its evidence.

### What the spine should bind

- The five-check first-connection suite as a hard gate before the first command and before any
  evidence-bearing decode: spot-timestamp unit, D1 boundary, bar-basis reconciliation, pip formula,
  money exponent — each with its named refusal, each journalled as a `data quality` event.
- The verified quote side stored as per-broker configuration with its reconciliation evidence attached.
- Bar-derived comparisons refused until the basis is recorded; tick-based comparison as the interim
  path.

### Operator question (residue 13)

**Q-QB11a.** The broker's candle charts are almost certainly built from bid prices, but nobody at
Spotware has written that down on a documentation page — only a moderator said it on their forum.
**Recommended: keep the design as it already is (measure it ourselves on the first connection and store
the answer per broker), and in the meantime compare backtests to live using raw tick prices rather than
candles** — because it costs nothing, and a wrong assumption here would quietly shift every entry price
by the spread. Alternatives: (b) assume bid and move on; (c) email Spotware and wait for a written
answer. **Cheap-veto ASSUMPTION** — this is already ratified corpus, the recommendation is just the
interim comparison rule.

---

## QB12 — Latency

**VERDICT: PARTIAL.** Settled: no numbers may enter the spine. Open: nothing that blocks anything.

### Settled

AD-13 (quoted in full under QB9) forbids invented performance numbers. The six-stage live-path
decomposition exists as **named rungs with no numeric budgets until measured**
(`ADR-0007:37`; `docs/components/qmf-venue.md:103`;
`docs/lenses/observability/metrics-and-alerts.md:28`). The rungs are named in the order-path study:
tick received → evidence write → indicator update → decision → risk evaluation → order submitted
(`trading-node-order-path-study.md`, §e.7).

**The contradiction is on the record, deliberately unresolved:**

> "**Latency:** operator ~50ms full-round-trip direction vs GitBook 35/10-45/100ms budgets — GAP-0013
> forbids invented numbers; the **six-stage latency decomposition** … recorded as **AD-13 rungs WITHOUT
> numbers until measured**"
> — `tracker/trading-node-notes.md:24`

And the routing verdict: "node latency budgets are **evidence, not spine constants**"
(`_bmad-output/planning-artifacts/prds/prd-QMX-2026-08-21/correlate.md:149`).

**Two measurement laws bind now**, both from the time audit's blocker tier: durations are **monotonic**
only — "Never subtract wall timestamps for durations; never publish monotonic as a timestamp"
(`time-audit-devops.md:14`) — and cross-machine "latency" is an offset-contaminated **estimate**, never
a measured duration (`:15`).

**Where the first measurements land:** the paper soak, on the VPS, as a fingerprinted `(OS, CPU-class)`
baseline — and CT-28 then requires that baseline before any live binding (`ct-28:36`, quoted under QB9).

### What the node sitting may rule

Rung **names** and **measurement points** only: which stamp opens and closes each rung (the adapter owns
arrival and submit stamps, K-42), that every rung duration is monotonic-derived, and that no rung's
number enters the spine. The operator's "favor scalping" direction is a design bias — it shows up as
drain-order discipline (execution and system events served before market data, so a tick storm cannot
starve the risk checks — idea-ledger #50) — not as a budget.

### Operator question (residue 14)

**Q-QB12a.** You have said roughly 50 ms end to end, and an older document says 35/45/100 ms; our own
rules forbid writing any of those into the design before we measure. **Recommended: name the six stages
and exactly where we start and stop the stopwatch, record your ~50 ms as a target we are watching
rather than a rule, and let the paper soak produce the first real numbers** — because a made-up budget
becomes a fake pass/fail gate, and the design already refuses to let anything go live without a real
measurement on the real machine. Alternatives: (b) adopt 50 ms as a hard limit now; (c) adopt the older
35/45/100 ms set. **Cheap-veto ASSUMPTION.**

---

## QB13 — Multi-account / multi-broker direction

**VERDICT: PARTIAL** — the shape is comprehensively ratified; one identity-axis question is open.

### Settled

**Broker identity is configuration, not architecture:**

> "broker identity is **deployment configuration**, never architecture; IC Markets is stated intent, not
> commitment."
> — `docs/decisions/ADR-0007-venue-neutral-integration.md:38` (DEC-0139); `registry:venue_broker_identity`
> is `configurable: true` (`docs/registry/variables.yaml:405`)

**The binding chain and its tuple:**

> "bot → book → BMS → operator (L36). One BMS instance per account serves many Books; a Book binds
> exactly one BMS at a time …; an instance never spans venues; the risk domain is the binding
> `(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)`, aligned with the `(VenueId, account)`
> command stream."
> — `docs/decisions/ADR-0008-book-and-risk-boundary.md:32`

**Account roles are already the enum the question names:** `live | demo | paper-validation |
paper-benched | prop-firm`, riding the execution-target record and **not** part of the identity tuple
(`docs/contracts/ct-21-venue-secret-session.yaml:40`; `ct-28:17`).

**Command stream granularity:** `(VenueId, account)` — "coarser than an account binding and strictly
finer than a connection; a session-epoch id rides every venue observation" (`SCN-0005:21`). It is the
unit of UNKNOWN blocking, `WriterId`, gapless sequence, and the BMS control-rank table
(`ct-30:28`, one table per stream).

**Connections:** PRIMARY-verified — "Demo and live environments are fully separated … you would need to
establish and maintain two separate connections"; "At most, you should create two connections: one for
demo accounts and one for live accounts. Each connection can support an unlimited number of accounts of
a certain type." (`https://help.ctrader.com/open-api/proxies-endpoints/`,
`https://help.ctrader.com/open-api/connection/`); recorded at `tracker/trading-node-notes.md:8`.

**Pooling is already framed as the multi-account seam** (PRD mined doctrine): "One connection pool per
account binding, per-account command affinity, token-bucket limiting; caps are per connection at
protocol level, so synchronized bursts … need sharding or a shared bucket; **this is also the future
multi-account load-balancer seam**" (`prd.md:412-416`). CT-18 makes `throttle_scope`
(`connection | account | binding`) a **declared** capability, so the node must read it rather than
assume per-connection (`ct-18:39-64`).

### What the V1 node must have so a second account/broker is config, not architecture

1. Every runtime object keyed by the ratified tuple. Nowhere a singleton "the account" or "the broker".
2. A **roster** artifact — deployment configuration read at the composition root — listing account
   bindings `(VenueId, AccountId, role, world)` plus credential reference, BMS definition fingerprint,
   and the Book bindings on that account; one BMS instance minted per account from it.
3. One **command stream** object per `(VenueId, account)` carrying its own UNKNOWN block, `WriterId`,
   gapless sequence, control-rank table and token bucket; the bucket keyed by the CT-18-declared
   throttle scope.
4. A connection layer that already models *N* connections keyed by `(venue, environment)` with accounts
   multiplexed onto each — cTrader caps the useful count at two today, but the shape must not assume it.
5. Adapter selection by `VenueId` at the composition root. The port is already neutral (CT-18..21), so a
   second broker on cTrader is a new AccountId plus credentials; a second *platform* is a new adapter
   behind the same port.

**Do not build now:** cross-account netting, a load balancer, or any cross-stream ordering guarantee —
AD-37 declares cross-stream ordering an explicit **non-guarantee**
(`discovery-architecture-sessions.md:88`).

### Not settled

The **venue-vs-platform axis**. CT-03 identity is an opaque `(venue, symbol)` pair; ~6 brokers all on
cTrader means "venue" is doing double duty. Recorded as an open modelling question, not adopted:
"does QMF need a *platform* axis distinct from *venue*?" (`mine-planning.md:197-205`).

### Operator question (residue 15)

**Q-QB13a.** If you later add a second broker that also uses cTrader — say Pepperstone alongside IC
Markets — we need to know whether the system sees that as one venue with two accounts, or two venues.
**Recommended: treat each broker as its own venue, even on the same platform** — because their symbol
lists, spreads, daily boundaries and trading hours genuinely differ, and lumping them together would
force a symbol-mapping problem later that we would have to unpick. Alternatives: (b) one venue
("cTrader") with brokers as a sub-field; (c) add a third identity axis for the platform. **Cheap-veto
ASSUMPTION** — nothing built now depends on it, and (a) is the option that leaves (c) reachable.

---

## QB14 — PRD open items rows 12–15

**VERDICT: PARTIAL** across all four rows, with the split below.

### Row 12 — the node-phase position-safety cluster (`prd.md:673`)

**(a) Stop-out taxonomy vs sizing — HALF-RATIFIED.**
*Closed:* the **bench** half. AD-41/CT-29 give the predicate `realized_r <= -q`, and
"breakevens never count; scratches/partial losses don't count by default; a forced flat counts only if
it realized a qualifying loss" (`docs/scenarios/SCN-0011-qualifying-loss-bench.md:35-40`); the
disposition vocabulary is `qualifying_loss_exit | scratch-or-partial-loss | breakeven` (`ct-29:54`);
"stop-out" is banned as a bare word, `venue_liquidation` reserved for venue margin liquidation
(`ct-29:25`).
*Open:* the **sizing** half — whether a breakeven exit or a forced flat feeds the measured loss rate
that the money ladder divides by. PE-3, verbatim: "Whether a BE-out counts is undefined" — "the breaker
counter cannot be implemented correctly until ruled on"
(`workroom/reference/10-dpr-prs-bench-dig.md:142`).
*And a trap worth surfacing:* the symbol **`B`** is both the bench threshold and a divisor in FORM-0004
/ FORM-0006 — "Changing the how-many-losses-before-bench number therefore silently resizes every seat"
(`10-dpr-prs-bench-dig.md:100, 188-190`).

**(b) Position fate at money boundaries — MOSTLY RATIFIED, accounting open.**
*Closed:* "every other money boundary (rollover, sweep, re-seed, paper flip) **leaves positions
alone**" (`tracker/trading-node-notes.md:56`); "A boundary event never closes a position and never
re-bases a frozen R" (`docs/glossary.md`, treasury boundary event). Only the kill line auto-flattens.
*Open:* how open unrealized P&L enters a sweep. The interim ruling is PE-7-neutral: no automatic
position action, open positions force the reconciliation verdict toward `unknown` (K-36,
`trading-node-delta.md:89`).

**(c) Dynamic SL/TP grammar — RATIFIED for V1, nothing open.**
AD-34/DEC-0148: "V1 dynamic SL/TP = move-to-breakeven ratchet only", risk-reducing, per-Book
configurable (`tracker/trading-node-notes.md:62`); `registry:breakeven_ratchet_trigger` is flagged "V1
only dynamic SL/TP" (`variables.yaml:713`), offset "risk-non-increasing vs frozen distance" (`:724`).
K-35 places the grammar in Book money-rules with BMS configuration authority and adapter enforcement; a
globally uniform stop service is a DROP (D-07). And OR-01 is ratified: a bot may propose **any**
risk-non-increasing tighten (never a price) — "breakeven only" governs the Book's own *automatic* stop,
a separate machine (`qa/_trace/rulings-corpus-verdicts.md:16-49`).

**(d) Amendment idempotency threshold — OPEN, cheaply.**
Command-identity idempotency is already ratified (same `fp1` = idempotent accept). What is missing is
the *suppression* threshold that stops a tick storm producing a hundred near-identical amends.

### Row 13 — atomic decision-plus-evidence commit vs the store seam (`prd.md:674`)

**PARTIAL, and the corpus already offers the shape of the answer.** Ratified: a control action is
journaled **before** dispatch and a storage failure blocks dispatch (`ct-25:25-26`); CT-20 declares
each multi-room write as one ordered unit typed `atomic | ordered-with-recovery`, and a partial write is
a `storage failure` blocking the command stream (`ct-20:25, 42`); one-writer-per-stream; recording
precedes interpretation. The old build demanded true atomic dual-write inside one SQLite transaction
(K-10/K-47, `trading-node-delta.md:48`) — `RECONFIRM`, and the two-node PostgreSQL topology it lived in
is dead. So the corpus does not demand one global atomicity rule; it demands a **declared** mode per
write, and never a silent third.

### Row 14 — news-provider selection evidence (`prd.md:675`)

**OPEN — an operator item by ruling.** Evidence on record: Forex Factory free weekly JSON as primary
(rate-limited ~2 downloads / 5 min); FMP, Trading Economics, FXStreet as impact-carrying fallbacks;
EODHD disqualified (no impact field); scraping rejected. Compilation invariants already ratified in
stricter form than the old build: instrument scope comes from dated per-instrument currency-exposure
records and **reading a currency out of a symbol is prohibited**
(`docs/scenarios/SCN-0008-pair-scoped-news.md:25`), windows widen-never-shrink, and a failed calendar
refresh blocks fail-closed — "there is no live skip button" (`ct-31:24, 47`). The **legal archiving
posture** remains an open operator item recorded rather than resolved
(`docs/components/calendar-feed.md:39`; DEC-0119).

### Row 15 — deep-history acquisition (`prd.md:676`)

**OPEN, and not node-blocking.** Dukascopy is the ratified first source, personal-use posture closed
(DEC-0170: "QMX's downloaded market data is used at a personal level only … If a future posture ever
exceeds personal use … the question reopens as its own sitting"). TrueFX and HistData are recorded
companions with a provenance caveat (R-18 recorded TrueFX internal-only / no-redistribution and
excluded HistData in one story). Venue-only backfill is rate-capped into unviability (5 req/s
historical, one-week tick-span cap), so the recent window needs a continuity bridge.

### What the spine should bind

- Bench predicate and sizing loss-rate consume **one** disposition vocabulary, so a single ruling covers
  both; and the bench threshold is split from the money-ladder divisor as two separately named
  variables.
- Money boundaries never touch positions; only the kill line flattens.
- V1 dynamic protection = breakeven ratchet only, risk-non-increasing against the frozen distance.
- Every decision-plus-evidence write declares `atomic` or `ordered-with-recovery`, evidence-first
  ordering always, partial write = storage failure blocking the command stream.
- News windows fail closed with no skip button; provider choice recorded as configuration.

### Operator questions (residues 16–19)

**Q-QB14a.** When a trade is closed at break-even rather than at a loss, we have already ruled it does
not count toward benching a bot — but we have not said whether it counts toward the measured "how often
does this bot lose" figure that sets position size. **Recommended: use the same rule for both — only a
real losing exit counts, break-evens and scratches count for neither** — because one vocabulary means
one rule to get right, and a bot that scratches out of trades should not be sized as though it were
losing. Alternatives: (b) count break-evens in the sizing figure but not the bench count; (c) count
everything that is not a winner. **Cheap-veto ASSUMPTION.** Separately and more urgently: the "how many
losses before we bench" number currently doubles as a divisor in the position-sizing formula, so
changing it silently resizes every seat — **recommend splitting it into two named settings**, which is
the higher-value half of this answer.

**Q-QB14b.** At the daily rollover we sweep profit out of a Book; if a trade is still open we have to
say what happens to its floating profit. **Recommended: leave the position completely alone (already
ruled), sweep only realised cash, and list the floating profit as a named, explained part of the
difference between broker and our books** — because it keeps the two things apart: money that exists,
and money that might. Alternatives: (b) include floating profit in the swept amount; (c) refuse to
sweep at all while a position is open. **Cheap-veto ASSUMPTION.**

**Q-QB14c.** In a fast market a bot could ask to nudge its stop hundreds of times a second, and each
nudge is a broker request. **Recommended: a per-Book minimum improvement — if the new stop is not
better than the current one by at least that much, we skip it and write down that we skipped** —
because it costs nothing when markets are calm and prevents a self-inflicted flood when they are not.
Alternatives: (b) a minimum time gap between amendments; (c) no limit. **Cheap-veto ASSUMPTION.**

**Q-QB14d.** Our economic-calendar feed decides when the node stops taking trades around news; the free
Forex Factory file is the obvious primary source but has usage limits and unclear terms for storing it
long-term. **Recommended: Forex Factory as primary with one paid fallback, refreshed once a day before
the trading day, and if the refresh fails we block entries rather than trade blind — with the
"can we keep archives of this?" question recorded as still open, exactly as we did with Dukascopy for
personal use only.** Alternatives: (b) go straight to a paid provider with clear terms; (c) use two
free sources and cross-check. **Cheap-veto ASSUMPTION for personal use**; it becomes a genuine question
only if QMX is ever open-sourced or shared.

---

## QB15 — Prediction linter, shakedown, demo registration test; warm-up week vs paper soak

**VERDICT: PARTIAL.** The admission gate is fully ratified. The relationship between the warm-up week
and the paper soak is not.

### Settled — what must run before a Book goes live

**Three layers, no probation, no performance gate:**

> "three-layer admission packet — Layer 1 registration linters …, Layer 2 a technical demo/paper
> shakedown, and Layer 3 one operator signature on one assembled page — plus the CT-32 performance
> evidence, with **no trial period, probation window, or paper-performance gate** and no paper role
> permitted to gate live money"
> — `docs/scenarios/SCN-0007-human-promotion.md:21` (AD-32, DEC-0146)

**Layer 1's prediction linter is pinned to four checks** (DEC-0178, filling AD-32's Layer-1 slot):

> "**(a)** the CT-33 footprint satisfies the Book's `footprint_requirements`; **(b)** the bot's declared
> permitted EXIT-intent kinds are a subset of the Book's `exit_policy` permitted EXIT kinds (`entry` is
> never gated — a zero-exit-kind Book, the honest V1 default, admits entry-only bots); **(c)** the bot's
> family resolves an `exit_policy` entry (explicit or the declared catch-all); **(d)** the bot's stream
> set lies within the binding's declared venue capabilities (CT-18, through AD-29's bind-time check)"
> — `docs/components/qml.md:100`

It "runs statically on demand and at seat time against the CT-28 binding context." The glossary is
explicit that it "passes registration and blocks live binding, **not a performance gate**."

**Layer 2 splits cleanly** — QML owns the pure denial set, AST/import scan, determinism harness,
golden-slice generator and verdict function; the **host** (the node) owns only process spawning and
isolation, so "a bot's conformance verdict is **host-independent by construction**"
(`docs/components/qml.md:96`). Hardened OS-level runtime confinement (seccomp-class on Linux) is "a
named deferred dependency of the node/platform sitting, and V1 does not wait on it"
(`docs/architecture/stack.md:159`; `epics.md:2622-2625`).

**Layer 3** is one operator signature on one assembled page carrying both proofs, the binding identity,
the capability-satisfaction result and the resolved BMS fingerprint; the card carries the Book-definition
fingerprint as an identity field "so a signature can never attest a superseded template"
(`docs/components/qmf-registry.md:56`). The mandatory plain-words summary is itself an identity field —
"the signature attests the exact words the human read"
(`docs/decisions/ADR-0015-registry-records-and-promotion.md:43`).

**The "demo registration/execution test in the UI"** is the operator's own minted idea: "the 'prediction
linter' — a static check showing whether a Book can actually register/execute a given bot, testable
against demo in the UI" (`tracker/trading-node-notes.md:74`). The linter half is now ratified as above.
The UI half is terminal-phase; the node owes a CLI/API door now, per the operator's standing rule.

### The warm-up week and the paper soak are three different things

1. **The first-connection verification suite** — five verify-or-refuse checks, run at first connect,
   before the first command and before any evidence-bearing decode
   (`docs/lenses/ops/runbook.md:65-71`). It **precedes** everything.
2. **The paper soak** — the operator's milestone 1: "paper mode on demo account ~2 days under full
   logging/monitoring" (`architecture-NODE-2026-08-28/.memlog.md`, constraint line).
3. **The warm-up rider** — "The operator's rider is a ~1-week warm-up/observation period before live
   trading (DEC-0135). This runbook authorizes no live trading." (`docs/lenses/ops/runbook.md:80`);
   restated at `tracker/trading-node-notes.md:12, 21` as a warm-up week carrying the empirical checks
   with loud refusals.

So the checks precede the soak, and the soak sits inside the observation period. What is **not** ruled
is whether the ~2-day soak counts toward the ~1-week warm-up or runs before it.

### What the spine should bind

- Three admission layers, in order, with no probation and no paper-performance gate; the four-check
  prediction linter as Layer 1's pinned list, addable never redefined.
- Layer 2's verdict function pure and host-independent; the node supplies only process spawn and
  isolation.
- Layer 3 as one signature on one page whose plain-words summary is an identity field, carrying the
  Book-definition fingerprint.
- The five-check first-connection suite as a hard precondition of the first command.
- Paper before live, with the soak's evidence never gating live money (SCN-0007).

### Operator question (residue 20)

**Q-QB15a.** You have asked for a roughly one-week warm-up before live trading, and separately for a
two-day paper run on the demo account — we need to know whether those are the same week.
**Recommended: treat the two-day paper run as the first two days of the warm-up week, with the broker
checks running throughout and live trading only at the end** — because the checks that matter (daily
boundary, candle basis, clock drift) need days of observation, not a fresh start, and this gets you to
live in about a week rather than nine days. Alternatives: (b) two days paper, then a separate full week
of warm-up (safest, slowest); (c) skip the warm-up week if the two-day soak is clean (fastest, and it
throws away the observation the rider exists for). **Cheap-veto ASSUMPTION.**

---

## Contradictions and tensions surfaced

1. **Drift bands: numbers exist one layer below the ratified text.** `docs/lenses/ops/runbook.md`
   deliberately carries the four band *names* with no numbers; the quadruple 10/25/100/250 ms survives
   only in `time-audit-devops.md:9` (spine planning artifact). No registry variable exists. Treat the
   numbers as RECONFIRM evidence, never as ratified constants (L38/DEC-0157).
2. **Latency: operator ~50 ms vs GitBook 35 / 10–45 / 100 ms.** Recorded unresolved at
   `tracker/trading-node-notes.md:24`; GAP-0013 forbids inventing either. Node budgets are evidence,
   not spine constants (`correlate.md:149`).
3. **Reconciliation verdicts: three vs four.** The node corpus and GitBook use `reconciled | drift |
   unknown` (`05-trading-node-primer.md:294`); ratified CT-20 uses **four**, adding `out-of-lookback`
   specifically so "I cannot see that far back" is never read as "the position closed" (`ct-20:26`).
   **The node must use four.** This is a live correction the node inherits, not a wording difference.
4. **Paper mode: three incompatible readings.** K-25 "Trading paper is ONLY a fail-mechanism surface"
   (`trading-node-delta.md:71`); the data-layer blueprint's "every bot runs its paper twin permanently,
   including while it is trading live" (`09-data-layer-blueprint.md:67`, research synthesis, **not
   ratified**); and the ratified AD-35 standing-evidence state. **AD-35 wins**, and the permanent-twin
   reading is refused by two ratified rules: one active paper-routing target per live binding, and
   `execution_target` resolved **once** at intent mint (`SCN-0006:35-37`) — an intent goes to one place,
   never to both.
5. **World labelling for a replayed live day.** "demo and paper runs are `world = live`" (money-reality
   rule) vs "replay may never write into the live evidence namespace" (time audit). Resolved above: the
   money-reality rule is about a real account; a replay has no venue, so a replayed day is
   `world = replay`.
6. **`daily_dead_zone_width` carries two disagreeing recorded values** — a one-hour table row vs Flow
   9's ~3-hour prose — recorded as a disagreement, never merged (`variables.yaml:669`; `ct-31:52`).
7. **SQS formula status.** SRC-03 memlog entry 118 says "SQS formula stays open pending re-understanding
   pass" while the risk sitting closed it as GAP-0043/DEC-0153 (`sweep-signoff-mechanics.md:220-222`).
   Surfaced, unresolved; the ratified ADR wins unless the operator says otherwise.
8. **CI runs on Linux; the type gate renders Windows; the node's target is Linux.** All four CI jobs are
   `ubuntu-latest`, yet pyright pins `pythonPlatform = "Windows"` and the Ubuntu clean-install smoke is
   deferred "until a remote exists" (`pyproject.toml:307-312, 503-506`). The node runs on the ratified-
   but-unexercised tier-1 leg. First-order gap for this sitting.
9. **A currency conflict that is already closed but reads as open.** The web dossier flags
   `ctrader-open-api==0.9.2`'s hard pin `protobuf==3.20.1` (no cp314 wheels) as "the single largest
   currency-conflict the node spine must resolve." It is already resolved in the repo: the Spotware SDK
   is **reference-only and rejected as a runtime dependency** because "its pinned Twisted reactor is
   platform-imposing" (`DEPENDENCIES.md:11-13, 47`), and `qmf-venue` compiles the Spotware proto
   in-house against `protobuf==7.36.0` with **zero Spotware code running**
   (`packages/qmf-venue/pyproject.toml:9-18`). The spine should record this as settled, not re-litigate
   it.
10. **"One CLI" is scoped narrower than it reads.** DEC-0159 ("one CLI for agents and operator alike")
    and DEC-0185 Ruling C ("QMB's CLI is the single command-line surface") were both ruled inside the
    QMB/QML authoring context. The trading node's operator control door is a separate, unruled surface —
    the Trading Node is "outside QMF V1 documentation scope." The operator's anti-second-CLI lean is on
    the record and should be weighed, but it is not a node ruling.
11. **Notification severity ownership.** GitBook says Notification *proposes* severity while
    `CT-NOTIFY-01` already *requires* `proposed_tier` (C-17); and CT-31 says QMX "mints no severity
    scale" for news, carrying the provider's impact label verbatim and leaving severity→window as a node
    mapping (`ct-31:33-41`). Minor, but it lands on the node.
12. **Two evidence taxonomies to bridge.** The node's five Records streams (`veto_ledger,
    trade_journal, book_journal, ksa_audit_log, correlation_ledger`) and QMF's seven journal event types
    are two vocabularies; CT-25 already carries the mapping table as projection names only
    (`ct-25:20, 47`). The order-path study flags the bridge as "a node-sitting documentation item"
    (`trading-node-order-path-study.md:136`).
