# Pass 2 verification-gap audit

Audit target: candidate architecture in `pass2-candidate/`; implementation pinned at `C:/Users/Mubarak/Desktop/QMX-worktrees/epic-051-skylos-mill-split` (`270e992995c2378ca63cf6343254ef8140a8c97e`). This is a read-only source audit. I read the relevant tests before assessing claims; no broad suite or mutation testing was run.

## Executive result

The candidate is directionally honest about the largest gaps, and its proposed ownership is mostly consistent with the repository's existing package boundaries. The strongest current support is QML mill/stage-0 persistence and graduation, QMF data/risk surfaces, QMB's Book/BMS-gated doors, and QMN's closed venue selector. The largest unverified or refuted reuse claims are: QMA `TaskGraphStore` is only an in-memory projection; it has no sqlite lifecycle and dispatch does not walk successor edges; topology validation rejects only direct reverse edges, not self-loops or longer cycles; the daemon listener accepts/drains bytes but does not dispatch wire commands; product-session and capability-descriptor contracts are design-only; and the proposed third `ContributionHit` is not present (the implementation intentionally freezes the union at KnowledgeHit | ArtifactHit).

## Evidence-first test read

- QMA taskgraph tests (`qma-daemon/tests/test_taskgraph_execution_model.py`, `test_taskgraph_mission_compiler.py`, `test_taskgraph_closed_state.py`) cover state transitions, leases, compiler boundaries, and direct back-edge cases. They do not prove sqlite persistence, restart recovery, successor walking, or a longer-cycle/self-loop refusal. `test_daemon_experiment_spec.py` and `test_experiment_spec_persistence.py` prove CT-07 ExperimentSpec lineage, which the candidate explicitly says is not workflow control flow.
- QMA wire tests (`qma-wire/tests/test_federated_discovery.py`, `test_wire_listener_outbox.py`, `test_host_request_bridge.py`) prove DTO/schema validation, framing/outbox, and request vocabulary. They do not prove a live daemon command-to-owner dispatch path.
- QML tests (`qml/tests/test_mill_graduation.py`, `test_research_collapse.py`, `test_legal_entries.py`, Stage-0 tests) are meaningful unit/contract coverage and support the candidate's “reuse existing mill/store” claim. They do not prove a QML→QMB→QMN end-to-end run.
- QMB/QMN tests are extensive but mostly door/package tests. They prove Book/BMS fields and refusal behavior, risk/venue invariants, and replay/conformance paths; they do not prove the proposed AD-3 descriptor facade, product sessions, graph-template execution, or a cross-component workflow.
- The candidate's `RECON-RETURN.md` correctly records that QMA selected tests were blocked by the invalid/missing `qmx-agents/.venv` Python executable. Therefore any statement that the whole QMA suite is green at `270e992` is false-green if repeated from historical audit notes.

## QMA: claimed owners and nearest consumers

| Claim | Current evidence | Verification status / gap |
|---|---|---|
| Reuse `qma.daemon.taskgraph` / `TaskGraphStore` | `qma-daemon/src/qma/daemon/taskgraph/dispatcher.py:118` defines `TaskGraphStore` as an in-memory dataclass of dicts/sets. `TaskGraphDispatcher` consumes it at `:252+`; `hooks/controls.py` imports it as the nearest non-taskgraph consumer. | **Supported owner, refuted durability claim.** No sqlite writer, migration, restore, or journal projection is wired for this store. Later test: materialize → restart daemon → recover graph, edges, leases, and job evidence through the sole sqlite writer. |
| Persist `task_graph_state` and walk edge successors | `taskgraph/records.py` carries frozen `edges`; `dispatcher.py` selects `graph.ready_tasks()` and dispatches a task, but no successor traversal/persistence consumer exists. `taskgraph/procedures.py` and `experiments/service.py` use successors for ExperimentSpec lineage only. | **Missing adoption.** Do not conflate CT-07 lineage (covered by `test_experiment_spec_persistence.py`) with graph control flow. Later test: A→B completion schedules B, mapping is applied, join/conditional semantics are deterministic, and restart preserves the projection. |
| DAG topology validator | `taskgraph/execution.py:172` `validate_graph_template_topology` checks endpoints and `(dst,src) in forward`; `test_taskgraph_execution_model.py` exercises direct reverse-edge refusal. | **Refuted as full DAG law.** A→B→C→A and A→A pass. Candidate correctly identifies this. Later tests should cover self-loop, 3-cycle, disconnected DAG, duplicate edge, and compiler/registration parity. |
| Plugin graph-template topology | `taskgraph/compiler.py` calls the validator and rejects daemon-owned templates; plugin loader's DFS is for plugin `requires`, not graph edges. | **Partial reuse only.** The candidate must not claim the existing plugin DFS already validates template topology until the graph validator is replaced/covered. |
| QMA wire/session/command bus | `qma-wire` has schemas, vocabulary, listener/outbox, federated DTOs, and host-request bridge. `qma-daemon/src/qma/daemon/process.py` owns the listener, but `_handle_client` only reads/drains framed bytes and closes/acknowledges; no owner dispatch is present. | **Vocabulary exists; runtime adoption missing.** Product-session commands/queries, grant intersection, and `psess:` durability are not present. Later test: authenticated command reaches exactly one owner, refusal is typed, idempotency/context revision are durable, and reconnect/replay is safe. |
| Plugin/tool grants and published contributions | First-party plugin manifests/daemon modules exist (`plugins/analysis-backtest`, `research-corpus`, `pm-coordination`, etc.); capability narrowing and plugin loader tests exist. | **Partial support.** This proves plugin loading/permission boundaries, not the candidate's AD-3 descriptor registry or `published_contributions()` ContributionHit production. Later test: manifest request → host grant → product-session intersection → healthy published operation; missing dependency yields typed unavailability. |
| ContributionHit third rail | `qma-wire/src/qma/wire/federated_discovery.py` explicitly declares `FEDERATED_HIT_CLASSES = {knowledge, artifact}`, `FederatedHit = KnowledgeHit | ArtifactHit`, and refuses `qml_candidate`/`strats`; `qma-wire/tests/test_federated_discovery.py` asserts those refusals. | **Directly refuted in current code; candidate labels it a named amendment.** Adding it later requires wire schema, parser, discovery producer, pin identity, and tests; it is not reuse already present. |

## QMF / QMB

- QMF registry/data/risk ownership is real and consumed broadly. `qmf-data` tests cover room/store engines, ingestion, CT-10/15, splits, backup, and failure behavior; `qmf-risk` tests cover templates, admission, sizing, exits, paper, control windows/actions, and performance. QMB tests import these surfaces directly, so the candidate's “QMF toolbox, QMB doors” ownership is supported.
- QMB's nearest consumers are its door/CLI/analysis modules and tests such as `qmb/tests/test_analysis_project.py`, `test_analysis_compare_runs.py`, `test_walk_forward.py`, and `test_workbench_lanes.py`. These construct `ResolvedRunConfig` with non-null `book_fp1` and `bms_fp1`; the candidate's claim that full-run configuration remains Book/BMS-gated is supported. This is not evidence for an alternative non-Book live path.
- QMB CLI/config/experiment machinery exists, but the candidate's shared AD-3 operation descriptor and recipe contract are not implemented as a cross-door registry. `qma-daemon/tests/test_qmb_cli_transport.py` proves a bounded bridge, not parity of every future operation. Later test: descriptor validation and identical semantics through QMB CLI, library, node, and copilot doors.
- No evidence was found that a new “data recipe” persisted as a QMF registry kind; current data lineage and CT-07/room contracts remain the nearest consumers. This supports the candidate's “recipe is not a Library kind” constraint.

## QML mill and graduation

- `qml/src/qml/research/stage0.py`, `vocab.py`, projection/collapse modules, and `qml/src/qml/host/research_store.py` are implemented at the pinned revision. The Stage-0 tests and 32-test mill slice support reuse; do not rebuild these types.
- `qml/conformance` exports `graduate_mill_to_governed`; `test_mill_graduation.py`, `test_research_collapse.py`, and `test_legal_entries.py` exercise accepted/refused graduation and legal entries. This proves lineage/validation behavior, not compilation into a QMB bot or seating in QMN. The candidate's “partial” graduation status is accurate.
- Nearest missing consumer: no tested QML graduation output is passed through QMB compile and then QMN host/seat. Later test should use a real governed artifact and assert provenance, refusal of incomplete/looped entries, QMB compile, and QMN admission without synthetic Book/BMS placeholders.

## QMN venue and command ownership

- `qmn/src/qmn/venue/port.py:39` defines closed `VenueClientKind`; `select_venue_client` is exported by `qmn.venue` and covered by `test_qmn_conformance.py`, `test_qmn_connect_session.py`, `test_qmn_fx_paper.py`, replay/live tests, and the `mt5` refusal assertion. This supports the candidate's QMN ownership and the “new protocol means new kind, not account row” boundary.
- QMN order/venue modules import QMF risk and venue contracts; `qmn/tests/test_qmn_powers.py` scans for forbidden direct dependencies in protected paths. This is a real command/risk boundary, but it is not evidence that QMA owns venue dispatch; the candidate correctly keeps QMA venue-free.
- QMN tests prove paper/replay/conformance and safety gates, not an external live broker/demo or the proposed alternative-system path. Keep live non-Book trading deferred and require an operator-accepted end-to-end test before changing that status.

## False-green and adoption cautions

1. Source-inspection tests and package unit tests can make architecture appear integrated. In particular, the presence of `edges` in immutable `TaskGraph` records does not mean edges are durable or walked; ExperimentSpec successor tests are a different lineage feature.
2. The QMA package has a large test inventory, but the pinned environment is blocked as recorded in `RECON-RETURN.md`; do not report QMA green. The 32 QML tests and 5 QMN conformance tests reported there are bounded evidence only.
3. Wire DTO tests currently lock the two-class discovery union. Treat the candidate's ContributionHit as proposed amendment, not current capability.
4. Plugin manifests and permission tests demonstrate loading and narrowing, not a complete host-grant/product-session lifecycle.

## Recommended later verification gate

Run bounded, newly written tests in this order: (a) DAG self-loop/long-cycle plus successor dispatch; (b) task-graph sqlite restart/backup/restore; (c) live wire command dispatch and product-session grant intersection; (d) ContributionHit producer/schema/pinning; (e) one QML graduation → QMB compile → QMN paper/conformance journey; (f) alternative Book/BMS refusal and no-dummy checks. Keep the existing QMF/QMB/QMN package suites as regression gates, but do not treat them as proof of cross-component workflow integration.
