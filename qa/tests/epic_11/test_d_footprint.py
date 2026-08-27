"""Epic 11 / Story 11.4 — footprint, producer templates, horizon (FR-047, QL-4, R-011).

D1 total single-valued resolution; D2 omitted AD-22 field -> Layer-1 refusal;
D3 transitive-union completeness reporting; D4 derived horizon (no hand window);
D5 nested stream set; D6 order-stable coercion. ``footprint/_coerce.py`` behaviour
is pinned BY REQUIREMENT and reached only through public surfaces
(mint_producer_template / resolve_template / mint_footprint), never a _helper.
"""

from __future__ import annotations

import helpers as H
from hypothesis import given, settings
from hypothesis import strategies as st

from qmf.core.exact import UnitKind
from qml.footprint import (
    AD22_IDENTITY_FIELDS,
    Footprint,
    ProducerBinding,
    derive_horizon,
    mint_footprint,
    mint_producer_template,
    report_completeness,
    resolve_template,
)


# --- D1 total single-valued resolution --------------------------------------


def test_d1_resolution_is_deterministic_and_order_independent() -> None:
    """D1 (11.4 AC1, R-011): one assignment -> one deterministic producer fingerprint.

    Extra/unused assignment keys and key insertion order never fork identity.
    Counter-case: two orderings of the same value set producing different fps.
    """
    template = H.unwrap(mint_producer_template(H.template_body()), "template")
    a = H.unwrap(resolve_template(template, {"sma_period": H.exact(20)}), "resolve-a")
    b = H.unwrap(
        resolve_template(template, {"unused": H.exact(9), "sma_period": H.exact(20)}), "resolve-b"
    )
    fp_a = H.unwrap(a.fingerprint_content(), "fp-a")
    fp_b = H.unwrap(b.fingerprint_content(), "fp-b")
    assert fp_a == fp_b
    assert fp_a.value.startswith("fp1:sha256:")


def test_d1_resolution_is_total_missing_space_bound_value_refuses() -> None:
    """D1 (totality): a space-bound parameter with no assignment value is invalid input.

    Counter-case: a silent default / silent fingerprint on a missing value.
    """
    template = H.unwrap(mint_producer_template(H.template_body()), "template")
    refused = resolve_template(template, {})
    assert H.category_of(refused) == "invalid input"


@settings(max_examples=40, deadline=None)
@given(p=st.integers(min_value=1, max_value=500), q=st.integers(min_value=1, max_value=500))
def test_d1_resolution_is_single_valued_injective_on_value(p: int, q: int) -> None:
    """D1 (single-valued): distinct space-bound values give distinct producer fps; equal give equal.

    Counter-case: p != q yet identical fingerprints (a value dropped from identity).
    """
    template = H.unwrap(mint_producer_template(H.template_body()), "template")
    fp_p = H.unwrap(
        H.unwrap(resolve_template(template, {"sma_period": H.exact(p)}), "rp").fingerprint_content(),
        "fp_p",
    )
    fp_q = H.unwrap(
        H.unwrap(resolve_template(template, {"sma_period": H.exact(q)}), "rq").fingerprint_content(),
        "fp_q",
    )
    assert (fp_p == fp_q) == (p == q)


# --- D2 omitted AD-22 identity field -> Layer-1 refusal (R-011 / R-009) ------


def test_d2_omitted_ad22_identity_field_is_layer1_registration_refusal() -> None:
    """D2 (11.4 AC2, R-011/R-009): a template missing any AD-22 identity field refuses.

    Every AD-22 field is required; an omission is an invalid-input Layer-1
    registration refusal (journaled). Counter-case: a template missing warm_up (or
    any other AD-22 field) still minting.
    """
    for field in AD22_IDENTITY_FIELDS:
        body = H.template_body()
        del body[field]
        refused = mint_producer_template(body)
        assert H.category_of(refused) == "invalid input", f"{field} omission not refused"
        assert refused.context.get("layer") == 1, f"{field} omission not marked Layer-1"


# --- D3 transitive-union completeness reporting -----------------------------


def test_d3_completeness_reports_set_equality_never_refuses() -> None:
    """D3 (11.4 AC3): the module REPORTS whether the footprint set equals the union.

    Reporting only (Epic 12's linter turns a report into a refusal). Counter-case:
    a report claiming complete when a union member is missing, or refusing outright.
    """
    template = H.unwrap(mint_producer_template(H.template_body()), "template")
    binding = H.unwrap(ProducerBinding.try_create(template), "binding")
    footprint = H.unwrap(mint_footprint([H.stream()], [H.calendar()], [binding]), "footprint")

    complete = H.unwrap(report_completeness(footprint, [binding], bot_direct=()), "complete")
    assert complete.complete is True
    assert complete.missing == () and complete.extra == ()

    # A union member absent from the footprint -> incomplete, reported as missing.
    other = H.unwrap(ProducerBinding.try_create(H.pinned_fp("other-producer")), "other")
    incomplete = H.unwrap(report_completeness(footprint, [binding, other], bot_direct=()), "inc")
    assert incomplete.complete is False
    assert incomplete.missing != ()

    # A footprint carrying a binding absent from the union -> extra, still a report.
    empty_union = H.unwrap(report_completeness(footprint, (), bot_direct=()), "extra")
    assert empty_union.complete is False
    assert empty_union.extra != ()


# --- D4 derived horizon (no hand-declared window) ---------------------------


def test_d4_horizon_is_derived_from_the_resolved_chain() -> None:
    """D4 (11.4 AC4): the warm-up/embargo horizon is derived from the resolved chain.

    Counter-case: a derived warm-up that ignores the chain's declared warm_up.
    """
    template = H.unwrap(mint_producer_template(H.template_body(warm_up=20)), "template")
    resolved = H.unwrap(resolve_template(template, {"sma_period": H.exact(20)}), "resolved")
    horizon = H.unwrap(derive_horizon((resolved,)), "horizon")
    assert horizon.warm_up == 20
    # A different chain warm_up derives a different horizon (non-vacuity).
    template2 = H.unwrap(mint_producer_template(H.template_body(warm_up=50)), "template2")
    resolved2 = H.unwrap(resolve_template(template2, {"sma_period": H.exact(20)}), "resolved2")
    assert H.unwrap(derive_horizon((resolved2,)), "horizon2").warm_up == 50


def test_d4_hand_declared_window_field_on_declaration_is_refused() -> None:
    """D4: there is no second, hand-declared window field on the declaration.

    Counter-case: a footprint accepting a hand-declared warm_up_horizon/embargo window.
    """
    for window_field in ("warm_up_horizon", "embargo_window", "horizon"):
        refused = Footprint.try_from_mapping(
            {
                "stream_set": [H.stream()],
                "required_calendars": [H.calendar()],
                "producer_bindings": [H.pinned_fp("sma")],
                window_field: 99,
            }
        )
        assert H.category_of(refused) == "invalid input", f"{window_field} accepted"


# --- D5 nested stream set ----------------------------------------------------


def test_d5_stream_set_is_nested_and_missing_stream_set_refuses() -> None:
    """D5 (11.4 AC5): the stream set is nested inside the footprint, the one locus.

    Counter-case: a missing stream_set silently admitted.
    """
    footprint = H.unwrap(mint_footprint([H.stream()], [H.calendar()], [H.pinned_fp("sma")]), "fp")
    manifest = dict(footprint.host_manifest())
    assert "stream_set" in manifest
    assert manifest["stream_set"][0]["stream_role"] == "trading"

    missing = Footprint.try_from_mapping(
        {"required_calendars": [H.calendar()], "producer_bindings": [H.pinned_fp("sma")]}
    )
    assert H.category_of(missing) == "invalid input"


def test_d5_try_create_refuses_a_second_top_level_field() -> None:
    """D5 (11.4 AC5): the positional footprint factory refuses a second top-level field.

    Counter-case: an extra top-level footprint field being admitted.
    """
    extra = Footprint.try_create(
        [H.stream()], [H.calendar()], [H.pinned_fp("sma")], streams=[H.stream()]
    )
    assert H.category_of(extra) == "invalid input"


def test_d5_try_from_mapping_refuses_a_second_top_level_field() -> None:
    """D5 (11.4 AC5): the mapping footprint factory must ALSO refuse a second top-level field.

    'never a second top-level field' is a whole-declaration guarantee. Counter-case:
    a second `streams` top-level field being silently ignored rather than refused.
    """
    extra = Footprint.try_from_mapping(
        {
            "stream_set": [H.stream()],
            "required_calendars": [H.calendar()],
            "producer_bindings": [H.pinned_fp("sma")],
            "streams": [H.stream()],
        }
    )
    assert H.category_of(extra) == "invalid input"


# --- D6 order-stable coercion (R-011) ---------------------------------------


def test_d6_coercion_is_order_stable_across_assignment_orderings() -> None:
    """D6 (11.4 AC1, R-011): equal inputs coerce to the same fingerprint, any input order.

    The _coerce space-bound substitution is deterministic and order-stable, reached
    through resolve_template. Counter-case: two orderings of one value set producing
    different coerced CT-16 configurations / fingerprints.
    """
    body = H.template_body(space_bound={"period": "sma_period", "smoothing": "sma_smooth"})
    template = H.unwrap(mint_producer_template(body), "template")
    forward = {"sma_period": H.exact(20), "sma_smooth": H.exact(3)}
    reverse = {"sma_smooth": H.exact(3), "sma_period": H.exact(20)}
    fp_forward = H.unwrap(
        H.unwrap(resolve_template(template, forward), "rf").fingerprint_content(), "ff"
    )
    fp_reverse = H.unwrap(
        H.unwrap(resolve_template(template, reverse), "rr").fingerprint_content(), "fr"
    )
    assert fp_forward == fp_reverse
    # Non-vacuity: a different value for one slot forks the coerced identity.
    changed = {"sma_period": H.exact(21), "sma_smooth": H.exact(3)}
    fp_changed = H.unwrap(
        H.unwrap(resolve_template(template, changed), "rc").fingerprint_content(), "fc"
    )
    assert fp_changed != fp_forward
