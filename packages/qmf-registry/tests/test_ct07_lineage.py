"""CT-07 contract test — append-only typed lineage edges (Story 2.2).

The Tier-1 contract test for the CT-07 boundary. Each acceptance criterion is asserted
against the real edge/stream types, with every ``fp1`` fingerprint computed by qmf-core:

* AC1 — an edge references BOTH endpoints by their fp1 fingerprint and carries an
  edge_type from the ratified V1 set; a type outside the set, or an endpoint that is not
  an fp1 fingerprint, is a typed refusal (FM-2).
* AC2 — edges serialize to the pinned JSONL line (one fp1-canonical JSON object,
  LF-terminated); the edge fingerprint is DERIVED, never minted; indexes are local and
  rebuildable, so losing one costs a rebuild, never evidence.
* AC3 — supersedes is pinned linear (one outgoing per subject, one resolvable head, no
  fork, no cycle); branches-from allows several heads.
* AC4 — a correction is a NEW edge (a superseding relationship is a supersedes edge);
  corroborates and disagrees-with are kept visible and never merged away.
* AC5 — a byte-identical re-append is idempotent; a true collision is refused and
  alarmed, never overwritten.
* AC6 — an edge stream has exactly one writer and unlimited readers; the module imports
  only qmf.core (default-deny).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Fingerprint,
    RefusalCategory,
    Result,
    TypedRefusal,
    WriterId,
    canonical_bytes,
    fingerprint,
    is_ok,
)
from qmf.registry import (
    EDGE_CONTRACT_FORMAT_VERSION,
    EdgeAppendReceipt,
    EdgeLog,
    EdgeType,
    LineageEdge,
    WriteOutcome,
)
from qmf.registry import lineage as lineage_module

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _writer(machine: str = "node-a", stream: str = "lineage") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", stream, "boot-1"))


def _fp(tag: object) -> Fingerprint:
    return _ok(fingerprint({"rec": tag}))


def _edge(**overrides: object) -> LineageEdge:
    args: dict[str, object] = {
        "edge_type": EdgeType.SUPERSEDES,
        "from_ref": _fp("newer"),
        "to_ref": _fp("older"),
        "writer": _writer(),
        "contract_format_version": EDGE_CONTRACT_FORMAT_VERSION,
    }
    args.update(overrides)
    return _ok(
        LineageEdge.try_create(
            args["edge_type"],
            args["from_ref"],
            args["to_ref"],
            args["writer"],
            args["contract_format_version"],
        )
    )


def _refused(result: object, field: str, category: RefusalCategory) -> TypedRefusal:
    assert isinstance(result, TypedRefusal), result
    assert result.category is category, result
    assert result.context["field"] == field, result
    return result


# --- AC1: typed edges over fp1 endpoints, from the ratified set --------------


def test_edge_references_both_endpoints_by_fp1() -> None:
    edge = _edge(from_ref=_fp("a"), to_ref=_fp("b"))
    assert isinstance(edge.from_ref, Fingerprint)
    assert isinstance(edge.to_ref, Fingerprint)
    assert edge.from_ref.value.startswith("fp1:sha256:")
    assert edge.to_ref.value.startswith("fp1:sha256:")


def test_every_ratified_edge_type_is_admitted() -> None:
    # All fourteen ratified V1 edge types construct; the set is closed in V1.
    assert {member.value for member in EdgeType} == {
        "supersedes",
        "promoted-from",
        "occurrence-of",
        "corroborates",
        "disagrees-with",
        "confirmed-as",
        "confirmation",
        "invalidation",
        "interaction",
        "out-of-sequence",
        "continues-performance",
        "carries-ledger",
        "enacts",
        "branches-from",
    }
    for member in EdgeType:
        edge = _edge(edge_type=member)
        assert edge.edge_type is member


def test_edge_type_accepts_the_canonical_string_form() -> None:
    edge = _edge(edge_type="promoted-from")
    assert edge.edge_type is EdgeType.PROMOTED_FROM


def test_edge_refuses_type_outside_the_ratified_set() -> None:
    # A kind outside the ratified set is FM-2 — edge types are addable, never invented.
    refusal = _refused(
        LineageEdge.try_create("merged-into", _fp("a"), _fp("b"), _writer()),
        "edge_type",
        RefusalCategory.INVALID_INPUT,
    )
    assert "supersedes" in refusal.context["allowed"]  # type: ignore[operator]
    # A non-string, non-EdgeType value is likewise refused, never coerced.
    _refused(
        LineageEdge.try_create(123, _fp("a"), _fp("b"), _writer()),
        "edge_type",
        RefusalCategory.INVALID_INPUT,
    )


def test_edge_refuses_non_fp1_endpoints() -> None:
    # An endpoint that is not an fp1 fingerprint (a minted/mutable id) is FM-2.
    _refused(
        LineageEdge.try_create(EdgeType.SUPERSEDES, "record-42", _fp("b"), _writer()),
        "from_ref",
        RefusalCategory.INVALID_INPUT,
    )
    _refused(
        LineageEdge.try_create(EdgeType.SUPERSEDES, _fp("a"), 12345, _writer()),
        "to_ref",
        RefusalCategory.INVALID_INPUT,
    )


def test_edge_refuses_bad_writer_and_version() -> None:
    _refused(
        LineageEdge.try_create(EdgeType.SUPERSEDES, _fp("a"), _fp("b"), "node-a"),
        "writer",
        RefusalCategory.INVALID_INPUT,
    )
    for bad in (0, -1, True, "1", 1.0):
        _refused(
            LineageEdge.try_create(EdgeType.SUPERSEDES, _fp("a"), _fp("b"), _writer(), bad),
            "contract_format_version",
            RefusalCategory.INVALID_INPUT,
        )


def test_edge_endpoints_accept_fingerprint_strings() -> None:
    edge = _edge(from_ref=_fp("a").value, to_ref=_fp("b").value)
    assert edge.from_ref == _fp("a")
    assert edge.to_ref == _fp("b")


# --- AC2: pinned JSONL, derived fingerprint, rebuildable indexes -------------


def test_edge_fingerprint_is_derived_never_minted() -> None:
    edge = _edge()
    # The id equals the fingerprint of the identity content (computed by qmf-core);
    # try_create accepts no caller-supplied id.
    assert edge.edge_fingerprint == _ok(fingerprint(edge.fp1_identity()))
    assert edge.edge_fingerprint.value.startswith("fp1:sha256:")


def test_edge_identity_content_carries_every_field() -> None:
    identity = _edge().fp1_identity()
    assert set(identity) == {
        "class",
        "edge_type",
        "from_ref",
        "to_ref",
        "contract_format_version",
        "writer",
    }
    assert identity["class"] == "lineage-edge"
    assert identity["contract_format_version"] == EDGE_CONTRACT_FORMAT_VERSION


def test_canonical_line_is_one_lf_terminated_fp1_canonical_object() -> None:
    edge = _edge()
    line = _ok(edge.canonical_line())
    assert line.endswith(b"\n")
    assert line.count(b"\n") == 1
    # The line is exactly the fp1-canonical serialization of the identity content.
    assert line[:-1] == _ok(canonical_bytes(edge.fp1_identity()))
    parsed = json.loads(line)
    assert parsed == {
        "class": "lineage-edge",
        "edge_type": "supersedes",
        "from_ref": edge.from_ref.value,
        "to_ref": edge.to_ref.value,
        "contract_format_version": EDGE_CONTRACT_FORMAT_VERSION,
        "writer": {
            "machine": "node-a",
            "role": "authoring",
            "stream": "lineage",
            "boot_epoch_id": "boot-1",
        },
    }
    # Keys are sorted at every depth (the fp1 canonical rule).
    assert list(parsed) == sorted(parsed)
    assert list(parsed["writer"]) == sorted(parsed["writer"])


def test_a_different_field_derives_a_different_fingerprint() -> None:
    base = _edge()
    other_type = _edge(edge_type=EdgeType.PROMOTED_FROM)
    other_from = _edge(from_ref=_fp("different"))
    other_writer = _edge(writer=_writer("node-b"))
    assert other_type.edge_fingerprint != base.edge_fingerprint
    assert other_from.edge_fingerprint != base.edge_fingerprint
    # Writer is an identity field on an edge (CT-07 declares no exclusion), so a
    # different writer derives a different edge fingerprint.
    assert other_writer.edge_fingerprint != base.edge_fingerprint


def test_indexes_are_local_and_rebuildable() -> None:
    log = EdgeLog(_writer())
    v1, v2, v3 = _fp("v1"), _fp("v2"), _fp("v3")
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v1))
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v3, to_ref=v2))
    head_before = _ok(log.current_head(v1))
    edges_before = log.edges()
    # Drop and rebuild the derived indexes: the evidence is untouched and the head
    # resolves identically, so losing an index costs a rebuild, never evidence.
    log.rebuild_indexes()
    assert log.edges() == edges_before
    assert _ok(log.current_head(v1)) == head_before == v3


# --- AC3: supersedes is linear; branches-from is not ------------------------


def test_supersedes_is_linear_one_outgoing_per_subject() -> None:
    log = EdgeLog(_writer())
    v0, v1, v2 = _fp("v0"), _fp("v1"), _fp("v2")
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v1))
    # A second outgoing supersedes from the same subject is refused (would make
    # "current" ambiguous).
    second = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v0)
    _refused(second, "supersedes", RefusalCategory.POLICY_REJECTION)
    assert log.edge_count() == 1


def test_supersedes_refuses_a_second_superseder_of_one_record() -> None:
    log = EdgeLog(_writer())
    v1, v2, v3 = _fp("v1"), _fp("v2"), _fp("v3")
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v1))
    # Two records both superseding v1 would fork "current"; refused.
    fork = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v3, to_ref=v1)
    _refused(fork, "supersedes", RefusalCategory.POLICY_REJECTION)


def test_supersedes_refuses_self_and_cycle() -> None:
    log = EdgeLog(_writer())
    v1, v2 = _fp("v1"), _fp("v2")
    self_edge = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v1, to_ref=v1)
    _refused(self_edge, "supersedes", RefusalCategory.POLICY_REJECTION)
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v1))
    # v1 supersedes v2 would close the v2->v1 chain into a cycle: no resolvable head.
    cycle = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v1, to_ref=v2)
    _refused(cycle, "supersedes", RefusalCategory.POLICY_REJECTION)


def test_current_head_resolves_one_unambiguous_current() -> None:
    log = EdgeLog(_writer())
    v1, v2, v3, other = _fp("v1"), _fp("v2"), _fp("v3"), _fp("unrelated")
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v1))
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v3, to_ref=v2))
    assert _ok(log.current_head(v1)) == v3
    assert _ok(log.current_head(v2)) == v3
    assert _ok(log.current_head(v3)) == v3  # the head is its own current
    assert _ok(log.current_head(other)) == other  # nothing supersedes it
    _refused(log.current_head("not-a-fingerprint"), "record", RefusalCategory.INVALID_INPUT)


def test_branches_from_allows_several_heads() -> None:
    log = EdgeLog(_writer())
    child = _fp("child")
    branch_a, branch_b = _fp("branch-a"), _fp("branch-b")
    # A branching version graph: several branches-from edges from one subject are all
    # legal — "current" is a separate dated pointer record, never inferred here.
    assert is_ok(log.append(edge_type=EdgeType.BRANCHES_FROM, from_ref=child, to_ref=branch_a))
    assert is_ok(log.append(edge_type=EdgeType.BRANCHES_FROM, from_ref=child, to_ref=branch_b))
    assert len(log.edges_from(child)) == 2
    assert len(log.edges_of_type(EdgeType.BRANCHES_FROM)) == 2


# --- AC4: a correction is a new edge; disagreements stay visible ------------


def test_a_correction_is_a_new_edge_never_an_edit() -> None:
    log = EdgeLog(_writer())
    original, corrected = _fp("card-v1"), _fp("card-v2")
    # A correction adds a supersedes edge; the original edge/record is never edited.
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=corrected, to_ref=original))
    assert log.edge_count() == 1
    assert _ok(log.current_head(original)) == corrected


def test_corroborates_and_disagrees_with_are_kept_visible() -> None:
    log = EdgeLog(_writer())
    source_a, source_b = _fp("tick-source-a"), _fp("tick-source-b")
    assert is_ok(log.append(edge_type=EdgeType.CORROBORATES, from_ref=source_a, to_ref=source_b))
    assert is_ok(log.append(edge_type=EdgeType.DISAGREES_WITH, from_ref=source_a, to_ref=source_b))
    # Both edges coexist — a disagreement is never merged away.
    assert len(log.edges_of_type(EdgeType.CORROBORATES)) == 1
    assert len(log.edges_of_type(EdgeType.DISAGREES_WITH)) == 1
    assert log.edge_count() == 2


# --- AC5: idempotent re-append vs true collision ----------------------------


def test_append_stores_then_idempotent_reappend() -> None:
    log = EdgeLog(_writer())
    first = log.append(edge_type=EdgeType.PROMOTED_FROM, from_ref=_fp("a"), to_ref=_fp("b"))
    assert is_ok(first)
    assert isinstance(first.value, EdgeAppendReceipt)
    assert first.value.outcome is WriteOutcome.STORED
    # A byte-identical re-append (same single writer) dedups and is accepted silently.
    again = log.append(edge_type=EdgeType.PROMOTED_FROM, from_ref=_fp("a"), to_ref=_fp("b"))
    assert is_ok(again)
    assert again.value.outcome is WriteOutcome.IDEMPOTENT
    assert again.value.edge is first.value.edge
    assert log.edge_count() == 1


def test_idempotent_reappend_of_a_later_edge_returns_that_edge() -> None:
    log = EdgeLog(_writer())
    first = _ok(log.append(edge_type=EdgeType.PROMOTED_FROM, from_ref=_fp("a"), to_ref=_fp("b")))
    second = _ok(log.append(edge_type=EdgeType.PROMOTED_FROM, from_ref=_fp("c"), to_ref=_fp("d")))
    # Re-appending the SECOND edge (not the first) is idempotent and returns that edge —
    # the admitted-edge lookup scans past the first, non-matching edge.
    again = log.append(edge_type=EdgeType.PROMOTED_FROM, from_ref=_fp("c"), to_ref=_fp("d"))
    assert is_ok(again)
    assert again.value.outcome is WriteOutcome.IDEMPOTENT
    assert again.value.edge is second.edge
    assert again.value.edge is not first.edge
    assert log.edge_count() == 2


def test_idempotent_supersedes_reappend_is_not_a_linearity_violation() -> None:
    log = EdgeLog(_writer())
    v1, v2 = _fp("v1"), _fp("v2")
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v1))
    # The very same supersedes edge again is idempotent, not a "second edge" refusal.
    again = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v1)
    assert is_ok(again)
    assert again.value.outcome is WriteOutcome.IDEMPOTENT
    assert log.edge_count() == 1


def test_true_collision_is_refused_and_alarmed() -> None:
    log = EdgeLog(_writer())
    receipt = _ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=_fp("a"), to_ref=_fp("b")))
    digest = receipt.edge.edge_fingerprint.digest
    # A sha256 collision cannot arise naturally; tamper the content-addressed store so
    # the same edge fingerprint maps to different bytes, then re-append. The EdgeLog
    # composes qmf-core's FM-6 rule: differing bytes under one id are refused and
    # alarmed, never overwritten.
    log._bytes[digest] = b"different-stored-bytes"  # pyright: ignore[reportPrivateUsage]
    collision = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=_fp("a"), to_ref=_fp("b"))
    assert isinstance(collision, TypedRefusal)
    assert collision.category is RefusalCategory.POLICY_REJECTION
    assert collision.context["alarm"] is True


# --- AC6: exactly one writer, unlimited readers -----------------------------


def test_stream_has_exactly_one_writer() -> None:
    log = EdgeLog(_writer("node-a"))
    assert log.writer == _writer("node-a")
    # An edge stamped by another writer is refused: one writer per stream.
    foreign = _edge(writer=_writer("node-b"))
    refused = log.append_edge(foreign)
    _refused(refused, "writer", RefusalCategory.POLICY_REJECTION)
    assert log.edge_count() == 0


def test_append_edge_accepts_a_matching_prebuilt_edge() -> None:
    writer = _writer("node-a")
    log = EdgeLog(writer)
    edge = _edge(
        writer=writer, edge_type=EdgeType.ENACTS, from_ref=_fp("cmd"), to_ref=_fp("intent")
    )
    receipt = _ok(log.append_edge(edge))
    assert receipt.outcome is WriteOutcome.STORED
    assert receipt.edge is edge


def test_append_edge_refuses_a_non_edge() -> None:
    log = EdgeLog(_writer())
    _refused(log.append_edge("not-an-edge"), "edge", RefusalCategory.INVALID_INPUT)


def test_append_propagates_construction_refusal() -> None:
    log = EdgeLog(_writer())
    refused = log.append(edge_type="not-a-type", from_ref=_fp("a"), to_ref=_fp("b"))
    _refused(refused, "edge_type", RefusalCategory.INVALID_INPUT)


def test_readers_return_empty_on_malformed_lookup() -> None:
    log = EdgeLog(_writer())
    assert is_ok(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=_fp("a"), to_ref=_fp("b")))
    assert log.edges_from("not-a-fingerprint") == ()
    assert log.edges_to("not-a-fingerprint") == ()
    assert log.edges_of_type("not-a-type") == ()
    assert log.edges_from(_fp("a")) == (log.edges()[0],)
    assert log.edges_to(_fp("b")) == (log.edges()[0],)


def test_idempotent_reappend_returns_the_admitted_edge_via_index() -> None:
    # L4: the idempotent path resolves the admitted edge through the O(1) digest index and
    # returns the already-admitted edge object (never a fresh build, never a raise). The index
    # is rebuildable — after a rebuild the digest lookup is reconstructed and still resolves.
    log = EdgeLog(_writer())
    first = _ok(log.append(edge_type=EdgeType.OCCURRENCE_OF, from_ref=_fp("a"), to_ref=_fp("b")))
    assert first.outcome is WriteOutcome.STORED
    again = _ok(log.append(edge_type=EdgeType.OCCURRENCE_OF, from_ref=_fp("a"), to_ref=_fp("b")))
    assert again.outcome is WriteOutcome.IDEMPOTENT
    assert again.edge is first.edge  # the admitted edge object, resolved from the index
    log.rebuild_indexes()
    third = _ok(log.append(edge_type=EdgeType.OCCURRENCE_OF, from_ref=_fp("a"), to_ref=_fp("b")))
    assert third.outcome is WriteOutcome.IDEMPOTENT
    assert third.edge is first.edge  # the digest index was rebuilt, so it still resolves


def test_lineage_module_imports_only_qmf_core() -> None:
    source = Path(lineage_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    qmf_imports = {name for name in imported if name.startswith("qmf")}
    assert qmf_imports == {"qmf.core"}, qmf_imports
