# Workbench expansion — documentation-factory Stage 9 brief (2026-09-14)

Route e, change mode, Stage 9. Architecture already FINAL. Do not restart Stages 1–8. Do not implement code, UI, or Penpot. Operator away: do not coach or pause.

Planning checkout: `codex/plan-qmx-ui-design` at the same tip as `main` `430fb7d`. Implementation inspected via `git show` / `git ls-tree` on `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. Do not switch branches.

## Authority (this increment only)

- `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md` (status: final; local AD-1..AD-16). **FINAL spine wins** over earlier memlog lines (reviewer-gate amendments are already in the spine).
- `CAPABILITY-EXPANSION.md` (companion; not a second spine).
- that folder’s `.memlog.md` and `inputs/` (code-qma/qmb/qml/qmf/qmn, classify-synthesis, donor cuts, reviews).
- `epansion_session` — architecture sitting transcript; house treatment: citation surface is the memlog/spine (SRC-17), transcript registered as SRC-18 for operator-word provenance only.

Generated layouts and reactions to them are **not** preference evidence.

## ID block (disjoint from QMA DEC-0300+ / GAP-0070+ / FEAT-0040+ / CT-40+)

| Kind | Range | Use |
|---|---|---|
| SRC | SRC-17, SRC-18 | architecture folder; epansion_session |
| EXT | EXT-2183..EXT-2212 | extractions |
| DEC | DEC-0269..DEC-0287 | one per AD-1..16, umbrella, wiring reconcile, cheap-veto |
| GAP | GAP-0061, GAP-0062, GAP-0063; GAP-0085 updated in place | PRD hole; AD-10 host machine; generator algorithm; mechanism nouns |
| FEAT | FEAT-0033..FEAT-0039 | connect-wave then generation |
| ADR | ADR-0022 | this increment |
| SCN | SCN-0015, SCN-0016 | three lanes; projection vs path-dependent |
| CT | no new id | annotations + wiring_status reconcile only |
| COMP | none | **no sixth application** |

Local AD-1..AD-16 do **not** renumber QMF AD-*, QMA AD-*, CONNECT AD-*. Cite parents as `QMF AD-n` / `QMA AD-n` / `B-n` / `QL-n` / `TN-n` / `CONNECT AD-n`.

## Preflight verdict (record in ADR-0022)

**reuse** existing application-layer products. **new COMP: none.**

| Work | Owner | Class |
|---|---|---|
| QMA→QMB real CLI transport, persist ExperimentSpec/ledger, compose asyncio daemon | COMP-QMA-DAEMON | connect |
| Named analysis (`analysis.project` / `analysis.rerun`), CLI coverage of robustness/sweep, data commands | COMP-QMB | extend / connect (wiring) |
| Generation authoring of new CT-33/CT-34 + logic | COMP-QML | new function, existing COMP |
| Library kinds / CT-07 | COMP-QMF-REGISTRY | reuse |
| Book/BMS shapes | COMP-QMF-RISK | reuse |
| Data rooms | COMP-QMF-DATA | reuse |
| Node-paper / soak / live; unforked `run_slice` | COMP-QMN | reuse (unchanged money path) |

Candidates refused by id:

- **new COMP-EXP / HTTP experiment service / Project package / Workspace kind** — AD-1, AD-16, DEC-0084 stays dead.
- **second backtest governor / `import qmb` from QMA** — QMA AD-17, AD-8.
- **donor engines** (LEAN, StrategyQuant genetic, RoboQuant RQ Engine) — DEC-0013, DEC-0085/0086, Cut DEC-0376.
- **QMA-paper / any QMA execution tool** — DEC-0341, AD-7.
- **per-bot paper lane on the node** — DEC-0261.
- **UI contribution SDK** — GAP-0081 stays deferred.
- **extending CT-32 or B-4 with `lane` / `analysis_method`** — AD-15.

No existing component’s authority shrinks. No new dependency edge. No new contract id.

## Unresolved — keep as GAPs, never silent prose

1. **GAP-0085** — typed mechanism vocabulary (Entry/Exit/Filter/Session nouns). Ownership is QML/host write path (AD-4 / DEC-0272). Nouns still deferred. QMA already refuses `GAP_0085_STRATEGY_MECHANISMS` in `ports/experiments.py` on integration.
2. **GAP-0063** — first generator algorithm (placeholder-fill of CT-34 legs vs Python-logic synthesis). Ownership AD-4; algorithm unruled.
3. **GAP-0062** — concrete always-on host for AD-10. Property decided (daemon + remote env + outbox; must not live only on the sleeping laptop). Machine is not.
4. **GAP-0061** — PRD FR addenda for ExperimentSpec, analysis methods, generation-vs-search, procedures. Note the hole; **do not rewrite the PRD** this sitting.

## Wiring-status law (DEC-0286)

`wiring_status: defined-unwired` plus “no code exists” is **stale** where matching packages exist on `integration@1b451a8`. Class/test existence is **not** end-to-end demonstration.

New stamp: `source-inspected` — matching source exists on that SHA; composition-root / daemon-process / real-CLI-transport / e2e walk is still connect work, not proven.

Especially: CT-32, CT-33, CT-34, CT-47, and CT-40..CT-51. Also CT-22..CT-31 where `qmf-risk` value types exist (composition-root wiring, not missing shapes).

Independently re-verified this sitting (no checkout):

- `qmb/src/qmb/results` (CT-32 producer path)
- `qml/src/qml/declaration` (CT-33 author types)
- `RecordingQmbDoorTransport` default in `qma/daemon/backtest/service.py` (records, does not spawn `qmb`)
- `GAP_0085_STRATEGY_MECHANISMS` refused in `qma/core/ports/experiments.py`
- no `asyncio.run` / websockets / uvicorn under `qma-daemon`/`qma-wire` `src/` (process composition missing)
- no `robustness` group under `qmb` CLI (library-only)
- `packages/qmf-risk/src/qmf/risk` exists
- `qma-ui-contract` is a stub (GAP-0081)

## Dead list — do not revive

DEC-0084 (central backtest service), DEC-0085/0086 (donor engines), DEC-0376 (git-branch-per-parameter), QMA-paper, `.qml` DSL, complexity gate, paper twins, QuantConnect paper-brokerage as a QMX lane.

## Feature slices (implementation still factory-pipeline-only)

| FEAT | Name | Primary DECs | Blocked by |
|---|---|---|---|
| FEAT-0033 | Connect the QMA→QMB door, persist ExperimentSpec, compose the daemon process; three lanes + paper trinity + notebooks-as-import | DEC-0269, 0270, 0275, 0276, 0279, 0284, 0285 | FEAT-0044, FEAT-0042, FEAT-0029 |
| FEAT-0034 | Library projections + candidate-set queries over fp1 kinds | DEC-0271, 0282 | FEAT-0007, FEAT-0029, FEAT-0045 |
| FEAT-0035 | Named analysis methods (projection saved view vs path-dependent rerun) + Book/BMS complete candidates | DEC-0273, 0274, 0283 | FEAT-0029, FEAT-0027 |
| FEAT-0036 | CLI/API parity for robustness and sweep batch/rank; data commands wrap qmf-data | DEC-0281, 0276 | FEAT-0029 |
| FEAT-0037 | Procedures as QMA Graph Templates / Skills / Routines placing QMB via the door | DEC-0277 | FEAT-0033, FEAT-0046 |
| FEAT-0038 | Continuation host config (AD-10 property); extensibility rungs 1–3 | DEC-0278, 0280 | FEAT-0042, FEAT-0041 |
| FEAT-0039 | QML structure-generation authoring (trails connect-wave) | DEC-0272 | FEAT-0030, FEAT-0007 |

Connect-wave first: 0033–0038. Generation (0039) may trail. Not a required sequence beyond `blocked_by`.

## Drafting rules

- Cite new DECs on every new normative sentence. Self-contained sections. No “as discussed above”. No hedges. No TODO without a GAP id.
- `workbench_lane` is derived from the door, recorded as metadata on the QMB ledger line (`governed` for every orchestrator spawn) and/or Experiment Ledger (`coordinated` when QMA placed it). **Not** a CT-32 field, not AD-12 evidence class, not B-4 role.
- L33 graduation is two-artifact registration, **not** an orchestrator spawn.
- Projection never rescales size/R/Book/ports/`starting_capital`. Path-dependent is a new run. `compare_runs` is readout only.
- Saved-view body **is** the canonical JSON `{method: projection, source_ct32, source_ct29, predicate, as_of}`. Homes: ungoverned return value; governed-without-QMA JSON sidecar in the **source** run-dir; coordinated daemon-persisted + `analysis.published`.
- Occupancy: one `qmb` CLI/MCP **run** invocation per ExecutionEnvironment. Queries (`analysis.project`, `compare_runs`, `sweep.rank`, gap-check/verify/catalog/list) do not consume occupancy.
- QMA never `import qmb`. QMB/QML never import `qmf-venue`.
- Preserve identities, history, graveyard. Dated follow-ups on ADR-0017/0018/0020; do not rewrite those ADRs’ original Decision sections.
- Docs stay `status: ratified` (spine FINAL, same as CONNECT). `verified: 2026-09-14`. Implementation authorization remains factory-pipeline-only.
- Ban: engine/kernel for QMB; bare paper/calendar/plugin (outside QMA)/snapshot for registry state.

## Docs to touch (blast radius)

New: `docs/decisions/ADR-0022-workbench-expansion.md`; `docs/scenarios/SCN-0015-three-experiment-lanes.md`; `docs/scenarios/SCN-0016-projection-vs-path-dependent.md`.

Update: qmb.md, qml.md, qma-daemon.md, qma-core.md, qma-wire.md, qmf-registry.md, qmf-risk.md, qmf-data.md, trading-node.md, overview.md, stack.md, dependencies.yaml, constitution.md, AGENTS.md, glossary.md, gap-report.md, traceability.md, changelog.md, index.md, ADR-0017/0018/0020 dated follow-ups, SCN-0012, contracts CT-22..34 and CT-40..51 wiring comments, lenses that still say “no code exists” for those CTs (test-strategy, fixtures, security, logging, metrics, triage).

## Next skill after this sitting

`bmad-create-epics-and-stories` using `validate_inventory.py --handoff` on FEAT-0033..0039. Do not run that skill here.
