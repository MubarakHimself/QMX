"""Story 25.19 — roster-driven multi-account / multi-broker runtime keys."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    Duration,
    Instrument,
    MonotonicReading,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmn.config import (
    ADDING_BROKER_REQUIRES_CORE_CODE_CHANGE,
    HAS_DEFAULT_VENUE_ACCOUNT_SINGLETON,
    ROSTER_SURFACE,
    STATE_CARRY_COUNTERS,
    AccountBindingDecl,
    BookBindingDecl,
    PositionModelDecl,
    SensingOnlyDecl,
    StateCarryChoice,
    ThrottleScope,
    compose_roster_runtime,
    streams_independent,
    writer_streams_from_composition,
)
from qmn.host import allocate_writer_ids
from qmn.order import AdmissionClass, ConnectionCommandPacer, admission_class_for
from qmn.venue import Command, OrderParameters, OrderType, TimeInForce, VenueClientKind

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _state_carry(**overrides: StateCarryChoice) -> dict[str, StateCarryChoice]:
    body = dict.fromkeys(STATE_CARRY_COUNTERS, StateCarryChoice.RESET)
    body.update(overrides)
    return body


def _book(
    binding_id: str,
    *,
    instruments: frozenset[str],
    attribution: frozenset[str] | None = None,
    shared_flatten: str | None = None,
) -> BookBindingDecl:
    return BookBindingDecl(
        binding_id=binding_id,
        book_definition_fp1=f"fp1:book:{binding_id}",
        instruments=instruments,
        attribution_instruments=attribution,
        shared_flatten_signature=shared_flatten,
    )


def _binding(
    *,
    venue_id: str = "ic-markets",
    account_id: str = "acct-demo-1",
    role: AccountRole = AccountRole.DEMO,
    world: World = World.LIVE,
    environment: str = "demo",
    position_model: PositionModelDecl = PositionModelDecl.HEDGING,
    books: tuple[BookBindingDecl, ...] | None = None,
    throttle_scope: ThrottleScope = ThrottleScope.CONNECTION,
    state_carry: dict[str, StateCarryChoice] | None = None,
    carries_ledger_signature: str | None = None,
    bms_instance_id: str = "bms-1",
) -> AccountBindingDecl:
    if books is None:
        books = (
            _book(
                "book-1",
                instruments=frozenset({"EURUSD"}),
                attribution=(
                    frozenset({"EURUSD"}) if position_model is PositionModelDecl.NETTING else None
                ),
            ),
        )
    return AccountBindingDecl(
        venue_id=venue_id,
        account_id=account_id,
        role=role,
        world=world,
        environment=environment,
        credential_reference="qmx/venue-demo",
        credential_sharing="exclusive",
        bms_definition_fp1="fp1:bms:1",
        bms_instance_id=bms_instance_id,
        book_bindings=books,
        state_carry=_state_carry() if state_carry is None else state_carry,
        throttle_scope=throttle_scope,
        position_model=position_model,
        opaque_metric_id=f"m-{account_id}",
        carries_ledger_signature=carries_ledger_signature,
    )


def test_surface_markers_refuse_singleton_and_core_broker_edit() -> None:
    assert ROSTER_SURFACE == "qmn.config.roster"
    assert HAS_DEFAULT_VENUE_ACCOUNT_SINGLETON is False
    assert ADDING_BROKER_REQUIRES_CORE_CODE_CHANGE is False


def test_compose_keys_by_tuples_and_seals_writer_streams() -> None:
    demo = _binding(account_id="acct-demo-1", venue_id="ic-markets", environment="demo")
    live_broker = _binding(
        account_id="acct-live-2",
        venue_id="pepperstone",
        role=AccountRole.LIVE,
        environment="live",
        books=(_book("book-ps", instruments=frozenset({"GBPUSD"})),),
    )
    composition = _ok(
        compose_roster_runtime(
            account_bindings=(demo, live_broker),
            protective_reserve_capacity=2,
        )
    )
    assert composition.sealed is True
    assert len(composition.command_streams) == 2
    assert len(composition.connections) == 2
    assert {c.token for c in composition.connections} == {
        "ic-markets:demo",
        "pepperstone:live",
    }
    stream_tokens = {p.stream.token for p in composition.command_streams}
    assert stream_tokens == {"ic-markets::acct-demo-1", "pepperstone::acct-live-2"}
    assert len(composition.binding_keys) == 2
    assert all(p.opens_sequencer for p in composition.command_streams)
    assert all(p.carries_pacer_bucket is False for p in composition.command_streams)
    assert all(p.pacer.owned_by_connection for p in composition.command_streams)
    assert all(p.entry_may_consume_reserve is False for p in composition.pacer_buckets)

    # Second broker selected by (world, VenueId) — ctrader kind, no core edit.
    kinds = {s.kind for s in composition.port_selections}
    assert VenueClientKind.CTRADER in kinds
    assert {s.venue_id.value for s in composition.port_selections} == {
        "ic-markets",
        "pepperstone",
    }

    writer_streams = _ok(writer_streams_from_composition(composition))
    allocation = _ok(
        allocate_writer_ids(
            machine="vps-a",
            boot_epoch_id="boot-roster-25-19",
            streams=writer_streams,
        )
    )
    assert allocation.pairwise_distinct() is True
    assert len(allocation.allocated) == 6  # 2 streams x (command+adapter+risk)


def test_sensing_only_is_legal_compiled_state_without_sequencer() -> None:
    sensing = SensingOnlyDecl(
        venue_id="ic-markets",
        environment="live",
        account_id="acct-live-sense",
        credential_reference="qmx/venue-live",
        opaque_metric_id="m-sense",
    )
    demo = _binding()
    composition = _ok(
        compose_roster_runtime(
            account_bindings=(demo,),
            sensing_only=(sensing,),
            protective_reserve_capacity=1,
        )
    )
    assert len(composition.sensing_plans) == 1
    plan = composition.sensing_plans[0]
    assert plan.opens_sequencer is False
    assert plan.has_book_binding is False
    assert plan.has_bms_instance is False
    assert plan.has_command_stream is False
    assert plan.resolves_execution_target is False
    assert plan.admits_promotion is False
    assert plan.admits_live_intent is False
    assert plan.may_record_observations is True
    assert plan.may_serve_observations is True
    # Sensing-only connection is present; no command stream WriterId for it.
    assert any(c.token == "ic-markets:live" for c in composition.connections)
    writer_streams = _ok(writer_streams_from_composition(composition))
    assert all("acct-live-sense" not in stream for _role, stream in writer_streams)


def test_sensing_only_refuses_smuggled_book_or_bms_fields() -> None:
    smuggled: dict[str, object] = {
        "venue_id": "ic-markets",
        "environment": "live",
        "account_id": "acct-x",
        "credential_reference": "qmx/venue-live",
        "opaque_metric_id": "m-x",
        "book_bindings": [],
    }
    refused = _refusal(
        compose_roster_runtime(
            sensing_only=(smuggled,),
            protective_reserve_capacity=1,
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "sensing_only"


def test_netting_attribution_partition_and_shared_flatten() -> None:
    # Missing attribution on netting → policy rejection.
    missing = _refusal(
        compose_roster_runtime(
            account_bindings=(
                _binding(
                    position_model=PositionModelDecl.NETTING,
                    books=(_book("b1", instruments=frozenset({"EURUSD"})),),
                ),
            ),
            protective_reserve_capacity=1,
        )
    )
    assert missing.category is RefusalCategory.POLICY_REJECTION
    assert missing.context["field"] == "attribution_instruments"

    # Overlap → invalid input at compose.
    overlap = _refusal(
        compose_roster_runtime(
            account_bindings=(
                _binding(
                    position_model=PositionModelDecl.NETTING,
                    books=(
                        _book(
                            "b1",
                            instruments=frozenset({"EURUSD", "GBPUSD"}),
                            attribution=frozenset({"EURUSD"}),
                            shared_flatten="sig-shared",
                        ),
                        _book(
                            "b2",
                            instruments=frozenset({"EURUSD", "USDJPY"}),
                            attribution=frozenset({"EURUSD"}),
                            shared_flatten="sig-shared",
                        ),
                    ),
                ),
            ),
            protective_reserve_capacity=1,
        )
    )
    assert overlap.category is RefusalCategory.INVALID_INPUT
    assert "disjoint" in str(overlap.context["reason"])

    # Gap (not exhaustive) → invalid input.
    gap = _refusal(
        compose_roster_runtime(
            account_bindings=(
                _binding(
                    position_model=PositionModelDecl.NETTING,
                    books=(
                        _book(
                            "b1",
                            instruments=frozenset({"EURUSD", "GBPUSD"}),
                            attribution=frozenset({"EURUSD"}),
                        ),
                    ),
                ),
            ),
            protective_reserve_capacity=1,
        )
    )
    assert gap.category is RefusalCategory.INVALID_INPUT
    assert "exhaustive" in str(gap.context["reason"])

    # Second Book overlapping without shared-flatten → unsupported capability.
    no_sig = _refusal(
        compose_roster_runtime(
            account_bindings=(
                _binding(
                    position_model=PositionModelDecl.NETTING,
                    books=(
                        _book(
                            "b1",
                            instruments=frozenset({"EURUSD", "GBPUSD"}),
                            attribution=frozenset({"EURUSD"}),
                        ),
                        _book(
                            "b2",
                            instruments=frozenset({"EURUSD", "USDJPY"}),
                            attribution=frozenset({"USDJPY"}),
                        ),
                    ),
                ),
            ),
            protective_reserve_capacity=1,
        )
    )
    assert no_sig.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert no_sig.context["field"] == "shared_flatten_signature"

    # Valid partition with shared-flatten on overlap.
    ok = _ok(
        compose_roster_runtime(
            account_bindings=(
                _binding(
                    position_model=PositionModelDecl.NETTING,
                    books=(
                        _book(
                            "b1",
                            instruments=frozenset({"EURUSD"}),
                            attribution=frozenset({"EURUSD"}),
                            shared_flatten="sig-a",
                        ),
                        _book(
                            "b2",
                            instruments=frozenset({"GBPUSD"}),
                            attribution=frozenset({"GBPUSD"}),
                            shared_flatten="sig-a",
                        ),
                    ),
                ),
            ),
            protective_reserve_capacity=1,
        )
    )
    assert len(ok.binding_keys) == 2


def _params(venue: VenueId) -> OrderParameters:
    instrument = _ok(Instrument.try_create(venue, "EURUSD"))
    qty = _ok(Quantity.try_create(100, "lot", 2))
    delta = _ok(PriceDelta.try_create(100, instrument, 5))
    return _ok(
        OrderParameters.try_create(
            OrderType.MARKET,
            TimeInForce.GOOD_TILL_CANCEL,
            qty,
            protective_stop_distance=delta,
        )
    )


def test_protective_reserve_isolated_per_connection_from_entry() -> None:
    composition = _ok(
        compose_roster_runtime(
            account_bindings=(
                _binding(account_id="a1", venue_id="ic-markets", environment="demo"),
                _binding(account_id="a2", venue_id="ic-markets", environment="demo"),
            ),
            protective_reserve_capacity=2,
        )
    )
    # Both streams share one connection pacer plan; streams do not own buckets.
    assert len(composition.pacer_buckets) == 1
    bucket = composition.pacer_buckets[0]
    assert bucket.connection.token == "ic-markets:demo"
    assert bucket.protective_reserve_capacity == 2
    assert bucket.entry_may_consume_reserve is False
    assert all(p.carries_pacer_bucket is False for p in composition.command_streams)
    assert all(
        p.pacer is bucket or p.pacer.connection.token == bucket.connection.token
        for p in composition.command_streams
    )

    pacer = _ok(
        ConnectionCommandPacer.try_create(
            local_queue_bound=_ok(Duration.try_create(50_000_000)),
            protective_reserve_capacity=bucket.protective_reserve_capacity,
            general_capacity=1,
        )
    )
    venue = _ok(VenueId.try_create("ic-markets"))
    account = _ok(Account.try_create("a1", venue, AccountRole.DEMO))
    entry = _ok(Command.place_order(venue, account, "session-r", 1, _params(venue)))
    protect = _ok(Command.cancel_order(venue, account, "session-r", 2, "ord-1"))
    assert _ok(admission_class_for(entry)) is AdmissionClass.ENTRY
    assert _ok(admission_class_for(protect)) is AdmissionClass.PROTECTIVE

    _ok(pacer.enqueue(protect))
    admitted = _ok(
        pacer.admit(
            protect,
            enqueued_at=_ok(MonotonicReading.try_create(1_000, "boot-r")),
            now=_ok(MonotonicReading.try_create(2_000, "boot-r")),
        )
    )
    assert admitted.admission_class is AdmissionClass.PROTECTIVE

    _ok(pacer.enqueue(protect))
    _ok(pacer.enqueue(entry))
    reserved = _ok(
        pacer.admit(
            protect,
            enqueued_at=_ok(MonotonicReading.try_create(3_000, "boot-r")),
            now=_ok(MonotonicReading.try_create(4_000, "boot-r")),
        )
    )
    assert reserved.used_protective_reserve is True
    refused_reserve = _refusal(
        pacer.admit(
            entry,
            enqueued_at=_ok(MonotonicReading.try_create(5_000, "boot-r")),
            now=_ok(MonotonicReading.try_create(6_000, "boot-r")),
        )
    )
    assert refused_reserve.context["field"] == "protective_reserve_capacity"


def test_one_stream_unknown_does_not_freeze_another() -> None:
    composition = _ok(
        compose_roster_runtime(
            account_bindings=(
                _binding(account_id="acct-a", venue_id="ic-markets"),
                _binding(account_id="acct-b", venue_id="ic-markets"),
            ),
            protective_reserve_capacity=1,
        )
    )
    left, right = composition.command_streams
    assert _ok(streams_independent(left, right)) is True
    assert _ok(streams_independent(left, left)) is False
    # Distinct UNKNOWN scopes by construction of stream tokens.
    assert left.stream.token != right.stream.token
    assert left.has_unknown_block is True
    assert right.has_unknown_block is True


def test_empty_roster_and_blank_reserve_refuse() -> None:
    empty = _refusal(
        compose_roster_runtime(account_bindings=(), sensing_only=(), protective_reserve_capacity=1)
    )
    assert empty.category is RefusalCategory.INVALID_INPUT
    blank = _refusal(
        compose_roster_runtime(account_bindings=(_binding(),), protective_reserve_capacity=-1)
    )
    assert blank.context["field"] == "protective_reserve_capacity"


def test_mapping_form_compose_and_fingerprint_stable() -> None:
    first = _ok(
        compose_roster_runtime(
            account_bindings=(
                {
                    "venue_id": "ic-markets",
                    "account_id": "acct-1",
                    "role": "demo",
                    "world": "live",
                    "environment": "demo",
                    "credential_reference": "qmx/venue-demo",
                    "credential_sharing": "exclusive",
                    "bms_definition_fp1": "fp1:bms:1",
                    "bms_instance_id": "bms-1",
                    "book_bindings": [
                        {
                            "binding_id": "book-1",
                            "book_definition_fp1": "fp1:book:1",
                            "instruments": ["EURUSD"],
                        }
                    ],
                    "state_carry": dict.fromkeys(STATE_CARRY_COUNTERS, "reset"),
                    "throttle_scope": "connection",
                    "position_model": "hedging",
                    "opaque_metric_id": "m-1",
                },
            ),
            sensing_only=(
                {
                    "venue_id": "ic-markets",
                    "environment": "live",
                    "account_id": "acct-sense",
                    "credential_reference": "qmx/venue-live",
                    "opaque_metric_id": "m-sense",
                },
            ),
            protective_reserve_capacity=3,
        )
    )
    second = _ok(
        compose_roster_runtime(
            account_bindings=(
                {
                    "venue_id": "ic-markets",
                    "account_id": "acct-1",
                    "role": "demo",
                    "world": "live",
                    "environment": "demo",
                    "credential_reference": "qmx/venue-demo",
                    "credential_sharing": "exclusive",
                    "bms_definition_fp1": "fp1:bms:1",
                    "bms_instance_id": "bms-1",
                    "book_bindings": [
                        {
                            "binding_id": "book-1",
                            "book_definition_fp1": "fp1:book:1",
                            "instruments": ["EURUSD"],
                        }
                    ],
                    "state_carry": dict.fromkeys(STATE_CARRY_COUNTERS, "reset"),
                    "throttle_scope": "connection",
                    "position_model": "hedging",
                    "opaque_metric_id": "m-1",
                },
            ),
            sensing_only=(
                {
                    "venue_id": "ic-markets",
                    "environment": "live",
                    "account_id": "acct-sense",
                    "credential_reference": "qmx/venue-live",
                    "opaque_metric_id": "m-sense",
                },
            ),
            protective_reserve_capacity=3,
        )
    )
    assert first.composition_fp == second.composition_fp
    assert first.identity() == second.identity()
