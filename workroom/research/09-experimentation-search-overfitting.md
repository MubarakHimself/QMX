# QMF Prior Art: Experimentation, Parameter Search and Overfitting Control

**Research date:** 2026-08-17
**Area:** How candidate strategies get searched, how the search gets recorded, and — most importantly — what number has to be reported alongside a Sharpe ratio before a search result is allowed to mean anything. Covers hyperparameter search frameworks, genetic/evolutionary search, the overfitting statistics (DSR / PBO / SPA / MinBTL), experiment tracking, determinism, and sweep orchestration.
**Method:** primary sources only — upstream repos read via the GitHub API, PyPI JSON metadata, library source code read directly, and the original papers (AMS *Notices* PDF, López de Prado's own slide deck, Harvey & Liu's Duke-hosted PDF). Maintenance state verified today, 2026-08-17, via GitHub `pushed_at` and PyPI upload timestamps. Every load-bearing claim carries an inline URL. Anything I could not confirm against a primary source is tagged **UNVERIFIED**.

---

## In plain words

1. The single most important fact in this whole file: **if you try enough strategy variations, one of them will look brilliant even when none of them has any edge at all.** This is not an opinion, it is arithmetic, and it has an exact formula.
2. That formula says: try 10 variations of a worthless strategy and the best one will show a Sharpe ratio of about **1.57**. Try 100 and the best shows about **2.53**. Try a million — which an LLM agent can do in a weekend — and the best shows about **4.87**. All of them are worth exactly zero.
3. The same formula, read backwards, says how much history you need before a given Sharpe is even *possible* evidence of skill. With 5 years of data you may try **45 independent variations, and no more**. With 10 years, about 780. Beyond that you are guaranteed to manufacture a beautiful lie.
4. So the rule QMX must live by is: **a Sharpe ratio reported without the number of trials that produced it is not a result. It is a decoration.** Any strategy report that does not carry a trial count should be treated as unread.
5. There are four cheap, well-published numbers that turn a search result into something trustworthy, and QMF should compute all four automatically: the **Deflated Sharpe Ratio** (probability the edge is real, after discounting for how many things you tried), the **Probability of Backtest Overfitting** (how often your selection method picks a loser), the **Minimum Backtest Length** (do you even have enough history for this many trials), and **Hansen's SPA test** (is the best candidate genuinely better than doing nothing, allowing for the whole field of candidates).
6. Three of those four are short formulas QMF can implement in about a hundred lines. The fourth already exists, correct and free, in a library called `arch`. The most famous implementation of the first three, `mlfinlab`, is **not free** — already established in file 03 — but a small MIT-licensed library called `purgedcv` implements them all and I read its source line by line today; it matches the papers exactly.
7. For actually running the search, **Optuna** is the clear answer: MIT licence, actively developed (a commit landed this morning), works identically on Windows and Linux, needs no server, and can save a search to a plain file so it survives a crash and resumes.
8. Optuna also has two features that matter specifically for noisy trading objectives that most people never use: a sampler that explicitly models "my measurements are noisy" (GPSampler), and a stopper that uses a proper statistical test to abandon a candidate that is losing across your validation folds (WilcoxonPruner).
9. Of the alternatives — Ray Tune is enormous and only *beta* on Windows; Hyperopt just came back from the dead after five years and is fine but weaker; **scikit-optimize is dead** (archived on GitHub, last release 2024); Nevergrad has not shipped a release in 16 months; SMAC is healthy but aimed at a different problem.
10. On the operator's request for **genetic algorithms over indicators**: the tools exist and are fine (PyGAD is BSD, gplearn is BSD, DEAP is copyleft and therefore an operator decision), but genetic search is an *overfitting engine*. It evaluates tens of thousands of candidates by design, which is precisely the machine that manufactures the fake Sharpe in point 2. A GA is only safe if the fitness function itself already contains the deflation — that is the design decision, not the library choice.
11. **Freqtrade's `hyperopt` is the closest shipped example** of what the operator wants, and studying it is worth more than copying it (it is GPL-3.0, so it can only be studied). It is well engineered — twelve loss functions, a proper parameter type system, now built on Optuna — and yet its documentation never once tells the user to hold out data, never counts trials, and never deflates anything. That gap is exactly where QMX's edge is.
12. On recording experiments: a full tracking server (MLflow, Weights & Biases) is **not justified yet** for one operator. What is justified is a boring, versioned folder of run manifests — one JSON file per experiment recording the code commit, the split id, the parameters, the seeds, and the environment. Six months later that folder answers "how did I get this number"; a tracking server would too, but at ten times the operating cost.
13. Reproducibility is harder than it looks and QMX has one specific landmine: **DuckDB's own documentation admits that `stddev` and `corr` can return different answers on different runs** because of multi-threaded floating-point. A Sharpe ratio computed that way is not bit-reproducible. QMF must pin thread counts and always sort explicitly.
14. On the design question the operator most needs answered: **an experiment must be an object QMF owns, not a script the caller writes.** It must refuse to accept raw dates (only a `split_id`, as already ratified in file 02), it must count how many times each out-of-sample window has been touched, and it must **refuse the call** when a window's budget is exhausted rather than merely warning. Discipline that is not enforced by an API does not survive an LLM author.
15. Recommended stack, smallest version: **Optuna** (search) + **`arch`** (SPA/StepM/MCS bootstrap tests) + **QMF-owned code** for the four overfitting numbers, the run manifest, and the split budget ledger + **joblib** locally and **Modal** for cloud sweeps. Nothing else earns its place in version one.

---

## Findings

### 1. The false-strategy theorem — the arithmetic that governs everything else

This is the foundation. Everything in sections 2–5 is a consequence of it, and every design recommendation in section 14 exists to make it operationally binding.

**Primary source:** Bailey, Borwein, López de Prado & Zhu (2014), *"Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance"*, **Notices of the American Mathematical Society**, 61(5), May 2014 — free full text at <https://www.ams.org/notices/201405/rnoti-p458.pdf> (SSRN mirror: <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659>). I extracted the text of this PDF directly rather than citing it from memory.

**Proposition 1** (the "false strategy theorem"). Given `N` independent trials whose Sharpe estimators have mean 0 and variance `V[SR]`, the expected maximum Sharpe ratio observed is

```
E[max{SR_n}]  ≈  sqrt(V[SR_n]) · ( (1 − γ)·Z⁻¹[1 − 1/N]  +  γ·Z⁻¹[1 − 1/(N·e)] )
```

where `γ = 0.5772156649…` is the Euler–Mascheroni constant, `Z⁻¹` is the inverse standard-normal CDF and `e` is Euler's number. The paper notes an upper bound of `sqrt(2·ln N)`. This exact form is also stated in López de Prado's own slide deck *"Deflating the Sharpe Ratio"* (Lawrence Berkeley National Laboratory), <https://pdfs.semanticscholar.org/c215/d0a2064ce1a3565d276475abc84305418f0f.pdf>, which is the companion to SSRN 2460551.

The paper's own worked figure: *"if the researcher tries only N = 10 alternative configurations of an investment strategy, she is expected to find a strategy with a Sharpe ratio IS of 1.57 despite the fact that all strategies are expected to deliver a Sharpe ratio of zero OOS (including the 'optimal' one selected IS)."*

**Minimum Backtest Length (MinBTL).** Solving the same expression for the sample length `y` in years (the paper's Equations 5 → 6) gives the shortest backtest under which a target annualised Sharpe `SR*` is *not* explicable by selection alone:

```
MinBTL(N, SR*)  ≈  [ ( (1 − γ)·Z⁻¹[1 − 1/N] + γ·Z⁻¹[1 − 1/(N·e)] ) / SR* ]²      (years)
```

The paper's stated calibration points: *"if only five years of data are available, no more than forty-five independent model configurations should be tried"* and *"After trying only seven independent strategy configurations, the expected maximum SR IS is 1 for a two-year long backtest, while the expected SR OOS is 0."*

I evaluated the formula independently (Python stdlib `statistics.NormalDist`, no library dependency) and it reproduces the paper's numbers exactly. **This table should be printed on the wall of the QMX research lane:**

| Independent trials N | E[max Sharpe] under the null | MinBTL for SR\*=1.0 | MinBTL for SR\*=2.0 |
|---|---|---|---|
| 7 | 1.387 | 1.92 yr | 0.48 yr |
| 10 | 1.575 | 2.48 yr | 0.62 yr |
| **45** | **2.236** | **5.00 yr** | 1.25 yr |
| 100 | 2.531 | 6.40 yr | 1.60 yr |
| 1,000 | 3.255 | 10.60 yr | 2.65 yr |
| 10,000 | 3.861 | 14.90 yr | 3.73 yr |
| 100,000 | 4.391 | 19.28 yr | 4.82 yr |
| 1,000,000 | 4.868 | 23.70 yr | 5.92 yr |

Read the N=45/5.00 yr row against the paper's sentence: exact match. Read the N=7/1.92 yr row against "two-year long backtest": exact match. The formula is verified.

**Why this is a QMX-specific emergency.** The operator's strategy schema is **Level + Trigger + Confirmation + Exit**, four slots each with parameters, plus a confluence-weighting vector over Confirmations. That is a combinatorial surface with easily 10⁶–10⁹ points *per strategy family*, and LLM agents will enumerate it without fatigue. At N = 10⁶ the null expects a Sharpe of **4.87**. Any QMX report showing a Sharpe of 3 after a large search is, by this arithmetic, **evidence of nothing**.

**Trials are not independent — and there is a correction.** The López de Prado deck gives the standard adjustment: with an `M × M` correlation matrix `C` across trials and average off-diagonal correlation `ρ̂`,

```
N̂  =  ρ̂  +  (1 − ρ̂)·M
```

so `ρ̂ → 1` collapses M trials to 1 effective trial and `ρ̂ → 0` leaves all M. In a grid over one indicator's lookback period, neighbouring settings are near-perfectly correlated, so a 10,000-point grid may only be a few hundred effective trials. **QMF must estimate `N̂`, not use the raw evaluation count** — the raw count is conservative (it over-penalises), which is the safe direction to err but will reject good strategies.

The same deck offers a stopping rule from optimal-stopping theory (the secretary problem): sample `1/e ≈ 37%` of the theoretically justifiable configurations at random, then take the first subsequent candidate that beats all of them. Cited here as prior art, not as a recommendation — it optimises "probability of picking the single best", which is not the objective QMX has.

---

### 2. Deflated Sharpe Ratio (DSR) and Probabilistic Sharpe Ratio (PSR)

**Primary sources.** Bailey & López de Prado (2014), *"The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality"*, **Journal of Portfolio Management** 40(5), 94–107 — SSRN <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551>. The PSR predecessor is Bailey & López de Prado (2012), *"The Sharpe Ratio Efficient Frontier"*, **Journal of Risk** 15(2). Formulas below are quoted from the author's own LBNL deck at <https://pdfs.semanticscholar.org/c215/d0a2064ce1a3565d276475abc84305418f0f.pdf>.

**PSR** — probability the *true* Sharpe exceeds a benchmark `SR*`, correcting for non-normal returns (this is Mertens' 2002 variance, valid under stationarity and ergodicity, not just i.i.d.):

```
PSR(SR*) = Z[ ( (SR̂ − SR*) · sqrt(T − 1) )
             / sqrt( 1 − γ₃·SR̂ + ((γ₄ − 1)/4)·SR̂² ) ]
```

where `γ₃` is sample skewness, `γ₄` is sample **kurtosis (not excess)**, `T` is the number of observations, `Z` is the standard normal CDF.

**DSR** — the same statistic with the benchmark raised to the level selection alone would have produced:

```
DSR ≡ PSR(SR̂₀)      where     SR̂₀ = sqrt(V[SR_n]) · ( (1 − γ)Z⁻¹[1 − 1/N] + γZ⁻¹[1 − 1/(N·e)] )
```

`V[SR_n]` is **the variance of the Sharpe ratios across the trials you actually ran** — not a theoretical quantity, an empirical one you must record during the search. This is the single most-missed input; it is why a search framework has to cooperate with the statistic.

**The deck's worked example, verbatim:** an analyst finds a daily strategy with annualised SR = 2.5 after N = 100 independent trials, with `V[SR_n] = 1/2`, `T = 1250`, `γ₃ = −3`, `γ₄ = 10`. *"QUESTION: Is this a legitimate discovery, at a 95% conf.? ANSWER: No. There is only a 90% probability that the true Sharpe ratio is above zero."* `DSR ≈ 0.9004`. Had the search been N = 46, `DSR ≈ 0.9505` — it would have passed. **The identical strategy passes or fails purely on how many things you tried.**

The deck also isolates the non-normality contribution: with `γ₃ = 0, γ₄ = 3` (normal returns) the same strategy clears 0.9505 at N = 88 rather than N = 46. Forex carry and mean-reversion strategies have exactly the negative-skew / fat-tail profile that costs the most here.

**Operator translation:** DSR is *"the probability that this is real, given how hard you looked."* Report it as a percentage. Below 95% means do not deploy.

---

### 3. Probability of Backtest Overfitting (PBO) via CSCV

**Primary source.** Bailey, Borwein, López de Prado & Zhu, *"The Probability of Backtest Overfitting"*, SSRN <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253>; published **Journal of Computational Finance** 20(4), 39–70 (2017). Open-access copies: <https://scholarworks.wmich.edu/math_pubs/42/> and <https://escholarship.org/uc/item/4w1110bb>.

**What it measures — and this is the part people get wrong.** PBO does not score a *strategy*. It scores your **selection procedure**. It answers: *when I pick the configuration that looked best in-sample, how often does that configuration land below the median out-of-sample?* A PBO of 0.5 means your selection method is worth exactly nothing.

**The CSCV algorithm** (Combinatorially Symmetric Cross-Validation), as implemented and documented in `purgedcv/_pbo.py` (read directly, see §6):

1. Build an `T × M` matrix of per-period returns, one column per configuration tried.
2. Cut the time axis into `S` contiguous blocks (S even).
3. Enumerate **every** way of choosing `S/2` blocks as in-sample; the complementary `S/2` are out-of-sample. That is `C(S, S/2)` combinations — the "combinatorially symmetric" part, and the reason it does not suffer hold-out's high variance.
4. In each combination: pick the IS-best configuration, find its **relative rank** among all M configurations OOS, take the logit of that rank.
5. `PBO` = the fraction of combinations whose logit is negative (i.e. IS-best landed below the OOS median).

The same run yields a second diagnostic worth keeping: the **OLS slope of OOS performance on IS performance** across combinations. Positive slope = in-sample strength carries over. Slope ≈ 0 = the link is random. **Negative slope = in-sample strength actively predicts out-of-sample weakness**, the signature of severe overfitting.

**Why hold-out is not a substitute** (from the deck, three reasons): hold-out is inadequate for short samples; different hold-outs give opposite conclusions (Van Belle & Kerr 2012); and critically — *"The hold-out method does not take into account the number of trials attempted before selecting a model, and consequently is subjected to selection bias."*

**Relation to file 03's splitter table.** `skfolio`'s `CombinatorialPurgedCV` and CSCV are the same construction: CSCV is CPCV with `n_test_groups = n_splits // 2`. So QMF already has the splitter; what it lacks is the *scoring loop on top of it*.

---

### 4. White's Reality Check, Hansen's SPA, StepM, MCS — verified first-hand in `arch`

This family answers a different question from DSR/PBO: **is the best of my candidates genuinely better than a benchmark, once the whole field of candidates is accounted for?** It is a bootstrap test, not a closed-form correction, and it handles the dependence between candidates properly.

**Package:** `arch` by Kevin Sheppard. **PyPI:** version **8.0.0**, uploaded **2025-10-21** (<https://pypi.org/pypi/arch/json>). **GitHub:** <https://github.com/bashtage/arch>, `pushed_at` **2026-08-10**, 1,551 stars, not archived. **Maintained.**

**Licence — checked directly, not from the GitHub badge.** GitHub's API reports `NOASSERTION`, which is misleading. I read `LICENSE.md` (<https://github.com/bashtage/arch/blob/main/LICENSE.md>): it is a **permissive NCSA/BSD-style licence** — "Permission is hereby granted, free of charge… including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies", with the three standard BSD conditions (retain notice in source, reproduce in binaries, no endorsement). **Commercially safe for QMX. ADOPT.**

**API verified by reading `arch/bootstrap/multiple_comparison.py` directly** (813 lines) rather than trusting the docs:

| Class | Test | Signature (verbatim from source) |
|---|---|---|
| `SPA` | Hansen (2005) Superior Predictive Ability | `SPA(benchmark, models, block_size=None, reps=1000, bootstrap="stationary", studentize=True, nested=False, *, seed=None)` |
| `RealityCheck` | White (2000) Reality Check | `class RealityCheck(SPA): # Shallow clone of SPA` |
| `StepM` | Romano & Wolf (2005) stepwise multiple testing | `StepM(benchmark, models, size=0.05, block_size=None, reps=1000, bootstrap="stationary", studentize=True, nested=False, *, seed=None)` |
| `MCS` | Hansen, Lunde & Nason (2011) Model Confidence Set | `MCS(losses, size, reps=1000, block_size=None, method="R"\|"max", bootstrap="stationary", *, seed=None)` |

Four facts from the source that the docs do not make loud enough and that will bite an implementer:

1. **These take *losses*, not returns.** The docstrings say so explicitly: *"benchmark : T element array of benchmark model **losses**"*. Internally `self._loss_diff = benchmark − models`. For a trading application you pass **negated returns**. Getting this backwards silently inverts the test.
2. **`RealityCheck` is literally `class RealityCheck(SPA): pass`** — a shallow clone. White's Reality Check in `arch` *is* Hansen's SPA, and Hansen's SPA strictly dominates it (White's version is the "Upper" recentering). Use `SPA` and read the `Consistent` p-value.
3. **Three p-values, not one.** From the `SPA` docstring: *"Upper: Never recenter so all models are relevant to distribution; Consistent: Only recenter if closer than a log(log(t)) bound; Lower: Never recenter a model if worse than benchmark."* `Consistent` is the one to report.
4. **The bootstrap is block-based and time-aware** — `StationaryBootstrap` (default), `CircularBlockBootstrap`, `MovingBlockBootstrap` — which is why this family is legitimate on autocorrelated financial returns where an i.i.d. bootstrap would not be. Default `block_size = int(sqrt(T))`; the docstring warns *"In general, this should be provided and chosen to be appropriate for the data."* For QMX, block size should reflect the strategy's average holding period, not `sqrt(T)`.

`seed` accepts an int, a `numpy.random.Generator`, or a `RandomState` — so these tests are reproducible if QMF passes a seed (see §12).

**`MCS` is the underused one for QMX.** It returns a *set* of models that cannot be statistically distinguished from the best. For a prop-firm operator running a small portfolio, "here are the 4 configurations I cannot tell apart" is a far more actionable output than "here is the single best", and it is a natural defence against picking the luckiest point on a plateau.

---

### 5. Harvey & Liu haircut and the general multiple-testing problem

**Primary source.** Harvey & Liu, *"Backtesting"*, **Journal of Portfolio Management** 42(1) (2015); working paper SSRN <https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2345489>; free full text at Duke <https://people.duke.edu/~charvey/Research/Published_Papers/P120_Backtesting.PDF>.

Different machinery, same disease. Harvey & Liu convert a Sharpe ratio to a t-statistic, apply a standard multiple-testing p-value adjustment (Bonferroni, Holm, or Benjamini–Hochberg–Yekutieli), then convert the adjusted p-value back into a "haircut" Sharpe ratio.

Load-bearing findings, quoted from the Duke PDF:

- Under independence, `p^M = 1 − (1 − p^I)^N`. With `p^I = 0.05` and `N = 10`, `p^M = 0.401` — a 5% result becomes a 40% result.
- Worked example: *"assuming there are twenty years of monthly returns (T = 240), an annual Sharpe ratio of 0.75 yields a p-value of 0.0008 for a single test. When N = 200, p^M = 0.15, implying an adjusted annual Sharpe ratio of 0.32… multiple testing with 200 tests reduces the original Sharpe ratio by approximately 60%."*
- **The haircut is non-linear, and this matters for QMX's screening policy:** *"the haircut is almost always more than and sometimes much larger than 50% when the annualized Sharpe ratio is less than 0.4. On the other hand, when the Sharpe ratio is greater than 1.0, the haircut is at most 25%."* They explicitly reject the industry's flat 50% rule of thumb: *"it is a serious mistake to use the usual 50% haircut."*
- Harvey & Liu independently corroborate the López de Prado result: *"only seven trials are needed to obtain a spurious two-year backtest that has an in-sample realized Sharpe ratio of more than 1.0, while the expected out-of-sample Sharpe ratio is zero."* Matches my computed table row (N=7 → 1.92 yr) exactly.
- Their published example run: initial annualised Sharpe 1.000 over 120 months, 100 tests, average correlation 0.4 → haircut Sharpe of **0.232 / 0.262 / 0.438 / 0.298** across the four adjustment methods, i.e. haircuts of **74.6% / 71.3% / 52.0% / 67.3%**.

**Verdict for QMF:** DSR is the better primary statistic (it handles non-normality, which forex strategies need). The Harvey–Liu haircut is a good *secondary* number because it is easier to explain to a non-technical operator: "your Sharpe of 1.0 is really 0.44 after accounting for the search." Both are cheap. Compute both.

**Practical consequence for the operator's `Confirmation` weighting.** The confluence weights over Confirmations are a continuous search space. Every weight vector explored is a trial. If the weights are fitted rather than chosen a priori from a hypothesis, the trial count for that strategy is the number of weight vectors evaluated, and it must enter `N`.

---

### 6. What actually implements DSR / PBO / MinBTL — the licensing reality

**`mlfinlab` is licence-blocked** (established in file 03, restated here because it is the default answer everyone gives). It is not open source; commercial use requires a paid licence from Hudson & Thames. **Do not use, do not vendor, do not copy.**

**`purgedcv` (`eslazarev/purged-cross-validation`) — the find of this file.**

- **PyPI:** `purgedcv` **0.1.3**, uploaded **2026-08-01** (<https://pypi.org/pypi/purgedcv/json>). Licence classifier **MIT**, confirmed by the repo's `LICENSE` and GitHub API `spdx_id: MIT`.
- **GitHub:** <https://github.com/eslazarev/purged-cross-validation>, `pushed_at` **2026-08-01**, 26 stars, not archived.
- **Dependencies:** `numpy>=1.24`, `pandas>=2.0`, `scikit-learn>=1.3`, `scipy>=1.10`. Nothing else. Pure Python, so Windows and Linux install identically. Optional extras only for docs/examples/optuna.
- **Modules** (`src/purgedcv/`): `_purged_kfold.py`, `_walk_forward.py`, `_cpcv.py`, `_embargo.py`, `_purge.py`, `_pbo.py`, `_metrics.py`, `_path_metrics.py`, `diagnostics.py`, `optuna_integration.py`, plus `py.typed`.

**I read `_metrics.py` and `_pbo.py` source directly.** The implementations match the papers:

- `_expected_max_z(n)` computes `(1 − γ)·Φ⁻¹(1 − 1/n) + γ·Φ⁻¹(1 − 1/(n·e))` with `_GAMMA_EM = 0.5772156649015329`, and correctly returns `0.0` at `n = 1` where the formula diverges.
- `minimum_backtest_length(n_trials, target_sharpe=1.0)` returns `(expected_max_z / target_sharpe)²` in **years**. Its own doctest asserts `minimum_backtest_length(10) ≈ 2.5` — matching my independent computation of 2.48 and the AMS paper.
- `probabilistic_sharpe_ratio` uses `stats.kurtosis(arr, bias=False, fisher=False)` — i.e. **kurtosis, not excess kurtosis**, with an explicit `# NOT excess` comment. This is the single most common bug in hand-rolled PSR code; they got it right.
- `_sharpe_moments` uses `std(ddof=0)` (population) for the Sharpe point estimate while PSR uses `sqrt(n−1)` in the numerator — consistent with the paper.
- `effective_n_trials(trial_sharpes, method="autocorr")` exists, addressing the correlated-trials problem from §1.
- `optuna_integration.TrialSharpeRecorder` is an Optuna study callback that accumulates per-trial Sharpes and exposes `var_sharpe()` and `n_trials()` — solving exactly the "where does `V[SR_n]` come from" problem. Its module docstring is candid about why it exists: *"Optuna only stores each trial's objective value, so users hand-roll the bookkeeping every time."* It has **no import-time dependency on Optuna** (duck-typed on `(study, trial)`), so it is safe to import unconditionally.
- `_pbo.py` implements CSCV correctly, including the degenerate-slice guard (`np.ptp(arr) == 0.0 → return 0.0`) that stops a constant return series from producing an infinite Sharpe and winning the in-sample selection.

**Risk:** version 0.1.3, "Development Status :: 3 - Alpha", 26 stars, effectively a single maintainer. That is a real bus-factor problem for a component QMX's integrity depends on.

**Recommendation — and this is a genuine fork in the road:**
- **Option A (recommended):** treat `purgedcv` as a *reference implementation*, and have QMF own ~200 lines implementing PSR, DSR, MinBTL, `effective_n_trials` and CSCV/PBO natively. They are short closed-form formulas plus one combinatorial loop. Test QMF's implementation against `purgedcv` as an oracle in CI. QMF then has zero external dependency on an alpha library for its most safety-critical number, and the formulas cannot silently change under it.
- **Option B:** depend on `purgedcv` directly, pin the exact version, and vendor the source into the repo (MIT permits this with attribution).

Do **not** take the third option of "no implementation, just eyeball the walk-forward curve".

**Other candidates surveyed and rejected.** A GitHub search for `deflated sharpe` / `backtest overfitting CSCV` returns roughly a dozen repositories created in 2026, nearly all 0–7 stars with no test suites (e.g. `mnemox-ai/deflated-sharpe`, Apache-2.0, 7★; `Aliipou/backtest-audit`, no licence). One relatively substantial one, `quantskills/skill-backtest-overfit` (19★), is **GPL-3.0** — study only. None of these is a dependency a trading system should rest on.

---

### 7. Hyperparameter search frameworks

#### 7.1 Optuna — the recommendation

- **PyPI:** **4.9.0**, uploaded **2026-06-01**. Licence classifier **MIT**. `requires_python >=3.9`, claims support through Python 3.14. (<https://pypi.org/pypi/optuna/json>)
- **GitHub:** <https://github.com/optuna/optuna>, `pushed_at` **2026-08-17T02:45:29Z** — commits landing today. **14,668 stars, 16 open issues.** That issue count against that star count is the strongest maintenance signal in this entire file.
- **Install story:** pure Python core, no compiled extension. Identical `pip install optuna` on Windows and Linux. Only `GPSampler` pulls extra weight (`scipy` + CPU `torch`).

**Samplers** (<https://optuna.readthedocs.io/en/stable/reference/samplers/index.html>): `RandomSampler`, `TPESampler`, `GPSampler`, `CmaEsSampler` (backed by the `cmaes` package), `NSGAIISampler`, `NSGAIIISampler`, `GridSampler`, `QMCSampler`, `BruteForceSampler`, `PartialFixedSampler`. `AutoSampler` lives in OptunaHub, not core.

**The noisy-objective question — the one that actually matters here.** A backtest metric is noisy, non-i.i.d., low-signal, and non-stationary. Most samplers implicitly assume a deterministic objective. Reading `optuna/samplers/_gp/sampler.py` directly:

> *"To prevent overfitting, Gamma prior is introduced for kernel scale **and noise variance**"*

and the `deterministic_objective` argument (added v3.6.0, still flagged experimental):

> *"Whether the objective function is deterministic or not. If True, the sampler will fix the noise variance of the surrogate model to the minimum value… **Defaults to False.**"*

So **`GPSampler` with the default `deterministic_objective=False` is the only Optuna sampler that explicitly learns an observation-noise variance.** For a backtest objective that is the theoretically correct choice. Its acquisition function is log-Expected-Improvement (logEHVI for multi-objective), and it uses a Matérn ν=2.5 kernel with ARD. Cost: it fits a GP each trial, so it does not scale to 10⁵ trials — which, given §1, is a feature.

**`WilcoxonPruner` — underrated and near-perfect for QMX.** From `optuna/pruners/_wilcoxon.py`:

> *"This pruner performs the Wilcoxon signed-rank test between the current trial and the current best trial, and stops whenever the pruner is sure up to a given p-value that the current trial is worse than the best one. This pruner is effective for optimizing the mean/median of some (costly-to-evaluate) performance scores over a set of problem instances."*

The listed use cases include *"the k-fold cross-validation score of a machine learning model"*. Map that onto QMX: the "problem instances" are the **CPCV paths**, or the **28 currency pairs**, or the **walk-forward folds**. You call `trial.report(value, instance_id)` per instance and the pruner abandons the candidate on statistical evidence rather than on a threshold. The docstring's own caveat matters: *"In each trial, it is recommended to shuffle the evaluation order, so that the optimization doesn't overfit to the instances in the beginning"* and *"You need to pass the same id for the same instance, otherwise WilcoxonPruner cannot correctly pair the losses across trials."* Full pruner roster: `MedianPruner`, `NopPruner`, `PatientPruner`, `PercentilePruner`, `SuccessiveHalvingPruner`, `HyperbandPruner`, `ThresholdPruner`, `WilcoxonPruner`.

**Storage / resumability** (<https://optuna.readthedocs.io/en/stable/reference/storages.html>): `InMemoryStorage` (default, single process, lost on crash), `RDBStorage` (any SQLAlchemy DB — **SQLite is the right answer for a solo operator**), `JournalStorage` with `JournalFileBackend` or `JournalRedisBackend`, and `GrpcStorageProxy`. For NFS, `JournalFileSymlinkLock` (NFSv2+) and `JournalFileOpenLock` (NFSv3+) are provided. A study with a file-backed storage **resumes after a crash and can be inspected months later** — which, combined with §11, means Optuna's storage *is itself a partial experiment log.

**Parallelism — read the source, not the marketing.** From `optuna/study/study.py`, the `optimize(..., n_jobs=1, ...)` docstring:

> *"`n_jobs` allows parallelization using `threading` and may suffer from Python's GIL. It is recommended to use process-based parallelization if `func` is CPU bound."*

A backtest is CPU-bound. **Therefore `n_jobs` is the wrong knob.** The correct pattern is: create a study on a shared `RDBStorage`/`JournalStorage`, then launch N independent OS processes each calling `study.optimize(..., n_jobs=1)` against the same `study_name`. No server, no scheduler, no Ray. `optuna.study.MaxTrialsCallback` bounds the total across all processes.

**Ask-and-tell** (<https://optuna.readthedocs.io/en/stable/tutorial/20_recipes/009_ask_and_tell.html>): `trial = study.ask()` or `study.ask(distributions)`; `study.tell(trial, value)`, `study.tell(trial_number, value)`, `study.tell(trial, state=optuna.trial.TrialState.PRUNED)`. This is **the API QMF should wrap**, not `study.optimize`. Ask-and-tell means QMF owns the evaluation loop — and therefore owns the point at which it can refuse to evaluate, count the trial against a split's budget, and record the manifest. `study.optimize` inverts control and gives the callback the ability to do whatever it likes.

**Multi-objective:** confirmed in `study.py` — `_is_multi_objective()`, and `best_trials` returns the Pareto front rather than a single winner. `NSGAIISampler`, `NSGAIIISampler` and `GPSampler` (logEHVI) all handle it. **This is the right shape for prop-firm evaluation**, where a strategy is judged on path (max daily loss, trailing drawdown) as well as on return — see §14.

Other confirmed API surface: `enqueue_trial` (seed the search with a human's hypothesis), `add_trial`/`add_trials` (import prior results), `set_user_attr` (attach the split id, the git sha, the per-trial Sharpe), `trials_dataframe()` (export), `stop()`, and `optuna.terminator.Terminator` with `BestValueStagnationEvaluator`.

**Verdict: ADOPT.** MIT, actively developed today, no server, resumable, Windows/Linux identical, and it has the two specific features (noise-aware GP, Wilcoxon pruning over folds) that a noisy backtest objective actually needs.

#### 7.2 Ray Tune

- **PyPI:** `ray` **2.57.0**, uploaded **2026-08-11**. Licence **Apache-2.0**. `requires_python >=3.10`. (<https://pypi.org/pypi/ray/json>)
- **GitHub:** <https://github.com/ray-project/ray>, `pushed_at` **2026-08-17**, 43,536 stars, **3,495 open issues**. Very actively developed; also very large.
- **Windows:** from <https://docs.ray.io/en/latest/ray-overview/installation.html>, *"Ray on Windows is currently in beta"* with documented caveats: *"Multi-node Ray clusters are untested"*; *"Filenames are tricky on Windows and there still may be a few places where Ray assumes UNIX filenames"*; *"Performance on Windows is known to be slower since opening files on Windows is considerably slower"*; *"Windows does not have a copy-on-write forking model, so spinning up new processes can require more memory."* Windows wheels for Python 3.10/3.11/3.12, amd64 only.

**Verdict: AVOID for v1.** Apache-2.0 is fine and the feature set is genuinely superior *at cluster scale*. But QMX is one operator with one Windows machine and cloud sandboxes. Ray's value proposition is multi-node clusters, which is precisely the configuration Ray documents as untested on the operator's primary OS. Adopting Ray means adopting a distributed-systems dependency to solve a problem `joblib` + Optuna-over-SQLite solves. Revisit only if sweeps outgrow a single sandbox.

#### 7.3 Hyperopt — back from the dead, but still not the answer

- **PyPI:** **0.3.0**, uploaded **2026-07-24** — the first release since **0.2.7 on 2021-11-17**, a **4.7-year gap**. (<https://pypi.org/pypi/hyperopt/json>)
- **GitHub:** <https://github.com/hyperopt/hyperopt>, `pushed_at` **2026-08-10**, 7,592 stars, 9 open issues.
- **Licence:** BSD-3-Clause — I read `LICENSE.txt` directly (GitHub API reports `NOASSERTION`; the file is standard BSD-3 © 2013 James Bergstra).
- **Release notes** (<https://github.com/hyperopt/hyperopt/releases>, v0.3.0): *"Lots has changed since the last release in 2021… Hyperopt is now only tested with Python versions >= 3.10. The main thing for most users is that this release brings changes to improve compatibility with modern versions of numpy, simplifying installation."*

**Correction to conventional wisdom:** Hyperopt is **not** dead as of 2026-08-17. It has a new release and active commits. But the 0.3.0 changelog is entirely maintenance — NumPy compatibility, CI modernisation, packaging — not new capability. Its parallelism story is `MongoTrials` (requires a MongoDB) or `SparkTrials` (requires Spark); both are heavier than Optuna's SQLite-file study. No pruning. No multi-objective. **Verdict: AVOID** — not because it is unmaintained, but because Optuna is strictly better at the same job with a lighter install.

#### 7.4 scikit-optimize — dead

- **Upstream GitHub `scikit-optimize/scikit-optimize` is ARCHIVED**, last push **2024-02-23**, 2,829 stars, 318 open issues frozen at archive time. (<https://github.com/scikit-optimize/scikit-optimize>)
- The successor fork `holgern/scikit-optimize` (<https://github.com/holgern/scikit-optimize>) has **24 stars** and last push **2024-06-04** — it published 0.10.2 to PyPI on **2024-06-04** and has done nothing since. **26 months of silence.**
- Licence BSD-3-Clause (moot).

**Verdict: AVOID — dead.** This one matters because `skopt` is still the default answer in a great deal of older quant-finance writing, and Freqtrade itself used it before migrating to Optuna. Anything an LLM agent has memorised about "use `skopt.gp_minimize` for backtest tuning" is out of date.

#### 7.5 Nevergrad

- **PyPI:** **1.0.12**, uploaded **2025-04-23** — **16 months** with no release as of today. (<https://pypi.org/pypi/nevergrad/json>)
- **GitHub:** <https://github.com/facebookresearch/nevergrad>, `pushed_at` **2026-07-24**, 4,202 stars, 141 open issues, MIT, not archived.
- Repo is alive, releases are not. Nevergrad's genuine strength is a very large, well-benchmarked zoo of **gradient-free evolutionary optimisers** — which is directly relevant to the operator's GA request, and its `NGOpt` meta-optimiser auto-selects an algorithm for the budget and space.

**Verdict: OPERATOR DECISION.** MIT so there is no licence risk. Worth a look **only if** the GA lane in §8 needs algorithm variety beyond CMA-ES/NSGA-II that Optuna already exposes. Flag the release stall.

#### 7.6 SMAC3

- **PyPI:** `smac` **2.4.0**, uploaded **2026-04-22**. (<https://pypi.org/pypi/smac/json>)
- **GitHub:** <https://github.com/automl/SMAC3>, `pushed_at` **2026-08-17** (today), 1,242 stars, 125 open issues.
- **Licence:** GitHub reports `NOASSERTION`; I read `LICENSE.txt` directly — **BSD 3-Clause, © 2025 Leibniz University Hannover — Institute of AI**. Permissive.

SMAC's design target is **algorithm configuration** (AutoML, SAT solvers): expensive evaluations, mixed/conditional spaces, multi-fidelity, random-forest surrogate. Technically well suited to noisy objectives, and academically rigorous.

**Verdict: AVOID for v1.** Nothing wrong with it; it is a second Bayesian-optimisation dependency delivering marginal benefit over Optuna's `GPSampler`, with a much smaller ecosystem and a heavier install (ConfigSpace, pyrfr).

---

### 8. Genetic and evolutionary search — the operator's explicit request, and its failure mode

#### 8.1 State the failure mode first

A genetic algorithm over indicator combinations **is** the machine from §1. A modest run — population 100, 50 generations — evaluates **5,000 candidates**. Per §1, the null expects the best of 5,000 independent trials to show a Sharpe near **3.6**, and the MinBTL for a Sharpe of 1.0 at that trial count is roughly **13 years**. The operator has multi-year history for ~28 pairs; if a GA runs per-pair on 5 years of data, **it is mathematically guaranteed to produce a beautiful, worthless strategy on every single pair.**

Worse, a GA violates the independence assumption in the direction that is *hard to correct*: generation N+1 descends from generation N by selection, so the trials are heavily correlated, and applying `N̂ = ρ̂ + (1 − ρ̂)M` requires a `ρ̂` you can only estimate after the fact.

**Therefore the single design rule for the GA lane is: the fitness function must already be deflated.** Do not optimise Sharpe and check DSR afterwards — that is checking the exam after the student has seen the answers. Optimise a quantity that already penalises search: e.g. out-of-sample fold performance from a purged walk-forward, minus the running selection bar. Concretely, one of:

- **Deflated fitness:** `fitness = observed_metric − expected_max_under_null(n_evaluated_so_far, dispersion_of_population_fitness)`. This is computable inside the GA loop with no extra backtests.
- **Fold-median fitness with a Wilcoxon requirement:** score = median across CPCV paths, and disqualify any candidate whose fold scores do not beat a null at some p-value.
- **Path constraints as hard disqualifiers**, not soft penalties: any candidate breaching the prop-firm daily-loss cap on any fold gets fitness `−inf` before anything else is computed.

#### 8.2 The libraries

| Library | Latest / date | Licence | GitHub state (2026-08-17) | Note |
|---|---|---|---|---|
| **DEAP** | 1.4.4 / 2026-04-17 | **LGPL-3.0** (read `LICENSE.txt`: "GNU LESSER GENERAL PUBLIC LICENSE Version 3") | `pushed_at` 2026-04-17, 6,431★, 281 open issues | The reference GP/GA toolkit. Release cadence roughly annual (1.4.2 2025-01, 1.4.3 2025-05, 1.4.4 2026-04). **Copyleft → OPERATOR DECISION.** |
| **PyGAD** | 3.7.0 / 2026-06-05 | **BSD-3-Clause** (read `LICENSE`: standard 3-clause, "Copyright GeneticAlgorithmPython Contributors") | `pushed_at` 2026-07-09, 2,221★, 102 open issues | Simpler API, permissive licence, actively released. |
| **gplearn** | 0.4.3 / 2026-01-07 | **BSD-3-Clause** (read `LICENSE`: "BSD 3-Clause License, Copyright (c) 2015-2026, Trevor Stephens") | `pushed_at` 2026-08-14, 1,874★, 17 open issues | Symbolic regression / genetic programming, scikit-learn-compatible. |

Sources: <https://pypi.org/pypi/deap/json>, <https://github.com/DEAP/deap>; <https://pypi.org/pypi/pygad/json>, <https://github.com/ahmedfgad/GeneticAlgorithmPython>; <https://pypi.org/pypi/gplearn/json>, <https://github.com/trevorstephens/gplearn>.

**On DEAP's licence.** LGPL-3.0 is weak copyleft: QMX may *use* DEAP as an unmodified library in a commercial product provided the user can replace it, but any modification to DEAP itself must be released under LGPL. This is the same class of decision already flagged for NautilusTrader (LGPL-3.0) in file 01, so it is not novel — but it is an operator decision, and PyGAD achieves the same outcome under BSD. **If the operator wants zero copyleft in the tree, use PyGAD.**

**On gplearn's revival.** Release history: 0.4.2 on **2022-05-03**, then nothing until **0.4.3 on 2026-01-07** — a 3.7-year gap, with `pushed_at` 2026-08-14 and only 17 open issues. It is alive again. `requires_python >=3.11`. Its `SymbolicRegressor`/`SymbolicTransformer` evolve *expression trees* over a function set (`add`, `mul`, `log`, `sqrt`, custom functions). Mapped to QMX, the "custom functions" would be QMF indicators and the evolved tree would be a Trigger or Confirmation expression. **This is genuinely the closest existing tool to "genetic algorithms over indicators".** It is also, for exactly that reason, the most dangerous.

**Optuna already ships evolutionary samplers.** `NSGAIISampler`, `NSGAIIISampler` and `CmaEsSampler` are genetic/evolutionary optimisers inside a framework that already has storage, resumability, pruning and trial accounting. For *parameter* evolution (fixed structure, evolving numbers — which is most of the Level/Trigger/Confirmation/Exit surface) **Optuna's NSGA-II is sufficient and adds no new dependency.** A separate GA library is only needed for *structural* evolution (evolving the shape of the rule tree), which is gplearn/DEAP territory.

#### 8.3 Prior art: a live project that evolves trading rules

**`imsatoshi/GeneTrader`** — <https://github.com/imsatoshi/GeneTrader>. **MIT**, **199 stars**, `pushed_at` **2026-07-29**. A GA wrapped around Freqtrade backtests, optimising strategy parameters and pair selection.

This is the most instructive artefact in this section, because its author independently arrived at the guardrails this file recommends. Its README lists, among the features: *"Walk-forward validation: train each fold on its own window, score it out of sample"* and *"Selection bar: how good the best of N candidates would have looked by luck alone."*

I read `strategy/selection_bar.py`. Its module docstring is worth quoting nearly in full because it is the correct mental model, written by a practitioner:

> *"A GA that evaluates 900 candidates and reports the best one has run 900 experiments and published the winner. Some of that winner's score is skill and some is the luck of being the luckiest of 900 draws. This module estimates the luck component… That value is the search's own selection bar, and a winner that does not clear it has not demonstrated anything the search couldn't have produced from noise."*

The implementation is the Bailey/López de Prado expected-maximum formula (`EULER_MASCHERONI = 0.5772156649015329`, Acklam's rational probit approximation, `expected_max(n_trials, dispersion)`), applied **to the GA's own fitness scale rather than to Sharpe** — with an explicitly stated reason:

> *"applied to the quantity this project actually selects on — Final Fitness — rather than to Sharpe. Sharpe is one weighted input to fitness…; deflating it would measure selection pressure that was never applied."*

**That reasoning is correct and QMF must copy it.** If the search selects on a composite score, the deflation must be applied to that composite score's dispersion, not to Sharpe. Deflating the wrong quantity gives a number that looks rigorous and measures nothing.

The file is also honest about its own two violated assumptions — non-independence of GA generations (*"Using the full evaluation count overstates the number of independent draws, which raises the bar — the test is therefore conservative on that axis"*) and non-normality of a bounded weighted-sum fitness — and closes with: *"The real answer to 'is this curve-fitted' is out-of-sample performance… This number is a cheap in-sample screen."* Repo also contains `strategy/walk_forward.py`, `strategy/robustness.py`, and both `optimization/genetic_optimizer.py` and `optimization/optuna_optimizer.py`.

**Everything else in this space is abandoned or trivial.** A GitHub search for genetic-algorithm trading repositories sorted by stars returns, after GeneTrader: `jodhangill/GenTrader` (12★, GPL-3.0, last push 2024-05), `jmberutich/GeneticProgrammingTradingExperiments` (9★, 2019), `gpanterov/genetic_algorithms_trading` (9★, 2015), then a long tail of sub-5-star student projects. **No evidence found** of a maintained, well-tested, permissively licensed framework for evolving trading rules other than GeneTrader.

---

### 9. Freqtrade `hyperopt` — the closest shipped prior art, in depth

**Licence: GPL-3.0** (<https://github.com/freqtrade/freqtrade>, 53,371★, `pushed_at` 2026-08-17, 34 open issues — extremely healthy). **Design study only. No code may be copied into QMX.**

#### 9.1 The parameter type system

From <https://www.freqtrade.io/en/stable/hyperopt/>:

| Type | Meaning |
|---|---|
| `IntParameter` | Integer with upper/lower bounds |
| `DecimalParameter` | Float limited to N decimal places (default 3) |
| `RealParameter` | Unbounded-precision float — *"rarely used due to near-infinite possibilities"* |
| `CategoricalParameter` | Choice from a list |
| `BooleanParameter` | Shorthand for `CategoricalParameter([True, False])` |

Each takes `optimize=True|False` (exclude from search) and `load=True|False` (ignore previous results). A caveat worth stealing: *"setting the `load` option to `False` will mean **backtesting will also use the default value** specified in the parameter and not the value found through hyperoptimisation"* — i.e. the search config leaks into the evaluation config, a class of bug QMF should design out.

**The most transferable idea here is `DecimalParameter`'s deliberate coarseness.** The docs justify it explicitly (repeated three times in `docs/hyperopt.md`, lines 659/701/739): *"To limit the search space further, Decimals are limited to 3 decimal places (a precision of 0.001). This is usually sufficient, every value more precise than this will usually result in overfitted results."* **Coarsening the grid is a first-class overfitting defence, and it is free.** QMF's parameter declarations should default to coarse and require justification to go finer.

#### 9.2 Search spaces

`buy`/`enter`, `sell`/`exit`, `roi`, `stoploss`, `trailing`, `protection`, `trades`, `all`, `default` (= all except trailing/trades/protection), plus user-defined named spaces via `space='custom_name'`. The docs recommend sequential rather than joint optimisation of `trailing`: *"We recommend you to run optimization for the `trailing` hyperspace separately, when the best parameters for other hyperspaces were found, validated and pasted into your custom strategy."*

Mapped to QMX's schema, these spaces are near-isomorphic to **Level / Trigger / Confirmation / Exit**, which is a useful validation that the operator's decomposition is the natural one. Note the trap though: sequential per-space optimisation **multiplies** the trial count while making it look smaller. Three sequential 1,000-trial searches is not 1,000 trials; for deflation purposes it is closer to 3,000.

#### 9.3 The twelve loss functions

`ShortTradeDurHyperOptLoss` (legacy default), `OnlyProfitHyperOptLoss`, `SharpeHyperOptLoss`, `SharpeHyperOptLossDaily`, `SortinoHyperOptLoss`, `SortinoHyperOptLossDaily`, `CalmarHyperOptLoss`, `MaxDrawDownHyperOptLoss`, `MaxDrawDownRelativeHyperOptLoss`, `MaxDrawDownPerPairHyperOptLoss`, `ProfitDrawDownHyperOptLoss`, `MultiMetricHyperOptLoss`.

The interface (`freqtrade/optimize/hyperopt_loss/hyperopt_loss_interface.py`, read directly) is a single static method:

```python
class IHyperOptLoss(ABC):
    timeframe: str
    @staticmethod
    @abstractmethod
    def hyperopt_loss_function(
        *, results: DataFrame, trade_count: int, min_date: datetime, max_date: datetime,
        config: Config, processed: dict[str, DataFrame], backtest_stats: dict[str, Any],
        starting_balance: float, **kwargs) -> float:
        """Objective function, returns smaller number for better results"""
```

**Keyword-only, with `**kwargs` for forward compatibility.** That is a good interface shape for a plugin point QMF will need to expose to LLM authors — it means adding a new input never breaks an existing loss function.

**`MultiMetricHyperOptLoss` is the one to study.** Read in full from source; the returned objective is:

```
−1 × profit_draw_function × log_profit_factor × log_expectancy_ratio × log_winrate_coef × trade_count_penalty
```

with `profit_draw_function = total_profit − (relative_account_drawdown × total_profit) × (1 − DRAWDOWN_MULT)`, `DRAWDOWN_MULT = 0.055`.

Two design lessons:

1. **The trade-count penalty is a genuine guardrail.** `TARGET_TRADE_AMOUNT = 50`; below that, the score is multiplied by `max(1 − |trade_count − 50|/50, 0.1)`. This kills the classic overfit — a "strategy" that took four trades, won all four, and shows an infinite profit factor. **QMF should make this a hard rejection, not a soft multiplier:** below a minimum trade count, the result is not a result. (Related: MinBTL is about *time*; minimum trade count is about *sample*. Both are needed.)
2. **The log-wrapping and the `+ CONST` offsets** (`PF_CONST=1.0`, `EXPECTANCY_CONST=2.0`, `WINRATE_CONST=1.2`) exist to compress unbounded ratios so no single metric dominates the product. Reasonable engineering, but it means the objective scale is arbitrary — which, per GeneTrader's insight in §8.3, is exactly why deflation must be applied to *this* composite's dispersion, not to Sharpe.

#### 9.4 The optimiser under the hood — it is Optuna

From `freqtrade/optimize/hyperopt/hyperopt_optimizer.py` (read directly):

```python
optuna_samplers_dict = {
    "TPESampler": optuna.samplers.TPESampler,
    "GPSampler": optuna.samplers.GPSampler,
    "CmaEsSampler": optuna.samplers.CmaEsSampler,
    "NSGAIISampler": optuna.samplers.NSGAIISampler,
    "NSGAIIISampler": optuna.samplers.NSGAIIISampler,
    "QMCSampler": optuna.samplers.QMCSampler,
}
INITIAL_POINTS = 30
...
return optuna.create_study(sampler=sampler, direction="minimize")
```

Seeding: NSGA-II/III get `seed=random_state, population_size=INITIAL_POINTS`; GP/TPE/CmaEs get `seed=random_state, n_startup_trials=INITIAL_POINTS`; others get `seed=random_state` only. Early stopping via `optuna.terminator.Terminator(BestValueStagnationEvaluator(es_epochs))`.

**Three observations that are decision-relevant for QMF:**

1. **Freqtrade migrated off scikit-optimize onto Optuna.** The largest retail trading framework in existence (53k stars) independently chose the same tool this file recommends. That is a strong signal.
2. **`create_study(direction="minimize")` — single objective, no `storage=`.** The default sampler is `NSGAIIISampler`, a *multi-objective* genetic algorithm, running against a *scalarised single objective*. That is a defensible engineering choice (NSGA-III's diversity preservation still helps) but it throws away the Pareto front, which is exactly what a prop-firm operator needs. **QMF should use `directions=[...]` and keep the front.**
3. **No `storage=` means `InMemoryStorage`.** A Freqtrade hyperopt run that crashes at epoch 900 of 1,000 loses everything, and the study cannot be re-opened later to recover the trial-Sharpe dispersion needed for DSR. **QMF must always pass a storage.**

#### 9.5 Where it fails — the gap QMX exists to fill

I grepped the full 851-line `docs/hyperopt.md` for `overfit`, `out-of-sample`, `validat`, `unseen`. Findings:

- **The word "overfit" appears exactly three times**, all three the same boilerplate about decimal precision.
- **There is no out-of-sample discipline whatsoever.** `--timerange` is presented purely as a speed knob: *"Use the `--timerange` argument to change how much of the test-set you want to use. For example, to use one month of data…"*. Nothing tells the user to hold data back.
- **"Validate backtesting results" means the opposite of validation.** The section (line 836) says: *"To achieve same the results… as during Hyperopt, please use the same configuration and parameters (timerange, timeframe, ...) used for hyperopt for Backtesting."* It is a *consistency* check that the numbers reproduce on **the same data**, and it is followed by a troubleshooting list for when they do not. A user reading only this page would reasonably conclude that re-running the backtest on the training data *is* the validation step.
- **The trial count is never used for anything.** `--epochs` is a budget, never an input to a statistic. There is no DSR, no PBO, no MinBTL, no selection bar. Freqtrade will happily run 10,000 epochs on two years of data and print the winner in green.
- **Reproducibility is addressed, and reasonably**: *"If you have not changed anything in the command line options, configuration, timerange, Strategy and Hyperopt classes, historical data and the Loss Function — you should obtain same hyper-optimization results with same random state value used."* Note the length of that conditional list — it is, in effect, an informal run manifest (see §11).
- Windows note in the docs: colour output is disabled on Windows natively; they suggest WSL.

**Freqtrade has excellent search ergonomics and no epistemics.** The parameter system, the loss-function plugin point, and the space decomposition are all worth imitating. The absence of trial accounting is the defect QMF must not inherit.

Worth noting as adjacent prior art: Freqtrade ships `freqtrade/optimize/analysis/lookahead.py` and `recursive.py` — automated **look-ahead bias detection** and **recursive-indicator detection** tools. That is a genuinely good idea (an automated check that a strategy's signals do not change when future data is withheld) and is complementary to everything in this file. **UNVERIFIED** in detail — I did not read these two modules.

---

### 10. LEAN and vectorbt — briefer prior art

#### 10.1 QuantConnect LEAN

<https://github.com/QuantConnect/Lean>, **Apache-2.0**, 21,240★, `pushed_at` 2026-08-14 — healthy and permissively licensed, unlike Freqtrade. Docs: <https://www.quantconnect.com/docs/v2/lean-cli/optimization/deployment>.

- **Parameters** are declared as project-level parameters (not code constants), and the optimiser is asked which to vary. Same principle as Freqtrade's `IntParameter` — the search space is *declared*, not inferred.
- **Two strategies:** `GridSearchOptimizationStrategy` (*"runs through all possible combinations of parameters"*) and `EulerSearchOptimizationStrategy` (*"performs an Euler-like [search] which gradually works towards smaller optimizations"*). Both are naive relative to Optuna's samplers.
- **Targets:** eight predefined, minimise or maximise — Sharpe Ratio, Compounding Annual Return, **Probabilistic Sharpe Ratio**, Drawdown. **LEAN ships PSR as a first-class optimisation target.** That is the closest any mainstream retail platform gets to the statistics in §2, and it is still only PSR, not DSR — it corrects for non-normality and sample length but **not for the number of trials the optimiser itself just ran**. Optimising *for* PSR while ignoring `N` is arguably worse than not having it, because it looks rigorous.
- **Constraints** filter results with relational operators, e.g. `Drawdown <= 0.25`, discarding combinations that breach. **This is the right shape for prop-firm rules** and QMF should have the same feature — but as a *pre-registered* constraint, not a post-hoc filter.
- **Nodes:** cloud optimisation runs on 1–12 parallel "optimization nodes" (O2-8 = 2 cores/8 GB up to O8-16 = 8 cores/16 GB), with an estimated backtest count, batch time and **cost** shown before execution. The cost preview is a nice operator-facing touch worth copying.

#### 10.2 vectorbt

Licensing already ruled in file 01: **Apache-2.0 plus Commons Clause**, which forbids selling a product that is primarily the software. Since QMX may ship commercially, vectorbt is a **design reference only**.

Its parameter approach (<https://vectorbt.dev/api/utils/params/>) is a pure Cartesian-product model: `create_param_product(param_list)` — *"Make Cartesian product out of all params in `param_list`"* — plus `create_param_combs(op_tree)` for arbitrary nested combination trees, `broadcast_params`, `flatten_param_tuples`. `IndicatorFactory.run(..., param_product=True)` then evaluates the whole grid vectorised across a third array dimension.

**The lesson is a warning.** vectorbt's grid model is extremely fast and therefore extremely dangerous: the ergonomic default is "evaluate every combination", which maximises `N` by construction and produces a heat-map whose bright spot the user is invited to read off. Per §1, on 5 years of data a grid of more than ~45 *effectively independent* points has already exhausted the evidence budget. **QMF must never make exhaustive grid search the ergonomic default.** If a grid is offered at all, the API should require the caller to state the trial budget up front and should report the selection bar alongside the heat map.

---

### 11. Experiment tracking and reproducibility

#### 11.1 The tools

| Tool | Latest / date | Licence | State (2026-08-17) | Offline / self-host |
|---|---|---|---|---|
| **MLflow** | 3.15.1 / 2026-08-03 | Apache-2.0 | <https://github.com/mlflow/mlflow> `pushed_at` 2026-08-17, 27,541★, 2,034 open issues | **Yes, fully.** Local `./mlruns` file store with no server at all; or SQLite backend; or a server. |
| **Weights & Biases** | client `wandb` 0.28.2 / 2026-08-12 | **Client MIT**; hosted service proprietary | <https://github.com/wandb/wandb> `pushed_at` 2026-08-15, 11,233★ | Self-hosted server repo <https://github.com/wandb/server> is MIT-licensed *deployment tooling*; the docs state a **W&B trial or enterprise licence key is required** to configure the server, and Dedicated Cloud starts around **$2,000/month**. Standard cloud: Free / Pro ~$60/mo / Enterprise. |
| **Neptune** | `neptune` 1.14.0.post2 / 2026-03-17 | Apache-2.0 | **`neptune-client`, `neptune-api` and `neptune-query` repos are all ARCHIVED on GitHub.** A `neptune-exporter` repo exists (pushed 2026-03-03). | Product pivoted to "Neptune Scale" for large-scale foundation-model training. |
| **Aim** | 3.29.1 / 2025-05-08 | Apache-2.0 | <https://github.com/aimhubio/aim> 6,234★, 468 open issues. `pushed_at` 2026-08-16 but the **last substantive commits are 2025-12-31 (a CI permissions fix) and 2025-06-26**; last release **15 months ago**. | Local-first by design. |

Sources: <https://pypi.org/pypi/mlflow/json>, <https://pypi.org/pypi/wandb/json>, <https://pypi.org/pypi/neptune/json>, <https://pypi.org/pypi/aim/json>, plus the GitHub API for each; MLflow tracking docs <https://mlflow.org/docs/latest/ml/tracking/>; W&B self-managed docs <https://docs.wandb.ai/guides/hosting/hosting-options/self-managed/>.

**Verdicts.** **Neptune: AVOID** — the client the operator would import is archived; an exporter repo exists, which is what a vendor ships when customers need to leave. **Aim: AVOID** — 15 months without a release, 468 open issues; the "local-first, no server" positioning is attractive but a stalled dependency is worse than no dependency. **W&B: AVOID** — the client is MIT but the value is in the hosted service; a solo operator with proprietary strategy parameters should not default to shipping them to a vendor, and the self-hosted path needs a commercial licence. **MLflow: OPERATOR DECISION, later** — genuinely free, genuinely self-hostable, genuinely maintained, and Apache-2.0.

#### 11.2 The actual answer for a solo operator: a run-manifest directory

**Recommendation: do not stand up a tracking server for version one.** MLflow's local mode writes to `./mlruns` with no server (<https://mlflow.org/docs/latest/ml/tracking/>: *"MLflow records metadata and artifacts for each run to a local directory, `mlruns`"*), which is already close to a manifest directory — but it brings a large dependency, a schema QMF does not control, and a UI that has to be run to read anything. The operator is non-technical and reads diagrams, not dashboards.

**What is actually required is that a result be re-derivable six months later.** That is a *content* requirement, not a tool requirement. The minimum manifest — one immutable JSON/TOML file per experiment, in a directory that is itself version-controlled or content-addressed:

| Field | Why it is non-negotiable |
|---|---|
| `experiment_id` | Content hash of everything below; the primary key. |
| `code_version` | Git commit SHA of QMF **plus a dirty flag**. A dirty tree must either refuse to run or record the full diff. A commit SHA on a dirty tree is a lie. |
| `qmf_version`, `qml_version` | Released versions, for the case where the repo is gone. |
| `split_id` | **The only permitted way to name data** (ratified in file 02). Never a date range. |
| `split_registry_version` | Splits can be edited; a `split_id` alone is not enough if the registry mutated. |
| `data_fingerprint` | Hash of the Parquet partition set actually read — file paths + sizes + mtimes, or better, per-file content hashes. Catches silent data revisions from the broker. |
| `parameters` | The full resolved parameter set, including defaults that were not searched. |
| `search_config` | Sampler name, sampler seed, trial budget, pruner, objective definition(s) and directions. |
| `seeds` | Every seed: Python `random`, NumPy `SeedSequence` entropy, any ML library, the bootstrap seed passed to `arch`. |
| `environment` | Python version, OS, CPU arch, **exact pinned dependency set** (a `uv.lock` / `requirements.txt` hash), and **thread-count environment variables** (see §12). |
| `n_trials_this_run` | The raw evaluation count. |
| `n_trials_cumulative_on_split` | **The running total against this `split_id`** — see §14. |
| `var_sharpe` | Dispersion of the metric across trials. Required for DSR; irrecoverable if not captured at run time. |
| `results` | The metric(s), plus the equity/return series or a pointer to it. |
| `overfit_stats` | DSR, PBO, PBO slope, MinBTL vs actual length, SPA consistent p-value, minimum trade count. |
| `verdict` | PASS / FAIL against pre-registered thresholds, computed by QMF, not by the caller. |

**Two properties matter more than the field list:**

1. **The manifest is written by QMF, not by the caller.** An LLM-authored caller must have no way to write a manifest by hand or to omit a field. If `n_trials` can be typed in, it will eventually be typed in wrong.
2. **The manifest is append-only and immutable.** Deleting a failed experiment is how a trial count gets laundered. Failed experiments are the most valuable rows in the table, because they are the denominator.

**When to graduate to MLflow:** when the operator wants to compare runs visually across months and the JSON directory has stopped being browsable, or when a second person joins. Not before. Migration from a well-specified manifest directory into MLflow is a script; migration out of a half-used tracking server is a project.

---

### 12. Determinism and seeding — what actually makes a backtest bit-reproducible

Reproducibility is a stronger claim than most people realise, and QMX has a specific, documented landmine.

**12.1 The DuckDB problem — this one is real and QMX-specific.**

DuckDB's own operations manual (<https://duckdb.org/docs/current/operations_manual/non-deterministic_behavior>) documents that result order is not guaranteed — *"SQL uses set semantics, which allows results to be returned in a different order"* — with causes listed as multi-threaded execution, different compilers, operating systems, and hardware architectures. Crucially it also documents that **floating-point aggregates are affected**: functions such as `stddev` and `corr` may produce varying results under multi-threading due to floating-point inaccuracies.

**`stddev` is the denominator of the Sharpe ratio.** A Sharpe computed by DuckDB across threads is not bit-reproducible. Documented workarounds: `SET threads = 1`, always use an explicit `ORDER BY` (or `ORDER BY ALL`), and `list_sort()` for array results.

**Concrete QMF practice:** every DuckDB connection opened for a *metric* computation sets `threads = 1` and every query that feeds a downstream computation carries an explicit `ORDER BY`. Bulk data *loading* can stay multi-threaded because it is followed by a deterministic sort. Record the thread setting in the manifest.

**12.2 NumPy RNG — pin the version, do not trust the stream.**

Per **NEP 19** (<https://numpy.org/neps/nep-0019-rng-policy.html>): `RandomState` maintains strict stream-compatibility; the newer `Generator` **does not** — *"breaking stream-compatibility in order to introduce new features or improve performance will be allowed with caution… on `X.Y` releases, never `X.Y.Z`."* Only a small subset of `BitGenerator` methods (`bytes()`, `integers()`, `random()`) are strictly stream-stable. The NEP's own conclusion is that cross-version reproducibility must come from **pinning versions**, not from the RNG policy: *"Trying to maintain stream-compatibility for our random number distributions does not help reproducible research."*

**Consequence:** "same seed" is only a reproducibility claim *conditional on a pinned NumPy version*. The environment pin in the manifest is not bureaucracy; it is load-bearing.

**12.3 The concrete practices**

1. **One root seed per experiment; derive everything else.** Use `numpy.random.SeedSequence(root_seed).spawn(k)` to produce independent child streams for each worker/fold/trial. Never let workers call `default_rng()` with no argument, and never let two workers share a stream. Record the root seed and the spawn key structure.
2. **Seed every library that has one:** Python `random.seed`, NumPy per above, `PYTHONHASHSEED` set as an environment variable *before interpreter start* (setting it inside the process is too late — it governs `str`/`bytes` hash randomisation and therefore set/dict iteration order in some code paths), plus any ML library.
3. **Seed the statistics too.** `arch`'s `SPA`/`StepM`/`MCS` all accept `seed=`; without it the bootstrap p-value moves between runs and a marginal result flips.
4. **Pin BLAS/OpenMP thread counts** (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`, `POLARS_MAX_THREADS`) and record them. Floating-point addition is not associative, so a threaded reduction changes the *order* of summation and therefore the last bits of any mean, variance or cumulative-return series. On a long return series those last bits can compound into a visible difference.
5. **Make event ordering total, not partial.** This is the one that silently ruins trading backtests. When two events share a timestamp — a stop and a target both touched within the same bar; two pairs' signals on the same minute; a fill and a new signal at the same millisecond — the outcome depends on iteration order. **QMF must define a total order** (timestamp, then a documented event-type priority, then a stable instrument key, then a monotonic sequence number) and never rely on the order a dict, a set, a `groupby`, or a multi-threaded query happened to produce. This also covers the partial-fill case: a partially-filled order and a subsequent signal must have a defined relative order.
6. **Parallel execution must not change results, only wall-clock.** The test for this is mechanical and should be in CI: run the same experiment with 1 worker and with N workers and assert bit-identical outputs. If they differ, the parallelism is leaking into the result. Note that reductions performed *across* workers (summing partial results) reintroduce ordering sensitivity — sum in a fixed, sorted worker order.
7. **A determinism regression test in CI.** One canonical experiment, one pinned environment, one expected output hash. This is the only thing that keeps determinism true after six months of dependency upgrades.

**Honest caveat:** *bit*-identical reproduction across different machines (Windows dev box vs Linux VPS vs cloud sandbox, different CPU generations, different BLAS builds) is very hard and may not be worth chasing. A more achievable and still-defensible standard is **bit-identical on the same pinned environment, and tolerance-identical (e.g. metrics agree to 1e-9) across environments**, with the tolerance itself asserted in CI. **The operator should decide which standard QMX commits to** — see Open Questions.

---

### 13. Compute orchestration for parameter sweeps

**The honest baseline: a modern desktop CPU runs a very large number of backtests.** Before adopting any orchestration layer, the question is whether one machine plus `joblib` is enough. For most of QMX's sweeps it will be.

| Option | Latest / date | Licence | Verdict for QMX |
|---|---|---|---|
| `multiprocessing` (stdlib) | — | PSF | Works, but `spawn` on Windows re-imports the module in every worker; every argument must be picklable. Usable, unpleasant. |
| **`joblib`** | 1.5.3 / 2025-12-15 (<https://pypi.org/pypi/joblib/json>) | BSD-3-Clause; <https://github.com/joblib/joblib> `pushed_at` 2026-08-17, 4,383★ | **ADOPT.** The `loky` backend handles Windows `spawn` and worker crashes properly, and `Parallel(n_jobs=…)` is a one-line change. This is the local sweep answer. |
| **Ray** | 2.57.0 / 2026-08-11 | Apache-2.0 | **AVOID for v1** — see §7.2; beta on Windows, multi-node untested there. |
| **Dask** | 2026.7.1 / 2026-07-14 (<https://pypi.org/pypi/dask/json>) | BSD-3-Clause; <https://github.com/dask/dask> `pushed_at` 2026-08-10, 13,891★ | **AVOID for v1.** Healthy and permissive, but its strength is out-of-core *dataframes* — a problem DuckDB + Polars already solve for QMX (file 02). Adopting Dask for task parallelism alone duplicates `joblib`. |
| **Modal** | `modal` 1.5.4 / 2026-08-12 (<https://pypi.org/pypi/modal/json>) | **Client Apache-2.0** (<https://github.com/modal-labs/modal-client>, `pushed_at` 2026-08-14); **service is proprietary and hosted** | **OPERATOR DECISION — and probably yes.** See below. |

**Modal, assessed against what the operator actually needs.** Pricing (<https://modal.com/pricing>): Starter plan **$0/month with $30/month of free credits**; per-second billing — CPU **$0.0000131/core/sec** (minimum 0.125 cores/container), memory **$0.00000222/GiB/sec**; Sandboxes/Notebooks billed higher at **$0.00003942/core/sec**; GPUs from T4 at $0.000164/sec to B300 at $0.001972/sec; volume storage **$0.09/GiB/month with 1 TiB/month free**. Starter allows **100 concurrent containers**; Team ($250/mo, $100 credits) allows 5,000. No minimum commitment.

- **Can Python functions be shipped to it?** Yes — that is the core model: decorate a function with `@app.function(...)` and Modal builds the image and runs it remotely.
- **Can data be mounted?** Yes, via Volumes (<https://modal.com/docs/guide/volumes>): `modal volume create my-volume`, then `vol = modal.Volume.from_name("my-volume")` and `@app.function(volumes={"/data": vol})`. Upload via `modal volume put` or `vol.batch_upload()` with `put_file` / `put_directory`.
- **The one gotcha that matters for QMX's data layout.** V1 volumes cap at **500,000 inodes** and performance degrades past **50,000 files**, with attachment latency *"scal[ing] linearly with the number of files in the Volume."* V2 volumes (beta) lift this but cap a single directory at 262,144 files. **Hive-partitioned Parquet for 28 pairs across multiple years and timeframes can easily exceed 50,000 files.** Mitigation: ship coarser partitions (fewer, larger Parquet files) to Modal than the local research layout uses, or use object storage rather than a Volume for the raw archive. **This is a concrete design constraint on the sweep pipeline, not a footnote.**
- Concurrent readers are fine; concurrent writes to the same file are last-write-wins.
- **Free-tier arithmetic:** $30/month of credits at $0.0000131/core/sec buys roughly 636 core-hours/month. If a backtest takes 10 core-seconds, that is on the order of 200,000+ backtests per month within the free credits — which is a delightful number and, per §1, also a warning. The credits will not be the binding constraint; **the evidence budget will be.**

**Should QMF build distributed backtest orchestration?** NautilusTrader — a production-grade engine with a real team — says no, in its `ROADMAP.md` (<https://github.com/nautechsystems/nautilus_trader/blob/develop/ROADMAP.md>), quoted verbatim under **"Out of scope"**:

> *"Distributed or massively parallel backtesting orchestration: externally orchestrated workflows are technically compatible, but a built-in distributed runner is beyond the project's current scope."*

and, on the immediately following line:

> *"Integrated hyper-parameter optimization or built-in AI/ML tooling: users should integrate their own optimization frameworks tailored to their needs."*

**QMF should agree with the first and disagree with the second.** Nautilus is right that a distributed runner is not a small team's job — QMF should use `joblib` locally and Modal remotely and own neither scheduler. But Nautilus's second exclusion is a decision made for a *library that does not know its users*. QMF **does** know its user, and the whole thesis of this file is that letting each user bring their own optimisation framework is how you get 53,000 Freqtrade users optimising 10,000 epochs on two years of data with no deflation. **QMF must own the optimisation surface precisely because Nautilus correctly declines to.**

---

### 14. What an "experiment" should be as a first-class QMF object

This is the design question the operator most needs answered, so it gets stated as a specification rather than a discussion.

#### 14.1 The premise

File 02 ratified that **IS/OOS is data, not code**: `qmf.data.load(split_id=...)` is the only entry point and never accepts raw dates, with embargo windows as first-class rows in a split registry. That rule stops one failure mode (accidentally training on test data). It does **not** stop the failure mode this file is about: **legitimately calling the correct OOS split, over and over, until something passes.** Every one of those calls is honest, correctly purged, correctly embargoed — and collectively they destroy the split.

An out-of-sample window is a **consumable resource**. It has a finite amount of evidence in it and each look spends some. §1 gives the exchange rate: 5 years of data buys 45 independent looks at a Sharpe-1.0 threshold. **QMF must model this as a budget with a ledger, because nothing else will.**

#### 14.2 `Experiment` — the required record

An `Experiment` is an immutable, QMF-constructed record. Beyond the manifest fields in §11.2, it must carry:

- **`hypothesis`** — free text, **required, non-empty, recorded before the run.** The operator's research lane starts from papers, videos and conversations; this is where that provenance lands. It also creates the audit trail that distinguishes "I had a reason" from "I tried everything."
- **`pre_registered_thresholds`** — the pass/fail bar, **recorded before results exist**: minimum DSR, maximum PBO, minimum trade count, maximum drawdown, and prop-firm path constraints (daily loss cap, trailing drawdown). Post-hoc threshold adjustment is the most common form of self-deception and must be structurally impossible.
- **`trial_budget`** — the maximum number of evaluations, declared up front. QMF computes and displays `E[max metric | budget]` **before the run starts**, so the operator sees the bar he must clear before he has any emotional attachment to a result.
- **`objective_spec`** — the metric(s) and direction(s), as data. Not a callable the LLM author can quietly redefine mid-search.
- **`split_id` + `split_registry_version`**, never dates.
- **`parent_experiment_id`** — if this run refines a previous one, the lineage is explicit and **the trial counts chain**. A "small follow-up search" that inherits a 5,000-trial parent has 5,000 trials in its denominator, not 50.

#### 14.3 What the API must refuse

These are **errors, not warnings.** A warning is a suggestion, and an LLM author that reads a warning and proceeds has done nothing wrong from its own perspective.

1. **Refuse raw dates.** Already ratified. `load(start=..., end=...)` does not exist.
2. **Refuse an evaluation on an OOS split whose budget is exhausted.** Raise `SplitBudgetExhausted` with the ledger attached. There must be **no `force=True`**. The only way to get more budget is a deliberate, separately-recorded operator override that itself lands in the ledger and permanently marks every subsequent result derived from that split.
3. **Refuse to run without a `hypothesis` and `pre_registered_thresholds`.**
4. **Refuse to return an unqualified metric.** The return type of an experiment is not a float. It is a result object carrying the metric *and* `n_trials`, `n_trials_cumulative_on_split`, DSR, PBO, MinBTL-vs-actual and the verdict. If a caller wants the Sharpe, it must reach through an object that also carries the deflation. Make the naked number inaccessible.
5. **Refuse to run on a dirty git tree** unless the full diff is captured into the manifest.
6. **Refuse to delete or mutate an experiment record.** Append-only. Superseding is a new record with a `supersedes` pointer.
7. **Refuse to accept a caller-supplied trial count.** QMF counts. The caller does not report.
8. **Refuse to promote a strategy whose OOS evaluation was preceded by fewer IS trials than declared** — i.e. detect and reject the pattern where a caller runs a huge undeclared IS search, then declares a small budget for the record.

#### 14.4 Making "you have burned this window N times" countable

The mechanism is a **split budget ledger**: one append-only table keyed by `split_id`, with one row per evaluation, each row recording `experiment_id`, timestamp, `n_trials`, the metric family evaluated, and a correlation fingerprint of the parameter set.

Rules:

- **Every evaluation writes a row before it returns a result.** Not after — a crashed run that saw the data has still spent the budget.
- **The budget is derived, not chosen.** `budget(split_id) = N_max` such that `MinBTL(N_max, SR*) ≤ length_of_split_in_years`, with `SR*` the pre-registered threshold. From §1: a 5-year OOS split at `SR* = 1.0` has a budget of **45**. At `SR* = 2.0` it is **~1,600** — which is the honest reason to hold strategies to a high bar rather than a low one.
- **The spend is in *effective* trials, not raw ones.** Apply `N̂ = ρ̂ + (1 − ρ̂)·M` using the correlation between the current parameter set and previously evaluated ones. A genuinely novel strategy family spends more than a nudge of one lookback period. This is the mechanism that makes the budget *fair* rather than merely restrictive — without it, every operator will (correctly) feel the budget is absurd.
- **The ledger is per-split, and splits are cheap.** The escape valve is not "raise the budget", it is "the split registry has more splits" — walk-forward folds, different pairs, different eras. Each has its own budget. This is what makes the discipline liveable, and it is why file 02's split registry is the right foundation.
- **A dashboard the operator reads at a glance:** one row per split, a bar showing budget consumed, red when exhausted. That is the diagram the operator wants; the ledger is what makes it truthful.

#### 14.5 Three layers, and where searching is allowed

- **Explore (unlimited).** A dedicated exploration split, or synthetic/bootstrapped data. Search as hard as you like. Nothing here may be reported as a result, and QMF should tag every artefact accordingly.
- **Validate (budgeted).** The purged walk-forward / CPCV splits. Every evaluation spends budget. This is where DSR, PBO and SPA are computed.
- **Confirm (once).** A final holdout split with a budget of **1**, ideally the most recent period, ideally not even loadable until the strategy has passed Validate. One look. Ever.

#### 14.6 Prop-firm evaluation is multi-objective by construction

The mandate says a strategy is judged on **path**, not on final return. Daily loss caps and trailing drawdown are path properties. Therefore:

- The objective is a **vector**, not a scalar — Optuna's `create_study(directions=[...])` with `best_trials` returning the Pareto front (§7.1). Freqtrade's choice to scalarise (§9.4) is the thing not to copy.
- **Path constraints are hard, pre-registered disqualifiers evaluated before the objective.** A candidate that breaches the daily loss cap on any fold is not "penalised", it is not a candidate. This has a pleasant side effect: disqualified candidates arguably should not count against the trial budget in the same way, since they were rejected by a rule rather than selected by a metric — **though this is genuinely arguable and belongs in Open Questions.**
- The reported result should include the **worst-fold path metrics**, not the average. Prop-firm rules are evaluated on the worst day, not the mean day.
- `MCS` (§4) fits this well: report the *set* of configurations that cannot be statistically separated, and let the operator choose within it on grounds (simplicity, robustness, intuition) that a metric cannot capture.

#### 14.7 What the LLM author sees

The constrained surface the operator wants should expose roughly: `qmf.experiment.propose(hypothesis, strategy_spec, search_space, split_id, thresholds, budget) -> Experiment`, then `experiment.run() -> ExperimentResult`. The author declares a search space; it does not write a loop. It cannot call the backtester directly, cannot see a raw date, cannot see a naked float, and gets an exception rather than a result when the budget is gone.

The corollary is that **QMF must wrap Optuna's ask-and-tell (§7.1), not `study.optimize`.** With ask-and-tell, QMF owns the loop and therefore owns the refusal point. With `optimize(objective)`, the objective function is the caller's code and QMF has handed away control at the exact moment it needs to exercise it.

---

## Summary table

Maintenance state and versions verified **2026-08-17** via the GitHub API (`pushed_at`, `archived`) and PyPI JSON upload timestamps.

| Library / tool | Latest version | Last release | Licence | Maintenance (2026-08-17) | Verdict |
|---|---|---|---|---|---|
| **Optuna** | 4.9.0 | 2026-06-01 | MIT | `pushed_at` 2026-08-17, 14,668★, 16 open issues | **ADOPT** — search framework |
| **arch** | 8.0.0 | 2025-10-21 | Permissive NCSA/BSD (read `LICENSE.md`) | `pushed_at` 2026-08-10, 1,551★ | **ADOPT** — SPA / StepM / MCS |
| **joblib** | 1.5.3 | 2025-12-15 | BSD-3-Clause | `pushed_at` 2026-08-17, 4,383★ | **ADOPT** — local sweep parallelism |
| **purgedcv** | 0.1.3 | 2026-08-01 | MIT | `pushed_at` 2026-08-01, 26★, alpha | **OPERATOR DECISION** — adopt-and-pin, or use as reference implementation and have QMF own the formulas (recommended) |
| **Modal** (`modal` client) | 1.5.4 | 2026-08-12 | Client Apache-2.0; service proprietary/hosted | `pushed_at` 2026-08-14 | **OPERATOR DECISION** — good fit for cloud sweeps; note the 50k-file Volume limit vs Hive-partitioned Parquet |
| **PyGAD** | 3.7.0 | 2026-06-05 | BSD-3-Clause | `pushed_at` 2026-07-09, 2,221★ | **OPERATOR DECISION** — only if structural GA is needed beyond Optuna's NSGA-II/CMA-ES |
| **gplearn** | 0.4.3 | 2026-01-07 | BSD-3-Clause | `pushed_at` 2026-08-14, 1,874★; revived after a 3.7-yr gap | **OPERATOR DECISION** — closest tool to "GA over indicators"; highest overfitting risk in this file |
| **DEAP** | 1.4.4 | 2026-04-17 | **LGPL-3.0** | `pushed_at` 2026-04-17, 6,431★ | **OPERATOR DECISION** — copyleft; PyGAD does the job under BSD |
| **Nevergrad** | 1.0.12 | 2025-04-23 (**16 mo**) | MIT | `pushed_at` 2026-07-24, 4,202★; releases stalled | **OPERATOR DECISION** — only for optimiser variety |
| **MLflow** | 3.15.1 | 2026-08-03 | Apache-2.0 | `pushed_at` 2026-08-17, 27,541★ | **OPERATOR DECISION — defer.** Adopt when a manifest directory stops being enough |
| **SMAC3** (`smac`) | 2.4.0 | 2026-04-22 | BSD-3-Clause (read `LICENSE.txt`) | `pushed_at` 2026-08-17, 1,242★ | **AVOID** — healthy, but redundant with Optuna `GPSampler` |
| **Ray / Ray Tune** | 2.57.0 | 2026-08-11 | Apache-2.0 | `pushed_at` 2026-08-17, 43,536★, 3,495 open issues | **AVOID (v1)** — Windows support is *beta*, multi-node untested there |
| **Dask** | 2026.7.1 | 2026-07-14 | BSD-3-Clause | `pushed_at` 2026-08-10, 13,891★ | **AVOID (v1)** — DuckDB/Polars already cover its strength |
| **Hyperopt** | 0.3.0 | 2026-07-24 | BSD-3-Clause (read `LICENSE.txt`) | `pushed_at` 2026-08-10, 7,592★; **revived after 4.7 yrs** | **AVOID** — alive, but strictly dominated by Optuna |
| **Weights & Biases** | `wandb` 0.28.2 | 2026-08-12 | Client MIT; service proprietary | `pushed_at` 2026-08-15, 11,233★ | **AVOID** — hosted-first; self-host needs a commercial licence key |
| **Aim** | 3.29.1 | 2025-05-08 (**15 mo**) | Apache-2.0 | 6,234★, 468 open issues; last substantive commit 2025-12-31 | **AVOID** — stalled |
| **scikit-optimize** | 0.10.2 | 2024-06-04 | BSD-3-Clause | **Upstream repo ARCHIVED 2024-02-23**; fork `holgern/scikit-optimize` (24★) silent since 2024-06-04 | **AVOID — DEAD** |
| **Neptune** | `neptune` 1.14.0.post2 | 2026-03-17 | Apache-2.0 | **`neptune-client`, `neptune-api`, `neptune-query` all ARCHIVED**; product pivoted to Neptune Scale | **AVOID — ABANDONED for this use case** |
| **mlfinlab** | — | — | **Commercial licence required** | (per file 03) | **AVOID — LICENCE-BLOCKED** |
| **Freqtrade `hyperopt`** | — | — | **GPL-3.0** | `pushed_at` 2026-08-17, 53,371★ | **STUDY ONLY** — best-in-class ergonomics, zero epistemics |
| **LEAN Optimizer** | — | — | Apache-2.0 | `pushed_at` 2026-08-14, 21,240★ | **STUDY ONLY** — good constraint model; PSR target without trial-count correction |
| **vectorbt** param grid | — | — | Apache-2.0 **+ Commons Clause** | (per file 01) | **STUDY ONLY — cautionary.** Exhaustive grid as the ergonomic default is the wrong default |
| **GeneTrader** | — | — | MIT | `pushed_at` 2026-07-29, 199★ | **STUDY — recommended read.** Its `selection_bar.py` is the guardrail QMF needs, correctly reasoned |

---

## Recommendation

**The smallest adoptable stack:**

```
Search          Optuna (MIT)  — ask-and-tell, wrapped by QMF, never optimize()
                              — GPSampler for noisy objectives; NSGA-II for multi-objective
                              — WilcoxonPruner over CPCV paths / pairs
                              — RDBStorage on SQLite so every study resumes and is auditable
Statistics      arch (permissive) — SPA (read the "Consistent" p-value), StepM, MCS
                QMF-owned         — PSR, DSR, MinBTL, effective_n_trials, PBO via CSCV
                                  — validated in CI against purgedcv (MIT) as an oracle
Splitting       existing (file 03) — sklearn TimeSeriesSplit(gap=), skfolio WalkForward,
                                     skfolio CombinatorialPurgedCV; CSCV is CPCV at n_test=S/2
Recording       QMF-owned run-manifest directory. Append-only. No tracking server in v1.
Parallelism     joblib (BSD) locally; multiple processes against one Optuna storage
Cloud           Modal (client Apache-2.0) for heavy sweeps — mind the 50k-file Volume limit
```

**What QMF must own outright — this is the non-negotiable list:**

1. **The four overfitting numbers**, computed automatically and attached to every result: **DSR, PBO (+ its IS→OOS slope), MinBTL-vs-actual-length, and the SPA `Consistent` p-value.** Plus two sanity gates: **minimum trade count** and **worst-fold path metrics**.
2. **The `Experiment` object** — immutable, QMF-constructed, carrying hypothesis, pre-registered thresholds, declared trial budget, `split_id`, seeds, environment, and lineage.
3. **The split budget ledger** — append-only, per-`split_id`, spending *effective* trials via `N̂ = ρ̂ + (1 − ρ̂)M`, with the budget derived from MinBTL rather than chosen, and **`SplitBudgetExhausted` raised as an error with no `force=True`**.
4. **A result type that has no naked float.** The metric is only reachable through an object that also carries the deflation and the verdict.
5. **The determinism contract** — pinned seeds, pinned thread counts, `SET threads = 1` for metric queries, a total event ordering, and a CI test asserting 1-worker and N-worker runs are bit-identical.
6. **The three-layer split discipline** — Explore (unlimited, unreportable) / Validate (budgeted) / Confirm (budget of 1).

**The one-line policy the operator should ratify:**

> **A Sharpe ratio is not a result. A Sharpe ratio *plus the number of effective trials that produced it* is a result. QMF will refuse to emit the former.**

**Shortlist of what NOT to adopt, with reasons:**

| Do not adopt | Reason |
|---|---|
| `mlfinlab` | Not open source; commercial licence required. The single most-recommended library in this space is the one QMX cannot use. |
| `scikit-optimize` | Dead — upstream archived 2024-02-23; the fork has been silent since 2024-06-04. Much older quant-finance writing still recommends it, so agents will suggest it. |
| Neptune | `neptune-client`, `neptune-api`, `neptune-query` all archived; product pivoted away. |
| Aim | 15 months without a release; 468 open issues. |
| Ray / Ray Tune (v1) | Beta on Windows; multi-node explicitly untested there. Solves a scale problem QMX does not have. |
| Dask (v1) | Duplicates joblib for task parallelism; its dataframe strength is already covered by DuckDB + Polars. |
| Hyperopt | Alive again but strictly dominated by Optuna; parallelism needs Mongo or Spark. |
| SMAC3 | Fine library, redundant second Bayesian-optimisation dependency. |
| W&B (hosted) | Hosted-first; strategy parameters are the operator's IP; self-hosting needs a commercial key. |
| MLflow **in v1** | Correct eventually, premature now. A manifest directory migrates *into* MLflow easily; a half-used server does not migrate out. |
| Copying Freqtrade / backtesting.py / vectorbt code | GPL-3.0, AGPL-3.0, and Apache-2.0+Commons-Clause respectively. Design study only. |
| An exhaustive parameter grid as the default API | Maximises `N` by construction — the single fastest route to a manufactured result. |
| A GA optimising raw Sharpe | The overfitting engine from §8.1. If a GA is built, its fitness function must already be deflated. |

**Where I disagree with the obvious answer.** The obvious answer to "how do I track experiments" is MLflow, and the obvious answer to "how do I search parameters at scale" is Ray Tune. I am recommending against both for version one, and the reason is the same in each case: they solve *coordination* problems (many people, many machines) that a solo operator does not have, while doing nothing about the *epistemic* problem (search inflates results) that is the actual threat. Spending the build budget on a tracking server instead of on the split budget ledger would be optimising the wrong thing.

---

## Open questions

1. **Reproducibility standard.** Does QMX commit to *bit*-identical results only within a pinned environment (achievable), or also across Windows / Linux VPS / cloud sandbox (very hard, possibly not worth it)? If the latter is dropped, what numeric tolerance is asserted in CI — 1e-9 on metrics? The answer changes how much engineering goes into §12.
2. **`purgedcv` — vendor, depend, or reimplement?** It is MIT, correct (I verified against the papers), and saves real work, but it is version 0.1.3 with ~26 stars and effectively one maintainer, and it would sit on QMX's most safety-critical path. My recommendation is reimplement-and-test-against-it, but that costs a few days. Operator call.
3. **What is `SR*`?** The whole budget arithmetic hangs off the pre-registered Sharpe threshold. At `SR* = 1.0` a 5-year split allows 45 effective trials; at `SR* = 2.0` it allows ~1,600. A higher bar buys enormously more search freedom while demanding a better strategy. What bar does the operator want, and does it differ for prop-firm accounts versus personal capital?
4. **Do disqualified candidates spend budget?** A candidate rejected by a hard pre-registered path constraint (daily loss cap breach) was rejected by a *rule*, not selected by a *metric*. Arguably it should not count against the trial budget. Arguably it should, because the constraint threshold itself was chosen. This genuinely matters — it could be the difference between a 45-trial budget and a 4,500-trial one.
5. **Is there a budget override at all?** I have recommended no `force=True`. But a real operator will eventually hit an exhausted split with a genuinely new idea. Is the answer "add a new split", "wait for new data", or a formal, permanently-recorded override that taints downstream results? Recommend deciding now, while it is abstract.
6. **DEAP's LGPL-3.0.** Same class of decision as NautilusTrader's LGPL in file 01. PyGAD (BSD) covers most GA needs. Does the operator want a blanket "no copyleft in the QMX tree" policy, or case-by-case?
7. **Modal Volume file counts.** The Hive-partitioned zstd Parquet layout for 28 pairs across multiple years and timeframes may exceed Modal's 50k-file performance threshold. Does the sweep pipeline ship a coarser repartitioned copy to Modal, or use object storage instead of a Volume? This needs measuring against the actual file count, which I do not have.
8. **Genetic search — build it at all in v1?** Optuna's NSGA-II/CMA-ES covers *parameter* evolution with no new dependency. A separate GA is only needed for *structural* evolution (evolving the shape of a Trigger/Confirmation expression), which is gplearn/DEAP territory and is the highest-overfitting-risk thing in this file. Should the GA lane be deferred until the split budget ledger and the overfitting statistics are proven in production?
9. **Where does the research lane's hypothesis provenance live?** I have specified a required `hypothesis` field on `Experiment`. The operator's research lane ingests papers, videos and chat. Is the hypothesis a free-text string, or a pointer into a separate research artefact store (paper id, timestamp in a video, chat message id)? The latter is much more valuable for an LLM author and needs its own design.
10. **Freqtrade's look-ahead and recursive-bias analysers.** `freqtrade/optimize/analysis/lookahead.py` and `recursive.py` appear to automate detection of look-ahead bias and warm-up-dependent indicators — complementary to everything here and directly relevant to file 03's TA-Lib "unstable period" finding. **UNVERIFIED**: I did not read these modules. Worth a follow-up read as GPL-licensed design prior art.
11. **Does the trial-count denominator include LLM-authored strategies that were never run?** If an agent generates 500 candidate strategies and QMF's static validation rejects 450 before backtesting, is `N` = 50 or 500? Formally the 450 were filtered by a rule, not a metric — but if the rule was tuned on data, they count. Needs a ruling.
