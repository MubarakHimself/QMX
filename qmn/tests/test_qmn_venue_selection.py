"""Story 31.1 — fail-closed live selection by roster VenueClientKind."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    AccountRole,
    RefusalCategory,
    Result,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmn.config import (
    STATE_CARRY_COUNTERS,
    AccountBindingDecl,
    BookBindingDecl,
    PositionModelDecl,
    SensingOnlyDecl,
    StateCarryChoice,
    ThrottleScope,
    compose_roster_runtime,
)
from qmn.venue import VenueClientKind, select_venue_client
from qmn.venue.conformance import ConformanceDouble

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _venue(value: str) -> VenueId:
    return _ok(VenueId.try_create(value))


def _book() -> BookBindingDecl:
    return BookBindingDecl(
        binding_id="book-1",
        book_definition_fp1="fp1:book:1",
        instruments=frozenset({"EURUSD"}),
    )


def _state_carry() -> dict[str, StateCarryChoice]:
    return dict.fromkeys(STATE_CARRY_COUNTERS, StateCarryChoice.RESET)


def _binding(
    *, venue_client_kind: str | VenueClientKind | None = VenueClientKind.CTRADER
) -> AccountBindingDecl:
    return AccountBindingDecl(
        venue_id="ic-markets",
        account_id="acct-demo-1",
        role=AccountRole.DEMO,
        world=World.LIVE,
        environment="demo",
        credential_reference="qmx/venue-demo",
        credential_sharing="exclusive",
        bms_definition_fp1="fp1:bms:1",
        bms_instance_id="bms-1",
        book_bindings=(_book(),),
        state_carry=_state_carry(),
        throttle_scope=ThrottleScope.CONNECTION,
        position_model=PositionModelDecl.HEDGING,
        opaque_metric_id="m-1",
        venue_client_kind=venue_client_kind,
    )


def test_venue_client_kind_enum_is_exactly_three_members() -> None:
    assert tuple(member.value for member in VenueClientKind) == (
        "ctrader",
        "replay",
        "conformance",
    )


def test_replay_world_selects_replay_for_any_venue_id() -> None:
    selected = _ok(select_venue_client(World.REPLAY, _venue("venue-ctrader-demo")))
    assert selected.kind is VenueClientKind.REPLAY
    other = _ok(select_venue_client(World.REPLAY, _venue("pepperstone")))
    assert other.kind is VenueClientKind.REPLAY
    prefixed = _ok(select_venue_client(World.REPLAY, _venue("conformance:ctrader-demo")))
    assert prefixed.kind is VenueClientKind.REPLAY


def test_replay_refuses_ctrader_and_conformance_roster_kind() -> None:
    ctrader = _refusal(
        select_venue_client(
            World.REPLAY,
            _venue("venue-ctrader-demo"),
            VenueClientKind.CTRADER,
        )
    )
    assert ctrader.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert ctrader.context["field"] == "venue_client_kind"
    assert ctrader.context["given"] == "ctrader"

    conformance = _refusal(
        select_venue_client(
            World.REPLAY,
            _venue("conformance:ctrader-demo"),
            "conformance",
        )
    )
    assert conformance.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert conformance.context["field"] == "venue_client_kind"
    assert conformance.context["given"] == "conformance"

    bound = _refusal(ConformanceDouble.try_create(World.REPLAY, _venue("conformance:x")))
    assert bound.category is RefusalCategory.POLICY_REJECTION


def test_simulated_world_is_unsupported_and_constructs_no_client() -> None:
    refused = _refusal(select_venue_client(World.SIMULATED, _venue("venue-ctrader-demo")))
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["field"] == "world"
    with_kind = _refusal(
        select_venue_client(
            World.SIMULATED,
            _venue("venue-ctrader-demo"),
            VenueClientKind.CTRADER,
        )
    )
    assert with_kind.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert with_kind.context["field"] == "world"


def test_live_explicit_ctrader_kind_selects_ctrader() -> None:
    selected = _ok(
        select_venue_client(
            World.LIVE,
            _venue("ic-markets"),
            VenueClientKind.CTRADER,
        )
    )
    assert selected.kind is VenueClientKind.CTRADER
    by_token = _ok(select_venue_client(World.LIVE, _venue("pepperstone"), "ctrader"))
    assert by_token.kind is VenueClientKind.CTRADER


def test_live_conformance_kind_or_prefix_selects_conformance() -> None:
    by_kind = _ok(
        select_venue_client(
            World.LIVE,
            _venue("credential-free-double"),
            VenueClientKind.CONFORMANCE,
        )
    )
    assert by_kind.kind is VenueClientKind.CONFORMANCE
    by_prefix = _ok(select_venue_client(World.LIVE, _venue("conformance:ctrader-demo")))
    assert by_prefix.kind is VenueClientKind.CONFORMANCE
    both = _ok(
        select_venue_client(
            World.LIVE,
            _venue("conformance:ctrader-demo"),
            "conformance",
        )
    )
    assert both.kind is VenueClientKind.CONFORMANCE


def test_live_absent_empty_unknown_kind_is_unsupported_naming_field_and_given() -> None:
    absent = _refusal(select_venue_client(World.LIVE, _venue("venue-ctrader-demo")))
    assert absent.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert absent.context["field"] == "venue_client_kind"
    assert absent.context["given"] is None
    assert absent.context["venue_id"] == "venue-ctrader-demo"

    empty = _refusal(select_venue_client(World.LIVE, _venue("ic-markets"), ""))
    assert empty.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert empty.context["field"] == "venue_client_kind"
    assert empty.context["given"] == ""

    unknown = _refusal(select_venue_client(World.LIVE, _venue("ic-markets"), "mt5"))
    assert unknown.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert unknown.context["field"] == "venue_client_kind"
    assert unknown.context["given"] == "mt5"

    replay_kind = _refusal(
        select_venue_client(World.LIVE, _venue("ic-markets"), VenueClientKind.REPLAY)
    )
    assert replay_kind.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert replay_kind.context["given"] == "replay"


def test_live_broker_spelling_without_ctrader_kind_is_unsupported() -> None:
    refused = _refusal(select_venue_client(World.LIVE, _venue("pepperstone-ctrader")))
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["field"] == "venue_client_kind"
    selected = _ok(
        select_venue_client(
            World.LIVE,
            _venue("pepperstone-ctrader"),
            VenueClientKind.CTRADER,
        )
    )
    assert selected.kind is VenueClientKind.CTRADER


def test_roster_live_binding_passes_explicit_kind() -> None:
    composition = _ok(
        compose_roster_runtime(
            account_bindings=(_binding(),),
            protective_reserve_capacity=1,
        )
    )
    assert {s.kind for s in composition.port_selections} == {VenueClientKind.CTRADER}


def test_roster_live_binding_without_kind_is_unsupported() -> None:
    refused = _refusal(
        compose_roster_runtime(
            account_bindings=(_binding(venue_client_kind=None),),
            protective_reserve_capacity=1,
        )
    )
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["field"] == "venue_client_kind"
    assert refused.context["given"] is None


def test_roster_live_binding_unknown_kind_names_field_and_given() -> None:
    refused = _refusal(
        compose_roster_runtime(
            account_bindings=(_binding(venue_client_kind="mt5"),),
            protective_reserve_capacity=1,
        )
    )
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert refused.context["field"] == "venue_client_kind"
    assert refused.context["given"] == "mt5"


def test_roster_sensing_only_passes_explicit_kind() -> None:
    composition = _ok(
        compose_roster_runtime(
            sensing_only=(
                SensingOnlyDecl(
                    venue_id="ic-markets",
                    environment="live",
                    account_id="acct-live-sense",
                    credential_reference="qmx/venue-live",
                    opaque_metric_id="m-sense",
                    venue_client_kind=VenueClientKind.CTRADER,
                ),
            ),
            protective_reserve_capacity=1,
        )
    )
    assert composition.sensing_plans[0].port_selection.kind is VenueClientKind.CTRADER
