"""Story 47.2 — KnowledgeSource port definitions (CT-44; FR-Q65)."""

from __future__ import annotations

from qma.core.ports import (
    EVIDENCE_CONFIDENCE_DIMENSION_COUNT,
    GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
    KNOWLEDGE_QUERY_SURFACE,
    KNOWLEDGE_SOURCE_OPERATIONS,
    build_corpus_snapshot,
    literal_search,
    parse_citation,
    parse_confidence_dimensions,
    parse_provenance,
    refuse_evidence_confidence_scalarization,
    refuse_hybrid_knowledge_indexing,
    refuse_knowledge_write_back,
    validate_evidence_confidence_shape,
)
from qma.core.refusals import ProvenanceShapeMismatch
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
    body: dict[str, object] = {key: 0.5 for key in _DIMS}
    body.update(overrides)
    return body


def test_operation_surface_is_literal_query_only() -> None:
    assert KNOWLEDGE_SOURCE_OPERATIONS == frozenset(
        {"snapshot", "search", "retrieve", "cite"}
    )
    assert KNOWLEDGE_QUERY_SURFACE == frozenset({"search", "retrieve", "cite"})
    assert EVIDENCE_CONFIDENCE_DIMENSION_COUNT == 6


def test_snapshot_id_is_content_addressed_tree_digest() -> None:
    first = build_corpus_snapshot(
        source_id="strats",
        file_bytes={"a.md": b"alpha", "b.md": b"beta"},
    )
    second = build_corpus_snapshot(
        source_id="strats",
        file_bytes={"b.md": b"beta", "a.md": b"alpha"},
    )
    assert is_ok(first)
    assert is_ok(second)
    assert first.value.id == second.value.id
    assert first.value.id.startswith("fp1:sha256:")
    assert set(first.value.file_digests) == {"a.md", "b.md"}

    changed = build_corpus_snapshot(
        source_id="strats",
        file_bytes={"a.md": b"alpha!", "b.md": b"beta"},
    )
    assert is_ok(changed)
    assert changed.value.id != first.value.id


def test_literal_search_is_grep_class() -> None:
    hits = literal_search(
        {"notes.md": b"liquidity sweep near London open", "other.md": b"unrelated"},
        "liquidity sweep",
    )
    assert is_ok(hits)
    assert hits.value == ("notes.md",)

    empty = literal_search({"notes.md": b"hello"}, "missing-token")
    assert is_ok(empty)
    assert empty.value == ()


def test_confidence_dimensions_exactly_six() -> None:
    ok = parse_confidence_dimensions(_DIMS)
    assert is_ok(ok)
    assert ok.value == _DIMS

    too_few = parse_confidence_dimensions(_DIMS[:5])
    assert is_refusal(too_few)

    dup = parse_confidence_dimensions((*_DIMS[:5], _DIMS[0]))
    assert is_refusal(dup)


def test_provenance_shape_mismatch_and_verbatim_fields() -> None:
    parsed = parse_provenance(
        {
            "source_ref": "strats",
            "snapshot_ref": "fp1:sha256:abc",
            "locator": "notes.md",
            "evidence_label": "source-stated/explicit",
            "evidence_confidence": _confidence(),
        },
        declared_keys=_DIMS,
        source_id="strats",
    )
    assert is_ok(parsed)
    assert parsed.value.evidence_label == "source-stated/explicit"
    assert dict(parsed.value.evidence_confidence) == _confidence()

    mismatch = validate_evidence_confidence_shape(
        {"extraction_confidence": 1.0},
        declared_keys=_DIMS,
        source_id="strats",
    )
    assert is_refusal(mismatch)
    assert ProvenanceShapeMismatch.matches(mismatch)

    citation = parse_citation(
        {
            "source_ref": "strats",
            "snapshot_ref": "fp1:sha256:abc",
            "locator": "notes.md",
            "evidence_label": "visually-demonstrated",
            "evidence_confidence": _confidence(empirical_status=0.1),
            "artifact_ref": "artifact://knowledge/x",
            "authored_by": "agent:research/quant/a1",
        },
        declared_keys=_DIMS,
        source_id="strats",
    )
    assert is_ok(citation)
    assert citation.value.artifact_ref == "artifact://knowledge/x"
    assert citation.value.evidence_confidence["empirical_status"] == 0.1


def test_gap_0073_and_no_scalarization_or_write_back() -> None:
    hybrid = refuse_hybrid_knowledge_indexing(mode="semantic")
    assert is_refusal(hybrid)
    assert hybrid.context["gap"] == GAP_0073_KNOWLEDGE_HYBRID_INDEXING
    assert hybrid.context.get("deferred") is True

    scalar = refuse_evidence_confidence_scalarization()
    assert is_refusal(scalar)
    assert scalar.context["field"] == "evidence_confidence"

    write = refuse_knowledge_write_back()
    assert is_refusal(write)
    assert write.context["field"] == "write"
