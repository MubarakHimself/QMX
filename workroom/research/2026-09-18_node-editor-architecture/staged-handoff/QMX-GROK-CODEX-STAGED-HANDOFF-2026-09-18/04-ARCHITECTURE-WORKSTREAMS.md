# Architecture workstreams and cross-cutting decisions

> Process update: use `10-STAGED-PROCESS-AND-REVIEW-CONTRACT.md` for the Grok → Codex → Grok handoff and the latest delegation rules. Historical evidence is unchanged.

This is a coverage guide, not a mandated component decomposition. Workstreams can run in parallel; the lead must integrate their conclusions. Proposed record names below describe responsibilities, not implemented APIs or automatically authorized registry kinds.

## W1 — Framework boundaries and alternative systems

**Question:** which restrictions are genuine shared invariants, and which encode the current system?

Trace QMF risk/value/data/registry interfaces, QML declarations and authoring, QMB config/risk/result semantics, and QMN assembly. Separate a default algorithm or policy from the interface that permits a different one. Test two materially different complete systems, not only Book parameter variants. Identify where alternate accounting and risk units mean outputs cannot be compared directly.

Deliver an owner/dependency map, existing default-system compatibility path, proposed contract amendments, migration notes and falsification tests. No dummy Book/BMS identities, untyped universal policy blob, replacement of useful exactness/provenance guarantees or unbounded runtime rewrite.

## W2 — Public capability and extension surface

**Question:** can a user add and share functionality without editing core source?

Audit real registration/discovery, not just importability. Inventory data adapters, computation/indicator/structure/risk policies, authoring operations, experiments, model/tool/compute/context/memory bindings, skills/loops/procedures and UI contributions. Distinguish absent, closed-but-extendable, wired, installable and demonstrated.

A contribution descriptor should expose identity/version, responsibility, schemas and units, input/output cardinality, parameters, dependency/permission requirements, side effects, execution/lifecycle modes, configuration, errors and diagnostic metadata. A package can span multiple contributions without becoming their domain owner.

Design install/validate/configure/enable/disable/update/pin/export/import with conflicts, dependency removal, migration, rollback, partial install and old running versions. Manifest permissions are requests, not grants. Public sharing must not require private authoring history or a marketplace.

## W3 — Workflow semantics and reusable composition

**Question:** how do authored procedures become durable work without imposing QMA ontology on everything?

Trace Graph Templates, Task Graphs, Skills, Loops, Routines, scheduling, QMB doors and job handles. Consider one declarative composition model with appropriate specialised semantics, or explicit adapters between existing models. Justify any new scheduler/runtime/store.

Define partial drafts, versioned runnable definitions, executions, attempts, result references and layout. Typed dataflow must distinguish reference/data/event/control inputs and collection mapping. Specify conditional skips, joins, empty collections, errors, nested subflows, loops, budgets, deterministic versus stochastic steps and reproducibility limits. A loop is not a skill just because its body is reusable. A scheduled trigger is not the workflow.

Cover executing a selected subgraph, obtaining its required inputs, reusing prior results when valid, and invalidating derived results after actual semantic changes. Never use a projection as a path-dependent rerun. A graph edit must not silently mutate an in-flight execution.

## W4 — Copilot, harness, session context and memory

**Question:** how do the authoring and app-use profiles share infrastructure without mixing authority or work?

Design product sessions around explicit host-granted context; audit current QMA Session compatibility. Include app/installed-instance/version, selected objects, allowed operations, source/result/run/deployment refs, broker/account/environment and context revision. App-use can inspect and invoke exposed work, not edit implementation. A change-request artifact bridges to authoring.

Audit model routing, tool discovery, specialist/delegation lifecycle, compaction, RLM, memory-provider bindings, context compilation, history retrieval, exports and logs. Distinguish model identity from execution profile. Same model can have different tools; more intelligent does not mean more authorized.

Make private session memory and shareable app documentation separable. Historical retrieval must not retarget actions. Explain how revocation changes ongoing work, how app-supplied context is treated as data, and how agents consult actual records rather than invent the explanation of a prior run.

## W5 — Data and provider construction kit

**Question:** what new data can be brought into QMX and combined reproducibly?

Trace existing raw capture, ingestion, schema normalization, historical queries, source revision, licensing and model/MIS inputs. Identify new fact families without forcing them into quote schemas. Separate schema normalization from meaning equivalence: similarly named provider fields are not automatically interchangeable.

Specify provider capabilities, configurations and quality/freshness; historical retrieval versus polling/streaming; files/API/SDK/CLI/webhook transports; entity mapping; point-in-time memberships and corporate actions; raw/adjusted distinctions; revisions, units, currencies, time zones and source disagreement.

A recipe describes typed inputs, transformations, joins/features, split policy, pinned releases and output provenance. Raw bytes, analytical tables, saved artifact references and application state need appropriate ownership. Support derived data reuse without silently overwriting old evidence. Investigate publication lag and training/test information boundaries.

Streams require subscription ownership, buffering, backpressure, dedupe, late-event policies, catch-up and consumer lifetimes. Source failure must be observable; switching sources must be explicit where it affects run meaning or trading.

## W6 — QMN deployment, accounts and system transitions

**Question:** what makes a tested system independently deployable and observable?

Split reusable host responsibilities from default trading policy without assuming every protection belongs on one side. Trace account/venue/credential scope, command identity, reconciliation, unknown outcomes, lifecycle supervision, shutdown and external order ownership.

Versioned systems may share code but must not unknowingly share mutable state or command authority. Explore distinct accounts first, then shared-account aggregation/attribution only with explicit semantics. Model flat/stopped replacement, demo/shadow comparison, partial rollback, unknown commands, old process recovery and residual positions. Software rollback does not reverse fills.

QMN remains the inspected runtime, not a claim that every workload requires VPS-only placement. Readiness views should expose actual checks, model/data compatibility, latency measurements, deployment revision and unresolved state—not merely a global green light.

## W7 — Compute, external access, models and settings

**Question:** can a requested job actually run in the intended environment?

Compare required capacity, configured providers, available resources, entitlement, credentials, isolation, dependencies and current health. Cover CPU/GPU, image/driver/CUDA compatibility where relevant, time/memory limits, network policy, artifact upload/download, checkpointing, preemption, quota and cost visibility. Training placement and deployed inference are different choices.

Define available/configured/authorized/reachable/healthy as separate states. A local/server toggle is presentation of a real placement decision. Preserve explicit job identity, cancellation, unknown outcome and restart semantics. A remote child does not make a sleeping laptop coordinator durable.

Settings should support connection tests that do not mutate accounts; secrets by reference; scoped defaults; provider-specific schema options; capability discovery; revocation; and explicit effective configuration. Supported model subscription integration must be verified, not implemented by extracting private tokens.

## W8 — Persistence and evidence

**Question:** can the exact work be reconstructed after interruption and upgrades?

Inventory existing authoritative writers and stores: data evidence, registry, research blobs, QMB ledger, QMA journal/ledgers, workflow state, app/session definitions, telemetry and checkpoints. Document what is projected/rebuildable, what is independently durable and how cross-store announcements/commits maintain consistency.

Specify draft saves and concurrent edits; immutable released definitions and run snapshots; reference integrity; bulk artifacts; content/version distinction; transactional boundaries; partial write/recovery; orphan detection; retention; private export; backup/restore validation; and bounded analytics/telemetry growth. Log messages are not interchangeable with accepted evidence.

Do not invent a database merely because a table is shown on a canvas. Do not reject legitimate new persistence needs just to preserve an old closed store list; propose owner/migration changes explicitly where required.

## W9 — Desktop contribution and copilot interaction protocol

**Question:** what must the backend provide so the UI can be designed coherently later?

Define discoverable widgets/editors/views, navigation contributions, parameter forms, commands, state queries, progress/events, errors, app-use context and reconnect. Rich widgets may include notebooks, charts, tables, model evaluation and execution inspectors. Not all extensions need independent navigation.

Study JSON Render for component/action catalogues and MCP Apps for supported tool-linked interactive views. Keep native QMX navigation and external/interoperable views as explicit options. Do not presume either technology implements domain permission checks, persistence or workflow execution.

Exported operation/data contracts enable app-to-app reuse; presentation is not the integration boundary. UI mounting/disposal must not implicitly start/kill durable backend work. Preserve app version and session targeting through preview/published views.

## W10 — Evaluation, defaults and opportunity governance

**Question:** how can the user trust reusable contributions without freezing experimentation?

Ship enough defaults to do real work, then a clear custom-development path. Separate structural/schema validation, behavioral correctness, role/activation tests, domain fitness and operational readiness. A scientifically negative experiment can be a technically correct reusable method. A model output is not a self-issued verification certificate.

Use Caliper's evaluation patterns as a reference to assess skill activation, ablation, regressions and author/verifier independence, subject to QMA compatibility. Preserve evidence and version labels for skills, models and procedures.

Use CIS to maintain opportunity → journey → capability/contract → acceptance traceability. The opportunity map is not the implementation backlog. Avoid making every innovative idea a new core subsystem.

## Cross-workstream integration reviews

Review at least: duplicate identity/registry/runtime ownership; hidden Book/BMS coupling; app-use privilege escalation; stale targets and account mix-ups; current-state evidence versus proposal; projection versus rerun semantics; incomplete historical-data meaning; shared subscription lifetime; long-running job recovery; plugin uninstall during work; dependency/version skew; secrets/private-memory export; and installer/provisioning side effects.

A useful hypothesis to test is that existing owners plus a small set of new interfaces can meet the requirements. Neither that hypothesis nor a new-library alternative is pre-approved. Compare real dependency costs and two concrete implementations.


## W11 — Cross-app composition and stack compatibility

Study artifact, operation, workflow and optional view exports; composition without whole-code merging; dependency diamonds, shared instances and independently configured instances; compatibility pinning, removal, partial failure and legitimate bounded cycles. Define how a composite app's copilot discovers authorized contributions. Internal interfaces must state semantics, effects and scope independent of HTTP/IPC/in-process transport. Separate transient values, durable artifacts, jobs and streams.

Produce a stack decision matrix against current QMX: runtimes/languages, IPC/wire, schema contracts, provider/CLI adapters, metadata/analytical/blob storage, stream ownership, notebook/GPU isolation, test execution platform and future host/render integration. Reuse existing choices where suitable, explicitly justify changes and their migration impact. Do not add dependencies merely to mirror donors. Stage B independently challenges this matrix and its consequences.
