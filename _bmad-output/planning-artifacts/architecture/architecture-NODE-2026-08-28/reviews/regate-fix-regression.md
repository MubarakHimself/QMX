# Re-gate — Fix-pass regression check (FRESH lens)

**Target:** `ARCHITECTURE-SPINE.md` (Trading Node, architecture-NODE-2026-08-28), 951 lines, TN-1..TN-25, `status: draft`.
**Lens:** FIX-PASS REGRESSION CHECK — verify every `reviews/fix-pass-1.md` amendment (243 rows + operator round) is present in the current text; verify the six first-gate reviews' CRITICAL and HIGH findings are each closed; run the mechanical checks.
**Date:** 2026-08-28.
**Verdict:** CONDITIONAL PASS — the fix pass and the operator round are faithfully applied and every reviewed CRITICAL/HIGH is closed in the current text; ONE HIGH contradiction survives (an operator-round straggler in the load-bearing Inherited Invariants table), plus two LOW nits. No CRITICAL. Close H-1 and re-gate is clean.

---

## 1. Mechanical checks — ALL PASS (one LOW note)

| Check | Result |
| --- | --- |
| Every TN-1..TN-25 carries **Binds** / **Prevents** / **Rule** | PASS — 25/25, exactly one each (the second `**Rule:**` the scan sees after TN-25 belongs to the "Dependency direction" block, not TN-25) |
| No `<!--` anywhere | PASS — 0 occurrences |
| Balanced mermaid fences | PASS — 6 ```mermaid + 1 ```text = 7 opens / 7 closes, 14 fence lines total |
| Every mermaid block has ≥1 edge | PASS — edge counts 19 / 13 / 16 / 20 / 15 / 10 |
| Stack table has a version on every row | PASS with LOW note (L-2): three rows carry no version literal by design — `click` (a deliberate **NOT TAKEN** row), `just` (external repo tool), and the observability stack (**seed only**, versions pinned at the implementation gate). Each states why; none is an accidental blank |
| Registry mint table lists every configurable variable named in a TN | PASS — every newly node-minted `configurable`/do-not-default variable named across TN-4..TN-25 appears in the mint table (lines 663-688). Tokens in TN bodies but absent from the table are all either non-variables (command kinds, event/close-reason enums, fold/field/function names) or pre-existing ratified keys not being newly minted (`kill_line_capital_floor` @ variables.yaml:548, `holdout_months` @ ct-14:18) |

Vocabulary sweep: banned words (`engine`, `kernel`, `plugins`, `exam`, `minimal core`, `paper node`, `timeframe`) appear ONLY inside their own prohibition sentences (lines 127, 702). Withdrawn command forms (`Door 2`, `qmn CLI`, `qmn deploy/secrets/config/data/replay/notify/registry`) — 0 occurrences. The three `CLI` tokens are all licit: the withdrawn-note (129), the word "CLICK" (543), and the Stack no-CLI-framework row (718). Door numbering is clean: FIRST/SECOND/THIRD DOOR, no literal "Door 2".

## 2. Fix-pass-1 rows (243) — PRESENT

Every structural addition and every C/H/M/L row I sampled resolves to concrete current text. All 15 CRITICAL and 43 HIGH rows verified individually (see §3). Representative M/L confirmations: `qa/` tree + `FAILURES.md` (adv:L4 → lines 765, 768); governor budgets (rubric:M12 → 685); sealed-period final look (parent:M21 → 492); Records↔CT-13 bridge (inputs:M2 → 450); provisioning privilege path (ops:M3 → 405); two RTO numbers (ops:M8 → 423); `--with-key=host` (currency:F5 → 405); raw sd_notify over AF_UNIX datagram (currency:F4 → 205). The single documented deviation (doors kept ordinal *words* rather than literal numerals to satisfy the zero-"Door 2" grep) is present as described and is internally consistent. **No fix-pass row found MISSING or PARTIAL.**

## 3. Six first-gate reviews — CRITICAL/HIGH closure

Actual finding-id counts in the review files reconcile to the fix-pass table (NOT the memlog gate headline, which over-counted parent-consistency H at 15 and ops-security H at 7):
- rubric 3C (C1-C3) / 8H (H1-H8) — closed: TN-8:301, TN-12:402, TN-7:290, TN-25, TN-11:385, TN-6:242 + TN-7:288, TN-2:140 + TN-4:211, TN-3:155/TN-12:403, TN-15:452/456, TN-19:524, TN-17:491.
- adversarial 7C (C1-C7) / 15H (H1-H15) — closed: entry-side block TN-6:238, stand-down enactable TN-4:209, refresh-by-ref TN-12:404, config partition TN-18:509, ordinal≠sequence TN-6:244, KSA monotone TN-7:286, arithmetic domain TN-10:342; H1-H15 all present (pacer bucket TN-22:569, WriterId TN-2:145, accumulator single-first-writer TN-5:223, safe point TN-4:212, roster eligibility TN-19:525, registry schema-only TN-18:510, replay import port TN-21:555, wire-handoff deadline TN-6:246, drift-on-role TN-10:345, SQS-in-snapshot TN-19:528, baseline keyed TN-8:305, hub split TN-3:159, three holders TN-12:406, kill line per-binding TN-8:301, timer ceremony TN-2:146).
- parent-consistency 4C (C-1..C-4) / 11H (H-1..H-11) — closed: drain never-auto TN-7:290, state_carry TN-25:619/TN-18:515, transport locus qmf-venue increment TN-11:383, one-way replay import port TN-21:555; H-1..H-11 all present (virtual-vs-venue TN-25:614, netting bind-time TN-22:567, ratchet origination TN-8:306, flatten authority TN-24:600, CT-30 vocab TN-7:287, gate entries-only TN-6:243, standing-intent machinery TN-7:291, amend atomicity 6th check TN-10:332, port conflict-surfaced TN-11:385, risk-domain writer TN-2:145, slice frontier TN-5:224).
- inputs-reconcile 1C (H1)/... value-status TN-18:511; venue conformance double TN-23:581 — closed.
- ops-security 1C (C1) / 6H (H1-H6) — closed: payload-key escrow + clean-host rehearsal TN-12:402/TN-13:422; dead-man's switch TN-15:454; allow-list reconciled TN-15:453; disk_headroom_min TN-13:425; doors-before-preflight TN-2:140; config init/validate (now toolkit recipes) TN-17:497; FAILURES.md CI gate TN-23:583.
- currency 0C / 1H (F1 fixed `User=qmx`) TN-16:470 — closed.

**All CRITICAL and HIGH findings from all six reviews are closed by current spine text.**

## 4. Remaining divergence (introduced/left by the operator round)

### H-1 (HIGH) — Inherited Invariants row still calls the shadow lane "deferred," contradicting TN-19's operator-round elevation to V1
**Line 96** (load-bearing Inherited Invariants table, PRD §6 row that BINDS TN-19) reads: *"The **shadow lane is a NAMED SEAM, deferred** (TN-19)…"*. The operator round (memlog entries 48-49, fix-pass operator amendment #13) elevated the seam to V1: **TN-19 line 532** — *"THE SHADOW-LANE SEAM IS EXPLICIT V1 NODE WORK — three pieces, built now"* — and the Deferred table **line 877** — *"the seam, the shadow stream and the comparison read model are built now, the live binding is not."* The binding row was not propagated. A builder scoping from the authoritative binding table reads "shadow lane… deferred" and defers the seam TN-19 mandates building now — a V1-vs-follow-on scope split between two load-bearing statements.
**Fix:** change line 96 to read, e.g., *"The shadow-lane **seam is explicit V1 node work** (TN-19) — candidate-labeler registration, the shadow snapshot stream and the comparison read model — while its **ML/training half is deferred**; the live-runtime guardrail binds now: no ambient randomness in the live runtime, and a recovered or pre-trained model carries no authority without fresh ratification."

## 5. LOW nits (rolled into counts)

- **L-1** — Line 604 uses the bare phrase *"a venue stop-out or margin liquidation"* while the Naming convention (line 702) bans *"the bare word 'stop-out'."* Self-inconsistent gloss. Fix: *"a venue liquidation or margin liquidation"* or drop the bare word, keeping the typed `venue_liquidation`.
- **L-2** — Stack rows `just` and the observability stack carry no pinned version literal (external tool / seed-only pinned-at-implementation-gate). Deliberate, but if the mechanical rule is read strictly, add "external tool, pinned in DEPENDENCIES.md at the implementation gate" as an explicit version cell for both so no row is literally blank.

---

## Counts

| Severity | Count |
| --- | --- |
| Critical | 0 |
| High | 1 |
| Medium | 0 |
| Low | 2 |

Fix pass faithful, six gates' criticals/highs all closed, mechanical checks green. Close H-1 (line 96) and the spine is certifiable; L-1/L-2 are optional polish.
