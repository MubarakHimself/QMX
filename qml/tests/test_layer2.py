"""Story 12.4 — Layer 2 pure conformance surface and golden-slice generator."""

from __future__ import annotations

import ast
import inspect
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import ExactRational, PriceDelta, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.door import Direction, EntryIntent, ExitIntent, ExitKind, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.conformance import (
    CONFORMANCE_FORMAT_VERSION,
    CONFORMANCE_LADDER,
    DENIAL_SET,
    LAYER2_CHECKS,
    GoldenSlice,
    Layer2Verdict,
    ast_scan_rules_identity,
    conformance_contract_identity,
    evaluate_layer2,
    generate_golden_slice,
    run_layer2_suite,
    scan_logic_source,
)
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    FootprintEvidence,
    FunctionFactory,
    PresenceState,
    mint_state_scope,
)

import qml

T = TypeVar("T")

_CLEAN_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_OS = "windows-11"
_AR = "none"
_BOUND = 256
_CONFORMANCE = Path(__file__).resolve().parents[1] / "src" / "qml" / "conformance"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _int_param() -> dict[str, object]:
    return {
        "name": "lookback",
        "type": "exact integer",
        "bounds": {"min": 1, "max": 200},
        "step": 1,
        "default": 20,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _declaration(
    *,
    source: dict[str, str] | None = None,
    extra_footprint: str | None = None,
    permitted_exit_intents: object = (),
) -> BotDefinition:
    zone = _pinned("zone")
    sma = _pinned("sma" if extra_footprint is None else extra_footprint)
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = _ok(mint_footprint([_stream()], [_calendar()], [zone, sma]))
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", source or _CLEAN_SOURCE))
    return _ok(
        mint_bot_definition(
            {
                "strategy_family_id": "trend-follow",
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "permitted_exit_intents": permitted_exit_intents,
                "logic_reference": logic,
            }
        )
    )


def _scope(declaration: BotDefinition):
    return _ok(
        mint_state_scope(
            os=_OS,
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build=_AR,
        )
    )


def _silent() -> FunctionFactory:
    return FunctionFactory(logic=lambda evidence: ())


def _suite(
    declaration: BotDefinition,
    factory: object | None = None,
    *,
    source: dict[str, str] | None = None,
    state_bound: int = _BOUND,
) -> Result[Layer2Verdict]:
    return run_layer2_suite(
        declaration=declaration,
        factory=_silent() if factory is None else factory,
        source_tree=source or _CLEAN_SOURCE,
        state_scope=_scope(declaration),
        state_bound=state_bound,
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


def _exit_full() -> ExitIntent:
    reason = _ok(ReasonCode.try_create("breakout", "trend-follow"))
    fp = _ok(fingerprint({"class": "virtual-position"}))
    return _ok(ExitIntent.try_create(ExitKind.CLOSE_FULL, reason, fp))


# --- AC: QML-owned format-versioned pure surface -----------------------------


def test_layer2_contract_is_qml_ad5_not_ct_numbered() -> None:
    identity = conformance_contract_identity()
    assert identity["class"] == "qml-conformance-gate"
    assert identity["contract_format_version"] == CONFORMANCE_FORMAT_VERSION
    assert identity["ladder"] == CONFORMANCE_LADDER
    assert identity["ladder"] == "qml-ad5"
    assert "ct" not in identity
    assert "CT-" not in str(identity)
    assert qml.__version__ not in identity.values()
    assert identity["denial_set"] == sorted(DENIAL_SET)
    assert identity["layer2_checks"] == list(LAYER2_CHECKS)
    rules = ast_scan_rules_identity()
    assert rules["class"] == "qml-ast-import-scan-rules"
    assert rules["contract_format_version"] == 1
    assert qml.__version__ not in rules.values()


def test_denial_set_is_clock_io_network_randomness() -> None:
    assert frozenset({"clock", "io", "network", "undeclared_randomness"}) == DENIAL_SET


def test_run_layer2_suite_has_no_book_and_no_process_parameter() -> None:
    names = inspect.signature(run_layer2_suite).parameters
    assert "book" not in names
    assert "book_module" not in names
    assert "subprocess" not in names
    assert "isolation" not in names


# --- AC: golden-slice generator keyed off footprint --------------------------


def test_golden_slice_is_deterministic_and_identity_bearing() -> None:
    declaration = _declaration()
    first = _ok(generate_golden_slice(declaration.footprint))
    second = _ok(generate_golden_slice(declaration.footprint))
    assert isinstance(first, GoldenSlice)
    left = _ok(first.fingerprint_content())
    right = _ok(second.fingerprint_content())
    assert left.value == right.value
    identity = first.fp1_identity()
    assert identity["class"] == "qml-golden-slice"
    assert (
        identity["footprint_fingerprint"] == _ok(declaration.footprint.fingerprint_content()).value
    )
    assert qml.__version__ not in identity.values()
    assert "package_version" not in identity
    assert len(first.evaluation_instants) == 3
    other = _declaration(extra_footprint="other")
    other_slice = _ok(generate_golden_slice(other.footprint))
    assert _ok(other_slice.fingerprint_content()).value != left.value


def test_golden_slice_keys_match_declared_footprint() -> None:
    declaration = _declaration()
    slice_ = _ok(generate_golden_slice(declaration))
    from qml.protocol.evidence import declared_evidence_keys

    keys = _ok(declared_evidence_keys(declaration.footprint))
    for _ns, payload in slice_.frames.items():
        assert frozenset(payload) == keys
        for sample_block in payload.values():
            mapping = cast(Mapping[str, object], sample_block)
            samples = cast(list[object], mapping["samples"])
            item = cast(Mapping[str, object], samples[0])
            assert item["presence"] == "present"
            assert isinstance(item["value"], int)


# --- AC: suite — isolation, twice-identical, permitted kinds, restore --------


def test_clean_logic_passes_every_layer2_check() -> None:
    declaration = _declaration()
    verdict = _ok(_suite(declaration))
    assert isinstance(verdict, Layer2Verdict)
    assert verdict.checks == LAYER2_CHECKS
    identity = verdict.fp1_identity()
    assert identity["class"] == "qml-layer2-verdict"
    assert identity["contract_format_version"] == CONFORMANCE_FORMAT_VERSION
    assert identity["declaration_fingerprint"] == verdict.declaration_fingerprint.value
    assert identity["golden_slice_fingerprint"] == verdict.golden_slice_fingerprint.value
    assert qml.__version__ not in identity.values()
    assert "host" not in identity
    fp = _ok(verdict.fingerprint_content())
    assert fp.value.startswith("fp1:sha256:")


def test_entry_emitting_bot_is_deterministic_across_golden_slice() -> None:
    declaration = _declaration()

    def logic(evidence: FootprintEvidence) -> object:
        series = evidence.series.get("primary")
        if series is None or not series.samples:
            return ()
        if series.samples[-1].presence is not PresenceState.PRESENT:
            return ()
        return (_entry(),)

    verdict = _ok(_suite(declaration, FunctionFactory(logic=logic)))
    assert verdict.checks == LAYER2_CHECKS


# --- AC: same bot, two hosts, identical verdict, no Book ---------------------


def test_two_hosts_feed_identical_verdict() -> None:
    declaration = _declaration()
    host_a = _ok(_suite(declaration))
    host_b = _ok(_suite(declaration))
    assert host_a.fp1_identity() == host_b.fp1_identity()
    assert _ok(host_a.fingerprint_content()) == _ok(host_b.fingerprint_content())

    obs = {
        "loaded_in_isolation": True,
        "book_present": False,
        "scan_findings": (),
        "golden_slice_fingerprint": host_a.golden_slice_fingerprint,
        "declaration_fingerprint": host_a.declaration_fingerprint,
        "first_run": ((), (), ()),
        "second_run": ((), (), ()),
        "emitted_kinds": (),
        "permitted_exit_intents": (),
        "state_bound_holds": True,
        "restore_equivalent": True,
        "host": "qmb",
    }
    other = dict(obs)
    other["host"] = "node"
    left = _ok(evaluate_layer2(obs))
    right = _ok(evaluate_layer2(other))
    assert left.fp1_identity() == right.fp1_identity()
    assert "host" not in left.fp1_identity()


def test_book_present_is_layer2_failure() -> None:
    declaration = _declaration()
    slice_ = _ok(generate_golden_slice(declaration.footprint))
    refused = evaluate_layer2(
        {
            "loaded_in_isolation": True,
            "book_present": True,
            "scan_findings": (),
            "golden_slice_fingerprint": _ok(slice_.fingerprint_content()),
            "declaration_fingerprint": _ok(declaration.fingerprint_content()),
            "first_run": ((), (), ()),
            "second_run": ((), (), ()),
            "state_bound_holds": True,
            "restore_equivalent": True,
        }
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "no_book_present"
    assert refused.context["layer"] == 2


# --- AC: differing intents or non-permitted kind is Layer-2 failure ----------


def test_differing_golden_slice_intents_are_layer2_failure() -> None:
    declaration = _declaration()

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
                def on_instant(self, evidence: FootprintEvidence) -> object:
                    del evidence
                    Flip.n += 1
                    if Flip.n % 2:
                        return (_entry(),)
                    return ()

            return Ok(Callback())

    refused = _suite(declaration, Flip())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "golden_slice_determinism"
    assert refused.context["layer"] == 2
    assert refused.context["journal"] is True


def test_non_permitted_intent_kind_is_layer2_failure() -> None:
    declaration = _declaration(permitted_exit_intents=())
    refused = _suite(declaration, FunctionFactory(logic=lambda _evidence: (_exit_full(),)))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "permitted_intent_kinds"
    assert refused.context["layer"] == 2


def test_host_fed_non_permitted_kind_is_layer2_failure() -> None:
    declaration = _declaration()
    slice_ = _ok(generate_golden_slice(declaration.footprint))
    refused = evaluate_layer2(
        {
            "loaded_in_isolation": True,
            "book_present": False,
            "scan_findings": (),
            "golden_slice_fingerprint": _ok(slice_.fingerprint_content()),
            "declaration_fingerprint": _ok(declaration.fingerprint_content()),
            "first_run": ((), (), ()),
            "second_run": ((), (), ()),
            "emitted_kinds": ("close_full",),
            "permitted_exit_intents": (),
            "state_bound_holds": True,
            "restore_equivalent": True,
        }
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "permitted_intent_kinds"


def test_host_fed_differing_traces_are_layer2_failure() -> None:
    declaration = _declaration()
    slice_ = _ok(generate_golden_slice(declaration.footprint))
    refused = evaluate_layer2(
        {
            "loaded_in_isolation": True,
            "book_present": False,
            "scan_findings": (),
            "golden_slice_fingerprint": _ok(slice_.fingerprint_content()),
            "declaration_fingerprint": _ok(declaration.fingerprint_content()),
            "first_run": (({"intent_family": "entry"},),),
            "second_run": ((),),
            "emitted_kinds": ("entry",),
            "permitted_exit_intents": (),
            "state_bound_holds": True,
            "restore_equivalent": True,
        }
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "golden_slice_determinism"


# --- static AST/import scan --------------------------------------------------


def test_clock_import_is_layer2_failure() -> None:
    source = {"bot.py": "import time\n\ndef on_instant(self, evidence):\n    return ()\n"}
    declaration = _declaration(source=source)
    refused = _suite(declaration, source=source)
    assert is_refusal(refused)
    assert refused.context["field"] == "static_ast_import_scan"
    assert refused.context["capability"] == "clock"


def test_datetime_now_is_clock_denial() -> None:
    source = {
        "bot.py": (
            "from datetime import datetime\n\n"
            "def on_instant(self, evidence):\n"
            "    datetime.now()\n"
            "    return ()\n"
        )
    }
    report = _ok(scan_logic_source(source))
    assert not report.clean
    assert report.findings[0].capability == "clock"


def test_open_call_is_io_denial() -> None:
    source = {"bot.py": "def on_instant(self, evidence):\n    open('x')\n    return ()\n"}
    report = _ok(scan_logic_source(source))
    assert report.findings[0].capability == "io"


def test_socket_import_is_network_denial() -> None:
    source = {"bot.py": "import socket\n\ndef on_instant(self, evidence):\n    return ()\n"}
    report = _ok(scan_logic_source(source))
    assert report.findings[0].capability == "network"


def test_random_import_is_undeclared_randomness() -> None:
    source = {"bot.py": "import random\n\ndef on_instant(self, evidence):\n    return ()\n"}
    report = _ok(scan_logic_source(source))
    assert report.findings[0].capability == "undeclared_randomness"
    allowed = _ok(scan_logic_source(source, declared_seed=True))
    assert allowed.clean


def test_scan_is_pure_over_in_memory_source() -> None:
    report = _ok(scan_logic_source(_CLEAN_SOURCE))
    assert report.clean


# --- state bound -------------------------------------------------------------


def test_exceeded_state_bound_is_layer2_failure() -> None:
    declaration = _declaration()

    class Overflow:
        def export_state(self) -> dict[str, object]:
            return {"blob": "x" * 80}

        def on_instant(self, evidence: FootprintEvidence) -> object:
            del evidence
            return ()

    class OverflowFactory:
        def construct(
            self,
            *,
            declaration: object,
            assignment: object,
            read_surfaces: object,
        ) -> Result[object]:
            del declaration, assignment, read_surfaces
            return Ok(Overflow())

    refused = _suite(declaration, OverflowFactory(), state_bound=16)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "state_bound_restore_equivalent"


def test_logic_that_does_not_load_fails_isolation() -> None:
    declaration = _declaration()
    refused = _suite(declaration, factory=object())
    assert is_refusal(refused)
    assert refused.context["field"] == "logic_loads_in_isolation"


# --- purity of the QML-owned surface ----------------------------------------


def test_layer2_modules_are_pure_no_io_or_process() -> None:
    banned = frozenset(
        {
            "subprocess",
            "threading",
            "multiprocessing",
            "socket",
            "asyncio",
            "qmf.venue",
        }
    )
    for path in sorted(_CONFORMANCE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name not in banned, path
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module not in banned
                assert not node.module.startswith("qmf.venue")
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "open"


def test_public_export_surface() -> None:
    assert qml.run_layer2_suite is run_layer2_suite
    assert qml.evaluate_layer2 is evaluate_layer2
    assert qml.generate_golden_slice is generate_golden_slice
    assert qml.scan_logic_source is scan_logic_source
    assert qml.LAYER2_CHECKS == LAYER2_CHECKS
    assert qml.Layer2Verdict is Layer2Verdict
    assert qml.GoldenSlice is GoldenSlice
