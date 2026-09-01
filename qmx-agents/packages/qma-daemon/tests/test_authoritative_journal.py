"""Story 42.2 — authoritative journal, closed stores, evidence announcements."""

from __future__ import annotations

from pathlib import Path

from qma.daemon import AuthoritativeJournal, PersistenceSubstrate
from qma.daemon.journal import (
    ANNOUNCEMENT_REQUIRED_STORES,
    CLOSED_INDEPENDENT_STORES,
    CLOSED_PROJECTIONS,
    CLOSED_STORE_NAMES,
    DEFINITION_STORE_MEMBERS,
    TELEMETRY_STORE,
    AnnouncedRecord,
    FoldMetadata,
    StoreClass,
    order_by_announcement_journal_seq,
)
from qmf.core import RefusalCategory, fingerprint, is_ok, is_refusal


def _open_journal(tmp_path: Path, *, boot: str = "boot-1") -> tuple[
    PersistenceSubstrate, AuthoritativeJournal
]:
    substrate_result = PersistenceSubstrate.open(
        tmp_path, machine="test-host", boot_epoch_id=boot
    )
    assert is_ok(substrate_result), substrate_result
    substrate = substrate_result.value
    journal_result = AuthoritativeJournal.bind(substrate)
    assert is_ok(journal_result), journal_result
    return substrate, journal_result.value


def test_append_assigns_global_monotonic_journal_seq(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        scope = [{"kind": "desk", "id": "research"}]
        first = journal.append_event("mission.updated", scope_path=scope, payload={"n": 1})
        second = journal.append_event("task.completed", scope_path=scope, payload={"n": 2})
        assert is_ok(first) and is_ok(second)
        assert first.value.record.journal_seq == 1
        assert second.value.record.journal_seq == 2
        assert journal.next_journal_seq == 3

        rows = journal.read_all()
        assert is_ok(rows)
        assert [row["journal_seq"] for row in rows.value] == [1, 2]
        assert all(row["class"] == "qma-journal-event" for row in rows.value)
    finally:
        journal.close()
        substrate.close()


def test_journal_seq_is_sole_total_order_per_scope_seq_is_derived(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        desk = [{"kind": "desk", "id": "research"}]
        deeper = [
            {"kind": "desk", "id": "research"},
            {"kind": "quant", "id": "q1"},
        ]
        a = journal.append_event("agent.started", scope_path=desk, payload={"i": 1})
        b = journal.append_event("agent.started", scope_path=deeper, payload={"i": 2})
        c = journal.append_event("agent.started", scope_path=desk, payload={"i": 3})
        assert is_ok(a) and is_ok(b) and is_ok(c)
        assert a.value.scope_seq == 1
        assert b.value.scope_seq == 1  # different scope key
        assert c.value.scope_seq == 2

        # journal_seq is global; scope seq is a derived projection index.
        assert [a.value.record.journal_seq, b.value.record.journal_seq, c.value.record.journal_seq] == [
            1,
            2,
            3,
        ]
        projected = journal.scope_projection(desk)
        assert is_ok(projected)
        assert [seq for seq, _ in projected.value] == [1, 2, 3]
        assert [row["journal_seq"] for _, row in projected.value] == [1, 2, 3]
    finally:
        journal.close()
        substrate.close()


def test_closed_store_list_accepts_only_declared_vocabulary(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        assert len(DEFINITION_STORE_MEMBERS) == 16
        assert CLOSED_PROJECTIONS | CLOSED_INDEPENDENT_STORES | frozenset(
            DEFINITION_STORE_MEMBERS
        ) == CLOSED_STORE_NAMES

        for name in sorted(CLOSED_STORE_NAMES):
            declared = journal.declare_store(name)
            assert is_ok(declared), name
            assert declared.value.materialized is False
            assert declared.value.fold_metadata.ordering_key == "journal_seq"
            assert (
                declared.value.fold_metadata.equal_instant_disposition
                == "ascending_journal_seq"
            )

        refused = journal.declare_store("shadow_cache")
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert "closed" in str(refused.context.get("reason", "")).lower()

        # Redeclare is idempotent and still not materialized.
        again = journal.declare_store("task_ledger")
        assert is_ok(again)
        assert again.value.store_class is StoreClass.INDEPENDENT_STORE
        assert again.value.materialized is False
    finally:
        journal.close()
        substrate.close()


def test_materialize_only_on_first_in_scope_write(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        declared = journal.declare_store("artifact_store")
        assert is_ok(declared)
        assert declared.value.materialized is False

        fp = fingerprint({"artifact": "bytes", "n": 1})
        assert is_ok(fp)
        announced = journal.announce_evidence_append("artifact_store", fp.value)
        assert is_ok(announced)
        assert announced.value.status == "announced"
        assert journal.stores.declared()["artifact_store"].materialized is True
    finally:
        journal.close()
        substrate.close()


def test_evidence_announcement_carries_store_and_fp1(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        record_fp = fingerprint({"ledger_entry": "done", "attempt_no": 1})
        assert is_ok(record_fp)
        for store in sorted(ANNOUNCEMENT_REQUIRED_STORES):
            outcome = journal.announce_evidence_append(
                store,
                record_fp.value,
                scope_path=[{"kind": "desk", "id": "research"}],
            )
            assert is_ok(outcome), store
            assert outcome.value.status == "announced"
            assert outcome.value.journal_seq is not None
            assert outcome.value.append is not None
            payload = outcome.value.append.record.payload
            assert payload["store"] == store
            assert payload["record_fp1"] == record_fp.value.value
            assert outcome.value.append.record.event.endswith(
                ("appended", "registered", "admitted")
            )
    finally:
        journal.close()
        substrate.close()


def test_telemetry_store_is_exempt_from_announcement_law(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        before = journal.next_journal_seq
        fp = fingerprint({"metric": "latency_ms", "value": 12})
        assert is_ok(fp)
        outcome = journal.announce_evidence_append(TELEMETRY_STORE, fp.value)
        assert is_ok(outcome)
        assert outcome.value.status == "exempted"
        assert outcome.value.journal_seq is None
        assert outcome.value.append is None
        assert journal.next_journal_seq == before

        rows = journal.read_all()
        assert is_ok(rows)
        assert rows.value == []
    finally:
        journal.close()
        substrate.close()


def test_fold_orders_by_announcement_journal_seq_not_timestamp() -> None:
    # Same recorded_at instant; lower journal_seq must win regardless of payload time.
    same_instant = 1_700_000_000_000_000_000
    records = [
        AnnouncedRecord(
            journal_seq=3,
            store="artifact_store",
            record_fp1="fp1:sha256:" + ("a" * 64),
            recorded_at=same_instant,
        ),
        AnnouncedRecord(
            journal_seq=1,
            store="task_ledger",
            record_fp1="fp1:sha256:" + ("b" * 64),
            recorded_at=same_instant,
        ),
        AnnouncedRecord(
            journal_seq=2,
            store="staging_store",
            record_fp1="fp1:sha256:" + ("c" * 64),
            recorded_at=same_instant - 10,  # earlier timestamp must not reorder
        ),
    ]
    ordered = order_by_announcement_journal_seq(records)
    assert [item.journal_seq for item in ordered] == [1, 2, 3]
    assert FoldMetadata().ordering_key == "journal_seq"


def test_journal_seq_resumes_after_rebind(tmp_path: Path) -> None:
    first_substrate, first = _open_journal(tmp_path, boot="boot-a")
    try:
        result = first.append_event("hook.blocked", payload={"reason": "deny"})
        assert is_ok(result)
        assert result.value.record.journal_seq == 1
    finally:
        first.close()
        first_substrate.close()

    second_substrate, second = _open_journal(tmp_path, boot="boot-b")
    try:
        assert second.next_journal_seq == 2
        result = second.append_event("provider.cooldown", payload={"ms": 5})
        assert is_ok(result)
        assert result.value.record.journal_seq == 2
        rows = second.read_all()
        assert is_ok(rows)
        assert [row["journal_seq"] for row in rows.value] == [1, 2]
    finally:
        second.close()
        second_substrate.close()


def test_unknown_store_announcement_refused(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        fp = fingerprint({"x": 1})
        assert is_ok(fp)
        refused = journal.announce_evidence_append("not_a_store", fp.value)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
    finally:
        journal.close()
        substrate.close()
