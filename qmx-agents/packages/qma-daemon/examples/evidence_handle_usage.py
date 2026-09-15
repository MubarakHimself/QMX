"""L27 reference usage: daemon-resolved evidence handles (Story 45.6 / 38.2)."""

from __future__ import annotations

from qma.core.content import content_address
from qma.core.ports.handles import MONEY_PATH_FIELD_DIFF_SCHEMA
from qma.core.vocabulary.enums import HandleKind, MessageKind
from qma.daemon.handles import EvidenceHandleService
from qmf.core import is_ok, is_refusal
from qmf.registry import EdgeType


def main() -> None:
    service = EvidenceHandleService()
    for kind in HandleKind:
        minted = service.mint(
            kind=kind,
            handle_id=f"h:{kind.value}",
            evidence_ref=f"fp1:sha256:{kind.value}",
        )
        assert is_ok(minted)
        assert minted.value.contents is None
    assert is_refusal(
        service.mint(
            kind="OrderHandle",
            handle_id="h:order",
            evidence_ref="fp1:sha256:order",
        )
    )
    compiled = service.compile_context()
    assert is_ok(compiled)
    assert compiled.value["contents_in_context"] is False

    first = service.create_strategy_candidate(
        handle_id="h:StrategyHandle",
        proposed={"note": "v1", "window": "H1"},
    )
    assert is_ok(first)
    successor = service.create_strategy_candidate(
        handle_id="h:StrategyHandle",
        proposed={"note": "v2", "window": "H1"},
        ancestor={"note": "v1", "window": "H1"},
        lineage_predecessor=first.value.payload_fp1,
    )
    assert is_ok(successor)
    assert successor.value.money_path_relevant is False
    money = service.create_strategy_candidate(
        handle_id="h:StrategyHandle",
        proposed={"note": "v1", "window": "H1", "sizing": "2R"},
        ancestor={"note": "v1", "window": "H1", "sizing": "1R"},
    )
    assert is_ok(money)
    assert money.value.money_path_relevant is True
    approved = service.emit_approval_request(
        candidate_ref=money.value.payload_fp1,
        field_diff={
            "schema": MONEY_PATH_FIELD_DIFF_SCHEMA,
            "candidate_ref": money.value.payload_fp1,
            "predecessor_ref": money.value.lineage_predecessor,
            "fields": [{"path": "sizing", "ancestor": "1R", "proposed": "2R"}],
        },
    )
    assert is_ok(approved)
    assert approved.value.kind == MessageKind.APPROVAL_REQUEST.value
    assert is_refusal(service.promote(money.value.payload_fp1))
    assert is_refusal(service.transition_zone(zone="live"))
    assert service.minted_promotion_command is None

    addressed = content_address({"qml_host_minted": "bot-v1"})
    assert is_ok(addressed)
    record_fp1 = addressed.value.value
    referenced = service.reference_registry_record(
        handle_id="h:StrategyHandle:ref",
        record_fp1=record_fp1,
    )
    assert is_ok(referenced)
    registered = service.register_fingerprinted_record(
        handle_id="h:StrategyHandle:ref",
        record_fp1=record_fp1,
    )
    assert is_ok(registered)
    assert registered.value.record_fp1 == record_fp1
    edge = service.candidate_lineage_edge(registered.value.payload_fp1)
    assert edge is not None
    assert edge.edge_type is EdgeType.BRANCHES_FROM
    assert is_refusal(
        service.create_strategy_candidate(
            handle_id="h:StrategyHandle",
            proposed={"kind": "bot-definition", "strategy_family_id": "trend"},
        )
    )
    assert is_refusal(
        service.create_strategy_candidate(
            handle_id="h:StrategyHandle",
            proposed={"EntryMechanism": {"kind": "breakout"}},
        )
    )
    assert is_refusal(
        service.register_fingerprinted_record(
            handle_id="h:StrategyHandle:ref",
            record_fp1=record_fp1,
            proposed={"RandomCondition": {"min": 1, "max": 5}},
        )
    )


if __name__ == "__main__":
    main()
