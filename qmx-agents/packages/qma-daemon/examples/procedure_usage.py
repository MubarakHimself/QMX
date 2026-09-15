"""L27 reference usage: reusable procedures live in QMA, not QMB."""

from __future__ import annotations

from qma.core.control import (
    ANALYSIS_PROCEDURE_ID,
    author_procedure,
    procedure_mints_ct07_edge,
    qmb_grows_task_graph,
)
from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.plugins import analysis_procedure_graph_payload, analysis_procedure_skill_payload
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.taskgraph import MissionCompiler, instantiate_procedure
from qmf.core import is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.ANALYSIS,
        quant_slug="notebook",
        role=RoleName.ANALYST,
        name="Quant notebook",
    )
    compiler = MissionCompiler(known_quant_actor_ids={owner.actor_id.value})

    authored = author_procedure(analysis_procedure_graph_payload())
    assert is_ok(authored)
    assert authored.value.qualified_id == ANALYSIS_PROCEDURE_ID
    assert authored.value.is_experiment_spec is False
    assert qmb_grows_task_graph() is False
    assert procedure_mints_ct07_edge() is False

    compiled = instantiate_procedure(
        authored.value,
        owner=owner,
        compiler=compiler,
        goal=Goal(text="place any QMB door step first"),
    )
    assert is_ok(compiled)
    assert compiled.value.mission.graph_template_ref == ANALYSIS_PROCEDURE_ID
    assert compiled.value.task_graph.mission_id == compiled.value.mission.id

    wizard = author_procedure(
        {
            "product": "research-backtest-paper",
            "qualified_id": "analysis-backtest:wizard",
            "version": "1",
            "nodes": (),
        }
    )
    assert is_refusal(wizard)

    clone = author_procedure(
        {
            "kind": "sq_custom_projects",
            "qualified_id": "analysis-backtest:sq",
            "version": "1",
        }
    )
    assert is_refusal(clone)

    skill = author_procedure(analysis_procedure_skill_payload())
    assert is_ok(skill)
    assert is_refusal(instantiate_procedure(skill.value, owner=owner, compiler=compiler))

    routine = author_procedure(
        {
            "kind": "routine",
            "id": "routine-replay",
            "owner_ref": owner.actor_id.value,
            "schedule": {"kind": "interval", "every_ns": 1_000, "iana_zone": "UTC"},
            "goal": "replay recorded evidence",
            "graph_template_ref": ANALYSIS_PROCEDURE_ID,
            "enabled": True,
            "max_concurrent": 1,
        },
        principal=PrincipalClass.OPERATOR,
    )
    assert is_ok(routine)


if __name__ == "__main__":
    main()
