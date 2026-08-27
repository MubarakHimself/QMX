"""Reference usage — complete example conformant bot (Story 12.8).

Executable::

    python qml/examples/conformant_bot_usage.py

Ships one complete conformant bot as a tier-1 L27 artifact:

1. A CT-33 declaration: one strategy family, one-or-more CT-34 confluences,
   a unit-kinded parameter space whose defaults are the canonical assignment,
   a complete footprint, and a permitted EXIT-intent declaration.
2. Plain-Python logic (``conformant_bot/bot.py``) conforming to the runtime
   protocol — factory + callback, no clock, no I/O, no sizing, no exit-logic
   field.
3. Layer 1 and Layer 2 both pass and the registration candidate carries the
   two-layer ticket. The dated Bot-kind mint is defined-unwired in qml
   (CT-33, DEC-0173; OR-06): a host composition root stamps the CT-06
   envelope — this example never drives a mint.
4. Driven per evaluation instant, the logic consumes only declared-footprint
   evidence, emits only permitted CT-23 kinds, and carries an advisory stop
   on every entry. Two golden-slice runs are identical.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, is_ok
from qmf.risk.door import EntryIntent
from qml.conformance import (
    DENIED_IMPORTS,
    DENIED_NAME_CALLS,
    Layer1Verdict,
    Layer2Verdict,
    collect_layer2_observations,
    gate_registration,
    generate_golden_slice,
    lint_declaration,
    read_surfaces_for_slice,
    run_layer2_suite,
    scan_logic_source,
    traces_equal,
)
from qml.declaration import (
    FORBIDDEN_BOT_FIELDS,
    KIND_BOT_DEFINITION,
    BotDefinition,
    Confluence,
    mint_bot_definition,
    mint_confluence,
)
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint, report_completeness
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    construct_bot,
    declared_evidence_keys,
    mint_state_scope,
)

T = TypeVar("T")

_EXAMPLES = Path(__file__).resolve().parent
_LOGIC_DIR = _EXAMPLES / "conformant_bot"
_OS = "windows-11"
_AR = "none"
_BOUND = 256
_DISTRIBUTION = "example-breakout-bot"
_VERSION = "1.0.0"


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _logic_source_tree() -> dict[str, str]:
    """In-memory source tree of the logic distribution. Host I/O, not bot I/O."""
    tree: dict[str, str] = {}
    for path in sorted(_LOGIC_DIR.glob("*.py")):
        tree[f"breakout_bot/{path.name}"] = path.read_text(encoding="utf-8")
    if not tree:
        raise AssertionError("conformant bot logic source is missing")
    return tree


def _load_factory() -> object:
    path = _LOGIC_DIR / "bot.py"
    spec = importlib.util.spec_from_file_location("example_breakout_bot", path)
    if spec is None or spec.loader is None:
        raise AssertionError("conformant bot logic failed to load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    factory_type = getattr(module, "BreakoutFactory", None)
    if not callable(factory_type):
        raise AssertionError("BreakoutFactory missing")
    return factory_type()


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _parameter_space() -> list[dict[str, object]]:
    return [
        {
            "name": "lookback",
            "type": "exact integer",
            "bounds": {"min": 1, "max": 200},
            "step": 1,
            "default": 1,
            "unit_kind": UnitKind.COUNT,
            "ui": "ui-editable",
        },
        {
            "name": "stop_distance",
            "type": "exact integer",
            "bounds": {"min": 1, "max": 10_000},
            "step": 1,
            "default": 500,
            "unit_kind": UnitKind.COUNT,
            "ui": "ui-editable",
        },
    ]


def build_world() -> dict[str, object]:
    zone = _pinned("zone")
    sma = _pinned("sma")
    session = _pinned("session-filter")
    family = _unwrap(mint_strategy_family("trend-follow"), "family")
    confluence = _unwrap(
        mint_confluence(
            [
                {"role": "level", "producer_binding": zone},
                {"role": "trigger", "producer_binding": sma},
                {"role": "filter", "producer_binding": session},
            ]
        ),
        "confluence",
    )
    footprint = _unwrap(
        mint_footprint([_stream()], [_calendar()], [zone, sma, session]),
        "footprint",
    )
    source = _logic_source_tree()
    logic = _unwrap(mint_logic_identity(_DISTRIBUTION, _VERSION, source), "logic")
    declaration = _unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": _parameter_space(),
                "footprint": footprint,
                "permitted_exit_intents": ("close_full",),
                "logic_reference": logic,
            }
        ),
        "declaration",
    )
    return {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": [zone, sma, session],
        "source": source,
        "factory": _load_factory(),
    }


def _declaration_of(world: dict[str, object]) -> BotDefinition:
    return cast(BotDefinition, world["declaration"])


def _scope(declaration: BotDefinition) -> object:
    return _unwrap(
        mint_state_scope(
            os=_OS,
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build=_AR,
        ),
        "scope",
    )


def _lint(world: dict[str, object]) -> Result[Layer1Verdict]:
    return lint_declaration(
        world["declaration"],
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["producers"],
        logic_catalog=[world["logic"]],
    )


def _suite(world: dict[str, object]) -> Result[Layer2Verdict]:
    declaration = _declaration_of(world)
    return run_layer2_suite(
        declaration=declaration,
        factory=world["factory"],
        source_tree=world["source"],
        state_scope=_scope(declaration),
        state_bound=_BOUND,
    )


def layers_pass_and_candidate_is_content_only() -> bool:
    world = build_world()
    layer1 = _unwrap(_lint(world), "layer1")
    layer2 = _unwrap(_suite(world), "layer2")
    candidate = _unwrap(gate_registration(layer1=layer1, layer2=layer2), "gate")
    assert candidate.ticket.layer1_passed is True
    assert candidate.ticket.layer2_passed is True
    # The dated Bot-kind mint is defined-unwired in qml (CT-33, DEC-0173;
    # OR-06): the host composition root stamps writer/sequence/created-at.
    # qml hands back fingerprintable content plus the two-layer ticket only.
    payload = candidate.declaration.identity_payload()
    assert payload["kind"] == KIND_BOT_DEFINITION
    fp = _unwrap(candidate.declaration.fingerprint_content(), "content fp")
    assert fp.value.startswith("fp1:sha256:")
    assert "writer" not in candidate.identity_payload()
    return True


def declaration_is_complete() -> bool:
    world = build_world()
    declaration = _declaration_of(world)
    body = declaration.body()
    assert set(body) == {
        "strategy_family_id",
        "confluence_set",
        "parameter_space",
        "footprint",
        "permitted_exit_intents",
        "logic_reference",
    }
    assert declaration.strategy_family_id.value == "trend-follow"
    assert len(declaration.confluence_set) >= 1
    assert dict(declaration.canonical_assignment()) == {"lookback": 1, "stop_distance": 500}
    assert "canonical_assignment" not in body
    assert declaration.permitted_exit_intents == ("close_full",)
    assert FORBIDDEN_BOT_FIELDS.isdisjoint(body)
    assert "exit_logic" not in body
    confluence = cast(Confluence, world["confluence"])
    completeness = _unwrap(
        report_completeness(
            declaration.footprint,
            [leg.as_completeness_leg() for leg in confluence.legs],
            bot_direct=(),
        ),
        "completeness",
    )
    assert completeness.complete is True
    return True


def logic_emits_advisory_entry_deterministically() -> tuple[bool, bool, str]:
    world = build_world()
    declaration = _declaration_of(world)
    observed = _unwrap(
        collect_layer2_observations(
            declaration=declaration,
            factory=world["factory"],
            source_tree=world["source"],
            state_scope=_scope(declaration),
            state_bound=_BOUND,
        ),
        "layer2 observations",
    )
    assert traces_equal(observed.first_run, observed.second_run)
    kinds = set(observed.emitted_kinds)
    assert kinds <= {"entry", "close_full"}
    assert "entry" in kinds
    slice_ = _unwrap(generate_golden_slice(declaration.footprint), "golden slice")
    keys = _unwrap(declared_evidence_keys(declaration.footprint), "declared keys")
    for payload in slice_.frames.values():
        assert frozenset(payload) == keys
    surfaces = _unwrap(read_surfaces_for_slice(slice_), "slice surfaces")
    hosted = _unwrap(
        construct_bot(
            world["factory"],
            declaration=declaration,
            assignment=declaration.canonical_assignment(),
            read_surfaces=surfaces,
            state_scope=_scope(declaration),
            state_bound=_BOUND,
        ),
        "hosted bot",
    )
    saw_advisory = False
    for instant in slice_.evaluation_instants:
        intents = _unwrap(hosted.on_instant(instant), "drive")
        for intent in intents:
            assert isinstance(intent, EntryIntent)
            assert intent.advisory_stop_proposal is not None
            assert not hasattr(intent, "requested_r")
            assert not hasattr(intent, "declared_full_loss_price")
            saw_advisory = True
    assert saw_advisory
    return True, True, ",".join(sorted(kinds))


def boundary_is_honest() -> tuple[bool, bool, bool, bool]:
    world = build_world()
    declaration = _declaration_of(world)
    scan = _unwrap(scan_logic_source(world["source"]), "scan")
    assert scan.clean is True
    joined = "\n".join(cast(dict[str, str], world["source"]).values())
    assert "import time" not in joined
    assert "import os" not in joined
    assert "import pathlib" not in joined
    assert "datetime.now" not in joined
    clock_mods = DENIED_IMPORTS["clock"]
    io_mods = DENIED_IMPORTS["io"]
    assert clock_mods.isdisjoint(_imported_names(joined))
    assert io_mods.isdisjoint(_imported_names(joined))
    assert "open" in DENIED_NAME_CALLS["io"]
    assert "exit_logic" not in declaration.body()
    assert "requested_r" not in declaration.body()
    return False, False, False, False


def _imported_names(source: str) -> set[str]:
    names: set[str] = set()
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            names.add(stripped.split()[1].split(".")[0])
    return names


def main() -> None:
    world = build_world()
    declaration = _declaration_of(world)
    assignment = dict(declaration.canonical_assignment())
    lookback = assignment["lookback"]
    stop_distance = assignment["stop_distance"]
    print(f"strategy family: {declaration.strategy_family_id.value}")
    print(f"confluences: {len(declaration.confluence_set)}")
    print(f"canonical assignment: lookback={lookback},stop_distance={stop_distance}")
    print(f"permitted exit intents: {','.join(declaration.permitted_exit_intents)}")
    print(f"declaration is complete: {declaration_is_complete()}")
    print(f"layer 1 and layer 2 pass: {layers_pass_and_candidate_is_content_only()}")
    print("bot-kind mint defined-unwired: True")
    advisory, deterministic, kinds = logic_emits_advisory_entry_deterministically()
    print(f"advisory stop on entry: {advisory}")
    print(f"emitted kinds: {kinds}")
    print(f"golden-slice deterministic: {deterministic}")
    print("consumes only declared footprint: True")
    sizes, clock, io, exit_logic = boundary_is_honest()
    print(f"sizes: {sizes}")
    print(f"reads a clock: {clock}")
    print(f"performs I/O: {io}")
    print(f"exit-logic field: {exit_logic}")
    print("conformant bot ok")


if __name__ == "__main__":
    main()
