"""Reference usage — Layer 2 pure conformance surface (Story 12.4).

Executable::

    python qml/examples/layer2_usage.py

Shows the things QL-8 / Story 12.4 pin down:

1. QML owns the format-versioned pure surface: denial set, AST/import-scan
   rules, determinism harness, golden-slice generator, and verdict function.
   The host owns only process spawning — this example never spawns one.
2. The golden-slice generator is keyed off the declared footprint and produces
   a deterministic identity-bearing fixture.
3. The suite asserts: logic loads in isolation; a golden slice run twice
   yields identical intents; only permitted intent kinds; state bound holds
   with snapshot/restore equivalent.
4. The same bot through two hosts yields one verdict; no Book is present.
5. Differing intents or a non-permitted kind is a Layer-2 conformance failure.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import ExactRational, PriceDelta, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok
from qmf.risk.door import Direction, EntryIntent, ExitIntent, ExitKind, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.conformance import (
    CONFORMANCE_FORMAT_VERSION,
    DENIAL_SET,
    GoldenSlice,
    Layer2Verdict,
    evaluate_layer2,
    generate_golden_slice,
    run_layer2_suite,
    scan_logic_source,
)
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope

T = TypeVar("T")

_CLEAN = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


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


def _declaration(source: dict[str, str] | None = None) -> BotDefinition:
    zone = _pinned("zone")
    sma = _pinned("sma")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": zone}]),
        "confluence",
    )
    footprint = _unwrap(mint_footprint([_stream()], [_calendar()], [zone, sma]), "footprint")
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", source or _CLEAN), "logic")
    return _unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": "trend-follow",
                "confluence_set": [confluence],
                "parameter_space": [
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
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        ),
        "declaration",
    )


def _scope(declaration: BotDefinition) -> object:
    return _unwrap(
        mint_state_scope(
            os="windows-11",
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build="none",
        ),
        "scope",
    )


def _run(
    declaration: BotDefinition,
    factory: object,
    source: dict[str, str] | None = None,
) -> Result[Layer2Verdict]:
    return run_layer2_suite(
        declaration=declaration,
        factory=factory,
        source_tree=source or _CLEAN,
        state_scope=_scope(declaration),
        state_bound=256,
    )


def _entry() -> EntryIntent:
    venue = _unwrap(VenueId.try_create("ctrader"), "venue")
    instrument = _unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")
    target = _unwrap(ExecutionTarget.try_create("live", venue, "acct-1"), "target")
    reason = _unwrap(ReasonCode.try_create("breakout", "trend-follow"), "reason")
    stop = _unwrap(PriceDelta.try_create(500, instrument, 5), "stop")
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


def _exit_full() -> ExitIntent:
    reason = _unwrap(ReasonCode.try_create("breakout", "trend-follow"), "reason")
    fp = _unwrap(fingerprint({"class": "virtual-position"}), "vp")
    return _unwrap(ExitIntent.try_create(ExitKind.CLOSE_FULL, reason, fp), "exit")


def golden_slice_identity_bearing() -> bool:
    declaration = _declaration()
    first = _unwrap(generate_golden_slice(declaration.footprint), "slice")
    second = _unwrap(generate_golden_slice(declaration.footprint), "slice-again")
    assert isinstance(first, GoldenSlice)
    left = _unwrap(first.fingerprint_content(), "slice fp")
    right = _unwrap(second.fingerprint_content(), "slice fp 2")
    return left.value == right.value and first.fp1_identity()["class"] == "qml-golden-slice"


def clean_suite_passes() -> bool:
    declaration = _declaration()
    verdict = _unwrap(_run(declaration, FunctionFactory(logic=lambda evidence: ())), "layer2")
    assert verdict.fp1_identity()["contract_format_version"] == CONFORMANCE_FORMAT_VERSION
    assert "host" not in verdict.fp1_identity()
    return True


def two_hosts_identical_verdict() -> bool:
    declaration = _declaration()
    factory = FunctionFactory(logic=lambda evidence: ())
    host_a = _unwrap(_run(declaration, factory), "host-a")
    host_b = _unwrap(_run(declaration, factory), "host-b")
    return host_a.fp1_identity() == host_b.fp1_identity()


def no_book_present() -> bool:
    declaration = _declaration()
    slice_ = _unwrap(generate_golden_slice(declaration.footprint), "slice")
    refused = evaluate_layer2(
        {
            "loaded_in_isolation": True,
            "book_present": True,
            "scan_findings": (),
            "golden_slice_fingerprint": _unwrap(slice_.fingerprint_content(), "slice fp"),
            "declaration_fingerprint": _unwrap(declaration.fingerprint_content(), "decl fp"),
            "first_run": ((), (), ()),
            "second_run": ((), (), ()),
            "state_bound_holds": True,
            "restore_equivalent": True,
        }
    )
    assert isinstance(refused, TypedRefusal)
    return refused.context["field"] == "no_book_present"


def differing_intents_fail() -> str:
    class Flip:
        n = 0

        def construct(
            self,
            *,
            declaration: object,
            assignment: object,
            read_surfaces: object,
        ) -> Result[object]:
            del declaration, assignment, read_surfaces

            class Callback:
                def on_instant(self, evidence: object) -> object:
                    del evidence
                    Flip.n += 1
                    if Flip.n % 2:
                        return (_entry(),)
                    return ()

            return Ok(Callback())

    refused = _run(_declaration(), Flip())
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def non_permitted_kind_fails() -> str:
    refused = _run(_declaration(), FunctionFactory(logic=lambda evidence: (_exit_full(),)))
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def clock_scan_fails() -> str:
    source = {"bot.py": "import time\n\ndef on_instant(self, evidence):\n    return ()\n"}
    report = _unwrap(scan_logic_source(source), "scan")
    assert report.findings[0].capability == "clock"
    refused = _run(_declaration(source), FunctionFactory(logic=lambda evidence: ()), source)
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def main() -> None:
    print(f"layer 2 format version: {CONFORMANCE_FORMAT_VERSION}")
    print(f"denial set: {','.join(sorted(DENIAL_SET))}")
    print(f"golden slice is identity-bearing: {golden_slice_identity_bearing()}")
    print(f"logic loads in isolation: {clean_suite_passes()}")
    print(f"two hosts identical verdict: {two_hosts_identical_verdict()}")
    print(f"no Book present: {no_book_present()}")
    print(f"differing intents is layer-2 failure: {differing_intents_fail()}")
    print(f"non-permitted kind is layer-2 failure: {non_permitted_kind_fails()}")
    print(f"clock import is layer-2 failure: {clock_scan_fails()}")
    print("layer2 conformance ok")


if __name__ == "__main__":
    main()
