"""Epic 11 — cross-cutting gates X1-X4 (R-009 register, R-011 aggregate, AD-7 float-ban).

X1/X2 collect the categories qml's authoring doors actually emit and assert they
are all on-register and exactly the four the CT-33/CT-34 contracts declare;
X3 re-affirms the footprint/_coerce.py refusals are requirement-anchored;
X4 proves no binary float enters any qml identity field.
"""

from __future__ import annotations

import helpers as H

from qmf.core.exact import UnitKind
from qmf.core.refusal import RefusalCategory, is_refusal
from qml.declaration import mint_bot_definition, mint_confluence
from qml.declaration.versioning import continues_performance_edge
from qml.families import resolve_family_at_layer1, validate_family_body
from qml.footprint import derive_horizon, mint_producer_template, resolve_template
from qml.footprint.template import ProducerTemplate
from qml.logic import resolve_logic_at_layer1


def _authoring_refusals() -> list[object]:
    """A battery of real refusals across every qml CT-33/CT-34/11.7 authoring door."""
    refusals: list[object] = []
    # invalid input
    refusals.append(mint_confluence([]))  # zero-leg confluence
    refusals.append(mint_bot_definition(H.bot_payload(strategy_family_id=[])))  # cardinality-zero
    refusals.append(mint_producer_template({k: v for k, v in H.template_body().items() if k != "warm_up"}))
    # unsupported capability (unknown kind format version)
    refusals.append(mint_confluence([{"role": "level", "producer_binding": H.pinned("z")}], format_version=2))
    refusals.append(mint_bot_definition(H.bot_payload(), format_version=2))
    # unavailable dependency
    refusals.append(resolve_family_at_layer1("missing", ()))
    refusals.append(
        resolve_logic_at_layer1(
            {"distribution": "x", "distribution_version": "1", "source_manifest": "fp1:sha256:" + "0" * 64},
            (),
        )
    )
    # policy rejection
    refusals.append(validate_family_body({"family_id": "f", "permitted_timeframes": ["M1"]}))
    refusals.append(continues_performance_edge(child=None, parent=None, writer=None, human_signed=False))
    return [r for r in refusals if is_refusal(r)]


def test_x1_every_authoring_refusal_is_on_the_seven_category_register() -> None:
    """X1 (R-009): every door-reachable typed refusal is a member of the seven-category register.

    Counter-case: any qml authoring path emitting a category outside the register.
    """
    emitted = {r.category.value for r in _authoring_refusals()}
    assert emitted, "no refusals collected — the battery is vacuous"
    assert emitted <= H.SEVEN_REGISTER
    # Every emitted value is a genuine RefusalCategory member (typed, not raw prose).
    for value in emitted:
        assert value in {member.value for member in RefusalCategory}


def test_x2_qml_authoring_paths_emit_only_the_four_declared_categories() -> None:
    """X2 (R-009 corollary): qml's authoring doors emit only the four contract-declared categories.

    Never stale evidence / transient venue failure / storage failure. Counter-case:
    a qml authoring door emitting an off-authoring category.
    """
    emitted = {r.category.value for r in _authoring_refusals()}
    assert emitted <= H.QML_AUTHORING_CATEGORIES
    assert emitted.isdisjoint(H.OFF_AUTHORING_CATEGORIES)
    # The battery actually exercises all four declared categories (non-vacuity).
    assert emitted == H.QML_AUTHORING_CATEGORIES


# --- X3 R-011 aggregate: _coerce refusals are requirement-anchored -----------


def test_x3_coerce_refusals_are_requirement_anchored_invalid_input() -> None:
    """X3 (R-011): footprint/_coerce.py refusals are pinned by requirement, each invalid input.

    Reached only through public template/leg surfaces. Each maps to a named
    requirement: AD-22 field completeness, exact-rational values, calendar identity,
    bar-spec identity. Counter-case: a _coerce path admitting a malformed value.
    """
    body = H.template_body()
    # AD-22 identity field completeness (D2): drop a required field.
    assert H.category_of(mint_producer_template({k: v for k, v in body.items() if k != "inputs"})) == "invalid input"
    # exact-rational leg parameter (AD-7): a float never enters coercion.
    assert (
        H.category_of(
            mint_confluence(
                [{"role": "level", "producer_binding": H.pinned("z"), "declared_parameters": {"p": 0.5}}]
            )
        )
        == "invalid input"
    )
    # calendar identity coercion: a malformed calendar requirement.
    assert H.category_of(mint_producer_template(H.template_body(calendar_requirements=["not-a-calendar"]))) == "invalid input"
    # bar-spec identity coercion: a bare string that is not an fp reference.
    bad_bar = H.template_body()
    bad_bar["inputs"] = [
        {
            "name": "close",
            "source": {"kind": "instrument", "venue": "v", "symbol": "S"},
            "bar_spec": "1m",
            "channel_kind": "exact-price",
            "quote_side": "mid",
        }
    ]
    assert H.category_of(mint_producer_template(bad_bar)) == "invalid input"


# --- X4 AD-7 float-ban -------------------------------------------------------


def test_x4_no_binary_float_enters_a_parameter_identity_field() -> None:
    """X4 (AD-7): a binary float in default/step/bounds is invalid input, never coerced silently.

    Counter-case: a float default admitted into a Bot's parameter space.
    """
    float_default = mint_bot_definition(
        H.bot_payload(
            parameter_space=[
                {
                    "name": "ratio",
                    "type": "exact rational",
                    "bounds": {"min": H.exact(0, 1, UnitKind.DIMENSIONLESS_RATIO), "max": H.exact(2, 1, UnitKind.DIMENSIONLESS_RATIO)},
                    "step": H.exact(1, 2, UnitKind.DIMENSIONLESS_RATIO),
                    "default": 0.5,  # binary float
                    "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
                    "ui": "ui-editable",
                }
            ]
        )
    )
    assert H.category_of(float_default) == "invalid input"


def test_x4_no_binary_float_enters_a_leg_declared_parameter() -> None:
    """X4 (AD-7): a binary float in a leg's declared_parameters is invalid input."""
    refused = mint_confluence(
        [{"role": "level", "producer_binding": H.pinned("z"), "declared_parameters": {"lookback": 0.5}}]
    )
    assert H.category_of(refused) == "invalid input"


def test_x4_no_binary_float_enters_a_template_fixed_parameter() -> None:
    """X4 (AD-7): a binary float in a producer template's fixed parameters is invalid input."""
    refused = ProducerTemplate.try_create(H.template_body(fixed_parameters={"k": 0.5}))
    assert H.category_of(refused) == "invalid input"
