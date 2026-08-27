"""L2 — property / invariant tests (CT-05, CT-07, P0-4, P0-5).

E2-L2-01  (P0) distinct semantic contents => distinct fp1 (injective identity)
E2-L2-02  (P0) fp1 invariant under key reorder / occurrence-field variation
E2-L2-03  identity content containing a float is refused
E2-L2-04  (P0) the edge log is append-only and order-preserving
E2-L2-05  (P0) any promotion attempt with no signed card never enters live
E2-L2-06  one writer per stream; a second writer is rejected

A declared, derandomized seed is used so any failure reproduces (no system RNG).
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core import RefusalCategory, WriteOutcome, canonical_bytes, fingerprint, is_ok, is_refusal
from qmf.registry import EdgeLog, EdgeType, LineageEdge, authorize_live_promotion

import helpers as h

_SETTINGS = settings(
    max_examples=150,
    derandomize=True,  # declared, reproducible — never the system RNG
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)

# fp1-clean identity content: non-blank string keys (canonical_bytes refuses blank/
# whitespace-only keys), int/str leaf values (no floats, no null). Keys use printable,
# non-space ASCII so no generated key is whitespace-only.
_clean_keys = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=6
)
_clean_scalars = st.one_of(st.integers(min_value=-(10**9), max_value=10**9), st.text(max_size=8))
_clean_dicts = st.dictionaries(_clean_keys, _clean_scalars, max_size=5)


@_SETTINGS
@given(a=_clean_dicts, b=_clean_dicts)
def test_e2_l2_01_distinct_semantics_distinct_fp1(a: dict, b: dict) -> None:
    ca = canonical_bytes(a)
    cb = canonical_bytes(b)
    assert is_ok(ca) and is_ok(cb)
    fa = h.unwrap(fingerprint(a), "fa")
    fb = h.unwrap(fingerprint(b), "fb")
    if ca.value == cb.value:
        # Same canonical form => same identity by construction (equal semantics).
        assert fa == fb
    else:
        # Distinct canonical form => distinct fp1 (no accidental collision).
        assert fa != fb


@_SETTINGS
@given(body=_clean_dicts, seq=st.integers(min_value=0, max_value=10**6),
       ns=st.integers(min_value=1, max_value=2_000_000_000_000_000_000))
def test_e2_l2_02_fp1_invariant_under_occurrence_and_key_order(body: dict, seq: int, ns: int) -> None:
    base = h.record(body)
    # Same identity content, reordered keys + different occurrence facts => same stable id.
    reordered = {k: body[k] for k in reversed(list(body))}
    twin = h.record(reordered, writer_id=h.writer("node-z"), sequence=seq, ns=ns)
    assert twin.stable_id == base.stable_id


@_SETTINGS
@given(fval=st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6))
def test_e2_l2_03_float_in_identity_is_refused(fval: float) -> None:
    from qmf.registry import RegistrationRecord
    out = RegistrationRecord.try_create(
        "producer", 1, [], {"weight": fval}, h.writer(), 0, h.instant()
    )
    assert is_refusal(out)  # floats are refused in identity content (integers only)


@_SETTINGS
@given(n=st.integers(min_value=1, max_value=25))
def test_e2_l2_04_edge_log_is_append_only_and_order_preserving(n: int) -> None:
    log = EdgeLog(h.writer())
    appended = []
    for i in range(n):
        # Distinct occurrence-of edges (distinct endpoints) — append order recorded.
        e = LineageEdge.try_create(EdgeType.OCCURRENCE_OF, h.fp(f"from-{i}"), h.fp(f"to-{i}"), log.writer)
        rec = log.append_edge(h.unwrap(e, "edge"))
        assert h.unwrap(rec, "append").outcome is WriteOutcome.STORED
        appended.append(h.unwrap(e, "edge").edge_fingerprint)
    got = [edge.edge_fingerprint for edge in log.edges()]
    assert got == appended  # exactly N, in order, none rewritten
    assert log.edge_count() == n


@_SETTINGS
@given(target=st.text(min_size=1, max_size=10))
def test_e2_l2_05_no_card_never_enters_live(target: str) -> None:
    tfp = h.fp(target).value
    out = authorize_live_promotion(target_fp1=tfp, card=None, superseded=[])
    assert is_refusal(out)
    assert out.category is RefusalCategory.POLICY_REJECTION


@_SETTINGS
@given(machine=st.text(min_size=1, max_size=6), boot=st.text(min_size=1, max_size=6))
def test_e2_l2_06_one_writer_per_stream(machine: str, boot: str) -> None:
    stream_writer = h.writer("stream-owner", boot="boot-owner")
    log = EdgeLog(stream_writer)
    other = h.writer(machine, boot=boot)
    edge = h.unwrap(
        LineageEdge.try_create(EdgeType.OCCURRENCE_OF, h.fp("a"), h.fp("b"), other), "edge"
    )
    out = log.append_edge(edge)
    if other == stream_writer:
        assert is_ok(out)  # same writer identity — accepted
    else:
        assert is_refusal(out)
        assert out.category is RefusalCategory.POLICY_REJECTION
