"""Story 58.1 — default Book path still compiles; dummy Book is INVALID_INPUT."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.analysis import register_book_bms_variant
from qmb.config import (
    CLOCK_REPLAY,
    CONFIG_FRAGMENT_CLASS,
    FRAGMENT_FORMAT_VERSION,
    IDENTITY_FIELDS,
    OPTIONAL_IDENTITY_FIELDS,
    PROVENANCE_RECORDED,
    SOURCE_BOOK,
    STARTING_CAPITAL_KEY,
    ConfigFragment,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.config.dummy import refuse_sensing_as_atc
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(stream: str = "config-fragment", machine: str = "node-a") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", stream, "boot-1"))


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


def _bot_record() -> RegistrationRecord:
    return _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})


def _port(
    records: tuple[RegistrationRecord, ...],
    *,
    pointers: tuple[DatedPointer, ...] = (),
) -> RegistryReadPort:
    as_of = _ok(AsOfSet.try_create(_instant(), records=records, pointers=pointers))
    hub = _ok(PassiveHub.try_create((as_of,)))
    return _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))


def _fragments() -> tuple[ConfigFragment, ConfigFragment, RegistryReadPort, RegistrationRecord]:
    book = _book()
    bms = _bms()
    book_record = _record("book-definition", book)
    bms_record = _record("bms-definition", bms)
    bot = _bot_record()
    pointer = _ok(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()))
    book_pointer = _ok(DatedPointer.try_create("scalping", book_record.stable_id, _instant()))
    port = _port(
        (book_record, bms_record, bot),
        pointers=(pointer, book_pointer),
    )
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    return book_fragment, bms_fragment, port, bot


def _defaults() -> dict[str, object]:
    return {
        "account_id": "acct-replay",
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "fill": "default-fill",
        "venue_id": "venue-replay",
    }


def _compile(
    *,
    run_spec: Mapping[str, object] | None = None,
    book_fragment: ConfigFragment | None = None,
    bms_fragment: ConfigFragment | None = None,
    port: RegistryReadPort | None = None,
    bot: RegistrationRecord | None = None,
    workspace_defaults: Mapping[str, object] | None = None,
) -> Result[ResolvedRunConfig]:
    materialized_book, materialized_bms, materialized_port, materialized_bot = _fragments()
    spec: dict[str, object] = {
        "bot": (bot or materialized_bot).stable_id,
        STARTING_CAPITAL_KEY: _SEED,
    }
    if run_spec is not None:
        spec.update(run_spec)
        if "bot" not in run_spec:
            spec["bot"] = (bot or materialized_bot).stable_id
        if STARTING_CAPITAL_KEY not in run_spec:
            spec[STARTING_CAPITAL_KEY] = _SEED
    return compile_run_config(
        port or materialized_port,
        book_fragment=book_fragment or materialized_book,
        bms_fragment=bms_fragment or materialized_bms,
        run_spec=spec,
        workspace_defaults=workspace_defaults if workspace_defaults is not None else _defaults(),
    )


def _unchecked_fragment(
    source_kind: str,
    source_fp1: object,
    keys: Mapping[str, object],
) -> ConfigFragment:
    if isinstance(source_fp1, Fingerprint):
        source = source_fp1
    else:
        source = _ok(Fingerprint.try_create(source_fp1))
    identity: dict[str, object] = {
        "class": CONFIG_FRAGMENT_CLASS,
        "format_version": FRAGMENT_FORMAT_VERSION,
        "keys": dict(keys),
        "source_fp1": source.value,
        "source_kind": source_kind,
    }
    return ConfigFragment(
        format_version=FRAGMENT_FORMAT_VERSION,
        source_kind=source_kind,
        source_fp1=source,
        keys=keys,
        fingerprint=_ok(fingerprint(identity)),
        lineage=None,
        preset_name=None,
    )


def _assert_invalid(result: Result[T], *, field: str | None = None) -> None:
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    if field is not None:
        assert result.context["field"] == field


def test_resolved_run_config_still_requires_book_bms_bot_and_fragments() -> None:
    required = set(IDENTITY_FIELDS)
    optional = set(OPTIONAL_IDENTITY_FIELDS)
    for field in ("book_fp1", "bms_fp1", "bot_fp1", "book_fragment_fp1", "bms_fragment_fp1"):
        assert field in required
        assert field not in optional
    compiled = _ok(_compile())
    identity = compiled.fp1_identity()
    for field in ("book_fp1", "bms_fp1", "bot_fp1", "book_fragment_fp1", "bms_fragment_fp1"):
        missing = dict(identity)
        del missing[field]
        _assert_invalid(ResolvedRunConfig.try_read(missing), field=field)


def test_compile_without_book_or_bms_fragment_is_invalid_input() -> None:
    book, bms, port, bot = _fragments()
    missing_book = compile_run_config(
        port,
        book_fragment=None,
        bms_fragment=bms,
        run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
        workspace_defaults=_defaults(),
    )
    _assert_invalid(missing_book, field="book_fragment")
    missing_bms = compile_run_config(
        port,
        book_fragment=book,
        bms_fragment=None,
        run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
        workspace_defaults=_defaults(),
    )
    _assert_invalid(missing_bms, field="bms_fragment")


def test_empty_object_book_fragment_is_invalid_input() -> None:
    book, bms, port, bot = _fragments()
    dummy = _unchecked_fragment(SOURCE_BOOK, book.source_fp1, {})
    refused = compile_run_config(
        port,
        book_fragment=dummy,
        bms_fragment=bms,
        run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
        workspace_defaults=_defaults(),
    )
    _assert_invalid(refused, field="book_fragment")
    currency_only = _unchecked_fragment(
        SOURCE_BOOK,
        book.source_fp1,
        {"sizing": {"accounting_currency": "USD"}},
    )
    refused_currency = compile_run_config(
        port,
        book_fragment=currency_only,
        bms_fragment=bms,
        run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
        workspace_defaults=_defaults(),
    )
    _assert_invalid(refused_currency, field="book_fragment")


def test_dummy_policy_and_sentinel_cites_are_invalid_input() -> None:
    book, bms, port, bot = _fragments()
    for policy in ("identity", "no-op", "unlimited", "pass-through"):
        sizing_map: dict[str, object] = {}
        raw_sizing = book.keys.get("sizing")
        if isinstance(raw_sizing, Mapping):
            nested = cast("Mapping[object, object]", raw_sizing)
            sizing_map = {str(key): item for key, item in nested.items()}
        sizing_map["policy"] = policy
        dummy = _unchecked_fragment(
            SOURCE_BOOK,
            book.source_fp1,
            {**dict(book.keys), "sizing": sizing_map},
        )
        refused = compile_run_config(
            port,
            book_fragment=dummy,
            bms_fragment=bms,
            run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults=_defaults(),
        )
        _assert_invalid(refused, field="policy")
    _assert_invalid(_compile(run_spec={"bot": "NULL_BOT"}), field="bot")
    identity = _ok(_compile()).fp1_identity()
    identity["book_fp1"] = "NULL_BOOK"
    _assert_invalid(ResolvedRunConfig.try_read(identity), field="book_fp1")
    identity = _ok(_compile()).fp1_identity()
    identity["bms_fp1"] = "NULL_BMS"
    _assert_invalid(ResolvedRunConfig.try_read(identity), field="bms_fp1")


def test_fake_mis_ref_null_and_policy_pair_on_resolved_run_config_are_invalid() -> None:
    _assert_invalid(_compile(run_spec={"mis_ref": None}), field="mis_ref")
    _assert_invalid(
        _compile(run_spec={"policy_pair": {"accounting": "identity", "risk": "no-op"}}),
        field="policy_pair",
    )
    _assert_invalid(
        _compile(run_spec={"composition_class": "alternative"}),
        field="composition_class",
    )


def test_dummy_book_register_is_invalid_input() -> None:
    empty = _ok(BookDefinition.try_create(BOOK_CONTRACT_FORMAT_VERSION, "USD", {}))
    refused = register_book_bms_variant(
        definition=empty,
        writer=_writer(),
        created_at=_instant(),
    )
    _assert_invalid(refused, field="book")
    complete = _ok(
        register_book_bms_variant(
            definition=_book(),
            writer=_writer(),
            created_at=_instant(),
        )
    )
    assert complete.kind == "book-definition"


def test_sensing_labeled_atc_or_seat_is_refused() -> None:
    _assert_invalid(
        refuse_sensing_as_atc({"class": "ungoverned-work-config", "label": "atc"}),
        field="label",
    )
    _assert_invalid(
        refuse_sensing_as_atc({"sensing": True, "role": "seat"}),
        field="label",
    )
    _assert_invalid(
        refuse_sensing_as_atc({"class": "research", "composition_class": "alternative"}),
        field="label",
    )
    allowed = refuse_sensing_as_atc({"class": "ungoverned-work-config"})
    assert is_ok(allowed)
    _assert_invalid(
        _compile(run_spec={"sensing": True, "label": "alternative"}),
        field="label",
    )


def test_default_book_path_still_compiles_and_validates() -> None:
    compiled = _ok(_compile())
    assert compiled.book_fp1.value.startswith("fp1:sha256:")
    assert compiled.bms_fp1.value.startswith("fp1:sha256:")
    assert compiled.bot_fp1.value.startswith("fp1:sha256:")
    reread = _ok(ResolvedRunConfig.try_read(compiled.fp1_identity()))
    assert reread.fingerprint == compiled.fingerprint
