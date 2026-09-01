"""Story 45.1 — daemon registration of ExecutionEnvironment declarations (FR-Q48)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.ports.tools import ToolKind
from qma.core.refusals import ProhibitedMoneyPathTool, ProhibitedReachability
from qma.core.vocabulary.enums import (
    EnvironmentLifecycle,
    ExecutionEnvironmentKind,
    NetworkPolicy,
)
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal


class _EnvStub:
    """Structural ExecutionEnvironment stand-in."""


def test_register_requires_complete_declaration_surface() -> None:
    registry = ExecutionEnvironmentRegistry()
    declaration = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        mounts=({"source": "/opt/cache", "target": "/cache", "mode": "ro"},),
        environment_allowlist=("LANG",),
        capabilities=("cpu",),
        lifecycle="ephemeral",
    )
    accepted = registry.register_declaration(declaration)
    assert is_ok(accepted)
    stored = registry.declaration("docker")
    assert stored is not None
    surface = stored.surface()
    assert surface["kind"] == "docker"
    assert surface["provider_ref"] == "local-docker"
    assert surface["image"] == "qma-worker:isolated"
    assert surface["environment_allowlist"] == ("LANG",)
    assert surface["capabilities"] == ("cpu",)
    assert surface["network"] == "none"
    assert surface["lifecycle"] == "ephemeral"
    assert stored.lifecycle is EnvironmentLifecycle.EPHEMERAL


def test_ordinary_worker_is_docker_per_worker_ephemeral() -> None:
    registry = ExecutionEnvironmentRegistry()
    selected = registry.select_ordinary_worker()
    assert is_ok(selected)
    assert selected.value.kind is ExecutionEnvironmentKind.DOCKER
    assert selected.value.lifecycle is EnvironmentLifecycle.EPHEMERAL
    assert selected.value.is_docker_per_worker()
    assert selected.value.mounts == ()

    ensured = registry.ensure_ordinary_worker()
    assert is_ok(ensured)
    assert "docker" in registry.kinds()
    assert registry.snapshot()["ordinary_worker"] is True
    lease = registry.evaluate_environment_lease(
        task_id="task:ordinary",
        kind=ExecutionEnvironmentKind.DOCKER,
    )
    assert is_ok(lease)


def test_persistent_docker_is_not_the_ordinary_worker() -> None:
    registry = ExecutionEnvironmentRegistry()
    persistent = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        lifecycle="persistent",
    )
    assert is_ok(registry.register_declaration(persistent))
    refused = registry.select_ordinary_worker()
    assert is_refusal(refused)
    assert refused.context["reason"] == "ordinary_worker_not_ephemeral"


def test_shared_dirty_filesystem_refused_at_registration() -> None:
    registry = ExecutionEnvironmentRegistry()
    dirty = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        mounts=(
            {
                "source": "/var/lib/qma/shared-scratch",
                "target": "/work",
                "mode": "rw",
                "shared": True,
            },
        ),
    )
    refused = registry.register(
        ExecutionEnvironmentKind.DOCKER,
        _EnvStub(),
        declaration=dirty,
    )
    assert is_refusal(refused)
    assert ProhibitedReachability.matches(refused)
    assert refused.context["reason"] == "shared_dirty_filesystem"
    assert refused.context["stage"] == "registration"
    assert registry.is_empty()


def test_control_channel_env_allowlist_refused() -> None:
    registry = ExecutionEnvironmentRegistry()
    parsed = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        environment_allowlist=("QMA_CONTROL_CHANNEL",),
    )
    refused = registry.register_declaration(parsed)
    assert is_refusal(refused)
    assert refused.context["reason"] == "control_channel"
    assert refused.context["stage"] == "registration"


def test_allowlist_enumerates_permitted_destinations_only() -> None:
    registry = ExecutionEnvironmentRegistry()
    permitted = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="allowlist",
        reachable_hosts=("pypi.org",),
        provider_ref="local-docker",
        image="qma-worker:isolated",
    )
    assert is_ok(registry.register_declaration(permitted))
    stored = registry.declaration("docker")
    assert stored is not None
    assert stored.network is NetworkPolicy.ALLOWLIST

    other = ExecutionEnvironmentRegistry()
    venue = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="allowlist",
        reachable_hosts=("live.ctraderapi.com",),
        provider_ref="local-docker",
        image="qma-worker:isolated",
    )
    refused = other.register_declaration(venue)
    assert is_refusal(refused)
    assert refused.context["reason"] == "denied_host"
    assert refused.context["stage"] == "registration"
    assert other.is_empty()


def test_openrouter_host_refused_at_registration() -> None:
    registry = ExecutionEnvironmentRegistry()
    parsed = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="allowlist",
        reachable_hosts=("openrouter.ai",),
        provider_ref="local-docker",
        image="qma-worker:isolated",
    )
    refused = registry.register_declaration(parsed)
    assert is_refusal(refused)
    assert ProhibitedReachability.matches(refused)
    assert refused.context["matched"] == "openrouter"


def test_reachability_is_registration_refusal_not_hook() -> None:
    registry = ExecutionEnvironmentRegistry()
    parsed = ExecutionEnvironmentDeclaration.try_parse(
        kind="remote_host",
        network="none",
        reachable_hosts=(),
        provider_ref="trading-node-vps",
        host="trading-node-vps",
        lifecycle="persistent",
    )
    refused = registry.register_declaration(parsed)
    assert is_refusal(refused)
    assert refused.context["stage"] == "registration"
    assert refused.context["reason"] == "trading_node_host"
    placement = registry.place(
        task_id="task:hook",
        kind=ExecutionEnvironmentKind.REMOTE_HOST,
        host="qmn-vps",
    )
    assert is_refusal(placement)
    assert placement.context["stage"] == "placement"


def test_environment_registration_is_not_a_money_path_act() -> None:
    registry = ExecutionEnvironmentRegistry()
    tools = ToolRegistry(environments=registry)
    accepted = registry.register_declaration(
        ExecutionEnvironmentDeclaration.ordinary_docker_worker()
    )
    assert is_ok(accepted)
    refused = tools.register(
        tool_id="trading-readonly:submit_order",
        kind=ToolKind.PLUGIN,
        schema={"name": "submit_order"},
        acts=("submit_order",),
    )
    assert is_refusal(refused)
    assert ProhibitedMoneyPathTool.matches(refused)
    readonly = tools.register(
        tool_id="trading-readonly:positions",
        kind=ToolKind.PLUGIN,
        schema={"name": "positions"},
        acts=("read_positions",),
    )
    assert is_ok(readonly)


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "environment_declaration_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()


def test_money_path_capability_on_environment_refused() -> None:
    registry = ExecutionEnvironmentRegistry()
    parsed = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        capabilities=("submit_order",),
    )
    refused = registry.register_declaration(parsed)
    assert is_refusal(refused)
    assert refused.context["reason"] == "money_path_capability"
    assert registry.is_empty()
