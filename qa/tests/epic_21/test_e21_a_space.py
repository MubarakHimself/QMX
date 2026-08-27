"""Group A — Typed parameter search space (Story 21.1) -> R1-R5.

Public surface driven: ``qmb.optimize.coerce_study_space`` (Study-creation admission
over the one CT-33 schema) and the returned ``StudyParameterSpace`` value's identity
and fingerprint. A malformed space is a FINDING only if it is *accepted*; a refusal
is the requirement.
"""

from __future__ import annotations

from conftest import (
    RefusalCategory,
    assert_ct04_refusal,
    boolean_param,
    categorical_param,
    find_floats,
    int_param,
    is_ok,
    money_param,
    rational_param,
    unwrap,
)

from qmb.optimize.space import STUDY_SPACE_KEY, coerce_study_space


# --- T21-301 [R1] ------------------------------------------------------------


def test_t21_301_wellformed_space_validates_and_is_identity_content() -> None:
    """A four-type space validates at creation and materialises as run-config identity.

    Counter-case that would FAIL: a well-formed space rejected, or its declared
    parameters absent from the fingerprinted config layer (a mutated tunnel, OPT-2).
    """
    decl = [
        int_param("fast", lo=1, hi=30, step=1, default=5),
        rational_param("tol"),
        categorical_param("mode", ["trend", "range"], "trend"),
        boolean_param("use_stop", True),
        money_param("stop"),
    ]
    result = coerce_study_space(decl)
    assert is_ok(result), f"a well-formed four-type space must validate, got {result!r}"
    space = result.value

    # The declared parameters are identity-bearing content of the resolved run-config,
    # not a code-edited tunnel: the run-config layer carries the space's fp1 identity.
    layer = space.run_config_layer()
    assert STUDY_SPACE_KEY in layer
    assert layer[STUDY_SPACE_KEY] == space.fp1_identity()
    assert set(space.parameter_names) == {"fast", "tol", "mode", "use_stop", "stop"}

    # The space fingerprints clean and its identity holds no binary float.
    assert is_ok(space.fingerprint())
    assert find_floats(space.fp1_identity()) == []


# --- T21-302 [R2] ------------------------------------------------------------


def test_t21_302_numeric_bounds_violations_refuse_without_clamp() -> None:
    """min>max, step<=0, and step>(max-min) each refuse invalid input, never a clamp.

    Counter-case that would FAIL: any of the three malformed ranges accepted (a silent
    clamp), or a refusal of a category other than invalid input.
    """
    # min > max
    bad_range = coerce_study_space([int_param("x", lo=20, hi=1, step=1, default=1)])
    assert_ct04_refusal(bad_range, RefusalCategory.INVALID_INPUT, what="min>max")

    # step <= 0
    bad_step = coerce_study_space([int_param("x", lo=0, hi=10, step=0, default=0)])
    assert_ct04_refusal(bad_step, RefusalCategory.INVALID_INPUT, what="step<=0")

    # step > (max - min): the OPT-3 search-room rule
    no_room = coerce_study_space([int_param("x", lo=0, hi=4, step=10, default=0)])
    refusal = assert_ct04_refusal(no_room, RefusalCategory.INVALID_INPUT, what="step>span")
    assert refusal.context.get("parameter") == "x", "the refusal names the offending parameter"


# --- T21-303 [R3] ------------------------------------------------------------


def test_t21_303_categorical_violations_refuse() -> None:
    """Empty options and a default outside the options each refuse invalid input.

    Counter-case that would FAIL: either malformed categorical accepted.
    """
    empty = coerce_study_space([categorical_param("mode", [], "trend")])
    assert_ct04_refusal(empty, RefusalCategory.INVALID_INPUT, what="empty options")

    not_in = coerce_study_space([categorical_param("mode", ["trend", "range"], "chop")])
    assert_ct04_refusal(not_in, RefusalCategory.INVALID_INPUT, what="default not in options")


# --- T21-304 [R4] P0 money-path float ban ------------------------------------


def test_t21_304_money_binary_float_anywhere_refuses() -> None:
    """A binary float at any money bound refuses; a well-formed money param validates.

    Counter-case that would FAIL: a float min/max/step/default admitted into a money
    parameter (a float on the money path), or a money-as-rational declaration accepted.
    """
    ok = coerce_study_space([money_param("stop", lo=100, hi=1000, step=100, default=500)])
    assert is_ok(ok), f"an exact-integer money parameter must validate, got {ok!r}"

    for field, decl in (
        ("min", money_param("stop", lo=100.0, hi=1000, step=100, default=500)),
        ("max", money_param("stop", lo=100, hi=1000.5, step=100, default=500)),
        ("step", money_param("stop", lo=100, hi=1000, step=100.5, default=500)),
        ("default", money_param("stop", lo=100, hi=1000, step=100, default=500.0)),
    ):
        result = coerce_study_space([decl])
        assert_ct04_refusal(result, RefusalCategory.INVALID_INPUT, what=f"float money {field}")

    # OPT-4: money declared as an exact rational (not exact integer) is refused.
    as_rational = coerce_study_space([money_param("stop", type_="exact rational")])
    assert_ct04_refusal(as_rational, RefusalCategory.INVALID_INPUT, what="money-as-rational")


# --- T21-305 [R5] identity ---------------------------------------------------


def test_t21_305_same_space_shares_fingerprint_no_float_in_identity() -> None:
    """Two Studies declaring the same space share the space fingerprint; identity is float-free.

    Counter-case that would FAIL: identical spaces fingerprinting differently, a
    genuinely different space sharing a fingerprint, or a float reaching identity.
    """
    decl = [int_param("fast", lo=1, hi=30, step=1, default=5), money_param("stop")]
    a = unwrap(coerce_study_space(decl))
    b = unwrap(coerce_study_space([int_param("fast", lo=1, hi=30, step=1, default=5), money_param("stop")]))
    assert unwrap(a.fingerprint()).value == unwrap(b.fingerprint()).value

    # A materially different space must NOT collide (the fingerprint is discriminating).
    other = unwrap(coerce_study_space([int_param("fast", lo=1, hi=40, step=1, default=5), money_param("stop")]))
    assert unwrap(a.fingerprint()).value != unwrap(other.fingerprint()).value

    assert find_floats(a.fp1_identity()) == []
