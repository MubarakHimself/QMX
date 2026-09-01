"""L27 reference usage: daemon-resolved evidence handles (Story 45.6)."""

from __future__ import annotations

from qma.core.ports.handles import MONEY_PATH_FIELD_DIFF_SCHEMA
from qma.core.vocabulary.enums import HandleKind, MessageKind
from qma.daemon.handles import EvidenceHandleService
from qmf.core import is_ok, is_refusal


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


if __name__ == "__main__":
    main()
