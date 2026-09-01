"""Zero-authority liveness heartbeat — outbound alive-ping only (DEC-0261).

The node emits an outbound alive-ping on a declared cadence to an off-VPS
free-tier watcher through an injected HTTP sink. The watcher alerts on a
MISSING ping. This surface holds ZERO authority: it cannot stop entries, close
positions, call a door, or accept an inbound node path. The daily liveness
digest does not exist. Real free-tier account checks are soak-tagged (AR-87);
contract tests use the local watcher double.
"""

from __future__ import annotations

from collections.abc import MutableSequence
from dataclasses import dataclass, field
from typing import ClassVar, Final, Literal, Protocol

from qmf.core import Ok, Result
from qmf.core.refusal import is_refusal

from qmn.observability._refuse import clean_token, invalid, policy

__all__ = [
    "CAN_CALL_DOOR",
    "CAN_CLOSE_POSITIONS",
    "CAN_STOP_ENTRIES",
    "DAILY_LIVENESS_DIGEST_EXISTS",
    "HOLDS_INBOUND_NODE_PATH",
    "HOLDS_ZERO_AUTHORITY",
    "UI_STREAMED_HEALTH_VIEW_IMPLEMENTED",
    "LivenessHeartbeat",
    "LivenessHttpSink",
    "RecordingLivenessHttpSink",
    "WatcherDouble",
    "WatcherNotificationState",
]

# Authority surface — constants, not knobs (DEC-0261).
HOLDS_ZERO_AUTHORITY: Final[bool] = True
HOLDS_INBOUND_NODE_PATH: Final[bool] = False
CAN_STOP_ENTRIES: Final[bool] = False
CAN_CLOSE_POSITIONS: Final[bool] = False
CAN_CALL_DOOR: Final[bool] = False

# Rejected / deferred products (DEC-0261 / FR-067).
DAILY_LIVENESS_DIGEST_EXISTS: Final[bool] = False
UI_STREAMED_HEALTH_VIEW_IMPLEMENTED: Final[bool] = False

WatcherNotificationState = Literal["alive", "missing-ping"]


class LivenessHttpSink(Protocol):
    """Outbound-only HTTP sink for alive-pings. Never receives node commands."""

    def post_alive(
        self,
        *,
        endpoint: str,
        token_reference: str,
        emitted_at_ns: int,
    ) -> Result[None]:
        """POST one alive-ping. ``token_reference`` is a credential reference."""
        ...


@dataclass
class WatcherDouble:
    """Local free-tier watcher stub (AR-87). Alerts on a missing alive-ping."""

    cadence_ns: int
    last_ping_ns: int | None = None
    missing_notifications: MutableSequence[int] = field(default_factory=list[int])
    _missing_latched: bool = False

    def accept_ping(self, emitted_at_ns: object) -> Result[None]:
        if not isinstance(emitted_at_ns, int) or isinstance(emitted_at_ns, bool):
            return invalid(
                "emitted_at_ns",
                "alive-ping stamp is a monotonic nanosecond int",
                given=repr(emitted_at_ns),
            )
        if emitted_at_ns < 0:
            return invalid("emitted_at_ns", "alive-ping stamp is non-negative")
        self.last_ping_ns = emitted_at_ns
        self._missing_latched = False
        return Ok(None)

    def evaluate(self, now_ns: object) -> Result[WatcherNotificationState]:
        """Return out-of-band notification state for the acceptance double."""
        if not isinstance(now_ns, int) or isinstance(now_ns, bool):
            return invalid("now_ns", "watcher evaluate stamp is a monotonic nanosecond int")
        if self.cadence_ns <= 0:
            return invalid("cadence_ns", "watcher cadence is a positive nanosecond int")
        if self.last_ping_ns is None:
            state: WatcherNotificationState = "missing-ping"
        elif now_ns - self.last_ping_ns > self.cadence_ns:
            state = "missing-ping"
        else:
            state = "alive"
        if state == "missing-ping" and not self._missing_latched:
            self.missing_notifications.append(now_ns)
            self._missing_latched = True
        return Ok(state)


@dataclass
class RecordingLivenessHttpSink:
    """Records outbound pings; optionally forwards them to a watcher double."""

    posts: MutableSequence[dict[str, object]] = field(default_factory=list[dict[str, object]])
    watcher: WatcherDouble | None = None
    fail_next: bool = False

    def post_alive(
        self,
        *,
        endpoint: str,
        token_reference: str,
        emitted_at_ns: int,
    ) -> Result[None]:
        if self.fail_next:
            self.fail_next = False
            return policy("liveness_http_sink", "injected outbound alive-ping failure")
        ep = clean_token(endpoint)
        ref = clean_token(token_reference)
        if ep is None:
            return invalid("endpoint", "liveness endpoint is a non-blank string")
        if ref is None:
            return invalid(
                "token_reference",
                "liveness token_reference is a non-blank credential reference",
            )
        self.posts.append(
            {
                "endpoint": ep,
                "token_reference": ref,
                "emitted_at_ns": emitted_at_ns,
                "carries_secret_value": False,
            }
        )
        if self.watcher is not None:
            accepted = self.watcher.accept_ping(emitted_at_ns)
            if is_refusal(accepted):
                return accepted
        return Ok(None)


@dataclass
class LivenessHeartbeat:
    """Outbound alive-ping emitter — notification only, zero authority.

    Holds no door handle, no entry/position control, and no inbound listener.
    Cadence and endpoint come from resolved node-config (registry rows); this
    type never invents them.
    """

    endpoint: str
    cadence_ns: int
    token_reference: str
    sink: LivenessHttpSink
    emissions: int = 0
    last_emit_ns: int | None = None

    HOLDS_ZERO_AUTHORITY: ClassVar[bool] = True
    HOLDS_INBOUND_NODE_PATH: ClassVar[bool] = False
    CAN_STOP_ENTRIES: ClassVar[bool] = False
    CAN_CLOSE_POSITIONS: ClassVar[bool] = False
    CAN_CALL_DOOR: ClassVar[bool] = False
    DAILY_LIVENESS_DIGEST_EXISTS: ClassVar[bool] = False

    @classmethod
    def try_create(
        cls,
        *,
        endpoint: object,
        cadence_ns: object,
        token_reference: object,
        sink: LivenessHttpSink,
    ) -> Result[LivenessHeartbeat]:
        ep = clean_token(endpoint)
        ref = clean_token(token_reference)
        if ep is None:
            return invalid("liveness_heartbeat_endpoint", "endpoint is a non-blank string")
        if ref is None:
            return invalid(
                "liveness_heartbeat_token_reference",
                "token_reference is a non-blank credential reference, never a secret value",
            )
        if not isinstance(cadence_ns, int) or isinstance(cadence_ns, bool) or cadence_ns <= 0:
            return invalid(
                "liveness_heartbeat_cadence",
                "cadence is a positive nanosecond int",
                given=repr(cadence_ns),
            )
        return Ok(
            cls(
                endpoint=ep,
                cadence_ns=cadence_ns,
                token_reference=ref,
                sink=sink,
            )
        )

    def maybe_emit(self, now_ns: object) -> Result[bool]:
        """Emit one outbound alive-ping when the configured cadence has elapsed.

        Returns ``Ok(True)`` when a ping was sent, ``Ok(False)`` when the cadence
        has not yet elapsed. Never touches entries, positions, or doors.
        """
        if not isinstance(now_ns, int) or isinstance(now_ns, bool):
            return invalid("now_ns", "heartbeat stamp is a monotonic nanosecond int")
        if self.last_emit_ns is not None and now_ns - self.last_emit_ns < self.cadence_ns:
            return Ok(False)
        posted = self.sink.post_alive(
            endpoint=self.endpoint,
            token_reference=self.token_reference,
            emitted_at_ns=now_ns,
        )
        if is_refusal(posted):
            return posted
        self.last_emit_ns = now_ns
        self.emissions += 1
        return Ok(True)

    def authority_surface(self) -> dict[str, bool]:
        """Explicit zero-authority claim for contract tests."""
        return {
            "holds_zero_authority": self.HOLDS_ZERO_AUTHORITY,
            "holds_inbound_node_path": self.HOLDS_INBOUND_NODE_PATH,
            "can_stop_entries": self.CAN_STOP_ENTRIES,
            "can_close_positions": self.CAN_CLOSE_POSITIONS,
            "can_call_door": self.CAN_CALL_DOOR,
            "daily_liveness_digest_exists": self.DAILY_LIVENESS_DIGEST_EXISTS,
        }
