"""Epic 14 · Group B — six pinned identity-bearing sub-phases (Story 14.2, R7-R11).

B-2/AR-57: per slice the sub-phases run in EXACTLY the pinned order; a phase-5
minted intent never fills against this slice's path; within a phase instruments
process in stream-set declaration order; indicators update on closed data only;
altering the order is identity-bearing; an out-of-order order is refused.
"""

from __future__ import annotations

import inspect

from _e14 import NS, RecordingHandler, inst, obs, ok

from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import is_refusal
from qmb.runloop import SUBPHASES, WarmupProgress, loop_identity, run, run_slice
from qmb.runloop import loop as loop_mod

_PINNED = (
    "frontier-advance",
    "scheduled-position-events",
    "resting-orders",
    "closed-data-indicators-structure",
    "strategy-callbacks",
    "new-intents-rest",
)


# --- T-14.2-a (L1) exact pinned order, no omission, no reorder [R7] · P0 ------
def test_t142a_subphase_order_is_exactly_pinned() -> None:
    assert tuple(SUBPHASES) == _PINNED
    out = ok(run_slice((obs("eurusd"),), stream_set=("eurusd",)))
    assert out.subphase_order() == _PINNED
    assert len(out.trace) == 6


# --- T-14.2-b (L2) a phase-5 minted intent never fills this slice [R8] · P0 ---
def test_t142b_minted_intent_never_fills_its_own_slice() -> None:
    handler = RecordingHandler(mint_on="eurusd", fill=True)  # execute_resting would fill
    out = ok(
        run_slice(
            (obs("eurusd"), obs("gbpusd")),
            stream_set=("eurusd", "gbpusd"),
            handler=handler,
            resting=(),
        )
    )
    assert len(out.minted) == 1
    minted_id = out.minted[0]
    # Observably resting after the slice; never filled against this slice's path.
    assert minted_id in {item.intent_id for item in out.resting}
    assert minted_id in out.ineligible
    assert minted_id not in out.filled
    assert out.filled == ()


# --- T-14.2-c (L1) per-phase order == stream-set declaration order [R9] -------
def test_t142c_instrument_order_is_declaration_order() -> None:
    forward = RecordingHandler()
    out_fwd = ok(
        run_slice((obs("eurusd"), obs("gbpusd")), stream_set=("eurusd", "gbpusd"), handler=forward)
    )
    assert out_fwd.trace[0].instrument_order == ("eurusd", "gbpusd")
    assert forward.stream_updates == ["eurusd", "gbpusd"]
    # Permuting the declaration permutes the processing order deterministically.
    rev = RecordingHandler()
    out_rev = ok(
        run_slice((obs("gbpusd"), obs("eurusd")), stream_set=("gbpusd", "eurusd"), handler=rev)
    )
    assert out_rev.trace[0].instrument_order == ("gbpusd", "eurusd")
    assert rev.stream_updates == ["gbpusd", "eurusd"]


# --- T-14.2-d (L2) indicators see closed data only; forming never reaches [R10]
def test_t142d_closed_data_only_forming_skipped() -> None:
    handler = RecordingHandler()
    # Two streams at the same instant: one closed, one forming.
    slice_ = (obs("eurusd", NS, closed=True), obs("gbpusd", NS, closed=False))
    ok(run_slice(slice_, stream_set=("eurusd", "gbpusd"), handler=handler))
    assert handler.closed_updates == ["eurusd"]
    assert "gbpusd" not in handler.closed_updates


# --- T-14.2-e (L3) altering sub-phase order changes the fingerprint [R11] · P0
def test_t142e_subphase_order_is_identity_bearing() -> None:
    base = ok(fingerprint(loop_identity()))
    altered = dict(loop_identity())
    altered["subphases"] = tuple(reversed(SUBPHASES))
    changed = ok(fingerprint(altered))
    assert base != changed
    # Any permutation of the pinned order is a distinct identity.
    swapped = dict(loop_identity())
    swapped["subphases"] = (SUBPHASES[1], SUBPHASES[0], *SUBPHASES[2:])
    assert ok(fingerprint(swapped)) != base


# --- T-14.2-f (L1) order is not a runtime parameter; unknown phase refused [R11]
def test_t142f_order_violation_is_unrepresentable_or_refused() -> None:
    # The pinned order is an immutable tuple, not runtime-supplied.
    assert isinstance(SUBPHASES, tuple)
    assert "subphase" not in inspect.signature(run).parameters
    assert "subphases" not in inspect.signature(run).parameters
    assert "order" not in inspect.signature(run_slice).parameters
    # The private dispatcher refuses an out-of-order / unknown phase name.
    acc = loop_mod._Acc(
        frontier=inst(NS),
        remaining=[],
        filled=[],
        minted=[],
        traces=[],
        observations={},
        stream_ids=(),
        handler=loop_mod.SilentSliceHandler(),
        consumptions=(),
        warmup=ok(WarmupProgress.try_create(0)),
        slice_warming=False,
    )
    refused = loop_mod._run_one_phase("bogus-out-of-order-phase", acc)
    assert is_refusal(refused), refused
    assert refused.context.get("field") == "subphases"
