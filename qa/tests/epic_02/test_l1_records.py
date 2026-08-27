"""L1 — unit assertions for CT-06 records (FR-006, P0-4).

E2-L1-01  undefined kind / field-set => typed refusal (FM-1), never raises
E2-L1-02  well-formed registration succeeds; stable_id == fp1(canonical content)
E2-L1-03  occurrence facts excluded from identity => dedup by construction
E2-L1-04  changing any identity-bearing field => different stable_id  (P0-4)
E2-L1-05  a true fp1 collision is refused and alarmed, never overwritten  (P0-4)
E2-L1-06  a byte-identical idempotent re-write is accepted silently
"""

from __future__ import annotations

from qmf.core import (
    RefusalCategory,
    WriteOutcome,
    canonical_bytes,
    fingerprint,
    is_ok,
    is_refusal,
    reconcile_write,
)

import helpers as h


# --- E2-L1-01 : FM-1 undefined kind / field is a returned typed refusal --------


def test_e2_l1_01_unknown_kind_is_typed_refusal_not_raise() -> None:
    reg = h.registrar()
    out = reg.register(kind="not-registered", body={"id": "x"}, writer=h.writer(),
                       sequence=0, created_at=h.instant())
    assert is_refusal(out)
    assert out.category is RefusalCategory.INVALID_INPUT


def test_e2_l1_01_undefined_body_field_is_typed_refusal() -> None:
    reg = h.registrar()
    out = reg.register(kind="producer", body={"id": "x", "unknown_field": 1},
                       writer=h.writer(), sequence=0, created_at=h.instant())
    assert is_refusal(out)
    assert out.category is RefusalCategory.INVALID_INPUT
    assert out.context.get("field") == "body"


# --- E2-L1-02 : stable id is DERIVED from fp1, never minted --------------------


def test_e2_l1_02_stable_id_equals_fp1_over_canonical_content() -> None:
    reg = h.registrar()
    out = reg.register(kind="producer", body={"id": "sma-20", "period": 20},
                       writer=h.writer(), sequence=0, created_at=h.instant())
    receipt = h.unwrap(out, "register")
    assert receipt.outcome is WriteOutcome.STORED
    rec = receipt.record
    # The stable id IS the fp1 over the record's canonical identity content.
    recomputed = h.unwrap(fingerprint(rec.fp1_identity()), "fp1")
    assert rec.stable_id == recomputed
    assert rec.stable_id.value.startswith("fp1:sha256:")


# --- E2-L1-03 : occurrence facts excluded from identity => dedup ---------------


def test_e2_l1_03_occurrence_facts_excluded_from_identity() -> None:
    body = {"id": "sma-20", "period": 20}
    a = h.record(body, writer_id=h.writer("node-a"), sequence=0, ns=1_700_000_000_000_000_000)
    b = h.record(body, writer_id=h.writer("node-b"), sequence=99, ns=1_900_000_000_000_000_000)
    # Different writer, sequence, created_at — same computation identity => same stable id.
    assert a.stable_id == b.stable_id


# --- E2-L1-04 (P0) : distinct semantics => distinct fp1 ------------------------


def test_e2_l1_04_changing_any_identity_field_changes_stable_id() -> None:
    base = h.record({"id": "sma-20", "period": 20})
    variants = [
        h.record({"id": "sma-20", "period": 20}, kind="consumer"),        # kind
        h.record({"id": "sma-20", "period": 20}, version=2),               # contract version
        h.record({"id": "sma-20", "period": 21}),                          # body value
        h.record({"id": "sma-20", "period": 20}, parents=[h.fp("p1")]),    # at-birth parent
    ]
    for v in variants:
        assert v.stable_id != base.stable_id, f"identity change did not change stable id: {v.kind}"
    # All four variants are pairwise distinct too.
    ids = {base.stable_id.value} | {v.stable_id.value for v in variants}
    assert len(ids) == 1 + len(variants)


# --- E2-L1-05 (P0) : a true fp1 collision is refused and alarmed ---------------


def test_e2_l1_05_true_collision_refused_and_alarmed() -> None:
    # The FM-6 identity decision the Registrar composes: one fp1 addressing DIFFERING
    # canonical bytes is a true collision — refused (policy rejection) and alarmed,
    # never overwritten. (Distinct contents cannot share a stable id through the public
    # register() path, so the identity decision itself is exercised here; the
    # store-boundary variant is E2-L4-07.)
    rec = h.record({"id": "x"})
    canonical = h.unwrap(canonical_bytes(rec.fp1_identity()), "canonical")
    differing = canonical + b" "  # same presented fp1, different bytes
    decision = reconcile_write(rec.stable_id, canonical, differing)
    assert is_refusal(decision)
    assert decision.category is RefusalCategory.POLICY_REJECTION
    assert decision.context.get("alarm") is True


# --- E2-L1-06 : byte-identical idempotent re-write accepted silently -----------


def test_e2_l1_06_idempotent_rewrite_accepted_silently() -> None:
    reg = h.registrar()
    kw = dict(kind="producer", body={"id": "sma-20", "period": 20},
              writer=h.writer(), sequence=0, created_at=h.instant())
    first = h.unwrap(reg.register(**kw), "first")
    assert first.outcome is WriteOutcome.STORED
    # A byte-identical re-write (same identity) is idempotent — no error, no duplicate.
    second = h.unwrap(reg.register(**kw), "second")
    assert second.outcome is WriteOutcome.IDEMPOTENT
    assert second.record.stable_id == first.record.stable_id
    assert len(reg.stable_ids()) == 1
