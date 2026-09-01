"""L27 reference usage: capability-matched Compute Router placement (Story 45.3)."""

from __future__ import annotations

from qma.core.ports.compute import ComputeRequirement
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.tools import ToolKind
from qma.core.refusals import NoEnvironment
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qma.daemon.tools import GAP_0070_DESKTOP_EXCLUSION, ToolRegistry
from qmf.core import is_ok, is_refusal


def main() -> None:
    registry = ExecutionEnvironmentRegistry()
    declaration = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        capabilities=("cpu", "memory"),
        cpu=2,
        memory=1024,
        disk=4096,
    )
    assert is_ok(registry.register_declaration(declaration))
    router = ComputeRouter(environments=registry)
    requirement = ComputeRequirement.try_parse(
        kind="docker",
        cpu=1,
        memory=512,
        disk=1024,
        capabilities=("cpu",),
        timeout=1_000_000_000,
        max_memory=512,
        isolation="required",
    )
    placed = router.place_requirement(
        task_id="task:worker",
        requirement=requirement,
        agent_machine="agent-chosen-box",
        agent_vendor="modal",
    )
    assert is_ok(placed)
    assert placed.value.granted is True
    agent_view = placed.value.to_agent_payload()
    assert "provider_id" not in str(dict(agent_view))
    assert "modal" not in str(dict(agent_view))
    assert "agent-chosen-box" not in str(dict(agent_view))
    assert agent_view["kind"] == "docker"

    desktop = ComputeRequirement.try_parse(
        kind="desktop",
        cpu=1,
        memory=512,
        disk=1024,
        capabilities=("display",),
        timeout=1_000_000_000,
        max_memory=512,
        isolation="shared",
    )
    missing = router.place_requirement(task_id="task:computer-use", requirement=desktop)
    assert is_refusal(missing)
    assert NoEnvironment.matches(missing)
    assert missing.context["kind"] == "desktop"
    assert router.occupied_count("desktop") == 0
    assert GAP_0070_DESKTOP_EXCLUSION["gap"] == "GAP-0070"
    assert is_refusal(router.provision_windows_vps(host="windows-vps"))

    tools = ToolRegistry(environments=registry)
    assert is_ok(
        tools.register(
            tool_id="computer:click",
            kind=ToolKind.COMPUTER_USE,
            schema={"name": "click"},
            acts=("click",),
        )
    )
    tool = tools.get("computer:click")
    assert tool is not None
    assert tool.is_available() is False
    print("requirement placed by Compute Router; missing desktop is NoEnvironment")


if __name__ == "__main__":
    main()
