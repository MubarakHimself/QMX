# Donor investigation — Quant Data Manager (quantdatamanager)

Architecture-only. Mechanisms, not engines. Official StrategyQuant documentation is the primary donor evidence. QMX docs plus `git show 1b451a848d897e42f6e2c7fd9f2ea86fab7295f2:` (integration) are the primary QMX evidence. Workroom notes were not used as facts.

Donor: **Quant Data Manager** (standalone QDM; same Data Manager technology is also embedded in StrategyQuant X). Product page last modified 2026-08-31. Docs hub: https://strategyquant.com/doc/. Support FAQ: https://strategyquant.com/support/.

Standing bans applied while classifying: no donor engine adoption; QMA never executes the money path including paper; QMB never imports `qmf-venue`; ordinary Python stays legal; QMF is a toolbox, applications own scheduling.

Evidence levels used below: `user-intent` (operator standing laws), `documented-design` (ratified QMX docs), `source-inspected` (integration tree), `behavior-demonstrated` (official QDM docs/product copy — we did not run QDM).

## Compact map

| Mechanism | Donor shape | QMX home | Status | Why this status |
|---|---|---|---|---|
| Acquire from Dukascopy-class providers | Download tick/M1 from Dukascopy (and Darwinex/Yahoo/crypto in QDM) | QMB | reuse | `qmb data download` is already a thin CT-15 front; `COMP-DUKASCOPY` is provider #1 |
| File / CSV import | Flexible text/CSV importer with timezone, bartype, errorhandling | QMF | new | No CT-15 file-source adapter and no `qmb data` import command |
| Coverage catalog + incremental update | Data tab + `-u` / “since last date” / range presets | QMB | extend | `catalog`/`list` exist; “update all since last” is not a first-class command |
| Quality — gaps | View & Analyze gaps | QMB | reuse | `qmb data gap-check` already distinguishes calendar closure from missing bars |
| Quality — spikes / incorrect candles | View & Analyze spikes and incorrect candles | QMB | extend | `verify` checks integrity (bid/ask, monotonic ns, scaled-int) but not spike/OHLC-illegal detectors |
| Timezone / DST transform | Clone to timezone (DST-aware); clones refresh with source | QMF | new | Raw timestamps stay verbatim; no processed-room TZ-shifted series yet |
| Timeframe / BarSpec transform | Compute higher TFs from tick or M1 | QMF | connect | In-loop BarSpec fold exists in QMB; persistent processed-room aggregation is designed, not a data-command |
| Provenance | Datasource, postfix, broker profile, instrument metadata | QMF | reuse | CT-10/CT-15 + license tags are already stricter than QDM postfix naming |
| Export | CSV + MT4 FXT/HST + MT5 + many platform formats | QMB | connect | Research-door unsealed exports are designed; no `qmb data export`; vendor FXT/HST is banned |
| Venue-as-source history | MT5 Direct API import (SQX build 144) | QMF | connect | CT-15 already homes venue market data; QMB must not import `qmf-venue` |
| Verified window integrity | Pro “verified downloads” (no extra download-induced gaps) | QMB | reuse | `qmb data verify` is the completeness/integrity front |

## Official donor facts (fetched)

### What QDM is

From https://strategyquant.com/quantdatamanager/ and https://strategyquant.com/support/ (QuantDataManager FAQ):

- Tool to **download, manage, analyze, manipulate, convert and export** historical data.
- Same technology is integrated into StrategyQuant X as its Data Manager section.
- Free sources named on the product page: Dukascopy, Yahoo, Darwinex, Binance, Bitfinex, Coinbase, Poloniex, File import.
- Tick or minute quality. Markets: forex, stocks, crypto, CFDs, metals.
- Pro adds CDN speed (~10–15×) and **verified downloads**. Verified does **not** mean the source has no gaps — only that QDM did not add extra gaps from a broken connection.

### Acquire

- Product page: “Download high-quality historical data … in tick or minute quality.”
- CLI (https://strategyquant.com/doc/quantdatamanager/quant-data-manager-command-line-interface-help/): `-a` add symbols with `datasource=[dukascopy,file,darwinex,crypto,yahoo]`, `datatype=[M1,TICK]`; `-u` update all data; `-di` import from file.
- Newer CLI (https://strategyquant.com/doc/cli-command-line/data-manage-data/): `qdmcli.exe -data action=update|import|export|clone|timezones`. “Data work on existing symbols. Before you can import or update data for some symbol you have to create it using the `-symbol` command.”
- File import (https://strategyquant.com/doc/quantdatamanager/import-history-data-metatrader-4/): configurable importer, predefined MetaTrader4 format; **SQ/QDM import M1 and compute higher timeframes automatically**.
- MT5 Direct API import (https://strategyquant.com/doc/quantdatamanager/metatrader5-data-import/, 2026-04-30): pull OHLC **and** symbol metadata (digits, tick size, tick value, contract size, spread) from a local MT5 `terminal64.exe`. Range presets include From/To, **Since last date**, Last 6 months / year / 5 / 10 years / All time. Broker-capped history is explicit. Incremental “since last date” is a range preset; the same page also says each MT5 import **creates a new symbol** rather than appending — so QDM’s incremental story is mixed even in official docs.
- Broker profiles (https://strategyquant.com/doc/strategyquant/broker-profiles/): when adding Dukascopy/Darwinex data, selecting a non-default broker profile **automatically converts source timezone to the broker timezone**. Official warning: this does **not** resolve broker data-feed differences; for accurate results use broker data from the platform.

### Coverage

- Incremental update (`-u`, “Since last date”, Update selected / Update all in the GUI tutorials).
- Date-bounded download (calendar / From–To).
- Coverage is operator-visible in the Data tab (range present per symbol). Official docs do not publish a machine-readable coverage contract.
- Dukascopy FX history is described as mostly 2002–2007 start; Darwinex shorter (2017/2019); broker MT5 history “capped by what your broker stores” (MT5 import page).

### Quality (gaps / spikes)

- Product page and FAQ: “Analyze data quality – review **gaps, spikes and incorrect candles**.” Table and chart in a selected timeframe. Tools tab “View & Analyze” (https://strategyquant.com/blog/historical-data-sources-quality-data-means-quality-backtest/).
- Pro verified downloads: extra gaps from transport are the thing being prevented; source gaps remain.
- Official docs do **not** publish numeric spike thresholds, OHLC-illegal definitions, or auto-repair rules. Forum answers treat some hour-scale holes as “market paused or Dukascopy missing” rather than auto-fill.

### Timezone / timeframe transform

- Product page: “Easily compute higher timeframes from tick or minute data, or change data timezone.” “Create a clone of the data recomputed into a different timezone – and the cloned data will be automatically updated when you update the source data.”
- CLI `-dc` clone: `timezone=…` or `hours=` fixed shift; `postfix=_{timeframe}_{cloneTime}`; `removeWeekends=true|false`. Timezone list includes IANA names plus broker-shaped aliases such as `(EST+07),EETUS`.
- Official blog https://strategyquant.com/blog/preparing-accurate-data-for-algo-trading-broker-data-feed-differences/: Dukascopy/Darwinex **raw QDM source is UTC**; clone to the broker (Dukascopy MT4 = EST+7; RoboForex = UTC+2 with DST/EET). DST mismatch moves H4/D1 OHLC and time filters. FAQ screenshot is “Clone to timezone.”
- Import CLI: `bartype=[startofbar,endofbar]`, `timeframe=[auto,Intraday,TICK,M1,M5,M15,M30,H1,H4,D1]`.
- Higher-TF compute-from-tick vs from-M1 is called out for MT5 export: MT5 “doesn’t support compute higher timeframe from tick data”; for tick-precision you import **both M1 and tick** (https://strategyquant.com/doc/quantdatamanager/how-to-import-data-to-metatrader-5/).

### Provenance (donor-grade)

QDM’s provenance is operational, not bitemporal:

- Source selector (`datasource=`).
- Optional **postfix** to keep parallel imports of the same symbol apart (MT5 import: `_MT5`, `_BrokeX`).
- Broker profile groups instruments by broker (spread, commission, trading hours, timezone).
- Instrument record: point value, tick size/step, default spread, data type.
- Import errorhandling `stop|ignore`.
- No official QDM contract for event-time vs known-at, license tags, or fp1 identity.

### Export

- Product: export to MetaTrader 4 & 5 “for highest accuracy backtests”; “clone data to any timeframe, export for virtually any trading platform.”
- CLI `-de`: timeframe, datefrom/dateto, outputdir, format enum including Generic tick/bar CSV, MetaTrader4 tick/bar, Amibroker, Birt CSV2FXT, Forex Tester, NinjaTrader, Neuroshell, TradeStation.
- MT4 FXT & HST export (https://strategyquant.com/doc/quantdatamanager/test-strategy-metatrader-4-tick-precision/): writes into the MT4 tester folders; requires MT4 off during export; optional `ExportProperties.mq4` for broker symbol specs. This is a **foreign tester-file generator**, not a data-room export.
- MT5 path: QDM writes CSV; operator manually creates a custom symbol and imports bars. Admin comment 2025-10-31: QDM does **not** inject into the MT5 folder structure.

### CLI automation

https://strategyquant.com/doc/cli-command-line/introduction-to-cli/ — `qdmcli.exe` / `sqcli.exe`, `-data action=…`, `-run file=`, redirect to log. Script examples batch Dukascopy add → update → clone to `EETUS` (https://strategyquant.com/doc/quantdatamanager/quant-data-manager-command-line-interface-script-examples/).

---

## Mechanism findings (mapped onto QMX)

### 1. Acquire from Dukascopy-class providers — `reuse` — QMB

**What.** Bounded historical tick/M1 pull from a named source into a local store, then stop fetching; later jobs update rather than re-download the world.

**Donor.** Product page + CLI `-a`/`-u` + Dukascopy as the free FX/metals source (historical-data blog).

**QMX.** Already the B-11 posture:

- `qmf-data` ingest door + immutable raw archive, CT-15 port, CT-10 observations (`docs/components/qmf-data.md` Acquisition seam; `docs/contracts/ct-15-external-source-adapter.yaml`).
- `COMP-DUKASCOPY` is active provider #1; adapter is QMF-authored, never vendored dukascopy-node (`docs/components/dukascopy.md`; `git show integration:packages/qmf-data/src/qmf/data/dukascopy.py`).
- `qmb data download` parses `(venue, symbols, start, end, resolution, side)`, injects a `ProviderAdapter`, admits through `ExternalSourceIngest`, writes the raw room (`git show integration:qmb/src/qmb/data/download.py`). Runs never fetch (`qmb/src/qmb/data/policy.py` `refuse_run_provider_fetch`).
- Scheduling stays application-owned (DEC-0119). That is QMB (workstation historical) / QMN (live sensing), never the QMF library.

**Do not copy.** QDM CDN, GUI source tiles, SQ paid equities/futures subscription, Darwinex/Yahoo/crypto as V1 sources unless a later sitting names them.

### 2. File / CSV import — `new` — QMF

**What.** Admit operator-owned files (CSV/text, broker History Center dumps) as a **source**, with declared timezone, bar type (start/end of bar), timeframe, and error policy.

**Donor.** File import tile; `-di` with `timezone`, `bartype`, `timeframe`, `errorhandling=stop|ignore`; MT4 History Center → M1 CSV tutorial.

**QMX.** CT-15 is the right port (`source` orthogonal to `VenueId`; idempotent `(source, source-native id, revision)`). No file-source adapter exists on integration under `qmb/src/qmb/data/` or `packages/qmf-data/src/qmf/data/` (source-inspected). `qmb data` commands are only `download, verify, gap-check, list, catalog, generate` (`qmb/src/qmb/data/__init__.py` `DATA_COMMANDS`).

**Home.** New CT-15 adapter in **QMF** (`COMP-QMF-DATA-INGEST`). QMB may later grow a thin `download`/`import` front; it must not become a second parser. Foreign timestamps in the file stay verbatim (CT-10). `errorhandling=ignore` is **not** a QMX default — malformed rows are `invalid input` (FM-2), not silent skip, unless a later AD names a quarantine artifact.

**Open.** Whether V1 needs file import at all (Dukascopy + venue sensing may be enough). That can stay Deferred.

### 3. Coverage catalog + incremental update — `extend` — QMB

**What.** Answer “what windows exist for (source, instrument, resolution)?” and pull only the missing tail.

**Donor.** Data tab; `-u`; MT5 “Since last date”; range presets.

**QMX already.**

- `qmb data list` / `catalog`: rebuildable DuckDB view over Parquet raw rooms; absent windows are the explicit value `not present`, never a refusal (`qmb/src/qmb/data/catalog.py`).
- Download windows are half-open `[start, end)` in int64 UTC-ns; overlapping re-runs are idempotent via durable CT-15 intake keys (`.qmb_intake_keys.jsonl` in `download.py`).
- CT-12 split manifests are **not** coverage catalogs; they are research seals (train/validation/sealed-test) over already-admitted rooms (`docs/contracts/ct-12-dataset-split.yaml`).

**Missing function (extend).** QDM’s “update all selected symbols from last stored bar to now” as a first-class command. QMX has the pieces (catalog end_ns + download start_ns) but not the composed `update` action or an application timer. Scheduling must stay outside QMF. Do **not** put this on QMN for Dukascopy history (node owns live sensing, not the workstation corpus).

### 4. Quality — gaps — `reuse` — QMB

**What.** Report holes inside market-open sessions; do not invent bars.

**Donor.** View & Analyze gaps; Pro verified-download FAQ (source gaps remain).

**QMX.** `qmb data gap-check` (Story 18.5): CT-02 market-hours calendar; calendar-closed absence is closure, not a gap; missing calendar is `unavailable dependency`, never “always open”; `fills_gaps=False`; synthetic fill is `policy rejection` until GAP-0048 (`qmb/src/qmb/data/gap_check.py`). Aligns with older corpus intent “weekend gaps classify/annotate only — no interpolation.”

Journal already has a `data quality` event type (CT-13). Gap reports should remain facts, never edge claims.

**Do not copy.** The View & Analyze chart UI.

### 5. Quality — spikes / incorrect candles — `extend` — QMB

**What.** Flag pathological prints (spikes) and illegal OHLC relations without rewriting raw.

**Donor.** Product copy names “spikes and incorrect candles.” No official threshold table was published on the fetched pages.

**QMX already.** `qmb data verify` (Story 18.4): bid/ask presence, monotonic int64 UTC-ns, exact scaled-integer prices, interior holes as `InteriorGap` (never filled); pass/fail is a data-quality verdict journaled CT-13 (`qmb/src/qmb/data/verify.py`). Tick seam refuses mid-merge (`packages/qmf-data/src/qmf/data/ticks.py` `refuse_mid_merge`).

**Missing function.** Spike / OHLC-illegal detectors. Corrections in QMX are **appended annotations**, never overwrites (CT-10). Do not import QDM’s silent `errorhandling=ignore`. Numeric thresholds are **not** to be invented here — that is an AD or Deferred (same posture as unrecovered “no thresholds were ratified” cleaning work).

**Home.** Extend `qmb data verify` (application front) over QMF rooms; persist defects as CT-13 `data quality` plus CT-10 annotations. UI may later render them; UI does not own the detector.

### 6. Timezone / DST derived view — `new` — QMF

**What.** Present the same raw ticks under a broker- or calendar-aligned civil grouping so D1/H4 boundaries match the live book, without destroying UTC evidence.

**Donor.** Clone-to-timezone with DST (EETUS / EST+7); clones auto-update; `removeWeekends`; broker-profile auto-convert on download. Official blog: raw Dukascopy in QDM is UTC; clone to broker TZ; DST shifts H4/D1 OHLC.

**QMX already (do not clone-in-place).**

- Foreign timestamps stored verbatim with declared zone/offset/resolution; conversions are **derived under lineage**, never rewrites (CT-10, DEC-0106).
- TradingDate carries calendar identity + tzdata in-band; CT-12 splits pin one calendar and refuse foreign rows (`docs/contracts/ct-12-dataset-split.yaml`).
- Civil-time bucket keys (instant + zone + tzdata) are legitimate grouping values, never timestamps (CT-02).
- Forex market-hours calendar: 17:00 America/New_York rollover (`docs/components/qmf-core.md`).

**Missing function.** QDM stores a second named series (`postfix=_M1_UTC2`). QMX should **not** mint a second raw archive. The transferable mechanism is a **processed-room derived series** (or a read-time projection) fingerprinted with `(source series fp1, target calendar identity, tzdata version)`, lineage edge back to raw, auto-rebuild when raw revises — the moral equivalent of “cloned data automatically updated,” without QDM’s mutable clone.

`removeWeekends=true` as a rewrite of raw is banned; weekend absence is calendar closure (gap-check).

`qmb/src/qmb/data/convert.py` is **price** conversion (`provider_price_to_exact`), not timezone. Do not overload it.

**Home.** QMF processed room (rebuildable). QMB may expose a later thin command; QMA/QML/QMN stay out. Broker-profile auto-shift at download is **undecided** (see open questions): QMX currently admits Dukascopy in source time and binds calendars at split/run time.

### 7. Timeframe / BarSpec aggregation — `connect` — QMF

**What.** Higher bars computed from a finest base (tick or M1), never a bare “M15 file” as identity.

**Donor.** Compute higher TFs from tick/M1; clone to timeframe; MT5 note that tick does not aggregate inside MT5.

**QMX already.**

- `BarSpec` is a qmf-core noun (time-interval, tick-count, volume, notional, price-brick, range, session) with calendar identity on time-based kinds (`docs/components/qmf-core.md`).
- Bar aggregation is a **fingerprinted qmf-data derivation** in the processed room (DEC-0126, DEC-0130); tick-to-bar builder remains a Deferred-table row in `qmf-data.md`.
- QMB run loop already folds higher BarSpecs from the finest declared base, emit-only on completed boundary (`qmb/src/qmb/runloop/bars.py`). Forming bars are not actionable.

**Missing wiring.** Persistent processed-room series that `catalog` can list and that runs can name by fp1, so research does not re-fold from ticks every time. Connect: QMF processed-room builder (the deferred tick-to-bar row) ← QMB stream-set BarSpecs. Do not store QDM’s M1/M5/M15/H1/H4/D1 enum as identity.

Venue-native bars stay ungoverned until the venue daily boundary is measured (DEC-0138) — QMN first-connection suite, not QDM clone.

### 8. Provenance and license tags — `reuse` — QMF

**What.** Every window knows who produced it, which revision, whether it may be governed evidence, and how it relates to siblings.

**Donor.** `datasource`, postfix, broker profile, instrument specs. Weak provenance.

**QMX (already stronger — keep).** CT-10: event-time, known-at, source, source_native_id, revision, foreign timestamp/money, writer, sequence, world, fp1. CT-15 idempotent intake. License tag on every ingested window; unlicensed → typed refusal (DEC-0166, DEC-0170; `qmb/src/qmb/data/licensing.py`). Tick disagreements: `corroborates` / `disagrees-with` / `supersedes` (`ticks.py`). Worlds `live|replay|simulated` with cross-world reads refused. QDM postfix is a naming hack; QMX identity is fp1 + source key.

Instrument metadata (tick size, point value, spread) is **not** QDM-clone data. It is CT-03 / venue-observation profile / QMN first-connection verification. Do not grow a QDM “Instruments and Sessions” table inside qmf-data.

### 9. Export of unsealed research windows — `connect` — QMB

**What.** Give a portable, split-governed extract to a research host or a human, without leaking the sealed holdout.

**Donor.** CSV + a zoo of platform formats + MT4 FXT/HST writer.

**QMX already.**

- Research door + CT-12 seal: sealed holdout is a `policy rejection` at every read including backups (`qmf-data.md`).
- B-9: workstation is a controlled-room host; other portable contexts get **only unsealed, split-governed exports** (`docs/components/qmb.md`).
- `catalog` lists coverage; it does not emit a dump.

**Missing wiring.** A thin `qmb data` export/extract command that reads the research door, cites split-manifest fp1, and writes Parquet/CSV (ordinary Python). **Do not** implement MT4 FXT/HST, MT5 custom-symbol injectors, or NinjaTrader/Amibroker writers. Those are foreign tester contracts (DEC-0013).

### 10. Venue-as-source history — `connect` — QMF

**What.** Broker-accurate history and symbol metadata from the venue the operator actually trades.

**Donor.** MT5 Direct API import (local terminal, OHLC + specs); also “export from MT5 to CSV then File import.”

**QMX already.** Venue is also a source: ticks, bars, depth, gap-replay backfill, historical paging enter as CT-10 through CT-15, application-mediated, no fifth contract (`docs/contracts/ct-15-external-source-adapter.yaml`; `qmf-data.md`). QMN push-to-pull accumulator is the first writer of live observations. QMB **never** imports `qmf-venue`.

**Missing wiring.** A historical paging/backfill **application** path (QMN or a workstation just-recipe) that calls CT-15 without QMB growing a venue client. Do not copy QDM’s `terminal64.exe` folder picker or “always create a new symbol” rule — QMX identity is `(source, source-native id, revision)` idempotence.

cTrader, not MT5, is the V1 venue. MT5 import is donor-only.

### 11. Verified window integrity — `reuse` — QMB

**What.** After acquire, prove the stored window matches what was requested (no transport holes, legal money/time types).

**Donor.** Pro verified downloads (CDN inventory check). Free QDM has no equivalent guarantee.

**QMX.** `qmb data verify` is exactly this front, plus CT-13 data-quality journaling. Completeness vs calendar is `gap-check`. No CDN to copy.

---

## Do not copy

- Quant Data Manager / StrategyQuant X **UI** (source tiles, View & Analyze chart, clone wizard, broker-profile tab).
- QDM/SQX **engine**, Java runtime, `qdmcli`/`sqcli` command surface as a contract.
- StrategyQuant **CDN** and Pro verified-download infrastructure.
- **MT4 FXT & HST** exporter, `ExportProperties.mq4`, MT5 custom-symbol injector.
- Foreign platform CSV dialects (Amibroker, NinjaTrader, TradeStation, Forex Tester, Birt CSV2FXT) as QMX identity.
- Silent **raw rewrite**: timezone clone in place, `removeWeekends` deletion, `errorhandling=ignore`, bid/ask mid-merge, interpolating gaps.
- SQ **paid Equities/Futures** subscription pipeline (explicitly not in standalone QDM; not a QMX source).
- dukascopy-node or any vendor downloader **code** (shape reference only; DEC-0013 already recorded).
- Broker-profile XML import scripts as a QMX registry kind.

---

## 1. What already exists

| Layer | Exists | Evidence |
|---|---|---|
| Rooms | ingest door, immutable raw archive, processed, journal, split-governed research door, backup, registry room, sealed-archive | `docs/components/qmf-data.md`; integration `packages/qmf-data/src/qmf/data/rooms.py` |
| CT-15 / CT-10 | Dukascopy adapter, ingest, ticks, license tags | `packages/qmf-data/src/qmf/data/{dukascopy,ingest,ticks,observation}.py` |
| CT-12 splits | fingerprinted train/validation/sealed-test, calendar in-band, purge/embargo | `docs/contracts/ct-12-dataset-split.yaml`; `packages/qmf-data/src/qmf/data/splits.py` |
| QMB data commands | `download`, `verify`, `gap-check`, `list`/`catalog`, `generate` | `qmb/src/qmb/data/__init__.py`; CLI `qmb/src/qmb/doors/cli/tree.py` |
| In-loop TF fold | completed-boundary BarSpec derivation | `qmb/src/qmb/runloop/bars.py` |
| Live venue as source | QMN accumulator → CT-15 → live world room | `docs/components/qmf-data.md` TN sitting notes; CONNECT CT-13 data quality |

Class/test existence is not end-to-end proof of a live Dukascopy corpus on this workstation; the **functions** are source-inspected on integration.

## 2. Missing wiring vs missing function

**Missing wiring (connect):**

- Processed-room persistent BarSpec series ↔ runloop BarSpec fold ↔ `catalog`.
- Research-door unsealed extract ↔ a QMB data command.
- Venue historical paging (CT-15) ↔ an application caller that is **not** QMB.

**Missing function (new / extend):**

- File/CSV CT-15 adapter (`new`).
- Timezone/DST **derived** series in the processed room (`new`).
- Spike / incorrect-candle detectors on `verify` (`extend`).
- Composed incremental “update from catalog tail” (`extend`).

**Not missing — refuse the donor shape:** FXT/HST, CDN, in-place clone, weekend deletion, mid merge.

## 3. Recommended architectural ownership

- **QMF** owns source contracts, rooms, CT-10/CT-12/CT-15, processed-room derivations (TZ view, BarSpec series), provenance, seal.
- **QMB** owns the workstation CLI fronts (`download`, `verify`, `gap-check`, `catalog`, future `export`/`update`) as thin doors. No second data layer.
- **QMN** owns live sensing, gap-replay of the pinned feed, first-connection venue calendar/metadata. Not Dukascopy history.
- **QMA** does not acquire, clone, or export market data and does not execute paper.
- **QML** consumes rooms via QMB runs; it is not a data owner.
- **UI** may later render coverage/quality; it does not own detectors or stores (`configurable = UI-editable` applies to parameters, not to inventing a Data Manager product).

## 4. Open questions

**Need an AD**

- Admit Dukascopy in UTC and bind calendars at split/run time **versus** persist a processed-room TZ-shifted series (donor clone). CT-02 bucket keys may already be enough; a stored clone is a new artifact kind.
- Spike / incorrect-candle **definitions and thresholds** (or an explicit ruling that V1 only reports gaps + type integrity). Do not silently copy QDM’s unnamed heuristics.
- Incremental update-all: QMB command vs operator `just` recipe. Application-owned either way; pick one face.

**Can stay Deferred**

- File/CSV import (if Dukascopy + venue cover V1).
- Extra QDM sources (Yahoo, Binance, Darwinex, Poloniex).
- Tick-to-bar processed-room builder details already on the QMF Deferred table (DEC-0126/0130).
- Research export physical format (Parquet vs CSV) as long as it is split-governed and unsealed.
- GAP-0048 synthetic fill (already refused by `gap-check`).

---

## Source log (official fetches)

- https://strategyquant.com/quantdatamanager/
- https://strategyquant.com/support/
- https://strategyquant.com/doc/
- https://strategyquant.com/doc/quantdatamanager/quant-data-manager-command-line-interface-help/
- https://strategyquant.com/doc/quantdatamanager/quant-data-manager-command-line-interface-script-examples/
- https://strategyquant.com/doc/cli-command-line/introduction-to-cli/
- https://strategyquant.com/doc/cli-command-line/data-manage-data/
- https://strategyquant.com/doc/quantdatamanager/metatrader5-data-import/
- https://strategyquant.com/doc/quantdatamanager/how-to-import-data-to-metatrader-5/
- https://strategyquant.com/doc/quantdatamanager/how-to-export-data-from-metatrader-5/
- https://strategyquant.com/doc/quantdatamanager/import-history-data-metatrader-4/
- https://strategyquant.com/doc/quantdatamanager/test-strategy-metatrader-4-tick-precision/
- https://strategyquant.com/doc/quantdatamanager/introduction-to-qdm/ (stub; comments only)
- https://strategyquant.com/doc/strategyquant/broker-profiles/
- https://strategyquant.com/blog/historical-data-sources-quality-data-means-quality-backtest/
- https://strategyquant.com/blog/preparing-accurate-data-for-algo-trading-broker-data-feed-differences/
