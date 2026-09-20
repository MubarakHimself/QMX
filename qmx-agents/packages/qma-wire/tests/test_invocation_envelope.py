"""Story 54.2 — InvocationEnvelope is bound request context, not authority."""

from __future__ import annotations

from collections.abc import Callable

from qma.core.operations import public_operation_descriptors
from qma.core.refusals import (
    AmbiguousResolution,
    EnvelopeMismatch,
    GrantMismatch,
    InvocationEnvelopeRequired,
    StaleObservation,
)
from qma.wire import (
    AMBIGUOUS_RESOLUTION_TOKENS,
    ENVELOPE_CRYPTO_ALGORITHM_SELECTED,
    ENVELOPE_CRYPTO_GAP,
    INVOCATION_ENVELOPE_CONTRACT,
    INVOCATION_ENVELOPE_DTO_OWNER,
    INVOCATION_ENVELOPE_FIELDS,
    INVOCATION_ENVELOPE_INSPECT_SHAS,
    INVOCATION_ENVELOPE_IS_AUTHORITY,
    INVOCATION_ENVELOPE_NEW_CT_MINTED,
    INVOCATION_ENVELOPE_OPTIONAL_FIELDS,
    INVOCATION_ENVELOPE_REFUSED_CT,
    INVOCATION_ENVELOPE_REQUIRED_FIELDS,
    INVOCATION_ENVELOPE_SCHEMA,
    INVOCATION_ENVELOPE_SCHEMA_FILE,
    INVOCATION_ENVELOPE_SCHEMA_NAME,
    INVOCATION_ENVELOPE_WIRED_AT_INSPECT_SHA,
    PUBLIC_CALL_TRANSPORTS,
    SCHEMA_FILES,
    AuthoritativeStores,
    BoundInvocation,
    ContributionBinding,
    ContributionRecord,
    GrantRecord,
    InstanceRecord,
    InvocationEnvelope,
    PublicCallTransport,
    WireEnvelope,
    compute_input_hash,
    derive_child_logical_invocation_id,
    parse_invocation_envelope,
    public_call_from_cli,
    public_call_from_wire,
    public_call_in_process,
    public_call_nested,
    validate_invocation_envelope,
)
from qmf.core import is_ok, is_refusal

_INPUT = {"run_fp1": "run-1"}


def _capture(executed: list[BoundInvocation]) -> Callable[[BoundInvocation], None]:
    def execute(bound: BoundInvocation) -> None:
        executed.append(bound)

    return execute


def _descriptor():
    for item in public_operation_descriptors():
        if item.op_id == "qmb.analysis.project" and item.version == 1:
            return item
    raise AssertionError("qmb.analysis.project v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
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
        "caller_session_ref": "psess:caller",
        "grant_id": "grant:1",
        "effect_class": "read",
        "idempotency_key": "idem:1",
        "reconcile_policy": "query-then-decide",
        "input_hash": _hash(),
        "call_depth": 0,
    }
    payload.update(overrides)
    return payload


def _grant(**overrides: object) -> GrantRecord:
    fields: dict[str, object] = {
        "grant_id": "grant:1",
        "principal": "operator",
        "audience": "psess:caller",
        "contribution": {
            "qualified_id": "analysis-backtest:qmb",
            "package_version": "0.1.0",
        },
        "instance_id": "inst:1",
        "config_revision": 4,
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "effect_class": "read",
        "parameter_ceiling": {"allow_keys": ["run_fp1", "as_of"]},
        "expires_at": "2099-01-01T00:00:00Z",
    }
    fields.update(overrides)
    built = GrantRecord.try_create(**fields)
    assert is_ok(built)
    return built.value


def _stores(*, grant: GrantRecord | None = None) -> AuthoritativeStores:
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
    resolved_grant = grant if grant is not None else _grant()
    instance = InstanceRecord(instance_id="inst:1", config_revision=4)
    return AuthoritativeStores(
        contributions={record.as_tuple(): record},
        descriptors={(descriptor.op_id, descriptor.version): descriptor},
        grants={resolved_grant.grant_id: resolved_grant},
        instances={(instance.instance_id, instance.config_revision): instance},
    )


def test_inspect_sha_did_not_wire_invocation_envelope() -> None:
    """Claiming InvocationEnvelope existed at 270e992 fails the story."""
    assert INVOCATION_ENVELOPE_INSPECT_SHAS == ("270e992",)
    assert INVOCATION_ENVELOPE_WIRED_AT_INSPECT_SHA is False
    assert INVOCATION_ENVELOPE_NEW_CT_MINTED is False
    assert INVOCATION_ENVELOPE_REFUSED_CT == "CT-52"
    assert INVOCATION_ENVELOPE_DTO_OWNER == "COMP-QMA-WIRE"
    assert INVOCATION_ENVELOPE_CONTRACT == "CT-40"
    assert INVOCATION_ENVELOPE_IS_AUTHORITY is False
    assert ENVELOPE_CRYPTO_GAP == "GAP-DESK-ENVELOPE-CRYPTO"
    assert ENVELOPE_CRYPTO_ALGORITHM_SELECTED is False
    assert SCHEMA_FILES[INVOCATION_ENVELOPE_SCHEMA_NAME] == INVOCATION_ENVELOPE_SCHEMA_FILE
    assert INVOCATION_ENVELOPE_SCHEMA == "qma.wire.invocation_envelope.v1"


def test_envelope_carries_cheap_veto_a3_field_catalogue() -> None:
    payload = _envelope_payload()
    parsed = parse_invocation_envelope(payload)
    assert is_ok(parsed)
    envelope = parsed.value
    dumped = dict(envelope.to_payload())
    for field in INVOCATION_ENVELOPE_REQUIRED_FIELDS:
        assert field in dumped
    assert set(INVOCATION_ENVELOPE_FIELDS) == set(INVOCATION_ENVELOPE_REQUIRED_FIELDS) | set(
        INVOCATION_ENVELOPE_OPTIONAL_FIELDS
    )
    assert dumped["caller_session_ref"] == "psess:caller"
    assert "callee_session_ref" not in dumped
    assert "parent_logical_invocation_id" not in dumped
    schema_ok = validate_invocation_envelope(dumped)
    assert is_ok(schema_ok)
    round_trip = parse_invocation_envelope(dumped)
    assert is_ok(round_trip)
    assert round_trip.value.to_payload() == envelope.to_payload()


def test_null_optional_fields_are_refused() -> None:
    payload = _envelope_payload(callee_session_ref=None)
    refused = parse_invocation_envelope(payload)
    assert is_refusal(refused)
    assert refused.context["field"] == "invocation_envelope"


def test_transport_never_bypasses_the_envelope() -> None:
    stores = _stores()
    executed: list[BoundInvocation] = []
    execute = _capture(executed)

    for transport_call in (
        lambda: public_call_in_process(None, _INPUT, stores, execute=execute),
        lambda: public_call_from_cli(None, _INPUT, stores, execute=execute),
        lambda: public_call_nested(None, _INPUT, stores, execute=execute),
    ):
        refused = transport_call()
        assert is_refusal(refused)
        assert isinstance(refused, InvocationEnvelopeRequired)
        assert refused.context["reason"] == "transport_must_carry_envelope"
    wire = WireEnvelope.try_create(
        v="1.0.0",
        type="start_mission",
        id="msg-1",
        producer_id="client-a",
        correlation_id="corr-1",
        scope_path=[{"kind": "desk", "id": "research"}],
        payload={"mission_ref": "m-1"},
    )
    assert is_ok(wire)
    missing_wire = public_call_from_wire(wire.value, stores, execute=execute)
    assert is_refusal(missing_wire)
    assert isinstance(missing_wire, InvocationEnvelopeRequired)
    assert missing_wire.context["transport"] == "wire"
    assert executed == []
    assert {member.value for member in PublicCallTransport} == PUBLIC_CALL_TRANSPORTS


def test_host_compares_stores_envelope_is_not_authority() -> None:
    stores = _stores()
    executed: list[BoundInvocation] = []
    execute = _capture(executed)

    bound = public_call_in_process(_envelope_payload(), _INPUT, stores, execute=execute)
    assert is_ok(bound)
    assert bound.value.is_authority is False
    assert INVOCATION_ENVELOPE_IS_AUTHORITY is False
    assert bound.value.grant.grant_id == "grant:1"
    assert bound.value.descriptor.op_id == "qmb.analysis.project"
    assert len(executed) == 1


def test_labeling_external_effect_as_read_is_mismatch_before_execute() -> None:
    stores = _stores()
    executed: list[BoundInvocation] = []
    execute = _capture(executed)

    payload = _envelope_payload(effect_class="external-egress")
    refused = public_call_in_process(payload, _INPUT, stores, execute=execute)
    assert is_refusal(refused)
    assert isinstance(refused, EnvelopeMismatch)
    assert refused.context["field"] == "effect_class"
    assert refused.context["code"] == "MISMATCH"
    assert refused.context["envelope_is_authority"] is False
    assert executed == []


def test_valid_grant_paired_with_another_instance_is_grant_mismatch() -> None:
    grant = _grant(instance_id="inst:other")
    stores = _stores(grant=grant)
    executed: list[BoundInvocation] = []
    execute = _capture(executed)

    refused = public_call_from_cli(_envelope_payload(), _INPUT, stores, execute=execute)
    assert is_refusal(refused)
    assert isinstance(refused, GrantMismatch)
    assert refused.context["code"] == "GRANT_MISMATCH"
    assert refused.context["field"] == "instance_id"
    assert executed == []


def test_stale_contribution_version_does_not_pick_another_package() -> None:
    stores = _stores()
    payload = _envelope_payload(
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "9.9.9"}
    )
    refused = public_call_in_process(payload, _INPUT, stores)
    assert is_refusal(refused)
    assert isinstance(refused, StaleObservation)
    assert refused.context["code"] == "STALE_OBSERVATION"
    assert refused.context["substituted"] is False


def test_ambiguous_instance_or_config_never_picks_latest() -> None:
    stores = _stores()
    latest_instance = public_call_in_process(
        _envelope_payload(instance_id="latest"),
        _INPUT,
        stores,
    )
    assert is_refusal(latest_instance)
    assert isinstance(latest_instance, AmbiguousResolution)
    assert latest_instance.context["never_latest"] is True
    assert latest_instance.context["field"] == "instance_id"

    latest_revision = public_call_in_process(
        _envelope_payload(config_revision="latest"),
        _INPUT,
        stores,
    )
    assert is_refusal(latest_revision)
    assert isinstance(latest_revision, AmbiguousResolution)
    assert latest_revision.context["field"] == "config_revision"
    assert "latest" in AMBIGUOUS_RESOLUTION_TOKENS

    extra = InstanceRecord(instance_id="inst:1", config_revision=99)
    grant = _grant(config_revision=3)
    richer = AuthoritativeStores(
        contributions=dict(stores.contributions),
        descriptors=dict(stores.descriptors),
        grants={grant.grant_id: grant},
        instances={
            ("inst:1", 4): InstanceRecord(instance_id="inst:1", config_revision=4),
            (extra.instance_id, extra.config_revision): extra,
        },
    )
    stale = public_call_in_process(
        _envelope_payload(config_revision=3),
        _INPUT,
        richer,
    )
    assert is_refusal(stale)
    assert isinstance(stale, StaleObservation)
    assert stale.context["never_latest"] is True
    assert stale.context["substituted"] is False


def test_input_hash_is_canonical_json_and_secrets_are_never_inlined() -> None:
    descriptor = _descriptor()
    left = compute_input_hash({"run_fp1": "run-1"}, descriptor=descriptor)
    right = compute_input_hash({"run_fp1": "run-1"}, descriptor=descriptor)
    assert is_ok(left) and is_ok(right)
    assert left.value == right.value
    assert left.value.startswith("fp1:sha256:")
    reordered = compute_input_hash({"run_fp1": "run-1", "as_of": "x"}, descriptor=descriptor)
    assert is_ok(reordered)
    secret = compute_input_hash({"run_fp1": "run-1", "password": "secret"}, descriptor=descriptor)
    assert is_refusal(secret)
    inline = public_call_in_process(
        _envelope_payload(),
        {"run_fp1": "run-1", "token": "abc"},
        _stores(),
    )
    assert is_refusal(inline)


def test_input_hash_mismatch_refuses_while_crypto_algorithm_stays_a_gap() -> None:
    assert ENVELOPE_CRYPTO_ALGORITHM_SELECTED is False
    assert ENVELOPE_CRYPTO_GAP == "GAP-DESK-ENVELOPE-CRYPTO"
    payload = _envelope_payload(input_hash="fp1:sha256:" + ("00" * 32))
    refused = public_call_in_process(payload, _INPUT, _stores())
    assert is_refusal(refused)
    assert isinstance(refused, EnvelopeMismatch)
    assert refused.context["field"] == "input_hash"
    assert refused.context["gap"] == ENVELOPE_CRYPTO_GAP
    assert refused.context["algorithm_selected"] is False
    signed = parse_invocation_envelope(_envelope_payload(signature_algorithm="ed25519"))
    assert is_refusal(signed)
    assert isinstance(signed, EnvelopeMismatch)
    assert signed.context["gap"] == ENVELOPE_CRYPTO_GAP


def test_wire_and_nested_transports_carry_the_envelope() -> None:
    stores = _stores()
    envelope = _envelope_payload()
    wire = WireEnvelope.try_create(
        v="1.0.0",
        type="start_mission",
        id="msg-1",
        producer_id="client-a",
        correlation_id="corr-1",
        scope_path=[{"kind": "desk", "id": "research"}],
        payload={"invocation_envelope": envelope, "input": _INPUT},
    )
    assert is_ok(wire)
    bound = public_call_from_wire(wire.value, stores)
    assert is_ok(bound)
    assert bound.value.transport is PublicCallTransport.WIRE

    child_id = derive_child_logical_invocation_id(
        parent_logical_invocation_id="inv:1",
        call_depth=1,
        child_op_id="qmb.analysis.project",
        child_canonical_input_hash=_hash(),
    )
    assert is_ok(child_id)
    nested_payload = _envelope_payload(
        logical_invocation_id=child_id.value,
        parent_logical_invocation_id="inv:1",
        call_depth=1,
    )
    nested = public_call_nested(nested_payload, _INPUT, stores)
    assert is_ok(nested)
    assert nested.value.envelope.call_depth == 1
    assert nested.value.envelope.parent_logical_invocation_id == "inv:1"
    assert nested.value.envelope.logical_invocation_id == child_id.value

    top_level_depth = public_call_in_process(
        _envelope_payload(call_depth=1, parent_logical_invocation_id="inv:1"),
        _INPUT,
        stores,
    )
    assert is_refusal(top_level_depth)


def test_sess_ref_is_not_a_product_session() -> None:
    refused = parse_invocation_envelope(_envelope_payload(caller_session_ref="sess:qma"))
    assert is_refusal(refused)
    assert refused.context["field"] == "caller_session_ref"


def test_try_create_round_trips_invocation_envelope() -> None:
    created = InvocationEnvelope.try_create(**_envelope_payload())
    assert is_ok(created)
    assert created.value.contribution.as_tuple() == ("analysis-backtest:qmb", "0.1.0")
