# Cut — What-if and money-management (filter/rescale vs path-dependent Book/BMS)

**Sitting:** architecture-QMX-2026-09-14 (planning only; no implementation).  
**Checkout:** `main` `430fb7d2d08997085c28d717b25a1ff5c3c78e62`.  
**Product source:** `integration` @ `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` via `git show` / `git ls-tree` only.  
**Evidence:** `source-inspected` (integration) + `documented-design` (`docs/`) + `user-intent` (research leads). Not `behavior-demonstrated`.  
**Leads only:** `workroom/research/2026-09-14-backend-baseline.md`, `2026-09-14-grok-feature-prompts.md`, donor notes. Spine already drafts AD-5/AD-6; this cut is the evidence, not a silent override.

## Compact table

| Question | Answer | Class | Owner |
|---|---|---|---|
| Is filtering/rescaling a CT-32/CT-29 stream a legal analysis view? | **Yes**, as a **projection**: read-time filter/rescale of a *cited* parent stream. Claim-class `projection`. Never admission evidence, never `role=confirmation`, never a live-money gate. | **new** procedure on existing streams | `COMP-QMB` (library function). UI/agents consume the stamp. |
| When must QMB re-run path-dependent Book/BMS? | Whenever later fills, sizing, vetoes, overlapping capacity, leash/kill, or bot decisions would change: Book `money_rules`, BMS constraints, `starting_capital`, execution ports, bot logic, CT-33 params. | **reuse** tunnel | `COMP-QMB` `run()` / orchestrator + `COMP-QMF-RISK` shapes |
| Who owns the named method so UI and agents cannot confuse the two? | Every analysis artifact stamps exactly one method: `projection` \| `path-dependent`. QMB mints the stamp. QMF-Risk owns Book/BMS/CT-29/CT-32 shapes. QMA may *request* via the CT-47 door and never computes either method. | **connect** (stamp) + **extend** QMB | No new COMP. Simulator stays deferred UI over QMB (DEC-0159). |
| QuantAnalyzer “What-If / MM simulator” (no re-backtest) | Donor Class A. Legal only as **projection**. Vendor itself says skipped trades may change later trades — QMX’s honest counterpart is the path-dependent re-run. | donor shape, not a product | Do not copy QuantEditor/`SQOrderList`. Ordinary Python over the stream is already legal. |
| Book/BMS “money-management simulator” | Book **is** the money-management container (glossary; CT-22 `money_rules`). Varying MM honestly = new CT-22/CT-27 `fp1` + QMB replay. Trade-list lot/% rescale is **not** Book simulation. | **reuse** (replay) / **new** (rescale, labelled) | QMA `money_path_relevant` candidates; humans fill unset money-path fields (CT-47). |
| Named condition presets (stress-spread, etc.) | Already B-3 config fragments (`SOURCE_PRESET`). They change the **resolved run-config** → path-dependent. They are **not** QuantAnalyzer What-If. | **reuse** | `qmb.config.fragments.materialize_condition_preset` |

**Overall verdict: `extend` `COMP-QMB`.** Path-dependent Book/BMS replay already exists. Projection filter/rescale does not. The architecture job is to *name* the two methods and refuse a third noun so two builders cannot ship incompatible What-if surfaces.

---

## Source-linked findings

### 1. Two donor classes that QMX must not collapse

QuantAnalyzer documents, in words, that headline simulations **do not re-backtest** (official: What-If “doesn’t backtest the strategy again — it works with existing list of trades”; MM “DOESNT RUN A NEW BACKTEST”). The vendor caveat is that skipped trades “might influence subsequent trades” and the user should retest. QMX already *is* that retest surface in `world=replay`.

| Class | Consumes | Path dependence | QMX today |
|---|---|---|---|
| **A. Trade-list filter / rescale** | Closed orders (PnL, time, optional SL) | Later entries/fills **not** re-decided | **Absent** as a named procedure. Closest: trade-shuffle MC (reorder, not drop) and `compare_runs` (field-diff, “No new number”). |
| **B. Sequential trade-list control** | Same list, walked with running equity | State depends on prior take/skip/resize; still not a slice replay | **Absent** (QA Equity Control). Sibling; not this cut’s AD. |
| **C. Path-dependent Book/BMS replay** | Market slices + CT-23 intents + Book `money_rules` / leash / doors + BMS constraints + ports | Later fills, sizing, vetoes, overlapping positions **do** change | **Present:** QMB `run`/`run_slice` + QMN unforked `run_slice`. |

Do **not** implement Class A by calling it a Book. Do **not** replace Class C with a QuantAnalyzer rescale.

### 2. Filtering/rescaling a CT-29/CT-32 stream **is** a legal analysis view

**Law already on the streams:**

- The run’s trade record **IS** the CT-29 stream of the replay binding; CT-32 is the canonical result; chart series and trade-event references are declared QMB extensions citing CT-13 (`docs/components/qmb.md:46-47`, `:105`; `docs/contracts/ct-32-performance-result.yaml:31-32`).
- Measurement publishes, never acts — may not size, allocate, promote, demote, bench, or change a mode (`docs/contracts/ct-32-performance-result.yaml:29`; `git show integration:packages/qmf-risk/src/qmf/risk/performance.py` `PublishAct.SIZE`, `FORBIDDEN_MEASURE_ACTS`).
- QMB interpret skills copy stored CT-32 fields only and refuse `size`/`promote`/`bench`/`bind` (`git show integration:qmb/src/qmb/results/interpret.py` `DOWNSTREAM_FORBIDDEN_ACTS`, `compare_runs` “No new number”).
- A replay-world verdict cannot gate live money (`docs/components/qmb.md:77`; B-4). Ledger roles are `confirmation | trial | replicate | aborted` (`git show integration:qmb/src/qmb/ledger/line.py:54-57`); Book-bar read is `role=confirmation` only.
- Procedure-ephemeral perturbation that does not persist a synthetic series stays `world=replay` with claim-class **robustness-only**, never edge, never admission (`docs/components/qmb.md:91`; B-7). Trade-shuffle already permutes ClosedTrade PnL onto the original close timeline (`git show integration:qmb/src/qmb/robustness/shuffle.py`).
- Ordinary Python over returned values is legal (L33 / B-9). A *product* What-if must still stamp a method so UI and agents cannot treat a notebook filter as a Book counterfactual.

**Therefore:** a read-time filter or linear rescale of a **cited** parent CT-29/CT-13 stream, emitting a derived analysis artifact with `method=projection` and `claim-class=projection`, is a legal analysis view. It is **not** a new CT-32 confirmation run. It must not be written back as a mutation of the parent. It must not feed AD-32 live bars.

**Limits that the method name exists to carry:**

- Class A cannot see Book vetoes, BMS free-margin, overlapping capacity, frozen-R admission, or later bot decisions that would have fired if an earlier trade had been skipped or resized.
- QMB’s measure helper `ClosedTrade` is **not** a full CT-29 row. Fields are `realized_pnl`, `fees`, `side`, `closed_at` only (`git show integration:qmb/src/qmb/results/measures.py` class `ClosedTrade`). CT-29 itself freezes `original_risk_distance` / `original_risk_amount`, fill refs, close reason, mechanism/outcome (`docs/contracts/ct-29-exit-record.yaml:36-50`; `git show integration:packages/qmf-risk/src/qmf/risk/exit_record.py` class `ExitRecord`). Weekday/hour-of-**open** filters (the QuantAnalyzer default) need the journal/fill refs, not `ClosedTrade.closed_at` alone.
- Linear PnL rescale (lot multiplier) is Class A. Honest %-of-account / Book `money_rules` is Class C.

Docs still stamp CT-29/CT-32 `wiring_status: defined-unwired` / “no code exists” (`docs/contracts/ct-29-exit-record.yaml:9`, `docs/contracts/ct-32-performance-result.yaml:10`). Integration already has `qmf.risk.exit_record.mint_exit_record`, `qmf.risk.performance.mint_performance_result`, and QMB `mint_replay_exit` (`git show integration:qmb/src/qmb/execution/risk.py`). That is **documentation drift**, not missing function of the *shapes*. Reconcile later; do not pick docs or code silently.

### 3. When QMB **must** re-run path-dependent Book/BMS

Path-dependent evaluation is the existing wind tunnel: one resolved run-config, one `world=replay` binding, CT-23 door, CT-29 exits, CT-32 artifact (`docs/components/qmb.md:17`, `:63-67`; `git show integration:qmb/src/qmb/runloop/loop.py`; `git show integration:qmb/src/qmb/execution/risk.py`).

**Must re-run (method = `path-dependent`) when any of these change, or when the operator wants a counterfactual that would change later path:**

| Change | Why filter/rescale is illegal as a substitute |
|---|---|
| Book `money_rules` (`book_capital`, `loss_floor`=kill line, `r_unit_price`, `seat_r_ceiling`, `requested_r × r_unit_price` frozen at admission) | Units-only R-ladder, not a post-hoc lot multiplier (`docs/contracts/ct-22-book-charter.yaml:29`; `git show integration:packages/qmf-risk/src/qmf/risk/sizing.py`). A changed number changes `fp1` ⇒ new Book identity (`docs/contracts/ct-22-book-charter.yaml:28`). |
| Bot-supplied size / inbound `requested_r` | Refused: “the bot may not size” (`docs/contracts/ct-23-risk-evaluation.yaml:19`; `git show integration:packages/qmf-risk/src/qmf/risk/door.py:913-930`). |
| BMS constraints, capacity, leash, kill-line, protection windows | Later admits/exits/vetoes change. BMS fragment namespaces `accounting` / `constraints` / `kill-line` / `reporting` (`git show integration:qmb/src/qmb/config/fragments.py` `BMS_NAMESPACES`). |
| `starting_capital` | Binding virtual-ledger seed; flag override stamps `seed_overridden` and forces fold `unrated` (`docs/components/qmb.md:67`). |
| Fill / slippage / cost / financing ports | GAP-0048 seams; mixed-fidelity comparison of Book bars is a typed refusal (`docs/components/qmb.md:85-87`). |
| Bot logic, including session/day filters **promoted into the bot** | Later intents change. Promotion path = QML Python + Class C replay, never “QA said skip.” |
| CT-33 parameter search | Optimize space is the Bot schema only (`git show integration:qmb/src/qmb/optimize/space.py`). Book knobs are a different namespace — a new Book version per combo, not a silent TPE axis. |
| Named condition presets (stress-spread, etc.) | Already config fragments that enter the resolved run-config (`git show integration:qmb/src/qmb/config/fragments.py` `SOURCE_PRESET = "named-condition-preset"`; `docs/components/qmb.md:67`). Path-dependent by construction. |

QMN reuses the same `run_slice` unforked for live/paper Book evaluation. It must **not** grow a research MM laboratory. Paper-before-promotion is QMB governed replay **outside** the node (DEC-0261). QMA has no execution tool, paper included (DEC-0341; `docs/contracts/ct-47-qma-experiment-spec.yaml:39`).

### 4. Who owns the named method

| Actor | May | Must never |
|---|---|---|
| **`COMP-QMB`** | Own both procedures as library functions. Stamp `method ∈ {projection, path-dependent}` and `claim-class` on every analysis artifact. Path-dependent goes through the existing compiler/orchestrator (new resolved-config, new replay binding, new CT-32). Projection is a pure function over a cited CT-29/CT-13 parent + predicate/scale, writing no parent mutation. | A second tunnel. A QuantAnalyzer process. Calling a filtered list a Book. `import qmf-venue`. |
| **`COMP-QMF-RISK`** | Own CT-22/23/27/28/29/32 **shapes** (Book is the MM container). Publish-never-act. Bench fold over the real CT-29 stream. | Runtime What-if. Evaluating the sizing ladder as a research UI (node/QMB composition roots do that). |
| **`COMP-QMA-*`** | Request a QMB job through the CT-47 door (`world=replay` only). Emit `money_path_relevant` Book/BMS **candidates** with a field-level diff; unset money-path fields stay unset until a human fills them (`docs/contracts/ct-47-qma-experiment-spec.yaml:34-35`). | `import qmb`. Compute projection or replay. Fill sizing/risk fields. Mint a third method noun. Paper/live execution. |
| **`COMP-QML`** | Session/day/overlap filters as **bot logic** when the operator promotes a projection insight. | Analysis filters. Sizing. |
| **`COMP-QMN`** | Evaluate already-shaped Book/BMS policy on the unforked loop. | Research What-if / MM lab. Per-bot paper lane. |
| **UI / agents** | Select method, display limitations, consume series/artifacts. Thin doors. | Invent a fourth method. Parse HTML reports (`interpret.py`). Treat projection numbers as confirmation. |
| **Simulator** | Deferred product UI that **consumes QMB** (glossary Simulator; DEC-0159, DEC-0088). | A second backtest path or fill model (competes with GAP-0048 ports). |

Corpus-factory-map row “What-if analysis = reuse named condition presets” names Class C config, not Class A trade-list filter. Keep the two nouns apart.

---

## (1) What already exists

- QMB wind tunnel: one resolved run-config, disjoint Book/BMS namespaces, named condition presets as config fragments, pure `run`/`run_slice`, orchestrator ledger (`confirmation|trial|replicate|aborted`), CT-32 mint with CT-13/CT-29 trade-event extension (`docs/components/qmb.md` B-1..B-10; `git show integration:qmb/src/qmb/{runloop/loop.py,config/compiler.py,config/fragments.py,results/ct32.py,execution/risk.py}`).
- QMF-Risk value types on integration: `money_rules` unit-kind shape, CT-23 door (bot may not size), `ExitRecord` / `mint_exit_record`, CT-32 `mint_performance_result`, publish-never-act including `size`.
- Robustness Class A **reorder**: `run_trade_shuffle` over ClosedTrade PnL; claim-class robustness; no weekday/hour drop (`git show integration:qmb/src/qmb/robustness/shuffle.py`).
- Results interpret: explain/compare/flag from stored CT-32; forbids downstream `size` (`git show integration:qmb/src/qmb/results/interpret.py`).
- Optimize/sweep: Cartesian **re-runs** over CT-33 bot params; “the batch merges nothing.” Book knobs are not a search axis.
- QMA: ExperimentSpec + single `qmb` door; `money_path_relevant` + field-level diff; no execution tool (`docs/contracts/ct-47-qma-experiment-spec.yaml`).
- QMN: unforked `run_slice`; Book-level paper; no research laboratory.
- Ordinary Python over ClosedTrade / returned run values (B-9 / L33).

## (2) Missing wiring vs missing function

| Missing wiring (function present) | Missing function |
|---|---|
| Robustness / sweep batch+rank not on CLI (`code-qmb.md`); UI not consuming chart-series | Named **projection** procedure: filter/drop/rescale a cited CT-29/CT-13 stream (days/hours/count/overlap/best-N/lot multiplier) with `method=projection` |
| Method + claim-class stamps not yet a field on CT-32 / ledger (roles exist; `projection` does not) | Hour/dow/month profitability tables (`MEASURE_IDENTITIES` is aggregate-only — `git show integration:qmb/src/qmb/results/measures.py`) |
| QMA→QMB door transport is recording stub vs live CLI (connect, not this cut’s function) | Book-knob studies as a product sweep (must mint new CT-22/CT-27 versions; not a CT-33 axis) |
| Docs `defined-unwired` vs integration value types (documentation-factory reconcile) | Equity-control sequential walk (Class B) — sibling **new**, not Book `control_policy` by default |
| `ClosedTrade` reduction vs full CT-29 for open-time predicates — projection must cite journal/fill refs | A twin MM simulator duplicating Book (**forbid**; DEC-0069 paper twins stay dead) |

Class existence / tests ≠ end-to-end proof. Absence of a What-if module under `git ls-tree integration qmb/src/qmb` **is** source-inspected negative evidence for the named projection procedure.

## (3) Recommended architectural ownership

**Extend `COMP-QMB`.** Do not mint COMP-QA / COMP-WHATIF / a sixth application (sitting AD-1).

- **Projection What-if / MM rescale:** new QMB pure library function(s) over a cited parent CT-29/CT-13 stream. Output is an analysis artifact, not a confirmation CT-32. CLI later; UI consumes.
- **Path-dependent What-if / MM / Book policy:** reuse QMB compiler + `run` + orchestrator. New Book/BMS version = new fingerprinted CT-22/CT-27 candidate in registry `dev` zone, then a **governed** replay citing that fingerprint.
- **Shapes:** reuse `COMP-QMF-RISK`. QMB consumes, never redefines AD-29..41.
- **Agents:** connect `COMP-QMA-DAEMON` through CT-47; QMA never computes the analysis.
- **Live evaluation:** connect `COMP-QMN` to existing policy; no MM lab on the node.
- **Promoted session filters:** `COMP-QML` logic + path-dependent replay.
- **Workbench:** deferred Simulator UI over QMB (DEC-0159). Operations `analysis.project` and `analysis.rerun` (capability companion) are the two named doors, not a third.

Companion sitting ADs already drafted: AD-5 (two named methods), AD-6 (Book/BMS variants are candidates plus replay), AD-15 (claim-class including `projection`). This cut is the evidence that those ADs are load-bearing.

## (4) Open questions — AD vs Deferred

**Need an AD this sitting (two builders would otherwise diverge):**

1. **Two named analysis methods (AD-5).** Every analysis artifact stamps exactly one of `{projection, path-dependent}`. Projection = read-time filter/rescale of a cited CT-29/CT-32 (CT-13) stream, claim-class `projection`, never admission evidence. Path-dependent = new resolved run-config through the QMB tunnel (Book/BMS fragments, ports, `starting_capital`). QuantAnalyzer hours/days/max-trades maps to **projection** unless the operator requests a re-run. UI and agents select a stamp; they do not invent a third method. **This is the recommended AD.**

**Companion, already required for MM (not a substitute for AD-5):**

2. **Book/BMS variants (AD-6).** A proposed Book/BMS version is a new fingerprinted CT-22/CT-27 candidate. Path-dependent evaluation is a QMB governed replay under that fingerprint. QMA emits `money_path_relevant` candidates only with a field-level diff; unset money-path fields stay unset until a human fills them. Trade-list rescaling must not pose as Book simulation.

**Can stay Deferred (no AD required to keep builders compatible):**

- Equity-control MA-of-equity **into** Book `control_policy` — default **no**. Live on/off stays leash/kill/BMS demotion unless a later risk sitting ratifies an equity-curve module. Class B as a labelled QMB analysis walk can trail.
- Hour/dow/month table catalogue and extra MC skip/resample/Predict&Verify (extend robustness later).
- QuantEditor snippet IDE (ordinary Python is enough).
- GAP-0048 fidelity taxonomy / `world=simulated` unlock; GAP-0049 thresholds.
- Simulator layout / databank UX (product UI; no second results store — sitting AD-14).
- Exact first-ship predicate set (Mon–Thu, max-1/day, …) — product content after the method stamp exists.

---

*No implementation. No branch switch. No vendor engine copy. Planning checkout `main`.*
