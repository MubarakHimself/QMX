# QMX adaptation opportunities

These are selective proposals, not a requirement to copy every donor feature. Each must survive an independent QMX repository audit.

## Priority summary

| ID | Opportunity | Classification | Priority |
|---|---|---|---|
| QMX-OPP-01 | Extension capability manifest and discovery index | Enabling requirement candidate | Highest |
| QMX-OPP-02 | Typed data-resource/provider contract | Enabling requirement candidate | Highest |
| QMX-OPP-03 | Unified run/job/artifact lifecycle | Enabling requirement candidate | Highest |
| QMX-OPP-04 | Replay-to-live stream boundary | Enabling requirement candidate | High |
| QMX-OPP-05 | Declarative mini-app/widget composition and shared parameters | Enabling requirement candidate | High |
| QMX-OPP-06 | Reproducible dataset/experiment/backtest recipe | Reference scenario | High |
| QMX-OPP-07 | Authoring versus app-use copilot scopes | Enabling requirement candidate | Highest |
| QMX-OPP-08 | Workspace asset graph and template reuse | Reference scenario | Medium |
| QMX-OPP-09 | ML experiment workbench | Optional future app | Medium/conditional |
| QMX-OPP-10 | Macro/intermarket research app pack | Optional future app/reference scenario | Medium/conditional |

## QMX-OPP-01 — extension capability manifest and discovery index

- **User goal:** install or enable a QMX extension and immediately discover what data, operations, apps, agents, streams and jobs it contributes without core edits.
- **Evidence:** OpenBB provider coverage and generated extension assets; `widgets.json`/`apps.json`; Taskade MCP tool taxonomy/templates; LSE resource catalogue.
- **Proposed QMX capability:** versioned extension manifest, generated capability index, typed operation schemas, owner/version/health, required scopes/credentials/entitlements/cost, and explicit unavailable states.
- **Input/output shape:** extension package + manifest → validated registry entries, generated schemas, diagnostics and discoverable app/tool/resource descriptors.
- **Likely owners to investigate:** QMF extension/plugin registry; app shell; QMA tool registry; QML schema/validator; packaging/build/migration code.
- **Normal journey:** install extension → validate manifest → rebuild/index → capabilities appear with owner/version and setup status → user opens a supplied app or invokes an operation.
- **Failure journey:** incompatible version, duplicate ID, missing dependency, invalid schema, unavailable provider, missing credential or failed migration; keep previous registry consistent and report actionable diagnostics.
- **Uncertainties:** QMX’s current extension mechanism, hot reload, package trust, versioning and manifest format are unknown.

## QMX-OPP-02 — typed data-resource and provider contract

- **User goal:** find a dataset/series, understand coverage and provenance, preview a safe slice, then query/export it through a replaceable provider.
- **Evidence:** LSE catalogue/preview/builder/API; OpenBB provider selection, coverage and normalization.
- **Proposed capability:** `DataResource`, `ProviderCapability`, shared query model, provider-specific validated extras, normalized result envelope, warnings, quota/entitlement and provenance.
- **Inputs:** resource/provider, identifiers, fields, resolution, start/end, row limit, transforms.
- **Outputs:** typed table/series/event result plus source/provider, schema, units/timezone, coverage, freshness, warnings, truncation and lineage.
- **Owners:** QMF provider adapters; QMB data catalogue/loader; QMN market-data adapters; shared schema/provenance/secret services.
- **Normal journey:** discover coverage → choose provider or preference → validate symbol/window → preview → query or submit export.
- **Failure journey:** unsupported symbol/resolution, ambiguous mapping, empty window, missing key, entitlement denied, quota exhausted, provider timeout, partial/truncated response or schema drift.
- **Uncertainties:** existing canonical schemas, caching, licensing metadata, symbol master and provider preference behavior.

## QMX-OPP-03 — unified run/job/artifact lifecycle

- **User goal:** start a long operation, see status/logs/cost, cancel safely, and retrieve reproducible artifacts.
- **Evidence:** LSE queued export lifecycle; ML/backtest controls; Taskade trigger/action flows but unverified run contract.
- **Proposed capability:** common job handle across export, transform, backtest, model training, optimisation and report builds; typed state/events/artifacts/failures; budget and approval fields.
- **Inputs:** immutable run request referencing definition versions, data resources/snapshots, parameters, executor, seed and budget.
- **Outputs:** run ID, progress/events, metrics, logs, artifact references/checksums/expiry, terminal state and stable error.
- **Owners:** QMB runner/experiment store; QML execution bridge; QMA flow runtime; QMN operational scheduler; artifact storage; quota/budget/audit services.
- **Normal journey:** validate → estimate/approve if needed → queue → run → stream progress → succeed → inspect/compare/export artifacts.
- **Failure journey:** validation failure, missing data/permission, timeout, worker loss, user cancellation, partial artifacts, exceeded budget, stale input, artifact expiry; retry policy must be explicit.
- **Uncertainties:** whether QMX already has one runner or several domain-specific executors; distributed execution and persistence guarantees.

## QMX-OPP-04 — historical replay to live stream boundary

- **User goal:** initialize a research or trading app with recent history and then continue with live events without confusing replay for live market state.
- **Evidence:** LSE WebSocket replay flag, replay completion and subscription controls.
- **Proposed capability:** typed stream subscription, phase/cursor, event/receive time, replay/live provenance, heartbeat, gap/deduplication and reconnect policy.
- **Inputs:** provider/channel/symbols, optional replay window/cursor, aggregation and entitlement.
- **Outputs:** acknowledged subscription, ordered event envelopes, phase transitions, quota and connection/gap events.
- **Owners:** QMN data-feed/stream manager; QMF provider adapters; QMB replay/backtest feed; event bus and observability.
- **Normal journey:** authorize → subscribe → replay → explicit handoff → live → unsubscribe.
- **Failure journey:** invalid symbol, quota, auth expiry, disconnect, gap, duplicate/out-of-order event, provider clock drift; surface whether recovery is complete.
- **Uncertainties:** current event bus, ordering guarantees, replay store and separation from broker execution.

## QMX-OPP-05 — declarative mini-app/widget composition

- **User goal:** add a new data/ML/trading-neutral mini-app from an extension and compose views that share typed context without core UI edits.
- **Evidence:** OpenBB widget/app declarations, nested parameters and shared bindings; Taskade multi-asset app kits.
- **Proposed capability:** app/widget declaration for operation, parameters, output/view, layout hints, refresh/raw/export policy, shared-parameter edges and optional agent/tool binding.
- **Inputs:** validated manifest/declarations and runtime parameter values.
- **Outputs:** rendered app layout, operation requests, typed view models and persisted user layout/state separate from extension code.
- **Owners:** app shell/layout engine; QMF extension registry; QML authoring/schema editor; shared state/router; QMA tool/citation bridge.
- **Normal journey:** discover app → validate declaration → render controls → execute read operation/job → propagate selected symbol/date/resource to bound widgets.
- **Failure journey:** unknown widget type, invalid binding, conflicting writer/cycle, stale option source, unauthorized operation, untrusted embed or extension upgrade incompatibility.
- **Uncertainties:** QMX frontend framework, sandbox model, existing component registry, layout persistence and cross-module state ownership.

## QMX-OPP-06 — reproducible dataset, experiment and backtest recipe

- **User goal:** configure a derived dataset or experiment once, rerun it reproducibly, compare results and understand lineage.
- **Evidence:** LSE builder’s source/window/features/cross-asset/time filters; ML configuration; backtest setup; LSE Terminal/Brue repository concepts.
- **Proposed capability:** versioned recipe/definition with exact data binding, transforms, costs, split policy, executor version and immutable run references.
- **Inputs:** sources/snapshots, alignment/timezone/calendar, transform DAG or ordered steps, feature/label roles, strategy/model parameters, execution assumptions.
- **Outputs:** derived dataset, trades/predictions, metrics/diagnostics, logs, artifact lineage and comparison set.
- **Owners:** QMB dataset/feature pipeline and experiment store; QML authoring; QMF transforms; QMN simulation assumptions.
- **Normal journey:** configure → validate/leakage check → preview sample → save version → run → compare → promote/share reference.
- **Failure journey:** missing/stale source, alignment error, look-ahead leakage, insufficient sample, invalid costs, nondeterminism, incompatible transform/model version, partial artifact.
- **Uncertainties:** QMX’s current strategy/model representation and whether recipes are declarative, code-first or hybrid.

## QMX-OPP-07 — authoring versus app-use copilot scopes

- **User goal:** use AI to build or edit an app safely, while keeping the runtime assistant limited to the app’s granted capabilities.
- **Evidence:** Taskade’s documented Genesis/EVE authoring and agent use; OpenBB MCP-tool bindings; assignment context explicitly distinguishes authoring and app-use sessions.
- **Proposed capability:** two scope profiles, explicit tool declarations and side-effect classes, diff/preview/test before persistent authoring changes, runtime capability tokens, action-time approval and audit.
- **Inputs:** session role, workspace/app scope, tool registry, user instruction, current definition/state.
- **Outputs:** proposed diff or capability-scoped query/action; approval request where required; audit event and result.
- **Owners:** QMA agent/session/tool policy; QML authoring and diff/validation; QMF capability registry; QMN trade/action approvals; auth/secrets/audit.
- **Normal journey:** author asks for change → assistant proposes typed diff → validate/preview → explicit save/publish; app user asks question → assistant uses only app-scoped read tools.
- **Failure journey:** attempted privilege escalation, unavailable connector, sensitive input, external mutation, paid compute or trade without approval, invalid diff, stale base version; deny safely and explain.
- **Uncertainties:** present session model, authorization framework and confirmation/audit semantics.

## QMX-OPP-08 — workspace asset graph and template reuse

- **User goal:** assemble apps from reusable datasets, files, projects, agents and flows, then clone a safe template into a new workspace without losing provenance.
- **Evidence:** Taskade Workspace DNA, app-kit composition, project/custom-field/media/template/MCP tools.
- **Proposed capability:** typed asset graph with owner/scope/permissions, live-reference versus snapshot edges, versioned templates, clone provenance, parameter substitution, migration and rollback.
- **Inputs:** template version, target workspace, parameter/credential bindings and requested assets.
- **Outputs:** new asset identities, resolved graph, migration log, provenance link and warnings.
- **Owners:** workspace/project store; file/media service; QMF packages; QMA knowledge/assets; QML app definitions; migration/versioning.
- **Normal journey:** preview kit contents/scopes → choose target → validate dependencies → clone atomically → configure bindings → test privately.
- **Failure journey:** missing dependency/permission, name/schema conflict, partial clone, incompatible version, deleted source, live reference not allowed; rollback or clear recovery plan.
- **Uncertainties:** whether QMX has a workspace abstraction and which assets are already first class.

## QMX-OPP-09 — ML experiment workbench

- **User goal:** configure, train, evaluate and compare predictive/risk models with reproducible data and budgets.
- **Evidence:** observed LSE model families, feature groups, test split, run limit, optimisation methods and sizing controls; repository claims from LSE Terminal.
- **Proposed capability:** a QMB app over the common resource/recipe/job/artifact contracts, not a separate bespoke subsystem.
- **Inputs:** dataset snapshot/recipe, feature/label definitions, split/embargo, model family/hyperparameters, seed, compute budget and evaluation policy.
- **Outputs:** metrics with confidence/diagnostics, predictions, model artifact/card, lineage, logs and comparison.
- **Owners:** QMB ML/experiment modules; compute runner; artifact store; QML app authoring; QMF model extensions.
- **Normal journey:** validate → leakage check → estimate/approve budget → train → evaluate → compare → optionally register artifact.
- **Failure journey:** no trained prerequisite, bad split, leakage, class imbalance, divergence/OOM, exhausted quota, poor calibration or unsupported serialization.
- **Uncertainties:** product priority, existing ML executor, target users and safe promotion path. Classification is optional until enabling contracts exist.

## QMX-OPP-10 — macro/intermarket research app pack

- **User goal:** combine calendars, yields, macro series, COT, correlations and equity screening into reusable research views and downstream dataset inputs.
- **Evidence:** observed LSE calendar, correlations, yield preview and screener; official LSE repository/API feed names; heatmap/COT route failures recorded.
- **Proposed capability:** extension-supplied reference apps built on normalized event/series/table resources, shared symbol/date/geography parameters and alignment/provenance metadata.
- **Inputs:** resource providers, country/symbol/universe, date/timezone, filters and comparison window.
- **Outputs:** event tables, aligned series/matrices, screen results and recipe-ready selections.
- **Owners:** QMF data providers; QMB research/dataset layer; app shell/shared parameters; licensing/provenance.
- **Normal journey:** discover resources → set shared scope → inspect events/series/screen → select rows/symbols into a recipe.
- **Failure journey:** route/source unavailable, inconsistent calendars/timezones/units, sparse data, stale release, provider disagreement, licensing restriction.
- **Uncertainties:** data entitlements and whether these should ship as official, community or example extensions.

## Suggested sequencing

1. Audit the repository for current ownership and invariants.
2. Decide the capability manifest, resource envelope, scope/permission model and job/artifact lifecycle first.
3. Prove one vertical reference scenario: provider-backed resource → preview → derived recipe → queued run → artifact → two bound widgets.
4. Add replay/live only after event provenance and recovery semantics are explicit.
5. Treat ML workbench and macro/intermarket apps as consumers of the platform contracts, not reasons to hard-code new core paths.
