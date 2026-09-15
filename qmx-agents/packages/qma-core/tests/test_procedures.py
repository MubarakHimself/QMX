"""Story 37.1 — reusable procedures live in QMA (FR-W32; DEC-0277)."""

from __future__ import annotations

from pathlib import Path

from qma.core.barriers import assert_no_qmb_import, scan_qmb_imports, validate_worker_image
from qma.core.control import (
    ANALYSIS_PROCEDURE_ID,
    COMPOSITION_NON_LINEAR,
    FORBIDDEN_QMB_TASK_GRAPH_NAMES,
    PROCEDURE_HOMES,
    PROCEDURE_IS_EXPERIMENT_SPEC,
    QMB_GROWS_TASK_GRAPH,
    QMB_PROCEDURE_DOOR_STEPS,
    ProcedureKind,
    author_procedure,
    first_door_step_ids,
    parse_reusable_procedure,
    procedure_ct07_edge_kinds,
    procedure_mints_ct07_edge,
    qmb_grows_task_graph,
    scan_qmb_task_graph_modules,
)
from qma.core.ontology import ActorId, DeskSlug
from qma.core.plugins import (
    analysis_procedure_graph_payload,
    analysis_procedure_skill_payload,
)
from qma.core.ports.execution import WorkerImageManifest
from qma.core.ports.experiments import (
    CT07_V1_EDGE_TYPES,
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    admit_coordinated_continuity,
)
from qma.core.vocabulary.enums import PrincipalClass
from qmf.core import is_ok, is_refusal

AGENTS_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = AGENTS_ROOT.parent
QMB_SRC = REPO_ROOT / "qmb" / "src" / "qmb"
CORE_SRC = Path(__file__).resolve().parents[1] / "src"
PLUGINS_ROOT = AGENTS_ROOT / "plugins"


def _owner() -> ActorId:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    return minted.value


def _routine_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "kind": "routine",
        "id": "routine-daily-replay",
        "owner_ref": _owner().value,
        "schedule": {
            "kind": "cron",
            "expression": "0 9 * * 1-5",
            "iana_zone": "America/New_York",
        },
        "goal": "replay recorded evidence",
        "graph_template_ref": ANALYSIS_PROCEDURE_ID,
        "enabled": True,
        "max_concurrent": 1,
    }
    body.update(overrides)
    return body


def test_procedure_homes_are_graph_template_skill_or_routine() -> None:
    assert ProcedureKind.GRAPH_TEMPLATE in PROCEDURE_HOMES
    assert ProcedureKind.SKILL in PROCEDURE_HOMES
    assert ProcedureKind.ROUTINE in PROCEDURE_HOMES
    assert len(PROCEDURE_HOMES) == 3


def test_graph_template_skill_and_routine_author() -> None:
    template = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(template)
    record = template.value
    assert record.kind is ProcedureKind.GRAPH_TEMPLATE
    assert record.qualified_id == ANALYSIS_PROCEDURE_ID
    assert record.composition == COMPOSITION_NON_LINEAR
    assert record.is_experiment_spec is PROCEDURE_IS_EXPERIMENT_SPEC
    assert record.ct07_edge_kind is None
    assert record.first_door_steps == ("backtest", "project", "rank", "download")
    assert first_door_step_ids(record.nodes) == record.first_door_steps

    skill = author_procedure(analysis_procedure_skill_payload())
    assert is_ok(skill)
    assert skill.value.kind is ProcedureKind.SKILL
    assert skill.value.skill is not None
    assert skill.value.skill.is_loop is False

    routine = author_procedure(_routine_body(), principal=PrincipalClass.OPERATOR)
    assert is_ok(routine)
    assert routine.value.kind is ProcedureKind.ROUTINE
    assert routine.value.graph_template_ref == ANALYSIS_PROCEDURE_ID


def test_any_door_step_may_be_first_placement() -> None:
    authored = parse_reusable_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    steps = authored.value.first_door_steps
    assert set(steps) == {str(node["id"]) for node in QMB_PROCEDURE_DOOR_STEPS}
    for node_id in steps:
        assert node_id in authored.value.first_door_steps


def test_wizard_and_custom_projects_clone_are_refused() -> None:
    wizard = author_procedure(
        {
            "kind": "wizard",
            "qualified_id": "analysis-backtest:wizard",
            "version": "1",
        }
    )
    assert is_refusal(wizard)
    assert wizard.context["field"] == "product"

    linear = author_procedure(
        {
            **dict(analysis_procedure_graph_payload()),
            "required_first_door": "backtest",
        }
    )
    assert is_refusal(linear)

    chain = author_procedure(
        {
            "kind": "graph_template",
            "qualified_id": "analysis-backtest:linear",
            "version": "1",
            "nodes": (
                {"id": "research", "kind": "task"},
                {"id": "backtest", "kind": "task"},
                {"id": "paper", "kind": "task"},
            ),
            "edges": (
                {"from": "research", "to": "backtest"},
                {"from": "backtest", "to": "paper"},
            ),
        }
    )
    assert is_refusal(chain)

    clone = author_procedure(
        {
            "kind": "custom_projects",
            "qualified_id": "analysis-backtest:sq",
            "version": "1",
        }
    )
    assert is_refusal(clone)
    assert "donor" in clone.context


def test_procedure_is_not_experiment_spec_and_mints_no_ct07() -> None:
    as_spec = author_procedure(
        {
            "kind": "experiment_spec",
            "qualified_id": "analysis-backtest:procedure",
            "version": "1",
        }
    )
    assert is_refusal(as_spec)
    continuity = admit_coordinated_continuity("procedure")
    assert is_refusal(continuity)
    authored = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    payload = authored.value.to_payload()
    assert payload["is_experiment_spec"] is False
    assert payload["ct07_edge_kind"] is None
    assert payload["mints_ct07_edge"] is False
    assert procedure_mints_ct07_edge() is False
    assert procedure_ct07_edge_kinds() == frozenset()
    assert "branches-from" in CT07_V1_EDGE_TYPES
    assert EXPERIMENT_LINEAGE_EDGE_TYPE == "branches-from"
    assert "procedure" not in CT07_V1_EDGE_TYPES
    assert not procedure_ct07_edge_kinds() - CT07_V1_EDGE_TYPES


def test_qmb_does_not_grow_a_task_graph_module() -> None:
    assert qmb_grows_task_graph() is False
    assert QMB_GROWS_TASK_GRAPH is False
    assert scan_qmb_task_graph_modules(QMB_SRC) == ()
    names = {path.name.casefold().replace("-", "_") for path in QMB_SRC.iterdir()}
    assert names.isdisjoint(FORBIDDEN_QMB_TASK_GRAPH_NAMES)
    qmb_home = author_procedure(
        {
            **dict(analysis_procedure_graph_payload()),
            "home": "qmb.taskgraph",
        }
    )
    assert is_refusal(qmb_home)
    assert qmb_home.context["qmb_grows_task_graph"] is False


def test_daemon_plugins_and_workers_still_never_import_qmb() -> None:
    assert_no_qmb_import(CORE_SRC)
    assert_no_qmb_import(AGENTS_ROOT / "packages" / "qma-daemon" / "src")
    assert_no_qmb_import(PLUGINS_ROOT)
    assert scan_qmb_imports(CORE_SRC) == ()
    assert scan_qmb_imports(PLUGINS_ROOT) == ()
    qmb_image = validate_worker_image(WorkerImageManifest.from_values(imports=("qmb",)))
    assert is_refusal(qmb_image)
    qmb_pkg = validate_worker_image(WorkerImageManifest.from_values(packages=("qmb",)))
    assert is_refusal(qmb_pkg)


def test_routine_stays_operator_authored() -> None:
    machine = author_procedure(_routine_body(), principal=PrincipalClass.MACHINE)
    assert is_refusal(machine)
    omitted = author_procedure(_routine_body())
    assert is_refusal(omitted)
