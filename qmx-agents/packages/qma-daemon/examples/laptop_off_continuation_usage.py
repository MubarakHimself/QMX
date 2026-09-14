"""L27 reference usage: laptop-off continuation is a daemon property."""

from __future__ import annotations

import tempfile
from pathlib import Path

from qma.core.ontology import CONTINUATION_BOUND_KEYS
from qma.core.ports.continuation_host import ContinuationDoor
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.refusals import LaptopOffContinuationRefused
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.envs import LaptopOffContinuationGate
from qma.wire.outbox import OutboxBounds, RemoteOutbox
from qmf.core import is_ok, is_refusal


def main() -> None:
    gate = LaptopOffContinuationGate()
    assert gate.bound_keys == CONTINUATION_BOUND_KEYS
    assert is_ok(
        gate.environments.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
    )
    laptop_only = gate.evaluate(promised=True)
    assert is_refusal(laptop_only)
    assert LaptopOffContinuationRefused.matches(laptop_only)

    assert is_ok(
        gate.environments.register_declaration(
            ExecutionEnvironmentDeclaration.try_parse(
                kind="remote_host",
                network="none",
                reachable_hosts=(),
                provider_ref="fixture-remote",
                host="fixture-remote",
                lifecycle="persistent",
            )
        )
    )
    assert is_ok(gate.environments.mark_continuation_reachable("remote_host", False))
    unreachable = gate.evaluate(promised=True)
    assert is_refusal(unreachable)
    assert unreachable.context["detail"] == "remote_unreachable"
    assert unreachable.context["host_machine"] == "operator_config"

    governed = gate.evaluate(promised=True, door=ContinuationDoor.GOVERNED_ORCHESTRATOR)
    assert is_ok(governed)
    assert governed.value.laptop_off is False
    assert governed.value.reason == "qmb_process_per_run"

    assert is_ok(gate.environments.mark_continuation_reachable("remote_host", True))
    root = Path(tempfile.mkdtemp(prefix="qma-laptop-off-"))
    bounds = OutboxBounds.try_create(max_depth=4, max_spool_bytes=32_000)
    assert is_ok(bounds)
    gate.bind_outbox(RemoteOutbox(directory=root / "outbox", bounds=bounds.value))
    admitted = gate.evaluate(promised=True)
    assert is_ok(admitted)
    assert admitted.value.laptop_off is True
    assert admitted.value.gap == "GAP-0062"


if __name__ == "__main__":
    main()
