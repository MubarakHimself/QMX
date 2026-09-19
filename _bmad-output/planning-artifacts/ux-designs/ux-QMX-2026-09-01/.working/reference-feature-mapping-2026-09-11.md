# QMX reference inspection and department needs

Status: research and design proposals, not approved information architecture. Latest operator dictation overrides earlier shell assumptions. Canonical decisions remain in ../.memlog.md.

## Inspection evidence

Browser inspection completed for StrategyQuant's generation, robustness and advanced feature categories; expanded robustness and advanced controls; navigated strategy templates and opened both screenshot-gallery images; navigated Custom Projects and opened its task-palette screenshot; inspected QuantAnalyzer features. Navigated QuantConnect Projects, Research Pipeline and IDE; inspected the pipeline illustration and its documented card/agent interactions. These are public product pages and official documentation/screenshots, not hands-on tests of an installed StrategyQuant application or an authenticated QuantConnect account.

Sources:
- https://strategyquant.com/features/
- https://strategyquant.com/doc/strategyquant/strategy-templates/
- https://strategyquant.com/doc/strategyquant/introduction-to-custom-projects/
- https://strategyquant.com/quantanalyzer/
- https://www.quantconnect.com/docs/v2/cloud-platform/projects
- https://www.quantconnect.com/docs/v2/cloud-platform/research-pipeline
- https://www.quantconnect.com/docs/v2/cloud-platform/projects/ide

Hermes update, 2026-09-12: the installed desktop app was successfully launched and inspected with Windows computer use. Session switching, the session actions menu, Capabilities and the layout editor were opened. See `inspection-and-feature-opportunities-2026-09-12.md` for observed behavior and explicit limits. Earlier inability to inspect Hermes is superseded. Fincept remains a screenshot-only reference.

## Concrete feature mappings

| Observed reference feature | QMX adaptation candidate | Existing documented basis / remaining work |
|---|---|---|
| SQ templates keep strategy structure while generating placeholder conditions; building-block table selects signals, weights and parameter ranges | Experiment setup chooses what is fixed, what may vary, eligible Library building blocks and search budget | QML parameter space/footprint and QMB sampling already documented. Typed mechanism decomposition is deferred GAP-0085; don't claim arbitrary condition generation exists |
| SQ generates multi-symbol/multi-timeframe candidates | Experiment scope shows instrument roles, timeframes and data dependencies together | QML footprint and QMB stream sets already provide basis; UI remains to design |
| SQ retests candidates under different markets/settings | Compare candidate versions against explicit datasets and conditions | QMB resolved run-config, split manifests and result identity already documented |
| SQ walk-forward, Monte Carlo, SPP, optimization profiles and stable parameter regions | Result workspace compares parameter sensitivity and robustness alongside ordinary performance | QMB already documents optimization/sensitivity, MC, significance and walk-forward. SQ-specific SPP parity is not established; procedure thresholds remain unresolved |
| SQ automated filtering across metrics and test results | Candidate table supports saved filters, rejection reasons and inspectable evidence | QMB publishes measures; verdicts are reader-derived. Filtering must not become automatic live promotion |
| SQ Custom Projects chains build/retest/optimize/filter, loops, waits, notifications and external scripts | Experiment procedures expose stages, current work, intermediate candidates and resumption | QMA Graph Templates, loops, tasks and Experiment Ledger already documented. Need user-facing procedure composition, not a new generic orchestration backend by assumption |
| SQ charts show trades/indicators; equity view includes excursions | Selecting a result or trade opens corresponding chart evidence | QMB CT-32 extensions already include chart-series and trade-event references |
| QuantAnalyzer compares money management, what-if time filters and portfolio combinations | Analyst compares hypotheses; portfolio work evaluates combinations and Book/BMS configuration effects | Existing QMF risk and QMB replay basis; portfolio search capability and exact metrics require audit, not assumed implemented |
| QC Project connects notebooks, backtests, optimizations and deployments | An undertaking links its hypothesis, artifacts and runs across departments | Useful concept; Project versus Workspace remains unresolved; no mandatory file-tree layout |
| QC Research Pipeline links project cards to running agents and deployment output | Department overview opens the relevant experiment and its agent session together | QMA ExperimentSpec/ledger, actor and task references already supply linkage concepts |
| QC IDE has project-context AI panel, resource selection, console and split editor | Agent can accompany selected work; show execution location/resources when relevant; allow side-by-side comparison | Adapt to Hermes and QMA. Don't copy QC's money-path tools or require code editor as main canvas |

## Documentation findings that change the design

1. docs/components/qma-core.md AD-7 defines Desk as an organizational/workspace unit and Profile as presentation-only grouping. Five existing desk slugs are research, trading, dev, analysis and pm. Display consolidation is permitted without changing identity or permissions.
2. Vocabulary conflict: that document names the PM Role Product Manager; the operator's quantitative role description names Portfolio Manager. Keep this discrepancy visible for reconciliation; no silent backend rename.
3. docs/decisions/ADR-0017-qmb-experimentation-library.md records the Lean-CLI-shaped inspiration explicitly. docs/components/qmb.md already covers research functions, optimization, sensitivity, statistical procedures and result rendering. These are documented capabilities, not newly discovered requirements and not implementation proof.
4. docs/contracts/ct-47-qma-experiment-spec.yaml already connects QMA and QMB through ExperimentSpec, candidate handles, lineage and an Experiment Ledger. Parameter changes use config references; no Git branch per parameter. Thus agent/experiment UI separation need not imply disconnected work.
5. docs/components/qml.md defines a bot as declaration plus versioned Python logic. Bot profile identity should use those definitions; measured stats come from identified result artifacts, not QML inventing performance numbers.
6. A backend extension contract does not prove arbitrary runtime UI extensions exist. Department tool contribution, placement and lifecycle are still UI design work.

## Department needs map — provisional, not a tab roster

| Work perspective | Operator needs | Agent needs | Useful working surface |
|---|---|---|---|
| Research | Source ideas, inspect data, specify hypotheses, compare evidence | Sources, datasets, hypothesis context, notebook/analysis tools | Hypothesis record, data preview, notebook or analysis panel, experiment links |
| Development | Build or revise bot logic, confluences and dependencies; inspect versions | Library definitions, allowed edits, validation tools | Library object detail, declaration editor, optional code/diff and validation results |
| Analysis / experimentation | Configure searches, track batches, understand failures and robustness | ExperimentSpec, permitted compute, candidate/result handles, ledger | Experiment setup, candidate table, run progress, comparative charts and explanations |
| Portfolio work | Compare diversification and capital/risk arrangements | Read/calculation access to candidates and Book/BMS definitions | Combination comparison and configuration evidence; live operations remain within Trading Node |
| Trading | Understand deployed system state and respond to operational issues | Authorized observations, diagnostics and escalation paths | One Trading Node area with its Books/BMS/risk/positions/events and relevant controls |

Library is shared across these perspectives. Departments may share tools and objects without duplicating records. The operator can move between perspectives; these are not five isolated applications or a finalized number of departments.

## Navigation proposal to test

Keep three responsibilities distinct: global destination selection; local department navigation; currently open work. Test a thin global left rail with a collapsible labelled department sidebar beside it, and work tabs above the department canvas. Agents open against the selected work in a dock that can expand into the Hermes-style session surface. This is a proposal, not an adopted layout. A top global switcher remains a comparison option suggested by Fincept.

Tabs must answer whether they represent departments or individual work items; this is not settled. Avoid introducing both layers with identical-looking tabs before that distinction is tested. Department overview does not imply generic KPI cards: show current work, useful evidence and decisions appropriate to that department.

## Bot profile proposal

The FC/FIFA analogy means recognizable identity plus useful attributes and track record, not a sports-card visual style or an invented overall score. Candidate content: bot name/version/family and intended behavior; declared parameters and data footprint; measured results labelled by dataset, period, run configuration and evidence class; robustness detail; lineage; operational bindings when present. The same bot may be opened from Library, experiment results or Trading Node. Different views emphasize different information while preserving identity. Missing or incomparable measurements stay explicit.

## Open work

- Hermes core interactive inspection completed on 2026-09-12. Live hover timing, drag/resize behavior, running-agent interruption and restart recovery are not exhaustively tested.
- Resolve PM terminology and Project/Workspace distinction during design discussion.
- Validate department task boundaries and global/local/tab placement visually in Penpot.
- Audit implementation separately before calling a documented capability built or a proposed capability missing.
- Keep chart language/preferences and community-library choices from earlier memlog; no new visual identity selected here.
