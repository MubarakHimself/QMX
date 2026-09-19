# QMX UX — Discovery Synthesis & Open Decisions

**Session:** 2026-09-16 · Update mode · Resuming `ux-QMX-2026-09-01`

---

## Navigation Resolution

Your two ChatGPT images reveal the exact tension the session has been circling:

| | Image 1 (Dashboard) | Image 2 (Agents) | Accepted Direction (Memlog) |
|---|---|---|---|
| **Global nav** | Persistent left sidebar | Horizontal top bar | Thin left activity rail |
| **World tabs** | Not shown | Top bar IS the nav | Durable tabs across top |
| **Local nav** | N/A (dashboard surface) | Left agent categories | World-owned sidebar |
| **Right panel** | Agent Status (summary) | Agent context/params | Independent resource host |

**The reconciliation:** Image 1's left sidebar IS the global rail — but too wide. Image 2's top bar IS the world tabs — but it replaced the rail instead of sitting beside it. Your note about "empty space on the far left" in Image 2 confirms you saw this. The fix:

```
┌─────────────────────────────────────────────────────────┐
│ [Rail] │ [Durable World Tabs: Research | Agents | ...]  │
│  🏠    │─────────────────────────────────────────────────│
│  📊    │ [Local Nav]  │  [Central Work]  │ [Right Host] │
│  🤖    │  Sessions    │  Conversation    │  Context     │
│  📈    │  Pinned      │  or Data View    │  Files       │
│  📋    │  Recent      │  or Chart        │  Terminal    │
│  ⚙️    │  ...         │                  │  Review      │
└─────────────────────────────────────────────────────────┘
```

- **Rail** (far left, always visible, thin ~48px): Icons for each world + settings + profile
- **Tabs** (top, durable): Opened worlds as browser-like tabs, closeable
- **Local nav** (inside each world): World-specific sessions, categories, tools
- **Central work** (main): Conversation, chart, editor, evidence — depends on world
- **Right host** (collapsible): Context panel, files, terminal, agent sessions — Codex/Hermes pattern

This matches: your accepted `layout-common-workspace.png` direction, the Hermes/Codex references, and both ChatGPT images when corrected.

---

## Information Architecture — Proposed Surface Map

Based on the full memlog, ChatGPT images, separation map, and feature register:

| World | Rail Icon | Purpose | Local Navigation | Key Surfaces |
|---|---|---|---|---|
| **Home / Overview** | 🏠 | Daily briefing, portfolio summary, agent status, alerts | Minimal — summary cards + quick actions | Dashboard (Image 1 style), Recent activity, Quick launch |
| **Research** | 🔬 | Hypotheses, data exploration, notebooks, source extraction | Projects/Notebooks list, Datasets | Notebook editor, Data browser, Source inspector, Agent sessions |
| **Strategies** | 📐 | Strategy library, bot definitions, templates, versioning | Library browser (categories, tags, search) | Strategy detail/FC card, Version history, Template editor |
| **Experiments** | 🧪 | Backtesting, optimization, what-if scenarios, QMB workflows | Experiment list, Running jobs, Results | Experiment setup, Progress/results, Comparison view, Workflow editor |
| **Agents** | 🤖 | Dedicated agent workspace (Image 2 pattern) | Agent categories (Trading/Research/...), Pinned, Recent | Conversation + right context panel, Quick actions, Workflow builder |
| **Markets** | 📊 | Live data, charts, watchlists, news | Asset class tabs, Watchlists | Chart workspace, Market overview, News feed |
| **Portfolio** | 📈 | Books, BMS, positions, risk, asset allocation | Portfolio sections (Crypto, Forex, Equities...) | Portfolio dashboard, Book/BMS config, Risk metrics |
| **Trading** | ⚡ | Live operations, orders, execution, kill switch | Active bots, Orders, System log | Trading Node, Order management, Position monitor |
| **Settings** | ⚙️ | Account, connections, API keys, preferences | Settings categories | Configuration panels |

> [!NOTE]
> The five quant perspectives (Researcher, Analyst, Developer, Trader, Portfolio Manager) are **lenses that work across worlds**, not one-to-one with worlds. A Researcher primarily lives in Research + Experiments. A Trader primarily lives in Trading + Markets + Portfolio. The worlds organize work surfaces; the perspectives organize agent behavior and contextual recommendations.

---

## New Concept Integration

### 1. N8N-Style Workflow Editor

**Where it fits:** Inside the **Experiments** world and accessible from **Agents**.

An experiment is fundamentally a workflow: data in → process → evidence out. The N8N concept maps naturally to QMX:

| N8N Concept | QMX Equivalent |
|---|---|
| Node | A step: data source, transform, backtest run, analysis, filter |
| Connection | Data flow between steps |
| Workflow | An Experiment definition (saveable, versionable, rerunnable) |
| Trigger | Manual, scheduled, agent-initiated, or event-driven |
| Execution | QMB/QMF running the workflow on local or remote |

**Agents generate workflows.** When you say "test this hypothesis across 5 timeframes with walk-forward validation," an agent can compose the workflow visually as nodes, you approve, it executes. The workflow IS the experiment definition — reproducible, inspectable, versionable.

**Storyboard becomes the workflow canvas in build mode** — collect sources, data, strategies, parameters, connect them, then execute. This unifies the storyboard and N8N concepts.

### 2. JSON Render + MCP Apps

**Where it fits:** Agent-generated artifacts and extensible tool surfaces.

| Use Case | Mechanism |
|---|---|
| Agent produces a report/dashboard | Agent outputs json-render spec → QMX renders it using the component catalog |
| Custom analysis view | Defined as a json-render layout with QMX components |
| MCP App integration | Third-party or user-built tools render inside QMX's right-host panel |
| Extensibility without code | Users define layouts/views through the component catalog, not raw HTML/CSS |

**Component catalog = the QMX design system.** Every component that json-render can use is defined in DESIGN.md. Agents can only compose from this catalog — safe, predictable, on-brand output.

### 3. Core Pilot Agent

**Proposed role:** The orchestrating agent for a given world/context. Each world has a Core Pilot that:
- Understands the world's purpose, tools, and data
- Routes requests to specialist sub-agents
- Maintains session context across interactions
- Can generate workflows for the Experiments world

---

## 8 Decisions to Close IA

These are the remaining questions that block spine distillation. I need your call on each:

### DEC-1: World Roster
The table above proposes 9 worlds. **Is this the right set?** Specifically:
- Should Research and Experiments be separate or combined?
- Should Strategies/Library be its own world or a shared panel accessible from everywhere?
- Is Markets a separate world or part of Portfolio?

### DEC-2: Agent Presence
Agents have a dedicated world (Image 2) but also participate in every other world. **How does an agent surface in non-Agent worlds?**
- A) Collapsible agent lane at the bottom of every world (like Cursor's AI bar)
- B) Agent accessible via the right-host panel in every world (Codex pattern)
- C) Command palette invocation (`⌘K` → talk to agent) with the agent appearing inline
- D) Some combination — describe what feels right

### DEC-3: Workflow Editor Scope
The N8N-style editor: **Where does it live?**
- A) Exclusively in Experiments world
- B) In Experiments + accessible from Agents (agents can generate workflows)
- C) Available in any world as a tool (like a notebook)

### DEC-4: Library Organization
The shared Library for strategies, bots, experiments, evidence:
- A) Its own world (Strategies world as proposed)
- B) A persistent left-panel overlay accessible from any world (like a global file browser)
- C) Inline within each world where relevant, with a shared search/browse

### DEC-5: Home Dashboard Density
Image 1 shows Bloomberg-level density. **How dense should Home be?**
- A) Full Bloomberg (as in Image 1) — markets, positions, agents, risk, all at once
- B) Curated summary — key metrics + agent status + alerts, with links to depth in other worlds
- C) Configurable — user chooses widgets/density

### DEC-6: Portfolio Separation
You confirmed Crypto and Forex as separate sections. **Within one Portfolio world, or separate worlds?**
- A) One Portfolio world with tabs/sections (Crypto, Forex, Equities, Commodities, etc.)
- B) Separate top-level worlds per asset class

### DEC-7: Right-Host Panel Default Content
When the right panel is open, **what's the default view?**
- A) Context-dependent (shows agent details in Agents world, chart tools in Markets, etc.)
- B) Always starts with agent context (every world is agent-first)
- C) User configures per world

### DEC-8: Component System
For building the UI components:
- A) shadcn/ui as the component library (proven, composable, code-ownable)
- B) Custom components from scratch aligned to QMX design tokens
- C) shadcn/ui base + json-render for agent-generated surfaces + custom QMX extensions

> [!IMPORTANT]
> I'm presenting these as options to anchor the conversation, not to impose choices. Tell me your picks, adjustments, or if any of these need rethinking entirely. Once these 8 decisions land, I can close the IA and distill both DESIGN.md and EXPERIENCE.md.
