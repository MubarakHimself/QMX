# Spec: Data Download + Organization

Reverse-engineering spec for QMX's `data` CLI surface, distilled from reading QuantConnect Lean (CLI + C# engine, Apache-2.0) and Jesse (Python, MIT, v3.0.6). Mechanism understanding only — QMX ships none of their code.

Scope: what QMX's `data` commands must do (download windows, verify/gap-check, catalog listing, split-manifest awareness), what Lean's map-file / factor-file / market-hours machinery teaches for QMX's `(venue, symbol) + calendar` model, and the data-licensing constraint.

---

## 1. Feature claim (verbatim, with URL)

**Lean / QuantConnect** — https://www.lean.io/docs/v2/lean-cli/datasets/downloading-data (landing copy):
- "LEAN integrates with 40 price, fundamental, and alternative data sources, all preformatted, point in time, and ready for your fund."
- "Download data from popular online repositories and brokerages into LEAN format automatically. Pull any of the QuantConnect Cloud data on-premises in LEAN format for easy manipulation."
- "Backtest on almost any time series and import your proprietary signal data into your strategy."

**Lean — CLI API Access and Data Agreement** (verbatim from the presigned-terms block the CLI prints, `lean-cli/lean/commands/data/download.py:31-41`):
- "Display or distribution of data obtained through CLI API Access is not permitted."
- "Data and Third Party Data obtained via CLI API Access can only be used for individual or internal employee's use."
- "Data is provided in LEAN format can not be manipulated for transmission or use in other applications."

**Jesse** — https://docs.jesse.trade/docs/import-candles (verbatim):
- You "choose the **exchange**, **Symbol**, and the **Start Date**"; "Jesse will always import until the same day (today)."
- "Next time, to keep your data storage up to date try running with the same inputs without worry, and duplicate candles will be skipped."

Note: Jesse's public docs make **no** data-licensing claim — ABSENT. Jesse ships no data; it fetches from the exchange's own public REST under the user's relationship (see §2, §3).

---

## 2. Mechanism — how the code actually does it

### 2A. Lean — two download engines behind one command

`lean data download` (`lean-cli/lean/commands/data/download.py:566-742`) branches on `--data-provider-historical`:

**Path 1 — QuantConnect Datasets (paid, curated corpus).**
- Datasets are described by **JSON metadata**, not code. `_get_available_datasets` (`download.py:383-413`) pulls each dataset's `options`, `paths`, and `requirements` from the API and builds a `Dataset` (`lean-cli/lean/models/data.py:288-339`).
- A dataset's `paths` are **path templates** with two lists — `all` and `latest` (`data.py:254-285`). Templates contain `{variable}` placeholders (`{date}`, `{year}`, `{month}`, `{day}`, ticker, resolution, …).
- `Product.get_data_files()` (`data.py:380-460`) is the resolver: for a start/end window it expands the template **day-by-day** via `rrule(DAILY, …)` (`data.py:439-444`), computes a common prefix, lists the matching cloud files under that prefix (`_list_files`, `data.py:462-467` — refuses listings shallower than 3 path levels), and returns the concrete file set. `latest` templates resolve to the single newest match by regex (`DataFileLatestGroup`, `data.py:364-373`).
- Each concrete file is mapped to a **vendor by regex** to price it (`_map_data_files_to_vendors`, `download.py:57-91`). Price is in **QCC** (QuantConnect Credits); balance is checked before purchase (`_confirm_organization_balance`, `download.py:229-245`).
- Some datasets require an active **Security Master subscription** (`requirements`, `download.py:203-212`) — a gate on corporate-action/mapping accuracy.
- The **Data Agreement** must be accepted before any bytes move: `_verify_accept_agreement` (`download.py:248-282`) either prints the presigned terms or opens the agreement URL and **polls the org** until `organization.data.current` flips true.
- Download is parallel (`DataDownloader.download_files`, `lean-cli/lean/components/cloud/data_downloader.py:104-139`): joblib threading, one file → `data_dir / relative_file`. **Bulk** files (`setup/*.tar`) are streamed to a temp dir, untarred into the data folder, and a `.log` **canary** is written so re-runs skip them (`_download_file`, `data_downloader.py:164-211`). `--overwrite` bypasses the canary/exists check.
- Side effect: after pulling `map_files_*.zip` or `factor_files_*.zip`, the CLI **rewrites the Lean config** to point `map-file-provider` / `factor-file-provider` at the `LocalZip…` implementations (`data_downloader.py:125-134`).

**Path 2 — third-party historical providers (self-serve).** For any non-QuantConnect provider, the CLI does **not** download in Python at all. It builds a Lean config, mounts it, and runs the **C# `QuantConnect.DownloaderDataProvider.Launcher.dll`** inside the engine Docker image (`download.py:694-737`) with `--data-type --start-date --end-date --security-type --resolution --tickers [--market]`. The C# engine writes files in LEAN format into the same data folder. OAuth-based brokerage providers need a real cloud `project-id` for the Auth0 flow (`download.py:687-692`).

**Auxiliary-DB refresh.** Independently, `update_database_files` (`data_downloader.py:63-102`) re-pulls `symbol-properties-database.csv` and `market-hours-database.json` from GitHub raw on a cadence (`database-update-frequency`, default `1.00:00:00` = 1 day), stamping `file-database-last-update` in config.

### 2B. Lean — the data-folder model (the "LEAN format")

Canonical layout is generated by `LeanData.cs` (`lean-engine/Common/Util/LeanData.cs`):

- **Relative path** = `securityType/market/resolution[/symbol]/filename` (`GenerateRelativeZipFilePath`, `LeanData.cs:617-626`). For `Daily`/`Hour` there is **no symbol subdirectory**; for `Tick/Second/Minute` the symbol is a subdirectory.
- **Zip granularity**: intraday resolutions store **one zip per (symbol, day)**; hour/daily store **one zip per symbol** (whole history in one file). Entry name inside the zip (`GenerateZipEntryName`, `LeanData.cs:669-718`):
  - equity/forex/cfd/crypto/index intraday: `{yyyyMMdd}_{symbol}_{resolution}_{tickType}.csv`
  - hour/daily: `{symbol}.csv`
  - options/future-options: entry name encodes `style_right_strike_expiry` (`LeanData.cs:694-740`).
- Option/future **chains** get a `universes/` directory (`GenerateRelativeUniversesDirectory`, `LeanData.cs:631-656`).
- `tickType` is the key axis Jesse lacks: Lean separates **`trade` / `quote` / `openinterest`** into distinct files. Quote files are where bid/ask live.

So a security is addressed by the tuple **`(securityType, market, resolution, tickType, symbol, day)`** — the market (venue) and security-type are *first-class directory levels*, not columns.

### 2C. Lean — map files (symbol identity over time)

`MapFile` (`lean-engine/Common/Data/Auxiliary/MapFile.cs:32-79`) + `MapFileRow` (`MapFileRow.cs:27-66`): a per-security CSV of `{date, mappedSymbol[, primaryExchange[, dataMappingMode]]}`. It records **ticker renames** across history (rows ordered by date), exposes `FirstDate`, `DelistingDate` (the last row = delisting event), and `Permtick` (the permanent internal id). This is how Lean keeps a backtest referencing "the same company" when its ticker changed. Stored either as loose CSV (`LocalDiskMapFileProvider`) or bundled `map_files_YYYYMMDD.zip` (`LocalZipMapFileProvider`) — the provider is auto-selected at download time (§2A).

### 2D. Lean — factor files (corporate-action price adjustment)

`CorporateFactorRow` (`lean-engine/Common/Data/Auxiliary/CorporateFactorRow.cs:30-90`): CSV of `date, priceFactor, splitFactor, referencePrice`. `PriceScaleFactor = priceFactor * splitFactor` is the multiplier that turns **raw** prices into **split/dividend-adjusted** prices. Parser skips `inf` / `e+` lines as precision-lossy (`CorporateFactorRow.cs`, comment at ~L82). Bundled as `factor_files_YYYYMMDD.zip`. This is Lean's **split/dividend manifest** — the exact machinery QMX's "split-manifest awareness" needs.

### 2E. Lean — market-hours database (the calendar)

`market-hours-database.json` → `MarketHoursDatabase` (`lean-engine/Common/Securities/MarketHoursDatabase.cs:34-111`; CLI mirror `lean-cli/lean/models/market_hours_database.py:19-45`). JSON keyed by `SecurityDatabaseKey` = `market-securityType` or `market-securityType-symbol` (symbol-specific overrides the wildcard). Each `Entry` carries:
- `dataTimeZone` and `exchangeTimeZone` (two distinct zones — raw data time vs. trading time),
- per-weekday `MarketHoursSegment[]` = `{start, end, state}` where state ∈ premarket/market/postmarket,
- `holidays`, `earlyCloses`, `lateOpens`.

Lookup is `(market, symbol, securityType)` with wildcard fallback (`GetExchangeHours`, `MarketHoursDatabase.cs:95-98`). `force-exchange-always-open` config and an `AlwaysOpen` DB (`MarketHoursDatabase.cs:48-59`) serve 24/7 crypto/forex. **This is the model for QMX's `(venue, symbol) + calendar`**: a venue-scoped, symbol-overridable table of sessions + two timezones + holiday/half-day exceptions.

### 2F. Jesse — import_candles_mode (fetch, gap-fill, store)

`run(client_id, exchange, symbol, start_date, …)` (`jesse/modes/import_candles_mode/__init__.py:79-289`):
- Validates `start_date` (must be before today; `__init__.py:108-119`), then walks from start to today in **fixed 1-minute base candles** only — higher timeframes are resampled later, never stored.
- `driver = drivers[exchange]()` implementing `CandleExchange` (`drivers/interface.py:6-53`): `fetch(symbol, start_ts, timeframe)`, `get_starting_time(symbol)`, `get_available_symbols()`, plus `count` (batch size, e.g. Binance `1000`, `Binance/BinanceMain.py:20`), `sleep_time = 1/rate_limit`, and an optional `backup_exchange`.
- Loop processes `driver.count` minutes per REST call. **Idempotent dedup**: before fetching, it counts existing rows in the window; if `count == driver.count` it **skips** (`__init__.py:152-163`).
- **Range-integrity check** (`__init__.py:172-207`): if the provider returns nothing, or the first returned candle is off by more than `MAX_MISSING_EDGE_MINUTES = 50` (`__init__.py:27`), it falls back to `get_starting_time()`, tries the **backup exchange**, or restarts the import from the first existing date. This is Jesse's "the exchange silently gave me the wrong range" guard.
- **Interior gap fill** (`_fill_absent_candles`, `__init__.py:408-470`): missing minutes inside a batch are synthesized as **flat candles** (o=h=l=c = previous close, volume 0). It **refuses** (raises `CandleNotFoundInExchange`) if the *trailing* gap exceeds 50 minutes — it will not fabricate a long synthetic tail.
- **Store**: `store_candles_list` → `Candle.insert_many(...).on_conflict_ignore()` (`__init__.py:473-477`) — idempotent write keyed on the unique index.
- Live **progress** (percent, ETA, date-reached) is written to Redis (`__init__.py:58-76`) so the dashboard / MCP `get_candle_import_status` can report real advancement — the pattern QMX needs for agent-observable long imports.

Each driver is a thin REST adapter. Binance (`BinanceMain.py:84-116`): GET `/klines`, maps `[ts,o,h,l,c,v]` → candle dicts, with a retrying `requests.Session` and an explicit **HTTP 451 geo-block** message (`BinanceMain.py:45-50`).

### 2G. Jesse — candle storage schema

`Candle` (Postgres via peewee, `jesse/models/Candle.py:11-32`):
```
id UUID pk | timestamp BigInteger(ms epoch) | open close high low volume Float
exchange Char | symbol Char | timeframe Char
UNIQUE INDEX (exchange, symbol, timeframe, timestamp)
```
Two consequences that matter for QMX: prices are **Float** (not exact) and the schema is **single OHLCV** — **no bid/ask**, one price stream per candle. Both violate QMX contracts (see §3).

---

## 3. Jesse vs Lean — which approach fits QMX

| Axis | Lean | Jesse | Fit for QMX |
|---|---|---|---|
| Data source | Curated paid corpus (QCC) + brokerage downloaders in a C# container | Direct exchange public REST, user's own relationship | **Jesse's model** for acquisition (agent fetches under its own entitlement; ship no corpus); **Lean's rigor** for organization |
| On-disk layout | `securityType/market/resolution/tickType/symbol/day` zips — venue & type are directory levels; trade/quote split | Everything in one Postgres table keyed `(exchange,symbol,timeframe,ts)` | **Lean's addressing model** maps cleanly onto QMX's Parquet/DuckDB rooms + `(venue,symbol)`; keep **tickType/quote split** to honor bid+ask |
| Money type | `decimal` (C#) | `Float` | **Neither is QMX-legal** as-is; QMX requires exact integer money (QMF law) |
| Time | `DateTime` + explicit `dataTimeZone`/`exchangeTimeZone` | ms epoch int (UTC implied) | **Lean's dual-timezone** discipline + **QMX's UTC-ns**; store ns, project to session tz via calendar |
| Bid/ask | Separate quote `tickType` files | None (single OHLCV) | **Lean** — QMX must preserve bid+ask (ratified) |
| Symbol identity over time | **Map files** (renames, delisting) | None (ticker is literal) | **Lean** — needed for any non-crypto venue and for honest replay |
| Corporate actions | **Factor files** (price/split factors) | None | **Lean** — this *is* QMX's split-manifest awareness |
| Calendar | **Market-hours DB** (sessions, holidays, half-days, 2 tz) | 24/7 assumed (crypto) | **Lean** — QMX's `(venue,symbol)+calendar` should be this table |
| Gap handling | Reader-side; download is bulk-file | **Explicit**: dedup, range check, interior flat-fill, trailing-gap refusal, backup exchange | **Jesse's verify/gap logic** is the better teacher for QMX's `verify`/`gap-check` command |
| Idempotent re-run | Canary `.log` + exists check | `on_conflict_ignore` unique index + window-count skip | Both good; QMX bitemporal store gets this **for free** via the temporal key |
| Progress for agents | Rich progress bar (human) | **Redis percent/ETA/date-reached** (machine-readable) | **Jesse** — QMX agents need machine-observable progress |
| Licensing posture | Redistribution prohibited; LEAN format locked; paid; ToS gate polled | Ships no data; exchange ToS is the user's problem | **Jesse's "ship no data"** posture is what clears QMX's licensing gate |

**Verdict**: QMX should **acquire like Jesse** (agent pulls from a provider under its own credentials; no bundled corpus) but **organize like Lean** (venue/security-type/resolution/tickType addressing, map files, factor/split manifests, market-hours calendar) — re-expressed over QMX's already-ratified contracts (Dukascopy primary, CT-10/CT-15 intake, Parquet/DuckDB rooms, bitemporal, bid+ask). Jesse's download-time **verify/gap/backup** logic is the model for QMX's integrity commands; Lean's auxiliary databases are the model for QMX's identity/calendar/corporate-action metadata.

**Licensing constraint (flagged).** QMX's old Dukascopy corpus failed the licensing gate — consistent with what the references teach:
- **Lean** treats redistribution as prohibited and locks format ("Display or distribution … is not permitted", "individual or internal … use", "can not be manipulated for transmission", `download.py:36-38`); a signed Data Agreement is *enforced in-flow* (polled) before download.
- **Jesse** sidesteps redistribution entirely: it ships **no** data and fetches at run time from the exchange under the user's own API relationship, so the only license in play is the exchange's ToS.
- **QMX rule**: do **not** bundle or redistribute a data corpus. The agent fetches under its own entitlement; every ingested window records **provenance + a license tag** in the ledger, and the CLI issues a **typed refusal** (QMF) when a source lacks a redistribution/usage right rather than silently ingesting.

---

## 4. QMX spec draft — requirements (WHAT, mapped to QMF where obvious)

Config-driven per the wind-tunnel model: `data` commands consume the Book/BMS config that names venue, symbols, window, resolution, and provider — they never take the tunnel apart. All commands **log during** the run and **write a pass/fail verdict into the ledger** at completion.

**R1 — `data download` (window acquisition).**
- MUST accept `(venue, symbol[list], start, end, resolution, side={bid,ask,both})` from config or flags; default `end = today` (Jesse) but MUST also accept an explicit end for reproducible windows.
- MUST fetch through a **provider adapter** interface (Jesse's `CandleExchange` shape: `fetch`, `earliest_available`, `list_symbols`, batch `count`, rate-limit) so Dukascopy-primary and future providers are swappable without touching the tunnel.
- MUST preserve **bid and ask** as distinct streams (Lean tickType split; QMX ratified) — never collapse to one OHLCV.
- MUST write to the **Parquet/DuckDB rooms** addressed by `(venue, security-type, resolution, side, symbol, time-partition)` — the Lean addressing tuple re-expressed.
- MUST store time as **UTC-ns** and money as **exact integer** (QMF law) — never Float (Jesse's defect) and never provider-native decimals unconverted.
- MUST be **idempotent** on re-run via the bitemporal key (already-present windows skipped/deduped, Jesse's `on_conflict_ignore` + window-count skip); `--overwrite` forces re-ingest as a new bitemporal revision, not an in-place mutation.
- MUST emit **machine-observable progress** (percent, ETA, date-reached), not just a human bar (Jesse/Redis pattern) so a supervising agent can watch a long import.
- MUST record **provenance + license tag** per window in the ledger; MUST issue a **typed refusal** when the source's license does not grant the requested use (licensing gate).

**R2 — `data verify` / `data gap-check` (integrity).**
- MUST detect and report **gaps** against the venue calendar (R5): expected bars minus present bars per session.
- MUST distinguish **real absence** (venue closed per calendar) from **missing data** (venue open, bars absent) — Lean's calendar makes this decidable; Jesse assumes 24/7.
- MUST apply Jesse's **range-integrity guard**: refuse/flag when a provider returns a range whose edges are off by more than a configured tolerance (analog of `MAX_MISSING_EDGE_MINUTES`).
- MUST NOT silently fabricate data. Interior gap-fill (if offered at all) MUST be an explicit, **flagged, separately-labeled** derived layer (Jesse flat-fills but marks volume 0 and refuses large trailing tails) — never written as if it were observed. Result labels carry the world (`live`/`replay`/`simulated`); synthetic fill is `simulated`.
- MUST write a **pass/fail** integrity verdict to the ledger (unbiased end result, per operator context).

**R3 — `data list` / `data catalog` (discovery).**
- MUST list what is present in the rooms: per `(venue, symbol, resolution, side)` the covered `[start, end]`, bar count, gap summary, provenance, license tag, and bitemporal revision.
- MUST let an agent answer "do I already have this window?" before requesting a download (the quant-agent's first question in a sandbox).

**R4 — split/corporate-action manifest awareness.**
- MUST support a **factor/split manifest** per `(venue, symbol)` analogous to Lean's factor files: `date, price_factor, split_factor, reference_price`, combined into an adjustment multiplier, so raw and adjusted views are both derivable.
- MUST support a **symbol-identity map** analogous to Lean's map files: `(effective_date, mapped_symbol)` with first/delisting dates, so a replay references the same instrument across renames.
- These are **metadata rooms**, versioned bitemporally; a backtest result MUST record which manifest revision it used (reproducibility).
- Adjustments MUST be applied with exact-integer money semantics (no Float factor drift).

**R5 — venue calendar (`(venue, symbol) + calendar`).**
- MUST maintain a Lean-market-hours-shaped table keyed by `(venue, security-type[, symbol])` with symbol-level overriding the venue default.
- Each entry MUST carry **two timezones** (raw `data` tz and `exchange`/session tz), per-weekday **session segments** with state (pre/regular/post), plus `holidays`, `early_closes`, `late_opens`.
- MUST support an **always-open** calendar for 24/7 venues (crypto/FX) — the common QMX-primary case.
- Calendar is the authority R2 uses to decide open-vs-closed, and the authority that projects UTC-ns storage into session-local reasoning.
- Calendar + manifests MUST be **refreshable** on a cadence with a stamped last-update (Lean's `database-update-frequency` pattern), and each refresh recorded in the ledger.

**R6 — cross-cutting (QMF compliance).**
- Every `data` command result MUST be a QMF-typed outcome: success carries counts + coverage; failure is a **typed refusal** (bad window, missing entitlement, license denied, provider maintenance, geo-block — cf. Jesse's explicit 451 handling).
- No third-party engine code is ever vendored (QMF law); provider adapters are QMX-authored against public REST/protocol only.
- Results and ledger entries MUST label the **world** (live/replay/simulated) so observed vs. synthetic-fill data are never conflated.
- MUST sustain the target concurrency (12–14 concurrent import/verify tasks) — adapters rate-limited per provider (Jesse's per-driver `sleep_time`), rooms written without cross-task corruption (bitemporal append, not in-place edit).

---

## 5. Open questions

1. **Provider adapter surface for Dukascopy**: Dukascopy serves tick-level bi5 (bid/ask) per hour, not klines. Does the `fetch` contract return ticks that QMX bars server-side, or does the adapter bar them? (Lean bars in C# engine; Jesse fetches pre-barred 1m.) Affects where bid+ask granularity is preserved.
2. **Bitemporal + `--overwrite` semantics**: is an overwrite a new valid-time revision, a new transaction-time revision, or both? Needs a ruling to keep "re-download" honest and auditable.
3. **Interior gap-fill policy**: does QMX offer synthetic fill at all, or refuse and force the agent to acknowledge gaps? Jesse fills flat + volume 0; a hard-truth stance might refuse entirely and only expose gaps via `verify`.
4. **License-tag taxonomy**: what are the discrete license states the gate recognizes (redistribution-ok / internal-only / denied / unknown), and who asserts them — the provider adapter, a per-venue policy file, or an operator ruling? The old Dukascopy corpus failure suggests this needs an explicit registry.
5. **Symbol-identity / factor manifests for QMX-primary venues**: crypto/FX rarely have splits or renames; are map/factor rooms deferred until an equity/futures venue is onboarded, or scaffolded now for AD-consistency? (Lean bundles them universally; Jesse omits them entirely.)
6. **Calendar sourcing**: Lean hand-maintains `market-hours-database.json` in its repo. Where does QMX's calendar authority come from for each venue — provider-published trading hours, an operator-curated file, or a third-party calendar library — and how is its own provenance/licensing tracked?
7. **Catalog store**: is `data list` served from DuckDB queries over the Parquet rooms (compute on read) or a maintained catalog index (compute on write)? Affects the "do I have this window?" latency at 12–14 concurrent tasks.
