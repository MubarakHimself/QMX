# QMF Prior Art: MIS — ML, Regime Models, Registry and Drift

**Research date:** 2026-08-17
**Area:** What the Market Intelligence Subsystem (MIS) should be built from — regime detection families and their Python implementations, the look-ahead trap that poisons most of them, online vs batch learning, gradient boosting on a trading VPS, feature stores, model registry/lifecycle for a one-person shop, drift detection, and whether any open trading framework already ships an ML subsystem worth copying.
**Method:** primary sources only (upstream repos read as source code where a claim is decision-critical, official docs, PyPI JSON metadata, GitHub API as of 2026-08-17, and the actual papers). Every load-bearing claim carries an inline URL. Anything I could not confirm against a primary source is tagged **UNVERIFIED**.

---

## In plain words

1. The MIS's job is to answer one question every bar: *what kind of market is this right now?* Quiet or violent, trending or chopping, normal or broken. Books and bots read that answer; the BMS reads it to decide whether to let anyone trade at all.
2. There are five real families of tool for this, and they are not interchangeable. Hidden Markov / Markov-switching models (a small number of hidden "states" that price flips between), statistical **jump models** (same idea but with a penalty that stops the label flickering), **change-point detection** (find the exact bars where the world changed), **GARCH** volatility models (forecast tomorrow's volatility, not just measure yesterday's), and plain **clustering** (k-means on a handful of engineered numbers).
3. There is one trap that matters more than every other finding in this file. Most of these tools, when you ask them "what regime was bar *t* in?", answer using bars that came **after** *t*. That is called *smoothing*. It makes the chart look beautiful and the backtest look brilliant, and it is completely fake — live, those future bars do not exist yet.
4. I read the actual source code of the main libraries to pin this down, not the documentation. In `hmmlearn`, both `predict()` and `predict_proba()` are contaminated — `predict_proba` in particular looks like an innocent per-bar probability and is not. Someone else hit exactly this and filed [hmmlearn issue #579](https://github.com/hmmlearn/hmmlearn/issues/579) in January 2026; it is still open and unfixed.
5. The one exception I verified from the C source: the **last row** of `hmmlearn`'s output is clean, because there are no future bars past the end. So the safe live recipe is "ask about the newest bar only, never about history."
6. `statsmodels` is better behaved: it hands you three clearly separated answers — *predicted* (uses data up to yesterday), *filtered* (up to today), *smoothed* (uses the future). Two of the three are safe. Almost every tutorial online plots the third one.
7. `jumpmodels` is the newest family and the only library I found that ships an explicitly online method (`predict_online`) alongside the cheating one — but it is a 163-star academic package that has not been touched since January 2025.
8. Does regime detection actually make money in forex? Honest answer: **not as a direction predictor.** Engel (1994) fitted Markov-switching to eighteen currencies and it did not beat a coin flip on forecast error. It was slightly better at calling *direction*, and Dueker & Neely (2007) found it earns modestly when blended with ordinary technical rules. The 2026 evidence is about **volatility state**, not direction. So: use regime as a **risk filter — a reason not to trade** — which is exactly the prop-firm job the operator described.
9. On learning: there are two shapes. "Learn continuously from every new bar" (the `river` library) or "train quarterly in the cloud, freeze the result, ship the frozen file to the VPS." QMX's accord already leans to the second and I agree with it — a model that quietly retrains itself on a live VPS is a model you cannot reproduce, cannot roll back, and cannot explain after a loss.
10. If QMF does ship a machine-learning predictor, it should be **LightGBM** and nothing else. Concrete numbers: LightGBM's Windows wheel is 1.4 MB with three dependencies. XGBoost on Linux drags in a 252 MB NVIDIA CUDA library you will never use. CatBoost is a 100 MB download that installs a charting stack on your trading server.
11. LightGBM also saves models as **plain readable text**, not a pickle. That matters: a pickle can silently break when you upgrade a library; a text file cannot.
12. For "keeping track of which model is which", MLflow is the standard answer and it is lighter than its reputation — as of MLflow 3 it defaults to a single SQLite file, no server process, and it runs on Windows. But it is twenty dependencies to solve a problem that a versioned folder plus a JSON manifest also solves. I present both; the operator decides.
13. The single most copyable idea in the whole survey comes from Freqtrade's **FreqAI**: every prediction it publishes carries a companion flag saying *trust this / this input looks nothing like what I trained on / this model is past its expiry date*. That flag is exactly what the BMS needs. Freqtrade is GPL-3.0, so QMF may copy the idea and must not copy the code.
14. FreqAI also shows what to avoid: it has **no purge or embargo** anywhere in its data pipeline (I grepped the source), and it lets a user turn on random train/test shuffling from a config file — which silently destroys the whole experiment. QMF must make that mistake impossible rather than merely discouraged.
15. NautilusTrader's roadmap explicitly puts built-in AI/ML tooling **out of scope**. That is the right call for a general engine and the wrong call for QMX, because QMX *is* the operator's whole business and the MIS is a named subsystem — but it is the right instinct about *depth*: QMF should own the thin contract (what a model is, how it registers, what it publishes, how it expires) and borrow the maths from libraries.

---

## Findings

### 1. Regime detection — the five families, what each actually outputs

#### 1.1 Summary of the families

| Family | Representative library | Output | Online-capable? | Fitted state persistable? |
|---|---|---|---|---|
| Hidden Markov Model | `hmmlearn` | state probabilities + hard label | **Only via a QMF-written forward step** (see §2.1) | Yes — plain numpy arrays |
| Markov-switching regression | `statsmodels.tsa.regime_switching` | 3 separate probability series (predicted / filtered / smoothed) | **Yes** — `predicted` and `filtered` are causal by construction | Yes — a float parameter vector |
| Statistical jump model | `jumpmodels` | state probabilities + hard label | **Yes** — dedicated `predict_online` / `predict_proba_online` | Yes — `centers_`, `transmat_` numpy arrays |
| Change-point detection | `ruptures` (offline), `bayesian_changepoint_detection` (online BOCPD) | list of breakpoint indices / run-length posterior | `ruptures` **no**; BOCPD **yes** | `ruptures` has no fitted state to persist |
| Volatility model | `arch` (GARCH family) | conditional variance series + h-step variance forecast | **Yes** — the variance recursion is causal | Yes — `fix(params)` re-applies a saved parameter vector |
| Clustering / unsupervised labels | `scikit-learn` KMeans / GaussianMixture | cluster id + (GMM) membership probability | **Yes** — `predict` is per-row, memoryless | Yes — `cluster_centers_` / `means_`, `covariances_` |

#### 1.2 `hmmlearn` — the standard HMM, and a maintenance problem

- Repo <https://github.com/hmmlearn/hmmlearn>, BSD-3-Clause, 3,413 stars. GitHub API `pushed_at` = **2024-10-31**; latest PyPI release **0.3.3, 2024-10-31** (<https://pypi.org/pypi/hmmlearn/json>).
- **This is ~22 months without a commit as of 2026-08-17.** It is not archived, and issues are still being filed against it (newest open issues dated 2026-06-29, 2026-06-28, 2026-01-08 per GitHub API), but nobody is landing them. Treat as **effectively dormant**.
- Wheel is tiny: 0.1 MB Windows / 0.2 MB Linux; deps are only `numpy`, `scipy`, `scikit-learn`.
- Fitted state on `GaussianHMM` is documented as plain arrays — `startprob_` (n_components,), `transmat_` (n_components, n_components), `means_` (n_components, n_features), `covars_` (<https://github.com/hmmlearn/hmmlearn/blob/main/src/hmmlearn/hmm.py>, lines 170–179). **This means a fitted hmmlearn model serialises losslessly to JSON or `.npz` with no pickle.** That is the single best property it has, and it is what makes "freeze in the cloud, ship to the VPS" trivial for HMMs.

#### 1.3 `statsmodels.tsa.regime_switching` — the best-behaved of the lot

- `MarkovRegression` and `MarkovAutoregression` live in <https://github.com/statsmodels/statsmodels/blob/main/statsmodels/tsa/regime_switching/markov_switching.py>. statsmodels 0.14.6 (PyPI 2025-12-05), repo `pushed_at` 2026-08-17, BSD-3-Clause, 11,580 stars — **healthy**.
- The results object exposes **three distinct probability series**, which is the cleanest look-ahead API in the whole survey:
  - `predicted_marginal_probabilities` — P(state_t | data up to t−1). One-step-ahead. Strictly causal.
  - `filtered_marginal_probabilities` — P(state_t | data up to t). Hamilton filter. Causal.
  - `smoothed_marginal_probabilities` — P(state_t | **all** data through T). Kim smoother. **Look-ahead.**
  Source: `HamiltonFilterResults.__init__` sets the first two (lines ~1793–1798); `KimSmootherResults` adds the smoothed pair (lines ~1866–1878).
- It also exposes `expected_durations` = `1 / (1 - diag(regime_transition))` (lines ~1825–1843) — i.e. how many bars a regime is expected to last. That is directly consumable as a *confidence-in-persistence* number for the BMS.
- **Critically, `MarkovSwitching.filter(params)` runs the Hamilton filter with a caller-supplied frozen parameter vector** and returns only filtered/predicted outputs — no smoothing (source lines 884–950). This is exactly the ship-a-frozen-artifact pattern: fit quarterly, persist `res.params` (a short float vector), and at inference construct `MarkovRegression(new_data, ...).filter(saved_params)`.
- Caveat: `.filter()` recomputes the whole filter over whatever window you hand it — O(T·K²), not incremental. For a live bar QMF should keep its own one-step Hamilton recursion (O(K²)) seeded from the saved transition matrix. Cheap to write, ~20 lines.

#### 1.4 `jumpmodels` — the newest family, and the only one shipping an explicit online method

- Repo <https://github.com/Yizhan-Oliver-Shu/jump-models>, **Apache-2.0**, 163 stars, `pushed_at` **2025-01-12**. PyPI `jumpmodels` 0.1.1, **2024-10-04**. Deps: numpy, pandas, scipy, scikit-learn, matplotlib.
- Implements the discrete jump model (JM), continuous JM, and **sparse** JM with feature selection. The distinguishing idea versus an HMM: instead of a transition-probability matrix, a *jump penalty* Λ is added to the objective every time the state changes, so the fitted label sequence is persistent by construction rather than by luck.
- API is scikit-learn shaped: `fit`, `predict`, `predict_proba`, **plus** `predict_online` and `predict_proba_online`.
- **Source-verified mechanism** (<https://github.com/Yizhan-Oliver-Shu/jump-models/blob/master/jumpmodels/jump.py>): the `dp()` function builds a forward value matrix `values[t] = loss_mx[t] + (values[t-1][:, None] + penalty_mx).min(axis=0)`. With `return_value_mx=True` it returns that matrix *without* the backward traceback; `predict_proba_online` then takes `value_mx.argmin(axis=1)` per row. `predict_proba` instead runs the full DP including the backward traceback loop `for t in range(n_s-1, 0, -1): assign[t-1] = (values[t-1] + penalty_mx[:, assign[t]]).argmin()`. **So `predict_online` is causal and `predict` is not.**
- **A source-level doc correction:** the `predict_online` docstring says the prediction "is based only on data **prior to** that row". The code uses `values[t]`, which *includes* `loss_mx[t]`. So it is a **filtered** estimate (uses data up to *and including* t), not a one-step-ahead prediction. This matters if QMF wants to trade on the same bar the label refers to.
- Fitted state is `centers_`, `transmat_`, `jump_penalty_mx`, `feat_weights` — all plain arrays, so JSON/npz-serialisable.
- **Maintenance risk is real:** one academic author, ~19 months since last push, no release since Oct 2024. Because it is Apache-2.0 and the algorithmic core is ~100 lines of dynamic programming, **vendoring or reimplementing it inside QMF is a legitimate option** and removes the abandonment risk entirely.
- Backing papers: Shu, Yu & Mulvey, *Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach* — <https://arxiv.org/abs/2402.05272>, published in *Journal of Asset Management* (<https://link.springer.com/article/10.1057/s41260-024-00376-x>). **Note for FX relevance: the empirical work is on US, German and Japanese equity indices, 1990–2023. No currencies.**

#### 1.5 Change-point detection — `ruptures` is offline, full stop

- <https://github.com/deepcharles/ruptures>, BSD-2-Clause, 2,071 stars, `pushed_at` 2026-07-06, PyPI 1.1.10 (2025-09-10). **Healthy.** Deps: numpy, scipy only.
- The documentation states plainly it is "a Python library for **off-line** change point detection" (<https://centre-borelli.github.io/ruptures-docs/>). Search methods: `Pelt`, `Binseg`, `BottomUp`, `Window`, `Dynp`, `KernelCPD`. There is **no online detector**.
- What that means for QMX: `ruptures` returns breakpoint indices computed with knowledge of the whole series. Feeding those labels into a backtest is a guaranteed poisoned result. It is a **research-only** tool — legitimate for "where did the regime change historically, so I can inspect it", illegitimate as a live signal or a backtest feature.
- **Online alternative:** `hildensia/bayesian_changepoint_detection` (MIT, 772 stars) implements Adams & MacKay BOCPD in `online_likelihoods.py` alongside offline Fearnhead in `offline_likelihoods.py`. `pushed_at` 2025-11-06.
- **Trap, verified:** the GitHub master was rewritten onto **PyTorch 2.0+** (README badge and `import torch` at the top of `online_likelihoods.py`), while the PyPI package `bayesian-changepoint-detection` is still at **0.2.dev1, uploaded 2019-08-12**. The repo's own README tells you to run `uv pip install bayesian-changepoint-detection`, **which installs the 2019 code, not the code in the repo.** Anyone following the README gets a different library than they read about. Do not depend on this package; if BOCPD is wanted, implement the recursion (it is ~40 lines) or vendor the file under its MIT licence.

#### 1.6 `arch` — GARCH, and what it gives beyond ATR percentiles

- <https://github.com/bashtage/arch>, 1,551 stars, `pushed_at` 2026-08-10, PyPI **8.0.0 (2025-10-21)**. **Healthy.**
- **Licence needs a note.** GitHub reports `NOASSERTION`; PyPI `license_expression` says `NCSA`. Reading the actual file (<https://raw.githubusercontent.com/bashtage/arch/main/LICENSE.md>) it is the University of Illinois/NCSA Open Source License — an MIT/BSD-3 hybrid: unrestricted use, copy, modify, sublicense **and sell**, subject to notice retention and a no-endorsement clause. **Permissive and commercially safe**, but it is not one of the three licences QMF's checklist recognises by name, so it is worth the operator ticking it off explicitly.
- Models: GARCH, ARCH, EGARCH, FIGARCH, APARCH, HARCH; mean models Constant/Zero/AR/ARX/HAR/HARX; distributions Normal, Student-t, skew-t, GED (<https://bashtage.github.io/arch/univariate/introduction.html>).
- **What it gives you over an ATR percentile:** an ATR percentile tells you what volatility *has been*. GARCH gives you a **forecast** of conditional variance at horizon h, with the mean-reversion of volatility built in. `forecast()` returns an `ARCHModelForecast` with `.mean`, `.variance`, `.residual_variance`, columns `h.1 … h.N`, and the docs state "analytical forecasts are always available for the 1-step ahead forecast due to the structure of ARCH-type models" (<https://bashtage.github.io/arch/univariate/forecasting.html>). For a prop-firm daily-loss-cap decision, "expected volatility over the next N bars" is a materially better input than "volatility over the last N bars".
- **Look-ahead status: clean by construction.** The conditional-variance recursion σ²_t = ω + α·ε²_{t−1} + β·σ²_{t−1} only reads the past. The *only* leakage vector is parameter estimation — fitting ω, α, β on the whole sample and then reporting in-sample conditional volatility as if it were live.
- **Frozen-artifact support is first class.** `ARCHModel.fix(params, first_obs=None, last_obs=None)` returns an `ARCHModelFixedResult` computed with a caller-supplied parameter vector; its docstring notes "Parameters are not checked against model-specific constraints" (source lines 528–556 of <https://github.com/bashtage/arch/blob/main/arch/univariate/base.py>). So: fit quarterly → persist a 4-to-6-float vector → at inference `arch_model(live_series).fix(saved)` → read `.conditional_volatility[-1]` and `.forecast()`. No pickle.
- `arch` pulls `statsmodels` as a dependency, so adopting one brings the other.

#### 1.7 Clustering — scikit-learn KMeans / GaussianMixture

- scikit-learn **1.9.0**, PyPI 2026-06-02, `license_expression` BSD-3-Clause, `requires_python >= 3.11`. Wheels ~8.2 MB Windows / 9.1 MB Linux.
- `KMeans.predict(X)` and `GaussianMixture.predict_proba(X)` are **per-row and memoryless** — they carry no temporal state, so they cannot leak across time. This makes clustering the *only* family in this table that is look-ahead-safe by default.
- The leakage moves elsewhere and is easy to miss: it moves into **feature scaling** (fitting a `StandardScaler` on the whole history, including the test period) and into **cluster fitting** (fitting centroids on data that includes the evaluation window). Both are QMF's problem, not sklearn's.
- The honest trade-off: clustering has no notion of persistence, so labels flicker bar-to-bar. That is precisely the problem jump models were invented to fix. If QMF starts with k-means, it will need its own hysteresis/dwell-time layer — which is roughly reinventing the jump penalty.

---

### 2. The look-ahead trap — the highest-value answer in this file

**The rule in one line:** a regime labeller is safe for live trading and for backtesting *only if* the label at bar *t* is a function of bars ≤ *t*. Anything that runs a **backward pass** — Viterbi traceback, forward-backward smoothing, Kim smoothing, offline segmentation — violates this.

#### 2.1 `hmmlearn` — API-level evidence, read from source

I read <https://github.com/hmmlearn/hmmlearn/blob/main/src/hmmlearn/base.py> and the C extension <https://github.com/hmmlearn/hmmlearn/blob/main/ext/_hmmc.cpp>. The call graph is:

| Public call | Internal path | Uses future bars? |
|---|---|---|
| `predict(X)` | → `decode(X)` → `_decode_viterbi` → `_hmmc.viterbi(...)` over the whole array | **YES** — Viterbi is a global MAP path; the backward traceback rewrites earlier labels |
| `decode(X, algorithm="map")` | → `_decode_map` → `score_samples` → forward **and** backward → `argmax` | **YES** |
| `predict_proba(X)` | → `score_samples(X)` → `_score_log`/`_score_scaling` with `compute_posteriors=True` | **YES** |
| `score_samples(X)` | → `forward_log` **and** `backward_log`, then `_compute_posteriors_log(fwd, bwd)` | **YES** |
| `score(X)` | → `_score(..., compute_posteriors=False)` → `forward_log` only, returns scalar | No — but returns no state either |

The decisive lines. In `_score_log` (base.py ~line 253):

```python
log_probij, fwdlattice = _hmmc.forward_log(self.startprob_, self.transmat_, log_frameprob)
if compute_posteriors:
    bwdlattice = _hmmc.backward_log(self.startprob_, self.transmat_, log_frameprob)
    sub_posteriors.append(self._compute_posteriors_log(fwdlattice, bwdlattice))
```

and `_compute_posteriors_log` (~line 513) is literally `log_gamma = fwdlattice + bwdlattice`.

**So `predict_proba` is the smoothed posterior γ_t = P(state_t | x_1 … x_T), not the filtered one.** This is the trap, because `predict_proba` *looks* like a per-row probability and is the single most common thing people put into a feature matrix.

**Independent corroboration:** [hmmlearn issue #579](https://github.com/hmmlearn/hmmlearn/issues/579), opened 2026-01-08, still open:

> "Since the output of `predict_proba` combines forward backward probabilities for the entire sequence, the probability at timestamp `t` includes lookahead bias from observations `X_t+1 ... X_n`. This is not suitable for prediction tasks that mimic realtime behavior… It would be great to support a parameter `mask_future=True`."

Given the repo has had no commits since 2024-10-31, **do not expect this to be fixed.**

**The one clean row — verified from the C source.** `backward_log` initialises the last row to zero:

```cpp
for (auto i = 0; i < nc; ++i) { bwd(ns - 1, i) = 0; }
```

Since log-space zero is a multiplicative identity, `log_gamma[T-1] = fwd[T-1] + 0`. **The final row of `predict_proba` is exactly the normalised forward (filtered) posterior P(state_T | x_1 … x_T).** All other rows are contaminated.

**Therefore there are exactly three legal ways to use `hmmlearn` live in QMF:**

- **(a) Expanding-window last row.** `model.predict_proba(X[:t+1])[-1]`. Correct, uses only the public API, but costs O(t·K²) per bar and grows unbounded. Acceptable for a daily-bar MIS, wasteful for M1.
- **(b) Private forward call.** `_hmmc.forward_log(model.startprob_, model.transmat_, model._compute_log_likelihood(X))` and normalise row t. Correct and O(T·K²) once, but depends on a private C symbol in a dormant package.
- **(c) QMF owns the recursion — recommended.** Export `startprob_`, `transmat_`, `means_`, `covars_` to JSON, and implement the one-step forward update in QMF: `α_t ∝ (α_{t-1} @ A) ⊙ b_t`, ~15 lines, O(K²) per bar, exact, no runtime dependency on hmmlearn at all. hmmlearn is then a *training-time-only* dependency that never ships to the VPS.

#### 2.2 The others, classified

| Library / call | Filtered (live-safe) | Smoothed (backtest-poisoning) |
|---|---|---|
| `hmmlearn.predict` | — | **Yes (Viterbi)** |
| `hmmlearn.predict_proba` | Last row only | **Yes for all other rows** |
| `statsmodels` `predicted_marginal_probabilities` | **Safe** (info through t−1) | — |
| `statsmodels` `filtered_marginal_probabilities` | **Safe** (info through t) | — |
| `statsmodels` `smoothed_marginal_probabilities` | — | **Yes (Kim smoother)** |
| `jumpmodels.predict_online` / `predict_proba_online` | **Safe** (forward DP value matrix, no traceback) | — |
| `jumpmodels.predict` / `predict_proba` | — | **Yes (DP with backward traceback)** |
| `pomegranate` `predict` / `predict_proba` | — | **Yes** — `predict_log_proba` calls `self.forward_backward(...)` (source below) |
| `pomegranate` `forward(X)` | **Safe** — public method, returns the forward lattice | — |
| `ruptures` (all search methods) | — | **Yes — offline by design** |
| BOCPD run-length posterior | **Safe** — sequential by construction | — |
| `arch` conditional variance / `forecast` | **Safe** — causal recursion | Parameter *estimation* is the only leak |
| sklearn `KMeans.predict` / `GaussianMixture.predict_proba` | **Safe** — memoryless per row | Scaler/centroid fitting is the only leak |

`pomegranate` evidence: <https://github.com/jmschrei/pomegranate/blob/master/pomegranate/hmm/_base.py> — `predict_log_proba` body is `_, r, _, _, _ = self.forward_backward(X, priors=priors); return r`, and `predict_proba` is `torch.exp(self.predict_log_proba(...))`. Its docstring says so openly: "These probabilities are calculated using the forward-backward algorithm."

#### 2.3 The standard discipline

The literature-standard, and what QMF should enforce mechanically:

1. **Fit only on a closed past window.** Parameters θ used to label bar *t* must have been estimated from data ending at or before *t* minus an embargo.
2. **Purge and embargo the boundary.** If the target label spans *k* bars forward (a common regime-model setup is "label = realised volatility over next k bars"), the last *k* rows of the training window overlap the evaluation window and must be dropped, plus an embargo gap after. QMF's file 03 already established `sklearn.model_selection.TimeSeriesSplit`, `skfolio`'s `WalkForward` and `CombinatorialPurgedCV` as the available implementations.
3. **Infer forward only.** After fitting, never re-run the labeller over history with the new parameters and store the result. Store the *live sequence of labels as they were produced*.
4. **Log the vintage.** Every published regime label carries `(model_id, model_version, fitted_through_timestamp, inference_timestamp)`. Without this you cannot later prove a backtest was honest.
5. **A machine-checkable invariant QMF can actually enforce:** for the same model artifact, `label(bars[0:t])[-1]` must equal `label(bars[0:t+n])[t]` for all n. Run this as a unit test on every regime component. Every smoothed labeller fails it immediately; every filtered one passes. **This single property test is worth more than all the documentation warnings in this file**, because it is the only defence that survives an LLM agent writing a new Confirmation component at 3am.

---

### 3. Does regime detection help in FX? The honest answer

**Short version: there is no credible published evidence that regime models predict FX direction. There is reasonable evidence they help as risk filters and as blend components. Recommend as a risk filter; do not sell it as alpha.**

#### 3.1 The foundational negative result

Engel, Charles (1994), "Can the Markov switching model forecast exchange rates?", *Journal of International Economics* 36(1–2), 151–165 (<https://ideas.repec.org/a/eee/inecon/v36y1994i1-2p151-165.html>; NBER working-paper version <https://www.nber.org/papers/w4210>). Abstract, verbatim:

> "A Markov-switching model is fit for eighteen exchange rates at quarterly and monthly frequencies. This model fits well in-sample at the quarterly frequency for many exchange rates. By the mean-squared-error or mean-absolute-error criterion, the Markov model does not generate superior forecasts at a random walk or at the forward rate. There appears to be some evidence that the forecast of the Markov model are superior at predicting the direction of change of the exchange rate."

Read that carefully: **fits well in-sample, does not beat a random walk out-of-sample on error, maybe helps on direction.** That is the canonical shape of this whole literature and it has not fundamentally changed in thirty years.

#### 3.2 The most trading-relevant positive result

Dueker, Michael & Neely, Christopher J. (2007), "Can Markov switching models predict excess foreign exchange returns?", *Journal of Banking & Finance* 31(2), 279–296 (<https://ideas.repec.org/a/eee/jbfina/v31y2007i2p279-296.html>). Abstract, verbatim:

> "This paper merges the literature on technical trading rules with the literature on Markov switching to develop economically useful trading rules. The Markov models' out-of sample, excess returns modestly exceed those of standard technical rules and are profitable over the most recent subsample. A portfolio of Markov and standard technical rules outperforms either set individually, on a risk-adjusted basis. The Markov rules' high excess returns contrast with mixed performance on statistical tests of forecast accuracy."

Three things QMX should take from this: (i) the gain is **modest**, not transformative; (ii) the gain shows up in **trading returns** while **statistical forecast tests are mixed** — i.e. the model is not really "predicting", it is reshaping the return distribution; (iii) the best result is the **combination** of Markov rules with ordinary technical rules, which maps precisely onto QMX's Level + Trigger + **Confirmation** structure. A regime probability belongs as a *weighted Confirmation*, not as a Trigger.

#### 3.3 Volatility/session state — where the evidence is better

- Chaudhary, Jayesh (2026), "Multi-Scale Markov Switching GARCH", <https://arxiv.org/abs/2606.06190>, submitted 2026-06-04. Abstract: "This paper proposes a triple-timeframe Markov-Switching GARCH (MS-GARCH) framework for volatility regime detection in EUR/USD across daily, four-hour, and hourly horizons." Reports "superior volatility forecasting performance relative to conventional GARCH benchmarks" and statistically distinct Calm / Turbulent / Crisis regimes, EUR/USD 2015–2025.
  **Caveats the operator must weigh:** this is a **single-author arXiv preprint, not peer-reviewed**, dated two months before this research. It forecasts **volatility**, not direction. Treat as suggestive, not established.
- The jump-model evidence (Shu, Yu & Mulvey, *Journal of Asset Management* 2024, <https://arxiv.org/abs/2402.05272>) reports reduced volatility and reduced maximum drawdown versus both an HMM strategy and buy-and-hold — i.e. **the benefit is on the risk side**, and again **the tested assets are equity indices, not currencies**.

#### 3.4 Verdict

- **Directional prediction in FX from regime models: no reliable evidence found.** Say so plainly.
- **Volatility-state / risk-gating in FX: modest, defensible evidence**, mostly through the GARCH and MS-GARCH line, plus the general asset-allocation drawdown-reduction results.
- **Blending with existing rules: the one clearly positive trading-level FX result** (Dueker & Neely 2007).
- For QMX's stated purpose — prop-firm daily loss caps and trailing drawdown, "knowing when *not* to trade" — the evidence base **supports** building the MIS. It does not support letting the MIS generate entries.

---

### 4. Online / incremental learning — `river`, and why QMF should not build for it first

#### 4.1 `river`

- <https://github.com/online-ml/river>, **BSD-3-Clause**, 5,917 stars, `pushed_at` 2026-08-12. PyPI **0.25.0, 2026-05-31**; release cadence 0.22 (2024-11) → 0.23 (2025-11) → 0.24 (2026-04) → 0.25 (2026-05). **Actively maintained.**
- Origin, from the README: "River is the result of a merger between **creme** and **scikit-multiflow**." The old `creme` package on PyPI is frozen at **0.6.1, 2020-06-10** — dead, do not install it.
- Wheels are small: 1.4 MB Windows / 1.5 MB Linux. Core deps `scipy`, `numpy`, `altair`. Requires Python ≥ 3.11.
- API is `learn_one(x, y)` / `predict_one(x)` on plain Python dicts. The docs are explicit that "vectorization doesn't bring any speed-up" in this setting (<https://riverml.xyz/latest/introduction/basic-concepts/>).
- Modules include `drift` (ADWIN, PageHinkley, KSWIN, plus binary-target DDM/EDDM/FHDDM/HDDM-A/HDDM-W), `forest` (ARFClassifier, AMFClassifier), `linear_model`, `preprocessing`, `time_series` (<https://riverml.xyz/latest/api/overview/>).

#### 4.2 The serialisation problem — this is the decisive point

River's own FAQ (<https://riverml.xyz/latest/faq/>) offers exactly one persistence mechanism:

```python
from river import ensemble
import pickle
model = ensemble.ARFClassifier()
with open('model.pkl', 'wb') as f: pickle.dump(model, f)
with open('model.pkl', 'rb') as f: model = pickle.load(f)
```

with the note: "We also encourage you to try out dill and cloudpickle."

**A pickle of a live-learning model is the worst possible artifact for QMX's shape.** It is:
- **version-fragile** — a `pip install --upgrade river` on the VPS can make an existing pickle unloadable, and there is no schema to migrate;
- **unreproducible** — the model's state is the integral of every bar it has ever seen, in the order it saw them, including the ones during the outage;
- **unrollback-able** — "roll back to last week's model" is meaningless when the model has been mutating continuously;
- **unauditable after a loss** — you cannot answer "what did the model believe on Tuesday" unless you snapshotted Tuesday.

#### 4.3 Batch-fit / live-infer vs online learning — the recommendation

| | Batch-fit, frozen artifact | Online learning (`river`) |
|---|---|---|
| Reproducible | Yes — same data + seed → same artifact | No — path-dependent on the live stream |
| Rollbackable | Yes — pin a previous version id | Not meaningfully |
| Shadow-rollout compatible | **Yes, naturally** — run v_new beside v_old on the same inputs | Awkward — the two copies diverge by construction |
| Auditable after a drawdown | Yes — the artifact is immutable | Only if you snapshot every bar |
| Adapts to a shifting market | Only at retrain | Continuously |
| Artifact | JSON/npz/text, tiny | pickle, version-fragile |
| VPS footprint | ~0 (numpy) or 1.4 MB (LightGBM) | 1.4 MB + pickle risk |

**QMF should build for batch-fit / live-infer first, and it is not close.** Every property QMX has already committed to — quarterly cloud training, shadow rollout, promotion, rollback, a BMS that can halt a Book — assumes an *immutable, identifiable, comparable* model. Online learning destroys all four.

**Where `river` still earns a place:** as a **drift detector**, not a learner. `river.drift.ADWIN` maintains a small bucket structure over a stream of scalars and flips `drift_detected` (<https://riverml.xyz/latest/api/drift/ADWIN/>, constructor `delta=0.002, clock=32, max_buckets=5, min_window_length=5, grace_period=10`, method `update(x)`, attributes `drift_detected`, `estimation`, `n_detections`, `width`). That is a legitimate small addition to the VPS — 1.4 MB, three deps, BSD-3 — and it is the *watchdog* on the frozen model, not a replacement for it. See §8.

---

### 5. Gradient boosting and classical supervised ML on the trading VPS

#### 5.1 Footprint — measured from PyPI file metadata, 2026-08-17

| Package | Version | Windows wheel | Linux wheel | Core deps | Licence |
|---|---|---|---|---|---|
| **lightgbm** | 4.7.0 (2026-07-18) | **1.4 MB** | **3.5 MB** | `narwhals`, `numpy`, `scipy` | MIT |
| xgboost | 3.4.1 (2026-08-15) | 48.9 MB | 57.6 MB | `numpy`, `scipy`, **`nvidia-nccl-cu13; platform_system == "Linux"`** | Apache-2.0 |
| catboost | 1.2.10 (2026-02-18) | 100.2 MB | 97.2 MB | `graphviz`, `matplotlib`, `numpy`, `pandas`, `scipy`, `plotly`, `six` | Apache-2.0 |
| scikit-learn | 1.9.0 (2026-06-02) | 8.3 MB | 9.3 MB | numpy, scipy, joblib, threadpoolctl | BSD-3-Clause |
| onnxruntime | 1.28.0 (2026-07-25) | 13.8 MB | 19.2 MB | `flatbuffers`, `numpy`, `packaging`, `protobuf` | MIT |

**The XGBoost finding is decisive for a Linux VPS.** `xgboost` 3.4.1 declares `nvidia-nccl-cu13` unconditionally on Linux. That wheel is **252.4 MB** (`nvidia_nccl_cu13-2.31.2-py3-none-manylinux_2_18_x86_64.whl`, <https://pypi.org/pypi/nvidia-nccl-cu13/json>). So `pip install xgboost` on the trading VPS costs roughly **310 MB** to obtain a CPU tree predictor. Additionally xgboost 3.4.1 declares `requires_python >= 3.12`.

**CatBoost installs a charting stack on the trading server** — `matplotlib`, `plotly`, `graphviz`. That is 100 MB and a set of dependencies with no business being on a machine whose only job is to place orders.

**No compiler toolchain is needed for any of them** on Windows or Linux x86-64 — all three ship prebuilt wheels for CPython 3.10–3.14. The historical "you need a C++ compiler for LightGBM on Windows" pain is gone.

#### 5.2 Minimal inference-only footprint — options ranked

**Option A (recommended): LightGBM's native text model.** `Booster.save_model(filename, num_iteration=None, start_iteration=0, importance_type='split')` writes a **text-based** model file; `lgb.Booster(model_file=path)` reloads it, and `Booster.model_to_string()` / `model_from_string()` do the same in memory (<https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.Booster.html>).

Why this is the right answer for QMX:
- The artifact is **human-readable text** — diffable in git, inspectable by the operator, and by an LLM agent.
- It is **not a pickle**, so it does not carry arbitrary code and does not break on a library upgrade the way a pickled sklearn estimator does.
- Inference needs only the 1.4 MB `lightgbm` wheel and numpy — the training stack (pandas, optuna, whatever) never reaches the VPS.
- `save_model(num_iteration=None)` defaults to saving the **best** iteration if early stopping found one, which is the behaviour you want and the one people forget to ask for.

**Option B: ONNX Runtime.** `onnxruntime` 1.28.0 (MIT), 13.8 MB Windows / 19.2 MB Linux, four small deps. Conversion via `onnxmltools` 1.16.0 (Apache-2.0, `pushed_at` 2026-08-01) for LightGBM/XGBoost or `skl2onnx` 1.20.0 (Apache-2.0, `pushed_at` 2026-08-07) for scikit-learn pipelines. Both are alive.
- **Worth it if and only if** QMF wants *one* inference runtime for heterogeneous model types (a tree model, a logistic regression, a small neural net) with a single loader and a single latency profile. That is a real architectural benefit for an MIS that will host several model families.
- **Cost:** an extra conversion step that can silently change numerics, and 14–19 MB. For a single LightGBM model it is pure overhead.

**Option C: compile to source.** `treelite` 4.7.0 (Apache-2.0, `pushed_at` 2026-08-12) — alive, but v4 moved the runtime out into TL2cgen, adding a build step. `m2cgen` (MIT, 2,996 stars) converts models to dependency-free code in many languages — but PyPI 0.10.0 dates from **2022-04-26** and the repo's last push was **2024-08-03**. **`m2cgen` is dormant; do not adopt.**

#### 5.3 Inference latency

**UNVERIFIED.** I did not benchmark, and I found no primary-source latency figure I would stand behind for LightGBM single-row prediction. What is safe to say without a measurement: a single-row `Booster.predict` on a few-hundred-tree model is well under a millisecond in every published account, and it is not the bottleneck next to a cTrader protobuf round-trip. **If latency is decision-critical, measure it on the actual VPS with the actual model — do not take a number from a blog.**

---

### 6. Feature engineering and feature stores

#### 6.1 `tsfresh`

- <https://github.com/blue-yonder/tsfresh>, MIT, 9,291 stars, `pushed_at` 2026-07-06, PyPI **0.21.2 (2026-05-31)**. **Alive.**
- Extracts ~800 statistical features per series and provides hypothesis-test-based feature *selection*.
- Its forecasting story is `roll_time_series` (<https://tsfresh.readthedocs.io/en/latest/text/forecasting.html>): "Rolling is a way to turn a single time series into multiple time series, each of them ending one (or n) time step later than the one before." Parameters `max_timeshift` ("The extracted time series will have at maximum length of max_timeshift + 1") and `min_timeshift` ("Shorter time series (usually at the beginning) will be omitted").
- **What it enforces vs what it leaves to you:** `roll_time_series` *mechanically* guarantees each feature row is computed from a window ending at its own timestamp — that is real and valuable. It does **not** align your target, does not purge or embargo, and does not stop you from fitting a scaler across the whole rolled matrix afterwards. And 12 dependencies including `stumpy`, `pywavelets`, `cloudpickle`, `tqdm` make it a research-environment package, never a VPS one.

#### 6.2 `tsfel`

- <https://github.com/fraunhoferportugal/tsfel>, BSD-3-Clause, 1,098 stars, `pushed_at` 2026-01-30, PyPI **0.2.0 (2025-08-20)**. Slower cadence than tsfresh but not dead.
- Smaller and simpler than tsfresh — a curated statistical/temporal/spectral feature catalogue driven by a JSON config. Deps include `ipython` and `setuptools`, which is sloppy for a library.
- Honest assessment: **neither tsfresh nor tsfel is a good fit for QMX.** They are built for the "I have thousands of short labelled segments and want a big feature matrix" problem. QMX has one long stream per pair, needs the *same* features live and in research, and has already committed (file 03) to defining indicators once in incremental form. Bolting on an 800-feature batch extractor breaks that principle. **Use them for one-off exploratory research only, if at all.**

#### 6.3 Feature stores — `feast`

- <https://github.com/feast-dev/feast>, Apache-2.0, 7,212 stars, `pushed_at` 2026-08-16, PyPI **0.65.0 (2026-07-20)**. **Alive and busy** (402 open issues).
- **But: 30 core dependencies**, including `fastapi`, `uvicorn`, `dask[dataframe]`, `SQLAlchemy[mypy]`, `prometheus_client`, `gunicorn`, `pyarrow`, `pydantic`, `bigtree`, `pyjwt`. This is a service, not a library.
- The point-in-time mechanism is real: `get_historical_features()` takes an *entity dataframe* whose timestamps represent "the events at which we want to reproduce the state of the world", and scans backward from each row's timestamp up to the feature view's TTL. The docs stress that "the TTL time is relative to each timestamp within the entity dataframe. TTL is not relative to the current point in time (when you run the query)" (<https://docs.feast.dev/getting-started/concepts/point-in-time-joins>).
- **What Feast enforces vs what it leaves to you — the critical distinction.** Feast joins as-of the `timestamp_field` you declared on the data source. It has a separate `created_timestamp_column` (present in `sdk/python/feast/infra/offline_stores/offline_utils.py`), but that is used for **deduplication/tie-breaking**, with as-of filtering on it gated behind an opt-in `filter_by_created_timestamp` flag. **So if your source rows carry the event time but the value was not actually knowable until later — a revised economic release, a late-corrected bar, a restated calendar entry — Feast will happily join a value you could not have had.** Point-in-time correctness is only as good as the timestamps you declared. The tool provides the join; it does not provide the truth.
- **Verdict for QMX: do not adopt Feast.** Thirty dependencies and a service to run, to solve a problem that for a single-operator system with Hive-partitioned Parquet is solved by (a) storing an explicit `available_at` column alongside `event_time` on anything that can be revised, and (b) an as-of query in DuckDB — which file 02 already established as the storage layer. QMF should own the invariant, not import a platform.

**The point-in-time rule QMF must adopt regardless of tooling:** every feature row records both the timestamp it *describes* and the timestamp it was *knowable at*. Backtests filter on the second. Anything without a knowable-at timestamp is assumed knowable only at the close of the next bar.

---

### 7. Model registry, versioning and lifecycle for a one-person shop

#### 7.1 MLflow — what it actually costs

- <https://github.com/mlflow/mlflow>, 27,541 stars, `pushed_at` 2026-08-17, PyPI **3.15.1 (2026-08-03)**. **Very much alive.**
- **Licence:** the PyPI `license` field literally reads "Copyright 2018 Databricks, Inc. All rights reserved." which reads alarmingly, but the actual `LICENSE.txt` is the **Apache License 2.0** with that line as a copyright header (<https://raw.githubusercontent.com/mlflow/mlflow/master/LICENSE.txt>). Permissive. Fine.
- **Windows: supported.** Its dependency list contains `gunicorn<27; platform_system != "Windows"` and `waitress<4; platform_system == "Windows"` — i.e. the project explicitly ships a Windows WSGI server. That is direct evidence of intentional Windows support for the tracking server.
- **Weight:** `mlflow` wheel is 11.2 MB with **20 core dependencies** (Flask, Flask-CORS, alembic, SQLAlchemy, graphene, docker, cryptography, matplotlib, pyarrow, scikit-learn, scipy, skops, huey, aiohttp, plus `mlflow-skinny` and `mlflow-tracing`). `mlflow-skinny` alone is 3.6 MB and is the client-only variant.
- **The 2025/2026 change that matters.** Per the official deprecation notice, [mlflow issue #18534](https://github.com/mlflow/mlflow/issues/18534) (opened 2025-10-27, still open):
  > "The filesystem backend (e.g., `tracking_uri='./mlruns'`) is deprecated. The database backend (e.g., `tracking_uri='sqlite:///mlruns.db'`) will be the new default."
  and, for URI resolution: "**New users**: If no existing mlruns data is found, MLflow uses `sqlite:///mlflow.db`."
- **So the honest cost of self-hosted MLflow for one person in 2026 is:** one SQLite file, one artifact directory on disk, **no long-running server process required** for logging or for the registry, and a `mlflow ui` process started on demand when the operator wants to look. That is much cheaper than MLflow's reputation. The Model Registry does require a database-backed store — but SQLite counts, so this is satisfied by default now.
- **Against it:** 20 dependencies and a slow import to solve a problem that, at the scale of "one operator, a handful of models, four retrains a year", is a directory and a JSON file. MLflow's value is *experiment tracking across hundreds of runs*, which is a research-environment need, not a VPS need.

#### 7.2 DVC — note the governance change

- The repo `iterative/dvc` **now redirects to `treeverse/dvc`**. lakeFS (Treeverse) acquired the DVC open-source project from Iterative.ai, announced 2025-11-18 (<https://dvc.org/blog/dvc-joins-lakefs-your-questions-answered/>, <https://lakefs.io/media-mentions/lakefs-acquires-dvc-uniting-data-version-control-pioneers/>). Still Apache-2.0, 15,822 stars, `pushed_at` 2026-08-17.
- **But the release cadence slowed:** PyPI 3.67.1 dates from **2026-03-31** — 4.5 months with commits but no release. Not dead; not the same velocity as before the acquisition. **Flag as watch-item, not adopt-item.**
- DVC's actual value proposition is versioning *large datasets* against a remote. QMX's data is already Hive-partitioned Parquet with an IS/OOS split registry (file 02). DVC would be a second, overlapping answer to a solved problem.

#### 7.3 What "registration" must mean for QMX — the design

The operator's question is the right one: *some models are book-specific, what does that imply for registration?* Here is what registration has to carry, derived from the shapes QMX has already committed to (quarterly cloud training, shadow rollout, single Linux VPS, BMS authority, LLM-authored strategies).

**A QMF model registration is a JSON manifest sitting beside the artifact. Minimum fields:**

| Field | Why it exists |
|---|---|
| `model_id` | Stable identity across versions. `mis.regime.volstate.fx_majors` |
| `version` | Monotonic. Rollback target. |
| `scope` | **`global`** or **`book:<book_id>`** — the answer to the operator's question. A book-scoped model is *invisible* to discovery from any other Book. This is an access rule, not a convention. |
| `kind` | `regime` \| `volatility` \| `classifier` \| `regressor`. Determines the output schema the consumer can expect. |
| `output_schema` | Named fields + types + ranges. What a Confirmation can bind to. Machine-readable so an LLM can discover it without reading code. |
| `input_contract` | **Exact ordered feature names** the model consumes, plus the QMF component id that produces each. |
| `causality` | `filtered` \| `predicted` \| `smoothed`. **Anything marked `smoothed` is refused for live binding and permitted only in research.** This is the §2 defence expressed as metadata. |
| `fitted_through` | Last timestamp in the training data. The anchor for staleness. |
| `train_window`, `purge_bars`, `embargo_bars` | Reproducibility and leakage audit. |
| `expires_after` | Duration. Past this, predictions are marked stale (see §7.4). |
| `runtime` | `lightgbm-text` \| `hmm-json` \| `onnx` \| `params-vector`. Tells the loader which of the small set of loaders to use. **No `pickle` value exists.** |
| `artifact_sha256` | Tamper/corruption detection on the VPS. |
| `promotion_state` | `candidate` \| `shadow` \| `live` \| `retired`. |
| `shadow_since` / `promoted_at` | Rollout audit trail. |
| `supersedes` | Previous version id — the rollback pointer. |

**Discovery** is then: scan the model directory, parse manifests, filter by `scope ∈ {global, book:<me>}` and `promotion_state == live`. That is a ~30-line function with no dependencies, it is trivially testable, and it presents exactly the "small, discoverable, machine-readable surface" the mandate requires.

**Book-specific binding falls out for free.** A book-scoped model is registered with `scope: "book:scalping_v2"`. The discovery filter excludes it from every other Book. No central coordination, no naming convention that an agent can accidentally violate, no shared namespace to pollute.

**Shadow rollout falls out too:** promotion is a **manifest edit**, not a file move. `candidate → shadow` starts the new version producing predictions into the prediction log alongside the live one, consuming identical inputs. `shadow → live` flips which one Books read. Rollback is `live → retired` plus flipping `supersedes` back. Because the artifacts are immutable and both versions see the same inputs, "did the new model actually do better" is answerable from the prediction log alone, with no re-run.

#### 7.4 What the BMS needs to know

Copying the FreqAI idea (§9.2) but making it explicit, **every published MIS output must carry three scalars the BMS can act on without understanding the model**:

1. **`confidence`** ∈ [0,1] — the model's own probability/margin. For an HMM, `max(filtered_posterior)`. For a jump model, the online proba max. For GARCH, absent (use `null`, not a fake 1.0).
2. **`novelty`** ∈ [0,∞) — how unlike the training data the current input is. FreqAI's Dissimilarity Index (§9.2) is the reference design: distance from the prediction vector to the training set, normalised by the training set's characteristic spread. **This is what catches "the market is doing something the model has literally never seen", which is precisely when a prop-firm account dies.**
3. **`staleness`** — `now - fitted_through`, plus a boolean `expired` derived from `expires_after`.

**BMS policy then needs no ML knowledge at all:** *if `expired`, or `novelty > threshold`, or `confidence < floor`, downgrade the Book's authority.* That is a rule the operator can read, reason about and set numbers on.

---

### 8. Model decay / drift detection — the minimum viable version

#### 8.1 What exists

- **`river.drift`** — ADWIN, PageHinkley, KSWIN + binary-target DDM/EDDM/FHDDM/HDDM-A/HDDM-W. BSD-3, 1.4 MB, actively maintained. `update(x)` / `drift_detected`. Small enough to put on the VPS.
- **`evidently`** — <https://github.com/evidentlyai/evidently>, Apache-2.0, 7,812 stars, `pushed_at` 2026-08-05, PyPI **0.7.21 (2026-03-10)**. Alive. Produces drift reports and dashboards (100+ metrics, data drift, target drift, model quality).
  - **26 core dependencies** including `litestar`, `uvicorn[standard]`, `nltk`, `plotly`, `watchdog`, `typer`, and `iterative-telemetry`.
  - **Telemetry, verified:** anonymous usage reporting is on by default and is disabled by setting the `DO_NOT_TRACK` environment variable to any value; per Evidently's own docs, telemetry is collected only when using the Monitoring UI, not when used as a library in a script or notebook (<https://docs.evidentlyai.com/faq/telemetry>). **Operator decision: a trading-system dependency that phones home by default is a policy question, even when the payload is anonymous.**
  - Verdict: **research-environment only, if at all.** Never on the trading VPS.

#### 8.2 The minimum viable version — and it is not a detector

The genuinely important insight for a solo operator: **you do not need a drift detector running today. You need the data that makes drift detectable later.** A detector you can add in six months is worthless if the six months of evidence was never written down.

**Log one row per prediction, append-only, to Parquet. Minimum columns:**

| Column | Why |
|---|---|
| `prediction_id`, `inference_ts` | Identity and ordering |
| `model_id`, `model_version`, `promotion_state` | Which model — including shadow models, which is how you compare |
| `input_hash` | Cheap reproducibility check |
| `features` (the actual values) | Without these you can never compute input drift retrospectively |
| `output` (the full published object) | The claim being made |
| `confidence`, `novelty`, `staleness` | §7.4 |
| `fitted_through` | Model vintage at time of use |
| `realised_outcome`, `outcome_ts` | **Written later**, when the label becomes knowable. Nullable at write time. |

With that table, every drift question becomes a query you can run at any future date: input drift = distribution shift in `features` over time; concept drift = degradation of `output` vs `realised_outcome`; model comparison = shadow vs live on identical `inference_ts`. **Zero dependencies, zero runtime cost beyond an append.**

Then, *optionally*, add `river.drift.ADWIN` fed with per-prediction error once outcomes exist. That is a strict upgrade to the same data, added later, with no migration.

---

### 9. Prior art — does any open trading framework ship an ML/regime subsystem worth copying?

#### 9.1 Summary

| Framework | Licence | ML/regime subsystem? | Copyable? |
|---|---|---|---|
| **Freqtrade / FreqAI** | **GPL-3.0** | **Yes — the only real one.** Retraining scheduler, walk-forward backtest, feature callbacks, outlier/confidence flags, model store | **Ideas only. Code is GPL — cannot enter a closed QMF.** |
| NautilusTrader | **LGPL-3.0** | **No — explicitly out of scope** | Ideas only |
| LEAN / QuantConnect | Apache-2.0 | Partial — `Train()` scheduler + `ObjectStore` blob store. No models, no registry, no regime detection | **Yes, code is Apache-2.0** |
| Hummingbot | Apache-2.0 | **No.** Its `hummingbot/model/` directory is SQLAlchemy ORM (orders, positions, market_state) — database models, not ML models | n/a |

#### 9.2 FreqAI — real depth, read from source

Freqtrade is **GPL-3.0** (repo licence, PyPI classifier "GNU General Public License v3"), 53,371 stars, `pushed_at` 2026-08-17, PyPI 2026.7. **Extremely healthy.** For a closed-source QMF, this means: **read it, learn from it, do not copy a line of it.**

**Architecture, verified against `freqtrade/freqai/freqai_interface.py`, `data_kitchen.py`, `data_drawer.py` on `develop`.**

**(a) The walk-forward backtest and the live path are the same shape.** From `FreqaiModelInterface.start_backtesting` (source comment, verbatim):

> "For backtesting, each pair enters and then gets trained for each window along the sliding window defined by `train_period_days` (training window) and `backtest_period_days` (backtest window, i.e. window immediately following the training window). FreqAI slides the window and sequentially builds the backtesting results before returning the concatenated results for the full backtesting period back to the strategy."

implemented as `for tr_train, tr_backtest in zip(dk.training_timeranges, dk.backtesting_timeranges, strict=False)`. **This is the single best structural idea in FreqAI: the backtest simulates the retrain schedule rather than assuming one model for all time.** For QMX — which retrains quarterly — the backtest must therefore replay quarterly retrains, or it is testing a model that never existed.

**(b) Retrain triggering in live** is `check_if_new_training_required(trained_timestamp)` in `data_kitchen.py`: `elapsed_time = (now - trained_timestamp) / 3600; retrain = elapsed_time > live_retrain_hours`. Simple wall-clock. A separate thread (`_start_scanning`) does the training so the trading loop is not blocked, and `_set_train_queue` orders pairs by oldest `trained_timestamp` first.

**(c) The warm-up extension — worth stealing.** In the same function, the *data load* range is deliberately longer than the *training* range:

```python
max_period = self.config.get("startup_candle_count", 20) * 2
additional_seconds = max_period * max_tf_seconds
data_load_timerange.startts = int(time - train_period_days * SECONDS_IN_DAY - additional_seconds)
```

with the source comment: "we want to load/populate indicators on more data than we plan to train on so because most of the indicators have a rolling timeperiod, and are thus NaNs unless they have data further back in time before the start of the train period". **QMF's indicator warm-up discipline (file 03) needs exactly this at the MIS boundary too.**

**(d) The model store layout** — from `FreqaiDataDrawer.save_data`:
- `<model_filename>_model.joblib` (cloudpickle of the model), or `_model.h5` (keras) / `_model.zip` (sb3/pytorch)
- `<model_filename>_metadata.json` — **a JSON sidecar carrying `training_features_list`, `label_list`, `data_path`, `model_filename`**
- `<model_filename>_feature_pipeline.pkl`, `<model_filename>_label_pipeline.pkl` (cloudpickle)
- `<model_filename>_trained_df.pkl`, `_trained_dates_df.pkl`
- directory-level: `pair_dictionary.json` (the index), `global_metadata.json`, `metric_tracker.json`, `historic_predictions.pkl` **plus `historic_predictions.backup.pkl`**

**Copy:** the JSON manifest sitting beside the binary artifact listing the exact feature and label column names, and the directory-level index file. That is 80% of a model registry for zero dependencies.
**Avoid:** cloudpickle for the model *and* the pipelines. The strongest evidence that this is a mistake is in FreqAI's own code — `load_historic_predictions_from_disk` contains an explicit corruption-recovery path ("Historical prediction file was corrupted. Trying to load backup file."). They had to build a backup-file fallback because pickle broke in production.

**(e) Contract enforcement between artifact and consumer.** `check_if_feature_list_matches_strategy(dk)` refuses to load a pretrained model whose stored `training_features_list` does not match what the strategy currently produces, with the message "Trying to access pretrained model with `identifier` … strategy is furnishing the same features as the pretrained…". **Copy this exactly.** It is the mechanism that stops an LLM-authored strategy silently feeding a model the wrong columns.

**(f) The confidence/staleness triple — the most valuable idea.** FreqAI publishes a `do_predict` column alongside every prediction:
- Outlier detection sets `dk.do_predict = outliers` from `feature_pipeline.transform(..., outlier_check=True)`.
- The **Dissimilarity Index** `DI_k = d_k / d̄`, where d_k is the distance from the prediction vector to the training data and d̄ the training data's characteristic spread; `DI_threshold` controls tolerance — "A higher `DI_threshold` means that the DI is more lenient and allows predictions further away from the training data to be used" (<https://www.freqtrade.io/en/stable/freqai-feature-engineering/>). Also available: SVM outlier removal (`use_SVM_to_remove_outliers`), DBSCAN (`use_DBSCAN_to_remove_outliers`), and PCA.
- **Expiry:** `check_if_model_expired(trained_timestamp)` against `expiration_hours`; when expired, `build_strategy_return_arrays` returns zero predictions with `do_preds = np.ones(2) * 2` and logs "Model expired for {pair}, returning null values to strategy. Strategy construction should take care to consider this event with prediction == 0 and do_predict == 2".

**This is the direct precedent for §7.4.** A prediction is never published bare; it is published with a machine-readable trust flag that a non-ML consumer can branch on.

**(g) What FreqAI gets wrong — QMF must not repeat it.**

- **No purging, no embargo, anywhere.** I grepped `data_kitchen.py` and `freqai_interface.py` for `purge` and `embargo`: the only hit is `self.dd.purge_old_models()`, which deletes old *files* from disk. Since FreqAI targets are forward-looking (the docs describe `set_freqai_targets` shifting by `label_period_candles` and averaging across that span), **the tail of every training window overlaps the head of its test window**. The train/test score is therefore optimistic by construction.
- **A leakage-critical knob exposed as a plain config passthrough.** In `make_train_test_datasets`:

  ```python
  if "shuffle" not in self.freqai_config["data_split_parameters"]:
      self.freqai_config["data_split_parameters"].update({"shuffle": False})
  ...
  train_test_split(filtered_dataframe[...], labels, weights,
                   **self.config["freqai"]["data_split_parameters"])
  ```

  The default is correct (`shuffle=False` → chronological split). But the whole dict is splatted into `train_test_split`, so a user who writes `"shuffle": true` in JSON gets a randomly interleaved train/test split with forward-looking labels — total leakage, no warning, no error. There is also a `shuffle_after_split` feature-parameter that reshuffles both sides afterwards.
  **Lesson for QMF: never let a leakage-critical parameter be a config passthrough.** A knob an LLM agent can set to a value that silently invalidates every result is a design defect, not a feature.

#### 9.3 NautilusTrader — the explicit out-of-scope precedent

LGPL-3.0, 25,666 stars, `pushed_at` 2026-08-17. Its ROADMAP lists, verbatim, under out of scope:

> "Integrated hyper-parameter optimization or built-in AI/ML tooling: users should integrate their own optimization frameworks tailored to their needs."

alongside "UI dashboards or frontends: focus remains strictly on the core trading engine".

**Should the precedent apply to QMF? Partially, and the distinction matters.**
- Nautilus is a *general engine* serving unknown users; it is right to refuse ML, because it cannot know which ML anyone wants and a wrong guess becomes permanent API.
- QMX is *one operator's whole business*, and the MIS is a **named subsystem in the mandate** with a concrete job (prop-firm risk gating). Refusing it would leave a named requirement unimplemented.
- **Where the precedent absolutely does apply: depth.** Nautilus's instinct is that a trading engine should not own model *training*. QMF should own the **contract** — what a model is, how it registers, what it publishes, how it expires, how it is bound to a Book — and own **zero** of the mathematics. Every fitting algorithm stays in a third-party library that runs in the cloud sandbox and never touches the VPS.

Also relevant, from the same document: Nautilus is "purpose-built for individual and small team quantitative traders" on single-node infrastructure. That is QMX's exact profile and it is a useful sanity check on scope creep.

#### 9.4 LEAN / QuantConnect

Apache-2.0, 21,240 stars, `pushed_at` 2026-08-14. I grepped the full repo tree for `regime`, `MachineLearning`, `Hmm`, `MarkovS` — **no ML or regime subsystem in-tree.** What LEAN does provide:

- **`Train()`** — `Train(MyTrainingMethod)` and `Train(DateRules.Every(DayOfWeek.Sunday), TimeRules.At(8, 0), MyTrainingMethod)` (<https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/training-models>). It exists to buy compute time: "Algorithms usually must process each timeslice within 10 minutes, but the Train method allows you to increase this time", governed by a leaky bucket. Crucially, **"in backtests the Train method is synchronous… in live trading the Train method is asynchronous"** — so the docs tell you to keep a boolean readiness flag before using predictions.
  **This asymmetry is a design smell QMF should avoid.** Backtest and live must not differ in whether training blocks; if they do, your backtest cannot exhibit the "trading with a stale model while the new one trains" state that live will definitely hit.
- **`ObjectStore`** — an untyped key/value blob store with `Save`, `SaveBytes`, `SaveJson`, `SaveXml`. The docs recommend saving "at the end of the training method" in live and "during the OnEndOfAlgorithm event handler" in backtests. **No versioning, no manifest, no promotion states, no scoping, no expiry** — it is a bucket, not a registry.
- The docs do state the discipline: "To avoid look-ahead bias in backtests, don't train your model on the same data you use to test the model" — but it is advice, not a mechanism.
- Supported ML libraries in QC Cloud include scikit-learn, TensorFlow, PyTorch, XGBoost, Keras, **hmmlearn**, tslearn (<https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/key-concepts>) — note that this makes `hmmlearn`'s smoothing trap live inside QuantConnect algorithms too.

**Net: LEAN provides a scheduler and a blob store, and is Apache-2.0 so it can be copied. Neither is a hard thing to write, and QMF's registry design (§7.3) is strictly richer.**

#### 9.5 Hummingbot

Apache-2.0, 19,487 stars. Grepping its tree for ML terms returns only `hummingbot/model/*` — `controllers.py`, `order.py`, `position.py`, `market_state.py`, `db_migration/` — which is the **SQLAlchemy persistence layer**, not machine learning. **Hummingbot has no ML subsystem.** Do not be misled by the directory name.

---

### 10. Library summary table

| Library | Version | Last release | Repo pushed | Licence | VPS footprint | Verdict |
|---|---|---|---|---|---|---|
| **statsmodels** (`regime_switching`) | 0.14.6 | 2025-12-05 | 2026-08-17 | BSD-3-Clause | 9.5 MB | **ADOPT** — research + as `arch`'s dep; best filtered/smoothed API |
| **arch** (GARCH) | 8.0.0 | 2025-10-21 | 2026-08-10 | **NCSA** (permissive) | pulls statsmodels | **ADOPT** — but flag NCSA for operator sign-off |
| **LightGBM** | 4.7.0 | 2026-07-18 | 2026-08-14 | MIT | **1.4 MB Win / 3.5 MB Linux** | **ADOPT** — the only GBM that belongs on a VPS |
| **scikit-learn** | 1.9.0 | 2026-06-02 | — | BSD-3-Clause | 8.3 MB | **ADOPT** — clustering, scaling, splitters |
| **hmmlearn** | 0.3.3 | 2024-10-31 | **2024-10-31** | BSD-3-Clause | 0.1 MB | **OPERATOR DECISION** — dormant ~22mo; use training-side only, QMF owns the forward step |
| **river** (`drift` only) | 0.25.0 | 2026-05-31 | 2026-08-12 | BSD-3-Clause | 1.4 MB | **OPERATOR DECISION** — adopt `drift` module only; reject online *learning* |
| **jumpmodels** | 0.1.1 | 2024-10-04 | 2025-01-12 | Apache-2.0 | ~0.1 MB | **OPERATOR DECISION** — best online API, worst maintenance; vendor rather than depend |
| **ruptures** | 1.1.10 | 2025-09-10 | 2026-07-06 | BSD-2-Clause | 0 (research only) | **OPERATOR DECISION** — research-only; offline by design, never a live/backtest feature |
| **onnxruntime** (+ onnxmltools/skl2onnx) | 1.28.0 | 2026-07-25 | 2026-08-17 | MIT / Apache-2.0 | 13.8–19.2 MB | **OPERATOR DECISION** — only if >1 model family needs one loader |
| **MLflow** | 3.15.1 | 2026-08-03 | 2026-08-17 | Apache-2.0 | research only, 11.2 MB, 20 deps | **OPERATOR DECISION** — genuinely cheap now (SQLite default, Windows OK) but duplicable in ~200 lines |
| **XGBoost** | 3.4.1 | 2026-08-15 | 2026-08-17 | Apache-2.0 | **~310 MB on Linux** (nccl) | **AVOID** — for the VPS |
| **CatBoost** | 1.2.10 | 2026-02-18 | 2026-08-16 | Apache-2.0 | ~100 MB + matplotlib/plotly/graphviz | **AVOID** |
| **pomegranate** | 1.1.2 | 2025-02-07 | 2025-03-06 | MIT | **torch: 526 MB Linux / 122 MB Win** | **AVOID** — public `forward()` is nice, torch dep is disqualifying |
| **bayesian-changepoint-detection** | 0.2.dev1 | **2019-08-12** | 2025-11-06 | MIT | — | **AVOID as a dependency** — PyPI and GitHub are different codebases; vendor the BOCPD file if needed |
| **feast** | 0.65.0 | 2026-07-20 | 2026-08-16 | Apache-2.0 | 30 deps, a service | **AVOID** — solve PIT with an `available_at` column + DuckDB |
| **evidently** | 0.7.21 | 2026-03-10 | 2026-08-05 | Apache-2.0 | 26 deps, telemetry-on-by-default | **AVOID on VPS**; operator decision for research |
| **tsfresh** | 0.21.2 | 2026-05-31 | 2026-07-06 | MIT | 12 deps | **AVOID** — conflicts with QMF's define-once incremental indicator model |
| **tsfel** | 0.2.0 | 2025-08-20 | 2026-01-30 | BSD-3-Clause | 9 deps | **AVOID** — same reason, and slower cadence |
| **DVC** | 3.67.1 | 2026-03-31 | 2026-08-17 | Apache-2.0 | — | **AVOID** — overlaps solved Parquet/DuckDB storage; ownership moved to lakeFS 2025-11 |
| **m2cgen** | 0.10.0 | **2022-04-26** | 2024-08-03 | MIT | 0 | **AVOID** — dormant |
| **creme** | 0.6.1 | **2020-06-10** | — | BSD-3 | — | **AVOID** — superseded by `river` |
| **treelite** | 4.7.0 | 2026-03-06 | 2026-08-12 | Apache-2.0 | build step | **AVOID for now** — LightGBM text format already solves this |
| **mlfinlab** | — | — | — | **commercial** | — | **AVOID** (already established in file 03) |

---

## What QMF should copy / avoid

### Copy

1. **From FreqAI: publish a trust flag with every prediction.** Never publish a bare number. Every MIS output carries `confidence`, `novelty` (a DI-style distance-to-training-distribution), and `staleness`/`expired`. This is the mechanism that lets the BMS act on model health without knowing any ML. *(GPL-3.0 — idea only, write it fresh.)*
2. **From FreqAI: a JSON manifest beside every artifact, listing the exact ordered input feature names and output names**, plus a directory-level index file. Then refuse to bind a model whose manifest's input contract does not match what the consumer produces — FreqAI's `check_if_feature_list_matches_strategy`. This is the single defence against an LLM-authored Confirmation quietly feeding a model the wrong columns.
3. **From FreqAI: make the backtest replay the retrain schedule.** If production retrains quarterly, the backtest walks quarterly windows: train on window N, predict on window N+1, slide. A backtest that fits once and predicts across ten years is testing a model that never existed.
4. **From FreqAI: load more history than you train on.** Extend the data-load window backwards by (max indicator warm-up × 2 × max timeframe) so no training row is computed from a partially warmed indicator.
5. **From statsmodels: three separate, differently-named probability series.** QMF's regime interface should expose `predicted` / `filtered` / `smoothed` as *distinct named methods*, never one `predict()` whose safety depends on a keyword argument. Making the unsafe one impossible to call by accident is worth more than documenting it.
6. **From `arch` and `statsmodels`: the `fix(params)` / `filter(params)` pattern.** Every QMF model artifact is a *parameter vector plus a loader*, applied to fresh data. Nothing is ever "the fitted object" carried across a process boundary.
7. **From LEAN: an explicit training-time budget and an asynchronous training path** — but symmetric between backtest and live, unlike LEAN's.
8. **From NautilusTrader: refuse depth.** QMF owns the *contract*; libraries own the *mathematics*; training happens off the VPS.

### Avoid

1. **Never ship a pickle to the VPS.** Not `pickle`, not `cloudpickle`, not `joblib`. Permitted artifact formats: LightGBM text, JSON/npz parameter arrays, ONNX. FreqAI's own corrupted-file recovery path is the evidence.
2. **Never bind a `smoothed` model to a live consumer.** Enforce it in the registry (`causality` field) *and* with the property test in §2.3, not with a comment.
3. **Never call `hmmlearn.predict_proba()` and use anything but the last row.** Better: never call it at all — export the arrays and own the forward recursion.
4. **Never expose a leakage-critical parameter as a config passthrough.** FreqAI's `data_split_parameters` splat into `train_test_split` means `"shuffle": true` in a JSON file silently destroys the experiment. QMF's splitters take enumerated, validated arguments; a chronological split is not overridable.
5. **Do not put XGBoost or CatBoost on the Linux VPS.** 310 MB of CUDA libraries and 100 MB of charting stack respectively, for a CPU tree predictor LightGBM does in 3.5 MB.
6. **Do not adopt a feature store.** Own the point-in-time invariant instead: every revisable input carries both `event_time` and `available_at`; backtests filter on `available_at`.
7. **Do not build for online learning first.** It is incompatible with shadow rollout, rollback, reproducibility and post-hoc audit — all four of which QMX has already committed to.
8. **Do not oversell regime detection as alpha.** The FX literature does not support directional prediction. Position it in the specification as a *risk filter and Confirmation weight*, so nobody — human or agent — later builds a Trigger on it and is surprised.
9. **Do not depend on `bayesian-changepoint-detection` from PyPI.** The published package is from 2019 and is not the code its own README documents.

---

## Open questions

1. **Regime granularity — operator decision.** Is the MIS's regime *per-pair* (28 separate labellers), *per-cluster* (majors / JPY crosses / commodity currencies), or *global* (one "dollar/risk state")? This determines whether QMF ships 1 model or 28, and drives the whole registry cardinality. File 06 established FRED's `DTWEXBGS` as a slow dollar proxy, which argues for at least one global model.
2. **What is a regime, in QMX's vocabulary?** Volatility state (calm/turbulent/crisis) and trend state (trending/ranging) are different models with different evidence bases — the volatility one has support, the trend one does not. Are both in scope, and does the BMS consume both?
3. **`hmmlearn`'s dormancy — accept, vendor, or avoid?** No commits in ~22 months, and the look-ahead issue (#579) will not be fixed. Options: (a) accept it as a training-side-only dependency; (b) vendor the ~300 relevant lines under BSD-3; (c) use `statsmodels.MarkovRegression` instead, which is maintained and has the better API but is a regression model rather than a general multivariate HMM. **My lean is (c) primary, (a) secondary.**
4. **`arch`'s NCSA licence.** Permissive and commercially safe on reading, but not MIT/BSD/Apache-2.0. Needs an explicit operator tick if QMF ships commercially. Note that avoiding `arch` also means avoiding GARCH entirely — ATR percentiles are not a substitute for a variance forecast.
5. **MLflow or a hand-rolled manifest directory?** MLflow is cheaper than expected (SQLite default, no server, Windows-supported) and gives experiment tracking for free — which matters because *experimentation is a first-class QMX feature*. Against: 20 dependencies and a second source of truth beside QMF's own registry. **This is a genuine trade-off and I decline to pick silently.** Suggested split: QMF owns the *registry* (manifests, scoping, promotion, rollback — the VPS-facing part), MLflow optionally owns *experiment tracking in the cloud sandbox only*.
6. **`jumpmodels`: depend, vendor, or reimplement?** It has the best online API in the survey and the worst maintenance. Apache-2.0 permits vendoring. The core DP is ~100 lines. **Vendoring looks correct but is an operator call**, since it means QMF carries the maintenance.
7. **Shadow-rollout promotion criteria — undefined.** What quantitative test promotes `shadow → live`? A minimum shadow duration? Agreement rate with the incumbent? Better realised outcome on the prediction log? Until this is specified, shadow rollout is a mechanism without a decision rule.
8. **BMS thresholds are unset.** §7.4 defines `confidence`, `novelty`, `staleness`; nothing here says what values throttle a Book. These must be calibrated on real data, not guessed, and they are probably Book-specific (a prop-firm Book should be far more paranoid than a personal-capital Book).
9. **Crypto (3–4 months out) will need different regime features.** Funding rate and perp basis (file 07) are regime signals that have no FX analogue. Does the MIS's published object have room for asset-class-specific fields, or does each asset class get its own model kind?
10. **Retrain cadence vs `expires_after`.** Quarterly training implies models routinely operate 90 days past their fit. What is the expiry horizon, and what happens in the gap if a quarterly retrain fails or is skipped — does the Book halt, or degrade to a no-model default?
11. **Latency is unmeasured.** I found no primary-source figure for LightGBM single-row inference latency that I would rely on. **This must be benchmarked on the actual VPS**, not inferred.
12. **Where does the MIS run?** It is described as publishing to Books and the BMS, but it is not stated whether it is an in-process QMF component on the VPS, a separate process, or both (desktop app for research, VPS for live). This affects whether the published object crosses a serialisation boundary — and if it does, it needs a wire format, not just a Python type.

---

### Source index (primary only)

| Topic | URL |
|---|---|
| hmmlearn repo | https://github.com/hmmlearn/hmmlearn |
| hmmlearn `base.py` (predict / score_samples / decode) | https://github.com/hmmlearn/hmmlearn/blob/main/src/hmmlearn/base.py |
| hmmlearn `_hmmc.cpp` (forward_log / backward_log) | https://github.com/hmmlearn/hmmlearn/blob/main/ext/_hmmc.cpp |
| hmmlearn issue #579 — look-ahead in `predict_proba` | https://github.com/hmmlearn/hmmlearn/issues/579 |
| statsmodels `markov_switching.py` | https://github.com/statsmodels/statsmodels/blob/main/statsmodels/tsa/regime_switching/markov_switching.py |
| jumpmodels repo | https://github.com/Yizhan-Oliver-Shu/jump-models |
| jumpmodels `jump.py` (dp / predict_online) | https://github.com/Yizhan-Oliver-Shu/jump-models/blob/master/jumpmodels/jump.py |
| Jump model paper (arXiv) | https://arxiv.org/abs/2402.05272 |
| Jump model paper (J. Asset Management) | https://link.springer.com/article/10.1057/s41260-024-00376-x |
| ruptures docs (offline statement) | https://centre-borelli.github.io/ruptures-docs/ |
| bayesian_changepoint_detection repo | https://github.com/hildensia/bayesian_changepoint_detection |
| arch LICENSE (NCSA) | https://raw.githubusercontent.com/bashtage/arch/main/LICENSE.md |
| arch `base.py` (`fix`) | https://github.com/bashtage/arch/blob/main/arch/univariate/base.py |
| arch forecasting docs | https://bashtage.github.io/arch/univariate/forecasting.html |
| pomegranate HMM `_base.py` | https://github.com/jmschrei/pomegranate/blob/master/pomegranate/hmm/_base.py |
| Engel (1994), J. Int. Economics 36(1–2) | https://ideas.repec.org/a/eee/inecon/v36y1994i1-2p151-165.html |
| Engel (1994) NBER working paper | https://www.nber.org/papers/w4210 |
| Dueker & Neely (2007), JBF 31(2) | https://ideas.repec.org/a/eee/jbfina/v31y2007i2p279-296.html |
| Multi-Scale MS-GARCH EUR/USD (preprint) | https://arxiv.org/abs/2606.06190 |
| river repo | https://github.com/online-ml/river |
| river FAQ (pickle persistence) | https://riverml.xyz/latest/faq/ |
| river ADWIN API | https://riverml.xyz/latest/api/drift/ADWIN/ |
| river API overview (drift detectors) | https://riverml.xyz/latest/api/overview/ |
| LightGBM org move issue #7187 | https://github.com/lightgbm-org/LightGBM/issues/7187 |
| LightGBM Booster API (save_model, text format) | https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.Booster.html |
| nvidia-nccl-cu13 wheel size (252 MB) | https://pypi.org/pypi/nvidia-nccl-cu13/json |
| tsfresh forecasting / roll_time_series | https://tsfresh.readthedocs.io/en/latest/text/forecasting.html |
| Feast point-in-time joins | https://docs.feast.dev/getting-started/concepts/point-in-time-joins |
| MLflow filesystem-backend deprecation (#18534) | https://github.com/mlflow/mlflow/issues/18534 |
| MLflow LICENSE (Apache-2.0) | https://raw.githubusercontent.com/mlflow/mlflow/master/LICENSE.txt |
| MLflow tracking docs | https://mlflow.org/docs/latest/ml/tracking/ |
| DVC joins lakeFS | https://dvc.org/blog/dvc-joins-lakefs-your-questions-answered/ |
| Evidently telemetry FAQ (DO_NOT_TRACK) | https://docs.evidentlyai.com/faq/telemetry |
| FreqAI overview | https://www.freqtrade.io/en/stable/freqai/ |
| FreqAI configuration | https://www.freqtrade.io/en/stable/freqai-configuration/ |
| FreqAI feature engineering (DI, SVM, DBSCAN) | https://www.freqtrade.io/en/stable/freqai-feature-engineering/ |
| FreqAI `freqai_interface.py` | https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqai/freqai_interface.py |
| FreqAI `data_kitchen.py` | https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqai/data_kitchen.py |
| FreqAI `data_drawer.py` | https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/freqai/data_drawer.py |
| NautilusTrader ROADMAP (AI/ML out of scope) | https://github.com/nautechsystems/nautilus_trader/blob/develop/ROADMAP.md |
| QuantConnect ML key concepts | https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/key-concepts |
| QuantConnect `Train()` docs | https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/training-models |

---

## Closing recommendation

**The smallest dependency set QMF should adopt for the MIS:**

*Cloud sandbox (training only — never installed on the VPS):*
`statsmodels` (Markov-switching, and it comes with `arch` anyway) · `arch` (GARCH) · `scikit-learn` (clustering, scaling, purged splitters) · `LightGBM` (if and only if a supervised predictor is actually wanted) · optionally a vendored copy of the ~100-line jump-model DP.

*Linux trading VPS (inference only):*
`numpy` · `LightGBM` 1.4 MB text-model loader (only if a GBM is in play) · `river` **for `drift` only**, 1.4 MB. **That is it.** No statsmodels, no arch, no hmmlearn, no sklearn, no MLflow, no evidently, no torch.

**What QMF must own itself, because no library does it:**
1. The one-step **forward/filtered recursion** for HMM and Markov-switching inference (~15–30 lines each), so nothing smoothed can reach a live consumer.
2. The **`causality` invariant test** — `label(bars[0:t])[-1] == label(bars[0:t+n])[t]` — run against every regime component in CI.
3. The **model registry**: manifest schema, `scope` (global vs `book:<id>`), promotion states, `supersedes` rollback pointer, artifact hash, expiry.
4. The **prediction log** (§8.2) — the append-only Parquet table that makes decay detectable retrospectively.
5. The **point-in-time invariant**: `event_time` + `available_at` on every revisable input.
6. The **published MIS output object**.

**What the published MIS output should look like** — one typed, frozen, JSON-serialisable object, so a Book, a Confirmation, and the BMS can each read the parts they care about and ignore the rest:

```
MarketView
  as_of                : timestamp        # bar close this view describes
  published_at         : timestamp        # when it was computed (>= as_of)
  scope                : "global" | "symbol:EURUSD" | "book:<id>"
  model_id, model_version, promotion_state

  # --- what a Confirmation reads (weighted filter input) ---
  regime               : enum             # e.g. CALM | TURBULENT | CRISIS
  regime_proba         : {enum: float}    # sums to 1
  expected_duration    : float | null     # bars, from 1/(1-p_ii)

  # --- what a Book reads (sizing / participation) ---
  volatility_forecast  : float | null     # h-step conditional sigma, in price units
  volatility_percentile: float | null     # [0,1] vs training distribution

  # --- what the BMS reads (authority) ---
  confidence           : float | null     # [0,1]; null when the model has no notion
  novelty              : float            # DI-style distance-to-training-distribution
  staleness_seconds    : int
  expired              : bool
  causality            : "filtered" | "predicted"   # "smoothed" is not constructible here
```

Three properties make this safe for an LLM-authored caller: the `causality` field can only take the two safe values in a live object (a smoothed model cannot produce one at all); `confidence` is explicitly nullable so nobody can read a fabricated `1.0`; and every consumer reads named fields rather than positional tuples, so a schema change breaks loudly.

**Shortlist of what NOT to adopt, and why, in one line each:**
XGBoost (310 MB of CUDA on Linux) · CatBoost (100 MB + charting stack) · pomegranate (526 MB torch) · Feast (30 deps and a service for a problem an `available_at` column solves) · evidently on the VPS (26 deps, telemetry on by default) · tsfresh/tsfel (fights QMF's define-once incremental indicator model) · DVC (duplicates the solved Parquet layer; ownership just moved) · m2cgen (dormant since 2022) · creme (dead, superseded by river) · `bayesian-changepoint-detection` from PyPI (the published package is not the code its README describes) · `river` as an *online learner* (incompatible with shadow rollout and rollback) · `mlfinlab` (not open source).

**And the one sentence to carry into the specification:** the MIS is a **risk instrument, not an alpha source** — the published evidence supports using regime state to decide *when not to trade*, and does not support using it to decide *what to trade*.
