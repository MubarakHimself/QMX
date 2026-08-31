"""Command idempotency on ``producer_id`` + ``id`` (CT-40; AD-5; FR-Q16).

Every wire command is idempotent on the pair ``producer_id`` plus ``id``. The
daemon's dedup cursor window is the registry-homed duration
``registry:wire.dedup_window`` — referenced by key here, never restated as a
spine literal. A changed member of the pair is a different command.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final, Literal

from qmf.core.chrono import Duration, Instant
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "DEDUP_WINDOW_REGISTRY_KEY",
    "CommandDedupCursor",
    "DedupVerdict",
    "IdempotencyKey",
    "idempotency_key_from_envelope",
]


DEDUP_WINDOW_REGISTRY_KEY: Final[str] = "wire.dedup_window"


class IdempotencyError(ValueError):
    """Raised when an idempotency key cannot be constructed."""


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    """The command identity pair: ``producer_id`` + ``id`` (DEC-0304)."""

    producer_id: str
    id: str

    @classmethod
    def try_create(cls, *, producer_id: object, id: object) -> Result[IdempotencyKey]:
        if not isinstance(producer_id, str) or producer_id.strip() == "":
            return _invalid(
                "producer_id",
                "producer_id is a non-empty stable identity (first half of the idempotency pair)",
                given=repr(producer_id),
            )
        if not isinstance(id, str) or id.strip() == "":
            return _invalid(
                "id",
                "id is a non-empty producer-minted string (second half of the idempotency pair)",
                given=repr(id),
            )
        return Ok(cls(producer_id=producer_id, id=id))

    def same_command_as(self, other: object) -> bool:
        """True only when both members of the pair match."""
        return isinstance(other, IdempotencyKey) and self == other


def idempotency_key_from_envelope(envelope: Mapping[str, object]) -> Result[IdempotencyKey]:
    """Extract the idempotency pair from a wire-envelope mapping."""
    return IdempotencyKey.try_create(
        producer_id=envelope.get("producer_id"),
        id=envelope.get("id"),
    )


@dataclass(frozen=True, slots=True)
class DedupVerdict:
    """Outcome of observing a command against the dedup cursor."""

    key: IdempotencyKey
    disposition: Literal["accept", "duplicate"]
    first_seen_at: Instant
    window_registry_key: str = DEDUP_WINDOW_REGISTRY_KEY

    @property
    def is_idempotent_replay(self) -> bool:
        return self.disposition == "duplicate"


@dataclass
class CommandDedupCursor:
    """In-memory contract model of the daemon's command dedup cursor.

    The window is supplied as a ``Duration`` resolved from
    ``registry:wire.dedup_window`` by the composition root — this module never
    hardcodes an installation duration.
    """

    window: Duration
    _seen: dict[IdempotencyKey, Instant] = field(
        default_factory=dict[IdempotencyKey, Instant],
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.window.value_ns <= 0:
            raise IdempotencyError(f"{DEDUP_WINDOW_REGISTRY_KEY} must be a positive duration")

    @property
    def window_registry_key(self) -> str:
        return DEDUP_WINDOW_REGISTRY_KEY

    def _prune(self, now: Instant) -> None:
        cutoff_ns = now.value_ns - self.window.value_ns
        expired = [key for key, seen_at in self._seen.items() if seen_at.value_ns < cutoff_ns]
        for key in expired:
            del self._seen[key]

    def observe(
        self,
        key: object,
        *,
        now: object,
    ) -> Result[DedupVerdict]:
        """Accept a first delivery or mark a same-pair replay as duplicate.

        Within ``registry:wire.dedup_window`` of the first sighting, the same
        ``producer_id`` + ``id`` resolves as one idempotent command. A changed
        member of the pair is not the same command.
        """
        if not isinstance(key, IdempotencyKey):
            return _invalid(
                "idempotency_key",
                "observe requires an IdempotencyKey",
                given=repr(key),
            )
        if not isinstance(now, Instant):
            return _invalid("now", "dedup observation time must be an Instant", given=repr(now))

        self._prune(now)
        prior = self._seen.get(key)
        if prior is not None and now.value_ns - prior.value_ns <= self.window.value_ns:
            return Ok(
                DedupVerdict(
                    key=key,
                    disposition="duplicate",
                    first_seen_at=prior,
                )
            )

        self._seen[key] = now
        return Ok(
            DedupVerdict(
                key=key,
                disposition="accept",
                first_seen_at=now,
            )
        )

    def contains(self, key: IdempotencyKey, *, now: Instant) -> bool:
        """True when ``key`` is still inside the configured dedup window."""
        self._prune(now)
        prior = self._seen.get(key)
        if prior is None:
            return False
        return now.value_ns - prior.value_ns <= self.window.value_ns
