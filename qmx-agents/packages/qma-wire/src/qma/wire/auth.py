"""Pre-protocol wire authentication by credential reference (CT-40; AD-24; FR-Q17).

Every client authenticates with a Credential-Broker-resolved credential before
protocol bytes. The wire carries only the credential reference — never a
resolved secret value — in envelopes, schema examples, traces, or diagnostics.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qma.core.plugins.credential import CredentialRef, CredentialRefError, parse_credential_ref
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "FORBIDDEN_SECRET_SURFACE_KEYS",
    "AuthenticatedWireSession",
    "assert_no_secret_on_wire_surface",
    "authenticate_before_protocol",
]


FORBIDDEN_SECRET_SURFACE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "secret",
        "secret_value",
        "password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "bearer",
        "credential_value",
        "resolved_credential",
    }
)


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class AuthenticatedWireSession:
    """Connection authenticated before protocol bytes; carries only the ref."""

    credential_ref: CredentialRef
    authenticated_before_protocol: bool = True

    def to_diagnostic(self) -> dict[str, object]:
        """Diagnostic surface — reference only, never a resolved secret."""
        return {
            "credential_ref": str(self.credential_ref),
            "authenticated_before_protocol": self.authenticated_before_protocol,
        }

    def to_trace(self) -> dict[str, object]:
        """Trace surface — reference only."""
        return self.to_diagnostic()


def authenticate_before_protocol(credential_ref: object) -> Result[AuthenticatedWireSession]:
    """Authenticate a client before any protocol bytes are accepted.

    ``credential_ref`` must be a broker-resolved *reference*. Inline secret
    shapes are refused; the returned session exposes only the reference.
    """
    try:
        parsed = parse_credential_ref(credential_ref)
    except CredentialRefError as exc:
        return _invalid("credential_ref", str(exc), given=repr(credential_ref))
    return Ok(
        AuthenticatedWireSession(
            credential_ref=parsed,
            authenticated_before_protocol=True,
        )
    )


def assert_no_secret_on_wire_surface(surface: object) -> Result[None]:
    """Refuse any mapping that places a secret value on a wire-facing surface.

    Covers envelopes, schema examples, traces, and diagnostics. Only credential
    *references* are permitted; forbidden key names and inline secret prefixes
    are hard refusals.
    """
    if not isinstance(surface, Mapping):
        return _invalid(
            "surface",
            "wire surface must be a mapping to scan for secret material",
            given=repr(surface),
        )
    return _scan_mapping(cast("Mapping[object, object]", surface), path="$")


def _scan_mapping(mapping: Mapping[object, object], *, path: str) -> Result[None]:
    for key_obj, value in mapping.items():
        if not isinstance(key_obj, str):
            return _invalid("surface", "wire surface keys must be strings", path=path)
        key_lower = key_obj.lower()
        if key_lower in FORBIDDEN_SECRET_SURFACE_KEYS:
            return _policy(
                "secret_on_wire",
                "secret values must not appear on a wire envelope, schema example, "
                "trace, or diagnostic — carry credential_ref only",
                path=f"{path}.{key_obj}",
                key=key_obj,
            )
        if key_lower == "credential_ref":
            if not isinstance(value, str):
                return _invalid(
                    "credential_ref",
                    "credential_ref on a wire surface must be a string reference",
                    path=f"{path}.{key_obj}",
                )
            try:
                parse_credential_ref(value)
            except CredentialRefError as exc:
                return _policy(
                    "secret_on_wire",
                    str(exc),
                    path=f"{path}.{key_obj}",
                )
            continue
        if isinstance(value, Mapping):
            nested = _scan_mapping(cast("Mapping[object, object]", value), path=f"{path}.{key_obj}")
            if not isinstance(nested, Ok):
                return nested
        elif isinstance(value, str):
            lowered = value.lower()
            if lowered.startswith(("secret=", "password=", "token=", "bearer ")):
                return _policy(
                    "secret_on_wire",
                    "inline secret material is forbidden on wire surfaces",
                    path=f"{path}.{key_obj}",
                )
    return Ok(None)
