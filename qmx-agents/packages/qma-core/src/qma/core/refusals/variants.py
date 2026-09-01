"""Named QMA refusal variants of the qmf-core typed-refusal base (FR-Q05).

Each variant is defined once here under ``qma-core/refusals/``. Public boundaries
RETURN these values; they are never raised across a package boundary (CT-04;
DEC-0302).
"""

from __future__ import annotations

from typing import ClassVar, Final

from qma.core.refusals._base import QmaRefusal
from qmf.core.refusal import RefusalCategory, Retryability

__all__ = [
    "NAMED_REFUSAL_VARIANTS",
    "CredentialOutOfScope",
    "CursorScopeMismatch",
    "NoEligibleDeployment",
    "NoEligibleReviewer",
    "NoEnvironment",
    "NoMemoryProvider",
    "NonLoopbackProxy",
    "OperatorPrincipalRequired",
    "ProhibitedMoneyPathTool",
    "ProhibitedReachability",
    "ProvenanceShapeMismatch",
    "SlugUnavailable",
    "StaleSnapshot",
    "StoreVersionMismatch",
    "UnauthenticatedProxy",
    "UnknownHostRequest",
]


class NoMemoryProvider(QmaRefusal):
    """No MemoryProvider bound for the desk (AD-1 / AD-18)."""

    VARIANT: ClassVar[str] = "NoMemoryProvider"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.UNAVAILABLE_DEPENDENCY
    RETRYABILITY: ClassVar[Retryability] = Retryability.AFTER_CONDITION

    @classmethod
    def of(cls, *, desk: str) -> NoMemoryProvider:
        return cls.create(
            context={"desk": desk},
            after_condition_descriptor="a MemoryProvider is bound for the desk",
        )


class NoEnvironment(QmaRefusal):
    """ComputeRequirement kind has no registered environment (AD-17 / AD-25)."""

    VARIANT: ClassVar[str] = "NoEnvironment"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.UNAVAILABLE_DEPENDENCY
    RETRYABILITY: ClassVar[Retryability] = Retryability.AFTER_CONDITION

    @classmethod
    def of(cls, *, kind: str) -> NoEnvironment:
        return cls.create(
            context={"kind": kind},
            after_condition_descriptor="an ExecutionEnvironment providing the kind is registered",
        )


class SlugUnavailable(QmaRefusal):
    """desk_slug / quant_slug collision or reserved token (AD-7)."""

    VARIANT: ClassVar[str] = "SlugUnavailable"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.INVALID_INPUT

    @classmethod
    def of(cls, *, slug: str, slug_kind: str) -> SlugUnavailable:
        return cls.create(context={"slug": slug, "slug_kind": slug_kind})


class CursorScopeMismatch(QmaRefusal):
    """wire.attach cursor belongs to another scope (AD-5)."""

    VARIANT: ClassVar[str] = "CursorScopeMismatch"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.POLICY_REJECTION

    @classmethod
    def of(cls, *, cursor_scope: str, expected_scope: str) -> CursorScopeMismatch:
        return cls.create(
            context={"cursor_scope": cursor_scope, "expected_scope": expected_scope},
        )


class NoEligibleReviewer(QmaRefusal):
    """No Deployment qualifies under ReviewPolicy (AD-10 / AD-15)."""

    VARIANT: ClassVar[str] = "NoEligibleReviewer"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.UNAVAILABLE_DEPENDENCY

    @classmethod
    def of(cls, *, model_class: str) -> NoEligibleReviewer:
        return cls.create(context={"model_class": model_class})


class NoEligibleDeployment(QmaRefusal):
    """Filtered Deployment pool empty for the requested ModelClass (AD-15)."""

    VARIANT: ClassVar[str] = "NoEligibleDeployment"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.UNAVAILABLE_DEPENDENCY

    @classmethod
    def of(
        cls,
        *,
        model_class: str,
        unmet_constraint: str,
    ) -> NoEligibleDeployment:
        return cls.create(
            context={
                "model_class": model_class,
                "unmet_constraint": unmet_constraint,
            }
        )


class NonLoopbackProxy(QmaRefusal):
    """Proxy Deployment binds a non-loopback address (AD-15)."""

    VARIANT: ClassVar[str] = "NonLoopbackProxy"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.POLICY_REJECTION

    @classmethod
    def of(cls, *, address: str) -> NonLoopbackProxy:
        return cls.create(context={"address": address})


class UnauthenticatedProxy(QmaRefusal):
    """Loopback proxy accepts unauthenticated connections while disallowed (AD-15)."""

    VARIANT: ClassVar[str] = "UnauthenticatedProxy"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.POLICY_REJECTION

    @classmethod
    def of(cls, *, deployment_id: str) -> UnauthenticatedProxy:
        return cls.create(context={"deployment_id": deployment_id})


class ProhibitedMoneyPathTool(QmaRefusal):
    """Tool matches the act-level money-path deny-list at registration (AD-16)."""

    VARIANT: ClassVar[str] = "ProhibitedMoneyPathTool"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.POLICY_REJECTION

    @classmethod
    def of(
        cls,
        *,
        tool_id: str,
        matched_act: str | None = None,
        plugin_id: str | None = None,
    ) -> ProhibitedMoneyPathTool:
        context: dict[str, object] = {"tool_id": tool_id}
        if matched_act is not None:
            context["matched_act"] = matched_act
        if plugin_id is not None:
            context["plugin_id"] = plugin_id
        return cls.create(context=context)


class ProhibitedReachability(QmaRefusal):
    """Environment, image, host, or profile hits the AD-28 barrier (FR-Q47).

    Raised at registration or placement, never as a runtime hook deny.
    """

    VARIANT: ClassVar[str] = "ProhibitedReachability"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.POLICY_REJECTION

    @classmethod
    def of(
        cls,
        *,
        surface: str,
        reason: str,
        stage: str = "registration",
        host: str | None = None,
        kind: str | None = None,
        via: str | None = None,
        matched: str | None = None,
    ) -> ProhibitedReachability:
        context: dict[str, object] = {
            "surface": surface,
            "reason": reason,
            "stage": stage,
        }
        if host is not None:
            context["host"] = host
        if kind is not None:
            context["kind"] = kind
        if via is not None:
            context["via"] = via
        if matched is not None:
            context["matched"] = matched
        return cls.create(context=context)


class UnknownHostRequest(QmaRefusal):
    """host_request verb maps to no daemon-owned primitive (AD-14)."""

    VARIANT: ClassVar[str] = "UnknownHostRequest"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.UNSUPPORTED_CAPABILITY

    @classmethod
    def of(cls, *, verb: str) -> UnknownHostRequest:
        return cls.create(context={"verb": verb})


class ProvenanceShapeMismatch(QmaRefusal):
    """Citation evidence_confidence keys/count mismatch source declaration (AD-19)."""

    VARIANT: ClassVar[str] = "ProvenanceShapeMismatch"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.INVALID_INPUT

    @classmethod
    def of(
        cls,
        *,
        source_id: str,
        expected_keys: tuple[str, ...],
        given_keys: tuple[str, ...],
    ) -> ProvenanceShapeMismatch:
        return cls.create(
            context={
                "source_id": source_id,
                "expected_keys": list(expected_keys),
                "given_keys": list(given_keys),
            },
        )


class StaleSnapshot(QmaRefusal):
    """Retrieval against a CorpusSnapshot whose bytes QMA never copied (AD-19)."""

    VARIANT: ClassVar[str] = "StaleSnapshot"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.STALE_EVIDENCE

    @classmethod
    def of(cls, *, snapshot_ref: str) -> StaleSnapshot:
        return cls.create(context={"snapshot_ref": snapshot_ref})


class OperatorPrincipalRequired(QmaRefusal):
    """Human-gate command arrived from a machine principal (AD-24)."""

    VARIANT: ClassVar[str] = "OperatorPrincipalRequired"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.POLICY_REJECTION

    @classmethod
    def of(cls, *, command: str, principal_class: str) -> OperatorPrincipalRequired:
        return cls.create(
            context={"command": command, "principal_class": principal_class},
        )


class CredentialOutOfScope(QmaRefusal):
    """Credential reference not on the broker's allowlist (AD-24)."""

    VARIANT: ClassVar[str] = "CredentialOutOfScope"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.POLICY_REJECTION

    @classmethod
    def of(cls, *, credential_ref: str) -> CredentialOutOfScope:
        return cls.create(context={"credential_ref": credential_ref})


class StoreVersionMismatch(QmaRefusal):
    """Store lifecycle refused an unknown ``store_schema_version`` (AD-27).

    Context names the store and both schema versions — the version the daemon
    knows and the version stamped on the store (DEC-0326).
    """

    VARIANT: ClassVar[str] = "StoreVersionMismatch"
    CATEGORY: ClassVar[RefusalCategory] = RefusalCategory.STORAGE_FAILURE

    @classmethod
    def of(
        cls,
        *,
        store: str,
        expected_schema_version: int,
        store_schema_version: int,
    ) -> StoreVersionMismatch:
        return cls.create(
            context={
                "store": store,
                "expected_schema_version": expected_schema_version,
                "store_schema_version": store_schema_version,
            },
        )


NAMED_REFUSAL_VARIANTS: Final[tuple[type[QmaRefusal], ...]] = (
    NoMemoryProvider,
    NoEnvironment,
    SlugUnavailable,
    CursorScopeMismatch,
    NoEligibleReviewer,
    NoEligibleDeployment,
    NonLoopbackProxy,
    UnauthenticatedProxy,
    ProhibitedMoneyPathTool,
    ProhibitedReachability,
    UnknownHostRequest,
    ProvenanceShapeMismatch,
    StaleSnapshot,
    OperatorPrincipalRequired,
    CredentialOutOfScope,
    StoreVersionMismatch,
)
