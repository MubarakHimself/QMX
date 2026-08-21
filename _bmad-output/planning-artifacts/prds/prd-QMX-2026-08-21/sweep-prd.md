# Fidelity sweep — draft PRD vs corpus (2026-08-21)

Scope: every FR (FR-001..FR-050), every NFR (NFR-01..NFR-10), every cited artifact id
(CT-*, ADR-*, SCN-*, DEC-*, L*, spec names, registry keys) in
`prd.md` + `addendum.md`, verified against `docs/` (contracts, constitution, ADRs,
scenarios, components, variables registry, gap report, changelog), `_docwork/`
(ledger, stage_state), and the QMB spec set at
`_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-08-19/research-backtesting/specs/`
plus the ratified QMB spine (`architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md`) and
QML increment artifacts. Leanness is not a finding per the sweep charter.

Verdict: **findings** — no critical, 3 major, 10 minor. The PRD is substantially
corpus-faithful: 45 of 50 FRs, all 10 NFRs, and virtually all citations check out
exactly (including the obscure ones: DEC-0185 "Rider A / Rider B / Ruling C" labels are
verbatim in the ledger entry; DEC-0159 does carry the "QMB, not qmx" naming ruling;
DEC-0049 is formally `status: open`; CT-08 is the one deferred contract; the SQS-formula
memlog conflict is surfaced in `stage_state.yaml`). The majors all cluster in one place:
FR-039/FR-040 bind intake-spec requirements that the *ratified* QMB spine explicitly
defers out of V1, enabled by a §2 status line that calls the 13 intake dossiers
"ratified".

---

## A. Findings

### Major

**A1. FR-039 binds two capabilities the ratified QMB spine explicitly excludes from V1
(locked-validation split; grid sampler).**
FR-039: "typed search space, objective plus constraints, train/test/locked-validation
discipline, TPE and grid samplers, resume, cost estimation, and an anti-overfit
sensitivity report. (spec-optimization)". The cited intake spec does contain all of it
(OPT-1..7, OPT-9/10, OPT-12/13, OPT-22/23/24). But the ratified spine that superseded
the intake — `architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md`, Deferred table —
says verbatim: "**Locked validation window** as a third split (intake OPT-10) and
optional Grid/Euler sampler modes — **not in v1**; TPE-class default + split-manifest
fingerprints hold the line." `docs/components/qmb.md` (Deferred fence) repeats it:
"Also fenced: … the locked validation window as a third split". An epic cut from FR-039
as written would build two deferred capabilities. Fix: drop "locked-validation" and
"grid" from FR-039 (or mark them explicitly deferred-per-spine), and cite the spine/
`qmb.md` B-8 alongside spec-optimization.

**A2. FR-040 binds the governance battery (PBO, CSCV S=16) that the ratified spine
defers to GAP-0048/0049.**
FR-040: "…and the governance battery (MC-1000, PBO, CSCV S=16). (spec-mc-significance)".
The intake spec's R-MC-5 does specify exactly that battery. But the ratified spine's
Deferred table says: "**Pass batteries / thresholds** — old battery values (WF windows,
OOS counts, **PBO bands, CSCV**) remain candidates for the GAP-0048/0049 sittings
('keep it simple' — operator)." The ratified B-14 ladder (`qmb.md`) ships: backtest,
optimize, Monte Carlo (trade-shuffle; real-seeded candle perturbation),
rule-significance, walk-forward — PBO and CSCV are absent from the shipped procedure
set. The rule-significance gate and both MC modes in FR-040 are corpus-good; the
"governance battery" clause is not V1. Fix: keep the gate + MC modes; move
MC-1000/PBO/CSCV to the GAP-0048/0049 open item or mark deferred.

**A3. §2 status line "Direction + 13 specs ratified (B-1..15, DC-1..5)" over-claims the
specs' authority status — and is the root cause of A1/A2.**
The 13 spec files are *intake dossiers* (QMB spine front-matter: `sources:
research-backtesting/specs/ (intake)`; ADR-0017: "the two donors were reverse-engineered
into thirteen intake dossiers first … and the architecture was then run normally").
What was ratified is the direction (DC-1..5, `backtesting-direction-position.md` — DC-5's
`qmx` command name itself superseded) and the spine B-1..B-15 (DEC-0169, by delegation).
Several intake requirements were explicitly weakened or reversed at ratification:
OPT-10 locked window and OPT-13 grid mode (deferred, A1), OPT-21 and R11's *stored*
pass/fail ledger verdict (reversed by B-4's reader-derived-fold law, DEC-0162),
R5's warm-up-as-pre-seed (reversed by B-2's in-loop warm-up). The PRD already treats
the spine correctly everywhere else (FR-036, FR-043..FR-046 match the ratified layer);
the table row should read the specs as ratified *inputs* whose requirements bind only
as absorbed by B-1..B-15 / `docs/`. Fix the row and A1/A2 fall out mechanically.

### Minor

**A4. FR-023 (and the §4 journey): "an UNKNOWN blocks its (venue, account) command
stream until explicit reconciliation" — the corpus clears the block on explicit
*resolution*, never on a reconciliation verdict.**
L35: blocked "until an explicit recorded resolution". CT-19: unblocking is an explicit
typed `resolve_unknown(command identity, resolution ∈ observed-accepted |
observed-absent | operator-attested)` call, and "the block is per command and clears on
resolution, **never on a reconciliation verdict**"; reconciliation read-back is the
*evidence* the application resolves from (SCN-0005), and its verdicts gate the command
pipe separately (CT-20). As written, FR-023 invites wiring block-clear to a
`reconciled` verdict — a DEC-0137 violation. Fix: "until an explicit recorded
resolution (`resolve_unknown`)".

**A5. FR-031 citation: "A bot binds exactly one Book" is not carried by CT-28.**
CT-28's own invariant is "a Book binds exactly one **BMS** at a time"; the record it
defines couples Book↔BMS↔account, and the bot side is the AD-41 *seat record* riding
the CT-28 binding context (CT-33, CT-13). The exactly-one-Book-per-bot law lives in
DEC-0115/ADR-0015 ("one Bot at exactly one Book at any time") and SCN-0006 ("A Bot
binds exactly one Book at a time"). "Bindings are dated epochs" is CT-28-correct.
Fix: cite (CT-28; ADR-0015).

**A6. FR-018 and §3/§4 journey use the retired "pair-scoped" framing for news
windows.** DEC-0152 (CT-31, SCN-0008) explicitly *supersedes* the dated 2026-08-18
pair-scoped ruling: scope is per-instrument, resolved through dated currency-exposure
records ("a set of exposures, so a non-pair instrument is expressible; reading a
currency out of a symbol is prohibited"). FR-033 already says "by instrument scope"
correctly; FR-018 ("powering pair-scoped news windows") and the journey line should
match. (The scenario *filename* is still `SCN-0008-pair-scoped-news.md`, so the cite
itself is fine; the title inside is "News Windows Block Entries by Instrument Scope".)

**A7. FR-038 uses banned vocabulary: "multi-timeframe".**
ADR-0006 (binding on all documentation): "`BarSpec` never bare 'timeframe'"; CT-16:
"bare 'timeframe' is banned vocabulary". The corpus phrasing is "bot × symbols ×
BarSpecs × parameters" (qmb.md B-12). A PRD feeding agent pipelines should not seed the
banned word. Fix: "multi-symbol / multi-BarSpec permutation sweeps".

**A8. Determinism success measure over-claims: "identical run configs produce
byte-identical CT-32 artifacts across machines and runs".**
The ratified promise is fingerprint reproduction: "Re-running a run id under its
resolved config must reproduce the **CT-32 fingerprint**; a mismatch is a typed
refusal" (DEC-0163, CT-32), enforced by the tier-2 golden-slice test (DEC-0169).
Cross-OS bit-identity of float content is explicitly **not** promised (CT-05/DEC-0108:
float-bearing series take label-derived identity with (OS, library-version) provenance;
B-14's return-space float carve-out). "Byte-identical across machines" would make the
un-promised float property a gate. Fix: "reproduce the CT-32 fingerprint".

**A9. FR-044 / Open item 2: "no verdict-bearing backtest ships until GAP-0048
closes" is not the corpus mechanism.**
The ratified rules are: all fills `optimistic`-tainted; such runs cannot claim edge or
spend split budget (DEC-0164); a replay-world verdict can never gate live money
(DEC-0162). Per-requirement read-time bar verdicts DO exist pre-GAP-0048 (the fold
answers per requirement, `not-yet-ruled` where blank — B-4/SCN-0012 step 8).
"Verdict-bearing" isn't corpus vocabulary and overstates the block. Fix: "…and no
backtest claims edge or spends split budget until GAP-0048 closes".

**A10. FR-005 phrase "identity rides two version ladders" contradicts the cited
contract's own split.** CT-05: code-package SemVer is "display-only provenance that
**never enters identity**"; only the integer contract format version (plus fp1) is
identity-bearing. The meanings-never-mutate / history-readable-forever halves are
right. Fix: "…a deterministic fp1 fingerprint plus a per-contract integer format
version (SemVer stays display-only); meanings never mutate…".

**A11. FR-028 citation gap: the three-layer/no-probation admission clause is not
carried by CT-23 or ADR-0010.** Its home is DEC-0146 (ADR-0008; CT-22/CT-27: "Layer 1
linters, Layer 2 technical shakedown, Layer 3 one operator signature — no trial
period, probation window, or paper-performance gate"). The rest of FR-028
(requested_r Book-resolved — CT-23; full-loss-price-or-refuse and three-face frozen R —
ADR-0010/CT-23) is correctly cited. Fix: add CT-22/CT-27 or ADR-0008 to FR-028's cites.

**A12. No FR covers the SQS V1 sensor, though the corpus makes it a bind-time
prerequisite and a QMB-run input (load-bearing omission).**
ADR-0010/DEC-0153 ratify SQS V1 as a CT-16 configured producer (ratio sensor,
hysteresis, conservative sentinel, "the sensor computes, the transport carries, the
Book door decides; V1 blocks only"); CT-22 makes a present SQS baseline a bind-time
prerequisite for every sensor a Book's doors read, CT-28 lists it in the bind-time
capability check, and `qmb.md` feeds the run's modeled-spread series to the Book's SQS
door in non-live runs. FR-035 mentions SQS values only as configurables. Without an FR,
a factory build of qmf-risk/QMB could omit the sensor and every Book-door replay run
(and later any live binding) would refuse. Suggested FR (area F): "SQS V1 ships as the
corpus ratio sensor — a CT-16 configured producer whose baseline is a bind-time
prerequisite; the Book door decides, V1 blocks only. (qmf-risk; ADR-0010)".

**A13. Addendum internal inconsistency: QMA still tagged "[ASSUMPTION — confirm
before it appears anywhere binding]" while PRD Open item 7 records the name as
CONFIRMED by operator dictation (closed).** One of the two should be updated (the
PRD's closed row is the later state; the addendum tag is stale).

---

## B. FR-by-FR verification record

- **FR-001** ✓ CT-01 (scaled integers; money-path taint; float ban). ADR-0013 ✓.
- **FR-002** ✓ CT-02 (int64 UTC ns; versioned calendars; "nothing below the root reads
  the system clock", clock injected). ADR-0013 ✓.
- **FR-003** ✓ CT-03 ((venue, symbol), symbol opaque/never parsed).
- **FR-004** ✓ CT-04 (seven categories; returned never raised; value-or-refusal).
- **FR-005** ✓ CT-05 + spine, with A10 wording nuance. `world=simulated`
  reserved-unusable ✓ (policy-rejection refusal, GAP-0048).
- **FR-006** ✓ CT-06 (per-kind records, fp1-derived stable id, dedup by construction).
- **FR-007** ✓ CT-07 (append-only typed edges, never rewritten).
- **FR-008** ✓ CT-09 + L30 (no DB server; registry→data the single ratified edge).
- **FR-009** ✓ ADR-0015/CT-06 (human-only signer; plain-words summary as identity
  field), SCN-0007, L17.
- **FR-010** ✓ CT-10 + SCN-0002. (Nuance, note-level: corrections append as annotation
  records referencing the corrected record's fp1 (`correction_of`); the
  (source, native-id, **revision**) key is CT-15's idempotent-intake mechanism —
  "corrections append under revision keys" fuses the two, harmlessly at capability
  level.)
- **FR-011** ✓ CT-11 (seven room-roles per world; cross-world reads refused; raw
  forever), L18.
- **FR-012** ✓ CT-11/CT-12 (12-month no-peek seal at every read boundary incl.
  restored backups; fingerprinted train/validation/sealed-test), SCN-0003, L19.
  `registry:historical_holdout_months = 12` ✓.
- **FR-013** ✓ CT-13 (seven event types; gapless per-writer streams; entity journals =
  read-time projections; "logbook" = the per-bot journal per CT-25).
- **FR-014** ✓ CT-14/CT-26 + SCN-0004, L18. Note: CT-14 splits primitives (QMF) from
  schedule/execution (application/ops-owned); "nightly" is the ratified design cadence
  run by ops — fine at capability level, epics should not put the scheduler inside QMF.
- **FR-015** ✓ CT-15 (idempotent (source, native-id, revision) intake).
- **FR-016** ✓ qmf-data-store.md (dependency-free seam; Parquet/DuckDB/SQLite/JSONL
  swappable; no DB server).
- **FR-017** ✓ dukascopy.md + spec-data-mgmt (download-once, DEC-0166; personal-use
  ruling DEC-0170; no redistributed corpus).
- **FR-018** ✓ calendar-feed.md + SCN-0008, except A6 ("pair-scoped" retired).
- **FR-019** ✓ CT-16 + ADR-0006; TA-Lib confirmed as
  `registry:canonical_indicator_reference` ("TA-Lib C 0.7.1 + wrapper 0.7.1").
  (Note: the equality law binds where both modes are declared; batch-only/
  streaming-only configurations are conformant — CT-16's own purpose supports the
  same-numbers-by-construction headline, so no finding.)
- **FR-020** ✓ CT-17 (causal, append-only, look-ahead-safe families).
- **FR-021** ✓ qmf-calendar-forex.md (first CT-02 market-hours provider, 17:00 NY).
- **FR-022** ✓ CT-18 (two artifacts, verify-or-refuse, profile before first command).
- **FR-023** ✓ CT-19/SCN-0005/L35 (five kinds, four outcomes, timeout≠rejection,
  UNKNOWN a state, never self-clears/retries/flattens) except A4 (resolution vs
  reconciliation).
- **FR-024** ✓ CT-20 (recording precedes interpretation; reconciliation gates command
  pipe only; sensing pipe never blocks).
- **FR-025** ✓ CT-21, L34 (references never values; connection manager sole holder).
- **FR-026** ✓ ctrader component + ADR-0007, L21/L22 (cTrader Open API first; venue-
  neutral port; venue-blind above).
- **FR-027** ✓ CT-22/CT-27 + ADR-0008, L36 (one BMS per account serving many Books;
  accounts/constrains, never trades or reaches inside).
- **FR-028** ✓ CT-23 + ADR-0010 (requested_r Book-resolved; no full-loss price → no
  admission; R three typed faces frozen at admission), with A11 citation gap on the
  three-layer clause.
- **FR-029** ✓ CT-24 + ADR-0009 + SCN-0006 (Book-level standing evidence state; dated
  binding-epoch change).
- **FR-030** ✓ CT-25 (entity journals as read-time projections).
- **FR-031** content ✓ (ADR-0015/DEC-0115, SCN-0006; dated epochs per CT-28), citation
  A5.
- **FR-032** ✓ CT-29 + L39 (Book-owned, risk-monotonic, exactly one exit record per
  virtual close).
- **FR-033** ✓ CT-30/CT-31 + SCN-0008/SCN-0010, L39 (exit-preservation; kill-switch vs
  kill-line distinct; BMS rank per stream; instrument-scoped fail-closed windows).
- **FR-034** ✓ CT-32 + SCN-0011 (publishes never acts; no composite; bench = read-time
  fold over CT-29).
- **FR-035** ✓ variables registry (`numeraire: USD`, configurable rows with no spine
  values) + CT-22 ("blank blocks live money": registers and binds non-live freely,
  live binding is a policy rejection), L38.
- **FR-036** ✓ QMB spine B-1..15 + SCN-0012 (one never-forked loop; one resolved
  fingerprinted config; world provenance-derived). Nuance (note): run id =
  resolved-config fingerprint **+ occurrence id** (spine Consistency row); B-3 calls
  the fingerprint the "run-id root and the ledger key" — the ledger-key half is exact,
  "is the run id" is compressed.
- **FR-037** ✓ spec-backtest-loop (R5 warm-up; reproduction assertion; intra-bar
  fill-path model; R10 bounded/cancellable/observable). (The spec's pre-seed warm-up
  framing was superseded by B-2's in-loop warm-up; FR-037's capability wording is
  compatible with both.)
- **FR-038** ✓ spec-multi-routes (R9 Cartesian + pre-flight count; R11 one ledger row
  per combo + cross-combo ranking), with A7 vocabulary.
- **FR-039** — A1 (locked-validation + grid deferred); rest ✓ vs spec.
- **FR-040** — A2 (PBO/CSCV deferred); gate + two MC modes ✓ (spec R-MC-1/2, B-14).
- **FR-041** ✓ spec-synthetic-data (claim classes `infra-stress` / `robustness` /
  `logic-smoke` at spec §"claim class"; never validates edge — L20, SCN-0009,
  DEC-0164).
- **FR-042** ✓ spec-data-mgmt (R1 download, R2 verify/gap-check, R3 catalog;
  ship-no-corpus + license tags; calendar/split-manifest aware). Trivial: catalog key
  in the spec is (venue, symbol, **resolution**, side) with a covered window — PRD says
  "window" where the spec key says "resolution".
- **FR-043** ✓ spec-reports (R-RPT-8 suppression+veto; R-RPT-10 no composite; series
  as data never images) + CT-32 QMB extensions (DEC-0163).
- **FR-044** ✓ spec-fill-fees (synthetic spread, FX slippage, commission shapes, daily
  swap gap named; fidelity labels LABEL-1; optimistic taint per DEC-0164), with A9
  wording.
- **FR-045** ✓ spec-concurrency + B-5 (process-per-run, min(cpu,mem) governed cap,
  enqueue-on-full backpressure, isolated output dirs).
- **FR-046** ✓ spec-cli-config + DEC-0159 ("QMB, not qmx" verbatim in the ledger) +
  DEC-0185 Ruling C (label verbatim in the ledger statement) + DEC-0167/DEC-0180
  (`uv add qmb` / `uv add qml`); MCP door post-CLI-v1, sibling, never required; plain
  Python first-class (L9, B-1).
- **FR-047** ✓ CT-33 + ADR-0018/DEC-0172 (exactly two artifacts; `.qml` DSL not
  revived; plain Python first-class forever).
- **FR-048** ✓ ADR-0018/DEC-0178 (technical-never-performance; ticket into evidence
  citation and seats; never tunnel entry).
- **FR-049** ✓ CT-34.
- **FR-050** ✓ QL-7/QL-10 (qml.md): QML owns the runtime protocol; QMB hosts through
  the QL-7 adapter; the node hosts seats later.

## C. NFR verification record

- **NFR-01** ✓ ADR-0012/`python_version=3.14`; tier-1 Win11 + Ubuntu LTS x86-64.
- **NFR-02** ✓ ADR-0012; `coverage_floor_percent=80`; 100% branch on CT-01/CT-02
  modules; three event-bound tiers (poe check / check-integration / check-release).
- **NFR-03** ✓ CT-05 + B-spine (golden-slice determinism; replay reproducibility).
- **NFR-04** ✓ ADR-0014 + `design_bot_concurrency=40` ("Motivating reference for
  sizing benchmark ladders (10/100/200 marks)") — the PRD's "10/100/200 marks against
  the ~40-bot reference workload" matches the registry row exactly. (SCN-0009 renders
  the same fact as "10/40/100/200 load marks"; that internal corpus wobble is not a
  PRD defect.) Import <~1s ✓ `core_import_time_budget`.
- **NFR-05** ✓ CT-21/CT-14, L34, tier-1 secret-scan gate.
- **NFR-06** ✓ CT-11 + ADR-0012 (format-version ladder, history readable forever).
- **NFR-07** ✓ L38 + variables registry.
- **NFR-08** ✓ CT-07/CT-13. (Note: consider also citing ADR-0014/DEC-0112 —
  correlation_id propagation, `health()`, Prometheus-class exportability — the
  concrete ratified observability obligations behind NFR-08/NFR-10's "monitoring built
  in"; currently no PRD line reaches them.)
- **NFR-09** ✓ ADR-0014 (QMF spawns nothing; async at venue edge only; QMB governor =
  the V1 instance per B-5).
- **NFR-10** ✓ operator ruling + qmf-data-store (no DB server) + spec-cli-config/
  DEC-0161 (no Ray, no required Docker, no daemon; `uv add`).

## D. Citation audit (ids, labels, statuses)

- CT-01..CT-34 all exist; every PRD use matches the contract's actual binding. CT-22
  and CT-23 are at format v2 (QML increment) — PRD does not contradict this anywhere.
- ADR-0002/0006/0007/0008/0009/0010/0011/0012/0013/0014/0015/0017/0018 all exist and
  carry what the PRD attributes to them.
- SCN-0002..SCN-0012 all exist; journey lines match scenario content (with A4/A6
  wording nuances).
- L2, L7, L9, L13, L14, L17, L18, L19, L20, L29, L30, L34, L35, L36, L37, L38, L39 all
  verified verbatim against `constitution.md`.
- DEC-0159 ("QMB, not qmx" — ledger rationale verbatim), DEC-0185 (Riders A/B and
  Ruling C labels verbatim in the ledger statement), DEC-0121 (GAP-0016/0017
  deferral), DEC-0049 (`status: open` — PRD open item 5 correct) all check out.
- Open item 10's three coordination questions + resolutions match the changelog's QML
  row exactly (Rider A → CT-34 leg cardinality; Rider B → CT-23 inbound full-loss;
  CT-29 keying operator-aligned deferred); the SQS-formula memlog conflict is surfaced
  in `_docwork/stage_state.yaml` ("remains surfaced, unresolved").
- Gap statuses: GAP-0048/0049 deferred (0048 partially closed — seams ruled) ✓;
  gap-report shows 45 answered, 0 open, 2 deferred-to-backtesting + 2 deferred-
  consumer ✓ — consistent with PRD §10 and the standing-status framing.
- Spec names: all 10 cited spec files exist under `research-backtesting/specs/`
  (spec-backtest-loop, spec-multi-routes, spec-optimization, spec-mc-significance,
  spec-synthetic-data, spec-data-mgmt, spec-reports, spec-fill-fees, spec-concurrency,
  spec-cli-config).
- "AD-spine" (FR-005) resolves to `architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md`
  ✓.
- CT-08 "deferred" in §9 supporting metrics ✓ (version null, GAP-0005/0016/0017).

## E. Notes (non-findings, for the PRD editor's discretion)

1. §1 vision's "resurrection, periodic review, and ratification" trio is GitBook-
   sourced; the word "unattended" appears nowhere in `docs/`, and the co-cited
   ADR-0008/L17/L36 support the surrounding authority-chain claims, not the trio
   itself. Legitimate under L2/L37 (GitBook authoritative for live doctrine), but
   downstream should know the trio is not docs-tracked. CT-31's "no live skip button;
   operator control is upstream configuration between sessions" is the closest docs/
   anchor for the no-intraday-loop doctrine.
2. FR-010's "corrections append under revision keys" fuses CT-10 annotations
   (`correction_of` → fp1) with CT-15's revision-keyed intake (see B record above).
3. The extension/graduation law (L33, DEC-0133 — plain-Python experiments graduate
   into governed evidence via the extension shape, for indicators and structure
   families, not only bots) has no FR of its own; FR-019/020's cited contracts carry
   it, and ADR-0006 calls it "a first-class design feature". Borderline leanness;
   flagged only because epics for qmf-indicators/structure need the catalog-surface
   work item.
4. ADR-0012's packaging shape (single uv workspace, seven `qmf.*` PEP 420 packages,
   SemVer lockstep, DEPENDENCIES.md register, licence tiers) is reachable only through
   NFR-01/NFR-02's ADR-0012 cite; factory epics will need it early.
5. PRD open item 2 says GAP-0048 "blocks verdict-bearing backtests" — same wording
   issue as A9.
6. FR-042 "window" vs spec "resolution" in the catalog tuple (see B record).

Sweep complete. No critical findings; the corrections in section A are all local
edits — no FR needs re-scoping beyond FR-039/FR-040, and no citation is to a
nonexistent artifact.
