"""Reference usage — shared tick cancel and cutover ack (Story 59.1).

Executable::

    python qmb/examples/stream_cancel_cutover_usage.py

Shows the things AD-28 / Story 59.1 pin down:

1. Two consumers of one tick subscription; cancelling A leaves B running.
2. refcount is derived from live leases.
3. Cutover requires barrier + cutover-ack; missing watermark holds in cutover.
4. Replay provenance cannot authorize a live command.
5. A stream subscription is not trading permission.
"""

from __future__ import annotations

import sys
from typing import TypeVar

from qmb.runloop import (
    ack_stream_cutover,
    authorize_live_command,
    begin_stream_cutover,
    cancel_stream_lease,
    record_stream_subscription,
    refuse_subscription_as_trading_permission,
    shared_feed_consumers,
)
from qmf.core.refusal import Result, is_ok, is_refusal

T = TypeVar("T")

_NOW = 1_700_000_000_000_000_000
_WATERMARK = {"epoch": 3, "sequence": 1100000}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _lease(consumer: str, lease: str) -> dict[str, object]:
    return {
        "consumer_id": consumer,
        "expires_at": _NOW + 60_000_000_000,
        "lease_id": lease,
        "renewed_at": _NOW,
    }


def main() -> None:
    recorded = _unwrap(
        record_stream_subscription(
            {
                "backpressure_policy": "block",
                "buffer_bound": 10000,
                "channel": "ticks",
                "cursor": dict(_WATERMARK),
                "cursor_durable": True,
                "cutover_watermark": dict(_WATERMARK),
                "epoch": 3,
                "leases": [
                    _lease("consumer:a", "lease:a"),
                    _lease("consumer:b", "lease:b"),
                ],
                "phase": "replay",
                "sequence_domain": "provider-channel",
                "shared": True,
                "source_id": "dukascopy",
                "sub_id": "sub:ticks-eurusd",
                "venue_id": "ctrader-live",
            },
            as_of=_NOW,
        ),
        "shared tick subscription",
    )
    after = _unwrap(
        cancel_stream_lease(recorded, lease_id="lease:a", as_of=_NOW),
        "cancel A",
    )
    cutover = _unwrap(begin_stream_cutover(after), "cutover barrier")
    live, ack = _unwrap(
        ack_stream_cutover(cutover, watermark=_WATERMARK, acked_at=_NOW),
        "cutover-ack",
    )
    replay_cmd = authorize_live_command(recorded, provenance_phase="replay")
    permission = refuse_subscription_as_trading_permission(live)
    missing = _unwrap(
        record_stream_subscription(
            {
                "backpressure_policy": "block",
                "buffer_bound": 1,
                "channel": "ticks",
                "cursor": {"epoch": 3, "sequence": 1},
                "cursor_durable": True,
                "cutover_watermark": None,
                "epoch": 3,
                "leases": [_lease("consumer:b", "lease:b")],
                "phase": "replay",
                "sequence_domain": "provider-channel",
                "source_id": "dukascopy",
                "sub_id": "sub:ticks-eurusd",
                "venue_id": None,
            },
            as_of=_NOW,
        ),
        "missing watermark",
    )
    held = _unwrap(begin_stream_cutover(missing), "hold in cutover")
    refused = ack_stream_cutover(held, watermark=_WATERMARK, acked_at=_NOW)
    sys.stdout.write("stream cancel cutover ok\n")
    sys.stdout.write(f"refcount after cancel A {after.refcount}\n")
    if shared_feed_consumers(after, after.as_of) == ("consumer:b",):
        sys.stdout.write("cancelling A leaves B running\n")
    sys.stdout.write(f"cutover-ack {ack.event_kind} phase {live.phase}\n")
    if is_refusal(replay_cmd):
        sys.stdout.write("replay provenance cannot authorize a live command\n")
    if is_refusal(refused) and held.phase == "cutover":
        sys.stdout.write("missing watermark holds in cutover\n")
    if permission.context["trading_permission"] is False:
        sys.stdout.write("a stream subscription is not trading permission\n")


if __name__ == "__main__":
    main()
