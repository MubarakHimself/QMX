"""L3 acceptance — Story 7.3 batch mode (T7-A8..A12). Gate 3: BarSpec-as-data,
as-of-only alignment, honest presence, warm-up discipline."""

from __future__ import annotations

import _fixtures as F
from qmf.core import EvidenceClass, World, is_ok, is_refusal
from qmf.indicators import (
    AlignmentMode,
    EmissionPolicy,
    EmissionTiming,
    PresenceState,
    ReferenceKernel,
    align_to_instant,
    compute_batch,
    require_governed,
)


def _batch(cfg, series, kernel=None):
    return compute_batch(
        cfg, {"close": series}, kernel=kernel or F.EchoKernel(), world=World.REPLAY
    )


# --- T7-A8 [R12] P0 — full-length, index-aligned, presence-mapped -----------


def test_a8_output_is_full_length_index_aligned_no_sentinel() -> None:
    """Counter-case: begin-index trimming (output shorter than input) or a NaN/sentinel.
    Every position of the input maps to exactly one presence-mapped output position."""
    values = [100, 102, 101, 103, 105, 104, 106]
    series = F.input_series(values)
    out = F.unwrap(_batch(F.config(warm_up=2), series, ReferenceKernel())).outputs["sma"]
    assert out.length == len(values), "begin-index trimming is prohibited"
    assert len(out.presence) == len(values)
    for i in range(out.length):
        assert isinstance(out.value_at(i), int)  # int64 layout cannot hold a NaN
        assert out.presence_at(i) in set(PresenceState)


def test_a8_absent_and_gap_positions_carry_presence_states_not_holes() -> None:
    """A non-present input position is a presence-map state at the same index — never an
    omitted slot. Length is preserved and the state is carried through."""
    values = [100, 0, 102, 0, 104]
    presence = [
        PresenceState.PRESENT,
        PresenceState.ABSENT_BY_SCHEDULE,
        PresenceState.PRESENT,
        PresenceState.GAP,
        PresenceState.PRESENT,
    ]
    series = F.input_series(values, presence)
    out = F.unwrap(_batch(F.config(warm_up=0), series)).outputs["sma"]
    assert out.length == 5
    assert out.presence_at(1) is PresenceState.ABSENT_BY_SCHEDULE
    assert out.presence_at(3) is PresenceState.GAP


# --- T7-A9 [R13] P0 — BarSpec received as data, never derived ---------------


def test_a9_different_barspec_is_a_different_configured_identity() -> None:
    """The indicator receives its BarSpec as data; the same values under a different
    BarSpec are a different configured identity. Counter-case: two BarSpecs sharing fp1."""
    minute = F.series_input("close", bar_spec={"kind": "time-interval", "seconds": 60})
    hour = F.series_input("close", bar_spec={"kind": "time-interval", "seconds": 3600})
    assert F.unwrap(F.config(inputs=[minute]).fp1()).value != F.unwrap(F.config(inputs=[hour]).fp1()).value


def test_a9_indicator_never_derives_bar_boundaries_passes_knowable_at_through() -> None:
    """Bar boundaries are not derived: for a single-input config the output's per-position
    knowable-at equals the input's (the indicator computes no instants of its own)."""
    values = [100, 101, 102, 103]
    series = F.input_series(values, start=5_000)
    out = F.unwrap(_batch(F.config(warm_up=0), series)).outputs["sma"]
    assert [i.value_ns for i in out.knowable_at] == [i.value_ns for i in series.knowable_at]


# --- T7-A10 [R14] P0 — as-of only -------------------------------------------


def test_a10_forward_fill_or_interpolation_across_the_instant_is_policy_rejection() -> None:
    """Only as-of alignment is legal for governed evidence. Counter-case: a forward-fill or
    interpolation request returning a value instead of a policy rejection."""
    series = F.input_series([100, 101, 102])
    instant = F.instants(1, start=2_000)[0]
    for mode in (AlignmentMode.FORWARD_FILL, AlignmentMode.INTERPOLATE):
        refusal = align_to_instant(series, instant, mode)
        assert is_refusal(refusal)
        assert refusal.category.value == "policy rejection"


def test_a10_as_of_returns_last_value_known_at_or_before_the_instant() -> None:
    """The accept arm: as-of returns the last present value whose knowable-at ≤ the instant;
    nothing known yet is a not_ready sample, never a filled number."""
    series = F.input_series([100, 101, 102], start=1_000)  # instants 1000,1001,1002
    at_1001 = align_to_instant(series, F.instants(1, start=1_001)[0], AlignmentMode.AS_OF)
    sample = F.unwrap(at_1001)
    assert sample.presence is PresenceState.PRESENT
    assert sample.value == 101 and sample.index == 1
    before_all = align_to_instant(series, F.instants(1, start=999)[0], AlignmentMode.AS_OF)
    assert F.unwrap(before_all).presence is PresenceState.NOT_READY
    assert F.unwrap(before_all).value is None


# --- T7-A11 [R15] P1 — schedule vs missing ----------------------------------


def test_a11_calendar_closed_is_absent_by_schedule_never_a_gap() -> None:
    values = [100, 0, 102]
    presence = [PresenceState.PRESENT, PresenceState.ABSENT_BY_SCHEDULE, PresenceState.PRESENT]
    out = F.unwrap(_batch(F.config(warm_up=0), F.input_series(values, presence))).outputs["sma"]
    assert out.presence_at(1) is PresenceState.ABSENT_BY_SCHEDULE


def test_a11_calendar_open_gap_follows_declared_policy_never_silent_fill() -> None:
    """mark-gap marks a gap; refuse returns a policy rejection. Counter-case: a silent fill."""
    values = [100, 0, 102]
    presence = [PresenceState.PRESENT, PresenceState.GAP, PresenceState.PRESENT]
    marked = F.unwrap(_batch(F.config(warm_up=0, missing_value_policy="mark-gap"), F.input_series(values, presence)))
    assert marked.outputs["sma"].presence_at(1) is PresenceState.GAP
    refused = _batch(F.config(warm_up=0, missing_value_policy="refuse"), F.input_series(values, presence))
    assert is_refusal(refused)
    assert refused.category.value == "policy rejection"


# --- T7-A12 [R16, R17] P0 — warm-up integer count + knowable-at -------------


def test_a12_warm_up_below_reference_lookback_is_refused() -> None:
    """warm-up must be at least the reference lookback. Counter-case: a warm-up below the
    kernel's leading-undefined count accepted."""
    series = F.input_series([100, 101, 102, 103, 104])
    refused = _batch(F.config(warm_up=2, supported_modes=["batch"]), series, F.EchoKernel(lookback=4))
    assert is_refusal(refused)
    assert refused.context["field"] == "warm_up"


def test_a12_warm_up_window_is_marked_not_ready_never_a_number() -> None:
    series = F.input_series([100, 101, 102, 103, 104])
    out = F.unwrap(_batch(F.config(warm_up=3, supported_modes=["batch"]), series, F.EchoKernel(lookback=0))).outputs["sma"]
    for i in range(3):
        assert out.presence_at(i) is PresenceState.NOT_READY
    assert out.presence_at(3) is PresenceState.PRESENT


def test_a12_every_sample_carries_a_knowable_at_and_provisional_never_enters_governed() -> None:
    """Every output sample carries a knowable-at; a provisional (in-progress) result is a
    policy rejection at the governed-evidence gate. Counter-case: provisional admitted."""
    series = F.input_series([100, 101, 102, 103])
    # bar-closed / confirmed result may enter governed evidence:
    confirmed = F.unwrap(_batch(F.config(warm_up=0, supported_modes=["batch"]), series))
    assert all(len(s.knowable_at) == s.length for s in confirmed.outputs.values())
    assert is_ok(require_governed(confirmed))
    # in-progress emission ⇒ provisional samples ⇒ refused at the governed gate:
    in_progress = F.config(
        warm_up=0,
        supported_modes=["batch"],
        emission_policy=EmissionPolicy(EmissionTiming.IN_PROGRESS, "per-tick"),
    )
    provisional = F.unwrap(_batch(in_progress, series))
    refusal = require_governed(provisional)
    assert is_refusal(refusal)
    assert refusal.category.value == "policy rejection"
