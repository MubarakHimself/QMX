"""Story 15.4 — one ledger line per run over WriterId-scoped JSONL fragments."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.doors import api
from qmb.ledger.line import LEDGER_LINE_CLASS
from qmb.runloop import (
    STREAM_SET_KEY,
    CancelToken,
    SilentSliceHandler,
    SliceObservation,
    run,
)
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, canonical_bytes, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_BOOT = "boot-1"
_MACHINE = "test-machine"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs("eurusd"),), (_obs("eurusd", _NS + 1),))


def _config(*, tag: str) -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "orch-ledger", "tag": tag}))
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _sink(tmp_path: Path, *, slot: object = 0) -> qmb.LedgerSink:
    return _ok(
        qmb.LedgerSink.try_create(
            tmp_path / "ledger",
            machine=_MACHINE,
            worker_slot=slot,
            boot_epoch_id=_BOOT,
        )
    )


def test_ledger_identity_names_one_jsonl_line_and_no_verdict() -> None:
    identity = qmb.ledger_identity()
    assert identity["run_roles"] == qmb.RUN_ROLES
    assert identity["run_roles"] == (
        qmb.ROLE_CONFIRMATION,
        qmb.ROLE_TRIAL,
        qmb.ROLE_REPLICATE,
        qmb.ROLE_ABORTED,
    )
    assert identity["fragment_kind"] == "jsonl"
    assert identity["one_line_per_run"] is qmb.ONE_LINE_PER_RUN is True
    assert identity["stores_verdict"] is qmb.STORES_VERDICT is False
    assert identity["book_bar_read_role"] == qmb.BOOK_BAR_READ_ROLE == qmb.ROLE_CONFIRMATION
    assert identity["writer_scope"] == ("machine", "role", "worker-slot")
    assert identity["line_class"] == LEDGER_LINE_CLASS
    assert qmb.__version__ not in identity.values()
    assert api.finish_run is qmb.finish_run
    assert api.LedgerSink is qmb.LedgerSink
    assert api.read_book_bar is qmb.read_book_bar
    assert api.LedgerLine is qmb.LedgerLine
    orch = qmb.orchestrator_identity()
    assert orch["ledger_writes"] == qmb.IMPURE_OWNER
    assert orch["ledger_fragment"] == qmb.FRAGMENT_FILENAME
    assert orch["factory_sandbox_env"] == qmb.FACTORY_SANDBOX_ENV


def test_finished_run_appends_exactly_one_confirmation_line(tmp_path: Path) -> None:
    config = _config(tag="one")
    sink = _sink(tmp_path)
    live = _ok(qmb.start_run(config=config, slices=_slices(), output_root=tmp_path))
    done = _ok(qmb.finish_run(live, config=config, ledger=sink, role=qmb.ROLE_CONFIRMATION))
    assert done.run_id == config.fingerprint
    assert done.ct32_fingerprint is not None

    lines = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION))
    assert len(lines) == 1
    line = lines[0]
    assert line.run_id == config.fingerprint
    assert line.role == qmb.ROLE_CONFIRMATION
    assert line.world is World.REPLAY
    assert line.ct32_fingerprint == done.ct32_fingerprint
    assert line.refusal is None
    assert "verdict" not in line.fp1_identity()
    assert "pass" not in line.fp1_identity()
    assert "fail" not in line.fp1_identity()
    assert line.result_label["evidence_class"] == "provisional"
    assert line.result_label["world"] == World.REPLAY.value
    assert "provenance" not in line.result_label
    assert line.measures
    for measure in line.measures:
        assert "measure_identity" in measure
        if measure.get("class") == "undefined-measure":
            assert "refusal" in measure
            continue
        assert "unit_kind" in measure
    bar = _ok(qmb.book_bar_fingerprint(config))
    assert line.book_bar_fp1 == bar

    again = _ok(qmb.finish_run(live, config=config, ledger=sink, role=qmb.ROLE_CONFIRMATION))
    assert again.run_id == done.run_id
    tampered = qmb.LedgerLine(
        run_id=line.run_id,
        role=line.role,
        world=line.world,
        result_label=dict(line.result_label),
        book_bar_fp1=line.book_bar_fp1,
        measures=(),
        ct32_fingerprint=line.ct32_fingerprint,
    )
    collision = sink.append(tampered)
    assert is_refusal(collision)
    assert collision.category is RefusalCategory.POLICY_REJECTION
    still = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION))
    assert len(still) == 1
    assert still[0].fp1_identity() == line.fp1_identity()


def test_aborted_run_writes_one_line_with_refusal_context(tmp_path: Path) -> None:
    config = _config(tag="abort")
    sink = _sink(tmp_path)
    named = _ok(qmb.run_directory_name(config.fingerprint))
    directory = tmp_path / named
    directory.mkdir()
    import subprocess
    import sys

    from qmb.orchestrator.watch import monotonic_ns

    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    token = CancelToken()
    live = qmb.LiveSpawn(
        run_id=config.fingerprint,
        output_dir=str(directory),
        pid=process.pid,
        process=process,
        cancel=token,
        limits=qmb.RunLimits(),
        started_monotonic_ns=monotonic_ns(),
    )
    _ok(token.cancel())
    refused = qmb.finish_run(live, config=config, ledger=sink)
    assert is_refusal(refused)
    assert refused.context["terminal"] == "aborted"
    assert refused.context["writes_ledger"] is True
    assert refused.context["aborted_line_absent"] is False
    assert refused.context["ledger_role"] == qmb.ROLE_ABORTED

    aborted = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_ABORTED))
    assert len(aborted) == 1
    line = aborted[0]
    assert line.role == qmb.ROLE_ABORTED
    assert line.ct32_fingerprint is None
    assert line.refusal is not None
    assert line.refusal["category"] == RefusalCategory.POLICY_REJECTION.value
    assert line.refusal["cause"] == "cancel"
    assert line.refusal["terminal"] == "aborted"
    assert "provenance" not in line.result_label
    confirm = _ok(qmb.read_book_bar(sink.root, world=World.REPLAY))
    assert confirm == ()


def test_book_bar_read_selects_confirmation_only(tmp_path: Path) -> None:
    confirmation = _config(tag="bar-c")
    trial = _config(tag="bar-t")
    replicate = _config(tag="bar-r")
    sink = _sink(tmp_path, slot=0)
    other = _sink(tmp_path, slot=1)
    for config, role, bound in (
        (confirmation, qmb.ROLE_CONFIRMATION, sink),
        (trial, qmb.ROLE_TRIAL, other),
        (replicate, qmb.ROLE_REPLICATE, sink),
    ):
        live = _ok(qmb.start_run(config=config, slices=_slices(), output_root=tmp_path))
        _ok(qmb.finish_run(live, config=config, ledger=bound, role=role))

    bar = _ok(qmb.read_book_bar(sink.root, world=World.REPLAY))
    assert len(bar) == 1
    assert bar[0].role == qmb.ROLE_CONFIRMATION
    assert bar[0].run_id == confirmation.fingerprint
    trials = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_TRIAL))
    assert len(trials) == 1
    assert trials[0].run_id == trial.fingerprint
    replicates = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_REPLICATE))
    assert len(replicates) == 1


def test_concurrent_slots_never_share_a_fragment_file(tmp_path: Path) -> None:
    first = _config(tag="slot-a")
    second = _config(tag="slot-b")
    sink_a = _sink(tmp_path, slot=0)
    sink_b = _sink(tmp_path, slot=1)
    live_a = _ok(qmb.start_run(config=first, slices=_slices(), output_root=tmp_path))
    live_b = _ok(qmb.start_run(config=second, slices=_slices(), output_root=tmp_path))
    _ok(qmb.finish_run(live_a, config=first, ledger=sink_a, role=qmb.ROLE_CONFIRMATION))
    _ok(qmb.finish_run(live_b, config=second, ledger=sink_b, role=qmb.ROLE_CONFIRMATION))
    writer_a = _ok(sink_a.writer_id(qmb.ROLE_CONFIRMATION))
    writer_b = _ok(sink_b.writer_id(qmb.ROLE_CONFIRMATION))
    path_a = _ok(
        qmb.fragment_path(sink_a.root, writer_a, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION)
    )
    path_b = _ok(
        qmb.fragment_path(sink_b.root, writer_b, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION)
    )
    assert path_a != path_b
    assert path_a.is_file()
    assert path_b.is_file()
    assert writer_a.machine == writer_b.machine == _MACHINE
    assert writer_a.role == writer_b.role == qmb.ROLE_CONFIRMATION
    assert writer_a.stream != writer_b.stream
    merged = _ok(qmb.read_merge_view(sink_a.root, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION))
    assert {line.run_id for line in merged} == {first.fingerprint, second.fingerprint}


def test_fragment_line_is_fp1_canonical_and_lf_terminated(tmp_path: Path) -> None:
    config = _config(tag="canon")
    sink = _sink(tmp_path)
    live = _ok(qmb.start_run(config=config, slices=_slices(), output_root=tmp_path))
    _ok(qmb.finish_run(live, config=config, ledger=sink, role=qmb.ROLE_CONFIRMATION))
    writer = _ok(sink.writer_id(qmb.ROLE_CONFIRMATION))
    path = _ok(qmb.fragment_path(sink.root, writer, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION))
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r" not in raw
    payload = raw[:-1]
    lines = _ok(qmb.read_merge_view(sink.root, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION))
    expected = _ok(canonical_bytes(lines[0].fp1_identity()))
    assert payload == expected
    assert lines[0].fp1_identity()["class"] == LEDGER_LINE_CLASS


def test_factory_sandbox_stamps_provenance_sandbox(tmp_path: Path) -> None:
    config = _config(tag="sandbox")
    sink = _sink(tmp_path)
    live = _ok(qmb.start_run(config=config, slices=_slices(), output_root=tmp_path))
    _ok(
        qmb.finish_run(
            live,
            config=config,
            ledger=sink,
            role=qmb.ROLE_CONFIRMATION,
            factory_sandbox=True,
        )
    )
    lines = _ok(qmb.read_book_bar(sink.root, world=World.REPLAY))
    assert lines[0].result_label["provenance"] == qmb.PROVENANCE_SANDBOX == "sandbox"


def test_direct_library_run_writes_no_governed_ledger(tmp_path: Path) -> None:
    config = _config(tag="pure")
    outcome = _ok(run(slices=_slices(), config=config, handler=SilentSliceHandler()))
    assert outcome.ct32_fingerprint is not None or outcome.performance_result is not None
    assert list(tmp_path.rglob("*.jsonl")) == []
    source = (_SRC / "runloop" / "loop.py").read_text(encoding="utf-8")
    assert "writes no log and no ledger" in source
    tree = ast.parse((_SRC / "runloop" / "loop.py").read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert "qmb.orchestrator.ledger" not in imported
    assert "qmb.orchestrator" not in imported


def test_storage_refusal_helper_is_storage_failure() -> None:
    from qmb._refuse import storage

    refused = storage("ledger", "disk full")
    assert refused.category is RefusalCategory.STORAGE_FAILURE
