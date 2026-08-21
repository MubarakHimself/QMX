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

---

## 7. Documentation factory — risk increment (written 2026-08-20, after the risk sitting closed)

```
Run /documentation-factory in change mode, RISK increment only. Intake:
_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/ —
ARCHITECTURE-SPINE.md (final, now AD-1..AD-41), .memlog.md entries 84..116
(rulings + provenance, incl. the post-close confirmations: journals =
extraction views, one-Book-per-netted-account, USD, QML verdict), research-risk/ (nine extractor dossiers, six briefs,
ctrader-sltp-amend-research.md, qml-original-dig.md), and
tracker/trading-node-notes.md risk-sitting section (reference only — never
absorbed into docs). Job: absorb AD-29..AD-41 + cross-AD amendments
(AD-7/10/16/17/18/21/27/28) into docs/ — answer GAP-0039..0046, mint ledger
decisions (incl. DEC-0067 resolved, DEC-0095 resolved, DEC-0070 confirmed),
fill CT-22..CT-25 re-purposed + CT-27..CT-32 new, update qmf-risk component +
registry/variables (all new numbers = configurable UI-editable variables with
recorded evidence, no ratified constants), glossary (kill switch vs kill line,
BENCHED seat-only, qualifying_loss_exit vs venue_liquidation, Book
version/instance/binding-epoch, value-factor, window kinds), constitution
additions per the spine's invariant rows (corpus-precedence; configurable =
UI-editable). Honor the supersession notes (2026-08-18 paper-through-news
ruling superseded; AD-29 supersedes prior docs BMS direction). Also extend qmf-data's component docs with AD-31's projection machinery
(declared read-time entity-journal projections — per-bot / per-Book /
combined views extracted from the recorded streams, join guarantees on
CT-25) — operator flagged qmf-data needs this enhancement. Remaining open
after this: GAP-0016/0017 + 0047..0049 (backtesting + QML sittings).
```

## 8. QML sitting — SUPERSEDED (ran autonomously 2026-08-21; the QML spine is FINAL at architecture-QML-2026-08-21/ — use prompt 11 instead)

```
Run /bmad-architecture. Update intent: resume from the memlog at
_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/.
Scope: GAP-0047 — the QML sitting (the bot-authoring layer). Primary input:
research-risk/qml-original-dig.md (old QML = "QML Shared Contract Library";
BotSpec = Archetype + Features + Filters + Risk + Execution + ExitLogic;
ExitLogicRef; CloseReason taxonomy) PLUS research-backtesting/
qml-dig-verification.md (the `.qml` bot-source FILE FORMAT the dig missed —
plain-Python-vs-.qml-DSL authoring must be ruled here). Job: rebuild QML as
a THIN CONSUMER of QMF V1 contracts — never a foundation layer: the Bot
schema (registry kind reserved by AD-16), confluence composition per AD-17
recursive multiplicity, Book binding via CT-28/CT-23, exit declarations via
AD-33's ExitLogicRef atom, admission-bar measure interfaces (thresholds come
from the backtesting sitting — INTERFACES only, so this sitting may run
before backtesting per operator lead 2026-08-20; QML-first BUILD order is
natural). Old QML is evidence and shape ONLY, never code; its old
risk/sizing content is superseded by AD-29..41. Bots stay authorable in
plain Python (don't-box-in); QML conformance is the ticket into governed
evidence and Book seats, nothing else. Operator brain-dumps;
recommendation-first questions; every configurable = UI-editable.
```

## 9. QMB spec-synthesis session — SUPERSEDED (ran same-day 2026-08-20; the QMB spine is FINAL at architecture-QMB-2026-08-20/ — use prompt 10 instead)

```
Run /bmad-architecture. Update intent: resume from the memlog at
_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/
(entries 117+ are the backtesting-direction session of 2026-08-20). The
product is named QMB (operator ruling): ONE library + ONE CLI (command qmb)
— an application built on QMF contracts, never a QMF roster package; QMB is
the name because QMX is the whole platform. Operator-ruled method:
spec-driven reverse-engineering — understand HOW Lean/Jesse achieve each
marketed feature from their code; never adopt code (D1). Intake:
research-backtesting/specs/ (12 feature HOW-specs + website-visuals.md +
screens/), the eight grounding dossiers and three challenge reports in
research-backtesting/, and backtesting-direction-position.md (v2 —
challenged; its DC-1..5 were NOT ratified as-is; the operator redirected).
Operator rulings that bind: config-driven wind-tunnel CLI (a Book/BMS
compiles to a validated fingerprinted config fragment; test = can the bot
fit the Book; change variables, never swap the tunnel); logs during runs +
ONE completion-ledger entry with unbiased pass/fail; distribution like
pip/uv tool (lean does 'pip install lean'); Books/strategies resolved
name@version from the registry (the npm-for-scale half); MCP ships as a
thin wrapper AFTER CLI v1 (does not wait for the agentic system); target
12-14 concurrent runs; spec stays appendable (QMX keeps growing). Standing
law untouched: L20 synthetic-never-validates-edge (operator wants Lean's
generator mechanism in front of him before ruling), replay-first until
GAP-0048, engine vocabulary banned. Job: synthesize the specs into the QMB
blueprint (command tree, config layering, run loop + fill-model interface
feeding GAP-0048, optimize/MC/significance surface, report + ledger
formats, concurrency model), then mint ADs at the proper backtesting
sitting together with GAP-0016/0017/0048/0049. The ticket-008 GPT
brainstorm markdown is STILL a missing input — ask for it first. Operator
brain-dumps; recommendation-first; correct his analogies when wrong rather
than accepting.
```

## 10. Documentation factory — QMB increment (written 2026-08-20 end of session; run this next)

```
Run /documentation-factory in change mode, QMB increment. Intake:
_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ —
ARCHITECTURE-SPINE.md (FINAL, B-1..B-15 + inherited-invariants table),
.memlog.md (12 entries: rulings, gate rounds, provenance, ratified-by-
delegation), reviews/ (six gate lenses + review-reconcile-docs.md — its
citation-hygiene findings are already applied); plus the QMF run's
research-backtesting/ (intake dossiers + specs/INDEX.md + position paper)
and QMF .memlog.md entries 117-138 (the backtesting-direction session).
Job: absorb QMB into docs/ — QMB realizes the glossary's "future
backtesting library" entry (the Simulator stays a separate deferred UI
product consuming QMB); SETTLE the experimentation/backtest rename (ruled
at this sitting); record CT-32 as ADOPTED by QMB (chart-series +
trade-event-refs = declared QMB extensions), CT-13 replay-world emission
from the run loop, CT-11 honored (per-run logs = operational only). Do NOT
close GAP-0016/0017 (registration gate still deferred per DEC-0121 —
but record that look-ahead PREVENTION is delivered by B-2/B-8/B-12). Mark
GAP-0048 PARTIALLY closed: seams ruled (fill/cost/financing ports, partial
fills, fidelity lowest-wins, optimistic taint, calibration-not-invention
method per DEC-0135); taxonomy values + calibration content still open.
Mint ledger decisions: QMB naming (qmx command superseded), config-compiler
wind tunnel + disjoint Book/BMS namespaces (BMS outranks), pure-run/
orchestrator split, reader-derived per-requirement verdicts, B-15 registry
as-of sets + passive hub (DEC-0084 stays dead), download-once data + per-
window license tags (dukascopy-node = acquisition reference), uv-add-not-
uv-tool distribution, stack pins click==8.4.2/optuna==4.9.0. New variables
= configurable UI-editable per L38. Flag for the operator: the Dukascopy
data-licensing ops question stays open. Remaining after this: GAP-0016/0017
gate, GAP-0048 content, GAP-0049, GAP-0047 (QML sitting — operator lead:
may run BEFORE the backtesting-content sitting; QMB tests plain-Python
bots meanwhile). Then PRD, then BMad exit.
```

## 11. Documentation factory — QML increment (written 2026-08-21, after the QML sitting closed; run this next)

```
Run /documentation-factory in change mode, QML increment. Intake:
_bmad-output/planning-artifacts/architecture/architecture-QML-2026-08-21/ —
ARCHITECTURE-SPINE.md (FINAL, QL-1..QL-10 + inherited-invariants table +
the "Parent-contract mints proposed by this sitting" section), .memlog.md
(18 entries: rulings, assumptions tagged for operator override, gate
amendments), reviews/ (five gate lenses, all findings applied); plus the
two evidence dossiers research-risk/qml-original-dig.md and
research-backtesting/qml-dig-verification.md (QMX-discussion citations in
them ride the named structural-definition exemption; no risk/sizing
content). Job: absorb QML into docs/ — close GAP-0047. Mint contracts:
ct-33-bot-definition.yaml and ct-34-confluence.yaml (qmf-registry kinds,
QML-authored); update ct-06-registration.yaml (Bot kind body now ruled via
CT-33; add the strategy-family dated metadata record kind). Apply the two
PROPOSED PARENT-CONTRACT FORMAT MINTS with AD-5 migration notes: CT-22
(admission_bar evidence_requirements gains registered-conformant-Bot cite
+ canonical-assignment evidence; exit_policy gains one explicit optional
catch-all default entry with the exit record keying the RESOLVED entry;
footprint_requirements pending(GAP-0047) slot fills with QL-4's
requirement-set shape) and CT-23 (new OPTIONAL entry field: advisory stop
proposal; document the declared full-loss price as Book-resolved at the
door, mirroring requested_r; close the GAP-0047 revision flag — ExitLogicRef
and the close-reason taxonomy are RATIFIED as-is, old CloseReason members
recorded as an evidence mapping, never a second taxonomy). New component
doc docs/components/qml.md (library identity, two-artifact bot, runtime
protocol, conformance gate, dependency stance incl. the declared
reconciliation note: annotate the QMF Dependency-direction rule as
roster-scoped so application-layer qmf-risk imports are legal at source;
also fix the QMB docs' "AD-2 / L21" mis-citation to "AD-2 / L11").
Glossary: rewrite QML (no longer a deferred stub) and Bot (full CT-33
shape); add strategy family, canonical assignment, advisory stop proposal,
conformance/ticket, confluence leg + roles incl. filter; record BotSpec
and archetype as retired aliases. Mint ledger decisions: no-DSL-in-V1
(.qml not revived), Bot kind body, confluence kind + leg-role vocabulary,
family = key-not-authority, canonical-assignment parameterization law,
conformance-as-ticket (technical, never performance; complexity gate NOT
revived — stated drop), prediction-linter four checks (AD-30/AD-32 pending
slots resolved), Book-side single-sited full-loss derivation, QML-before-
the-trading-node build order, QML version ladder (own SemVer display-only,
uv add qml). Record the three QMB coordination items in the qmb component
doc: B-3 assignment_is_canonical stamp, B-3/seat-admission producer-
template resolution step, B-8 parameter-space schema completed with
unit-kinds (one schema, CT-33-authoritative). Update gap-report
(GAP-0047 answered), traceability, changelog, AGENTS.md if it enumerates
open gaps. All memlog "assumption" entries are operator-overridable calls
— surface them in the changelog row so the operator can veto cheaply.
Remaining open after this: GAP-0016/0017 (registration gate, DEC-0121),
GAP-0048 content, GAP-0049. Then the PRD, then BMad exit.
```
