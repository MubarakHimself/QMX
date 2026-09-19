# Capability and coupling matrix

Evidence revision: planning main b8b4d21a3d6; implementation integration 8510c032496b. “Demonstrated” means this audit observed a composed path or a test that spans the named seam; documentation alone is never classified as a composed run.

## Classification key

- demonstrated: exercised across the named composed seam;
- unit-tested: implementation and isolated tests exist, but the larger lifecycle was not demonstrated;
- needs wiring: pieces exist but the required call path is absent or unproven;
- documented only: described by authority documents but not found in the inspected source;
- extension interface: callers can supply a compatible implementation without editing the interface owner;
- refactor: a compatibility-preserving seam must be extracted or generalized;
- breaking contract: existing serialized/interface meaning changes;
- architecture amendment: a ratified owner/law must change;
- unknown: bounded audit did not establish the claim.

## Matrix

| Capability | Documented owner | Source entry point | Public extension mechanism | Embedded dependency / constraint | Evidence level | Change classification |
|---|---|---|---|---|---|---|
| Exact identity, money, time, refusals | QMF Core | packages/qmf-core/src/qmf/core | Value types and protocols | Closed worlds live/replay/simulated; exact identity rules are invariants, not trading policy | Broad unit coverage; reused by QML/QMB/QMN | Reuse |
| Instrument/venue/account identity | QMF Core | qmf/core/identity.py:235–405 | Construct new VenueId, Instrument and venue-scoped Account values | Account identity includes venue and role; broker name is deployment metadata | Unit-tested; QMN roster consumes it | Reuse |
| Addable registry kinds | QMF Registry | qmf/registry/records.py:671–745 | KindRegistry.register_kind then RegistrationService | Reserved kind names and contracts remain protected; no user-facing package installer was demonstrated | Unit-tested interface, persistence present | Reuse plus wiring for installation |
| Raw source observation/provenance | QMF Data | qmf/data/observation.py:450–690; ingest.py:147–388 | ExternalSourcePort and injected ingest adapter | In the inspected source, SourceObservation is a provenance/timing shell and ProviderRecord is instrument-centric, carrying quote sides or optional money/timestamp; no general typed payload for sector/fundamental/macro/news/sentiment values was found. This is a bounded implementation finding, not a claim that QMF Data is incapable by design | Unit-tested; provider revision and source/venue separation implemented | Candidate extension of existing owner; additive schema/versioning after architecture preflight |
| Historical market-data download | QMB wrapping QMF Data | qmb/data/ports.py:1–123 | ProviderAdapter protocol | Request is quote-shaped: symbol, resolution and bid/ask side | Unit-tested; Dukascopy adapter exists | Reuse for quotes; new adapter plus QMF-data extension for multimodal data |
| Provider revisions and point-in-time facts | QMF Data | qmf/data/ingest.py:147–190; observation.py:466–480 | New revision creates new immutable artifact | No dataset-recipe/builder contract connecting heterogeneous releases was found | Unit-tested primitives, no multi-source composed study demonstrated | Wiring plus additive recipe interface |
| QML governed bot definition | QML; kind owned by QMF Registry | qml/declaration/bot.py:54–184 | CT-33 body plus plain-Python logic and host RecordSink | CT-33 forbids sizing, venue and Book fields; correct separation for bot logic | Unit-tested/source-inspected, not full lifecycle e2e | Reuse |
| QML confluence/composition | QML; kind owned by QMF Registry | qml/declaration/confluence.py:58–220 | CT-34 leg roles and child references | Role vocabulary is level/trigger/confirmation/filter; this is bot semantics, not a general workflow graph | Unit-tested/source-inspected | Reuse for bots; do not stretch into workflow runtime |
| QML Stage 0 research mill | Proposed QML expansion | docs/decisions/ADR-0023:17–25, 43–63; docs/components/qml.md:224 | Proposed qml.research and host blob store | Most decisions provisional; source note says Stage 0 types absent and research-corpus remains an in-memory stub | Documented only/provisional | Architecture review then new package surface and wiring |
| QML validation/graduation | QML | qml/conformance/layer1.py; layer2.py; registration.py | gate_registration and graduate_to_governed | Technical conformance, not performance approval | Unit-tested; no QML→QMB→QMN composed proof | Reuse plus integration proof |
| QMB direct/API/CLI/MCP doors | QMB | qmb/doors, qmb/workbench.py, qmb/orchestrator | Python functions, qmb CLI and MCP render door | Governed/coordinated lanes carry different evidence; no arbitrary workflow contract | Unit-tested; door parity exists | Reuse |
| QMB optimization/search | QMB | qmb/optimize/sampler.py, objective.py, space.py | Declared parameter spaces | Current implementation is Optuna/TPE search, not a genetic structure generator | Unit-tested | Reuse; generation remains QML-owned and GAP-0063 |
| QMB Book/BMS variants | QMB analysis over QMF Risk | qmb/analysis/variants.py:59–1104 | Complete CT-22/CT-27 dev-zone candidates | Only BookDefinition or BmsDefinition is accepted; patches/rescaled trade lists are refused | 54-test audit slice included this file and passed; still not an alternative non-Book system | Reuse for Book/BMS variants; refactor/new interface for other policies |
| QMB run configuration | QMB | qmb/config/compiler.py:114–216, 381–468, 475–648 | Layer fragments and execution-port adapters | book_fp1, bms_fp1, book_fragment_fp1 and bms_fragment_fp1 are mandatory; every run mints CT-28 world=replay binding | Unit-tested, hard coupling confirmed in source | Compatibility-preserving refactor plus architecture amendment |
| QMB execution simulation | QMB | qmb/execution/ports.py:906–1025 | FillPort, SlippagePort, CostPort, FinancingPort | Ports never resize; admission/sizing/exits still go through qmf-risk and Book-resolved R | Unit-tested interface | Existing extension interface for execution fidelity; not a generic risk-policy seam |
| QMB risk/admission | QMB consuming QMF Risk | qmb/execution/risk.py:38–171 | None beyond qmf-risk CT-23 input | Requires ReplayBinding, Book-resolved requested R and CT-23/CT-29 semantics | Unit-tested | Refactor/new policy interface if non-Book systems must compare honestly |
| QMA product Session | QMA Core | qma/core/ontology/records.py:168–180; control/runtime.py:231–285 | Session execution_model and autonomy only | No app instance/version, selected object, allowed operation set, account scope or profile kind; attachment explicitly excluded from durable record | Unit-tested execution session, not app-use/authoring product session | New host/session context contract; architecture amendment |
| QMA agent permissions | QMA Core/Daemon | qma/daemon/capabilities/spawn.py:36–176 | Role base/overlay, mission/parent narrowing, tool tags | Frozen per Agent spawn; skills do not grant authority; good enforcement primitive but not app profile identity | Tested in 54-test audit slice | Reuse and wire to host-granted session profiles |
| QMA context | QMA Core/Daemon | qma/core/ports/context.py:13–25; daemon/context/compiler.py:13–22 | Replaceable per-daemon ContextCompiler | Default compiles EvidenceHandle references only; product selection/app context schema absent | Tested plugin context; app context not demonstrated | Extend existing seam |
| QMA memory | QMA Core/Daemon | qma/core/ports/memory.py:503–550; daemon/memory | MemoryProvider per desk | V1 only NoMemoryProvider; scopes are strings and not an app/session provenance model | Unit-tested protocol/admission; external backend deferred GAP-0072 | Extend binding/scope semantics; no second memory system by default |
| QMA Graph Template/Mission/Task Graph | QMA Core/Daemon | qma/core/control/procedures.py; qma/daemon/taskgraph | Graph Template, Skill, Routine compile to one Mission | Agentic organizational graph; no general typed data ports/cardinality/fan-out/join package contract | Extensive unit tests, no generic workflow e2e | Reuse for agentic procedures; new/general workflow definition seam needed |
| QMA→QMB placement | QMA Daemon/QMB CLI | qma/daemon/backtest/cli.py, service.py | CLI transport behind QmbDoorTransport | QMA cannot import QMB; ExperimentSpec required for coordinated lane | CLI transport tests passed in audit; complete daemon/listener/run chain not demonstrated | Wiring and composed proof |
| QMA execution environments | QMA Core/Daemon | qma/core compute/environment ports; daemon compute router | ExecutionEnvironment and ComputeProvider ports | Remote vendors/GPU inventory/entitlement/image contract not established; concrete always-on host is GAP-0062 | Unit-tested declaration/capacity/placement; no provisioned GPU run | Extend existing owner; explicit capability contract |
| QMA plugin loading | QMA Core/Daemon | qma/core/plugins; qma/daemon/plugins | Manifest/contribution points, migrations, load refusal | Contributions exclude UI view; plugin cannot widen money-path authority | Unit-tested; plugin context test passed | Reuse for agent capabilities, not a mini-app package by itself |
| Mini-app definition/installation | Deferred UI/platform | No implementation found; qma-ui-contract is GAP-0081 | None demonstrated | App definition, installed instance, run and deployment are not first-class separate records | Documented need only | Architecture amendment/new package envelope; reuse existing registries/stores |
| UI contributions/widgets | Deferred UI/platform | No qma-ui-contract implementation found | JSON Render/MCP Apps are external candidates only | Presentation must not become authority/execution/persistence | Not implemented | New contract; no final layout decision |
| QMN hosting/supervision | QMN | qmn/host, deploy, observability, reconcile, secrets | Internal protocols and deployment toolkit | Strong reusable operational behavior exists, but it is interleaved with current rulebook packages | Broad unit/integration-shaped tests; no live operational proof in audit | Extract/deepen hosting interface rather than replace |
| QMN node configuration | QMN | qmn/config/compiler.py:50–132, 349–421 | Fixed roster/bms/book/node_defaults layers | BMS/Book are explicit compile layers; runtime overrides refused | Unit-tested | Refactor plus architecture amendment for generic system packages |
| QMN capital/risk/protection | QMN/QMF Risk | qmn/capital, protection, seats, host/risk_population.py | No complete alternative-policy plugin seam | Book seats, BMS supervision, KSA, kill line, SQS, CT-22/23/27/28 are named across runtime | Unit-tested current system | Compatibility refactor or new interface; retain exact accounting and command safety |
| QMN MIS | QMN | qmn/mis | Current catalog/labeler/shadow modules | MIS is a named current subsystem; alternative or absent intelligence is not a package-level option | Source/tests exist; training/shadow authority still has deferred items | Make optional contribution behind declared system package |
| QMN venue client | QMN over QMF Venue | qmn/venue/port.py:39–191 | VenueClientPort protocol internally | Selector enum is exactly replay/ctrader/conformance. Another cTrader broker/account can reuse configuration; a different production broker technology requires selector/adapter owner changes despite roster comments | Venue selection tests passed; fixed enum proven | Candidate refactor to external adapter discovery/registration |
| Multi-account runtime | QMN/QMF Core | qmn/config/roster.py:129–225, 357–532 | Explicit account-binding roster | One command stream per venue/account; no global default; netting attribution restrictions remain | Unit-tested implementation | Reuse |
| Multiple brokers | QMN/QMF Venue | qmn/config/roster.py plus qmn/venue/port.py | VenueId rows and credential references | Per-broker data is configurable, but adapter kind selection is closed and cTrader is the only production kind inspected | Partially implemented | Wiring for multiple cTrader brokers; refactor for another broker technology |
| Paper/demo/live | QMB/QMF Risk/QMN | qmb/config/replay.py; qmn/paper; qmn/venue | Separate world, account role and environment values | Current node-paper is Book-level demo routing; per-bot lane refused; cannot be relabeled as whole arbitrary system validation without amendment | Unit-tested current semantics | Reuse terms precisely; amendment for complete-system candidate lane |
| Sequential deployment/rollback | QMN deployment and venue reconciliation | qmn/deploy/switch.py, qmn/reconcile, qmn/order/unknown.py | Deployment switch and reconciliation mechanisms | No audited contract for two arbitrary system versions sharing an account and command ownership; software rollback cannot undo fills | Partial/unit-tested current path | Extend with deployment/command ownership state machine |

## Central coupling answer

The hard-coded part is not every QMF library. The hard-coded part is the complete application path:

1. QMB requires Book and BMS identities/fragments and mints a Book binding.
2. QMB risk execution consumes CT-23/CT-29 and Book-resolved R.
3. QMN compiles roster → BMS → Book → node defaults and operates Book seats, BMS/account supervision, KSA/protection/SQS/MIS-specific modules.
4. QMN's production venue selector is a closed enum.

The replaceable parts today include QMF registry kinds, QMF external source adapters, QMB fill/slippage/cost/financing ports, QMA model/memory/knowledge/tool/compute/context providers, QMA plugins and explicit multi-account roster rows. Those are real seams, though several lack installation/discovery and composed-run evidence.

## New library verdict

No new general-purpose framework library is justified by this audit alone. First deepen existing owners:

- QMF Risk (or a QMF-owned sibling contract family) should own a system-policy interface only if two real policy implementations prove one common semantic interface.
- QMB should consume that interface rather than mandatory Book/BMS fields.
- QMN should split reusable host/execution safeguards from the current Book/BMS/KSA/SQS/MIS rulebook.
- QMA should retain agentic procedure ownership; a general authored workflow definition may need a separate QMF-level contract, but not a second scheduler by default.
- QMF Data should be extended for typed multimodal facts and dataset recipes before a duplicate data store is introduced.
