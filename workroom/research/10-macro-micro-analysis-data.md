# 10 — Macro & Micro Analysis Data: Sources, Metrics, and Point-in-Time Storage

**Research date:** 2026-08-17. Every maintenance state, licence and endpoint response was checked on that date unless noted.
**Area:** The non-price data subsystem. What macro series enter QMF and from where; what "micro analysis" means concretely on cTrader tick data; which analyst-hat libraries earn their place; and the one storage shape that holds historical, revised, and forward-dated data without letting a backtest cheat.
**Method:** Primary sources only. Where an API is free and unauthenticated I **called it and pasted what came back**. GitHub state via the `gh` API (`pushed_at`, `archived`, SPDX licence); package state via the PyPI JSON API (version + upload date + declared licence). Terms of use read in full, not summarised from blogs. Anything I could not confirm against a primary source is tagged **UNVERIFIED**.

**Relationship to existing files.** This file does not re-cover file 02 (Parquet/DuckDB/Polars price stack, Dukascopy, `split_id` rule), file 03 (TA-Lib, talipp, pandas-ta-classic, quantstats, statsmodels/sklearn splitters), file 05 (cTrader Open API), or the fragments of this area already in file 06 (FairEconomy calendar has no `actual`; `investpy`/`ecocal` dead; DXY is ICE property; FX cointegration decays). It picks up exactly where those stopped. Two places where I **disagree with an earlier file** are flagged inline in §9.3 and §5.1.

---

## In plain words

1. The single most useful macro number in foreign exchange is the **gap between two countries' central-bank interest rates**, and I found one free web address that returns all eight of our currencies' policy rates in a single request, with no sign-up and no key — I called it today and it worked.
2. That address belongs to the Bank for International Settlements, the central bankers' own bank, so it is about as authoritative and as stable as free data gets.
3. Everything else we need — European Central Bank rates, UK Bank Rate, Swiss, Japanese, Australian and Canadian data, US Treasury yields, inflation prints — is also free and also worked when I called it, but each one is a different address in a different shape, so QMF needs one small adapter per source rather than one magic library.
4. There is a trap in this area that would silently ruin every backtest we ever run, and I confirmed it is real today: **economic numbers get rewritten after they are published**. The unemployment figure you can download now is not the figure that was on the screen the day the trade happened.
5. The US Federal Reserve runs a service (ALFRED) that remembers every old version of every number — this is the fix — but it **requires a free registered key**, and the key-free shortcut that hundreds of blog posts recommend is broken: I called it, it returned a "success" and quietly handed back today's numbers instead of the old ones. Anyone who trusts it gets a backtest that looks great and is a lie.
6. So the ruling is simple and non-negotiable: **every macro number QMF stores carries two dates** — the date it is *about*, and the moment we could first have *known* it. Backtests may only ever filter on the second one.
7. The same two-date rule is what makes "future data" work without any extra machinery. A scheduled event that has not happened yet is just a row whose "about" date is in the future and whose value is empty. A forecast is the same row with a value and a label saying it is a forecast. Nothing special is needed.
8. For positioning data, the US regulator publishes free weekly figures on how hedge funds are positioned in currency futures. I pulled the live file today. But the honest evidence, from a New York Federal Reserve study, is that this data explains what *already happened* that week and **does not predict next week** — so it is a context reading for the market-view subsystem, never a trade trigger.
9. For an economic calendar that includes the **actual released number** (not just the schedule), there is no longer a free option: the long-standing free "guest" account at the main commercial provider was switched off — I hit it today and got a "discontinued" error — and every other provider now demands a paid key. The realistic cheap path is to poll the free schedule feed every day from day one and build our own archive.
10. On the "micro" side, we have to be honest about what a retail cTrader account can see: bid and ask prices tick by tick, and a *count* of ticks — never real traded volume, never a full order book. That rules out most textbook microstructure work.
11. What it does not rule out is the thing that actually matters for prop-firm trading: measuring **the spread**, hour by hour and day by day, per pair. "Is this pair currently cheap enough to trade?" is answerable from data we already have, and it is worth more to us than any exotic indicator.
12. Nobody has published a good, correctly-licensed Python library for these FX-specific micro measurements. The best prior art is NautilusTrader, which already implements the exotic bar types (tick bars, volume bars, imbalance bars) properly; we can read it, and its two-timestamp discipline is exactly the pattern we are adopting.
13. On the analyst's toolbox, the operator's instinct was right — there is much more than pandas and NumPy — but the useful list is short, not long. **Five** libraries earn a place: `arch`, `statsmodels`, `ruptures`, `pandera`, and one charting library. Most of the famous rest are research-laptop-only and must never be installed on the trading server.
14. For storage, nothing new needs to be bought or installed. The Parquet + DuckDB + Polars stack already ratified handles all of this, because both DuckDB and Polars have a built-in "as of" join — the exact operation that answers "what did we know at 09:30 on that Tuesday" — and Polars even has a switch that forbids using a number released at the same instant as the bar.
15. Total verdict: **five macro sources for version one** (BIS policy rates, ECB, FRED/ALFRED with a key, the CFTC positioning file, and the free calendar feed we archive ourselves), **four micro metrics**, **five analyst libraries**, and **one storage table** with two dates on every row.

---

## Findings

# Part A — Macro data sources and access

## 1. What actually moves FX, ranked by strength of causal story

This is the filter I applied before auditing any API. A series earns ingestion only if there is a defensible mechanism linking it to a *currency pair*, not to a single economy.

| Rank | Input | Mechanism | Frequency achievable free | QMF role |
|---|---|---|---|---|
| 1 | **Policy-rate differential** (e.g. RBA cash rate − BoJ rate) | Direct: it *is* the carry the operator earns or pays on an overnight position; it is also the broker's swap rate driver | Daily (BIS `WS_CBPOL`) | Confirmation + gate; per-currency library input |
| 2 | **2y government yield differential** | Market's forward expectation of (1); moves *before* the central bank does | Daily (FRED `DGS2`, ECB, BoE) | Confirmation (the faster version of 1) |
| 3 | **Scheduled high-impact event in the next N minutes** | Mechanical: spreads widen, stops get run, prop-firm rules are breached | Event-level (FairEconomy + FRED release calendar) | **Hard gate — highest v1 value** |
| 4 | **Inflation surprise** (actual − consensus) | Repricing of (1) and (2) | Event-level, requires a paid `actual`+`consensus` feed (see §5) | Confirmation |
| 5 | **Terms of trade / commodity proxy** (iron ore→AUD, oil→CAD, dairy→NZD) | Real income shock to a commodity exporter | Daily via commodity futures; monthly via ABS/StatCan | Confirmation for AUD/CAD/NZD only |
| 6 | **Employment prints** (US NFP, AU labour force) | Repricing of (1) | Event-level | Gate (§3) + surprise if `actual` is available |
| 7 | **PMIs** | Leading indicator of (4) and (6) | Monthly; **S&P Global PMIs are licensed, not free** (see §2.9) | Optional |
| 8 | **Speculative positioning** (CFTC COT) | Crowding / squeeze risk | Weekly with a 3-day lag | Context only — see §3.3 |
| 9 | **Broad effective exchange rate** (BIS EER) | The "is the dollar strong against everything, or just against us" question — the honest free substitute for DXY | Daily (BIS `WS_EER`) | Confirmation; complements the synthetic index from file 06 |

Everything below rank 9 (GDP, current account, retail sales, consumer confidence) I judge **not worth ingesting for v1**: quarterly or noisy, heavily revised, and their FX impact is already in the price by the time a retail operator can act.

---

## 2. Endpoint audit — every one of these was called on 2026-08-17

### 2.1 BIS — the highest-value single finding in this file

**Base URL (verified):** `https://stats.bis.org/api/v2/` — SDMX 2.1 REST, **no API key, no registration**.

`WS_CBPOL` ("Central bank policy rates") returns every FX bloc's policy rate in **one request**:

```
GET https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.US+GB+JP+XM+AU+NZ+CA+CH?lastNObservations=1&format=csv
```

Live response, 2026-08-17:

| REF_AREA | TIME_PERIOD | OBS_VALUE |
|---|---|---|
| US | 2026-08-11 | 3.625 |
| XM (euro area) | 2026-08-11 | 2.25 |
| GB | 2026-08-10 | 3.75 |
| JP | 2026-08-11 | 1 |
| AU | 2026-07-30 | 4.35 |
| NZ | 2026-08-07 | 2.5 |
| CA | 2026-08-10 | 2.25 |
| CH | 2026-08-11 | 0 |

That is the entire rate-differential matrix for all 28 major pairs, from one free unauthenticated call. Nothing else in this file comes close on value-per-line-of-code. The CSV also carries a `COMPILATION` metadata field explaining the series definition ("From 19 Dec 1985 onwards: mid-point of the Federal Reserve target rate…"), which is exactly the provenance a knowledge-library agent needs.

**Full BIS dataflow inventory** (verified via `GET https://stats.bis.org/api/v2/structure/dataflow/BIS/all/latest?detail=allstubs`, 29 dataflows). The FX-relevant ones:

| Dataflow | Name | QMF use |
|---|---|---|
| `WS_CBPOL` | Central bank policy rates | **ADOPT — v1** |
| `WS_EER` | Effective exchange rates | ADOPT — broad/narrow NEER+REER, the DXY substitute |
| `WS_XRU` | US dollar exchange rates | Reference/cross-check only (we have broker quotes) |
| `WS_LONG_CPI` | Consumer prices statistics | Long inflation history, cross-country comparable |
| `WS_CBTA` | Central bank total assets | QE/QT proxy — research only |
| `WS_DER_OTC_TOV` | OTC derivatives turnover | Triennial only; context for §6 session work |
| `BIS_REL_CAL` | BIS_RELEASE_CALENDAR | **Listed but returns HTTP 404 "No results for query"** — an external-reference stub with no data behind it. Do not plan on it. |

`WS_EER` verified: `GET .../BIS/WS_EER/1.0/D.N.B.US?lastNObservations=2&format=csv` → US nominal broad EER = 102.04 on 2026-08-11, daily, `TITLE_TS` = "United States - Nominal - Broad (64 economies)".

**Terms** (https://data.bis.org/help/legal): commercial use **is permitted**; BIS must be cited as the source; a translation must be labelled non-official; you may not imply BIS endorsement. On automation, BIS "reserves the right to monitor the usage of the APIs" and to "limit or suspend any User's IP address access to the APIs at any time and without notice for any reason." No published numeric rate limit. → **Low risk. Cite BIS, poll once daily, do not hammer.**

### 2.2 ECB Data Portal — verified working, no key

**Base URL:** `https://data-api.ecb.europa.eu/service/data/{FLOW}/{KEY}`

Verified calls:

```
GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?lastNObservations=2&format=csvdata
→ 200. EUR/USD ECB reference rate, 2026-08-13 = 1.1534, 2026-08-14 = 1.1567

GET https://data-api.ecb.europa.eu/service/data/FM/D.U2.EUR.4F.KR.DFR.LEV?lastNObservations=2&format=csvdata
→ 200. ECB Deposit Facility Rate, 2026-08-16 = 2.25
```

`format=csvdata` is the sane output — flat SDMX-CSV with every attribute inlined. `format=jsondata` returns SDMX-JSON, which is a nested dimension-index structure that is genuinely painful to parse by hand; **prefer CSV everywhere SDMX is involved** (this applies to BIS, OECD and Eurostat too).

Note the ECB reference rate is a **daily 14:15 CET fixing**, not a tradeable rate — it is a benchmark/reconciliation series, not a price feed. Do not confuse it with broker quotes.

**Terms** (https://www.ecb.europa.eu/services/disclaimer/html/index.en.html): reuse permitted; "the ECB must be cited as the source"; commercial resale permitted but buyers must be told the data is free from the ECB site; **any transformation (seasonal adjustment, growth rates) must be stated explicitly**. That last clause is a real obligation for QMF: if the MIS publishes a "rate differential" derived from ECB data, the derivation must be labelled. → **ADOPT, with a provenance field in the store.**

### 2.3 FRED and ALFRED — and a live trap that would poison every backtest

**FRED API base:** `https://api.stlouisfed.org/fred/…` — **API key required**. Verified:

```
GET https://api.stlouisfed.org/fred/series?series_id=DGS10&file_type=json
→ 400 {"error_message":"Bad Request.  Variable api_key is not set."}
```

The key is free on registration (https://fred.stlouisfed.org/docs/api/api_key.html). The Terms of Use (https://fred.stlouisfed.org/docs/api/terms_of_use.html), read in full, impose four things that matter to us:

- **Mandatory notice:** "Place the following notice prominently on your application: *This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.*"
- **Third-party copyright pass-through:** "Data series available through the FRED® API may be owned by third parties and subject to copyright restrictions… **Before using data series owned by third parties for anything other than your own personal use, you must contact the data owner to obtain permission.**" Copyrighted series are identifiable — they contain the word `Copyright` in their notes and can be found via `fred/series/search`.
- **No published numeric rate limit.** The terms only say the Bank "may impose or adjust the limit on the amount of bandwidth you may use or the number of transactions you may send". The widely-quoted "120 requests per minute" figure is **UNVERIFIED** — it does not appear in the terms document.
- No cloaking of identity; no use of "FRED"/"ALFRED"/"Federal Reserve" in our hostname.

→ **OPERATOR RISK DECISION #1:** FRED is safe for QMF's own internal use. But if a per-currency knowledge library ever *republishes* a FRED-sourced chart or number to anyone other than Mubarak, the third-party-copyright clause becomes live and the copyright status of each series must be checked first. Cheapest mitigation: restrict FRED ingestion to series whose notes do **not** contain "Copyright", and record that check in the store.

**The unauthenticated CSV back door and why it is dangerous.**

`https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10` works with **no key at all**. Verified: returned the 10-year Treasury constant-maturity series through 2026-08-13 (4.63). Tempting.

The trap: this endpoint **accepts `&vintage_date=` and silently ignores it**. Verified side by side today:

```
GET https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPC1
  first row 1947-01-01,2182.681 … last row 2026-04-01,24270.599

GET https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPC1&vintage_date=2020-05-01
  first row 1947-01-01,2182.681 … last row 2026-04-01,24270.599   ← IDENTICAL
```

A May-2020 vintage of US real GDP cannot contain observations dated 2026. The parameter is dropped, HTTP 200 is returned, and the caller receives today's numbers believing they are the 2020 vintage. The ALFRED host is no better: `https://alfred.stlouisfed.org/graph/fredgraph.csv?id=GDPC1&vintage_date=2020-05-01` returns **HTTP 404** with an HTML error page.

→ **Hard rule for QMF:** the key-free `fredgraph.csv` route is permitted **only** for series QMF treats as never-revised (market rates such as `DGS2`, `DGS10`, `DTWEXBGS`). For anything revisable, the **registered-key `fred/series/observations` endpoint with explicit `realtime_start`/`realtime_end` is the only acceptable path**, and an ingestion adapter that passes `vintage_date` to `fredgraph.csv` must be treated as a defect, not a shortcut.

### 2.4 OECD — works, SDMX, best cross-country comparability

```
GET https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_KEI@DF_KEI,4.0/AUS.M.IRSTCI.....?lastNObservations=2
Accept: application/vnd.sdmx.data+csv; charset=utf-8
→ 200. AUS immediate interest rate, 2026-06 = 4.35, 2026-05 = 4.31
```

No key. The `Accept` header is what selects CSV; without it you get SDMX-ML. The dataflow addressing scheme (`AGENCY,DATAFLOW,VERSION` then a positional dot-separated key with empty slots) is the most awkward of any source here — note the five consecutive dots in the example, each a wildcard dimension.

**Terms** (https://www.oecd.org/en/about/terms-conditions.html), quoted: "you can extract from, download, copy, adapt, print, distribute, share and embed Data for any purpose, **even for commercial use**… You must give appropriate credit to the OECD by using the citation associated with the relevant Data". Sub-licensees must carry the same acknowledgment. → **ADOPT for research; skip for v1 production** (BIS + ECB + FRED cover the same ground with cleaner addressing).

### 2.5 Eurostat — works, JSON-stat, no key

```
GET https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hicp_manr?format=JSON&geo=EA&coicop=CP00&lastTimePeriod=2
→ 200. Euro-area HICP annual rate: 2.1, 2.0
```

Output is **JSON-stat 2.0** — a flat `value` array indexed by a `size`/`dimension` product, not a list of records. Parsing it is ~20 lines. Note the payload's own `"updated":"2026-02-06T23:00:00+0100"` field looked stale relative to the observations returned; I did not chase this down → **UNVERIFIED whether `updated` is per-dataset or per-extraction**. Do not use that field as a release timestamp without checking.

Eurostat data is reusable under Commission Decision 2011/833/EU (free reuse including commercial, with source acknowledgement); the copyright notice page returned HTTP 200 but I did not capture its text → **UNVERIFIED wording**, though the policy itself is long-standing.

### 2.6 IMF — the API moved and the old one is dead

- Legacy `http://dataservices.imf.org/REST/SDMX_JSON.svc/…` → **connection failed entirely (curl exit, HTTP 000)**. Every tutorial and several Python wrappers still point here. Treat as **DEAD**.
- New `https://api.imf.org/external/sdmx/2.1/dataflow` → **200**, returns valid SDMX-ML 2.1 structure. But `https://api.imf.org/external/sdmx/2.1/data/IMF,IFS/M.US.PMP_IX` → **404 `No such dataflow found: Dataflow=IMF:IFS(latest)`**, i.e. the dataflow IDs have changed from the familiar `IFS`/`DOT` codes. Discovering the new IDs is a half-day of work I did not do → **UNVERIFIED which dataflow now carries International Financial Statistics.**
- `https://www.imf.org/external/datamapper/api/v1/{indicator}/{country}` → **200**, clean JSON, no key. Verified: `NGDP_RPCH/AUS`. But this is **World Economic Outlook data only — annual**, and it includes IMF *forecasts* out several years.

→ IMF is **not needed for v1**. The DataMapper endpoint is interesting for exactly one reason: it is a free, structured source of **forward-dated forecast values**, which is a useful test fixture for the "future data" storage shape in Part C.

### 2.7 National sources that worked

| Bloc | Endpoint verified today | Result | Key? |
|---|---|---|---|
| GBP | `https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jul/2026&Dateto=17/Aug/2026&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N` | **302 → follow redirect → clean CSV.** Bank Rate `IUDBEDR` = 3.75 throughout Jul–Aug 2026 | No |
| CHF | `https://data.snb.ch/api/cube/zimoma/data/csv/en` | 200. Semicolon-delimited CSV. **Carries a `PublishingDate` header line: `2026-08-03 14:30`** | No |
| JPY | `https://www.stat-search.boj.or.jp/ssi/mtshtml/csv/ir01_m_1.csv` | 200, `text/csv` | No |
| AUD | `https://www.rba.gov.au/statistics/tables/csv/f1-data.csv` | 200, 304,952 bytes (Table F1 Interest Rates and Yields — Money Market) | No |
| USD | `https://api.bls.gov/publicAPI/v1/timeseries/data/` (POST JSON) | 200. CPI-U `CUUR0000SA0` July 2026 = 333.918 | **No key on v1**; v2 needs a free key |
| CAD | `https://www150.statcan.gc.ca/t1/wds/rest/getAllCubesListLite` | 200, full cube catalogue | No |
| World | `https://api.worldbank.org/v2/country/aus/indicator/FP.CPI.TOTL.ZG?format=json` | 200, annual only | No |

Two notes worth carrying forward:

- **The BoE endpoint 302-redirects.** A naive HTTP client that does not follow redirects gets an empty body and a "the BoE API is broken" bug report. Set `follow_redirects=True`.
- **SNB is the only source here that hands you a publication timestamp in the payload itself.** That is exactly the `known_at` column Part C needs. Every other source makes us infer it.

### 2.8 Sources that failed or are unusable

| Source | Attempt | Result |
|---|---|---|
| Statistics Canada WDS data endpoints | `POST getDataFromVectorsAndLatestNPeriods`, `getSeriesInfoFromVector`, `getDataFromCubePidCoordAndLatestNPeriods`, `getChangedSeriesList` | All returned **HTTP 409 `{"message":"The product is not released yet"}`**, while the catalogue endpoint worked. Either my vectors/coordinates were wrong or the data plane was degraded. → **UNVERIFIED. Do not schedule StatCan work without a spike first.** |
| RBNZ (NZD) | `GET https://www.rbnz.govt.nz/statistics/series/...` | **403** to a plain GET. NZ policy rate is available via BIS `WS_CBPOL` (`NZ` = 2.5), so this is not blocking. |
| BEA (US GDP detail) | `GET https://apps.bea.gov/api/data?&UserID=&method=GETDATASETLIST` | HTTP **200**, but I did not read the body — it almost certainly contains an error, since BEA requires a free `UserID`. → **UNVERIFIED.** |

### 2.9 What is *not* free

- **S&P Global / HCOB PMIs** are a commercial licensed product. FRED carries some PMI-adjacent series but the headline manufacturing/services PMIs are the ones with copyright notes. → treat as **not available free**; the ISM series (US only) is the closest free substitute, redistributed via DBnomics provider `ISM`.
- **Real DXY** — ICE proprietary (established in file 06).
- **Citi CESI** — institutional only (established in file 06).

### 2.10 DBnomics — one API over many providers, but it cannot do the one thing we need

**Base URL:** `https://api.db.nomics.world/v22/` — no key. Verified endpoint set from `apispec_1.json`:

```
/providers                                   /datasets/{provider}
/providers/{provider}                        /datasets/{provider}/{dataset}
/series                                      /series/{provider}/{dataset}
/series/{provider}/{dataset}/{series}        /search
/last-updates
```

**Coverage verified today: 93 providers.** Present and relevant: `BIS`, `ECB`, `IMF`, `OECD`, `Eurostat`, `BOE`, `BOJ`, `FED`, `BLS`, `BEA`, `RBA`, `STATCAN`, `WB`, `ISM`, `ONS`, `SECO`, `BUBA`, `DESTATIS`, `INSEE`, `SARB`, `TCMB`.

**Critically absent: FRED/ALFRED** (`FED` is the Federal Reserve *Board of Governors*, a different and much smaller catalogue), **CFTC**, **RBNZ**, **SNB**.

Verified working: `GET https://api.db.nomics.world/v22/series/BIS/WS_EER/D.N.B.US?observations=1` → 200 with full attribute labels.

**The disqualifier:** there is **no vintage, revision, or as-of parameter anywhere in the API surface**. DBnomics serves the current value of a series and nothing else. For a point-in-time-correct macro store, that makes it unusable as the system of record.

→ **Verdict: DBnomics is an excellent *discovery* and *prototyping* tool and a terrible *production* dependency.** Use it in the research environment to find series and check ideas; ingest from the primary source for anything that reaches a backtest. Its own licence terms page could not be located (`https://db.nomics.world/legal` → 404) → **UNVERIFIED licence**; and since it is a re-publisher, the upstream provider's terms bind us anyway.

### 2.11 Python clients — maintenance and licence, verified 2026-08-17

| Package | PyPI version / date | GitHub `pushed_at` / stars / licence | Verdict |
|---|---|---|---|
| `fredapi` | 0.5.2 · **2024-05-05** | `mortada/fredapi` 2026-01-28 · 1,651★ · Apache-2.0 | **Low-maintenance but fine.** ~600 lines wrapping a stable API. Supports `realtime_start`/`realtime_end` and `get_series_all_releases`. ADOPT or vendor. |
| `full-fred` | 0.2 · 2026-03-28 | `7astro7/full_fred` 2026-06-05 · 115★ · Apache-2.0 | Fuller endpoint coverage than `fredapi`, tiny user base. Reference implementation, not a dependency. |
| `pandas-datareader` | 0.11.1 · **2026-06-24** | `pydata/pandas-datareader` **2026-07-21** · 3,234★ · NOASSERTION | **It is alive again** — this contradicts the common belief that it died at 0.10.0 in 2021. Still: it is a lowest-common-denominator wrapper over many flaky sources, and its FRED path does not expose vintages. **AVOID** for QMF. |
| `sdmx1` | 2.27.0 · **2026-08-07** | `khaeru/sdmx` 2026-08-07 · 46★ · Apache-2.0 | **The maintained SDMX client.** Actively developed, handles BIS/ECB/OECD/Eurostat/IMF structures properly. ADOPT *if* we decide SDMX-ML parsing is needed. |
| `pandaSDMX` | 1.10.0 · **2023-02-25** | `dr-leo/pandaSDMX` **2023-12-28** · 134★ · Apache-2.0 | **Effectively abandoned.** `sdmx1` is its successor. **AVOID.** |
| `dbnomics` | 1.2.7 · 2025-06-18 | hosted on `git.nomics.world` (GitLab), not GitHub · **AGPL-3.0** | **AGPL is a serious problem** for a framework we do not intend to open-source. And we only want DBnomics in research anyway. **AVOID as a dependency**; call the REST API directly with `httpx` if needed. |
| `wbdata` | 1.1.0 · 2025-10-05 | `OliverSherouse/wbdata` 2026-07-27 · 212★ · **GPL-2.0** | Maintained, but GPL and World Bank data is annual. **AVOID.** |
| `cot-reports` | 0.1.3 · **2023-12-29** | `NDelventhal/cot_reports` **2024-04-06** · 194★ · MIT | **Stale two years.** It scrapes the CFTC ZIP archives. The Socrata API (§3) is better and needs no library. **AVOID.** |

**The pattern:** for every macro source here, the "client library" is a thin, often stale wrapper around an HTTP call that returns CSV or JSON. QMF should own ~40 lines per source (`httpx` + Polars) rather than take eight dependencies with four different licences. The one genuine exception is `sdmx1`, and only if we choose SDMX-ML over the `format=csv` shortcut — which I recommend we do **not**.

---

## 3. CFTC Commitments of Traders

### 3.1 The endpoint — verified live, no token

```
GET https://publicreporting.cftc.gov/resource/gpe5-46if.json
      ?$where=contract_market_name like '%EURO FX%'
      &$order=report_date_as_yyyy_mm_dd DESC
      &$limit=1
```

Returned, 2026-08-17, for **EURO FX – CHICAGO MERCANTILE EXCHANGE**, `report_date_as_yyyy_mm_dd = 2026-08-11`:

| Field | Value |
|---|---|
| `open_interest_all` | 801,884 |
| `dealer_positions_long_all` / `_short_all` | 53,721 / 259,757 |
| `asset_mgr_positions_long` / `_short` | 450,831 / 225,442 |
| `lev_money_positions_long` / `_short` | 86,753 / 147,353 → **net −60,600** |
| `other_rept_positions_long` / `_short` | 23,277 / 12,837 |
| `traders_tot_all` | 322 |
| `conc_net_le_4_tdr_short_all` | 40.1 (top-4 net short = 40.1% of OI) |
| `contract_units` | (CONTRACTS OF EUR 125,000) |

That dataset ID `gpe5-46if` is the **Traders in Financial Futures (TFF), futures-only** report — the one that contains currencies. It is a Socrata endpoint supporting `$where`, `$order`, `$limit`, `$offset`, `$select`. **The CFTC states explicitly that no token is required:** "Currently, we are not providing tokens to use the Public Reporting APIs. People who are using the API are generally using it successfully without using a token." (https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)

Flat-file alternatives, no API at all: `https://www.cftc.gov/dea/newcot/FinFutWk.txt` (TFF futures-only, current week, comma-delimited) and `FinComWk.txt` (futures-and-options combined).

### 3.2 Release schedule, lag, and revisions — all from the CFTC's own FAQ

Quoted from the CFTC page above:

- "The COT Report is generally published **each Friday at 3:30 pm Eastern Time (US)**, using the data from the **immediately preceding Tuesday** of that week."
- "It takes **three days to process the data**… Note that holidays can change the COT release schedule."
- **"Do you perform backdated COT updates to the (historical) data? — No, historical data is not updated once published."**
- History depth: **TFF back to 2006-06-13**; Legacy back to 1986-01-15.
- Contracts vanish from the report when fewer than 20 reportable large traders hold positions, and reappear later. An ingestion job must tolerate a missing week for a contract without treating it as an error.
- "There is not a list of historical release dates; the only available release dates are for the 13 months of reports that are published on the Commission's website."

Two consequences for QMF:

1. **COT is not revised.** So it needs no vintage dimension — only the two timestamps: `ref_period = Tuesday 15:30 ET` (position snapshot) and `known_at = Friday 15:30 ET` (publication). The gap between them is the entire point-in-time problem for this dataset, and it is a constant.
2. **Historical `known_at` must be reconstructed, not looked up**, because the CFTC does not publish a release-date history beyond 13 months. The safe reconstruction is "the Friday following the report Tuesday, 15:30 America/New_York, unless a US federal holiday intervened, in which case add one business day." This will occasionally be wrong by a day. **Record it as an estimated timestamp with a flag**, do not pretend it is exact.

**Legacy vs TFF.** Legacy splits into "commercial" and "non-commercial", which for currency futures is a crude and much-abused proxy. TFF splits into Dealer/Intermediary, Asset Manager/Institutional, **Leveraged Funds**, and Other Reportables. "Leveraged Funds" is the closest thing to "speculators" and is the series worth watching. **Use TFF, not Legacy, for FX.** Also note the CFTC's own caveat that TFF classifies a trader into the same category across all commodities, unlike the other reports.

### 3.3 Does COT positioning predict FX? The honest answer

The definitive retail-accessible study is Klitgaard & Weir, *Exchange Rate Changes and Net Positions of Speculators in the Futures Market*, Federal Reserve Bank of New York **Economic Policy Review**, vol. 10 no. 1, 2004 (https://www.newyorkfed.org/research/epr/04v10n1/0405klit/0405klit.html). Six currencies, CME data, 1993–2003. Quoted from the Fed's own executive summary:

> "knowing the direction of the change in the net position in a particular currency would give observers a **75 percent chance** of guessing the exchange rate's direction correctly, and … weekly changes in speculators' net positions can track **30 to 45 percent** of exchange rate movements of the major currencies **over the same week**. **The authors conclude, however, that position data do not predict exchange rate changes over the following week.**"

That is unambiguous and it is fatal to the naive use. The relationship is **contemporaneous**, and the data arrives **three days after the snapshot**. By publication time the move that the positioning explains has already happened.

Broader literature on COT as a signal in other markets is mixed and mostly weak; the searches I ran surfaced no peer-reviewed paper establishing out-of-sample FX profitability from COT positioning. → **"no evidence found" for a tradeable COT edge in FX.**

**What COT is still good for in QMX:**

- **Crowding / squeeze-risk context in the MIS.** "Leveraged funds are at a 3-year extreme net short JPY" is a legitimate *risk* input — it says a violent unwind is possible — even though it does not say when.
- **Per-currency knowledge-library colour.** It is a fact about a currency's ownership structure that an agent fleet can reason about.
- **Never a Trigger. Never a Confirmation with meaningful weight.** If it appears at all, it should be a low-weight regime tag or a position-size haircut.

---

## 4. Point-in-time / vintage correctness — the decision-critical section

### 4.1 How ALFRED actually works

From https://fred.stlouisfed.org/docs/api/fred/realtime_period.html, quoted:

> "The real-time period marks **when facts were true or when information was known until it changed**. Economic data sources, releases, series, and observations are all assigned a real-time period… On almost all URLs, the default real-time period is today. This can be thought of as FRED mode — what information about the past is available today. **ALFRED users can change the real-time period to retrieve information that was known as of a past period of history.**"
>
> "Variables `realtime_start` and `realtime_end` are optional YYYY-MM-DD formatted dates that default to today's date. The real-time period set by `realtime_start` and `realtime_end` is a **(closed, closed)** period."

The sentinel values are `1776-07-04` (first available) and `9999-12-31` (last available). So:

| Intent | Parameters |
|---|---|
| What we know today (default, **wrong for backtests**) | none |
| What was known on 2020-05-01 | `realtime_start=2020-05-01&realtime_end=2020-05-01` |
| Every version ever published | `realtime_start=1776-07-04&realtime_end=9999-12-31` |

A companion endpoint, `fred/series/vintagedates` (https://fred.stlouisfed.org/docs/api/fred/series_vintagedates.html), returns "the dates in history when a series' data values were **revised or new data values were released**. Vintage dates are the release dates for a series **excluding release dates when the data for the series did not change.**" Max `limit` is 10,000.

**This is the model QMF should copy wholesale.** `realtime_start`/`realtime_end` *is* a transaction-time interval; `9999-12-31` *is* the open-ended-current sentinel. We do not need to invent a design — we need to adopt this one and apply it to every non-price source.

### 4.2 What happens to a backtest that ignores this

Concretely, three separate failure modes, in increasing order of nastiness:

1. **Value revision.** US non-farm payrolls, GDP, retail sales are revised for years. A strategy trained on final-revised employment data learns a relationship that was not observable in real time. Effect: inflated in-sample edge that vanishes live.
2. **Existence lookahead.** The series exists in today's download for a date on which it had not yet been published at all. A monthly CPI for reference month March is not knowable on 15 March; it lands around 10–15 April. Naively joining on the *reference date* injects roughly one month of clairvoyance into every macro confirmation. **This is the single most common and most damaging mistake in retail macro backtests, and it is the one that `join_asof` on the wrong column produces by default.**
3. **Definition/basket revision.** GDP gets rebased, CPI baskets get reweighted, index bases move (BIS EER, DXY substitutes). The *history itself* changes shape, not just the last few points. ALFRED vintages capture this; nothing else free does.

Note that these failure modes have different sizes by series. Market-observed series (`DGS2`, `DGS10`, ECB DFR, BIS policy rates, FX rates) are **effectively never revised** — for them, mode 1 does not apply and mode 2 collapses to a one-day publication lag. Survey and national-accounts series suffer all three. **QMF should classify every macro series into `revision_class ∈ {never, minor, heavy}` at registration time** and enforce a stricter ingestion path for `heavy`.

### 4.3 Which sources publish vintages at all

| Source | Vintages available? | Evidence |
|---|---|---|
| **FRED/ALFRED** | **Yes, first class** — `realtime_start`/`realtime_end` on nearly every endpoint, plus `series/vintagedates` | Verified from docs (§4.1) |
| **CFTC COT** | **Not needed** — data is never revised | CFTC FAQ, quoted §3.2 |
| **SNB** | **Partial** — payload carries `PublishingDate` but not prior versions | Verified live (§2.7) |
| **BIS** | **No vintage API.** SDMX has an attribute vocabulary for it but `WS_CBPOL`/`WS_EER` returned only `OBS_STATUS`, `OBS_CONF`, `OBS_PRE_BREAK` | Verified from the returned CSV headers |
| **ECB** | **No vintage API** in the Data Portal REST surface. (The ECB does publish a separate Real Time Database of macroeconomic vintages as a research product — **UNVERIFIED** whether it has a machine-readable API.) | Verified: no realtime params in the calls I made |
| **OECD / Eurostat / World Bank / IMF / BoE / BoJ / RBA / StatCan / BLS(v1)** | **No** | No vintage parameters observed |
| **DBnomics** | **No** — no such parameter exists in the v22 API surface | Verified §2.10 |

→ **This is the finding that shapes the architecture.** Only one free source gives us true vintages, and only for US data. For everything else, **QMF must manufacture its own vintage history by archiving every poll from day one.** There is no way to buy back the past for ECB, BIS, RBA or the calendar. Every day we do not archive is a day of point-in-time history permanently lost.

That single sentence is the strongest argument in this file for building the ingestion archive **before** building anything that consumes it.

### 4.4 What the store must record per macro observation

Minimum viable, per row:

| Field | Why it is mandatory |
|---|---|
| `ref_period_start`, `ref_period_end` | **Valid time** — the period the number describes (2026-Q2, 2026-07, or an instant for an event) |
| `value` | Nullable — NULL is meaningful (scheduled, not yet released) |
| `known_at` | **Transaction time start** — the instant QMF could first have used this row. **The only column a backtest may filter or join on.** |
| `known_until` | Transaction time end; `9999-12-31T00:00:00Z` while current (ALFRED's sentinel) |
| `vintage_id` | The source's own vintage label if it has one (ALFRED `realtime_start`), else `ingest:<utc-timestamp>` |
| `revision_no` | 0 = first print. Lets a strategy explicitly ask for "the number as first printed" |
| `observed_at` | When *our poller* saw it — differs from `known_at` when the source publishes at a scheduled time we polled late |
| `known_at_is_estimated` | Boolean. True for reconstructed COT Fridays and for any source that does not stamp its own publication time |

`known_at` vs `observed_at` matters more than it looks. If NFP is released at 08:30 ET and our poller runs at 09:00, the *market* knew at 08:30 — using `observed_at` would make the backtest slightly pessimistic, and using `known_at` correctly. Conversely if the source's stated time is unreliable, `observed_at` is the defensible bound. **Store both; let the strategy choose; default to `known_at`.**

### 4.5 How this maps onto the file-02 stack

It maps cleanly, with no new technology:

- **Parquet, Hive-partitioned** exactly as file 02 ratified, but partitioned by `source=` / `series_id=` rather than by symbol/date. Macro data is *tiny* — the entire macro store for 8 currencies × ~25 series × 40 years × all revisions is on the order of 10⁶ rows, single-digit MB compressed with zstd. Partitioning is for readability, not performance.
- **Append-only.** A revision never rewrites a row; it writes a new row and closes the previous one's `known_until`. This is textbook SCD Type 2, and DuckDB ships a documented recipe for exactly it (https://duckdb.org/docs/current/guides/sql_features/merge — "Merge Statement for SCD Type 2").
- **SQLite WAL inbox** (file 02's pattern) is the right landing zone for pollers, since a poll is a small, frequent, transactional write.
- **`split_id` rule from file 02 still applies unchanged** — IS/OOS selection by `split_id`, never by raw dates. Nothing here weakens that.

---

## 5. A calendar with `actual` values — the survey

### 5.1 Confirming and extending file 06

I re-tested the FairEconomy feed and its neighbours:

| URL | Result 2026-08-17 |
|---|---|
| `https://nfs.faireconomy.media/ff_calendar_thisweek.json` | **200, 12,960 bytes.** Fields present: `title`, `country`, `date`, `impact`, `forecast`, `previous`. **No `actual` field** — confirms file 06 |
| `…/ff_calendar_nextweek.json` | **404** |
| `…/ff_calendar_lastweek.json` | **404** |
| `…/ff_calendar_thismonth.json` | **404** |

So the feed is genuinely this-week-only. **A small correction to how file 06 framed it:** the feed's `date` values are forward-dated (the first record I got was `2026-08-16T18:30:00-04:00`, i.e. later in the week), so the feed does give us **forward-looking scheduled events** — it is a "future data" source in the operator's sense, just a short-horizon one. File 06's "this-week-only" is right about depth but understates its role: it is the primary v1 supply of forward-dated event rows.

### 5.2 Paid options — actual prices, tested

| Provider | What I tested | Result |
|---|---|---|
| **Trading Economics** | `https://api.tradingeconomics.com/calendar?c=guest:guest&f=json` | **HTTP 410**: *"We are sorry, but the guest account has been discontinued. Please subscribe to a plan at https://tradingeconomics.com/api/pricing.aspx"*. **The single most-recommended free FX calendar credential on the internet is dead.** |
| Trading Economics pricing | pricing page | **Standard $149/month billed yearly**, includes "Global real-time economic calendar with **Actual, Previous and Consensus** for many countries". Redistribution is an enterprise-tier feature. Trial: "limited to 100000 data points and 100 requests for data", non-refundable, auto-converts to paid if not cancelled |
| **Financial Modeling Prep** | `https://financialmodelingprep.com/stable/economic-calendar?apikey=demo` | **401** — `demo` key rejected. Free tier exists but requires registration; calendar is not in the free endpoint set → **UNVERIFIED which tier includes it** |
| **Finnhub** | `https://finnhub.io/api/v1/calendar/economic` | **401** "Please use an API key." Finnhub's docs place the economic calendar on a **premium** tier → **UNVERIFIED price** |
| **EODHD** | `https://eodhd.com/api/economic-events?api_token=demo` | **403 Forbidden** |
| **Marketaux** | `https://api.marketaux.com/v1/news/all` | **401**. Marketaux is a *news* API anyway, not an economic calendar — it does not solve this problem |

**Assessment:** there is currently **no free source of historical economic releases with both `actual` and `consensus`** that I could verify. The cheapest verified path to surprise-based strategies is **Trading Economics Standard at $149/month billed yearly (~$1,788/yr)**.

→ **OPERATOR RISK DECISION #2:** $1,788/year buys the "surprise" family of strategies (actual − consensus) and nothing else. Given that (a) the highest-value calendar use case is a *blackout gate*, which the free feed already serves, and (b) surprise strategies are the hardest to execute at retail spreads anyway, my opinion is **do not buy this for v1**. Revisit only if a funded account is running and a surprise strategy has been validated on paper.

### 5.3 The free fallback and its honest timeline

Poll `ff_calendar_thisweek.json` **daily**, and archive every poll verbatim with an `observed_at` stamp. What that buys, over time:

- **Immediately (day 1):** a forward-looking blackout calendar with impact ratings. Enough for "do not trade 30 minutes around Red news" and "this pair has three high-impact events this week, do not attempt a prop-firm challenge on it." **This is already most of the value.**
- **Immediately, and unlocked by daily polling:** because the feed carries `forecast` and `previous` and we archive successive polls, we capture **how the consensus forecast moved during the week** — which the single weekly snapshot does not give you. That is a genuinely useful series nobody else archives.
- **Never, from this feed alone:** the `actual`. It is simply not in the payload.
- **~6 months:** enough polls to characterise the schedule reliably (which events recur, at what times, with what impact ratings) and to build a session-aware blackout model.
- **~2 years:** enough to test "does event density predict spread widening" per pair — a directly prop-firm-relevant question.

**A partial free `actual` for the US, worth doing:** the US statistical agencies publish their own numbers with precise release schedules. `BLS API v1` needs no key at all (verified: CPI-U July 2026 = 333.918), and FRED's `fred/releases/dates` endpoint with `include_release_dates_with_no_data=true` returns **future scheduled release dates** — quoted from https://fred.stlouisfed.org/docs/api/fred/releases_dates.html: the default `false` "excludes release dates that do not have data. **In particular, this excludes future release dates** which may be available in the FRED release calendar or the ALFRED release calendar." Setting it to `true` therefore gives an authoritative forward-dated US release calendar, free, from the Fed. Combining FRED release dates (the *when*) with BLS/FRED observations (the *what*) reconstructs `actual` for US events at zero cost. It does **not** give consensus.

→ **v1 rule: free feed for the gate; FRED releases + BLS for US actuals; no consensus, no surprise strategies, no subscription.**

---

# Part B — Micro / microstructure analysis

## 6. What "micro" can mean on a retail cTrader account

### 6.1 The data ceiling, stated plainly

FX has **no consolidated tape**. There is no NBBO, no exchange print, no aggregate volume. What a cTrader account sees is: **our broker's bid and ask, tick by tick**, and in the bar API a **tick count** labelled "volume" (file 05). Depth of market exists only if the broker publishes it and is that broker's book alone.

Everything that follows respects that ceiling. Anything requiring true traded volume, aggressor side, or a consolidated book is **not computable** and I say so rather than proposing a proxy that is really a guess.

### 6.2 The computable metric set, in priority order

| # | Metric | Computable from cTrader? | Library? | Verdict |
|---|---|---|---|---|
| **M1** | **Quoted spread** `ask − bid`, per tick, and its distribution | **Yes, exactly** — this is directly observed | None needed | **BUILD — v1, highest value** |
| **M2** | **Spread profile**: median/p90 spread by hour-of-day × day-of-week × pair, in points and as a fraction of ATR | Yes | None | **BUILD — v1. This is the "is this pair clean enough to trade" answer.** |
| **M3** | **Tick arrival rate** (ticks per minute) as an activity/liquidity proxy | Yes | None | **BUILD — v1** |
| **M4** | **Spread cost as a share of edge**: for a given strategy's average winner in points, what fraction is eaten by the spread at the hour it trades | Yes (M1 + strategy stats) | None | **BUILD — v1. Directly kills unviable strategies before they are coded.** |
| M5 | **Realised volatility** from high-frequency data: Parkinson, Garman-Klass, Rogers-Satchell, Yang-Zhang | Yes from OHLC bars | See §6.4 | BUILD (≈120 lines) |
| M6 | **Realised variance / bipower variation** from ticks | Yes, **with a large caveat** (§6.5) | None maintained | Research only |
| M7 | **Alternative bars**: tick bars, volume(=tick-count) bars, dollar bars | Yes | **NautilusTrader** (§6.6) | Research; adopt the design, not the dependency |
| M8 | **Tick imbalance / run bars** | **Degraded** — requires aggressor side, which we do not have. A tick-rule classifier (uptick=buy) is a *guess* | NautilusTrader has the machinery | **Research only, clearly labelled as approximated** |
| M9 | **Session profile**: Tokyo / London / New York and the London–NY overlap, per pair | Yes | None (`smartmoneyconcepts.sessions` exists but is slow and from a library file 06 already condemned) | **BUILD — v1** |
| M10 | **Rollover / swap-time behaviour**: the 17:00 New York gap in spread and quote continuity | Yes | None | **BUILD — v1** (prop-firm relevant: many challenges are blown by overnight gaps) |
| M11 | **Weekend gap distribution** per pair | Yes | None | BUILD |
| M12 | **Order-book imbalance / depth** | **NO** — not available unless the broker publishes DOM | — | **Do not attempt** |
| M13 | **Effective spread vs quoted spread** (true execution cost) | **Only after we have fills** — see §7 | — | Phase 2 |

**My opinionated cut: M1, M2, M3, M4, M9, M10 are v1.** They are all simple, all directly serve the prop-firm goal, and none of them needs a library. Everything else is research.

### 6.3 Why M2 is the most valuable thing in Part B

The operator's two named outputs are "do not trade into this event" and "this pair is currently clean enough to trade". The second one is *exactly* a spread-profile query:

> For EURJPY on our broker, at 03:00 UTC, the median spread over the last 60 trading days is 2.8 points and the 90th percentile is 9.1 points; at 13:00 UTC it is 1.1 and 1.6. The strategy's average winner is 14 points.

That single table decides which pairs and which hours a prop-firm challenge should be attempted in, and it comes from data we are already storing. No macro source in Part A produces an answer this actionable this cheaply.

It also gives the MIS a clean publishable signal: a per-pair, per-hour **`tradeability` score** in [0,1] that Books and bots consume as a gate. That is a small, discoverable, machine-readable surface — exactly what an LLM strategy-author needs.

### 6.4 Realised volatility estimators — no clean library

| Candidate | State 2026-08-17 | Verdict |
|---|---|---|
| `volatility-trading` (`jasonstrimpel/volatility-trading`) | 1,944★, PyPI 0.7.0 (2026-03-16), **GitHub `pushed_at` 2024-10-21** — stale ~22 months. **Licence conflict: PyPI metadata says "MIT License", the GitHub repo declares GPL-3.0.** | **AVOID.** The licence ambiguity alone disqualifies it for a proprietary framework; GPL-3.0 would be contagious. |
| `quantreo` | 0.1.1, 2026-04-06, licence field empty on PyPI | Too young, no declared licence. **AVOID.** |
| `RiskLabAI` (`RiskLabAI/RiskLabAI.py`) | PyPI 2.0.1 (2026-06-20), GitHub pushed 2026-07-12, **2★**, GitHub licence `NOASSERTION` while PyPI claims BSD-3 | Implements the López de Prado material including bar types. **AVOID as a dependency** (2 stars, licence mismatch); **useful as a reading reference.** |
| `arch` 8.0.0 | Maintained, NCSA licence | Does **not** provide range-based RV estimators. It provides GARCH, unit roots, bootstraps — a different job (§8). |

The formulas (Parkinson 1980; Garman–Klass 1980; Rogers–Satchell 1991; Yang–Zhang 2000) are each three to eight lines of vectorised arithmetic over OHLC. **QMF implements them itself.** That is roughly 120 lines including tests, and it removes a licence risk. This is the same conclusion file 06 reached about levels and structure, for the same reason.

### 6.5 The realised-variance noise caveat (why M6 is research-only)

Summing squared tick returns over a day does **not** converge to the day's integrated variance as sampling frequency rises — it diverges, because each tick carries microstructure noise (bid-ask bounce, quote flicker) that is squared and accumulated. In FX with a bid/ask feed and no trades, the bounce is the dominant term at high frequency. The standard mitigations are sparse sampling (5-minute returns), two-scale estimators, and bipower variation for jump-robustness.

I did **not** verify a maintained Python library for two-scale realised volatility or bipower variation → **no evidence found** of one. QMF should not put realised-variance-from-ticks anywhere near a live confirmation until this is done properly with a named estimator and a documented sampling frequency. **Use M5 (range-based, on 1-minute or 5-minute bars) instead — it is far more robust to this problem and costs nothing.**

### 6.6 Alternative bars — NautilusTrader is the reference implementation

`nautilus_trader` 1.231.0 (PyPI 2026-08-02), **LGPL-3.0-or-later**, is the only maintained Python framework I found that implements the full alternative-bar family properly. Its `BarAggregation` enum covers:

- Threshold: `TICK`, `VOLUME`, `VALUE` (dollar bars)
- Information-driven: `TICK_IMBALANCE`, `TICK_RUNS`, `VOLUME_IMBALANCE`, `VOLUME_RUNS`, `VALUE_IMBALANCE`, `VALUE_RUNS`
- Time: `MILLISECOND` … `YEAR`
- Price-driven: `RENKO`

A `BarSpecification` is `{step}-{aggregation}-{price_type}` with `price_type ∈ {bid, ask, mid, last}` — a clean, small, machine-readable surface worth copying for QMF's own bar vocabulary.

Two details worth stealing outright:

1. **`QuoteTick` (best bid/ask + sizes) and `TradeTick` (with `aggressor_side`) are separate types.** cTrader gives us the first and not the second. Making that a *type-level* distinction rather than a nullable column means an LLM-authored strategy that asks for aggressor side gets a clear error instead of silent nonsense.
2. **Every record carries both `ts_event` (venue timestamp) and `ts_init` (when our system first had it).** That is precisely the `ref_period` / `known_at` pair from Part A, applied to ticks. **The same two-timestamp discipline should run through the entire QMF store, price and non-price alike.** This is the single strongest architectural convergence in this file.

**Licence position:** LGPL-3.0 permits use as a *linked library* without infecting our code, but copying its source into QMF would infect. → **Read it, copy the design vocabulary, do not paste the code.** Whether to take it as a runtime dependency at all is a separate question already open from file 01/02.

### 6.7 Session and liquidity context

The BIS Triennial Central Bank Survey is the authoritative measurement of FX activity concentration; the April 2025 round reported **global FX turnover of roughly USD 9.5 trillion per day** (https://www.bis.org/statistics/rpfx25_fx.htm — I retrieved this figure via search summarising the BIS release; the exact BIS-adjusted headline was not read from the PDF directly → **UNVERIFIED to one decimal place**, though the order of magnitude and the ~28% rise vs 2022 are consistently reported).

For our purposes the survey is background, not an input. **The session profile QMF actually needs is measured from our own broker's ticks**, because what matters is *this broker's* spread at *this hour*, not the global market's turnover. M2/M3/M9 measure exactly that. Do not ingest the Triennial.

---

## 7. Execution-quality micro-analysis — the trader hat's analytics

### 7.1 What a retail operator without FIX drop-copy can actually measure

We do not get a drop copy, and we do not get the venue's view of our order. What we do get from cTrader is: our own order events (submitted / filled) with timestamps and prices, and our own recorded tick stream. That is enough for four real measurements:

| Measurement | Definition | Needs |
|---|---|---|
| **Slippage vs decision price** | `fill_price − price_at_signal_time`, signed by direction | Our tick archive + our order log |
| **Slippage vs arrival price** | `fill_price − mid_at_order_submit` | Same |
| **Spread paid** | `fill_price − mid_at_fill` — the half-spread we actually crossed | Same |
| **Latency** | `fill_ts − submit_ts` | Our order log |

Doing this **requires that QMF archive its own tick stream continuously on the VPS**, not just the broker's history. Reconstructing the mid at fill time from a later download is unreliable. → **Design consequence: the live tick recorder is an execution-analytics prerequisite, not just a data-collection nicety.**

The high-value derived statistic is **slippage distribution conditioned on session and event proximity**: "our average slippage is 0.3 points, except in the 60 seconds after a Red event where it is 4.1 points." That number both validates the blackout gate from Part A and quantifies what the gate is worth.

### 7.2 Prior art

| Framework | Licence (verified) | What it offers here |
|---|---|---|
| **QuantConnect LEAN** (`QuantConnect/Lean`, 21,240★, pushed 2026-08-14) | **Apache-2.0** | The best-organised slippage model taxonomy: `Common/Orders/Slippage/` contains `ConstantSlippageModel`, `VolumeShareSlippageModel` (both C# and Python), `MarketImpactSlippageModel`, `AlphaStreamsSlippageModel`, `NullSlippageModel`, behind an `ISlippageModel` interface. `Common/Orders/Fees/` holds ~30 per-broker fee models. **Apache-2.0 means we may read and adapt freely.** → **ADOPT the interface shape** (`ISlippageModel` as a pluggable, per-instrument, per-model-class abstraction), implement our own bodies against cTrader reality. |
| **NautilusTrader** | LGPL-3.0-or-later | Execution reports and the `ts_event`/`ts_init` discipline (§6.6). Its fill model is simulation-side. |
| **Hummingbot** (`hummingbot`, PyPI `20260729`, 2026-07-29) | **Apache-2.0** | Crypto market-making; its per-exchange fee/slippage handling is instructive but the market structure is wrong for FX. **Low relevance to the forex-first priority.** Revisit for the crypto phase. |

Note that LEAN's models are for *simulating* slippage in a backtest, whereas what §7.1 describes is *measuring* realised slippage live. QMF needs both, and they should share one vocabulary so that the measured distribution can be fed back as the simulation model's parameters. That closed loop — measure live, calibrate the backtest — is the thing none of the surveyed frameworks does for a retail FX operator, and it is a genuine QMF differentiator.

---

## 8. Analyst-hat libraries beyond pandas and NumPy

All rows verified 2026-08-17 via PyPI JSON + GitHub API. File 03 already covered TA-Lib, talipp, pandas-ta-classic, quantstats, statsmodels, sklearn/skfolio — not repeated.

| Library | Version · PyPI date | GitHub pushed · stars · licence | Weight | Verdict |
|---|---|---|---|---|
| **`arch`** | 8.0.0 · 2025-10-21 | 2026-08-10 · 1,551★ · NCSA | 1.0 MB | **ADOPT — core.** GARCH family (the right tool for FX volatility regimes), unit-root tests, cointegration (`arch.unitroot.cointegration`), and the **bootstrap module — the honest way to put confidence intervals on a backtest statistic.** Kevin Sheppard maintains it personally and reliably. |
| **`ruptures`** | 1.1.10 · 2025-09-10 | 2026-07-06 · 2,071★ · **BSD-2-Clause** | 1.3 MB | **ADOPT — core.** Offline change-point detection (PELT, BinSeg, Window). This is the quantitative form of "the regime changed" — directly feeds the MIS's market-view state. Small, permissive, stable API. |
| **`pandera`** | 0.32.1 · 2026-06-29 | 2026-08-07 · 4,433★ · **MIT** | 0.4 MB, 55 deps | **ADOPT — core.** Declarative dataframe schema validation with **native Polars support**. Every ingestion adapter in Part A should terminate in a `pandera` schema check. Cheap insurance against a source silently changing shape. |
| **`scipy.stats`** | (with SciPy) | — · BSD | already present | **ADOPT.** Already a transitive dependency. Covers 90% of what an analyst actually runs. |
| **One charting library** | see below | | | **ADOPT one, ban the rest.** |
| `plotly` | 6.9.0 · 2026-07-09 | MIT | **9.9 MB wheel, 71 deps** | The pragmatic choice: interactive, self-contained HTML output, no server. **ADOPT for the Windows QMX app / research only.** |
| `altair` | 6.2.2 · 2026-06-23 | BSD-3 | 0.8 MB, 47 deps | Cleanest grammar-of-graphics API, but Vega-Lite struggles past ~50k points. Good for macro (small data), bad for ticks. |
| `hvplot` | 0.12.2 · 2025-12-18 | BSD | 0.2 MB but **175 declared deps** | Best large-data story (Datashader). The dependency count is alarming for a solo operator to maintain. **AVOID unless tick-scale plotting becomes a real need.** |
| `bokeh` | 3.9.2 · 2026-07-25 | BSD-3 | | Fine; `hvplot` and `plotly` cover its ground. Skip. |
| **`great-expectations`** | 1.20.0 · 2026-08-07 | 2026-08-17 · 11,713★ · Apache-2.0 | **5.0 MB, 136 deps** | **AVOID.** Enterprise data-quality platform with its own store, config, and docs pipeline. Wildly disproportionate for a solo operator. `pandera` does the needed 5% at 1/10th the weight. |
| **`statsforecast`** | 2.1.1 · 2026-07-16 | **2026-08-17** · 4,868★ · Apache-2.0 | 0.6 MB, **10 deps** | **ADOPT — optional, research.** Numba-compiled classical forecasting (AutoARIMA, ETS, Theta). Genuinely light. If any forecasting is done, do it with this. |
| `sktime` | 1.1.0 · 2026-07-28 | 2026-08-16 · 9,926★ · BSD-3 | **37.6 MB wheel, 117 deps, 2,403 open issues** | **AVOID.** Enormous surface, enormous issue backlog. Research-laptop only if at all. |
| `darts` | 0.46.1 · 2026-07-20 | 2026-08-06 · 9,497★ · Apache-2.0 | 0.8 MB core; `torch`/`lightning` only under the `[torch]` extra | **Research environment only.** Good API. Never on the VPS. |
| `neuralforecast` / `mlforecast` / `skforecast` / `prophet` / `chronos-forecasting` | all maintained 2026 | Apache/BSD/MIT | heavy | **AVOID for v1.** FX return forecasting by deep learning is where retail projects go to die. |
| `pymc` 6.3.1 (2026-08-16) / `arviz` 1.3.0 (2026-08-11) | both very actively maintained | Apache-2.0 | | **AVOID for v1.** Bayesian work is justified only for small-sample problems where priors carry real information — e.g. estimating a strategy's true win rate from 40 trades. That is a genuine future use case, but it is a *research* activity, needs an expert, and never belongs on the VPS. Defer. |
| `pingouin` 0.6.1 (2026-03-28) | 2026-04-05 · 1,929★ · **GPL-3.0** | 0.2 MB | **AVOID — GPL-3.0.** It is a convenience wrapper over `scipy.stats`; the convenience is not worth a copyleft licence in a proprietary framework. Use `scipy.stats` directly. |
| `tsfresh` 0.21.2 (2026-05-31) | MIT | | Automated feature extraction (~800 features). **AVOID** — a feature factory of that size against ~10³ FX trades is a p-hacking machine. |

### 8.1 The five an analyst actually needs

1. **`statsmodels`** (already in file 03) — regression, time-series tests, the workhorse.
2. **`arch`** — volatility models, unit roots, and above all **bootstrap confidence intervals on performance statistics**.
3. **`ruptures`** — regime/change-point detection, feeding the MIS.
4. **`scipy.stats`** — the everyday statistics; already installed.
5. **`pandera`** — schema validation on every ingestion boundary.

Plus **one** interactive charting library (`plotly`) for the Windows app and research, and **`statsforecast`** as an optional sixth if forecasting is ever actually required.

### 8.2 VPS vs research environment — an explicit split

**Never on the Linux Trading VPS:** `sktime`, `darts`, `pymc`/`arviz`, `neuralforecast`, `great-expectations`, `plotly`, `hvplot`, `tsfresh`, `prophet`, anything pulling `torch`.

**Permitted on the VPS:** `polars`, `duckdb`, `pyarrow`, `numpy`, `scipy`, `statsmodels`, `arch`, `ruptures`, `pandera`, `httpx`, plus the broker SDK.

The rule to write into the constitution: **if a package's install footprint exceeds ~50 MB or its dependency list exceeds ~30 entries, it is research-only by default and requires an explicit exception to reach the VPS.** A trading VPS that cannot be rebuilt from scratch in five minutes is an operational risk, and every extra dependency is a supply-chain surface.

---

# Part C — Storage

## 9. "Handles anything we throw at it — historical and future data"

### 9.1 The insight: it is one schema, not several

The five things the operator listed sound like five problems:

- irregular macro series with vintages
- scheduled future events with no value yet
- forecasts and consensus numbers
- model predictions with a prediction time and a target time
- revisions of any of the above

They are one problem. Every one of them is a **fact with two independent time axes**:

- **Valid time** — the period or instant the fact is *about* (`ref_period_start`, `ref_period_end`)
- **Transaction time** — the interval during which our system *believed* it (`known_at`, `known_until`)

Once both axes are explicit, each case falls out:

| Case | Shape |
|---|---|
| Historical macro observation | `ref_period` in the past, `known_at` shortly after it, one row |
| **Revision** | Same `ref_period`, **new row** with later `known_at`; the old row's `known_until` is closed to the new `known_at`. `revision_no` increments |
| **Scheduled future event, no value** | `ref_period` **in the future**, `value = NULL`, `value_kind = 'scheduled'`, `known_at` = when the schedule was published |
| **Forecast / consensus** | `ref_period` in the future, `value` populated, `value_kind = 'forecast_consensus'`. A moving consensus is just successive rows with the same `ref_period` and increasing `known_at` — **structurally identical to a revision** |
| **Model prediction** | `ref_period` = target time, `known_at` = prediction time, `value_kind = 'model_prediction'`, plus a `model_id` |
| **Scenario path** | Same as a forecast with a `scenario_id` discriminator |

**`ref_period_start > known_at` is the complete definition of "future data".** No separate table, no separate engine, no separate query language. That is the whole answer to the operator's requirement.

### 9.2 The concrete schema

One Parquet dataset, `facts/`, Hive-partitioned `source=<X>/series_id=<Y>/`:

| Column | Type | Notes |
|---|---|---|
| `series_id` | `str` | Canonical QMF id, e.g. `POLICY_RATE.USD`, `CAL.US.NFP`, `COT.TFF.EURFX.LEV_NET` |
| `source` | `str` | `BIS` \| `ECB` \| `FRED` \| `CFTC` \| `FF` \| `QMF_MODEL` |
| `ref_period_start` | `timestamp[us, UTC]` | **Valid time start.** For an event, the scheduled instant |
| `ref_period_end` | `timestamp[us, UTC]` | Equal to start for instants |
| `value` | `float64` | **Nullable.** NULL means "known to be scheduled, value not yet released" |
| `value_kind` | `str` (enum) | `actual` \| `forecast_consensus` \| `forecast_official` \| `previous` \| `model_prediction` \| `scenario` \| `scheduled` |
| `known_at` | `timestamp[us, UTC]` | **Transaction time start. The only column a backtest may join or filter on.** |
| `known_until` | `timestamp[us, UTC]` | `9999-12-31T00:00:00Z` while current (ALFRED's sentinel, §4.1) |
| `revision_no` | `int32` | 0 = first print |
| `vintage_id` | `str` | Source vintage label, or `ingest:<utc>` |
| `observed_at` | `timestamp[us, UTC]` | When our poller saw it |
| `known_at_is_estimated` | `bool` | True for reconstructed timestamps (COT Fridays, undated sources) |
| `revision_class` | `str` | `never` \| `minor` \| `heavy` (§4.2) |
| `unit`, `scale`, `freq`, `country`, `currency` | `str` | Metadata |
| `attrs` | `struct`/JSON | Source-specific extras: calendar `impact`, COT `open_interest`, model `model_id`, `scenario_id` |
| `ingest_run_id` | `str` | Provenance for reproducibility |

**Invariants an LLM-authored strategy cannot violate:**

1. Rows are **append-only**. A revision never mutates.
2. `known_at <= known_until`.
3. For any `(series_id, ref_period_start, value_kind)`, the `[known_at, known_until)` intervals **tile without overlap**.
4. **The strategy API never exposes `ref_period` as a filter.** The only accessor is `as_of(t)`, which internally applies `known_at <= t < known_until`. This is the point-in-time equivalent of file 02's "select by `split_id`, never by raw dates" rule, and it should be enforced the same way — by making the wrong thing unreachable rather than merely documented.

### 9.3 Prior art for bitemporal / as-of storage in Python

| System | What it does | Licence | Fit |
|---|---|---|---|
| **ALFRED** (`realtime_start`/`realtime_end`, `9999-12-31` sentinel) | The canonical transaction-time interval model, applied to macroeconomics | Public API | **Copy the semantics exactly.** Best specification available. |
| **DuckDB `ASOF JOIN`** | `FROM bars b ASOF JOIN facts f ON b.symbol = f.symbol AND b.ts >= f.known_at` — "give me the value of the property **as of this time**" (https://duckdb.org/docs/current/guides/sql_features/asof_join) | MIT | **Already in the stack. This is the query engine for §9.2.** Supports `ASOF LEFT JOIN` so rows without a prior fact become NULL instead of vanishing — essential, since dropping bars silently biases a backtest |
| **DuckDB `MERGE INTO` / SCD Type 2 recipe** | Documented pattern for closing an old row and inserting a new version (https://duckdb.org/docs/current/guides/sql_features/merge) | MIT | **Adopt for the revision-write path** |
| **Polars `join_asof`** | `strategy ∈ {backward, forward, nearest}`, `by=` for grouping, `tolerance=` with a time-string DSL (`"3d12h4m25s"`), **`allow_exact_matches: bool`**, `check_sortedness=True` (errors if unsorted) | MIT | **Already in the stack.** `allow_exact_matches=False` gives strict `<` — the exact flag needed so a value released at 08:30:00.000 is not used by an 08:30:00.000 bar. **Use `strategy="backward"`, never `"forward"` or `"nearest"`, in any code path that feeds a backtest.** `"forward"`/`"nearest"` are lookahead generators and should be lint-banned outside research notebooks |
| **NautilusTrader `ts_event` / `ts_init`** | Two timestamps on every record | LGPL-3.0 | **Adopt the discipline** (§6.6) |
| **ArcticDB `as_of`** | `Library.read(symbol, as_of=…)` accepts an int version (−1 = latest), a snapshot name, or a datetime | **BSL 1.1** — see below | **Reject, but not for the reason file 02 gave** |
| Delta Lake / Apache Iceberg time travel | Snapshot-level "read the table as of version N" | Apache-2.0 | **Wrong granularity.** It versions the *table*, not the *fact*. It answers "what did the file look like" not "what did we know about US CPI for March". Adds a metadata layer we do not need. **AVOID.** |
| `bitemporal` on PyPI | version 1.0, no release date, Ervacon copyright notice | proprietary-ish | Dead/irrelevant. **AVOID.** |
| XTDB (`xtdb` PyPI 0.6.2, 2023-11-22) | A genuine bitemporal database (Clojure/JVM) | | Real bitemporal semantics, but a JVM database on the trading VPS is a large operational cost for a table of ~10⁶ rows. **AVOID.** |

**Correction to file 02 on ArcticDB.** File 02 recorded ArcticDB as blocked by a "commercial licence". Reading the actual `LICENSE.txt` (https://raw.githubusercontent.com/man-group/ArcticDB/master/LICENSE.txt), the restriction is **narrower than that**. It is Business Source License 1.1 with this Additional Use Grant:

> "You may make use of the Licensed Work under the terms of this License, provided that you may not use the Licensed Work for a **Database Service**. A 'Database Service' is a commercial offering that allows third parties (other than your employees and contractors) to access the functionality of the Licensed Work by creating tables whose schemas are controlled by such third parties."

Change Date: two years from each version's release; Change Licence: **Apache 2.0**. A solo operator running ArcticDB inside his own trading system is **not** offering a Database Service, so production use appears permitted. → **OPERATOR RISK DECISION #3: file 02's blanket "commercial-licence block" on ArcticDB is stronger than the licence text supports.** I still recommend **not** adopting it — but for a technical reason, not a legal one: **ArcticDB's `as_of` is transaction-time only.** It versions *writes to a symbol*; it has no valid-time axis at all. It cannot answer "what was our March-2020 CPI estimate as believed on 15 April 2020" without us re-encoding valid time inside the payload anyway — at which point Parquet + `ASOF JOIN` does the same job with no licence question and no extra binary on the VPS.

### 9.4 What "what did we know at time T" costs

Two query shapes:

**(a) Snapshot — the whole macro state at an instant:**
```sql
SELECT * FROM facts
WHERE known_at <= $T AND known_until > $T;
```
On a Hive-partitioned Parquet dataset with `known_at` sorted within each file, DuckDB prunes by row-group min/max statistics. Over a 10⁶-row store this is **single-digit milliseconds** and is dominated by file-open overhead, not scanning.

**(b) Aligned join — attach the then-known macro value to every bar in a backtest:**
```sql
SELECT b.*, f.value AS policy_rate_diff
FROM bars b
ASOF LEFT JOIN facts f
  ON f.series_id = 'RATE_DIFF.AUDJPY'
 AND b.ts >= f.known_at;
```
This is one sorted merge. For 5 years of M1 bars (~1.8M rows) against a few thousand macro rows, expect **well under a second** in DuckDB, and the same in Polars via `join_asof(..., strategy="backward", allow_exact_matches=False)`.

**The cost is negligible. There is no performance argument for cutting the corner.** The only real cost is discipline: the `facts` table must be written correctly once, and the accessor must be the only door.

**One caveat to record:** `ASOF LEFT JOIN` on `known_at` alone gives you "the most recently *published* fact", which for a `heavy`-revision series may be a revision of an *older* reference period rather than the latest reference period. A strategy usually wants "the latest reference period, as believed at T" — which is a two-step: filter by `known_at`, then take `argmax(ref_period_start)` per series. **QMF's accessor must implement the two-step and not expose the naive one-step**, because the one-step is subtly wrong in exactly the cases that matter.

---

## 10. Summary table

| Source / Library | Endpoint or version | Verified today | Licence / terms | Verdict |
|---|---|---|---|---|
| **BIS `WS_CBPOL`** | `stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D.US+GB+JP+XM+AU+NZ+CA+CH` | ✅ all 8 rates, one call, no key | Cite BIS; commercial OK; BIS may throttle IPs | **ADOPT — v1 core** |
| **BIS `WS_EER`** | `.../WS_EER/1.0/D.N.B.US` | ✅ US broad NEER 102.04 | same | **ADOPT — v1** |
| BIS `BIS_REL_CAL` | listed dataflow | ❌ HTTP 404 "No results" | — | **AVOID (no data)** |
| **ECB Data Portal** | `data-api.ecb.europa.eu/service/data/{FLOW}/{KEY}?format=csvdata` | ✅ EXR + FM/DFR | Cite ECB; **must label transformations** | **ADOPT — v1** |
| **FRED API (keyed)** | `api.stlouisfed.org/fred/series/observations` + `realtime_start/end` | ✅ key required (400 without) | Free key; **mandatory disclaimer notice**; third-party copyright pass-through | **ADOPT — v1, key required** |
| **ALFRED vintages** | `fred/series/vintagedates`, `realtime_*` params | ✅ semantics confirmed from docs | as above | **ADOPT — the vintage model** |
| ⚠️ `fredgraph.csv?…&vintage_date=` | key-free CSV | ✅ **200 but silently returns current data** | — | **BANNED for revisable series** |
| `alfred.stlouisfed.org/graph/fredgraph.csv` | key-free vintage CSV | ❌ HTTP 404 | — | **AVOID** |
| **CFTC TFF (Socrata)** | `publicreporting.cftc.gov/resource/gpe5-46if.json` | ✅ EURO FX 2026-08-11 | No token needed (CFTC states so); public domain | **ADOPT — MIS context only** |
| CFTC flat file | `cftc.gov/dea/newcot/FinFutWk.txt` | not called | public domain | Fallback |
| **FairEconomy calendar** | `nfs.faireconomy.media/ff_calendar_thisweek.json` | ✅ 200, no `actual`; next/last/month = 404 | ForexFactory ToU — **already an open operator risk from file 06** | **ADOPT for the gate + archive from day 1** |
| **FRED `releases/dates`** | `include_release_dates_with_no_data=true` → future dates | doc-verified | FRED ToU | **ADOPT — free forward-dated US calendar** |
| **BLS API v1** | `api.bls.gov/publicAPI/v1/timeseries/data/` | ✅ CPI-U Jul 2026 = 333.918, **no key** | US public domain | **ADOPT — US actuals** |
| BoE IADB | `bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp` | ✅ **needs redirect-following**; Bank Rate 3.75 | BoE terms not read → **UNVERIFIED** | ADOPT (phase 2) |
| SNB | `data.snb.ch/api/cube/zimoma/data/csv/en` | ✅ + `PublishingDate` in payload | not read → **UNVERIFIED** | ADOPT (phase 2) |
| BoJ | `stat-search.boj.or.jp/ssi/mtshtml/csv/ir01_m_1.csv` | ✅ 200 text/csv | not read → **UNVERIFIED** | Covered by BIS for v1 |
| RBA | `rba.gov.au/statistics/tables/csv/f1-data.csv` | ✅ 200, 305 KB | not read → **UNVERIFIED** | Covered by BIS for v1 |
| OECD SDMX | `sdmx.oecd.org/public/rest/data/…` | ✅ AUS short rate 4.35 | **CC-style: commercial use OK with citation** | Research |
| Eurostat | `ec.europa.eu/eurostat/api/dissemination/…` | ✅ JSON-stat | Decision 2011/833/EU → **UNVERIFIED wording** | Research |
| World Bank | `api.worldbank.org/v2/…` | ✅ annual only | open | Low value |
| IMF SDMX (new) | `api.imf.org/external/sdmx/2.1/` | ⚠️ structure ✅, `IFS` dataflow **404** | — | **UNVERIFIED — spike needed** |
| IMF legacy | `dataservices.imf.org` | ❌ connection failed | — | **DEAD** |
| IMF DataMapper | `imf.org/external/datamapper/api/v1/…` | ✅ annual WEO + forecasts | — | Test fixture for future-dated rows |
| StatCan WDS | `www150.statcan.gc.ca/t1/wds/rest/…` | ⚠️ catalogue ✅, data endpoints HTTP 409 | — | **UNVERIFIED** |
| RBNZ | site GET | ❌ 403 | — | Use BIS |
| **DBnomics** | `api.db.nomics.world/v22/` | ✅ 93 providers; **no FRED, no CFTC; no vintage support** | `/legal` → 404, **UNVERIFIED** | **Research/discovery only** |
| **Trading Economics** | `api.tradingeconomics.com/calendar?c=guest:guest` | ❌ **HTTP 410 — guest discontinued** | Standard **$149/mo billed yearly**, actual+consensus | **OPERATOR DECISION — recommend NO for v1** |
| FMP / Finnhub / EODHD / Marketaux | calendar endpoints | ❌ 401 / 401 / 403 / 401 | paid | **UNVERIFIED tiers** |
| `fredapi` | 0.5.2 (2024-05-05) · pushed 2026-01-28 · Apache-2.0 | | | ADOPT or vendor |
| `full-fred` | 0.2 (2026-03-28) · 115★ · Apache-2.0 | | | Reference only |
| `pandas-datareader` | 0.11.1 (2026-06-24) · pushed 2026-07-21 · 3,234★ | **alive, contrary to belief** | NOASSERTION | **AVOID (no vintages)** |
| `sdmx1` | 2.27.0 (2026-08-07) · pushed 2026-08-07 · Apache-2.0 | | | ADOPT only if SDMX-ML needed |
| `pandaSDMX` | 1.10.0 (2023-02-25) · pushed 2023-12-28 | **abandoned** | Apache-2.0 | **AVOID** |
| `dbnomics` | 1.2.7 (2025-06-18) | **AGPL-3.0** | | **AVOID (licence)** |
| `wbdata` | 1.1.0 (2025-10-05) | GPL-2.0 | | **AVOID (licence)** |
| `cot-reports` | 0.1.3 (2023-12-29) · pushed 2024-04-06 | stale | MIT | **AVOID (use Socrata)** |
| **`arch`** | 8.0.0 (2025-10-21) · pushed 2026-08-10 · 1,551★ | | NCSA | **ADOPT — core** |
| **`ruptures`** | 1.1.10 (2025-09-10) · pushed 2026-07-06 · 2,071★ | | BSD-2-Clause | **ADOPT — core** |
| **`pandera`** | 0.32.1 (2026-06-29) · pushed 2026-08-07 · 4,433★ | | MIT | **ADOPT — core** |
| `statsforecast` | 2.1.1 (2026-07-16) · pushed 2026-08-17 · 4,868★ | 10 deps | Apache-2.0 | ADOPT — optional |
| `plotly` | 6.9.0 (2026-07-09) | 9.9 MB | MIT | ADOPT — app/research only |
| `great-expectations` | 1.20.0 (2026-08-07) · 11,713★ | **136 deps** | Apache-2.0 | **AVOID (weight)** |
| `sktime` | 1.1.0 (2026-07-28) · 9,926★ · 2,403 open issues | **37.6 MB** | BSD-3 | **AVOID** |
| `darts` | 0.46.1 (2026-07-20) · 9,497★ | torch is an extra | Apache-2.0 | Research only |
| `pymc` / `arviz` | 6.3.1 / 1.3.0 (Aug 2026) | very active | Apache-2.0 | Defer |
| `pingouin` | 0.6.1 (2026-03-28) · 1,929★ | | **GPL-3.0** | **AVOID (licence)** |
| `tsfresh` | 0.21.2 (2026-05-31) | | MIT | **AVOID (p-hacking risk)** |
| `volatility-trading` | PyPI 0.7.0 (2026-03-16), **repo stale 2024-10-21** | **PyPI says MIT, repo says GPL-3.0** | conflict | **AVOID — build our own** |
| `bidask` | 2.1.0 (2024-12-22) · `eguidotti/bidask` pushed 2025-10-13 · 136★ · **MIT** | Ardia/Guidotti/Kroencke JFE 2024 EDGE estimator from OHLC | MIT | **Nice-to-have.** We observe the spread directly, so this is a cross-check, not a necessity |
| `RiskLabAI` | 2.0.1 (2026-06-20) · **2★** · GitHub `NOASSERTION` vs PyPI BSD-3 | | conflict | **AVOID as dep; read as reference** |
| **NautilusTrader** | 1.231.0 (2026-08-02) | Bar aggregation taxonomy; `ts_event`/`ts_init` | **LGPL-3.0-or-later** | **Copy the design, not the code** |
| **QuantConnect LEAN** | pushed 2026-08-14 · 21,240★ | `ISlippageModel` + 5 slippage models + ~30 fee models | **Apache-2.0** | **ADOPT the interface shape** |
| Hummingbot | `20260729` (2026-07-29) | crypto MM | Apache-2.0 | Defer to crypto phase |
| **DuckDB `ASOF JOIN`** | in stack | ✅ doc-verified | MIT | **ADOPT — the as-of query engine** |
| **DuckDB `MERGE INTO` SCD2** | in stack | doc-verified | MIT | **ADOPT — the revision write path** |
| **Polars `join_asof`** | 1.43.2 | ✅ signature verified: `strategy`, `tolerance`, `by`, **`allow_exact_matches`**, `check_sortedness` | MIT | **ADOPT — `strategy="backward"`, `allow_exact_matches=False`** |
| ArcticDB | 6.23.0 (2026-08-17) | `as_of` = **transaction-time only** | **BSL 1.1**, narrower than file 02 implied | **AVOID (technical, not legal)** |
| Delta Lake / Iceberg | maintained | table-level time travel | Apache-2.0 | **AVOID (wrong granularity)** |
| XTDB | 0.6.2 (2023-11-22) | true bitemporal, JVM | | **AVOID (operational weight)** |

---

## 11. Recommendation

### 11.1 The smallest macro set for v1 — five sources

1. **BIS `WS_CBPOL`**, daily poll. All 8 policy rates, one call, no key. Produces every pair's rate differential.
2. **BIS `WS_EER`**, daily. Broad nominal effective exchange rates — the honest free DXY-family substitute, complementing the synthetic broker-quote index from file 06.
3. **FRED with a registered key**, daily, for `DGS2` / `DGS10` (2y and 10y yields → the market's forward view of #1) and `fred/releases/dates?include_release_dates_with_no_data=true` (the free forward-dated US release calendar).
4. **FairEconomy `ff_calendar_thisweek.json`**, polled **daily** and archived verbatim. Feeds the blackout gate immediately; builds the consensus-drift and release-schedule archive we can never buy retroactively.
5. **CFTC TFF Socrata**, weekly on Fridays after 15:30 ET. MIS context only, never a trigger.

ECB (DFR, HICP) and BLS (US CPI) are a close sixth and seventh — add them the week after v1 ships. Everything else waits.

### 11.2 The smallest micro set for v1 — four metrics plus two profiles

- **M1 quoted spread** per tick, archived.
- **M2 spread profile** by pair × hour-of-day × day-of-week (median, p90), rolling 60 days → publish a per-pair `tradeability` score to the MIS.
- **M3 tick arrival rate** as the liquidity proxy.
- **M4 spread cost as a share of edge**, computed per strategy at design time and refused if it exceeds a threshold.
- **M9 session profile** (Tokyo / London / NY / overlap) and **M10 rollover-window behaviour** at 17:00 New York.

All six are QMF-built, none needs a library, and together they answer the operator's two named questions.

### 11.3 Analyst libraries

Adopt: **`statsmodels`, `arch`, `ruptures`, `scipy.stats`, `pandera`**. Plus `plotly` for the Windows app and research only, and `statsforecast` if and only if forecasting becomes a real requirement.

### 11.4 The storage shape

**One append-only bitemporal `facts` table** (§9.2) in Hive-partitioned zstd Parquet, written through the SQLite WAL inbox, queried through DuckDB `ASOF JOIN` and Polars `join_asof(strategy="backward", allow_exact_matches=False)`. Two time axes on every row; `9999-12-31` as the open-interval sentinel; `known_at` the only column a backtest may touch; the accessor is `as_of(t)` and `ref_period` is not exposed as a filter.

`ref_period_start > known_at` is the definition of future data. That one predicate covers scheduled events, forecasts, consensus, model predictions and scenarios with no additional machinery.

### 11.5 What NOT to adopt, and why

| Do not adopt | Reason |
|---|---|
| `fredgraph.csv?…&vintage_date=` | Verified today: returns HTTP 200 and **silently ignores the vintage**. Would poison every macro backtest while looking correct. |
| `pandas-datareader` | Alive, but no vintage support and a lowest-common-denominator abstraction over flaky sources. |
| `pandaSDMX` | Abandoned since 2023. `sdmx1` superseded it. |
| `dbnomics`, `wbdata`, `pingouin` | AGPL-3.0, GPL-2.0, GPL-3.0 — copyleft in a proprietary framework. |
| `volatility-trading` | PyPI declares MIT, the repo declares GPL-3.0. Unresolvable licence ambiguity + 22 months stale. |
| `RiskLabAI` | 2 stars, licence mismatch between PyPI and repo. |
| `great-expectations` | 136 dependencies to do what `pandera` does in 55. |
| `sktime`, `darts`, `pymc`, `neuralforecast`, `prophet`, `tsfresh` | Research-laptop only. Never on the trading VPS. Deep-learning FX forecasting in particular is where retail projects die. |
| ArcticDB | Not the licence (BSL 1.1 is narrower than file 02 implied) — the problem is that `as_of` is **transaction-time only**, so it cannot express valid time without us re-encoding it anyway. |
| Delta Lake / Iceberg time travel | Versions the table, not the fact. Wrong granularity. |
| XTDB | A JVM database on the VPS for a 10⁶-row table. |
| Trading Economics for v1 | $1,788/year buys only the `actual`+`consensus` surprise family, which is the hardest edge to execute at retail spreads. Revisit after funding. |
| BIS Triennial turnover data | Interesting background, zero operational value. Our own tick archive measures what actually matters. |
| Polars `join_asof(strategy="forward"\|"nearest")` in production | Lookahead generators. Lint-ban them outside research notebooks. |
| COT as a Trigger or heavy Confirmation | The NY Fed's own study: "position data **do not predict** exchange rate changes over the following week." |

---

## Open questions

1. **OPERATOR RISK DECISION #1 — FRED third-party copyright.** FRED's ToU requires contacting the data owner before any non-personal use of copyrighted series. Does Mubarak want QMF restricted to non-copyrighted FRED series only (mechanically enforceable by checking series notes for "Copyright"), or accept the risk on internal-only use? The mandatory disclaimer notice ("This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis") must appear in the QMX app either way.
2. **OPERATOR RISK DECISION #2 — Trading Economics at ~$1,788/year.** This is the only verified route to historical `actual`+`consensus`. My recommendation is no for v1. Does he agree, or does he want the surprise-strategy family available from the start?
3. **OPERATOR RISK DECISION #3 — ArcticDB.** File 02 recorded a blanket commercial block; the licence text is narrower. I still say no on technical grounds. Does he want file 02 amended so the record is accurate?
4. **ForexFactory terms.** Still the open risk from file 06, and now more load-bearing: my recommendation makes daily archiving of that feed a foundational, unrecoverable-if-delayed activity. Whether daily automated polling and permanent local archiving is acceptable under ForexFactory's terms is his call, not an engineering one.
5. **When does the archive start?** Every day without the ingestion archive is a day of point-in-time macro history permanently lost for every source except ALFRED. This argues for building ingestion **before** anything that consumes it — an ordering decision that affects the whole build plan.
6. **IMF new SDMX dataflow IDs — UNVERIFIED.** `api.imf.org` structure endpoints work but `IMF,IFS` 404s. A half-day spike would settle whether IMF is worth anything to us. Low priority.
7. **Statistics Canada WDS — UNVERIFIED.** Every data endpoint returned HTTP 409 "The product is not released yet" while the catalogue worked. Needs a spike before any CAD macro work is scheduled.
8. **`revision_class` assignment.** Who decides whether a series is `never` / `minor` / `heavy`? Proposal: default `heavy` for anything survey- or accounts-based, `never` for market-observed rates, and require an explicit registration entry per series. Needs ratification.
9. **`known_at` for undated sources.** BIS, ECB, OECD, RBA and BoJ do not stamp publication time in the payload (SNB is the honourable exception). Do we set `known_at = observed_at` (safe, slightly pessimistic) or model each source's known publication schedule (accurate, more maintenance)? I lean safe-and-pessimistic for v1, with `known_at_is_estimated=true`.
10. **The two-step as-of accessor.** §9.4 notes that the naive one-step `ASOF JOIN` returns the most recently *published* fact, not the latest *reference period* as believed at T. The accessor must do the two-step. This needs to be written as a component spec, not left to whoever writes the first adapter.
11. **Does the MIS publish `tradeability` as a hard gate or a soft weight?** M2 gives a per-pair, per-hour score. Whether a low score *blocks* trading or merely down-weights a Confirmation is an operator policy decision with real consequences for prop-firm challenges.
12. **Bipower variation / two-scale realised volatility.** No maintained Python implementation found. If tick-level realised volatility ever becomes a required MIS input, that is a build with a named estimator and a documented sampling frequency — not something to improvise.
