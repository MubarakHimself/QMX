"""Story 42.3 — durable-clock and fold-contract enforcement (FR-Q25)."""

from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

from qma.daemon import AuthoritativeJournal, DaemonClock, PersistenceSubstrate
from qma.daemon.journal import (
    DEFINITION_STORE_MEMBERS,
    FILTERED_PROJECTIONS_NOT_FOLDS,
    V1_FOLD_IDS,
    FoldContractRegistry,
    refuse_host_local_time,
    refuse_worker_evidence_timestamp,
    v1_fold_contract,
)
from qmf.core import (
    DataDrivenClock,
    Duration,
    Instant,
    RefusalCategory,
    fingerprint,
    is_ok,
    is_refusal,
)


def _test_clock(*, boot: str = "boot-clock", n: int = 128) -> DataDrivenClock:
    base = 1_710_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i * 10) for i in range(n))
    monos = tuple(i * 1_000 for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=monos)


def _open_journal(
    tmp_path: Path, *, boot: str = "boot-clock", clock: DataDrivenClock | None = None
) -> tuple[PersistenceSubstrate, AuthoritativeJournal, DaemonClock]:
    substrate_result = PersistenceSubstrate.open(
        tmp_path, machine="test-host", boot_epoch_id=boot
    )
    assert is_ok(substrate_result), substrate_result
    substrate = substrate_result.value
    injected = clock if clock is not None else _test_clock(boot=boot)
    journal_result = AuthoritativeJournal.bind(substrate, clock=injected)
    assert is_ok(journal_result), journal_result
    journal = journal_result.value
    return substrate, journal, journal.clock


def test_durable_append_stamps_occurred_at_and_recorded_at(tmp_path: Path) -> None:
    substrate, journal, _clock = _open_journal(tmp_path)
    try:
        result = journal.append_event(
            "mission.updated",
            scope_path=[{"kind": "desk", "id": "research"}],
            payload={"n": 1},
        )
        assert is_ok(result)
        record = result.value.record
        assert isinstance(record.occurred_at, int)
        assert isinstance(record.recorded_at, int)
        assert record.occurred_at == record.recorded_at
        assert record.journal_seq == 1

        rows = journal.read_all()
        assert is_ok(rows)
        row = rows.value[0]
        assert row["occurred_at"] == record.occurred_at
        assert row["recorded_at"] == record.recorded_at
        assert row["journal_seq"] == 1
    finally:
        journal.close()
        substrate.close()


def test_evidence_stamp_includes_journal_seq_when_announcement_bound(
    tmp_path: Path,
) -> None:
    substrate, journal, clock = _open_journal(tmp_path)
    try:
        stamped = clock.stamp_evidence_record(
            {"entry": "done"},
            journal_seq=7,
            announcement_bound=True,
        )
        assert is_ok(stamped)
        assert stamped.value["occurred_at"] == stamped.value["recorded_at"]
        assert stamped.value["journal_seq"] == 7
        assert stamped.value["entry"] == "done"
    finally:
        journal.close()
        substrate.close()


def test_telemetry_stamp_omits_journal_seq(tmp_path: Path) -> None:
    substrate, journal, clock = _open_journal(tmp_path)
    try:
        stamped = clock.stamp_evidence_record(
            {"metric": "latency"},
            announcement_bound=False,
        )
        assert is_ok(stamped)
        assert "journal_seq" not in stamped.value
        assert "occurred_at" in stamped.value
        assert "recorded_at" in stamped.value
    finally:
        journal.close()
        substrate.close()


def test_worker_authored_evidence_timestamp_refused(tmp_path: Path) -> None:
    substrate, journal, _clock = _open_journal(tmp_path)
    try:
        refused = journal.append_event(
            "task.completed",
            worker_authored_timestamp=1_700_000_000_000_000_000,
        )
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert "worker" in str(refused.context.get("reason", "")).lower()

        fp = fingerprint({"x": 1})
        assert is_ok(fp)
        announced = journal.announce_evidence_append(
            "task_ledger",
            fp.value,
            worker_authored_timestamp={"occurred_at": 1},
        )
        assert is_refusal(announced)

        stamped = journal.stamp_evidence_record(
            {"occurred_at": 99, "body": True},
            journal_seq=1,
        )
        assert is_refusal(stamped)

        direct = refuse_worker_evidence_timestamp(attempted="worker-now")
        assert is_refusal(direct)
    finally:
        journal.close()
        substrate.close()


def test_host_local_time_read_refused() -> None:
    refused = refuse_host_local_time(attempted="datetime.now")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert "host local" in str(refused.context.get("reason", "")).lower()


def test_wall_clock_policy_requires_explicit_iana_zone(tmp_path: Path) -> None:
    substrate, journal, clock = _open_journal(tmp_path)
    try:
        ok = clock.wall_clock_policy("quiet_hours", "America/New_York")
        assert is_ok(ok)
        assert ok.value.iana_zone == "America/New_York"
        zone = ok.value.resolve_zone()
        assert is_ok(zone)
        assert isinstance(zone.value, ZoneInfo)

        evaluated = clock.evaluate_wall_clock_policy(ok.value)
        assert is_ok(evaluated)
        resolved_zone, instant = evaluated.value
        assert resolved_zone.key == "America/New_York"
        assert isinstance(instant, Instant)

        missing = clock.wall_clock_policy("quiet_hours", "")
        assert is_refusal(missing)
        bad_zone = clock.wall_clock_policy("routine_cron", "Not/A_Zone")
        assert is_refusal(bad_zone)
        bad_kind = clock.wall_clock_policy("host_local", "UTC")
        assert is_refusal(bad_kind)
    finally:
        journal.close()
        substrate.close()


def test_duration_policy_is_span_from_recorded_utc_instant(tmp_path: Path) -> None:
    substrate, journal, clock = _open_journal(tmp_path)
    try:
        recorded = 1_710_000_000_000_000_000
        policy = clock.duration_policy(
            "ask_timeout",
            5_000_000_000,
            from_recorded_at=recorded,
        )
        assert is_ok(policy)
        assert policy.value.from_recorded_at == recorded
        assert isinstance(policy.value.span, Duration)
        # Duration policies carry no timezone attribute.
        assert not hasattr(policy.value, "iana_zone")

        deadline = policy.value.deadline()
        assert is_ok(deadline)
        assert deadline.value.value_ns == recorded + 5_000_000_000
    finally:
        journal.close()
        substrate.close()


def test_v1_fold_contracts_declare_four_elements() -> None:
    assert "desk_ledger_views" in V1_FOLD_IDS
    assert "task_state" in V1_FOLD_IDS
    assert "mission_state" in V1_FOLD_IDS
    assert "session_state" in V1_FOLD_IDS
    assert "agent_state" in V1_FOLD_IDS
    assert "mailbox_delivery_state" in V1_FOLD_IDS
    assert "deployment_provider_health" in V1_FOLD_IDS
    assert "staging_application_state" in V1_FOLD_IDS
    for member in DEFINITION_STORE_MEMBERS:
        assert member in V1_FOLD_IDS

    desk = v1_fold_contract("desk_ledger_views")
    assert desk is not None
    assert desk.source_stream == "ledger.appended"
    assert desk.ordering_key == "journal_seq"
    assert desk.knowledge_time_bound == "as_of_recorded_at"
    assert desk.equal_instant_disposition == "ascending_journal_seq"

    registry = FoldContractRegistry()
    registered = registry.register_all_v1()
    assert set(registered) == V1_FOLD_IDS
    for fold_id, contract in registered.items():
        assert contract.fold_id == fold_id
        assert contract.source_stream
        assert contract.ordering_key == "journal_seq"
        assert contract.knowledge_time_bound == "as_of_recorded_at"
        assert contract.equal_instant_disposition == "ascending_journal_seq"


def test_new_fold_refused_without_spine_amendment(tmp_path: Path) -> None:
    substrate, journal, _clock = _open_journal(tmp_path)
    try:
        refused = journal.register_fold("shadow_risk_fold")
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        reason = str(refused.context.get("reason", "")).lower()
        assert "spine amendment" in reason or "v1 fold" in reason

        for name in FILTERED_PROJECTIONS_NOT_FOLDS:
            not_fold = journal.register_fold(name)
            assert is_refusal(not_fold)
    finally:
        journal.close()
        substrate.close()


def test_fold_store_declaration_carries_source_stream_and_stays_unmaterialized(
    tmp_path: Path,
) -> None:
    substrate, journal, _clock = _open_journal(tmp_path)
    try:
        declared = journal.declare_store("desk_ledger_views")
        assert is_ok(declared)
        assert declared.value.materialized is False
        meta = declared.value.fold_metadata
        assert meta.source_stream == "ledger.appended"
        assert meta.ordering_key == "journal_seq"
        assert meta.knowledge_time_bound == "as_of_recorded_at"
        assert meta.equal_instant_disposition == "ascending_journal_seq"

        # Filtered projections are not folds — no source_stream.
        quarantine = journal.declare_store("ledger_quarantine_stream")
        assert is_ok(quarantine)
        assert quarantine.value.fold_metadata.source_stream is None
        assert quarantine.value.materialized is False

        fold = journal.register_fold("desk_ledger_views")
        assert is_ok(fold)
        assert fold.value.source_stream == "ledger.appended"
    finally:
        journal.close()
        substrate.close()


def test_announcement_bound_record_carries_journal_seq_with_stamps(
    tmp_path: Path,
) -> None:
    substrate, journal, _clock = _open_journal(tmp_path)
    try:
        fp = fingerprint({"ledger": "row", "n": 1})
        assert is_ok(fp)
        outcome = journal.announce_evidence_append("task_ledger", fp.value)
        assert is_ok(outcome)
        assert outcome.value.status == "announced"
        assert outcome.value.journal_seq == 1
        assert outcome.value.append is not None
        record = outcome.value.append.record
        assert record.occurred_at == record.recorded_at
        assert record.journal_seq == 1
    finally:
        journal.close()
        substrate.close()
