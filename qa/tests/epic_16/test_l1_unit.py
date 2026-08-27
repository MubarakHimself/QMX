"""Epic 16 — L1 targeted pure units.

The refusal-rendering pure function (shape, isolated from CLI wiring) and the two
capability-enumeration mechanisms (pure functions of the door structure, so the
parity test can never smuggle in a hand-list).

Tests: T-16.2-render [R6] · T-16.5-enumCLI [R18 mechanism]
       · T-16.5-enumAPI [R18 mechanism].
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import _e16 as e
import click

from qmb.doors.cli.render import render_refusal
from qmf.core.refusal import RefusalCategory, Retryability


# --- T-16.2-render -----------------------------------------------------------
def test_t16_2_render_maps_refusal_to_machine_readable_json_shape() -> None:
    """render_refusal maps any CT-04 TypedRefusal to a JSON object carrying
    category (∈ seven), context (present, non-null), retryability (∈ three) — and
    the after-condition descriptor exactly when retryability is after-condition. [R6]
    """
    for refusal in e.refusal_corpus():
        text = render_refusal(refusal)
        payload = json.loads(text)
        assert isinstance(payload, dict)
        # the three required fields are present and machine-readable
        assert payload["category"] == refusal.category.value
        assert payload["category"] in e.SEVEN_CATEGORY_VALUES
        assert payload["retryability"] == refusal.retryability.value
        assert payload["retryability"] in e.RETRYABILITY_VALUES
        assert "context" in payload and payload["context"] is not None
        assert isinstance(payload["context"], (dict, list, str, int, bool))
        # counter-case that must FAIL a correct renderer: dropping the descriptor
        if refusal.retryability is Retryability.AFTER_CONDITION:
            assert payload.get("after_condition_descriptor") == refusal.after_condition_descriptor
        else:
            assert "after_condition_descriptor" not in payload


def test_t16_2_render_emits_canonical_category_strings_not_enum_names() -> None:
    """The rendered category is CT-04's canonical spaced string (e.g. 'invalid
    input'), not the Python enum member name ('INVALID_INPUT'). [R6]"""
    payload = json.loads(
        render_refusal(e.refusal(RefusalCategory.INVALID_INPUT, context={"field": "x"}))
    )
    assert payload["category"] == "invalid input"
    assert payload["category"] != "INVALID_INPUT"
    nested = json.loads(
        render_refusal(
            e.refusal(
                RefusalCategory.UNAVAILABLE_DEPENDENCY,
                context={"missing": ["port", "book_fragment"]},
            )
        )
    )
    assert nested["context"]["missing"] == ["port", "book_fragment"]


# --- T-16.5-enumCLI ----------------------------------------------------------
def test_t16_5_enumcli_is_a_pure_function_of_the_click_tree() -> None:
    """The CLI-capability enumeration walks a click Group to its leaves and is a
    pure function of the tree — the same tree yields the same surface, and a
    subcommand added to the tree appears (so no hand-list can hide). [R18 mechanism]
    """

    @click.group(name="probe")
    def probe() -> None:
        ...

    @probe.group("alpha")
    def alpha() -> None:
        ...

    @alpha.command("one")
    def one() -> None:
        ...

    @alpha.command("two")
    def two() -> None:
        ...

    @probe.command("solo")
    def solo() -> None:
        ...

    leaves = e.derive_cli_leaves(probe)
    assert leaves == {"alpha.one", "alpha.two", "solo"}
    # purity: same tree -> same surface
    assert e.derive_cli_leaves(probe) == leaves

    # teeth: a leaf added to the tree changes the derived surface
    @alpha.command("three")
    def three() -> None:
        ...

    assert e.derive_cli_leaves(probe) == {"alpha.one", "alpha.two", "alpha.three", "solo"}


# --- T-16.5-enumAPI ----------------------------------------------------------
def test_t16_5_enumapi_is_a_pure_function_of_the_public_surface() -> None:
    """The API-capability enumeration introspects a module's public re-export
    surface (names in __all__ that are identity-equal to a library object). It is
    a pure function of that surface — it reflects exactly the re-exported objects. [R18 mechanism]
    """

    def _derive(module: object, library: object) -> set[str]:
        out: set[str] = set()
        for name in getattr(module, "__all__", ()):
            if (
                hasattr(module, name)
                and hasattr(library, name)
                and getattr(module, name) is getattr(library, name)
            ):
                out.add(name)
        return out

    def cap_a() -> int:
        return 1

    def cap_b() -> int:
        return 2

    library = SimpleNamespace(cap_a=cap_a, cap_b=cap_b, __all__=["cap_a", "cap_b"])
    # a door that re-exports both, plus one door-local extra that is NOT a re-export
    door = SimpleNamespace(cap_a=cap_a, cap_b=cap_b, door_only=object(), __all__=["cap_a", "cap_b", "door_only"])
    assert _derive(door, library) == {"cap_a", "cap_b"}
    # teeth: a re-export replaced by a door-local reimplementation drops out
    door_drift = SimpleNamespace(cap_a=cap_a, cap_b=lambda: 2, __all__=["cap_a", "cap_b"])
    assert _derive(door_drift, library) == {"cap_a"}


def test_t16_5_enumapi_reflects_the_real_api_door_surface() -> None:
    """The real API door surface is non-empty and every derived name is a genuine
    library re-export (identity-equal to qmb.<name>). [R18 mechanism]"""
    import qmb
    from qmb.doors import api

    surface = e.api_library_surface()
    assert surface, "API door exposes no library re-exports"
    for name in surface:
        assert getattr(api, name) is getattr(qmb, name)
