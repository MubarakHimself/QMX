# Spec: Interactive Charts (candlesticks + execution markers + indicator overlays, per-bot, JSON)

Reverse-engineered from Jesse (MIT, v3.0.6) and QuantConnect Lean (Apache-2.0). Mechanism understanding only — no third-party code is reused. This spec defines QMX's own renderer-agnostic **chart-data JSON contract**, emitted alongside the result artifact so our UI can render it later and quant agents can read the JSON directly.

---

## 1. Feature claim (verbatim, with URL)

**Jesse** — "Interactive Charts Overview", https://docs.jesse.trade/docs/charts/interactive-charts:
> "Interactive charts combine candlesticks, execution markers, and indicators drawn by your strategy. Backtests show the complete simulated history, while paper and live charts update as the session runs and remain available afterward."

Per-method claims (same page):
> `add_line_to_candle_chart()`: "Adds a time-series line on top of the candlestick chart"
> `add_horizontal_line_to_candle_chart()`: "Adds or updates a named horizontal level on the candlestick chart"
> `add_extra_line_chart()`: "Adds a time-series line to a separate indicator pane"
> Open Trade Chart "to review completed trades and their executions alongside price action"

Jesse changelog (https://docs.jesse.trade/docs/changelog) markets the whole capability as: "candlesticks, strategy indicators, horizontal levels, orders, and completed trades in synchronized charts across backtest, paper, and live sessions".

**Lean / QuantConnect** — Charting docs (quantconnect.com/docs/v2/writing-algorithms/charting):
> "We provide a powerful charting API that you can use to build many chart types."
> "A Candle series displays OHLC data as candlesticks."
> Series types: Line, Scatter, Candle, Bar, StackedArea, Treemap. Reserved chart names: Strategy Equity, Capacity, Drawdown, Benchmark, Portfolio Turnover. Custom charts allow "customizable units, colors, and marker symbols." Up to four indicators plotted at once.

---

## 2. Mechanism — how the code actually does it

### 2.1 Jesse — the payload IS the frontend library's data model

Jesse's chart JSON is not renderer-agnostic; it is shaped **exactly** for TradingView Lightweight-Charts (the marker fields `position: aboveBar|belowBar`, `shape: arrowUp|arrowDown`, `lineStyle` as integer `0=solid / 1=dotted`, and `series.update()` semantics are Lightweight-Charts conventions). The engine emits the data the JS widget ingests directly. This is the key design lesson QMX must *invert*.

**Where strategy chart data is captured** (`jesse/strategies/Strategy.py`):
- Four dict buffers initialised per strategy instance (lines 89–92): `_add_line_to_candle_chart_values`, `_add_extra_line_chart_values`, `_add_horizontal_line_to_candle_chart_values`, `_add_horizontal_line_to_extra_chart_values`.
- `add_line_to_candle_chart(title, value, color)` (Strategy.py:371) — validates the value is finite (`_validate_chart_value`, logs + skips NaN/inf, line 372), lazily creates the series with an auto hex color, then appends a point `{'time': int(current_candle[0]/1000), 'value': value, 'color': color}` (lines 379–384). **Time is candle-open ms floored to integer seconds.**
- `add_extra_line_chart(chart_name, title, value, color)` (Strategy.py:448) — same point shape, but nested two levels: `{chart_name: {title: {'data': [...], 'color': ...}}}`. Each `chart_name` is a **separate stacked pane**.
- `add_horizontal_line_to_candle_chart(title, value, color, line_width, line_style)` (Strategy.py:401) — stores a single mutable level `{'title','price','color','lineWidth','lineStyle'}`; `line_style` string is mapped to int `solid→0, dotted→1` (raises `ValueError` otherwise, line 409). Called again with same title → updates in place (line 411).
- `_store_chart_line_point` (Strategy.py:386): in **live** mode, if the last point shares the same `time`, it overwrites (idempotent per-bar update); otherwise appends. `_trim_chart_line_data` (line 393) caps live series at `LIVE_CHART_MAX_POINTS_PER_LINE` — backtests keep full history, live sessions are ring-buffered because "live sessions never end".

**Execution markers** (`_handle_executed_order_for_chart`, Strategy.py:521): on every filled order, appends to `_executed_orders`:
```
{'time': int(current_candle[0]/1000),
 'position': 'aboveBar' if SELL else 'belowBar',
 'color':    '#e91e63' if SELL else '#2196F3',
 'shape':    'arrowDown' if SELL else 'arrowUp',
 'text':     f'{side.upper()} • {position_type}',   # e.g. "BUY • LONG"
 'order_id': order.id}
```
`position_type` (LONG/SHORT) is derived from position state including the just-closed direction (previous_qty sign).

**Candle shape** (`_get_formatted_candles_for_frontend`, backtest_mode.py:336): each candle `{'time': int(c[0]/1000), 'open','close','high','low','volume'}`. Note Jesse's internal candle array order is `[timestamp, open, close, high, low, volume]` — high/low come *after* close.

**Assembly at backtest completion** (`backtest_mode.py` ~228–239). Only if `chart=True`, a single dict is built and persisted to the `BacktestSession` DB row (`chart_data` column, `update_backtest_session_results`, line 258):
```
chart_data = {
  'candles_chart':                      [ {exchange,symbol,timeframe, candles:[...]} , ... ],   # per route
  'orders_chart':                       [ {exchange,symbol,timeframe, orders:[...]} , ... ],
  'add_line_to_candle_chart':           [ {exchange,symbol,timeframe, lines:{title:{data,color}}} ],
  'add_extra_line_chart':               [ {exchange,symbol,timeframe, charts:{pane:{title:{data,color}}}} ],
  'add_horizontal_line_to_candle_chart':[ {exchange,symbol,timeframe, lines:{title:{price,color,lineWidth,lineStyle}}} ],
  'add_horizontal_line_to_extra_chart': [ {exchange,symbol,timeframe, lines:{pane:{title:{...}}}} ],
}
```
It is a **list-of-routes per chart category** (one entry per bot/route: exchange-symbol-timeframe).

**Read-back / selection API** (`backtest_controller.get_backtest_session_chart_data`, line 250; POST `/backtest/sessions/{id}/chart-data`, auth-gated). Client sends `{exchange,symbol,timeframe}`; the controller:
1. `json.loads(session.chart_data)` then scrubs it: `jh.clean_nan_values(jh.clean_infinite_values(...))` (line 262) — NaN/inf → `null` so JSON is strict-valid.
2. `route_item(...)` picks the one route matching the requested key (line 269).
3. Returns `null` if that route has no candles (line 278).
4. **Sorts on read**: candles by `int(time)` (line 295); orders by `(int(time), order_id)` for stable ordering (line 296).
5. Emits a flattened per-route payload (verified by `tests/test_backtest_session_chart_data.py`):
```
chart_data = {
  'route': {exchange,symbol,timeframe},
  'candles': [ {time,open,close,high,low,volume}, ... ],          # sorted asc
  'orders':  [ {time,position,color,shape,text,order_id}, ... ],  # sorted asc
  'strategy_charts': {
     'lines':                 {title: {data:[{time,value,color}], color}},   # overlays on candle pane
     'horizontal_lines':      {title: {price,color,lineWidth,lineStyle,title}},
     'extra_charts':          {pane:  {title: {data:[...], color}}},         # separate panes
     'horizontal_extra_lines':{pane:  {title: {price,...}}},
  }
}
```
Transport: FastAPI `GZipMiddleware`, `minimum_size=1024, compresslevel=5` (compresses large chart payloads).

**Live mode** uses a parallel path. `LiveChartSeries`/`LiveChartPoint` peewee tables (`models/LiveChart.py`) persist series metadata + points to SQLite so a page reload can rehydrate; `services/report.py` exposes `strategy_charts()` (full snapshot, line 140) and `strategy_charts_updates()` (last point per line only, line 160) — the latter is "small enough to publish on every dashboard tick; the frontend applies it idempotently with `series.update()`". Live equity is a separate stream (`LiveEquitySnapshot`).

**Equity curve** (`services/charts.py:547`, `equity_curve()`): returns a list of series each `{'name', 'color', 'data':[{'time': date.timestamp(), 'value': balance, 'color'}]}`. Portfolio first (color `#818CF8`), then one per benchmark route; a fixed 10-color palette with `_generate_color()` (line 531) rotating RGB +50 mod 256 past 10 routes. This is the `[{name,color,data:[{time,value}]}]` shape.

**PNG fallback** (`services/charts.py:170`, `_plot_backtest_charts`): matplotlib `Agg` backend renders **six** standalone PNGs — `equity_curve, cumulative_returns, drawdown, underwater, monthly_heatmap, monthly_distribution, trade_pnl` (names in `_BACKTEST_CHART_NAMES`, line 17) — saved as `{session_id}_{chart_name}.png`. Full light/dark theme dicts (lines 20–61). These are **portfolio-analytics** charts (equity, drawdown, monthly heatmap via `TwoSlopeNorm` RdYlGn, KDE distributions via `scipy.gaussian_kde`), NOT the candlestick chart. Frontend is notified via `sync_publish('charts_image_ready', {session_id})`. So Jesse has **two disjoint chart systems**: interactive JSON (price + executions + indicators) and static PNG (portfolio stats).

### 2.2 Lean — a typed, sampled, delta-streamed chart model

Lean's chart model is a proper object graph, serialized to a compact JSON, and (critically) **downsampled** and **delta-streamed**. Files under `Common/`:

**Object graph:**
- `Chart` (Chart.cs:30) — `{Name, Series: Dictionary<string,BaseSeries>, Symbol?, LegendDisabled}`. `ChartType` (Overlay/Stacked) is **obsolete** (line 38) — replaced by per-series `Index` (which pane) and `ZIndex` (line 47, 59). `GetUpdates()` (line 157) returns only new points since last fetch.
- `BaseSeries` (BaseSeries.cs:29) — `{Name, Unit="$", Index, IndexName?, ZIndex?, SeriesType, Tooltip?, Values: List<ISeriesPoint>}`. `AddPoint` overwrites the last point if the incoming `Time` equals the last (line 141) — same idempotent-per-timestamp rule as Jesse live. `GetUpdates()` (line 163) tracks `_updatePosition` and returns only the delta — this is how Lean streams growing charts cheaply.
- `SeriesType` enum (BaseSeries.cs:259): Line=0, Scatter=1, Candle=2, Bar=3, Flag=4, StackedArea=5, Pie=6, Treemap=7, Heatmap=9, Scatter3d=10.
- `Series : BaseSeries` (Series.cs:31) — adds `Color` and `ScatterMarkerSymbol` (enum: none/circle/square/diamond/triangle/triangle-down, serialized as strings, Series.cs:217). Value points are `ChartPoint` (or `ScatterChartPoint` for scatter).
- `CandlestickSeries : BaseSeries` — value points are `Candlestick`.

**Point types & wire format (the compact array trick):**
- `ChartPoint` (ChartPoint.cs) — `x` = **long unix seconds** (line 45, `DateTimeToUnixTimeStamp`), `y` = `decimal?` passed through `SmartRounding()` (line 78). Serialized by `ChartPointJsonConverter` as a **2-element array `[x, y]`** (line 76) — "Lower case for javascript encoding simplicity" (line 52). Reader accepts both `[x,y]` array and `{x,y}` object (backward compat).
- `Candlestick` (Candlestick.cs:27) — `{Time, Open, High, Low, Close}` all `decimal?` + `SmartRounding` (lines 54–85). `LongTime` = unix seconds (line 43). Serialized by `CandlestickJsonConverter` as a **5-element array `[time, open, high, low, close]`** (line 43–51). Reader (line 57) tolerates: object form, a ≤2-element array (treats as flat ChartPoint → OHLC all = y, for old equity charts), or full 5-element. `Update(value)` (line 183) aggregates a streaming value into OHLC.
- `Series` JSON (`SeriesJsonConverter.cs:38`): `{name, unit, index, seriesType, [zIndex], [indexName], [tooltip], values:[...], color, scatterMarkerSymbol}`. Pie is special-cased to a single consolidated point (line 79). `seriesType` serialized as its **integer** enum value.

**Result carriage:** charts live as `IDictionary<string, Chart>` on `Result` (Result.cs:36), `BaseResultParameters` (line 37), the API `Backtest`/`LiveAlgorithmResults` (Backtest.cs:149), and `BaseResultsHandler.Charts` is a `ConcurrentDictionary<string,Chart>` (BaseResultsHandler.cs:187). So the backtest result JSON carries a top-level `"Charts": { chartName: {name, series:{...}} }`.

**Downsampling before emit** — `SeriesSampler` (SeriesSampler.cs). Constructed with a target resolution `Step` (TimeSpan). `SampleCharts` (line 88) walks every chart/series and resamples to the desired resolution; `SubSample` flag (line 37) controls whether to interpolate finer or just thin. This is why Lean can chart multi-year minute backtests without shipping millions of points — the result handler samples to a screen-appropriate density. Candlestick series get a dedicated `SampleCandlestickSeries` (line 75) that correctly re-aggregates OHLC per bucket rather than naively dropping points.

**Delta streaming for live/long backtests:** `Chart.GetUpdates()` + `Series.GetUpdates()` + `BacktestingResultHandler.SplitPackets` (BacktestingResultHandler.cs:277) chunk `deltaCharts` into result packets so the UI receives incremental series growth, not full re-sends.

**Report rendering** (`Report/ReportElements/ChartReportElement.cs`): the C# report engine does NOT render charts in C#. It boots Python (`PythonInitializer`, `Py.GIL()`) and imports a `ReportCharts` Python module (line 35) — matplotlib-based — to render the static PDF/HTML report. So Lean, like Jesse, has a **live/interactive JSON model** (consumed by the JS webapp) and a **separate static matplotlib report** path.

### 2.3 Shared mechanism truths (both engines)

- **Time = integer unix seconds** on the wire, everywhere (Jesse `int(ms/1000)`, Lean `long` seconds). Neither ships ns or ms in the chart payload.
- **Idempotent-per-timestamp append**: last point overwritten if same time (Jesse `_store_chart_line_point`, Lean `BaseSeries.AddPoint`). Enables live tick updates without duplicate bars.
- **Panes via index, not chart-type**: Lean uses `Series.Index`/`ZIndex`; Jesse uses named `extra_charts`. Overlays (indicators on the price pane) vs stacked sub-panes (RSI, ADX) is a first-class concept in both.
- **NaN/inf are scrubbed to null** before serialization (Jesse `clean_nan_values`; Lean `SmartRounding` + nullable decimals).
- **Compaction**: Lean packs points as positional arrays (`[x,y]`, `[t,o,h,l,c]`); Jesse uses named objects but gzips the response. Both fight payload size — Lean structurally, Jesse at transport.
- **Downsampling**: only Lean does it (`SeriesSampler`). Jesse ships full backtest history and trims only live series by count. **This is Jesse's scalability gap.**

---

## 3. Jesse vs Lean — which fits QMX

| Dimension | Jesse | Lean | QMX choice |
|---|---|---|---|
| Data shape | Named-object points, TradingView-coupled | Typed graph, positional-array points, integer enums | **Lean-style typed model, but renderer-agnostic names** (not TradingView field names). |
| Panes | Named `extra_charts` dicts | `Index`/`ZIndex` per series | **Lean's numeric pane index** — cleaner for arbitrary panes, agent-legible. |
| Point time | int seconds | long seconds | Wire = int seconds, but **carry ns-precision open time too** (QMF UTC-ns law). |
| Payload size | Full history + gzip | `SeriesSampler` downsample + delta packets | **Adopt Lean's sampling** — mandatory for 12–14 concurrent long backtests. |
| Markers | Rich (position/shape/text/color/order_id) | Scatter series w/ marker symbol | **Adopt Jesse's marker richness**, decoupled from TradingView vocab. |
| Emit trigger | On completion → DB blob; live via WS + SQLite | Result handler packets | QMX: **emit JSON artifact at completion** (batch), keep live streaming out of scope v1. |
| Money in points | float | decimal + SmartRounding | **QMF exact integer money** — see §4. |
| Coupling | Payload = frontend model (bad) | Payload = domain model, converters isolate wire form | **Lean's separation** — domain model + explicit wire serializer. |

**Verdict.** Take Lean's architecture (typed series graph, positional wire encoding, SeriesSampler downsampling, converter-isolated wire form, pane-by-index) and Jesse's execution-marker richness and per-bot slicing. **Reject** Jesse's frontend coupling and its no-downsampling policy. QMX's payload must be a *domain* artifact a quant agent can `json.load` and reason over — never TradingView's private data model.

---

## 4. QMX spec draft — the chart-data JSON contract

QMX emits **one chart-data JSON artifact per Book/BMS run, per bot (route)**, written into the ledger alongside the result artifact at run completion. Renderer-agnostic: our UI renders it later; agents read it directly. The CLI is config-driven — chart emission is a config toggle on the Book (wind-tunnel: flip the variable, same tunnel), default on for backtest/replay.

### CH-1 — Artifact identity & placement
- CH-1.1 One artifact per (run_id, bot_id) where bot_id = the route key (venue-symbol-timeframe). Multi-bot runs emit N artifacts (or one keyed map) — **never** collapse bots into one series set.
- CH-1.2 Written to the run's ledger directory at completion, next to the pass/fail result. Filename deterministic, includes run_id + bot_id.
- CH-1.3 Logged incrementally *during* the run is out of scope for v1; the artifact is a **completion snapshot** (matches operator's "logged during runs, saved at completion" — charts are in the saved set).

### CH-2 — Top-level shape
```
{
  "schema_version": "qmx.chart/1",
  "run_id": "...", "bot_id": "venue:symbol:timeframe",
  "world": "live" | "replay" | "simulated",      // QMF result-label law — mandatory
  "time_unit": "unix_seconds",                     // wire unit declared, not assumed
  "price_scale": <int>,                            // 10^n integer-money scale (see CH-6)
  "candles": Candle[],
  "markers": Marker[],                             // execution markers
  "overlays": Series[],                            // indicator lines ON the price pane
  "levels": Level[],                               // horizontal lines on price pane
  "panes": Pane[]                                  // extra stacked sub-panes
}
```
- CH-2.1 `world` MUST be present and MUST equal the run's result label (QMF law: every result labeled live/replay/simulated). A renderer MUST surface it.
- CH-2.2 `schema_version` MUST be present; consumers reject unknown majors.

### CH-3 — Candles
- CH-3.1 `Candle = [t, o, h, l, c, v]` positional array (Lean-style compaction), `t` = unix seconds (bar open), OHLCV as integer-scaled money (CH-6). Order is O,H,L,C,V — **not** Jesse's O,C,H,L,V (avoid that footgun; document explicitly).
- CH-3.2 Candles sorted ascending by `t`; no duplicate `t`. A gap in `t` is permitted (missing bars) and MUST NOT be interpolated.
- CH-3.3 Candles are the price pane's base layer for this bot only (the bot's traded symbol/timeframe).

### CH-4 — Execution markers
- CH-4.1 `Marker = {t, side, effect, price, qty, order_id, label}` where `side ∈ {buy,sell}`, `effect ∈ {open,increase,reduce,close}` (richer than Jesse LONG/SHORT text; derived from position delta like Strategy.py:558). `price`/`qty` integer-scaled.
- CH-4.2 Renderer-agnostic placement: emit semantic `side`/`effect`, NOT TradingView `position:aboveBar` / `shape:arrowUp`. The UI derives glyph/position from side+effect. (Explicitly reject Jesse's frontend-coupled fields.)
- CH-4.3 `order_id` MUST join to the run's order/trade ledger (typed refusal if an emitted marker references a non-existent order — no orphan markers).
- CH-4.4 Sorted ascending by `(t, order_id)` for stable ordering (Lean/Jesse both do stable sort).

### CH-5 — Overlays, levels, panes (indicator drawing API)
- CH-5.1 `Series = {name, color?, unit?, points: [[t, y], ...]}` — positional `[t,y]` points, `y` integer-scaled if a price, raw decimal-as-string if a ratio/oscillator (unit declares which). NaN/inf → `null` y (CH-6.3).
- CH-5.2 `overlays[]` render on the price pane (moving averages, bands). `panes[] = {pane_index, title, series: Series[], levels: Level[]}` render as separate stacked sub-panes (RSI, ADX). Pane identity by **integer index** (Lean model), not by name-string lookup.
- CH-5.3 `Level = {title, price|value, color?, width?, style}` where `style ∈ {solid,dotted,dashed}` as a **string enum** (not Jesse's magic int 0/1 — agents read strings). Levels are mutable-by-title within a run (last write wins), matching both engines.
- CH-5.4 The strategy-facing drawing API (whatever the sandboxed agent calls) MUST validate every plotted value is finite at call time and emit a typed refusal / structured warning naming the series (Jesse `_validate_chart_value` pattern, Strategy.py:355) rather than silently poisoning the chart.
- CH-5.5 A point whose `t` equals the previous point's `t` overwrites it (idempotent-per-timestamp) — required so replay/live re-emits don't duplicate.

### CH-6 — QMF contract bindings
- CH-6.1 **Exact integer money**: all prices/PnL in chart points are integers at `price_scale` (10^n). No floats for money — reject Jesse's float points and Lean's decimal. Ratios/oscillators (non-money) carried as decimal strings with `unit` != money.
- CH-6.2 **UTC-ns time**: wire `t` is unix **seconds** for renderer compatibility, but each candle/marker MAY carry an optional `t_ns` (UTC nanoseconds) for exactness; when both present `t = floor(t_ns/1e9)`. The artifact declares `time_unit`. (Reconciles chart-lib reality with QMF ns law.)
- CH-6.3 **Typed refusals / clean nulls**: NaN/inf never serialized — scrub to `null` (Jesse `clean_nan_values`) and, at emit time, a typed warning records how many were dropped per series.
- CH-6.4 **Result labels**: `world` field (CH-2.1); a replay and a live run of the same bot produce distinguishable artifacts.
- CH-6.5 **No third-party engine code**: the serializer is QMX's own; the format borrows *ideas* (positional arrays, sampling) not code.

### CH-7 — Scalability (the Lean lesson Jesse lacks)
- CH-7.1 QMX MUST downsample series to a target density before writing the artifact (port the *idea* of `SeriesSampler`): candles re-aggregated OHLC per bucket, line series thinned. Full-resolution retention is a separate opt-in (config toggle on the Book).
- CH-7.2 Target load 12–14 concurrent runs: artifact size MUST be bounded (declare a max points/series after sampling); a multi-year minute backtest MUST NOT emit millions of raw candles by default.
- CH-7.3 Artifact SHOULD be gzip-compressible / stored compressed (Jesse's transport lesson).

### CH-8 — Agent consumability
- CH-8.1 The JSON MUST be self-describing (schema_version, time_unit, price_scale, world, units per series) so an agent needs no external context to interpret it.
- CH-8.2 Positional arrays MUST be documented in-schema (a `columns` legend for candles) so an agent parsing `[t,o,h,l,c,v]` isn't guessing column order.
- CH-8.3 One bot = one artifact keeps an agent's read scoped to the bot it's reasoning about (Jesse's per-route slicing on read, generalized to per-artifact).

---

## 5. Open questions

1. **Live/streaming charts** — v1 is a completion snapshot. Do QMX agents ever need mid-run chart deltas (Lean `GetUpdates`/`SplitPackets`, Jesse `strategy_charts_updates`), or is the logged result stream + final artifact enough? Streaming adds a delta-encoding + transport surface.
2. **Portfolio-analytics charts** — both engines ship a *separate* stats system (Jesse's 6 matplotlib PNGs; Lean's Python `ReportCharts`): equity curve, drawdown, underwater, monthly heatmap, PnL distribution. Is that a distinct spec (result/report artifact) or part of this chart contract? Recommend: **separate** — this spec is price+execution+indicator; equity/drawdown belong with the result/ledger metrics.
3. **Downsampling policy** — what target density (points per pane) balances agent-readability, UI render cost, and the 12–14 concurrent budget? Needs a number.
4. **Multi-bot correlation view** — when a Book runs N bots, does the UI ever need a synchronized multi-symbol view (shared time axis)? If so, artifacts need a shared time-origin guarantee, not just per-bot independence.
5. **price_scale per symbol** — one scale per artifact assumes one symbol per bot (true for a route). Confirm no cross-symbol overlay on a single price pane is ever needed (would break single integer scale).
6. **Marker glyph vocabulary** — CH-4.2 pushes glyph choice to the renderer from semantic side+effect. Does the agent-facing drawing API also let a strategy force an explicit shape/color (Jesse allows), or is semantic-only sufficient to keep artifacts renderer-agnostic?
7. **`t_ns` optionality** — is carrying both seconds and ns worth the size, or should the artifact commit to one and let the renderer convert? QMF ns law argues for ns as source of truth with seconds derived.
