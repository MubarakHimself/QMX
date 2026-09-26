"""Reference usage — Story 7.4: streaming mode, the tier-2 equality law, and
restore-equivalence (COMP-QMF-INDICATORS; CT-16; DEC-0126, DEC-0113, DEC-0103).

Executable::

    python packages/qmf-indicators/examples/streaming_mode_usage.py

Shows the four things Story 7.4 pins down, over a single SMA configuration computed with
the canonical TA-Lib reference:

1. A :class:`StreamingIndicator` is the one named stateful class — one feeder (one
   WriterId holder), unlimited readers — that exposes ``health()`` and tags every output
   with the input sequence number that produced it.
2. Streaming numbers equal batch by construction: feeding one observation at a time and
   comparing the accumulated result to a whole-series batch passes the tier-2 equality law
   under the default integer-ULP comparator (0).
3. Restore-equivalence: warming, snapshotting, restoring, and advancing by N updates
   yields exactly the values a cold-warm-then-the-same-N path produces; a result from
   restored state carries the snapshot fingerprint as an input fingerprint.
4. A snapshot restored on a different (OS, arithmetic-reference build) tuple is refused
   with an ``unavailable dependency`` refusal (FM-7).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    ExactRational,
    Instant,
    Instrument,
    Result,
    UnitKind,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    AlignmentPolicy,
    ArithmeticReference,
    ChannelKind,
    ConfiguredIndicator,
    InputSeries,
    MissingValuePolicy,
    OutputArity,
    OutputChannel,
    PresenceState,
    QuoteSide,
    ReferenceKernel,
    SeriesInput,
    SnapshotScope,
    StreamingIndicator,
    StreamingObservation,
    SupportedMode,
    assert_mode_equality,
    compute_batch,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


def main() -> None:
    venue = _unwrap(VenueId.try_create("venue-ic"))
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"))
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
    period = _unwrap(ExactRational.try_create(3, 1, UnitKind.COUNT))
    close = _unwrap(
        SeriesInput.try_create(
            name="close",
            source=instrument,
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        )
    )
    sma_channel = _unwrap(
        OutputChannel.try_create(
            "sma", ChannelKind.FLOAT_ANALYTIC, OutputArity.SCALAR_PER_SAMPLE, 0
        )
    )
    reference = _unwrap(
        ArithmeticReference.try_create(
            "ta-lib-c==0.7.1",
            "ta-lib==0.7.1",
            {"compatibility_mode": "default", "candle_settings": "reference-default"},
        )
    )
    configuration = _unwrap(
        ConfiguredIndicator.try_create(
            formula_id="sma",
            contract_format_version=1,
            parameters={"period": period},
            inputs=[close],
            calendar_requirements=[calendar],
            alignment_policy=AlignmentPolicy.AS_OF,
            missing_value_policy=MissingValuePolicy.MARK_GAP,
            warm_up=2,
            output_schema=[sma_channel],
            supported_modes=[SupportedMode.BATCH, SupportedMode.STREAMING],
            arithmetic_reference_configuration=reference,
        )
    )

    values = [30000, 31000, 32000, 33000, 34000, 35000]
    instants = [_unwrap(Instant.try_create(1_000 + step)) for step in range(len(values))]

    # 1. The one named stateful class: one feeder (a WriterId holder), health(), and every
    #    output carries the input sequence number that produced it.
    feeder = _unwrap(WriterId.try_create("m1", "indicator-feeder", "eurusd-sma-3", "boot-1"))
    scope = _unwrap(SnapshotScope.try_create("windows-11", "ta-lib==0.7.1"))
    stream = _unwrap(
        StreamingIndicator.try_create(
            configuration,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=feeder,
            scope=scope,
            input_scales={"close": 2},
        )
    )
    for value, instant in zip(values, instants, strict=True):
        sample = _unwrap(
            stream.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
        channel = sample.channels["sma"]
        print(f"update seq={sample.sequence}: {channel.presence.value} value={channel.value}")
    print(f"health: ready={stream.health().ready} seen={stream.health().observations_seen}")

    # 2. The tier-2 equality law: streaming equals batch by construction (comparator 0).
    series = _unwrap(
        InputSeries.from_values(values, 2, [PresenceState.PRESENT] * len(values), instants)
    )
    batch_result = _unwrap(
        compute_batch(
            configuration, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY
        )
    )
    streaming_result = _unwrap(stream.result())
    equal = _unwrap(assert_mode_equality(configuration, batch_result, streaming_result))
    print(f"tier-2 equality law (streaming == batch, 0 ULP): {equal}")

    # 3. Restore-equivalence: warm three, snapshot, restore, advance three.
    warm = _unwrap(
        StreamingIndicator.try_create(
            configuration,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=feeder,
            scope=scope,
            input_scales={"close": 2},
        )
    )
    for value, instant in zip(values[:3], instants[:3], strict=True):
        _unwrap(warm.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)}))
    snapshot = _unwrap(warm.snapshot())
    restored = _unwrap(
        StreamingIndicator.restore(
            snapshot,
            configuration=configuration,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            current_scope=scope,
        )
    )
    for value, instant in zip(values[3:], instants[3:], strict=True):
        _unwrap(
            restored.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
    restored_result = _unwrap(restored.result())
    equivalent = _unwrap(streaming_result.outputs["sma"].equals(restored_result.outputs["sma"]))
    snapshot_fp = _unwrap(snapshot.fingerprint())
    carries = snapshot_fp in restored_result.label.input_fingerprints
    print(f"restore-equivalence (values equal): {equivalent}")
    print(f"restored result carries snapshot fingerprint as input: {carries}")

    # 4. A cross-tuple restore is an unavailable-dependency refusal (FM-7).
    other_scope = _unwrap(SnapshotScope.try_create("ubuntu-24.04", "ta-lib==0.7.1"))
    cross = StreamingIndicator.restore(
        snapshot,
        configuration=configuration,
        kernel=ReferenceKernel(),
        world=World.REPLAY,
        current_scope=other_scope,
    )
    assert is_refusal(cross), cross
    print(f"cross-tuple restore: {cross.category.value}")


if __name__ == "__main__":
    main()
