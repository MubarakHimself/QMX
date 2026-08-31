"""``wire.attach`` / ``wire.detach`` scoped replay (CT-40; AD-5; FR-Q15).

Attachment is client state only: it never changes a Quant's identity and never
stops its work. ``wire.attach(since_seq=0)`` is read-only replay of that scope's
durable event stream. A cursor is valid only for the scope that issued it; using
it on another scope returns ``CursorScopeMismatch`` and never silently re-bases,
broadens, or narrows the cursor.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final, Literal, cast

from qma.core.refusals import CursorScopeMismatch
from qma.wire.envelope import ScopePathError, ScopeSegment, parse_scope_path
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "ATTACH_METHOD",
    "DETACH_METHOD",
    "AttachError",
    "AttachRequest",
    "AttachSubscription",
    "ClientAttachmentState",
    "DetachRequest",
    "ReplayCursor",
    "format_scope_key",
    "mint_replay_cursor",
    "validate_attach",
]


ATTACH_METHOD: Final[str] = "wire.attach"
DETACH_METHOD: Final[str] = "wire.detach"


class AttachError(ValueError):
    """Raised when attach/detach inputs cannot be constructed."""


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def format_scope_key(scope: Sequence[ScopeSegment | Mapping[str, str]]) -> str:
    """Stable scope key for cursor binding (``kind/id`` segments joined by ``/``)."""
    segments = parse_scope_path(scope)
    return "/".join(f"{segment.kind}/{segment.id}" for segment in segments)


def mint_replay_cursor(
    scope: object,
    seq: object,
) -> Result[ReplayCursor]:
    """Mint a replay cursor bound to exactly one scope."""
    try:
        path = parse_scope_path(scope)
    except ScopePathError as exc:
        return _invalid("scope", str(exc))
    if not path:
        return _invalid("scope", "replay cursor requires a non-empty scope_path")
    if isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
        return _invalid("seq", "cursor seq is a non-negative integer")
    return Ok(ReplayCursor(scope=path, seq=seq))


@dataclass(frozen=True, slots=True)
class ReplayCursor:
    """Per-scope durable-stream cursor. Valid only for the issuing scope."""

    scope: tuple[ScopeSegment, ...]
    seq: int

    @property
    def scope_key(self) -> str:
        return format_scope_key(self.scope)

    def to_dict(self) -> dict[str, object]:
        return {
            "scope": [segment.to_dict() for segment in self.scope],
            "seq": self.seq,
        }


@dataclass(frozen=True, slots=True)
class AttachRequest:
    """``wire.attach(scope, since_seq)`` params; optional cursor for resume checks."""

    scope: tuple[ScopeSegment, ...]
    since_seq: int
    cursor: ReplayCursor | None = None

    @classmethod
    def try_create(
        cls,
        *,
        scope: object,
        since_seq: object,
        cursor: object = None,
    ) -> Result[AttachRequest]:
        try:
            path = parse_scope_path(scope)
        except ScopePathError as exc:
            return _invalid("scope", str(exc))
        if not path:
            return _invalid("scope", "wire.attach requires a non-empty scope")
        if isinstance(since_seq, bool) or not isinstance(since_seq, int) or since_seq < 0:
            return _invalid("since_seq", "since_seq is a non-negative integer")

        resolved_cursor: ReplayCursor | None
        if cursor is None:
            resolved_cursor = None
        elif isinstance(cursor, ReplayCursor):
            resolved_cursor = cursor
        elif isinstance(cursor, Mapping):
            raw = cast("Mapping[object, object]", cursor)
            built = mint_replay_cursor(raw.get("scope", ()), raw.get("seq"))
            if not isinstance(built, Ok):
                return built
            resolved_cursor = built.value
        else:
            return _invalid("cursor", "cursor must be a ReplayCursor or object")

        return Ok(cls(scope=path, since_seq=since_seq, cursor=resolved_cursor))

    @property
    def scope_key(self) -> str:
        return format_scope_key(self.scope)

    @property
    def read_only_replay(self) -> bool:
        """``since_seq=0`` is read-only replay of the scope's durable event stream."""
        return self.since_seq == 0

    def to_params(self) -> dict[str, object]:
        out: dict[str, object] = {
            "scope": [segment.to_dict() for segment in self.scope],
            "since_seq": self.since_seq,
        }
        if self.cursor is not None:
            out["cursor"] = self.cursor.to_dict()
        return out


@dataclass(frozen=True, slots=True)
class DetachRequest:
    """``wire.detach`` params — drops client subscription for one scope."""

    scope: tuple[ScopeSegment, ...]

    @classmethod
    def try_create(cls, *, scope: object) -> Result[DetachRequest]:
        try:
            path = parse_scope_path(scope)
        except ScopePathError as exc:
            return _invalid("scope", str(exc))
        if not path:
            return _invalid("scope", "wire.detach requires a non-empty scope")
        return Ok(cls(scope=path))

    @property
    def scope_key(self) -> str:
        return format_scope_key(self.scope)


@dataclass(frozen=True, slots=True)
class AttachSubscription:
    """Accepted client attachment — never mutates Quant identity or work."""

    method: Literal["wire.attach"]
    scope: tuple[ScopeSegment, ...]
    since_seq: int
    read_only_replay: bool
    changes_quant_identity: Literal[False] = False
    stops_quant_work: Literal[False] = False

    @property
    def scope_key(self) -> str:
        return format_scope_key(self.scope)

    def to_dict(self) -> dict[str, object]:
        return {
            "method": self.method,
            "scope": [segment.to_dict() for segment in self.scope],
            "since_seq": self.since_seq,
            "read_only_replay": self.read_only_replay,
            "changes_quant_identity": self.changes_quant_identity,
            "stops_quant_work": self.stops_quant_work,
        }


def validate_attach(request: AttachRequest) -> Result[AttachSubscription]:
    """Validate ``wire.attach``; refuse cross-scope cursors with ``CursorScopeMismatch``."""
    if request.cursor is not None:
        cursor_key = request.cursor.scope_key
        expected_key = request.scope_key
        if cursor_key != expected_key:
            # Never silent re-base / broaden / narrow — typed refusal only.
            return CursorScopeMismatch.of(
                cursor_scope=cursor_key,
                expected_scope=expected_key,
            )
        # Cursor seq positions the stream; since_seq must match the bound cursor.
        if request.cursor.seq != request.since_seq:
            return _invalid(
                "since_seq",
                "since_seq must equal the cursor seq for the same scope; "
                "cursors are never silently re-based",
                cursor_seq=request.cursor.seq,
                since_seq=request.since_seq,
            )

    return Ok(
        AttachSubscription(
            method="wire.attach",
            scope=request.scope,
            since_seq=request.since_seq,
            read_only_replay=request.read_only_replay,
        )
    )


def _empty_subscriptions() -> dict[str, AttachSubscription]:
    return {}


@dataclass(slots=True)
class ClientAttachmentState:
    """Client-only scope subscriptions. Detach / drop never stops Quant work."""

    _subscriptions: dict[str, AttachSubscription] = field(
        default_factory=_empty_subscriptions,
    )
    quant_identity: str | None = None
    quant_work_active: bool = True

    @property
    def attached_scopes(self) -> frozenset[str]:
        return frozenset(self._subscriptions)

    def attach(self, request: AttachRequest) -> Result[AttachSubscription]:
        """Apply ``wire.attach`` to client state only."""
        validated = validate_attach(request)
        if not isinstance(validated, Ok):
            return validated
        subscription = validated.value
        # Client subscription map only — Quant identity and work are untouched.
        self._subscriptions[subscription.scope_key] = subscription
        return Ok(subscription)

    def detach(self, request: DetachRequest) -> Result[str]:
        """Apply ``wire.detach`` — remove client subscription only."""
        key = request.scope_key
        self._subscriptions.pop(key, None)
        return Ok(key)

    def subscription_for(
        self,
        scope: Sequence[ScopeSegment | Mapping[str, str]],
    ) -> AttachSubscription | None:
        return self._subscriptions.get(format_scope_key(scope))
