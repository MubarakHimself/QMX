# Reviewer gate — LENS: parent / sibling consistency

**Subject:** `architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md` (local AD-1..AD-16)
**Against:** QMF AD-1..AD-41; QMB B-1..B-15; QML QL-1..QL-10; NODE TN-1..TN-25 + DEC-0261; QMA AD-1..AD-29 + DEC-0341 + DEC-0376; CONNECT AD-1..AD-5; constitution L7–L11, L17, L30–L36, L39; `docs/AGENTS.md` hard rules.
**Question this lens answers:** does a local AD contradict or weaken an inherited one? A local AD that does so is a conflict to surface, never an override.
**Date:** 2026-09-14. Reviewer: parent-consistency seat.

**Verdict: FAIL-with-amendments.** The sitting’s posture is the right one (inherited table, “consume never redefine,” DEC-0084 stays dead, no sixth application). Most local rules compose over existing doors. Five local sentences still contradict or weaken a parent; none require re-opening a ruling; all are amendments at this desk.

**What this lens found GOOD, so the amendment pass does not undo it:**

- Paper *nouns* in AD-7 (body) now split correctly: research-paper = QMB `world=replay`; node-paper = AD-35/TN-9/CONNECT `role=demo`, `world=live`; QMA-paper does not exist (QMA AD-16/AD-28, DEC-0341). The old “Book paper-mode evidence” parenthetical is gone.
- AD-4 write-ownership is QML/host; QMA never assembles CT-33/CT-34 JSON — QMA AD-14 / GAP-0085 “revisit at the QML sitting” honored without minting the mechanism nouns.
- AD-5 projection is a saved view, not a CT-32; size/R/Book/ports/`starting_capital` are forbidden as projection — B-10 one-canonical-artifact held.
- AD-6 `money_path_relevant` + field-level diff + unset stays unset — QMA AD-14 verbatim.
- AD-8 QMB ledger reached by `_ref`, never copied or merged — QMA AD-6; one `qmb` invocation per env — QMA AD-17; `never import qmb` — QMA AD-2 diagram.
- AD-10 continuation on `qma-daemon` + outbox, QMB lifetime = the job — B-5 no QMB daemon; QMA AD-5/AD-29 close-client / unattended.
- AD-11 notebooks `import qmb` on a B-9 host; managed lifecycle is QMA RLM kernel — DEC-0346.
- AD-12 rung 4 stays GAP-0081; `plugin` stays QMA-scoped — AGENTS hard rule.
- Unforked `run_slice`; QMN never QMA; human promote outside QMA onto the node — TN-5, TN-17, TN-20, L17.
- GAP-0048/0049, GAP-0016/0017 *gate*, GAP-0081 remain deferred on parent revisit conditions.

---

## Findings (most severe first)

### F1 — HIGH — AD-2 cites L33 for an orchestrator spawn, and records `lane` as that line’s “evidence class”

**Where:** local AD-2 rule; Consistency Conventions “Lanes” row. Related slip: AD-13 “coordinated/governed ExperimentSpec”.

**Parent sentences:**
- L33: *“a working plain-Python experiment enters governed evidence only by graduating through the extension shape — a separate versioned package, explicitly registered at the composition root — with a lineage edge back to the originating research artifact.”*
- QL-8: *“Ungoverned bots keep full tunnel access (B-4 ledger lines, the research door): conformance gates evidence **citation** and **seats**, never tunnel entry.”* Graduation is *“minting the two artifacts with a lineage edge.”*
- QMF AD-12: evidence class is *“confirmed / unconfirmed / provisional.”*
- B-4 ledger line already carries the AD-12 result label **and** a discriminated run role (`confirmation | trial | replicate | aborted`).
- Local AD-15: *“do not extend CT-32 or B-4.”*

**Spine sentences:** AD-2 — *“Graduation to governed evidence is an explicit later orchestrator spawn (L33).”* *“`lane` is derived from the door and is recorded only on the QMB ledger line (`governed` for every orchestrator spawn, including those QMA placed — it names that line’s **evidence class**).”* Conventions: *“Artifact metadata includes `lane` ∈ `{ungoverned, governed, coordinated}`.”* AD-13: *“A coordinated/governed ExperimentSpec `data_ref` must cite CT-12 split fingerprints.”* while AD-2 says governed has **no** ExperimentSpec.

**What:** three inherited collisions in one lane rule.
1. An orchestrator spawn is B-4’s impure door, not L33. L33/QL-8 graduation is the two-artifact registration. Treating spawn as L33 lets unregistered Python wear “graduated governed evidence” without the extension shape, and it mis-labels the QL-8 tunnel-open path as the citation path.
2. Calling `lane` the ledger line’s **evidence class** overwrites AD-12’s closed class with `{ungoverned, governed, coordinated}`. Recording `lane` on the B-4 line is a QMB ledger format mint that local AD-15 just forbade.
3. AD-13’s “governed ExperimentSpec” reopens ExperimentSpec on the governed lane, which QMA AD-17/CT-47 ties to the CT-47 door only.

**Why it matters:** implementers will either extend the B-4 JSONL schema (silent parent mint) or skip QML registration because AD-2 told them spawn *is* L33. Admission citation then rests on the wrong artifact.

**Fix:** drop the L33 cite from spawn. Say: ungoverned = B-4 values, no ledger; governed = orchestrator ledger line (QL-8: citation still requires the two artifacts); L33/QL-8 graduation remains minting CT-33/CT-34 + lineage. Record `lane` only on the QMA Experiment Ledger entry for coordinated placements — never on the QMB ledger line, never as AD-12 evidence class. Delete “governed ExperimentSpec” from AD-13 (split fingerprints already bind every governed run via B-8/B-3). Align the Conventions “Lanes” row with AD-15 (“do not extend B-4”).

---

### F2 — HIGH — AD-7 last sentence closes the only legal hub write path and opens only the refused one

**Where:** local AD-7, final sentence.

**Parent sentences:**
- B-15: registry as-of sets and WriterId-scoped ledger fragments reach the **passive file-sync hub**; *“dumb storage, not an always-on service (DEC-0084 stands).”*
- TN-3: two inbound crossings — sandbox fragments into `/var/lib/qmx/hub-inbox`; click-gated promotion pull from the **published** area. Inbox→published is the operator `hub_publish` power, which **refuses `provenance = sandbox` at publish and at pull.**
- TN-20: promotion presupposes **reviewed QMB backtest evidence** on the card; the crossing is a node-initiated pull of the registry as-of set from the hub’s published area.

**Spine sentence:** *“QMA/QMB never write the node hub-inbox except as sandbox-tainted fragments the node already refuses; ingest is human `hub_publish` of governed artifacts.”*

**What:** the exception is the path TN-3 already refuses (`provenance = sandbox`). The path B-15/TN-20 need — non-sandbox WriterId fragments / as-of sets that `hub_publish` may accept — is forbidden by “QMA/QMB never write the node hub-inbox.”

**Why it matters:** research-paper (the same AD’s `world=replay` governed replay) cannot reach the published hub, so TN-20 has no QMB evidence to pull. Or an implementer “fixes” it by letting sandbox fragments publish, which is the exact merge TN-3/TN-20 exist to block.

**Fix:** replace the sentence with: QMA never writes the hub (QMA AD-2/AD-28, no edge to the node). QMB WriterId fragments may enter `hub-inbox` under B-15. `hub_publish` remains the human act and still refuses `provenance = sandbox`. Promotion pull stays TN-20.

---

### F3 — HIGH — AD-1’s legal-store pair omits the inherited QMA store the rest of this spine uses

**Where:** local AD-1 rule. Touches AD-8, AD-14, Stack.

**Parent sentences:**
- QMA AD-6: *“A store not on this list may not be created.”* Closed list includes the event journal, three ledger stores (Task / Quant / **Experiment**), artifact store, staging, telemetry, sqlite behind `qmf-data` sinks. *“External stores that legitimately live elsewhere (QMB’s run ledger) are reached by `_ref` and never merged in.”*
- QMA AD-9: Experiment Ledger is a daemon store, one per Experiment.

**Spine sentences:** AD-1 — *“Minting … or a store beside `qmf-registry`/`qmf-data` is a spine amendment.”* AD-8 — persist ExperimentSpec and the Experiment Ledger through the **daemon journal / sqlite writer**. Stack — *“QMA daemon store | SQLite … inherited QMA AD-6/AD-27.”* AD-14 — saved-view home includes the Experiment Ledger (not `qmf-registry`).

**What:** AD-1 states a closed pair that would make the inherited QMA Experiment Ledger (and AD-8’s connect work) a spine amendment. That is a local AD weakening QMA AD-6, not a restatement of DEC-0084.

**Why it matters:** preflight will either reject daemon persistence as “a store beside qmf-data” or park ExperimentSpec in `qmf-registry`, minting the second identity store AD-1’s **Prevents** clause names.

**Fix:** name the closed owners: `qmf-registry`, `qmf-data` rooms, QMB run-dir/ledger JSONL (B-4/B-15), and the QMA AD-6 list. Minting anything *else* is the amendment. Keep DEC-0084 dead (no central backtest *service*).

---

### F4 — MEDIUM — AD-5/AD-9 silently amend parent contracts (Experiment Ledger writer, B-3 seed, `branches-from`)

**Where:** local AD-5 publishing clause and path-dependent `starting_capital`; local AD-9 successor clause.

**Parent sentences:**
- QMA AD-6 sole writer: only the daemon writes the journal / sqlite / artifact store; QMB ledger is external, `_ref` only.
- QMA AD-9: Experiment Ledger appends only through `before_ledger_append` by the Agent holding the registering Task’s `dispatch_lease`.
- B-3: *“a flag override of the seed stamps `seed_overridden` on the binding and forces the B-4 fold to `unrated`.”*
- AD-16/AD-30: `branches-from` is the **template** version graph (multiple heads; “current” is a dated pointer). DEC-0376 / QMA Cut: *git-branch-per-parameter-mutation as the lineage mechanism* is cut; CT-47 already uses content-addressed `resolved_config_ref` plus predecessor CT-07 edges, *never a git branch per parameter*.

**Spine sentences:** AD-5 — *“Publishing appends that `fp1` to the QMA Experiment Ledger when a coordinated experiment exists.”* Path-dependent rerun may change `starting_capital` with no `seed_overridden`/`unrated` restatement. AD-9 — *“Each door step that changes resolved-config is an ExperimentSpec successor (`create_successor` + CT-07 `branches-from`).”*

**What:**
1. If `analysis.project` (COMP-QMB) appends the Experiment Ledger, QMB writes a QMA store — QMA AD-6/AD-9 violated. The later AD-5 sentence (“QMA queries may call … and persist refs”) is the legal path; the “Publishing appends” sentence does not say who writes.
2. Path-dependent `starting_capital` without B-3’s unrated stamp lets a What-if capital override ledger `role=confirmation` and reach AD-15’s “unless `role=confirmation`” admission clause.
3. Reusing `branches-from` for ExperimentSpec config successors redefines an inherited edge kind and is the DEC-0376 shape without git. CT-47 already has predecessor lineage on a new content-addressed spec.

**Fix:** QMA daemon (lease holder) persists refs after calling QMB; QMB never opens the daemon sqlite. Restate B-3: `starting_capital` override ⇒ `seed_overridden` ⇒ fold `unrated`; that run cannot be `role=confirmation`. ExperimentSpec succession = new `fp1` + CT-07 predecessor edge of an addable experiment-lineage kind (or CT-47’s existing predecessor language) — not `branches-from`.

---

### F5 — MEDIUM — Local AD-1..AD-16 collide with QMF/QMA/CONNECT AD-n; diagrams/conventions still state the pre-amendment rules

**Where:** Invariants headings; Consistency Conventions; Structural Seed mermaid (`CAND --> … QMA staging`).

**Parent sentences:** CONNECT conventions: *“Parent ids stay QMX AD-n, TN-n, B-n, QL-n. This spine’s AD-1..AD-5 are CONNECT-local.”* QMA AD-8: `JOURNAL != LEDGER != … != STAGING`. Local AD-14: candidate-set query *“does **not** read QMA staging.”* Local AD-15: do not extend B-4.

**What:** this child never declares its AD-n as workbench-local. Local AD-7 (paper trinity) vs QMF AD-7 (exact money), local AD-12 (extensibility) vs QMF AD-12 (worlds), local AD-1 (sixth application) vs QMF AD-1 (runtime matrix) / QMA AD-1 (packages) / CONNECT AD-1 (fail-closed selection) will be cited as the parent. The Conventions “Lanes” row still requires `lane` on artifact metadata; the capability mermaid still pipes candidate-set queries through QMA staging — both contradict the tightened AD-14/AD-15.

**Why it matters:** F1–F4 become un-reviewable in epics if “AD-7” and “AD-12” are ambiguous. Stale mermaid/conventions will be copied into stories.

**Fix:** add CONNECT’s sentence: parent ids stay QMF AD-n / B-n / QL-n / TN-n / QMA AD-n / CONNECT AD-n; this spine’s AD-1..AD-16 are workbench-local (WX-n is better). Fix the mermaid to AD-14’s three sources (QMB ledger, registry as-of including `dev`, Experiment Ledger refs). Fix Conventions “Lanes” to match AD-2/AD-15 as amended under F1.

---

## Touchpoint roll-up (no further findings)

| Local | Inherited | Class |
| --- | --- | --- |
| AD-3 Library kinds; staging excluded; STRATS = KnowledgeSource | QMA AD-8/AD-19; CONNECT STRATS out | **consistent** (after AD-14 staging exclusion) |
| AD-4 generation vs search; QMA never mints mechanism nouns | B-8; QL-2/QL-5; QMA AD-14; GAP-0085 | **consistent** / fulfills QMA deferred revisit |
| AD-6 complete CT-22/CT-27 candidate, not a patch | QMA AD-2/AD-14; AD-30 identity-is-content | **consistent** |
| AD-7 paper nouns (body, before hub sentence) | AD-12 worlds; AD-35; TN-9; CONNECT AD-2; DEC-0261 | **consistent** |
| AD-8 CLI transport, occupancy, `_ref` | QMA AD-17/CT-47; B-1 MCP-later; B-5 children | **consistent** |
| AD-10 JobHandle.cancel → QMB `aborted`; tab-close cancels nothing | QMA AD-5/AD-17; B-4 aborted line | **consistent** |
| AD-11 / AD-12 / GAP-0081 | B-9; DEC-0346; QMA Deferred UI SDK | **consistent** |
| AD-15 mapping table (roles vs claim-class vs evidence class) | B-4, B-7, AD-12, L20 | **consistent in intent**; undone by AD-2 `lane` as evidence class (F1) |
| AD-16 no Project/Workspace kind | B-3 workspace defaults; CT-47 ExperimentSpec | **consistent** |
| Optuna “5.0.0 current upstream; lockfile owns the pin” | B-8 `==4.9.0`; major bump is a contract event | **nit** — restate “major bump = contract-versioning event,” do not adopt 5.0.0 here |
| Deferred GAP-0048/49/16/17/81/70/76/79/86 | parent Deferred tables | **consistent** |

---

## Required amendment list (desk, not operator)

1. AD-2: spawn ≠ L33; `lane` not on B-4 and not AD-12 evidence class; AD-13 drop “governed ExperimentSpec.”
2. AD-7: restore B-15/TN-3 hub write path; keep sandbox refuse.
3. AD-1: closed store owners include QMA AD-6 + QMB ledger/run-dir.
4. AD-5: QMA persists refs; B-3 `seed_overridden` → `unrated`. AD-9: no `branches-from` for ExperimentSpec.
5. Conventions + mermaid + local-id disclaimer (F5).
