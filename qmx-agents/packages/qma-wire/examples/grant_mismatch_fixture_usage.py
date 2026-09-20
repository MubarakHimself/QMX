"""Reference usage — grant refuses the wrong instance or config (Story 59.5)."""

from __future__ import annotations

from qma.core.refusals import GrantMismatch, GrantWidenRefused
from qma.wire import (
    GRANT_MISMATCH_FIXTURE_OWNER,
    GRANT_MISMATCH_GAP_0100,
    GRANT_MISMATCH_MUTMUT_IS_PROOF,
    GRANT_MISMATCH_NEW_CT_MINTED,
    GRANT_MISMATCH_SILENT_RETARGET,
    INVOCATION_ENVELOPE_IS_AUTHORITY,
    GrantMismatchFixture,
    grant_mismatch_fixture_identity,
    refuse_gap_0100_readiness_dashboard,
    refuse_silent_grant_retarget,
)
from qmf.core import is_ok, is_refusal


def main() -> None:
    assert GRANT_MISMATCH_FIXTURE_OWNER == "COMP-QMA-WIRE"
    assert GRANT_MISMATCH_GAP_0100 is False
    assert GRANT_MISMATCH_MUTMUT_IS_PROOF is False
    assert GRANT_MISMATCH_NEW_CT_MINTED is False
    assert GRANT_MISMATCH_SILENT_RETARGET is False
    assert INVOCATION_ENVELOPE_IS_AUTHORITY is False
    schema = grant_mismatch_fixture_identity()
    assert schema["grant_mismatch_gap_0100"] is False
    chrome = refuse_gap_0100_readiness_dashboard()
    assert is_refusal(chrome)
    print("GAP-0100 chrome is refused; mutmut is not architecture proof")

    fixture = GrantMismatchFixture()
    executed: list[object] = []
    bound = fixture.dispatch_matching(execute=executed.append)
    assert is_ok(bound)
    assert bound.value.grant.instance_id == "inst:1"
    assert bound.value.grant.config_revision == 4
    assert len(executed) == 1
    print("matching instance and config dispatch")

    executed.clear()
    wrong_instance = fixture.dispatch_wrong_instance(execute=executed.append)
    assert is_refusal(wrong_instance)
    assert isinstance(wrong_instance, GrantMismatch)
    assert wrong_instance.context["field"] == "instance_id"
    assert wrong_instance.context["retargeted"] is False
    assert executed == []
    print("wrong instance is GRANT_MISMATCH before execution")

    executed.clear()
    wrong_config = fixture.dispatch_wrong_config(execute=executed.append)
    assert is_refusal(wrong_config)
    assert isinstance(wrong_config, GrantMismatch)
    assert wrong_config.context["field"] == "config_revision"
    assert executed == []
    print("wrong config revision is GRANT_MISMATCH before execution")

    retarget = fixture.retarget_grant(instance_id="inst:2")
    assert isinstance(retarget, GrantWidenRefused)
    named = refuse_silent_grant_retarget(grant_id="grant:1")
    assert isinstance(named, GrantMismatch)
    print("a valid grant cannot be pointed at another instance")


if __name__ == "__main__":
    main()
