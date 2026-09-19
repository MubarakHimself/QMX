# OpenBB official research

Research scope: OpenBB provider/data selection and transformation, widget declarations, app layouts, shared parameters, capability discovery, and public-versus-gated limitations. This is a read-only, docs/source-only study; no OpenBB account, backend, API key, or QMX state was changed.

Access mode: public web documentation and public GitHub source. UTC access window: 2026-09-18T08:30:48Z–2026-09-18T08:34:00Z (individual source times are listed below). Evidence labels are deliberately conservative: `DOCUMENTED_CAPABILITY` is explicit first-party documentation; `REPOSITORY_SOURCE` is inspected code in the official OpenBB-finance organization; `VENDOR_CLAIM` is product/documentation wording that was not independently exercised; `UNVERIFIED` means not observable from public pages in this run.

## Findings

### OBB-01 — Provider selection and coverage

**DOCUMENTED_CAPABILITY.** OpenBB standardizes common query fields such as `provider`, `symbol`, `start_date`, `end_date`, `date`, and `limit`. The `provider` argument selects the source for an endpoint; if no user default exists, the first alphabetically installed provider is selected. `obb.coverage.providers` reports provider coverage. Provider-specific parameters follow shared parameters and unsupported provider-specific parameters produce a warning. Symbols may be strings, lists, or comma-separated strings, but ticker conventions can differ by provider.

Source: [Input Query Params](https://docs.openbb.co/odp/python/basic_usage/query_parameters) (accessed 2026-09-18T08:31:10Z UTC).

**DOCUMENTED_CAPABILITY.** Provider extensions are independent packages and can be installed/removed without disturbing core components; a provider is absent from choices if its module is not installed. Coverage can therefore be environment-dependent, and credentials/subscription status can change usable coverage. OpenBB explicitly says it does not host or serve provider data.

Source: [Providers](https://docs.openbb.co/odp/python/extensions/providers) (accessed 2026-09-18T08:31:18Z UTC); [Data Providers FAQ](https://docs.openbb.co/odp/python/faqs/data_providers) (accessed 2026-09-18T08:31:26Z UTC).

**DOCUMENTED_CAPABILITY.** Defaults may be a single provider or a priority list. A priority list uses the first provider whose required credentials are configured; defaults are ignored when a call supplies the parameter explicitly. Settings are local in `~/.openbb_platform/user_settings.json`.

Source: [User Settings & Environment Variables](https://docs.openbb.co/platform/settings_and_environment_variables) (accessed 2026-09-18T08:31:35Z UTC).

### OBB-02 — Shared parameter and provider interface model

**DOCUMENTED_CAPABILITY.** `QueryParams` is a Pydantic model used by the ProviderInterface to validate, merge, and discriminate parameters shared across provider extensions. It supports aliases, constrained choices, and multiple-item metadata. Standard models make comparable requests use consistent names/types (for example `symbol` rather than `ticker`) and normalize output into JSON-serializable lower-snake-case fields; provider-specific inputs become `extra_params`.

Sources: [Architecture Overview](https://docs.openbb.co/odp/python/developer/architecture_overview) (accessed 2026-09-18T08:31:50Z UTC); [Standardization](https://docs.openbb.co/odp/python/developer/standardization) (accessed 2026-09-18T08:31:58Z UTC).

**REPOSITORY_SOURCE.** The official `OpenBB-finance/OpenBB` `Fetcher` source defines the execution contract: `transform_query(params)` → `extract_data`/`aextract_data(query, credentials)` → `transform_data(query, data)`. `fetch_data` invokes those stages in order; `require_credentials` is overridable; `Fetcher.test()` checks each TET stage and result typing. This is source evidence of the contract, not evidence that every vendor connector behaves identically in production.

Source: [official fetcher.py](https://github.com/OpenBB-finance/OpenBB/blob/develop/openbb_platform/core/openbb_core/provider/abstract/fetcher.py) (accessed 2026-09-18T08:33:05Z UTC).

**DOCUMENTED_CAPABILITY.** Provider models inherit standard `QueryParams` and `Data`; provider transforms adapt source-specific input/output while validation makes the result serializable. `AnnotatedResult` can carry metadata separately from main results, exposed as `output.extra["results_metadata"]`.

Sources: [Provider Extensions](https://docs.openbb.co/odp/python/developer/extension_types/provider) (accessed 2026-09-18T08:32:10Z UTC); [Annotated Results](https://docs.openbb.co/python/developer/how-to/annotated_results/) (accessed 2026-09-18T08:32:18Z UTC).

### OBB-03 — Capability discovery and rebuild boundary

**DOCUMENTED_CAPABILITY.** Installed extensions populate routers and the Python interface. The bare interface exposes `/coverage`, including provider/command/model/schema/reference metadata. After installing or changing extensions, `openbb-build` (or `openbb.build()`) regenerates static assets; without this, the Python interface may remain incomplete.

Source: [Architecture Overview](https://docs.openbb.co/odp/python/developer/architecture_overview) (accessed 2026-09-18T08:32:30Z UTC); [Data Providers FAQ](https://docs.openbb.co/odp/python/faqs/data_providers) (accessed 2026-09-18T08:32:36Z UTC).

**DOCUMENTED_CAPABILITY.** Router commands reference provider metamodels with `@router.command(model="...")`; the Provider maps fetchers to those models. A provider extension by itself does not define a user-facing API route. The official Workspace-app guide documents a separate REST API and Python interface sharing core models.

Sources: [Provider Extensions](https://docs.openbb.co/odp/python/developer/extension_types/provider) (accessed 2026-09-18T08:32:44Z UTC); [official build_workspace_app guide](https://github.com/OpenBB-finance/OpenBB/blob/develop/openbb_platform/extensions/mcp_server/openbb_mcp_server/skills/build_workspace_app/SKILL.md) (accessed 2026-09-18T08:33:20Z UTC).

### OBB-04 — Widget declarations and app layouts

**DOCUMENTED_CAPABILITY.** A custom Workspace backend returns data plus a `widgets.json` declaration. A widget declaration can define name, description, category, endpoint, type, source, grid sizing, data mapping, parameters, refresh interval, raw-data view, run button, exportability, and MCP-tool matching. Parameter types include date, text, ticker, number, boolean, endpoint, form, and tabs. Options can be static or loaded from an `optionsEndpoint`; `optionsParams` can pass another parameter value (for example `$type`).

Sources: [Data Integration](https://docs.openbb.co/workspace/developers/data-integration) (accessed 2026-09-18T08:32:56Z UTC); [widgets.json reference](https://docs.openbb.co/workspace/developers/json-specs/widgets-json-reference) (accessed 2026-09-18T08:33:12Z UTC).

**DOCUMENTED_CAPABILITY.** `apps.json` is optional and defines an App, tabs, layout grid entries, initial widget state/parameters, groups, imagery, description, and whether customization is allowed. The public example shows a layout entry binding widget id `hello_world` to initial `name` state.

Source: [Data Integration, app layout section](https://docs.openbb.co/workspace/developers/data-integration) (accessed 2026-09-18T08:33:00Z UTC).

**DOCUMENTED_CAPABILITY.** Shared parameters connect widgets in a group. Table/cell interactions can update another widget's shared parameter; `valueField` allows a displayed value to map to another row field, and `forceUpdate` controls whether the source widget refetches itself. Parameter arrays can be nested to place controls on multiple rows.

Sources: [widgets.json reference](https://docs.openbb.co/workspace/developers/json-specs/widgets-json-reference) (accessed 2026-09-18T08:33:12Z UTC); [Parameter Positioning](https://docs.openbb.co/workspace/developers/widget-parameters/parameter-positioning) (accessed 2026-09-18T08:33:28Z UTC).

**REPOSITORY_SOURCE.** The official [backends-for-openbb](https://github.com/OpenBB-finance/backends-for-openbb) repository states that a Workspace backend returns JSON plus `widgets.json`; it includes examples for widget types and an iframe/HTML parameter bridge. It documents optional query-parameter/header authentication for a connected backend. This is repository documentation and example code, not an independently verified hosted Workspace run.

### OBB-05 — Widget data/raw view and MCP discovery

**DOCUMENTED_CAPABILITY.** For supported widget types, `raw: true` adds a raw-data control and re-requests the endpoint with `raw=true`; the endpoint should then return underlying JSON. A widget can declare `mcp_tool` with exact MCP server name and tool id; the docs say Workspace can match an invoked MCP tool to a widget and provide a citation. An iframe widget can auto-connect an MCP URL when mounted, making tools available to Copilot immediately.

Source: [widgets.json reference](https://docs.openbb.co/workspace/developers/json-specs/widgets-json-reference) (accessed 2026-09-18T08:33:12Z UTC).

**DOCUMENTED_CAPABILITY.** HTML widgets execute returned JavaScript in an embedded context and can dispatch a CustomEvent through the injected bridge to push a parameter back to Workspace. The docs warn to render only trusted markup/scripts.

Source: [HTML widget](https://docs.openbb.co/workspace/developers/widget-types/html) (accessed 2026-09-18T08:33:42Z UTC).

### OBB-06 — Gated/public boundary

**DOCUMENTED_CAPABILITY.** Public docs and public repositories describe OpenBB Platform, Workspace data-integration contracts, widget JSON, and local/custom backends. The docs identify OpenBB Workspace/Terminal Pro as the product surface for connected apps and widgets, but the public pages do not expose a complete signed-in Workspace catalog, plan entitlements, or provider subscription results.

**UNVERIFIED.** I did not sign in, connect a backend, add an app, run a provider query, inspect a live widget, or verify that a particular provider/API key/Workspace feature is available under any plan. No claim is made here about actual account gating, latency, data quality, live-stream delivery, or successful computation.

## QMX-relevant adaptation proposals (not OpenBB facts)

These are explicitly `QMX_ADAPTATION_PROPOSAL`, derived from the evidence above and requiring independent QMX repository audit:

1. Treat a data connector as a replaceable provider package with declared credentials, coverage, shared query schema, provider-specific extras, and normalized output. Preserve source/provider identity and warnings in result metadata.
2. Model each composable app/widget as a declaration: endpoint/job operation, input parameters, typed output/view, grid/layout hints, refresh policy, export/raw policy, and optional capability/tool binding. Keep layout state separate from operation implementation.
3. Add a capability index generated from installed QMX extensions, exposing provider coverage, command schemas, parameter choices, and owners. Make rebuild/versioning explicit when extensions change.
4. Support shared parameter bindings between widgets, including displayed-field versus identity-field mapping and explicit source-refetch policy. Treat bindings as dataflow edges, not visual styling.
5. Preserve a clear permission boundary: public docs/examples can describe capabilities, while account/provider credentials and paid/entitled operations require explicit user authorization and should surface unavailable/credential-required states.

## Still unknown / follow-up boundary

Live Workspace behavior, actual app discovery UI, provider-choice dropdown behavior in a connected backend, error/loading states, plan gating, real stream semantics, and export/download behavior remain `UNVERIFIED` from this public-only run. These should be tested only with an explicitly authorized account/backend and without entering keys or submitting paid jobs.

