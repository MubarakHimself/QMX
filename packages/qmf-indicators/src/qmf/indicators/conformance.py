"""CT-16 — the conformance register bound to the concept-walk list (COMP-QMF-INDICATORS;
Story 7.5).

The CT-16 contract carries a **conformance register**: the concept-walk test list the
contract must keep **expressible** as governed configurations (CT-16 ``conformance_register``;
DEC-0130, DEC-0102). This module lands that register as machine-readable contract surface
plus the harness that, at tier 2, proves every concept is expressible — never inventing a
concept the contract does not name, never dropping one it does.

The register is the ten concepts the story and the contract enumerate, in order
(:data:`CONCEPT_WALK_REGISTER`):

1. multi-instrument input sets;
2. multi-BarSpec input sets;
3. derived-series chaining;
4. non-time bar kinds;
5. calendar-scoped windows;
6. calendar-anchored sampling;
7. projected outputs under knowable-at;
8. batch-only statistical methods;
9. price-valued outputs re-entering the money path via the named boundary;
10. delta-typed price differences.

Each concept carries a **structural predicate** over a :class:`~qmf.indicators.ConfiguredIndicator`:
a governed configuration *expresses* the concept when it genuinely exhibits that structural
feature (two distinct instruments; a derived input carrying an upstream fingerprint; a
non-time BarSpec kind; a calendar-scoped time bound; a session BarSpec anchored to a
declared calendar; a projected output offset; a batch-only mode set; an exact-price output;
a price-difference formula with an exact-price output). :func:`check_expressible` runs the
predicate **and** computes the configuration's ``fp1`` — expressible means both hold.
:func:`run_conformance` runs a set of expressions, reports each concept's check, and
reports any register concept left uncovered, so the tier-2 suite fails closed on a missing
or non-expressible concept.

The concept-walk **configurations** are supplied by the caller (the tier-2 test builds them
from the ``qmf-core`` identity nouns); this module ships the register and the verifier, not
constructed sample data. Default-deny holds: it imports **only** ``qmf.core`` and this
package's own modules; public value types are frozen dataclasses and every operation
succeeds or RETURNS a CT-04 typed refusal (DEC-0101, DEC-0109, DEC-0120).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    canonical_bytes,
    is_ok,
    is_refusal,
)
from qmf.indicators.configured_indicator import (
    ChannelKind,
    ConfiguredIndicator,
    SeriesInput,
    SupportedMode,
    SupportsFp1Identity,
)

__all__ = [
    "CONCEPT_WALK_REGISTER",
    "ConceptCheck",
    "ConceptExpression",
    "ConceptWalk",
    "ConformanceReport",
    "check_expressible",
    "run_conformance",
]

# The non-time BarSpec kinds — registry:barspec_kinds minus the one time kind. A
# configuration expresses "non-time bar kinds" when an input declares one of these
# (DEC-0126, DEC-0130).
_NON_TIME_BAR_KINDS: Final[frozenset[str]] = frozenset(
    {"tick-count", "volume-threshold", "notional-threshold", "price-brick", "range", "session"}
)

# The BarSpec kind that samples anchored to the market-hours calendar — session bars reset
# and sample at session boundaries (calendar-anchored sampling) (DEC-0126).
_SESSION_BAR_KIND: Final[str] = "session"

# Formula ids that produce a price *difference* (a delta), not a price *level*. MOM is a
# price difference and MACD is a difference of EMAs; both carry a delta-typed price
# difference through an exact-price output. Distinguishes concept 10 from the price-level
# re-entry of concept 9 (DEC-0126, DEC-0127).
_DELTA_FORMULAS: Final[frozenset[str]] = frozenset({"mom", "macd"})


class ConceptWalk(StrEnum):
    """One concept the CT-16 conformance register must keep expressible (CT-16; DEC-0130).

    The names mirror the contract's ``conformance_register`` list verbatim; the register
    order (:data:`CONCEPT_WALK_REGISTER`) is the order the contract and the story enumerate.
    """

    MULTI_INSTRUMENT = "multi-instrument-input-sets"
    MULTI_BARSPEC = "multi-barspec-input-sets"
    DERIVED_SERIES_CHAINING = "derived-series-chaining"
    NON_TIME_BAR_KINDS = "non-time-bar-kinds"
    CALENDAR_SCOPED_WINDOWS = "calendar-scoped-windows"
    CALENDAR_ANCHORED_SAMPLING = "calendar-anchored-sampling"
    PROJECTED_OUTPUTS_KNOWABLE_AT = "projected-outputs-under-knowable-at"
    BATCH_ONLY_STATISTICAL = "batch-only-statistical-methods"
    PRICE_VALUED_REENTRY = "price-valued-outputs-reentering-the-money-path"
    DELTA_TYPED_PRICE_DIFFERENCES = "delta-typed-price-differences"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a conformance operation returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )


# --- structural predicates --------------------------------------------------


def _canonical_key(content: object) -> bytes:
    """A stable comparison key for an identity fragment, via the one canonical serializer."""
    serialized = canonical_bytes(content)
    if is_ok(serialized):
        return serialized.value
    return repr(content).encode("utf-8")


def _instrument_sources(configuration: ConfiguredIndicator) -> tuple[Instrument, ...]:
    """The instrument-typed sources of a configuration's inputs (source-id tokens excluded)."""
    return tuple(
        series_input.source
        for series_input in configuration.inputs
        if isinstance(series_input.source, Instrument)
    )


def _bar_spec_kind(series_input: SeriesInput) -> str | None:
    """The declared BarSpec kind of an input, or ``None`` when referenced by fingerprint."""
    bar_spec = series_input.bar_spec
    if isinstance(bar_spec, Mapping):
        kind = bar_spec.get("kind")
        return kind if isinstance(kind, str) else None
    if isinstance(bar_spec, SupportsFp1Identity):
        kind = bar_spec.fp1_identity().get("kind")
        return kind if isinstance(kind, str) else None
    return None


def _expresses_multi_instrument(configuration: ConfiguredIndicator) -> bool:
    instruments = _instrument_sources(configuration)
    return len({(source.venue.value, source.symbol) for source in instruments}) >= 2


def _expresses_multi_barspec(configuration: ConfiguredIndicator) -> bool:
    keys = {
        _canonical_key(series_input.fp1_identity()["bar_spec"])
        for series_input in configuration.inputs
    }
    return len(keys) >= 2


def _expresses_derived_series_chaining(configuration: ConfiguredIndicator) -> bool:
    return any(
        series_input.upstream_fingerprint is not None for series_input in configuration.inputs
    )


def _expresses_non_time_bar_kinds(configuration: ConfiguredIndicator) -> bool:
    return any(
        _bar_spec_kind(series_input) in _NON_TIME_BAR_KINDS for series_input in configuration.inputs
    )


def _expresses_calendar_scoped_windows(configuration: ConfiguredIndicator) -> bool:
    return (
        configuration.warm_up_time_bound is not None
        and len(configuration.calendar_requirements) >= 1
    )


def _expresses_calendar_anchored_sampling(configuration: ConfiguredIndicator) -> bool:
    has_session = any(
        _bar_spec_kind(series_input) == _SESSION_BAR_KIND for series_input in configuration.inputs
    )
    return has_session and len(configuration.calendar_requirements) >= 1


def _expresses_projected_outputs(configuration: ConfiguredIndicator) -> bool:
    return any(channel.index_offset != 0 for channel in configuration.output_schema)


def _expresses_batch_only_statistical(configuration: ConfiguredIndicator) -> bool:
    modes = set(configuration.supported_modes)
    return SupportedMode.BATCH in modes and SupportedMode.STREAMING not in modes


def _has_exact_price_output(configuration: ConfiguredIndicator) -> bool:
    return any(
        channel.channel_kind is ChannelKind.EXACT_PRICE for channel in configuration.output_schema
    )


def _expresses_price_valued_reentry(configuration: ConfiguredIndicator) -> bool:
    return _has_exact_price_output(configuration)


def _expresses_delta_typed_price_differences(configuration: ConfiguredIndicator) -> bool:
    return configuration.formula_id in _DELTA_FORMULAS and _has_exact_price_output(configuration)


# The register: each concept mapped to the structural predicate that recognizes it. The
# tuple order is the contract's enumeration order; the predicate map is the machine test.
CONCEPT_WALK_REGISTER: Final[tuple[ConceptWalk, ...]] = (
    ConceptWalk.MULTI_INSTRUMENT,
    ConceptWalk.MULTI_BARSPEC,
    ConceptWalk.DERIVED_SERIES_CHAINING,
    ConceptWalk.NON_TIME_BAR_KINDS,
    ConceptWalk.CALENDAR_SCOPED_WINDOWS,
    ConceptWalk.CALENDAR_ANCHORED_SAMPLING,
    ConceptWalk.PROJECTED_OUTPUTS_KNOWABLE_AT,
    ConceptWalk.BATCH_ONLY_STATISTICAL,
    ConceptWalk.PRICE_VALUED_REENTRY,
    ConceptWalk.DELTA_TYPED_PRICE_DIFFERENCES,
)

_PREDICATES: Final[Mapping[ConceptWalk, Callable[[ConfiguredIndicator], bool]]] = MappingProxyType(
    {
        ConceptWalk.MULTI_INSTRUMENT: _expresses_multi_instrument,
        ConceptWalk.MULTI_BARSPEC: _expresses_multi_barspec,
        ConceptWalk.DERIVED_SERIES_CHAINING: _expresses_derived_series_chaining,
        ConceptWalk.NON_TIME_BAR_KINDS: _expresses_non_time_bar_kinds,
        ConceptWalk.CALENDAR_SCOPED_WINDOWS: _expresses_calendar_scoped_windows,
        ConceptWalk.CALENDAR_ANCHORED_SAMPLING: _expresses_calendar_anchored_sampling,
        ConceptWalk.PROJECTED_OUTPUTS_KNOWABLE_AT: _expresses_projected_outputs,
        ConceptWalk.BATCH_ONLY_STATISTICAL: _expresses_batch_only_statistical,
        ConceptWalk.PRICE_VALUED_REENTRY: _expresses_price_valued_reentry,
        ConceptWalk.DELTA_TYPED_PRICE_DIFFERENCES: _expresses_delta_typed_price_differences,
    }
)


# --- expression + check value types -----------------------------------------


@dataclass(frozen=True, slots=True)
class ConceptExpression:
    """One register concept paired with a governed configuration claimed to express it."""

    concept: ConceptWalk
    configuration: ConfiguredIndicator


@dataclass(frozen=True, slots=True)
class ConceptCheck:
    """The result of checking one concept against its claimed configuration (CT-16; DEC-0130).

    ``expressible`` is true only when the configuration structurally exhibits the concept
    **and** its ``fp1`` computes; ``fingerprint`` is that ``fp1`` string when so, else
    ``None``; ``defect`` names why it failed when not.
    """

    concept: ConceptWalk
    expressible: bool
    fingerprint: str | None
    defect: str | None


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    """The tier-2 conformance report over a set of concept expressions (CT-16; DEC-0130).

    ``checks`` is one :class:`ConceptCheck` per supplied expression; ``missing`` is the
    register concepts no expression covered; ``passed`` is true only when every register
    concept is covered and every check is expressible.
    """

    checks: tuple[ConceptCheck, ...]
    missing: tuple[ConceptWalk, ...]
    passed: bool


def check_expressible(concept: object, configuration: object) -> Result[ConceptCheck]:
    """Check that ``configuration`` expresses ``concept`` (CT-16 conformance; DEC-0130).

    Runs the concept's structural predicate and computes the configuration's ``fp1``. The
    concept is *expressible* only when the predicate holds and the fingerprint computes.
    Returns a :class:`ConceptCheck` (expressible or with a defect), or an ``invalid input``
    refusal for a concept outside the register or a non-configuration argument.
    """
    if not isinstance(concept, ConceptWalk):
        return _invalid(
            "concept",
            "the concept is a member of the CT-16 conformance register",
            given=repr(concept),
            register=[member.value for member in CONCEPT_WALK_REGISTER],
        )
    if not isinstance(configuration, ConfiguredIndicator):
        return _invalid(
            "configuration", "a ConfiguredIndicator is required", given=repr(configuration)
        )
    predicate = _PREDICATES[concept]
    if not predicate(configuration):
        return Ok(
            ConceptCheck(
                concept=concept,
                expressible=False,
                fingerprint=None,
                defect="the configuration does not structurally express this concept",
            )
        )
    computed = configuration.fp1()
    if is_refusal(computed):  # pragma: no cover - a valid configuration always fingerprints
        return Ok(
            ConceptCheck(
                concept=concept,
                expressible=False,
                fingerprint=None,
                defect="the configuration's fp1 identity did not compute",
            )
        )
    return Ok(
        ConceptCheck(
            concept=concept, expressible=True, fingerprint=computed.value.value, defect=None
        )
    )


def run_conformance(expressions: object) -> Result[ConformanceReport]:
    """Run the conformance suite over a set of concept expressions (CT-16; DEC-0130).

    Each expression is checked with :func:`check_expressible`; the report records every
    check, the register concepts no expression covered, and whether the suite passed (every
    register concept covered and every check expressible). Returns an ``invalid input``
    refusal for a non-sequence of expressions or a non-:class:`ConceptExpression` member.
    """
    if isinstance(expressions, (str, bytes)) or not hasattr(expressions, "__iter__"):
        return _invalid(
            "expressions",
            "expressions are an iterable of ConceptExpression values",
            given=repr(expressions),
        )
    checks: list[ConceptCheck] = []
    covered: set[ConceptWalk] = set()
    for index, expression in enumerate(cast("Iterable[object]", expressions)):
        if not isinstance(expression, ConceptExpression):
            return _invalid(
                "expressions",
                "each expression is a ConceptExpression",
                index=index,
                given=repr(expression),
            )
        checked = check_expressible(expression.concept, expression.configuration)
        if is_refusal(checked):  # pragma: no cover - members are validated above
            return checked
        checks.append(checked.value)
        covered.add(expression.concept)
    missing = tuple(concept for concept in CONCEPT_WALK_REGISTER if concept not in covered)
    passed = not missing and all(check.expressible for check in checks)
    return Ok(ConformanceReport(checks=tuple(checks), missing=missing, passed=passed))
