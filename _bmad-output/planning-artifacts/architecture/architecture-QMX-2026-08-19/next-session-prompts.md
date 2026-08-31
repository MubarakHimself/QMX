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

## 12. Documentation factory — QMA increment (written 2026-08-28, after the agentic-system sitting closed; run this next)

```
Run /documentation-factory in change mode, QMA increment (the QMX agentic
system). Intake: _bmad-output/planning-artifacts/architecture/
architecture-QMA-2026-08-28/ — ARCHITECTURE-SPINE.md (FINAL, AD-1..AD-29 or
higher if the validation pass minted more; ids are stable, never renumbered;
Inherited Invariants table cites parent AD/L/DEC ids read-only), .memlog.md
(THE AUTHORITY: ~110 entries of operator rulings, adopted leans, gate
amendments, validation-pass fixes; later lines supersede earlier),
research/options-sheet.md (D1..D22 options + leans + 21 adversary
dispositions) and the 12 research/*.md primary-source studies (2026-08-28,
cite them as evidence, never as rulings), reviews/ (six gate lenses, all
critical/high applied), inputs/transcript-decision-register.md (the
ChatGPT-session distillation; section 4 = operator's own words) and
inputs/packet-delta.md. The raw transcript and the packet are seed
material only. The deleted workroom/agentic-system-planning folder is NOT
an input (operator ruling 2026-08-28). Job: absorb the agentic system into
docs/ as a new application-layer consumer beside QMB and QML. New component
docs: docs/components/qma-core.md (ontology, ports, refusal variants, plugin
contribution surface, closed vocabularies: hook verbs, HookResult decisions
+ total precedence, JobHandle states incl. UNKNOWN, Task/Mission states,
MessageKind, DeliveryState, handle kinds, ModelClass four values, principal
classes, the three verbs admit/apply/promote), docs/components/qma-wire.md
(envelope v/type/id/correlation_id/scope_path/seq/payload; JSON-RPC 2.0 over
WebSocket + HTTP GET queries; initialize handshake + semver protocolVersion,
additive-only within a major, wire.deprecation_minors; the 26-noun seed
vocabulary; attach/detach/replay; transport posture loopback-default,
TLS + recorded config otherwise, dial-out for remote workers),
docs/components/qma-daemon.md (one journal / sole writer / clock law; the
closed store list and folds; Task Graph; hooks registry and source bounds;
ledgers task/quant/experiment + desk views; Agent Bus; scheduler + Routines
+ continuation; model proxy chain with OpenCodex behind it; Tool Registry
with the act-level money-path deny-list and check_fn; ExecutionEnvironment /
Compute Router / JobHandle; plugin loader with reversible scopes and
migration down/forward_only; staging store and admission gate; telemetry
export port; Credential Broker allowlist + egress rule; store lifecycle,
backup, restore per parent AD-20/L18). Mint contracts from the ADs at the
next free CT numbers: the wire envelope + command/query/event families,
HookEvent/HookResult, PluginManifest/PluginContext, MemoryProvider,
KnowledgeSource/CorpusSnapshot/Citation/Provenance, ModelClassRequest/
Deployment/ModelCapabilities/CredentialBroker, ExecutionEnvironment/
ComputeRequirement/JobHandle, ExperimentSpec (content-addressed, lineage
DAG), Envelope/Mailbox, Routine, RefinementProposal, the Task Ledger entry
schema and the TaskCompleted structured append. Mint ledger decisions for
every load-bearing ruling: Python 3.14 daemon (L31 dispositive), contract-hub
house style, workstation-default daemon + UI-driven remote deploy, Quant
replaces Bot for the agentic actor, qma.* namespace and no blanket QMX
prefix, task-level ledgers, hooks on every primitive, three control
primitives with the Graph Template vs Task Graph name split, no execution
tool at any account role + reachability barrier (AD-16/AD-28), no memory
engine in-house (MemoryProvider port; Hindsight deferred behind an eval),
read-only Knowledge adapter over the STRATS plain-file library, OpenCodex
behind the Deployment/Broker contract with auth_mode none + loopback bind,
promote reserved for the L17 live-zone act, plugin adopted / kernel only as
"RLM kernel" (parent ban is QMB-scoped; L30 roster-scoped per its 2026-08-21
annotation), the Cut-outright table as spine law. Glossary: add Quant, Desk
/ Profile / Role (five of each, never interchanged), Agent / Subagent /
Session / Worker, Mission / Task / Task Graph, Graph Template, Loop, Skill,
Hook, Task Ledger / Quant Ledger / Experiment Ledger / desk ledger view /
event journal, Memory vs Knowledge, evidence_confidence vs
admission_confidence, admit / apply / promote, ModelClass / Deployment /
Credential Broker / model_family, ExecutionEnvironment / JobHandle /
UNKNOWN, ExperimentSpec, Agent Bus / Mailbox / Envelope, Routine,
principal class, RLM kernel, plugin (agentic sense), QMA = QuantMind Agents
(the SDK only); record "Quantum Mind", "Steward", "QMX Backtesting
Framework" (= QMB) and "QMX Event Ledger" as retired names. Update
registry/variables.yaml with every AD-26 variable (quiet hours, wake caps,
sticky limit, budget hint, hook timeouts, ask_timeout,
wire.deprecation_minors, dedup window, RLM depth cap, retention windows,
max_in_flight, routine caps, continuation budget + escalation target,
backup + restore-rehearsal cadence, model_family, ReviewPolicy families,
proxy.allow_unauthenticated_loopback), each ui-editable/uneditable per L38.
Record the constitution touchpoints (L17, L18, L30 scope, L31, L33, L34,
L35 adopted, L36, L38, L39) in traceability; add the agentic system to
docs/architecture/overview.md as an application-layer consumer and to
AGENTS.md's reading order. Do not revive anything in the spine's Cut table;
the UI extension SDK, memory backend, knowledge indexing, self-improvement
gates, compute vendors, browser stack and desk consolidation stay Deferred
with their stated revisit conditions. All memlog "assumption" entries and
every Deferred row are operator-overridable — surface them in the changelog
row so the operator can veto cheaply. Then bmad-create-epics-and-stories
over the QMA increment (build order: qma-core → qma-wire → qma-daemon
journal/store/hooks/task-graph → model proxy + tools → environments + QMB
door → ledgers/bus/scheduler → plugins; a Quant reachable through models
over the wire is the first milestone; UI later).
```

## 13. Documentation factory — TRADING-NODE increment (written 2026-08-28, after the trading-node sitting closed; run this next)

```
Run /documentation-factory in change mode, TRADING-NODE increment (Phase 2 of
the PRD). Intake: _bmad-output/planning-artifacts/architecture/
architecture-NODE-2026-08-28/ — ARCHITECTURE-SPINE.md (FINAL, TN-1..TN-25 +
Inherited Invariants + "Corrections the node inherits from adjudication" +
"Parent annotations and mints proposed by this sitting" + "Operator rulings
2026-08-28" + "Assumption register (A1–A47)"), .memlog.md (every ruling,
the 20 gate rulings, the four operator rulings, every assumption — the
authority when spine and memlog differ on rationale), inputs/ (parts-bin.md
= the ground-truth inventory of integration@ef9bb25: 154 capabilities,
78 as-is / 24 needs-live-adapter / 52 missing, effort-weighted 45–60%;
corpus-verdicts-A.md + corpus-verdicts-B.md; the ten discovery dossiers),
reviews/ (six first-gate lenses, fix-pass-1.md, five re-gate lenses).
Ground rules unchanged: docs/ is the requirements body the factory codes
against; this increment is its only writer; lint_docs --strict stays clean;
banned words (engine, kernel, plugins, exam, minimal core, "paper node",
bare stop-out, bare calendar, timeframe); "the trading node" is ONE product
with modes paper|live; there is NO operator command line (operator ruling
2026-08-28) — deployment tooling is `just node-…` recipes only.

Job: absorb the trading node into docs/.
- New component doc docs/components/trading-node.md (code name qmn; the
  operator declined to name it — record that). Cover every TN: identity and
  base branch (application on QMF like QMB/QML; the sole sanctioned
  qmf-venue wirer); composition root + boot ceremony (compose → fingerprint
  → seal; composition_fp; boot-attempt record; preflight; check mode; timer
  units' abbreviated ceremony); topology/planes/trust boundaries; process
  model (one asyncio loop at the edge; QMB's loop unforked via run_slice;
  push-to-pull accumulator as single first writer + interpretation cursor;
  one loop per command stream; stand-down-alive + resurrect; safe point;
  shutdown contract minting UNKNOWN for in-flight commands); the order path
  chain of command with veto and suppression paths, entry-side-only blocks,
  AD-37 collapse/conflict/compose, command ordinal ≠ journal sequence,
  durable command-id-binding, submission deadline from wire handoff; KSA
  (GitBook levels adopted, effect matrix blank-blocks-live, monotone fold,
  kill switch under a dead wire, never-auto predicates); the protection set
  run verbatim (kill line = loss_floor per binding on the virtual-ledger
  equity series; windows; SQS via the signal snapshot only, baseline keyed
  by environment; ratchet; bench; disposition routes-to-paper|blocks-paper);
  paper mode + the WEEK-LONG unattended soak with its acceptance checklist;
  startup/recovery/explained drift with FOUR verdicts, resolve_unknown
  only from a reconciled read-back inside the lookback, drift stand-down
  keyed by role, operator_review; venue integration (VenueClientPort minted
  by the node; the cTrader transport increment lands in qmf-venue's
  ConnectionManager — A37; refresh keyed by credential reference; equity
  exact-integer at the account exponent; netting|hedging at bind time and
  dispatch; maintenance windows = sensing-outage fail-closed); secrets
  (two-layer store: systemd-creds --with-key=host KEK + AEAD state; three
  named holders; wizard over SSH stdin from Credential Manager qmx/*;
  backup payload key escrowed on the workstation + offline copy; VPS-loss
  runbook; repo deploy key; privilege model); live data, bootstrap,
  calendar timer (Forex Factory free is the SOLE source, refresh cadence
  configurable, no paid fallback ever), backup + nightly sample restore +
  monthly full restore + host-loss rehearsal, capacity/disk headroom,
  hot_room_retention_window; time discipline (chrony, bands as registry
  rows, skew vs offset, three calendars); observability (JSON logs to
  journald ≠ journals; qmn_ metric families; /health independent states;
  allow-list + the new "stopped accepting entries / cannot persist
  evidence" class; external dead-man's switch; the SEPARATE zero-authority
  observability stack Prometheus/Grafana/Loki-class under
  qmn/deploy/observability/ — containers permitted for that stack only);
  deployment (User=qmx, /var/lib/qmx trees, unit files in repo, Ubuntu
  24.04, ubuntu-24.04 CI lane, check mode, deploy switch/rollback,
  one environment with compensating controls); doors (Python API +
  localhost HTTP evidence channel + unix-socket powers channel with
  SO_PEERCRED; UI plugs in later over an SSH tunnel; per-read provenance
  fields; AD-31 cross-role reads; settings scopes; admission_impact on
  edits); config surface (eligibility-and-identity only, runtime state =
  folds; registry = schema, config = values; value-status
  blank|provisional-evidence|ratified with countersign; extensibility =
  registry + config, never code); seats (QL-7 hosting, callback deadline +
  quarantine, prediction linter, conformance runner, OR-06 relocation) +
  MIS seam (signal snapshot, labelers as CT-16 producers under AD-24,
  shadow-lane seam built now) ; promotion sign + separate activation
  (AD-18 identity fields, sandbox-provenance refusal on the pull);
  replay (import port = the one sanctioned cross-world read; ungoverned
  diff); multi-account seam (roster, state_carry, broker = its own
  VenueId); QA standard (battery + mutmut on node money-path modules on
  the code-carrying branch + venue conformance double FEAT-0023 + the four
  golden scenarios + soak checklist + QA-debt node stories by id);
  position-safety closures (a)–(k); the accounting boundary + virtual
  ledger (TN-25). NFR-11 FAILURES.md obligation mapped to the allow-list.
- ADR (the factory numbers it): the trading node = supervised
  composition-root runtime over a pure rulebook; one product two modes; no
  command line; plain systemd service; separate observability stack.
- docs/architecture/overview.md: the platform C4 context + container view
  and a deployment diagram from TN-3/TN-16 and the process-internals
  diagram (VPS plane: qmn.service + timers + hot rooms + evidence tier +
  hub inbox/published; workstation plane; bucket; sandboxes; cTrader demo
  and live hosts; observability stack); docs/architecture/dependencies.yaml
  gains the qmn edges (qmn → qmf.* incl. qmf-venue, qmb, qml, extensions;
  nothing imports qmn).
- Lens pages: docs/lenses/ops/runbook.md (start/stop/restart/deploy/
  rollback/switch now ruled as `just node-…` recipes; safe point; check
  mode; stand-down + resurrect; VPS-loss runbook; compromise drill
  unchanged; the warm-up rider = the soak week), incident-playbook.md
  (stuck-UNKNOWN affordance; drift stand-down; kill switch under a dead
  wire; disk-full), observability/logging-spec.md (node log fields and
  levels; the five Records streams ↔ seven CT-13 types via CT-25 projection
  names), metrics-and-alerts.md (qmn_ signal families; allow-list + new
  class; dead-man's switch; drift bands as registry rows; the separate
  stack as zero-authority consumer), security/security-model.md (three
  named secret holders; SO_PEERCRED; backup-key escrow; repo deploy key;
  privilege model; sandbox-provenance refusal).
- Contracts and parent annotations (every one is in the spine's "Parent
  annotations and mints proposed by this sitting" section — apply as
  recorded, never widen): annotate L30 in docs/constitution.md at source
  (the node's `qmn.venue` subpackage is the sanctioned qmf-venue import
  boundary — declared reconciliation note); AD-15/L30 async stance: the
  qmf-venue async-conformance test gains a named exemption for
  `qmf.venue.connection` (the ConnectionManager holds the socket, session
  and the single venue secret value on the loop the node injects — the one
  DELEGATED impurity; if refused, the transport increment lands in
  `qmn.venue.ctrader` instead); CT-18: the candidate annotation "realize
  VenueClientPort in qmf-venue" recorded-not-applied, plus the
  SessionTopology connection-count relaxation (derived from the roster)
  as a qmf-venue increment item; CT-20: a mapping-row addition — position
  and balance read-back observations journal under the existing seven
  AD-21 types (never a new journal type); CT-25: the five Records streams
  ↔ seven types projection-name bridge; CT-30: the node's
  satisfaction-predicate declarations per matrix cell, and the AD-21
  `control action` EVENT subtype `node_resurrect` (a node lifecycle act,
  not a CT-30 kind) beside the sealed-period final-look subtype;
  CT-24/CT-28: the node's disposition + state_carry usage (no format
  change); CT-14: backup payload-key custody (workstation-escrowed),
  the nightly sample + monthly full restore timers, the host-loss
  rehearsal, the `sealed-archive` evidence-tier room role; PRD §3: the
  PROPOSED allow-list widening (the "stopped accepting entries / cannot
  persist evidence" silent-degradation class + the external dead-man's
  switch + a liveness digest) recorded as a PRD amendment — surfaced by
  the sitting, ratified by the increment only if the operator accepts it
  (cheap veto; default = accept).
- docs/registry/variables.yaml: mint every row of the spine's registry
  mint table as configurable: true with unit-kind, owner scope, evidence
  values and its BLANK-EFFECT tag (blocks-boot | blocks-role-live |
  blocks-soak); add the NEW schema field `value_status_required` (the
  per-value `value-status` blank | provisional-evidence | ratified lives on
  the resolved config artifact, countersigned through the powers channel
  with an evidence citation — the PRD-named gap, closed this way); record
  that kill_line_capital_floor IS AD-40's loss_floor (one variable, one
  name).
- Glossary: Trading Node (full entry, retire the stub), composition_fp,
  boot/session/binding/level epochs, stand-down-alive + resurrect,
  push-to-pull accumulator + interpretation cursor, evidence tier, passive
  hub (inbox | published), safe point, check mode, soak (= first-deploy
  warm-up week), replay import port, KEK store, VenueClientPort, signal
  snapshot, shadow-lane seam, value-status, virtual ledger vs venue
  position, operations toolkit, observability stack, dead-man's switch,
  amend_min_improvement (a ratchet authoring threshold, never a
  suppression), four reconciliation verdicts.
- Ledger decisions (DEC-*): one per TN (25) + the 20 gate rulings that
  changed behaviour + the four operator rulings 2026-08-28 (no command
  line; week-long soak with the DevOps stack; free news only; promotion =
  click + separate activation) + KSA vocabulary re-ratified into docs from
  the GitBook baseline (GAP-0015 shape closed; matrix values blank-block-
  live, pre-SOAK ruling for whatever the checklist exercises) + PRD §6
  mined doctrine ratified by adoption + PRD open items rows 12–15
  dispositions + ticket 006 disposition (trendbar basis measured per
  broker; SECONDARY web evidence says BID; tick-based interim comparison).
- gap-report: GAP-0015 shape closed; new Deferred rows with GAP ids (MIS
  training + shadow rollout epic; hot-apply settings; agent/MCP door;
  hardened confinement; second VPS; fill simulation in replay); traceability,
  changelog, AGENTS.md; tracker/trading-node-notes.md already carries the
  sitting note.
- All memlog assumption entries (A1–A47; A1/A10/A17/A26 RULED, A8 retired)
  surface in the changelog row so the operator can veto cheaply.
Remaining open after this: the KSA matrix values (pre-soak operator
ratification through the settings surface), GAP-0016/0017, GAP-0048/0049,
the MIS training epic. Then prompt 14 (epics for the node).
```

## 14. Epics and stories — TRADING NODE (rewritten 2026-08-30 after the docs increment and the veto round; run this next)

```
Run /bmad-create-epics-and-stories for the trading node. Fully autonomous
session; ask me only for money, vocabulary I care about, or irreversible
scope. Use dynamic workflows and subagents: bulk-worker for fan-out, Opus 5
for synthesis and adversarial verdicts, Sonnet 5 for light stages; no Fable
subagents.

Intake (docs/ is the requirements body — "what you see is what you code";
the spine is background only): docs/components/trading-node.md (COMP-QMN,
every TN-1..TN-25 section), docs/decisions/ADR-0019-trading-node.md,
docs/architecture/overview.md (deployment view + process internals),
docs/architecture/dependencies.yaml (COMP-QMN edges), docs/registry/
variables.yaml (the 71 node rows with blank-effect tags and
value_status_required), the lens pages (ops runbook + incident playbook,
observability logging-spec + metrics-and-alerts, security-model,
test-strategy + fixtures, performance budgets, data-layer, bugs triage),
the contracts CT-13/14/18/19/20/21/24/25/28/30/31 as annotated, the
glossary, and _docwork/feature_inventory.yaml FEAT-0031 (its blocked_by
reasons are the ordering). Ledger DEC-0186..DEC-0262; gaps GAP-0050..
GAP-0058 (0057 answered, 0058 OPEN and in scope, the rest deferred). Existing epics.md carries
epics 1–23 (shipped) — number the node epics from 24; the QMA epics draft
parked at _docwork/qma/epics-draft/ is NOT in scope (operator ruling
2026-08-30: QMA is documentation only).

Base: main@361ae2c carries the docs; code lives on origin/integration@
ef9bb25 until the operator's squash-merge click — write the epics against
that code base and re-point onto main after the click.

Target: a SMALL epic set (5–8), a wave plan, paper-milestone epics first,
routed for the Grok epic-factory lane (/run-epics in the Grok plugin, 4.5
workhorse / 4.6 orchestrator + reviewer). The operator wants throughput:
epics that can run in parallel on disjoint branches must be marked so, and
no epic may block on a human step it does not need. Validate with the usual
validator workflow; record factory-time ruling items explicitly.

Binding rulings to carry into every epic (already in docs/, DEC-0261):
- There is NO operator command line. Every operator act is a powers-channel
  call the desktop UI makes later; deployment tooling is `just node-…`
  recipes (DevOps, never a trading control). Do not write a CLI story.
- ONE product, modes paper|live; NO per-bot warm-up, probation, ramp or
  paper lane on the node — bots arrive backtested and paper-tested outside
  the node (QMB) and operator-approved; the only route back to paper is the
  BMS/Book protective demotion. Activation takes effect at the next day
  boundary of the account-scoped day-boundary calendar (a mid-day promotion
  trades from the next trading day). No manual override.
- The soak = the full first-deployment week, unattended, whole system on the
  demo account, TN-23 acceptance checklist = the paper-milestone epic's
  acceptance; the live connection opens for sensing-and-recording only once
  credentials exist; VPS procurement gates the soak, Spotware approval +
  live KYC gate go-live only.
- Forex Factory's free weekly file is the SOLE news-calendar source; no paid
  fallback story, ever.
- Alerts: the closed allow-list generated from FAILURES.md + the accepted
  silent-degradation class + the liveness heartbeat (renamed from dead-man's
  switch; outbound alive-ping to a free off-VPS watcher; notification only,
  zero authority). The daily liveness digest is REJECTED — no story. The
  Prometheus/Grafana/Loki-class stack is a SEPARATE zero-authority system
  under qmn/deploy/observability/ (the only place containers are allowed;
  the node itself is a plain systemd service on Ubuntu 24.04).
- Costs already accepted: Backblaze B2 bucket via rclone; the observability
  stack on the same VPS. VPS spec is measured by the node's own benchmark in
  the soak's first hours (procurement starting point, evidence only: 4 vCPU,
  8 GB RAM, ~100 GB SSD, near the broker's cTrader server).
- TWO PLACEMENT VARIANTS are in scope (DEC-0262, GAP-0058 open): the VPS
  variant (build it now, as ratified) and a SINGLE-MACHINE variant (the node
  co-located with the agentic system as one installed QMX application, set
  up out of the box by a non-technical operator; Docker where it earns its
  place; the UI fronts an install page later). The single-machine variant
  and the self-setup installer are DESIGN-OWED: mint ONE epic for them whose
  first story is "run a one-shot bmad-architecture change increment for
  GAP-0058 (supervision without systemd, secrets without systemd-creds,
  powers channel without a unix socket, observability placement,
  installer)"; no other story in that epic starts before that ruling lands,
  and NO VPS epic blocks on it. Do not design the variant inside stories.
- qmn.venue is the ONE sanctioned qmf-venue importer; the cTrader transport
  increment lands in qmf-venue's ConnectionManager (A37) with the
  qmf.venue.connection async exemption; if the parent refuses the exemption
  it lands in qmn.venue.ctrader — the epics may not choose between them,
  they carry both as the declared fallback.

Sequencing rules: the cTrader transport increment + VenueClientPort (three
implementations: cTrader client, replay adapter, the FEAT-0023 conformance
double) is coded FIRST against the conformance double and is the first
story unblocked by the Spotware tokens for its live test; every QA-debt id
becomes a named story (QMX-F045, F046, F062, F063, F064, F067, F068, F069,
F102, D008, D010, E15-F01/F02/F03, E7-R28, E9-F04, E12-F01/F04/F05); the
stale packages/qmf-venue/README.md correction is a story; the four golden
scenarios SCN-0006/0008/0010/0011 are wired and proven by the node; nightly
mutmut extends to the node money-path modules on the code-carrying branch.

Suggested waves: W1 host + config + doors + observability (boot ceremony,
stand-down/resurrect, check mode, config compiler + value-status, three
doors, logs/metrics/health/alerts incl. the liveness heartbeat, toolkit
recipes, the five systemd units, ubuntu-24.04 CI lane, observability
compose); W2 venue transport (qmf-venue) + VenueClientPort + accumulator +
per-stream loop + order-path wiring + conformance double; W3 protection set
+ TN-25 virtual ledger + paper/demotion + reconciliation (four verdicts,
two residuals) + KSA; W4 data (live CT-10 producer, bootstrap, news-calendar
timer, backups + the three restore drills, evidence tier + sealed-archive,
hub) + secrets wizard + replay; W5 the paper-soak epic (deploy to the VPS,
the unattended week, checklist, benchmark baselines) = the live-milestone
gate; W6 MIS training + shadow rollout — the LAST epic, but mark it
PARALLEL-CAPABLE on its own branch from W3 onward (it touches no node code
until the shadow lane consumes a candidate): starting inventory = the
ratified labeler catalog (six rule-based: identity, spread-state,
gap-event, feed-state, SQS, degraded-sensors; one fitted:
liquidity_stress_v1, CPU quantile fit; one trained: regime_classifier_v1
with NO ratified model family, hyperparameters, label-generation method or
training location; recovered candidates Kronos/HMM/BOCPD/MS-GARCH carry no
authority) — so the first story is the regime_classifier_v1 DESIGN (model
family, features, label generation, data windows across all sessions,
evaluation), then data fetch/clean/label, then offline training as a
script the operator runs on his own machine (hours; seed and data window
recorded), model registration as versioned artifacts, shadow rollout,
re-certification over one full affected-Book cycle. Sequencing: W6 is the
LAST epic in importance; the fitted liquidity_stress_v1 needs no epic of
its own and ships with the rule-based labelers in W3. Human-only
steps to list inside the epics, never as blockers of unrelated epics:
Spotware app approval + sandbox token (Applications → Sandbox → Get token),
VPS procurement (an existing Linux VPS may serve the demo window), live
KYC, the swap-free admin-fee schedule in writing, the bucket account, the
backup-key escrow, the notification-channel account, the liveness-heartbeat
watcher account (free tier).
```

## 15. RESUME — QMA spine validation — OBSOLETE (closed dry 2026-08-29; the spine is export-ready — run prompt 12 directly)

```
Resume the QMA architecture sitting at _bmad-output/planning-artifacts/
architecture/architecture-QMA-2026-08-28/ (bmad-architecture, update
intent; .memlog.md is the authority — read its last 40 lines first). State
at pause: ARCHITECTURE-SPINE.md is 29 ADs, lint-clean, frontmatter
status: final, but validation is NOT dry: three divergence findings with
exact replacement text are saved at reviews/final-three-findings.json
(AD-6 record law vs the telemetry announcement exemption; AD-11's
agent-authored-hook validator must also reject verifier_ref; AD-22
role.base is a definition-store record written only by an operator-
principal role.set_base wire command, plus the AD-24 gate-list insertion).
Job: apply the three fixes surgically (touch nothing else), re-read the
neighbouring ADs (6, 8, 10, 11, 22, 23, 24) for adjacent consistency, lint
(uv run .claude/skills/bmad-architecture/scripts/lint_spine.py --workspace
<run folder>), then run ONE high-effort divergence-only verifier over the
whole spine (bar: a finding exists only if two builders obeying the text
literally would build incompatibly; empty result is valid). If zero:
update reviews/validation-report.md verdict to export-ready, append memlog
event "validation final: verified=true dry=true remaining=0". If not zero:
apply those, verify once more, and report the truth. Standing rulings
(never reopen): Quant; task/quant/experiment ledgers; Python 3.14 daemon;
contract-hub; workstation-default daemon + UI-driven remote deploy;
Skill/Loop/Graph with Graph Template vs Task Graph; qma.*; hooks on every
primitive; no external agent SDK; QMB path; no execution tool; admit/apply/
promote; plugin adopted, kernel only as "RLM kernel". Do NOT ask the
operator anything the transcript or memlog settled. Then hand off to
prompt 12 (documentation factory, QMA increment).
```
