"""CT-13 journal mapping for live intake — closed seven, no ``observation`` type.

FTR-01: position/balance read-back mapping onto CT-13 is refused until a
contract annotation names the row. This module never infers or mints an
``observation`` journal type and never adds an eighth type (CT-13/CT-20).
"""

from __future__ import annotations

from typing import Final

from qmf.core import Ok, Result, TypedRefusal

from qmn.data._refuse import clean_token, invalid, unsupported

__all__ = [
    "CT13_SEVEN_EVENT_TYPES",
    "FTR01_BLOCKED_KINDS",
    "OBSERVATION_JOURNAL_TYPE",
    "assert_no_eighth_journal_type",
    "journal_event_for_kind",
    "refuse_ftr01_mapping",
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

FTR01_BLOCKED_KINDS: Final[frozenset[str]] = frozenset(
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
        "closed seven stand and FTR-01 blocks an eighth type",
        ftr="FTR-01",
        failure_id="data.intake.observation_journal_type",
        given=OBSERVATION_JOURNAL_TYPE if given is None else repr(given),
        allowed_ct13=sorted(CT13_SEVEN_EVENT_TYPES),
    )


def refuse_ftr01_mapping(*, kind: object) -> TypedRefusal:
    """Refuse accepting a live position/balance → CT-13 mapping (FTR-01)."""
    return unsupported(
        "observation_kind",
        "position/balance read-back mapping onto CT-13 remains unresolved "
        "(FTR-01); this story refuses acceptance for that mapping and does not "
        "mint an eighth node-private journal type",
        ftr="FTR-01",
        failure_id="data.intake.ftr01_mapping",
        blocked=sorted(FTR01_BLOCKED_KINDS),
        given=repr(kind),
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

    Position/balance read-backs are FTR-01-blocked (the mapping AC is skipped).
    Asking for an ``observation`` event type is refused.
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
    if normalized in FTR01_BLOCKED_KINDS:
        return refuse_ftr01_mapping(kind=normalized)
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
