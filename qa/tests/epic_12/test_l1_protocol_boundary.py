"""L1 — highest-consequence boundary decisions on the runtime protocol (Epic 12).

Each test names a concrete counter-case and pairs the refusal with a control
that the SAME surface admits, so a green is discriminating.

- E12-L1-01 (P0): an inbound ``requested_r`` is invalid input — the bot may not size. (QL-7, CT-23)
- E12-L1-02 (P0): a venue command / close_partial is refused unsupported capability. (QL-7, CT-23)
- E12-L1-04 (P1): a permitted EXIT kind outside close_full|tighten_protective_stop is invalid input. (FM-3)
- E12-L1-05 (P1): an unknown declaration format version is unsupported capability. (FM-12)
- E12-L1-06 (P1): strategy_family_id cardinality != 1 is invalid input. (FM-10)
- E12-L1-07 (P1): a restore across a differing tuple component is unavailable dependency. (FM-6)
- E12-L1-08 (P1): every Layer-1 failure is a RETURNED, journaled AD-11 typed refusal. (CT-04)
"""

from __future__ import annotations

import _world as w
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qml.declaration import mint_bot_definition
from qml.conformance import lint_declaration
from qml.protocol import accept_intents, construct_bot, restore_bot


# --- E12-L1-01 ---------------------------------------------------------------


def test_e12_l1_01_inbound_requested_r_is_invalid_input() -> None:
    """A bot-supplied requested_r through the door is invalid input (no bot sizing)."""
    refusal = accept_intents([{"intent_family": "entry", "requested_r": 3}])
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context.get("field") == "requested_r"
    # Control: a conformant entry (advisory stop only, no requested_r) is admitted.
    admitted = accept_intents([w.make_entry()])
    assert is_ok(admitted) and len(admitted.value) == 1


def test_e12_l1_01_sizing_dict_refused_in_live_drive_path() -> None:
    """A callback that tries to size is refused when the host drives it per instant."""

    class SizingFactory:
        def construct(self, *, declaration, assignment, read_surfaces):  # noqa: ANN001
            del declaration, assignment, read_surfaces

            class _Cb:
                def on_instant(self, evidence, /):  # noqa: ANN001
                    del evidence
                    return [{"intent_family": "entry", "requested_r": 2}]

            from qmf.core.refusal import Ok

            return Ok(_Cb())

    world = w.build_world()
    d = world["declaration"]
    hosted = construct_bot(
        SizingFactory(),
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=None,
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(hosted)
    from qmf.core.chrono import Instant

    instant = Instant.try_create(1_700_000_000_000_000_000)
    driven = hosted.value.on_instant(instant.value)
    assert is_refusal(driven)
    assert driven.context.get("field") == "requested_r"


# --- E12-L1-02 ---------------------------------------------------------------


def test_e12_l1_02_venue_command_is_unsupported() -> None:
    """A venue command never enters the Book through the CT-23 door."""
    refusal = accept_intents([{"venue_command": "place", "symbol": "EURUSD"}])
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_e12_l1_02_close_partial_is_unsupported() -> None:
    """close_partial is not a V1 exit kind — an unsupported-capability refusal."""
    refusal = accept_intents([{"intent_family": "exit", "kind": "close_partial"}])
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- E12-L1-04 ---------------------------------------------------------------


def test_e12_l1_04_exit_kind_outside_ct23_vocab_is_invalid() -> None:
    """A permitted EXIT kind outside close_full|tighten_protective_stop is invalid input."""
    refusal = mint_bot_definition(w.declaration_mapping(permitted_exit_intents=["close_half"]))
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    # 'entry' is never a declared permitted-exit kind.
    entry_ref = mint_bot_definition(w.declaration_mapping(permitted_exit_intents=["entry"]))
    assert is_refusal(entry_ref)
    assert entry_ref.category is RefusalCategory.INVALID_INPUT
    # Control: the ratified vocabulary builds.
    assert is_ok(mint_bot_definition(w.declaration_mapping(permitted_exit_intents=["close_full"])))


# --- E12-L1-05 ---------------------------------------------------------------


def test_e12_l1_05_unknown_declaration_format_version_is_unsupported() -> None:
    """An uninterpretable declaration contract format version is unsupported capability.

    The declaration PARSER and the Layer-1 linter are the surfaces that READ an
    incoming version; both refuse v99. (mint_bot_definition mints NEW content and
    always stamps the current version, so it is not the read surface under test.)
    """
    from qml.declaration import BotDefinition

    parsed = BotDefinition.try_from_mapping(w.declaration_mapping(contract_format_version=99))
    assert is_refusal(parsed)
    assert parsed.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    # The Layer-1 linter refuses it up front too (never a best-effort read).
    lint = lint_declaration(w.declaration_mapping(contract_format_version=99))
    assert is_refusal(lint)
    assert lint.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert lint.context.get("journal") is True


# --- E12-L1-06 ---------------------------------------------------------------


def test_e12_l1_06_family_cardinality_must_be_exactly_one() -> None:
    """A strategy_family_id of zero or more-than-one is invalid input (AD-17 cardinality-one)."""
    for bad in ([], ["a", "b"], None):
        refusal = mint_bot_definition(w.declaration_mapping(strategy_family_id=bad))
        assert is_refusal(refusal), f"cardinality {bad!r} must refuse"
        assert refusal.category is RefusalCategory.INVALID_INPUT
    # Control: exactly one builds.
    assert is_ok(mint_bot_definition(w.declaration_mapping(strategy_family_id="trend-follow")))


# --- E12-L1-07 ---------------------------------------------------------------


def _snapshot_of(world: dict[str, object]) -> object:
    d = world["declaration"]
    hosted = construct_bot(
        world["factory"],
        declaration=d,
        assignment=d.canonical_assignment(),  # type: ignore[attr-defined]
        read_surfaces=None,
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(hosted)
    snap = hosted.value.snapshot()
    assert is_ok(snap)
    return snap.value


def test_e12_l1_07_restore_across_differing_tuple_is_unavailable() -> None:
    """Restore across a differing OS / protocol version / arithmetic build is unavailable."""
    world = w.build_world()
    d = world["declaration"]
    snapshot = _snapshot_of(world)
    from qml.logic import mint_logic_identity

    other_logic = mint_logic_identity(
        "a-different-distribution", "9.9.9", {"pkg/other.py": "x = 1\n"}
    )
    assert is_ok(other_logic)
    # Only protocol format version 1 is known, so the OS / arithmetic-reference /
    # logic-identity components exercise the differing-tuple seam.
    differing = {
        "os": w.scope_for(d, os_name="a-different-os"),
        "arithmetic_reference_build": w.scope_for(d, arithmetic_reference_build="build-XYZ"),
        "logic_identity": w.scope_for(d, logic_identity=other_logic.value),
    }
    for component, current_scope in differing.items():
        restored = restore_bot(
            snapshot,
            world["factory"],
            declaration=d,
            assignment=d.canonical_assignment(),
            read_surfaces=None,
            current_scope=current_scope,
        )
        assert is_refusal(restored), f"{component} differing must refuse"
        assert restored.category is RefusalCategory.UNAVAILABLE_DEPENDENCY, component
    # Control: an identical tuple restores.
    same = restore_bot(
        snapshot,
        world["factory"],
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=None,
        current_scope=w.scope_for(d),
    )
    assert is_ok(same)


# --- E12-L1-08 ---------------------------------------------------------------


def test_e12_l1_08_layer1_failures_are_returned_not_raised_and_journaled() -> None:
    """An unresolvable reference is a RETURNED, journaled AD-11 typed refusal (never raised)."""
    world = w.build_world()
    d = world["declaration"]
    try:
        refusal = lint_declaration(
            d,
            family_catalog=[],  # family cannot resolve
            confluence_catalog=[world["confluence"]],
            producer_catalog=world["catalog_producers"],
            logic_catalog=[world["logic"]],
        )
    except Exception as exc:  # noqa: BLE001
        raise AssertionError(f"Layer 1 must RETURN a refusal, not raise: {exc!r}") from exc
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context.get("journal") is True
    assert refusal.context.get("layer") == 1
