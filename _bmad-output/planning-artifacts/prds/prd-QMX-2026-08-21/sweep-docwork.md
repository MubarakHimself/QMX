# Docwork contradiction sweep — corpus sign-off gate

Date: 2026-08-21. Scope: `_docwork/` (ledger.yaml, manifest.yaml, feature_inventory.yaml, gaps.yaml, stage_state.yaml, extractions.yaml, enhancements.yaml, ratification-packet.md, final-validation.md) swept against `docs/`. Verdict: **findings — 1 major (mechanical), 2 minor**. Nothing invalidates the corpus content; the major item should be fixed before the sign-off flips provisional statuses.

## 1. Counts and cross-references — VERIFIED

| Claim | Checked against | Result |
|---|---|---|
| DEC range to 0185, contiguous, no duplicates | `_docwork/ledger.yaml` | **Holds.** 185 entries, DEC-0001..DEC-0185, gapless. Statuses: 86 ratified, 53 provisional, 18 superseded, 18 dead, 9 out-of-scope, 1 open (DEC-0049 — matches gap-report.md:183 "only one open ledger decision remains"). |
| 45 answered gaps | `_docwork/gaps.yaml` vs docs | **Holds.** 49 gaps total: 45 `answered`, 4 `deferred` (GAP-0016/0017 per DEC-0121, GAP-0048 content-half, GAP-0049). Matches gap-report.md:18/:243 ("45 answered"), AGENTS.md:17 ("answer 45 gaps") and AGENTS.md:107 (44 + a 45th). |
| FEAT-0001..0030 | `_docwork/feature_inventory.yaml` | **Holds.** 30 entries. FEAT-0029 blocked_by FEAT-0027/0015/0016/0020/0022 and FEAT-0030 blocked_by FEAT-0005/0007/0027 — exactly as stage_state.yaml claims. |
| EXT range | `_docwork/extractions.yaml` | **Holds.** 523 entries, tail EXT-2091 (QML) + EXT-2092 (veto round; full rider text present, `authority: rider`). |
| Supersession chains | ledger forward/back pointers | **18 of 20 hold** (status `superseded` + `superseded_by` back-pointer). **Two broken — see finding F1.** |
| Sources SRC-01..SRC-10 registered | `_docwork/manifest.yaml` | **Holds.** All ten present with harvest notes; SRC-09/SRC-10 (QML sitting + transcript) registered as stage_state claims. |
| docs/index.md file count | filesystem | **Holds.** 102 files = 66 .md + 36 .yaml, exactly as index.md:18 states. |
| Constitution laws L1..L39 | docs/constitution.md | **Holds.** All 39 present, including L36–L39 from the risk sitting. |
| DEC-0170 (Dukascopy personal-use ruling) | ledger:1587 vs qmb.md:109/:216 | **Holds.** Ruled closed, personal-use only, license-tag mechanism unchanged; qmb.md's former open/closed contradiction is fixed (reads closed with DEC-0170). |
| "pending(bot-schema sitting)" residue | docs sweep | **Holds.** Survives only in negation/historical contexts (qmf-risk.md:83, ct-22:23, glossary:390/:490), as stage_state's final-sweep claim states. |

## 2. DEC-0185 riders — VERIFIED IN DOCS

DEC-0185 (ledger:1722, ratified, operator-direct, sourced EXT-2092) is fully reflected:

- **Rider A (CT-34 leg may carry BOTH producer binding and child-confluence cite; counts never bounded):** ct-34-confluence.yaml:27 (counts-NEVER-bounded invariant, cites the veto round + DEC-0185), :28, :42, :51, :57 (both-allowed, at-least-one-required, role mandatory).
- **Rider B (bot-owned exit methodologies first-class; adopt-the-advisory-stop module mode inside `{module_id, config}`, no format change, no CT-23 inbound-refusal posture):** ct-22-book-charter.yaml:31 (adoption-mode invariant, "format stays 2"); ct-23-risk-evaluation.yaml:42 ("NO inbound-refusal posture exists", DEC-0185); qmf-risk.md:95; glossary.md:34 (advisory-stop entry carries both riders' language).
- **Ruling C (no second CLI; QMB's `qmb` is the single command-line surface):** qml.md:19 and qml.md:165 (deferred table: "RULED by the operator veto round: no second command line, ever in this shape").
- **Changelog asked-vs-ruled history:** changelog.md:28 records all three coordination questions with the VETO ROUND HELD outcome — (iii) resolved by Rider A, (ii) resolved by Rider B, (i) CT-29 keying operator-aligned deferred; `qml` CLI ruled out; UI name open with the read-only-when-live lean; NN-weights kind still open. traceability.md:260 has the DEC-0185 row; ADR-0018 carries the dated follow-up; AGENTS.md frontmatter and qml.md frontmatter include DEC-0185.
- **CT-29 (the deferred third question):** ct-29-exit-record.yaml:32 correctly states the resolved-entry-keying semantics are ratified but "the exact field shape of that keying is NOT minted here" and points at the changelog's coordination item — consistent with DEC-0185's deferred-with-note. No stale "unresolved" language anywhere else.

## 3. Findings

### F1 (major, new, mechanical): ledger status fields for DEC-0056 and DEC-0124 never flipped to `superseded`

- `_docwork/ledger.yaml:526` — DEC-0056 ("Light and heavy indicator split") is `status: provisional`, no `superseded_by` field.
- `_docwork/ledger.yaml:1166` — DEC-0124 ("Freeze-choice status after the foundation sitting") is `status: ratified`, no `superseded_by` field.
- Yet the forward edges exist — ledger:1208 `DEC-0128 supersedes: [DEC-0056]`, ledger:1263 `DEC-0134 supersedes: [DEC-0124]` — and every doc treats both as superseded: stage_state.yaml:68 ("DEC-0056 superseded by DEC-0128; DEC-0124 superseded by DEC-0134"), changelog.md:90, traceability.md:79 (DEC-0056 marked `superseded`), traceability.md:154 (DEC-0124 marked `superseded`), ADR-0006:34, AGENTS.md:21, qmf-indicators.md:90, gap-report.md:226/:231/:232.
- All 18 other supersession chains carry the full pattern (target `status: superseded` + `superseded_by` back-pointer). These two are the only exceptions — the indicators/structure absorption's desk-fix wave repaired the *citations* ("superseded DEC-0124/DEC-0056 cited as live", stage_state.yaml:81) but missed the ledger's own status fields.
- **Why it matters at sign-off:** the sign-off flips provisional→ratified. As it stands DEC-0056 (provisional) would be *ratified* while DEC-0128 (already ratified) supersedes it — two live decisions giving contradictory light/heavy classifications (role-based vs budget-declared/benchmark-policed). DEC-0124 (ratified) contradicts DEC-0134 (ratified) on the freeze-choice count (three-of-six vs four-of-six) whenever both read as live.
- **Fix:** two-field mechanical edit in ledger.yaml — set both to `status: superseded` and add `superseded_by: DEC-0128` / `superseded_by: DEC-0134`. Classify: **fix before sign-off** (cheap; no doc text changes needed — docs are already right).

### F2 (minor, new): changelog risk-increment row cites the wrong memlog range

- docs/changelog.md:58 says "Memlog entries 85–124 of the architecture sitting workspace".
- The canonical bullet numbering (verified by counting bullets in `architecture-QMX-2026-08-19/.memlog.md`: sitting-reopen bullet = 84, GAP-0043 ruling = 95 matching DEC-0153's rationale, gate-amendments = 111, backtesting dictation = 118) makes the risk sitting **entries 84..116**, exactly as stage_state.yaml:107 and manifest.yaml SRC-06 note state. "85–124" also overlaps the backtesting-direction entries (117+) that belong to the next increment, and contradicts the changelog's own venue row (63–83, correct). Provenance-pointer typo only; no decision content affected. Rides the docs process.

### F3 (minor, note): ratification-packet.md and final-validation.md are frozen 2026-08-18 snapshots

- `_docwork/ratification-packet.md` (Stage-4 packet: "All 45 items below remain open and blocking", DEC-0040/DEC-0067 presented as unresolved conflicts) and `_docwork/final-validation.md` ("98 decisions: 55 provisional, 8 open, 2 conflict…") predate every increment. Both self-declare their date and non-signature status, so they are not contradictions — but **neither is a usable sign-off instrument** for the current corpus (185 decisions, 45 answered gaps, 0 blocking, conflicts resolved). If the operator's sign-off ceremony reads a packet, it must be regenerated from the current state (changelog + gap-report + stage_state are the live surfaces). Rides the docs process. Similarly, stage_state.yaml:39-47 `final_gate` ("45 unique blocking gaps") is a point-in-time 2026-08-18 record, superseded in substance by the change_mode rows beneath it.

## 4. Tracked leftovers — classification

### SQS-formula memlog conflict — SIGN-OFF AGENDA ITEM (one-line operator ask), not a docs defect

- The conflict: memlog bullet 118 (the 2026-08-20 backtesting-direction dictation, *later the same day* than the risk sitting's round-3 ruling at bullet 95) says "SQS formula stays open pending re-understanding pass" — while DEC-0153 (ledger:1432, ratified, supersedes DEC-0075) adopts the old ratio sensor as SQS V1, GAP-0043 `answered` (gaps.yaml:422), with the operator's caveat recorded verbatim ("it was some agent's idea, not mine — go with it").
- Docs are internally consistent: SQS V1 ratified everywhere (qmf-risk, index, AD-39), the v2 depth/L2 seam named, and QMB's modeled-spread reconciliation with DEC-0153 parked as a GAP-0048 pending item (DEC-0169, ledger:1580). No docs file mentions "re-understanding" — the conflict lives only memlog-vs-ledger and is flagged in stage_state.yaml:125 and :145 ("surfaced, unresolved").
- Classification: **cannot ride the docs process** (only the operator resolves it), but it does **not block** the sweep or make the corpus contradictory. It belongs as the first cheap-veto question at the sign-off conversation: *confirm DEC-0153's ratio-sensor V1 stands (with the re-understanding pass as a future GAP-0048/SQS-v2 concern), or reopen GAP-0043.* Signing off silently would ratify DEC-0153 against the operator's later-in-the-day remark — under DEC-0001 (later rulings govern) that remark deserves an explicit disposition.

### Three QML coordination questions — RESOLVED (two) / DEFERRED-BY-RULING (one); docs verified

- (iii) CT-34 leg cardinality — resolved by Rider A; in ct-34. (ii) CT-23 inbound full-loss price — resolved by Rider B; in ct-22/ct-23/qmf-risk/glossary. (i) CT-29 resolved-entry keying field shape — operator-aligned deferred by DEC-0185; ct-29:32 states exactly that. **Nothing blocks; nothing rides unresolved.** Residual open items (UI display name with the read-only-when-live lean; NN-weights parameter kind) are recorded non-blocking platform/later-mint territory in changelog.md:28 and qml.md:165.

### Pending ENH backlog (71 entries) — RIDES the docs process

- `_docwork/enhancements.yaml`: 71 entries, all `status: pending`, all of one class — disclosed *agent additions beyond verbatim spine/ledger content* during the change-mode absorptions (schema field decompositions, boundary notes, extra invariant cites). None is a contradiction; none is blocking; lint_docs_strict already counts the batch among its expected-blocked reasons (stage_state.yaml:123). At sign-off the operator implicitly blesses the corpus text containing them; the backlog remains the register for later trims/ratifications. **Non-blocking; ride.**

## 5. Bottom line for the sign-off gate

1. **Fix F1 first** (two ledger status fields) so the provisional→ratified flip cannot resurrect DEC-0056/DEC-0124 as live. Mechanical, no doc prose changes.
2. Put the **SQS confirm-or-reopen question** on the sign-off agenda (one line, cheap veto).
3. F2 (changelog memlog range) and F3 (regenerate the sign-off surface; don't sign the 2026-08-18 packet) ride the docs process.
4. Everything else verified clean: counts, ranges, supersession chains (18/20), DEC-0185 riders, coordination questions, ENH backlog, GAP catalog state.
