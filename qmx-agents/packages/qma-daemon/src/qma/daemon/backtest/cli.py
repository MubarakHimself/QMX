"""Production QMB door: spawn a real ``qmb`` CLI process (Story 36.2 / 36.5).

Agent → QMA backtest tool → Backtesting Service → this transport → ``qmb``
CLI → QMB. MCP is later. This module never imports the ``qmb`` package.

``RecordingQmbDoorTransport`` is not production and must not be presented as
a working integration. Acceptance tests that claim the door works spawn
``qmb`` or the documented test double written by ``write_qmb_cli_test_double``.
``JobHandle.cancel`` maps onto QMB abort; QMB writes the ``aborted`` ledger
line and QMA does not.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Literal

from qma.core.ports.cancel_authority import PRODUCTION_DOOR_MAPS_CANCEL_TO_QMB_ABORT
from qma.core.ports.qmb import (
    QMB_CLI_PROGRAM,
    QMB_OCCUPANCY_QUERY,
    QMB_ROUTE,
    QMB_WORLD_REPLAY,
    QmbAbortReceipt,
    QmbDoorInvocation,
    QmbDoorKind,
    QmbDoorReceipt,
    occupancy_from_invocation,
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
"""Documented QMB CLI test double (Story 36.2 / 36.5; NFR-W05).

Spawned by CliQmbDoorTransport as a real process. Not production and not
RecordingQmbDoorTransport. Writes a JSON receipt when QMA_QMB_RECEIPT_PATH
is set. Query argv ``analysis project`` prints canonical saved-view JSON.
Hang mode waits for QMA_QMB_CANCEL_PATH then writes an aborted QMB ledger
line — QMA never writes that file.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def _aborted_line(job_id: str) -> dict[str, object]:
    return {
        "role": "aborted",
        "state": "aborted",
        "writer": "qmb",
        "job_id": job_id,
        "cause": "cancel",
    }


def main() -> int:
    argv = sys.argv[1:]
    job_id = os.environ.get("QMA_QMB_JOB_ID", "")
    cancel_path = os.environ.get("QMA_QMB_CANCEL_PATH")
    ledger_path = os.environ.get("QMA_QMB_LEDGER_PATH")
    hang = os.environ.get("QMA_QMB_HANG") == "1"

    def write_aborted() -> None:
        if ledger_path:
            Path(ledger_path).write_text(
                json.dumps(_aborted_line(job_id)),
                encoding="utf-8",
            )

    if hang:
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            if cancel_path and Path(cancel_path).is_file():
                write_aborted()
                return 1
            time.sleep(0.05)
        write_aborted()
        return 1

    if argv[:2] == ["analysis", "project"]:
        view = {
            "as_of": {"kind": "registry-as-of", "value_ns": 0},
            "method": "projection",
            "predicate": {},
            "source_ct29": os.environ.get("QMA_QMB_SOURCE_CT29", "ct29:stream"),
            "source_ct32": os.environ.get(
                "QMA_QMB_SOURCE_CT32",
                "fp1:sha256:" + ("c" * 64),
            ),
        }
        sys.stdout.write(json.dumps(view, separators=(",", ":")))
        sys.stdout.flush()

    payload = {
        "argv": argv,
        "program": Path(sys.argv[0]).name,
        "world": os.environ.get("QMA_QMB_WORLD", ""),
        "job_id": job_id,
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
    cancel_path: str | None,
    ledger_path: str | None,
    hang: bool,
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
        ("source_ct32", "QMA_QMB_SOURCE_CT32"),
        ("source_ct29", "QMA_QMB_SOURCE_CT29"),
    ):
        value = _payload_str(payload, key)
        if value is not None:
            env[env_key] = value
    if receipt_path:
        env["QMA_QMB_RECEIPT_PATH"] = receipt_path
    if cancel_path:
        env["QMA_QMB_CANCEL_PATH"] = cancel_path
    if ledger_path:
        env["QMA_QMB_LEDGER_PATH"] = ledger_path
    if hang:
        env["QMA_QMB_HANG"] = "1"
    return env


@dataclass
class CliQmbDoorTransport:
    """Production QMB door. Spawns a ``qmb`` CLI process and never imports ``qmb``.

    Production ``argv0`` is ``("qmb",)``. Tests that claim the door works pass
    ``cli_qmb_test_double_argv0`` so this class still subprocess-spawns.
    """

    argv0: tuple[str, ...] = (QMB_CLI_PROGRAM,)
    receipt_path: str | None = None
    cancel_path: str | None = None
    ledger_path: str | None = None
    hang: bool = False
    query_timeout: float = 10.0
    production: Literal[True] = True
    spawns_qmb_process: Literal[True] = True
    maps_cancel_to_qmb_abort: Literal[True] = PRODUCTION_DOOR_MAPS_CANCEL_TO_QMB_ABORT
    _processes: dict[str, subprocess.Popen[bytes] | subprocess.Popen[str]] = field(
        default_factory=dict[str, subprocess.Popen[bytes] | subprocess.Popen[str]]
    )
    _spawned: list[SpawnedQmbProcess] = field(default_factory=list[SpawnedQmbProcess])
    _abort_invocations: list[str] = field(default_factory=list[str])
    _cancel_paths: dict[str, str] = field(default_factory=dict[str, str])

    @property
    def abort_invocations(self) -> tuple[str, ...]:
        return tuple(self._abort_invocations)

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

    def _cancel_path_for(self, job_id: str) -> str:
        existing = self._cancel_paths.get(job_id)
        if existing is not None:
            return existing
        if self.cancel_path:
            return self.cancel_path
        safe = job_id.replace(":", "_").replace("/", "_")
        if self.receipt_path:
            return f"{self.receipt_path}.{safe}.cancel"
        return f"{safe}.qmb.cancel"

    def abort(self, job_id: str) -> Result[QmbAbortReceipt]:
        """Map JobHandle.cancel onto QMB abort. QMB writes the aborted ledger line."""
        proc = self._processes.get(job_id)
        if proc is None:
            return invalid_input(
                "job_id",
                "JobHandle.cancel maps to QMB abort only for a spawned qmb process",
                given=job_id,
            )
        self._abort_invocations.append(job_id)
        cancel_path = self._cancel_path_for(job_id)
        Path(cancel_path).write_text("JobHandle.cancel", encoding="utf-8")
        if proc.poll() is None:
            if sys.platform != "win32":
                try:
                    os.kill(int(proc.pid), signal.SIGINT)
                except OSError:
                    proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.terminate()
                try:
                    proc.wait(timeout=2.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2.0)
        return Ok(
            QmbAbortReceipt(
                job_id=job_id,
                mapped_from="JobHandle.cancel",
            )
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
        classified = occupancy_from_invocation(invocation)
        is_query = classified.occupancy == QMB_OCCUPANCY_QUERY
        command = self.command_for(invocation)
        cancel_path = self._cancel_path_for(job_id)
        self._cancel_paths[job_id] = cancel_path
        env = _door_env(
            invocation,
            receipt_path=self.receipt_path,
            cancel_path=cancel_path,
            ledger_path=self.ledger_path,
            hang=self.hang and not is_query,
        )
        stdout = subprocess.PIPE if is_query else subprocess.DEVNULL
        try:
            proc: subprocess.Popen[bytes] | subprocess.Popen[str]
            if sys.platform == "win32" and is_query:
                proc = subprocess.Popen(
                    list(command),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            elif sys.platform == "win32":
                proc = subprocess.Popen(
                    list(command),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            elif is_query:
                proc = subprocess.Popen(
                    list(command),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    start_new_session=True,
                    close_fds=True,
                )
            else:
                proc = subprocess.Popen(
                    list(command),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout,
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
        captured = ""
        if is_query:
            try:
                out, _err = proc.communicate(timeout=self.query_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=self.query_timeout)
                return policy_rejection(
                    "qmb_cli",
                    "qmb query CLI timed out; queries wait and persist refs (FR-W11; FR-W24)",
                    job_id=job_id,
                    occupancy=QMB_OCCUPANCY_QUERY,
                )
            captured = out if isinstance(out, str) else (out.decode("utf-8") if out else "")
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
                occupancy=classified.occupancy,
                mints_ct32=classified.mints_ct32,
                mints_experiment_spec=False,
                stdout=captured,
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
