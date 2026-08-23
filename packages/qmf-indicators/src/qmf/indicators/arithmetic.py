"""Canonical arithmetic ownership and mandatory wrapping (CT-16; DEC-0127, DEC-0134).

Canonical arithmetic binds every governed producer. Where the pinned reference
(``registry:canonical_indicator_reference``) implements a formula, **wrapping it is
mandatory and it is canonical** — re-implementing arithmetic the reference already
owns is a contract defect that fails conformance (FM-5). Where the reference does not
implement a formula (volume-weighted, session-anchored, or QMX-original formulas),
**this package's own implementation is the canonical arithmetic** under the identical
upgrade gate. This module lands that ownership model plus the package-neutral seam a
governed producer resolves canonical arithmetic through (Story 7.2).

The public surface stays package-neutral: no TA-Lib or other vendor object appears in
any signature or output. A governed producer resolves the canonical owner of a formula
and, for a reference-owned formula, obtains the verified reference through
:func:`resolve_canonical_arithmetic`; if the reference is unavailable the seam returns
the ``unavailable dependency`` refusal the import assertion produced, so a wrapper never
silently falls back to re-implemented arithmetic (FM-2, FM-5). The concrete wrapper set
and the two-mode compute protocol arrive in later stories; this module owns the
ownership registry, the resolution seam, and the conformance checks that keep every
formula to exactly one canonical owner.

Default-deny holds: this module imports only ``qmf.core`` and this package's own value
types. Public value types are frozen dataclasses; every operation succeeds or RETURNS a
CT-04 refusal (DEC-0109, DEC-0101).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal
from qmf.indicators import _reference
from qmf.indicators.configured_indicator import ArithmeticReference

__all__ = [
    "CANONICAL_OWNERS",
    "FormulaOwner",
    "FormulaOwnership",
    "canonical_owner",
    "ownership_conformance_defects",
    "reference_grounded_defects",
    "reference_status",
    "resolve_canonical_arithmetic",
]


class FormulaOwnership(StrEnum):
    """Who owns a formula's canonical arithmetic (CT-16; DEC-0127).

    ``REFERENCE`` — the pinned reference implements the formula, so wrapping it is
    mandatory and it is canonical. ``PACKAGE`` — the reference does not implement the
    formula (volume-weighted, session-anchored, QMX-original), so this package's own
    implementation is the canonical arithmetic under the identical upgrade gate.
    """

    REFERENCE = "reference"
    PACKAGE = "package"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal an ownership lookup returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class FormulaOwner:
    """The canonical owner of one formula's arithmetic (CT-16; DEC-0127).

    ``formula_id`` is the opaque, stable formula identity; ``ownership`` says who owns
    the canonical arithmetic; ``reference_function`` names the reference function a
    reference-owned formula wraps (the delegation target) and is ``None`` for a
    package-owned formula. A reference-owned owner that names no reference function, or
    a package-owned owner that names one (which would mean re-implementing a formula the
    reference owns), is a contract defect the conformance checks catch (FM-5).
    """

    formula_id: str
    ownership: FormulaOwnership
    reference_function: str | None = None


def _reference_owned(formula_id: str, reference_function: str) -> FormulaOwner:
    """A reference-owned canonical owner delegating to ``reference_function``."""
    return FormulaOwner(
        formula_id=formula_id,
        ownership=FormulaOwnership.REFERENCE,
        reference_function=reference_function,
    )


def _package_owned(formula_id: str) -> FormulaOwner:
    """A package-owned (QMX-original / reference-lacking) canonical owner."""
    return FormulaOwner(formula_id=formula_id, ownership=FormulaOwnership.PACKAGE)


# The canonical-arithmetic ownership registry (CT-16; DEC-0127, DEC-0134). Every formula
# a governed producer may resolve has exactly one canonical owner here. Reference-owned
# formulas name the TA-Lib function they wrap (wrapping mandatory); package-owned
# formulas name none (the reference lacks them, so this package is canonical). The set
# grows as the first wrapper set lands in later stories; the ownership law binds from
# birth.
CANONICAL_OWNERS: Final[Mapping[str, FormulaOwner]] = MappingProxyType(
    {
        # Reference-owned: TA-Lib implements the formula, so wrapping it is mandatory.
        "sma": _reference_owned("sma", "SMA"),
        "ema": _reference_owned("ema", "EMA"),
        "wma": _reference_owned("wma", "WMA"),
        "rsi": _reference_owned("rsi", "RSI"),
        "atr": _reference_owned("atr", "ATR"),
        "macd": _reference_owned("macd", "MACD"),
        "bbands": _reference_owned("bbands", "BBANDS"),
        "adx": _reference_owned("adx", "ADX"),
        "stoch": _reference_owned("stoch", "STOCH"),
        "obv": _reference_owned("obv", "OBV"),
        "mom": _reference_owned("mom", "MOM"),
        "roc": _reference_owned("roc", "ROC"),
        # Package-owned: the reference does not implement these, so this package's own
        # arithmetic is canonical under the identical upgrade gate (volume-weighted and
        # session-anchored formulas the reference has no function for).
        "vwap": _package_owned("vwap"),
        "session_anchored_vwap": _package_owned("session_anchored_vwap"),
        "session_range": _package_owned("session_range"),
    }
)


def reference_status() -> Result[ArithmeticReference]:
    """The cached import-time reference assertion — the verified identity or a refusal.

    Returns the package-neutral :class:`ArithmeticReference` when the pinned reference
    was resolved and its reference-configuration record asserted at import, or the
    ``unavailable dependency`` refusal the assertion produced. No TA-Lib object crosses
    this boundary (FM-2, FM-5).
    """
    return _reference.reference_verification


def canonical_owner(formula_id: object) -> Result[FormulaOwner]:
    """Resolve the canonical owner of ``formula_id``, or an ``invalid input`` refusal.

    An unknown formula id is refused (it has no declared canonical owner yet) rather
    than defaulted, so a governed producer can never compute uncanonical arithmetic by
    accident (DEC-0127).
    """
    if not isinstance(formula_id, str) or formula_id.strip() == "":
        return _invalid(
            "formula_id",
            "a formula id is a non-empty opaque token",
            given=repr(formula_id),
        )
    owner = CANONICAL_OWNERS.get(formula_id)
    if owner is None:
        return _invalid(
            "formula_id",
            "the formula id has no declared canonical owner; declare its ownership "
            "before a governed producer may compute it (DEC-0127)",
            given=formula_id,
            known=sorted(CANONICAL_OWNERS),
        )
    return Ok(owner)


def resolve_canonical_arithmetic(
    formula_id: object,
    reference: Result[ArithmeticReference] | None = None,
) -> Result[FormulaOwner]:
    """Resolve canonical arithmetic for a formula, enforcing mandatory wrapping.

    For a **reference-owned** formula, wrapping the reference is mandatory: the seam
    requires the verified reference and returns the ``unavailable dependency`` refusal
    when it is not available, so a wrapper never falls back to re-implemented arithmetic
    (FM-2, FM-5). For a **package-owned** formula, this package's own arithmetic is
    canonical and no reference is required. Returns the :class:`FormulaOwner` on success.

    ``reference`` is injected (defaulting to the composition-time import assertion via
    :func:`reference_status`), never read ambiently, so a caller resolves against an
    explicit reference status at its composition root.
    """
    resolved = canonical_owner(formula_id)
    if isinstance(resolved, TypedRefusal):
        return resolved
    owner = resolved.value
    if owner.ownership is FormulaOwnership.PACKAGE:
        return Ok(owner)
    status = reference if reference is not None else reference_status()
    if isinstance(status, TypedRefusal):
        return status
    return Ok(owner)


def ownership_conformance_defects(
    owners: Mapping[str, FormulaOwner] = CANONICAL_OWNERS,
) -> tuple[str, ...]:
    """Structural conformance over the ownership registry — the defects, or empty.

    A contract defect (FM-5), caught here rather than as a runtime refusal: a formula
    id that does not match its registry key; a reference-owned formula that names no
    reference function (nothing to wrap); a package-owned formula that names a reference
    function (re-implementing a formula the reference owns); a blank reference-function
    name. An empty result means the registry is conformant.
    """
    defects: list[str] = []
    for key, owner in owners.items():
        if owner.formula_id != key:
            defects.append(f"{key}: formula_id {owner.formula_id!r} does not match its key")
        if owner.ownership is FormulaOwnership.REFERENCE:
            if owner.reference_function is None:
                defects.append(
                    f"{key}: reference-owned formula names no reference function to wrap"
                )
            elif owner.reference_function.strip() == "":
                defects.append(f"{key}: reference-owned formula names a blank reference function")
        elif owner.reference_function is not None:
            defects.append(
                f"{key}: package-owned formula names reference function "
                f"{owner.reference_function!r} — re-implementing a formula the reference "
                f"owns is a contract defect (FM-5)"
            )
    return tuple(defects)


def reference_grounded_defects(
    owners: Mapping[str, FormulaOwner] = CANONICAL_OWNERS,
    reference: Result[ArithmeticReference] | None = None,
) -> Result[tuple[str, ...]]:
    """Reference-grounded conformance — verified against the live reference.

    When the reference is available, every reference-owned formula's named function must
    genuinely exist in the reference (a real wrap target), and no package-owned formula
    may collide with a reference function (which would mean the reference does implement
    it, so wrapping would be mandatory — FM-5). Returns the defects (empty when
    conformant), or the ``unavailable dependency`` refusal when the reference cannot be
    reached so the caller knows the grounded check did not run.

    ``reference`` is injected (defaulting to the import assertion via
    :func:`reference_status`), never read ambiently.
    """
    status = reference if reference is not None else reference_status()
    if isinstance(status, TypedRefusal):
        return status
    defects: list[str] = []
    for key, owner in owners.items():
        if owner.ownership is FormulaOwnership.REFERENCE:
            if owner.reference_function is None:
                continue
            if _reference.reference_function(owner.reference_function) is None:
                defects.append(
                    f"{key}: reference function {owner.reference_function!r} is not "
                    f"implemented by the reference (nothing to wrap)"
                )
        elif _reference.reference_function(key.upper()) is not None:
            defects.append(
                f"{key}: the reference implements {key.upper()!r}; a package-owned "
                f"formula must not re-implement a formula the reference owns (FM-5)"
            )
    return Ok(tuple(defects))
