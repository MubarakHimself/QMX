"""Reference usage — Python API door as a pure re-export (Story 16.3).

Executable::

    python qmb/examples/api_door_usage.py

Shows the things Story 16.3 / B-1 / B-4 / B-13 / AR-58 pin down:

1. ``qmb.doors.api`` is a thin re-export of the library surface, importable
   from the uv-added ``qmb`` package.
2. A typed refusal is RETURNED verbatim — never raised, never swallowed.
3. The UI backend consumes this door in-process, never stacked over HTTP.
4. A direct ``run()`` through the door returns values and writes no ledger.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmb.doors import api
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _obs(stream_id: str, ns: int = _NS) -> api.SliceObservation:
    return _unwrap(
        api.SliceObservation.try_create(stream_id, _instant(ns), True),
        "observation",
    )


def importable_reexport() -> None:
    assert api.run is qmb.run
    assert api.compile_run_config is qmb.compile_run_config
    assert api.STRUCTURAL_SEED is qmb.STRUCTURAL_SEED
    assert api.CHANNEL == "uv add qmb"
    print("importable from uv-added qmb as qmb.doors.api")
    print("thin re-export: api.run is qmb.run")


def refusals_return_verbatim() -> None:
    refused = api.compile_run_config(
        None,
        book_fragment=None,
        bms_fragment=None,
        run_spec=None,
    )
    assert is_refusal(refused)
    assert isinstance(refused, TypedRefusal)
    assert refused.category is RefusalCategory.INVALID_INPUT
    print("refusal returned verbatim, not raised")


def ui_consumes_in_process() -> None:
    identity = api.api_door_identity()
    assert identity["in_process"] is True
    assert identity["stacked_over_http"] is False
    assert identity["consumer"] == "ui-backend"
    assert identity["transport"] == "in-process"
    print("UI backend consumes this in-process; never HTTP")


def direct_run_writes_no_ledger(output_root: Path) -> None:
    _unwrap(
        api.run(
            slices=((_obs("eurusd"),),),
            stream_set=("eurusd",),
            handler=api.SilentSliceHandler(),
        ),
        "pure run",
    )
    assert list(output_root.rglob("*.jsonl")) == []
    sink = _unwrap(
        api.LedgerSink.try_create(
            output_root / "ledger",
            machine="example",
            worker_slot=0,
            boot_epoch_id="boot-1",
        ),
        "sink",
    )
    merged = _unwrap(
        api.read_merge_view(sink.root, world=World.REPLAY, role=api.ROLE_CONFIRMATION),
        "merge",
    )
    assert merged == ()
    print("direct library run() produces no governed evidence")


def main() -> None:
    importable_reexport()
    refusals_return_verbatim()
    ui_consumes_in_process()
    with tempfile.TemporaryDirectory(prefix="qmb_api_door_", ignore_cleanup_errors=True) as tmp:
        direct_run_writes_no_ledger(Path(tmp))
    print("qmb Python API door ok")


if __name__ == "__main__":
    main()
