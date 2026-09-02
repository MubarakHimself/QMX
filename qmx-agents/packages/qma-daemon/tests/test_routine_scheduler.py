"""Story 46.6 — fire Quant-owned Routines deterministically (FR-Q62; CT-49)."""

from __future__ import annotations

import runpy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.ontology.routine import (
    MAX_CONCURRENT_REGISTRY_KEY,
    MISSED_FIRE_DISPOSITION,
    ROUTINE_CATCH_UP_COMMAND,
    ROUTINE_WRITE_COMMAND,
)
from qma.core.plugins.hooks import HookEvent, HookResult, build_hook_result
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary.enums import GraphArtifactKind, HookResultDecision, PrincipalClass
from qma.daemon.scheduler import (
    AUTOMATIC_BACKFILL,
    ROUTINE_FIRE_PRINCIPAL,
    ROUTINE_RECORDS_STORE_NAME,
    RoutineScheduler,
    machine_principal_may_answer_human_gate,
)
from qma.daemon.taskgraph import GraphTemplate, MissionCompiler
from qma.wire.correlation import CorrelationMintOrigin
from qmf.core import Instant, is_ok, is_refusal


def _actor(desk: DeskSlug, slug: str) -> ActorId:
    minted = ActorId.mint(desk, slug)
    assert is_ok(minted)
    return minted.value


def _quant(*, slug: str = "nova") -> Quant:
    return Quant(
        actor_id=_actor(DeskSlug.RESEARCH, slug),
        desk=DeskSlug.RESEARCH,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
    )


def _ns(year: int, month: int, day: int, hour: int, minute: int, zone: str = "UTC") -> int:
    dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(zone))
    return int(dt.timestamp()) * 1_000_000_000


def _instant(ns: int) -> Instant:
    return Instant(value_ns=ns)


def _template() -> GraphTemplate:
    return GraphTemplate(
        qualified_id="research-corpus:survey",
        version="1",
        nodes=({"id": "survey", "kind": "task", "intent": "survey corpus"},),
    )


def _scheduler() -> tuple[RoutineScheduler, Quant]:
    compiler = MissionCompiler()
    registered = compiler.templates.register(_template())
    assert is_ok(registered)
    owner = _quant()
    scheduler = RoutineScheduler(_compiler=compiler)
    scheduler.register_quant(owner)
    return scheduler, owner


def _interval_body(owner: Quant, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "routine-interval",
        "owner_ref": owner.actor_id.value,
        "schedule": {"kind": "interval", "every_ns": 1_000, "iana_zone": "UTC"},
        "goal": "survey corpus coverage",
        "graph_template_ref": "research-corpus:survey",
        "enabled": True,
        "max_concurrent": 2,
    }
    body.update(overrides)
    return body


def test_operator_write_persists_declarative_routine() -> None:
    scheduler, owner = _scheduler()
    created = scheduler.write(
        _interval_body(owner),
        principal_class=PrincipalClass.OPERATOR,
        at=_instant(1_000),
    )
    assert is_ok(created)
    record = created.value
    assert record.id == "routine-interval"
    assert record.owner_ref == owner.actor_id
    assert record.graph_template_ref == "research-corpus:survey"
    assert record.max_concurrent_registry_key == MAX_CONCURRENT_REGISTRY_KEY
    assert scheduler.get("routine-interval") == record
    assert scheduler.store_name == ROUTINE_RECORDS_STORE_NAME
    assert scheduler.automatic_backfill is False
    assert AUTOMATIC_BACKFILL is False
    payload = scheduler.to_payload("routine-interval")
    assert payload is not None
    assert payload["max_concurrent_registry_key"] == "registry:routine.max_concurrent"

    machine = scheduler.write(
        _interval_body(owner, id="routine-machine"),
        principal_class=PrincipalClass.MACHINE,
        at=_instant(1_000),
    )
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    assert machine.context["command"] == ROUTINE_WRITE_COMMAND

    agent = scheduler.write(
        _interval_body(owner, id="routine-agent"),
        principal_class=PrincipalClass.OPERATOR,
        source="agent",
        at=_instant(1_000),
    )
    assert is_refusal(agent)


def test_due_routine_mints_correlation_runs_hooks_and_compiles_mission() -> None:
    scheduler, owner = _scheduler()
    events: list[str] = []

    def before(event: HookEvent) -> HookResult:
        events.append(event.event)
        assert event.payload["correlation_id"]
        assert event.payload["principal_class"] == "machine"
        assert event.payload["goal"] == "survey corpus coverage"
        assert event.payload["graph_template_ref"] == "research-corpus:survey"
        return build_hook_result(HookResultDecision.ALLOW)

    def after(event: HookEvent) -> HookResult:
        events.append(event.event)
        return build_hook_result(HookResultDecision.OBSERVE)

    assert is_ok(scheduler.hooks.register_handler("before_routine_fire", before))
    assert is_ok(scheduler.hooks.register_handler("after_routine_fire", after))
    assert is_ok(
        scheduler.write(_interval_body(owner), principal_class="operator", at=_instant(1_000))
    )

    ticked = scheduler.tick(at=_instant(2_000), routine_id="routine-interval")
    assert is_ok(ticked)
    result = ticked.value[0]
    assert len(result.fired) == 1
    fire = result.fired[0]
    assert fire.correlation_id == "routine:routine-interval:2000"
    assert fire.principal_class is ROUTINE_FIRE_PRINCIPAL
    assert fire.principal_class is PrincipalClass.MACHINE
    assert fire.extra_authority is False
    assert fire.may_answer_human_gate is False
    assert machine_principal_may_answer_human_gate() is False
    assert fire.before_event == "before_routine_fire"
    assert fire.after_event == "after_routine_fire"
    assert events == ["before_routine_fire", "after_routine_fire"]
    assert fire.mission.goal.text == "survey corpus coverage"
    assert fire.mission.graph_template_ref == "research-corpus:survey"
    assert fire.mission.owner == owner.actor_id
    assert fire.compiled.task_graph.artifact_kind is GraphArtifactKind.TASK_GRAPH
    assert fire.to_payload()["mint_origin"] == CorrelationMintOrigin.SCHEDULED_TRIGGER.value

    gate = scheduler.authorize_human_gate("approval_request.answer", "machine")
    assert is_refusal(gate)
    assert OperatorPrincipalRequired.matches(gate)
    allowed = scheduler.authorize_human_gate("approval_request.answer", "operator")
    assert is_ok(allowed)


def test_disabled_routine_emits_no_firing() -> None:
    scheduler, owner = _scheduler()
    assert is_ok(
        scheduler.write(
            _interval_body(owner, enabled=False),
            principal_class="operator",
            at=_instant(1_000),
        )
    )
    ticked = scheduler.tick(at=_instant(2_000), routine_id="routine-interval")
    assert is_ok(ticked)
    result = ticked.value[0]
    assert result.fired == ()
    assert result.missed == ()
    assert result.skipped_disabled is True
    assert scheduler.fires("routine-interval") == ()


def test_missed_fires_are_recorded_not_replayed() -> None:
    scheduler, owner = _scheduler()
    created_at = _ns(2024, 1, 15, 8, 0)
    recover_at = _ns(2024, 1, 15, 10, 0)
    assert is_ok(
        scheduler.write(
            _interval_body(owner)
            | {
                "id": "routine-cron",
                "schedule": {
                    "kind": "cron",
                    "expression": "0 9 * * *",
                    "iana_zone": "UTC",
                },
            },
            principal_class="operator",
            at=_instant(created_at),
        )
    )
    recovered = scheduler.recover(at=_instant(recover_at))
    assert is_ok(recovered)
    cron_result = next(item for item in recovered.value if item.routine_id == "routine-cron")
    assert cron_result.fired == ()
    assert len(cron_result.missed) == 1
    missed = cron_result.missed[0]
    assert missed.disposition == MISSED_FIRE_DISPOSITION
    assert missed.caught_up is False
    assert missed.to_payload()["replayed"] is False
    assert missed.to_payload()["automatic_backfill"] is False
    assert scheduler.fires("routine-cron") == ()
    assert scheduler.missed_fires("routine-cron") == (missed,)

    machine_catch = scheduler.catch_up("routine-cron", principal_class="machine")
    assert is_refusal(machine_catch)
    assert OperatorPrincipalRequired.matches(machine_catch)
    assert machine_catch.context["command"] == ROUTINE_CATCH_UP_COMMAND

    caught = scheduler.catch_up(
        "routine-cron",
        principal_class="operator",
        at=_instant(recover_at),
    )
    assert is_ok(caught)
    assert len(caught.value.fired) == 1
    assert caught.value.fired[0].catch_up is True
    assert caught.value.fired[0].principal_class is PrincipalClass.MACHINE
    assert caught.value.remaining_missed == ()


def test_max_concurrent_skips_without_inventing_authority() -> None:
    scheduler, owner = _scheduler()
    assert is_ok(
        scheduler.write(
            _interval_body(owner, max_concurrent=1),
            principal_class="operator",
            at=_instant(1_000),
        )
    )
    first = scheduler.tick(at=_instant(2_000), routine_id="routine-interval")
    assert is_ok(first)
    assert len(first.value[0].fired) == 1
    second = scheduler.tick(at=_instant(3_000), routine_id="routine-interval")
    assert is_ok(second)
    assert second.value[0].fired == ()
    assert second.value[0].skipped_at_cap is True
    assert scheduler.active_count("routine-interval") == 1
    scheduler.release_mission("routine-interval", first.value[0].fired[0].mission.id)
    third = scheduler.tick(at=_instant(4_000), routine_id="routine-interval")
    assert is_ok(third)
    assert len(third.value[0].fired) == 1


def test_unresolvable_template_is_refused_not_expanded() -> None:
    scheduler, owner = _scheduler()
    assert is_ok(
        scheduler.write(
            _interval_body(owner, graph_template_ref="research-corpus:missing"),
            principal_class="operator",
            at=_instant(1_000),
        )
    )
    ticked = scheduler.tick(at=_instant(2_000), routine_id="routine-interval")
    assert is_refusal(ticked)


def test_example_script() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "routine_usage.py"
    namespace = runpy.run_path(str(path), run_name="__main__")
    assert namespace["main"] is not None
