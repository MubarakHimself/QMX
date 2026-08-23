"""CT-17 — the first governed family: the swing-point family (COMP-QMF-STRUCTURE).

Story 9.1 minted the object, 9.2 pinned the append-only lifecycle, 9.3 made evidence
class and knowledge time first-class. Story 9.4 ships the **first governed family** from
the seed candidates (``registry:structure_seed_family_candidates``): a swing-point family,
proving the whole CT-17 lifecycle end-to-end on a real, unprivileged family (DEC-0129,
DEC-0133).

**A swing point is a local price extreme (DEC-0129).** :class:`SwingPointFamily` scans a
declared sequence of :class:`PriceObservation` inputs and mints a
:class:`~qmf.structure.StructureObject` (geometry ``point``) at each **pivot** — a bar
whose high strictly exceeds every high in its ``left``/``right`` window (a swing high) or
whose low strictly undercuts every low in its window (a swing low). The vocabulary is
school-neutral — "swing point", "pivot", "extreme" — and no trading-school name appears in
any rule or parameter (FM-9, DEC-0132). The seed candidate holds **no privilege** over an
operator-authored family: it is a plain :class:`~qmf.structure.StructureFamily` built with
the same public factories any peer uses, admitted through the same
:func:`~qmf.structure.admit_to_governed_library` gate under identical law (DEC-0133).

**The confirmation rule is precise — "confirmed the moment X happens" with X knowable at
that instant (FM-2, DEC-0129).** A swing point is confirmed the moment a later bar **closes
beyond the pivot bar's opposite extreme** — below the pivot bar's low for a swing high,
above the pivot bar's high for a swing low. X is a bar close, knowable exactly at that bar's
instant, so the family is admissible to the governed library.
:meth:`SwingPointFamily.confirmation_for` locates that instant and returns the
:class:`~qmf.structure.ConfirmationRecord`, or ``Ok(None)`` when no later bar has confirmed
it within the family's declared confirmation-delay bound.

**Look-ahead safety is by construction (FM-1, DEC-0129, DEC-0121).** A pivot at bar ``i`` is
not derivable until its ``right``-window bars exist, so its ``observed_at`` is the instant of
bar ``i + right`` — never earlier. The anchor span is frozen at the pivot bar (permitted to
precede ``observed_at``), the consumed-input evidence times are the whole window, and the
in-component emission invariant (Story 9.1) rejects any object whose ``observed_at`` would
precede the newest consumed bar. A repainted or future-peeking swing can never be minted.

**Source/bar observations are declared inputs (FM-6, DEC-0126).** The family consumes
:class:`PriceObservation` values the composition root supplies — a projection of CT-10 source
observations or a CT-16 bar series — through the declared-input seam, never by defining the
CT-16 series vocabulary (Bar/BarSpec live in qmf-core, and this package imports only
qmf-core). A family needing an indicator would likewise consume it as a declared input
through the composition law, never re-implement its arithmetic inline (see
:mod:`qmf.structure.routing`).

Default-deny holds: this module imports **only** ``qmf.core`` and the sibling
``qmf.structure`` value types. Every ``fp1`` fingerprint is computed in qmf-core; the family
returns fingerprintable content, never stamped records. Public value types are frozen
dataclasses, the observation seam is a ``typing.Protocol``, and every operation succeeds or
RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain failure is never raised across the
boundary (DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast, runtime_checkable

from qmf.core import (
    EvidenceClass,
    ExactRational,
    Instant,
    Ok,
    Price,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    UnitKind,
    is_refusal,
)
from qmf.structure.lifecycle import ConfirmationRecord
from qmf.structure.objects import (
    AnchorSpan,
    ConfirmationRule,
    DeclaredFamily,
    FamilyIdentity,
    StructureObject,
)

__all__ = [
    "SWING_POINT_CONFIRMATION_RULE",
    "HighLowObservation",
    "PriceObservation",
    "SwingKind",
    "SwingPoint",
    "SwingPointFamily",
]


# The declared confirmation rule of the swing-point family — precise, "confirmed the moment
# X happens" with X knowable at that instant (DEC-0129, DEC-0132). It names no trading school
# (FM-9): a "pivot bar" and a "bar close" are mechanical, school-neutral terms.
SWING_POINT_CONFIRMATION_RULE: str = (
    "confirmed the moment a later bar closes beyond the pivot bar's opposite extreme "
    "(below the pivot bar's low for a swing high, above the pivot bar's high for a swing low)"
)


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a family operation returns (CT-04; DEC-0109).

    ``retryability`` is ``no`` — a malformed observation, a non-monotonic input series, or a
    bad window size is a caller/wiring mistake, not a transient condition — and ``context``
    always names the offending ``field`` and a human-legible ``reason`` (returned, never
    raised).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _positive_int(value: object) -> int | None:
    """Return ``value`` as a genuine positive ``int`` (a ``bool`` is rejected), else ``None``."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _ratio(numerator: int) -> ExactRational:
    """A dimensionless exact-rational integer parameter (window size or a 0/1 flag).

    Window sizes and the swing-direction flag are exact rationals, never binary floats, so
    the money-path float ban holds by construction and the value fingerprints canonically.
    """
    built = ExactRational.try_create(numerator, 1, UnitKind.DIMENSIONLESS_RATIO)
    # The numerator is a plain int and the denominator is 1, so construction never refuses;
    # unwrapping here keeps the caller's parameter map free of Result plumbing.
    if is_refusal(built):  # pragma: no cover - integer/1 is always a valid exact rational
        raise AssertionError("an integer-over-one exact rational must construct")
    return built.value


# --- the declared-input seam: a source/bar observation ----------------------


@runtime_checkable
class PriceObservation(Protocol):
    """The ``typing.Protocol`` seam a source/bar observation the family consumes exposes
    (CT-17, CT-10, CT-16; DEC-0126, DEC-0120).

    A family consumes source/bar observations as **declared inputs** through this structural
    seam — the composition root supplies them from a CT-10 source observation stream or a
    CT-16 bar series, and declaring an input creates no package dependency edge. The seam is
    deliberately minimal (the instant, the high/low extent, and the close) and is **not** the
    CT-16 series vocabulary: qmf-structure never defines Bar or BarSpec (those are qmf-core
    nouns). :class:`HighLowObservation` is the reference implementation, but any object
    satisfying this protocol is a valid input.
    """

    @property
    def at(self) -> Instant:  # pragma: no cover - protocol seam
        """The observation's instant (int64 UTC ns) — known-at, never event time."""
        ...

    @property
    def high(self) -> Price:  # pragma: no cover - protocol seam
        """The observation's high (exact Price)."""
        ...

    @property
    def low(self) -> Price:  # pragma: no cover - protocol seam
        """The observation's low (exact Price)."""
        ...

    @property
    def close(self) -> Price:  # pragma: no cover - protocol seam
        """The observation's close (exact Price) — the confirmation reference."""
        ...


@dataclass(frozen=True, slots=True)
class HighLowObservation:
    """A reference :class:`PriceObservation`: an instant with exact high/low/close prices
    (CT-17; DEC-0129, DEC-0105).

    All three prices are of one instrument and satisfy ``low <= close <= high`` — a bar's
    close sits within its own range. A binary float never reaches here: a
    :class:`~qmf.core.Price` is a scaled integer.
    """

    at: Instant
    high: Price
    low: Price
    close: Price

    @classmethod
    def try_create(
        cls, at: object, high: object, low: object, close: object
    ) -> Result[HighLowObservation]:
        """Validate and build a :class:`HighLowObservation`, returning value-or-refusal."""
        if not isinstance(at, Instant):
            return _invalid("at", "an observation instant is an Instant", given=repr(at))
        if not isinstance(high, Price):
            return _invalid("high", "an observation high is a Price", given=repr(high))
        if not isinstance(low, Price):
            return _invalid("low", "an observation low is a Price", given=repr(low))
        if not isinstance(close, Price):
            return _invalid("close", "an observation close is a Price", given=repr(close))
        if not (low.instrument == high.instrument == close.instrument):
            return _invalid(
                "close",
                "the observation's high, low, and close are of one instrument",
                high=repr(high.instrument),
                low=repr(low.instrument),
                close=repr(close.instrument),
            )
        low_f, high_f, close_f = low.as_fraction(), high.as_fraction(), close.as_fraction()
        if low_f > high_f:
            return _invalid(
                "low", "an observation requires low <= high", low=str(low_f), high=str(high_f)
            )
        if not (low_f <= close_f <= high_f):
            return _invalid(
                "close",
                "an observation's close sits within its own range: low <= close <= high",
                low=str(low_f),
                close=str(close_f),
                high=str(high_f),
            )
        return Ok(cls(at=at, high=high, low=low, close=close))


def _as_instant(value: object) -> Instant | None:
    """Return ``value`` if it is an :class:`~qmf.core.Instant`, else ``None`` (the ``object``
    parameter keeps the isinstance guard real for a duck-typed Protocol member)."""
    return value if isinstance(value, Instant) else None


def _as_price(value: object) -> Price | None:
    """Return ``value`` if it is a :class:`~qmf.core.Price`, else ``None``."""
    return value if isinstance(value, Price) else None


def _observation_prices(obs: PriceObservation) -> tuple[Instant, Price, Price, Price] | None:
    """Read an observation's fields as concrete types, or ``None`` if any is wrong.

    A ``runtime_checkable`` Protocol's isinstance proves the members EXIST but never their
    types, so a structurally-valid :class:`PriceObservation` may still hand back wrong types —
    routing each field through an ``object``-typed helper keeps the type checks real, not
    redundant.
    """
    at = _as_instant(obs.at)
    high = _as_price(obs.high)
    low = _as_price(obs.low)
    close = _as_price(obs.close)
    if at is None or high is None or low is None or close is None:
        return None
    return at, high, low, close


def _coerce_observations(value: object) -> tuple[PriceObservation, ...] | TypedRefusal:
    """Resolve the input series to a tuple of validated observations, or refuse.

    A bare string or bytes is refused — it is not a sequence of observations — and every
    element must be a :class:`PriceObservation` exposing typed fields. An empty series is
    legal (no pivots are found).
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "observations",
            "the input series is a sequence of PriceObservations (a bare string is not one)",
            given=repr(value),
        )
    resolved: list[PriceObservation] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, PriceObservation) or _observation_prices(item) is None:
            return _invalid(
                "observations",
                "each element is a PriceObservation with an Instant instant and exact "
                "high/low/close Prices",
                index=index,
                given=repr(item),
            )
        resolved.append(item)
    return tuple(resolved)


# --- the swing point --------------------------------------------------------


class SwingKind(StrEnum):
    """The direction of a swing point: a local high or a local low (DEC-0129)."""

    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class SwingPoint:
    """A detected swing point: its direction, its minted object, and its break level (CT-17;
    DEC-0129).

    ``kind`` is the swing direction; ``object`` is the minted, unconfirmed
    :class:`~qmf.structure.StructureObject` (geometry ``point``); and ``break_level`` is the
    exact price a later bar must close beyond to confirm it — the pivot bar's low for a swing
    high, its high for a swing low. It is fingerprintable content the family returns, never a
    stamped record.
    """

    kind: SwingKind
    object: StructureObject
    break_level: Price


@dataclass(frozen=True, slots=True)
class SwingPointFamily:
    """The first governed family: a swing-point family under the CT-17 lifecycle law (CT-17;
    DEC-0129, DEC-0133).

    A :class:`~qmf.structure.StructureFamily` (it exposes ``identity`` and
    ``confirmation_rule``) built with the same public factories any operator-authored peer
    uses — it holds **no privilege**. ``left`` and ``right`` are the pivot window sizes (bars
    required on each side of an extreme); they ride into every minted object's exact-rational
    parameters. Use :meth:`create` to build one; :meth:`detect` mints the pivots and
    :meth:`confirmation_for` locates a pivot's confirmation instant.
    """

    identity: FamilyIdentity
    confirmation_rule: ConfirmationRule
    left: int
    right: int

    @classmethod
    def create(
        cls, *, left: object, right: object, confirmation_delay_bound: object
    ) -> Result[SwingPointFamily]:
        """Build the swing-point family, returning value-or-refusal.

        ``left`` and ``right`` are strictly-positive window sizes; ``confirmation_delay_bound``
        is the family's declared confirmation-delay bound (a non-negative integer count of
        observations at its BarSpec, or ``None`` for the unbounded exclusion). The declared
        confirmation rule is :data:`SWING_POINT_CONFIRMATION_RULE` — precise and school-neutral.
        """
        left_n = _positive_int(left)
        if left_n is None:
            return _invalid("left", "the left window is a positive integer", given=repr(left))
        right_n = _positive_int(right)
        if right_n is None:
            return _invalid("right", "the right window is a positive integer", given=repr(right))
        identity = FamilyIdentity.try_create("swing-point", 1, "point")
        if is_refusal(identity):  # pragma: no cover - fixed valid identity parts
            return identity
        rule = ConfirmationRule.try_create(
            SWING_POINT_CONFIRMATION_RULE,
            confirmation_delay_bound=confirmation_delay_bound,
        )
        if is_refusal(rule):
            return rule
        built = DeclaredFamily.try_create(identity.value, rule.value)
        if is_refusal(built):  # pragma: no cover - identity/rule are valid by construction
            return built
        return Ok(
            cls(
                identity=built.value.identity,
                confirmation_rule=built.value.confirmation_rule,
                left=left_n,
                right=right_n,
            )
        )

    def _parameters(self, *, swing_high: bool) -> dict[str, ExactRational]:
        """The exact-rational parameter map for a minted pivot object.

        ``left`` / ``right`` are the window sizes and ``swing_high`` is a 0/1 direction flag —
        all exact rationals, so the object self-describes its configuration and direction and
        fingerprints canonically. No trading-school name appears (FM-9).
        """
        return {
            "left": _ratio(self.left),
            "right": _ratio(self.right),
            "swing_high": _ratio(1 if swing_high else 0),
        }

    def _mint_pivot(
        self, window: Sequence[PriceObservation], *, center: int, swing_high: bool
    ) -> Result[StructureObject]:
        """Mint the pivot object at ``window[center]``, observed at the window's last bar.

        The anchor is a point frozen at the pivot bar (``start == end`` at its instant,
        ``low == high`` at its extreme price); ``observed_at`` is the last window bar's instant
        (the earliest instant the pivot was derivable); and the consumed-input evidence times
        are the whole window, so the in-component emission invariant proves look-ahead safety.
        """
        pivot = window[center]
        level = pivot.high if swing_high else pivot.low
        anchor = AnchorSpan.try_create(pivot.at, pivot.at, level, level)
        if is_refusal(anchor):  # pragma: no cover - a point anchor at one price is always valid
            return anchor
        observed_at = window[-1].at
        return StructureObject.try_create(
            DeclaredFamily(identity=self.identity, confirmation_rule=self.confirmation_rule),
            self._parameters(swing_high=swing_high),
            anchor.value,
            observed_at,
            EvidenceClass.UNCONFIRMED,
            consumed_input_times=[bar.at for bar in window],
        )

    def detect(self, observations: object) -> Result[tuple[SwingPoint, ...]]:
        """Detect swing points over a declared observation series, returning value-or-refusal.

        Scans every bar with a full ``left``/``right`` window and mints an **unconfirmed**
        pivot object where a bar's high strictly exceeds every high in its window (a swing
        high) and/or where its low strictly undercuts every low (a swing low). A single outside
        bar can be both. Objects are minted at observation and are look-ahead-safe by
        construction. The input series must be strictly increasing in time and of one
        instrument; an out-of-order or mixed-instrument series is an ``invalid input`` refusal.
        """
        resolved = _coerce_observations(observations)
        if isinstance(resolved, TypedRefusal):
            return resolved
        bars = resolved
        count = len(bars)
        for index in range(1, count):
            if bars[index].at.value_ns <= bars[index - 1].at.value_ns:
                return _invalid(
                    "observations",
                    "the observation series is strictly increasing in time",
                    index=index,
                    previous=bars[index - 1].at.value_ns,
                    current=bars[index].at.value_ns,
                )
        instrument = None if count == 0 else bars[0].high.instrument
        for index in range(1, count):
            if bars[index].high.instrument != instrument:
                return _invalid(
                    "observations",
                    "a swing-point family scans one instrument; the series is mixed",
                    index=index,
                )

        found: list[SwingPoint] = []
        for center in range(self.left, count - self.right):
            window = bars[center - self.left : center + self.right + 1]
            local = self.left  # the pivot's index within the window
            pivot = window[local]
            is_high = all(
                pivot.high.as_fraction() > bar.high.as_fraction()
                for offset, bar in enumerate(window)
                if offset != local
            )
            is_low = all(
                pivot.low.as_fraction() < bar.low.as_fraction()
                for offset, bar in enumerate(window)
                if offset != local
            )
            for swing_high, active in ((True, is_high), (False, is_low)):
                if not active:
                    continue
                minted = self._mint_pivot(window, center=local, swing_high=swing_high)
                if is_refusal(minted):  # pragma: no cover - a valid pivot always mints
                    return minted
                found.append(
                    SwingPoint(
                        kind=SwingKind.HIGH if swing_high else SwingKind.LOW,
                        object=minted.value,
                        break_level=pivot.low if swing_high else pivot.high,
                    )
                )
        return Ok(tuple(found))

    def confirmation_for(
        self, pivot: object, later_observations: object
    ) -> Result[ConfirmationRecord | None]:
        """Locate a pivot's confirmation instant, returning the record, ``Ok(None)``, or a
        refusal (FM-2; DEC-0129).

        Scans ``later_observations`` (only bars strictly after the pivot's ``observed_at``) in
        order and returns a :class:`~qmf.structure.ConfirmationRecord` at the **first** bar
        that closes beyond the break level — below it for a swing high, above it for a swing
        low. That instant is exactly the moment the declared confirmation rule fires (X is a
        bar close, knowable then). ``Ok(None)`` means no bar has confirmed the pivot within the
        family's declared confirmation-delay bound; an unbounded family scans the whole series.
        """
        if not isinstance(pivot, SwingPoint):
            return _invalid("pivot", "confirmation is for a detected SwingPoint", given=repr(pivot))
        resolved = _coerce_observations(later_observations)
        if isinstance(resolved, TypedRefusal):
            return resolved
        pivot_fp = pivot.object.content_fingerprint()
        if is_refusal(pivot_fp):  # pragma: no cover - a minted object's identity is canonical
            return pivot_fp
        bound = self.confirmation_rule.confirmation_delay_bound
        break_level = pivot.break_level.as_fraction()
        seen = 0
        for bar in resolved:
            if bar.at.value_ns <= pivot.object.observed_at.value_ns:
                continue  # a confirming bar is strictly after the pivot was observed
            seen += 1
            if bound is not None and seen > bound:
                break  # past the declared confirmation-delay bound: not confirmed
            close = bar.close.as_fraction()
            fired = close < break_level if pivot.kind is SwingKind.HIGH else close > break_level
            if fired:
                record = ConfirmationRecord.try_create(pivot_fp.value, bar.at)
                if is_refusal(record):  # pragma: no cover - a valid fp/instant always builds
                    return record
                confirmed: ConfirmationRecord | None = record.value
                return Ok(confirmed)
        none_found: ConfirmationRecord | None = None
        return Ok(none_found)
