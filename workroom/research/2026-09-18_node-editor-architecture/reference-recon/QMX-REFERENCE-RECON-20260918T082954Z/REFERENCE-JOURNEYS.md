# Reference journeys

## Method and access

Browser control was first verified by binding the explicitly attached Brave LSE tab and reading its visible state. The attached OpenBB marketing tab was also readable. New research tabs were used for public official documentation and Taskade public pages. The controlled browser session did not inspect cookies, tokens, password stores, or unrelated tabs.

Access times below are UTC. Screenshot creation times are the closest per-journey timestamps; source-document reads by parallel workers occurred at approximately 08:30–08:35 UTC. “Inputs” means visible/configured form values, not submitted payloads.

## London Strategic Edge

### LSE-NAV-001 — home and feature inventory

- **Classification:** `OBSERVED_INTERACTION`, with page-scale statements treated as `VENDOR_CLAIM`.
- **URL/time:** https://londonstrategicedge.com/ at 2026-09-18T08:30:20Z.
- **Access/preconditions:** user-attached browser tab; account already signed in; no credential handling.
- **Actions:** bound the tab, read the navigation and visible landing sections, followed only relevant read-only routes.
- **Visible inputs/outputs:** navigation for Markets, Machine Learning, Data, Backtesting, and Tools; homepage statements of 118,000 datasets, 30+ years of history, and 500+ TB; LSE Terminal beta and official GitHub link.
- **States:** normal loaded state. No permission or loading error.
- **Evidence:** `screenshots/LSE-00-home.png`.
- **Limitations:** landing-page quantities are vendor statements; no entitlement or data-quality conclusion follows.

### LSE-DATA-001 — databank overview, catalogue and preview

- **Classification:** `OBSERVED_INTERACTION`; endpoint/SDK descriptions also `DOCUMENTED_CAPABILITY` and `REPOSITORY_SOURCE`.
- **URL/time:** https://londonstrategicedge.com/data/ at 2026-09-18T08:30:37Z–08:30:50Z.
- **Access/preconditions:** signed-in read-only page; no API key generated.
- **Actions:** opened Databank, entered the stock catalogue, expanded NVIDIA, selected the one-minute preview.
- **Visible inputs:** asset-class navigation, catalogue search, direction/history/update/sort filters, and timeframe choices from tick through monthly.
- **Visible outputs:** overview counters (403.39B recorded ticks, 22,966 instruments/series, 27 asset classes, 211 countries, price history since 1905); catalogue metadata including symbol, points, history, update time, latest/change; ten preview rows for NVDA.
- **States:** a brief preview-loading state preceded rows; no-data/error/permission states were not triggered.
- **Evidence:** `screenshots/LSE-01-databank-overview.png`, `screenshots/LSE-02-catalogue-preview.png`.
- **Limitations:** preview values were not validated against an external source. The download icon was not used.

### LSE-DATA-002 — dataset builder / recipe configuration

- **Classification:** `OBSERVED_INTERACTION`; recipe generalization is `QMX_ADAPTATION_PROPOSAL`.
- **URL/time:** https://londonstrategicedge.com/data/ (Dataset builder) at 2026-09-18T08:31:09Z.
- **Actions:** selected NVIDIA; kept a one-year/one-minute window; selected RSI(14) and Return(5); inspected cross-asset, time/day/timezone, and output-column controls; stopped before Build CSV.
- **Visible inputs:** instrument class/symbol, date range, resolution, 61 indicator/feature choices, second-instrument comparison with close/% change/correlation, time-of-day/timezone/day filters, output columns.
- **Visible outputs:** a summarized configured recipe and enabled Build CSV action after a symbol was chosen.
- **States:** Build CSV was disabled before required input and enabled after configuration. No build, progress, result, or failure state was produced.
- **Evidence:** `screenshots/LSE-03-dataset-builder-configured.png`.
- **Limitations:** recipe serialization, lineage, compute cost, output schema, reuse, cancellation, and artifact lifecycle are unverified.

### LSE-API-001 — REST query and export-job documentation

- **Classification:** `DOCUMENTED_CAPABILITY`, `REPOSITORY_SOURCE`.
- **URL/time:** https://londonstrategicedge.com/api-documentation/ at 2026-09-18T08:31:19Z–08:31:23Z; official repository https://github.com/londonstrategicedge/lse-data.
- **Actions:** read authentication, endpoint, limit, usage, and bulk-export sections; no request was sent.
- **Visible contract:** HTTPS `/vault` base, `x-api-key`; catalogue/meta/reference/candles/series/options endpoints; query row cap of 5,000; bulk `POST /export`, poll, download; statuses queued/running/ready/failed/expired; artifact lifetime stated as 48 hours; Range-based resume.
- **States:** documentation normal state. Runtime authentication, invalid input, rate-limit, partial download, and expiration were not exercised.
- **Evidence:** `screenshots/LSE-04-api-docs.png`, `screenshots/LSE-05-api-export-job.png`.
- **Limitations:** docs describe a contract; successful service behavior and plan limits remain unverified.

### LSE-STREAM-001 — WebSocket replay-to-live contract

- **Classification:** `DOCUMENTED_CAPABILITY`, `REPOSITORY_SOURCE`.
- **URL/time:** https://londonstrategicedge.com/websocket-documentation/ at 2026-09-18T08:31:35Z–08:31:36Z.
- **Actions:** read connection/auth/subscribe sections and replay lifecycle; no socket was opened.
- **Visible inputs/outputs:** endpoint `wss://data-ws.londonstrategicedge.com`; auth, subscribe, unsubscribe, subscribe_options, list_symbols, ping; tick fields symbol/price/bid/ask/volume/timestamp; replay up to 24 hours, `replay_complete`, then live events; quota/error messages.
- **States:** documented connection lifecycle and error types only; actual reconnect, ordering, duplicates, gap recovery, and quota exhaustion unverified.
- **Evidence:** `screenshots/LSE-06-websocket-docs.png`, `screenshots/LSE-07-websocket-replay.png`.

### LSE-BACKTEST-001 — setup, playback, overlays and empty results

- **Classification:** `OBSERVED_INTERACTION`; terminal/Brue README details are `REPOSITORY_SOURCE`.
- **URL/time:** https://londonstrategicedge.com/backtest/XAUUSD at 2026-09-18T08:31:51Z–08:32:08Z.
- **Actions:** inspected the initial setup modal; closed it without starting; opened History, Indicators, and Layout; closed each panel.
- **Visible inputs:** XAU/USD, five-minute timeframe, UTC timezone, start date/time/presets, starting capital 10,000, spread in pips; in-session lot size, buy/sell/limit controls, playback 1x/10x/100x, timeframes, annotation tools, and four layout choices.
- **Visible outputs:** empty history metrics (total P&L, win rate, trades, profit factor, “No closed trades yet”); 104 built-in indicators grouped by category with parameters.
- **States:** setup modal, normal chart/workbench, empty-result state. No run/progress/cancel/comparison/export/failure state was created.
- **Evidence:** `screenshots/LSE-08-backtest-setup.png`, `screenshots/LSE-09-backtest-empty-results.png`, `screenshots/LSE-10-backtest-indicators.png`.
- **Limitations:** the observed route was a manual playback/trade simulator; no strategy code editor was visible. Do not conflate this route with capabilities claimed by the separate LSE Terminal or Brue repositories.

### LSE-ML-001 — model configuration and optimisation setup

- **Classification:** `OBSERVED_INTERACTION` for controls/states; claimed model outcomes/infrastructure remain `VENDOR_CLAIM`/`UNVERIFIED`.
- **URL/time:** https://londonstrategicedge.com/machine-learning-studio/ at 2026-09-18T08:32:28Z–08:33:06Z.
- **Actions:** inspected model families; opened XGBoost configuration and feature groups; switched to optimisation setup; did not run or train.
- **Visible inputs:** dataset, timeframe, dates, prediction horizon, test split, XGBoost hyperparameters, feature-engineering categories; optimisation methods Grid Search, Walk Forward, Monte Carlo, Fixed R:R, Adaptive and Volatility-Scaled; ATR/PIPS/% distance, stop-loss/take-profit ranges, max hold, and fixed/% risk/Kelly sizing.
- **Visible outputs/states:** daily run counter shown at 3/3; empty output prompting “Click RUN”; optimiser required a trained model and reported none; 49-combination configuration with disabled Optimise.
- **Evidence:** `screenshots/LSE-11-ml-studio-config.png`, `screenshots/LSE-12-ml-optimise-config.png`.
- **Limitations:** training data, leakage controls, compute substrate, run IDs, logs, cancellation, metrics, artifacts, reproducibility, and backtest linkage remain unverified.

### LSE-RESEARCH-001 — calendar, intermarket, yields and screener

- **Classification:** `OBSERVED_INTERACTION`.
- **URLs/times:** https://londonstrategicedge.com/calendar/ at 08:33:28Z; https://londonstrategicedge.com/correlation-matrix/ at 08:33:45Z; https://londonstrategicedge.com/data?class=bonds at 08:34:10Z; https://londonstrategicedge.com/stock-screener/ at 08:34:21Z.
- **Actions:** inspected calendar filters and rows; opened a crypto/tech correlation preset; expanded United States 10-year yield preview; changed screener to Valuation.
- **Visible inputs/outputs:** calendar country/timezone/impact/date filters and event actual/forecast/previous; 10×10 correlation matrix with timeframe and Matrix/Screener/Insights views; 206 bond-yield datasets and preview rows; 4,417 stock results with search/country/sector/market-cap/P-E/dividend/change filters and multiple table modes.
- **States:** normal loaded states; bonds briefly loaded before rows. Calendar export was not clicked.
- **Evidence:** `screenshots/LSE-13-economic-calendar.png`, `screenshots/LSE-15-correlation-matrix.png`, `screenshots/LSE-16-bond-yield-preview.png`, `screenshots/LSE-17-stock-screener-valuation.png`.
- **Limitations:** calculations, alignment methodology, export payloads, and data accuracy were not validated.

### LSE-ROUTE-ERR-001 — linked tools returning 404

- **Classification:** `OBSERVED_INTERACTION`, `UNVERIFIED` capability status.
- **URL/time:** https://londonstrategicedge.com/heatmap at 2026-09-18T08:33:35Z; a `/cot-data` attempt in the same session.
- **Actions/output:** followed the linked heatmap route and received a 404; the tested COT route also returned 404.
- **Evidence:** `screenshots/LSE-14-heatmap-404.png`.
- **Limitations:** official repository/API documentation still lists COT/reference feeds. A route failure does not establish feature absence.

## OpenBB

### OBB-MKT-001 — public Workspace positioning

- **Classification:** `VENDOR_CLAIM`, `UNVERIFIED` runtime.
- **URL/time:** https://openbb.co/products/workspace/ at approximately 2026-09-18T08:34Z.
- **Access/preconditions:** attached public marketing tab; no login.
- **Observed page claims:** custom data, interactive dashboards, agents, and self-host/VPC options.
- **Limitations:** no signed-in catalog, entitlement, connected backend, or live widget was observed; no screenshot retained because the documentation supplied stronger contract evidence.

### OBB-DEV-001 — backend registration, widget declaration and app layout

- **Classification:** `DOCUMENTED_CAPABILITY`, `REPOSITORY_SOURCE`.
- **URL/time:** https://docs.openbb.co/workspace/developers/data-integration at 2026-09-18T08:34:47Z–08:34:52Z; official repository https://github.com/OpenBB-finance/backends-for-openbb.
- **Actions:** read the data-integration flow and examples.
- **Visible contract:** a backend serves data endpoints plus `/widgets.json`; optional `/apps.json` composes tabs/layouts and initial widget parameters. Widget declarations separate endpoint/operation from presentation and metadata.
- **States:** documentation normal state only; backend connect/loading/error/permission behavior was not exercised.
- **Evidence:** `screenshots/OPENBB-01-widget-declaration.png`, `screenshots/OPENBB-02-app-layout.png`.

### OBB-DECL-001 — capability schema and shared parameters

- **Classification:** `DOCUMENTED_CAPABILITY`.
- **URL/time:** https://docs.openbb.co/workspace/developers/json-specs/widgets-json-reference at 08:35:03Z and https://docs.openbb.co/workspace/developers/widget-parameters/parameter-positioning at 08:35:12Z.
- **Visible inputs/outputs:** widget name/description/endpoint or `wsEndpoint`/category/type/source/grid/data mapping/parameters/refresh/raw/run/export/MCP binding; static or endpoint-sourced options; nested parameter rows; cross-widget interactions using shared parameter groups, `valueField`, and `forceUpdate`.
- **States:** schema examples only; validation errors and conflicting bindings were not exercised.
- **Evidence:** `screenshots/OPENBB-03-widget-capability-schema.png`, `screenshots/OPENBB-04-parameter-positioning.png`.

### OBB-PROVIDER-001 — provider selection, normalization and coverage

- **Classification:** `DOCUMENTED_CAPABILITY`, `REPOSITORY_SOURCE`.
- **URL/time:** https://docs.openbb.co/odp/python/basic_usage/query_parameters#provider at 2026-09-18T08:35:20Z; architecture/provider docs read at 08:32–08:33Z.
- **Visible contract:** shared query fields such as provider/symbol/start/end/date/limit; explicit provider selection, provider-specific formats/extras, default provider behavior, warnings for invalid extras, and coverage discovery. Official architecture documents a Fetcher flow of `transform_query`, `extract_data`, and `transform_data` into normalized models.
- **States:** documentation only; no provider credential, subscription, query, fallback, or data error was exercised.
- **Evidence:** `screenshots/OPENBB-05-provider-selection.png`.

## Taskade

### TSK-CREATE-001 — public creation surface

- **Classification:** `OBSERVED_INTERACTION`, with generation outcomes `UNVERIFIED`.
- **URL/time:** https://www.taskade.com/create at 2026-09-18T08:35:30Z.
- **Access/preconditions:** public unauthenticated page.
- **Actions:** opened the surface and inspected the prompt and modes; did not type or submit.
- **Visible inputs:** prompt field and category choices such as Run my business, Create with AI, Build AI Agents, and Automate everything.
- **States:** public initial state with Login/Sign up. No generation/loading/preview/error/publish state.
- **Evidence:** `screenshots/TASKADE-01-public-create-surface.png`.
- **Limitations:** official docs describe account/workspace preconditions for the full Genesis journey.

### TSK-GALLERY-001 — app kits and template reuse

- **Classification:** `OBSERVED_INTERACTION`; successful cloning is `UNVERIFIED`.
- **URL/time:** https://www.taskade.com/apps at approximately 2026-09-18T08:37–08:40Z.
- **Actions:** read search/category/price filters and visible cards; did not click Clone.
- **Visible outputs:** cards describe an app kit as a composition of projects, AI agents, and automations, with clone counts and Free/Premium labels. Examples include Application Tracker Board, Finance Tracker Dashboard, Investor Dashboard, Broker Calendar, and Airtable Sync Dashboard.
- **States:** loaded public gallery. No clone, ownership, conflict, version, rollback, or permission state.
- **Evidence:** `screenshots/TASKADE-02-app-kits-gallery.png`.

### TSK-AGENT-001 — agent builder/gallery surface

- **Classification:** `OBSERVED_INTERACTION` for UI; memory/tool/team behavior is `VENDOR_CLAIM` or `DOCUMENTED_CAPABILITY`.
- **URL/time:** https://www.taskade.com/agents at approximately 2026-09-18T08:37–08:40Z.
- **Actions:** inspected the public Agents mode, builder controls, categories, and cards; did not submit Build it or invoke an agent.
- **Visible inputs/outputs:** builder prompt plus Prompts, Tools, Connect, Models and Files controls; public copy says agents receive instructions/knowledge/commands and can be used in projects, teams, or public embeds; galleries for featured, project management, operations intelligence, productivity, marketing, translator, workflow, and research agents.
- **States:** loaded public gallery. No tool permission, chat, run, approval, memory, or failure state.
- **Evidence:** `screenshots/TASKADE-03-agent-builder-gallery.png`.

### TSK-DOC-001 — workspace/app model, Genesis, automations and MCP

- **Classification:** `DOCUMENTED_CAPABILITY`, `REPOSITORY_SOURCE`; outcomes not exercised are `UNVERIFIED`.
- **URLs/time:** official docs read around 2026-09-18T08:31Z: https://docs.taskade.com/platform/workspace-dna.md, https://docs.taskade.com/taskade-genesis/genesis/getting-started.md, https://docs.taskade.com/ai-features/ai-features/ai-agents-getting-started.md, https://docs.taskade.com/automations/automation.md; official repositories https://github.com/taskade/mcp and https://github.com/taskade/docs.
- **Documented journey/model:** workspace “DNA” connects projects/databases (memory), agents (intelligence), and automations (execution); a Genesis app runs on that workspace. The documented authoring journey is prompt → generate → preview/test → refine by natural language → keep private or publish/share. Automations use Trigger → optional Condition/Filter → Actions, including agent steps and connectors.
- **Repository contract:** the official MCP README exposes a concrete taxonomy for workspaces, projects, tasks, custom fields, agents, knowledge/media, templates, conversations, sharing, and webhook subscriptions. It distinguishes local Workspace MCP, hosted Genesis App MCP, and in-product connectors.
- **States/limitations:** no signed-in workspace, live asset graph, app preview, assistant edit, automation run, run log, external connector, gated endpoint, publication, or failure state was observed. Stable run ID, idempotency, replay, per-step result, and retry contracts remain unverified.

## Cross-source caution

Observed controls establish interaction shape, not donor backend internals. Documentation establishes a public contract, not successful execution. Repository READMEs establish an official-associated interface claim, not entitlement or production behavior. QMX proposals in the companion report must be validated against a later QMX repository audit before ownership or implementation decisions.
