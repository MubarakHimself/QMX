# Backtesting corpus brief — for the QMX architecture sitting

Distilled 2026-08-20 from the standing backtesting corpus. Read-only research; nothing
below is ratified beyond the DEC-lines explicitly marked ratified. Every load-bearing
claim carries a file path + line.

---

## 1. Standing rulings (what is actually decided)

### 1.1 Ratified decisions in the docs ledger (binding)

- **DEC-0084 — DEAD**: "All agents and Books share one centralized always-on backtesting
  service." Rejected because centralization "could not supply enough compute for
  concurrent work" / "cannot supply the required isolation and Book-specific variation."
  (`docs/gap-report.md:199`; `docs/decisions/ADR-0011-deferred-consumer-products.md:24`;
  status `dead` `docs/knowledge/traceability.md:107`). → Backtesting is **decentralized**,
  runs on-demand in agent sandboxes / VPS, never centralized on the workstation.
- **DEC-0085 — DEAD**: "QMF adopts Nautilus Trader's contracts as its foundation."
  Rejected — "operator does not want the Nautilus contract; QMX-owned semantics stand."
  (`docs/gap-report.md:200`; `ADR-0011:25`).
- **DEC-0086 — DEAD**: "QMF performs a three-day spike to decide whether to adopt an
  external trading framework." The three-day adoption spike was **cancelled; locally
  owned contracts committed.** (`docs/gap-report.md:201`; `ADR-0011:25`). → **Build our
  own; no external-engine code adoption.**
- **DEC-0082 — REJECTED**: modeling prop-firm workflows with generic Program/Campaign
  state machines was "rejected as far off; a prop firm is modeled as a new Book."
  (`docs/gap-report.md:198`). NB: this **overrules** the verdict doc's §4.3 Program/Campaign
  proposal — the ratified position is "a prop firm is a Book," not a new phase-machine type.
- **DEC-0083/0087–0091 — DEFERRED (ADR-0011)**: "Backtesting, the future modular sandbox,
  the visual Simulator, MIS, the QML Bot library, and agentic runtime organs are outside
  QMF V1." (`ADR-0011:30`). QMF V1 ships **reusable contracts**, not a complete trading
  node (`ADR-0011:34`). Related venue rulings: **DEC-0063** — broker connection ships
  separately, "parity belongs to future backtesting" (`docs/gap-report.md:192`).
- **DEC-0135 (venue sitting, 2026-08-20)**: the 2013-forum cTrader claims — the
  17:00-New-York daily boundary and **BID-derived trendbars** — were **demoted** and
  replaced by "measure-per-broker adapter obligations" (`docs/gap-report.md:206`). This
  closes verdict-doc open question #2 (BID vs mid) as: measure per broker, do not assume.

### 1.2 Vocabulary / framing rulings (tracker/map.md, operator, not yet DEC-numbered)

- **"Engine" is BANNED for backtesting — "it is a library."** Also banned: "plugins",
  "exam" (collides with legacy Examination Engine), "fake counterparty" framing.
  (`tracker/map.md:21`; ticket `tracker/tickets/008-backtesting-framework.md:19` bans "exam").
- **Backtesting is a decentralized set of callable QMF components — no monolith, no
  central engine.** "design lives wholly in ticket 008 … explicitly OUT of qmf-core
  (no loop, no broker, no backtest, no downloads)" (`tracker/map.md:71`; also
  `map.md:49` "no central backtest engine — backtesting decentralizes into callable QMF
  components").
- **Build our OWN QuantConnect/Lean-shaped library** (operator ruling 2026-08-19),
  "consistent with the build-our-own ruling; Lean CLI extraction already in
  workroom/…/research/raw/" (`tracker/map.md:29`, circle-back ruling #5). Lean is a
  **shape reference, not a code donor.**
- **Backtesting is PAUSED as a decision area** — its own session, ticket 008. "The verdict
  briefs are research inputs only; nothing in them is ratified." Approach = his staged
  funnel; the GPT brainstorm markdown is the **missing required input — request it.**
  (`tracker/map.md:36`).
- **Simulator (ratified vocabulary, ABSTRACT)**: = backtest library + a Book + chosen
  conditions, via a UI — stress a bot against any real/theoretical Book. **UI-driven,
  a later product; the fill engine belongs wholly to ticket 008.** (`tracker/map.md:63,66`).
- **Fidelity taxonomy (bar_close / intrabar / tick) is a CANDIDATE, not ratified** — it is
  one of "six irreversible technical decisions pending ratification (each invalidates every
  prior stored result if changed later)": fidelity taxonomy, TA-Lib as canonical indicator
  arithmetic, UTC-nanosecond timestamps, (venue,symbol) identity with opaque symbol string,
  SR* (pre-registered Sharpe bar), the result-key tuple — queued for the locks discussion
  (`tracker/map.md:76`).
- **Alpha-decay math confirmed UNRECOVERABLE** (2026-08-18, two independent sources, never
  written down): "design fresh, don't excavate." Old QML feature complicated because "edge"
  was Book-relative and Books are now plural (`tracker/map.md:61`).
- **Framework-vs-node split (re-affirmed hard, 2026-08-19)**: kill switch, news windows,
  dynamic SL/TP, Book runtime behavior = trading-node/application territory; **QMF carries
  only their contracts/seams** (`tracker/map.md:29`, ruling #2).
- **Research protocol**: findings are NEVER auto-adopted (`tracker/map.md:22`).

### 1.3 Ticket 008 scope (the paused session's charge)

`tracker/tickets/008-backtesting-framework.md`: design QMF's backtesting **framework**
(never "engine") as a **staged funnel** — cheap screen → research test → robustness test →
execution/replay → full Book/BMS simulation; early stages exist only to decide whether a
strategy earns more compute; outcomes route pass→promote / pass+opportunity→enhance /
fail+known-issue→repair-component / fail+unexplained→archive. **Execution is ON-DEMAND in
agent sandboxes/VPSs (bare-metal Ryzen 9 planned), never centralized on the workstation.**
Constraints (008:16): intraday scalping profile (swap largely irrelevant; IC Markets
swap-free account), synthetic data = experimentation/stress only (99% historical), spread
modeled within measured ranges, SQS reverse-engineered into backtest conditions. The
sim≡live **parity checklist** (Lock 2) belongs here and must be re-presented "with more
depth." The full overfitting-statistics discussion lands here wholesale. **Agents, not
Mubarak, execute backtests — the design must make the right thing the easy thing for an
agent** (008:24). Each Book may carry its own testing mechanism (bot × Book matrix) —
the funnel must accommodate per-Book test conditions (008:26).

---

## 2. What the old QMX backtesting engine actually was
(`archive/recovery/backtesting-engine-retrieval/` — README, recovered-backtesting-engine.md,
restart-handoff.md, source-ledger.md)

**Headline retrieval verdict**: the old repo did **NOT** contain a completed Backtesting
Engine. "A claim that the former repository already had a Backtesting Engine" is `DROP` as
false (`recovered-backtesting-engine.md:405`). What existed was three non-conflatable things
(`README.md:7-14`):

1. an unratified old-vault Backtest Engine **spec** embedded in obsolete WF2 mechanics;
2. a later architecture for a **backend-node Examination Engine** with an in-house
   deterministic replay harness (this is the recoverable target);
3. a real **Dukascopy tick-acquisition pipeline + large multi-year raw tick corpus** that
   **failed the licensing gate** (`SOURCE_LICENSE_NOT_CANONICAL_USABLE`), plus
   verifier-backed MIS-Archive storage and bounded replay-query proofs that deliberately
   stop **before** any bot/Book execution, fill simulation, or certificate generation.

**What was actually built (all SUBSTRATE, not the engine)** (`recovered-…:323-341`):
inert Backend scaffold `main.py`; real Dukascopy CLI decoding `.bi5` ticks to Parquet with
manifests; Story 3.5 immutable-archive publication proof; Story 3.6 `serve_bounded_replay_query`
(CT-MIS-02, five fields: `query_id, pair, start_utc, end_utc, labeler_versions`); Story 3.7
labeler-materialization proof; PostgreSQL DDL reserving certificate/dossier table families.
Machine-readable status: **`exam_engine_implemented: false`**. The Examination Engine —
runner, fill simulator, battery executor, certificate generator, run lifecycle — was
**unbuilt, "Deferred D1"** (`recovered-…:334`; `source-ledger.md:68`).

**The recovered design (intent, not code)** — a **backend-node, process-per-run,
book-specific Examination Engine** answering one question: *does this immutable bot spec
retain a cost-adjusted edge under production-equivalent behavior against this exact Book
profile and pinned policy versions?* (`recovered-…:30-33`). Key invariants (§6):
- **INV-02**: replay/live parity permits exactly **two substitutions** — historical data for
  live ticks, and an in-house fill simulator for the Adapter. Everything else
  production-equivalent.
- **INV-04**: every relevant refusal reproduced, ordered, visible. "Easier-than-production
  evidence is invalid."
- **INV-05/06**: run identity carries no ambient time/randomness; min reproducibility =
  `bot_spec_version + data_snapshot_id + config_hash + seed`.
- **INV-08**: exact money arithmetic in scaled integers/Decimal.
- **INV-14**: the engine **evaluates only** — never generates signal logic, mutates
  candidates, self-registers, self-promotes, or decides live entry. Certificates are
  evidence, not permission to trade.
- Placement: off the Trading-Node hot path; read-only over Class-3 Parquet; Backend is sole
  Parquet writer.

**Old examination battery values (all `RECONFIRM`, not authority)** (`recovered-…:190-217`):
walk-forward IS window 6mo / OOS 1mo; min 200 OOS trades/window; OOS expectancy floor 0.15R
after modeled costs; Monte Carlo 1,000 permutations; PBO pass `<0.25`, dead `>0.50`; PBO via
CSCV with 16 subperiods. Cost formulas FORM-0009 `EV = p·W − (1−p)·L − c`, break-even
`p > (L+c)/(W+L)`. Honesty acceptance (SM-6, `KEEP`, never implemented): overfit archetypes
must fail, a known-good control must pass, a mismatched-labeler certificate must block live.

**Old fill-simulator dimensions (design candidates)** (`recovered-…:229-262`): per-symbol
historical/fixed spread model, slippage distribution, commission schedule, partial-fill
probability, rejection probability (incl. widened-news). **Must be re-anchored** to the new
Book/doors/protection model; do **not** inherit old BE-at-+1R, six-clamp, multiplier stack,
equity bands, slot caps, circuit breaker (all `DROP`, §17).

**Explicit DROP list** (`recovered-…:392-407`): WF1 / old WF2 Stages G–I orchestration,
weakness buckets, DPR/PRS ranking, slot auctions, automatic registry writes / paper
redemption / auto live progression, session windows as authority, general-purpose
strategy-playground scope (dropped for V1).

---

## 3. What the verdict doc recommends
(`workroom/reference/02-backtesting-verdict.md`, rev2, 2026-08-17, **status: "proposal, not
adopted"**)

**Core recommendation — Option 2**: build QMF's own **five contracts first**, then the
engine as a thin assembly (§6.1, lines 582-592):
1. `RunSpec`/`RunResult` + canonical result document & BLAKE3 digest (`qmf.run`) — nothing
   produces a result except a registered Run;
2. metrics contract (`qmf.metrics`) — registered metric set, `metrics_set_id`,
   framework-computed, **no naked float**;
3. `FillAssumptions` manifest + fidelity taxonomy fixed before any fill rule;
4. registration gate (`qmf.registry`) — causality/stability/warm-up composition, no-lookahead
   test, edge-vs-spread refusal;
5. Book seam (`qmf.book`/`qmf.bms`) — Signal carries no size; one gate + separate cancel door;
   rulesets are data with `source_url`+`retrieved_on`.
Rationale: contracts are the product; you can improve a crude fill engine later and re-run
because every Run names its inputs; **provenance cannot be retrofitted.**

**Vocabulary the doc proposes** (§1, lines 60-72): `SimBroker`→**SimVenue** (same broker
port + conformance suite as cTrader); its guts = **Fill Engine**; knobs = **Fill Assumption
Set** (named/versioned/seeded/cited, e.g. `fx.pessimistic@1.2.0`); one evaluation = **Run**;
data pump = **Replay**; **Paper mode** = live prices + simulated fills (prop-firm dry-run);
**Simulator** = UI only; **Chart Trainer** = out of core; **Book Matrix**, **Program**,
**Campaign**. Rule: "the word Simulator never again means the fill engine."
⚠ Note the "SimVenue/fake counterparty" framing conflicts with the operator's banned "fake
counterparty" framing (`map.md:21`); and **Program/Campaign conflicts with ratified DEC-0082**
(prop firm = a Book, not a phase-machine).

**Architecture**: one deterministic kernel, three wirings (§2.1): Backtest (SimClock +
Replay + Fill Engine), Paper (WallClock + live feed + Fill Engine), Live (WallClock + live
feed + cTrader). SimVenue and cTrader are two implementations of one broker port passing one
conformance suite; assert-no-import-edge CI test.

**Six irreversible / load-bearing design claims**:
- **Fidelity taxonomy** (§2.3): `bar_close` / `bar_intrabar` / `tick`; enters every result
  key, cannot be retrofit; **optimistic matching modes TAINT the result** — recorded
  `fidelity: optimistic`, refused promotion, cannot spend split budget.
- **Warm-up as an engine invariant** (§2.4) — computed automatically up the composition tree,
  enforced by dispatch (a separate `pre_warm` method, not an `if`), because an LLM composing
  a Confluence cannot be trusted to compute combined warm-up and the failure is silent.
- **Fill Engine** (§2.5) — an 8-step named pipeline returning `Fill | NoFill(reason)`;
  slippage may refuse to fill; limit clamp applied by the framework, not the model; ship a
  `PessimisticFillModel` — every promotion candidate runs under both.
- **Cost = 5-column TradingCost** (§2.6): spread, commission, slippage, **financing**, other
  — financing present from the first commit; makes decay attribution a subtraction.
- **Two clocks** (§2.7): `wall_ts` + `session_date`; prop-firm daily-loss anchor reads
  `session_date`, never `wall_ts.date()`.
- **Result integrity — six mechanisms** (§3): (1) refuse composition at registration before
  data loads; (2) framework-computed metrics (agent never holds arithmetic); (3) registered
  runs (`run_id = sha256(canonical_json(RunSpec))`, append-only, failed runs are the
  denominator); (4) content-addressed inputs; (5) canonical digest + `verify(run_id)`
  re-execution ("an agent can lie in a sentence; it cannot make the lie survive a re-run");
  (6) MinBTL-derived split budget, no `force=True`. Ratify-verbatim line: **"A Sharpe ratio
  is not a result. A Sharpe ratio plus the number of effective trials that produced it is a
  result. QMF will refuse to emit the former."**

**Why not adopt an existing engine** (§6.2, lines 613-625): NautilusTrader (LGPL, mid-rewrite
v2 rc, no cTrader adapter, models no prop-firm rules); rqalpha (non-commercial licence —
blocked, ideas-only); zipline (Apache but US-equity-shaped, 28 deps); backtrader (GPL, dead
since 2023, agents write its idioms unprompted); Jesse (MIT but crypto-baked, no pip/lot/swap
concept); LEAN (Apache but C#+Docker, wrong for a solo non-technical operator). **"The engines
that are legally clean and mature are built for the wrong asset class; the ones built closest
to your needs are licence-blocked or mid-rewrite. That is the honest reason to build."** — the
operator has since ratified build-our-own (DEC-0085/0086).

**The honest risk the doc flags** (§6.3): the **fill model for retail-forex CFDs has no good
reference implementation anywhere** — variable spread by hour/event, weekend gaps, swap as a
P&L line, partial-lot rounding, per-instrument margin; only backtrader has any (interest only).
"Integrity is not fidelity" — a reproducible result from a wrong fill model is a reproducible
wrong answer. Mitigation = the slippage-measurement loop (§5.4): measure live slippage,
recalibrate `FillAssumptions`, bump version, re-run baseline — fidelity becomes a measured,
improving quantity.

**Alpha decay** (§5): live and backtest write the same ledger rows → decay is a comparison of
two objects of one type. Baseline keyed to `(confluence_id, book_config_hash, venue_model_id,
fill_assumptions_id, fidelity, split_id, metrics_set_id)` — change a Book value and the old
baseline is automatically inapplicable (fixes the "Books are plural" wrinkle). Three-cause
split (cost/fill vs signal vs regime); ship the append-only per-trade log now, add a drift
detector (`river.drift` only) later. Monitor never re-sizes/retrains/deploys.

**Lean CLI extraction** (`workroom/agentic-system-planning/research/raw/lean-cli-readme-extraction.md`):
raw, unreviewed straggler output; QuantConnect/lean-cli v1.0.228, Apache-2.0, 100% Python,
Docker-based. Documents the full command surface (`lean backtest/optimize/research/report/
live/cloud/data/config`), local↔cloud parity model, project scaffolding, and
`lean private-cloud` master/slave compute. It is the **shape reference** for the
"build our own Lean-shaped library" ruling — parked for the future Lean-borrowings step.

---

## 4. Reconciliation flags for the architect

- **DEC-0082 vs verdict §4.3**: ratified position is prop-firm = a Book. The verdict's
  Program/Campaign phase-machine is superseded — do not carry it as a new type.
- **DEC-0084/0085/0086 already ratify** the decentralized + build-our-own + no-adoption
  posture that the verdict doc argues toward; the verdict remains "not adopted" as a design.
- **Fidelity taxonomy + result-key tuple are candidates** (map.md:76), pending the locks
  discussion — not yet lockable in architecture.
- **cTrans BID/mid + 17:00 boundary demoted** (DEC-0135): "measure per broker," closing
  verdict OQ#2.
- Backtesting is **deferred out of QMF V1** (ADR-0011) and **paused as a decision area**
  (map.md:36) pending the operator's GPT brainstorm markdown + ticket-008 session.
