"""Story 59.1 — stream cancel releases one lease; cutover needs ack."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.runloop import (
    STREAM_BACKPRESSURE_POLICIES,
    STREAM_CONTROL_KINDS,
    STREAM_DATA_KIND,
    STREAM_GAP_0081_CHROME,
    STREAM_IS_TRADING_PERMISSION,
    STREAM_PHASES,
    STREAM_PROTOCOL,
    STREAM_RECORD_CLASSES,
    STREAM_REFCOUNT_DERIVED,
    STREAM_SUBSCRIPTION_FIELDS,
    STREAM_WRAP_OWNER,
    ack_stream_cutover,
    authorize_live_command,
    begin_stream_cutover,
    cancel_stream_lease,
    emit_stream_control,
    emit_stream_data,
    live_stream_leases,
    record_stream_subscription,
    refuse_subscription_as_trading_permission,
    shared_feed_consumers,
    stream_protocol_identity,
)
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

T = TypeVar("T")

_NOW = 1_700_000_000_000_000_000
_RENEWED = _NOW
_EXPIRES = _NOW + 60_000_000_000
_WATERMARK = {"epoch": 3, "sequence": 1100000}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _assert_invalid(result: Result[T], *, field: str | None = None) -> None:
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    if field is not None:
        assert result.context["field"] == field


def _assert_policy(result: Result[T], *, field: str | None = None) -> None:
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    if field is not None:
        assert result.context["field"] == field


def _lease(consumer: str, lease: str) -> dict[str, object]:
    return {
        "consumer_id": consumer,
        "expires_at": _EXPIRES,
        "lease_id": lease,
        "renewed_at": _RENEWED,
    }


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "backpressure_policy": "block",
        "buffer_bound": 10000,
        "channel": "ticks",
        "cursor": {"epoch": 3, "sequence": 1100000},
        "cursor_durable": True,
        "cutover_watermark": dict(_WATERMARK),
        "epoch": 3,
        "leases": [_lease("consumer:a", "lease:a"), _lease("consumer:b", "lease:b")],
        "phase": "replay",
        "sequence_domain": "provider-channel",
        "shared": True,
        "source_id": "dukascopy",
        "sub_id": "sub:ticks-eurusd",
        "venue_id": "ctrader-live",
    }
    body.update(overrides)
    return body


def test_cancel_releases_one_lease_and_shared_feed_stays() -> None:
    recorded = _ok(record_stream_subscription(_payload(), as_of=_NOW))
    assert recorded.refcount == 2
    assert STREAM_REFCOUNT_DERIVED is True
    consumers = shared_feed_consumers(recorded, recorded.as_of)
    assert consumers == ("consumer:a", "consumer:b")
    after = _ok(cancel_stream_lease(recorded, lease_id="lease:a", as_of=_NOW))
    assert after.refcount == 1
    remaining = live_stream_leases(after, after.as_of)
    assert len(remaining) == 1
    assert remaining[0].lease_id == "lease:b"
    assert remaining[0].consumer_id == "consumer:b"
    assert after.feed_alive(after.as_of) is True
    assert shared_feed_consumers(after, after.as_of) == ("consumer:b",)
    tick = _ok(
        emit_stream_data(
            after,
            sequence=1100001,
            event_time=_NOW,
            receive_time=_NOW + 1,
            payload_ref="fp1:sha256:" + "ab" * 32,
        )
    )
    assert tick.event_kind == STREAM_DATA_KIND
    assert tick.sub_id == after.sub_id
    empty = _ok(cancel_stream_lease(after, lease_id="lease:b", as_of=_NOW))
    assert empty.refcount == 0
    assert empty.feed_alive(empty.as_of) is False
    stopped = emit_stream_data(
        empty,
        sequence=1100002,
        event_time=_NOW,
        receive_time=_NOW + 1,
        payload_ref="fp1:sha256:" + "cd" * 32,
    )
    _assert_policy(stopped, field="leases")
    mismatched = record_stream_subscription(_payload(refcount=99), as_of=_NOW)
    _assert_invalid(mismatched, field="refcount")


def test_recorded_fields_split_subscription_data_and_control() -> None:
    recorded = _ok(record_stream_subscription(_payload(), as_of=_NOW))
    body = recorded.as_record()
    for field in STREAM_SUBSCRIPTION_FIELDS:
        assert field in body
    assert body["source_id"] == "dukascopy"
    assert body["venue_id"] == "ctrader-live"
    assert body["source_id"] != body["venue_id"]
    assert body["phase"] in STREAM_PHASES
    assert body["backpressure_policy"] in STREAM_BACKPRESSURE_POLICIES
    assert body["cursor_durable"] is True
    leases = cast("list[object]", body["leases"])
    first = cast("Mapping[str, object]", leases[0])
    assert "lease_id" in first
    assert "consumer_id" in first
    assert "expires_at" in first
    schema = stream_protocol_identity()
    assert schema["stream_wrap_owner"] == STREAM_WRAP_OWNER == "COMP-QMB"
    assert schema["stream_protocol"] == STREAM_PROTOCOL
    assert schema["stream_record_classes"] == STREAM_RECORD_CLASSES
    assert schema["stream_control_kinds"] == STREAM_CONTROL_KINDS
    assert schema["stream_data_kind"] == STREAM_DATA_KIND
    assert schema["stream_is_trading_permission"] is False is STREAM_IS_TRADING_PERMISSION
    assert schema["stream_gap_0081_chrome"] is False is STREAM_GAP_0081_CHROME
    data = _ok(
        emit_stream_data(
            recorded,
            sequence=1048291,
            event_time=_NOW,
            receive_time=_NOW + 80_000_000,
            payload_ref="fp1:sha256:" + "ab" * 32,
        )
    )
    assert data.as_record()["event_kind"] == STREAM_DATA_KIND
    gap = _ok(
        emit_stream_control(
            recorded,
            event_kind="gap",
            detected_at=_NOW,
            from_sequence=1048200,
            to_sequence=1048290,
        )
    )
    assert gap.event_kind == "gap"
    for kind in STREAM_CONTROL_KINDS:
        event = _ok(emit_stream_control(recorded, event_kind=kind, detected_at=_NOW))
        assert event.event_kind == kind
    _assert_invalid(
        emit_stream_control(recorded, event_kind="data", detected_at=_NOW),
        field="event_kind",
    )
    collided = _payload(source_id="ctrader-live", venue_id="ctrader-live")
    _assert_invalid(
        record_stream_subscription(collided, as_of=_NOW),
        field="venue_id",
    )
    _assert_invalid(
        record_stream_subscription(_payload(provider_venue="dukascopy"), as_of=_NOW),
        field="provider_venue",
    )
    chrome = record_stream_subscription(_payload(ui_view="ticks-panel"), as_of=_NOW)
    assert is_refusal(chrome)
    assert chrome.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert chrome.context["field"] == "ui_view"
    assert chrome.context["gap"] == "GAP-0081"
    sixth = record_stream_subscription(_payload(component="COMP-QMX-STREAM"), as_of=_NOW)
    assert is_refusal(sixth)
    assert sixth.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert sixth.context["field"] == "component"


def test_cutover_requires_ack_and_replay_cannot_authorize_live() -> None:
    recorded = _ok(record_stream_subscription(_payload(), as_of=_NOW))
    assert recorded.phase == "replay"
    live_direct = record_stream_subscription(_payload(phase="live"), as_of=_NOW)
    _assert_policy(live_direct, field="phase")
    cutover = _ok(begin_stream_cutover(recorded))
    assert cutover.phase == "cutover"
    skipped = ack_stream_cutover(recorded, watermark=_WATERMARK, acked_at=_NOW + 1_000_000_000)
    _assert_policy(skipped, field="phase")
    acked = _ok(ack_stream_cutover(cutover, watermark=_WATERMARK, acked_at=_NOW + 1_000_000_000))
    live, event = acked
    assert live.phase == "live"
    assert event.event_kind == "cutover-ack"
    assert event.watermark is not None
    assert event.watermark.as_record() == _WATERMARK
    forged = emit_stream_control(cutover, event_kind="cutover-ack", detected_at=_NOW)
    assert is_ok(forged)
    assert cutover.phase == "cutover"
    missing = _ok(record_stream_subscription(_payload(cutover_watermark=None), as_of=_NOW))
    held = _ok(begin_stream_cutover(missing))
    assert held.phase == "cutover"
    refused = ack_stream_cutover(held, watermark=_WATERMARK, acked_at=_NOW)
    _assert_policy(refused, field="cutover_watermark")
    assert held.phase == "cutover"
    replay_cmd = authorize_live_command(recorded, provenance_phase="replay")
    _assert_policy(replay_cmd, field="provenance_phase")
    cutover_cmd = authorize_live_command(cutover, provenance_phase="live")
    _assert_policy(cutover_cmd, field="phase")
    live_cmd = _ok(authorize_live_command(live, provenance_phase="live"))
    assert live_cmd is True
    permission = refuse_subscription_as_trading_permission(live)
    assert permission.category is RefusalCategory.POLICY_REJECTION
    assert permission.context["field"] == "stream_subscription"
    assert permission.context["trading_permission"] is False
    trading = record_stream_subscription(_payload(trading_permission=True), as_of=_NOW)
    _assert_policy(trading, field="trading_permission")
    stale = _ok(
        record_stream_subscription(
            _payload(
                leases=[
                    {
                        "consumer_id": "consumer:a",
                        "expires_at": _NOW,
                        "lease_id": "lease:a",
                        "renewed_at": _RENEWED,
                    },
                    _lease("consumer:b", "lease:b"),
                ]
            ),
            as_of=_NOW,
        )
    )
    assert stale.refcount == 1
    assert shared_feed_consumers(stale, stale.as_of) == ("consumer:b",)
