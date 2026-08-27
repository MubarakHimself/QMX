"""L1 — unit assertions for CT-07 lineage edges (FR-007).

E2-L1-07  edge_type outside the ratified 14-value set is refused (FM-2)
E2-L1-08  a non-fp1 endpoint is refused (FM-2)
E2-L1-09  a well-formed edge serializes to exactly one LF-terminated canonical JSONL line
E2-L1-10  supersedes is linear (one outgoing per subject); branches-from is multi-head
"""

from __future__ import annotations

import json

from qmf.core import RefusalCategory, WriteOutcome, canonical_bytes, is_ok, is_refusal
from qmf.registry import EdgeLog, EdgeType, LineageEdge

import helpers as h

_RATIFIED_EDGE_TYPES = {
    "supersedes", "promoted-from", "occurrence-of", "corroborates", "disagrees-with",
    "confirmed-as", "confirmation", "invalidation", "interaction", "out-of-sequence",
    "continues-performance", "carries-ledger", "enacts", "branches-from",
}


def test_e2_l1_07_off_enum_edge_type_is_refused() -> None:
    out = LineageEdge.try_create("not-a-ratified-type", h.fp("a"), h.fp("b"), h.writer())
    assert is_refusal(out)
    assert out.category is RefusalCategory.INVALID_INPUT
    assert out.context.get("field") == "edge_type"


def test_e2_l1_07_ratified_set_is_exactly_fourteen() -> None:
    # The ratified V1 set is a closed 14 — addable later, never redefined.
    assert {e.value for e in EdgeType} == _RATIFIED_EDGE_TYPES
    assert len(list(EdgeType)) == 14


def test_e2_l1_08_non_fp1_endpoint_is_refused() -> None:
    for bad in ("record-42", "minted:id", 12345):
        out = LineageEdge.try_create(EdgeType.SUPERSEDES, bad, h.fp("b"), h.writer())
        assert is_refusal(out), f"non-fp1 from_ref accepted: {bad!r}"
        assert out.context.get("field") == "from_ref"
    out2 = LineageEdge.try_create(EdgeType.SUPERSEDES, h.fp("a"), "not-a-fingerprint", h.writer())
    assert is_refusal(out2)
    assert out2.context.get("field") == "to_ref"


def test_e2_l1_09_edge_serializes_to_one_lf_terminated_line() -> None:
    edge = h.unwrap(
        LineageEdge.try_create(EdgeType.OCCURRENCE_OF, h.fp("a"), h.fp("b"), h.writer()), "edge"
    )
    line = h.unwrap(edge.canonical_line(), "canonical line")
    assert line.endswith(b"\n")
    assert line.count(b"\n") == 1  # exactly one line
    body = line[:-1]
    # It is one fp1-canonical JSON object equal to canonical_bytes(fp1_identity()).
    assert body == h.unwrap(canonical_bytes(edge.fp1_identity()), "canonical bytes")
    obj = json.loads(body)
    assert obj["edge_type"] == "occurrence-of"
    assert obj["from_ref"] == edge.from_ref.value


def test_e2_l1_10_supersedes_is_linear_second_outgoing_refused() -> None:
    log = EdgeLog(h.writer())
    a, b, c = h.fp("A"), h.fp("B"), h.fp("C")
    first = h.unwrap(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=a, to_ref=b), "A>B")
    assert first.outcome is WriteOutcome.STORED
    # A second outgoing supersedes from the same subject A forks "current" — refused.
    second = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=a, to_ref=c)
    assert is_refusal(second)
    assert second.category is RefusalCategory.POLICY_REJECTION
    assert second.context.get("field") == "supersedes"
    # current_head resolves one unambiguous head.
    head = h.unwrap(log.current_head(b), "head")
    assert head == a


def test_e2_l1_10_supersedes_second_incoming_refused() -> None:
    log = EdgeLog(h.writer())
    a, b, c = h.fp("A"), h.fp("B"), h.fp("C")
    h.unwrap(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=b, to_ref=a), "B>A")
    # A second superseder of the same record A forks "current" — refused.
    forked = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=c, to_ref=a)
    assert is_refusal(forked)
    assert forked.context.get("field") == "supersedes"


def test_e2_l1_10_branches_from_allows_multi_head() -> None:
    log = EdgeLog(h.writer())
    a, b, c = h.fp("A"), h.fp("B"), h.fp("C")
    # branches-from carries no linearity constraint: several heads are legal.
    e1 = log.append(edge_type=EdgeType.BRANCHES_FROM, from_ref=b, to_ref=a)
    e2 = log.append(edge_type=EdgeType.BRANCHES_FROM, from_ref=c, to_ref=a)
    assert is_ok(e1)
    assert is_ok(e2)
    assert log.edge_count() == 2
