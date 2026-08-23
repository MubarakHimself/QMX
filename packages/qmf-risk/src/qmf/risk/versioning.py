"""Story 10.1 — git-logic-without-git template versioning (COMP-QMF-RISK).

Book and BMS templates version by **git logic without git** (AD-30; DEC-0144,
DEC-0158):

* an **append-only version graph** built on ``branches-from`` edges — a new
  version branches from a parent, **multiple heads are legal**, and a version is
  never mutated (a UI edit mints a new version);
* ``supersedes`` stays **linear** everywhere else in the spine, so it is a distinct
  edge kind here and never carries the branching version graph;
* ``current`` is a **separate dated pointer record**, not a graph property — the
  latest dated pointer names the current version, and re-pointing appends a new
  dated pointer, never mutating an old one;
* **every old version stays readable forever** — the graph only ever grows;
* a **diff is derivable between any two versions** (:func:`diff_variable_maps`);
* and because a changed number changes ``fp1``, a new version is a new fingerprint
  node — the identity change is what the graph records.

This module is the pure graph and diff machinery over ``qmf-core``
:class:`~qmf.core.Fingerprint` identities and injected :class:`~qmf.core.Instant`
pointer dates — it reads no clock (a dated pointer's instant is supplied by the
caller at the composition root; AR-16). It holds no physical store: a
:class:`TemplateVersionGraph` is an in-memory reference structure, the same way
``qmf-core``'s ``GovernedEvidenceLedger`` is a pure reference guard — the governed
version records live in ``qmf-registry`` and reach it only through the composition
root (DEC-0158). Imports only ``qmf-core``; nothing imports ``qmf.risk``
(default-deny, L30/DEC-0120). Ratified ``defined-unwired`` surface.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import cast

from qmf.core import Fingerprint, Instant, Ok, Result, TypedRefusal
from qmf.risk._common import invalid, unavailable
from qmf.risk.grammar import TemplateVariable

__all__ = [
    "CurrentPointer",
    "TemplateVersionGraph",
    "VariableDiff",
    "VersionEdgeKind",
    "diff_variable_maps",
]


class VersionEdgeKind(StrEnum):
    """The two lineage edge kinds the version machinery names apart (DEC-0144).

    ``BRANCHES_FROM`` builds the append-only version graph (multiple heads legal).
    ``SUPERSEDES`` stays linear and is used everywhere else in the spine — never for
    the version graph — so ``current`` resolves linearly elsewhere while versions
    branch here.
    """

    BRANCHES_FROM = "branches-from"
    SUPERSEDES = "supersedes"


@dataclass(frozen=True, slots=True)
class CurrentPointer:
    """A dated pointer naming the current template version (DEC-0144, DEC-0158).

    ``current`` is a separate dated record, not a graph property: it carries the
    pointed :class:`~qmf.core.Fingerprint` and the :class:`~qmf.core.Instant` it was
    dated at (injected, never clock-read). Re-pointing appends a new pointer with a
    later instant; an old pointer is never mutated.
    """

    fingerprint: Fingerprint
    dated_at: Instant

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this pointer."""
        return {
            "class": "current-pointer",
            "fingerprint": self.fingerprint.value,
            "dated_at": self.dated_at.fp1_identity(),
        }


class TemplateVersionGraph:
    """An append-only, multiple-head template version graph (DEC-0144, DEC-0158).

    A pure in-memory reference structure — **not** the platform's store — holding
    the version nodes (by ``fp1``), their ``branches-from`` edges, and the dated
    ``current`` pointer history. Every write only ever appends: a version node is
    immutable and re-adding one is refused, so every old version stays readable
    forever.
    """

    def __init__(self) -> None:
        self._nodes: list[Fingerprint] = []
        self._node_set: set[str] = set()
        # child fp1 -> parent fp1 it branches from (a child branches from at most
        # one parent; multiple children of one parent give multiple branches).
        self._branches_from: dict[str, str] = {}
        self._pointers: list[CurrentPointer] = []

    def append_version(self, fingerprint: object, branches_from: object = None) -> Result[None]:
        """Append a new version node, optionally branching from a parent.

        The fingerprint must be a :class:`~qmf.core.Fingerprint` not already in the
        graph (a version is immutable; re-adding one is ``invalid input`` — never a
        silent idempotent accept). A ``branches_from`` parent, when given, must
        already be a node (else ``unavailable dependency`` — a branch never dangles),
        and a node may not branch from itself.
        """
        if not isinstance(fingerprint, Fingerprint):
            return invalid(
                "fingerprint",
                "a version node is identified by a Fingerprint",
                given=repr(fingerprint),
            )
        if fingerprint.value in self._node_set:
            return invalid(
                "fingerprint",
                "a version is immutable and already present; a UI edit mints a NEW version "
                "(a changed number changes fp1), never a re-add of an existing one",
                given=fingerprint.value,
            )
        parent: Fingerprint | None = None
        if branches_from is not None:
            if not isinstance(branches_from, Fingerprint):
                return invalid(
                    "branches_from",
                    "a branches-from parent is a Fingerprint",
                    given=repr(branches_from),
                )
            if branches_from.value == fingerprint.value:
                return invalid(
                    "branches_from", "a version may not branch from itself", given=fingerprint.value
                )
            if branches_from.value not in self._node_set:
                return unavailable(
                    "branches_from",
                    "a branches-from parent must already be a version node; a branch never dangles",
                    given=branches_from.value,
                )
            parent = branches_from
        self._nodes.append(fingerprint)
        self._node_set.add(fingerprint.value)
        if parent is not None:
            self._branches_from[fingerprint.value] = parent.value
        return Ok(None)

    def set_current(self, fingerprint: object, dated_at: object) -> Result[CurrentPointer]:
        """Append a dated ``current`` pointer naming a known version.

        The fingerprint must be a known node; the date is an injected
        :class:`~qmf.core.Instant` and must not predate the latest existing pointer
        (the pointer history is dated-forward, append-only — an old pointer is never
        mutated). Returns the appended pointer.
        """
        if not isinstance(fingerprint, Fingerprint):
            return invalid(
                "fingerprint", "the current pointer names a Fingerprint", given=repr(fingerprint)
            )
        if fingerprint.value not in self._node_set:
            return unavailable(
                "fingerprint",
                "the current pointer must name a known version node",
                given=fingerprint.value,
            )
        if not isinstance(dated_at, Instant):
            return invalid(
                "dated_at",
                "the current pointer is dated with an injected Instant (never a clock read)",
                given=repr(dated_at),
            )
        if self._pointers and dated_at.value_ns < self._pointers[-1].dated_at.value_ns:
            return invalid(
                "dated_at",
                "a current pointer is dated forward; it may not predate the latest pointer",
                given=dated_at.value_ns,
                latest=self._pointers[-1].dated_at.value_ns,
            )
        pointer = CurrentPointer(fingerprint=fingerprint, dated_at=dated_at)
        self._pointers.append(pointer)
        return Ok(pointer)

    def current(self) -> Fingerprint | None:
        """The current version, per the latest dated pointer, or ``None`` if unset."""
        if not self._pointers:
            return None
        return self._pointers[-1].fingerprint

    def pointer_history(self) -> tuple[CurrentPointer, ...]:
        """The full dated pointer history, oldest first (append-only)."""
        return tuple(self._pointers)

    def versions(self) -> tuple[Fingerprint, ...]:
        """Every version node, in append order — all readable forever."""
        return tuple(self._nodes)

    def is_readable(self, fingerprint: object) -> bool:
        """True when this fingerprint is a known version node.

        The graph only ever grows, so a version once appended is readable forever.
        """
        return isinstance(fingerprint, Fingerprint) and fingerprint.value in self._node_set

    def parent_of(self, fingerprint: object) -> Fingerprint | None:
        """The parent a version branches from, or ``None`` if it is a root."""
        if not isinstance(fingerprint, Fingerprint):
            return None
        parent_value = self._branches_from.get(fingerprint.value)
        if parent_value is None:
            return None
        return Fingerprint(value=parent_value)

    def heads(self) -> tuple[Fingerprint, ...]:
        """The head versions — nodes nothing branches from (multiple heads legal).

        A head is a tip of the branching graph: a version that is no other version's
        ``branches-from`` parent. In append order.
        """
        parents = set(self._branches_from.values())
        return tuple(node for node in self._nodes if node.value not in parents)


@dataclass(frozen=True, slots=True)
class VariableDiff:
    """The derivable diff between two template versions' variable maps (AD-5).

    Names ``added`` (in the new map only), ``removed`` (in the old map only), and
    ``changed`` (present in both but with a differing ``fp1_identity`` — i.e. a
    changed number, unit-kind, flag, impact, or evidence). ``unchanged`` names the
    rest, so the diff is total over both maps.
    """

    added: tuple[str, ...]
    removed: tuple[str, ...]
    changed: tuple[str, ...]
    unchanged: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        """True when the two versions' variable maps are identical."""
        return not (self.added or self.removed or self.changed)


def diff_variable_maps(old: object, new: object) -> Result[VariableDiff]:
    """Derive the diff between two flattened variable maps (AD-5; DEC-0144).

    A structural diff by variable key: a key only in ``new`` is added, only in
    ``old`` is removed, in both with differing canonical identity is changed, and in
    both with identical identity is unchanged. Both arguments must be mappings of
    :class:`~qmf.risk.grammar.TemplateVariable`; anything else is ``invalid input``.
    """
    old_map = _coerce_variable_map("old", old)
    if isinstance(old_map, TypedRefusal):
        return old_map
    new_map = _coerce_variable_map("new", new)
    if isinstance(new_map, TypedRefusal):
        return new_map
    added = tuple(sorted(key for key in new_map if key not in old_map))
    removed = tuple(sorted(key for key in old_map if key not in new_map))
    changed: list[str] = []
    unchanged: list[str] = []
    for key in sorted(old_map.keys() & new_map.keys()):
        if old_map[key].fp1_identity() == new_map[key].fp1_identity():
            unchanged.append(key)
        else:
            changed.append(key)
    return Ok(
        VariableDiff(
            added=added,
            removed=removed,
            changed=tuple(changed),
            unchanged=tuple(unchanged),
        )
    )


def _coerce_variable_map(field: str, value: object) -> dict[str, TemplateVariable] | TypedRefusal:
    """Resolve a mapping of :class:`TemplateVariable`, or a refusal to return."""
    if not isinstance(value, Mapping):
        return invalid(
            field, "a variable map is a name-keyed mapping of TemplateVariable", given=repr(value)
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, TemplateVariable] = {}
    for key, variable in mapping.items():
        if not isinstance(key, str) or not isinstance(variable, TemplateVariable):
            return invalid(
                field,
                "a variable map keys names to TemplateVariable values",
                key=repr(key),
            )
        resolved[key] = variable
    return resolved
