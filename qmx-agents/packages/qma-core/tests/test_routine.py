"""Story 46.6 — Quant-owned Routine record (FR-Q62; CT-49)."""

from __future__ import annotations

from qma.core.ontology import (
    FORBIDDEN_GRAPH_TEMPLATE_PLUGINS,
    MAX_CONCURRENT_REGISTRY_KEY,
    MISSED_FIRE_DISPOSITION,
    ROUTINE_CATCH_UP_COMMAND,
    ROUTINE_EDITABILITY,
    ROUTINE_HOME,
    ROUTINE_REQUIRED_FIELDS,
    ROUTINE_SCOPE,
    ROUTINE_WRITE_COMMAND,
    ActorId,
    DeskSlug,
    Goal,
    Routine,
    authorize_routine_catch_up,
    authorize_routine_write,
    has_routine_edit_kind,
    parse_graph_template_ref,
    parse_routine,
    parse_routine_schedule,
    refuse_agent_routine_write,
    source_may_write_routine,
)
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary.enums import (
    PrincipalClass,
    RefinementEditKind,
    VariableEditability,
    VariableScope,
)
from qmf.core import is_ok, is_refusal


def _owner(*, slug: str = "nova") -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, slug)
    assert is_ok(minted)
    return minted.value


def _routine_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "id": "routine-daily-survey",
        "owner_ref": _owner().value,
        "schedule": {
            "kind": "cron",
            "expression": "0 9 * * 1-5",
            "iana_zone": "America/New_York",
        },
        "goal": "survey corpus coverage",
        "graph_template_ref": "research-corpus:survey",
        "enabled": True,
        "max_concurrent": 1,
    }
    body.update(overrides)
    return body


def test_routine_carries_exactly_seven_fields() -> None:
    parsed = parse_routine(_routine_body())
    assert is_ok(parsed)
    record = parsed.value
    assert isinstance(record, Routine)
    assert record.id == "routine-daily-survey"
    assert record.owner_ref == _owner()
    assert record.schedule.kind == "cron"
    assert record.schedule.expression == "0 9 * * 1-5"
    assert record.schedule.iana_zone == "America/New_York"
    assert record.goal == Goal(text="survey corpus coverage")
    assert record.graph_template_ref == "research-corpus:survey"
    assert record.enabled is True
    assert record.max_concurrent == 1
    assert {
        "id",
        "owner_ref",
        "schedule",
        "goal",
        "graph_template_ref",
        "enabled",
        "max_concurrent",
    } == ROUTINE_REQUIRED_FIELDS
    extra = parse_routine(_routine_body(agent_authored=True))
    assert is_refusal(extra)
    assert extra.context["field"] == "routine"
    missing = _routine_body()
    missing.pop("enabled")
    refused = parse_routine(missing)
    assert is_refusal(refused)
    null_goal = parse_routine(_routine_body(goal=None))
    assert is_refusal(null_goal)
    assert null_goal.context["field"] == "goal"


def test_schedule_is_cron_or_interval_with_iana_zone() -> None:
    cron = parse_routine_schedule({"kind": "cron", "expression": "30 6 * * *", "iana_zone": "UTC"})
    assert is_ok(cron)
    interval = parse_routine_schedule(
        {"kind": "interval", "every_ns": 3_600_000_000_000, "iana_zone": "Europe/London"}
    )
    assert is_ok(interval)
    assert interval.value.every_ns == 3_600_000_000_000
    no_zone = parse_routine_schedule({"kind": "cron", "expression": "0 9 * * *", "iana_zone": ""})
    assert is_refusal(no_zone)
    invented = parse_routine_schedule({"kind": "once", "iana_zone": "UTC"})
    assert is_refusal(invented)


def test_graph_template_ref_is_qualified_and_never_a_task_graph() -> None:
    ok = parse_graph_template_ref("research-corpus:survey")
    assert is_ok(ok)
    bare = parse_graph_template_ref("survey")
    assert is_refusal(bare)
    task_graph = parse_graph_template_ref("taskgraph:runtime")
    assert is_refusal(task_graph)
    daemon = parse_graph_template_ref("qma-daemon:act-observe-verify")
    assert is_refusal(daemon)
    assert "taskgraph" in FORBIDDEN_GRAPH_TEMPLATE_PLUGINS


def test_operator_only_ui_editable_record_homed_cap() -> None:
    parsed = parse_routine(_routine_body())
    assert is_ok(parsed)
    record = parsed.value
    assert record.scope is VariableScope.ROUTINE
    assert record.editability is VariableEditability.UI_EDITABLE
    assert record.ui_editable is True
    assert record.home == "routine_record"
    assert record.SCOPE is ROUTINE_SCOPE
    assert record.EDITABILITY is ROUTINE_EDITABILITY
    assert record.HOME is ROUTINE_HOME
    payload = record.to_payload()
    assert payload["max_concurrent_registry_key"] == MAX_CONCURRENT_REGISTRY_KEY
    assert MAX_CONCURRENT_REGISTRY_KEY == "registry:routine.max_concurrent"
    assert ROUTINE_WRITE_COMMAND == "routine.write"
    assert ROUTINE_CATCH_UP_COMMAND == "routine.catch_up"
    assert MISSED_FIRE_DISPOSITION == "recorded"

    assert source_may_write_routine("operator") is True
    assert source_may_write_routine(ROUTINE_WRITE_COMMAND) is True
    assert source_may_write_routine("model") is False
    assert source_may_write_routine("agent") is False
    refused = refuse_agent_routine_write(source="mission")
    assert is_refusal(refused)
    assert refused.context["command"] == ROUTINE_WRITE_COMMAND

    machine = authorize_routine_write(PrincipalClass.MACHINE)
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    assert machine.context["command"] == ROUTINE_WRITE_COMMAND
    operator = authorize_routine_write("operator")
    assert is_ok(operator)
    catch_up_machine = authorize_routine_catch_up("machine")
    assert is_refusal(catch_up_machine)
    assert OperatorPrincipalRequired.matches(catch_up_machine)
    assert catch_up_machine.context["command"] == ROUTINE_CATCH_UP_COMMAND
    assert has_routine_edit_kind() is False
    assert "routine" not in {kind.value for kind in RefinementEditKind}
