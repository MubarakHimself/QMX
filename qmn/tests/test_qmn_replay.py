"""Story 24.8 — TN-21 replay VenueClientPort: no credential, socket, or submit."""

from __future__ import annotations

from typing import TypeVar

import pytest
from qmf.core import (
    Account,
    AccountRole,
    RefusalCategory,
    Result,
    SecretRef,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.venue.commands import Command
from qmn.venue import (
    REPLAY_SUBMIT_REFUSAL_CATEGORY,
    ReplayAdapter,
    VenueClientKind,
    VenueClientPort,
    conformance_measured_facts,
    ctrader_static_declaration,
    replay_command_attempt_refused,
    select_venue_client,
)
from qmn.venue.verify import VenueFactVerifier

T = TypeVar("T")

_WALL_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue(value: str = "venue-ctrader-demo") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-replay-1", venue or _venue(), AccountRole.DEMO))


def _instant(ns: int = _WALL_NS):
    from qmf.core import Instant

    return _ok(Instant.try_create(ns))


def _adapter(*, with_verification: bool = True) -> ReplayAdapter:
    venue = _venue()
    recorded: tuple[dict[str, object], ...] = (
        {
            "kind": "fill",
            "observation_id": "rec-fill-1",
            "payload": {"deal": "d1"},
        },
        {
            "kind": "spot",
            "observation_id": "rec-spot-1",
            "payload": {"bid": 1},
        },
    )
    verification = None
    if with_verification:
        account = _account(venue)
        decl = _ok(ctrader_static_declaration())
        verifier = _ok(VenueFactVerifier.try_create(decl, venue, account))
        wall = _instant()
        bundle = _ok(conformance_measured_facts(received_at=wall))
        verification = _ok(verifier.verify(bundle, received_at=wall))
    return _ok(
        ReplayAdapter.try_create(
            World.REPLAY,
            venue,
            recorded=recorded,
            verification=verification,
        )
    )


def test_selection_binds_replay_kind_for_every_venue() -> None:
    selected = select_venue_client(World.REPLAY, _venue("any-venue"))
    assert is_ok(selected)
    assert selected.value.kind is VenueClientKind.REPLAY


def test_replay_adapter_is_venue_client_port_without_socket_or_credential() -> None:
    client = _adapter()
    assert isinstance(client, VenueClientPort)
    assert client.kind is VenueClientKind.REPLAY
    assert client.world is World.REPLAY
    assert client.socket_opened is False
    assert client.credential_resolved is False


def test_replay_refuses_live_world_and_credential_bind() -> None:
    refused = _refusal(ReplayAdapter.try_create(World.LIVE, _venue()))
    assert refused.category is RefusalCategory.POLICY_REJECTION

    client = _adapter()
    cred = _ok(SecretRef.try_create("cred-ref-rpl24"))
    bind = _refusal(client.bind_credential(cred))
    assert bind.category is RefusalCategory.POLICY_REJECTION
    cm_bind = _refusal(client.bind_connection_manager(object()))
    assert cm_bind.category is RefusalCategory.POLICY_REJECTION


def test_command_attempt_is_typed_policy_refusal_with_no_side_effect() -> None:
    client = _adapter()
    account = _account(client.venue_id)
    _ok(client.open_session(account))
    _ok(client.verify_capabilities())

    command = _ok(
        Command.cancel_order(client.venue_id, account, "replay-session", 1, "order-1")
    )
    submitted = client.submit(command)
    assert is_refusal(submitted)
    assert submitted.category is REPLAY_SUBMIT_REFUSAL_CATEGORY
    assert submitted.category is RefusalCategory.POLICY_REJECTION
    assert client.commands_submitted == 1
    assert client.socket_opened is False
    assert client.credential_resolved is False
    assert replay_command_attempt_refused().category is RefusalCategory.POLICY_REJECTION


def test_observations_surface_injected_recorded_ct20_ct10_rows() -> None:
    client = _adapter()
    account = _account(client.venue_id)
    _ok(client.open_session(account))
    _ok(client.verify_capabilities())
    rows = _ok(client.observations())
    kinds = {row.get("kind") for row in rows}
    assert "capability-profile" in kinds
    assert "fill" in kinds
    assert "spot" in kinds
    reconciled = _ok(client.reconcile())
    assert "replay" in reconciled.detail


def test_replay_reads_recorded_capability_profile_without_injected_verification() -> None:
    venue = _venue()
    client = _ok(
        ReplayAdapter.try_create(
            World.REPLAY,
            venue,
            recorded=[
                {
                    "kind": "capability-profile",
                    "profile": {
                        "verified": True,
                        "static_declaration_present": True,
                        "measured_at_connection": True,
                        "profile_version": 3,
                        "command_sequencer_open": True,
                        "market_data_recordable": True,
                        "proto_tag": 91,
                    },
                }
            ],
        )
    )
    _ok(client.open_session(_account(venue)))
    caps = _ok(client.verify_capabilities())
    assert caps["verified"] is True
    assert caps["profile_version"] == 3
    assert caps["socket_opened"] is False
    assert caps["credential_resolved"] is False


@pytest.mark.live
def test_replay_needs_no_live_token() -> None:
    """Replay stays credential-free; live marker exists only as a negative control."""
    pytest.skip("replay adapter never resolves a Spotware token")
