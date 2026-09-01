"""Role-keyed unexplained-drift response (TN-10/TN-24d; DEC-0195).

``role = live`` enters an entries-only stand-down cleared only by operator
``resume`` after a fresh reconciliation review. ``role = demo`` raises the same
severity alarm and continues the soak. Role — never world — selects the
behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import AccountRole, Ok, Result, World

from qmn.reconcile._refuse import clean_token, invalid, policy

__all__ = [
    "DRIFT_ALARM_CLASS",
    "OPERATOR_RESUME_CLEARANCE",
    "DriftResponse",
    "DriftResponseKind",
    "apply_drift_response",
    "clear_operator_review",
]

# Same live severity class the soak's demo-drift digest uses (DEC-0195).
DRIFT_ALARM_CLASS: Final[str] = "silent-degradation"
OPERATOR_RESUME_CLEARANCE: Final[str] = "operator-resume"


class DriftResponseKind(StrEnum):
    """Closed response set for unexplained drift (DEC-0195; TN-24d)."""

    ENTRIES_ONLY_STAND_DOWN = "entries-only-stand-down"
    ALARM_AND_CONTINUE = "alarm-and-continue"


@dataclass(frozen=True, slots=True)
class DriftResponse:
    """Binding-scoped drift disposition selected by account role."""

    kind: DriftResponseKind
    role: AccountRole
    alarm_class: str
    operator_review: bool
    entries_blocked: bool
    exits_and_protection_pass: bool
    continues_soak: bool
    clears_only_by: str | None
    world_ignored: bool = True

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "alarm_class": self.alarm_class,
                "clears_only_by": self.clears_only_by,
                "continues_soak": self.continues_soak,
                "entries_blocked": self.entries_blocked,
                "exits_and_protection_pass": self.exits_and_protection_pass,
                "kind": self.kind.value,
                "operator_review": self.operator_review,
                "role": self.role.value,
                "world_ignored": self.world_ignored,
            }
        )


def apply_drift_response(
    *,
    role: object,
    world: object | None = None,
) -> Result[DriftResponse]:
    """Select the drift response from binding role — world never participates.

    Live → entries-only stand-down + ``operator_review``, cleared only by
    operator ``resume``. Demo → same-severity alarm and continue. Other account
    roles that are not live money paths follow the demo continue posture.
    """
    resolved_role = _coerce_role(role)
    if resolved_role is None:
        return invalid(
            "role",
            "drift response is keyed on AccountRole",
            given=repr(role),
            allowed=[member.value for member in AccountRole],
        )
    # World is accepted only to prove it is ignored — never selects behavior.
    if world is not None and _coerce_world(world) is None and clean_token(world) is not None:
        return invalid(
            "world",
            "when supplied, world must be a World member; it still never selects "
            "the drift response",
            given=repr(world),
        )

    if resolved_role is AccountRole.LIVE:
        return Ok(
            DriftResponse(
                kind=DriftResponseKind.ENTRIES_ONLY_STAND_DOWN,
                role=resolved_role,
                alarm_class=DRIFT_ALARM_CLASS,
                operator_review=True,
                entries_blocked=True,
                exits_and_protection_pass=True,
                continues_soak=False,
                clears_only_by=OPERATOR_RESUME_CLEARANCE,
                world_ignored=True,
            )
        )

    return Ok(
        DriftResponse(
            kind=DriftResponseKind.ALARM_AND_CONTINUE,
            role=resolved_role,
            alarm_class=DRIFT_ALARM_CLASS,
            operator_review=True,
            entries_blocked=False,
            exits_and_protection_pass=True,
            continues_soak=True,
            clears_only_by=None,
            world_ignored=True,
        )
    )


def clear_operator_review(
    *,
    response: object,
    clearance: object,
    fresh_review: object = True,
) -> Result[DriftResponse]:
    """Clear live stand-down only via operator ``resume`` after fresh review.

    A restart, reconnect, or reconciled tick alone never clears. Demo alarms do
    not require resume clearance.
    """
    if not isinstance(response, DriftResponse):
        return invalid(
            "response",
            "clearance reads a DriftResponse",
            given=repr(response),
        )
    if response.kind is DriftResponseKind.ALARM_AND_CONTINUE:
        # Demo/soak posture — alarm recorded; no stand-down to clear.
        return Ok(
            DriftResponse(
                kind=response.kind,
                role=response.role,
                alarm_class=response.alarm_class,
                operator_review=False,
                entries_blocked=False,
                exits_and_protection_pass=True,
                continues_soak=response.continues_soak,
                clears_only_by=None,
                world_ignored=True,
            )
        )

    token = clean_token(clearance)
    if token != OPERATOR_RESUME_CLEARANCE:
        return policy(
            "clearance",
            "live drift stand-down clears only by operator resume after a fresh "
            "reconciliation review; a restart is never permission to resume",
            given=repr(clearance),
            required=OPERATOR_RESUME_CLEARANCE,
        )
    if fresh_review is not True:
        return policy(
            "fresh_review",
            "operator resume requires a fresh reconciliation review",
            given=repr(fresh_review),
        )
    return Ok(
        DriftResponse(
            kind=response.kind,
            role=response.role,
            alarm_class=response.alarm_class,
            operator_review=False,
            entries_blocked=False,
            exits_and_protection_pass=True,
            continues_soak=False,
            clears_only_by=OPERATOR_RESUME_CLEARANCE,
            world_ignored=True,
        )
    )


def _coerce_role(value: object) -> AccountRole | None:
    if isinstance(value, AccountRole):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return AccountRole(token)
    except ValueError:
        return None


def _coerce_world(value: object) -> World | None:
    if isinstance(value, World):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return World(token)
    except ValueError:
        return None
