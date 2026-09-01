"""Schema check excluding secrets from hook/plugin/graph payloads (AD-24; FR-Q46).

Secrets are excluded from ``updated_input``, ``updated_output``, and
``injected_context`` by this schema check rather than author discipline. Those
surfaces may carry ``credential_ref`` strings only.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

from qma.core.plugins.credential import CredentialRefError, parse_credential_ref
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "FORBIDDEN_SECRET_PAYLOAD_KEYS",
    "HOOK_SECRET_EXCLUDED_FIELDS",
    "assert_no_secret_in_hook_payloads",
    "assert_no_secret_in_mapping",
]


FORBIDDEN_SECRET_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
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
        "resolved_secret",
    }
)

HOOK_SECRET_EXCLUDED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "updated_input",
        "updated_output",
        "injected_context",
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


def assert_no_secret_in_mapping(surface: object, *, path: str = "$") -> Result[None]:
    """Refuse mappings that place a resolved secret on a hook/graph surface."""
    if surface is None:
        return Ok(None)
    if not isinstance(surface, Mapping):
        return _invalid(
            "surface",
            "secret-excluded surface must be a mapping",
            path=path,
            given=repr(surface),
        )
    return _scan_mapping(cast("Mapping[object, object]", surface), path=path)


def assert_no_secret_in_hook_payloads(
    *,
    updated_input: Mapping[str, object] | None = None,
    updated_output: Mapping[str, object] | None = None,
    injected_context: Mapping[str, object] | None = None,
) -> Result[None]:
    """Schema-check the three secret-excluded HookResult fields (FR-Q46)."""
    for name, payload in (
        ("updated_input", updated_input),
        ("updated_output", updated_output),
        ("injected_context", injected_context),
    ):
        outcome = assert_no_secret_in_mapping(payload, path=f"$.{name}")
        if not isinstance(outcome, Ok):
            return outcome
    return Ok(None)


def _scan_mapping(mapping: Mapping[object, object], *, path: str) -> Result[None]:
    for key_obj, value in mapping.items():
        if not isinstance(key_obj, str):
            return _invalid("surface", "secret-excluded keys must be strings", path=path)
        key_lower = key_obj.lower()
        if key_lower in FORBIDDEN_SECRET_PAYLOAD_KEYS:
            return _policy(
                "secret_in_payload",
                "resolved secrets are excluded from updated_input, updated_output, "
                "and injected_context — carry credential_ref only (AD-24; FR-Q46)",
                path=f"{path}.{key_obj}",
                key=key_obj,
            )
        if key_lower == "credential_ref":
            if not isinstance(value, str):
                return _invalid(
                    "credential_ref",
                    "credential_ref must be a string reference",
                    path=f"{path}.{key_obj}",
                )
            try:
                parse_credential_ref(value)
            except CredentialRefError as exc:
                return _policy(
                    "secret_in_payload",
                    str(exc),
                    path=f"{path}.{key_obj}",
                )
            continue
        if isinstance(value, Mapping):
            nested = _scan_mapping(
                cast("Mapping[object, object]", value),
                path=f"{path}.{key_obj}",
            )
            if not isinstance(nested, Ok):
                return nested
        elif isinstance(value, str):
            lowered = value.lower()
            if lowered.startswith(("secret=", "password=", "token=", "bearer ")):
                return _policy(
                    "secret_in_payload",
                    "inline secret material is forbidden on hook/graph surfaces",
                    path=f"{path}.{key_obj}",
                )
    return Ok(None)
