# Codex assignment: observe reference products for QMX — LSE first

Perform a read-only, evidence-backed product-reconnaissance study. The main target is https://londonstrategicedge.com/ (London Strategic Edge, not London Stock Exchange). Then study selected relevant OpenBB and Taskade journeys: https://docs.openbb.co/ and https://www.taskade.com/. The purpose is to uncover interaction and backend capability requirements for QMX; do not clone those products or implement QMX now.

## Environment and boundaries

Discover available browser/Playwright/MCP/computer-use tools and read their installed skills before use. Verify actual browser control by a harmless navigation/read. Do not assume Codex can control an existing signed-in tab. Prefer the user's explicitly attached/authorized tab or public pages. If sign-in is required, identify the limitation or ask the user to complete it without sharing credentials. Never inspect browser cookie stores, tokens, unrelated tabs or password managers.

Do not buy subscriptions, launch paid API/ML/backtest jobs, place trades, send messages, change account settings, connect personal brokers, upload user datasets, perform broad scraping, or download large/proprietary data collections. Do not enter a key just to discover an API. Do not auto-publish or save persistent workflows/apps in the user's account. Harmless navigation, previews, documentation reads and non-submitting configuration inspection are allowed. Where observing a result would require side effects, stop at preview, use supplied demos where permitted, and record the gap. Respect access and licensing boundaries.

No QMX repo mutation. Notes/screenshots belong to a fresh local research folder. Log failed navigation accurately. If browser automation is unavailable, finish a labeled docs/source-only study and list the specific unobserved interactions—never invent click paths or screenshots.

## Context

QMX has one framework, QMF, with QML authoring, QMB experimentation, QMA agents and QMN trading operation. The desired extension/workflow/mini-app system should support data and ML outcomes as well as trading. The user wants to construct new applications without core edits. Authoring and app-use copilot sessions differ in scope. Actual stack/implementation findings come from the QMX repository audit, not from donor UI appearances.

Read the attached latest transcript and QMX scope summary if provided; a lack of those files does not prevent observing the products. Keep transferred personal content out of external product inputs.

## Journey-driven investigation

Start with navigation and a feature/route inventory. Then walk complete accessible journeys, not just home-page screenshots. Prioritize:

1. LSE data discovery, coverage, metadata, preview, historical/live distinction, dataset-builder/recipe concept if it actually exists, file/API/WebSocket access, API docs and data-bank guides.
2. LSE backtesting: inputs, instrument/data selection, code/strategy definition, configuration, chart annotations, run controls, results, comparison and export where visible without submitting new jobs.
3. LSE ML Studio: actual model families, input/feature/label setup, splits, training/evaluation settings, compute/limits, outputs and connection to other tools. Label advertised versus observable features precisely.
4. LSE tools most relevant to composable research: macro calendars/heatmaps, screens, intermarket data, COT/yield information if present. Do not produce investment advice; report software behavior.
5. OpenBB provider/data selection and transformation, widget declarations, app layouts and shared parameters, and how app capabilities are discovered. Use official docs/source where the interface is gated.
6. Taskade distinction between app/workspace, flows, runs, agents, connections, data/project assets, template reuse and assistant-driven editing. Inspect public demonstrations or authorized read-only examples; do not create an account or publish an app.

Follow official links to repositories; verify association before calling a repo official. Do not infer backend architecture from a screen. Source/JS inspection permitted only within tool permissions and legitimate page access; do not bypass gates or hidden endpoints.

## Evidence format

For each observed journey record ID, source URL, UTC access time, access mode, preconditions, actual navigation/actions, visible inputs/outputs, loading/empty/error/permission states, screenshots or page evidence with filenames, and limitations. Capture useful screenshots without sensitive account information; redact before packaging. Distinguish:
- OBSERVED_INTERACTION
- DOCUMENTED_CAPABILITY
- VENDOR_CLAIM
- REPOSITORY_SOURCE
- QMX_ADAPTATION_PROPOSAL
- UNVERIFIED

A screenshot proves visible UI state, not data accuracy, successful computation, availability under another plan, or production readiness. Do not infer missing features from one failed page.

## Deliverables

Write `REFERENCE-RECON-RETURN.md` (operator summary), `REFERENCE-JOURNEYS.md`, `CAPABILITY-AND-BACKEND-IMPLICATIONS.md`, `QMX-ADAPTATION-OPPORTUNITIES.md`, `EVIDENCE-MANIFEST.json`, and a screenshots/ folder if actual screenshots were captured. Equivalent consolidated reports are allowed with a file index.

Each retained opportunity links a real user goal to evidence, proposed QMX capabilities, input/output shape, likely affected existing owners to investigate, normal/failure journeys, uncertainties, and classification: enabling requirement candidate / reference scenario / optional future app. Do not demand adoption of all donor features. List high-value public capability relationships (files, operations, job handles, streams, shared parameter bindings) rather than copying visual styling.

Package safe outputs as `QMX-REFERENCE-RECON-<timestamp>.zip`. End with exact paths and a short account of what was observed versus still unknown. Stop; do not invoke Grok or implement anything. This report feeds Grok's exploration and Codex's later independent challenge.
