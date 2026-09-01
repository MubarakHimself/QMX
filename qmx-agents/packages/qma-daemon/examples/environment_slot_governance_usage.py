"""L27 reference usage: environment-slot governance (Story 45.2)."""

from __future__ import annotations

from qma.core.ports.execution import (
    ENVIRONMENT_MAX_IN_FLIGHT_KEY,
    ExecutionEnvironmentDeclaration,
)
from qma.daemon.envs import ComputeRouter, ExecutionEnvironmentRegistry
from qmf.core import is_ok, is_refusal


def main() -> None:
    registry = ExecutionEnvironmentRegistry()
    declaration = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        max_in_flight=1,
    )
    assert is_ok(registry.register_declaration(declaration))
    router = ComputeRouter(environments=registry)
    granted = router.place_job(task_id="task:running", kind="docker")
    assert is_ok(granted)
    assert granted.value.granted is True
    assert granted.value.to_payload()["capacity_key"] == ENVIRONMENT_MAX_IN_FLIGHT_KEY

    queued = router.place_job(
        task_id="task:waiting",
        kind="docker",
        agent_machine="agent-box",
        agent_vendor="modal",
    )
    assert is_ok(queued)
    assert queued.value.is_queued is True
    assert queued.value.agent_choice_ignored is True
    assert router.occupied_count("docker") == 1

    assert is_ok(router.hold_unknown("task:running"))
    assert is_refusal(router.retry_unknown("task:running"))
    assert is_refusal(router.assume_outcome("task:running", "failed"))
    resolved = router.resolve_unknown("task:running", recorded=True)
    assert is_ok(resolved)
    assert resolved.value is not None
    assert resolved.value.lease is not None
    assert resolved.value.lease.task_id == "task:waiting"
    print("slot granted, overflow queued, unknown held until recorded resolution")


if __name__ == "__main__":
    main()
