"""Story 21.1 — typed parameter search space schema, validated at Study creation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.doors import api
from qmb.optimize import (
    STUDY_SPACE_CLASS,
    STUDY_SPACE_FORMAT_VERSION,
    STUDY_SPACE_KEY,
    StudyParameterSpace,
    coerce_study_space,
    study_space_from_bot,
    study_space_identity,
)
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)
from qml.declaration import mint_bot_definition, mint_confluence
from qml.declaration.bot import BotDefinition
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_DEFAULTS = {
    "account_id": "acct-replay",
    "clock": CLOCK_REPLAY,
    "data_provenance": PROVENANCE_RECORDED,
    "fill": "default-fill",
    "venue_id": "venue-replay",
}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refused(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


# --- parameter declarations (read through the one CT-33 schema) ----------------


def _int_param(
    name: str = "lookback", *, low: int = 1, high: int = 200, step: int = 1
) -> dict[str, object]:
    return {
        "name": name,
        "type": "exact integer",
        "bounds": {"min": low, "max": high},
        "step": step,
        "default": low,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _rational_param(name: str = "atr_mult") -> dict[str, object]:
    return {
        "name": name,
        "type": "exact rational",
        "bounds": {
            "min": {"num": 5, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
            "max": {"num": 30, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        },
        "step": {"num": 5, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        "default": {"num": 10, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
        "ui": "ui-editable",
    }


def _categorical_param(
    name: str = "mode", *, options: tuple[str, ...] = ("fast", "slow"), default: str = "fast"
) -> dict[str, object]:
    return {
        "name": name,
        "type": "categorical",
        "options": list(options),
        "default": default,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _boolean_param(name: str = "use_atr", *, default: bool = True) -> dict[str, object]:
    return {
        "name": name,
        "type": "boolean",
        "default": default,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _money_int_param(
    name: str = "stop", *, low: int = 10, high: int = 100, step: int = 5
) -> dict[str, object]:
    """A money parameter as exact-integer minor units (OPT-4)."""
    return {
        "name": name,
        "type": "exact integer",
        "bounds": {"min": low, "max": high},
        "step": step,
        "default": low,
        "unit_kind": UnitKind.MONEY,
        "ui": "ui-editable",
    }


def _valid_space() -> list[dict[str, object]]:
    return [
        _int_param(),
        _rational_param(),
        _categorical_param(),
        _boolean_param(),
        _money_int_param(),
    ]


# --- AC-1: a valid typed space is accepted and canonically ordered -------------


def test_valid_typed_space_accepted() -> None:
    space = _ok(coerce_study_space(_valid_space()))
    assert isinstance(space, StudyParameterSpace)
    # Canonical name order (the one CT-33 schema sorts by name).
    assert space.parameter_names == ("atr_mult", "lookback", "mode", "stop", "use_atr")
    assert len(space.parameters) == 5
    # Idempotent: coercing an already-built space returns it unchanged.
    assert _ok(coerce_study_space(space)) is space
    # A pre-coerced ParameterSpec tuple is admitted too.
    again = _ok(StudyParameterSpace.try_create(space.parameters))
    assert again.parameters == space.parameters


def test_study_space_identity_excludes_semver() -> None:
    ident = study_space_identity()
    assert ident["class"] == STUDY_SPACE_CLASS
    assert ident["format_version"] == STUDY_SPACE_FORMAT_VERSION
    assert ident["run_config_key"] == STUDY_SPACE_KEY
    assert qmb.__version__ not in str(ident)


# --- AC-5: the space is identity content; equal spaces share one fingerprint ---


def test_equal_spaces_share_fingerprint_regardless_of_declaration_order() -> None:
    space_a = _ok(coerce_study_space(_valid_space()))
    reordered = list(reversed(_valid_space()))
    space_b = _ok(coerce_study_space(reordered))
    fp_a = _ok(space_a.fingerprint())
    fp_b = _ok(space_b.fingerprint())
    assert fp_a.value.startswith("fp1:sha256:")
    assert fp_a == fp_b  # two Studies declaring the same space share the space fp1


def test_different_space_yields_different_fingerprint() -> None:
    base = _ok(coerce_study_space(_valid_space()))
    widened = _ok(coerce_study_space([*_valid_space()[:-1], _money_int_param(high=200)]))
    assert _ok(base.fingerprint()) != _ok(widened.fingerprint())


def test_space_identity_is_float_free_and_fp1_clean() -> None:
    space = _ok(coerce_study_space(_valid_space()))
    identity = space.fp1_identity()
    assert identity["class"] == STUDY_SPACE_CLASS
    assert identity["parameter_order"] == list(space.parameter_names)
    # The whole content re-fingerprints clean — no binary float survives anywhere.
    assert _ok(fingerprint(identity)).value.startswith("fp1:sha256:")
    assert "e-" not in str(identity)  # no float scientific notation leaked in


# --- AC-1: the space is materialized as identity content of the run-config -----


def test_space_materialized_into_resolved_run_config_identity() -> None:
    port, book_fragment, bms_fragment = _compiler_inputs()
    space = _ok(coerce_study_space(_valid_space()))
    layer = space.run_config_layer()
    assert layer == {STUDY_SPACE_KEY: space.fp1_identity()}

    compiled = _ok(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": "mean-reversion", **layer, "starting_capital": _SEED},
            workspace_defaults=_DEFAULTS,
        )
    )
    # The space rides in the resolved keys and therefore in the run-config fp1.
    resolved_space = cast("Mapping[str, object]", compiled.keys[STUDY_SPACE_KEY])
    assert resolved_space["class"] == STUDY_SPACE_CLASS
    identity_keys = cast("Mapping[str, object]", compiled.fp1_identity()["keys"])
    identity_space = cast("Mapping[str, object]", identity_keys[STUDY_SPACE_KEY])
    assert identity_space["parameter_order"] == list(space.parameter_names)

    # Same space -> same run-config fingerprint; a different space -> different.
    twin = _ok(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": "mean-reversion", **layer, "starting_capital": _SEED},
            workspace_defaults=_DEFAULTS,
        )
    )
    assert twin.fingerprint == compiled.fingerprint
    other = _ok(coerce_study_space([*_valid_space()[:-1], _money_int_param(high=200)]))
    changed = _ok(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={
                "bot": "mean-reversion",
                **other.run_config_layer(),
                "starting_capital": _SEED,
            },
            workspace_defaults=_DEFAULTS,
        )
    )
    assert changed.fingerprint != compiled.fingerprint


# --- AC-2: numeric bound / step rules are typed invalid-input refusals ----------


def test_step_wider_than_span_is_refused_naming_the_parameter() -> None:
    refused = _refused(coerce_study_space([_int_param("lookback", low=10, high=20, step=50)]))
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["parameter"] == "lookback"
    assert "step" in cast("str", refused.context["reason"])


def test_rational_step_wider_than_span_is_refused() -> None:
    wide: dict[str, object] = {
        "name": "atr_mult",
        "type": "exact rational",
        "bounds": {
            "min": {"num": 10, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
            "max": {"num": 20, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        },
        "step": {"num": 50, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        "default": {"num": 10, "den": 10, "unit_kind": UnitKind.DIMENSIONLESS_RATIO},
        "unit_kind": UnitKind.DIMENSIONLESS_RATIO,
        "ui": "ui-editable",
    }
    refused = _refused(coerce_study_space([wide]))
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["parameter"] == "atr_mult"


def test_min_exceeds_max_and_nonpositive_step_are_refused() -> None:
    bad_bounds = _refused(coerce_study_space([_int_param("lb", low=50, high=10, step=1)]))
    assert bad_bounds.category is RefusalCategory.INVALID_INPUT
    zero_step = _refused(coerce_study_space([_int_param("lb", low=1, high=10, step=0)]))
    assert zero_step.category is RefusalCategory.INVALID_INPUT
    assert zero_step.context["field"] == "step"


# --- AC-3: categorical option rules --------------------------------------------


def test_categorical_empty_options_is_refused() -> None:
    refused = _refused(coerce_study_space([_categorical_param(options=(), default="x")]))
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_categorical_default_not_in_options_is_refused() -> None:
    refused = _refused(
        coerce_study_space([_categorical_param(options=("fast", "slow"), default="medium")])
    )
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "default"


# --- AC-4: money is exact-integer minor units; a binary float is banned ----------


def test_money_parameter_is_exact_integer_minor_units() -> None:
    space = _ok(coerce_study_space([_money_int_param()]))
    stop = space.parameters[0]
    assert stop.unit_kind is UnitKind.MONEY
    low, high = stop.bounds  # type: ignore[misc]
    assert isinstance(low, int) and not isinstance(low, bool)
    assert isinstance(high, int) and isinstance(stop.step, int)


def test_money_declared_as_rational_is_refused() -> None:
    money_rational: dict[str, object] = {
        "name": "stop_r",
        "type": "exact rational",
        "bounds": {
            "min": {"num": 5, "den": 1, "unit_kind": UnitKind.MONEY},
            "max": {"num": 50, "den": 1, "unit_kind": UnitKind.MONEY},
        },
        "step": {"num": 5, "den": 1, "unit_kind": UnitKind.MONEY},
        "default": {"num": 10, "den": 1, "unit_kind": UnitKind.MONEY},
        "unit_kind": UnitKind.MONEY,
        "ui": "ui-editable",
    }
    refused = _refused(coerce_study_space([money_rational]))
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["parameter"] == "stop_r"
    assert refused.context["declared_type"] == "exact rational"


def test_binary_float_anywhere_in_the_space_is_refused() -> None:
    float_default: dict[str, object] = {
        "name": "stop",
        "type": "exact integer",
        "bounds": {"min": 10, "max": 100},
        "step": 5,
        "default": 12.5,
        "unit_kind": UnitKind.MONEY,
        "ui": "ui-editable",
    }
    refused = _refused(coerce_study_space([float_default]))
    assert refused.category is RefusalCategory.INVALID_INPUT


# --- B-8: the schema is read from the one CT-33-authoritative source ------------


def test_reads_space_from_a_ct33_bot_definition() -> None:
    bot = _bot_with_space()
    from_bot = _ok(study_space_from_bot(bot))
    assert from_bot.parameter_names == ("lookback",)
    # coerce_study_space accepts the BotDefinition object too, same result.
    via_coerce = _ok(coerce_study_space(bot))
    assert _ok(via_coerce.fingerprint()) == _ok(from_bot.fingerprint())


def test_thin_study_config_mapping_carries_the_parameter_space() -> None:
    config: dict[str, object] = {"parameter_space": _valid_space()}
    space = _ok(coerce_study_space(config))
    assert space.parameter_names == ("atr_mult", "lookback", "mode", "stop", "use_atr")
    no_space = _refused(coerce_study_space({"not": "a-space"}))
    assert no_space.category is RefusalCategory.INVALID_INPUT
    assert no_space.context["field"] == "declaration"


def test_study_space_from_bot_refuses_a_non_bot() -> None:
    refused = _refused(study_space_from_bot({"not": "a-bot"}))
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_empty_search_space_is_refused() -> None:
    refused = _refused(coerce_study_space([]))
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "parameter_space"


# --- door parity ---------------------------------------------------------------


def test_door_reexports_the_study_space_surface() -> None:
    assert api.coerce_study_space is qmb.coerce_study_space
    assert api.study_space_from_bot is qmb.study_space_from_bot
    assert api.study_space_identity is qmb.study_space_identity
    assert api.StudyParameterSpace is qmb.StudyParameterSpace
    for name in (
        "StudyParameterSpace",
        "coerce_study_space",
        "study_space_from_bot",
        "study_space_identity",
        "STUDY_SPACE_KEY",
    ):
        assert name in qmb.__all__
        assert name in api.__all__


# --- scaffolding ---------------------------------------------------------------


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(stream: str) -> WriterId:
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


def _definition_record(kind: str, definition: BookDefinition | BmsDefinition) -> RegistrationRecord:
    stamped = _ok(definition.fingerprint())
    return _ok(
        RegistrationRecord.try_create(
            kind,
            definition.contract_format_version,
            (stamped,),
            definition.fp1_identity(),
            _writer(kind),
            0,
            _instant(),
        )
    )


def _bot_record() -> RegistrationRecord:
    return _ok(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            [],
            {"class": "bot-definition", "alias": "mean-reversion"},
            _writer("bot-definition"),
            0,
            _instant(),
        )
    )


def _compiler_inputs() -> tuple[RegistryReadPort, object, object]:
    book_record = _definition_record("book-definition", _book())
    bms_record = _definition_record("bms-definition", _bms())
    bot = _bot_record()
    as_of = _ok(
        AsOfSet.try_create(
            _instant(),
            records=(book_record, bms_record, bot),
            pointers=(
                _ok(DatedPointer.try_create("scalping", book_record.stable_id, _instant())),
                _ok(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant())),
            ),
        )
    )
    port = _ok(
        RegistryReadPort.try_create(
            _ok(PassiveHub.try_create((as_of,))),
            stale_evidence_severity=_SEVERITY,
        )
    )
    book_fragment = _ok(materialize_book_fragment(port, "scalping", _writer("config-fragment")))
    bms_fragment = _ok(
        materialize_bms_fragment(port, bms_record.stable_id, _writer("config-fragment"))
    )
    return port, book_fragment, bms_fragment


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "example-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _bot_with_space() -> BotDefinition:
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
    logic = _ok(
        mint_logic_identity(
            "research-bot",
            "1.0.0",
            {
                "research_bot/__init__.py": "",
                "research_bot/bot.py": "def on_instant(self, instant):\n    return ()\n",
            },
        )
    )
    payload: dict[str, object] = {
        "strategy_family_id": "trend-follow",
        "confluence_set": [confluence],
        "parameter_space": [_int_param()],
        "footprint": footprint,
        "permitted_exit_intents": (),
        "logic_reference": logic,
    }
    return _ok(mint_bot_definition(payload))
