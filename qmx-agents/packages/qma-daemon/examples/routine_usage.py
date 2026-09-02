"""L27 reference usage: operator-only Routines fire deterministically."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.scheduler import AUTOMATIC_BACKFILL, RoutineScheduler
from qma.daemon.taskgraph import GraphTemplate, MissionCompiler
from qmf.core import Instant, is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.RESEARCH, "nova")
    assert is_ok(minted)
    owner = Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="nova",
        role=RoleName.RESEARCHER,
        name="Quant nova",
    )
    compiler = MissionCompiler()
    registered = compiler.templates.register(
        GraphTemplate(
            qualified_id="research-corpus:survey",
            version="1",
            nodes=({"id": "survey", "kind": "task", "intent": "survey corpus"},),
        )
    )
    assert is_ok(registered)
    scheduler = RoutineScheduler(_compiler=compiler)
    scheduler.register_quant(owner)
    assert scheduler.automatic_backfill is False
    assert AUTOMATIC_BACKFILL is False

    created = scheduler.write(
        {
            "id": "routine-interval",
            "owner_ref": owner.actor_id.value,
            "schedule": {"kind": "interval", "every_ns": 1_000, "iana_zone": "UTC"},
            "goal": "survey corpus coverage",
            "graph_template_ref": "research-corpus:survey",
            "enabled": True,
            "max_concurrent": 4,
        },
        principal_class=PrincipalClass.OPERATOR,
        at=Instant(value_ns=1_000),
    )
    assert is_ok(created)

    machine = scheduler.write(
        {
            "id": "routine-forbidden",
            "owner_ref": owner.actor_id.value,
            "schedule": {"kind": "interval", "every_ns": 1_000, "iana_zone": "UTC"},
            "goal": "should not persist",
            "graph_template_ref": "research-corpus:survey",
            "enabled": True,
            "max_concurrent": 1,
        },
        principal_class=PrincipalClass.MACHINE,
        at=Instant(value_ns=1_000),
    )
    assert is_refusal(machine)

    ticked = scheduler.tick(at=Instant(value_ns=2_000), routine_id="routine-interval")
    assert is_ok(ticked)
    fire = ticked.value[0].fired[0]
    assert fire.principal_class is PrincipalClass.MACHINE
    assert fire.extra_authority is False
    assert fire.may_answer_human_gate is False
    assert fire.mission.goal.text == "survey corpus coverage"
    assert fire.correlation_id.startswith("routine:")

    recovered = scheduler.recover(at=Instant(value_ns=5_000))
    assert is_ok(recovered)
    missed = scheduler.missed_fires("routine-interval")
    assert missed
    assert all(item.disposition == "recorded" for item in missed)
    catch = scheduler.catch_up(
        "routine-interval",
        principal_class=PrincipalClass.OPERATOR,
        at=Instant(value_ns=5_000),
    )
    assert is_ok(catch)


if __name__ == "__main__":
    main()
