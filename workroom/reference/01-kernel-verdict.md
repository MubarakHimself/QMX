# 01 — The Kernel Verdict (rev2): Build It, Adopt One, or Both?

**Written:** 2026-08-17 · **Revision 2**, rebuilt on `reference/studies/nautilus-trader.md` and `reference/studies/backtest-engines.md`, which did not exist when rev1 was written.
**Decides:** `research/00-qmf-synthesis-module-map.md` decision **D2** ("Do we write QMF's engine, or build it on top of NautilusTrader?")
**Depends on:** **D1** (licence posture — still pending, and this brief asks you to amend it) · **Status:** recommendation, open to disagreement.

**Evidence read in full for this revision:** `reference/studies/nautilus-trader.md` · `reference/studies/backtest-engines.md` · `reference/studies/jesse.md` · `reference/studies/bot-frameworks.md` · `reference/studies/platform-patterns.md` · `reference/studies-wave2/fill-simulation.md` · `reference/studies-wave2/macro-backtester.md` · `research/01-architecture-references.md` · `research/00-qmf-synthesis-module-map.md`. Plus direct measurement of the clones under `reference/repos/`, commands given inline.

---

## What changed since rev1, including where I was wrong

Rev1 was written without the two deepest studies. Three things in it were wrong or too soft, and I would rather lead with them than bury them.

**1. I undercounted the build by roughly three times.** Rev1 said "the kernel is ~4,000 lines of Python." `reference/studies/nautilus-trader.md` §"What a from-scratch Python-only kernel would actually cost" puts an honest, itemised number on the same job for one venue: **13,000–19,000 lines of Python, plus a comparable or larger volume of tests, and three to six months to production confidence.** The same study also confirms my 4,000-line figure — but only as *the skeleton*: "Clock + bus + cache + engines + strategy base + a naive `SimBroker` is roughly 2,500 lines and two to four weeks. That produces something that *runs*. Everything after it… is the other 80% and the part that decides whether real money survives." Rev1 quoted the number that makes building look easy. That was the wrong number.

**2. The single most decisive fact about Nautilus was missing.** In v2 there is no Python implementation left at all. I counted it in the clone:

```
$ find python/nautilus_trader -name "*.py" | wc -l          → 49
$ find python/nautilus_trader -name "*.py" -exec cat {} + | wc -l → 5,476
```

The entire published Python package is **49 files, 5,476 lines**, and almost all of it is one-line re-exports of a compiled Rust extension (`from nautilus_trader._libnautilus.<area> import *`, verified in `python/nautilus_trader/adapters/binance/__init__.py` and every sibling). Behind it sit ~1.1 million lines of Rust. That reframes "adopt Nautilus" completely, in a way rev1 did not see.

**3. My factory-day estimates need to go up on every option**, and the honest headline is that on raw days the options remain within each other's error bars — as rev1 said — but at higher numbers than rev1 quoted. See §(c).

Everything else in rev1 survives contact with the new evidence, and two of its arguments got considerably stronger.

---

## 0. Where you were right

You pushed back on "write our own kernel, copy proven shapes" by saying mature platforms exist and we should not reinvent the wheel. Three parts of that are simply correct.

**"Write our own kernel" was phrased as if it meant "write everything."** It does not, and rev1 was sloppy about saying so. The plan already wraps other people's code for the great majority of the system by volume: TA-Lib for indicators, DuckDB and Polars for the lake, Optuna for search, `statsmodels` and `arch` for statistics, `pyarrow`, `httpx`, `pandera` (`research/00` Rings 1–7, "Wrap / build" column). You were reacting to a phrase that overstated the build, and the phrase deserved the reaction.

**The licence objection against Nautilus was stated too strongly.** `research/00` A.1 says assuming QMX may be sold "rules out NautilusTrader (LGPL)". That is stronger than LGPL-3.0 actually says, and `reference/studies/nautilus-trader.md` §"Licence & maturity" agrees with the correction: LGPL permits linking from a proprietary application, and subclassing a library class is explicitly "a mode of using an interface provided by the Library." The obligations bite on *modification* and *redistribution*, not on use. §(b) works this through. It matters, because it removes the cheap reason to dismiss adoption and forces the decision onto real ground.

**"Backtesting runs on the same core as live" is the right thing to be impressed by.** It is the strongest architectural finding in the whole reference set, and it is now confirmed four independent times. Nautilus proves it *hardest*: the simulated venue is not a special case, it is an ordinary `ExecutionClient` over a venue-agnostic matching engine, and there is a **third** mode — "sandbox", live prices with simulated fills — built from the same machinery (`crates/adapters/sandbox/src/execution.rs`, per `reference/studies/nautilus-trader.md` §Mental-model-3). Lumibot ships it commercially (`lumibot/backtesting/backtesting_broker.py`, a 5,008-line subclass of the same `Broker` ABC every live venue implements — `reference/studies/bot-frameworks.md` §Mental-model-1). Jesse runs two speeds of one replay and CI-tests that they are bit-identical (`jesse/modes/backtest_mode.py:536` vs `:1048`). rqalpha swaps the broker as a plug-in and emits the same events either way.

What follows disagrees with your conclusion, not your reasoning — and it disagrees more narrowly than you would expect.

---

## (a) What "the kernel" actually is, in plain words

"Kernel" sounds like the biggest, hardest thing in the system. It is the smallest. It is the traffic-control code in the middle, and here is the honest inventory.

**The kernel decides what happens next, and in what order.** Nine jobs:

1. **It holds the clock.** One object answers "what time is it." In live it reads the wall clock; in a backtest it reads the next bar's timestamp. Nothing else may ask the operating system for the time. In Nautilus this is 155 lines — a `ClockFactory` that hands out a `TestClock` or a `LiveClock` (`crates/system/src/clock_factory.rs`). *There is no `if backtest:` anywhere in their kernel.* That factory is the entire "backtest ≡ live" mechanism, and it is smaller than most of QMX's data adapters.

2. **It takes events one at a time, on one thread.** A tick, a fill, a timer. One queue, strict order, never two at once. This is the only reason a backtest number means anything: run it twice, get the same answer. Nautilus cites the LMAX single-threaded design for this and keeps it in live trading too — async at the edges (sockets), synchronous and single-threaded at the core (`crates/live/src/runner.rs`).

3. **It writes each new fact into a cache *before* telling anyone about it.** So when your strategy runs and asks "what's the current price", the answer is already there and already right. Getting this backwards is a whole family of bugs that simply cannot occur if you do it in this order (`docs/concepts/architecture.md`, "life of a quote tick").

4. **It calls the strategy's methods in a fixed order, every time.** Jesse's is `before() → check() → after()` (`jesse/strategies/Strategy.py:1308`). Lumibot's is `before_market_opens → on_trading_iteration → after_market_closes` (`lumibot/strategies/strategy.py:5286-5680`). The strategy never owns a loop; the kernel runs the strategy.

5. **It warms the indicators up before anything may trade.** Counts how many bars each needs, feeds them, refuses to call the strategy until every one is ready. backtrader does this automatically by walking the tree of indicators and taking the maximum (`backtrader/lineiterator.py:120-135, 174-176`), so a strategy's `next()` is *structurally incapable* of running on a half-warm indicator. That single feature, from a dead 2015 project, is the best idea in it.

6. **It loads the strategy under a leash.** Instantiates it with a time and memory limit, wraps it behind an interface, survives its crash. LEAN's own comment: *"Loader creates and manages the memory and exception space of the algorithm, ensuring if it explodes the Lean Engine is intact"* (`research/01` §2). For LEAN the untrusted author is a stranger on the internet. For QMX it is an LLM.

7. **It sends every order through exactly one door.** No order from any source reaches a broker without passing the pre-trade gate. Nautilus calls it `RiskEngine`; hummingbot calls it `budget_checker`; rqalpha calls it `AbstractFrontendValidator` and has the nicest shape — *returning a reason string means denial, returning `None` means pass*, with cancellations on a **separate** method so a "reduce-only" state can block entries while still permitting exits (`rqalpha/interface.py:711-733`). QMF calls it `qmf.bms`, and that separate-door detail is exactly `TradingState.REDUCING`.

8. **It records a snapshot after every iteration whether or not anyone asked** — portfolio value, cash, open positions, which bar caused this. In lumibot the audit trail is engine code wrapped around every lifecycle call, so a strategy author *cannot forget* to produce one.

9. **It talks to the outside world through one small named slot.** "Place this order." "Give me these bars." "What's my balance." Two plugs fit that slot: a real broker and a simulated one. Swap the plug and the same strategy runs live or over five years of history — **and there is no second program called "the backtester" at all.**

That last point is the one you were impressed by. It is not a feature you build; it is a consequence of doing jobs 1 and 9 properly.

**What the kernel is *not*.** Not the indicators. Not the data lake. Not the cTrader connection. Not the sizing maths. Not the prop-firm rules. Not the overfitting statistics. Not the agent schema. Not the charts. Each of those is a separate module in `research/00`'s map and most wrap somebody else's library.

### How big is it, honestly

Two numbers, and the gap between them is the whole argument.

**The skeleton is small.** `reference/studies/backtest-engines.md` §6 measures the part of rqalpha that everything else exists to serve — the simulated broker, the matcher, the slippage model — at **under 700 lines**. And it costs QMF's backtest capability at "roughly 1,500 lines of new code across five small modules": `SimClock` (~150), `SimBroker` (~300), `FillModel` (~400), `Ledger` (~250), `metrics` (~400). Nautilus's own study says the equivalent skeleton is ~2,500 lines and two to four weeks.

**The production kernel is not small.** The same Nautilus study itemises the honest cost for **one venue, one account model, market/limit/stop plus attached stop-loss and take-profit, bars and quotes only, no order book**:

| Piece | QMF, honest Python | Note |
|---|---:|---|
| Value types (nanosecond time, Decimal money/price/qty, identifiers) | 600–900 | cheap; get precision and fail-fast right once |
| Domain model (instrument, bar, order, position, account, events) | 2,500–4,000 | **the order state machine is the hidden cost** |
| Clock (sim + live) + timers | 400–600 | |
| Message bus | 250–400 | |
| Cache + indexes | 800–1,200 | only if split by concern |
| Data engine + time-bar aggregation | 700–1,000 | |
| Execution engine | 1,200–1,800 | |
| Risk engine + trading state | 500–800 | BMS is separate and additional |
| Portfolio: balances, margin, PnL, cross-rates | 800–1,200 | multi-currency CFD margin is genuinely fiddly |
| `SimBroker` matching + fill/fee/latency models | 1,500–2,500 | second-largest item |
| Kernel + component lifecycle | 500–800 | |
| Backtest driver | 400–600 | the *ordering* is the hard part, not the code |
| Live runner | 400–700 | |
| **Startup reconciliation** | 800–1,200 | **largest risk-per-line item in the table** |
| cTrader adapter + conformance suite | 1,500–2,000 | no prior art anywhere |
| **Total** | **13,000–19,000** | plus a comparable or larger volume of tests |

And the cost signal that matters more than the line count, from the same study: in the Nautilus crates sampled, **test code runs 0.7×–1.6× production code** — `crates/execution` carries ~40k lines of tests against ~56k of production. That ratio, not the feature list, is what "production-grade" costs.

QMX can cut below the 13k–19k figure because that estimate still assumes more breadth than we need. But rev1's 4,000 was the skeleton, not the job, and I should have said so.

### The fact that reframes everything

Measured in the clone today:

| Layer | Size |
|---|---:|
| Nautilus v2 published **Python** package | **49 files, 5,476 lines** — almost entirely `from nautilus_trader._libnautilus.<x> import *` |
| Nautilus **Rust** implementation | ~1.1M lines across 24 crates |
| Of which, **venue adapters** | the single largest block — 17 official integrations |
| Of which, **cTrader** | **zero** |

So: the wheel that exists is the kernel, and it is written in a language QMX does not use and cannot patch. The wheel that does not exist is the axle that connects it to your broker — and by the mature platforms' own measurements, the axle is the bigger job.

---

## (b) The real options

### Ruled out on licence, if QMX might ever be sold (D1)

Not judgement calls — verified licence text in the clones.

| Candidate | Licence (verified) | Effect |
|---|---|---|
| **backtrader** | GPL-3.0 (`reference/repos/backtrader/LICENSE`) | Contagious. Also **dead** — last `master` commit 2023-04-19, and it was killed by its own metaclass magic (`reference/studies/backtest-engines.md` §2.1). Design study only. |
| **lumibot** | GPL-3.0 (`reference/repos/lumibot/LICENSE`) | Contagious. Genuinely excellent and actively maintained (changelog 2026-08-05). Design study only. |
| **backtesting.py** | AGPL-3.0 | Strongest copyleft; network use triggers disclosure. Read it for API taste, import nothing. |
| **vectorbt** | Apache-2.0 **+ Commons Clause** | *"You may not sell products or services that are primarily this software."* Also structurally incapable of live trading. |
| **rqalpha** | **Custom, non-OSI** (`reference/repos/rqalpha/LICENSE`) | Non-commercial only; *any legal entity or organisation* is barred from any use without Ricequant's authorisation, and the text reaches derivative works that "reference or draw upon this software's functionality or source code". The best *interface* design of the three engines and legally untouchable. **Read `interface.py`, `core/executor.py`, `apis/api_abstract.py`, `matcher/base.py`; write your own.** |
| **mlfinlab** | Proprietary | The public repo is a stub — every inspected module body is `pass`. |

### The candidates the licence actually permits

Four, and they are more interesting than rev1 allowed.

| Candidate | Licence | What the licence costs you |
|---|---|---|
| **NautilusTrader** | LGPL-3.0 | Link and sell: **allowed**, with notice, and it must stay separately installable so a user could swap in their own build (a normal `pip install` satisfies this). Subclassing `Strategy` is explicitly "using an interface". **But any modification to Nautilus itself must be published under LGPL** — and in v2 "modification" means forking Rust. Trademark restrictions on the name (`TRADEMARK.md`); a CLA to upstream anything (`CLA.md`). |
| **QuantConnect LEAN** | Apache-2.0 | Nothing. The cleanest licence of any mature engine. |
| **Jesse** | **MIT** (`reference/repos/jesse/LICENSE`) | Nothing at all. Code could legally be copied wholesale. |
| **zipline-reloaded** | Apache-2.0 | Attribution and a NOTICE file. The only one of the three classic engines whose code could be legally adapted. |

Also inside the allowlist and worth naming: **hftbacktest** (MIT) for fill-model shapes, **QuantLib** (BSD-3) for the Calendar/DayCounter naming pattern.

### Option A — Build the minimal Python kernel

Write the domain-shaped code; wrap everything else. Copy shapes from Nautilus, LEAN, lumibot, Jesse, rqalpha, backtrader without copying their code. Legally adapt small, targeted pieces from the MIT/Apache candidates where they fit exactly (§(d) names two).

**What you get:** every interface designed around the three things QMX needs and nobody sells — cTrader, prop-firm rules, and a typed agent schema. Two lockfiles you control. No upstream release cadence. Every line readable and patchable by the agent factory that is your actual production method.

**What you give up:** the tested-ness of half a million lines of somebody else's kernel, and the speed.

### Option B — Adopt and wrap NautilusTrader

Take Nautilus as a dependency. Write a cTrader adapter against *their* contract. Wrap their `Strategy` with QMF's typed schema. Drive their `RiskEngine` from QMF's prop-firm rules.

**What you genuinely inherit, and I am not going to pretend otherwise:**

- The `TradingState` machine `qmf.bms` proposes — `{Active, Reducing, Halted}` with cancels always permitted and typed rejections — **already exists**, tested, with a public `set_trading_state()` a QMF-side FTMO evaluator could drive (`crates/risk/src/engine/mod.rs`).
- Backtest ≡ live as a *proved* property, plus a **third mode for free**: sandbox = live prices, simulated fills. That is exactly what a prop-firm challenge dry-run needs, and it is not in QMX's plan.
- Startup reconciliation — the largest risk-per-line item in the build table — done, including the ugly cases (venue history windows that start after the fill that opened your position).
- The order state machine, multi-currency margin accounting, 44 indicators, canonical run results with a blake3 digest and a `first_divergence()` helper.

**What adoption costs, beyond the licence:**

1. **You cannot read or patch the engine.** The Python surface is 5,476 lines of re-exports. Every bug below it is Rust. QMX's production method is a non-technical operator driving coding agents; a dependency whose failure modes are only reachable in a language the factory does not write is a dependency whose bugs are, for practical purposes, permanent. This is the argument rev1 missed and it is the strongest one in the brief.
2. **It is mid-migration.** `version.json` reads `v2.0.0rc3`; the latest published release is `v1.231.0 **Beta**` — still labelled Beta after ten years. `MIGRATION_V2.md` gives v1 "approximately three months of critical security backports" and no parity work. The rc's release notes delete the entire Cython package and rename the core callbacks (`on_quote_tick` → `on_quote`, and dozens more). Adopting now is adopting somebody else's migration.
3. **One node per process.** Verified in `docs/concepts/architecture.md:779-793`: *"Running multiple `LiveNode` or `BacktestNode` instances **concurrently** in the same process is not supported… For parallel execution or workload isolation, run each node in its own separate process."* The message bus, actor registry and channel senders live in thread-local storage. **In fairness this is not fatal** — Optuna+Ray sweeps run as separate processes anyway — but it is a real constraint on `qmf.experiment`'s design that you would inherit, not choose.
4. **No cTrader, and the adapter contract is Rust-shaped.** `ADAPTERS.md` lists 17 official adapters (Binance, Bybit, IB, Databento, Betfair, Polymarket…) and one *community* MT5 connector. Their conformance contract is a four-table rule set with a named shared baseline type per contract (`docs/developer_guide/adapters.md`). Writing to a contract you designed is meaningfully easier than satisfying a 17-adapter-deep one you cannot change.
5. **Three of QMF's nine rings are declared permanently out of scope.** `ROADMAP.md`, verbatim: out of scope are "UI dashboards or frontends", "distributed or massively parallel backtesting orchestration", and "**Integrated hyper-parameter optimization or built-in AI/ML tooling**". That is all of Ring 7 (`qmf.experiment`, `qmf.overfit`, `qmf.ledger` — the split-budget refusal machinery) and all of Ring 8 (`qmf.registry`, `qmf.spec`). Their entire risk config is `bypass: bool`, a submit rate limit and a max notional — nothing resembling a 00:00 CE(S)T daily anchor, a ratchet-lock, or a breach action. And note `bypass: bool`: a hard-coded escape hatch, precisely the thing `research/00` Ring 7 says must not exist.
6. **Two documented sharp edges you would be building on.** The cache is one object of 8,221 lines with **392 public methods** — safe in Rust because of the borrow checker, and their own architecture doc concedes that registry handles are `Rc<UnsafeCell<...>>` where "creating overlapping mutable references is undefined behavior" and same-actor re-entrancy is "a constraint of the current dispatch model, not a safe aliasing guarantee."

### Option B′ — Adopt Jesse (the option the licence most permits)

This deserves a fair hearing, because you like it, you know its creator, and **MIT means we could copy the whole thing.** It is the strongest possible form of "don't reinvent the wheel," and it fails on shape, not on law.

**For it:** one authored loop replayed at two speeds with a CI-enforced bit-identical equivalence test between them — the cleanest existence proof of "backtest is just replay" in any Python codebase (`jesse/modes/backtest_mode.py:536` vs `:1048`, and the invariant comment block at `:597-671`). Order *type* is inferred from price, never chosen by the author — a smaller, sharper version of QMX's own "the Trigger never names a quantity" rule. And its MCP layer plus `jesse/mcp/agent_rules.md` is the closest prior art in existence to QMX's actual problem: a written, versioned agent constitution with hard stops (p>0.10 on a rule-significance test is a **HARD STOP**, agents may never fabricate a result, never hand-edit config to route around a broken tool).

**Against it, decisively:**
- **Crypto is welded into the core.** `liquidation_price`, `bankruptcy_price`, `funding_rate`, `mark_price`, `exchange_type ∈ {spot, futures}` are baked into `jesse/models/Position.py`, not pushed behind a venue model. **There is no pip, lot, swap, rollover or weekend-gap concept anywhere in the codebase.** Porting it to forex-over-cTrader means editing core files, not writing an adapter.
- **The live half is not in the repo.** `jesse-live` is a separate, not-included project. This clone is backtest, optimize, paper-trading and research. So the parity claim you would be buying cannot be verified from what you can see, and the reconciliation-after-restart code — the highest-risk part of live trading — is not there to copy.
- **Sizing is advisory, not enforced.** `risk_to_qty`, `kelly_criterion` are helper functions a strategy *may* call; nothing requires it, and `agent_rules.md` compensates in prose. A strategy can still write `self.buy = 1000000, price`. That is the exact inverse of QMX's central safety claim, where an agent-authored component is structurally incapable of naming a quantity.
- **Infra footprint:** Postgres, Redis, Ray, FastAPI, Peewee — a hosted multi-user dashboard stack, not one VPS.

Verdict: **mine it hard, adopt none of it.** Its ergonomics, its two-speed equivalence test, and above all its agent constitution are worth copying. Its domain model is the wrong animal.

### Option B″ — LEAN

Apache-2.0, actively maintained, the best containment story anywhere (`Loader` + `Isolator`: RAM cap, 10-second instantiation limit, engine survives the algorithm's crash), and backtest-vs-live is literally a swap of handler class names in `config.json`. Licence-wise it is the cleanest mature engine on the table.

Against: it is a C#/.NET engine with Python via pythonnet, Docker as the reproducibility unit, a `QCAlgorithm` surface spanning eight partial classes, and no cTrader brokerage. For a non-technical solo operator whose agents write Python and whose deploy target is a small Linux VPS, adding a .NET build-and-container surface is a large, permanent operational tax paid to avoid writing ~1,500 lines of simulator. Fair to consider, easy to decline.

### Option C — Hybrid: adopt an engine for research-backtesting, build thin for live

**This is the option that sounds most reasonable and is the most dangerous one on the table.** I recommend against it more strongly than anything else here, and the evidence is the least ambiguous in the reference set.

Two engines means two sets of semantics, and the gap between them is where money disappears. Every healthy platform refused it deliberately, and the one that did not is dead:

- **Nautilus** makes three environments (backtest, sandbox, live) three *wirings of one kernel*, over one matching engine, behind one `ExecutionClient` trait.
- **Jesse** persists only 1-minute candles and generates every higher timeframe from them through the same function in backtest and live — and CI-tests that its fast and slow replays are bit-identical.
- **Lumibot** implements the backtest as a second implementation of the same `Broker` ABC and raises a hard error if you try to mix live and backtest strategies in one run.
- **qtpylib** bolted backtesting on as a flag inside a live-only class. `reference/studies/bot-frameworks.md` names the consequence: every new feature must be manually taught to check the flag, and a forgotten check means a "backtest" silently touches a live broker connection. Abandoned 2019-11-10.

A "research engine plus a thin live engine" is qtpylib's mistake with a nicer name: the branch moves from an `if` statement to a directory boundary, which makes it *harder* to notice, not easier. Every number you would ever show yourself would come from a code path that has never traded.

**There are two legitimate hybrids, and neither is that one.**

*Legitimate hybrid #1 — one semantics, two drivers, equivalence enforced by CI.* Jesse's step-simulator and skip-simulator. A reference step-by-step replay is the source of truth; an accelerated replay exists for research iteration speed and is **never shipped without a test asserting it produces the same numbers on fixture data**. Same semantics, two speeds. That is legitimate and cheap.

*Legitimate hybrid #2 — adopt other engines as CI oracles, not as runtime dependencies.* This is the constructive answer to "don't reinvent the wheel," and it is new in rev2. The plan already does it once — `talipp` as a test-only oracle for indicators, `purgedcv` as an oracle for the overfitting maths (`research/00` Rings 2 and 7). Extend it: run one fixture strategy through an Apache-2.0 engine and assert QMF's ledger agrees on a shared, simple case. You get somebody else's decade of correctness as a *test*, with none of their release cadence, licence surface, or migration schedule in your VPS lockfile.

*And the one hybrid that is just Option A stated honestly:* adopt aggressively for maths and storage — TA-Lib, DuckDB, Polars, Optuna, `arch`, `statsmodels`, `pyarrow`, `pandera`. By volume of code executing on your VPS, that is already mostly other people's work.

---

## (c) What each costs

**Unit.** A *factory-day* = one working day of you driving agent runs through the factory: a few queue cards authored, reviewed, merged. Not a developer-day, not eight hours of your attention. **Honest error bar: ±40%, and rev1's estimates proved to be biased low by roughly 3× on line count.** Read these as ranges, not numbers.

**The milestone for all three columns:** *a strategy spec runs against five years of EURUSD history and against a live cTrader demo account, through one kernel, with the FTMO daily-loss rule able to halt it.* Rings 7 and 8 (experiment, overfit, ledger, registry, spec) are excluded from every column because they cost the same in all of them.

| Work item | A: Build | B: Adopt Nautilus | C: Two engines |
|---|---:|---:|---:|
| Learn the platform, spike it, build it on Windows + Linux VPS (Rust toolchain, Python 3.12–3.14) | 0 | **4–6** | 4–6 |
| `qmf.core` + `qmf.model`, **including the order state machine** | **8–12** | 2–3 (map to theirs) | 8–12 |
| `qmf.runtime` kernel (dispatch, cache-then-publish, warm-up, loader with budgets) | **4–6** | 0 | 4–6 |
| `qmf.sim` (SimClock, SimBroker, FillModel, Ledger with financing line, metrics) — ~1,500 lines | **7–10** | 0 | 0 |
| Broker port + adapter conformance suite | **4–5** | 0 (theirs) | 4–5 |
| **Startup reconciliation** | **4–6** | 0 | 4–6 |
| **cTrader adapter** | 12–18 | **20–35** | 12–18 |
| Prop-firm rules (`qmf.bms`) | 6–10 | **5–8** (mechanism exists, policy does not) | 6–10 |
| Reconcile two engines' semantics, and keep them reconciled | 0 | 0 | **8–15, forever** |
| Unplanned v1→v2 migration tax | 0 | **3–8** | 3–8 |
| **Total to milestone** | **45–67** | **34–60** | **53–86** |

Three things about that table deserve to be said out loud.

**First: on raw factory-days, A and B remain within each other's error bars, and B may still be slightly cheaper.** I am not spinning this. Adoption genuinely saves the kernel, the simulator and reconciliation — 15–22 days of the build. What eats the saving back is one line: **the cTrader adapter costs more under adoption, not less.** Writing an adapter to a contract you designed and can change is easier than satisfying a 17-adapter-deep contract in a codebase mid-migration, whose official adapters are Rust and whose conformance rules name a specific shared baseline type per contract. I have costed that friction at +8 to +17 days and I think that is fair rather than conservative.

**Second: neither column includes the part that decides whether any of this works.** `reference/studies/backtest-engines.md` closes with the honest risk: *"The fill model is the whole ballgame and it is the one component with no good reference implementation for retail forex."* None of the three classic engines has variable spread, a weekend gap, or swap as a first-class P&L line — backtrader's overnight-interest hook (`comminfo.py:258-303`) is the only forex-shaped affordance in all three, and Nautilus's own bar-execution doc admits its intrabar path is *"a deterministic heuristic, not a reconstruction of the actual trade sequence."* **Adoption does not buy you the hard part. It buys you the cheap part.**

**Third: the test volume is the number nobody quotes.** 0.7×–1.6× production code in the execution and reconciliation paths. Any build estimate that does not carry that ratio is a build estimate for something that will lose money quietly.

### Long-term maintenance — where the options genuinely diverge

| | A: Build | B: Adopt Nautilus | C: Two engines |
|---|---|---|---|
| **Code you own** | ~7,000–11,000 lines of Python you wrote, plus tests | ~2,000 lines of wrapper + a cTrader adapter against a foreign contract | both, plus the seam |
| **Code you can debug** | all of it | **5,476 lines of re-exports; the rest is Rust** | mixed |
| **Who sets your schedule** | you | **them** | them and you, out of phase |
| **Steady state** | low — event-loop semantics do not change. 3–6 days/year, spiking when you add a venue | 4–8 days/year tracking releases, plus unplanned migrations | 10–18 days/year; the seam rots continuously |
| **Known scheduled pain** | none | **the v1→v2 migration is live right now**, and v2 is at rc while stable is still labelled Beta | inherits B's, twice |
| **If you must patch upstream** | n/a | your patch is LGPL, in Rust, and you maintain a fork | same |
| **Worst realistic case** | a kernel bug you must find yourself, with no upstream to ask | a breaking release lands while a prop-firm challenge is live, and the fix is below the Python line | a backtest number live can never reproduce, discovered after you traded on it |
| **Best realistic case** | boring, stable code you stop thinking about | a large tested core doing the boring parts for free | — |

The asymmetry: Option A's failure mode is *a bug you own and can fix on your own schedule*. Option B's failure mode is *unplanned work arriving on someone else's schedule, in a language your factory does not write*. For a solo operator with a funded challenge running, those are not the same size of problem even when they cost the same number of days.

One maintenance point specific to your setup: `research/00` Novel-7 wants two CI-enforced lockfiles, with `>50 MB or >30 dependencies` a hard CI failure on the trading side. Nautilus is a compiled PyO3 wheel with a Rust toolchain behind it. That constraint is buildable under A and becomes a negotiation under B. It is also the exact discipline whose absence killed qtpylib — and whose presence is why zipline-reloaded's 28 hard dependencies (including `bcolz-zipline`, *a fork created solely to keep an abandoned columnar format alive*) mean its maintenance history is dominated by re-pinning numpy.

---

## (d) Recommendation

### Build the kernel — smaller than rev1 implied it, staged, and with three specific purchases that buy down the risk. Keep Nautilus on a dated review trigger.

Concretely:

1. **Fix the fidelity taxonomy before writing any code.** Three levels — `bar_close`, `bar_intrabar`, `tick` — and the result key becomes `(confluence_id, split_id, data_fingerprint, qmf_version, venue_model_id, fidelity, metrics_set_id)`. This cannot be retrofitted: it becomes part of every stored result. It is a decision, not a build, and it is the cheapest thing in this brief.

2. **Build in two stages, and make stage 1 prove the claim.** Stage 1 is the ~2,500–4,000-line skeleton *plus* the adapter conformance suite, with `SimBroker` as implementation #1 — so "backtest ≡ live" is a CI failure when it breaks, not a discovery you make after trading on a bad number. Stage 2 is the expensive 80%: the order state machine, partial and contingent fills, margin, reconciliation. Do not let stage 1's speed set expectations for stage 2.

3. **Buy what is legally buyable.** Three purchases, all inside the allowlist:
   - **Adapt** zipline-reloaded's slippage-model contract and its registered-metric-set pattern (Apache-2.0, attribution and a NOTICE file). Its `process_order → (price, volume)` shape makes partial fills the default case, and its centrally-enforced `fill_price_worse_than_limit_price` check means a fill model *cannot* breach a limit price even by mistake — a defect rqalpha actually has.
   - **Copy** what fits from MIT sources: Jesse's inferred-order-type ergonomics, hftbacktest's fill-decision shape (touching a price is not filling at it; buys fill at the ask, sells at the bid, always).
   - **Use engines as CI oracles, not dependencies** — `talipp` for indicators, `purgedcv` for the overfitting maths, and one Apache-2.0 engine as a differential-test oracle on a shared fixture case.

4. **Amend D1.** The allowlist should read: Apache-2.0 / MIT / BSD / NCSA freely; **LGPL permitted for unmodified, separately-installed dependencies with notice** (this is what LGPL actually says, and `research/00` A.1 overstates it); AGPL, GPL, Commons Clause and non-OSI custom licences excluded. Make this correction whether or not you take the rest of the recommendation.

5. **Set a dated review trigger on D2, not a permanent answer.** Re-open when Nautilus ships **2.0 stable with a formal deprecation policy** *and* either a cTrader adapter exists or the community tier proves durable. Watch `version.json` and `RELEASES.md` monthly.

**Why, in one paragraph.** Not because the kernel is hard, and not because other people's code is untrustworthy — it is neither. It is that QMX's three most valuable components are the three no surveyed platform has, and two of which Nautilus has declared **permanently out of scope**: the cTrader connection (absent from every project surveyed), prop-firm rules as a first-class citizen (their entire risk config is three fields and a `bypass` flag), and a typed agent-authoring surface with a real evidence budget (`ROADMAP.md`: "integrated hyper-parameter optimization or built-in AI/ML tooling" — out of scope). Layer on the fact that Nautilus v2's Python surface is 5,476 lines of re-exports over 1.1 million lines of Rust, and adoption means your production method — a non-technical operator driving coding agents — is locked out of every bug below the wrapper. Paying somebody else's release schedule to save 15–22 factory-days on the *commodity* half, while the differentiated half stays yours anyway and the hardest single component (the forex fill model) has no reference implementation in any of them, is paying in the currency you cannot replace to save the one you can.

### The strongest honest argument against my recommendation

Here is the best version of your case. I think it is genuinely strong, and if you decide against me I will build it your way without relitigating.

**My estimates moved 3× in one revision, in the direction that flatters building.** Rev1 said 4,000 lines and 32–48 days. Rev2 says 7,000–11,000 lines and 45–67 days — on *the same evidence base*, just read more carefully. That is not a small correction; it is the signature error of someone who wants to build. If the true number moves another 3×, the kernel is a nine-month project, the prop-firm challenge never gets attempted, and the correct decision in hindsight was obviously to adopt. Adoption's costs are visible, bounded and front-loaded. Building's costs are invisible and discovered one at a time.

**Boring code somebody else already tested is free, and the tail is where trading engines actually break.** My estimate covers the kernel *working*. It does not cover it being *correct* under: a partial fill arriving after a cancel, a duplicate fill on reconnect, a VPS restart mid-position, a weekend gap inside an indicator warm-up, a timer firing while an order is in flight, a venue history window that starts *after* the fill that opened your position. Nautilus's own reconciliation code carries ~2.7k lines of production against ~8k of tests precisely because those cases are numerous, and each was found by somebody in production. My estimate assumes we find them by thinking. Mature platforms found them by bleeding.

**The specific thing you admired is the specific thing hardest to keep.** "Backtest runs on the same core as live" is not a shape you copy — it is a property you must preserve through every subsequent change. Even lumibot, which gets the strategy-facing polymorphism right, leaks `IS_BACKTESTING_BROKER` checks into 15+ call sites inside its own base `Broker` class. That is a production framework, with a test suite and outside contributors, admitting the property erodes under maintenance pressure. A solo operator with an agent factory and a prop-firm deadline is exactly the person who papers over it at 2am — and QMF's entire epistemic apparatus is worthless the moment backtest and live silently diverge.

**And two of my three original objections have been weakened by my own research.** The LGPL blocker is gone. The `TradingState` machine exists, tested, with a public setter a QMF-side FTMO evaluator could drive. Reconciliation exists. Sandbox mode — live prices, simulated fills — exists, and it is exactly the prop-firm dry-run mode QMX has not even planned. A fair reading is that the adopt case got *stronger* while I was writing, and the remaining objections are timing (fixable by waiting for 2.0 stable) and scope (fixable by wrapping, since the out-of-scope rings are additive layers on top, not modifications underneath).

**My honest response, so you can weigh it.** The tail-risk argument is the one that concerns me and I have no clean rebuttal — only two mitigations. The conformance suite is the first, and it is cheap: if `SimBroker` is implementation #1 and cTrader is #2 and both pass the same tests, backtest≡live becomes a machine problem instead of a discipline problem, for 4–5 days. The second is Nautilus's own cheapest idea: a canonical, identity-normalised, content-digested run result. Freeze one golden backtest's digest in CI and any accidental change to ordering, timers or fill logic is caught instantly, by a byte comparison, forever. Neither of those makes the tail disappear. Both make it visible, which is the difference between a backtest capability and backtest theatre.

### How to settle this without either of us being persuasive

Do not decide on argument. **Spend 3 factory-days measuring it**, then decide with a number in hand. On a throwaway branch:

1. Install Nautilus v2 rc in a fresh venv on the Linux VPS *and* on the Windows box. Log every hour lost to toolchain, Python-version and PyO3 build problems.
2. Load one year of Dukascopy EURUSD and run an EMA-cross backtest end to end.
3. Write a **stub** cTrader `ExecutionClient` + `DataClient` against their adapter contract — not working, just far enough to hit the first three things `docs/developer_guide/adapters.md` demands that cTrader cannot cleanly supply. This is the load-bearing unknown in the whole brief.
4. Drive `set_trading_state(Halted)` from a hardcoded FTMO daily-loss check.
5. **New in rev2, and the tie-breaker:** pick one deliberately awkward requirement — a forex swap charged as a P&L line, or a fill refused because the spread is too wide at 22:05 — and find where it would have to live. If it lives in a QMF-side wrapper, adoption survives. **If it lives in a Rust crate, adoption is over**, because that is a fork, in a language the factory does not write, published under LGPL.

**Decision rule, agreed in advance so neither of us can move the goalposts:** if all five land inside 3 factory-days and steps 3 and 5 felt like filling in a form, adoption is real, my recommendation is wrong, and I will write the wrapper plan. If day 3 goes to build errors, Python 3.14, a contract that wants order-book depth cTrader does not expose, or a swap line that has nowhere to live above the Rust boundary — then Option A is proven by measurement rather than by my opinion, and D2 closes for the year.

Three days is under 7% of the cheaper build estimate. It is the best-value spend in this brief, and it settles a question sitting under every decision downstream of it.

---

## Decision record — for the ledger

| Field | Value |
|---|---|
| **Decision** | D2 — build QMF's kernel, or adopt an existing engine |
| **Recommendation** | **Build**, staged: ~2,500–4,000-line skeleton + conformance suite first, then the expensive 80%. Wrap libraries for all non-domain work. Legally adapt targeted Apache-2.0/MIT pieces. Use rival engines as CI oracles, never as runtime dependencies. Keep Nautilus on a dated review trigger. |
| **Confidence** | Medium. On factory-days the options overlap inside the error bars; the recommendation rests on schedule ownership, on scope gaps Nautilus has declared permanent, and on the fact that its engine is unreadable to QMX's production method. |
| **Revised from rev1** | Build cost tripled on line count (4k → 7–11k) and rose ~40% on factory-days (32–48 → 45–67). Rev1's headline number was the skeleton, not the job. |
| **Strongest counter** | My estimates moved 3× in one revision, all in the flattering direction; the tail cases that break trading engines are found by bleeding, not by thinking; and Nautilus already has reconciliation, a trading-state machine, and a sandbox mode QMX has not planned. |
| **Blocked on** | D1 (licence posture) — **and D1 needs amending**: LGPL-3.0 is permitted for unmodified, separately-installed dependencies, contrary to `research/00` A.1. |
| **Cheapest way to overturn** | The 5-step / 3-factory-day spike above, with its decision rule fixed in advance. Step 5 is the tie-breaker. |
| **Revisit** | Monthly check of `nautilus_trader` `version.json` and `RELEASES.md`; hard re-open on 2.0 stable with a formal deprecation policy. |

---

## Evidence index

**Studies read in full:** `reference/studies/nautilus-trader.md` · `reference/studies/backtest-engines.md` · `reference/studies/jesse.md` · `reference/studies/bot-frameworks.md` · `reference/studies/platform-patterns.md` · `reference/studies-wave2/fill-simulation.md` · `reference/studies-wave2/macro-backtester.md`

**Research read in full:** `research/01-architecture-references.md` · `research/00-qmf-synthesis-module-map.md`

**Measured directly from the clones on 2026-08-17 (facts not in any study, or sharpening one):**
- `reference/repos/nautilus_trader/python/` — `find nautilus_trader -name "*.py" | wc -l` → **49**; `… -exec cat {} + | wc -l` → **5,476**. Sampled `adapters/{architect_ax,betfair,binance}/__init__.py`: every one is a re-export of `nautilus_trader._libnautilus.<area>`.
- `reference/repos/nautilus_trader/version.json` → `v2.0.0rc3`.
- `reference/repos/nautilus_trader/docs/concepts/architecture.md:779-793` — multiple `LiveNode`/`BacktestNode` in one process "is not supported"; "run each node in its own separate process."
- `reference/repos/nautilus_trader/docs/developer_guide/adapters.md:952-954,1163` — the `NotSent` / `VenueRejected` / `Ambiguous` outcome table, and the rule that an `Ambiguous` classification **never** emits a terminal event by itself.
- `reference/repos/jesse/LICENSE` — MIT, Copyright (c) 2020 Jesse.Trade.
- `reference/repos/zipline-reloaded/LICENSE` — Apache License 2.0.
- Licence confirmations carried forward from rev1 and re-checked against the studies: `backtrader` GPL-3.0, `lumibot` GPL-3.0, `rqalpha` custom non-OSI, `nautilus_trader` LGPL-3.0.

**Not verified, flagged honestly:**
- Whether cTrader's Open API can satisfy Nautilus's adapter contract without patching a Rust crate. **This is the load-bearing unknown in the entire brief**, and steps 3 and 5 of the spike exist to answer it.
- Whether `jesse-live` is open, paid or closed. Not in the clone, so Jesse's backtest≡live parity claim is proven for the backtest half only.
- LEAN was assessed from `research/01` §2 and not re-measured in a clone for this revision.
