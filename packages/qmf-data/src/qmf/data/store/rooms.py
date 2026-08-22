"""Room-roles and per-world routing for the store seam (AR-19, DEC-0117).

The store physically holds the **seven room-roles**, each instantiated **per
world**; world isolation is delivered by storage separation, not by identity
distinctness alone (DEC-0110, DEC-0117). This module pins the room-role vocabulary
(defined once, reused by CT-11/CT-26), records which roles are evidence-bearing
(only the immutable raw archive and the journal), and owns the two world-policy
gates every write and read passes through:

* a ``world = simulated`` write is a ``policy rejection`` (reserved-unusable in V1,
  DEC-0110) — resolved through ``qmf.core.governed_namespace``; and
* a read that crosses worlds is a ``policy rejection`` (DEC-0117).

``World`` and ``governed_namespace`` come from ``qmf-core``; this module adds only
the room vocabulary and the cross-world read gate. Stdlib + qmf-core only.
"""

from __future__ import annotations

from enum import StrEnum

from qmf.core import Ok, Result, TypedRefusal, World, governed_namespace, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "EVIDENCE_BEARING_ROLES",
    "ROOM_ROLE_VALUES",
    "RoomRole",
    "namespace_block",
    "namespace_for_write",
    "require_same_world",
]


class RoomRole(StrEnum):
    """The seven room-roles a store holds, each instantiated per world (DEC-0117).

    The values are the canonical spaced strings CT-11 pins; the vocabulary is
    defined once here and reused verbatim by CT-26. Only the immutable raw archive
    and the journal are evidence-bearing (see :data:`EVIDENCE_BEARING_ROLES`);
    processed data and analytics views are rebuildable, so an engine format break
    costs a rebuild and never evidence.
    """

    INGEST_DOOR = "ingest door"
    IMMUTABLE_RAW_ARCHIVE = "immutable raw archive"
    PROCESSED = "processed"
    JOURNAL = "journal"
    RESEARCH_DOOR = "split-governed research door"
    BACKUP = "backup"
    REGISTRY_ROOM = "registry room"


# The room-role vocabulary, in CT-11's declared order. Reused by CT-26.
ROOM_ROLE_VALUES: tuple[str, ...] = tuple(role.value for role in RoomRole)

# Only these two room-roles bear evidence; every other role holds rebuildable
# views whose deletion is licensed when no result label cites them (DEC-0117).
EVIDENCE_BEARING_ROLES: frozenset[RoomRole] = frozenset(
    {RoomRole.IMMUTABLE_RAW_ARCHIVE, RoomRole.JOURNAL}
)


def namespace_for_write(world: object) -> Result[str]:
    """The storage namespace a write of ``world`` may occupy, or a refusal.

    Delegates to ``qmf.core.governed_namespace``: ``live`` and ``replay`` route to
    their own namespaces, while ``world = simulated`` is a ``policy rejection`` —
    reserved-unusable in V1 until the backtesting sitting defines simulated-time
    typing (DEC-0110). Because the namespace is derived from the world, a non-live
    world can never resolve to the live namespace (storage separation).
    """
    return governed_namespace(world)


def namespace_block(world: World) -> TypedRefusal | None:
    """The write-world gate: a ``policy rejection`` if unwritable, else ``None``.

    ``world = simulated`` has no governed namespace in V1, so a write into it is a
    policy-rejection refusal (DEC-0110); ``live`` and ``replay`` are writable and
    return ``None``. A boundary calls this before persisting so a ``simulated`` write
    is refused before any bytes are touched (AC5).
    """
    namespace = namespace_for_write(world)
    if is_refusal(namespace):
        return namespace
    return None


def require_same_world(bound_world: World, requested_world: object) -> Result[World]:
    """Gate a read against the room's own world; a cross-world read refuses (AC5).

    A store boundary is bound to exactly one world's room instance. The caller must
    **declare** the world it is reading as — there is no implicit "my own world"
    default, so the guard always evaluates and an omitted declaration can never read
    freely (M4). A read that names a *different* world than the room's is a ``policy
    rejection`` — world isolation is storage separation, so one world's room never
    serves another's evidence (DEC-0117, DEC-0110). A missing declaration (``None``)
    is an ``invalid input`` refusal: a read must state its world.
    """
    if requested_world is None:
        return invalid_input(
            "for_world",
            "a read must declare the world it is reading as; there is no implicit "
            "same-world default, so a cross-world read is always evaluated (M4)",
        )
    if isinstance(requested_world, World):
        resolved = requested_world
    elif isinstance(requested_world, str):
        try:
            resolved = World(requested_world)
        except ValueError:
            return invalid_input(
                "world",
                "world is one of the closed set live | replay | simulated",
                given=requested_world,
            )
    else:
        return invalid_input(
            "world",
            "world is a World or one of the closed set live | replay | simulated",
            given=repr(requested_world),
        )
    if resolved is not bound_world:
        return policy_rejection(
            "world",
            "a read that crosses worlds is refused; storage separation delivers "
            "world isolation (DEC-0117)",
            requested=resolved.value,
            room_world=bound_world.value,
        )
    return Ok(resolved)
