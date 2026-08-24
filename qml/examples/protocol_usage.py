"""Reference usage — bot runtime protocol factory and callback (Story 12.1).

Executable::

    python qml/examples/protocol_usage.py

Shows the things QL-7 / Story 12.1 pin down:

1. The protocol is a QML-owned format-versioned contract on the qml-ad5 ladder,
   not CT-numbered. Package SemVer never enters identity.
2. A conformant bot is a factory taking (declaration, resolved assignment,
   injected read surfaces) and returning a callback the host drives per
   evaluation instant.
3. The callback receives only declared-footprint evidence (presence-mapped
   series and structure folds, each sample carrying knowable-at) and returns
   zero-or-more CT-23 intents.
4. An advisory stop proposal is advisory; the declared full-loss price is
   Book-side. No Book module is injected.
5. An inbound requested_r is invalid input; a venue command is rejected.
6. Identical (declaration, assignment, evidence sequence, state) yields
   identical intents.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import CalendarIdentity, Instant
from qmf.core.exact import PriceDelta, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.declaration import mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    PROTOCOL_LADDER,
    FootprintEvidence,
    FunctionFactory,
    MappingReadSurface,
    PresenceState,
    accept_intents,
    construct_bot,
    intent_identity,
    protocol_contract_identity,
)

import qml

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SOURCE = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _declaration() -> object:
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
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", _SOURCE), "logic")
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
            advisory_stop_proposal=stop,
        ),
        "entry",
    )


def _present(instant: Instant) -> dict[str, object]:
    return {
        "kind": "series",
        "samples": [{"presence": "present", "knowable_at": instant, "value": 1}],
    }


def _factory() -> FunctionFactory:
    def logic(evidence: FootprintEvidence) -> object:
        series = evidence.series.get("primary")
        if series is None or not series.samples:
            return ()
        if series.samples[-1].presence is not PresenceState.PRESENT:
            return ()
        return (_entry(),)

    return FunctionFactory(logic=logic)


def protocol_is_qml_ad5_not_ct() -> bool:
    identity = protocol_contract_identity()
    assert identity["ladder"] == PROTOCOL_LADDER == "qml-ad5"
    assert identity["contract_format_version"] == PROTOCOL_FORMAT_VERSION == 1
    assert "ct" not in identity
    assert qml.__version__ not in identity.values()
    return True


def factory_constructs_and_emits_advisory_entry() -> tuple[bool, bool, bool]:
    declaration = _declaration()
    empty_at = _instant()
    live_at = _instant(_NS + 1)
    hosted = _unwrap(
        construct_bot(
            _factory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={
                "primary": _unwrap(
                    MappingReadSurface.try_create({empty_at: None, live_at: _present(live_at)}),
                    "surface",
                )
            },
        ),
        "hosted bot",
    )
    zero = _unwrap(hosted.on_instant(empty_at), "empty instant")
    intents = _unwrap(hosted.on_instant(live_at), "live instant")
    assert zero == ()
    assert len(intents) == 1
    entry = intents[0]
    assert isinstance(entry, EntryIntent)
    assert entry.advisory_stop_proposal is not None
    assert not hasattr(entry, "requested_r")
    assert not hasattr(entry, "declared_full_loss_price")
    return True, True, True


def inbound_requested_r_is_invalid() -> TypedRefusal:
    refused = accept_intents({"intent_family": "entry", "entry": _entry(), "requested_r": 2})
    assert isinstance(refused, TypedRefusal)
    assert refused.category.value == "invalid input"
    return refused


def venue_command_is_rejected() -> TypedRefusal:
    refused = accept_intents({"venue_command": "place", "place": {"symbol": "EURUSD"}})
    assert isinstance(refused, TypedRefusal)
    assert refused.category.value == "unsupported capability"
    return refused


def replay_is_deterministic() -> bool:
    declaration = _declaration()
    t0 = _instant()
    t1 = _instant(_NS + 1)
    surfaces = {
        "primary": _unwrap(
            MappingReadSurface.try_create({t0: _present(t0), t1: _present(t1)}),
            "surface",
        )
    }

    def run() -> tuple[object, object]:
        hosted = _unwrap(
            construct_bot(
                _factory(),
                declaration=declaration,
                assignment={"lookback": 20},
                read_surfaces=surfaces,
            ),
            "replay bot",
        )
        first = _unwrap(hosted.on_instant(t0), "t0")
        second = _unwrap(hosted.on_instant(t1), "t1")
        return (
            tuple(intent_identity(item) for item in first),
            tuple(intent_identity(item) for item in second),
        )

    return run() == run()


def main() -> None:
    print(f"protocol format version: {PROTOCOL_FORMAT_VERSION}")
    print(f"ladder is qml-ad5, not CT-numbered: {protocol_is_qml_ad5_not_ct()}")
    constructed, empty, advisory = factory_constructs_and_emits_advisory_entry()
    print(f"factory constructed: {constructed}")
    print(f"zero intents on empty evidence: {empty}")
    print(f"advisory stop is advisory: {advisory}")
    sizing = inbound_requested_r_is_invalid()
    print(f"inbound requested_r is {sizing.category.value}")
    venue = venue_command_is_rejected()
    print(f"venue command rejected: {venue.category.value}")
    print(f"replay identical intents: {replay_is_deterministic()}")
    print("protocol usage ok")


if __name__ == "__main__":
    main()
