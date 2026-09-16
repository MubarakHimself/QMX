# Donor investigation — QuantAnalyzer (StrategyQuant)

**Sitting:** architecture-QMX-2026-09-14 (planning only).  
**Donor:** QuantAnalyzer (`https://strategyquant.com/quantanalyzer/`).  
**Method:** official product pages + StrategyQuant documentation fetched 2026-09-14 (`web_search` + `web_fetch`). Workroom/research notes used as leads only.  
**QMX product source:** `integration` @ `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` (`git show`). Checkout stays on `main`.  
**Standing bans:** no donor engine adoption; QMA never executes the money path including paper; QMB never imports `qmf-venue`; ordinary Python stays legal.

## Law of this donor (must not blur)

QuantAnalyzer is an **offline analyser of existing backtests and account histories**. Official docs state, in words, that the headline simulations **do not re-backtest**:

- What-If (SQX cross-check, originated in QA): “What If simulation doesn’t backtest the strategy again — it works with existing list of trades from main backtest.” Source: `https://strategyquant.com/doc/strategyquant/what-if-simulations/`
- Money Management: “Quant Analyzer DOESNT RUN A NEW BACKTEST, it ‘only’ analyzes existing trades… go through the strategy orders and apply each MM method to it.” Source: `https://strategyquant.com/doc/quantanalyzer/money-management-simulation/`
- Vendor caveat on What-If: skipped trades “might influence subsequent trades”; “always retest your strategy with these settings incorporated.” Source: `https://strategyquant.com/blog/analyzing-and-improving-your-strategies-using-what-if-scenarios/`

QMX already owns the **honest counterpart** of that retest: QMB `run()` / `run_slice` against Book/BMS rules in `world=replay` (CT-22/23/27/28/29/32), and QMN live/paper Book evaluation. Those are **path-dependent Book/BMS replay**, not QuantAnalyzer.

Two simulation classes that this sitting must keep apart:

| Class | What it consumes | Path dependence | QMX analog today |
|---|---|---|---|
| **A. Trade-list filter / rescale** | Closed orders (PnL, open time, optional SL) | Independent of slice path; overlapping trades and later entries are **not** re-decided | Absent as a named procedure (except trade-shuffle MC) |
| **B. Sequential trade-list control** | Same closed orders, walked in open-time order with running equity | State depends on prior take/skip/resize; still **not** a slice replay | Absent (QA Equity Control) |
| **C. Path-dependent Book/BMS replay** | Market slices + CT-23 intents + Book `money_rules` / leash / doors + BMS constraints | Later fills, sizing, vetoes, and overlapping positions **do** change | **Present:** QMB run loop + QMN `run_slice` |

Do **not** implement Class A/B by silently calling it a Book. Do **not** replace Class C with a QuantAnalyzer-style rescale.

Classification: `reuse | connect | extend | new | undecided`.  
Evidence: `user-intent | documented-design | source-inspected` (official docs = documented-design for the donor; QMX code = source-inspected).

---

## Compact table

| # | Mechanism | Donor class | qmx_home | Status | One-line |
|---|---|---|---|---|---|
| 1 | What-If trade-list filtering | A | QMB | **new** | Filter/drop existing CT-29 trades (days/hours/count/overlap/best-N); mint a labelled non-confirmation result. Not a re-run. |
| 2 | Money-management trade-list rescale | A | QMB | **new** | Apply alternate lot/%-risk multipliers to the existing order list. Not Book `money_rules`. |
| 3 | Path-dependent Book/BMS sizing replay | C (QMX counterpart, not a QA copy) | QMB | **reuse** | Already: one replay binding, CT-23 Book-resolved `requested_r`, CT-22 `money_rules`. This is the retest QA tells you to do. |
| 4 | Equity-control sequential simulation | B | QMB | **new** | Walk closed trades with running equity; skip or resize using equity-curve rules; paper-update skipped trades. Analysis only. |
| 5 | Live/replay Book–BMS on/off (leash, kill, demotion) | C | QMN | **connect** | Existing kill line, bench, doors, BMS protective paper demotion. Not QA’s MA-of-equity snippet. |
| 6 | Portfolio combination search | A | QMB | **new** | Combine existing CT-32/CT-29 streams; brute/genetic **engines** stay out. |
| 7 | Portfolio correlation + sector caps | A | QMB | **new** | Correlation/overlap of existing results; sector metadata as registry/Book attributes, not a second library. |
| 8 | Monte Carlo trade-shuffle | A | QMB | **reuse** | `qmb.robustness.shuffle.run_trade_shuffle` already permutes ClosedTrade PnL on the original close timeline. |
| 9 | Monte Carlo skip / resample / Predict&Verify | A | QMB | **extend** | Shuffle exists; random-skip, resample-with-replacement, and MC projection bands are not in source. |
| 10 | Day/hour/month trade analysis | A (feeds What-If) | QMB | **extend** | V1 measure set is aggregate only; no hour/dow tables on `MEASURE_IDENTITIES`. |

QMA may **request** these via the QMB door (`world=replay` only) and must never compute or execute them. QML does not own analysis filters. UI consumes series/artifacts; it does not become a second analyser.

---

## Source-linked findings

### Donor product (official)

QuantAnalyzer’s own index lists: extensive reports; What-If; Money Management simulator; Monte Carlo; Equity control; Portfolio Master; extendability/snippets (`https://strategyquant.com/quantanalyzer/`). It loads “strategy backtest or real trades.” It is not a live trading node and not a strategy generator.

### 1. What-If scenarios — filter existing trades

**Donor (official):**

- Product: trade only Mon–Thu; max 1 trade/day; only 09:00–15:00; “many others”; snippet-extendable (`https://strategyquant.com/quantanalyzer/what-if-scenarios/`).
- Blog (Mark Fric): uncheck days → “trades opened on Monday and Wednesday **removed from the results**”; max-1-per-day; remove balance transactions; omit 5 best trades; fixed lots; “don’t take trade when another one is opened (remove overlapping trades)” (`https://strategyquant.com/blog/analyzing-and-improving-your-strategies-using-what-if-scenarios/`).
- Snippet API: `filter(SQOrderList originalOrders)` walks orders sorted by open time and `i.remove()` (`https://strategyquant.com/doc/quantanalyzer/create-a-new-what-if-function/`).
- SQX port of the same idea (explicit mechanics, originated in QA): apply to the **list of orders from the standard backtest**; example “Trade only in days” **filters out** opens not on the chosen weekdays; “doesn’t backtest the strategy again” (`https://strategyquant.com/doc/strategyquant/what-if-simulations/`).

**QMX (source-inspected):**

- No what-if / day-hour refilter module under `qmb/` (`git ls-tree integration qmb/src/qmb`). Closest: `qmb.results.interpret.compare_runs` — field-diff of two stored CT-32 artifacts, “No new number” (`git show integration:qmb/src/qmb/results/interpret.py`).
- Trade record for a run **is** the CT-29 stream (`docs/contracts/ct-32-performance-result.yaml` QMB-adoption invariant; `docs/components/qmb.md` B-10).
- Robustness shuffle **reorders** ClosedTrade PnL; it does not drop by weekday/hour (`git show integration:qmb/src/qmb/robustness/shuffle.py`).

**Status:** **new** on **QMB** as a pure analysis procedure over a completed run’s CT-29/ClosedTrade list. Output must **not** be `role=confirmation` and must not gate live money. If the operator wants the filter as **bot logic**, that is a QML Python change + QMB **replay** (Class C), which is the retest the vendor itself requires.

Ordinary Python over the ClosedTrade list is already legal; do not copy QuantEditor/`SQOrderList`.

### 2. Money-management simulator — rescale existing trades

**Donor (official):**

- Product: compare fixed position size vs risk-% of account; snippet MM methods (`https://strategyquant.com/quantanalyzer/money-management-simulator/`).
- Docs: add methods (named **Risk fixed % of account**: Risk in %, Maximum lots, StopLoss in pips); “Run MM simulation” walks **strategy orders**; equity charts vs original; “Move to databank”; **does not run a new backtest**; SL taken from imported report or recognised max/avg loss; three default methods, more in `Snippets -> MoneyManagementTypes`; “Always retest… in your trading platform. Remember that Quant Analyzer does only simulations, not actual backtesting.” (`https://strategyquant.com/doc/quantanalyzer/money-management-simulation/`).

This is **Class A rescale**: same trade times/prices, different size → scaled PnL. It cannot see Book vetoes, BMS free-margin, overlapping capacity, or frozen-R admission.

**QMX (source-inspected):**

- No MM-simulator package in QMB. `results.interpret.refuse_downstream_act` forbids `size` on a CT-32 read (`interpret.py` `DOWNSTREAM_FORBIDDEN_ACTS`).
- Book sizing is **not** “risk % of account per trade” as a post-hoc multiplier. CT-22 `money_rules` is units-only R-ladder: `book_capital`, `loss_floor` (= kill line), `r_unit_price`, `requested_r × r_unit_price` frozen at admission (`docs/contracts/ct-22-book-charter.yaml`; `git show integration:packages/qmf-risk/src/qmf/risk/sizing.py`). Bots may not inbound-size (`git show integration:packages/qmf-risk/src/qmf/risk/door.py`).
- QMB already **replays** those rules (Class C). Varying MM honestly = new Book fragment / `money_rules` values → new `fp1` → new replay run.

**Status:** **new** on **QMB** for the donor’s post-hoc rescale, with an explicit claim-class (robustness/analysis, never edge, never confirmation). The path-dependent comparison of Book `money_rules` is mechanism 3 (**reuse**), not this. QMA must not mint sizing. QMN must not grow an MM laboratory.

### 3. Path-dependent Book/BMS sizing replay — QMX counterpart (not a QA copy)

**Donor:** QA docs tell the user to retest MM/What-If on the trading platform because trade-list simulation is incomplete.

**QMX already is that retest surface in `world=replay`:**

- QMB: one event-slice loop; mint one AD-29 replay binding; consume `qmf-risk` sizing / R-freeze / exits; CT-23 door executes Book-resolved intents, never bot-sized orders (`docs/components/qmb.md` B-2/B-3; ADR-0017).
- `run_slice` / `run` pure; orchestrator writes evidence (`git show integration:qmb/src/qmb/runloop/loop.py` per code-qmb inventory).
- QMN reuses the **same** `run_slice` unforked (`git show integration:qmn/src/qmn/loop/driver.py` per code-qmn inventory).
- QMB never imports `qmf-venue`.

**Status:** **reuse** **QMB**. Product work to *batch* Book `money_rules` variants is **extend** of QMB optimize/sweep (parameter space today is CT-33 bot params, `git show integration:qmb/src/qmb/optimize/space.py` — Book knobs are a different namespace). Do not invent a second tunnel.

### 4. Equity-control simulation — sequential trade-list (Class B)

**Donor (official):**

- Product: “simulate switching a strategy on and off based on the equity curve” (`https://strategyquant.com/quantanalyzer/equity-control/`).
- Blog: 20-period MA of equity; if equity **above** MA take the next trade; if **below**, skip for real but **still take a paper trade and update the equity curve**; chart points are trades, equity = **account balance at trade open**; simultaneous opens grouped; skipped periods marked; alternate snippet doubles size when below MA (`https://strategyquant.com/blog/better-results-with-equity-control/`).
- Admin comment: QA “cannot give you codes that manage the equity control trading”; implement in the EA yourself.

Class B: sequential, original-curve (or paper-updated) state, still on the imported trade list — **not** a slice replay, **not** BMS kill/demotion.

**QMX:** no equity-MA sequential simulator in QMB robustness/results (`git ls-tree integration qmb/src/qmb/robustness` = shuffle, perturbation, significance, walkforward only).

**Status:** **new** on **QMB** as analysis. Must label Class B. Promoting a winning equity-control rule into live trading is a **Book `control_policy` / QML** change plus Class C replay — never “QA said skip.”

### 5. Live/replay Book–BMS on/off — existing QMX controls

**Donor analog (do not copy the MA rule):** switch trading from equity-curve state.

**QMX already has path-dependent controls (Class C):**

- Book `leash_grammar` (bench consecutive losses), `control_policy` (kill line = `loss_floor`), `protection_windows`; BMS `constraints`, KSA posture, control-rank table (`docs/contracts/ct-22-book-charter.yaml`, `docs/contracts/ct-27-bms-definition.yaml`).
- QMN: BMS/Book protective demotion to paper; forbidden per-bot paper lane (`code-qmn.md`; `qmn.paper.lane`).
- Measurement publishes, never acts: CT-32 / interpret skills cannot bench or change mode (`performance.py`, `interpret.py`).

**Status:** **connect** **QMN** (runtime evaluation of already-shaped Book/BMS policy) + QMF templates as substrate. Mapping QA’s MA-of-equity **into** `control_policy` is a **new** Book module and needs an AD; default is **do not**. QMA is deny-listed from kill/mode/sizing acts (`docs/scenarios/SCN-0014-money-path-barrier.md`).

### 6. Portfolio Master — combinations of existing results

**Donor (official):**

- “checks all possible combinations of strategies and chooses the one that gives the best results”; pick 5 of 20 strategies or 5 of 20 markets (`https://strategyquant.com/quantanalyzer/portfolio-master/`).
- Correlation filter; sector caps; automatic metric filters; genetic search may reserve an **out-of-sample** part the evolution must not see (`https://strategyquant.com/doc/quantanalyzer/portfolio-master-new-features-in-4-7/`).
- Sectors via databank Note field; skip combos exceeding max-per-sector (`https://strategyquant.com/doc/quantanalyzer/using-sectors-in-portfolio-master/`).
- Free version: max 4 strategies.

This is **Class A merge** of existing trade lists / equities. It is **not** a multi-bot QMB sweep (sweeps **re-run** the loop per axis).

**Not this donor:** StrategyQuant X **Portfolio Composer** (Build 141) adds **weights** and **free-margin** skip (`https://strategyquant.com/doc/strategyquant/portfolio-composer/`). That is SQX, not QuantAnalyzer. If QMX wants weight+margin, that is Class C (BMS constraints + Book sizing) — do not smuggle Composer in under “Portfolio Master.”

**QMX:**

- Sweeps: Cartesian **re-runs**, “the batch merges nothing” (`git show integration:qmb/src/qmb/sweep/__init__.py`).
- CT-32 `population` can name multiple binding fingerprints (`docs/contracts/ct-32-performance-result.yaml`) — container shape, not a combinator.
- No portfolio-master search under QMB.

**Status:** **new** on **QMB**: merge/rank existing CT-32 + CT-29 streams; OOS split can **reuse** CT-12 / walk-forward split manifests rather than a private genetic holdout. **Do not copy** the vendor brute/genetic engine. QMA may orchestrate a study graph that **calls** QMB; it does not become Portfolio Master.

### 7. Portfolio correlation and overlap

**Donor (official):** correlation by period (day typical) of Profit/Loss, closed/open position or trade counts; optional empty periods; snippet `CorrelationOf`; overlapping-trades table (`https://strategyquant.com/doc/quantanalyzer/portfolio-correlation-explained/`). Also in extensive reports (`https://strategyquant.com/quantanalyzer/extensive-reports/`).

**QMX:** no correlation-of-bots procedure in QMB results. CT-32 forbids spanning account roles in one result; a **portfolio-of-bots** result is a **new population declaration**, not a second DB.

**Status:** **new** on **QMB** (pure function over two or more CT-29 streams / daily PnL series). Sector labels: Book/registry metadata (`strategy-family` / instrument class), not a Note-column clone.

### 8–9. Monte Carlo on existing trades

**Donor (official):**

- Product: many simulations, each a small change; snippet-extendable (`https://strategyquant.com/quantanalyzer/monte-carlo/`).
- Predict & Verify: project MC runs forward; verify live path vs MC envelope (`https://strategyquant.com/doc/quantanalyzer/predict-verify-strategy-performance-using-monte-carlo-simulation/`).
- Custom MC columns consume `double[] orders` (`https://strategyquant.com/doc/quantanalyzer/add-new-monte-carlo-column/`).
- SQX (not QA) documents shuffle / randomly skip / resample on existing trades (`https://strategyquant.com/doc/strategyquant/monte-carlo-trades-manipulation/`). QA marketing does not enumerate those methods on the fetched QA page; treat skip/resample as **likely sibling**, not fully evidenced QA surface.

**QMX (source-inspected):**

- **Reuse:** `run_trade_shuffle` — permute realised PnL onto the original close timeline; path-dependent metrics move; net profit does not; `world=replay`; no synthetic series (`git show integration:qmb/src/qmb/robustness/shuffle.py`).
- **Different rung:** candle-perturbation mints ephemeral synthetic series; persisted synthetic is `world=simulated` and refused as evidence until GAP-0048 (`qmb.robustness.perturbation`).
- No skip-trades MC, no Predict&Verify projection tab.

**Status:** shuffle **reuse** **QMB**; skip/resample/Predict&Verify **extend** **QMB** robustness (still Class A; still not confirmation).

### 10. Day / hour / month trade analysis

**Donor:** results by day and hour; monthly table; stagnation; 20+ charts (`https://strategyquant.com/quantanalyzer/extensive-reports/`). This is how users pick What-If day/hour filters.

**QMX:** V1 `MEASURE_IDENTITIES` = net profit, ratios, drawdown, trade counts, win rates, expectancy, etc. — **no** hour/dow/month slice (`git show integration:qmb/src/qmb/results/measures.py`). Charts are series data, not PNG identity (`qmb.results.charts`).

**Status:** **extend** **QMB** results (same ClosedTrade input). Do not copy vendor “Strategy Quality Number” or HTML report packs.

### Extensibility (not a shipped mechanism)

QA: QuantEditor Java snippets (What-If, MM, Equity, MC, metrics, Scripter macros) (`https://strategyquant.com/quantanalyzer/extendability/`).  
QMX: ordinary Python is legal; governed evidence requires graduation. **Do not copy** QuantEditor, Scripter, or snippet class hierarchies. Custom Class A/B procedures are QMB library functions + optional QMA Skill that **invokes** QMB.

---

## (1) What already exists

- QMB library+CLI: pure `run`/`run_slice`, orchestrator, CT-32 mint, ClosedTrade measure set, interpret/compare (no deltas), TPE optimize over **bot** params, sweeps that **re-run**, walk-forward, trade-shuffle MC, candle-perturbation MC.
- QMF-risk: CT-22 Book (`money_rules`, leash, control_policy), CT-23 door (Book sizes), CT-27 BMS, CT-29 exits, CT-32 container.
- QMN: unforked `run_slice`, Book paper routing, protective demotion, evidence/powers doors. No research laboratory on the node.
- QMA: ExperimentSpec + QMB door (`world=replay`, no `import qmb`), money-path deny-list including paper.
- QML: declaration + plain Python; no analysis filters; bots do not size.

## (2) Missing wiring vs missing function

| Missing wiring (function present) | Missing function (donor-shaped) |
|---|---|
| Robustness / sweep batch+rank not on CLI | What-If trade-list filter (days/hours/count/overlap/best-N) |
| QMA→QMB door transport (recording stub vs live CLI) | MM rescale of existing orders |
| Book `money_rules` already consumed in replay; no product **study** that varies Book knobs | Equity-control sequential walk |
| CT-32 population can cite many bindings | Portfolio combination search over existing results |
| Walk-forward / CT-12 splits (usable as portfolio OOS) | Correlation / overlap / sector-constrained combinator |
| Trade-shuffle MC | MC skip, resample, Predict&Verify |
| Aggregate CT-32 measures | Day/hour/month profitability tables |
| | QA-style databank UX (product/UI, not a second results DB) |

## (3) Recommended architectural ownership

| Concern | Owner | Class |
|---|---|---|
| Class A/B analysis procedures (What-If, MM rescale, equity-control walk, correlation, combinator, extra MC) | **QMB** pure library; CLI later | new / extend |
| Class C replay of Book/BMS (the required retest) | **QMB** | reuse |
| Book/BMS **shapes** (`money_rules`, control_policy, constraints) | **QMF** | reuse |
| Live/paper evaluation, kill, demotion | **QMN** | connect (existing policy) |
| Agent-launched studies | **QMA** via QMB door only | connect |
| Session/day filters as **bot logic** | **QML** ordinary Python + replay | new only if promoted from What-If |
| Workbench / charts | **UI** consuming QMB series | connect |
| Databank as a **second store** | **forbid** | Shared Library = registry + rooms + CT-32 |

Never: QMA execution/paper; QMB `qmf-venue`; a QuantAnalyzer process inside QMX; genetic/MM engines from the vendor.

## (4) Open questions — AD vs Deferred

**Need an AD this sitting (or immediately after):**

1. **Claim class for Class A/B outputs.** New CT-32 evidence_class / run role vs a sibling artifact? Confirmation is illegal; `replicate` is MC-shaped. Recommend a dedicated analysis role that cannot feed AD-32 live bars.
2. **Does a “winning” What-If/MM/equity-control ever write Bot or Book fields?** Default: no. Promotion path = human edits QML/Book → Class C replay → new fp1.
3. **Portfolio combinator vs sweep.** Keep combinator on **existing** results (QA); keep sweep as **re-run**. Do not merge the two.
4. **Equity-control into `control_policy`?** Default no. Live on/off stays leash/kill/BMS demotion unless a later risk sitting ratifies an equity-MA module.
5. **Book-knob studies.** Is varying `money_rules` a QMB sweep axis (extend) or a forbidden mutation of Book identity (new Book version per combo — already the CT-22 law)?

**Can stay Deferred:**

- GAP-0048 simulated world / candle-MC persistence.
- GAP-0049 robustness thresholds / MC-1000 battery (already refused as baked default in shuffle).
- QuantEditor-like snippet IDE (ordinary Python is enough).
- SQX Portfolio Composer weight+margin (not this donor; Class C BMS/Book if ever).
- Vendor metric catalogue (Strategy Quality Number, Z-score, stagnation) — pick later against CT-32 unit-kinds; do not bulk-import.
- Exact QA Monte Carlo method list beyond shuffle (skip/resample evidenced on SQX docs, not on the QA product page).

---

## Official URLs fetched

- `https://strategyquant.com/quantanalyzer/`
- `https://strategyquant.com/quantanalyzer/what-if-scenarios/`
- `https://strategyquant.com/quantanalyzer/money-management-simulator/`
- `https://strategyquant.com/quantanalyzer/portfolio-master/`
- `https://strategyquant.com/quantanalyzer/equity-control/`
- `https://strategyquant.com/quantanalyzer/monte-carlo/`
- `https://strategyquant.com/quantanalyzer/extendability/`
- `https://strategyquant.com/quantanalyzer/extensive-reports/`
- `https://strategyquant.com/doc/quantanalyzer/money-management-simulation/`
- `https://strategyquant.com/doc/quantanalyzer/create-a-new-what-if-function/`
- `https://strategyquant.com/doc/quantanalyzer/portfolio-correlation-explained/`
- `https://strategyquant.com/doc/quantanalyzer/using-sectors-in-portfolio-master/`
- `https://strategyquant.com/doc/quantanalyzer/portfolio-master-new-features-in-4-7/`
- `https://strategyquant.com/doc/quantanalyzer/predict-verify-strategy-performance-using-monte-carlo-simulation/`
- `https://strategyquant.com/blog/analyzing-and-improving-your-strategies-using-what-if-scenarios/`
- `https://strategyquant.com/blog/better-results-with-equity-control/`
- `https://strategyquant.com/doc/strategyquant/what-if-simulations/` (QA-origin mechanics, explicit “no re-backtest”)
- `https://strategyquant.com/doc/strategyquant/portfolio-composer/` (SQX, **out of donor scope**)
- `https://strategyquant.com/doc/strategyquant/monte-carlo-trades-manipulation/` (SQX sibling; used only to flag skip/resample uncertainty)

*No implementation. No vendor UI/engine copy. Planning checkout `main`.*
