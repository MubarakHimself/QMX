"""Story 14.7 — tier-2 golden-slice determinism and run-id reproduction."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from qmb.config import CLOCK_SIMULATED, ResolvedRunConfig
from qmb.doors import api
from qmb.results import (
    CHART_SERIES_IN_IDENTITY,
    CONCURRENCY_IS_SCHEDULING_ONLY,
    HTML_PAYLOAD,
    MEASURE_IDENTITIES,
    RESULT_CONTRACT,
    mint_run_performance_result,
    require_reproduced_fingerprint,
    result_identity,
)
from qmb.runloop import (
    STREAM_SET_KEY,
    CancelToken,
    LoopOutcome,
    SilentSliceHandler,
    SliceObservation,
    loop_identity,
    reproduce_run,
    run,
)
from qmf.core.chrono import CalendarIdentity, Instant
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.identity import AccountRole
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.performance import PerformanceResult

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS, *, closed: bool = True) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), closed))


def _config(
    *,
    streams: tuple[str, ...] = ("eurusd", "gbpusd"),
    **keys: object,
) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "golden-cfg", "streams": list(streams)}))
    payload: dict[str, object] = {STREAM_SET_KEY: streams}
    payload.update(keys)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=payload,
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _slices(
    streams: tuple[str, ...] = ("eurusd", "gbpusd"),
) -> tuple[tuple[SliceObservation, ...], ...]:
    first = tuple(_obs(stream_id, _NS) for stream_id in streams)
    second = tuple(_obs(stream_id, _NS + 1) for stream_id in streams)
    return (first, second)


def _run(
    *,
    config: ResolvedRunConfig | None = None,
    streams: tuple[str, ...] = ("eurusd", "gbpusd"),
    handler: object = None,
) -> LoopOutcome:
    bound = config if config is not None else _config(streams=streams)
    return _ok(
        run(
            slices=_slices(streams),
            config=bound,
            handler=SilentSliceHandler() if handler is None else handler,
        )
    )


def _ct32_fp(outcome: LoopOutcome) -> str:
    return _ok(outcome.ct32_fingerprint()).value


def test_result_identity_excludes_charts_html_and_semver() -> None:
    payload = result_identity()
    assert payload["contract"] == RESULT_CONTRACT
    assert payload["chart_series_in_identity"] is False
    assert payload["html_payload"] is False
    assert payload["concurrency_is_scheduling_only"] is True
    assert payload["measure_identities"] == list(MEASURE_IDENTITIES)
    assert qmb.__version__ not in payload.values()
    assert CHART_SERIES_IN_IDENTITY is False
    assert HTML_PAYLOAD is False
    assert CONCURRENCY_IS_SCHEDULING_ONLY is True
    assert loop_identity()["concurrency_is_scheduling_only"] is True
    assert loop_identity()["pure_run_independent_of_siblings"] is True


def test_two_identical_runs_share_ct32_fingerprint() -> None:
    config = _config()
    first = _run(config=config)
    second = _run(config=config)
    left = _ct32_fp(first)
    right = _ct32_fp(second)
    assert left == right
    assert left.startswith("fp1:sha256:")
    assert first.fp1_identity() == second.fp1_identity()
    assert "performance_result" not in first.fp1_identity()
    assert "chart" not in first.fp1_identity()
    assert "html" not in first.fp1_identity()
    artifact = first.performance_result
    assert isinstance(artifact, PerformanceResult)
    identity = artifact.fp1_identity()
    assert "chart" not in identity
    assert "html" not in identity
    assert [row.measure_identity for row in artifact.measure_set] == list(MEASURE_IDENTITIES)
    assert all(row.quantity.unit_kind is UnitKind.COUNT for row in artifact.measure_set)
    assert artifact.suppression_accounting == ()
    assert artifact.veto_accounting == ()
    assert artifact.account_binding_role is AccountRole.DEMO
    assert artifact.result_label.world is World.REPLAY
    assert first.self_assessment["result_contract"] == RESULT_CONTRACT
    assert first.self_assessment["ct32_fingerprint"] == left


def test_rerun_under_resolved_config_reproduces_or_refuses() -> None:
    config = _config()
    original = _run(config=config)
    expected = _ok(original.ct32_fingerprint())
    reproduced = _ok(
        reproduce_run(
            run_id=config.fingerprint,
            config=config,
            expected_fingerprint=expected,
            slices=_slices(),
            handler=SilentSliceHandler(),
        )
    )
    assert _ok(reproduced.fingerprint()) == expected
    other = _ok(fingerprint({"n": "not-this-run"}))
    mismatch = reproduce_run(
        run_id=config.fingerprint,
        config=config,
        expected_fingerprint=other,
        slices=_slices(),
        handler=SilentSliceHandler(),
    )
    assert is_refusal(mismatch)
    assert mismatch.category is RefusalCategory.POLICY_REJECTION
    assert mismatch.context["field"] == "ct32_fingerprint"
    wrong_id = reproduce_run(
        run_id=other,
        config=config,
        expected_fingerprint=expected,
        slices=_slices(),
    )
    assert is_refusal(wrong_id)
    assert wrong_id.category is RefusalCategory.INVALID_INPUT
    assert wrong_id.context["field"] == "run_id"
    compared = require_reproduced_fingerprint(expected, other, run_id=config.fingerprint)
    assert is_refusal(compared)
    assert compared.category is RefusalCategory.POLICY_REJECTION


def test_stream_set_order_is_identity_bearing_for_ct32() -> None:
    left = _ct32_fp(_run(config=_config(streams=("eurusd", "gbpusd"))))
    right = _ct32_fp(_run(config=_config(streams=("gbpusd", "eurusd"))))
    assert left != right


def test_configless_run_emits_no_governed_result() -> None:
    outcome = _ok(
        run(
            slices=_slices(("eurusd",)),
            stream_set=("eurusd",),
            handler=SilentSliceHandler(),
        )
    )
    assert outcome.performance_result is None
    refused = outcome.ct32_fingerprint()
    assert is_refusal(refused)
    assert refused.context["field"] == "performance_result"


def test_abort_emits_no_partial_governed_result() -> None:
    token = CancelToken()
    _ok(token.cancel())
    aborted = run(
        slices=_slices(),
        config=_config(),
        cancel=token,
        handler=SilentSliceHandler(),
    )
    assert is_refusal(aborted)
    assert aborted.context["terminal"] == "aborted"
    assert "performance_result" not in aborted.context


def test_non_replay_world_refuses_ct32() -> None:
    stamp = _ok(fingerprint({"n": "live-cfg"}))
    live = ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.LIVE,
        fingerprint=stamp,
    )
    refused = run(slices=((_obs("eurusd"),),), config=live)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "world"
    simulated = mint_run_performance_result(
        ResolvedRunConfig(
            format_version=1,
            book_fp1=stamp,
            bms_fp1=stamp,
            bot_fp1=stamp,
            book_fragment_fp1=stamp,
            bms_fragment_fp1=stamp,
            keys={STREAM_SET_KEY: ("eurusd",)},
            clock=CLOCK_SIMULATED,
            data_provenance="synthetic-tainted",
            world=World.SIMULATED,
            fingerprint=stamp,
        ),
        evidence_range=_ok(run(slices=((_obs("eurusd"),),), stream_set=("eurusd",))).evidence_range,
        stream_order=("eurusd",),
        slice_count=1,
        filled_count=0,
        resting_count=0,
        data_points_processed=1,
        outcome_identity={"class": "event-slice-loop-outcome"},
    )
    assert is_refusal(simulated)
    assert simulated.category is RefusalCategory.POLICY_REJECTION


def test_concurrent_siblings_are_scheduling_only() -> None:
    config = _config()
    isolated = _ct32_fp(_run(config=config))

    def isolated_again() -> str:
        return _ct32_fp(_run(config=config))

    def sibling() -> str:
        other = _config(streams=("usdjpy",))
        return _ct32_fp(_run(config=other, streams=("usdjpy",)))

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(isolated_again)
        extra = pool.submit(sibling)
        second = pool.submit(isolated_again)
        concurrent_a = first.result()
        concurrent_b = second.result()
        sibling_fp = extra.result()
    assert concurrent_a == isolated
    assert concurrent_b == isolated
    assert sibling_fp != isolated
    assert api.reproduce_run is qmb.reproduce_run
    assert api.require_reproduced_fingerprint is qmb.require_reproduced_fingerprint
    assert api.mint_run_performance_result is qmb.mint_run_performance_result
    assert api.PerformanceResult is qmb.PerformanceResult
    assert api.RESULT_CONTRACT == RESULT_CONTRACT


def test_mint_refuses_malformed_inputs_and_honors_overrides() -> None:
    outcome = _run()
    dummy = {
        "evidence_range": outcome.evidence_range,
        "stream_order": outcome.stream_order,
        "slice_count": 1,
        "filled_count": 0,
        "resting_count": 0,
        "data_points_processed": 1,
        "outcome_identity": outcome.fp1_identity(),
    }
    assert is_refusal(mint_run_performance_result("not-config", **dummy))
    assert is_refusal(
        mint_run_performance_result(
            _config(),
            evidence_range="nope",
            stream_order=outcome.stream_order,
            slice_count=1,
            filled_count=0,
            resting_count=0,
            data_points_processed=1,
            outcome_identity=outcome.fp1_identity(),
        )
    )
    assert is_refusal(
        mint_run_performance_result(
            _config(),
            evidence_range=outcome.evidence_range,
            stream_order="eurusd",
            slice_count=1,
            filled_count=0,
            resting_count=0,
            data_points_processed=1,
            outcome_identity=outcome.fp1_identity(),
        )
    )
    assert is_refusal(
        mint_run_performance_result(
            _config(),
            evidence_range=outcome.evidence_range,
            stream_order=("eurusd", ""),
            slice_count=1,
            filled_count=0,
            resting_count=0,
            data_points_processed=1,
            outcome_identity=outcome.fp1_identity(),
        )
    )
    for kwargs in (
        {"slice_count": True},
        {"filled_count": -1},
        {"resting_count": -1},
        {"data_points_processed": -1},
    ):
        body = {
            "evidence_range": outcome.evidence_range,
            "stream_order": outcome.stream_order,
            "slice_count": 1,
            "filled_count": 0,
            "resting_count": 0,
            "data_points_processed": 1,
            "outcome_identity": outcome.fp1_identity(),
        }
        body.update(kwargs)
        assert is_refusal(mint_run_performance_result(_config(), **body))
    assert is_refusal(
        mint_run_performance_result(
            _config(),
            evidence_range=outcome.evidence_range,
            stream_order=outcome.stream_order,
            slice_count=1,
            filled_count=0,
            resting_count=0,
            data_points_processed=1,
            outcome_identity=["not-a-mapping"],
        )
    )
    expected = _ok(outcome.ct32_fingerprint())
    assert is_refusal(require_reproduced_fingerprint("left", "right"))
    assert is_refusal(require_reproduced_fingerprint(expected, "right"))
    assert is_refusal(require_reproduced_fingerprint(expected, _ok(fingerprint({"n": "x"}))))
    assert is_refusal(reproduce_run(run_id="x", config="y", expected_fingerprint="z", slices=()))
    assert is_refusal(
        reproduce_run(
            run_id="x",
            config=_config(),
            expected_fingerprint=expected,
            slices=_slices(),
        )
    )
    cancelled = CancelToken()
    _ok(cancelled.cancel())
    aborted = reproduce_run(
        run_id=_config().fingerprint,
        config=_config(),
        expected_fingerprint=expected,
        slices=_slices(),
        cancel=cancelled,
    )
    assert is_refusal(aborted)
    stamp = _ok(fingerprint({"n": "unbound-epoch"}))
    unbound = ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd", "gbpusd")},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
    )
    assert _run(config=unbound).performance_result is not None
    blank_role = run(
        slices=_slices(),
        config=_config(account_role="  "),
        handler=SilentSliceHandler(),
    )
    assert is_refusal(blank_role)
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2024a"))
    overridden = _run(
        config=_config(
            account_role=AccountRole.PAPER_VALIDATION,
            calendar=calendar,
        )
    )
    artifact = overridden.performance_result
    assert artifact is not None
    assert artifact.account_binding_role is AccountRole.PAPER_VALIDATION
    assert artifact.period.calendar == calendar
    mapped = _run(
        config=_config(
            account_role="demo",
            calendar={
                "rule_set": "qmb-replay",
                "rule_set_version": "v1",
                "tzdata_version": "UTC",
            },
        )
    )
    assert mapped.performance_result is not None
    assert mapped.performance_result.account_binding_role is AccountRole.DEMO
    bad_role = run(
        slices=_slices(),
        config=_config(account_role="not-a-role"),
        handler=SilentSliceHandler(),
    )
    assert is_refusal(bad_role)
    bad_calendar = run(
        slices=_slices(),
        config=_config(calendar=1),
        handler=SilentSliceHandler(),
    )
    assert is_refusal(bad_calendar)
