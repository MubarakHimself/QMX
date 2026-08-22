"""Reference usage — CT-06 per-kind, fingerprint-keyed registration records
(COMP-QMF-REGISTRY).

Executable::

    python packages/qmf-registry/examples/records_usage.py

Shows the six things CT-06 pins down:

1. A per-kind versioned record — its own contract, a tiny common header plus a
   kind-specific body — with no universal all-fields card. The stable id is DERIVED
   from the record's fp1 fingerprint (``fp1:sha256:<hex>``), never minted.
2. Identical work from two sandboxes deduplicates: different writers, sequences, and
   created-at instants, same kind + parents + body, one stable id.
3. At-birth parent references are identity-bearing but order-insignificant — the same
   parents in a different order derive the same id — while different parents derive a
   different id, and they stay in the header (never unioned with CT-07 edges).
4. A byte-identical re-registration is accepted silently (idempotent); a true
   collision (same fp1 stable id, differing bytes) is refused and alarmed.
5. An unknown kind, a reserved kind, and a body field the kind's contract does not
   define are each typed refusals (FM-1); kinds are addable and never redefined.
6. Every fp1 fingerprint is computed in qmf-core, and this module imports only
   qmf.core.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Instant,
    Result,
    TypedRefusal,
    WriterId,
    canonical_bytes,
    fingerprint,
    is_ok,
    reconcile_write,
)
from qmf.registry import (
    FieldSetKind,
    KindRegistry,
    Registrar,
    RegistrationRecord,
)

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _kinds() -> KindRegistry:
    """A registry with one addable kind: an AD-9 dated metadata record."""
    registry = KindRegistry()
    contract = _unwrap(
        FieldSetKind.try_create(
            "instrument-class",
            1,
            required_fields=["target_fp1", "asset_class"],
            optional_fields=["note"],
        ),
        "instrument-class kind",
    )
    _unwrap(registry.register(contract), "register instrument-class")
    return registry


def _writer(machine: str) -> WriterId:
    return _unwrap(
        WriterId.try_create(machine, "authoring", "instrument-class", "boot-1"), "writer"
    )


def per_kind_record_has_derived_id() -> RegistrationRecord:
    """A per-kind record whose stable id is derived from its fp1 fingerprint."""
    registrar = Registrar(_kinds())
    receipt = _unwrap(
        registrar.register(
            kind="instrument-class",
            body={"target_fp1": "EURUSD", "asset_class": "fx-major"},
            writer=_writer("node-a"),
            sequence=0,
            created_at=_unwrap(Instant.try_create(1_700_000_000_000_000_000), "created-at"),
        ),
        "first registration",
    )
    record = receipt.record
    # The id is derived, not minted: it equals the fingerprint of the identity content.
    assert record.stable_id.value.startswith("fp1:sha256:")
    assert record.stable_id == _unwrap(fingerprint(record.fp1_identity()), "derived id")
    assert receipt.outcome.value == "stored"
    return record


def two_sandboxes_deduplicate() -> tuple[str, str]:
    """Identical work from two sandboxes lands on one stable id."""
    body = {"target_fp1": "EURUSD", "asset_class": "fx-major"}
    a = _unwrap(
        RegistrationRecord.try_create(
            "instrument-class",
            1,
            [],
            body,
            _writer("node-a"),
            0,
            _unwrap(Instant.try_create(1_700_000_000_000_000_000), "a created-at"),
        ),
        "sandbox-a record",
    )
    b = _unwrap(
        RegistrationRecord.try_create(
            "instrument-class",
            1,
            [],
            body,
            _writer("node-b"),
            99,
            _unwrap(Instant.try_create(1_700_000_500_000_000_000), "b created-at"),
        ),
        "sandbox-b record",
    )
    # Different writer, sequence, and created-at; one stable id.
    assert a.stable_id == b.stable_id
    assert a.writer != b.writer
    return a.stable_id.value, b.stable_id.value


def parent_refs_are_order_insensitive_but_identity_bearing() -> None:
    """Same parents in any order derive one id; different parents derive another."""
    p1 = _unwrap(fingerprint({"parent": 1}), "parent-1").value
    p2 = _unwrap(fingerprint({"parent": 2}), "parent-2").value
    body = {"target_fp1": "EURUSD", "asset_class": "fx-major"}
    writer = _writer("node-a")
    at = _unwrap(Instant.try_create(1_700_000_000_000_000_000), "created-at")
    forward = _unwrap(
        RegistrationRecord.try_create("instrument-class", 1, [p1, p2], body, writer, 0, at),
        "forward-order record",
    )
    reverse = _unwrap(
        RegistrationRecord.try_create("instrument-class", 1, [p2, p1], body, writer, 0, at),
        "reverse-order record",
    )
    orphan = _unwrap(
        RegistrationRecord.try_create("instrument-class", 1, [], body, writer, 0, at),
        "no-parent record",
    )
    assert forward.stable_id == reverse.stable_id  # order-insignificant
    assert forward.stable_id != orphan.stable_id  # identity-bearing
    # At-birth references live in the header, canonically ordered, never unioned with
    # CT-07 edges (which are Story 2.2).
    assert [ref.value for ref in forward.header_parent_refs()] == sorted([p1, p2])


def idempotent_accept_but_collision_refused() -> TypedRefusal:
    """A byte-identical re-registration is idempotent; a true collision is refused."""
    registrar = Registrar(_kinds())
    args = {
        "kind": "instrument-class",
        "body": {"target_fp1": "EURUSD", "asset_class": "fx-major"},
        "writer": _writer("node-a"),
        "sequence": 0,
        "created_at": _unwrap(Instant.try_create(1_700_000_000_000_000_000), "created-at"),
    }
    first = _unwrap(registrar.register(**args), "first write")
    assert first.outcome.value == "stored"
    # A re-write of byte-identical content — even from a different writer/sequence —
    # dedups to the same id and is accepted silently.
    again = _unwrap(
        registrar.register(
            kind="instrument-class",
            body={"target_fp1": "EURUSD", "asset_class": "fx-major"},
            writer=_writer("node-b"),
            sequence=7,
            created_at=_unwrap(Instant.try_create(1_700_000_900_000_000_000), "later created-at"),
        ),
        "idempotent re-write",
    )
    assert again.outcome.value == "idempotent"

    # A true collision: the same fp1 stable id already mapping to different stored
    # bytes is refused and alarmed, never overwritten. A sha256 collision cannot arise
    # naturally, so the rule itself is shown through qmf-core's pure decision — the same
    # rule the Registrar composes over its content-addressed store (FM-6).
    stored_bytes = _unwrap(canonical_bytes(first.record.fp1_identity()), "stored bytes")
    collision = reconcile_write(first.record.stable_id, stored_bytes, b"different-stored-bytes")
    assert isinstance(collision, TypedRefusal)
    assert collision.category.value == "policy rejection"
    assert collision.context["alarm"] is True
    return collision


def unknown_reserved_and_bad_field_are_refused() -> tuple[TypedRefusal, TypedRefusal, TypedRefusal]:
    """An unknown kind, a reserved kind, and an undefined body field are all FM-1."""
    registrar = Registrar(_kinds())
    common = {
        "body": {"target_fp1": "EURUSD", "asset_class": "fx-major"},
        "writer": _writer("node-a"),
        "sequence": 0,
        "created_at": _unwrap(Instant.try_create(1_700_000_000_000_000_000), "created-at"),
    }
    unknown = registrar.register(kind="no-such-kind", **common)
    assert isinstance(unknown, TypedRefusal)
    reserved = registrar.register(kind="promotion-occurrence-card", **common)
    assert isinstance(reserved, TypedRefusal)
    assert reserved.context["reserved"] is True
    bad_field = registrar.register(
        kind="instrument-class",
        body={"target_fp1": "EURUSD", "asset_class": "fx-major", "leverage": "50"},
        writer=_writer("node-a"),
        sequence=0,
        created_at=_unwrap(Instant.try_create(1_700_000_000_000_000_000), "created-at"),
    )
    assert isinstance(bad_field, TypedRefusal)
    return unknown, reserved, bad_field


def main() -> None:
    record = per_kind_record_has_derived_id()
    print(f"per-kind record, derived id: {record.stable_id.value[:19]}...")

    id_a, id_b = two_sandboxes_deduplicate()
    print(f"two sandboxes deduplicate: {id_a == id_b}")

    parent_refs_are_order_insensitive_but_identity_bearing()
    print("at-birth parent refs: order-insensitive, identity-bearing, header-only")

    collision = idempotent_accept_but_collision_refused()
    print(f"true collision refused and alarmed: {collision.category.value}")

    unknown, reserved, bad_field = unknown_reserved_and_bad_field_are_refused()
    print(f"unknown kind refused: {unknown.category.value}")
    print(f"reserved kind honored (refused): {reserved.category.value}")
    print(f"undefined body field refused: {bad_field.category.value}")


if __name__ == "__main__":
    main()
