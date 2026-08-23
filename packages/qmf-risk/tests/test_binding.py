"""Story 10.4 — the binding chain, identity trinity, and bind-time capability check.

Verifies the Book binding record on qmf-core nouns: the binding tuple
``(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)`` with ``role`` deliberately
absent and aligned with the ``(VenueId, account)`` command stream (AC1); the identity
trinity — a Book version fingerprint, an operator-minted Book instance, a content-derived
``BmsInstanceId``, and the binding epoch as the record's own fingerprint, with an
equal-fingerprint re-mint refused (AC2); the mandatory complete per-counter ``state_carry``
with carry gated on a human-signed carries-ledger edge and the independent
continues-performance edge (AC3); the bind-time capability check over the CT-18 projection
with every shortfall refusing at bind time (AC4); the settlement-currency policy rejection
(AC5); and the netted-second-Book shared-flatten refusal (AC6) (CT-28, CT-27; DEC-0143,
DEC-0158).
"""

from __future__ import annotations

from qmf.core import (
    Fingerprint,
    Instant,
    RefusalCategory,
    VenueId,
    World,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.binding import (
    STATE_CARRY_COUNTERS,
    BindingLineageEdgeKind,
    BindingState,
    BmsInstanceId,
    BookBindingLog,
    BookBindingRecord,
    BookBindingRequirements,
    BookInstance,
    BookInstanceId,
    CapabilityCheckResult,
    ContinuesPerformanceEdge,
    PairingRecord,
    PositionModel,
    SignedLedgerEdge,
    StateCarry,
    StateCarryChoice,
    StateCarryCounter,
    VenueBindingProfile,
    bind_time_capability_check,
    check_rank_table_non_contradiction,
)
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable

_INSTANT = Instant(value_ns=1_700_000_000_000_000_000)
_VENUE = VenueId(value="venue-ctrader")
_ACCOUNT = "acct-001"


# --- builders ----------------------------------------------------------------


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _book_version() -> Fingerprint:
    return _fp("book-version-1")


def _bms_version() -> Fingerprint:
    return _fp("bms-version-1")


def _book_instance_id(value: str = "book-inst-1") -> BookInstanceId:
    result = BookInstanceId.try_create(value)
    assert is_ok(result)
    return result.value


def _bms_instance_id() -> BmsInstanceId:
    result = BmsInstanceId.derive(_bms_version(), _ACCOUNT, _VENUE, World.LIVE)
    assert is_ok(result)
    return result.value


def _state_carry(**overrides: StateCarryChoice) -> StateCarry:
    per_counter: dict[StateCarryCounter, StateCarryChoice] = dict.fromkeys(
        STATE_CARRY_COUNTERS, StateCarryChoice.RESET
    )
    for name, choice in overrides.items():
        per_counter[StateCarryCounter(name)] = choice
    result = StateCarry.try_create(per_counter)
    assert is_ok(result)
    return result.value


def _rank_table() -> ControlRankTable:
    rows = [
        ControlRankRow(control_action_kind=ControlActionKind.FLATTEN, rank=0),
        ControlRankRow(control_action_kind=ControlActionKind.DRAIN, rank=1),
        ControlRankRow(control_action_kind=ControlActionKind.SUSPEND_NEW, rank=2),
        ControlRankRow(control_action_kind=ControlActionKind.RESUME, rank=3),
    ]
    result = ControlRankTable.try_create(rows)
    assert is_ok(result)
    return result.value


def _requirements(
    *,
    accounting_currency: str = "USD",
    required_venue_capabilities: object = frozenset({"protective-stop-attachment"}),
    required_sensor_ids: object = frozenset({"sqs-eurusd"}),
    control_policy_ranks: object | None = None,
) -> BookBindingRequirements:
    result = BookBindingRequirements.try_create(
        accounting_currency,
        required_venue_capabilities,
        required_sensor_ids,
        {} if control_policy_ranks is None else control_policy_ranks,
    )
    assert is_ok(result)
    return result.value


def _profile(
    *,
    declared_capabilities: object = frozenset({"protective-stop-attachment", "close_all"}),
    position_model: object = PositionModel.HEDGING,
    settlement_currency: object = "USD",
) -> VenueBindingProfile:
    result = VenueBindingProfile.try_create(
        declared_capabilities, position_model, settlement_currency
    )
    assert is_ok(result)
    return result.value


def _capability_result(**overrides: object) -> CapabilityCheckResult:
    kwargs: dict[str, object] = {
        "requirements": _requirements(),
        "profile": _profile(),
        "bms_rank_table": _rank_table(),
        "sensor_baselines_present": frozenset({"sqs-eurusd"}),
        "live_path_rung_baseline_present": True,
        "is_second_book_on_account": False,
        "overlapping_instrument_set": False,
    }
    kwargs.update(overrides)
    result = bind_time_capability_check(**kwargs)  # type: ignore[arg-type]
    assert is_ok(result)
    return result.value


def _record(**overrides: object) -> BookBindingRecord:
    kwargs: dict[str, object] = {
        "book_instance_id": _book_instance_id(),
        "bms_instance_id": _bms_instance_id(),
        "venue_id": _VENUE,
        "account_id": _ACCOUNT,
        "world": World.LIVE,
        "book_definition_fingerprint": _book_version(),
        "bms_definition_fingerprint": _bms_version(),
        "state_carry": _state_carry(),
        "capability_check_result": _capability_result(),
    }
    kwargs.update(overrides)
    result = BookBindingRecord.try_create(**kwargs)  # type: ignore[arg-type]
    assert is_ok(result)
    return result.value


# --- AC1: the binding tuple and the command stream ---------------------------


def test_tuple_is_the_five_components_without_role() -> None:
    record = _record()
    identity = record.tuple_identity()
    assert set(identity) == {
        "class",
        "book_instance_id",
        "bms_instance_id",
        "venue_id",
        "account_id",
        "world",
    }
    # role is deliberately not in the tuple — it rides the execution-target record.
    assert "role" not in identity


def test_tuple_aligns_with_the_command_stream() -> None:
    record = _record()
    assert record.command_stream() == (_VENUE, _ACCOUNT)


def test_record_refuses_malformed_tuple_parts() -> None:
    assert is_refusal(
        BookBindingRecord.try_create(
            "not-an-id",
            _bms_instance_id(),
            _VENUE,
            _ACCOUNT,
            World.LIVE,
            _book_version(),
            _bms_version(),
            _state_carry(),
            _capability_result(),
        )
    )
    assert is_refusal(
        BookBindingRecord.try_create(
            _book_instance_id(),
            "not-an-id",
            _VENUE,
            _ACCOUNT,
            World.LIVE,
            _book_version(),
            _bms_version(),
            _state_carry(),
            _capability_result(),
        )
    )
    assert is_refusal(
        BookBindingRecord.try_create(
            _book_instance_id(),
            _bms_instance_id(),
            "not-a-venue",
            _ACCOUNT,
            World.LIVE,
            _book_version(),
            _bms_version(),
            _state_carry(),
            _capability_result(),
        )
    )
    assert is_refusal(
        BookBindingRecord.try_create(
            _book_instance_id(),
            _bms_instance_id(),
            _VENUE,
            "  ",
            World.LIVE,
            _book_version(),
            _bms_version(),
            _state_carry(),
            _capability_result(),
        )
    )
    assert is_refusal(
        BookBindingRecord.try_create(
            _book_instance_id(),
            _bms_instance_id(),
            _VENUE,
            _ACCOUNT,
            "not-a-world",
            _book_version(),
            _bms_version(),
            _state_carry(),
            _capability_result(),
        )
    )
    assert is_refusal(
        BookBindingRecord.try_create(
            _book_instance_id(),
            _bms_instance_id(),
            _VENUE,
            _ACCOUNT,
            World.LIVE,
            "not-a-fp",
            _bms_version(),
            _state_carry(),
            _capability_result(),
        )
    )
    assert is_refusal(
        BookBindingRecord.try_create(
            _book_instance_id(),
            _bms_instance_id(),
            _VENUE,
            _ACCOUNT,
            World.LIVE,
            _book_version(),
            "not-a-fp",
            _state_carry(),
            _capability_result(),
        )
    )
    assert is_refusal(
        BookBindingRecord.try_create(
            _book_instance_id(),
            _bms_instance_id(),
            _VENUE,
            _ACCOUNT,
            World.LIVE,
            _book_version(),
            _bms_version(),
            "not-a-state-carry",
            _capability_result(),
        )
    )
    assert is_refusal(
        BookBindingRecord.try_create(
            _book_instance_id(),
            _bms_instance_id(),
            _VENUE,
            _ACCOUNT,
            World.LIVE,
            _book_version(),
            _bms_version(),
            _state_carry(),
            "not-a-result",
        )
    )


def test_one_bms_per_account_serves_many_books() -> None:
    # Two different Book instances bind the same account and BMS instance — allowed.
    log = BookBindingLog()
    first = _record(book_instance_id=_book_instance_id("book-inst-A"))
    second = _record(book_instance_id=_book_instance_id("book-inst-B"))
    assert is_ok(log.mint(first))
    assert is_ok(log.mint(second))
    assert len(log.bindings()) == 2


def test_a_book_binds_exactly_one_bms_at_a_time() -> None:
    # A second live binding for the SAME Book instance, without a supersedes edge, refuses.
    log = BookBindingLog()
    first = _record(book_instance_id=_book_instance_id("book-inst-A"))
    minted = log.mint(first)
    assert is_ok(minted)
    # A different BMS instance for the same Book, no supersedes → refused.
    second = _record(
        book_instance_id=_book_instance_id("book-inst-A"),
        state_carry=_state_carry(cycle=StateCarryChoice.RESET),
        pairing_record=_pairing(),
    )
    result = log.mint(second)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def _pairing() -> PairingRecord:
    result = PairingRecord.try_create(_bms_instance_id(), _bms_instance_id(), "acct-demo")
    assert is_ok(result)
    return result.value


# --- AC2: the identity trinity ------------------------------------------------


def test_book_instance_is_operator_minted_and_distinct_by_mint() -> None:
    # Two copies of ONE version on ONE account are distinct by mint (opaque id + sequence).
    one = BookInstance.try_create(
        _book_instance_id("copy-1"), _book_version(), _ACCOUNT, _VENUE, World.LIVE, "mint-a", 0
    )
    two = BookInstance.try_create(
        _book_instance_id("copy-2"), _book_version(), _ACCOUNT, _VENUE, World.LIVE, "mint-b", 1
    )
    assert is_ok(one)
    assert is_ok(two)
    assert one.value.fp1_identity() != two.value.fp1_identity()
    assert one.value.instance_id != two.value.instance_id


def test_book_instance_refuses_bad_parts() -> None:
    assert is_refusal(
        BookInstance.try_create(
            "not-an-id", _book_version(), _ACCOUNT, _VENUE, World.LIVE, "mint", 0
        )
    )
    assert is_refusal(
        BookInstance.try_create(
            _book_instance_id(), "not-a-fp", _ACCOUNT, _VENUE, World.LIVE, "mint", 0
        )
    )
    assert is_refusal(
        BookInstance.try_create(
            _book_instance_id(), _book_version(), "  ", _VENUE, World.LIVE, "mint", 0
        )
    )
    assert is_refusal(
        BookInstance.try_create(
            _book_instance_id(), _book_version(), _ACCOUNT, "not-a-venue", World.LIVE, "mint", 0
        )
    )
    assert is_refusal(
        BookInstance.try_create(
            _book_instance_id(), _book_version(), _ACCOUNT, _VENUE, "not-a-world", "mint", 0
        )
    )
    assert is_refusal(
        BookInstance.try_create(
            _book_instance_id(), _book_version(), _ACCOUNT, _VENUE, World.LIVE, "  ", 0
        )
    )
    assert is_refusal(
        BookInstance.try_create(
            _book_instance_id(), _book_version(), _ACCOUNT, _VENUE, World.LIVE, "mint", True
        )
    )
    assert is_refusal(
        BookInstance.try_create(
            _book_instance_id(), _book_version(), _ACCOUNT, _VENUE, World.LIVE, "mint", -1
        )
    )


def test_book_instance_id_refuses_blank() -> None:
    assert is_refusal(BookInstanceId.try_create("   "))
    assert is_refusal(BookInstanceId.try_create(42))


def test_bms_instance_id_is_content_derived_and_stable() -> None:
    one = BmsInstanceId.derive(_bms_version(), _ACCOUNT, _VENUE, World.LIVE)
    two = BmsInstanceId.derive(_bms_version(), _ACCOUNT, _VENUE, World.LIVE)
    assert is_ok(one)
    assert is_ok(two)
    # Content-derived: same inputs → same id.
    assert one.value == two.value
    # A different account → a different id.
    other = BmsInstanceId.derive(_bms_version(), "acct-other", _VENUE, World.LIVE)
    assert is_ok(other)
    assert other.value != one.value
    assert one.value.value.startswith("fp1:sha256:")


def test_bms_instance_id_refuses_bad_parts() -> None:
    assert is_refusal(BmsInstanceId.derive("not-a-fp", _ACCOUNT, _VENUE, World.LIVE))
    assert is_refusal(BmsInstanceId.derive(_bms_version(), "  ", _VENUE, World.LIVE))
    assert is_refusal(BmsInstanceId.derive(_bms_version(), _ACCOUNT, "not-a-venue", World.LIVE))
    assert is_refusal(BmsInstanceId.derive(_bms_version(), _ACCOUNT, _VENUE, "not-a-world"))


def test_binding_epoch_is_the_records_own_fingerprint() -> None:
    record = _record()
    epoch = record.fingerprint()
    assert is_ok(epoch)
    assert epoch.value.value.startswith("fp1:sha256:")
    # The epoch is the full-record fingerprint, distinct from the tuple identity.
    assert record.tuple_identity() != record.fp1_identity()


def test_equal_fingerprint_rebinding_is_invalid_input_not_idempotent() -> None:
    log = BookBindingLog()
    record = _record()
    first = log.mint(record)
    assert is_ok(first)
    # A byte-identical second record fingerprints equal → refused, never silently accepted.
    duplicate = _record()
    result = log.mint(duplicate)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


# --- AC3: state_carry and the lineage edges ----------------------------------


def test_state_carry_is_mandatory_and_complete() -> None:
    assert is_refusal(StateCarry.try_create("not-a-mapping"))
    # A partial declaration (missing counters) is invalid input.
    partial = StateCarry.try_create({StateCarryCounter.LEDGER: StateCarryChoice.RESET})
    assert is_refusal(partial)
    assert partial.category is RefusalCategory.INVALID_INPUT
    # An unknown counter or an unrecognised choice is invalid input.
    assert is_refusal(StateCarry.try_create({"not-a-counter": "reset"}))
    bad_choice = {counter.value: "reset" for counter in STATE_CARRY_COUNTERS}
    bad_choice["ledger"] = "maybe"
    assert is_refusal(StateCarry.try_create(bad_choice))


def test_state_carry_accepts_string_names_and_reports_carried() -> None:
    declared = {counter.value: "reset" for counter in STATE_CARRY_COUNTERS}
    declared["ledger"] = "carry"
    result = StateCarry.try_create(declared)
    assert is_ok(result)
    assert result.value.carried_counters() == frozenset({StateCarryCounter.LEDGER})
    assert result.value.choice_for(StateCarryCounter.CYCLE) is StateCarryChoice.RESET


def test_carry_requires_a_signed_carries_ledger_edge() -> None:
    carrying = _state_carry(ledger=StateCarryChoice.CARRY)
    # No signed edge → invalid input (carry is legal only under a signed carries-ledger edge).
    without_edge = BookBindingRecord.try_create(
        _book_instance_id(),
        _bms_instance_id(),
        _VENUE,
        _ACCOUNT,
        World.LIVE,
        _book_version(),
        _bms_version(),
        carrying,
        _capability_result(),
    )
    assert is_refusal(without_edge)
    assert without_edge.category is RefusalCategory.INVALID_INPUT
    # With the signed edge → admitted.
    edge = SignedLedgerEdge.try_create("operator", _INSTANT, _fp("prior-binding"))
    assert is_ok(edge)
    with_edge = _record(state_carry=carrying, carries_ledger_edge=edge.value)
    assert with_edge.carries_ledger_edge is not None
    assert with_edge.fp1_identity()["carries_ledger_edge"] is not None


def test_all_reset_needs_no_edge() -> None:
    record = _record(state_carry=_state_carry())
    assert record.state_carry.carried_counters() == frozenset()
    assert record.carries_ledger_edge is None


def test_continues_performance_edge_is_independent_and_moves_no_money() -> None:
    # A continues-performance edge asserts a track record; it never gates a carry and is
    # never inferred from a carries-ledger edge.
    continues = ContinuesPerformanceEdge.try_create(_fp("prior-binding"))
    assert is_ok(continues)
    # Present alone (no carries-ledger edge) with an all-reset state_carry → admitted.
    record = _record(continues_performance_edge=continues.value)
    assert record.continues_performance_edge is not None
    assert record.carries_ledger_edge is None
    # A carry still refuses even with a continues-performance edge but no signed ledger edge.
    carrying = _state_carry(budget=StateCarryChoice.CARRY)
    refused = BookBindingRecord.try_create(
        _book_instance_id(),
        _bms_instance_id(),
        _VENUE,
        _ACCOUNT,
        World.LIVE,
        _book_version(),
        _bms_version(),
        carrying,
        _capability_result(),
        continues_performance_edge=continues.value,
    )
    assert is_refusal(refused)


def test_lineage_edges_carry_distinct_kinds() -> None:
    edge = SignedLedgerEdge.try_create("operator", _INSTANT, _fp("prior"))
    assert is_ok(edge)
    assert edge.value.fp1_identity()["kind"] == BindingLineageEdgeKind.CARRIES_LEDGER.value
    continues = ContinuesPerformanceEdge.try_create(_fp("prior"))
    assert is_ok(continues)
    assert (
        continues.value.fp1_identity()["kind"] == BindingLineageEdgeKind.CONTINUES_PERFORMANCE.value
    )


def test_signed_ledger_edge_refuses_bad_parts() -> None:
    assert is_refusal(SignedLedgerEdge.try_create("  ", _INSTANT, _fp("p")))
    assert is_refusal(SignedLedgerEdge.try_create("operator", 123, _fp("p")))
    assert is_refusal(SignedLedgerEdge.try_create("operator", _INSTANT, "not-a-fp"))


def test_continues_performance_edge_refuses_bad_part() -> None:
    assert is_refusal(ContinuesPerformanceEdge.try_create("not-a-fp"))


# --- AC4: the bind-time capability check -------------------------------------


def test_capability_check_passes_and_records_the_result() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_ok(result)
    assert result.value.position_model is PositionModel.HEDGING
    assert result.value.settlement_currency == "USD"
    assert result.value.rank_table_non_contradicted is True
    assert result.value.fp1_identity()["class"] == "capability-check-result"


def test_capability_check_refuses_bad_top_level_inputs() -> None:
    assert is_refusal(
        bind_time_capability_check(
            requirements="x",
            profile=_profile(),
            bms_rank_table=_rank_table(),
            sensor_baselines_present=frozenset({"sqs-eurusd"}),
            live_path_rung_baseline_present=True,
            is_second_book_on_account=False,
            overlapping_instrument_set=False,
        )
    )
    assert is_refusal(
        bind_time_capability_check(
            requirements=_requirements(),
            profile="x",
            bms_rank_table=_rank_table(),
            sensor_baselines_present=frozenset({"sqs-eurusd"}),
            live_path_rung_baseline_present=True,
            is_second_book_on_account=False,
            overlapping_instrument_set=False,
        )
    )
    assert is_refusal(
        bind_time_capability_check(
            requirements=_requirements(),
            profile=_profile(),
            bms_rank_table="x",
            sensor_baselines_present=frozenset({"sqs-eurusd"}),
            live_path_rung_baseline_present=True,
            is_second_book_on_account=False,
            overlapping_instrument_set=False,
        )
    )
    # non-bool flags
    assert is_refusal(
        bind_time_capability_check(
            requirements=_requirements(),
            profile=_profile(),
            bms_rank_table=_rank_table(),
            sensor_baselines_present=frozenset({"sqs-eurusd"}),
            live_path_rung_baseline_present="yes",
            is_second_book_on_account=False,
            overlapping_instrument_set=False,
        )
    )


def test_missing_required_capability_refuses_unsupported_capability() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(required_venue_capabilities=frozenset({"guaranteed-stop"})),
        profile=_profile(declared_capabilities=frozenset({"protective-stop-attachment"})),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_unmeasured_settlement_currency_is_unavailable_dependency() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(settlement_currency=None),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_unmeasured_position_model_is_unavailable_dependency() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(position_model=None),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_missing_sensor_baseline_is_unavailable_dependency() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(required_sensor_ids=frozenset({"sqs-eurusd", "sqs-gbpusd"})),
        profile=_profile(),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_missing_live_path_rung_baseline_is_unavailable_dependency() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=False,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_bad_sensor_baselines_collection_refuses() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(),
        bms_rank_table=_rank_table(),
        sensor_baselines_present="sqs-eurusd",
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_contradicting_rank_table_refuses_unsupported_capability() -> None:
    # The Book control_policy ranks FLATTEN at 9, the BMS table at 0 → contradiction.
    result = bind_time_capability_check(
        requirements=_requirements(control_policy_ranks={ControlActionKind.FLATTEN: 9}),
        profile=_profile(),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_agreeing_rank_table_passes() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(control_policy_ranks={ControlActionKind.FLATTEN: 0}),
        profile=_profile(),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_ok(result)


def test_check_rank_table_non_contradiction_standalone() -> None:
    assert is_ok(check_rank_table_non_contradiction({}, _rank_table()))
    assert is_ok(check_rank_table_non_contradiction({ControlActionKind.DRAIN: 1}, _rank_table()))
    # A kind absent from the BMS table is a contradiction.
    trimmed = ControlRankTable.try_create(
        [ControlRankRow(control_action_kind=ControlActionKind.FLATTEN, rank=0)]
    )
    assert is_ok(trimmed)
    absent = check_rank_table_non_contradiction({ControlActionKind.DRAIN: 1}, trimmed.value)
    assert is_refusal(absent)
    assert absent.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    # A differing rank is a contradiction.
    differing = check_rank_table_non_contradiction({ControlActionKind.FLATTEN: 5}, _rank_table())
    assert is_refusal(differing)
    # Bad inputs refuse.
    assert is_refusal(check_rank_table_non_contradiction("x", _rank_table()))
    assert is_refusal(check_rank_table_non_contradiction({}, "not-a-table"))
    assert is_refusal(
        check_rank_table_non_contradiction({ControlActionKind.FLATTEN: True}, _rank_table())
    )
    assert is_refusal(
        check_rank_table_non_contradiction({ControlActionKind.FLATTEN: -1}, _rank_table())
    )
    assert is_refusal(check_rank_table_non_contradiction({"not-a-kind": 0}, _rank_table()))


# --- AC5: settlement-currency mismatch is a policy rejection -----------------


def test_non_usd_settlement_currency_is_a_policy_rejection() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(settlement_currency="EUR"),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=False,
        overlapping_instrument_set=False,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_requirements_refuse_non_usd_accounting_currency() -> None:
    # The numeraire law: a non-USD accounting currency is a policy rejection at construction.
    result = BookBindingRequirements.try_create("EUR", frozenset[str](), frozenset[str](), {})
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_requirements_refuse_bad_token_sets_and_ranks() -> None:
    assert is_refusal(BookBindingRequirements.try_create("USD", "cap", frozenset[str](), {}))
    assert is_refusal(
        BookBindingRequirements.try_create("USD", frozenset({"  "}), frozenset[str](), {})
    )
    assert is_refusal(BookBindingRequirements.try_create("USD", frozenset[str](), "sensor", {}))
    assert is_refusal(
        BookBindingRequirements.try_create("USD", frozenset[str](), frozenset[str](), "ranks")
    )


# --- AC6: a second Book on a netted account needs the shared-flatten signature ---


def test_second_book_on_netted_overlap_without_signature_refuses() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(position_model=PositionModel.NETTING),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=True,
        overlapping_instrument_set=True,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_second_book_on_netted_overlap_with_signature_passes() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(position_model=PositionModel.NETTING),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=True,
        overlapping_instrument_set=True,
        shared_flatten_signature="operator-signed-2026-08-23",
    )
    assert is_ok(result)
    # The signature is an identity field of the binding when it applied.
    assert result.value.shared_flatten_signature == "operator-signed-2026-08-23"


def test_netting_without_overlap_needs_no_signature() -> None:
    result = bind_time_capability_check(
        requirements=_requirements(),
        profile=_profile(position_model=PositionModel.NETTING),
        bms_rank_table=_rank_table(),
        sensor_baselines_present=frozenset({"sqs-eurusd"}),
        live_path_rung_baseline_present=True,
        is_second_book_on_account=True,
        overlapping_instrument_set=False,
    )
    assert is_ok(result)
    # No netted-overlap condition held, so no signature is recorded on the result.
    assert result.value.shared_flatten_signature is None


def test_signature_flows_onto_the_binding_record() -> None:
    capability = _capability_result(
        profile=_profile(position_model=PositionModel.NETTING),
        is_second_book_on_account=True,
        overlapping_instrument_set=True,
        shared_flatten_signature="operator-signed",
    )
    record = _record(capability_check_result=capability)
    assert record.shared_flatten_signature == "operator-signed"
    assert record.fp1_identity()["shared_flatten_signature"] == "operator-signed"


# --- the append-only binding log ---------------------------------------------


def test_log_mints_and_reports_liveness() -> None:
    log = BookBindingLog()
    record = _record(book_instance_id=_book_instance_id("book-inst-A"))
    minted = log.mint(record)
    assert is_ok(minted)
    assert log.is_present(minted.value)
    assert log.is_superseded(minted.value) is False
    live = log.live_binding_for(_book_instance_id("book-inst-A"))
    assert live is not None
    assert live.value == minted.value.value
    assert log.live_binding_for(_book_instance_id("nope")) is None
    assert log.live_binding_for("not-an-id") is None
    assert log.is_present("not-a-fp") is False


def test_log_refuses_non_record() -> None:
    log = BookBindingLog()
    assert is_refusal(log.mint("not-a-record"))


def test_rebinding_with_a_supersedes_edge_swaps_the_bms() -> None:
    log = BookBindingLog()
    book = _book_instance_id("book-inst-A")
    first = _record(book_instance_id=book)
    first_epoch = log.mint(first)
    assert is_ok(first_epoch)
    # Re-bind: a new record that supersedes the prior and carries a different edge, so its
    # fingerprint differs.
    continues = ContinuesPerformanceEdge.try_create(first_epoch.value)
    assert is_ok(continues)
    second = _record(
        book_instance_id=book,
        supersedes=first_epoch.value,
        continues_performance_edge=continues.value,
    )
    second_epoch = log.mint(second)
    assert is_ok(second_epoch)
    assert log.is_superseded(first_epoch.value) is True
    live = log.live_binding_for(book)
    assert live is not None
    assert live.value == second_epoch.value.value


def test_supersedes_must_name_an_existing_current_live_binding() -> None:
    log = BookBindingLog()
    book = _book_instance_id("book-inst-A")
    # Dangling supersedes → unavailable dependency.
    dangling = _record(
        book_instance_id=book,
        supersedes=_fp("never-minted"),
        continues_performance_edge=_continues(_fp("never-minted")),
    )
    result = log.mint(dangling)
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def _continues(fp: Fingerprint) -> ContinuesPerformanceEdge:
    result = ContinuesPerformanceEdge.try_create(fp)
    assert is_ok(result)
    return result.value


def test_supersedes_cannot_cross_book_instances() -> None:
    log = BookBindingLog()
    book_a = _book_instance_id("book-inst-A")
    book_b = _book_instance_id("book-inst-B")
    a_epoch = log.mint(_record(book_instance_id=book_a))
    assert is_ok(a_epoch)
    # book B trying to supersede book A's binding → invalid input.
    crossing = _record(
        book_instance_id=book_b,
        supersedes=a_epoch.value,
        continues_performance_edge=_continues(a_epoch.value),
    )
    result = log.mint(crossing)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_supersedes_cannot_target_an_already_superseded_binding() -> None:
    log = BookBindingLog()
    book = _book_instance_id("book-inst-A")
    first_epoch = log.mint(_record(book_instance_id=book))
    assert is_ok(first_epoch)
    second = _record(
        book_instance_id=book,
        supersedes=first_epoch.value,
        continues_performance_edge=_continues(first_epoch.value),
    )
    second_epoch = log.mint(second)
    assert is_ok(second_epoch)
    # A third re-bind that names the FIRST (already superseded) binding → invalid input.
    third = _record(
        book_instance_id=book,
        supersedes=first_epoch.value,
        pairing_record=_pairing(),
    )
    result = log.mint(third)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_supersedes_must_be_the_current_live_binding() -> None:
    # A supersedes naming a known binding that is not the Book's current live one refuses.
    log = BookBindingLog()
    book = _book_instance_id("book-inst-A")
    other_book = _book_instance_id("book-inst-B")
    a_epoch = log.mint(_record(book_instance_id=book))
    assert is_ok(a_epoch)
    b_epoch = log.mint(_record(book_instance_id=other_book))
    assert is_ok(b_epoch)
    # book A re-bind that (wrongly) names book B's live binding as its supersedes.
    wrong = _record(
        book_instance_id=book,
        supersedes=b_epoch.value,
        continues_performance_edge=_continues(b_epoch.value),
    )
    result = log.mint(wrong)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


# --- pairing record and binding-state vocabulary -----------------------------


def test_pairing_record_builds_and_refuses_bad_parts() -> None:
    assert is_ok(PairingRecord.try_create(_bms_instance_id(), _bms_instance_id(), "acct-demo"))
    assert is_refusal(PairingRecord.try_create("x", _bms_instance_id(), "acct-demo"))
    assert is_refusal(PairingRecord.try_create(_bms_instance_id(), "x", "acct-demo"))
    assert is_refusal(PairingRecord.try_create(_bms_instance_id(), _bms_instance_id(), "  "))


def test_pairing_record_rides_the_binding_identity() -> None:
    record = _record(pairing_record=_pairing())
    assert record.pairing_record is not None
    assert "pairing_record" in record.fp1_identity()


def test_profile_refuses_bad_inputs() -> None:
    # declared_capabilities is a collection, not a bare string.
    assert is_refusal(VenueBindingProfile.try_create("cap", PositionModel.HEDGING, "USD"))
    # a token that is not a non-blank string.
    assert is_refusal(VenueBindingProfile.try_create(frozenset({"  "}), None, "USD"))
    # an unrecognised position model (None is legal — unmeasured).
    assert is_refusal(VenueBindingProfile.try_create(frozenset[str](), "not-a-model", "USD"))
    assert is_ok(VenueBindingProfile.try_create(frozenset[str](), None, "USD"))
    # a blank settlement currency (None is legal — unmeasured).
    assert is_refusal(VenueBindingProfile.try_create(frozenset[str](), None, "  "))
    assert is_ok(VenueBindingProfile.try_create(frozenset[str](), None, None))


def test_record_refuses_bad_optional_fields() -> None:
    common: dict[str, object] = {
        "book_instance_id": _book_instance_id(),
        "bms_instance_id": _bms_instance_id(),
        "venue_id": _VENUE,
        "account_id": _ACCOUNT,
        "world": World.LIVE,
        "book_definition_fingerprint": _book_version(),
        "bms_definition_fingerprint": _bms_version(),
        "state_carry": _state_carry(),
        "capability_check_result": _capability_result(),
    }
    assert is_refusal(BookBindingRecord.try_create(**common, carries_ledger_edge="x"))  # type: ignore[arg-type]
    assert is_refusal(BookBindingRecord.try_create(**common, continues_performance_edge="x"))  # type: ignore[arg-type]
    assert is_refusal(BookBindingRecord.try_create(**common, pairing_record="x"))  # type: ignore[arg-type]
    assert is_refusal(BookBindingRecord.try_create(**common, supersedes="x"))  # type: ignore[arg-type]


def test_binding_state_vocabulary_is_the_three_members() -> None:
    assert {s.value for s in BindingState} == {"live", "paper", "stood-down"}


def test_state_carry_counters_are_the_five() -> None:
    assert {c.value for c in STATE_CARRY_COUNTERS} == {
        "ledger",
        "cycle",
        "budget",
        "bench_counter",
        "exposure",
    }
