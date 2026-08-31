"""FEAT-0023 conformance double and deterministic suite (Story 24.1)."""

from __future__ import annotations

import pytest
from qmf.core import Account, AccountRole, VenueId, World, is_ok, is_refusal
from qmf.venue.commands import SubmissionOutcome, UnknownTrigger
from qmn.venue import (
    CONFORMANCE_CASES,
    ConformanceCase,
    ConformanceDouble,
    VenueClientKind,
    compound_command_acceptance_blocked,
    run_conformance_suite,
    select_venue_client,
)


def _venue(value: str = "conformance:ctrader-demo") -> VenueId:
    result = VenueId.try_create(value)
    assert is_ok(result)
    return result.value


def test_selection_by_world_and_venue_id() -> None:
    live = select_venue_client(World.LIVE, _venue("venue-ctrader-demo"))
    assert is_ok(live)
    assert live.value.kind is VenueClientKind.CTRADER

    conf = select_venue_client(World.LIVE, _venue("conformance:ctrader-demo"))
    assert is_ok(conf)
    assert conf.value.kind is VenueClientKind.CONFORMANCE

    replay = select_venue_client(World.REPLAY, _venue("venue-ctrader-demo"))
    assert is_ok(replay)
    assert replay.value.kind is VenueClientKind.REPLAY


def test_compound_command_acceptance_blocked_until_ftr02() -> None:
    refusal = compound_command_acceptance_blocked()
    assert is_refusal(refusal)
    assert refusal.context["ftr"] == "FTR-02"


def test_conformance_suite_covers_all_cases_without_network() -> None:
    built = ConformanceDouble.try_create(World.LIVE, _venue())
    assert is_ok(built)
    suite = run_conformance_suite(built.value)
    assert is_ok(suite)
    results = suite.value
    assert results["compound_command"] == "blocked-ftr02"
    for case in CONFORMANCE_CASES:
        assert case.value in results


def test_unknown_triggers_are_distinct() -> None:
    built = ConformanceDouble.try_create(World.LIVE, _venue())
    assert is_ok(built)
    client = built.value
    account = Account.try_create("a1", client.venue_id, AccountRole.DEMO)
    assert is_ok(account)
    assert is_ok(client.open_session(account.value))
    assert is_ok(client.verify_capabilities())

    expected = {
        ConformanceCase.TIMEOUT: UnknownTrigger.TIMEOUT,
        ConformanceCase.TRANSPORT_ERROR: UnknownTrigger.TRANSPORT_ERROR,
        ConformanceCase.DISCONNECT: UnknownTrigger.DISCONNECT,
    }
    from qmf.venue.commands import Command

    for case, trigger in expected.items():
        assert is_ok(client.arm(case))
        command = Command.cancel_order(client.venue_id, account.value, "ep", 1, f"sub-{case.value}")
        assert is_ok(command)
        submitted = client.submit(command.value)
        assert is_ok(submitted)
        assert submitted.value.outcome is SubmissionOutcome.UNKNOWN
        assert submitted.value.observation.unknown_trigger is trigger


def test_netting_and_hedging_arm_position_model() -> None:
    built = ConformanceDouble.try_create(World.LIVE, _venue())
    assert is_ok(built)
    client = built.value
    account = Account.try_create("a1", client.venue_id, AccountRole.DEMO)
    assert is_ok(account)
    assert is_ok(client.open_session(account.value))

    assert is_ok(client.arm(ConformanceCase.HEDGING))
    caps = client.verify_capabilities()
    assert is_ok(caps)
    assert caps.value["position_model"] == "hedging"

    assert is_ok(client.arm(ConformanceCase.NETTING))
    caps = client.verify_capabilities()
    assert is_ok(caps)
    assert caps.value["position_model"] == "netting"


@pytest.mark.live
def test_live_transport_smoke_separately_tagged() -> None:
    """Live smoke is separately tagged and is not this story's credential-free gate."""
    pytest.skip("Spotware sandbox token not a Story 24.1 prerequisite")
