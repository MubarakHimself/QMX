"""Test-owned fixtures for the Epic 7 (qmf-indicators) independent audit.

Every fixture here is a controlled test input the TEST owns (no product mock data;
DEC-0007 / L20): a small deterministic input series supplied *as data* to the
indicator, a canonical both-modes configuration, and a pure in-test kernel that is an
independent :class:`BatchKernel` double — never the package's own reference. The
arithmetic reference itself is asserted, not mocked: :func:`verified_reference` returns
the live, import-time-verified :class:`ArithmeticReference`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeVar

from qmf.core import (
    CalendarIdentity,
    ExactRational,
    Instant,
    Instrument,
    Ok,
    Result,
    UnitKind,
    VenueId,
    WriterId,
    is_ok,
)
from qmf.indicators import (
    AlignmentPolicy,
    ArithmeticReference,
    ChannelKind,
    ConfiguredIndicator,
    InputSeries,
    KernelOutput,
    MissingValuePolicy,
    OutputArity,
    OutputChannel,
    PresenceState,
    QuoteSide,
    SeriesInput,
    SnapshotScope,
    StreamingObservation,
    SupportedMode,
    reference_status,
)

T = TypeVar("T")


def unwrap(result: Result[T]) -> T:
    """Unwrap an ``Ok`` in a test, failing loudly on a refusal."""
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


# --- identity nouns ---------------------------------------------------------


def instrument(symbol: str = "EURUSD", venue: str = "venue-ic") -> Instrument:
    return unwrap(Instrument.try_create(unwrap(VenueId.try_create(venue)), symbol))


def calendar(tzdata_version: str = "2025.2") -> CalendarIdentity:
    return unwrap(CalendarIdentity.try_create("forex-17NY", "v3", tzdata_version))


def period(numerator: int = 3, denominator: int = 1) -> ExactRational:
    return unwrap(ExactRational.try_create(numerator, denominator, UnitKind.COUNT))


def series_input(
    name: str = "close",
    *,
    source: object = None,
    bar_spec: object = None,
    channel_kind: ChannelKind = ChannelKind.EXACT_PRICE,
    quote_side: QuoteSide = QuoteSide.MID,
    upstream_fingerprint: object = None,
) -> SeriesInput:
    return unwrap(
        SeriesInput.try_create(
            name=name,
            source=source if source is not None else instrument(),
            bar_spec=bar_spec if bar_spec is not None else {"kind": "time-interval", "seconds": 60},
            channel_kind=channel_kind,
            quote_side=quote_side,
            upstream_fingerprint=upstream_fingerprint,
        )
    )


def output_channel(
    name: str = "sma",
    *,
    channel_kind: ChannelKind = ChannelKind.FLOAT_ANALYTIC,
    arity: OutputArity = OutputArity.SCALAR_PER_SAMPLE,
    index_offset: int = 0,
) -> OutputChannel:
    return unwrap(OutputChannel.try_create(name, channel_kind, arity, index_offset))


def verified_reference() -> ArithmeticReference:
    """The live, import-time-verified reference identity (asserted, not mocked)."""
    return unwrap(reference_status())


def config(**overrides: object) -> ConfiguredIndicator:
    """A canonical both-modes configuration; ``overrides`` replace named kwargs."""
    kwargs: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "parameters": {"period": period(3)},
        "inputs": [series_input("close")],
        "calendar_requirements": [calendar()],
        "alignment_policy": AlignmentPolicy.AS_OF,
        "missing_value_policy": MissingValuePolicy.MARK_GAP,
        "warm_up": 2,
        "output_schema": [output_channel("sma")],
        "supported_modes": [SupportedMode.BATCH, SupportedMode.STREAMING],
        "arithmetic_reference_configuration": verified_reference(),
    }
    kwargs.update(overrides)
    return unwrap(ConfiguredIndicator.try_create(**kwargs))


def try_config(**overrides: object) -> Result[ConfiguredIndicator]:
    """Attempt to build a configuration, returning the raw value-or-refusal Result."""
    kwargs: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "parameters": {"period": period(3)},
        "inputs": [series_input("close")],
        "calendar_requirements": [calendar()],
        "alignment_policy": AlignmentPolicy.AS_OF,
        "missing_value_policy": MissingValuePolicy.MARK_GAP,
        "warm_up": 2,
        "output_schema": [output_channel("sma")],
        "supported_modes": [SupportedMode.BATCH, SupportedMode.STREAMING],
        "arithmetic_reference_configuration": verified_reference(),
    }
    kwargs.update(overrides)
    return ConfiguredIndicator.try_create(**kwargs)


# --- bulk series ------------------------------------------------------------


def instants(count: int, start: int = 1_000) -> list[Instant]:
    return [unwrap(Instant.try_create(start + step)) for step in range(count)]


def input_series(
    scaled: Sequence[int],
    presence: Sequence[PresenceState] | None = None,
    *,
    scale: int = 2,
    start: int = 1_000,
) -> InputSeries:
    states = list(presence) if presence is not None else [PresenceState.PRESENT] * len(scaled)
    return unwrap(
        InputSeries.from_values(list(scaled), scale, states, instants(len(scaled), start))
    )


def writer(stream: str = "eurusd-sma", machine: str = "m1") -> WriterId:
    return unwrap(WriterId.try_create(machine, "indicator-feeder", stream, "boot-1"))


def scope(os_name: str = "windows-11", build: str = "ta-lib==0.7.1") -> SnapshotScope:
    return unwrap(SnapshotScope.try_create(os_name, build))


def observation(value: int, presence: PresenceState, ns: int) -> StreamingObservation:
    return unwrap(StreamingObservation.try_create(value, presence, unwrap(Instant.try_create(ns))))


# --- an independent, test-owned kernel double -------------------------------


class EchoKernel:
    """A pure, position-causal :class:`BatchKernel` double owned by the test.

    Echoes the primary dense input as the single output channel; ``lookback`` leading
    dense positions are undefined. It is NOT the package's reference kernel — it lets
    presence/warm-up/scatter and streaming==batch be asserted deterministically without
    the reference. Because each output depends only on its own position, streaming
    (recompute over the accumulated prefix) equals batch position for position.
    """

    def __init__(self, *, lookback: int = 0, scale: int = 2, bias: int = 0) -> None:
        self._lookback = lookback
        self._scale = scale
        self._bias = bias

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
        values: list[int | None] = [None] * prefix + [v + self._bias for v in dense[prefix:]]
        return Ok(
            KernelOutput(channels={channel: tuple(values)}, lookback=self._lookback, scale=self._scale)
        )
