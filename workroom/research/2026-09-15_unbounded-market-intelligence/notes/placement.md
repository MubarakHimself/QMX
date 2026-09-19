# Placement & filters — corpus notes

**Pass:** 2026-09-15 unbounded MIS research  
**Family:** sit-out / gate / cooldown / compatibility / execution-quality / skip / invalidation  
**Corpus:** `.worktrees/mql5-library/data/mql5-library/` only  
**Extractions:** `extractions/placement.jsonl`  
**QMX law (do not smuggle):** MIS labels and may veto; MIS does **not** switch playbooks or size; Book door may later use **class activation**; bots own direction. Placement research = *when not to fire / which family is compatible*, not a new entry signal.

Prior 24 (regime/scalp notes) are leads, not re-mined as the quota:  
`17737,23286,22940,16830,15223,23482,23016,10715,23454,21003,14203,19944,9804,23355,22938,22939,15748,19290,18867,1575,21235,16752,9231,22772`.

This pass full-read **40+ new** articles (placement core + stratified Interviews/Examples). See jsonl for per-id rows.

---

## 1. What “placement” means in this corpus

Three different nouns collide under “filter/gate”:

| Sense | Examples | QMX home |
|---|---|---|
| **Admission / sit-out** | news windows, session/DOW, Jardine multi-gate, meta-label p-threshold, RiskGate approve/skip | Book door (+ MIS coordinates) |
| **Compatibility / class** | regime→strategy maps, ADX gate on DI-cross, hysteresis bull/bear oscillators | MIS label → *possible later* Book class activation; **not** MIS-owned playbook switch |
| **DSP / set / ML jargon** | Ehlers Roofing, Bloom filter, “information flow” in nets | Bot preprocessing or irrelevant — rename in docs |

If a source EA **detects a regime then switches trend/MR/breakout and sizes**, that is evidence for *compatibility research* and an **anti-pattern for MIS** (`17781`, `23444`, `22783`).

---

## 2. Method clusters (beyond the prior 24)

### 2.1 Clock & calendar sit-out

- **`3395`** — composable time filters (range, DOW, timer, intraday) + OR sub-filters for discontinuous schedules (skip lunch). Pure engineering of *when features are allowed*.
- **`20037`** — session/hour wrappers + economic calendar block before/after. Note: `InpCalLookAheadMin` is a **news horizon name**, not look-ahead bias.
- **`16380` / `21446` / `21803` / `22231` / `22580` / `17999`** — calendar series: currency×importance×time filters; stop-management inside news; persist windows across terminal restart; static CSV for honest tester; live/CSV fallback.

**QMX cut:** `session_id` / `tod_bucket` / `news_window` as snapshot coordinates; Book owns block/protect. Not SQS.

### 2.2 Secondary filters on a primary signal (meta-label & ML gates)

- **`22274` / `22754` / `22755`** — López de Prado-style meta-label trilogy (RSI, ADX, Bollinger). Secondary outputs **p**; skips if low; **does not flip side**; may size. Hard OOS rhetoric on EURUSD H1.
- **`16487`** — CatBoost→ONNX filter on simple MA-cross; keep backbone dumb.
- **`23700`** — *online* logistic filter updated after each closed trade (shift-1 features only); cold-start useless for ~25–50 trades.
- **`21351`** — Jardine’s Gate: multi-dimensional “should I trade at all?” stack (entropy/structure → expert agreement → confidence…). Explicitly prioritizes sit-out over direction.

**QMX cut:** Side = bot. Admission ≈ Book. Fitted p used for sizing = Book, never MIS. Online updating fights freeze-and-ship — shadow only.

### 2.3 Regime as compatibility (and the forbidden half)

- **`20996`** — compression / transition / expansion / trend-bias from range & CLV; closed-candle non-repaint. Good MIS-shaped *labels without side*.
- **`17781`** — same detector as prior `17737`, then **auto-selects playbooks + regime lots**. Anti-pattern for MIS.
- **`23444`** — Ehlers “two markets, two playbooks” via Even Better Sinewave; excellent closed-bar/IIR-replay hygiene; still a playbook switch.
- **`22783`** — hysteresis channel; different oscillators in bull vs bear; modes for counter-trend allowance.
- **`15033` / `11930` / `15541`** — HMM/Markov as conditioning filters (Nash+HMM writeup thin).

**QMX cut:** Emit state; do not let MIS choose the bot.

### 2.4 Changeover → cooldown

- **`23043` / `23103`** — CUSUM breakpoints on standardized log-returns; author suggests vol-regime gate; z uses **prior W only** (anti-leak); signal after bar close.
- Complements prior **`23482` BOCPD** (risk cooldown overlay).

**QMX cut:** MIS `cp_*` / break sensors; Book owns sit-out duration.

### 2.5 Execution-quality gates (not market-state)

- **`23532`** — execution gateway: lot/stop validation, fill-policy retry, **`success` vs `slippage_rejected` as separate bits**.
- **`21720`** — RiskGate: central approve/size/skip across many EAs (Book/BMS analogue).
- **`9804` / `23355`** (prior scalp pass) remain the spread/SQS cousins — not re-extracted here.

**QMX cut:** QMN/Book/SQS lane. MIS may *carry* SQS inside snapshot; MIS is not the gateway.

### 2.6 Invalidation as state transition

- **`19619`** — SMC orderblocks: violated → mitigation block (reuse), not hard delete.

**QMX cut:** Bot structure; optional KSA invalidation sensor.

### 2.7 “Filter” false friends

- **`23149`** Ehlers DSP library, **`22389`** Bloom filter trailing, **`21279`** ALGLIB-smoothed MA crosses — valuable engineering, easy to mis-file as admission gates.

---

## 3. Contradictions & folklore (high value)

1. **Regime gate always helps?** **`22290`** five-year TECH100 H1 ablation: *regime alone ≈ 0, HTF alone ≈ 0, session did the work*. Contradicts vendor “add a regime filter” pitch and also **`21351`**’s claim that TOD filters are merely arbitrary/brittle.
2. **Sit out after losses?** **`1441`**: history/virtual-trade pause criteria **worsened** results vs unfiltered (one variant higher win-rate, lower profit).
3. **Filter DD improvement = edge?** **`23665`** splits *operational* path effects from *selection ability* via block-permutation placebos. **`22274`**: meta-label cut most trades; P&L barely moved; DD fell mainly from **exposure**.
4. **L1/trend filters as entries?** **`21142`**: L1 often better on **exits/holding**; entry filtering cuts count without proportional quality.
5. **MIS playbook switch?** Corpus loves it (`17781`,`23444`,`22783`); QMX forbids it inside MIS. Treat as compatibility evidence only.
6. **Look-ahead folklore:**
   - Dominant good hygiene: closed bar index 1+, non-repaint timestamp gates (`20996`,`23444`,`23700`,`21142`,`17956`).
   - Explicit ML leakage warnings: **`22755`** (`shift().dropna()`, full-sample “static” features).
   - **`23043`**: exclude current bar from z window.
   - Many placement articles are **silent** on leakage — absence is not safety.
   - Naming trap: calendar `LookAheadMin` (`20037`) ≠ peeking.

---

## 4. Stratified Interviews / Examples (n=10)

| id | section | Placement yield |
|---|---|---|
| 623, 624 | Interviews | Anecdote only; section has only 3 ok articles total |
| 22768 | Interviews | Platform historiography mis-shelved as Interview — cultural why EA-local risk dominates |
| 638, 639, 748, 1341, 1414, 690 | Examples | True negatives (print/UI/DLL/OpenCL/sound) — taxonomy not hiding physics |
| **652** | Examples | **Surprise hit:** multi-symbol shared-params as anti-overfit *validation filter* — Examples shelf hides promotion-bar content |

**Taxonomy lesson:** do not trust section labels for recall. `Examples` contains both zero-signal cookbooks and real robustness methods (`652`) plus major filter papers (`21142`,`22274`,`21720`). Title/body search required.

---

## 5. Practical map into QMX (no production code)

| Want | Prefer from this pass | Avoid smuggling |
|---|---|---|
| Sit-out coordinates | session/TOD, news_window, CUSUM/BOCPD break prob | Direction, lots |
| Compatibility / class activation (Book later) | compression/transition/expansion (`20996`); ADXR gate features (`22754`); vol-first hierarchy (prior `17737`) | Auto playbook switch (`17781`) |
| Filter promotion bar | `23665` selection vs operational; `22290` ablation; `652` multi-symbol sameness | Single with/without backtest |
| Execution quality | `23532` slippage bit-split; RiskGate authority split (`21720`); SQS from prior | Putting spread math in regime model |
| Fitted secondary gates | meta-label pattern with **bot side / Book size** | MIS sizing from p; online SGD as V1 governed producer |

---

## 6. Read set (this pass)

Placement/regime/filter core:  
`3395,1441,15541,16380,16487,17956,19619,20037,21133,21142,21279,21351,21446,21460,21720,21803,22231,22274,22290,22580,22754,22755,23665,23700,17781,20996,22783,23444,15033,23043,23103,23532,23149,22389,11930,20157,20851,17999,23488,23112`

Stratified: `623,624,22768,638,639,690,1341,1414,748,652`

Rare-physics companion reads documented in `notes/rare_and_surprising.md` / `extractions/rare_physics.jsonl`.
