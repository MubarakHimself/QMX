"""Story 24.8 — shared VenueClientPort contract suite across all three kinds."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

import pytest
from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Instant,
    RefusalCategory,
    Result,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.venue.capabilities import ErrorMap
from qmn.venue import (
    PORT_CONTRACT_CAPABILITY_KEYS,
    ConformanceDouble,
    LiveCTraderClient,
    ReplayAdapter,
    VenueClientKind,
    compare_port_contract_shapes,
    conformance_measured_facts,
    ctrader_static_declaration,
    run_port_contract_suite,
)
from qmn.venue.verify import VenueFactVerifier

T = TypeVar("T")

_BOOT = "boot-epoch-port-24-8"
_WALL_NS = 1_724_000_000 * 1_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _venue(value: str) -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId) -> Account:
    return _ok(Account.try_create("port-acct", venue, AccountRole.DEMO))


def _instant(ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _verification(venue: VenueId, account: Account):
    decl = _ok(ctrader_static_declaration())
    verifier = _ok(VenueFactVerifier.try_create(decl, venue, account))
    bundle = _ok(conformance_measured_facts(received_at=_instant()))
    return _ok(verifier.verify(bundle, received_at=_instant()))


def _double() -> ConformanceDouble:
    venue = _venue("conformance:port-contract")
    return _ok(ConformanceDouble.try_create(World.LIVE, venue))


def _replay() -> ReplayAdapter:
    venue = _venue("venue-ctrader-demo")
    account = _account(venue)
    recorded: list[dict[str, object]] = [
        {"kind": "fill", "observation_id": "r1", "payload": {}}
    ]
    return _ok(
        ReplayAdapter.try_create(
            World.REPLAY,
            venue,
            recorded=recorded,
            verification=_verification(venue, account),
        )
    )


def _live() -> LiveCTraderClient:
    venue = _venue("venue-ctrader-live-port")
    account = _account(venue)
    clock = DataDrivenClock(
        boot_epoch_id=_BOOT,
        wall_instants=tuple(_instant(_WALL_NS + i * 1_000_000) for i in range(16)),
        monotonic_ns=tuple(5_000_000_000 + i * 1_000_000 for i in range(16)),
    )
    client = _ok(
        LiveCTraderClient.try_create(
            World.LIVE,
            venue,
            clock=clock,
            error_map=_ok(ErrorMap.try_create(1, [])),
        )
    )
    _ok(client.accept_verification(_verification(venue, account)))
    return client


def _as_map(result: Mapping[str, object]) -> Mapping[str, object]:
    return result


def test_port_contract_suite_passes_double_and_replay_on_ci_lane() -> None:
    double_shape = _as_map(_ok(run_port_contract_suite(_double())))
    replay_shape = _as_map(_ok(run_port_contract_suite(_replay())))
    assert double_shape["kind"] == VenueClientKind.CONFORMANCE.value
    assert replay_shape["kind"] == VenueClientKind.REPLAY.value
    assert set(cast("list[str]", double_shape["capability_keys"])) == set(
        PORT_CONTRACT_CAPABILITY_KEYS
    )
    assert set(cast("list[str]", replay_shape["capability_keys"])) == set(
        PORT_CONTRACT_CAPABILITY_KEYS
    )
    parity = _as_map(
        _ok(
            compare_port_contract_shapes(
                {
                    VenueClientKind.CONFORMANCE: double_shape,
                    VenueClientKind.REPLAY: replay_shape,
                }
            )
        )
    )
    assert parity["parity"] is True


def test_port_contract_suite_includes_credential_free_live_shape() -> None:
    live_shape = _as_map(_ok(run_port_contract_suite(_live())))
    double_shape = _as_map(_ok(run_port_contract_suite(_double())))
    replay_shape = _as_map(_ok(run_port_contract_suite(_replay())))
    parity = _as_map(
        _ok(
            compare_port_contract_shapes(
                {
                    "conformance": double_shape,
                    "replay": replay_shape,
                    "ctrader": live_shape,
                }
            )
        )
    )
    assert sorted(cast("list[str]", parity["compared"])) == [
        "conformance",
        "ctrader",
        "replay",
    ]
    live_submit = cast("Mapping[str, object]", live_shape["submit_shape"])
    replay_submit = cast("Mapping[str, object]", replay_shape["submit_shape"])
    assert live_submit["form"] == "refusal"
    assert live_submit["category"] == RefusalCategory.UNSUPPORTED_CAPABILITY.value
    assert replay_submit["category"] == RefusalCategory.POLICY_REJECTION.value


def test_capability_or_refusal_divergence_fails_suite() -> None:
    good = dict(_ok(run_port_contract_suite(_double())))
    diverged = dict(good)
    diverged["capability_keys"] = ["verified"]  # missing required keys
    refused = compare_port_contract_shapes({"conformance": diverged, "replay": good})
    assert is_refusal(refused)
    assert refused.context["field"] == "capability_shape"

    submit_diverged = dict(good)
    submit_diverged["submit_shape"] = {
        "form": "refusal",
        "category": RefusalCategory.POLICY_REJECTION.value,
    }
    refused_submit = compare_port_contract_shapes(
        {"conformance": submit_diverged, "replay": good}
    )
    assert is_refusal(refused_submit)
    assert refused_submit.context["field"] == "refusal_shape"


@pytest.mark.live
def test_credentialed_live_port_contract_token_gated() -> None:
    """Credentialed live suite is an explicit token-gated acceptance (TN-23; SC-13)."""
    pytest.skip("Spotware sandbox token not a Story 24.8 CI prerequisite")
