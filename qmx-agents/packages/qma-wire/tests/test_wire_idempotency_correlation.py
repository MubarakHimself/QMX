"""Story 41.3 — command idempotency and correlation provenance (FR-Q16)."""

from __future__ import annotations

from qma.wire import (
    CORRELATION_MINT_ORIGINS,
    CORRELATION_MISSING_ANNOTATION,
    DEDUP_WINDOW_REGISTRY_KEY,
    CommandDedupCursor,
    CorrelationMintOrigin,
    IdempotencyKey,
    WireEnvelope,
    admit_correlation,
    assert_copied_verbatim,
    copy_correlation_id,
    idempotency_key_from_envelope,
    mint_correlation_id,
    propagate_correlation,
)
from qma.wire.idempotency import IdempotencyError
from qmf.core.chrono import Duration, Instant
from qmf.core.refusal import Ok, RefusalCategory, is_ok, is_refusal


def _instant(ns: int) -> Instant:
    result = Instant.try_create(ns)
    assert isinstance(result, Ok)
    return result.value


def _duration(ns: int) -> Duration:
    result = Duration.try_create(ns)
    assert isinstance(result, Ok)
    return result.value


def _key(producer_id: str = "client-a", msg_id: str = "cmd-1") -> IdempotencyKey:
    result = IdempotencyKey.try_create(producer_id=producer_id, id=msg_id)
    assert isinstance(result, Ok)
    return result.value


def test_dedup_window_registry_key_is_homed() -> None:
    assert DEDUP_WINDOW_REGISTRY_KEY == "wire.dedup_window"
    cursor = CommandDedupCursor(window=_duration(1_000_000_000))
    assert cursor.window_registry_key == DEDUP_WINDOW_REGISTRY_KEY


def test_same_producer_id_and_id_are_one_idempotent_command() -> None:
    cursor = CommandDedupCursor(window=_duration(10_000_000_000))
    key = _key()
    first = cursor.observe(key, now=_instant(1_000))
    second = cursor.observe(key, now=_instant(2_000))
    assert isinstance(first, Ok) and isinstance(second, Ok)
    assert first.value.disposition == "accept"
    assert second.value.disposition == "duplicate"
    assert second.value.is_idempotent_replay is True
    assert second.value.first_seen_at == first.value.first_seen_at
    assert second.value.window_registry_key == DEDUP_WINDOW_REGISTRY_KEY


def test_changed_pair_member_is_not_the_same_command() -> None:
    cursor = CommandDedupCursor(window=_duration(10_000_000_000))
    base = _key(producer_id="client-a", msg_id="cmd-1")
    other_producer = _key(producer_id="client-b", msg_id="cmd-1")
    other_id = _key(producer_id="client-a", msg_id="cmd-2")
    assert base.same_command_as(other_producer) is False
    assert base.same_command_as(other_id) is False

    assert isinstance(cursor.observe(base, now=_instant(1)), Ok)
    changed_producer = cursor.observe(other_producer, now=_instant(2))
    changed_id = cursor.observe(other_id, now=_instant(3))
    assert isinstance(changed_producer, Ok) and isinstance(changed_id, Ok)
    assert changed_producer.value.disposition == "accept"
    assert changed_id.value.disposition == "accept"


def test_idempotency_outside_dedup_window_is_not_duplicate() -> None:
    window = _duration(100)
    cursor = CommandDedupCursor(window=window)
    key = _key()
    assert isinstance(cursor.observe(key, now=_instant(0)), Ok)
    later = cursor.observe(key, now=_instant(101))
    assert isinstance(later, Ok)
    assert later.value.disposition == "accept"
    assert cursor.contains(key, now=_instant(101)) is True


def test_idempotency_key_from_envelope() -> None:
    env = WireEnvelope.try_create(
        v="1.0.0",
        type="start_mission",
        id="msg-9",
        producer_id="producer-9",
        correlation_id="corr-9",
        scope_path=[{"kind": "desk", "id": "d"}],
        payload={},
    )
    assert isinstance(env, Ok)
    key = idempotency_key_from_envelope(env.value.to_dict())
    assert isinstance(key, Ok)
    assert key.value == IdempotencyKey(producer_id="producer-9", id="msg-9")


def test_non_positive_dedup_window_refused() -> None:
    try:
        CommandDedupCursor(window=_duration(0))
    except IdempotencyError as exc:
        assert DEDUP_WINDOW_REGISTRY_KEY in str(exc)
    else:
        raise AssertionError("expected IdempotencyError")


def test_three_correlation_mint_origins_only() -> None:
    assert (
        frozenset(
            {
                "operator_command",
                "scheduled_trigger",
                "daemon_lifecycle",
            }
        )
        == CORRELATION_MINT_ORIGINS
    )
    for origin in CorrelationMintOrigin:
        minted = mint_correlation_id(origin=origin, correlation_id="corr-root-1")
        assert isinstance(minted, Ok)
        assert minted.value.origin is origin
        assert minted.value.correlation_id == "corr-root-1"
        assert minted.value.correlation_missing is False

    refused = mint_correlation_id(origin="recipient", correlation_id="x")
    assert is_refusal(refused)


def test_correlation_copied_verbatim_never_regenerated() -> None:
    origin = mint_correlation_id(
        origin=CorrelationMintOrigin.OPERATOR_COMMAND,
        correlation_id="corr-origin-full-opaque-token",
    )
    assert isinstance(origin, Ok)
    copied = copy_correlation_id(origin.value.correlation_id)
    assert isinstance(copied, Ok)
    assert copied.value == "corr-origin-full-opaque-token"

    chain = propagate_correlation(
        origin.value.correlation_id,
        [
            origin.value.correlation_id,
            "corr-origin-full-opaque-token",
            copy_correlation_id(origin.value.correlation_id).value,  # type: ignore[union-attr]
        ],
    )
    assert is_ok(chain)

    abbreviated = assert_copied_verbatim(
        origin.value.correlation_id,
        origin.value.correlation_id[:8],
    )
    assert is_refusal(abbreviated)
    assert "verbatim" in str(abbreviated.context["reason"])

    regenerated = assert_copied_verbatim(origin.value.correlation_id, "corr-brand-new")
    assert is_refusal(regenerated)

    derived = propagate_correlation(
        origin.value.correlation_id,
        [origin.value.correlation_id, f"{origin.value.correlation_id}-child"],
    )
    assert is_refusal(derived)
    assert derived.context["downstream_index"] == 1


def test_non_evidence_missing_correlation_is_typed_refusal_without_substitute() -> None:
    refused = admit_correlation(correlation_id=None, is_evidence_append=False)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "correlation_id"
    assert refused.context["substitute_identifier"] is None
    assert "correlation_id" not in refused.context or refused.context.get("correlation_id") is None
    # Conformance: refusal must not invent a stand-in id under any key.
    for key, value in refused.context.items():
        if key in {"field", "reason", "is_evidence_append", "substitute_identifier"}:
            continue
        assert value is None or not (
            isinstance(value, str) and value.startswith(("corr-", "lifecycle-", "daemon-"))
        )


def test_evidence_append_carve_out_preserves_correlation_missing() -> None:
    admitted = admit_correlation(
        correlation_id=None,
        is_evidence_append=True,
        daemon_lifecycle_id="daemon-lifecycle-42",
    )
    assert isinstance(admitted, Ok)
    assert admitted.value.correlation_id == "daemon-lifecycle-42"
    assert admitted.value.correlation_missing is True
    assert admitted.value.source == "lifecycle_carve_out"
    assert admitted.value.origin is CorrelationMintOrigin.DAEMON_LIFECYCLE

    fields = admitted.value.to_envelope_fields()
    assert fields["correlation_id"] == "daemon-lifecycle-42"
    assert fields[CORRELATION_MISSING_ANNOTATION] is True

    env = WireEnvelope.try_create(
        v="1.0.0",
        type="ledger.updated",
        id="ev-1",
        producer_id="daemon",
        scope_path=[{"kind": "desk", "id": "d"}],
        payload={"entry": "evidence"},
        correlation_id=fields["correlation_id"],
        correlation_missing=True,
        seq=1,
    )
    assert isinstance(env, Ok)
    serialized = env.value.to_dict()
    assert serialized["correlation_id"] == "daemon-lifecycle-42"
    assert serialized[CORRELATION_MISSING_ANNOTATION] is True
    # Annotation preserved for audit — evidence is not dropped.
    assert CORRELATION_MISSING_ANNOTATION in serialized


def test_present_correlation_on_evidence_skips_carve_out() -> None:
    admitted = admit_correlation(
        correlation_id="corr-already",
        is_evidence_append=True,
        daemon_lifecycle_id="daemon-lifecycle-unused",
    )
    assert isinstance(admitted, Ok)
    assert admitted.value.correlation_id == "corr-already"
    assert admitted.value.correlation_missing is False
    assert CORRELATION_MISSING_ANNOTATION not in admitted.value.to_envelope_fields()
