"""Story 12.1 — bot runtime protocol (QL-7)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar, get_args

from qmf.core.chrono import CalendarIdentity, DataDrivenClock, Instant
from qmf.core.exact import ExactRational, Price, PriceDelta, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.door import Direction, EntryIntent, ExitIntent, ExitKind, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.conformance import DENIAL_SET
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_CONTRACT_CLASS,
    PROTOCOL_DENIAL_SET,
    PROTOCOL_FORMAT_VERSION,
    PROTOCOL_LADDER,
    BotIntent,
    FootprintEvidence,
    FunctionFactory,
    HostedBot,
    MappingReadSurface,
    PresenceState,
    SeriesSample,
    StructureFold,
    accept_intents,
    coerce_protocol_format_version,
    collect_evidence,
    construct_bot,
    declared_evidence_keys,
    intent_identity,
    protocol_contract_identity,
    resolve_assignment,
)

import qml

T = TypeVar("T")

_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_NS = 1_700_000_000_000_000_000
_QML_PROTOCOL = Path(__file__).resolve().parents[1] / "src" / "qml" / "protocol"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _venue() -> VenueId:
    return _ok(VenueId.try_create("ctrader"))


def _instrument() -> Instrument:
    return _ok(Instrument.try_create(_venue(), "EURUSD"))


def _price(value: int) -> Price:
    return _ok(Price.try_create(value, _instrument(), 5))


def _delta(value: int) -> PriceDelta:
    return _ok(PriceDelta.try_create(value, _instrument(), 5))


def _r(numerator: int, denominator: int = 1) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, denominator, UnitKind.R_MULTIPLE))


def _reason() -> ReasonCode:
    return _ok(ReasonCode.try_create("breakout", "trend-follow"))


def _target() -> ExecutionTarget:
    return _ok(ExecutionTarget.try_create("live", _venue(), "acct-1"))


def _entry(*, advisory: Price | PriceDelta | None = None) -> EntryIntent:
    return _ok(
        EntryIntent.try_create(
            _instrument(),
            Direction.LONG,
            _reason(),
            _target(),
            proposed_r=_r(1),
            advisory_stop_proposal=advisory if advisory is not None else _delta(500),
        )
    )


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _declaration(*, permitted_exit_intents: object = ()) -> BotDefinition:
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
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
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
            permitted_exit_intents=permitted_exit_intents,
            logic_reference=logic,
        )
    )


def _present_series(instant: Instant, value: int = 1) -> dict[str, object]:
    return {
        "kind": "series",
        "samples": [
            {
                "presence": "present",
                "knowable_at": instant,
                "value": value,
            }
        ],
    }


def _surface(instant: Instant, payload: object) -> MappingReadSurface:
    return _ok(MappingReadSurface.try_create({instant: payload}))


def _silent_factory() -> FunctionFactory:
    return FunctionFactory(logic=lambda evidence: ())


def _entry_factory() -> FunctionFactory:
    def logic(evidence: FootprintEvidence) -> object:
        series = evidence.series.get("primary")
        if series is None or not series.samples:
            return ()
        if series.samples[-1].presence is not PresenceState.PRESENT:
            return ()
        return (_entry(),)

    return FunctionFactory(logic=logic)


# --- AC: QML-owned format-versioned contract --------------------------------


def test_protocol_is_qml_ad5_ladder_not_ct_numbered() -> None:
    assert PROTOCOL_FORMAT_VERSION == 1
    assert PROTOCOL_LADDER == "qml-ad5"
    assert PROTOCOL_CONTRACT_CLASS == "qml-bot-runtime-protocol"
    identity = protocol_contract_identity()
    assert "ct" not in identity
    assert "CT-" not in str(identity)
    assert identity["ladder"] == "qml-ad5"
    assert identity["contract_format_version"] == 1
    assert qml.__version__ not in identity.values()
    fp = _ok(fingerprint(identity))
    assert fp.value.startswith("fp1:sha256:")
    with_semver = _ok(fingerprint({**identity, "package_version": qml.__version__}))
    assert fp.value != with_semver.value


def test_unknown_protocol_format_version_is_unsupported_capability() -> None:
    refused = coerce_protocol_format_version(2)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    zero = coerce_protocol_format_version(0)
    assert is_refusal(zero)
    assert zero.category is RefusalCategory.INVALID_INPUT
    flag = coerce_protocol_format_version(True)
    assert is_refusal(flag)
    text = coerce_protocol_format_version("1")
    assert is_refusal(text)


def test_denial_set_matches_conformance() -> None:
    assert PROTOCOL_DENIAL_SET == DENIAL_SET
    assert frozenset({"clock", "io", "network", "undeclared_randomness"}) == PROTOCOL_DENIAL_SET


def test_bot_intent_is_the_ct23_door_types() -> None:
    assert set(get_args(BotIntent)) == {EntryIntent, ExitIntent}


# --- AC: factory (declaration, assignment, read surfaces) -> callback --------


def test_construct_bot_returns_hosted_callback_driven_per_instant() -> None:
    declaration = _declaration()
    hosted = _ok(
        construct_bot(
            _silent_factory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={},
        )
    )
    assert isinstance(hosted, HostedBot)
    assert hosted.protocol_format_version == PROTOCOL_FORMAT_VERSION
    intents = _ok(hosted.on_instant(_instant()))
    assert intents == ()


def test_construct_bot_refuses_unknown_protocol_version() -> None:
    refused = construct_bot(
        _silent_factory(),
        declaration=_declaration(),
        assignment={"lookback": 20},
        read_surfaces={},
        protocol_format_version=2,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_construct_bot_refuses_non_factory() -> None:
    refused = construct_bot(
        object(),
        declaration=_declaration(),
        assignment={"lookback": 20},
        read_surfaces={},
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_assignment_must_match_declared_space() -> None:
    declaration = _declaration()
    extra = resolve_assignment(declaration, {"lookback": 20, "ghost": 1})
    assert is_refusal(extra)
    missing = resolve_assignment(declaration, {})
    assert is_refusal(missing)
    bad_type = resolve_assignment(declaration, {"lookback": "20"})
    assert is_refusal(bad_type)
    out_of_bounds = resolve_assignment(declaration, {"lookback": 0})
    assert is_refusal(out_of_bounds)
    ok = resolve_assignment(declaration, {"lookback": 20})
    assert is_ok(ok)
    assert ok.value["lookback"] == 20


def test_read_surfaces_may_not_inject_undeclared_or_book_or_clock() -> None:
    declaration = _declaration()
    instant = _instant()
    extra = construct_bot(
        _silent_factory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={"ghost": _surface(instant, _present_series(instant))},
    )
    assert is_refusal(extra)
    assert extra.category is RefusalCategory.INVALID_INPUT
    book = construct_bot(
        _silent_factory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={"book": _surface(instant, _present_series(instant))},
    )
    assert is_refusal(book)
    clock = DataDrivenClock(boot_epoch_id="boot", wall_instants=(instant,), monotonic_ns=(0,))
    clocked = construct_bot(
        _silent_factory(),
        declaration=declaration,
        assignment={"lookback": 20},
        read_surfaces={"primary": clock},
    )
    assert is_refusal(clocked)


# --- AC: callback receives only declared footprint evidence ------------------


def test_callback_receives_presence_mapped_series_and_structure_fold() -> None:
    declaration = _declaration()
    instant = _instant()
    seen: list[FootprintEvidence] = []

    def logic(evidence: FootprintEvidence) -> object:
        seen.append(evidence)
        return ()

    producer_key = _ok(declaration.footprint.producer_bindings[0].fingerprint_content()).value
    hosted = _ok(
        construct_bot(
            FunctionFactory(logic=logic),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={
                "primary": _surface(instant, _present_series(instant, 7)),
                producer_key: _surface(
                    instant,
                    {
                        "kind": "structure_fold",
                        "knowable_at": instant,
                        "observed_at": instant,
                        "geometry": {"role": "level"},
                    },
                ),
            },
        )
    )
    _ok(hosted.on_instant(instant))
    assert len(seen) == 1
    evidence = seen[0]
    assert evidence.evaluation_instant == instant
    assert "primary" in evidence.series
    sample = evidence.series["primary"].samples[0]
    assert sample.presence is PresenceState.PRESENT
    assert sample.knowable_at == instant
    assert sample.value == 7
    assert producer_key in evidence.structure_folds
    assert evidence.structure_folds[producer_key].knowable_at == instant


def test_undeclared_evidence_key_and_look_ahead_are_invalid_input() -> None:
    declaration = _declaration()
    keys = _ok(declared_evidence_keys(declaration.footprint))
    assert "primary" in keys
    instant = _instant()
    later = _instant(_NS + 1)
    ahead = collect_evidence(
        {"primary": _surface(instant, _present_series(later, 1))},
        instant,
        declared_keys=keys,
    )
    assert is_refusal(ahead)
    assert ahead.category is RefusalCategory.INVALID_INPUT
    missing_known = SeriesSample.try_create("present", None, 1)
    assert is_refusal(missing_known)


def test_provisional_and_float_samples_are_refused() -> None:
    instant = _instant()
    provisional = SeriesSample.try_create("provisional", instant, 1)
    assert is_refusal(provisional)
    floated = SeriesSample.try_create("present", instant, 1.5)
    assert is_refusal(floated)
    fold_float = StructureFold.try_create("k", instant, geometry={"x": 1.0})
    assert is_refusal(fold_float)


def test_sample_requires_knowable_at() -> None:
    instant = _instant()
    present = _ok(SeriesSample.try_create(PresenceState.PRESENT, instant, 3))
    assert present.knowable_at == instant
    gap = _ok(SeriesSample.try_create("gap", instant))
    assert gap.value is None


# --- AC: zero-or-more CT-23 intents; advisory stop; no Book full-loss --------


def test_callback_returns_zero_or_more_ct23_intents() -> None:
    declaration = _declaration()
    instant = _instant()
    silent = _ok(
        construct_bot(
            _silent_factory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={"primary": _surface(instant, _present_series(instant))},
        )
    )
    assert _ok(silent.on_instant(instant)) == ()
    live = _ok(
        construct_bot(
            _entry_factory(),
            declaration=declaration,
            assignment={"lookback": 20},
            read_surfaces={"primary": _surface(instant, _present_series(instant))},
        )
    )
    intents = _ok(live.on_instant(instant))
    assert len(intents) == 1
    entry = intents[0]
    assert isinstance(entry, EntryIntent)
    assert entry.advisory_stop_proposal == _delta(500)
    assert not hasattr(entry, "requested_r")
    assert not hasattr(entry, "declared_full_loss_price")


def test_advisory_stop_is_advisory_full_loss_is_book_side() -> None:
    entry = _entry(advisory=_price(104000))
    accepted = _ok(accept_intents((entry,)))
    got = accepted[0]
    assert isinstance(got, EntryIntent)
    assert got.advisory_stop_proposal == _price(104000)
    refused = accept_intents(
        {
            "intent_family": "entry",
            "entry": entry,
            "declared_full_loss_price": _price(104000),
        }
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "declared_full_loss_price"


# --- AC: inbound requested_r and venue commands rejected ---------------------


def test_inbound_requested_r_is_invalid_input() -> None:
    refused = accept_intents(
        {
            "intent_family": "entry",
            "entry": _entry(),
            "requested_r": _r(2),
        }
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "requested_r"


def test_venue_command_through_the_door_is_rejected() -> None:
    refused = accept_intents({"venue_command": "place", "place": {"symbol": "EURUSD"}})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    partial = accept_intents({"kind": "close_partial"})
    assert is_refusal(partial)
    assert partial.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_exit_kind_must_be_in_declared_permitted_subset() -> None:
    fp = _ok(fingerprint({"class": "virtual-position"}))
    exit_intent = _ok(ExitIntent.try_create(ExitKind.CLOSE_FULL, _reason(), fp))
    entry_only = accept_intents((exit_intent,), permitted_exit_intents=())
    assert is_refusal(entry_only)
    assert entry_only.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    allowed = accept_intents((exit_intent,), permitted_exit_intents=("close_full",))
    assert is_ok(allowed)


# --- AC: identical (declaration, assignment, evidence sequence, state) --------


def test_identical_replay_yields_identical_intents() -> None:
    declaration = _declaration()
    t0 = _instant(_NS)
    t1 = _instant(_NS + 1)
    surfaces = {
        "primary": _ok(
            MappingReadSurface.try_create({t0: _present_series(t0), t1: _present_series(t1)})
        )
    }
    assignment = {"lookback": 20}

    def _run() -> tuple[tuple[object, ...], tuple[object, ...]]:
        hosted = _ok(
            construct_bot(
                _entry_factory(),
                declaration=declaration,
                assignment=assignment,
                read_surfaces=surfaces,
            )
        )
        first = _ok(hosted.on_instant(t0))
        second = _ok(hosted.on_instant(t1))
        return (
            tuple(intent_identity(item) for item in first),
            tuple(intent_identity(item) for item in second),
        )

    assert _run() == _run()


def test_stateful_callback_replays_identically_from_equal_start_state() -> None:
    declaration = _declaration()
    t0 = _instant(_NS)
    t1 = _instant(_NS + 1)

    class CounterFactory:
        def construct(
            self,
            *,
            declaration: object,
            assignment: object,
            read_surfaces: object,
        ) -> Result[object]:
            del declaration, assignment, read_surfaces

            class Counter:
                def __init__(self) -> None:
                    self.n = 0

                def on_instant(self, evidence: FootprintEvidence) -> object:
                    del evidence
                    self.n += 1
                    if self.n == 2:
                        return (_entry(),)
                    return ()

            return Counter()  # type: ignore[return-value]

    def replay() -> list[int]:
        hosted = _ok(
            construct_bot(
                CounterFactory(),
                declaration=declaration,
                assignment={"lookback": 20},
                read_surfaces={},
            )
        )
        a = _ok(hosted.on_instant(t0))
        b = _ok(hosted.on_instant(t1))
        return [len(a), len(b)]

    assert replay() == replay() == [0, 1]


def test_protocol_source_never_derives_full_loss_or_reads_a_clock() -> None:
    banned = ("derive_full_loss_price_at_door", "wall_now", "hashlib", "random")
    hits: list[str] = []
    for path in sorted(_QML_PROTOCOL.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in banned:
                hits.append(f"{path.name}:{node.id}")
            if isinstance(node, ast.Attribute) and node.attr in {"wall_now", "monotonic_now"}:
                hits.append(f"{path.name}:{node.attr}")
    assert hits == []


def test_on_instant_refuses_a_non_instant() -> None:
    hosted = _ok(
        construct_bot(
            _silent_factory(),
            declaration=_declaration(),
            assignment={"lookback": 20},
            read_surfaces={},
        )
    )
    refused = hosted.on_instant("now")  # type: ignore[arg-type]
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
