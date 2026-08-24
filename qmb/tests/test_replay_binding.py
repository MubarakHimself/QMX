"""Story 13.5 — starting_capital seed and the world=replay binding mint."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.config import (
    CLOCK_REPLAY,
    CONFIG_FRAGMENT_CLASS,
    FOLD_RATED,
    FOLD_UNRATED,
    FRAGMENT_FORMAT_VERSION,
    PROVENANCE_RECORDED,
    SOURCE_BOOK,
    STARTING_CAPITAL_KEY,
    ConfigFragment,
    ReplayBinding,
    ResolvedRunConfig,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.doors import api
from qmb.execution import admit_open, evaluate_exit, mint_replay_exit, require_full_loss_before_open
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, Money, Price, PriceDelta, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord
from qmf.risk.binding import (
    STATE_CARRY_COUNTERS,
    BmsInstanceId,
    BookBindingRecord,
    BookInstanceId,
    CapabilityCheckResult,
    PositionModel,
    StateCarry,
    StateCarryChoice,
)
from qmf.risk.door import (
    Direction,
    EntryIntent,
    ExitIntent,
    ExitKind,
    ExitLogicRef,
    ReasonCode,
    refuse_no_full_loss_price,
)
from qmf.risk.exit_record import (
    CloseOutcome,
    CloseReason,
    ClosingAuthority,
    ExitResultLabel,
)
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.paper import ExecutionTarget
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
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_SEED_ALT = Money(value=2_000_000, currency="USD", scale=2)


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
    port = _port((book_record, bms_record, bot), pointers=(pointer, book_pointer))
    book_fragment = _ok(materialize_book_fragment(port, book_record.stable_id, _writer()))
    bms_fragment = _ok(materialize_bms_fragment(port, bms_record.stable_id, _writer()))
    return book_fragment, bms_fragment, port, bot


def _defaults() -> dict[str, object]:
    return {
        "account_id": "acct-replay",
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "venue_id": "venue-replay",
    }


def _compile(
    *,
    run_spec: Mapping[str, object] | None = None,
    invocation_flags: Mapping[str, object] | None = None,
    workspace_defaults: Mapping[str, object] | None = None,
    book_fragment: ConfigFragment | None = None,
    bms_fragment: ConfigFragment | None = None,
    port: RegistryReadPort | None = None,
    bot: RegistrationRecord | None = None,
    include_seed: bool = True,
) -> Result[ResolvedRunConfig]:
    materialized_book, materialized_bms, materialized_port, materialized_bot = _fragments()
    spec: dict[str, object] = {"bot": (bot or materialized_bot).stable_id}
    if include_seed:
        spec[STARTING_CAPITAL_KEY] = _SEED
    if run_spec is not None:
        spec.update(run_spec)
        if "bot" not in run_spec:
            spec["bot"] = (bot or materialized_bot).stable_id
        if include_seed and STARTING_CAPITAL_KEY not in run_spec:
            spec[STARTING_CAPITAL_KEY] = _SEED
    return compile_run_config(
        port or materialized_port,
        book_fragment=book_fragment or materialized_book,
        bms_fragment=bms_fragment or materialized_bms,
        run_spec=spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults if workspace_defaults is not None else _defaults(),
    )


def _unchecked_book_fragment(source_fp1: Fingerprint, keys: Mapping[str, object]) -> ConfigFragment:
    identity: dict[str, object] = {
        "class": CONFIG_FRAGMENT_CLASS,
        "format_version": FRAGMENT_FORMAT_VERSION,
        "keys": dict(keys),
        "source_fp1": source_fp1.value,
        "source_kind": SOURCE_BOOK,
    }
    return ConfigFragment(
        format_version=FRAGMENT_FORMAT_VERSION,
        source_kind=SOURCE_BOOK,
        source_fp1=source_fp1,
        keys=keys,
        fingerprint=_ok(fingerprint(identity)),
        lineage=None,
        preset_name=None,
    )


def _fp(seed: str) -> Fingerprint:
    return _ok(fingerprint({"seed": seed}))


def _live_binding(book_fp1: Fingerprint, bms_fp1: Fingerprint) -> BookBindingRecord:
    venue = VenueId(value="venue-replay")
    account = "acct-replay"
    instance = _ok(BookInstanceId.try_create("live-book-inst-1"))
    bms_instance = _ok(BmsInstanceId.derive(bms_fp1, account, venue, World.LIVE))
    carry = _ok(StateCarry.try_create(dict.fromkeys(STATE_CARRY_COUNTERS, StateCarryChoice.RESET)))
    capability = CapabilityCheckResult(
        position_model=PositionModel.HEDGING,
        settlement_currency="USD",
        satisfied_capabilities=frozenset(),
        shared_flatten_signature=None,
        satisfied_sensor_baselines=frozenset(),
        live_path_rung_baseline_present=True,
        rank_table_non_contradicted=True,
    )
    return _ok(
        BookBindingRecord.try_create(
            instance,
            bms_instance,
            venue,
            account,
            World.LIVE,
            book_fp1,
            bms_fp1,
            carry,
            capability,
        )
    )


class _OffsetStopModule:
    def __init__(self, offset: int = 500) -> None:
        self.offset = offset

    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        if direction is Direction.LONG:
            value = entry_price.value - self.offset
        else:
            value = entry_price.value + self.offset
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


class _NoStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        return refuse_no_full_loss_price(module="no-stop")


def test_compile_mints_one_world_replay_binding_and_seeds_the_ledger() -> None:
    compiled = _ok(_compile())
    binding = compiled.replay_binding
    assert isinstance(binding, ReplayBinding)
    assert compiled.binding_fp1 == binding.fingerprint
    assert binding.world is World.REPLAY
    assert binding.record.world is World.REPLAY
    assert binding.book_instance.world is World.REPLAY
    assert binding.starting_capital == _SEED
    assert binding.virtual_ledger.seed == _SEED
    assert binding.virtual_ledger.equity == _SEED
    assert binding.virtual_ledger.binding_epoch == binding.fingerprint
    assert binding.seed_overridden is False
    assert compiled.fold_rating == FOLD_RATED
    assert compiled.keys[STARTING_CAPITAL_KEY] == _SEED.fp1_identity()
    assert compiled.fp1_identity()["binding_fp1"] == binding.fingerprint.value
    assert binding.fingerprint.value.startswith("fp1:sha256:")


def test_same_inputs_mint_the_same_binding() -> None:
    first = _ok(_compile())
    second = _ok(_compile())
    assert first.binding_fp1 == second.binding_fp1
    assert first.replay_binding is not None
    assert second.replay_binding is not None
    assert first.replay_binding.fingerprint == second.replay_binding.fingerprint
    assert first.fingerprint == second.fingerprint


def test_book_fragment_may_default_starting_capital() -> None:
    book, bms, port, bot = _fragments()
    sizing_raw = book.keys["sizing"]
    assert isinstance(sizing_raw, Mapping)
    sizing = dict(cast("Mapping[str, object]", sizing_raw))
    sizing[STARTING_CAPITAL_KEY] = _SEED.fp1_identity()
    defaulted = _unchecked_book_fragment(book.source_fp1, {**dict(book.keys), "sizing": sizing})
    compiled = _ok(
        compile_run_config(
            port,
            book_fragment=defaulted,
            bms_fragment=bms,
            run_spec={"bot": bot.stable_id},
            workspace_defaults=_defaults(),
        )
    )
    assert compiled.replay_binding is not None
    assert compiled.replay_binding.starting_capital.fp1_identity() == _SEED.fp1_identity()
    assert compiled.seed_overridden is False
    assert compiled.fold_rating == FOLD_RATED


def test_invocation_flag_override_stamps_seed_overridden_and_unrated() -> None:
    compiled = _ok(_compile(invocation_flags={STARTING_CAPITAL_KEY: _SEED_ALT}))
    assert compiled.replay_binding is not None
    assert compiled.replay_binding.seed_overridden is True
    assert compiled.fold_rating == FOLD_UNRATED
    assert compiled.replay_binding.starting_capital.fp1_identity() == _SEED_ALT.fp1_identity()
    rated = _ok(_compile())
    assert rated.fold_rating == FOLD_RATED
    assert compiled.binding_fp1 != rated.binding_fp1


def test_missing_starting_capital_is_invalid_input() -> None:
    refused = _compile(include_seed=False)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == STARTING_CAPITAL_KEY


def test_float_starting_capital_is_invalid_input() -> None:
    refused = _compile(run_spec={STARTING_CAPITAL_KEY: 10000.0})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == STARTING_CAPITAL_KEY


def test_non_usd_starting_capital_is_policy_rejection() -> None:
    refused = _compile(
        run_spec={STARTING_CAPITAL_KEY: Money(value=1_000_000, currency="EUR", scale=2)}
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_caller_declared_seed_overridden_is_invalid() -> None:
    refused = _compile(run_spec={"seed_overridden": True})
    assert is_refusal(refused)
    assert refused.context["field"] == "seed_overridden"


def test_replay_binding_is_incomparable_to_live() -> None:
    compiled = _ok(_compile())
    binding = compiled.replay_binding
    assert binding is not None
    live = _live_binding(compiled.book_fp1, compiled.bms_fp1)
    live_epoch = _ok(live.fingerprint())
    assert binding.fingerprint != live_epoch
    assert binding.record.tuple_identity()["world"] == World.REPLAY.value
    assert live.tuple_identity()["world"] == World.LIVE.value
    compared = qmb.check_incomparable_to_live(binding, live)
    assert is_refusal(compared)
    assert compared.category is RefusalCategory.POLICY_REJECTION
    assert compared.context["field"] == "world"


def test_different_seed_mints_a_different_binding() -> None:
    first = _ok(_compile())
    second = _ok(_compile(run_spec={STARTING_CAPITAL_KEY: _SEED_ALT}))
    assert first.binding_fp1 != second.binding_fp1


def test_admit_open_consumes_ct23_and_requires_full_loss_price() -> None:
    compiled = _ok(_compile())
    binding = compiled.replay_binding
    assert binding is not None
    instrument = Instrument(venue=VenueId(value="venue-replay"), symbol="EURUSD")
    entry = _ok(Price.try_create(1_10000, instrument, 5))
    intent = _ok(
        EntryIntent.try_create(
            instrument,
            Direction.LONG,
            _ok(ReasonCode.try_create("breakout", "scalper-v1")),
            _ok(ExecutionTarget.try_create("demo", VenueId(value="venue-replay"), "acct-replay")),
        )
    )
    logic = _ok(ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}))
    requested = _ok(ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE))
    admitted = _ok(
        admit_open(
            binding,
            intent=intent,
            entry_price=entry,
            exit_logic_ref=logic,
            module=_OffsetStopModule(),
            book_resolved_requested_r=requested,
        )
    )
    assert admitted.declared_full_loss_price.value == entry.value - 500
    refused = admit_open(
        binding,
        intent=intent,
        entry_price=entry,
        exit_logic_ref=logic,
        module=_NoStopModule(),
        book_resolved_requested_r=requested,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    none_price = require_full_loss_before_open(None)
    assert is_refusal(none_price)
    assert none_price.category is RefusalCategory.INVALID_INPUT


def test_mint_replay_exit_is_ct29_against_the_replay_binding() -> None:
    compiled = _ok(_compile())
    binding = compiled.replay_binding
    assert binding is not None
    instrument = Instrument(venue=VenueId(value="venue-replay"), symbol="EURUSD")
    label = _ok(ExitResultLabel.try_create("demo", World.REPLAY))
    record = _ok(
        mint_replay_exit(
            binding,
            virtual_position_ref=_fp("pos-1"),
            opening_bot_id="bot-alpha",
            original_risk_distance=_ok(PriceDelta.try_create(50, instrument, 5)),
            original_risk_amount=Money(value=10_000, currency="USD", scale=2),
            fill_references=(_fp("fill-1"),),
            realized_pnl=Money(value=-10_000, currency="USD", scale=2),
            cost_components=(),
            close_reason=CloseReason.PROTECTIVE_STOP_FILL,
            mechanism=CloseReason.PROTECTIVE_STOP_FILL,
            outcome=CloseOutcome.LOSS,
            closing_authority=ClosingAuthority.BOOK_POLICY,
            close_reason_mapping_version=1,
            result_label=label,
            loss_predicate_format_version=1,
            recorded_at=_instant(),
            arbitration_record_ref=_fp("arb-1"),
        )
    )
    assert record.binding_epoch == binding.fingerprint
    assert record.result_label.world is World.REPLAY
    live_label = _ok(ExitResultLabel.try_create("live", World.LIVE))
    mismatched = mint_replay_exit(
        binding,
        virtual_position_ref=_fp("pos-2"),
        opening_bot_id="bot-alpha",
        original_risk_distance=_ok(PriceDelta.try_create(50, instrument, 5)),
        original_risk_amount=Money(value=10_000, currency="USD", scale=2),
        fill_references=(_fp("fill-2"),),
        realized_pnl=Money(value=-10_000, currency="USD", scale=2),
        cost_components=(),
        close_reason=CloseReason.PROTECTIVE_STOP_FILL,
        mechanism=CloseReason.PROTECTIVE_STOP_FILL,
        outcome=CloseOutcome.LOSS,
        closing_authority=ClosingAuthority.BOOK_POLICY,
        close_reason_mapping_version=1,
        result_label=live_label,
        loss_predicate_format_version=1,
        recorded_at=_instant(),
        arbitration_record_ref=_fp("arb-2"),
    )
    assert is_refusal(mismatched)
    assert mismatched.category is RefusalCategory.POLICY_REJECTION


def test_evaluate_exit_consumes_ct23() -> None:
    compiled = _ok(_compile())
    binding = compiled.replay_binding
    assert binding is not None
    intent = _ok(
        ExitIntent.try_create(
            ExitKind.CLOSE_FULL,
            _ok(ReasonCode.try_create("done", "scalper-v1")),
            _fp("vp-1"),
        )
    )
    evaluated = _ok(evaluate_exit(binding, intent))
    assert evaluated.kind is ExitKind.CLOSE_FULL
    assert is_refusal(evaluate_exit("not-a-binding", intent))


def test_api_door_matches_library_binding_surface() -> None:
    book, bms, port, bot = _fragments()
    library = _ok(
        qmb.compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults=_defaults(),
        )
    )
    door = _ok(
        api.compile_run_config(
            port,
            book_fragment=book,
            bms_fragment=bms,
            run_spec={"bot": bot.stable_id, STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults=_defaults(),
        )
    )
    assert library.binding_fp1 == door.binding_fp1
    assert api.ReplayBinding is qmb.ReplayBinding is ReplayBinding
    assert api.admit_open is qmb.admit_open is admit_open
    assert api.mint_replay_exit is qmb.mint_replay_exit
    assert api.FOLD_UNRATED == qmb.FOLD_UNRATED == FOLD_UNRATED
