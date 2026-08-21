# Wiki mine — second half (platform-above-framework extract)

**Source:** `C:/Users/Mubarak/Documents/QMX/wiki`, ascending path sort, indices
floor(93/2)=46..92 (1-indexed lines 47–93 of the sorted list; 47 files). The two
`.js` mermaid assets fall in the first half, so this range is all content.

**Judged against:** `prd-QMX-2026-08-21/prd.md` (read in full) and the current
`docs/` corpus state summarized in the task context.

**Framing of this wiki:** it is the *later* pre-QMF redocumentation
(GitBook capture 2026-07-18 + July-2026 BMad planning run + recovered artifacts).
Its authority order is Architecture-Spine → PRD/addendum → wiki → memlog. Almost
all of its *mechanics* (authority chain bot→book→BMS→operator, cycles/sweep,
KSA/leash, doors, Records streams, four data classes, CT-BMS/CT-BOOK/CT-ADAPTER
contracts) are the **trading-node (Phase 2) GitBook baseline** the current corpus
already treats as authoritative-for-the-node and expects to be rewritten on QMF.
Those are **not** carried here — they are already reflected in the corpus's
qmf-risk contracts (CT-22..32) and the Phase-2 node outline (PRD §6).

What IS worth carrying is the **platform ABOVE the framework** — the material the
current PRD only stubs: the **QMX terminal / trading console** (PRD §6 Phase-3, an
inferred `[ASSUMPTION]` paragraph), and the **platform-integration / operator-
workflow / observability** surfaces that sit between the node and the operator.
The single richest new artifact in this half is
`decisions/trading-console-alignment.md` — a full evidence-boundary register for
the terminal UX phase that the current corpus does not carry at all.

Agentic depth is de-scoped throughout (the wiki itself scopes the agentic UI out
of the console phase, UD-04).

---

## A. Trading-console (QMX terminal) design register — the biggest gap

**Where it lives:** `decisions/trading-console-alignment.md`, cross-cut by
`lenses/operations.md`, `lenses/observability.md`, `overview.md`.

The current PRD's terminal treatment (§6 "QMX terminal (Phase 3)") is one inferred
paragraph flagged `[ASSUMPTION: capability list inferred ... no terminal design
exists yet]`. The wiki actually holds a ratified-in-old-planning **system-truth
register** that translates system behavior into UI consequences and backend
obligations *without* deciding layout/styling. It is exactly the missing Phase-3
capability spine. Post-QMF-durable content:

**Product/deployment boundary (survives QMF):**
- The console is **UI-only**, **never a second system of record**; business
  authority, persistence, and command validation stay server-side.
- The console is a **desktop application that holds no trading secrets**; desktop
  availability must not imply possession of trading credentials.
- It is **not a manual-trading or generic market-analysis terminal** — optimize
  for system operation, safety, evidence, and repeated expert use. Trading stays
  behind bots/books/BMS/KSA/adapter.
- **Unattended-by-default UX:** the interface must not invent an intraday
  human-control loop; avoid manual-order ergonomics and action queues that demand
  continuous operator decisions. Commands map to *ratified operator powers*, not
  arbitrary runtime mutation.

**Command model — the "Powers API" (survives QMF as the terminal↔platform seam):**
- Console commands target a trading-node **Powers API**; the console cannot bypass
  it to directly mutate orders, sizing, modes, ledgers, or bot state.
- **Evidence review and command execution are visibly distinct steps.**
- **Command preconditions rerun on the trading node at click time** and return an
  authoritative committed outcome (event identity / audit linkage) — never an
  optimistic success flag. Stale backend evidence **never** authorizes a command.

**Ten derived design-evaluation criteria (durable UI invariants):**
authority clarity; **state independence** (see §B); evidence linkage; source &
freshness; guarded powers; unattended-by-default; progressive disclosure; domain
fidelity; backend feasibility; **venue containment** (see §F).

**Explicit anti-goals (durable):** no direct manual-trading surface; **no generic
LIVE/PAPER operator toggle**; **no single global health indicator that hides
independent failure domains**; no stale backend evidence authorizing an action; no
editable setting without registry-backed configurability; no optimistic command
success without server validation + evidence; no agent-development workspace or
Prometheus/Grafana clone; no assumption that future venues are recolored forex.

**UI-to-backend adaptation register — named backend contracts the terminal needs
(still-open work, but the *list* is the requirement):** trading-console
evidence-read channel (transport, read models, authz, source/freshness metadata,
degraded behavior, pagination/streaming); Powers-API command envelope (ids,
preconditions, acks, refusals, idempotency, committed outcome, audit refs);
operator identity + small-team readiness; promotion/registration fields
(click-time validation result, refusal detail, `ADMITTED` response, evidence
linkage); A1-recovery command contract; reconciliation-status fields (report id,
account scope, generation time, validity age, evidence refs, recovery progress);
sync/evidence-freshness fields; connection/execution-readiness states; venue
context/toggle; activation-after-`ADMITTED`.

**Process note (transferable to the eventual UX pass):** approval gates run
system-truth register → UX brief/IA/flows/states (no code) → reconcile prior
Figma/journeys → low-fi wireframes + style tiles → one hi-fi vertical slice →
extract Design System v0.1.

*Post-QMF disposition:* the node-runtime specifics behind these obligations will
be rebuilt on QMF, but the **console-as-UI-only**, **Powers-API-at-click-time**,
**evidence-vs-command separation**, and the **anti-goals** are architecture-neutral
and should seed the Phase-3 terminal PRD/architecture rather than being
re-derived. This turns the §6 `[ASSUMPTION]` stub into a grounded outline.

---

## B. Terminal status model: state independence + read authority/freshness

**Where:** `trading-console-alignment.md` (criteria 2 & 4; ST-16..21), reinforced
by `lenses/operations.md`, `lenses/observability.md`.

A crisp, QMF-durable platform requirement the corpus lacks: **safety, execution
readiness, connection, reconciliation, data freshness, lifecycle, and sync are
independent states and must never collapse into one health color.** Corollaries:
- Distinguish **"trading operational"** from **"evidence sync degraded."**
- Show **requested protection state separately from enforcement completion**
  (KSA escalation is requested; enforcement isn't complete until account
  connections quiesce and drain).
- Every important read reveals **authority source** (live authoritative vs
  replicated evidence), **source time, receive time, watermark**, and **authority
  classification** — i.e. read models carry provenance/freshness, not a spinner.

This is a platform-legibility law (operator + agent), independent of the node
rewrite. It enriches NFR-10 (one-person operability) and the terminal outline.

---

## C. Guarded-power operator-workflow contract (A1 / promotion / ratification)

**Where:** `trading-console-alignment.md` (ST-06..08, ST-13, ST-15; adaptation
register), `lenses/operations.md`, `topics/registration-and-promotion.md`.

The corpus captures the *authority* (bot→Book→BMS→operator; human-signed
promotion, SCN-0007; resurrection/review/ratification, L17/L36) but not the
**operator-facing power contract** the terminal must honor:
- Named operator powers = **A1 resurrection, ratification/promotion, Sunday-review
  actions**. A1 is a **guarded recovery command, never an ordinary toggle**.
- Each guarded power exposes **impact preview, preconditions, server validation,
  outcome receipt, and audit linkage**; A1 additionally needs allowed-transition
  set + confirmation.
- **KSA escalates automatically but cannot de-escalate automatically — only A1
  de-escalates**, and only after connections quiesce/drain (requested vs enforced,
  per §B).
- Kill-line recovery is **cycle-boundary `re_seed` only** — the terminal must
  **not** expose resume/top-up/hand-edited-balance actions; it shows the next
  valid system boundary instead.
- Promotion is a **manual ratification click that shows evidence and reruns the
  precondition battery server-side at click time**; success lands `ADMITTED`
  (no ledger, no intents), distinct from book mode and execution readiness.

*Post-QMF:* the exact command schemas are node-phase, but the **guarded-power UX
contract** (preview → precondition rerun → confirm → outcome receipt → audit) and
the **requested-vs-enforced** separation are durable operator-workflow
requirements.

---

## D. Registry-metadata-driven editability + provisional-value console countersign

**Where:** `trading-console-alignment.md` ST-09; `registry/variables.md`,
`registry/index.md`; `topics/registration-and-promotion.md`.

The corpus has `configurable:true ⇒ UI-editable` and "blank risk blocks live
money" (L38, NFR-07). The wiki adds a **richer editability model the terminal must
implement:**
- **Editability is evidence-driven.** `measured`, non-configurable, `provisional`,
  and `null` values are **not editable defaults** and must not masquerade as
  settings. (E.g. `scalper_mean_loss_r` is `measured` per bot at exam;
  `order_latency_min_ms` is non-configurable while `_max_ms` is configurable.)
- **Registry metadata must expose ownership, qualifier, value status, and
  ratification requirements** so the UI can decide editability from data.
- **Provisional values require an explicit operator countersign via the console
  before live** (e.g. `roster_capacity = 6 PROVISIONAL`, "operator countersign via
  console before live"). This is a concrete operator workflow, not just "edit a
  number."

*Post-QMF:* the specific pre-QMF variable values are node/GitBook baseline
(superseded by the QMF variables registry), but the **metadata-driven editability
+ provisional-countersign workflow** is a durable terminal/config-surface
requirement that sharpens NFR-07.

---

## E. Multi-operator (~3) readiness — attribution + operator identity

**Where:** `trading-console-alignment.md` UD-01 + adaptation register
("operator identity and small-team readiness").

The corpus is strongly *solo-operator*. The wiki records a real future-scope
direction: **one primary operator now, possibly a small team of ~3 later.**
Consequence: **do not build enterprise collaboration now, but preserve named
action attribution and avoid anonymous single-user assumptions.** Operator
identity/authentication/authorization/session/attribution/concurrency is an
explicit unresolved backend contract to define *before* multi-operator UI work.

*Post-QMF:* keep the hook — journals/lineage already attribute actions; the ask is
to not hard-bake "one anonymous user" into the terminal or the Powers-API identity
model. Non-agentic. Belongs in the terminal/platform-integration outline.

---

## F. Venue-selector product shell / venue containment

**Where:** `trading-console-alignment.md` UD-02/UD-03 + criterion 10;
`open-questions.md`, `sources/bmad-planning-run-2026-07.md`.

The corpus scopes V1 to the seeded forex vertical and puts crypto/stocks out of
scope, and qmf-venue is venue-neutral below the port. The wiki adds the
**product-shell framing above the framework** that the corpus lacks:
- Future forex-adjacent, crypto, and other venue experiences should be reachable
  through the **same product shell** via a **venue selector** — valid shell
  architecture — **but each venue may have a different information model.**
- **Venue containment:** forex must work completely on its own; **future venues do
  not force false shared concepts into the forex UI**, and are not "recolored
  forex."
- Mechanism: future venues enter QMX as in-system components **behind their own
  externally designed and ratified adapters** (consistent with qmf-venue).

*Post-QMF:* a durable terminal/shell design principle for Phase 3 (venue-isolated
information models under one shell), de-scoped to a design constraint, not a V1
build.

---

## G. Two-plane observability + fixed notification event-class allow-list

**Where:** `lenses/observability.md`, `lenses/operations.md`, `overview.md`,
`gap-report.md` (GAP-0009 closed, GAP-0002 open).

The corpus NFR-10 says "monitoring/evaluation built in, not bolted on" and the
unattended doctrine says notifications must not create intraday loops. The wiki
adds the **specific platform observability shape**:
- **Two distinct layers that must not be conflated:** (1) authoritative system
  records used to explain/constrain behavior (veto ledger, journals, lineage);
  (2) operator notification delivery, whose policy is separate and lower. **Losing
  a notification never erases underlying BMS/KSA evidence.**
- **External, zero-authority monitoring plane = Prometheus + Grafana** (Loki
  optional); it consumes synced metrics and holds no trading authority. The
  console **must not become a Prometheus/Grafana clone**.
- **Notifications fire only for a fixed, closed event-class allow-list** — sweep,
  `re_seed`, refund (dormant in V1), KSA/kill-switch events, supervision
  fail-closed. **Everything else is console evidence / UI log**, not a
  notification. Delivery mechanics (channels, retries, dedup, quiet hours,
  credentials) remain open (GAP-0002).
- Metrics are collected in **hot/warm/cold measurement tiers**; **journal
  durable-commit latency is a required hot-tier metric from day one**; every
  latency measurement is per-hop with structured timestamps and carries the
  **snapshot version** when market state influenced a decision.

*Post-QMF:* the Prometheus/Grafana substrate and latency budgets are node-phase,
but the **two-plane authority separation**, the **fixed notification allow-list**,
and **console-evidence-vs-notification** distinction are durable platform framing
that belongs alongside the unattended doctrine and NFR-10.

---

## H. Node↔terminal integration boundary: evidence node, sync, no-secrets console

**Where:** `overview.md`, `lenses/data-and-ml.md`, `trading-console-alignment.md`
ST-16..21.

Platform-integration topology the corpus only implies. Durable boundary
principles (mechanics themselves are Phase-2 node, GitBook-baselined, likely
QMF-rewritten):
- **Three deterministic nodes:** single-process **trading node** (authoritative
  live state), always-on **backend evidence node** (read replicas, dossiers,
  certificates, sync ledgers — **never a second writer**), and the **desktop
  console** (UI-only, no secrets).
- **The console reads the backend evidence node, not the trading hot path.**
- **Sync is one-way, idempotent, resumable, watermarked, verify-before-purge**
  (CT-SYNC-01 v2 shape); **backend failure never blocks the trading hot path**;
  unsynced trading-node data is retained until backend persistence is verified.
- Read models therefore need source identity/time, receive time, watermark, and
  authority classification (ties to §B).

*Post-QMF:* carry the **read-model source-authority separation** and the
**verify-before-purge / hot-path-never-blocked** principles as platform
integration invariants; treat the storage engines (SQLite/PostgreSQL/DuckDB/
Parquet) as node-phase implementation, subject to the QMF rewrite.

---

## I. One-person deploy/ops posture: systemd + crash-loop → fail-closed stand-down

**Where:** `lenses/operations.md` (Open surfaces), `overview.md`.

Enriches the corpus's primary success lens (PRD §9 DevOps, NFR-10). Node-phase but
concrete:
- Trading + backend nodes on **Linux under `systemd` units** (`Restart=on-failure`,
  start-limit counters); node-service secrets via **`systemd-creds`**.
- On **crash-loop threshold (`K` restarts in `T` minutes, both null-until-ruled)**,
  the process **boots alive into fail-closed stand-down**: sequencers refuse and
  append evidence, adapter connections quiesce and drain, and the **Powers API
  remains available** (so recovery controls stay reachable in degraded/stand-down
  states — ST-21).
- If it cannot boot even into stand-down: **wrapper notification + restore** path.
- London-cloud Linux is the target; **laptop/WSL2 is bootstrap parity only**.

*Post-QMF:* the "boots into stand-down rather than dying, Powers API stays up,
recovery reachable while degraded" posture is a durable operability requirement
for the node/terminal phases; the exact systemd/creds choices are Phase-2 detail.

---

## J. (Framework-level, lower priority) Attribute register + binding allow-list

**Where:** `topics/attribute-model.md`.

Not strictly platform-above-framework, but a distinct governed surface that may not
be fully captured by the QMF variables registry / qmf-registry — flag to
check-against, not assume-absorbed:
- **Attribute register:** versioned, append-only definitions (name, scope
  bot/book, type/units, qualifier, owner, semantics, DEC link); **immutable and
  versioned**; lifecycle `experimental → operator ratification → ratified`;
  experimental attributes are observable but **unbindable**.
- **Binding allow-list:** decision logic reads an attribute only through an
  explicit **`(attr_id, version)` binding allow-list** — the explicit act that
  permits a versioned attribute to shape behavior.
- **Promotion-to-typed-columns:** when an attribute becomes behavior-shaping its
  numeric value migrates to the variable registry under instance ownership;
  non-numeric behavior-shaping values (pair/session scope) become **typed promoted
  core columns**; the **JSON attribute bag is never the primary filter surface**;
  **EAV is forbidden**.
- **Inertness boundary (QML-relevant):** a bot may *declare* attributes but
  **cannot read its own declared attributes at runtime**; if bot logic consumes an
  attribute, that attribute is part of the bot spec identity and changing it mints
  a new `bot_spec_version`.

*Post-QMF:* verify against qmf-registry + variables registry (L38) and QML
(CT-33). If the binding-allow-list + inertness boundary is not already bound, it is
a worthwhile registry/QML enrichment; if it is, this is confirmation only.

---

## Deprecated / superseded (confirmed dead or node-baseline; NOT carried)

- **"Desktop console is load-bearing V1 scope" (GAP-0014, July run)** — *tension
  with current phasing.* The current corpus places the terminal at **Phase 3**
  (out of V1). Carry the console *content* (§A–F) as Phase-3 seed, but note the old
  "V1 console" framing is superseded by the QMF-first, terminal-last sequence.
- **All pre-QMF node contracts** — CT-BMS-01..05, CT-BOOK-01..03, CT-ADAPTER-01,
  CT-KSA-01, CT-MIS-01/02, CT-PAPER-01, CT-EXAM-01/02, CT-NOTIFY-01, CT-DATA-01,
  CT-QML-01, CT-SYNC-01, CT-REG-01, CT-ATTR-01 — superseded by CT-01..CT-34.
- **Node mechanics already in corpus/Phase-2 outline** — authority chain,
  cycles/seed-to-cap, rollover-only sweep, KSA escalate-only + A1 de-escalation,
  seven book doors, leash chain, reconciliation drift = technical kill, news
  blocks live+paper, four data classes, Records five append-only streams, MIS→KSA→
  adapter protection funnel, `ADMITTED`→`LIVE` activation, breaker bench/auto-reset.
- **Recovered-era dead ideas (dead-decisions.md)** — RMF declared weights,
  TIGHTEN half-size kill, mid-cycle top-up, region-shift budget rotation, human
  intraday chorus review, live restart from kill-line remnant, uniform values
  across books, session windows as trading authority. Plus ruled-out DPR/PRS
  capital authority, WF-stage lifecycle, slot auctions, paper-to-live redemption,
  global bot-pool merit ranking, second Records writers, crypto-adaptable V1
  grammar, MCP/live agent surfaces.
- **Global SL/TP authority + amend_order mechanics** (`position-safety-*.md`) —
  donor design; stop-policy grammar now belongs to book money rules; `amend_order`
  unresolved; carried nowhere as platform framing.
- **Backtest/replay recovered mechanics** (`backtest-and-replay.md`) — reproduced
  by QMB specs (one run loop, config-fingerprint run id, WF/MC/PBO/CSCV battery
  values, four-key reproducibility). Already in corpus §5 G.
- **Agentic UI** — the wiki itself scopes it out of the console phase (UD-04);
  consistent with the corpus's own-track de-scope.
