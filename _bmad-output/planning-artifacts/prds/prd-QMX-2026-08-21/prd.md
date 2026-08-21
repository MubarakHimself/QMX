---
title: QMX Platform PRD
status: final
created: 2026-08-21
updated: 2026-08-21
---

# QMX Platform PRD

**Audience.** This PRD is written for the planning chain that follows it —
`bmad-architecture` reconciliation, epics-and-stories, and the factory lanes —
and for agents consuming it alongside the `docs/` knowledge base. It is
deliberately **lean but complete**: every functional requirement is stated at
capability level and cites the `docs/` artifact (component, contract CT-*,
ADR-*, SCN-*, constitution law L*) that holds the ratified depth. The PRD never
restates what a cited artifact already binds; where PRD text and a cited
artifact disagree, the cited artifact wins.

Two tags mark provenance: `[ASSUMPTION]` is an inference awaiting the
operator's confirmation; `[MINED]` is a carry from the pre-QMF versions —
corpus-compatible direction that binds nothing until its phase's planning
ratifies it. PRD vocabulary binds to `docs/glossary.md` verbatim; the terms
this document leans on hardest are **Book** (chartered gatekeeper owning
sizing and exits), **BMS** (per-account accounting/constraint layer that never
trades), **charter doors** (a Book's admission checks), **tunnel entry**
(running a bot through QMB's run loop — open to plain Python, unlike governed
seats), **benched** (a seat suspended by qualifying-loss count, a read-time
fold), **room-roles** (the seven per-world storage partitions), **fidelity
taint** (fills labeled `optimistic` until GAP-0048), **SQS** (Spread Quality
Sensor — historical session-window average spread over current live spread,
DEC-0153), **footprint** (a bot definition's canonical consumption
manifest), **kill-switch vs kill-line** (global halt vs per-Book floor).

**Standing status.** Authority is checkable from the repo:
`_docwork/stage_state.yaml` → `ratification.status`. While it reads
`provisional`, nothing anywhere authorizes implementation or live money
(L29). Once it reads `ratified`, the operator's 2026-08-21 sign-off has
landed (given as a conditional go-ahead in the PRD session, contingent on an
independent contradiction sweep passing) and the corpus carries documentation
authority — implementation authorization still arrives only through the
factory pipeline. Owner: the operator. See Open Items row 1.

---

## 1. Vision

QMX ("Quant Mind") is a deterministic, self-governing automated-trading
platform built and operated by **one person** — the operator — not offered to
end traders. Autonomous **bots** are the only things that touch the market;
every trade intent passes through a **Book**'s charter doors; a **BMS**
accounts for and constrains Books without ever trading; the operator sits at
the top of the authority chain (bot → Book → BMS → operator) and is the only
entity that can promote anything to live money. The platform runs unattended:
the operator's in-flight powers are exactly three — resurrection (the only
de-escalation authority), the periodic review, and ratification/promotion
(GitBook baseline; ADR-0008; L17, L36).

The end-state product is a **Bloomberg-terminal-style desktop application**
(the QMX terminal) paired with a **VPS-resident trading node** that trades
continuously, and — in a later phase — **agent workers** that operate the
platform's libraries and CLIs on the operator's behalf.

QMX is being rebuilt from a re-documented foundation rather than from the old
codebase. The operator's framing: *we are building React and its documentation
before we build the website.* The framework layer (QMF) and its first two
application-layer products (QMB, QML) are architecturally done in `docs/`; the
platform surfaces above them are phased.

**V1 goal: a stable platform foundation** — QMF's seven packages, the
off-roster `qmf-calendar-forex` extension, the first adapters (Dukascopy, the
news-calendar feed, cTrader), plus QMB and QML — buildable by the factory,
with every contract implemented and every invariant enforced. The terminal,
trading node, and agentic system are named phases, not V1 deliverables.

## 2. Platform composition and delivery phases

| Layer | What it is | Corpus status | PRD treatment |
|---|---|---|---|
| **QMF** (Quant Mind Framework) | Contracts-first pure-Python toolbox: 5 libraries + 2 edge modules. Explicitly not an application — no loop, scheduler, UI, or live runtime (L7, L13, L14; ADR-0002) | Architecture ratified into `docs/` (AD-1..41) | Full FRs (§5 A–F) |
| **QMB** | Experimentation/backtesting library + CLI on QMF; backtesting is its verification stage | Spine B-1..B-15 + direction DC-1..5 ratified by delegation; the 13 `spec-*` documents are intake dossiers — the spine wins where they disagree | Full FRs (§5 G) |
| **QML** | Bot-authoring library on QMF; authors CT-33 bots + CT-34 confluence | Architecture ratified (QL-1..10) | Full FRs (§5 H) |
| **Quant Mind trading node** | Unattended live runtime on a VPS (KSA, Book/BMS runtime, order path) | GitBook design baseline; build not started | Capability outline only (§6) |
| **QMX terminal** | Desktop application — the operator's Bloomberg-style surface | Not yet designed | Capability outline only (§6) |
| **Agentic system (QMA)** | Agent workers operating the platform (local or server-sandboxed) | Deliberately unplanned; own kernel-first planning track | Named phase boundary only (§6) |
| **Simulator UI, consumer MIS product** | Deferred consumer products (ADR-0011); distinct from the node's own MIS-Live labeler layer (§6) | Deferred | Out of V1 (§7) |

**Delivery sequence (operator-ratified 2026-08-21).** Phase 1 — everything in
`docs/` and `_docwork/`: QMF + QMB + QML through the factory ("why would you
build something before the framework that is meant to build it comes in").
Phase 2 — the trading node, with a high chance it is rewritten using QMF and
everything built before it. QMA runs on its own track and requires a
different level of attention; it is still in research and ideation has not
begun. [ASSUMPTION: the terminal's placement after the node (Phase 3) remains
inferred, not ratified.]

One sequencing constraint for epics-and-stories [MINED]: the cTrader
capability probe (CT-18 verify-or-refuse) belongs among the earliest factory
work units — venue feasibility (lot rounding, minimum lot, feasibility clamp,
the shape of the capability declaration) cannot be designed on paper and can
invalidate upstream assumptions.

## 3. Users and operating model

- **The operator** (sole human user): configures, ratifies, promotes, reviews.
  Non-programmer; interacts through the terminal (later), CLIs/notebooks (now),
  and ratification workflows. Everything configurable must be UI-editable —
  numbers are evidence, never constants (L38).
- **Agents** (secondary, growing user class): consume the Python APIs and the
  QMB CLI; later run as governed workers in the agentic phase. The platform
  must stay agent-legible (typed refusals, machine-readable artifacts,
  deterministic identity) without ever boxing out plain-Python human use.
- **Bots** (in-platform actors, not users): the only market-touching entities;
  governed by Books, never by direct operator action.

**Unattended doctrine.** No intraday human judgment. Notifications must never
create intraday decision loops. Only a human-signed promotion occurrence
crosses into live money (SCN-0007; ADR-0015; L17).

The notification constraint, made concrete [MINED]: notifications fire only
on a closed, ratified event-class allow-list — sweep, re-seed, refund,
kill-switch/KSA events, and supervision fail-closed; everything else is
console evidence, never a push. Two-plane rule: authoritative system records
(journals, veto ledger, lineage) and operator notification delivery are
separate layers with separate policies — losing a notification never erases
the underlying evidence, and the notification channel is never a permission
path back into live trading. Delivery mechanics (channels, retries, dedupe,
quiet hours, credentials) stay deferred to the node/terminal phases.

Forward-compatibility hook [ASSUMPTION — operator to confirm]: one primary
operator today, possibly a small team (~3) later — so action attribution
stays named and no surface hard-bakes an anonymous single-user assumption.
No collaboration features now.

## 4. Operator journeys (captured from golden scenarios)

The corpus's golden scenarios are the ratified journeys; the PRD lists the
load-bearing ones rather than re-authoring them:

- **Promote a bot to live** — human-signed promotion attesting the record's
  fingerprint; no agent or test result can do it (SCN-0007). [MINED] The
  promotion click re-runs its full precondition battery server-side against
  fresh state — displayed-eligible is never a guarantee and stale evidence
  never authorizes; the crossing is a node-initiated pull, idempotent by
  artifact key, landing the unit ADMITTED (no intents, no ledger) with live
  activation a later, separate boundary.
- **Run the periodic review** [MINED] — the named weekly ritual (Sunday
  review) and the retirement decision (sunset review), both operator power
  actions fed by read-model evidence: performance explanation,
  footprint/decay sensing, reconciliation status.
- **Run a backtest** — an agent or the operator invokes the QMB CLI; the
  config fingerprint is the run id and the ledger key; results carry fidelity
  taint until GAP-0048 closes (SCN-0012).
- **Survive venue uncertainty** — a lost order submission resolves to UNKNOWN
  and blocks the command stream until explicitly reconciled (SCN-0005).
- **Flip a Book to paper** — a dated binding-epoch change, not a new object
  (SCN-0006).
- **Ride out news** — pair-scoped news windows block entries fail-closed,
  live and paper alike; risk-reducing acts always pass (SCN-0008, SCN-0010).
- **Correct bad source data** — corrections append; nothing overwrites
  (SCN-0002).
- **Restore from disaster** — recoverability is claimed only through verify
  primitives (SCN-0004).

## 5. Functional requirements — Phase 1 (V1)

FRs are numbered globally and grouped by capability area. Each is a binding
capability; its cited artifacts carry the detail. **For epics-and-stories:
each FR's cited artifact is the epic boundary and the source of its
acceptance criteria; where an FR cites a `spec-*` intake dossier, that
dossier is one epic** — FR granularity here is deliberately coarser than
epic granularity, so never size a lane by counting FRs.

### A. Domain foundation (qmf-core)

- **FR-001** All money, price, and quantity values are exact scaled integers;
  binary floats are banned on the money path and treated as a taint. (CT-01;
  ADR-0013)
- **FR-002** All timestamps are int64 UTC nanoseconds with versioned trading
  calendars; nothing below the composition root reads the system clock — time
  is injected. (CT-02; ADR-0013)
- **FR-003** Instrument identity is an opaque, never-parsed
  `(venue, symbol)` pair. (CT-03)
- **FR-004** Every public operation returns value-or-refusal using the seven
  typed refusal categories; refusals are returned, never raised. (CT-04;
  ADR-0013)
- **FR-005** Every governed artifact carries a deterministic `fp1:sha256`
  fingerprint; identity rides two version ladders (meanings never mutate,
  history stays forever readable); results are labeled with their `world`
  (live / replay / simulated), and `world=simulated` is reserved-unusable in
  V1. (CT-05; AD-spine)

### B. Identity, lineage, and promotion (qmf-registry)

- **FR-006** Per-kind registration records are keyed on fingerprint, giving
  deduplication by construction. (CT-06)
- **FR-007** Provenance is captured as append-only typed lineage edges that
  are never rewritten. (CT-07)
- **FR-008** The registry persists through qmf-data only — no database
  server; registry→data is the single ratified inter-library dependency edge.
  (CT-09; L30)
- **FR-009** The only path to live money is a human-signed promotion
  occurrence attesting the record's fingerprint, with a mandatory plain-words
  summary as an identity field. (ADR-0015; SCN-0007; L17)

### C. Evidence and data (qmf-data and its internal seams; sources)

`qmf-data-store`, `-backup`, and `-ingest` are internal seams of `qmf-data`,
not roster peers — they do not enlarge the seven-package roster
(overview.md).

- **FR-010** Market and reference data lands as bitemporal source
  observations; corrections append under revision keys and never overwrite.
  (CT-10; SCN-0002)
- **FR-011** The append-only evidence store partitions into seven room-roles
  per world; cross-world reads are refused; raw evidence is retained forever.
  (CT-11; L18)
- **FR-012** Research access enforces the 12-month no-peek seal and
  fingerprinted train/validation/holdout splits; the sealed holdout is
  excluded from default access at every boundary. (CT-11, CT-12; SCN-0003;
  L19)
- **FR-013** Durable journals carry the seven event types in per-writer
  gapless streams, with entity projections (logbooks) derived at read time.
  (CT-13)
- **FR-014** Nightly encrypted off-machine backup with first-class restore
  and verify primitives; recoverability claims come only from verify.
  (CT-14, CT-26; SCN-0004; L18)
- **FR-015** External-source intake is idempotent through the CT-15 adapter
  seam. (CT-15)
- **FR-016** Persistence rides a dependency-free store seam over swappable
  local engines; no DB server anywhere in V1. (qmf-data-store)
- **FR-017** Dukascopy is the first historical tick source (download-once;
  personal-use licensing honored — no redistributed corpus). (dukascopy;
  QMB data-mgmt spec)
- **FR-018** A news-calendar feed is ingested as a governed source powering
  pair-scoped news windows; every import is journaled, and a failed refresh
  degrades visibly to the ratified fail-closed block — it never silently
  opens. (calendar-feed; SCN-0008)

### D. Analytics (qmf-indicators, qmf-structure; qmf-calendar-forex off-roster)

`qmf-calendar-forex` sits outside the seven-package roster on its own SemVer
ladder (qmf-calendar-forex.md) — a packaging fact the factory must not
flatten.

- **FR-019** Indicators run in two modes — batch and streaming — with
  guaranteed equivalence, as-of-only alignment, and TA-Lib as canonical
  arithmetic. (CT-16; ADR-0006)
- **FR-020** Market structure is expressed as causal, append-only,
  look-ahead-safe chart-object families. (CT-17)
- **FR-021** A forex market-hours calendar ships as the first CT-02 calendar
  provider. (qmf-calendar-forex)

### E. Venue boundary (qmf-venue; cTrader adapter)

- **FR-022** Venue capabilities are discovered through the two-artifact
  verify-or-refuse mechanism before any command is accepted. (CT-18)
- **FR-023** Venue commands come in exactly five kinds under the four-outcome
  law: timeout is not rejection, UNKNOWN is a state not an error, and an
  UNKNOWN blocks its `(venue, account)` command stream until explicit
  reconciliation; the platform never self-clears, auto-retries, or
  auto-flattens. (CT-19; SCN-0005; L35)
- **FR-024** Venue events are recorded before they are interpreted;
  reconciliation gates the command pipe only — market data keeps flowing.
  (CT-20)
- **FR-025** Credentials are handled as secret references, never values, and
  never leave the connection manager. (CT-21; L34)
- **FR-026** cTrader Open API is the first venue adapter behind the
  venue-neutral port; the platform stays venue-blind above the port.
  (ctrader; ADR-0007)

### F. Risk and governance (qmf-risk)

- **FR-027** Books are chartered gatekeepers: every bot trade intent passes a
  Book's charter doors; the BMS (one per account, serving many Books)
  accounts and constrains but never trades, sizes, or reaches inside a Book.
  (CT-22, CT-27; ADR-0008)
- **FR-028** The Book owns sizing: `requested_r` is Book-resolved; an
  admitted entry requires a declared full-loss price or admission refuses;
  admission is three technical layers with no probation and no
  paper-performance gate; R is one relationship with three typed faces,
  frozen at admission. (CT-23; ADR-0010)
- **FR-029** Paper is a Book-level standing evidence state entered by a dated
  binding-epoch change. (CT-24; ADR-0009; SCN-0006)
- **FR-030** Risk journals project Book/BMS state at read time. (CT-25)
- **FR-031** A bot binds exactly one Book; bindings are dated epochs.
  (CT-28)
- **FR-032** Exits are Book-owned and risk-monotonic; bots may only propose
  risk-reducing exits; every virtual close mints exactly one exit record.
  (CT-29; L39)
- **FR-033** Controls obey the exit-preservation invariant — no control ever
  blocks a risk-reducing act; kill-switch (global) and kill-line (per-Book
  floor) are distinct; same-tick actions arbitrate by BMS rank on one stream;
  news windows block entries fail-closed by instrument scope. (CT-30, CT-31;
  SCN-0008, SCN-0010; L39)
- **FR-034** Performance measurement publishes and never acts; no composite
  score gates money; benching (e.g. by qualifying-loss count) is a read-time
  fold. (CT-32; SCN-0011)
- **FR-035** The numeraire is USD-only in V1; every risk/sizing/window/SQS
  value is a UI-editable configurable with no spine constant, and a blank
  value blocks live money while allowing registration and non-live binding.
  (variables registry; L38)

### G. Experimentation and backtesting (QMB)

- **FR-036** One event-slice run loop serves backtest, replay, and live —
  never forked; each run consumes exactly one resolved, fingerprinted run
  config; the config fingerprint is the run id and the ledger key; `world`
  derives from data provenance, never from a flag. (QMB spine B-1..15;
  SCN-0012)
- **FR-037** Replay backtests support warm-up, deterministic reproduction
  (same config → same results), intra-bar fill fidelity, and cancel/observe
  while running. (spec-backtest-loop)
- **FR-038** Multi-symbol / multi-timeframe permutation sweeps run the
  Cartesian space with a pre-flight run count, one labeled run per combo, and
  cross-run ranking. (spec-multi-routes)
- **FR-039** Parameter-optimization Studies offer a typed search space,
  objective plus constraints, train/test split discipline with fingerprinted
  split manifests, a TPE-class default sampler, resume, cost estimation, and
  an anti-overfit sensitivity report. The locked-validation third split and
  grid/Euler sampler modes are explicitly deferred out of V1 by the ratified
  spine's Deferred table. (spec-optimization intake; QMB spine)
- **FR-040** A robustness toolkit ships the ratified B-14 ladder: backtest,
  optimize, Monte Carlo (trade-shuffle and candle-perturbation), the
  pre-build rule-significance gate, and walk-forward. Threshold values and
  pass batteries (the intake dossier's MC-1000 / PBO / CSCV S=16 candidates)
  stay deferred to the GAP-0048/0049 sittings. (QMB spine;
  spec-mc-significance intake)
- **FR-041** Synthetic data generation is claim-class labeled
  (infra-stress / robustness / logic-smoke) and never validates edge.
  (spec-synthetic-data; SCN-0009; L20)
- **FR-042** Data management covers download, verify, gap-check, and catalog
  by `(venue, symbol, window, side)`, calendar-aware, behind a
  ship-no-corpus licensing gate. (spec-data-mgmt)
- **FR-043** Every run emits one canonical machine-readable result artifact
  (it IS CT-32) plus chart series as data, never images; the metric set
  includes QMX-native suppression/veto accounting; no composite score.
  (spec-reports; CT-32)
- **FR-044** Fill/slippage/fee modeling (synthetic spread, FX slippage,
  commissions, daily swap) carries fidelity labels; all fills are
  `optimistic`-tainted and no verdict-bearing backtest ships until GAP-0048
  closes. (spec-fill-fees)
- **FR-045** Runs execute process-per-run under a governed concurrency cap
  with backpressure and per-run isolation. (spec-concurrency)
- **FR-046** QMB is reachable through thin doors: the **`qmb` CLI** — the
  platform's single command-line surface (DEC-0185 Ruling C; the `qmx`
  command name is superseded per DEC-0159), Lean-CLI-inspired and
  agent-facing — plus the Python API and notebooks (`uv add qmb`,
  `uv add qml`), and an optional MCP door that is never required; plain
  Python remains first-class. (spec-cli-config; DEC-0159, DEC-0185)

### H. Bot authoring (QML)

- **FR-047** A governed bot is exactly two artifacts: a CT-33 declaration
  plus plain-Python logic; plain-Python bots stay first-class forever — the
  `.qml` DSL is not revived in V1. (CT-33; QL-spine; ADR-0018)
- **FR-048** Conformance is technical-never-performance and is the ticket
  into governed evidence citation and Book seats — never into tunnel entry.
  (ADR-0018)
- **FR-049** Confluence definitions are authored as CT-34 artifacts.
  (CT-34)
- **FR-050** QML defines the bot runtime protocol that QMB (and later the
  trading node) hosts. (QL-spine)

## 6. Future-phase capability outlines (no V1 FRs)

These phases are in-scope for QMX the platform but carry no FRs in this PRD;
each gets its own planning pass before the factory touches it.

**Quant Mind trading node (Phase 2).** Unattended VPS runtime hosting the
Book/BMS runtime, the order path over qmf-venue, KSA (escalate-only global
protection; only operator resurrection de-escalates), sizing-ladder
evaluation, ledger↔broker drift kill, retry/pool constants, and MIS-Live —
the node-runtime labeler layer computing market-condition signals,
compute-once, for Book and KSA. Design baseline: the GitBook (authoritative
for risk/sizing/live per L2/L37). Explicitly out of QMF scope by ruling;
build not started, and the operator expects it to be **rewritten on QMF** and
everything built before it. Operator note (2026-08-21): the node is the
operationally intense phase — MIS carries machine-learning instances with
training, shadow-rollout, and retraining cycles — which is why the DevOps
success lens (§9) is primary.

One piece of node doctrine is already operator-ratified (2026-08-21, resolves
DEC-0049): *detector-pause scoping* — on a rare data-quality or drift event an
automatic detector may pause, as an entry-blocking control at the narrowest
affected scope (instrument, currency cohort, Book, venue/broker, or system),
never wider and never touching positions or exits (L39); the inform-vs-pause
posture is UI-editable per L38.

Mined node doctrine — all [MINED], to ratify at node planning:

- *Startup and recovery ordering.* A deterministic cold-start preflight gate
  runs before any state mutation (host/disk/network/pinned-version checks,
  fail-closed with a typed failure id), then a fixed per-Book order: connect
  → reconnect gap recovery (fetch deals/positions since the last-seen
  execution event, commit recovered fills before reporting healthy) → missed
  rollover catch-up (boundary equity reconstructed from journals, sweep
  journaled as a correction-style append) → protection-state projection
  (breakers, budgets, exposure rebuilt from journals) → readiness gates →
  the sequencer accepts intents. The invariant: a crash never resets safety
  counters, because there are no safety counters — only journal projections.
- *Drift is reconciled-explained, never raw equality.* Broker-vs-virtual
  divergence decomposes into journaled components (swept-but-unwithdrawn
  cash, re-seed remnants, open unrealized P&L); only the residual is drift.
  Verdicts: reconciled | drift | unknown. Unexplained live drift halts
  trading, and restart is not permission to resume — a fresh reconciliation
  review is. The paper/demo binding is excluded from the live drift check.
- *Rate limits are a design input.* One connection pool per account binding,
  per-account command affinity, token-bucket limiting — caps are per
  connection at protocol level, so synchronized bursts (mass
  invalidation-close plus re-amend) need sharding or a shared bucket; this
  is also the future multi-account load-balancer seam.
- *Fail-closed stand-down is an alive state.* Past a crash-loop threshold the
  process boots into stand-down: sequencers refuse-and-journal, adapter
  connections quiesce and drain, and the operator-powers surface keeps
  serving — resurrection stays reachable exactly when needed. Paired rule: a
  protection transition counts as enforced only after the account's
  connections have quiesced and drained.
- *Shadow lane shape.* Candidate labeler/model versions run as near-real-time
  replay over the captured canonical feed, off the hot path, to their own
  manifest prefix, never to live consumers, evaluated over one full
  affected-Book cycle; promotion is ratification → version bump →
  re-certification. A recovered or pre-trained model carries no authority
  without fresh ratification (parameter identity + training + shadow
  evidence). Training is an offline job — it may seed its RNG, provided the
  seed is recorded; the no-ambient-randomness invariant binds the live
  runtime.
- *The always-on evidence tier.* The node phase implicitly needs a placement
  and authority boundary for archive, captured feed, heavy analytics, and
  the shadow lane — explicitly not a database server and not a second
  writer: the hot path never blocks on it (only disk physics fail-closes
  trading); sync is one-way, watermarked, idempotent, resumable, under
  verify-before-purge (the hot side purges only what the evidence side has
  durably persisted AND content-verified); recovery re-requests carry
  watermarks only, never payload backward; the only reverse crossing is the
  click-gated promotion pull. A placement boundary, not a mandate for
  separately deployed services.

**QMX terminal (Phase 3).** The Bloomberg-terminal-style desktop application:
operating Books and bots, browsing evidence/journals/lineage, editing every
`configurable: true` variable (this is where the L38 UI-editability law lands
as a surface), ratification and promotion workflows, and the charts/reports
front-end consuming QMB's renderer-agnostic chart data.

Mined console spine — all [MINED], to ratify at terminal planning:

- *UI-only, never a second system of record.* Business authority,
  persistence, and command validation stay server-side; the desktop app
  holds no trading secrets. It is not a manual-trading or generic
  market-analysis terminal — optimize for system operation, safety,
  evidence, and repeated expert use; unattended-by-default UX that never
  invents an intraday human-control loop.
- *Exactly two channels.* An evidence read channel and a powers action
  channel (resurrection, ratification/promotion, review actions), with
  evidence review and command execution visibly distinct steps.
- *Anti-goals, carried verbatim:* no direct manual-trading surface; no
  generic LIVE/PAPER toggle; no single global health indicator hiding
  independent failure domains; no stale evidence authorizing an action; no
  editable setting without registry-backed configurability; no optimistic
  command success without server validation and evidence; no
  Prometheus/Grafana clone; no assumption that a future venue is recolored
  forex.
- *State independence and read provenance.* Safety, execution readiness,
  connection, reconciliation, data freshness, lifecycle, and sync are
  independent states that never collapse into one health color; requested
  protection state displays separately from enforcement completion. Every
  important read reveals authority source (live-authoritative vs replicated
  evidence), source time, receive time, and watermark.
- *The read data-plane.* A family of publish-never-act read models — each
  budgeted, authority-free, returning refusals as evidence: Records Read API
  (journals, veto evidence, cycle events), deterministic replay, performance
  explanation, decay/footprint-drift sensing, archive access. The concrete
  back end for "browsing evidence/journals/lineage".
- *Settings are evidence-scoped, not a boolean.* Three scopes render
  distinctly — system settings (secrets and bindings, console-managed, never
  registry numerics), component settings (registry), instance values
  (registry under instance ownership). A non-configurable value renders
  read-only; a null renders *unresolved*, never as an editable default;
  measured/provisional values never masquerade as settings; a provisional
  value requires an explicit operator countersign before live; a value fixed
  within an active cycle (the kill line) is not editable mid-cycle.
  Book↔account bindings are console-configured, mutable, journaled, in
  system-settings scope. (Note: `docs/registry/variables.yaml` carries
  `configurable` but no value-status field — the terminal cannot decide
  editability from data until it does.)
- *Promotion evidence panel and per-bot dossier.* The promotion click
  presents a conformance/certificate summary, pair/session overlap with the
  live roster, and footprint similarity to existing bots — recomputed
  against the fresh roster at click time, because the human performs the
  dedup and correlation judgment V1 deliberately declines to automate. Every
  artifact about a bot (declaration, run results including failures,
  reports, notes) attaches immutably to its bot id from entry onward.
- *Venue containment.* Future venue experiences share the product shell via
  a venue selector, but each venue may carry a different information model;
  forex works completely on its own, and no future venue arrives as
  "recolored forex" or forces false shared concepts into the forex UI.

**Agentic system (QMA — named phase, own track).** Agent workers operating
the platform through its typed, machine-readable doors (the `qmb` CLI,
Python API, optional MCP), running locally or in server sandboxes (Modal/E2B
class — direction only, see addendum). Core to QMX's end state, and still in
**research — ideation has not begun** (operator, 2026-08-21); it requires a
different level of attention and gets its own planning track. Old-version
agentic requirements are scrapped, not carried. Kernel-first, step-gated
planning in its own workroom track. One track input [MINED], recorded not
adopted: an earlier ruling set the agentic data-egress boundary as pull-only
access to curated datasets, with no live-service surfaces exposed to agents
at all — a harder starting governance stance for the QMA track to weigh
against the current typed-doors posture when ideation begins.

**Deferred consumer products.** Simulator UI and MIS remain deferred per
ADR-0011.

## 7. Out of scope (V1)

- Trading node runtime and all its constants (kill-switch matrix, severity
  policy, retry/pool numbers, RPO/RTO); deploy/infra/ops.
- Any UI (terminal, Simulator, charts front-end) beyond QMB's chart-data
  contract.
- Agentic runtime and MCP specifics beyond the optional QMB door.
- `world=simulated` (reserved-unusable until GAP-0048's fidelity taxonomy).
- Margin-aware sizing, multi-currency/non-USD numeraire, prop-firm Book
  extension, L2 depth vocabulary, `close_partial`, swap-Wednesday handling.
- Futures and options (permanently excluded); any asset class beyond the
  seeded forex vertical.
- ML extras, live/streaming charts, crisis/regime windows, strategy-capacity,
  multi-objective optimization, the locked-validation third split, grid/Euler
  sampler modes, and all robustness threshold values / pass batteries
  (MC-1000, PBO, CSCV — GAP-0048/0049 sittings) — all deferred by QMB
  rulings.
- Donor code — the platform is built-our-own; external references are
  mechanism donors only.

## 8. Non-functional requirements

- **NFR-01 Environment.** CPython 3.14; tier-1 OSes Windows 11 x86-64 and
  Ubuntu LTS x86-64. (ADR-0012)
- **NFR-02 Quality gates.** ruff + pyright-strict + pytest; coverage floor
  80%, 100% branch coverage on CT-01/CT-02 modules; three event-bound gate
  tiers. (ADR-0012) [MINED] Two static scanners ship as tier-1 gate
  artifacts, making FR-001/FR-002 mechanically enforceable: a money-path
  scanner (declared money-name fragments crossed with a forbidden AST set —
  float calls/literals/annotations, division on a money path — plus an
  explicit allowlist) and an ambient-nondeterminism scanner (forbidden calls:
  `datetime.now/utcnow`, `time.time/monotonic/perf_counter`, `random.*`,
  `secrets.*`, `np.random`, per-path allowlist).
- **NFR-03 Determinism.** Same inputs produce the same fingerprints and the
  same results — replay reproducibility is a platform property, not a QMB
  feature. (CT-05; B-spine)
- **NFR-04 Performance.** Measure-then-budget: no invented numbers; benchmark
  speed and peak memory at the 10/100/200 marks against the ~40-bot reference
  workload; the only stated constraint is qmf-core import under ~1s.
  (ADR-0014)
- **NFR-05 Security.** Secrets as references only, tier-1 scan gate,
  encrypted off-machine backup; credentials never leave the connection
  manager. (CT-21, CT-14; L34)
- **NFR-06 Durability & compatibility.** Evidence append-only and retained
  forever; per-contract integer format versions keep old evidence readable
  forever. (CT-11; ADR-0012)
- **NFR-07 Configurability.** `configurable: true` means UI-editable, always;
  recorded numbers are evidence, not authority; blank risk values block live
  money. (variables registry; L38)
- **NFR-08 Auditability.** Journals, lineage edges, and memlogged decisions
  make every state change reconstructable; corrections append. (CT-07,
  CT-13)
- **NFR-09 Concurrency posture.** QMF spawns no concurrency; applications own
  it (QMB's governor is the V1 instance); async only at the venue edge.
  (ADR-0014)
- **NFR-10 Operability & deployability (operator-ratified 2026-08-21).** The
  platform works out of the box: `uv add` installation, no database server,
  no Docker requirement for QMB; a single person can deploy, monitor, and
  repair it — when something breaks, diagnosis and fix must not demand more
  than the one-man army running it. Monitoring and evaluation are built in,
  not bolted on. (operator ruling; qmf-data-store; spec-cli-config)
  [MINED] The plain-words shipment criterion: install, start, stop, back up,
  and recover from **one canonical checkout** — the operator never hunts
  across folders or reconstructs Git state. Serve-both-layers: the
  monitoring/evaluation substrate stood up for QMF/QMB is the same one that
  later serves QMA — never two stacks — and any external plane
  (Prometheus/Grafana class) is zero-authority: it consumes exported
  evidence (DEC-0112) and never becomes a control path ("an alert is
  evidence, not permission", DEC-0041).
- **NFR-11 Failure-register discipline.** [MINED] Every designed failure
  mode ships a register entry: failure class, detection, auto-recovery/retry
  semantics, the visible degraded state, its notification tier, and a
  product-user affordance — what failed, why, can I retry, what a retry
  does — written for someone who was not in the design room. CT-04 gives the
  machine-legible refusal; this is the operator-legible half, and the direct
  instrument of one-person operability: the sole operator is treated as a
  product user for failure rendering.

## 9. Success measures

**Primary (operator-ratified 2026-08-21) — the DevOps lens.** Judge V1 like a
senior DevOps engineer serving a one-man army:

- **Deployable, out of the box.** The frameworks and libraries install and
  run without ceremony (`uv add`, no DB server, no Docker for QMB) on the
  tier-1 platforms. Deploying to a server must be unremarkable — the trading
  node phase will demand it (ML training, shadow rollouts, retraining under
  MIS), so the foundation must not fight it.
- **One-person operability.** When something breaks, finding and fixing it
  takes little effort — monitoring and evaluation are built in, failures
  surface as typed refusals and journal evidence, not archaeology.
- **External usability proves internal usability.** An agent *outside* QMX
  can use the frameworks and libraries to build and backtest bots — which
  means an agent inside QMX can by default. Same for humans: bots can be
  built in plain Python as well as with the libraries, and backtested through
  QMB at the full depth of its specs.

Each primary measure carries an executable test, so pass/fail is never a
vibe:

1. *Deployability:* on a clean machine on each tier-1 OS, `uv add qmb` +
   `uv add qml` followed by a canned replay backtest from one canonical
   checkout completes without manual intervention.
2. *Operability:* against a named injected-failure set, the first diagnostic
   artifact the operator sees is a typed CT-04 refusal or a CT-13 journal
   event — never a stack-trace archaeology session.
3. *External usability:* a scripted agent, using only the published docs and
   installed packages outside the QMX repo, authors a plain-Python bot and
   produces a CT-32 result artifact through the `qmb` CLI.

*Counter-metrics:* operability achieved by scope-cutting the governance
invariants (a platform easy to run because it skipped the doors is a
failure); usability achieved by coupling — if a library works only inside the
QMX repo, the external-agent test fails; and fabrication [MINED] — no code,
spec, or review agent in the factory lanes may invent mock, synthetic, or
placeholder data: a missing value, dependency, or architectural answer fails
closed and lands in the ledger. (Synthetic data stays legal only as the
claim-class-labeled artifact of FR-041, never a silent stand-in.)

**Relationship between the lenses:** the DevOps lens is the **gating** lens —
V1 does not ship without it — while foundation stability is the **thesis**
lens: the "React before the website" bet the whole rebuild rests on. The
factory optimizes to the gate; the operator judges the thesis.

**Supporting (proposed, kept from the draft):**

- **Traceability:** 100% of V1 FRs trace to ratified `docs/` IDs; every
  contract CT-01..CT-34 (except deferred CT-08) implemented with passing
  conformance tests. *Counter-metric:* docs-drift — code diverging from a
  cited contract without a docs change is a build-stopping defect.
- **Determinism:** identical run configs produce byte-identical CT-32
  artifacts across machines and runs. *Counter-metric:* determinism by
  over-pinning that freezes upgrades (the format-version ladder must keep
  moving).
- **Money-path purity:** zero float taints on the money path, enforced by
  gate tooling, not review.
- **Foundation stability:** QMB and QML build against QMF's published
  contracts without patching the framework — the "React before the website"
  test.

## 10. Open items and risks

| # | Item | Status / owner |
|---|---|---|
| 1 | ~~Corpus sign-off~~ — EXECUTED 2026-08-21: the contradiction sweep passed (after two desk fixes), `_docwork/stage_state.yaml` ratification now reads `ratified`, all 100 docs artifacts carry `status: ratified`, and `lint_docs --strict` is fully clean for the first time. Ratified docs remain documentation authority only — implementation arrives via the factory pipeline. | Closed |
| 2 | **GAP-0048** backtesting fidelity taxonomy — blocks verdict-bearing backtests and `world=simulated`. | Future sitting |
| 3 | **GAP-0049** SR*/search-quality threshold. | Future sitting |
| 4 | **GAP-0016 / GAP-0017** causality registration gate, attempt counter (CT-08 unresolved). | Deferred per DEC-0121 |
| 5 | ~~DEC-0049~~ — RESOLVED by operator ruling 2026-08-21: on rare (black-swan-class) data-quality/drift events a detector may pause via an entry-blocking control at the narrowest affected scope (instrument, currency cohort, Book, venue/broker, or system — never wider), never touching positions or exits (L39); inform-vs-pause posture is UI-editable per L38 (inform when the operator is reachable, pause when not). | Closed |
| 6 | ~~CLI/package naming~~ — RESOLVED by the corpus: the `qmb` CLI is the single command-line surface (DEC-0185 Ruling C; `qmx` superseded per DEC-0159). | Closed |
| 7 | ~~QMA name~~ — CONFIRMED by operator dictation 2026-08-21 ("QMA is mostly the agentic system"). | Closed |
| 8 | **GitBook vs `docs/` QML framing** — GitBook conservative, `docs/` carries the absorbed increment; reconcile at the next GitBook update rather than assuming agreement. | Documentation pass |
| 9 | ~~Phase ordering~~ — RESOLVED: Phase 1 docs-corpus scope, Phase 2 trading node (operator 2026-08-21); only the terminal's Phase-3 slot stays assumed. | Closed (terminal slot open) |
| 10 | **Docs-tracked coordination questions** — three QML reviewer questions (CT-29 keying shape, CT-23 inbound full-loss posture, CT-34 leg cardinality — the last two answered by DEC-0185 Riders A/B) and the surfaced SQS-formula memlog conflict live in the changelog/stage-state, not here; they ride the docs process. | Docs process |
| 11 | [MINED] **Alpha-decay signal catalog** — the corpus ratifies the concept and guardrails but no signal list. Input catalog for a future sitting: breaker-door/leash-event fire density, MAE/MFE drift, drawdown decomposition, regime/session-conditioned performance drift, plus measured proximity to a charter-death condition. Guardrails ride along: measured quantities and registry formulas only, never a declared-weight composite score; decay informs the sunset review, never disposes. | Future sitting |
| 12 | [MINED] **Node-phase position-safety cluster** — four questions neither old build nor corpus closed: (a) stop-out taxonomy — does a breakeven exit / forced flat count toward sizing (the bench half is ruled); (b) position fate at money boundaries — how unrealized P&L enters a sweep (boundaries leave positions alone; the accounting is unstated); (c) dynamic SL/TP grammar — Book grammar, BMS as config authority; (d) an amendment idempotency threshold (UI-editable) suppressing tick-storm duplicate amends. | Node planning |
| 13 | [MINED] **Atomic decision-plus-evidence commit vs the store seam** — the old build required a decision state change and its journal append to commit atomically; the corpus has WriterId ownership and gapless streams but no dual-write atomicity rule, and the store seam spans engines without transactions (Parquet/JSONL). Is atomic dual-write a journal-path requirement, and does it constrain the seam? Corpus wins pending a ruling. | Architecture |
| 14 | [MINED] **News-provider selection evidence for DEC-0119** — old-build evaluation recorded as input, not a choice: Forex Factory free weekly JSON as primary (rate-limited ~2 downloads/5 min), FMP / Trading Economics / FXStreet as impact-carrying fallbacks, EODHD disqualified (no impact field), scraping rejected. | Operator ruling at node/ops |
| 15 | [MINED] **Deep-history acquisition evidence** — TrueFX (16 majors, tick since 2009) and HistData (M1 + tick) as evaluated Dukascopy companions; Databento carries no spot FX; venue-only backfill is rate-capped into unviability, so the recent window needs a platform-continuity bridge, not broker backfill. | Input to FR-042 epics |

**Live `[ASSUMPTION]` index:** (1) the terminal's Phase-3 slot (§2); (2) the
small-team (~3) forward-compatibility hook (§3). Everything else that was
once tagged has been resolved by operator ruling and untagged.
