"""Reference usage — starting_capital seed and the world=replay binding (Story 13.5).

Executable::

    python qmb/examples/replay_binding_usage.py

Shows the things B-3 / Story 13.5 pin down:

1. ``starting_capital`` is a mandatory run-spec seed (the Book fragment may
   default it) and seeds the minted binding's virtual ledger.
2. An invocation-flag override stamps ``seed_overridden`` and forces the fold
   to ``unrated``.
3. Each compile mints exactly one AD-29/CT-28 binding with ``world=replay``,
   a different identity from any live binding and incomparable to it.
4. Sizing, R-freeze, and exits consume qmf-risk CT-23 and CT-29; an AD-40
   full-loss price is required before any open.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.config import (
    CLOCK_REPLAY,
    FOLD_RATED,
    FOLD_UNRATED,
    PROVENANCE_RECORDED,
    STARTING_CAPITAL_KEY,
    check_incomparable_to_live,
    compile_run_config,
    materialize_bms_fragment,
    materialize_book_fragment,
)
from qmb.execution import admit_open, mint_replay_exit, require_full_loss_before_open
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, Money, Price, PriceDelta, UnitKind
from qmf.core.fingerprint import World, fingerprint
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
from qmf.risk.door import Direction, EntryIntent, ExitLogicRef, ReasonCode
from qmf.risk.exit_record import CloseOutcome, CloseReason, ClosingAuthority, ExitResultLabel
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


class _OffsetStopModule:
    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: object
    ) -> Result[Price]:
        value = entry_price.value - 500 if direction is Direction.LONG else entry_price.value + 500
        return Price.try_create(value, entry_price.instrument, entry_price.scale)


def main() -> None:
    book = _book()
    bms = _bms()
    book_record = _definition_record("book-definition", book)
    bms_record = _definition_record("bms-definition", bms)
    bot = _unwrap(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            [],
            {"class": "bot-definition", "alias": "mean-reversion"},
            _writer("bot-definition"),
            0,
            _instant(),
        ),
        "bot record",
    )
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
                    DatedPointer.try_create("mean-reversion", bot.stable_id, _instant()),
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
    defaults = {
        "account_id": "acct-replay",
        "clock": CLOCK_REPLAY,
        "data_provenance": PROVENANCE_RECORDED,
        "venue_id": "venue-replay",
    }
    compiled = _unwrap(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": "mean-reversion", STARTING_CAPITAL_KEY: _SEED},
            workspace_defaults=defaults,
        ),
        "resolved run-config",
    )
    binding = compiled.replay_binding
    assert binding is not None
    assert binding.world is World.REPLAY
    assert binding.starting_capital == _SEED
    assert binding.virtual_ledger.equity == _SEED
    assert compiled.fold_rating == FOLD_RATED
    print(f"minted world=replay binding {binding.fingerprint.value}")
    print("virtual ledger seeded from starting_capital")

    missing = compile_run_config(
        port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec={"bot": "mean-reversion"},
        workspace_defaults=defaults,
    )
    assert is_refusal(missing)
    assert missing.context["field"] == STARTING_CAPITAL_KEY
    print("starting_capital is a mandatory run-spec field")

    overridden = _unwrap(
        compile_run_config(
            port,
            book_fragment=book_fragment,
            bms_fragment=bms_fragment,
            run_spec={"bot": "mean-reversion", STARTING_CAPITAL_KEY: _SEED},
            invocation_flags={
                STARTING_CAPITAL_KEY: Money(value=2_000_000, currency="USD", scale=2)
            },
            workspace_defaults=defaults,
        ),
        "overridden seed",
    )
    assert overridden.replay_binding is not None
    assert overridden.replay_binding.seed_overridden is True
    assert overridden.fold_rating == FOLD_UNRATED
    assert overridden.binding_fp1 != compiled.binding_fp1
    print("flag override stamps seed_overridden and forces the fold unrated")

    live = _unwrap(
        BookBindingRecord.try_create(
            _unwrap(BookInstanceId.try_create("live-book-inst-1"), "live instance"),
            _unwrap(
                BmsInstanceId.derive(
                    compiled.bms_fp1,
                    "acct-replay",
                    VenueId(value="venue-replay"),
                    World.LIVE,
                ),
                "live bms instance",
            ),
            VenueId(value="venue-replay"),
            "acct-replay",
            World.LIVE,
            compiled.book_fp1,
            compiled.bms_fp1,
            _unwrap(
                StateCarry.try_create(dict.fromkeys(STATE_CARRY_COUNTERS, StateCarryChoice.RESET)),
                "state carry",
            ),
            CapabilityCheckResult(
                position_model=PositionModel.HEDGING,
                settlement_currency="USD",
                satisfied_capabilities=frozenset(),
                shared_flatten_signature=None,
                satisfied_sensor_baselines=frozenset(),
                live_path_rung_baseline_present=True,
                rank_table_non_contradicted=True,
            ),
        ),
        "live binding",
    )
    compared = check_incomparable_to_live(binding, live)
    assert is_refusal(compared)
    assert compared.category is RefusalCategory.POLICY_REJECTION
    assert _unwrap(live.fingerprint(), "live epoch") != binding.fingerprint
    print("replay binding is incomparable to any live binding")

    instrument = Instrument(venue=VenueId(value="venue-replay"), symbol="EURUSD")
    admitted = _unwrap(
        admit_open(
            binding,
            intent=_unwrap(
                EntryIntent.try_create(
                    instrument,
                    Direction.LONG,
                    _unwrap(ReasonCode.try_create("breakout", "scalper-v1"), "reason"),
                    _unwrap(
                        ExecutionTarget.try_create(
                            "demo", VenueId(value="venue-replay"), "acct-replay"
                        ),
                        "target",
                    ),
                ),
                "entry intent",
            ),
            entry_price=_unwrap(Price.try_create(1_10000, instrument, 5), "entry price"),
            exit_logic_ref=_unwrap(
                ExitLogicRef.try_create("book.default.evidence_stop", {"style": "structure"}),
                "exit logic",
            ),
            module=_OffsetStopModule(),
            book_resolved_requested_r=_unwrap(
                ExactRational.try_create(1, 1, UnitKind.R_MULTIPLE), "requested_r"
            ),
        ),
        "admitted entry",
    )
    assert admitted.declared_full_loss_price is not None
    none_price = require_full_loss_before_open(None)
    assert is_refusal(none_price)
    print("CT-23 admit requires an AD-40 full-loss price before any open")

    exit_record = _unwrap(
        mint_replay_exit(
            binding,
            virtual_position_ref=_unwrap(fingerprint({"seed": "pos-1"}), "position"),
            opening_bot_id="bot-alpha",
            original_risk_distance=_unwrap(PriceDelta.try_create(50, instrument, 5), "distance"),
            original_risk_amount=Money(value=10_000, currency="USD", scale=2),
            fill_references=(_unwrap(fingerprint({"seed": "fill-1"}), "fill"),),
            realized_pnl=Money(value=-10_000, currency="USD", scale=2),
            cost_components=(),
            close_reason=CloseReason.PROTECTIVE_STOP_FILL,
            mechanism=CloseReason.PROTECTIVE_STOP_FILL,
            outcome=CloseOutcome.LOSS,
            closing_authority=ClosingAuthority.BOOK_POLICY,
            close_reason_mapping_version=1,
            result_label=_unwrap(ExitResultLabel.try_create("demo", World.REPLAY), "label"),
            loss_predicate_format_version=1,
            recorded_at=_instant(),
            arbitration_record_ref=_unwrap(fingerprint({"seed": "arb-1"}), "arb"),
        ),
        "exit record",
    )
    assert exit_record.binding_epoch == binding.fingerprint
    assert exit_record.result_label.world is World.REPLAY
    print("CT-29 exit is minted against the run's world=replay binding")

    print(f"qmb {qmb.__version__}")
    print("replay binding ok")


if __name__ == "__main__":
    main()
