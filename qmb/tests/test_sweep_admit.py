"""Story 20.2 — one registry as-of resolved at batch admission, frozen for every combo."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.config import (
    CLOCK_REPLAY,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
)
from qmb.doors import api
from qmb.registryread import (
    STALE_EVIDENCE_SEVERITY_KEY,
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryReadPort,
    SupersedesRef,
)
from qmb.results import REGISTRY_AS_OF_KEY as CT32_REGISTRY_AS_OF_KEY
from qmb.results import mint_run_performance_result
from qmb.sweep import (
    ADMISSION_FREEZES_AS_OF,
    ADMISSION_HAS_SECOND_CACHE,
    ADMISSION_SINGLE_AS_OF,
    REGISTRY_AS_OF_KEY,
    SWEEP_LABEL_CLASS,
    SWEEP_RUN_LABEL_CLASS,
    AdmittedSweep,
    SweepDeclaration,
    SweepLabel,
    SweepRunSpec,
    admit_sweep,
    expand_sweep,
    sweep_admission_identity,
)
from qmf.core.chrono import Instant, Interval, WriterId
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

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_TF_1M = {"kind": "time-interval", "seconds": 60}
_TF_5M = {"kind": "time-interval", "seconds": 300}
# The one class marker CT-32 reads registry_as_of under (ct32._REGISTRY_AS_OF_CLASS).
_REGISTRY_AS_OF_CLASS = "registry-as-of"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(stream: str = "config-fragment") -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", stream, "boot-1"))


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


def _book(q: int = 100) -> BookDefinition:
    return _ok(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _variable("q", q)),
            },
        )
    )


def _bms(cadence: int = 1) -> BmsDefinition:
    return _ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section("accounting_rules", _variable("numeraire_unit", 1)),
                "constraints": _section("constraints", _variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _variable("posture", 1)),
                "reporting": _section("reporting", _variable("cadence", cadence)),
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


def _port(*records: RegistrationRecord, **as_of_kwargs: object) -> RegistryReadPort:
    as_of = _ok(AsOfSet.try_create(_instant(), records=records, **as_of_kwargs))
    hub = _ok(PassiveHub.try_create((as_of,)))
    return _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))


def _bot_record() -> RegistrationRecord:
    return _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})


def _fixture_port() -> tuple[
    RegistryReadPort, RegistrationRecord, RegistrationRecord, RegistrationRecord
]:
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    bot_record = _bot_record()
    pointers = (
        _ok(DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant())),
        _ok(DatedPointer.try_create("scalping", book_record.stable_id, _instant())),
    )
    port = _port(book_record, bms_record, bot_record, pointers=pointers)
    return port, book_record, bms_record, bot_record


def _declaration(
    *,
    bot: object,
    book: object,
    bms: object,
    instruments: object = ("EURUSD", "GBPUSD"),
    timeframes: object = (_TF_1M, _TF_5M),
    parameters: object = None,
) -> SweepDeclaration:
    return _ok(
        SweepDeclaration.try_create(
            bot=bot,
            book=book,
            bms=bms,
            instruments=instruments,
            timeframes=timeframes,
            parameters=parameters,
        )
    )


def _admit(
    *,
    parameters: object = None,
    instruments: object = ("EURUSD", "GBPUSD"),
    timeframes: object = (_TF_1M, _TF_5M),
) -> AdmittedSweep:
    port, book_record, bms_record, bot_record = _fixture_port()
    decl = _declaration(
        bot=bot_record.stable_id,
        book=book_record.stable_id,
        bms=bms_record.stable_id,
        instruments=instruments,
        timeframes=timeframes,
        parameters=parameters,
    )
    return _ok(admit_sweep(decl, port, _writer()))


def _run_settings() -> dict[str, object]:
    return {
        "invocation_flags": {STARTING_CAPITAL_KEY: _SEED},
        "workspace_defaults": {
            "account_id": "acct-replay",
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_RECORDED,
            "venue_id": "venue-replay",
        },
    }


# --- AC1: one as-of resolved through the single port, frozen for the batch ----


def test_admission_resolves_one_as_of_and_freezes_it_for_the_batch() -> None:
    port, book_record, bms_record, bot_record = _fixture_port()
    as_of = port.bound
    decl = _declaration(
        bot=bot_record.stable_id,
        book=book_record.stable_id,
        bms=bms_record.stable_id,
        parameters={"lookback": [10, 20, 30]},
    )
    admitted = _ok(admit_sweep(decl, port, _writer()))
    assert isinstance(admitted, AdmittedSweep)
    # Exactly one as-of, frozen for the whole batch (B-15, SC-11).
    assert admitted.port.frozen is True
    assert admitted.registry_as_of == as_of.registry_as_of
    assert admitted.set_fingerprint == as_of.fingerprint
    assert admitted.run_count == 2 * 2 * 3 == 12
    assert len(admitted.combos) == admitted.run_count


def test_the_one_as_of_is_stamped_into_sweep_label_and_every_run_label() -> None:
    admitted = _admit(parameters={"lookback": [10, 20]})
    label = admitted.label
    assert isinstance(label, SweepLabel)
    assert label.fp1_identity()["class"] == SWEEP_LABEL_CLASS
    assert is_ok(label.fingerprint())
    stamp = admitted.registry_as_of_stamp()
    assert stamp == {
        "value_ns": admitted.registry_as_of.value_ns,
        "fingerprint": admitted.set_fingerprint.value,
    }
    # Every combination's run label carries the identical frozen as-of (spec R10).
    for combo in admitted.combos:
        run_label = _ok(admitted.run_label(combo))
        assert run_label["class"] == SWEEP_RUN_LABEL_CLASS
        assert run_label["registry_as_of"] == stamp
        assert run_label["sweep_id"] == label.sweep_id.value


def test_admission_owns_one_port_no_second_cache() -> None:
    assert ADMISSION_SINGLE_AS_OF is True
    assert ADMISSION_FREEZES_AS_OF is True
    assert ADMISSION_HAS_SECOND_CACHE is False
    identity = sweep_admission_identity()
    assert identity["admission_single_as_of"] is True
    assert identity["admission_freezes_as_of"] is True
    assert identity["admission_has_second_cache"] is False
    assert identity["sweep_label_class"] == SWEEP_LABEL_CLASS
    assert qmb.__version__ not in identity.values()
    assert is_ok(fingerprint(identity))


def test_admission_accepts_the_raw_axis_mapping() -> None:
    port, book_record, bms_record, bot_record = _fixture_port()
    admitted = _ok(
        admit_sweep(
            {
                "bot": bot_record.stable_id,
                "book": book_record.stable_id,
                "bms": bms_record.stable_id,
                "instruments": ["EURUSD"],
                "timeframes": [_TF_1M],
            },
            port,
            _writer(),
        )
    )
    assert admitted.run_count == 1


# --- AC2: fragments resolve by explicit fp1 against the one frozen as-of ------


def test_every_combo_resolves_the_identical_book_bms_bot_fp1() -> None:
    admitted = _admit(parameters={"lookback": [10, 20, 30]})
    settings = _run_settings()
    configs = _ok(admitted.compile_all(**settings))
    assert len(configs) == admitted.run_count
    book_fps = {config.book_fp1 for config in configs}
    bms_fps = {config.bms_fp1 for config in configs}
    bot_fps = {config.bot_fp1 for config in configs}
    # Two combos citing the same Book resolve the identical Book fp1 (SC-11, B-15).
    assert book_fps == {admitted.label.book_fp1}
    assert bms_fps == {admitted.label.bms_fp1}
    assert bot_fps == {admitted.label.bot_fp1}


def test_the_frozen_port_resolves_by_fp1_never_by_name_at_latest() -> None:
    admitted = _admit()
    # After admission the port refuses an alias — resolution is by explicit fp1.
    aliased = admitted.port.resolve("mean-reversion")
    assert is_refusal(aliased)
    at_latest = admitted.port.resolve("scalping@latest")
    assert is_refusal(at_latest)
    assert at_latest.category is RefusalCategory.INVALID_INPUT
    # The bot resolves by the fp1 captured at admission.
    resolved = _ok(admitted.port.resolve(admitted.label.bot_fp1))
    assert resolved.fingerprint == admitted.label.bot_fp1
    config = _ok(admitted.compile_combo(admitted.combos[0], **_run_settings()))
    assert config.bot_fp1 == admitted.label.bot_fp1


def test_a_fresher_as_of_mid_batch_never_changes_an_in_flight_combo() -> None:
    admitted = _admit(parameters={"lookback": [10, 20]})
    settings = _run_settings()
    first = _ok(admitted.compile_combo(admitted.combos[0], **settings))
    # A fresher registry state cannot reach a frozen port: recompiling the same
    # combo yields the byte-identical run id (SC-11, B-15).
    again = _ok(admitted.compile_combo(admitted.combos[0], **settings))
    assert first.fingerprint == again.fingerprint
    # Build a fresher as-of that supersedes the Book and grow the hub; a frozen
    # port bound to the admission as-of still resolves the frozen Book fp1.
    superseding = _record("book-definition", _book(q=200))
    grown = _ok(admitted.port.hub.with_set(_fresher_superseding(admitted, superseding)))
    frozen = _ok(
        RegistryReadPort.try_create(
            grown,
            stale_evidence_severity=_SEVERITY,
            bound=admitted.port.bound,
            frozen=True,
        )
    )
    # The frozen port does not consult the fresher as-of, so the Book the batch
    # bound still resolves — never a stale refusal, never the superseding version.
    book_id = _book_record_id(admitted)
    still = _ok(frozen.resolve(book_id))
    assert still.fingerprint == book_id


def _fresher_superseding(admitted: AdmittedSweep, superseding: RegistrationRecord) -> AsOfSet:
    bound = admitted.port.bound
    return _ok(
        AsOfSet.try_create(
            _instant(_NS + 1),
            records=(*bound.records, superseding),
            supersedes=(
                _ok(SupersedesRef.try_create(superseding.stable_id, _book_record_id(admitted))),
            ),
        )
    )


def _book_record_id(admitted: AdmittedSweep) -> Fingerprint:
    for record in admitted.port.bound.records:
        if record.kind == "book-definition":
            return record.stable_id
    raise AssertionError("book record missing from the admitted as-of")


# --- AC3: a superseded context reference at admission is an AD-11 stale refusal


def test_stale_context_reference_at_admission_is_an_ad11_refusal() -> None:
    book_v1 = _record("book-definition", _book(q=100))
    book_v2 = _record("book-definition", _book(q=200))
    bms_record = _record("bms-definition", _bms())
    bot_record = _bot_record()
    pointers = (
        _ok(DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant())),
        _ok(DatedPointer.try_create("scalping", book_v2.stable_id, _instant())),
    )
    supersedes = (_ok(SupersedesRef.try_create(book_v2.stable_id, book_v1.stable_id)),)
    port = _port(
        book_v1,
        book_v2,
        bms_record,
        bot_record,
        pointers=pointers,
        supersedes=supersedes,
    )
    # The sweep cites the superseded v1 Book directly.
    decl = _declaration(bot=bot_record.stable_id, book=book_v1.stable_id, bms=bms_record.stable_id)
    refused = admit_sweep(decl, port, _writer())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE
    # Severity is the configured key — no invented default (AR-55).
    assert refused.context["severity"] == _SEVERITY
    assert refused.context["severity_key"] == STALE_EVIDENCE_SEVERITY_KEY
    assert refused.context["fingerprint"] == book_v1.stable_id.value


def test_stale_bot_reference_at_admission_also_refuses() -> None:
    bot_v1 = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    bot_v2 = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion-v2"})
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    supersedes = (_ok(SupersedesRef.try_create(bot_v2.stable_id, bot_v1.stable_id)),)
    port = _port(bot_v1, bot_v2, book_record, bms_record, supersedes=supersedes)
    decl = _declaration(bot=bot_v1.stable_id, book=book_record.stable_id, bms=bms_record.stable_id)
    refused = admit_sweep(decl, port, _writer())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE


# --- AC4: the frozen as-of appears verbatim in every combo's CT-32 label ------


def test_registry_as_of_is_verbatim_in_every_combo_ct32_label_set() -> None:
    admitted = _admit(parameters={"lookback": [10, 20]})
    settings = _run_settings()
    expected_stamp = admitted.registry_as_of_stamp()
    registry_input = _ok(
        fingerprint(
            {
                "class": _REGISTRY_AS_OF_CLASS,
                "registry_as_of": admitted.registry_as_of.fp1_identity(),
                "fingerprint": admitted.set_fingerprint.value,
            }
        )
    )
    for combo in admitted.combos:
        config = _ok(admitted.compile_combo(combo, **settings))
        # Verbatim in the resolved run-config the CT-32 label reads.
        assert config.keys[REGISTRY_AS_OF_KEY] == expected_stamp
        result = _ok(
            mint_run_performance_result(
                config,
                evidence_range=_ok(Interval.try_create(_instant(_NS), _instant(_NS + 1_000))),
                stream_order=(combo.instrument,),
                slice_count=1,
                filled_count=0,
                resting_count=0,
                data_points_processed=1,
                outcome_identity={"done": True},
            )
        )
        assert registry_input in result.result_label.input_fingerprints


def test_sweep_registry_as_of_key_matches_the_ct32_field() -> None:
    assert REGISTRY_AS_OF_KEY == CT32_REGISTRY_AS_OF_KEY == "registry_as_of"


# --- guards and surface -------------------------------------------------------


def test_admission_refuses_a_non_port_and_a_non_writer() -> None:
    port, book_record, bms_record, bot_record = _fixture_port()
    decl = _declaration(
        bot=bot_record.stable_id, book=book_record.stable_id, bms=bms_record.stable_id
    )
    bad_port = admit_sweep(decl, object(), _writer())
    assert is_refusal(bad_port)
    assert bad_port.context["field"] == "port"
    bad_writer = admit_sweep(decl, port, "node-a")
    assert is_refusal(bad_writer)
    assert bad_writer.context["field"] == "writer"


def test_admission_refuses_a_malformed_declaration() -> None:
    port, _book_record, _bms_record, _bot_record = _fixture_port()
    refused = admit_sweep(["not", "a", "declaration"], port, _writer())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "declaration"


def test_caller_may_not_declare_registry_as_of() -> None:
    admitted = _admit()
    combo = admitted.combos[0]
    flags: dict[str, object] = {
        STARTING_CAPITAL_KEY: _SEED,
        REGISTRY_AS_OF_KEY: {"value_ns": 1, "fingerprint": "x"},
    }
    refused = admitted.compile_combo(
        combo,
        invocation_flags=flags,
        workspace_defaults=_run_settings()["workspace_defaults"],
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "invocation_flags"
    # The same guard covers a workspace-default declaration of registry_as_of.
    on_defaults = admitted.compile_combo(
        combo,
        invocation_flags={STARTING_CAPITAL_KEY: _SEED},
        workspace_defaults={
            "account_id": "acct-replay",
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_RECORDED,
            "venue_id": "venue-replay",
            REGISTRY_AS_OF_KEY: {"value_ns": 1, "fingerprint": "x"},
        },
    )
    assert is_refusal(on_defaults)
    assert on_defaults.context["field"] == "workspace_defaults"


def test_compile_all_returns_a_single_combos_compile_refusal() -> None:
    admitted = _admit(parameters={"lookback": [10, 20]})
    # Omitting venue_id makes every combo's compile refuse; compile_all returns
    # the first refusal rather than a half-built batch (Story 20.3 isolates them).
    refused = admitted.compile_all(
        invocation_flags={STARTING_CAPITAL_KEY: _SEED},
        workspace_defaults={
            "account_id": "acct-replay",
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_RECORDED,
        },
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "venue_id"


def test_stale_bms_reference_at_admission_also_refuses() -> None:
    book_record = _record("book-definition", _book())
    bms_v1 = _record("bms-definition", _bms(cadence=1))
    bms_v2 = _record("bms-definition", _bms(cadence=2))
    bot_record = _bot_record()
    supersedes = (_ok(SupersedesRef.try_create(bms_v2.stable_id, bms_v1.stable_id)),)
    port = _port(book_record, bms_v1, bms_v2, bot_record, supersedes=supersedes)
    decl = _declaration(bot=bot_record.stable_id, book=book_record.stable_id, bms=bms_v1.stable_id)
    refused = admit_sweep(decl, port, _writer())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.STALE_EVIDENCE


def test_compile_and_label_refuse_a_foreign_combo() -> None:
    admitted = _admit()
    foreign = expand_sweep(
        _declaration(
            bot="other-bot",
            book="other-book",
            bms="other-bms",
            instruments=["XAUUSD"],
            timeframes=[_TF_5M],
        )
    )
    stranger = _ok(foreign)[0]
    assert isinstance(stranger, SweepRunSpec)
    refused_compile = admitted.compile_combo(stranger, **_run_settings())
    assert is_refusal(refused_compile)
    assert refused_compile.context["field"] == "combo"
    refused_label = admitted.run_label(stranger)
    assert is_refusal(refused_label)
    refused_type = admitted.run_label(object())
    assert is_refusal(refused_type)


def test_admission_surface_is_on_both_doors_identity_equal() -> None:
    assert api.admit_sweep is qmb.admit_sweep
    assert api.AdmittedSweep is qmb.AdmittedSweep
    assert api.SweepLabel is qmb.SweepLabel
    assert api.sweep_admission_identity is qmb.sweep_admission_identity
    assert api.REGISTRY_AS_OF_KEY == qmb.REGISTRY_AS_OF_KEY
    for name in (
        "admit_sweep",
        "AdmittedSweep",
        "SweepLabel",
        "sweep_admission_identity",
        "SWEEP_LABEL_CLASS",
        "SWEEP_RUN_LABEL_CLASS",
    ):
        assert name in api.__all__
        assert name in qmb.__all__
