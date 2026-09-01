"""Story 45.6 — closed evidence handle kinds (FR-Q53; CT-47)."""

from __future__ import annotations

import pytest
from qma.core.plugins import ManifestError, parse_plugin_manifest
from qma.core.ports.cardinality import PortError, validate_contribution_point
from qma.core.ports.handles import (
    MONEY_PATH_FIELD_DIFF_SCHEMA,
    EvidenceHandle,
    FieldLevelDiff,
    StrategyCandidate,
    context_entries_for_handles,
    parse_evidence_handle,
    refuse_plugin_handle_kind_extension,
    touched_money_path_fields,
    unset_money_path_fills,
)
from qma.core.vocabulary.enums import HandleKind
from qma.core.vocabulary.handles import (
    CLOSED_HANDLE_KINDS,
    FORBIDDEN_LIVE_MONEY_PATH_HANDLE_TARGETS,
    MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS,
    MONEY_PATH_RELEVANT_FIELDS,
    QMA_OWNED_CANDIDATE_ORIGIN,
    READ_ONLY_EVIDENCE_HANDLE_KINDS,
    STRATEGY_CANDIDATE_ZONE,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import is_ok, is_refusal


def test_closed_handle_kinds_are_exactly_the_six() -> None:
    assert {member.value for member in HandleKind} == {
        "BacktestHandle",
        "ExperimentHandle",
        "TradeLogHandle",
        "StrategyHandle",
        "KnowledgeHandle",
        "MarketDataHandle",
    }
    assert frozenset(HandleKind) == CLOSED_HANDLE_KINDS
    assert frozenset() == MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS
    with pytest.raises(VocabularyError):
        parse_closed(HandleKind, "OrderHandle")
    with pytest.raises(VocabularyError):
        parse_closed(HandleKind, "PositionHandle")
    with pytest.raises(VocabularyError):
        parse_closed(HandleKind, "BookHandle")


def test_plugin_cannot_extend_handle_kind_vocabulary() -> None:
    refused = refuse_plugin_handle_kind_extension("OrderHandle")
    assert is_refusal(refused)
    assert refused.context["field"] == "handle_kind"
    with pytest.raises(PortError, match="closed handle-kind vocabulary"):
        validate_contribution_point("handle_kind")
    with pytest.raises(ManifestError, match="closed qma-core vocabulary"):
        parse_plugin_manifest(
            {
                "id": "analysis-backtest",
                "version": "0.1.0",
                "qma_api": ">=0.1.0,<1.0.0",
                "desk": "analysis",
                "entrypoint": "analysis_backtest.activate",
                "contributions": [{"point": "handle_kind", "local_id": "OrderHandle"}],
            }
        )


def test_minted_handle_is_reference_without_contents() -> None:
    for kind in HandleKind:
        minted = EvidenceHandle.try_create(
            kind=kind,
            handle_id=f"h:{kind.value}:1",
            evidence_ref="fp1:sha256:abc",
        )
        assert is_ok(minted)
        handle = minted.value
        assert handle.kind is kind
        assert handle.contents is None
        assert handle.contents_in_context is False
        assert handle.writable is False
        assert handle.live is False
        entry = handle.context_entry()
        assert entry["contents"] is None
        assert entry["contents_in_context"] is False
        assert "body" not in entry
        stuffed = EvidenceHandle.try_create(
            kind=kind,
            handle_id=f"h:{kind.value}:stuffed",
            evidence_ref="fp1:sha256:abc",
            contents={"secret": "do-not-prompt"},
        )
        assert is_refusal(stuffed)
        assert stuffed.context["field"] == "contents"


def test_live_money_path_targets_are_not_minted() -> None:
    for target in FORBIDDEN_LIVE_MONEY_PATH_HANDLE_TARGETS:
        refused = parse_evidence_handle(
            kind="TradeLogHandle",
            handle_id="h:bad",
            evidence_ref="fp1:sha256:abc",
            target=target,
        )
        assert is_refusal(refused)
        assert refused.context["field"] == "target"
    live = EvidenceHandle.try_create(
        kind="MarketDataHandle",
        handle_id="h:live",
        evidence_ref="fp1:sha256:abc",
        live=True,
    )
    assert is_refusal(live)
    writable = EvidenceHandle.try_create(
        kind="ExperimentHandle",
        handle_id="h:write",
        evidence_ref="fp1:sha256:abc",
        writable=True,
    )
    assert is_refusal(writable)


def test_trade_log_and_market_data_are_recorded_closed_read_only() -> None:
    assert {
        HandleKind.TRADE_LOG_HANDLE,
        HandleKind.MARKET_DATA_HANDLE,
    } == READ_ONLY_EVIDENCE_HANDLE_KINDS
    for kind in READ_ONLY_EVIDENCE_HANDLE_KINDS:
        ok = EvidenceHandle.try_create(
            kind=kind,
            handle_id=f"h:{kind.value}",
            evidence_ref="fp1:sha256:closed",
            recorded=True,
            closed=True,
            read_only=True,
        )
        assert is_ok(ok)
        open_log = EvidenceHandle.try_create(
            kind=kind,
            handle_id=f"h:{kind.value}:open",
            evidence_ref="fp1:sha256:open",
            closed=False,
        )
        assert is_refusal(open_log)
        assert open_log.context["field"] == "evidence_state"


def test_context_entries_never_include_handle_contents() -> None:
    handles: list[EvidenceHandle] = []
    for kind in HandleKind:
        minted = EvidenceHandle.try_create(
            kind=kind,
            handle_id=f"h:{kind.value}",
            evidence_ref=f"ref:{kind.value}",
        )
        assert is_ok(minted)
        handles.append(minted.value)
    entries = context_entries_for_handles(handles)
    assert len(entries) == 6
    for entry in entries:
        assert entry["contents"] is None
        assert entry["contents_in_context"] is False


def test_strategy_candidate_is_dev_zone_with_qma_origin() -> None:
    first = StrategyCandidate.try_create(
        origin=QMA_OWNED_CANDIDATE_ORIGIN,
        zone=STRATEGY_CANDIDATE_ZONE,
        payload_fp1="fp1:sha256:aaa",
        stable_id="fp1:sha256:aaa",
        handle_id="h:strategy:1",
        money_path_relevant=False,
    )
    assert is_ok(first)
    assert first.value.lineage_predecessor is None
    successor = StrategyCandidate.try_create(
        origin="qma",
        zone="dev",
        payload_fp1="fp1:sha256:bbb",
        stable_id="fp1:sha256:bbb",
        handle_id="h:strategy:1",
        money_path_relevant=False,
        lineage_predecessor="fp1:sha256:aaa",
    )
    assert is_ok(successor)
    live = StrategyCandidate.try_create(
        origin="qma",
        zone="live",
        payload_fp1="fp1:sha256:ccc",
        stable_id="fp1:sha256:ccc",
        handle_id="h:strategy:1",
        money_path_relevant=False,
    )
    assert is_refusal(live)
    foreign = StrategyCandidate.try_create(
        origin="plugin-x",
        zone="dev",
        payload_fp1="fp1:sha256:ddd",
        stable_id="fp1:sha256:ddd",
        handle_id="h:strategy:1",
        money_path_relevant=False,
    )
    assert is_refusal(foreign)


def test_money_path_relevant_diff_requires_named_schema_and_set_ancestor() -> None:
    ancestor = {"sizing": "1R", "note": "keep"}
    proposed = {"sizing": "2R", "note": "keep"}
    assert touched_money_path_fields(ancestor, proposed) == ("sizing",)
    assert unset_money_path_fills(ancestor, proposed) == ()
    assert unset_money_path_fills(ancestor, {"risk": "0.5"}) == ("risk",)
    assert {
        "risk",
        "sizing",
        "exit",
        "protection",
        "binding",
        "priority",
    } == MONEY_PATH_RELEVANT_FIELDS
    diff = FieldLevelDiff.try_create(
        schema=MONEY_PATH_FIELD_DIFF_SCHEMA,
        candidate_ref="fp1:sha256:bbb",
        predecessor_ref="fp1:sha256:aaa",
        fields=[{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
    )
    assert is_ok(diff)
    missing_schema = FieldLevelDiff.try_create(
        schema="invented.schema",
        candidate_ref="fp1:sha256:bbb",
        predecessor_ref="fp1:sha256:aaa",
        fields=[{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
    )
    assert is_refusal(missing_schema)
    unset = FieldLevelDiff.try_create(
        schema=MONEY_PATH_FIELD_DIFF_SCHEMA,
        candidate_ref="fp1:sha256:bbb",
        predecessor_ref="fp1:sha256:aaa",
        fields=[{"path": "risk", "ancestor": None, "proposed": "new"}],
    )
    assert is_refusal(unset)
    assert unset.context["field"] == "ancestor"
