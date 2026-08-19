# QMF Research — Area 02: Data Foundation

**Scope:** multi-pair forex tick/bar data — historical acquisition and continuous live collection — stored and queried on a Windows workstation and a Linux VPS, by one operator.
**Researched:** 2026-08-17. All version numbers, release dates and repo activity dates below were checked against primary sources on that date.
**Verification note:** claims marked **[measured]** were verified first-hand by this researcher on 2026-08-17 (network probe + decode). Claims marked **UNVERIFIED** could not be confirmed against a primary source.

---

## In plain words

Trading data is boring plumbing, and getting it wrong is the single most expensive mistake QMX can make — every strategy result is downstream of it.

You need two kinds of data. **History** (years of past prices, to test ideas) and **live** (prices arriving right now, to trade on). They come from different places, in different shapes, and the hard part is making them into one seamless timeline.

For history, the best free forex source is **Dukascopy**, a Swiss bank that publishes tick-by-tick prices going back ~20 years. I downloaded and decoded one of their files today to confirm exactly how it works. Their data is genuinely good: one hour of EUR/USD contains about 4,000 individual price updates. But their website terms forbid automated downloading, so this is a legal grey area you should decide on deliberately, not drift into.

For storage, the honest answer for one person is **plain files, not a database server**. Specifically: **Parquet** files (a compressed columnar file format) laid out in dated folders, queried by **DuckDB** (a database that needs no server — it's just a Python import) and **Polars** (a very fast tool for reshaping data). All three are free, MIT-licensed, actively developed, and run identically on Windows and Linux.

I looked hard at **ArcticDB**, Man Group's professional market-data store. Technically it fits beautifully. But its licence is a trap: Man Group's own FAQ says a paid commercial agreement is required for *any business use, including research, where any economic benefit is derived*. Trading your own money for profit plausibly counts. There is an escape hatch (older versions have already converted to a free licence) but it costs you a two-year-old codebase.

I also ruled out PostgreSQL/TimescaleDB for the research archive: they are servers you must run, patch and back up, and they buy you nothing a single operator needs.

One subtle trap worth knowing: DuckDB lets only **one program write at a time**. So the live collector must not write into the DuckDB file that research reads. The fix is a small **SQLite** file as the live "inbox", flushed into Parquet once a day.

---

## Findings

### 1. Historical source of record: Dukascopy

#### 1.1 The wire format, verified first-hand **[measured]**

The classic endpoint is still live as of 2026-08-17:

```
https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YYYY}/{MM}/{DD}/{HH}h_ticks.bi5
```

- `{MM}` is **zero-based, zero-padded** (`05` = June). `{HH}` zero-padded, UTC.
- I fetched `EURUSD/2026/05/12/09h_ticks.bi5` → HTTP 200, 17,934 bytes. **[measured]**
- Payload is raw **LZMA** (alone/auto format; `.bi5` is not a container). Decompressed to 81,460 bytes = exactly 4,073 × 20 bytes. **[measured]**
- Record layout confirmed by decode as **big-endian `>iiiff`** (20 bytes):

| offset | type | meaning |
|---|---|---|
| 0–3 | int32 BE | milliseconds since the **start of the file's hour** |
| 4–7 | int32 BE | **ask** in points — divide by the instrument point divisor |
| 8–11 | int32 BE | **bid** in points — same divisor |
| 12–15 | float32 BE | ask volume (millions of base units) |
| 16–19 | float32 BE | bid volume |

Decoded sample (EURUSD 2026-06-12): `09:00:05.995 ask=1.15771 bid=1.15768 askvol=3.6 bidvol=2.7` … `09:59:59.595 ask=1.15841 bid=1.15840`. **[measured]** This confirms the divisor is `100000` for EURUSD. Community documentation states the divisor is `1000` for JPY-quoted pairs and many CFDs ([Zebiner / medium](https://medium.com/@tomas.rampas/the-dukascopy-tick-data-demystified-3af1da80e6c5), [limemojito](https://limemojito.com/reading-dukascopy-bi5-tick-history-with-the-tradingdata-stream-library-for-java/)) — **treat the divisor as per-instrument metadata QMF must carry, not as a constant.**

Note a contradiction in the wild: [ninety47/dukascopy](https://github.com/ninety47/dukascopy) documents ask/bid as *float32*. My decode shows int32-points; float32 interpretation yields denormal garbage. **The int32 reading is correct.** Do not trust that README.

LZMA compression ratio measured at **4.54×** (81,460 → 17,934 bytes). **[measured]**

#### 1.2 Operational behaviour **[measured]**

- A bare `urllib` request with no `User-Agent` returned **HTTP 429**. Setting `User-Agent: Mozilla/5.0` succeeded.
- Issuing 8 sequential hourly fetches with no pacing returned **HTTP 503 on 4 of them** (107-byte error bodies). Dukascopy throttles bursts.
- **Implication:** any QMF downloader needs (a) a UA header, (b) inter-request pacing, (c) retry with exponential backoff, (d) distinguishing "503 = retry" from "empty body = genuinely no ticks (weekend/holiday)". Silent treatment of a 503 as an empty hour would inject invisible holes into the archive.

#### 1.3 Terms of use — the actual legal text

Dukascopy Bank SA's [Terms of Use](https://www.dukascopy.com/swiss/english/legal-pages/terms-of-use/) state verbatim:

> "you may download material from the WEBSITE and/or make one print copy for your own personal, non-commercial use"
> "You shall not use or attempt to use any 'scraper,' 'robot,' 'bot,' 'spider,' 'data mining,' 'computer code,' or any other automate device, program, tool, algorithm, process or methodology to access, acquire, copy, or monitor any portion of the WEBSITE"
> "The WEBSITE and the information contained therein may not be used to construct a database of any kind. Nor may the WEBSITE be stored (in its entirety or in any part) in databases for access by you or any third party"

The same language appears on [Dukascopy Europe's terms](https://www.dukascopy.com/europe/english/legal-pages/terms-of-use/).

**Honest assessment:** the literal text prohibits exactly what every Dukascopy downloader does. Whether `datafeed.dukascopy.com` (a separate host serving the JForex platform) is "the WEBSITE" is arguable, and Dukascopy has tolerated these tools for a decade without visible enforcement. But this is an **operator risk decision**, not an engineering one, and it should be recorded in the decision ledger rather than assumed away. Redistribution of the raw archive is unambiguously out.

Corroborating signal that the maintainers know this is grey: `dukascopy-node`'s current source hides its API host behind character codes rather than writing it as a literal — `String.fromCharCode(106, 101, 116, 116, 97)` → `jetta`, in [src/config/data-api.ts](https://github.com/Leo4815162342/dukascopy-node/blob/master/src/config/data-api.ts).

#### 1.4 Downloader tooling — maintenance audit (GitHub API, 2026-08-17)

| Tool | Language | Stars | Last push | Licence | Verdict |
|---|---|---|---|---|---|
| [Leo4815162342/dukascopy-node](https://github.com/Leo4815162342/dukascopy-node) | TS/Node | 864 | **2026-07-24** | MIT | Alive, most complete. npm `dukascopy-node@1.50.0` |
| [Eghosa-Osayande/dukascopy](https://github.com/Eghosa-Osayande/dukascopy) (`dukascopy-python`) | Python | 25 | **2025-10-07** | MIT (PyPI 4.0.1, 2025-04-28, py≥3.10) | Alive-ish, thin, only real Python option |
| [keyhankamyar/TickVault](https://github.com/keyhankamyar/TickVault) | Python | 41 | **2025-10-13** | MIT | Alive-ish; good ideas (SQLite manifest, gap detect, resume), tiny community |
| [giuse88/duka](https://github.com/giuse88/duka) | Python | 353 | **2019-07-15** | MIT | **ABANDONED** (last *commit* 2017-08-06) |
| [nova-land/dukascopy-tools](https://github.com/nova-land/dukascopy-tools) | TS | 1 | 2021-11-03 | — | Dead fork |
| [kyo06/dukascopy-node-plus](https://github.com/kyo06/dukascopy-node-plus) | TS | 0 | 2026-07-29 | MIT | Fresh fork, zero community |
| [mayeranalytics/bi5](https://github.com/mayeranalytics/bi5) | Haskell/CLI | 3 | 2023-03-11 | MIT | Stale |
| [ninety47/dukascopy](https://github.com/ninety47/dukascopy) | C++ | — | — | — | Format doc is **wrong** (see 1.1) |

**Critical finding about `dukascopy-node`:** as of v1.50.0 it **no longer reads `.bi5`**. Its [url-generator](https://github.com/Leo4815162342/dukascopy-node/blob/master/src/url-generator/index.ts) emits `https://jetta.dukascopy.com/v1/ticks/{INSTRUMENT}/{Y}/{M}/{D}/{H}` and `…/v1/candles/{minute|hour|day}/{INSTRUMENT}/{BID|ASK}/…`, and its [data-normaliser](https://github.com/Leo4815162342/dukascopy-node/blob/master/src/data-normaliser/index.ts) parses a **JSON columnar** response with delta-encoded `times`, integer price `units`, and a `multiplier`. My probe of that host with instrument code `EURUSD` returned `400 Unknown instrument` — the code vocabulary differs from the bi5 path. **[measured]**

So there are now **two incompatible Dukascopy interfaces**, and the most-maintained tool has migrated off the one that older Python tooling uses. Both currently work.

#### 1.5 Alternative / complementary sources

- **[HistData.com](https://www.histdata.com/download-free-forex-data/)** — free M1 bars for all pairs, tick data for some, in Generic ASCII / MT4 / NinjaTrader / MetaStock formats. Page shows "DataFiles Last Updated at: 2026-08-16" → alive. Monthly/yearly ZIPs. Offers paid FTP/Google-Drive auto-update at $7/month/format. Useful as an **independent cross-check** on Dukascopy bars (a second opinion catches silent Dukascopy gaps). I could not locate a terms-of-service page (`/terms-of-service/` → 404) — **UNVERIFIED** what its licence actually is.
- **The broker itself** (cTrader) — see §2. Authoritative for *your* execution prices but limited in depth.

---

### 2. Live and broker-side collection

#### 2.1 cTrader Open API — the hard limits

From [help.ctrader.com/open-api](https://help.ctrader.com/open-api/) (Getting started):

> "You can perform a maximum of **50 requests per second per connection** for any non-historical data requests."
> "You can perform a maximum of **5 requests per second per connection** for any historical data requests."

From [help.ctrader.com/open-api/symbol-data](https://help.ctrader.com/open-api/symbol-data/):

> "It is impossible to request historical tick data for a period larger than one week. As such, the difference between the specified `toTimestamp` and the `fromTimestamp` must not be larger than `604800000`."

From [help.ctrader.com/open-api/messages](https://help.ctrader.com/open-api/messages/) and [model-messages](https://help.ctrader.com/open-api/model-messages/):

- `ProtoOAGetTickDataReq` takes `type: ProtoOAQuoteType` = **BID(1) or ASK(2)** — **one side per request**. Getting both bid and ask means **2× the requests** and a client-side merge.
- `ProtoOAGetTickDataRes` returns `hasMore: bool` — responses are chunked; you must page.
- Tick timestamps are **delta-encoded**: "The first tick contains Unix time in milliseconds while all subsequent ticks have the time difference in milliseconds between the previous and the current one." The doc also says the list is "in chronological order (newest first)" — self-contradictory; **the actual ordering must be asserted at runtime by QMF, not assumed.**
- `ProtoOATickData` = `{timestamp: int64, tick: int64}`. `tick` is a price in points; divide by 100000 and round to symbol digits.
- `ProtoOATrendbar` = `{volume: int64, low: int64, deltaOpen: uint64, deltaHigh: uint64, deltaClose: uint64, utcTimestampInMinutes: uint32}`. So `open = low + deltaOpen`, etc., then `/100000`. **`volume` is "Bar volume in ticks"** — it is a tick *count*, not traded size. Any strategy treating cTrader bar volume as real volume is wrong.
- Bar timestamps are **minute-resolution uint32**, so sub-minute bar starts are not representable.
- `ProtoOATrendbarPeriod`: M1, M2, M3, M4, M5, M10, M15, M30, H1, H4, H12, D1, W1, MN1. **No M2/M3/M4 equivalents exist in most other vendors — do not assume a resolution grid.**
- Live: `ProtoOASubscribeSpotsReq` must succeed **before** `ProtoOASubscribeLiveTrendbarReq`.
- Whether cTrader trendbars are BID-derived or mid-derived is **UNVERIFIED** — must be established empirically against a known bid tick series.

A widely-cited limit of **14,000 bars per `ProtoOAGetTrendbarsReq`** and **25 concurrent connections per application** appears in community threads and third-party SDK docs but I could **not** find it in the current official pages — **UNVERIFIED**, treat as a runtime-discovered constraint.

#### 2.2 cTrader Python SDK — stale

[spotware/OpenApiPy](https://github.com/spotware/OpenApiPy) (`ctrader-open-api` on PyPI): **190 stars, last push 2024-08-07, last PyPI release 0.9.2 on 2024-06-26**, MIT, requires `Twisted 24.3.0` + `protobuf 3.20.1` + `pyOpenSSL`. Two years without a commit, and pinned to a protobuf version from 2022.

**This is a real risk for QMF.** The protocol itself (protobuf `.proto` files) is stable and vendor-published; the *Python wrapper* is not maintained. QMF should depend on the **protobuf definitions**, not on Twisted-era wrapper semantics, and keep the transport (TLS socket + length-prefixed protobuf) behind its own thin, testable adapter.

#### 2.3 MT5 — a platform trap for the Linux VPS

[`MetaTrader5` on PyPI](https://pypi.org/project/MetaTrader5/): latest **5.0.6090, uploaded 2025-01-18**, wheels for **`win_amd64` only**. The package works by IPC to a running MetaTrader 5 *terminal* process.

**Implication:** MT5 as a data source cannot run natively on the Linux VPS. It would require Wine or a second Windows box. Given cTrader-first, treat MT5 as workstation-only, optional, and never as a dependency of the live path.

---

### 3. Storage engines evaluated

#### 3.1 Parquet + DuckDB — recommended core

**DuckDB** ([duckdb/duckdb](https://github.com/duckdb/duckdb)): 40,277 stars, pushed 2026-08-17, **MIT**. Latest **v1.5.5 (2026-07-22)**; **v1.4.0 is the LTS line** with, per [the 1.4.0 announcement](https://duckdb.org/2025/09/16/announcing-duckdb-140), *one year of community support ending 2026-09-16* — i.e. the current LTS lapses in a month.

Why it fits:

- **Zero server.** `pip install duckdb`. Identical on Windows and Linux.
- **Queries Parquet directly** — no import step, no second copy of the data.
- **Hive partition pruning.** Per [DuckDB hive partitioning docs](https://duckdb.org/docs/current/data/partitioning/hive_partitioning.html), directory layouts of the form `key=value/` are auto-detected, and filters on partition columns are pushed down so only matching directories are read. A published benchmark on 365 daily partitions (~12 GB) reports a [30× improvement from pruning](https://duckdblab.org/en/post/duckdb-parquet-partition-pruning/).
- **Row-group statistics skipping.** Per [DuckDB Parquet tips](https://duckdb.org/docs/current/data/parquet/tips.html): DuckDB keeps per-column min/max per row group and *"uses these to skip row groups that cannot match a query's WHERE clause"*; and *"Sorting the data on the columns that you filter on most often before writing makes these min/max ranges tight and non-overlapping."* For a timestamp-sorted tick archive this is close to free indexing.
- **`PIVOT` without knowing the columns.** Per [DuckDB PIVOT docs](https://duckdb.org/docs/current/sql/statements/pivot.html), the simplified `PIVOT dataset ON columns USING values GROUP BY rows` syntax discovers distinct values at execution time — you do not have to hardcode the pair list. This is the cross-pair correlation matrix primitive (§7).
- **Attaches SQLite.** Per the [sqlite extension docs](https://duckdb.org/docs/current/core_extensions/sqlite.html), `ATTACH 'x.db' (TYPE sqlite)` makes SQLite tables queryable, and `COPY` moves data straight to Parquet. This is exactly the live-buffer → archive compaction path.
- **Zero-copy with Polars.** Per [DuckDB's Polars guide](https://duckdb.org/docs/current/guides/python/polars.html), DuckDB can query a Polars DataFrame by variable name in scope, and `.pl()` returns results as Polars (optionally lazy), via Arrow. Requires `pyarrow`.

**The decisive constraint** — from [DuckDB concurrency docs](https://duckdb.org/docs/current/connect/concurrency.html): *"one process can both read and write to the database"* while *"multiple processes can read from the database, but no processes can write."* It is single-writer-process, enforced with file locks, and the docs warn about network storage.

⇒ **A live collector holding a DuckDB file open for writing locks research out of that file entirely.** The architecture must not put the live writer and the research reader on the same DuckDB database. Reading *Parquet files* has no such lock — that is the escape.

**Partitioned writes** ([docs](https://duckdb.org/docs/current/data/partitioning/partitioned_writes.html)): `COPY t TO 'dir' (FORMAT parquet, PARTITION_BY (year, month))`, with `OVERWRITE_OR_IGNORE` / `APPEND` (UUID collision detection) / default-reject. Two documented caveats worth carrying into QMF's design: *"Writing data into many small partitions is expensive"* with a recommended **≥100 MB per partition**, and `partitioned_write_max_open_files` defaults to **100**. Also `PARTITION_BY` **cannot take an expression** — derive the partition column in a subquery.

#### 3.2 Polars — recommended as the transform layer

[pola-rs/polars](https://github.com/pola-rs/polars): 39,368 stars, pushed 2026-08-17, **MIT**. Latest Python release **py-1.43.2 (2026-08-01)**. The 1.x line has been stable since mid-2024.

Where it beats DuckDB for QMF specifically:

- **`join_asof`** ([docs](https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.join_asof.html)) — `strategy` ∈ {backward, forward, nearest}, plus `by` / `by_left` / `by_right` for per-symbol grouping and `tolerance` to cap the gap. This is *the* primitive for aligning multiple pairs' irregular tick streams onto a common clock without look-ahead. **Requires both frames sorted on the join key; unsorted input produces silently wrong results.**
- **`group_by_dynamic`** ([docs](https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.group_by_dynamic.html)) — `index_column`, `every`, `period`, `offset`, `label`, `closed`, `group_by`. This is tick→bar aggregation with explicit control of window closure and labelling, which is exactly where off-by-one bar-boundary bugs live.
- **Lazy API** ([docs](https://docs.pola.rs/user-guide/concepts/lazy-api/)) — `scan_parquet` + predicate pushdown + projection pushdown, `.explain()` to inspect the plan before running it. An LLM-authored strategy that accidentally asks for 20 years × 28 pairs of ticks gets that plan pruned before any I/O happens.
- **Hive support** ([docs](https://docs.pola.rs/user-guide/io/hive/)): hive parsing is **on by default when `scan_parquet` gets a single directory path**, and **off when given a list of file paths** unless `hive_partitioning=True`. Writing via `write_parquet(..., partition_by=[...])` is documented as **unstable** — prefer DuckDB `COPY … PARTITION_BY` or `pyarrow.dataset.write_dataset` for writes.
- **New streaming engine**: available from **1.31.1** and *"in time, it will become the default engine"* per the [Polars streaming guide](https://docs.pola.rs/user-guide/concepts/streaming/); out-of-core with disk spill, with transparent fallback to the in-memory engine for operations lacking a streaming implementation.

**Polars vs pandas for QMF:** Polars' expression API is *declarative and composable* — an expression is a value that can be validated, logged, hashed, and diffed. That is a far better substrate for the constrained surface LLM agents will author against than pandas' mutable-`DataFrame`-plus-chained-indexing model. Polars also has no `SettingWithCopyWarning`-class ambiguity and no implicit index. Keep pandas only where a third-party library demands it (`statsmodels`, `arch`) and convert at the boundary.

#### 3.3 ArcticDB — technically ideal, licence-blocked

[man-group/ArcticDB](https://github.com/man-group/ArcticDB): 2,483 stars, **pushed 2026-08-17**, latest release **v6.24.0+man0 (2026-08-17)**. Extremely alive. Wheels for Linux x86_64, Windows x86_64, macOS arm64, Python 3.9–3.14; conda-forge adds Linux arm64 and macOS x86_64. Storage: S3 / Azure Blob / **LMDB (local file)** / `mem://`.

Capabilities that map exactly onto QMF's problem ([Library API](https://docs.arcticdb.io/dev/api/library/)):

- `append()` — requires the new data's first index ≥ existing last index; validated by `validate_index=True` (default). Creates a new version.
- `update()` — replaces a contiguous date range wholesale (the *entire* range between first and last index entry of the input).
- `read(..., date_range=(lo, hi), columns=[...], query_builder=q)` — server-side (well, client-side C++) date-range slicing, column projection and predicate filtering.
- `read_batch()` / `write_batch()` / `append_batch()` — **parallel multi-symbol reads**, which is precisely the cross-pair access pattern.
- **Versioning / time-travel** via `as_of` (int version, snapshot name, or datetime) — genuinely valuable for reproducible backtests: pin a backtest to the exact data version it ran against.
- Staged writes (`write(..., staged=True)` + `finalize_staged_data()`) enable coordinated concurrent single-symbol writes.

Documented limits ([FAQ](https://docs.arcticdb.io/dev/faq/), [LMDB tutorial](https://docs.arcticdb.io/dev/tutorials/lmdb_and_in_memory/)):

- Concurrent writers to a **single symbol** are not supported outside staged writes; behaviour is last-writer-wins.
- Not a transactional system: *"does not isolate transactions"*, OLAP not OLTP.
- LMDB: *"you should ensure that you only have one Arctic instance open over a given LMDB database"* per process; LMDB **does not work with remote filesystems**; for multi-process concurrent access the docs recommend LMDB over **tmpfs** (i.e. RAM), which is not a durability story. Highest performance is stated to require an **S3 backend**.

**The licence.** [LICENSE.txt](https://github.com/man-group/ArcticDB/blob/master/LICENSE.txt) is **Business Source License 1.1**, Licensor *Man Group Operations Limited*, Change License *Apache 2.0*, with this Additional Use Grant verbatim:

> "You may make use of the Licensed Work under the terms of this License, provided that you may not use the Licensed Work for a Database Service. A 'Database Service' is a commercial offering that allows third parties (other than your employees and contractors) to access the functionality of the Licensed Work by creating tables whose schemas are controlled by such third parties."

Read alone, that permits solo trading use. **But Man Group's own [licensing FAQ](https://docs.arcticdb.io/latest/licensing/) states the opposite reading:**

> "For BSL versions of ArcticDB, a commercial agreement is required for any business use."
> "That includes use in research or dev environments, or where any economic benefit is being derived."
> "ArcticDB is available at no cost for non-commercial, personal, or academic use."

And the [README](https://github.com/man-group/ArcticDB#license) says: *"Use of ArcticDB in production (including business or commercial environments) or for a Database Service requires a paid for license from ArcticDB Limited."*

Trading one's own capital for profit derives economic benefit. **The vendor's stated interpretation is the operative risk, regardless of how the bare BSL text parses.** Pricing is not published; the FAQ mentions a "Small Team License" for up to 5 users and directs enquiries to `info@arcticdb.io` (**UNVERIFIED** pricing).

**The escape hatch — and its cost.** BSL converts each version to Apache 2.0 two years after that version's release. The README publishes the table. As of **2026-08-17**, versions **1.0 through 4.5 have already converted to Apache 2.0** (4.5's change date was **2026-08-14**, three days ago). 5.0 converts **2026-10-31**; 6.21 not until **2028-08-04**.

The last 4.5 wheels on PyPI are **`arcticdb==4.5.1` (2024-10-18)** — and that build line ships wheels only up to **CPython 3.11**. (Careful: the README table gives the 4.5 *line* a change date of 2026-08-14, which matches 4.5.0's 2024-08-13 release + 2 years; 4.5.1 released 2024-10-18 arguably converts 2026-10-18. **This distinction is legally load-bearing and should be confirmed with the vendor before relying on it.**)

⇒ Adopting free-as-in-Apache ArcticDB means **pinning a two-year-old build and capping QMF at Python 3.11**. That is a heavy tax for a solo operator, and it fights the rest of the stack (Polars, DuckDB, NautilusTrader all target 3.12+).

#### 3.4 Relational options

**SQLite** — bundled with Python, zero install, single file. In [WAL mode](https://www.sqlite.org/wal.html): readers do not block the writer and vice versa; **one writer at a time**; more sequential I/O; fewer `fsync()` calls. Documented limits that matter here: WAL **requires shared memory between processes, so it does not work over network filesystems** (all processes must be on the same host); `page_size` cannot be changed in WAL mode; not optimal for transactions >100 MB; adds `-wal` and `-shm` sidecar files.

⇒ SQLite WAL is the *only* zero-dependency local store that gives QMF **"collector writes while research reads"** on one box. That is exactly the live-buffer requirement. It is a bad *archive* (row-oriented, no columnar compression, no partition pruning) and a great *inbox*.

**PostgreSQL** — a server. Real users, real roles, real WAL, real replication, real backups, real patching. For one operator running one collector and one research session, every one of those is cost with no matching benefit. Its analytical performance on 5-billion-row tick scans is not competitive with a columnar engine.

**TimescaleDB** — [timescale/timescaledb](https://github.com/timescale/timescaledb): 23,337 stars, pushed 2026-08-17, latest release **2.29.1 (2026-08-04)**. Very much alive. The company [rebranded from Timescale to TigerData in June 2025](https://www.tigerdata.com/newsroom/timescale-becomes-tiger-data-defining-a-new-standard-as-the-fastest-postgresql-platform-for-modern-applications) — expect stale docs and split search results.

Its **licence is split**: an Apache-2.0 edition with core hypertables, and a **Timescale/Tiger License (TSL)** source-available edition that carries the features you'd actually want — **columnar compression (Hypercore), continuous aggregates, retention policies, hyperfunctions, vectorized execution** ([editions comparison](https://www.tigerdata.com/docs/about/latest/timescaledb-editions), [licence page](https://www.tigerdata.com/legal/licenses)). TSL is free for self-hosting and only forbids offering it as a managed service — so unlike ArcticDB it is **not** a licensing blocker for QMX. It is, however, still a PostgreSQL server the operator must run and maintain on the VPS, and its columnar compression is a subset of what a Parquet lake gives for free.

**Verdict:** Timescale is the right answer if QMX ever needs concurrent multi-writer ingest with SQL-level durability guarantees. It is the wrong answer for a single-operator research archive.

#### 3.5 Deprecated / not-candidates

- **[man-group/arctic](https://github.com/man-group/arctic)** (the original, MongoDB-backed, LGPL-2.1): 3,086 stars, **last push 2024-04-08**. Superseded by ArcticDB, in maintenance only. Do not adopt.
- **QuestDB / ClickHouse / InfluxDB** — capable, but all are servers and all impose operational surface a solo operator does not need. Not evaluated in depth.

---

### 4. Storage layout patterns

#### 4.1 Prior art worth stealing from

**NautilusTrader's `ParquetDataCatalog`** ([docs](https://nautilustrader.io/docs/latest/concepts/data/)) is the closest thing to a reference design for exactly QMF's problem. [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader): 25,659 stars, pushed 2026-08-17, LGPL-3.0, latest **v1.231.0 (2026-08-02)**, PyPI requires Python ≥3.12,<3.15. Its design:

```
catalog/
└── data/
    ├── quote_ticks/
    │   └── EURUSD.SIM/
    │       └── 2024-01-01T00-00-00-000000000Z_2024-01-01T23-59-59-999999999Z.parquet
    └── trade_ticks/
        └── BTCUSD.BINANCE/
```

Five ideas to copy outright:

1. **Directory = `<data_type>/<instrument_id>/`**, identifiers made URI-safe by stripping `/`.
2. **Filename encodes the covered time range**: `{start_ts}_{end_ts}.parquet`, ISO-8601 with `:` and `.` replaced by `-`. A file's coverage is knowable **without opening it**. This is a free index.
3. **Overlapping writes raise by default** (`skip_disjoint_check=True` to opt out). Silent overlap is the #1 way a tick archive quietly double-counts.
4. **Explicit compaction API**: `consolidate_catalog()` merges small files; `consolidate_data_by_period()` re-splits into fixed periods; `reset_all_file_names()` re-derives filenames from actual content. Compaction is a *named operation*, not an accident.
5. **Deletes split partially-overlapping files** to preserve data outside the deleted range, and are documented as irreversible.

**QuantConnect LEAN** ([Data/readme.md](https://github.com/QuantConnect/Lean/blob/master/Data/readme.md)) uses `/data/{securityType}/{market}/{resolution}/{ticker}/{date}_{tradeType}.zip` for tick/second/minute and `/data/{securityType}/{market}/{resolution}/{ticker}.zip` for hour/daily — i.e. **file granularity follows resolution**: fine resolutions get one file per day, coarse resolutions get one file per symbol. Steal that principle; skip the zipped-CSV format (no columnar pushdown, no statistics).

#### 4.2 Sizing arithmetic **[measured anchor + estimate]**

Measured EURUSD tick counts, 2026-06-12 UTC: hour 00 = 3,075; hour 06 = 3,231; hour 09 = 4,073; hour 15 = 5,310. Mean ≈ **3,922 ticks/hour**. **[measured]**

Derived (estimate, single-day sample, current-era liquidity):

| quantity | value |
|---|---|
| ticks/day (24h) | ~94,000 |
| ticks/week (5 trading days) | ~470,000 |
| ticks/year | **~24.5 M** |
| raw bi5 payload/year (20 B/tick) | ~490 MB |
| LZMA'd/year (measured 4.54×) | ~110 MB |
| 28 pairs × 10 years, current rates | ~6.9 B rows, ~140 GB raw |
| realistic, accounting for lower historic tick rates | **~3–5 B rows, ~15–30 GB as zstd Parquet** |

Two consequences: (a) the whole multi-pair tick archive **fits on a laptop SSD and on a modest VPS disk** — no distributed anything is needed; (b) it does **not** fit in RAM, so lazy/streaming execution (Polars streaming engine, DuckDB out-of-core) is mandatory, not optional.

#### 4.3 Concrete partition scheme for QMF

Design constraints in tension:
- DuckDB says **≥100 MB per partition** and warns that many small partitions are expensive to write ([docs](https://duckdb.org/docs/current/data/partitioning/partitioned_writes.html)).
- DuckDB's default `ROW_GROUP_SIZE` is **122,880 rows**, and the rule of thumb is *"ensure that the number of row groups per file is at least as large as the number of CPU threads"* ([Parquet tips](https://duckdb.org/docs/current/data/parquet/tips.html)).
- Independent guidance converges on 128–512 MB row groups for batch and **100k–1M rows** for interactive filtering workloads ([Dremio](https://medium.com/data-engineering-with-dremio/all-about-parquet-part-10-performance-tuning-and-best-practices-with-parquet-d697ba4e8a57)).
- Partitioning by day would give EURUSD ~94k rows ≈ 1–2 MB per file — **far too small**, and 28 pairs × 20 years × 260 days ≈ **145,000 files**.

**Recommendation:**

```
lake/
  ticks/       symbol=EURUSD/year=2026/month=06/part-000.parquet     # ~2.4 M rows, ~30–60 MB
  bars_m1/     symbol=EURUSD/year=2026/part-000.parquet              # ~370 k rows/yr
  bars_h1/     symbol=EURUSD/part-000.parquet                        # one file per symbol, all history
  live_raw/    symbol=EURUSD/date=2026-08-17/part-000.parquet        # staging only, compacted nightly
```

- **Ticks: `symbol / year / month`** → ~2.4 M rows and 30–60 MB per file for a major pair; ~6,700 files for 28 pairs × 20 years. Under the 100 MB ideal but well clear of the small-file cliff, and month granularity is the natural unit for IS/OOS slicing.
- **Bars M1 and coarser: `symbol / year`** (or single-file for H1+). 20 years of M1 for one pair is ~7.5 M rows — one file.
- **Within every file, sort by `(symbol, ts)` before writing** so row-group min/max on `ts` are tight and non-overlapping — that is what makes `WHERE ts BETWEEN …` skip row groups ([Parquet tips](https://duckdb.org/docs/current/data/parquet/tips.html)).
- Compression **zstd** (Parquet-native, better ratio than snappy at similar decode speed).
- Store `ts` as `TIMESTAMP` with **nanosecond or microsecond** precision, always **UTC**, never naive local time.
- **`symbol` appears BOTH as a partition key and as a column in the file.** Partition-key-only means every read of a single file loses the symbol; column-only means no pruning. Carry both, and validate they agree during compaction.

#### 4.4 Appending: Parquet is immutable

A Parquet file's footer holds its schema and row-group statistics and is written last; adding rows means rewriting the file. Every write API reflects this: `pyarrow.dataset.write_dataset` offers `existing_data_behavior` ∈ `{'error', 'overwrite_or_ignore', 'delete_matching'}` plus `basename_template`, `max_rows_per_file`, `min_rows_per_group`/`max_rows_per_group` (default 1,048,576) and a `file_visitor` callback ([docs](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.write_dataset.html)); DuckDB's `APPEND` mode adds *new files with UUID names* into an existing partition rather than modifying existing ones ([docs](https://duckdb.org/docs/current/data/partitioning/partitioned_writes.html)).

⇒ **The append story must be a two-tier one:** an appendable hot store, plus a scheduled compaction into the immutable archive. This is the same conclusion Nautilus reached with `consolidate_catalog()`.

**QMF's append pipeline:**

1. Collector writes each tick into **SQLite (WAL)** `live_ticks(symbol, ts_ms, bid, ask, bid_vol, ask_vol)` with a `(symbol, ts_ms)` index. Single writer, durable, readable concurrently.
2. Research reads the union: `read_parquet('lake/ticks/**/*.parquet')` UNION ALL the SQLite tail via DuckDB `ATTACH … (TYPE sqlite)`. The seam is one SQL view, `qmf.ticks`.
3. A nightly/weekly compaction job: read yesterday's SQLite rows → dedupe on `(symbol, ts, bid, ask)` → sort → `COPY … TO 'lake/ticks' (FORMAT parquet, PARTITION_BY (symbol, year, month), APPEND)` → verify row counts → **only then** delete from SQLite.
4. A separate monthly `compact` step rewrites each `symbol/year/month` partition into a single sorted file (the equivalent of Nautilus `consolidate_data_by_period`).
5. Every compaction writes a **manifest row**: partition, row count, min ts, max ts, source (dukascopy/ctrader), sha256 of the file, wall-clock of the run. TickVault's use of a SQLite manifest for exactly this is a good pattern to copy ([TickVault](https://github.com/keyhankamyar/TickVault)).

#### 4.5 Reconciling two sources into one timeline

Historical (Dukascopy) and live (cTrader) prices come from **different liquidity providers** and will not agree tick-for-tick. QMF must:

- Store a **`source` column** in every row (or at minimum every partition), never silently mix.
- Keep **separate symbol namespaces** or a `source` partition key at the boundary, so a backtest can declare which feed it ran on.
- Maintain an explicit **overlap window** where both feeds exist, and a stored reconciliation report (median bid/ask delta, spread distribution difference, tick-count ratio) so the operator can see how much the swap costs.
- Never let a strategy silently backtest on Dukascopy and trade on cTrader without that report having been generated.

---

### 5. In-sample / out-of-sample and walk-forward data management

**Principle: the split is data, not code.** A split must be a persisted, named, immutable artefact — otherwise a strategy that "worked out-of-sample" cannot be audited, and an LLM agent authoring strategies can trivially (and invisibly) leak.

Design:

- A **split registry** (a small table/JSON, versioned in git) of named windows: `{split_id, kind: is|oos|embargo, symbol_set, t_start, t_end, created_at, created_by}`.
- `qmf.data.load(split_id=...)` is the **only** way a strategy obtains data. There is no API that takes raw dates. An agent cannot reach into the future because the function signature does not let it.
- **A permanently sealed holdout**: the most recent N months, never returned by any research API, only by an explicitly-privileged `final_validation` path that logs every call. This is the strongest structural defence against a solo operator's own iteration bias.
- **Purging and embargo.** Standard walk-forward trains on `[t0,t1)` and tests on `[t1,t2)`, but with overlapping labels (any multi-bar holding period) the last training samples leak into the test set. [Purged cross-validation](https://en.wikipedia.org/wiki/Purged_cross-validation) — López de Prado, 2017 — removes training observations whose label windows overlap the test set (*purging*) and additionally drops samples immediately after the test set (*embargo*). QMF's split registry should represent the embargo as a **first-class `kind: embargo` window**, so it is visible in the data layer rather than buried in a training loop.
- **Combinatorial Purged CV (CPCV)** partitions data into N ordered groups, tests on all C(N,K) combinations, and yields many OOS paths instead of the single chronological path walk-forward gives. Worth supporting later; it multiplies compute by C(N,K) and its main benefit is a *distribution* of OOS outcomes rather than one number. Not v1.
- **Data versioning for reproducibility.** Because Parquet files are immutable and named by content range, a backtest result should record the **manifest sha256s of every partition it read**. That gives ArcticDB's `as_of` time-travel benefit without ArcticDB's licence. Re-running a 6-month-old backtest and getting a different number because the archive was backfilled is a silent, corrosive failure mode.

---

### 6. Cross-pair access patterns

The distinguishing workload: "give me aligned closes for 28 pairs over 5 years and compute a correlation matrix / run a cointegration scan". Three things make or break it.

**(a) Long vs wide.** Store **long** (`ts, symbol, price`) — it partitions cleanly, appends cleanly, and tolerates pairs with different histories. Pivot to **wide** (`ts, EURUSD, GBPUSD, …`) only at query time, in memory. A 28-pair × 5-year M1 wide frame is ~1.8 M rows × 28 float64 ≈ **400 MB** — comfortably in RAM on any modern machine.

DuckDB's dynamic PIVOT does this without hardcoding the pair list ([docs](https://duckdb.org/docs/current/sql/statements/pivot.html)):

```sql
PIVOT (SELECT ts, symbol, close FROM read_parquet('lake/bars_m1/**/*.parquet')
       WHERE ts BETWEEN $t0 AND $t1)
ON symbol USING first(close) GROUP BY ts;
```

Polars equivalent: `.pivot(on="symbol", index="ts", values="close")`.

**(b) Alignment.** Forex pairs do not tick simultaneously, and different pairs have different holiday calendars. Two correct approaches, one wrong one:

- ✅ Resample every pair onto a **common bar grid** (`group_by_dynamic`), then forward-fill *within a bounded tolerance*.
- ✅ `join_asof(strategy="backward", tolerance=...)` against a reference clock — this is the tick-accurate version and is what pairs trading on ticks requires.
- ❌ Unbounded `forward_fill` across a weekend or a broker outage. This manufactures fake stationarity and will produce beautiful, false cointegration.

**(c) Correlation and cointegration at scale.** 28 pairs → 378 unordered pairs → 378 Engle–Granger tests per rolling window. That is fine; 200 instruments (19,900 pairs) is not. Practical shape:

1. **Screen with correlation** (cheap, vectorised — one matrix op on the wide frame, or DuckDB's `corr()` aggregate).
2. **Test only survivors** with Engle–Granger (`statsmodels.tsa.stattools.coint`) or Johansen (`statsmodels.tsa.vector_ar.vecm.coint_johansen`). Engle–Granger handles 2 series; Johansen handles n>2 and treats every asset symmetrically, returning trace and max-eigenvalue statistics.
3. **Correct for multiple testing.** 378 tests at α=0.05 yields ~19 false positives by construction. Without a Bonferroni/FDR correction a "cointegration scanner" is a random-pair generator. This is the most common failure in retail pairs-trading code and QMF should bake the correction into the scan API rather than leaving it to the strategy author.
4. **Forex majors are largely driven by USD**, so raw correlations are high and largely spurious; cointegration among the seven majors is often absent. Expect the scan to mostly return nothing, and treat "it found 40 pairs" as a bug signal.

**Access-pattern implication for storage:** cross-pair queries read **all symbols for a narrow time range** — the opposite of single-strategy backtests, which read **one symbol for a wide time range**. The `symbol/year/month` layout serves both: the first prunes on year/month across all symbol directories, the second prunes on the symbol directory. A layout partitioned by *date only* would serve cross-pair well and single-pair terribly; symbol-only the reverse. Keep both keys.

---

## What QMF should copy / avoid

### The recommended stack

| Layer | Choice | Why |
|---|---|---|
| **Historical acquisition** | Own thin Python downloader for Dukascopy `.bi5` (`lzma` + `struct.unpack('>iiiff')` — both stdlib) | Format verified first-hand and trivially small (~40 lines). Beats depending on a 25-star package or shelling out to Node. Zero runtime dependencies. |
| **Live acquisition** | cTrader Open API over own protobuf adapter | The published SDK is 2 years stale (§2.2); depend on the `.proto` definitions, not the Twisted wrapper. |
| **Hot / live buffer** | **SQLite, WAL mode**, one file per VPS | Only local store giving concurrent write+read with zero install. Rolled to Parquet nightly. |
| **Archive** | **Hive-partitioned Parquet, zstd**, `symbol/year/month` for ticks | Immutable, portable, engine-agnostic, cheap to back up (rsync), survives every tool in this table. |
| **Query engine** | **DuckDB** (MIT, v1.5.x; pin the current LTS) | Serverless, reads Parquet in place, partition pruning + row-group skipping, dynamic PIVOT, ATTACHes SQLite. |
| **Transform layer** | **Polars** (MIT, py-1.43.x) | `join_asof`, `group_by_dynamic`, lazy plans that an LLM-authored strategy cannot accidentally blow up. Zero-copy to/from DuckDB via Arrow. |
| **Escape hatch** | Arrow as the in-memory interchange type at every seam | Lets any of the above be swapped without touching strategy code. |

### Copy

1. **Nautilus's filename-encodes-time-range convention** (`{start_ts}_{end_ts}.parquet`) plus its **overlapping-writes-raise-by-default** policy and its **named compaction operations**. Three cheap ideas that eliminate whole classes of silent archive corruption.
2. **LEAN's principle that file granularity follows resolution** — ticks per month, minutes per year, hours per symbol.
3. **TickVault's SQLite download manifest** with resume and explicit gap detection. QMF should be able to answer "which hours of EURUSD do I not have?" from a table, in milliseconds, without touching the filesystem.
4. **ArcticDB's `as_of` reproducibility idea, implemented cheaply**: record the sha256 of every partition a backtest read, in the backtest's result record.
5. **DuckDB's own advice**: sort by the filter column before writing; keep row groups ≥ thread count; keep partitions large.
6. **Long storage, wide-at-query-time.**
7. **Splits as persisted named artefacts**, with `kind: embargo` as a first-class window type.

### Avoid

1. **Do not adopt ArcticDB.** Man Group's licensing FAQ asserts a paid agreement is required for *any business use including research where economic benefit is derived*. The Apache-converted ≤4.5 route caps QMF at Python 3.11 on a two-year-old build. The features it buys (time-travel, batch reads) are reproducible on Parquet for a fraction of the risk. **Revisit only if the operator decides to buy a licence, or in Oct 2028 when 6.x converts.**
2. **Do not run PostgreSQL or TimescaleDB for the research archive.** A server to patch, tune, back up and monitor, in exchange for nothing a single operator needs. (Timescale's licence is *not* the problem — TSL permits self-hosting; the operational surface is.)
3. **Do not let the live collector and the research session share a DuckDB file.** DuckDB is single-writer-process ([docs](https://duckdb.org/docs/current/connect/concurrency.html)); this deadlocks the workflow the first time both run at once.
4. **Do not put a DuckDB or SQLite-WAL file on a network mount.** DuckDB's docs warn about file locking on network storage; SQLite WAL *cannot work* over a network filesystem because it requires shared memory.
5. **Do not use `giuse88/duka`** — last commit 2017-08-06.
6. **Do not partition ticks by day.** ~1–2 MB files, ~145,000 of them, and DuckDB explicitly warns that many small partitions are expensive.
7. **Do not treat cTrader `ProtoOATrendbar.volume` as traded volume.** It is a tick count.
8. **Do not assume Dukascopy price fields are floats.** They are int32 point values. The most-linked format README on GitHub gets this wrong.
9. **Do not treat an empty/error Dukascopy response as "no ticks".** 503-on-burst was observed directly; conflating it with a genuine quiet hour silently perforates the archive.
10. **Do not forward-fill across weekends** when aligning pairs. Bound every fill with an explicit tolerance.
11. **Do not run a cointegration scan without multiple-testing correction.**
12. **Do not depend on `MetaTrader5` in anything that must run on the VPS** — Windows-only wheels.
13. **Do not use Polars' `write_parquet(partition_by=...)` for the archive yet** — the docs mark it unstable. Write with DuckDB `COPY … PARTITION_BY` or `pyarrow.dataset.write_dataset`.
14. **Do not build QMF's data API around pandas.** Convert at third-party boundaries only.

### The API surface QMF should expose (the part LLM agents see)

Narrow deliberately. Everything below is enforceable in one module:

```python
qmf.data.symbols() -> list[Symbol]
qmf.data.load_bars(symbols, timeframe, split_id) -> pl.LazyFrame   # long format
qmf.data.load_ticks(symbols, split_id) -> pl.LazyFrame
qmf.data.aligned(symbols, timeframe, split_id, fill_tolerance) -> pl.LazyFrame  # wide
qmf.data.coverage(symbol) -> Coverage    # what exists, where the holes are
```

Three properties that matter more than the signatures:
- **No function takes raw start/end dates.** Only `split_id`. Look-ahead becomes structurally impossible rather than merely discouraged.
- **Everything returns a `LazyFrame`.** An agent that writes a catastrophically wide query gets it pruned before I/O.
- **`fill_tolerance` is required, not defaulted.** The author must state how much staleness they accept.

---

## Open questions

1. **Dukascopy terms of use — operator decision.** The literal text forbids automated acquisition and database construction (§1.3). Options: (a) accept the risk for personal, non-redistributed use; (b) buy commercial historical data (which vendors, what budget?); (c) build history solely from the broker's own API (cTrader tick history is capped at 1 week per request at 5 req/s — how far back does *your* broker actually retain?). **This gates the whole data foundation and needs an explicit, recorded decision.**

2. **Which cTrader broker, and what is its actual tick-history depth?** The API's per-request limits are documented; the *retention* is broker-specific and I found no authoritative statement. Must be measured empirically against the live account before committing.

3. **Are cTrader trendbars BID-derived or mid-derived?** UNVERIFIED. Must be established by comparing a downloaded M1 trendbar series against a reconstructed series from BID ticks. Affects every backtest-to-live comparison.

4. **The 14,000-bar `ProtoOAGetTrendbarsReq` limit and the 25-connections-per-app limit** appear only in community sources. UNVERIFIED. Discover at runtime and encode as configuration, not constants.

5. **DuckDB LTS timing.** 1.4.0's community support ends **2026-09-16**, one month out. Pin to 1.4.x LTS and accept an imminent EOL, or track 1.5.x and accept a shorter support horizon? Whether a 1.5.x LTS has been designated is **UNVERIFIED**.

6. **ArcticDB version-conversion legal detail.** The README table assigns "4.5 → 2026-08-14", derived from 4.5.0's release. Whether the patch release `4.5.1` (2024-10-18) converts on that date or on 2026-10-18 is legally load-bearing if this route is ever taken. Would need a written answer from `info@arcticdb.io`. Also unknown: actual "Small Team License" pricing.

7. **How many pairs, really?** 28 majors/minors is a very different sizing problem from 200+ crosses. The recommended partition scheme is tuned for ~28. Needs an operator decision before the first bulk download.

8. **Nanosecond or microsecond timestamps?** Dukascopy is millisecond-resolution; cTrader is millisecond-resolution. Nanosecond `TIMESTAMP_NS` (Nautilus's choice) costs nothing in Parquet and future-proofs for crypto; microsecond is more universally supported by older tooling. Cheap now, expensive to change later.

9. **Backup and integrity policy for the VPS.** The archive fits on one disk (§4.2), which makes rsync-to-workstation viable. But nothing here specifies: how often, verified how (sha256 manifest comparison?), and what the restore drill looks like. A solo operator with no backup drill effectively has no archive.

10. **Crypto later.** Crypto trades 24/7 with no weekend gap, has per-exchange order books rather than a single bid/ask, and has far higher tick rates. Does the `symbol/year/month` tick layout hold, or does crypto need `symbol/year/month/day`? Worth deciding the *rule* (target ~50 MB/file) rather than the *value* now.

11. **Is a separate "features" tier needed?** Rolling z-scores, spreads, and cointegration residuals are expensive to recompute per backtest. A third Parquet tier (`lake/features/`) keyed by feature-definition hash would help — but it introduces cache-invalidation, which is the classic way a research archive silently goes stale. Defer, but decide consciously.
