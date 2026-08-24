"""Story 12.2 — bot state snapshot/restore (QL-7, AR-67)."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity, Instant, Interval
from qmf.core.exact import ExactRational, PriceDelta, UnitKind
from qmf.core.fingerprint import EvidenceClass, ResultLabel, World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    SCOPE_COMPONENTS,
    STATE_SNAPSHOT_FORMAT_VERSION,
    BotIntent,
    BotStateScope,
    BotStateSnapshot,
    FootprintEvidence,
    FunctionFactory,
    HostedBot,
    assert_declared_state_bound,
    construct_bot,
    intent_identity,
    mint_state_scope,
    restore_bot,
)

T = TypeVar("T")

_SOURCE_A: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_SOURCE_B: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return (1,)\n",
}
_NS = 1_700_000_000_000_000_000
_OS = "windows-11"
_AR = "none"
_BOUND = 256
_QML_PROTOCOL = Path(__file__).resolve().parents[1] / "src" / "qml" / "protocol"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _declaration(*, source: dict[str, str] | None = None) -> BotDefinition:
    tree = _SOURCE_A if source is None else source
    calendar = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": _pinned("zone")}]))
    footprint = _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [calendar],
            [_pinned("sma")],
        )
    )
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", tree))
    return _ok(
        mint_bot_definition(
            strategy_family_id="trend-follow",
            confluence_set=[confluence],
            parameter_space=[
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 200},
                    "step": 1,
                    "default": 20,
                    "unit_kind": UnitKind.COUNT,
                    "ui": "ui-editable",
                }
            ],
            footprint=footprint,
            permitted_exit_intents=(),
            logic_reference=logic,
        )
    )


def _entry() -> EntryIntent:
    venue = _ok(VenueId.try_create("ctrader"))
    instrument = _ok(Instrument.try_create(venue, "EURUSD"))
    target = _ok(ExecutionTarget.try_create("live", venue, "acct-1"))
    reason = _ok(ReasonCode.try_create("breakout", "trend-follow"))
    stop = _ok(PriceDelta.try_create(500, instrument, 5))
    return _ok(
        EntryIntent.try_create(
            instrument,
            Direction.LONG,
            reason,
            target,
            proposed_r=_ok(ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE)),
            advisory_stop_proposal=stop,
        )
    )


def _scope(
    declaration: BotDefinition,
    *,
    os: str = _OS,
    arithmetic_reference_build: str = _AR,
    protocol_format_version: int = PROTOCOL_FORMAT_VERSION,
) -> BotStateScope:
    return _ok(
        mint_state_scope(
            os=os,
            logic_identity=declaration.logic_reference,
            protocol_format_version=protocol_format_version,
            arithmetic_reference_build=arithmetic_reference_build,
        )
    )


class _Counter:
    def __init__(self) -> None:
        self.n = 0

    def export_state(self) -> dict[str, object]:
        return {"n": self.n}

    def import_state(self, payload: object) -> None:
        mapping = cast("Mapping[str, object]", payload)
        n = mapping["n"]
        assert isinstance(n, int) and not isinstance(n, bool)
        self.n = n

    def on_instant(self, evidence: FootprintEvidence) -> object:
        del evidence
        self.n += 1
        if self.n == 2:
            return (_entry(),)
        return ()


class _CounterFactory:
    def construct(
        self,
        *,
        declaration: object,
        assignment: object,
        read_surfaces: object,
    ) -> Result[object]:
        del declaration, assignment, read_surfaces
        return Ok(_Counter())


class _Overflow:
    def export_state(self) -> dict[str, object]:
        return {"blob": "x" * 80}

    def on_instant(self, evidence: FootprintEvidence) -> object:
        del evidence
        return ()


class _OverflowFactory:
    def construct(
        self,
        *,
        declaration: object,
        assignment: object,
        read_surfaces: object,
    ) -> Result[object]:
        del declaration, assignment, read_surfaces
        return Ok(_Overflow())


def _host(
    declaration: BotDefinition,
    factory: object = None,
    *,
    os: str = _OS,
    arithmetic_reference_build: str = _AR,
    state_bound: int = _BOUND,
) -> HostedBot:
    return _ok(
        construct_bot(
            factory if factory is not None else _CounterFactory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            state_scope=_scope(
                declaration, os=os, arithmetic_reference_build=arithmetic_reference_build
            ),
            state_bound=state_bound,
        )
    )


def _identities(intents: tuple[BotIntent, ...]) -> tuple[object, ...]:
    return tuple(intent_identity(item) for item in intents)


# --- AC: identical tuple round-trip + restored-state fingerprint in labels --


def test_identical_tuple_round_trip_is_equivalent() -> None:
    declaration = _declaration()
    t0 = _instant(_NS)
    t1 = _instant(_NS + 1)
    t2 = _instant(_NS + 2)

    cold = _host(declaration)
    cold_intents = (
        _ok(cold.on_instant(t0)),
        _ok(cold.on_instant(t1)),
        _ok(cold.on_instant(t2)),
    )

    warm = _host(declaration)
    _ok(warm.on_instant(t0))
    snapshot = _ok(warm.snapshot())
    restored = _ok(
        restore_bot(
            snapshot,
            _CounterFactory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            current_scope=_scope(declaration),
        )
    )
    continued = (
        _ok(restored.on_instant(t1)),
        _ok(restored.on_instant(t2)),
    )
    assert _identities(continued[0]) == _identities(cold_intents[1])
    assert _identities(continued[1]) == _identities(cold_intents[2])
    assert [len(item) for item in cold_intents] == [0, 1, 0]
    assert [len(item) for item in continued] == [1, 0]


def test_restored_state_fingerprint_enters_downstream_labels() -> None:
    declaration = _declaration()
    warm = _host(declaration)
    _ok(warm.on_instant(_instant()))
    snapshot = _ok(warm.snapshot())
    snapshot_fp = _ok(snapshot.fingerprint())
    restored = _ok(
        restore_bot(
            snapshot,
            _CounterFactory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            current_scope=_scope(declaration),
        )
    )
    assert restored.restored_from == snapshot_fp
    assert snapshot_fp in restored.restored_state_fingerprints()
    start = _instant(_NS)
    end = _instant(_NS + 1)
    interval = _ok(Interval.try_create(start, end))
    producer = _ok(declaration.fingerprint_content())
    label = _ok(
        ResultLabel.try_create(
            producer,
            1,
            restored.label_input_fingerprints(),
            interval,
            EvidenceClass.CONFIRMED,
            World.REPLAY,
        )
    )
    assert snapshot_fp in label.input_fingerprints
    cold = _host(declaration)
    assert cold.restored_from is None
    assert cold.restored_state_fingerprints() == ()


def test_snapshot_is_a_versioned_serialized_contract() -> None:
    declaration = _declaration()
    hosted = _host(declaration)
    _ok(hosted.on_instant(_instant()))
    snapshot = _ok(hosted.snapshot())
    assert snapshot.format_version == STATE_SNAPSHOT_FORMAT_VERSION
    assert SCOPE_COMPONENTS == (
        "os",
        "logic_identity",
        "protocol_format_version",
        "arithmetic_reference_build",
    )
    mapping = snapshot.to_mapping()
    assert mapping["format_version"] == STATE_SNAPSHOT_FORMAT_VERSION
    assert snapshot.scope.os == _OS
    round_trip = _ok(BotStateSnapshot.from_mapping(mapping))
    assert _ok(round_trip.fingerprint()) == _ok(snapshot.fingerprint())
    assert round_trip.payload["n"] == 1


# --- AC: any differing tuple component is unavailable, never best-effort -----


def test_restore_across_differing_os_is_unavailable_dependency() -> None:
    declaration = _declaration()
    hosted = _host(declaration)
    snapshot = _ok(hosted.snapshot())
    refused = restore_bot(
        snapshot,
        _CounterFactory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={},
        current_scope=_scope(declaration, os="ubuntu-24.04"),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["differing"] == ("os",)


def test_restore_across_differing_logic_identity_is_unavailable_dependency() -> None:
    original = _declaration(source=_SOURCE_A)
    other = _declaration(source=_SOURCE_B)
    hosted = _host(original)
    snapshot = _ok(hosted.snapshot())
    refused = restore_bot(
        snapshot,
        _CounterFactory(),
        declaration=other,
        assignment={"lookback": 20},
        read_surfaces={},
        current_scope=_scope(other),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["differing"] == ("logic_identity",)


def test_restore_across_differing_protocol_format_version_is_unavailable() -> None:
    declaration = _declaration()
    hosted = _host(declaration)
    snapshot = _ok(hosted.snapshot())
    refused = restore_bot(
        snapshot,
        _CounterFactory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={},
        current_scope=_scope(declaration, protocol_format_version=2),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["differing"] == ("protocol_format_version",)


def test_restore_across_differing_arithmetic_reference_build_is_unavailable() -> None:
    declaration = _declaration()
    hosted = _host(declaration)
    snapshot = _ok(hosted.snapshot())
    refused = restore_bot(
        snapshot,
        _CounterFactory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={},
        current_scope=_scope(declaration, arithmetic_reference_build="ta-lib==0.7.1"),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["differing"] == ("arithmetic_reference_build",)


def test_cross_tuple_restore_is_never_best_effort() -> None:
    declaration = _declaration()
    hosted = _host(declaration)
    _ok(hosted.on_instant(_instant()))
    snapshot = _ok(hosted.snapshot())
    refused = restore_bot(
        snapshot,
        _CounterFactory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={},
        current_scope=_scope(declaration, os="darwin-24"),
    )
    assert is_refusal(refused)
    assert not hasattr(refused, "_logic")


# --- AC: declared state bound is a Layer-2 concern, never unbounded ----------


def test_exceeded_state_bound_is_layer2_policy_rejection() -> None:
    declaration = _declaration()
    hosted = _host(declaration, _OverflowFactory(), state_bound=16)
    refused = hosted.snapshot()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["layer"] == 2
    assert refused.context["field"] == "state_bound"
    direct = assert_declared_state_bound({"blob": "x" * 80}, 16)
    assert is_refusal(direct)
    assert direct.category is RefusalCategory.POLICY_REJECTION
    assert direct.context["layer"] == 2


def test_unbounded_state_is_refused() -> None:
    declaration = _declaration()
    hosted = _ok(
        construct_bot(
            _CounterFactory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            state_scope=_scope(declaration),
        )
    )
    refused = hosted.snapshot()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "state_bound"
    missing_scope = _ok(
        construct_bot(
            _CounterFactory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            state_bound=_BOUND,
        )
    )
    no_scope = missing_scope.snapshot()
    assert is_refusal(no_scope)
    assert no_scope.category is RefusalCategory.INVALID_INPUT
    zero = construct_bot(
        _CounterFactory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={},
        state_scope=_scope(declaration),
        state_bound=0,
    )
    assert is_refusal(zero)


def test_unknown_snapshot_format_version_is_unsupported_capability() -> None:
    declaration = _declaration()
    hosted = _host(declaration)
    snapshot = _ok(hosted.snapshot())
    mapping = snapshot.to_mapping()
    mapping["format_version"] = 2
    refused = BotStateSnapshot.from_mapping(mapping)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_stateless_function_factory_round_trips_empty_state() -> None:
    declaration = _declaration()
    factory = FunctionFactory(logic=lambda evidence: ())
    hosted = _host(declaration, factory)
    snapshot = _ok(hosted.snapshot())
    assert dict(snapshot.payload) == {}
    restored = _ok(
        restore_bot(
            snapshot,
            factory,
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            current_scope=_scope(declaration),
        )
    )
    assert _ok(restored.on_instant(_instant())) == ()


def test_state_source_never_reads_ambient_os_or_hashes() -> None:
    banned_modules = frozenset({"platform", "os", "hashlib", "hmac", "socket", "random"})
    hits: list[str] = []
    for path in sorted(_QML_PROTOCOL.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.append(node.module.split(".", 1)[0])
            for name in names:
                if name in banned_modules:
                    hits.append(f"{path.name}:{name}")
    assert hits == []
