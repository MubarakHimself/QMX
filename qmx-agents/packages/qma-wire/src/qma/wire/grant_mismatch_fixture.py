"""Story 59.5 — grant refuses the wrong instance or config revision.

A GrantRecord bound to ``instance_id`` / ``config_revision`` (Story 54.4) cannot
be pointed at another target. An InvocationEnvelope that cites a different
instance or config is typed ``GRANT_MISMATCH`` before execution (FR-WF-73;
FR-WF-18; RC-03). The host does not silently retarget. GAP-0100 chrome is not
shipped; mutmut score is not architecture proof (FR-WF-74). COMP-QMA-WIRE owns
the fixture. Additive CT-40 only.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar, Final

from qma.core.operations import OperationDescriptor, public_operation_descriptors
from qma.core.refusals.variants import GrantMismatch
from qma.wire.grant_record import HostGrantLedger
from qma.wire.invocation_envelope import (
    AuthoritativeStores,
    BoundInvocation,
    ContributionRecord,
    GrantRecord,
    InstanceRecord,
    PublicCallTransport,
    compute_input_hash,
    dispatch_public_call,
)
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "GRANT_MISMATCH_FIXTURE_OWNER",
    "GRANT_MISMATCH_GAP",
    "GRANT_MISMATCH_GAP_0100",
    "GRANT_MISMATCH_MUTMUT_IS_PROOF",
    "GRANT_MISMATCH_NEW_CT_MINTED",
    "GRANT_MISMATCH_SILENT_RETARGET",
    "GrantMismatchFixture",
    "GrantMismatchWorld",
    "grant_mismatch_fixture_identity",
    "refuse_gap_0100_readiness_dashboard",
    "refuse_silent_grant_retarget",
]


GRANT_MISMATCH_FIXTURE_OWNER: Final[str] = "COMP-QMA-WIRE"
GRANT_MISMATCH_GAP: Final[str] = "GAP-0100"
GRANT_MISMATCH_GAP_0100: Final[bool] = False
GRANT_MISMATCH_MUTMUT_IS_PROOF: Final[bool] = False
GRANT_MISMATCH_NEW_CT_MINTED: Final[bool] = False
GRANT_MISMATCH_SILENT_RETARGET: Final[bool] = False

_OP_ID: Final[str] = "qmb.analysis.project"
_CONTRIBUTION: Final[Mapping[str, str]] = MappingProxyType(
    {"qualified_id": "analysis-backtest:qmb", "package_version": "0.1.0"}
)
_PAYLOAD: Final[Mapping[str, object]] = MappingProxyType({"run_fp1": "run-1"})
_GRANT_ID: Final[str] = "grant:1"
_BOUND_INSTANCE: Final[str] = "inst:1"
_BOUND_REVISION: Final[int] = 4
_OTHER_INSTANCE: Final[str] = "inst:2"
_OTHER_REVISION: Final[int] = 5
_EXPIRES: Final[str] = "2099-01-01T00:00:00Z"
_CHROME_REASON: Final[str] = (
    "GAP-0100 readiness dashboard chrome is refused; mutmut score is not "
    "architecture proof (FR-WF-74; NFR-WF-07)"
)
_RETARGET_REASON: Final[str] = (
    "a valid GrantRecord cannot be pointed at another instance or config revision (FR-WF-73; RC-03)"
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


def refuse_gap_0100_readiness_dashboard(**extra: object) -> TypedRefusal:
    """GAP-0100 chrome is not this story (FR-WF-74)."""
    field = str(extra.pop("field", "readiness_dashboard"))
    extra.setdefault("gap", GRANT_MISMATCH_GAP)
    extra.setdefault("gap_0100", GRANT_MISMATCH_GAP_0100)
    extra.setdefault("mutmut_is_architecture_proof", GRANT_MISMATCH_MUTMUT_IS_PROOF)
    extra.setdefault("new_ct_minted", GRANT_MISMATCH_NEW_CT_MINTED)
    extra.setdefault("owner", GRANT_MISMATCH_FIXTURE_OWNER)
    return _unsupported(field, _CHROME_REASON, **extra)


def refuse_silent_grant_retarget(
    *,
    grant_id: object,
    field: object = "instance_id",
    **extra: object,
) -> GrantMismatch:
    """Named refuse: a valid grant is not retargeted (FR-WF-73)."""
    token = grant_id if isinstance(grant_id, str) else repr(grant_id)
    name = field if isinstance(field, str) else "instance_id"
    extra.setdefault("retargeted", GRANT_MISMATCH_SILENT_RETARGET)
    extra.setdefault("substituted", False)
    extra.setdefault("detail", _RETARGET_REASON)
    return GrantMismatch.of(field=name, grant_id=token, **extra)


def grant_mismatch_fixture_identity() -> Mapping[str, object]:
    """Identity-bearing fixture schema. Package SemVer is omitted."""
    return MappingProxyType(
        {
            "grant_mismatch_fixture_owner": GRANT_MISMATCH_FIXTURE_OWNER,
            "grant_mismatch_gap": GRANT_MISMATCH_GAP,
            "grant_mismatch_gap_0100": GRANT_MISMATCH_GAP_0100,
            "grant_mismatch_mutmut_is_proof": GRANT_MISMATCH_MUTMUT_IS_PROOF,
            "grant_mismatch_new_ct_minted": GRANT_MISMATCH_NEW_CT_MINTED,
            "grant_mismatch_silent_retarget": GRANT_MISMATCH_SILENT_RETARGET,
        }
    )


def _descriptor() -> Result[OperationDescriptor]:
    for item in public_operation_descriptors():
        if item.op_id == _OP_ID and item.version == 1:
            return Ok(item)
    return _invalid("op_id", "qmb.analysis.project v1 descriptor is required", op_id=_OP_ID)


def _envelope_payload(*, input_hash: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "logical_invocation_id": "inv:1",
        "attempt_id": 1,
        "op_id": _OP_ID,
        "op_version": 1,
        "contribution": dict(_CONTRIBUTION),
        "instance_id": _BOUND_INSTANCE,
        "config_revision": _BOUND_REVISION,
        "caller_session_ref": "psess:caller",
        "grant_id": _GRANT_ID,
        "effect_class": "read",
        "idempotency_key": "idem:1",
        "reconcile_policy": "query-then-decide",
        "input_hash": input_hash,
        "call_depth": 0,
    }
    payload.update(overrides)
    return payload


@dataclass(frozen=True, slots=True)
class GrantMismatchWorld:
    """Bound grant plus live sibling instance/config targets."""

    grant: GrantRecord
    stores: AuthoritativeStores
    matching_envelope: Mapping[str, object]
    payload: Mapping[str, object]
    ledger: HostGrantLedger
    bound_instance: InstanceRecord
    other_instance: InstanceRecord
    other_revision: InstanceRecord

    def aliased_stores(self) -> AuthoritativeStores:
        """Lookup key matches the grant; the record identity is a different instance."""
        return AuthoritativeStores(
            contributions=dict(self.stores.contributions),
            descriptors=dict(self.stores.descriptors),
            grants=dict(self.stores.grants),
            instances={
                (self.bound_instance.instance_id, self.bound_instance.config_revision): (
                    self.other_instance
                ),
                (self.other_instance.instance_id, self.other_instance.config_revision): (
                    self.other_instance
                ),
                (self.other_revision.instance_id, self.other_revision.config_revision): (
                    self.other_revision
                ),
            },
        )


def _bootstrap() -> Result[GrantMismatchWorld]:
    descriptor = _descriptor()
    if is_refusal(descriptor):
        return descriptor
    hashed = compute_input_hash(dict(_PAYLOAD), descriptor=descriptor.value)
    if is_refusal(hashed):
        return hashed
    ledger = HostGrantLedger()
    minted = ledger.mint(
        issuer="host",
        grant_id=_GRANT_ID,
        principal="operator",
        audience="psess:caller",
        contribution=dict(_CONTRIBUTION),
        instance_id=_BOUND_INSTANCE,
        config_revision=_BOUND_REVISION,
        op_id=_OP_ID,
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1", "as_of"]},
        expires_at=_EXPIRES,
    )
    if is_refusal(minted):
        return minted
    contribution = ContributionRecord(
        qualified_id=_CONTRIBUTION["qualified_id"],
        package_version=_CONTRIBUTION["package_version"],
        availability="enabled",
    )
    bound = InstanceRecord(instance_id=_BOUND_INSTANCE, config_revision=_BOUND_REVISION)
    other_instance = InstanceRecord(instance_id=_OTHER_INSTANCE, config_revision=_BOUND_REVISION)
    other_revision = InstanceRecord(instance_id=_BOUND_INSTANCE, config_revision=_OTHER_REVISION)
    stores = AuthoritativeStores(
        contributions={contribution.as_tuple(): contribution},
        descriptors={(descriptor.value.op_id, descriptor.value.version): descriptor.value},
        grants={minted.value.grant_id: minted.value},
        instances={
            (bound.instance_id, bound.config_revision): bound,
            (other_instance.instance_id, other_instance.config_revision): other_instance,
            (other_revision.instance_id, other_revision.config_revision): other_revision,
        },
    )
    envelope = MappingProxyType(_envelope_payload(input_hash=hashed.value))
    return Ok(
        GrantMismatchWorld(
            grant=minted.value,
            stores=stores,
            matching_envelope=envelope,
            payload=_PAYLOAD,
            ledger=ledger,
            bound_instance=bound,
            other_instance=other_instance,
            other_revision=other_revision,
        )
    )


class GrantMismatchFixture:
    """Safety fixture: wrong instance/config is GRANT_MISMATCH before execute."""

    owner: ClassVar[str] = GRANT_MISMATCH_FIXTURE_OWNER
    gap_0100: ClassVar[bool] = GRANT_MISMATCH_GAP_0100
    mutmut_is_proof: ClassVar[bool] = GRANT_MISMATCH_MUTMUT_IS_PROOF
    silent_retarget: ClassVar[bool] = GRANT_MISMATCH_SILENT_RETARGET
    new_ct_minted: ClassVar[bool] = GRANT_MISMATCH_NEW_CT_MINTED

    def world(self) -> Result[GrantMismatchWorld]:
        return _bootstrap()

    def envelope_for(
        self,
        world: GrantMismatchWorld,
        **overrides: object,
    ) -> Mapping[str, object]:
        body = dict(world.matching_envelope)
        body.update(overrides)
        return MappingProxyType(body)

    def dispatch(
        self,
        world: GrantMismatchWorld,
        envelope: object,
        *,
        transport: object = PublicCallTransport.IN_PROCESS,
        stores: AuthoritativeStores | None = None,
        execute: Callable[[BoundInvocation], None] | None = None,
    ) -> Result[BoundInvocation]:
        return dispatch_public_call(
            transport=transport,
            envelope=envelope,
            payload=world.payload,
            stores=world.stores if stores is None else stores,
            execute=execute,
        )

    def dispatch_matching(
        self,
        *,
        transport: object = PublicCallTransport.IN_PROCESS,
        execute: Callable[[BoundInvocation], None] | None = None,
    ) -> Result[BoundInvocation]:
        world = self.world()
        if is_refusal(world):
            return world
        return self.dispatch(
            world.value,
            world.value.matching_envelope,
            transport=transport,
            execute=execute,
        )

    def dispatch_wrong_instance(
        self,
        *,
        transport: object = PublicCallTransport.IN_PROCESS,
        execute: Callable[[BoundInvocation], None] | None = None,
    ) -> Result[BoundInvocation]:
        world = self.world()
        if is_refusal(world):
            return world
        envelope = self.envelope_for(
            world.value,
            instance_id=world.value.other_instance.instance_id,
            idempotency_key="idem:instance",
        )
        return self.dispatch(world.value, envelope, transport=transport, execute=execute)

    def dispatch_wrong_config(
        self,
        *,
        transport: object = PublicCallTransport.IN_PROCESS,
        execute: Callable[[BoundInvocation], None] | None = None,
    ) -> Result[BoundInvocation]:
        world = self.world()
        if is_refusal(world):
            return world
        envelope = self.envelope_for(
            world.value,
            config_revision=world.value.other_revision.config_revision,
            idempotency_key="idem:config",
        )
        return self.dispatch(world.value, envelope, transport=transport, execute=execute)

    def dispatch_aliased_instance(
        self,
        *,
        execute: Callable[[BoundInvocation], None] | None = None,
    ) -> Result[BoundInvocation]:
        world = self.world()
        if is_refusal(world):
            return world
        return self.dispatch(
            world.value,
            world.value.matching_envelope,
            stores=world.value.aliased_stores(),
            execute=execute,
        )

    def retarget_grant(
        self,
        *,
        instance_id: str = _OTHER_INSTANCE,
        config_revision: int | None = None,
    ) -> TypedRefusal:
        world = self.world()
        if is_refusal(world):
            return world
        changes: dict[str, object] = {"instance_id": instance_id}
        if config_revision is not None:
            changes["config_revision"] = config_revision
        return world.value.ledger.apply_upgrade(world.value.grant.grant_id, **changes)
