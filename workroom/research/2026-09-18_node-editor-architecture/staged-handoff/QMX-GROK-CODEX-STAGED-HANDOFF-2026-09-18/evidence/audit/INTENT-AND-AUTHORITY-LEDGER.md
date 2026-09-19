# Intent and authority ledger

Audit date: 2026-09-17. Source transcript: session-input/Explore-Node-Editor-Architecture.md (1,239 lines). This ledger reconciles intent; it does not ratify architecture or authorize implementation.

## Authority order used

1. The operator's latest clear correction.
2. Earlier operator statements that were not superseded.
3. Current ratified QMX documentation as current design authority.
4. Source and reproducible diagnostics at the recorded revision as implementation evidence.
5. Assistant suggestions, screenshots, donor products, old reconnaissance and the prior handoff as proposals or research inputs only.

The two screenshots are references only. image-001 depicts a proposed QMX operations/dashboard surface; image-002 depicts a Taskade assistant/workspace/flow/app-preview arrangement. Neither proves QMX functionality or another product's hidden architecture.

## Turn-indexed accepted intent

| Turn / transcript location | Latest operator outcome | Authority effect |
|---|---|---|
| T1, lines 3–8 | Explore a substantial node/editor direction inspired by n8n and follow evidence beyond the seed prompt. | Exploration authorization only; no implementation. |
| T3, lines 194–200 | The system spans Library, Trading Node, risk, sizing, backtesting, research and hypotheses. Agents are optional. Local and always-on/VPS placement are both relevant. A canvas can contain disposable, non-executable research. | Supersedes the assistant's QMA-centric and reusable-procedure-only framing. |
| T5, lines 309–324 | Defaults and templates are required alongside custom construction. Taskade and OpenBB are patterns, not authorities. | Do not require blank-slate authoring or clone donor object models. |
| T6, lines 425–600, especially 595 | QMF is the one framework; QML, QMB, QMA and QMN belong to its ecosystem without necessarily moving into one namespace. Data/API/CLI, polling, streaming and resolution matter. QMA's advanced capabilities may be restructured but must not be casually removed. | Rejects a parallel-framework answer and requires code-backed extensibility analysis. |
| T8, lines 718–872, correction near 840 | QMF should be a construction kit for complete systems. The current Book/BMS/SQS/MIS arrangement is a possible composition, not the framework's ceiling. Trading-floor PM means Portfolio Manager. | This is the controlling framework correction. Do not replace genuine Product Manager references in BMAD/product material. |
| T9, lines 882–1064 | Separate app-use and authoring copilot sessions. An app-use session may inspect and invoke exposed operations but must not edit implementation or grant itself powers. Replacement is normally sequential development, evaluation and deployment, not unsafe hot swap. QMN represents continuous hosting but must not own every possible local/supervised execution arrangement. | Supersedes one-global-chat, one-Agent, and QMN-as-universal-owner interpretations. |
| T10, lines 1054–1072 | Trace the entire hypothesis → QML → QMB → validation/iteration → QMN lifecycle. Support app/system-specific templates, headless/CLI/notebook steps, actual GPU/provider capability checks, widgets, multiple brokers and multiple accounts. A dashboard is aggregation, not an implicit execution target selector. Codex should audit first; Grok should architect later. | Defines this audit's stop boundary and the downstream architecture scope. |

## Accepted distinctions to preserve

- QMF is the framework/construction kit. “Under QMF” does not require a qmf.* namespace or application behavior inside qmf-core.
- Capabilities perform operations; extensions contribute capability; workflows compose work; mini-apps expose useful combinations; widgets are views/controls. These are related but not one-to-one.
- QMA Mission/Task Graph execution is not automatically the general workflow model.
- QML Stage 0 research, governed QML definitions/logic, QMB experiment evidence, and QMN deployment are different planes.
- A draft, published definition, installed app instance, run/attempt, deployment and external account are different identities.
- Semantic identity excludes cosmetic layout unless layout changes trading meaning. Package version, installed instance, deployment revision and execution ID remain distinct.
- Source provider, execution venue/broker, account, credential, data permission, execution permission, app instance and execution environment must not be collapsed.
- Paper/replay, broker demo, and live are separate meanings. Software rollback cannot reverse external trades.

## Explicit corrections and migration impact

### Portfolio Manager

The transcript correction is specific: trading-floor “PM” means Portfolio Manager (around line 840). Required later work is a scoped vocabulary and data migration:

- change trading-domain PM labels, role ids, plugin copy and documentation where they mean Portfolio Manager;
- preserve true Product Manager references in BMAD/product-development material;
- provide aliases/migration for stored trading-domain identifiers rather than blind search-and-replace;
- do not apply the change during this audit.

### One copilot identity, independent sessions

The product identity may be QMX / QuantMind Copilot, but sessions are independent. The two required profiles are:

- authoring/experimentation: may create candidate revisions using explicitly granted file/code/test/tool/environment capabilities;
- app-use: pinned to an app instance/version and allowed operations, may query/explain/run exposed operations and inspect evidence, but cannot edit source, install code, redefine schemas or elevate itself.

The model may be the same. Authority comes from host-granted capability and context profiles, not model intelligence or app-supplied prose.

### Complete-system construction

The current Book/BMS/MIS/SQS system is an architectural probe and useful default, not a universal requirement. A complete package may choose different risk, sizing, allocation, intelligence and supervision arrangements. Compatibility must be proven at named interfaces; it must not be faked by wrapping a semantically different system in Book/BMS labels.

## Current documented authority versus desired direction

| Subject | Current documented authority | Latest desired direction | Reconciliation status |
|---|---|---|---|
| QMF role | Ratified contracts-first toolbox with five libraries plus Venue and Risk modules; applications are built ON it. | One construction kit for varied complete systems. | Compatible in principle, incomplete at application-composition seams. |
| Workbench | ADR-0022 is ratified. It explicitly chooses composition over existing applications, Book/BMS candidate variants, QMA procedures and QMB steps. | Broader deterministic/non-deterministic composition and alternative system policies. | Ratified workbench is a narrower starting point; amendment required where it forbids/assumes more than the new outcome. |
| QML Stage 0 | DEC-0380 paradigm is ratified; ADR-0023 and most absorbed decisions remain provisional. Source note says Stage 0 types do not exist at integration 8510c03. | Full hypothesis/dictionary/authoring stage. | Documented proposal, not implemented or generally accepted. |
| QMA UI/app packaging | qma-ui-contract and UI extension SDK are deferred (GAP-0081). | Mini-apps, widgets, app-use context profiles and preview. | New architecture contract required; do not claim it exists. |
| QMA→QMB | ADR-0022 requires real CLI transport; current code has a real transport test surface but no audited whole-product composed run. | Reliable headless reuse from apps/workflows. | Implemented/unit-tested seam; integration proof still missing. |
| Continuous placement | QMA continuation property is documented; concrete host is GAP-0062. QMN has VPS/systemd deployment. | Local, remote/VPS and supervised execution chosen by capability. | Separate existing mechanisms need a coherent placement contract; no ambient GPU/cloud assumption. |

## Superseded suggestions

- “One Book configuration comparison” is only a useful falsification slice, not the platform scope.
- “Expose QMA orchestration through the canvas” is too narrow; QMA is not the universal owner.
- A new parallel workflow framework/library is not the default; first test whether existing owners can expose deeper interfaces.
- Treating Book/BMS as mandatory system primitives is superseded as product intent, though still true of current QMB/QMN implementation.
- Treating QMN as the only runtime destination is superseded by local/VPS/supervised placement goals.
- “Research Board” is not the settled name; the exploratory surface is Experimentation Board in the QMX Workflows direction.
- JSON Render and MCP Apps are candidate presentation/host protocols, not execution, persistence or authorization systems.

## Unresolved choices for the later architecture session

1. The canonical complete-system package/interface and who owns it.
2. Whether the smallest compatible change is a generic system-policy seam in existing QMF Risk/QMB/QMN or an additional QMF-owned contract family.
3. How an authored workflow definition relates to QMA Graph Templates without making every workflow a Mission.
4. App definition, installed instance, run and deployment identity/persistence.
5. Product-session/app-context contract and cross-session retrieval.
6. Typed dataflow semantics: ports, cardinality, fan-out/join, loops, partial execution and side-effect idempotency.
7. Point-in-time multimodal dataset and recipe contracts.
8. Broker/venue adapter discovery beyond the fixed current selector.
9. Local/remote/GPU environment declaration and capability negotiation.
10. UI contribution packaging and host authorization, including JSON Render/MCP Apps adaptation.

## Opportunity seeds, not commitments

Taskade-style combined assistant/workspace/flows/preview; n8n-style inspectable composition; OpenBB/QuantConnect data patterns; London Strategic Edge; Caliper skill creation; agentic research loops; reusable optimizers/data routes/risk modules; mini-app lineage and change-request handoff; readiness and operations widgets.

## Transcript evidence note

The detailed contiguous-read extraction is retained at diagnostics/TRANSCRIPT-LEDGER-DRAFT.md. No assistant proposal from that transcript was treated as accepted without later operator support.
