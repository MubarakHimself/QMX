"""Reference usage — Story 7.3: batch mode with as-of-only alignment and presence-mapped
outputs (COMP-QMF-INDICATORS; CT-16; DEC-0126).

Executable::

    python packages/qmf-indicators/examples/batch_mode_usage.py

Shows the four things Story 7.3 pins down, over a single SMA configuration computed with
the canonical TA-Lib reference:

1. Batch output is full-length and index-aligned to the input — begin-index trimming is
   prohibited — and every position carries a ``registry:presence_map_states`` value, with
   no NaN or sentinel anywhere.
2. A market-hours-closed position is ``absent_by_schedule`` (never a gap); a calendar-open
   position with no data is a ``gap`` under the mark-gap policy (never silent filling); and
   during warm-up the output is a marked ``not_ready`` value, never a number.
3. A value is aligned to an evaluation instant as-of only — the last value known at or
   before it; a forward-fill request across the instant is a policy rejection (no
   look-ahead).
4. Every output sample carries a knowable-at instant, and a confirmed (bar-closed) result
   is admissible to governed evidence while a provisional one never is.
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
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    AlignmentMode,
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
    SupportedMode,
    align_to_instant,
    compute_batch,
    require_governed,
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
            warm_up=3,
            output_schema=[sma_channel],
            supported_modes=[SupportedMode.BATCH, SupportedMode.STREAMING],
            arithmetic_reference_configuration=reference,
        )
    )

    # The application supplies the aggregated-bar column: present observations, a
    # calendar-open gap (position 5), and a market-hours-closed position (position 6). The
    # indicator receives its BarSpec as data and derives no bar boundaries.
    scaled_closes = [10000, 10100, 10200, 10300, 10400, 0, 0, 10500]
    presence = [
        PresenceState.PRESENT,
        PresenceState.PRESENT,
        PresenceState.PRESENT,
        PresenceState.PRESENT,
        PresenceState.PRESENT,
        PresenceState.GAP,
        PresenceState.ABSENT_BY_SCHEDULE,
        PresenceState.PRESENT,
    ]
    knowable_at = [_unwrap(Instant.try_create(1_000 + step)) for step in range(len(scaled_closes))]
    series = _unwrap(InputSeries.from_values(scaled_closes, 2, presence, knowable_at))

    result = _unwrap(
        compute_batch(
            configuration, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY
        )
    )
    output = result.outputs["sma"]

    # 1. Full-length, index-aligned, presence-mapped.
    print(f"batch output length: {output.length} (input length: {series.length})")
    print("presence map: " + " ".join(state.value for state in output.presence))

    # 2. Schedule vs missing vs warm-up.
    print(f"position 5 (calendar-open, no data): {output.presence[5].value}")
    print(f"position 6 (market-hours closed): {output.presence[6].value}")
    print(f"position 0 (during warm-up): {output.presence[0].value}")

    # 3. As-of-only alignment; forward-fill across the instant is refused.
    at_instant = _unwrap(Instant.try_create(1_004))
    as_of = _unwrap(align_to_instant(output, at_instant, AlignmentMode.AS_OF))
    print(f"as-of@1004: {as_of.presence.value} at index {as_of.index}")
    forward_fill = align_to_instant(output, at_instant, AlignmentMode.FORWARD_FILL)
    assert is_refusal(forward_fill), forward_fill
    print(f"forward-fill across the instant: {forward_fill.category.value}")

    # 4. Every sample carries a knowable-at; a confirmed result is governable.
    print(f"output sample knowable-at count: {len(output.knowable_at)}")
    governed = require_governed(result)
    evidence = result.label.evidence_class.value
    verdict = f"admitted ({evidence})" if is_ok(governed) else "refused"
    print(f"governed evidence: {verdict}")


if __name__ == "__main__":
    main()
