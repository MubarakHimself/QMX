"""L3 — contract (owner-conformance) tests for CT-06 / CT-07 / CT-09 / CT-04 / CT-05.

E2-L3-01  CT-06 round-trip — canonical encode/decode semantic equality
E2-L3-02  (P0) CT-06 boundary — unknown kind; missing required field; fp1-derived id;
          human-only promotion occurrence attesting the record fp1; format-version stamp
E2-L3-03  CT-07 round-trip — all 14 enum types accepted; pinned-JSONL shape
E2-L3-04  CT-07 boundary — non-fp1 endpoint refusal; idempotent re-append;
          rebuildable index (drop -> rebuild reproduces the edge view)
E2-L3-05  (P0) CT-09 round-trip — persist through the qmf-data seam, read back equal
E2-L3-07  CT-04 conformance — every returned refusal is one of the seven categories
E2-L3-08  CT-05 as-consumed — the stable id derives from the CONTENT fp1
"""

from __future__ import annotations

import json

from qmf.core import (
    Fingerprint,
    RefusalCategory,
    World,
    canonical_bytes,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.registry import (
    EdgeLog,
    EdgeType,
    LineageEdge,
    PromotionCard,
    authorize_live_promotion,
    persistence_fingerprint,
)

import helpers as h

_SEVEN = {c.value for c in RefusalCategory}


def test_e2_l3_01_ct06_record_canonical_round_trip() -> None:
    rec = h.record({"id": "sma-20", "period": 20}, parents=[h.fp("p1")])
    canonical = h.unwrap(canonical_bytes(rec.fp1_identity()), "canonical")
    decoded = json.loads(canonical)
    # Semantic equality: decoding the canonical bytes reproduces the identity content.
    assert decoded == json.loads(json.dumps(rec.fp1_identity(), default=str))
    # And re-fingerprinting the decoded content reproduces the stable id.
    assert h.unwrap(fingerprint(decoded), "refp") == rec.stable_id


def test_e2_l3_02_ct06_boundary_conditions() -> None:
    reg = h.registrar()
    # unknown kind
    assert is_refusal(reg.register(kind="ghost", body={"id": "x"}, writer=h.writer(),
                                   sequence=0, created_at=h.instant()))
    # missing required field
    reg2 = h.registrar(required=("id",), optional=("period",))
    assert is_refusal(reg2.register(kind="producer", body={"period": 1}, writer=h.writer(),
                                    sequence=0, created_at=h.instant()))
    # fp1-derived stable id + CT-06 envelope format-version stamped
    rec = h.record({"id": "x"})
    assert rec.fp1_identity()["format_version"] == 1
    assert rec.stable_id == h.unwrap(fingerprint(rec.fp1_identity()), "fp")
    # human-only promotion occurrence attesting the record's fp1
    card = h.unwrap(
        PromotionCard.sign(signer="operator:mubarak", plain_words_summary="ship it",
                           attested_fp1=rec.stable_id, writer=h.writer(), sequence=0,
                           signed_at=h.instant()),
        "card",
    )
    assert card.attests(rec.stable_id)
    ok = authorize_live_promotion(target_fp1=rec.stable_id, card=card, superseded=[])
    assert is_ok(ok)


def test_e2_l3_03_ct07_all_fourteen_types_round_trip() -> None:
    for et in EdgeType:
        edge = h.unwrap(LineageEdge.try_create(et, h.fp("a"), h.fp("b"), h.writer()), et.value)
        line = h.unwrap(edge.canonical_line(), "line")
        obj = json.loads(line[:-1])
        assert obj["edge_type"] == et.value
        # Re-create from the pinned line's fields => same edge fingerprint (total round trip).
        rebuilt = h.unwrap(
            LineageEdge.try_create(obj["edge_type"], obj["from_ref"], obj["to_ref"],
                                   edge.writer, obj["contract_format_version"]),
            "rebuilt",
        )
        assert rebuilt.edge_fingerprint == edge.edge_fingerprint


def test_e2_l3_04_ct07_boundary_and_rebuildable_index() -> None:
    log = EdgeLog(h.writer())
    a, b, c = h.fp("A"), h.fp("B"), h.fp("C")
    # non-fp1 endpoint refusal
    assert is_refusal(log.append(edge_type=EdgeType.SUPERSEDES, from_ref="x", to_ref=b))
    # a supersedes chain A<-B<-C (B supersedes A, C supersedes B)
    h.unwrap(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=b, to_ref=a), "b>a")
    h.unwrap(log.append(edge_type=EdgeType.SUPERSEDES, from_ref=c, to_ref=b), "c>b")
    head_before = h.unwrap(log.current_head(a), "head")
    edges_before = log.edges()
    # idempotent re-append is accepted
    again = log.append(edge_type=EdgeType.SUPERSEDES, from_ref=b, to_ref=a)
    assert is_ok(again) and again.value.outcome.value == "idempotent"
    # rebuildable index: drop the derived indexes and rebuild => identical view.
    log.rebuild_indexes()
    assert log.current_head(a) == log.current_head(a)
    assert h.unwrap(log.current_head(a), "head-after") == head_before
    assert log.edges() == edges_before  # evidence untouched by an index rebuild


def test_e2_l3_05_ct09_round_trip_through_the_store_seam(tmp_path) -> None:
    p = h.live_persistence(tmp_path)
    rec = h.record({"id": "sma-20", "period": 20}, parents=[h.fp("p1")])
    receipt = h.unwrap(p.persist_record(rec), "persist")
    assert receipt.fingerprint == rec.stable_id
    loaded = h.unwrap(p.load_record(receipt.fingerprint, for_world=World.LIVE), "load")
    assert loaded.stable_id == rec.stable_id
    assert dict(loaded.body) == {"id": "sma-20", "period": 20}
    assert loaded.at_birth_parent_refs == rec.at_birth_parent_refs


def test_e2_l3_07_ct04_refusals_are_the_seven_categories_returned() -> None:
    reg = h.registrar()
    probes = [
        reg.register(kind="ghost", body={"id": "x"}, writer=h.writer(), sequence=0,
                     created_at=h.instant()),
        LineageEdge.try_create("bad", h.fp("a"), h.fp("b"), h.writer()),
        authorize_live_promotion(target_fp1=h.fp("t").value, card=None, superseded=[]),
        persistence_fingerprint(object()),
    ]
    for out in probes:
        assert is_refusal(out)
        assert out.category.value in _SEVEN
        assert out.retryability is not None
        assert out.context is not None


def test_e2_l3_08_ct05_stable_id_is_the_content_fp1_not_a_wrapper() -> None:
    rec = h.record({"id": "x", "period": 3})
    # persistence_fingerprint (the CT-09 storage key) IS the record's content fp1 stable id,
    # never a second fingerprint wrapping the record envelope (CT-05 as-consumed).
    key = h.unwrap(persistence_fingerprint(rec), "key")
    assert key == rec.stable_id
    assert key == h.unwrap(fingerprint(rec.fp1_identity()), "content fp1")
