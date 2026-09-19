# Microstructure family notes (unbounded pass)

**Date:** 2026-09-15  
**Corpus:** `C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/` (on-disk md only)  
**Output:** `extractions/microstructure.jsonl` + this file  
**Scope:** spread, liquidity, order-flow proxies, DOM, tick, VWAP, imbalance, VPIN, execution quality  
**Not production code.** Read-only on git.

## QMX seams (do not blur)

- **SQS** = Spread Quality Sensor: **spread RATIO vs session baseline**, **block-only**. Do **not** dump ATR/ADX/HMM/range into SQS.
- **MIS** = snapshot labelers to Book door + KSA only. Never sizes, never owns entries.
- **Book** owns doors / fast invalidation / hysteresis.
- **Bot** owns direction, pullbacks, slicers, BE managers.

Preserve venue: **NQ futures DOM ≠ spot FX book ≠ crypto-spot L2**. **Tick volume ≠ traded volume**.

## Prior already fully read (do not count as new)

Regime miner A: 17737, 23286, **22940**, 16830, 15223, 23482, 23016, 10715, 23454, 21003, 14203, 19944.  
Scalp miner B: **9804, 23355, 22938, 22939, 15748, 19290**, 18867, 1575, 21235, 16752, 9231, **22772**.

High-value prior microstructure already in those notes: Kelly bid/ask (9804), adaptive spread percentiles (23355), Brown Parts 5–7 (noise / VPIN-OHLC / regime), Santos DOM I (15748), tick VWAP+imbalance (19290), exec-noise gate (22772).

## This pass — FULL-READ count

**45 new articles** beyond the prior 24 (see jsonl). Clusters:

| Cluster | IDs |
|---|---|
| Brown Parts 1–4, 8 | 22263, 22553, 22598, 22638, 23372 |
| DoEasy tick → DOM | 8818, 8912, 8952, 8988, 9010, 9044, 9095 |
| Classic DOM UI | 1179, 1793, 3336 |
| Quoted-spread / exec cost | 18821, 20371, 22998, 23299, 23755 |
| “Spread” naming collisions (pairs/seasonal) | 2739, 14035, 15622 |
| VWAP / execution algos | 17934, 22963, 22990, 16984 |
| Activity / imbalance / footprint | 22063, 21825, 21829, 21984 |
| Tick infra / tester | 2612, 11106, 11113, 23465, 22460, 18680 |
| Liquidity *proxies* (VP / round / heat) | 20327, 23550, 22342, 18661, 21876 |
| Noise theory / negative examples | 8136, 15895, 20287 |

---

## Evidence-level legend

| Level | Meaning |
|---|---|
| **L1** | Method/plumbing description only; no useful empirical claim for QMX |
| **L2** | Method + named venue demo or qualitative claim; weak/short sample or confound |
| **L3** | Method + quantified results **and** stated limitations usable as sitting fuel |

No L4 (multi-venue OOS transfer) found in this family this pass.

---

## Lookahead / leakage patterns to watch

| Pattern | Where seen | QMX rule |
|---|---|---|
| Full-sample percentiles / hour probabilities fit then reused in-sample | Brown Parts 4–7 empirics; 18821 hour bias cells | Freeze thresholds offline; tag `not_ready` until warm; never claim OOS from article |
| Session-level regime confidence applied to all bars in session | 23372 adaptive threshold | Prefer bar-causal gates; session aggregates leak if used before session close |
| Session volume profile / VWAP using full-day realized volume mid-day | 17934 VWAP slicer risk; VP articles | Expanding-window only; no hindsight session volume |
| Passive fill slip measured on quote *after* `OnTradeTransaction` | 22998 | Diagnostic only — not a live pre-trade gate |
| SMC swing confirmation on footprint overlays | 21984 | Unconfirmed pivots stay out of MIS |
| Tester OHLC / synthetic ticks vs real ticks | 2612 | Scalp/microstructure claims require real-tick path |
| Simulated `BookEvent` on custom symbols | 11106/11113; prior 15748 | Sim ≠ venue evidence |

---

## Cluster findings

### 1. Brown microstructure series (complete the stack)

Prior had Parts **5–7**. This pass closes **1–4 and 8**.

- **Part 1 (22263):** defensive foundation for NQ M1 — shared structs already anticipate OrderFlow / TimeAware / fractal fields. Broker `GMT_OFFSET_HOURS=2` is a footgun.
- **Part 2 (22553):** three Hurst estimators, confidence blend. **133 NQ M1 Globex sessions**: pooled H≈0.511, rolling≈0.48. **Author null result:** H does not forecast intraday trend. Session reset mandatory (pre/post-open mix is structural break).
- **Part 3 (22598):** GPH `d`; pooled d≈0 on **US100** M1 (72 sessions). Fractional differencing would fit noise.
- **Part 4 (22638):** switches to **NQ futures proper** (514 sessions) and **explicitly denounces US100 CFD as order-flow proxy**. MFDFA Δα, clustering, GJR leverage proxy, bipower jumps (mean 1.4%, P90 2.1%). Stress → *lower* clustering. **Venue lesson is load-bearing.**
- **Part 8 (23372):** micro-trend composite uses **tick volume as activity proxy** (author says so). Regime-coherent with Part 7 without being handed the label.

**SQS note:** Brown’s Part 5 “quoted spread *proxy* from range” (prior 22938) **conflates spread with directional range** — do not launder into SQS. SQS stays bid/ask vs session baseline.

**VPIN note:** Part 6 (prior 22939) OHLC-VPIN is a **proxy**, weak 0.45–0.62 on NQ M1 — never ship as PIN.

### 2. DoEasy DOM + tick stack (8818→9095)

Pure **L1 library**. Value for QMX:

1. Tick object stores **Ask−Bid spread** even when Last/volume are zero (typical FX).
2. DOM subscribe/unsubscribe lifecycle on the symbol object (8988).
3. Snapshot → series → collection (9010/9044/9095) is the right shape **if and only if** `BOOKDEPTH>0`.

Still true (prior Santos 15748): **do not build a system solely on the book**; tester has no native BookEvent.

### 3. Classic DOM UI (1179, 1793, 3336)

MOEX futures demos (1179 SBRF). Kirichenko correctly notes **ECN FX aggregator DOM ≠ exchange book**. Sokolov CMarketBook + scalping DOM sync Last to Ask/Bid — UI/execution aid, not a labeler.

### 4. Quoted spread & execution quality (the SQS-adjacent gold)

| ID | Keep | Reject for SQS |
|---|---|---|
| **22998** | Probe vs passive slip; p95 tails; entry/exit asymmetry; honest “quoted ≠ effective spread” | Using passive post-fill quote as live gate |
| **23299** | Offline cushion / PF-at-cost robustness | Constant slip as live MIS |
| **20371** | Multi-symbol spread router / disable-on-spike | **`spread/ATR` ratio** — mixes cost with range/vol |
| **18821** | Hour-of-day *coordinate* idea | Promotional hour “edges”; word “spread” also means pair spread |
| **23755** | Reminder stops die by spread | Bot BE utility only |

**QMX SQS stays:** live spread ÷ session-window baseline (as in prior 9804/23355 spirit), block-only. **20371’s ATR normalization is explicitly not SQS.**

### 5. Naming collisions: “spread” that is not bid/ask

- **2739** MOEX Si/RTS **residual** spread (pairs). Real futures venue — still **not SQS**.
- **14035 / 15622** seasonal **inter-symbol** spreads.

Tag these `spread_vs_range_conflation` / naming-collision in jsonl so later agents do not pollute SQS.

### 6. VWAP family

- **22963 / 22990:** solid session/anchored VWAP engines; tick volume admitted as proxy.
- **17934:** TWAP / VWAP / Iceberg taxonomy useful as **Book/bot execution policy**, not MIS. Promo backtest numbers ignored.
- **16984:** Python bridge VWAP — prefer in-process (cf. prior 19290 tick VWAP).

VWAP = fair-value **coordinate**. Promote to SQS **block** only by explicit later decision.

### 7. Imbalance bars & footprint (OF proxies without DOM)

- **22063 (L3):** AFML activity/imbalance bars; documents zero-tick phantoms, EWM persistence, Python/MQL5 parity. Best sampling paper in this pass.
- **21825→21984:** tick footprint / diagonal imbalance. Proxy OF when DOM missing. **Not** Lee-Ready aggressor tape. Structure overlay (21984) is lookahead-risky.

Prior **19290** already covers short-window tick imbalance + VWAP — this pass extends the sampling theory and footprint UI.

### 8. “Liquidity” overload

Most titles mean **volume-at-price**, **round-number psychology**, or **synthetic liquidation guesses** — not L2.

- **23550:** honest — no OI/liq feed; leverage-based estimates only.
- **21876:** round-number **locations** → optional **SQS blocks**, not MIS OF.
- **20327 / 22342 / 18661:** VP / time heatmaps — coordinates or blocks, never DOM.

### 9. Tick truth & noise theory

- **2612 (L3):** same EA, three tester modes → **opposite economic conclusions**. Microstructure work that only OHLC-tests is fiction.
- **8136:** clock bars inject noise; motivates tick/activity bars (bridges to 22063).
- **15895 / 20287:** **negative examples** — “orderflow” / “microstructure” in the title, TA or BS greeks in the body.

---

## MIS / SQS / Book placement map (this pass only)

### Eligible MIS sensors (venue-tagged, versioned)

| Working name | Source IDs | Notes |
|---|---|---|
| `spread_obs` / slip stats | 22998 (+ prior 9804/23355) | Quoted spread & fill quality — **not** ATR |
| `hurst` / `arfima_d` | 22553, 22598 | Near-RW on NQ; null predictive claim kept |
| `mfd_fa_width`, `jump_intensity`, `clustering` | 22638 | Futures provenance |
| `micro_trend_strength` (unsigned) | 23372 | Sign → bot |
| `session_vwap` / `anchored_vwap` | 22963, 22990 (+ prior 19290) | Tick-vol proxy labelled |
| `activity_bar_clock` / `imbalance_bar` | 22063 | Feature sampling |
| `footprint_delta_proxy` | 21825 | Proxy tag mandatory |
| `book_available`, `dom_depth_n` | DoEasy + 1179 + prior 15748 | Emit only if depth real |

### SQS-only (blocks / locations)

Round-number levels (21876); VP nodes (20327/22342); DOM resting clusters **if** real book; **not** residual pairs spreads; **not** ATR-scaled spread.

### Book-only

Exec door on slip/spread regime (22998); multi-symbol disable router policy (20371 without ATR-in-SQS); fast invalidation; TWAP/Iceberg policy (17934).

### Bot-only

Signed micro-trend, VWAP pullback EA, footprint entry rules, BE manager, pairs residual trades, seasonal spread EAs.

---

## Transfer rules (reaffirmed)

1. Tag every metric with **venue class**: `futures_nq`, `moex_futures`, `fx_retail`, `cfd_index`, `crypto_spot`, `unspecified`.
2. Never promote CEX liquidation heatmaps or funding into spot-FX facts (23550 is the cautionary tale).
3. FX “volume” in footprint/VWAP articles is usually **tick volume**.
4. Word **spread** has ≥3 meanings in this corpus (bid/ask, inter-symbol residual, range/ATR). SQS uses meaning #1 only.
5. Brown NQ percentiles are **not** portable thresholds.

---

## Leftovers (not full-read this pass; high signal)

- Brown Parts **9–12** if/when fetched (series announced in Part 1; catalog may lag).
- Order Book Part **II+** (only Part I = 15748 present in inventory).
- DoEasy post-65 DOM analytics articles if any beyond Signals detour.
- Deeper read of 21954 CPCV tick-level evidence (ML family overlap).
- 20455 Python-MT5 bars/ticks overload (tester semantics).

---

## Sources

Local paths only under  
`C:/Users/Mubarak/Desktop/QMX/.worktrees/mql5-library/data/mql5-library/md/{id}.md`  
for every ID listed in `extractions/microstructure.jsonl`.  
Prior briefs: `workroom/research/2026-09-09_mql5-mis-regime-notes.md`, `workroom/research/2026-09-09_mql5-mis-scalp-notes.md`.  
Operating line: `workroom/research/2026-09-15_unbounded-market-intelligence/OPERATING_LINE.md`.
