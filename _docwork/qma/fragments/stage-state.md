# stage_state.yaml — QMA increment `change_mode:` entry (draft)

Append the list item below to the existing `change_mode:` list in
`_docwork/stage_state.yaml` (after the 2026-08-21 corpus sign-off entry).
`current_stage` stays `8` and the `ratification` block is untouched — the corpus
is already ratified and every QMA doc ships `status: ratified`. The gate values
below are the QMA increment's expected outcome; the orchestrator confirms them at
the merge-window gate run and edits any that differ.

```yaml
- date: '2026-08-29'
  change: "Absorb the QMA increment — the QMX agentic system (daemon + QMA SDK + wire contract; spine AD-1..AD-29, ratified by delegation under the sitting's I-draft-operator-ratifies mode, SRC-15 ordering the absorption) into docs/"
  sources: [SRC-13, SRC-14, SRC-15]
  provenance: "SRC-13 = architecture-QMA-2026-08-28/ (FINAL spine AD-1..AD-29 + Inherited Invariants + Consistency Conventions + Stack + the Deferred/Cut tables + Vocabulary; .memlog.md ~290 typed entries, later lines supersede earlier, the 2026-08-29 tail recording the validation close verified=true dry=true remaining=0; research/ studies as evidence only; reviews/ six gate lenses + validation-report.md + xref-table.md, critical/high applied). SRC-14 = archive/agentic-spine.txt (the sitting transcript, citation surface for the operator's own words only). SRC-15 = _docwork/qma/riders/job-spec-2026-08-29.md (the operator's verbatim job spec, a direct ruling of 2026-08-29). The deleted workroom/agentic-system-planning folder is NOT an input."
  ledger: "DEC-0300..DEC-0328 minted (ratified, authority rider — one per AD-1..AD-29); DEC-0329 spine-adoption umbrella; DEC-0330..DEC-0350 the 21 ruling decisions; DEC-0360..DEC-0379 minted status: dead for the Cut-outright table; EXT-2300..EXT-2459 extractions; SRC-13/SRC-14/SRC-15 registered; no live DEC superseded"
  gaps: "GAP-0070..GAP-0091 minted status: deferred (blocking false, answer null, each carrying its spine revisit condition); the Cut-outright table is spine law and nothing on it is revived"
  adr: "ADR-0020 written (new); preflight verdict: NEW COMP-QMA-CORE / COMP-QMA-WIRE / COMP-QMA-DAEMON — candidates refused by id (qmf-core = definitions-only L13, no runtime; qmf-registry = records never orchestration; QMB = experimentation host never an agent runtime; QML = bot authoring; the node = money path, AD-28 barrier); dead list honored (DEC-0084/0085/0086 stay dead; DEC-0360..0379 minted dead)"
  contracts: "CT-40..CT-51 minted defined-unwired (no code exists): wire envelope, hook event/result, plugin manifest/context, memory provider, knowledge source, model deployment/broker, execution environment/job, experiment spec, mailbox envelope, routine, refinement proposal, task ledger entry; CT-35..CT-39 deliberately left free for the trading-node increment; no QMF contract changes meaning"
  components: "COMP-QMA-CORE / COMP-QMA-WIRE / COMP-QMA-DAEMON minted in dependencies.yaml (all layer backend; qma-core depends_on qmf-core only; qma-wire depends_on qma-core + qmf-core; qma-daemon depends_on the QMF roster with qmf-registry/qmf-risk read-and-calculate over a default-deny enumerated surface and NO qmf-venue edge; nothing imports a QMA package upward)"
  registry: "variables.yaml gains the AD-26 configurable-variables registry (configurable: true <-> ui-editable, false <-> uneditable); stack.md gains the QMA application stack section (one Python 3.14 asyncio runtime and its pins, with the [UNPINNED] JSON-Schema validator row stated)"
  features: "FEAT-0040..FEAT-0046 minted (multi-pass, status planned) in the operator's build order: qma-core, qma-wire, qma-daemon substrate, model proxy + Tool Registry + reachability barrier (the first-milestone landing), execution environments + Compute Router + RLM kernel + the QMB door, ledgers/bus/scheduler/memory+knowledge/telemetry, plugin loader + the five desk packs"
  orchestration: "wave-1 harvest (ledger-L1..L5 + extractions + gaps-L5 + veto-register + transcript-scan), wave-2 disjoint bulk-worker drafting over staged docs and fragments, wave-3 overlay gate rehearsal, wave-4 two fresh reviews + fixes"
  status: complete
  gates:
    validate_ledger: pass
    validate_registry: pass
    validate_inventory: pass (pre-existing house-accepted warnings only)
    check_citations: pass (house-accepted dead-DEC frontmatter class; DEC-0360..0379 join it)
    lint_docs: clean
    lint_docs_strict: "clean (the corpus is post-sign-off; every QMA doc ships status ratified)"
  review: "two fresh reviews (ledger-grounded consistency + spine-fidelity) with all critical/major findings fixed in the staged sources"
  operator_flags: "The cheap-veto register is surfaced in the changelog row for one-line overturn: eleven assumption/inference calls (five operator-flagged — account pooling, the loopback-unauthenticated proxy default true, the planned-not-provisioned Windows VPS, the word plugin, the desk-level lead flag) plus the 22 Deferred rows GAP-0070..GAP-0091. Nothing in the docs grants implementation, credential, order, promotion, live-money or destructive authority."
  id_block_note: "Ids were block-reserved from DEC-0300 / EXT-2300 / GAP-0070 / FEAT-0040 / CT-40 to keep the QMA numbering disjoint from the trading-node increment's DEC-0186.. and CT-35..CT-39 ranges; CT-35..CT-39 are left free for the trading-node increment, and DEC-0351..0359, DEC-0380..0399 and CT-35..CT-39 stay unused by QMA"
  remaining: "GAP-0070..GAP-0091 deferred with their revisit conditions; the UI and its extension SDK, contribution points and packaging are deferred (GAP-0081) while the wire contract (AD-5) and the variables registry (AD-26) bind now; the QMA epics follow the operator's build order (daemon, data layer, wire, DevOps first; a Quant reachable through models over the wire the first milestone), and implementation ships only through the factory lanes"
```
