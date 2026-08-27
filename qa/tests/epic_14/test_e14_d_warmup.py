"""Epic 14 · Group D — in-loop warm-up with trading locked (Story 14.4, R16-R20).

B-2/SC-10/CT-12: warm-up is the SAME loop, same six-phase order, same adapters,
with trading LOCKED; any act during warm-up is a typed policy rejection;
warm-up length is the AD-21 split-manifest embargo observation COUNT (never a
Duration) and the loop adds no second window; the result label's evidence range
is the trading interval only; pre-seeding buffers is NOT warm-up.
"""

from __future__ import annotations

from _e14 import NS, RecordingHandler, slices

from qmf.core.chrono import Duration
from qmf.core.refusal import RefusalCategory, is_refusal
from qmb.runloop import (
    PRESEED_IS_WARMUP,
    SUBPHASES,
    WARMUP_ADDS_SECOND_WINDOW,
    WARMUP_UNIT,
    SplitEmbargo,
    guard_trading,
    preseed_indicator_buffers,
    refuse_act_during_warmup,
    run,
    run_slice,
)
from qmb.runloop import loop as loop_mod


def _ok(result: object) -> object:
    from qmf.core.refusal import is_ok

    assert is_ok(result), getattr(result, "context", result)
    return result.value  # type: ignore[attr-defined]


# --- T-14.4-a (L2) warm-up drives the same loop, same order, locked [R16] -----
def test_t144a_warmup_uses_same_loop_and_order() -> None:
    out = _ok(run(slices=slices(("eurusd",), n=2), stream_set=("eurusd",), embargo=5))
    assert out.is_warming_up is True  # 2 observations < 5-count embargo
    for sub in out.slices:
        assert sub.subphase_order() == tuple(SUBPHASES)
        assert sub.is_warming_up is True
    assert out.warmup.embargo.unit == WARMUP_UNIT


# --- T-14.4-b (L2) any act during warm-up is a policy rejection [R17] · P1 ----
def test_t144b_act_during_warmup_is_policy_rejection() -> None:
    for action in ("entry", "exit", "cancel", "resize"):
        refused = refuse_act_during_warmup(action)
        assert is_refusal(refused) and refused.category is RefusalCategory.POLICY_REJECTION
    locked = guard_trading(is_warming_up=True, action="fill")
    assert is_refusal(locked) and locked.category is RefusalCategory.POLICY_REJECTION
    assert _ok(guard_trading(is_warming_up=False, action="fill")) is None
    # Integration: minting an intent while warm-up is locked aborts the run.
    handler = RecordingHandler(mint_on="eurusd")
    refused_run = run(
        slices=slices(("eurusd",), n=1),
        stream_set=("eurusd",),
        embargo=1,
        handler=handler,
    )
    assert is_refusal(refused_run), refused_run
    assert refused_run.category is RefusalCategory.POLICY_REJECTION
    assert refused_run.context.get("field") == "warmup"


# --- T-14.4-c (L1) length is an observation count, never a Duration [R18] -----
def test_t144c_embargo_is_observation_count_no_second_window() -> None:
    assert WARMUP_UNIT == "observation-count"
    assert WARMUP_ADDS_SECOND_WINDOW is False
    # A Duration is refused as an embargo length.
    dur = SplitEmbargo.try_create(_ok(Duration.try_create(1_000_000)))
    assert is_refusal(dur) and dur.category is RefusalCategory.INVALID_INPUT
    # A "second window" key is refused — the loop adds no second window.
    second = SplitEmbargo.try_create({"warmup_bars": 5})
    assert is_refusal(second) and second.category is RefusalCategory.INVALID_INPUT
    # A plain non-negative observation count is accepted.
    embargo = _ok(SplitEmbargo.try_create({"embargo_width": 3}))
    assert embargo.observation_count == 3
    assert embargo.unit == WARMUP_UNIT


# --- T-14.4-d (L2) evidence range is the trading interval only [R19] · P1 -----
def test_t144d_evidence_range_excludes_warmup() -> None:
    out = _ok(run(slices=slices(("eurusd",), n=3), stream_set=("eurusd",), embargo=1))
    # slice 1 (frontier NS) is warm-up; slices 2 and 3 are trading.
    assert out.slices[0].is_warming_up is True
    assert out.slices[1].is_warming_up is False
    assert out.is_warming_up is False
    assert out.evidence_range.start.value_ns == NS + 1  # first TRADING frontier
    assert out.evidence_range.start.value_ns > NS  # warm-up frontier NS is excluded
    assert out.self_assessment["evidence_covers_warmup"] is False


# --- T-14.4-e (L1) pre-seeding buffers is NOT warm-up [R20] -------------------
def test_t144e_preseeding_is_not_warmup() -> None:
    assert PRESEED_IS_WARMUP is False
    refused = preseed_indicator_buffers()
    assert is_refusal(refused) and refused.category is RefusalCategory.POLICY_REJECTION
    # A non-progress "warmup" argument is rejected (pre-seeding is not warm-up).
    from _e14 import obs

    bad = run_slice((obs("eurusd"),), stream_set=("eurusd",), warmup="pre-seeded-buffers")
    assert is_refusal(bad)
    assert loop_mod.PRESEED_IS_WARMUP is False
