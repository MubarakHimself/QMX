"""Story 15.1 — process-per-run via stdlib with isolated output directories."""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from typing import Any, TypeVar, cast

from qmb.config import ResolvedRunConfig, artifact_relative_path
from qmb.doors import api
from qmb.orchestrator import spawn as spawn_mod
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_RUNLOOP = _SRC / "runloop"
_ORCH = _SRC / "orchestrator"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS, *, closed: bool = True) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), closed))


def _slices(
    streams: tuple[str, ...] = ("eurusd", "gbpusd"),
) -> tuple[tuple[SliceObservation, ...], ...]:
    first = tuple(_obs(stream_id, _NS) for stream_id in streams)
    second = tuple(_obs(stream_id, _NS + 1) for stream_id in streams)
    return (first, second)


def _config(*, tag: str, streams: tuple[str, ...] = ("eurusd", "gbpusd")) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "orch-spawn", "tag": tag, "streams": list(streams)}))
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: streams},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _imported_roots(directory: Path) -> set[str]:
    imported: set[str] = set()
    for path in sorted(directory.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".", 1)[0])
    return imported


def test_identity_names_stdlib_process_per_run_without_ray_docker_or_daemon() -> None:
    identity = qmb.orchestrator_identity()
    assert identity["impure_owner"] == qmb.IMPURE_OWNER == "orchestrator"
    assert identity["spawn_model"] == qmb.SPAWN_MODEL == "process-per-run"
    assert identity["process_management"] == qmb.PROCESS_MANAGEMENT == "stdlib.subprocess"
    assert identity["ray"] == qmb.RAY == "absent"
    assert identity["docker"] == qmb.DOCKER == "not-required"
    assert identity["daemon"] == qmb.DAEMON == "not-required"
    assert identity["one_writer_per_stream"] is qmb.ONE_WRITER_PER_STREAM is True
    assert qmb.__version__ not in identity.values()
    assert api.spawn_run is qmb.spawn_run
    assert api.start_run is qmb.start_run
    assert api.collect_run is qmb.collect_run
    assert api.spawn_concurrent is qmb.spawn_concurrent
    assert api.IsolatedRun is qmb.IsolatedRun


def test_runloop_stays_pure_and_orchestrator_owns_subprocess() -> None:
    runloop_imports = _imported_roots(_RUNLOOP)
    orch_imports = _imported_roots(_ORCH)
    assert "subprocess" not in runloop_imports
    assert "threading" not in runloop_imports
    assert "multiprocessing" not in runloop_imports
    assert "concurrent" not in runloop_imports
    assert "subprocess" in orch_imports
    assert "threading" not in orch_imports
    assert "multiprocessing" not in orch_imports
    assert "ray" not in orch_imports
    assert "docker" not in orch_imports
    source = (_ORCH / "spawn.py").read_text(encoding="utf-8")
    assert "subprocess.Popen" in source
    assert "stdlib.subprocess" in source
    assert "not-required" in source


def test_run_directory_name_is_the_run_id_with_colons_made_filesystem_safe() -> None:
    config = _config(tag="dir")
    named = _ok(qmb.run_directory_name(config.fingerprint))
    assert ":" not in named
    assert named == config.fingerprint.value.replace(":", "-")
    relative = artifact_relative_path(config.fingerprint)
    assert relative.startswith(named + "/")
    refused = qmb.run_directory_name("not-a-fingerprint")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_spawn_run_is_a_separate_os_process_in_a_run_id_directory(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    config = _config(tag="one")
    slices = _slices()
    recorded: dict[str, object] = {}
    real_popen = spawn_mod.subprocess.Popen

    def wrapped(*args: Any, **kwargs: Any) -> Any:
        argv = args[0] if args else kwargs.get("args")
        recorded["argv"] = list(cast("list[object]", argv))
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(spawn_mod.subprocess, "Popen", wrapped)
    isolated = _ok(qmb.spawn_run(config=config, slices=slices, output_root=tmp_path))
    argv = recorded["argv"]
    assert isinstance(argv, list)
    tokens = [str(item) for item in cast("list[object]", argv)]
    assert tokens[0] == sys.executable
    assert "-m" in tokens
    assert "qmb.orchestrator.worker" in tokens
    lowered = [item.lower() for item in tokens]
    assert "ray" not in lowered
    assert "docker" not in lowered
    directory = Path(isolated.output_dir)
    assert directory.resolve().parent == tmp_path.resolve()
    assert directory.name == _ok(qmb.run_directory_name(config.fingerprint))
    assert isolated.pid != os.getpid()
    assert isolated.worker_pid != os.getpid()
    assert isolated.worker_pid > 0
    assert isolated.run_id == config.fingerprint
    assert (directory / qmb.PAYLOAD_NAME).is_file()
    assert (directory / qmb.RESULT_NAME).is_file()
    writer = json.loads((directory / qmb.WRITER_NAME).read_text(encoding="utf-8"))
    assert writer["pid"] == isolated.worker_pid
    assert writer["run_id"] == config.fingerprint.value
    in_process = _ok(run(slices=slices, config=config, handler=SilentSliceHandler()))
    assert isolated.outcome_identity == in_process.fp1_identity()
    assert isolated.ct32_fingerprint == _ok(in_process.ct32_fingerprint())


def test_pure_run_writes_no_output_directory(tmp_path: Path) -> None:
    config = _config(tag="pure")
    _ok(run(slices=_slices(), config=config, handler=SilentSliceHandler()))
    assert list(tmp_path.iterdir()) == []


def test_invalid_config_and_missing_root_are_typed_refusals(tmp_path: Path) -> None:
    refused = qmb.spawn_run(config="nope", slices=_slices(), output_root=tmp_path)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "config"
    missing = qmb.spawn_run(
        config=_config(tag="missing-root"),
        slices=_slices(),
        output_root=tmp_path / "absent",
    )
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT
    assert missing.context["field"] == "output_root"


def test_existing_run_directory_is_one_writer_policy_rejection(tmp_path: Path) -> None:
    config = _config(tag="reuse")
    first = _ok(qmb.spawn_run(config=config, slices=_slices(), output_root=tmp_path))
    again = qmb.spawn_run(config=config, slices=_slices(), output_root=tmp_path)
    assert is_refusal(again)
    assert again.category is RefusalCategory.POLICY_REJECTION
    assert again.context["field"] == "output_dir"
    assert Path(first.output_dir).is_dir()


def test_two_concurrent_runs_never_share_a_writer(tmp_path: Path) -> None:
    first_config = _config(tag="alpha")
    second_config = _config(tag="beta")
    slices = _slices()
    live_a = _ok(qmb.start_run(config=first_config, slices=slices, output_root=tmp_path))
    live_b = _ok(qmb.start_run(config=second_config, slices=slices, output_root=tmp_path))
    assert live_a.pid != live_b.pid
    assert live_a.pid != os.getpid()
    assert live_b.pid != os.getpid()
    assert live_a.output_dir != live_b.output_dir
    assert Path(live_a.output_dir).name == _ok(qmb.run_directory_name(first_config.fingerprint))
    assert Path(live_b.output_dir).name == _ok(qmb.run_directory_name(second_config.fingerprint))
    done_a = _ok(qmb.collect_run(live_a))
    done_b = _ok(qmb.collect_run(live_b))
    writer_a = json.loads((Path(done_a.output_dir) / qmb.WRITER_NAME).read_text(encoding="utf-8"))
    writer_b = json.loads((Path(done_b.output_dir) / qmb.WRITER_NAME).read_text(encoding="utf-8"))
    assert writer_a["pid"] != writer_b["pid"]
    assert writer_a["output_dir"] != writer_b["output_dir"]
    assert writer_a["run_id"] != writer_b["run_id"]
    assert not (Path(done_a.output_dir) / qmb.RESULT_NAME).samefile(
        Path(done_b.output_dir) / qmb.RESULT_NAME
    )
    in_a = _ok(run(slices=slices, config=first_config, handler=SilentSliceHandler()))
    in_b = _ok(run(slices=slices, config=second_config, handler=SilentSliceHandler()))
    assert done_a.outcome_identity == in_a.fp1_identity()
    assert done_b.outcome_identity == in_b.fp1_identity()


def test_spawn_concurrent_refuses_duplicate_run_ids(tmp_path: Path) -> None:
    config = _config(tag="dup")
    slices = _slices()
    refused = qmb.spawn_concurrent(
        (
            qmb.SpawnJob(config=config, slices=slices),
            qmb.SpawnJob(config=config, slices=slices),
        ),
        output_root=tmp_path,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "run_id"
    assert list(tmp_path.iterdir()) == []


def test_spawn_concurrent_two_jobs_match_in_process(tmp_path: Path) -> None:
    first = _config(tag="batch-a")
    second = _config(tag="batch-b")
    slices = _slices()
    isolated = _ok(
        qmb.spawn_concurrent(
            (
                {"config": first, "slices": slices},
                {"config": second, "slices": slices},
            ),
            output_root=tmp_path,
        )
    )
    assert len(isolated) == 2
    assert isolated[0].pid != isolated[1].pid
    assert isolated[0].output_dir != isolated[1].output_dir
    in_first = _ok(run(slices=slices, config=first, handler=SilentSliceHandler()))
    in_second = _ok(run(slices=slices, config=second, handler=SilentSliceHandler()))
    assert isolated[0].outcome_identity == in_first.fp1_identity()
    assert isolated[1].outcome_identity == in_second.fp1_identity()
    assert isolated[0].ct32_fingerprint == _ok(in_first.ct32_fingerprint())
    assert isolated[1].ct32_fingerprint == _ok(in_second.ct32_fingerprint())


def test_worker_main_requires_the_isolated_output_directory() -> None:
    from qmb.orchestrator import worker_main

    assert worker_main([]) == 2
    assert worker_main(["one", "two"]) == 2


def test_worker_main_writes_refusal_when_payload_is_missing(tmp_path: Path) -> None:
    from qmb.orchestrator import worker_main

    assert worker_main([str(tmp_path)]) == 0
    envelope = json.loads((tmp_path / qmb.RESULT_NAME).read_text(encoding="utf-8"))
    assert envelope["ok"] is False
    assert envelope["category"] == RefusalCategory.UNAVAILABLE_DEPENDENCY.value


def test_worker_main_refuses_unknown_payload_class(tmp_path: Path) -> None:
    from qmb.orchestrator import worker_main

    (tmp_path / qmb.PAYLOAD_NAME).write_text(
        json.dumps({"class": "not-the-payload"}),
        encoding="utf-8",
        newline="\n",
    )
    assert worker_main([str(tmp_path)]) == 0
    envelope = json.loads((tmp_path / qmb.RESULT_NAME).read_text(encoding="utf-8"))
    assert envelope["ok"] is False
    assert envelope["category"] == RefusalCategory.INVALID_INPUT.value
    assert envelope["context"]["field"] == "class"


def test_collect_run_and_empty_jobs_are_typed_refusals(tmp_path: Path) -> None:
    refused = qmb.collect_run("nope")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    empty = qmb.spawn_concurrent((), output_root=tmp_path)
    assert is_refusal(empty)
    assert empty.context["field"] == "jobs"
    not_jobs = qmb.spawn_concurrent("nope", output_root=tmp_path)
    assert is_refusal(not_jobs)
    assert not_jobs.context["field"] == "jobs"


def test_invalid_slices_refuse_before_spawn(tmp_path: Path) -> None:
    refused = qmb.spawn_run(config=_config(tag="slices"), slices="nope", output_root=tmp_path)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "slices"
    assert list(tmp_path.iterdir()) == []


def test_popen_failure_cleans_the_unstarted_directory(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    config = _config(tag="popen-fail")

    def boom(*_args: object, **_kwargs: object) -> object:
        raise OSError("spawn failed")

    monkeypatch.setattr(spawn_mod.subprocess, "Popen", boom)
    refused = qmb.start_run(config=config, slices=_slices(), output_root=tmp_path)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["field"] == "spawn_process"
    named = _ok(qmb.run_directory_name(config.fingerprint))
    assert not (tmp_path / named).exists()


def test_spawn_concurrent_reaps_started_jobs_when_a_later_job_is_refused(
    tmp_path: Path,
) -> None:
    first = _config(tag="reap-a")
    second = _config(tag="reap-b")
    named = _ok(qmb.run_directory_name(second.fingerprint))
    (tmp_path / named).mkdir()
    refused = qmb.spawn_concurrent(
        (
            qmb.SpawnJob(config=first, slices=_slices()),
            qmb.SpawnJob(config=second, slices=_slices()),
        ),
        output_root=tmp_path,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "output_dir"
