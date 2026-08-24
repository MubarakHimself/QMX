"""Immutable fingerprinted as-of set of registry records and fragments (B-15).

An as-of set is identified by its ``registry_as_of`` instant plus a set
``fp1`` fingerprint. It is not a registry of its own — qmf-registry owns
records and lineage; this is the delivery value the one library-owned
read port serves. Package SemVer never enters the set fingerprint
(DEC-0167).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import RegistrationRecord

from qmb._refuse import clean_token, invalid

__all__ = [
    "AS_OF_FORMAT_VERSION",
    "FRAGMENT_CLASS",
    "POINTER_CLASS",
    "STATE_KIND",
    "AsOfSet",
    "DatedPointer",
    "RegistryFragment",
    "SupersedesRef",
]

# The as-of-set envelope format version (AD-5). Incompatible meaning mints the
# next integer; history stays readable. Not package SemVer.
AS_OF_FORMAT_VERSION: Final[int] = 1
STATE_KIND: Final[str] = "as-of set"
FRAGMENT_CLASS: Final[str] = "registry-fragment"
POINTER_CLASS: Final[str] = "dated-pointer"


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a Fingerprint or a valid ``fp1:sha256:<hex>`` string, or ``None``."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _coerce_instant(value: object) -> Instant | None:
    """Resolve an Instant, or ``None``."""
    if isinstance(value, Instant):
        return value
    return None


def _is_name_at_cite(token: str) -> bool:
    """Whether ``token`` is the banned ``name@version`` / ``name@latest`` cite form."""
    return "@" in token


# --- dated pointer (legal UX; not identity) ---------------------------------


@dataclass(frozen=True, slots=True)
class DatedPointer:
    """A dated alias pointer naming one ``fp1`` (B-13, B-15).

    ``current`` is legal UX; ``name@version`` is not a legal identity cite.
    The pointer is occurrence/display for doors; callers cite the target
    fingerprint.
    """

    alias: str
    target: Fingerprint
    dated_at: Instant

    @classmethod
    def try_create(
        cls,
        alias: object,
        target: object,
        dated_at: object,
    ) -> Result[DatedPointer]:
        """Validate and build a dated pointer, returning value-or-refusal."""
        token = clean_token(alias)
        if token is None:
            return invalid(
                "alias",
                "a dated pointer names a non-empty human alias",
                given=repr(alias),
            )
        if _is_name_at_cite(token):
            return invalid(
                "alias",
                "name@version is not a legal identity cite; a dated pointer "
                "record ('current') is legal UX and the caller cites fp1 (B-13)",
                given=token,
            )
        resolved = _coerce_fingerprint(target)
        if resolved is None:
            return invalid(
                "target",
                "a dated pointer names a record or fragment by fp1",
                given=repr(target),
            )
        instant = _coerce_instant(dated_at)
        if instant is None:
            return invalid(
                "dated_at",
                "a dated pointer is dated with an Instant",
                given=repr(dated_at),
            )
        return Ok(cls(alias=token, target=resolved, dated_at=instant))

    def fp1_identity(self) -> dict[str, object]:
        """Identity content of this pointer inside an as-of set."""
        return {
            "class": POINTER_CLASS,
            "alias": self.alias,
            "target": self.target.value,
            "dated_at": self.dated_at.fp1_identity(),
        }


# --- derived fragment (not a newly minted registry kind) --------------------


@dataclass(frozen=True, slots=True)
class RegistryFragment:
    """A derived, fingerprinted fragment delivered inside an as-of set (B-3, B-15).

    Not a newly minted registry kind. Identity is content-derived by qmf-core
    ``fp1`` over source fingerprint plus body. Story 13.3 materializes Book/BMS
    fragments into this shape.
    """

    source_fp1: Fingerprint
    body: Mapping[str, object]
    fingerprint: Fingerprint

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", _freeze_mapping(self.body))

    @classmethod
    def try_create(cls, source_fp1: object, body: object) -> Result[RegistryFragment]:
        """Derive the fragment fingerprint from source plus body."""
        source = _coerce_fingerprint(source_fp1)
        if source is None:
            return invalid(
                "source_fp1",
                "a fragment carries lineage back to a source record by fp1",
                given=repr(source_fp1),
            )
        if not isinstance(body, Mapping):
            return invalid(
                "body",
                "a fragment body is a key->value mapping",
                given=repr(type(body).__name__),
            )
        body_map = cast("Mapping[str, object]", body)
        derived = fingerprint(
            {
                "class": FRAGMENT_CLASS,
                "format_version": AS_OF_FORMAT_VERSION,
                "source_fp1": source.value,
                "body": dict(body_map),
            }
        )
        if is_refusal(derived):
            return invalid(
                "body",
                "the fragment body is not fp1-clean identity content",
                cause=dict(derived.context),
            )
        return Ok(cls(source_fp1=source, body=body_map, fingerprint=derived.value))

    def fp1_identity(self) -> dict[str, object]:
        """The parts that ARE this fragment's identity."""
        return {
            "class": FRAGMENT_CLASS,
            "format_version": AS_OF_FORMAT_VERSION,
            "source_fp1": self.source_fp1.value,
            "body": dict(self.body),
        }


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    """Deep-freeze a mapping so a later caller mutation cannot reach the fragment."""
    frozen: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Mapping):
            nested = cast("Mapping[str, object]", item)
            frozen[key] = _freeze_mapping(nested)
        elif isinstance(item, (list, tuple)):
            sequence = cast("Sequence[object]", item)
            frozen[key] = tuple(sequence)
        else:
            frozen[key] = item
    return MappingProxyType(frozen)


# --- supersedes pair (linear; current is the walk's head) -------------------


@dataclass(frozen=True, slots=True)
class SupersedesRef:
    """A ``supersedes`` pair inside an as-of set: ``newer`` replaces ``older`` (CT-07).

    Matches lineage ``from_ref`` (newer) / ``to_ref`` (older). Pinned linear:
    one newer per older.
    """

    newer: Fingerprint
    older: Fingerprint

    @classmethod
    def try_create(cls, newer: object, older: object) -> Result[SupersedesRef]:
        """Validate both endpoints as fp1 fingerprints, returning value-or-refusal."""
        left = _coerce_fingerprint(newer)
        if left is None:
            return invalid(
                "newer",
                "a supersedes pair names the newer record by fp1",
                given=repr(newer),
            )
        right = _coerce_fingerprint(older)
        if right is None:
            return invalid(
                "older",
                "a supersedes pair names the older record by fp1",
                given=repr(older),
            )
        if left.value == right.value:
            return invalid(
                "supersedes",
                "a supersedes pair cannot point a record at itself",
                given=left.value,
            )
        return Ok(cls(newer=left, older=right))


# --- the as-of set ----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AsOfSet:
    """An immutable fingerprinted as-of set (``registry_as_of`` + set fingerprint).

    Records, derived fragments, dated pointers, and linear supersedes pairs
    together ARE the set. The set fingerprint is qmf-core ``fp1`` over that
    identity; package SemVer is omitted (DEC-0165, DEC-0167).
    """

    registry_as_of: Instant
    fingerprint: Fingerprint
    records: tuple[RegistrationRecord, ...]
    fragments: tuple[RegistryFragment, ...]
    pointers: tuple[DatedPointer, ...]
    supersedes: tuple[SupersedesRef, ...]
    _by_fp: Mapping[str, RegistrationRecord | RegistryFragment] = field(
        init=False, compare=False, repr=False
    )
    _by_alias: Mapping[str, DatedPointer] = field(init=False, compare=False, repr=False)
    _newer_of: Mapping[str, str] = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        by_fp: dict[str, RegistrationRecord | RegistryFragment] = {}
        for record in self.records:
            by_fp[record.stable_id.value] = record
        for fragment in self.fragments:
            by_fp[fragment.fingerprint.value] = fragment
        object.__setattr__(self, "_by_fp", MappingProxyType(by_fp))
        object.__setattr__(
            self,
            "_by_alias",
            MappingProxyType({pointer.alias: pointer for pointer in self.pointers}),
        )
        object.__setattr__(
            self,
            "_newer_of",
            MappingProxyType({pair.older.value: pair.newer.value for pair in self.supersedes}),
        )

    @classmethod
    def try_create(
        cls,
        registry_as_of: object,
        records: object = (),
        fragments: object = (),
        pointers: object = (),
        supersedes: object = (),
    ) -> Result[AsOfSet]:
        """Validate members, derive the set fingerprint, and build the as-of set."""
        instant = _coerce_instant(registry_as_of)
        if instant is None:
            return invalid(
                "registry_as_of",
                "an as-of set is dated by an Instant (the registry_as_of instant)",
                given=repr(registry_as_of),
            )
        record_tuple = _as_record_tuple(records)
        if isinstance(record_tuple, TypedRefusal):
            return record_tuple
        fragment_tuple = _as_fragment_tuple(fragments)
        if isinstance(fragment_tuple, TypedRefusal):
            return fragment_tuple
        pointer_tuple = _as_pointer_tuple(pointers)
        if isinstance(pointer_tuple, TypedRefusal):
            return pointer_tuple
        supersedes_tuple = _as_supersedes_tuple(supersedes)
        if isinstance(supersedes_tuple, TypedRefusal):
            return supersedes_tuple
        known = _member_ids(record_tuple, fragment_tuple)
        if isinstance(known, TypedRefusal):
            return known
        members_ok = _check_member_refs(pointer_tuple, supersedes_tuple, known, instant)
        if isinstance(members_ok, TypedRefusal):
            return members_ok
        identity = _set_identity(
            instant, record_tuple, fragment_tuple, pointer_tuple, supersedes_tuple
        )
        derived = fingerprint(identity)
        if is_refusal(derived):
            return invalid(
                "as_of_set",
                "the as-of set identity is not fp1-clean",
                cause=dict(derived.context),
            )
        return Ok(
            cls(
                registry_as_of=instant,
                fingerprint=derived.value,
                records=record_tuple,
                fragments=fragment_tuple,
                pointers=pointer_tuple,
                supersedes=supersedes_tuple,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The parts that ARE this as-of set's identity. Package SemVer is omitted."""
        return _set_identity(
            self.registry_as_of,
            self.records,
            self.fragments,
            self.pointers,
            self.supersedes,
        )

    def get(self, ref: object) -> RegistrationRecord | RegistryFragment | None:
        """The record or fragment named by ``fp1``, or ``None`` if absent."""
        resolved = _coerce_fingerprint(ref)
        if resolved is None:
            return None
        return self._by_fp.get(resolved.value)

    def pointer_for(self, alias: object) -> DatedPointer | None:
        """The dated pointer for a human alias, or ``None``."""
        token = clean_token(alias)
        if token is None:
            return None
        return self._by_alias.get(token)

    def current_head(self, ref: object) -> Result[Fingerprint]:
        """Walk linear supersedes from ``ref`` to the one current head (CT-07)."""
        resolved = _coerce_fingerprint(ref)
        if resolved is None:
            return invalid(
                "ref",
                "a head is resolved for a record named by an fp1 fingerprint",
                given=repr(ref),
            )
        seen: set[str] = set()
        cursor = resolved.value
        while cursor in self._newer_of and cursor not in seen:
            seen.add(cursor)
            cursor = self._newer_of[cursor]
        if cursor == resolved.value:
            return Ok(resolved)
        head = _coerce_fingerprint(cursor)
        if head is None:  # pragma: no cover - chain endpoints are admitted fingerprints
            return invalid("ref", "the resolved head is not a valid fingerprint", given=cursor)
        return Ok(head)

    def is_superseded(self, ref: object) -> bool:
        """True when ``ref`` is in this set and is not the current supersedes head."""
        resolved = _coerce_fingerprint(ref)
        if resolved is None or resolved.value not in self._by_fp:
            return False
        head = self.current_head(resolved)
        if is_refusal(head):
            return False
        return head.value.value != resolved.value


def _set_identity(
    instant: Instant,
    records: tuple[RegistrationRecord, ...],
    fragments: tuple[RegistryFragment, ...],
    pointers: tuple[DatedPointer, ...],
    supersedes: tuple[SupersedesRef, ...],
) -> dict[str, object]:
    """Canonical as-of-set identity; keys sorted by the fp1 serializer."""
    return {
        "class": STATE_KIND,
        "format_version": AS_OF_FORMAT_VERSION,
        "fragments": sorted(fragment.fingerprint.value for fragment in fragments),
        "pointers": [
            pointer.fp1_identity() for pointer in sorted(pointers, key=lambda item: item.alias)
        ],
        "records": sorted(record.stable_id.value for record in records),
        "registry_as_of": instant.fp1_identity(),
        "supersedes": [
            {"newer": pair.newer.value, "older": pair.older.value}
            for pair in sorted(supersedes, key=lambda item: (item.newer.value, item.older.value))
        ],
    }


def _as_sequence(value: object, field: str) -> tuple[object, ...] | TypedRefusal:
    """Admit a sequence (not a bare string) as a tuple of items."""
    if isinstance(value, (str, bytes)):
        return invalid(
            field,
            "a collection of as-of-set members is a sequence, not a bare string",
            given=repr(value),
        )
    if value is None:
        return ()
    if not isinstance(value, Sequence):
        return invalid(
            field,
            "a collection of as-of-set members is a sequence",
            given=repr(type(value).__name__),
        )
    return tuple(cast("Sequence[object]", value))


def _as_record_tuple(value: object) -> tuple[RegistrationRecord, ...] | TypedRefusal:
    """Admit CT-06 records; a duplicate fp1 with differing content is refused."""
    items = _as_sequence(value, "records")
    if isinstance(items, TypedRefusal):
        return items
    admitted: list[RegistrationRecord] = []
    seen: dict[str, RegistrationRecord] = {}
    for item in items:
        if not isinstance(item, RegistrationRecord):
            return invalid(
                "records",
                "an as-of set record is a CT-06 RegistrationRecord",
                given=repr(type(item).__name__),
            )
        key = item.stable_id.value
        existing = seen.get(key)
        if existing is not None:
            if existing == item:
                continue
            return invalid(
                "records",
                "a true fp1 collision on differing record bytes is refused, never overwritten",
                fingerprint=key,
            )
        seen[key] = item
        admitted.append(item)
    return tuple(admitted)


def _as_fragment_tuple(value: object) -> tuple[RegistryFragment, ...] | TypedRefusal:
    """Admit derived fragments; duplicate fp1 with differing content is refused."""
    items = _as_sequence(value, "fragments")
    if isinstance(items, TypedRefusal):
        return items
    admitted: list[RegistryFragment] = []
    seen: dict[str, RegistryFragment] = {}
    for item in items:
        if not isinstance(item, RegistryFragment):
            return invalid(
                "fragments",
                "an as-of set fragment is a RegistryFragment",
                given=repr(type(item).__name__),
            )
        key = item.fingerprint.value
        existing = seen.get(key)
        if existing is not None:
            if existing == item:
                continue
            return invalid(
                "fragments",
                "a true fp1 collision on differing fragment bytes is refused, never overwritten",
                fingerprint=key,
            )
        seen[key] = item
        admitted.append(item)
    return tuple(admitted)


def _as_pointer_tuple(value: object) -> tuple[DatedPointer, ...] | TypedRefusal:
    """Admit dated pointers; a duplicate alias is refused."""
    items = _as_sequence(value, "pointers")
    if isinstance(items, TypedRefusal):
        return items
    admitted: list[DatedPointer] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, DatedPointer):
            return invalid(
                "pointers",
                "an as-of set pointer is a DatedPointer",
                given=repr(type(item).__name__),
            )
        if item.alias in seen:
            return invalid(
                "pointers",
                "a human alias names at most one dated pointer in an as-of set",
                alias=item.alias,
            )
        seen.add(item.alias)
        admitted.append(item)
    return tuple(admitted)


def _as_supersedes_tuple(value: object) -> tuple[SupersedesRef, ...] | TypedRefusal:
    """Admit linear supersedes pairs (one newer per older, no cycles)."""
    items = _as_sequence(value, "supersedes")
    if isinstance(items, TypedRefusal):
        return items
    admitted: list[SupersedesRef] = []
    newer_of: dict[str, str] = {}
    older_of: dict[str, str] = {}
    for item in items:
        if not isinstance(item, SupersedesRef):
            return invalid(
                "supersedes",
                "an as-of set supersedes member is a SupersedesRef",
                given=repr(type(item).__name__),
            )
        if item.older.value in newer_of:
            return invalid(
                "supersedes",
                "supersedes is pinned linear: an older record already has a newer",
                older=item.older.value,
            )
        if item.newer.value in older_of:
            return invalid(
                "supersedes",
                "supersedes is pinned linear: a newer record already supersedes one older",
                newer=item.newer.value,
            )
        if _would_cycle(newer_of, item.newer.value, item.older.value):
            return invalid(
                "supersedes",
                "a supersedes pair would close a cycle, leaving no current head",
                newer=item.newer.value,
                older=item.older.value,
            )
        newer_of[item.older.value] = item.newer.value
        older_of[item.newer.value] = item.older.value
        admitted.append(item)
    return tuple(admitted)


def _would_cycle(newer_of: Mapping[str, str], newer: str, older: str) -> bool:
    """True when adding ``newer`` supersedes ``older`` would close a cycle."""
    cursor: str | None = newer
    seen: set[str] = set()
    while cursor is not None and cursor not in seen:
        if cursor == older:
            return True
        seen.add(cursor)
        cursor = newer_of.get(cursor)
    return False


def _member_ids(
    records: tuple[RegistrationRecord, ...],
    fragments: tuple[RegistryFragment, ...],
) -> frozenset[str] | TypedRefusal:
    """Every fp1 present in the set; a record/fragment collision is refused."""
    record_ids = {record.stable_id.value for record in records}
    fragment_ids = {fragment.fingerprint.value for fragment in fragments}
    overlap = record_ids & fragment_ids
    if overlap:
        return invalid(
            "fragments",
            "a fragment fp1 collides with a record fp1; refused, never overwritten",
            overlap=sorted(overlap),
        )
    return frozenset(record_ids | fragment_ids)


def _check_member_refs(
    pointers: tuple[DatedPointer, ...],
    supersedes: tuple[SupersedesRef, ...],
    known: frozenset[str],
    instant: Instant,
) -> TypedRefusal | None:
    """Pointers and supersedes endpoints must name members of this as-of set."""
    for pointer in pointers:
        if pointer.target.value not in known:
            return invalid(
                "pointers",
                "a dated pointer must name a record or fragment in this as-of set",
                alias=pointer.alias,
                target=pointer.target.value,
            )
        if pointer.dated_at.value_ns > instant.value_ns:
            return invalid(
                "pointers",
                "a dated pointer may not post-date the as-of instant",
                alias=pointer.alias,
                dated_at=pointer.dated_at.value_ns,
                registry_as_of=instant.value_ns,
            )
    for pair in supersedes:
        if pair.newer.value not in known or pair.older.value not in known:
            return invalid(
                "supersedes",
                "both supersedes endpoints must name members of this as-of set",
                newer=pair.newer.value,
                older=pair.older.value,
            )
    return None
