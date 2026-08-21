"""Executable CT-04 contract test, owned by qmf-core.

Verifies the typed refusal envelope: the seven categories and three retryability
values exactly, refusals RETURNED (never raised) across the boundary, the
``try_create`` value-or-refusal pattern, the never-null context, the
after-condition pairing rule, and value immutability (CT-04; DEC-0109, DEC-0112).
"""

from __future__ import annotations

import dataclasses

import pytest
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)


def test_category_enum_is_exactly_the_seven_values() -> None:
    assert {member.value for member in RefusalCategory} == {
        "invalid input",
        "unsupported capability",
        "unavailable dependency",
        "stale evidence",
        "policy rejection",
        "transient venue failure",
        "storage failure",
    }


def test_retryability_enum_is_exactly_three_values() -> None:
    assert {member.value for member in Retryability} == {"yes", "no", "after-condition"}


def test_typed_refusal_is_a_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(TypedRefusal)
    refusal = TypedRefusal(RefusalCategory.INVALID_INPUT, Retryability.NO)
    with pytest.raises(dataclasses.FrozenInstanceError):
        refusal.category = RefusalCategory.STORAGE_FAILURE  # type: ignore


def test_context_defaults_to_present_empty_non_null_mapping() -> None:
    refusal = TypedRefusal(RefusalCategory.STORAGE_FAILURE, Retryability.NO)
    assert refusal.context is not None
    assert dict(refusal.context) == {}


def test_context_is_snapshotted_and_immutable() -> None:
    source: dict[str, object] = {"path": "/x"}
    refusal = TypedRefusal(RefusalCategory.STORAGE_FAILURE, Retryability.NO, context=source)
    source["path"] = "/mutated"  # mutating the source must not leak into the value
    assert refusal.context["path"] == "/x"
    with pytest.raises(TypeError):
        refusal.context["path"] = "/nope"  # type: ignore


def test_after_condition_descriptor_absent_by_default() -> None:
    refusal = TypedRefusal(RefusalCategory.INVALID_INPUT, Retryability.NO)
    assert refusal.after_condition_descriptor is None


def test_try_create_returns_ok_on_valid_input() -> None:
    result = TypedRefusal.try_create("policy rejection", "no")
    assert is_ok(result)
    refusal = result.value
    assert refusal.category is RefusalCategory.POLICY_REJECTION
    assert refusal.retryability is Retryability.NO
    assert refusal.after_condition_descriptor is None


def test_try_create_accepts_enum_members_too() -> None:
    result = TypedRefusal.try_create(RefusalCategory.STALE_EVIDENCE, Retryability.YES)
    assert is_ok(result)
    assert result.value.category is RefusalCategory.STALE_EVIDENCE


def test_try_create_after_condition_carries_descriptor() -> None:
    result = TypedRefusal.try_create(
        "transient venue failure",
        "after-condition",
        after_condition_descriptor="retry after 2s",
    )
    assert is_ok(result)
    assert result.value.retryability is Retryability.AFTER_CONDITION
    assert result.value.after_condition_descriptor == "retry after 2s"


def test_try_create_preserves_context_but_never_null() -> None:
    result = TypedRefusal.try_create("policy rejection", "no", context={"rule": "R-1"})
    assert is_ok(result)
    assert result.value.context["rule"] == "R-1"
    empty = TypedRefusal.try_create("policy rejection", "no")
    assert is_ok(empty)
    assert dict(empty.value.context) == {}


def test_try_create_refuses_unknown_category() -> None:
    result = TypedRefusal.try_create("nonsense", "no")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.retryability is Retryability.NO
    assert result.context["field"] == "category"


def test_try_create_refuses_unknown_retryability() -> None:
    result = TypedRefusal.try_create("invalid input", "maybe")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "retryability"


def test_try_create_refuses_missing_after_condition_descriptor() -> None:
    result = TypedRefusal.try_create("transient venue failure", "after-condition")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "after_condition_descriptor"


def test_try_create_refuses_descriptor_without_after_condition() -> None:
    result = TypedRefusal.try_create("invalid input", "no", after_condition_descriptor="nope")
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "after_condition_descriptor"


def test_invalid_construction_is_returned_not_raised() -> None:
    # A domain-invalid request produces a value, never an exception across the
    # boundary — the caller branches on it (CT-04; DEC-0109).
    result = TypedRefusal.try_create("nonsense", "nonsense")
    assert isinstance(result, TypedRefusal)


def test_is_ok_and_is_refusal_partition_the_result() -> None:
    good = TypedRefusal.try_create("storage failure", "no")
    bad = TypedRefusal.try_create("storage failure", "sometimes")
    assert is_ok(good)
    assert not is_refusal(good)
    assert is_refusal(bad)
    assert not is_ok(bad)


def test_refusals_with_equal_parts_are_equal() -> None:
    left = TypedRefusal(RefusalCategory.INVALID_INPUT, Retryability.NO, context={"k": 1})
    right = TypedRefusal(RefusalCategory.INVALID_INPUT, Retryability.NO, context={"k": 1})
    assert left == right


def test_ok_wraps_and_exposes_its_value() -> None:
    assert Ok(42).value == 42
    assert Ok(42) == Ok(42)


# --- L1: TypedRefusal is hashable -------------------------------------------


def test_typed_refusal_is_hashable() -> None:
    # Regression (L1): a frozen dataclass hashes its fields, but ``context`` is a
    # MappingProxyType wrapping a dict (unhashable), so the generated hash used to
    # raise TypeError. Hashing must work.
    refusal = TypedRefusal(
        RefusalCategory.INVALID_INPUT,
        Retryability.NO,
        context={"field": "scale", "allowed": ["a", "b"]},
    )
    assert isinstance(hash(refusal), int)


def test_typed_refusal_hash_is_consistent_with_equality() -> None:
    # Equal refusals hash alike regardless of context key order (matches ``==``).
    left = TypedRefusal(
        RefusalCategory.STORAGE_FAILURE, Retryability.NO, context={"a": 1, "b": [2, 3]}
    )
    right = TypedRefusal(
        RefusalCategory.STORAGE_FAILURE, Retryability.NO, context={"b": [2, 3], "a": 1}
    )
    assert left == right
    assert hash(left) == hash(right)


def test_typed_refusal_is_usable_in_sets_and_dicts() -> None:
    a = TypedRefusal(RefusalCategory.POLICY_REJECTION, Retryability.NO, context={"rule": "R-1"})
    b = TypedRefusal(RefusalCategory.POLICY_REJECTION, Retryability.NO, context={"rule": "R-1"})
    c = TypedRefusal(RefusalCategory.POLICY_REJECTION, Retryability.NO, context={"rule": "R-2"})
    # Equal refusals collapse; a distinct one stays separate.
    assert len({a, b, c}) == 2
    assert {a: "seen"}[b] == "seen"


def test_typed_refusal_hash_handles_nested_mapping_context() -> None:
    # A nested mapping in context (deep-frozen to a mappingproxy) is still hashable.
    refusal = TypedRefusal(
        RefusalCategory.INVALID_INPUT,
        Retryability.NO,
        context={"meta": {"k": [1, 2]}},
    )
    assert isinstance(hash(refusal), int)


# --- L3: context is deep-frozen ---------------------------------------------


def test_context_nested_mapping_is_deep_frozen() -> None:
    # Regression (L3): __post_init__ froze only the top level, leaving nested dicts
    # and lists shared and mutable. Nested containers must be read-only too.
    source: dict[str, object] = {"meta": {"alias": "ICM"}, "tags": ["x", "y"]}
    refusal = TypedRefusal(RefusalCategory.INVALID_INPUT, Retryability.NO, context=source)
    # A later mutation of the caller's nested dict cannot leak into the value.
    source["meta"]["alias"] = "TAMPERED"  # type: ignore[index]
    assert refusal.context["meta"]["alias"] == "ICM"  # type: ignore[index]
    # The stored nested mapping is itself immutable.
    with pytest.raises(TypeError):
        refusal.context["meta"]["k"] = 1  # type: ignore[index]
    # Nested sequences are frozen to tuples.
    assert refusal.context["tags"] == ("x", "y")
