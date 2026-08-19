# 00 — QMF Synthesis: How the Ten Areas Fit Together, and the Module Map They Imply

**Written:** 2026-08-17. **Status:** entry point for the minimal-core design session.
**Sources:** the ten area briefs in this folder — `01-architecture-references.md`, `02-data-foundation.md`, `03-indicators-analysis.md`, `04-portfolio-risk-sizing.md`, `05-broker-connectivity.md`, `06-forex-domain-components.md`, `07-crypto-inefficiencies.md`, `08-mis-ml-regime-models.md`, `09-experimentation-search-overfitting.md`, `10-macro-micro-analysis-data.md`. This file does not repeat their content; it names the file where each claim lives.

---

## In plain words

1. Ten separate investigations, run independently, kept arriving at the **same four ideas**. That agreement is the strongest signal in the whole sweep, and it is what the module map below is built on.
2. **Idea one: every fact carries two times** — when it happened, and when we could first have known it. Price ticks, chart levels, economic numbers, model predictions and fills all need it. Four files invented it separately (`03`, `06`, `08`, `10`) and one framework already ships it (`05`).
3. **Idea two: write each calculation once, in the live "one bar at a time" form, and produce research results by replaying it.** Three mature platforms landed on this independently (`03`). It is also exactly what makes "no central backtest engine" workable: a backtest becomes a replay, not a separate program.
4. **Idea three: the strategy is never allowed to say how much money to risk.** It expresses an opinion; the framework sizes it; one mandatory gate can refuse it. Four frameworks do this, none of them does all of it (`04`).
5. **Idea four: nothing counts unless it is registered.** A component, a strategy, a model, a data split, an experiment — each becomes a small text record with a version, and results cite those versions (`08`, `09`).
6. The four ideas are not four features. They are one discipline applied in four places: **know what you knew, and be able to prove it later.**
7. There is essentially **nothing to buy or borrow** for the parts that matter most to you. No project has a cTrader adapter (`01`, `05`). No project models prop-firm rules (`04`). No maintained library does support/demand zones honestly (`06`). Those three are QMX's actual work.
8. The most popular library for your style of trading, `smartmoneyconcepts`, **reads future candles**. A user measured its backtest profit factor falling from 7.32 to 1.82 once that was removed. It has been known for two years and is unfixed (`06`).
9. The arithmetic that should scare us most: try a million variations of a worthless strategy and the best will show a Sharpe of 4.87. Five years of data only honestly supports about 45 independent attempts (`09`). LLM agents can burn that budget in an afternoon.
10. So QMF's job is not to help agents search harder. It is to **count the searching and refuse when the evidence is spent**.
11. On the data side: plain compressed files plus DuckDB and Polars is the right answer for one person. No database server, no ArcticDB, no feature store (`02`, `08`, `10`).
12. On the broker side: cTrader over our own thin client, because the official Python SDK is two years stale and MetaTrader 5 needs a Windows emulator on the Linux box (`05`).
13. Two of the free things we depend on **cannot be bought back later** — the economic calendar feed and our own tick stream. Every day we do not archive them is a day permanently lost (`10`).
14. Almost everything a machine-learning subsystem could tell us about forex is about *volatility*, not *direction*. It belongs in the "when not to trade" seat, never the "what to trade" seat (`08`).
15. Net: about fifteen small packages, of which QMF genuinely *builds* the domain-shaped half and *wraps* well-chosen libraries for the maths.

---

## How the five hats link

The five hats are not five subsystems. The sweep shows they are five *readings* of a small number of shared objects. Where a component serves several hats, it is load-bearing and must be got right once; where it serves one, it can be thin.

**The ten cross-cutting components, and who reads each:**

| Shared object | Analyst | PM | Trader | Developer | Researcher | Why it is shared |
|---|:--:|:--:|:--:|:--:|:--:|---|
| **`Provenance` (two timestamps)** | ● | | ● | ● | ● | Analyst asks "what did I know then"; trader needs venue-vs-local clocks for reconciliation (`05`); researcher needs it to prove no leakage (`06`, `08`); developer gets **one** invariant to test instead of five. Independently invented in `03`, `06`, `08`, `10`. |
| **Domain model (Instrument/Order/Position/Fill)** | ● | ● | ● | ● | ● | The single reason "same strategy, backtest and live" can be true rather than aspirational (`01`). |
| **`Indicator` protocol + `replay()`** | ● | | ● | ● | ● | One definition, two execution modes. Analyst gets a column, trader gets a live value, researcher gets a backtest — provably the same numbers (`03`). |
| **`VenueModel`** (what this venue *allows*) | | ● | ● | | ● | Trader is constrained by it live; researcher is constrained by the *same object* in simulation; PM's sizing needs its fees, lot step and leverage (`05` LEAN split, `04` sizing signature). |
| **BMS gate + typed denial reasons** | ● | ● | ● | | ● | PM owns it; trader's orders pass through it; researcher runs it as a **hard disqualifier inside the fitness function** (`09` §14.6); analyst reads the reason codes as diagnostics (`04`, `05`). |
| **Registry + manifests** | | ● | ● | ● | ● | Developer's versioning, researcher's reproducibility, PM's audit of what is live, trader's rollback pointer. Same file format for components, models, books, splits and experiments (`08`, `09`). |
| **Spread / tradeability profile** | ● | ● | ● | | ● | Analyst measures it; trader times entries by it; PM gates a prop-firm attempt on it; researcher uses "spread cost as a share of edge" to kill unviable ideas before a backtest is run (`10` M2/M4). |
| **`MarketView` trust triple** (confidence / novelty / staleness) | ● | ● | | ● | ● | Analyst produces it; PM's BMS acts on it *without knowing any ML*; researcher calibrates the thresholds; developer enforces `causality` so a look-ahead model cannot reach a live consumer (`08`). |
| **Split registry + budget ledger** | | ● | | ● | ● | Researcher spends it; PM reads it as "how much evidence backs this book"; developer makes exhaustion an error, not a warning (`02`, `09`). |
| **Slippage / fee models** | ● | ● | ● | | ● | Trader *measures* realised slippage live; researcher *simulates* with the same vocabulary; PM's sizing consumes commission. Nobody surveyed closes this loop for retail FX (`10` §7.2). |

**Three correlations worth naming explicitly, because they change the design:**

- **Trader ≡ Researcher, structurally.** If the simulator is just another `BrokerAdapter` and the sim clock just another `Clock`, then the trader's runtime *is* the researcher's runtime. This is the concrete meaning of "no central backtest engine": there is no `Backtest` class that owns a loop; there is one kernel and two sets of injected parts (`01`, `05`, `03`).
- **PM ≡ Researcher, through the ledger.** Prop-firm rules are path constraints; path constraints are pre-registered hard disqualifiers in a search; a disqualified candidate is a *rule* rejection, not a *metric* selection. The money rules and the epistemics are the same schema read twice (`04` §4.4, `09` §14.6).
- **Analyst ≡ everybody, through provenance.** Every analyst output — a level, a regime, a rate differential, a spread percentile — is a fact with two timestamps. Once that is one type, the analyst hat stops being a separate subsystem and becomes a set of producers into one store (`06`, `08`, `10`).

---

## Proposed QMF module map

Dependency arrows point **one way only**, outward from `qmf.core`. Nothing in a lower ring imports from a higher one. `qmf.strategies/` is a drop-in directory *outside* the package, importable by nothing (`01`).

### Ring 0 — Core (developer hat owns; every hat reads)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.core` | `Decimal` money/price/quantity, UTC-nanosecond `Clock`, the **`Provenance`** struct (`ts_event`/`ts_init`, `known_at`/`known_until`, `origin`/`confirmed_at`), total event ordering, deterministic seeding. | all | **Build** (~400 lines). Design from `05`/`10` (`ts_event`/`ts_init`), `06` (`origin_bar`/`confirmed_at`), `10` (`known_at`/`known_until`), `09` (seed + thread discipline). |
| `qmf.model` | The one domain model: `Symbol=(venue,symbol)` opaque, `InstrumentSpec` (nullable superset covering forex CFD *and* crypto perp), `Bar`, `QuoteTick`, `TradeTick`, `Order`, `Fill`, `Position`, `AccountState`, `BarSpecification`. | all | **Build.** Field sets lifted from `05` (cTrader/LEAN), `07` (ccxt `MarketInterface` ∪ Hummingbot `TradingRule`), `10` (Nautilus bar taxonomy). |
| `qmf.errors` | Two-branch hierarchy: `VenueRejection` (deterministic no) vs `OperationFailed` (unknown). Plus BMS denial codes. | trader, PM, dev | **Build.** Shape from ccxt (`05`), codes extended per `04`. |

### Ring 1 — Data (analyst + researcher own; trader reads live tail)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.data.lake` | Hive-partitioned zstd Parquet archive (`symbol/year/month` ticks), SQLite-WAL live inbox, named compaction, per-partition sha256 manifest. | analyst, researcher | **Build thin over** DuckDB + Polars + pyarrow (`02`). |
| `qmf.data.splits` | The split registry: named `is`/`oos`/`embargo`/`holdout` windows. `load(split_id=...)` is the only door; raw dates do not exist in the signature. | researcher, PM | **Build** (`02` §5). |
| `qmf.data.facts` | One append-only **bitemporal** table for everything non-price: macro series, calendar events, forecasts, consensus, model predictions, scenarios. `as_of(t)` is the only accessor. | analyst, PM, researcher | **Build over** DuckDB `ASOF JOIN` / Polars `join_asof(strategy="backward", allow_exact_matches=False)` (`10` §9). |
| `qmf.data.ingest` | One ~40-line adapter per source: Dukascopy `.bi5`, cTrader history, BIS `WS_CBPOL`/`WS_EER`, ECB, FRED+ALFRED (keyed), CFTC TFF, FairEconomy calendar. Each terminates in a schema check. | analyst | **Build** + wrap `httpx`, `pandera`. Reject `fredapi`-class wrappers except optionally FRED (`10` §2.11). |
| `qmf.data.micro` | Spread distribution, spread profile by pair×hour×weekday, tick-arrival rate, session profile, rollover window, weekend gaps → a per-pair-per-hour **`tradeability`** score. | analyst, trader, PM | **Build** (~300 lines, no library exists) (`10` Part B). |

### Ring 2 — Features (analyst owns; trader and researcher consume identically)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.indicators` | `Indicator` protocol (`handle_bar` / `peek` / `reset` / `has_inputs` / `initialized` / `warmup_bars`), a single `replay()` driver, warm-up arithmetic, `stability` class, and a metadata registry. | analyst, trader, researcher | **Wrap** TA-Lib (batch, metadata, 61 candle patterns) + **build** ~15 incremental indicators, with `talipp` as a test-only oracle (`03`, `06` §4.1). |
| `qmf.structure` | Causal market structure: ATR-normalised commit-on-threshold zigzag, Williams fractals, BOS/CHoCH with `close_break`. Every output carries `origin`/`confirmed_at`. | analyst, researcher | **Build.** Loop shape from `jbn/ZigZag`, definitions from `smc.py`, **code from neither** (`06` §2). |
| `qmf.components` | **The four first-class typed concepts** — see the sub-section below. | all | **Build.** |

### Ring 3 — Intelligence (analyst produces, PM consumes)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.mis` | Publishes the frozen `MarketView`: regime + probabilities, volatility forecast, and the trust triple `confidence` / `novelty` / `staleness`. `causality` may only be `filtered` or `predicted`. | analyst, PM, researcher | **Wrap** `statsmodels.regime_switching` + `arch` (training side); **build** the one-step forward recursion so nothing smoothed reaches live (`08` §2, §7.4). |
| `qmf.models` | Model registry and loaders: JSON manifest per artifact (`scope: global | book:<id>`, `causality`, `fitted_through`, `expires_after`, `input_contract`, `artifact_sha256`, `promotion_state`, `supersedes`), plus the append-only prediction log. **No `pickle` runtime exists.** | researcher, dev, PM | **Build** + wrap LightGBM's *text* model format (`08` §5, §7, §8). |

### Ring 4 — Money authority (PM owns; nobody else may write to it)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.book` | A Book converts a dimensionless `Signal` into a target position: fixed-fractional sizing with `commission_rate`, `exchange_rate`, `hard_limit`, `unit_batch_size`; optional volatility target; a portfolio risk multiplier in [0,1] computed as `min()` over independent limit checks, with the binding constraint **named**. | PM, researcher | **Build.** Sizing signature from Nautilus, split from pysystemtrade, overlay shape from pysystemtrade — **designs only, both are (L)GPL** (`04`). |
| `qmf.bms` | The single mandatory pre-trade gate. `TradingState ∈ {ACTIVE, REDUCING, HALTED}` with cancels always permitted; typed denial codes; a six-axis prop-firm rule schema (anchor / measure / cadence / day-boundary tz / ratchet-lock / breach action); durable state reconciled against the broker at startup. | PM, trader, researcher | **Build — genuinely greenfield.** `04` §4.5 found no prior art worth copying. |

### Ring 5 — Venue (trader owns)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.broker` | The platform-blind port: `capabilities()` with an `EMULATED` sentinel, `limits()`, `instrument()`, order commands returning `outcome ∈ {ACCEPTED, REJECTED, DENIED_LOCALLY, UNKNOWN}`, one ordered event stream, the reconciliation triple, separate rate buckets with an order-priority lane. | trader, dev | **Build.** Shapes from ccxt (`has`, `info`), Nautilus (three-tier outcome, reconciliation), LEAN (`IBrokerage`) (`05`, `07`). |
| `qmf.broker.ctrader` | The only place cTrader dialect exists: length-prefixed protobuf over TLS, two-stage auth, heartbeat, delta-decoding, pagination, `ProtoOAErrorCode` → QMF error table. | trader | **Build ~400 lines asyncio over vendored `.proto`.** Do **not** build on `ctrader-open-api` (`05` §2). |
| `qmf.venue_model` | What a venue *allows*: order types, fee model, slippage model, session schedule, min/max/step. Used identically by live and by simulation. | trader, PM, researcher | **Build**; interface shape adapted from LEAN `BrokerageModel` / `ISlippageModel` (Apache-2.0, safe to adapt) (`05` §6, `10` §7.2). |

### Ring 6 — Runtime and simulation (trader + researcher share; this is where "no central backtest engine" lives)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.runtime` | The kernel: single-threaded deterministic dispatch, cache-then-publish ordering, register→warm→subscribe sequencing, a loader that instantiates a strategy under wall-clock and memory budgets and survives its crash. | trader, researcher, dev | **Build.** Copy Nautilus's ordering/threading and LEAN's `Loader`+`Isolator` containment (`01`). |
| `qmf.sim` | **Not an engine — four callable parts:** `SimClock`, `SimBroker` (an ordinary `BrokerAdapter` that passes the same conformance suite), `FillModel`/`SlippageModel` calibrated from measured live slippage, and a `Ledger` whose P&L includes a **`financing`** line (forex swap ≡ crypto funding). | researcher, trader | **Build** (`01`, `05`, `07` bonus, `10` §7). |
| `qmf.metrics` | Performance statistics with **four input shapes** (returns / realised P&L / orders / positions), benchmark-relative ones nullable by default, emitting one versioned machine-readable JSON contract. | analyst, PM, researcher | **Build** (~34 statistics); `quantstats` research-environment only, never on the VPS (`03` §8). |

### Ring 7 — Epistemics (researcher owns; PM reads the verdict)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.experiment` | The `Experiment` object: required `hypothesis`, pre-registered thresholds, declared trial budget, `split_id`, seeds, environment, lineage. Owns the search loop via Optuna **ask-and-tell**, so it owns the refusal point. Returns a result object with **no naked float**. | researcher, PM | **Wrap** Optuna (MIT); **build** the refusals (`09` §7.1, §14). |
| `qmf.overfit` | DSR, PSR, PBO via CSCV (+ its IS→OOS slope), MinBTL-vs-actual, `effective_n_trials`, Harvey–Liu haircut, plus SPA/StepM/MCS. | researcher, PM | **Build** the closed forms (~200 lines), validated in CI against `purgedcv` as an oracle; **wrap** `arch` for the bootstrap tests (`09` §4, §6). |
| `qmf.ledger` | The append-only split budget ledger. Budget is *derived* from MinBTL, spent in *effective* trials, and `SplitBudgetExhausted` is an error with **no `force=True`**. | researcher, PM, dev | **Build** (`09` §14.4). |

### Ring 8 — Registry and authoring surface (developer owns; agents see only this)

| Module | Responsibility | Hats | Wrap / build |
|---|---|---|---|
| `qmf.registry` | One manifest format, one discovery function, one promotion state machine — for components, confluences, models, books, prop-firm rulesets, splits and experiments. Content-addressed, append-only, retirement never deletes. | dev, researcher, PM | **Build** (~300 lines). Manifest idea from FreqAI, scoping/promotion from `08` §7.3. |
| `qmf.spec` | **The entire surface an LLM agent sees** — target: one printed page. Typed schemas + validators for `Level`, `Trigger`, `Confirmation`, `Exit`, `Confluence`, `BookConfig`, `ExperimentRequest`. No order methods, no raw dates, no floats, no venue enums. | dev, all agents | **Build** (`01` §23, `09` §14.7). |
| `qmf.app` / `qmf.cli` | The two deployables' thin shells: Windows research app (charts, tearsheets, plotly) and the Linux VPS process (inference + trading only). Two lockfiles, machine-enforced. | dev, operator | **Build thin** (`08`, `10` §8.2). |

---

### Level / Trigger / Confirmation / Exit as first-class typed concepts

The four slots are **types**, not conventions. Each is a frozen, JSON-serialisable *spec* — `{kind, params, component_version}` — never a callable an agent supplies.

```
Level        → emits Zone{provenance, lower, upper, side, kind, strength, state}
Trigger      → emits Signal{provenance, direction, conviction, invalidation_price?}   # never a size
Confirmation → emits Score{provenance, value ∈ [0,1], weight, evidence_state}         # never an entry
Exit         → a chosen typed policy (fixed-R | ATR-multiple | structure-invalidation
                | trailing-to-structure | partial-at-R) + numbers.  Framework-owned.
Confluence   = {level: Level, trigger: Trigger, confirmations: [Confirmation],
                exit: Exit, sizing_policy: ..., gates: [...],
                max_bars_between_touch_and_trigger: int}
```

Three properties make this safe for an agent author, and each comes from a specific finding:

- **`Signal` carries no quantity.** An agent that cannot express "buy 5 lots" cannot blow the account through sizing (`04` §Copy 1). `qmf.book` alone converts conviction → size; `qmf.bms` alone can veto.
- **`Confirmation` cannot generate an entry.** Candlestick patterns tested negative (`06` §4.1), SMC has no peer-reviewed support (`06` §1.4), regime models do not predict FX direction (`08` §3), COT does not predict next week (`10` §3.3). The type system encodes that: these are weights, not triggers.
- **`Exit` is a choice from a closed set, not free-form code.** Stops, sizing and correlated-basket limits are framework property (`06` §Exit, `04`).

**Registration.** A component kind is registered once as a `ComponentDef`:

| Manifest field | Purpose |
|---|---|
| `component_id`, `semver` | Identity and definitional version, e.g. `level.order_block@2.1.0` |
| `input_contract` | Exact ordered inputs + which QMF producer supplies each. Binding is **refused** on mismatch (FreqAI's `check_if_feature_list_matches_strategy`, `08` §9.2e) |
| `output_schema` | Named fields + types + ranges — machine-readable so an agent discovers it without reading code |
| `warmup_bars`, `stability` | `lookback + unstable_period + 1`; TA-Lib's four stability classes, with `path_dependent` warned loudly (`03`) |
| `causality` | `filtered` \| `predicted`. `smoothed` is **not constructible** for a live-bound component (`08`) |
| `canonical_resolution` | Which timeframe the definition is *defined at* — a sweep on M15 is not a sweep on M5 (`06` OQ8) |
| `evidence_state` | `hypothesis` \| `measured` \| `validated` \| `retired`, with a citation. SMC and candlesticks ship as `hypothesis`, visibly |
| `definition_source` | Pointer into the research store: paper, video timestamp, chat message (`09` OQ9) |

**Confluence identity is a content hash.** `confluence_id = sha256(canonical_json(spec))` over the fully-resolved parameter set *plus every component's semver*. Consequences, all free:

- The same confluence "discovered" twice by two agents is the **same id** — automatic deduplication, and the budget ledger can tell whether a search actually explored anything new.
- A backtest result is keyed by `(confluence_id, split_id, data_fingerprint, qmf_version, venue_model_id)`. Changing what `OrderBlock` *means* bumps a semver, changes the hash, and **old results do not silently become claims about the new definition** — which is the unresolved problem in `06` OQ7.
- Promotion is a manifest edit, never a file move: `proposed → measured (explore, unlimited, unreportable) → validated (budgeted) → confirmed (holdout, budget of 1) → live → retired`, with a `supersedes` pointer as the rollback path (`08` §7.3, `09` §14.5).
- Records are append-only. **Failed confluences are the most valuable rows in the table, because they are the denominator** (`09` §11.2).

---

## Novel ideas

These were not asked for. Each is supported by evidence already in the briefs.

1. **Collapse five provenance inventions into one `Provenance` type, then write one property test.** `03`/`06`/`08`/`10` each independently derived a two-timestamp rule. `08` §2.3 gives the machine-checkable form: `label(bars[0:t])[-1] == label(bars[0:t+n])[t]`. Generalise it from regime models to **every** registered component and run it in CI as a **precondition of registration**. That single test is the only defence against an agent reproducing the `smartmoneyconcepts` lookahead at 3am — and it costs one afternoon.

2. **Make the simulator an ordinary `BrokerAdapter`, and give it the adapter conformance suite first.** Hummingbot ships a shared `connector/test_support/` suite (`01` §7). If `SimBroker` is implementation #1 and cTrader is implementation #2, both pass the same tests, backtest≡live becomes structural rather than aspirational, and "no central backtest engine" stops being a slogan and becomes a dependency graph.

3. **Refuse a confluence at registration time if its edge is smaller than its spread.** `10` M4 computes spread-cost-as-share-of-edge from data we already have. Turn it into a **registration precondition**, not a report. A confluence whose median winner at its trading hours is smaller than the p90 spread cannot be registered, is never backtested, and therefore **never spends split budget**. This is the cheapest possible way to protect the scarce resource identified in `09`.

4. **Close the slippage loop.** `10` §7.2 notes that LEAN *simulates* slippage and nobody *measures* it back. Measure realised slippage live, conditioned on session and event proximity, and feed the distribution into `qmf.sim`'s `FillModel` as its parameters. Backtest fidelity then becomes a **measured, improving quantity** rather than a constant guessed once — and it quantifies exactly what the news blackout gate is worth.

5. **Publish `tradeability` as a BMS input, not an analyst chart.** The per-pair-per-hour spread score from `10` M2 is the honest answer to "is this pair clean enough right now". Wire it into `qmf.bms` alongside the prop-firm rules so a challenge is never attempted in a hostile hour. Costs nothing extra — the data is already being collected.

6. **Build ingestion before anything that consumes it.** `10` §4.3 is the strongest sequencing argument in the sweep: apart from ALFRED, **no free source lets you buy back point-in-time history**. The FairEconomy calendar is this-week-only; our own tick stream exists only if we record it. Every week of delay is permanently lost evidence. Ship `qmf.data.ingest` + `qmf.data.facts` + the tick recorder *first*, before components, before the sim.

7. **Two lockfiles, enforced by CI, not by discipline.** `08` and `10` disagree about the VPS dependency set — and both are right, because they are describing different processes. Resolve it structurally: a **trading** lockfile (numpy, polars, duckdb, pyarrow, httpx, LightGBM text loader, `river.drift`, the broker client) and an **analysis** lockfile (adds statsmodels, arch, ruptures, pandera, scipy). `10` §8.2's rule — >50 MB or >30 dependencies is research-only — becomes a CI assertion on the trading lockfile.

8. **Financing as a P&L line item from day one.** Forex swap/rollover and crypto funding are the same accounting object (`07` bonus). Retrofitting it later touches the ledger, every report and every stored result. It costs one column now.

9. **Make `evidence_state` visible in the operator UI.** Rather than refusing SMC, candlesticks, regime models and COT — all of which have negative or absent evidence (`06`, `08`, `10`) — register them honestly with a citation and a badge the non-technical operator can see, and let an agent read the same field when weighting confirmations. Honesty as a data field beats honesty as a doc paragraph.

10. **The three data layers are three different accessors, not three conventions.** Explore (unlimited, unreportable), Validate (budgeted), Confirm (budget of 1). The Confirm holdout should be **not loadable at all** until a Validate pass is recorded against the confluence (`09` §14.5). Structural, not documented.

11. **Cross-file corrections worth carrying into the design session.** `10` §9.3 shows `02`'s blanket ArcticDB licence block is stronger than the licence text supports — the real objection is technical (transaction-time only, no valid-time axis). `10` §5.1 shows `06` understated the FairEconomy feed: it is forward-dated, and is therefore the primary v1 supply of scheduled-event rows. Amend both records so the ledger is accurate.

---

## Decide next

Ordered by irreversibility. Each is one question; the recommendation is mine, not a consensus.

**A. Decisions that are very expensive to reverse after the first line of code**

1. **Will QMX ever be sold, licensed, or served over a network?**
   → **Assume yes.** That makes the dependency pool Apache-2.0 / MIT / BSD / NCSA plus original code, and rules out NautilusTrader (LGPL), vectorbt (Commons Clause), backtesting.py (AGPL), Freqtrade and pysystemtrade (GPL — design study only), DEAP, `pingouin`, `dbnomics`, `wbdata`. Ratify once, apply everywhere. (`01` OQ1, `03` OQ4, `09`)

2. **Do we write QMF's engine, or build it on top of NautilusTrader?**
   → **Write it, copy the shapes.** Nautilus is at v2.0.0rc3 mid-rewrite with a sweeping rename list and documented feature gaps; adopting it now means inheriting somebody else's migration, plus LGPL. Revisit after 2.0 stable. (`01` OQ2)

3. **Is the simulator just another `BrokerAdapter`, so there is no backtest engine at all?**
   → **Yes.** `SimBroker` + `SimClock` injected into the one kernel; the conformance suite runs against both. This is the concrete form of the brief's "backtesting decentralises into callable components". (`01`, `05`)

4. **What are the canonical numerical definitions — indicator seeding, timestamps, and symbol identity?**
   → **TA-Lib is canonical for indicators** (its metadata and 150-function catalogue come free); **UTC nanoseconds everywhere**; **identity is `(venue, symbol)` with the symbol string treated as opaque**. All three invalidate every prior backtest if changed later. Decide before the first strategy exists. (`03` OQ2, `02` OQ8, `05` OQ9, `07`)

5. **Do LLM agents write Python, or fill a typed schema?**
   → **Schema first.** Agents compose registered components into a `Confluence` spec through `qmf.spec`. Free-form Python is a separate, gated path requiring a human click, and agents never deploy to live unattended — Hummingbot's shipped rule: the agent may propose configuration, safety limits are user-only. (`01` OQ3/OQ4 §14)

**B. Decisions that set the scope of the first build**

6. **Is `Confluence` the unit of registration, content-addressed by hash, with components carrying their own semver?**
   → **Yes**, per the sub-section above. It gives deduplication, honest trial counting and non-rotting historical results for one hash function. (`06` OQ7, `08` §7.3, `09` §14)

7. **What is `SR*`, the pre-registered Sharpe bar? It sets the whole search budget.**
   → **1.5 for personal capital, 2.0 for a prop-firm book.** At SR\*=1.0 a five-year split allows ~45 effective trials; at SR\*=2.0 it allows ~1,600. A higher bar buys enormously more search freedom *and* demands a better strategy — that is the right trade for an agent-driven pipeline. (`09` OQ3)

8. **Which prop firm does the first Book model, and is the Book a simulator, a live guard, or both?**
   → **FTMO 2-Step** (static max loss, 00:00 CE(S)T daily anchor) since cTrader/forex-first; **one rule-evaluation core run in both contexts**, with a configurable safety buffer that trips at ~80% of the firm's cap. Build the six-axis schema; instantiate one firm. (`04` OQ1, OQ2, OQ3)

9. **Do we build ingestion before anything that consumes it?**
   → **Yes.** Tick recorder, FairEconomy daily poll, and the `facts` table ship first. This is the only decision in the list where delay destroys value that cannot be recovered at any price. (`10` OQ5)

**C. Decisions that need the operator, not the framework**

10. **Which levels does Mubarak actually watch, and is a confirmation lag acceptable?**
    → **Pick three of the seven candidate `ZoneKind`s by screen-share, not by more research** — building all seven is roughly 3× the work. And demonstrate the causal-swing lag (a ±5-bar fractal is knowable 5 bars late; 75 minutes on M15) side-by-side against his current charts *before* it arrives as a bug report. (`06` OQ1, OQ6)

11. **Which cTrader broker, and do we submit the Spotware app registration this week?**
    → **Submit now, pick two candidate brokers, verify Open API on both a demo and a live account.** Spotware reviews new Open API applications before development is sanctioned; it is the longest-pole external dependency and it gates the entire trader hat. (`05` OQ1, OQ2)

12. **Dukascopy's terms forbid automated download. Accept, or build history from the broker only?**
    → **Accept for personal, non-redistributed use, recorded as an explicit dated decision in the ledger** — and in parallel measure how far back the chosen cTrader broker actually retains tick history, so a fallback exists. This is a risk posture, not an engineering call. (`02` OQ1, OQ2)
