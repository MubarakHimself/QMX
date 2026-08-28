"""Story 14.8 — QL-7 adapter, DEC-0183 compiler stamps, Layer-2 hosting."""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from typing import TypeVar

from qmb.config import (
    ASSIGNMENT_IS_CANONICAL_KEY,
    ASSIGNMENT_KEY,
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    RESOLVED_PRODUCERS_KEY,
    STARTING_CAPITAL_KEY,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.doors import api
from qmb.host import run_sandbox as public_run_sandbox
from qmb.host.sandbox import run_sandbox
from qmb.ledger import (
    CANONICAL_ASSIGNMENT_CANONICAL,
    CANONICAL_ASSIGNMENT_MISS,
    CANONICAL_ASSIGNMENT_NOT_YET_RULED,
    fold_canonical_assignment,
)
from qmb.optimize import parameter_space_from_bot
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.runloop import EventSlice, SliceObservation, StreamSet, run_slice
from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import ExactRational, Money, PriceDelta, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.paper import ExecutionTarget
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)
from qml.conformance import run_layer2_suite
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint, mint_producer_template, resolve_template
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    FunctionFactory,
    MappingReadSurface,
    PresenceState,
    mint_state_scope,
)

import qmb

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_SOURCE = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_CLEAN = _SOURCE


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(stream: str = "config-fragment") -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", stream, "boot-1"))


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return _ok(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        )
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _ok(TemplateSection.try_create(name, {variable.name: variable}))


def _book() -> BookDefinition:
    return _ok(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
            },
        )
    )


def _bms() -> BmsDefinition:
    return _ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section(
                    "accounting_rules", _money_variable("numeraire_unit", 1)
                ),
                "constraints": _section("constraints", _money_variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _money_variable("posture", 1)),
                "reporting": _section("reporting", _money_variable("cadence", 1)),
            },
        )
    )


def _record(
    kind: str, body: Mapping[str, object] | BookDefinition | BmsDefinition
) -> RegistrationRecord:
    if isinstance(body, (BookDefinition, BmsDefinition)):
        parents: tuple[object, ...] = (_ok(body.fingerprint()),)
        payload: Mapping[str, object] = body.fp1_identity()
        version = body.contract_format_version
    else:
        parents = ()
        payload = dict(body)
        version = 1
    return _ok(
        RegistrationRecord.try_create(
            kind,
            version,
            parents,
            payload,
            _writer(kind),
            0,
            _instant(),
        )
    )


def _period(numerator: int = 20) -> ExactRational:
    return _ok(ExactRational.try_create(numerator, 1, UnitKind.COUNT))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "qmb-test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _template_fields(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "inputs": [
            {
                "name": "close",
                "source": {"kind": "instrument", "venue": "venue-ic", "symbol": "EURUSD"},
                "bar_spec": {"kind": "time-interval", "seconds": 60},
                "channel_kind": "exact-price",
                "quote_side": "mid",
            }
        ],
        "calendar_requirements": [_calendar()],
        "alignment_policy": "as-of",
        "missing_value_policy": "mark-gap",
        "warm_up": 20,
        "output_schema": [
            {
                "name": "sma",
                "channel_kind": "float-analytic",
                "arity": "scalar-per-sample",
                "index_offset": 0,
            }
        ],
        "supported_modes": ["batch", "streaming"],
        "arithmetic_reference_configuration": {
            "c_library": "ta-lib-c@sha256:aaaa",
            "python_wrapper": "ta-lib-py@sha256:bbbb",
            "reference_configuration": {
                "compatibility_mode": "classic",
                "candle_settings": "default",
            },
        },
        "space_bound": {"period": "sma_period"},
    }
    fields.update(overrides)
    return fields


def _definition() -> BotDefinition:
    zone = _pinned("zone")
    template = _ok(mint_producer_template(_template_fields()))
    templated = _ok(ProducerBinding.try_create(template))
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = _ok(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [_calendar()],
            [zone, templated],
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
                },
                {
                    "name": "sma_period",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 200},
                    "step": 1,
                    "default": 20,
                    "unit_kind": UnitKind.COUNT,
                    "ui": "ui-editable",
                },
            ],
            footprint=footprint,
            permitted_exit_intents=(),
            logic_reference=logic,
        )
    )


def _defaults() -> dict[str, object]:
    return {
        "account_id": "acct-replay",
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "fill": "default-fill",
        "venue_id": "venue-replay",
    }


def _fragments_with_bot(bot: RegistrationRecord):
    book = _book()
    bms = _bms()
    book_record = _record("book-definition", book)
    bms_record = _record("bms-definition", bms)
    pointer = _ok(DatedPointer.try_create("breakout", bot.stable_id, _instant()))
    book_pointer = _ok(DatedPointer.try_create("scalping", book_record.stable_id, _instant()))
    as_of = _ok(
        AsOfSet.try_create(
            _instant(),
            records=(book_record, bms_record, bot),
            pointers=(pointer, book_pointer),
        )
    )
    port = _ok(
        RegistryReadPort.try_create(
            _ok(PassiveHub.try_create((as_of,))),
            stale_evidence_severity=_SEVERITY,
        )
    )
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    return book_fragment, bms_fragment, port, bot


def _ct33_record():
    definition = _definition()
    return definition, _record("bot-definition", definition.body())


def _compile_ct33(*, run_spec: Mapping[str, object] | None = None):
    definition, bot = _ct33_record()
    book, bms, port, _rec = _fragments_with_bot(bot)
    spec: dict[str, object] = {
        "bot": bot.stable_id,
        STARTING_CAPITAL_KEY: _SEED,
    }
    if run_spec is not None:
        spec.update(run_spec)
        spec.setdefault("bot", bot.stable_id)
        spec.setdefault(STARTING_CAPITAL_KEY, _SEED)
    compiled = compile_run_config(
        port,
        book_fragment=book,
        bms_fragment=bms,
        run_spec=spec,
        workspace_defaults=_defaults(),
    )
    return definition, bot, compiled


def _silent_factory() -> FunctionFactory:
    return FunctionFactory(logic=lambda evidence: ())


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
            advisory_stop_proposal=stop,
        )
    )


def _present(instant: Instant) -> dict[str, object]:
    return {
        "kind": "series",
        "samples": [{"presence": PresenceState.PRESENT.value, "knowable_at": instant, "value": 1}],
    }


def _scope(declaration: BotDefinition) -> object:
    return _ok(
        mint_state_scope(
            os="windows-11",
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build="none",
        )
    )


def test_construct_via_ql7_factory_and_drive_declared_footprint_only() -> None:
    definition = _definition()
    at = _instant()
    hosted = _ok(
        qmb.construct_conformant_bot(
            qmb.FunctionFactory(logic=lambda evidence: (_entry(),) if evidence.series else ()),
            declaration=definition,
            assignment={"lookback": 20, "sma_period": 20},
            read_surfaces={
                "primary": _ok(MappingReadSurface.try_create({at: _present(at)})),
            },
        )
    )
    assert isinstance(hosted, qmb.HostedBot)
    intents = _ok(qmb.drive_instant(hosted, at))
    assert len(intents) == 1
    assert isinstance(intents[0], EntryIntent)
    assert intents[0].advisory_stop_proposal is not None
    booked = qmb.construct_conformant_bot(
        _silent_factory(),
        declaration=definition,
        assignment={"lookback": 20, "sma_period": 20},
        read_surfaces={
            "primary": _ok(MappingReadSurface.try_create({at: _present(at)})),
            "book": _ok(MappingReadSurface.try_create({at: None})),
        },
    )
    assert is_refusal(booked)
    assert booked.category is RefusalCategory.INVALID_INPUT


def test_compiler_stamps_canonical_assignment_and_resolves_templates() -> None:
    definition, _bot, compiled = _compile_ct33()
    resolved = _ok(compiled)
    assert resolved.assignment_is_canonical is True
    assert resolved.keys[ASSIGNMENT_IS_CANONICAL_KEY] is True
    assignment = resolved.keys[ASSIGNMENT_KEY]
    assert isinstance(assignment, Mapping)
    assert assignment["lookback"] == 20
    expected = _ok(
        resolve_template(
            definition.footprint.producer_bindings[1].template,
            {
                "sma_period": _period(20),
            },
        )
    )
    producers = resolved.keys[RESOLVED_PRODUCERS_KEY]
    pinned = definition.footprint.producer_bindings[0].pinned
    assert pinned is not None
    assert producers == (pinned.value, _ok(expected.fingerprint_content()).value)
    again = _ok(_compile_ct33()[2])
    assert again.fingerprint == resolved.fingerprint
    assert fold_canonical_assignment(resolved) == CANONICAL_ASSIGNMENT_CANONICAL
    space = _ok(parameter_space_from_bot(definition))
    assert [spec.name for spec in space] == ["lookback", "sma_period"]


def test_non_canonical_assignment_is_run_spec_override() -> None:
    _definition, _bot, compiled = _compile_ct33(
        run_spec={"assignment": {"lookback": 21, "sma_period": 21}}
    )
    resolved = _ok(compiled)
    assert resolved.assignment_is_canonical is False
    assignment = resolved.keys[ASSIGNMENT_KEY]
    assert isinstance(assignment, Mapping)
    assert assignment["lookback"] == 21
    assert fold_canonical_assignment(resolved) == CANONICAL_ASSIGNMENT_MISS
    refused = _compile_ct33(run_spec={ASSIGNMENT_IS_CANONICAL_KEY: True})[2]
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == ASSIGNMENT_IS_CANONICAL_KEY


def test_ungoverned_plain_python_bot_needs_no_ql7_adapter() -> None:
    stub = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    book, bms, port, bot = _fragments_with_bot(stub)
    compiled = _ok(
        compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults=_defaults(),
        )
    )
    assert compiled.assignment_is_canonical is None
    assert ASSIGNMENT_IS_CANONICAL_KEY not in compiled.keys
    assert RESOLVED_PRODUCERS_KEY not in compiled.keys
    assert fold_canonical_assignment(compiled) == CANONICAL_ASSIGNMENT_NOT_YET_RULED
    at = _instant()
    outcome = _ok(
        run_slice(
            _ok(EventSlice.try_create((_ok(SliceObservation.try_create("eurusd", at, True)),))),
            stream_set=_ok(StreamSet.try_create(("eurusd",))),
        )
    )
    assert outcome.minted == ()
    assert fold_canonical_assignment(compiled) == CANONICAL_ASSIGNMENT_NOT_YET_RULED


def test_conformant_slice_handler_mints_on_declared_stream() -> None:
    definition = _definition()
    at = _instant()
    hosted = _ok(
        qmb.construct_conformant_bot(
            FunctionFactory(logic=lambda evidence: (_entry(),)),
            declaration=definition,
            assignment={"lookback": 20, "sma_period": 20},
            read_surfaces={"primary": _ok(MappingReadSurface.try_create({at: _present(at)}))},
        )
    )
    handler = qmb.ConformantSliceHandler(hosted=hosted, stream_id="eurusd")
    outcome = _ok(
        run_slice(
            _ok(EventSlice.try_create((_ok(SliceObservation.try_create("eurusd", at, True)),))),
            stream_set=_ok(StreamSet.try_create(("eurusd",))),
            handler=handler,
        )
    )
    assert len(outcome.minted) == 1
    assert outcome.resting[-1].stream_id == "eurusd"
    assert outcome.subphase_order()[-2] == "strategy-callbacks"


def test_layer2_under_qmb_hosting_passes_verdict_through_unchanged() -> None:
    declaration = _definition()
    in_process = _ok(
        run_layer2_suite(
            declaration=declaration,
            factory=FunctionFactory(logic=lambda evidence: ()),
            source_tree=_CLEAN,
            state_scope=_scope(declaration),
            state_bound=256,
        )
    )
    hosted = _ok(
        run_sandbox(
            declaration=declaration,
            source_tree=_CLEAN,
            state_scope=_scope(declaration),
            state_bound=256,
            timeout_seconds=30,
        )
    )
    assert hosted.fp1_identity() == in_process.fp1_identity()
    assert run_sandbox is public_run_sandbox
    assert "host" not in hosted.fp1_identity()
    names = inspect.signature(run_sandbox).parameters
    assert "book" not in names
    assert "verdict" not in names
    assert not hasattr(qmb, "run_sandbox")
    assert qmb.construct_conformant_bot is api.construct_conformant_bot
    assert qmb.drive_instant is api.drive_instant
    assert qmb.fold_canonical_assignment is api.fold_canonical_assignment
