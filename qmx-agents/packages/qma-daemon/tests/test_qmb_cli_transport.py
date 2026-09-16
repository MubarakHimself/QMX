"""Story 36.2 — production QMB door spawns a real qmb CLI process."""

from __future__ import annotations

import inspect
import json
import runpy
import shutil
from pathlib import Path

from qma.core.barriers import assert_no_qmb_import, scan_qmb_imports, validate_worker_image
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.execution import ExecutionEnvironmentDeclaration, WorkerImageManifest
from qma.core.ports.qmb import (
    QMB_BACKTEST_TOOL_ID,
    QMB_CLI_ARGV,
    QMB_CLI_PROGRAM,
    QMB_OWNED_CONCERNS,
    QMB_ROUTE,
    QMB_WORLD_REPLAY,
    QmbDoorKind,
    refuse_qmb_import_edge,
)
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, JobHandleState
from qma.daemon.backtest import (
    BacktestingService,
    CliQmbDoorTransport,
    RecordingQmbDoorTransport,
    cli_qmb_test_double_argv0,
)
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal

AGENTS_ROOT = Path(__file__).resolve().parents[3]
DAEMON_SRC = AGENTS_ROOT / "packages" / "qma-daemon" / "src"
PLUGINS_ROOT = AGENTS_ROOT / "plugins"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "qmb_door_usage.py"
CLI_SRC = DAEMON_SRC / "qma" / "daemon" / "backtest" / "cli.py"
SERVICE_SRC = DAEMON_SRC / "qma" / "daemon" / "backtest" / "service.py"


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _envs(*kinds: ExecutionEnvironmentKind) -> ExecutionEnvironmentRegistry:
    registry = ExecutionEnvironmentRegistry()
    for kind in kinds:
        assert is_ok(
            registry.register_declaration(
                ExecutionEnvironmentDeclaration.isolated(
                    kind,
                    provider_ref=f"local-{kind.value}",
                )
            )
        )
    return registry


def _cli_transport(tmp_path: Path) -> CliQmbDoorTransport:
    receipt = tmp_path / "qmb-receipt.json"
    return CliQmbDoorTransport(
        argv0=cli_qmb_test_double_argv0(tmp_path / "qmb_double.py"),
        receipt_path=str(receipt),
    )


def _service(
    tmp_path: Path,
    *kinds: ExecutionEnvironmentKind,
) -> tuple[BacktestingService, CliQmbDoorTransport]:
    if not kinds:
        kinds = (ExecutionEnvironmentKind.DOCKER,)
    transport = _cli_transport(tmp_path)
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(*kinds),
        transport=transport,
    )
    installed = service.install()
    assert is_ok(installed)
    return service, transport


def test_default_transport_is_cli_not_recording() -> None:
    service = BacktestingService()
    transport = service.transport
    assert isinstance(transport, CliQmbDoorTransport)
    assert not isinstance(transport, RecordingQmbDoorTransport)
    assert transport.production is True
    assert transport.spawns_qmb_process is True
    assert RecordingQmbDoorTransport.production is False
    assert RecordingQmbDoorTransport.spawns_qmb_process is False
    source = SERVICE_SRC.read_text(encoding="utf-8")
    assert "else CliQmbDoorTransport()" in source
    assert "else RecordingQmbDoorTransport()" not in source
    assert "source-inspected" not in inspect.getsource(CliQmbDoorTransport)


def test_cli_transport_spawns_documented_double_not_recording(tmp_path: Path) -> None:
    service, transport = _service(tmp_path)
    try:
        placed = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=_owner(),
            task_id="task-cli-1",
            environment_ref="env:docker",
            experiment_spec_fp1="fp1:sha256:" + ("a" * 64),
            evidence_ref="evidence:recorded-bars",
        )
        assert is_ok(placed)
        payload = placed.value.to_payload()
        assert payload["route"] == list(QMB_ROUTE)
        assert payload["program"] == QMB_CLI_PROGRAM
        assert payload["argv"] == list(QMB_CLI_ARGV)
        assert payload["world"] == QMB_WORLD_REPLAY
        assert payload["import_edge"] is False
        assert payload["qma_re_specifies"] is False
        assert isinstance(service.transport, CliQmbDoorTransport)
        assert not isinstance(service.transport, RecordingQmbDoorTransport)
        assert len(transport.spawned) == 1
        spawned = transport.spawned[0]
        assert spawned.pid > 0
        assert spawned.argv == QMB_CLI_ARGV
        assert spawned.command[-2:] == QMB_CLI_ARGV
        rc = transport.wait(placed.value.handle.job_id, timeout=10.0)
        assert rc == 0
        receipt = json.loads((tmp_path / "qmb-receipt.json").read_text(encoding="utf-8"))
        assert receipt["argv"] == list(QMB_CLI_ARGV)
        assert receipt["world"] == QMB_WORLD_REPLAY
        assert receipt["job_id"] == placed.value.handle.job_id
        assert int(receipt["pid"]) > 0
    finally:
        transport.close()


def test_second_qmb_run_in_occupied_environment_is_refused(tmp_path: Path) -> None:
    service, transport = _service(
        tmp_path,
        ExecutionEnvironmentKind.DOCKER,
        ExecutionEnvironmentKind.LOCAL,
    )
    try:
        owner = _owner()
        first = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=owner,
            task_id="task-cli-occ-1",
            environment_ref="env:docker",
            experiment_spec_fp1="fp1:spec-1",
            evidence_ref="evidence:recorded-1",
        )
        assert is_ok(first)
        assert service.occupying_job("env:docker") == first.value.handle.job_id
        second = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=owner,
            task_id="task-cli-occ-2",
            environment_ref="env:docker-analysis",
            experiment_spec_fp1="fp1:spec-2",
            evidence_ref="evidence:recorded-2",
        )
        assert is_refusal(second)
        assert second.context["field"] == "qmb_job"
        assert len(transport.spawned) == 1
        other = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=owner,
            task_id="task-cli-occ-3",
            environment_ref="env:local",
            experiment_spec_fp1="fp1:spec-3",
            evidence_ref="evidence:recorded-3",
        )
        assert is_ok(other)
        assert len(transport.spawned) == 2
        completed = service.observe_outcome(first.value.handle.job_id, JobHandleState.DONE)
        assert is_ok(completed)
        retry = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=owner,
            task_id="task-cli-occ-4",
            environment_ref="env:docker",
            experiment_spec_fp1="fp1:spec-4",
            evidence_ref="evidence:recorded-4",
        )
        assert is_ok(retry)
        assert is_refusal(service.set_parallelism(8))
        assert is_refusal(service.append_run_ledger({"line": 1}))
        assert is_refusal(service.store_artifact({"ct32": True}))
        assert service.qmb_owned_concerns() == QMB_OWNED_CONCERNS
        assert is_refusal(service.import_qmb_package())
        assert refuse_qmb_import_edge().context["field"] == "import"
    finally:
        transport.close()


def test_venue_account_and_mcp_are_refused_before_spawn(tmp_path: Path) -> None:
    service, transport = _service(tmp_path)
    try:
        paper = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=_owner(),
            task_id="task-cli-paper",
            environment_ref="env:docker",
            experiment_spec_fp1="fp1:spec",
            evidence_ref="evidence:recorded",
            world="paper",
        )
        assert is_refusal(paper)
        account = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=_owner(),
            task_id="task-cli-acct",
            environment_ref="env:docker",
            experiment_spec_fp1="fp1:spec",
            evidence_ref="evidence:recorded",
            extra={"account_id": "venue-acct"},
        )
        assert is_refusal(account)
        mcp = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=_owner(),
            task_id="task-cli-mcp",
            environment_ref="env:docker",
            experiment_spec_fp1="fp1:spec",
            evidence_ref="evidence:recorded",
            door=QmbDoorKind.MCP,
        )
        assert is_refusal(mcp)
        assert mcp.context["field"] == "door"
        assert transport.spawned == ()
        assert transport.maps_cancel_to_qmb_abort is True
        abort = transport.abort("qmb:docker:task-cli-mcp")
        assert is_refusal(abort)
        assert abort.context["field"] == "job_id"
    finally:
        transport.close()


def test_daemon_plugins_and_workers_have_no_import_qmb_edge() -> None:
    assert_no_qmb_import(DAEMON_SRC)
    assert_no_qmb_import(PLUGINS_ROOT)
    for pack in PLUGINS_ROOT.iterdir():
        if pack.is_dir():
            assert_no_qmb_import(pack)
            worker = pack / "worker"
            if worker.exists():
                assert_no_qmb_import(worker)
    assert scan_qmb_imports(DAEMON_SRC) == ()
    assert scan_qmb_imports(PLUGINS_ROOT) == ()
    cli_src = CLI_SRC.read_text(encoding="utf-8")
    assert "import qmb" not in cli_src
    assert "from qmb" not in cli_src
    assert "subprocess" in cli_src
    assert "Popen" in cli_src
    qmb_image = validate_worker_image(WorkerImageManifest.from_values(imports=("qmb",)))
    assert is_refusal(qmb_image)
    qmb_pkg = validate_worker_image(WorkerImageManifest.from_values(packages=("qmb",)))
    assert is_refusal(qmb_pkg)


def test_missing_qmb_binary_is_typed_refusal_not_import(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-qmb-binary"
    transport = CliQmbDoorTransport(argv0=(str(missing),))
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(ExecutionEnvironmentKind.DOCKER),
        transport=transport,
    )
    refused = service.invoke(
        QMB_BACKTEST_TOOL_ID,
        owner=_owner(),
        task_id="task-cli-missing",
        environment_ref="env:docker",
        experiment_spec_fp1="fp1:spec",
        evidence_ref="evidence:recorded",
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "qmb_cli"
    assert transport.spawned == ()
    assert is_refusal(service.import_qmb_package())


def test_composed_process_default_door_is_cli(tmp_path: Path) -> None:
    seed = tmp_path / "seed-corpus"
    seed.mkdir()
    result = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id="boot-36-2",
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
    )
    assert is_ok(result)
    process = result.value
    try:
        assert isinstance(process.backtesting.transport, CliQmbDoorTransport)
        snap = process.snapshot()
        assert snap["qmb_door_transport"] == "CliQmbDoorTransport"
        assert snap["qmb_door_production"] is True
        assert snap["parallelism"] is None
        assert snap["backtest_state"] is None
    finally:
        process.close()


def test_real_qmb_binary_is_spawned_when_on_path(tmp_path: Path) -> None:
    found = shutil.which("qmb")
    argv0 = (found,) if found is not None else cli_qmb_test_double_argv0(tmp_path / "qmb_double.py")
    transport = CliQmbDoorTransport(argv0=argv0, receipt_path=str(tmp_path / "receipt.json"))
    service = BacktestingService(
        tools=ToolRegistry(),
        jobs=JobHandleService(),
        environments=_envs(ExecutionEnvironmentKind.DOCKER),
        transport=transport,
    )
    try:
        placed = service.invoke(
            QMB_BACKTEST_TOOL_ID,
            owner=_owner(),
            task_id="task-cli-bin",
            environment_ref="env:docker",
            experiment_spec_fp1="fp1:spec",
            evidence_ref="evidence:recorded",
        )
        assert is_ok(placed)
        assert len(transport.spawned) == 1
        assert transport.spawned[0].pid > 0
        assert transport.spawned[0].command[0] == argv0[0]
        assert transport.spawned[0].argv == QMB_CLI_ARGV
    finally:
        transport.close()


def test_reference_usage_example_spawns_cli_double() -> None:
    namespace = runpy.run_path(str(EXAMPLE))
    namespace["main"]()
