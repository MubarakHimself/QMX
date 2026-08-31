"""TN-21 replay :class:`~qmn.venue.port.VenueClientPort` (Story 24.8).

Implements the same port as the live client and FEAT-0023 double, reading
injected recorded CT-20 / CT-10 observations. It resolves no credential,
opens no socket, and every command attempt is a typed policy refusal —
recorded venue answers ride as evidence only (FR-061; DEC-0206, DEC-0228).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Account,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretValue,
    TypedRefusal,
    VenueId,
    World,
    is_refusal,
)
from qmf.venue.commands import Command, CompoundCommand, SubmissionResult
from qmf.venue.connection import ConnectionManager
from qmf.venue.events import Reconciliation, ReconciliationVerdict

from qmn.venue.conformance import compound_command_acceptance_blocked
from qmn.venue.port import VenueClientKind
from qmn.venue.verify import VenueFactVerification, ctrader_static_declaration

__all__ = [
    "REPLAY_SUBMIT_REFUSAL_CATEGORY",
    "ReplayAdapter",
    "replay_command_attempt_refused",
]


REPLAY_SUBMIT_REFUSAL_CATEGORY: Final[RefusalCategory] = RefusalCategory.POLICY_REJECTION

_REPLAY_SUBMIT_REFUSAL: Final[TypedRefusal] = TypedRefusal(
    category=REPLAY_SUBMIT_REFUSAL_CATEGORY,
    retryability=Retryability.NO,
    context={
        "field": "submit",
        "reason": "replay VenueClientPort refuses every command attempt; "
        "recorded venue answers ride as evidence only — no submit side effect",
        "world": World.REPLAY.value,
        "socket_opened": False,
        "credential_resolved": False,
    },
)


def replay_command_attempt_refused() -> TypedRefusal:
    """Typed policy refusal every replay command attempt returns (FR-061)."""
    return _REPLAY_SUBMIT_REFUSAL


@dataclass
class ReplayAdapter:
    """Replay VenueClientPort — no credential, no socket, no submit side effect."""

    _world: World
    _venue_id: VenueId
    _recorded: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    _account: Account | None = None
    _session_open: bool = False
    _capabilities_verified: bool = False
    _verification: VenueFactVerification | None = None
    _observations: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    _socket_opened: bool = False
    _credential_resolved: bool = False
    _commands_submitted: int = 0

    @classmethod
    def try_create(
        cls,
        world: object,
        venue_id: object,
        *,
        recorded: object = (),
        verification: object = None,
    ) -> Result[ReplayAdapter]:
        """Build a replay adapter for ``(world=replay, VenueId)`` with injected evidence."""
        if not isinstance(world, World):
            return _invalid(
                "world",
                "replay adapter is selected by (world, VenueId)",
                given=repr(world),
            )
        if world is not World.REPLAY:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "world",
                    "reason": "ReplayAdapter binds only world=replay; live and "
                    "conformance kinds use their own VenueClientPort implementations",
                    "world": world.value,
                },
            )
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid(
                "venue_id",
                "replay adapter requires a valid VenueId",
                given=repr(venue_id),
            )
        rows = _coerce_recorded(recorded)
        if is_refusal(rows):
            return rows
        ver: VenueFactVerification | None
        if verification is None:
            ver = None
        elif isinstance(verification, VenueFactVerification):
            ver = verification
        else:
            return _invalid(
                "verification",
                "when supplied, verification must be a VenueFactVerification",
                given=type(verification).__name__,
            )
        return Ok(
            cls(
                _world=world,
                _venue_id=venue_id,
                _recorded=[dict(item) for item in rows.value],
                _verification=ver,
            )
        )

    @property
    def kind(self) -> VenueClientKind:
        return VenueClientKind.REPLAY

    @property
    def venue_id(self) -> VenueId:
        return self._venue_id

    @property
    def world(self) -> World:
        return self._world

    @property
    def socket_opened(self) -> bool:
        """Always False — replay opens no venue socket (DEC-0206)."""
        return self._socket_opened

    @property
    def credential_resolved(self) -> bool:
        """Always False — replay resolves no credential reference (DEC-0206)."""
        return self._credential_resolved

    @property
    def commands_submitted(self) -> int:
        """Count of command attempts that reached submit — always refused, never sent."""
        return self._commands_submitted

    def bind_credential(self, credential: object) -> Result[bool]:
        """Refuse every credential bind — replay holds no venue secret."""
        if isinstance(credential, (SecretRef, SecretValue)):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "credential",
                    "reason": "replay resolves no credential reference and holds "
                    "no venue secret",
                    "given_type": type(credential).__name__,
                },
            )
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "credential",
                "reason": "replay resolves no credential reference and holds "
                "no venue secret",
                "given": repr(credential),
            },
        )

    def bind_connection_manager(self, connection_manager: object) -> Result[bool]:
        """Refuse ConnectionManager wiring — no socket / session owner in replay."""
        del connection_manager
        return TypedRefusal(
            category=RefusalCategory.POLICY_REJECTION,
            retryability=Retryability.NO,
            context={
                "field": "connection_manager",
                "reason": "replay opens no socket and never binds a ConnectionManager",
                "connection_manager_type": ConnectionManager.__name__,
            },
        )

    def open_session(self, account: object) -> Result[bool]:
        if not isinstance(account, Account):
            return _invalid(
                "account",
                "open_session requires an Account",
                given=repr(account),
            )
        if account.venue != self._venue_id:
            return _invalid(
                "account",
                "account does not belong to this VenueId",
                venue=self._venue_id.value,
                account_venue=account.venue.value,
            )
        self._account = account
        self._session_open = True
        return Ok(True)

    def close_session(self) -> Result[bool]:
        self._session_open = False
        self._account = None
        self._capabilities_verified = False
        return Ok(True)

    def accept_verification(self, verification: object) -> Result[bool]:
        """Optionally bind a precomputed Story 24.2 verification for profile parity."""
        if not isinstance(verification, VenueFactVerification):
            return _invalid(
                "verification",
                "accept_verification requires a VenueFactVerification",
                given=repr(verification),
            )
        self._verification = verification
        return Ok(True)

    def verify_capabilities(self) -> Result[Mapping[str, object]]:
        """CT-18 readiness from injected verification or recorded capability profile.

        No network and no credential — static declaration presence is checked
        locally; measured facts come from the injected verification or a recorded
        capability-profile observation.
        """
        if not self._session_open or self._account is None:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "session",
                    "reason": "capability verification requires an open session",
                },
                after_condition_descriptor="open_session",
            )
        declaration = ctrader_static_declaration()
        if is_refusal(declaration):
            return declaration
        if self._verification is not None:
            if not self._verification.command_sequencer_open:
                return TypedRefusal(
                    category=RefusalCategory.POLICY_REJECTION,
                    retryability=Retryability.NO,
                    context={
                        "field": "command_sequencer",
                        "reason": "verified profile left the command sequencer closed",
                        "defects": {
                            key: value.value
                            for key, value in self._verification.defects.items()
                        },
                    },
                )
            self._capabilities_verified = True
            profile: dict[str, object] = {
                "verified": True,
                "static_declaration_present": True,
                "measured_at_connection": True,
                "profile_version": self._verification.profile_version,
                "command_sequencer_open": True,
                "market_data_recordable": self._verification.market_data_recordable,
                "proto_tag": 91,
                "world": World.REPLAY.value,
                "socket_opened": False,
                "credential_resolved": False,
            }
            self._observations.append({"kind": "capability-profile", "profile": dict(profile)})
            return Ok(profile)

        recorded_profile = _find_recorded_capability_profile(self._recorded)
        if recorded_profile is not None:
            self._capabilities_verified = True
            profile = {
                "verified": True,
                "static_declaration_present": True,
                "measured_at_connection": True,
                "profile_version": recorded_profile.get("profile_version", 1),
                "command_sequencer_open": bool(
                    recorded_profile.get("command_sequencer_open", True)
                ),
                "market_data_recordable": bool(
                    recorded_profile.get("market_data_recordable", True)
                ),
                "proto_tag": recorded_profile.get("proto_tag", 91),
                "world": World.REPLAY.value,
                "socket_opened": False,
                "credential_resolved": False,
            }
            self._observations.append({"kind": "capability-profile", "profile": dict(profile)})
            return Ok(profile)

        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=Retryability.AFTER_CONDITION,
            context={
                "field": "measured_profile",
                "reason": "replay requires an injected VenueFactVerification or a "
                "recorded capability-profile observation before verify_capabilities "
                "can open the sequencer",
                "static_declaration_present": True,
            },
            after_condition_descriptor="accept_verification or recorded capability-profile",
        )

    def submit(self, command: object) -> Result[SubmissionResult]:
        if isinstance(command, CompoundCommand):
            return compound_command_acceptance_blocked()
        if not isinstance(command, Command):
            return _invalid(
                "command",
                "submit requires a CT-19 Command",
                given=type(command).__name__,
            )
        # Count the attempt, then refuse — no wire, no side effect.
        self._commands_submitted += 1
        return replay_command_attempt_refused()

    def observations(self) -> Result[Sequence[Mapping[str, object]]]:
        """Drain capability observations plus injected recorded CT-20/CT-10 rows."""
        combined: list[Mapping[str, object]] = [
            MappingProxyType(dict(item)) for item in self._observations
        ]
        combined.extend(MappingProxyType(dict(item)) for item in self._recorded)
        return Ok(tuple(combined))

    def reconcile(self) -> Result[Reconciliation]:
        """Replay reconciliation is evidence-only against recorded observations."""
        if not self._session_open:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "session",
                    "reason": "reconcile requires an open replay session",
                },
                after_condition_descriptor="open_session",
            )
        return Ok(
            Reconciliation(
                verdict=ReconciliationVerdict.RECONCILED,
                detail="replay adapter evidence-only reconciliation over recorded "
                "CT-20/CT-10 observations",
            )
        )


def _find_recorded_capability_profile(
    recorded: Sequence[Mapping[str, object]],
) -> Mapping[str, object] | None:
    for item in recorded:
        if item.get("kind") != "capability-profile":
            continue
        profile = item.get("profile")
        if isinstance(profile, Mapping):
            return cast("Mapping[str, object]", profile)
    return None


def _coerce_recorded(
    recorded: object,
) -> Result[tuple[Mapping[str, object], ...]]:
    if isinstance(recorded, (str, bytes)) or not isinstance(recorded, Sequence):
        return _invalid(
            "recorded",
            "replay injects a sequence of recorded CT-20/CT-10 observation mappings",
            given=type(recorded).__name__,
        )
    rows: list[Mapping[str, object]] = []
    for index, item in enumerate(cast("Sequence[object]", recorded)):
        if not isinstance(item, Mapping):
            return _invalid(
                "recorded",
                "each recorded observation is a mapping",
                index=index,
                given=type(item).__name__,
            )
        rows.append(MappingProxyType(dict(cast("Mapping[str, object]", item))))
    return Ok(tuple(rows))


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )
