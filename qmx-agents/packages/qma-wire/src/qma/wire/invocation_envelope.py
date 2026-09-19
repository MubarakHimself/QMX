"""InvocationEnvelope — additive CT-40 bound request context (Story 54.2).

Every public call carries the CONTRACTS §1b / cheap-veto A3 field set.
The envelope is signed/bound request context, not authority by assertion
(RC-03; FR-WF-17; FR-WF-18). Transport never bypasses it. Host resolve +
compare of contribution, descriptor, and GrantRecord happens before
execution. Crypto algorithm remains GAP-DESK-ENVELOPE-CRYPTO; mismatch
refuse is still required (NFR-WF-16). Not on the wire at inspect SHA
270e992 (DEC-0450; GAP-0096). No new CT (do not mint CT-52).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qma.core.operations.descriptor import OperationDescriptor
from qma.core.ports.permissions import nested_invocation_permissions
from qma.core.refusals.variants import (
    AmbiguousResolution,
    EnvelopeMismatch,
    GrantMismatch,
    InvocationEnvelopeRequired,
    StaleObservation,
)
from qma.core.vocabulary.enums import EffectClass, ReconcilePolicy
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.wire.auth import FORBIDDEN_SECRET_SURFACE_KEYS, assert_no_secret_on_wire_surface
from qma.wire.envelope import WireEnvelope
from qma.wire.invocation_idempotency import assert_child_logical_invocation_id
from qma.wire.schemas import validate_instance
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "AMBIGUOUS_RESOLUTION_TOKENS",
    "ENVELOPE_CRYPTO_ALGORITHM_SELECTED",
    "ENVELOPE_CRYPTO_GAP",
    "INVOCATION_ENVELOPE_CONTRACT",
    "INVOCATION_ENVELOPE_DTO_OWNER",
    "INVOCATION_ENVELOPE_FIELDS",
    "INVOCATION_ENVELOPE_INSPECT_SHAS",
    "INVOCATION_ENVELOPE_IS_AUTHORITY",
    "INVOCATION_ENVELOPE_NEW_CT_MINTED",
    "INVOCATION_ENVELOPE_OPTIONAL_FIELDS",
    "INVOCATION_ENVELOPE_REFUSED_CT",
    "INVOCATION_ENVELOPE_REQUIRED_FIELDS",
    "INVOCATION_ENVELOPE_SCHEMA",
    "INVOCATION_ENVELOPE_SCHEMA_FILE",
    "INVOCATION_ENVELOPE_SCHEMA_NAME",
    "INVOCATION_ENVELOPE_WIRED_AT_INSPECT_SHA",
    "PUBLIC_CALL_TRANSPORTS",
    "AuthoritativeStores",
    "BoundInvocation",
    "ContributionBinding",
    "ContributionRecord",
    "GrantRecord",
    "InstanceRecord",
    "InvocationEnvelope",
    "PublicCallTransport",
    "bind_invocation_envelope",
    "compute_input_hash",
    "dispatch_public_call",
    "parse_invocation_envelope",
    "public_call_from_cli",
    "public_call_from_wire",
    "public_call_in_process",
    "public_call_nested",
    "validate_input_payload",
    "validate_invocation_envelope",
]


INVOCATION_ENVELOPE_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
INVOCATION_ENVELOPE_CONTRACT: Final[str] = "CT-40"
INVOCATION_ENVELOPE_NEW_CT_MINTED: Final[bool] = False
INVOCATION_ENVELOPE_REFUSED_CT: Final[str] = "CT-52"
INVOCATION_ENVELOPE_SCHEMA: Final[str] = "qma.wire.invocation_envelope.v1"
INVOCATION_ENVELOPE_SCHEMA_NAME: Final[str] = "invocation_envelope"
INVOCATION_ENVELOPE_SCHEMA_FILE: Final[str] = "invocation_envelope.v1.schema.json"
INVOCATION_ENVELOPE_INSPECT_SHAS: Final[tuple[str, ...]] = ("270e992",)
INVOCATION_ENVELOPE_WIRED_AT_INSPECT_SHA: Final[bool] = False
INVOCATION_ENVELOPE_IS_AUTHORITY: Final[bool] = False
ENVELOPE_CRYPTO_GAP: Final[str] = "GAP-DESK-ENVELOPE-CRYPTO"
ENVELOPE_CRYPTO_ALGORITHM_SELECTED: Final[bool] = False

INVOCATION_ENVELOPE_FIELDS: Final[tuple[str, ...]] = (
    "logical_invocation_id",
    "attempt_id",
    "op_id",
    "op_version",
    "contribution",
    "instance_id",
    "config_revision",
    "caller_session_ref",
    "callee_session_ref",
    "grant_id",
    "effect_class",
    "idempotency_key",
    "reconcile_policy",
    "input_hash",
    "parent_logical_invocation_id",
    "call_depth",
)
INVOCATION_ENVELOPE_OPTIONAL_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "caller_session_ref",
        "callee_session_ref",
        "parent_logical_invocation_id",
    }
)
INVOCATION_ENVELOPE_REQUIRED_FIELDS: Final[tuple[str, ...]] = tuple(
    field
    for field in INVOCATION_ENVELOPE_FIELDS
    if field not in INVOCATION_ENVELOPE_OPTIONAL_FIELDS
)
AMBIGUOUS_RESOLUTION_TOKENS: Final[frozenset[str]] = frozenset(
    {"latest", "*", "current", "head", "newest"}
)
_SESSION_PREFIX: Final[str] = "psess:"
_FORBIDDEN_SESSION_PREFIX: Final[str] = "sess:"
_CONTRIBUTION_KEYS: Final[frozenset[str]] = frozenset({"qualified_id", "package_version"})
_UNAVAILABLE_AVAILABILITY: Final[frozenset[str]] = frozenset(
    {"disabled", "unavailable", "tombstone"}
)


class PublicCallTransport(StrEnum):
    """Public-call transports that must carry InvocationEnvelope (FR-WF-17)."""

    IN_PROCESS = "in-process"
    CLI = "cli"
    WIRE = "wire"
    NESTED = "nested"


PUBLIC_CALL_TRANSPORTS: Final[frozenset[str]] = frozenset(
    member.value for member in PublicCallTransport
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unavailable(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason, "code": "UNAVAILABLE"}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.AFTER_CONDITION,
        context=context,
        after_condition_descriptor="the contribution is enabled on the live roster",
    )


def _as_str_tokens(field: str, value: object) -> Result[list[str]]:
    collected: list[object]
    if isinstance(value, list):
        collected = cast(list[object], value)
    elif isinstance(value, tuple):
        collected = list(cast(tuple[object, ...], value))
    elif isinstance(value, set):
        collected = list(cast(set[object], value))
    elif isinstance(value, frozenset):
        collected = list(cast(frozenset[object], value))
    else:
        return _invalid(field, f"{field} is a sequence of permission tokens", given=repr(value))
    tokens: list[str] = []
    for raw in collected:
        if not isinstance(raw, str) or raw.strip() == "":
            return _invalid(field, f"{field} is a sequence of permission tokens", given=repr(raw))
        tokens.append(raw)
    return Ok(tokens)


def _as_mapping(field: str, value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return _invalid(field, f"{field} must be an object")
    mapping = cast("Mapping[object, object]", value)
    out: dict[str, object] = {}
    for key, item in mapping.items():
        if not isinstance(key, str):
            return _invalid(field, f"{field} keys must be strings")
        if item is None:
            return _invalid(
                field,
                "null is prohibited; omit absent optional keys (fp1)",
                key=key,
            )
        out[key] = item
    return Ok(out)


def _require_str(field: str, value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(field, f"{field} must be a non-empty string", given=repr(value))
    token = value.strip()
    if token.casefold() in AMBIGUOUS_RESOLUTION_TOKENS:
        return AmbiguousResolution.of(field=field, given=token)
    return Ok(token)


def _require_int(field: str, value: object, *, minimum: int) -> Result[int]:
    if isinstance(value, str) and value.strip().casefold() in AMBIGUOUS_RESOLUTION_TOKENS:
        return AmbiguousResolution.of(field=field, given=value)
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(field, f"{field} must be an integer", given=repr(value))
    if value < minimum:
        return _invalid(field, f"{field} must be >= {minimum}", given=value)
    return Ok(value)


def _parse_session_ref(field: str, value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(field, f"{field} is an omitted key or a non-empty psess: ref")
    token = value.strip()
    if token.casefold().startswith(_FORBIDDEN_SESSION_PREFIX) and not token.casefold().startswith(
        _SESSION_PREFIX
    ):
        return _invalid(
            field,
            f"{field} is a product-session psess: ref, never a QMA sess: id",
            given=token,
        )
    if not token.startswith(_SESSION_PREFIX) or len(token) <= len(_SESSION_PREFIX):
        return _invalid(field, f"{field} must be a psess: product-session ref", given=token)
    return Ok(token)


def _parse_effect(value: object) -> Result[EffectClass]:
    try:
        return Ok(parse_closed(EffectClass, value))
    except VocabularyError as exc:
        return _invalid("effect_class", str(exc), given=repr(value))


def _parse_reconcile(value: object) -> Result[ReconcilePolicy]:
    try:
        return Ok(parse_closed(ReconcilePolicy, value))
    except VocabularyError as exc:
        return _invalid("reconcile_policy", str(exc), given=repr(value))


def _parse_input_hash(value: object) -> Result[str]:
    token = _require_str("input_hash", value)
    if is_refusal(token):
        return token
    parsed = Fingerprint.try_create(token.value)
    if is_refusal(parsed):
        return _invalid(
            "input_hash",
            "input_hash is fp1:sha256:<hex> over canonical JSON of the "
            "input_schema-validated payload (FR-WF-21)",
            given=token.value,
        )
    return Ok(parsed.value.value)


@dataclass(frozen=True, slots=True)
class ContributionBinding:
    """Contribution tuple bound on the envelope: never fp1 (DEC-0415)."""

    qualified_id: str
    package_version: str

    def as_tuple(self) -> tuple[str, str]:
        return (self.qualified_id, self.package_version)

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "package_version": self.package_version,
                "qualified_id": self.qualified_id,
            }
        )


def _parse_contribution(value: object) -> Result[ContributionBinding]:
    mapped = _as_mapping("contribution", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    extra = sorted(set(body) - _CONTRIBUTION_KEYS)
    if extra:
        return _invalid(
            "contribution",
            "contribution is {qualified_id, package_version}",
            extra=extra,
        )
    qualified = _require_str("contribution.qualified_id", body.get("qualified_id"))
    if is_refusal(qualified):
        return qualified
    version = _require_str("contribution.package_version", body.get("package_version"))
    if is_refusal(version):
        return version
    return Ok(ContributionBinding(qualified_id=qualified.value, package_version=version.value))


@dataclass(frozen=True, slots=True)
class GrantRecord:
    """Authoritative grant snapshot used for hop compare (Story 54.2).

    Minting, immutability, and GrantRevocation are Story 54.4. This record is
    what the host resolves from the grant store and compares to bound fields.
    """

    grant_id: str
    contribution: ContributionBinding
    instance_id: str
    config_revision: int
    op_id: str
    op_version: int
    effect_class: EffectClass

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "config_revision": self.config_revision,
                "contribution": dict(self.contribution.to_payload()),
                "effect_class": self.effect_class.value,
                "grant_id": self.grant_id,
                "instance_id": self.instance_id,
                "op_id": self.op_id,
                "op_version": self.op_version,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        grant_id: object,
        contribution: object,
        instance_id: object,
        config_revision: object,
        op_id: object,
        op_version: object,
        effect_class: object,
    ) -> Result[GrantRecord]:
        gid = _require_str("grant_id", grant_id)
        if is_refusal(gid):
            return gid
        bound = _parse_contribution(contribution)
        if is_refusal(bound):
            return bound
        instance = _require_str("instance_id", instance_id)
        if is_refusal(instance):
            return instance
        revision = _require_int("config_revision", config_revision, minimum=0)
        if is_refusal(revision):
            return revision
        op = _require_str("op_id", op_id)
        if is_refusal(op):
            return op
        version = _require_int("op_version", op_version, minimum=1)
        if is_refusal(version):
            return version
        effect = _parse_effect(effect_class)
        if is_refusal(effect):
            return effect
        return Ok(
            cls(
                grant_id=gid.value,
                contribution=bound.value,
                instance_id=instance.value,
                config_revision=revision.value,
                op_id=op.value,
                op_version=version.value,
                effect_class=effect.value,
            )
        )


@dataclass(frozen=True, slots=True)
class ContributionRecord:
    """Live contribution row from the authoritative contribution store."""

    qualified_id: str
    package_version: str
    availability: str

    def as_tuple(self) -> tuple[str, str]:
        return (self.qualified_id, self.package_version)


@dataclass(frozen=True, slots=True)
class InstanceRecord:
    """Exact instance + config revision; never a latest alias."""

    instance_id: str
    config_revision: int


@dataclass(frozen=True, slots=True)
class InvocationEnvelope:
    """CONTRACTS §1b InvocationEnvelope (cheap-veto A3). Not authority."""

    logical_invocation_id: str
    attempt_id: int
    op_id: str
    op_version: int
    contribution: ContributionBinding
    instance_id: str
    config_revision: int
    grant_id: str
    effect_class: EffectClass
    idempotency_key: str
    reconcile_policy: ReconcilePolicy
    input_hash: str
    call_depth: int
    caller_session_ref: str | None = None
    callee_session_ref: str | None = None
    parent_logical_invocation_id: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "attempt_id": self.attempt_id,
            "call_depth": self.call_depth,
            "config_revision": self.config_revision,
            "contribution": dict(self.contribution.to_payload()),
            "effect_class": self.effect_class.value,
            "grant_id": self.grant_id,
            "idempotency_key": self.idempotency_key,
            "input_hash": self.input_hash,
            "instance_id": self.instance_id,
            "logical_invocation_id": self.logical_invocation_id,
            "op_id": self.op_id,
            "op_version": self.op_version,
            "reconcile_policy": self.reconcile_policy.value,
        }
        if self.caller_session_ref is not None:
            payload["caller_session_ref"] = self.caller_session_ref
        if self.callee_session_ref is not None:
            payload["callee_session_ref"] = self.callee_session_ref
        if self.parent_logical_invocation_id is not None:
            payload["parent_logical_invocation_id"] = self.parent_logical_invocation_id
        return MappingProxyType(payload)

    @classmethod
    def try_create(cls, **fields: object) -> Result[InvocationEnvelope]:
        return parse_invocation_envelope(fields)


def parse_invocation_envelope(value: object) -> Result[InvocationEnvelope]:
    """Parse CONTRACTS §1b. Null optional fields are omitted keys, never null."""
    if isinstance(value, InvocationEnvelope):
        return parse_invocation_envelope(dict(value.to_payload()))
    mapped = _as_mapping("invocation_envelope", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    extra = sorted(set(body) - set(INVOCATION_ENVELOPE_FIELDS))
    if extra:
        if any(key.casefold() in {"signature", "signature_algorithm", "crypto"} for key in extra):
            return EnvelopeMismatch.of(
                field="signature_algorithm",
                extra=extra,
                gap=ENVELOPE_CRYPTO_GAP,
                algorithm_selected=False,
                reason="mismatch",
            )
        return _invalid("invocation_envelope", "unknown InvocationEnvelope fields", extra=extra)
    missing = [field for field in INVOCATION_ENVELOPE_REQUIRED_FIELDS if field not in body]
    if missing:
        return _invalid(
            "invocation_envelope",
            "CONTRACTS §1b field catalogue is incomplete (cheap-veto A3; FR-WF-17)",
            missing=missing,
        )

    logical = _require_str("logical_invocation_id", body["logical_invocation_id"])
    if is_refusal(logical):
        return logical
    attempt = _require_int("attempt_id", body["attempt_id"], minimum=1)
    if is_refusal(attempt):
        return attempt
    op_id = _require_str("op_id", body["op_id"])
    if is_refusal(op_id):
        return op_id
    op_version = _require_int("op_version", body["op_version"], minimum=1)
    if is_refusal(op_version):
        return op_version
    contribution = _parse_contribution(body["contribution"])
    if is_refusal(contribution):
        return contribution
    instance_id = _require_str("instance_id", body["instance_id"])
    if is_refusal(instance_id):
        return instance_id
    config_revision = _require_int("config_revision", body["config_revision"], minimum=0)
    if is_refusal(config_revision):
        return config_revision
    caller = _parse_session_ref("caller_session_ref", body.get("caller_session_ref"))
    if is_refusal(caller):
        return caller
    callee = _parse_session_ref("callee_session_ref", body.get("callee_session_ref"))
    if is_refusal(callee):
        return callee
    grant_id = _require_str("grant_id", body["grant_id"])
    if is_refusal(grant_id):
        return grant_id
    effect = _parse_effect(body["effect_class"])
    if is_refusal(effect):
        return effect
    idempotency = _require_str("idempotency_key", body["idempotency_key"])
    if is_refusal(idempotency):
        return idempotency
    reconcile = _parse_reconcile(body["reconcile_policy"])
    if is_refusal(reconcile):
        return reconcile
    input_hash = _parse_input_hash(body["input_hash"])
    if is_refusal(input_hash):
        return input_hash
    parent = _require_optional_parent(body.get("parent_logical_invocation_id"))
    if is_refusal(parent):
        return parent
    depth = _require_int("call_depth", body["call_depth"], minimum=0)
    if is_refusal(depth):
        return depth
    if depth.value == 0 and parent.value is not None:
        return _invalid(
            "parent_logical_invocation_id",
            "top-level calls omit parent_logical_invocation_id",
        )
    if depth.value >= 1 and parent.value is None:
        return _invalid(
            "parent_logical_invocation_id",
            "nested public calls carry parent_logical_invocation_id and call_depth",
        )
    return Ok(
        InvocationEnvelope(
            logical_invocation_id=logical.value,
            attempt_id=attempt.value,
            op_id=op_id.value,
            op_version=op_version.value,
            contribution=contribution.value,
            instance_id=instance_id.value,
            config_revision=config_revision.value,
            grant_id=grant_id.value,
            effect_class=effect.value,
            idempotency_key=idempotency.value,
            reconcile_policy=reconcile.value,
            input_hash=input_hash.value,
            call_depth=depth.value,
            caller_session_ref=caller.value,
            callee_session_ref=callee.value,
            parent_logical_invocation_id=parent.value,
        )
    )


def _require_optional_parent(value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    parsed = _require_str("parent_logical_invocation_id", value)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value)


def validate_invocation_envelope(value: object) -> Result[InvocationEnvelope]:
    """Schema-validate then parse the additive CT-40 InvocationEnvelope DTO."""
    checked = validate_instance(value, INVOCATION_ENVELOPE_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_invocation_envelope(checked.value)


def validate_input_payload(
    descriptor: OperationDescriptor,
    payload: object,
) -> Result[Mapping[str, object]]:
    """Return the ``input_schema``-validated payload (required + optional keys)."""
    mapped = _as_mapping("input", payload)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    secret = assert_no_secret_on_wire_surface(body)
    if is_refusal(secret):
        return secret
    folded_keys = {key.casefold() for key in body}
    stolen = sorted(key for key in FORBIDDEN_SECRET_SURFACE_KEYS if key in folded_keys)
    if stolen:
        return EnvelopeMismatch.of(field="input", secrets=stolen, reason="secrets_never_inlined")
    required = descriptor.configuration.required_keys
    missing = [key for key in required if key not in body]
    if missing:
        return _invalid(
            "input",
            "payload failed input_schema required keys",
            missing=missing,
            input_schema=descriptor.input_schema,
        )
    allowed = (
        set(required)
        | set(descriptor.configuration.optional_keys)
        | set(descriptor.configuration.defaults)
    )
    validated = {key: body[key] for key in body if key in allowed}
    for key in required:
        validated.setdefault(key, body[key])
    return Ok(MappingProxyType(validated))


def compute_input_hash(
    payload: object,
    *,
    descriptor: OperationDescriptor,
) -> Result[str]:
    """Canonical JSON (sorted keys, no whitespace) of the validated payload."""
    validated = validate_input_payload(descriptor, payload)
    if is_refusal(validated):
        return validated
    fp = fingerprint(dict(validated.value))
    if is_refusal(fp):
        return fp
    return Ok(fp.value.value)


@dataclass(frozen=True, slots=True)
class AuthoritativeStores:
    """In-memory authoritative stores the host compares on every hop (RC-03)."""

    contributions: Mapping[tuple[str, str], ContributionRecord]
    descriptors: Mapping[tuple[str, int], OperationDescriptor]
    grants: Mapping[str, GrantRecord]
    instances: Mapping[tuple[str, int], InstanceRecord]

    def __post_init__(self) -> None:
        object.__setattr__(self, "contributions", MappingProxyType(dict(self.contributions)))
        object.__setattr__(self, "descriptors", MappingProxyType(dict(self.descriptors)))
        object.__setattr__(self, "grants", MappingProxyType(dict(self.grants)))
        object.__setattr__(self, "instances", MappingProxyType(dict(self.instances)))


@dataclass(frozen=True, slots=True)
class BoundInvocation:
    """Host-compared invocation. ``is_authority`` is always false (RC-03)."""

    envelope: InvocationEnvelope
    contribution: ContributionRecord
    descriptor: OperationDescriptor
    grant: GrantRecord
    instance: InstanceRecord
    transport: PublicCallTransport
    validated_payload: Mapping[str, object]
    is_authority: bool = False

    def __post_init__(self) -> None:
        frozen = MappingProxyType(dict(self.validated_payload))
        object.__setattr__(self, "validated_payload", frozen)
        object.__setattr__(self, "is_authority", False)


def _resolve_contribution(
    stores: AuthoritativeStores,
    bound: ContributionBinding,
) -> Result[ContributionRecord]:
    exact = stores.contributions.get(bound.as_tuple())
    if exact is not None:
        if exact.availability in _UNAVAILABLE_AVAILABILITY:
            return _unavailable(
                "contribution",
                "contribution is not enabled on the live roster",
                availability=exact.availability,
            )
        return Ok(exact)
    other_versions = [key[1] for key in stores.contributions if key[0] == bound.qualified_id]
    if other_versions:
        return StaleObservation.of(
            field="contribution.package_version",
            bound=bound.package_version,
            live_versions=other_versions,
            substituted=False,
        )
    return _unavailable(
        "contribution",
        "contribution is not on the authoritative store",
        qualified_id=bound.qualified_id,
        package_version=bound.package_version,
    )


def _resolve_descriptor(
    stores: AuthoritativeStores,
    *,
    op_id: str,
    op_version: int,
) -> Result[OperationDescriptor]:
    exact = stores.descriptors.get((op_id, op_version))
    if exact is not None:
        return Ok(exact)
    other = [key[1] for key in stores.descriptors if key[0] == op_id]
    if other:
        return StaleObservation.of(
            field="op_version",
            bound=op_version,
            live_versions=other,
            substituted=False,
        )
    return StaleObservation.of(field="op_id", bound=op_id, live=False)


def _resolve_instance(
    stores: AuthoritativeStores,
    *,
    instance_id: str,
    config_revision: int,
) -> Result[InstanceRecord]:
    exact = stores.instances.get((instance_id, config_revision))
    if exact is not None:
        return Ok(exact)
    siblings = [
        record.config_revision
        for record in stores.instances.values()
        if record.instance_id == instance_id
    ]
    if siblings:
        return StaleObservation.of(
            field="config_revision",
            bound=config_revision,
            live_revisions=siblings,
            substituted=False,
            never_latest=True,
        )
    return StaleObservation.of(field="instance_id", bound=instance_id, live=False)


def _compare_grant(envelope: InvocationEnvelope, grant: GrantRecord) -> Result[GrantRecord]:
    if grant.grant_id != envelope.grant_id:
        return GrantMismatch.of(field="grant_id", grant_id=envelope.grant_id)
    if grant.op_id != envelope.op_id:
        return GrantMismatch.of(
            field="op_id",
            grant_id=envelope.grant_id,
            bound=envelope.op_id,
            granted=grant.op_id,
        )
    if grant.op_version != envelope.op_version:
        return GrantMismatch.of(
            field="op_version",
            grant_id=envelope.grant_id,
            bound=envelope.op_version,
            granted=grant.op_version,
        )
    if grant.instance_id != envelope.instance_id:
        return GrantMismatch.of(
            field="instance_id",
            grant_id=envelope.grant_id,
            bound=envelope.instance_id,
            granted=grant.instance_id,
        )
    if grant.config_revision != envelope.config_revision:
        return GrantMismatch.of(
            field="config_revision",
            grant_id=envelope.grant_id,
            bound=envelope.config_revision,
            granted=grant.config_revision,
        )
    if grant.contribution.as_tuple() != envelope.contribution.as_tuple():
        return GrantMismatch.of(
            field="contribution",
            grant_id=envelope.grant_id,
            bound=list(envelope.contribution.as_tuple()),
            granted=list(grant.contribution.as_tuple()),
        )
    if grant.effect_class is not envelope.effect_class:
        return GrantMismatch.of(
            field="effect_class",
            grant_id=envelope.grant_id,
            bound=envelope.effect_class.value,
            granted=grant.effect_class.value,
        )
    return Ok(grant)


def bind_invocation_envelope(
    envelope: InvocationEnvelope,
    stores: AuthoritativeStores,
    *,
    payload: object,
) -> Result[
    tuple[
        ContributionRecord,
        OperationDescriptor,
        GrantRecord,
        InstanceRecord,
        Mapping[str, object],
    ]
]:
    """Resolve stores and compare every bound field. Envelope is not authority."""
    contribution = _resolve_contribution(stores, envelope.contribution)
    if is_refusal(contribution):
        return contribution
    descriptor = _resolve_descriptor(stores, op_id=envelope.op_id, op_version=envelope.op_version)
    if is_refusal(descriptor):
        return descriptor
    if descriptor.value.op_id != envelope.op_id:
        return EnvelopeMismatch.of(
            field="op_id",
            bound=envelope.op_id,
            live=descriptor.value.op_id,
        )
    if descriptor.value.version != envelope.op_version:
        return StaleObservation.of(
            field="op_version",
            bound=envelope.op_version,
            live=descriptor.value.version,
        )
    if descriptor.value.effect_class is not envelope.effect_class:
        return EnvelopeMismatch.of(
            field="effect_class",
            bound=envelope.effect_class.value,
            live=descriptor.value.effect_class.value,
            reason="mismatch",
        )
    grant = stores.grants.get(envelope.grant_id)
    if grant is None:
        return GrantMismatch.of(field="grant_id", grant_id=envelope.grant_id, live=False)
    compared = _compare_grant(envelope, grant)
    if is_refusal(compared):
        return compared
    instance = _resolve_instance(
        stores,
        instance_id=envelope.instance_id,
        config_revision=envelope.config_revision,
    )
    if is_refusal(instance):
        return instance
    validated = validate_input_payload(descriptor.value, payload)
    if is_refusal(validated):
        return validated
    expected_hash = compute_input_hash(validated.value, descriptor=descriptor.value)
    if is_refusal(expected_hash):
        return expected_hash
    if expected_hash.value != envelope.input_hash:
        return EnvelopeMismatch.of(
            field="input_hash",
            bound=envelope.input_hash,
            live=expected_hash.value,
            gap=ENVELOPE_CRYPTO_GAP,
            algorithm_selected=ENVELOPE_CRYPTO_ALGORITHM_SELECTED,
        )
    return Ok(
        (
            contribution.value,
            descriptor.value,
            compared.value,
            instance.value,
            validated.value,
        )
    )


def _parse_transport(value: object) -> Result[PublicCallTransport]:
    if isinstance(value, PublicCallTransport):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(PublicCallTransport(value))
        except ValueError:
            return _invalid(
                "transport",
                "transport is in-process | cli | wire | nested",
                given=value,
            )
    return _invalid("transport", "transport is in-process | cli | wire | nested", given=repr(value))


def dispatch_public_call(
    *,
    transport: object,
    envelope: object,
    payload: object,
    stores: AuthoritativeStores,
    execute: Callable[[BoundInvocation], None] | None = None,
    parent_permissions: object | None = None,
) -> Result[BoundInvocation]:
    """Dispatch a public call. Missing envelope is a typed refusal; no execute."""
    parsed_transport = _parse_transport(transport)
    if is_refusal(parsed_transport):
        return parsed_transport
    door = parsed_transport.value
    if envelope is None:
        return InvocationEnvelopeRequired.of(transport=door.value)
    parsed = parse_invocation_envelope(envelope)
    if is_refusal(parsed):
        return parsed
    env = parsed.value
    if door is PublicCallTransport.NESTED:
        if env.parent_logical_invocation_id is None or env.call_depth < 1:
            return _invalid(
                "call_depth",
                "nested public calls carry parent_logical_invocation_id and call_depth",
            )
        child_id = assert_child_logical_invocation_id(
            logical_invocation_id=env.logical_invocation_id,
            parent_logical_invocation_id=env.parent_logical_invocation_id,
            call_depth=env.call_depth,
            child_op_id=env.op_id,
            child_canonical_input_hash=env.input_hash,
        )
        if is_refusal(child_id):
            return child_id
    elif env.call_depth != 0:
        return _invalid(
            "call_depth",
            "non-nested public calls have call_depth 0",
            transport=door.value,
        )
    bound_parts = bind_invocation_envelope(env, stores, payload=payload)
    if is_refusal(bound_parts):
        return bound_parts
    contribution, descriptor, grant, instance, validated = bound_parts.value
    if door is PublicCallTransport.NESTED:
        if parent_permissions is None:
            parent_tokens: tuple[str, ...] | list[str] = descriptor.permission_requests
        else:
            parsed_parent = _as_str_tokens("parent_permissions", parent_permissions)
            if is_refusal(parsed_parent):
                return parsed_parent
            parent_tokens = parsed_parent.value
        permitted = nested_invocation_permissions(
            parent_tokens,
            descriptor.permission_requests,
        )
        if is_refusal(permitted):
            return permitted
    bound = BoundInvocation(
        envelope=env,
        contribution=contribution,
        descriptor=descriptor,
        grant=grant,
        instance=instance,
        transport=door,
        validated_payload=validated,
        is_authority=False,
    )
    if execute is not None:
        execute(bound)
    return Ok(bound)


def public_call_in_process(
    envelope: object,
    payload: object,
    stores: AuthoritativeStores,
    *,
    execute: Callable[[BoundInvocation], None] | None = None,
) -> Result[BoundInvocation]:
    """In-process public call; envelope is required."""
    return dispatch_public_call(
        transport=PublicCallTransport.IN_PROCESS,
        envelope=envelope,
        payload=payload,
        stores=stores,
        execute=execute,
    )


def public_call_from_cli(
    envelope: object,
    payload: object,
    stores: AuthoritativeStores,
    *,
    execute: Callable[[BoundInvocation], None] | None = None,
) -> Result[BoundInvocation]:
    """CLI public call; envelope is required. Transport never bypasses it."""
    return dispatch_public_call(
        transport=PublicCallTransport.CLI,
        envelope=envelope,
        payload=payload,
        stores=stores,
        execute=execute,
    )


def _payload_from_wire_message(message: object) -> Result[dict[str, object]]:
    if isinstance(message, WireEnvelope):
        return _as_mapping("payload", dict(message.payload))
    mapped = _as_mapping("wire", message)
    if is_refusal(mapped):
        return InvocationEnvelopeRequired.of(transport=PublicCallTransport.WIRE.value)
    body = mapped.value
    inner = body.get("payload")
    if "invocation_envelope" not in body and inner is not None:
        nested = _as_mapping("payload", inner)
        if is_refusal(nested):
            return nested
        return Ok(nested.value)
    return Ok(body)


def public_call_from_wire(
    message: object,
    stores: AuthoritativeStores,
    *,
    execute: Callable[[BoundInvocation], None] | None = None,
) -> Result[BoundInvocation]:
    """Wire public call. ``invocation_envelope`` must ride in the payload."""
    extracted = _payload_from_wire_message(message)
    if is_refusal(extracted):
        return extracted
    payload_map = extracted.value
    if "invocation_envelope" not in payload_map:
        return InvocationEnvelopeRequired.of(transport=PublicCallTransport.WIRE.value)
    input_payload: object
    if "input" in payload_map:
        input_payload = payload_map["input"]
    elif "args" in payload_map:
        input_payload = payload_map["args"]
    else:
        input_payload = {
            key: value for key, value in payload_map.items() if key != "invocation_envelope"
        }
    return dispatch_public_call(
        transport=PublicCallTransport.WIRE,
        envelope=payload_map["invocation_envelope"],
        payload=input_payload,
        stores=stores,
        execute=execute,
    )


def public_call_nested(
    envelope: object,
    payload: object,
    stores: AuthoritativeStores,
    *,
    execute: Callable[[BoundInvocation], None] | None = None,
    parent_permissions: object | None = None,
) -> Result[BoundInvocation]:
    """Nested public call. Child id derives from parent; permissions do not union."""
    return dispatch_public_call(
        transport=PublicCallTransport.NESTED,
        envelope=envelope,
        payload=payload,
        stores=stores,
        execute=execute,
        parent_permissions=parent_permissions,
    )
