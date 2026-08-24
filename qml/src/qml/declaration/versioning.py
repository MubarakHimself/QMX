"""AD-30 git-logic versioning for CT-33 Bot definitions (DEC-0173, DEC-0144).

An append-only ``branches-from`` graph (multiple heads legal); ``current`` is a
separate dated pointer record, never a graph property. Every version stays
readable forever. ``continues-performance`` carries a track record across
versions only when human-signed. Re-binding, seats, and paper flips never mint
a Bot version — they are occurrence facts outside this graph.
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result
from qmf.registry import EdgeType, LineageEdge

from qml._refuse import invalid, policy, unavailable

__all__ = [
    "BotVersionGraph",
    "CurrentPointer",
    "branches_from_edge",
    "continues_performance_edge",
]


@dataclass(frozen=True, slots=True)
class CurrentPointer:
    """A dated pointer naming the current Bot definition version (DEC-0144).

    ``current`` is a separate dated record, not a graph property. Re-pointing
    appends a new pointer with a later injected instant; an old pointer is never
    mutated. The pointer is not Bot identity — seats cite a Bot ``fp1``.
    """

    fingerprint: Fingerprint
    dated_at: Instant

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "bot-current-pointer",
            "fingerprint": self.fingerprint.value,
            "dated_at": self.dated_at.fp1_identity(),
        }


class BotVersionGraph:
    """Append-only, multiple-head Bot version graph over CT-33 ``fp1`` nodes."""

    def __init__(self) -> None:
        self._nodes: list[Fingerprint] = []
        self._node_set: set[str] = set()
        self._branches_from: dict[str, str] = {}
        self._pointers: list[CurrentPointer] = []

    def append_version(self, fingerprint: object, branches_from: object = None) -> Result[None]:
        """Append a Bot version node, optionally branching from a parent.

        Re-adding an existing ``fp1`` is ``invalid input`` — a version is immutable;
        a changed default, confluence, footprint, or logic artifact mints a NEW
        fingerprint. A dangling parent is ``unavailable dependency``.
        """
        if not isinstance(fingerprint, Fingerprint):
            return invalid(
                "fingerprint",
                "a Bot version node is identified by a Fingerprint",
                given=repr(fingerprint),
            )
        if fingerprint.value in self._node_set:
            return invalid(
                "fingerprint",
                "a Bot version is immutable and already present; a changed default, "
                "confluence, footprint, or logic artifact mints a NEW Bot (a changed "
                "number changes fp1), never a re-add of an existing one",
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
                    "branches_from",
                    "a Bot version may not branch from itself",
                    given=fingerprint.value,
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
        """Append a dated ``current`` pointer naming a known Bot version."""
        if not isinstance(fingerprint, Fingerprint):
            return invalid(
                "fingerprint",
                "the current pointer names a Fingerprint",
                given=repr(fingerprint),
            )
        if fingerprint.value not in self._node_set:
            return unavailable(
                "fingerprint",
                "the current pointer must name a known Bot version node",
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
        """The current Bot version per the latest dated pointer, or ``None``."""
        if not self._pointers:
            return None
        return self._pointers[-1].fingerprint

    def pointer_history(self) -> tuple[CurrentPointer, ...]:
        return tuple(self._pointers)

    def versions(self) -> tuple[Fingerprint, ...]:
        """Every version node, in append order — all readable forever."""
        return tuple(self._nodes)

    def is_readable(self, fingerprint: object) -> bool:
        return isinstance(fingerprint, Fingerprint) and fingerprint.value in self._node_set

    def parent_of(self, fingerprint: object) -> Fingerprint | None:
        if not isinstance(fingerprint, Fingerprint):
            return None
        parent_value = self._branches_from.get(fingerprint.value)
        if parent_value is None:
            return None
        return Fingerprint(value=parent_value)

    def heads(self) -> tuple[Fingerprint, ...]:
        """Tip versions nothing branches from — multiple heads are legal."""
        parents = set(self._branches_from.values())
        return tuple(node for node in self._nodes if node.value not in parents)


def branches_from_edge(
    *,
    child: object,
    parent: object,
    writer: object,
) -> Result[LineageEdge]:
    """A CT-07 ``branches-from`` edge from a child Bot version to its parent."""
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "a branches-from edge stamps a host WriterId (machine, authoring role, kind)",
            given=repr(writer),
        )
    return LineageEdge.try_create(EdgeType.BRANCHES_FROM, child, parent, writer)


def continues_performance_edge(
    *,
    child: object,
    parent: object,
    writer: object,
    human_signed: object,
) -> Result[LineageEdge]:
    """A CT-07 ``continues-performance`` edge — track record, only when human-signed.

    The edge asserts comparability across Bot versions and moves no money. An
    unsigned attempt is ``policy rejection`` (DEC-0173, DEC-0158).
    """
    if human_signed is not True:
        return policy(
            "continues_performance",
            "continues-performance carries a track record across Bot versions only "
            "when human-signed; it is never inferred from branches-from",
            human_signed=repr(human_signed),
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "a continues-performance edge stamps a host WriterId",
            given=repr(writer),
        )
    return LineageEdge.try_create(EdgeType.CONTINUES_PERFORMANCE, child, parent, writer)
