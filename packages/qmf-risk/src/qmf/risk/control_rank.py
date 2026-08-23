"""Story 10.3 — the control-rank table and rank uniqueness (COMP-QMF-RISK).

Same-tick arbitration is resolved strictly by rank at exactly one arbitration point
per ``(VenueId, account)`` command stream, so the rank table is **BMS-declared, one
per command stream** — several Books share one stream, and a Book-owned table would
put two rank orders at one arbiter (AD-37; DEC-0151). This module defines that table
on ``qmf-core`` nouns and the admission Layer-1 uniqueness check:

* :class:`ControlActionKind` — the CT-30 control-action kinds a rank table ranks
  (``suspend_new | drain | flatten | resume``);
* :class:`ControlRankRow` — one ``(control_action_kind, rank)`` row, the rank a
  declared, mandatory, non-defaultable count (its existence is QMF's, its value is
  the BMS's — no spine default);
* :class:`ControlRankTable` — a **total order with uniqueness enforced at admission
  Layer 1**: two control-action kinds sharing a rank is an ``invalid input`` refusal,
  and a kind appearing twice is too (DEC-0151).

The ordering the ranks encode is corpus-derived (constitution ``bot → book → BMS →
operator`` plus the protection funnel), highest first; QMF supplies no rank *values*,
only the table's shape and its total-order/uniqueness law. Imports only ``qmf-core``
and sibling ``qmf.risk`` modules; nothing imports ``qmf.risk`` (default-deny,
L30/DEC-0120). Ratified ``defined-unwired`` surface — no wiring is authorized here
(DEC-0158).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from qmf.core import Ok, Result, TypedRefusal
from qmf.risk._common import coerce_enum, invalid, type_name

__all__ = [
    "ControlActionKind",
    "ControlRankRow",
    "ControlRankTable",
    "check_control_rank_uniqueness",
]

# This module's own contract format version stamped into fp1 identity content; its
# meaning never mutates — an incompatible change mints the next version (L15).
_CONTROL_RANK_FORMAT_VERSION = 1


class ControlActionKind(StrEnum):
    """The CT-30 control-action kinds a rank table ranks (DEC-0150, DEC-0151).

    Addable never redefined, each defined once at CT-30: ``suspend_new`` (no new
    entries; open/resting untouched), ``drain`` (no new entries and resting orders run
    to their own terminal state), ``flatten`` (close the scope), and ``resume``.
    """

    SUSPEND_NEW = "suspend_new"
    DRAIN = "drain"
    FLATTEN = "flatten"
    RESUME = "resume"


@dataclass(frozen=True, slots=True)
class ControlRankRow:
    """One ``(control_action_kind, rank)`` row of the rank table (AD-37; DEC-0151).

    The ``rank`` is a declared, mandatory, non-defaultable count — its existence is
    QMF's, its value the BMS's; there is no spine default. A lower rank number means a
    higher arbitration priority (operator highest), but this row carries only the
    value; the ordering law is the table's.
    """

    control_action_kind: ControlActionKind
    rank: int

    @classmethod
    def try_create(cls, control_action_kind: object, rank: object) -> Result[ControlRankRow]:
        """Validate and build a :class:`ControlRankRow`, value-or-refusal.

        The kind names a member of the closed :class:`ControlActionKind` set; the rank
        is a non-negative integer (a bool, an int subclass, is not a rank; a missing
        rank is ``invalid input`` — the field is non-defaultable).
        """
        resolved_kind = coerce_enum(ControlActionKind, control_action_kind)
        if resolved_kind is None:
            return invalid(
                "control_action_kind",
                "a rank row names a control-action kind from the closed CT-30 set",
                given=repr(control_action_kind),
                allowed=[member.value for member in ControlActionKind],
            )
        if isinstance(rank, bool) or not isinstance(rank, int):
            return invalid(
                "rank",
                "a rank is a mandatory, non-defaultable integer (its value is the BMS's)",
                given=repr(rank),
            )
        if rank < 0:
            return invalid("rank", "a rank is a non-negative integer", given=repr(rank))
        return Ok(cls(control_action_kind=resolved_kind, rank=rank))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this row."""
        return {
            "class": "control-rank-row",
            "control_action_kind": self.control_action_kind.value,
            "rank": self.rank,
            "format_version": _CONTROL_RANK_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ControlRankTable:
    """A BMS-declared control-rank table — a total order, unique (AD-37; DEC-0151).

    Carries one :class:`ControlRankRow` per ranked control-action kind, canonically
    ordered by rank. Uniqueness is enforced at admission Layer 1: **two control-action
    kinds may not share a rank** (``invalid input``), and no kind appears twice. One
    table per ``(VenueId, account)`` command stream — the arbitration point's own
    cardinality.
    """

    rows: tuple[ControlRankRow, ...]

    @classmethod
    def try_create(cls, rows: object) -> Result[ControlRankTable]:
        """Validate and build a :class:`ControlRankTable`, value-or-refusal.

        ``rows`` is a non-empty collection of :class:`ControlRankRow`; a kind appearing
        twice or two kinds sharing a rank is ``invalid input`` (see
        :func:`check_control_rank_uniqueness`). Rows are stored canonically ordered by
        rank so declaration order never forks the table's identity.
        """
        resolved = _coerce_rows(rows)
        if isinstance(resolved, TypedRefusal):
            return resolved
        uniqueness = check_control_rank_uniqueness(resolved)
        if isinstance(uniqueness, TypedRefusal):
            return uniqueness
        ordered = tuple(sorted(resolved, key=lambda row: row.rank))
        return Ok(cls(rows=ordered))

    def ranks_by_kind(self) -> Mapping[ControlActionKind, int]:
        """The rank each control-action kind holds (a read-only view)."""
        return MappingProxyType({row.control_action_kind: row.rank for row in self.rows})

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — rows in rank order."""
        return {
            "class": "control-rank-table",
            "rows": [row.fp1_identity() for row in self.rows],
            "format_version": _CONTROL_RANK_FORMAT_VERSION,
        }


def _coerce_rows(rows: object) -> tuple[ControlRankRow, ...] | TypedRefusal:
    """Resolve a non-empty collection of :class:`ControlRankRow` values."""
    given = type_name(rows)
    if isinstance(rows, (str, bytes, Mapping)) or not isinstance(rows, Iterable):
        return invalid(
            "rows",
            "a control-rank table is a collection of ControlRankRow values",
            given=given,
        )
    items: list[ControlRankRow] = []
    for item in cast("Iterable[object]", rows):
        if not isinstance(item, ControlRankRow):
            return invalid("rows", "each row is a ControlRankRow", given=repr(item))
        items.append(item)
    if not items:
        return invalid("rows", "a control-rank table declares at least one row")
    return tuple(items)


def check_control_rank_uniqueness(rows: object) -> Result[None]:
    """Enforce the total-order/uniqueness law of a rank table (AD-37; DEC-0151).

    **Two control-action kinds sharing a rank is an ``invalid input`` refusal**, and a
    control-action kind appearing twice is too — a rank table is a total order with
    uniqueness enforced at admission Layer 1. ``rows`` is a collection of
    :class:`ControlRankRow` (or a built :class:`ControlRankTable`'s rows). Returns
    ``Ok(None)`` when the table is a well-formed total order.
    """
    if isinstance(rows, ControlRankTable):
        candidate: object = rows.rows
    else:
        candidate = rows
    given = type_name(candidate)
    if isinstance(candidate, (str, bytes, Mapping)) or not isinstance(candidate, Iterable):
        return invalid(
            "rows",
            "the uniqueness check reads a collection of ControlRankRow values",
            given=given,
        )
    seen_kinds: set[ControlActionKind] = set()
    seen_ranks: dict[int, ControlActionKind] = {}
    for item in cast("Iterable[object]", candidate):
        if not isinstance(item, ControlRankRow):
            return invalid("rows", "each row is a ControlRankRow", given=repr(item))
        if item.control_action_kind in seen_kinds:
            return invalid(
                "rows",
                "a control-action kind appears at most once in a rank table",
                control_action_kind=item.control_action_kind.value,
            )
        if item.rank in seen_ranks:
            return invalid(
                "rows",
                "two control-action kinds may not share a rank; ranks are a total order with "
                "uniqueness enforced at admission Layer 1",
                rank=item.rank,
                first=seen_ranks[item.rank].value,
                second=item.control_action_kind.value,
            )
        seen_kinds.add(item.control_action_kind)
        seen_ranks[item.rank] = item.control_action_kind
    return Ok(None)
