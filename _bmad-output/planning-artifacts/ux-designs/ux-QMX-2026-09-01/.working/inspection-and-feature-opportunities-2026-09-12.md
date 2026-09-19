# QMX — completed reference pass and feature opportunities

Date: 2026-09-12. Research findings and proposals, not approved IA or implementation claims. Read with `reference-feature-mapping-2026-09-11.md` and `../.memlog.md`.

Later correction: mentions below of a contextual agent dock (F14 and consequence 8) are historical proposals, not an adopted fixed placement. The operator rejected a universal/permanent right-side dock. Agent access and exact-context continuity remain relevant; placement is open, and the human-facing layout leads.

## What was actually inspected

- StrategyQuant: previous browser pass covered generation, robustness, advanced features, rule-template screenshots and Custom Projects' task palette. This pass opened the product menu, QuantAnalyzer What-if, Money Management Simulator, Portfolio Master, QuantDataManager, and AlgoCloud home/how-it-works pages.
- QuantConnect: previous browser pass covered Projects, Research Pipeline and IDE. This pass revisited IDE, opened Research and Research Deployment, and read notebook, compute, collaboration and methodological constraints.
- Hermes: launched the installed desktop app, selected an existing QMX conversation, opened its session menu, opened Capabilities, opened the layout editor, and exited the layout editor without selecting a new preset. No messages sent, capabilities installed, model changed, code restored or session deleted.
- Fincept: user-provided screenshot only. No claim of installed-app inspection.
- RoboQuant: existing Grok video report is available at `workroom/research/roboquant-video-ux.md`; not rewatched. It remains a weak donor after the user's corrections.
- Public product pages and documentation are not equivalent to testing paid/installed products. No authenticated QuantConnect workspace was manipulated.

## Expanded mechanism inventory

Each QMX entry below is an adaptation proposal. Current documentation is a foundation, not proof that a usable feature exists. Priority means order of design exploration, not engineering commitment.

| ID / source mechanism | Purpose, independent of vendor UI | QMX surface and adaptation | Backend/evidence question | Design order |
|---|---|---|---|---|
| F01 SQ template generation | Freeze the thesis structure while varying selected conditions | Experiment setup: fixed rules, variable slots, eligible Library primitives, parameter ranges and budget | QML/QMB parameter basis exists in docs; typed rule decomposition is still a documented gap | First |
| F02 SQ candidate databanks/filtering | Keep many generated candidates inspectable and reusable | Candidate table, saved views, lineage, failed/pending/completed distinctions, rejection reasons | Define candidate/result query projection and references; don't create a second STRATS store | First |
| F03 SQ Custom Projects | Repeat a research procedure with stages and intermediate outputs | Procedure view with current step, results, retries, loops and logs; optional visual composition later | Map to QMA graphs/loops/ledger before proposing another orchestrator | First |
| F04 SQ robustness tools | Establish whether results survive changed assumptions | Evidence tabs for walk-forward, sensitivity, Monte Carlo and cross-market comparisons | QMB documents related procedures; exact supported outputs and thresholds need implementation audit | First |
| F05 QA What-if | Compare a result under explicit altered conditions | Named baseline and scenario; visible filters, affected trades, metrics and chart deltas | Distinguish filtering historical trades from rerunning a strategy. Filters can change path-dependent state; a filtered report is not automatically a valid counterfactual backtest | First |
| F06 QA Money Management Simulator | Isolate position-sizing effects | Compare fixed-size and risk-based policies against identical evidence; link a proposed BMS configuration version | A QMX Book may alter admission, exposure and concurrent trades. Trade-list rescaling alone may not simulate the Book; specify replay model and cost assumptions | First |
| F07 QA Portfolio Master | Choose combinations under constraints, not just rank individual strategies | Select eligible bots/versions, objectives, maximum holdings, diversification/sector constraints; compare candidate combinations | Portfolio search, correlation definitions, capital constraints and out-of-sample separation need specific evidence, not assumed parity | Next |
| F08 QA equity control / result comparison | Study operating-policy effects and divergence between results | Baseline vs alternative policy, historical vs observed evidence with comparable intervals | Add exact policy/version, data and execution assumptions; evidence comparison is not permission to change live state | Next |
| F09 QDM ingest and normalize | Make datasets usable across sources/formats | Data work surface: source/coverage, import mapping, timezone, resolution, derived dataset relationship | Audit available import/transform operations and immutable dataset references | First |
| F10 QDM quality review | Explain why evidence may be unreliable | Gap/spike/incorrect-candle table linked to a chart; quality status visible at experiment launch | Define quality outputs and whether anomalies are flagged, excluded or corrected; preserve raw data | First |
| F11 QDM derived clones | Reuse data with different timezones/timeframes | Transformation lineage and preview, with explicit source and derived versions | Vendor auto-update behavior should not silently rewrite QMX experiment inputs | Next |
| F12 QC project continuity | Keep a research undertaking coherent across tools | Hypothesis/ML undertaking links notebooks, Library objects, experiments and results | Project vs Workspace remains open; don't force a file-tree or duplicate object identity | First |
| F13 QC notebook environment | Support exploratory analysis distinct from event-driven backtesting | Notebook as a work tab/tool, not the application shell; kernel location/state and outputs visible | A notebook renderer is not a managed kernel. Audit lifecycle, imports, data access, persistence and cancellation | First |
| F14 QC contextual agents | Work on the selected project with tools, not chat in isolation | Contextual agent dock that can expand into a Hermes-style session workspace | Bind exact object/version/run context, authorized actions and resulting artifacts; QMA ExperimentSpec already supplies a documented bridge | First |
| F15 QC resources | Explain where work runs and what capacity it consumes | Local/server execution indicator, queued/running state, ownership and resource details on demand | Research compute is not a QMX Trading Node. Laptop closure should not be conflated with server-job cancellation | First |
| F16 QC collaboration limits | Avoid concurrent edits corrupting shared work | Show version conflicts and agent/user changes; keep an inspected baseline stable | QC documents notebook simultaneous-edit limits and IDE multi-session sync issues. These are design warnings, not requirements to copy its limitation | Next |
| F17 AlgoCloud visible rules and cloud execution | Let non-specialists inspect strategy logic; separate browser from execution location | Clear rule summary, editable allowed parameters and explicit execution target | Already aligned with QMX intent; no adoption of donor deployment powers or broker assumptions | Later |

### Source evidence

- [StrategyQuant features](https://strategyquant.com/features/), [strategy templates](https://strategyquant.com/doc/strategyquant/strategy-templates/), [Custom Projects](https://strategyquant.com/doc/strategyquant/introduction-to-custom-projects/).
- [QuantAnalyzer overview](https://strategyquant.com/quantanalyzer/), [What-if](https://strategyquant.com/quantanalyzer/what-if-scenarios/), [Money Management Simulator](https://strategyquant.com/quantanalyzer/money-management-simulator/), [Portfolio Master](https://strategyquant.com/quantanalyzer/portfolio-master/).
- [QuantDataManager](https://strategyquant.com/quantdatamanager/): import, source coverage, tick/minute data, chart/table review, gaps/spikes/incorrect candles, timeframe/timezone transformations and verified downloads are described on the page.
- [QuantConnect IDE](https://www.quantconnect.com/docs/v2/cloud-platform/projects/ide), [Research](https://www.quantconnect.com/docs/v2/cloud-platform/research), [Research Deployment](https://www.quantconnect.com/docs/v2/cloud-platform/research/deployment).
- [AlgoCloud](https://algocloud.com/), [How it works](https://algocloud.com/how-it-works/). The latter visibly contains multiple Lorem ipsum sections and inconsistent levels of detail. Treat as weak evidence, not a reliable complete specification. No broker-support parity claim.

The currently expanded StrategyQuant product menu listed StrategyQuant, AlgoCloud, QuantDataManager and QuantAnalyzer. AlgoWizard was observed as a rule-authoring area in the earlier SQ screenshots; a separate current AlgoWizard product application was not tested.

## Hermes interaction study

Observed installed version: v0.21.1 (+759), 9e6c410. This is newer than the initial user screenshot, so do not attribute every observed feature to that screenshot.

| Interaction | Observed behavior | QMX lesson |
|---|---|---|
| Open saved session | Clicking a QMX session changed the central conversation tab/title and loaded its transcript. The independent browser pane stayed open at the same target | Selected work and supporting tools can coexist without forcing a full-page navigation |
| Session navigation | Pinned sessions, project groups, unread/finished indicators, model/message-count metadata and local session actions were visible | Persistent work needs recognizable identity and activity, not a flat anonymous chat list |
| Session menu | New window, terminal, rename, pin, unread, appearance, copy ID, branch, export, move-to-project, archive and delete appeared | Keep secondary operations discoverable but out of the primary reading path; don't copy every action into QMX |
| Layout editor | Default, Focus, Terminal deck, Quad, custom grid and save-as-template were visible; pane zones showed Sessions, conversation, Browser, Review and Files | Saved arrangements can accommodate different attention modes without making each arrangement a new domain |
| Exit layout editor | Done returned to the previous conversation/browser arrangement; no template selection was made | Layout editing should be a temporary mode, not permanent chrome |
| Capabilities | Central area switched to Skills/Tools/MCP management while the independent browser remained. Skills used list/detail panes and an embedded catalogue below | Even the agent world has task-specific interiors; it is not all a chat transcript |
| Preview failure | Browser pane clearly showed server-not-found for localhost:9001, with retry and ask-agent recovery actions, while the agent gateway was ready | Different subsystems need independent states; one global green light is misleading |

Source-only hover findings: local `src/components/ui/pane-tab.tsx` describes/reifies a hover-revealed close control without changing tab width. `src/app/chat/sidebar/chrome.tsx` includes hover/focus-visible new-item controls; `session-row.tsx` includes hover title treatment. These supplement observed clicks; hover timing and visual behavior were not live-tested because the available Windows API has no documented hover/move method. Do not claim otherwise. No source was changed.

Not tested: drag/resize persistence, all layout presets, active-agent stop/retry, terminal commands, computer-use execution, browser annotation, server job continuation after shutdown, or all settings. We have sufficient evidence for layout ideation, not an exhaustive Hermes product audit.

## QMX design consequences

1. A department is a context for work, not a forced clone of Hermes and not a backend package.
2. Distinguish global destinations, department tools and open work. Tabs with three indistinguishable meanings will recreate the confusion being solved.
3. A shared bot/version/result can appear from Library, experiments or Trading Node without creating three records.
4. Comparison is a first-class activity: pin a baseline, change one assumption, inspect the evidence delta and retain the candidate version.
5. Agents need visible target context and version. Switching the inspected object must not silently retarget an already-running agent action.
6. Proposed BMS/Book edits and simulations must remain visibly distinct from the currently operating configuration. Trading Node owns operational state; research tools can link into it.
7. Data, kernels, runs, agents and trading connections need separate availability states. A closed tab is not necessarily a cancelled job.
8. We should prototype a dense table-plus-evidence workspace and a contextual agent dock before polishing generic dashboard cards.

## Implementation readiness

No production code was written. No assertion that all 17 opportunities are absent from the backend. The next implementation audit should classify each selected feature as implemented with evidence, documented/unwired, partially supported, or genuinely new. Exact API/read-model/event contracts follow the first approved UI slice, before Grok builds that slice.
