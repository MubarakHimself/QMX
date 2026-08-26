"""Story 19.1 — canonical CT-32 artifact, full AD-12 label, results/ assembly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar, cast

from qmb.config import CLOCK_SIMULATED, ResolvedRunConfig
from qmb.doors import api
from qmb.execution import COMPOSITION_VERSION, TAINT_OPTIMISTIC, stamp_fidelity
from qmb.results import (
    ACCOUNT_ROLE_KEY,
    CT32_ARTIFACT_NAME,
    CT32_ARTIFACT_RELATIVE_PATH,
    DATA_FINGERPRINT_KEY,
    FIDELITY_KEY,
    REGISTRY_AS_OF_KEY,
    RESULT_CONTRACT,
    RESULTS_DIR_NAME,
    RNG_PROVENANCE_KEY,
    SPLIT_FINGERPRINT_KEY,
    assemble_run_performance_result,
    ct32_artifact_path,
    mint_run_performance_result,
    result_identity,
)
from qmb.runloop import (
    STREAM_SET_KEY,
    LoopOutcome,
    SilentSliceHandler,
    SliceObservation,
    run,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import EvidenceClass, World, canonical_bytes, fingerprint
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
    stamp = _ok(
        fingerprint({"n": "ct32-artifact-cfg", "streams": list(streams), "keys": sorted(keys)})
    )
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


def _run(*, config: ResolvedRunConfig | None = None) -> LoopOutcome:
    bound = config if config is not None else _config()
    return _ok(run(slices=_slices(), config=bound, handler=SilentSliceHandler()))


def test_result_identity_never_claims_edge_or_charts() -> None:
    payload = result_identity()
    assert payload["contract"] == RESULT_CONTRACT
    assert payload["claims_edge"] is False
    assert payload["spends_split_budget"] is False
    assert payload["chart_series_in_identity"] is False
    assert payload["html_payload"] is False
    assert qmb.__version__ not in payload.values()


def test_assembly_writes_exactly_one_ct32_and_returns_fp1(tmp_path: Path) -> None:
    outcome = _run()
    artifact = outcome.performance_result
    assert isinstance(artifact, PerformanceResult)
    stamped = _ok(assemble_run_performance_result(outcome, output_dir=tmp_path))
    path = tmp_path / RESULTS_DIR_NAME / CT32_ARTIFACT_NAME
    assert path.is_file()
    assert list((tmp_path / RESULTS_DIR_NAME).iterdir()) == [path]
    assert not (tmp_path / "report.json").exists()
    assert f"{RESULTS_DIR_NAME}/{CT32_ARTIFACT_NAME}" == CT32_ARTIFACT_RELATIVE_PATH
    assert _ok(ct32_artifact_path(tmp_path)) == path
    raw = path.read_bytes()
    identity = artifact.fp1_identity()
    assert raw == _ok(canonical_bytes(identity))
    assert stamped == _ok(artifact.fingerprint())
    assert stamped == _ok(fingerprint(identity))
    assert stamped.value.startswith("fp1:sha256:")
    assert stamped.digest == _ok(fingerprint(json.loads(raw.decode("utf-8")))).digest
    parsed = json.loads(raw.decode("utf-8"))
    assert "chart" not in parsed
    assert "html" not in parsed
    assert _walk_has_no_float(parsed)


def test_full_ad12_label_and_ar59_stamps(tmp_path: Path) -> None:
    registry_as_of = _instant(_NS + 9)
    data_fp = _ok(fingerprint({"class": "data-window", "n": "recorded-eurusd"}))
    split_fp = _ok(fingerprint({"class": "split-manifest", "n": "holdout-a"}))
    fidelity = _ok(stamp_fidelity("fill.declared-path", composition_version=COMPOSITION_VERSION))
    rng = {"family": "qmx-pcg64", "algorithm_version": "v1", "base_seed": 7}
    config = _config(
        registry_as_of=registry_as_of,
        data_fingerprint=data_fp,
        split_fingerprint=split_fp,
        fidelity=fidelity,
        rng_provenance=rng,
        account_role=AccountRole.DEMO,
    )
    outcome = _run(config=config)
    artifact = outcome.performance_result
    assert isinstance(artifact, PerformanceResult)
    label = artifact.result_label
    assert label.producer_contract_identity == _ok(fingerprint(result_identity()))
    assert label.producer_contract_format_version == 1
    assert label.evidence_class is EvidenceClass.PROVISIONAL
    assert label.world is World.REPLAY
    assert label.world is config.world
    assert label.evidence_time_range == outcome.evidence_range
    assert label.computation_identity == _ok(fingerprint(label.fp1_identity()))
    assert artifact.account_binding_role is AccountRole.DEMO
    inputs = label.input_fingerprints
    assert inputs[0] == config.fingerprint
    assert config.fingerprint == config.run_id
    registry_fp = _ok(
        fingerprint({"class": "registry-as-of", "registry_as_of": registry_as_of.fp1_identity()})
    )
    fidelity_fp = _ok(fingerprint(fidelity.fp1_identity()))
    rng_fp = _ok(fingerprint({"class": "rng-provenance", **rng}))
    assert registry_fp in inputs
    assert data_fp in inputs
    assert split_fp in inputs
    assert fidelity_fp in inputs
    assert rng_fp in inputs
    assert fidelity.taint == TAINT_OPTIMISTIC
    assert "taint" not in fidelity.fp1_identity()
    stamped = _ok(assemble_run_performance_result(outcome, output_dir=tmp_path))
    assert stamped == _ok(artifact.fingerprint())
    body = json.loads(
        (tmp_path / RESULTS_DIR_NAME / CT32_ARTIFACT_NAME).read_text(encoding="utf-8")
    )
    assert body["result_label"]["world"] == World.REPLAY.value
    assert body["account_binding_role"] == AccountRole.DEMO.value
    assert "score" not in body
    assert "verdict" not in body
    assert result_identity()["claims_edge"] is False


def test_evidence_range_is_trading_interval_never_warmup() -> None:
    config = _config(streams=("eurusd",))
    outcome = _ok(
        run(
            slices=(
                (_obs("eurusd", _NS),),
                (_obs("eurusd", _NS + 1),),
                (_obs("eurusd", _NS + 2),),
            ),
            config=config,
            handler=SilentSliceHandler(),
            embargo=2,
        )
    )
    artifact = outcome.performance_result
    assert isinstance(artifact, PerformanceResult)
    assert outcome.self_assessment["evidence_covers_warmup"] is False
    assert outcome.slices[0].is_warming_up is True
    assert outcome.slices[1].is_warming_up is True
    assert outcome.slices[2].is_warming_up is False
    span = artifact.result_label.evidence_time_range
    assert span.start == outcome.slices[2].frontier
    assert span.start.value_ns == _NS + 2
    assert span.end.value_ns == _NS + 3
    assert span.start.value_ns > outcome.slices[0].frontier.value_ns
    assert span.start.value_ns > outcome.slices[1].frontier.value_ns


def test_multi_role_is_policy_rejection_and_writes_nothing(tmp_path: Path) -> None:
    config = _config(account_role=(AccountRole.DEMO, AccountRole.LIVE))
    refused = run(slices=_slices(), config=config, handler=SilentSliceHandler())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == ACCOUNT_ROLE_KEY
    assembled = assemble_run_performance_result(refused, output_dir=tmp_path)
    assert is_refusal(assembled)
    assert assembled.category is RefusalCategory.POLICY_REJECTION
    assert list(tmp_path.iterdir()) == []
    minted = mint_run_performance_result(
        config,
        evidence_range=_ok(run(slices=_slices(), stream_set=("eurusd", "gbpusd"))).evidence_range,
        stream_order=("eurusd", "gbpusd"),
        slice_count=2,
        filled_count=0,
        resting_count=0,
        data_points_processed=4,
        outcome_identity={"class": "event-slice-loop-outcome"},
    )
    assert is_refusal(minted)
    assert minted.category is RefusalCategory.POLICY_REJECTION
    assert not (tmp_path / RESULTS_DIR_NAME).exists()


def test_world_is_data_derived_and_simulated_is_refused_upstream() -> None:
    replay = _run()
    assert replay.performance_result is not None
    assert replay.performance_result.result_label.world is World.REPLAY
    stamp = _ok(fingerprint({"n": "simulated-cfg"}))
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
    assert simulated.context["field"] == "world"


def test_assembly_refuses_configless_outcome_and_writes_nothing(tmp_path: Path) -> None:
    outcome = _ok(
        run(
            slices=_slices(("eurusd",)),
            stream_set=("eurusd",),
            handler=SilentSliceHandler(),
        )
    )
    assert outcome.performance_result is None
    refused = assemble_run_performance_result(outcome, output_dir=tmp_path)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert list(tmp_path.iterdir()) == []
    assert is_refusal(assemble_run_performance_result(outcome, output_dir=""))
    assert is_refusal(assemble_run_performance_result("not-an-outcome", output_dir=tmp_path))
    missing = assemble_run_performance_result(_run(), output_dir=tmp_path / "absent")
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.STORAGE_FAILURE


def test_exclusive_write_refuses_a_second_artifact(tmp_path: Path) -> None:
    outcome = _run()
    first = _ok(assemble_run_performance_result(outcome, output_dir=tmp_path))
    again = assemble_run_performance_result(outcome, output_dir=tmp_path)
    assert is_refusal(again)
    assert again.category is RefusalCategory.STORAGE_FAILURE
    path = tmp_path / RESULTS_DIR_NAME / CT32_ARTIFACT_NAME
    assert path.is_file()
    assert list((tmp_path / RESULTS_DIR_NAME).iterdir()) == [path]
    assert first == _ok(outcome.ct32_fingerprint())


def test_malformed_optional_stamps_are_typed_refusals() -> None:
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
    assert is_refusal(mint_run_performance_result(_config(data_fingerprint="nope"), **dummy))
    assert is_refusal(mint_run_performance_result(_config(split_fingerprint=1), **dummy))
    assert is_refusal(mint_run_performance_result(_config(fidelity="adapter"), **dummy))
    assert is_refusal(mint_run_performance_result(_config(rng_provenance=1.5), **dummy))
    assert is_refusal(mint_run_performance_result(_config(registry_as_of={"nope": True}), **dummy))
    calibrated = mint_run_performance_result(
        _config(fidelity={"adapter_id": "fill.declared-path", "taint": "calibrated"}),
        **dummy,
    )
    assert is_refusal(calibrated)
    assert calibrated.context["field"] == "taint"


def test_door_exports_the_assembly_surface() -> None:
    assert api.assemble_run_performance_result is qmb.assemble_run_performance_result
    assert api.ct32_artifact_path is qmb.ct32_artifact_path
    assert api.CT32_ARTIFACT_NAME == CT32_ARTIFACT_NAME
    assert api.RESULTS_DIR_NAME == RESULTS_DIR_NAME
    assert api.REGISTRY_AS_OF_KEY == REGISTRY_AS_OF_KEY
    assert api.DATA_FINGERPRINT_KEY == DATA_FINGERPRINT_KEY
    assert api.SPLIT_FINGERPRINT_KEY == SPLIT_FINGERPRINT_KEY
    assert api.FIDELITY_KEY == FIDELITY_KEY
    assert api.RNG_PROVENANCE_KEY == RNG_PROVENANCE_KEY
    assert api.mint_run_performance_result is qmb.mint_run_performance_result


def _walk_has_no_float(value: object) -> bool:
    if isinstance(value, float):
        return False
    if isinstance(value, dict):
        mapping = cast("dict[object, object]", value)
        return all(_walk_has_no_float(item) for item in mapping.values())
    if isinstance(value, list):
        items = cast("list[object]", value)
        return all(_walk_has_no_float(item) for item in items)
    return True
