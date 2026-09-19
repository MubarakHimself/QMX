# 06 — QMX authority and dataflow (regime / placement lens)

Research note for REGIME and PLACEMENT work. Not a physics essay. Not production code.
Cites `docs/` and `integration` package surfaces only. Read with `OPERATING_LINE.md`.

## 0. Hard fence (do not smuggle)

A **market-state / regime / placement model** may label, filter, or veto. It must **not**:

| Smuggled claim | Who actually owns it | Cite |
|---|---|---|
| Profitability / edge | Book admission bar + human promotion; QMB only *publishes* CT-32 | `docs/components/qmb.md` (May never: bench/promote/bind); CT-32 |
| Sizing (`requested_r`, lots, R ladder) | **Book** at CT-23 door; bot proposes advisory `proposed_r` only | `docs/contracts/ct-23-risk-evaluation.yaml`; `docs/components/qmf-risk.md` |
| Execution / venue commands | **QMN** via `VenueClientPort` / `qmf-venue`; QMB/QML/QMA never import venue | `docs/components/trading-node.md`; ADR-0019 |
| Playbook / Book switching | Operator + binding records; not MIS | AD-29 chain in `qmf-risk.md` |
| Kill / flatten / resume | KSA / Book kill-line / operator; sensors are **inputs** | DEC-0150; TN-7 |

**Constitutional order (verbatim):** *Bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market.* Hierarchy: `bot → book → BMS → operator` (`docs/components/qmf-risk.md`, DEC-0143).

---

## 1. Layer map (who is what)

| Layer | Code / COMP | Role | Authority |
|---|---|---|---|
| **QMF** | seven roster packages under `packages/` | Contract hub: exact money/time, registry, data rooms, indicators (CT-16), structure (CT-17), venue shapes, risk shapes | Defines nouns and doors; **runs no loop**, places no orders |
| **QML** | `qml/` (`COMP-QML`) | Bot authoring: CT-33/CT-34, runtime protocol, conformance | Authors intents; **never sizes**, never venue |
| **QMB** | `qmb/` (`COMP-QMB`) | Experimentation / backtesting; `world = replay` | Pure `run()` + impure orchestrator; **publishes** CT-32; never benches/promotes/binds |
| **QMN** | `qmn/` (`COMP-QMN`) | Trading node; modes `paper \| live` | Sole `qmf-venue` wirer; hosts seats; runs Book/BMS/KSA/MIS seam |
| **QMA** | `qma-*` | Agentic daemon | Candidates a **human** promotes; **no** venue; **no** QMA-paper |
| **MIS** | `qmn/mis/` (node seam, not a QMF library) | Labeler layer → **signal snapshot** | Closed consumers: **Book door + KSA only**; bots never |

Sources: `docs/architecture/overview.md`, `docs/architecture/stack.md`, `docs/architecture/dependencies.yaml`, `docs/glossary.md` (MIS, signal snapshot), ADR-0017/0018/0019.

**DEC-0089:** MIS is *not* a QMF V1 library (`docs/gap-report.md`). It is built on the node with `qmf-data` / `qmf-indicators` contracts.

---

## 2. Authority by concern (regime-relevant)

### 2.1 MIS / market-state labels

- **Produces:** per-instant **signal snapshot** (immutable, frontier-bound, freshness = Book `decision_freshness_bound`).
- **Governed consumers (closed):** Book door + KSA. **Bots never consume** (`docs/components/trading-node.md` TN-19; `docs/glossary.md` MIS / signal snapshot; `OPERATING_LINE.md`).
- **SQS:** Spread Quality Sensor — CT-16 configured producer, **block-only** V1. Computes; transport carries; **Book door decides**. Never sizes (`docs/components/qmf-risk.md` SQS; DEC-0153). Delivered **inside** the snapshot only (one SQS value per instant).
- **V1 governed producers (docs + `OPERATING_LINE.md`):** identity, spread-state, gap-event, feed-state, SQS, degraded-sensors, fitted `liquidity_stress_v1`.
- **`regime_classifier_v1`:** design story (GAP-0051). Docs: no ratified family/hyperparams/training location (`docs/glossary.md`, DEC-0262). On `integration`, design surface chooses `lightgbm-multiclass` with classes `quiet|normal|elevated|stressed` (`qmn/src/qmn/mis/regime_design.py`) — still **unbound** as a live governed producer; catalog refuses trained classifier bind (`qmn/src/qmn/mis/catalog.py`). Kronos/HMM/BOCPD/MS-GARCH **unauthoritative**.
- **A classification score is not a trading edge** (`OPERATING_LINE.md`). MIS does not size, does not switch playbooks, does not own entries.

### 2.2 Book / BMS / CT-23 door

- **Book:** admission, sizing, exit policy, leash, protection windows, SQS/MIS *consumption at door*, paper routing.
- **BMS:** one per account; accounting, constraints, kill-line series, control-rank table.
- **CT-23:** bot → Book intents. Entry: advisory `proposed_r` + optional `advisory_stop_proposal`. Book resolves `requested_r` and declared full-loss price. Exit kinds V1: `close_full | tighten_protective_stop` only.
- **CT-22:** Book charter (v2): `admission_bar`, `exit_policy`, `footprint_requirements`, money rules — values UI-editable, blank blocks live.

### 2.3 Bot / QML

- CT-33 declaration + plain-Python logic; footprint = only evidence the host injects.
- Strategy family = **key, no authority**.
- Conformance gates **citation and seats**, not tunnel entry.
- Never: size, venue commands, clock, Book module injection.

### 2.4 Execution / QMN

- Order path: seat callback → CT-23 Book door → protection gate (KSA fold, standing intent, UNKNOWN) → command mint → `VenueClientPort`.
- Entry-side-only blocks (L39): never block risk-reducing acts or evidence recording.
- Kill switch = KSA blocking levels; **MIS snapshot + SQS are inputs, never authorities**.

### 2.5 Paper trinity (do not collapse)

| Noun | What | World / role |
|---|---|---|
| **research-paper** | QMB governed replay outside node | `world = replay` |
| **node-paper** | Book-level demo routing + soak | `role = demo`, `world = live` |
| **QMA-paper** | Does not exist | — |

DEC-0275; `docs/components/qmf-risk.md`; ADR-0022.

---

## 3. Dataflow (placement-oriented)

### 3.1 Live / node-paper slice (simplified)

```
venue / CT-15 intake
  → push-to-pull accumulator (first writer; record then fold)
  → QMB run_slice (unforked; six sub-phases)
       update streams → scheduled events → resting fills
       → closed-data indicators/structure
       → mint_intents (QL-7 seat; footprint only — NO MIS)
  → MIS signal snapshot (compute-once; Book door + KSA only)
  → CT-23 Book door (admission, R, SQS/MIS veto slots, windows, bench, ladder)
  → protection / KSA
  → CT-19 command → VenueClientPort → cTrader
  → CT-13 journals + CT-29 exits
```

Cite: `docs/architecture/overview.md` process internals; `trading-node.md` TN-5/TN-6/TN-19; `qmb.md` B-2.

### 3.2 Experiment / research-paper (QMB)

```
as-of registry set (passive hub)
  → compile one resolved run-config (Book/BMS fragments + bot)
  → pure run() over qmf-data rooms (split-governed)
  → CT-23 against fill/slip/cost ports (no venue)
  → CT-32 + CT-13 in world=replay
  → orchestrator: one ledger line (governed lane only)
```

QMB **never** imports `qmf-venue`. Replay bindings are incomparable to live bindings (`world` is a binding component).

### 3.3 Promotion path (human)

Ungoverned research → (optional) governed QMB CT-32 → human promotion card → hub publish (refuse `provenance=sandbox`) → QMN click-gated pull → **separate** activation click → next day-boundary trade start (DEC-0261). QMA may only stage **candidates**; never orders.

### 3.4 Three experiment lanes (door-selected)

Per SCN-0015 / DEC-0270 — lane = **which door**, never a payload flag:

1. **Ungoverned** — `qmb.run()` / `import qml` → values only; no ledger, no CT-32 registry, no ExperimentSpec.
2. **Governed** — QMB orchestrator spawn → one ledger line + one CT-32; research-paper.
3. **Coordinated** — QMA CT-47 places at most one `qmb` CLI/MCP run per env; never `import qmb`; Experiment Ledger refs QMB evidence.

---

## 4. Placement implications for regime research

| Placement question | Current QMX answer |
|---|---|
| Where does a regime label live? | MIS snapshot producer slot (node), not bot footprint, not CT-33 parameter |
| Who may *act* on a regime label? | Book door (entry veto / window / SQS-class block) and KSA escalation — not bot logic |
| Can a bot subscribe to regime? | **No** (closed consumer set) |
| Can regime change size? | **No** — sizing is Book R ladder |
| Can regime switch Books/playbooks? | **No** — rebinding is operator/record |
| Shadow training path? | Candidate labeler → shadow snapshot stream → ungoverned diff; never governed consumer until ratified (TN-19; GAP-0051) |
| Offline vs VPS? | Training OFFLINE (operator machine script); never on decision path / VPS (GAP-0051) |

---

## 5. Deferred rows that touch MIS / experiments

From `docs/gap-report.md` (non-authorizing):

| Gap | Touch |
|---|---|
| **GAP-0051** | MIS train + shadow rollout; `regime_classifier_v1` design story; last node epic |
| **GAP-0050** | KSA matrix *values* (shape closed); blank blocks live |
| **GAP-0048** | QMB fidelity / fill calibration / modeled-spread vs SQS freshness |
| **GAP-0049** | Search-quality / SR* thresholds |
| **GAP-0016/0017** | Causality registration gate / attempt counter (prevention exists in QMB; gate deferred) |
| **GAP-0056** | Node replay fill simulation (none in V1; decision-diff only) |
| **GAP-0063 / GAP-0085** | Structure generation algorithm / mechanism nouns (QML ownership; deferred) |
| **DEC-0089** | MIS not a QMF library (out-of-scope for roster) |

---

## 6. Path index

| Topic | Path |
|---|---|
| Overview / C4 | `docs/architecture/overview.md` |
| Stack / apps | `docs/architecture/stack.md` |
| Depends | `docs/architecture/dependencies.yaml` |
| Risk / Book / SQS | `docs/components/qmf-risk.md` |
| Indicators | `docs/components/qmf-indicators.md` |
| QMB | `docs/components/qmb.md` |
| QML | `docs/components/qml.md` |
| Node / MIS seam | `docs/components/trading-node.md` |
| ADRs | `docs/decisions/ADR-0017-*.md`, `ADR-0018-*.md`, `ADR-0019-*.md`, `ADR-0022-*.md` |
| CT-16/22/23/33/34 | `docs/contracts/ct-16-indicator.yaml`, `ct-22-book-charter.yaml`, `ct-23-risk-evaluation.yaml`, `ct-33-bot-definition.yaml`, `ct-34-confluence.yaml` |
| Lanes scenario | `docs/scenarios/SCN-0015-three-experiment-lanes.md` |
| Gaps | `docs/gap-report.md` |
| Integration MIS | `qmn/src/qmn/mis/` (`signal_snapshot.py`, `catalog.py`, `regime_*.py`, `shadow.py`, `labelers.py`) |

---

## 7. One-line research posture

**Regime/placement work feeds MIS → Book door / KSA as block-or-label evidence.** It does not become bot alpha, size, or execution authority. Profitability claims stay in governed QMB confirmation evidence and human promotion — never inside a classifier score.
