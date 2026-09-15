"""Story 45.6 / 38.2 — daemon-resolved evidence handles and candidates (FR-Q53)."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import cast

import pytest
from qma.core.content import content_address
from qma.core.plugins import PluginContext
from qma.core.ports.experiments import GAP_0085_STRATEGY_MECHANISMS
from qma.core.ports.handles import (
    MONEY_PATH_FIELD_DIFF_SCHEMA,
    STRATEGY_HANDLE_LINEAGE_EDGE_TYPE,
    EvidenceHandle,
)
from qma.core.vocabulary.enums import HandleKind, MessageKind
from qma.core.vocabulary.handles import (
    QMA_OWNED_CANDIDATE_ORIGIN,
    STRATEGY_CANDIDATE_ZONE,
)
from qma.daemon.handles import EvidenceHandleService
from qma.daemon.plugins import DaemonPluginContext, PluginContextError
from qma.daemon.tools import DEV_ZONE
from qmf.core import is_ok, is_refusal
from qmf.registry import EdgeType

KINDS = (
    HandleKind.EXPERIMENT_HANDLE,
    HandleKind.TRADE_LOG_HANDLE,
    HandleKind.KNOWLEDGE_HANDLE,
    HandleKind.MARKET_DATA_HANDLE,
    HandleKind.BACKTEST_HANDLE,
    HandleKind.STRATEGY_HANDLE,
)


def _mint_all(service: EvidenceHandleService) -> None:
    for kind in KINDS:
        minted = service.mint(
            kind=kind,
            handle_id=f"h:{kind.value}",
            evidence_ref=f"fp1:sha256:{kind.value}",
        )
        assert is_ok(minted)


def _qml_record_fp(tag: str) -> str:
    addressed = content_address({"qml_host_minted": tag})
    assert is_ok(addressed)
    return addressed.value.value


def test_daemon_resolves_only_closed_kinds() -> None:
    service = EvidenceHandleService()
    _mint_all(service)
    for kind in KINDS:
        resolved = service.resolve(f"h:{kind.value}")
        assert is_ok(resolved)
        assert resolved.value.kind is kind
        assert resolved.value.contents is None
    invented = service.mint(
        kind="OrderHandle",
        handle_id="h:order",
        evidence_ref="fp1:sha256:order",
    )
    assert is_refusal(invented)
    plugin = service.register_plugin_handle_kind("BookHandle")
    assert is_refusal(plugin)
    assert plugin.context["field"] == "handle_kind"


def test_plugin_context_cannot_register_handle_kind() -> None:
    ctx = DaemonPluginContext("analysis-backtest")
    assert isinstance(ctx, PluginContext)
    assert not hasattr(PluginContext, "register_handle_kind")
    with pytest.raises(PluginContextError, match="closed qma-core vocabulary"):
        ctx.register_handle_kind("OrderHandle")


def test_context_window_holds_references_not_contents() -> None:
    service = EvidenceHandleService()
    _mint_all(service)
    compiled = service.compile_context()
    assert is_ok(compiled)
    window = compiled.value
    assert window["contents_in_context"] is False
    handles_raw = window["handles"]
    assert isinstance(handles_raw, list)
    entries = cast("list[dict[str, object]]", handles_raw)
    assert len(entries) == 6
    for entry in entries:
        assert entry["contents"] is None
        assert entry["contents_in_context"] is False
        assert "body" not in entry


def test_no_handle_for_open_money_path_records() -> None:
    service = EvidenceHandleService()
    for target in (
        "open_order",
        "open_position",
        "binding",
        "Book",
        "seat",
        "bms",
        "control_action",
        "kill_switch",
        "venue_session",
    ):
        refused = service.mint(
            kind="TradeLogHandle",
            handle_id=f"h:{target}",
            evidence_ref="fp1:sha256:x",
            target=target,
        )
        assert is_refusal(refused)


def test_trade_log_and_market_data_are_recorded_closed_read_only() -> None:
    service = EvidenceHandleService()
    for kind in (HandleKind.TRADE_LOG_HANDLE, HandleKind.MARKET_DATA_HANDLE):
        ok = service.mint(
            kind=kind,
            handle_id=f"h:{kind.value}",
            evidence_ref="fp1:sha256:closed",
        )
        assert is_ok(ok)
        assert ok.value.recorded is True
        assert ok.value.closed is True
        assert ok.value.read_only is True
        live = service.mint(
            kind=kind,
            handle_id=f"h:{kind.value}:live",
            evidence_ref="fp1:sha256:live",
            live=True,
        )
        assert is_refusal(live)
        opened = service.mint(
            kind=kind,
            handle_id=f"h:{kind.value}:open",
            evidence_ref="fp1:sha256:open",
            closed=False,
        )
        assert is_refusal(opened)


def test_strategy_handle_writes_dev_zone_candidate_with_origin_and_lineage() -> None:
    service = EvidenceHandleService()
    minted = service.mint(
        kind=HandleKind.STRATEGY_HANDLE,
        handle_id="h:strategy",
        evidence_ref="fp1:sha256:strategy",
    )
    assert is_ok(minted)
    first = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={"note": "v1", "window": "H1"},
    )
    assert is_ok(first)
    assert first.value.origin == QMA_OWNED_CANDIDATE_ORIGIN
    assert first.value.zone == STRATEGY_CANDIDATE_ZONE == DEV_ZONE
    assert first.value.lineage_predecessor is None
    assert first.value.money_path_relevant is False
    successor = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={"note": "v2", "window": "H1"},
        ancestor={"note": "v1", "window": "H1"},
        lineage_predecessor=first.value.payload_fp1,
    )
    assert is_ok(successor)
    assert successor.value.lineage_predecessor == first.value.payload_fp1
    live = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={"note": "live"},
        zone="live",
    )
    assert is_refusal(live)
    assert live.context["field"] == "zone_transition"
    experiment = service.mint(
        kind=HandleKind.EXPERIMENT_HANDLE,
        handle_id="h:exp",
        evidence_ref="fp1:sha256:exp",
    )
    assert is_ok(experiment)
    refused_kind = service.create_strategy_candidate(
        handle_id="h:exp",
        proposed={"note": "nope"},
    )
    assert is_refusal(refused_kind)


def test_money_path_relevant_requires_exact_named_schema_diff() -> None:
    service = EvidenceHandleService()
    assert is_ok(
        service.mint(
            kind=HandleKind.STRATEGY_HANDLE,
            handle_id="h:strategy",
            evidence_ref="fp1:sha256:strategy",
        )
    )
    ancestor = {"sizing": "1R", "note": "keep"}
    proposed = {"sizing": "2R", "note": "keep"}
    candidate = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed=proposed,
        ancestor=ancestor,
    )
    assert is_ok(candidate)
    assert candidate.value.money_path_relevant is True
    assert candidate.value.touched_fields == ("sizing",)
    missing = service.emit_approval_request(candidate_ref=candidate.value.payload_fp1)
    assert is_refusal(missing)
    wrong_fields = service.emit_approval_request(
        candidate_ref=candidate.value.payload_fp1,
        field_diff={
            "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": candidate.value.payload_fp1,
            "predecessor_ref": candidate.value.lineage_predecessor,
            "fields": [
                {"path": "sizing", "ancestor": "1R", "proposed": "2R"},
                {"path": "risk", "ancestor": "x", "proposed": "y"},
            ],
        },
    )
    assert is_refusal(wrong_fields)
    ok = service.emit_approval_request(
        candidate_ref=candidate.value.payload_fp1,
        field_diff={
            "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": candidate.value.payload_fp1,
            "predecessor_ref": candidate.value.lineage_predecessor,
            "fields": [{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
        },
    )
    assert is_ok(ok)
    assert ok.value.kind == MessageKind.APPROVAL_REQUEST.value
    assert ok.value.schema == MONEY_PATH_FIELD_DIFF_SCHEMA


def test_unset_money_path_field_is_never_filled() -> None:
    service = EvidenceHandleService()
    assert is_ok(
        service.mint(
            kind=HandleKind.STRATEGY_HANDLE,
            handle_id="h:strategy",
            evidence_ref="fp1:sha256:strategy",
        )
    )
    filled = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={"sizing": "1R", "note": "new"},
        ancestor={"note": "old"},
    )
    assert is_refusal(filled)
    assert filled.context["field"] == "money_path_field"
    first = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={"risk": "fresh"},
    )
    assert is_refusal(first)


def test_no_promotion_or_zone_transition_command() -> None:
    service = EvidenceHandleService()
    assert service.minted_promotion_command is None
    assert is_ok(
        service.mint(
            kind=HandleKind.STRATEGY_HANDLE,
            handle_id="h:strategy",
            evidence_ref="fp1:sha256:strategy",
        )
    )
    written = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={"note": "candidate"},
    )
    assert is_ok(written)
    promoted = service.promote(written.value.payload_fp1)
    assert is_refusal(promoted)
    assert promoted.context["field"] == "zone_transition"
    zone = service.transition_zone(zone="live")
    assert is_refusal(zone)
    stored_body = service.candidate_body(written.value.payload_fp1)
    assert stored_body is not None
    compiled = service.compile_context(("h:strategy",))
    assert is_ok(compiled)
    dumped = str(compiled.value)
    assert compiled.value["contents_in_context"] is False
    note = stored_body["note"]
    assert isinstance(note, str)
    assert note not in dumped


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "evidence_handle_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()


def test_handle_payload_round_trip() -> None:
    minted = EvidenceHandle.try_create(
        kind="KnowledgeHandle",
        handle_id="h:know",
        evidence_ref="corpus:snap:1",
    )
    assert is_ok(minted)
    restored = EvidenceHandle.from_payload(minted.value.to_payload())
    assert is_ok(restored)
    assert restored.value.handle_id == "h:know"
    assert restored.value.contents is None


def test_strategy_handle_registers_fingerprinted_bytes_with_origin_and_ct07() -> None:
    service = EvidenceHandleService()
    record_fp1 = _qml_record_fp("bot-v1")
    referenced = service.reference_registry_record(
        handle_id="h:strategy",
        record_fp1=record_fp1,
    )
    assert is_ok(referenced)
    assert referenced.value.evidence_ref == record_fp1
    candidate = service.register_fingerprinted_record(
        handle_id="h:strategy",
        record_fp1=record_fp1,
    )
    assert is_ok(candidate)
    assert candidate.value.origin == QMA_OWNED_CANDIDATE_ORIGIN
    assert candidate.value.zone == STRATEGY_CANDIDATE_ZONE
    assert candidate.value.record_fp1 == record_fp1
    assert candidate.value.lineage_predecessor == record_fp1
    edge = service.candidate_lineage_edge(candidate.value.payload_fp1)
    assert edge is not None
    assert edge.edge_type is EdgeType.BRANCHES_FROM
    assert edge.edge_type.value == STRATEGY_HANDLE_LINEAGE_EDGE_TYPE
    assert edge.to_ref.value == record_fp1
    assert edge.from_ref.value == candidate.value.payload_fp1


def test_strategy_handle_never_assembles_ct33_or_fills_random_condition() -> None:
    service = EvidenceHandleService()
    assert is_ok(
        service.mint(
            kind=HandleKind.STRATEGY_HANDLE,
            handle_id="h:strategy",
            evidence_ref=_qml_record_fp("bot"),
        )
    )
    assembled = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={
            "kind": "bot-definition",
            "strategy_family_id": "trend",
            "confluence_set": [_qml_record_fp("confluence")],
        },
    )
    assert is_refusal(assembled)
    assert assembled.context["field"] == "assembly"
    confluence = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={"kind": "confluence", "legs": [{"role": "trigger"}]},
    )
    assert is_refusal(confluence)
    assert confluence.context["field"] == "assembly"
    slots = service.register_fingerprinted_record(
        handle_id="h:strategy",
        record_fp1=_qml_record_fp("bot-v2"),
        proposed={"RandomCondition": {"min": 1, "max": 3}},
    )
    assert is_refusal(slots)
    assert slots.context["field"] == "random_condition"
    assembled_ref = service.reference_registry_record(
        handle_id="h:assembled",
        record_fp1={"kind": "bot-definition", "strategy_family_id": "trend"},
    )
    assert is_refusal(assembled_ref)


def test_gap_0085_strategy_mechanisms_still_refused_on_strategy_handle() -> None:
    service = EvidenceHandleService()
    assert is_ok(
        service.mint(
            kind=HandleKind.STRATEGY_HANDLE,
            handle_id="h:strategy",
            evidence_ref=_qml_record_fp("bot"),
        )
    )
    assert "entry_mechanism" in GAP_0085_STRATEGY_MECHANISMS
    refused = service.create_strategy_candidate(
        handle_id="h:strategy",
        proposed={"EntryMechanism": {"kind": "breakout"}, "note": "nope"},
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "mechanisms"


def test_register_fingerprinted_record_keeps_money_path_field_diff() -> None:
    service = EvidenceHandleService()
    record_fp1 = _qml_record_fp("bot-money")
    assert is_ok(service.reference_registry_record(handle_id="h:strategy", record_fp1=record_fp1))
    filled = service.register_fingerprinted_record(
        handle_id="h:strategy",
        record_fp1=record_fp1,
        proposed={"sizing": "1R", "note": "new"},
        ancestor={"note": "old"},
    )
    assert is_refusal(filled)
    assert filled.context["field"] == "money_path_field"
    candidate = service.register_fingerprinted_record(
        handle_id="h:strategy",
        record_fp1=record_fp1,
        proposed={"sizing": "2R", "note": "keep"},
        ancestor={"sizing": "1R", "note": "keep"},
    )
    assert is_ok(candidate)
    assert candidate.value.money_path_relevant is True
    assert candidate.value.touched_fields == ("sizing",)
    missing = service.emit_approval_request(candidate_ref=candidate.value.payload_fp1)
    assert is_refusal(missing)
    approved = service.emit_approval_request(
        candidate_ref=candidate.value.payload_fp1,
        field_diff={
            "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": candidate.value.payload_fp1,
            "predecessor_ref": candidate.value.lineage_predecessor,
            "fields": [{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
        },
    )
    assert is_ok(approved)
    assert approved.value.schema == MONEY_PATH_FIELD_DIFF_SCHEMA
