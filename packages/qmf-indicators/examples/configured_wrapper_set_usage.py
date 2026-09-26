"""Reference usage — Story 7.6: the first wrapper set of TA-Lib-backed configured
indicators, and the FM-4 arithmetic-upgrade comparison suite (COMP-QMF-INDICATORS; CT-16;
DEC-0127).

Executable::

    python packages/qmf-indicators/examples/configured_wrapper_set_usage.py

Shows the four things Story 7.6 pins down:

1. The first wrapper set is a set of concrete configured indicators, each wrapping a
   TA-Lib formula the reference implements, declared in **both modes**, with **warm-up at
   least the reference's lookback** — the default warm-up is exactly the lookback.
2. No trading-school name appears in the vocabulary: each wrapper's capability term is a
   mechanically stated operation (a mean, a difference, a rate of change).
3. A both-modes wrapper passes the tier-2 equality law: streaming equals batch by
   construction under the integer-ULP comparator (default 0).
4. The FM-4 comparison suite catches an output-changing reference upgrade over identical
   canonical inputs — never a silent accept — and mints the per-configured-indicator
   contract format version with recorded before/after evidence, never a protocol-wide bump.
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
)
from qmf.indicators import (
    WRAPPER_FORMULAS,
    WRAPPER_SET,
    ArithmeticReference,
    BatchResult,
    ChannelKind,
    ConfiguredIndicator,
    IndicatorSeries,
    InputSeries,
    PresenceState,
    QuoteSide,
    ReferenceKernel,
    SeriesInput,
    SnapshotScope,
    StreamingIndicator,
    StreamingObservation,
    SupportedMode,
    assert_mode_equality,
    compare_reference_outputs,
    compute_batch,
    configure_wrapper,
    reference_lookback,
)
from qmf.indicators.series import encode_int64_values

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


def main() -> None:
    venue = _unwrap(VenueId.try_create("venue-ic"))
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"))
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
    close = _unwrap(
        SeriesInput.try_create(
            name="close",
            source=instrument,
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.EXACT_PRICE,
            quote_side=QuoteSide.MID,
        )
    )
    reference = _unwrap(
        ArithmeticReference.try_create(
            "ta-lib-c==0.7.1",
            "ta-lib==0.7.1",
            {"compatibility_mode": "default", "candle_settings": "reference-default"},
        )
    )
    period = _unwrap(ExactRational.try_create(3, 1, UnitKind.COUNT))

    def build(formula_id: str) -> ConfiguredIndicator:
        return _unwrap(
            configure_wrapper(
                formula_id=formula_id,
                period=period,
                inputs=[close],
                calendar_requirements=[calendar],
                arithmetic_reference_configuration=reference,
            )
        )

    # 1 + 2. The first wrapper set: each a both-modes configured indicator with warm-up at
    # the reference lookback, and a mechanically stated capability term (no trading school).
    print(f"wrapper set: {' '.join(WRAPPER_FORMULAS)}")
    for formula_id in WRAPPER_FORMULAS:
        spec = WRAPPER_SET[formula_id]
        config = build(formula_id)
        lookback = _unwrap(reference_lookback(formula_id, period))
        both = {SupportedMode.BATCH, SupportedMode.STREAMING} == set(config.supported_modes)
        print(
            f"  {formula_id}: warm_up={config.warm_up} lookback={lookback} "
            f"both_modes={both} term={spec.capability_term!r}"
        )

    # 3. The tier-2 equality law: streaming equals batch by construction (SMA period 3).
    sma = build("sma")
    values = [3, 6, 9, 12, 15, 18, 21, 24]
    instants = [_unwrap(Instant.try_create(1_000 + step)) for step in range(len(values))]
    series = _unwrap(
        InputSeries.from_values(values, 0, [PresenceState.PRESENT] * len(values), instants)
    )
    batch = _unwrap(
        compute_batch(sma, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    )
    writer = _unwrap(WriterId.try_create("m1", "indicator-feeder", "eurusd-sma", "boot-1"))
    scope = _unwrap(SnapshotScope.try_create("windows-11", "ta-lib==0.7.1"))
    stream = _unwrap(
        StreamingIndicator.try_create(
            sma,
            kernel=ReferenceKernel(),
            world=World.REPLAY,
            writer_id=writer,
            scope=scope,
            input_scales={"close": 0},
        )
    )
    for value, instant in zip(values, instants, strict=True):
        _unwrap(
            stream.update({"close": StreamingObservation(value, PresenceState.PRESENT, instant)})
        )
    streaming = _unwrap(stream.result())
    equal = _unwrap(assert_mode_equality(sma, batch, streaming))
    print(f"equality law (streaming == batch): {equal}")

    # 4. FM-4: an output-changing upgrade over identical canonical inputs is caught and
    # mints the per-configured-indicator version; an unchanged output does not.
    unchanged = _unwrap(compare_reference_outputs(sma, batch, batch))
    print(f"upgrade with no output change: {unchanged.verdict.value} (mint={unchanged.mint})")

    after = _perturb(batch, "sma")
    changed = _unwrap(compare_reference_outputs(sma, batch, after))
    mint = changed.mint
    assert mint is not None, changed
    print(
        f"upgrade that changes output: {changed.verdict.value} "
        f"mint {mint.previous_format_version}->{mint.minted_format_version} "
        f"protocol_unchanged={changed.protocol_format_version}"
    )
    evidence_differs = mint.before_evidence["sma"] != mint.after_evidence["sma"]
    print(f"before/after evidence differ: {evidence_differs}")


def _perturb(result: BatchResult, channel: str) -> BatchResult:
    """A candidate-reference result: the same series with one present value nudged one ULP."""
    series = result.outputs[channel]
    values = [series.value_at(index) for index in range(series.length)]
    for index, state in enumerate(series.presence):
        if state is PresenceState.PRESENT:
            values[index] += 1
            break
    changed = _unwrap(
        IndicatorSeries.try_create(
            _unwrap(encode_int64_values(values)),
            series.scale,
            list(series.presence),
            list(series.knowable_at),
        )
    )
    outputs = dict(result.outputs)
    outputs[channel] = changed
    return BatchResult(outputs=outputs, label=result.label)


if __name__ == "__main__":
    main()
