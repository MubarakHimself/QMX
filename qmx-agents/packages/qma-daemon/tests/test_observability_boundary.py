"""Story 61.3 — logs are not evidence; QMN allow-list stays QMN; agents do not write telemetry."""

from __future__ import annotations

import logging
import runpy
from io import StringIO
from pathlib import Path

from qma.core.plugins.hooks import HookSource
from qma.core.ports.telemetry import HARNESS_AUTHOR, refuse_model_authored_hook_telemetry
from qma.daemon.hooks.agent_authored import AgentAuthoredHookRegistrar
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.observability_boundary import (
    DAEMON_OPERATOR_LOGGER,
    LOGS_REMAIN_LOGS,
    MINI_APP_FAILURE_MARKERS,
    MINI_APP_FIRST_FAILURE_FLOOR,
    OWNING_FAILURES_MD,
    QMB_LOGSINK_CLASS,
    QMB_LOGSINK_MAY_REMAIN,
    QMB_LOGSINK_SOURCE,
    QMN_FAILURES_MD,
    QMN_FAILURES_MD_EXTENDED,
    THIRD_LOGGER_MINTED,
    emit_telemetry_from_hook,
    mint_third_logger,
    owning_failures_md,
    page_qmn_alert_with_mini_app_failure,
    parse_failure_entries,
    place_typed_failure,
    qmn_allow_list_overlap,
    refuse_qmn_allow_list_extension,
    refuse_third_logger,
)
from qma.daemon.operator_log import JsonLineFormatter
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.telemetry.store import TelemetryStore
from qmf.core import is_ok, is_refusal

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "observability_boundary_usage.py"
DAEMON_FAILURES = Path(__file__).resolve().parents[1] / "FAILURES.md"


def _worktree_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / "qmn" / "FAILURES.md").is_file() and (parent / "qmb" / "src").is_dir():
            return parent
    return None


def _compose(tmp_path: Path, *, boot: str) -> DaemonProcess:
    seed = tmp_path / "seed-corpus"
    seed.mkdir(exist_ok=True)
    result = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id=boot,
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
        log_handler=logging.StreamHandler(StringIO()),
    )
    assert is_ok(result), result
    return result.value


def test_mini_app_first_ids_live_in_owning_package_failures_md() -> None:
    home = owning_failures_md("qma-daemon")
    assert is_ok(home)
    assert home.value == OWNING_FAILURES_MD["qma-daemon"]
    assert home.value.endswith("qma-daemon/FAILURES.md")
    placed = place_typed_failure(
        owner="qma-daemon",
        target_failures_md=home.value,
    )
    assert is_ok(placed)
    assert placed.value == home.value
    plugin = owning_failures_md("plugin:research-corpus")
    assert is_ok(plugin)
    assert plugin.value == "qmx-agents/plugins/research-corpus/FAILURES.md"
    plugin_home = place_typed_failure(
        owner="plugin:research-corpus",
        target_failures_md=plugin.value,
    )
    assert is_ok(plugin_home)
    text = DAEMON_FAILURES.read_text(encoding="utf-8")
    ids = {fr_id for fr_id, _title in parse_failure_entries(text)}
    assert "FR-74" in ids
    assert "FR-83" in ids
    assert "FR-84" in ids
    assert "FR-85" in ids


def test_mini_app_failures_never_extend_qmn_failures_or_allow_list() -> None:
    assert QMN_FAILURES_MD_EXTENDED is False
    qmn = place_typed_failure(owner="qma-daemon", target_failures_md=QMN_FAILURES_MD)
    assert is_refusal(qmn)
    assert qmn.context["extended"] is False
    assert qmn.context["allow_list_owner"] == "qmn"
    paged = page_qmn_alert_with_mini_app_failure("FR-74")
    assert is_refusal(paged)
    assert paged.context["on_qmn_allow_list"] is False
    assert paged.context["pages_node"] is False
    plugin_to_qmn = place_typed_failure(
        owner="plugin:research-corpus",
        target_failures_md="qmn/FAILURES.md",
    )
    assert is_refusal(plugin_to_qmn)
    assert is_refusal(refuse_qmn_allow_list_extension())

    daemon_text = DAEMON_FAILURES.read_text(encoding="utf-8")
    root = _worktree_root()
    assert root is not None, "qmn/FAILURES.md must be visible from this worktree"
    qmn_text = (root / "qmn" / "FAILURES.md").read_text(encoding="utf-8")
    overlap = qmn_allow_list_overlap(daemon_text, qmn_text, floor=MINI_APP_FIRST_FAILURE_FLOOR)
    assert overlap == frozenset()
    lowered = qmn_text.lower()
    for marker in MINI_APP_FAILURE_MARKERS:
        assert marker.lower() not in lowered, marker
    qmn_titles = {title for _fr_id, title in parse_failure_entries(qmn_text)}
    assert "Mini-app typed failures added to qmn/FAILURES.md" not in qmn_titles
    assert "Model-authored hook emitting QMA telemetry" not in qmn_titles
    assert "A third logger besides JSON-lines and QMB LogSink" not in qmn_titles


def test_model_authored_hook_cannot_emit_qma_telemetry() -> None:
    store = TelemetryStore()
    payload = {
        "kind": "trace",
        "correlation_id": "corr-hook",
        "payload": {"event": "before_tool"},
    }
    model = emit_telemetry_from_hook(
        store,
        payload,
        source=HookSource.MISSION,
        authored_by="model",
    )
    assert is_refusal(model)
    assert model.context["model_authored_hook_emits"] is False
    assert model.context["agents_write_telemetry"] is False
    assert store.event_count() == 0

    launder = emit_telemetry_from_hook(
        store,
        payload,
        source="mission",
        authored_by=HARNESS_AUTHOR,
    )
    assert is_refusal(launder)
    assert store.event_count() == 0

    agent = store.append({"kind": "log", "correlation_id": "corr-agent", "authored_by": "agent"})
    assert is_refusal(agent)
    model_parse = store.append(
        {"kind": "metric", "correlation_id": "corr-model", "authored_by": "model"}
    )
    assert is_refusal(model_parse)
    assert model_parse.context["field"] == "authored_by"

    registrar = AgentAuthoredHookRegistrar(registry=HookRegistry())
    refused = registrar.emit_telemetry(
        {"kind": "hook_timeout", "correlation_id": "corr-reg", "authored_by": "model"}
    )
    assert is_refusal(refused)
    assert store.event_count() == 0
    assert refuse_model_authored_hook_telemetry().context["author"] == HARNESS_AUTHOR

    harness = emit_telemetry_from_hook(
        store,
        {
            "kind": "hook_timeout",
            "correlation_id": "corr-harness",
            "authored_by": HARNESS_AUTHOR,
        },
        source=HookSource.PLUGIN,
        authored_by=HARNESS_AUTHOR,
    )
    assert is_ok(harness)
    assert harness.value.authored_by == HARNESS_AUTHOR
    assert store.event_count() == 1


def test_logs_remain_logs_qmb_logsink_may_remain_no_third_logger() -> None:
    assert LOGS_REMAIN_LOGS is True
    assert QMB_LOGSINK_MAY_REMAIN is True
    assert THIRD_LOGGER_MINTED is False
    assert DAEMON_OPERATOR_LOGGER == "stdlib.logging"
    assert issubclass(JsonLineFormatter, logging.Formatter)
    third = mint_third_logger("MiniAppLogger")
    assert is_refusal(third)
    assert third.context["minted"] is False
    assert third.context["qmb_logsink_may_remain"] is True
    assert third.context["daemon_logger"] == DAEMON_OPERATOR_LOGGER
    assert is_refusal(refuse_third_logger())

    root = _worktree_root()
    assert root is not None
    log_src = root.joinpath(*QMB_LOGSINK_SOURCE.split("/"))
    assert log_src.is_file()
    text = log_src.read_text(encoding="utf-8")
    assert f"class {QMB_LOGSINK_CLASS}" in text


def test_daemon_process_enforces_boundary(tmp_path: Path) -> None:
    process = _compose(tmp_path, boot="boot-61-3")
    try:
        snap = process.snapshot()
        assert snap["logs_remain_logs"] is True
        assert snap["qmb_logsink_may_remain"] is True
        assert snap["third_logger_minted"] is False
        assert snap["qmn_failures_extended"] is False
        assert is_refusal(
            process.place_typed_failure(
                owner="qma-daemon",
                target_failures_md="qmn/FAILURES.md",
            )
        )
        assert is_refusal(process.page_qmn_alert_with_mini_app_failure("qma-daemon:FR-83"))
        assert is_refusal(
            process.emit_telemetry_from_hook(
                {"kind": "trace", "correlation_id": "corr-proc"},
                source=HookSource.MISSION,
                authored_by="model",
            )
        )
        assert is_refusal(process.mint_third_logger("qma.daemon.miniapp"))
        assert is_refusal(process.extend_qmn_failures_md())
    finally:
        process.close()


def test_example_script() -> None:
    namespace = runpy.run_path(str(EXAMPLE), run_name="__main__")
    assert namespace["main"] is not None
