"""Story 27.7 — replay one recorded day as a credential-free decision diff."""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import TypeVar, cast

import pytest
from qmf.core import (
    Account,
    AccountRole,
    RefusalCategory,
    Result,
    SecretRef,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)
from qmn.config import compile_node_config
from qmn.data import CommittedHotPrefix, SealedArchive
from qmn.loop import CommandStreamLoop, clear_first_writer_registry
from qmn.mis.signal_snapshot import ProducerReadiness
from qmn.replay import (
    FILL_SIMULATION_IN_REPLAY,
    GAP_0056_DEFERRED,
    NODE_PROCESS_ENV,
    REPLAY_IMPORT_PORT,
    REPLAY_SURFACE,
    REPLAY_WRITER_ROLE_PREFIX,
    RecordedDay,
    RecordedSignalSnapshot,
    ReplayImportPort,
    ReplayJobSpec,
    allocate_replay_writer,
    attach_replay_to_loop,
    encode_recorded_day,
    refuse_admission_gate,
    refuse_command_submit,
    refuse_cross_world_write,
    refuse_fill_simulation,
    refuse_sqs_recompute,
    run_recorded_day,
    spawn_replay_job,
    writers_are_disjoint,
)
from qmn.venue import ReplayAdapter, VenueClientKind, select_venue_client

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_DEPLOY = _QMN_ROOT / "deploy"
_START = 1_725_300_000 * 1_000_000_000
_END = _START + 60_000_000_000
_STREAM = "eurusd"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


@pytest.fixture(autouse=True)
def reset_first_writer_registry() -> Iterator[None]:
    clear_first_writer_registry()
    yield
    clear_first_writer_registry()


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account() -> Account:
    return _ok(Account.try_create("acct-replay-1", _venue(), AccountRole.DEMO))


def _config_fp() -> str:
    return _ok(compile_node_config()).fingerprint.value


def _snapshot(
    *,
    frontier_ns: int = _START,
    readiness: ProducerReadiness = ProducerReadiness.OK,
    hard_block: bool = False,
) -> RecordedSignalSnapshot:
    return RecordedSignalSnapshot(
        frontier_ns=frontier_ns,
        environment="demo",
        feed_state="live",
        sqs_readiness=readiness,
        sqs_hard_block=hard_block,
        snapshot_fp1="fp1:sha256:" + ("ab" * 32),
        labeler_version="sqs-v1",
    )


def _day(
    *,
    composition_fp: str,
    readiness: ProducerReadiness = ProducerReadiness.OK,
    include_snapshot: bool = True,
    decision_refused: bool | None = None,
) -> RecordedDay:
    snapshot_block = readiness is not ProducerReadiness.OK
    if decision_refused is None:
        refused = (not include_snapshot) or snapshot_block
    else:
        refused = decision_refused
    snapshots = (
        (_snapshot(readiness=readiness, hard_block=snapshot_block),) if include_snapshot else ()
    )
    observation = {
        "kind": "spot",
        "observation_id": "obs-1",
        "stream_id": _STREAM,
        "receive_wall_time_ns": _START,
        "closed": True,
        "payload": {"bid": 1},
    }
    decision = {
        "kind": "decision",
        "frontier_ns": _START,
        "stream_id": _STREAM,
        "sqs_readiness": (
            readiness.value if include_snapshot else ProducerReadiness.NOT_READY.value
        ),
        "entry_refused": refused if include_snapshot else True,
    }
    control = {
        "kind": "interpretation-cursor-commit",
        "observation_id": "obs-1",
        "receive_wall_time_ns": _START,
        "event_type": "control action",
    }
    return RecordedDay(
        source_world=World.LIVE,
        venue_id=_venue(),
        account=_account(),
        stream_id=_STREAM,
        composition_fp=composition_fp,
        start_ns=_START,
        end_ns=_END,
        observations=(observation,),
        snapshots=snapshots,
        decisions=(decision,),
        controls=(control,),
        commands=(),
    )


def _seal(tmp_path: Path, day: RecordedDay) -> SealedArchive:
    archive = SealedArchive(tmp_path / "evidence")
    prefix = _ok(
        CommittedHotPrefix.try_create(
            world=World.LIVE,
            room_role="journal",
            prefix_id="recorded-day-1",
            start=day.start_ns,
            end=day.end_ns,
            payload=encode_recorded_day(day),
            committed=True,
        )
    )
    receipt = _ok(archive.sync(prefix))
    assert receipt.verified is True
    return archive


def _spec(tmp_path: Path, day: RecordedDay) -> ReplayJobSpec:
    port = ReplayImportPort(_seal(tmp_path, day))
    return _ok(
        ReplayJobSpec.try_create(
            import_port=port,
            source_world=World.LIVE,
            room_role="journal",
            prefix_id="recorded-day-1",
            start_ns=day.start_ns,
            end_ns=day.end_ns,
            composition_fp=day.composition_fp,
            machine="replay-host",
            boot_epoch_id="replay-boot-27-7",
        )
    )


def _load_deploy(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_surface_and_deferred_fill_simulation() -> None:
    assert REPLAY_SURFACE == "qmn.replay"
    assert REPLAY_IMPORT_PORT == "replay-import"
    assert FILL_SIMULATION_IN_REPLAY is False
    assert GAP_0056_DEFERRED is True
    refused = refuse_fill_simulation()
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "replay.fill_simulation"
    assert refused.context["gap"] == "GAP-0056"


def test_replay_selects_replay_port_without_socket_or_secret() -> None:
    selected = _ok(select_venue_client(World.REPLAY, _venue()))
    assert selected.kind is VenueClientKind.REPLAY
    client = _ok(ReplayAdapter.try_create(World.REPLAY, _venue(), recorded=()))
    assert client.socket_opened is False
    assert client.credential_resolved is False
    assert is_refusal(client.bind_credential(_ok(SecretRef.try_create("cred-ref-rpl27"))))


def test_disjoint_writer_namespace() -> None:
    live = _ok(
        WriterId.try_create(
            "vps-fra-01", "ctrader-adapter", "venue-ctrader-demo:acct-1", "boot-live"
        )
    )
    replay = _ok(
        allocate_replay_writer(
            machine="vps-fra-01",
            role="replay-adapter",
            stream="replay:venue-ctrader-demo:acct-1",
            boot_epoch_id="replay-boot",
        )
    )
    assert replay.role.startswith(REPLAY_WRITER_ROLE_PREFIX)
    assert writers_are_disjoint((replay,), (live,)) is True
    assert is_refusal(
        allocate_replay_writer(
            machine="vps-fra-01",
            role="ctrader-adapter",
            stream="replay:x",
            boot_epoch_id="replay-boot",
        )
    )


def test_import_port_is_read_only_and_reads_sealed_interval(tmp_path: Path) -> None:
    fp = _config_fp()
    day = _day(composition_fp=fp)
    archive = _seal(tmp_path, day)
    raw = _ok(
        archive.read_prefix(world=World.LIVE, room_role="journal", prefix_id="recorded-day-1")
    )
    assert b"qmn-replay-recorded-day" in raw
    port = ReplayImportPort(archive)
    assert port.writable is False
    loaded = _ok(
        port.read_interval(
            source_world=World.LIVE,
            room_role="journal",
            prefix_id="recorded-day-1",
            start_ns=_START,
            end_ns=_END,
        )
    )
    assert loaded.composition_fp == fp
    assert loaded.source_world is World.LIVE
    write = port.write(target_world=World.LIVE, payload={"x": 1})
    assert is_refusal(write)
    assert write.context["failure_id"] == "replay.cross_world_write"
    assert is_refusal(port.write_to_paper())
    assert is_refusal(refuse_cross_world_write(target_world="live"))


def test_missing_sealed_interval_refuses(tmp_path: Path) -> None:
    port = ReplayImportPort(SealedArchive(tmp_path / "empty-evidence"))
    refused = _refusal(
        port.read_interval(
            source_world=World.LIVE,
            room_role="journal",
            prefix_id="recorded-day-1",
            start_ns=_START,
            end_ns=_END,
        )
    )
    assert refused.context["failure_id"] == "replay.missing_sealed_interval"


def test_replay_job_requires_named_import_port() -> None:
    refused = ReplayJobSpec.try_create(
        import_port=object(),
        source_world=World.LIVE,
        room_role="journal",
        prefix_id="recorded-day-1",
        start_ns=_START,
        end_ns=_END,
        composition_fp="fp1:sha256:" + ("0" * 64),
    )
    assert is_refusal(refused)
    assert refused.context["failure_id"] == "replay.import_port_required"


def test_recorded_day_reuses_snapshots_and_diffs_clean(tmp_path: Path) -> None:
    fp = _config_fp()
    day = _day(composition_fp=fp)
    report = _ok(run_recorded_day(_spec(tmp_path, day)))
    assert report.world is World.REPLAY
    assert report.clean is True
    assert report.diagnostic_only is True
    assert report.admission_gate is False
    assert report.live_gate is False
    assert report.fill_simulation is False
    assert report.commands_submitted == 0
    assert report.commands_resent == 0
    assert report.sqs_recomputed is False
    assert report.socket_opened is False
    assert report.credential_resolved is False
    assert report.provenance["port"] == REPLAY_IMPORT_PORT
    assert all(bool(row.get("equal")) for row in report.decisions)
    assert all(bool(row.get("equal")) for row in report.controls)
    produced = cast("Mapping[str, object]", report.decisions[0]["produced"])
    assert produced["sqs_recomputed"] is False
    assert produced["entry_refused"] is False
    assert produced["world"] == World.REPLAY.value


def test_missing_snapshot_reads_not_ready_and_refuses_entry(tmp_path: Path) -> None:
    fp = _config_fp()
    day = _day(composition_fp=fp, include_snapshot=False)
    report = _ok(run_recorded_day(_spec(tmp_path, day)))
    produced = cast("Mapping[str, object]", report.decisions[0]["produced"])
    assert produced["sqs_readiness"] == ProducerReadiness.NOT_READY.value
    assert produced["entry_refused"] is True
    assert report.sqs_recomputed is False
    assert is_refusal(refuse_sqs_recompute(frontier_ns=_START))


def test_dirty_decision_diff_when_recorded_disagrees(tmp_path: Path) -> None:
    fp = _config_fp()
    day = _day(composition_fp=fp, decision_refused=True, readiness=ProducerReadiness.OK)
    report = _ok(run_recorded_day(_spec(tmp_path, day)))
    assert report.clean is False
    assert report.decisions[0]["equal"] is False


def test_in_node_process_and_attach_to_loop_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert is_refusal(attach_replay_to_loop(object()))
    monkeypatch.setenv(NODE_PROCESS_ENV, "1")
    fp = _config_fp()
    refused = _refusal(run_recorded_day(_spec(tmp_path, _day(composition_fp=fp))))
    assert refused.context["failure_id"] == "replay.in_node_process"


def test_composition_refuses_secrets_network_live_sink_and_submit() -> None:
    fp = _config_fp()
    day = _day(composition_fp=fp)
    # Drive a clean job so we can reuse composition refusals off the report.
    # Direct composition helpers:
    from qmf.core import DataDrivenClock, Instant
    from qmn.replay.session import ReplayComposition

    adapter = _ok(
        ReplayAdapter.try_create(
            World.REPLAY,
            _venue(),
            recorded=[
                {
                    "kind": "capability-profile",
                    "profile": {
                        "verified": True,
                        "command_sequencer_open": True,
                        "profile_version": 1,
                    },
                }
            ],
        )
    )
    writer = _ok(
        allocate_replay_writer(
            machine="replay-host",
            role="replay-adapter",
            stream="replay:venue-ctrader-demo:acct-replay-1",
            boot_epoch_id="replay-boot",
        )
    )
    wall = _ok(Instant.try_create(_START))
    clock = DataDrivenClock(boot_epoch_id="replay-boot", wall_instants=(wall,), monotonic_ns=(1,))
    composition = ReplayComposition(
        world=World.REPLAY,
        composition_fp=fp,
        venue_id=_venue(),
        account=_account(),
        writer=writer,
        venue_client=adapter,
        clock=clock,
        socket_opened=False,
        credential_resolved=False,
        live_sink=False,
        secrets_resolved=False,
    )
    assert is_refusal(composition.bind_credential(_ok(SecretRef.try_create("cred-ref-rpl27b"))))
    assert is_refusal(composition.bind_live_sink(object()))
    assert is_refusal(composition.open_network("ctrader"))
    assert is_refusal(composition.submit_or_resend(object()))
    assert is_refusal(composition.simulate_fills())
    assert composition.as_mapping()["fill_simulation"] is False
    del day


def test_diff_is_diagnostic_never_a_gate_or_restore() -> None:
    refused_gate = refuse_admission_gate(purpose="admission")
    assert refused_gate.context["failure_id"] == "replay.admission_gate"
    submit = refuse_command_submit(command=object())
    assert submit.context["failure_id"] == "replay.command_submit"
    fp = _config_fp()
    from types import MappingProxyType

    from qmn.replay.session import ReplayDiffReport

    report = ReplayDiffReport(
        world=World.REPLAY,
        composition_fp=fp,
        interval=MappingProxyType({"start_ns": _START, "end_ns": _END}),
        provenance=MappingProxyType({"port": REPLAY_IMPORT_PORT}),
        decisions=(),
        controls=(),
        commands=(),
        clean=True,
    )
    assert is_refusal(report.use_as_admission_gate())
    assert is_refusal(report.use_as_live_gate())
    assert is_refusal(report.restore_into_seat(target_world="live", target_seat="live"))
    assert is_refusal(report.restore_into_seat(target_world="paper"))


def test_spawn_runs_outside_this_process(tmp_path: Path) -> None:
    fp = _config_fp()
    day = _day(composition_fp=fp)
    spec = _spec(tmp_path, day)
    output = tmp_path / "out" / "diff.json"
    receipt = _ok(
        spawn_replay_job(
            spec,
            evidence_root=tmp_path / "evidence",
            output_path=output,
        )
    )
    assert receipt.pid != os.getpid()
    assert receipt.outside_node is True
    assert receipt.world == World.REPLAY.value
    assert receipt.as_mapping()["same_process"] is False
    body = json.loads(output.read_text(encoding="utf-8"))
    assert body["world"] == "replay"
    assert body["clean"] is True
    assert body["commands_submitted"] == 0
    assert body["fill_simulation"] is False


def test_deploy_recipe_plans_spawn_without_qmn_import(tmp_path: Path) -> None:
    module = _load_deploy("qmn_deploy_replay_27_7", _DEPLOY / "replay.py")
    plan = module.build_replay_plan(day_or_range="2024-01-15")
    assert plan.recipe == "node-replay"
    assert plan.principal == "ops"
    assert plan.world == "replay"
    assert plan.live_network is False
    assert plan.secrets_resolved is False
    assert plan.fill_simulation is False
    assert plan.ok is True
    assert any(step.kind == "spawn_outside_node" for step in plan.steps)
    out = tmp_path / "plan.json"
    module.write_plan(plan, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["world"] == "replay"
    code = module.main(["--check-mode", "--day", "2024-01-15"])
    assert code == 0
    apply_refused = module.main(["--apply"])
    assert apply_refused == 2


def test_replay_sources_stay_credential_free_and_do_not_recompute_sqs() -> None:
    banned_mods = ("urllib", "socket", "http.client", "qmf.venue", "qmn.mis.labelers")
    banned_names = ("evaluate_sqs", "mint_signal_snapshot")
    hits: list[str] = []
    for path in sorted((_SRC / "replay").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                imported.add(node.module)
            elif isinstance(node, ast.Name) and node.id in banned_names:
                hits.append(f"{path.name}:{node.id}")
        for name in imported:
            root = name.split(".", 1)[0]
            if name in banned_mods or root in {"urllib", "socket"}:
                hits.append(f"{path.name}:{name}")
    assert hits == []
    deploy = (_DEPLOY / "replay.py").read_text(encoding="utf-8")
    tree = ast.parse(deploy)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module)
    assert not any(name == "qmn" or name.startswith("qmn.") for name in imported)


def test_just_recipe_is_no_longer_reserved() -> None:
    text = (_DEPLOY / "justfile-recipes" / "node.just").read_text(encoding="utf-8")
    assert "node-replay" in text
    assert "replay.py" in text
    assert "reserved" not in text.split("node-replay", 1)[1].split("node-config-init", 1)[0]


def test_attach_replay_never_uses_command_stream_loop_type() -> None:
    # Guard the production symbol so a future in-process drive fails closed.
    assert CommandStreamLoop is not None
    assert is_refusal(attach_replay_to_loop(CommandStreamLoop))
