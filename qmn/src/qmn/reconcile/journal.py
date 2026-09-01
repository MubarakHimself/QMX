"""FTR-01 — position/balance read-backs map onto CT-13's closed seven.

DEC-0247 adds two CT-20 observation kinds (``position-read-back``,
``balance-read-back``) and maps them onto an existing AD-21 journal event type.
No eighth node-private journal type is minted (FTR-01; CT-13; DEC-0198).
"""

from __future__ import annotations

from typing import Final

from qmf.core import Ok, Result

from qmn.reconcile._refuse import clean_token, invalid, unsupported

__all__ = [
    "CT13_SEVEN_EVENT_TYPES",
    "READBACK_CT13_EVENT_TYPE",
    "READBACK_OBSERVATION_KINDS",
    "assert_no_eighth_journal_type",
    "map_readback_journal_event_type",
]

# AD-21 / CT-13 closed seven — never an eighth node-private type (FTR-01).
CT13_SEVEN_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "decision",
        "order",
        "fill",
        "risk transition",
        "promotion",
        "data quality",
        "control action",
    }
)

# Read-backs are CT-20 observation kinds; among the seven they journal as
# ``data quality`` evidence — never a novel ``observation`` / ``reconciliation``
# eighth type (DEC-0247; FTR-01).
READBACK_CT13_EVENT_TYPE: Final[str] = "data quality"

READBACK_OBSERVATION_KINDS: Final[frozenset[str]] = frozenset(
    {"position-readback", "position-read-back", "balance-readback", "balance-read-back"}
)


def map_readback_journal_event_type(kind: object) -> Result[str]:
    """Map a position/balance read-back kind onto one of CT-13's seven types.

    Returns ``data quality``. Any proposed type outside the closed seven is an
    unsupported-capability refusal carrying ``ftr = FTR-01``.
    """
    token = clean_token(kind)
    if token is None:
        return invalid(
            "kind",
            "read-back journal mapping requires a non-blank observation kind",
            given=repr(kind),
        )
    normalized = token.strip().lower().replace("_", "-")
    if normalized not in READBACK_OBSERVATION_KINDS:
        return invalid(
            "kind",
            "only position-read-back and balance-read-back map through this door",
            given=repr(kind),
            allowed=sorted(READBACK_OBSERVATION_KINDS),
        )
    return assert_no_eighth_journal_type(READBACK_CT13_EVENT_TYPE)


def assert_no_eighth_journal_type(proposed: object) -> Result[str]:
    """Refuse any journal event type outside CT-13's closed seven (FTR-01)."""
    token = clean_token(proposed)
    if token is None:
        return invalid(
            "event_type",
            "a CT-13 journal event type is a non-blank token among the closed seven",
            given=repr(proposed),
            allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
        )
    if token not in CT13_SEVEN_EVENT_TYPES:
        return unsupported(
            "event_type",
            "position/balance read-backs map onto CT-13's existing seven; an eighth "
            "node-private journal type is refused (FTR-01)",
            ftr="FTR-01",
            given=token,
            allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
        )
    return Ok(token)
