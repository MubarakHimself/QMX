"""Remaining TN-24 venue-edge dispositions: requote and deep-history sources (TN-24i).

A cTrader requote is an ordinary mapped venue rejection through the pinned CT-18
error map — never a new outcome type. Dukascopy remains the node deep-history
source; TrueFX and HistData are recorded nonblocking companions only. This
module records that inventory and refuses companion-source implementation
(DEC-0209; Story 24.9).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.venue.capabilities import (
    ErrorMap,
    ErrorMapResolution,
    ErrorMapRow,
    SubmissionOutcomeClass,
)

__all__ = [
    "COMPANION_SOURCE_IMPLEMENTATION_FORBIDDEN",
    "DEEP_HISTORY_NODE_SOURCE",
    "REQUOTE_OUTCOME_TYPE_FORBIDDEN",
    "DeepHistorySourceRole",
    "RequoteMapping",
    "companion_source_implementation_allowed",
    "deep_history_source_inventory",
    "map_requote",
    "requote_error_map_row",
]


DEEP_HISTORY_NODE_SOURCE: Final[str] = "dukascopy"
REQUOTE_OUTCOME_TYPE_FORBIDDEN: Final[str] = "requote"
COMPANION_SOURCE_IMPLEMENTATION_FORBIDDEN: Final[bool] = True

_COMPANIONS: Final[tuple[str, ...]] = ("truefx", "histdata")


class DeepHistorySourceRole(StrEnum):
    """How a deep-history source participates in the node inventory (TN-24i)."""

    NODE_SOURCE = "node-source"
    NONBLOCKING_COMPANION = "nonblocking-companion"


@dataclass(frozen=True, slots=True)
class RequoteMapping:
    """A requote resolved as an ordinary mapped ``rejected-by-venue`` (TN-24i)."""

    venue_code: str
    context: str
    outcome_class: SubmissionOutcomeClass
    mapped: bool
    minted_outcome_type: str | None

    @property
    def is_ordinary_rejection(self) -> bool:
        return (
            self.mapped
            and self.outcome_class is SubmissionOutcomeClass.REJECTED_BY_VENUE
            and self.minted_outcome_type is None
        )


def deep_history_source_inventory() -> Mapping[str, DeepHistorySourceRole]:
    """Recorded deep-history inventory: Dukascopy node source, companions only."""
    rows: dict[str, DeepHistorySourceRole] = {
        DEEP_HISTORY_NODE_SOURCE: DeepHistorySourceRole.NODE_SOURCE,
    }
    for name in _COMPANIONS:
        rows[name] = DeepHistorySourceRole.NONBLOCKING_COMPANION
    return MappingProxyType(rows)


def companion_source_implementation_allowed() -> bool:
    """TrueFX/HistData stay recorded companions — no companion implementation (TN-24i)."""
    return not COMPANION_SOURCE_IMPLEMENTATION_FORBIDDEN


def requote_error_map_row(
    *,
    venue_code: object = "REQUOTE",
    context: object = "place_order",
) -> Result[ErrorMapRow]:
    """Build the pinned error-map row that makes a requote ``rejected-by-venue``."""
    return ErrorMapRow.try_create(
        venue_code,
        context,
        RefusalCategory.POLICY_REJECTION,
        Retryability.NO,
        SubmissionOutcomeClass.REJECTED_BY_VENUE,
    )


def map_requote(
    error_map: object,
    venue_code: object,
    context: object,
) -> Result[RequoteMapping]:
    """Map a requote through the CT-18 error map as ordinary rejected-by-venue.

    Never mints a ``requote`` outcome type. An unmapped code stays the fail-closed
    UNKNOWN default from the map — still not a requote vocabulary of its own.
    """
    if not isinstance(error_map, ErrorMap):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "error_map",
                "reason": "requote resolves only through a pinned CT-18 ErrorMap",
                "given": type(error_map).__name__,
            },
        )
    if isinstance(venue_code, str) and venue_code.strip().lower() == REQUOTE_OUTCOME_TYPE_FORBIDDEN:
        # The venue code token "REQUOTE" is fine as a map key; the forbidden thing is
        # minting a submission-outcome class named requote.
        pass
    resolved = error_map.resolve(venue_code, context)
    if is_refusal(resolved):
        return resolved
    if not is_ok(resolved):
        return resolved
    outcome: ErrorMapResolution = resolved.value
    if outcome.outcome_class is SubmissionOutcomeClass.REJECTED_BY_VENUE and outcome.mapped:
        return Ok(
            RequoteMapping(
                venue_code=outcome.venue_code,
                context=outcome.context,
                outcome_class=outcome.outcome_class,
                mapped=True,
                minted_outcome_type=None,
            )
        )
    return Ok(
        RequoteMapping(
            venue_code=outcome.venue_code,
            context=outcome.context,
            outcome_class=outcome.outcome_class,
            mapped=outcome.mapped,
            minted_outcome_type=None,
        )
    )
