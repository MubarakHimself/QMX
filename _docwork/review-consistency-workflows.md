# Stage 7 pass-1 consistency review — Workflows construction kit

Date: 2026-09-19. Reviewer: grok-4.6 (fresh; did not draft). Scope: increment docs listed in `_docwork/workflows-increment-brief.md` against ledger DEC-0414..DEC-0451, `_docwork/gaps.yaml` GAP-0092..GAP-0100, and the Pass 1 checklist in `documentation-factory/stages/07-review.md`. No file edits. No git commit.

Authority read: `_docwork/ledger.yaml` (DEC-0389, DEC-0414..DEC-0451), `_docwork/gaps.yaml` (GAP-0081/0083/0058/0062/0085/0061/0063 and GAP-0092..0100), `_docwork/workflows-increment-brief.md`, `docs/` (ADR-0024, SCN-0018..0022, constitution, AGENTS, qma-*, qmb, qml, trading-node, qmf-risk/registry/data, CT-40/47/22/27/33/06/04, glossary, gap-report, overview, stack, dependencies, changelog, index, traceability, ADR-0020/0022/0023 follow-ups, SCN-0015). Did not read architecture sitting transcripts, Explore-Node-Editor zip, architecture-mimi0apps, or raw chunks.

## Verdict: FAIL-with-amendments

No critical. Wiring honesty at `270e992`, ADR-0023 `status: provisional`, L36 original sentence plus named DEC-0448 amendment, dummy Book as CT-04 `invalid input`, JobHandle parent vocab, `product_session` ≠ QMA Session, no sixth COMP, and dead-list honors are consistent across the fold. Amendments are required before pass: ADR-0023 Consequences still forbids a third federated hit class after DEC-0449 added ContributionHit; unqualified Workflows `AD-n` numbers collide with parent QMA ADs in the same files; SCN-0022 cites DEC-0431 for AD-10 composition modes.

## Findings

### 1. major — `docs/decisions/ADR-0023-qml-research-expansion.md` (Consequences)

**What's wrong.** The original Consequences sentence still reads as current mill law: “Federation must not grow a third hit class.” The 2026-09-19 follow-up on the same page named-amends DEC-0389 so product discovery concatenates `KnowledgeHit`, `ArtifactHit`, and `ContributionHit` as a third **discovery** class. Original Decision AD-9 (two-query freeze) is correctly left in place as mill text. Consequences was not annotated, so the same ADR both forbids and requires a third hit class.

**Contradicts.** DEC-0449 (named amendment of the two-class freeze; ContributionHit added; do not whole-supersede DEC-0389); DEC-0415 (frozen facade hits include ContributionHit); ADR-0024 / `qma-wire.md` Workflows section / CT-40 WORKFLOWS NAMED AMENDMENT (current facade law is three classes). DEC-0389 remains `provisional` with no `superseded_by` — that standing is correct; the unamended Consequences sentence is the defect.

**Fix.** In the 2026-09-19 follow-up (do not rewrite the original Decision section), retract or qualify the Consequences sentence: federation may grow ContributionHit as a discovery class; hypotheses still must not become a third **Library** rail (DEC-0381). Point at DEC-0449.

### 2. major — `docs/components/qma-daemon.md`; also `docs/components/qma-core.md`; `docs/decisions/ADR-0020-qma-agentic-system.md`

**What's wrong.** Local Workflows AD numbers are written unqualified inside parent QMA specs that already number AD-1..AD-29. The increment brief warned that AD-26 is a numbering collision (Workflows AD-26 = outbox; QMA AD-26 = variables registry). The daemon file now contains both “AD-26 outbox” (DEC-0439) and “### The configurable-variable registry write path (AD-26)” (DEC-0325). The same Workflows subsection says “Change-request is the AD-22 staging kind `change_request` (DEC-0429)” — DEC-0429 attributes the kind to Workflows AD-8; QMA AD-22 is the staging store; Workflows AD-22 is the Portfolio Manager label (DEC-0435). `qma-core.md` Workflows section says “contribution identity is the AD-2 tuple” (Workflows AD-2 / DEC-0415) in a spec whose QMA AD-2 is dependency direction, and “The AD-22 staging store gains the addable staging kind” next to Workflows content. ADR-0020’s dated follow-up repeats “the AD-26 outbox” inside the QMA ADR. JobHandle was correctly qualified as “QMA AD-17”; the other collisions were not.

**Contradicts.** DEC-0445 (“Local AD-1..AD-31 do not renumber parents”); DEC-0429 (change-request = staging kind, cited as AD-8, not AD-22); DEC-0435 (Workflows AD-22 is Portfolio Manager / `desk_slug=pm`); DEC-0439 (Workflows AD-26 outbox); DEC-0325 (QMA AD-26 variable registry); DEC-0321 (QMA AD-22 staging store).

**Fix.** Always qualify: “Workflows AD-26 outbox”, “QMA AD-26 variables”, “QMA AD-22 staging store”, “Workflows AD-8 product_session”, “Workflows AD-2 contribution tuple”. In the daemon Workflows paragraph, say the change-request kind is defined with product_session (DEC-0421 / DEC-0442) and stored as an addable kind in the existing QMA AD-22 staging store (DEC-0321) — do not call it “the AD-22 staging kind” in a Workflows section.

### 3. major — `docs/scenarios/SCN-0022-pack-lifecycle-headless.md`

**What's wrong.** Given paragraph: “Four composition modes (J12) remain available without core edits: consume artifact fp1; invoke exported op through the envelope; Graph Template coordinates two apps; composite app cites contribution ids. [DEC-0431]”. DEC-0431 is Workflows AD-18 (pack lifecycle / export). The four modes are Workflows AD-10 / DEC-0423. Citation-present-but-content-drifted.

**Contradicts.** DEC-0423 (four cross-app composition modes, none compulsory); DEC-0431 (pack is versioned; lifecycle AD-30; missing dep is a hard error; export scanner is the oracle).

**Fix.** Cite DEC-0423 for the four modes. Keep DEC-0431 / DEC-0443 on pack lifecycle and the export scanner.

### 4. minor — `docs/AGENTS.md` (Workflows hard rules)

**What's wrong.** “JobHandle uses parent vocabulary only — never `succeeded` / `awaiting_approval` (DEC-0445).” DEC-0445 is the umbrella (composition paradigm, no sixth COMP, docs authority only). It does not state JobHandle states. The closed vocab and the `succeeded` / `awaiting_approval` ban are DEC-0439 (and parent DEC-0316).

**Contradicts.** DEC-0439; the same rule is cited correctly in `qma-core.md` FM-14, SCN-0021, and ADR-0020 follow-up.

**Fix.** Cite DEC-0439 (optionally DEC-0316). Add DEC-0439 to AGENTS frontmatter `decisions` if the body keeps the sentence.

### 5. minor — `docs/glossary.md` (ATC / dummy); `docs/constitution.md` L36; `docs/scenarios/SCN-0020-two-trading-compositions.md`; vs `docs/contracts/ct-04-typed-refusal.yaml`

**What's wrong.** Workflows prose shouts `INVALID_INPUT` (glossary ATC, L36 amendment, SCN-0020, AGENTS, qmb, trading-node headings). CT-04’s closed category — the glossary’s refusal arbiter — is `invalid input`. `qmf-risk.md` FM-11 correctly maps dummy to `invalid input`; CT-04 / CT-22 / CT-27 / CT-33 WORKFLOWS USAGE invariants already use `invalid input`. Same refusal, two spellings.

**Contradicts.** DEC-0109 / CT-04 category enum; Pass 1 “same concept, same name everywhere (glossary is the arbiter).” Ledger DEC-0424 uses `INVALID_INPUT`; the contract fold maps it onto CT-04.

**Fix.** Glossary ATC entry: dummy is CT-04 category `invalid input` (workflows alias `INVALID_INPUT`). Align SCN-0020 / L36 annotation / AGENTS to the CT-04 spelling, or one explicit “aka” once.

### 6. minor — `docs/index.md`

**What's wrong.** “The corpus contains 128 files: 80 Markdown documents and 48 YAML artifacts.” Count on disk is 86 Markdown + 48 YAML = 134. The six new Markdown files (ADR-0024 + SCN-0018..0022) were indexed in the lists but the totals were not bumped.

**Contradicts.** The same page’s file lists (ADR-0024 and SCN-0018..0022 are linked).

**Fix.** Set 134 files: 86 Markdown, 48 YAML.

### 7. minor — `docs/scenarios/SCN-0018-contribution-hit-honesty.md`

**What's wrong.** Then (1): tool availability “still requires the intersection of published hits, host grants, product-session GrantRecords, and health. [DEC-0415]”. DEC-0415 says a hit is not a grant and that listings distinguish published vs configured vs granted vs reachable vs healthy. The intersection formula is DEC-0422. SCN-0019 cites DEC-0422 for the same sentence.

**Contradicts.** DEC-0422 (“Tool availability = intersection of (published ContributionHits, host grants, product_session GrantRecords, health)”).

**Fix.** Cite DEC-0422 for the intersection; keep DEC-0415 on “hit is not a grant.”

### 8. minor — `docs/glossary.md` (JobHandle)

**What's wrong.** JobHandle lists the seven parent states (DEC-0316) but does not record the Workflows ban on `succeeded` / `awaiting_approval` even though glossary is the vocab arbiter and this increment made that ban load-bearing (DEC-0439). Not a disagreement — `succeeded` is not listed as legal — but an implementer looking only at glossary misses the rejected aliases that SCN-0021 / qma-core FM-14 name.

**Contradicts.** None on legal states. Completeness vs DEC-0439.

**Fix.** One sentence: never `succeeded` or `awaiting_approval` on a handle; `awaiting_approval` remains a Mission/Task gate (DEC-0439).

### 9. minor — `docs/gap-report.md` vs `_docwork/gaps.yaml` (GAP-0083 / 0058 / 0062)

**What's wrong.** Gap-report navigation says “GAP-0081/0083 notes updated in place.” `gaps.yaml` GAP-0081 was updated (2026-09-19 chrome vs DTOs). GAP-0083 is still dated 2026-08-29 with no Workflows / DEC-0435 note. GAP-0058 and GAP-0062 were also in the increment “update notes in place” list and have no 2026-09-19 note. Standing is still deferred/open as required (not filled); the claim that 0083 was updated in the YAML catalog is false.

**Contradicts.** Increment brief (“update notes on GAP-0081/0083/0058/0062 in place”); gap-report table vs `gaps.yaml` GAP-0083 record.

**Fix.** Add a one-line 2026-09-19 note on those YAML rows: GAP-0083 not closed by Portfolio Manager display rename (DEC-0435); GAP-0058 stays its own increment (DEC-0427); GAP-0062 host still unruled. Do not change status.

### 10. minor — `docs/components/qma-core.md` frontmatter

**What's wrong.** Body cites DEC-0418 for “Collection mapping is not on the descriptor — it lives on Graph Template edges.” Frontmatter `decisions` omits DEC-0418.

**Contradicts.** Pass 1 “every normative statement traces to its cited ledger entry” plus house frontmatter-includes-body-cites convention used on this increment.

**Fix.** Add DEC-0418 to `decisions:`.

## Hunt results (checklist)

| # | Hunt | Result |
|---|---|---|
| 1 | New normative sentences cite DEC-04xx **and** say what the entry says | **FAIL** (narrow) — SCN-0022 DEC-0431 for DEC-0423 modes; SCN-0018 DEC-0415 for DEC-0422 intersection; AGENTS JobHandle → DEC-0445; daemon “AD-22 staging kind” vs DEC-0429 AD-8. Other new sentences on ADR-0024 / SCN-0018..0021 / constitution L36 / CT annotations match. |
| 2 | No two docs disagree (L36, ContributionHit vs mill two-class, JobHandle, dummy Book, `product_session` vs Session) | **FAIL** — ADR-0023 Consequences vs DEC-0449 (finding 1). L36 original + DEC-0448 amendment present. JobHandle seven states consistent; `succeeded` banned where Workflows speaks. Dummy forbidden everywhere. `psess:` ≠ `sess:` consistent. `INVALID_INPUT` vs `invalid input` is naming only (finding 5). |
| 3 | Dead list: nothing dead described as alive | **PASS** — DEC-0084/0085/0086, DEC-0361 marketplace, DEC-0362 solver, DEC-0366 HMR, DEC-0408..0413, dummy Book, sensing-as-ATC, `hit_class: strats`, Stage 0 `graph` as executor stay dead (DEC-0451). |
| 4 | `depends_on` in frontmatter exist in `dependencies.yaml` | **PASS** — all increment `depends_on` COMP-* ids resolve; no new edge. |
| 5 | ADR-0023 mill package remains `status: provisional` | **PASS** — YAML `status: provisional`; follow-up says mill is not flipped; DEC-0389 stays provisional with no `superseded_by`. |
| 6 | Wiring honesty: do not claim ContributionHit / `product_session` / durable edges / ATC PolicyPair exist at `270e992` | **PASS** — ADR-0024, all five SCNs, qma-wire/daemon/core, qmb, qml, trading-node, qmf-risk, CT-40, overview, dependencies notes, AGENTS, glossary. Inspect SHA is `270e992`; `8510c03` not used for absence. |
| 7 | L36 original sentence still present PLUS named amendment DEC-0448 | **PASS** — constitution L36 keeps bot → Book → BMS → operator (DEC-0143) and appends the 2026-09-19 named amendment (DEC-0448, DEC-0424, DEC-0436). `qmf-risk.md` quotes the original chain then amends. |
| 8 | No sixth COMP minted in `dependencies.yaml` | **PASS** — 21 component ids; no COMP-WF / COMP-LIB. Preflight reuse recorded on every touched COMP notes block. |
| 9 | GAP-0085 / 0063 / 0061 / 0062 / 0058 / 0081 chrome not filled; GAP-0083 not closed by renaming `desk_slug` | **PASS** on standing — all still deferred/open; DEC-0435 keeps `desk_slug=pm`. YAML note completeness is finding 9. |
| 10 | SCN-0015 still two-class Library only? | **PASS** (no change required) — SCN-0015 is door-derived lanes, not Library hit classes; `verified: 2026-09-14` is honest. |
| 11 | Lenses: JobHandle `succeeded`; Experimentation Board as registry kind; Book/BMS as only legal live composition | **PASS** — no `succeeded` in lenses; Experimentation Board is client-only (glossary + ADR-0022 follow-up); Book/BMS default-not-ceiling in constitution / qmf-risk / SCN-0020. |
| 12 | CT-06 recipe kind not minted; no new CT number | **PASS** — CT-06 WORKFLOWS USAGE defers recipe kind (DEC-0444, A5); CT-40 additive family only; no CT-52. |

DEC-0445 umbrella, DEC-0446 preflight reuse, DEC-0448 L36 amendment, DEC-0450 wiring honesty, and DEC-0451 dead-list honors are treated as ratified throughout, which matches ADR-0024. The fail is numbering-collision honesty, one mill Consequences leftover vs ContributionHit, and one wrong DEC on SCN-0022 — not a paradigm reversal.

## Counts

| Severity | Open findings |
|---|---|
| critical | 0 |
| major | 3 |
| minor | 7 |
| **total** | **10** |
