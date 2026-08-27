"""L3 — the shipped example conformant bot, end-to-end within tier (E12-L3-12, P0).

The SHIPPED ``qml/examples/conformant_bot`` is loaded and driven through the
independent Layer-1 + Layer-2 machinery with the TEST's own assertions (never the
example's own self-checks). This is the strongest in-package proxy for the
out-of-tier wired mint (L4). Story 12.8 / L27 / FR-047/FR-050 / CT-33.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import qml
from qmf.core.refusal import is_ok
from qmf.risk.door import EntryIntent
from qml.conformance import (
    drive_golden_slice,
    gate_registration,
    generate_golden_slice,
    lint_declaration,
    read_surfaces_for_slice,
    run_layer2_suite,
    scan_logic_source,
)
from qml.protocol import PROTOCOL_FORMAT_VERSION, construct_bot, mint_state_scope

_EXAMPLE_PATH = Path(qml.__file__).resolve().parents[2] / "examples" / "conformant_bot_usage.py"


def _load_example() -> object:
    spec = importlib.util.spec_from_file_location("qa_example_conformant_bot", _EXAMPLE_PATH)
    assert spec is not None and spec.loader is not None, f"cannot load {_EXAMPLE_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scope(declaration: object) -> object:
    return mint_state_scope(
        os="windows-11",
        logic_identity=declaration.logic_reference,
        protocol_format_version=PROTOCOL_FORMAT_VERSION,
        arithmetic_reference_build="none",
    ).value


def test_e12_l3_12_example_bot_passes_both_layers_and_mints() -> None:
    """The shipped example passes Layer 1 AND Layer 2 and the Bot kind mints (both tickets)."""
    assert _EXAMPLE_PATH.exists(), "the L27 reference bot must ship in examples/"
    world = _load_example().build_world()
    d = world["declaration"]
    l1 = lint_declaration(
        d,
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["producers"],
        logic_catalog=[world["logic"]],
    )
    assert is_ok(l1), f"example must pass Layer 1: {l1}"
    l2 = run_layer2_suite(
        declaration=d,
        factory=world["factory"],
        source_tree=world["source"],
        state_scope=_scope(d),
        state_bound=256,
    )
    assert is_ok(l2), f"example must pass Layer 2: {l2}"
    gate = gate_registration(layer1=l1.value, layer2=l2.value)
    assert is_ok(gate)
    assert gate.value.ticket.layer1_passed and gate.value.ticket.layer2_passed


def test_e12_l3_12_example_declaration_boundary_is_honest() -> None:
    """The example declaration carries no exit_logic / sizing / full-loss fields; one family."""
    world = _load_example().build_world()
    d = world["declaration"]
    body = d.body()
    assert d.strategy_family_id.value  # exactly one family (cardinality enforced at build)
    assert len(d.confluence_set) >= 1
    for forbidden in ("exit_logic", "requested_r", "declared_full_loss_price", "sizing"):
        assert forbidden not in body
    assert d.permitted_exit_intents == ("close_full",)
    # And the shipped logic source is clean under the denial-set scan.
    assert scan_logic_source(world["source"]).value.clean is True


def test_e12_l3_12_example_logic_is_deterministic_advisory_entry() -> None:
    """Driven per instant, the example emits only permitted kinds with an advisory stop; deterministic."""
    world = _load_example().build_world()
    d = world["declaration"]
    slice_ = generate_golden_slice(d.footprint)
    assert is_ok(slice_)
    surfaces = read_surfaces_for_slice(slice_.value)
    assert is_ok(surfaces)

    def _drive() -> tuple[object, ...]:
        hosted = construct_bot(
            world["factory"],
            declaration=d,
            assignment=d.canonical_assignment(),
            read_surfaces=surfaces.value,
            state_scope=_scope(d),
            state_bound=256,
        )
        assert is_ok(hosted), hosted
        trace = drive_golden_slice(hosted.value, slice_.value)
        assert is_ok(trace), trace
        return trace.value

    first = _drive()
    assert first == _drive(), "the example must be deterministic under the golden slice"

    # Drive live and inspect every emitted intent: entry-only, advisory stop present, no sizing.
    hosted = construct_bot(
        world["factory"],
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=surfaces.value,
        state_scope=_scope(d),
        state_bound=256,
    )
    assert is_ok(hosted)
    saw_entry = False
    for instant in slice_.value.evaluation_instants:
        intents = hosted.value.on_instant(instant)
        assert is_ok(intents)
        for intent in intents.value:
            assert isinstance(intent, EntryIntent)
            assert intent.advisory_stop_proposal is not None
            assert not hasattr(intent, "requested_r")
            saw_entry = True
    assert saw_entry, "the example emits an advisory-stop entry over the golden slice"
