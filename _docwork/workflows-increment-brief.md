# QMX Workflows construction kit — documentation-factory Stage 9 brief (2026-09-19)

Route e, change mode, Stage 9. Do not restart Stages 1–8. Do not implement code, UI, n8n, Hermes, or OpenBB. Operator away: do not coach or pause. Do **not** emit a BMAD epics-and-stories prompt.

Planning checkout: `main` (this workspace). Implementation inspect: `integration@270e992995c2378ca63cf6343254ef8140a8c97e` via worktree `C:\Users\Mubarak\Desktop\QMX-worktrees\epic-051-skylos-mill-split` (HEAD matches). Do not use `8510c03` for absence claims. Do not switch branches.

## Authority

1. **Operator rider (ratified this session):** `_docwork/riders/workflows-construction-kit-2026-09-19.md`.
2. **Architecture package (folded):** `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/` — citation surface is `ARCHITECTURE-SPINE.md` (local AD-1..AD-31), `CHALLENGE-RECONCILIATION.md` (prefer §1/§6/§8 over residual AF-01 “OD-01 deferred” table cells), `OPERATOR-QUESTIONS.md` (OD-01 CLOSED), `CONTRACTS.md`, `JOURNEYS.md`, `REQUIREMENTS-ADDENDUM.md`, `CONFLICT-REGISTER.md` **C-05 row only** (footer is stale).
3. **Operator words:** `transcript-refresh-20260919/Explore-Node-Editor-Architecture.md` (~L1061 Book/BMS replace; sequential not tomorrow; Kelly; adopt-the-chain; sessions not tabs; app-use cannot edit).
4. **Codex catalog (oracles, not approval):** `codex-challenge-20260919/SCENARIO-CATALOG.jsonl` (85 IDs). BDD is specification.
5. **Parents bind read-only.** Local AD-1..AD-31 do not renumber them.

**Do not fold as current law:** `ARCHITECTURE-CANDIDATE-MANIFEST.json` (still 2026-09-18-a); `IMPLEMENTATION-SEQUENCE.md` **Blockers now** (OD-01 unanswered — stale); `CODEX-RECHECK-HANDOFF.md` wait text; empty `companions/` and `contracts/` dirs; Stage A `reviews/review-adversarial.md` as a judgment of 2026-09-19-c; CONFLICT footer “OD-01 option A”.

## Standing of claims

| Set | Stamp |
|---|---|
| Rider standing corrections | ratified (`authority: rider`) |
| OD-01 / AD-11 / AD-23 ATC class | ratified |
| AD-1..AD-22 | ratified |
| AD-24..AD-31 machines | ratified **with cheap-veto A1–A6** |
| ADR-0024 + new SCN-0018..0022 | ratified (docs authority only; not implementation) |
| ADR-0023 mill package | stays **provisional** |
| New normative sentences on already-ratified parent docs | cite new DECs; dated follow-up or annotation; do not rewrite original ADR Decision sections |

`verified: 2026-09-19` on every doc you touch.

## ID block

| Kind | Range | Use |
|---|---|---|
| SRC | SRC-21, SRC-22, SRC-23 | architecture folder; rider; original Explore transcript (operator words; no_chunks house treatment) |
| EXT | EXT-2246..EXT-2290 | one per AD + umbrellas + rider |
| DEC | DEC-0414..DEC-0444 = AD-1..AD-31; DEC-0445 umbrella; DEC-0446 preflight; DEC-0447 cheap-veto; DEC-0448 L36 amendment; DEC-0449 DEC-0389 amendment; DEC-0450 wiring honesty; DEC-0451 dead-list |
| GAP | GAP-0092..GAP-0100 new; update notes on GAP-0081/0083/0058/0062 in place. Do not fill 0085/0063/0061. |
| FEAT | FEAT-0051..FEAT-0057 |
| ADR | ADR-0024 |
| SCN | SCN-0018..SCN-0022 |
| CT | **no new id** | annotations + additive CT-40 family |
| COMP | **none** | **no sixth application** |

DEC-0408..0413 stay **dead**. DEC-0389 stays provisional mill text; **DEC-0449** is the named amendment of its two-class freeze (do not whole-supersede DEC-0389).

## Preflight verdict (record in ADR-0024)

**reuse** existing applications. **new COMP: none. new CT: none.**

| Work | Owner | Class |
|---|---|---|
| ContributionHit DTO + pin/tombstone | COMP-QMA-WIRE + COMP-QMA-DAEMON `published_contributions()` | amend DEC-0389 / extend CT-40 |
| Operation descriptor + InvocationEnvelope + GrantRecord | COMP-QMA-CORE + COMP-QMA-WIRE | extend |
| product_session CAS + authoring/app-use | COMP-QMA-DAEMON + COMP-QMA-WIRE | extend (journal projection, not new store class) |
| DAG validator | COMP-QMA-DAEMON / COMP-QMA-CORE | extend (closes hole under DEC-0312) |
| Task Graph edges + outbox + JobHandle parent vocab | COMP-QMA-DAEMON | connect named `task_graph_state` |
| ATC PolicyPair / AlternativeRunConfig | COMP-QMB (eval/journal) + COMP-QML (author) + COMP-QMN (seat after paper+L17) + COMP-QMF-RISK (default shapes only) | new function, existing COMPs |
| Data recipes definition identity | COMP-QMB wrap of COMP-QMF-DATA | amend sitting identity; release fp1 existing |
| Fencing sequential deploy | COMP-QMN (+ QMB simulate tokens) | extend |
| UI contribution DTOs | COMP-QMA-WIRE | new DTOs; chrome GAP-0081 |
| Pack lifecycle / export scanner | COMP-QMA-DAEMON | connect QMA AD-21 |

Candidates refused: COMP-WF / COMP-LIB / sixth COMP; new CT-*; marketplace (DEC-0361); solver (DEC-0362); HMR (DEC-0366); QMA `import qmb`; dummy Book; sensing-as-ATC; `hit_class: strats`; Stage 0 `graph` as executor (DEC-0411).

No existing component's authority shrinks. No new `depends_on` edge. No new contract id.

## Cheap-veto (DEC-0447) — operator may overturn in one line

| Id | Item | Default if no veto |
|---|---|---|
| A1 | PolicyPair field catalogue (AccountingPolicy / RiskPolicy closed fields in CONTRACTS §11) | proceed — ATC **class** is operator-direct; field list is sitting machinery |
| A2 | AD-25 fencing state enum (`idle`…`retired`) | proceed |
| A3 | InvocationEnvelope full field set + effect-specific idempotency matrix | proceed |
| A4 | ContributionHit pin tuple `(qualified_id, package_version, availability_revision)` | proceed |
| A5 | Recipe definition identity `(recipe_def_id, version, hash)` | proceed — CT-06 kind still deferred |
| A6 | CheckpointManifest restore order | proceed |

Not vetoable here: no sixth COMP; dummy Book INVALID_INPUT; sessions≠tabs; app-use cannot edit; QMN sole venue importer; L17; sequential paper-then-live; BDD=spec; mutmut optional.

## Feature slices (implementation still factory-pipeline-only)

| FEAT | Name | Primary DECs | Blocked by |
|---|---|---|---|
| FEAT-0051 | ContributionHit concatenate + pin/tombstone | DEC-0415, 0449, 0414, 0446 | FEAT-0050, FEAT-0041, FEAT-0046 |
| FEAT-0052 | Operation descriptor + InvocationEnvelope + GrantRecord | DEC-0416, 0437 | FEAT-0041, FEAT-0040 |
| FEAT-0053 | product_session + CAS + grant intersection | DEC-0421, 0442, 0422 | FEAT-0052, FEAT-0042 |
| FEAT-0054 | Graph Template DAG validator | DEC-0419, 0417, 0420 | FEAT-0042, FEAT-0037 |
| FEAT-0055 | Task Graph edges + outbox + JobHandle parent vocab | DEC-0420, 0439, 0429 | FEAT-0054, FEAT-0042, FEAT-0044, FEAT-0033 |
| FEAT-0056 | Four proofs as thin fixtures (Book regression; ATC simulate zero Book keys; recipe-def identity; app-use change-request; pack export/import) | DEC-0424, 0436, 0444, 0421, 0442, 0443, 0448 | FEAT-0051..0055, FEAT-0029, FEAT-0031 |
| FEAT-0057 | Safety fixtures (≥2 of: stream cancel+cutover; outbox restart; UNKNOWN blocks handover; stale predecessor refused; grant refuses other instance) | DEC-0438, 0439, 0441, 0437, 0443 | FEAT-0055, FEAT-0056 |

First epic = FEAT-0051. Do not launch it from this sitting. Do not schedule GAP-0081 chrome or GAP-0058 as first epic.

## Gaps (new)

| GAP | Question | Status |
|---|---|---|
| GAP-0092 | Focused Codex recheck of AD-23..AD-31 was skipped. When, if ever, is independent recheck required? | deferred, non-blocking. DF fold proceeds. Do not claim Codex approved those ADs. |
| GAP-0093 | product_session runtime absent at 270e992 | deferred; feeds FEAT-0053 |
| GAP-0094 | ContributionHit + pin/tombstone not on wire at 270e992 (still KnowledgeHit\|ArtifactHit) | deferred; feeds FEAT-0051 |
| GAP-0095 | Task Graph edges dropped / outbox absent (in-memory store) | deferred; feeds FEAT-0055 |
| GAP-0096 | Operation descriptor / InvocationEnvelope / GrantRecord absent | deferred; feeds FEAT-0052 |
| GAP-0097 | AlternativeRunConfig / PolicyPair not in code | deferred; feeds FEAT-0056 |
| GAP-0098 | QML→QMB→QMN cross-component integration unsupported (P2-INT-001) | deferred; package tests ≠ e2e |
| GAP-0099 | QMN supervision-mode taxonomy (unattended VPS vs local-attended vs agent-watched) — operator-seeded, sitting did not decide | deferred; do not invent |
| GAP-0100 | Cutover **readiness dashboard** (latency/deployed) vs AD-25 fencing machine — operator-seeded, sitting answered with fencing only | deferred; do not invent chrome |

## Drafting rules

- Cite new DECs on every new normative sentence. Self-contained sections. No “as discussed above”. No hedges. No TODO without a GAP id.
- Product nouns: capability / extension / workflow / mini-app / widget; Experimentation Board (layout only); product_session `psess:` ≠ QMA Session `sess:`; ContributionHit never fp1; Alternative Trading Composition / PolicyPair; RecipeDefinition ≠ release fp1.
- Banned: sixth COMP; dummy Book; treating sensing as ATC; `hit_class: strats`; Stage 0 `graph` as workflow; JobHandle states `succeeded` / `awaiting_approval`; n8n/OpenBB/Hermes as runtime; “Codex approved AD-23..31”; claiming product sessions / ContributionHit / durable edges exist at 270e992.
- L36 named amendment: keep bot → Book → BMS → operator as the **default** chain. Book/BMS are default implementations of accounting and risk/sizing roles, not the only implementations. Complete PolicyPair may occupy those roles without dummy records. L17 + sequential paper-then-live remain. QMN remains the only venue importer.
- Wiring honesty: inherit DEC-0286. At 270e992 this session reconfirmed KnowledgeHit\|ArtifactHit only.
- Preserve 85 Codex IDs as a pointer in gap-report and ADR-0024; do not mint 85 SCN files.
- UI-HOST “UiFlag / AD-26” is a numbering collision (AD-26 is now outbox). Do not invent which AD UiFlag belonged to; GAP if needed.

## Docs to touch

**New:** `docs/decisions/ADR-0024-workflows-construction-kit.md`; `docs/scenarios/SCN-0018-contribution-hit-honesty.md`; `SCN-0019-app-use-change-request.md`; `SCN-0020-two-trading-compositions.md`; `SCN-0021-outbox-jobhandle.md`; `SCN-0022-pack-lifecycle-headless.md`.

**Update:** constitution L36 (+ L7/L31 annotations); AGENTS.md; qma-core, qma-daemon, qma-wire; qmb, qml, trading-node; qmf-risk, qmf-registry, qmf-data; overview, stack, dependencies (notes only, no new COMP row); glossary; gap-report; traceability; index; changelog; ADR-0020/0022/0023 **dated follow-ups only**; CT-40, CT-47, CT-22, CT-27, CT-33, CT-06, CT-04 annotations; SCN-0015 note if it still says Library is two-class only.

Lenses: only if they still say JobHandle `succeeded`, or treat Experimentation Board as a registry kind, or treat Book/BMS as the only legal live composition.

## What not to do

- Do not mint COMP-WF, CT-52, or a recipe CT-06 kind.
- Do not fill GAP-0085 / 0063 / 0061 / 0062 / 0058 / 0081 chrome.
- Do not close GAP-0083 by renaming `desk_slug`.
- Do not rewrite ADR-0020/0022/0023 original Decision sections.
- Do not claim implementation.
- Do not start epics.
- Do not invent harness-engineering, loops-as-mini-apps, or readiness-dashboard designs.
