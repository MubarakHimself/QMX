# Feature impact register — product and platform expansion

Status: preliminary discussion record. This is not SPEC.md or an architecture spine. Reference opportunity IDs F01–F17 remain defined in `inspection-and-feature-opportunities-2026-09-12.md`; do not renumber them or create a competing full feature catalogue here.

## User corrections governing this register

- New product features may require extending QMB, QML, QMF and the data/persistence, middleware and API layers. They are not merely screens over assumed-complete services.
- QMB must remain useful independently through Python/CLI. QML is a structured bot-authoring library, not merely UI organisation.
- User suspects STRATS has richer strategy/bot semantics than QML. Record a compatibility/enrichment investigation for later; do not claim the mismatch is proven or redesign QML now.
- Shared Library and end-user extensibility are core product requirements. The user should be able to extend supported aspects of QMX without reading source code.
- Lieflat remains the preferred chart-language reference, especially for data-rich bot attributes/evidence. The FC/FIFA analogy remains identity plus attributes/statistics, not a fabricated aggregate score.

## Documented basis checked

- `_docwork/ledger.yaml` DEC-0159: QMB library, CLI, Python API and later MCP doors; UI backend consumes the Python API in-process; added capabilities through adapters/config fragments/library functions. No duplicated implementation per door.
- DEC-0160: resolved, fingerprinted run configuration and explicit Book/BMS fragment namespaces. Named conditions are config fragments. This is relevant to templates and scenario variants.
- DEC-0161: pure run returns results; the impure orchestrator owns logs/ledger and run processes. The same package is intended on laptops and sandboxes; no required Docker or daemon.
- `docs/decisions/ADR-0017-qmb-experimentation-library.md`: LEAN CLI and Jesse inspired requirements/mechanisms; code/engine adoption was rejected. Keep 'inspired by' separate from 'depends on'.
- `docs/components/qml.md`: declaration plus versioned Python logic, authoring helpers/runtime protocol/conformance. Declaration fields carry editable/uneditable discipline. This does not prove a rich no-code strategy composer exists.
- `docs/components/qmf-data.md`: data-policy/API responsibilities already differ from ingest middleware, physical store and backup execution. Extend these boundaries deliberately; do not create a second data layer inside QMB or choose a database because a screen needs a table.

All above are **documented basis**, not verified implementation. Proposals below must be checked against inherited spines before becoming architecture decisions.

## Initial impact records

| Feature / status | Product surface question | Library/compute question | Data and API question | Open evidence / scope |
|---|---|---|---|---|
| F01 Templates and candidate generation — user strongly interested | Where are templates authored, shared and used? Which rules stay fixed and which vary? | Are declared parameter changes sufficient, or is composable condition/logic generation needed? Preserve QMB/Python access | Store/reference template versions, chosen inputs, candidate lineage and run configuration; expose validation and compatible choices | STRATS→QML semantic compatibility is a separate deferred audit. No arbitrary generation support assumed |
| F02/F03 Batch experimentation — proposal | How does a person or agent configure a campaign and inspect many candidates? | Reuse QMB execution and QMA procedure concepts where supported; genetic-search support requires exact audit | Candidate/run lookup, stages, progress, failures, restart state, retention and bounded result queries | Avoid treating a genetic algorithm as only a progress bar; population/generation/fitness lineage may introduce new requirements |
| F05/F06 What-if and sizing — user interested | Compare baseline with an explicitly altered assumption/configuration | Distinguish filtering/rescaling prior trades from rerunning path-dependent Book/BMS behavior | Preserve baseline, changed assumptions, input versions, comparison method and output references; expose scenario execution/status | Exact simulation semantics not decided. A scenario result is not an operational change |
| F09/F10/F11 Data preparation and quality — proposal | Browse coverage, anomalies, transformations and previews where work needs them | Determine which acquisition/quality/transform operations already exist | Raw evidence, derived versions, gap/quality outputs, provenance, large-data queries and live/replay semantics | Physical database/store choice remains open within existing architecture; do not equate UI worlds to backend evidence worlds |
| Bot profile — confirmed mental model, composition open | Same recognizable bot identity with useful attributes and evidence across worlds | QML supplies structure; identified runs supply measurements | Join definition/version with results and optional operational references; label dataset, interval and missing/incomparable measurements | Lieflat informs presentation, not metric definitions. No overall score assumed |
| User-facing extension system — confirmed intent, mechanism open | Discover/configure/use supported extensions without source access; local tools versus full worlds | Identify config-only, compositional and executable additions; preserve independent libraries | Contribution metadata, compatible versions, dependency/permission visibility, persisted configuration and safe failure/unavailability | No plugin manifest, sandbox, installer, runtime loading strategy or universal no-code guarantee chosen |

## Consistent record shape for later additions

Each added feature record should carry: stable ID; intent; source; adoption status; main world and other consumers; shared inputs/outputs; extension mechanism; existing documented basis; implementation evidence; proposed library/data/API/UI changes; open questions and dependency links. Detail lives with the record rather than expanding the global menu.

Do not write final API shapes or database schemas until semantics and ownership are understood. Conversely, do not defer data needs until after visual design: volume, lineage, filtering, live updates and versioning affect which interaction can work at all.

## Open-lab clarification and baseline reconciliation

Latest user intent: open-ended experimentation with normal Python and optional QML/QMB, supplied or discovered sources, reusable agent-assisted loops, and durable remote teams. New reference evidence is in `research-harness-references.md`; references remain donors, not selected dependencies. These cross-cutting checks do not renumber F01–F17 or assert that all listed behavior is implemented.

| Requirement | Documented basis | Product/architecture work still needed |
|---|---|---|
| Research when needed, across supplied sources, Library, papers, articles and videos | QMA `KnowledgeSource` preserves citations and copied evidence, but v1 is literal/locator-based lookup with no index (`qma-daemon.md`, AD-19, GAP-0073) | Audit ingestion/discovery/normalization and retrieval coverage separately from evidence custody. Rich indexing is not already provided merely because an agent has a search tool. Any extension must respect the owning port and existing persistence constraints |
| Composable procedures and iterative experiments | Graph Template = versioned topology; Loop = control cycle with runtime-owned stopping condition, budget and escalation; Skill = reusable procedure/knowledge. QMA has parallel/join/human-gate node kinds, but no bundled graph templates in v1; graph implementation choice is deferred (AD-13, GAP-0086) | Author usable procedures and controls without making one sequence compulsory. Record individual attempts, stop reasons, failures and changed methods. Expose progress and pending human work without making a chat transcript the work record |
| Coordinated work while laptop is off | Durable Task Graph, ledgers, JobHandle and continuation budget exist in the documented design (AD-9/12/17/29); client detach never stops work (`qma-wire.md`, AD-5) | A workstation-default daemon plus remote workers is not by itself an always-on organisation. Resolve supervisor/state placement, disconnect/recovery, remote resources and reconnect surfaces; remote workers must not depend on a sleeping coordinator to start the next task. No deployment or infrastructure purchase authorized |
| Isolation without silently adopting a donor stack | QMB standalone execution has no mandatory Docker/daemon; QMA separately specifies Docker-per-worker by default with other environment kinds (AD-17/25) | Reconcile the operator's earlier no-Docker statement with QMA's documented default. Do not conflate QMB independence with QMA placement, or import OpenResearch worktrees/Delphi PostgreSQL as requirements |
| Tool-produced evidence rather than agent-invented outcomes | CT-47 content-addressed inputs/configuration/data/environment/seed/model/harness and lineage; defined-unwired. QMB pure result and governed orchestration split; QMA deterministic completion verifiers | Protect evaluator/protocol identity and canonical raw outputs. Proposal: agent changes to methods create a new explicit version; derived interpretations are separately labelled. Verify test/data isolation and incomplete/failed attempts are visible. Determinism does not prove correctness, eliminate stochastic variation or guarantee edge |
| Reusable strategy/Book/BMS variants and exact approval | Registry content identities and branching; CT-22/27 definitions; bindings separate; signed promotion occurrence references the exact artifacts (`qmf-registry.md`, AD-16–18/30) | Design history/diff/compare/reuse and exact-version approval views, not GitHub or a second canonical Library database. Editing a candidate must not silently edit an active binding. Precise workflow remains unagreed |
| Paper testing before live | Already in node DEC-0261: bots arrive backtested, paper-tested outside the node and operator-approved; no per-bot warm-up lane after promotion | Reconcile the research paper-test execution owner and surface with QMB's no-account boundary and QMA's prohibition on account execution, paper included (CT-47/DEC-0341). Do not claim agents can autonomously paper-trade through QMA or invent a new component. Keep the Trading Node integrated |

Proposed engineering principle for discussion: freedom in the investigation, strict provenance in recorded evidence, and explicit human authority at the operational boundary. This is not a finalized architecture amendment or a new permission policy.

## Decisions not made

No replacement framework, central QMB service, per-department database, new QML language, copied donor engine, UI plugin protocol, production schema or new permission policy is selected. A new requirement conflicting with an inherited contract must be surfaced as an amendment decision, not silently worked around.
