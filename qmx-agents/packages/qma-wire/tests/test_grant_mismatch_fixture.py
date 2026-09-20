"""Story 59.5 — grant refuses the wrong instance or config revision."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path
from typing import cast

from qma.core.refusals import GrantMismatch, GrantWidenRefused
from qma.wire import (
    GRANT_MISMATCH_FIXTURE_OWNER,
    GRANT_MISMATCH_GAP,
    GRANT_MISMATCH_GAP_0100,
    GRANT_MISMATCH_MUTMUT_IS_PROOF,
    GRANT_MISMATCH_NEW_CT_MINTED,
    GRANT_MISMATCH_SILENT_RETARGET,
    INVOCATION_ENVELOPE_IS_AUTHORITY,
    INVOCATION_ENVELOPE_NEW_CT_MINTED,
    PUBLIC_CALL_TRANSPORTS,
    GrantMismatchFixture,
    PublicCallTransport,
    grant_mismatch_fixture_identity,
    refuse_gap_0100_readiness_dashboard,
    refuse_silent_grant_retarget,
)
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import RefusalCategory, Result

_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "wire" / "grant_mismatch_fixture.py"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "grant_mismatch_fixture_usage.py"


def _ok[T](result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def test_matching_instance_and_config_still_dispatch() -> None:
    fixture = GrantMismatchFixture()
    executed: list[object] = []
    bound = _ok(fixture.dispatch_matching(execute=executed.append))
    assert bound.is_authority is False
    assert INVOCATION_ENVELOPE_IS_AUTHORITY is False
    assert bound.grant.instance_id == bound.instance.instance_id == "inst:1"
    assert bound.grant.config_revision == bound.instance.config_revision == 4
    assert bound.envelope.instance_id == "inst:1"
    assert bound.envelope.config_revision == 4
    assert len(executed) == 1


def test_wrong_instance_is_grant_mismatch_before_execution() -> None:
    fixture = GrantMismatchFixture()
    executed: list[object] = []
    for transport in (
        PublicCallTransport.IN_PROCESS,
        PublicCallTransport.CLI,
        PublicCallTransport.WIRE,
    ):
        executed.clear()
        refused = fixture.dispatch_wrong_instance(
            transport=transport,
            execute=executed.append,
        )
        assert is_refusal(refused), transport
        assert isinstance(refused, GrantMismatch)
        assert refused.context["code"] == "GRANT_MISMATCH"
        assert refused.context["field"] == "instance_id"
        assert refused.context["retargeted"] is False
        assert refused.context["substituted"] is False
        assert refused.context["envelope_is_authority"] is False
        assert executed == []
    assert "cli" in PUBLIC_CALL_TRANSPORTS


def test_wrong_config_revision_is_grant_mismatch_before_execution() -> None:
    fixture = GrantMismatchFixture()
    executed: list[object] = []
    refused = fixture.dispatch_wrong_config(
        transport=PublicCallTransport.CLI,
        execute=executed.append,
    )
    assert is_refusal(refused)
    assert isinstance(refused, GrantMismatch)
    assert refused.context["code"] == "GRANT_MISMATCH"
    assert refused.context["field"] == "config_revision"
    assert refused.context["bound"] == 5
    assert refused.context["granted"] == 4
    assert refused.context["retargeted"] is False is GRANT_MISMATCH_SILENT_RETARGET
    assert executed == []


def test_aliased_instance_record_does_not_silently_retarget() -> None:
    fixture = GrantMismatchFixture()
    executed: list[object] = []
    refused = fixture.dispatch_aliased_instance(execute=executed.append)
    assert is_refusal(refused)
    assert isinstance(refused, GrantMismatch)
    assert refused.context["code"] == "GRANT_MISMATCH"
    assert refused.context["field"] == "instance_id"
    assert refused.context["retargeted"] is False
    assert refused.context["substituted"] is False
    assert executed == []


def test_in_place_retarget_requires_regrant() -> None:
    fixture = GrantMismatchFixture()
    world = _ok(fixture.world())
    before = world.grant.canonical_bytes()
    assert is_ok(before)
    refused = world.ledger.apply_upgrade(
        world.grant.grant_id, instance_id="inst:2", config_revision=5
    )
    assert isinstance(refused, GrantWidenRefused)
    assert refused.context["requires_regrant"] is True
    also = fixture.retarget_grant(instance_id="inst:2")
    assert is_refusal(also)
    assert isinstance(also, GrantWidenRefused)
    after = world.ledger.grants[world.grant.grant_id].canonical_bytes()
    assert is_ok(after)
    assert after.value == before.value
    named = refuse_silent_grant_retarget(grant_id=world.grant.grant_id)
    assert isinstance(named, GrantMismatch)
    assert named.context["retargeted"] is False
    assert named.context["code"] == "GRANT_MISMATCH"


def test_gap_0100_chrome_and_mutmut_are_not_proof() -> None:
    schema = grant_mismatch_fixture_identity()
    assert schema["grant_mismatch_fixture_owner"] == GRANT_MISMATCH_FIXTURE_OWNER == "COMP-QMA-WIRE"
    assert schema["grant_mismatch_gap"] == GRANT_MISMATCH_GAP == "GAP-0100"
    assert schema["grant_mismatch_gap_0100"] is False is GRANT_MISMATCH_GAP_0100
    assert schema["grant_mismatch_mutmut_is_proof"] is False is GRANT_MISMATCH_MUTMUT_IS_PROOF
    assert schema["grant_mismatch_new_ct_minted"] is False is GRANT_MISMATCH_NEW_CT_MINTED
    assert schema["grant_mismatch_silent_retarget"] is False is GRANT_MISMATCH_SILENT_RETARGET
    assert INVOCATION_ENVELOPE_NEW_CT_MINTED is False
    chrome = refuse_gap_0100_readiness_dashboard()
    assert chrome.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert chrome.context["field"] == "readiness_dashboard"
    assert chrome.context["gap"] == "GAP-0100"
    assert chrome.context["mutmut_is_architecture_proof"] is False
    fixture = GrantMismatchFixture()
    assert fixture.owner == GRANT_MISMATCH_FIXTURE_OWNER
    assert fixture.gap_0100 is False
    assert fixture.mutmut_is_proof is False


def test_module_constants_and_no_new_ct() -> None:
    tree = ast.parse(_SRC.read_text(encoding="utf-8"))
    assigned: dict[str, object] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
            and isinstance(node.value, (ast.Constant, ast.Tuple, ast.List))
        ):
            assigned[node.target.id] = ast.literal_eval(node.value)
        elif (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, (ast.Constant, ast.Tuple, ast.List))
        ):
            assigned[node.targets[0].id] = ast.literal_eval(node.value)
    assert assigned.get("GRANT_MISMATCH_FIXTURE_OWNER") == "COMP-QMA-WIRE"
    assert assigned.get("GRANT_MISMATCH_GAP_0100") is False
    assert assigned.get("GRANT_MISMATCH_MUTMUT_IS_PROOF") is False
    assert assigned.get("GRANT_MISMATCH_NEW_CT_MINTED") is False
    assert assigned.get("GRANT_MISMATCH_SILENT_RETARGET") is False
    source = _SRC.read_text(encoding="utf-8")
    assert "CT-52" not in source
    assert "CREATE TABLE" not in source


def test_reference_usage_example_runs() -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    main = cast("object", namespace["main"])
    assert callable(main)
    main()
