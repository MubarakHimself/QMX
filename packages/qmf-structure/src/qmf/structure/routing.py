"""CT-17 — the routing test and declared-input indicator consumption (COMP-QMF-STRUCTURE).

The routing test separates the two libraries so a concept lands in exactly one (CT-17;
DEC-0129, DEC-0126, DEC-0127):

* **a value per evaluation instant is CT-16** — an indicator, one number (or vector) at every
  evaluation instant;
* **a discrete object with a birth and a lifetime is CT-17** — a structure object, minted once
  at observation and evolving through append-only records.

:func:`route` classifies a concept from those two declared properties. A concept expressible
**both** ways must declare which it is (refused as ``invalid input`` until it does); a concept
that is neither is likewise refused — the routing test admits exactly one answer.

**A family needing an indicator consumes it as a declared input, never re-implemented inline
(FM-6, DEC-0126, DEC-0127).** When a structure family needs a per-evaluation-instant value it
does **not** re-compute the indicator's arithmetic — a governed producer already publishes it.
It consumes the indicator's **result** as a declared input through the composition law: the
indicator result's fingerprint enters the structure object's input fingerprints (and thereby
its result label), so the dependency is recorded in lineage and the arithmetic is never
duplicated. :class:`IndicatorResultInput` is that declared-input seam and
:func:`consume_indicator_input` is the consumption that returns the fingerprint to record;
re-implementing the arithmetic inline is the FM-6 contract defect this makes unnecessary.

Default-deny holds: this module imports **only** ``qmf.core``. It defines no indicator and
computes no indicator arithmetic — it only names how a family consumes one. Public value types
are frozen dataclasses, the seam is a ``typing.Protocol``, and every operation succeeds or
RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain failure is never raised across the
boundary (DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from qmf.core import (
    Fingerprint,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
)

__all__ = [
    "IndicatorResultInput",
    "RoutingKind",
    "consume_indicator_input",
    "route",
]


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a routing operation returns (CT-04; DEC-0109)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _as_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string, or
    ``None`` — the ``object`` parameter keeps the check real for a duck-typed Protocol member."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


class RoutingKind(StrEnum):
    """Which library a concept belongs to under the routing test (CT-17; DEC-0129).

    * ``value-per-instant`` — a CT-16 indicator: a value at every evaluation instant.
    * ``discrete-object`` — a CT-17 structure object: a discrete object with a birth and a
      lifetime.
    """

    VALUE_PER_INSTANT = "value-per-instant"
    DISCRETE_OBJECT = "discrete-object"


def route(
    *, value_per_evaluation_instant: object, discrete_with_birth_and_lifetime: object
) -> Result[RoutingKind]:
    """Classify a concept as CT-16 or CT-17, returning value-or-refusal (CT-17; DEC-0129).

    ``value_per_evaluation_instant`` is whether the concept is a value at every evaluation
    instant (CT-16); ``discrete_with_birth_and_lifetime`` is whether it is a discrete object
    with a birth and a lifetime (CT-17). Exactly one must hold: a concept that is **both** must
    declare which it is (an ``invalid input`` refusal until it does), and a concept that is
    **neither** is not a governed CT-16/CT-17 concept at all.
    """
    if not isinstance(value_per_evaluation_instant, bool):
        return _invalid(
            "value_per_evaluation_instant",
            "the CT-16 property is a bool",
            given=repr(value_per_evaluation_instant),
        )
    if not isinstance(discrete_with_birth_and_lifetime, bool):
        return _invalid(
            "discrete_with_birth_and_lifetime",
            "the CT-17 property is a bool",
            given=repr(discrete_with_birth_and_lifetime),
        )
    if value_per_evaluation_instant and discrete_with_birth_and_lifetime:
        return _invalid(
            "routing",
            "a concept expressible both as a value per evaluation instant (CT-16) and as a "
            "discrete object with a lifetime (CT-17) must declare which it is",
        )
    if not value_per_evaluation_instant and not discrete_with_birth_and_lifetime:
        return _invalid(
            "routing",
            "a concept that is neither a value per evaluation instant (CT-16) nor a discrete "
            "object with a birth and a lifetime (CT-17) is not a governed structure concept",
        )
    if value_per_evaluation_instant:
        return Ok(RoutingKind.VALUE_PER_INSTANT)
    return Ok(RoutingKind.DISCRETE_OBJECT)


@runtime_checkable
class IndicatorResultInput(Protocol):
    """The declared-input seam for a CT-16 indicator result a family consumes (FM-6; DEC-0126).

    A family consuming an indicator does not re-implement its arithmetic; it consumes the
    indicator's **result** through this structural seam, whose ``result_fingerprint`` is the
    indicator result's ``fp1``. The composition root supplies it; declaring the input creates no
    package dependency edge. Any object exposing this fingerprint is a valid indicator input.
    """

    @property
    def result_fingerprint(self) -> Fingerprint:  # pragma: no cover - protocol seam
        """The consumed indicator result's ``fp1`` fingerprint."""
        ...


def consume_indicator_input(indicator_input: object) -> Result[Fingerprint]:
    """Consume an indicator result as a declared input, returning its fingerprint to record
    (FM-6; DEC-0126, DEC-0127).

    Returns the indicator result's ``fp1`` — the value the caller adds to the structure object's
    input fingerprints so the dependency is recorded in lineage and the indicator's arithmetic
    is **never** re-implemented inline (the FM-6 contract defect). A missing or malformed
    fingerprint is an ``invalid input`` refusal. This function computes no indicator value; it
    only records that one was consumed.
    """
    if not isinstance(indicator_input, IndicatorResultInput):
        return _invalid(
            "indicator_input",
            "a family consumes an indicator through the IndicatorResultInput seam (a "
            "result_fingerprint), never by re-implementing its arithmetic (FM-6)",
            given=repr(indicator_input),
        )
    resolved = _as_fingerprint(indicator_input.result_fingerprint)
    if resolved is None:
        return _invalid(
            "indicator_input",
            "the indicator input's result_fingerprint is an fp1 fingerprint",
            given=repr(indicator_input.result_fingerprint),
        )
    return Ok(resolved)
