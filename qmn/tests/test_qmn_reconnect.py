"""Story 24.8 — reconnect, gap-recover, never resubmit; frontiers stay distinct."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    Ok,
    RefusalCategory,
    Result,
    SecretRef,
    SecretValue,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.venue.commands import SubmissionOutcome, UnknownTrigger
from qmf.venue.connection import AccountBinding, ConnectionManager, venue_writer_id
from qmf.venue.ctrader import SessionRecovery
from qmn.venue import (
    ConformanceDouble,
    ReceiveFrontier,
    ReconnectGapRecovery,
    ReconnectPhase,
    RecoveredObservation,
)

T = TypeVar("T")

_BOOT = "boot-epoch-reconnect-24-8"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue(value: str = "conformance:reconnect-24-8") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-reconnect-1", venue or _venue(), AccountRole.DEMO))


def _cred() -> SecretRef:
    return _ok(SecretRef.try_create("cred-ref-reconnect-24-8"))


class FakeSecretStore:
    def __init__(self) -> None:
        self._values: dict[SecretRef, SecretValue] = {}

    def put(self, ref: SecretRef, token: str = "access-token") -> None:
        self._values[ref] = _ok(SecretValue.try_create(ref, token))

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:
        if ref not in self._values:
            return unpersistable("no such credential")
        return Ok(self._values[ref])

    def atomic_replace(self, ref: SecretRef, new_value: SecretValue, /) -> Result[SecretRef]:
        self._values[ref] = new_value
        return Ok(ref)


class FakeObservationSink:
    def __init__(self) -> None:
        self.emitted: list[object] = []

    def emit(self, observation: object, /) -> SinkResult:
        self.emitted.append(observation)
        return Ok(SinkAck())


class FakeJournalSink:
    def __init__(self) -> None:
        self.appended: list[object] = []

    def append(self, event: object, /) -> SinkResult:
        self.appended.append(event)
        return Ok(SinkAck())


class FakeRecordSink:
    def write(self, record: object, /) -> SinkResult:
        return Ok(SinkAck())


def _double() -> ConformanceDouble:
    client = _ok(ConformanceDouble.try_create(World.LIVE, _venue()))
    _ok(client.open_session(_account(client.venue_id)))
    return client


def test_session_recovery_invariant_never_resubmits() -> None:
    assert SessionRecovery.resubmits_command is False


def test_reconnect_refuses_secret_value() -> None:
    client = _double()
    value = _ok(SecretValue.try_create(_cred(), "plaintext-must-not-cross"))
    refused = _refusal(
        ReconnectGapRecovery.try_create(client=client, credential_ref=value)
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert "reference" in str(refused.context["reason"])


def test_reconnect_gap_replay_persists_before_healthy_and_never_resubmits() -> None:
    client = _double()
    cred = _cred()
    obs = FakeObservationSink()
    journal = FakeJournalSink()
    frontier = ReceiveFrontier(last_seen_execution_id="exec-0")
    recovery = _ok(
        ReconnectGapRecovery.try_create(
            client=client,
            credential_ref=cred,
            receive_frontier=frontier,
            interpretation_cursor_observation_id="cursor-obs-9",
            observation_sink=obs,
            journal_sink=journal,
        )
    )
    assert recovery.resubmits_command is False
    assert recovery.healthy is False

    report = _ok(
        recovery.run(
            recovered=[
                RecoveredObservation(
                    observation_id="fill-1",
                    kind="fill",
                    receive_wall_ns=1_700_000_000_000_000_100,
                    payload={"qty": 1},
                    execution_id="exec-1",
                ),
                {
                    "observation_id": "life-1",
                    "kind": "lifecycle",
                    "receive_wall_ns": 1_700_000_000_000_000_200,
                    "payload": {"state": "filled"},
                    "execution_id": "exec-2",
                },
            ],
            outstanding_command_ids=["cmd-inflight-a", "cmd-inflight-b"],
        )
    )

    assert report.healthy is True
    assert list(report.phases_completed) == [
        ReconnectPhase.AUTHENTICATE,
        ReconnectPhase.VERIFY_CAPABILITIES,
        ReconnectPhase.GAP_REPLAY,
        ReconnectPhase.PERSIST_RECOVERED,
        ReconnectPhase.RECONCILE_OUTSTANDING,
        ReconnectPhase.HEALTHY,
    ]
    assert report.commands_resubmitted == 0
    assert report.credential_ref_id == cred.value
    assert report.interpretation_cursor_observation_id == "cursor-obs-9"
    assert report.receive_frontier["last_seen_execution_id"] == "exec-2"
    assert report.receive_frontier["recorded_count"] == 2
    # Frontiers stay distinct: cursor unchanged while receive frontier advanced.
    assert report.interpretation_cursor_observation_id != report.receive_frontier[
        "last_observation_id"
    ]
    assert len(obs.emitted) == 2
    assert len(journal.appended) == 2
    assert len(report.outstanding_resolutions) == 2
    for item in report.outstanding_resolutions:
        assert item.outcome is SubmissionOutcome.UNKNOWN
        assert item.trigger is UnknownTrigger.DISCONNECT
    assert report.correlation_evidence["frontiers_distinct"] is True
    assert report.correlation_evidence["commands_resubmitted"] == 0


def test_no_gap_reconnect_still_emits_correlation_evidence() -> None:
    client = _double()
    recovery = _ok(
        ReconnectGapRecovery.try_create(
            client=client,
            credential_ref=_cred(),
            interpretation_cursor_observation_id="cursor-a",
        )
    )
    report = _ok(recovery.run(recovered=(), outstanding_command_ids=()))
    assert report.healthy is True
    assert report.correlation_evidence["no_gap"] is True
    assert report.correlation_evidence["gap_had_events"] is False
    assert report.recovered == ()
    assert report.interpretation_cursor_observation_id == "cursor-a"


def test_reconnect_skips_last_seen_execution_and_authenticates_via_connection_manager() -> None:
    venue = _venue()
    account = _account(venue)
    cred = _cred()
    store = FakeSecretStore()
    store.put(cred)
    writer = _ok(venue_writer_id("vps-fra-01", "ctrader-adapter", venue, account, _BOOT))
    cm = _ok(
        ConnectionManager.try_create(
            writer, store, FakeObservationSink(), FakeJournalSink(), FakeRecordSink()
        )
    )
    binding = _ok(AccountBinding.try_create(venue, account, World.LIVE, cred))
    # Pre-open then lose the session so reconnect must re-auth by reference.
    _ok(cm.open_session(binding))
    assert cm.holds_secret(cred) is True

    client = _ok(ConformanceDouble.try_create(World.LIVE, venue))
    _ok(client.open_session(account))
    frontier = ReceiveFrontier(last_seen_execution_id="exec-keep")
    recovery = _ok(
        ReconnectGapRecovery.try_create(
            client=client,
            credential_ref=cred,
            receive_frontier=frontier,
            connection_manager=cm,
            binding=binding,
            observation_sink=FakeObservationSink(),
            journal_sink=FakeJournalSink(),
        )
    )
    recovered_rows: list[dict[str, object]] = [
        {
            "observation_id": "dup",
            "kind": "fill",
            "receive_wall_ns": 10,
            "payload": {},
            "execution_id": "exec-keep",
        },
        {
            "observation_id": "new-fill",
            "kind": "fill",
            "receive_wall_ns": 20,
            "payload": {},
            "execution_id": "exec-new",
        },
    ]
    report = _ok(recovery.run(recovered=recovered_rows))
    assert report.healthy is True
    assert [row["observation_id"] for row in report.recovered] == ["new-fill"]
    assert cm.holds_secret(cred) is True
    assert report.credential_ref_id == cred.value
