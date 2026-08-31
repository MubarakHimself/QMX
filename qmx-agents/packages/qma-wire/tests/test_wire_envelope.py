"""Story 41.1 — wire envelope, scope_path, and fp1 canonical JSON (FR-Q11)."""

from __future__ import annotations

import json

import pytest
from qma.wire import (
    CORRELATION_MISSING_ANNOTATION,
    JOURNAL_SEQ_FIELD,
    SCOPE_KIND_ORDER,
    ScopePathError,
    ScopeSegment,
    WireEnvelope,
    is_scope_prefix,
    parse_scope_path,
    validate_wire_envelope_dict,
)
from qmf.core.fingerprint import canonical_bytes
from qmf.core.refusal import Ok, is_ok, is_refusal


def _ok_envelope(**overrides: object) -> WireEnvelope:
    base: dict[str, object] = {
        "v": "1.0.0",
        "type": "start_mission",
        "id": "msg-1",
        "producer_id": "client-a",
        "correlation_id": "corr-1",
        "scope_path": [
            {"kind": "desk", "id": "research"},
            {"kind": "quant", "id": "q-1"},
        ],
        "payload": {"mission_ref": "m-1"},
        "seq": 3,
    }
    base.update(overrides)
    result = WireEnvelope.try_create(**base)  # type: ignore[arg-type]
    assert isinstance(result, Ok), result
    return result.value


def test_envelope_carries_required_fields_and_optional_seq() -> None:
    env = _ok_envelope()
    data = env.to_dict()
    assert set(data) >= {
        "v",
        "type",
        "id",
        "producer_id",
        "correlation_id",
        "scope_path",
        "payload",
        "seq",
    }
    assert data["seq"] == 3
    assert JOURNAL_SEQ_FIELD not in data


def test_absent_optional_seq_is_omitted_not_null() -> None:
    env = _ok_envelope(seq=None)
    data = env.to_dict()
    assert "seq" not in data
    assert None not in data.values()
    canonical = env.canonical_bytes()
    assert is_ok(canonical)
    assert b"null" not in canonical.value
    assert b'"seq"' not in canonical.value


def test_correlation_missing_carve_out_keeps_lifecycle_id() -> None:
    env = _ok_envelope(
        type="ledger.updated",
        correlation_id="daemon-lifecycle-9",
        correlation_missing=True,
        seq=1,
        payload={"entry": "evidence"},
    )
    data = env.to_dict()
    assert data["correlation_id"] == "daemon-lifecycle-9"
    assert data[CORRELATION_MISSING_ANNOTATION] is True
    checked = validate_wire_envelope_dict(data)
    assert is_ok(checked)


def test_canonical_json_uses_imported_fp1() -> None:
    env = _ok_envelope()
    ours = env.canonical_bytes()
    theirs = canonical_bytes(env.to_dict())
    assert is_ok(ours) and is_ok(theirs)
    assert ours.value == theirs.value
    # Key order is lexicographic under fp1.
    decoded = json.loads(ours.value.decode("utf-8"))
    assert list(decoded.keys()) == sorted(decoded.keys())


def test_scope_path_order_and_ancestors() -> None:
    assert SCOPE_KIND_ORDER == (
        "desk",
        "quant",
        "mission",
        "task",
        "session",
        "agent",
        "subagent",
    )
    path = parse_scope_path(
        [
            ScopeSegment("desk", "d"),
            ScopeSegment("quant", "q"),
            ScopeSegment("mission", "m"),
        ]
    )
    assert [s.kind for s in path] == ["desk", "quant", "mission"]


def test_scope_path_rejects_gaps_and_out_of_order() -> None:
    with pytest.raises(ScopePathError):
        parse_scope_path([{"kind": "quant", "id": "q"}])
    with pytest.raises(ScopePathError):
        parse_scope_path(
            [
                {"kind": "desk", "id": "d"},
                {"kind": "mission", "id": "m"},
            ]
        )
    with pytest.raises(ScopePathError):
        parse_scope_path(
            [
                {"kind": "desk", "id": "d"},
                {"kind": "desk", "id": "d2"},
            ]
        )


def test_prefix_filters_match_prefixes_only() -> None:
    full = [
        {"kind": "desk", "id": "d"},
        {"kind": "quant", "id": "q"},
        {"kind": "mission", "id": "m"},
    ]
    assert is_scope_prefix(full[:2], full) is True
    assert is_scope_prefix(full, full) is True
    assert is_scope_prefix(full, full[:2]) is False
    assert (
        is_scope_prefix(
            [{"kind": "desk", "id": "other"}, {"kind": "quant", "id": "q"}],
            full,
        )
        is False
    )


def test_seq_is_final_scope_projection_index() -> None:
    env = _ok_envelope(
        scope_path=[
            {"kind": "desk", "id": "d"},
            {"kind": "quant", "id": "q"},
            {"kind": "mission", "id": "m"},
        ],
        seq=42,
    )
    assert env.final_scope_kind == "mission"
    assert env.seq == 42
    assert JOURNAL_SEQ_FIELD not in env.to_dict()
    assert is_refusal(
        WireEnvelope.try_create(
            v="1.0.0",
            type="start_mission",
            id="x",
            producer_id="p",
            correlation_id="c",
            scope_path=[],
            payload={},
            seq=1,
        )
    )


def test_journal_seq_rejected_in_payload() -> None:
    assert is_refusal(
        WireEnvelope.try_create(
            v="1.0.0",
            type="start_mission",
            id="x",
            producer_id="p",
            correlation_id="c",
            scope_path=[{"kind": "desk", "id": "d"}],
            payload={JOURNAL_SEQ_FIELD: 99},
        )
    )
