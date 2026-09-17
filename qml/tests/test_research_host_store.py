"""Story 50.3 — host research_root blob store; explicit save returns bytes + ref."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.host import (
    QMA_BINDS_SECOND_CT44_OVER_RESEARCH_ROOT_V1,
    QMA_WRITES_RESEARCH_ROOT,
    RESEARCH_ROOT_IS_QMA_SETTING,
    RESEARCH_ROOT_IS_SEED_ROOT,
    persist_research_blob,
    read_research_blob,
    save_research_hypothesis,
)
from qml.research import (
    F_SLOTS,
    RESEARCH_CONTRACT_CLASS,
    RESEARCH_FORMAT_VERSION,
    DictionaryCite,
    Graph,
    Hypothesis,
    LayoutDemoProjection,
    SavedHypothesis,
    fingerprint_hypothesis,
    mint_hypothesis,
    restore_hypothesis,
    save_hypothesis,
)

from qml import host, research

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _hypothesis() -> Hypothesis:
    cite = DictionaryCite("dictionary/a.md", "swing-high")
    return _ok(
        mint_hypothesis(
            hypothesis_class="entry_hypothesis",
            origin="idea",
            dictionary_cites=[cite],
            graph=Graph(operators=("ALL",), meaning=("boolean",)),
            f_labels=dict.fromkeys(F_SLOTS, "unresolved"),
            unknowns=("pair",),
            title="from idea",
        )
    )


def test_explicit_save_returns_canonical_bytes_and_research_ref() -> None:
    hyp = _hypothesis()
    saved = save_hypothesis(hyp)
    assert is_ok(saved)
    assert isinstance(saved.value, SavedHypothesis)
    assert isinstance(saved.value.canonical_bytes, bytes)
    assert saved.value.research_ref.value.startswith("fp1:sha256:")
    assert saved.value.research_ref.value == _ok(fingerprint_hypothesis(hyp)).value
    envelope = json.loads(saved.value.canonical_bytes.decode("utf-8"))
    assert envelope["class"] == RESEARCH_CONTRACT_CLASS
    assert envelope["contract_format_version"] == RESEARCH_FORMAT_VERSION
    assert "body" in envelope
    for banned in ("occurrence", "writer", "created_at", "snapshot_ref"):
        assert banned not in envelope
        assert banned not in envelope["body"]
    restored = restore_hypothesis(envelope)
    assert is_ok(restored)
    assert restored.value.canonical_body() == hyp.canonical_body()


def test_host_persists_only_canonical_bytes_under_research_root(
    tmp_path: Path,
) -> None:
    hyp = _hypothesis()
    research_root = tmp_path / "research_root"
    seed_root = tmp_path / "seed_root"
    seed_root.mkdir()
    persisted = save_research_hypothesis(hyp, research_root=research_root)
    assert is_ok(persisted)
    record = persisted.value
    assert record.research_root == research_root
    assert record.path.is_file()
    assert record.path.parent == research_root
    assert record.path.name == record.research_ref.value.replace(":", "-")
    assert record.canonical_bytes == _ok(save_hypothesis(hyp)).canonical_bytes
    assert list(research_root.iterdir()) == [record.path]
    # Distinct from seed root_path — nothing written there.
    assert list(seed_root.iterdir()) == []
    reread = read_research_blob(
        research_root=research_root,
        research_ref=record.research_ref,
    )
    assert is_ok(reread)
    assert reread.value == record.canonical_bytes


def test_research_root_ownership_law_and_home() -> None:
    assert QMA_WRITES_RESEARCH_ROOT is False
    assert RESEARCH_ROOT_IS_QMA_SETTING is False
    assert RESEARCH_ROOT_IS_SEED_ROOT is False
    assert QMA_BINDS_SECOND_CT44_OVER_RESEARCH_ROOT_V1 is False
    assert host.QMA_WRITES_RESEARCH_ROOT is False
    assert "save_research_hypothesis" in host.__all__
    assert "persist_research_blob" in host.__all__
    # Same composition root that stamps CT-06/CT-07.
    assert hasattr(host, "mint_ct06_envelope")
    assert hasattr(host, "mint_generation_envelope")


def test_viewing_cited_seed_without_save_mints_no_research_ref(
    tmp_path: Path,
) -> None:
    assert not hasattr(research, "research_ref")
    assert not hasattr(research, "mint_research_ref")
    view = LayoutDemoProjection(
        package_id="STRAT-000001",
        hypothesis_class="entry_hypothesis",
        f_labels=dict.fromkeys(F_SLOTS, "unresolved"),
        read_only=True,
    )
    refused = save_hypothesis(view)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["research_ref"] is None
    host_refused = save_research_hypothesis(view, research_root=tmp_path / "research_root")
    assert is_refusal(host_refused)
    assert host_refused.context["field"] == "hypothesis"
    assert not (tmp_path / "research_root").exists()


def test_persist_rejects_non_bytes_payload(tmp_path: Path) -> None:
    hyp = _hypothesis()
    ref = _ok(fingerprint_hypothesis(hyp))
    refused = persist_research_blob(
        research_root=tmp_path / "research_root",
        research_ref=ref,
        canonical_bytes={"not": "bytes"},
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "canonical_bytes"
