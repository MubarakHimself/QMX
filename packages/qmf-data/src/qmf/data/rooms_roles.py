"""Room-role catalog for one world's seven rooms (AC1, AC2, AC5).

Disconnected from :class:`~qmf.data.rooms.WorldRooms` store-boundary and
series-policy groups (LCOM4). The catalog tuple is shared instance state so
``roles``, ``evidence_bearing_roles``, and ``is_evidence_bearing`` stay one
component.
"""

from __future__ import annotations

from qmf.data.store import EVIDENCE_BEARING_ROLES, RoomRole


class WorldRoomRoles:
    """The seven room-roles plus the evidence-bearing subset, for one world."""

    def __init__(self) -> None:
        self._catalog: tuple[tuple[RoomRole, ...], frozenset[RoomRole]] = (
            tuple(RoomRole),
            EVIDENCE_BEARING_ROLES,
        )

    @property
    def roles(self) -> tuple[RoomRole, ...]:
        """The seven room-roles this world instantiates, in CT-11's declared order (AC1)."""
        return self._catalog[0]

    @property
    def evidence_bearing_roles(self) -> frozenset[RoomRole]:
        """The two evidence-bearing roles — immutable raw archive and journal (AC2, AC5)."""
        return self._catalog[1]

    def is_evidence_bearing(self, role: RoomRole) -> bool:
        """Whether ``role`` is evidence-bearing — true only for raw archive and journal.

        Processed data and analytics views are rebuildable, so they are never
        evidence-bearing; an engine format break over them costs a rebuild, not evidence
        (AC2, AC5; DEC-0117).
        """
        return role in self._catalog[1]
