"""Story 13.4 — one resolved run-config compiled from fixed-precedence layers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from typing import TypeVar

from qmb.config import (
    BMS_NAMESPACES,
    BOOK_NAMESPACES,
    CLOCK_REPLAY,
    CLOCK_SIMULATED,
    CONFIG_FRAGMENT_CLASS,
    DISPLAY_FIELDS,
    FRAGMENT_FORMAT_VERSION,
    IDENTITY_FIELDS,
    LAYER_PRECEDENCE,
    OPTIONAL_IDENTITY_FIELDS,
    PROVENANCE_PROCEDURE_EPHEMERAL,
    PROVENANCE_RECORDED,
    PROVENANCE_SYNTHETIC_TAINTED,
    RUN_CONFIG_ARTIFACT_NAME,
    RUN_CONFIG_CLASS,
    RUN_CONFIG_FORMAT_VERSION,
    RUN_CONFIG_FORMAT_VERSION_1,
    RUN_CONFIG_KNOWN_FORMAT_VERSIONS,
    SANCTIONED_OVERLAP_KEYS,
    SOURCE_BOOK,
    ConfigFragment,
    ResolvedRunConfig,
    artifact_relative_path,
    compile_run_config,
    ledger_key,
    materialize_bms_fragment,
    materialize_book_fragment,
    materialize_condition_preset,
    merge_book_bms_keys,
    run_config_identity,
    run_id_root,
)
from qmb.doors import api
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import World, canonical_bytes, fingerprint
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

_CREATED_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"


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


def _binding_record() -> RegistrationRecord:
    return _record("book-binding", {"class": "book-binding", "world": "replay"})


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
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "fill": "default-fill",
    }


def _compile(
    *,
    run_spec: Mapping[str, object] | None = None,
    invocation_flags: Mapping[str, object] | None = None,
    workspace_defaults: Mapping[str, object] | None = None,
    condition_presets: tuple[ConfigFragment, ...] = (),
    book_fragment: ConfigFragment | None = None,
    bms_fragment: ConfigFragment | None = None,
    port: RegistryReadPort | None = None,
    bot: RegistrationRecord | None = None,
) -> Result[ResolvedRunConfig]:
    materialized_book, materialized_bms, materialized_port, materialized_bot = _fragments()
    spec: dict[str, object] = {"bot": (bot or materialized_bot).stable_id}
    if run_spec is not None:
        spec.update(run_spec)
        if "bot" not in run_spec:
            spec["bot"] = (bot or materialized_bot).stable_id
    return compile_run_config(
        port or materialized_port,
        book_fragment=book_fragment or materialized_book,
        bms_fragment=bms_fragment or materialized_bms,
        run_spec=spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults if workspace_defaults is not None else _defaults(),
        condition_presets=condition_presets,
    )


def _unchecked_fragment(
    source_kind: str,
    source_fp1: object,
    keys: Mapping[str, object],
    *,
    preset_name: str | None = None,
) -> ConfigFragment:
    from qmf.core.fingerprint import Fingerprint as Fp

    source = source_fp1 if isinstance(source_fp1, Fp) else _ok(Fp.try_create(source_fp1))
    identity: dict[str, object] = {
        "class": CONFIG_FRAGMENT_CLASS,
        "format_version": FRAGMENT_FORMAT_VERSION,
        "keys": dict(keys),
        "source_fp1": source.value,
        "source_kind": source_kind,
    }
    if preset_name is not None:
        identity["preset_name"] = preset_name
    return ConfigFragment(
        format_version=FRAGMENT_FORMAT_VERSION,
        source_kind=source_kind,
        source_fp1=source,
        keys=keys,
        fingerprint=_ok(fingerprint(identity)),
        lineage=None,
        preset_name=preset_name,
    )


def test_compile_produces_one_read_only_fingerprinted_artifact() -> None:
    book, bms, port, bot = _fragments()
    compiled = _ok(
        compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": "mean-reversion", "parameter": 3},
            workspace_defaults=_defaults(),
        )
    )
    assert compiled.format_version == RUN_CONFIG_FORMAT_VERSION == RUN_CONFIG_FORMAT_VERSION_1
    assert compiled.clock == CLOCK_REPLAY
    assert compiled.data_provenance == PROVENANCE_RECORDED
    assert compiled.world is World.REPLAY
    assert compiled.book_fp1 == book.source_fp1
    assert compiled.bms_fp1 == bms.source_fp1
    assert compiled.bot_fp1 == bot.stable_id
    assert compiled.book_fragment_fp1 == book.fingerprint
    assert compiled.bms_fragment_fp1 == bms.fingerprint
    assert compiled.binding_fp1 is None
    assert compiled.keys["parameter"] == 3
    assert compiled.keys["fill"] == "default-fill"
    assert "bot" not in compiled.keys
    assert "clock" not in compiled.keys
    assert "world" not in compiled.keys
    identity = compiled.fp1_identity()
    assert identity["class"] == RUN_CONFIG_CLASS
    assert identity["identity_fields"] == list(IDENTITY_FIELDS) + list(OPTIONAL_IDENTITY_FIELDS)
    assert identity["display_fields"] == list(DISPLAY_FIELDS)
    assert identity["layer_precedence"] == list(LAYER_PRECEDENCE)
    assert "package_version" not in identity
    assert qmb.__version__ not in str(identity)
    assert compiled.display["bot_alias"] == "mean-reversion"
    assert _ok(fingerprint(identity)) == compiled.fingerprint
    assert compiled.fingerprint.value.startswith("fp1:sha256:")


def test_same_inputs_yield_byte_identical_artifact() -> None:
    first = _ok(_compile(run_spec={"bot": "mean-reversion", "horizon": 5}))
    second = _ok(_compile(run_spec={"bot": "mean-reversion", "horizon": 5}))
    assert first.fingerprint == second.fingerprint
    assert _ok(first.artifact_bytes()) == _ok(second.artifact_bytes())
    assert _ok(canonical_bytes(first.fp1_identity())) == _ok(first.artifact_bytes())


def test_alias_and_fp1_bot_cites_fingerprint_identically() -> None:
    book, bms, port, bot = _fragments()
    from_alias = _ok(
        compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": "mean-reversion"},
            workspace_defaults=_defaults(),
        )
    )
    from_fp1 = _ok(
        compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": bot.stable_id},
            workspace_defaults=_defaults(),
        )
    )
    assert from_alias.fingerprint == from_fp1.fingerprint
    assert from_alias.bot_fp1 == from_fp1.bot_fp1 == bot.stable_id
    assert "bot_alias" in from_alias.display
    assert "bot_alias" not in from_fp1.display


def test_fixed_precedence_higher_layer_wins() -> None:
    compiled = _ok(
        _compile(
            run_spec={"fill": "bot-fill", "sizing_note": "spec"},
            invocation_flags={"fill": "flag-fill"},
            workspace_defaults={**_defaults(), "fill": "default-fill", "sizing_note": "default"},
        )
    )
    assert compiled.keys["fill"] == "flag-fill"
    assert compiled.keys["sizing_note"] == "spec"
    assert "admission" in compiled.keys
    assert "accounting" in compiled.keys
    assert set(compiled.keys) >= {"admission", "sizing", "exit-door"}
    assert set(compiled.keys) >= {"accounting", "constraints", "kill-line", "reporting"}


def test_book_and_bms_collision_is_compile_time_refusal() -> None:
    book, bms, port, bot = _fragments()
    colliding_book = _unchecked_fragment(
        SOURCE_BOOK,
        book.source_fp1,
        {**dict(book.keys), "accounting": {"stolen": 1}},
    )
    refused = compile_run_config(
        port,
        book_fragment=colliding_book,
        bms_fragment=bms,
        run_spec={"bot": bot.stable_id},
        workspace_defaults=_defaults(),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "keys"
    assert refused.context["colliding"] == ("accounting",)


def test_sanctioned_overlap_bms_outranks_book() -> None:
    assert frozenset() == SANCTIONED_OVERLAP_KEYS
    merged = _ok(
        merge_book_bms_keys(
            {"admission": {"x": 1}, "reporting": {"from": "book"}},
            {"reporting": {"from": "bms"}, "accounting": {"y": 1}},
            sanctioned_overlap={"reporting"},
        )
    )
    assert merged["reporting"] == {"from": "bms"}
    assert merged["admission"] == {"x": 1}
    assert merged["accounting"] == {"y": 1}
    refused = merge_book_bms_keys(
        {"reporting": {"from": "book"}},
        {"reporting": {"from": "bms"}},
    )
    assert is_refusal(refused)


def test_name_at_version_cite_is_invalid_input() -> None:
    refused = _compile(run_spec={"bot": "mean-reversion@1"})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "bot"
    binding_refused = _compile(run_spec={"bot": "mean-reversion", "binding": "live@2"})
    assert is_refusal(binding_refused)
    assert binding_refused.context["field"] == "binding"


def test_cites_are_fp1_never_name_at_version() -> None:
    compiled = _ok(_compile(run_spec={"bot": "mean-reversion"}))
    identity = compiled.fp1_identity()
    for field in ("book_fp1", "bms_fp1", "bot_fp1", "book_fragment_fp1", "bms_fragment_fp1"):
        value = identity[field]
        assert isinstance(value, str)
        assert value.startswith("fp1:sha256:")
        assert "@" not in value
    assert compiled.book_fp1.value.startswith("fp1:sha256:")


def test_fingerprint_is_run_id_root_and_ledger_key() -> None:
    compiled = _ok(_compile())
    assert run_id_root(compiled) == compiled.fingerprint == compiled.run_id
    assert ledger_key(compiled) == compiled.fingerprint
    assert api.run_id_root is qmb.run_id_root
    assert api.ledger_key is qmb.ledger_key
    path = compiled.artifact_relative_path()
    assert path == artifact_relative_path(compiled.fingerprint)
    assert path.endswith("/" + RUN_CONFIG_ARTIFACT_NAME)
    directory, _, name = path.rpartition("/")
    assert name == RUN_CONFIG_ARTIFACT_NAME
    assert ":" not in directory
    assert directory.startswith("fp1-sha256-")
    assert compiled.fingerprint.value.replace(":", "-") == directory


def test_replay_clock_plus_synthetic_tainted_data_is_invalid_input() -> None:
    refused = _compile(
        workspace_defaults={
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_SYNTHETIC_TAINTED,
        }
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "clock"
    mismatch = _compile(
        workspace_defaults={
            "clock": CLOCK_SIMULATED,
            "data_provenance": PROVENANCE_RECORDED,
        }
    )
    assert is_refusal(mismatch)
    assert mismatch.category is RefusalCategory.INVALID_INPUT


def test_provenance_derived_world_and_caller_declared_world_refused() -> None:
    replay = _ok(
        _compile(
            workspace_defaults={
                "clock": CLOCK_REPLAY,
                "data_provenance": PROVENANCE_PROCEDURE_EPHEMERAL,
            }
        )
    )
    assert replay.world is World.REPLAY
    simulated = _ok(
        _compile(
            workspace_defaults={
                "clock": CLOCK_SIMULATED,
                "data_provenance": PROVENANCE_SYNTHETIC_TAINTED,
            }
        )
    )
    assert simulated.world is World.SIMULATED
    declared = _compile(run_spec={"world": "replay"})
    assert is_refusal(declared)
    assert declared.category is RefusalCategory.INVALID_INPUT
    assert declared.context["field"] == "world"


def test_binding_cite_resolves_to_fp1() -> None:
    book_def = _book()
    bms_def = _bms()
    book_record = _record("book-definition", book_def)
    bms_record = _record("bms-definition", bms_def)
    bot = _bot_record()
    binding = _binding_record()
    port = _port(
        (book_record, bms_record, bot, binding),
        pointers=(
            _ok(DatedPointer.try_create("mean-reversion", bot.stable_id, _instant())),
            _ok(DatedPointer.try_create("replay-bind", binding.stable_id, _instant())),
            _ok(DatedPointer.try_create("scalping", book_record.stable_id, _instant())),
        ),
    )
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    compiled = _ok(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": "mean-reversion", "binding": "replay-bind"},
            workspace_defaults=_defaults(),
        )
    )
    assert compiled.binding_fp1 == binding.stable_id
    assert compiled.fp1_identity()["binding_fp1"] == binding.stable_id.value
    assert compiled.display["binding_alias"] == "replay-bind"


def test_condition_preset_merges_after_fragments_before_run_spec() -> None:
    book, bms, port, bot = _fragments()
    preset = _ok(
        materialize_condition_preset(
            port,
            "scalping",
            _writer(),
            name="stress-spread",
            keys={"spread-schedule": {"name": "stress-spread", "widening_bps": 20}},
        )
    )
    compiled = _ok(
        compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": bot.stable_id, "spread-schedule": {"name": "override"}},
            workspace_defaults=_defaults(),
            condition_presets=(preset,),
        )
    )
    assert compiled.keys["spread-schedule"] == {"name": "override"}
    assert compiled.condition_preset_fp1 == (preset.fingerprint,)
    assert compiled.fp1_identity()["condition_preset_fp1"] == [preset.fingerprint.value]


def test_old_run_configs_stay_readable_forever() -> None:
    compiled = _ok(_compile())
    later = _ok(ResolvedRunConfig.try_read(compiled.fp1_identity(), reader_format_version=2))
    assert later.fingerprint == compiled.fingerprint
    assert RUN_CONFIG_FORMAT_VERSION_1 in RUN_CONFIG_KNOWN_FORMAT_VERSIONS
    tampered = dict(compiled.fp1_identity())
    tampered["format_version"] = 2
    refused = ResolvedRunConfig.try_read(tampered, reader_format_version=1)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    unknown = ResolvedRunConfig.try_read(tampered, reader_format_version=2)
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_try_read_validates_schema_and_ignores_display() -> None:
    compiled = _ok(_compile(run_spec={"bot": "mean-reversion"}))
    assert is_refusal(ResolvedRunConfig.try_read("body"))
    assert is_refusal(ResolvedRunConfig.try_read({"class": "other"}))
    identity = compiled.fp1_identity()
    identity["book_alias"] = "scalping"
    identity["package_version"] = qmb.__version__
    reread = _ok(ResolvedRunConfig.try_read(identity))
    assert reread.fingerprint == compiled.fingerprint
    assert reread.display["book_alias"] == "scalping"
    assert "package_version" not in reread.fp1_identity()
    extra = compiled.fp1_identity()
    extra["unknown"] = 1
    assert is_refusal(ResolvedRunConfig.try_read(extra))
    keys = compiled.fp1_identity()
    keys["keys"] = {"bot": "left-over"}
    assert is_refusal(ResolvedRunConfig.try_read(keys))


def test_missing_bot_or_clock_is_invalid() -> None:
    book, bms, port, _bot = _fragments()
    missing_bot = compile_run_config(
        port,
        book_fragment=book,
        bms_fragment=bms,
        run_spec={},
        workspace_defaults=_defaults(),
    )
    assert is_refusal(missing_bot)
    assert missing_bot.context["field"] == "bot"
    missing_clock = compile_run_config(
        port,
        book_fragment=book,
        bms_fragment=bms,
        run_spec={"bot": "mean-reversion"},
        workspace_defaults={"data_provenance": PROVENANCE_RECORDED},
    )
    assert is_refusal(missing_clock)
    assert missing_clock.context["field"] == "clock"


def test_compile_passthrough_port_refusals_and_bad_args() -> None:
    book, bms, port, _bot = _fragments()
    missing = compile_run_config(
        port,
        book_fragment=book,
        bms_fragment=bms,
        run_spec={"bot": "unknown-bot"},
        workspace_defaults=_defaults(),
    )
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert is_refusal(
        compile_run_config(
            "port",
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": "mean-reversion"},
        )
    )
    assert is_refusal(
        compile_run_config(
            port,
            book_fragment=bms,
            bms_fragment=bms,
            run_spec={"bot": "mean-reversion"},
            workspace_defaults=_defaults(),
        )
    )
    assert is_refusal(
        compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec="spec",
            workspace_defaults=_defaults(),
        )
    )
    assert is_refusal(
        compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": "mean-reversion"},
            condition_presets=book,
            workspace_defaults=_defaults(),
        )
    )
    floated = _compile(run_spec={"spread": 1.5})
    assert is_refusal(floated)
    assert floated.category is RefusalCategory.INVALID_INPUT


def test_artifact_is_immutable_and_api_matches() -> None:
    compiled = _ok(_compile())
    try:
        compiled.keys = {}  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("resolved run-config mutated")
    assert api.ResolvedRunConfig is qmb.ResolvedRunConfig is ResolvedRunConfig
    assert api.compile_run_config is qmb.compile_run_config is compile_run_config
    assert api.merge_book_bms_keys is qmb.merge_book_bms_keys
    assert api.LAYER_PRECEDENCE == qmb.LAYER_PRECEDENCE == LAYER_PRECEDENCE
    assert api.SANCTIONED_OVERLAP_KEYS == SANCTIONED_OVERLAP_KEYS
    schema = run_config_identity()
    assert "version" not in schema
    assert qmb.__version__ not in schema.values()
    assert schema["class"] == RUN_CONFIG_CLASS
    assert BOOK_NAMESPACES.isdisjoint(BMS_NAMESPACES)


def test_doors_compute_the_same_fingerprint() -> None:
    book, bms, port, bot = _fragments()
    kwargs = {
        "book_fragment": book,
        "bms_fragment": bms,
        "run_spec": {"bot": bot.stable_id, "horizon": 8},
        "workspace_defaults": _defaults(),
    }
    library = _ok(qmb.compile_run_config(port, **kwargs))
    door = _ok(api.compile_run_config(port, **kwargs))
    assert library.fingerprint == door.fingerprint
    assert run_id_root(library) == run_id_root(door)
    assert ledger_key(library) == ledger_key(door)
