"""Story 12.8 — complete example conformant bot (L27, QL-8)."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.registry import KindRegistry, Registrar
from qmf.risk.door import EntryIntent
from qml.conformance import (
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
    install_bot_definition_kind,
    mint_bot_definition,
    mint_confluence,
    register_bot_definition,
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

_QML_ROOT = Path(__file__).resolve().parents[1]
_LOGIC_DIR = _QML_ROOT / "examples" / "conformant_bot"
_OS = "windows-11"
_AR = "none"
_BOUND = 256
_CREATED_NS = 1_700_000_000_000_000_000
_DISTRIBUTION = "example-breakout-bot"
_VERSION = "1.0.0"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _source_tree() -> dict[str, str]:
    tree: dict[str, str] = {}
    for path in sorted(_LOGIC_DIR.glob("*.py")):
        tree[f"breakout_bot/{path.name}"] = path.read_text(encoding="utf-8")
    assert tree
    return tree


def _factory() -> object:
    path = _LOGIC_DIR / "bot.py"
    spec = importlib.util.spec_from_file_location("example_breakout_bot", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.BreakoutFactory()


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "example-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


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


def _world() -> dict[str, object]:
    zone = _pinned("zone")
    sma = _pinned("sma")
    session = _pinned("session-filter")
    family = _ok(mint_strategy_family("trend-follow"))
    confluence = _ok(
        mint_confluence(
            [
                {"role": "level", "producer_binding": zone},
                {"role": "trigger", "producer_binding": sma},
                {"role": "filter", "producer_binding": session},
            ]
        )
    )
    footprint = _ok(mint_footprint([_stream()], [_calendar()], [zone, sma, session]))
    source = _source_tree()
    logic = _ok(mint_logic_identity(_DISTRIBUTION, _VERSION, source))
    declaration = _ok(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": _parameter_space(),
                "footprint": footprint,
                "permitted_exit_intents": ("close_full",),
                "logic_reference": logic,
            }
        )
    )
    return {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": [zone, sma, session],
        "source": source,
        "factory": _factory(),
    }


def _declaration(world: dict[str, object]) -> BotDefinition:
    return cast(BotDefinition, world["declaration"])


def _scope(declaration: BotDefinition) -> object:
    return _ok(
        mint_state_scope(
            os=_OS,
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build=_AR,
        )
    )


def test_declaration_has_the_six_ct33_groups() -> None:
    world = _world()
    declaration = _declaration(world)
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
    assert len(declaration.confluence_set) == 1
    confluence = cast(Confluence, world["confluence"])
    assert {leg.role.value for leg in confluence.legs} == {"level", "trigger", "filter"}
    assert dict(declaration.canonical_assignment()) == {
        "lookback": 1,
        "stop_distance": 500,
    }
    assert "canonical_assignment" not in body
    assert declaration.permitted_exit_intents == ("close_full",)
    completeness = _ok(
        report_completeness(
            declaration.footprint,
            [leg.as_completeness_leg() for leg in confluence.legs],
            bot_direct=(),
        )
    )
    assert completeness.complete is True


def test_declaration_carries_no_exit_logic_or_sizing() -> None:
    world = _world()
    body = _declaration(world).body()
    payload = _declaration(world).identity_payload()
    assert FORBIDDEN_BOT_FIELDS.isdisjoint(body)
    assert "exit_logic" not in body
    assert "requested_r" not in body
    assert "exit_logic" not in payload
    stuffed = mint_bot_definition({**body, "exit_logic": "book-owned"})
    assert is_refusal(stuffed)


def test_layer1_and_layer2_pass_and_bot_kind_mints() -> None:
    world = _world()
    declaration = _declaration(world)
    layer1 = _ok(
        lint_declaration(
            declaration,
            family_catalog=[world["family"]],
            confluence_catalog=[world["confluence"]],
            producer_catalog=world["producers"],
            logic_catalog=[world["logic"]],
        )
    )
    layer2 = _ok(
        run_layer2_suite(
            declaration=declaration,
            factory=world["factory"],
            source_tree=world["source"],
            state_scope=_scope(declaration),
            state_bound=_BOUND,
        )
    )
    candidate = _ok(gate_registration(layer1=layer1, layer2=layer2))
    assert candidate.ticket.layer1_passed is True
    assert candidate.ticket.layer2_passed is True
    registry = KindRegistry()
    _ok(install_bot_definition_kind(registry))
    receipt = _ok(
        register_bot_definition(
            candidate.declaration,
            registrar=Registrar(registry),
            writer=_ok(
                WriterId.try_create("example-host", "authoring", KIND_BOT_DEFINITION, "boot-1")
            ),
            sequence=0,
            created_at=_ok(Instant.try_create(_CREATED_NS)),
        )
    )
    assert receipt.record.kind == KIND_BOT_DEFINITION
    assert receipt.outcome.value == "stored"
    assert "writer" not in candidate.identity_payload()


def test_logic_emits_advisory_entry_on_golden_slice() -> None:
    world = _world()
    declaration = _declaration(world)
    observed = _ok(
        collect_layer2_observations(
            declaration=declaration,
            factory=world["factory"],
            source_tree=world["source"],
            state_scope=_scope(declaration),
            state_bound=_BOUND,
        )
    )
    assert traces_equal(observed.first_run, observed.second_run)
    assert "entry" in observed.emitted_kinds
    assert set(observed.emitted_kinds) <= {"entry", "close_full"}
    slice_ = _ok(generate_golden_slice(declaration.footprint))
    keys = _ok(declared_evidence_keys(declaration.footprint))
    for payload in slice_.frames.values():
        assert frozenset(payload) == keys
    hosted = _ok(
        construct_bot(
            world["factory"],
            declaration=declaration,
            assignment=declaration.canonical_assignment(),
            read_surfaces=_ok(read_surfaces_for_slice(slice_)),
            state_scope=_scope(declaration),
            state_bound=_BOUND,
        )
    )
    saw_entry = False
    for instant in slice_.evaluation_instants:
        intents = _ok(hosted.on_instant(instant))
        for intent in intents:
            assert isinstance(intent, EntryIntent)
            assert intent.advisory_stop_proposal is not None
            assert not hasattr(intent, "requested_r")
            assert not hasattr(intent, "declared_full_loss_price")
            saw_entry = True
    assert saw_entry


def test_logic_source_neither_reads_clock_nor_performs_io() -> None:
    source = _source_tree()
    report = _ok(scan_logic_source(source))
    assert report.clean is True
    banned = frozenset(
        {
            "time",
            "datetime",
            "os",
            "io",
            "pathlib",
            "socket",
            "random",
            "secrets",
        }
    )
    for path, content in source.items():
        tree = ast.parse(content, filename=path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in banned
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in banned
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "open"
