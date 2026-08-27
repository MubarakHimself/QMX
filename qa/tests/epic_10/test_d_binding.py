"""Epic 10 independent audit — Cluster D (Story 10.4).

The binding chain, the identity trinity, and the bind-time capability check.
Authored from Story 10.4 ACs, CT-28, CT-27, and the R-001 currency gate.

Planned IDs: D1-D11.
"""

from __future__ import annotations

from qmf.core import Fingerprint, Instant, RefusalCategory, VenueId, World, fingerprint, is_ok, is_refusal
from qmf.risk.binding import (
    STATE_CARRY_COUNTERS,
    BmsInstanceId,
    BookBindingLog,
    BookBindingRecord,
    BookBindingRequirements,
    BookInstance,
    BookInstanceId,
    CapabilityCheckResult,
    ContinuesPerformanceEdge,
    PositionModel,
    SignedLedgerEdge,
    StateCarry,
    StateCarryChoice,
    StateCarryCounter,
    VenueBindingProfile,
    bind_time_capability_check,
)
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable

_INSTANT = Instant(value_ns=1_700_000_000_000_000_000)
_VENUE = VenueId(value="venue-ctrader")
_ACCOUNT = "acct-001"


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _book_instance_id(value: str = "book-inst-1") -> BookInstanceId:
    result = BookInstanceId.try_create(value)
    assert is_ok(result)
    return result.value


def _bms_instance_id() -> BmsInstanceId:
    result = BmsInstanceId.derive(_fp("bms-version-1"), _ACCOUNT, _VENUE, World.LIVE)
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


def _requirements(**overrides: object) -> BookBindingRequirements:
    kwargs: dict[str, object] = {
        "accounting_currency": "USD",
        "required_venue_capabilities": frozenset({"protective-stop-attachment"}),
        "required_sensor_ids": frozenset({"sqs-eurusd"}),
        "control_policy_ranks": {},
    }
    kwargs.update(overrides)
    result = BookBindingRequirements.try_create(
        kwargs["accounting_currency"], kwargs["required_venue_capabilities"],
        kwargs["required_sensor_ids"], kwargs["control_policy_ranks"],
    )
    assert is_ok(result)
    return result.value


def _profile(**overrides: object) -> VenueBindingProfile:
    kwargs: dict[str, object] = {
        "declared_capabilities": frozenset({"protective-stop-attachment", "close_all"}),
        "position_model": PositionModel.HEDGING,
        "settlement_currency": "USD",
    }
    kwargs.update(overrides)
    result = VenueBindingProfile.try_create(
        kwargs["declared_capabilities"], kwargs["position_model"], kwargs["settlement_currency"]
    )
    assert is_ok(result)
    return result.value


def _capability(**overrides: object) -> object:
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
    return bind_time_capability_check(**kwargs)  # type: ignore[arg-type]


def _capability_ok(**overrides: object) -> CapabilityCheckResult:
    result = _capability(**overrides)
    assert is_ok(result)
    return result.value


def _record(**overrides: object) -> BookBindingRecord:
    kwargs: dict[str, object] = {
        "book_instance_id": _book_instance_id(),
        "bms_instance_id": _bms_instance_id(),
        "venue_id": _VENUE,
        "account_id": _ACCOUNT,
        "world": World.LIVE,
        "book_definition_fingerprint": _fp("book-version-1"),
        "bms_definition_fingerprint": _fp("bms-version-1"),
        "state_carry": _state_carry(),
        "capability_check_result": _capability_ok(),
    }
    kwargs.update(overrides)
    result = BookBindingRecord.try_create(**kwargs)  # type: ignore[arg-type]
    assert is_ok(result)
    return result.value


# --- D1: the binding tuple has five components and no role --------------------


def test_D1_binding_tuple_is_five_components_without_role() -> None:
    record = _record()
    identity = record.tuple_identity()
    assert set(identity) == {
        "class", "book_instance_id", "bms_instance_id", "venue_id", "account_id", "world",
    }
    assert "role" not in identity
    # It is aligned with the (VenueId, account) command stream.
    assert record.command_stream() == (_VENUE, _ACCOUNT)


# --- D2: the identity trinity ------------------------------------------------


def test_D2_identity_trinity_version_instance_and_epoch() -> None:
    # Book instance is an operator-minted deployment record: two copies of one version
    # on one account are distinct by mint.
    one = BookInstance.try_create(
        _book_instance_id("copy-1"), _fp("book-version-1"), _ACCOUNT, _VENUE, World.LIVE, "mint-a", 0
    )
    two = BookInstance.try_create(
        _book_instance_id("copy-2"), _fp("book-version-1"), _ACCOUNT, _VENUE, World.LIVE, "mint-b", 1
    )
    assert is_ok(one) and is_ok(two)
    assert one.value.fp1_identity() != two.value.fp1_identity()
    # The binding epoch is the record's OWN fingerprint, distinct from the tuple identity.
    record = _record()
    epoch = record.fingerprint()
    assert is_ok(epoch)
    assert record.tuple_identity() != record.fp1_identity()


# --- D3: an equal-fingerprint re-mint -> invalid input, not idempotent --------


def test_D3_equal_fingerprint_rebinding_is_invalid_input() -> None:
    log = BookBindingLog()
    assert is_ok(log.mint(_record()))
    duplicate = _record()  # byte-identical -> equal fingerprint
    result = log.mint(duplicate)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


# --- D4: state_carry is mandatory and complete -------------------------------


def test_D4_state_carry_is_mandatory_and_complete() -> None:
    assert {c.value for c in STATE_CARRY_COUNTERS} == {
        "ledger", "cycle", "budget", "bench_counter", "exposure",
    }
    # A partial declaration (missing counters) is invalid input.
    partial = StateCarry.try_create({StateCarryCounter.LEDGER: StateCarryChoice.RESET})
    assert is_refusal(partial)
    assert partial.category is RefusalCategory.INVALID_INPUT
    # Each counter is carry|reset; a non-mapping / unknown counter / bad choice refuses.
    assert is_refusal(StateCarry.try_create("not-a-mapping"))
    assert is_refusal(StateCarry.try_create({"not-a-counter": "reset"}))


# --- D5: carry is legal only under a signed carries-ledger edge ---------------


def test_D5_carry_requires_a_signed_carries_ledger_edge() -> None:
    carrying = _state_carry(ledger=StateCarryChoice.CARRY)
    without = BookBindingRecord.try_create(
        _book_instance_id(), _bms_instance_id(), _VENUE, _ACCOUNT, World.LIVE,
        _fp("book-version-1"), _fp("bms-version-1"), carrying, _capability_ok(),
    )
    assert is_refusal(without)
    assert without.category is RefusalCategory.INVALID_INPUT
    edge = SignedLedgerEdge.try_create("operator", _INSTANT, _fp("prior-binding"))
    assert is_ok(edge)
    with_edge = _record(state_carry=carrying, carries_ledger_edge=edge.value)
    assert with_edge.carries_ledger_edge is not None


# --- D6: the two lineage edges are never inferred from each other -------------


def test_D6_lineage_edges_are_independent() -> None:
    from qmf.risk.binding import BindingLineageEdgeKind

    edge = SignedLedgerEdge.try_create("operator", _INSTANT, _fp("prior"))
    assert is_ok(edge)
    assert edge.value.fp1_identity()["kind"] == BindingLineageEdgeKind.CARRIES_LEDGER.value
    continues = ContinuesPerformanceEdge.try_create(_fp("prior"))
    assert is_ok(continues)
    assert continues.value.fp1_identity()["kind"] == BindingLineageEdgeKind.CONTINUES_PERFORMANCE.value
    # A continues-performance edge (a track-record claim) NEVER unlocks a carry: a carry
    # still refuses with a continues edge but no signed ledger edge.
    carrying = _state_carry(budget=StateCarryChoice.CARRY)
    refused = BookBindingRecord.try_create(
        _book_instance_id(), _bms_instance_id(), _VENUE, _ACCOUNT, World.LIVE,
        _fp("book-version-1"), _fp("bms-version-1"), carrying, _capability_ok(),
        continues_performance_edge=continues.value,
    )
    assert is_refusal(refused)


# --- D7: the bind-time capability check refuses a shortfall at bind time ------


def test_D7_missing_required_capability_refuses_at_bind_time() -> None:
    result = _capability(
        requirements=_requirements(required_venue_capabilities=frozenset({"guaranteed-stop"})),
        profile=_profile(declared_capabilities=frozenset({"protective-stop-attachment"})),
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- D8 [R-001]: a settlement-currency mismatch -> policy rejection at bind ---


def test_D8_non_usd_settlement_currency_is_policy_rejection() -> None:
    result = _capability(profile=_profile(settlement_currency="EUR"))
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    # A non-USD accounting currency is likewise refused at construction (numeraire law).
    non_usd = BookBindingRequirements.try_create("EUR", frozenset[str](), frozenset[str](), {})
    assert is_refusal(non_usd)
    assert non_usd.category is RefusalCategory.POLICY_REJECTION


# --- D9: a second Book on a netted overlap needs a shared-flatten signature ---


def test_D9_second_book_netted_overlap_needs_shared_flatten_signature() -> None:
    refused = _capability(
        profile=_profile(position_model=PositionModel.NETTING),
        is_second_book_on_account=True, overlapping_instrument_set=True,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    signed = _capability_ok(
        profile=_profile(position_model=PositionModel.NETTING),
        is_second_book_on_account=True, overlapping_instrument_set=True,
        shared_flatten_signature="operator-signed",
    )
    assert signed.shared_flatten_signature == "operator-signed"


# --- D10: a missing SQS / live-path rung baseline -> unavailable dependency ---


def test_D10_missing_baselines_are_unavailable_dependency() -> None:
    no_sensor = _capability(
        requirements=_requirements(required_sensor_ids=frozenset({"sqs-eurusd", "sqs-gbpusd"})),
    )
    assert is_refusal(no_sensor)
    assert no_sensor.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    no_rung = _capability(live_path_rung_baseline_present=False)
    assert is_refusal(no_rung)
    assert no_rung.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# --- D11: a control_policy contradicting the BMS rank table -> unsupported ----


def test_D11_contradicting_rank_table_refuses_at_bind() -> None:
    result = _capability(
        requirements=_requirements(control_policy_ranks={ControlActionKind.FLATTEN: 9}),
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    # An agreeing rank passes.
    assert is_ok(_capability(
        requirements=_requirements(control_policy_ranks={ControlActionKind.FLATTEN: 0}),
    ))
