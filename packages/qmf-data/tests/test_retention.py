"""Tier-1 tests for the keep-forever-vs-deletion-licensed retention law (AC3)."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import Fingerprint, RefusalCategory, Result, World, fingerprint, is_ok, is_refusal
from qmf.data.retention import RetentionPolicy, RetentionVerdict
from qmf.data.store import RoomRole, StoreReceipt, WriteOutcome

T = TypeVar("T")


def _fp(seed: str) -> Fingerprint:
    built = fingerprint({"seed": seed})
    assert is_ok(built)
    return built.value


def _verdict(result: Result[RetentionVerdict]) -> RetentionVerdict:
    assert is_ok(result), result
    return result.value


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


class _RaisingIndex:
    """A citation index whose registry seam is unavailable and raises across the boundary."""

    def __init__(self) -> None:
        self.calls = 0

    def cites(self, fingerprint: Fingerprint, /) -> bool:
        self.calls += 1
        raise ConnectionError("registry seam unreachable")


def test_raw_evidence_is_retained_forever_and_never_deletable() -> None:
    raw = _receipt(
        room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, retained_forever=True, is_evidence_bearing=True
    )
    verdict = _verdict(RetentionPolicy(_Cites()).verdict_for(raw))
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
        verdict = _verdict(RetentionPolicy(_Cites(receipt.fingerprint)).verdict_for(receipt))
        assert verdict.retained_forever is True
        assert verdict.deletion_licensed is False


def test_uncited_rebuildable_view_is_deletion_licensed() -> None:
    view = _receipt(room_role=RoomRole.PROCESSED, retained_forever=False, is_evidence_bearing=False)
    verdict = _verdict(RetentionPolicy(_Cites()).verdict_for(view))
    assert verdict.retained_forever is False
    assert verdict.deletion_licensed is True
    assert "no result label cites" in verdict.reason
    assert RetentionPolicy(_Cites()).may_delete(view)


def test_cited_rebuildable_view_is_retained_forever() -> None:
    view = _receipt(room_role=RoomRole.PROCESSED, retained_forever=False, is_evidence_bearing=False)
    policy = RetentionPolicy(_Cites(view.fingerprint))
    verdict = _verdict(policy.verdict_for(view))
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
    verdict = _verdict(RetentionPolicy(_Cites(other)).verdict_for(view))
    assert verdict.deletion_licensed is True


def test_reason_names_the_room_role_for_evidence() -> None:
    raw = _receipt(
        room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, retained_forever=True, is_evidence_bearing=True
    )
    verdict = _verdict(RetentionPolicy(_Cites()).verdict_for(raw))
    assert "immutable raw archive" in verdict.reason


# --- M6: fail closed when the citation index is unavailable -----------------


def test_raising_citation_index_is_a_typed_refusal_not_a_raise() -> None:
    # A raising index must NOT propagate ConnectionError across the package boundary
    # (CT-04, AR-13); it becomes an unavailable-dependency typed refusal instead.
    view = _receipt(room_role=RoomRole.PROCESSED, retained_forever=False, is_evidence_bearing=False)
    index = _RaisingIndex()
    verdict = RetentionPolicy(index).verdict_for(view)  # must not raise
    assert index.calls == 1
    assert is_refusal(verdict)
    assert verdict.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert verdict.context.get("field") == "citations"


def test_raising_citation_index_does_not_license_deletion() -> None:
    # Fail closed against Story 3.3 AC3: a failed/unavailable citation read never licenses
    # deleting a rebuildable view — deletion needs a positive, successful "nothing cites this".
    view = _receipt(room_role=RoomRole.PROCESSED, retained_forever=False, is_evidence_bearing=False)
    assert RetentionPolicy(_RaisingIndex()).may_delete(view) is False


def test_evidence_verdict_never_consults_a_raising_index() -> None:
    # A retained-forever artifact is decided by its receipt alone; the citation seam is never
    # consulted, so even a raising index yields the clean keep-forever verdict.
    raw = _receipt(
        room_role=RoomRole.IMMUTABLE_RAW_ARCHIVE, retained_forever=True, is_evidence_bearing=True
    )
    index = _RaisingIndex()
    verdict = _verdict(RetentionPolicy(index).verdict_for(raw))
    assert index.calls == 0
    assert verdict.deletion_licensed is False
