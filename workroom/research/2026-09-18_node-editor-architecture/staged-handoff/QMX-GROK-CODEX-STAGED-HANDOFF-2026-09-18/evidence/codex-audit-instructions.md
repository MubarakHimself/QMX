# QMX — Framework, Extensibility and Copilot Reconciliation Audit

**Assignment:** evidence-led brownfield diagnosis for a local Codex session.
**Status:** investigation instructions, not accepted architecture or implementation authorization.
**Prepared:** 2026-09-17.
**Downstream technical lead:** Grok using the installed BMAD architecture workflow, after this audit is reviewed.

## 1. Mission and stop boundary

Before anyone finalizes the QMX Workflows expansion, establish what the current platform actually supports, where the implementation or documentation constrains the operator's intended extensibility, and which changes are wiring, extensions, refactoring, or genuinely new design.

The central question is:

> Can QMF serve as a construction kit for different complete systems that can be authored, experimented with, packaged, operated, and deployed through QMX—not only for variants of the present Bot/Book/BMS/MIS arrangement?

This is not an instruction to replace everything. Equally, existing application-specific constraints are not proof that the operator must abandon the desired platform. Investigate which constraints preserve necessary invariants and which make a particular implementation unnecessarily mandatory.

Use the installed architecture, repository-analysis, testing, and review skills that fit. Discover the actual installed skills and read their instructions; do not invent skill commands or assume a cloud/browser capability exists. Use BMAD architecture methods for investigation and alternatives, but stop before ratifying a new spine or applying its changes. CIS may help derive scenarios and expose blind spots; it must not turn every idea into committed scope.

**Read-only applies to the existing project and operational systems.** You may write reports, scratch scripts, and diagnostic results into a fresh, clearly identified audit directory outside the existing repository, and run safe tests against disposable fixtures. Do not edit source, canonical documentation, manifests, lockfiles, settings, or production data. Do not run Documentation Factory, generate implementation epics as accepted work, start coding features, push commits, create PRs, or modify the earlier handoff package.

Never trade, change a broker account, provision chargeable infrastructure, launch paid training, install unreviewed packages into the operator's working environment, or expose credentials. Inspect test fixtures and startup code before running them. A prompt asking for thoroughness is not authorization for uncontrolled side effects.

Finish with a reconciled report that the operator can return to the ongoing discussion. Do not automatically begin Grok's architecture or implementation phase.

## 2. Inputs and authority

Read the attached exported discussion transcript completely, in manageable contiguous sections where necessary. Build a turn-indexed intent ledger before drawing conclusions. The conversation is dictated and contains corrections, phonetic mistakes, abandoned ideas, and evolving terminology.

Also inspect, when supplied:
- `02-workflows-architecture-prompt.md`, the original architecture seed;
- the earlier QMX handoff, only as a non-authoritative draft;
- the QMX terminal inspiration image;
- the Taskade screenshot showing its assistant, workspace navigation, Flows, runs, connections, and app preview.

Images are interaction references, not proof of working QMX functionality, target statistics, or another product's hidden architecture. The Taskade image does not by itself establish that an entire app is generated from a workflow graph.

**Authority distinctions:**
1. The latest clear operator statements determine desired outcomes and corrections.
2. Earlier operator statements supply context where not subsequently changed.
3. Current ratified documents describe the presently approved architecture; they are not automatically the final architecture for the new requirement.
4. Source and reproducible diagnostics establish implementation behaviour at a recorded revision.
5. Assistant suggestions, old reconnaissance, proposed packages, screenshots, and external products are research inputs, not operator decisions.

Keep current behaviour, current documented authority, desired behaviour, and your recommendations separate. Do not silently reconcile conflicts by rewriting either side. Identify proposed amendments and their consequences. Do not globally change statuses from proposed to ratified because the operator recalls accepting an increment; trace acceptance evidence.

If the exported transcript is unavailable or incomplete, inventory what is present and proceed with independent repository discovery. Mark the missing coverage and request the transcript once if genuinely necessary. Do not invent its contents. Do not ask the operator to design technical interfaces that you can investigate yourself.

## 3. Operator intent to preserve

These are orientation notes, not a substitute for the full transcript.

### The framework and construction model

- QMF is the one framework. QML, QMB, QMA, QMN, and any justified additional libraries belong to the same ecosystem. “Under QMF” does not automatically require relocating all packages into a `qmf.*` namespace or placing application behaviour into `qmf-core`.
- QMX should expose useful defaults and allow users to introduce, test, compose, version, package, and share additional capabilities without repeatedly editing core source.
- Extensibility is not limited to indicators, bot parameters, agent plugins, or Python snippets. Investigate its coverage across data, authoring, experiments, models, runtime policy, providers, compute, workflows, and presentation contributions.
- The operator regards the current Book/BMS/MIS/SQS arrangement as a possible default composition, not necessarily a permanent universal architecture. Do not claim that this is already implemented.
- Local experimentation, trained models, sentiment analysis, industry intelligence, data engineering, portfolio/risk/sizing work, and general ML are legitimate outcomes. They need not become trading bots.
- A hypothetical trading-system package can combine strategy logic, sizing/risk policy, optional intelligence, data requirements, testing procedures, and deployment configuration. The current Book/BMS implementation and an alternative without that organizational model should both be examined as architectural journeys.
- A separately versioned custom implementation may conform to a framework-owned interface without entering the framework's source tree. A mini-app may package or use such capabilities without owning their entire implementation.

### Composition and presentation

- Preserve the accepted distinctions: capabilities perform operations; extensions contribute functionality; workflows compose work; mini-apps expose useful combinations through an interface; widgets are individual views or controls. These are not rigid one-to-one nesting rules.
- The exploratory surface is the **Experimentation Board**, within the QMX Workflows direction. Do not reintroduce “research board” as a settled product name.
- Defaults, templates, manual editing, assistant-authored compositions, code/notebook operations, CLI-backed operations, one-off calls, and headless execution must be considered.
- Node granularity is intentional but flexible: a substantial script may be one node, show its code, or expose selected stages. Neither “everything is a node” nor “internals can never be nodes” is an accepted requirement.
- Selected headless capabilities should be reusable as steps where useful. They do not need a dedicated top-level page or a permanently visible running canvas.
- Drafts can be incomplete and exploratory. Running a draft does not certify it for reuse or live operation. Tests can disprove a hypothesis while confirming that the experimental method worked correctly.
- The board may build behaviour; app configuration, presentation, contribution metadata, and an optional copilot profile also matter. Determine a coherent authoring path instead of assuming the graph alone is a complete app definition.
- Final visual design is deferred. Backend contracts for context, contributions, commands, events, logs, errors, preview, and reconnect are in scope now.

### Copilot sessions and powers — latest clarification

Treat **QMX / QuantMind Copilot** as one user-facing identity with multiple independent sessions. Do not interpret that as one global transcript, one universal stateful Agent instance, or removal of QMA specialists.

Two interaction profiles must be investigated:

1. **Authoring/experimentation session.** Helps build or revise workflows, scripts, hypotheses, models, extensions, mini-apps, and candidate trading systems. Uses authorized file, code, test, tool, and execution-environment capabilities. It creates candidate revisions rather than silently changing installed/live versions.
2. **App-use session.** Associated with a particular app instance and version. Understands its exposed state, selections, results, documentation, and available operations. Can query, explain, adjust permitted run parameters, run exposed workflows, inspect records, and ask an authorized specialist about a relevant execution. It must not edit the app implementation, redefine its schemas, install code, or grant itself authoring powers.

These may use the same model or different models. Permission and execution profiles—not model intelligence alone—determine their powers. Investigate whether the existing QMA Session type maps cleanly to these product sessions; do not assume the names mean the same thing.

An app may ship a versioned copilot/context capability profile rather than a separate agent framework. Its declaration requests tools and context; the host grants permissions. App documentation or skills do not grant privileges or replace deterministic validation.

**Session context is primary, not whichever tab happens to be active.** A session can receive deliberate structured selections; navigating elsewhere must not retarget pending work or leak account/app context. Internal QMX interaction should use schemas and APIs. Browser/computer use is primarily for external systems lacking a suitable interface.

Cross-session retrieval is allowed through an explicit, scoped mechanism with provenance. It must not become an automatic global memory merge or an authority transfer. Original authoring sessions are useful lineage but must not be required for an installed app to work after export or transfer to another user.

Preserve QMA agents, specialist roles, subagents, workflows, hooks, skills, RLM-related capability, and tool/provider mechanisms unless evidence supports a deliberate amendment. Do not equate skills with loops, loops with graphs, or a mini-app with one agent or department.

**Operator terminology correction:** trading-floor PM means **Portfolio Manager**, not Product Manager. Record the precise semantic and migration impact; do not blindly replace genuine Product Manager references in BMAD/product-development materials. This read-only audit reports required changes; it does not apply them.

### Deployment and account scope

- The purpose of a Trading Node is continuous trading independent of the desktop, not to make a particular portfolio policy immutable forever.
- Consider a compatible deployed system on a VPS, on the workstation while the user is present, or with an agent observing it. Separate placement, supervision, and account mode from policy choice.
- Sequential candidate development, replay testing, paper/demo validation, review, and activation are intended. Do not assume the operator wants unsafe live hot-swapping.
- Consider multiple brokers, multiple accounts per broker, different market-data sources, explicit demo/live scope, and multiple simultaneously installed system versions. A home dashboard can aggregate read views; it must not introduce one implicit global execution account.
- Analysis access and trade permission are different. The user's spot-instrument preference must not force exclusion of unrelated instruments as research data, nor allow their execution by implication.
- CPU/GPU/remote execution depends on actual hardware, provisioned environments, credentials, entitlements, declared limits, and network/data availability. Do not invent availability or silently purchase capacity.

## 4. Establish repository reality first

Use the selected local QMX checkout. A previously supplied location was `C:/Users/Mubarak/Desktop/QMX`; verify the actual root rather than assuming it exists. Record current time, root, branch/HEAD, dirty status, linked worktrees, submodules, relevant running local processes if safely inspectable, and which files are authoritative.

Earlier reconnaissance used planning `main@b8b4d21a3d6ec33158254f1827912c8fc0c4dcc3` and code on `integration@270e992995c2378ca63cf6343254ef8140a8c97e`. These are pointers, not a claim about today's state. Documentation also cites older `integration` revisions. Re-resolve every relevant version.

Read applicable repository instructions, `docs/AGENTS.md`, constitution, glossary, component/dependency manifests, relevant spines/ADRs, contracts, `_docwork` decisions and gaps, current stories, and tests. Use the documented ownership/dependency graph to drive source inspection. Check changed files and active branches/worktrees. Do not switch, reset, stash, merge, or clean someone else's working tree.

Use safe read operations such as `git show` and `git ls-tree` where appropriate. If runtime diagnostics need a writable location, use a disposable copy or dedicated temporary fixture outside operational stores. Record any diagnostic side effects, commands, exit status, and environment limitations. Do not mistake missing credentials or a dependency mismatch for a demonstrated implementation defect.

For each investigated capability, report independent evidence dimensions:
- document status and exact ruling;
- source presence and entry point;
- wiring/call path;
- isolated-test evidence;
- composed execution evidence;
- deployment/operational evidence, if any;
- what remains unknown.

A class name, registry constant, matching test, or accepting TCP socket is not automatically an end-to-end feature. Conversely, an in-memory projection is not automatically missing persistence: trace its authoritative journal, replay path, checkpoints, and reconstruction.

## 5. Investigations

Choose bounded parallel investigators where available, with separate outputs and one lead responsible for reconciliation. Share the operator-intent ledger and revision manifest with all investigators. Do not let independent reports invent competing universal registries, schedulers, identities, or terminology. Research can be parallel; accepted conclusions must be reconciled.

### A. Framework boundaries and true extensibility

Map definitions, computation, adapters, registries, application composition, runtime, and presentation across QMF/QML/QMB/QMA/QMN. Inspect the actual public interfaces, extension loaders, closed registries/catalogues, concrete-type checks, hard-coded model or provider lists, permitted dependency edges, and deployment assumptions.

Determine where a new implementation is already registerable, where new core edits are required, and whether those edits are intentional, incidental, or only documentary. Audit more than CT-16. Distinguish configuration variation, structural generation, dependency injection, separately installed packages, user-facing extension installation, and generated UI.

Test the claim that every new portfolio/system version must change all underlying libraries. The audit should locate actual coupling, not repeat that claim. A sound public interface should often let a new implementation reuse unchanged consumers. Equally, do not force a fundamentally different system into a nominally compatible adapter that changes its meaning.

Evaluate alternatives such as extending existing owners, extracting shared contracts, or introducing a justified composition/extension library. Do not mint it during the audit. Keep one framework, acyclic dependencies, and one clear owner per public responsibility. Report whether a uniform package envelope can support different contribution types without pretending all lifecycles are identical.

### B. QMA sessions, context, memory, and app profiles

Trace the current meanings of Session, Agent, Quant, Worker, Mission, Task, Graph Template, Loop, Skill, Routine, handles, tools, and hook policies. Audit their actual storage and lifecycle. Map product conversations separately from executions and UI attachments.

Investigate authoring and app-use profiles: discovery, allowed tools, context providers, run parameters versus source edits, model selection, budgets, local files, external browser/computer use, RLM invocation, subagent scope, and consistent enforcement for manual and agent actions. Check how stale or malicious app content, files, tool results, or documentation could misdirect a privileged authoring session.

Determine what structured app context can include: app instance/version, selected objects, query filters, chart range, dataset release, workflow definition/version, execution and attempt IDs, configuration references, allowed operation names, and authorization/account scope. Decide what must be pinned versus refreshed. An app-provided profile cannot grant itself more authority or alter a host-wide system policy.

Audit current memory provider bindings, retrieval, supersession/deletion, no-provider behaviour, session history retrieval, token budgeting, and evidence provenance. Existing desk-scoped memory and organizational keys may not fit cross-app conversations without amendments. Find the smallest honest change; do not invent a second memory system by default.

Trace app-origin lineage and cross-session change requests. Operation sessions should survive independent of the original creation transcript. A new user installing the app gets appropriate documentation and capability descriptions—not the original author's private chats, credentials, or permissions.

Trace “ask the agent that produced this result” through durable work records. Do not fabricate an agent's past rationale when only outputs remain. Distinguish recorded evidence, a new interpretation, and a resumed investigation.

### C. Compositions, templates, extensions, mini-apps, and steps

Map the existing authored graph, runtime graph, job/attempt records, dataflow and control flow, draft storage, and UI contribution surfaces. Find whether users can actually register new compatible capabilities—not just whether the codebase is modular.

Investigate typed ports, cardinality, item collections, fan-out, Cartesian versus paired mapping, joins, failures, parallel completion, loops, stop/budget policies, subworkflows, explicit triggers, scheduled invocations, and partial execution. Look for code-versus-canvas parity without requiring arbitrary Python to round-trip into a graph.

Define options for an app package to reference behaviour, presentation, defaults, metadata, tests, optional copilot profile, and documentation. Distinguish an app definition, installed instance, independent run, and deployment. Do not create a single mutable record that means all four.

Trace how a tested draft becomes reusable, how a reusable subflow becomes a node where appropriate, and how a mini-app is packaged without copying or flattening every dependency. No public marketplace is required. Compatibility, install/uninstall, dependency conflicts, rollback/migrations, and exported interfaces still need evidence.

### D. Authoring and experiments across QML and QMB

Audit QML Stage 0 hypotheses/dictionary roles, governed authoring, Python logic, conformance, registration, graduation and evidence boundaries. Identify stale proposed/accepted status rather than silently changing it.

Audit QMB direct/Python/CLI/coordinated entry points; what-if studies, analysis projections versus reruns, sweeps, structural generation versus parameter search, robustness, calibration, and policy adapters. Do not claim a genetic algorithm is present because an optimization loop exists; inspect its actual sampler and generation logic.

Trace whether QMB can evaluate alternative risk/sizing/accounting systems without fake Book/BMS wrappers. Distinguish existing defaults from assumptions embedded in signatures, core run loops, serialized records, result labels, tests, and admission/approval logic.

The audit must cover the complete loop: candidate authoring, data selection, testing, iteration, model training if relevant, paper/demo readiness, packaging, deployment, and later inspection. Do not require every ML or data experiment to be a trading backtest or a QML bot.

### E. QMN: hosting, policy composition, transitions, and accounting

Start from the actual current QMN implementation and documents, not the label “server.” They currently describe more than a machine location. Identify which responsibilities belong to reliable execution hosting and which implement the particular current rulebook.

Investigate two systems: A using existing Book/BMS/SQS/MIS choices; B using another declared allocation/risk/sizing model, potentially no Book/BMS organization and an optional different or absent MIS. Treat B as an architectural probe, not permission to deploy or a demand to code that strategy.

Evaluate plugin/extension versus deployable system package approaches and the effect on QMF risk interfaces, QML bot protocol, QMB replay semantics, registries, telemetry, provider routing, and current UI/read models. Preserve necessary exact accounting, command traceability, access controls, and protective behaviour without assuming every existing named policy is universally required.

Explain identity in plain language: exact code/configuration/model/input versions and references, rather than bot category or display name. Distinguish semantic identity, package version, instance identity, deployment version, and execution ID. Do not hash cosmetic layout changes into trading semantics without a reason.

Trace sequential transition cases separately:
- old version has no open positions or pending orders;
- old version drains while the candidate runs only on a separate demo environment;
- versions operate on distinct accounts;
- versions share an account with explicit exposure and command ownership;
- a process disappears after a submission but before acknowledgement;
- restart/rollback after the new version already changed external state.

Do not impose hot replacement as the default question. Explain current supervised restart rules as current mechanisms to assess, not as permanent product constraints. Software rollback does not reverse executed trades. Agent-authored skills can guide a transition, but runtime checks must enforce the resulting ownership and permissions.

Audit current paper/demo semantics against the user's desire to evaluate whole new system versions. Report exact incompatible rules rather than bypassing them or inventing a new “paper” label with conflicting meanings.

### F. Data, market access, and multiple brokers/accounts

Trace acquisition through retention and consumption: provider adapters, historical files/API/CLI ingestion, polling, streaming, timestamps, revisions, symbol/entity mapping, units/currencies, sampling/resolution, missingness, point-in-time availability, derived datasets, and dataset recipes/builders.

Separate source-provider identity from execution venue/broker, account, credential, strategy/system instance, data permissions, execution permissions, and demo/live environment. Test duplicate symbols across venues and accounts. Never assume one global active account from UI selection.

Audit whether current schemas genuinely cover sector/fundamental/macro/news/sentiment/model data or are specific to quotes/events. Do not force every source into bid/ask fields or label raw source data as a model result. Investigate extending QMF data before adding a duplicate store or another data-policy owner.

Trace provider switching, entitlement failures, query limits, restarts, gaps, subscription sharing, and historical-to-live boundaries. Preserve disagreements and measured freshness. Check how comparisons remain honest when the execution feed and research feed differ.

Home-dashboard aggregation is an authorized read model with source, account, currency, freshness, and mode metadata—not a new global trading controller. Ordinary operation sessions must not accidentally target another account by changing a visible filter.

### G. Execution environments, GPU jobs, CLI-backed nodes, and operations

Trace model-provider routing separately from data providers, broker adapters, and compute providers. Inspect current QMA/QMB scheduling and ownership before recommending another scheduler.

Audit local CPU/GPU detection, remote-environment declarations, credentials/entitlements, dependency images, CUDA/runtime requirements where relevant, upload/export policies, resource/cost limits, streaming logs, cancellation, checkpoints, output registration, and unsupported-capability behaviour. “GPU requested” is not “GPU available.” A subscription is not proof of API or automation rights.

Distinguish training, serving inference, and live trading. A trained model can be an output artifact deployed elsewhere. An unattended system cannot depend on an unavailable local coordinator. A CLI-backed step should produce structured outputs plus readable logs; terminal-style presentation is optional and is not its authority boundary.

Use registered commands and allowlisted execution targets where applicable. Audit timeout, lost-acknowledgement, child-process cleanup, duplicate submissions, and recovery. Do not silently reuse a trading-host credential to provision a research environment.

### H. Persistence, provenance, and platform operation

Separate app/extension packages, mutable drafts, published definitions, sessions, work records, model files, datasets, time-series stores, memory, audit journals, and rebuildable projections. Map one writer and a recovery path for each authoritative record.

Trace backup and restore across linked artifacts, not only individual databases. Inspect migrations, schema/version compatibility, disk pressure, partial writes, corrupted artifacts, orphan jobs, startup reconstruction, and evidence ordering. Do not infer end-to-end recovery from an in-memory store, nor from a database's existence.

Define the evidence needed for a readiness dashboard: which tests ran, their scope and versions, unknown/unmeasured status, latency and capacity measurements, paper/demo observations, compatibility checks, operator decisions, and deployment state. This is a read model to specify, not a final UI design or a promise of profitability.

### I. Backend-to-UI contracts and reusable app context

Specify what the backend must expose for the eventual desktop host: capability discovery, config schemas, node descriptors, views/widgets, app metadata, app-use profiles, commands/queries/events, context updates, run/attempt logs, reconnect, preview, and installation lifecycle.

Study JSON Render and MCP Apps from current official sources. JSON Render's component/action catalogue and MCP Apps' interactive host protocol are references/candidates, not replacements for execution, persistence, authorization, or context ownership. Ordinary native QMX views need not all become MCP Apps.

The latest Taskade screenshot is a reference for one workspace containing assistant interaction, agents, flows, connections and app preview. Do not infer unobserved implementation details. Analyse how a graph-based authoring view and an app view can be projections of related assets without becoming the same data structure.

Investigate whether an app can call an exported operation from another app/extension without driving its visual controls. A contributed UI action must enter the same supported domain boundary as another authorized caller. A malicious view, stale action or app profile must not impersonate the operator.

## 6. Required end-to-end scenario probes

Use these to trace actual paths and derive a risk-based test matrix. Extend with meaningful adjacent cases; do not attempt an unbounded Cartesian enumeration.

1. **App-use to authoring:** inspect a macro/sector result, query its run records or originating specialist, produce a scoped change-request artifact, open a separate authoring session, and develop/test v2 without editing v1's implementation from the app-use session.
2. **Concurrent session isolation:** a workflow-building session, a strategy-authoring session and an ML session coexist. Navigate elsewhere, reconnect, and deliberately retrieve an earlier result. Targets, rights and histories must not be silently mixed.
3. **Default versus alternative policy:** evaluate one scalping system using Book/BMS and another candidate using a different sizing/risk composition. Find exactly where QML/QMB/QMF/QMN support or prevent this.
4. **Two MIS versions:** existing output serves production; another version runs in shadow. Also examine explicit distinct active consumers. Compare outputs without two writers claiming the same authority.
5. **Multiple brokers/accounts:** same instrument label across two brokers and several accounts; separate source data from execution routing; aggregate authorized dashboard reads without cross-account commands.
6. **Multi-source study:** sector membership, prices and macro/sentiment data have different timestamps and revisions. Build a point-in-time dataset; change a provider without silently changing the old study.
7. **Compute placement:** a notebook/model operation requests a GPU. Exercise provisioned local, provisioned remote, missing entitlement and no-compatible-environment paths. Trace logs, cancellation and returned artifacts.
8. **Distribution:** another user installs a package in their own installation, configures their own credentials, opens the mini-app and invokes its workflow without access to the author's private conversations or core modifications.
9. **Headless reuse:** one capability is invoked directly, through a supported CLI/tool door and as a selected node. Compare inputs, outputs, errors, permissions and evidence without mandating a full terminal or UI page.
10. **Sequential rollout:** a new system is developed and evaluated, then replaces a flat stopped predecessor. Separately trace the non-flat/unknown-command case. Do not turn the complex case into a requirement for live hot-swapping.
11. **Skill lifecycle:** an authoring agent drafts a specialist skill, validates/evaluates it including when it should not activate, records its version, and requests supported registration. Skill text cannot grant new permissions.
12. **Exported dependency:** app B consumes an output from app A. App A upgrades or is removed; B must remain pinned, explicitly migrate or report incompatibility—not silently change meaning.

For each: state the user's goal, prerequisites, asset/account scope, relevant interfaces, records written, execution location, authoritative outcomes, permissions, interruption behaviour, observed support level, and exact missing seam.

Include cross-cutting failures: stale state, concurrent edits, revoked access, unknown external outcome, duplicate events, corrupted checkpoint, provider revision, unsupported schema version, missing secret, exhausted quota, inactive app, expired session, cross-scope memory retrieval, untrusted document/tool output, changed model weights, and failed partial install. Prioritize by consequence and likelihood; document residual uncertainty instead of claiming all imaginable cases are covered.

## 7. External references: bounded verification, not product cloning

Use primary documentation and public source where it resolves an audit question. Record retrieval date, version, licence where relevant, observed behaviour versus inference, the QMX concern, and adaptation versus dependency adoption. Existing QMX donor studies must be read before repeating them.

Relevant references supplied by the operator:
- n8n: https://github.com/n8n-io/n8n and https://docs.n8n.io/
- Taskade: https://www.taskade.com/ and https://help.taskade.com/
- OpenBB: https://docs.openbb.co/ and its linked official source repositories
- QuantConnect: https://www.quantconnect.com/docs/v2/
- StrategyQuant: https://strategyquant.com/doc/
- JSON Render: https://json-render.dev/docs/catalog
- MCP Apps: https://modelcontextprotocol.io/extensions/apps/overview
- DeepSeek Harness/Cordis: https://deepseek-harness.github.io/deepseek-harness/reference/cordis-primer
- Caliper: https://github.com/edonadei/caliper
- VS Code extension model: https://code.visualstudio.com/api
- Zed extension model: https://zed.dev/docs/extensions/developing-extensions
- London Strategic Edge: https://londonstrategicedge.com/
- BMAD/CIS: use the actual installed skills and their current official references.

These are mental-model inputs, not a requirement to embed their runtimes, adopt restrictive dependencies, or reproduce all their features. A broad LSE browser reconnaissance can be a separate report; it is not a prerequisite to investigating QMX's own architecture. Do not spend the audit rediscovering every external product or scraping entire catalogues.

Model examples, alternative data sources and unusual portfolio experiments in the transcript are capability probes unless the user explicitly commits them. Do not make every reference an installation or a new subsystem.

## 8. Audit outputs

Create a fresh report directory, for example a timestamped sibling `QMX-RECON-YYYYMMDD-HHMMSS/`, and report its exact path. Keep the repository and earlier handoff unchanged. Prefer useful depth and source traceability over document count.

Produce:

1. **`RECON-RETURN.md`** — the primary readout. Start with a short operator summary, then answer the central framework question, the two-session copilot question, and the main coupling findings. End with recommended scope/options for the later Grok architecture session and what must be resolved first.
2. **`INTENT-AND-AUTHORITY-LEDGER.md`** — latest accepted outcomes, explicit corrections, unresolved choices, superseded suggestions, and opportunity seeds with transcript locations. Include the PM/Portfolio Manager correction without applying it.
3. **`CAPABILITY-AND-COUPLING-MATRIX.md`** — domain capability, documented owner, source entry point, public extension mechanism, hard-coded dependencies, test/wiring evidence, and change classification.
4. **`SCENARIO-TRACES-AND-RISKS.md`** — representative journeys, state transitions, failure coverage, and impact across QMF/QML/QMB/QMA/QMN/data/storage/UI contracts. Give trace IDs future requirements and UI journeys can reuse.
5. **`EVIDENCE-MANIFEST.md`** — revisions, paths/line ranges, relevant functions/tests, exact safe commands and outcomes, external references, untested claims, and limitations. Small reproducers/output files may sit in an accompanying diagnostics directory.

These files must distinguish:
- already demonstrated in a composed run;
- implemented and unit-tested, integration not demonstrated;
- present but needing wiring;
- documented but not found in the inspected code;
- conflicting documents or branch mismatch;
- supported by an existing extension interface;
- needing a compatibility-preserving refactor or new interface;
- requiring an explicit architecture amendment;
- not investigated / blocked, with reason.

Classify proposed changes as reuse, wiring, extension, refactor, breaking-contract change, data migration, new package, or missing evidence. For every important claim, attach a source or a diagnostic. Do not turn a partial search into a global absence claim.

Answer specifically:
- What is genuinely hard-coded versus just a default?
- Which defaults can already be replaced without editing core code?
- Can alternative systems be compared in QMB and later hosted in QMN using consistent semantics?
- Can current session/context/memory models support authoring and app-use profiles without state or authority leakage?
- Which responsibilities fit existing owners, and is any new library justified?
- Which contracts are needed now for later UI work, without selecting final layouts?
- What is the smallest representative proof that would falsify a weak architecture?
- What should Grok independently verify, and what should it avoid redoing?

## 9. Reconciliation and completion

Have a reviewer challenge the principal findings, preferably with independent source tracing rather than a summary-only review. Look specifically for assumption-driven rewrites, false claims of readiness, forcing all work through agent Missions, stripping necessary execution safeguards, mistaking safety boundaries for immutable Book/BMS business policy, and treating a mini-app as only a chart.

Consolidate contradictory reports into explicit resolved findings or unresolved questions. Do not settle factual disagreements by majority vote between agents. Prefer a direct trace or diagnostic. Do not report complete coverage if you ran out of time or context; leave a precise continuation index.

The desired result is a strong diagnostic foundation for Grok, not a preselected redesign. Recommend the next architecture scope and likely change sequence; do not perform it. Summarize the largest decisions in plain language so the operator does not need to understand internal identifiers to review the result.

**Finish and stop after the audit package is produced. Return the exact paths and a short readout. No architecture ratification, Documentation Factory run, production implementation, infrastructure provisioning, or live operation follows automatically.**
