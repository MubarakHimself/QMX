# Calendars & FX Value-Dates — exchange_calendars, pandas_market_calendars, fx-value-date

**Scope:** two mature, actively-maintained Python market-calendar libraries (`exchange_calendars`, `pandas_market_calendars`) and one tiny, single-author TypeScript FX value-date utility (`fx-value-date`). Focus questions: what does a mature `is_open(dt)` / `sessions_in_range` / holidays / early-closes API actually look like, what does a 24/5 forex-session variant need that equity calendars never had to solve, and does `fx-value-date`'s spot/forward rule set stand in as the specification for `qmf.venue_model`'s swap/rollover accounting.

---

## In plain words

1. `exchange_calendars` and `pandas_market_calendars` are the real thing: 50+ exchange calendars, a shared abstract base class, a `schedule` DataFrame with `open`/`break_start`/`break_end`/`close` columns, and a consistent verb set (`is_session`, `sessions_in_range`, `sessions_window`, `is_open_on_minute`, `next_open`, `previous_close`). As of `pandas_market_calendars` v2.0 the second library literally mirrors the first — they are one ecosystem, not two competing designs.
2. Both ship as **static, versioned code** — holiday tables are baked into the package at release time, not fetched from a server. "Update the library" is how you get a corrected holiday. That is a good, boring, worth-copying idea.
3. Neither library has ever needed to model a 24-hour, multi-timezone, always-open market. The closest either gets is a single flat `AlwaysOpenCalendar` ("24/7") and `WeekdayCalendar` ("24/5") — one open time, one close time, no internal structure, fixed in UTC, zero DST awareness because there is nothing to be DST-aware *of*.
4. `pandas_market_calendars`'s actual `ForexExchangeCalendar` (OTC spot FX) treats the entire trading week as **one session**: Sunday 17:00 to Friday 17:00, both anchored to `America/New_York`, no holidays at all. There is no Sydney, no Tokyo, no London, no overlap window, no rollover marker distinct from the week's own open/close. This is the single clearest piece of evidence in the whole assignment: the most mature calendar tooling in the Python ecosystem has never had to represent what QMX actually needs.
5. The CME Globex FX **futures** calendar (a different product from spot FX) is the same shape — one `market_open`/`market_close` pair per business day, offset `-1` day so Sunday evening counts as "opening" the next day's session — plus ordinary holiday closes and early-close specials borrowed from the US equity calendar. Still no sub-session structure.
6. `fx-value-date` is the opposite kind of artifact: ~270 lines, zero dependencies, one author, days old, no track record — and yet the logic inside it (spot lag, the USD intermediate-day rule, modified-following, end-of-month tenor rolls) is exactly the settlement math a forex swap/rollover line item needs. Small and unvetted is not the same as wrong; the algorithm is checkable by reading it, and it reads correctly against its own test cases.
7. The two mature libraries are **wrap-worthy for their API shape, not for their forex data model** — pulling either in as a runtime dependency buys 50 equity/futures calendars QMX will never use, at the cost of a mandatory `numpy`+`pandas` dependency on the trading VPS, in exchange for a forex calendar that is *less* detailed than what `qmf.venue_model` already needs to build from scratch.
8. `fx-value-date` is **not wrap-worthy at all** in the literal sense — it's TypeScript/npm, unusable from Python — but it is exactly re-specify-worthy: port the four rules (spot lag table, USD intermediate-day rule, EOM+modified-following forward tenor, business-day-convention adjuster) into `qmf.venue_model`'s rollover module, keeping its clean design choice of **injecting** holiday calendars as predicates rather than owning holiday data itself.
9. The one structural idea worth lifting wholesale from `exchange_calendars` is the **`(time, day_offset)` tuple for session boundaries** — `(None, time(17), -1)` meaning "17:00 the day before the session date." That is precisely the right primitive for a session that starts the evening before its nominal calendar date (Sydney's Monday session opening Sunday evening UTC), and QMX should copy the pattern even though it must build the surrounding session model itself.
10. Verdict up front: **re-specify, not wrap.** Read both calendar libraries closely for naming and internals, port `fx-value-date`'s rules faithfully into Python, but build `qmf.venue_model`'s forex session/rollover object as new code — because the one thing that object exists to represent (four overlapping named sessions, a weekend gap, a rollover hour, and DST transitions that land on different Sundays in different countries) has no precedent in any of the three repos.

---

## Findings per repo

### `exchange_calendars` — Apache-2.0

The mature reference implementation. Abstract base class `ExchangeCalendar` (`reference/repos/exchange_calendars/exchange_calendars/exchange_calendar.py:146`) defines the full API surface a calendar subclass gets for free once it declares `regular_market_times`, `tz`, `regular_holidays`, `adhoc_holidays`, `special_opens`/`special_opens_adhoc`, `special_closes`/`special_closes_adhoc` (`:593-746`).

Core query methods, all present and doing what their names say:
- `is_session(date)` (`:1265`) — is this calendar date a trading day at all.
- `is_open_on_minute(minute, ignore_breaks=False)` (`:1404`) and `is_open_at_time(timestamp, side=...)` (`:1442`) — the actual `is_open(dt)` equivalent, parameterised by a `side` enum (`"left"|"right"|"both"|"neither"`) controlling whether the exchange counts as open exactly *at* its own open/close/break boundaries. This `side` parameter is a genuinely useful idea: it makes "is a fill at exactly 17:00:00.000 in-session or not" an explicit, testable choice instead of an off-by-one bug.
- `sessions_in_range(start, end)` (`:2202`) and `sessions_window(session, count)` (`:2242`) — exactly the two range-query shapes QMX needs, returning a `pd.DatetimeIndex` of session dates.
- `next_open` / `previous_close` (`:1531`, `:1620`) for stepping to the next/prior open boundary.
- `sessions_has_break` (`:2223`) — flags any session in a range with a lunch-style break, feeding a `schedule` DataFrame with `break_start`/`break_end` columns (visible in the README's HKEX example, `README.md:37-49`).

Holidays and early closes are two orthogonal properties, not one list: `regular_holidays` is a `pandas` `AbstractHolidayCalendar` (recurring rules, e.g. "third Monday of January"); `adhoc_holidays` is a flat list of one-off dates; `special_closes`/`special_opens` are `(time, HolidayCalendar|int)` pairs describing a *recurring* early close (Thanksgiving Friday at 13:00, say); `special_closes_adhoc`/`special_opens_adhoc` cover one-off early closes not tied to a rule. This four-way split (regular/adhoc × holiday/special-time) is the correct factoring — it is the same shape QMX's own `qmf.venue_model` should copy for prop-firm-relevant closures (e.g. a broker's own ad-hoc Christmas-week early close is not the same kind of fact as "always closes early on the day before Independence Day").

Two purpose-built minimal calendars exist and are directly relevant: `AlwaysOpenCalendar` ("24/7", `always_open.py`) and `WeekdayCalendar` ("24/5", `weekday_calendar.py`) — both fixed in `UTC`, both a single `(None, time(0))` open/close pair with `close_offset=1` (close is midnight the *next* day). These are literally the naive "forex is a market that's open all week" answer this ecosystem has ever produced, and they confirm finding #3/#4 above by being exactly that thin.

**Quality verdict:** genuinely mature, well-factored, well-tested software (property-based tests via `hypothesis`, per-calendar CSV answer fixtures, CI matrix across OS/Python versions per its own `AGENTS.md`/CI config). Worth reading closely for API naming and the boundary-inclusion (`side`) idea. Not worth depending on for forex — it has no forex-session concept beyond the flat 24/5 calendar, and adopting it pulls `numpy`+`pandas` into a runtime that the module map's "two lockfiles" decision wants to keep minimal.

### `pandas_market_calendars` — MIT

As of v2.0 this package **mirrors every `exchange_calendars` calendar** and adds its own product-specific futures calendars (`README.rst:50-51`); the two are effectively one ecosystem with two entry points. `MarketCalendar` (`pandas_market_calendars/market_calendar.py:74`) is a parallel abstract base with the same shape: `regular_market_times`, `schedule(start_date, end_date, tz=..., market_times=...)` (`:717`) building the open/close/break DataFrame, `holidays()` (`:574`) returning a `CustomBusinessDay` offset object, `early_closes(schedule)` (`:1073`) filtering a schedule down to rows where the close differs from the regular close, `is_open_now(schedule, ...)` (`:1039`).

`ForexExchangeCalendar` (`calendars/forex.py`) is this package's *actual* answer to "what is a forex calendar": `regular_market_times = {"market_open": ((None, time(17,0), -1),), "market_close": ((None, time(17,0)),)}`, `weekmask = "Sun Mon Tue Wed Thu Fri"`, `tz = ZoneInfo("America/New_York")`, no `regular_holidays` at all. In plain terms: one continuous session per week, Sunday 17:00 NY to Friday 17:00 NY, with the `(None, time(17,0), -1)` tuple meaning "opens at 17:00 the calendar day before." This is honest and correct as far as it goes (retail forex genuinely has almost no exchange-style holidays — liquidity just thins around Christmas/New Year rather than the market formally closing), but it stops at exactly the point QMX needs it to continue: there is no session decomposition inside that one long week.

`cme_globex_fx.py` — the CME **futures** FX calendar (a different, listed-derivative product from spot forex) — is the same one-session-per-day shape: `market_open` at 17:00 offset -1 day, `market_close` at 16:00, US-holiday-derived `regular_holidays` (New Year, Good Friday, Christmas) and `special_closes` borrowed wholesale from the US equity holiday list (Martin Luther King Day, Presidents' Day, Thanksgiving, etc. — `calendars/cme_globex_fx.py:56-101`). Useful as evidence that even a listed FX-futures venue's calendar collapses to "one open, one close, occasional early close" — the multi-session structure QMX needs is a spot-forex-specific, liquidity-driven concept that doesn't exist even one level up the derivatives stack.

**Quality verdict:** mature, actively maintained, honest about its own limits ("does not request market hours from a server at runtime… install a newer package release," `README.rst:33-38` — a good design note in itself). Its `ForexExchangeCalendar` is correct but deliberately minimal — it is not hiding a richer forex model; there simply isn't one to find here.

### `fx-value-date` — MIT

Single-file (`src/index.ts`, ~270 lines), zero runtime dependencies, one author (Moshe Malka), days-old per the catalog study's flag. Read start to finish; the algorithm is small enough to verify by hand and its own `vitest` test file (`test/index.test.ts`) covers the cases that matter: T+2 crossing a weekend, T+2 rolling off a US holiday, T+1 pairs (USD/CAD etc.), the USD intermediate-day rule on a non-USD cross (EUR/GBP), and the modified-following month-end-rollback case.

Four rules, each independently checkable:
- **Spot lag** (`spotLag(pair)`, `:114-117`): 1 business day for a small hard-coded set of T+1 pairs (`USD/CAD`, `USD/TRY`, `USD/PHP`, `USD/RUB`), 2 otherwise. This table is not exhaustive of real FX market convention (e.g. USD/MXN is also commonly T+1) — treat it as a *pattern* to re-derive against a proper reference, not as ground truth to copy verbatim.
- **Spot value date** (`spotValueDate`, `:135-162`): step forward `lag` joint-business-days (a day must be a business day on *both* legs' calendars to count), with the USD intermediate-day rule for non-USD crosses — the T+1 day must additionally be USD-good even though USD isn't in the pair, because the cross is presumed to settle relative to USD's clearing calendar. Then roll the final date forward again if the value date itself isn't jointly good.
- **Business-day adjustment** (`adjust`, `:176-206`): the four standard conventions (`following`, `modified-following`, `preceding`, `modified-preceding`), including the "if `following` crosses a month boundary, roll backward instead" rule that gives `modified-following` its name.
- **Forward tenor value date** (`forwardValueDate`, `:224-255`): day/week tenors add calendar days then adjust modified-following; month/year tenors add calendar months with the **end-of-month rule** (if spot lands on the last day of its month, the forward tenor also lands on the last day of its target month, not on the same day-number) and then adjust.

The design choice to **inject** holiday calendars as `(isoDate) => boolean` predicates rather than shipping holiday data is exactly right for QMX's situation — QMX will have its own FX holiday source of truth (broker-observed rollover calendar, or a maintained table), and a value-date module that takes calendars as parameters rather than owning them stays decoupled from that source.

**Quality verdict:** small, honestly scoped, no track record, but the logic is transparent and testable, and it reads as correct for the cases it claims to handle. Appropriate to treat as `evidence_state: hypothesis` — a specification to re-derive and test against QMX's own fixtures, not a dependency to trust blindly (it has never been run against a real settlement system, has no maintainer history, and its T+1-pair list is known-incomplete).

---

## Mental models worth borrowing

| Idea | Where | Why for QMF | How QMF implements |
|---|---|---|---|
| Boundary-inclusion as an explicit parameter, not an implicit off-by-one | `exchange_calendars.exchange_calendar.ExchangeCalendar.is_open_at_time(timestamp, side=...)`, `exchange_calendar.py:1442` | A forex fill or bar boundary landing exactly on a rollover-hour or weekend-gap edge is exactly the kind of ambiguity that silently corrupts backtests. Making "open on the boundary itself" a named, tested choice removes a whole class of off-by-one bugs. | `qmf.venue_model`'s session-membership check takes a `side` (or equivalent) argument the same way; property-tested at the boundary minute for every session edge (Sydney open, weekend close, DST-shifted London/NY overlap). |
| `(local_time, tz)` pair as the session-boundary primitive, not a fixed UTC hour | `ForexExchangeCalendar.tz = ZoneInfo("America/New_York")` + fixed `17:00` local open/close, `calendars/forex.py:24-39` | DST-awareness comes for free when a boundary is defined as "17:00 in this timezone" rather than a UTC offset — `zoneinfo` resolves the correct UTC instant on both sides of a DST transition automatically. | Each of QMX's four named sessions (Sydney/Tokyo/London/NY) is defined the same way — `(tz, local_open_time, local_close_time)` — resolved to UTC per calendar day, not hardcoded as a UTC window. |
| `(time, day_offset)` tuple for a session that opens the evening before its nominal date | `regular_market_times = {"market_open": ((None, time(17,0), -1),)}`, `calendars/cme_globex_fx.py:44-47` and `exchange_calendars`'s `_tdelta` handling of `(time, day_offset)` tuples, `exchange_calendar.py:98-103` | Sydney's Monday session (UTC) genuinely opens Sunday evening; a naive "open time on this calendar date" model gets this backwards. | `qmf.venue_model`'s session definitions use the same `(local_time, day_offset)` shape for Sydney's open and for the Friday-evening→Sunday-evening weekend gap. |
| Four-way split of closures: regular-recurring / one-off, holiday vs early-close | `regular_holidays` / `adhoc_holidays` / `special_opens(_adhoc)` / `special_closes(_adhoc)`, `exchange_calendar.py:593-746` | Forex's rare true closures (Christmas Day illiquidity, a broker's own maintenance window) are a different *kind* of fact from "this pair's spread triples every day at the NY 17:00 rollover" — conflating them into one list loses information a prop-firm rule or a sizing model would want separately. | `qmf.venue_model` keeps a small `adhoc_closures` list (broker-announced) separate from the recurring `rollover_hour`/`weekend_gap` structure; `qmf.data.micro`'s tradeability score reads the latter, `qmf.bms` reads the former. |
| Calendars shipped as static, versioned code — never fetched live | `README.rst:33-38` ("does not request market hours from a server at runtime… install a newer package release") | Matches the module map's own decision that `qmf.data.ingest` sources terminate in a schema check and that nothing live-critical should depend on an unversioned network call. | QMX's FX holiday/rollover table (thin — forex has almost no true holidays) ships as a reviewed, versioned file inside `qmf.venue_model`, bumped on release like any other calendar package, not fetched at runtime. |
| Inject the holiday calendar as a predicate; don't own the data | `fx-value-date`'s `HolidayCalendar = (isoDate: string) => boolean` parameter, `src/index.ts:16-29` | Keeps the value-date *algorithm* decoupled from the *source* of holiday truth — QMX can point it at a broker-observed rollover calendar without forking the logic. | `qmf.venue_model.spot_value_date(...)` and `forward_value_date(...)` take calendar predicates as arguments; the actual FX holiday table lives in `qmf.data` and is swappable per venue. |
| USD intermediate-day rule, end-of-month forward-tenor rule, modified-following/-preceding adjuster | `fx-value-date`, `src/index.ts:119-255` | This is the exact rule set a swap/rollover P&L line needs to compute value dates correctly for crosses and for forward-tenor rolls — nobody else surveyed in QMF's research has this. | Port the four functions (`spotValueDate`, `adjust`, `forwardValueDate`, and the T+1-pair override) into `qmf.sim`'s `financing` line / `qmf.venue_model`'s rollover module as Python, re-testing every case in the TS test file plus QMX's own broker-specific T+1-pair list. |

---

## What to avoid

- **Depending on `exchange_calendars` or `pandas_market_calendars` at runtime for `qmf.venue_model`.** Both mandate `numpy`+`pandas` (and `pyluach`, `korean_lunar_calendar`, `tzdata` for the former) to get 50+ equity/futures calendars QMX will never call. That is exactly the >50MB/>30-dependency "research-only" bucket the module map's lockfile rule (`10 §8.2`) was written to keep off the trading VPS. Read them; don't `pip install` them into the trading lockfile.
- **Trusting `pandas_market_calendars`'s `ForexExchangeCalendar` as "the" forex calendar.** It is correct and honestly scoped as a single-session week, but treating it as evidence that "forex calendars are basically solved" would be a mistake — it deliberately omits everything QMX actually needs (session decomposition, rollover-hour marking distinct from close, tradeability-by-hour).
- **Copying `fx-value-date`'s T+1 pair list verbatim.** It lists `USD/CAD`, `USD/TRY`, `USD/PHP`, `USD/RUB` as T+1 and is silent on other commonly-T+1 pairs (e.g. `USD/MXN` in some conventions) — re-derive this table from a primary source or the actual broker's rollover behaviour rather than trusting a days-old, single-author list.
- **Treating `fx-value-date` as a dependency rather than a specification.** It's TypeScript/npm and unusable from Python directly, and — separately from the language mismatch — it has zero track record; port the logic, then verify it against QMX's own fixtures and (where possible) a broker's actual observed value dates, before letting it touch the financing P&L line.
- **Assuming DST is "handled" once each session uses a `(tz, local_time)` pair.** That pattern fixes single-session DST correctly, but it does *not* by itself solve the forex-specific problem of **misaligned DST transition dates across countries** — the US and UK/EU change clocks on different Sundays in spring and fall, so the London/New York overlap window shifts by an hour for one to three weeks each year. None of the three repos studied here have ever had to represent that, because none of them model more than one timezone-anchored session at a time. This has to be designed and tested explicitly in `qmf.venue_model`, not assumed to fall out of copying the `(tz, local_time)` primitive.

---

## Licence & maturity

| Repo | Licence | Maturity verdict |
|---|---|---|
| `exchange_calendars` | Apache-2.0 (confirmed `LICENSE`) | Mature, actively maintained: `hypothesis`-based property tests, per-calendar CSV answer fixtures, CI matrix (Ubuntu/Windows/macOS × Python 3.10/3.14), a documented dependency-update routine, 50+ calendars. Fork of the unmaintained `trading_calendars` (Quantopian), now independently maintained under `gerrymanoim`. |
| `pandas_market_calendars` | MIT (confirmed `LICENSE`; `NOTICE` documents it as a zipline/Quantopian-derived fork, Apache-2.0 origin acknowledged, MIT re-license permitted) | Mature, actively maintained: versioned major-release history through v5.0 documented in its own README, mirrors `exchange_calendars` since v2.0, explicit "no live network calls" design statement. |
| `fx-value-date` | MIT (confirmed `LICENSE`) | Single-author, days-old per the catalog study's own flag; no stars/history signal available in this clone. Small enough (one file) to fully read and independently verify rather than merely trust — which this study did. Treat as `evidence_state: hypothesis`, re-tested before use, not as a maintained dependency. |

---

## Verdict: wrap vs re-specify for `qmf.venue_model`

**Re-specify, not wrap**, for both halves of this assignment:

- **Session-calendar API shape:** read `exchange_calendars`/`pandas_market_calendars` closely and copy their *vocabulary and boundary semantics* — `is_session`/`sessions_in_range`, the `side`-parameterised open check, the `(local_time, tz, day_offset)` boundary primitive, the four-way regular/adhoc × holiday/special-time split. Do not depend on either package at runtime: their forex data model is thinner than what QMX needs (one flat session), and their dependency weight (`numpy`+`pandas`+extras) is wrong for the trading-VPS lockfile. Build `qmf.venue_model`'s session object as new code carrying four named, overlapping, DST-aware sessions plus an explicit weekend gap and rollover hour — a data model none of the three repos studied here contain.
- **Spot/forward value-date rules:** port `fx-value-date`'s algorithm (spot lag, USD intermediate-day rule, modified-following/-preceding, end-of-month forward-tenor roll) into Python inside `qmf.venue_model`/`qmf.sim`'s financing line, keeping its calendar-injection design. Re-derive its T+1-pair table and add QMX's own test fixtures before trusting it for real swap/rollover accounting — it is a good specification from an unvetted source, not a dependency.

---

## Files referenced

- `C:/Users/Mubarak/Desktop/QMX/reference/repos/exchange_calendars/exchange_calendars/exchange_calendar.py`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/exchange_calendars/exchange_calendars/always_open.py`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/exchange_calendars/exchange_calendars/weekday_calendar.py`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/exchange_calendars/exchange_calendars/calendar_helpers.py`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/exchange_calendars/README.md`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/exchange_calendars/LICENSE`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/pandas_market_calendars/pandas_market_calendars/market_calendar.py`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/pandas_market_calendars/pandas_market_calendars/calendars/forex.py`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/pandas_market_calendars/pandas_market_calendars/calendars/cme_globex_fx.py`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/pandas_market_calendars/README.rst`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/pandas_market_calendars/LICENSE`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/pandas_market_calendars/NOTICE`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/fx-value-date/src/index.ts`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/fx-value-date/test/index.test.ts`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/fx-value-date/README.md`
- `C:/Users/Mubarak/Desktop/QMX/reference/repos/fx-value-date/LICENSE`
