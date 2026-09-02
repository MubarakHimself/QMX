"""Stdlib process-per-job spawn for a replay run (TN-21 / DEC-0206).

The public Python API and ``just node-replay`` start a child process. The child
loads a JSON spec and calls :func:`run_recorded_day`. The parent never drives
``run_slice`` on the node thread. Story 27.8 admits every spawned job through
the QMB orchestration seam and appends exactly one terminal ledger line.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmb.orchestrator.paths import MAX_JSONL_BYTES, read_contained_bytes
from qmb.orchestrator.watch import (
    WATCH_POLL_S,
    ProcessLimitProbe,
    check_process_abort,
    is_aborted_refusal,
    kill_owned_process,
)
from qmb.runloop.observe import (
    CAUSE_CANCEL,
    CAUSE_MEMORY_LIMIT,
    CAUSE_TIME_LIMIT,
    CancelToken,
    RunLimits,
)
from qmf.core import (
    Clock,
    Duration,
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    World,
    WriterId,
    is_ok,
    is_refusal,
)

from qmn.data.sealed_archive import SealedArchive
from qmn.replay._refuse import invalid, policy, storage, unavailable
from qmn.replay.ledger import (
    OUTPUT_NAME,
    SPEC_NAME,
    TERMINAL_ABORT,
    TERMINAL_BOUND,
    TERMINAL_CANCEL,
    TERMINAL_COMPLETE,
    TERMINAL_REFUSE,
    TERMINAL_TEARDOWN,
    WRITER_NAME,
    ReplayLedgerSink,
    ReplayTerminalRecord,
    mint_data_fingerprint,
    mint_run_fingerprint,
    read_intent,
    read_writer_manifest,
    write_intent,
)
from qmn.replay.port import ReplayImportPort
from qmn.replay.session import (
    NODE_PROCESS_ENV,
    REPLAY_PROCESS_ENV,
    ReplayJobSpec,
    allocate_replay_writer,
    assert_outside_node_process,
)
from qmn.time import VpsClock

__all__ = [
    "REPLAY_MODULE",
    "ReplayLiveJob",
    "ReplaySpawnReceipt",
    "finish_replay_job",
    "recover_replay_terminal",
    "run_replay_job",
    "spawn_replay_job",
    "spec_from_jsonable",
    "spec_to_jsonable",
    "start_replay_job",
    "teardown_replay_job",
]


REPLAY_MODULE: Final[str] = "qmn.replay"
_SPAWN_TIMEOUT_S: Final[int] = 60
_STORAGE_ID: Final[str] = "replay.ledger.storage"


@dataclass(frozen=True, slots=True)
class ReplaySpawnReceipt:
    """Evidence that the replay job ran in a distinct process."""

    pid: int
    parent_pid: int
    exit_code: int
    outside_node: bool
    world: str
    output_path: str
    terminal_status: str = TERMINAL_COMPLETE
    run_fp: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "pid": self.pid,
            "parent_pid": self.parent_pid,
            "exit_code": self.exit_code,
            "outside_node": self.outside_node,
            "world": self.world,
            "output_path": self.output_path,
            "same_process": self.pid == self.parent_pid,
            "terminal_status": self.terminal_status,
        }
        if self.run_fp is not None:
            payload["run_fp"] = self.run_fp
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class ReplayLiveJob:
    """A live OS process whose isolated output directory is named by the run."""

    spec: ReplayJobSpec
    run_fp: Fingerprint
    config_fp: str
    data_fp: Fingerprint
    composition_fp: str
    run_dir: Path
    output_path: Path
    evidence_root: Path
    pid: int
    process: subprocess.Popen[str]
    start_ns: int
    writer: WriterId
    cancel: CancelToken
    limits: RunLimits
    probe: ProcessLimitProbe | None


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


def start_replay_job(
    spec: ReplayJobSpec,
    *,
    evidence_root: Path,
    output_path: Path,
    cancel: CancelToken | None = None,
    limits: RunLimits | None = None,
    clock: object = None,
) -> Result[ReplayLiveJob]:
    """Create the isolated run directory and start the child OS process."""
    outside = assert_outside_node_process()
    if is_refusal(outside):
        return outside
    token = cancel if cancel is not None else CancelToken()
    bound = limits if limits is not None else RunLimits()
    if token.is_cancelled:
        return policy(
            "cancel",
            "a cancelled job is not admitted; no process starts and no terminal line is written",
            cause=token.cause,
        )
    bound_clock = _as_clock(clock, boot_epoch_id=spec.boot_epoch_id)
    if is_refusal(bound_clock):
        return bound_clock
    run_dir = output_path.parent
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return storage(
            "run_dir",
            "the isolated replay run directory could not be created",
            failure_id=_STORAGE_ID,
            given=type(exc).__name__,
            requiring_review=True,
        )
    run_fp = mint_run_fingerprint(spec, output_dir=run_dir)
    if is_refusal(run_fp):
        return run_fp
    data_fp = mint_data_fingerprint(spec)
    if is_refusal(data_fp):
        return data_fp
    writer = _ledger_writer(spec)
    if is_refusal(writer):
        return writer
    spec_path = run_dir / SPEC_NAME
    writer_path = run_dir / WRITER_NAME
    start = _stamp_wall_ns(bound_clock.value)
    if is_refusal(start):
        return start
    start_ns = start.value
    spec_body = spec_to_jsonable(spec, evidence_root=evidence_root)
    try:
        spec_path.write_text(json.dumps(spec_body, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return storage(
            "spec",
            "the isolated spec.json could not be written",
            failure_id=_STORAGE_ID,
            given=type(exc).__name__,
            requiring_review=True,
        )
    manifest = {
        "boot_epoch_id": spec.boot_epoch_id,
        "composition_fp": spec.composition_fp,
        "config_fp": spec.composition_fp,
        "data_fp": data_fp.value.value,
        "interval": {"start_ns": spec.start_ns, "end_ns": spec.end_ns},
        "machine": spec.machine,
        "output_path": str(output_path),
        "pid": 0,
        "run_fp": run_fp.value.value,
        "start_ns": start_ns,
        "writer": {
            "boot_epoch_id": writer.value.boot_epoch_id,
            "machine": writer.value.machine,
            "role": writer.value.role,
            "stream": writer.value.stream,
        },
    }
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
    manifest["pid"] = proc.pid
    try:
        writer_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        kill_owned_process(proc)
        return storage(
            "writer",
            "writer.json could not be written after spawn",
            failure_id=_STORAGE_ID,
            given=type(exc).__name__,
            requiring_review=True,
        )
    started_mono = _stamp_mono_ns(bound_clock.value)
    if is_refusal(started_mono):
        kill_owned_process(proc)
        return started_mono
    probe = ProcessLimitProbe(proc.pid, started_mono.value)
    return Ok(
        ReplayLiveJob(
            spec=spec,
            run_fp=run_fp.value,
            config_fp=spec.composition_fp,
            data_fp=data_fp.value,
            composition_fp=spec.composition_fp,
            run_dir=run_dir,
            output_path=output_path,
            evidence_root=evidence_root,
            pid=proc.pid,
            process=proc,
            start_ns=start_ns,
            writer=writer.value,
            cancel=token,
            limits=bound,
            probe=probe,
        )
    )


def finish_replay_job(
    live: object,
    *,
    ledger: object,
    terminal: object = None,
    clock: object = None,
) -> Result[ReplayTerminalRecord]:
    """Collect one spawned replay job and append exactly one terminal line.

    ``terminal`` forces teardown. Cancel and per-run bound breaches are observed
    through the QMB watch seam. A second call is idempotent.
    """
    job = _as_live(live)
    if is_refusal(job):
        return job
    sink = _as_ledger(ledger)
    if is_refusal(sink):
        return sink
    existing = sink.value.line_for(job.value.run_fp)
    if is_refusal(existing):
        return existing
    if existing.value is not None:
        return Ok(existing.value)
    forced = _optional_status(terminal)
    if is_refusal(forced):
        return forced
    bound_clock = _as_clock(clock, boot_epoch_id=job.value.spec.boot_epoch_id)
    if is_refusal(bound_clock):
        return bound_clock
    if forced.value == TERMINAL_TEARDOWN:
        kill_owned_process(job.value.process)
        return _commit_terminal(
            job.value,
            sink.value,
            status=TERMINAL_TEARDOWN,
            exit_code=None,
            clock=bound_clock.value,
        )
    status = _wait_for_job(job.value)
    if is_refusal(status):
        return status
    return _commit_terminal(
        job.value,
        sink.value,
        status=status.value,
        exit_code=job.value.process.returncode,
        clock=bound_clock.value,
    )


def teardown_replay_job(
    live: object, *, ledger: object, clock: object = None
) -> Result[ReplayTerminalRecord]:
    """Kill an in-flight admitted job and append the teardown terminal line."""
    return finish_replay_job(live, ledger=ledger, terminal=TERMINAL_TEARDOWN, clock=clock)


def recover_replay_terminal(
    *,
    run_dir: object,
    ledger: object,
    clock: object = None,
) -> Result[ReplayTerminalRecord]:
    """Scan the run directory and writer stream; append a missing terminal line.

    Ordered-with-recovery: an existing terminal line is returned unchanged. A
    committed intent is appended idempotently. Otherwise output persistence
    classifies complete/refuse, and a missing output is abort. A storage
    failure is explicit and requires review; nothing is rewritten.
    """
    sink = _as_ledger(ledger)
    if is_refusal(sink):
        return sink
    directory = run_dir if isinstance(run_dir, Path) else Path(str(run_dir))
    manifest = read_writer_manifest(directory)
    if is_refusal(manifest):
        return manifest
    run_fp = Fingerprint.try_create(manifest.value.get("run_fp"))
    if is_refusal(run_fp):
        return run_fp
    existing = sink.value.line_for(run_fp.value)
    if is_refusal(existing):
        return existing
    if existing.value is not None:
        return Ok(existing.value)
    intent = read_intent(directory)
    if is_refusal(intent):
        return intent
    if intent.value is not None:
        appended = sink.value.append(intent.value)
        if is_refusal(appended):
            return _review(appended)
        return appended
    boot_raw = manifest.value.get("boot_epoch_id")
    boot_epoch_id = (
        boot_raw.strip() if isinstance(boot_raw, str) and boot_raw.strip() != "" else "replay-boot"
    )
    bound_clock = _as_clock(clock, boot_epoch_id=boot_epoch_id)
    if is_refusal(bound_clock):
        return bound_clock
    inferred = _infer_from_run_dir(directory, manifest.value, clock=bound_clock.value)
    if is_refusal(inferred):
        return inferred
    decided = write_intent(directory, inferred.value)
    if is_refusal(decided):
        return _review(decided)
    appended = sink.value.append(inferred.value)
    if is_refusal(appended):
        return _review(appended)
    return appended


def run_replay_job(
    spec: ReplayJobSpec,
    *,
    evidence_root: Path,
    output_path: Path,
    ledger: ReplayLedgerSink,
    cancel: CancelToken | None = None,
    limits: RunLimits | None = None,
    timeout_s: int | None = None,
    clock: object = None,
) -> Result[ReplayTerminalRecord]:
    """Admit one replay job through the QMB orchestration seam and ledger it."""
    bound = limits
    if bound is None and timeout_s is not None:
        parsed = _limits_from_timeout(timeout_s)
        if is_refusal(parsed):
            return parsed
        bound = parsed.value
    started = start_replay_job(
        spec,
        evidence_root=evidence_root,
        output_path=output_path,
        cancel=cancel,
        limits=bound,
        clock=clock,
    )
    if is_refusal(started):
        return started
    return finish_replay_job(started.value, ledger=ledger, clock=clock)


def spawn_replay_job(
    spec: ReplayJobSpec,
    *,
    evidence_root: Path,
    output_path: Path,
    timeout_s: int = _SPAWN_TIMEOUT_S,
    ledger: ReplayLedgerSink | None = None,
    cancel: CancelToken | None = None,
    limits: RunLimits | None = None,
    clock: object = None,
) -> Result[ReplaySpawnReceipt]:
    """Spawn ``python -m qmn.replay`` and append exactly one terminal line."""
    outside = assert_outside_node_process()
    if is_refusal(outside):
        return outside
    parent = os.getpid()
    sink = ledger
    if sink is None:
        created = ReplayLedgerSink.try_create(
            output_path.parent / "replay-ledger",
            machine=spec.machine,
            worker_slot="slot-0",
            boot_epoch_id=spec.boot_epoch_id,
        )
        if is_refusal(created):
            return created
        sink = created.value
    finished = run_replay_job(
        spec,
        evidence_root=evidence_root,
        output_path=output_path,
        ledger=sink,
        cancel=cancel,
        limits=limits,
        timeout_s=timeout_s,
        clock=clock,
    )
    if is_refusal(finished):
        return finished
    record = finished.value
    if record.status != TERMINAL_COMPLETE:
        extra: dict[str, object] = {
            "terminal": record.status,
            "writes_ledger": True,
            "aborted_line_absent": False,
            "run_fp": record.run_fp.value,
            "output_path": str(output_path),
        }
        if record.refusal is not None:
            extra["refusal"] = dict(record.refusal)
        if record.failure is not None:
            extra["failure"] = dict(record.failure)
        return unavailable(
            "spawn",
            "replay job terminated without a complete diagnostic report",
            terminal=extra["terminal"],
            writes_ledger=True,
            aborted_line_absent=False,
            run_fp=extra["run_fp"],
            output_path=extra["output_path"],
            refusal=extra.get("refusal"),
            failure=extra.get("failure"),
        )
    if record.run_fp.value == "":
        return invalid("run_fp", "a completed replay job carries a run fingerprint")
    return Ok(
        ReplaySpawnReceipt(
            pid=_pid_from_refs(record.output_refs, fallback=parent),
            parent_pid=parent,
            exit_code=0,
            outside_node=True,
            world=World.REPLAY.value,
            output_path=str(output_path),
            terminal_status=record.status,
            run_fp=record.run_fp.value,
        )
    )


def _wait_for_job(live: ReplayLiveJob) -> Result[str]:
    process = live.process
    while process.poll() is None:
        checked = check_process_abort(
            cancel=live.cancel,
            limits=live.limits,
            probe=live.probe,
        )
        if is_refusal(checked):
            if is_aborted_refusal(checked):
                cause = checked.context.get("cause", CAUSE_CANCEL)
                token = cause if isinstance(cause, str) else CAUSE_CANCEL
                kill_owned_process(process)
                if token in {CAUSE_TIME_LIMIT, CAUSE_MEMORY_LIMIT}:
                    return Ok(TERMINAL_BOUND)
                if token == CAUSE_CANCEL:
                    return Ok(TERMINAL_CANCEL)
                return Ok(TERMINAL_ABORT)
            return checked
        try:
            process.wait(timeout=WATCH_POLL_S)
        except subprocess.TimeoutExpired:
            continue
    if process.returncode is not None:
        with suppress(OSError):
            process.communicate()
    return Ok(_classify_exit(live))


def _classify_exit(live: ReplayLiveJob) -> str:
    envelope = _read_output_envelope(live.output_path, contain_within=live.run_dir)
    if envelope is not None and envelope.get("status") == TERMINAL_REFUSE:
        return TERMINAL_REFUSE
    if live.process.returncode == 0 and envelope is not None:
        return TERMINAL_COMPLETE
    if envelope is not None and envelope.get("world") == World.REPLAY.value:
        if envelope.get("status") == TERMINAL_REFUSE:
            return TERMINAL_REFUSE
        if "decisions" in envelope or "composition_fp" in envelope:
            return TERMINAL_COMPLETE
    if live.process.returncode not in (0, None) and envelope is None:
        return TERMINAL_ABORT
    if live.process.returncode not in (0, None):
        return TERMINAL_REFUSE
    if envelope is None:
        return TERMINAL_ABORT
    return TERMINAL_COMPLETE


def _commit_terminal(
    live: ReplayLiveJob,
    ledger: ReplayLedgerSink,
    *,
    status: str,
    exit_code: int | None,
    clock: Clock,
) -> Result[ReplayTerminalRecord]:
    ended = _stamp_wall_ns(clock)
    if is_refusal(ended):
        return ended
    end_ns = ended.value
    envelope = _read_output_envelope(live.output_path, contain_within=live.run_dir)
    refusal, failure = _refusal_from_envelope(envelope, status=status, exit_code=exit_code)
    refs: dict[str, object] = {
        "output_path": str(live.output_path),
        "pid": live.pid,
        "run_dir": live.run_dir.as_posix(),
        "writer_role": live.writer.role,
        "writer_stream": live.writer.stream,
    }
    if live.output_path.is_file():
        digest = _fingerprint_file(live.output_path, contain_within=live.run_dir)
        if is_ok(digest):
            refs["output_fp1"] = digest.value.value
    record = ReplayTerminalRecord(
        run_fp=live.run_fp,
        config_fp=live.config_fp,
        data_fp=live.data_fp,
        composition_fp=live.composition_fp,
        interval={"start_ns": live.spec.start_ns, "end_ns": live.spec.end_ns},
        status=status,
        start_ns=live.start_ns,
        end_ns=end_ns,
        output_refs=refs,
        refusal=refusal,
        failure=failure,
    )
    intent = write_intent(live.run_dir, record)
    if is_refusal(intent):
        return _review(intent)
    appended = ledger.append(record)
    if is_refusal(appended):
        return _review(appended)
    return appended


def _infer_from_run_dir(
    run_dir: Path, manifest: Mapping[str, object], *, clock: Clock
) -> Result[ReplayTerminalRecord]:
    run_fp = Fingerprint.try_create(manifest.get("run_fp"))
    if is_refusal(run_fp):
        return run_fp
    data_fp = Fingerprint.try_create(manifest.get("data_fp"))
    if is_refusal(data_fp):
        return data_fp
    config_fp = manifest.get("config_fp")
    composition_fp = manifest.get("composition_fp")
    if not isinstance(config_fp, str) or not isinstance(composition_fp, str):
        return invalid("writer", "writer.json carries config and composition fingerprints")
    interval_raw = manifest.get("interval")
    if not isinstance(interval_raw, Mapping):
        return invalid("interval", "writer.json carries the sealed interval")
    interval_map = cast("Mapping[str, object]", interval_raw)
    start_ns_raw = manifest.get("start_ns", 0)
    start_ns = (
        start_ns_raw if isinstance(start_ns_raw, int) and not isinstance(start_ns_raw, bool) else 0
    )
    output_raw = manifest.get("output_path")
    output_path = Path(output_raw) if isinstance(output_raw, str) else run_dir / OUTPUT_NAME
    envelope = _read_output_envelope(output_path, contain_within=run_dir)
    if envelope is not None and envelope.get("status") == TERMINAL_REFUSE:
        status = TERMINAL_REFUSE
    elif envelope is not None:
        status = TERMINAL_COMPLETE
    else:
        status = TERMINAL_ABORT
    refusal, failure = _refusal_from_envelope(envelope, status=status, exit_code=None)
    refs: dict[str, object] = {
        "output_path": str(output_path),
        "run_dir": run_dir.as_posix(),
        "recovered": True,
    }
    pid_raw = manifest.get("pid")
    if isinstance(pid_raw, int) and not isinstance(pid_raw, bool):
        refs["pid"] = pid_raw
    if output_path.is_file():
        digest = _fingerprint_file(output_path, contain_within=run_dir)
        if is_ok(digest):
            refs["output_fp1"] = digest.value.value
    start_raw = interval_map.get("start_ns")
    end_raw = interval_map.get("end_ns")
    interval = {
        "start_ns": start_raw
        if isinstance(start_raw, int) and not isinstance(start_raw, bool)
        else 0,
        "end_ns": end_raw if isinstance(end_raw, int) and not isinstance(end_raw, bool) else 0,
    }
    ended = _stamp_wall_ns(clock)
    if is_refusal(ended):
        return ended
    return Ok(
        ReplayTerminalRecord(
            run_fp=run_fp.value,
            config_fp=config_fp,
            data_fp=data_fp.value,
            composition_fp=composition_fp,
            interval=interval,
            status=status,
            start_ns=start_ns,
            end_ns=ended.value,
            output_refs=refs,
            refusal=refusal,
            failure=failure,
        )
    )


def _read_output_envelope(path: Path, *, contain_within: Path) -> Mapping[str, object] | None:
    if not path.exists():
        return None
    loaded = read_contained_bytes(
        path, contain_within=contain_within, max_bytes=MAX_JSONL_BYTES, field="output"
    )
    if is_refusal(loaded):
        return None
    try:
        parsed: object = json.loads(loaded.value)
    except ValueError:
        return None
    if not isinstance(parsed, Mapping):
        return None
    return dict(cast("Mapping[str, object]", parsed))


def _refusal_from_envelope(
    envelope: Mapping[str, object] | None,
    *,
    status: str,
    exit_code: int | None,
) -> tuple[Mapping[str, object] | None, Mapping[str, object] | None]:
    if envelope is not None:
        raw_refusal = envelope.get("refusal")
        if isinstance(raw_refusal, Mapping):
            refusal = dict(cast("Mapping[str, object]", raw_refusal))
            failure = (
                {"status": status, "exit_code": exit_code}
                if exit_code not in (0, None)
                else {"status": status}
            )
            return refusal, failure
    if status in {TERMINAL_COMPLETE}:
        return None, None
    failure: dict[str, object] = {"status": status}
    if exit_code is not None:
        failure["exit_code"] = exit_code
    return None, failure


def _fingerprint_file(path: Path, *, contain_within: Path) -> Result[Fingerprint]:
    loaded = read_contained_bytes(
        path, contain_within=contain_within, max_bytes=MAX_JSONL_BYTES, field="output"
    )
    if is_refusal(loaded):
        return loaded
    digest = hashlib.sha256(loaded.value).hexdigest()
    return Fingerprint.try_create(f"fp1:sha256:{digest}")


def _limits_from_timeout(timeout_s: object) -> Result[RunLimits]:
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, int) or timeout_s < 1:
        return invalid("timeout_s", "timeout_s is a positive integer second count")
    duration = Duration.try_create(timeout_s * 1_000_000_000)
    if is_refusal(duration):
        return duration
    return RunLimits.try_create(time_limit=duration.value)


def _ledger_writer(spec: ReplayJobSpec) -> Result[WriterId]:
    return allocate_replay_writer(
        machine=spec.machine,
        role="replay-ledger",
        stream="replay:ledger:slot-0",
        boot_epoch_id=spec.boot_epoch_id,
    )


def _as_live(value: object) -> Result[ReplayLiveJob]:
    if isinstance(value, ReplayLiveJob):
        return Ok(value)
    return invalid(
        "live",
        "finish_replay_job collects a ReplayLiveJob started by start_replay_job",
        given=repr(type(value).__name__),
    )


def _as_ledger(value: object) -> Result[ReplayLedgerSink]:
    if isinstance(value, ReplayLedgerSink):
        return Ok(value)
    return invalid(
        "ledger",
        "replay terminal writes go through a ReplayLedgerSink on the QMB orchestration seam",
        given=repr(type(value).__name__),
    )


def _optional_status(value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    token = value if isinstance(value, str) else None
    if token not in {
        TERMINAL_COMPLETE,
        TERMINAL_REFUSE,
        TERMINAL_ABORT,
        TERMINAL_CANCEL,
        TERMINAL_BOUND,
        TERMINAL_TEARDOWN,
    }:
        return invalid(
            "terminal",
            "forced terminal is complete, refuse, abort, cancel, bound, or teardown",
            given=repr(value),
        )
    return Ok(token)


def _pid_from_refs(refs: Mapping[str, object], *, fallback: int) -> int:
    raw = refs.get("pid")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return fallback


def _review(refusal: TypedRefusal) -> TypedRefusal:
    extra = dict(refusal.context)
    extra["failure_id"] = extra.get("failure_id", _STORAGE_ID)
    extra["requiring_review"] = True
    return TypedRefusal(
        category=refusal.category,
        retryability=refusal.retryability,
        context=extra,
        after_condition_descriptor=refusal.after_condition_descriptor,
    )


def _as_clock(clock: object, *, boot_epoch_id: str) -> Result[Clock]:
    if clock is None:
        bound = VpsClock.from_host_os(boot_epoch_id=boot_epoch_id)
        if is_refusal(bound):
            return bound
        return Ok(bound.value)
    if not isinstance(clock, Clock):
        return invalid(
            "clock",
            "the composition root injects a Clock; replay spawn never reads the system clock",
            given=repr(type(clock).__name__),
        )
    return Ok(clock)


def _stamp_wall_ns(clock: Clock) -> Result[int]:
    wall = clock.wall_now()
    if is_refusal(wall):
        return wall
    return Ok(wall.value.value_ns)


def _stamp_mono_ns(clock: Clock) -> Result[int]:
    mono = clock.monotonic_now()
    if is_refusal(mono):
        return mono
    return Ok(mono.value.value_ns)
