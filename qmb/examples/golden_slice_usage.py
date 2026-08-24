"""Reference usage — golden-slice CT-32 determinism (Story 14.7).

Executable::

    python qmb/examples/golden_slice_usage.py

Shows the things AR-58 / B-2 / B-5 / FM-11 pin down:

1. Two runs of identical inputs produce the same CT-32 fingerprint.
2. Re-running a run id under its resolved config reproduces that fingerprint.
3. A fingerprint mismatch is a typed refusal, never a silent accept.
4. Concurrency is scheduling only; ``run()`` does not depend on siblings.
5. Chart series and HTML are not part of the fingerprint (Epic 19).
"""

from __future__ import annotations

from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.results import (
    CHART_SERIES_IN_IDENTITY,
    CONCURRENCY_IS_SCHEDULING_ONLY,
    HTML_PAYLOAD,
    RESULT_CONTRACT,
)
from qmb.runloop import (
    STREAM_SET_KEY,
    SilentSliceHandler,
    SliceObservation,
    loop_identity,
    reproduce_run,
    run,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _unwrap(SliceObservation.try_create(stream_id, _instant(ns), True), "observation")


def _config() -> ResolvedRunConfig:
    stamp = _unwrap(fingerprint({"n": "golden-example"}), "stamp")
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd", "gbpusd")},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def identical_inputs_identical_fingerprint() -> str:
    """Two isolated runs of the same resolved config share one CT-32 fingerprint."""
    config = _config()
    slices = ((_obs("eurusd"), _obs("gbpusd")),)
    first = _unwrap(
        run(slices=slices, config=config, handler=SilentSliceHandler()),
        "run-a",
    )
    second = _unwrap(
        run(slices=slices, config=config, handler=SilentSliceHandler()),
        "run-b",
    )
    left = _unwrap(first.ct32_fingerprint(), "fp-a")
    right = _unwrap(second.ct32_fingerprint(), "fp-b")
    assert left == right
    assert first.fp1_identity() == second.fp1_identity()
    assert "html" not in first.fp1_identity()
    assert CHART_SERIES_IN_IDENTITY is False
    assert HTML_PAYLOAD is False
    return left.value


def reproduce_or_refuse(expected: str) -> None:
    """Re-run the run id under the resolved config, or a typed refusal."""
    config = _config()
    slices = ((_obs("eurusd"), _obs("gbpusd")),)
    original = _unwrap(
        run(slices=slices, config=config, handler=SilentSliceHandler()),
        "original",
    )
    expected_fp = _unwrap(original.ct32_fingerprint(), "expected")
    assert expected_fp.value == expected
    reproduced = _unwrap(
        reproduce_run(
            run_id=config.fingerprint,
            config=config,
            expected_fingerprint=expected_fp,
            slices=slices,
            handler=SilentSliceHandler(),
        ),
        "reproduce",
    )
    assert _unwrap(reproduced.fingerprint(), "reproduced fp") == expected_fp
    other = _unwrap(fingerprint({"n": "not-this-run"}), "other")
    refused = reproduce_run(
        run_id=config.fingerprint,
        config=config,
        expected_fingerprint=other,
        slices=slices,
        handler=SilentSliceHandler(),
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "ct32_fingerprint"


def concurrency_is_scheduling_only(expected: str) -> None:
    """A sibling run does not leak into the golden slice."""
    assert CONCURRENCY_IS_SCHEDULING_ONLY is True
    assert loop_identity()["pure_run_independent_of_siblings"] is True
    config = _config()
    slices = ((_obs("eurusd"), _obs("gbpusd")),)
    sibling_cfg = ResolvedRunConfig(
        format_version=config.format_version,
        book_fp1=config.book_fp1,
        bms_fp1=config.bms_fp1,
        bot_fp1=config.bot_fp1,
        book_fragment_fp1=config.book_fragment_fp1,
        bms_fragment_fp1=config.bms_fragment_fp1,
        keys={STREAM_SET_KEY: ("usdjpy",)},
        clock=config.clock,
        data_provenance=config.data_provenance,
        world=config.world,
        fingerprint=_unwrap(fingerprint({"n": "sibling"}), "sibling stamp"),
        binding_fp1=config.binding_fp1,
    )
    _unwrap(
        run(slices=((_obs("usdjpy"),),), config=sibling_cfg, handler=SilentSliceHandler()),
        "sibling",
    )
    isolated = _unwrap(
        run(slices=slices, config=config, handler=SilentSliceHandler()),
        "after-sibling",
    )
    assert _unwrap(isolated.ct32_fingerprint(), "after sibling").value == expected


def main() -> None:
    assert qmb.RESULT_CONTRACT == RESULT_CONTRACT
    assert qmb.reproduce_run is reproduce_run
    fingerprint_value = identical_inputs_identical_fingerprint()
    print("two identical runs share one CT-32 fingerprint")
    reproduce_or_refuse(fingerprint_value)
    print("re-run under resolved config reproduces; mismatch is typed refusal")
    concurrency_is_scheduling_only(fingerprint_value)
    print("concurrency is scheduling only; run() does not depend on siblings")
    print("no HTML/charts in the fingerprint")
    print("golden-slice determinism ok")


if __name__ == "__main__":
    main()
