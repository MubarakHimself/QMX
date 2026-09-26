"""Reference usage — CT-20 venue observations and their journal events (L27, AR-21).

Executable::

    python packages/qmf-venue/examples/observation_events_usage.py

Shows the things CT-20 / DEC-0137 / DEC-0140 pin down:

1. The cardinality law: every :class:`~qmf.venue.ObservationKind` maps to
   EXACTLY ONE journal event type, ``observation.<kind>``, and the mapping is
   total over the closed vocabulary.
2. A value that does not name an observation kind is an ``invalid input``
   typed refusal — returned, never raised (R-002, CT-04; the venue boundary
   succeeds or refuses).
3. The four-outcome submission law and the risk-reducing command vocabulary
   are closed, nameable sets — the roster downstream policy quotes, never
   re-derives.
"""

from __future__ import annotations

from qmf.core import TypedRefusal
from qmf.venue import (
    FOUR_OUTCOME_LAW,
    RISK_REDUCING_KINDS,
    ObservationKind,
    observation_journal_event_type,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def every_kind_maps_to_exactly_one_event_type() -> int:
    """CT-20 cardinality law: one journal event type per observation kind."""
    mapped: dict[str, str] = {}
    for kind in ObservationKind:
        event_type = observation_journal_event_type(kind)
        if not isinstance(event_type, str):
            raise AssertionError(f"{kind.value} must map, not refuse")
        _require(event_type == f"observation.{kind.value}", "the mapping is deterministic")
        mapped[kind.value] = event_type
    _require(len(set(mapped.values())) == len(mapped), "no two kinds share an event type")
    return len(mapped)


def malformed_kind_is_a_typed_refusal() -> str:
    """R-002: a public venue boundary succeeds or returns a typed refusal."""
    refused = observation_journal_event_type("not-a-kind")
    if not isinstance(refused, TypedRefusal):
        raise AssertionError("a malformed kind must refuse, never raise")
    _require(refused.category.value == "invalid input", "the refusal category is typed")
    return refused.category.value


def closed_vocabularies_are_nameable() -> tuple[int, int]:
    """The four-outcome law and risk-reducing kinds are closed, quotable sets."""
    outcomes = sorted(outcome.value for outcome in FOUR_OUTCOME_LAW)
    _require(len(outcomes) == 4, "exactly four submission outcomes")
    reducing = sorted(kind.value for kind in RISK_REDUCING_KINDS)
    _require("close_position" in reducing and "cancel_order" in reducing, "risk reducers")
    return len(outcomes), len(reducing)


def main() -> None:
    print(f"observation kinds mapped one-to-one: {every_kind_maps_to_exactly_one_event_type()}")
    print(f"malformed kind refused: {malformed_kind_is_a_typed_refusal()}")
    outcomes, reducing = closed_vocabularies_are_nameable()
    print(f"submission outcomes: {outcomes}; risk-reducing kinds: {reducing}")
    print("observation events usage ok")


if __name__ == "__main__":
    main()
