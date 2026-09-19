"""Caller-issued invocation idempotency and nested identity (Story 54.3).

Issuer of ``idempotency_key`` is the caller. Uniqueness domain is
``(principal, op_id, op_version, instance_id, config_revision, grant_id,
target, canonical_input_hash)``. Retention is at least the journal lifetime
of the invocation. Collision with a different payload hash is a typed
refusal; replay of the same key within retention returns the prior result
(FR-WF-19; RC-04). Child ``logical_invocation_id`` derives from
``(parent_logical_invocation_id, call_depth, child_op_id,
child_canonical_input_hash)`` (FR-WF-20).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal

from qma.core.refusals.variants import EnvelopeMismatch, IdempotencyCollision
from qmf.core.chrono import Duration, Instant
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "HOST_MINTS_IDEMPOTENCY_KEY",
    "IDEMPOTENCY_DOMAIN_FIELDS",
    "IDEMPOTENCY_KEY_ISSUER",
    "IDEMPOTENCY_RETENTION_FLOOR",
    "IdempotencyDomain",
    "IdempotencyObserveResult",
    "InvocationIdempotencyLedger",
    "assert_child_logical_invocation_id",
    "derive_child_logical_invocation_id",
    "domain_from_mapping",
    "mint_caller_idempotency_key",
    "refuse_host_minted_idempotency_key",
]


IDEMPOTENCY_KEY_ISSUER: Final[str] = "caller"
HOST_MINTS_IDEMPOTENCY_KEY: Final[bool] = False
IDEMPOTENCY_RETENTION_FLOOR: Final[str] = "journal_lifetime"
IDEMPOTENCY_DOMAIN_FIELDS: Final[tuple[str, ...]] = (
    "principal",
    "op_id",
    "op_version",
    "instance_id",
    "config_revision",
    "grant_id",
    "target",
    "canonical_input_hash",
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _require_str(field: str, value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(field, f"{field} must be a non-empty string", given=repr(value))
    return Ok(value.strip())


def _require_int(field: str, value: object, *, minimum: int) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(field, f"{field} must be an integer", given=repr(value))
    if value < minimum:
        return _invalid(field, f"{field} must be >= {minimum}", given=value)
    return Ok(value)


def _parse_input_hash(field: str, value: object) -> Result[str]:
    token = _require_str(field, value)
    if not isinstance(token, Ok):
        return token
    parsed = Fingerprint.try_create(token.value)
    if not isinstance(parsed, Ok):
        return _invalid(
            field,
            f"{field} is fp1:sha256:<hex> over canonical JSON of the payload",
            given=token.value,
        )
    return Ok(parsed.value.value)


def mint_caller_idempotency_key(
    token: object,
    *,
    issuer: object = IDEMPOTENCY_KEY_ISSUER,
) -> Result[str]:
    """Mint an ``idempotency_key``. Issuer is the caller; the host never mints."""
    if issuer != IDEMPOTENCY_KEY_ISSUER:
        return refuse_host_minted_idempotency_key(issuer=issuer)
    return _require_str("idempotency_key", token)


def refuse_host_minted_idempotency_key(*, issuer: object = "host") -> TypedRefusal:
    """Host-minted ``idempotency_key`` is refused (FR-WF-19)."""
    return _invalid(
        "idempotency_key",
        "idempotency_key issuer is the caller; the host never mints a substitute",
        issuer=repr(issuer) if not isinstance(issuer, str) else issuer,
        required_issuer=IDEMPOTENCY_KEY_ISSUER,
        host_mints=HOST_MINTS_IDEMPOTENCY_KEY,
    )


@dataclass(frozen=True, slots=True)
class IdempotencyDomain:
    """Uniqueness domain for a caller-issued ``idempotency_key`` (RC-04)."""

    principal: str
    op_id: str
    op_version: int
    instance_id: str
    config_revision: int
    grant_id: str
    target: str
    canonical_input_hash: str
    idempotency_key: str

    def uniqueness_tuple(self) -> tuple[object, ...]:
        return (
            self.principal,
            self.op_id,
            self.op_version,
            self.instance_id,
            self.config_revision,
            self.grant_id,
            self.target,
            self.canonical_input_hash,
        )

    def scope_tuple(self) -> tuple[object, ...]:
        """Lookup scope: domain without hash, plus the caller key."""
        return (
            self.principal,
            self.op_id,
            self.op_version,
            self.instance_id,
            self.config_revision,
            self.grant_id,
            self.target,
            self.idempotency_key,
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "canonical_input_hash": self.canonical_input_hash,
                "config_revision": self.config_revision,
                "grant_id": self.grant_id,
                "idempotency_key": self.idempotency_key,
                "instance_id": self.instance_id,
                "issuer": IDEMPOTENCY_KEY_ISSUER,
                "op_id": self.op_id,
                "op_version": self.op_version,
                "principal": self.principal,
                "target": self.target,
            }
        )


def domain_from_mapping(
    value: Mapping[str, object],
    *,
    principal: object,
    target: object,
    idempotency_key: object | None = None,
    canonical_input_hash: object | None = None,
) -> Result[IdempotencyDomain]:
    """Build the uniqueness domain from envelope fields plus caller principal/target."""
    issuer_key = mint_caller_idempotency_key(
        value.get("idempotency_key") if idempotency_key is None else idempotency_key
    )
    if not isinstance(issuer_key, Ok):
        return issuer_key
    principal_token = _require_str("principal", principal)
    if not isinstance(principal_token, Ok):
        return principal_token
    op_id = _require_str("op_id", value.get("op_id"))
    if not isinstance(op_id, Ok):
        return op_id
    op_version = _require_int("op_version", value.get("op_version"), minimum=1)
    if not isinstance(op_version, Ok):
        return op_version
    instance_id = _require_str("instance_id", value.get("instance_id"))
    if not isinstance(instance_id, Ok):
        return instance_id
    revision = _require_int("config_revision", value.get("config_revision"), minimum=0)
    if not isinstance(revision, Ok):
        return revision
    grant_id = _require_str("grant_id", value.get("grant_id"))
    if not isinstance(grant_id, Ok):
        return grant_id
    target_token = _require_str("target", target)
    if not isinstance(target_token, Ok):
        return target_token
    hashed = _parse_input_hash(
        "canonical_input_hash",
        value.get("input_hash") if canonical_input_hash is None else canonical_input_hash,
    )
    if not isinstance(hashed, Ok):
        return hashed
    return Ok(
        IdempotencyDomain(
            principal=principal_token.value,
            op_id=op_id.value,
            op_version=op_version.value,
            instance_id=instance_id.value,
            config_revision=revision.value,
            grant_id=grant_id.value,
            target=target_token.value,
            canonical_input_hash=hashed.value,
            idempotency_key=issuer_key.value,
        )
    )


def derive_child_logical_invocation_id(
    *,
    parent_logical_invocation_id: object,
    call_depth: object,
    child_op_id: object,
    child_canonical_input_hash: object,
) -> Result[str]:
    """Deterministic child id from parent, depth, child op, and child input hash."""
    parent = _require_str("parent_logical_invocation_id", parent_logical_invocation_id)
    if not isinstance(parent, Ok):
        return parent
    depth = _require_int("call_depth", call_depth, minimum=1)
    if not isinstance(depth, Ok):
        return depth
    child_op = _require_str("child_op_id", child_op_id)
    if not isinstance(child_op, Ok):
        return child_op
    child_hash = _parse_input_hash("child_canonical_input_hash", child_canonical_input_hash)
    if not isinstance(child_hash, Ok):
        return child_hash
    preimage = {
        "call_depth": depth.value,
        "child_canonical_input_hash": child_hash.value,
        "child_op_id": child_op.value,
        "parent_logical_invocation_id": parent.value,
    }
    fp = fingerprint(preimage)
    if not isinstance(fp, Ok):
        return fp
    return Ok(fp.value.value)


def assert_child_logical_invocation_id(
    *,
    logical_invocation_id: object,
    parent_logical_invocation_id: object,
    call_depth: object,
    child_op_id: object,
    child_canonical_input_hash: object,
) -> Result[str]:
    """Refuse a nested id that does not derive from the parent tuple (FR-WF-20)."""
    derived = derive_child_logical_invocation_id(
        parent_logical_invocation_id=parent_logical_invocation_id,
        call_depth=call_depth,
        child_op_id=child_op_id,
        child_canonical_input_hash=child_canonical_input_hash,
    )
    if not isinstance(derived, Ok):
        return derived
    given = _require_str("logical_invocation_id", logical_invocation_id)
    if not isinstance(given, Ok):
        return given
    if given.value != derived.value:
        return EnvelopeMismatch.of(
            field="logical_invocation_id",
            bound=given.value,
            live=derived.value,
            reason="child_id_must_derive_from_parent",
            parent_logical_invocation_id=parent_logical_invocation_id
            if isinstance(parent_logical_invocation_id, str)
            else derived.value,
        )
    return Ok(derived.value)


def _empty_seen() -> dict[
    tuple[object, ...],
    tuple[IdempotencyDomain, Instant, Mapping[str, object]],
]:
    return {}


@dataclass(frozen=True, slots=True)
class IdempotencyObserveResult:
    """Accept a first delivery or replay the prior durable result."""

    domain: IdempotencyDomain
    disposition: Literal["accept", "replay"]
    first_seen_at: Instant
    retention_floor: str = IDEMPOTENCY_RETENTION_FLOOR
    prior_result: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if self.prior_result is not None:
            object.__setattr__(self, "prior_result", MappingProxyType(dict(self.prior_result)))

    @property
    def is_replay(self) -> bool:
        return self.disposition == "replay"


@dataclass
class InvocationIdempotencyLedger:
    """In-memory contract model of invocation idempotency retention.

    Retention is the invocation journal lifetime — never the wire command
    ``registry:wire.dedup_window``. Entries are not pruned earlier.
    """

    journal_lifetime: Duration
    _seen: dict[
        tuple[object, ...],
        tuple[IdempotencyDomain, Instant, Mapping[str, object]],
    ] = field(default_factory=_empty_seen, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.journal_lifetime.value_ns <= 0:
            msg = f"{IDEMPOTENCY_RETENTION_FLOOR} must be a positive duration"
            raise ValueError(msg)

    @property
    def retention_floor(self) -> str:
        return IDEMPOTENCY_RETENTION_FLOOR

    def _in_retention(self, first_seen: Instant, now: Instant) -> bool:
        return now.value_ns - first_seen.value_ns <= self.journal_lifetime.value_ns

    def observe(
        self,
        domain: object,
        *,
        now: object,
        result: Mapping[str, object] | None = None,
    ) -> Result[IdempotencyObserveResult]:
        """Replay the prior result or refuse a payload-hash collision."""
        if not isinstance(domain, IdempotencyDomain):
            return _invalid(
                "idempotency_domain",
                "observe requires an IdempotencyDomain",
                given=repr(domain),
            )
        if not isinstance(now, Instant):
            return _invalid(
                "now",
                "idempotency observation time must be an Instant",
                given=repr(now),
            )

        stored = self._seen.get(domain.scope_tuple())
        if stored is not None:
            prior_domain, first_seen, prior_result = stored
            if self._in_retention(first_seen, now):
                if prior_domain.canonical_input_hash != domain.canonical_input_hash:
                    return IdempotencyCollision.of(
                        idempotency_key=domain.idempotency_key,
                        stored_hash=prior_domain.canonical_input_hash,
                        given_hash=domain.canonical_input_hash,
                        principal=domain.principal,
                        op_id=domain.op_id,
                        target=domain.target,
                    )
                return Ok(
                    IdempotencyObserveResult(
                        domain=prior_domain,
                        disposition="replay",
                        first_seen_at=first_seen,
                        prior_result=prior_result,
                    )
                )

        payload = dict(result) if result is not None else {}
        self._seen[domain.scope_tuple()] = (domain, now, MappingProxyType(payload))
        return Ok(
            IdempotencyObserveResult(
                domain=domain,
                disposition="accept",
                first_seen_at=now,
                prior_result=None,
            )
        )
