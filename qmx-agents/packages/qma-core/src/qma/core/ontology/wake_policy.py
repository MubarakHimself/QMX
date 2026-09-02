"""Quant ``WakePolicy`` definition (CT-48; AD-20; DEC-0319, DEC-0325; FR-Q61).

Definitions only. The policy is a field of the Quant record — operator-authored,
``ui-editable``, scope ``quant``. No model authors, alters, or overrides it.
The daemon's deterministic scheduler evaluates it at delivery time.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Final, cast

from qma.core.refusals.variants import OperatorPrincipalRequired
from qma.core.vocabulary.enums import (
    MessageKind,
    PrincipalClass,
    VariableEditability,
    VariableScope,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "MAX_WAKES_PER_WINDOW_REGISTRY_KEY",
    "QUANT_WRITE_COMMAND",
    "QUIET_HOURS_REGISTRY_KEY",
    "WAKE_CONDITION_ANY",
    "WAKE_POLICY_EDITABILITY",
    "WAKE_POLICY_HOME",
    "WAKE_POLICY_SCOPE",
    "QuietHours",
    "WakePolicy",
    "authorize_quant_write",
    "is_wake_condition",
    "parse_quiet_hours",
    "parse_wake_policy",
    "refuse_model_wake_policy_write",
    "source_may_write_wake_policy",
    "wake_conditions_match",
]


QUANT_WRITE_COMMAND: Final[str] = "quant.write"
WAKE_POLICY_HOME: Final[str] = "quant_record.WakePolicy"
WAKE_POLICY_SCOPE: Final[VariableScope] = VariableScope.QUANT
WAKE_POLICY_EDITABILITY: Final[VariableEditability] = VariableEditability.UI_EDITABLE
QUIET_HOURS_REGISTRY_KEY: Final[str] = "registry:quant.quiet_hours"
MAX_WAKES_PER_WINDOW_REGISTRY_KEY: Final[str] = "registry:quant.max_wakes_per_window"
WAKE_CONDITION_ANY: Final[str] = "any"

_MINUTES_PER_DAY: Final[int] = 24 * 60


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


def refuse_model_wake_policy_write(*, source: object = "model", **extra: object) -> TypedRefusal:
    """Refuse a model/agent/hook attempt to author, alter, or override WakePolicy."""
    return _policy(
        "wake_policy",
        "WakePolicy is operator-authored, ui-editable, and scoped to the Quant; "
        "no model authors, alters, or overrides it (CT-48; DEC-0319, DEC-0325; FR-Q61)",
        source=repr(source),
        command=QUANT_WRITE_COMMAND,
        editability=WAKE_POLICY_EDITABILITY.value,
        scope=WAKE_POLICY_SCOPE.value,
        home=WAKE_POLICY_HOME,
        **extra,
    )


def authorize_quant_write(principal: PrincipalClass | str) -> Result[PrincipalClass]:
    """Accept ``quant.write`` only from an operator principal (CT-48; FR-Q61)."""
    if isinstance(principal, PrincipalClass):
        resolved = principal
    else:
        try:
            resolved = PrincipalClass(principal)
        except ValueError:
            return OperatorPrincipalRequired.of(
                command=QUANT_WRITE_COMMAND,
                principal_class=str(principal),
            )
    if resolved is not PrincipalClass.OPERATOR:
        return OperatorPrincipalRequired.of(
            command=QUANT_WRITE_COMMAND,
            principal_class=resolved.value,
        )
    return Ok(resolved)


def _parse_hhmm(value: object, field: str) -> Result[int]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field,
            "quiet hours bound is HH:MM in 24-hour form (CT-48; DEC-0319; FR-Q61)",
            given=repr(value),
        )
    token = value.strip()
    parts = token.split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return _invalid(
            field,
            "quiet hours bound is HH:MM in 24-hour form (CT-48; DEC-0319; FR-Q61)",
            given=token,
        )
    hour = int(parts[0])
    minute = int(parts[1])
    if hour > 23 or minute > 59 or len(parts[0]) != 2 or len(parts[1]) != 2:
        return _invalid(
            field,
            "quiet hours bound is HH:MM with hour 00-23 and minute 00-59 (CT-48; DEC-0319; FR-Q61)",
            given=token,
        )
    return Ok(hour * 60 + minute)


def _format_hhmm(minutes: int) -> str:
    hour, minute = divmod(minutes, 60)
    return f"{hour:02d}:{minute:02d}"


def is_wake_condition(value: object) -> bool:
    """True when ``value`` is ``any`` or a closed MessageKind member."""
    if not isinstance(value, str):
        return False
    if value == WAKE_CONDITION_ANY:
        return True
    try:
        parse_closed(MessageKind, value)
    except VocabularyError:
        return False
    return True


def wake_conditions_match(conditions: frozenset[str], kind: MessageKind | str) -> bool:
    """True when the operator-authored conditions wake this MessageKind."""
    token = kind.value if isinstance(kind, MessageKind) else kind
    return WAKE_CONDITION_ANY in conditions or token in conditions


@dataclass(frozen=True, slots=True)
class QuietHours:
    """Daily interval plus its IANA zone (``registry:quant.quiet_hours``).

    ``start_minute`` is inclusive, ``end_minute`` is exclusive. When start >= end
    the interval wraps midnight. The zone is an explicit IANA name resolved at
    evaluation time — never the host local zone.
    """

    start_minute: int
    end_minute: int
    iana_zone: str

    def __post_init__(self) -> None:
        if not (0 <= self.start_minute < _MINUTES_PER_DAY):
            msg = "quiet hours start_minute is in 0..1439"
            raise ValueError(msg)
        if not (0 <= self.end_minute < _MINUTES_PER_DAY):
            msg = "quiet hours end_minute is in 0..1439"
            raise ValueError(msg)
        if self.start_minute == self.end_minute:
            msg = "quiet hours start and end must differ (CT-48; FR-Q61)"
            raise ValueError(msg)
        if not self.iana_zone.strip():
            msg = "quiet hours carry an explicit IANA zone (CT-48; FR-Q61)"
            raise ValueError(msg)

    @property
    def wraps_midnight(self) -> bool:
        return self.start_minute > self.end_minute

    @property
    def start(self) -> str:
        return _format_hhmm(self.start_minute)

    @property
    def end(self) -> str:
        return _format_hhmm(self.end_minute)

    @property
    def registry_key(self) -> str:
        return QUIET_HOURS_REGISTRY_KEY

    def contains_minute(self, minute_of_day: int) -> bool:
        """True when ``minute_of_day`` (0..1439) lies in the daily interval."""
        if self.wraps_midnight:
            return minute_of_day >= self.start_minute or minute_of_day < self.end_minute
        return self.start_minute <= minute_of_day < self.end_minute

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "start": self.start,
                "end": self.end,
                "iana_zone": self.iana_zone,
                "registry_key": QUIET_HOURS_REGISTRY_KEY,
            }
        )


@dataclass(frozen=True, slots=True)
class WakePolicy:
    """Operator-authored Quant wake policy (CT-48; AD-20; DEC-0319, DEC-0325).

    The spine mints no default for an unauthored policy; absence is ``None`` on
    the Quant record, never a synthesized interval or cap.
    """

    wake_conditions: frozenset[str]
    quiet_hours: QuietHours | None = None
    max_wakes_per_window: int | None = None

    SCOPE: ClassVar[VariableScope] = WAKE_POLICY_SCOPE
    EDITABILITY: ClassVar[VariableEditability] = WAKE_POLICY_EDITABILITY
    HOME: ClassVar[str] = WAKE_POLICY_HOME

    def __post_init__(self) -> None:
        object.__setattr__(self, "wake_conditions", frozenset(self.wake_conditions))
        if self.max_wakes_per_window is not None and (
            isinstance(self.max_wakes_per_window, bool) or self.max_wakes_per_window < 0
        ):
            msg = "max_wakes_per_window is a non-negative count (CT-48; FR-Q61)"
            raise ValueError(msg)

    @property
    def scope(self) -> VariableScope:
        return WAKE_POLICY_SCOPE

    @property
    def editability(self) -> VariableEditability:
        return WAKE_POLICY_EDITABILITY

    @property
    def home(self) -> str:
        return WAKE_POLICY_HOME

    @property
    def ui_editable(self) -> bool:
        return True

    def matches(self, kind: MessageKind | str) -> bool:
        return wake_conditions_match(self.wake_conditions, kind)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "wake_conditions": sorted(self.wake_conditions),
            "scope": WAKE_POLICY_SCOPE.value,
            "editability": WAKE_POLICY_EDITABILITY.value,
            "home": WAKE_POLICY_HOME,
            "quiet_hours_registry_key": QUIET_HOURS_REGISTRY_KEY,
            "max_wakes_per_window_registry_key": MAX_WAKES_PER_WINDOW_REGISTRY_KEY,
        }
        if self.quiet_hours is not None:
            payload["quiet_hours"] = dict(self.quiet_hours.to_payload())
        if self.max_wakes_per_window is not None:
            payload["max_wakes_per_window"] = self.max_wakes_per_window
        return MappingProxyType(payload)


def parse_quiet_hours(value: object) -> Result[QuietHours]:
    """Parse a daily interval plus its IANA zone (``registry:quant.quiet_hours``)."""
    if isinstance(value, QuietHours):
        return Ok(value)
    if not isinstance(value, Mapping):
        return _invalid(
            "quiet_hours",
            "quiet hours is a daily interval plus its IANA zone "
            "(registry:quant.quiet_hours) (CT-48; DEC-0319, DEC-0325; FR-Q61)",
            given=repr(value),
            registry_key=QUIET_HOURS_REGISTRY_KEY,
        )
    entry = cast("Mapping[str, object]", value)
    start = _parse_hhmm(entry.get("start"), "quiet_hours.start")
    if not isinstance(start, Ok):
        return start
    end = _parse_hhmm(entry.get("end"), "quiet_hours.end")
    if not isinstance(end, Ok):
        return end
    if start.value == end.value:
        return _invalid(
            "quiet_hours",
            "quiet hours start and end must differ (CT-48; DEC-0319; FR-Q61)",
        )
    zone = entry.get("iana_zone")
    if not isinstance(zone, str) or zone.strip() == "":
        return _invalid(
            "quiet_hours.iana_zone",
            "quiet hours carry an explicit IANA zone resolved at evaluation time; "
            "never the host local zone (CT-48; AD-6; FR-Q61)",
            given=repr(zone),
            registry_key=QUIET_HOURS_REGISTRY_KEY,
        )
    return Ok(
        QuietHours(
            start_minute=start.value,
            end_minute=end.value,
            iana_zone=zone.strip(),
        )
    )


def _parse_wake_conditions(value: object) -> Result[frozenset[str]]:
    if value is None:
        return _invalid(
            "wake_conditions",
            "wake_conditions is an operator-authored set, never null; the spine "
            "mints no default (CT-48; DEC-0319, DEC-0325; FR-Q61)",
        )
    if isinstance(value, str):
        items: tuple[object, ...] = (value,)
    elif isinstance(value, (list, tuple, set, frozenset)):
        items = tuple(cast("list[object] | tuple[object, ...] | set[object]", value))
    else:
        return _invalid(
            "wake_conditions",
            "wake_conditions is a set of 'any' or MessageKind values (CT-48; DEC-0319; FR-Q61)",
            given=repr(value),
        )
    parsed: set[str] = set()
    for item in items:
        if not isinstance(item, str) or item.strip() == "":
            return _invalid(
                "wake_conditions",
                "wake_conditions members are 'any' or a closed MessageKind "
                "(CT-48; DEC-0319; FR-Q61)",
                given=repr(item),
            )
        token = item.strip()
        if not is_wake_condition(token):
            return _invalid(
                "wake_conditions",
                "wake_conditions members are 'any' or a closed MessageKind "
                "(CT-48; DEC-0319; FR-Q61)",
                given=token,
            )
        parsed.add(token)
    return Ok(frozenset(parsed))


def parse_wake_policy(value: object) -> Result[WakePolicy]:
    """Parse an operator-authored WakePolicy; the spine mints no default."""
    if isinstance(value, WakePolicy):
        return Ok(value)
    if value is None:
        return _invalid(
            "wake_policy",
            "a WakePolicy is operator-authored; the spine mints no default for "
            "an unauthored policy (CT-48; DEC-0319, DEC-0325; FR-Q61)",
        )
    if not isinstance(value, Mapping):
        return _invalid("wake_policy", "a WakePolicy is an object (CT-48; FR-Q61)")
    entry = cast("Mapping[str, object]", value)
    if "wake_conditions" not in entry:
        return _invalid(
            "wake_conditions",
            "WakePolicy carries operator-authored wake_conditions (CT-48; DEC-0319; FR-Q61)",
        )
    conditions = _parse_wake_conditions(entry.get("wake_conditions"))
    if not isinstance(conditions, Ok):
        return conditions

    quiet: QuietHours | None = None
    if "quiet_hours" in entry:
        parsed_quiet = parse_quiet_hours(entry.get("quiet_hours"))
        if not isinstance(parsed_quiet, Ok):
            return parsed_quiet
        quiet = parsed_quiet.value

    cap: int | None = None
    if "max_wakes_per_window" in entry:
        raw_cap = entry.get("max_wakes_per_window")
        if isinstance(raw_cap, bool) or not isinstance(raw_cap, int) or raw_cap < 0:
            return _invalid(
                "max_wakes_per_window",
                "max_wakes_per_window is a non-negative count "
                "(registry:quant.max_wakes_per_window) (CT-48; DEC-0319, DEC-0325; FR-Q61)",
                given=repr(raw_cap),
                registry_key=MAX_WAKES_PER_WINDOW_REGISTRY_KEY,
            )
        cap = raw_cap

    return Ok(
        WakePolicy(
            wake_conditions=conditions.value,
            quiet_hours=quiet,
            max_wakes_per_window=cap,
        )
    )


def source_may_write_wake_policy(source: object) -> bool:
    """True only for the operator write path — never a model or machine source."""
    return source in (None, "operator", QUANT_WRITE_COMMAND)
