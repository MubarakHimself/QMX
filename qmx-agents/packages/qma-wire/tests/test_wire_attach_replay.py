"""Story 41.2 — scoped attach / detach / replay (FR-Q15)."""

from __future__ import annotations

from qma.core.refusals import CursorScopeMismatch
from qma.wire import (
    ATTACH_METHOD,
    DETACH_METHOD,
    AttachRequest,
    ClientAttachmentState,
    DetachRequest,
    format_scope_key,
    mint_replay_cursor,
    validate_attach,
)
from qmf.core.refusal import Ok, is_ok, is_refusal

SCOPE_A = (
    {"kind": "desk", "id": "research"},
    {"kind": "quant", "id": "alpha"},
)
SCOPE_B = (
    {"kind": "desk", "id": "trading"},
    {"kind": "quant", "id": "beta"},
)


def test_attach_detach_method_names_are_qualified() -> None:
    assert ATTACH_METHOD == "wire.attach"
    assert DETACH_METHOD == "wire.detach"


def test_attach_changes_client_state_only_never_quant() -> None:
    state = ClientAttachmentState(quant_identity="quant:research/alpha", quant_work_active=True)
    request = AttachRequest.try_create(scope=SCOPE_A, since_seq=4)
    assert isinstance(request, Ok)

    attached = state.attach(request.value)
    assert isinstance(attached, Ok)
    assert attached.value.changes_quant_identity is False
    assert attached.value.stops_quant_work is False
    assert attached.value.read_only_replay is False
    assert state.quant_identity == "quant:research/alpha"
    assert state.quant_work_active is True
    assert format_scope_key(SCOPE_A) in state.attached_scopes

    detach = DetachRequest.try_create(scope=SCOPE_A)
    assert isinstance(detach, Ok)
    assert is_ok(state.detach(detach.value))
    assert format_scope_key(SCOPE_A) not in state.attached_scopes
    assert state.quant_identity == "quant:research/alpha"
    assert state.quant_work_active is True


def test_attach_since_seq_zero_is_read_only_replay() -> None:
    request = AttachRequest.try_create(scope=SCOPE_A, since_seq=0)
    assert isinstance(request, Ok)
    assert request.value.read_only_replay is True

    subscription = validate_attach(request.value)
    assert isinstance(subscription, Ok)
    assert subscription.value.read_only_replay is True
    assert subscription.value.since_seq == 0
    assert subscription.value.method == "wire.attach"


def test_cursor_from_other_scope_returns_cursor_scope_mismatch() -> None:
    cursor = mint_replay_cursor(SCOPE_A, 7)
    assert isinstance(cursor, Ok)

    mismatched = AttachRequest.try_create(scope=SCOPE_B, since_seq=7, cursor=cursor.value)
    assert isinstance(mismatched, Ok)
    refused = validate_attach(mismatched.value)
    assert is_refusal(refused)
    assert CursorScopeMismatch.matches(refused)
    assert refused.context["cursor_scope"] == format_scope_key(SCOPE_A)
    assert refused.context["expected_scope"] == format_scope_key(SCOPE_B)


def test_cursor_never_silently_rebases_broadens_or_narrows() -> None:
    cursor = mint_replay_cursor(SCOPE_A, 10)
    assert isinstance(cursor, Ok)

    # Same scope but different seq → refuse, never silent re-base.
    rebased = AttachRequest.try_create(scope=SCOPE_A, since_seq=3, cursor=cursor.value)
    assert isinstance(rebased, Ok)
    refused = validate_attach(rebased.value)
    assert is_refusal(refused)
    assert refused.context["field"] == "since_seq"

    # Narrower / broader scope with foreign cursor → CursorScopeMismatch.
    broader = (
        {"kind": "desk", "id": "research"},
        {"kind": "quant", "id": "alpha"},
        {"kind": "mission", "id": "m1"},
    )
    broaden = AttachRequest.try_create(scope=broader, since_seq=10, cursor=cursor.value)
    assert isinstance(broaden, Ok)
    broaden_refused = validate_attach(broaden.value)
    assert is_refusal(broaden_refused)
    assert CursorScopeMismatch.matches(broaden_refused)

    matching = AttachRequest.try_create(scope=SCOPE_A, since_seq=10, cursor=cursor.value)
    assert isinstance(matching, Ok)
    assert is_ok(validate_attach(matching.value))


def test_client_attach_with_mismatched_cursor_leaves_subscriptions_unchanged() -> None:
    state = ClientAttachmentState(quant_identity="quant:x", quant_work_active=True)
    cursor = mint_replay_cursor(SCOPE_A, 1)
    assert isinstance(cursor, Ok)
    bad = AttachRequest.try_create(scope=SCOPE_B, since_seq=1, cursor=cursor.value)
    assert isinstance(bad, Ok)
    refused = state.attach(bad.value)
    assert is_refusal(refused)
    assert state.attached_scopes == frozenset()
    assert state.quant_work_active is True
