# London Strategic Edge — official product reconnaissance

Research date: 2026-09-18. Sources were accessed at approximately 2026-09-18 08:30–08:35 UTC. This is a read-only, public-source study; no API key was entered, no account was created, and no job/trade/export was submitted.

## Source and access notes

| ID | Source | Classification | Access mode / limitation |
|---|---|---|---|
| S1 | https://londonstrategicedge.com/data/ | VENDOR_CLAIM / DOCUMENTED_CAPABILITY | Public HTML fetched; page says full platform requires JavaScript, so interactive controls were not observed. |
| S2 | https://londonstrategicedge.com/free-market-data-api/ | VENDOR_CLAIM / DOCUMENTED_CAPABILITY | Public HTML fetched; links to API/WebSocket docs, but those routes returned only a JS-gated shell. |
| S3 | https://londonstrategicedge.com/docs/api/ | DOCUMENTED_CAPABILITY (limited) | Public route fetched; no endpoint schema rendered in non-JS response. |
| S4 | https://londonstrategicedge.com/docs/websocket/ | DOCUMENTED_CAPABILITY (limited) | Public route fetched; no protocol schema rendered in non-JS response. |
| S5 | https://londonstrategicedge.com/backtest/ | VENDOR_CLAIM | Public HTML fetched; no run was submitted. |
| S6 | https://londonstrategicedge.com/machine-learning-studio/ | VENDOR_CLAIM | Public HTML fetched; no model/job was created or trained. |
| S7 | https://github.com/londonstrategicedge | REPOSITORY_SOURCE / association evidence | Official-looking organization page lists the product URL, support address, and four public repositories. |
| S8 | https://github.com/londonstrategicedge/lse-data/blob/main/README.md | REPOSITORY_SOURCE | Public README inspected. It is linked from the vendor organization and documents SDK surfaces. |
| S9 | https://github.com/londonstrategicedge/lse-terminal | REPOSITORY_SOURCE | Public README inspected. It is listed in the vendor organization. README claims are not independent runtime verification. |
| S10 | https://github.com/londonstrategicedge/brue | REPOSITORY_SOURCE | Public README inspected. It is listed in the vendor organization. |

The attached LSE browser-tab binding was accepted by the browser-control layer, but it did not return a usable accessibility/page state in this worker. Therefore there are no retained screenshots and no claim below is based on a successful UI click-through. This is an access limitation, not evidence that the features are absent.

## Journey LSE-DATA-001 — catalogue, coverage, metadata, preview and exports

**Classification: DOCUMENTED_CAPABILITY + VENDOR_CLAIM; interactive OBSERVED_INTERACTION unavailable.**

The public data page describes a databank with 133 billion ticks, 118,000 datasets and 27 asset classes. It lists stocks (3,979), options with greeks (3,186 US underlyings), 62 currency pairs, 58 cryptocurrencies, 54 futures, 25 ETFs, 23 commodities, 19 indices, 202 government-bond yield series and 14,640 macroeconomic series for 100+ countries, with some series back to 1900. It says users can browse datasets, preview rows, chart series, and download slices as Parquet or CSV with one key (S1).

The same page exposes product concepts named Overview, API & WebSocket, Dataset builder and Data Visualisation, and links guides for Parquet-to-CSV, Python loading, model training, live streaming and a data assistant (S1). These are visible page claims/navigation labels, not proof that each journey is available on every plan.

The API page documents a REST grammar naming an instrument, resolution and window, returning up to 5,000 rows, with pagination for longer ranges; examples use `client.candles(symbol, timeframe, start=...)`. It says JSON/CSV are supported and lists economic calendar, insider trades, dividends, splits and company profiles beyond candles (S2). The page claims a single WebSocket can stream covered asset classes, up to 16 symbols on the free key, and can replay recorded history before switching to live on the same connection (S2).

The official `lse-data` README provides more detailed documented surfaces: 14 candle resolutions from 1s through 1mo; REST reference feeds for economic calendar, insider trades, dividends, splits, COT positioning, financial reports, company profiles, fundamentals and bond yields; `datasets()` discovery; `history()`/`dataset()` bulk export jobs producing Parquet; and `GET /vault/usage` for allowance status (S8). The README describes a tick object containing symbol, price, bid, ask, volume, timestamp, name and replay flag, plus sync/async and callback/iterator streaming interfaces (S8).

**Backend-relevant evidence, without architecture inference:** the public SDK names resource operations (`candles`, `series`, `datasets`, `history`, `options`, `options_flow`, etc.), request windows/limits, an export-job abstraction for deep history, a usage/quota read, and a replay marker. These are interface facts; they do not establish the provider’s internal storage or execution architecture. The README’s mention of a “ClickHouse store” is a repository text claim, not independently verified here.

## Journey LSE-DATA-002 — live/history distinction and WebSocket

**Classification: DOCUMENTED_CAPABILITY / REPOSITORY_SOURCE; UNVERIFIED at runtime.**

S2 states that historical data is served over HTTP and live prices over WebSocket, with one key and a common symbol/resolution/window grammar. S8 documents `stream(..., start=...)` replay up to 24 hours followed by live ticks on the same connection, with each tick’s `replay` flag. S8 also documents dynamic subscribe/unsubscribe, option-chain subscriptions, async streaming and clean disconnect behavior.

No key was requested or entered, and no socket was opened. Thus connection authentication, message envelopes, replay ordering, reconnect behavior, quota exhaustion, symbol validation and actual availability remain **UNVERIFIED**.

## Journey LSE-DATA-003 — dataset builder / recipe concept

**Classification: VENDOR_CLAIM; UNVERIFIED interaction.**

S1 explicitly labels a “Dataset builder” and describes it as a computed CSV with indicators and features over a symbol and window. The page also offers a data assistant that answers dataset questions and returns code to pull data. No public form schema, recipe serialization, feature vocabulary, lineage/provenance record or job status contract was available in the fetched HTML. Do not infer that a builder is a general DAG or reusable workflow system.

## Journey LSE-BACKTEST-001 — strategy inputs, run and results

**Classification: VENDOR_CLAIM; REPOSITORY_SOURCE for Brue/terminal only; runtime UI UNVERIFIED.**

The public backtesting page claims indicator-based strategy definition (RSI, MACD, Bollinger Bands, moving averages and 20+ indicators), stop-loss/take-profit inputs, historical replay, equity curves, drawdown, win rate, profit factor, Sharpe ratio and a per-trade table (S5). A separate public marketing page claims a no-account flow and form/manual modes, but that page was not treated as runtime proof.

The official `brue` repository documents a small script language for trade entries/exits, with historical runs over local CSV and live broker calls through Brue Connect. It describes simulated next-bar-open fills, brackets, commission, slippage, trade records, log lines and canonical JSON; it explicitly says this package has no statistics block/equity frame, leaving result research to host-side Python (S10). This is important scope evidence: the repository implementation is narrower than the marketing page’s reported analytics.

The official `lse-terminal` README claims a Python workspace with a shared `strategy.py`, date ranges, walk-forward folds, Monte Carlo resamples, commission/slippage, trade list, equity curve, drawdown, Sharpe, Sortino, VaR and time-in-market; it also claims assistant actions such as pulling data, running backtests, building ML datasets, training models, reading positions/fills, running Python and editing workspace files (S9). These are repository README claims, not a completed UI observation or independent test.

No backtest was run. Inputs, validation, progress/cancel semantics, result comparison, chart annotation persistence, export format and failure states are **UNVERIFIED**.

## Journey LSE-ML-001 — ML Studio

**Classification: VENDOR_CLAIM; runtime UI and job contract UNVERIFIED.**

The ML Studio page advertises LSTM, XGBoost, CatBoost, LightGBM, Random Forest, Transformer, ARIMA, Prophet, GARCH, CNN and GAN models; customisable hyperparameters; “in depth” performance reporting; and dedicated GPU infrastructure (S6). The public data page offers a train-a-model guide (S1). The terminal repository separately names GARCH(1,1), Kalman filter, hidden Markov regimes, LSTM forecasts and an autoencoder for anomaly detection, fitted on the dataset in view and plotted next to a chart (S9).

There was no public schema for feature/label selection, train/validation/test splits, leakage controls, compute limits, experiment IDs, model artifacts, metric payloads, reproducibility, cancellation or connection from ML output into backtesting. Those are **UNVERIFIED**. Marketing claims about GPU infrastructure and model breadth must not be treated as availability or quality guarantees.

## Journey LSE-TOOLS-001 — macro/intermarket/reference tools

**Classification: DOCUMENTED_CAPABILITY + VENDOR_CLAIM.**

The data page’s coverage and guides include economic series, government yields, release calendars, COT positioning, company/fundamental/reference data and chart comparison (S1). The SDK README names `economics`, `series`, `economic_calendar`, `cot`, `bond_yields`, `fundamentals`, `financial_reports`, `company_profiles`, plus options chains/flow and option candles (S8). The page navigation includes an economic calendar and stock screener (S1); no screener schema or observed filter journey was available.

These facts support a composable research vocabulary of series, event/reference tables, symbol catalogs, chart comparisons and derived datasets. They do not prove that each source can be joined, aligned, transformed or passed into ML/backtests without extra work.

## Official-repository verification

S7 lists `londonstrategicedge/lse-data`, `lse-terminal`, `brue` and `brue-connect`, and the organization profile links to `www.londonstrategicedge.com`; this is the basis for calling those four repositories official-associated sources. The code was read through public GitHub pages only. An unrelated community `lse-data-mcp` repository was not used as official evidence; its own README calls it unofficial.

## QMX adaptation opportunities (proposals, not donor facts)

1. **Enabling requirement candidate — typed data-resource contract.** Model a data resource with provider, asset class, symbol/series identifier, fields, timeframe, start/end, row limit, entitlement/quota and provenance. Support preview, paged reads and explicit export jobs. Evidence: S1, S2, S8. Failure journey: invalid symbol, empty range, quota exceeded, partial/truncated result and export timeout must be first-class states.
2. **Enabling requirement candidate — history/live boundary.** Represent a historical replay and a live stream as distinct phases with event-time and replay/live provenance; expose subscribe/unsubscribe and reconnect state. Evidence: S2, S8. Do not assume LSE’s protocol or internal storage.
3. **Reference scenario — dataset recipe.** Treat “computed CSV with indicators/features” as a candidate recipe object: source references, window, transforms, output schema and lineage. Evidence: S1 only; builder serialization and reusability are unknown.
4. **Reference scenario — reproducible research run.** Capture strategy/model code or declarative inputs, dataset snapshot/reference, parameters, costs, run handle, logs, metrics, artifacts and comparison links. Evidence: S5, S9, S10. Keep backtest execution separate from live execution authority.
5. **Optional future app — ML experiment workbench.** Add explicit feature/label definitions, split policy, model family, hyperparameters, compute budget, metrics and model artifact lineage. Evidence is only S6/S9 claims; all operational details remain unknown.
6. **Enabling requirement candidate — composable reference series.** Normalize macro/economic events, yields, COT, fundamentals, options and calendars into discoverable resources with alignment rules and licensing metadata. Evidence: S1, S8.

## Unknowns and non-observations

The public no-JavaScript pages did not expose authenticated catalogue rows, preview payloads, builder controls, backtest forms/results, ML Studio forms/jobs, API schemas, WebSocket frames, plan entitlements or failure states. No screenshot is included. No claim is made about data accuracy, completeness, production readiness, pricing permanence, backend architecture, or whether marketing features are enabled for a particular account.

