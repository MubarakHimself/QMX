"""L1 minimal unit laws for Epic 7 — reached only where L3 acceptance cannot.

T7-U1 binary-float refusal; T7-U2 fp1 spans the whole configuration; T7-U3 presence-map
integrity; T7-U4 warm-up discipline. hypothesis drives U1/U3/U4 where a property over a
range carries the law; each generator's refuse/accept arm is reachable.
"""

from __future__ import annotations

import _fixtures as F
from hypothesis import given, settings
from hypothesis import strategies as st
from qmf.core import World, canonical_bytes, fingerprint, is_ok, is_refusal
from qmf.indicators import (
    ArithmeticReference,
    PresenceState,
    compute_batch,
)


# --- T7-U1: a binary-float parameter is refused [R4] ------------------------


@settings(max_examples=60)
@given(value=st.floats(allow_nan=False, allow_infinity=False, min_value=-1e9, max_value=1e9))
def test_u1_any_binary_float_parameter_is_refused(value: float) -> None:
    """Counter-case that must fail: a float parameter admitted into a configuration.
    Every binary float on the parameter path is refused with `invalid input`."""
    result = F.try_config(parameters={"period": value})
    assert is_refusal(result), f"a float parameter {value!r} was not refused"
    assert result.category.value == "invalid input"
    assert result.context["field"] == "parameters"


def test_u1_exact_rational_parameter_is_accepted_and_leaves_no_float_in_identity() -> None:
    """The accept arm: a scaled-integer / num-den rational is admitted, and the whole
    identity content serialises fp1-clean (no binary float ever enters identity)."""
    cfg = F.config(parameters={"period": F.period(20)})
    assert is_ok(canonical_bytes(cfg.fp1_identity())), "identity content is not fp1-clean"


def test_u1_num_den_rational_is_accepted() -> None:
    cfg = F.config(parameters={"period": F.period(21, 1)})
    assert F.unwrap(cfg.fp1()).value.startswith("fp1:sha256:")


# --- T7-U2: fp1 spans the WHOLE configuration [R1, R2] ----------------------

# The eleven required identity elements the CT-16 contract names (invariant 2). Each is
# mutated at the configuration level; the fingerprint MUST move. Alignment policy has a
# single governed-evidence-legal member, so its presence is proven by content pruning.
_MUTATIONS: dict[str, dict[str, object]] = {
    "formula_id": {"formula_id": "ema"},
    "contract_format_version": {"contract_format_version": 2},
    "parameters": {"parameters": {"period": F.period(21)}},
    "inputs": {"inputs": [F.series_input("open")]},
    "calendar_requirements": {"calendar_requirements": [F.calendar("2024.1")]},
    "missing_value_policy": {"missing_value_policy": "refuse"},
    "warm_up": {"warm_up": 5},
    "output_schema": {"output_schema": [F.output_channel("ema")]},
    "supported_modes": {"supported_modes": ["batch"]},
    "arithmetic_reference_configuration": {
        "arithmetic_reference_configuration": F.unwrap(
            ArithmeticReference.try_create(
                "ta-lib-c==9.9.9", "ta-lib==0.7.1", {"compatibility_mode": "default"}
            )
        )
    },
}


def test_u2_mutating_any_required_identity_element_changes_fp1() -> None:
    """Counter-case: mutating an element leaves fp1 unchanged (element not in identity).
    Ten of the eleven required elements are mutable at the config level; each must move fp1."""
    baseline = F.unwrap(F.config().fp1()).value
    for element, override in _MUTATIONS.items():
        mutated = F.unwrap(F.config(**override).fp1()).value
        assert mutated != baseline, f"mutating {element!r} did not change fp1 (missing from identity)"


def test_u2_alignment_policy_is_present_and_load_bearing_in_identity() -> None:
    """alignment_policy (single legal value) is present in the hashed identity content and
    dropping it changes the fingerprint — proving it is hashed, not stored-but-ignored."""
    content = F.config().fp1_identity()
    assert "alignment_policy" in content
    baseline = F.unwrap(fingerprint(content)).value
    pruned = {k: v for k, v in content.items() if k != "alignment_policy"}
    assert F.unwrap(fingerprint(pruned)).value != baseline


def test_u2_byte_identical_config_yields_identical_fp1_and_display_field_is_absent() -> None:
    """Same input + same config ⇒ the same fingerprinted series. The light/heavy verdict is
    display-only and never a config field, so identity carries no verdict."""
    assert F.unwrap(F.config().fp1()).value == F.unwrap(F.config().fp1()).value
    assert "verdict" not in F.config().fp1_identity()
    assert "light" not in F.config().fp1_identity()


# --- T7-U3: presence-map integrity [R12] ------------------------------------

_PRESENCE_STATES = {s.value for s in PresenceState}


@settings(max_examples=40)
@given(
    values=st.lists(st.integers(min_value=-10_000, max_value=10_000), min_size=1, max_size=20),
    lookback=st.integers(min_value=0, max_value=6),
)
def test_u3_batch_output_is_full_length_presence_mapped_no_sentinel(
    values: list[int], lookback: int
) -> None:
    """Counter-case: an output shorter than the input (begin-index trim), a position with
    no presence state, or a NaN/sentinel in the value channel. For any generated series the
    output is full-length, every position carries a presence state, values are integers."""
    warm_up = max(lookback, 0)
    cfg = F.config(warm_up=warm_up, supported_modes=["batch"])
    series = F.input_series(values)
    result = compute_batch(
        cfg, {"close": series}, kernel=F.EchoKernel(lookback=lookback), world=World.REPLAY
    )
    assert is_ok(result), f"batch refused for values={values!r}: {result}"
    out = F.unwrap(result).outputs["sma"]
    assert out.length == len(values), "begin-index trimming is prohibited (full-length output)"
    assert len(out.presence) == len(values)
    for index in range(out.length):
        assert out.presence_at(index).value in _PRESENCE_STATES
        assert isinstance(out.value_at(index), int)  # int64 layout — a NaN cannot appear


# --- T7-U4: warm-up discipline [R16] ----------------------------------------


@settings(max_examples=30)
@given(lookback=st.integers(min_value=1, max_value=6))
def test_u4_warm_up_below_reference_lookback_is_refused(lookback: int) -> None:
    """Counter-case: a warm-up below the reference lookback accepted. compute_batch must
    refuse when warm_up < the kernel's leading-undefined count."""
    values = list(range(100, 100 + lookback + 4))
    cfg = F.config(warm_up=lookback - 1, supported_modes=["batch"])
    result = compute_batch(
        cfg, {"close": values_series(values)}, kernel=F.EchoKernel(lookback=lookback), world=World.REPLAY
    )
    assert is_refusal(result), "warm-up below the reference lookback was not refused"
    assert result.context["field"] == "warm_up"


@settings(max_examples=30)
@given(warm_up=st.integers(min_value=1, max_value=6))
def test_u4_warm_up_window_is_marked_not_ready_never_a_number(warm_up: int) -> None:
    """During warm-up the output is a marked not_ready value, never a number. Every dense
    position before `warm_up` completed observations is not_ready."""
    values = list(range(100, 100 + warm_up + 3))
    cfg = F.config(warm_up=warm_up, supported_modes=["batch"])
    result = compute_batch(
        cfg, {"close": values_series(values)}, kernel=F.EchoKernel(lookback=0), world=World.REPLAY
    )
    out = F.unwrap(result).outputs["sma"]
    for index in range(warm_up):
        assert out.presence_at(index) is PresenceState.NOT_READY, f"position {index} not marked not_ready"
    # After warm-up a present value carries a real number.
    assert out.presence_at(warm_up) is PresenceState.PRESENT


def test_u4_warm_up_is_an_integer_count_not_a_duration() -> None:
    """warm_up is an integer count; a Duration or float is refused (never ticks/Duration)."""
    assert is_refusal(F.try_config(warm_up=1.0))
    assert is_refusal(F.try_config(warm_up="2"))
    assert F.unwrap(F.try_config(warm_up=0)).warm_up == 0


def values_series(values: list[int]):
    return F.input_series(values)
