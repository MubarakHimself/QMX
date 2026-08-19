# 08 — Answer-Keys Catalog: External Truth per QMX Module Family

**Written:** 2026-08-18. **Status:** research finding, NOT adopted (operator ratification pending — Lock 5 was "not ratified, rework grounded in actual QMX components first"; this is that rework).
**Purpose:** for each concrete module family, the EXTERNAL thing that proves agent-built code right — so operator review stops being the throughput ceiling. Backtesting-framework design explicitly excluded (ticket 008); rows only note where a check belongs to it.

---

## Catalog — external truth per QMX module family

**1. Light indicators (bot/strategy tier)**
- *External check:* TA-Lib C core as batch oracle + `talipp` as a second, independently-seeded incremental oracle; TA-Lib's **published stability classification** (Start-Independent / Initial-Unstable / Depends-on-MA-Type / Path-Dependent) and machine-readable `Function(x).lookback` as known-truth fixtures. Every indicator registers a declared class + `warmup_bars`; the harness re-derives `lookback + unstable_period + 1` and refuses a mismatch. Broken specimen for free: Nautilus seeds EMA with the first value, TA-Lib with an SMA of the first *n* — the parity test must *see* that mismatch, proving it isn't asleep.
- *Catches:* research-vs-live drift ("backtest says buy, live says hold" — the single most expensive bug class); half-warm indicators trading; an agent using SAR or AD, where a different start date can flip trend direction for the whole run and never converges.
- *When:* at registration (warm-up arithmetic) + CI (parity, and incremental-replay ≡ batch bit-identical).
- *Source:* `research/03-indicators-analysis.md` §1a, §1b, §11, plain-words 7–8, 14–15.

**2. Market-structure components (swings, BOS/CHoCH, FVG, order blocks, liquidity, zones)**
- *External check:* vendor `smartmoneyconcepts/smc.py` **as a pinned deliberately-broken specimen, never a dependency** — its `swing_highs_lows` uses `shift(-(swing_length // 2))` *and* silently doubles the parameter. QMF's causality test must FAIL it, every time, in CI. Its definitions remain the reference spec (read, don't import).
- *Catches:* an agent re-introducing the same lookahead; a swing published at bar X without `confirmed_at = X+N`; `fvg`'s off-by-one; `MitigatedIndex`/`liquidity` forward scans over the whole remaining series.
- *When:* at registration (blocking precondition) + CI regression against the pinned specimen.
- *Source:* `research/06-forex-domain-components.md` §1.1 (issues #101/#103/#108/#34/#59; measured profit factor 7.32 → 1.82), §2.2; `research/00` Novel-1.

**3. Heavy / MIS models (regime, volatility, correlation, ML inference)**
- *External check:* `statsmodels.MarkovRegression` emits **all three** probability series from one fitted model — `smoothed_*` (look-ahead) and `filtered_*`/`predicted_*` (causal). That is a free known-truth fixture *pair*: the causality test must fail smoothed and pass filtered. Additional must-fail specimens: `pomegranate.predict_proba` (forward-backward), `jumpmodels.predict_online` (docstring claims one-step-ahead; the code is filtered — the test catches the vendor's own doc error).
- *Catches:* a smoothed labeller reaching a live consumer; an agent-authored Confirmation trained on the future; a model whose registry `causality` field lies.
- *When:* CI per registered MIS component + registry refuses `causality: smoothed` at live binding.
- *Source:* `research/08-mis-ml-regime-models.md` §1.3, §2.2 table, §2.3 item 5, §9.

**4. The two-timestamp / causality precondition (spans every family above)**
- *External check:* one `Provenance` type (`event_time` + `available_at`) and one property — `label(bars[0:t])[-1] == label(bars[0:t+n])[t]` — run as a **precondition of registration for every component**, self-tested by the two known-broken specimens in rows 2 and 3.
- *Catches:* any future-peek anywhere, including code an agent writes unattended.
- *When:* at registration (blocking) + CI. Costed at "one afternoon".
- *Source:* `research/00-qmf-synthesis-module-map.md` Novel-1; `research/08` §2.3.5.

**5. Data layer (manifests, splits, sealed holdout)**
- *External check:* (a) **two independent vendors of the same series** — Dukascopy archive vs cTrader trendbars — reconciled against each other; (b) sha256 + row-count + min/max-ts manifest per partition, recorded into every result; (c) `qmf.data.load(split_id=...)` with **no raw-date API** and an access log on the permanently sealed holdout; (d) 1-worker vs N-worker bit-identical determinism run.
- *Catches:* a backfill silently changing a six-month-old number; missing bars read as "no trade" (cTrader creates trendbars only when ticks arrive); an agent reaching the holdout; parallelism leaking into results.
- *When:* continuously at ingestion (manifest + gap detect), at load (split_id only), CI (determinism hash).
- *Source:* `research/02-data-foundation.md` §4.4 item 5, §5, Copy 3–4, Open Q9; `research/09` §12.3 items 6–7.

**6. Venue adapter**
- *External check:* one **conformance suite both `SimBroker` and the cTrader adapter must pass** (Hummingbot `connector/test_support/` pattern) — this is what makes sim≡live structural rather than aspirational; plus a **real cTrader demo account** for what no fixture can supply: the undocumented per-period bar-span table (probe it), the delta-encoded trendbar decode (`open = low + deltaOpen`, timestamp in **minutes**) and the self-contradictory tick-ordering comment, symbol-spec units (volume in cents, `pipPosition`, `digits`, `min/step/maxVolume`), reconciliation after a deliberate process kill, `UNKNOWN` order outcomes on mid-submit disconnect, rejection reason codes, partial fills, `ProtoOASymbolChangedEvent`, token-refresh session invalidation, locally-derived equity vs `GetPositionUnrealizedPnL`.
- *Catches:* OpenApiPy's class-level shared send queue mixing demo/live messages; deferreds silently dropped on disconnect (in-flight orders becoming unknown with no signal); no re-auth/re-subscribe after reconnect; treating UNKNOWN as REJECTED.
- *When:* CI (suite, against sim) + nightly against demo + startup-and-periodic reconcile in production.
- *Source:* `research/05-broker-connectivity.md` §1, §2, §5D, §7 items 4/11/12, Open Q4/Q6; `research/00` Novel-2.

**7. Book / BMS money math**
- *External check:* the **operator's GitBook Book schema is the spec** — the check is schema-conformance against *that* document (extract it to a machine-readable registry first; never assume a variable, never invent a default, and preserve which variables are locked vs editable vs defaulted). Layered on top: venue-reported instrument specs as external truth for pip value and lot rounding, and a **demo round-trip** — submit the computed size and compare the venue's accepted volume / margin / commission against QMF's number.
- *Catches:* a locked variable silently made editable; an agent-invented default; lot-rounding and cross-currency errors (Nautilus's fixed-risk sizer takes `hard_limit`, `unit_batch_size`, `exchange_rate` precisely because naive `risk_pct*equity/stop` misses them).
- *When:* at registration (schema conformance) + against demo (round-trip) + continuously (reconcile).
- *Source:* ticket 002 Session 2026-08-18 ("documented on GitBook — NEVER assume"; "very many variables… very surgical"); `research/04-portfolio-risk-sizing.md` §1.3.

**8. Prop-firm rule engine (inside BMS)**
- *External check:* the **published rulebooks are the oracle** — FTMO anchors to balance at midnight CET, Topstep trails end-of-day balance, Apex trails in real time and counts unrealized profit. One equity path, three different verdicts: known-truth fixtures no one has to invent. Broken specimen: Freqtrade's `MaxDrawdown`, which evaluates only **closed** trades — feed it a floating-loss path and the check must catch it passing when it should breach.
- *Catches:* closed-P&L-only rule engines; wrong-timezone day anchors; drawdown state (peak equity, day anchor) not surviving a VPS restart — LEAN keeps it in memory and re-arms instantly with no cooldown.
- *When:* CI (fixtures) + continuously in production (state persisted; verified at every restart).
- *Source:* `research/04` plain-words 9–13, §Freqtrade Protections.

**9. Kill switch — pair-scoped**
- *External check:* the archived `ff_calendar_thisweek.json` polls (real events, currency codes, impact ratings, timestamps) as the fixture corpus, plus IANA `zoneinfo` for DST. Assertions: a Red USD event blocks USD pairs **only** while EURJPY keeps trading; a global-halt implementation is the deliberately-broken specimen the test must reject; a DST-boundary week must not shift the blackout (smc's `sessions()` issue #46 is the specimen of that failure). Paired continuity assertion: across every kill-switch fire, the recorded paper-trading stream is unbroken.
- *Catches:* over-broad halting (violates the pair-scoping ruling), missed blackouts, DST drift, and a gap in the alpha-decay data series — which needs uninterrupted points by design.
- *When:* CI (fixtures) + continuously in production (paper-record continuity asserted per kill event).
- *Source:* ticket 002 Session 2026-08-18 (pair-scoped news; paper trading as a standing state); `research/10` §5.3; `research/06` §DST/#46.

**10. Overfitting statistics — placed here, NOT designed here**
- The external check exists and is good: `purgedcv` (MIT, source-read, matches the papers; its own doctest `minimum_backtest_length(10) ≈ 2.5`) as a CI oracle for QMF-owned PSR/DSR/MinBTL/CSCV-PBO; and the old spec's overfit-archetype battery (several fake strategies the battery must fail + one known-good control it must pass). **Both belong to ticket 008.** Cited only so the map has no hole: `research/09` §2–3, §6; `reference/04-recovery-comparison.md` A5 and §4 item 12.

---

## Highest payback per unit effort

1. **The single causality property test at registration** (row 4). One afternoon, covers indicators, market structure, MIS and any component an agent writes later, and arrives with two free known-broken specimens (smc swings; smoothed HMM) that prove the test itself works.
2. **Indicator dual-oracle + automatic warm-up arithmetic** (row 1). Uses libraries already installed, kills the most expensive bug class in the system, and converts "is it warm enough?" from hope into a computed number the registration gate can enforce.
3. **One adapter conformance suite run against both SimBroker and a cTrader demo account** (row 6). It is simultaneously the sim≡live guarantee and the only way to learn the venue facts that are not in any document.

## Honest gaps — no external check exists

- **The fill / slippage model.** Nothing external can certify a simulated fill. The only honest oracle is *measured* live slippage (conditioned on session and event proximity) fed back as the model's parameters — which requires the live tick recorder to exist first. **Flagged for ticket 008; deliberately not designed here.**
- **What a "correct" order block or zone *is*.** There is no canonical definition; the reference package's own issues (#61, #76) report divergence from TradingView/LuxAlgo. Causality is checkable, semantics are not — ship these as `evidence_state: hypothesis` and treat the operator's GitBook definition as the only spec.
- **Book/BMS variable semantics, until the GitBook schema is extracted to machine-readable form.** Right now there is a document, not a checkable schema, so check #7 has nothing to conform against. That extraction is the prerequisite, and it is operator-verified work, not an agent guess.
