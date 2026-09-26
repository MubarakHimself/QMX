"""Rebuild pins a rebuildable analytics view must honor (AC2).

Split from :mod:`qmf.data.rooms` so :class:`~qmf.data.rooms.WorldRooms` can
delegate without a circular import. Callers keep importing :class:`RebuildPins`
from :mod:`qmf.data.rooms`.
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core import CalendarIdentity, Ok, Result
from qmf.data.store.refusals import invalid_input

__all__ = ["RebuildPins"]


@dataclass(frozen=True, slots=True)
class RebuildPins:
    """The pins a rebuild of a rebuildable analytics view must honor (AC2).

    A processed/analytics view is never evidence: an engine format break costs a rebuild.
    A faithful rebuild must replay against the **exact** calendar the view was built
    under, so this value carries the original :class:`~qmf.core.CalendarIdentity` — which
    itself pins the ``tzdata_version`` — and the view's receipt records both the calendar
    identity and the tzdata version, so a rebuild can never silently re-derive the seal or
    a session boundary under a later tzdata release (DEC-0117, DEC-0103, DEC-0106).

    The analytics-engine major is *not* carried here: the engine records its own major on
    the receipt, so this value holds only what the caller must declare — the calendar the
    view was computed under.
    """

    calendar_identity: CalendarIdentity

    @classmethod
    def try_create(cls, calendar_identity: object) -> Result[RebuildPins]:
        """Validate and build :class:`RebuildPins`, returning value-or-refusal.

        ``calendar_identity`` must be a ``qmf-core`` :class:`CalendarIdentity` (which
        already pins its rule set, rule-set version, and tzdata version); anything else is
        an ``invalid input`` refusal (CT-04; DEC-0109).
        """
        if not isinstance(calendar_identity, CalendarIdentity):
            return invalid_input(
                "calendar_identity",
                "rebuild pins carry a qmf-core CalendarIdentity — the original calendar a "
                "rebuild must replay against (DEC-0106)",
                given=repr(calendar_identity),
            )
        return Ok(cls(calendar_identity=calendar_identity))

    def calendar_identity_label(self) -> str:
        """The calendar identity a rebuild pins, as an opaque ``rule_set:version`` label.

        The tzdata version is recorded separately (:attr:`tzdata_version`), matching the
        CT-11 ``rebuild_calendar_identity`` / ``rebuild_tzdata_version`` split.
        """
        return f"{self.calendar_identity.rule_set}:{self.calendar_identity.rule_set_version}"

    @property
    def tzdata_version(self) -> str:
        """The original tzdata version a rebuild pins (from the calendar identity)."""
        return self.calendar_identity.tzdata_version
