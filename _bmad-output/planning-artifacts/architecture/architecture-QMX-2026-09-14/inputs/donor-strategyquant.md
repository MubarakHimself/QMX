# Donor investigation — StrategyQuant (SQ X)

**Donor:** StrategyQuant X (strategyquant.com). Analysis/strategy-development software; official footer: not a broker, does not execute trades.
**Date:** 2026-09-14
**Scope:** official documentation only as primary evidence. Workroom/research notes were not used as authority.
**Product snapshot (QMX, this sitting):** QMF toolbox; QMB library+CLI on `integration` `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` (run loop, orchestrator, TPE optimize, walk-forward, sweeps, data, CT-32); QML declaration+plain-Python logic (same commit); QMA daemon/missions/tools/ExperimentSpec **documented, no `qma/` package on integration**; Trading Node paper|live.
**Standing bans:** no donor engine adoption; QMA never executes money path including paper; QMB never imports qmf-venue; ordinary Python stays legal.

Evidence levels used below: `user-intent` (operator brief), `documented-design` (QMX docs / SQ official docs), `source-inspected` (`git show integration:…`).

## Compact table

| Mechanism | What (donor, not vendor UI) | qmx_home | Status | QMX already | Gap |
|---|---|---|---|---|---|
| Fixed vs variable template slots | Template pins some slots (order type, SL required, time window, a named condition) and leaves others as RandomCondition / RandomValue / RandomAction. Inside a slot, a block may be **fixed-period** or **random-period**. | QML | extend | Producer templates: complete CT-16/CT-17 minus only space-bound params; `fixed_parameters` vs `space_bound` (`qml/src/qml/footprint/template.py`). CT-34 legs declare producer+role, not predicates. | No RandomCondition-style **structure** slot on the declaration. Condition WHEN lives in Python (`FORBIDDEN_CONDITION_FIELDS`). |
| Structure generation vs declared-parameter variation | Builder invents **which indicators, comparisons, AND/OR arity** fill a slot. Optimizer later varies **declared** numbers (periods, SL/PT) on a **fixed** strategy. These are two different searches. | QML | extend | Parameter space is one CT-33 schema; QMB TPE searches **only** that schema. Logic identity is a source-manifest; changing logic mints a new Bot. | No generator of condition trees. V1 explicitly defers a predicate grammar. |
| Random generation of condition structure | Random pick of building blocks into entry/exit rules, with type-validity constraints (price not compared to time). Foundation of SQ Builder. | QMA | new | Agent-codegen of bots is already reserved as agentic territory compiling to CT-33 + Python (`docs/components/qml.md:62`). StrategyHandle may mint **dev-zone candidates** (CT-47). | No candidate-bot generator. No QMA package on integration. |
| Genetic evolution of structure | Initial random population, then crossover/mutation of **blocks** across generations. SQ itself warns later generations can violate the template. | QMA | undecided | QMB TPE is **parameter** search, not genetic programming of rules. | Adopt vs refuse genetic-of-structure is an AD. Do not treat TPE as this mechanism. |
| Building-block pools / random groups | Global building-block set, or per-placeholder Random Groups (Conditions / Values / Actions) that can pin or randomize parameters. | QMF | extend | `qmf-indicators` catalog + CT-16 identity is the governed producer pool. QML footprint binds a subset. | No per-slot allow-list of formulas/comparisons for a **structure** generator. Catalog is not a random-block DSL. |
| Databanks + ranking + filtering | Top-N store of strategies+results; fitness ranking; automatic/custom filters (IS/OOS/RT/P); optional dismiss-similar on stats fingerprint (trades, net profit, DD ±5%). | QMB | extend | Ledger lines + CT-32; `qmb.sweep.rank.rank_sweep` is a **read-time** fold (no stored pass/fail, no composite score). Constraint filters are metric-operator-value. | No multi-stage source/target “databank” collections. No similar-strategy dismiss. Ranking publishes, never dismisses. |
| Custom Projects as repeatable procedures | Ordered tasks (Build, Retest, Filter/copy/move, Optimize, Custom analysis) over named databanks, with **Go To** loops until a final set is full. | QMA | connect | QMA: Mission + Graph Template + Loop + Routine + ExperimentSpec (CT-47). QMB: versioned ladder functions (backtest, optimize, MC, significance, walk-forward). | CT-47 `defined-unwired`; no `qma/` tree on integration. Missing: graph templates that **call** QMB procedures as tasks. |
| Declared-parameter optimization | Given a **fixed** strategy, iterate Start/Stop/Step (or genetic/brute) over recommended params (periods, multipliers, SL/PT). Distinct from Builder. | QMB | reuse | `qmb.optimize` TPE-class sampler over CT-33 space; generation-stepped; trials `role=trial`; anti-overfit sensitivity shipped. | Sequential/stable-region optimizer is **not** present (optional extend, AD). |
| Robustness funnel (cross-checks) | After generation, optional increasingly-expensive tests: higher precision, MC trade-shuffle, additional markets, MC retest (param/data noise), IS/OOS ratios. Failures drop before databank. | QMB | extend | B-14: trade-shuffle, candle-perturbation, significance, walk-forward. Claim class robustness-only, never edge. | No automatic dismiss funnel. Multi-market retest is a sweep axis, not a cross-check gate. Thresholds GAP-0048/0049. |
| Walk-forward as robustness of reoptimization | Simple opt = best past params (curve-fit risk). WF = reoptimize on rolling IS, trade OOS; answers “does periodic reopt help, and is the strategy robust?” WF Matrix searches reopt period. | QMB | extend | `qmb.robustness.walkforward`: sequence of CT-12 split-manifest runs, not one merged run. IS `role=trial`. | No WF-as-reoptimization-of-parameters inside each window (current WF is split-sequence of **declared** assignments). No WF Matrix. Thresholds deferred. |

Status vocabulary: `reuse` = use as-is · `connect` = wire existing owners · `extend` = existing owner needs more function · `new` = function absent · `undecided` = needs an AD.

---

## Official donor mechanisms (fetched)

### 1. How SQ works — random first, genetic second

Source: https://strategyquant.com/doc/strategyquant/how-does-strategyquant-work/ (fetched 2026-09-14)

- **Random generation is the foundation.** A strategy is constructed from price patterns, indicators, order types, logical/equality operators. The builder “randomly picks different building blocks from the available pool and combines them to create entry rule, order type and exit rule.” Validity constraints exist (e.g. price is not compared to time).
- Each generated strategy is **backtested on history**; profitable ones are kept. Throughput claim is thousands of strategies per hour.
- **Genetic evolution** starts from a random (or loaded) initial population and evolves successive generations by selecting fittest individuals. This is **structure search**, not a parameter grid.
- Example generated pseudo-code mixes **invented conditions** (`Stoch(40,1,3) < 50`) with **invented order geometry** (limit offset via Ichimoku+ATR, expiry bars, pip/ATR stops). That whole tree is the generated object.

QMX mapping: this is **not** QMB TPE. TPE varies numbers inside a **declared** CT-33 space (`git show 1b451a8:qmb/src/qmb/optimize/sampler.py` header: “parameter-optimization Study”). Random combination of indicators into new Python/logic is **absent**.

### 2. Strategy templates — fixed slots vs random placeholders

Source: https://strategyquant.com/doc/strategyquant/strategy-templates/ (start URL; fetched 2026-09-14)
Also: https://strategyquant.com/blog/introduction-strategyquant-templating-system-part/ (official blog, linked from the doc)

- A template is a strategy with **Random placeholders** in named parts. SQ fills those placeholders; the rest of the architecture stays operator-authored.
- `RandomCondition(RandomConditionLong)` — generate one or more conditions at this slot. Identity is the placeholder name so it can be reused.
- `NegatedCondition(RandomConditionLong)` — put the **negation** of that named generated condition in another slot (symmetrical long/short).
- After fill: Long `CCI(14)[1] > 0 and RSI(20)[1] > 50` vs Short with reversed comparators. (Comment thread notes this is not always De Morgan-correct; treat as donor UI semantics, not a QMX contract.)
- Conditions are drawn from **Building blocks** plus `# of Conditions`, Period, Shift ranges (What to build).
- Blog Part I states the three steps: (1) building blocks, (2) generate conditions from blocks, (3) place generated conditions into template placeholders. The **template defines where** conditions go; generation defines **what** they are.

This is the donor form of **fixed vs variable slots**: the skeleton is fixed; named holes are variable **structure**, not just numbers.

### 3. Random groups — per-slot pools; fixed vs random **parameters** inside a block

Source: https://strategyquant.com/doc/strategyquant/random-groups/ (fetched 2026-09-14)

- Global building-block selection applies to every RandomCondition unless a **Random group** is attached to that placeholder.
- Group types: **Conditions** (RandomCondition), **Values** (RandomValue — e.g. stop/limit price), **Actions** (RandomAction — order types).
- A group’s contents **take precedence** over Builder → Building blocks. Blocks in the group need not be globally selected.
- **Fixed vs random parameters inside a chosen block:** example group `CCI > 0` with period **fixed 18** always emits `CCI(18) > 0`; `RSI is rising` with **random period** emits `RSI(20) is rising`, `RSI(50) is rising`, etc.
- Genetic limitation (official): “strict control over block usage cannot be guaranteed beyond the initial population.” Crossover/mutation invent combinations not in the template. Recommendation: use **Random Generation** when the template must be honored for every candidate.

This is the cleanest official statement of the distinction this sitting must keep:

- **Structure slot:** which block (CCI vs RSI vs Aroon cross).
- **Declared parameter:** period 18 vs period sampled in range.

QMX already has the **second** (producer `fixed_parameters` vs `space_bound` in `qml/src/qml/footprint/template.py`: “a parameter is either fixed or space-bound, never both”). QMX does **not** have the **first**.

### 4. What to build — generation knobs, not optimizer knobs

Source: https://strategyquant.com/doc/strategyquant/what-to-build/ (start URL; fetched 2026-09-14)

- Strategy types: simple; multi-TF/multi-symbol extra charts; **strategy from template**; **improve existing strategy** (choose parts: Long entry, Short exit, order type).
- Trading direction: long / short / both; **symmetrical** vs **independent** long/short rules.
- **Build mode:** Genetic evolution **or** Random generation (genetic reveals Genetic options).
- `# of Conditions` min/max — this is **arity of the generated predicate**, not a bot parameter. One condition vs three AND/OR-connected comparisons.
- Shift (lookback) min/max; indicator period min/max — ranges used **when generating** conditions; “the exact number of conditions, shift and period will be determined randomly when every strategy or condition is generated.”
- Mandatory SL/PT, pip ranges, RR ratio — generation constraints on exit geometry.

QMX analog for “improve existing”: CT-33 `branches-from` version graph (`docs/components/qml.md:67`) — a **new Bot version**, not in-place mutation of one rule. Analog for extra charts: QMB stream-set declaration (B-12). Analog for period ranges: CT-33 parameter bounds consumed by QMB optimize. Analog for **condition arity** as a generation range: **none**.

### 5. Genetic options — population search over **strategies**, not parameters

Source: https://strategyquant.com/doc/strategyquant/genetic-options/ (fetched 2026-09-14)

- Max generations, population size, crossover and mutation probability.
- Islands + migration (diversity vs local minima).
- Initial population: random, or load existing strategies from an **Initial population databank** (not filtered by the initial-population filter).
- Decimation: generate N× more passing strategies, keep the best, as a higher-quality start (time cost).
- Evolution management: restart when finished; restart if fitness stagnates.
- “Fresh blood”: replace duplicate or weakest strategies with newly random ones.

Crossover (admin comment on that page): exchange **blocks between parent strategies**. Mutation: likelihood of changing a strategy’s **rule (block)**. This is genetic **programming of structure**. QMB’s “generation-stepped sampler” (`propose_generation`) is a different word: it is TPE batches over **declared numbers**.

Status **undecided** for QMX: SQ’s own Random-groups page says genetic search **breaks template control**. QMX templates (CT-33/CT-34 + Python) would suffer the same if crossover spliced logic. An AD must choose random-only structure search, refuse structure search, or accept later-generation template drift.

### 6. Databanks, ranking, filters, dismiss-similar

Sources (fetched 2026-09-14):
- https://strategyquant.com/doc/strategyquant/databank/
- https://strategyquant.com/doc/strategyquant/ranking-options/
- https://strategyquant.com/doc/strategyquant/builder-dismiss-similar-strategies-in-databank/

- Databank = storage of generated/tested strategies **with results**. Multiple databanks per project; Builder / Retester / Optimizer each have independent banks. Capacity is **top N** (100 / 1000), not unlimited.
- Ranking: every new strategy is backtested; **Fitness** in 0..1 from chosen criteria (or weighted combo). Databank keeps the best by that sort. Optional stop-when-full.
- Automatic filters: 0 trades, no profit, no filled orders.
- Custom filters: dismiss if a rule matches. Separate IS / OOS / RT (robustness tests) / P (portfolio) values; money / percent / pips; long / short / both.
- Actions: load/save `.sqx`, export CSV/XLS, retest (copy to Retester with config), edit parameters/rules, merge portfolio.
- Dismiss similar: **does not compare rules**. Fingerprint = Number of trades, Net profit, Drawdown (money, full sample). Match if **all three** within ±5%. Keep the higher fitness. Recommended on unless the template has few variations and the operator wants every one.

QMX:

- Result store already exists: WriterId-scoped ledger + one CT-32 per run (`docs/components/qmb.md:73-79`, `qmb/src/qmb/ledger/`). **No stored pass/fail** (DEC-0162) — SQ Fitness as a stored 0..1 composite is **incompatible** (QMB bans composite scores; `FORBIDDEN_COMPOSITE_EXPRESSIONS` in `qmb/src/qmb/sweep/rank.py`).
- Ranking already exists as **read-time** `rank_sweep` (`qmb/src/qmb/sweep/rank.py`): orders one sweep by a roster `measure_identity`, applies caller-supplied constraints, reports incomplete combos separately, **publishes and never acts**.
- Missing: named staging collections (Build Results → Retest → Final) as **first-class** objects; automatic **dismiss** as a write; similar-strategy stats fingerprint. Those are **extend QMB** (ledger views + sweep admit), not a new databank service.

### 7. Custom Projects — repeatable procedures

Sources (fetched 2026-09-14):
- https://strategyquant.com/doc/strategyquant/introduction-to-custom-projects/ (start URL)
- https://strategyquant.com/doc/strategyquant/custom-projects-main-concepts/
- https://strategyquant.com/doc/strategyquant/filtering/
- https://strategyquant.com/doc/strategyquant/optimization/ (Optimize strategies **task**)

- Custom project = **workflow**: series of tasks in operator-specified order. Example: build 1000 → retest market A → retest remaining on market B → WF Matrix on the rest → store survivors in Final databank; or **restart until Final is full**.
- Tasks are separate actions (Build, Retest, Filter, Optimize, Custom analysis, Automatic retest, Go To, …). New task types are added over builds.
- Multiple named databanks; a task has **source** and **target** banks.
- **Go To Task** + condition (e.g. Final count < 100) loops back to Build. That is the repeatable procedure.
- Filter task: delete / copy / move between banks, optionally only if conditions match.
- Optimize task: mass simple or Walk-Forward optimization **as a workflow step**, then filter.

QMX analog is **not** a new “Custom Project service”. It is QMA’s already-ratified:

- Mission (executable organizational contract) + Graph Template (versioned topology) + Loop node (`stopping_condition`, budget, escalation) + Routine (scheduled Goal + graph_template id) — `docs/components/qma-daemon.md:108-167`.
- ExperimentSpec + single `qmb` door — `docs/contracts/ct-47-qma-experiment-spec.yaml` (`wiring_status: defined-unwired`; `consumers: []`).
- QMB already owns the **task implementations** as library functions (run, optimize, robustness rungs, sweeps).

Status **connect**: QMA sequences, QMB executes, QML artifacts are the candidates. Do not invent a third workflow engine. Reconcile: CT-47 docs say no code; `git ls-tree 1b451a8` has **no `qma/` package** — defined-unwired is true on integration, not a stale-doc lie.

### 8. Optimization vs robustness (must stay two things)

**Optimization** sources (fetched 2026-09-14):
- https://strategyquant.com/doc/strategyquant/simple-optimization/
- https://strategyquant.com/doc/strategyquant/recommended-optimization-parameters/
- https://strategyquant.com/doc/strategyquant/sequential-optimization/

Simple optimization: **you already have a system**. Vary its **parameters** (indicator periods, constants) Start/Stop/Step (or automatic % distribution). Store all combinations or only best. Result: values that worked **on this history**. Official warning: this is curve fitting; more parameters ⇒ more danger. Two postures: (a) refuse to optimize, demand robustness at original values; (b) accept periodic reoptimization if WF shows it helps.

Recommended parameters (default, and the **only** choice in cross-check optimizations): indicator periods, entry multiplier, SL/PT pips/multipliers. Ignore the rest of every block’s knobs — optimizing everything “highly increase[s] risk of curve fitting.” Lower number of optimizable parameters ⇒ more robust.

Sequential optimization (also a cross-check): optimize **one parameter at a time**, choosing the **middle of a stable area** (not the peak fitness). If no stable area, keep original. Result depends on original values. Used as a **robustness test** of parameter sensitivity, not as Builder.

**Robustness** sources (fetched 2026-09-14):
- https://strategyquant.com/doc/strategyquant/cross-checks-automated-strategy-robustness-tests/
- https://strategyquant.com/doc/strategyquant/types-of-robustness-tests-in-sqx/
- https://strategyquant.com/doc/strategyquant/walk-forward-optimization/ (start-adjacent; fetched)

Robustness = cope with changing conditions: unknown data; missed trades; small input/data/spread/slippage changes. Basic test = OOS. Cross-checks are a **funnel**: generate cheap → filter → more expensive tests only on survivors. Groups Basic / Standard / Extensive. Example funnel: generate + global filters → retest higher precision → MC trade manipulation (shuffle/skip; **no new backtest**) → additional markets → optional MC retest (new backtests with param/data/spread noise). Official time warning: 0.2 s generate vs 10–200 s with cross-checks.

Walk-forward: **not** simple optimization. Split history into optimization+run periods; reoptimize on IS; trade OOS with those params; repeat. Tells you (1) whether **reoptimization helps** vs the original non-optimized strategy, (2) whether the strategy can cope with change **via reopt**. If WF is worse than original, curve-fit signal. WF Matrix (linked from that page) searches the reoptimization period. Robustness **score** is a configurable pass count of score components — a stored composite SQ uses; QMX must **not** copy that as a frozen bar (DEC-0162).

QMX already draws this line:

- Optimize = B-8 declared space + TPE (`qmb/src/qmb/optimize/`).
- Robustness = B-14 library rungs, claim class robustness-only (`qmb/src/qmb/robustness/__init__.py`: “Every procedure claims robustness or infra-stress, never edge”).
- Walk-forward = ordered CT-12 windows, not one number (`qmb/src/qmb/robustness/walkforward.py`).

Do not collapse Builder (structure), Optimizer (declared params), and Cross-checks (robustness) into one “search” in QMX architecture.

---

## QMX owners (source-inspected, integration `1b451a8`)

| Owner | What exists on integration | Relevance |
|---|---|---|
| **QMF** | `packages/qmf-indicators` catalog, CT-16 configured-indicator identity | Building-block **pool** (formulas), not a random-condition DSL |
| **QML** | `qml/src/qml/declaration/`, `footprint/template.py`, `declaration/confluence.py` (`FORBIDDEN_CONDITION_FIELDS`), `declaration/parameters.py` | Template + declared space + producer fixed vs space-bound; **no** predicate generator |
| **QMB** | `qmb/src/qmb/optimize/`, `robustness/`, `sweep/rank.py`, `ledger/`, `orchestrator/` | Parameter search, robustness rungs, ranking fold, run evidence |
| **QMA** | **no package** on this commit; CT-47/CT-49/graph templates are docs-only | Intended sequencer / candidate mint via StrategyHandle; not wired |
| **QMN** | `qmn/src/qmn/paper/`, `venue/`, seats | Paper\|live only. Not a research generator. QMA must not drive it. |
| **UI** | out of this sitting | Must not copy AlgoWizard / databank grid / 3D WF charts |

QML V1 law that blocks silent copy of SQ condition trees (`docs/components/qml.md:80` and `qml/src/qml/declaration/confluence.py:8-11`):

> Condition semantics live in logic in V1: the declaration carries WHAT is consumed and WHICH role each plays; WHEN a leg is satisfied is the Python logic’s job. A fully declarative predicate grammar is Deferred.

Agent-codegen is allowed **as compilation into those two artifacts** (`docs/components/qml.md:62`), which is why random/genetic **structure** search, if adopted, homes on **QMA** and writes QML bots — it does not become a QMB “engine” and does not revive `.qml` DSL in V1.

---

## Findings by mechanism

### Fixed vs variable template slots — extend QML

SQ: template skeleton + named RandomCondition/RandomValue/RandomAction holes; Random groups can freeze a block’s period or leave it random.

QMX already:

- CT-33 footprint producer **template** = complete CT-16/CT-17 minus space-bound values (`git show 1b451a8:qml/src/qml/footprint/template.py` lines 1–6, `ProducerTemplate.fixed_parameters` / `space_bound`).
- Resolution is total and single-valued (`resolve_template`).
- Confluence legs: role + producer binding, not a condition AST.

Missing function (not missing wiring): a declaration-level **structure slot** (“this entry filter is a hole to be filled by a generated predicate”) while keeping order-type / family / stream-set / Book exits **fixed**. That is an **extend** of QML declaration (and only then a QMA filler). Do not put structure holes in QMB run-config.

### Structure generation vs declared-parameter variation — extend QML (law already half-there)

This is the sitting’s required distinction.

| Axis | SQ | QMX now |
|---|---|---|
| **Structure** | Builder fills RandomCondition with indicator+comparator+AND/OR arity | Python logic + CT-34 roles. No generator. Changing logic ⇒ new Bot `fp1` |
| **Declared parameters** | Optimizer Start/Stop/Step on recommended knobs | CT-33 parameter_space + QMB TPE. Canonical assignment vs run-spec override (`docs/components/qml.md:67`, `qmb/src/qmb/optimize/space.py`) |

QMB **must not** grow a second sampler that invents indicators. QML **must not** grow a second parameter space for QMB. If structure search is wanted, it mints **new Bot versions / ungoverned Python candidates**, each then optionally optimized on **its own** declared space.

Status **extend**: the split is already law; the structure-generation half is absent.

### Random structure generation — new QMA

SQ: random pick from pool, validity constraints, backtest, keep.

QMX: QMA StrategyHandle may create content-addressed **dev-zone** candidates only; QMA never runs paper/live (CT-47 invariants; `docs/components/qma-daemon.md:19-25`). Evaluation is one `qmb` job per environment.

Missing function: a generator that emits candidate logic+declaration. Missing wiring: CT-47 door. Ordinary Python stays legal for ungoverned research (`docs/components/qml.md:18`); graduation is conformance + lineage.

Do **not** home this on QMB (QMB runs a Bot; it does not author one). Do **not** home it on QMN.

### Genetic structure evolution — undecided QMA

SQ genetic is crossover/mutation of **blocks**. SQ documents that this **cannot** keep Random-group/template constraints after generation 0.

QMX TPE is not this mechanism. Copying SQ islands/crossover would be donor-engine-shaped. Decision needs an AD: refuse; random-only; or genetic with an explicit “template may drift” label (incompatible with QML conformance if the declaration no longer matches the logic). Until that AD, status **undecided**.

### Building-block pools — extend QMF

SQ: 250+ blocks; custom Java blocks; Random groups as allow-lists.

QMX: CT-16 catalog is the governed pool (`docs/components/qmf-indicators.md:16-48`); custom indicators graduate as CT-16 extensions; plain Python is the escape hatch (DEC-0133). Extend = optional **allow-list of formula_ids / comparison shapes** for a future generator, authored in QML footprint/family, **resolved against QMF catalog**. QMF does not run search.

### Databanks + filtering — extend QMB

Reuse the ledger and `rank_sweep`. Extend with (if wanted): sweep-to-sweep staging (source/target sweep ids as Custom-Project banks), constraint filters as **admit** (already close: `ConstraintFilter` in rank.py — today they exclude from a **view**, they do not delete), optional similar-run clustering. Similar-strategy ±5% on trades/NP/DD is a **possible** read-time fold; it is **not** identity (QMX identity is `fp1` of config+logic). Do not store Fitness 0..1. Do not copy `.sqx`.

### Custom Projects — connect QMA → QMB

Existing function, missing wiring. Graph Template node kinds already include `task`, `deterministic_script`, `loop`, `artifact_dependency` (`docs/components/qma-daemon.md:135`). Map SQ tasks:

| SQ task | QMX |
|---|---|
| Build strategies | QMA candidate mint (if structure search adopted) or operator-authored bots + QMB run |
| Retest | QMB run with another run-config / stream set |
| Filter / copy / move | QMB rank/admit view over ledger; QMA artifact refs |
| Optimize | QMB optimize Study |
| Walk-forward / cross-check | QMB robustness rungs |
| Go To until Final full | QMA Loop `stopping_condition` + Routine |
| Databanks | ledger namespaces + Experiment Ledger (CT-47), not a new store |

QMA places **one** qmb job per environment; QMB owns intra-node parallelism (CT-47).

### Declared-parameter optimization — reuse QMB

Shipped on integration: space, sampler, resume, sensitivity, splits (`qmb/src/qmb/optimize/*`, tests `test_optimize_*`). Recommended-parameters discipline maps to **declaring a small CT-33 space** (QML authoring), not to a QMB default that silently drops knobs. Sequential/stable-area search is an optional later **extend** of QMB robustness/sensitivity, not Builder.

### Robustness funnel — extend QMB

Rungs exist; **automatic drop funnel** and **multi-market-as-gate** do not. Funnel orchestration is Custom Project / QMA Loop (connect), the tests themselves stay QMB (extend). Monte Carlo that **persists** synthetic series is already refused as `world=simulated` (`docs/components/qmb.md:91,121`). Do not copy SQ “Robustness score threshold” as a stored composite.

### Walk-forward as robustness of reoptimization — extend QMB

Present: rolling split-sequence, IS trial role, OOS fold `not-yet-ruled`, no merged run (`qmb/src/qmb/robustness/walkforward.py`). Absent: **re-running B-8 optimize inside each IS window** and applying the chosen assignment to that window’s OOS — that is the donor WF meaning. WF Matrix (search of reopt period) is further deferred. Thresholds: GAP-0048/0049, stay Deferred unless an AD mints values.

---

## 1. What already exists

- QML: Bot declaration, confluence roles, producer templates with **fixed vs space-bound parameters**, one parameter-space schema, Python logic as the condition language, conformance gate. Structure search is **out of V1 declaration**.
- QMB: run loop, orchestrator, CT-32, ledger roles, TPE optimize, sweep rank/admit, MC shuffle/perturbation, significance, walk-forward **split sequence**, data commands. Parameter search and robustness procedures are real files on integration, not docs-only.
- QMF: indicator/structure producers as the block pool.
- QMA: ontology, missions, graph templates, loops, routines, ExperimentSpec **as ratified docs**. No integration package.
- QMN: paper|live; not a donor-Builder analog.

## 2. Missing wiring vs missing function

| Missing wiring (owners exist) | Missing function |
|---|---|
| CT-47 QMA → one `qmb` door per environment | RandomCondition-style **structure** slots on QML declaration |
| QMA Graph Template / Loop calling QMB ladder rungs (Custom Project) | Generator that emits condition **structure** (random) |
| QMB sweep rank/admit used as funnel stages (source/target) | Genetic-of-structure (and whether it is legal) |
| Experiment Ledger as the scientist notebook over QMB ledger lines | WF **reoptimization inside** each IS window |
| | Similar-strategy dismiss fold |
| | Sequential/stable-area optimizer |
| | Multi-market robustness **gate** (vs permutation sweep) |
| | Predicate grammar (explicitly Deferred in QML) |

## 3. Recommended architectural ownership

- **QML** owns templates and the structure-vs-parameter **law**. Any new structure slot is declaration surface, compiled still to (CT-33, Python). No second language in V1.
- **QMB** owns evaluation: run, declared-parameter optimize, robustness rungs, ranking views, ledger. Never authors bots. Never a “Builder engine.”
- **QMA** owns repeatable procedures (Custom Project analog) and, if an AD allows it, candidate generation that **compiles to** QML artifacts. Candidates stay dev-zone. No paper/live tools.
- **QMF** owns the producer catalog the generator may draw from.
- **QMN / UI**: no ownership of these research mechanisms. UI may later **display** QMB rank views; it must not copy AlgoWizard.

## 4. Open questions — AD vs Deferred

**Need an AD**

- Is **structure search** in scope for this architecture sitting, or is QMX V1 “human/agent writes Python, QMB only searches declared parameters”?
- If structure search is in: **random-only** (honors templates) vs **genetic** (SQ documents template drift). Default recommendation from donor docs: random-only if template control matters.
- If structure search is in: does a generated predicate become Python logic (keep V1 law) or force a predicate-grammar mint (contradicts QML Deferred)?
- Walk-forward: keep split-sequence of a **fixed** assignment, or add **per-window reoptimization** (donor WF)? That is a QMB extend with claim-class implications.
- Similar-strategy dismiss: stats-proximity fold vs relying on `fp1` identity only.

**Can stay Deferred**

- QML declarative predicate grammar (`docs/components/qml.md:80`).
- WF/OOS pass-battery **values** (GAP-0048/0049; QMB already refuses invented defaults).
- Sequential optimization / Optimization Profile / System Parameter Permutation as extra robustness rungs.
- WF Matrix 3D surface.
- Island genetic options, decimation, “fresh blood.”
- Custom Java snippets / per-databank Custom Analysis plugins.
- Improve-existing “parts to improve” as a distinct generator (version graph already covers “new Bot from old”).

---

## Do not copy

- AlgoWizard / Builder / Optimizer / Databank **UI**, 3D WF charts, fitness gauges.
- SQ genetic-programming **engine**, island migration, Java snippet runtime, `.sqx` format, MT4/NT/EasyLanguage export.
- Stored composite Fitness 0..1 or “Robustness score threshold” as a frozen pass/fail that gates money.
- Persisting synthetic/perturbed history as governed evidence.
- Vendor building-block catalog as a copy-paste indicator library (QMF wrap-not-reimplement + own catalog).
- A new “Builder / Databank / Custom Project” **service** beside QMB/QMA/QML.

Primary evidence: official URLs listed above (all fetched this sitting). QMX evidence: `docs/components/{qml,qmb,qma-daemon,qmf-indicators}.md`, `docs/contracts/ct-47-qma-experiment-spec.yaml`, `git show 1b451a848d897e42f6e2c7fd9f2ea86fab7295f2:qml/src/qml/…` and `qmb/src/qmb/…`.
