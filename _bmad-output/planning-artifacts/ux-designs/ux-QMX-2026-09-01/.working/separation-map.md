# QMX provisional separation map

Status: discussion proposal grounded in confirmed user intent and existing docs. No department count, menu placement or full layout is finalized. No implementation authorization.

## Confirmed anchors

- A tab opens a full work environment with its own local layout; global navigation must not flatten everything into one generic canvas and agent dock.
- Five quantitative perspectives inform daily work and agent organisation: Researcher, Analyst, Developer, Trader and Portfolio Manager. QMA provides a documented foundation, not a command to clone its ontology into navigation.
- Cross-perspective sharing is essential. STRATS informs the shared Library; the product Library itself still needs designing/building.
- Latest clarification: STRATS is the relatively simple library/database-like collection populated in advance so QMX has strategies ready to test. Do not inflate its implementation into a major dependency or require reproducing its internals. The product Library can be QMX's own implementation. Broad experimentation, not Library complexity, is the central design concern.
- QMX must support diverse and extensible experimentation, including genetic approaches and user-defined research, drawing mechanisms from QuantConnect and StrategyQuant. Do not reduce this to one fixed backtesting funnel; resource limits and permissions remain separate technical questions.
- Latest open-lab clarification: experimentation is an undertaking, not a mandatory sequence of research, development and analysis screens. A person may supply the resources, request discovery, start from a video/paper/article/Library item, write ordinary Python, or repeat an existing procedure. New research is optional when the required resources are already available. QML/QMB are available tools, not compulsory wrappers around every exploratory action.
- Agents may assist interactively or work as a coordinated team with explicit instructions, tools, acceptance conditions and durable work records. The operator's overnight example requires work to continue when the laptop is off, not merely when a tab is closed.
- Agent interpretation is not measured evidence. The intent is tool-produced results that agents cannot rewrite or improve by manipulating the evaluation. Reproducible execution alone does not establish a correct method or valid trading edge.
- Trading Node is one integrated operational area: do not duplicate Book/BMS/risk/live ownership across standalone worlds.
- QMB is an independently useful experimentation/backtesting library with CLI/Python access; QML supplies structured bot authoring. They must not become UI-only services by assumption.
- Extensibility must be available to an operator who does not inspect source code, not only to developers writing plugins.

## Daily-purpose lenses — proposed boundaries to examine

These rows describe work responsibilities, NOT five approved top-level tabs. One person can move between them; agents may assist or continue work independently.

| Perspective | Purpose of the work | Operator work | Agent participation | Shared material used/produced |
|---|---|---|---|---|
| Research | Turn questions and sources into testable ideas | Inspect sources/data; state hypotheses and uncertainties; explore notebooks | Source extraction, data inspection, hypothesis variants, research assistance | Sources, primitives, hypotheses, datasets, notebooks, experiment references |
| Development | Make an idea expressible and executable | Compose/edit templates and bot declarations; inspect logic, versions and conformance | Author proposed changes, explain dependencies, execute allowed validation | Library primitives/templates, Bot definitions and logic versions, validation results |
| Analysis | Establish what results mean and what changes matter | Compare candidates, assumptions, robustness, distributions and failures | Run analyses, locate evidence, explain differences and limitations | Identified results, candidate versions, scenario definitions, comparison reports |
| Portfolio work | Examine combinations and capital/risk arrangements | Compare bot combinations, sizing and proposed Book/BMS configurations | Calculate alternatives and document evidence/assumptions | Bot evidence, configuration versions, portfolio candidates; operational references |
| Trading | Operate and understand the trading system | Inspect actual bindings, positions, Book/BMS state, events and allowed operational actions | Observe, diagnose and assist within existing authority | Trading Node's operational records plus shared definitions and historical evidence |

Open: experimentation includes setup, execution and analysis, so it may span Research/Development/Analysis. Determine whether the Experimentation Lab is a shared world, a local tool exposed in several worlds, or a world with several working modes. Do not choose simply by counting backend packages.

The user has not finished describing the progression to live use. Their latest dictation is intake, not approval of a full pipeline or of this table. Research is a capability within experimentation when needed; the Research perspective is not thereby deleted or made the mandatory entry point.

Open: QMA docs name the `pm` Role Product Manager; the operator describes Portfolio Manager. Use Portfolio Manager for the user's intent in this map, but do not silently rename backend identity or treat the discrepancy as settled.

## Shared objects, not duplicated departmental products

Proposed sharing map:

| Shared material | Why several worlds need it | Boundary to resolve |
|---|---|---|
| Source knowledge and strategy primitives | Research extracts them; development composes them; analysis checks their evidence | What STRATS already defines versus what the product Library must expose |
| Templates | Research experiments, developers author, portfolio/trading work may use Book/BMS templates | Distinguish strategy template, Bot definition, Book template and BMS template; do not invent one interchangeable template type |
| Bot identity/profile | Recognize the same bot from Library, experiment results and operations | Declaration/attributes versus measured statistics versus operating state; FC/FIFA is a mental model, not a visual prescription |
| Datasets and transformations | Hypothesis exploration, backtests and analysis require related data | Preserve dataset identity, provenance and allowed access; distinguish live observations from replay inputs |
| Experiments, candidates and evidence | Several perspectives contribute to or inspect the same undertaking | Ownership, lifecycle, reproducible inputs and saved comparisons; Project/Workspace relation remains open |
| Agent context | Agents need exact relevant work regardless of where invoked | Selected objects/versions, execution location and allowed actions; no silent retargeting on tab switch |

Sharing means references and appropriate access, not blanket cross-world reads or multiple competing canonical records. Product-level Library views need not mirror a filesystem directory tree.

### Versioning clarification

Confirmed intent: the Library should carry Git-like history/variants and relationships for strategies and Book/BMS definitions, without requiring GitHub. A human approves the specific strategy variant for its intended Book before live use; paper testing belongs before promotion. This is not approval of the whole lifecycle, a promise of profitability, or permission for QMA to trade.

Documented basis: `docs/components/qmf-registry.md` already defines content-fingerprinted records, append-only lineage, branching Book/BMS definitions, separate bindings and human promotion. CT-47 already distinguishes code changes from configuration changes: no Git branch per parameter mutation. Preserve those semantics; a Library view is not a second registry. The appropriate product-level history, comparison and approval surfaces are still open.

### Desktop STRATS check — bounded, read-only

The directory is `C:/Users/Mubarak/Desktop/Stats`; its `README.md` identifies it as STRATS. The inspection found canonical Markdown/YAML with a rebuildable SQLite index, a 239-primitive dictionary, and a source-faithful strategy-DNA/knowledge graph model. Current strategy content is one explicitly labelled layout demonstration; this inspected folder is not evidence of a populated source corpus. The user-mentioned roughly 3,000 MT5 articles were not located or audited in this bounded check and may be elsewhere.

Sources: `Stats/README.md`, `dictionary/README.md`, `schema/strategy-dna.md`, `schema/graph.yaml.md`, `catalog/strategies.md`, and `strategies/STRAT-000001-asian-high-london-reversal/identity.md`. The graph is knowledge, not an executable QMX strategy or proof of trading validity. Treat this collection as an optional input and useful semantic reference, never a prerequisite to building the lab or a mandate to reproduce its internals.

## Extensibility questions must accompany placement

For every proposed addition ask:

1. Is this a new template/configuration, a composition of existing capabilities, or genuinely new executable behavior?
2. How does a non-coding user discover, understand, configure and use it?
3. Which worlds expose it, and does it add a local tool, a view or a new world?
4. What definitions/data does it read or create, and who owns those records?
5. How are versions, dependencies, compatibility and required permissions visible?
6. What persists if the tab closes or the laptop disconnects?

These are questions, not an adopted plugin protocol. Do not promise that every arbitrary new algorithm can be authored with no code. The required outcome is meaningful end-user extension without source access; its supported range must be specified.

## Next design focus

Start with what the lab must make available, rather than a compulsory workflow: working material, executable methods, permitted human/agent collaboration, execution control and inspectable evidence. These are capability questions, not five panes or approved menus.

Use contrasting examples to test the separation: a supplied dataset and a Python question with no new research; a video or paper requiring source inspection before a hypothesis; and an overnight batch with agents and bounded verification loops. None is the universal journey. Determine which needs share records/tools and which justify a distinct local layout, while preserving the tab-opens-a-world principle. The exact Project/Workspace relationship and world roster remain open.
