"""Code-declared Credential Broker allowlist (AD-24; DEC-0323; FR-Q45).

Shipped in ``qma-core`` as source — never settings, never a plugin contribution,
never a UI-editable variable, and never widened by a Mission, Role, or permission
mode. Exact-reference resolution only; venue/broker/exchange/trading-node/
platform-registry credentials are outside QMA's namespace.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from qma.core.refusals.variants import CredentialOutOfScope

__all__ = [
    "ALLOWED_CREDENTIAL_REF_PREFIXES",
    "CREDENTIAL_ALLOWLIST_OWNER",
    "CredentialAllowlistCategory",
    "CredentialAllowlistError",
    "OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES",
    "assert_allowlist_not_widenable",
    "classify_credential_ref",
    "is_credential_ref_allowed",
    "refuse_credential_out_of_scope",
]


class CredentialAllowlistCategory(StrEnum):
    """Closed allowlist categories — the entire broker scope (DEC-0323)."""

    MODEL_INFERENCE = "model_inference"
    COMPUTE_SANDBOX = "compute_sandbox"
    CORPUS_KNOWLEDGE = "corpus_knowledge"
    TELEMETRY = "telemetry"


CREDENTIAL_ALLOWLIST_OWNER: Final[str] = "AD-24"

# Exact-reference prefixes admitted by the broker. Membership is the allowlist.
ALLOWED_CREDENTIAL_REF_PREFIXES: Final[frozenset[str]] = frozenset(
    {
        "cred://models/",
        "cred://inference/",
        "cred://compute/",
        "cred://sandbox/",
        "cred://corpus/",
        "cred://knowledge/",
        "cred://telemetry/",
    }
)

_PREFIX_TO_CATEGORY: Final[dict[str, CredentialAllowlistCategory]] = {
    "cred://models/": CredentialAllowlistCategory.MODEL_INFERENCE,
    "cred://inference/": CredentialAllowlistCategory.MODEL_INFERENCE,
    "cred://compute/": CredentialAllowlistCategory.COMPUTE_SANDBOX,
    "cred://sandbox/": CredentialAllowlistCategory.COMPUTE_SANDBOX,
    "cred://corpus/": CredentialAllowlistCategory.CORPUS_KNOWLEDGE,
    "cred://knowledge/": CredentialAllowlistCategory.CORPUS_KNOWLEDGE,
    "cred://telemetry/": CredentialAllowlistCategory.TELEMETRY,
}

# Outside QMA's namespace — resolvable by no QMA component under any mode.
OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES: Final[frozenset[str]] = frozenset(
    {
        "cred://venue/",
        "cred://broker/",
        "cred://exchange/",
        "cred://trading-node/",
        "cred://platform-registry/",
    }
)


class CredentialAllowlistError(ValueError):
    """Raised when the allowlist constant is misused or illegally widened."""


def classify_credential_ref(credential_ref: str) -> CredentialAllowlistCategory | None:
    """Return the allowlist category for an exact reference, or ``None``."""
    for prefix, category in _PREFIX_TO_CATEGORY.items():
        if credential_ref.startswith(prefix) and len(credential_ref) > len(prefix):
            return category
    return None


def is_credential_ref_allowed(credential_ref: object) -> bool:
    """True only when ``credential_ref`` is an exact allowlisted reference."""
    if not isinstance(credential_ref, str) or not credential_ref:
        return False
    if any(credential_ref.startswith(prefix) for prefix in OUT_OF_SCOPE_CREDENTIAL_REF_PREFIXES):
        return False
    return classify_credential_ref(credential_ref) is not None


def refuse_credential_out_of_scope(credential_ref: str) -> CredentialOutOfScope:
    """Build ``CredentialOutOfScope`` naming the refused reference."""
    return CredentialOutOfScope.of(credential_ref=credential_ref)


def assert_allowlist_not_widenable(
    proposed: frozenset[str] | set[str] | None = None,
) -> None:
    """Refuse any attempt to treat a wider prefix set as the allowlist.

    The allowlist is the frozenset ``ALLOWED_CREDENTIAL_REF_PREFIXES``. Callers
    may not supply a superset; a ``None`` check pins the constant itself.
    """
    if proposed is None:
        if not ALLOWED_CREDENTIAL_REF_PREFIXES:
            raise CredentialAllowlistError("credential allowlist must be non-empty")
        return
    resolved = frozenset(proposed)
    if not resolved <= ALLOWED_CREDENTIAL_REF_PREFIXES:
        extras = sorted(resolved - ALLOWED_CREDENTIAL_REF_PREFIXES)
        raise CredentialAllowlistError(
            "credential allowlist is code-declared and may not be widened; "
            f"rejected extras={extras!r} (owner={CREDENTIAL_ALLOWLIST_OWNER})"
        )
