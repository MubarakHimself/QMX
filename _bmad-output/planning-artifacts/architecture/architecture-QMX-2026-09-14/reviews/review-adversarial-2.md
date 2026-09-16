---
review: adversary-2
target: ARCHITECTURE-SPINE.md (amended after review-adversarial.md C-1..C-4, H-1..H-4)
companion: CAPABILITY-EXPANSION.md
date: 2026-09-14
lens: 'Re-attack the amended spine. Check whether C-1..C-4 and H-1..H-4 actually closed. Report only NEW pairs that still obey every AD yet diverge, or reopenings of those old holes.'
---

# Adversary review 2 — amended workbench spine

## Method

Same as `review-adversarial.md`: for each local AD, two units one level down that obey every written Rule (plus inherited parents) and still cannot assemble. Parent spines bind read-only. A local sentence that forces a parent-container fork is a hole.

Scope is the C-1..C-4 / H-1..H-4 paste, plus joints the paste newly opened. Unapplied items from the first review (H-5 owner list, M-1 extra env kind) are out of this pass except where the new text reopens an old hole.

## Verdict

**Return for amendment — remaining-critical-count: 2.** Do not freeze connect-wave What-if, Library, or door-persistence epics.

C-3 (invoke/occupancy/cancel), C-4 (candidate homes / QML mint / no staging), H-1 (two ledgers stay two), H-3 (`compare_runs` readout), and H-4 (`sweep.rank` is the view) hold. C-1 named a kind and forbade size-rescale, but the saved view still has two durable bodies and no legal coordinated shape. C-2 named a stamper, but the stamp extends B-4 (which H-2/AD-15 just forbade) and dual-labels one QMA-placed run `governed` and `coordinated`. Three Highs are new paste defects, not the old holes: Experiment vs successor-ledger cardinality (AD-16 × AD-9), the AD-7 hub sentence blocking the only legal B-15 write, and `branches-from` reused for ExperimentSpec.

| Tier | Count |
| --- | --- |
| Critical (reopened) | 2 |
| High (new) | 3 |
| Medium (new / leftover under amended text) | 2 |

---

## Closures that hold (do not re-litigate)

| Old hole | Why it is closed |
| --- | --- |
| C-1 rescale vs `starting_capital` | AD-5 permitted predicates are a closed filter list; size / R / Book / ports / `starting_capital` are forbidden as projection. |
| C-1 kind = CT-32 sibling | Projection is a saved view, not a CT-32. Path-dependent canonical artifact is the new CT-32. F07 synthetic portfolio refused. |
| C-1 quality-as-analysis | AD-13: quality surfaces are CT-13 / `gap_check` reads, not AD-5 views. |
| C-2 caller-declared `lane` flag | Door-derived only. CT-32 not extended with `lane`. Ungoverned is not a Library object. ExperimentSpec coordinated-only **in AD-2** (undone by AD-13 — see C-2-R). |
| C-3 import / occupancy / cancel | Daemon, plugins, worker images never `import qmb`. One CLI invocation per env; children inside are not extra QMA jobs; data/analysis/robustness CLI consume occupancy. Coordinated cancel = `JobHandle.cancel` only. |
| C-4 CT-33 mint / staging bag | QML/host mints; QMA never assembles CT-33/34 JSON. AD-3 list closed. AD-14 does not read QMA staging. Book/BMS = complete `dev`-zone document, not a patch. |
| H-1 ledger merge / QMB writing ExperimentSpec edges | AD-8: QMB JSONL by `_ref`, never copied, never merged. QMB does not write ExperimentSpec edges. |
| H-2 mapping table (as text) | AD-15 table is total and forbids extending CT-32/B-4. Undone in force by AD-2’s stamp — see C-2-R. |
| H-3 `compare_runs` | Readout, not a method; stamps nothing. F08 overlay vs path-dependent split is named. |
| H-4 `sweep.rank` | AD-14: the view; publishes no copied-row artifact. |
| H-6 paper nouns (body) | Not in the applied set; body still dropped “Book paper-mode evidence” and pinned `world=replay`. Closed as a paper-noun fork. |

Stale illustration (not a conforming pair): Structural Seed mermaid still pipes candidate-set query through `QMA staging`, which AD-14 forbids. Fix the diagram so stories do not copy it. Companion §4 A.5 still says “Stamp `lane` on artifacts” — that would reopen C-2 if an epic follows the companion against AD-2/AD-15.

---

## CRITICAL (reopened)

### C-1-R — AD-5 × AD-14 × AD-2 × AD-9 × QMA AD-6: the saved view is named, still unassemblable

The paste named kind (saved view), identity formula (`fp1` of a JSON), and function owner (COMP-QMB). It did not name a single durable body, a single writer, or a coordinated shape that is not a run.

**Unit A — What-if / QMB results epic.** AD-5: `analysis.project` stores the predicate and cites. AD-14 governed home: QMB run-dir sidecar. Writes the canonical JSON into the **source** run-dir, keyed by `fp1`. Coordinated: “Publishing appends that `fp1`” — the QMB CLI (AD-9 door step, AD-8 occupancy) appends Experiment Ledger and writes a QMB ledger line because AD-2 coordinated evidence is “ledger line and CT-32”. `as_of` is query time, so each publish is a new `fp1`.

**Unit B — What-if / QMA query epic.** AD-5 otherwise-clause: no coordinated experiment ⇒ return value, **no ledger** (ungoverned). Coordinated: “QMA queries may call … and persist refs.” Daemon (QMA AD-6 sole writer, AD-9 lease holder) stores only the `fp1` citation (AD-14 “citing `fp1`”). No sidecar. No QMB ledger line (projection is not a CT-32 — AD-5). No new ExperimentSpec (AD-9 successor only when resolved-config changes). `as_of` is the source CT-32’s occurrence, so the same predicate is stable.

Both obey every local sentence they cite. What diverges:

- **Body.** A persists JSON. B persists a hash of JSON that nobody stored. Tomorrow’s Library hit reconstructs a predicate in A and a dangling `fp1` in B.
- **Writer.** A: QMB process writes QMA sqlite (parent QMA AD-6/AD-9 fork). B: daemon persists refs after the CLI returns (the only parent-legal path). The two AD-5 sentences authorize both.
- **Governed-without-QMA.** A has a sidecar. B has a return value that vanishes. AD-5 never mentions the sidecar; AD-14 does.
- **Coordinated shape.** A is a `qmb` job: occupancy, JobHandle, and AD-2’s “one CT-32” (must mint a dummy CT-32 or a ledger line without one — both forbidden by the other AD). B is a query: no occupancy, no CT-32, no JobHandle. Same Graph Template step deadlocks on A’s occupancy during an in-flight backtest and sails on B.
- **Identity.** `as_of` in the identity JSON is unspecified. A’s query-time `as_of` makes one predicate many fps; B’s source `as_of` makes one.

Kind/owner/rescale are closed. The joint the What-if epic will implement is not.

**Tightened Rule (replace AD-5 publishing + identity `as_of`; replace AD-14 home; carve `analysis.project` out of AD-8 occupancy).**

> The saved-view **body** is the canonical JSON `{method: projection, source_ct32, source_ct29, predicate, as_of}`. `as_of` is the source CT-32’s occurrence / `registry_as_of`, never query time. Identity `fp1` is of that JSON. The durable record **is** that JSON (predicate + cites). A citation without a body is not a saved view. Never a copied trade list or rescaled measure set.
>
> Homes, body stored, keyed by `fp1`: **ungoverned** — return value only, not durable, not a Library object. **governed-without-QMA** — write the JSON as a sidecar in the **source** run-dir (not a new orchestrator spawn, not a ledger line, not a CT-32). **coordinated** — the QMA daemon (lease holder) persists the JSON (artifact store or Experiment Ledger payload) and an `analysis.published` entry citing that `fp1`. QMB never opens daemon sqlite. AD-5 “Publishing appends” is this daemon write, not a QMB write.
>
> `analysis.project` is a QMB library function with thin doors (B-1). It is **not** a run: no CT-32, no QMB ledger line, no ExperimentSpec successor, no `environment_lease`. Coordinated call = daemon shells the CLI as a **query**, waits, persists refs. `analysis.rerun` remains a run (AD-2/AD-8 occupancy, spec successor, new CT-32). Permitted predicates, path-dependent list, `compare_runs`, and F07 refusal stay.

---

### C-2-R — AD-2 × AD-15 × B-4 × QMF AD-12 × AD-13: the stamp law and the mapping table cannot both be built; one QMA-placed run still has two lanes

The paste closed caller-declared flags and “CT-32 is the experiment.” It closed the stamp by writing `lane` onto the QMB ledger line **and** calling it that line’s “evidence class.” H-2/AD-15, applied in the same pass, says do not extend B-4 and leaves QMF AD-12 evidence class (`confirmed|unconfirmed|provisional`) as parent.

**Unit A — QMB orchestrator / results epic.** AD-2 literal: every orchestrator spawn, including those QMA placed, records `lane=governed` on the B-4 JSONL line. That field **is** the line’s evidence class (AD-2 words). Coordinated confirmation therefore carries evidence class `governed`. Library filter `lane=governed` reads the QMB merge view (AD-3 query surface) and includes QMA-placed runs. AD-13 “coordinated/governed ExperimentSpec” authorizes a spec on the governed lane so Library has an identity to hang `lane` on.

**Unit B — QMA door / Library epic.** AD-15 literal: do not extend B-4. `lane` is not a B-4 field. QMF AD-12 evidence class stays `confirmed|unconfirmed|provisional`. Confirmation evidence is B-4 `role=confirmation` only. `lane=coordinated` lives only on the Experiment Ledger. Library filter `lane=coordinated` reads that ledger and is empty against the QMB view. Governed has no ExperimentSpec (AD-2). L33 remains two-artifact mint, not spawn (parent).

Both readings are of adopted Rules. What diverges:

- **Unimplementable pair.** A extends B-4 and overwrites AD-12 evidence class. B omits the AD-2 stamp. No unit obeys both AD-2 and AD-15.
- **One experiment, two lanes.** A’s QMB line says `governed`; B’s Experiment Ledger says `coordinated`. AD-3 lists both as Library query surfaces and does not say which `lane` the UX filter binds. `lane=coordinated` is empty in A and full in B.
- **ExperimentSpec cardinality.** A ships governed specs (AD-13). B does not (AD-2). C-2’s “ExperimentSpec coordinated-only” is reopened by one sentence.
- **Graduation.** A treats `spawn_governed` as L33 (AD-2 cite) and ledgers unregistered Python as governed evidence. B requires QL-8 two-artifact mint before citation. Parent fork, introduced by the C-2 paste.

**Tightened Rule (replace AD-2 stamp/graduation sentences; delete AD-13 “governed ExperimentSpec”; align Conventions “Lanes”).**

> `lane` is derived from the door, never a payload flag, never a CT-32 field, **never a B-4 field**, never QMF AD-12 evidence class. Record it **only** on the QMA Experiment Ledger entry, and only when QMA placed the invocation (`lane=coordinated`). Governed-without-QMA has no `lane` field — the door is the lane. Library filter `lane=coordinated` reads the Experiment Ledger only. The QMB ledger merge is filtered by B-4 `role` / QMF AD-12 evidence class, not by `lane`.
>
> Ungoverned → governed is a B-4 orchestrator spawn. **Not L33.** L33 / QL-8 graduation remains minting CT-33/CT-34 with a lineage edge; citation of governed evidence still requires those artifacts. Drop “(L33)” from AD-2.
>
> AD-13: a coordinated ExperimentSpec `data_ref` must cite CT-12 split fingerprints (B-8). Ungoverned calls may not mint ExperimentSpec. Governed-without-QMA has no ExperimentSpec; split fingerprints already bind via B-8/B-3.
>
> AD-15 mapping table stands. Companion §4 A.5 (“Stamp `lane` on artifacts”) is deleted; doors select lanes.

---

## HIGH (new — paste defects, not the old H-1..H-4)

### N-1 — AD-16 × AD-9 × QMA AD-9: “the Experiment” is still three cardinalities

AD-16 is new in the amendment (F12). It says coordinated continuity **is** the ExperimentSpec `fp1`, while listing identity-bearing refs (`code_ref`, `resolved_config_ref`, …) that parent QMA AD-17 already makes content-addressed — any field change mints a new `fp1`. Local AD-9 then `create_successor`s a new spec per resolved-config door step. QMA AD-9 is one Experiment Ledger **per Experiment**.

**Unit A — Experiment persistence epic.** Experiment = spec `fp1`. Each successor opens a new Experiment Ledger. Continuity is UX grouping of aliases (AD-16 last sentence). Laptop-off query of “this experiment” is one spec’s notebook.

**Unit B — same epic, other reading.** Experiment = the CT-07 predecessor chain (scientist notebook). `create_successor` appends to the **same** ledger. Continuity is the chain; the head spec is a display alias. Laptop-off query returns the whole notebook.

Both obey the local sentences they cite. Door-persistence and procedure epics then ship different sqlite cardinalities, different `_ref` joins, and different AD-10 continuation stories for one Custom-Project run.

**Tightened Rule (replace AD-16 continuity sentence; pin ledger cardinality; stop using `branches-from` — see N-3).**

> An **Experiment** is the predecessor chain of ExperimentSpec `fp1`s sharing one registering Quant and one initial intent. **One Experiment Ledger per Experiment** (QMA AD-9), not per spec `fp1`. `create_successor` mints a new spec `fp1` and appends to that same ledger; it does not open a second ledger. AD-16 continuity **is that chain** (UX may alias the head). There is still no Project / Workspace kind. Notebooks join as `code_ref` or as an ExecutionEnvironment session, not as a fourth identity. Display names “project” / “workspace” are UX aliases over that chain (coordinated) or over a bot `fp1` (governed).

---

### N-2 — AD-7 last sentence closes the only legal hub write and opens only the refused one

Not H-6 (paper nouns are closed). New last sentence of AD-7:

> QMA/QMB never write the node hub-inbox except as sandbox-tainted fragments the node already refuses; ingest is human `hub_publish` of governed artifacts.

**Unit A — research-paper / promotion epic.** Obeys AD-7: QMB never writes hub-inbox except sandbox. TN-3 already refuses `provenance=sandbox` at publish and pull. Governed CT-32 never reaches the published hub. TN-20 has no QMB evidence to pull.

**Unit B — same epic, parent-preserving.** B-15: WriterId fragments **do** enter the passive hub. `hub_publish` is the human act and still refuses sandbox. QMA still never writes the hub. Unit B violates local AD-7 to obey B-15/TN-20.

Neither unit can both promote research-paper and obey every AD. A local AD that forces a parent-container fork is a hole.

**Tightened Rule (replace AD-7 last sentence only; paper nouns stay).**

> QMA never writes the hub (QMA AD-2/AD-28). QMB WriterId fragments may enter `hub-inbox` under B-15. `hub_publish` remains the human act and still refuses `provenance=sandbox`. Promotion pull stays TN-20. research-paper remains QMB `world=replay` governed (or coordinated) replay outside the node; never Book paper-mode, never `world=live`.

---

### N-3 — AD-9 `branches-from` redefines a parent edge kind

The C-3 paste required `create_successor + CT-07 branches-from` for every resolved-config door step. Parent QMF AD-16 / AD-30: `branches-from` is the **template** version graph (Bot/Book/BMS; multiple heads; “current” is a dated pointer). CT-47 already has a content-addressed predecessor / lineage DAG. DEC-0376 cut git-branch-per-parameter; reusing `branches-from` for config successors is that shape without git.

**Unit A — procedures epic.** Writes `branches-from` from ExperimentSpec → ExperimentSpec. A registry query of `branches-from` returns Book versions **and** experiment successors. Two graphs, one type.

**Unit B — parent-preserving procedures epic.** Successor uses CT-47’s existing predecessor language (or a new addable experiment-lineage kind). `branches-from` stays Bot/Book/BMS.

Both obey a written Rule. The C-3 occupancy/cancel close holds; this sentence is the leftover landmine.

**Tightened Rule (replace AD-9 successor sentence).**

> Each coordinated door step that changes resolved-config is `create_successor` of a new ExperimentSpec `fp1` plus a CT-07 **experiment-predecessor** edge (CT-47’s existing predecessor / lineage DAG). Do not write `branches-from` for ExperimentSpec. `branches-from` remains the parent template version graph. The procedure / Mission is not itself an ExperimentSpec.

---

## MEDIUM

### M-1 — AD-13 derived dataset is still “a fingerprinted artifact”

Not in the applied C/H set. The amended sentence (“new fingerprinted artifact with a lineage edge; it is not a Library kind”) still admits two v1 shapes F09–F11 must pick:

**Unit A.** New qmf-data room (existing room machinery, new as-of) + CT-07 to source room(s).

**Unit B.** QMB run-dir sidecar (not a Library kind, not a new store).

Replay that “cites the derived dataset” resolves to different fingerprints. Classify I-13 already pinned the room; the spine did not take it.

**Close (AD-13).** A derived dataset is a new fingerprinted **qmf-data room** with a CT-07 lineage edge to its source room(s). Not a CT-10, not a CT-32, not a QMB sidecar.

### M-2 — `analysis.rerun` vs `spawn_governed` as two doors for one mutation

AD-2 says governed **includes** `analysis.rerun`. AD-5 makes `analysis.rerun` the path-dependent method. AD-15 stamps analysis only if published.

**Unit A.** Any `spawn_governed` that cites a predecessor CT-32 stamps `analysis_method=path-dependent` on the ledger (or publishes `analysis.published`).

**Unit B.** Only the `analysis.rerun` door stamps; a fresh `spawn_governed` with new capital is a new experiment (`role` from the caller).

Same tunnel, two metadata stories, two admission populations if both can be `role=confirmation`. Pin: `analysis.rerun` **is** `spawn_governed` with a required predecessor `_ref`; the analysis publication is the Experiment Ledger entry (coordinated) or omitted (governed-without-QMA). A spawn with no predecessor is not path-dependent analysis.

---

## Pairs that still would not assemble even as cheats

Unchanged from review 1, and the amendment did not reopen them: sixth application; generator inside QMB optimize; QMA execution tool / QMA-paper; `import qmb` from `qma-daemon` or `analysis-backtest`; copied-row databank (given H-4 holds); QDM clone store; node-paper as the pre-promotion lane.

---

## Apply

Editor can paste without the operator.

1. **C-1-R** — AD-5/AD-14: saved-view **body** is the JSON; `as_of` is source occurrence; homes store the body; QMA daemon persists coordinated refs; QMB never writes sqlite; `analysis.project` is a query (no occupancy, no CT-32, no spec successor). `analysis.rerun` stays a run.
2. **C-2-R** — AD-2: `lane` only on Experiment Ledger (`coordinated`); never on B-4; never AD-12 evidence class; drop L33 cite. AD-13: drop “governed ExperimentSpec.” Conventions “Lanes” and companion §4 A.5 follow. AD-15 table stays.
3. **N-1** — AD-16: Experiment = spec chain; one Experiment Ledger per Experiment.
4. **N-2** — AD-7 last sentence: restore B-15 hub write; keep sandbox refuse.
5. **N-3** — AD-9: experiment-predecessor, not `branches-from`.
6. **M-1 / mermaid** — derived dataset = qmf-data room; candidate-set mermaid drops `QMA staging`.

Do not start What-if, Library-filter, or ExperimentSpec-persistence as parallel epics until 1–3 are in the spine; those three epics **are** units A and B of C-1-R, C-2-R, and N-1.
