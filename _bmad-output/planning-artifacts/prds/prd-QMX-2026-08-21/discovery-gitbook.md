# GitBook Discovery Extract — QMX PRD (2026-08-21)

Source: **https://elios-1.gitbook.io/qmx** — the live GitBook is the stable
product baseline and is **authoritative for risk, position-sizing, Book, and BMS
governance** content. Extract prepared as PRD discovery input. Anything below
that the GitBook states as law is a constraint the PRD **must not contradict**.

---

## 1. TOC / Site Map (URL inventory from firecrawl_map)

The GitBook is organized as an agent-consumable knowledge base with a prescribed
reading order (constitution → architecture → components → registries/contracts →
gap report → engineering workflow). Sections:

**Root / orientation**
- `/` — home
- `/agent-entry-point` — top-level orientation / reading order
- `/system-constitution` — the laws (L1..L14+, precedence rules)
- `/changelog`, `/glossary`, `/gap-report`, `/dead-decisions`

**Architecture**
- `/architecture` (index), `/architecture/overview`, `/architecture/dependency-graph`

**Components** (`/components/...`)
- `scalper-book` — the trading node / first Book template instance
- `book-template` — reusable Book template (charter + doors)
- `book-management-system` — BMS (Treasury/Exposure/Records/Reporting desks)
- `treasury-desk` — virtual capital ledger, seed→cap cycle, sweeps
- `kill-switch-authority` — KSA global protection state machine
- `market-intelligence-service` — MIS (Live + Archive), information-only
- `examination-engine` — bot certification against a book
- `paper-mode-system` — benching / counterfactual paper trading
- `broker-adapter` — platform-blind broker execution (cTrader Open API)
- `data-layer` — immutable MIS emissions + append-only BMS journals
- `notification-system` — operator-facing event delivery
- `qml-library-layer` — shared deterministic library layer (interfaces open)

**Registries** (`/registry/...`): `variables`, `formulas`
**Contracts** (`/contracts/...`): CT-BOOK-01/02, CT-BMS-01..05, CT-MIS-01/02,
CT-KSA-01, CT-ADAPTER-01, CT-EXAM-01/02, CT-DATA-01, CT-NOTIFY-01,
CT-PAPER-01, CT-QML-01
**Scenarios** (`/scenarios/...`): SCN-0001 money-ladder, SCN-0002 rollover-sweep,
SCN-0003 news-block
**Lenses** (`/lenses/...`): security-model, incident-playbook, ops-runbook,
logging-spec, metrics-and-alerts, test-strategy, fixtures-and-scenarios,
mlops-data-pipeline, mlops-model-lifecycle, data-layer-lens, performance-budgets
**Decisions** (`/decisions/...`): ADR-0001 authority-hierarchy, ADR-0002
template/instance split, ADR-0003 transcript-authority
**Knowledge** (`/knowledge/...`): documentation-method, engineering-workflow

---

## 2. Per-Page Product Framing

### `/architecture/overview`
QMX is a **"deterministic trading architecture for book-governed bots."** Every
bot action is validated and constrained at multiple checkpoints before broker
execution: *"The examination engine certifies a bot against a book. The book
receives bot intent and runs the doors before anything reaches the adapter."*
An **Operator** manages via periodic reviews (A1 and Sunday reviews), working
with BMS as the control interface. Two domains:
- **Certification layer** (research/validation): COMP-EXAM, COMP-QML,
  COMP-MIS-ARCHIVE.
- **Runtime layer** (execution/control): COMP-BOOK-SCALPER (bot-command receiver
  / first book template) → COMP-MIS-LIVE (real-time market data) → COMP-BMS
  (accounting, constraint, journaling) → COMP-KSA (global protection) →
  COMP-ADAPTER (broker-agnostic, cTrader Open API).
Execution flow: bot intent → book validates against MIS snapshot → BMS applies
constraints + logs → KSA final protection → adapter → broker.

### `/system-constitution` (LAWS — hard constraints for the PRD)
- **L1 Market isolation:** *"Bots trade; books control bots; BMS accounts for and
  constrains books; nothing above a bot touches the market."*
- **L3 Autonomy:** system runs **unattended**; *"intraday human judgment is
  invalid except A1 resurrection and Sunday committee review."*
- **L4:** *"Unclaimed or freed risk budget is never redistributed during a cycle."*
- **L5:** *"A cycle is a seed-to-cap event; money resets between cycles, while
  knowledge persists."*
- **L6 MIS:** *"publishes information only; MIS never sizes, blocks, or trades."*
- **L14 Ledger integrity:** *"Unexplained drift between the BMS virtual ledger and
  broker reality is a technical kill."*
- Authority flows **bot → book → BMS → operator**; operator retains only *"A1
  resurrection, Sunday review, and ratification."*
- Precedence: documentation conflicts resolve *against the ledger and source
  authority rules*, not convenience.

### `/agent-entry-point`
QMX is *"a deterministic trading architecture where bots trade, books control
bots, and BMS accounts for and constrains books."* The audience is **the
operator/team implementing and modifying the trading architecture itself, not end
traders.** Three tiers: autonomous trading agents (base), portfolio Books
managing agents, BMS enforcing constraints (top). Docs prioritize hard rules over
flexibility; operator is the source of authority for ambiguity. Unresolved items
are explicit GAP entries; dead ideas are separated from ratified law.

### `/components/scalper-book` (the trading node / Book)
A **Book is a template instance**. Scalper Book = *"a treasury-customized
cash-flow machine judged by swept cash per month per dollar of seed."*
- **May:** select global infrastructure, run the scalper profile, offer risk
  seats, apply decision gates ("doors"), bench bots to paper, sweep cash at
  rollover.
- **May never:** *"become the global template, defend itself by headline equity
  curve, compound between cycles, or trade directly."*
- Lifecycle: live vs. configurable capital limits → paper after consecutive
  stop-outs → terminate live if kill line crossed (*"flip to paper until
  cycle-boundary re-seed; live remnant restart is dead"*) → sweep at rollover.
- Consumes MIS snapshot; produces treasury events, paper-transition commands,
  adapter commands.
- Operator configures seed capital, risk params, budget coefficients via registry
  values; sensitive vars (seed capital, budget shaping) are **operator-
  countersigned**.

### `/components/book-management-system` (BMS)
*"BMS accounts for and constrains books. It has Treasury, Exposure, Records, and
Reporting desks, and it never trades, sizes, or reaches inside a book."* (DEC-0045)
- Owns virtual ledger state + append-only journals (**Records desk = exclusive
  write path**); measures exposure; owns mode registry + reporting metrics.
- **Never:** trade directly, mutate bot logic, overwrite journals in place, or
  bypass the veto ledger. Reporting computes metrics but has **no authority**.
- Every rejection ("no") must be journaled; unjournaled rejections violate
  governance. Unclear desk authority stays deliberately unassigned (no silent
  authority).

### `/components/book-template`
Template/instance split: *"The template is documented separately from any book
instance so scalper-specific values do not become global values"* (ADR-0002).
Defines **four charter slots** — *"game played, money shape, customer plus
headline metric, and death condition"* — and **seven operational "doors"** (each a
decision gate): footprint validation, viability, R_max limits, daily budgeting,
breaker, exposure tracking, kill switch. Also defines authority boundaries,
interface contracts, config variables, failure modes. (Instantiation workflow not
fully detailed on-page.)

### `/components/treasury-desk` (RISK / SIZING / MONEY-PATH — authoritative)
Owns the virtual capital ledger and the book↔treasury boundary: *"Only sweep,
refund, and re-seed cross that boundary."*
- Cycle: *"The cycle is seed to cap. The book compounds within a cycle and
  ratchets between cycles."* Seed (S) = starting capital; Cap (C) = ceiling via
  **FORM-0001** modulated by `scalper_cap_multiplier`; instance-specific **kill
  line**.
- Sweeps at **rollover only**: *"If cap is hit intraday, the book completes the
  day and sweep uses rollover equity"* (no forced mid-session liquidation).
- Failure modes: broker/ledger drift → immediate halt (DEC-0015); **mid-cycle
  top-ups rejected / permanently disabled** (DEC-0020); **live restarts from
  remnants rejected**, cycle-boundary re-seed required (DEC-0023).
- May record seeds, equity changes, reconciliation verdicts; **may never** revive
  the dead mid-cycle top-up path or treat broker withdrawals as automatic.

### `/components/kill-switch-authority` (KSA)
*"The global protection state machine."* BMS owns policy; the trading node
enforces via adapter; bots are isolated. **Five levels:** GREEN, YELLOW, ORANGE,
RED, BLACK (progressively restrict). **Four trigger classes:** scheduled news,
black-swan, connectivity failure, unknown state. On trigger, blocks affected
pairs globally for live and paper. **Never** de-escalates automatically, never
asks bots to interpret state; *"automatic transitions may escalate only; A1
required for de-escalation."*

### `/components/market-intelligence-service` (MIS)
Computes and publishes **typed market snapshots**, stores immutable emissions,
versions labelers, supports replay queries, exposes degraded sensor state.
**MIS-Live** feeds COMP-BOOK-SCALPER (CT-MIS-01); **MIS-Archive** feeds COMP-EXAM
(CT-MIS-02). Boundary: *"MIS is information-only and never sizes, blocks, or
trades"* and must not let exam/live labeler versions drift silently.

### `/components/examination-engine`
*"The examination engine certifies whether a bot can join a specific book"* —
against the book contract, not in the abstract. Tests bot against historical data
via replay; measures in-sample/out-of-sample; checks edge survives costs. Outputs
**exam certificate (CT-EXAM-01)** + **cohort correlation certificate
(CT-EXAM-02)**. Gate conditions: *"The edge is real after costs"* and *"The
candidate is not fiction."* **Never** authorizes live trading, changes a book
profile, or bypasses exam-live parity — certification ≠ deployment authority.

### `/components/paper-mode-system`
Paper mode *"freezes the counterfactual balance at flip and preserves evidence
after a breaker, kill-line stand-down, or demotion."* Entry: after
`registry:scalper_breaker_threshold` consecutive stop-outs, bot benches to paper
for the rest of the day and **auto-resets at next open**. **Never** hand-adjust
paper balance, revive live-restart-from-remnant, or treat paper gains as treasury
cash. Circuit-breaker pattern; live↔paper is a defined state machine.

### `/components/broker-adapter`
Platform-abstraction layer between bots and broker execution; translates
platform-blind commands to broker-specific ops. Position: receives commands from
Book Scalper, consumes KSA state, emits reconciliation to Treasury. **May:**
translate commands, maintain account binding, enforce fail-safes, surface unknown
state. **Must not:** expose broker APIs to bots, choose trade permission, or hide
reconciliation drift. Principle: *"Bots never see broker platforms, and KSA
reaches bots only through effects."* On startup emits `unknown_state` and blocks
until reconciliation (does not invent a target level). Broker = cTrader Open API,
though cTrader capability is flagged unvalidated (GAP-0005/0015).

### `/components/data-layer`
Provides storage for **immutable MIS emissions** and **append-only BMS journals**
where a component contract names an owner. **Never** silently choose
source-of-truth ownership, rewrite append-only journals, or set retention/
migration policy without a GAP. In-place updates rejected — *"Reject and append
correction instead."* Ownership via Data Ownership Register (CT-DATA-01).
Retention/backup/migration/schema boundary **remain open (GAP-0003)**.

### `/components/notification-system`
Reads journal-derived events, proposes severity, dedupes incidents, delivers
**operator-facing messages** after rules are ratified. **Never** asks for intraday
trade judgment, overrides protection, invents its own severity table, or defines
a UI inbox in this run. Constraint: *"must not create intraday human judgment
loops."* Severity/channels/dedupe/quiet-hours under GAP-0002.

### `/components/qml-library-layer`
QML = the custom library layer; hosts shared domain types, adapter-neutral
contracts, and reusable **deterministic** library interfaces once ratified. Must
**not** become an agentic workflow surface in the deterministic pass or silently
define interfaces. (Note: the live GitBook frames QML conservatively / interfaces
open under GAP-0013; the local `docs/` corpus has since absorbed a richer QML
bot-authoring increment — the PRD should reconcile the two, treating GitBook as
the stable baseline for governance and local docs for the newer bot-authoring
framing.)

### `/scenarios/scn-0001-money-ladder` (golden money path)
Day opens after rollover with book equity **E = seed**. Then:
1. **Runway U = E − `registry:scalper_kill_line`.**
2. **Daily loss budget D = U / `registry:scalper_runway_divisor`.**
3. **Offer per seat** recomputed from **FORM-0004**; **final take** is **FORM-0005**.
Constraint: *"Any conversation number for U, D, offer, take, cycle-day count,
monthly envelope, or worst case is a checksum, not an authority source"* — the
registry/formulas are the authority, not narrative numbers.

### `/decisions/adr-0001-authority-hierarchy`
Chain: **Bots → Books → BMS → Operator.** *"Keep strict hierarchy — chosen
because each layer owns one authority."* Bots: no visibility into platforms or KSA
(DEC-0008). MIS read-only (DEC-0007). Each new component must declare its role —
**sensing, deciding, accounting, or executing.** Rationale: strict separation
prevents bots circumventing controls and keeps market ops insulated from
higher-level interference while preserving oversight.

---

## 3. Constraints the PRD MUST NOT contradict (consolidated)

1. **Nothing above a bot touches the market** (L1); only bots trade.
2. **Unattended operation**; no intraday human judgment except **A1 resurrection**
   and **Sunday committee review** (L3). Notifications must not create intraday
   human-judgment loops.
3. **Seed→cap cycle**; money resets between cycles, **knowledge persists** (L5);
   book compounds within a cycle, ratchets between cycles.
4. **Risk budget never redistributed mid-cycle** (L4); **no mid-cycle top-ups**
   (DEC-0020); **no live restart from remnant** (DEC-0023).
5. **MIS is information-only** — never sizes/blocks/trades (L6).
6. **BMS never trades, sizes, or reaches inside a book**; Records desk is the only
   write path; journals are append-only (correct by appending, never rewrite).
7. **Ledger↔broker drift = technical kill** (L14); adapter blocks on unknown state
   until reconciled.
8. **KSA escalates automatically but only A1 de-escalates**; bots never interpret
   KSA state (reached only through effects).
9. **Exam certifies but never authorizes live**; exam-live parity must hold.
10. **Sweeps at rollover only**; cap-hit intraday completes the day.
11. **Strict authority hierarchy** bot→book→BMS→operator; each component declares
    exactly one role (sensing/deciding/accounting/executing).
12. **Registry values + formulas are the authority**; narrative numbers are
    checksums. Sensitive registry vars are operator-countersigned.
13. Open items are governed by **GAPs** (e.g. data-layer retention GAP-0003,
    notification design GAP-0002, cTrader validation GAP-0005, QML interfaces
    GAP-0013) — the PRD should not silently close them.

---

## 4. Product story (one paragraph)

QMX is a deterministic, self-governing automated-trading platform run by a single
**operator** (not end traders). Autonomous **bots** generate trade intent; a
**Book** (first instance: the Scalper Book, a "cash-flow machine judged by swept
cash per month per dollar of seed") gates every intent through its charter
"doors"; the **BMS** accounts for and constrains books across Treasury/Exposure/
Records/Reporting desks without ever trading; the **Treasury** runs the seed→cap
money ladder with rollover-only sweeps and no resurrection paths; **KSA** provides
an escalate-only global protection state machine; **MIS** publishes information
only; the **Examination Engine** certifies a bot against a specific book before it
can be deployed; and the **Broker Adapter** executes platform-blind against
cTrader while bots never see the broker. The whole thing runs unattended, with the
operator limited to A1 resurrection, Sunday committee review, and ratification —
all state append-only and reconciled against the ledger as source of truth.
