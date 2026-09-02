"""Story 26.17 — rule-based MIS labelers plus fitted liquidity_stress_v1."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar, cast

from qmf.core import (
    Duration,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Price,
    PriceDelta,
    RefusalCategory,
    UnitKind,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import Result
from qmn.host.light_heavy import (
    CompositionClass,
    FourBoundDeclaration,
    WorkloadClaim,
    WorkloadKind,
    evaluate_workload_claim,
)
from qmn.mis import (
    DEGRADED_SENSORS_PRODUCER_ID,
    FEED_STATE_PRODUCER_ID,
    FITTED_PRODUCER_IDS,
    GAP_EVENT_PRODUCER_ID,
    IDENTITY_PRODUCER_ID,
    LIQUIDITY_STRESS_PRODUCER_ID,
    MIS_PRODUCER_SURFACE,
    REGIME_CLASSIFIER_PRODUCER_ID,
    RULE_BASED_PRODUCER_IDS,
    SPREAD_STATE_PRODUCER_ID,
    SQS_PRODUCER_ID,
    UNAUTHORITATIVE_CANDIDATES,
    V1_GOVERNED_PRODUCER_IDS,
    CanonicalFeedState,
    FormulaNature,
    FrontierFrame,
    MisProducerCatalog,
    MisProducerRole,
    ProducerReadiness,
    SpreadState,
    SqsBaselineArtifact,
    assemble_governed_snapshot,
    configure_mis_producer,
    empty_mis_catalog,
    evaluate_mis_producer,
    exact_nearest_rank_quantile,
    fit_liquidity_quantiles,
    mis_formula,
    refuse_trained_regime_classifier,
    refuse_unauthoritative_candidate,
    register_mis_producer,
    sqs_baseline_key,
    v1_formula_catalog,
    v1_mis_inventory,
)

T = TypeVar("T")

_MIS_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "mis"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = 1_000_000_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _venue() -> VenueId:
    return _ok(VenueId.try_create("ctrader"))


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return _ok(Instrument.try_create(_venue(), symbol))


def _ratio(num: int, den: int = 1) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


def _count(value: int) -> ExactRational:
    return _ok(ExactRational.try_create(value, 1, UnitKind.COUNT))


def _price(value: int, instrument: Instrument | None = None) -> Price:
    return _ok(Price.try_create(value, instrument or _instrument(), 5))


def _delta(value: int, instrument: Instrument | None = None) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, instrument or _instrument(), 5))


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "cite", "label": label}))


def _frame(**overrides: object) -> FrontierFrame:
    instrument = _instrument()
    known = _instant(1_000_000_000)
    body: dict[str, object] = {
        "frontier_instant": _instant(1_000_000_000),
        "instrument": instrument,
        "environment": "live",
        "resolution": "tick",
        "known_at": known,
        "bid": _price(100_000, instrument),
        "ask": _price(100_012, instrument),
        "pip": _delta(1, instrument),
        "last_tick_at": _instant(999_000_000),
        "bar_gap_count": 0,
        "sample_cadence": "quote",
        "previous_sqs_hard_block": False,
        "current_depth": 50,
        "current_spread_ticks": 12,
    }
    body.update(overrides)
    return FrontierFrame(**body)  # type: ignore[arg-type]


def _sqs_params() -> dict[str, object]:
    return {
        "hard_block_threshold": _ratio(3, 5),
        "hysteresis_band": _ratio(1, 20),
        "outlier_guard_multiple": _ratio(4, 1),
        "sample_cadence": "quote",
        "staleness_horizon": _duration(2_000_000_000),
        "baseline_statistic": "mean",
        "session_window_id": "london",
        "decision_freshness_bound": _duration(5_000_000_000),
    }


def _baseline(*, environment: str = "live", average: int = 10) -> SqsBaselineArtifact:
    instrument = _instrument()
    key = _ok(sqs_baseline_key(_venue(), environment, instrument))
    return SqsBaselineArtifact(
        key=key,
        average_spread=_delta(average, instrument),
        session_window_id="london",
        statistic="mean",
        refit_series_id="sqs-refit-series-1",
        refit_policy_fp=_fp("sqs-refit-policy"),
        dispersion=_delta(2, instrument),
    )


def _register_all() -> MisProducerCatalog:
    catalog = empty_mis_catalog()
    configs = {
        IDENTITY_PRODUCER_ID: {},
        SPREAD_STATE_PRODUCER_ID: {"normal_max": _count(12), "elevated_max": _count(25)},
        GAP_EVENT_PRODUCER_ID: {
            "max_expected_tick_gap": _duration(1_500_000_000),
            "max_expected_bar_gap_count": 1,
        },
        FEED_STATE_PRODUCER_ID: {
            "live_max_age": _duration(1_000_000_000),
            "degraded_max_age": _duration(5_000_000_000),
        },
        SQS_PRODUCER_ID: _sqs_params(),
        DEGRADED_SENSORS_PRODUCER_ID: {},
        LIQUIDITY_STRESS_PRODUCER_ID: {
            "spread_stress_quantile": _ratio(95, 100),
            "depth_stress_quantile": _ratio(5, 100),
        },
    }
    calendars = {SQS_PRODUCER_ID: ("market-hours-calendar:forex-17NY",)}
    for producer_id, params in configs.items():
        configured = _ok(
            configure_mis_producer(
                producer_id,
                parameters=params,
                calendar_requirements=calendars.get(producer_id, ()),
                warm_up=0
                if producer_id in {IDENTITY_PRODUCER_ID, DEGRADED_SENSORS_PRODUCER_ID}
                else 1,
            )
        )
        catalog = _ok(register_mis_producer(catalog, configured))
    return catalog


def test_v1_inventory_is_six_rule_based_plus_fitted_liquidity() -> None:
    inventory = v1_mis_inventory()
    assert inventory["rule_based"] == list(RULE_BASED_PRODUCER_IDS)
    assert inventory["fitted"] == list(FITTED_PRODUCER_IDS)
    assert inventory["trained_unbound"] == [REGIME_CLASSIFIER_PRODUCER_ID]
    assert inventory["governed_v1"] == list(V1_GOVERNED_PRODUCER_IDS)
    assert inventory["regime_classifier_bound"] is False
    assert inventory["trained_model_selected"] is False
    candidates = cast("list[str]", inventory["unauthoritative_candidates"])
    assert set(candidates) == UNAUTHORITATIVE_CANDIDATES
    formulas = v1_formula_catalog()
    assert [row.producer_id for row in formulas] == list(V1_GOVERNED_PRODUCER_IDS)
    assert all(row.nature is FormulaNature.RULE_BASED for row in formulas[:6])
    assert formulas[-1].nature is FormulaNature.FITTED
    assert MIS_PRODUCER_SURFACE == "qmn.mis.catalog"
    assert REGIME_CLASSIFIER_PRODUCER_ID not in {row.producer_id for row in formulas}


def test_each_producer_has_versioned_identity_inputs_and_fp1() -> None:
    for producer_id in V1_GOVERNED_PRODUCER_IDS:
        row = _ok(mis_formula(producer_id))
        assert row.version == "v1"
        assert row.inputs
        assert row.outputs
        assert row.formula_id.endswith("_v1") or row.formula_id.endswith("sensor_v1")
        configured = _ok(
            configure_mis_producer(
                producer_id,
                parameters=_params_for(producer_id),
                warm_up=0,
            )
        )
        fp = _ok(configured.fingerprint())
        assert fp.value.startswith("fp1:")
        again = _ok(
            configure_mis_producer(
                producer_id,
                parameters=_params_for(producer_id),
                warm_up=0,
            )
        )
        assert _ok(again.fingerprint()) == fp
        identity = configured.fp1_identity()
        for key in (
            "formula_id",
            "contract_format_version",
            "parameters",
            "inputs",
            "alignment_policy",
            "missing_value_policy",
            "warm_up",
            "supported_modes",
        ):
            assert key in identity
        assert "declared_budget" not in identity


def _params_for(producer_id: str) -> dict[str, object]:
    mapping: dict[str, dict[str, object]] = {
        IDENTITY_PRODUCER_ID: {},
        SPREAD_STATE_PRODUCER_ID: {"normal_max": _count(12), "elevated_max": _count(25)},
        GAP_EVENT_PRODUCER_ID: {
            "max_expected_tick_gap": _duration(1_500_000_000),
            "max_expected_bar_gap_count": 1,
        },
        FEED_STATE_PRODUCER_ID: {
            "live_max_age": _duration(1_000_000_000),
            "degraded_max_age": _duration(5_000_000_000),
        },
        SQS_PRODUCER_ID: _sqs_params(),
        DEGRADED_SENSORS_PRODUCER_ID: {},
        LIQUIDITY_STRESS_PRODUCER_ID: {
            "spread_stress_quantile": _ratio(95, 100),
            "depth_stress_quantile": _ratio(5, 100),
        },
    }
    return mapping[producer_id]


def test_missing_declared_parameters_refused_no_invented_defaults() -> None:
    refused = configure_mis_producer(SPREAD_STATE_PRODUCER_ID, parameters={})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert "normal_max" in str(refused.context["missing"])


def test_forward_fill_alignment_is_policy_rejection() -> None:
    refused = configure_mis_producer(
        IDENTITY_PRODUCER_ID,
        alignment_policy="forward-fill",
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_float_parameter_refused() -> None:
    refused = configure_mis_producer(
        SPREAD_STATE_PRODUCER_ID,
        parameters={"normal_max": 12.0, "elevated_max": _count(25)},
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_regime_classifier_not_selected_trained_registered_or_bound() -> None:
    assert is_refusal(mis_formula(REGIME_CLASSIFIER_PRODUCER_ID))
    assert is_refusal(configure_mis_producer(REGIME_CLASSIFIER_PRODUCER_ID))
    catalog = empty_mis_catalog()
    identity = _ok(configure_mis_producer(IDENTITY_PRODUCER_ID))
    # Cannot sneak the trained id through registration of a V1 producer renamed.
    bound = refuse_trained_regime_classifier("regime_classifier_v1")
    assert is_refusal(bound)
    assert bound.category is RefusalCategory.POLICY_REJECTION
    registered = register_mis_producer(catalog, identity)
    assert is_ok(registered)
    assert REGIME_CLASSIFIER_PRODUCER_ID not in registered.value.producers


def test_unauthoritative_candidates_have_no_authority() -> None:
    for name in ("kronos", "HMM", "bocpd", "ms-garch"):
        refused = refuse_unauthoritative_candidate(name)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert is_refusal(mis_formula(name))
        assert is_refusal(configure_mis_producer(name))


def test_candidate_role_refused_this_story() -> None:
    producer = _ok(configure_mis_producer(IDENTITY_PRODUCER_ID))
    refused = register_mis_producer(
        empty_mis_catalog(),
        producer,
        role=MisProducerRole.CANDIDATE,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_identity_spread_gap_feed_sqs_degraded_and_liquidity_evaluate() -> None:
    catalog = _register_all()
    frame = _frame()
    bound = _duration(5_000_000_000)
    fit = _ok(
        fit_liquidity_quantiles(
            spread_samples=(8, 9, 10, 11, 12, 40),
            depth_samples=(10, 20, 30, 40, 50, 60),
            spread_quantile=_ratio(95, 100),
            depth_quantile=_ratio(5, 100),
        )
    )
    identity = _ok(
        evaluate_mis_producer(
            catalog.producers[IDENTITY_PRODUCER_ID], frame, decision_freshness_bound=bound
        )
    )
    assert identity.identity_key is not None
    assert "EURUSD" in identity.identity_key

    spread = _ok(
        evaluate_mis_producer(
            catalog.producers[SPREAD_STATE_PRODUCER_ID],
            frame,
            decision_freshness_bound=bound,
        )
    )
    assert spread.spread_state is SpreadState.NORMAL

    gap = _ok(
        evaluate_mis_producer(
            catalog.producers[GAP_EVENT_PRODUCER_ID],
            frame,
            decision_freshness_bound=bound,
        )
    )
    assert gap.gap_event is False

    feed = _ok(
        evaluate_mis_producer(
            catalog.producers[FEED_STATE_PRODUCER_ID],
            frame,
            decision_freshness_bound=bound,
        )
    )
    assert feed.feed_state is CanonicalFeedState.LIVE

    sqs = _ok(
        evaluate_mis_producer(
            catalog.producers[SQS_PRODUCER_ID],
            frame,
            sqs_baseline=_baseline(average=12),
            decision_freshness_bound=bound,
        )
    )
    assert sqs.sqs is not None
    assert sqs.sqs.hard_block is False
    assert sqs.sqs.score is not None

    snap = _ok(
        assemble_governed_snapshot(
            catalog,
            frame,
            decision_freshness_bound=bound,
            sqs_baseline=_baseline(average=12),
            liquidity_fit=fit,
        )
    )
    assert set(snap.producers) == set(V1_GOVERNED_PRODUCER_IDS)
    assert snap.feed_state is CanonicalFeedState.LIVE
    assert snap.degraded_sensors == ()
    assert snap.sqs_for(_instrument()) is not None


def test_spread_state_thresholds_and_extreme() -> None:
    producer = _ok(
        configure_mis_producer(
            SPREAD_STATE_PRODUCER_ID,
            parameters={"normal_max": _count(12), "elevated_max": _count(25)},
        )
    )
    elevated = _ok(
        evaluate_mis_producer(
            producer,
            _frame(spread_points=_count(20)),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert elevated.spread_state is SpreadState.ELEVATED
    extreme = _ok(
        evaluate_mis_producer(
            producer,
            _frame(spread_points=_count(40)),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert extreme.spread_state is SpreadState.EXTREME


def test_gap_event_true_on_tick_gap() -> None:
    producer = _ok(
        configure_mis_producer(
            GAP_EVENT_PRODUCER_ID,
            parameters={
                "max_expected_tick_gap": _duration(1_500_000_000),
                "max_expected_bar_gap_count": 1,
            },
        )
    )
    emission = _ok(
        evaluate_mis_producer(
            producer,
            _frame(last_tick_at=_instant(1_000_000_000 - 2_000_000_000)),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert emission.gap_event is True


def test_feed_state_live_degraded_dead() -> None:
    producer = _ok(
        configure_mis_producer(
            FEED_STATE_PRODUCER_ID,
            parameters={
                "live_max_age": _duration(1_000_000_000),
                "degraded_max_age": _duration(5_000_000_000),
            },
        )
    )
    bound = _duration(10_000_000_000)
    live = _ok(
        evaluate_mis_producer(
            producer,
            _frame(last_tick_at=_instant(500_000_000), known_at=_instant(500_000_000)),
            decision_freshness_bound=bound,
        )
    )
    assert live.feed_state is CanonicalFeedState.LIVE
    degraded = _ok(
        evaluate_mis_producer(
            producer,
            _frame(
                last_tick_at=_instant(1_000_000_000 - 2_000_000_000),
                known_at=_instant(1_000_000_000 - 2_000_000_000),
            ),
            decision_freshness_bound=bound,
        )
    )
    assert degraded.feed_state is CanonicalFeedState.DEGRADED
    dead = _ok(
        evaluate_mis_producer(
            producer,
            _frame(
                last_tick_at=_instant(1_000_000_000 - 6_000_000_000),
                known_at=_instant(1_000_000_000 - 6_000_000_000),
            ),
            decision_freshness_bound=bound,
        )
    )
    assert dead.feed_state is CanonicalFeedState.DEAD


def test_sqs_formula_threshold_hysteresis_and_conservative_sentinel() -> None:
    producer = _ok(configure_mis_producer(SQS_PRODUCER_ID, parameters=_sqs_params()))
    bound = _duration(5_000_000_000)
    # score = 10/20 = 0.5 < 0.6 → hard block
    blocked = _ok(
        evaluate_mis_producer(
            producer,
            _frame(
                bid=_price(100_000),
                ask=_price(100_020),
                spread=_delta(20),
            ),
            sqs_baseline=_baseline(average=10),
            decision_freshness_bound=bound,
        )
    )
    assert blocked.sqs is not None
    assert blocked.sqs.hard_block is True
    assert blocked.sqs.score is not None
    assert blocked.sqs.score.as_fraction() == _ratio(1, 2).as_fraction()

    # at-or-above threshold passes: 10/10 = 1.0
    passed = _ok(
        evaluate_mis_producer(
            producer,
            _frame(spread=_delta(10), bid=_price(100_000), ask=_price(100_010)),
            sqs_baseline=_baseline(average=10),
            decision_freshness_bound=bound,
        )
    )
    assert passed.sqs is not None
    assert passed.sqs.hard_block is False

    # hysteresis: previously blocked, score 0.62 < 0.65 stays blocked
    stay = _ok(
        evaluate_mis_producer(
            producer,
            _frame(
                spread=_delta(100),
                bid=_price(10_000),
                ask=_price(10_100),
                previous_sqs_hard_block=True,
            ),
            sqs_baseline=_baseline(average=62),
            decision_freshness_bound=bound,
        )
    )
    # 62/100 = 0.62; threshold 0.6 + band 0.05 = 0.65
    assert stay.sqs is not None
    assert stay.sqs.hard_block is True

    missing = _ok(
        evaluate_mis_producer(
            producer,
            _frame(),
            sqs_baseline=None,
            decision_freshness_bound=bound,
        )
    )
    assert missing.readiness is ProducerReadiness.NOT_READY
    assert missing.sqs is not None
    assert missing.sqs.hard_block is True
    assert missing.sqs.score is None


def test_bar_sampled_sqs_refused() -> None:
    bar_params = dict(_sqs_params())
    bar_params["sample_cadence"] = "bar"
    bar_producer = _ok(configure_mis_producer(SQS_PRODUCER_ID, parameters=bar_params))
    refused = evaluate_mis_producer(
        bar_producer,
        _frame(),
        sqs_baseline=_baseline(),
        decision_freshness_bound=_duration(5_000_000_000),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_demo_baseline_cannot_satisfy_live_frame() -> None:
    producer = _ok(configure_mis_producer(SQS_PRODUCER_ID, parameters=_sqs_params()))
    refused = evaluate_mis_producer(
        producer,
        _frame(environment="live"),
        sqs_baseline=_baseline(environment="demo"),
        decision_freshness_bound=_duration(5_000_000_000),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_lookahead_known_at_refused() -> None:
    producer = _ok(
        configure_mis_producer(
            FEED_STATE_PRODUCER_ID,
            parameters={
                "live_max_age": _duration(1_000_000_000),
                "degraded_max_age": _duration(5_000_000_000),
            },
        )
    )
    refused = evaluate_mis_producer(
        producer,
        _frame(known_at=_instant(2_000_000_000)),
        decision_freshness_bound=_duration(5_000_000_000),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_stale_input_publishes_not_ready_or_sqs_stale() -> None:
    feed = _ok(
        configure_mis_producer(
            FEED_STATE_PRODUCER_ID,
            parameters={
                "live_max_age": _duration(1_000_000_000),
                "degraded_max_age": _duration(5_000_000_000),
            },
        )
    )
    late = _ok(
        evaluate_mis_producer(
            feed,
            _frame(known_at=_instant(1_000_000_000 - 6_000_000_000)),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert late.readiness is ProducerReadiness.NOT_READY

    sqs = _ok(configure_mis_producer(SQS_PRODUCER_ID, parameters=_sqs_params()))
    stale = _ok(
        evaluate_mis_producer(
            sqs,
            _frame(known_at=_instant(1_000_000_000 - 6_000_000_000)),
            sqs_baseline=_baseline(),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert stale.readiness is ProducerReadiness.STALE
    assert stale.sqs is not None
    assert stale.sqs.hard_block is True


def test_degraded_sensors_lists_non_ok_peers() -> None:
    producer = _ok(configure_mis_producer(DEGRADED_SENSORS_PRODUCER_ID))
    peers = (
        _ok(evaluate_mis_producer(_ok(configure_mis_producer(IDENTITY_PRODUCER_ID)), _frame())),
        _ok(
            evaluate_mis_producer(
                _ok(configure_mis_producer(SQS_PRODUCER_ID, parameters=_sqs_params())),
                _frame(),
                sqs_baseline=None,
                decision_freshness_bound=_duration(5_000_000_000),
            )
        ),
    )
    emission = _ok(evaluate_mis_producer(producer, _frame(peer_emissions=peers)))
    assert emission.degraded_sensors == (SQS_PRODUCER_ID,)


def test_liquidity_cpu_quantile_fit_and_stress_label() -> None:
    q95 = _ratio(95, 100)
    q05 = _ratio(5, 100)
    fit = _ok(
        fit_liquidity_quantiles(
            spread_samples=(10, 11, 12, 13, 14, 100),
            depth_samples=(5, 20, 30, 40, 50, 60),
            spread_quantile=q95,
            depth_quantile=q05,
        )
    )
    assert fit.spread_quantile_value == 100
    assert fit.depth_quantile_value == 5
    assert _ok(fit.fingerprint()).value.startswith("fp1:")

    producer = _ok(
        configure_mis_producer(
            LIQUIDITY_STRESS_PRODUCER_ID,
            parameters={"spread_stress_quantile": q95, "depth_stress_quantile": q05},
            warm_up=1,
        )
    )
    stressed = _ok(
        evaluate_mis_producer(
            producer,
            _frame(current_spread_ticks=100, current_depth=50),
            liquidity_fit=fit,
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert stressed.liquidity_stress is True
    calm = _ok(
        evaluate_mis_producer(
            producer,
            _frame(current_spread_ticks=12, current_depth=40),
            liquidity_fit=fit,
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert calm.liquidity_stress is False
    missing_fit = _ok(
        evaluate_mis_producer(
            producer,
            _frame(),
            liquidity_fit=None,
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert missing_fit.readiness is ProducerReadiness.NOT_READY


def test_quantile_fit_refuses_floats_and_empty() -> None:
    empty = fit_liquidity_quantiles(
        spread_samples=(),
        depth_samples=(1,),
        spread_quantile=_ratio(1, 2),
        depth_quantile=_ratio(1, 2),
    )
    assert is_refusal(empty)
    floated = fit_liquidity_quantiles(
        spread_samples=(1.5,),  # type: ignore[arg-type]
        depth_samples=(1,),
        spread_quantile=_ratio(1, 2),
        depth_quantile=_ratio(1, 2),
    )
    assert is_refusal(floated)
    q = _ok(exact_nearest_rank_quantile((1, 2, 3, 4), _ratio(1, 2)))
    assert q == 2


def test_ad24_heavy_by_default_light_claim_refused_without_baseline() -> None:
    configured = _ok(configure_mis_producer(IDENTITY_PRODUCER_ID))
    assert configured.declared_budget is None
    claim = _ok(
        WorkloadClaim.try_create(
            kind=WorkloadKind.LABELER,
            definition_fp=_ok(configured.fingerprint()),
            live_path_baseline_present=False,
        )
    )
    assignment = _ok(evaluate_workload_claim(claim))
    assert assignment.effective_class is CompositionClass.HEAVY

    bounds = _ok(
        FourBoundDeclaration.try_create(
            per_update_cost_rung="live-path",
            bounded_state=True,
            window_or_anchor_rule="frontier-as-of",
            synchronous_availability=True,
        )
    )
    light_claim = _ok(
        WorkloadClaim.try_create(
            kind=WorkloadKind.PRODUCER,
            definition_fp=_ok(configured.fingerprint()),
            declared_bounds=bounds,
            live_path_baseline_present=False,
            benchmark_proven=True,
        )
    )
    refused = evaluate_workload_claim(light_claim)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_liquidity_and_labeler_modules_stay_cpu_stdlib() -> None:
    banned = ("numpy", "torch", "sklearn", "tensorflow", "jax")
    for path in (
        _MIS_SRC / "liquidity.py",
        _MIS_SRC / "labelers.py",
        _MIS_SRC / "catalog.py",
        _MIS_SRC / "shadow.py",
    ):
        text = path.read_text(encoding="utf-8")
        for name in banned:
            assert f"import {name}" not in text
            assert f"from {name}" not in text
