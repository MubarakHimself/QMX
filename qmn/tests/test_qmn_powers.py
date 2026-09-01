"""Story 25.7 — human-only signers at the SO_PEERCRED powers transport (QMX-F045)."""

from __future__ import annotations

import ast
import importlib.util
import struct
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.doors.http import powers as powers_mod
from qmn.doors.http.powers import (
    AGENT_SIGNER_PREFIXES,
    CLOSED_POWERS,
    OPERATOR_ONLY_POWERS,
    OPERATOR_PRINCIPAL,
    OPS_ALLOWED_POWERS,
    OPS_PRINCIPAL,
    POWERS_SOCKET_MODE,
    POWERS_SOCKET_OWNER,
    POWERS_SOCKET_PATH,
    POWERS_TRANSPORT_SURFACE,
    PRINCIPAL_SET,
    SERVICE_ACCOUNT_NAME,
    DeclaredPrincipals,
    PeerCredential,
    RecordingPowersJournal,
    authorize_powers_call,
    declare_principals,
    evaluate_unit_principals,
    is_human_signer,
    ops_power_allowed,
    peercred_option,
    powers_transport_identity,
    read_peercred,
    resolve_peer_principal,
)

from qmn import doors

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_DEPLOY = _QMN_ROOT / "deploy"

# Fixed fixture UIDs — none invented at runtime.
_OPERATOR_UID = 1001
_OPS_UID = 1002
_QMX_UID = 1000
_STRANGER_UID = 1999


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _principals() -> DeclaredPrincipals:
    return _ok(
        declare_principals(
            operator_uid=_OPERATOR_UID,
            ops_uid=_OPS_UID,
            service_account_uid=_QMX_UID,
        )
    )


def _peer(uid: int, *, pid: int = 42, gid: int = 100) -> PeerCredential:
    return PeerCredential(pid=pid, uid=uid, gid=gid)


def _load_deploy_boundary():
    path = _DEPLOY / "boundary.py"
    spec = importlib.util.spec_from_file_location("qmn_deploy_boundary_powers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_transport_identity_and_closed_sets() -> None:
    identity = powers_transport_identity()
    assert identity["surface"] == POWERS_TRANSPORT_SURFACE == "qmn.doors.http.powers"
    assert identity["socket_path"] == POWERS_SOCKET_PATH == "/run/qmn/powers.sock"
    assert identity["socket_owner"] == POWERS_SOCKET_OWNER == "qmx:qmxops"
    assert identity["socket_mode"] == POWERS_SOCKET_MODE == 0o660
    assert identity["service_account"] == SERVICE_ACCOUNT_NAME == "qmx"
    assert set(cast(Iterable[str], identity["principal_set"])) == PRINCIPAL_SET == {
        OPERATOR_PRINCIPAL,
        OPS_PRINCIPAL,
    }
    assert "agent" not in PRINCIPAL_SET
    assert identity["agent_never_a_principal"] is True
    assert set(cast(Iterable[str], identity["ops_allowed_powers"])) == OPS_ALLOWED_POWERS
    assert {
        "notify_test",
        "restore_drill_run",
        "config_validate",
        "hub_publish",
    } == OPS_ALLOWED_POWERS
    assert OPERATOR_ONLY_POWERS.isdisjoint(OPS_ALLOWED_POWERS)
    assert CLOSED_POWERS == OPS_ALLOWED_POWERS | OPERATOR_ONLY_POWERS
    for power in (
        "promotion_sign",
        "activation",
        "resurrect",
        "settings_edit",
        "attestation",
        "countersign",
        "value_status_countersign",
        "flatten",
    ):
        assert power in OPERATOR_ONLY_POWERS
        assert ops_power_allowed(power) is False


def test_declare_principals_refuses_service_account_and_collision() -> None:
    ok = _principals()
    assert ok.operator_uid == _OPERATOR_UID
    assert ok.ops_uid == _OPS_UID
    assert ok.service_account_uid == _QMX_UID

    same = declare_principals(
        operator_uid=_OPERATOR_UID,
        ops_uid=_OPERATOR_UID,
        service_account_uid=_QMX_UID,
    )
    assert is_refusal(same)
    assert same.context["field"] == "principals"

    op_is_qmx = declare_principals(
        operator_uid=_QMX_UID,
        ops_uid=_OPS_UID,
        service_account_uid=_QMX_UID,
    )
    assert is_refusal(op_is_qmx)
    assert op_is_qmx.context["field"] == "operator_uid"

    ops_is_qmx = declare_principals(
        operator_uid=_OPERATOR_UID,
        ops_uid=_QMX_UID,
        service_account_uid=_QMX_UID,
    )
    assert is_refusal(ops_is_qmx)
    assert ops_is_qmx.context["field"] == "ops_uid"

    bad = declare_principals(
        operator_uid=-1,
        ops_uid=_OPS_UID,
        service_account_uid=_QMX_UID,
    )
    assert is_refusal(bad)


def test_unknown_and_service_peer_refused_and_journaled() -> None:
    principals = _principals()
    journal = RecordingPowersJournal()

    stranger = authorize_powers_call(
        peer=_peer(_STRANGER_UID),
        principals=principals,
        power="notify_test",
        journal=journal,
    )
    assert is_refusal(stranger)
    assert stranger.context["field"] == "peer"
    assert journal.records[-1]["decision"] == "refuse"
    assert journal.records[-1]["reason"] == "unknown-or-service-peer"

    service = authorize_powers_call(
        peer=_peer(_QMX_UID),
        principals=principals,
        power="notify_test",
        journal=journal,
    )
    assert is_refusal(service)
    assert "qmx" in str(service.context["reason"])
    assert journal.records[-1]["decision"] == "refuse"


def test_claimed_identity_never_overrides_peer_credentials() -> None:
    principals = _principals()
    journal = RecordingPowersJournal()

    # Ops peer claiming to be the operator still authenticates as ops.
    auth = _ok(
        authorize_powers_call(
            peer=_peer(_OPS_UID),
            principals=principals,
            power="notify_test",
            claimed_signer="operator:mubarak",
            journal=journal,
        )
    )
    assert auth.principal == OPS_PRINCIPAL
    assert auth.peer.uid == _OPS_UID
    assert auth.claimed_signer == "operator:mubarak"
    assert auth.peer_overrides_claim is True

    # Same claim cannot unlock an operator-only power for ops.
    refused = authorize_powers_call(
        peer=_peer(_OPS_UID),
        principals=principals,
        power="promotion_sign",
        claimed_signer="operator:mubarak",
        journal=journal,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "power"
    assert journal.records[-1]["reason"] == "ops-power-refused"
    assert journal.records[-1]["principal"] == OPS_PRINCIPAL


def test_ops_refused_trading_and_human_only_powers_before_dispatch() -> None:
    principals = _principals()
    journal = RecordingPowersJournal()
    forbidden = (
        "promotion_sign",
        "activation",
        "resurrect",
        "settings_edit",
        "attestation",
        "countersign",
        "value_status_countersign",
        "flatten",
        "resolve_unknown",
        "seat_reinstate",
        "paper_flip",
        "kill_switch_escalate",
    )
    for power in forbidden:
        result = authorize_powers_call(
            peer=_peer(_OPS_UID),
            principals=principals,
            power=power,
            journal=journal,
        )
        assert is_refusal(result), power
        assert result.context["power"] == power

    for power in sorted(OPS_ALLOWED_POWERS):
        admitted = _ok(
            authorize_powers_call(
                peer=_peer(_OPS_UID),
                principals=principals,
                power=power,
                journal=journal,
            )
        )
        assert admitted.principal == OPS_PRINCIPAL
        assert admitted.power == power


def test_operator_may_call_every_closed_power() -> None:
    principals = _principals()
    for power in sorted(CLOSED_POWERS):
        auth = _ok(
            authorize_powers_call(
                peer=_peer(_OPERATOR_UID),
                principals=principals,
                power=power,
                claimed_signer="operator:mubarak",
            )
        )
        assert auth.principal == OPERATOR_PRINCIPAL
        assert auth.power == power


def test_agent_signer_refused_human_signer_admitted() -> None:
    principals = _principals()
    journal = RecordingPowersJournal()

    assert is_human_signer("operator:mubarak") is True
    assert is_human_signer("reviewer:amina") is True
    for prefix in AGENT_SIGNER_PREFIXES:
        assert is_human_signer(f"{prefix}bot-7") is False

    agent = authorize_powers_call(
        peer=_peer(_OPERATOR_UID),
        principals=principals,
        power="promotion_sign",
        claimed_signer="agent:bot-7",
        journal=journal,
    )
    assert is_refusal(agent)
    assert agent.context["field"] == "claimed_signer"
    assert journal.records[-1]["reason"] == "agent-signer-refused"

    machine = authorize_powers_call(
        peer=_peer(_OPERATOR_UID),
        principals=principals,
        power="activation",
        claimed_signer="machine:cron",
        journal=journal,
    )
    assert is_refusal(machine)

    human = _ok(
        authorize_powers_call(
            peer=_peer(_OPERATOR_UID),
            principals=principals,
            power="promotion_sign",
            claimed_signer="operator:mubarak",
            journal=journal,
        )
    )
    assert human.claimed_signer == "operator:mubarak"
    assert journal.records[-1]["decision"] == "admit"


def test_unknown_power_and_blank_inputs_refused() -> None:
    principals = _principals()
    unknown = authorize_powers_call(
        peer=_peer(_OPERATOR_UID),
        principals=principals,
        power="invented_live_toggle",
    )
    assert is_refusal(unknown)
    assert unknown.context["field"] == "power"

    blank = authorize_powers_call(
        peer=_peer(_OPERATOR_UID),
        principals=principals,
        power="  ",
    )
    assert is_refusal(blank)

    blank_signer = authorize_powers_call(
        peer=_peer(_OPERATOR_UID),
        principals=principals,
        power="notify_test",
        claimed_signer="   ",
    )
    assert is_refusal(blank_signer)


def test_resolve_peer_principal_mapping() -> None:
    principals = _principals()
    op = _ok(resolve_peer_principal(peer=_peer(_OPERATOR_UID), principals=principals))
    assert op.principal == OPERATOR_PRINCIPAL
    ops = _ok(resolve_peer_principal(peer=_peer(_OPS_UID), principals=principals))
    assert ops.principal == OPS_PRINCIPAL
    assert is_refusal(
        resolve_peer_principal(peer=_peer(_STRANGER_UID), principals=principals)
    )


def test_unit_principals_preflight_refuses_operator_uid() -> None:
    ok = evaluate_unit_principals(
        operator_uid=_OPERATOR_UID,
        unit_uids=(_QMX_UID, _OPS_UID, 0),
    )
    assert is_ok(ok)

    bad = evaluate_unit_principals(
        operator_uid=_OPERATOR_UID,
        unit_uids=(_QMX_UID, _OPERATOR_UID),
    )
    assert is_refusal(bad)
    assert bad.context["field"] == "unit_principals"
    assert bad.context["unit_uid"] == _OPERATOR_UID

    # Agent is never added to the principal set — only operator/ops exist.
    assert frozenset({OPERATOR_PRINCIPAL, OPS_PRINCIPAL}) == PRINCIPAL_SET


def test_read_peercred_from_socket_double() -> None:
    class _Sock:
        def getsockopt(self, level: int, opt: int, buflen: int) -> bytes:
            assert level  # SOL_SOCKET
            assert opt == peercred_option()
            assert buflen == struct.calcsize("3i")
            return struct.pack("3i", 99, _OPERATOR_UID, 50)

    cred = _ok(read_peercred(_Sock()))
    assert cred == PeerCredential(pid=99, uid=_OPERATOR_UID, gid=50)

    class _Broken:
        def getsockopt(self, *_args: object) -> bytes:
            raise OSError("no peercred")

    assert is_refusal(read_peercred(_Broken()))
    assert is_refusal(read_peercred(object()))


def test_doors_reexport_powers_transport() -> None:
    assert doors.POWERS_TRANSPORT_SURFACE == POWERS_TRANSPORT_SURFACE
    assert doors.OPERATOR_PRINCIPAL == OPERATOR_PRINCIPAL
    assert doors.OPS_PRINCIPAL == OPS_PRINCIPAL
    assert doors.PRINCIPAL_SET == PRINCIPAL_SET
    assert callable(doors.authorize_powers_call)
    assert callable(doors.evaluate_unit_principals)
    assert doors.shipped_doors() == ("python_api", "evidence_http", "powers_unix")


def test_deploy_toolkit_runs_only_as_ops_principal() -> None:
    boundary = _load_deploy_boundary()
    assert boundary.toolkit_principal() == OPS_PRINCIPAL
    assert boundary.OPS_PRINCIPAL_NAME == OPS_PRINCIPAL
    for action in (
        "place",
        "promote",
        "activate",
        "resurrect",
        "settings",
        "attestation",
        "countersign",
    ):
        assert boundary.recipe_action_allowed(action) is False


def test_powers_module_stays_stdlib_and_qmf_core_only() -> None:
    """Powers transport must not pull venue/risk or invent ambient principals."""
    path = _SRC / "doors" / "http" / "powers.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    banned_roots = {"qmf.venue", "qmf.risk", "twisted", "ctrader_open_api"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                assert alias.name not in banned_roots
                assert root not in {"twisted", "ctrader_open_api"}
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module not in banned_roots
            assert not node.module.startswith("qmf.venue")
            assert not node.module.startswith("qmf.risk")


def test_no_ambient_principal_invention_in_powers_source() -> None:
    assert frozenset({OPERATOR_PRINCIPAL, OPS_PRINCIPAL}) == PRINCIPAL_SET
    assert "agent" not in PRINCIPAL_SET
    # declare_principals never accepts a third principal name — only UIDs.
    assert not hasattr(powers_mod, "AGENT_PRINCIPAL")
    assert doors.PRINCIPAL_SET == PRINCIPAL_SET
