"""Tier-1 tests for Story 7.2 — canonical arithmetic ownership and mandatory wrapping
(COMP-QMF-INDICATORS; CT-16; DEC-0127, DEC-0134).

These tests bind the story's acceptance criteria for wrapping:

* a formula the reference implements is reference-owned — wrapping it is mandatory and
  canonical, and re-implementing it is a contract defect that fails conformance (FM-5);
* a formula the reference does not implement (volume-weighted, session-anchored,
  QMX-original) is package-owned — this package's arithmetic is canonical; and
* the public surface stays package-neutral — no TA-Lib object appears in any signature
  or output, and failures are CT-04 refusals.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TypeVar

import qmf.indicators
from qmf.core import (
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.indicators import (
    CANONICAL_OWNERS,
    FormulaOwner,
    FormulaOwnership,
    canonical_owner,
    ownership_conformance_defects,
    reference_grounded_defects,
    reference_status,
    resolve_canonical_arithmetic,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


def _unavailable() -> TypedRefusal:
    """An injected unavailable-dependency reference status (never a faked install)."""
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={"field": "reference", "reason": "the pinned reference is not installed"},
    )


# --- AC3/AC4: ownership -----------------------------------------------------


def test_reference_owned_formula_names_its_wrap_target() -> None:
    owner = _unwrap(canonical_owner("sma"))
    assert owner.ownership is FormulaOwnership.REFERENCE
    assert owner.reference_function == "SMA"


def test_package_owned_formula_names_no_reference_function() -> None:
    # Volume-weighted / session-anchored formulas the reference does not implement.
    for formula_id in ("vwap", "session_anchored_vwap", "session_range"):
        owner = _unwrap(canonical_owner(formula_id))
        assert owner.ownership is FormulaOwnership.PACKAGE
        assert owner.reference_function is None


def test_unknown_formula_is_refused_not_defaulted() -> None:
    refusal = canonical_owner("no_such_formula")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "formula_id"


def test_blank_or_nonstring_formula_is_refused() -> None:
    assert is_refusal(canonical_owner("   "))
    assert is_refusal(canonical_owner(123))
    assert is_refusal(canonical_owner(None))


# --- AC3: mandatory wrapping ------------------------------------------------


def test_reference_owned_resolves_when_reference_available() -> None:
    # The reference installs on this machine, so a reference-owned formula resolves.
    owner = _unwrap(resolve_canonical_arithmetic("rsi"))
    assert owner.ownership is FormulaOwnership.REFERENCE
    assert owner.reference_function == "RSI"


def test_reference_owned_refuses_when_reference_unavailable() -> None:
    # Wrapping is mandatory: with no verified reference, a reference-owned formula cannot
    # be computed — the seam returns the unavailable-dependency refusal, never a silent
    # fall back to re-implemented arithmetic (FM-2, FM-5).
    refusal = resolve_canonical_arithmetic("sma", reference=_unavailable())
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_package_owned_resolves_without_a_reference() -> None:
    # A package-owned formula is canonical here regardless of the reference status.
    owner = _unwrap(resolve_canonical_arithmetic("vwap", reference=_unavailable()))
    assert owner.ownership is FormulaOwnership.PACKAGE


def test_resolve_unknown_formula_is_refused() -> None:
    assert is_refusal(resolve_canonical_arithmetic("no_such_formula"))


def test_resolve_uses_import_assertion_by_default() -> None:
    # With no injected status, resolution uses the import-time assertion (Ok here).
    assert is_ok(resolve_canonical_arithmetic("ema"))


# --- AC3/FM-5: structural conformance ---------------------------------------


def test_shipped_registry_is_structurally_conformant() -> None:
    assert ownership_conformance_defects() == ()


def test_reimplementing_a_reference_formula_is_a_defect() -> None:
    # A package-owned formula that names a reference function re-implements arithmetic the
    # reference owns — a contract defect (FM-5).
    bad = MappingProxyType(
        {"sma": FormulaOwner("sma", FormulaOwnership.PACKAGE, reference_function="SMA")}
    )
    defects = ownership_conformance_defects(bad)
    assert len(defects) == 1
    assert "FM-5" in defects[0]


def test_reference_owned_without_a_wrap_target_is_a_defect() -> None:
    bad = MappingProxyType({"sma": FormulaOwner("sma", FormulaOwnership.REFERENCE, None)})
    assert ownership_conformance_defects(bad) != ()


def test_blank_wrap_target_is_a_defect() -> None:
    bad = MappingProxyType(
        {"sma": FormulaOwner("sma", FormulaOwnership.REFERENCE, reference_function="   ")}
    )
    assert ownership_conformance_defects(bad) != ()


def test_key_formula_id_mismatch_is_a_defect() -> None:
    bad = MappingProxyType(
        {"sma": FormulaOwner("ema", FormulaOwnership.REFERENCE, reference_function="EMA")}
    )
    assert ownership_conformance_defects(bad) != ()


# --- FM-5: reference-grounded conformance -----------------------------------


def test_shipped_registry_is_reference_grounded_conformant() -> None:
    # Verified against the live reference: every wrap target exists, no package-owned
    # formula collides with a reference function.
    defects = _unwrap(reference_grounded_defects())
    assert defects == ()


def test_reference_grounded_flags_missing_wrap_target() -> None:
    bad = MappingProxyType(
        {"nope": FormulaOwner("nope", FormulaOwnership.REFERENCE, reference_function="NOT_A_FUNC")}
    )
    defects = _unwrap(reference_grounded_defects(bad))
    assert len(defects) == 1
    assert "not " in defects[0].lower()


def test_reference_grounded_flags_package_owned_collision() -> None:
    # "sma" declared package-owned but the reference implements SMA — must be wrapped.
    bad = MappingProxyType({"sma": FormulaOwner("sma", FormulaOwnership.PACKAGE, None)})
    defects = _unwrap(reference_grounded_defects(bad))
    assert len(defects) == 1
    assert "FM-5" in defects[0]


def test_reference_grounded_refuses_when_reference_unavailable() -> None:
    # With no verified reference, the grounded check cannot run and says so.
    refusal = reference_grounded_defects(reference=_unavailable())
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# --- AC5: package-neutral surface -------------------------------------------


def test_ownership_surface_exposes_no_vendor_object() -> None:
    # FormulaOwner carries only package-neutral fields; reference_status is a neutral
    # ArithmeticReference; the vendor module is never re-exported.
    owner = _unwrap(canonical_owner("macd"))
    assert isinstance(owner.formula_id, str)
    assert isinstance(owner.ownership, FormulaOwnership)
    assert owner.reference_function is None or isinstance(owner.reference_function, str)
    assert is_ok(reference_status())
    assert not hasattr(qmf.indicators, "talib")


def test_canonical_owners_is_immutable() -> None:
    assert isinstance(CANONICAL_OWNERS, MappingProxyType)
