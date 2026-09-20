"""Immutable GrantRecord and append-only GrantRevocation (Story 54.4).

GrantRecord fields follow CONTRACTS §3b. ``revoked_at`` is not a GrantRecord
field. Revocation is a separate append-only record. Manifests request; the
host grants. ``product_session.granted_ops`` stores grant_ids, not bare
op-id strings — this module does not mint product_session rows (Epic 55).
No new CT (do not mint CT-52). Additive CT-40.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qma.core.operations.descriptor import OperationDescriptor
from qma.core.refusals.variants import (
    GrantInactive,
    GrantWidenRefused,
    ManifestIsNotGrant,
)
from qma.core.vocabulary.enums import GrantEvaluationMoment
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qma.wire.invocation_envelope import (
    GRANT_RECORD_FIELDS,
    GRANT_RECORD_FORBIDDEN_FIELDS,
    AuthoritativeStores,
    BoundInvocation,
    ContributionRecord,
    GrantRecord,
    InstanceRecord,
    ParameterCeiling,
    PublicCallTransport,
    dispatch_public_call,
    parse_invocation_envelope,
    parse_utc_iso_z,
)
from qma.wire.schemas import validate_instance
from qmf.core.chrono import Instant
from qmf.core.fingerprint import canonical_bytes
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "GRANTED_OPS_STORE_BARE_OP_IDS",
    "GRANTED_OPS_STORE_GRANT_IDS",
    "GRANT_ID_PREFIX",
    "GRANT_RECORD_CONTRACT",
    "GRANT_RECORD_DTO_OWNER",
    "GRANT_RECORD_FIELDS",
    "GRANT_RECORD_FORBIDDEN_FIELDS",
    "GRANT_RECORD_NEW_CT_MINTED",
    "GRANT_RECORD_REFUSED_CT",
    "GRANT_RECORD_SCHEMA",
    "GRANT_RECORD_SCHEMA_FILE",
    "GRANT_RECORD_SCHEMA_NAME",
    "GRANT_REVOCATION_FIELDS",
    "GRANT_REVOCATION_SCHEMA",
    "GRANT_REVOCATION_SCHEMA_FILE",
    "GRANT_REVOCATION_SCHEMA_NAME",
    "HOST_GRANTS",
    "MANIFESTS_GRANT",
    "PRODUCT_SESSION_ROWS_MINTED",
    "AcceptedGrantWork",
    "GrantRecord",
    "GrantRevocation",
    "HostGrantLedger",
    "ParameterCeiling",
    "ProductSessionGrantedOps",
    "RegrantResult",
    "parse_grant_record",
    "parse_grant_revocation",
    "parse_granted_ops",
    "refuse_in_place_upgrade",
    "refuse_manifest_grant",
    "refuse_product_session_rows",
    "validate_grant_record",
    "validate_grant_revocation",
]


GRANT_RECORD_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
GRANT_RECORD_CONTRACT: Final[str] = "CT-40"
GRANT_RECORD_NEW_CT_MINTED: Final[bool] = False
GRANT_RECORD_REFUSED_CT: Final[str] = "CT-52"
GRANT_RECORD_SCHEMA: Final[str] = "qma.wire.grant_record.v1"
GRANT_RECORD_SCHEMA_NAME: Final[str] = "grant_record"
GRANT_RECORD_SCHEMA_FILE: Final[str] = "grant_record.v1.schema.json"
GRANT_REVOCATION_SCHEMA: Final[str] = "qma.wire.grant_revocation.v1"
GRANT_REVOCATION_SCHEMA_NAME: Final[str] = "grant_revocation"
GRANT_REVOCATION_SCHEMA_FILE: Final[str] = "grant_revocation.v1.schema.json"
GRANT_ID_PREFIX: Final[str] = "grant:"
GRANT_REVOCATION_FIELDS: Final[tuple[str, ...]] = (
    "grant_id",
    "revoked_at",
    "principal",
    "reason",
)
MANIFESTS_GRANT: Final[bool] = False
HOST_GRANTS: Final[bool] = True
PRODUCT_SESSION_ROWS_MINTED: Final[bool] = False
GRANTED_OPS_STORE_GRANT_IDS: Final[bool] = True
GRANTED_OPS_STORE_BARE_OP_IDS: Final[bool] = False
_HOST_ISSUER: Final[str] = "host"
_NEW_DISPATCH_MOMENTS: Final[frozenset[GrantEvaluationMoment]] = frozenset(
    {
        GrantEvaluationMoment.ACCEPT,
        GrantEvaluationMoment.DISPATCH,
    }
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


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
    return Ok(value.strip())


def refuse_manifest_grant(*, issuer: object = "manifest", **extra: object) -> ManifestIsNotGrant:
    """Manifests request; they never mint GrantRecord (FR-WF-25)."""
    return ManifestIsNotGrant.of(issuer=issuer, **extra)


def refuse_product_session_rows(**extra: object) -> TypedRefusal:
    """Story 54.4 does not mint product_session rows (Epic 55; FR-WF-30)."""
    context: dict[str, object] = {
        "field": "product_session",
        "reason": "product_session rows are Epic 55; this story does not mint them",
        "product_session_rows_minted": False,
        "granted_ops_store_grant_ids": True,
        "granted_ops_store_bare_op_ids": False,
        "epic": 55,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def refuse_in_place_upgrade(*, grant_id: str, **extra: object) -> GrantWidenRefused:
    """Upgrade cannot widen or retarget without an explicit re-grant."""
    return GrantWidenRefused.of(grant_id=grant_id, **extra)


def parse_grant_record(value: object) -> Result[GrantRecord]:
    """Parse CONTRACTS §3b GrantRecord. ``revoked_at`` is refused."""
    if isinstance(value, GrantRecord):
        return parse_grant_record(dict(value.to_payload()))
    mapped = _as_mapping("grant_record", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    if any(key in GRANT_RECORD_FORBIDDEN_FIELDS for key in body):
        return _invalid(
            "revoked_at",
            "revoked_at is not a GrantRecord field; revocation is append-only "
            "GrantRevocation (FR-WF-23; RC-05)",
            extra=sorted(key for key in body if key in GRANT_RECORD_FORBIDDEN_FIELDS),
        )
    extra = sorted(set(body) - set(GRANT_RECORD_FIELDS))
    if extra:
        return _invalid("grant_record", "unknown GrantRecord fields", extra=extra)
    required = [name for name in GRANT_RECORD_FIELDS if name != "account_scope"]
    missing = [name for name in required if name not in body]
    if missing:
        return _invalid(
            "grant_record",
            "CONTRACTS §3b field catalogue is incomplete",
            missing=missing,
        )
    return GrantRecord.try_create(
        grant_id=body["grant_id"],
        principal=body["principal"],
        audience=body["audience"],
        contribution=body["contribution"],
        instance_id=body["instance_id"],
        config_revision=body["config_revision"],
        op_id=body["op_id"],
        op_version=body["op_version"],
        effect_class=body["effect_class"],
        parameter_ceiling=body["parameter_ceiling"],
        expires_at=body["expires_at"],
        account_scope=body.get("account_scope"),
    )


def validate_grant_record(value: object) -> Result[GrantRecord]:
    """Schema-validate then parse the additive CT-40 GrantRecord DTO."""
    checked = validate_instance(value, GRANT_RECORD_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_grant_record(checked.value)


@dataclass(frozen=True, slots=True)
class GrantRevocation:
    """Append-only revocation row. Does not mutate GrantRecord bytes (FR-WF-24)."""

    grant_id: str
    revoked_at: Instant
    revoked_at_iso: str
    principal: str
    reason: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "grant_id": self.grant_id,
                "principal": self.principal,
                "reason": self.reason,
                "revoked_at": self.revoked_at_iso,
            }
        )

    def canonical_bytes(self) -> Result[bytes]:
        return canonical_bytes(dict(self.to_payload()))

    @classmethod
    def try_create(
        cls,
        *,
        grant_id: object,
        revoked_at: object,
        principal: object,
        reason: object,
    ) -> Result[GrantRevocation]:
        gid = _require_str("grant_id", grant_id)
        if is_refusal(gid):
            return gid
        if not gid.value.startswith(GRANT_ID_PREFIX) or gid.value == GRANT_ID_PREFIX:
            return _invalid(
                "grant_id",
                "grant_id is a grant: token, never a bare op-id string",
                given=gid.value,
            )
        when = parse_utc_iso_z("revoked_at", revoked_at)
        if is_refusal(when):
            return when
        who = _require_str("principal", principal)
        if is_refusal(who):
            return who
        why = _require_str("reason", reason)
        if is_refusal(why):
            return why
        instant, iso_text = when.value
        return Ok(
            cls(
                grant_id=gid.value,
                revoked_at=instant,
                revoked_at_iso=iso_text,
                principal=who.value,
                reason=why.value,
            )
        )


def parse_grant_revocation(value: object) -> Result[GrantRevocation]:
    """Parse append-only GrantRevocation {grant_id, revoked_at, principal, reason}."""
    if isinstance(value, GrantRevocation):
        return parse_grant_revocation(dict(value.to_payload()))
    mapped = _as_mapping("grant_revocation", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    extra = sorted(set(body) - set(GRANT_REVOCATION_FIELDS))
    if extra:
        return _invalid("grant_revocation", "unknown GrantRevocation fields", extra=extra)
    missing = [name for name in GRANT_REVOCATION_FIELDS if name not in body]
    if missing:
        return _invalid(
            "grant_revocation",
            "GrantRevocation is {grant_id, revoked_at, principal, reason}",
            missing=missing,
        )
    return GrantRevocation.try_create(
        grant_id=body["grant_id"],
        revoked_at=body["revoked_at"],
        principal=body["principal"],
        reason=body["reason"],
    )


def validate_grant_revocation(value: object) -> Result[GrantRevocation]:
    """Schema-validate then parse the additive CT-40 GrantRevocation DTO."""
    checked = validate_instance(value, GRANT_REVOCATION_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_grant_revocation(checked.value)


def parse_granted_ops(value: object) -> Result[tuple[str, ...]]:
    """``product_session.granted_ops`` stores grant_ids, never bare op-id strings."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "granted_ops",
            "granted_ops is an array of grant_id tokens, never bare op-id strings",
            granted_ops_store_grant_ids=True,
            granted_ops_store_bare_op_ids=False,
        )
    collected = cast("Sequence[object]", value)
    tokens: list[str] = []
    for raw in collected:
        if not isinstance(raw, str) or raw.strip() == "":
            return _invalid(
                "granted_ops",
                "granted_ops is an array of grant_id tokens, never bare op-id strings",
                given=repr(raw),
            )
        token = raw.strip()
        if not token.startswith(GRANT_ID_PREFIX) or token == GRANT_ID_PREFIX:
            return _invalid(
                "granted_ops",
                "granted_ops stores grant_ids, not bare op-id strings (FR-WF-30)",
                given=token,
                granted_ops_store_grant_ids=True,
                granted_ops_store_bare_op_ids=False,
            )
        tokens.append(token)
    return Ok(tuple(tokens))


@dataclass(frozen=True, slots=True)
class ProductSessionGrantedOps:
    """Type-level granted_ops: grant_ids only. Not a product_session row."""

    grant_ids: tuple[str, ...]
    stores_grant_ids: bool = True
    stores_bare_op_ids: bool = False
    product_session_rows_minted: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "granted_ops": list(self.grant_ids),
                "product_session_rows_minted": False,
                "stores_bare_op_ids": False,
                "stores_grant_ids": True,
            }
        )

    @classmethod
    def try_create(cls, granted_ops: object) -> Result[ProductSessionGrantedOps]:
        parsed = parse_granted_ops(granted_ops)
        if is_refusal(parsed):
            return parsed
        return Ok(cls(grant_ids=parsed.value))


@dataclass(frozen=True, slots=True)
class AcceptedGrantWork:
    """Invocation accepted under a grant; later revoke does not unwind it."""

    grant_id: str
    logical_invocation_id: str
    moment: GrantEvaluationMoment


@dataclass(frozen=True, slots=True)
class RegrantResult:
    """Explicit re-grant: new GrantRecord plus bumped context_revision."""

    grant: GrantRecord
    previous_grant_id: str
    previous_bytes: bytes
    context_revision: int

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "context_revision": self.context_revision,
                "grant": dict(self.grant.to_payload()),
                "previous_grant_id": self.previous_grant_id,
            }
        )


def _parse_moment(value: object) -> Result[GrantEvaluationMoment]:
    try:
        return Ok(parse_closed(GrantEvaluationMoment, value))
    except VocabularyError as exc:
        return _invalid("moment", str(exc), given=repr(value))


def _serial_from_grant_id(grant_id: str) -> int | None:
    rest = grant_id[len(GRANT_ID_PREFIX) :] if grant_id.startswith(GRANT_ID_PREFIX) else ""
    if rest.isdigit():
        return int(rest)
    return None


def _inactive_reason(*, revoked: bool, expired: bool) -> str:
    if revoked and expired:
        return "revoked"
    if revoked:
        return "revoked"
    return "expired"


@dataclass
class HostGrantLedger:
    """In-memory host grant authority. Manifests request; the host grants.

    GrantRecord rows are immutable. Revocations append. Persistence beside
    product_session is COMP-QMA-DAEMON (Story 55.2) — this ledger does not
    mint a new sqlite class.
    """

    _grants: dict[str, GrantRecord] = field(default_factory=dict[str, GrantRecord])
    _minted_bytes: dict[str, bytes] = field(default_factory=dict[str, bytes])
    _revocations: list[GrantRevocation] = field(default_factory=list[GrantRevocation])
    _accepted: dict[str, str] = field(default_factory=dict[str, str])
    _context_revision: int = 0
    _next_serial: int = 1

    @property
    def context_revision(self) -> int:
        return self._context_revision

    @property
    def grants(self) -> Mapping[str, GrantRecord]:
        return MappingProxyType(dict(self._grants))

    @property
    def revocations(self) -> tuple[GrantRevocation, ...]:
        return tuple(self._revocations)

    def minted_bytes(self, grant_id: str) -> bytes | None:
        return self._minted_bytes.get(grant_id)

    def granted_ops(self) -> Result[ProductSessionGrantedOps]:
        """grant_ids for product_session.granted_ops (Story 55.2)."""
        return ProductSessionGrantedOps.try_create(tuple(self._grants))

    def import_grant(self, record: GrantRecord) -> Result[GrantRecord]:
        """Hydrate an already-minted GrantRecord. Does not re-issue."""
        if record.grant_id in self._grants:
            return _invalid(
                "grant_id",
                "grant_id is unique; minted GrantRecord bytes do not change",
                grant_id=record.grant_id,
            )
        minted = record.canonical_bytes()
        if is_refusal(minted):
            return minted
        self._grants[record.grant_id] = record
        self._minted_bytes[record.grant_id] = minted.value
        serial = _serial_from_grant_id(record.grant_id)
        if serial is not None and serial >= self._next_serial:
            self._next_serial = serial + 1
        return Ok(record)

    def import_revocation(self, revocation: GrantRevocation) -> Result[GrantRevocation]:
        """Hydrate an append-only GrantRevocation. Minted bytes stay."""
        record = self._grants.get(revocation.grant_id)
        if record is None:
            return _invalid(
                "grant_id",
                "grant_id is not a minted GrantRecord",
                grant_id=revocation.grant_id,
            )
        self._revocations.append(revocation)
        current = record.canonical_bytes()
        if is_refusal(current):
            return current
        minted = self._minted_bytes[revocation.grant_id]
        if current.value != minted:
            return _invalid(
                "grant_id",
                "minted GrantRecord bytes must not change on revocation",
                grant_id=revocation.grant_id,
            )
        return Ok(revocation)

    def import_accepted(
        self,
        *,
        grant_id: object,
        logical_invocation_id: object,
    ) -> Result[AcceptedGrantWork]:
        """Hydrate already-accepted work. Does not re-evaluate liveness."""
        gid = _require_str("grant_id", grant_id)
        if is_refusal(gid):
            return gid
        if gid.value not in self._grants:
            return _invalid(
                "grant_id",
                "grant_id is not a minted GrantRecord",
                grant_id=gid.value,
            )
        invocation = _require_str("logical_invocation_id", logical_invocation_id)
        if is_refusal(invocation):
            return invocation
        self._accepted[invocation.value] = gid.value
        return Ok(
            AcceptedGrantWork(
                grant_id=gid.value,
                logical_invocation_id=invocation.value,
                moment=GrantEvaluationMoment.ACCEPT,
            )
        )

    def authoritative_stores(
        self,
        *,
        contributions: Mapping[tuple[str, str], ContributionRecord],
        descriptors: Mapping[tuple[str, int], OperationDescriptor],
        instances: Mapping[tuple[str, int], InstanceRecord],
    ) -> AuthoritativeStores:
        return AuthoritativeStores(
            contributions=contributions,
            descriptors=descriptors,
            grants=dict(self._grants),
            instances=instances,
        )

    def mint(
        self,
        *,
        issuer: object = _HOST_ISSUER,
        grant_id: object | None = None,
        principal: object,
        audience: object,
        contribution: object,
        instance_id: object,
        config_revision: object,
        op_id: object,
        op_version: object,
        effect_class: object,
        parameter_ceiling: object,
        expires_at: object,
        account_scope: object | None = None,
    ) -> Result[GrantRecord]:
        """Host-mint an immutable GrantRecord. Manifest issuer is refused."""
        if issuer != _HOST_ISSUER:
            return refuse_manifest_grant(issuer=issuer)
        serial = grant_id
        if serial is None:
            serial = f"{GRANT_ID_PREFIX}{self._next_serial}"
            self._next_serial += 1
        built = GrantRecord.try_create(
            grant_id=serial,
            principal=principal,
            audience=audience,
            contribution=contribution,
            instance_id=instance_id,
            config_revision=config_revision,
            op_id=op_id,
            op_version=op_version,
            effect_class=effect_class,
            parameter_ceiling=parameter_ceiling,
            expires_at=expires_at,
            account_scope=account_scope,
        )
        if is_refusal(built):
            return built
        record = built.value
        if record.grant_id in self._grants:
            return _invalid(
                "grant_id",
                "grant_id is unique; minted GrantRecord bytes do not change",
                grant_id=record.grant_id,
            )
        minted = record.canonical_bytes()
        if is_refusal(minted):
            return minted
        self._grants[record.grant_id] = record
        self._minted_bytes[record.grant_id] = minted.value
        return Ok(record)

    def revoke(
        self,
        *,
        grant_id: object,
        principal: object,
        reason: object,
        revoked_at: object,
    ) -> Result[GrantRevocation]:
        """Append GrantRevocation. Minted GrantRecord bytes stay unchanged."""
        gid = _require_str("grant_id", grant_id)
        if is_refusal(gid):
            return gid
        record = self._grants.get(gid.value)
        if record is None:
            return _invalid("grant_id", "grant_id is not a minted GrantRecord", grant_id=gid.value)
        revocation = GrantRevocation.try_create(
            grant_id=gid.value,
            revoked_at=revoked_at,
            principal=principal,
            reason=reason,
        )
        if is_refusal(revocation):
            return revocation
        self._revocations.append(revocation.value)
        current = record.canonical_bytes()
        if is_refusal(current):
            return current
        minted = self._minted_bytes[gid.value]
        if current.value != minted:
            return _invalid(
                "grant_id",
                "minted GrantRecord bytes must not change on revocation",
                grant_id=gid.value,
            )
        return Ok(revocation.value)

    def _revocation_for(self, grant_id: str) -> GrantRevocation | None:
        for item in reversed(self._revocations):
            if item.grant_id == grant_id:
                return item
        return None

    def _inactive(
        self,
        grant: GrantRecord,
        *,
        now: Instant,
    ) -> tuple[bool, bool]:
        revoked = self._revocation_for(grant.grant_id) is not None
        expired = now.value_ns >= grant.expires_at.value_ns
        return revoked, expired

    def _already_accepted(self, *, grant_id: str, logical_invocation_id: str | None) -> bool:
        if logical_invocation_id is None:
            return False
        return self._accepted.get(logical_invocation_id) == grant_id

    def evaluate(
        self,
        *,
        grant_id: object,
        moment: object,
        now: object,
        logical_invocation_id: object | None = None,
        parent_logical_invocation_id: object | None = None,
    ) -> Result[GrantRecord]:
        """Evaluate at accept, dispatch, nested call, retry, or external commit."""
        parsed_moment = _parse_moment(moment)
        if is_refusal(parsed_moment):
            return parsed_moment
        when = parse_utc_iso_z("now", now)
        if is_refusal(when):
            return when
        gid = _require_str("grant_id", grant_id)
        if is_refusal(gid):
            return gid
        grant = self._grants.get(gid.value)
        if grant is None:
            return _invalid("grant_id", "grant_id is not a minted GrantRecord", grant_id=gid.value)
        invocation: str | None = None
        if logical_invocation_id is not None:
            parsed_id = _require_str("logical_invocation_id", logical_invocation_id)
            if is_refusal(parsed_id):
                return parsed_id
            invocation = parsed_id.value
        parent: str | None = None
        if parent_logical_invocation_id is not None:
            parsed_parent = _require_str(
                "parent_logical_invocation_id", parent_logical_invocation_id
            )
            if is_refusal(parsed_parent):
                return parsed_parent
            parent = parsed_parent.value
        revoked, expired = self._inactive(grant, now=when.value[0])
        if not revoked and not expired:
            return Ok(grant)
        accepted_here = self._already_accepted(
            grant_id=grant.grant_id, logical_invocation_id=invocation
        )
        accepted_parent = self._already_accepted(
            grant_id=grant.grant_id, logical_invocation_id=parent
        )
        may_finish = accepted_here or (
            parsed_moment.value is GrantEvaluationMoment.NESTED_CALL and accepted_parent
        )
        if may_finish and parsed_moment.value is not GrantEvaluationMoment.ACCEPT:
            return Ok(grant)
        if parsed_moment.value in _NEW_DISPATCH_MOMENTS or not may_finish:
            return GrantInactive.of(
                grant_id=grant.grant_id,
                reason=_inactive_reason(revoked=revoked, expired=expired),
                moment=parsed_moment.value.value,
                revoked=revoked,
                expired=expired,
                already_accepted=accepted_here,
            )
        return GrantInactive.of(
            grant_id=grant.grant_id,
            reason=_inactive_reason(revoked=revoked, expired=expired),
            moment=parsed_moment.value.value,
            revoked=revoked,
            expired=expired,
            already_accepted=accepted_here,
        )

    def accept(
        self,
        *,
        grant_id: object,
        logical_invocation_id: object,
        now: object,
    ) -> Result[AcceptedGrantWork]:
        """Accept work under a live grant. Later revoke does not unwind it."""
        evaluated = self.evaluate(
            grant_id=grant_id,
            moment=GrantEvaluationMoment.ACCEPT,
            now=now,
            logical_invocation_id=logical_invocation_id,
        )
        if is_refusal(evaluated):
            return evaluated
        invocation = _require_str("logical_invocation_id", logical_invocation_id)
        if is_refusal(invocation):
            return invocation
        self._accepted[invocation.value] = evaluated.value.grant_id
        return Ok(
            AcceptedGrantWork(
                grant_id=evaluated.value.grant_id,
                logical_invocation_id=invocation.value,
                moment=GrantEvaluationMoment.ACCEPT,
            )
        )

    def apply_upgrade(
        self,
        grant_id: object,
        **changes: object,
    ) -> GrantWidenRefused:
        """In-place upgrade/widen/retarget is refused. Re-grant instead."""
        token = grant_id if isinstance(grant_id, str) else repr(grant_id)
        return refuse_in_place_upgrade(
            grant_id=token,
            changes=sorted(changes),
            in_place=True,
        )

    def regrant(
        self,
        previous_grant_id: object,
        *,
        context_revision: object,
        from_revision: object | None = None,
        issuer: object = _HOST_ISSUER,
        principal: object | None = None,
        audience: object | None = None,
        contribution: object | None = None,
        instance_id: object | None = None,
        config_revision: object | None = None,
        op_id: object | None = None,
        op_version: object | None = None,
        effect_class: object | None = None,
        parameter_ceiling: object | None = None,
        expires_at: object | None = None,
        account_scope: object | None = None,
        grant_id: object | None = None,
    ) -> Result[RegrantResult]:
        """Mint a new GrantRecord and bump context_revision. Prior bytes stay."""
        if issuer != _HOST_ISSUER:
            return refuse_manifest_grant(issuer=issuer)
        gid = _require_str("previous_grant_id", previous_grant_id)
        if is_refusal(gid):
            return gid
        previous = self._grants.get(gid.value)
        if previous is None:
            return _invalid(
                "previous_grant_id",
                "re-grant requires an existing GrantRecord",
                grant_id=gid.value,
            )
        if not isinstance(context_revision, int) or isinstance(context_revision, bool):
            return _invalid(
                "context_revision",
                "explicit re-grant bumps context_revision",
                given=repr(context_revision),
            )
        if from_revision is None:
            base = self._context_revision
        elif isinstance(from_revision, bool) or not isinstance(from_revision, int):
            return _invalid(
                "from_revision",
                "explicit re-grant bumps context_revision",
                given=repr(from_revision),
            )
        else:
            base = from_revision
        expected = base + 1
        if context_revision != expected:
            return _invalid(
                "context_revision",
                "explicit re-grant bumps context_revision",
                expected=expected,
                given=context_revision,
            )
        minted = self.mint(
            issuer=issuer,
            grant_id=grant_id,
            principal=previous.principal if principal is None else principal,
            audience=previous.audience if audience is None else audience,
            contribution=(
                dict(previous.contribution.to_payload()) if contribution is None else contribution
            ),
            instance_id=previous.instance_id if instance_id is None else instance_id,
            config_revision=(
                previous.config_revision if config_revision is None else config_revision
            ),
            op_id=previous.op_id if op_id is None else op_id,
            op_version=previous.op_version if op_version is None else op_version,
            effect_class=(previous.effect_class.value if effect_class is None else effect_class),
            parameter_ceiling=(
                dict(previous.parameter_ceiling.to_payload())
                if parameter_ceiling is None
                else parameter_ceiling
            ),
            expires_at=previous.expires_at if expires_at is None else expires_at,
            account_scope=previous.account_scope if account_scope is None else account_scope,
        )
        if is_refusal(minted):
            return minted
        previous_bytes = self._minted_bytes[previous.grant_id]
        still = previous.canonical_bytes()
        if is_refusal(still):
            return still
        if still.value != previous_bytes:
            return _invalid(
                "previous_grant_id",
                "minted GrantRecord bytes must not change on re-grant",
                grant_id=previous.grant_id,
            )
        self._context_revision = context_revision
        return Ok(
            RegrantResult(
                grant=minted.value,
                previous_grant_id=previous.grant_id,
                previous_bytes=previous_bytes,
                context_revision=context_revision,
            )
        )

    def dispatch(
        self,
        *,
        transport: object,
        envelope: object,
        payload: object,
        contributions: Mapping[tuple[str, str], ContributionRecord],
        descriptors: Mapping[tuple[str, int], OperationDescriptor],
        instances: Mapping[tuple[str, int], InstanceRecord],
        now: object,
        execute: Callable[[BoundInvocation], None] | None = None,
        parent_permissions: object | None = None,
    ) -> Result[BoundInvocation]:
        """Evaluate the grant at dispatch/nested-call, then hop-compare."""
        parsed = parse_invocation_envelope(envelope)
        if is_refusal(parsed):
            return parsed
        env = parsed.value
        if transport is PublicCallTransport.NESTED or transport == PublicCallTransport.NESTED.value:
            moment = GrantEvaluationMoment.NESTED_CALL
            door: object = PublicCallTransport.NESTED
        else:
            moment = GrantEvaluationMoment.DISPATCH
            door = transport
        evaluated = self.evaluate(
            grant_id=env.grant_id,
            moment=moment,
            now=now,
            logical_invocation_id=env.logical_invocation_id,
            parent_logical_invocation_id=env.parent_logical_invocation_id,
        )
        if is_refusal(evaluated):
            return evaluated
        stores = self.authoritative_stores(
            contributions=contributions,
            descriptors=descriptors,
            instances=instances,
        )
        return dispatch_public_call(
            transport=door,
            envelope=env,
            payload=payload,
            stores=stores,
            execute=execute,
            parent_permissions=parent_permissions,
        )
