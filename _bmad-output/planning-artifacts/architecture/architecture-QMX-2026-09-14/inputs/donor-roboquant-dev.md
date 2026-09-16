# Donor investigation — roboquant.dev (AI Trading IDE)

**Donor:** roboquant-dev (FXC Algo Trade LLC commercial product at [roboquant.dev](https://www.roboquant.dev/)).
**Date:** 2026-09-14.
**Mode:** architecture only. No implementation. No vendor UI or engine adoption.
**Evidence grade:** official pages fetched this sitting. Workroom notes were not used as primary evidence.

## Identity split (mandatory)

Three different things share a similar name. Only the first is this donor.

| Product | Operator | What it is | Official home |
| --- | --- | --- | --- |
| **roboquant.dev (this donor)** | FXC Algo Trade LLC, Sheridan WY | Closed commercial **cloud AI Trading IDE** + webhook execution. Current GA product plus a **v2 closed-beta** rebuild. | [www.roboquant.dev](https://www.roboquant.dev/), [ToS](https://www.roboquant.dev/terms), [Privacy](https://www.roboquant.dev/privacy), [FAQ/docs](https://www.roboquant.dev/docs), [pricing](https://www.roboquant.dev/pricing), [v2 waitlist](https://www.roboquant.dev/next) |
| **neurallayer/roboquant** | Apache-2.0 OSS | **Kotlin/JVM** algorithmic-trading **library** (Maven `org.roboquant:roboquant`), Jupyter notebooks, IntelliJ. Documented at **roboquant.org**, not .dev. | [github.com/neurallayer/roboquant](https://github.com/neurallayer/roboquant), [README](https://raw.githubusercontent.com/neurallayer/roboquant/main/README.md) |
| **PyPI `roboquant`** | OSS Python library | Separate Python package (`pip install roboquant`). Not the .dev IDE. | [pypi.org/project/roboquant](https://pypi.org/project/roboquant/) |

Do **not** attribute JVM/Kotlin features (CSVFeed, EMACrossover, Jupyter `%use roboquant`, Alpaca/IBKR modules, 150+ TA indicators, Kotlin `run(feed, strategy)`) to the .dev product. Do **not** attribute .dev IDE/workspace/BYOK/chat-to-chart claims to the Kotlin library.

Inside .dev itself, **v1 current** and **v2 `/next`** are also distinct. FAQ on `/next`: the current platform stays available; the new platform is a ground-up rebuild — different workspace, different deployment model, different data.

## Standing QMX bans applied here

- No donor engine adoption (not the v2 “RQ Engine”, not neurallayer backtest `run()`, not Connect webhook execution).
- QMA never executes the money path, including paper.
- QMB never imports `qmf-venue`.
- Ordinary Python stays legal; QML is declaration + plain-Python logic.
- QMX already owns: QMF contracts/toolbox; QMB library+CLI (run loop, orchestrator, TPE, walk-forward, sweeps, data commands, CT-32); QML declaration+plain-Python; QMA daemon/missions/tools/ExperimentSpec; Trading Node paper|live.

## Compact table

| Mechanism | What (transferable pattern, not vendor surface) | qmx_home | status | Official evidence |
| --- | --- | --- | --- | --- |
| Isolated authoring workspace | One isolated container per authoring workspace holding operator-owned files; workspace survives model-budget exhaustion | QMA | extend | ToS §2; Privacy §2.1, §5; FAQ “run out of credits”; `/next` private-container claim is **runtime**, not copied |
| Visible authoring chrome (editor, terminal, files) | Operator-visible file tree + editor + terminal beside the agent, not hidden tool calls | UI | new | First-party blog: Monaco editor + terminal; ToS “cloud-based IDE”; Privacy “files you create or upload” |
| Conversational idea-to-code | Plain-language strategy → clarifying questions → house-language artifacts (QML declaration + Python logic). Not Pine/MQL as QMX languages | QMA | extend | Homepage; FAQ; [natural-language guide](https://www.roboquant.dev/blog/natural-language-to-trading-code) |
| Validate-before-hand-off | Syntax/conformance check **before** a human copies or graduates a candidate. Not a money-path run | QMA | connect | Homepage “validates before you copy”; ToS §7.2 operator must review; QML QL-8 linter already exists |
| Workspace files as agent context | Created/uploaded workspace files are the agent’s working context; operator owns the IP | QMA | extend | Privacy §2.1 Workspace Content; ToS §4.1 ownership; ToS §7.1 code may be sent to model providers |
| Media-to-rules-to-code | Import a transcript/video idea, extract **explicit** rules, fill gaps as documented assumptions, emit testable artifacts | QMA | new | FAQ “import strategy ideas from YouTube”; [YouTube-to-code guide](https://www.roboquant.dev/blog/youtube-trading-strategy-to-code) |
| Cross-dialect import into house language | Convert foreign strategy dialects into QML+Python. Do not add Pine/MQL as first-class QMX languages | QMA | new | FAQ languages + converters; [MQL5→Pine guide](https://www.roboquant.dev/blog/convert-mt5-to-tradingview) |
| BYOK + per-task model routing | Operator-supplied keys; encrypted; route different models per task class. QMA already has a model proxy | QMA | extend | [`/next` BYOK](https://www.roboquant.dev/next); QMA packet `09_MODEL_PROXY_TOOLS_COMPUTE.md` |
| Chat-to-chart preview | Describe an indicator in chat; overlay it on the research chart. Preview only — no live orders | UI | connect | `/next` “Describe an indicator. See it on your chart.” QML already authors CT-16 producers |
| Template-seeded conversation | Start from a starter bot (declaration+logic), customize through conversation | QML | extend | FAQ 50+ templates + “start with a template and customize through conversation”; QML AD-30 template discipline |
| Operator-visible tool/capability set | Named, inspectable surfaces for what the agent may use; capability independent of token wallet | UI | connect | `/next` “What’s inside” named surfaces; pricing FAQ workspace continues without credits; QMA AD-16 capability snapshot |
| Same-artifact research protocol | One strategy artifact for research hosts; live remains node-owned. Confirms QML QL-7; do not copy RQ Engine | QML | reuse | `/next` “Same code runs in backtest and live”; already QML QL-7 + QMB run() + Node seats |

Status vocabulary: `reuse` | `connect` | `extend` | `new` | `undecided`.

---

## Source-linked findings

### 1. Isolated authoring workspace — QMA / extend

**Donor (v1, legal + FAQ).** ToS §2: cloud IDE with “AI-assisted coding, **containerized development environments**, and tools for Python, PineScript, and MQL5.” Privacy §2.1: **Workspace Content** = “Code, trading strategies, files, and other content you create or upload.” Privacy §5: security measures include “**Isolated container environments for each workspace**.” FAQ: if AI credits run out, “Your **workspace and existing strategies continue working**.”

**Donor (v2 `/next`).** “Every strategy runs in its own private container. No one else’s code can touch yours.” That sentence is **deployed-strategy isolation on the RQ Engine**, not the v1 authoring workspace. Transfer the **authoring** isolation idea only.

**QMX already.** QMA environment hierarchy already lists native → CLI → local process → Docker/container → remote container (`09_MODEL_PROXY_TOOLS_COMPUTE.md`). Daemon may deploy a quant/mission/worker to a remote workspace (QMA AD-15 / D15).

**Transfer.** Productize an **authoring ExecutionEnvironment**: isolated, file-backed, operator-owned, detachable from the UI, not a live trading container. Do not copy their cloud container product or per-strategy live runtime.

### 2. Visible authoring chrome — UI / new

**Donor.** First-party blog [Best Pine Script AI Generators](https://www.roboquant.dev/blog/best-pine-script-ai-generators): “Integrated code editor (**Monaco**)”, “**Built-in terminal** for testing.” [Tradovate comparison](https://www.roboquant.dev/blog/best-tradingview-tradovate-automation-tools): “Built-in **code editor and terminal**.” ToS: cloud-based IDE. Privacy: files created or uploaded.

**Not in official docs (excluded from this row):** YouTube tutorial claims of zip export, plan/act modes, per-plan workspace quotas. Those remain uncertainties.

**QMX already.** QMA owns the tool registry (filesystem, shell, tests). QMA v1 explicitly removed `ui_view`. There is no ratified authoring IDE chrome.

**Transfer.** UI owns **visible** editor / terminal / file tree bound to a QMA ExecutionEnvironment. Pattern is tool visibility, not cloning Monaco, RoboCharts, or their layout. Closing the UI must not kill the daemon.

### 3. Conversational idea-to-code — QMA / extend

**Donor.** Homepage: “Describe Your Strategy. AI Writes the Code.” FAQ: “Describe what you want in plain English—our AI writes the code. Or start with a template and customize through conversation.” [Natural-language guide](https://www.roboquant.dev/blog/natural-language-to-trading-code): intent extraction → parameter identification → logic structuring → code generation → validation; agent “asks clarifying questions if needed”; emits Pine Script or Python. `/next` hero: “Idea → code → backtest → live.”

**QMX already.** QMA has missions, tools, ExperimentSpec. QML is the **only** governed authoring library (declaration + plain-Python logic). Ordinary unregistered Python remains legal in QMB.

**Transfer.** A QMA authoring mission that interviews the operator and emits **QML artifacts** (CT-33 declaration + logic package) plus an ExperimentSpec candidate. Never a QMA path to paper or live. Never adopt Pine/MQL as house languages.

### 4. Validate-before-hand-off — QMA / connect

**Donor.** Homepage: “Code validates before you copy—no more compile errors.” Marketing elsewhere: “always compiles.” ToS §7.2: AI code is as-is; **operator** must review and test. There is **no public compiler API**. Treat “always compiles” as a claim, not a spec.

**QMX already.** QML QL-8 Layer-1 declaration linter (schema, unit-kinds, footprint, templates) and Layer-2 sandboxed conformance (host spawns isolation; QML owns the verdict; **no Book present**). QMB `run()` is the research host, not an agent tool.

**Transfer.** Connect a QMA **read-only validate tool** to QML’s linter/conformance. That is missing **wiring**, not missing function. Forbidden: QMA calling QMB `run()` as a hidden backtest-to-trade, QMA paper/live, or copying a Pine compiler.

### 5. Workspace files as agent context — QMA / extend

**Donor.** Privacy §2.1 workspace files are collected as content. Privacy §3: used to “provision cloud development environments, and deliver AI-assisted coding features.” ToS §4.1: operator retains IP. ToS §7.1 / Privacy §4.2: prompts and code are sent to Anthropic/OpenAI (v1). FAQ: “Encrypted, never shared, never used for training” — **conflicts** with ToS provider-send; see uncertainties.

**QMX already.** QMA context/memory/knowledge packet; filesystem tools.

**Transfer.** Authoring-workspace tree is first-class context for the authoring Quant. Do not copy their analytics stack (GA4, Facebook Pixel, Clarity) or their provider-send policy.

### 6. Media-to-rules-to-code — QMA / new

**Donor.** FAQ: “You can also import strategy ideas from YouTube videos.” [YouTube-to-code guide](https://www.roboquant.dev/blog/youtube-trading-strategy-to-code): transcript → extract **only explicit** rules, mark `NOT SPECIFIED`, fill gaps as documented assumptions, pseudocode, then platform code; then backtest (in QMX that last step is QMB after human promotion, not QMA).

**Transfer.** New QMA tool: ingest transcript/text (and later other media), emit a structured rule sheet + draft QML artifacts with explicit gap flags. Human reviews. QMA still does not run the money path.

### 7. Cross-dialect import — QMA / new

**Donor.** FAQ: “Pine Script for TradingView, Python for custom bots. We can also convert MQL5/MT5 code to Pine Script.” Conversion guide is a documented product path.

**Transfer.** Mechanism is **import foreign artifacts → house language**, not “become a Pine IDE.” Output is QML declaration + ordinary Python. Pine/MQL remain external dialects, never QMX runtime languages.

### 8. BYOK + per-task model routing — QMA / extend

**Donor v2 `/next` only (not v1 credits).** “Plug in your existing Claude, OpenAI, Gemini, or OpenRouter accounts. End-to-end encrypted, never logged. Route different models per task — Sonnet for code, Gemini for fast Q&A, Opus when it matters.” v1 instead meters **credits** through the platform (ToS §6.4; [pricing](https://www.roboquant.dev/pricing)).

**QMX already.** QMA model proxy: provider/account/deployment routing, quotas, aliases; harness/Role picks model class; proxy picks a healthy deployment.

**Transfer.** Extend the existing proxy with operator-supplied keys and **task-class routing**. Do not copy v1 credit wallets as architecture.

### 9. Chat-to-chart preview — UI / connect

**Donor v2 `/next`.** “Every indicator you build in the chat shows up on your charts — alongside the classics.” Custom indicator named in marketing (`ny_box_v2`) is shown on the same chart as RSI/SMA/Bollinger. This is **visualization of authoring**, not Bookmap cloning.

**QMX already.** QML authors CT-16 producers / confluences. Research charts are a UI concern. QMB already produces run evidence.

**Transfer.** Wire: QMA writes a producer artifact → QML types → UI overlay on research charts. Missing **wiring**. Do not copy RoboCharts, footprint/order-book chrome, or any live order overlay. Preview ≠ paper/live.

### 10. Template-seeded conversation — QML / extend

**Donor.** FAQ: “50+ and growing” templates (RSI, MACD, grid, mean reversion, trend following), “start with a template and customize through conversation.”

**QMX already.** QML AD-30 template discipline is the declaration grammar; family is a keying token (QL-6), not an authority.

**Transfer.** Starter **declaration+logic** examples under QML (ordinary Python legal). Conversation that mutates them is a QMA mission consuming QML types. Do not copy ICT/SMC vendor template packs or their UI gallery.

### 11. Operator-visible tool/capability set — UI / connect

**Donor.** `/next` names inspectable product surfaces: Strategy Workspace, RoboCharts, Order Flow, Optimizer, Live Deploy, Institutional Data, BYOK AI. Pricing FAQ: AI credits are for generation/debug/chat; the **workspace keeps working** without credits.

**QMX already.** QMA AD-16 capability snapshot minted at Agent spawn; tool registry; hooks. Optimizer/walk-forward/TPE already live in **QMB** — do not re-home them in the IDE.

**Transfer.** UI shows the agent’s **actual** QMA capability snapshot and which tools are in play. “Live Deploy / Order Flow / RQ Engine” stay banned as QMA surfaces. QMB optimizer remains QMB; Node remains Node.

### 12. Same-artifact research protocol — QML / reuse

**Donor v2.** Sample `ImbalanceBreakout(Strategy)` with `on_bar` / `self.book` “runs in backtest AND live, unchanged.” Also: walk-forward, Deflated Sharpe, PBO, grid/genetic optimizer — **already QMB’s job** (TPE, walk-forward, sweeps). Copying their engine or optimizer UI is banned.

**QMX already.** QML QL-7: one factory protocol; QMB binds conformant bots; the node hosts seats later. Plain Python bots run in QMB with zero QML imports.

**Transfer.** Reuse QL-7. Treat the donor slogan as confirmation, not a new runtime. Live/paper stay on the Trading Node. QMA’s only money-path output remains a **candidate a human promotes**.

---

## What already exists in QMX

- **QML:** declaration + plain-Python logic, AD-30 templates, QL-8 conformance, QL-7 one protocol for QMB and (later) node.
- **QMB:** library+CLI `run()`, orchestrator evidence, TPE, walk-forward, sweeps, data commands, CT-32. Research host — not an IDE.
- **QMA:** daemon, missions, tools, ExperimentSpec, model proxy, ExecutionEnvironment hierarchy, capability snapshots. **No money-path tools.**
- **QMF:** toolbox/contracts only.
- **Trading Node:** paper | live. Human promotion into live. Paper-before-promotion is outside the node (DEC-0261).
- **UI:** separate product from the daemon (QMA constitution). Authoring chrome not yet a ratified v1 contribution.

## Missing wiring vs missing function

| Gap | Kind |
| --- | --- |
| QMA validate tool → QML QL-8 linter/conformance (no `run()`, no paper) | **Wiring** |
| QMA authoring mission → QML CT-33/logic artifacts + ExperimentSpec | **Wiring** (QMA tools + QML types exist) |
| Chat/producer artifact → research chart overlay | **Wiring** (UI + QML producers) |
| UI display of QMA capability snapshot / tool list | **Wiring** |
| Isolated **authoring** ExecutionEnvironment as a first-class operator workspace | **Function** on QMA (hierarchy exists; authoring productization does not) |
| Visible editor/terminal/file tree | **Function** on UI (do not copy vendor chrome) |
| Transcript/media ingest → structured rule sheet | **Function** on QMA |
| Foreign-dialect → QML converter | **Function** on QMA |
| Operator BYOK into the existing model proxy | **Function** (extend QMA proxy) |

## Recommended architectural ownership

- **QMA** owns authoring missions, isolated authoring environments, model routing/BYOK, file/media context, conversion/validate tools. Never a venue client. Never paper/live.
- **QML** owns the artifacts those missions emit (declaration, logic, templates, family keys) and the conformance gate.
- **QMB** owns research execution (run, optimize, walk-forward) **after** a human (or a non-money QMA candidate hand-off) asks for an experiment. QMA does not become a backtest engine.
- **UI** owns visible chrome: editor, terminal, files, chart preview, capability inspector. Detachable from the daemon.
- **QMN** owns paper|live. Donor Connect/Tradovate/webhook/kill-switch/multi-account fan-out is **not** a QMA or QMB mechanism.
- **QMF** is not an application and takes no donor IDE features.

## Open questions — AD vs Deferred

**Need an AD**

1. **Authoring ExecutionEnvironment vs live node process.** Confirm authoring containers cannot place orders (including paper). Likely a one-line AD on QMA env kinds: `authoring | research | (never venue)`.
2. **QMA validate vs QMB run.** Pin that the authoring loop may call QML linter/conformance only; a backtest is a QMB experiment the operator (or a later mission **without** execution tools) requests. Closes a likely builder confusion with donor “idea → backtest → live.”
3. **House language.** Explicitly refuse Pine/MQL as QMX runtime languages; conversion is import-only. Ordinary Python stays legal.

**Can stay Deferred**

- v2 chat-to-chart and BYOK until `/next` is more than a waitlist page (closed beta Jul/Aug 2026; GA TBA).
- Media ingest beyond pasted transcripts (true video/audio).
- Whether UI editor is Monaco-class or a thinner buffer — implementation choice, not architecture.
- Credit/wallet metering, SMS trading alerts, Connect pricing, prop-firm fan-out.
- File zip export / plan-act modes (YouTube only; not official docs).

## Do not copy

- **RQ Engine** and all live-runtime claims (tab-close survival, broker reconcile, contract rolls, per-strategy live containers, restart-safe flatten).
- **RoboQuant Connect** / Tradovate OAuth / TradingView webhooks / multi-account fan-out / kill-switch-as-execution-product (`connect.roboquant.dev`, `/tradingview-to-tradovate`). Money path belongs to Node, and QMA must not grow an execution tool.
- **Vendor UI:** Monaco branding, RoboCharts, footprint/order-flow chrome, their dashboard/P&L calendar, template gallery look.
- **Pine Script / MQL5 / NinjaTrader as QMX languages** (donor languages; QML + ordinary Python only).
- **neurallayer/roboquant** Kotlin APIs, Jupyter, Maven modules, feeds, brokers.
- **Bundled Databento-grade data product** and symbol packs as an IDE feature.
- **v1 credit-wallet billing** as architecture.
- **“Always compiles”** as a guarantee (contradicted by ToS as-is).
- Any path where the authoring agent deploys live or paper.

## Uncertainties

- v1 IDE vs v2 `/next` are different products; several high-value authoring claims (BYOK, chat-to-chart, Strategy Workspace name) are **v2 waitlist marketing**, not GA docs.
- No public workspace file API, compiler, or agent-tool schema — editor/terminal details rest on first-party **blog** copy, not a reference manual.
- FAQ “never used for training” vs ToS/Privacy “code may be sent to Anthropic and OpenAI.”
- Published prices disagree across pages ($1–10 hobby copy on third-party directories; first-party blog $15/$30; affiliates $49 Pro; Connect $39.90). Irrelevant to architecture, signals doc drift.
- Official YouTube walkthroughs (file zip export, plan/act, workspace quotas) were **not** treated as documentation.
- Closed beta access was not available; behavior-demonstrated evidence is therefore absent.

## Sources fetched this sitting

- https://www.roboquant.dev/
- https://www.roboquant.dev/next
- https://www.roboquant.dev/terms
- https://www.roboquant.dev/privacy
- https://www.roboquant.dev/docs
- https://www.roboquant.dev/pricing
- https://www.roboquant.dev/blog
- https://www.roboquant.dev/blog/natural-language-to-trading-code
- https://www.roboquant.dev/blog/roboquant-vs-pineify
- https://www.roboquant.dev/blog/best-pine-script-ai-generators
- https://www.roboquant.dev/blog/youtube-trading-strategy-to-code
- https://www.roboquant.dev/blog/convert-mt5-to-tradingview
- https://www.roboquant.dev/blog/best-tradingview-tradovate-automation-tools
- https://www.roboquant.dev/tradingview-to-tradovate
- https://connect.roboquant.dev
- https://github.com/neurallayer/roboquant and raw README (distinction only)
