"""Story 45.9 — deployment envelope and computer-use exclusion (FR-Q56)."""

from __future__ import annotations

import pytest
from qma.core.ports.deployment import (
    DAEMON_DIAL_DIRECTION,
    DEFAULT_DAEMON_HOST,
    DEFAULT_WORKER_ISOLATION,
    DEPLOYABLE_UNITS,
    GAP_0070_COMPUTER_USE_EXCLUSION,
    PAPER_ACCOUNT_ROLE,
    PAPER_IS_SANDBOX,
    QMA_MINTED_PROMOTION_COMMAND,
    QMA_MINTED_ZONE_TRANSITION,
    REMOTE_DEPLOY_TARGETS,
    REMOTE_DIAL_DIRECTION,
    SOLE_ZONE_WRITE,
    AccountZone,
    DeployableUnit,
    RemoteDeployTarget,
    ZoneMutation,
    admit_paper_role,
    admit_zone_access,
    default_deployment_envelope,
    is_paper_sandbox_token,
    kind_and_lifecycle_for,
    parse_dial_out_declaration,
    parse_remote_deployment_request,
    record_human_promotion_ref,
    refuse_computer_use_provision,
    refuse_daemon_dial_in,
    refuse_deployed_inbound_port,
    refuse_paper_as_sandbox,
    refuse_promotion_command,
)
from qma.core.vocabulary.enums import EnvironmentLifecycle, ExecutionEnvironmentKind
from qmf.core import is_ok, is_refusal


def test_default_envelope_is_workstation_with_docker_workers() -> None:
    envelope = default_deployment_envelope()
    assert envelope.host == DEFAULT_DAEMON_HOST == "operator_workstation"
    assert envelope.worker_isolation == DEFAULT_WORKER_ISOLATION == "docker_on_host"
    assert envelope.docker_workers_on_host is True
    assert envelope.computer_use_provisioned is False
    assert envelope.paper_is_sandbox is False
    assert envelope.minted_promotion_command is None
    payload = envelope.to_payload()
    assert payload["remote_dial_direction"] == REMOTE_DIAL_DIRECTION == "out"
    assert payload["daemon_dial_direction"] == DAEMON_DIAL_DIRECTION == "never_in"
    assert payload["sole_write"] == SOLE_ZONE_WRITE
    gap = payload["gap_0070"]
    assert isinstance(gap, dict)
    assert gap["gap"] == "GAP-0070"
    assert gap["provisioned"] == "false"


@pytest.mark.parametrize("unit", tuple(member.value for member in DeployableUnit))
@pytest.mark.parametrize("target", tuple(member.value for member in RemoteDeployTarget))
def test_quant_mission_worker_deploy_to_remote_targets(unit: str, target: str) -> None:
    parsed = parse_remote_deployment_request(
        unit=unit,
        target=target,
        host="research-box",
        daemon_address="wss://daemon.example:8443",
    )
    assert is_ok(parsed)
    assert parsed.value.unit.value == unit
    assert parsed.value.target.value == target
    assert parsed.value.dial_out.dials_out_to_daemon is True
    assert parsed.value.dial_out.exposes_inbound_listener is False
    assert parsed.value.dial_out.daemon_dials_in is False
    mapped = kind_and_lifecycle_for(target)
    assert is_ok(mapped)
    kind, lifecycle = mapped.value
    if target == "sandbox":
        assert kind is ExecutionEnvironmentKind.REMOTE_CONTAINER
        assert lifecycle is EnvironmentLifecycle.EPHEMERAL
    else:
        assert kind is ExecutionEnvironmentKind.REMOTE_HOST
        assert lifecycle is EnvironmentLifecycle.PERSISTENT


def test_invented_unit_and_target_refused() -> None:
    bad_unit = parse_remote_deployment_request(
        unit="steward",
        target="research_node",
        host="research-box",
        daemon_address="wss://daemon.example:8443",
    )
    assert is_refusal(bad_unit)
    assert bad_unit.context["field"] == "unit"
    bad_target = parse_remote_deployment_request(
        unit="quant",
        target="trading_node",
        host="research-box",
        daemon_address="wss://daemon.example:8443",
    )
    assert is_refusal(bad_target)
    assert bad_target.context["field"] == "target"
    assert frozenset(DeployableUnit) == DEPLOYABLE_UNITS
    assert frozenset(RemoteDeployTarget) == REMOTE_DEPLOY_TARGETS


def test_remote_must_dial_out_daemon_never_dials_in() -> None:
    inbound = parse_dial_out_declaration(
        dials_out_to_daemon=True,
        exposes_inbound_listener=True,
        daemon_address="wss://daemon.example:8443",
    )
    assert is_refusal(inbound)
    assert inbound.context["field"] == "exposes_inbound_listener"
    assert refuse_deployed_inbound_port().context["field"] == "exposes_inbound_listener"

    silent = parse_dial_out_declaration(
        dials_out_to_daemon=False,
        daemon_address="wss://daemon.example:8443",
    )
    assert is_refusal(silent)
    assert silent.context["field"] == "dials_out_to_daemon"

    dial_in = parse_dial_out_declaration(
        daemon_dials_in=True,
        daemon_address="wss://daemon.example:8443",
    )
    assert is_refusal(dial_in)
    assert dial_in.context["field"] == "daemon_dials_in"
    assert refuse_daemon_dial_in().context["daemon_dial_direction"] == "never_in"

    second = parse_dial_out_declaration(
        second_transport_channel=True,
        daemon_address="wss://daemon.example:8443",
    )
    assert is_refusal(second)

    admitted = parse_dial_out_declaration(daemon_address="wss://daemon.example:8443")
    assert is_ok(admitted)
    assert admitted.value.dials_out_to_daemon is True


def test_dev_and_paper_read_only_except_dev_zone_candidate() -> None:
    read_dev = admit_zone_access(zone="dev", mutation="read")
    assert is_ok(read_dev)
    read_paper = admit_zone_access(zone=AccountZone.PAPER, mutation=ZoneMutation.READ)
    assert is_ok(read_paper)
    candidate = admit_zone_access(zone="dev", mutation="candidate_write")
    assert is_ok(candidate)

    paper_write = admit_zone_access(zone="paper", mutation="write")
    assert is_refusal(paper_write)
    assert paper_write.context["field"] == "paper"
    dev_write = admit_zone_access(zone="dev", mutation="write")
    assert is_refusal(dev_write)
    live = admit_zone_access(zone="live", mutation="read")
    assert is_refusal(live)
    promote = admit_zone_access(zone="dev", mutation="promote")
    assert is_refusal(promote)
    assert promote.context["field"] == "zone_transition"
    transition = admit_zone_access(zone="dev", mutation="zone_transition")
    assert is_refusal(transition)


def test_paper_is_account_role_never_sandbox() -> None:
    assert PAPER_IS_SANDBOX is False
    admitted = admit_paper_role()
    assert is_ok(admitted)
    assert admitted.value == PAPER_ACCOUNT_ROLE
    sandbox = admit_paper_role(treat_as_sandbox=True)
    assert is_refusal(sandbox)
    assert is_paper_sandbox_token("paper-sandbox")
    token = parse_remote_deployment_request(
        unit="worker",
        target="sandbox",
        host="paper_sandbox",
        daemon_address="wss://daemon.example:8443",
    )
    assert is_refusal(token)
    assert token.context["field"] == "paper"
    assert refuse_paper_as_sandbox().context["paper_is_sandbox"] is False


def test_human_promotion_records_artifact_ref_only() -> None:
    recorded = record_human_promotion_ref("fp1:sha256:" + ("a" * 64))
    assert is_ok(recorded)
    assert recorded.value.recorded_outside_qma is True
    assert recorded.value.minted_promotion_command is None
    assert recorded.value.minted_zone_transition is None
    assert QMA_MINTED_PROMOTION_COMMAND is None
    assert QMA_MINTED_ZONE_TRANSITION is None
    command = record_human_promotion_ref("fp1:ok", promotion_command={"promote": True})
    assert is_refusal(command)
    assert command.context["field"] == "zone_transition"
    transition = record_human_promotion_ref("fp1:ok", zone_transition="live")
    assert is_refusal(transition)
    assert refuse_promotion_command().context["field"] == "zone_transition"
    empty = record_human_promotion_ref("  ")
    assert is_refusal(empty)


def test_computer_use_exclusion_is_deferred_gap_0070() -> None:
    assert GAP_0070_COMPUTER_USE_EXCLUSION["gap"] == "GAP-0070"
    assert GAP_0070_COMPUTER_USE_EXCLUSION["status"] == "deferred"
    assert GAP_0070_COMPUTER_USE_EXCLUSION["provisioned"] == "false"
    refused = refuse_computer_use_provision(host="windows-vps")
    assert is_refusal(refused)
    assert refused.context["gap"] == "GAP-0070"
    assert refused.context["kind"] == "desktop"
    assert refused.context["provisioned"] == "false"
