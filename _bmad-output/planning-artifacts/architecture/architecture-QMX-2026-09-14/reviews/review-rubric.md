---
lens: rubric-walker
target: ARCHITECTURE-SPINE.md (architecture-QMX-2026-09-14, status draft)
altitude: feature
reviewer_gate: good-spine checklist (references/reviewer-gate.md)
date: 2026-09-14
lint: 0 findings
---

# Rubric walker — QMX Strategy Experimentation Workbench spine

Verdict: **fail**. The sitting names the right paradigm and closes most workbench forks (no sixth app, generation ≠ search, three lanes, procedures in QMA, continuation ≠ QMB process, claim-class, data wraps qmf-data). It does not pass the enforceability bar: two load-bearing Rules fail to prevent their own stated divergences (AD-5 `rescale`, AD-7 “Book paper-mode evidence”), and F12 — listed in `binds` and called out by the driving intent as needing an AD — is never named. Those three let the next layer fork on What-if/MM, paper, and Project identity. Lint is clean (0 findings). Named tech checks out. Brownfield is ratified, not copied. Ops envelope is not silent.

Altitude: feature (keeps epics). Parents inherited by original ids. Local AD-1..AD-15 each have Binds/Prevents/Rule and `[ADOPTED 2026-09-14]`. No template comments. Companion `CAPABILITY-EXPANSION.md` is out of this walk except as spec coverage context.

## Checklist

| Bar | Result |
| --- | --- |
| Fixes real divergence for the level below; misses none | **Fail** — core forks are named, but F12 Project/Workspace (in `binds`, intent “needs an AD”) has no Rule, and Shared Library has no COMP owner despite AD-1 |
| Every AD Rule is enforceable and prevents its stated divergence | **Fail** — AD-5 and AD-7 undercut their Prevents; AD-2 stamp has no locus |
| Nothing under Deferred lets two units diverge | **Pass** — ownership vs nouns split on GAP-0085 is real; F07 method split held; host is operator config |
| Named tech verified-current | **Pass** — CPython 3.14.7 (2026-08-05); 3.15.0rc2 not adopted; Optuna 5.0.0 (2026-09-07) current, lockfile-owned not re-pinned |
| Ratifies brownfield rather than contradicting it | **Pass** — `RecordingQmbDoorTransport`, in-memory ExperimentSpec maps, and `defined-unwired` vs `integration@1b451a8` are named as connect-wave, not as a second design |
| Spec capabilities covered | **Partial** — F01–F06, F09–F13, F15, F07/F17 deferred; F12 unbound in Rules; F08 claimed by AD-5 but omitted from frontmatter; F14/F16 neither bound nor deferred |
| Inherited parents not weakened | **Pass with wording risk** — no local AD claims an override; AD-7 parenthetical can be *read* as QMB `world=live` paper-mode (B-7, QMA door, CONNECT AD-2, AD-35) |
| Every owned dimension decided, deferred, or open — especially ops envelope | **Pass** — AD-10/AD-11 + deferred host + inherited QMA AD-17/AD-25/AD-26; screen chrome deferred; no new plane |

## What works

Paradigm is a real contract: workbench composition over the four application-layer products plus QMF, not a fifth runtime. AD-1, AD-4, AD-6, AD-8–AD-15 are generally the right shape for epics.

- **AD-1** blocks COMP-EXP / HTTP experiment service / second identity store; DEC-0084 stays dead.
- **AD-4** actually splits search (QMB B-8) from generation (QML authors; QMB runs; QMA handles). GAP-0085 nouns stay deferred with ownership no longer undecided.
- **AD-6** restates QMA AD-14 money-path candidate law and forbids trade-list rescaling as Book simulation — the right prevent — *if AD-5 does not reopen it*.
- **AD-8** ratifies the existing route and occupancy; names the recording transport as the defect to replace; does not invent a second governor. “Backtesting Service” is the inherited QMA AD-17 / DEC-0348 plugin half, not a DEC-0084 revival, provided readers keep the parent.
- **AD-9 / AD-10 / AD-11 / AD-12** put procedures, continuation, notebooks, and extension rungs on existing COMPs. AD-10 aligns with QMA AD-25 (workstation default; overnight = stay on *or* deploy) without weakening B-5 (QMB still has no daemon).
- **AD-13 / AD-14 / AD-15** stop a QDM clone store, a copied databank, and projection-as-confirmation.
- Brownfield: treat CT-47 source as library-wired; process wiring (real CLI door, journal persistence) still to connect. Correct.
- Stack: no new framework. Optuna remains a QMB sampler adapter; floats still hit the named AD-7/AD-22 conversion (B-8).

## Findings

### High

#### H-1 — AD-5 Rule does not prevent its Prevents: unbounded `rescale`

**Where:** AD-5 Rule; AD-6 Prevents; F05/F06/F08.

**Prevents (AD-5):** “a filtered trade list being treated as a Book/BMS counterfactual.”

**Rule:** projection is “read-time filter/**rescale** of a cited CT-29/CT-32 stream, claim-class `projection`, never admission evidence.”

“Never admission evidence” blocks live-gating. It does **not** block shipping QuantAnalyzer money-management as a projection rescale of sizes/equity and calling it a Book/BMS counterfactual analysis. That is exactly AD-6’s prevent (“trade-list rescaling posing as Book simulation”). Hours/days/max-trades → projection is a good default; `rescale` is not scoped, so two epics fork:

- *A* implements F06/F08 as projection rescale of the trade list (allowed by AD-5 literal).
- *B* refuses any size/Book/BMS/`starting_capital` rewrite except path-dependent replay (AD-6).

Exact-money (QMF AD-7) is also unpinned on “rescale.”

**Action:** apply. Bound projection to filter / time-window / cap-count / display-only axis rescale of a cited stream. Size, Book, BMS, ports, and `starting_capital` are path-dependent (AD-6). Keep “never admission evidence.”

#### H-2 — AD-7 parenthetical re-collides the paper nouns it exists to split

**Where:** AD-7 Rule: “research-paper = QMB governed replay (**and Book paper-mode evidence**) outside the node.”

AD-35 paper-mode is Book-level `LIVE | PAPER`, routed with `role=demo`, `world=live`. Node-paper in this same AD is that path. QMB’s legal world is `replay` (B-7). The QMA door refuses venue/account/paper fields and is `world=replay` only (CT-47 / QMA AD-17). CONNECT AD-2 is honest FX paper on the node.

The parenthetical lets a unit classify Book paper-mode / `world=live` evidence as research-paper “because it is outside the node,” which is the three-noun collapse the AD Prevents.

Charitable intent: research-paper is Book-*constrained* QMB replay (DEC-0261), not per-bot, and is not node soak. The words “paper-mode” do not say that.

**Action:** apply. Drop “and Book paper-mode evidence.” State: research-paper = QMB governed replay (`world=replay`, Book/BMS fragments in the run-config) outside the node, before promotion. Node-paper stays `role=demo`, `world=live` on QMN. QMA-paper does not exist.

#### H-3 — AD-2 `lane` stamp has no artifact locus

**Where:** AD-2 Rule “stamped on every experiment artifact”; Conventions “Artifact metadata includes `lane`”; ungoverned “writes no ledger.”

The three lanes themselves are enforceable at write boundaries (`qmb.run()` vs orchestrator vs CT-47 door / no `import qmb`). The stamp is not. Ungoverned returns values. Two units will stamp (a) a returned dataclass, (b) only CT-32/ledger/ExperimentSpec, or (c) a sidecar file.

**Action:** apply. Stamp `lane` on ExperimentSpec, CT-32, and governed ledger lines. Ungoverned values are not experiment artifacts until L33 graduation, which records origin `lane=ungoverned` on the lineage edge. Coordinated artifacts also carry the door/job id.

#### H-4 — F12 Project vs Workspace is in `binds` and has no Rule

**Where:** frontmatter `binds`; intent-durable “Project vs Workspace … Open (needs an AD)”; companion claims it is “answered as ExperimentSpec + projections”; AD-3/AD-8 never say the nouns.

AD-1 blocks a *Project service / new store*. It does not stop two epics from minting “Project” as (a) ExperimentSpec, (b) a QMA Mission wrapping many specs, or (c) a saved view. That is the F12 divergence.

**Action:** apply. One clause, likely AD-3 or AD-8: a research undertaking (QC Project continuity) **is** an ExperimentSpec plus its Experiment Ledger; work-environment / Workspace / tabs are UX over fp1 cites (and existing QMA Desk/Profile), not an identity kind and not a store.

### Medium

#### M-1 — Shared Library query owner unpinned against AD-1

AD-1 requires every new capability to name an existing `COMP-*` owner or an explicit connect/extend. Capability map: “Shared Library | projections over fp1 kinds.” AD-14 correctly forbids a copied payload store; it does not say who exposes the federated query. Connect-wave can grow two Library APIs (QMB ledger fold vs QMA wire vs a helper module).

**Action:** apply. No federating COMP. Registry answers as-of kinds; QMB owns ledger views; QMA may expose a wire query that cites those folds by fp1; UI does not persist a third copy (AD-14).

#### M-2 — F08 in AD-5 Binds, absent from frontmatter; F14/F16 neither bound nor deferred

F08 equity-control is a real AD-5 consumer; omitting it from `binds` lets an epic treat comparison as out of scope. F14 (contextual agent binding to exact fp1) and F16 (concurrent edit) are owned enough at this altitude to be deferred explicitly (UI chrome / append-only identity) rather than dropped.

**Action:** apply. Add F08 to `binds`. Deferred rows: F14 placement = UI; agent-to-fp1 binding = AD-3 + inherited QMA `scope_path`. F16 = content-addressed versions + sole writer; no lock service in this sitting.

#### M-3 — Path-dependent analysis has no default claim-class

AD-5 stamps `analysis_method`; AD-15 stamps `claim-class` ∈ `{confirmation, trial, replicate, projection, robustness, infra-stress}`. Projection maps to `projection`. A path-dependent Book/BMS replay is a new QMB run (almost always B-4 `trial`, never confirmation unless it meets B-4). Unstated, two units will stamp `confirmation` on a What-if re-run that cited a confirmation baseline.

**Action:** apply. Path-dependent artifacts take the B-4 role of *that* run. Citing a confirmation baseline does not mint `claim-class=confirmation` on the child.

### Low

#### L-1 — Optuna 5.0.0 cited as current without “not adopted”

Verified: Optuna v5.0.0 released 2026-09-07; QMB spine pin is 4.9.0 and calls a major bump a contract-versioning event. This sitting correctly leaves the lockfile in charge, but CONNECT-style “5.0.0 exists and is not adopted here” would stop a careless bump.

**Action:** apply (one clause) or ignore if the currency lens already carries it.

#### L-2 — AD-8 “Backtesting Service” without the no-state clause

Relies on inherited QMA AD-17 / glossary DEC-0348. A reader of this spine alone could mint a stateful service and think DEC-0084 still holds because AD-1 said so in prose.

**Action:** ignore if H-2 is applied and Inherited Invariants stay binding; else restating “plugin daemon half; no scheduler, parallelism, or durable backtest state” is cheap.

#### L-3 — Local AD-n vs QMF/QMA AD-n in conversation

Same as CONNECT. Conventions already keep parent ids as QMF AD-n / B-n / QL-n / TN-n / QMA AD-n.

**Action:** ignore.

## Dimensions owned at this altitude

| Dimension | Disposition |
| --- | --- |
| Sixth app / identity store | AD-1, AD-3 |
| Experiment lanes | AD-2 (stamp locus = H-3) |
| Search vs generation | AD-4; algorithm open |
| Analysis method | AD-5 (rescale = H-1); AD-15 |
| Book/BMS variants | AD-6 |
| Paper nouns | AD-7 (H-2) |
| QMA↔QMB door | AD-8 |
| Procedures | AD-9 |
| Continuation / laptop-off | AD-10; host deferred/open (operator ExecutionEnvironment / QMA AD-25/26) |
| Notebooks | AD-11; Jupyter vendor pin deferred |
| Extensibility | AD-12; rung 4 = GAP-0081 |
| Data work | AD-13 |
| Candidate sets | AD-14 |
| Project / Workspace | **silent as nouns** (H-4) |
| Deployment / infra / ops | inherited; no new plane; AD-10 property; MCP after CLI v1 deferred |
| UI chrome / departments | deferred |
| F07 / F17 / GAP-0048/49/81/85 nouns | deferred with reasons |

## Tech currency (this walker)

- CPython 3.14.7 current stable (python.org, 2026-08-05). 3.15.0rc2 exists 2026-09-01; not adopted. Matches inherited QMX AD-1 / `docs/architecture/stack.md`.
- Optuna 5.0.0 current PyPI (2026-09-07). Spine does not re-pin (L-1).
- No new framework. uv/QMF stores inherited.

## Brownfield

Ratified, not contradicted: replace `RecordingQmbDoorTransport`; persist ExperimentSpec/ledger through the daemon writer rather than in-memory `_specs`; do not treat contract `defined-unwired` as “no code.” Unforked `run_slice`, one library, CT-47 door law, no `import qmb` from QMA — all match `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` as described in the sitting’s own code inputs.

## Gate action

Do not hand to documentation-factory / epics until H-1..H-4 are applied on the spine (editor-applicable; no new sitting). M-1..M-3 should ride the same pass. L-1 optional.
