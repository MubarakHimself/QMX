"""L4 composition-law participation — T7-SCN.

A CT-16 output series fed as a CT-16 input to a second configuration: the derived series'
identity carries the upstream artifact's fingerprint and never mints an Instrument, and
the two-hop batch result equals the two-hop streaming result under the equality law. The
CT-16 → CT-17 hop (structure families) is Epic 9's and out of scope (epic-binding).
"""

from __future__ import annotations

import _fixtures as F
from qmf.core import World, is_ok
from qmf.indicators import (
    ChannelKind,
    InputSeries,
    PresenceState,
    QuoteSide,
    SeriesInput,
    StreamingIndicator,
    assert_mode_equality,
    compute_batch,
    reference_status,
)


def _series_from_output(out) -> InputSeries:
    """Re-express a hop-1 IndicatorSeries as a hop-2 InputSeries (same bulk form)."""
    return F.unwrap(
        InputSeries.try_create(out.values, out.scale, list(out.presence), list(out.knowable_at))
    )


def test_scn_upstream_fingerprint_enters_downstream_identity() -> None:
    """The upstream artifact's fingerprint enters downstream identity: a derived input
    carries it (composition is law), and it moves the downstream fp1. Counter-case: the
    upstream fingerprint absent from downstream identity."""
    hop1 = F.config(warm_up=0)
    values = [100, 101, 102, 103, 104]
    hop1_out = F.unwrap(compute_batch(hop1, {"close": F.input_series(values)}, kernel=F.EchoKernel(), world=World.REPLAY)).outputs["sma"]
    upstream_fp = F.unwrap(hop1_out.fingerprint())

    # A derived input: source is the upstream artifact (a source-id token — NOT an
    # Instrument, so the derived series never mints an Instrument), carrying the upstream fp.
    derived = F.unwrap(
        SeriesInput.try_create(
            name="close",
            source="derived:sma-hop1",
            bar_spec={"kind": "time-interval", "seconds": 60},
            channel_kind=ChannelKind.FLOAT_ANALYTIC,
            quote_side=QuoteSide.MID,
            upstream_fingerprint=upstream_fp,
        )
    )
    assert derived.upstream_fingerprint == upstream_fp
    assert "upstream_fingerprint" in derived.fp1_identity()

    non_derived = F.series_input("close", source="derived:sma-hop1", channel_kind=ChannelKind.FLOAT_ANALYTIC)
    assert F.unwrap(F.config(inputs=[derived]).fp1()).value != F.unwrap(F.config(inputs=[non_derived]).fp1()).value


def test_scn_two_hop_batch_equals_two_hop_streaming() -> None:
    """Driven end to end over both paths (with the arithmetic reference asserted at the
    seam), the two-hop batch result equals the two-hop streaming result under the equality
    law. Counter-case: the two paths diverging across the chain."""
    assert is_ok(reference_status()), "the arithmetic reference is not verified at the seam"

    hop1 = F.config(warm_up=0)
    values = [100, 101, 102, 103, 104, 105]

    # Hop 1 batch output, re-expressed as a hop-2 input column.
    hop1_batch = F.unwrap(compute_batch(hop1, {"close": F.input_series(values)}, kernel=F.EchoKernel(), world=World.REPLAY))
    hop2_input = _series_from_output(hop1_batch.outputs["sma"])

    hop2 = F.config(warm_up=0)
    hop2_batch = F.unwrap(compute_batch(hop2, {"close": hop2_input}, kernel=F.EchoKernel(), world=World.REPLAY))

    # Hop 2 streaming, fed the same hop-1 output values position by position.
    stream = F.unwrap(
        StreamingIndicator.try_create(
            hop2, kernel=F.EchoKernel(), world=World.REPLAY, writer_id=F.writer(), scope=F.scope(),
            input_scales={"close": hop2_input.scale},
        )
    )
    for index in range(hop2_input.length):
        F.unwrap(
            stream.update({
                "close": F.observation(
                    hop2_input.value_at(index), hop2_input.presence_at(index), hop2_input.knowable_at[index].value_ns
                )
            })
        )
    hop2_stream = F.unwrap(stream.result())

    equal = assert_mode_equality(hop2, hop2_batch, hop2_stream)
    assert is_ok(equal) and equal.value is True, "the two-hop chain diverged across modes"
