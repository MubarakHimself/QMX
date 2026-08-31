"""Node-minted :class:`VenueClientPort` over CT-19/CT-20 (DEC-0196, DEC-0228).

``qmf-venue`` exposes no injectable port seam at the inventory baseline, so the
node mints this Protocol over the CT-19 command and CT-20 event/reconciliation
shapes. V1 implementations are selected by the pair ``(world, VenueId)`` — never
by ``VenueId`` alone — and a replay composition refuses any venue-connecting
implementation (DEC-0196, DEC-0228).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from qmf.core import (
    Account,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    World,
)
from qmf.venue.commands import Command, SubmissionResult
from qmf.venue.events import Reconciliation

__all__ = [
    "VenueClientKind",
    "VenueClientPort",
    "VenueClientSelection",
    "select_venue_client",
]


class VenueClientKind(StrEnum):
    """The three V1 :class:`VenueClientPort` implementations (DEC-0196, DEC-0228)."""

    CTRADER = "ctrader"
    REPLAY = "replay"
    CONFORMANCE = "conformance"


@runtime_checkable
class VenueClientPort(Protocol):
    """Neutral venue client seam over CT-19 commands and CT-20 events.

    Implementations: the live cTrader client composed around
    ``qmf-venue``'s :class:`~qmf.venue.connection.ConnectionManager`, the TN-21
    replay adapter, and the FEAT-0023 conformance double (DEC-0196, DEC-0228).
    """

    @property
    def kind(self) -> VenueClientKind:
        """Which V1 implementation this instance is."""
        ...

    @property
    def venue_id(self) -> VenueId:
        """The venue this client is bound to."""
        ...

    @property
    def world(self) -> World:
        """The world this client was selected for."""
        ...

    def open_session(self, account: Account) -> Result[bool]:
        """Open the session lifecycle for ``account`` (CT-21)."""
        ...

    def close_session(self) -> Result[bool]:
        """Close the open session, if any."""
        ...

    def verify_capabilities(self) -> Result[Mapping[str, object]]:
        """CT-18 capability verification / observe-profile readiness gate."""
        ...

    def submit(self, command: Command | object) -> Result[SubmissionResult]:
        """Submit one CT-19 command; every well-formed path yields a four-outcome result.

        Implementations also accept :class:`~qmf.venue.commands.CompoundCommand` so the
        FTR-02 block can be asserted through the same port surface.
        """
        ...

    def observations(self) -> Result[Sequence[Mapping[str, object]]]:
        """Drain recorded CT-20 observations / read-backs (credential-free shapes)."""
        ...

    def reconcile(self) -> Result[Reconciliation]:
        """On-demand CT-20 reconciliation read-back."""
        ...


@dataclass(frozen=True, slots=True)
class VenueClientSelection:
    """Resolved ``(world, VenueId) → implementation kind`` selection (DEC-0196)."""

    world: World
    venue_id: VenueId
    kind: VenueClientKind


def select_venue_client(world: object, venue_id: object) -> Result[VenueClientSelection]:
    """Select a :class:`VenueClientPort` implementation by ``(world, VenueId)``.

    ``world = replay`` selects the replay implementation for every ``VenueId``.
    A venue-connecting kind is never bound into a replay composition. Unknown
    worlds or a malformed venue are typed refusals (DEC-0196, DEC-0228).
    """
    resolved_world = _coerce_world(world)
    if resolved_world is None:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": "VenueClientPort selection requires live | replay | simulated",
                "given": repr(world),
                "allowed": [m.value for m in World],
            },
        )
    if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "venue_id",
                "reason": "VenueClientPort selection requires a valid VenueId",
                "given": repr(venue_id),
            },
        )
    if resolved_world is World.REPLAY:
        kind = VenueClientKind.REPLAY
    elif resolved_world is World.SIMULATED:
        # Simulated stays reserved-unusable until fidelity content lands; refuse
        # binding a venue-connecting client rather than inventing a fourth kind.
        return TypedRefusal(
            category=RefusalCategory.UNSUPPORTED_CAPABILITY,
            retryability=Retryability.NO,
            context={
                "field": "world",
                "reason": "world=simulated is reserved-unusable; no VenueClientPort binds",
                "world": resolved_world.value,
            },
        )
    # world=live: conformance double is selected by an explicit VenueId convention
    # for credential-free gates; live cTrader otherwise. Callers that want the
    # double under live pass a VenueId whose value starts with "conformance:".
    elif venue_id.value.startswith("conformance:"):
        kind = VenueClientKind.CONFORMANCE
    else:
        kind = VenueClientKind.CTRADER
    return Ok(VenueClientSelection(world=resolved_world, venue_id=venue_id, kind=kind))


def _coerce_world(value: object) -> World | None:
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None
