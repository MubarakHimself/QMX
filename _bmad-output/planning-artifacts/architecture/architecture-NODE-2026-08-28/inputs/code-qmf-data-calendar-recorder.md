# Code inventory — qmf-data, qmf-calendar-forex, recorder/, qmb/data (LIVE data side of the node)

Read-only inventory for the trading-node architecture sitting. All `path:line` citations are
repo-relative to the worktree root `C:/Users/Mubarak/Desktop/QMX-worktrees/node-inventory/`.
Nothing was modified. No credential was opened, printed, or copied (none found in scope).

Scope covered:
- `packages/qmf-data/` (the evidence/rooms/journal/backup/ingest package)
- `extensions/qmf-calendar-forex/` (the market-hours calendar — lives under `extensions/`, NOT `packages/`)
- `recorder/` (standalone news-calendar recorder scripts)
- `qmb/src/qmb/data/` (backtesting-library download/convert; the CLI download front)
- `packages/qmf-core/src/qmf/core/chrono.py` (the Clock port + calendar identity)

## Size / test counts

- `qmf-data` src: **14,730 LOC** across 34 `.py` files under `packages/qmf-data/src/qmf/data/`.
- `qmf-data` tests: **10,360 LOC**, **46 test files**, **545 `def test_` functions**.
- `qmf-data` examples: 3,326 LOC across 15 runnable usage examples.
- `qmf-calendar-forex` src: **793 LOC** (6 files); tests: 508 LOC, **36 test functions**.
- `qmb/src/qmb/data`: **9,425 LOC** across 15 files (download.py 678, dukascopy.py 242, licensing.py 480, catalog.py 596, gap_check.py 762, etc.).
- `recorder/`: `fetch_calendar.py` **213 LOC**, `status.py` **311 LOC**, `README.md` (1 KB). Stdlib-only, zero project imports.

## HEADLINE: there is NO live tick/stream ingestion path anywhere

Grep for `stream|subscribe|live|spot|websocket|realtime|streaming|push` across
`packages/qmf-data/src` returns only: the JSONL append-**stream** journal engine, the `World.live`
enum value, "no **live** skip button" (calendar degradation), and `datetime` conversion. There is
**no** websocket, no subscribe, no spot/tick stream, no long-poll — every ingest path is a
**bounded, called, batch** fetch. Confirmed structurally:
- CT-15 `ExternalSourcePort.fetch(request)` returns `Result[tuple[ProviderRecord, ...]]` — one call, one bounded window `packages/qmf-data/src/qmf/data/ingest.py:305`.
- The ingest seam **refuses to own a scheduler, daemon, process supervisor, or retry loop** — a `policy rejection` (AC6/FM-5) `packages/qmf-data/src/qmf/data/ingest.py:31`.
- Dukascopy adapter is explicitly **download-once**; "runs never fetch from providers; the application owns scheduling, retry, checkpoint, and supervision" `packages/qmf-data/src/qmf/data/dukascopy.py:5`.
- `SourceRequest` "issues one call and returns; it never schedules the next" `packages/qmf-data/src/qmf/data/ingest.py:258`.

Implication for the node: the live tick path (venue-originated market data → CT-10) is the single
biggest thing the node must build. The **value type** for a venue observation exists
(`MarketDataContext`, `packages/qmf-data/src/qmf/data/observation.py:240`) and the CT-10 boundary
accepts "venue-originated market data" producer values `packages/qmf-data/src/qmf/data/source_boundary.py:3`,
but no live producer/adapter that fills them exists. `ExternalSourcePort`'s own docstring names
"future venue market-data adapters" as not-yet-built `packages/qmf-data/src/qmf/data/ingest.py:297`.

---

## 1. World rooms — live world, the seven room-roles, the writer append path

### The seven room-roles (StrEnum, canonical wording)
`packages/qmf-data/src/qmf/data/store/rooms.py:50` — `class RoomRole(StrEnum)`; values `store/rooms.py:60-66`:
`INGEST_DOOR = "ingest door"`, `IMMUTABLE_RAW_ARCHIVE = "immutable raw archive"`, `PROCESSED = "processed"`,
`JOURNAL = "journal"`, `RESEARCH_DOOR = "split-governed research door"`, `BACKUP = "backup"`,
`REGISTRY_ROOM = "registry room"`. Vocabulary "defined once here and reused verbatim by CT-26"
`store/rooms.py:54`. Only two are evidence-bearing: `EVIDENCE_BEARING_ROLES = {IMMUTABLE_RAW_ARCHIVE, JOURNAL}`
`store/rooms.py:71`.

### Instantiated PER WORLD; world isolation is storage separation
`WorldRooms` is the data-policy facade binding the seven roles for **exactly one** world
`packages/qmf-data/src/qmf/data/rooms.py:1`. `live` and `replay` each get their **own independent set of
seven rooms**; `world = simulated` is reserved-unusable → `policy rejection` `rooms.py:14-16`.
Physical separation is delivered by the store: `EvidenceStore.for_world` resolves each world to its
own namespace directory `packages/qmf-data/src/qmf/data/store/facade.py:71`; `world = simulated` has no
governed namespace and is refused `facade.py:74`. The write-world gate is `namespace_block`
`store/rooms.py:96`; the cross-world read gate `require_same_world` — a read must **declare** its world,
there is no implicit "my own world" default `store/rooms.py:105`.

### On-disk layout (content-addressed, injected root — NO ambient paths)
`EvidenceStore(root: Path, *, rotation_bytes, seal)` — root is **injected** `store/facade.py:54`.
`EvidenceStore._build` is "the composition root — the one place the concrete JSONL engine is named"
`store/facade.py:90`. Layout under `<root>/<namespace>/` (`facade.py:98-104`):
- `immutable-raw-archive/<fp1-digest>.parquet` (Parquet, evidence, temp-file + atomic-rename) `store/engines/parquet.py:1`
- `processed/views.duckdb` (DuckDB rebuildable views)
- `registry-room/records.sqlite` (SQLite per-kind versioned records) + `registry-room/lineage/*.jsonl`
- `journal/*.jsonl` (N one-writer JSONL streams)

Partitioning is by **content address**, not directory tree: the `(source, instrument, time-window)`
`SeriesPartition` rides INTO the artifact's fp1 identity `packages/qmf-data/src/qmf/data/partitions.py:1`,
so the same bytes under two windows are two distinct artifacts. Store paths are injected everywhere
(`journal_dir`, `lineage_dir`, `room_dir` are constructor args — `store/journal.py:55`,
`store/registry_room.py:56`, `store/streams.py:98`); **qmf-data has zero ambient path reads**
(no `os.getcwd`/`Path.cwd`/`os.environ` in src) and **zero ambient time reads** (grep for
`datetime.now|time.time|monotonic|utcnow|time_ns` in `packages/qmf-data/src` returns only payload
`event_time_ns` fields and a `datetime.fromtimestamp` conversion at `dukascopy.py:677`).

### CT-10 source observation (the fact that lands)
`packages/qmf-data/src/qmf/data/observation.py:1` — CT-10 bitemporal, source-attributed evidence.
Every observation preserves `event_time` (when it occurred) + `known_at` (when it became knowable),
a read-only `source` (provenance noun, **orthogonal to VenueId**), provider `revision`, an AD-8
`WriterId` with a **per-writer strictly-increasing `sequence`**, its `world`, and its `fp1` identity
(computed only by qmf-core) `observation.py:4-9`. Foreign timestamps/money kept **verbatim**, never
rewritten `observation.py:12`. Corrections **append, never overwrite** — a correction is a distinct
`SourceObservation` with its own fp1 and `correction_of` set `observation.py:22`. The one ratified
reader is `SourceObservationBoundary` `packages/qmf-data/src/qmf/data/source_boundary.py:1`, which hands
each write to the immutable raw archive.

### CT-11 evidence-persistence append-store (how a writer appends)
`packages/qmf-data/src/qmf/data/store/append_store.py:1` — the public seam evidence is persisted through.
`append_raw(rows, presented_fingerprint)` content-addresses on fp1, writes Parquet, returns a
`StoreReceipt` with `room_role=IMMUTABLE_RAW_ARCHIVE, is_evidence_bearing=True, retained_forever=True`
`append_store.py:71-119`. Byte-identical re-write is idempotent (silent); a true collision is refused
and alarmed; empty artifact refused; engine failure → `storage failure` refusal, never raised across
the seam `append_store.py:11-15`. Reads (`read_raw`) require `for_world`; a miss is `stale evidence`
not `invalid input`; the seal is consulted on **every** read `append_store.py:121`.

### WriterId + gapless sequence
`WriterId` is a qmf-core value `(machine, role, stream, boot_epoch_id)` `packages/qmf-data/src/qmf/data/journal.py:220`.
The gapless, strictly-increasing per-`(writer, boot-epoch)` sequence is minted by the CT-13
`JournalWriter` (see §2). Tick appends preserve `sequence` end-to-end (`ingest.py:238`, `ingest.py:496-510`;
`calendar_feed.py:699-751` accepts `sequence_start`). A `WriterSequencer` starts at 0 by default.

---

## 2. Journals (CT-13)

### Seven ratified event types (StrEnum, addable but never redefined)
`packages/qmf-data/src/qmf/data/journal.py:108` — `class JournalEventType(StrEnum)`; values `journal.py:120-126`:
`DECISION = "decision"`, `ORDER = "order"`, `FILL = "fill"`, `RISK_TRANSITION = "risk transition"`,
`PROMOTION = "promotion"`, `DATA_QUALITY = "data quality"`, `CONTROL_ACTION = "control action"`.
"A record whose type is outside the set never becomes a journal event (an `invalid input` refusal)"
`journal.py:16`. QMF's own wired producers = qmf-data (data quality, control action); the other five
come from qmf-registry/venue/risk "through the core-defined `JournalSink` injected at the composition
root" `journal.py:115`. Decision events carry a mandatory closed `DecisionOutcome`
(`AUTHORIZED | REFUSED_BY_DOOR | SUPPRESSED`) `journal.py:128`.

### JournalSink protocol
The `JournalSink` **protocol lives in qmf-core, not qmf-data**: `packages/qmf-core/src/qmf/core/sinks.py:1`
("The injected persistence seams: ObservationSink, JournalSink, RecordSink"), `sinks.py:12`
("appends a journal event to a gapless, append-only [stream]"). qmf-data's producer surface is
`JournalWriter`/`JournalReader` over the store's `JournalStore`.

### The physical journal boundary + producer
`packages/qmf-data/src/qmf/data/store/journal.py:1` — `JournalStore` persists journal evidence as **N
append-only JSONL streams, one per producing component**, one-writer per named stream (a second
distinct writer for a held stream is a `policy rejection`, DEC-0113) `store/journal.py:1-9`; fsync +
monotonic-ordinal rotation; JSONL is the ratified append engine. The data-policy producer is
`JournalWriter` `packages/qmf-data/src/qmf/data/journal_producer.py:1`: mints the gapless per-`(writer,
boot-epoch)` sequence, stamps the seven types, and enforces **block-on-unpersistable** —
an event that cannot be durably persisted (or a partial multi-room write) is a `storage failure` that
**blocks the command stream**; the failed event is retained, the sequence is NOT advanced, and no
later event proceeds until `retry_blocked` durably journals it on recovery `journal_producer.py:33-45`.

### Sequence-gap detection = surfaced loss (never swallowed)
`detect_sequence_gaps` groups by `(machine, role, stream, boot_epoch_id)` and requires contiguous
run from `expected_start`; a gap or duplicate returns a `storage failure` refusal with
retryability `NO` and `context={"signal":"loss", ...}` `packages/qmf-data/src/qmf/data/journal.py:769`.

### Journal-unavailable typed refusal
There is no literal "journal unavailable" string; the fail-closed answer is the block-on-unpersistable
`storage failure` refusal above (`journal_producer.py` blocks the stream and retains the pending write).
The store-level engine failure → `storage failure` translation is at `store/journal.py:10`
(`translate_engine_failure`). So "journal unavailable" is realized as: **block the stream + retain +
storage-failure refusal**, never a silent success.

### Projections over journals (AD-31 / CT-25 folds)
`packages/qmf-data/src/qmf/data/logbooks.py:1` — CT-25 **read-time entity-journal projections
(logbooks)**: the Book journal, BMS journal, and per-bot journal (the operator's logbook) are
**declared read-time projections** over the AD-21 writer-scoped streams, selected by entity identity
`logbooks.py:1-8`. Entities hold no WriterId and mint no stream — "the same recorded set yields many
views, and no view is a stream" `logbooks.py:19`. Node-critical: **paper and live are separated by
construction** — a projection resolves inside one **role-scoped namespace**; the live evidence
namespace admits only `role = live` rows; demo/paper-validation/paper-benched rows resolve in their
own role-scoped namespaces; cross-role aggregation without an explicitly-declared cross-role read is a
`policy rejection` (FM-11) `logbooks.py:33-41`. Decision projections (`select_decisions`, `veto_ledger`)
select on the declared `outcome` field, never key presence `journal.py:819-843`. Cross-stream causality
rides typed `CausalEdge` records, never a timestamp/ordering key `journal.py:44`.

---

## 3. The 12-month research seal (CT-12)

`packages/qmf-data/src/qmf/data/seal.py:1` — the newest sealed window (`registry:historical_holdout_months`,
~twelve months) is a **no-peek lock, not retention** — all history is kept regardless (DEC-0044,
DEC-0119). A read whose position falls at or after the frozen seal boundary is a `policy rejection` at
**every** qmf-data read boundary — raw archive, processed, split-governed research door, and restored
backups alike — never a silent empty result `seal.py:4-8`. `holdout_months` is "taken as configuration
and **never hardcoded**" `seal.py:16`. Read boundaries enumerated: `class ReadBoundary(StrEnum)` =
`RAW_ARCHIVE`, `PROCESSED`, `RESEARCH_DOOR`, `RESTORED_BACKUP` `seal.py:82-97`. Exactly one authorized
final look, journaled as a `control action` subtype `sealed-period-final-look`, second look refused
`seal.py:32`. Look-ahead and attempt-counter gates (GAP-0016/0017) are **deferred**; the seal is
enforced now, independent of them `seal.py:8,239`.

### QA F006 (seal-bypass) fix — LANDED
`FIX-LEDGER.md:19` (FC-06, QMX-F006, **PROVEN**, commit `57ec359`): shared
`derive_content_position`/`guard_derived_content` added in `store/rooms.py` so **every** read path
(`read_raw`, `read_view`, `read_raw_self_guarded` defense-in-depth, `read_room` canonical-JSON scan)
now guards the seal at the position **derived from the stored content itself**, additionally to the
caller's declared `at`. Visible in code: `read_raw` calls `guard_derived_content` on the returned rows
`packages/qmf-data/src/qmf/data/store/append_store.py:158`; `read_view` likewise `append_store.py:333`;
`read_raw_self_guarded` derives the position from the evidence, not a caller argument `append_store.py:165`.
Residual gap (content with no derivable event-time contributes nothing) was **recorded, not doc-edited**.

---

## 4. License tags (Dukascopy personal-use, DEC-0170)

`packages/qmf-data/src/qmf/data/dukascopy.py:100` — `class LicenseTag(StrEnum)`; values `dukascopy.py:109-112`:
`REDISTRIBUTION_OK = "redistribution-ok"`, `INTERNAL_ONLY = "internal-only"`, `DENIED = "denied"`,
`UNKNOWN = "unknown"`. `INTERNAL_ONLY` is the Dukascopy personal-use posture (DEC-0170) `dukascopy.py:105`;
`PERSONAL_USE_LICENSE = "internal-only"` `dukascopy.py:85`. `grants_governed_evidence()` returns True only
for `REDISTRIBUTION_OK`/`INTERNAL_ONLY` `dukascopy.py:114`. Blank/unrecognized → `UNKNOWN` and **blocks**
governed-evidence use `dukascopy.py:118`. Offering a window without an authorizing tag is a typed refusal:
`offer_for_governed_evidence` `dukascopy.py:189-207`. Every acquired window is a `LicensedSourceWindow`
(`(source, instrument, time-window)` + tag + provenance) `dukascopy.py:137-145`.

---

## 5. Backups (CT-14) — encrypted, versioned, off-machine

`packages/qmf-data/src/qmf/data/backup.py:1` — consumes the CT-26 `RoomExport` input and produces a
**new** encrypted, versioned off-machine artifact through an injected `ObjectStorage` port; restore
fetches, decrypts, and writes into a **replacement** `EvidenceStore` — **never rewriting the only local
copy in place** `backup.py:1-8`. Encryption is **required** (`ENCRYPTION_REQUIRED = True`, `backup.py:75`);
a `PayloadCipher` protocol is injected `backup.py:100` — "the crypto dependency is node/ops-owned".

### Backend: provider-neutral port, NOT S3/rclone/local-specific
`class ObjectStorage(Protocol)` `backup.py:120` with `put(*, world, copy_version, source_room_role, payload,
format_version)` and `get(...)` — "Object-key layout, provider selection, and credentials stay outside
QMF" `backup.py:121`. So **no concrete backend (local dir / S3 / rclone) is chosen in code** — it is a
node/ops injection. No credential enters the receipt or evidence (`BackupCopyReceipt`, `backup.py:117`).

### Sample-restore / restore-drill — EXISTS as primitives, cadence is deferred
`packages/qmf-data/src/qmf/data/verify.py:1` — CT-14 verify primitives: `OffMachineVerify.sample_restore`
and `full_restore_rehearsal` are the **only** source of a `RecoverabilityClaim` (never a snapshot's
existence) `verify.py:1-5`; a corrupt/failed restore yields `storage failure`, no claim. `migrate_evidence`
runs `preflight → backup-first → dry-run → migrate → verify` `verify.py:6`. The nightly cadence itself
is `OffMachineCycle.run_once` (Story 5.4): one `CT-26 → CT-14 → sample-restore (+ optional full-restore
rehearsal)` cycle **with no threads, cron, or daemon in qmf-data**; asking it to own the schedule or a
numeric RPO/RTO is a typed refusal `packages/qmf-data/src/qmf/data/cycle.py:1-16`,
`refuse_schedule_ownership`/`refuse_numeric_rpo_rto`. **Numeric RPO/RTO/retention-depth/verification-
cadence are null node/ops-sitting pointers, never filled** `verify.py:10`, `verify.py:67`, `cycle.py:124-137`.

Node must add: the concrete `ObjectStorage` backend, the `PayloadCipher` + key custody, the scheduler
that calls `run_once`, and the numeric RPO/RTO/retention/cadence values.

---

## 6. Projections (AD-31 folds over journals)

Covered in §2: `logbooks.py` (CT-25) is the read-time projection surface (Book/BMS/bot logbooks,
role-scoped, paper/live-separated). Decision/veto projections in `journal.py`. Rebuildable analytics
**views** (the "processed" room) are materialized via `AppendStore.materialize_view`
`store/append_store.py:232` and record their rebuild pins (calendar identity + tzdata version) so an
engine format break costs a rebuild, never evidence `rooms.py:75` (`RebuildPins`). A view is never
evidence-bearing.

---

## 7. Dataset splits / purge / embargo (CT-12) — for live, note-only

`packages/qmf-data/src/qmf/data/splits.py:1` — a CT-12 dataset split is a fingerprinted, time-ordered,
non-overlapping manifest dividing research evidence into `train | validation | sealed-test`; `split_id`
= its fp1 `splits.py:11`. Boundaries are TradingDates or Instants, never civil dates `splits.py:19`.
Required `purge_width`/`embargo_width` are leak-guarded against every cited `ProducerHorizon`; a manifest
that under-covers its producers is refused `splits.py:26`. Records partition by **knowledge time**
`splits.py:33`. **For the live node this matters less** (splits govern research/backtest reads, not live
recording), but the same read boundaries carry the seal, so live reads still hit the seal law.

---

## 8. Ingest adapters (CT-15)

### The port
`packages/qmf-data/src/qmf/data/ingest.py:295` — `ExternalSourcePort(Protocol).fetch(request) ->
Result[tuple[ProviderRecord, ...]]`. Owned+called by `ExternalSourceIngest` `ingest.py:313`, which
normalizes to CT-10 producer values under idempotent `IntakeKey = (source, source-native id, revision)`
`ingest.py:146`. `ProviderRecord` carries optional `bid`/`ask` scaled integers with per-side timestamps,
never merged; a presented `mid` is a `policy rejection` `ingest.py:265-291`. Refuses scheduler ownership.

### (a) Dukascopy adapter — download-once history bootstrap
`packages/qmf-data/src/qmf/data/dukascopy.py:1` (740 LOC). `DukascopyAdapter` decodes bounded bi5 evidence
(stdlib `lzma`+`struct`, QMF-authored, never vendored `dukascopy-node`) through an injected
`DukascopyTransport` `dukascopy.py:23`. Bounded window `[start_ns, end_ns)`; a span over
`FACTORY_MAX_WINDOW_NS` (1 day) or a complete-corpus/unbounded download is refused `dukascopy.py:571-576`,
`refuse_complete_corpus_download`. Batch unit = one Dukascopy hour file.
**QA F004 (bid/ask money) fix — LANDED**: `FIX-LEDGER.md:16` (FC-03, QMX-F004, **PROVEN**, `06ef7a2`):
"CT-15 quote money is rebuilt through the CT-10 factory and persisted at the requested side's exact
integer/scale." Visible in `_tick_to_record`: `bid={"verbatim": tick.bid_verbatim, "scale": price_scale}`,
`ask={...}` with separate `bid_timestamp`/`ask_timestamp` `packages/qmf-data/src/qmf/data/dukascopy.py:702-716`.
`DEFAULT_PRICE_SCALE = 5` `dukascopy.py:93`.

### (b) Calendar-feed adapter — the news calendar
`packages/qmf-data/src/qmf/data/calendar_feed.py:1` — `CalendarFeedAdapter`, CT-15 provider, source token
`CALENDAR_FEED_SOURCE = "news-calendar"` `calendar_feed.py:82`. Provider-native `(source, id, revision)`
identity, **verbatim impact labels (QMX mints no severity scale** — `refuse_minted_severity_scale`),
every import journaled as a CT-13 `data quality` event (`CalendarFeedImport`), and **fail-closed
degradation**: failed refresh / unknown coverage / missing per-instrument currency exposure →
treated-as-affected downstream, **no live skip button** (`refuse_live_skip`) `calendar_feed.py:1-14`,
`FailClosedReason` enum `calendar_feed.py:94-105`. Transport bytes injected (`CalendarFeedTransport`).
**Legal archiving/retention posture is an OPEN operator item** (`LEGAL_ARCHIVING_POSTURE =
"open-operator-item"`), and the adapter never claims retention is authorized `calendar_feed.py:84`,
`calendar_feed.py:221-232`. Provider/format itself (Forex Factory weekly JSON, DEC-0119) is not
hardcoded in this adapter — it decodes an injected snapshot (`decode_calendar_snapshot`); the concrete
provider lives in the standalone `recorder/` (below).

---

## 9. The recorder/ scripts — what they do, and how they are scheduled TODAY

`recorder/README.md:1` + `recorder/fetch_calendar.py:1` — a **standalone, stdlib-only, zero-import**
recorder for the **FairEconomy / ForexFactory** weekly economic calendar. It is **NOT wired into
qmf-data** ("No project imports, no pip dependencies; do not couple anything here to platform code"
`recorder/README.md:5`).

- **Provider / URL**: `https://nfs.faireconomy.media/ff_calendar_thisweek.{json,xml}` — both JSON and
  XML variants fetched `recorder/fetch_calendar.py:32-35`. **The feed serves the CURRENT WEEK ONLY** —
  `nextweek`/`lastweek`/`thismonth` all 404; an un-recorded week is **permanently lost evidence**
  `recorder/fetch_calendar.py:29-31`, `README.md:3-6`.
- **What it writes / where**: raw bytes byte-for-byte, never normalised, to
  `recorder/data/calendar/raw/YYYY/MM/fetch-<UTC-timestamp>.{json,xml}` +
  `recorder/data/calendar/manifest.jsonl` (one line per fetch: `fetched_at_utc, url, sha256, bytes,
  http_status, variant`) + `recorder/data/calendar/recorder.log` `README.md:8-12`,
  `fetch_calendar.py:48-52`. Append-only; identical payloads deduped by sha256, never rewritten
  `fetch_calendar.py:179-183`. Two-timestamp discipline: `fetched_at_utc` = when WE knew it vs event
  time inside the payload, untouched `fetch_calendar.py:9-12`.
- **Scheduling TODAY — Windows Scheduled Task, NOT cron**: scheduled task **`QMX-Calendar-Recorder`,
  daily 06:00, repeats every 12h → 06:00 + 18:00 local** `recorder/README.md:15`. `status.py` probes
  task names `QMX-Calendar-Recorder`, `-AM`, `-PM` via `schtasks`/`subprocess` `recorder/status.py:22-27`.
  Manual run: `py -3 fetch_calendar.py`. Feed is rate-limited (~2 downloads / 5 min) `README.md:17`.
- **`status.py`** is a **read-only** operator status screen (never writes the archive): is it still
  recording, how much have we got, is the scheduled job alive, upcoming high-impact events
  `recorder/status.py:1-8`. Renders a boxed TUI with Unicode/color capability detection.
- **Path posture**: BASE_DIR is derived from `__file__` (`recorder/fetch_calendar.py:48`,
  `status.py:18`) — an **ambient, script-relative path**, and both scripts read `datetime.now(timezone.utc)`
  directly (`fetch_calendar.py:59`, `status.py:120`). This is acceptable for a standalone stdlib recorder
  outside the ambient-scan scope, but it means the recorder is **not injectable** the way the platform
  store is — the node must decide whether to keep it standalone or fold its output through the
  `CalendarFeedAdapter`.

**GAP for the node**: the recorder stores raw FairEconomy bytes; the `CalendarFeedAdapter` decodes
snapshots into governed CT-15 evidence. **These two halves are not wired together today** — the bridge
(feed raw bytes → adapter → CT-10/CT-13) is unbuilt.

---

## 10. Time — the Clock port (qmf-core `chrono.py`) and the ambient-time site

`packages/qmf-core/src/qmf/core/chrono.py:712` — `class Clock(Protocol)`: the core-defined clock seam,
injected at the composition root; "**nothing below the root reads the system clock**" (AR-16)
`chrono.py:712-720`. Type-separated access: `wall_now() -> Result[Instant]`, `monotonic_now() ->
Result[MonotonicReading]`; value-or-refusal even at the clock seam `chrono.py:730-735`.
- There is **no class named `WallClock` or `ReplayClock`**. The production "real clock" is a concrete
  adapter injected at the composition root (in qmb), not a named qmf-core type.
- `DataDrivenClock` `chrono.py:739` is the pure replay/test clock: reads no system clock, replays a
  scripted ordered sequence of wall Instants + monotonic readings; exhausting the script is an
  `unavailable dependency` refusal, returned never raised. `ClockKind(StrEnum)` at `chrono.py:201`.

### The ONE allowed ambient-time site for the download path (QA F018 fix — LANDED)
`FIX-LEDGER.md:27` (FC-14, QMX-F018, **PROVEN**, `c44b4cc`): selected the `now` injection key, removed
the library's ambient fallback, and reads the real clock only at the CLI composition root under the
scanner's explicit allow marker. Visible: the CLI door IS the composition root —
`injected_now = None if end is not None else datetime.now(timezone.utc)  # ambient-scan: allow`
`qmb/src/qmb/doors/cli/__init__.py:263` (context `cli/__init__.py:260`). The library layer takes `now`
injected and **never reads ambiently** `qmb/src/qmb/data/download.py:129`, `download.py:165`,
`resolve_end_ns(end, *, now=None)` `download.py:127`.

Other `# ambient-scan: allow` sites exist in qmb, each at a composition root / orchestrator (NOT in the
download data path): `qmb/data/generate.py:1645` (backtest synthesis stamp), `qmb/orchestrator/log.py:97`
(token_hex) + `:551` (AD-14 operational display timestamp), `qmb/orchestrator/watch.py:63` (monotonic),
`qmb/host/runner.py:241` (uuid4), and `qmb/runloop/frontier.py:211` ("the only approved time read below
the composition root (AR-16)"). **qmf-data itself has zero ambient time reads.**

---

## 11. qmf-calendar-forex — the market-hours calendar

Lives at `extensions/qmf-calendar-forex/` (off-roster extension, own SemVer ladder `README.md:3`).

### One provider, not three
The extension ships **one** calendar: `Forex17NYCalendar` `extensions/qmf-calendar-forex/src/qmf/calendar_forex/_provider.py:1`.
Per DEC-0106 the domain distinguishes **three calendar kinds** — market-hours, day-boundary/evaluation-day,
and news — but this extension implements **only the market-hours calendar**. The provider explicitly
**refuses** the other two as out-of-authority:
- `evaluation_day_of(...)` → `unsupported capability` refusal, "day-boundary calendars are a separate
  named kind (FM-4)" `_provider.py:195-201`.
- `news_events(...)` → refusal `_provider.py:207` (the news calendar is the separate `recorder/` +
  `CalendarFeedAdapter` feed, not a calendar provider).

### What the market-hours provider does
- **Accounting rollover / D1 boundary**: 17:00 America/New_York (`registry:forex_rollover`);
  `ROLLOVER_ZONE = "America/New_York"`, `ROLLOVER_HOUR = 17` `_provider.py:38-40`. `trading_date_of(instant)`
  applies the 17:00 NY rollover and returns a `TradingDate` `_provider.py:135`. This rollover **is** the
  trading-date (D1) boundary; it is distinct from the refused "evaluation-day/day-boundary calendar".
- **Session windows + weekend gaps**: `session_window(instant)` returns the open `SessionWindow`
  (half-open `[prev 17:00 NY, 17:00 NY)`) or `None` when closed; models weekend gaps **Friday 17:00 NY
  through Sunday 17:00 NY** and the pinned holiday set `_provider.py:155-180`.
- **Holidays**: pinned recurring set = **Jan 1 + Dec 25 only**; **Swap-Wednesday is NOT modeled (V1
  accounts are swap-free)** `extensions/qmf-calendar-forex/src/qmf/calendar_forex/_holidays.py:1-20`.
- **tz database version pinning**: PyPI `tzdata==2025.2` → IANA tzdb **`2025b`**; forced at import via
  `TZPATH` + `reset_tzpath`, verified against the pin by `qmf.core.verify_tzdb_pin`; mismatch stores an
  `unavailable dependency` refusal and the package is **not** a usable provider
  `extensions/qmf-calendar-forex/src/qmf/calendar_forex/_tzdb.py:20-27`, `_tzdb.py:83-101`. A tzdata pin
  change is at least a minor SemVer bump `__init__.py:90-92`. Extension version `0.1.0`.
- **Calendar identity in TradingDate**: `CalendarIdentity(forex-17NY / v1 / verified tzdata_version)`
  is exposed for downstream fingerprints `_tzdb.py:100`; `TradingDate.try_create(self.identity, civil)`
  carries the calendar identity **in-band** on every trading date `_provider.py:153`. Splits/seal pin
  exactly one calendar identity and refuse a row carrying a different one (never a silent rescale)
  `splits.py:19-26`, `seal.py:28`.
- **Composition-root wiring only**: `register_forex_17ny()` named surface — never ambient package
  scanning, entry points, or `pkgutil` `__init__.py:14-17`, `README.md:15-17`. Distribution identity +
  version ride into fingerprints; binding (venues/accounts) is separate and excluded from identity.

---

## 12. qmb/src/qmb/data (backtesting-library data lane — reference for the node)

`qmb/src/qmb/data/download.py:1` — `qmb data download` is a thin front over CT-10/CT-15: parses the
request, selects a `ProviderAdapter`, fetches through CT-15, admits CT-10 observations into the
world-scoped raw room. **"No second data layer: persistence is entirely qmf-data"** `download.py:5`.
`DownloadRequest` carries `(venue, symbols, start_ns, end_ns, resolution, side, world, license_tag,
revision, destination, overwrite)` `download.py:52-66`. `ProviderAdapter` port
`qmb/src/qmb/data/ports.py:87` is a Jesse `CandleExchange`-shaped surface (`fetch`, `earliest_available`,
`list_symbols`, `batch_count`, `rate_limit_per_second`) — "fetches only … qmf-data CT-15/CT-10 owns
intake" `ports.py:1-5`. `DownloadSide = bid | ask | both` `ports.py:38-43`. Long-import progress is a
machine-observable `DownloadProgress` (percent, date-reached, ETA) delivered to a `ProgressSink`
`ports.py:64-83`. This whole lane is **batch/bounded**, not streaming. Other qmb/data modules:
`licensing.py` (480), `catalog.py` (596, coverage windows), `gap_check.py` (762), `store_taint.py` (915),
`claim_class.py` (989), `generate.py` (2102, synthetic backtest data), `dukascopy.py` (242).

---

## Deferred / node-sitting / not-in-V1 markers (verbatim locations)

- `backup.py:13`, `:75`, `:100` — key custody + crypto dependency are **node/ops-sitting** (PayloadCipher injected).
- `verify.py:10`, `:67`; `cycle.py:16`, `:124`, `:137`, `:188`, `:320`, `:327` — numeric **RPO/RTO/retention/verification-cadence stay null node/ops pointers, never filled**.
- `__init__.py:54` — "Story 5.4 lands the application-owned nightly cycle" (no threads/cron/daemon in qmf-data).
- `calendar_feed.py:84`, `:221`, `:232`, `:538` — news-calendar **legal archiving/retention is an OPEN operator item**.
- `observation.py:27` — read-time **correction annotation resolution is deferred in V1**.
- `seal.py:8`, `:239`, `:262` — **look-ahead + attempt-counter gates (GAP-0016/0017) deferred**; seal enforced now.
- `rooms.py:16`, `:145`; `store/rooms.py:10` — **`world = simulated` reserved-unusable in V1** (policy rejection).
- `logbooks.py:26`, `:128`, `:324` — risk/QML types "**arrive in later epics**" (binding identity modelled on qmf-core nouns for now).
- `_provider.py:11`, `:195`, `:207` — **day-boundary and news calendars out-of-authority** (not built in the forex extension).
- `ingest.py:297` — "**future venue market-data adapters**" named as not-yet-built (the live path).

---

## CAPABILITY TABLE — the node's LIVE data side

status ∈ {exists-as-is, exists-needs-live-adapter, does-not-exist}

| Capability | path:line | status | What the node must add |
|---|---|---|---|
| Seven room-roles per world (incl. registry room) | packages/qmf-data/src/qmf/data/store/rooms.py:50 | exists-as-is | Wire the **live** world's `EvidenceStore.for_world(live)` at the node composition root; inject store root. |
| WorldRooms data-policy facade (live world) | packages/qmf-data/src/qmf/data/rooms.py:1 | exists-as-is | Instantiate for `world=live`; nothing to build. |
| CT-11 append-store (evidence persistence, WriterId, gapless seq) | packages/qmf-data/src/qmf/data/store/append_store.py:71 | exists-as-is | Call `append_raw` from the live writer; supply WriterId + sequence per boot-epoch. |
| CT-10 source-observation boundary | packages/qmf-data/src/qmf/data/source_boundary.py:1 | exists-as-is | Route live producer values through it. |
| Live tick/stream **source** (venue-originated market data) | packages/qmf-data/src/qmf/data/ingest.py:297; observation.py:240 | **does-not-exist** | Build a live venue market-data adapter (cTrader/IC Markets over qmf-venue) that mints CT-10 observations / `MarketDataContext`; there is NO streaming path today — only bounded batch fetch. |
| A running downloader / scheduler / retry loop | packages/qmf-data/src/qmf/data/ingest.py:31 | **does-not-exist** (refused by design) | The node OWNS the loop that CALLS `ExternalSourcePort.fetch`; qmf-data refuses to own it. |
| CT-13 journal event types (seven) | packages/qmf-data/src/qmf/data/journal.py:108 | exists-as-is | Emit the right types from live Book/BMS/venue/risk producers. |
| JournalSink protocol | packages/qmf-core/src/qmf/core/sinks.py:1 | exists-as-is | Inject the concrete durable sink at the node composition root. |
| JournalWriter block-on-unpersistable + gapless sequence | packages/qmf-data/src/qmf/data/journal_producer.py:1 | exists-as-is | One `JournalWriter` per producing component; call `retry_blocked` on recovery. |
| Journal-unavailable typed refusal (fail-closed) | packages/qmf-data/src/qmf/data/journal_producer.py:33 | exists-as-is | Handle the blocking `storage failure`; surface to operator door. |
| Sequence-gap = surfaced loss | packages/qmf-data/src/qmf/data/journal.py:769 | exists-as-is | Alarm on the loss signal. |
| Entity-journal projections (Book/BMS/bot logbooks, paper/live role-scoped) | packages/qmf-data/src/qmf/data/logbooks.py:1 | exists-as-is | Read-only; surface through operator doors. Paper vs live already separated by role namespace. |
| 12-month research seal at every read boundary | packages/qmf-data/src/qmf/data/seal.py:1 | exists-as-is | Wire `HoldoutSeal` into the live store; supply `holdout_months` from config. |
| QA F006 seal-bypass fix (content-derived guard) | packages/qmf-data/src/qmf/data/store/append_store.py:158 | exists-as-is | Landed (FIX-LEDGER.md:19). |
| License tags (Dukascopy personal-use, DEC-0170) | packages/qmf-data/src/qmf/data/dukascopy.py:100 | exists-as-is | Reuse `LicenseTag` for any live source; live venue data needs its own tag decision. |
| CT-14 backup primitive (encrypted, versioned, off-machine) | packages/qmf-data/src/qmf/data/backup.py:1 | exists-needs-live-adapter | Inject a concrete `ObjectStorage` backend (local/S3-compatible/rclone — **none chosen in code**) + `PayloadCipher` + key custody. |
| Restore drill / sample-restore + full-restore rehearsal | packages/qmf-data/src/qmf/data/verify.py:1 | exists-as-is | Primitives exist; node must schedule them and set numeric cadence. |
| Nightly backup cadence (scheduler) | packages/qmf-data/src/qmf/data/cycle.py:1 | exists-needs-live-adapter | `OffMachineCycle.run_once` exists (no cron/daemon in qmf-data); node adds the scheduler + numeric RPO/RTO/retention. |
| Projections (AD-31 folds over journals) | packages/qmf-data/src/qmf/data/logbooks.py:1 | exists-as-is | Read-only; surface through doors. |
| Dataset splits/purge/embargo (research) | packages/qmf-data/src/qmf/data/splits.py:1 | exists-as-is (note-only for live) | Not on the live-recording path; live reads still honor the seal. |
| Dukascopy ingest adapter (download-once history bootstrap) | packages/qmf-data/src/qmf/data/dukascopy.py:1 | exists-as-is | Inject `DukascopyTransport`; drive bounded windows from the node to bootstrap history. F004 bid/ask fix landed. |
| Calendar-feed adapter (news calendar, CT-15) | packages/qmf-data/src/qmf/data/calendar_feed.py:1 | exists-needs-live-adapter | Inject `CalendarFeedTransport`; bridge the standalone recorder's raw bytes into the adapter (unbuilt bridge). Legal archiving = open operator item. |
| recorder/ scripts (FairEconomy/ForexFactory feed) | recorder/fetch_calendar.py:1 | exists-as-is (standalone, decoupled) | Runs as a **Windows Scheduled Task** (`QMX-Calendar-Recorder`, 06:00 + 18:00); on the Linux VPS the node must re-home scheduling (systemd/cron) and decide whether to keep it standalone or feed the adapter. Not wired to qmf-data. |
| Store layout on disk (Parquet/DuckDB/SQLite/JSONL, injected root) | packages/qmf-data/src/qmf/data/store/facade.py:90 | exists-as-is | Inject the store root path; no ambient paths — node owns the path. |
| Clock port (WallClock/DataDrivenClock/ReplayClock) | packages/qmf-core/src/qmf/core/chrono.py:712 | exists-as-is | Inject a concrete real-clock adapter at the node composition root; nothing below reads the system clock. No `WallClock`/`ReplayClock` named type — build the real-clock adapter. |
| The one allowed ambient-time site (QA F018 fix) | qmb/src/qmb/doors/cli/__init__.py:263 | exists-as-is | Landed; the node's own composition root needs its own `# ambient-scan: allow` real-clock read. |
| qmf-calendar-forex market-hours calendar (17:00 NY rollover, sessions, holidays, tzdb pin) | extensions/qmf-calendar-forex/src/qmf/calendar_forex/_provider.py:1 | exists-as-is | `register_forex_17ny()` at the node root; tzdata==2025.2 / IANA 2025b pinned. |
| Day-boundary/evaluation-day calendar | extensions/qmf-calendar-forex/src/qmf/calendar_forex/_provider.py:195 | **does-not-exist** (refused) | If the node needs a separate evaluation-day calendar, it is a new named kind. |
| News calendar as a calendar provider | extensions/qmf-calendar-forex/src/qmf/calendar_forex/_provider.py:207 | **does-not-exist** (refused) | News is the feed (recorder + CalendarFeedAdapter), not a calendar provider. |
