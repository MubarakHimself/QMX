# QMF Prior Art: Indicators and Analysis Tooling

**Research date:** 2026-08-17
**Area:** Which indicator / performance-metric / statistics wheels already exist, their 2025–2026 maintenance state, and where a thin QMF abstraction earns its keep.
**Method:** primary sources only (upstream repos, official docs, PyPI JSON metadata, GitHub API). Every load-bearing claim carries an inline URL. Anything I could not confirm against a primary source is tagged **UNVERIFIED**.

---

## In plain words

1. An "indicator" is a number computed from price history — a 20-bar average, an RSI, an ATR stop distance. Every trading system needs dozens of them.
2. There are two completely different ways to compute them, and QMF needs both. In **research** you have ten years of bars sitting in memory and you want the whole column of values at once, fast. In **live trading** one new bar arrives every minute and you want just the newest value, cheaply.
3. The trap: if you write the research version and the live version separately, they drift. Your backtest says "buy" and the live bot says "hold" — same strategy, different numbers. This is the single most expensive bug class in this whole area.
4. The good news is that the best platforms already solved it, and they solved it the same way: **write the indicator once as the live, one-bar-at-a-time version, then produce the research column by replaying that same object over history.** QuantConnect's LEAN does exactly this in production. NautilusTrader does the same.
5. So QMF should define each indicator once, in incremental form, and treat "vectorized" as a replay loop over that definition — not as a second, hand-written implementation.
6. TA-Lib is still the industry-standard library of ~150 indicators. It was famously painful to install on Windows for a decade. **That is now fixed** — since version 0.6.5 it ships prebuilt Windows/Linux/Mac wheels, so `pip install TA-Lib` just works.
7. But TA-Lib has a subtle correctness trap: about twenty of its indicators (EMA, RSI, ATR, ADX, KAMA…) give slightly *different answers depending on how much history you fed in*. TA-Lib itself documents this and calls it the "unstable period". QMF must handle warm-up explicitly rather than hope.
8. A worse pair — Parabolic SAR and Accumulation/Distribution — *never* agree across different start dates. TA-Lib says so plainly. Strategies built on those two need special care.
9. `pandas-ta`, once the most popular Python indicator library, effectively **imploded**: the original GitHub repo is gone (404), its PyPI history was wiped, and its replacement website no longer resolves. A community fork, `pandas-ta-classic`, took over and is now the wrapper TA-Lib's own site links to. Use the fork; never the original.
10. `tulipy` is dead (its own description says "NOT ACTIVELY MAINTAINED", last touched 2019). `ta` (bukosabino) has had no release since 2023. Neither should be a QMF dependency.
11. For "how did my strategy do" reports — Sharpe, drawdown, win rate, tearsheets — `quantstats` is alive and actively maintained again as of 2026. It drags in charting and Yahoo-Finance dependencies, so QMF should keep it in the research environment, never on the live trading VPS.
12. For statistics that aren't indicators — cointegration tests for pairs trading, regressions — `statsmodels` is the boring, stable, correct answer. Use it as-is.
13. For splitting data into "train here, test there" windows without cheating, `scikit-learn` and `skfolio` cover it. Avoid `mlfinlab`: despite appearances it is **not** open source and forbids commercial use without a paid licence.
14. Net recommendation: QMF wraps TA-Lib (batch) plus a small set of hand-written incremental indicators behind **one** QMF-owned interface, so strategies and future LLM agents see a stable, small surface, and the two computation modes are provably the same numbers.
15. The abstraction earns its keep in exactly three places: (a) one definition, two execution modes; (b) automatic, correct warm-up so live and backtest agree; (c) machine-readable indicator metadata so an LLM can discover what exists and what parameters are legal without reading code.

---

## Findings

### 1. TA-Lib — the C core and the Python wrapper

**Maintenance: healthy and unusually active.** The C core lives at <https://github.com/TA-Lib/ta-lib> ("Official TA-Lib Core", BSD 3-Clause, ~1,658 stars). GitHub API reports `pushed_at` = 2026-08-17 — commits landing the day of this research. The project was resurrected from the long-dormant SourceForge 0.4.0 (released September 2007, re-tagged on GitHub 2024-02-13) into an actively released library.

**Release line** (<https://github.com/TA-Lib/ta-lib/releases>):

| Version | Date | Note |
|---|---|---|
| v0.4.0 | 2024-02-13 (tag) | the 2007 original |
| v0.6.1 | 2024-12-23 | link name changed `-lta_lib` → `-lta-lib`; headers moved under `ta-lib/`; autotools + CMake only |
| v0.6.2 | 2024-12-26 | Windows 64-bit DLL install location fixed to `C:\Program Files\TA-Lib` |
| v0.6.3 | 2025-01-06 | Windows DLL export fix |
| v0.6.4 | 2025-01-11 | gen_code Windows compile fix |
| **v0.7.1** | **2026-07-03** | **latest stable.** New Rust-based `ta_codegen` replaces `gen_code`; `TA_FUNC_NO_RANGE_CHECK` removed in favour of exported `TA_*_Unguarded` variants; period=1 handling fixed across SMA/EMA/WMA/DEMA/TEMA/TRIMA/KAMA/T3/MAVP and the MACD family |
| `ci-build-pool` | 2026-08-05 | **prerelease**, internal CI artifact store, contains 0.8.1 build assets. Explicitly labelled "Not an installation source." |

So: **0.7.1 is the newest stable C release; 0.8.x exists only as CI artifacts.** This matters for the streaming API below.

**The Windows install story — resolved.** The historical pain (needing MSVC, a manual `ta-lib` C build, or Christoph Gohlke's unofficial wheels) is over. From the wrapper README (<https://github.com/TA-Lib/ta-lib-python>, ~12,188 stars, `pushed_at` 2026-07-29):

> "Starting with version 0.6.5, we now build binary wheels for different operating systems, architectures, and Python versions using GitHub Actions."

Covered: Linux x86_64/arm64 (manylinux + musllinux), macOS x86_64/arm64, **Windows x86_64, x86, and arm64**, Python **3.9 through 3.14**. `python -m pip install TA-Lib` now resolves to a wheel on both Mubarak's Windows box and the Linux VPS with no C toolchain. Wrapper releases: **v0.7.0 (2026-07-04)**, **v0.7.1 (2026-07-16)** — "Fix wheels to build with TA-Lib C 0.7.1 properly."

Branch policy from the README: `0.4.x` (ta-lib C 0.4.x + numpy 1), `0.5.x` (ta-lib C 0.4.x + numpy 2), `0.6.x` (ta-lib C 0.6.x + numpy 2). The 0.7.x line tracks C 0.7.1. Coverage: "150+ indicators such as ADX, MACD, RSI, Stochastic, Bollinger Bands" plus candlestick pattern recognition, across ten function groups (<https://ta-lib.github.io/ta-lib-python/doc_index.html>).

Source builds still need the C library: `ta-lib-0.7.1-windows-x86_64.msi` on Windows, or `ta-lib-0.7.1-src.tar.gz` → `./configure --prefix=/usr && make && sudo make install` on Linux. There is also now a GitHub Action, `TA-Lib/setup-ta-lib`, and Conan package support (both added in C 0.7.1).

#### 1a. The numerical-stability trap — the most important finding in this document

TA-Lib now documents formally what used to be folklore. From <https://ta-lib.org/functions/stability.html> (page modified 2026-08-10), every function is classified into one of four categories answering: *"does the value at a given bar depend on how much history you passed in?"*

- **Start-Independent** — "reads a bounded window — a fixed number of bars — and ignores everything older." Safe. (SMA, WMA, TRIMA, HMA.)
- **Initial Unstable Period** — "Early values depend on how much history precedes them, and converge as more bars are supplied. These functions are defined recursively: each value folds in the previous one, so the series never entirely forgets where it began."
- **Depends on MA Type** — functions taking `optInMAType`; the choice decides which category applies. EMA(1), DEMA(3), TEMA(4), KAMA(6), MAMA(7), T3(8) are unstable; SMA(0), WMA(2), TRIMA(5), HMA(9) are start-independent.
- **Path-Dependent** — "built up from the first bar … so it depends on where your data begins and **never converges**. Unlike an unstable period, there is no warm-up you can discard: the difference persists for the whole series."

The path-dependent examples are named explicitly and are both commonly used in FX strategies:

> "**AD** adds each bar's money-flow volume to a running total that begins at zero on your first bar. Only the differences between bars carry meaning; the absolute level is an artifact of the start date."
> "**SAR** is a state machine: it reads the first two bars to decide whether the trend starts long or short, then carries that direction, the extreme price, and an acceleration factor forward. **Start a day earlier and it can pick the opposite direction, putting the stop on the other side of price for the rest of the run.**"

The exact list of functions with an unstable period (<https://ta-lib.org/api/unstable-period/>, modified 2026-08-11):

`ADX`, `ATR`, `CMO`, `DX`, `EMA`, `HT_DCPERIOD`, `HT_DCPHASE`, `HT_PHASOR`, `HT_SINE`, `HT_TRENDLINE`, `HT_TRENDMODE`, `KAMA`, `MAMA`, `MINUS_DI`, `MINUS_DM`, `NATR`, `PLUS_DI`, `PLUS_DM`, `RSI`, `T3`.

That is EMA, RSI, ATR and ADX — the four most common building blocks in a retail FX strategy.

The same page lays out the three remedies, and QMF must pick one deliberately:

> 1. **"Ignore the problem."** … "The weakness is that nothing warns you when the assumption stops holding — a short series, or a back-test that acts on the earliest bars, will quietly use values that are off."
> 2. **"Provide extra history."** … "TA-Lib is left at its default (unstable period `0`) and returns everything it can compute, while your code chooses what to drop."
> 3. **"Have TA-Lib drop the unstable data."** `TA_SetUnstablePeriod(TA_FUNC_UNST_EMA, 30)` or `TA_SetUnstablePeriod(TA_FUNC_UNST_ALL, 30)`.

Critical operational detail: the setting is **global process state**, and "the setting follows the function wherever it runs: whether you call it directly, or another indicator uses it internally. The EMA id therefore affects EMA itself and every indicator built on one, such as MACD and DEMA." The C API page (<https://ta-lib.org/api/>) further warns that `TA_SetUnstablePeriod` must be called single-threaded before any concurrent TA calls.

Also documented on that page and relevant to long-horizon FX minute data: `TA_MAX_INDEX` is 100,000,000, and "a handful of functions accumulate rounding error as the series grows … **WMA, HMA, CORREL and the LINEARREG family are the ones to know about.**"

#### 1b. Lookback — the machine-readable warm-up length

Every TA function has a matching `TA_XXXX_Lookback()`: "The lookback is the number of input elements consumed before the first output can be calculated. Example: a simple moving average (SMA) of period 10 has a lookback of 9." (<https://ta-lib.org/api/>). Exposed in Python via the Abstract API as `Function('x').lookback` (<https://ta-lib.github.io/ta-lib-python/abstract.html>).

This is the primitive QMF needs to compute warm-up automatically: `required_history = lookback + unstable_period + 1`.

#### 1c. The Abstract API — the LLM-facing metadata surface

<https://ta-lib.github.io/ta-lib-python/abstract.html> exposes per-function introspection:

```python
Function('x').function_flags   # behavioural flags
Function('x').input_names      # expected price inputs
Function('x').parameters       # current settings + defaults
Function('x').lookback         # required historical bars
Function('x').output_names     # result field names
Function('x').output_flags
```

`print(Function('stoch').info)` returns an ordered dict with `name`, `display_name`, `group`, `input_names`, `parameters` (with defaults), `output_names`.

The C docs call out this exact use case (<https://ta-lib.org/api/>):

> "'Mutating' the function and its parameters while searching for strategies (e.g. a genetic or neural-network algorithm)."
> "Populating a charting app: the indicator menu and each settings dialog come straight from the metadata."

**This is directly relevant to QMX's stated goal of LLM agents authoring strategies through a constrained surface.** QMF gets a free, authoritative, machine-readable catalogue of ~150 indicators with legal parameter ranges — no hand-maintained JSON schema needed for the TA-Lib-backed subset.

#### 1d. TA-Lib's own streaming API — coming, but NOT YET RELEASED

<https://ta-lib.org/api/stream/> (modified 2026-08-07) documents a real C streaming API, banner: **"Not yet released. This feature is planned for v0.8.x."**

The design is precisely the contract QMF wants:

> "open a stream once, then feed it one bar at a time. The stream carries its state from bar to bar, so each new bar costs O(1) — and every value is **bit-identical** to what the batch function (`TA_SMA`, `TA_RSI`, …) would return by recomputing over the whole array."

| Call | When | Does |
|---|---|---|
| `TA_<NAME>_Open` | once | validate params, consume warm-up history, return stream + current value |
| `TA_<NAME>_OpenAndFill` | once, instead of `Open` | like `Open`, but returns the output for **every** history bar |
| `TA_<NAME>_Update` | once per **closed** bar | commit one bar, return the new value |
| `TA_<NAME>_Peek` | any time on the **forming** bar | evaluate a provisional bar **without** committing state |
| `TA_<NAME>_Close` | once | free the stream |

Rules worth stealing wholesale:
- **Warm-up:** "`Open` succeeds only if `historyLen >= TA_<NAME>_Lookback(params) + 1`."
- **Closed vs forming bar:** "`Update` commits state irreversibly, so use it only for **closed** bars. `Peek` returns the exact value `Update` would, but without committing."
- **Parameters fixed at Open;** unstable period and candle settings "are first read at `Open` and must not change during the stream's life."
- Streams are single-writer; do not persist across library versions.
- Discoverability: "streamable functions carry the `TA_FUNC_FLG_STREAM` flag in their function info."

`OpenAndFill` is the exact "one definition, two modes" primitive: it returns the full historical array *and* leaves you a live stream, from one call.

**Status caveat:** not shipped in 0.7.1. QMF cannot depend on it today, but should design its own interface to mirror it so adoption later is a swap, not a rewrite.

#### 1e. `talib.stream` in Python is NOT incremental — verified from source

This is a widespread misconception and worth pinning down. The Python `stream` module (<https://github.com/TA-Lib/ta-lib-python/blob/master/talib/stream.py>) is generated, and the generator (`tools/generate_stream.py`) emits, for both `startIdx` and `endIdx`:

```python
elif var in ('startIdx', 'endIdx'):
    print('<int>(length) - 1', end= ' ')
```

i.e. it calls the ordinary batch `TA_*` function with the **entire input array** and `startIdx == endIdx == length - 1`. It saves the output allocation, not the computation: for recursive functions the C code still walks from index 0. The README frames it accordingly:

> "An experimental Streaming API … allows users to compute the latest value of an indicator" and "can be faster than using the Function API."

**Consequence for QMF:** calling `talib.stream.RSI(close_array)` once per bar in live trading is O(n) per bar and O(n²) over a session. It is not a live-trading incremental engine. Treat `talib.stream` as "batch with a cheaper return", nothing more.

---

### 2. pandas-ta — a supply-chain cautionary tale. AVOID the original.

Confirmed facts:

- **`https://github.com/twopirllc/pandas-ta` returns HTTP 404.** GitHub API on `repos/twopirllc/pandas-ta` also 404s. The canonical repository is gone.
- PyPI `pandas-ta` (<https://pypi.org/project/pandas-ta/>) latest is **0.4.71b0, released 2025-09-14**, marked **pre-release** ("may not be stable for production use"), sole maintainer listed as `pta`, author "Pandas TA Support <support@pandas-ta.dev>", requires Python >=3.12, status "4 - Beta". Repository URL still points at the dead `github.com/twopirllc/pandas-ta`.
- The stated homepage/docs host, `www.pandas-ta.dev`, **does not resolve** as of 2026-08-17 (`getaddrinfo ENOTFOUND www.pandas-ta.dev`).
- Community account of what happened, GitHub issue opened 2025-09-17 by PabloRuizCuevas (<https://github.com/xgboosted/pandas-ta-classic/issues/30>): maintainership moved from `@twopirllc` to `@amortizer`; "in Pypi the history is wiped out"; the new site described as "like a crazy addware"; reporter suspected a supply-chain attack and stated "I can't even tell which one is the good one or if the web is just a plain scam". Issue was still open with no maintainer response at time of fetch.

**The successor: `pandas-ta-classic`** (<https://github.com/xgboosted/pandas-ta-classic>, ~420 stars, 1,137 commits). PyPI (<https://pypi.org/pypi/pandas-ta-classic/json>): **0.6.52, uploaded 2026-06-24**, MIT, requires Python >=3.10, core deps `numpy>=2.0.0` and `pandas>=2.0.0`, with optional TA-Lib / Numba / tulipy acceleration and optional scipy/sklearn/statsmodels. README claims "224 indicators and utility functions and 62 native candlestick patterns"; the PyPI summary says 193 indicators + 62 patterns (minor inconsistency, **UNVERIFIED** which is current). Rolling Python support policy: latest stable plus 4 preceding minors.

**Decisive endorsement:** TA-Lib's own install page (<https://ta-lib.org/install/>, modified 2026-08-07) lists, under "Wrappers":

| Language | Github Repos |
|---|---|
| pandas | [pandas-ta-classic](https://github.com/xgboosted/pandas-ta-classic) |
| Python | [ta-lib-python](https://github.com/ta-lib/ta-lib-python) |

`pandas-ta-classic` is the officially-linked pandas wrapper. The original `pandas-ta` is not listed anywhere.

A second snapshot fork exists, `MerlinR/Pandas-ta-fork`, self-described as a pre-removal copy with no PyPI release. Not a maintained option.

---

### 3. Polars-native indicator options

Polars is the right dataframe for QMF's research path (columnar, lazy, multithreaded, no pandas index semantics). Three live options, all confirmed maintained:

| Project | Package | Approach | Stars | `pushed_at` |
|---|---|---|---|---|
| [Yvictor/polars_ta_extension](https://github.com/Yvictor/polars_ta_extension) | `pip install polars_talib` | Rust plugin binding **TA-Lib C** into Polars expressions | 247 | 2026-06-04 |
| [wukan1986/polars_ta](https://github.com/wukan1986/polars_ta) | `pip install polars-ta` | Indicators **rewritten** as native `pl.Expr`, plus wrappers for non-expr-shaped functions | 260 | 2026-02-11 |
| [noahbclarkson/polars-ta](https://github.com/noahbclarkson/polars-ta) | Rust crate `polars-ta` | Pure-Rust reimplementation, adds fractional differentiation | **UNVERIFIED** (GitHub API rate-limited during research) | **UNVERIFIED** |

`polars_talib` usage (from its README):

```python
import polars as pl
import polars_talib as plta

df.with_columns(
    pl.col("close").ta.ema(5).alias("ema5"),
    pl.col("close").ta.macd(12, 26, 9).struct.field("macd"),
)

# multi-symbol, the killer feature for a portfolio of FX pairs:
df.with_columns(
    pl.col("close").ta.ema(5).over("symbol").alias("ema5"),
)
```

Its README claims "about 150x faster" than pandas+TA-Lib (135 ms/loop vs 19.2 s/loop) — a vendor benchmark, unaudited, and the comparison baseline is pandas `groupby.apply`, so treat the magnitude as indicative only. The `.over("symbol")` grouped-expression form is the genuinely load-bearing win: it eliminates the per-symbol Python loop.

**Key architectural point:** because `polars_talib` binds the same TA-Lib C core, its numbers should agree bit-for-bit with `talib` — the same unstable-period semantics apply. `wukan1986/polars_ta`, being a reimplementation, does **not** carry that guarantee. **UNVERIFIED:** whether `polars_talib` exposes `TA_SetUnstablePeriod` or `Lookback`, and whether it publishes Windows wheels (its CI workflows exist but the platform matrix was not visible in the README).

---

### 4. tulipy / tulipindicators — dead. Do not use.

<https://github.com/cirla/tulipy> — GitHub API: `pushed_at` **2019-04-11**, `open_issues_count` 0, 93 stars, and the repository's own description reads:

> "**[NOT ACTIVELY MAINTAINED]** Tulipy - Financial Technical Analysis Indicator Library (Python bindings for Tulip Charts)"

Its parent, `TulipCharts/tulipy`, has 376 stars and 10 open issues but is likewise not a live project. `pandas-ta-classic` still lists `tulipy` as an *optional* accelerator, which is a compatibility shim, not an endorsement. **Verdict: seven years stale, self-declared unmaintained. Exclude from QMF entirely.**

---

### 5. NautilusTrader — the reference incremental-indicator architecture

<https://github.com/nautechsystems/nautilus_trader> — LGPL-3.0, ~25,654 stars, `pushed_at` **2026-08-17 11:09 UTC** (same day as this research), default branch `develop`, description now "Production-grade **Rust-native** trading engine with deterministic event-driven architecture". Indicators have migrated out of the Cython `nautilus_trader/indicators/*.pyx` tree into the Rust crate `crates/indicators` (a commit dated 2026-08-07 is titled "Remove Cython residuals and guard against new deferrals", and 2026-08-04 "Align PyO3 module ownership"). **This is a live, in-flight architectural migration — relevant to dependency risk if QMF were to bind Nautilus internals.**

**The `Indicator` trait** (<https://github.com/nautechsystems/nautilus_trader/blob/develop/crates/indicators/src/indicator.rs>), verbatim:

```rust
pub trait Indicator {
    fn name(&self) -> String;
    fn has_inputs(&self) -> bool;
    fn initialized(&self) -> bool;

    fn handle_delta(&mut self, delta: &OrderBookDelta) { … }
    fn handle_deltas(&mut self, deltas: &OrderBookDeltas) { … }
    fn handle_depth(&mut self, depth: &OrderBookDepth10) { … }
    fn handle_book(&mut self, book: &OrderBook) { … }
    fn handle_quote(&mut self, quote: &QuoteTick) -> anyhow::Result<()> { … }
    fn handle_trade(&mut self, trade: &TradeTick) { … }
    fn handle_bar(&mut self, bar: &Bar) { … }

    fn reset(&mut self);
}
```

Three design decisions worth copying exactly:

1. **`has_inputs()` and `initialized()` are separate.** "Has it seen any data at all" is a different question from "has it seen enough data to be trusted". Conflating them is how strategies act on half-warm indicators.
2. **One handler per input type,** all defaulting to a panic/`bail!` with a message naming the indicator. An indicator declares which data shapes it accepts by which handlers it overrides; wiring the wrong feed fails loudly and immediately rather than silently producing garbage.
3. **`reset()` is mandatory,** not optional. Deterministic replay requires it.

Concrete incremental implementation, `ExponentialMovingAverage` (<https://github.com/nautechsystems/nautilus_trader/blob/develop/crates/indicators/src/average/ema.rs>): fields `period`, `price_type`, `alpha` (= 2/(period+1)), `value`, `count`, `initialized`, `has_inputs`. First input seeds `value` and sets `count = 1`; subsequent inputs apply `value = alpha * new + (1 - alpha) * previous`; `initialized` flips to `true` once `count >= period`. `handle_bar` is a one-liner delegating to `update_raw((&bar.close).into())`.

Note that this is TA-Lib's "Initial Unstable Period" category, seeded differently (TA-Lib seeds EMA with an SMA of the first `period` values; Nautilus seeds with the first value). **The two will not agree bit-for-bit.** That is a concrete, verifiable reason QMF must not mix indicator sources within one strategy without a parity test.

**Python-side usage** (<https://nautilustrader.io/docs/latest/getting_started/quickstart/> and `/concepts/strategies/`), verbatim:

```python
class EMACross(Strategy):
    def __init__(self, config: EMACrossConfig):
        super().__init__(config)
        self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)

    def on_start(self):
        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar):
        if not self.indicators_initialized():
            return
        if self.fast_ema.value >= self.slow_ema.value:
            ...
```

The strategy never calls `update()`. Registration wires the indicator to a bar type; the engine updates every registered indicator **before** `on_bar` fires. `indicators_initialized()` is an engine-provided aggregate guard.

**Warm-up ordering** is documented as load-bearing (<https://nautilustrader.io/docs/latest/concepts/strategies/>):

```python
def on_start(self) -> None:
    self.register_indicator_for_bars(self.bar_type, self.fast_ema)
    self.register_indicator_for_bars(self.bar_type, self.slow_ema)

    self.request_bars(
        self.bar_type,
        callback=lambda _: self.subscribe_bars(self.bar_type),
    )
```

> "Live bars are subscribed via the `request_bars()` `callback` so the stream starts only once history has loaded"

Register → request history → *only then* subscribe to live. Historical bars flow through the same `handle_bar` path as live bars, so warm-up is not a separate code path. **This is the single most copyable pattern in this document.**

Nautilus's Rust indicator set is modest and hand-written, not a TA-Lib port. `crates/indicators/src` contains `average/`, `book/`, `momentum/`, `ratio/`, `volatility/`. The `momentum/` directory holds: `amat`, `aroon`, `bb`, `bias`, `cci`, `cmo`, `dm`, `ichimoku`, `kvo`, `macd`, `obv`, `pressure`, `psl`, `roc`, `rsi`, `stochastics`, `swings`, `vhf`. Roughly 20 momentum indicators against TA-Lib's 150+. **Nautilus is the architecture to copy, not the indicator catalogue.**

Quality signals worth noting: PR #4718 ("Scale indicator test tolerance with magnitude", 2026-08-13) replaced `f64::EPSILON` exact-equality assertions with relative+absolute tolerances across 32 expectations; PR #4779 ("Fix MovingAverageConvergenceDivergence input count", 2026-08-16) — the indicator layer is under real, ongoing correctness scrutiny.

---

### 6. QuantConnect LEAN — proof that "one definition, two modes" works in production

LEAN's research environment uses **the same indicator classes** as backtest and live, driven by an explicit replay loop. From <https://www.quantconnect.com/docs/v2/research-environment/indicators/bar-indicators> (verbatim):

```python
qb = QuantBook()
symbol = qb.add_equity("SPY").symbol
atr = AverageTrueRange(20)
```

Manual replay:

```python
# Request historical trading data with the daily resolution.
history = qb.history[TradeBar](symbol, 70, Resolution.DAILY)

# Set the window.size to the desired timeseries length
atr.window.size = 50
atr.true_range.window.size = 50

for bar in history:
    atr.update(bar)

atr_dataframe = pd.DataFrame({
    "current":   pd.Series({x.end_time: x.value for x in atr}),
    "truerange": pd.Series({x.end_time: x.value for x in atr.true_range})
}).sort_index()
```

Or the one-line helper:

```python
atr_dataframe = qb.indicator_history(atr, symbol, 50, Resolution.DAILY).data_frame
```

which, per the algorithm-side docs, "resets your indicator, makes a history request, and updates the indicator with the historical data."

Three mechanisms QMF should note:

1. **Replay is the vectorized mode.** There is no separate array implementation. The DataFrame is a by-product of driving the incremental object over history. Drift is structurally impossible.
2. **`window.size` is the retention dial.** By default an incremental indicator keeps only the current value; opting into a rolling window of the last N values is a per-indicator, per-sub-output setting (`atr.window.size` *and* `atr.true_range.window.size` separately). This is how you get a research column out of a live object without paying memory in production.
3. **Sub-outputs are first-class objects.** `atr.true_range` is itself an indicator with its own window, not a tuple field. Multi-output indicators (MACD → line/signal/histogram; Bollinger → upper/mid/lower) compose rather than special-case.

On the algorithm side (<https://www.quantconnect.com/docs/v2/writing-algorithms/indicators/key-concepts>): automatic indicators (`BB(symbol, 20, 2, Resolution.Daily)`) self-update from the data stream; manual indicators (`new BollingerBands(20, 2)`) require explicit `Update`. `IsReady` gates use, and its docs note "Indicators aren't always ready when you first create them. The length of time it takes to trust the indicator values depends on the indicator period." Warm-up is either `Settings.AutomaticIndicatorWarmUp = true` or an explicit history-request-plus-`Update` loop.

---

### 7. vectorbt IndicatorFactory — the opposite pole, plus a licence trap

<https://github.com/polakowo/vectorbt> — ~8,705 stars, `pushed_at` 2026-08-02, 136 open issues.

**Licence warning (load-bearing for a commercial QMX):** `LICENSE.md` is **Apache 2.0 with the Commons Clause**. The Commons Clause states "the grant of rights under the License will not include, and the License does not grant to you, the right to Sell the Software," where "Sell" covers "a product or service whose value derives, entirely or substantially, from the functionality of the Software," including hosting and support. Solo personal trading is almost certainly fine; QMX-as-a-product is not, and this needs an operator decision before vectorbt appears in any shipped dependency list. (The commercial successor, vectorbt.pro, is separately licensed.)

`IndicatorFactory` (<https://vectorbt.dev/api/indicators/factory/>) solves a *different* problem from Nautilus/LEAN: not one-definition-two-modes, but **one-definition-many-parameters**.

> "by providing it with information such as calculation functions and the names of your inputs, parameters, and outputs, it will create a stand-alone indicator class capable of running the indicator for an arbitrary combination of your inputs and parameters."

```python
MyInd = vbt.IndicatorFactory(
    input_names=['price'],
    param_names=['window'],
    output_names=['ma'],
).from_apply_func(vbt.nb.rolling_mean_nb)

myind = MyInd.run(price, [2, 3])   # both windows, one call
```

Adapters exist: `from_talib()` ("automatically detecting and mapping their inputs, parameters, and outputs" — i.e. it drives the TA-Lib Abstract API) and `from_pandas_ta()` (which, given §2, is now a liability).

**The `input_names` / `param_names` / `output_names` triple is the same metadata shape as TA-Lib's Abstract API `info` dict and is what QMF should adopt for its own indicator registry** — it is independently arrived at by two mature projects, which is decent evidence it is the right decomposition.

Walk-forward splitting also lives here: `vectorbt.generic.splitters` provides `RollingSplitter`, `ExpandingSplitter` and `RangeSplitter`, surfaced via the accessor `rolling_split()` / `expanding_split()`, returning `in_price, in_indexes, out_price, out_indexes` (<https://vectorbt.dev/api/generic/splitters/>; worked example at <https://github.com/polakowo/vectorbt/blob/master/examples/WalkForwardOptimization.ipynb>).

---

### 8. Performance metrics and tearsheets

#### quantstats — ALIVE, actively maintained (this reverses the common 2024-era advice)

<https://github.com/ranaroussi/quantstats> — Apache-2.0, ~7,554 stars, 31 open issues, `pushed_at` **2026-07-20**. PyPI latest **0.0.81, uploaded 2026-01-13**, `requires_python >= 3.10`.

Release cadence (<https://github.com/ranaroussi/quantstats/releases>): 0.0.72 → 0.0.77 across Aug–Sep 2025 (a run of pandas-2.x and DataFrame-handling bug fixes: "truth value of Series is ambiguous", CVaR returning NaN, `1M` → `1ME` frequency alias, timezone normalisation); then **v0.0.78 "2026 Modernization Update" (2026-01-13)** adding Monte Carlo simulation, HTML report parameters and comprehensive type hints, fixing 13 issues; then **v0.0.81 (2026-01-13)** repairing import errors introduced by 0.0.78 and adding Ulcer Performance Index and Risk-Adjusted Return, with "a comprehensive 125-test suite".

**Dependency weight is the real objection, not maintenance.** From <https://pypi.org/pypi/quantstats/json>: `matplotlib>=3.7.0`, `seaborn>=0.13.0`, `scipy>=1.11.0`, `tabulate>=0.9.0`, **`yfinance>=0.2.40`**, `python-dateutil`, `numpy`, `pandas`, optional `plotly`. A charting stack and a Yahoo Finance scraper are not things that belong on a live trading VPS.

Three modules: `quantstats.stats` (metrics), `quantstats.plots` (visualisation), `quantstats.reports` (tearsheets, incl. `qs.reports.html(returns, "SPY")`).

#### quantstats_lumi — the fork, and it has something quantstats lacks

<https://github.com/Lumiwealth/quantstats_lumi> — Apache-2.0, 152 stars, 576 commits, last commit **2026-05-31** ("Emit strict tearsheet metrics JSON"). PyPI `quantstats-lumi`, latest 1.1.5 (~2026-06-01).

Its README's founding rationale — "it seems that the original library is no longer being maintained" — **is now out of date**; ranaroussi/quantstats resumed active development. But the fork added a feature the original does not advertise, and it is directly relevant to QMX's LLM-agent ambitions:

```python
payload = qs.reports.metrics_json(stock, benchmark="SPY", summary_only=True)
```

with a documented contract (`docs/TEARSHEET_METRICS_CONTRACT.md`): `payload["scalar_metrics"]` is the canonical dict; "Percentage-style metrics are stored as raw decimals in JSON (`0.0369`, not `\"3.69%\"`)"; custom metrics can be appended via `custom_metrics={...}` and are merged into both the HTML table and `tearsheet_metrics.json`.

A **machine-readable, versioned metrics contract** is exactly what an LLM agent needs to read a backtest result. Note the fork's README still claims Python >= 3.5 and pandas >= 0.24 in its Requirements section — stale documentation, not a real constraint.

#### empyrical — ABANDONED. Do not use.

<https://pypi.org/project/empyrical/>: latest **0.5.5, released 2020-10-13**, maintainer "Quantopian Inc", classifiers list **Python 2.7, 3.4, 3.5**. Nearly six years stale, from a company that no longer exists. The GitHub repo <https://github.com/quantopian/empyrical> is technically not archived but `pushed_at` is **2024-07-26** with 37 open issues.

**Fork: `empyrical-reloaded`** by Stefan Jansen (<https://github.com/stefan-jansen/empyrical-reloaded>, ~118 stars, 247 commits, Python 3.10+). PyPI: **0.5.12, uploaded 2025-06-01** — roughly 14 months stale at time of writing. Deps include `bottleneck` and a pinned `peewee<3.17.4`. Maintained-ish, but quiet, and it exists mainly to keep `pyfolio-reloaded` / `zipline-reloaded` alive.

**Verdict: empyrical's entire metric set is a strict subset of what quantstats and Nautilus already compute. There is no reason for QMF to take this dependency.**

#### NautilusTrader's built-in analysis crate — the strongest reason not to take quantstats into production

`crates/analysis/src` contains `analyzer.rs`, `snapshot.rs`, `statistic.rs`, and a `statistics/` directory with **34 statistics**: `alpha`, `beta_ratio`, `cagr`, `calmar_ratio`, `down_capture_ratio`, `expectancy`, `expected_shortfall`, `information_ratio`, `long_ratio`, `loser_avg/max/min`, `max_drawdown`, `omega_ratio`, `profit_factor`, `returns_avg`, `returns_avg_loss`, `returns_avg_win`, `returns_kurtosis`, `returns_skewness`, `returns_volatility`, `risk_return_ratio`, `sharpe_ratio`, `sortino_ratio`, `tail_ratio`, `tracking_error`, `treynor_ratio`, `ulcer_index`, `up_capture_ratio`, `value_at_risk`, `win_rate`, `winner_avg/max/min`.

The `PortfolioStatistic` trait (<https://github.com/nautechsystems/nautilus_trader/blob/develop/crates/analysis/src/statistic.rs>) is a well-designed extension point:

```rust
pub trait PortfolioStatistic: Debug {
    type Item;
    fn name(&self) -> String;
    fn calculate_from_returns(&self, returns: &Returns) -> Option<Self::Item> { … }
    fn calculate_from_realized_pnls(&self, realized_pnls: &[f64]) -> Option<Self::Item> { … }
    fn calculate_from_orders(&self, orders: Vec<Box<dyn Order>>) -> Option<Self::Item> { … }
    fn calculate_from_positions(&self, positions: &[Position]) -> Option<Self::Item> { … }
    fn calculate_from_returns_with_benchmark(&self, returns: &Returns, benchmark: &Returns) -> Option<Self::Item> { None }
    // + align_returns, check_valid_returns, downsample_to_daily_bins, calculate_std
}
```

Two details QMF should steal:

- **Four input shapes, not one.** A statistic declares whether it consumes a returns series, realized PnLs, orders, or positions. Win rate wants positions; Sharpe wants returns; expectancy wants realized PnLs. Forcing everything through "a returns series" is why so many Python metric libraries mis-handle trade-level statistics.
- **Benchmark-relative statistics return `None` by default, deliberately.** The doc comment: "The `None` default lets analyzer loops filter results by `Option` — non-benchmark statistics are simply skipped … rather than panicking." Only beta, alpha, information ratio, tracking error and Treynor ratio override it.

Also note the documented convention in `downsample_to_daily_bins`: intraday returns are compounded geometrically within each UTC day via `(1 + r1)(1 + r2) - 1` before any daily-frequency statistic is computed, and `align_returns` **inner-joins** strategy and benchmark on shared daily timestamps — "Timestamps present in only one series are dropped (not zero-filled)." `calculate_std` uses Bessel's correction and returns `NaN` for n < 2. These are exactly the decisions that silently differ between metric libraries and make two Sharpe numbers disagree.

---

### 9. statsmodels — cointegration, regressions. Use directly, do not wrap deeply.

PyPI `statsmodels` **0.14.6**, `requires_python >= 3.9`, Modified BSD (3-clause). The stable, boring, correct choice; no maintenance concerns.

The pairs-trading primitive (<https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.coint.html>):

```python
statsmodels.tsa.stattools.coint(y0, y1, trend='c', method='aeg',
                                maxlag=None, autolag='aic', return_results=None)
```

- Implements the **augmented Engle–Granger two-step** test (`method='aeg'` is the only option).
- Null hypothesis: **no cointegration**, between series assumed I(1).
- Returns `(coint_t, pvalue, crit_value)` — t-statistic of the unit-root test on the first-stage residuals, MacKinnon (1994) asymptotic p-value, and a dict of 1%/5%/10% critical values.
- `trend` ∈ {`"c"`, `"ct"`, `"ctt"`, `"n"`}; `autolag` ∈ {AIC, BIC, t-stat, None}.

Two caveats QMF should encode rather than leave to the strategy author: Engle–Granger is **order-dependent** (`coint(y0, y1)` ≠ `coint(y1, y0)`), and repeated testing across a universe of pairs is a multiple-comparisons machine — a raw p-value < 0.05 over 28 major FX pairs is not evidence of anything.

---

### 10. Walk-forward and data-splitting utilities

| Tool | What it gives | Status |
|---|---|---|
| `sklearn.model_selection.TimeSeriesSplit` | expanding-window CV with `gap` | core scikit-learn, permanently maintained |
| `skfolio.model_selection.WalkForward` | rolling/expanding walk-forward with purging | active (<https://skfolio.org/>) |
| `skfolio.model_selection.CombinatorialPurgedCV` | multiple testing paths, López de Prado style | active |
| `vectorbt.generic.splitters` | Rolling / Expanding / Range splitters | active, **Commons Clause licence** |
| `eslazarev/purged-cross-validation` | purging, embargo, CPCV, deflated Sharpe | **UNVERIFIED** (GitHub API rate-limited) |
| `mlfinlab` (Hudson & Thames) | PurgedKFold, CPCV | **NOT OPEN SOURCE — avoid** |

**sklearn** (<https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html>):

```python
TimeSeriesSplit(n_splits=5, *, max_train_size=None, test_size=None, gap=0)
```

"In the k-th split, it returns the first k folds as the train set and the (k+1)-th fold as the test set"; "Successive training sets are supersets of those that come before them." `gap` (added 0.24) is "Number of samples to exclude from the end of each train set before the test set" — the minimal leakage guard. This is *expanding-window* only; there is no fixed-size rolling mode.

**skfolio** (<https://skfolio.org/generated/skfolio.model_selection.WalkForward.html>) is the better fit for trading:

```python
WalkForward(test_size, train_size, freq=None, freq_offset=None, previous=False,
            expend_train=None, reduce_test=False, purged_size=0, *, expand_train=None)
```

You specify *window lengths*, not a split count — "making it more practical for portfolio backtesting scenarios." `freq` accepts calendar strings ("MS" = month start) against a `DatetimeIndex`, so you can say "retrain monthly on 24 months" directly. `purged_size` "Removes N observations between training and test to avoid look-ahead bias". `expand_train` toggles anchored vs rolling. Note `expend_train` is a legacy misspelling kept for compatibility alongside the correct `expand_train` — a small API wart to hide behind a QMF wrapper.

`CombinatorialPurgedCV` yields "k-p folds for training with p>1 test folds, allowing multiple testing paths to be recombined … unlike KFold which generates a single testing path" — the distribution-of-outcomes approach rather than a single equity curve.

**mlfinlab — explicit avoid.** Its own licence documentation states the codebase "is licensed under an all rights reserved licence and is **NOT open-source**, and may not be used for commercial purposes without a commercial license which may be purchased from Hudson and Thames Quantitative Research" (<https://github.com/hudson-and-thames/mlfinlab/blob/master/docs/source/additional_information/license.rst>). Many blog posts still recommend it as if it were free. It is not.

---

### 11. talipp — the only real pure-Python incremental indicator library

<https://github.com/nardew/talipp> — MIT, 534 stars, 31 open issues, `pushed_at` **2025-09-09**. Releases: 2.4.1 (2025-02-09), 2.4.2 & 2.5.0 (2025-03-16), 2.6.0 (2025-07-25), **2.7.0 (2025-09-09)**. **~11 months without a release as of 2026-08-17** — slowing, not dead, no deprecation notice in the README. A `quantstation-dev/talipp` fork exists but is **archived** and last pushed 2024-01-02; not an alternative.

The API is the most complete CRUD-over-a-series model available in Python:

```python
from talipp.indicators import EMA, SMA

ema = EMA(period=3, input_values=[1, 3, 5, 7, 9, 2, 4, 6, 8, 10])
ema.add(11)          # append a new closed bar
ema.update(15)       # revise the LAST input value  <- forming-bar support
ema.remove()         # drop the most recent value
ema.purge_oldest(1)  # drop N oldest values
```

`update()` is the interesting one: it is TA-Lib's planned `Peek` in mutable form, and it is what lets an indicator track a *forming* bar tick-by-tick without committing a wrong closed-bar value. `purge_oldest()` bounds memory for a long-running live process.

Performance claims from the README: "For batch processing talib is a clear winner", but "talipp scales linearly with input size compared to quadratic curve of talib when incremental operations are concerned" — for 50k inputs, "~200ms vs. ~6800ms". That quadratic curve is precisely the `talib.stream` O(n)-per-bar behaviour verified in §1e. **These are vendor benchmarks, unaudited.**

Coverage is ~50+ indicators including the full MA family (ALMA, DEMA, EMA, HMA, KAMA, SMA, SMMA, T3, TEMA, VWMA, WMA, ZLEMA), MACD, RSI, StochRSI, ATR, ADX, Bollinger, Keltner, Donchian, Ichimoku, SuperTrend, Parabolic SAR, VWAP, ZigZag. Wide enough for a first-generation FX strategy library; narrower than TA-Lib's 150+.

**No claim of numerical parity with TA-Lib.** Independent implementation, independent seeding choices. Any QMF use requires a parity test against TA-Lib per indicator, and where they differ, a documented decision about which is canonical.

---

### 12. Consolidated maintenance table (as of 2026-08-17)

| Library | Latest | Date | Signal | Verdict |
|---|---|---|---|---|
| TA-Lib C (`TA-Lib/ta-lib`) | 0.7.1 | 2026-07-03 | pushed 2026-08-17 | **ADOPT** |
| `ta-lib-python` | 0.7.1 | 2026-07-16 | pushed 2026-07-29; wheels Py3.9–3.14 | **ADOPT** |
| `polars_talib` (Yvictor) | — | pushed 2026-06-04 | 247★, binds TA-Lib C | **ADOPT (research path)** |
| `polars_ta` (wukan1986) | — | pushed 2026-02-11 | 260★, reimplementation | Evaluate |
| `pandas-ta-classic` | 0.6.52 | 2026-06-24 | linked from ta-lib.org | **ADOPT (optional)** |
| `pandas-ta` (original) | 0.4.71b0 | 2025-09-14 | repo 404, PyPI wiped, site dead | **AVOID** |
| `ta` (bukosabino) | 0.11.0 | 2023-11-02 | 43 indicators, ~2.8 yr no release | Avoid |
| `tulipy` | — | 2019-04-11 | self-declared unmaintained | **AVOID** |
| `talipp` | 2.7.0 | 2025-09-09 | ~11 mo quiet, MIT, no notice | **ADOPT WITH CARE** |
| NautilusTrader | — | pushed 2026-08-17 | 25.7k★, LGPL-3.0, Cython→Rust migration live | **STUDY / selectively adopt** |
| `quantstats` | 0.0.81 | 2026-01-13 | pushed 2026-07-20, Apache-2.0 | **ADOPT (research only)** |
| `quantstats-lumi` | 1.1.5 | ~2026-06-01 | last commit 2026-05-31 | Adopt for `metrics_json` idea |
| `empyrical` | 0.5.5 | 2020-10-13 | Py2.7 classifiers | **AVOID** |
| `empyrical-reloaded` | 0.5.12 | 2025-06-01 | ~14 mo quiet | Not needed |
| `statsmodels` | 0.14.6 | — | BSD-3, core scientific stack | **ADOPT** |
| `scikit-learn` | — | — | `TimeSeriesSplit` | **ADOPT** |
| `skfolio` | — | active | WalkForward, CombinatorialPurgedCV | **ADOPT** |
| `vectorbt` | — | pushed 2026-08-02 | **Apache-2.0 + Commons Clause** | Licence decision required |
| `mlfinlab` | — | — | all rights reserved, no commercial use | **AVOID** |

---

## What QMF should copy / avoid

### COPY: one definition, two modes — with incremental as the source of truth

**The decision:** every QMF indicator is defined **once**, in incremental form. The "vectorized" research mode is a replay driver over that same definition, not a second implementation.

This is not a theoretical preference. LEAN ships it (`qb.indicator_history()` "resets your indicator, makes a history request, and updates the indicator with the historical data"), Nautilus ships it (historical bars from `request_bars()` flow through the same `handle_bar` as live bars), and TA-Lib is building it in C (`TA_<NAME>_OpenAndFill` returns the full history array *and* a live stream from one call). Three independent mature projects converged on the same answer.

Concretely, the QMF interface — modelled on the Nautilus trait, with LEAN's window idea and TA-Lib's stream vocabulary:

```python
class Indicator(Protocol):
    name: str
    def handle_bar(self, bar: Bar) -> None: ...   # commit a CLOSED bar (TA-Lib: Update)
    def peek(self, bar: Bar) -> float | None: ...  # evaluate a FORMING bar, no state change
    def reset(self) -> None: ...
    @property
    def has_inputs(self) -> bool: ...             # seen any data
    @property
    def initialized(self) -> bool: ...            # seen ENOUGH data
    @property
    def warmup_bars(self) -> int: ...             # lookback + unstable_period + 1
    @property
    def value(self) -> float: ...
```

Plus one QMF-owned replay function that is the *only* way research gets a column:

```python
def replay(indicator: Indicator, bars: Iterable[Bar]) -> pl.Series: ...
```

**Then enforce it with a test, not a convention.** For every indicator, a property test asserts `replay(ind, bars)[-1] == ind_driven_live_value` and, where a TA-Lib equivalent exists, `replay(ind, bars) ≈ talib.FUNC(array)` within a documented tolerance. Nautilus PR #4718 is instructive here: they had to move from `f64::EPSILON` exact equality to scaled relative+absolute tolerances. Do not start with exact equality.

### COPY: register-then-warm-then-subscribe, as an enforced sequence

Nautilus's ordering — register indicators → `request_bars(callback=subscribe)` → live stream — should be a QMF invariant the strategy author cannot get wrong, not a documented best practice they can forget. In a solo-operator system with LLM-authored strategies, "the agent forgot to warm up the indicator" must be impossible by construction.

Pair it with `indicators_initialized()`: a single engine-level guard the strategy checks once at the top of `on_bar`.

### COPY: separate `has_inputs` from `initialized`, and make `reset()` mandatory

Cheap to implement, and it eliminates a whole class of "acted on a half-warm RSI" bugs. `reset()` is non-negotiable for deterministic replay.

### COPY: TA-Lib's numerical-stability vocabulary into QMF's indicator metadata

Every QMF indicator declares a `stability` field with TA-Lib's four values: `start_independent`, `initial_unstable_period`, `depends_on_ma_type`, `path_dependent`.

Then act on it:
- `start_independent` → warm-up is just `lookback`. Safe.
- `initial_unstable_period` → warm-up is `lookback + unstable_period`. QMF should **set an explicit unstable period and record it in strategy metadata**, so a backtest and a live run provably use the same setting. Default of `0` is a silent-drift generator.
- `path_dependent` → **QMF should warn loudly at strategy-registration time.** For `SAR` and `AD`, backtest results are a function of the start date, permanently. TA-Lib's own words: "Start a day earlier and it can pick the opposite direction, putting the stop on the other side of price for the rest of the run." An LLM agent proposing a SAR-based strategy needs this flagged.

Because `TA_SetUnstablePeriod` is **global process state** and must be set single-threaded before any concurrent calls, QMF should set it once at engine start from configuration and refuse to change it thereafter.

### COPY: the metadata triple `(input_names, param_names, output_names)` + `lookback`

TA-Lib's Abstract API and vectorbt's IndicatorFactory independently landed on the same decomposition. Make it QMF's indicator-registry schema. For TA-Lib-backed indicators, **generate the registry from `Function(name).info` rather than hand-writing it** — that is ~150 indicators of accurate, parameter-range-checked metadata for free, and it is exactly the constrained, discoverable surface an LLM strategy author needs. TA-Lib's own docs name this use case: "'Mutating' the function and its parameters while searching for strategies."

### COPY: the four-input-shapes idea for performance statistics

Nautilus's `PortfolioStatistic` takes `returns` / `realized_pnls` / `orders` / `positions`, and benchmark-relative statistics return `None` by default so analyzer loops filter rather than panic. Forcing everything through a returns series is why trade-level metrics (win rate, expectancy, payoff ratio) are so often subtly wrong in Python metric libraries.

Also copy the two conventions Nautilus wrote down explicitly, because they are the ones that make two Sharpe numbers disagree: geometric compounding of intraday returns into daily bins before computing daily-frequency statistics, and **inner-join** (not zero-fill) when aligning strategy against benchmark.

### COPY: a machine-readable metrics contract

`quantstats_lumi`'s `reports.metrics_json(..., summary_only=True)` with a documented `TEARSHEET_METRICS_CONTRACT.md`, percentages as raw decimals (`0.0369`, not `"3.69%"`), and a `custom_metrics` merge hook — that is the right shape for a QMF backtest result an LLM agent will read. QMF should emit its own equivalent regardless of which metrics library it wraps.

### WRAP: TA-Lib, behind a narrow QMF surface

TA-Lib is the batch engine. It is BSD-3, actively maintained, wheels everywhere, 150+ functions, has authoritative metadata, and its numerical semantics are now formally documented. But its Python surface (positional numpy arrays, `NaN` padding, global unstable-period state, `MA_Type` integer enums) is not a surface to hand an LLM.

Wrap it. The wrapper owns: warm-up arithmetic, unstable-period configuration, NaN-trimming policy, Polars-native I/O (via `polars_talib` where possible), and the metadata registry.

### WRAP OR VENDOR: incremental indicators

Two viable routes, and this needs an operator decision (see Open Questions):

- **(a) Depend on `talipp`.** MIT, ~50 indicators, true O(1), and its `update()`/`remove()` are the only Python implementation of forming-bar revision. Risk: single maintainer, ~11 months without a release.
- **(b) Hand-write ~15 indicators inside QMF**, following the Nautilus EMA pattern (~40 lines each). Risk: your own bugs. Benefit: zero dependency risk, exact control over seeding so TA-Lib parity is achievable by construction, and full ownership of the `peek()` semantics.

Given QMX is solo-operated and a first-generation FX strategy library needs maybe EMA, SMA, RSI, ATR, ADX, MACD, Bollinger, Donchian, Keltner, Stochastic and a couple of stops, **(b) with `talipp` as a cross-check oracle in tests** is the lower-risk path. Vendoring ~600 lines you fully understand beats a dependency that could go quiet.

### AVOID, unambiguously

- **`pandas-ta` (original).** Repo 404, PyPI history wiped, maintainer changed without communication, homepage DNS dead, unresolved community supply-chain concerns. Not a maintenance question — a trust question. Use `pandas-ta-classic` if a pandas indicator library is wanted at all.
- **`tulipy`.** Self-declared unmaintained, last touched 2019.
- **`ta` (bukosabino).** No release since 2023-11-02; 43 indicators; superseded on every axis.
- **`empyrical`.** 2020, Python 2.7 classifiers, dead parent company. Its metrics are a subset of quantstats and Nautilus.
- **`mlfinlab`.** Not open source; commercial use requires a paid licence. Widely mis-recommended.
- **`talib.stream` as a live engine.** Verified from `tools/generate_stream.py`: passes the full array with `startIdx == endIdx == length - 1`. O(n) per bar, O(n²) per session. Useful only as "batch without the output allocation".
- **Two independent implementations of the same indicator.** The failure mode this whole document exists to prevent.

### CONDITIONAL

- **`vectorbt`** — technically excellent for parameter sweeps and its splitters are good, but **Apache-2.0 + Commons Clause forbids "Sell"**, defined broadly enough to cover a product whose value derives substantially from it. Operator decision required before it enters a shipped dependency list. Personal research use is almost certainly fine.
- **`quantstats`** — adopt for research tearsheets; **do not install on the trading VPS.** It pulls matplotlib, seaborn, and yfinance. Keep the live process dependency-minimal; compute live metrics from QMF's own statistics module and generate tearsheets offline.
- **NautilusTrader** — the architecture is the best available reference and should be studied closely. Actually depending on it is a much larger decision (LGPL-3.0, a live Cython→Rust migration, and it wants to own the whole event loop). If QMF ever adopts Nautilus as its engine, its indicator and analysis layers come along and most of this document's "build it" recommendations collapse into "use theirs".

### Where the thin QMF abstraction genuinely earns its keep

Only in four places. Everywhere else, call the library directly.

1. **`Indicator` protocol + `replay()` driver.** Guarantees backtest and live compute identical numbers, structurally. Highest value in this entire document.
2. **Warm-up arithmetic.** `warmup_bars = lookback + unstable_period + 1`, computed from metadata, enforced by the engine, identical in backtest and live. Removes the most common silent-divergence bug.
3. **Indicator registry / metadata surface.** Generated from TA-Lib's Abstract API where possible, hand-declared otherwise, carrying `stability` and `warmup_bars`. This *is* the constrained surface LLM agents author against.
4. **A stable metrics contract.** One QMF-owned JSON shape for backtest results, so swapping quantstats for something else later does not break every downstream consumer or agent prompt.

Do **not** abstract over: statsmodels (`coint` is already a clean function), sklearn/skfolio splitters (already sklearn-compatible protocols), or Polars itself.

---

## Open questions

1. **Incremental indicators: vendor `talipp`, or hand-write ~15 inside QMF?** My recommendation is hand-write with `talipp` as a test oracle, but this is an operator call on dependency risk vs. code ownership. Trigger for revisiting: a `talipp` 2.8 release, or 18 months of silence.

2. **What is QMF's canonical numerical definition for recursive indicators?** TA-Lib seeds EMA with an SMA of the first `period` values; Nautilus seeds with the first value. They will never agree bit-for-bit. QMF must pick one, document it, and make every implementation conform. **This decision should be made before the first strategy is written, because changing it later invalidates every prior backtest.**

3. **What unstable-period policy?** TA-Lib offers three (ignore / supply extra history / `TA_SetUnstablePeriod`). Recommendation: option 2 — leave TA-Lib at `0` and have QMF's warm-up arithmetic drop the unstable prefix, so the policy lives in QMF code rather than global C state. Needs confirmation.

4. **Does QMX ship as a product?** This determines whether vectorbt's Commons Clause is a blocker. Same question governs any future GPL/LGPL dependency (NautilusTrader is LGPL-3.0).

5. **Is NautilusTrader QMF's engine, or only its reference architecture?** The answer collapses or expands roughly half the build recommendations above. Worth resolving before writing the indicator layer.

6. **Polars or pandas as the research dataframe?** If Polars, `polars_talib` gives TA-Lib parity plus `.over("symbol")` grouped evaluation, which is the right shape for a multi-pair FX book. If pandas, `pandas-ta-classic`. Choosing both is the expensive option.

7. **Forming-bar semantics for cTrader.** TA-Lib's planned API distinguishes `Update` (closed bar, irreversible) from `Peek` (forming bar, no commit); `talipp` uses `add()`/`update()`. **UNVERIFIED:** whether QMX's cTrader feed delivers explicit bar-close events or whether QMF must infer bar boundaries itself. This determines whether `peek()` is a core requirement or a later addition, and it is a data-layer question that needs answering before the indicator interface is frozen.

8. **UNVERIFIED items to close before implementation:**
   - Does `polars_talib` publish Windows wheels, and does it expose `TA_SetUnstablePeriod` / `Lookback`?
   - `noahbclarkson/polars-ta` maintenance state (GitHub API was rate-limited).
   - `eslazarev/purged-cross-validation` maintenance state and licence.
   - `pandas-ta-classic`'s actual indicator count (README says 224, PyPI summary says 193).
   - Whether the TA-Lib C 0.8.x streaming API has a published target date — it would materially change recommendation (b) in "Incremental indicators".

9. **Where do live performance metrics get computed?** If quantstats stays out of production (recommended), QMF needs a small live statistics module. Should it mirror Nautilus's 34-statistic set, or a deliberately smaller operator-facing set (Sharpe, max drawdown, win rate, expectancy, exposure)? Smaller is likely better for a non-technical operator, but it is a product decision, not a technical one.
