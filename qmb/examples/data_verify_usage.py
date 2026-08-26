"""Reference usage — ``qmb data verify`` window integrity (Story 18.4).

Executable::

    python qmb/examples/data_verify_usage.py

Shows the things B-11 / SC-07 pin down for integrity:

1. Pass carries counts; defects are CT-04 refusals with machine-readable context.
2. Blank edge tolerance leaves the guard un-armed and reports raw offsets.
3. Armed edge tolerance refuses when edges drift beyond the configured bound.
4. Interior gaps are reported and never filled (synthetic fill is Epic 23).
5. Pass/fail journals through CT-13 data quality with a propagated correlation_id.
6. Same immutable window + same config reproduces the same factual verdict.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar, cast

from qmb.data import verify, verify_identity
from qmf.core import RefusalCategory, Result, World, WriterId, is_ok, is_refusal
from qmf.data import EvidenceStore
from qmf.data.journal_producer import JournalReader

T = TypeVar("T")

_START = 1_700_000_000_000_000_000
_END = _START + 60_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    if not condition:
        raise AssertionError(f"expected {what}")


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "qmb", "verify", "boot-1"), "writer")


def _ticks() -> tuple[dict[str, object], ...]:
    return (
        {
            "t_ns": _START + 1_000_000_000,
            "bid": {"verbatim": 110250, "scale": 5},
            "ask": {"verbatim": 110260, "scale": 5},
        },
        {
            "t_ns": _START + 3_000_000_000,
            "bid": {"verbatim": 110251, "scale": 5},
            "ask": {"verbatim": 110261, "scale": 5},
        },
        {
            "t_ns": _START + 20_000_000_000,
            "bid": {"verbatim": 110252, "scale": 5},
            "ask": {"verbatim": 110262, "scale": 5},
        },
    )


def main() -> None:
    identity = verify_identity()
    _require("edge_tolerance_default" not in identity, "no invented edge tolerance")
    _require(identity["edge_guard_requires_explicit_tolerance"] is True, "guard opt-in")
    _require(identity["fills_gaps"] is False, "verify never fills")
    _require(identity["verdict_is_edge_claim"] is False, "factual data-quality only")
    print(
        "verify identity: "
        f"kind={identity['integrity_kind']} "
        f"edge_opt_in={identity['edge_guard_requires_explicit_tolerance']} "
        f"fills={identity['fills_gaps']}"
    )

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = EvidenceStore(root)
        base: dict[str, object] = {
            "archive": str(root),
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "start": _START,
            "end": _END,
            "side": "both",
            "world": World.REPLAY,
            "store": store,
            "writer": _writer(),
            "ticks": _ticks(),
            "expected_step_ns": 2_000_000_000,
            "correlation_id": "demo-verify-18-4",
            "journal_instant": _END + 1,
        }

        # Un-armed edge guard: raw offsets only, interior gap reported, pass.
        passed = _unwrap(verify(base), "unarmed verify pass")
        _require(passed.verdict == "pass", "clean window passes")
        _require(passed.edge_guard_armed is False, "blank tolerance un-armed")
        _require(passed.edge_start_offset_ns == 1_000_000_000, "raw leading offset")
        _require(len(passed.interior_gaps) == 1, "interior gap reported")
        _require(passed.interior_gaps[0].as_mapping()["filled"] is False, "gap not filled")
        _require(passed.is_edge_claim is False, "not an edge claim")
        print(
            f"pass counts={passed.counts.as_mapping()} "
            f"edge_offsets=({passed.edge_start_offset_ns},{passed.edge_end_offset_ns}) "
            f"interior_gaps={len(passed.interior_gaps)}"
        )

        # Armed edge guard beyond leading offset → CT-04 refusal.
        refused = verify({**base, "edge_tolerance_ns": 100, "correlation_id": "demo-edge-fail"})
        assert is_refusal(refused)
        _require(refused.category is RefusalCategory.POLICY_REJECTION, "armed edge defect refuses")
        result = cast("dict[str, object]", refused.context["result"])
        print(
            f"armed edge refusal signal={refused.context.get('signal')} verdict={result['verdict']}"
        )

        # Float price taint → CT-04.
        tainted = verify(
            {
                **base,
                "ticks": (
                    {
                        "t_ns": _START + 1,
                        "bid": 1.1,
                        "ask": {"verbatim": 2, "scale": 5},
                    },
                ),
                "expected_step_ns": None,
                "correlation_id": "demo-taint",
            }
        )
        assert is_refusal(tainted)
        _require(tainted.category is RefusalCategory.POLICY_REJECTION, "float taint refuses")
        print(f"float taint refused category={tainted.category.value}")

        # CT-13 journal carries propagated correlation_id.
        world = _unwrap(store.for_world(World.REPLAY), "replay world")
        events = _unwrap(JournalReader(world.journal).read("dq", for_world=World.REPLAY), "dq read")
        _require(
            any(event.correlation_id == "demo-verify-18-4" for event in events), "corr propagated"
        )
        print(f"CT-13 data-quality events={len(events)} correlation propagated")

        # Determinism of the factual verdict (correlation_id is linking-only).
        again = _unwrap(
            verify({**base, "correlation_id": "demo-verify-replay"}),
            "deterministic re-run",
        )
        _require(again.verdict == passed.verdict, "same verdict")
        _require(again.counts.as_mapping() == passed.counts.as_mapping(), "same counts")
        print("determinism: same window + config -> same verdict")

    print("qmb data verify ok")


if __name__ == "__main__":
    main()
