"""Story 47.2 — retained KnowledgeSource snapshots and citations (FR-Q65)."""

from __future__ import annotations

from pathlib import Path

from qma.core.ports.knowledge import GAP_0073_KNOWLEDGE_HYBRID_INDEXING
from qma.core.refusals import ProvenanceShapeMismatch, StaleSnapshot
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.knowledge import (
    KnowledgeService,
    KnowledgeSourceRegistry,
    PlainFileLibrarySource,
)
from qma.daemon.plugins import DaemonPluginContext
from qmf.core import is_ok, is_refusal

_DIMS = (
    "extraction_confidence",
    "rule_explicitness",
    "source_quality_completeness",
    "ambiguity_unresolved_status",
    "empirical_status",
    "portability_market_transfer_status",
)


def _confidence(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = dict.fromkeys(_DIMS, 0.7)
    body.update(overrides)
    return body


def _corpus(tmp_path: Path, *, name: str = "strats") -> Path:
    root = tmp_path / name
    root.mkdir(exist_ok=True)
    (root / "notes.md").write_text(
        "liquidity sweep near London open\nrange holds\n",
        encoding="utf-8",
    )
    (root / "ideas.md").write_text("unrelated note\n", encoding="utf-8")
    return root


def test_exactly_one_adapter_per_source_id(tmp_path: Path) -> None:
    registry = KnowledgeSourceRegistry()
    assert registry.source_ids() == ()
    root = _corpus(tmp_path)
    source = PlainFileLibrarySource(root_path=root, source_id="strats")
    first = registry.bind("strats", source, plugin_id="research-strats")
    assert is_ok(first)
    assert first.value.to_payload()["read_only"] is True
    assert first.value.to_payload()["impose_schema"] is False
    assert first.value.to_payload()["hybrid_indexing"] is False
    assert (
        first.value.to_payload()["evidence_confidence_distinct_from_admission_confidence"]
        is True
    )

    duplicate = registry.bind(
        "strats",
        PlainFileLibrarySource(root_path=root, source_id="strats"),
        plugin_id="other-plugin",
    )
    assert is_refusal(duplicate)
    assert "exactly one" in str(duplicate.context.get("reason", ""))
    assert duplicate.context.get("existing_plugin_id") == "research-strats"
    assert duplicate.context.get("incoming_plugin_id") == "other-plugin"


def test_plugin_context_registers_source_scoped_adapter(tmp_path: Path) -> None:
    ctx = DaemonPluginContext("research-strats")
    source = PlainFileLibrarySource(root_path=_corpus(tmp_path), source_id="strats")
    dispose = ctx.register_knowledge_source("strats", source)
    snap = ctx.snapshot()
    assert ("KnowledgeSource", "strats") in snap["singletons"]
    dispose()
    assert ("KnowledgeSource", "strats") not in ctx.snapshot()["singletons"]


def test_snapshot_search_and_no_layout_imposition(tmp_path: Path) -> None:
    service = KnowledgeService()
    root = _corpus(tmp_path)
    source = PlainFileLibrarySource(root_path=root, source_id="strats")
    assert source.declaration()["hardcoded_layout"] is False
    assert is_ok(service.bind("strats", source, plugin_id="research-strats"))

    snapped = service.snapshot("strats")
    assert is_ok(snapped)
    assert snapped.value.id.startswith("fp1:sha256:")
    assert "notes.md" in snapped.value.file_digests
    assert "ideas.md" in snapped.value.file_digests

    hits = service.search("strats", snapped.value, "liquidity sweep")
    assert is_ok(hits)
    assert hits.value == ("notes.md",)

    write = source.write(path="notes.md", content=b"nope")
    assert is_refusal(write)


def test_cite_copies_through_before_artifact_register(tmp_path: Path) -> None:
    hooks = HookRegistry()
    service = KnowledgeService(hooks=hooks)
    source = PlainFileLibrarySource(root_path=_corpus(tmp_path), source_id="strats")
    assert is_ok(service.bind("strats", source))

    snapped = service.snapshot("strats")
    assert is_ok(snapped)

    cited = service.cite(
        "strats",
        snapped.value,
        "notes.md",
        evidence_label="source-stated/explicit",
        evidence_confidence=_confidence(),
        authored_by="agent:research/quant/a1",
    )
    assert is_ok(cited)
    citation = cited.value.citation
    assert citation.source_ref == "strats"
    assert citation.snapshot_ref == snapped.value.id
    assert citation.locator == "notes.md"
    assert citation.evidence_label == "source-stated/explicit"
    assert dict(citation.evidence_confidence) == _confidence()
    assert citation.authored_by == "agent:research/quant/a1"
    assert citation.artifact_ref.startswith("artifact://knowledge/")
    assert cited.value.artifact.content == (tmp_path / "strats" / "notes.md").read_bytes()

    resolved = service.resolve_citation(citation)
    assert is_ok(resolved)
    assert resolved.value == cited.value.artifact.content


def test_retrieve_uncopied_snapshot_is_stale(tmp_path: Path) -> None:
    service = KnowledgeService()
    source = PlainFileLibrarySource(root_path=_corpus(tmp_path), source_id="strats")
    assert is_ok(service.bind("strats", source))
    snapped = service.snapshot("strats")
    assert is_ok(snapped)

    refused = service.retrieve("strats", snapped.value, "notes.md")
    assert is_refusal(refused)
    assert StaleSnapshot.matches(refused)
    assert refused.context["snapshot_ref"] == snapped.value.id


def test_provenance_shape_mismatch_and_no_scalarization(tmp_path: Path) -> None:
    service = KnowledgeService()
    source = PlainFileLibrarySource(root_path=_corpus(tmp_path), source_id="strats")
    assert is_ok(service.bind("strats", source))
    snapped = service.snapshot("strats")
    assert is_ok(snapped)

    bad = service.cite(
        "strats",
        snapped.value,
        "notes.md",
        evidence_label="source-stated/explicit",
        evidence_confidence={"extraction_confidence": 1.0},
        authored_by="agent:research/quant/a1",
    )
    assert is_refusal(bad)
    assert ProvenanceShapeMismatch.matches(bad)

    scalar = service.refuse_scalarize_evidence_confidence()
    assert is_refusal(scalar)
    assert scalar.context["field"] == "evidence_confidence"


def test_mission_pin_and_supersedes_chain(tmp_path: Path) -> None:
    service = KnowledgeService()
    root = _corpus(tmp_path)
    source = PlainFileLibrarySource(root_path=root, source_id="strats")
    assert is_ok(service.bind("strats", source))

    first = service.snapshot("strats")
    assert is_ok(first)
    pin = service.pin_mission_snapshot("mission-1", "strats", first.value)
    assert is_ok(pin)
    assert pin.value.snapshot_ref == first.value.id
    assert pin.value.previous_snapshot_ref is None

    (root / "notes.md").write_text("liquidity sweep revised\n", encoding="utf-8")
    source.invalidate_cache()
    second = service.snapshot("strats")
    assert is_ok(second)
    assert second.value.id != first.value.id
    assert second.value.supersedes == first.value.id

    re_pin = service.pin_mission_snapshot("mission-1", "strats", second.value)
    assert is_ok(re_pin)
    assert re_pin.value.previous_snapshot_ref == first.value.id
    assert re_pin.value.to_payload()["re_pin"] is True

    chain = service.supersedes_chain("strats")
    assert is_ok(chain)
    assert chain.value == (first.value.id, second.value.id)


def test_gap_0073_excluded_from_search(tmp_path: Path) -> None:
    service = KnowledgeService()
    source = PlainFileLibrarySource(root_path=_corpus(tmp_path), source_id="strats")
    assert is_ok(service.bind("strats", source))
    snapped = service.snapshot("strats")
    assert is_ok(snapped)

    hybrid = service.search("strats", snapped.value, "liquidity", mode="hybrid")
    assert is_refusal(hybrid)
    assert hybrid.context["gap"] == GAP_0073_KNOWLEDGE_HYBRID_INDEXING

    deferred = service.refuse_hybrid_indexing(requested="embeddings")
    assert is_refusal(deferred)
    assert deferred.context.get("deferred") is True
