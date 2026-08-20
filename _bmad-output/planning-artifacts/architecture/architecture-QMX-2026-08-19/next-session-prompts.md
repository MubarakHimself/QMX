# Paste-ready prompts for the next sessions (written 2026-08-20)

Each block is self-contained — paste it as the first message of a fresh session.
Recommended order: 1 → 2 → (3, 4 in either order) → 5 → 6.

---

## 1. Documentation factory (run this first)

```
Run /documentation-factory in change mode. Intake: the ratified architecture
sitting at _bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/
— read ARCHITECTURE-SPINE.md (final, AD-1..AD-21), .memlog.md (rulings +
provenance), the two time-audit files, ctrader-time-research.md, and the
tracker/map.md entries for 2026-08-19/20. Job: absorb the 21 ADs into docs/ —
close GAP-0001..0015, 0018..0030 (GAP-0016/0017 are operator-deferred to the
backtesting sitting — mark them so, do NOT close them), fill contracts
CT-01..CT-07, CT-09..CT-15, CT-26 from the ADs, mint ledger decisions, update
component specs and registry/variables.yaml, add glossary terms (Instant,
TradingDate, Duration, Interval, Account, WriterId, world, market-hours vs
day-boundary vs news calendar, experimentation vs backtesting), rename the
calendar concepts apart (COMP-CALENDAR-FEED = news calendar). The cTrader
research is evidence pending GAP-0037 — record, don't adopt. Standing
principle to record: everything downstream of QMF (trading node, backtesting,
agentic system, UI) is built with QMF libraries. The five-hats sweep
(reviews/five-hats-sweep.md) is an input register for remaining sittings —
reference it, don't resolve it.
```

## 2. Queue the first factory work (after the docs land)

```
Run /queue-publish. Brief: stand up the QMF workspace scaffold + qmf-core,
exactly per docs/ (which now carries the ratified ADs): uv workspace, seven
packages plus extensions/ per AD-2's skeleton, toolchain and poe commands per
AD-3/AD-4, then implement qmf-core — exact money (AD-7), exact time (AD-8),
identity nouns (AD-9), fingerprints (AD-10), typed refusals (AD-11), result
labels (AD-12), Clock/calendar protocols — zero dependencies, 100% branch
coverage on CT-01/CT-02 primitives, reference usage per L27. Nothing else:
no registry/data/venue/risk implementation yet.
```

## 3. Indicators & structure sitting (GAP-0031..0034)

```
Run /bmad-architecture. Update intent: resume from the memlog at
_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/
(AD ids stable, add new ADs). Scope: GAP-0031..0034 only — the indicator
protocol (batch + incremental, warm-up, missing values, typed failures),
the TA-Lib canonical-arithmetic pin (verify current version on the web),
the light-vs-heavy indicator rule (GAP-0033, nonblocking), and the first
causal market-structure families (observed-at/confirmed-at, per AD-8).
Method: gap by gap, one recommendation, AskUserQuestion, recommended option
first, dumb it down on request — operator is non-technical and will brain-dump.
Consult reviews/five-hats-sweep.md for the researcher/trader conflict on the
indicator protocol (burst throughput vs per-tick latency — design two
conformant modes). Park everything venue/risk/backtesting.
```

## 4. Venue sitting (GAP-0035..0038)

```
Run /bmad-architecture. Update intent: resume from the memlog at
_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/.
Scope: GAP-0035..0038 — secret lifecycle (OAuth, VPS storage, rotation,
compromise recovery), the venue order-state machine (idempotency keys,
reconciliation, outage behavior, flatten authority), first broker + account
confirmation, and the venue-adapter contract (capability discovery, so crypto
and stocks slot in later). FIRST: present ctrader-time-research.md for
ratification (UTC ms, BID bars, 17:00-NY boundary, no server clock, rate
limits) — research protocol: present, discuss, ratify; never auto-adopt.
Honor AD-8's operational clock rules and AD-9's VenueId discipline. Same
gap-loop method; operator brain-dumps, park node runtime behavior.
```

## 5. Risk sitting (GAP-0039..0046)

```
Run /bmad-architecture. Update intent: resume from the memlog at
_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/.
Scope: GAP-0039..0046 with the 2026-08-19 re-bucketing ruling applied first —
kill switch, news windows, dynamic SL/TP, Book runtime behavior are trading-
node territory; QMF carries only their contracts/seams; propose per gap
whether it stays QMF (seam) or re-buckets to the node. QMF-side to rule:
Book and BMS schemas + cardinalities (multiple-BMS question DEC-0095),
exit-ownership conflict DEC-0067 (recommend Book owns exit policy, bots emit
signals), R and the FORM-0006 replacement (dimensional tests mandatory),
stop-out definition + un-overloading B/BENCHED (dig delivered in
workroom/reference/10). Leads to honor: "the Book sets the bar" (bot
qualifies by the Book's own metrics); Books/BMS need their own validation
mechanism; paper accounts are world=live (AD-12). Consult the five-hats
sweep. Operator brain-dumps; SQS formula stays open (re-understanding pass
first, operator ruling)."
```

## 6. Backtesting kickoff (ticket 008 — the big one, when you're ready)

```
Run /bmad-brainstorming on the backtesting framework (ticket 008). Ground
yourself: tracker/map.md, tracker/tickets/008-backtesting-framework.md,
workroom/reference/02-backtesting-verdict.md, the Lean CLI extraction in
workroom/agentic-system-planning/research/raw/, and archive/recovery/
backtesting-engine-retrieval/. Standing rulings that bind: it is a FRAMEWORK
(decentralized callable components), never an engine or central service
(DEC-0084 dead); Lean/QuantConnect-shaped, built our own (no code adoption);
agents run experiments in paid sandboxes/VPS, driven via the UI; bar-close /
intrabar / tick fidelity labels are candidates only. Operator vocabulary
lead: "experimentation" may become the umbrella term — backtesting is the
verification of experimentation. In scope here (operator-deferred from the
architecture sitting): the look-ahead/causality registration gate
(GAP-0016), the attempt counter and budgets (GAP-0017, with GAP-0049's SR*),
simulated-time typing (unlocks world=simulated in AD-12), fidelity taxonomy,
fill models, the Bot-by-Book matrix, parity contracts (GAP-0048), "the Book
sets the bar" qualification metrics, and Book/BMS validation mechanisms.
The operator's GPT brainstorm markdown is a missing input — ask for it
before proposing anything. Brainstorm first, one topic at a time, plain
words; the operator will brain-dump; nothing adopts without his ruling.
```
