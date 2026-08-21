# Corpus sign-off mechanics — provisional → signed-off flip plan

Prepared 2026-08-21 by the sign-off-mechanics planner (sweep workflow, no contradiction hunting).
Condition being recorded: **operator sign-off 2026-08-21, given as a conditional go-ahead in the
PRD session, contingent on the independent contradiction sweep (this workflow) passing.**
The flip executes ONLY after the sweep's pass verdict is recorded; the wording below assumes that
verdict exists and cites it.

---

## 1. Current state (measured, 2026-08-21)

- **100 files** under `docs/` carry `status: provisional` frontmatter: **66 Markdown** documents
  (the lint-enforced set) and **34 contract YAMLs** (`docs/contracts/ct-01..ct-34`, not scanned by
  `lint_docs.py` but part of the same status vocabulary).
- `_docwork/ledger.yaml`: 185 decisions — **53 provisional**, 86 ratified, 18 superseded, 18 dead,
  9 out-of-scope, **1 open (DEC-0049)**, 0 conflict.
- Two ledger status inconsistencies found (validator does not catch them):
  - **DEC-0056** carries `status: provisional` but DEC-0128 declares `supersedes: [DEC-0056]`
    (stage_state's indicators/structure row also records the supersession).
  - **DEC-0124** carries `status: ratified` but DEC-0134 declares `supersedes: [DEC-0124]`
    (stage_state's same row records it).
- `_docwork/gaps.yaml`: 45 answered, 4 deferred (GAP-0016/0017/0048/0049), **zero blocking**.
- `_docwork/enhancements.yaml`: **71 ENH entries, all `status: pending`** — each one is a strict-lint
  error by design.
- `_docwork/stage_state.yaml`: `provisional: true`; `ratification: {status: provisional,
  by: operator-pending, date: 2026-08-18}`; `final_gate` block stale (2026-08-18 snapshot).
- Gate baseline (all run read-only today):
  - `validate_ledger.py` → PASS
  - `validate_registry.py` → PASS
  - `validate_inventory.py` → PASS with house-accepted warnings (FEAT-0009 ordering heuristic;
    11 ratified component-scoped decisions feature-unassigned)
  - `check_citations.py` → PASS with the house-accepted dead-DEC frontmatter warning class
  - `lint_docs.py` → PASS (`OK: docs lint clean`)
  - `lint_docs.py --strict` → **137 errors = 66 provisional .md docs + 71 pending ENH entries.
    Nothing else.** (Zero blocking-gap references, zero staleness, zero provenance-field errors.)

## 2. Validation tooling (exact commands)

The gates live in the documentation-factory skill, not in the repo:

```
python C:/Users/Mubarak/.claude/skills/documentation-factory/scripts/validate_ledger.py    --root C:/Users/Mubarak/Desktop/QMX
python C:/Users/Mubarak/.claude/skills/documentation-factory/scripts/validate_registry.py  --root C:/Users/Mubarak/Desktop/QMX
python C:/Users/Mubarak/.claude/skills/documentation-factory/scripts/validate_inventory.py --root C:/Users/Mubarak/Desktop/QMX
python C:/Users/Mubarak/.claude/skills/documentation-factory/scripts/check_citations.py    --root C:/Users/Mubarak/Desktop/QMX
python C:/Users/Mubarak/.claude/skills/documentation-factory/scripts/lint_docs.py          --root C:/Users/Mubarak/Desktop/QMX
python C:/Users/Mubarak/.claude/skills/documentation-factory/scripts/lint_docs.py          --root C:/Users/Mubarak/Desktop/QMX --strict
```

There are **no** validate/lint scripts inside `C:/Users/Mubarak/Desktop/QMX` itself
(`_docwork`, `_bmad/scripts`, `tools/` checked; `_bmad/scripts` holds only BMad config/memlog
helpers). Every stage_state gate reference resolves to the skill scripts above.

House status vocabulary (`lint_docs.py`): `draft | reviewed | ratified | provisional`.
The sign-off flip target is therefore **`status: ratified`** — no "signed-off" value exists.
`lint_docs --strict` additionally requires: no `provisional` status, no pending ENH entries,
no doc-body references to `blocking: true` gaps (already zero), frontmatter
`sources/generated/stale_after` present (already present everywhere).

## 3. The flip plan, file by file

Execute in this order. **Step 0 is the condition itself.**

### Step 0 — preconditions (do not start without them)
1. The independent contradiction sweep reports **pass**, and its verdict (date + workflow id) is
   in hand to cite.
2. Commit the currently uncommitted QML-increment + veto-round working tree first, so the
   sign-off flip lands as its **own commit** with a clean audit trail.

### Step 1 — `_docwork/ledger.yaml` (fix-first, then flip)
- **DEC-0056**: `status: provisional` → `status: superseded`, add `superseded_by: DEC-0128`
  (required by `validate_ledger` for superseded entries). This is a correction, not a ratification.
- **DEC-0124**: `status: ratified` → `status: superseded`, add `superseded_by: DEC-0134`. Same.
- **The remaining 52 provisional entries** (DEC-0001..0098 subset: 0001–0009, 0011, 0013, 0017,
  0019, 0022, 0024–0031, 0033, 0035, 0038, 0039, 0041, 0042, 0044–0046, 0048, 0051–0055, 0058–0061,
  0065, 0066, 0068, 0074, 0076, 0078, 0080, 0092, 0096–0098 — i.e. the 53 listed minus DEC-0056):
  `status: provisional` → `status: ratified`. No other field changes; the event record lives in
  stage_state + changelog, matching how sitting-ratified entries carry no per-entry signature.
- **DEC-0049 stays `open`.** Do not flip it. It is the only open ledger row (automatic detector
  action: notify-versus-mutate authority). Surface it to the operator for an explicit ruling or an
  explicit "stays open past sign-off" acknowledgment.

### Step 2 — docs frontmatter (the lint-enforced flip)
- All **66** `docs/**/*.md` files: frontmatter `status: provisional` → `status: ratified`.
- All **34** `docs/contracts/ct-*.yaml` files: `status: provisional` → `status: ratified`.
  (Not lint-scanned, but the corpus keeps one status vocabulary; leaving contracts provisional
  while their owner docs read ratified would mint a fresh internal contradiction.)
- Do **not** bump `verified:` on files receiving only the status flip; bump `verified: 2026-08-21`
  only on files whose body text changes (Steps 4–6).

### Step 3 — contract version-comment lines (19 files)
`ct-16` through `ct-25`, `ct-27` through `ct-34` carry a line-4 comment ending
"…the doc stays provisional pending (operator) corpus re-ratification". Replace that clause with:
`corpus signed off by the operator 2026-08-21`. These comments were forward-looking gates whose
condition is now met; fulfilling them is not history-rewriting.

### Step 4 — ADR status lines (18 files)
Every `docs/decisions/ADR-00NN-*.md` carries a body line
"Date: … Status: provisional pending …". Per the immutable-ADR convention, keep the original
Date clause verbatim and update only the Status clause, to:

> Status: ratified — corpus signed off by the operator 2026-08-21 (conditional go-ahead given in
> the PRD session, contingent on the independent contradiction sweep passing; the sweep passed).

The "pending operator ratification / pending corpus re-ratification" wording anticipated exactly
this event, so the edit fulfills the recorded condition rather than rewriting a decision record.

### Step 5 — load-bearing prose banners
- **`docs/AGENTS.md`**
  - Line 15 tail: replace "This knowledge base is **provisional design**, not implementation or
    live-operation authority: unresolved gaps and conflicts must be ratified by the operator
    before affected work begins." with:
    "This knowledge base is **operator-ratified design** — the corpus was signed off by the
    operator on 2026-08-21 (a conditional go-ahead given in the PRD session, contingent on the
    independent contradiction sweep passing; the sweep passed). Ratified status is documentation
    authority only: implementation authorization still arrives exclusively through the factory
    pipeline, live-money action still requires the human-promotion law, and the deferred gaps
    (GAP-0016/GAP-0017, GAP-0048 content, GAP-0049) remain non-authorizing until their own
    sittings."
  - Line 17 tail: replace "The rulings are authoritative, but the documents absorbing them stay
    `status: provisional` until the whole knowledge base is re-ratified: an answered gap is an
    operator ruling, never on its own implementation or live-money authority." with:
    "The rulings are authoritative, and the knowledge base absorbing them was re-ratified by the
    operator's corpus sign-off of 2026-08-21: documents now carry `status: ratified`. An answered
    gap remains an operator ruling, never on its own implementation or live-money authority."
  - Lines 21–24: change each "(build against it as the source of truth, still under the
    provisional-corpus gate)" to "(build against it as the source of truth)". Where a bullet ends
    "…stays `provisional` surface" (the QML bullet), change to "…is ratified design surface;
    implementation authorization still arrives only through the factory pipeline."
  - Line 107 ("Current release gate"): replace the paragraph with one recording: corpus signed
    off 2026-08-21 (conditional go-ahead, sweep passed); still NO implementation, live venue
    connection, order submission, paper-mode transition, operational restore, destructive
    migration, or release-quality acceptance authority from documentation status alone — those
    authorities arrive only through the factory pipeline and the constitution's human-authority
    laws; deferred gaps unchanged (GAP-0016/GAP-0017, GAP-0048 content, GAP-0049); DEC-0049
    remains the one deliberately open ledger row.
- **`docs/index.md`**
  - Line 16: replace "All artifacts remain `provisional`: they authorize no…" with "The corpus
    was signed off by the operator on 2026-08-21 (a conditional go-ahead given in the PRD session,
    contingent on the independent contradiction sweep passing; the sweep passed); artifacts carry
    `status: ratified`. Ratified status authorizes documentation authority only — no
    implementation, credential use, external connection, order, live-money action, promotion,
    restore, deletion, or other destructive operation. Research and recommendations remain
    evidence for operator rulings, never automatic adoption. [DEC-0001] [DEC-0003] [DEC-0004]"
  - Line 28: "records creation of the provisional knowledge base and future documentation
    changes" → "records creation, ratification (operator sign-off 2026-08-21), and ongoing
    changes of the knowledge base".
- **`docs/gap-report.md`**
  - Line 24: replace the final sentence with "An **answered** gap records an operator ruling; with
    the operator's corpus sign-off of 2026-08-21 the absorbing documents now carry
    `status: ratified`. Ratified documentation is still not implementation or live-money
    authority. (DEC-0003, DEC-0004, DEC-0041)"
  - Line 41 tail and line 125 tail: replace "the absorbing documents remain `provisional`" /
    "`COMP-QML` stays `provisional`" with sign-off wording ("ratified at the 2026-08-21 corpus
    sign-off; implementation authorization remains factory-pipeline-only").
  - Line 243: replace "but the corpus stays `provisional` until the whole knowledge base is
    re-ratified" with "and the corpus was re-ratified by the operator's sign-off of 2026-08-21".
- **`docs/knowledge/traceability.md`**
  - Line 16: "Statuses are copied from the provisional ledger, gap catalog, and feature
    inventory" → "Statuses are copied from the ledger (operator corpus sign-off 2026-08-21), gap
    catalog, and feature inventory"; append one sentence recording the sign-off + condition.
  - Status column: the 52 flipped rows `provisional` → `ratified`; DEC-0056 row → `superseded`;
    DEC-0124 row → `superseded`; DEC-0049 row stays `open`. (Dead/superseded/out-of-scope rows
    untouched — the locator preserves them so agents cannot revive them.)
- **`docs/glossary.md`** line 16: "fixes names for the provisional QMF V1 documentation" →
  "fixes names for the QMF V1 documentation (operator corpus sign-off 2026-08-21)".
  **Do NOT touch line 394** — the presence-map state `provisional` there is CT-16 data
  vocabulary (DEC-0126), not a document status.
- **`docs/architecture/overview.md`** line 83 (mermaid edge label): "composes provisional QMF
  libraries; no runtime or live authority" → "composes QMF libraries; no runtime or live
  authority".
- **`docs/constitution.md`**: **no change.** L29 speaks generically about provisional artifacts
  and unresolved GAPs — it remains true and load-bearing for the deferred gaps. Historical
  changelog entries (lines 101, 137 of changelog.md) also stay untouched: append-only history.

### Step 6 — the event records
- **`docs/changelog.md`**: prepend a new entry
  "## 2026-08-21 — Corpus sign-off (provisional → ratified)" recording, in the house table style:
  operator sign-off 2026-08-21, given as a conditional go-ahead in the PRD session, contingent on
  the independent contradiction sweep passing (cite the sweep's workflow id and pass date);
  the 100 doc-status flips; the 52 ledger flips + the DEC-0056/DEC-0124 supersession corrections;
  what deliberately did NOT change (DEC-0049 open; GAP-0016/0017/0048/0049 deferred; dead/
  superseded/out-of-scope rows; SRC-01-C0022 evidence caveat preserved as recorded); the ENH-batch
  disposition the operator chose (see blockers); and the post-flip gate results.
- **`_docwork/stage_state.yaml`**:
  - `provisional: true` → `provisional: false`
  - `ratification:` → `{status: ratified, by: operator, date: '2026-08-21', notes: "Operator
    sign-off 2026-08-21 — conditional go-ahead given in the PRD session, contingent on the
    independent contradiction sweep passing; sweep passed (<workflow id/date>). Scope: docs/
    corpus (100 status flips) + ledger (52 provisional entries ratified; DEC-0056/DEC-0124
    corrected to superseded; DEC-0049 deliberately left open). ENH batch: <operator's
    disposition>."}`
  - Append a `change_mode` row for the sign-off pass with its gate results (house pattern), and
    refresh/append to `final_gate` with the post-flip snapshot.
- **`_docwork/ratification-packet.md`**: prepend a dated header note: this Stage-4 packet is a
  point-in-time record; every conflict and gap in it was subsequently ruled through the
  2026-08-19..21 sittings; the operator signed off the corpus 2026-08-21 (conditional go-ahead,
  sweep passed); the authoritative sign-off record is `stage_state.yaml` + `docs/changelog.md`.
  Body untouched.
- **`_docwork/enhancements.yaml`**: per the operator's disposition ruling only (see blockers) —
  e.g. batch `status: pending` → `status: deferred` with a `disposition:` note citing the ruling.
  Never silently.

## 4. Genuine blockers — things the flip must NOT paper over

1. **The sweep verdict itself.** The go-ahead is conditional. If the contradiction sweep reports
   findings, they are ruled/fixed first; the flip cites the pass verdict explicitly.
2. **71 pending ENH entries** (`_docwork/enhancements.yaml`) keep `lint_docs --strict` failing
   even after every status flip (71 of today's 137 strict errors). Bulk-flipping them without
   triage would silently discard or silently accept 71 recorded suggestions. Requires an explicit
   operator disposition — even a one-line "defer the whole batch to post-V1" ruling suffices —
   or an explicit recorded decision that strict lint stays expected-blocked on exactly this class.
3. **DEC-0049 is `open`** — the only open ledger row (automatic detector notify-vs-mutate
   authority). Sign-off must not silently ratify it. Ask the operator: rule it now, or record it
   as deliberately open past sign-off.
4. **DEC-0056 and DEC-0124 status inconsistencies.** Both are superseded per their successors'
   `supersedes` fields but carry live statuses. They must flip to `superseded` (with
   `superseded_by`), never be swept into `ratified`.
5. **The standing SQS memlog conflict** (SRC-03 memlog entry 118 "SQS formula stays open pending
   re-understanding pass" vs the risk sitting's GAP-0043 resolution, DEC-0153) — surfaced in
   stage_state, still unresolved. The sweep or the operator must rule it; a status flip cannot.
6. **Deferred gaps stay deferred.** GAP-0016/0017 (registration gate, DEC-0121), GAP-0048 content,
   GAP-0049 remain `deferred`/non-blocking and non-authorizing. No flip wording may claim
   completeness beyond the 45 answered gaps.
7. **The SRC-01-C0022 evidence caveat** (paper-mode rulings preserved only via assistant recap;
   direct operator wording lost in the export) survives ratification as recorded — DEC-0149's
   confirmation largely retires the risk, but the sign-off record must preserve, not delete, the
   caveat.
8. **Dirty working tree.** The QML increment + veto round are uncommitted. Commit them first;
   the sign-off must be its own commit.
9. **Expected post-flip warning growth** (not a blocker, must not be "fixed" silently):
   `validate_inventory` will newly warn that 4 more ratified component-scoped decisions belong to
   no feature (DEC-0005, DEC-0025, DEC-0052, DEC-0098 — DEC-0056 exits the set by becoming
   superseded), joining the 11 existing house-accepted rows (which drop to 10 as DEC-0124 flips to
   superseded). Record the new expected total in the changelog/stage_state row so it is not
   mistaken for a regression.

## 5. Post-flip validation

Run, in order, the six commands from section 2. Expected results:

- `validate_ledger` → PASS (superseded entries carry `superseded_by`).
- `validate_registry` → PASS.
- `validate_inventory` → PASS with the house-accepted warning classes; uncovered-decision list
  changes as predicted in blocker 9 (expect ~14 ids: today's 11, minus DEC-0124, plus DEC-0005,
  DEC-0025, DEC-0052, DEC-0098).
- `check_citations` → PASS with the house-accepted dead-DEC frontmatter warning class.
- `lint_docs` → PASS.
- `lint_docs --strict` → **PASS if the ENH batch was dispositioned**; otherwise exactly 71 ENH
  errors and **zero** provisional-status errors (any provisional-status error means a missed file).

Then three greps as belt-and-braces:

```
grep -rln "status: provisional" C:/Users/Mubarak/Desktop/QMX/docs            # must return nothing
grep -rn  "pending corpus re-ratification\|pending operator ratification\|provisional-corpus gate" C:/Users/Mubarak/Desktop/QMX/docs   # must return nothing
grep -rn  "re-ratified" C:/Users/Mubarak/Desktop/QMX/docs                    # only historical changelog entries and past-tense sign-off wording may remain
```

(The glossary presence-map state `provisional` on line 394 does not match any of these patterns —
`status: provisional` is frontmatter-shaped — so it survives correctly.)

Finally: update memory/project-state records per the operator's standing conventions, and commit
the flip as a single dedicated commit.
