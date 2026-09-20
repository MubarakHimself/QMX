"""Story 54.4 — GrantRecord is immutable; revocation is a separate record."""

from __future__ import annotations

from qma.core.operations import OperationDescriptor, public_operation_descriptors
from qma.core.refusals import GrantInactive, GrantWidenRefused, ManifestIsNotGrant
from qma.core.vocabulary import GrantEvaluationMoment
from qma.wire import (
    GRANT_ID_PREFIX,
    GRANT_RECORD_CONTRACT,
    GRANT_RECORD_DTO_OWNER,
    GRANT_RECORD_FIELDS,
    GRANT_RECORD_FORBIDDEN_FIELDS,
    GRANT_RECORD_NEW_CT_MINTED,
    GRANT_RECORD_REFUSED_CT,
    GRANT_RECORD_SCHEMA,
    GRANT_RECORD_SCHEMA_FILE,
    GRANT_RECORD_SCHEMA_NAME,
    GRANT_REVOCATION_FIELDS,
    GRANT_REVOCATION_SCHEMA_FILE,
    GRANT_REVOCATION_SCHEMA_NAME,
    GRANTED_OPS_STORE_BARE_OP_IDS,
    GRANTED_OPS_STORE_GRANT_IDS,
    HOST_GRANTS,
    MANIFESTS_GRANT,
    PRODUCT_SESSION_ROWS_MINTED,
    SCHEMA_FILES,
    ContributionRecord,
    GrantRecord,
    HostGrantLedger,
    InstanceRecord,
    PublicCallTransport,
    compute_input_hash,
    derive_child_logical_invocation_id,
    parse_grant_record,
    parse_granted_ops,
    refuse_in_place_upgrade,
    refuse_manifest_grant,
    refuse_product_session_rows,
    validate_grant_record,
    validate_grant_revocation,
)
from qmf.core import is_ok, is_refusal

_INPUT = {"run_fp1": "run-1"}
_NOW = "2026-09-20T00:00:00Z"
_EXPIRES = "2026-12-31T00:00:00Z"
_AFTER_EXPIRY = "2027-01-01T00:00:00Z"


def _descriptor() -> OperationDescriptor:
    for item in public_operation_descriptors():
        if item.op_id == "qmb.analysis.project" and item.version == 1:
            return item
    raise AssertionError("qmb.analysis.project v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _contribution() -> dict[str, str]:
    return {"qualified_id": "analysis-backtest:qmb", "package_version": "0.1.0"}


def _grant_fields(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "grant_id": "grant:1",
        "principal": "operator",
        "audience": "psess:session",
        "contribution": _contribution(),
        "instance_id": "inst:1",
        "config_revision": 4,
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "effect_class": "read",
        "parameter_ceiling": {"allow_keys": ["run_fp1", "as_of"]},
        "expires_at": _EXPIRES,
    }
    fields.update(overrides)
    return fields


def _envelope_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "logical_invocation_id": "inv:1",
        "attempt_id": 1,
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "contribution": _contribution(),
        "instance_id": "inst:1",
        "config_revision": 4,
        "grant_id": "grant:1",
        "effect_class": "read",
        "idempotency_key": "idem:1",
        "reconcile_policy": "query-then-decide",
        "input_hash": _hash(),
        "call_depth": 0,
    }
    payload.update(overrides)
    return payload


def _stores_parts() -> tuple[
    dict[tuple[str, str], ContributionRecord],
    dict[tuple[str, int], OperationDescriptor],
    dict[tuple[str, int], InstanceRecord],
]:
    descriptor = _descriptor()
    contribution = ContributionRecord(
        qualified_id="analysis-backtest:qmb",
        package_version="0.1.0",
        availability="enabled",
    )
    instance = InstanceRecord(instance_id="inst:1", config_revision=4)
    return (
        {contribution.as_tuple(): contribution},
        {(descriptor.op_id, descriptor.version): descriptor},
        {(instance.instance_id, instance.config_revision): instance},
    )


def test_grant_record_contract_surface_and_no_revoked_at() -> None:
    assert GRANT_RECORD_CONTRACT == "CT-40"
    assert GRANT_RECORD_DTO_OWNER == "COMP-QMA-WIRE"
    assert GRANT_RECORD_NEW_CT_MINTED is False
    assert GRANT_RECORD_REFUSED_CT == "CT-52"
    assert GRANT_RECORD_SCHEMA == "qma.wire.grant_record.v1"
    assert SCHEMA_FILES[GRANT_RECORD_SCHEMA_NAME] == GRANT_RECORD_SCHEMA_FILE
    assert SCHEMA_FILES[GRANT_REVOCATION_SCHEMA_NAME] == GRANT_REVOCATION_SCHEMA_FILE
    assert "revoked_at" not in GRANT_RECORD_FIELDS
    assert "revoked_at" in GRANT_RECORD_FORBIDDEN_FIELDS
    assert "revoked_at" not in GrantRecord.__dataclass_fields__
    assert GRANT_RECORD_FIELDS == (
        "grant_id",
        "principal",
        "audience",
        "contribution",
        "instance_id",
        "config_revision",
        "op_id",
        "op_version",
        "effect_class",
        "parameter_ceiling",
        "account_scope",
        "expires_at",
    )
    assert GRANT_REVOCATION_FIELDS == ("grant_id", "revoked_at", "principal", "reason")
    assert GRANT_ID_PREFIX == "grant:"
    assert MANIFESTS_GRANT is False
    assert HOST_GRANTS is True
    assert PRODUCT_SESSION_ROWS_MINTED is False
    assert GRANTED_OPS_STORE_GRANT_IDS is True
    assert GRANTED_OPS_STORE_BARE_OP_IDS is False


def test_minted_grant_record_includes_contracts_fields() -> None:
    built = GrantRecord.try_create(**_grant_fields())
    assert is_ok(built)
    grant = built.value
    payload = dict(grant.to_payload())
    for name in GRANT_RECORD_FIELDS:
        if name == "account_scope":
            assert name not in payload
        else:
            assert name in payload
    assert "revoked_at" not in payload
    assert payload["principal"] == "operator"
    assert payload["audience"] == "psess:session"
    assert payload["parameter_ceiling"] == {"allow_keys": ["run_fp1", "as_of"]}
    assert payload["expires_at"] == _EXPIRES
    assert grant.account_scope is None
    schema_ok = validate_grant_record(payload)
    assert is_ok(schema_ok)
    round_trip = parse_grant_record(payload)
    assert is_ok(round_trip)
    assert round_trip.value.to_payload() == grant.to_payload()
    refused = GrantRecord.try_create(**_grant_fields(revoked_at="2026-09-19T14:00:00Z"))
    assert is_refusal(refused)
    assert refused.context["field"] == "revoked_at"
    parsed = parse_grant_record({**_grant_fields(), "revoked_at": "2026-09-19T14:00:00Z"})
    assert is_refusal(parsed)
    assert parsed.context["field"] == "revoked_at"


def test_account_scope_is_omitted_unless_granted() -> None:
    none_scope = GrantRecord.try_create(**_grant_fields())
    assert is_ok(none_scope)
    assert "account_scope" not in none_scope.value.to_payload()
    granted = GrantRecord.try_create(**_grant_fields(account_scope="acct:paper-1"))
    assert is_ok(granted)
    assert granted.value.to_payload()["account_scope"] == "acct:paper-1"


def test_revocation_is_append_only_and_does_not_change_minted_bytes() -> None:
    ledger = HostGrantLedger()
    minted = ledger.mint(issuer="host", **_grant_fields())
    assert is_ok(minted)
    grant = minted.value
    before = grant.canonical_bytes()
    assert is_ok(before)
    assert ledger.minted_bytes(grant.grant_id) == before.value
    first = ledger.revoke(
        grant_id=grant.grant_id,
        principal="operator",
        reason="session-ended",
        revoked_at="2026-09-19T14:00:00Z",
    )
    assert is_ok(first)
    payload = dict(first.value.to_payload())
    assert payload == {
        "grant_id": "grant:1",
        "principal": "operator",
        "reason": "session-ended",
        "revoked_at": "2026-09-19T14:00:00Z",
    }
    schema_ok = validate_grant_revocation(payload)
    assert is_ok(schema_ok)
    after = grant.canonical_bytes()
    assert is_ok(after)
    assert after.value == before.value
    assert dict(ledger.grants[grant.grant_id].to_payload()) == dict(grant.to_payload())
    second = ledger.revoke(
        grant_id=grant.grant_id,
        principal="operator",
        reason="operator-revoke",
        revoked_at="2026-09-19T15:00:00Z",
    )
    assert is_ok(second)
    assert len(ledger.revocations) == 2
    still = ledger.grants[grant.grant_id].canonical_bytes()
    assert is_ok(still)
    assert still.value == before.value


def test_already_accepted_work_may_finish_new_dispatch_is_refused() -> None:
    ledger = HostGrantLedger()
    assert is_ok(ledger.mint(issuer="host", **_grant_fields()))
    accepted = ledger.accept(grant_id="grant:1", logical_invocation_id="inv:1", now=_NOW)
    assert is_ok(accepted)
    contributions, descriptors, instances = _stores_parts()

    revoked = ledger.revoke(
        grant_id="grant:1",
        principal="operator",
        reason="session-ended",
        revoked_at=_NOW,
    )
    assert is_ok(revoked)

    retry = ledger.evaluate(
        grant_id="grant:1",
        moment=GrantEvaluationMoment.RETRY,
        now=_NOW,
        logical_invocation_id="inv:1",
    )
    assert is_ok(retry)
    commit = ledger.evaluate(
        grant_id="grant:1",
        moment="external_commit",
        now=_NOW,
        logical_invocation_id="inv:1",
    )
    assert is_ok(commit)
    dispatch_accepted = ledger.dispatch(
        transport=PublicCallTransport.IN_PROCESS,
        envelope=_envelope_payload(),
        payload=_INPUT,
        contributions=contributions,
        descriptors=descriptors,
        instances=instances,
        now=_NOW,
    )
    assert is_ok(dispatch_accepted)

    new_dispatch = ledger.dispatch(
        transport=PublicCallTransport.CLI,
        envelope=_envelope_payload(logical_invocation_id="inv:new", idempotency_key="idem:new"),
        payload=_INPUT,
        contributions=contributions,
        descriptors=descriptors,
        instances=instances,
        now=_NOW,
    )
    assert is_refusal(new_dispatch)
    assert isinstance(new_dispatch, GrantInactive)
    assert new_dispatch.context["reason"] == "revoked"
    assert new_dispatch.context["moment"] == "dispatch"
    assert new_dispatch.context["new_dispatch_refused"] is True

    child_id = derive_child_logical_invocation_id(
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        child_op_id="qmb.analysis.project",
        child_canonical_input_hash=_hash(),
    )
    assert is_ok(child_id)
    nested = ledger.evaluate(
        grant_id="grant:1",
        moment=GrantEvaluationMoment.NESTED_CALL,
        now=_NOW,
        logical_invocation_id=child_id.value,
        parent_logical_invocation_id="inv:1",
    )
    assert is_ok(nested)
    nested_new = ledger.evaluate(
        grant_id="grant:1",
        moment="nested_call",
        now=_NOW,
        logical_invocation_id="inv:orphan",
        parent_logical_invocation_id="inv:other",
    )
    assert is_refusal(nested_new)
    assert isinstance(nested_new, GrantInactive)


def test_expiry_refuses_new_dispatch_and_accept() -> None:
    ledger = HostGrantLedger()
    assert is_ok(ledger.mint(issuer="host", **_grant_fields()))
    expired_accept = ledger.accept(
        grant_id="grant:1",
        logical_invocation_id="inv:late",
        now=_AFTER_EXPIRY,
    )
    assert is_refusal(expired_accept)
    assert isinstance(expired_accept, GrantInactive)
    assert expired_accept.context["reason"] == "expired"
    assert expired_accept.context["moment"] == "accept"

    live_accept = ledger.accept(grant_id="grant:1", logical_invocation_id="inv:1", now=_NOW)
    assert is_ok(live_accept)
    finish = ledger.evaluate(
        grant_id="grant:1",
        moment="retry",
        now=_AFTER_EXPIRY,
        logical_invocation_id="inv:1",
    )
    assert is_ok(finish)
    new_after_expiry = ledger.evaluate(
        grant_id="grant:1",
        moment="dispatch",
        now=_AFTER_EXPIRY,
        logical_invocation_id="inv:2",
    )
    assert is_refusal(new_after_expiry)
    assert isinstance(new_after_expiry, GrantInactive)
    assert new_after_expiry.context["expired"] is True


def test_upgrade_cannot_widen_or_retarget_without_regrant() -> None:
    ledger = HostGrantLedger()
    minted = ledger.mint(issuer="host", **_grant_fields())
    assert is_ok(minted)
    before = minted.value.canonical_bytes()
    assert is_ok(before)
    in_place = ledger.apply_upgrade(
        "grant:1",
        package_version="0.2.0",
        allow_keys=["run_fp1", "as_of", "secret"],
        instance_id="inst:2",
    )
    assert isinstance(in_place, GrantWidenRefused)
    assert in_place.context["requires_regrant"] is True
    assert in_place.context["bumps_context_revision"] is True
    same = refuse_in_place_upgrade(grant_id="grant:1")
    assert isinstance(same, GrantWidenRefused)
    assert ledger.context_revision == 0
    stale = ledger.regrant(
        "grant:1",
        context_revision=0,
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "0.2.0"},
        parameter_ceiling={"allow_keys": ["run_fp1", "as_of", "extra"]},
        instance_id="inst:2",
        grant_id="grant:2",
    )
    assert is_refusal(stale)
    assert stale.context["field"] == "context_revision"
    regranted = ledger.regrant(
        "grant:1",
        context_revision=1,
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "0.2.0"},
        parameter_ceiling={"allow_keys": ["run_fp1", "as_of", "extra"]},
        instance_id="inst:2",
        grant_id="grant:2",
    )
    assert is_ok(regranted)
    assert regranted.value.context_revision == 1
    assert ledger.context_revision == 1
    assert regranted.value.grant.grant_id == "grant:2"
    assert regranted.value.previous_grant_id == "grant:1"
    assert regranted.value.previous_bytes == before.value
    still = ledger.grants["grant:1"].canonical_bytes()
    assert is_ok(still)
    assert still.value == before.value
    assert ledger.grants["grant:1"].contribution.package_version == "0.1.0"
    assert ledger.grants["grant:2"].contribution.package_version == "0.2.0"
    assert ledger.grants["grant:2"].parameter_ceiling.allow_keys == (
        "run_fp1",
        "as_of",
        "extra",
    )


def test_manifests_request_host_grants() -> None:
    ledger = HostGrantLedger()
    refused = ledger.mint(issuer="manifest", **_grant_fields())
    assert is_refusal(refused)
    assert isinstance(refused, ManifestIsNotGrant)
    assert refused.context["manifests_grant"] is False
    assert refused.context["host_grants"] is True
    assert MANIFESTS_GRANT is False is (not HOST_GRANTS)
    assert HOST_GRANTS is True
    same = refuse_manifest_grant()
    assert isinstance(same, ManifestIsNotGrant)
    minted = ledger.mint(issuer="host", **_grant_fields())
    assert is_ok(minted)
    assert minted.value.grant_id.startswith(GRANT_ID_PREFIX)


def test_granted_ops_are_grant_ids_and_product_session_rows_are_not_minted() -> None:
    ledger = HostGrantLedger()
    assert is_ok(ledger.mint(issuer="host", **_grant_fields()))
    ops = ledger.granted_ops()
    assert is_ok(ops)
    assert ops.value.grant_ids == ("grant:1",)
    assert ops.value.stores_grant_ids is True
    assert ops.value.stores_bare_op_ids is False
    assert ops.value.product_session_rows_minted is False
    assert "product_session_id" not in ops.value.to_payload()
    parsed = parse_granted_ops(["grant:1", "grant:2"])
    assert is_ok(parsed)
    bare = parse_granted_ops(["qmb.analysis.project"])
    assert is_refusal(bare)
    assert bare.context["granted_ops_store_bare_op_ids"] is False
    rows = refuse_product_session_rows()
    assert is_refusal(rows)
    assert rows.context["product_session_rows_minted"] is False
    assert PRODUCT_SESSION_ROWS_MINTED is False
