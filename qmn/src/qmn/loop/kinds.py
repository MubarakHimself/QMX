"""Inbound observation classes and cycle-band effects for TN-5 (Story 24.4).

Accumulator overflow and slice-latency breach never drop execution or system
observations. Market-data coalescing emits explicit ``data quality`` evidence,
and the affected cycle receives entry-side ``no-new-entry`` while every exit or
protection act remains enactable (NFR-12; L39; DEC-0190).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Instant, Ok, RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "DATA_QUALITY_EVENT_TYPE",
    "CycleBand",
    "InboundObservation",
    "ObservationClass",
    "classify_observation",
    "entry_side_refused",
    "protection_enactable",
]


DATA_QUALITY_EVENT_TYPE: Final[str] = "data quality"

_MARKET_TOKENS: Final[frozenset[str]] = frozenset(
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
_EXECUTION_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "fill",
        "lifecycle",
        "submission-acknowledgement",
        "cancel-acknowledgement",
        "expiry",
        "close-by-venue",
        "execution",
        "order",
    }
)
_SYSTEM_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "system",
        "capability-profile",
        "venue-error",
        "data-quality",
        "data quality",
        "heartbeat",
        "reconnect",
        "gap-replay",
    }
)


class ObservationClass(StrEnum):
    """Overflow priority class for inbound observations (DEC-0190)."""

    MARKET_DATA = "market-data"
    EXECUTION = "execution"
    SYSTEM = "system"


class CycleBand(StrEnum):
    """Per-decision-cycle precondition bands (TN-14/TN-5; L39)."""

    OK = "ok"
    NO_NEW_ENTRY = "no-new-entry"


@dataclass(frozen=True, slots=True)
class InboundObservation:
    """One VenueClientPort observation stamped at the accumulator frontier.

    ``receive_wall`` is the slice frontier stamp; ``venue_instant`` rides beside
    it as evidence and never substitutes for the receive wall (DEC-0190).
    """

    observation_id: str
    stream_id: str
    observation_class: ObservationClass
    receive_wall: Instant
    payload: Mapping[str, object]
    venue_instant: Instant | None = None
    coalesce_key: str | None = None
    closed: bool = True

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "observation_id": self.observation_id,
            "stream_id": self.stream_id,
            "observation_class": self.observation_class.value,
            "receive_wall_time_ns": self.receive_wall.value_ns,
            "closed": self.closed,
            "payload": dict(self.payload),
        }
        if self.venue_instant is not None:
            body["venue_instant_ns"] = self.venue_instant.value_ns
        if self.coalesce_key is not None:
            body["coalesce_key"] = self.coalesce_key
        return MappingProxyType(body)

    @classmethod
    def try_create(
        cls,
        *,
        observation_id: object,
        stream_id: object,
        observation_class: object,
        receive_wall: object,
        payload: object,
        venue_instant: object = None,
        coalesce_key: object = None,
        closed: object = True,
    ) -> Result[InboundObservation]:
        """Validate and build one inbound observation."""
        oid = _token(observation_id)
        if oid is None:
            return _invalid(
                "observation_id",
                "an inbound observation names a non-empty observation id",
                given=repr(observation_id),
            )
        sid = _token(stream_id)
        if sid is None:
            return _invalid(
                "stream_id",
                "an inbound observation names a non-empty stream id",
                given=repr(stream_id),
            )
        klass = _coerce_class(observation_class)
        if klass is None:
            return _invalid(
                "observation_class",
                "observation_class is market-data | execution | system",
                given=repr(observation_class),
                allowed=[m.value for m in ObservationClass],
            )
        if not isinstance(receive_wall, Instant):
            return _invalid(
                "receive_wall",
                "the accumulator stamps a receive-wall Instant as the slice frontier",
                given=repr(type(receive_wall).__name__),
            )
        if not isinstance(payload, Mapping):
            return _invalid(
                "payload",
                "inbound observation payload is a mapping",
                given=repr(type(payload).__name__),
            )
        venue: Instant | None
        if venue_instant is None:
            venue = None
        elif isinstance(venue_instant, Instant):
            venue = venue_instant
        else:
            return _invalid(
                "venue_instant",
                "venue instant is an Instant or omitted",
                given=repr(type(venue_instant).__name__),
            )
        key: str | None
        if coalesce_key is None:
            key = None
        else:
            key = _token(coalesce_key)
            if key is None:
                return _invalid(
                    "coalesce_key",
                    "a coalesce key is a non-empty token when supplied",
                    given=repr(coalesce_key),
                )
        if not isinstance(closed, bool):
            return _invalid(
                "closed",
                "observation completeness is a bool; forming is closed=False",
                given=repr(closed),
            )
        return Ok(
            cls(
                observation_id=oid,
                stream_id=sid,
                observation_class=klass,
                receive_wall=receive_wall,
                payload=MappingProxyType(dict(cast("Mapping[str, object]", payload))),
                venue_instant=venue,
                coalesce_key=key,
                closed=closed,
            )
        )


def classify_observation(kind: object) -> ObservationClass:
    """Map a wire/observation kind token onto an overflow priority class."""
    token = str(kind).strip().lower() if kind is not None else ""
    if token in _MARKET_TOKENS or token.startswith("market"):
        return ObservationClass.MARKET_DATA
    if token in _EXECUTION_TOKENS or token.startswith("execution"):
        return ObservationClass.EXECUTION
    if token in _SYSTEM_TOKENS or token.startswith("system"):
        return ObservationClass.SYSTEM
    # Unknown kinds are treated as system so overflow never silently drops them.
    return ObservationClass.SYSTEM


def entry_side_refused(band: CycleBand, *, act: object) -> bool:
    """True when ``act`` is refused by an entry-side-only ``no-new-entry`` band."""
    if band is not CycleBand.NO_NEW_ENTRY:
        return False
    token = str(act).strip().lower()
    return token in {"place_order", "risk-increasing-amend", "entry"}


def protection_enactable(band: CycleBand, *, act: object) -> bool:
    """True when an exit/protection act remains enactable under ``band`` (L39)."""
    del band  # entry-side bands never suppress protection.
    token = str(act).strip().lower()
    return token in {
        "cancel_order",
        "close_position",
        "close_all",
        "amend_protection",
        "close_full",
        "tighten_protective_stop",
        "exit",
        "protection",
    }


def _coerce_class(value: object) -> ObservationClass | None:
    if isinstance(value, ObservationClass):
        return value
    if isinstance(value, str):
        try:
            return ObservationClass(value.strip().lower())
        except ValueError:
            return None
    return None


def _token(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )
