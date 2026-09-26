"""Reference usage — CT-07 append-only typed lineage edges (COMP-QMF-REGISTRY).

Executable::

    python packages/qmf-registry/examples/lineage_usage.py

Shows the six things CT-07 pins down:

1. A typed edge references BOTH endpoints by their fp1 fingerprint and carries an
   edge_type from the ratified V1 set; its edge fingerprint is DERIVED from the identity
   content, and it serializes to the pinned JSONL line — one fp1-canonical JSON object,
   LF-terminated.
2. supersedes is pinned linear: a chain resolves to one unambiguous "current" head, and
   a second supersedes edge for a subject is refused.
3. branches-from is not linear: several branches-from edges from one subject are all
   legal, because a branching graph's "current" is a separate dated pointer record.
4. A byte-identical re-append is accepted silently (idempotent); a true collision (same
   edge fingerprint, differing bytes) is refused and alarmed.
5. An edge type outside the ratified set, and an endpoint that is not an fp1 fingerprint,
   are each typed refusals (FM-2); edge types are addable, never redefined.
6. An edge stream has exactly one writer; every fp1 fingerprint is computed in qmf-core,
   and this module imports only qmf.core.
"""

from __future__ import annotations

import json
from typing import TypeVar

from qmf.core import (
    Fingerprint,
    Result,
    TypedRefusal,
    WriterId,
    fingerprint,
    is_ok,
)
from qmf.registry import (
    EdgeLog,
    EdgeType,
    LineageEdge,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _writer(machine: str) -> WriterId:
    return _unwrap(WriterId.try_create(machine, "authoring", "lineage", "boot-1"), "writer")


def _rec(tag: str) -> Fingerprint:
    """A stand-in fp1 fingerprint for a registered record."""
    return _unwrap(fingerprint({"rec": tag}), f"record {tag}")


def typed_edge_and_its_jsonl_line() -> bytes:
    """A typed edge over fp1 endpoints, with a derived id and a pinned JSONL line."""
    edge = _unwrap(
        LineageEdge.try_create(
            EdgeType.PROMOTED_FROM, _rec("promoted"), _rec("source"), _writer("node-a")
        ),
        "promoted-from edge",
    )
    # The id is derived, not minted: it equals the fingerprint of the identity content.
    assert edge.edge_fingerprint == _unwrap(fingerprint(edge.fp1_identity()), "derived id")
    line = _unwrap(edge.canonical_line(), "canonical line")
    assert line.endswith(b"\n")
    parsed = json.loads(line)
    assert parsed["edge_type"] == "promoted-from"
    assert parsed["from_ref"] == edge.from_ref.value
    return line


def supersedes_is_linear() -> tuple[str, str]:
    """A supersedes chain resolves to one head; a second edge for a subject is refused."""
    log = EdgeLog(_writer("node-a"))
    v1, v2, v3 = _rec("v1"), _rec("v2"), _rec("v3")
    _unwrap(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v2, to_ref=v1), "v2 supersedes v1")
    _unwrap(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=v3, to_ref=v2), "v3 supersedes v2")
    head = _unwrap(log.current_head(v1), "current head of v1")
    assert head == v3  # one unambiguous "current"
    # A second superseder of v1 would fork "current" — refused.
    fork = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=_rec("rogue"), to_ref=v1)
    assert isinstance(fork, TypedRefusal)
    return head.value, fork.category.value


def branches_from_allows_several_heads() -> int:
    """Several branches-from edges from one subject are all legal."""
    log = EdgeLog(_writer("node-a"))
    child = _rec("child")
    _unwrap(
        log.append(edge_type=EdgeType.BRANCHES_FROM, from_ref=child, to_ref=_rec("branch-a")),
        "branch a",
    )
    _unwrap(
        log.append(edge_type=EdgeType.BRANCHES_FROM, from_ref=child, to_ref=_rec("branch-b")),
        "branch b",
    )
    return len(log.edges_from(child))


def idempotent_accept_but_collision_refused() -> tuple[str, TypedRefusal]:
    """A byte-identical re-append is idempotent; a true collision is refused and alarmed."""
    log = EdgeLog(_writer("node-a"))
    first = _unwrap(
        log.append(edge_type=EdgeType.CORROBORATES, from_ref=_rec("src-a"), to_ref=_rec("src-b")),
        "first append",
    )
    again = _unwrap(
        log.append(edge_type=EdgeType.CORROBORATES, from_ref=_rec("src-a"), to_ref=_rec("src-b")),
        "idempotent re-append",
    )
    assert again.outcome.value == "idempotent"
    # A true collision: the same edge fingerprint already mapping to different stored
    # bytes is refused and alarmed, never overwritten. A sha256 collision cannot arise
    # naturally, so it is forced by tampering the content-addressed store.
    digest = first.edge.edge_fingerprint.digest
    log._bytes[digest] = b"different-stored-bytes"  # pyright: ignore[reportPrivateUsage]
    collision = log.append(
        edge_type=EdgeType.CORROBORATES, from_ref=_rec("src-a"), to_ref=_rec("src-b")
    )
    assert isinstance(collision, TypedRefusal)
    assert collision.context["alarm"] is True
    return first.outcome.value, collision


def bad_type_and_non_fp1_endpoint_are_refused() -> tuple[TypedRefusal, TypedRefusal]:
    """An edge type outside the ratified set and a non-fp1 endpoint are FM-2 refusals."""
    bad_type = LineageEdge.try_create("merged-into", _rec("a"), _rec("b"), _writer("node-a"))
    assert isinstance(bad_type, TypedRefusal)
    non_fp1 = LineageEdge.try_create(EdgeType.SUPERSEDES, "record-42", _rec("b"), _writer("node-a"))
    assert isinstance(non_fp1, TypedRefusal)
    return bad_type, non_fp1


def one_writer_per_stream() -> TypedRefusal:
    """An edge stamped by another writer is refused: one writer per stream."""
    log = EdgeLog(_writer("node-a"))
    foreign = _unwrap(
        LineageEdge.try_create(EdgeType.ENACTS, _rec("cmd"), _rec("intent"), _writer("node-b")),
        "foreign-writer edge",
    )
    refused = log.append_edge(foreign)
    assert isinstance(refused, TypedRefusal)
    return refused


def main() -> None:
    line = typed_edge_and_its_jsonl_line()
    print(f"typed edge JSONL line, LF-terminated: {line.endswith(chr(10).encode())}")

    head, fork_category = supersedes_is_linear()
    print(f"supersedes head resolves to one current: {head[:19]}...")
    print(f"second supersedes for a subject refused: {fork_category}")

    branches = branches_from_allows_several_heads()
    print(f"branches-from allows several heads: {branches}")

    outcome, collision = idempotent_accept_but_collision_refused()
    print(f"first append outcome: {outcome}")
    print(f"true collision refused and alarmed: {collision.category.value}")

    bad_type, non_fp1 = bad_type_and_non_fp1_endpoint_are_refused()
    print(f"edge type outside the set refused: {bad_type.category.value}")
    print(f"non-fp1 endpoint refused: {non_fp1.category.value}")

    foreign = one_writer_per_stream()
    print(f"foreign writer refused (one writer per stream): {foreign.category.value}")


if __name__ == "__main__":
    main()
