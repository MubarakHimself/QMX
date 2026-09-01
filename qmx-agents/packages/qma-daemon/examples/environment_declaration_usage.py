"""L27 reference usage: ExecutionEnvironment declaration registration (Story 45.1)."""

from __future__ import annotations

from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.vocabulary.enums import EnvironmentLifecycle, ExecutionEnvironmentKind
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qmf.core import is_ok, is_refusal


def main() -> None:
    registry = ExecutionEnvironmentRegistry()
    ordinary = ExecutionEnvironmentDeclaration.ordinary_docker_worker()
    assert ordinary.kind is ExecutionEnvironmentKind.DOCKER
    assert ordinary.lifecycle is EnvironmentLifecycle.EPHEMERAL
    assert ordinary.is_docker_per_worker()
    accepted = registry.register_declaration(ordinary)
    assert is_ok(accepted)
    selected = registry.select_ordinary_worker()
    assert is_ok(selected)
    assert selected.value.lifecycle is EnvironmentLifecycle.EPHEMERAL

    dirty = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="other-docker",
        image="qma-worker:isolated",
        mounts=({"source": "/shared", "target": "/work", "mode": "rw", "shared": True},),
    )
    other = ExecutionEnvironmentRegistry()
    refused = other.register_declaration(dirty)
    assert is_refusal(refused)
    assert refused.context["reason"] == "shared_dirty_filesystem"
    assert refused.context["stage"] == "registration"
    print("ordinary docker-per-worker environment registered; dirty shared FS refused")


if __name__ == "__main__":
    main()
