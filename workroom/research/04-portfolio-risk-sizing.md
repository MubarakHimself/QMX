# 04 — Portfolio Management: Risk Management + Position Sizing (Prior Art)

Research date: **2026-08-17**. Every load-bearing claim is cited to a primary source (repo file, official doc, or paper). Anything I could not verify is marked **UNVERIFIED**.

Scope: position-sizing methods and their real implementations; the maintained state of `riskfolio-lib` / `PyPortfolioOpt` / `skfolio`; drawdown-based runtime controls; prop-firm constraint systems and whether open source models them; and — the central question — **how LEAN, NautilusTrader, pysystemtrade and Freqtrade separate risk/sizing AUTHORITY from strategy logic**, as prior art for QMX's Books + Book Management System (BMS).

---

## In plain words

1. Every serious trading framework I examined puts money rules **outside** the strategy. The strategy says *what* it likes; something above it decides *how much*, and something above that can say *no*.
2. LEAN (QuantConnect) does it in four stages: an Alpha suggests, a Portfolio Construction model turns suggestions into target position sizes, a Risk Management model may shrink or zero those targets, and only then does an Execution model place orders. Risk models are explicitly forbidden from placing orders themselves.
3. NautilusTrader does it differently: a single system-wide Risk Engine sits on the order path. Every order from every strategy passes through it, and it can deny orders, throttle order rate, or put the whole system into HALTED or REDUCING mode.
4. pysystemtrade (Rob Carver) is the closest match to what QMX wants: strategies emit a dimensionless "forecast" number, never a position. The framework alone converts forecast → contracts using a volatility target, and a portfolio-wide "risk overlay" can scale every position down at once.
5. Freqtrade has "Protections" — a declarative list of rules (max drawdown, stop-loss guard, cooldown) that lock trading for a period. Good pattern, but it only looks at *closed* trades, which makes it useless for prop-firm rules.
6. On sizing: fixed-fractional (risk X% per trade with a stop) is what live engines actually ship. Kelly is mathematically optimal for long-run growth but is dangerously sensitive to your estimate of the average return — the literature says errors in the mean matter roughly 100× more than errors in correlations for a full-Kelly bettor. Half-Kelly or less is the practical answer.
7. Volatility targeting (scale positions so risk, not notional, is constant) has strong published evidence for reducing extreme losses across all asset classes — but weaker evidence that it adds return.
8. The three big Python portfolio-optimization libraries (Riskfolio-Lib, PyPortfolioOpt, skfolio) are all alive in 2026, but they solve a different problem: splitting capital across many assets. QMF's first problem is one account, one broker, a handful of FX pairs. They are research tools, not runtime tools.
9. Prop firms define three separate constraints: a **daily** loss cap, a **total** loss cap, and sometimes a **trailing** cap. The details differ wildly and are where accounts die: FTMO measures against the balance at midnight Central European Time; Topstep trails on end-of-day balance; Apex trails in real time and counts *unrealized* profit, so an open winner that reverses can kill the account.
10. Every one of those firms checks **equity including floating P&L**, in real time. A rule engine that only looks at closed trades will fail the account.
11. There is essentially **no open-source library** that models prop-firm rules properly. The GitHub landscape is MetaTrader Expert Advisors and one 0-star Monte Carlo simulator. This is genuinely greenfield for QMX.
12. The recommendation: copy pysystemtrade's authority split (strategies emit intent, Book owns sizing), copy Nautilus's single mandatory gate on the order path, copy Freqtrade's declarative composable rules, and build the prop-firm rule model from scratch against the six axes listed in the Findings.
13. One warning that recurs everywhere: the drawdown state (peak equity, day-anchor balance) must **survive a restart**. LEAN's built-in drawdown models keep it in memory only, and re-arm themselves immediately after a breach with no cooldown. On a VPS that reboots, that is an account-ending bug.

---

## Findings

### 1. Authority separation — the core question

#### 1.1 LEAN / QuantConnect — a pipeline of models, risk sits between construction and execution

LEAN's Algorithm Framework pipeline is: **Universe → Alpha → Portfolio Construction → Risk Management → Execution**.

- Portfolio Construction produces `PortfolioTarget` objects — "the number of units of an asset to hold" — via `CreateTargets(QCAlgorithm algorithm, Insight[] insights)`. It does **not** execute. ([docs](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/portfolio-construction/key-concepts))
- Risk Management implements `manage_risk(self, algorithm, targets) -> List[PortfolioTarget]`, and per the docs *"The method should only return the adjusted targets, not all of targets."* Multiple risk models chain: *"The risk-adjusted targets from the first Risk Management model are passed to the second Risk Management model."* ([docs](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/risk-management/key-concepts))
- The authority boundary was a deliberate, breaking refactor. LEAN PR #1792: *"Refactors `IRiskManagementModel.ManageRisk` to return `IEnumerable<IPortfolioTarget>`. This targets are used as overrides and piped into the execution model with the targets from the construction model. … **Precludes risk models from submitting orders and leaves that responsibility to the execution model.**"* ([PR #1792](https://github.com/quantconnect/lean/issues/1792))

Composition semantics, verbatim from `Algorithm/Risk/CompositeRiskManagementModel.py` ([source](https://github.com/QuantConnect/Lean/blob/master/Algorithm/Risk/CompositeRiskManagementModel.py)):

```python
def manage_risk(self, algorithm, targets):
    for model in self.risk_management_models:
        risk_adjusted = model.manage_risk(algorithm, targets)
        # produce a distinct set of new targets giving preference to newer targets
        symbols = [x.symbol for x in risk_adjusted]
        for target in targets:
            if target.symbol not in symbols:
                risk_adjusted.append(target)
        targets = risk_adjusted
    return targets
```

So composition is **last-writer-wins per symbol**, chained in registration order. Note this was originally buggy — LEAN PR #2605: *"I noticed a bug in `CompositeRiskManagementModel.ManageRisk`, whereby the last risk model to run was the only one that actually mattered."* ([PR #2605](https://github.com/quantconnect/lean/issues/2605)). Registration is via `QCAlgorithm.AddRiskManagement` ([PR #3064](https://github.com/quantconnect/lean/issues/3064)).

Built-in risk models (`Algorithm.Framework/Risk/`, both `.cs` and `.py` for each): `MaximumDrawdownPercentPerSecurity`, `MaximumDrawdownPercentPortfolio`, `MaximumSectorExposureRiskManagementModel`, `MaximumUnrealizedProfitPercentPerSecurity`, `TrailingStopRiskManagementModel`, plus `NullRiskManagementModel` and `CompositeRiskManagementModel` in `Algorithm/Risk/`. ([dir listing](https://github.com/QuantConnect/Lean/tree/master/Algorithm.Framework/Risk), [supported models doc](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/risk-management/supported-models))

Portfolio Construction models available: `EqualWeighting`, `InsightWeighting`, `ConfidenceWeighted`, `Accumulative`, `MeanVarianceOptimization`, `BlackLittermanOptimization`, `RiskParity`, `SectorWeighting`, `MeanReversion`, `AlphaStreams`, plus pluggable optimizers (`MaximumSharpeRatioPortfolioOptimizer`, `MinimumVariancePortfolioOptimizer`, `RiskParityPortfolioOptimizer`, `UnconstrainedMeanVariancePortfolioOptimizer`). ([dir listing](https://github.com/QuantConnect/Lean/tree/master/Algorithm.Framework/Portfolio))

**Limits of LEAN's model for QMX's purpose:** a risk model can only rewrite target *quantities*. It cannot veto an order, throttle rate, impose a cooldown, or express "flat and blocked until 00:00 CET tomorrow." There is no session/day concept in the interface. State lives in Python instance attributes with no persistence contract.

Repo state: `QuantConnect/Lean`, Apache-2.0, 21,240 stars, last push **2026-08-14** — actively maintained.

#### 1.2 NautilusTrader — a single mandatory gate on the order path

Nautilus does not chain risk models; it has one `RiskEngine`, a component of every system (backtest, sandbox, live). Order flow ([docs](https://nautilustrader.io/docs/latest/concepts/execution/)):

```
Strategy -> OrderEmulator | ExecutionAlgorithm | RiskEngine
ExecutionAlgorithm -> RiskEngine -> ExecutionEngine -> ExecutionClient
```

*"It sits on the submit and modify path… Cancel and query commands route directly to other execution components and do not pass through the `RiskEngine`."*

Checks performed unless bypassed (verbatim list from the docs): price/trigger-price precision; positive prices unless the instrument allows negatives; quantity precision and min/max base-quantity bounds; GTD orders not already expired; `reduce_only` orders do not increase the referenced position; engine-level `max_notional_per_order` and instrument `max_notional`; cash-account balance impact for non-margin accounts; submit and modify rate limits; trading-state restrictions.

`TradingState` enum:
- `ACTIVE` — submit and modify operate normally
- `HALTED` — new submit and modify are denied; **cancels still pass through**
- `REDUCING` — cancels allowed; only submits/modifies that do not increase exposure are accepted

Failures emit `OrderDenied` with a standardized machine-readable reason code. Relevant codes include `TRADING_HALTED`, `TRADING_STATE_REDUCING`, `RATE_LIMIT_EXCEEDED`, `NOTIONAL_EXCEEDS_MAX_PER_ORDER`, `CUM_NOTIONAL_EXCEEDS_FREE_BALANCE`, `MARGIN_EXCEEDS_FREE_BALANCE`, `REDUCE_ONLY_WOULD_INCREASE_POSITION`. The docs state these codes *"are the source of truth for locally denied orders."*

Full config surface, verbatim from `nautilus_trader/risk/config.py` ([source](https://github.com/nautechsystems/nautilus_trader/blob/master/nautilus_trader/risk/config.py)):

```python
class RiskEngineConfig(NautilusConfig, frozen=True):
    bypass: bool = False                          # bypasses ALL pre-trade checks and rate limits
    max_order_submit_rate: str = "100/00:00:01"
    max_order_modify_rate: str = "100/00:00:01"
    max_notional_per_order: dict[str, int] = {}   # per instrument ID
    debug: bool = False
```

That is the **entire** built-in risk surface. Runtime mutators exist on the engine: `set_trading_state()`, `set_max_notional_per_order()`, plus `throttled_submit` / `throttled_modify_order` throttlers ([Rust API docs, nautilus-risk 0.61.0, published 2026-08-02](https://docs.rs/nautilus-risk/0.61.0/nautilus_risk/engine/struct.RiskEngine.html)).

**Critical gap, confirmed by an open issue dated July 2026:** there is no portfolio-level gross-exposure cap. Issue #4419: *"RiskEngineConfig supports max_notional_per_order and margin/free-balance checks, but I could not find a built-in config for total portfolio gross exposure across all active strategies and instruments… would this need a custom RiskEngine / portfolio-level limiter?"* ([issue #4419](https://github.com/nautechsystems/nautilus_trader/issues/4419)). No drawdown control, no daily loss cap, no session concept either.

Nautilus's only built-in sizing helper is fixed-risk ([Rust docs](https://docs.rs/nautilus-risk/0.61.0/nautilus_risk/sizing/fn.calculate_fixed_risk_position_size.html)):

```rust
pub fn calculate_fixed_risk_position_size(
    instrument: &InstrumentAny,
    entry: Price,
    stop_loss: Price,
    equity: Money,
    risk: Decimal,
    commission_rate: Decimal,
    exchange_rate: Decimal,
    hard_limit: Option<Decimal>,
    unit_batch_size: Decimal,
    units: usize,
) -> CorrectnessResult<Quantity>
```

Note it takes `hard_limit`, `unit_batch_size` and `exchange_rate` — real-world concerns (broker lot rounding, cross-currency accounts) that a naive `risk_pct * equity / stop_distance` formula misses. This is the single most directly reusable design in the whole survey for a forex Book.

The `Portfolio` component supplies the valuation primitives a drawdown rule needs: `equity(venue, account_id)`, `mark_values()`, `build_snapshot(account_id)`, `snapshots(account_id)`, and — since v2 — `PortfolioConfig.equity_curve=true` (default) which records a mark-to-market snapshot *"at every UTC midnight even while the account is flat"* ([Portfolio docs](https://nautilustrader.io/docs/latest/concepts/portfolio/)). Margin-account equity is `balances_total + Σ unrealized_pnl(open positions)` — i.e. floating P&L included, which is what prop firms measure. **But the snapshot boundary is UTC midnight, and FTMO anchors at 00:00 CE(S)T while Topstep uses 3:10 PM CT.** That mismatch has to be handled explicitly.

Repo state: `nautechsystems/nautilus_trader`, LGPL-3.0, 25,657 stars, last push **2026-08-17** (today), latest release **v1.231.0 on 2026-08-02** — very actively maintained.

#### 1.3 pysystemtrade — the closest prior art to QMX's Books + BMS

Rob Carver's pysystemtrade is the only framework here where **strategy code is structurally incapable of expressing a position size**. Its pipeline of stages ([docs/backtesting.md](https://github.com/robcarver17/pysystemtrade/blob/master/docs/backtesting.md)):

1. `RawData` (`system.rawdata`)
2. `Rules` (`system.rules`) — trading rules that output **forecasts**, not positions
3. `ForecastScaleCap` (`system.forecastScaleCap`) — scales forecasts to a common scale and caps them (`forecast_cap: 20.0`)
4. `ForecastCombine` (`system.combForecast`) — weights and combines forecasts, applies a forecast diversification multiplier
5. `PositionSizing` (`system.positionSize`) — **the only place a forecast becomes a position**
6. `Portfolios` (`system.portfolio`) — instrument weights and instrument diversification multiplier, buffering
7. `Account` (`system.accounts`)

The sizing stage is pure volatility targeting. Config:

```yaml
percentage_vol_target: 16.0
notional_trading_capital: 1000000
base_currency: "USD"
```

and the method chain (from the stage reference table in the same doc): `get_daily_cash_vol_target()` → dict of `base_currency, percentage_vol_target, notional_trading_capital, annual_cash_vol_target, daily_cash_vol_target`; `get_block_value()` = "value of a 1% move in the price"; `get_instrument_currency_vol()` = "daily volatility in the currency of the instrument"; `get_instrument_value_vol()` = "daily volatility in the currency of the trading account"; `get_average_position_at_subsystem_level()` = "ratio of target volatility vs volatility of instrument"; `get_subsystem_position()` = "position if we put our entire trading capital into one instrument."

Portfolio stage config:

```yaml
instrument_weights:
  EDOLLAR: 0.5
  US10: 0.5
instrument_div_multiplier: 1.2
```

Buffering / position inertia is a first-class concept (reduces churn, an underrated live-trading cost control):

```yaml
buffer_trade_to_edge: True
buffer_method: forecast      # or: position
buffer_size: 0.10
```

**The risk overlay is the single most transferable idea for QMX's BMS.** From `systems/risk_overlay.py` ([source](https://github.com/robcarver17/pysystemtrade/blob/master/systems/risk_overlay.py)):

> *"The risk overlay calculates a risk position multiplier, which is between 0 and 1. When this multiplier is one we make no changes to the positions calculated by our system. If it was 0.5, then we'd reduce our positions by half… So the overlay acts across the entire portfolio, reducing risk proportionally on all positions at the same time. The risk overlay has three components, designed to deal with the following issues: Expected risk that is too high; Weird correlation shocks combined with extreme positions; Jumpy volatility (non stationary and non Gaussian vol). Each component calculates it's own risk multiplier, and then we take the lowest (most conservative) value."*

Four multipliers are computed and `min()`-ed, labelled `["jump vol", "normal", "shock correlation", "leverage"]`, driven by config keys `max_risk_fraction_normal_risk`, `max_risk_fraction_stdev_risk`, `max_risk_limit_sum_abs_risk`, `max_risk_leverage`. The first three are expressed as *fractions of `percentage_vol_target`*, so limits are stated relative to the account's own risk budget rather than in absolute currency.

Two caveats: (a) the overlay is **disabled by default** — the block is commented out in `sysdata/config/defaults.yaml` with placeholder values of `99999` ([source](https://github.com/robcarver17/pysystemtrade/blob/master/sysdata/config/defaults.yaml)); (b) it is *forward-looking* — it constrains **expected** risk from volatility and correlation estimates. It is not a realized-drawdown kill switch and will not save a prop account.

Repo state: `robcarver17/pysystemtrade`, GPL-3.0, 3,439 stars, last push **2026-07-18** — maintained. GPL-3.0 means **do not copy code**; copy the design.

#### 1.4 Freqtrade — declarative, composable, sequenced Protections

Freqtrade's `Protections` are the best ergonomic model for a non-technical operator: a list of dicts with a `method` key, *"evaluated in the sequence they are defined"* ([docs](https://www.freqtrade.io/en/stable/plugins/)).

- Shared parameters across all protections: `method`, `stop_duration` / `stop_duration_candles`, `lookback_period` / `lookback_period_candles`, `trade_limit`, `unlock_at` ("HH:MM", 24-hour).
- `StoplossGuard` — stop trading if `trade_limit` stop-losses occurred within `lookback_period`. Flags: `only_per_pair`, `only_per_side`, `required_profit`.
- `MaxDrawdown` — two modes: `calculation_mode: "ratios"` (legacy, from cumulative trade profit ratios) and `calculation_mode: "equity"` (*"Standard peak-to-trough drawdown on the account equity curve, using starting balance and cumulative absolute profit"*). Docs recommend `"equity"` for new setups. Triggers when drawdown exceeds `max_allowed_drawdown`.
- `LowProfitPairs`, `CooldownPeriod` — per-pair locks.

**The disqualifying limitation for prop-firm use:** *"The MaxDrawdown protection evaluates trades that **closed** within the current lookback_period."* Prop firms breach on floating equity. A closed-trade-only rule engine cannot model them.

Repo state: `freqtrade/freqtrade`, GPL-3.0, 53,370 stars, last push **2026-08-17** (today) — very actively maintained.

#### 1.5 Summary of the authority patterns

| Framework | Where authority lives | Can it veto? | Can it throttle? | Portfolio-wide scalar? | Session/day concept? | Drawdown kill-switch? |
|---|---|---|---|---|---|---|
| LEAN | `RiskManagementModel` chain between construction and execution | No (only rewrites target qty) | No | No (per-symbol targets) | No | Yes (built-in models) |
| NautilusTrader | One system-wide `RiskEngine` on the submit/modify path | **Yes** (`OrderDenied`) | **Yes** (throttlers) | No (issue #4419) | No | No |
| pysystemtrade | `PositionSizing` stage owns sizing; `risk_overlay` scales portfolio | No | No | **Yes** (min of 4 multipliers, [0,1]) | No | No (forward-looking only) |
| Freqtrade | `Protections` list, sequenced, `PairLock` | Yes (locks) | Via cooldowns | No | Partial (`unlock_at`) | Yes, but **closed trades only** |

**No single framework has all six columns.** QMF's Book + BMS design would be the first to combine them, which is the strongest argument that building it is worth the effort rather than adopting one wholesale.

---

### 2. Position sizing methods

#### 2.1 Fixed fractional / fixed-risk-per-trade

This is what live engines actually ship. Nautilus's signature (§1.2) is the reference implementation: it takes `entry`, `stop_loss`, `equity`, `risk` (a `Decimal` fraction), and then the three things naive formulas forget — `commission_rate`, `exchange_rate` (cross-currency account), and `hard_limit` / `unit_batch_size` (broker lot granularity). LEAN has no equivalent built-in; sizing there is expressed as a portfolio *weight* via `PortfolioTarget.Percent(algorithm, symbol, 0.1)` ([docs](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/portfolio-construction/key-concepts)), which is margin-accounts-only and stop-agnostic.

#### 2.2 Kelly and fractional Kelly

Primary source used throughout: Ziemba & MacLean, *"Using the Kelly Criterion for Investing"*, Ch. 1 of *Stochastic Optimization Methods in Finance and Energy*, Springer 2011 ([full text PDF](https://webhomes.maths.ed.ac.uk/mckinnon/blackouts/StochOptFinanceAndEnergySpringer/Chap1_KellyZiemba.pdf)).

The formula: for a win payoff `+B`, `f* = (Bp − q)/B = edge/odds`. For even money, `f* = p − q`.

Breiman's three properties (asymptotic, discrete time, intertemporally independent assets), quoted from the chapter:
- **Property 1** — against any essentially different strategy, `W_N(λ*)/W_N(λ) → ∞`.
- **Property 2** — *"The expected time to reach a preassigned goal A is asymptotically least as A increases with a strategy maximizing E log W_N."*
- **Property 3** — a fixed-fraction strategy maximizes `E log W_N` and is independent of `N` (myopic).

The dangers, in the authors' own words:
- **Essentially zero risk aversion.** *"For log, R_A = 1/w which is close to zero for non-bankrupt investors, so we will argue that log is the most risky utility function one should ever consider."*
- **Bets are enormous.** *"if p = 0.99 and q = 0.01 then f* = 0.98 or 98% of one's current wealth."* In a worked real example the optimal Kelly bet was 97.5% of wealth; the practitioner actually invested 10%.
- **Never overbet.** *"Since the growth rate and the security are both decreasing for f > f*, it follows that it is never advisable to wager more than f*."* Positive-power utilities like `w^0.5` are *"growth-security dominated"*. And: *"the investor who wagers exactly twice this amount has a growth rate of zero plus the risk-free rate of interest."*
- **Estimation error is the killer.** *"Chopra and Ziemba (1993) show that in typical investment modeling, errors in the means average about 20 times in importance in objective value than errors in co-variances with errors in variances about double the co-variance errors… the relative importance of the errors is risk aversion dependent with the errors compounding more and more for lower risk aversion investors and **for the extreme log investors with essentially zero risk aversion the errors are worth about 100:3:1. So log investors must estimate means well if they are to survive.**"* (Original: Chopra & Ziemba, *"The Effect of Errors in Means, Variances, and Covariances on Optimal Portfolio Choice"*, JPM 19(2), 1993, 6–11, [journal page](https://jpm.pm-research.com/content/19/2/6).)
- **Correlations break exactly when you need them.** *"when times move suddenly from normal to bad the correlations/co-variances approach 1 and it is hard to predict the transition."*

Fractional Kelly: `f = 1/(1 − α) = 1/R_R` where `R_R` is relative risk aversion — *"exactly correct for lognormal assets and approximately correct otherwise… Thorp (2008) shows that this approximation can be very poor."* Half-Kelly corresponds to `α = −1`, quarter-Kelly to `α = −3`. The authors' verdict: *"in practice, half Kelly is a toned down version of full Kelly that provides a lot more security to compensate for its loss in long-term growth."*

The simulation (Table 1.3, 3000 scenarios, 40 yearly periods, US equities vs T-bills 1926–2001) is the number to remember: at 1.57×Kelly the minimum final wealth over 3000 paths was **−102,513,723** from an initial wealth normalized such that 0.26×Kelly's minimum was **+2,367.92**. The conclusion: *"For the most aggressive strategy (1.57 k), it is possible to lose 10,000 times the initial wealth."*

The chapter's closing bullets, verbatim, are worth encoding as doc constraints:
> *"The wealth accumulated from the full Kelly strategy does not stochastically dominate fractional Kelly wealth. The downside is often much more favorable with a fraction less than 1."*
> *"In cases of large uncertainty, from either intrinsic volatility or estimation error, security is gained by reducing the Kelly investment fraction."*
> *"no matter how favorable the investment opportunities are or how long the finite horizon is, a sequence of bad scenarios can lead to very poor final wealth outcomes, with a loss of most of the investor's initial capital."*

Note also MacLean, Sanegre, Zhao & Ziemba (2004), *"Capital growth with security"*, JEDC 28(4), 937–954 — cited in the chapter as *"a strategy to reduce the Kelly fraction to stay above a prespecified wealth path with high probability and to be penalized for being below the path."* That is precisely the mathematical shape of a prop-firm trailing drawdown constraint. **I did not read that paper directly — UNVERIFIED beyond the citation.**

Modern robust variants exist if QMF ever wants them: Wasserstein-Kelly DRO ([arXiv:2302.13979](https://arxiv.org/abs/2302.13979)), risk-constrained Kelly with an explicit drawdown-probability bound yielding a convex program ([arXiv:1603.06183](https://arxiv.org/abs/1603.06183)), distributionally-robust Kelly ([arXiv:1812.10371](https://arxiv.org/abs/1812.10371)). None have a production-grade maintained implementation I could find.

#### 2.3 Volatility targeting

Implementation reference is pysystemtrade (§1.3): annualized `percentage_vol_target: 16.0`, converted to an annual then daily cash vol target, divided by the instrument's value volatility to get a position.

Evidence, and the important nuance — **two different claims that are often conflated**:

- **Volatility targeting (constant risk exposure)** — Harvey, Hoyle, Korgaonkar, Rattray, Sargaison & van Hemert, *"The Impact of Volatility Targeting"*, Journal of Portfolio Management 45(1), Fall 2018, 14–33 ([SSRN 3175538](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538), [JPM](https://jpm.pm-research.com/content/45/1/14.abstract)). Abstract findings: the Sharpe-ratio improvement *"only holds for 'risk assets', such as equity and credit, and this is linked to the so-called leverage effect… In contrast, for bonds, currencies, and commodities the impact of volatility targeting on the Sharpe ratio is negligible."* But — and this is the part that matters for QMX — *"the impact of volatility targeting goes beyond the Sharpe ratio: **it reduces the likelihood of extreme returns, across all asset classes**. Particularly relevant for investors, 'left-tail' events tend to be less severe, as they typically occur at times of elevated volatility, when a target-volatility portfolio has a relatively small notional exposure."* Note: **currencies are explicitly in the "no Sharpe benefit" bucket.** QMX is forex-first. Vol targeting is justified there as a *tail-risk and drawdown-shape* control, not as an alpha source.

- **Volatility *management* (timing exposure on lagged vol to earn alpha)** — Cederburg, O'Doherty, Wang & Yan, *"On the performance of volatility-managed portfolios"*, Journal of Financial Economics 138(1), 2020, 95–117 ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X), [SSRN 3357038](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3357038)). Across 103 equity strategies, vol-managed portfolios *"do not systematically outperform their corresponding unmanaged portfolios"*; the implied trading strategies *"are not implementable in real time"*, and out-of-sample versions *"generally earn lower certainty equivalent returns and Sharpe ratios"*, attributed to *"structural instability in the underlying spanning regressions."*

**Conclusion for QMF:** volatility targeting is a *risk-normalization* primitive, not an alpha model. Adopt it for tail control and for making Book-level risk budgets comparable across strategies. Do not let anyone (including an LLM authoring a strategy) sell it as a return enhancer.

---

### 3. Portfolio-optimization libraries — maintenance state as of 2026-08-17

All figures pulled live from the GitHub and PyPI APIs today.

| Library | Latest version (PyPI) | Last commit / push | Stars | Open issues | License | Verdict |
|---|---|---|---|---|---|---|
| **skfolio** | 0.20.2 — **2026-08-13** | 2026-08-14 | 2,169 | 25 | BSD-3-Clause | **Actively maintained**, fastest release cadence of the three (v0.18 → v0.20.2 in four months) |
| **Riskfolio-Lib** | 7.3.0 — **2026-05-31** | 2026-06-22 | 4,445 | 5 | BSD-3-Clause | Maintained but single-maintainer; **no GitHub Releases at all**; last 3 commits are doc-only |
| **PyPortfolioOpt** | 1.6.0 — **2026-02-26** | 2026-07-07 | 5,966 | **112** | MIT | Revived after a long stall; ownership transferred |

Detail:

- **skfolio** ([skfolio.org](https://skfolio.org/), [repo](https://github.com/skfolio/skfolio)). Pure scikit-learn API: `model.fit(X_train)` → `model.weights_`; `model.predict(X_test)` → a `Portfolio` object exposing `.annualized_sharpe_ratio`, `.calmar_ratio`, `.summary()`. Composes with `Pipeline`, `GridSearchCV`, `RandomizedSearchCV`. Ships **CombinatorialPurgedCV** and **WalkForward** cross-validators — genuinely rare and correct for financial time series. Risk measures include the whole drawdown family: **CDaR, EDaR, Maximum Drawdown, Average Drawdown, Drawdown at Risk, Ulcer Index**, alongside CVaR/EVaR/semi-variance. Optimization features include turnover constraints, transaction costs, cardinality constraints, L1/L2 regularization. Paper: Nicolini, Manzi & Delatte, *"skfolio: Portfolio Optimization in Python"*, [arXiv:2507.04176](https://arxiv.org/abs/2507.04176) (submitted 2025-07-05). **Commercial backing note:** the homepage states *"skfolio is backed by [Skfolio Labs](https://skfoliolabs.com/), which provides enterprise support and SLAs for institutions."* That is a sustainability plus and an open-core risk to watch.
- **Riskfolio-Lib** ([repo](https://github.com/dcajasn/Riskfolio-Lib)). Advertises **26 convex risk measures** for mean-risk, 37 for hierarchical clustering, 22 for risk parity; drawdown family = Average Drawdown, Ulcer Index, CDaR, EDaR, RLDaR, Maximum Drawdown. Requires Python ≥3.10. Bus-factor of one; recent commit activity is documentation only.
- **PyPortfolioOpt**. The canonical repo path is now **`PyPortfolio/PyPortfolioOpt`** — `robertmartin8/PyPortfolioOpt` returns the same object via the GitHub API, i.e. it was transferred to an org. The release gap is stark: the previous GitHub release before v1.6.0 (2026-02-26) was **v1.4.1 on 2021-05-06**. The maintenance vacuum is documented in issue #587 (opened 2024-03-12, now closed): *"I have been trying to contact the maintainers of this package for a while… Tuan Tran is mentioned as 'primary maintainer' on the readme, but does not seem to own any relevant assets, nor have they made any GitHub contributions in the last year… Requests to put me in touch to maintainers of pyportfolioopt have now remained unanswered for more than a month."* ([issue #587](https://github.com/PyPortfolio/PyPortfolioOpt/issues/587)). 112 open issues is a lot for a library this size.

**Relevance verdict for QMF:** all three solve *N-asset weight allocation from a return/covariance matrix*. QMX's first-order problem is one cTrader account, a handful of FX pairs, per-trade stops, and hard prop-firm constraints. None of these libraries model a stop-loss, a lot size, a daily loss cap, or a session. Use skfolio **offline, in research**, for cross-validation machinery and drawdown-measure definitions; do not put any of them on the live path.

Also worth noting: `skfolio`'s own acknowledgements credit *"PyPortfolioOpt, Riskfolio-Lib, scikit-portfolio"* as predecessors — the ecosystem is consolidating toward skfolio.

Adjacent frameworks checked for completeness: `backtrader` last push **2024-08-19** (dormant); `zipline-reloaded` last push 2026-01-06 (low activity, 1,922 stars).

---

### 4. Prop-firm constraint systems — how the firms actually define them

This section is entirely from firm-operated primary sources. It is the specification a "prop-firm Book" must satisfy.

#### 4.1 FTMO (forex/CFD) — [ftmo.com/en/trading-objectives](https://ftmo.com/en/trading-objectives/) (page last modified 2026-05-13)

All limits are breached on **equity**, defined by FTMO as *"Balance + Open Positions P/L ± Swaps – Commissions"*.

**Maximum Daily Loss.** *"The Maximum Daily Loss Limit is recalculated daily at 00:00 CE(S)T as the difference between: the account balance recorded at 00:00 CE(S)T of the current day and the Maximum Daily Loss Amount."* Amount = **3%** of Initial Simulated Capital (1-Step) or **5%** (2-Step). On day 1 the anchor is the Initial Simulated Capital. The limit *"remains in effect until the next recalculation."*

Worked example (2-Step, $100k): Day 1 limit $95,000. If the balance at midnight is $102,000 → Day 2 limit $97,000. If then $101,000 → Day 3 limit $96,000. **Note the limit can go DOWN day-over-day** — it is anchored to *yesterday's* balance, not a peak.

**Maximum Loss — and this differs by product, which is the trap.**
- **2-Step (Challenge, Verification, and the funded FTMO Account):** *"establishes a **static** limit… calculated as the difference between the Initial Simulated Capital and the Maximum Loss Amount, which is 10% of the Initial Simulated Capital."* $100k → floor $90,000, forever.
- **1-Step (Challenge and funded FTMO Account):** *"establishes an **end-of-day trailing** limit… recalculated daily at 00:00 CE(S)T as the difference between the **highest account balance achieved at 00:00 CE(S)T of any preceding trading day** or, if higher, the Initial Simulated Capital, and the Maximum Loss Amount, which is 10%."* *"The limit can only increase, but never decrease."* Reset semantics: *"when a Reward is withdrawn and a new FTMO Account is provided, the Maximum Loss Limit fully resets, returning the first-day limit to 90% of the Initial Simulated Capital."*

**Best Day Rule (1-Step).** *"your Best Day does not represent more than 50% of your Positive Days' Profit."* Computed on **closed** trades, per day boundary 00:00 CE(S)T. Explicitly *"not treated as a rule breach"* — it just blocks passing/payout until more profit accrues elsewhere. This is a *consistency* constraint, a structurally different rule class from a loss cap: it is a **gate on eligibility**, not a kill switch.

**Minimum Trading Days (2-Step).** 4 days, where a Trading Day is *"any day – measured from 00:00:00 to 23:59:59 CE(S)T – during which at least one position is opened."*

Profit targets: 10% (Challenge), 5% (Verification); none on funded accounts.

#### 4.2 Topstep (CME futures) — [help.topstep.com](https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit) (article updated 2026-07-01)

**Maximum Loss Limit (MLL)** — *"the lowest point your account balance is allowed to reach. If your balance hits it at any point during the trading day, including on unrealized P&L, your account is liquidated immediately."* Sizes: $50K → $2,000; $100K → $3,000; $150K → $4,500.

Trailing mechanics: *"The MLL is a trailing limit. It rises as your **end-of-day** balance grows, but never moves down. Once it reaches your starting balance, **it locks permanently**."* And on cadence: *"The MLL updates at the end of each trading day but is **monitored in real time** throughout the session. Both realized and unrealized P&L count toward it."*

The slippage rule is important for how a Book must reason about breaches: *"Risk limits are monitored in real-time using Net P&L — both realized and unrealized. If your account touches or falls below a limit at any point, it's a violation and liquidation triggers immediately… Final balance above the limit doesn't matter. **The breach happened first.**"* Their own worked example shows the account liquidated at an unrealized $47,750 against a $48,000 MLL, with the final realized balance at $48,050 — still a breach.

**Daily Loss Limit (DLL)** — [separate article](https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account) (updated 2026-06-30). Optional in the Combine and Express Funded Account, mandatory in the Live Funded Account. *"Triggering it is not a rule violation — it's a forced break for the rest of that session."* Session runs 5 PM CT – 3:10 PM CT. Action on trigger: *"Open positions are flattened; Pending orders are canceled; No new trades until 5 PM CT next session."* Sizes: $50K → $1,000; $100K → $2,000; $150K → $3,000.

Also notable — Topstep exposes a **Personal Daily Loss Limit (PDLL)** with an explicit *action* enum: `Do Nothing` / `Liquidate` / `Liquidate and Block`, plus a **Trailing PDLL** with a `trailing method` of `Unrealized Gains` (real-time) or `Realized Gains` (only after a closing profitable trade). That action/method pair is a clean vocabulary QMF should steal directly.

Topstep is futures-only and day-trading-only: *"All positions must be closed by 3:10 PM CT every weekday… No swing trading. No Forex."* ([products article](https://help.topstep.com/en/articles/8284206-when-and-what-products-can-i-trade)) — so it is a design reference, not a venue for QMX.

#### 4.3 Apex Trader Funding (CME futures) — [apextraderfunding.com](https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/) (page modified 2026-04-28)

The most aggressive variant, and the one that most often kills accounts:

> *"The threshold follows the account's highest intraday balance (Peak Balance). As a new Peak Balance is reached, the threshold moves upward… **The threshold is enforced in real time, including unrealized PnL.**"*
> *"Peak Balance includes both realized and unrealized gains"* — and *"If an open trade pushes your account to a new high, the Trailing Threshold adjusts upward immediately even if the position is not closed."*

Worked example ($50K eval, $2,000 max intraday DD): threshold starts $48,000. Unrealized profit lifts balance to $50,900 → new threshold $48,900. *"If the trade closes at $50,300, the Peak Balance remains $50,900 and the threshold remains $48,900."* So the trader permanently gave up $600 of headroom for profit they never banked.

Trailing distance by size: 25K → $1,000; 50K → $2,000; 100K → $3,000; 150K → $4,000.

Stop-trailing rules differ by account **and by data provider**, which is a real modelling wrinkle:
- Performance Accounts: threshold stops rising once it reaches Starting Balance + $100.
- Rithmic and Wealthcharts Evaluations: stops at Profit Target Balance (reached when the high balance hits Profit Target Balance + Max Drawdown).
- **Tradovate Evaluations: *"the Intraday Trailing Drawdown continues to trail indefinitely with the Peak Balance and does not stop at a fixed level."***

Does not reset daily: *"The Intraday Trailing Threshold follows the highest balance achieved and does not reset daily."* Breach is terminal and slippage-tolerant in the firm's favour: *"Once the threshold is touched, the account is considered breached."*

Apex explicitly distinguishes the two rule classes: *"Is the Intraday Trailing Drawdown the same as a Daily Loss Limit? No… They are separate risk controls."*

#### 4.4 The six axes a prop-firm rule model must parameterize

Derived from the three primary sources above. Any QMF "prop-firm Book" schema that misses one of these will mis-model a real firm:

| Axis | Observed values |
|---|---|
| **Anchor** | Initial capital (FTMO 2-Step max loss) · Prior-day-boundary balance (FTMO daily) · Highest prior day-boundary balance (FTMO 1-Step max loss, Topstep MLL) · Running intraday peak incl. unrealized (Apex) |
| **Measure** | Equity incl. floating P&L, swaps, commissions (FTMO) · Net P&L realized + unrealized (Topstep) · Balance incl. unrealized (Apex) — **all three are floating-inclusive; none are closed-trade-only** |
| **Update cadence** | Static · End-of-day recalculation, real-time monitoring (FTMO, Topstep) · Continuous real-time (Apex) |
| **Day boundary / timezone** | 00:00 CE(S)T (FTMO) · 5:00 PM–3:10 PM CT session (Topstep) · none / continuous (Apex) |
| **Ratchet & lock** | Never decreases (FTMO 1-Step, Topstep, Apex) · Can decrease (FTMO daily limit) · Locks at start balance (Topstep) · Locks at start+$100 or profit target (Apex, provider-dependent) · Full reset on payout (FTMO, Topstep) |
| **Breach action** | Liquidate + permanent fail (FTMO max loss, Apex, Topstep MLL) · Flatten + cancel + block until next session, **no violation** (Topstep DLL) · Eligibility gate only, no liquidation (FTMO Best Day Rule) |

#### 4.5 Does open source model any of this? Essentially no.

A GitHub repository search sorted by stars for prop-firm risk/drawdown returns MetaTrader Expert Advisors and SEO-spam repos; nothing library-shaped. The two closest things:

- **`gabrielee5/prop-firm-simulator`** ([repo](https://github.com/gabrielee5/prop-firm-simulator)) — MIT, **0 stars, 1 fork, 17 commits**, Python 3.10+. A Monte Carlo EV analyzer, not a runtime rule engine. Its config models only three parameters — `daily_max_loss_pct`, `overall_max_loss_pct`, `target_profit_pct` — i.e. it collapses all six axes above into "static daily %" and "static total %". One genuinely useful idea from its README: **risk capping** — *"The simulator automatically reduces risk per trade when approaching loss limits. For example, with 6% max loss and 5% risk per trade, after one losing trade (-5%), the next trade can only risk 1% to avoid breaching the limit."* That is the correct interaction between a sizing rule and a hard constraint, and QMF should implement it. Its stated conclusion is also worth knowing: it claims a zero-edge coin-flip strategy passes many firms' challenges often enough to be EV-positive at the right R:R and risk-per-trade. **The claim is the repo author's simulation output, not independently verified — UNVERIFIED.**
- **`michaelsboost/PropForge`** ([repo](https://github.com/michaelsboost/PropForge)) — a browser-based training simulator for humans (phase-based evaluations, resets). Not a library.

Everything else found (`valtorim/mt5-propfirm-drawdown-guard`, `quorvathz/prop-matrix-engine`, `youcefbibo53/PropGuard-Trailing-Equity-Armor`, `cgemise971/PropFirmEA`, …) is MQL4/MQL5 Expert Advisor territory, mostly with fabricated badge links and no meaningful stars. **Conclusion: there is no prior art to copy. QMF must specify and build this.**

---

### 5. Drawdown-based runtime controls — what exists and what's wrong with it

**LEAN `MaximumDrawdownPercentPortfolio`** ([source](https://github.com/QuantConnect/Lean/blob/master/Algorithm.Framework/Risk/MaximumDrawdownPercentPortfolio.py)) — the whole thing, verbatim in substance:

```python
def __init__(self, maximum_drawdown_percent = 0.05, is_trailing = False):
    self.maximum_drawdown_percent = -abs(maximum_drawdown_percent)
    self.is_trailing = is_trailing          # False = vs starting value; True = vs peak
    self.initialised = False
    self.portfolio_high = 0

def manage_risk(self, algorithm, targets):
    current_value = algorithm.portfolio.total_portfolio_value
    if not self.initialised:
        self.portfolio_high = current_value
        self.initialised = True
    if self.is_trailing and self.portfolio_high < current_value:
        self.portfolio_high = current_value
        return []
    pnl = self.get_total_drawdown_percent(current_value)
    if pnl < self.maximum_drawdown_percent and len(targets) != 0:
        self.initialised = False            # <-- re-arms on the next bar
        risk_adjusted_targets = []
        for target in targets:
            algorithm.insights.cancel([target.symbol])
            risk_adjusted_targets.append(PortfolioTarget(target.symbol, 0))
        return risk_adjusted_targets
    return []
```

Four defects to learn from:
1. **`self.initialised = False` after a breach** resets the high-water mark to the *post-loss* value on the very next call. There is no cooldown, no lockout, no "blocked until tomorrow." It liquidates and immediately re-arms at the new lower level.
2. **State is in-memory only.** `portfolio_high` does not survive a process restart. On a VPS this silently resets the drawdown baseline.
3. **`if ... and len(targets) != 0`** — if the portfolio construction model emits no targets on the bar where the drawdown breaches, nothing is liquidated. The kill switch is coupled to the alpha's activity.
4. `total_portfolio_value` is a single scalar with no notion of day boundary or session, so a *daily* loss cap cannot be expressed at all.

**LEAN `TrailingStopRiskManagementModel`** ([source](https://github.com/QuantConnect/Lean/blob/master/Algorithm.Framework/Risk/TrailingStopRiskManagementModel.py)) — per-security, tracks `absolute_holdings_value` per symbol, seeded from `absolute_holdings_cost`, resets on position-side change, and liquidates when `abs((trailing - current)/trailing) > maximum_drawdown_percent`. Notably it iterates `algorithm.securities` rather than the incoming `targets`, so it is not coupled to alpha activity — a better pattern than the portfolio model above. Same in-memory-state problem.

**Freqtrade `MaxDrawdown`** — best ergonomics (declarative, composable, sequenced, `stop_duration` cooldown built in) but closed-trades-only. See §1.4.

**pysystemtrade risk overlay** — portfolio-wide multiplier, but forward-looking on estimated risk, not realized drawdown. See §1.3.

**skfolio / Riskfolio-Lib** — CDaR, EDaR, MDD, Average Drawdown, Ulcer Index exist as *convex optimization objectives* for allocating weights. They are not runtime kill switches and cannot be used as such.

**Nautilus** — has no drawdown control at all. It has the *primitives* (`equity()`, `build_snapshot()`, midnight equity-curve snapshots, `set_trading_state(HALTED|REDUCING)`) but nothing wires them together.

---

## What QMF should copy / avoid

### Copy

1. **pysystemtrade's forecast/position split as the Book boundary.** A strategy must emit a *dimensionless, bounded intent* — pysystemtrade caps forecasts at ±20 with an average absolute value of 10 — and be structurally unable to name a lot size. The Book alone owns the forecast→size conversion. This is the single most important idea in the survey for an LLM-authored-strategy future: an agent that cannot express "buy 5 lots" cannot blow up the account through sizing. Make `Signal` (or whatever QMF calls it) carry direction + conviction + optional stop distance, and nothing else. (GPL-3.0 — copy the *design*, not the code.)

2. **NautilusTrader's mandatory single gate with typed denial reasons.** Every order from every Book passes one BMS gate. Denials return a **standardized machine-readable reason code**, not a free-text log line — Nautilus's list (`TRADING_HALTED`, `TRADING_STATE_REDUCING`, `RATE_LIMIT_EXCEEDED`, `NOTIONAL_EXCEEDS_MAX_PER_ORDER`, …) is the model. For QMX add: `DAILY_LOSS_CAP_REACHED`, `TOTAL_DRAWDOWN_CAP_REACHED`, `TRAILING_THRESHOLD_BREACHED`, `SESSION_CLOSED`, `BOOK_LOCKED_UNTIL`. Non-technical operators and coding agents both need enumerable failure reasons.

3. **The three-state trading mode: `ACTIVE` / `REDUCING` / `HALTED`, with cancels always permitted.** This is exactly right for prop-firm rules: approaching a daily cap → `REDUCING` (can only close); breach → `HALTED`. Nautilus's detail that *cancels still pass through in HALTED* is the safety property that stops a kill switch from stranding open orders.

4. **pysystemtrade's risk overlay shape: a portfolio-wide multiplier in [0,1] computed as `min()` over independent limit checks.** Each rule computes its own multiplier independently; the BMS takes the most conservative. This composes cleanly, is trivially explainable to a non-technical operator ("the system is running at 40% size because the drawdown rule is the binding constraint"), and — crucially — degrades gracefully instead of binary on/off. Name the binding constraint in the output the way pysystemtrade labels its columns `["jump vol", "normal", "shock correlation", "leverage"]`.

5. **Freqtrade's declarative Protections list + `stop_duration` cooldowns + `unlock_at "HH:MM"`.** Rules as data, evaluated in declaration order, each with an explicit lock duration. `unlock_at` is exactly the primitive needed for "blocked until 00:00 CET." Copy the ergonomics wholesale; ignore the closed-trades-only semantics.

6. **Topstep's action/method vocabulary.** Breach action ∈ `{do_nothing, liquidate, liquidate_and_block}` and trailing method ∈ `{unrealized, realized}`. Those two enums cover most of the real design space and were arrived at by a firm with millions of accounts.

7. **Nautilus's `calculate_fixed_risk_position_size` parameter list as QMF's fixed-fractional sizer signature.** Specifically the three easy-to-forget parameters: `commission_rate`, `exchange_rate` (a USD-denominated account trading EURJPY), and `hard_limit` + `unit_batch_size` (broker lot step). Round *down* to the batch size, always.

8. **Risk capping against the remaining budget** (from `prop-firm-simulator`): the per-trade risk fraction must be `min(configured_risk, remaining_headroom_to_nearest_cap)`. With a 6% total cap and 5% per trade, the second trade may only risk 1%. This is the correct coupling between sizing and constraints and it must be computed against the *tightest binding cap* (daily vs total vs trailing), not just one.

9. **Half-Kelly or less, if Kelly is offered at all.** The primary literature is unambiguous: full Kelly's Arrow–Pratt risk aversion is `1/w ≈ 0`; errors in the estimated mean are worth ~100:3:1 against variance and covariance errors for a log investor; overbetting is growth-*and*-security dominated. If QMF exposes a Kelly sizer, hard-cap the fraction at 0.5 in the type system, not in documentation. And require an explicit, dated estimate of edge with a sample size — a Kelly sizer with a made-up win rate is the single most dangerous object an LLM agent could construct.

10. **Volatility targeting as a risk-normalizer.** Adopt `percentage_vol_target` as a Book-level parameter so different strategies' risk budgets are comparable. Justify it in docs by the *tail* result (Harvey et al. 2018: reduces extreme returns across all asset classes) and explicitly state that for **currencies the Sharpe benefit is negligible** — QMX is forex-first, so no one should expect vol targeting to raise returns.

11. **skfolio, offline only, for research.** Its `CombinatorialPurgedCV` and `WalkForward` splitters and its drawdown-measure definitions (CDaR/EDaR/Ulcer) are the best-maintained, best-tested implementations available (BSD-3, v0.20.2 on 2026-08-13). Use them to *evaluate* Book configurations in the research loop. Never on the live path.

12. **Persist all risk state and reconcile it on restart.** Peak equity, day-anchor balance, lock-until timestamps, and cumulative day P&L must be durable and must be re-derived from the broker's own account history at startup, not trusted from a local file alone. This is the defect in every framework surveyed.

### Avoid

1. **Do not adopt LEAN's `manage_risk(targets) -> targets` signature.** A risk authority that can only rewrite target quantities cannot veto, throttle, lock, or express a time window. QMX's BMS needs veto power. LEAN's own PR history shows they had to break the interface once already to get the authority boundary right (#1792) and shipped a composition bug where only the last model mattered (#2605).

2. **Do not couple the kill switch to alpha activity.** LEAN's `MaximumDrawdownPercentPortfolio` only liquidates `if ... and len(targets) != 0`. A drawdown breach must be evaluated on a clock/tick, independent of whether any Book produced a signal.

3. **Do not re-arm a breached rule automatically.** LEAN sets `self.initialised = False` on breach, resetting the high-water mark to the post-loss level on the next bar. Breach must transition to an explicit locked state with an explicit unlock condition (time, operator action, or new session).

4. **Do not build the rule engine on closed trades.** Freqtrade's `MaxDrawdown` default mode (`"ratios"`) is derived from cumulative trade profit ratios and its docs concede it *"can differ from account-level drawdown when position sizing changes over time."* All three prop firms surveyed breach on floating equity. QMF must evaluate on mark-to-market equity, tick-by-tick where the venue allows.

5. **Do not assume UTC day boundaries.** Nautilus's automatic equity curve snapshots at UTC midnight; FTMO recalculates at 00:00 CE(S)T (a moving offset — CET/CEST); Topstep's session runs 5:00 PM–3:10 PM CT. The day-boundary timezone must be a per-Book configuration value with DST handling, and the operator must be able to see it.

6. **Do not put Riskfolio-Lib, PyPortfolioOpt, or skfolio on the live path.** They are N-asset weight optimizers with no concept of a stop, a lot, a broker, or a constraint breach. PyPortfolioOpt additionally carries a documented governance history (5-year release gap, ownership transfer, 112 open issues, [issue #587](https://github.com/PyPortfolio/PyPortfolioOpt/issues/587)); Riskfolio-Lib is bus-factor-one with no GitHub Releases.

7. **Do not use full Kelly, and do not let a strategy author (human or LLM) supply the edge estimate that feeds a Kelly sizer.** *"log investors must estimate means well if they are to survive"* (Ziemba & MacLean). A 1.57×Kelly simulation lost >10,000× initial wealth in the worst of 3000 paths.

8. **Do not sell volatility targeting as alpha.** Cederburg et al. (JFE 2020) show volatility-*managed* strategies do not survive out-of-sample across 103 equity strategies, attributing failure to structural instability in the underlying regressions.

9. **Do not model a "trailing drawdown" as one thing.** FTMO 1-Step trails on end-of-day balance; Topstep trails on end-of-day balance and *locks* at the starting balance; Apex trails in real time on peak balance *including unrealized* and locks at different levels depending on the **data provider** (Rithmic vs Wealthcharts vs Tradovate). Encode the six axes from §4.4 as an explicit schema; do not hardcode any single firm's behaviour.

10. **Do not fork Freqtrade or pysystemtrade code.** Both are **GPL-3.0**. Nautilus is **LGPL-3.0** (dynamic linking is fine; modifying its source is not, for a closed codebase). LEAN is Apache-2.0 and skfolio/Riskfolio-Lib are BSD-3-Clause — those are the only two license families here that are safe to copy code from.

---

## Open questions

**Need an operator decision from Mubarak:**

1. **Which prop firm(s), if any, is QMX actually targeting?** The rule model differs enough between FTMO (equity, CET midnight anchor, static-or-EOD-trailing) and Apex (real-time peak incl. unrealized) that "generic prop-firm Book" is a schema problem, not a feature. Naming one or two target firms up front lets the first implementation be concrete and the schema be validated against something real. FTMO is the natural default given cTrader/forex-first.

2. **Is the prop-firm Book a *simulator* (backtest gate: "would this strategy have passed?") or a *live guard* (runtime: "block this order"), or both?** These have very different accuracy requirements. A live guard must run on ticks and must be conservative by a safety buffer; a simulator can run on bars. Recommend: build one rule-evaluation core, run it in both contexts, with a configurable safety buffer (e.g. trip the internal cap at 80% of the firm's cap).

3. **How much safety buffer, and expressed how?** Every practitioner repo found uses one (e.g. `jbm-ema-gold-scalper`: "Daily DD circuit breaker: 4.5% (buffer before prop firm limit 5%)"). Options: a fixed fraction of the firm limit, a volatility-scaled buffer, or an explicit currency amount. This is a risk-appetite call, not a technical one.

4. **Which sizing method is the default for QMF v1?** Recommendation: fixed-fractional with a stop (Nautilus's signature), with volatility targeting as an opt-in second Book parameter and Kelly deliberately **not** shipped in v1. Confirm.

5. **Is the BMS allowed to reduce sizes silently, or must it always surface a reason?** The pysystemtrade `min()`-multiplier design implies continuous silent scaling. For a non-technical operator I'd argue every scaling event must be logged with the binding constraint named. Confirm this is wanted (it costs log volume).

**Need further research:**

6. **cTrader/Spotware's own risk primitives.** cTrader Open API and cTrader Automate (cAlgo) have their own account/equity/margin model and possibly server-side protective orders. Nothing in this survey covers them. Needs its own investigation before the fixed-fractional sizer signature is finalized (lot step, min/max volume, margin calc, swap accounting).

7. **How Books coordinate when several are live on one account.** Nautilus explicitly lacks a portfolio-level gross exposure cap ([issue #4419](https://github.com/nautechsystems/nautilus_trader/issues/4419), still open July 2026); pysystemtrade solves it with fixed instrument weights and a diversification multiplier; LEAN solves it only inside a single portfolio construction model. QMX's multi-Book case (a prop-firm Book and a personal Book on different accounts vs on the same account) is unspecified. If they share one broker account, the drawdown caps are *joint* and the whole "Book owns money rules" model needs a shared-budget layer.

8. **MacLean, Sanegre, Zhao & Ziemba (2004), "Capital growth with security", JEDC 28(4), 937–954.** Cited by Ziemba & MacLean as reducing the Kelly fraction to *"stay above a prespecified wealth path with high probability"* — which is mathematically the same object as a trailing drawdown floor. If there is an implementable formulation, it is the principled way to size *under* a prop-firm constraint rather than sizing first and clipping after. **Not read; UNVERIFIED.** Worth a follow-up. Same for the convex drawdown-probability-constrained Kelly formulation in [arXiv:1603.06183](https://arxiv.org/abs/1603.06183).

9. **The `prop-firm-simulator` claim that a zero-edge strategy passes many challenges profitably.** If true at QMX's target firm and risk settings, it changes how a prop-firm Book should be *evaluated* (pass probability and EV per attempt, not Sharpe). The claim is one author's unreviewed simulation — reproduce it independently before relying on it.

10. **Does FTMO's Best Day Rule apply to the account QMX would use?** It applies to 1-Step only per the current page. It is a *consistency gate*, a rule class none of the surveyed frameworks can express at all (it constrains the *distribution* of daily profits, not a loss). If QMX targets 1-Step, this needs its own design.

11. **Prop firms change rules.** The FTMO page was last modified 2026-05-13, Topstep's MLL article 2026-07-01, Apex's 2026-04-28 — all within the last four months. Any encoded rule set needs a `source_url` + `retrieved_on` field and a scheduled re-verification, or the Book will silently model a rule that no longer exists.

---

### Source index (primary only)

| Topic | URL |
|---|---|
| LEAN risk management key concepts | https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/risk-management/key-concepts |
| LEAN portfolio construction key concepts | https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/portfolio-construction/key-concepts |
| LEAN supported risk models | https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/risk-management/supported-models |
| LEAN `MaximumDrawdownPercentPortfolio.py` | https://github.com/QuantConnect/Lean/blob/master/Algorithm.Framework/Risk/MaximumDrawdownPercentPortfolio.py |
| LEAN `TrailingStopRiskManagementModel.py` | https://github.com/QuantConnect/Lean/blob/master/Algorithm.Framework/Risk/TrailingStopRiskManagementModel.py |
| LEAN `CompositeRiskManagementModel.py` | https://github.com/QuantConnect/Lean/blob/master/Algorithm/Risk/CompositeRiskManagementModel.py |
| LEAN PR #1792 (authority refactor) | https://github.com/quantconnect/lean/issues/1792 |
| LEAN PR #2605 (composite bug) | https://github.com/quantconnect/lean/issues/2605 |
| Nautilus execution & risk engine concepts | https://nautilustrader.io/docs/latest/concepts/execution/ |
| Nautilus portfolio / equity concepts | https://nautilustrader.io/docs/latest/concepts/portfolio/ |
| Nautilus `RiskEngineConfig` source | https://github.com/nautechsystems/nautilus_trader/blob/master/nautilus_trader/risk/config.py |
| Nautilus `RiskEngine` Rust API 0.61.0 | https://docs.rs/nautilus-risk/0.61.0/nautilus_risk/engine/struct.RiskEngine.html |
| Nautilus `calculate_fixed_risk_position_size` | https://docs.rs/nautilus-risk/0.61.0/nautilus_risk/sizing/fn.calculate_fixed_risk_position_size.html |
| Nautilus issue #4419 (no portfolio exposure cap) | https://github.com/nautechsystems/nautilus_trader/issues/4419 |
| pysystemtrade backtesting docs | https://github.com/robcarver17/pysystemtrade/blob/master/docs/backtesting.md |
| pysystemtrade `risk_overlay.py` | https://github.com/robcarver17/pysystemtrade/blob/master/systems/risk_overlay.py |
| pysystemtrade `defaults.yaml` | https://github.com/robcarver17/pysystemtrade/blob/master/sysdata/config/defaults.yaml |
| Freqtrade Protections | https://www.freqtrade.io/en/stable/plugins/ |
| FTMO Trading Objectives | https://ftmo.com/en/trading-objectives/ |
| Topstep Maximum Loss Limit | https://help.topstep.com/en/articles/8284204-what-is-the-maximum-loss-limit |
| Topstep Daily Loss Limit | https://help.topstep.com/en/articles/10490293-daily-loss-limit-in-the-trading-combine-and-express-funded-account |
| Apex Intraday Trailing Drawdown | https://apextraderfunding.com/help-center/intraday-trailing-drawdown-accounts/intraday-trailing-drawdown-explained/ |
| Ziemba & MacLean, *Using the Kelly Criterion for Investing* | https://webhomes.maths.ed.ac.uk/mckinnon/blackouts/StochOptFinanceAndEnergySpringer/Chap1_KellyZiemba.pdf |
| Chopra & Ziemba (1993), JPM 19(2) | https://jpm.pm-research.com/content/19/2/6 |
| Harvey et al. (2018), *The Impact of Volatility Targeting* | https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3175538 |
| Cederburg et al. (2020), JFE 138(1) | https://www.sciencedirect.com/science/article/abs/pii/S0304405X2030132X |
| skfolio homepage / model list | https://skfolio.org/ |
| skfolio paper | https://arxiv.org/abs/2507.04176 |
| Riskfolio-Lib repo | https://github.com/dcajasn/Riskfolio-Lib |
| PyPortfolioOpt repo (transferred org) | https://github.com/PyPortfolio/PyPortfolioOpt |
| PyPortfolioOpt maintenance issue #587 | https://github.com/PyPortfolio/PyPortfolioOpt/issues/587 |
| `gabrielee5/prop-firm-simulator` | https://github.com/gabrielee5/prop-firm-simulator |
