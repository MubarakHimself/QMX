"""CT-13 journal mapping for live intake — closed seven, no ``observation`` type.

Position/balance read-backs are CT-20 observation kinds (DEC-0247). They map
onto CT-13 ``data quality``. This module never infers or mints an
``observation`` journal type and never adds an eighth type (CT-13/CT-20;
DEC-0266).
"""

from __future__ import annotations

from typing import Final

from qmf.core import Ok, Result, TypedRefusal

from qmn.data._refuse import clean_token, invalid, unsupported

__all__ = [
    "CT13_SEVEN_EVENT_TYPES",
    "OBSERVATION_JOURNAL_TYPE",
    "READBACK_KINDS",
    "assert_no_eighth_journal_type",
    "journal_event_for_kind",
    "refuse_observation_journal_type",
]


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

OBSERVATION_JOURNAL_TYPE: Final[str] = "observation"

# CT-20 observation kinds (DEC-0247). The word "observation" names the kind,
# not a journal type — these rows journal as CT-13 ``data quality`` (DEC-0266).
READBACK_KINDS: Final[frozenset[str]] = frozenset(
    {
        "position-readback",
        "position-read-back",
        "position_readback",
        "balance-readback",
        "balance-read-back",
        "balance_readback",
    }
)

_MARKET: Final[frozenset[str]] = frozenset(
    {
        "spot",
        "tick",
        "bar",
        "depth",
        "trendbar",
        "trendbar-in-spot",
        "market-data",
        "quote",
    }
)
_FILL: Final[frozenset[str]] = frozenset({"fill", "execution", "execution-fill", "deal"})
_LIFECYCLE: Final[frozenset[str]] = frozenset(
    {
        "lifecycle",
        "submission-acknowledgement",
        "cancel-acknowledgement",
        "expiry",
        "close-by-venue",
        "order",
    }
)


def refuse_observation_journal_type(*, given: object = None) -> TypedRefusal:
    """Refuse minting CT-13 ``observation`` — it is not one of the closed seven."""
    return unsupported(
        "event_type",
        "data intake never infers or mints an observation journal type; CT-13's "
        "closed seven stand and an eighth type is refused",
        ftr="FTR-01",
        failure_id="data.intake.observation_journal_type",
        given=OBSERVATION_JOURNAL_TYPE if given is None else repr(given),
        allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
    )


def assert_no_eighth_journal_type(proposed: object) -> Result[str]:
    """Admit only a closed-seven token; refuse ``observation`` and any eighth type."""
    token = clean_token(proposed)
    if token is None:
        return invalid(
            "event_type",
            "a CT-13 journal event type is a non-blank token among the closed seven",
            given=repr(proposed),
            allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
        )
    normalized = token.strip().lower()
    if normalized == OBSERVATION_JOURNAL_TYPE:
        return refuse_observation_journal_type(given=normalized)
    if normalized not in CT13_SEVEN_EVENT_TYPES:
        return unsupported(
            "event_type",
            "an eighth node-private journal type is refused (FTR-01); map onto "
            "CT-13's existing seven",
            ftr="FTR-01",
            failure_id="data.intake.observation_journal_type",
            given=normalized,
            allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
        )
    return Ok(normalized)


def journal_event_for_kind(kind: object) -> Result[str]:
    """Map an accepted live observation kind onto one of CT-13's seven types.

    Position/balance read-backs journal as ``data quality``. Asking for an
    ``observation`` event type is refused — that word is the CT-20 kind name.
    """
    token = clean_token(kind)
    if token is None:
        return invalid(
            "kind",
            "journal mapping requires a non-blank observation kind",
            given=repr(kind),
        )
    normalized = token.strip().lower().replace("_", "-")
    if normalized == OBSERVATION_JOURNAL_TYPE:
        return refuse_observation_journal_type(given=normalized)
    if normalized in READBACK_KINDS:
        return Ok("data quality")
    if normalized in _MARKET:
        return Ok("data quality")
    if normalized in _FILL:
        return Ok("fill")
    if normalized in _LIFECYCLE:
        return Ok("order")
    if normalized in {"data-quality", "data quality"}:
        return Ok("data quality")
    if normalized in {"heartbeat", "reconnect", "gap-replay", "system", "capability-profile"}:
        return Ok("control action")
    if normalized == "venue-error":
        return Ok("data quality")
    return invalid(
        "kind",
        "journal mapping requires an accepted live observation kind",
        given=repr(kind),
        allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
    )
