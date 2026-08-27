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

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Protocol, cast, runtime_checkable

from qmf.core import (
    Ok,
    Result,
    Retryability,
    TypedRefusal,
    World,
    governed_namespace,
    is_refusal,
)
from qmf.data.store.refusals import invalid_input, policy_rejection, storage_failure

__all__ = [
    "EVIDENCE_BEARING_ROLES",
    "ROOM_ROLE_VALUES",
    "ReadSeal",
    "RoomRole",
    "derive_content_position",
    "guard_derived_content",
    "guard_sealed_read",
    "guard_stored_row_world",
    "namespace_block",
    "namespace_for_write",
    "require_same_world",
    "require_write_world",
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


def require_write_world(bound_world: World, declared_world: object) -> TypedRefusal | None:
    """Gate a write whose payload declares its own world against the room's world (AC5).

    A journal event carries its own ``world`` (``JournalEvent.to_row`` stamps it), but the
    physical journal room is bound to exactly one world. A payload that declares a
    *different* world than the room's — or a ``world = simulated`` payload — is a ``policy
    rejection``: storage separation delivers world isolation, so one world's journal room
    never stores another world's evidence, and ``world = simulated`` has no governed
    namespace in V1 (DEC-0110, DEC-0117). This is the write-side counterpart to
    ``source_boundary`` routing on the observation's own world.

    A payload that declares **no** world (``None``) inherits the room's world: the
    data-policy writer (``JournalWriter``) always stamps the event with the store's world,
    and a bare physical row carries none, so it is not refused here. A malformed world
    value (not a ``World`` or a closed-set string) is an ``invalid input`` refusal.
    """
    if declared_world is None:
        return None
    if isinstance(declared_world, World):
        resolved = declared_world
    elif isinstance(declared_world, str):
        try:
            resolved = World(declared_world)
        except ValueError:
            return invalid_input(
                "world",
                "world is one of the closed set live | replay | simulated",
                given=declared_world,
            )
    else:
        return invalid_input(
            "world",
            "world is a World or one of the closed set live | replay | simulated",
            given=repr(declared_world),
        )
    if resolved is not bound_world:
        return policy_rejection(
            "world",
            "a journal event whose declared world differs from the room's is refused; "
            "storage separation delivers world isolation, so one world's journal room "
            "never stores another world's evidence, and world = simulated has no governed "
            "namespace in V1 (DEC-0110, DEC-0117)",
            declared=resolved.value,
            room_world=bound_world.value,
        )
    return None


def guard_stored_row_world(
    bound_world: World, declared_world: object, *, index: int
) -> TypedRefusal | None:
    """Refuse a *stored* row whose declared world differs from the room's (integrity).

    The read-side, defense-in-depth counterpart to :func:`require_write_world`. The
    write-side guard already blocks a cross-world event from ever landing, so a stored row
    that declares a world **different** from the room's can only have arrived through direct
    file tampering — corrupt stored evidence, not a caller mistake. It is surfaced as a
    ``storage failure`` (retryability ``no``, exactly how a torn middle line or a sequence
    gap is surfaced), never served as valid, so world isolation holds on the stored bytes
    themselves and not merely on the read's declared world (DEC-0110, DEC-0117).

    A row that declares **no** world (``None``) inherits the room's world — a bare physical
    row carries none — exactly as the write-side guard treats it, so this never refuses a
    legitimately world-less row. ``index`` is the offending row's position in the stream,
    carried on the refusal for the operator. Returns ``None`` when the row belongs here.
    """
    if declared_world is None or declared_world == bound_world.value:
        return None
    return storage_failure(
        "a stored journal row declares a world different from the room's; the write-side "
        "guard blocks a cross-world event from ever landing, so this row can only have "
        "arrived through direct file tampering — corrupt evidence that is refused rather "
        "than served, so world isolation holds on the stored bytes themselves, never just "
        "on the read's declared world (DEC-0110, DEC-0117)",
        retryability=Retryability.NO,
        context={
            "field": "world",
            "signal": "world-isolation",
            "declared": declared_world,
            "room_world": bound_world.value,
            "row_index": index,
        },
    )


@runtime_checkable
class ReadSeal(Protocol):
    """The CT-12 no-peek seal, consulted at a store read boundary (AC4; DEC-0119).

    Injected structurally so the dependency-free store seam never imports the qmf-data
    splits/seal vocabulary (M3). A boundary hands it the read's knowledge ``position`` and
    the boundary's own name; the seal refuses (a ``policy rejection``) a read that reaches
    into the sealed no-peek window and passes it otherwise, so a sealed read is never a
    silent empty result. ``qmf.data.seal.HoldoutSeal`` satisfies this structurally.
    """

    def guard_read(
        self, position: object, *, boundary: object
    ) -> Result[None]:  # pragma: no cover - protocol seam
        """Refuse a read into the sealed window at ``boundary``, or pass (value-or-refusal)."""
        ...


def derive_content_position(rows: Sequence[object]) -> int | None:
    """The latest int64 event-time derivable from stored artifact content (AC4; DEC-0119).

    The read-side twin of the derivation ``resolve_series`` pins ("never a caller
    argument, so the seal cannot be bypassed"): scans each stored row's top-level
    ``t`` event-time, and — for a series envelope — the declared partition window
    end (``partition.window_end_ns``) plus every nested ``series`` row's own ``t``,
    so the derived position is never earlier than the data it guards. Returns
    ``None`` when the content carries no derivable event-time at all — CT-12
    defines no derivation rule for such an artifact, so the caller-declared
    position guard remains the only gate there (recorded specification gap).
    """
    latest: int | None = None

    def _consider(value: object) -> None:
        nonlocal latest
        if not isinstance(value, int) or isinstance(value, bool):
            return
        if latest is None or value > latest:
            latest = value

    for row in rows:
        if not isinstance(row, Mapping):
            continue
        mapping = cast("Mapping[str, object]", row)
        _consider(mapping.get("t"))
        partition = mapping.get("partition")
        if isinstance(partition, Mapping):
            _consider(cast("Mapping[str, object]", partition).get("window_end_ns"))
        series = mapping.get("series")
        if isinstance(series, Sequence) and not isinstance(series, (str, bytes)):
            for nested in cast("Sequence[object]", series):
                if isinstance(nested, Mapping):
                    _consider(cast("Mapping[str, object]", nested).get("t"))
    return latest


def guard_derived_content(
    seal: ReadSeal | None, rows: Sequence[object], *, boundary: str
) -> TypedRefusal | None:
    """Guard a wired seal at the position derived from the content itself (AC4; DEC-0119).

    Consulted after the stored rows are resolved and before they are returned, in
    addition to the caller-declared ``at`` guard — so a caller that under-states its
    position can never read sealed-period content back out (the bypass the
    caller-position guard alone leaves open). Content with no derivable event-time
    contributes nothing here; ``seal is None`` is a pass.
    """
    if seal is None:
        return None
    position = derive_content_position(rows)
    if position is None:
        return None
    return guard_sealed_read(seal, position, boundary=boundary)


def guard_sealed_read(
    seal: ReadSeal | None, position: object, *, boundary: str
) -> TypedRefusal | None:
    """Consult a wired no-peek seal at a read boundary, fail-closed (AC4; DEC-0119).

    A wired ``seal`` is consulted on **every** read, never an optional per-call argument a
    caller can skip: when a ``position`` is declared, a read reaching into the sealed no-peek
    window is a ``policy rejection`` returned to the caller — never a silent empty result. A
    read that declares **no** position (``None``) while a seal is wired is *also* a ``policy
    rejection`` — a positionless read cannot be proven outside the sealed window, so it is
    refused (fail-closed) rather than served fail-open. A caller-facing boundary therefore
    requires its ``at`` position when a seal is wired; a boundary that derives its own position
    from the evidence (the split-governed research door) hands the derived position here so it
    is never ``None``. No wired seal at all (``seal is None``) is the only pass. ``boundary``
    is the named ``ReadBoundary`` value the seal coerces (kept a plain string so the store seam
    stays vocabulary-free) and rides the refusal so the caller sees which boundary refused.
    """
    if seal is None:
        return None
    if position is None:
        return policy_rejection(
            "seal",
            "a read through a wired no-peek seal must declare its knowledge position; a read "
            "that declares none cannot be proven outside the sealed no-peek window, so it is "
            f"refused at the {boundary} boundary rather than served fail-open — the seal is "
            "consulted on every read, never a per-call argument a caller can skip "
            "(AC4; DEC-0119)",
            boundary=boundary,
        )
    guarded = seal.guard_read(position, boundary=boundary)
    if is_refusal(guarded):
        return guarded
    return None
