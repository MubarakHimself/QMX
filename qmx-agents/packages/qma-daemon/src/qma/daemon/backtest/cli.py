"""Production QMB door: spawn a real ``qmb`` CLI process (Story 36.2; FR-W08).

Agent → QMA backtest tool → Backtesting Service → this transport → ``qmb``
CLI → QMB. MCP is later. This module never imports the ``qmb`` package.

``RecordingQmbDoorTransport`` is not production and must not be presented as
a working integration. Acceptance tests that claim the door works spawn
``qmb`` or the documented test double written by ``write_qmb_cli_test_double``.
``JobHandle.cancel`` still does not map onto a live ``qmb`` abort (Story 36.5).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

from qma.core.ports.cancel_authority import RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT
from qma.core.ports.qmb import (
    QMB_CLI_PROGRAM,
    QMB_ROUTE,
    QMB_WORLD_REPLAY,
    QmbDoorInvocation,
    QmbDoorKind,
    QmbDoorReceipt,
    refuse_qmb_import_edge,
    refuse_venue_account_backtest,
)
from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "QMB_CLI_TEST_DOUBLE_SOURCE",
    "CliQmbDoorTransport",
    "SpawnedQmbProcess",
    "cli_qmb_test_double_argv0",
    "write_qmb_cli_test_double",
]


QMB_CLI_TEST_DOUBLE_SOURCE: Final[str] = '''\
"""Documented QMB CLI test double (Story 36.2; NFR-W05).

Spawned by CliQmbDoorTransport as a real process. Not production and not
RecordingQmbDoorTransport. Writes a JSON receipt when QMA_QMB_RECEIPT_PATH
is set, then exits 0.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> int:
    payload = {
        "argv": sys.argv[1:],
        "program": Path(sys.argv[0]).name,
        "world": os.environ.get("QMA_QMB_WORLD", ""),
        "job_id": os.environ.get("QMA_QMB_JOB_ID", ""),
        "pid": os.getpid(),
    }
    out = os.environ.get("QMA_QMB_RECEIPT_PATH")
    if out:
        Path(out).write_text(json.dumps(payload), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def write_qmb_cli_test_double(path: Path) -> Path:
    """Write the documented spawnable ``qmb`` CLI stand-in to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(QMB_CLI_TEST_DOUBLE_SOURCE, encoding="utf-8")
    return path


def cli_qmb_test_double_argv0(path: Path) -> tuple[str, ...]:
    """``argv0`` that makes ``CliQmbDoorTransport`` spawn the documented double."""
    written = write_qmb_cli_test_double(path)
    return (sys.executable, str(written))


@dataclass(frozen=True, slots=True)
class SpawnedQmbProcess:
    """One placed ``qmb`` CLI process. QMB owns the run; QMA holds the pid."""

    job_id: str
    pid: int
    argv: tuple[str, ...]
    command: tuple[str, ...]


def _payload_str(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _door_env(
    invocation: QmbDoorInvocation,
    *,
    receipt_path: str | None,
) -> dict[str, str]:
    env = {str(key): str(value) for key, value in os.environ.items()}
    payload = dict(invocation.payload)
    env["QMA_QMB_DOOR"] = "cli"
    env["QMA_QMB_WORLD"] = str(payload.get("world", QMB_WORLD_REPLAY))
    env["QMA_QMB_DOOR_PAYLOAD"] = json.dumps(payload, separators=(",", ":"))
    for key, env_key in (
        ("job_id", "QMA_QMB_JOB_ID"),
        ("experiment_spec_fp1", "QMA_QMB_EXPERIMENT_SPEC_FP1"),
        ("evidence_ref", "QMA_QMB_EVIDENCE_REF"),
        ("environment_ref", "QMA_QMB_ENVIRONMENT_REF"),
        ("occupancy_key", "QMA_QMB_OCCUPANCY_KEY"),
    ):
        value = _payload_str(payload, key)
        if value is not None:
            env[env_key] = value
    if receipt_path:
        env["QMA_QMB_RECEIPT_PATH"] = receipt_path
    return env


@dataclass
class CliQmbDoorTransport:
    """Production QMB door. Spawns a ``qmb`` CLI process and never imports ``qmb``.

    Production ``argv0`` is ``("qmb",)``. Tests that claim the door works pass
    ``cli_qmb_test_double_argv0`` so this class still subprocess-spawns.
    """

    argv0: tuple[str, ...] = (QMB_CLI_PROGRAM,)
    receipt_path: str | None = None
    production: Literal[True] = True
    spawns_qmb_process: Literal[True] = True
    maps_cancel_to_qmb_abort: Literal[False] = RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT
    _processes: dict[str, subprocess.Popen[bytes]] = field(
        default_factory=dict[str, subprocess.Popen[bytes]]
    )
    _spawned: list[SpawnedQmbProcess] = field(default_factory=list[SpawnedQmbProcess])

    @property
    def spawned(self) -> tuple[SpawnedQmbProcess, ...]:
        return tuple(self._spawned)

    @property
    def spawned_pids(self) -> tuple[int, ...]:
        return tuple(row.pid for row in self._spawned)

    def command_for(self, invocation: QmbDoorInvocation) -> tuple[str, ...]:
        """Argv placed on the OS. Prefix is the CLI binary; suffix is door argv."""
        prefix = tuple(self.argv0) if self.argv0 else (QMB_CLI_PROGRAM,)
        return (*prefix, *invocation.argv)

    def abort(self, job_id: str) -> Result[None]:
        """Live qmb abort is Story 36.5. This transport places the process only."""
        return policy_rejection(
            "qmb_abort",
            "mapping JobHandle.cancel onto a live qmb abort is Story 36.5, "
            "not Story 36.2 (AR-W04; FR-W08)",
            job_id=job_id,
            transport="CliQmbDoorTransport",
            maps_cancel_to_qmb_abort=self.maps_cancel_to_qmb_abort,
        )

    def submit(self, invocation: QmbDoorInvocation) -> Result[QmbDoorReceipt]:
        if invocation.import_edge or invocation.program != QMB_CLI_PROGRAM:
            return refuse_qmb_import_edge(given=invocation.program)
        if invocation.kind is QmbDoorKind.MCP:
            return policy_rejection(
                "door",
                "the QMB door ships CLI first; MCP is later (DEC-0276; FR-W08)",
                given=invocation.kind.value,
            )
        payload = dict(invocation.payload)
        if payload.get("import_edge") is True:
            return refuse_qmb_import_edge()
        world = payload.get("world", QMB_WORLD_REPLAY)
        if world != QMB_WORLD_REPLAY:
            return refuse_venue_account_backtest(field="world", given=world)
        if payload.get("recorded") is not True:
            return refuse_venue_account_backtest(field="recorded", given=payload.get("recorded"))
        job_id = payload.get("job_id")
        environment_ref = payload.get("environment_ref")
        occupancy_key = payload.get("occupancy_key")
        if not isinstance(job_id, str) or not job_id:
            return invalid_input("job_id", "QMB door invocation requires a job id")
        if not isinstance(environment_ref, str) or not environment_ref:
            return invalid_input("environment_ref", "QMB door invocation requires environment_ref")
        if not isinstance(occupancy_key, str) or not occupancy_key:
            occupancy_key = environment_ref
        command = self.command_for(invocation)
        env = _door_env(invocation, receipt_path=self.receipt_path)
        try:
            if sys.platform == "win32":
                proc = subprocess.Popen(
                    list(command),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                proc = subprocess.Popen(
                    list(command),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True,
                )
        except OSError as exc:
            return policy_rejection(
                "qmb_cli",
                "could not spawn the qmb CLI process; the door is a runtime "
                "interaction, not an import (CT-47; DEC-0276)",
                program=command[0],
                argv=list(command[1:]),
                error=str(exc),
            )
        pid = int(proc.pid)
        self._processes[job_id] = proc
        self._spawned.append(
            SpawnedQmbProcess(
                job_id=job_id,
                pid=pid,
                argv=tuple(invocation.argv),
                command=command,
            )
        )
        return Ok(
            QmbDoorReceipt(
                job_id=job_id,
                environment_ref=environment_ref,
                occupancy_key=occupancy_key,
                door=invocation.kind,
                program=invocation.program,
                argv=invocation.argv,
                world=QMB_WORLD_REPLAY,
                route=QMB_ROUTE,
                import_edge=False,
            )
        )

    def wait(self, job_id: str, *, timeout: float = 10.0) -> int | None:
        """Wait for a spawned ``qmb`` process. Returns the exit code, if known."""
        proc = self._processes.get(job_id)
        if proc is None:
            return None
        return int(proc.wait(timeout=timeout))

    def close(self, *, timeout: float = 5.0) -> None:
        """Reap spawned CLI processes. Does not write QMB or Experiment ledgers."""
        for job_id, proc in list(self._processes.items()):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=timeout)
            self._processes.pop(job_id, None)
