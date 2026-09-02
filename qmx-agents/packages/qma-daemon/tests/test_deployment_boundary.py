"""Story 45.9 — daemon deployment boundary and computer-use exclusion (FR-Q56)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ports.deployment import (
    DEFAULT_DAEMON_HOST,
    DEFAULT_WORKER_ISOLATION,
    DEV_ZONE,
    GAP_0070_COMPUTER_USE_EXCLUSION,
    PAPER_IS_SANDBOX,
)
from qma.core.refusals import NoEnvironment, ProhibitedReachability
from qma.core.vocabulary.enums import (
    EnvironmentLifecycle,
    ExecutionEnvironmentKind,
)
from qma.daemon.envs import DeploymentBoundary, ExecutionEnvironmentRegistry
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal

DAEMON_ADDRESS = "wss://127.0.0.1:8443"


def test_start_binds_workstation_docker_workers_and_excludes_desktop() -> None:
    boundary = DeploymentBoundary()
    started = boundary.start()
    assert is_ok(started)
    assert started.value.host == DEFAULT_DAEMON_HOST
    assert started.value.worker_isolation == DEFAULT_WORKER_ISOLATION
    docker = boundary.environments.declaration("docker")
    assert docker is not None
    assert docker.kind is ExecutionEnvironmentKind.DOCKER
    assert docker.lifecycle is EnvironmentLifecycle.EPHEMERAL
    assert docker.is_docker_per_worker()
    assert docker.provider_ref == "operator-workstation-docker"
    assert "desktop" not in boundary.environments.kinds()
    assert boundary.computer_use_excluded is True
    again = boundary.start()
    assert is_ok(again)
    snap = boundary.snapshot()
    assert snap["docker_workers_on_host"] is True
    assert snap["computer_use_excluded"] is True
    assert snap["paper_is_sandbox"] is False


def test_quant_mission_worker_deploy_through_execution_environment() -> None:
    boundary = DeploymentBoundary()
    quant = boundary.deploy(
        unit="quant",
        target="research_node",
        host="research-box",
        daemon_address=DAEMON_ADDRESS,
    )
    assert is_ok(quant)
    assert quant.value.declaration.kind is ExecutionEnvironmentKind.REMOTE_HOST
    assert quant.value.dial_out.remote_dial_direction == "out"
    assert quant.value.dial_out.daemon_dial_direction == "never_in"
    assert quant.value.dial_out.daemon_is_sole_inbound is True
    assert quant.value.dial_out.deployed_exposes_listener is False

    mission = boundary.deploy(
        unit="mission",
        target="sandbox",
        host="sandbox-box",
        daemon_address=DAEMON_ADDRESS,
        image="qma-worker:isolated",
    )
    assert is_ok(mission)
    assert mission.value.declaration.kind is ExecutionEnvironmentKind.REMOTE_CONTAINER
    assert mission.value.declaration.lifecycle is EnvironmentLifecycle.EPHEMERAL

    worker = boundary.deploy(
        unit="worker",
        target="research_node",
        host="research-box",
        daemon_address=DAEMON_ADDRESS,
    )
    assert is_ok(worker)
    assert worker.value.request.unit.value == "worker"
    workspace = DeploymentBoundary().deploy(
        unit="quant",
        target="remote_workspace",
        host="workspace-box",
        daemon_address=DAEMON_ADDRESS,
    )
    assert is_ok(workspace)
    assert workspace.value.declaration.kind is ExecutionEnvironmentKind.REMOTE_HOST
    assert "docker" in boundary.environments.kinds()
    assert "remote_host" in boundary.environments.kinds()
    assert "remote_container" in boundary.environments.kinds()


def test_remote_inbound_port_and_daemon_dial_in_refused() -> None:
    boundary = DeploymentBoundary()
    inbound = boundary.deploy(
        unit="quant",
        target="research_node",
        host="research-box",
        daemon_address=DAEMON_ADDRESS,
        exposes_inbound_listener=True,
    )
    assert is_refusal(inbound)
    assert inbound.context["field"] == "exposes_inbound_listener"

    dial_in = boundary.deploy(
        unit="worker",
        target="sandbox",
        host="sandbox-box",
        daemon_address=DAEMON_ADDRESS,
        daemon_dials_in=True,
    )
    assert is_refusal(dial_in)
    assert dial_in.context["field"] == "daemon_dials_in"

    silent = boundary.deploy(
        unit="mission",
        target="research_node",
        host="research-box",
        daemon_address=DAEMON_ADDRESS,
        dials_out_to_daemon=False,
    )
    assert is_refusal(silent)
    assert "docker" in boundary.environments.kinds()
    assert "remote_host" not in boundary.environments.kinds()


def test_trading_node_vps_and_credential_hosts_refused_by_identity() -> None:
    boundary = DeploymentBoundary()
    vps = boundary.deploy(
        unit="quant",
        target="research_node",
        host="trading-node-vps",
        daemon_address=DAEMON_ADDRESS,
    )
    assert is_refusal(vps)
    assert ProhibitedReachability.matches(vps)
    assert vps.context["reason"] == "trading_node_host"
    assert vps.context["stage"] == "registration"
    assert boundary.environments.get("remote_host") is None

    credential = boundary.deploy(
        unit="worker",
        target="remote_workspace",
        host="ops-box",
        daemon_address=DAEMON_ADDRESS,
        carries_trading_credential=True,
    )
    assert is_refusal(credential)
    assert credential.context["reason"] == "trading_credential_host"

    node = boundary.deploy(
        unit="mission",
        target="research_node",
        host="ops-box",
        daemon_address=DAEMON_ADDRESS,
        running_node=True,
    )
    assert is_refusal(node)
    assert node.context["reason"] == "running_node_host"
    assert boundary.snapshot()["kinds"] == ["docker"]


def test_computer_use_excluded_until_desktop_registered() -> None:
    boundary = DeploymentBoundary()
    assert is_ok(boundary.start())
    registered = boundary.register_computer_use_tool()
    assert is_ok(registered)
    tool = boundary.tools.get("computer:click")
    assert tool is not None
    assert tool.requires_environment_kind == "desktop"
    assert tool.is_available() is False
    assert boundary.tools.model_visible_schemas() == ()

    placed = boundary.place_computer_use()
    assert is_refusal(placed)
    assert NoEnvironment.matches(placed)
    assert placed.context["kind"] == "desktop"

    provisioned = boundary.provision_computer_use_vps(host="windows-vps")
    assert is_refusal(provisioned)
    assert provisioned.context["gap"] == "GAP-0070"
    assert provisioned.context["provisioned"] == "false"
    assert GAP_0070_COMPUTER_USE_EXCLUSION["provisioned"] == "false"
    assert "desktop" not in boundary.environments.kinds()


def test_dev_paper_read_only_except_candidate_never_mints_promotion() -> None:
    boundary = DeploymentBoundary()
    assert is_ok(boundary.start())
    assert is_ok(boundary.access_zone(zone="dev", mutation="read"))
    assert is_ok(boundary.access_zone(zone="paper", mutation="read"))
    paper_write = boundary.access_zone(zone="paper", mutation="write")
    assert is_refusal(paper_write)
    live = boundary.access_zone(zone="live", mutation="read")
    assert is_refusal(live)

    written = boundary.write_dev_zone_candidate(
        {"note": "research candidate"},
        summary="content-addressed dev-zone candidate",
    )
    assert is_ok(written)
    assert written.value.zone == DEV_ZONE
    assert written.value.origin == "qma"

    paper_candidate = boundary.write_dev_zone_candidate({"note": "nope"}, zone="paper")
    assert is_refusal(paper_candidate)

    promote = boundary.attempt_promotion()
    assert is_refusal(promote)
    assert promote.context["field"] == "zone_transition"
    transition = boundary.attempt_zone_transition()
    assert is_refusal(transition)
    assert boundary.minted_promotion_command is None
    assert boundary.minted_zone_transition is None

    recorded = boundary.record_human_promotion("fp1:sha256:" + ("b" * 64))
    assert is_ok(recorded)
    assert recorded.value.recorded_outside_qma is True
    command = boundary.record_human_promotion("fp1:ok", promotion_command="promote")
    assert is_refusal(command)

    sandbox = boundary.admit_paper(treat_as_sandbox=True)
    assert is_refusal(sandbox)
    assert PAPER_IS_SANDBOX is False
    paper_host = boundary.deploy(
        unit="quant",
        target="sandbox",
        host="paper-sandbox",
        daemon_address=DAEMON_ADDRESS,
    )
    assert is_refusal(paper_host)
    snap = boundary.snapshot()
    assert snap["minted_promotion_command"] is None
    assert recorded.value.artifact_ref.startswith("fp1:")
    assert snap["human_promotion_refs"] == [dict(recorded.value.to_payload())]


def test_story_mints_no_promotion_or_openrouter_or_money_path_tool() -> None:
    source = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "envs"
    text = (source / "boundary.py").read_text(encoding="utf-8")
    assert "authorize_live_promotion" not in text
    assert "openrouter" not in text.casefold()
    assert "submit_order" not in text
    assert "qmf.venue" not in text
    tools = ToolRegistry()
    envs = ExecutionEnvironmentRegistry()
    boundary = DeploymentBoundary(environments=envs, tools=tools)
    assert boundary.tools is tools
    assert "qmn" not in text


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "deployment_boundary_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
