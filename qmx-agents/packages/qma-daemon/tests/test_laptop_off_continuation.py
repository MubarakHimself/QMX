"""Story 32.1 — laptop-off continuation is a daemon property, not QMB process-per-run."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import CONTINUATION_BOUND_KEYS
from qma.core.ports.continuation_host import (
    CONTINUATION_LAPTOP_OFF_PROMISED_KEY,
    ContinuationDoor,
    JobLifetime,
)
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.refusals import LaptopOffContinuationRefused
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon import AuthoritativeJournal, PersistenceSubstrate
from qma.daemon.envs import (
    GAP_0062_HOST_MACHINE,
    ExecutionEnvironmentRegistry,
    LaptopOffContinuationGate,
)
from qma.daemon.journal import GovernedVariableRegistry
from qma.wire.outbox import OutboxBounds, RemoteOutbox
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal


def _clock(*, boot: str = "boot-32-1", n: int = 32) -> DataDrivenClock:
    base = 1_700_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    monos = tuple(i * 1_000 for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=monos)


def _open_journal(
    tmp_path: Path, *, boot: str = "boot-32-1"
) -> tuple[PersistenceSubstrate, AuthoritativeJournal]:
    substrate_result = PersistenceSubstrate.open(tmp_path, machine="test-host", boot_epoch_id=boot)
    assert is_ok(substrate_result), substrate_result
    substrate = substrate_result.value
    journal_result = AuthoritativeJournal.bind(substrate, clock=_clock(boot=boot))
    assert is_ok(journal_result), journal_result
    return substrate, journal_result.value


def _docker() -> ExecutionEnvironmentDeclaration:
    return ExecutionEnvironmentDeclaration.isolated(
        ExecutionEnvironmentKind.DOCKER,
        provider_ref="local-docker",
    )


def _fixture_remote() -> ExecutionEnvironmentDeclaration:
    return ExecutionEnvironmentDeclaration.try_parse(
        kind="remote_host",
        network="none",
        reachable_hosts=(),
        provider_ref="fixture-remote",
        host="fixture-remote",
        lifecycle="persistent",
    )


def _outbox(tmp_path: Path) -> RemoteOutbox:
    bounds = OutboxBounds.try_create(max_depth=8, max_spool_bytes=64_000)
    assert is_ok(bounds)
    return RemoteOutbox(directory=tmp_path / "outbox", bounds=bounds.value)


def test_builtin_promise_defaults_false_and_does_not_touch_46_7_keys() -> None:
    variables = GovernedVariableRegistry.with_builtins()
    row = variables.get(CONTINUATION_LAPTOP_OFF_PROMISED_KEY)
    assert is_ok(row)
    assert row.value.default is False
    value = variables.get_value(CONTINUATION_LAPTOP_OFF_PROMISED_KEY)
    assert is_ok(value)
    assert value.value is False
    gate = LaptopOffContinuationGate(variables=variables)
    assert gate.bound_keys == CONTINUATION_BOUND_KEYS
    assert CONTINUATION_LAPTOP_OFF_PROMISED_KEY not in gate.bound_keys


def test_promised_workstation_docker_only_is_typed_refusal() -> None:
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(envs.register_declaration(_docker()))
    gate = LaptopOffContinuationGate(environments=envs)
    refused = gate.evaluate(promised=True)
    assert is_refusal(refused)
    assert LaptopOffContinuationRefused.matches(refused)
    assert refused.context["reason"] == "laptop_only"
    assert refused.context["detail"] == "no_remote_env"
    assert refused.context["host_machine"] == GAP_0062_HOST_MACHINE


def test_fixture_env_marked_unreachable_proves_refusal_without_live_host(
    tmp_path: Path,
) -> None:
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(envs.register_declaration(_docker()))
    assert is_ok(envs.register_declaration(_fixture_remote()))
    marked = envs.mark_continuation_reachable("remote_host", False)
    assert is_ok(marked)
    assert envs.continuation_reachable("remote_host") is False
    gate = LaptopOffContinuationGate(environments=envs, outbox=_outbox(tmp_path))
    refused = gate.evaluate(promised=True)
    assert is_refusal(refused)
    assert LaptopOffContinuationRefused.matches(refused)
    assert refused.context["detail"] == "remote_unreachable"
    assert refused.context["unreachable_env_ids"] == ("remote_host",)
    assert "vps" not in str(refused.context).casefold()


def test_reachable_remote_plus_durable_outbox_admits_laptop_off(tmp_path: Path) -> None:
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(envs.register_declaration(_docker()))
    assert is_ok(envs.register_declaration(_fixture_remote()))
    gate = LaptopOffContinuationGate(environments=envs, outbox=_outbox(tmp_path))
    admitted = gate.evaluate(promised=True)
    assert is_ok(admitted)
    assert admitted.value.laptop_off is True
    assert admitted.value.daemon is True
    assert admitted.value.remote_env is True
    assert admitted.value.outbox is True
    assert admitted.value.host_machine == "operator_config"
    assert admitted.value.gap == "GAP-0062"
    assert admitted.value.owners == (
        "qma-daemon",
        "remote_execution_environment",
        "durable_outbox",
    )


def test_governed_qmb_spawn_keeps_process_per_run_lifetime(tmp_path: Path) -> None:
    envs = ExecutionEnvironmentRegistry()
    assert is_ok(envs.register_declaration(_fixture_remote()))
    gate = LaptopOffContinuationGate(environments=envs, outbox=_outbox(tmp_path))
    classified = gate.evaluate(
        promised=True,
        door=ContinuationDoor.GOVERNED_ORCHESTRATOR,
    )
    assert is_ok(classified)
    assert classified.value.laptop_off is False
    assert classified.value.lifetime is JobLifetime.QMB_PROCESS_PER_RUN
    assert classified.value.reason == "qmb_process_per_run"


def test_operator_promise_writes_registry_and_unpromised_is_not_continuation(
    tmp_path: Path,
) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        envs = ExecutionEnvironmentRegistry()
        assert is_ok(envs.register_declaration(_docker()))
        gate = LaptopOffContinuationGate(environments=envs)
        written = gate.promise(True, journal=journal)
        assert is_ok(written)
        promised = gate.promised()
        assert is_ok(promised)
        assert promised.value is True
        refused = gate.evaluate()
        assert is_refusal(refused)
        assert LaptopOffContinuationRefused.matches(refused)
        cleared = gate.promise(False, journal=journal)
        assert is_ok(cleared)
        admitted = gate.evaluate()
        assert is_ok(admitted)
        assert admitted.value.laptop_off is False
        assert admitted.value.reason == "not_promised"
    finally:
        journal.close()
        substrate.close()


def test_example_script() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "laptop_off_continuation_usage.py"
    namespace = runpy.run_path(str(path), run_name="__main__")
    assert namespace["main"] is not None
