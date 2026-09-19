# Session / calendar family — unbounded MQL5 research notes

**Date:** 2026-09-15  
**Family:** sessions, time-of-day, time filters, news/calendar windows, overlaps, kill/dead zones, session breakouts  
**Corpus:** `.worktrees/mql5-library/data/mql5-library/` only (on-disk markdown). No mql5.com. No git writes. No production code.  
**Output:** `extractions/session_calendar.jsonl` + this note.

## QMX ownership (binding for placement)

| Concern | Owner |
|---|---|
| `session_id` / TOD bucket / overlap flag | **MIS** snapshot label (coordinate) |
| SQS baseline keyed by session | **SQS** may *key off* `session_id`; session ranges as **locations** may be SQS blocks; clocks are not SQS |
| News / economic-event windows | **CT-31** — never SQS |
| `news_window_active` | **MIS** may snapshot; **Book owns invalidation** |
| Entries, pendings, straddles, capital rotation | **Bot / Book** — never MIS |

Prior pass already fully read 24 articles (regime miner A + scalp miner B). This pass **full-reads 37 NEW** articles beyond that set.

**Prior 24 (not re-counted here):** 17737, 23286, 22940, 16830, 15223, 23482, 23016, 10715, 23454, 21003, 14203, 19944, 9804, 23355, 22938, 22939, 15748, 19290, 18867, 1575, 21235, 16752, 9231, 22772.

**New full-reads (37):** 18821, 3395, 4102, 20037, 17239, 20339, 20995, 21388, 21446, 21515, 21803, 22231, 22196, 22516, 22580, 22990, 23169, 9874, 13705, 14993, 16223, 16380, 17271, 17603, 17999, 18754, 18817, 719, 23546, 17986, 16171, 21976, 18486, 19886, 14324, 23388, 16301.

Machine rows: [`../extractions/session_calendar.jsonl`](../extractions/session_calendar.jsonl).

---

## 1. What the corpus actually gives (method clusters)

### 1.1 Clock / session gates (infrastructure)

- **3395** — OO time-filter library (range, DOW, timer, intraday schedule, reverse flag). GMT offset applied as naive `hour+gmt`.
- **20037** — Modern modular gate: clock ∧ (session OR…) ∧ (event stub); midnight wrap; shared GMT offset with session visualizer; **fail-open** if visualizer missing.
- **21515** — Discipline layer: binary allowed/blocked from session + news files; transaction-level intercept (platform analogue of Book door).
- **13705** — Hardcoded GMT session tables + broker offset for multi-currency EA allowlists.

**QMX cut:** MIS emits `in_clock_window` / `session_id` / `dow_allowed`. Book consumes as door. Do not ship 20037’s fail-open or 3395’s naive GMT+hour as the production clock.

### 1.2 Hour-of-day / seasonality / capital by session

- **18821** — Per-hour direction probability / mean move / vol (ISI ProSpread SMA); session lore + DST caveat in prose; claims crypto applicability without crypto ontology.
- **21976** — Time-of-day **capital rotation** (less Asia, more London/NY). This is **Book sizing**, not MIS.
- **22516** — Best feature-engineering article: Fourier cyclical time, **UTC-fixed** session flags, `session_overlap`, session-conditional vol with `shift(1)`, calendar-effect gate by timeframe, MT5 broker-local export trap.

### 1.3 Session breakouts / boxes / ORB / acceptance

- **17239** — Asia box breakout (default 23:00–03:00); author **assumes server time = GMT** (trap).
- **20339 / 18486 / 19886** — Session ORB family: start HH:MM + duration → range → breakout; server-time strings; DST/midnight warnings in teaching parts.
- **20995** — Session H/L + CPI acceptance/rejection (analytical, closed candle, no lookahead into level).
- **21388 / 23169 / 22990** — Session TPO / volume profile POC+VA / session VWAP (reset at **broker midnight**).

**QMX cut:** Box/ORB/POC/VA **levels → SQS blocks** if promoted. Breakout *alerts/entries → bot*. MIS keeps `session_ohlc`, `orb_defined`, `session_vwap` as coordinates.

### 1.4 Asia night (flat / spike) — not continuation

- **4102** — Asia night: BB mean-reversion on EURUSD-class flat; dual-pending JPY spike at fixed MSK hour. In-sample 2017 Halifax; real-ticks PF much weaker than OHLC. DOW matters, no stable DOW law.
- Complements prior **1575** (Asia continuation myth falsified) and prior **18867** (London box).

**Asia continuation status:** Still **not proven**. 1575 falsified “whole day follows Asia.” 4102/17239 trade *intra-Asia structure or post-Asia break*, which is a **different claim**. No new article in this pass rehabilitates Asia→day continuation. Do not treat “Asia continuation” as a certified playbook.

### 1.5 News / calendar windows (CT-31 family)

Method spine (filter, not alpha):

| Article | Role |
|---|---|
| Prior **21235** | Pre/post news windows; block new entries |
| **21446** | Suspend/restore SL/TP inside window (execution mitigation) |
| **21803** | Persist suspend state across terminal restart |
| **22231** | Static/CSV calendar for tester (live API blind) |
| **22196** | Reproducible news-layer architecture; TimeTradeServer vs TimeLocal |
| **22580** | Calendar + CSV fallback; optional size-down vs block |
| **16380** | Currency + importance + time filters (kernel) |
| **9874 / 16223** | Calendar API primers |
| **14324** | SQLite calendar + **DST-type tables** for PIT backtests |
| **17603 / 17999 / 14993** | Resource dumps, smart filters, wizard tests |
| **18754 / 18817 / 17271 / 719** | Pending straddle / post-impact / auto entry — **bot** |
| **17986** | News+ML — shadow only |
| **23546** | News helper ergonomics |
| **16301 / 18299 series** | Mostly UI; low producer value (18299+ UI parts not method-bearing enough to promote) |

**Hard rule:** News control = **CT-31 windows**. Never fold into SQS. MIS may snapshot `news_window_active`; Book invalidates / decides flatten or suspend-stops.

---

## 2. Broker-server time / DST traps (flagged)

These recur across the family and are load-bearing for any `session_id` producer:

1. **`TimeCurrent()` / chart hour = broker server time**, not London, not UTC, not the operator’s laptop (`TimeLocal`).
2. **`TimeTradeServer()` vs `TimeCurrent()` vs `TimeLocal()`** — 22196 and **23388** document silent wrong session-open checks if the wrong clock is passed; **no error is raised**.
3. **`TimeGMT()` is not trustworthy as true GMT** in Strategy Tester / some broker setups (**16171**). Therefore `tzOffset = TimeCurrent()-TimeGMT()` (**22580**) is fragile without venue validation.
4. **DST flips move institutional opens on the broker clock** even when UTC session definitions are fixed (**16171** Tokyo example: 02:00 → 01:00 broker after DST).
5. **US vs EU vs AU DST calendars differ** — US news can stay synced to a US-DST broker while UK news shifts an hour (**14324**). Need broker DST *type*, not a single boolean.
6. **Naive `hour + gmt` (3395)** and **“DST doesn’t matter because the server also advances” (13705)** are both insufficient / wrong for mixed calendars and UTC-fixed features.
7. **UTC-fixed session flags (22516)** are the cleanest *feature* approach (stationary across years) but intentionally drift 1h vs local exchange opens under DST — acceptable for ML features, not for compliance with exchange RTH.
8. **Broker midnight VWAP reset (22990)** ≠ UTC day ≠ NY 17:00 close.
9. **Fail-open filters (20037)** silently disable protection if session config missing.
10. **Static calendar dumps (22231 / 17603 / prior 16752)** must be stamped in the same frame as the replay clock or windows are fiction.

**QMX implication:** `session_id` and `news_window_active` require an explicit **clock provenance** object (`broker_tz`, `dst_schedule`, `source=TimeTradeServer|UTC`). If `not_ready`, Book should refuse session-conditioned doors rather than guess.

---

## 3. Crypto 24/7 vs FX sessions

| FX assumption in corpus | Crypto transfer |
|---|---|
| Sydney/Tokyo/London/NY open clusters | No exchange-open geography; “London” is at best a liquidity/participation cluster |
| Weekend gap / Friday NY close / Sunday open flags (22516) | Weak or absent on 24/7 venues |
| Asia night flat (4102) | No Tokyo open; quiet periods are venue-specific |
| ORB from “session start” (20339/19886) | Needs a **synthetic** session definition |
| Broker midnight session VWAP (22990) | Prefer UTC day or funding-period session |
| Macro calendar news windows | Still relevant for USD-sensitive crypto, but calendar completeness and PIT differ |
| SQS baseline keyed by FX `session_id` | Needs a crypto TOD/liquidity ontology before keying |

Do not port FX session enums onto crypto without a separate venue map. Hour-of-day features may still exist; they are not “London session.”

---

## 4. Overlaps, kill zones, dead zones

**Overlaps (method-bearing):**

- London–NY (~13:00–16:00 UTC in 22516) — highest vol / liquidity; primary overlap feature.
- Tokyo–London (~07:00–09:00 UTC) — secondary transition.
- 18821 prose: strongest activity on London/NY intersection; Pacific quiet.

**Dead / kill-style zones (corpus language is softer than ICT “kill zone” branding):**

- Post-NY / illiquid hours (20037, 21515).
- Pacific/Sydney quiet (18821).
- Weekend / Friday late (prior 9804; 22516 `friday_ny_close`).
- News blackout windows (CT-31) — structural refuse, not SQS.
- Asia as *soft* size dead-zone for trend systems (21976 allocates less capital) while flat/MR systems (4102) treat it as the *trade* zone — **Book policy chooses which**.

No article in this pass provides a calibrated ICT-style kill-zone edge; treat named kill zones as **unproven folklore** unless later measured.

---

## 5. Asia continuation myth — status after this pass

| Claim | Status | Evidence |
|---|---|---|
| “Whole day follows Asia direction” | **Falsified** (prior) | `md/1575.md` — ~coin-flip continuation on 50-day sample |
| Asia range is often quieter on EURUSD-class | **Lore with weak IS support** | 4102, 18821 |
| Asia box → later breakout is an edge | **Unproven** | 17239, prior 18867 — method only |
| Asia dir as MIS *feature* | **Allowed** | Coordinate, not trigger |
| Asia continuation as Book playbook | **Do not admit** without a later certified candidate | OPERATING_LINE + prior scalp notes |

No rehabilitation of the continuation myth found in the 37 new reads.

---

## 6. MIS / SQS / Book / CT-31 placement map (this family)

| Primitive | MIS | SQS | Book | Bot | CT-31 |
|---|---|---|---|---|---|
| `session_id` / session flags / overlap | yes | keys baseline | door | — | — |
| `tod_hour` / Fourier hour features | yes | — | door | — | — |
| Session H/L, ORB, POC, VA | coordinate | **levels/blocks** | — | entries | — |
| `session_vwap` | coordinate | only if levelized | — | cross | — |
| `news_window_active`, minutes_to/from event | snapshot | **never** | **invalidates** | optional flatten | **owns window** |
| Suspend stops / size-down in news | — | never | **policy** | execute | window input |
| TOD capital rotation | session_id only | — | **sizes** | — | — |
| Hour-direction bias / Asia continuation entry | — | — | refuse unless certified | if ever | — |
| Dual news/Asia pendings | — | never | likely refuse | yes | window |

---

## 7. Highest-transfer articles (short list)

1. **22516** — UTC session features + overlap + lookahead-safe session vol + MT5 TZ export trap.  
2. **16171** — Broker TZ/DST detection; TimeGMT unreliability.  
3. **14324** — DST-type-aware calendar DB (US/EU/AU asymmetry).  
4. **22196 / 22231 / 21803 / 21446** — News window engineering spine (clock, tester, durability, stop policy).  
5. **23388** — Silent TimeTradeServer vs TimeCurrent failure mode.  
6. **20037 / 21515** — Binary time+news permission patterns (Book-door analogues).  
7. **20995** — Session level acceptance/rejection without claiming entry edge.  
8. **4102 + prior 1575** — Asia night methods vs continuation myth boundary.

---

## 8. Leftovers / deliberately de-weighted

- **18299+ Animated News Headline UI parts** (I–V, VIII–XI): dashboards, scrollers, buttons — low method density. VI/VII (18754/18817) kept as bot patterns.  
- Pure calendar dashboard parts (**16301**, later canvas/SQLite UI **22597/22608**): skip for producers.  
- News-entry automations (**17271**, **719**, straddles): negative examples for MIS.

---

## 9. PLAN implications (no build)

1. Specify `session_id` with **UTC-fixed** flags (22516) plus a separate **broker_tz/dst** readiness bit (16171).  
2. Let SQS baseline key off `session_id` only when clock provenance is ok.  
3. Keep news in **CT-31**; MIS snapshots `news_window_active`; Book invalidates; never SQS.  
4. Session box/ORB/POC/VA wait for **SQS blocks**, not MIS entries.  
5. Do not encode Asia continuation, hour-bias direction, or TOD capital rotation inside MIS.  
6. Replay/QMB must **record** session and news labels (TN-21 posture) rather than recompute from a wrong tester clock.  
7. Crypto needs a separate session ontology before any FX session enum is reused.

## Sources

Local corpus paths under `C:\Users\Mubarak\Desktop\QMX\.worktrees\mql5-library\data\mql5-library\md\`.  
Extractions: `workroom/research/2026-09-15_unbounded-market-intelligence/extractions/session_calendar.jsonl`.  
Operating constraints: `OPERATING_LINE.md`, prior `2026-09-09_mql5-mis-regime-notes.md`, `2026-09-09_mql5-mis-scalp-notes.md`.
