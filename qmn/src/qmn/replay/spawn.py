"""Stdlib process-per-job spawn for a replay run (TN-21 / DEC-0206).

The public Python API and ``just node-replay`` start a child process. The child
loads a JSON spec and calls :func:`run_recorded_day`. The parent never drives
``run_slice`` on the node thread.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Ok, Result, World, is_refusal

from qmn.data.sealed_archive import SealedArchive
from qmn.replay._refuse import invalid, unavailable
from qmn.replay.port import ReplayImportPort
from qmn.replay.session import (
    NODE_PROCESS_ENV,
    REPLAY_PROCESS_ENV,
    ReplayJobSpec,
    assert_outside_node_process,
)

__all__ = [
    "REPLAY_MODULE",
    "ReplaySpawnReceipt",
    "spawn_replay_job",
    "spec_from_jsonable",
    "spec_to_jsonable",
]


REPLAY_MODULE: Final[str] = "qmn.replay"
_SPAWN_TIMEOUT_S: Final[int] = 60


@dataclass(frozen=True, slots=True)
class ReplaySpawnReceipt:
    """Evidence that the replay job ran in a distinct process."""

    pid: int
    parent_pid: int
    exit_code: int
    outside_node: bool
    world: str
    output_path: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "pid": self.pid,
                "parent_pid": self.parent_pid,
                "exit_code": self.exit_code,
                "outside_node": self.outside_node,
                "world": self.world,
                "output_path": self.output_path,
                "same_process": self.pid == self.parent_pid,
            }
        )


def spec_to_jsonable(spec: ReplayJobSpec, *, evidence_root: Path) -> dict[str, object]:
    """Serialize a job spec for the child process (no secrets)."""
    body = dict(spec.as_mapping())
    body["evidence_root"] = str(evidence_root)
    return body


def spec_from_jsonable(body: object) -> Result[ReplayJobSpec]:
    """Rebuild a job spec from the child-process JSON (no secrets)."""
    if not isinstance(body, Mapping):
        return invalid("spec", "replay spec JSON is an object", given=type(body).__name__)
    mapping = dict(cast("Mapping[str, object]", body))
    root_raw = mapping.get("evidence_root")
    if not isinstance(root_raw, str) or root_raw.strip() == "":
        return invalid("evidence_root", "child spec names the sealed-archive evidence root")
    port = ReplayImportPort(SealedArchive(Path(root_raw)))
    return ReplayJobSpec.try_create(
        import_port=port,
        source_world=mapping.get("source_world"),
        room_role=mapping.get("room_role"),
        prefix_id=mapping.get("prefix_id"),
        start_ns=mapping.get("start_ns"),
        end_ns=mapping.get("end_ns"),
        composition_fp=mapping.get("composition_fp"),
        machine=mapping.get("machine", "replay-host"),
        boot_epoch_id=mapping.get("boot_epoch_id", "replay-boot"),
    )


def spawn_replay_job(
    spec: ReplayJobSpec,
    *,
    evidence_root: Path,
    output_path: Path,
    timeout_s: int = _SPAWN_TIMEOUT_S,
) -> Result[ReplaySpawnReceipt]:
    """Spawn ``python -m qmn.replay`` outside the caller process."""
    outside = assert_outside_node_process()
    if is_refusal(outside):
        return outside
    parent = os.getpid()
    spec_path = output_path.parent / f".{output_path.name}.spec-{parent}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        json.dumps(spec_to_jsonable(spec, evidence_root=evidence_root), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    env.pop(NODE_PROCESS_ENV, None)
    env[REPLAY_PROCESS_ENV] = "1"
    argv = [
        sys.executable,
        "-m",
        REPLAY_MODULE,
        "--spec",
        str(spec_path),
        "--output",
        str(output_path),
    ]
    try:
        proc = subprocess.Popen(
            argv,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        return unavailable(
            "spawn", "replay child process failed to start", error=type(exc).__name__
        )
    child_pid = proc.pid
    try:
        _stdout, stderr = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        return unavailable(
            "spawn",
            "replay child process exceeded the job timeout",
            timeout_s=timeout_s,
            pid=child_pid,
        )
    if proc.returncode != 0:
        return unavailable(
            "spawn",
            "replay child process exited nonzero",
            exit_code=proc.returncode,
            pid=child_pid,
            stderr=(stderr or "")[-2000:],
        )
    if child_pid == parent:
        return invalid(
            "process",
            "replay spawn must not share the caller pid",
            pid=child_pid,
        )
    return Ok(
        ReplaySpawnReceipt(
            pid=child_pid,
            parent_pid=parent,
            exit_code=int(proc.returncode or 0),
            outside_node=True,
            world=World.REPLAY.value,
            output_path=str(output_path),
        )
    )
