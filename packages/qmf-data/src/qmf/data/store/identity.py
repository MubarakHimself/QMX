"""Content-addressed admission — the store's fp1 identity guard (AC2; DEC-0108).

Every artifact the store persists is keyed on its ``fp1:sha256:<hex>`` fingerprint,
never on a timestamp or a minted id. This module is the store's realization of the
Epic-1 ``GovernedEvidenceLedger`` pattern: **recompute the fingerprint of the
presented bytes before storing**, then decide the write with ``qmf-core``'s pure
``reconcile_write`` —

* an unseen fingerprint is ``stored``;
* a byte-identical re-write (the sandbox-merge normal case) is ``idempotent`` and
  accepted silently, with no second physical write; and
* a true collision — the same hash addressing differing bytes — is refused and
  alarmed, **never overwritten**.

:func:`admit` is the one orchestration point the four boundaries share. It stays
engine-agnostic: the caller injects a ``existing_bytes`` lookup and a ``persist``
sink, both of which may raise :class:`~qmf.data.store.engines.StoreEngineError` for
a physical failure — :func:`admit` lets that propagate so the boundary translates it
to a ``storage failure`` refusal (AC4). A physical write happens **only** on the
``stored`` decision, and never before the identity check clears.

Stdlib + qmf-core only.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from qmf.core import (
    Fingerprint,
    Ok,
    Result,
    WriteOutcome,
    canonical_bytes,
    fingerprint,
    is_ok,
    is_refusal,
    reconcile_write,
)
from qmf.data.store.refusals import invalid_input

__all__ = [
    "Admission",
    "WriteOutcome",
    "admit",
    "canonical_identity",
    "resolve_fingerprint",
]


def resolve_fingerprint(value: object) -> Result[Fingerprint]:
    """Resolve a read key to a :class:`Fingerprint`, or an ``invalid input`` refusal.

    Accepts a :class:`Fingerprint` or an ``fp1:sha256:<hex>`` string; the store keys
    every read on the fp1 fingerprint, never a timestamp or minted id (DEC-0108).
    """
    fp = _coerce_fingerprint(value)
    if fp is None:
        return invalid_input(
            "fingerprint",
            "a store key is a Fingerprint or an fp1:sha256:<hex> string",
            given=repr(value),
        )
    return Ok(fp)


@dataclass(frozen=True, slots=True)
class Admission:
    """The receipt of an admitted store write (AC2).

    ``outcome`` is ``stored`` (first write) or ``idempotent`` (byte-identical
    re-write accepted silently); a true collision is never an admission — it is
    refused. ``fingerprint`` is the artifact's fp1 identity and ``canonical`` the
    exact bytes hashed to produce it, so a boundary can hand the same bytes to its
    engine without re-serializing.
    """

    outcome: WriteOutcome
    fingerprint: Fingerprint
    canonical: bytes


def canonical_identity(content: object) -> Result[tuple[Fingerprint, bytes]]:
    """Serialize ``content`` to canonical bytes and its fp1 fingerprint, or refuse.

    Returns ``Ok((fingerprint, canonical_bytes))`` — the one canonical byte form and
    the fingerprint hashed from it — or the underlying ``invalid input`` refusal when
    the content carries a binary float, a null, a non-string key, or an unsupported
    type (identity numerics are integers; DEC-0108). Both halves route through
    ``qmf-core``'s single serializer, so identity is computed nowhere else.
    """
    canonical = canonical_bytes(content)
    if is_refusal(canonical):
        return canonical
    fp = fingerprint(content)
    if is_refusal(fp):  # pragma: no cover - canonical already succeeded, so this cannot
        return fp
    return Ok((fp.value, canonical.value))


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`Fingerprint` or a valid fp1 string, or ``None``."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    return parsed.value if is_ok(parsed) else None


def admit(
    content: object,
    *,
    existing_bytes: Callable[[str], bytes | None],
    persist: Callable[[Fingerprint, bytes], None],
    presented_fingerprint: object | None = None,
) -> Result[Admission]:
    """Admit a content-addressed write, deciding stored / idempotent / collision.

    ``content`` is canonicalized and fingerprinted (a float/null/unsupported value is
    an ``invalid input`` refusal). When the caller *presents* a fingerprint (a record
    that already carries its fp1), it is recomputed from the presented bytes and a
    mismatch is refused **before anything is stored** — so admitting bytes under the
    wrong fingerprint can never masquerade as a collision (DEC-0108). The stored bytes
    under this fingerprint (``existing_bytes`` may return ``None``) drive the pure
    ``reconcile_write`` decision: a first write calls ``persist``; a byte-identical
    re-write is silently idempotent; a true collision is refused and alarmed.

    ``existing_bytes`` and ``persist`` may raise
    :class:`~qmf.data.store.engines.StoreEngineError`; :func:`admit` does not catch it,
    so the boundary translates it to a ``storage failure`` refusal (AC4).
    """
    identity = canonical_identity(content)
    if is_refusal(identity):
        return identity
    fp, canonical = identity.value

    if presented_fingerprint is not None:
        presented = _coerce_fingerprint(presented_fingerprint)
        if presented is None:
            return invalid_input(
                "fingerprint",
                "a presented fingerprint is a Fingerprint or an fp1:sha256:<hex> string",
                given=repr(presented_fingerprint),
            )
        if presented.value != fp.value:
            return invalid_input(
                "fingerprint",
                "the presented fingerprint does not match the presented bytes; the "
                "store recomputes the fingerprint before storing, so a mismatched pair "
                "is refused rather than manufacturing a false collision (DEC-0108)",
                given=presented.value,
                computed=fp.value,
            )

    existing = existing_bytes(fp.digest)
    decision = reconcile_write(fp, canonical, existing)
    if is_refusal(decision):
        return decision
    if decision.value is WriteOutcome.STORED:
        persist(fp, canonical)
    return Ok(Admission(outcome=decision.value, fingerprint=fp, canonical=canonical))
