"""Tier-1 tests for ``qmb data verify`` window integrity (Story 18.4, B-11)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar, cast

from click.testing import CliRunner
from qmb.data import (
    INTEGRITY_KIND,
    data_front_identity,
    parse_verify_request,
    verify,
    verify_identity,
)
from qmb.doors import api
from qmb.doors.cli import invoke_data, main
from qmf.core import RefusalCategory, Result, World, WriterId, is_ok, is_refusal
from qmf.data import EvidenceStore
from qmf.data.journal_producer import JournalReader

T = TypeVar("T")

_START = 1_700_000_000_000_000_000
_END = _START + 60_000_000_000
_CORR = "corr-verify-18-4"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "qmb", "verify", "boot-1"))


def _clean_ticks() -> tuple[dict[str, object], ...]:
    return (
        {
            "t_ns": _START + 1_000_000,
            "bid": {"verbatim": 110250, "scale": 5},
            "ask": {"verbatim": 110260, "scale": 5},
        },
        {
            "t_ns": _START + 2_000_000,
            "bid": {"verbatim": 110251, "scale": 5},
            "ask": {"verbatim": 110261, "scale": 5},
        },
        {
            "t_ns": _START + 3_000_000,
            "bid": {"verbatim": 110252, "scale": 5},
            "ask": {"verbatim": 110262, "scale": 5},
        },
    )


def _resources(tmp: Path, **extra: object) -> dict[str, object]:
    body: dict[str, object] = {
        "archive": str(tmp),
        "venue": "dukascopy-fx",
        "symbol": "EURUSD",
        "start": _START,
        "end": _END,
        "resolution": "tick",
        "side": "both",
        "world": World.REPLAY,
        "store": EvidenceStore(tmp),
        "writer": _writer(),
        "correlation_id": _CORR,
        "journal_instant": _END + 1,
        "ticks": _clean_ticks(),
    }
    body.update(extra)
    return body


def test_verify_identity_names_unarmed_edge_guard() -> None:
    identity = verify_identity()
    assert identity["integrity_kind"] == INTEGRITY_KIND
    assert "edge_tolerance_default" not in identity
    assert identity["edge_guard_requires_explicit_tolerance"] is True
    assert identity["fills_gaps"] is False
    assert identity["verdict_is_edge_claim"] is False
    assert identity["journals_ct13_data_quality"] is True
    front = data_front_identity()
    assert front["integrity_kind"] == INTEGRITY_KIND
    assert front["edge_guard_requires_explicit_tolerance"] is True


def test_blank_edge_tolerance_reports_raw_offsets_without_edge_fail() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Leading/trailing offsets present, but guard un-armed.
        ticks = (
            {
                "t_ns": _START + 5_000_000_000,
                "bid": {"verbatim": 1, "scale": 5},
                "ask": {"verbatim": 2, "scale": 5},
            },
            {
                "t_ns": _END - 5_000_000_000,
                "bid": {"verbatim": 3, "scale": 5},
                "ask": {"verbatim": 4, "scale": 5},
            },
        )
        verdict = _ok(verify(_resources(root, ticks=ticks)))
        assert verdict.verdict == "pass"
        assert verdict.edge_guard_armed is False
        assert verdict.edge_tolerance_ns is None
        assert verdict.edge_start_offset_ns == 5_000_000_000
        assert verdict.edge_end_offset_ns == 5_000_000_000
        assert verdict.is_edge_claim is False
        assert verdict.as_mapping()["fills_gaps"] is False
        assert verdict.defects == ()


def test_armed_edge_tolerance_refuses_beyond_threshold() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ticks = (
            {
                "t_ns": _START + 10_000_000_000,
                "bid": {"verbatim": 1, "scale": 5},
                "ask": {"verbatim": 2, "scale": 5},
            },
        )
        refused = verify(
            _resources(
                root, ticks=ticks, edge_tolerance_ns=1_000_000_000, correlation_id="edge-fail"
            )
        )
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["signal"] == "window-integrity-defect"
        result = cast("dict[str, object]", refused.context["result"])
        defects = cast("tuple[object, ...]", result["defects"])
        codes = {cast("dict[str, object]", item)["code"] for item in defects}
        assert "edge_offset_beyond_tolerance" in codes


def test_missing_side_when_both_requested_is_ct04() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ticks = (
            {"t_ns": _START + 1, "bid": {"verbatim": 1, "scale": 5}},
            {"t_ns": _START + 2, "bid": {"verbatim": 2, "scale": 5}},
        )
        refused = verify(_resources(root, ticks=ticks, correlation_id="missing-ask"))
        assert is_refusal(refused)
        result = cast("dict[str, object]", refused.context["result"])
        defects = cast("tuple[object, ...]", result["defects"])
        codes = {cast("dict[str, object]", item)["code"] for item in defects}
        assert "missing_requested_side" in codes


def test_float_price_taint_is_ct04() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ticks = ({"t_ns": _START + 1, "bid": 1.2345, "ask": {"verbatim": 2, "scale": 5}},)
        refused = verify(_resources(root, ticks=ticks, correlation_id="float-taint"))
        assert is_refusal(refused)
        result = cast("dict[str, object]", refused.context["result"])
        defects = cast("tuple[object, ...]", result["defects"])
        codes = {cast("dict[str, object]", item)["code"] for item in defects}
        assert "non_integer_price_taint" in codes


def test_empty_provider_return_is_ct04() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        refused = verify(_resources(root, ticks=(), correlation_id="empty"))
        assert is_refusal(refused)
        result = cast("dict[str, object]", refused.context["result"])
        defects = cast("tuple[object, ...]", result["defects"])
        codes = {cast("dict[str, object]", item)["code"] for item in defects}
        assert "empty_provider_return" in codes


def test_interior_gaps_reported_never_filled() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ticks = (
            {
                "t_ns": _START + 1_000_000_000,
                "bid": {"verbatim": 1, "scale": 5},
                "ask": {"verbatim": 2, "scale": 5},
            },
            {
                "t_ns": _START + 10_000_000_000,
                "bid": {"verbatim": 3, "scale": 5},
                "ask": {"verbatim": 4, "scale": 5},
            },
        )
        verdict = _ok(
            verify(
                _resources(root, ticks=ticks, expected_step_ns=2_000_000_000, correlation_id="gaps")
            )
        )
        assert verdict.verdict == "pass"
        assert len(verdict.interior_gaps) == 1
        gap = verdict.interior_gaps[0]
        assert gap.delta_ns == 9_000_000_000
        assert gap.as_mapping()["filled"] is False
        mapping = verdict.as_mapping()
        assert mapping["fills_gaps"] is False


def test_non_monotonic_timestamps_refuse() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ticks = (
            {
                "t_ns": _START + 3_000_000,
                "bid": {"verbatim": 1, "scale": 5},
                "ask": {"verbatim": 2, "scale": 5},
            },
            {
                "t_ns": _START + 1_000_000,
                "bid": {"verbatim": 3, "scale": 5},
                "ask": {"verbatim": 4, "scale": 5},
            },
        )
        refused = verify(_resources(root, ticks=ticks, correlation_id="mono"))
        assert is_refusal(refused)
        result = cast("dict[str, object]", refused.context["result"])
        defects = cast("tuple[object, ...]", result["defects"])
        codes = {cast("dict[str, object]", item)["code"] for item in defects}
        assert "non_monotonic_timestamp" in codes


def test_pass_journals_ct13_with_propagated_correlation_id() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = _resources(root)
        verdict = _ok(verify(resources))
        assert verdict.verdict == "pass"
        assert verdict.journaled is True
        assert verdict.correlation_id == _CORR
        store = cast("EvidenceStore", resources["store"])
        world = _ok(store.for_world(World.REPLAY))
        events = _ok(JournalReader(world.journal).read("dq", for_world=World.REPLAY))
        assert len(events) == 1
        event = events[0]
        assert event.correlation_id == _CORR
        assert event.payload["signal"] == "window-integrity"
        assert event.payload["verdict"] == "pass"
        assert event.payload["is_edge_claim"] is False


def test_same_window_same_config_reproduces_verdict() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        first = _ok(verify(_resources(root, correlation_id="run-a")))
        second = _ok(verify(_resources(root, correlation_id="run-b")))
        assert first.verdict == second.verdict == "pass"
        assert first.counts.as_mapping() == second.counts.as_mapping()
        assert first.edge_start_offset_ns == second.edge_start_offset_ns
        assert first.edge_end_offset_ns == second.edge_end_offset_ns
        assert first.defects == second.defects
        assert first.is_edge_claim is False
        assert second.is_edge_claim is False


def test_parse_verify_request_rejects_float_tolerance() -> None:
    parsed = parse_verify_request(
        {
            "archive": "raw",
            "venue": "dukascopy-fx",
            "symbol": "EURUSD",
            "start": _START,
            "end": _END,
            "edge_tolerance_ns": 1.5,
        }
    )
    assert is_refusal(parsed)
    assert parsed.category is RefusalCategory.INVALID_INPUT


def test_invoke_data_verify_through_door() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        payload = _ok(invoke_data("verify", _resources(root)))
        assert payload["command"] == "verify"
        assert payload["verdict"] == "pass"
        assert payload["integrity_kind"] == INTEGRITY_KIND


def test_cli_and_api_door_parity_for_verify() -> None:
    assert api.verify is verify
    assert api.verify_identity is verify_identity
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = _resources(root)
        library = _ok(verify(resources))
        via_api = _ok(api.verify(resources))
        assert library.as_mapping()["verdict"] == via_api.as_mapping()["verdict"]
        runner = CliRunner()
        clicked = runner.invoke(
            main,
            [
                "data",
                "verify",
                "--archive",
                str(root),
                "--venue",
                "dukascopy-fx",
                "--symbol",
                "EURUSD",
                "--start",
                str(_START),
                "--end",
                str(_END),
                "--side",
                "both",
                "--correlation-id",
                "cli-verify",
            ],
            obj={
                "store": resources["store"],
                "writer": resources["writer"],
                "ticks": _clean_ticks(),
            },
        )
        assert clicked.exit_code == 0, clicked.output
        assert '"verdict": "pass"' in clicked.output
        assert '"is_edge_claim": false' in clicked.output
