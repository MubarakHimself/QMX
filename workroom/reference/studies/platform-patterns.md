# Platform Patterns — OpenBB, FinceptTerminal, zvt

**Scope:** OpenBB's provider/adapter architecture and CLI/app split; FinceptTerminal's data-presentation and news-display aesthetics (for QMX's future Rust UI); zvt's data-schema/recorder pattern. Read against `reference/repos/OpenBB`, `reference/repos/FinceptTerminal`, `reference/repos/zvt`, with `research/00-qmf-synthesis-module-map.md` as prior context (Ring 1 `qmf.data.ingest`, Ring 8 `qmf.app`/`qmf.cli`).

---

## In plain words

1. **OpenBB** is a financial-data aggregator: one Python API (`obb.equity.price.historical(...)`) that quietly talks to dozens of paid and free data vendors (FMP, Tiingo, yfinance, FRED, ECB...) and always hands back the same shape of answer, whichever vendor actually answered.
2. It does this with a very small, repeated pattern: for every "thing you can ask for" (a price series, a balance sheet, a news feed) there is one canonical answer-shape, and every vendor gets a small translator that turns the vendor's own reply into that shape. Add a new vendor, write one translator file, done — nothing else in the system changes.
3. It also separates *what the platform can do* (a library, callable from Python) from *how you reach it* (a REST API auto-built from that library, a terminal CLI built on top of the REST API, and a desktop app built on top of the REST API). Three doors, one house.
4. **FinceptTerminal** is a Bloomberg-style desktop terminal, now rewritten as a native C++/Qt6 app. What makes its screens feel expensive is not flashy graphics — it's density done carefully: every colour, font and spacing value comes from one central "theme tokens" table, data rows are hand-drawn pixel-by-pixel rather than dropped into a generic table widget (so a news wire row can pack a time, a priority dot, a source-quality star, a colour stripe and a headline into 26 vertical pixels and still look calm), and the screen is built from stacked fixed-height strips — a command bar, a stats strip, the main content, a scrolling ticker — the same skeleton Bloomberg terminals use.
5. It also has a "linked panels" idea: panels can join a coloured group (red, green, blue...) so that clicking a symbol in one panel updates every other panel in the same group, without them knowing about each other directly.
6. **zvt** is a research framework for Chinese equities/crypto. Its core habit: every data source is a small, resumable "Recorder" that remembers, per entity, the last timestamp it already saved, and only fetches what's new — so re-running the same recorder is always safe and cheap. All the data — regardless of which of nine data vendors produced it — lives under one shared schema per data-kind (an OHLCV table looks the same whether it came from Sina or Eastmoney), so downstream code never needs to know or care where a row came from.
7. None of the three is directly usable as-is for QMX (wrong asset class, wrong licence, or wrong UI stack) — the value here is entirely in the *shape* of how they organise ingestion and presentation, not in any code to reuse.
8. OpenBB and FinceptTerminal are both AGPL-3.0 — copyleft that would force QMX's source open if code from them shipped in QMX. zvt is MIT — permissively licensed, but its code is still not a fit for a forex/crypto framework. Treat all three as design references only.
9. The single most transferable idea across all three, for QMF's ingest layer, is: **one canonical shape per data kind, one thin translator per source, and a registry that both sides discover each other through** — never a fat `if provider == "x"` branch inside business logic.
10. The second most transferable idea, for the future Rust UI, is: **tokenised theme + custom-painted dense rows + fixed-height layout strips + colour-linked panel groups**, not any specific widget library.

---

## How it is built

### OpenBB — provider/adapter architecture

OpenBB Platform (`reference/repos/OpenBB/openbb_platform/`) splits into three trees:

- `core/openbb_core/` — the framework: the `Fetcher` abstract base, the provider `Registry`, the `ProviderInterface`, the `Query` executor, the `OBBject` result wrapper, the FastAPI router, and `static/package_builder.py` which generates the flat `obb.<category>.<command>(...)` Python surface at install time.
- `providers/<name>/` — one package per data vendor (`fmp`, `tiingo`, `yfinance`, `fred`, `ecb`, `cftc`, `sec`, `deribit`, ~30 in total), each containing `openbb_<name>/models/<endpoint>.py` files.
- `extensions/<domain>/` — the command surface grouped by financial domain (`equity`, `crypto`, `economy`, `news`, `technical`...), which is *provider-agnostic*: it only knows about standard models, never about FMP or Tiingo directly.

The adapter unit is the **`Fetcher`** (`openbb_platform/core/openbb_core/provider/abstract/fetcher.py:36`), a three-stage pipeline every provider implements once per endpoint:

```
transform_query(raw_params) -> Q      # provider-specific query object
extract_data(query, credentials)      -> raw vendor payload (sync or async)
transform_data(query, raw_payload)    -> R  (list[ProviderData] mapped onto the standard schema)
```

`fetch_data()` (`fetcher.py:73`) just calls the three stages in order; `Fetcher.test()` (`fetcher.py:116`) asserts the pipeline's contract at CI time — the fetched data must *not* already be typed as the transformed model, and the transformed output *must* subclass both the provider's own data model and the standard data model.

Every endpoint has one **standard model** (`core/openbb_core/provider/standard_models/equity_historical.py:17`) — a Pydantic `QueryParams`/`Data` pair with the canonical field names (`open`, `high`, `low`, `close`, `volume`, `vwap`...) and shared field docstrings from a `*_DESCRIPTIONS` dict. A provider's concrete model *subclasses* the standard model and only adds what's provider-specific:

```python
class FMPEquityHistoricalQueryParams(EquityHistoricalQueryParams):
    __alias_dict__ = {"start_date": "from", "end_date": "to"}   # FMP's own param names
    interval: Literal["1m","5m","15m","30m","1h","4h","1d"] = ...  # FMP-only extra
```
(`providers/fmp/openbb_fmp/models/equity_historical.py:21`)

`__alias_dict__` does the renaming; extra fields the standard schema doesn't define become "extra params" that only *that* provider accepts. Field-level `title` metadata records which providers support a given extra field, so `Query.filter_extra_params()` (`core/openbb_core/app/query.py:36`) can **warn and drop** a parameter silently if the caller picked a provider that doesn't support it, rather than erroring.

Registration is a `Provider` object (`core/openbb_core/provider/abstract/provider.py:6`) per package: `name`, `credentials` (auto-prefixed `fmp_api_key`), and a `fetcher_dict` mapping standard-model name → `Fetcher` subclass. Providers announce themselves via Python entry points (`providers/fmp/pyproject.toml:18`, `[tool.poetry.plugins."openbb_provider_extension"]`) and `RegistryLoader.from_extensions()` (`core/openbb_core/provider/registry.py:34`) discovers every installed provider package at import time — **no central "list of providers" file to edit**; installing the package *is* the registration.

At call time, `Query.execute()` (`app/query.py:66`) merges `standard_params` (shared across all providers) with the filtered provider-specific `extra_params`, then a `QueryExecutor` looks up the right `Fetcher` by `(provider_name, model_name)` and runs it. The result comes back wrapped in `OBBject` (`core/openbb_core/app/model/obbject.py:36`), a single envelope with `.results`, `.extra` (metadata like warnings/`results_metadata`), and `.to_df()/.to_dict()/.to_llm()` converters — so every command, from every provider, returns the same wrapper shape regardless of what's inside.

**CLI/app split** (Ring 8 of the QMX module map, confirmed in the wild): `openbb_platform/core` is a plain importable library. `openbb_platform/core/openbb_core/api/` auto-builds a FastAPI REST surface from the same router definitions the Python package uses (one router tree serves both). `cli/openbb_cli` (a separate Poetry package) is a Rich-based terminal shell that imports the platform library directly. `desktop/` is a Tauri (Rust!) + React app (`desktop/src-tauri/Cargo.toml`, `desktop/src/`) that talks to a locally-hosted instance of the same REST API. Three presentation layers, one command/provider core — none of them contain business logic of their own.

### FinceptTerminal — presentation architecture (native C++/Qt6, `fincept-qt/`)

The public repo is the free AGPL edition of a two-edition product (README, `reference/repos/FinceptTerminal/README.md:1`); Enterprise is closed-source. The rewrite (current) is **not** the old Python/Textual terminal — it's C++20 + Qt6, one native binary, embedded Python only for analytics.

- **Theme tokens** (`fincept-qt/src/ui/theme/ThemeTokens.h:8`): one `ThemeTokens` struct holds *every* colour, font and spacing value for a preset — background layers (`bg_base`→`bg_hover`), border weights, a four-step text hierarchy, an accent colour with a dimmed variant and an "on-accent" text colour, semantic colours (`positive`/`negative`/`warning`/`info`) that mean the same thing in every theme, tinted backgrounds for buy/sell fills, alternating-row colour, and a 6-colour chart palette. The comment on the struct is explicit about the rule: *"no hardcoded hex anywhere else."* Fonts are pinned to `'Consolas','Courier New',monospace` for data (`ThemeManager.cpp:40`) — numbers line up in columns because the font guarantees it, not because of manual padding.
- **Custom-painted dense rows**, not generic table widgets: `NewsFeedDelegate::paint_wire_row()` (`fincept-qt/src/screens/news/NewsFeedDelegate.cpp:52`) hand-draws each 26px-tall news row — background (selected/hovered/alternating), an amber "new" dot with a fading pulse-glow overlay, a 3px monitor-colour stripe, a right-aligned relative-time string in a tiny font, a coloured priority dot, a source-tier glyph (★ tier 1, ● tier 2, · tier 3), then pre-formatted source/language/threat/ticker strings pulled straight off model roles ("zero allocation in paint path" — the comment's own words). This is what makes a wire feed readable at Bloomberg density: every pixel of the row is a deliberate, theme-driven choice, not default widget padding.
- **Fixed-height layout strips**, stacked vertically and documented in the class comment itself (`fincept-qt/src/screens/news/NewsScreen.h:26`): a 32px command bar (search, category/time/sort/view pills), a 26px "intel strip" (live stats, sentiment, monitor hits, statistical deviations), a flexible content area (full-width feed, with an optional 420px right detail overlay and an optional 280px left intel drawer), and a 22px scrolling ticker strip at the bottom. Every screen in the app reuses this shape.
- **Panel registry with link groups** (`fincept-qt/src/core/panel/PanelRegistry.h:14`): every dockable panel is indexed by instance id, panel type, host frame, *and* a "link group" (e.g. red/green/blue). Selecting a symbol in one panel of a group can be broadcast to every other panel sharing that colour, without either panel importing the other — this is the mechanism behind the "linked panels" you see in real trading terminals, and it's a generic pub/sub registry, not per-screen wiring.
- **Async result staleness guards**: `NewsScreen` keeps `filter_generation_`/`enrichment_generation_` atomics (`NewsScreen.h:129`, `:162`) so a slow async filter or LLM-enrichment call that returns late (after the user has already changed the filter again) is discarded rather than overwriting fresher UI state. Small idea, worth stealing verbatim for any Rust UI that fires async requests from user input.

### zvt — data-schema/recorder pattern

`reference/repos/zvt/src/zvt/contract/`:

- **`Mixin`** (`contract/schema.py:34`) is the base of every SQLAlchemy schema class: `id`, `entity_id`, `timestamp`, plus `register_recorder_cls(provider, recorder_cls)` and `get_providers()`. A single logical table — e.g. daily K-line data for stocks — can be filled by *multiple* recorders from *multiple* providers (Sina, Eastmoney, JoinQuant...), and each schema tracks its own `provider_map_recorder` dict, so `Stock1dKdata.get_providers()` tells you exactly which vendors can fill that table.
- **`TradableEntity`/`Entity`** (`contract/schema.py:333`, `:348`) is the shared identity every time series hangs off — one entity row (a stock, an index, a portfolio) is the join key for every schema type.
- **`Recorder`** (`contract/recorder.py:91`) self-registers at class-definition time via a metaclass (`Meta.__new__`, `recorder.py:71`): defining a `Recorder` subclass with `provider` and `data_schema` set is *itself* the act of registering that provider for that schema — mirrors OpenBB's entry-point discovery but at the language level instead of the packaging level.
- **`EntityEventRecorder`** (`recorder.py:147`) adds entity-list scoping (`exchanges`, `entity_ids`, `codes`) and an `ignore_failed` skip-list built from entities that already have data as of `end_timestamp` — cheap resumability at the entity-selection stage.
- **`TimeSeriesDataRecorder.evaluate_start_end_size_timestamps()`** (`recorder.py:303`) is the resumable-ingestion core: for each entity, look up `get_latest_saved_record()` (the newest row already in the DB for that entity/schema/provider), and only fetch from that watermark forward — re-running a recorder is always an incremental top-up, never a full re-download, and never produces duplicates.
- **`NormalData`** (`contract/normal_data.py:6`) is the presentation-side normalizer: any dataframe gets reshaped to a `(entity_id, timestamp)` MultiIndex, then split into one `DataFrame` per entity in `entity_map_df` — so charts, tables and factor code all consume data in the same entity-first shape regardless of source.

---

## Mental models worth borrowing

1. **Idea: one canonical schema per data-kind, adapters translate into it, never out of it.**
   Where it lives: OpenBB's `standard_models/*.py` + provider subclasses (`core/openbb_core/provider/standard_models/equity_historical.py:17`, `providers/fmp/openbb_fmp/models/equity_historical.py:21`); zvt's `Mixin`-based schemas shared across recorders (`contract/schema.py:34`).
   Why it matters for QMF: this *is* Ring 1's `qmf.data.ingest` — "one ~40-line adapter per source, each terminates in a schema check" from the synthesis doc. OpenBB proves the pattern scales to dozens of vendors and stays maintainable; zvt proves it scales down to a single-operator research framework.
   How QMF would implement it: a `Bar`/`QuoteTick`/`TradeTick`/`MacroSeries` set of frozen dataclasses in `qmf.model` (already planned); each ingest adapter (Dukascopy, cTrader history, FRED, BIS, ECB, CFTC) implements exactly `fetch_raw(query) -> raw`, `to_model(raw) -> list[Bar|...]`; a `pandera`/pydantic schema check gates every adapter's output before it touches `qmf.data.lake`.

2. **Idea: standard params vs. provider-specific "extra" params, filtered with a warning, not an error.**
   Where it lives: `Query.filter_extra_params()` (`core/openbb_core/app/query.py:36`) — a field the chosen provider doesn't support is dropped with an `OpenBBWarning`, not a hard failure.
   Why it matters for QMF: forex data sources genuinely differ (Dukascopy gives tick data, cTrader gives OHLC bars with different session boundaries, FRED gives monthly releases with vintages) — a rigid one-shape-fits-all query would either break or silently misinterpret vendor-specific knobs.
   How QMF would implement it: `qmf.data.ingest` query objects carry a small `extra: dict` alongside the standard fields; each adapter declares which extra keys it honours; anything else logs a warning and is dropped, exactly the OpenBB pattern — keeps `qmf.data.facts`/`qmf.data.lake` callers ignorant of vendor quirks.

3. **Idea: registration by discovery, not by a central list.**
   Where it lives: OpenBB's Python entry points (`providers/fmp/pyproject.toml:18`, `core/openbb_core/provider/registry.py:34`); zvt's metaclass self-registration (`contract/recorder.py:71`).
   Why it matters for QMF: Ring 8's `qmf.registry` already wants "one discovery function... for components, confluences, models, books" — this is the concrete mechanism. It also matters for an LLM-authoring surface: an agent that writes a new ingest adapter or indicator shouldn't also need to remember to edit some unrelated `__init__.py` list.
   How QMF would implement it: since QMF is a single installable package (not many pip-installed provider packages like OpenBB), the entry-point mechanism is overkill — borrow zvt's simpler form instead: a metaclass or `__init_subclass__` hook on the relevant base classes (`Indicator`, `IngestAdapter`, `Component`) that registers into a module-level registry dict at class-definition time, discovered by importing the package once at startup.

4. **Idea: resumable, per-entity watermark ingestion — re-running a recorder is always a safe incremental top-up.**
   Where it lives: `TimeSeriesDataRecorder.evaluate_start_end_size_timestamps()` (`zvt/src/zvt/contract/recorder.py:303`) plus the entity-level `ignore_failed` skip-list in `EntityEventRecorder.__init__` (`recorder.py:147`).
   Why it matters for QMF: the synthesis doc calls the tick stream and calendar feed things that "cannot be bought back later" and says "every day we do not archive them is a day permanently lost" — that only holds if the archiver is trustworthy to *just re-run* without duplicating or gapping. This is exactly the discipline needed for a solo operator's unattended cron job.
   How QMF would implement it: every `qmf.data.ingest` adapter exposes `latest_saved(symbol) -> Timestamp | None` against the lake's manifest; the ingest runner always fetches from `max(latest_saved, requested_start)` forward, and a re-run with no new data is a fast no-op, not a re-download.

5. **Idea: one wrapper object for every result, self-describing enough to render, export, or feed to an LLM.**
   Where it lives: `OBBject` (`core/openbb_core/app/model/obbject.py:36`) — `.results`, `.extra` metadata, `.to_df()`, `.to_dict()`, `.to_llm()`.
   Why it matters for QMF: the spec ring (`qmf.spec`) already wants "no naked float" returned to an agent; a uniform result envelope with a documented LLM-serialisation path is a smaller, sharper version of the same idea, and it gives the future Rust UI one shape to render regardless of which command produced it.
   How QMF would implement it: a thin `Result[T]` wrapper around every `qmf.metrics`/`qmf.experiment`/analyst-hat output, carrying provenance + a `to_llm()`/`to_json()` pair, so the UI and the agent surface consume the same object.

6. **Idea: theme as one struct of tokens; nothing else in the UI hardcodes a colour, font or spacing value.**
   Where it lives: `ThemeTokens` (`fincept-qt/src/ui/theme/ThemeTokens.h:8`), consumed everywhere via `ui::colors::*()`/`ui::fonts::*` accessors.
   Why it matters for QMF: this is the cheapest, highest-leverage decision for a future Rust UI — get the token contract right once (background layers, text hierarchy, semantic colours, monospace data font, chart palette) and every screen, in both a light/dark and multi-theme sense, stays consistent for free.
   How QMF would implement it: a Rust `struct ThemeTokens` (or equivalent design-token file consumed by whatever UI toolkit is chosen — egui/iced/Tauri), mirroring Fincept's field list almost 1:1: bg layers, border weights, 4-step text hierarchy, accent+dim+on-accent, positive/negative/warning/info semantics, row-alt, monospace data font, N-colour chart palette.

7. **Idea: custom-paint dense data rows instead of generic table widgets, driven entirely by pre-formatted model fields ("zero allocation in paint path").**
   Where it lives: `NewsFeedDelegate::paint_wire_row()` (`fincept-qt/src/screens/news/NewsFeedDelegate.cpp:52`).
   Why it matters for QMF: this is *the* mechanism behind the Bloomberg-terminal look Mubarak likes — dense, calm, information-per-pixel — and it is a layout/paint discipline, not a specific library, so it transfers cleanly to a Rust UI (immediate-mode painting in egui, or a custom `Canvas`/`Paint` component in a retained-mode framework).
   How QMF would implement it: for any list-like view showing many rows of live-updating data (positions, orders, signals, the tick feed), pre-format every string once when the underlying model updates, then paint from those pre-formatted strings — never format-on-paint, never lay out with a generic table/grid widget's default row chrome.

8. **Idea: colour-linked panel groups for cross-panel symbol/context propagation, via a registry rather than direct references.**
   Where it lives: `PanelRegistry::find_by_group()` (`fincept-qt/src/core/panel/PanelRegistry.h:59`), `IGroupLinked` interface referenced in `NewsScreen.h:3`.
   Why it matters for QMF: a future multi-panel research/monitoring UI (charts, order book, news, positions) benefits from the same "click a symbol here, everything in the same colour group updates" idea without panels needing to know about each other.
   How QMF would implement it: a small pub/sub `LinkGroup` registry in the Rust UI shell; each panel declares an optional group id at creation and publishes/subscribes to a `SymbolChanged` event scoped to that group.

9. **Idea: stale-async-result guards via monotonic generation counters.**
   Where it lives: `filter_generation_`/`enrichment_generation_` atomics in `NewsScreen.h:129,162`.
   Why it matters for QMF: any UI or agent surface that fires an async fetch (a chart re-query, an LLM enrichment call, a re-run of an experiment) needs to discard a late-arriving response after a newer request superseded it — silent UI corruption otherwise.
   How QMF would implement it: every async request in the Rust UI (and in `qmf.experiment`'s ask/tell loop, arguably) carries a monotonic generation id from its issuing context; the handler compares against the current generation before applying its result.

---

## What to avoid

- **OpenBB's provider-agnostic layer still leaks vendor quirks through `__alias_dict__` and per-field `title` metadata strings used as a provider-list hack** (`fetcher.py` docstrings; `query.py:50`, `providers.split(",")` parsed out of a Pydantic field's `title`). It works, but it is a stringly-typed side-channel bolted onto a docs field — QMF should carry the provider-support list as an actual typed attribute on the extra-param spec, not smuggle it through a description string.
- **OpenBB's `Fetcher.test()` classmethod (`fetcher.py:116`) makes live network calls as its "test"** — there's no fixture/replay layer separating unit tests from hitting real vendor APIs with real credentials. For QMF's ingest adapters, tests must run against recorded fixtures (the same discipline the synthesis doc already assumes for backtest replay); never make CI depend on live broker/vendor availability.
- **FinceptTerminal's free tier is explicitly the stripped edition of a commercial product** (README: "Two editions run on one data core... AGPL copyleft won't apply [in Enterprise]"). The AGPL repo is a marketing/community funnel for a $99–299/user/month SaaS, not a project optimised for being forked and extended by outsiders — expect the public repo's roadmap and code quality to trail the private Enterprise build. Do not assume feature parity with what the screenshots imply.
- **zvt's `Recorder.run()` loop is unbounded sequential polling with a hardcoded `sleep()` between entities** (`contract/recorder.py:133`, `:136`) — fine for a research tool pulling from free Chinese-market APIs at low volume, wrong shape for QMF's forex tick/bar ingestion which needs proper backoff, rate-limit awareness per venue, and concurrency, not a single-threaded sleep loop.
- **None of the three model bitemporal/point-in-time data.** OpenBB's `OBBject` and zvt's `Mixin.timestamp` both carry a single "when it happened" timestamp with no "when we could have known it" field — reusing either schema idea verbatim would silently reintroduce the look-ahead risk the synthesis doc spent an entire finding warning about (`Provenance`, ring 0). Any schema borrowed from these three must have `ts_event`/`ts_init` (or `known_at`) bolted on before it enters QMF.
- **AGPL-3.0 (OpenBB, FinceptTerminal) means network-use copyleft.** Since QMF's Ring 6 runtime and Ring 8 app both talk to a network (broker, VPS, possibly a future hosted dashboard), *any* code — not just a whole file, even a non-trivial adapted snippet — copied from either repo into QMX would obligate offering QMX's complete corresponding source to every user who interacts with it over a network, including a solo operator's own remote VPS process. Treat both as read-only design references; write QMF's ingest adapters and UI from scratch against the mental models above.

---

## Licence & maturity

| Repo | Licence | Maturity signal | Verdict |
|---|---|---|---|
| **OpenBB** (`OpenBB-finance/OpenBB`) | AGPL-3.0 (confirmed in `reference/repos/OpenBB/LICENSE`) | ~72k GitHub stars, 6,800+ commits on `develop`, dozens of open issues/PRs, active `develop` branch, `openbb_platform/core` at package version `1.6.13` | Actively maintained, design-study only (AGPL + wrong asset class for QMX's forex-first scope). |
| **FinceptTerminal** (`Fincept-Corporation/FinceptTerminal`) | AGPL-3.0 (confirmed in `reference/repos/FinceptTerminal/LICENSE`, dual-edition model per README) | `updates.json` shows a current shipped release v4.4.0 across Windows/Linux/macOS installers, "one release a month" cadence stated in README, active native C++20/Qt6 rewrite in progress (`docs/datahub-phases`, `docs/agentic-research`) | Actively maintained, commercial-funnel open-source edition; design-study only (AGPL). Read for UI/aesthetic patterns, not for code. |
| **zvt** (`zvtvz/zvt`) | MIT (confirmed in `reference/repos/zvt/LICENSE`) | ~4.3k GitHub stars, 887 commits on `master`, package version `0.13.5` in `setup.py`, recent-looking features (REST API + standalone UI, QMT data source) referenced in-repo | Actively maintained, MIT — permissively licensed, but Chinese-equities/crypto-focused schema and recorder code is not a drop-in fit for QMF's forex domain. Borrow the recorder/watermark and schema-registration *mental models*, not the code. |

All three: **design-study only**, per the assignment's licence policy — nothing here should be code-transplanted into QMX.