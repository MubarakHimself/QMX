"""Host mint of mill CT-07 ``promoted-from`` (Story 51.1).

The QML authoring composition root stamps the dated lineage edge. The edge is
lineage, not governed evidence — CT-32 and seats cite Bot ``fp1`` only.
"""

from __future__ import annotations

from typing import Final

from qmf.core.chrono import WriterId
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.registry import EdgeType, LineageEdge

from qml._refuse import invalid, policy
from qml.conformance.registration import (
    MILL_RESEARCH_CLASS,
    PROMOTED_FROM_EDGE_TYPE,
    Graduation,
    cite_registered_bot,
)

__all__ = [
    "MILL_PROMOTED_FROM_IS_GOVERNED_EVIDENCE",
    "MILL_PROMOTED_FROM_IS_LINEAGE",
    "refuse_research_ref_as_governed_evidence",
    "stamp_promoted_from_edge",
]

MILL_PROMOTED_FROM_IS_LINEAGE: Final[bool] = True
MILL_PROMOTED_FROM_IS_GOVERNED_EVIDENCE: Final[bool] = False


def stamp_promoted_from_edge(
    *,
    graduation: object,
    writer: object,
) -> Result[LineageEdge]:
    """Stamp CT-07 ``promoted-from`` with ``to_ref = research_ref`` (host WriterId)."""
    if not isinstance(graduation, Graduation):
        return invalid(
            "graduation",
            "the host stamps promoted-from from a mill Graduation edge intent",
            given=type(graduation).__name__,
        )
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "the host supplies a WriterId when stamping the CT-07 promoted-from edge",
            given=type(writer).__name__,
        )
    intent = graduation.promoted_from_edge
    if intent.edge_type != PROMOTED_FROM_EDGE_TYPE:
        return invalid(
            "edge_type",
            "mill graduation stamps promoted-from only",
            given=intent.edge_type,
        )
    if intent.to_ref.value != graduation.originating_research_ref.value:
        return invalid(
            "to_ref",
            "promoted-from to_ref must equal originating research_ref",
            to_ref=intent.to_ref.value,
            research_ref=graduation.originating_research_ref.value,
        )
    if intent.from_ref.value == intent.to_ref.value:
        return invalid(
            "originating_research_ref",
            "a graduation links a governed Bot to a distinct originating research "
            "artifact; the two fingerprints cannot be the same",
            ref=intent.to_ref.value,
        )
    stamped = LineageEdge.try_create(
        EdgeType.PROMOTED_FROM,
        intent.from_ref,
        intent.to_ref,
        writer,
    )
    if is_refusal(stamped):
        return stamped
    return Ok(stamped.value)


def refuse_research_ref_as_governed_evidence(
    *,
    research_ref: object,
    candidate: object = None,
) -> Result[None]:
    """Lineage ``research_ref`` is not governed evidence; seats cite Bot fp1 only."""
    cited = research_ref
    if isinstance(research_ref, Fingerprint):
        cited = research_ref
    refused = cite_registered_bot(
        candidate=candidate,
        cited_fp1=cited,
        kind="governed-evidence",
    )
    if is_refusal(refused):
        return policy(
            "governed_evidence",
            "promoted-from to research_ref is lineage, not governed evidence; "
            "CT-32 and seats cite Bot fp1 only",
            research_class=MILL_RESEARCH_CLASS,
            is_lineage=MILL_PROMOTED_FROM_IS_LINEAGE,
            is_governed_evidence=MILL_PROMOTED_FROM_IS_GOVERNED_EVIDENCE,
            cause=dict(refused.context),
        )
    return policy(
        "governed_evidence",
        "promoted-from to research_ref is lineage, not governed evidence; "
        "CT-32 and seats cite Bot fp1 only",
        research_class=MILL_RESEARCH_CLASS,
        is_lineage=MILL_PROMOTED_FROM_IS_LINEAGE,
        is_governed_evidence=MILL_PROMOTED_FROM_IS_GOVERNED_EVIDENCE,
    )
