"""Tier-1 tests for the keep-forever-vs-deletion-licensed retention law (AC3)."""

from __future__ import annotations

from qmf.core import Fingerprint, World, fingerprint, is_ok
from qmf.data.retention import RetentionPolicy, RetentionVerdict
from qmf.data.store import RoomRole, StoreReceipt, WriteOutcome


def _fp(seed: str) -> Fingerprint:
    built = fingerprint({"seed": seed})
    assert is_ok(built)
    return built.value


def _receipt(
    *,
    room_role: RoomRole,
    retained_forever: bool,
    is_evidence_bearing: bool,
    seed: str = "artifact",
) -> StoreReceipt:
    return StoreReceipt(
        outcome=WriteOutcome.STORED,
        fingerprint=_fp(seed),
        world=World.LIVE,
        room_role=room_role,
        engine="parquet",
        is_evidence_bearing=is_evidence_bearing,
        retained_forever=retained_forever,
    )


class _Cites:
    """A citation index over an explicit set of cited fingerprint strings."""

    def __init__(self, *cited: Fingerprint) -> None:
        self._cited = {fp.value for fp in cited}

    def cites(self, fingerprint: Fingerprint, /) -> bool:
        return fingerprint.value in self._cited


def test_raw_evidence_is_retained_forever_and_never_deletable() -> None:
    raw = _receipt(
        room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, retained_forever=True, is_evidence_bearing=True
    )
    verdict = RetentionPolicy(_Cites()).verdict_for(raw)
    assert verdict == RetentionVerdict(
        retained_forever=True, deletion_licensed=False, reason=verdict.reason
    )
    assert not RetentionPolicy(_Cites()).may_delete(raw)


def test_journal_and_lineage_and_records_kept_forever() -> None:
    # Every retained_forever artifact — journal, registry records, lineage edges —
    # is kept forever and deletion is never licensed, citation irrelevant.
    for role in (RoomRole.JOURNAL, RoomRole.REGISTRY_ROOM):
        receipt = _receipt(room_role=role, retained_forever=True, is_evidence_bearing=True)
        # Even a citation index that would cite it cannot make it *more* deletable.
        verdict = RetentionPolicy(_Cites(receipt.fingerprint)).verdict_for(receipt)
        assert verdict.retained_forever is True
        assert verdict.deletion_licensed is False


def test_uncited_rebuildable_view_is_deletion_licensed() -> None:
    view = _receipt(room_role=RoomRole.PROCESSED, retained_forever=False, is_evidence_bearing=False)
    verdict = RetentionPolicy(_Cites()).verdict_for(view)
    assert verdict.retained_forever is False
    assert verdict.deletion_licensed is True
    assert "no result label cites" in verdict.reason
    assert RetentionPolicy(_Cites()).may_delete(view)


def test_cited_rebuildable_view_is_retained_forever() -> None:
    view = _receipt(room_role=RoomRole.PROCESSED, retained_forever=False, is_evidence_bearing=False)
    policy = RetentionPolicy(_Cites(view.fingerprint))
    verdict = policy.verdict_for(view)
    assert verdict.retained_forever is True
    assert verdict.deletion_licensed is False
    assert "a result label cites" in verdict.reason
    assert not policy.may_delete(view)


def test_citation_of_a_different_artifact_does_not_retain_this_view() -> None:
    view = _receipt(
        room_role=RoomRole.PROCESSED,
        retained_forever=False,
        is_evidence_bearing=False,
        seed="this-view",
    )
    other = _fp("some-other-artifact")
    verdict = RetentionPolicy(_Cites(other)).verdict_for(view)
    assert verdict.deletion_licensed is True


def test_reason_names_the_room_role_for_evidence() -> None:
    raw = _receipt(
        room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, retained_forever=True, is_evidence_bearing=True
    )
    verdict = RetentionPolicy(_Cites()).verdict_for(raw)
    assert "immutable raw archive" in verdict.reason
