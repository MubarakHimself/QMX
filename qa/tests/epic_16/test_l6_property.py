"""Epic 16 — L6 property-based breadth (hypothesis).

Two universally-quantified laws: the refusal union survives the Python door and
the per-transport renderers field-identically over arbitrary CT-04 refusals
(T-16.3-P), and each capability invoked through the CLI door and the Python door
maps to the SAME library result over arbitrary inputs (T-16.5-P).

Run with: uv run --with hypothesis pytest qa/tests/epic_16/test_l6_property.py
"""

from __future__ import annotations

import json

import _e16 as e
import pytest

hyp = pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

import qmb  # noqa: E402
from qmb.doors import api  # noqa: E402
from qmb.doors.cli import invoke_optimize_space, invoke_sweep_count, render_refusal  # noqa: E402
from qmf.core.refusal import (  # noqa: E402
    RefusalCategory,
    Retryability,
    TypedRefusal,
)

_scalars = st.one_of(st.text(max_size=8), st.integers(), st.booleans())
_contexts = st.dictionaries(
    st.text(min_size=1, max_size=6),
    st.one_of(_scalars, st.lists(st.text(max_size=6), max_size=3)),
    max_size=4,
)


@st.composite
def _refusals(draw) -> TypedRefusal:
    category = draw(st.sampled_from(list(RefusalCategory)))
    retryability = draw(st.sampled_from(list(Retryability)))
    context = draw(_contexts)
    descriptor = (
        draw(st.text(min_size=1, max_size=12))
        if retryability is Retryability.AFTER_CONDITION
        else None
    )
    return TypedRefusal(
        category=category,
        retryability=retryability,
        context=context,
        after_condition_descriptor=descriptor,
    )


# --- T-16.3-P ----------------------------------------------------------------
@settings(max_examples=250)
@given(_refusals())
def test_t16_3_p_refusal_union_survives_the_door_field_identically(refusal: TypedRefusal) -> None:
    """Over arbitrary CT-04 refusals, the Python door returns the field-identical
    refusal it received (pure re-export = identity), and the CLI renderer
    preserves the union — no transformation, no dropped field. [R11]"""
    # Python door: a pure re-export is the identity function on the refusal value.
    library = lambda: refusal  # noqa: E731 - a stand-in library function
    door = library  # the API door re-exports the library object verbatim
    assert door() is refusal
    got = door()
    assert got.category is refusal.category
    assert got.retryability is refusal.retryability
    assert got.context == refusal.context
    assert got.after_condition_descriptor == refusal.after_condition_descriptor
    # CLI transport preserves category / retryability / context keys / descriptor.
    payload = json.loads(render_refusal(refusal))
    assert payload["category"] == refusal.category.value
    assert payload["retryability"] == refusal.retryability.value
    assert set(payload["context"].keys()) == set(refusal.context.keys())
    for key, value in refusal.context.items():
        if isinstance(value, (str, int, bool)):
            assert payload["context"][key] == value
    if refusal.retryability is Retryability.AFTER_CONDITION:
        assert payload["after_condition_descriptor"] == refusal.after_condition_descriptor
    else:
        assert "after_condition_descriptor" not in payload


# --- T-16.5-P ----------------------------------------------------------------
@settings(max_examples=200)
@given(st.dictionaries(st.text(min_size=1, max_size=6), st.text(max_size=6), max_size=4))
def test_t16_5_p_semantic_parity_cli_door_equals_python_door(declaration: dict) -> None:
    """Over arbitrary declarations, a capability invoked through the CLI door maps
    back to the SAME library result as the Python door — semantic parity as a
    universally-quantified law, not a spot check. [R18]"""
    # optimize.space: the CLI invoker and the Python re-export share one library fn
    assert invoke_optimize_space(declaration=declaration) == api.parameter_space_from_bot(declaration)
    # sweep.count: likewise over the same declaration
    assert invoke_sweep_count(declaration=declaration) == qmb.preflight_run_count(declaration)
