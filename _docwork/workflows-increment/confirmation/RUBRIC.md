# Confirmation rubric — Workflows DF fold vs sources (2026-09-19)

**Seat:** grok-4.6 orchestrator, confirmation pass (not a second Documentation Factory fold, not epics, not architecture reopen).

**Question:** did the 2026-09-19 `docs/` fold actually absorb what the operator said, and did this session actually re-read the attached sources rather than grepping the architecture distill?

**Verdict:** **CONFIRM WITH CAVEATS.** Operator-direct law is in `docs/`. Sitting machinery is labeled cheap-veto, not operator diction. Thinned seeds are mostly later/optional (INT-28: enabling system, not every idea). No blocking miss of a spoken ruling. First DF pass under-read the Explore zip; this confirmation re-read it.

Inventories this file scores against:

- `A-explore-transcript.md` — sequential read of Explore transcript (ends L1905)
- `B-staged-handoff.md` — every text file in the staged-handoff zip
- `C-architecture-mimi.md` — sequential read of `architecture-mimi0apps` (ends L1234)

---

## 0. What this is / is not

| This pass does | This pass does not |
|---|---|
| Re-read the three attached sources (zip / zip / sitting export) | Re-run Documentation Factory |
| Score the uncommitted `docs/` fold against those sources | Launch `bmad-create-epics-and-stories` |
| Separate operator words from sitting paraphrase from Codex machinery | Implement code, mint a new COMP/CT, or reopen AD-1..31 |
| Record honest process holes (Codex recheck skip; first DF under-read) | Claim Codex approved AD-23..31 |

The fold remains **uncommitted working tree**. Implementation remains factory-pipeline-only (DEC-0445).

---

## 1. Source coverage — honest split

### 1.1 Explore zip (`Explore-Node-Editor-Architecture (1).zip`)

| Fact | Evidence |
|---|---|
| Zip still at Downloads | SHA256 `EB59C8785E4ADE1708FA0A930249AB06A959F71C1A4E651236E1E594FEC2D218` |
| Markdown inside | SHA256 `6C0D414143EB98A0E65E914F14270F63A35B8DD61AE66A9E52922BA0922836B7` · 287042 bytes · file ends **L1905** |
| Extracted copy used | `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/transcript-refresh-20260919/Explore-Node-Editor-Architecture.md` |
| Zip contents | `images/`, `images/image-001.png`, `Explore-Node-Editor-Architecture.md` |
| Image-001 | Opened in confirmation A. **Taskade** Flows UI (`taskade.com/workspace/flows`), attached ~L1053. **Not** the Bloomberg-style home-dashboard mock (~L591 / ~L1076). |

**Who actually read it, this confirmation:**

| Reader | What they opened |
|---|---|
| Agent A (grok-4.6) | Sequential overlapping ranges **L1–400, 350–750, 700–1100, 1050–1450, 1400–1905**. Operator dictation blocks in full: L3–7, L193–198, L309–327, L425–429, L589–597, L717–727, L879–889, L1051–1076, L1241–1243, L1369–1373, L1441–1446, L1641–1648, L1788–1795. **No unread tail.** |
| Orchestrator (this seat) | Independent contiguous re-open of L1–30, L185–200, L305–330, L710–730, L875–890, L1046–1125, L1888–1905. Spot-checked A's quotes against the file. Did **not** re-walk every line 1–1905 in this turn; A already did. |

**First DF fold (prior turn in this session):** Explore zip was **not** re-unzipped; sitting export was sampled; staged-handoff treated as already absorbed. That is the hole the operator called. This confirmation closes the *read* hole. It does not rewrite `docs/`.

### 1.2 Staged-handoff zip (`QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18.zip`)

| Fact | Evidence |
|---|---|
| Zip still at Downloads | SHA256 `9BCEC38EE94DD4A3E693B0486987A476C28207B6FA1BC9F744D0AD9E01E205B4` |
| Extracted tree | `workroom/research/2026-09-18_node-editor-architecture/staged-handoff/QMX-GROK-CODEX-STAGED-HANDOFF-2026-09-18/` |
| Self-declared status | Staged assignment; not implemented or ratified architecture |

**Who actually read it:**

| Reader | What they opened |
|---|---|
| Agent B (grok-4.6) | **Every** top-level `.md`/`.txt`/`.json`; provenance/source-selection/previous-manifest/review-delta/original-prompt/codex-audit-instructions; all five audit reports; all four diagnostic notes; `reference-images/README.md`; `evidence/earlier-session-snapshot.md` (1,239-line 17 Sep snapshot) with operator turns T1, T3, T5, T6, T8, T9, T10 contiguous. Binaries: existence + hashes only. |
| Orchestrator | Independent full read of `02-OPERATOR-INTENT-AND-SCOPE.md` (INT-01..30 + Sept 18 rider). Spot-checked `00-START-HERE.md` coverage against B's gist table. |

**Not in this ZIP (package says attach separately):** the 18 Sep full Explore transcript. INT-01..30 are **assistant-authored retrieval IDs**, not minted QMX requirements. Latest explicit transcript still governs (package's own rule).

### 1.3 Sitting export (`architecture-mimi0apps`)

| Fact | Evidence |
|---|---|
| Kind | Grok Stage A/C **tool log**, not the Explore brainstorm |
| Ends | **L1234** (DF launch prompt). Seven `## User` turns. |

**Who actually read it:** Agent C sequential overlapping **L1–400, 350–750, 700–1100, 1050–1234**. Orchestrator independently opened L1–5 and L1220–1234 (OD-01 close + DF prompt). No unread tail.

### 1.4 Fold artifacts scored (orchestrator)

Opened for scoring, not re-folded: `docs/constitution.md` L36; `docs/decisions/ADR-0024-workflows-construction-kit.md`; SCN-0018..0022; `_docwork/gaps.yaml` GAP-0092..0100; `_docwork/feature_inventory.yaml` FEAT-0051..0057; `_docwork/ledger.yaml` DEC-0448..0450; `_docwork/stage_state.yaml` 2026-09-19 row; `docs/AGENTS.md` Workflows hard rules; `docs/glossary.md` Experimentation Board / Portfolio Manager / product_session; `_docwork/workflows-increment-brief.md`.

---

## 2. Scoring key

| Score | Meaning |
|---|---|
| **HOLD** | Operator said it; `docs/` states it as law, with the right owner. |
| **HOLD-paraphrase** | Operator substance is in docs; the slogan or record name is sitting/Codex wording. Correct intent; do not treat the slogan as spoken. |
| **CHEAP-VETO** | Sitting machinery, correctly labeled DEC-0447 A1–A6. Operator may overturn in one line. Not operator diction. |
| **THINNED** | Operator seeded it; fold deferred it as GAP or left it as optional later work. Allowed under INT-28 (enabling system, not every idea) **if** the seed is not silently treated as refused. |
| **OVER-SPEC-labeled** | Architecture went past his words **and the fold says so** (cheap-veto, GAP, or “sitting machinery”). |
| **MISS** | Operator-direct ruling is absent, inverted, or presented as optional when it was law. |

---

## 3. Operator-direct rulings vs `docs/`

Quotes checked against Explore `# you asked` blocks this pass (A table + orchestrator re-open).

| Ruling | ~Line | Fold landing | Score |
|---|---|---|---|
| Node editor is a large blast radius; compose capabilities, not a small add-on | L3, L196 | ADR-0024 Context + AD-1/DEC-0414 composition over existing apps | **HOLD** |
| QMA long-running agentic tasks ≠ these workflows | L196 | AD-7 reuse QMA as procedure runtime; AD-4 four layers distinct; AD-8 product_session ≠ QMA Session | **HOLD** |
| Experimentation Board (not “research board”); messy drafts allowed; drawing is not execution | L196, L319 | Glossary “Experimentation Board” + AD-4/DEC-0417: client-only layout, writes nothing. “Messy storyboard” UI is chrome (GAP-0081) | **HOLD** of the enabling constraint; **THINNED** of UI messiness |
| Intentional connections; not every object is a node; notebook may encapsulate | L309 | AD-5 mapping explicit; INT-04 captured as AD-4 node granularity | **HOLD** |
| Defaults and templates; not an empty canvas; custom creation remains | L319, L426 | AD-20/DEC-0433 | **HOLD** |
| n8n / OpenBB / Hermes / Taskade = mental models, not runtimes | L327, L426, L1642 | AD-17 JSON Render/MCP Apps are presentation adapters; AD-19 mutmut optional; INT-27 | **HOLD** |
| Mini-apps / extensions / widgets as related-but-distinct; less core maintenance | L319, L591, L737 | AD-1 product nouns; AD-18 packs; AD-10 four composition modes | **HOLD** |
| QMF is the one framework; no parallel general framework | L591, L1061 | AD-1, DEC-0446, DEC-0451, AGENTS hard rule. No `COMP-WF` in `dependencies.yaml` | **HOLD** |
| Data/ML need not be a bot | L426 | AD-11 class 3 `UngovernedWorkConfig`; INT-17 | **HOLD** |
| Specialists remain; do not collapse to one main assistant | L720 | AD-8 “Specialists remain”; AGENTS | **HOLD** (later L879 oscillation about “one named copilot + multiple sessions” is packaged as INT-08 mixed — compatible, not a deletion) |
| Trading-floor PM = Portfolio Manager; preserve BMAD Product Manager | L720 | AD-22/DEC-0435; glossary; GAP-0083 not closed | **HOLD** |
| Marketplace not required | L890 | AD-18 marketplace stays dead DEC-0361 | **HOLD** |
| Headless / CLI; not everything in the UI | L889, L1069 | AD-21 headless parity; QMB only operator CLI | **HOLD** |
| Sessions own context, not tab switching | L1058 | AD-8/DEC-0421; SCN-0019; glossary `product_session` | **HOLD** (`psess:` vs `sess:` is sitting machinery — **OVER-SPEC-labeled**) |
| Two copilot firepowers; app-use cannot edit; authoring can | L1058–1061 | AD-8, AD-9, SCN-0019 | **HOLD** (typed `change_request` with hashes/CAS is sitting protocol — **OVER-SPEC-labeled**) |
| Book/BMS replace **or** improve; Kelly / no-Book portfolio; not the only stack | L196, L889, L1061 | L36 named amendment DEC-0448; AD-11/AD-23; SCN-0020 | **HOLD** |
| Sequential, not hot; cannot trade tomorrow; paper money first; readiness dashboard | L1061 | AD-14 sequential handover; AD-25 fencing; L17 remains. Dashboard chrome → **GAP-0100** | **HOLD** of operating discipline; **THINNED** of dashboard chrome (correct — do not invent UI) |
| Adopt-the-chain: new portfolio version affects QML, QMB, MIS, QMN, paper, live | L1061 | L36 amendment; AD-11 “when ATC is selected, consumers adopt”; SCN-0020 Then (2) | **HOLD** |
| QMN = unattended-server **symbol**, not the only live mode | L1061 | QMN sole **venue importer** (not sole supervision mode). Three modes → **GAP-0099** | **HOLD** of venue-importer law; **THINNED** of supervision taxonomy (honest — sitting did not decide) |
| Build the enabling system, not every transcript idea | L1070, L893 | INT-28; FEAT-0051..0057 first slice; OP-001..080 not a backlog | **HOLD** |
| Grok must read this whole transcript | L1901–1904 | This confirmation. First DF pass failed this. | **HOLD now**; first-pass process miss recorded in §7 |
| Dummy / “never fake a Book” / `NULL_BOOK` / `INVALID_INPUT` | **not spoken** | L36 + SCN-0020 + AGENTS. Closest operator intent: do not force Kelly/no-Book to pretend it is a Book; do not clash v1/v2 | **HOLD-paraphrase** |
| L17 / live zone / human-signed promote | **not spoken** | Mapped onto existing L17. Operator said paper money, sequential cutover, he must be sure, readiness dashboard, “a lot of this depends on me” | **HOLD-paraphrase** (compatible; not uttered) |
| L36 named amendment as operator diction | **not spoken** | He never named L36. He said Book/BMS are how this version is built and must be replaceable. Sitting named the law id | **HOLD-paraphrase** of substance; id is sitting |
| “Sensing/research is not a trading composition” | **sharper than spoken** | L36 + DEC-0451 + SCN-0020 Branch B. Operator said data/ML need not be a bot **and** MIS can be swapped inside a portfolio. Codex Stage C paste (operator-forwarded) forbade disguising sensing as the second trading system | **HOLD-paraphrase** via Stage C acceptance, not Explore slogan |

**No MISS in this table.** Load-bearing spoken law is in the constitution, ADR-0024, AGENTS, and the five SCNs.

---

## 4. INT-01..30 vs fold

INT IDs are handoff-local retrieval aids (`02-OPERATOR-INTENT-AND-SCOPE.md`). Origin labels from confirmation B. Latest Explore transcript still governs when they conflict.

| ID | Intent | Fold | Score |
|---|---|---|---|
| INT-01 | QMF one framework; no extra general framework | AD-1, DEC-0446, DEC-0451 | **HOLD** |
| INT-02 | Experimentation Board; not Research Board | AD-4, glossary | **HOLD** |
| INT-03 | Defaults + templates + custom | AD-20 | **HOLD** |
| INT-04 | Intentional/flexible granularity; notebooks encapsulate or expose | AD-4 | **HOLD** |
| INT-05 | Explicit connections, ports, cardinality | AD-5, AD-26 join algebra | **HOLD** (join algebra field catalogue is cheap-veto-adjacent sitting) |
| INT-06 | Capability / extension / workflow / mini-app / widget distinct | ADR-0024 Decision product nouns | **HOLD** |
| INT-07 | Copilot, manual, or code/CLI/notebook; deterministic and agentic | AD-20, AD-21 | **HOLD** |
| INT-08 | Familiar copilot identity; independent sessions; specialists remain | AD-8 | **HOLD** (mixed origin; L720 correction + L879 “one agent we can talk to”) |
| INT-09 | Authoring vs app-use | AD-8, SCN-0019 | **HOLD** |
| INT-10 | Session-owned context, not tabs | AD-8 | **HOLD** |
| INT-11 | Apps describe copilot access; change request to authoring | AD-9, SCN-0019 | **HOLD** (CAS completeness list is sitting) |
| INT-12 | Memory/context/skills/hooks/logs; do not collapse stores | AD-16 persistence split | **HOLD** |
| INT-13 | Local files, commands, browser/computer-use provisionable | AD-15 fail-closed until registered (GAP-0070/0078) | **HOLD** |
| INT-14 | Platform-wide customizability; less core maintenance | AD-1, AD-18 | **HOLD** |
| INT-15 | Shareable versioned packages; no compulsory marketplace | AD-18, AD-30, SCN-0022 | **HOLD** |
| INT-16 | First-class data expansion | AD-12 recipes wrap qmf-data | **HOLD** |
| INT-17 | Research includes data/ML/sentiment, not only trading ideas | AD-11 class 3 | **HOLD** |
| INT-18 | Materially different complete trading systems; no dummy wrappers | AD-11/AD-23, L36, SCN-0020 | **HOLD** |
| INT-19 | Blast radius QML/QMB/QMA/QMN/QMF | ADR-0024 blast-radius paragraph | **HOLD** |
| INT-20 | Sequential evaluate then deploy; not hot | AD-14, AD-25 | **HOLD** |
| INT-21 | VPS unattended central; local/supervised also valid | QMN venue importer + GAP-0099 | **HOLD** + **THINNED** taxonomy |
| INT-22 | Multi-broker/account/instrument/provider explicit | AD-12 provider ≠ venue ≠ account | **HOLD** |
| INT-23 | GPU/local/server preflight; no invented subscription | AD-15 | **HOLD** |
| INT-24 | Agentic plugins ≠ platform extensions | AD-18 / QMA AD-21 connect | **HOLD** |
| INT-25 | Portfolio Manager | AD-22 | **HOLD** |
| INT-26 | BMAD architecture; operator does not design schemas | Sitting did; DF folded | **HOLD** |
| INT-27 | Donors are mental models | AD-17, AD-19 | **HOLD** |
| INT-28 | No 40/80/200 ceiling; no duty to build all ideas | FEAT slice + OP-001..080 optional | **HOLD** |
| INT-29 | Backend/contracts now; visual UI later | AD-17 chrome GAP-0081 | **HOLD** |
| INT-30 | Architecture → DF → epics in later sessions; no impl in this sitting | DF ran in a **fresh** session as required; this confirmation does not start epics | **HOLD** |

**Unnumbered 18 Sep rider** (foot of `02`, not INT-IDs): four cross-app modes → AD-10/DEC-0423/SCN-0022; internal APIs + files → AD-3 descriptors (transport not dictated); copilot discovers without self-granting → AD-9; Hermes study → donor notes; mutmut optional isolated → AD-19/DEC-0432; authoring/app-use/specialists/PM remain. **HOLD.**

---

## 5. GAP-candidate inventory (A §3) vs fold

Operator content that is easy to lose once AD-11/AD-23/ATC catalogues take over. Inventory score, not a demand to mint 30 GAPs.

| # | Seed | Fold treatment | Score |
|---|---|---|---|
| 1 | Messy experimentation storyboard / draft sheet | Board = client layout (AD-4). Messy UI = GAP-0081 chrome | **THINNED** correctly |
| 2 | Notebook / Jupyter / GA node; declared outputs cross the wire | INT-04 / AD-4 granularity. No shipped node catalogue | **THINNED** (enabling, not a shipped catalogue) |
| 3 | Default node catalogue from existing Graph Templates | AD-20 “ship enough defaults”. Catalogue itself not listed | **THINNED** |
| 4 | WF1/WF2 birth story (old long-running research agents, Excel/Airtable) | **Not** QML's WF1/WF2. Not in GAP-0092..0100 | **THINNED** (historical seed; name collision with QML) |
| 5 | Desks vs mini-apps-as-departments | INT-06 “no compulsory hierarchy”. No department product | **THINNED** |
| 6 | Two copilot harnesses; each app ships access definitions | AD-8/AD-9. VS Code right-panel / MCP Apps driving visible mini-app is UI | **HOLD** of split; **THINNED** of chrome |
| 7 | Loops as mini-apps; four agentic-engineering pieces | Skills remain knowledge (AD-7); loops ≠ Missions | **THINNED** (correct refusal of loop-as-skill collapse) |
| 8 | Skill authoring ≠ skill activation (Caliper) | Not a v1 FEAT. Caliper = eval mental model | **THINNED** |
| 9 | Artifact Library upgrade / “database” | AD-2 kinds **unchanged**; discovery concatenates hits; AD-16 no new DB by default | **THINNED** — operator “database” was seed, not a mandated sixth store. No dedicated GAP. Acceptable under “no new store class” |
| 10 | Internal APIs + files | AD-3 descriptors; transport not dictated | **HOLD** |
| 11 | Composite apps (App D) | AD-10 mode 4; SCN-0022 | **HOLD** |
| 12 | JSON Render = widgets; MCP Apps = heavy lifting | AD-17 adapters, not runtime | **HOLD** |
| 13 | Dedicated assistant skill + hooks | QMA hooks already exist; no new QRM COMP | **THINNED** |
| 14 | Settings: provider / broker / account first-class; Islam/instrument class | INT-22 explicit identities. **Islam constraint not named** in docs | **HOLD** of explicit identities; **THINNED** of Islam-as-settings (seed, not a frozen product limit) |
| 15 | GPU / Colab / Modal / e2b preflight | AD-15 states; no invented provider | **HOLD** |
| 16 | Three live-supervision modes | **GAP-0099** | **THINNED** honestly |
| 17 | Readiness dashboard before cutover | **GAP-0100** | **THINNED** honestly |
| 18 | Versioned user packages (scalping Book v1/v2) | AD-18/AD-30 pack lifecycle | **HOLD** |
| 19 | Two MIS versions at once; need not render | Not a dedicated GAP. ATC/ungoverned can omit MIS | **THINNED** |
| 20 | LSE product surface as seed | INT-27 mental model; Codex browser recon was optional/separate | **THINNED** (correct — not a dependency) |
| 21 | Omarchy share-without-marketplace | Marketplace dead; packs install with local config | **HOLD** of no-marketplace |
| 22 | Webhooks / n8n node study | Mental model; operator gave liberty to refuse | **THINNED** |
| 23 | Computer-use / browser for copilot | AD-15 fail-closed GAP-0070/0078 | **HOLD** |
| 24 | Jev / TypeSafe; not automatically a QML bot | AD-11 class 3 | **HOLD** |
| 25 | CIS journeys for later UI sitting | INT-29 UI later | **THINNED** |
| 26 | Application-specific workflow templates | AD-20 | **HOLD** as principle; catalogue **THINNED** |
| 27 | Islam / instrument-class as settings | See #14 | **THINNED** |
| 28 | “Compilers” between mini-app agents/workflows | Unfinished dictation ~L1790 | **THINNED** (do not invent) |
| 29 | Local files for desktop copilot | INT-13 / AD-15 | **HOLD** |
| 30 | QMB speed / StrategyQuant mental model; local vs VPS split | INT-21/27 | **HOLD** |

Nothing in this inventory is a **MISS** of spoken law. GAP-0099 and GAP-0100 are the two operator-seeded items the sitting correctly refused to invent. The rest are enabling-vs-later under INT-28.

---

## 6. Over-specification — is it labeled?

From confirmation A §4. Fold handling:

| Sitting invention | Labeled as such? | Score |
|---|---|---|
| PolicyPair / AccountingPolicy / RiskPolicy **field catalogue** (AD-23) | Cheap-veto **A1**. ATC **class** is operator-direct | **OVER-SPEC-labeled** |
| Dummy Book `INVALID_INPUT` / `NULL_BOOK` slogan | HOLD-paraphrase of “don't pretend Kelly is a Book” | acceptable |
| `venue_requires_book` typed refusals / live-ATC admission codes | Sitting. Operator's gate is human sequential paper-then-dashboard | **OVER-SPEC-labeled** as AD-23 admission checks; live still L17 |
| AD-24..31 catalogues (envelope, grants, fencing enum, outbox, checkpoint, streams, CAS, pack pin, recipe identity) | Cheap-veto **A2–A6** + DEC-0447. Operator asked for permissions, logs, recovery, install-without-editing-core; he did not name these records | **OVER-SPEC-labeled** |
| `sess:` vs `psess:` | Sitting machinery on top of “sessions not tabs” | **OVER-SPEC-labeled** |
| Typed `change_request` hashes/CAS as the only app-use→authoring handoff | SCN-0019. Operator: create an artifact or prompt, walk it to the general copilot | **OVER-SPEC-labeled** (enabling protocol; not his words) |
| JSON-outside / Python-inside as operator-chosen stack | He said he is not technical enough; JSON vs Python is not the argument | **not presented as operator law** in ADR-0024 — good |
| React Flow / n8n OEM / SQLite WAL | Recon, not folded as law | good |
| mutmut mandated | AD-19 optional; WSL/POSIX; disposable; never `mutmut apply` | **HOLD** |
| 85 scenarios / freeze choreography | GAP-0092; catalog as oracles; do not mint 85 SCN files | **HOLD** |
| OD-02 persist `task_graph_state` / OD-03 ContributionHit | Technical defaults now DEC-0420 / DEC-0449. Operator never asked those questions | sitting defaults, folded as spine — acceptable as architect recommendations (INT-26) |
| Bot→Book→BMS→operator as **only** live shape | Overturned. Kept as **default** (DEC-0448) | **HOLD** |

Cheap-veto A1–A6 remain live (`stage_state.yaml` remaining). Operator may still overturn field catalogues without reopening ATC class, sessions≠tabs, dummy-Book, QMN venue importer, L17, sequential paper-then-live, BDD=spec, or mutmut-optional.

---

## 7. Process honesty

### 7.1 Architecture sitting (`architecture-mimi0apps`)

Confirmed from C + independent tail read:

| Claim | Status |
|---|---|
| Stage A froze `qmx-workflows-arch-2026-09-18-a` (AD-1..22), stop `AWAITING_CODEX_CHALLENGE` | true |
| Pins: docs `b8b4d21`, impl `270e992`; `8510c03` treated stale | true |
| QMA tests blocked (nested `.venv`); source-inspected | true |
| Stage C hashed Codex zip, candidate `qmx-workflows-arch-2026-09-19-c`, AD-23..31, AF-01..20, 85 scenarios kept | true |
| First C: **not** acceptance-ready pending OD-01 | true |
| Operator forbade in-session DF; recast Book/BMS; accused non-reading of Explore zip | true (Turn 7) |
| OD-01 closed from transcript re-read; DF **prompt only** | true |
| Focused Codex recheck of AD-23..31 | **skipped** — GAP-0092. Do not claim Codex approved those ADs (DEC-0447) |
| Post-OD-01 reviewer-gate re-run | **did not happen** |
| `ARCHITECTURE-CANDIDATE-MANIFEST.json` | still **`2026-09-18-a`**. Stage C never rewrote it. Fold brief already says do not fold the stale manifest as current law |
| Explore zip at Stage A | unpacked; **sampled** (L1–150, 1642–1721, 1788–1887 + searches). Full sequential read was **not** logged at A. Wrap-up re-read Book/BMS stretches after the accusation |

### 7.2 First Documentation Factory pass (this session, before this confirmation)

Honest: Explore zip was **not** re-unzipped; sitting export sampled; staged-handoff treated as already absorbed. Operator challenge was correct. This confirmation is the re-read he asked for.

Fold quality after that under-read was still rescued by: (a) architecture spine already carrying OD-01 close, (b) rider, (c) later desk-fixes on consistency review. Confirmation A/B/C now show the **operator-direct** set was not silently dropped. The risk that remains is **thinned seeds**, not inverted law.

### 7.3 Fold gates (as recorded; not re-run this confirmation)

`_docwork/stage_state.yaml` 2026-09-19 row: `status: complete`. `validate_ledger` / `validate_registry` / `validate_inventory` / `check_citations` pass; `lint_docs` clean; `lint_docs --strict` expected-blocked on mill **ADR-0023** and **SCN-0017**. Consistency FAIL-with-amendments desk-fixed. Wiring honesty at `270e992` preserved (DEC-0450).

This confirmation did **not** re-execute those gates.

### 7.4 Git

Fold is **uncommitted**. A YAML workhorse `git add -A` incident (`485d898`) was reset; HEAD is `b8b4d21` matching origin. Do not commit from this confirmation.

---

## 8. First-epic / remaining

| Item | State |
|---|---|
| First epic after docs | **FEAT-0051** (ContributionHit concatenate + pin/tombstone), blocked by FEAT-0050 / FEAT-0041 / FEAT-0046 |
| Then | FEAT-0052..0057 in inventory order |
| Not first | FEAT-0001; FEAT-0047 mill |
| Cheap-veto | A1–A6 still live |
| Codex recheck | only if operator asks (GAP-0092) |
| Epics session | operator-launched, fresh; paste already issued in the prior turn. **This confirmation does not launch it** |

---

## 9. Verdict

**CONFIRM WITH CAVEATS.**

1. **Operator-direct law is in `docs/`.** QMF one framework; no sixth COMP; Book/BMS default not ceiling; adopt-the-chain; sequential paper-then-live; QMN sole venue importer; sessions own context; app-use cannot edit; specialists remain; Portfolio Manager; marketplace dead; donors mental models; mutmut optional; BDD is specification; wiring honesty at `270e992`. L36 named amendment (DEC-0448) matches the Explore L1061 dictation and the sitting wrap-up recast.

2. **Sitting machinery is labeled.** PolicyPair field lists, fencing enum, envelope fields, pin tuple, recipe identity, checkpoint restore order are cheap-veto A1–A6, not spoken law. `psess:`/`sess:` and typed `change_request` CAS are enabling protocols on top of “sessions not tabs” and “create an artifact and walk it to the general copilot.”

3. **Paraphrases to keep honest.** “Never fake a Book” / dummy `INVALID_INPUT` was **not spoken**; it is the right mechanical reading of Kelly / no-Book / don't clash v1/v2. L17 was **not spoken**; paper + sequential + “I have to make sure it works” is compatible with existing L17. “Sensing is not ATC” is Codex/sitting sharper than Explore; the operator's Stage C paste accepted the prohibition on disguising sensing as the second trading system.

4. **Thinned seeds are not inverted law.** Readiness dashboard and three supervision modes are named GAPs (0100, 0099). Messy board chrome, default node catalogue, Islam-as-settings, two MIS versions, loops-as-mini-apps, Artifact Library “database” slogan, LSE surface, WF1/WF2 birth story stay later/optional under INT-28. Do not treat them as refused.

5. **Process holes stay named.** Focused Codex recheck of AD-23..31 never ran (GAP-0092). Freeze manifest still says `2026-09-18-a`. First DF pass did not re-read the Explore zip; this grok-4.6 confirmation did.

**No blocking miss. Do not re-fold. Do not start epics from this file.**
