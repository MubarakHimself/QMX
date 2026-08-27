"""L2 contract adoption + refusal shape for Epic 7.

T7-C1 valid CT-16 record + missing-element defect; T7-C2 refusals RETURNED never raised
+ no correlation_id on the pure signature; T7-C3 refusal-category mapping; T7-C4 the
equality-law contract behaviour (integer-ULP comparator; binds only when both modes).
"""

from __future__ import annotations

import inspect

import _fixtures as F
from qmf.core import World, is_ok, is_refusal
from qmf.indicators import (
    IndicatorSeries,
    ModeEqualityComparator,
    PresenceState,
    align_to_instant,
    assert_mode_equality,
    compute_batch,
    guard_synchronous_entry,
    evaluate_light_claim,
    series_equal_within_ulps,
)
from qmf.indicators import _reference
from qmf.indicators.configured_indicator import IDENTITY_ELEMENTS

# The eleven identity elements the CT-16 contract requires (invariant 2) — the oracle,
# stated from the contract, independent of the package's self-declared tuple.
_CONTRACT_IDENTITY_ELEMENTS = (
    "formula_id",
    "contract_format_version",
    "parameters",
    "inputs",
    "calendar_requirements",
    "alignment_policy",
    "missing_value_policy",
    "warm_up",
    "output_schema",
    "supported_modes",
    "arithmetic_reference_configuration",
)


# --- T7-C1: valid record + missing-element defect [R1, R3] ------------------


def test_c1_valid_record_carries_every_required_identity_element() -> None:
    """A valid CT-16 record's fp1 content carries every element the contract requires."""
    content = F.config().fp1_identity()
    for element in _CONTRACT_IDENTITY_ELEMENTS:
        assert element in content, f"required identity element {element!r} missing from fp1 content"
    # The package's declared element set must not narrow the contract's.
    for element in _CONTRACT_IDENTITY_ELEMENTS:
        assert element in IDENTITY_ELEMENTS


def test_c1_omitting_a_required_field_at_construction_is_refused() -> None:
    """A declaration omitting a required identity element is a contract defect the factory
    rejects (not silently accepted). Counter-case: a config built with no inputs succeeds."""
    assert is_refusal(F.try_config(inputs=[]))
    assert is_refusal(F.try_config(output_schema=[]))
    assert is_refusal(F.try_config(supported_modes=[]))


# --- T7-C2: refusals RETURNED, never raised [CT-04; CT-16 inv.18] -----------


def test_c2_every_boundary_returns_value_or_refusal_never_raises() -> None:
    """Counter-case: a malformed input raising across the pure boundary. Every public
    boundary RETURNS a value-or-refusal."""
    assert is_refusal(F.try_config(formula_id="  "))
    assert is_refusal(compute_batch("not-a-config", {}, kernel=F.EchoKernel(), world=World.REPLAY))
    assert is_refusal(align_to_instant("nope", "nope", "as-of"))
    assert is_refusal(assert_mode_equality("nope", "nope", "nope"))
    assert is_refusal(evaluate_light_claim("nope"))


def test_c2_correlation_id_does_not_cross_the_pure_value_signatures() -> None:
    """correlation_id rides the caller's context, never a pure signature. Counter-case: a
    public pure function declaring a correlation_id parameter."""
    for func in (compute_batch, align_to_instant, assert_mode_equality, series_equal_within_ulps):
        params = inspect.signature(func).parameters
        assert "correlation_id" not in params, f"{func.__name__} exposes correlation_id"


# --- T7-C3: refusal-category mapping [R14, R25, R7, R22, R4] -----------------


def test_c3_forward_fill_across_the_instant_is_policy_rejection() -> None:
    series = F.input_series([100, 101, 102])
    instant = F.instants(1, start=2_000)[0]
    for mode in ("forward-fill", "interpolate"):
        refusal = align_to_instant(series, instant, mode)
        assert is_refusal(refusal)
        assert refusal.category.value == "policy rejection", mode


def test_c3_heavy_synchronous_entry_is_unsupported_capability() -> None:
    verdict = F.unwrap(evaluate_light_claim(F.config()))  # no budget ⇒ heavy
    refusal = guard_synchronous_entry(verdict)
    assert is_refusal(refusal)
    assert refusal.category.value == "unsupported capability"


def test_c3_reference_config_mismatch_is_unavailable_dependency() -> None:
    """A drifted process-global reference configuration is an `unavailable dependency`
    refusal — asserted through the documented import-assertion seam."""
    from types import MappingProxyType

    resolved = _reference.ResolvedReference(
        c_library_version="0.7.1",
        wrapper_version="0.7.1",
        observed_configuration=MappingProxyType(
            {"compatibility_mode": "metastock", "candle_settings": "reference-default"}
        ),
    )
    refusal = _reference.assert_reference(resolved)
    assert is_refusal(refusal)
    assert refusal.category.value == "unavailable dependency"


def test_c3_binary_float_param_is_invalid_input() -> None:
    refusal = F.try_config(parameters={"period": 3.5})
    assert is_refusal(refusal)
    assert refusal.category.value == "invalid input"


# --- T7-C4: the equality-law contract behaviour [R19] -----------------------


def _two_series_differing_by_one_ulp() -> tuple[IndicatorSeries, IndicatorSeries]:
    presence = [PresenceState.PRESENT, PresenceState.PRESENT]
    instants = F.instants(2)
    from qmf.indicators import InputSeries  # reuse the bulk factory for two int64 columns

    left = F.unwrap(InputSeries.from_values([100, 200], 2, presence, instants))
    right = F.unwrap(InputSeries.from_values([100, 201], 2, presence, instants))
    a = F.unwrap(IndicatorSeries.try_create(left.values, 2, presence, instants))
    b = F.unwrap(IndicatorSeries.try_create(right.values, 2, presence, instants))
    return a, b


def test_c4_integer_ulp_comparator_default_zero_is_exact() -> None:
    """At ulps=0 a one-unit difference is unequal; at ulps=1 it is accepted. Counter-case:
    the default tolerance silently accepting a one-ULP difference."""
    a, b = _two_series_differing_by_one_ulp()
    assert F.unwrap(series_equal_within_ulps(a, b, 0)) is False
    assert F.unwrap(series_equal_within_ulps(a, b, 1)) is True
    assert ModeEqualityComparator().ulps == 0


def test_c4_equality_law_binds_only_when_both_modes_declared() -> None:
    """assert_mode_equality refuses a configuration that does not declare both modes."""
    batch_only = F.config(supported_modes=["batch"])
    series = F.input_series([100, 101, 102, 103])
    result = compute_batch(batch_only, {"close": series}, kernel=F.EchoKernel(), world=World.REPLAY)
    bres = F.unwrap(result)
    refusal = assert_mode_equality(batch_only, bres, bres)
    assert is_refusal(refusal)
    assert refusal.category.value == "invalid input"
