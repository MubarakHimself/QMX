# -*- coding: utf-8 -*-
"""Build extractions/changeover.jsonl from full-read notes. Read-only on corpus."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(r"C:\Users\Mubarak\Desktop\QMX")
OUT = ROOT / "workroom" / "research" / "2026-09-15_unbounded-market-intelligence"
MD = ROOT / ".worktrees" / "mql5-library" / "data" / "mql5-library" / "md"


def meta(aid: int) -> dict:
    p = MD / f"{aid}.md"
    m = {
        "article_id": aid,
        "path": f"md/{aid}.md",
        "title": "",
        "source": "mql5-library",
        "publication_date": "",
        "authors": [],
    }
    if not p.exists():
        return m
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()[:25]:
        if ln.startswith("title:"):
            m["title"] = ln[6:].strip().strip('"')
        elif ln.startswith("published:"):
            m["publication_date"] = ln[10:].strip()
        elif ln.startswith("author:"):
            a = ln[7:].strip().strip('"')
            if a:
                m["authors"] = [a]
        elif ln.startswith("source_url:"):
            m["source"] = ln[11:].strip()
    return m


def rec(aid: int, **kw):
    r = meta(aid)
    defaults = dict(
        topics=[],
        market_mechanisms=[],
        asset_or_venue_dependencies=[],
        time_horizons=[],
        data_requirements=[],
        central_claims=[],
        formulas=[],
        algorithms=[],
        implementation_details=[],
        execution_assumptions=[],
        cost_assumptions=[],
        risk_assumptions=[],
        evidence_level="article_claim",
        reproducibility="partial",
        lookahead_or_leakage_risks=[],
        transferable_mechanism="",
        qmx_overlap="",
        qmx_possible_gap="",
        testable_hypotheses=[],
        confidence=0.5,
        supporting_excerpts=[],
    )
    defaults.update(kw)
    r.update(defaults)
    return r


def build() -> list[dict]:
    rows: list[dict] = []

    rows.append(
        rec(
            23043,
            topics=[
                "CUSUM",
                "structural breakpoint",
                "sequential change detection",
                "online detector",
            ],
            market_mechanisms=[
                "return distributional shift",
                "dual-sided accumulators on z-scored log-returns",
            ],
            asset_or_venue_dependencies=[
                "method article; Part 2 validates FX/metals/indices"
            ],
            time_horizons=[
                "bar-by-bar; W=100 calibration; refractory MinBarsBetweenBreaks=10"
            ],
            data_requirements=[
                "closes for log-returns; rolling mean/std of prior W returns ending t-1"
            ],
            central_claims=[
                "Breakpoint at first bar where S+>h or S-<-h",
                "Standardization uses strictly historical window ending t-1",
                "Sequential detector vs lagging smoothers (MA/ATR)",
                "k absorbs noise; typical financial k in 0.25-0.75",
            ],
            formulas=[
                "tau=inf{t: S+_t>h or S-_t<-h}",
                "z_t=(r_t-mu_{t-1})/sigma_{t-1}",
                "S+=max(0,S+_prev+z-k); S-=min(0,S-_prev+z+k); reset after alarm",
            ],
            algorithms=[
                "Page 1954 two-sided CUSUM",
                "post-detection reset",
                "refractory gap",
            ],
            implementation_details=[
                "CUSUM_Breakpoint.mq5; defaults W=100,k=0.50,h=4.0",
                "buffers persist S+/S-; warm-up W+1",
            ],
            execution_assumptions=[
                "OnCalculate may re-evaluate forming last bar"
            ],
            cost_assumptions=["O(W) z-score + O(1) accumulator"],
            risk_assumptions=["h trades speed vs false alarms"],
            evidence_level="theory_plus_working_indicator",
            reproducibility="high_attached_mq5",
            lookahead_or_leakage_risks=[
                "Causal z-score (window ends t-1)",
                "Prefer closed-bar only for MIS",
                "Online stopping rule (not smoothed labels)",
            ],
            transferable_mechanism=(
                "Online break flag as MIS/Book sit-out sensor for vol-regime change, "
                "not a directional trade trigger"
            ),
            qmx_overlap="Sibling online CPD family to prior BOCPD 23482",
            qmx_possible_gap=(
                "No native CUSUM producer; regime_classifier_v1 is LightGBM not sequential CPD"
            ),
            testable_hypotheses=[
                "CUSUM breaks on crypto M1 co-occur with liquidity_stress/gap-event",
                "Empirical ARL << Siegmund ARL0 on QMX venues",
            ],
            confidence=0.88,
            supporting_excerpts=[
                "no batch reprocessing and no look-ahead bias",
                "estimated from the previous W returns only, ending at t-1",
            ],
        )
    )

    rows.append(
        rec(
            23103,
            topics=[
                "CUSUM validation",
                "empirical ARL",
                "volatility regime detector",
            ],
            market_mechanisms=[
                "fat-tail false-alarm inflation",
                "variance-shift vs mean-shift confirmation",
            ],
            asset_or_venue_dependencies=[
                "EURUSD GBPUSD XAUUSD DE40 USTEC USDJPY; M15/H1/H4; 2021-23 vs 2024-25"
            ],
            time_horizons=[
                "36-run battery; event latency median ~5 bars at h=4"
            ],
            data_requirements=[
                "F-test and Welch t on 200 bars pre/post each break (offline confirm)"
            ],
            central_claims=[
                "Empirical ARL ~65.7 vs theoretical 338.1 (~5x more alarms)",
                "Empirically a vol-regime detector: F% ~47%, mean T% ~0.7%",
                "Quiet tercile ARL ~430 closer to theory",
                "Calibrate h empirically; no tested k/h matches Siegmund",
                "Author use: pause MR / resize / widen stops — not directional anticipation",
            ],
            formulas=["ARL_emp=bars/breaks"],
            algorithms=[
                "cross-asset validation",
                "k x h grid on EURUSD H1",
                "macro latency table",
            ],
            implementation_details=["same CUSUM_Breakpoint.mq5"],
            execution_assumptions=["analyst-estimated event t0"],
            cost_assumptions=[],
            risk_assumptions=[
                "higher h adds slow outliers more than theory-predicted safety"
            ],
            evidence_level="strong_empirical_multi_asset",
            reproducibility="high_tables_plus_indicator",
            lookahead_or_leakage_risks=[
                "Post-break 200-bar tests are confirmatory only",
                "Event t0 not exact news timestamp",
            ],
            transferable_mechanism=(
                "Validated sit-out/cooldown after vol-break; matches QMX Book/KSA use, not bot entry"
            ),
            qmx_overlap="Same intended use pattern as prior BOCPD cooldown overlay",
            qmx_possible_gap="Need venue-specific empirical ARL on crypto M1",
            testable_hypotheses=[
                "Post-break N-bar Book refusal reduces DD vs random pauses",
            ],
            confidence=0.92,
            supporting_excerpts=[
                "empirically, a volatility regime detector, not a directional mean-shift detector",
                "pausing mean-reversion systems — is using it for exactly what the data confirms it does",
            ],
        )
    )

    rows.append(
        rec(
            23158,
            topics=[
                "AFML Ch17",
                "CSW",
                "SADF",
                "Chow DFC",
                "QADF",
                "CADF",
                "structural break features",
            ],
            market_mechanisms=[
                "steady vs unit-root vs explosive regimes",
                "bubble/explosiveness detection",
            ],
            asset_or_venue_dependencies=["synthetic demos; methods general"],
            time_horizons=["tau>=20; rolling L~504 daily suggested"],
            data_requirements=["log-prices for ADF family"],
            central_claims=[
                "CUSUM branch (CSW) + explosiveness branch (Chow/SADF/SMT/QADF/CADF)",
                "SADF regimes map to MR / reduce / trend playbooks in article",
                "Book snippets not production-ready; need NumPy/njit + bounded lookback",
            ],
            formulas=[
                "CSW critical sqrt(4.6+log(span))",
                "SADF_t=sup ADF",
                "half-life=-log(2)/log(1+beta)",
            ],
            algorithms=[
                "Chu-Stinchcombe-White",
                "Chow-type SDFC",
                "SADF family",
                "QADF/CADF robustifiers",
            ],
            implementation_details=["afml.structural_breaks; attached structural_breaks.py"],
            execution_assumptions=["offline or bounded-L live"],
            cost_assumptions=["unbounded SADF can be huge; bound L"],
            risk_assumptions=["CSW can stay elevated after rally ends"],
            evidence_level="implementation_plus_synthetic",
            reproducibility="code_attached",
            lookahead_or_leakage_risks=[
                "Endpoint-t features causal if windows<=t",
                "Full-sample Chow SDFC is offline confirmatory",
                "Article pushes strategy SWITCH (bot); QMX should use as filter/features",
            ],
            transferable_mechanism=(
                "CSW excess + rolling SADF as continuous changeover features for MIS/Book filter"
            ),
            qmx_overlap="Feature candidates for regime_classifier_v1 shadow",
            qmx_possible_gap="No SADF/CSW in V1 producers; compute budget",
            testable_hypotheses=[
                "SADF thresholds lift elevated/stressed vs quiet on QMX labels"
            ],
            confidence=0.86,
            supporting_excerpts=[
                "Always pass np.log(price_series), not the raw price series, to get_sadf()",
                "three regimes identified by the SADF specification (steady, unit-root, explosive)",
            ],
        )
    )

    rows.append(
        rec(
            23159,
            topics=["CStructuralBreaks", "MQL5 port", "rolling SADF"],
            market_mechanisms=["bar-indexed structural break stats for EAs"],
            asset_or_venue_dependencies=["EURUSD D1 validation defaults"],
            time_horizons=["L default 252; min_length 20"],
            data_requirements=["CopyClose log-prices; chronological vs series index map"],
            central_claims=[
                "Rolling SADF required for live EA (O(L^2) vs O(T^2))",
                "Index convention is main silent bug",
                "Python/MQL5 SADF r^2=1 on synthetic",
                "Example EA does playbook switch on SADF — bot use",
            ],
            formulas=["SB_EMPTY=-1e38 sentinel"],
            algorithms=["inline OLS per family"],
            implementation_details=[
                "CStructuralBreaks.mqh",
                "StructuralBreaksViewer.mq5",
                "Validation script",
            ],
            execution_assumptions=["new-bar recompute"],
            cost_assumptions=["shrink L on intraday"],
            risk_assumptions=["thresholds 1.5/-0.5 are knobs"],
            evidence_level="port_plus_numerical_agreement",
            reproducibility="high_attached_zip",
            lookahead_or_leakage_risks=[
                "Causal if closed bars only",
                "Chow supremum over window more batch than online",
            ],
            transferable_mechanism="Six features for shadow MIS; do not put playbook switch in MIS",
            qmx_overlap="Engineering path for structural-break features",
            qmx_possible_gap="M1 compute + not_ready warm-up",
            testable_hypotheses=[
                "Rolling SADF L~504 on M1 beats ATR alone for elevated class"
            ],
            confidence=0.84,
            supporting_excerpts=[
                "is the series explosive within the last L bars?",
                "r^2 = 1.000000 confirms floating-point agreement",
            ],
        )
    )

    rows.append(
        rec(
            20946,
            topics=[
                "structural break",
                "Chow test",
                "recursive CUSUM residuals",
                "RWEC",
                "pairs/cointegration break",
            ],
            market_mechanisms=[
                "hedge-ratio / correlation regime flip",
                "intercept shift vs slope inversion",
            ],
            asset_or_venue_dependencies=[
                "NVDA/INTC daily; US500/JPN225; equity pairs H4/D1"
            ],
            time_horizons=[
                "Chow needs ~20-30 bars post-break for stable OLS; CUSUM alarmed next day in example"
            ],
            data_requirements=["pair prices; breakpoint date for Chow; RecursiveLS residuals"],
            central_claims=[
                "Chow is confirmatory given hypothesized date; needs post-break buffer",
                "Recursive CUSUM on regression residuals is early-warning / monitoring tool",
                "RWEC detects vector drift earlier but is not a structural-break proof",
                "Use case is STOP/recalibrate pair when leash snaps — sit-out of broken model",
            ],
            formulas=["Chow F comparing pre/post/restricted regressions", "CUSUM of recursive residuals vs 95% bands"],
            algorithms=[
                "statsmodels RecursiveLS CUSUM",
                "Chow test",
                "RWEC cosine distance",
            ],
            implementation_details=["Python scripts attached; monitoring pipeline focus"],
            execution_assumptions=["pairs/stat-arb portfolio monitoring"],
            cost_assumptions=[],
            risk_assumptions=[
                "trading dead restricted model after break compounds error"
            ],
            evidence_level="case_study_plus_methods",
            reproducibility="scripts_attached_event_specific",
            lookahead_or_leakage_risks=[
                "Chow requires chosen breakpoint date (often known after news)",
                "Recursive CUSUM can be causal online on expanding residuals",
                "RWEC rolling windows causal if no future in window",
            ],
            transferable_mechanism=(
                "Model-death / relationship-break monitor as Book sit-out when fitted assumptions die "
                "(pairs analog of MIS assumption-break sensor)"
            ),
            qmx_overlap="Conceptual sibling to BOCPD 'assumptions just died'",
            qmx_possible_gap="QMX is not pairs-arb; still transferable as residual-CUSUM on any fitted sensor",
            testable_hypotheses=[
                "CUSUM on liquidity_stress residual vs its fitted mean flags stress onset earlier than raw threshold"
            ],
            confidence=0.85,
            supporting_excerpts=[
                "The Chow test is technically a confirmatory tool, not an early-warning tool",
                "the alarm was triggered on September 19, 2025, one day after the NVDA/INTC partnership announcement",
                "F-statistic with a value of 568 should sound like a get out signal",
            ],
        )
    )

    rows.append(
        rec(
            15033,
            topics=["HMM", "Viterbi", "forward-backward", "Baum-Welch", "hmmlearn export"],
            market_mechanisms=["hidden state as trend/range filter concept"],
            asset_or_venue_dependencies=["generic; demo random data in scripts"],
            time_horizons=["sequence models; freeze-and-ship params"],
            data_requirements=["multivariate continuous features; GaussianHMM"],
            central_claims=[
                "Train in Python hmmlearn, export JSON, infer in MQL5 with forward/backward/Viterbi",
                "Viterbi = most probable path; MAP/forward-backward = smoothed/filtered state probs",
                "First-order Markov + EM local optima; state count is a choice",
            ],
            formulas=["forward/backward likelihoods", "Bayes state probs from alpha*beta"],
            algorithms=["Baum-Welch EM", "Viterbi", "forward-backward"],
            implementation_details=["hmmlearn.mqh; hmm2json; log-domain numerics"],
            execution_assumptions=["frozen exported params at inference"],
            cost_assumptions=["inference cheap vs training"],
            risk_assumptions=["overfitting; wrong n_states"],
            evidence_level="integration_primer",
            reproducibility="code_attached",
            lookahead_or_leakage_risks=[
                "Viterbi on full batch sequence is SMOOTHED (uses future) — leakage if used as historical label",
                "Online causal use needs filtered forward probs only, or expanding Viterbi ending at t",
                "Training on full sample then labeling same sample leaks",
            ],
            transferable_mechanism=(
                "Freeze-and-ship HMM posteriors as MIS shadow state; prefer filtered P(state|past) over batch Viterbi"
            ),
            qmx_overlap="Infrastructure sibling to prior 16830 HMM filter",
            qmx_possible_gap="Clarify causal decode mode in any HMM shadow path",
            testable_hypotheses=[
                "Filtered forward state vs batch Viterbi disagree enough to change Book decisions"
            ],
            confidence=0.9,
            supporting_excerpts=[
                "By default, it uses the Viterbi algorithm to calculate the most probable state sequence",
                "forward, backward, and Viterbi algorithms",
            ],
        )
    )

    rows.append(
        rec(
            17917,
            topics=[
                "HMM",
                "GaussianHMM",
                "GMMHMM",
                "VariationalGaussianHMM",
                "market regimes",
            ],
            market_mechanisms=["regime as hidden emission clusters"],
            asset_or_venue_dependencies=["financial returns / multivariate features generally"],
            time_horizons=["EM training; sliding-window adaptation mentioned"],
            data_requirements=["returns preferred over prices; optional ATR/volume features"],
            central_claims=[
                "algorithm={'viterbi','map'} — map does forward-backward smoothing",
                "Start with 2-3 states; AIC/BIC; covariance_type matters",
                "GMMHMM for multimodal regimes; variational for uncertainty/priors",
                "Non-stationarity => sliding window retrain consideration",
            ],
            formulas=["EM E/M steps", "Dirichlet/Inverse-Wishart priors in variational"],
            algorithms=["EM", "variational inference", "Viterbi vs MAP decode"],
            implementation_details=["hmmlearn API survey; no single production EA"],
            execution_assumptions=["Python research path"],
            cost_assumptions=["GMMHMM heavier; full cov needs more data"],
            risk_assumptions=["EM local optima; prior misspecification"],
            evidence_level="method_survey",
            reproducibility="library_documented",
            lookahead_or_leakage_risks=[
                "MAP/forward-backward smoothed labels look ahead within the scored sequence",
                "Must separate train window from live filtered inference",
            ],
            transferable_mechanism=(
                "Decode-mode discipline: live MIS uses filtered probs; smoothed only for offline analysis"
            ),
            qmx_overlap="Deepens prior 16830 HMM discussion; recovered HMM stays unauthoritative per OPERATING_LINE",
            qmx_possible_gap="No variational uncertainty export in current QMX design",
            testable_hypotheses=[
                "2-state vol HMM filtered posterior vs LightGBM class concordance"
            ],
            confidence=0.8,
            supporting_excerpts=[
                "algorithm ({viterbi, map}... map ... performs smoothing (forward-backward)",
                "start with a small number of states (e.g. 2 or 3)",
            ],
        )
    )

    rows.append(
        rec(
            15541,
            topics=["HMM filter", "Nash equilibrium", "multi-strategy EA", "regime detection"],
            market_mechanisms=["HMM states as up/down/neutral; correlated pair Nash"],
            asset_or_venue_dependencies=["USDJPY focus; negatively correlated pairs; FX"],
            time_horizons=["train matrices in Python; paste into EA; re-opt ~3 months claimed"],
            data_requirements=["HMM matrices; EMA RSI ATR BB features"],
            central_claims=[
                "HMM + log-likelihood classify regime; strategies weighted including Nash",
                "Select profitable hidden states from IS bar charts — selection bias risk",
                "Results slowed; author says re-optimize matrices periodically",
            ],
            formulas=["forward algorithm likelihoods in EA"],
            algorithms=["hmmlearn train average of 10 models", "DetectMarketRegime"],
            implementation_details=["Nash EA; matrices from Python"],
            execution_assumptions=["bot trade trigger using regime"],
            cost_assumptions=[],
            risk_assumptions=["IS state picking; trailing stop simplistic"],
            evidence_level="demo_EA_case_study",
            reproducibility="zip_attached_but_results_fragile",
            lookahead_or_leakage_risks=[
                "State selection from full backtest charts is look-ahead model selection",
                "Unclear if decode is causal filtered vs batch",
            ],
            transferable_mechanism=(
                "Negative lesson for MIS: do not pick states by IS PnL; HMM as filter only if frozen OOS"
            ),
            qmx_overlap="Prior notes flagged 15541 as leftover; confirms bot-centric HMM use",
            qmx_possible_gap="Shows how NOT to wire HMM into Book",
            testable_hypotheses=[
                "Frozen matrices without IS state cherry-pick lose claimed edge OOS"
            ],
            confidence=0.62,
            supporting_excerpts=[
                "hidden states that we want to use are: 2, 3 and 7",
                "optimization should have been done for every 3 months",
            ],
        )
    )

    rows.append(
        rec(
            18864,
            topics=[
                "CUSUM filter sampling",
                "triple-barrier labeling",
                "meta-labeling",
                "event-based sampling",
            ],
            market_mechanisms=[
                "sample when cumulative price deviation exceeds h",
                "path-dependent labels",
            ],
            asset_or_venue_dependencies=["EURUSD M5 2018-2024 demo"],
            time_horizons=["vertical barrier 50 bars in demo; daily vol span 100"],
            data_requirements=["bars/ticks; volatility for barrier width"],
            central_claims=[
                "CUSUM filter triggers sampling events on significant moves; resets accumulator",
                "Avoids Bollinger-style chatter around threshold",
                "Triple-barrier labels encode risk path; meta-labeling filters primary signals",
                "CUSUM-filtered training kept performance with 76% less data in demo",
            ],
            formulas=[
                "S+/S- CUSUM on price changes vs h",
                "triple barrier pt/sl/t1",
            ],
            algorithms=["AFML CUSUM filter", "get_events/get_bins", "meta-label RF"],
            implementation_details=["Python blueprint; TA-Lib features"],
            execution_assumptions=["research labeling pipeline"],
            cost_assumptions=[],
            risk_assumptions=["barrier widths must be vol-scaled"],
            evidence_level="pipeline_demo_with_metrics",
            reproducibility="code_patterns_in_article",
            lookahead_or_leakage_risks=[
                "Triple-barrier LABEL uses future path — correct for labels, illegal as live feature",
                "CUSUM filter itself can be causal for event timestamps",
                "Part 1 timestamp trap warned; still must purge/embargo (see 19850)",
            ],
            transferable_mechanism=(
                "CUSUM as event sampler / changeover clock for corpus building — not a bot entry by itself"
            ),
            qmx_overlap="Labeling hygiene for regime_classifier_v1 corpora",
            qmx_possible_gap="QMX labels may not use CUSUM event sampling yet",
            testable_hypotheses=[
                "CUSUM-sampled regime labels reduce class imbalance noise vs every-bar labels"
            ],
            confidence=0.83,
            supporting_excerpts=[
                "CUSUM filter... triggering a sampling event when this accumulation surpasses a certain threshold",
                "Filtering only slightly degraded overall performance of the meta-model despite 76% less data",
            ],
        )
    )

    rows.append(
        rec(
            19850,
            topics=[
                "label concurrency",
                "sample uniqueness",
                "purged CV",
                "structural breaks in CV",
            ],
            market_mechanisms=["overlapping triple-barrier events violate IID"],
            asset_or_venue_dependencies=["financial ML pipelines generally"],
            time_horizons=["event lifespan overlap"],
            data_requirements=["event start/end times; returns for attribution weights"],
            central_claims=[
                "Concurrent labels inflate IS performance",
                "Average uniqueness sample weights correct redundancy",
                "Standard k-fold leaks; need purge + embargo",
                "Structural breaks listed among reasons standard CV fails in finance",
            ],
            formulas=["avg uniqueness = mean(1/concurrency)", "return-attribution weights", "time decay on uniqueness"],
            algorithms=["mp_pandas_obj concurrency", "PurgedKFold"],
            implementation_details=["sklearn sample_weight + max_samples=mean uniqueness"],
            execution_assumptions=["offline training"],
            cost_assumptions=[],
            risk_assumptions=["unweighted concurrent labels overfit"],
            evidence_level="method_from_AFML_with_code",
            reproducibility="code_in_article",
            lookahead_or_leakage_risks=[
                "Article is about preventing leakage; still labels use future by design",
                "Embargo length is a knob — too short leaks serial correlation",
            ],
            transferable_mechanism=(
                "Any changeover-feature ML must purge overlapping label spans and weight uniqueness"
            ),
            qmx_overlap="Directly relevant to regime_classifier_v1 train/eval seams",
            qmx_possible_gap="Confirm purged/embargoed CV on integration train path",
            testable_hypotheses=[
                "Enabling uniqueness weights reduces IS-OOS gap for quiet/elevated/stressed"
            ],
            confidence=0.88,
            supporting_excerpts=[
                "Models trained on concurrent observations exhibit inflated in-sample performance",
                "structural breaks" ,
            ],
        )
    )

    rows.append(
        rec(
            17781,
            topics=[
                "regime EA",
                "playbook switch",
                "trend/range/volatile",
                "MTF regimes",
            ],
            market_mechanisms=["hierarchical vol then trend/range from Part 1 detector"],
            asset_or_venue_dependencies=["XAUUSD M1 demo optimization"],
            time_horizons=["lookback 50-200 typical"],
            data_requirements=["CMarketRegimeDetector from 17737"],
            central_claims=[
                "EA switches trend-follow / RSI MR / BB breakout by regime",
                "Also switches lot/SL/TP by regime — Book-like sizing inside bot",
                "Transition smoothing and gradual sizing discussed (pseudo)",
                "Optimization on same period — overfitting risk admitted",
            ],
            formulas=["thresholds TrendThreshold VolatilityThreshold knobs"],
            algorithms=["ExecuteRegimeBasedStrategy", "MTF Comment indicator"],
            implementation_details=["MarketRegimeEA; multi-TF detectors array"],
            execution_assumptions=["bot consumes regime"],
            cost_assumptions=[],
            risk_assumptions=["abrupt switch slippage; overfit optimized params"],
            evidence_level="demo_backtest_with_caveats",
            reproducibility="files_attached",
            lookahead_or_leakage_risks=[
                "Detector itself can be causal on closed bars",
                "Genetic optimize on test window is leakage",
            ],
            transferable_mechanism=(
                "NEGATIVE for MIS: playbook switch + sizing belong in Book/bots, not MIS labeler"
            ),
            qmx_overlap="Part 2 of prior-read 17737; confirms bot half",
            qmx_possible_gap="Document boundary: MIS labels only; Book owns refusal",
            testable_hypotheses=[
                "Using Part1 labels as Book filter without EA switch still cuts DD"
            ],
            confidence=0.78,
            supporting_excerpts=[
                "automatically switch gears, deploying trend-following logic when trends are strong",
                "inherently introduces a risk of overfitting",
            ],
        )
    )

    rows.append(
        rec(
            23444,
            topics=[
                "regime-switching EA",
                "Ehlers",
                "Even Better Sinewave",
                "MAMA/FAMA",
                "dominant cycle",
            ],
            market_mechanisms=[
                "cycle vs trend modes demand opposite playbooks",
                "Hilbert period measurement",
            ],
            asset_or_venue_dependencies=["EURUSD M30 real-ticks demo ~5 weeks"],
            time_horizons=["dominant period clamped 6-50 bars; replay 1500 closed bars"],
            data_requirements=["OHLC median price into DSP filters"],
            central_claims=[
                "EBSW rail selects trend vs cycle mode; MAMA/FAMA trend; EBSW fade in cycle",
                "Closed bars only; full filter replay; Ready() warm-up — anti-lookahead discipline",
                "Demo PF 1.18, shallow DD — unoptimized single window; not validated system",
            ],
            formulas=["Hilbert 7-tap; alpha=fastLimit/deltaPhase for MAMA"],
            algorithms=["CyclePeriod", "MAMA/FAMA", "EhlersRegimeEA"],
            implementation_details=["EhlersDSP.mqh shared; no iCustom"],
            execution_assumptions=["once per closed bar"],
            cost_assumptions=["replay ~1500 bars/bar acceptable"],
            risk_assumptions=["single threshold mode filter whipsaws in mixed regimes"],
            evidence_level="engineered_demo_honest_limits",
            reproducibility="code_and_tester_settings_described",
            lookahead_or_leakage_risks=[
                "Author explicitly avoids forming-bar lookahead",
                "Still a TRADE TRIGGER bot (entries), not sit-out-only",
            ],
            transferable_mechanism=(
                "Mode detector (EBSW rail / period) as MIS coordinate; entries stay in bot; "
                "closed-bar replay discipline is transferable"
            ),
            qmx_overlap="Regime thesis matches MIS door idea; execution is bot",
            qmx_possible_gap="No Ehlers-style cycle/trend mode in V1 producers",
            testable_hypotheses=[
                "EBSW |value|>rail predicts elevated/stressed or trending better than ADX alone"
            ],
            confidence=0.82,
            supporting_excerpts=[
                "Acting on closed bars only",
                "Do not treat this as a validated trading system",
                "know which mode it is in and switch playbooks accordingly",
            ],
        )
    )

    rows.append(
        rec(
            21833,
            topics=[
                "CUSUM structural break",
                "change point detection",
                "VolatilityGate",
                "grid regime gating",
            ],
            market_mechanisms=[
                "sigma/mu ratio for ranging vs quiet-trend danger",
                "frozen-baseline CUSUM CPD blocks BGT into trends",
            ],
            asset_or_venue_dependencies=["forex grid context; ATR D1 spacing H4 regime"],
            time_horizons=["cycle hours age kill; CPD baseline freeze"],
            data_requirements=["ATR; MA drift magnitude; returns for CUSUM"],
            central_claims=[
                "Unconstrained grids ruin a.s.; restartable finite cycles required",
                "VolatilityGate: high sigma/mu safe for bi-directional grid; low ratio pause",
                "Frozen-baseline CUSUM detects structural shift; can force TGT or block cycle",
                "Kill switch on equity not only theoretical L_t",
            ],
            formulas=["L_t triangular loss", "RPR=L_t/E0", "sigma/mu gate"],
            algorithms=["VolatilityGate", "CPDEngine frozen CUSUM", "BGT/TGT/MGT modes"],
            implementation_details=["research-grounded grid EA + Python diagnostics"],
            execution_assumptions=["cycle restart resets variance clock"],
            cost_assumptions=[],
            risk_assumptions=["quiet trend is the dangerous regime for grids"],
            evidence_level="research_grounded_architecture",
            reproducibility="source_attached_claimed",
            lookahead_or_leakage_risks=[
                "Frozen baseline CUSUM is causal after baseline collected",
                "Mode switch is trading logic (bot), but gate is sit-out — QMX-aligned part",
            ],
            transferable_mechanism=(
                "Two-layer changeover: continuous gate (sigma/mu) + discrete CPD CUSUM block — "
                "Book admission pattern"
            ),
            qmx_overlap="Best articulation of change-point as START GATE / sit-out in corpus",
            qmx_possible_gap="No CPDEngine analog blocking Book door on structural break",
            testable_hypotheses=[
                "Frozen-baseline CUSUM on return z blocks more losing quiet-trend episodes than rolling vol alone"
            ],
            confidence=0.87,
            supporting_excerpts=[
                "CPDEngine asks has the process structurally shifted?",
                "The EA refuses to deploy a fresh BGT grid into a confirmed trend",
                "frozen baseline keeps the reference regime fixed",
            ],
        )
    )

    rows.append(
        rec(
            23734,
            topics=[
                "volatility regime",
                "implied vs realized",
                "variance risk premium proxy",
                "regime change notify",
            ],
            market_mechanisms=["IV/RV ratio regimes; options premium"],
            asset_or_venue_dependencies=["GLD options proxy for gold; XAUUSD RV in MT5"],
            time_horizons=["30-day IV and RV"],
            data_requirements=["external option chain JSON via WebRequest; local bars"],
            central_claims=[
                "Ratio IV/RV as scale-free regime context — not direction signal",
                "Heuristic thresholds 1.20/1.05/0.95 configurable",
                "Service notifies on regime CHANGE with cooldown — sit-out style alert",
                "Author: context for sizing/sanity, not timing trigger",
            ],
            formulas=["Black-Scholes IV bisection", "IV/RV ratio"],
            algorithms=["Python feed + MQL5 service panel"],
            implementation_details=["GitHub Actions feed; CVolatilityEngine"],
            execution_assumptions=["WebRequest allowed; feed freshness checks"],
            cost_assumptions=[],
            risk_assumptions=["GLD != spot gold options; stretched premium can persist weeks"],
            evidence_level="engineering_monitor_honest_limits",
            reproducibility="scripts_described",
            lookahead_or_leakage_risks=[
                "IV is contemporaneous market quote (not future price path)",
                "RV uses past bars only",
            ],
            transferable_mechanism=(
                "External forward-looking vol regime as MIS/Book context; notify-on-change with cooldown"
            ),
            qmx_overlap="Regime monitor without trade trigger — closest to MIS philosophy among vol articles",
            qmx_possible_gap="Crypto lacks clean options IV feed in current V1",
            testable_hypotheses=[
                "When IV/RV high, ATR-sized risk understates future range"
            ],
            confidence=0.8,
            supporting_excerpts=[
                "What you get is not a buy or sell signal but a reliable, money-backed second opinion",
                "notifies on a change of state, then waits out a cooldown",
            ],
        )
    )

    rows.append(
        rec(
            11930,
            topics=["Markov chains", "MSM", "HMM overview", "wizard signal"],
            market_mechanisms=["transition matrix forecasts of discrete states"],
            asset_or_venue_dependencies=["wizard EA examples"],
            time_horizons=["discrete-time steps"],
            data_requirements=["discretized returns/states"],
            central_claims=[
                "Taxonomy: DTMC, CTMC, HMM, Markov-switching",
                "Assumptions: stationarity, Markov property, finite states, time-homogeneity, ergodicity",
                "ALGLIB EM for probability estimation in MQL5 wizard context",
            ],
            formulas=["transition matrix P(j|i)"],
            algorithms=["MLE counts", "EM", "Bayesian update sketch"],
            implementation_details=["MQL5 wizard custom signal"],
            execution_assumptions=["bot signal generation"],
            cost_assumptions=[],
            risk_assumptions=["assumptions fail under non-stationary markets"],
            evidence_level="tutorial",
            reproducibility="wizard pattern",
            lookahead_or_leakage_risks=[
                "Estimating P on full sample then backtesting same sample leaks",
                "MSM/HMM mention without causal decode discipline",
            ],
            transferable_mechanism="Transition-matrix language for regime persistence features (P(stay))",
            qmx_overlap="Conceptual background for HMM/Markov recovered work",
            qmx_possible_gap="Persistence P(stay in stressed) not explicit in snapshot",
            testable_hypotheses=[
                "Empirical P(stressed->stressed) helps Book cooldown length"
            ],
            confidence=0.7,
            supporting_excerpts=[
                "Markov switching model (MSM)",
                "transition probabilities between states are constant over time",
            ],
        )
    )

    rows.append(
        rec(
            16030,
            topics=["deep Markov", "RSI state transitions", "symbol-specific thresholds"],
            market_mechanisms=["Markov on indicator states per symbol"],
            asset_or_venue_dependencies=["XPDUSD vs NZDJPY RSI vol contrast"],
            time_horizons=["indicator bar states"],
            data_requirements=["RSI series; Python+MQL5"],
            central_claims=[
                "Fixed RSI 30/70 not universal; learn symbol-specific extremes via Markov",
                "Transition matrix guides probabilistic entries — bot framing",
            ],
            formulas=["transition matrix on RSI bins"],
            algorithms=["deep Markov models with Python"],
            implementation_details=["self-optimizing EA series Part V"],
            execution_assumptions=["bot"],
            cost_assumptions=[],
            risk_assumptions=["regime change breaks fixed thresholds — article motivation"],
            evidence_level="illustrative",
            reproducibility="series_code",
            lookahead_or_leakage_risks=[
                "Learning thresholds on same test window leaks",
            ],
            transferable_mechanism=(
                "Symbol-specific regime thresholds; MIS should not hardcode folklore cutoffs"
            ),
            qmx_overlap="Supports unfrozen thresholds stance from prior ADX notes",
            qmx_possible_gap="Per-venue calibration story for classifier thresholds",
            testable_hypotheses=[
                "Per-symbol quiet/elevated cutoffs beat global cutoffs"
            ],
            confidence=0.65,
            supporting_excerpts=[
                "each market could have its own unique level of interest on the RSI indicator",
            ],
        )
    )

    rows.append(
        rec(
            18097,
            topics=["Markov chain matrix forecasting", "discrete states"],
            market_mechanisms=["probabilistic transitions between discretized market states"],
            asset_or_venue_dependencies=["unspecified FX/general"],
            time_horizons=["state-step forecasts"],
            data_requirements=["discretized price/indicator states"],
            central_claims=[
                "Market as transition system between discrete states",
                "Forecast via Markov matrix — primarily predictive/trading framing",
            ],
            formulas=["P(X_{t+1}|X_t)"],
            algorithms=["matrix forecasting model"],
            implementation_details=["MQL5 trading system article"],
            execution_assumptions=["bot forecasting"],
            cost_assumptions=[],
            risk_assumptions=["chaos vs order; probabilistic not certain"],
            evidence_level="narrative_method",
            reproducibility="partial",
            lookahead_or_leakage_risks=["state labeling and matrix fit on overlapping windows risk leakage"],
            transferable_mechanism="Discrete state occupancy vector as MIS feature family",
            qmx_overlap="Markov theme cluster",
            qmx_possible_gap="No matrix forecast in MIS (correct — MIS is not a forecaster)",
            testable_hypotheses=[],
            confidence=0.55,
            supporting_excerpts=[
                "representing the market as a system of transitions between discrete states",
            ],
        )
    )

    rows.append(
        rec(
            18192,
            topics=["Markov state-transition", "neural EA", "self-learning"],
            market_mechanisms=["NN on Markov transition features"],
            asset_or_venue_dependencies=["claims performance metrics — treat cautiously"],
            time_horizons=["ongoing self-learning"],
            data_requirements=["state matrix + NN"],
            central_claims=[
                "Combines Markov matrix with NN and hedging",
                "Reports high returns/Sharpe — unverified marketing-level claims",
            ],
            formulas=["Markov property equation"],
            algorithms=["self-learning EA"],
            implementation_details=["MQL5 EA"],
            execution_assumptions=["bot"],
            cost_assumptions=[],
            risk_assumptions=["overfit / unverifiable performance"],
            evidence_level="weak_unverifiable_claims",
            reproducibility="low",
            lookahead_or_leakage_risks=["self-learning on expanding history without purge risks leakage"],
            transferable_mechanism="Little for MIS; flag as bot+unverified",
            qmx_overlap="Markov keyword sibling only",
            qmx_possible_gap="None actionable",
            testable_hypotheses=[],
            confidence=0.35,
            supporting_excerpts=[
                "average annual return of 28.7% with a maximum drawdown of only 14.2%",
            ],
        )
    )

    rows.append(
        rec(
            15743,
            topics=["Q-learning", "Markov chains", "wizard"],
            market_mechanisms=["RL policy over Markov states"],
            asset_or_venue_dependencies=["wizard EA"],
            time_horizons=["episode/step RL"],
            data_requirements=["state discretization; rewards"],
            central_claims=[
                "Q-learning with Markov chain state representation in wizard signal",
            ],
            formulas=["Bellman/Q update"],
            algorithms=["Q-learning", "Markov states"],
            implementation_details=["MQL5 wizard Part 36"],
            execution_assumptions=["bot"],
            cost_assumptions=[],
            risk_assumptions=["RL non-stationarity"],
            evidence_level="tutorial",
            reproducibility="wizard",
            lookahead_or_leakage_risks=["reward uses future returns by definition"],
            transferable_mechanism="Not MIS; RL owns actions",
            qmx_overlap="Markov cluster peripheral",
            qmx_possible_gap="n/a",
            testable_hypotheses=[],
            confidence=0.5,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            21142,
            topics=[
                "L1 trend filter",
                "breakpoints",
                "piecewise-linear regime changes",
                "L1VolatilityRegime",
            ],
            market_mechanisms=[
                "sparse second differences = trend breakpoints",
                "residual vol regimes",
            ],
            asset_or_venue_dependencies=["S&P500 and FX examples"],
            time_horizons=["lambda via coef*lambda_max relative scale"],
            data_requirements=["price series length N for L1 solve"],
            central_claims=[
                "L1 trend filtering yields piecewise-linear trend with explicit breakpoints as regime changes",
                "Relative lambda = coef*lambda_max transfers better across instruments than absolute lambda",
                "L1VolatilityRegime indicator for market regime from residual volatility",
                "Can filter classic strategy signals to align with L1 trend",
            ],
            formulas=["argmin ||y-x||^2 + lambda||D2 x||_1", "lambda_max algorithm"],
            algorithms=["L1 trend filter", "lambda_max"],
            implementation_details=["multiple MQL5 indicators including L1VolatilityRegime"],
            execution_assumptions=["batch solve on window; complexity claimed linear"],
            cost_assumptions=["suitable for MQL5 per author"],
            risk_assumptions=["lambda choice still matters"],
            evidence_level="method_plus_strategy_filters",
            reproducibility="indicators_described",
            lookahead_or_leakage_risks=[
                "Full-window L1 solve uses entire window — endpoint trend can depend on future points inside window (TWO-SIDED smoother)",
                "Critical: causal use needs trailing window ending at t only, or online approximation",
            ],
            transferable_mechanism=(
                "Breakpoint count / slope-sign as regime-change features IF computed causally on trailing windows"
            ),
            qmx_overlap="Breakpoint-as-regime-change narrative; HMM also mentioned in related hits",
            qmx_possible_gap="Must not use two-sided L1 as live label without causalization",
            testable_hypotheses=[
                "Causal trailing L1 slope-sign changes align with CUSUM breaks"
            ],
            confidence=0.75,
            supporting_excerpts=[
                "explicit breakpoints as regime changes",
                "L1VolatilityRegime.mq5 - market regime detection based on volatility",
            ],
        )
    )

    rows.append(
        rec(
            22220,
            topics=["entropy", "adaptive volatility", "regime change mention"],
            market_mechanisms=["entropy-based adaptive vol"],
            asset_or_venue_dependencies=["MQL5+Python packages series"],
            time_horizons=["rolling entropy windows"],
            data_requirements=["returns"],
            central_claims=[
                "Entropy used to adapt volatility estimation across regimes",
            ],
            formulas=[],
            algorithms=["entropy-based adaptive volatility"],
            implementation_details=["Part 9 integration article"],
            execution_assumptions=[],
            cost_assumptions=[],
            risk_assumptions=[],
            evidence_level="series_part",
            reproducibility="partial",
            lookahead_or_leakage_risks=["rolling entropy can be causal"],
            transferable_mechanism="Entropy as changeover/feature coordinate (persistence family overlap)",
            qmx_overlap="Touches regime change language; persistence/entropy family",
            qmx_possible_gap="Not a CPD method",
            testable_hypotheses=[],
            confidence=0.55,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            23677,
            topics=["EGARCH", "asymmetric vol regime", "AVRO", "leverage effect"],
            market_mechanisms=["vol responds differently to down vs up shocks"],
            asset_or_venue_dependencies=["FX/equity samples in tests"],
            time_horizons=["rolling EGARCH fit window"],
            data_requirements=["returns"],
            central_claims=[
                "EGARCH captures leverage asymmetry; AVRO tracks calm vs panic variance transition speed",
                "Innovation z-score normalizes shocks to conditional distribution — regime-aware strain",
            ],
            formulas=["EGARCH log-variance recursion"],
            algorithms=["EGARCH MLE/fit", "asymmetry diagnostic tests"],
            implementation_details=["EGARCH indicators including AVRO"],
            execution_assumptions=["rolling refit cost"],
            cost_assumptions=["heavier than plain ATR"],
            risk_assumptions=["convergence failures need not_ready"],
            evidence_level="implementation_plus_diagnostics",
            reproducibility="archive_structure_described",
            lookahead_or_leakage_risks=[
                "Rolling window fit ending at t-1 is causal",
                "In-window MLE using bar t return for same-bar signal can leak — use lagged params",
            ],
            transferable_mechanism=(
                "Asymmetric vol-regime oscillator as elevated/stressed coordinate; fitted like liquidity_stress_v1"
            ),
            qmx_overlap="Extends prior GARCH 15223 family; MS-GARCH still absent as dedicated article",
            qmx_possible_gap="No EGARCH/AVRO producer; recovered MS-GARCH unauthoritative",
            testable_hypotheses=[
                "AVRO panic transitions precede stressed class labels"
            ],
            confidence=0.78,
            supporting_excerpts=[
                "Asymmetric Volatility Regime Oscillator (AVRO) tracks directional trend strength by monitoring the speed at which variance transitions between a calm state and a panic state",
            ],
        )
    )

    rows.append(
        rec(
            22258,
            topics=["GJR-GARCH", "asymmetric volatility", "leverage"],
            market_mechanisms=["threshold asymmetry in variance"],
            asset_or_venue_dependencies=["vol modeling series"],
            time_horizons=["conditional variance one-step"],
            data_requirements=["returns"],
            central_claims=[
                "GJR-GARCH implements leverage/threshold asymmetry vs plain GARCH",
            ],
            formulas=["GJR variance equation with indicator for negative shocks"],
            algorithms=["GJR-GARCH estimation"],
            implementation_details=["Building Volatility Models Part II"],
            execution_assumptions=["fitted params"],
            cost_assumptions=[],
            risk_assumptions=["misspecification"],
            evidence_level="implementation",
            reproducibility="code_series",
            lookahead_or_leakage_risks=["same lagged-param discipline as GARCH"],
            transferable_mechanism="Asymmetric conditional vol feature for regime stress",
            qmx_overlap="Vol family input to changeover",
            qmx_possible_gap="Not a change-point detector itself",
            testable_hypotheses=[],
            confidence=0.7,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            23488,
            topics=["catch22", "vol regime features", "time-series feature set"],
            market_mechanisms=["canonical features discriminating regimes"],
            asset_or_venue_dependencies=["vol regime tests in article"],
            time_horizons=["windowed catch22"],
            data_requirements=["univariate series windows"],
            central_claims=[
                "Port of catch22 feature set; tested on vol regimes",
            ],
            formulas=[],
            algorithms=["catch22 feature extraction"],
            implementation_details=["MQL5 port"],
            execution_assumptions=["batch window features"],
            cost_assumptions=["22 features per window"],
            risk_assumptions=[],
            evidence_level="feature_set_port",
            reproducibility="code_attached_claimed",
            lookahead_or_leakage_risks=["window must end at t"],
            transferable_mechanism="Feature pack for regime_classifier_v1 candidates",
            qmx_overlap="ML feature family adjacent to changeover labeling",
            qmx_possible_gap="Not CPD; features for state not transition",
            testable_hypotheses=[
                "catch22 features improve LightGBM regime macro-F1"
            ],
            confidence=0.68,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            22754,
            topics=["meta-labeling", "ADX", "filter and sizing"],
            market_mechanisms=["meta-model filters classic ADX signals"],
            asset_or_venue_dependencies=["ADX strategy context"],
            time_horizons=["triple-barrier style meta labels likely"],
            data_requirements=["primary ADX signals + features"],
            central_claims=[
                "Meta-labeling filters and sizes ADX trades — filter layer over primary signal",
            ],
            formulas=[],
            algorithms=["meta-labeling"],
            implementation_details=["Part 2 of meta-labeling classics"],
            execution_assumptions=["bot with filter"],
            cost_assumptions=[],
            risk_assumptions=[],
            evidence_level="strategy_article",
            reproducibility="partial",
            lookahead_or_leakage_risks=["meta labels use future outcomes"],
            transferable_mechanism=(
                "Meta-label as Book admission analog: primary signal exists, secondary says take/skip"
            ),
            qmx_overlap="Filter not trigger — philosophically close to Book door",
            qmx_possible_gap="MIS is not meta-labeler of bot signals (bots never consume MIS)",
            testable_hypotheses=[],
            confidence=0.6,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            14199,
            topics=["structural breaks", "spurious regression", "KPSS"],
            market_mechanisms=["breaks can look like non-stationarity"],
            asset_or_venue_dependencies=["Python econometrics examples"],
            time_horizons=["series-level tests"],
            data_requirements=["price/levels series"],
            central_claims=[
                "Structural breaks can cause KPSS to reject stationarity",
                "Spurious regressions risk when relationships unstable",
            ],
            formulas=[],
            algorithms=["KPSS", "stationarity tests"],
            implementation_details=["Python"],
            execution_assumptions=["offline diagnostics"],
            cost_assumptions=[],
            risk_assumptions=["trading on spurious co-movement"],
            evidence_level="econometric_warning",
            reproducibility="code_patterns",
            lookahead_or_leakage_risks=["full-sample stationarity tests are offline"],
            transferable_mechanism="Diagnostic: apparent regime/stationarity shifts may be breaks",
            qmx_overlap="Supports need for break tests beside level classifiers",
            qmx_possible_gap="No spurious-regression guard on multi-feature MIS",
            testable_hypotheses=[],
            confidence=0.7,
            supporting_excerpts=[
                "If there are structural breaks in the time series... the KPSS test may detect these as non-stationary trends",
            ],
        )
    )

    rows.append(
        rec(
            18549,
            topics=["Prophet", "changepoint", "forex forecasting"],
            market_mechanisms=["Prophet additive model with changepoints"],
            asset_or_venue_dependencies=["Forex"],
            time_horizons=["Prophet changepoint prior scale"],
            data_requirements=["timestamped series"],
            central_claims=[
                "Facebook Prophet uses changepoints for trend shifts in FX forecasting demo",
            ],
            formulas=[],
            algorithms=["Prophet"],
            implementation_details=["Python DS/ML Part 45"],
            execution_assumptions=["forecast bot assist"],
            cost_assumptions=[],
            risk_assumptions=["Prophet changepoints can be in-sample flexible — overfit"],
            evidence_level="tool_demo",
            reproducibility="partial",
            lookahead_or_leakage_risks=[
                "Prophet fit on full series places changepoints with hindsight unless carefully CV'd",
            ],
            transferable_mechanism="Named changepoint tooling exists but weak for causal MIS",
            qmx_overlap="Changepoint keyword hit",
            qmx_possible_gap="PELT/BOCPD better causal than Prophet for MIS",
            testable_hypotheses=[],
            confidence=0.5,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            10955,
            topics=["price movement model", "jumps"],
            market_mechanisms=["jump-like price increments in simplest model"],
            asset_or_venue_dependencies=["general"],
            time_horizons=["tick/bar increments"],
            data_requirements=["price series"],
            central_claims=[
                "Simplest price movement model discusses jumps/application to trading",
            ],
            formulas=[],
            algorithms=[],
            implementation_details=[],
            execution_assumptions=[],
            cost_assumptions=[],
            risk_assumptions=[],
            evidence_level="theoretical_model_article",
            reproducibility="low",
            lookahead_or_leakage_risks=[],
            transferable_mechanism="Jump language only; not a detector implementation",
            qmx_overlap="Jump keyword sparse in corpus",
            qmx_possible_gap="No dedicated jump-process CPD article found",
            testable_hypotheses=[],
            confidence=0.45,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            23049,
            topics=["market structure", "CUSUM mention", "hierarchical framework"],
            market_mechanisms=["structure breaks in hierarchical market structure prototype"],
            asset_or_venue_dependencies=["MQL5 prototype"],
            time_horizons=[],
            data_requirements=["price structure"],
            central_claims=[
                "Prototype hierarchical market structure framework references structural break/CUSUM ideas",
            ],
            formulas=[],
            algorithms=[],
            implementation_details=["modular architecture prototype"],
            execution_assumptions=[],
            cost_assumptions=[],
            risk_assumptions=[],
            evidence_level="prototype",
            reproducibility="partial",
            lookahead_or_leakage_risks=["structure zigzags often repaint — classic lookahead"],
            transferable_mechanism="Caution: market-structure 'breaks' often non-causal",
            qmx_overlap="Weak changeover signal",
            qmx_possible_gap="n/a",
            testable_hypotheses=[],
            confidence=0.4,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            23543,
            topics=["structural break", "pre-backtest evaluation", "LF quant"],
            market_mechanisms=["pre-trade evaluation including break awareness"],
            asset_or_venue_dependencies=["LF quant series"],
            time_horizons=[],
            data_requirements=[],
            central_claims=[
                "Pre-backtest evaluation discusses structural breaks among robustness checks",
            ],
            formulas=[],
            algorithms=[],
            implementation_details=[],
            execution_assumptions=[],
            cost_assumptions=[],
            risk_assumptions=["ignore breaks => fragile backtests"],
            evidence_level="process_article",
            reproducibility="partial",
            lookahead_or_leakage_risks=[],
            transferable_mechanism="Process: evaluate changeover robustness before promoting models",
            qmx_overlap="Eval hygiene for classifier",
            qmx_possible_gap="Add break-period slice metrics to regime eval",
            testable_hypotheses=[],
            confidence=0.55,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            22014,
            topics=["fractional differentiation", "stationarity", "regime change mention"],
            market_mechanisms=["memory vs stationarity trade-off"],
            asset_or_venue_dependencies=["ML feature engineering series"],
            time_horizons=["frac-diff d parameter"],
            data_requirements=["price series"],
            central_claims=[
                "Frac-diff for stationary features without full memory wipe; regime change called out as ML failure mode elsewhere in series",
            ],
            formulas=["fractional differentiation weights"],
            algorithms=["AFML frac-diff"],
            implementation_details=["Feature Engineering Part 1"],
            execution_assumptions=[],
            cost_assumptions=[],
            risk_assumptions=[],
            evidence_level="feature_method",
            reproducibility="code_series",
            lookahead_or_leakage_risks=["causal frac-diff on expanding history OK"],
            transferable_mechanism="Stationary features help regime models survive level shifts",
            qmx_overlap="Upstream of structural-break feature parts 9-10",
            qmx_possible_gap="Frac-diff not in V1 producers",
            testable_hypotheses=[],
            confidence=0.6,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            23410,
            topics=["GEX", "zero-gamma flip", "regime switch language"],
            market_mechanisms=["dealer gamma regime changes market behavior"],
            asset_or_venue_dependencies=["options/GEX mapping; equity index context"],
            time_horizons=["session/day GEX"],
            data_requirements=["options open interest/greeks external"],
            central_claims=[
                "Zero-gamma flip as regime switch in dealer hedging behavior",
            ],
            formulas=["GEX aggregation"],
            algorithms=["GEX mapping chart"],
            implementation_details=["MQL5 GEX tools"],
            execution_assumptions=["external options data"],
            cost_assumptions=[],
            risk_assumptions=["proxy quality"],
            evidence_level="microstructure_regime",
            reproducibility="partial",
            lookahead_or_leakage_risks=["GEX from prior OI is causal if dated correctly"],
            transferable_mechanism="Venue-specific regime switch from options positioning — Book context",
            qmx_overlap="Regime-switch vocabulary; crypto options sparse",
            qmx_possible_gap="No GEX in crypto V1",
            testable_hypotheses=[],
            confidence=0.58,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            18916,
            topics=["regime switches", "hybrid AR + U-Transformer", "adaptive switching"],
            market_mechanisms=["switch between linear and nonlinear residual model by quality"],
            asset_or_venue_dependencies=["FX forecasting EA"],
            time_horizons=["real-time claimed"],
            data_requirements=["25-feature AR + residuals"],
            central_claims=[
                "Hybrid system switches signal sources as market conditions change",
                "Mentions regime switches as nonlinearity challenge",
            ],
            formulas=[],
            algorithms=["AR + U-Transformer residuals"],
            implementation_details=["MarketSolver EA"],
            execution_assumptions=["bot with averaging/pyramiding"],
            cost_assumptions=[],
            risk_assumptions=["complex system overfit"],
            evidence_level="system_claim",
            reproducibility="mq5_attached",
            lookahead_or_leakage_risks=["training/residual pipeline leakage risk if not purged"],
            transferable_mechanism="Source-quality switch ≈ sensor confidence / not_ready pattern",
            qmx_overlap="Adaptation language",
            qmx_possible_gap="MIS already has degraded-sensors; not this NN",
            testable_hypotheses=[],
            confidence=0.5,
            supporting_excerpts=[
                "regime switches",
            ],
        )
    )

    rows.append(
        rec(
            1628,
            topics=["RBM", "HMM improvement", "deep network"],
            market_mechanisms=["HMM considered to improve DNN trading control"],
            asset_or_venue_dependencies=["GBPUSD session demo files"],
            time_horizons=["periodic retrain"],
            data_requirements=["predictors; darch DBN"],
            central_claims=[
                "Mentions using HMM to improve deep network trading self-control",
            ],
            formulas=[],
            algorithms=["Stacked RBM DBN", "HMM mention"],
            implementation_details=["R integration / darch era article"],
            execution_assumptions=["EA retrain on fly"],
            cost_assumptions=[],
            risk_assumptions=["old stack; reproducibility dated"],
            evidence_level="historical",
            reproducibility="low_today",
            lookahead_or_leakage_risks=["online retrain without purge"],
            transferable_mechanism="Early HMM-as-filter idea; prefer modern 15033/16830/17917",
            qmx_overlap="Historical HMM mention",
            qmx_possible_gap="n/a",
            testable_hypotheses=[],
            confidence=0.4,
            supporting_excerpts=[
                "possibility of using a hidden Markov model for improving",
            ],
        )
    )

    rows.append(
        rec(
            20590,
            topics=["HMC", "MCMC", "Bayesian sampling"],
            market_mechanisms=["posterior sampling — not market regime per se"],
            asset_or_venue_dependencies=[],
            time_horizons=[],
            data_requirements=[],
            central_claims=[
                "HMC MCMC sampling methods article — title Markov but not regime-switching",
            ],
            formulas=["Hamiltonian Monte Carlo"],
            algorithms=["HMC"],
            implementation_details=["statistics article"],
            execution_assumptions=[],
            cost_assumptions=["expensive sampling"],
            risk_assumptions=[],
            evidence_level="methods_offtopic_borderline",
            reproducibility="partial",
            lookahead_or_leakage_risks=[],
            transferable_mechanism="Bayesian uncertainty tooling only; not changeover detector",
            qmx_overlap="False friend: Markov in title != regime Markov-switching",
            qmx_possible_gap="No Hamilton filter article found under that name",
            testable_hypotheses=[],
            confidence=0.3,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            18785,
            topics=["ALGLIB Markov matrices", "quantum NN analogy"],
            market_mechanisms=["training on Markov matrices — weak regime link"],
            asset_or_venue_dependencies=[],
            time_horizons=[],
            data_requirements=[],
            central_claims=[
                "Uses ALGLIB Markov matrices in QNN training narrative; market regime change cited as failure mode of classical nets",
            ],
            formulas=[],
            algorithms=[],
            implementation_details=["SimpleQuantum EA"],
            execution_assumptions=["bot"],
            cost_assumptions=[],
            risk_assumptions=["unverifiable quantum analogy"],
            evidence_level="weak",
            reproducibility="mq5_attached",
            lookahead_or_leakage_risks=[],
            transferable_mechanism="None for CPD",
            qmx_overlap="Keyword-only",
            qmx_possible_gap="n/a",
            testable_hypotheses=[],
            confidence=0.25,
            supporting_excerpts=[
                "inability of traditional networks to adapt to changing market conditions",
            ],
        )
    )

    # Context siblings previously read — short records noting prior status
    rows.append(
        rec(
            23482,
            topics=["BOCPD", "run-length", "online change-point"],
            market_mechanisms=["run-length posterior; Normal-Gamma on log returns"],
            asset_or_venue_dependencies=["FX demo in prior pass"],
            time_horizons=["online per bar; lambda prior mean regime length"],
            data_requirements=["log returns"],
            central_claims=[
                "PRIOR FULL READ: online CPD with P(break)+E[run length]; three uses incl risk cooldown",
                "Best door-sensor pattern in prior 24 for MIS sit-out",
            ],
            formulas=["Adams-MacKay BOCPD"],
            algorithms=["BOCPD"],
            implementation_details=["MQL5 indicator"],
            execution_assumptions=["causal online"],
            cost_assumptions=["cheap once warm"],
            risk_assumptions=["slow mean shifts lag; lambda prior sensitive"],
            evidence_level="prior_pass",
            reproducibility="prior_notes",
            lookahead_or_leakage_risks=["causal if implemented as stated"],
            transferable_mechanism="cp_prob + run_length as Book/KSA sensor",
            qmx_overlap="OPERATING_LINE: recovered BOCPD unauthoritative; still best prior changeover ref",
            qmx_possible_gap="Promote shadow bocpd_* only after ARL-style calibration",
            testable_hypotheses=[],
            confidence=0.9,
            supporting_excerpts=[],
        )
    )

    rows.append(
        rec(
            16830,
            topics=["HMM", "Viterbi", "vol filter"],
            market_mechanisms=["2-state vol HMM filters MA-cross"],
            asset_or_venue_dependencies=["XAUUSD H1 prior"],
            time_horizons=["50-bar return sigma observation"],
            data_requirements=["rolling sigma; freeze matrices"],
            central_claims=[
                "PRIOR FULL READ: HMM as FILTER dropping ~70% trades; author caveats correlated observations",
            ],
            formulas=[],
            algorithms=["Viterbi current state"],
            implementation_details=["Python train paste MQL5"],
            execution_assumptions=["filter on backbone"],
            cost_assumptions=[],
            risk_assumptions=["may collapse to sigma threshold"],
            evidence_level="prior_pass",
            reproducibility="prior_notes",
            lookahead_or_leakage_risks=[
                "Viterbi path on batch can smooth; live needs care",
            ],
            transferable_mechanism="HMM as MIS filter candidate (shadow), not bot",
            qmx_overlap="Recovered HMM unauthoritative per OPERATING_LINE",
            qmx_possible_gap="Causal decode mode still underspecified in recovered path",
            testable_hypotheses=[],
            confidence=0.85,
            supporting_excerpts=[],
        )
    )

    return rows


def main() -> None:
    rows = build()
    out = OUT / "extractions" / "changeover.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} records to {out}")
    # corpus gaps note
    print("ids:", [r["article_id"] for r in rows])


if __name__ == "__main__":
    main()
