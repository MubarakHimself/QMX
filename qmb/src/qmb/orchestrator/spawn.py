"""Process-per-run spawn with isolated output directories (B-5, AR-50).

The library's ``run()`` stays pure. This module is the impure owner of stdlib
process management: each run is a separate OS process writing only into a
directory named by the run id. Concurrent runs never share a writer.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.fingerprint import Fingerprint, World
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

from qmb._refuse import invalid, policy, unavailable
from qmb.config.compiler import ResolvedRunConfig
from qmb.orchestrator.governor import (
    ON_FULL_ENQUEUE,
    GovernedRequest,
    ResourceGovernor,
)
from qmb.runloop.loop import STREAM_SET_KEY, EventSlice, SliceObservation, run

__all__ = [
    "DAEMON",
    "DOCKER",
    "ONE_WRITER_PER_STREAM",
    "PAYLOAD_NAME",
    "PROCESS_MANAGEMENT",
    "RAY",
    "RESULT_NAME",
    "WRITER_NAME",
    "IsolatedRun",
    "LiveSpawn",
    "SpawnJob",
    "collect_run",
    "run_directory_name",
    "spawn_concurrent",
    "spawn_governed",
    "spawn_run",
    "start_run",
    "worker_main",
]

PROCESS_MANAGEMENT: Final[str] = "stdlib.subprocess"
RAY: Final[str] = "absent"
DOCKER: Final[str] = "not-required"
DAEMON: Final[str] = "not-required"
ONE_WRITER_PER_STREAM: Final[bool] = True
PAYLOAD_NAME: Final[str] = "payload.json"
RESULT_NAME: Final[str] = "result.json"
WRITER_NAME: Final[str] = "writer.json"
WORKER_MODULE: Final[str] = "qmb.orchestrator.worker"
_PAYLOAD_CLASS: Final[str] = "qmb-orchestrator-payload-v1"


@dataclass(frozen=True, slots=True)
class SpawnJob:
    """One resolved run-config plus the event slices the child feeds ``run()``.

    ``projected_peak_memory`` is the governor's per-run reservation (bytes).
    ``cpu_cost`` is the CPU-slot reservation (default one slot per run).
    """

    config: ResolvedRunConfig
    slices: object
    projected_peak_memory: int | None = None
    cpu_cost: int = 1


@dataclass(frozen=True, slots=True)
class LiveSpawn:
    """A live OS process whose isolated output directory is named by the run id."""

    run_id: Fingerprint
    output_dir: str
    pid: int
    process: subprocess.Popen[str]


@dataclass(frozen=True, slots=True)
class IsolatedRun:
    """Completed process-per-run outcome read back from the isolated directory."""

    run_id: Fingerprint
    output_dir: str
    pid: int
    worker_pid: int
    ct32_fingerprint: Fingerprint | None
    outcome_identity: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "outcome_identity",
            MappingProxyType(dict(self.outcome_identity)),
        )


def run_directory_name(run_id: object) -> Result[str]:
    """Filesystem-safe directory name for a run id (colon is illegal on Windows)."""
    parsed = _as_run_id(run_id)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value.value.replace(":", "-"))


def spawn_run(
    *,
    config: object,
    slices: object,
    output_root: object,
) -> Result[IsolatedRun]:
    """Spawn one OS process, drive pure ``run()``, and collect the isolated result."""
    started = start_run(config=config, slices=slices, output_root=output_root)
    if is_refusal(started):
        return started
    return collect_run(started.value)


def spawn_governed(
    jobs: object,
    *,
    output_root: object,
    cpu_budget: object = None,
    memory_budget: object = None,
    budgets: object = None,
    on_full: object = ON_FULL_ENQUEUE,
    projected_peak_memory: object = None,
) -> Result[tuple[IsolatedRun, ...]]:
    """Spawn under the resource governor: admit by min(cpu, memory), enqueue-on-full.

    A run whose projected peak exceeds the declared total budget is a typed
    refusal. A run that exceeds only remaining budget enqueues until a running
    run finishes, then the next queued run is admitted (B-5, FM-6).
    """
    parsed = _coerce_jobs(jobs)
    if is_refusal(parsed):
        return parsed
    items = parsed.value
    if not items:
        return invalid(
            "jobs",
            "spawn_governed starts one or more isolated runs under the governor",
        )
    seen: set[str] = set()
    for job in items:
        token = job.config.fingerprint.value
        if token in seen:
            return policy(
                "run_id",
                "two concurrent runs never share a writer for any file or stream; "
                "the isolated output directory is named by the run id",
                run_id=token,
            )
        seen.add(token)
    governor = ResourceGovernor.try_create(
        cpu_budget,
        memory_budget,
        budgets=budgets,
        on_full=on_full,
    )
    if is_refusal(governor):
        return governor
    requests: list[GovernedRequest] = []
    for job in items:
        request = _request_for_job(job, projected_peak_memory)
        if is_refusal(request):
            return request
        requests.append(request.value)
    bound = governor.value
    for request in requests:
        submitted = bound.submit(request)
        if is_refusal(submitted):
            return submitted
    return _drain_governed(items, bound, output_root)


def spawn_concurrent(jobs: object, *, output_root: object) -> Result[tuple[IsolatedRun, ...]]:
    """Start every job as its own OS process, then collect — never a shared writer."""
    parsed = _coerce_jobs(jobs)
    if is_refusal(parsed):
        return parsed
    items = parsed.value
    if not items:
        return invalid(
            "jobs",
            "spawn_concurrent starts one or more isolated runs",
        )
    seen: set[str] = set()
    for job in items:
        token = job.config.fingerprint.value
        if token in seen:
            return policy(
                "run_id",
                "two concurrent runs never share a writer for any file or stream; "
                "the isolated output directory is named by the run id",
                run_id=token,
            )
        seen.add(token)
    live: list[LiveSpawn] = []
    for job in items:
        started = start_run(config=job.config, slices=job.slices, output_root=output_root)
        if is_refusal(started):
            _reap_live(live)
            return started
        live.append(started.value)
    collected: list[IsolatedRun] = []
    for item in live:
        done = collect_run(item)
        if is_refusal(done):
            _reap_live(live[len(collected) + 1 :])
            return done
        collected.append(done.value)
    return Ok(tuple(collected))


def start_run(
    *,
    config: object,
    slices: object,
    output_root: object,
) -> Result[LiveSpawn]:
    """Create the isolated directory and start the child OS process (B-5)."""
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "the orchestrator drives the library run() over a resolved run-config",
            given=repr(type(config).__name__),
        )
    encoded_slices = _encode_slices(slices)
    if is_refusal(encoded_slices):
        return encoded_slices
    root = _as_output_root(output_root)
    if is_refusal(root):
        return root
    named = run_directory_name(config.fingerprint)
    if is_refusal(named):
        return named
    directory = (root.value / named.value).resolve()
    try:
        directory.mkdir(parents=False, exist_ok=False)
    except FileExistsError:
        return policy(
            "output_dir",
            "two runs never share a writer for any file or stream; the isolated "
            "output directory named by this run id is already present",
            output_dir=str(directory),
            run_id=config.fingerprint.value,
        )
    except OSError as exc:
        return unavailable(
            "output_dir",
            "stdlib process management could not create the isolated output directory",
            given=type(exc).__name__,
            run_id=config.fingerprint.value,
        )
    payload = {
        "class": _PAYLOAD_CLASS,
        "run_id": config.fingerprint.value,
        "config": _encode_config(config),
        "slices": encoded_slices.value,
    }
    try:
        _write_json(directory / PAYLOAD_NAME, payload)
    except OSError as exc:
        _cleanup_unstarted(directory)
        return unavailable(
            "payload",
            "the orchestrator could not write the isolated run payload",
            given=type(exc).__name__,
            run_id=config.fingerprint.value,
        )
    try:
        process = subprocess.Popen(
            [sys.executable, "-B", "-m", WORKER_MODULE, str(directory)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=_child_env(),
            start_new_session=True,
        )
    except OSError as exc:
        _cleanup_unstarted(directory)
        return unavailable(
            "spawn_process",
            "stdlib process management could not spawn the isolated run process",
            given=type(exc).__name__,
            run_id=config.fingerprint.value,
        )
    return Ok(
        LiveSpawn(
            run_id=config.fingerprint,
            output_dir=str(directory),
            pid=process.pid,
            process=process,
        )
    )


def collect_run(live: object) -> Result[IsolatedRun]:
    """Wait for a live process and read the isolated result file."""
    if not isinstance(live, LiveSpawn):
        return invalid(
            "live",
            "collect_run waits on a LiveSpawn started by start_run",
            given=repr(type(live).__name__),
        )
    process = live.process
    stderr = ""
    if process.returncode is None:
        _stdout, captured_err = process.communicate()
        del _stdout
        stderr = captured_err or ""
    if process.returncode not in (0, None) and not (Path(live.output_dir) / RESULT_NAME).is_file():
        return unavailable(
            "spawn_process",
            "the isolated run process exited without a result file",
            returncode=process.returncode,
            stderr=stderr[-2000:],
            run_id=live.run_id.value,
            output_dir=live.output_dir,
        )
    envelope = _read_json(Path(live.output_dir) / RESULT_NAME)
    if is_refusal(envelope):
        return envelope
    return _isolated_from_envelope(live, envelope.value)


def worker_main(argv: Sequence[str] | None = None) -> int:
    """Child entry: drive pure ``run()`` and write only into the run directory."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        return 2
    return _run_worker(Path(args[0]))


def _run_worker(output_dir: Path) -> int:
    loaded = _read_json(output_dir / PAYLOAD_NAME)
    if is_refusal(loaded):
        return _write_envelope(output_dir, _refusal_envelope(loaded))
    decoded = _decode_payload(loaded.value)
    if is_refusal(decoded):
        return _write_envelope(output_dir, _refusal_envelope(decoded))
    config, slices = decoded.value
    try:
        _write_json(
            output_dir / WRITER_NAME,
            {
                "run_id": config.fingerprint.value,
                "pid": os.getpid(),
                "output_dir": str(output_dir.resolve()),
            },
        )
    except OSError:
        return 1
    outcome = run(slices=slices, config=config)
    if is_refusal(outcome):
        return _write_envelope(output_dir, _refusal_envelope(outcome))
    stamped = outcome.value.ct32_fingerprint()
    envelope: dict[str, object] = {
        "ok": True,
        "run_id": config.fingerprint.value,
        "worker_pid": os.getpid(),
        "output_dir": str(output_dir.resolve()),
        "outcome": outcome.value.fp1_identity(),
    }
    if not is_refusal(stamped):
        envelope["ct32_fingerprint"] = stamped.value.value
    return _write_envelope(output_dir, envelope)


def _isolated_from_envelope(
    live: LiveSpawn,
    envelope: Mapping[str, object],
) -> Result[IsolatedRun]:
    ok = envelope.get("ok")
    if ok is False:
        refusal = _typed_refusal_from_envelope(envelope)
        if refusal is None:
            return unavailable(
                "spawn_process",
                "the isolated run wrote a refusal envelope without CT-04 fields",
                run_id=live.run_id.value,
            )
        return refusal
    if ok is not True:
        return unavailable(
            "spawn_process",
            "the isolated run envelope must set ok true or false",
            run_id=live.run_id.value,
        )
    run_id = _as_run_id(envelope.get("run_id"))
    if is_refusal(run_id):
        return run_id
    if run_id.value != live.run_id:
        return invalid(
            "run_id",
            "the isolated result must carry the run id the orchestrator spawned",
            spawned=live.run_id.value,
            written=run_id.value.value,
        )
    worker_pid = envelope.get("worker_pid")
    if not isinstance(worker_pid, int) or isinstance(worker_pid, bool) or worker_pid <= 0:
        return unavailable(
            "spawn_process",
            "the isolated worker reports a positive pid",
            given=repr(worker_pid),
        )
    ct32: Fingerprint | None = None
    raw_fp = envelope.get("ct32_fingerprint")
    if raw_fp is not None:
        parsed_fp = Fingerprint.try_create(raw_fp)
        if is_refusal(parsed_fp):
            return parsed_fp
        ct32 = parsed_fp.value
    outcome = envelope.get("outcome")
    if not isinstance(outcome, Mapping):
        return unavailable(
            "spawn_process",
            "the isolated run envelope carries the pure run() outcome identity",
            given=repr(type(outcome).__name__),
        )
    return Ok(
        IsolatedRun(
            run_id=run_id.value,
            output_dir=live.output_dir,
            pid=live.pid,
            worker_pid=worker_pid,
            ct32_fingerprint=ct32,
            outcome_identity=cast("Mapping[str, object]", outcome),
        )
    )


def _coerce_jobs(jobs: object) -> Result[tuple[SpawnJob, ...]]:
    if isinstance(jobs, SpawnJob):
        bound = _bind_job(
            jobs.config,
            jobs.slices,
            jobs.projected_peak_memory,
            jobs.cpu_cost,
        )
        if is_refusal(bound):
            return bound
        return Ok((bound.value,))
    if isinstance(jobs, (str, bytes)) or not isinstance(jobs, Sequence):
        return invalid(
            "jobs",
            "spawn_concurrent takes a sequence of SpawnJob values or config/slices mappings",
            given=repr(type(jobs).__name__),
        )
    parsed: list[SpawnJob] = []
    for index, raw in enumerate(cast("Sequence[object]", jobs)):
        item = _coerce_job(raw)
        if is_refusal(item):
            extra = dict(item.context)
            extra["index"] = index
            return TypedRefusal(
                category=item.category,
                retryability=item.retryability,
                context=extra,
                after_condition_descriptor=item.after_condition_descriptor,
            )
        parsed.append(item.value)
    return Ok(tuple(parsed))


def _coerce_job(raw: object) -> Result[SpawnJob]:
    if isinstance(raw, SpawnJob):
        return _bind_job(
            raw.config,
            raw.slices,
            raw.projected_peak_memory,
            raw.cpu_cost,
        )
    if not isinstance(raw, Mapping):
        return invalid(
            "jobs",
            "each job is a SpawnJob or a mapping with config and slices",
            given=repr(type(raw).__name__),
        )
    mapping = cast("Mapping[str, object]", raw)
    return _bind_job(
        mapping.get("config"),
        mapping.get("slices"),
        mapping.get("projected_peak_memory"),
        mapping.get("cpu_cost", 1),
    )


def _bind_job(
    config: object,
    slices: object,
    projected_peak_memory: object = None,
    cpu_cost: object = 1,
) -> Result[SpawnJob]:
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "the orchestrator drives the library run() over a resolved run-config",
            given=repr(type(config).__name__),
        )
    encoded = _encode_slices(slices)
    if is_refusal(encoded):
        return encoded
    peak: int | None
    if projected_peak_memory is None:
        peak = None
    else:
        parsed_peak = _positive_int("projected_peak_memory", projected_peak_memory)
        if is_refusal(parsed_peak):
            return parsed_peak
        peak = parsed_peak.value
    parsed_cost = _positive_int("cpu_cost", cpu_cost)
    if is_refusal(parsed_cost):
        return parsed_cost
    return Ok(
        SpawnJob(
            config=config,
            slices=slices,
            projected_peak_memory=peak,
            cpu_cost=parsed_cost.value,
        )
    )


def _drain_governed(
    items: tuple[SpawnJob, ...],
    governor: ResourceGovernor,
    output_root: object,
) -> Result[tuple[IsolatedRun, ...]]:
    by_id = {job.config.fingerprint.value: job for job in items}
    live: dict[str, LiveSpawn] = {}
    collected: dict[str, IsolatedRun] = {}
    for request in governor.running:
        started = _start_job(by_id[request.run_id.value], output_root, live)
        if is_refusal(started):
            return started
    while live:
        finished = _wait_any(tuple(live.values()))
        token = finished.run_id.value
        done = collect_run(finished)
        if is_refusal(done):
            del live[token]
            _reap_live(tuple(live.values()))
            return done
        collected[token] = done.value
        del live[token]
        admitted = governor.release(finished.run_id)
        if is_refusal(admitted):
            _reap_live(tuple(live.values()))
            return admitted
        for admission in admitted.value:
            started = _start_job(by_id[admission.run_id.value], output_root, live)
            if is_refusal(started):
                return started
    order = [job.config.fingerprint.value for job in items]
    return Ok(tuple(collected[token] for token in order))


def _start_job(
    job: SpawnJob,
    output_root: object,
    live: dict[str, LiveSpawn],
) -> Result[None]:
    started = start_run(config=job.config, slices=job.slices, output_root=output_root)
    if is_refusal(started):
        _reap_live(tuple(live.values()))
        return started
    live[job.config.fingerprint.value] = started.value
    return Ok(None)


def _wait_any(live: Sequence[LiveSpawn]) -> LiveSpawn:
    items = tuple(live)
    if not items:
        raise RuntimeError("governor drain waited on no live run")
    for item in items:
        if item.process.poll() is not None:
            return item
    first = items[0]
    first.process.wait()
    return first


def _request_for_job(job: SpawnJob, default_peak: object) -> Result[GovernedRequest]:
    peak: object = job.projected_peak_memory
    if peak is None:
        peak = default_peak
    return GovernedRequest.try_create(job.config.fingerprint, peak, job.cpu_cost)


def _positive_int(field: str, value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(
            field,
            "a governor quantity is a positive integer declared by the caller",
            given=repr(value),
        )
    return Ok(value)


def _encode_config(config: ResolvedRunConfig) -> dict[str, object]:
    payload: dict[str, object] = {
        "format_version": config.format_version,
        "book_fp1": config.book_fp1.value,
        "bms_fp1": config.bms_fp1.value,
        "bot_fp1": config.bot_fp1.value,
        "book_fragment_fp1": config.book_fragment_fp1.value,
        "bms_fragment_fp1": config.bms_fragment_fp1.value,
        "keys": _jsonable(dict(config.keys)),
        "clock": config.clock,
        "data_provenance": config.data_provenance,
        "world": config.world.value,
        "fingerprint": config.fingerprint.value,
    }
    if config.binding_fp1 is not None:
        payload["binding_fp1"] = config.binding_fp1.value
    if config.condition_preset_fp1:
        payload["condition_preset_fp1"] = [item.value for item in config.condition_preset_fp1]
    return payload


def _encode_slices(slices: object) -> Result[list[list[dict[str, object]]]]:
    if isinstance(slices, (str, bytes)) or not isinstance(slices, Sequence):
        return invalid(
            "slices",
            "a spawned run feeds run() a sequence of event slices",
            given=repr(type(slices).__name__),
        )
    encoded: list[list[dict[str, object]]] = []
    for item in cast("Sequence[object]", slices):
        parsed = EventSlice.try_create(item)
        if is_refusal(parsed):
            return parsed
        encoded.append([dict(obs.fp1_identity()) for obs in parsed.value.observations])
    if not encoded:
        return invalid(
            "slices",
            "a spawned run feeds run() at least one event slice",
        )
    return Ok(encoded)


def _decode_payload(
    raw: object,
) -> Result[tuple[ResolvedRunConfig, tuple[tuple[SliceObservation, ...], ...]]]:
    if not isinstance(raw, Mapping):
        return invalid(
            "payload",
            "the isolated worker payload is a mapping",
            given=repr(type(raw).__name__),
        )
    mapping = cast("Mapping[str, object]", raw)
    if mapping.get("class") != _PAYLOAD_CLASS:
        return invalid(
            "class",
            "the isolated worker payload names class qmb-orchestrator-payload-v1",
            given=repr(mapping.get("class")),
        )
    config = _decode_config(mapping.get("config"))
    if is_refusal(config):
        return config
    slices = _decode_slices(mapping.get("slices"))
    if is_refusal(slices):
        return slices
    return Ok((config.value, slices.value))


def _decode_config(raw: object) -> Result[ResolvedRunConfig]:
    if not isinstance(raw, Mapping):
        return invalid(
            "config",
            "the isolated payload config is a mapping",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    version = body.get("format_version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        return invalid(
            "format_version",
            "a resolved run-config format version is a positive integer ordinal",
            given=repr(version),
        )
    book = _require_fingerprint(body.get("book_fp1"), "book_fp1")
    if is_refusal(book):
        return book
    bms = _require_fingerprint(body.get("bms_fp1"), "bms_fp1")
    if is_refusal(bms):
        return bms
    bot = _require_fingerprint(body.get("bot_fp1"), "bot_fp1")
    if is_refusal(bot):
        return bot
    book_frag = _require_fingerprint(body.get("book_fragment_fp1"), "book_fragment_fp1")
    if is_refusal(book_frag):
        return book_frag
    bms_frag = _require_fingerprint(body.get("bms_fragment_fp1"), "bms_fragment_fp1")
    if is_refusal(bms_frag):
        return bms_frag
    stamp = _require_fingerprint(body.get("fingerprint"), "fingerprint")
    if is_refusal(stamp):
        return stamp
    clock = body.get("clock")
    provenance = body.get("data_provenance")
    if not isinstance(clock, str) or not isinstance(provenance, str):
        return invalid(
            "config",
            "clock and data_provenance are strings on a resolved run-config",
        )
    world_token = body.get("world")
    if not isinstance(world_token, str):
        return invalid("world", "world is live, replay, or simulated", given=repr(world_token))
    try:
        world = World(world_token)
    except ValueError:
        return invalid("world", "world is live, replay, or simulated", given=world_token)
    keys = _restore_keys(body.get("keys"))
    if is_refusal(keys):
        return keys
    binding: Fingerprint | None = None
    if "binding_fp1" in body:
        bound = _require_fingerprint(body.get("binding_fp1"), "binding_fp1")
        if is_refusal(bound):
            return bound
        binding = bound.value
    presets: tuple[Fingerprint, ...] = ()
    if "condition_preset_fp1" in body:
        raw_presets = body.get("condition_preset_fp1")
        if not isinstance(raw_presets, Sequence) or isinstance(raw_presets, (str, bytes)):
            return invalid(
                "condition_preset_fp1",
                "condition_preset_fp1 is a sequence of fingerprints",
            )
        parsed_presets: list[Fingerprint] = []
        for item in cast("Sequence[object]", raw_presets):
            preset = _require_fingerprint(item, "condition_preset_fp1")
            if is_refusal(preset):
                return preset
            parsed_presets.append(preset.value)
        presets = tuple(parsed_presets)
    return Ok(
        ResolvedRunConfig(
            format_version=version,
            book_fp1=book.value,
            bms_fp1=bms.value,
            bot_fp1=bot.value,
            book_fragment_fp1=book_frag.value,
            bms_fragment_fp1=bms_frag.value,
            keys=keys.value,
            clock=clock,
            data_provenance=provenance,
            world=world,
            fingerprint=stamp.value,
            binding_fp1=binding,
            condition_preset_fp1=presets,
        )
    )


def _decode_slices(
    raw: object,
) -> Result[tuple[tuple[SliceObservation, ...], ...]]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return invalid(
            "slices",
            "the isolated payload slices are a sequence of observation sequences",
            given=repr(type(raw).__name__),
        )
    slices: list[tuple[SliceObservation, ...]] = []
    for item in cast("Sequence[object]", raw):
        if not isinstance(item, Sequence) or isinstance(item, (str, bytes)):
            return invalid(
                "slices",
                "each event slice is a sequence of observations",
                given=repr(type(item).__name__),
            )
        observations: list[SliceObservation] = []
        for obs_raw in cast("Sequence[object]", item):
            parsed = _decode_observation(obs_raw)
            if is_refusal(parsed):
                return parsed
            observations.append(parsed.value)
        slices.append(tuple(observations))
    if not slices:
        return invalid("slices", "a spawned run feeds run() at least one event slice")
    return Ok(tuple(slices))


def _decode_observation(raw: object) -> Result[SliceObservation]:
    if not isinstance(raw, Mapping):
        return invalid(
            "slices",
            "a slice observation is a mapping",
            given=repr(type(raw).__name__),
        )
    mapping = cast("Mapping[str, object]", raw)
    ns = mapping.get("instant_ns")
    if not isinstance(ns, int) or isinstance(ns, bool):
        return invalid(
            "instant_ns",
            "a slice observation carries instant_ns as an int64 nanosecond count",
            given=repr(ns),
        )
    instant = Instant.try_create(ns)
    if is_refusal(instant):
        return instant
    return SliceObservation.try_create(
        mapping.get("stream_id"),
        instant.value,
        mapping.get("closed", True),
    )


def _restore_keys(raw: object) -> Result[dict[str, object]]:
    if not isinstance(raw, Mapping):
        return invalid(
            "keys",
            "resolved run-config keys are a mapping",
            given=repr(type(raw).__name__),
        )
    keys: dict[str, object] = {}
    for key, value in cast("Mapping[object, object]", raw).items():
        keys[str(key)] = value
    streams = keys.get(STREAM_SET_KEY)
    if isinstance(streams, list):
        keys[STREAM_SET_KEY] = tuple(cast("list[object]", streams))
    return Ok(keys)


def _require_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    if isinstance(value, str):
        return Fingerprint.try_create(value)
    return invalid(
        field,
        "a fingerprint is the string fp1:sha256:<hex>",
        given=repr(value),
    )


def _as_run_id(value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    if isinstance(value, str):
        return Fingerprint.try_create(value)
    return invalid(
        "run_id",
        "the run id is the resolved-config fingerprint",
        given=repr(type(value).__name__),
    )


def _as_output_root(value: object) -> Result[Path]:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value.strip() != "":
        root = Path(value)
    else:
        return invalid(
            "output_root",
            "the orchestrator writes isolated run directories under an existing output root",
            given=repr(type(value).__name__),
        )
    if not root.is_dir():
        return invalid(
            "output_root",
            "the orchestrator writes isolated run directories under an existing output root",
            given=str(root),
        )
    return Ok(root)


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    extra = [item for item in sys.path if item]
    existing = env.get("PYTHONPATH", "")
    merged = extra + ([existing] if existing else [])
    env["PYTHONPATH"] = os.pathsep.join(merged)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, Fingerprint):
        return value.value
    if isinstance(value, World):
        return value.value
    identity = getattr(value, "fp1_identity", None)
    if callable(identity):
        return _jsonable(identity())
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {str(key): _jsonable(item) for key, item in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items = cast("Sequence[object]", value)
        return [_jsonable(item) for item in items]
    return str(value)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False),
        encoding="utf-8",
        newline="\n",
    )


def _write_envelope(output_dir: Path, payload: Mapping[str, object]) -> int:
    try:
        _write_json(output_dir / RESULT_NAME, payload)
    except OSError:
        return 1
    return 0


def _read_json(path: Path) -> Result[dict[str, object]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return unavailable(
            "result",
            "the isolated run did not write its result file",
            given=type(exc).__name__,
            path=str(path),
        )
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError:
        return unavailable(
            "result",
            "the isolated run result is JSON",
            path=str(path),
        )
    if not isinstance(parsed, dict):
        return unavailable(
            "result",
            "the isolated run result is a mapping",
            given=type(parsed).__name__,
        )
    return Ok(cast("dict[str, object]", parsed))


def _refusal_envelope(refusal: TypedRefusal) -> dict[str, object]:
    envelope: dict[str, object] = {
        "ok": False,
        "category": refusal.category.value,
        "retryability": refusal.retryability.value,
        "context": _jsonable(dict(refusal.context)),
        "worker_pid": os.getpid(),
    }
    if refusal.after_condition_descriptor is not None:
        envelope["after_condition_descriptor"] = refusal.after_condition_descriptor
    return envelope


def _typed_refusal_from_envelope(envelope: Mapping[str, object]) -> TypedRefusal | None:
    category = envelope.get("category")
    retryability = envelope.get("retryability", Retryability.NO.value)
    context = envelope.get("context", {})
    if not isinstance(category, str) or not isinstance(retryability, str):
        return None
    if not isinstance(context, Mapping):
        return None
    try:
        parsed_category = RefusalCategory(category)
        parsed_retry = Retryability(retryability)
    except ValueError:
        return None
    descriptor = envelope.get("after_condition_descriptor")
    if descriptor is not None and not isinstance(descriptor, str):
        descriptor = None
    return TypedRefusal(
        category=parsed_category,
        retryability=parsed_retry,
        context=dict(cast("Mapping[str, object]", context)),
        after_condition_descriptor=descriptor,
    )


def _cleanup_unstarted(directory: Path) -> None:
    payload = directory / PAYLOAD_NAME
    if payload.is_file():
        payload.unlink()
    try:
        directory.rmdir()
    except OSError:
        return


def _reap_live(live: Sequence[LiveSpawn]) -> None:
    for item in live:
        process = item.process
        if process.returncode is None:
            process.kill()
        try:
            process.communicate()
        except OSError:
            continue
