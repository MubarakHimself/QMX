"""Tier-1 tests for CT-16 streaming mode, the tier-2 equality law, and restore-equivalence
(COMP-QMF-INDICATORS; Story 7.4).

These tests bind the story's acceptance criteria:

* **The one named stateful class** — a streaming instance is created from a
  streaming-declaring configuration; it holds exactly one feeder (one ``WriterId``
  holder) and serves unlimited readers, exposes ``health()``, tags every output with the
  input sequence number that produced it, and instance count scales with distinct
  configurations, not consumers.
* **The tier-2 equality law** — for a both-modes configuration, streaming and batch
  results are equal same-process/same-build under a per-configuration integer-ULP
  comparator (default 0) over canonical inputs = (series, exact parameters, cold initial
  state), with the seeding rule and leading-undefined-prefix-to-not-ready mapping
  declared; cross-OS / cross-build agreement is never this gate.
* **Restore-equivalence** — restore-then-N-updates equals cold-warm-then-the-same-N
  updates; the snapshot is a serialized contract with its own format version scoped to a
  declared (OS, arithmetic-reference build) tuple; a result from restored state carries
  the snapshot fingerprint as an input fingerprint.
* **Cross-tuple restore** — restoring on a different (OS, arithmetic-reference build)
  tuple is an ``unavailable dependency`` refusal (FM-7).

Most tests drive a pure in-test kernel so presence, warm-up, sequencing, and restore are
asserted deterministically; a final group drives the real :class:`ReferenceKernel` so the
canonical TA-Lib equality law is exercised end to end on this machine.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

import pytest
from qmf.core import (
    CalendarIdentity,
    ExactRational,
    Instant,
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    UnitKind,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    CROSS_TUPLE_IS_A_REGISTERED_ARTIFACT,
    DEFAULT_MODE_EQUALITY_ULPS,
    LEADING_UNDEFINED_MAPPING,
    SEEDING_RULE,
    SNAPSHOT_FORMAT_VERSION,
    AlignmentPolicy,
    ArithmeticReference,
    BatchResult,
    ChannelKind,
    ConfiguredIndicator,
    IndicatorSeries,
    InputSeries,
    KernelOutput,
    MissingValuePolicy,
    ModeEqualityComparator,
    OutputArity,
    OutputChannel,
    PresenceState,
    QuoteSide,
    ReferenceKernel,
    SeriesInput,
    SnapshotScope,
    StreamingIndicator,
    StreamingObservation,
    StreamingSnapshot,
    SupportedMode,
    assert_mode_equality,
    compute_batch,
    reference_status,
    series_equal_within_ulps,
)
from qmf.indicators.series import encode_int64_values

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


# --- fixtures ---------------------------------------------------------------


def _instrument() -> Instrument:
    return _unwrap(Instrument.try_create(_unwrap(VenueId.try_create("venue-ic")), "EURUSD"))


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _period(numerator: int = 2, denominator: int = 1) -> ExactRational:
    return _unwrap(ExactRational.try_create(numerator, denominator, UnitKind.COUNT))


def _series_input(name: str = "close") -> SeriesInput:
    return _unwrap(
        SeriesInput.try_create(
            name=name,
            source=_instrument(),
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        )
    )


def _output_channel(name: str = "sma") -> OutputChannel:
    return _unwrap(
        OutputChannel.try_create(name, ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0)
    )


def _arithmetic_reference() -> ArithmeticReference:
    return _unwrap(
        ArithmeticReference.try_create(
            "ta-lib-c==0.7.1",
            "ta-lib==0.7.1",
            {"compatibility_mode": "default", "candle_settings": "reference-default"},
        )
    )


def _config(**overrides: object) -> ConfiguredIndicator:
    kwargs: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "parameters": {"period": _period(2)},
        "inputs": [_series_input("close")],
        "calendar_requirements": [_calendar()],
        "alignment_policy": AlignmentPolicy.AS_OF,
        "missing_value_policy": MissingValuePolicy.MARK_GAP,
        "warm_up": 1,
        "output_schema": [_output_channel("sma")],
        "supported_modes": [SupportedMode.BATCH, SupportedMode.STREAMING],
        "arithmetic_reference_configuration": _arithmetic_reference(),
    }
    kwargs.update(overrides)
    return _unwrap(ConfiguredIndicator.try_create(**kwargs))


def _writer(stream: str = "eurusd-sma") -> WriterId:
    return _unwrap(WriterId.try_create("m1", "indicator-feeder", stream, "boot-1"))


def _scope() -> SnapshotScope:
    return _unwrap(SnapshotScope.try_create("windows-11", "ta-lib==0.7.1"))


def _obs(value: int, presence: PresenceState, ns: int) -> StreamingObservation:
    return _unwrap(
        StreamingObservation.try_create(value, presence, _unwrap(Instant.try_create(ns)))
    )


# --- an in-test kernel ------------------------------------------------------


class _EchoKernel:
    """A pure causal kernel: it echoes the primary dense input as the single output channel.

    ``lookback`` leading dense positions are undefined (``None``); the rest echo the input
    value. Because the value at each position depends only on that position, the streaming
    incremental path (recompute over the accumulated prefix and emit the newest) equals the
    batch path over the whole series position for position.
    """

    def __init__(self, *, lookback: int = 0, scale: int = 2) -> None:
        self._lookback = lookback
        self._scale = scale

    def compute(
        self,
        dense_inputs: Mapping[str, tuple[int, ...]],
        input_scales: Mapping[str, int],
        configuration: ConfiguredIndicator,
    ) -> Result[KernelOutput]:
        primary = configuration.inputs[0].name
        dense = dense_inputs[primary]
        channel = configuration.output_schema[0].name
        prefix = min(self._lookback, len(dense))
        values: list[int | None] = [None] * prefix + list(dense[prefix:])
        return Ok(
            KernelOutput(
                channels={channel: tuple(values)}, lookback=self._lookback, scale=self._scale
            )
        )


def _cold_instance(config: ConfiguredIndicator | None = None) -> StreamingIndicator:
    configuration = config if config is not None else _config()
    return _unwrap(
        StreamingIndicator.try_create(
            configuration,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )


# --- AC1: the one named stateful class --------------------------------------


def test_streaming_output_carries_the_input_sequence_number() -> None:
    stream = _cold_instance(_config(warm_up=0))
    seqs: list[int] = []
    for step in range(3):
        sample = _unwrap(
            stream.update({"close": _obs(10 + step, PresenceState.PRESENT, 1_000 + step)})
        )
        seqs.append(sample.sequence)
    # Every streaming output carries the input sequence number that produced it: a
    # per-feeder strictly-increasing counter from the held WriterId's sequencer.
    assert seqs == [0, 1, 2]
    assert stream.health().next_sequence == 3


def test_exactly_one_feeder_a_second_writer_is_refused() -> None:
    stream = _cold_instance(_config(warm_up=0))
    held = _writer()
    # The held feeder is accepted.
    assert is_ok(stream.update({"close": _obs(10, PresenceState.PRESENT, 1_000)}, feeder=held))
    # A second, different feeder (different WriterId) is refused — one WriterId holder.
    other = _unwrap(WriterId.try_create("m2", "indicator-feeder", "eurusd-sma", "boot-9"))
    refusal = stream.update({"close": _obs(20, PresenceState.PRESENT, 1_001)}, feeder=other)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refusal.context["field"] == "feeder"
    # A non-WriterId feeder is invalid input.
    assert is_refusal(
        stream.update({"close": _obs(20, PresenceState.PRESENT, 1_002)}, feeder=object())
    )


def test_health_reports_identity_counts_and_readiness() -> None:
    stream = _cold_instance(_config(warm_up=1))
    # Before any update: not ready, no observations.
    health = stream.health()
    assert health.observations_seen == 0
    assert health.ready is False
    assert health.restored_from is None
    assert health.os == "windows-11"
    assert health.arithmetic_reference_build == "ta-lib==0.7.1"
    assert health.machine == "m1" and health.stream == "eurusd-sma"
    # Feed past warm-up: ready flips to True.
    _unwrap(stream.update({"close": _obs(10, PresenceState.PRESENT, 1_000)}))  # warm-up: not_ready
    _unwrap(stream.update({"close": _obs(20, PresenceState.PRESENT, 1_001)}))  # present
    assert stream.health().ready is True
    assert stream.health().observations_seen == 2


def test_instance_count_scales_with_configurations_not_consumers() -> None:
    # An instance carries its configuration fingerprint; two configs differing in one
    # element get different instances, and readers mint none.
    config_a = _config()
    config_b = _config(warm_up=5)  # a different declared configuration
    stream_a = _cold_instance(config_a)
    stream_b = _cold_instance(config_b)
    assert stream_a.configuration_fingerprint() == _unwrap(config_a.fp1())
    assert stream_a.configuration_fingerprint() != stream_b.configuration_fingerprint()
    # Reader calls (unlimited readers) never change the instance's identity or its counts.
    before = stream_a.configuration_fingerprint()
    stream_a.health()
    stream_a.health()
    assert stream_a.configuration_fingerprint() == before
    assert stream_a.observations_seen == 0


def test_latest_and_result_refuse_before_any_update() -> None:
    stream = _cold_instance()
    assert is_refusal(stream.latest())
    result = stream.result()
    assert is_refusal(result) and result.context["field"] == "result"


def test_latest_returns_the_most_recent_sample() -> None:
    stream = _cold_instance(_config(warm_up=0))
    _unwrap(stream.update({"close": _obs(10, PresenceState.PRESENT, 1_000)}))
    second = _unwrap(stream.update({"close": _obs(20, PresenceState.PRESENT, 1_001)}))
    latest = _unwrap(stream.latest())
    assert latest.sequence == second.sequence == 1
    assert latest.position == 1
    assert latest.channels["sma"].value == 20


# --- AC1/AC2: equality law by construction ----------------------------------


def test_streaming_equals_batch_by_construction_pure_kernel() -> None:
    config = _config(warm_up=1)
    values = [10, 20, 30, 40, 50]
    instants = [_unwrap(Instant.try_create(1_000 + step)) for step in range(len(values))]
    # Streaming: feed one at a time.
    stream = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=_EchoKernel(lookback=1),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )
    for value, instant in zip(values, instants, strict=True):
        _unwrap(
            stream.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
    streaming_result = _unwrap(stream.result())
    # Batch: the whole series at once with the identical kernel.
    series = _unwrap(
        InputSeries.from_values(values, 2, [PresenceState.PRESENT] * len(values), instants)
    )
    batch_result = _unwrap(
        compute_batch(config, {"close": series}, kernel=_EchoKernel(lookback=1), world=World.REPLAY)
    )
    # The tier-2 equality law: equal under the default integer-ULP comparator (0).
    assert _unwrap(assert_mode_equality(config, batch_result, streaming_result)) is True
    # And the per-update samples reconstruct the batch series position for position.
    assert _unwrap(batch_result.outputs["sma"].equals(streaming_result.outputs["sma"])) is True


def test_equality_law_binds_only_when_both_modes_declared() -> None:
    streaming_only = _config(supported_modes=[SupportedMode.STREAMING])
    stream = _unwrap(
        StreamingIndicator.try_create(
            streaming_only,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )
    _unwrap(stream.update({"close": _obs(10, PresenceState.PRESENT, 1_000)}))
    streaming_result = _unwrap(stream.result())
    refusal = assert_mode_equality(streaming_only, streaming_result, streaming_result)
    assert is_refusal(refusal)
    assert refusal.context["field"] == "supported_modes"


def test_equality_law_reports_divergence() -> None:
    config = _config(warm_up=0)
    instants = [_unwrap(Instant.try_create(1_000 + step)) for step in range(3)]
    batch_series = _unwrap(
        InputSeries.from_values([10, 20, 30], 2, [PresenceState.PRESENT] * 3, instants)
    )
    batch_result = _unwrap(
        compute_batch(config, {"close": batch_series}, kernel=_EchoKernel(), world=World.REPLAY)
    )
    # A streaming result over different data diverges.
    stream = _cold_instance(config)
    for value, instant in zip([10, 20, 99], instants, strict=True):
        _unwrap(
            stream.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
    diverging = _unwrap(stream.result())
    assert _unwrap(assert_mode_equality(config, batch_result, diverging)) is False


def test_equality_law_channel_set_mismatch_is_false() -> None:
    config = _config(warm_up=0)
    stream = _cold_instance(config)
    _unwrap(stream.update({"close": _obs(10, PresenceState.PRESENT, 1_000)}))
    result = _unwrap(stream.result())
    renamed = BatchResult(outputs={"other": result.outputs["sma"]}, label=result.label)
    assert _unwrap(assert_mode_equality(config, result, renamed)) is False


def test_equality_law_validates_arguments() -> None:
    config = _config()
    assert is_refusal(assert_mode_equality(object(), object(), object()))
    # Both modes declared but non-BatchResult arguments refuse.
    assert is_refusal(assert_mode_equality(config, object(), object()))


def test_the_seeding_and_leading_undefined_rules_are_declared_surface() -> None:
    # The seeding rule and the leading-undefined-prefix-to-not-ready mapping are declared
    # contract surface, and cross-tuple agreement is never the gate.
    assert "cold-initial-state" in SEEDING_RULE
    assert "not_ready" in LEADING_UNDEFINED_MAPPING
    assert CROSS_TUPLE_IS_A_REGISTERED_ARTIFACT is True
    assert DEFAULT_MODE_EQUALITY_ULPS == 0


# --- the integer-ULP comparator ---------------------------------------------


def test_comparator_tolerates_within_ulps_and_rejects_beyond() -> None:
    knowable = [_unwrap(Instant.try_create(1_000 + step)) for step in range(2)]
    presence = [PresenceState.PRESENT, PresenceState.PRESENT]
    left = _unwrap(
        IndicatorSeries.try_create(_unwrap(encode_int64_values([100, 200])), 2, presence, knowable)
    )
    # One scaled-integer unit larger at position 1.
    right = _unwrap(
        IndicatorSeries.try_create(_unwrap(encode_int64_values([100, 201])), 2, presence, knowable)
    )
    assert _unwrap(series_equal_within_ulps(left, right, 0)) is False
    assert _unwrap(series_equal_within_ulps(left, right, 1)) is True
    # A differing presence map is unequal regardless of tolerance.
    other_presence = [PresenceState.NOT_READY, PresenceState.PRESENT]
    diff_presence = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values([100, 201])), 2, other_presence, knowable
        )
    )
    assert _unwrap(series_equal_within_ulps(left, diff_presence, 5)) is False


def test_comparator_compares_exactly_across_scales() -> None:
    knowable = [_unwrap(Instant.try_create(1_000))]
    fine = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values([4_500_000])), 6, [PresenceState.PRESENT], knowable
        )
    )
    coarse = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values([450])), 2, [PresenceState.PRESENT], knowable
        )
    )
    assert _unwrap(series_equal_within_ulps(fine, coarse, 0)) is True


def test_comparator_and_series_equal_validate_arguments() -> None:
    assert is_refusal(series_equal_within_ulps(object(), object()))
    knowable = [_unwrap(Instant.try_create(1_000))]
    series = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values([1])), 0, [PresenceState.PRESENT], knowable
        )
    )
    assert is_refusal(series_equal_within_ulps(series, series, -1))
    assert is_refusal(ModeEqualityComparator.try_create(-1))
    assert is_refusal(ModeEqualityComparator.try_create(1.5))
    assert _unwrap(ModeEqualityComparator.try_create()).ulps == 0
    assert _unwrap(ModeEqualityComparator.try_create(3)).ulps == 3


# --- AC3: restore-equivalence -----------------------------------------------


def _feed(stream: StreamingIndicator, values: list[int], instants: list[Instant]) -> None:
    for value, instant in zip(values, instants, strict=True):
        _unwrap(
            stream.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )


def test_restore_then_n_updates_equals_cold_warm_then_the_same_n() -> None:
    config = _config(warm_up=1)
    values = [10, 20, 30, 40, 50, 60]
    instants = [_unwrap(Instant.try_create(1_000 + step)) for step in range(len(values))]

    # Cold-warm the whole series.
    cold = _cold_instance(config)
    _feed(cold, values, instants)
    cold_result = _unwrap(cold.result())

    # Warm the first three, snapshot, restore, feed the last three.
    warm = _cold_instance(config)
    _feed(warm, values[:3], instants[:3])
    snapshot = _unwrap(warm.snapshot())
    restored = _unwrap(
        StreamingIndicator.restore(
            snapshot,
            configuration=config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    _feed(restored, values[3:], instants[3:])
    restored_result = _unwrap(restored.result())

    # Restore-equivalence: the output values equal the cold-warm path exactly.
    assert _unwrap(cold_result.outputs["sma"].equals(restored_result.outputs["sma"])) is True
    # Sequence numbering continues across the snapshot (no restart to zero).
    assert _unwrap(restored.latest()).sequence == 5


def test_result_from_restored_state_carries_the_snapshot_fingerprint() -> None:
    config = _config(warm_up=0)
    instants = [_unwrap(Instant.try_create(1_000 + step)) for step in range(4)]
    warm = _cold_instance(config)
    _feed(warm, [10, 20], instants[:2])
    snapshot = _unwrap(warm.snapshot())
    snapshot_fp = _unwrap(snapshot.fingerprint())
    restored = _unwrap(
        StreamingIndicator.restore(
            snapshot,
            configuration=config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    _feed(restored, [30, 40], instants[2:])
    restored_result = _unwrap(restored.result())
    assert snapshot_fp in restored_result.label.input_fingerprints
    # A cold instance's result never carries a snapshot fingerprint.
    cold_result = _unwrap(warm.result())
    assert snapshot_fp not in cold_result.label.input_fingerprints
    assert warm.health().restored_from is None
    assert restored.health().restored_from == snapshot_fp.value


def test_snapshot_is_a_serialized_contract_with_its_own_format_version_and_scope() -> None:
    config = _config(warm_up=0)
    warm = _cold_instance(config)
    _feed(warm, [10, 20, 30], [_unwrap(Instant.try_create(1_000 + s)) for s in range(3)])
    snapshot = _unwrap(warm.snapshot())
    assert snapshot.format_version == SNAPSHOT_FORMAT_VERSION
    assert snapshot.scope == _scope()
    assert snapshot.next_sequence == 3
    # The serialized form round-trips exactly (a genuine serialized contract).
    mapping = snapshot.to_mapping()
    assert mapping["format_version"] == SNAPSHOT_FORMAT_VERSION
    restored_snapshot = _unwrap(StreamingSnapshot.from_mapping(mapping))
    assert _unwrap(restored_snapshot.fingerprint()) == _unwrap(snapshot.fingerprint())
    # A restore off the round-tripped snapshot advances identically to the original.
    restored = _unwrap(
        StreamingIndicator.restore(
            restored_snapshot,
            configuration=config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    assert restored.observations_seen == 3
    assert restored.health().next_sequence == 3


# --- AC4: cross-tuple restore refusal (FM-7) --------------------------------


def test_cross_tuple_restore_is_unavailable_dependency() -> None:
    config = _config(warm_up=0)
    warm = _cold_instance(config)
    _feed(warm, [10, 20], [_unwrap(Instant.try_create(1_000 + s)) for s in range(2)])
    snapshot = _unwrap(warm.snapshot())
    other_os = _unwrap(SnapshotScope.try_create("ubuntu-24.04", "ta-lib==0.7.1"))
    refusal = StreamingIndicator.restore(
        snapshot,
        configuration=config,
        kernel=_EchoKernel(),
        world=World.REPLAY,
        current_scope=other_os,
    )
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["field"] == "scope"
    # A different arithmetic-reference build is equally refused.
    other_build = _unwrap(SnapshotScope.try_create("windows-11", "ta-lib==0.8.0"))
    refusal_build = StreamingIndicator.restore(
        snapshot,
        configuration=config,
        kernel=_EchoKernel(),
        world=World.REPLAY,
        current_scope=other_build,
    )
    assert is_refusal(refusal_build)
    assert refusal_build.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# --- validation paths -------------------------------------------------------


def test_try_create_validates_wiring() -> None:
    config = _config()
    # Non-configuration.
    assert is_refusal(
        StreamingIndicator.try_create(
            object(),
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )
    # Configuration without streaming mode.
    batch_only = _config(supported_modes=[SupportedMode.BATCH])
    no_stream = StreamingIndicator.try_create(
        batch_only,
        kernel=_EchoKernel(),
        world=World.REPLAY,
        writer_id=_writer(),
        scope=_scope(),
        input_scales={"close": 2},
    )
    assert is_refusal(no_stream) and no_stream.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    # Bad kernel, world, writer, scope, and input scales each refuse.
    assert is_refusal(
        StreamingIndicator.try_create(
            config,
            kernel=object(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )
    assert is_refusal(
        StreamingIndicator.try_create(
            config,
            kernel=_EchoKernel(),
            world="mars",
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )
    assert is_refusal(
        StreamingIndicator.try_create(
            config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=object(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )
    assert is_refusal(
        StreamingIndicator.try_create(
            config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=object(),
            input_scales={"close": 2},
        )
    )
    missing_scale = StreamingIndicator.try_create(
        config,
        kernel=_EchoKernel(),
        world=World.REPLAY,
        writer_id=_writer(),
        scope=_scope(),
        input_scales={},
    )
    assert is_refusal(missing_scale) and missing_scale.context["field"] == "input_scales"
    assert is_refusal(
        StreamingIndicator.try_create(
            config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales=object(),
        )
    )


def test_world_accepts_string_and_scope_from_streaming_world() -> None:
    config = _config(warm_up=0)
    stream = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=_EchoKernel(),
            world="live",
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 2},
        )
    )
    sample = _unwrap(stream.update({"close": _obs(10, PresenceState.PRESENT, 1_000)}))
    assert sample.sequence == 0


def test_update_validates_observations() -> None:
    stream = _cold_instance(_config(warm_up=0))
    # Non-mapping observations.
    assert is_refusal(stream.update(object()))
    # Missing the declared input.
    missing = stream.update({"other": _obs(10, PresenceState.PRESENT, 1_000)})
    assert is_refusal(missing) and missing.context["field"] == "observations"


def test_streaming_observation_validation() -> None:
    good_instant = _unwrap(Instant.try_create(1_000))
    assert is_refusal(StreamingObservation.try_create(1.5, PresenceState.PRESENT, good_instant))
    assert is_refusal(StreamingObservation.try_create(True, PresenceState.PRESENT, good_instant))
    assert is_refusal(StreamingObservation.try_create(10, "nope", good_instant))
    assert is_refusal(StreamingObservation.try_create(10, PresenceState.PRESENT, 123))
    # A presence-state string is coerced.
    assert is_ok(StreamingObservation.try_create(10, "present", good_instant))


def test_snapshot_scope_validation() -> None:
    assert is_refusal(SnapshotScope.try_create("", "ta-lib==0.7.1"))
    assert is_refusal(SnapshotScope.try_create("windows-11", "  "))
    assert is_ok(SnapshotScope.try_create("windows-11", "ta-lib==0.7.1"))


def test_refused_update_rolls_back_the_accumulation() -> None:
    # A REFUSE missing-value policy makes a gap observation refuse the recompute; the
    # single-feeder path rolls the position back so the accumulation is unchanged.
    config = _config(warm_up=0, missing_value_policy=MissingValuePolicy.REFUSE)
    stream = _cold_instance(config)
    _unwrap(stream.update({"close": _obs(10, PresenceState.PRESENT, 1_000)}))
    assert stream.observations_seen == 1
    refusal = stream.update({"close": _obs(0, PresenceState.GAP, 1_001)})
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    # Rolled back: still one observation, and the next valid update still works.
    assert stream.observations_seen == 1
    good = _unwrap(stream.update({"close": _obs(20, PresenceState.PRESENT, 1_002)}))
    assert good.position == 1
    assert stream.observations_seen == 2


def test_restore_validates_arguments() -> None:
    config = _config(warm_up=0)
    warm = _cold_instance(config)
    _feed(warm, [10, 20], [_unwrap(Instant.try_create(1_000 + s)) for s in range(2)])
    snapshot = _unwrap(warm.snapshot())
    # Non-snapshot / non-scope.
    assert is_refusal(
        StreamingIndicator.restore(
            object(),
            configuration=config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    assert is_refusal(
        StreamingIndicator.restore(
            snapshot,
            configuration=config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            current_scope=object(),
        )
    )
    # Wrong configuration (fingerprint mismatch).
    wrong = _config(warm_up=9)
    mismatch = StreamingIndicator.restore(
        snapshot,
        configuration=wrong,
        kernel=_EchoKernel(),
        world=World.REPLAY,
        current_scope=_scope(),
    )
    assert is_refusal(mismatch) and mismatch.context["field"] == "configuration"
    # Non-configuration, a batch-only configuration, a bad kernel, and a bad world.
    assert is_refusal(
        StreamingIndicator.restore(
            snapshot,
            configuration=object(),
            kernel=_EchoKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    batch_only = _config(supported_modes=[SupportedMode.BATCH])
    assert is_refusal(
        StreamingIndicator.restore(
            snapshot,
            configuration=batch_only,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    assert is_refusal(
        StreamingIndicator.restore(
            snapshot,
            configuration=config,
            kernel=object(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    assert is_refusal(
        StreamingIndicator.restore(
            snapshot,
            configuration=config,
            kernel=_EchoKernel(),
            world="mars",
            current_scope=_scope(),
        )
    )


def test_snapshot_from_mapping_validation() -> None:
    config = _config(warm_up=0)
    warm = _cold_instance(config)
    _feed(warm, [10, 20], [_unwrap(Instant.try_create(1_000 + s)) for s in range(2)])
    good = _unwrap(warm.snapshot()).to_mapping()
    # Non-mapping.
    assert is_refusal(StreamingSnapshot.from_mapping(object()))
    # Bad format version.
    bad_version = dict(good)
    bad_version["format_version"] = 999
    assert is_refusal(StreamingSnapshot.from_mapping(bad_version))
    # Bad scope.
    bad_scope = dict(good)
    bad_scope["scope"] = object()
    assert is_refusal(StreamingSnapshot.from_mapping(bad_scope))
    bad_scope_content = dict(good)
    bad_scope_content["scope"] = {"os": "", "arithmetic_reference_build": "x"}
    assert is_refusal(StreamingSnapshot.from_mapping(bad_scope_content))
    # Bad configuration fingerprint.
    bad_fp = dict(good)
    bad_fp["configuration_fingerprint"] = "not-a-fingerprint"
    assert is_refusal(StreamingSnapshot.from_mapping(bad_fp))
    # Bad writer id.
    bad_writer = dict(good)
    bad_writer["writer_id"] = {"machine": ""}
    assert is_refusal(StreamingSnapshot.from_mapping(bad_writer))
    bad_writer_type = dict(good)
    bad_writer_type["writer_id"] = object()
    assert is_refusal(StreamingSnapshot.from_mapping(bad_writer_type))
    # Bad sequence.
    bad_seq = dict(good)
    bad_seq["next_sequence"] = -1
    assert is_refusal(StreamingSnapshot.from_mapping(bad_seq))
    # Bad columns container.
    bad_cols = dict(good)
    bad_cols["columns"] = object()
    assert is_refusal(StreamingSnapshot.from_mapping(bad_cols))


def test_snapshot_from_mapping_column_validation() -> None:
    config = _config(warm_up=0)
    warm = _cold_instance(config)
    _feed(warm, [10, 20], [_unwrap(Instant.try_create(1_000 + s)) for s in range(2)])
    good = _unwrap(warm.snapshot()).to_mapping()

    def _base_column() -> dict[str, object]:
        # A fresh, valid serialized column: two present int64 values at scale 2.
        return {
            "values_hex": _unwrap(encode_int64_values([10, 20])).hex(),
            "scale": 2,
            "presence": [0, 0],
            "knowable_at_ns": [1_000, 1_001],
        }

    def _with_column(column: object) -> dict[str, object]:
        variant = dict(good)
        variant["columns"] = {"close": column}
        return variant

    # Non-mapping column.
    assert is_refusal(StreamingSnapshot.from_mapping(_with_column(object())))
    # Non-string column name.
    bad_name = dict(good)
    non_string_keyed: dict[object, object] = {1: _base_column()}
    bad_name["columns"] = non_string_keyed
    assert is_refusal(StreamingSnapshot.from_mapping(bad_name))
    # Non-hex values.
    non_hex = _base_column()
    non_hex["values_hex"] = "zz"
    assert is_refusal(StreamingSnapshot.from_mapping(_with_column(non_hex)))
    # values_hex not a string.
    non_str = _base_column()
    non_str["values_hex"] = 123
    assert is_refusal(StreamingSnapshot.from_mapping(_with_column(non_str)))
    # Presence not a sequence.
    bad_presence = _base_column()
    bad_presence["presence"] = "present"
    assert is_refusal(StreamingSnapshot.from_mapping(_with_column(bad_presence)))
    # Unknown presence code.
    unknown_presence = _base_column()
    unknown_presence["presence"] = [99, 0]
    assert is_refusal(StreamingSnapshot.from_mapping(_with_column(unknown_presence)))
    # knowable-at not a sequence.
    bad_knowable = _base_column()
    bad_knowable["knowable_at_ns"] = 123
    assert is_refusal(StreamingSnapshot.from_mapping(_with_column(bad_knowable)))
    # Bad knowable-at nanosecond value.
    bad_ns = _base_column()
    bad_ns["knowable_at_ns"] = ["x", 1]
    assert is_refusal(StreamingSnapshot.from_mapping(_with_column(bad_ns)))
    # Bad scale (via InputSeries.try_create).
    bad_scale = _base_column()
    bad_scale["scale"] = -1
    assert is_refusal(StreamingSnapshot.from_mapping(_with_column(bad_scale)))
    # A fully valid single-column snapshot rebuilds.
    assert is_ok(StreamingSnapshot.from_mapping(_with_column(_base_column())))


# --- multi-input streaming --------------------------------------------------


def test_multi_input_streaming_updates_and_snapshot() -> None:
    config = _config(inputs=[_series_input("high"), _series_input("low")], warm_up=0)
    stream = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"high": 2, "low": 2},
        )
    )
    sample = _unwrap(
        stream.update(
            {
                "high": _obs(30, PresenceState.PRESENT, 1_005),
                "low": _obs(10, PresenceState.PRESENT, 1_000),
            }
        )
    )
    # The position's knowable-at (and the sequencer's minted instant) is the max across
    # inputs; the sample still carries sequence 0.
    assert sample.sequence == 0
    assert sample.channels["sma"].knowable_at.value_ns == 1_005
    # A snapshot captures both columns and restores identically.
    snapshot = _unwrap(stream.snapshot())
    restored = _unwrap(
        StreamingIndicator.restore(
            snapshot,
            configuration=config,
            kernel=_EchoKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    assert restored.observations_seen == 1


# --- the real reference kernel (canonical TA-Lib equality) ------------------


def _require_reference() -> None:
    if not is_ok(reference_status()):
        pytest.skip("the pinned canonical reference is unavailable on this machine")


def test_streaming_equals_batch_under_the_canonical_reference() -> None:
    _require_reference()
    config = _config(parameters={"period": _period(3)}, warm_up=2)
    values = [3, 6, 9, 12, 15, 18, 21]
    instants = [_unwrap(Instant.try_create(1_000 + step)) for step in range(len(values))]
    stream = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 0},
        )
    )
    for value, instant in zip(values, instants, strict=True):
        _unwrap(
            stream.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
    streaming_result = _unwrap(stream.result())
    series = _unwrap(
        InputSeries.from_values(values, 0, [PresenceState.PRESENT] * len(values), instants)
    )
    batch_result = _unwrap(
        compute_batch(config, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    )
    # Integer-ULP comparator default 0: exact equality between streaming and batch.
    assert _unwrap(assert_mode_equality(config, batch_result, streaming_result)) is True


def test_reference_restore_equivalence() -> None:
    _require_reference()
    config = _config(parameters={"period": _period(3)}, warm_up=2)
    values = [3, 6, 9, 12, 15, 18]
    instants = [_unwrap(Instant.try_create(1_000 + step)) for step in range(len(values))]

    cold = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 0},
        )
    )
    for value, instant in zip(values, instants, strict=True):
        _unwrap(cold.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)}))
    cold_result = _unwrap(cold.result())

    warm = _unwrap(
        StreamingIndicator.try_create(
            config,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=_writer(),
            scope=_scope(),
            input_scales={"close": 0},
        )
    )
    for value, instant in zip(values[:3], instants[:3], strict=True):
        _unwrap(warm.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)}))
    snapshot = _unwrap(warm.snapshot())
    restored = _unwrap(
        StreamingIndicator.restore(
            snapshot,
            configuration=config,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            current_scope=_scope(),
        )
    )
    for value, instant in zip(values[3:], instants[3:], strict=True):
        _unwrap(
            restored.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
    restored_result = _unwrap(restored.result())
    assert _unwrap(cold_result.outputs["sma"].equals(restored_result.outputs["sma"])) is True
