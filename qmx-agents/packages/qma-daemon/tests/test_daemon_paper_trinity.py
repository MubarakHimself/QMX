"""Story 36.6 — paper trinity, hub, notebooks, alias identity (daemon)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ports.paper import (
    EPIC_PROMOTION_AUTHORITY,
    PAPER_NOUN_RESEARCH,
    QMA_PAPER_EXISTS,
    QMA_WRITES_HUB,
)
from qma.core.ports.tools import ToolKind, ToolRecord, default_rung_for_kind
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.envs.runtime import RuntimeService
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import RefusalCategory


def test_research_paper_named_on_experiment_service() -> None:
    service = ExperimentSpecService()
    named = service.name_paper(world="replay", location="outside_node")
    assert is_ok(named)
    assert named.value == PAPER_NOUN_RESEARCH
    qma_paper = service.register_qma_paper(tool_id="analysis:qma-paper")
    assert is_refusal(qma_paper)
    assert QMA_PAPER_EXISTS is False


def test_qma_paper_tool_refused_at_registration_including_paper_only() -> None:
    registry = ToolRegistry()
    refused = registry.register(
        tool_id="trading:qma-paper",
        kind=ToolKind.PLUGIN,
        schema={"name": "qma-paper"},
        tags=("paper_only", "qma_paper"),
        acts=("backtest",),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert registry.get("trading:qma-paper") is None
    paper_order = registry.register(
        tool_id="trading:paper_only_order",
        kind=ToolKind.NATIVE,
        acts=("paper_only_submit_order",),
        tags=("paper_only",),
    )
    assert is_refusal(paper_order)


def test_daemon_never_writes_hub_and_does_not_promote(tmp_path: Path) -> None:
    seed = tmp_path / "seed-corpus"
    seed.mkdir()
    composed = DaemonProcess.compose(
        tmp_path,
        machine="test-host",
        boot_epoch_id="boot-36-6",
        bind_port=0,
        plugin_load_configs=research_corpus_plugin_load_config(seed),
    )
    assert is_ok(composed)
    process = composed.value
    try:
        assert QMA_WRITES_HUB is False
        assert is_refusal(process.write_hub(ref="inbox"))
        assert is_refusal(process.hub_publish())
        assert EPIC_PROMOTION_AUTHORITY is False
        assert is_refusal(process.promote(artifact="bot-fp1"))
        experiments = process.experiments
        assert is_refusal(experiments.write_hub())
        assert is_refusal(experiments.hub_publish())
        assert is_refusal(experiments.promote())
        ref = experiments.admit_hub_ref("ct32_ref")
        assert is_ok(ref)
    finally:
        process.close()


def test_aliases_and_tabs_do_not_mint_records() -> None:
    service = ExperimentSpecService()
    alias = service.resolve_alias(
        display="project",
        lane="coordinated",
        over="fp1:sha256:" + ("c" * 64),
    )
    assert is_ok(alias)
    tab = service.mint_ui_tab(display="workspace")
    assert is_refusal(tab)
    project = service.register_project()
    assert is_refusal(project)


def test_notebook_is_environment_not_qmb_module_or_jupyter() -> None:
    runtime = RuntimeService()
    notebook = runtime.admit_exploratory_notebook(imports=("qmb", "qml"))
    assert is_ok(notebook)
    env = runtime.admit_managed_interpreter(kind=ExecutionEnvironmentKind.DOCKER)
    assert is_ok(env)
    jupyter = runtime.admit_exploratory_notebook(
        imports=("qmb",),
        jupyter_product="colab",
    )
    assert is_refusal(jupyter)
    module = runtime.admit_managed_interpreter(kind="docker", as_qmb_module=True)
    assert is_refusal(module)
    fourth = runtime.notebook_joins_undertaking(as_identity=True)
    assert is_refusal(fourth)
    session = runtime.notebook_joins_undertaking(as_environment_session=True)
    assert is_ok(session)
    registered = runtime.register_analysis_notebook()
    assert is_ok(registered)
    record = runtime.notebook_entry()
    assert record is not None
    assert isinstance(record, ToolRecord)
    assert record.requires_environment_kind == ExecutionEnvironmentKind.DOCKER.value
    assert default_rung_for_kind(record.kind) == record.capability_rung


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "paper_trinity_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
