# Framework probe — QMF/QML/QMB/QMN

Date: 2026-09-17. Scope: bounded, read-only audit from main worktree `b8b4d21`; implementation evidence inspected in `.worktrees/integration-inspect` at `8510c03` (branch mismatch/behind origin as instructed). No source files were modified.

## Executive findings

| Area | Finding | Classification | Evidence |
|---|---|---|---|
| Layering | QMF is the contract/toolbox layer; QMB, QML and QMN are application-layer products built on it. QMN is the supervised composition root and sole sanctioned `qmf-venue` importer; QMB/QML retain the venue ban. | demonstrated composed run (documentation); needs wiring for full runtime | `docs/architecture/dependencies.yaml:100-210`; `docs/components/qml.md:17-25`; `docs/components/trading-node.md:1-35` |
| QML→QMB→validation→QMN | QML authors CT-33/CT-34 and pure runtime/conformance surfaces; QML Layer-1 validates references, footprint union, parameters and exit intents; QMB hosts bots/run loop and resolves Book/risk execution; QMN hosts seats/bindings and runs the protection/venue path. The intended chain is explicit, but no single end-to-end test proves all four products together. | needs wiring / source-inspected | `qml/src/qml/declaration/bot.py:126-184`; `qml/src/qml/conformance/layer1.py:1-55`; `docs/components/qml.md:38-46`; `docs/components/trading-node.md:545`; `docs/contracts/ct-33-bot-definition.yaml:81`; `docs/contracts/ct-34-confluence.yaml:6-10` |
| CT-33 identity | Bot declaration has exactly six semantic groups; canonical assignment is derived, sizing/venue/Book fields are forbidden, and host composition root stamps CT-06. | extension interface | `qml/src/qml/declaration/bot.py:54-90,126-184`; `docs/components/qml.md:58-62` |
| CT-34 composition | Confluence is reusable registry artifact; legs are any non-empty role mix, producer binding and/or child cite, with Python owning WHEN semantics. | extension interface | `qml/src/qml/declaration/confluence.py:1-9,58-70,183-220`; `docs/contracts/ct-34-confluence.yaml:24-35` |
| Validation | Layer-1 checks are explicit and typed; Layer-2 is a pure sandbox/conformance contract. Tests exist for both layers, but docs state `source-inspected` is not e2e. | unit-tested only / source-inspected | `qml/tests/test_layer1.py`, `qml/tests/test_layer2.py`, `qml/tests/test_prediction.py`; `docs/contracts/ct-33-bot-definition.yaml:81`; `docs/contracts/ct-34-confluence.yaml:9` |
| Book/BMS/SQS/MIS coupling | Book owns binding-facing charter, requested-R sizing, exits and paper evidence state; one BMS supervises many Books. SQS is a configured block-only producer. MIS training/shadow rollout is explicitly deferred; no authority path should be inferred. | documented not found / needs wiring | `docs/components/qmf-risk.md:1-120`; `docs/contracts/ct-22-book-charter.yaml`; `docs/contracts/ct-23-risk-evaluation.yaml`; `docs/components/trading-node.md:541`; `docs/gap-report.md` GAP-0051 |
| Replaceable defaults | Default-deny and injected ports are the intended replacement seam: QMB execution exposes fill/slippage/cost/financing ports; QMA separately defines provider/environment ports. Defaults may be replaced only at composition roots and fingerprints include relevant port composition. | extension interface / compatibility refactor | `qmb/src/qmb/execution/ports.py:85-159`; `qmb/src/qmb/execution/fill.py:1-12`; `docs/components/qma-core.md:59-61`; `docs/components/qml.md:58` |
| Risk/sizing/intelligence alternatives | Risk sizing is units-only and value-free; B split separates bench count from R allowance. CT-34 permits arbitrary role mixes and nested confluences, while logic remains plain Python. This supports alternative risk/sizing/intelligence compositions without changing QMF contracts, subject to Book resolution and conformance. | compatibility refactor / extension interface | `packages/qmf-risk/src/qmf/risk/sizing.py:1-34,63-105,140-176`; `qml/src/qml/declaration/confluence.py:24-35`; `docs/contracts/ct-33-bot-definition.yaml:63-78` |
| Data/provider/broker/account/execution separation | Identity separates venue/account/instrument; broker is deployment configuration. QMB execution is venue-neutral; QMN receives VenueClientPort and owns adapter construction. QMA provider ports (MemoryProvider, ModelDeployment, ExecutionEnvironment, etc.) are separate from money-path venue wiring. | demonstrated composed run (design); extension interface | `docs/contracts/ct-03-instrument-identity.yaml:11-24`; `docs/architecture/dependencies.yaml:183-210,307-371`; `docs/components/qma-core.md:23-37,59-73` |
| Paper/demo/rollout | Three distinct meanings are retained: Book-level Paper mode, venue demo account, and QMN product mode `paper|live`. Node has no per-bot warm-up; promotion is human and activation is a second act. Soak/observability and MIS rollout are not interchangeable. | documented not found for unified rollout; architecture amendment if conflated | `docs/AGENTS.md` (paper vocabulary and no-warm-up rules); `docs/components/trading-node.md:541-545`; `docs/scenarios/SCN-0006-book-paper-transition.md`; `docs/gap-report.md` GAP-0051/GAP-0057 |

## Wiring and test inventory

Integration source exists for QML (`qml/src/qml/declaration`, `conformance`, `protocol`, `host`) and QMB (`qmb/src/qmb/runloop`, `execution`, `registryread`, `host`). Relevant tests include `qml/tests/test_bot_definition.py`, `test_confluence.py`, `test_layer1.py`, `test_layer2.py`, `test_conformant_bot.py`, `test_generation_ownership.py`, and QMB `qmb/tests/test_execution_composition.py`, `test_execution_ports.py`, `test_ql7_host.py`, `test_replay_binding.py`, `test_analysis_book_bms_variants.py`, `test_paper_trinity.py`. QMN has broad unit/integration-shaped tests (`qmn/tests/test_qmn_risk_admission.py`, `test_qmn_runtime_risk_gate.py`, `test_qmn_venue_selection.py`, `test_qmn_paper.py`, `test_qmn_promotion.py`, `test_qmn_readback.py`), but the canonical contracts themselves record `wiring_status: source-inspected`, not demonstrated end-to-end.

The QMB execution implementation explicitly derives world from provenance and keeps optimistic fill taint while GAP-0048 remains open: `qmb/src/qmb/execution/ports.py:175-195` and `:93-104`. Risk sizing validates shape only; runtime Book-state evaluation belongs to QMN: `packages/qmf-risk/src/qmf/risk/sizing.py:30-34,95-105`. This is an important seam: replacing a fill/sizing/intelligence implementation must preserve the port identity, provenance/world law, exact units and Book-resolved authority.

## Exact commands run

```text
Get-Content -Raw docs/AGENTS.md
rg --files | Select-Object -First 200
rg -n -i "QML|QMB|QMN|Book|BMS|SQS|MIS|validation|composition|provider|broker|account|execution|risk|sizing|intelligen|registry|extension|interface|paper|demo|rollout" docs/components docs/contracts docs/architecture/overview.md docs/architecture/dependencies.yaml docs/scenarios
rg --files .worktrees/integration-inspect | rg '(qml|qmb|qmf-risk|qmf-registry)'
Get-Content with line numbering for the cited QML, QMB, QMF-risk and dependency files
Get-Content for the cited component and contract specifications
```

## Limitations

- Read-only audit only; no tests, live/demo connectivity, browser/UI verification, fetch, branch switch, or unsafe command was run.
- Main documentation is at `b8b4d21`; implementation evidence is from integration `8510c03`, so findings marked branch mismatch/source-inspected require re-check against the authoritative implementation branch.
- No unified QML→QMB→QMN process/composition test was demonstrated in this bounded pass. Documentation claims and unit tests are not promoted to an end-to-end claim.
- MIS model/training/shadow-rollout implementation was not found in the inspected paths; the docs classify it as a deferred gap, not an absent requirement.
