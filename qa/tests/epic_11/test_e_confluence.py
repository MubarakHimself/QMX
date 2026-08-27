"""Epic 11 / Story 11.5 — CT-34 confluence kind (FR-049, CT-34, QL-5, DEC-0185).

E1 role vocabulary + at-least-one leg + never-bounded; E2 binding/child/both leg
law; E3 fingerprint-ascending default; E4 content identity / reuse; E5 refusals
(R-009); E6 counts-never-bounded (Hypothesis over N, M, depth).
"""

from __future__ import annotations

import helpers as H
from hypothesis import given, settings
from hypothesis import strategies as st

from qml.declaration import mint_confluence, resolve_confluence_at_layer1


# --- E1 role vocabulary, at-least-one leg, mandatory role --------------------


def test_e1_each_role_in_vocabulary_validates_and_zero_legs_refuses() -> None:
    """E1 (11.5 AC1): each closed-vocabulary role validates; a zero-leg confluence refuses.

    Counter-case: a zero-leg confluence minting, or a valid role being refused.
    """
    for role in ("level", "trigger", "confirmation", "filter"):
        built = H.unwrap(
            mint_confluence([{"role": role, "producer_binding": H.pinned(f"p-{role}")}]),
            f"role {role}",
        )
        assert built.legs[0].role.value == role
    zero = mint_confluence([])
    assert H.category_of(zero) == "invalid input"


def test_e1_leg_role_is_mandatory() -> None:
    """E1: a leg with no role is invalid input (role always mandatory).

    Counter-case: a role-less leg minting.
    """
    refused = mint_confluence([{"producer_binding": H.pinned("z")}])
    assert H.category_of(refused) == "invalid input"


# --- E2 binding and/or child cite (DEC-0185) --------------------------------


def test_e2_leg_carries_binding_child_or_both_at_least_one_required() -> None:
    """E2 (11.5 AC2, DEC-0185): a leg carries a producer binding, a child cite, or BOTH.

    The 'both' arm is explicitly legal (AD-17 foreclosing-cardinality trap).
    Counter-case: a leg carrying neither being accepted, or a 'both' leg refused.
    """
    child = H.unwrap(mint_confluence([{"role": "level", "producer_binding": H.pinned("c")}]), "c")
    child_fp = H.unwrap(child.fingerprint_content(), "child fp")

    binding_only = H.unwrap(
        mint_confluence([{"role": "level", "producer_binding": H.pinned("z")}]), "binding only"
    )
    assert binding_only.legs[0].producer_binding is not None
    assert binding_only.legs[0].confluence_ref is None

    child_only = H.unwrap(mint_confluence([{"role": "trigger", "confluence_ref": child_fp}]), "child")
    assert child_only.legs[0].producer_binding is None
    assert child_only.legs[0].confluence_ref == child_fp

    both = H.unwrap(
        mint_confluence(
            [{"role": "trigger", "producer_binding": H.pinned("b"), "confluence_ref": child_fp}]
        ),
        "both",
    )
    assert both.legs[0].producer_binding is not None
    assert both.legs[0].confluence_ref == child_fp

    neither = mint_confluence([{"role": "level"}])
    assert H.category_of(neither) == "invalid input"


# --- E3 fingerprint-ascending default ---------------------------------------


def test_e3_default_ordering_is_fingerprint_ascending_ordinals_excluded() -> None:
    """E3 (11.5 AC3): default legs order fingerprint-ascending; display ordinals excluded.

    Reordered input and different display ordinals give one fp; declaring
    order-significance forks it. Counter-case: a display ordinal entering the
    default identity.
    """
    legs_a = [
        {"role": "trigger", "producer_binding": H.pinned("zzz"), "display_ordinal": 0},
        {"role": "level", "producer_binding": H.pinned("aaa"), "display_ordinal": 1},
    ]
    legs_b = [
        {"role": "level", "producer_binding": H.pinned("aaa"), "display_ordinal": 7},
        {"role": "trigger", "producer_binding": H.pinned("zzz"), "display_ordinal": 3},
    ]
    fp_a = H.unwrap(H.unwrap(mint_confluence(legs_a), "a").fingerprint_content(), "fp a")
    fp_b = H.unwrap(H.unwrap(mint_confluence(legs_b), "b").fingerprint_content(), "fp b")
    assert fp_a == fp_b  # reorder + different ordinals -> same identity
    default = H.unwrap(mint_confluence(legs_a), "default")
    assert "display_ordinal" not in default.identity_legs()[0]
    assert "order_significance" not in default.body()
    # Opt-in order-significance enters the fingerprint.
    opted = H.unwrap(mint_confluence(legs_a, order_significance=True), "opted")
    assert H.unwrap(opted.fingerprint_content(), "opted fp") != fp_a


# --- E4 content identity / reuse --------------------------------------------


def test_e4_reuse_is_content_identity_any_change_mints_new_fingerprint() -> None:
    """E4 (11.5 AC4): identical content reuses one fp; any semantic change mints a new one.

    Counter-case: a changed role / binding / leg parameter / order-significance
    that leaves the fingerprint unchanged.
    """
    base_legs = [
        {"role": "level", "producer_binding": H.pinned("zone")},
        {"role": "trigger", "producer_binding": H.pinned("break")},
    ]
    fp = H.unwrap(H.unwrap(mint_confluence(base_legs), "base").fingerprint_content(), "fp")
    # Reuse: same content, reversed input -> same fp.
    reuse = H.unwrap(mint_confluence(list(reversed(base_legs))), "reuse")
    assert H.unwrap(reuse.fingerprint_content(), "reuse fp") == fp

    changed_role = H.unwrap(
        mint_confluence(
            [
                {"role": "filter", "producer_binding": H.pinned("zone")},
                {"role": "trigger", "producer_binding": H.pinned("break")},
            ]
        ),
        "changed role",
    )
    assert H.unwrap(changed_role.fingerprint_content(), "cr fp") != fp

    changed_binding = H.unwrap(
        mint_confluence(
            [
                {"role": "level", "producer_binding": H.pinned("zone-2")},
                {"role": "trigger", "producer_binding": H.pinned("break")},
            ]
        ),
        "changed binding",
    )
    assert H.unwrap(changed_binding.fingerprint_content(), "cb fp") != fp

    changed_param = H.unwrap(
        mint_confluence(
            [
                {
                    "role": "level",
                    "producer_binding": H.pinned("zone"),
                    "declared_parameters": {"lookback": H.exact(14)},
                },
                {"role": "trigger", "producer_binding": H.pinned("break")},
            ]
        ),
        "changed param",
    )
    assert H.unwrap(changed_param.fingerprint_content(), "cp fp") != fp

    order_sig = H.unwrap(mint_confluence(base_legs, order_significance=True), "order sig")
    assert H.unwrap(order_sig.fingerprint_content(), "os fp") != fp


# --- E5 refusals (R-009) ----------------------------------------------------


def test_e5_off_vocabulary_role_and_missing_cite_are_invalid_input() -> None:
    """E5 (11.5 AC5, R-009): an off-vocabulary role or a cite-less leg is invalid input.

    Counter-case: role 'feature' (a retired concept) being admitted.
    """
    bad_role = mint_confluence([{"role": "feature", "producer_binding": H.pinned("sma")}])
    assert H.category_of(bad_role) == "invalid input"
    condition = mint_confluence(
        [{"role": "filter", "producer_binding": H.pinned("sma"), "when": "close > sma"}]
    )
    assert H.category_of(condition) == "invalid input"


def test_e5_unresolvable_producer_or_child_is_unavailable_dependency() -> None:
    """E5 (R-009): an unresolvable producer fp or cited child confluence is unavailable dependency.

    Counter-case: an unresolvable producer silently resolving to Ok.
    """
    from qmf.core.refusal import is_ok

    binding = H.pinned("sma")
    confluence = H.unwrap(mint_confluence([{"role": "level", "producer_binding": binding}]), "cf")
    ok = resolve_confluence_at_layer1(confluence, (), producer_catalog=[binding])
    assert is_ok(ok)  # sanity: the resolvable path succeeds
    missing_producer = resolve_confluence_at_layer1(confluence, (), producer_catalog=())
    assert H.category_of(missing_producer) == "unavailable dependency"

    from qmf.core.fingerprint import fingerprint

    missing_child_fp = H.unwrap(fingerprint({"class": "missing-child"}), "child fp")
    parent = H.unwrap(
        mint_confluence(
            [{"role": "trigger", "producer_binding": binding, "confluence_ref": missing_child_fp}]
        ),
        "parent",
    )
    missing_child = resolve_confluence_at_layer1(parent, (), producer_catalog=[binding])
    assert H.category_of(missing_child) == "unavailable dependency"


# --- E6 counts never bounded (DEC-0185) -------------------------------------


@settings(max_examples=25, deadline=None)
@given(n=st.integers(min_value=1, max_value=40), m=st.integers(min_value=0, max_value=40))
def test_e6_leg_counts_are_never_bounded(n: int, m: int) -> None:
    """E6 (11.5 AC1, DEC-0185): N level legs + M trigger legs always validate; no ceiling.

    Counter-case: a count ceiling refusing at some N or M.
    """
    legs = [{"role": "level", "producer_binding": H.pinned(f"lvl-{i}")} for i in range(n)]
    legs += [{"role": "trigger", "producer_binding": H.pinned(f"trg-{j}")} for j in range(m)]
    built = mint_confluence(legs)
    assert len(H.unwrap(built, "many legs").legs) == n + m


@settings(max_examples=15, deadline=None)
@given(depth=st.integers(min_value=1, max_value=12))
def test_e6_nesting_depth_is_never_bounded(depth: int) -> None:
    """E6 (DEC-0185): confluence composition nests to any depth; no depth ceiling.

    Counter-case: a nesting-depth ceiling refusing at some depth.
    """
    child = H.unwrap(mint_confluence([{"role": "level", "producer_binding": H.pinned("leaf")}]), "leaf")
    for level in range(depth):
        child_fp = H.unwrap(child.fingerprint_content(), "child fp")
        child = H.unwrap(
            mint_confluence(
                [{"role": "trigger", "producer_binding": H.pinned(f"n-{level}"), "confluence_ref": child_fp}]
            ),
            f"nest-{level}",
        )
    assert child.legs[0].confluence_ref is not None
