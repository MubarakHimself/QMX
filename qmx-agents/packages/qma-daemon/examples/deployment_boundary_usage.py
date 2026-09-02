"""L27 reference usage: deployment envelope and computer-use exclusion (Story 45.9)."""

from __future__ import annotations

from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.envs import DeploymentBoundary
from qmf.core import is_ok, is_refusal


def main() -> None:
    boundary = DeploymentBoundary()
    started = boundary.start()
    assert is_ok(started)
    assert started.value.host == "operator_workstation"
    assert started.value.docker_workers_on_host is True
    docker = boundary.environments.declaration("docker")
    assert docker is not None
    assert docker.kind is ExecutionEnvironmentKind.DOCKER
    assert docker.is_docker_per_worker()

    remote = boundary.deploy(
        unit="quant",
        target="research_node",
        host="research-box",
        daemon_address="wss://127.0.0.1:8443",
    )
    assert is_ok(remote)
    assert remote.value.dial_out.remote_dial_direction == "out"
    assert remote.value.dial_out.daemon_is_sole_inbound is True

    inbound = boundary.deploy(
        unit="worker",
        target="sandbox",
        host="sandbox-box",
        daemon_address="wss://127.0.0.1:8443",
        exposes_inbound_listener=True,
    )
    assert is_refusal(inbound)

    vps = boundary.deploy(
        unit="mission",
        target="remote_workspace",
        host="trading-node-vps",
        daemon_address="wss://127.0.0.1:8443",
    )
    assert is_refusal(vps)
    assert vps.context["reason"] == "trading_node_host"

    assert is_ok(boundary.register_computer_use_tool())
    tool = boundary.tools.get("computer:click")
    assert tool is not None
    assert tool.is_available() is False
    placed = boundary.place_computer_use()
    assert is_refusal(placed)

    assert is_ok(boundary.access_zone(zone="paper", mutation="read"))
    assert is_refusal(boundary.access_zone(zone="paper", mutation="write"))
    candidate = boundary.write_dev_zone_candidate({"note": "dev candidate"})
    assert is_ok(candidate)
    assert is_refusal(boundary.attempt_promotion())
    recorded = boundary.record_human_promotion("fp1:sha256:" + ("c" * 64))
    assert is_ok(recorded)
    assert recorded.value.minted_promotion_command is None
    print("workstation docker workers bound; remote dial-out admitted; trading-node refused")


if __name__ == "__main__":
    main()
