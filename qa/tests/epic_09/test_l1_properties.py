"""L1 property tests (hypothesis) for Epic 9 (qmf-structure) — CT-17 invariants,
quantified.

Oracles: CT-17 emission-invariant clause ("anchor.start <= anchor.end <= observed-at
<= confirmed-at <= invalidated-at, and observed-at >= the maximum evidence time of every
input actually consumed; violation is an invalid-input refusal"); CT-17 "All failures
are typed refusals" (R-002 no-raise); CT-17 identity-field / nullability invariant; CT-17
"exact parameters ... a binary float never enters a structure parameter".

Covers QA-E09-L1-001..004. Run:
  uv run --with hypothesis pytest qa/tests/epic_09/test_l1_properties.py -q
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from qmf.core import (
    EvidenceClass,
    Instant,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.structure import (
    AnchorPoint,
    AnchorSpan,
    CalendarAnchoredLevel,
    CompositeChild,
    CompositeObject,
    ConfirmationRecord,
    ConfirmationRule,
    DeclaredBudget,
    DeclaredFamily,
    EvaluationRuleRef,
    FamilyIdentity,
    HighLowObservation,
    InteractionRecord,
    InvalidationRecord,
    SlopedObject,
    StructureObject,
    SwingPointFamily,
    admit_across_boundary,
    admit_to_governed_library,
    causally_precedes,
    check_emission_invariant,
    check_regression,
    consume_indicator_input,
    evaluate_citation,
    evaluate_light_claim,
    graduate_to_governed,
    may_consume,
    promote_scanned,
    read_confirmed,
    refit,
    required_embargo_width,
    resolve_cascade,
    resolve_state,
    route,
    structure_result_label,
)

import _helpers as H

_NS = 1_000_000  # 1 ms step, so generated instants are well inside int64

# ---------------------------------------------------------------------------
# QA-E09-L1-001 — the emission-invariant universal (FM-1)
# ---------------------------------------------------------------------------

_offset = st.integers(min_value=0, max_value=12)


def _oracle_legal(
    *,
    a_end: int,
    observed: int,
    confirmed: int | None,
    invalidated: int | None,
    consumed: list[int],
) -> bool:
    """Independently recompute CT-17's emission invariant (anchor.start <= anchor.end is
    guaranteed by AnchorSpan construction; the rest is checked here)."""
    chain = [a_end, observed]
    if confirmed is not None:
        chain.append(confirmed)
    if invalidated is not None:
        chain.append(invalidated)
    non_decreasing = all(earlier <= later for earlier, later in zip(chain, chain[1:]))
    causal = (not consumed) or observed >= max(consumed)
    return non_decreasing and causal


@settings(max_examples=250, suppress_health_check=[HealthCheck.too_slow])
@given(
    a_start=_offset,
    a_len=st.integers(min_value=0, max_value=4),
    observed=_offset,
    confirmed=st.one_of(st.none(), _offset),
    invalidated=st.one_of(st.none(), _offset),
    consumed=st.lists(_offset, max_size=4),
)
def test_l1_001_emission_invariant_holds_iff_oracle(
    a_start: int,
    a_len: int,
    observed: int,
    confirmed: int | None,
    invalidated: int | None,
    consumed: list[int],
) -> None:
    a_end = a_start + a_len  # anchor.start <= anchor.end by construction
    anchor = H.anchor(start_min=a_start, end_min=a_end)
    result = check_emission_invariant(
        anchor=anchor,
        observed_at=H.inst(observed),
        confirmed_at=None if confirmed is None else H.inst(confirmed),
        invalidated_at=None if invalidated is None else H.inst(invalidated),
        consumed_input_times=[H.inst(c) for c in consumed],
    )
    expected = _oracle_legal(
        a_end=a_end,
        observed=observed,
        confirmed=confirmed,
        invalidated=invalidated,
        consumed=consumed,
    )
    assert is_ok(result) is expected, (
        f"emission invariant disagrees with oracle (expected legal={expected}): {result}"
    )
    if not expected:
        assert isinstance(result, TypedRefusal)
        assert result.category.value == "invalid input"


def test_l1_001_both_arms_are_reachable() -> None:
    # Falsifiability anchor: a legal chain mints, an observed-at behind a consumed input
    # refuses — both arms of the property are demonstrably hit.
    legal = check_emission_invariant(
        anchor=H.anchor(0, 1), observed_at=H.inst(2), consumed_input_times=[H.inst(1)]
    )
    illegal = check_emission_invariant(
        anchor=H.anchor(0, 1), observed_at=H.inst(2), consumed_input_times=[H.inst(9)]
    )
    assert is_ok(legal)
    assert isinstance(illegal, TypedRefusal)


# ---------------------------------------------------------------------------
# QA-E09-L1-002 — every public callable returns a Result, never raises (R-002)
# ---------------------------------------------------------------------------

_garbage = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-5, max_value=5),
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(max_size=5),
    st.lists(st.integers(min_value=-3, max_value=3), max_size=3),
    st.builds(object),
    st.builds(lambda n: Instant(value_ns=n), st.integers(min_value=0, max_value=10)),
)


def _public_calls(g: object) -> list[object]:
    """Every public boundary called with garbage in each position. Each returns a Result
    (Ok or TypedRefusal) or the property fails."""
    return [
        check_emission_invariant(
            anchor=g, observed_at=g, confirmed_at=g, invalidated_at=g, consumed_input_times=g
        ),
        resolve_state(g, g, at=g),
        resolve_cascade(g, g, g, at=g),
        refit(
            g,
            anchor=g,
            observed_at=g,
            parameters=g,
            evidence_class=g,
            consumed_input_times=g,
            first_observed_at=g,
        ),
        admit_to_governed_library(g),
        read_confirmed(g),
        may_consume(g, at=g),
        causally_precedes(g, later=g),
        structure_result_label(g, world=g, input_fingerprints=g, evidence_time_range=g),
        evaluate_citation(g),
        promote_scanned(g),
        required_embargo_width(g, observation_width=g),
        admit_across_boundary(boundary=g, observed_at=g, confirmed_at=g, embargo_width=g),
        route(value_per_evaluation_instant=g, discrete_with_birth_and_lifetime=g),
        consume_indicator_input(g),
        evaluate_light_claim(
            g, per_update_cost_ns=g, object_set_size=g, scan_window=g, has_baseline=g
        ),
        check_regression(g, g, tolerance_bps=g),
        graduate_to_governed(family=g, graduated_ref=g, originating_experiment_ref=g),
        FamilyIdentity.try_create(g, g, g),
        ConfirmationRule.try_create(g, clock_confirmed=g, confirmation_delay_bound=g),
        AnchorSpan.try_create(g, g, g, g),
        AnchorPoint.try_create(g, g),
        EvaluationRuleRef.try_create(g, g),
        DeclaredFamily.try_create(g, g),
        StructureObject.try_create(g, g, g, g, g, consumed_input_times=g),
        ConfirmationRecord.try_create(g, g, confirmed_as=g),
        InvalidationRecord.try_create(g, g),
        InteractionRecord.try_create(g, g, g, g, g),
        CompositeChild.try_create(g, g, confirmed_at=g, confirmation_delay_bound=g),
        CompositeObject.try_create(
            family=g, confirmation_rule=g, children=g, evidence_class=g, ordered=g, parameters=g
        ),
        SlopedObject.try_create(
            family=g,
            confirmation_rule=g,
            anchor_points=g,
            evaluation_rule=g,
            target_scale=g,
            rounding=g,
            observed_at=g,
            evidence_class=g,
            parameters=g,
        ),
        CalendarAnchoredLevel.try_create(
            family=g,
            confirmation_rule=g,
            calendar=g,
            sampling_policy=g,
            schedule_gap_policy=g,
            level=g,
            observed_at=g,
            evidence_class=g,
            parameters=g,
        ),
        HighLowObservation.try_create(g, g, g, g),
        DeclaredBudget.try_create(
            per_update_cost_ceiling_ns=g,
            object_set_size_ceiling=g,
            scan_window_ceiling=g,
            synchronous_available=g,
        ),
        SwingPointFamily.create(left=g, right=g, confirmation_delay_bound=g),
    ]


@settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
@given(g=_garbage)
def test_l1_002_no_public_callable_raises_on_arbitrary_input(g: object) -> None:
    for result in _public_calls(g):
        # A CT-17 boundary always succeeds or returns a typed refusal — never raises.
        assert is_ok(result) or is_refusal(result), f"non-Result return: {result!r}"


def test_l1_002_swing_family_methods_also_return_results() -> None:
    fam = H.swing_family()
    assert is_refusal(fam.detect(123))
    assert is_refusal(fam.detect("not-a-series"))
    assert is_refusal(fam.confirmation_for(object(), []))


# ---------------------------------------------------------------------------
# QA-E09-L1-003 — identity fields distinguish fingerprints; no null in identity
# ---------------------------------------------------------------------------


def _walk_values(content: object) -> list[object]:
    out: list[object] = []
    if isinstance(content, dict):
        for value in content.values():
            out.extend(_walk_values(value))
    elif isinstance(content, (list, tuple)):
        for item in content:
            out.extend(_walk_values(item))
    else:
        out.append(content)
    return out


@given(
    field=st.sampled_from(["observed_at", "param", "anchor_low", "version"]),
    a=st.integers(min_value=0, max_value=6),
    b=st.integers(min_value=0, max_value=6),
)
def test_l1_003_distinct_identity_field_yields_distinct_fingerprint(
    field: str, a: int, b: int
) -> None:
    if a == b:
        b = b + 1  # force two DISTINCT identity values
    base = _obj_varying(field, a)
    other = _obj_varying(field, b)
    # Two objects differing in exactly one identity field are two distinct facts.
    assert H.fp(base) != H.fp(other)


def _obj_varying(field: str, value: int) -> StructureObject:
    if field == "observed_at":
        return H.minted(observed_min=2 + value)
    if field == "param":
        return H.minted(parameters={"pivot_tolerance": H.rational(1, value + 2)})
    if field == "anchor_low":
        return H.minted(anc=H.anchor(low=107_900 + value))
    # version
    return H.minted(fam=H.family(version=value + 1))


def test_l1_003_each_evidence_class_is_a_distinct_fact() -> None:
    # Evidence class is a declared identity field: the three classes fingerprint distinctly.
    fingerprints = {
        cls: H.fp(H.minted(evidence_class=cls)) for cls in EvidenceClass
    }
    assert len(set(fingerprints.values())) == len(EvidenceClass)


@given(bound=st.one_of(st.none(), st.integers(min_value=0, max_value=5)))
def test_l1_003_no_null_ever_appears_in_identity_content(bound: int | None) -> None:
    obj = H.minted()
    assert None not in _walk_values(obj.fp1_identity())
    # An unbounded confirmation delay is the explicit "unbounded" token, never a null.
    rule = H.ok(ConfirmationRule.try_create("r", confirmation_delay_bound=bound))
    values = _walk_values(rule.fp1_identity())
    assert None not in values
    if bound is None:
        assert "unbounded" in values


# ---------------------------------------------------------------------------
# QA-E09-L1-004 — exactness: no binary float on the parameter/identity path
# ---------------------------------------------------------------------------


def _contains_float(content: object) -> bool:
    return any(isinstance(v, float) for v in _walk_values(content))


@given(f=st.floats(allow_nan=False, allow_infinity=False))
def test_l1_004_a_binary_float_parameter_is_refused(f: float) -> None:
    result = H.mint(parameters={"tolerance": f})
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "parameters"


@given(
    num=st.integers(min_value=-9, max_value=9),
    den=st.integers(min_value=1, max_value=9),
)
def test_l1_004_exact_rational_parameters_carry_no_float_in_identity(num: int, den: int) -> None:
    obj = H.minted(parameters={"tolerance": H.rational(num, den)})
    assert not _contains_float(obj.fp1_identity()), "a binary float leaked into fp1 identity"


@given(bad=st.floats(allow_nan=False, allow_infinity=False))
def test_l1_004_a_float_anchor_bound_is_refused(bad: float) -> None:
    # A Price is a scaled integer; a raw float in a price-bound position is refused.
    result = AnchorSpan.try_create(H.inst(0), H.inst(1), bad, H.price(108_500))
    assert isinstance(result, TypedRefusal)
    assert result.context["field"] == "low"
