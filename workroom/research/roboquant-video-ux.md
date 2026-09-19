# RoboQuant AI coding app — UX brief for QMX

Source: [Roboquant AI Coding App Tutorial](https://youtu.be/_ktzcUiojC0) (Tim Hutter, 15:44). Captions plus frames. Scene-aware sampling found only 11 cuts in this screen recording; UI coverage below is from caption-cued frames.

Product: cloud trading-bot IDE at `roboquant.dev` (spoken as robocon.de / future robocon.ai). Browser tab: **RoboQuant - Cloud Trading Bot IDE**. This is a hosted coding agent with Docker workspaces, not a research/backtest/live platform. Nothing in the video submits an order, runs a backtest UI, or deploys a bot.

QMX already logged RoboQuant as a mechanism candidate (persistent strategy workspaces, agent + code, server-side work that survives tab close). This brief is visual evidence for that row.

---

## Shell and navigation

Two shells, one left rail.

**App chrome (all authenticated pages).** Top bar: wordmark | green **Connected** | `Chat | Pro` | theme | avatar. Avatar menu (`09:38`): email, plan (Ultra), wallet balance, Dashboard, Workspaces, Profile, Sign out.

**Dashboard rail** (`01:49` onward): Overview, Workspaces, Chart Analyzer, Resources, Billing & Invoices, Plans, Usage, What's New, Support. Overview is a status desk, not a trading blotter.

**Workspace IDE** (`03:45`) is a sovereign three-pane world. It keeps the top chrome but drops the dashboard rail. Toggle **Chat** (top-right) collapses to a ChatGPT-style full-width agent (`08:07`).

---

## Screen catalog

### Marketing / auth

| Time | Screen | What is actually there |
|---|---|---|
| `00:00` | Talking-head intro | Not product UI. |
| `00:20`–`00:33` | Landing | Centered “What do you want to build?” prompt, placeholder “Describe your trading strategy…”, send control, four chips: RSI divergence, MACD crossover bot, Grid trading system, Mean reversion algo. Top-right **START**. Presenter: this prompt is a demo; real use starts at Start. |
| `00:40`–`01:23` | Sign-in | Split: landscape art left, form right. **Continue with Google** (Last used), GitHub, **Continue with Whop**, email. Terms/privacy. Google account picker targets `roboquant.dev` (`01:24`). |
| `01:31`–`01:49` | Claim academy credits | Spoken: Profile → Connect (Whop) → accept. Frame at `01:40` still shows Overview; the connect dialog itself is not held. After connect, plan jumps Pro → Ultra, wallet $0 → $10, workspace cap 7/8 → 7/10 (`01:37` vs `01:49`). |

### Dashboard

| Time | Screen | What is actually there |
|---|---|---|
| `01:37`–`01:49` | Overview | “Welcome back”. Workspaces list (lg, YT, Tori Trades) with **View All**. Resource Usage: Wallet Balance (red $0.00 + Add Funds, then green $10.00), Workspaces `n / cap` bar, Current Plan. Shortcuts: Manage Workspaces, View Plans, Browse Resources. |
| `02:28`–`02:36` | Plans | Monthly/Annual toggle. Cards: **Free** (browse, docs, no workspaces), **Hobby $15** (1 workspace, $1/mo AI credits, PAYG, community), **Pro $30** (5 workspaces, $5/mo, PAYG, priority), **Ultra $50** (10 workspaces, $10/mo, PAYG, priority, early access). Current plan badge + Downgrade. Spoken mapping: academy Premium → one paid tier, Advanced → another, Ultra → Ultra. Free can look, not run. |
| `02:50` | Workspaces | Card grid, date, **Open Workspace**. **Refresh**, **+ Create Workspace**. First paint only shows three cards; more load in. |
| `03:01` | Create Workspace modal | Name (`my-trading-bot`), optional Description, Cancel / Create. Spoken: isolated cloud environment; one per project or one per language (Pine / MQL5 / Python). |
| `03:29` | Workspaces after create | New **test** card dated 12/19/2025, cursor on Open Workspace. |
| `03:31` | Loading workspace | Full black: spinner + “Loading workspace…”. Presenter: new or file-heavy workspaces are slow. |

### Workspace IDE

Default layout (`03:45`–`04:08`): left file explorer, center editor over terminal, right agent column.

**File explorer.** Folders on a fresh workspace: `backtest`, `backtest_results`, `data`, `indicators`, `strategies`, `README.md`. Toolbar tooltips (`07:32`): search, download/export zip, upload, create new file, GitHub, trash. Spoken: delete/rename/copy, drag-and-drop, or tell the agent to delete.

**Editor.** Empty state “No file selected”. Open file shows tab + line numbers + toolbar: **+ New, Copy, Save, Export, Revert**. Pine files add **Validate** and **Close all** (`04:49`). README (`03:53`) documents:

- `/workspace/strategies/`, `/indicators/`, `/backtest/`
- Python 3.12, `python script.py`, `pip install`
- Pine Script for TradingView; “More coming soon…” (UI already exposes MetaTrader and NinjaTrader modes)

**Terminal.** Tab “Terminal 1 +”. Prompt `developer@roboquant-container:/workspace`. Green workspace id (`workspace-e81ba4d9`). Spoken: needed for Python, not for Pine/MQL.

**Agent column.** Header: History (empty → chat titles), **+ New chat**. Empty: robot mark, “Dear Sir / I can help you build, debug, and run code in your Docker workspace.” Prompt dock:

- `@ Add context` → searchable workspace files (`04:58`: `README.md`, `strategies/sample_ma_strategy.py`)
- **Thinking** toggle
- Placeholder “Ask, search, or make anything…”
- Paperclip (images/screenshots, `06:35`)
- Model chip (default **GLM-4.6**)
- Target-platform chip, mislabeled **Select Workspace**: Default, TradingView, Python, MetaTrader, NinjaTrader (`05:05`)
- Mode chip **Select Agent Mode**: Act / Plan; plus **Knowledge Retrieval**: Auto (heuristic) / Always on / Off (`05:13`)
- Send (blue) / Stop (red square while running)

**Model picker** (`05:50`–`06:09`): GLM-4.6 ($12/M), GLM-4.5, Claude Haiku 4.5 ($4/M), Sonnet 4.5 ($15/M), Opus 4.5, GPT-5.2 ($10/M) with nested **REASONING** Low / Medium / High / X-High, GPT-5.2 Pro ($110/M), Codex-5.1 / Mini / Max. Presenter: use default; switch models to repair, not as the first move.

**Chat-only mode** (`07:54`–`08:10`): thin left history rail (+, search, clock), centered empty agent, prompt dock at the bottom. Same model/mode chips. No files, no terminal.

**GitHub modal** (`07:10`): “Workspace GitHub — Manage repository syncing”. Connected account `@timhutter92` (12/4/2025), Disconnect, Repository Configuration spinner. Spoken: import, commit, push from the terminal.

**Agent run** (`08:20`–`09:10`). Prompt: “create a fully llm based hyperliquid trading bot in python”, Python + Act. Visible tool stream:

1. `create_todo_list`
2. `list_files` (“Checking files in the workspace…”)
3. `create_directory`
4. `update_todo_status`
5. `create_file` / `write_file` (`…/hyperliquid_bot/config.py`)

Status line: `Running {tool} {mm:ss} GLM-4.6` | live cost `$0.0051` → `$0.0116` | token rate. Toast: “Conversation renamed”. Interrupt via red stop. Wallet does not update live; after refresh, $10.00 → $9.95 (`09:38`). Presenter: cost scales with files written and thinking time; do not interrupt while the status is red.

### Billing, usage, changelog, help

| Time | Screen | What is actually there |
|---|---|---|
| `10:05`–`10:57` | Billing & Invoices | Plan overview: Ultra ACTIVE, wallet $9.95, Free credits/mo $5.00, Workspaces 10 max. Manage subscription, Refresh. AI Wallet: Available, Deposited $10 / Spent $0.05, Add Funds. Payment Methods (empty, “No cards saved”). Auto-Recharge toggle disabled until a card exists. Invoices table (id, date, amount, Paid, View) — $29 and $0 rows. Spoken but not shown: auto-recharge threshold (e.g. add $10 when below $5) and monthly spend cap. |
| `11:05`–`11:18` | Usage | “Your Activity” with remaining credits. Range 1d / 7d / 30d. Spark charts: Spend, Tokens, Requests (avg/day and period totals). Ledger: Timestamp, Model, Tokens (`16k → 4K`), Cost, Speed (tps), Finish (`error` / `Done`). Models in the table: `z-ai/glm-4.6`, `claude-sonnet-4-5-…`, `gpt-5.2`. |
| `14:30`–`14:54` | Resources | Three cards of docs, not videos yet. Getting Started (first workspace, AI assistant, workspace limits). Using the Platform (file management, terminal, AI code generation). Billing & Plans (compare plans, extra workspace slots, subscription). Spoken: later they will link a “code a YouTube/TikTok/Instagram strategy” guide. |
| `14:54`–`15:22` | Support | Community → Join Discord. FAQ accordion: create workspace, workspace limit, wallet, free monthly credits, auto-recharge, upgrade/downgrade, cancel, are files saved, GitHub, languages, connect Whop membership. |
| `15:22`–`15:34` | What's New | Dated changelog. **v1.5.0** wallet + usage billing, auto-recharge, Whop Premium/Advanced/Ultra, Claude 4.5, Haiku on demo workspace, token-accurate billing. **v1.4.0** GLM-4.6 (200K, full tool execution), OpenRouter fallback when Anthropic rate-limits, provider switching, workspace connection auto-scale, tool-execution reliability. **v1.3.0** Video-to-strategy (YouTube, TikTok, Instagram, Twitter, Facebook URL), GPT-5.2 reasoning controls, “Direct backend streaming bypasses timeout limits”, extended thinking, connection timeouts. |

### Chart Analyzer (separate product surface)

| Time | Screen | What is actually there |
|---|---|---|
| `13:03`–`13:09` | Empty analyzer | Headline “What chart can I analyze?”. Style dropdown: Price Action, **Smart Money (SMC)**, ICT, Order Flow, Supply & Demand, Classic TA. Bottom: paperclip + “Upload a chart…”. Phone screenshot path spoken, not shown. |
| `13:14`–`13:20` | External TradingView | XAUUSD candlesticks; screenshot from OS (download toast `XAUUSD_2025-12-19_….png`). |
| `13:23` | Upload | Thumbnail of the screenshot attached above the composer. |
| `13:34`–`13:40` | Text analysis | Market Overview (asset, TF, trend, context). Technical Analysis: BOS, order blocks with prices, FVG, liquidity pools, premium/discount. **Trade Setup** table: Bias LONG (on pullback), Entry Zone $4,300–$4,320, SL $4,265 (2.5% / below OB), TP1 $4,400 (1:2.3R), TP2 $4,450 (1:4.8R), alternative aggressive entry. Risk Note + invalidation + disclaimer. Follow-up composer “Ask a follow-up…”. Button **Analyze this chart**. |
| `14:07` | Annotated Chart | Overlay on the uploaded screenshot: Bullish OB boxes, FVG, trendline, Key Level, ENTRY ZONE, SL, TP1, TP2. Download / zoom. Presenter treats this as a takeable setup. ~1 minute generation. |

---

## Hypothesis → live (as the video actually runs it)

There is no live, no broker, no promotion gate. The shown path is **source → plan/act → files in a Docker workspace**.

1. **Source a hypothesis from media** (`11:42`–`12:22`). Find a YouTube strategy (TTR, ~28 min, “strategy itself maybe 5 minutes”). Copy URL. Paste into the workspace agent. Set **TradingView** so the target is Pine. Recommended: **Plan** first (“do you understand…”), then “okay execute”; he still hits Act on camera.
2. **Ingest** (`12:22`). Tool `get_video_transcript` on `https://www.youtube.com/watch?v=cPPREA-6ubY`. Status: Thinking, GLM-4.6.
3. **Retrieve prior patterns** (`12:57`). Two `search_knowledge` calls: “session-based trading strategies”, then “session time configurations and fakeout patterns”. Spoken: every prompt checks “have we built something similar”.
4. **Plan then write** (`12:57`). `create_todo_list` → `create_file` `/workspace/london_session_fakeout_strategy.pine`. Editor tab + Pine **Validate** appear. Spoken ETA 2–3 minutes. No compile-on-TradingView, no visual-parity loop, no backtest of the new file.
5. **Python variant** (`08:20`). Same agent, Python mode, Act: scaffolds `hyperliquid_bot/` (`config.py`, `requirements.txt`, `.env.example`, `hyperliquid_client.py`). Still no run/backtest UI; terminal is available for the user to run it.
6. **Repair loop (spoken, `06:32`–`06:48`)**. If a Pine indicator “doesn’t look the way you want”, attach a screenshot of current vs desired, or mark it wrong and explain. That is the only visual-diff workflow shown.

QMX’s candidate lifecycle (Project → sourced hypothesis → registry → experiments → robustness → Book/BMS → governed live) is **not** present. RoboQuant stops at “files exist in the workspace.”

---

## Data mining (as shown)

Not market-data mining. Three retrieval modes:

1. **Proprietary knowledge base** — `search_knowledge` over “our entire code base” / academy library. Toggle Auto / Always / Off. This is RAG, not a Databank of tested candidates.
2. **Media transcript ingest** — paste YouTube/TikTok/Instagram/Twitter/Facebook URL; backend fetches transcript; agent writes Pine/Python. Same job QMX already owns in `strats-video-populate`, but here it is an in-IDE one-box action with no evidence audit, no dictionary, no strategy package.
3. **Workspace files as context** — `@ Add context` file picker; paste foreign indicator code into a `.pine` / `.mq4` file and attach it (`04:26`–`04:57`). Folders `data/`, `backtest/`, `backtest_results/` exist as convention only; no miner, no experiment grid, no results inspector.

Chart Analyzer is vision-on-a-screenshot, not a data-mining surface.

---

## Agent integration

The agent is the product. It has **full filesystem + terminal** in the workspace (`07:46`).

Visible contract:

- **Plan vs Act.** Plan emits a todo list; user switches to Act or types “proceed” depending on model (`05:11`–`05:47`).
- **Steerable run.** Streaming tool rows with elapsed time, live USD, token rate, interrupt.
- **Target platform** as a first-class chip (TradingView / Python / MetaTrader / NinjaTrader), not a system prompt the user must remember.
- **Knowledge retrieval** as a separate control from Thinking.
- **Multi-model + reasoning depth** with list prices in the picker.
- **Session list** (History / New chat) inside a durable workspace, not a global chat.
- **Chat-only shell** for users who do not want the ADE.

What the agent does **not** do on camera: open charts inside the IDE, launch a backtest runner, talk to a broker, or attach a journal/lineage object to the files it writes.

---

## Backend the UI implies

- Auth: Google, GitHub, email, Whop (academy entitlements).
- Per-plan workspace quota and a monthly AI-credit stipend; usage beyond stipend is PAYG from a wallet.
- One Docker container per workspace (`roboquant-container`), persistent volume, slow cold start, memory readout (`5.35 MB` on a later workspace).
- Agent runtime with tool calling, streaming that “bypasses timeout limits”, interrupt, conversation rename.
- Transcript fetcher for social URLs.
- Knowledge index over internal strategies/components.
- Pine validator in the editor.
- GitHub OAuth + per-workspace repo sync.
- Zip export of the workspace.
- Billing: cards, auto-recharge, invoices, spend caps (spoken).
- Usage telemetry: tokens in/out, cost, tps, finish state, by model.
- OpenRouter failover when Anthropic rate-limits; provider switching under load.
- Chart-vision pipeline + overlay renderer (entry/SL/TP boxes on the uploaded PNG).
- Websocket **Connected** indicator; changelog admits connection/timeout issues.

---

## Reuse for QMX

Keep as mechanism, not as product shape.

**Worth stealing**

- Persistent **named workspaces** as the durable container (one per project or per language), with a quota and a loading state that tells the truth.
- **Three-pane ADE** (files | editor+terminal | agent) as the QML / agent-authoring world — matches the Hermes reference already imported. Chat-only as an alternate layout of the same world, not a second product.
- **Plan / Act** plus a visible todo stream. QMX already thinks in Run / Configure / Inspect; Plan is the missing “don’t touch files until the operator agrees” gate.
- **Target-platform chip** (Pine / MQL / Python / Ninja) on the prompt dock. QMX needs the same for QML vs research vs node vs QMB.
- **@ Add context** over project files. Operator context must travel; this is the cheap version.
- **Live cost/token meter on the run**, plus a usage ledger by model. QMX agents will burn money; hide-the-meter is how RoboQuant’s own free tier died.
- **Video URL in the prompt** as a first-class ingest. Do not copy the one-box “it codes Pine.” Route it through STRATS: transcript, chart evidence, dictionary, strategy package, then a candidate in the registry.
- **Default folder taxonomy** `strategies / indicators / backtest / data` as a workspace skeleton — useful, incomplete. QMX still needs experiments, robustness, Book/BMS, journals.
- **What's New** as a nav item. Cheap trust surface for a fast-moving agent product.
- **GitHub sync per workspace** and zip export. Survival of work off-laptop.

**Do not copy**

- Wallet-and-credits as the primary relationship. QMX is operator-owned infrastructure.
- Academy/Whop as the entitlement bus.
- Chart Analyzer as a **trade-call** product (Bias / Entry / SL / TP / “I would take this”). QMX’s chart grammar is evidence: one conclusion, sources, invalidation, no setup-as-advice. The overlay language (OB, FVG, entry zone, SL, TP) is reusable as an annotation layer, not as a signal.
- Stopping at “a `.pine` file appeared.” That is not hypothesis-to-live.
- One left-nav dashboard that mixes IDE, billing, chart-GPT, and docs. QMX already decided: global rail → tabbed compositor → sovereign domain worlds. Billing/usage/support are operator-admin, not research surfaces.
- Knowledge retrieval that silently reuses “stuff we built” with no lineage. QMX wants immutable hypothesis/config/agent lineage, not an opaque RAG hit.

**Gaps vs the QMX span**

| QMX need | In this video |
|---|---|
| Source hypotheses | Yes — URL paste, screenshot, pasted code |
| Ingest/scrape data | Transcript only; no market data |
| Research / notebooks | No |
| Strategy/bot authoring | Yes — files + agent |
| Data mining / experiment search | No (folders only) |
| QMB backtest / optimize / robustness | No UI; `backtest/` is a directory |
| Analysis / charts | Separate screenshot analyzer, not a desk |
| Governed promotion | No |
| Live trading / review | No |

Use RoboQuant as the **authoring-world analog** (how an agent sits on a durable code workspace). Use StrategyQuant for mining/registry and QuantConnect for research→live. Do not let this video collapse QMX into “chat that writes Pine.”
