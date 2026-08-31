"""Reference-only credential type exposed on PluginContext (AD-24; DEC-0323).

A ``credential_ref`` is an opaque string reference. Resolved secret values never
appear on the plugin context, hook payloads, or graph objects.
"""

from __future__ import annotations

from typing import Final, NewType

__all__ = [
    "CredentialRef",
    "CredentialRefError",
    "parse_credential_ref",
]

CredentialRef = NewType("CredentialRef", str)

_MAX_REF_LEN: Final[int] = 256


class CredentialRefError(ValueError):
    """Raised when a value is not a valid credential reference string."""


def parse_credential_ref(value: object) -> CredentialRef:
    """Accept only a non-empty opaque reference string — never a secret value."""
    if not isinstance(value, str) or not value or value != value.strip():
        raise CredentialRefError(f"{value!r} is not a credential_ref")
    if len(value) > _MAX_REF_LEN:
        raise CredentialRefError("credential_ref exceeds maximum length")
    # Hard reject shapes that look like inline secret material rather than refs.
    lowered = value.lower()
    if lowered.startswith(("secret=", "password=", "token=", "bearer ")):
        raise CredentialRefError(
            "credential_ref must be a reference string, never a resolved secret"
        )
    return CredentialRef(value)
