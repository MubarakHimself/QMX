"""Story 54.3 — caller idempotency domain, nested identity, journal retention."""

from __future__ import annotations

from qma.core.operations import public_operation_descriptors
from qma.core.refusals import (
    EnvelopeMismatch,
    IdempotencyCollision,
    NestedGrantUnionRefused,
    NestedPermissionUnionRefused,
)
from qma.wire import (
    HOST_MINTS_IDEMPOTENCY_KEY,
    IDEMPOTENCY_DOMAIN_FIELDS,
    IDEMPOTENCY_KEY_ISSUER,
    IDEMPOTENCY_RETENTION_FLOOR,
    AuthoritativeStores,
    BoundInvocation,
    ContributionBinding,
    ContributionRecord,
    GrantRecord,
    IdempotencyDomain,
    InstanceRecord,
    InvocationIdempotencyLedger,
    compute_input_hash,
    derive_child_logical_invocation_id,
    domain_from_mapping,
    mint_caller_idempotency_key,
    public_call_nested,
    refuse_host_minted_idempotency_key,
)
from qmf.core.chrono import Duration, Instant
from qmf.core.refusal import Ok, is_ok, is_refusal

_INPUT = {"run_fp1": "run-1"}


def _instant(ns: int) -> Instant:
    result = Instant.try_create(ns)
    assert isinstance(result, Ok)
    return result.value


def _duration(ns: int) -> Duration:
    result = Duration.try_create(ns)
    assert isinstance(result, Ok)
    return result.value


def _descriptor():
    for item in public_operation_descriptors():
        if item.op_id == "qmb.analysis.project" and item.version == 1:
            return item
    raise AssertionError("qmb.analysis.project v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _other_hash() -> str:
    hashed = compute_input_hash({"run_fp1": "run-2"}, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _envelope_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "logical_invocation_id": "inv:1",
        "attempt_id": 1,
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "contribution": {
            "qualified_id": "analysis-backtest:qmb",
            "package_version": "0.1.0",
        },
        "instance_id": "inst:1",
        "config_revision": 4,
        "grant_id": "grant:1",
        "effect_class": "read",
        "idempotency_key": "idem:1",
        "reconcile_policy": "query-then-decide",
        "input_hash": _hash(),
        "call_depth": 0,
        "caller_kind": "user",
    }
    payload.update(overrides)
    return payload


def _grant() -> GrantRecord:
    built = GrantRecord.try_create(
        grant_id="grant:1",
        principal="operator",
        audience="psess:caller",
        contribution={
            "qualified_id": "analysis-backtest:qmb",
            "package_version": "0.1.0",
        },
        instance_id="inst:1",
        config_revision=4,
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1", "as_of"]},
        expires_at="2099-01-01T00:00:00Z",
    )
    assert is_ok(built)
    return built.value


def _stores() -> AuthoritativeStores:
    descriptor = _descriptor()
    contribution = ContributionBinding(
        qualified_id="analysis-backtest:qmb",
        package_version="0.1.0",
    )
    record = ContributionRecord(
        qualified_id=contribution.qualified_id,
        package_version=contribution.package_version,
        availability="enabled",
    )
    grant = _grant()
    instance = InstanceRecord(instance_id="inst:1", config_revision=4)
    return AuthoritativeStores(
        contributions={record.as_tuple(): record},
        descriptors={(descriptor.op_id, descriptor.version): descriptor},
        grants={grant.grant_id: grant},
        instances={(instance.instance_id, instance.config_revision): instance},
    )


def test_idempotency_key_issuer_is_the_caller() -> None:
    assert IDEMPOTENCY_KEY_ISSUER == "caller"
    assert HOST_MINTS_IDEMPOTENCY_KEY is False
    minted = mint_caller_idempotency_key("idem:caller-1")
    assert is_ok(minted)
    assert minted.value == "idem:caller-1"
    host = mint_caller_idempotency_key("idem:host-1", issuer="host")
    assert is_refusal(host)
    assert host.context["required_issuer"] == "caller"
    assert host.context["host_mints"] is False
    refused = refuse_host_minted_idempotency_key()
    assert is_refusal(refused)


def test_uniqueness_domain_and_journal_lifetime_retention() -> None:
    assert IDEMPOTENCY_DOMAIN_FIELDS == (
        "principal",
        "op_id",
        "op_version",
        "instance_id",
        "config_revision",
        "grant_id",
        "target",
        "canonical_input_hash",
    )
    assert IDEMPOTENCY_RETENTION_FLOOR == "journal_lifetime"
    domain = domain_from_mapping(
        _envelope_payload(),
        principal="operator",
        target="inst:1",
    )
    assert is_ok(domain)
    assert domain.value.uniqueness_tuple()[-1] == _hash()
    assert domain.value.idempotency_key == "idem:1"
    ledger = InvocationIdempotencyLedger(journal_lifetime=_duration(100))
    assert ledger.retention_floor == "journal_lifetime"
    first = ledger.observe(
        domain.value,
        now=_instant(0),
        result={"status": "done", "value": 1},
    )
    assert is_ok(first)
    assert first.value.disposition == "accept"
    replay = ledger.observe(domain.value, now=_instant(50))
    assert is_ok(replay)
    assert replay.value.disposition == "replay"
    assert replay.value.is_replay is True
    assert dict(replay.value.prior_result or {}) == {"status": "done", "value": 1}
    expired = ledger.observe(domain.value, now=_instant(101))
    assert is_ok(expired)
    assert expired.value.disposition == "accept"


def test_collision_with_different_payload_hash_is_typed_refusal() -> None:
    first_domain = domain_from_mapping(
        _envelope_payload(),
        principal="operator",
        target="inst:1",
    )
    collided = domain_from_mapping(
        _envelope_payload(input_hash=_other_hash()),
        principal="operator",
        target="inst:1",
        canonical_input_hash=_other_hash(),
    )
    assert is_ok(first_domain) and is_ok(collided)
    ledger = InvocationIdempotencyLedger(journal_lifetime=_duration(1_000))
    accepted = ledger.observe(
        first_domain.value,
        now=_instant(0),
        result={"status": "done"},
    )
    assert is_ok(accepted)
    refused = ledger.observe(collided.value, now=_instant(1))
    assert is_refusal(refused)
    assert isinstance(refused, IdempotencyCollision)
    assert refused.context["stored_hash"] == _hash()
    assert refused.context["given_hash"] == _other_hash()
    assert refused.context["issuer"] == "caller"


def test_child_logical_invocation_id_derives_from_parent_tuple() -> None:
    derived = derive_child_logical_invocation_id(
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        child_op_id="qmb.analysis.project",
        child_canonical_input_hash=_hash(),
    )
    assert is_ok(derived)
    again = derive_child_logical_invocation_id(
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        child_op_id="qmb.analysis.project",
        child_canonical_input_hash=_hash(),
    )
    assert is_ok(again)
    assert derived.value == again.value
    different_depth = derive_child_logical_invocation_id(
        parent_logical_invocation_id="inv:1",
        call_depth=2,
        child_op_id="qmb.analysis.project",
        child_canonical_input_hash=_hash(),
    )
    assert is_ok(different_depth)
    assert different_depth.value != derived.value
    stores = _stores()
    nested_payload = _envelope_payload(
        logical_invocation_id=derived.value,
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        caller_kind="workflow",
    )
    nested = public_call_nested(nested_payload, _INPUT, stores)
    assert is_ok(nested)
    assert nested.value.envelope.logical_invocation_id == derived.value
    forged = public_call_nested(
        _envelope_payload(
            logical_invocation_id="inv:forged",
            parent_logical_invocation_id="inv:1",
            call_depth=1,
            caller_kind="workflow",
        ),
        _INPUT,
        stores,
    )
    assert is_refusal(forged)
    assert isinstance(forged, EnvelopeMismatch)
    assert forged.context["reason"] == "child_id_must_derive_from_parent"


def test_nested_public_call_does_not_union_permissions() -> None:
    derived = derive_child_logical_invocation_id(
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        child_op_id="qmb.analysis.project",
        child_canonical_input_hash=_hash(),
    )
    assert is_ok(derived)
    nested_payload = _envelope_payload(
        logical_invocation_id=derived.value,
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        caller_kind="workflow",
    )
    refused = public_call_nested(
        nested_payload,
        _INPUT,
        _stores(),
        parent_permissions=(),
    )
    assert is_refusal(refused)
    assert isinstance(refused, NestedPermissionUnionRefused)
    bound = public_call_nested(
        nested_payload,
        _INPUT,
        _stores(),
        parent_permissions=["library.read"],
    )
    assert is_ok(bound)
    assert isinstance(bound.value, BoundInvocation)


def test_nested_public_call_does_not_union_grants() -> None:
    derived = derive_child_logical_invocation_id(
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        child_op_id="qmb.analysis.project",
        child_canonical_input_hash=_hash(),
    )
    assert is_ok(derived)
    nested_payload = _envelope_payload(
        logical_invocation_id=derived.value,
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        caller_kind="workflow",
        grant_id="grant:1",
    )
    child = public_call_nested(
        nested_payload,
        _INPUT,
        _stores(),
        parent_grants=("grant:home",),
        child_grants=("grant:1",),
    )
    assert is_ok(child)
    assert child.value.grant.grant_id == "grant:1"
    leaked = public_call_nested(
        nested_payload,
        _INPUT,
        _stores(),
        parent_grants=("grant:home", "grant:1"),
        child_grants=("grant:1",),
        union_grants=True,
    )
    assert is_refusal(leaked)
    assert isinstance(leaked, NestedGrantUnionRefused)
    assert leaked.context["union"] is False
    caller_only = public_call_nested(
        _envelope_payload(
            logical_invocation_id=derived.value,
            parent_logical_invocation_id="inv:1",
            call_depth=1,
            caller_kind="workflow",
            grant_id="grant:1",
            idempotency_key="idem:caller-grant",
        ),
        _INPUT,
        _stores(),
        parent_grants=("grant:1",),
        child_grants=("grant:app",),
    )
    assert is_refusal(caller_only)
    assert isinstance(caller_only, NestedGrantUnionRefused)


def test_idempotency_domain_dataclass_round_trip() -> None:
    domain = IdempotencyDomain(
        principal="operator",
        op_id="qmb.analysis.project",
        op_version=1,
        instance_id="inst:1",
        config_revision=4,
        grant_id="grant:1",
        target="inst:1",
        canonical_input_hash=_hash(),
        idempotency_key="idem:1",
    )
    payload = dict(domain.to_payload())
    assert payload["issuer"] == "caller"
    assert payload["canonical_input_hash"] == _hash()
    assert domain.scope_tuple()[-1] == "idem:1"
