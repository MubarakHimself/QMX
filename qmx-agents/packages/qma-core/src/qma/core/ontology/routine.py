"""Quant-owned Routine record (CT-49; AD-29; DEC-0328, DEC-0325, DEC-0323; FR-Q62).

Definitions only. A Routine is declarative daemon state — never agent-authored —
and is UI-editable only through an operator-principal ``routine.write``. There is
no ``routine`` edit kind, so no agent, hook, Role, or Mission may propose, stage,
or apply one. The daemon scheduler evaluates the schedule; this module does not
read a clock.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Final, Literal, cast

from qma.core.ontology.actor_id import ActorId
from qma.core.ontology.records import Goal
from qma.core.refusals.variants import OperatorPrincipalRequired
from qma.core.vocabulary.enums import (
    GraphArtifactKind,
    PrincipalClass,
    RefinementEditKind,
    VariableEditability,
    VariableScope,
)
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "FORBIDDEN_GRAPH_TEMPLATE_PLUGINS",
    "MAX_CONCURRENT_REGISTRY_KEY",
    "MISSED_FIRE_DISPOSITION",
    "ROUTINE_CATCH_UP_COMMAND",
    "ROUTINE_EDITABILITY",
    "ROUTINE_HOME",
    "ROUTINE_METADATA_KEYS",
    "ROUTINE_REQUIRED_FIELDS",
    "ROUTINE_SCOPE",
    "ROUTINE_WRITE_COMMAND",
    "SCHEDULE_KINDS",
    "Routine",
    "RoutineSchedule",
    "authorize_routine_catch_up",
    "authorize_routine_write",
    "has_routine_edit_kind",
    "parse_graph_template_ref",
    "parse_routine",
    "parse_routine_schedule",
    "refuse_agent_routine_write",
    "source_may_write_routine",
]


ROUTINE_WRITE_COMMAND: Final[str] = "routine.write"
ROUTINE_CATCH_UP_COMMAND: Final[str] = "routine.catch_up"
ROUTINE_HOME: Final[str] = "routine_record"
ROUTINE_SCOPE: Final[VariableScope] = VariableScope.ROUTINE
ROUTINE_EDITABILITY: Final[VariableEditability] = VariableEditability.UI_EDITABLE
MAX_CONCURRENT_REGISTRY_KEY: Final[str] = "registry:routine.max_concurrent"
MISSED_FIRE_DISPOSITION: Final[str] = "recorded"

ScheduleKind = Literal["cron", "interval"]
SCHEDULE_KINDS: Final[frozenset[str]] = frozenset({"cron", "interval"})

ROUTINE_REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "owner_ref",
        "schedule",
        "goal",
        "graph_template_ref",
        "enabled",
        "max_concurrent",
    }
)
ROUTINE_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "scope",
        "editability",
        "home",
        "max_concurrent_registry_key",
        "ui_editable",
    }
)

# A Routine names a Graph Template ``<plugin_id>:<local_id>``, never a Task Graph
# and never a daemon-claimed template (CT-49; AD-13; DEC-0328, DEC-0312).
FORBIDDEN_GRAPH_TEMPLATE_PLUGINS: Final[frozenset[str]] = frozenset(
    {
        "qma-daemon",
        "daemon",
        "qma",
        "taskgraph",
        "task_graph",
    }
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def has_routine_edit_kind() -> bool:
    """False — AD-22 mints no ``routine`` edit kind (CT-49; DEC-0328, DEC-0321)."""
    return "routine" in {kind.value for kind in RefinementEditKind}


def refuse_agent_routine_write(*, source: object = "model", **extra: object) -> TypedRefusal:
    """Refuse a model/agent/hook/Role/Mission attempt to author a Routine."""
    return _policy(
        "routine",
        "a Routine is declarative daemon state, never agent-authored, and is "
        "UI-editable only through an operator-principal routine.write; there is "
        "no routine edit kind (CT-49; DEC-0328, DEC-0323; FR-Q62)",
        source=repr(source),
        command=ROUTINE_WRITE_COMMAND,
        editability=ROUTINE_EDITABILITY.value,
        scope=ROUTINE_SCOPE.value,
        home=ROUTINE_HOME,
        **extra,
    )


def authorize_routine_write(principal: PrincipalClass | str) -> Result[PrincipalClass]:
    """Accept ``routine.write`` only from an operator principal (CT-49; FR-Q62)."""
    if isinstance(principal, PrincipalClass):
        resolved = principal
    else:
        try:
            resolved = PrincipalClass(principal)
        except ValueError:
            return OperatorPrincipalRequired.of(
                command=ROUTINE_WRITE_COMMAND,
                principal_class=str(principal),
            )
    if resolved is not PrincipalClass.OPERATOR:
        return OperatorPrincipalRequired.of(
            command=ROUTINE_WRITE_COMMAND,
            principal_class=resolved.value,
        )
    return Ok(resolved)


def authorize_routine_catch_up(principal: PrincipalClass | str) -> Result[PrincipalClass]:
    """Catch-up is an explicit operator-gated command — never a machine action."""
    if isinstance(principal, PrincipalClass):
        resolved = principal
    else:
        try:
            resolved = PrincipalClass(principal)
        except ValueError:
            return OperatorPrincipalRequired.of(
                command=ROUTINE_CATCH_UP_COMMAND,
                principal_class=str(principal),
            )
    if resolved is not PrincipalClass.OPERATOR:
        return OperatorPrincipalRequired.of(
            command=ROUTINE_CATCH_UP_COMMAND,
            principal_class=resolved.value,
        )
    return Ok(resolved)


def source_may_write_routine(source: object) -> bool:
    """True only for the operator write path — never a model or machine source."""
    return source in (None, "operator", ROUTINE_WRITE_COMMAND)


def parse_graph_template_ref(value: object) -> Result[str]:
    """Accept fully-qualified ``<plugin_id>:<local_id>``; refuse a Task Graph id."""
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            "graph_template_ref",
            "graph_template_ref is the fully-qualified Graph Template id "
            "<plugin_id>:<local_id>, never a Task Graph (CT-49; AD-13; FR-Q62)",
            given=repr(value),
        )
    token = value.strip()
    if token.count(":") != 1:
        return _invalid(
            "graph_template_ref",
            "graph_template_ref must be fully-qualified <plugin_id>:<local_id>; "
            "a bare local id is refused (CT-49; DEC-0312; FR-Q62)",
            given=token,
        )
    plugin_id, local_id = token.split(":", 1)
    if plugin_id == "" or local_id == "":
        return _invalid(
            "graph_template_ref",
            "graph_template_ref segments must be non-empty (CT-49; AD-13; FR-Q62)",
            given=token,
        )
    if plugin_id in FORBIDDEN_GRAPH_TEMPLATE_PLUGINS:
        return _invalid(
            "graph_template_ref",
            "a Routine names a Graph Template, never a Task Graph or a "
            "daemon-claimed template (CT-49; AD-13; DEC-0328, DEC-0312; FR-Q62)",
            given=token,
            artifact_kind=GraphArtifactKind.TASK_GRAPH.value,
        )
    return Ok(token)


@dataclass(frozen=True, slots=True)
class RoutineSchedule:
    """Cron expression or fixed interval, each with an explicit IANA zone (AD-6)."""

    kind: ScheduleKind
    iana_zone: str
    expression: str | None = None
    every_ns: int | None = None

    def __post_init__(self) -> None:
        if self.kind == "cron":
            if self.expression is None or self.expression.strip() == "":
                msg = "cron schedule requires a cron expression (CT-49; FR-Q62)"
                raise ValueError(msg)
            if self.every_ns is not None:
                msg = "cron schedule does not carry every_ns (CT-49; FR-Q62)"
                raise ValueError(msg)
        elif self.kind == "interval":
            if self.every_ns is None or isinstance(self.every_ns, bool) or self.every_ns <= 0:
                msg = "interval schedule requires a positive every_ns (CT-49; FR-Q62)"
                raise ValueError(msg)
            if self.expression is not None:
                msg = "interval schedule does not carry a cron expression (CT-49; FR-Q62)"
                raise ValueError(msg)
        else:
            msg = "schedule kind is cron or interval (CT-49; FR-Q62)"
            raise ValueError(msg)
        if not self.iana_zone.strip():
            msg = "schedule carries an explicit IANA zone (CT-49; AD-6; FR-Q62)"
            raise ValueError(msg)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind,
            "iana_zone": self.iana_zone,
        }
        if self.kind == "cron":
            payload["expression"] = self.expression
        else:
            payload["every_ns"] = self.every_ns
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class Routine:
    """Durable Quant-owned scheduled trigger (CT-49; AD-29; DEC-0328).

    Exactly seven record fields: id, owner_ref, schedule, goal,
    graph_template_ref, enabled, max_concurrent.
    """

    id: str
    owner_ref: ActorId
    schedule: RoutineSchedule
    goal: Goal
    graph_template_ref: str
    enabled: bool
    max_concurrent: int

    SCOPE: ClassVar[VariableScope] = ROUTINE_SCOPE
    EDITABILITY: ClassVar[VariableEditability] = ROUTINE_EDITABILITY
    HOME: ClassVar[str] = ROUTINE_HOME

    def __post_init__(self) -> None:
        if not self.id.strip():
            msg = "Routine id is a non-empty record identity (CT-49; FR-Q62)"
            raise ValueError(msg)
        if isinstance(self.max_concurrent, bool) or self.max_concurrent < 1:
            msg = "max_concurrent is a positive count (CT-49; FR-Q62)"
            raise ValueError(msg)

    @property
    def scope(self) -> VariableScope:
        return ROUTINE_SCOPE

    @property
    def editability(self) -> VariableEditability:
        return ROUTINE_EDITABILITY

    @property
    def home(self) -> str:
        return ROUTINE_HOME

    @property
    def ui_editable(self) -> bool:
        return True

    @property
    def max_concurrent_registry_key(self) -> str:
        return MAX_CONCURRENT_REGISTRY_KEY

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "id": self.id,
                "owner_ref": self.owner_ref.value,
                "schedule": dict(self.schedule.to_payload()),
                "goal": self.goal.text,
                "graph_template_ref": self.graph_template_ref,
                "enabled": self.enabled,
                "max_concurrent": self.max_concurrent,
                "scope": ROUTINE_SCOPE.value,
                "editability": ROUTINE_EDITABILITY.value,
                "home": ROUTINE_HOME,
                "max_concurrent_registry_key": MAX_CONCURRENT_REGISTRY_KEY,
            }
        )


def parse_routine_schedule(value: object) -> Result[RoutineSchedule]:
    """Parse a cron or interval schedule with an explicit IANA zone."""
    if isinstance(value, RoutineSchedule):
        return Ok(value)
    if not isinstance(value, Mapping):
        return _invalid(
            "schedule",
            "schedule is a cron expression or interval with an explicit IANA "
            "zone (CT-49; AD-6; FR-Q62)",
            given=repr(value),
        )
    entry = cast("Mapping[str, object]", value)
    kind_raw = entry.get("kind")
    if not isinstance(kind_raw, str) or kind_raw not in SCHEDULE_KINDS:
        return _invalid(
            "schedule.kind",
            "schedule kind is cron or interval (CT-49; FR-Q62)",
            given=repr(kind_raw),
            allowed=sorted(SCHEDULE_KINDS),
        )
    zone = entry.get("iana_zone")
    if not isinstance(zone, str) or zone.strip() == "":
        return _invalid(
            "schedule.iana_zone",
            "schedule carries an explicit IANA zone resolved at evaluation time; "
            "never the host local zone (CT-49; AD-6; FR-Q62)",
            given=repr(zone),
        )
    if kind_raw == "cron":
        expression = entry.get("expression")
        if not isinstance(expression, str) or expression.strip() == "":
            return _invalid(
                "schedule.expression",
                "cron schedule carries a non-empty cron expression (CT-49; FR-Q62)",
                given=repr(expression),
            )
        extra = set(entry) - {"kind", "iana_zone", "expression"}
        if extra:
            return _invalid(
                "schedule",
                "cron schedule carries kind, expression, and iana_zone only (CT-49; FR-Q62)",
                given=sorted(extra),
            )
        return Ok(
            RoutineSchedule(kind="cron", iana_zone=zone.strip(), expression=expression.strip())
        )

    every_ns = entry.get("every_ns")
    if isinstance(every_ns, bool) or not isinstance(every_ns, int) or every_ns <= 0:
        return _invalid(
            "schedule.every_ns",
            "interval schedule carries a positive every_ns count (CT-49; FR-Q62)",
            given=repr(every_ns),
        )
    extra = set(entry) - {"kind", "iana_zone", "every_ns"}
    if extra:
        return _invalid(
            "schedule",
            "interval schedule carries kind, every_ns, and iana_zone only (CT-49; FR-Q62)",
            given=sorted(extra),
        )
    return Ok(RoutineSchedule(kind="interval", iana_zone=zone.strip(), every_ns=every_ns))


def _parse_goal(value: object) -> Result[Goal]:
    if isinstance(value, Goal):
        if value.text.strip() == "":
            return _invalid("goal", "goal text is non-empty (CT-49; AD-12; FR-Q62)")
        return Ok(value)
    if isinstance(value, str) and value.strip() != "":
        return Ok(Goal(text=value.strip()))
    if isinstance(value, Mapping):
        text = cast("Mapping[str, object]", value).get("text")
        if isinstance(text, str) and text.strip() != "":
            return Ok(Goal(text=text.strip()))
    return _invalid(
        "goal",
        "goal is the Goal supplied to the Mission Compiler (CT-49; AD-12; FR-Q62)",
        given=repr(cast("object", value)),
    )


def parse_routine(value: object) -> Result[Routine]:
    """Validate a Routine record: exactly the seven CT-49 fields, no more."""
    if isinstance(value, Routine):
        return Ok(value)
    if not isinstance(value, Mapping):
        return _invalid("routine", "a Routine is an object (CT-49; FR-Q62)", given=repr(value))
    entry = cast("Mapping[str, object]", value)
    unknown = set(entry) - ROUTINE_REQUIRED_FIELDS - ROUTINE_METADATA_KEYS
    if unknown:
        return _invalid(
            "routine",
            "a Routine carries exactly id, owner_ref, schedule, goal, "
            "graph_template_ref, enabled, and max_concurrent (CT-49; FR-Q62)",
            given=sorted(unknown),
        )
    missing = sorted(field for field in ROUTINE_REQUIRED_FIELDS if field not in entry)
    if missing:
        return _invalid(
            "routine",
            "an absent required Routine field is a load defect, never a "
            "best-effort read (CT-49; FR-Q62)",
            given=missing,
        )
    for field in ROUTINE_REQUIRED_FIELDS:
        if entry.get(field) is None:
            return _invalid(
                field,
                "fp1 null is prohibited; an absent value is an omitted key "
                "(CT-49; parent AD-10; FR-Q62)",
            )

    raw_id = entry.get("id")
    if not isinstance(raw_id, str) or raw_id.strip() == "":
        return _invalid(
            "id",
            "id is the Routine's own stable identity (CT-49; FR-Q62)",
            given=repr(raw_id),
        )

    owner_raw = entry.get("owner_ref")
    if isinstance(owner_raw, ActorId):
        owner = Ok(owner_raw)
    else:
        owner = ActorId.try_create(owner_raw)
        if not isinstance(owner, Ok):
            return _invalid(
                "owner_ref",
                "owner_ref is the owning Quant ActorId quant:<desk_slug>/<quant_slug> "
                "(CT-49; AD-7; FR-Q62)",
                given=repr(owner_raw),
            )

    schedule = parse_routine_schedule(entry.get("schedule"))
    if not isinstance(schedule, Ok):
        return schedule
    goal = _parse_goal(entry.get("goal"))
    if not isinstance(goal, Ok):
        return goal
    template = parse_graph_template_ref(entry.get("graph_template_ref"))
    if not isinstance(template, Ok):
        return template

    enabled = entry.get("enabled")
    if not isinstance(enabled, bool):
        return _invalid(
            "enabled",
            "enabled is a boolean flag; a disabled Routine holds its schedule "
            "and the scheduler mints no firing (CT-49; FR-Q62)",
            given=repr(enabled),
        )

    cap = entry.get("max_concurrent")
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        return _invalid(
            "max_concurrent",
            "max_concurrent is a positive count carried by "
            "registry:routine.max_concurrent (CT-49; DEC-0325; FR-Q62)",
            given=repr(cap),
            registry_key=MAX_CONCURRENT_REGISTRY_KEY,
        )

    return Ok(
        Routine(
            id=raw_id.strip(),
            owner_ref=owner.value,
            schedule=schedule.value,
            goal=goal.value,
            graph_template_ref=template.value,
            enabled=enabled,
            max_concurrent=cap,
        )
    )
