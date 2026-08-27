"""Epic 1 — CT-04 typed refusal envelope (Story 1.2, refusal.py). L1 unit.

Independent, requirements-derived assertions (E1-U01..U08). Authored from CT-04
(docs/contracts/ct-04-typed-refusal.yaml), component FM-8, and epics.md Story 1.2.
Source code is read-only evidence: a failing assertion is a FINDING, never a
reason to weaken the test.
"""

from __future__ import annotations

import dataclasses

import pytest
from qmf.core.exact import Money
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

# The seven CT-04 categories and three retryability values, verbatim from CT-04.
SEVEN_CATEGORIES = {
    "invalid input",
    "unsupported capability",
    "unavailable dependency",
    "stale evidence",
    "policy rejection",
    "transient venue failure",
    "storage failure",
}
THREE_RETRYABILITIES = {"yes", "no", "after-condition"}


def _refusal(result: Result[object]) -> TypedRefusal:
    assert is_refusal(result), f"expected a TypedRefusal arm, got {result!r}"
    return result


# E1-U01 -----------------------------------------------------------------------
def test_e1_u01_typed_refusal_is_frozen_value_carrying_the_three_fields() -> None:
    """CT-04 schema: TypedRefusal is a frozen-dataclass value carrying category,
    context, retryability; construct + read back all three."""
    assert dataclasses.is_dataclass(TypedRefusal)
    refusal = TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={"field": "x", "reason": "y"},
    )
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.retryability is Retryability.NO
    assert refusal.context["field"] == "x"
    assert refusal.context["reason"] == "y"
    # Frozen: post-construction mutation is refused.
    with pytest.raises(dataclasses.FrozenInstanceError):
        refusal.category = RefusalCategory.STORAGE_FAILURE  # type: ignore[misc]


# E1-U02 -----------------------------------------------------------------------
def test_e1_u02_category_is_exactly_the_seven_values_no_eighth() -> None:
    """CT-04 enums.category: exactly the seven values; an eighth is not
    representable."""
    assert {member.value for member in RefusalCategory} == SEVEN_CATEGORIES
    with pytest.raises(ValueError):
        RefusalCategory("an eighth category")


# E1-U03 -----------------------------------------------------------------------
def test_e1_u03_retryability_is_exactly_three_values() -> None:
    """CT-04 enums.retryability: exactly yes / no / after-condition."""
    assert {member.value for member in Retryability} == THREE_RETRYABILITIES
    with pytest.raises(ValueError):
        Retryability("maybe")


# E1-U04 -----------------------------------------------------------------------
def test_e1_u04_after_condition_descriptor_present_only_when_after_condition() -> None:
    """CT-04 nullability: after_condition_descriptor present ONLY when
    retryability = after-condition, absent otherwise (both arms)."""
    # Present + after-condition -> accepted.
    ok = TypedRefusal.try_create(
        RefusalCategory.TRANSIENT_VENUE_FAILURE,
        Retryability.AFTER_CONDITION,
        after_condition_descriptor="retry after venue reconnect",
    )
    assert is_ok(ok)
    assert ok.value.after_condition_descriptor == "retry after venue reconnect"
    # after-condition but MISSING descriptor -> refusal.
    missing = TypedRefusal.try_create(
        RefusalCategory.TRANSIENT_VENUE_FAILURE, Retryability.AFTER_CONDITION
    )
    r1 = _refusal(missing)
    assert r1.context["field"] == "after_condition_descriptor"
    # descriptor supplied with a non-after-condition retryability -> refusal.
    stray = TypedRefusal.try_create(
        RefusalCategory.INVALID_INPUT,
        Retryability.NO,
        after_condition_descriptor="should not be here",
    )
    r2 = _refusal(stray)
    assert r2.context["field"] == "after_condition_descriptor"


# E1-U05 -----------------------------------------------------------------------
def test_e1_u05_context_always_present_structured_never_null() -> None:
    """CT-04 / DEC-0112: context is always present and a structured object (may be
    empty), never null."""
    default_ctx = TypedRefusal(
        category=RefusalCategory.STORAGE_FAILURE, retryability=Retryability.NO
    )
    assert default_ctx.context is not None
    # A mapping (structured), possibly empty.
    assert hasattr(default_ctx.context, "keys")
    assert dict(default_ctx.context) == {}


# E1-U06 (mutmut pin) ----------------------------------------------------------
def test_e1_u06_refusal_context_carries_exact_field_reason_and_enum_member() -> None:
    """CT-04 / DEC-0112 (pins exact.py:166 & the refusal-helper family): a domain
    refusal's context carries the exact documented keys (field, reason) with real
    values, and retryability is the exact enum member — not merely a truthy dict."""
    refusal = _refusal(Money.try_create(1.5, "USD", 2))
    assert refusal.category is RefusalCategory.INVALID_INPUT
    # exact structural keys, real values (kills the key-rename mutants):
    assert refusal.context["field"] == "value"
    assert isinstance(refusal.context["reason"], str)
    assert refusal.context["reason"] != ""
    # exact enum member (kills the retryability=None mutant):
    assert refusal.retryability is Retryability.NO


# E1-U07 -----------------------------------------------------------------------
def test_e1_u07_try_create_returns_refusal_arm_unchecked_ctor_still_available() -> None:
    """CT-04 / DEC-0109: try_create(invalid) returns the refusal arm; the unchecked
    constructor remains available for trusted internal use."""
    bad = TypedRefusal.try_create("not a category", "no")
    assert is_refusal(bad)  # refusal arm returned directly, not Ok-wrapped
    # unchecked constructor path builds a value with no validation:
    direct = TypedRefusal(category=RefusalCategory.POLICY_REJECTION, retryability=Retryability.YES)
    assert direct.category is RefusalCategory.POLICY_REJECTION


# E1-U08 -----------------------------------------------------------------------
def test_e1_u08_refusal_is_returned_not_raised_and_not_swallowed() -> None:
    """CT-04 / DEC-0109/0112: a refusal is RETURNED as a result-union arm, never
    raised across the public boundary, and never swallowed (a value comes back)."""
    result = Money.try_create("not-an-int", "USD", 2)  # invalid domain input
    # No exception was raised to get here; a value was returned:
    assert isinstance(result, (Ok, TypedRefusal))
    assert is_refusal(result)
    # The refusal is not swallowed — it carries actionable context.
    assert dict(result.context) != {}
