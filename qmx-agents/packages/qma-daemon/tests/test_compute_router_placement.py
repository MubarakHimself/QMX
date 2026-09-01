"""Story 45.3 — capability-matched Compute Router placement (FR-Q50)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.ports.compute import ComputeRequirement
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.tools import ToolKind
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon import CompileRequest, MissionCompiler, TaskGraphDispatcher
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qma.daemon.tools import GAP_0070_DESKTOP_EXCLUSION, ToolRegistry
from qmf.core import is_ok, is_refusal


def _quant(*, slug: str = "alpha") -> Quant:
    minted = ActorId.mint(DeskSlug.RESEARCH, slug)
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
    )


def _docker(**overrides: object) -> ExecutionEnvironmentDeclaration:
    values: dict[str, object] = {
        "kind": "docker",
        "network": "none",
        "reachable_hosts": (),
        "provider_ref": "local-docker",
        "image": "qma-worker:isolated",
        "capabilities": ("cpu", "memory"),
        "cpu": 2,
        "memory": 1024,
        "disk": 4096,
    }
    values.update(overrides)
    return ExecutionEnvironmentDeclaration.try_parse(**values)  # type: ignore[arg-type]


def _requirement(**overrides: object) -> ComputeRequirement:
    values: dict[str, object] = {
        "kind": "docker",
        "cpu": 1,
        "memory": 512,
        "disk": 1024,
        "capabilities": ("cpu",),
        "timeout": 1_000_000_000,
        "max_memory": 512,
        "isolation": "required",
    }
    values.update(overrides)
    return ComputeRequirement.try_parse(**values)  # type: ignore[arg-type]


def _bound_router(
    declaration: ExecutionEnvironmentDeclaration | None = None,
) -> ComputeRouter:
    registry = ExecutionEnvironmentRegistry()
    parsed = declaration if declaration is not None else _docker()
    assert is_ok(registry.register_declaration(parsed))
    return ComputeRouter(environments=registry)


def test_satisfiable_requirement_places_through_router_only() -> None:
    router = _bound_router()
    placed = router.place_requirement(
        task_id="task:run",
        requirement=_requirement(),
        agent_machine="agent-chosen-box",
        agent_vendor="modal",
        host="should-not-select",
    )
    assert is_ok(placed)
    assert placed.value.granted is True
    assert placed.value.lease is not None
    assert placed.value.lease.kind == "docker"
    assert placed.value.requirement is not None
    assert placed.value.requirement.cpu == 1
    agent_view = placed.value.to_agent_payload()
    serialized = str(dict(agent_view))
    assert "agent-chosen-box" not in serialized
    assert "modal" not in serialized
    assert "should-not-select" not in serialized
    assert "provider_id" not in serialized
    assert "local-docker" not in serialized
    assert agent_view["kind"] == "docker"
    requirement_view = agent_view["compute_requirement"]
    assert isinstance(requirement_view, dict)
    assert requirement_view["isolation"] == "required"
    assert router.requirement_for("task:run") is placed.value.requirement


def test_unbound_kind_is_no_environment_and_is_not_broadened() -> None:
    router = _bound_router(_docker())
    local = ExecutionEnvironmentDeclaration.try_parse(
        kind="local",
        network="none",
        reachable_hosts=(),
        provider_ref="workstation",
        capabilities=("cpu",),
    )
    assert is_ok(router.environments.register_declaration(local))
    missing = router.place_requirement(
        task_id="task:desktop",
        requirement=_requirement(kind="desktop", isolation="shared", capabilities=("display",)),
    )
    assert is_refusal(missing)
    assert NoEnvironment.matches(missing)
    assert missing.context["kind"] == "desktop"
    assert missing.context["reason"] == "kind_unbound"
    assert router.occupied_count("desktop") == 0
    assert router.occupied_count("docker") == 0
    assert router.occupied_count("local") == 0
    assert router.lease_for("task:desktop") is None


def test_unmet_capabilities_do_not_place_elsewhere() -> None:
    router = _bound_router(_docker(capabilities=("cpu",)))
    local = ExecutionEnvironmentDeclaration.try_parse(
        kind="local",
        network="none",
        reachable_hosts=(),
        provider_ref="workstation",
        capabilities=("cpu", "gpu"),
        gpu_count=1,
    )
    assert is_ok(router.environments.register_declaration(local))
    refused = router.place_requirement(
        task_id="task:gpu",
        requirement=_requirement(capabilities=("gpu",), gpu={"count": 1}),
    )
    assert is_refusal(refused)
    assert NoEnvironment.matches(refused)
    assert refused.context["kind"] == "docker"
    assert refused.context["reason"] == "unmet"
    assert router.occupied_count("docker") == 0
    assert router.occupied_count("local") == 0


def test_desktop_missing_is_no_environment_and_tool_check_fn_fails() -> None:
    registry = ExecutionEnvironmentRegistry()
    router = ComputeRouter(environments=registry)
    tools = ToolRegistry(environments=registry)
    assert GAP_0070_DESKTOP_EXCLUSION["gap"] == "GAP-0070"
    assert GAP_0070_DESKTOP_EXCLUSION["status"] == "deferred"
    assert GAP_0070_DESKTOP_EXCLUSION["provisioned"] == "false"
    assert "desktop" not in registry.kinds()

    missing = router.place_requirement(
        task_id="task:computer-use",
        requirement=_requirement(kind="desktop", isolation="shared", capabilities=("display",)),
    )
    assert is_refusal(missing)
    assert NoEnvironment.matches(missing)
    assert missing.context["kind"] == "desktop"

    provision = router.provision_windows_vps(host="windows-vps.example")
    assert is_refusal(provision)
    assert provision.context["gap"] == "GAP-0070"
    assert provision.context["provisioned"] == "false"
    assert "desktop" not in registry.kinds()

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
    assert tool.requires_environment_kind == "desktop"
    assert tool.is_available() is False
    assert tools.model_visible_schemas() == ()


def test_dispatcher_places_requirement_through_router() -> None:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(envs.register_declaration(_docker()))
    router = ComputeRouter(environments=envs)
    compiled = compiler.compile(
        CompileRequest(goal=Goal(text="place via requirement"), owner=owner)
    )
    assert is_ok(compiled)
    dispatcher = TaskGraphDispatcher(environments=envs, router=router)
    dispatcher.materialize(compiled.value.task_graph, mission=compiled.value.mission)
    decision = dispatcher.dispatch_task(
        task_id=compiled.value.task_graph.tasks[0].id,
        holder_agent_id="agent:w1",
        environment_kind=ExecutionEnvironmentKind.LOCAL,
        requirement=_requirement(),
    )
    assert is_ok(decision)
    assert decision.value.environment_lease is not None
    assert decision.value.environment_lease.kind == "docker"
    assert decision.value.environment_refusal is None
    agent_view = router.place_requirement(
        task_id=compiled.value.task_graph.tasks[0].id,
        requirement=_requirement(),
    )
    assert is_ok(agent_view)
    assert "local-docker" not in str(dict(agent_view.value.to_agent_payload()))


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "compute_router_placement_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
