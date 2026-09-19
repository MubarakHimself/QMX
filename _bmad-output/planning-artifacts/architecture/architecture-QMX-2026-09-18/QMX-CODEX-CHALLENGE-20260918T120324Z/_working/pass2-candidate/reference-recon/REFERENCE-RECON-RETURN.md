# Reference reconnaissance return

Research package: `QMX-REFERENCE-RECON-20260918T082954Z`

Research window: 2026-09-18, approximately 08:30–08:40 UTC.

## Outcome

The supplied London Strategic Edge (LSE) tab was controllable through the installed browser tooling. The account was already signed in, but the study stayed read-only: no API key was generated, no export was downloaded, no backtest/model/optimisation was run, no trade was placed, and no setting was changed. OpenBB and Taskade were studied through public product surfaces, official documentation, and official-associated repositories. No OpenBB backend was connected and no Taskade app, agent, workflow, account, or publication was created.

The strongest transferable requirement is not a donor UI. It is a set of explicit capability contracts for QMX: discoverable data resources and providers; preview versus asynchronous export; replay versus live stream phases; declarative app/widget composition and shared parameters; reproducible experiment/run objects; workspace-scoped assets; and permission/audit boundaries for agents and external actions.

## Highest-value observations

1. **LSE data work is a progressive journey.** Catalogue rows expose coverage and metadata, expand into an inline preview, and lead to a dataset builder that combines a symbol/window/resolution with indicators, engineered features, optional cross-asset columns, time filters, and output selection. The builder was configured but not executed.
2. **Historical, export, and live access are distinct contracts.** LSE documents row-capped REST queries, queued bulk-export jobs with status and expiring artifacts, and a WebSocket replay phase that hands over to live ticks with an explicit replay marker.
3. **LSE backtesting is an interactive playback/trade simulator on the observed route.** The visible journey used instrument/timeframe/timezone/date/capital/spread setup, then manual order controls, playback speeds, layouts, indicator overlays, annotations, and empty-result metrics. No code editor was observed on that route and no run was started.
4. **LSE ML Studio exposes breadth, but execution remains unverified.** Model families, feature groups, train/test configuration, optimisation methods, risk/position sizing controls, a daily-run counter, and empty-output states were visible. No training or optimisation was launched.
5. **OpenBB separates provider normalization from presentation declarations.** Official docs describe provider-specific fetchers normalized to shared models, coverage discovery, `widgets.json` capability declarations, optional `apps.json` layouts, parameter positioning, and cross-widget shared-parameter bindings.
6. **Taskade treats apps as compositions over workspace assets.** Public gallery cards expose project/agent/automation composition and template cloning. Official docs describe projects/databases as memory, agents as intelligence, and automations as execution; a Genesis app runs on that workspace scope. Live generation, refinement, runs, and publishing were not exercised.

## Important negative evidence and uncertainty

- The LSE heatmap route linked from the site returned a 404, and the tested COT route also returned a 404. This is a failed navigation record, not proof the capabilities do not exist; official repository/API documentation still names COT data.
- LSE pages made differing scale statements (for example, homepage dataset counts versus databank instrument/series counts). They may measure different things. This report preserves each statement as page evidence and does not reconcile them.
- A screenshot proves a visible UI state only. It does not prove data accuracy, entitlement under another plan, successful computation, production reliability, or backend architecture.
- No signed-in OpenBB Workspace or Taskade workspace was used. Provider queries, connected widgets, Taskade run logs, failure/retry semantics, plan gates, and connector behavior remain `UNVERIFIED`.
- Vendor copy and repository README claims are labeled separately from observed interaction.

## Safety and privacy handling

All LSE screenshots were cropped to remove the signed-in header/avatar area. No email address, API key, token, credential, broker connection, personal dataset, or account-setting screen is included. The QMX repository was not modified.

## File index

- `REFERENCE-RECON-RETURN.md` — this operator summary.
- `REFERENCE-JOURNEYS.md` — journey-by-journey evidence, states, limitations, and screenshot mapping.
- `CAPABILITY-AND-BACKEND-IMPLICATIONS.md` — capability relationships and backend contract implications without architecture inference.
- `QMX-ADAPTATION-OPPORTUNITIES.md` — ranked QMX opportunities with user goal, evidence, I/O, owners to investigate, normal/failure journeys, and uncertainty.
- `EVIDENCE-MANIFEST.json` — machine-readable sources, evidence classifications, artifacts, timestamps, and hashes.
- `screenshots/` — privacy-clean UI evidence.
- `LSE-OFFICIAL-RESEARCH.md`, `OPENBB-OFFICIAL-RESEARCH.md`, `TASKADE-OFFICIAL-RESEARCH.md` — supporting official-source research notes from the parallel workers.

## Evidence vocabulary

- `OBSERVED_INTERACTION`: directly visible in the controlled browser during this run.
- `DOCUMENTED_CAPABILITY`: described by official product documentation.
- `VENDOR_CLAIM`: promotional or outcome claim not independently exercised.
- `REPOSITORY_SOURCE`: interface/source evidence from an official-associated public repository.
- `QMX_ADAPTATION_PROPOSAL`: proposed QMX requirement or scenario, not a donor fact.
- `UNVERIFIED`: not exercised or not established by the accessible evidence.
