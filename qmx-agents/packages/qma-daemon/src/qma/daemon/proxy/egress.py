"""Egress call frame for broker-resolved secrets (AD-24; DEC-0323; FR-Q46).

A resolved secret value exists only inside this frame and is never stored on,
attached to, or reachable from any object handed to a hook, plugin, or graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NoReturn, Self

from qma.core.plugins.credential import CredentialRef

__all__ = [
    "ADAPTER_LAYERS",
    "AdapterLayer",
    "AdapterLayerCaller",
    "EgressFrame",
    "EgressFrameError",
]

AdapterLayer = Literal["model_proxy", "provider_adapter"]
ADAPTER_LAYERS: frozenset[str] = frozenset({"model_proxy", "provider_adapter"})


class EgressFrameError(RuntimeError):
    """Raised when an egress frame is used outside its call window."""


@dataclass(frozen=True, slots=True)
class AdapterLayerCaller:
    """Proof that broker resolution was invoked from the adapter layer."""

    layer: AdapterLayer

    def __post_init__(self) -> None:
        if self.layer not in ADAPTER_LAYERS:
            msg = f"broker resolution is callable only from {sorted(ADAPTER_LAYERS)}"
            raise EgressFrameError(msg)


class EgressFrame:
    """Scoped holder for one resolved secret inside an adapter egress call.

    ``reveal`` is the only plaintext path and is valid only while the frame is
    entered. Exiting clears the secret; the frame never serializes it.
    """

    __slots__ = ("_credential_ref", "_closed", "_secret", "_entered")

    def __init__(self, credential_ref: CredentialRef, secret: str) -> None:
        if not secret:
            raise EgressFrameError("egress frame requires a non-empty secret")
        self._credential_ref = credential_ref
        self._secret = secret
        self._entered = False
        self._closed = False

    @property
    def credential_ref(self) -> CredentialRef:
        return self._credential_ref

    @property
    def is_open(self) -> bool:
        return self._entered and not self._closed

    def __enter__(self) -> Self:
        if self._closed:
            raise EgressFrameError("egress frame cannot be re-entered after close")
        self._entered = True
        return self

    def __exit__(self, *_exc: object) -> None:
        self._secret = ""
        self._entered = False
        self._closed = True

    def reveal(self) -> str:
        """Return the plaintext only while the egress frame is entered."""
        if not self._entered or self._closed or not self._secret:
            raise EgressFrameError(
                "resolved secret exists only inside an open egress call frame (AD-24)"
            )
        return self._secret

    def to_diagnostic(self) -> dict[str, object]:
        """Diagnostic surface — reference only, never the secret."""
        return {
            "credential_ref": str(self._credential_ref),
            "egress_open": self.is_open,
        }

    def __repr__(self) -> str:
        return f"EgressFrame(credential_ref={str(self._credential_ref)!r}, closed={self._closed})"

    def __str__(self) -> str:
        return self.__repr__()

    def __reduce_ex__(self, _protocol: object) -> NoReturn:
        raise TypeError("an EgressFrame is never serialized (AD-24; FR-Q46)")
