"""Reference usage — bot state snapshot/restore (Story 12.2).

Executable::

    python qml/examples/state_usage.py

Shows the things QL-7 / Story 12.2 pin down:

1. Snapshot/restore is a versioned contract scoped to the injected tuple
   (OS, logic identity + source-manifest fingerprint, protocol format version,
   arithmetic-reference build). The OS is never read ambiently.
2. On an identical tuple the round-trip is equivalent (identical continued
   intents), and the restored-state fingerprint enters downstream labels.
3. Restoring across any tuple component is an unavailable-dependency refusal,
   never best-effort.
4. The declared state bound is enforced as a Layer-2 conformance concern;
   bot state is bounded and declared, never unbounded.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity, Instant, Interval
from qmf.core.exact import ExactRational, PriceDelta, UnitKind
from qmf.core.fingerprint import EvidenceClass, ResultLabel, World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    STATE_SNAPSHOT_FORMAT_VERSION,
    BotIntent,
    BotStateScope,
    BotStateSnapshot,
    FootprintEvidence,
    HostedBot,
    construct_bot,
    intent_identity,
    mint_state_scope,
    restore_bot,
)

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SOURCE_A = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_SOURCE_B = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return (1,)\n",
}
_OS = "windows-11"
_AR = "none"
_BOUND = 256


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _declaration(source: dict[str, str] | None = None) -> BotDefinition:
    tree = _SOURCE_A if source is None else source
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": _pinned("zone")}]),
        "confluence",
    )
    footprint = _unwrap(
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
        ),
        "footprint",
    )
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", tree), "logic")
    return _unwrap(
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
        ),
        "bot definition",
    )


def _entry() -> EntryIntent:
    venue = _unwrap(VenueId.try_create("ctrader"), "venue")
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")
    target = _unwrap(ExecutionTarget.try_create("live", venue, "acct-1"), "target")
    reason = _unwrap(ReasonCode.try_create("breakout", "trend-follow"), "reason")
    stop = _unwrap(PriceDelta.try_create(500, instrument, 5), "advisory stop")
    return _unwrap(
        EntryIntent.try_create(
            instrument,
            Direction.LONG,
            reason,
            target,
            proposed_r=_unwrap(ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE), "R"),
            advisory_stop_proposal=stop,
        ),
        "entry",
    )


def _scope(
    declaration: BotDefinition,
    *,
    os: str = _OS,
    arithmetic_reference_build: str = _AR,
    protocol_format_version: int = PROTOCOL_FORMAT_VERSION,
) -> BotStateScope:
    return _unwrap(
        mint_state_scope(
            os=os,
            logic_identity=declaration.logic_reference,
            protocol_format_version=protocol_format_version,
            arithmetic_reference_build=arithmetic_reference_build,
        ),
        "scope",
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
    declaration: BotDefinition, factory: object | None = None, *, bound: int = _BOUND
) -> HostedBot:
    return _unwrap(
        construct_bot(
            factory if factory is not None else _CounterFactory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            state_scope=_scope(declaration),
            state_bound=bound,
        ),
        "hosted bot",
    )


def _idents(intents: tuple[BotIntent, ...]) -> tuple[object, ...]:
    return tuple(intent_identity(item) for item in intents)


def round_trip_equivalent() -> bool:
    declaration = _declaration()
    t0 = _instant(_NS)
    t1 = _instant(_NS + 1)
    cold = _host(declaration)
    _unwrap(cold.on_instant(t0), "cold t0")
    cold_t1 = _unwrap(cold.on_instant(t1), "cold t1")
    warm = _host(declaration)
    _unwrap(warm.on_instant(t0), "warm t0")
    snapshot = _unwrap(warm.snapshot(), "snapshot")
    restored = _unwrap(
        restore_bot(
            snapshot,
            _CounterFactory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            current_scope=_scope(declaration),
        ),
        "restored bot",
    )
    continued = _unwrap(restored.on_instant(t1), "restored t1")
    return _idents(continued) == _idents(cold_t1) and len(continued) == 1


def fingerprint_enters_labels() -> bool:
    declaration = _declaration()
    warm = _host(declaration)
    _unwrap(warm.on_instant(_instant()), "drive")
    snapshot = _unwrap(warm.snapshot(), "snapshot")
    snapshot_fp = _unwrap(snapshot.fingerprint(), "snapshot fp")
    restored = _unwrap(
        restore_bot(
            snapshot,
            _CounterFactory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
            current_scope=_scope(declaration),
        ),
        "restored bot",
    )
    interval = _unwrap(Interval.try_create(_instant(_NS), _instant(_NS + 1)), "interval")
    producer = _unwrap(declaration.fingerprint_content(), "bot fp")
    label = _unwrap(
        ResultLabel.try_create(
            producer,
            1,
            restored.label_input_fingerprints(),
            interval,
            EvidenceClass.CONFIRMED,
            World.REPLAY,
        ),
        "result label",
    )
    return snapshot_fp in label.input_fingerprints


def _cross(
    current_scope: BotStateScope, declaration: BotDefinition, snapshot: BotStateSnapshot
) -> TypedRefusal:
    refused = restore_bot(
        snapshot,
        _CounterFactory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={},
        current_scope=current_scope,
    )
    assert isinstance(refused, TypedRefusal)
    assert refused.category.value == "unavailable dependency"
    return refused


def cross_tuple_refusals() -> tuple[str, str, str, str]:
    original = _declaration(_SOURCE_A)
    other = _declaration(_SOURCE_B)
    snapshot = _unwrap(_host(original).snapshot(), "snapshot")
    os_miss = _cross(_scope(original, os="ubuntu-24.04"), original, snapshot)
    logic_miss = _cross(_scope(other), other, snapshot)
    protocol_miss = _cross(_scope(original, protocol_format_version=2), original, snapshot)
    ar_miss = _cross(
        _scope(original, arithmetic_reference_build="ta-lib==0.7.1"), original, snapshot
    )
    return (
        os_miss.category.value,
        logic_miss.category.value,
        protocol_miss.category.value,
        ar_miss.category.value,
    )


def exceeded_bound_is_layer2() -> TypedRefusal:
    declaration = _declaration()
    hosted = _host(declaration, _OverflowFactory(), bound=16)
    refused = hosted.snapshot()
    assert isinstance(refused, TypedRefusal)
    assert refused.category.value == "policy rejection"
    assert refused.context["layer"] == 2
    return refused


def main() -> None:
    print(f"snapshot format version: {STATE_SNAPSHOT_FORMAT_VERSION}")
    print(f"identical-tuple round-trip equivalent: {round_trip_equivalent()}")
    print(f"restored-state fingerprint enters labels: {fingerprint_enters_labels()}")
    os_miss, logic_miss, protocol_miss, ar_miss = cross_tuple_refusals()
    print(f"cross-OS restore: {os_miss}")
    print(f"cross-logic restore: {logic_miss}")
    print(f"cross-protocol restore: {protocol_miss}")
    print(f"cross-arithmetic-reference restore: {ar_miss}")
    bound = exceeded_bound_is_layer2()
    print(f"exceeded state bound: {bound.category.value}")
    print("state usage ok")


if __name__ == "__main__":
    main()
