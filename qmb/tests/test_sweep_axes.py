"""Story 20.1 — sweep axis declaration, Cartesian expansion, pre-flight run count."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import TypeVar, cast

from click.testing import CliRunner
from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
    ConfigFragment,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.doors import CAPABILITY_LIBRARY, api, flatten_capabilities, required_library_names
from qmb.doors.cli import invoke_sweep_count, main
from qmb.doors.cli.tree import command_tree
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.runloop import STREAM_SET_KEY, DeclaredBarSpec, StreamSet, stream_set_from_config
from qmb.sweep import (
    PREFLIGHT_ADMITS_BATCH,
    PREFLIGHT_IS_PURE_INSPECTION,
    PREFLIGHT_SPAWNS_PROCESS,
    PREFLIGHT_WRITES_LEDGER_LINE,
    SWEEP_DECLARATION_CLASS,
    SWEEP_RUN_SPEC_CLASS,
    SweepDeclaration,
    SweepRunSpec,
    expand_sweep,
    preflight_run_count,
    sweep_axes_identity,
)
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, Money, RoundingMode, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_TF_1M = {"kind": "time-interval", "seconds": 60}
_TF_5M = {"kind": "time-interval", "seconds": 300}
_TF_15M = {"kind": "time-interval", "seconds": 900}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(stream: str = "config-fragment") -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", stream, "boot-1"))


def _declaration(
    *,
    bot: object = "mean-reversion",
    book: object = "scalping",
    bms: object = "acct-1",
    instruments: object = ("EURUSD", "GBPUSD"),
    timeframes: object = (_TF_1M, _TF_5M),
    parameters: object = None,
) -> Result[SweepDeclaration]:
    return SweepDeclaration.try_create(
        bot=bot,
        book=book,
        bms=bms,
        instruments=instruments,
        timeframes=timeframes,
        parameters=parameters,
    )


# --- AC1: Cartesian expansion in deterministic declaration order --------------


def test_expansion_is_the_full_cartesian_product_in_declaration_order() -> None:
    decl = _ok(_declaration(parameters={"lookback": [10, 20, 30], "use_atr": [True, False]}))
    combos = _ok(expand_sweep(decl))
    assert len(combos) == 2 * 2 * 3 * 2 == 24
    # Instruments vary slowest; the last-declared parameter (use_atr) varies fastest.
    assert combos[0].instrument == "EURUSD"
    assert combos[0].timeframe.parameters["seconds"] == 60
    assert combos[0].parameters == {"lookback": 10, "use_atr": True}
    assert combos[1].parameters == {"lookback": 10, "use_atr": False}
    assert combos[2].parameters == {"lookback": 20, "use_atr": True}
    assert combos[6].instrument == "EURUSD"
    assert combos[6].timeframe.parameters["seconds"] == 300
    assert combos[12].instrument == "GBPUSD"
    assert combos[-1].instrument == "GBPUSD"
    assert combos[-1].parameters == {"lookback": 30, "use_atr": False}


def test_every_combination_is_a_distinct_run_spec() -> None:
    decl = _ok(_declaration(parameters={"lookback": [10, 20, 30]}))
    combos = _ok(expand_sweep(decl))
    fingerprints = {_ok(combo.fingerprint()).value for combo in combos}
    assert len(fingerprints) == len(combos) == 12
    for combo in combos:
        assert isinstance(combo, SweepRunSpec)
        assert combo.fp1_identity()["class"] == SWEEP_RUN_SPEC_CLASS


def test_expansion_and_count_are_deterministic() -> None:
    params: dict[str, object] = {"lookback": [10, 20], "mode": ["a", "b"]}
    decl = _ok(_declaration(parameters=params))
    twin = _ok(_declaration(parameters={"lookback": [10, 20], "mode": ["a", "b"]}))
    first = _ok(expand_sweep(decl))
    second = _ok(expand_sweep(decl))
    assert [c.fp1_identity() for c in first] == [c.fp1_identity() for c in second]
    assert _ok(decl.fingerprint()) == _ok(twin.fingerprint())


def test_single_run_is_a_unit_scale_sweep() -> None:
    unit = _ok(_declaration(instruments=["EURUSD"], timeframes=[_TF_1M]))
    combos = _ok(expand_sweep(unit))
    assert len(combos) == 1
    assert unit.run_count == 1
    only = combos[0]
    assert only.instrument == "EURUSD"
    assert only.parameters == {}
    assert isinstance(only, SweepRunSpec)


def test_a_bare_declared_barspec_is_accepted_as_a_unit_axis() -> None:
    spec = _ok(DeclaredBarSpec.try_create(_TF_1M))
    unit = _ok(_declaration(instruments=["EURUSD"], timeframes=spec))
    combos = _ok(expand_sweep(unit))
    assert len(combos) == 1
    assert combos[0].timeframe == spec


# --- AC2: pre-flight run count is a pure inspection ---------------------------


def test_preflight_count_is_the_product_of_axis_lengths() -> None:
    decl = _ok(
        _declaration(
            instruments=["EURUSD", "GBPUSD", "USDJPY"],
            timeframes=[_TF_1M, _TF_5M],
            parameters={"lookback": [10, 20, 30, 40], "use_atr": [True, False]},
        )
    )
    assert _ok(preflight_run_count(decl)) == 3 * 2 * 4 * 2 == 48
    assert decl.run_count == 48
    assert len(_ok(expand_sweep(decl))) == 48


def test_preflight_count_accepts_the_raw_axis_mapping() -> None:
    count = preflight_run_count(
        {
            "bot": "mean-reversion",
            "book": "scalping",
            "bms": "acct-1",
            "instruments": ["EURUSD", "GBPUSD"],
            "timeframes": [_TF_1M, _TF_5M, _TF_15M],
            "parameters": {"lookback": [10, 20]},
        }
    )
    assert _ok(count) == 2 * 3 * 2 == 12


def test_preflight_is_a_pure_inspection() -> None:
    assert PREFLIGHT_SPAWNS_PROCESS is False
    assert PREFLIGHT_WRITES_LEDGER_LINE is False
    assert PREFLIGHT_ADMITS_BATCH is False
    assert PREFLIGHT_IS_PURE_INSPECTION is True
    identity = sweep_axes_identity()
    assert identity["preflight_spawns_process"] is False
    assert identity["preflight_writes_ledger_line"] is False
    assert identity["preflight_admits_batch"] is False
    assert identity["preflight_is_pure_inspection"] is True
    assert identity["declaration_class"] == SWEEP_DECLARATION_CLASS
    assert qmb.__version__ not in identity.values()
    assert is_ok(fingerprint(identity))


# --- AC3: the qmb door is a thin wrapper over the one library function --------


def test_door_count_equals_the_library_and_lives_once() -> None:
    decl = _ok(_declaration(parameters={"lookback": [10, 20, 30]}))
    library = _ok(preflight_run_count(decl))
    assert _ok(invoke_sweep_count(declaration=decl)) == library
    assert _ok(api.preflight_run_count(decl)) == library
    assert api.preflight_run_count is qmb.preflight_run_count
    assert api.expand_sweep is qmb.expand_sweep


def test_sweep_count_is_catalogued_and_on_both_doors() -> None:
    assert "sweep.count" in CAPABILITY_LIBRARY
    assert CAPABILITY_LIBRARY["sweep.count"] == ("preflight_run_count",)
    assert "sweep.count" in flatten_capabilities()
    assert command_tree()["sweep"] == ("count",)
    for name in CAPABILITY_LIBRARY["sweep.count"]:
        assert name in required_library_names()
        assert hasattr(api, name)
        assert name in api.__all__
        assert name in qmb.__all__


def test_cli_sweep_count_renders_the_library_count() -> None:
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        [
            "sweep",
            "count",
            "mean-reversion",
            "--book",
            "scalping",
            "--bms",
            "acct-1",
            "--instrument",
            "EURUSD",
            "--instrument",
            "GBPUSD",
            "--seconds",
            "60",
            "--seconds",
            "300",
        ],
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    assert clicked.stdout.strip() == "4"


def test_cli_sweep_count_refusal_is_nonzero_stderr_json() -> None:
    runner = CliRunner()
    clicked = runner.invoke(main, ["sweep", "count", "mean-reversion"])
    assert clicked.exit_code != 0
    assert clicked.stdout.strip() == ""
    body = cast("dict[str, object]", json.loads(clicked.stderr))
    assert body["category"] in {
        RefusalCategory.INVALID_INPUT.value,
        RefusalCategory.UNAVAILABLE_DEPENDENCY.value,
    }


def test_cli_sweep_count_takes_a_prebuilt_declaration_from_the_object() -> None:
    decl = _ok(_declaration(parameters={"lookback": [10, 20, 30]}))
    runner = CliRunner()
    clicked = runner.invoke(main, ["sweep", "count"], obj={"declaration": decl})
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stdout.strip() == "12"


def test_invoke_sweep_count_refuses_a_missing_declaration() -> None:
    refused = invoke_sweep_count()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# --- AC4: an empty axis is a typed invalid-input refusal naming the axis ------


def test_empty_instrument_axis_refuses_naming_the_axis() -> None:
    refused = _declaration(instruments=[])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "instruments"


def test_empty_barspec_axis_refuses_naming_the_axis() -> None:
    refused = _declaration(timeframes=[])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "timeframes"


def test_empty_parameter_value_axis_refuses_naming_the_parameter() -> None:
    refused = _declaration(parameters={"lookback": []})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "parameters"
    assert refused.context["parameter"] == "lookback"


def test_non_sequence_axes_refuse() -> None:
    assert is_refusal(_declaration(instruments="EURUSD"))
    assert is_refusal(_declaration(timeframes="1m"))
    assert is_refusal(_declaration(parameters=["not", "a", "map"]))
    bad_values = _declaration(parameters={"lookback": "123"})
    assert is_refusal(bad_values)
    assert bad_values.context["parameter"] == "lookback"


def test_blank_instrument_and_parameter_name_refuse() -> None:
    assert is_refusal(_declaration(instruments=["EURUSD", "  "]))
    assert is_refusal(_declaration(parameters={"   ": [1, 2]}))


def test_duplicate_axis_entries_refuse() -> None:
    dup_instruments = _declaration(instruments=["EURUSD", "EURUSD"])
    assert is_refusal(dup_instruments)
    assert dup_instruments.context["field"] == "instruments"
    dup_bars = _declaration(timeframes=[_TF_1M, dict(_TF_1M)])
    assert is_refusal(dup_bars)
    assert dup_bars.context["field"] == "timeframes"
    dup_values = _declaration(parameters={"lookback": [10, 10]})
    assert is_refusal(dup_values)
    assert dup_values.context["parameter"] == "lookback"


def test_missing_context_cite_refuses() -> None:
    assert is_refusal(_declaration(bot=None))
    assert is_refusal(_declaration(book="   "))
    assert is_refusal(_declaration(bms=42))
    non_barspec = _declaration(timeframes=[{"kind": "not-a-kind"}])
    assert is_refusal(non_barspec)
    assert non_barspec.context["field"] == "timeframes"


def test_context_may_be_cited_by_fp1_fingerprint() -> None:
    bot_fp1 = _ok(fingerprint({"n": "bot"}))
    decl = _ok(_declaration(bot=bot_fp1, instruments=["EURUSD"], timeframes=[_TF_1M]))
    assert decl.bot == bot_fp1.value
    assert decl.fp1_identity()["bot"] == bot_fp1.value


def test_a_non_mapping_declaration_refuses() -> None:
    refused = preflight_run_count(["not", "a", "declaration"])
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "declaration"
    assert is_refusal(expand_sweep(42))


# --- AC5: exact values verbatim; money/rational cross a named conversion ------


def test_exact_integer_categorical_and_boolean_are_carried_verbatim() -> None:
    decl = _ok(
        _declaration(
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
            parameters={"lookback": [10, 20], "mode": ["fast", "slow"], "use_atr": [True, False]},
        )
    )
    combos = _ok(expand_sweep(decl))
    first = combos[0]
    assert first.parameters["lookback"] == 10
    assert first.parameters["mode"] == "fast"
    assert first.parameters["use_atr"] is True
    identity = first.fp1_identity()["parameters"]
    assert identity == {"lookback": 10, "mode": "fast", "use_atr": True}


def test_money_value_crosses_a_named_conversion_before_entering_the_run_spec() -> None:
    decl = _ok(
        _declaration(
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
            parameters={
                "stop": [
                    {
                        "kind": "money",
                        "value": 1.5,
                        "currency": "USD",
                        "scale": 2,
                        "rounding": "half-up",
                    }
                ]
            },
        )
    )
    run = _ok(expand_sweep(decl))[0]
    stop = run.parameters["stop"]
    assert isinstance(stop, Money)
    assert stop == Money(value=150, currency="USD", scale=2)
    # The identity content is the exact reduced rational — no binary float.
    stop_identity = cast("Mapping[str, object]", run.fp1_identity()["parameters"])["stop"]
    assert stop_identity == stop.fp1_identity()
    assert _ok(run.fingerprint()).value.startswith("fp1:sha256:")


def test_rational_value_crosses_a_named_conversion() -> None:
    decl = _ok(
        _declaration(
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
            parameters={
                "atr_mult": [
                    {
                        "kind": "rational",
                        "value": 2.5,
                        "unit_kind": "dimensionless-ratio",
                        "scale": 1,
                        "rounding": "half-up",
                    }
                ]
            },
        )
    )
    run = _ok(expand_sweep(decl))[0]
    mult = run.parameters["atr_mult"]
    assert isinstance(mult, ExactRational)
    assert mult.as_fraction().numerator == 5
    assert mult.as_fraction().denominator == 2


def test_already_exact_money_and_rational_instances_are_carried_verbatim() -> None:
    money = Money(value=250, currency="USD", scale=2)
    rational = _ok(ExactRational.try_create(3, 4, UnitKind.DIMENSIONLESS_RATIO))
    decl = _ok(
        _declaration(
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
            parameters={"stop": [money], "ratio": [rational]},
        )
    )
    run = _ok(expand_sweep(decl))[0]
    assert run.parameters["stop"] is money
    assert run.parameters["ratio"] is rational


def test_a_bare_binary_float_is_refused() -> None:
    refused = _declaration(instruments=["EURUSD"], timeframes=[_TF_1M], parameters={"stop": [1.5]})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["parameter"] == "stop"


def test_conversion_spec_validation() -> None:
    base: dict[str, object] = {
        "instruments": ["EURUSD"],
        "timeframes": [_TF_1M],
    }
    bad_kind = _declaration(
        parameters={"x": [{"kind": "price", "value": 1.0, "scale": 2, "rounding": "half-up"}]},
        **base,
    )
    assert is_refusal(bad_kind)
    non_float = _declaration(
        parameters={
            "x": [{"kind": "money", "value": 100, "currency": "USD", "scale": 2, "rounding": "up"}]
        },
        **base,
    )
    assert is_refusal(non_float)
    assert non_float.context["parameter"] == "x"
    missing_rounding = _declaration(
        parameters={"x": [{"kind": "money", "value": 1.0, "currency": "USD", "scale": 2}]},
        **base,
    )
    assert is_refusal(missing_rounding)
    bad_currency = _declaration(
        parameters={"x": [{"kind": "money", "value": 1.0, "scale": 2, "rounding": "up"}]},
        **base,
    )
    assert is_refusal(bad_currency)
    bad_unit_kind = _declaration(
        parameters={"x": [{"kind": "rational", "value": 1.0, "scale": 2, "rounding": "up"}]},
        **base,
    )
    assert is_refusal(bad_unit_kind)


def test_from_float_infinity_refusal_propagates_through_the_conversion() -> None:
    refused = _declaration(
        instruments=["EURUSD"],
        timeframes=[_TF_1M],
        parameters={
            "x": [
                {
                    "kind": "money",
                    "value": float("inf"),
                    "currency": "USD",
                    "scale": 2,
                    "rounding": "half-up",
                }
            ]
        },
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["parameter"] == "x"


def test_an_unsupported_value_type_refuses() -> None:
    refused = _declaration(
        instruments=["EURUSD"], timeframes=[_TF_1M], parameters={"x": [object()]}
    )
    assert is_refusal(refused)
    assert refused.context["parameter"] == "x"


# --- run-spec shape: stream set and the compile layer -------------------------


def test_run_spec_stream_set_names_the_single_instrument() -> None:
    run = _ok(expand_sweep(_ok(_declaration(instruments=["EURUSD"], timeframes=[_TF_1M]))))[0]
    stream_set = _ok(run.stream_set())
    assert isinstance(stream_set, StreamSet)
    assert stream_set.stream_ids == ("EURUSD",)
    layer = run.run_spec_layer()
    assert layer["bot"] == "mean-reversion"
    assert layer[STREAM_SET_KEY] == [
        {"stream_id": "EURUSD", "instrument_id": "EURUSD", "role": "trading"}
    ]


def test_frozen_declaration_and_run_spec_reject_mutation() -> None:
    decl = _ok(_declaration(parameters={"lookback": [10]}))
    values = decl.parameters["lookback"]
    assert isinstance(values, tuple)
    run = _ok(expand_sweep(decl))[0]
    assert isinstance(run.parameters, Mapping)
    assert run.parameters["lookback"] == 10


# --- AC1 / R13: the 1x1x1 run spec compiles the same way a run-config does ----


def _book() -> BookDefinition:
    def _variable(name: str, minor: int) -> TemplateVariable:
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

    return _ok(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _variable("q", 100)),
            },
        )
    )


def _bms() -> BmsDefinition:
    def _variable(name: str, minor: int) -> TemplateVariable:
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

    return _ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section("accounting_rules", _variable("numeraire_unit", 1)),
                "constraints": _section("constraints", _variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _variable("posture", 1)),
                "reporting": _section("reporting", _variable("cadence", 1)),
            },
        )
    )


def _record(kind: str, body: object) -> RegistrationRecord:
    if isinstance(body, (BookDefinition, BmsDefinition)):
        parents: tuple[object, ...] = (_ok(body.fingerprint()),)
        payload: Mapping[str, object] = body.fp1_identity()
        version = body.contract_format_version
    else:
        parents = ()
        payload = cast("Mapping[str, object]", body)
        version = 1
    return _ok(
        RegistrationRecord.try_create(kind, version, parents, payload, _writer(kind), 0, _instant())
    )


def _fixtures() -> tuple[ConfigFragment, ConfigFragment, RegistryReadPort]:
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointers = (
        _ok(DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant())),
        _ok(DatedPointer.try_create("scalping", book_record.stable_id, _instant())),
    )
    as_of = _ok(
        AsOfSet.try_create(
            _instant(), records=(book_record, bms_record, bot_record), pointers=pointers
        )
    )
    hub = _ok(PassiveHub.try_create((as_of,)))
    port = _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    return book_fragment, bms_fragment, port


def test_unit_scale_run_spec_compiles_the_same_way_a_run_config_does() -> None:
    book_fragment, bms_fragment, port = _fixtures()
    unit = _ok(
        _declaration(
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
            parameters={"lookback": [10]},
        )
    )
    run = _ok(expand_sweep(unit))[0]

    def _compile() -> Result[ResolvedRunConfig]:
        return compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec=run.run_spec_layer(),
            invocation_flags={STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults={
                "account_id": "acct-replay",
                "clock": CLOCK_REPLAY,
                "data_provenance": PROVENANCE_RECORDED,
                "venue_id": "venue-replay",
            },
        )

    config = _ok(_compile())
    again = _ok(_compile())
    assert config.fingerprint == again.fingerprint
    assert config.keys["lookback"] == 10
    # The compiled config carries this run's single-instrument stream set (B-12).
    resolved_streams = _ok(stream_set_from_config(config))
    assert resolved_streams.stream_ids == ("EURUSD",)


def test_conversion_uses_the_declared_rounding_mode() -> None:
    # 1.235 at scale 2 rounds up under half-up (0.005 tie away from zero).
    decl = _ok(
        _declaration(
            instruments=["EURUSD"],
            timeframes=[_TF_1M],
            parameters={
                "stop": [
                    {
                        "kind": "money",
                        "value": 1.005,
                        "currency": "USD",
                        "scale": 2,
                        "rounding": RoundingMode.FLOOR.value,
                    }
                ]
            },
        )
    )
    run = _ok(expand_sweep(decl))[0]
    stop = run.parameters["stop"]
    assert isinstance(stop, Money)
    # 1.005 is stored as a binary float slightly below 1.005; floor at scale 2 -> 1.00.
    assert stop == Money(value=100, currency="USD", scale=2)
