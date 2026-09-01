"""Credential Broker — references never values (CT-45; AD-24; FR-Q45/FR-Q46).

Resolves exact credential references from an OS secret store behind a backend
interface. Windows Credential Manager is the sole v1 backend. Resolution is
callable only from the adapter layer and never enumerates, searches, lists, or
globs the secret store.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from typing import Final, Protocol, runtime_checkable

from qma.core.barriers.credential_allowlist import (
    is_credential_ref_allowed,
    refuse_credential_out_of_scope,
)
from qma.core.plugins.credential import CredentialRef, CredentialRefError, parse_credential_ref
from qma.daemon.proxy.egress import AdapterLayerCaller, EgressFrame
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "WINDOWS_CREDENTIAL_MANAGER_BACKEND",
    "CredentialBackend",
    "CredentialBroker",
    "MemoryCredentialBackend",
    "WindowsCredentialManagerBackend",
]

WINDOWS_CREDENTIAL_MANAGER_BACKEND: Final[str] = "windows_credential_manager"


def _unavailable(credential_ref: str, reason: str) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "credential_ref": credential_ref,
            "reason": reason,
            "backend": WINDOWS_CREDENTIAL_MANAGER_BACKEND,
        },
    )


@runtime_checkable
class CredentialBackend(Protocol):
    """OS secret-store seam — exact-reference read only (DEC-0323).

    Implementations must not expose enumerate, search, list, or glob.
    """

    @property
    def backend_id(self) -> str:
        """Stable backend identity; v1 is Windows Credential Manager only."""
        ...

    def read_exact(self, credential_ref: str) -> Result[str]:
        """Return the secret for an exact reference, or a typed refusal."""
        ...


@dataclass
class MemoryCredentialBackend:
    """In-memory exact-reference backend for tests — never enumerates."""

    _values: MutableMapping[str, str] = field(default_factory=dict)
    backend_id: str = WINDOWS_CREDENTIAL_MANAGER_BACKEND

    def put(self, credential_ref: str, secret: str) -> None:
        if not secret:
            raise ValueError("secret must be non-empty")
        self._values[credential_ref] = secret

    def read_exact(self, credential_ref: str) -> Result[str]:
        value = self._values.get(credential_ref)
        if value is None:
            return _unavailable(credential_ref, "credential reference not present in store")
        return Ok(value)


@dataclass(frozen=True, slots=True)
class WindowsCredentialManagerBackend:
    """Sole v1 Credential Broker backend (L34; DEC-0323).

    Composition roots inject a reader that performs the OS CredRead. The broker
    never calls enumerate/search/list/glob APIs through this seam.
    """

    _reader: Mapping[str, str] | None = None
    backend_id: str = WINDOWS_CREDENTIAL_MANAGER_BACKEND

    def read_exact(self, credential_ref: str) -> Result[str]:
        store = self._reader
        if store is None:
            return _unavailable(
                credential_ref,
                "Windows Credential Manager reader is not wired at the composition root",
            )
        value = store.get(credential_ref)
        if value is None or value == "":
            return _unavailable(
                credential_ref,
                "Windows Credential Manager has no exact match for this reference",
            )
        return Ok(value)


class CredentialBroker:
    """Exact-reference Credential Broker over a code-declared allowlist."""

    def __init__(self, backend: CredentialBackend) -> None:
        if backend.backend_id != WINDOWS_CREDENTIAL_MANAGER_BACKEND:
            raise ValueError(
                "Windows Credential Manager is the sole v1 Credential Broker backend "
                f"(got {backend.backend_id!r})"
            )
        # Guard: backend must not advertise ambient enumeration surfaces.
        for forbidden in ("enumerate", "search", "list", "glob", "keys", "items"):
            if callable(getattr(backend, forbidden, None)):
                raise ValueError(
                    f"CredentialBackend must not expose {forbidden!r}; "
                    "exact-reference resolution only (AD-24)"
                )
        self._backend = backend

    @property
    def backend_id(self) -> str:
        return self._backend.backend_id

    def resolve(
        self,
        credential_ref: object,
        *,
        caller: AdapterLayerCaller,
    ) -> Result[EgressFrame]:
        """Resolve a reference into an adapter-layer egress frame (FR-Q45/FR-Q46).

        Refuses out-of-scope references with ``CredentialOutOfScope``. Callable
        only when ``caller`` proves the adapter layer.
        """
        if not isinstance(caller, AdapterLayerCaller):
            return policy_rejection(
                "caller",
                "broker resolution is callable only from the adapter layer "
                "(model_proxy or provider_adapter); hooks, plugins, and graphs "
                "expose credential_ref only (AD-24; FR-Q46)",
                given=repr(caller),
            )
        try:
            parsed: CredentialRef = parse_credential_ref(credential_ref)
        except CredentialRefError as exc:
            return invalid_input("credential_ref", str(exc), given=repr(credential_ref))

        ref_str = str(parsed)
        if not is_credential_ref_allowed(ref_str):
            return refuse_credential_out_of_scope(ref_str)

        outcome = self._backend.read_exact(ref_str)
        if not isinstance(outcome, Ok):
            return outcome
        return Ok(EgressFrame(parsed, outcome.value))
