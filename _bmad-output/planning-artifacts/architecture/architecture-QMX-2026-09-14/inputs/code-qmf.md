# code-qmf — QMF substrate for QMX strategy experimentation

**Scope:** architecture investigation only. Checkout `main`; product source inspected via `git show` / `git ls-tree` against `integration` @ `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` (ancestor of current `integration` tip; cited SHA is a reachable commit). No implement / commit / branch switch.

**Lead:** `workroom/research/2026-09-14-qmf-qml-understanding.md` — QMF is typed substrate (identity, rooms, registry, risk shapes); applications compose; many contracts `defined-unwired` even when source exists.

---

## Classification table

| Capability | Class | Evidence | Notes |
|---|---|---|---|
| Exact money/time/instrument/fp1/refusals/worlds (CT-01..05) | `reuse` | `source-inspected` | `packages/qmf-core` landed; single fingerprint implementation |
| Per-kind registry + lineage + promotion card (CT-06/07/09) | `reuse` | `source-inspected` | `qmf-registry` records/lineage/promotion/persistence |
| Rooms, splits, journals, ingest, backup (CT-10..15, CT-25/26) | `reuse` | `source-inspected` | `qmf-data` policy + store seam; app owns schedule |
| Configured indicators / structure objects (CT-16/17) | `reuse` | `source-inspected` | Fingerprinted producer identities in indicators/structure |
| Book/BMS/binding/door/result value types (CT-22..32) | `reuse` + `connect` | `source-inspected` + `documented-design` | Source present in `qmf-risk`; docs still say `defined-unwired` — reconcile as **source present, composition-root unwired** |
| Bot / confluence / strategy-family kinds (CT-33/34 + CT-06 metadata) | `reuse` + `connect` | `source-inspected` + `documented-design` | Owned by registry; authored via `qml/` content; root mints |
| QuantDataManager-class browse/quality/transform UX | `extend` / `new` (product) | `user-intent` + `documented-design` | Substrate exists; product work surface does not live in QMF |
| Parallel Library / results / dataset store beside QMF | **forbid** | `documented-design` | L31; Shared Library = registry kinds + rooms, not a second DB |
| Causality registration gate / attempt counter (GAP-0016/17) | `undecided` (Deferred) | `documented-design` | Spine Deferred → backtesting sitting |
| `world=simulated` governed evidence (GAP-0048) | `undecided` (Deferred) | `documented-design` | Reserved-unusable until backtesting sitting |

---

## 1. Dataset identity, provenance, quality, transforms — vs QuantDataManager-class work

### What already exists in QMF (`reuse`)

| Concern | QMF surface | Evidence |
|---|---|---|
| **Dataset / split identity** | CT-12 `SplitManifest.split_id` = `fp1` over calendar, segments, seal, purge/embargo widths, world, cited producers | `git show integration:packages/qmf-data/src/qmf/data/splits.py:1-55`; `docs/contracts/ct-12-dataset-split.yaml` |
| **Holdout / no-peek** | ~12-month `HoldoutSeal` as policy rejection at every read boundary; one journaled final look | `…/qmf/data/seal.py:1-35`; DEC-0119 |
| **Observation identity + provenance** | CT-10 bitemporal `SourceObservation`: event_time, known_at, source, revision, writer/sequence, world, `fp1`; foreign time/money verbatim; corrections append (`correction_of`) never overwrite | `…/qmf/data/observation.py:1-45` |
| **Ingest identity** | CT-15 intake key `(source, source-native id, revision)`; new revision → new `fp1`; schedule ownership refused | `…/qmf/data/ingest.py:1-50`; Dukascopy adapter stamps `LicenseTag` |
| **Store admission** | Content-addressed `admit` on fp1; idempotent byte-identical rewrite; collision refuse+alarm | `…/qmf/data/store/identity.py:1-45` |
| **Rooms / worlds** | Seven room-roles (+ sealed-archive per node DEC-0253) **per world** (`live\|replay\|simulated`); cross-world read = policy rejection; raw+journal evidence-bearing; processed rebuildable | `…/qmf/data/rooms.py:1-50`; `docs/components/qmf-data.md` Authority/Behavior |
| **Series partition** | `(source, instrument, time-window)` enters artifact identity | `rooms.py` AC5 / `partitions` |
| **Quality events** | CT-13 event type `data quality`; calendar-feed import journals quality; ticks emit `corroborates`/`disagrees-with` | `qmf/data/__init__.py` story 3.5/6.2/6.4; CT-07 edges in lineage |
| **Transforms** | Rebuildable processed/analytics views with `RebuildPins` (engine major + calendar/tzdata); never overwrite raw | `rooms.py` RebuildPins; DEC-0117 |
| **Verify** | CT-14 sample-restore / full-restore rehearsal — recoverability claims only | `…/qmf/data/verify.py:1-25` |

### QuantDataManager-class gap (product, not missing QMF primitives)

Donor UX (StrategyQuant QuantDataManager): import/normalize, coverage, gap/spike/incorrect-candle review, timezone/resolution transforms, verified downloads — see UX `inspection-and-feature-opportunities-2026-09-12.md` F09–F11 and `research-backtesting/specs/spec-data-mgmt.md`.

| QDM-class need | Substrate | Missing |
|---|---|---|
| Import / source coverage | CT-15 ingest + CT-10 + rooms | Application CLI/agent UX, progress surfaces (spec R1) |
| Gap / quality browse | Calendar + presence maps + CT-13 quality + seal | Product tooling over rooms; not a second store |
| Timezone / resolution transforms | BarSpec + calendar identity in fingerprints; rebuildable views | Named derived-dataset UX; must mint new fingerprinted artifacts, never mutate raw |
| Verified downloads / license | Dukascopy `LicenseTag`; typed refusal without rights | Broader provider matrix + operator entitlement UX |

**Class:** substrate `reuse`; QDM-like work surface `extend`/`new` on QMB/QMA/node ops — **must not** invent a parallel dataset identity or DB (`docs` L31; feature-impact register: “do not create a second data layer inside QMB”).

---

## 2. Registry kinds already covering bots, books, BMS, results, lineage

### Machinery (`source-inspected`)

- **CT-06** `RegistrationRecord` / `KindRegistry` / `Registrar` — addable-never-redefined kinds; stable id = content `fp1`; occurrence facts excluded (`packages/qmf-registry/src/qmf/registry/records.py`, `__init__.py:1-40`).
- **CT-07** `LineageEdge` / `EdgeType` (`lineage.py`): `supersedes`, `promoted-from`, `occurrence-of`, `corroborates`, `disagrees-with`, `continues-performance`, `carries-ledger`, `enacts`, `branches-from`.
- **CT-09** persistence into per-world registry room via ratified `qmf-registry → qmf-data` (`persistence.py`).
- **Reserved kinds** only: `promotion-occurrence-card`, `treasury-boundary-event` (`RESERVED_KIND_NAMES` in `records.py`). Bot and Book are **no longer** reserved names — bodies ruled by CT-33 / CT-22 (`docs/contracts/ct-06-registration.yaml` enums).

### Kind roster (documented + value types)

| Kind / artifact | Contract | Owner / author | Integration source |
|---|---|---|---|
| `bot-definition` | CT-33 | registry owns; QML authors | `qml/src/qml/declaration/bot.py` (+ conformance) |
| `confluence` | CT-34 | registry owns; QML authors | `qml/src/qml/declaration/confluence.py` |
| `strategy-family` | CT-06 metadata (no new CT) | registry; QML authors | `qml` families |
| `book-definition` | CT-22 | risk shapes; root wraps registry | `qmf/risk/templates.py` `BookDefinition` |
| `bms-definition` | CT-27 | same | `BmsDefinition` in `templates.py` |
| `book-binding` | CT-28 | risk | `qmf/risk/binding.py` |
| `binding-transition` | CT-24 | risk | `qmf/risk/paper.py` |
| `exit-record` | CT-29 | risk | `exit_record.py` / `exit_policy.py` |
| `control-action` | CT-30 | risk | `control_action.py` |
| `control-window` | CT-31 | risk | `control_window.py` |
| `performance-result` | CT-32 | risk | `performance.py` |
| `instrument-currency-exposure`, `instrument-class` | CT-06 AD-9 metadata | risk/docs | contracts; composition root |
| `promotion-occurrence-card` | reserved CT-06 | registry | `promotion.py` |

**Lineage coverage:** version graphs for Book/BMS use `branches-from` (multi-head); corrections use linear `supersedes`; promotion uses card + CT-13 `promotion` pointer event; performance continuity uses `continues-performance` (must not imply `carries-ledger`).

**Note:** CT YAML still often says `wiring_status: defined-unwired` / “no code exists” (e.g. `ct-22-book-charter.yaml`, `ct-33-bot-definition.yaml`). That is **stale relative to integration source**. Treat as: contracts ratified; **library source present**; **application composition-root wiring** (live bind / seat / money path) still unwired — same pattern as brief CT-47 reconcile rule.

---

## 3. Risk contracts: defined-unwired vs source present

**Documented stance:** `docs/architecture/dependencies.yaml` COMP-QMF-RISK notes — all risk contracts `defined-unwired`; records/journals reach registry/data only through composition root; `depends_on: [COMP-QMF-CORE]` only; nothing imports `qmf-risk` inside the roster.

**Source present on integration** (`packages/qmf-risk/src/qmf/risk/`): grammar, dimensional, numeraire, versioning, templates (CT-22/27), r_faces, sizing, admission_bar, admission, control_rank, binding (CT-28), paper (CT-24), door (CT-23), exit_*, control_action/window, journal, performance (CT-32), footprint_requirements, migrations, etc. Package `__init__.py` states explicitly: ratified `defined-unwired`; no live binding/order authorized by this code.

**Reconcile (do not pick one silently):**

| Layer | Status |
|---|---|
| Contract shapes + pure value types + tests/examples | **Present** (`source-inspected`) |
| Roster import of risk | **Forbidden** (L30); apps (QMB/QML/QMN) may import |
| Live/paper money path, door dispatch, ledger evaluation | **Unwired** — node / QMB composition roots; node runtime material out of QMF (`DEC-0142`) |
| Doc line “no code exists” on CT-22/CT-33 YAML | **Stale** vs integration |

QMB is the first sanctioned wirer for CT-22/23/27/28/29/32 in `world=replay` (`dependencies.yaml` COMP-QMB notes). Trading node wires live/paper and is sole `qmf-venue` importer.

---

## 4. What MUST stay in QMF vs what experimentation must not add as a parallel store

### Must stay in / be consumed from QMF (L7, L30, L31, L36)

- Exact primitives + single `fp1` recipe (`qmf-core`).
- Registry kinds, lineage edges, promotion card vocabulary (`qmf-registry`).
- Evidence rooms, splits/seal, journals, ingest boundary, backup primitives (`qmf-data` + store).
- Indicator/structure producer identity contracts (`qmf-indicators`, `qmf-structure`).
- Book/BMS/door/result **shapes** (`qmf-risk` as edge module).
- Worlds `live|replay|simulated` with storage separation; simulated reserved until GAP-0048.
- Authority: bots trade → books control → BMS accounts → human promotes.

### Experimentation product (QMB / QMA / UI) may own

- Orchestration, CLI/MCP, sweep/campaign UX, agent loops, progress, notebooks.
- Resolved run-config **fragments** as **derived** artifacts with lineage to CT-22/27 — never new registry kinds that mutate templates (`DEC-0160`, `qmf-registry.md`).
- As-of registry **reads** over passive file-sync hub — dumb storage, no central registry service (`DEC-0165`; dead DEC-0084).
- QDM-like browse/quality/transform **tools** that call qmf-data APIs.

### Must not add as parallel store / identity

| Anti-pattern | Why |
|---|---|
| Second Library database for bots/Books/results | Shared Library **is** CT-06 kinds + CT-07 edges + as-of sets |
| Per-department fragmented Library | UX layout-brief: Shared Library must not fragment by department |
| QMB-local results DB bypassing CT-32 / CT-13 | Results are CT-32 + journal streams in the run’s world (`DEC-0163`) |
| In-run provider fetch as governed evidence | Acquisition separate; QMB reads split-governed research rooms (`qmf-data.md`) |
| Re-implement fingerprints / money / time | Only `qmf-core` computes `fp1` |
| Import `qmf-venue` from QMB/QML/QMA | Default-deny; only `qmn.venue` |
| Bundle redistributable market corpus | License posture: fetch under entitlement + license tag |

---

## 5. Shared Library objects — which are already fingerprint kinds

Product “Shared Library” (UX feature-impact register / layout-brief) = reusable versioned strategies, Books, BMS, evidence-bearing producers — **not** a separate schema.

| Library object (product language) | Already a fingerprint / registry kind? | Identity locus |
|---|---|---|
| Bot (declaration) | **Yes** — CT-33 `bot-definition` | Content fp1; logic = dist id + version + source-manifest fp |
| Confluence | **Yes** — CT-34 | Cited by bot as ordered fingerprints |
| Strategy family | **Yes** — CT-06 metadata kind | Opaque id on every bot |
| Book template / version | **Yes** — CT-22 `BookDefinition.fp1` | UI edit → new version; `branches-from` graph |
| BMS template / version | **Yes** — CT-27 | Same template discipline |
| Book instance / binding epoch | **Yes** — CT-28 binding record fp = epoch; instance minted apart | Trinity: version fp ≠ instance ≠ binding epoch |
| Performance / experiment result | **Yes** — CT-32 (+ AD-12 `ResultLabel`) | Population cites binding fps; never spans account roles |
| Configured indicator | **Yes** — CT-16 configured-indicator fp1 | Entire config is identity |
| Structure object | **Yes** — CT-17 object fp1 | Mint-once fact; lifecycle via edges |
| Dataset split | **Yes** — CT-12 `split_id` | Manifest fp1 |
| Source observation / raw window | **Yes** — CT-10 / store admit | Bitemporal + intake key |
| Promotion approval | **Yes** — reserved promotion card | Human-signed; journal holds pointer only |
| QMB run-config fragment | **Derived**, not a new kind | Lineage back to Book/BMS; DEC-0160 |
| Seat / live binding occurrence | Binding + promotion machinery | Re-bind ≠ new Bot |

---

## Spine Deferred (relevant excerpts)

From `architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md` §Deferred (~L599–632):

- GAP-0016/0017 look-ahead registration + attempt counter → backtesting sitting.
- Full Bot schema historically deferred — **superseded for body** by CT-33 (2026-08-21); footprint_requirements pending slots remain Book-side.
- Alpha-decay **math** + admission-bar **threshold values** → backtesting; CT-32 primitives exist.
- GAP-0048 simulated-time / backtesting sitting unlocks `world=simulated`.
- Inter-library edges beyond `registry→data` remain default-deny.
- Node owns Book/BMS **runtime evaluation**, KSA matrix, MIS wiring; QMF owns shapes.
- Bar-builder derivation details, L2 governed vocabulary, margin-aware sizing → later sittings.

---

## Synthesis

### (1) What already exists

Full QMF roster on integration: core identity; registry kinds/lineage/promotion/persistence; data rooms/splits/seal/journals/ingest/backup/verify; indicators CT-16; structure CT-17; risk CT-22..32 value modules; QML authoring for CT-33/34. Dataset identity/provenance/quality primitives exceed a thin store — they are the lawful substrate under any QDM-like product.

### (2) Missing wiring vs missing function

| Item | Verdict |
|---|---|
| Risk/Book/BMS/result **types** | Function present; **wiring** at composition roots missing for live; QMB replay wiring is the sanctioned first path |
| Bot/confluence **authoring** | Function present in `qml/`; registration is root-mints (connect) |
| Dataset **policy** (splits, seal, bitemporal, license tags) | Function present |
| Dataset **manager UX** / multi-provider ops / gap studio | **Missing product function** on top of QMF — not missing QMF contracts |
| Causality gate, simulated world, alpha-decay scores | **Deferred function** (spine), not secretly present |
| Stale “no code exists” in some CT YAML | Doc drift — treat as unwired composition, not absent source |

### (3) Recommended architectural ownership

| Concern | Owner |
|---|---|
| Identity, kinds, lineage, promotion vocabulary | **QMF registry + core** |
| Evidence custody, splits, ingest ports, journals | **QMF data** (+ ingest/store/backup components) |
| Book/BMS/door/result shapes | **QMF risk** (edge module) |
| Bot/confluence declaration content + conformance | **QML** (app) authoring → registry kinds |
| Replay experimentation runs, CT-32 emission, orchestrator | **QMB** (first risk wirer in replay) |
| Live/paper composition, venue, evaluation loops | **QMN** |
| QDM-like coverage/quality/transform **product** | App/CLI/agent over qmf-data — **extend connect**, never fork store |
| Shared Library UI | Read model over registry as-of sets + rooms — **no parallel Library DB** |

### (4) Open questions — AD vs Deferred

| Question | Disposition |
|---|---|
| May QMX ship a QuantDataManager-class tool that writes only CT-10/11/12/13 artifacts? | **Needs AD** (product ownership: QMB CLI vs node ops vs QMA tool) — substrate is clear |
| Which derived-transform catalog (resample, TZ normalize, gap flags) becomes governed producers vs ungoverned research? | **Needs AD** — must preserve raw forever and fingerprint derivatives |
| When do CT YAML `wiring_status` / “no code exists” get refreshed to “source present / app-unwired”? | Docwork hygiene — not a capability AD |
| Causality gate + attempt counter | **Stay Deferred** (GAP-0016/17) |
| Admission thresholds / alpha-decay formulas / `world=simulated` | **Stay Deferred** (GAP-0048 family) |
| Whether Shared Library UX needs a new registry kind beyond CT-06 addable metadata | Prefer **no** — use existing kinds; new kind only via spine amendment if a true new artifact appears |
| Paper-before-promotion execution owner vs QMB no-account / QMA no-money | Already flagged in feature-impact register — **AD if experimentation spine assigns owner**; DEC-0261 stands |

---

## Key citations

- Brief laws: `_BRIEF.md` standing laws; constitution L7/L30/L31/L33/L36.
- Deps / defined-unwired: `git show integration:docs/architecture/dependencies.yaml` COMP-QMF-RISK / COMP-QMB / COMP-QML.
- Data rooms: `docs/components/qmf-data.md`; `packages/qmf-data/src/qmf/data/{rooms,splits,seal,observation,ingest}.py`.
- Registry kinds: `docs/contracts/ct-06-registration.yaml`; `packages/qmf-registry/src/qmf/registry/{records,lineage,promotion}.py`.
- Risk source: `packages/qmf-risk/src/qmf/risk/{__init__,templates,performance,binding,door}.py`.
- Deferred: `architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md:599-632`.
- Shared Library intent: `ux-QMX-2026-09-01/.working/feature-impact-register.md`; layout-brief Shared Library non-fragmentation.
