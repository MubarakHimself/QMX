# QMX reconciliation audit return

Audit date: 2026-09-17 (Africa/Nairobi)

Evidence revisions:

- planning repository: main at b8b4d21a3d6ec33158254f1827912c8fc0c4dcc3;
- implementation worktree: integration at 8510c032496bb870824ecc5c4f807e8a4e4f167e, clean and 32 commits behind its configured remote-tracking branch;
- session transcript: all 1,239 extracted lines reviewed, with later operator corrections given precedence;
- focused verification: 54 selected tests passed in 12.95 seconds using disposable audit-local pytest state.

This is a read-only reconciliation audit. It does not ratify an architecture, revise the earlier handoff, change either repository checkout, or begin implementation.

## Operator summary

QMX already contains a strong reusable substrate, but it is not yet a complete construction kit for materially different end-to-end trading systems.

The reusable substrate is real: exact identities and values, immutable provenance, kind registration, market execution-fidelity ports, QMA capability narrowing, replaceable compute/tool/context ports, and an explicit QMN multi-account roster. The current complete path is narrower. QMB requires Book and BMS fingerprints and evaluates admission and sizing through Book-resolved R. QMN's configuration and runtime combine reusable hosting/safety concerns with the present Book/BMS/SQS/MIS trading design. Consequently, a second system with genuinely different risk, sizing, intelligence, or portfolio composition cannot yet pass through QMB and QMN honestly without core edits or misleading compatibility wrappers.

The two copilot experiences are also not represented yet. QMA Session is currently an agent-execution container with owner, execution model, and autonomy. It is not a durable product conversation containing an application instance and version, selected domain objects, allowed operations, account scope, or an authoring-versus-app-use profile. QMA's frozen spawn permissions are a good enforcement primitive, but the product-session contract and its host-granted context still need to be defined and wired.

The QML lifecycle is partly implemented and partly prospective. CT-33/CT-34 declarations and conformance/graduation exist and are tested in isolation. The Stage 0 research mill is provisional and documented rather than implemented at the inspected revision. No evidence established a composed QML to QMB to validation/iteration to QMN run.

The most defensible option for architecture preflight is therefore a narrow compatibility-preserving seam extraction, not a wholesale framework replacement and not a new general library by default. Existing owners should be assessed first. Subject to an explicit ADR, the current Book/BMS/SQS/MIS composition could become one system-package or policy implementation behind general contracts; QMN's reusable host controls could be separated from that rulebook; product sessions could carry host-granted app context and profiles; and QMF Data could gain typed multimodal facts and dataset recipes without creating a duplicate data store. These are audit recommendations, not accepted architecture.

## Central framework answer

The operator's intended QMF is one framework that can be used to construct different complete systems. The current implementation satisfies that intent at the primitive and port level, but not across the whole application lifecycle.

The distinction is important:

1. **Already extensible:** low-level identities, values, provenance, registry kinds, execution-fidelity adapters, QMA agent capability narrowing, and explicit account rosters.
2. **Extensible only inside the current composition:** Book/BMS variants, current protection/KSA/SQS/MIS rules, and replay-bound QMB risk semantics.
3. **Documented or provisional:** the Stage 0 QML research mill, a general mini-app package model, product app sessions, a general typed workflow/dataflow contract, and the full composed lifecycle.
4. **Needs wiring or seam extraction:** a system-neutral QMB policy boundary, a host-versus-rulebook split in QMN, app context/profile enforcement in QMA, multimodal dataset recipes, and end-to-end lifecycle proof.

The framework should preserve strong non-negotiable laws such as exact identity, provenance, refusal semantics, explicit account selection, immutable authority narrowing, and money-path safety. It should not elevate Book, BMS, SQS, MIS, or a particular desk composition into universal framework law. Those are currently valuable implementations and defaults, not the ceiling of QMF.

## Authoring and app-use copilot sessions

These should be separate product-session profiles sharing one underlying authority system.

As target semantics from the operator's correction, an authoring session may inspect definitions, compose or revise a system package, run validation, and propose deployment artifacts subject to explicit permissions. An app-use session would be bound to a specific installed application instance and version, expose only that app's declared operations and views, carry selected objects and dataset/run context, and normally be unable to alter the package, broaden its tools, or silently switch accounts. A conversation would be able to say what app instance, version, object selection, data release, run, deployment, and account scope it is about. This target behavior is not current QMA capability evidence.

The current QMA Session record does not encode those facts. Its non-durable attachment field is explicitly unsuitable as the authoritative product context. One architecture-preflight candidate is a durable host/session-context contract and profile identity whose allowed-operation set maps into the existing spawn-time capability and permission narrowing. That addition requires an explicit architecture ruling. Skills must remain descriptive behavior; they must not grant authority. Memory should continue behind the existing MemoryProvider boundary, with explicit scopes and provenance, rather than becoming a second authority or application-state store.

## Main coupling findings

### QMB binds complete runs to Book/BMS

The QMB compiler requires book_fp1, bms_fp1, book_fragment_fp1, and bms_fragment_fp1 and mints a replay binding for the run. Its risk path requires a ReplayBinding and Book-resolved requested R under CT-23/CT-29 semantics. The variant API accepts complete BookDefinition or BmsDefinition candidates, not arbitrary system policies. Fill, slippage, cost, and financing are already proper ports, but those ports vary execution fidelity; they do not replace the admission, sizing, or portfolio policy.

Therefore Book/BMS is hard-coded at the full-run composition boundary even though parts of the execution engine are extensible. An alternative system cannot be compared faithfully by wrapping it in fake Book/BMS artifacts. That would erase the very semantic difference the experiment is supposed to test.

### QMN mixes reusable hosting with the current rulebook

QMN has a real reusable multi-account foundation. Its roster identifies venue, account, execution environment, and credential binding explicitly, and command streams are keyed per venue/account with no global default. That supports multiple accounts and can support multiple deployments safely.

However, the configuration compiler fixes layers around roster, BMS, Book, and node defaults, while runtime modules embed current Book seats, BMS, protection/KSA, SQS, MIS, and paper-execution rules. In addition, venue selection uses a closed VenueClientKind enumeration for replay, cTrader, and conformance. A second cTrader broker/account can be configured, but a materially different broker adapter technology requires editing the selector owner.

An architecture preflight should preserve demonstrably host-level controls: explicit identities, credential isolation, command idempotency, reconciliation and unknown-outcome handling, refusal, observability, and safe state transitions. It should separately rule which current protection/KSA behavior is universal host safety and which is policy-dependent. The current trading rulebook is a candidate supplied system policy or package contribution, not yet an accepted split. Not every system needs MIS, Book seats, or the current sizing grammar, but no system may bypass whatever host-safety contract is ultimately ratified.

### QMF Data has provenance but not the complete data construction kit

QMF Data correctly distinguishes a source/provider from a venue and preserves event time, known-at time, revision, and correction lineage. QMB's provider adapter is quote-shaped around symbol, resolution, and bid/ask sides. The inspected QMF observation shell does not expose a general typed payload suitable for sector classifications, fundamentals, macro series, news, sentiment, or model-derived intelligence. No first-class dataset recipe/builder contract was found that pins and combines heterogeneous releases.

The candidate owner remains QMF Data. Architecture preflight should assess an additive, versioned fact/payload and dataset-recipe contract rather than a parallel intelligence data store. If accepted, a recipe should identify every input source and revision, temporal semantics, transforms, joins, derived features, and resulting immutable release so QML/QMB/QMN can refer to exactly the same evidence.

### QMA procedures are not a general workflow engine

QMA Graph Templates, Missions, routines, and task graphs form a substantial agentic organizational runtime. They are appropriate for delegated work, authority narrowing, and agent procedure. They are not presently a generic typed dataflow model with port schemas, cardinality, fan-out/join, deterministic subflows, resumability, and package/run/deployment identities.

Do not force every application workflow through Missions. Reuse QMA when a workflow is agentic. A small deterministic system/workflow description contract is a preflight option, not a current requirement; it should be introduced only when a concrete second execution model establishes its semantics and owner. Avoid introducing a second general scheduler unless such evidence proves that it is necessary.

### QML lifecycle is not yet composed end to end

CT-33 bots, CT-34 confluences, registration gates, and graduation mechanisms exist. They establish governed definitions and technical conformance; they do not prove strategy merit. The proposed Stage 0 research/corpus facilities are not implemented at this revision. The audit did not find or execute a single path that starts with a QML research/definition artifact, builds and iterates it in QMB, validates/graduates the exact artifact, and deploys that same governed identity into QMN.

The lifecycle should preserve one identity and provenance chain through research inputs, declaration, build, experiment, validation decision, governed artifact, deployment, run, and operational observations. Each transition needs an explicit owner and refusal contract. Documentation describing those transitions is not evidence that the composed path exists.

## Direct answers

### What is hard-coded versus a default?

- Exact identity, provenance, explicit account selection, authority narrowing, refusal behavior, and operational safety are appropriate framework invariants.
- Book/BMS is hard-coded in the QMB full-run compiler and risk path, not merely selected as a default.
- Book/BMS/SQS/MIS and related seat/protection logic are embedded in QMN's current complete runtime composition. They should be treated as the present reference/default system, not universal law.
- Replay, cTrader, and conformance are a closed core venue-client selector today. Multiple accounts are supported, while arbitrary broker technologies are not plug-in complete.
- The Experimentation Board is the current operator term. Earlier references to a settled Research Board do not carry authority.

### What can be replaced without core edits?

- Registered kinds can be added through the registry's public mechanism, subject to protected names and contracts.
- QMB fill, slippage, cost, and financing behavior can be replaced through existing ports.
- QMA compute, model, tool, knowledge, execution-environment, context, and memory implementations have declared port seams, although several concrete production bindings remain deferred.
- Agent/plugin contributions can be loaded within QMA's authority restrictions.
- Accounts, venues, environments, and credentials can be enumerated through QMN roster records.
- The complete risk/sizing/intelligence composition, a different broker client technology, app-session profiles, mini-app definitions, and general typed workflows cannot currently be substituted end to end without owner changes or new wiring.

### Can materially different systems run through QMB and QMN today?

Not with consistent semantics and without core changes. A system that does not use Book/BMS or that uses a different sizing/admission grammar fails at QMB's required configuration and risk contract. A system with a different operational composition encounters QMN's embedded rulebook. Compatibility shims that invent Book/BMS values would create false comparability and are not recommended.

### Are session, context, and memory sufficient?

They are sufficient primitives for agent execution, not sufficient product semantics for the two copilot experiences. The missing durable contract includes profile kind, app/package instance and version, selected objects, allowed operations, data/run/deployment references, account scope, context revision, and audit provenance. Those fields must be host-granted and enforced through existing permission narrowing. Memory remains subordinate and scoped; it must not silently broaden authority or substitute for governed context.

### Which responsibilities belong to existing owners?

- QMF Core/Registry: stable identity, package/definition/run/deployment identifiers, versioning laws, protected kinds, and refusal semantics.
- QMF Data: typed multimodal facts, temporal/revision semantics, dataset recipes, immutable releases, and lineage.
- QMF Risk or a sibling framework contract: the smallest system-neutral admission/sizing/policy interface, once two real implementations establish shared semantics.
- QML: research-to-governed strategy construction and conformance, including the proposed Stage 0 facilities after architecture review.
- QMB: reproducible experiments and comparisons that consume declared system-policy contracts without inventing their semantics.
- QMA: agentic procedures, capability enforcement, model/tool/compute/context/memory ports, and execution of authorized copilot operations.
- QMN: reusable always-on hosting, account/venue isolation, safety, reconciliation, execution supervision, and observability; system-specific trading policies should be injected rather than universalized.

No new general framework library is justified by current evidence. A small package-envelope or system-policy contract may eventually deserve a QMF home, but only after the two-system falsification proof demonstrates that existing ownership would otherwise be contradictory. Creating a broad new framework now would risk duplicating QMF Registry, QMF Data, QMA plugins, and QMN deployment concepts.

### What contracts should exist now so later UI work stays thin?

- versioned package/application definition, installed instance, run, and deployment identities;
- declarative operation descriptors with input/output schemas, capability requirements, side-effect class, and refusal/error shapes;
- host-granted session profiles and context updates, including selected objects and account scope;
- capability discovery and configuration schemas for providers, policies, workflows, brokers, accounts, and execution environments;
- stable run/event/log/progress/cancellation/reconnect contracts;
- installation, upgrade, migration, validation, enable/disable, and rollback lifecycle events;
- optional view contributions that remain presentation-only and cannot grant domain authority.

JSON Render is a plausible schema-constrained presentation vocabulary, and MCP Apps is a plausible sandboxed host/app protocol. Neither should own QMX domain permissions, application state, persistence, or execution semantics. The exact UI technology can remain undecided if these host contracts are stable.

### What is the smallest falsification proof?

Build one bounded vertical proof with two materially different systems:

1. System A is the existing Book/BMS composition.
2. System B uses a genuinely different risk/sizing or intelligence composition and does not pretend to have MIS or Book semantics it does not use.
3. Both consume the same pinned dataset release and invoke one operation directly and once as a workflow node.
4. QMB produces provenance-complete, comparable results while preserving each system's declared semantics.
5. An app-use session for System B can inspect and rerun allowed operations but cannot edit the package, widen its capabilities, or switch account scope.
6. QMN validates a System B deployment for an explicitly different demo account/environment and refuses an unsafe shared-account or incompatible transition.

The proof fails today at QMB's mandatory Book/BMS binding, the absent app/package/session contracts, and QMN's host/rulebook coupling. A successful proof would demonstrate a construction kit; another Book variant would not.

## Current reality classification

| Area | Current reality | Needed next |
|---|---|---|
| QMF primitive substrate | Implemented and broadly reusable | Preserve invariants |
| Book/BMS experimentation | Implemented within the current semantic family | Keep as reference implementation |
| Alternative risk/sizing/intelligence systems | Blocked by full-run coupling | Extract a system-neutral policy seam |
| Multiple accounts and deployments | Explicit roster and per-account streams exist | Prove isolation and transitions end to end |
| Multiple broker technologies | Closed selector for replay/cTrader/conformance | Add registered adapter selection without weakening safety |
| Multimodal/research data | Provenance primitives exist; payload/recipes incomplete | Extend QMF Data additively |
| QML governed declarations | Implemented and isolated-test evidence exists | Compose lifecycle and prove identity continuity |
| QML Stage 0 research mill | Provisional/documented | Architecture review, then implement if accepted |
| Authoring/app-use copilot split | Not first-class | Durable profile and app-context contract |
| QMA agentic procedures | Implemented | Reuse for agentic flows |
| General typed workflows | Not demonstrated | Define minimal contract; avoid Mission overloading |
| Mini-app package/instance/run/deployment | Documented need only | Define identity and lifecycle envelope |
| Thin UI host | Contract gap; UI SDK deferred | Stabilize protocol before selecting presentation stack |
| Full QML to QMB to QMN lifecycle | Not demonstrated | One composed falsification proof |

## Recommendations for the later Grok architecture pass

These are options and gates, not ratified decisions.

### Recommended option: narrow seam extraction

Define the smallest system-package and system-policy contracts needed by the two-system proof. Adapt the current Book/BMS implementation to them without changing its behavior. Make QMB consume the neutral policy contract and split QMN's host/safety services from the supplied trading rulebook. Add durable product-session/app context and map it into QMA's existing authority enforcement. Extend QMF Data for typed facts and recipes. This path maximizes reuse and exposes where a genuinely new owner is needed through evidence rather than anticipation.

### Option to assess later: package contribution envelope

If the first proof reveals repeated contribution types, define a versioned package manifest that names definitions, operations, workflows, views, data dependencies, policy capabilities, and deployment requirements. It should coordinate existing owners rather than become a new execution engine or registry. QMA plugins, QMF kinds, QMB experiments, and QMN deployments remain authoritative in their own domains.

### Deferred option: new framework library

Create a new library only if two implemented systems demonstrate stable shared concepts that cannot live coherently in QMF Core/Registry, Data, Risk, or the existing lifecycle owners. Do not create it merely to collect unsettled abstractions.

Before architecture is ratified, Grok should resolve:

- the semantic boundary of a system policy, especially admission, sizing, exits, portfolio state, and evidence;
- what makes results comparable when systems use different risk units or intelligence compositions;
- the identities and ownership of package, installed app, workflow definition, run, deployment, and context revision;
- which app-session facts are authoritative and how host permissions narrow them;
- who owns accounts during transitions and how shared-account conflicts are refused;
- which QMN protections are universal host laws versus supplied system policy;
- the full QML artifact identity/provenance chain and promotion/refusal points.

Grok should verify the code pointers and branch state afresh, use the two-system proof as the acceptance test, and review any newer implementation work before deciding. It should not redo the operator-intent debate, rename the Experimentation Board, reinterpret PM as Product Manager in trading context, universalize Book/BMS/SQS/MIS, treat source inspection as end-to-end proof, or assume JSON Render/MCP Apps settle QMX's authority model.

## Evidence limits

- The implementation worktree was not fetched, switched, rebased, or modified; its 32-commit remote-tracking lag means newer remote code could change some findings.
- The repository's nested worktree/submodule metadata prevented a complete submodule-status inventory because no mapping was present for .worktrees/ui.
- The 54 passing tests cover selected relevant seams only. They do not prove a live broker, always-on node, rendered UI, or the full QML-to-QMN lifecycle.
- Process inspection found no clearly named live QMA or QMN service to exercise. No user-facing implementation was changed, so Reticle UI verification was not applicable.
- External technology findings are candidate assessments from official project sources, not adoption decisions.

## Supporting reports

- INTENT-AND-AUTHORITY-LEDGER.md — transcript chronology, corrections, authority levels, and non-decisions.
- CAPABILITY-AND-COUPLING-MATRIX.md — code-level owner, extension seam, coupling, evidence level, and change classification.
- SCENARIO-TRACES-AND-RISKS.md — end-to-end scenario traces, failure points, and risk register.
- EVIDENCE-MANIFEST.md — revisions, commands, tests, files inspected, external sources, and limitations.

Stop boundary reached: recommendations are recorded, but no repository change, handoff revision, architecture ratification, or implementation has been performed.
