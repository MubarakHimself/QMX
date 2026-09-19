# QMX Pass I Intent Extraction

Scope: only `pass1-sources/Explore-Node-Editor-Architecture.md` and `RECON-RETURN.md`. This is an intent/behavior extraction, not architecture ratification.

## Evidence classification

- **User requirement (explicit):** QMX should compose capabilities into understandable/reusable work; support experimentation/storyboards as well as reusable procedures; allow deterministic and non-deterministic/agent-assisted steps; permit ordinary Python; support on-prem and VPS/server execution; let work continue after the laptop closes; upgrade the artifact/library surface; enable apps/capabilities to interoperate; expose extensibility/plugin-like additions. (Explore…, lines 26, 116-156, 198 onward; lines 1791-1905)
- **Current implementation/fact:** QMA has mission compiler, authored graph templates, runtime task graph, dispatcher/leases, and procedure instantiation, but persistence and UI dispatch are uneven. QML Stage 0, research blob storage, graduation, and federated discovery have advanced at revision 270e992. (Explore…, lines 52-68; RECON…, lines 20-58)
- **Proposed design/idea:** workflow/app contracts with typed inputs/outputs plus effects and authority; versioned drafts/runs; reusable parameterized procedures; invalidation-aware reruns; evidence board partly non-executable; copilot discovers capability descriptors and session permissions; files/artifacts for bulk handoff and APIs/streams where needed; built-ins and extensions share interfaces. (Explore…, lines 90-156, 1725-1751)
- **Assumption/open question:** server execution location, credentials/data access, database durability, exact division between QMA agentic tasks and the separate workflow/automation system, and stack choices require proof/decision. (Explore…, lines 104-110, 198 onward; RECON…, lines 20-30, 58)

## Operators and participants

1. **Primary operator/researcher:** authors exploratory storyboards, selects existing governed strategies, configures Books/BMS or alternative risk/portfolio components, runs comparisons, reviews evidence, records conclusions, saves reusable procedures.
2. **Copilot/agent:** optional authoring or bounded workflow participant; must discover installed capabilities, schemas, effects, and session permissions dynamically. It is not the authority owner.
3. **Workflow/app runtime:** coordinates capabilities and lifecycle; may be deterministic or agent-assisted; distinct from QMA’s long-running agentic task runtime.
4. **Capability specialists/owners:** QMA, QMB, QML, QMF, Trading Node, Book, BMS, data/library/evidence services retain domain responsibility. QMF is one framework/toolbox, not a second product scheduler.
5. **Operator/supervisor and live execution:** retain authority chain Bot → Book → BMS → Operator; research workflows must not silently mutate live Books, positions, accounts, or allocation.
6. **Authoring session vs app-use session:** authoring creates/edits/version-publishes definitions; app-use executes an immutable/pinned definition and observes/intervenes through explicit commands. A session owns context; it is not a browser tab.
7. **Portfolio Manager:** the product role label is Portfolio Manager (existing slug may remain `pm-coordination`), not Product Manager. (RECON…, F-13)

## Behavioral requirements

- Compose existing capabilities rather than invent a new strategy language, trading runtime, or replacement UI. (Explore…, lines 48, 188)
- Represent a step as a contract: accepted inputs, outputs, owner, execution location, side effects, authority, retry/idempotency, and failure behavior. (Explore…, lines 90-104)
- Support files/artifacts for large outputs and API/streams for control or streaming; preserve evidence references and lineage rather than embedding all data in workflow JSON. (Explore…, lines 1735-1749)
- Distinguish hypothesis/evidence/storyboard relationships from executable dependencies. (Explore…, lines 152-156)
- Permit subflows/detail levels; do not force every function or Python operation into a visible node. (Explore…, lines 140-150)
- Separate browser/client closure, worker restart/recovery, and server migration; declare execution location and credentials. (Explore…, lines 104-110)
- Editing a definition creates a new draft/version; an in-flight run keeps its pinned definition. Explicit intervention only. (Explore…, lines 110, 1688-1717)
- Retry/recovery must not duplicate successful external effects; deliberate rerun is a new historical run. (Explore…, lines 108-110)
- Preserve evidence semantics: Book/risk/sizing changes are genuine path-dependent reruns, not mere rescaling/filtering. (Explore…, lines 130-138)
- First end-to-end proof: governed strategy → two complete research Book configurations through QMB → compare evidence → record conclusion → save reusable procedure. (Explore…, lines 172-180)
- Acceptance coverage includes reconnect, partial branch failure, interruption/recovery, concurrent editing/versioning, and exact input provenance. (Explore…, lines 176-180)
- Existing implementation constraints: full-run config still requires Book/BMS; venue kinds remain closed; TaskGraphStore has no edges/dispatcher successor walk; topology must reject all cycles; daemon listener currently drains bytes without dispatch. (RECON…, F-05–F-10)
- Data/ML capabilities need not be bots; specialists remain specialists. Book/BMS are defaults, not a ceiling on customizable risk/portfolio designs. (Explore…, lines 198 onward; preserve stated correction)

## Invariants and authority boundaries

- QMF is a single framework/toolbox for identity/data/registry/risk contracts; do not relocate scheduling/orchestration into it.
- A connected node/app cannot gain authority beyond its capability contract; research invocation cannot mutate active execution.
- Bot → Book → BMS → Operator remains the live authority chain; workflow is not a central allocator.
- Measured results, agent interpretations, hypotheses, source excerpts, and approvals are different artifact classes.
- A run is pinned to an immutable definition/version and records exact inputs, outputs, lineage, and effects.
- Session context is distinct from UI tabs; app-use cannot edit implementation/definitions. Authoring permissions are separate.
- Specialists (QMA/QMB/QML/QMF/Trading Node/data/ML) retain ownership; composition delegates rather than absorbs responsibility.
- Agents are optional; deterministic workflows remain first-class.
- A graph validator must enforce DAG/cycle laws, not only direct reverse-edge checks. (RECON…, F-08–F-10)

## Lifecycle expectations

`draft → validate (types/effects/authority) → publish/version → instantiate run (pin definition + inputs) → queued/running → waiting/paused/interrupted → succeeded/failed/cancelled → recover/retry or deliberate rerun → inspect evidence/lineage → promote selected exploration to reusable procedure`.

Parallel branches may complete independently; partial outputs remain inspectable. Reconnect must reattach to server-owned state. A definition edit never mutates an active run. Capability/permission revocation must block future invocations and produce an auditable outcome.

## End-to-end journey families / candidate IDs

- **J-AUTH-01 Storyboard exploration:** collect strategy, hypothesis, source, chart, and candidate nodes; mark non-executable relationships; selectively promote operations.
- **J-AUTH-02 Compose-and-validate:** choose capabilities; inspect schemas/effects/authority; reject cycle, missing input, forbidden side effect, or unavailable permission.
- **J-RUN-01 Governed comparison:** run one strategy under two complete Book/BMS configurations via QMB; preserve branch provenance and compare evidence.
- **J-RUN-02 Partial failure:** one branch fails while another succeeds; retry failed branch without duplicating successful effects.
- **J-RUN-03 Disconnect/reconnect:** close browser/laptop; server-owned run continues; reconnect and observe progress/results.
- **J-RUN-04 Interrupt/recover:** pause/interruption plus worker failure; recover idempotently or expose explicit rerun.
- **J-VERS-01 Concurrent versioning:** author publishes v3 while app-use runs pinned v2; reconnect still observes v2.
- **J-AUTHZ-01 Authority boundary:** research step attempts live Book/BMS mutation; deny and audit.
- **J-AUTHZ-02 Permission revocation:** revoke capability/session permission between steps; block invocation, preserve prior artifacts.
- **J-DATA-01 Artifact handoff:** large dataset/file output passes to another app; API/stream used only where necessary; lineage retained.
- **J-LIB-01 Library/procedure reuse:** inspect artifact library, parameterize a successful exploration, save versioned procedure, instantiate later.
- **J-EXT-01 Extension parity:** install an app/plugin/capability; copilot discovers its descriptor and permissions without core-prompt rewrite; built-in and extension contracts behave consistently.
- **J-CUSTOM-01 Beyond defaults:** author a custom portfolio/risk/data route or ML/data specialist without requiring it to be a bot or forcing Book/BMS semantics.

## Key unresolved decisions for later passes

Execution placement (on-prem/VPS), durable stores and recovery guarantees, capability packaging/discovery schema, copilot mediation, QMA/workflow boundary, and live-operation approval policy require architecture evidence and explicit decisions; this pass does not ratify them.

