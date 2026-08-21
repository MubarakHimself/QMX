"""Secret references, secret values, and the SecretStore seam (COMP-QMF-CORE).

QMF components handle secret **references, never values**: a credential never
enters a repository, configuration artifact, journal, evidence, fingerprint, or
log (CT-21; L34, DEC-0136). This module defines the two credential value types and
the one port through which the single permitted holder — the venue adapter's
connection manager — reads and rotates a secret:

* :class:`SecretRef` — an **opaque minted id** under the same discipline as
  :class:`~qmf.core.identity.VenueId`: stable, never reused, and never encoding
  venue, broker, account, environment, or key material. It is the safe handle that
  *does* appear in refusal context, logs, health reports, and metrics; it is
  occurrence/display-only and never enters ``fp1`` identity (a credential is a
  deployment fact, never a market fact). Any human-readable label is a separate
  deployment field held outside evidence — never part of the ref.
* :class:`SecretValue` — the render-guarded holder of a plaintext secret. It
  **never renders its value**: ``repr``, ``str``, ``format``, and logging all yield
  the reference id, it is never serialized (pickling and the canonical serializer
  both refuse it), and the plaintext is reachable only through the one controlled
  method :meth:`SecretValue.reveal`. No public attribute or getter returns the
  plaintext (AR-37, AR-38; DEC-0136).
* :class:`SecretStore` — the core-defined :class:`typing.Protocol` port the
  composition root injects into the connection manager. It exposes **exactly two**
  operations — :meth:`~SecretStore.read` (value-or-refusal, an
  ``unavailable dependency`` refusal carrying the reference id, never the value)
  and :meth:`~SecretStore.atomic_replace` (rotation is store-before-discard,
  AR-38). No getter path returns a plaintext value outside :class:`SecretValue`'s
  controlled access. ``qmf-core`` holds no secret value itself and performs no I/O:
  the store is a seam, and a real one is wired at the composition root (AD-15,
  DEC-0138).

Every value type follows the one CT-04 construction pattern: an **unchecked
constructor** for trusted internal use plus a validating :meth:`try_create`
factory returning ``Result[T] = Ok[T] | TypedRefusal`` (DEC-0109).

Stdlib only (DEC-0104). Immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NoReturn, Protocol, runtime_checkable

from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "SecretRef",
    "SecretStore",
    "SecretValue",
]


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a secret-value factory returns.

    ``retryability`` is ``no`` — a malformed reference or an empty secret is a
    caller mistake, not a transient condition — and ``context`` always names the
    offending ``field`` and a human-legible ``reason`` (returned, never raised;
    CT-04; DEC-0109). The offending *value* is never echoed for a secret.
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_token(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    Presence-only, like the identity tokens: the returned token is the caller's
    string **verbatim** — never stripped, cased, or parsed — so an opaque reference
    is stored exactly as minted.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


@dataclass(frozen=True, slots=True)
class SecretRef:
    """An opaque, operator-minted credential reference (CT-21; DEC-0136).

    The reference id is the *safe* handle: it is what appears in refusal context,
    logs, health reports, and metrics, and it is stored verbatim and never parsed.
    Stability, non-reuse, and non-derivation from venue/broker/account/environment/
    key material are operator disciplines this type cannot enforce; construction
    validates only that the token is a non-empty opaque string. A secret reference
    is occurrence/display-only and never enters ``fp1`` identity — it deliberately
    exposes no ``fp1_identity``, so fingerprinting one is refused rather than
    silently folding a credential into a market fact.
    """

    value: str

    @classmethod
    def try_create(cls, value: object) -> Result[SecretRef]:
        """Validate and build a :class:`SecretRef`, returning value-or-refusal."""
        token = _clean_token(value)
        if token is None:
            return _invalid(
                "value",
                "a SecretRef is a non-empty opaque token; it is operator-minted, "
                "stable, and never encodes venue, broker, account, environment, or "
                "key material",
                given=repr(value),
            )
        return Ok(cls(token))


class SecretValue:
    """A render-guarded holder of a plaintext secret (CT-21; AR-37, DEC-0136).

    The value **never renders**: :meth:`__repr__`, :meth:`__str__`,
    :meth:`__format__`, and logging all yield the reference id and never the
    secret, and the value is never serialized — pickling raises and the canonical
    ``fp1`` serializer refuses it as unsupported identity content. The plaintext is
    reachable only through the single controlled method :meth:`reveal`; there is no
    public attribute or getter that returns it, so a credential cannot leak through
    ordinary access, formatting, or logging.

    Not a frozen dataclass, deliberately: a dataclass would expose the secret as a
    public field. The secret lives in a private slot and the instance is immutable
    (:meth:`__setattr__` and :meth:`__delattr__` refuse post-construction change).
    The unchecked constructor is the trusted-internal path; :meth:`try_create`
    validates. The sole component permitted to hold one in memory in production is
    the venue adapter's connection manager, for a session's lifetime; ``qmf-core``
    holds none (DEC-0136, DEC-0138).
    """

    __slots__ = ("_ref", "_secret")

    # Slot attribute types (annotation-only; the slot descriptors are created by
    # __slots__, these just give the private fields their static types).
    _ref: SecretRef
    _secret: str

    def __init__(self, ref: SecretRef, secret: str) -> None:
        object.__setattr__(self, "_ref", ref)
        object.__setattr__(self, "_secret", secret)

    @classmethod
    def try_create(cls, ref: object, secret: object) -> Result[SecretValue]:
        """Validate and build a :class:`SecretValue`, returning value-or-refusal.

        The ``ref`` must be a :class:`SecretRef` and ``secret`` a non-empty string.
        A refusal never echoes the secret — only the offending field is named
        (CT-04; DEC-0109). The absence of a credential is an ``unavailable
        dependency`` refusal at the store boundary, never a null or empty
        SecretValue (CT-21).
        """
        if not isinstance(ref, SecretRef):
            return _invalid(
                "ref",
                "a SecretValue names the SecretRef it is the value of",
                given=repr(ref),
            )
        if not isinstance(secret, str) or secret == "":
            # The secret itself is never echoed; only its presence/type is reported.
            return _invalid(
                "secret",
                "a SecretValue holds a non-empty plaintext secret",
                given=type(secret).__name__,
            )
        return Ok(cls(ref, secret))

    @property
    def ref(self) -> SecretRef:
        """The :class:`SecretRef` this value belongs to — the safe, renderable
        handle. This getter returns the reference, never the plaintext."""
        return self._ref

    def reveal(self) -> str:
        """The **only** path to the plaintext secret (controlled access; AR-37).

        Every other access — attribute read, ``repr``/``str``/``format``,
        serialization — yields the reference id or refuses. Call this only inside
        the connection manager, at the moment the secret is handed to the venue
        client; never store, log, or return the result across a boundary.
        """
        return self._secret

    def __setattr__(self, name: str, value: object) -> NoReturn:
        raise AttributeError("a SecretValue is immutable")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("a SecretValue is immutable")

    def __repr__(self) -> str:
        return f"SecretValue(ref={self._ref.value!r})"

    def __str__(self) -> str:
        return f"SecretValue(ref={self._ref.value})"

    def __format__(self, format_spec: str) -> str:
        # Ignore the spec entirely: no format spec may coax out the secret.
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SecretValue):
            return NotImplemented
        return self._ref == other._ref and self._secret == other._secret

    def __hash__(self) -> int:
        # Keyed on the reference only — equal values share a reference and so a
        # hash, and the secret never enters the hash table's key material.
        return hash(self._ref)

    def __reduce_ex__(self, protocol: object) -> NoReturn:
        # Block every pickle protocol (and copy, which routes through it): a
        # SecretValue is never serialized, so the secret can never reach a byte
        # stream (CT-21, AR-37).
        raise TypeError("a SecretValue is never serialized (AR-37; DEC-0136)")


@runtime_checkable
class SecretStore(Protocol):
    """The core-defined secret port, injected at the composition root (CT-21;
    AR-37, AR-38, DEC-0136, DEC-0138).

    Exposes **exactly two** operations and no plaintext getter:

    * :meth:`read` — return the current :class:`SecretValue` for a reference, or an
      ``unavailable dependency`` typed refusal carrying the reference id (never the
      value) when the credential is missing, expired, or rejected.
    * :meth:`atomic_replace` — rotate a credential **store-before-discard**: the new
      secret is durably stored before the old is discarded (AR-38). A failed store
      after rotation is an ``unavailable dependency`` refusal (retryable
      ``after-condition`` = successful store or operator re-provision) that its
      caller turns into an alarm and a command-pipe block.

    A definitions-only seam: ``qmf-core`` performs no I/O and holds no secret. The
    composition root injects a real store, and the connection manager is its sole
    holder — nothing imports this port to become a dependency edge (AD-15).
    """

    def read(self, ref: SecretRef, /) -> Result[SecretValue]:  # pragma: no cover - protocol seam
        """Read the current secret value for ``ref`` (value-or-refusal)."""
        ...

    def atomic_replace(
        self, ref: SecretRef, new_value: SecretValue, /
    ) -> Result[SecretRef]:  # pragma: no cover - protocol seam
        """Rotate the secret for ``ref`` store-before-discard (value-or-refusal)."""
        ...
