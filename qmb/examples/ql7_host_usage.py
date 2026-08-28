"""Reference usage — QL-7 adapter and QML-aware config compilation (Story 14.8).

Executable::

    python qmb/examples/ql7_host_usage.py

Shows the things Story 14.8 / QL-7 / DEC-0183 pin down:

1. A run spec citing a CT-33 Bot by fp1 constructs via qml.protocol.construct_bot
   / FunctionFactory / HostedBot and drives per evaluation instant with
   declared-footprint evidence only.
2. The B-3 compiler stamps assignment_is_canonical and resolves producer
   templates to one configured-producer fingerprint. A non-canonical assignment
   is a run-spec override, never a governed-seat execution.
3. Layer 2 runs at QMB's composition root and the pure QML verdict passes
   through unchanged.
4. An ungoverned plain-Python bot needs no QL-7 adapter; tunnel entry stays
   ungated by conformance.
"""

from __future__ import annotations

from typing import TypeVar, cast

from qmb.config import (
    ASSIGNMENT_IS_CANONICAL_KEY,
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    RESOLVED_PRODUCERS_KEY,
    STARTING_CAPITAL_KEY,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.host.sandbox import run_sandbox
from qmb.ledger import fold_canonical_assignment
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)
from qml.conformance import run_layer2_suite
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint, mint_producer_template
from qml.logic import mint_logic_identity
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    FunctionFactory,
    MappingReadSurface,
    construct_bot,
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
_DEFAULTS = {
    "account_id": "acct-replay",
    "clock": CLOCK_REPLAY,
    "data_provenance": PROVENANCE_RECORDED,
    "fill": "default-fill",
    "venue_id": "venue-replay",
}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _writer(stream: str) -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "authoring", stream, "boot-1"), "writer")


def _money_variable(name: str, minor: int) -> TemplateVariable:
    return _unwrap(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        ),
        f"variable {name}",
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _unwrap(TemplateSection.try_create(name, {variable.name: variable}), f"section {name}")


def _definition() -> BotDefinition:
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")
    zone_fp = _unwrap(fingerprint({"class": "example-producer", "tag": "zone"}), "zone fp")
    zone = _unwrap(ProducerBinding.try_create(zone_fp), "zone")
    template = _unwrap(
        mint_producer_template(
            {
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
                "calendar_requirements": [calendar],
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
        ),
        "template",
    )
    templated = _unwrap(ProducerBinding.try_create(template), "templated binding")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": zone}]),
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
            [zone, templated],
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
                    "name": "sma_period",
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


def _book() -> BookDefinition:
    return _unwrap(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _money_variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _money_variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _money_variable("q", 100)),
            },
        ),
        "book definition",
    )


def _bms() -> BmsDefinition:
    return _unwrap(
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
        ),
        "bms definition",
    )


def _definition_record(kind: str, definition: BookDefinition | BmsDefinition) -> RegistrationRecord:
    stamped = _unwrap(definition.fingerprint(), f"{kind} fp1")
    return _unwrap(
        RegistrationRecord.try_create(
            kind,
            definition.contract_format_version,
            (stamped,),
            definition.fp1_identity(),
            _writer(kind),
            0,
            _instant(),
        ),
        f"{kind} record",
    )


def main() -> None:
    definition = _definition()
    at = _instant()
    surface = _unwrap(MappingReadSurface.try_create({at: None}), "surface")
    hosted = _unwrap(
        qmb.construct_conformant_bot(
            FunctionFactory(logic=lambda evidence: ()),
            declaration=definition,
            assignment={"sma_period": 20},
            read_surfaces={"primary": surface},
        ),
        "hosted bot",
    )
    assert hosted.__class__.__name__ == "HostedBot"
    zero = _unwrap(qmb.drive_instant(hosted, at), "drive")
    assert zero == ()
    via_qml = _unwrap(
        construct_bot(
            FunctionFactory(logic=lambda evidence: ()),
            declaration=definition,
            assignment={"sma_period": 20},
            read_surfaces={"primary": surface},
        ),
        "qml construct_bot",
    )
    assert via_qml.__class__ is hosted.__class__
    print("factory constructed via construct_bot / FunctionFactory / HostedBot")
    print("driven per evaluation instant with declared-footprint evidence only")

    bot = _unwrap(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            [],
            definition.body(),
            _writer("bot-definition"),
            0,
            _instant(),
        ),
        "bot record",
    )
    book_record = _definition_record("book-definition", _book())
    bms_record = _definition_record("bms-definition", _bms())
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(),
            records=(book_record, bms_record, bot),
            pointers=(
                _unwrap(
                    DatedPointer.try_create("scalping", book_record.stable_id, _instant()),
                    "book pointer",
                ),
                _unwrap(
                    DatedPointer.try_create("breakout", bot.stable_id, _instant()),
                    "bot pointer",
                ),
            ),
        ),
        "as-of set",
    )
    port = _unwrap(
        RegistryReadPort.try_create(
            _unwrap(PassiveHub.try_create((as_of,)), "hub"),
            stale_evidence_severity=_SEVERITY,
        ),
        "port",
    )
    book_fragment = _unwrap(
        materialize_book_fragment(port, "scalping", _writer("config-fragment")),
        "book fragment",
    )
    bms_fragment = _unwrap(
        materialize_bms_fragment(port, bms_record.stable_id, _writer("config-fragment")),
        "bms fragment",
    )
    canonical = _unwrap(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults=_DEFAULTS,
        ),
        "canonical compile",
    )
    assert canonical.assignment_is_canonical is True
    producers = canonical.keys[RESOLVED_PRODUCERS_KEY]
    assert isinstance(producers, (list, tuple))
    items = cast("list[object] | tuple[object, ...]", producers)
    assert len(items) == 2
    assert all(isinstance(item, str) and item.startswith("fp1:sha256:") for item in items)
    print(f"assignment_is_canonical {canonical.keys[ASSIGNMENT_IS_CANONICAL_KEY]}")
    print("producer template resolved to one configured-producer fingerprint")

    overridden = _unwrap(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={
                "bot": bot.stable_id,
                STARTING_CAPITAL_KEY: _SEED,
                "assignment": {"sma_period": 21},
            },
            workspace_defaults=_DEFAULTS,
        ),
        "override compile",
    )
    assert overridden.assignment_is_canonical is False
    assert fold_canonical_assignment(overridden) == "miss"
    print("non-canonical assignment is a run-spec override, never a governed-seat execution")

    scope = _unwrap(
        mint_state_scope(
            os="windows-11",
            logic_identity=definition.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build="none",
        ),
        "scope",
    )
    qmb_verdict = _unwrap(
        run_sandbox(
            declaration=definition,
            source_tree=_SOURCE,
            state_scope=scope,
            state_bound=256,
            timeout_seconds=30,
        ),
        "qmb sandbox",
    )
    in_process = _unwrap(
        run_layer2_suite(
            declaration=definition,
            factory=FunctionFactory(logic=lambda evidence: ()),
            source_tree=_SOURCE,
            state_scope=scope,
            state_bound=256,
        ),
        "in-process QML verdict",
    )
    assert qmb_verdict.fp1_identity() == in_process.fp1_identity()
    print("Layer 2 verdict under QMB hosting passed through unchanged")

    stub = _unwrap(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            [],
            {"class": "bot-definition", "alias": "mean-reversion"},
            _writer("bot-definition"),
            1,
            _instant(),
        ),
        "ungoverned bot",
    )
    ungoverned_as_of = _unwrap(
        AsOfSet.try_create(
            _instant(_CREATED_NS + 1),
            records=(book_record, bms_record, stub),
            pointers=(
                _unwrap(
                    DatedPointer.try_create("research", stub.stable_id, _instant(_CREATED_NS + 1)),
                    "research pointer",
                ),
            ),
        ),
        "ungoverned as-of",
    )
    ungoverned_port = _unwrap(
        RegistryReadPort.try_create(
            _unwrap(PassiveHub.try_create((ungoverned_as_of,)), "ungoverned hub"),
            stale_evidence_severity=_SEVERITY,
        ),
        "ungoverned port",
    )
    ungoverned = _unwrap(
        compile_run_config(
            ungoverned_port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": stub.stable_id, STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults=_DEFAULTS,
        ),
        "ungoverned compile",
    )
    assert ungoverned.assignment_is_canonical is None
    assert ASSIGNMENT_IS_CANONICAL_KEY not in ungoverned.keys
    assert is_refusal(
        qmb.construct_conformant_bot(
            FunctionFactory(logic=lambda evidence: ()),
            declaration={"class": "bot-definition", "alias": "mean-reversion"},
            assignment={},
            read_surfaces={},
        )
    )
    print("ungoverned plain-Python bot needs no QL-7 adapter; tunnel entry ungated")
    print("ql7 host ok")


if __name__ == "__main__":
    main()
