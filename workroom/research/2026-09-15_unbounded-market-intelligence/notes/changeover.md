# Changeover / regime-transition research notes

Date: 2026-09-15  
Corpus: `.worktrees/mql5-library/data/mql5-library/` (sqlite + md only)  
Output: `extractions/changeover.jsonl`  
Constraint: no invented estimators; flag look-ahead; no production code; QMX wants **sit-out / Book filter**, not bot triggers.

## Scope and search

Family: change-point, structural break, regime switch/transition, HMM-as-switch, BOCPD, CUSUM, PELT, jump, Markov-switching, Viterbi/Hamilton, MS-GARCH, run-length.

Prior 24 (leads only, not re-centered):  
17737, 23286, 22940, 16830, 15223, 23482, 23016, 10715, 23454, 21003, 14203, 19944, 9804, 23355, 22938, 22939, 15748, 19290, 18867, 1575, 21235, 16752, 9231, 22772.

Body keyword scan (≥2 strong hits): **105** articles. Title/desc sqlite hits for the family: **11** primary titles. **PELT**: no dedicated hit in corpus. **MS-GARCH**: no dedicated article. **Hamilton filter** as named tool: absent (HMC MCMC 20590 is a false friend).

Fully extracted this pass: **34** records in `changeover.jsonl` (32 new/deep + 2 prior siblings 23482/16830 for linkage). Digests for 40 candidates under `recovery_staging/changeover_digests/`.

## Taxonomy of methods found

| Family | Articles (new-centered) | Online vs offline | Causal decode? | Typical use in article |
| --- | --- | --- | --- | --- |
| Page CUSUM on z-returns | 23043, 23103 | Online sequential | Yes (z from t−1) | Break marks; Part 2 says **vol regime** → pause/resize |
| AFML CSW / SADF / Chow / SMT | 23158, 23159 | Offline or rolling-L | Endpoint causal if windows≤t; Chow often confirmatory | Features + **strategy switch** examples |
| Residual/recursive CUSUM + Chow | 20946 | Recursive online + confirmatory Chow | Recursive can be causal; Chow needs date + post buffer | **Get-out** when pair leash snaps |
| BOCPD run-length | 23482 (prior) | Online | Causal | Monitor / adaptive MA / **risk cooldown** |
| HMM / Viterbi / forward-backward | 15033, 17917, 15541, 16830 (prior), 11930 | Train offline; infer live | **Viterbi batch = smoothed (lookahead)**; MAP/FB smoothed; filtered forward = causal | Mostly **bot filter or trigger**; freeze-and-ship |
| CUSUM as event sampler | 18864, 19850 | Online sampler; labels use future | Sampler causal; triple-barrier labels are future by design | Labeling / meta-label pipelines |
| Regime playbook EA | 17781, 23444, 21833 | Live bar-close | 23444 excellent closed-bar discipline | **TRADE TRIGGER / switch** |
| Vol asymmetry / IV-RV regime | 23677, 22258, 23734 | Rolling / external feed | Causal if lagged | Context / sizing; 23734 notify-on-change |
| L1 breakpoints | 21142 | Window solve | **Two-sided L1 can look ahead inside window** | Breakpoints as regime changes |
| Prophet changepoints | 18549 | Fit-time | In-sample changepoints often hindsight | Weak for MIS |
| Jump model | 10955 | Narrative | n/a | No detector |

## Causal vs smoothed (lookahead flags)

Hard rules distilled from the corpus:

1. **Online stopping rules** (Page CUSUM 23043/23103, BOCPD 23482, CUSUM sampler 18864, frozen-baseline CPD in 21833) are the cleanest causal changeover sensors **if** standardization/windows end at t−1 and decisions use **closed bars**.
2. **Viterbi on a finished sequence** (15033 default, 16830, 17917 `algorithm=viterbi`) is a **global path** — using it to paint historical bars as features is **smoothed / look-ahead**. Live MIS needs **filtered** state probabilities (forward only) or an expanding decode that never sees future bars.
3. **Forward-backward / MAP** (17917) is explicitly **smoothing**. Offline analysis only.
4. **Chow test** (20946, 23158): confirmatory; needs hypothesized break date and **post-break sample** — not an early trigger by itself.
5. **SADF/CSW** (23158/23159): bar-t statistic from past windows can be causal; full-sample supremum Chow location is batch. Rolling L changes meaning to “explosive in last L,” which is what strategy/filter use wants.
6. **L1 trend filter** (21142): piecewise-linear breakpoints are attractive, but a full-window L1 solve is a **two-sided smoother** unless restricted to a trailing causal window.
7. **Triple-barrier / meta labels** (18864, 19850, 22754): labels **must** use the future; never feed label fields into live MIS features. Purge/embargo/uniqueness (19850) are mandatory for any classifier trained on them.

## Trade trigger vs sit-out (QMX cut)

QMX truth (OPERATING_LINE): MIS labels → **Book door + KSA only**. Bots never consume MIS. Classification ≠ edge. No sizing in MIS.

| Article | Article’s own use | QMX-aligned extraction |
| --- | --- | --- |
| 23103 CUSUM P2 | Pause MR / resize / widen stops | **Sit-out / Book cooldown** after vol-break |
| 23482 BOCPD (prior) | Risk cooldown overlay | Same |
| 20946 pairs breaks | “Get out” / stop dead hedge model | Assumption-death sensor |
| 21833 grid CPD | Block new BGT cycle on structural break | **Start-gate / refusal** |
| 23734 gold IV/RV | Notify on regime change; not a signal | Monitor + cooldown |
| 18864 CUSUM filter | Event sampling for ML | Corpus clock, not entry |
| 23158/23159 SADF | Article shows **strategy switch** | Keep stats as **features/filter**; refuse playbook switch in MIS |
| 17781 / 23444 / 15541 | Explicit EA entries / mode switch | **Bot half** — do not wire into MIS |
| 15033/17917/16830 HMM | Filter or trigger | Shadow filter only; causal decode required |

## Strongest transferable mechanisms (for MIS / Book)

1. **Online vol-break sensor (CUSUM Page or BOCPD)**  
   Empirically (23103): Page-CUSUM on standardized returns is a **variance-regime** detector (~47% F-test confirm; ~0.7% mean confirm). Textbook Siegmund ARL₀ is **wrong by ~5×** on real FX/index data — calibrate h empirically. Quiet markets behave closer to theory.  
   → Candidate snapshot fields: `cusum_break`, `bars_since_break`, `s_plus`, `s_minus`, `not_ready`. Book owns cooldown length.

2. **Structural-break feature pack (CSW excess, rolling SADF, SMT)**  
   Continuous explosiveness / drift scores for `regime_classifier_v1` shadow features or Book filters. Bound lookback L; log-prices; `SB_EMPTY`-style not_ready. Do **not** implement the article’s trend/MR/unit-root playbook switch inside MIS.

3. **Assumption-death residual CUSUM** (20946 pattern)  
   Apply recursive residual CUSUM not only to pairs betas but to any fitted producer (e.g. `liquidity_stress_v1` residual vs its training distribution). Chow remains confirmatory offline.

4. **Two-layer gate** (21833)  
   Continuous favorability (σ/μ or vol coordinate) + discrete CPD block. Matches Book admission better than a single classifier score.

5. **HMM filtered posterior** (15033/17917/16830)  
   Freeze-and-ship matrices OK. Prefer filtered P(state|F_t) over batch Viterbi. Remains **unauthoritative** per OPERATING_LINE; shadow only.

6. **Label hygiene** (18864 + 19850)  
   CUSUM event sampling + uniqueness weights + purged/embargoed CV before any changeover-aware LightGBM work.

## Corpus gaps (honest)

- **PELT**: not present as an article implementation.  
- **MS-GARCH / Hamilton filter**: no dedicated MQL5 article; Markov hits are mostly chains/HMM/wizard.  
- **Jump CPD**: 10955 narrative only.  
- **Bai–Perron**: essentially absent.  
- Crypto M1 evidence: almost none in these changeover articles (FX/gold/indices dominate).  
- QMX `regime_classifier_v1` is LightGBM multiclass quiet|normal|elevated|stressed — complementary to, not replaced by, sequential CPD.

## Testable hypotheses (priority)

1. On QMX venues, empirical CUSUM ARL ≪ Siegmund ARL₀; quiet-slice ARL closer to theory (replicate 23103 design).  
2. Book refusal for N bars after CUSUM/BOCPD break reduces scalp DD more than random N-bar pauses (prior BOCPD overlay logic).  
3. Filtered HMM vol-state vs LightGBM class concordance; disagreement rate under stress.  
4. Rolling SADF (causal L) lifts elevated/stressed precision vs ATR/vol_ratio alone.  
5. Uniqueness-weighted + purged CV reduces IS–OOS gap for regime_classifier_v1.  
6. Frozen-baseline CPD (21833 style) catches quiet-trend danger episodes that rolling vol thresholds miss.

## What not to do

- Do not invent PELT/MS-GARCH estimators from outside the corpus.  
- Do not treat Viterbi-colored history as a live causal label.  
- Do not put playbook switching or lot sizing in MIS because 17781/23444/23158 did.  
- Do not trust closed-form ARL₀ for production thresholds.  
- Do not promote recovered Kronos/HMM/BOCPD/MS-GARCH as authoritative — OPERATING_LINE stands; this pass only maps mechanisms and gaps.

## File map

- Extractions: `workroom/research/2026-09-15_unbounded-market-intelligence/extractions/changeover.jsonl`  
- Digests: `.../recovery_staging/changeover_digests/*.txt`  
- Builder: `.../tools/build_changeover_jsonl.py`  
- Prior regime pass: `workroom/research/2026-09-09_mql5-mis-regime-notes.md`
