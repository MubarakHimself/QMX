"""Story 37.1 — procedures live in QMA; one Graph Template is one Mission."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.barriers import assert_no_qmb_import, scan_qmb_imports, validate_worker_image
from qma.core.control import (
    ANALYSIS_PROCEDURE_ID,
    ANALYSIS_PROCEDURE_SKILL_ID,
    author_procedure,
    scan_qmb_task_graph_modules,
)
from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.plugins import analysis_procedure_graph_payload, analysis_procedure_skill_payload
from qma.core.ports.execution import WorkerImageManifest
from qma.core.ports.experiments import CT07_V1_EDGE_TYPES
from qma.core.vocabulary.enums import GraphArtifactKind, TaskMissionState
from qma.daemon.plugins import DeskPluginRoster, research_corpus_plugin_load_config
from qma.daemon.taskgraph import CompileRequest, MissionCompiler, instantiate_procedure
from qmf.core import is_ok, is_refusal

AGENTS_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = AGENTS_ROOT.parent
DAEMON_SRC = Path(__file__).resolve().parents[1] / "src"
PLUGINS_ROOT = AGENTS_ROOT / "plugins"
QMB_SRC = REPO_ROOT / "qmb" / "src" / "qmb"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "procedure_usage.py"


def _quant() -> Quant:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return Quant(
        actor_id=minted.value,
        desk=DeskSlug.ANALYSIS,
        quant_slug="notebook",
        role=RoleName.ANALYST,
        name="Quant notebook",
    )


def test_graph_template_instantiation_is_one_mission() -> None:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    authored = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    compiled = instantiate_procedure(
        authored.value,
        owner=owner,
        compiler=compiler,
        goal=Goal(text="place any QMB door step first"),
    )
    assert is_ok(compiled), compiled
    result = compiled.value
    assert result.mission.graph_template_ref == ANALYSIS_PROCEDURE_ID
    assert result.task_graph.mission_id == result.mission.id
    assert result.task_graph.artifact_kind is GraphArtifactKind.TASK_GRAPH
    assert result.task_graph.graph_template_ref == ANALYSIS_PROCEDURE_ID
    door_ids = set(authored.value.first_door_steps)
    ready = {
        task.node_id for task in result.task_graph.tasks if task.state is TaskMissionState.READY
    }
    assert door_ids <= ready
    assert len(result.task_graph.tasks) == 4
    again = instantiate_procedure(
        authored.value,
        owner=owner,
        compiler=compiler,
        goal=Goal(text="place any QMB door step first"),
    )
    assert is_ok(again)
    assert again.value.mission.id == result.mission.id
    payload = authored.value.to_payload()
    assert payload["is_experiment_spec"] is False
    assert payload["ct07_edge_kind"] is None
    assert "procedure" not in CT07_V1_EDGE_TYPES


def test_skill_does_not_compile_to_a_mission() -> None:
    owner = _quant()
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})
    skill = author_procedure(analysis_procedure_skill_payload())
    assert is_ok(skill)
    refused = instantiate_procedure(skill.value, owner=owner, compiler=compiler)
    assert is_refusal(refused)
    assert refused.context["field"] == "kind"


def test_analysis_backtest_pack_contributes_the_procedure(tmp_path: Path) -> None:
    seed = tmp_path / "seed-corpus"
    seed.mkdir()
    roster = DeskPluginRoster(plugin_load_configs=research_corpus_plugin_load_config(seed))
    activated = roster.activate()
    assert is_ok(activated), activated
    template = roster.templates.get(ANALYSIS_PROCEDURE_ID)
    assert template is not None
    assert template.artifact_kind is GraphArtifactKind.GRAPH_TEMPLATE
    assert template.to_payload()["stateless"] is True
    owner = _quant()
    roster.compiler.remember_quant(owner.actor_id)
    compiled = roster.compiler.compile(
        CompileRequest(
            goal=Goal(text="place a door step"),
            owner=owner,
            graph_template_ref=ANALYSIS_PROCEDURE_ID,
            require_decomposition_reasoning=False,
        )
    )
    assert is_ok(compiled), compiled
    assert compiled.value.mission.graph_template_ref == ANALYSIS_PROCEDURE_ID
    published = {row.qualified_id for row in roster.loader.published_contributions()}
    assert ANALYSIS_PROCEDURE_ID in published
    assert ANALYSIS_PROCEDURE_SKILL_ID in published


def test_qmb_and_import_gates_still_hold() -> None:
    assert scan_qmb_task_graph_modules(QMB_SRC) == ()
    assert_no_qmb_import(DAEMON_SRC)
    assert_no_qmb_import(PLUGINS_ROOT)
    assert scan_qmb_imports(DAEMON_SRC) == ()
    assert scan_qmb_imports(PLUGINS_ROOT) == ()
    assert is_refusal(validate_worker_image(WorkerImageManifest.from_values(imports=("qmb",))))


def test_procedure_usage_example() -> None:
    namespace = runpy.run_path(str(EXAMPLE), run_name="__main__")
    assert callable(namespace["main"])
