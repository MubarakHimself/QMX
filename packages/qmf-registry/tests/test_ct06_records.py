"""CT-06 contract test — per-kind, fingerprint-keyed registration records (Story 2.1).

The Tier-1 contract test for the CT-06 boundary. Each acceptance criterion is asserted
against the real record/registry types, with every ``fp1`` fingerprint computed by
qmf-core:

* AC1 — a per-kind versioned record carries the tiny common header (kind, contract
  format version, at-birth parent refs, WriterId, per-writer sequence) plus a
  kind-specific body; there is no universal all-fields card.
* AC2 — the stable id is DERIVED from the record's fp1 fingerprint, never minted, and
  created-at / writer / sequence are excluded from identity, so identical work from two
  sandboxes deduplicates.
* AC3 — a byte-identical re-write is idempotent; a true collision is refused and
  alarmed, never overwritten (FM-6).
* AC4 — an unknown kind, a reserved kind, or a body field the kind's contract does not
  define is a typed refusal (FM-1); kinds are addable and never redefined.
* AC5 — at-birth parent refs stay in the header and are never unioned with CT-07 edges;
  the frozen record has nowhere for post-birth lineage to be written.
* AC6 — the module imports only qmf.core (default-deny).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmf.core import (
    Fingerprint,
    Instant,
    RefusalCategory,
    Result,
    TypedRefusal,
    WriterId,
    canonical_bytes,
    fingerprint,
    is_ok,
    is_refusal,
    reconcile_write,
)
from qmf.registry import (
    CONTRACT_FORMAT_VERSION,
    RESERVED_KIND_NAMES,
    FieldSetKind,
    KindContract,
    KindRegistry,
    Registrar,
    RegistrationReceipt,
    RegistrationRecord,
    WriteOutcome,
)
from qmf.registry import records as records_module

_CREATED_NS = 1_700_000_000_000_000_000

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(machine: str = "node-a", stream: str = "instrument-class") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", stream, "boot-1"))


def _fp(value: object) -> Fingerprint:
    return _ok(fingerprint(value))


def _kind() -> FieldSetKind:
    return _ok(
        FieldSetKind.try_create(
            "instrument-class",
            1,
            required_fields=["target_fp1", "asset_class"],
            optional_fields=["note"],
        )
    )


def _registry() -> KindRegistry:
    registry = KindRegistry()
    assert is_ok(registry.register(_kind()))
    return registry


def _body() -> dict[str, object]:
    return {"target_fp1": "EURUSD", "asset_class": "fx-major"}


def _record(**overrides: object) -> RegistrationRecord:
    args: dict[str, object] = {
        "kind": "instrument-class",
        "contract_format_version": 1,
        "at_birth_parent_refs": [],
        "body": _body(),
        "writer": _writer(),
        "sequence": 0,
        "created_at": _instant(),
    }
    args.update(overrides)
    return _ok(
        RegistrationRecord.try_create(
            args["kind"],
            args["contract_format_version"],
            args["at_birth_parent_refs"],
            args["body"],
            args["writer"],
            args["sequence"],
            args["created_at"],
        )
    )


# --- AC1: per-kind record + tiny common header ------------------------------


def test_record_carries_the_tiny_common_header_plus_a_body() -> None:
    record = _record(at_birth_parent_refs=[_fp({"parent": 1}).value])
    assert record.kind == "instrument-class"
    assert record.contract_format_version == 1
    assert record.at_birth_parent_refs == (_fp({"parent": 1}),)
    assert isinstance(record.writer, WriterId)
    assert record.sequence == 0
    assert record.body["asset_class"] == "fx-major"


def test_each_kind_is_its_own_contract_no_universal_card() -> None:
    # A body valid for one kind is refused for another whose field set differs; there
    # is no single all-fields card that accepts everything.
    other = _ok(FieldSetKind.try_create("strategy-family", 1, required_fields=["family_key"]))
    assert isinstance(other.validate_body(_body()), TypedRefusal)


def test_body_is_deep_frozen_against_later_mutation() -> None:
    mutable = {"target_fp1": "EURUSD", "asset_class": "fx-major"}
    record = _record(body=mutable)
    mutable["asset_class"] = "tampered"
    assert record.body["asset_class"] == "fx-major"


def test_body_with_nested_collections_is_deep_frozen() -> None:
    # A nested list in the body is frozen to a tuple, so a later mutation of the
    # caller's nested list cannot reach into the frozen record.
    nested = ["a", "b"]
    body: dict[str, object] = {"target_fp1": "EURUSD", "asset_class": "fx-major", "note": nested}
    kind = _ok(
        FieldSetKind.try_create(
            "instrument-class",
            1,
            required_fields=["target_fp1", "asset_class"],
            optional_fields=["note"],
        )
    )
    assert is_ok(kind.validate_body(body))
    record = _record(body=body)
    nested.append("c")
    assert record.body["note"] == ("a", "b")


def test_envelope_format_version_is_stamped_into_identity() -> None:
    record = _record()
    assert record.fp1_identity()["format_version"] == CONTRACT_FORMAT_VERSION


# --- AC2: derived stable id + occurrence facts excluded ---------------------


def test_stable_id_is_derived_from_fp1_never_minted() -> None:
    record = _record()
    assert record.stable_id.value.startswith("fp1:sha256:")
    # The derived id equals the fingerprint of the identity content (computed by
    # qmf-core); try_create accepts no caller-supplied id.
    assert record.stable_id == _fp(record.fp1_identity())


def test_identical_work_from_two_sandboxes_deduplicates() -> None:
    a = _record(writer=_writer("node-a"), sequence=0, created_at=_instant(_CREATED_NS))
    b = _record(writer=_writer("node-b"), sequence=99, created_at=_instant(_CREATED_NS + 500))
    assert a.writer != b.writer
    assert a.sequence != b.sequence
    assert a.created_at != b.created_at
    assert a.stable_id == b.stable_id  # occurrence facts excluded from identity


def test_occurrence_facts_are_absent_from_identity_content() -> None:
    identity = _record().fp1_identity()
    assert set(identity) == {
        "class",
        "kind",
        "contract_format_version",
        "at_birth_parent_refs",
        "body",
        "format_version",
    }


def test_a_different_kind_or_body_or_version_derives_a_different_id() -> None:
    base = _record()
    other_body = _record(body={"target_fp1": "GBPUSD", "asset_class": "fx-major"})
    other_version = _record(contract_format_version=2)
    assert other_body.stable_id != base.stable_id
    assert other_version.stable_id != base.stable_id


# --- AC5: at-birth refs are identity-bearing, order-insensitive, header-only -


def test_parent_refs_are_order_insensitive_and_deduplicated() -> None:
    p1 = _fp({"parent": 1}).value
    p2 = _fp({"parent": 2}).value
    forward = _record(at_birth_parent_refs=[p1, p2])
    reverse = _record(at_birth_parent_refs=[p2, p1])
    duplicated = _record(at_birth_parent_refs=[p2, p1, p1, p2])
    assert forward.stable_id == reverse.stable_id == duplicated.stable_id
    # Canonically ordered ascending in the header (DEC-0115 multiplicity ordering).
    assert [ref.value for ref in forward.header_parent_refs()] == sorted([p1, p2])


def test_parent_refs_are_identity_bearing() -> None:
    with_parent = _record(at_birth_parent_refs=[_fp({"parent": 1}).value])
    orphan = _record(at_birth_parent_refs=[])
    assert with_parent.stable_id != orphan.stable_id


def test_header_parent_refs_returns_only_at_birth_refs() -> None:
    # The frozen record has no field for post-birth lineage: header_parent_refs is
    # exactly the at-birth set, never unioned with CT-07 edges (Story 2.2).
    record = _record(at_birth_parent_refs=[_fp({"parent": 1}).value])
    assert record.header_parent_refs() == record.at_birth_parent_refs


# --- AC2/AC5: RegistrationRecord.try_create refusals -------------------------


def _refused(result: object, field: str) -> TypedRefusal:
    assert isinstance(result, TypedRefusal), result
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == field
    return result


def _try_record(**overrides: object) -> Result[RegistrationRecord]:
    args: dict[str, object] = {
        "kind": "instrument-class",
        "contract_format_version": 1,
        "at_birth_parent_refs": [],
        "body": _body(),
        "writer": _writer(),
        "sequence": 0,
        "created_at": _instant(),
    }
    args.update(overrides)
    return RegistrationRecord.try_create(
        args["kind"],
        args["contract_format_version"],
        args["at_birth_parent_refs"],
        args["body"],
        args["writer"],
        args["sequence"],
        args["created_at"],
    )


def test_record_refuses_blank_kind() -> None:
    _refused(_try_record(kind="  "), "kind")


def test_record_refuses_bad_contract_format_version() -> None:
    for bad in (0, -1, True, "1", 1.0):
        _refused(_try_record(contract_format_version=bad), "contract_format_version")


def test_record_refuses_malformed_parent_refs() -> None:
    _refused(_try_record(at_birth_parent_refs="fp1:sha256:x"), "at_birth_parent_refs")
    _refused(_try_record(at_birth_parent_refs=["not-a-fingerprint"]), "at_birth_parent_refs")


def test_record_refuses_non_mapping_body() -> None:
    _refused(_try_record(body=["not", "a", "map"]), "body")


def test_record_refuses_fp1_unclean_body() -> None:
    # A binary float in the body is not fp1-clean identity content; qmf-core refuses it
    # and the record surfaces it as a body refusal.
    _refused(_try_record(body={"target_fp1": "EURUSD", "weight": 1.5}), "body")


def test_record_refuses_bad_writer_sequence_and_created_at() -> None:
    _refused(_try_record(writer="node-a"), "writer")
    for bad_seq in (-1, True, "0"):
        _refused(_try_record(sequence=bad_seq), "sequence")
    _refused(_try_record(created_at=1_700_000_000), "created_at")


# --- AC4: FieldSetKind + KindRegistry (addable, never redefined) -------------


def test_field_set_kind_construction_refusals() -> None:
    assert isinstance(FieldSetKind.try_create("  ", 1), TypedRefusal)
    assert isinstance(FieldSetKind.try_create("k", 0), TypedRefusal)
    assert isinstance(FieldSetKind.try_create("k", 1, required_fields="oops"), TypedRefusal)
    assert isinstance(FieldSetKind.try_create("k", 1, required_fields=[""]), TypedRefusal)
    assert isinstance(FieldSetKind.try_create("k", 1, optional_fields=42), TypedRefusal)
    assert isinstance(
        FieldSetKind.try_create("k", 1, required_fields=["a"], optional_fields=["a"]),
        TypedRefusal,
    )


def test_field_set_kind_validate_body() -> None:
    kind = _kind()
    assert is_ok(kind.validate_body({"target_fp1": "EURUSD", "asset_class": "fx", "note": "x"}))
    unknown = kind.validate_body({"target_fp1": "EURUSD", "asset_class": "fx", "leverage": "50"})
    assert isinstance(unknown, TypedRefusal)
    # TypedRefusal deep-freezes its context, so the list becomes a tuple.
    assert unknown.context["unknown"] == ("leverage",)
    missing = kind.validate_body({"target_fp1": "EURUSD"})
    assert isinstance(missing, TypedRefusal)
    assert missing.context["missing"] == ("asset_class",)


def test_kind_registry_is_addable() -> None:
    registry = KindRegistry()
    assert is_ok(registry.register(_kind()))
    assert registry.known_kinds() == frozenset({"instrument-class"})
    assert is_ok(registry.contract_for("instrument-class"))


def test_kind_registry_never_redefines() -> None:
    registry = _registry()
    again = registry.register(_kind())
    assert isinstance(again, TypedRefusal)
    assert again.context["kind"] == "instrument-class"


def test_kind_registry_refuses_reserved_names_on_register() -> None:
    registry = KindRegistry()
    for name in RESERVED_KIND_NAMES:
        contract = _ok(FieldSetKind.try_create(name, 1, required_fields=["x"]))
        refused = registry.register(contract)
        assert isinstance(refused, TypedRefusal)
        assert refused.context["reserved"] is True


def test_kind_registry_register_refuses_malformed_contract() -> None:
    registry = KindRegistry()
    blank = FieldSetKind(
        name="  ",
        contract_format_version=1,
        required_fields=frozenset[str](),
        optional_fields=frozenset[str](),
    )
    assert isinstance(registry.register(blank), TypedRefusal)
    bad_version = FieldSetKind(
        name="k",
        contract_format_version=0,
        required_fields=frozenset[str](),
        optional_fields=frozenset[str](),
    )
    assert isinstance(registry.register(bad_version), TypedRefusal)


def test_contract_for_unknown_and_reserved_and_blank() -> None:
    registry = _registry()
    unknown = registry.contract_for("no-such-kind")
    assert isinstance(unknown, TypedRefusal)
    assert unknown.context["kind"] == "no-such-kind"
    reserved = registry.contract_for("promotion-occurrence-card")
    assert isinstance(reserved, TypedRefusal)
    assert reserved.context["reserved"] is True
    assert isinstance(registry.contract_for("  "), TypedRefusal)


def test_is_reserved_and_reserved_names_honored() -> None:
    registry = KindRegistry()
    assert registry.is_reserved("promotion-occurrence-card")
    assert registry.is_reserved("treasury-boundary-event")
    assert not registry.is_reserved("instrument-class")
    assert not registry.is_reserved(123)
    assert RESERVED_KIND_NAMES == frozenset(
        {"promotion-occurrence-card", "treasury-boundary-event"}
    )


def test_field_set_kind_satisfies_the_kind_contract_protocol() -> None:
    assert isinstance(_kind(), KindContract)


# --- AC3 + AC4: Registrar (kind check, derivation, FM-6) --------------------


def test_registrar_stores_then_idempotent_rewrite() -> None:
    registrar = Registrar(_registry())
    first = registrar.register(
        kind="instrument-class", body=_body(), writer=_writer(), sequence=0, created_at=_instant()
    )
    assert is_ok(first)
    assert isinstance(first.value, RegistrationReceipt)
    assert first.value.outcome is WriteOutcome.STORED
    again = registrar.register(
        kind="instrument-class",
        body=_body(),
        writer=_writer("node-b"),
        sequence=7,
        created_at=_instant(_CREATED_NS + 900),
    )
    assert is_ok(again)
    assert again.value.outcome is WriteOutcome.IDEMPOTENT
    assert registrar.stable_ids() == {first.value.record.stable_id.value}


def test_registrar_refuses_true_collision_and_alarms() -> None:
    registrar = Registrar(_registry())
    first = registrar.register(
        kind="instrument-class", body=_body(), writer=_writer(), sequence=0, created_at=_instant()
    )
    assert is_ok(first)
    digest = first.value.record.stable_id.digest
    # A sha256 collision cannot arise naturally; tamper the content-addressed store so
    # the same stable id maps to different bytes, then re-register. The Registrar
    # composes qmf-core's FM-6 rule: differing bytes under one id are refused and
    # alarmed, never overwritten.
    registrar._bytes[digest] = b"different-stored-bytes"  # pyright: ignore[reportPrivateUsage]
    collision = registrar.register(
        kind="instrument-class", body=_body(), writer=_writer(), sequence=0, created_at=_instant()
    )
    assert isinstance(collision, TypedRefusal)
    assert collision.category is RefusalCategory.POLICY_REJECTION
    assert collision.context["alarm"] is True


def test_registrar_refuses_unknown_and_reserved_kinds() -> None:
    registrar = Registrar(_registry())
    unknown = registrar.register(
        kind="no-such-kind", body=_body(), writer=_writer(), sequence=0, created_at=_instant()
    )
    assert isinstance(unknown, TypedRefusal)
    reserved = registrar.register(
        kind="promotion-occurrence-card",
        body=_body(),
        writer=_writer(),
        sequence=0,
        created_at=_instant(),
    )
    assert isinstance(reserved, TypedRefusal)
    assert reserved.context["reserved"] is True


def test_registrar_refuses_bad_field_and_non_mapping_body() -> None:
    registrar = Registrar(_registry())
    bad_field = registrar.register(
        kind="instrument-class",
        body={"target_fp1": "EURUSD", "asset_class": "fx", "leverage": "50"},
        writer=_writer(),
        sequence=0,
        created_at=_instant(),
    )
    assert isinstance(bad_field, TypedRefusal)
    non_mapping = registrar.register(
        kind="instrument-class", body=["nope"], writer=_writer(), sequence=0, created_at=_instant()
    )
    assert isinstance(non_mapping, TypedRefusal)
    assert non_mapping.context["field"] == "body"


def test_registrar_refuses_bad_header_parts_from_register() -> None:
    registrar = Registrar(_registry())
    bad_writer = registrar.register(
        kind="instrument-class", body=_body(), writer="node-a", sequence=0, created_at=_instant()
    )
    assert isinstance(bad_writer, TypedRefusal)
    assert bad_writer.context["field"] == "writer"


def test_registrar_record_for_hit_miss_and_malformed() -> None:
    registrar = Registrar(_registry())
    receipt = registrar.register(
        kind="instrument-class", body=_body(), writer=_writer(), sequence=0, created_at=_instant()
    )
    assert is_ok(receipt)
    stable_id = receipt.value.record.stable_id
    assert registrar.record_for(stable_id) is receipt.value.record
    assert registrar.record_for(stable_id.value) is receipt.value.record
    assert registrar.record_for(_fp({"never": "stored"})) is None
    assert registrar.record_for("not-a-fingerprint") is None


# --- AC3: the pure FM-6 rule the Registrar composes -------------------------


def test_pure_reconcile_rule_matches_the_registrar() -> None:
    record = _record()
    canonical = canonical_bytes(record.fp1_identity())
    assert is_ok(canonical)
    assert is_ok(reconcile_write(record.stable_id, canonical.value, None))
    assert is_ok(reconcile_write(record.stable_id, canonical.value, canonical.value))
    assert is_refusal(reconcile_write(record.stable_id, canonical.value, b"other"))


# --- AC6: default-deny import discipline ------------------------------------


def test_records_module_imports_only_qmf_core() -> None:
    source = Path(records_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    qmf_imports = {name for name in imported if name.startswith("qmf")}
    assert qmf_imports == {"qmf.core"}, qmf_imports
