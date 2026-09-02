"""One-refresher-per-reference rotation gate (TN-12 / DEC-0222).

Token refresh is keyed by opaque credential reference, never by connection.
At most one ``atomic_replace`` is in flight per reference; other sessions are
readers. Store-before-discard is enforced by the SecretStore, not this gate.
"""

from __future__ import annotations

from qmf.core.refusal import Ok, Result
from qmf.core.secret import SecretRef

from qmn.secrets._refuse import policy

__all__ = ["RotationGate"]


class RotationGate:
    """Process-local one-writer lock keyed by ``SecretRef.value``."""

    def __init__(self) -> None:
        self._inflight: set[str] = set()

    def acquire(self, ref: SecretRef) -> Result[None]:
        """Begin a refresh for ``ref``; refuse if one is already in flight."""
        key = ref.value
        if key in self._inflight:
            return policy(
                "refresher",
                "at most one refresh is in flight per credential reference",
                failure_id="secrets.rotation.in_flight",
                secret_ref=key,
            )
        self._inflight.add(key)
        return Ok(None)

    def release(self, ref: SecretRef) -> None:
        """End the in-flight refresh for ``ref`` (success or failed store)."""
        self._inflight.discard(ref.value)

    def in_flight(self, ref: SecretRef) -> bool:
        """Whether a refresher currently holds ``ref`` (boolean, never a value)."""
        return ref.value in self._inflight
