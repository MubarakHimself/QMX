# Contradiction sweep — docs/ internal consistency

Sweep date: 2026-08-21. Scope: `docs/` only (constitution, contracts, components, ADRs, glossary, index, changelog, registry/variables.yaml, architecture docs, scenarios, traceability, gap report, AGENTS.md, lenses spot-checked). Purpose: gate the operator's corpus sign-off (provisional -> signed-off). Per the brief, known/tracked items were excluded: the changelog's open coordination questions (CT-29 resolved-entry keying shape, the UI display name, the NN/ML weights kind), the surfaced SQS-formula memlog conflict, deferred gaps GAP-0016/0017/0048/0049, and DEC-0049.

## Verdict

Three NEW internal contradictions found — one major, two minor. Everything else checked out clean.

---

## Finding 1 (MAJOR) — CT-28 says the binding `world` is "live, the only V1 value"; QMB is ratified to mint `world = replay` CT-28 bindings

**The contract side** — `docs/contracts/ct-28-book-binding.yaml`:

- Line 23 (invariant): "`world` is a constant `live` for every V1 binding…"
- Line 46 (field): "world: a constant `live` in V1; a replay mints a different binding identity and is incomparable by binding"
- Line 58 (enum): "world: live (the only V1 value; `simulated` is unlocked by the deferred backtesting sitting)" — **`replay` is not even enumerated as a legal value, ever**
- Line 73 (nullability): "world is never null; it is the constant `live` in V1…"

**The component/scenario side** — all live, current-state, ratified-by-absorption text:

- `docs/components/qmb.md` line 45 (interface table): "Book binding record (one `world = replay` binding per run) | out (minted) | CT-28"
- `docs/components/qmb.md` line 23 (authority boundary, May): "mint exactly one AD-29 binding with `world = replay` per run" (DEC-0160)
- `docs/scenarios/SCN-0012-qmb-replay-run.md` line 43: "**(3) A `world = replay` AD-29 binding is minted.** Exactly one binding per run… and the world is `replay`."
- `docs/contracts/ct-13-journal.yaml` line 30: "the run's trade record IS the CT-29 exit-record stream of the run's **replay binding**"
- `docs/contracts/ct-32-performance-result.yaml` line 9: QMB is the intended producer, its results citing the replay binding's stream.

**The reconciliation the rest of the corpus already made, which CT-28 missed:** the QMB absorption rewrote the glossary and qmf-risk.md with a "live-path" scope qualifier —

- `docs/glossary.md` (Binding identity, line 62): "a constant `live` for every **live-path** V1 Book binding — a QMB replay run mints its own `world = replay` binding (DEC-0160), a different binding identity"
- `docs/components/qmf-risk.md` line 60: "`world` is the constant `live` for every **live-path** V1 binding; a QMB replay run mints its own `world = replay` binding (DEC-0160)"

CT-28 was not touched by the QMB absorption (the changelog's QMB entry lists only CT-32, CT-13, and CT-11 as amended contracts), so it still carries the unscoped risk-sitting wording. As written, an implementer validating CT-28 against its own enum ("live is the only V1 value") would refuse every QMB run's binding — the exact record qmb.md declares QMB mints per run. Two live places assert incompatible things about the same normative field.

**Suggested fix (for the operator, not applied):** scope CT-28's four `world` statements to "live-path V1 binding" (matching glossary/qmf-risk) and add `replay` to the enum as the QMB-composition-root value (`simulated` still locked behind GAP-0048). A one-file edit; no ruling change needed — DEC-0160 already made the call.

---

## Finding 2 (MINOR) — index.md's current-state descriptions still call the venue command vocabulary "four-kind"; CT-19 ratifies exactly five

- `docs/index.md` line 80: "[CT-19 — venue command] — defines the **four-kind** command vocabulary, command identity, and the injective client-id mapping (DEC-0137)."
- `docs/index.md` line 47: "[QMF Venue] — specifies the ratified venue-neutral adapter module: the secret lifecycle, **four-command** uncertainty law, and one-port four-contract adapter…"

versus the ratified current state:

- `docs/contracts/ct-19-venue-command.yaml` line 19: "Command vocabulary is exactly **five kinds** — place_order, cancel_order, close_position, close_all, and amend_protection (the fifth, minted 2026-08-20…)" (also its purpose line 15: "exactly five typed command kinds")
- `docs/components/qmf-venue.md` line 65: "The command vocabulary is exactly **five kinds**…"
- `docs/architecture/overview.md` line 213: "the five command kinds are place_order, cancel_order, close_position, close_all, and amend_protection"
- `docs/components/ctrader.md` line 35: "Venue command shape (five kinds)"
- `docs/lenses/security/security-model.md` line 31: "a fixed **five-kind** vocabulary"
- `docs/components/qmf-risk.md` FM-4 (line 198): "the five-kind command vocabulary"

The index rows are current-state summaries of what those files contain, and they misstate the contract they link. Same-lineage but **defensible as dated sitting records** (not reported as defects): `docs/changelog.md` line 76 ("CT-19 v1 (four command kinds…)" — the venue-sitting entry, correct at that date, with the risk entry recording the fifth mint), `docs/gap-report.md` GAP-0036 row (records DEC-0137's answer as ratified at the venue sitting; GAP-0040 in the same table records the fifth mint), `docs/AGENTS.md` line 22 (the "ratified venue content" chronology, corrected by line 23's "amend_protection as the fifth venue command"), `docs/architecture/stack.md` line 140 (an answered-GAP note in the same dated style), and ADR-0007 (immutable-ADR convention; ADR-0008 carries the fifth command).

**Suggested fix:** update index.md lines 47 and 80 to "five-kind"/"five-command (amend_protection the fifth, DEC-0148)". Optionally add the same clause to stack.md line 140.

---

## Finding 3 (MINOR) — overview.md contradicts itself on CT-22/CT-23 format versions (v1 in two sections, v2 in a third)

- `docs/architecture/overview.md` line 209 (Runtime and data shape): "CT-22 through CT-25 and CT-27 through CT-32 are the ratified Risk boundaries (AD-29 through AD-41), **filled and minted at format version 1** as defined-unwired surface"
- `docs/architecture/overview.md` line 221 (COMP-QMF-RISK section): "CT-22 through CT-25 are filled and CT-27 through CT-32 are minted **at format version 1** as defined-unwired surface"

versus, in the same document:

- `docs/architecture/overview.md` line 304 (Contract authority): "CT-22 and CT-23 now sit at **format version 2** after the 2026-08-21 AD-5 format mints — superseding their format-1 fill — with pre-mint format-1 artifacts readable forever (DEC-0181, DEC-0182)."

and the contracts/corpus: `docs/contracts/ct-22-book-charter.yaml` line 4 (`version: 2`), `docs/contracts/ct-23-risk-evaluation.yaml` line 4 (`version: 2`), `docs/components/qmf-risk.md` line 95 ("CT-22 and CT-23 sit at contract format version 2 after the 2026-08-21 AD-5 format mints"), and the changelog's QML entry. The QML absorption updated overview line 304 but left lines 209 and 221 asserting v1 as current state.

**Suggested fix:** add "(CT-22 and CT-23 since re-minted at format version 2 by the 2026-08-21 QML increment, DEC-0181/DEC-0182)" at lines 209/221, or reword both to "first minted at format version 1".

---

## Checked and found clean (non-exhaustive highlights)

- **Constitution vs contracts/components:** L30 default-deny + roster-scope annotation is consistently mirrored in AGENTS.md, CT-06, dependencies.yaml (QMB imports six backend components, QML imports core/registry/risk, neither imports venue); L36 authority order verbatim everywhere; L38 configurable-means-UI-editable consistent with every variables.yaml row (pins marked configurable:false, all risk figures configurable:true, no restated literals); L39 exit-preservation consistent across CT-19/CT-30/glossary/qmf-risk.
- **CT-33/CT-34 vs glossary/qmf-registry/CT-06/dependencies.yaml:** ownership (qmf-registry) vs authorship (QML), the six content groups, identity carve-out, cardinality-one family, transitive-union footprint law, fingerprint-ascending ordering, and the DEC-0185 veto-round riders (leg may carry both a producer binding and a child cite; adopt-the-bot's-advisory-stop module mode; no `qml` CLI) are consistent across CT-34, CT-22 v2, CT-23 v2, qml.md, qmf-risk.md, ADR-0018, glossary, and changelog.
- **CT-22 v2 / CT-23 v2 change lists** match one another and the changelog exactly (two evidence_requirements fields + exit_policy catch-all + footprint_requirements shape; one optional advisory_stop_proposal field + Book-resolved full-loss documentation).
- **CT-29 close-reason taxonomy** (12 members) identical in glossary, CT-29, qmf-risk.md; the CloseReason evidence mapping lives only in CT-29 as required; closing_authority/adapter_self boundaries consistent with CT-30/CT-32.
- **Worlds vocabulary** (live/replay/simulated; account role carries money-reality; simulated reserved-unusable) consistent across glossary, overview, qmf-data, CT-13, CT-32, QMB docs — except the CT-28 enum (Finding 1).
- **Gap arithmetic:** 45 answered (13+4+11+4+4+8+1), 4 deferred (16/17/48/49) — consistent across index, gap report, AGENTS.md, changelog, traceability; GAP-0047 answered everywhere; CT-06 still carries gaps [GAP-0016, GAP-0017] as the deferral requires; dead-decision count (18) matches its table.
- **Corpus count:** index's "102 files: 66 Markdown and 36 YAML" verified by actual file census.
- **Vocabulary bans:** no live use of "BotSpec", "archetype", bare "timeframe", "engine/kernel" for QMB/QML, or "snapshot" for registry state (all remaining hits are the sanctioned senses: state snapshots, metadata snapshots, "Authority snapshot" table labels, retired-name entries).
- **Interfaces cross-check:** qmb.md and qml.md interface tables match dependencies.yaml's COMP-QMB/COMP-QML interface lists one-for-one; COMP-QMF-REGISTRY carries CT-33/CT-34 as the changelog claims.
- **Traceability:** DEC-0170/0171–0185 rows present and consistent with changelog/ADR-0017/ADR-0018; the CT-19 fifth-command row (line 375) is correct.
- **QMB pins/governor rows** (click==8.4.2, optuna==4.9.0, governor/limit/staleness) consistent between variables.yaml, qmb.md, stack.md, changelog.

## Excluded as known/tracked (not re-reported)

- Changelog coordination question (i): CT-29 resolved-entry keying field shape (operator-aligned deferred) — CT-29 line 32 self-declares it as the open changelog item.
- The SQS-formula memlog conflict (variables.yaml `spread_quality_sensor_formula` carries the operator caveat verbatim).
- GAP-0016/0017/0048/0049 deferrals and every doc restating them.
- DEC-0049 (automatic detector action), still `open` in the gap report by design.
- The UI display name and NN/ML weights-kind open questions (non-blocking, recorded in changelog/ADR-0018/qml.md consistently).
