"""Story 41.6 — principal classes and human-gate commands (FR-Q20)."""

from __future__ import annotations

from typing import cast

from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary import PrincipalClass
from qma.wire import (
    DAEMON_JOB_TRIM_STREAMS,
    HUMAN_GATE_COMMANDS,
    HUMAN_GATE_OWNING_AD,
    HUMAN_GATE_VOCABULARY_OWNER,
    WIRE_PROTOCOL_VERSION,
    InitializeParams,
    WireConnection,
    authorize_wire_command,
    command_carries_principal,
    is_daemon_job_trim,
    is_human_gate_command,
    journal_entry_principal_shape,
    ledger_entry_principal_shape,
    parse_principal_class,
    refuse_principal_impersonation,
    validate_instance,
)
from qmf.core.refusal import Ok, is_ok, is_refusal

_REQUIRED_HUMAN_GATES = frozenset(
    {
        "admission.approve",
        "migration.confirm_forward_only",
        "unknown.resolve",
        "retention.trim",
        "plugin.install",
        "plugin.enable",
        "plugin.reload",
        "desk.create",
        "quant.create",
        "role.set_base",
        "model_family.assign",
        "tool_adapter.write",
        "store.restore_live",
        "routine.catch_up",
        "approval_request.read",
        "approval_request.answer",
        "desk.moved",
        "quant.write",
        "routine.write",
        "execution_environment.write",
        "mission.set_approval_route",
        "variable.set",
        "human_gate.answer",
    }
)


def test_ownership_and_closed_human_gate_list() -> None:
    assert HUMAN_GATE_VOCABULARY_OWNER == "qma-wire"
    assert HUMAN_GATE_OWNING_AD == "AD-24"
    assert _REQUIRED_HUMAN_GATES <= HUMAN_GATE_COMMANDS
    # No silent additions beyond the AD-24 list and its seed aliases.
    extras = HUMAN_GATE_COMMANDS - _REQUIRED_HUMAN_GATES
    assert extras == frozenset({"install_enable_plugin", "approve_hook_action"})
    assert frozenset({"mailbox.delivery", "telemetry"}) == DAEMON_JOB_TRIM_STREAMS


def test_authenticated_connection_carries_exactly_one_principal() -> None:
    conn = WireConnection()
    assert conn.principal_class is None
    refused = conn.authorize_command("desk.create")
    assert is_refusal(refused)

    authed = conn.authenticate("cred://operator/ui", principal_class="operator")
    assert isinstance(authed, Ok)
    assert conn.principal_class is PrincipalClass.OPERATOR

    machine = WireConnection()
    assert isinstance(
        machine.authenticate("cred://worker/analysis", principal_class="machine"),
        Ok,
    )
    assert machine.principal_class is PrincipalClass.MACHINE

    bad = parse_principal_class("admin")
    assert is_refusal(bad)


def test_principal_carried_verbatim_on_command_journal_ledger_shapes() -> None:
    cmd = command_carries_principal(
        "desk.create",
        "operator",
        args={"slug": "research"},
    )
    assert isinstance(cmd, Ok)
    shape = cmd.value.to_dict()
    assert shape["principal_class"] == "operator"
    assert shape["command"] == "desk.create"

    journal = journal_entry_principal_shape(
        event="desk.created",
        principal_class="operator",
        correlation_id="corr-1",
        payload={"slug": "research"},
    )
    assert isinstance(journal, Ok)
    journal_dict = journal.value.to_dict()
    assert journal_dict["principal_class"] == "operator"
    assert is_ok(
        validate_instance(
            {"record_kind": "journal", **journal_dict},
            "principal_record",
        )
    )

    ledger = ledger_entry_principal_shape(
        kind="task.dispatched",
        principal_class=PrincipalClass.MACHINE,
        correlation_id="corr-2",
        body={"task_id": "t-1"},
    )
    assert isinstance(ledger, Ok)
    ledger_dict = ledger.value.to_dict()
    assert ledger_dict["principal_class"] == "machine"
    assert is_ok(
        validate_instance(
            {"record_kind": "ledger", **ledger_dict},
            "principal_record",
        )
    )


def test_operator_human_gate_preserves_principal_without_blanket_authority() -> None:
    conn = WireConnection()
    assert isinstance(
        conn.authenticate("cred://operator/ui", principal_class="operator"),
        Ok,
    )
    params = InitializeParams.try_create(protocol_version=WIRE_PROTOCOL_VERSION)
    assert isinstance(params, Ok)
    assert is_ok(conn.complete_initialize(params.value, assign_producer_id="op-1"))

    authorized = conn.authorize_command("role.set_base", args={"role": "researcher"})
    assert isinstance(authorized, Ok)
    assert authorized.value.principal_class is PrincipalClass.OPERATOR
    assert authorized.value.human_gate is True
    assert authorized.value.to_dict()["blanket_authority"] is False
    stamped = authorized.value.to_command_shape().to_dict()
    assert stamped["principal_class"] == "operator"


def test_machine_human_gate_returns_operator_principal_required() -> None:
    for command in sorted(_REQUIRED_HUMAN_GATES):
        result = authorize_wire_command(command, "machine")
        assert is_refusal(result), command
        assert OperatorPrincipalRequired.matches(result), command
        assert result.context["command"] == command
        assert result.context["principal_class"] == "machine"

    # Seed aliases also refuse machine.
    for alias in ("install_enable_plugin", "approve_hook_action"):
        refused = authorize_wire_command(alias, PrincipalClass.MACHINE)
        assert is_refusal(refused), alias
        assert OperatorPrincipalRequired.matches(refused)


def test_daemon_job_trims_exempt_from_human_gate() -> None:
    assert is_daemon_job_trim(
        "retention.trim",
        stream="mailbox.delivery",
        inside_retention_window=True,
    )
    assert is_daemon_job_trim(
        "retention.trim",
        stream="telemetry",
        inside_retention_window=True,
    )
    assert not is_daemon_job_trim(
        "retention.trim",
        stream="mailbox.delivery",
        inside_retention_window=False,
    )
    assert not is_daemon_job_trim("retention.trim", stream="journal", inside_retention_window=True)

    allowed = authorize_wire_command(
        "retention.trim",
        "machine",
        trim_stream="telemetry",
        inside_retention_window=True,
    )
    assert isinstance(allowed, Ok)
    assert allowed.value.human_gate is False

    refused = authorize_wire_command(
        "retention.trim",
        "machine",
        trim_stream="telemetry",
        inside_retention_window=False,
    )
    assert is_refusal(refused)
    assert OperatorPrincipalRequired.matches(refused)


def test_non_human_gate_allows_machine() -> None:
    assert not is_human_gate_command("start_mission")
    assert not is_human_gate_command("invented.command")
    result = authorize_wire_command("start_mission", "machine", args={"goal": "x"})
    assert isinstance(result, Ok)
    assert result.value.human_gate is False
    assert result.value.principal_class is PrincipalClass.MACHINE


def test_machine_cannot_impersonate_or_acquire_operator() -> None:
    refused = refuse_principal_impersonation("machine", "operator")
    assert is_refusal(refused)
    assert OperatorPrincipalRequired.matches(refused)

    same = refuse_principal_impersonation("machine", "machine")
    assert isinstance(same, Ok)

    conn = WireConnection()
    assert isinstance(
        conn.authenticate("cred://worker/w1", principal_class="machine"),
        Ok,
    )
    escalate = conn.authenticate("cred://worker/w1", principal_class="operator")
    assert is_refusal(escalate)
    assert OperatorPrincipalRequired.matches(escalate)
    assert conn.principal_class is PrincipalClass.MACHINE


def test_command_schema_accepts_principal_class() -> None:
    body: dict[str, object] = {
        "family": "command",
        "name": "install_enable_plugin",
        "principal_class": "operator",
        "args": {},
    }
    assert is_ok(validate_instance(body, "command"))

    bad = cast(dict[str, object], {**body, "principal_class": "admin"})
    assert is_refusal(validate_instance(bad, "command"))
