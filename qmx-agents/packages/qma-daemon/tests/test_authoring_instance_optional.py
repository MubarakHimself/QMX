"""Story 60.2 — authoring may omit app_instance_id; invoke needs exactly one instance_id."""

from __future__ import annotations

from qma.core.operations import OperationDescriptor, public_operation_descriptors
from qma.core.refusals import AmbiguousResolution, EnvelopeMismatch, GrantMismatch
from qma.daemon.sessions import (
    ADR_0024_DECISION_REWRITTEN,
    APP_INSTANCE_ID_OPTIONAL_AT_INSPECT_SHA,
    APP_USE_APP_INSTANCE_REQUIRED,
    AUTHORING_APP_INSTANCE_OPTIONAL,
    AUTHORING_INSTANCE_OPTIONAL_INSPECT_SHA,
    DEC_0421_SUPERSEDED_BY,
    DEC_0463_FOLLOWS_DEC_0421,
    ENVELOPE_INSTANCE_ID_REMAINS_REQUIRED,
    HOME_IS_AUTHORING_WITHOUT_INSTANCE,
    INSTANCE_ID_KIND,
    INSTANCE_ID_KIND_EXISTED_AT_INSPECT_SHA,
    PARENT_AD8_SELECTED_REF_KINDS,
    PRODUCT_SESSION_TYPES_EXISTED_AT_INSPECT_SHA_34C148B,
    SELECTED_REF_KINDS,
    THIRD_PRODUCT_SESSION_PROFILE_MINTED,
    ProductSession,
    ProductSessionProfile,
    ProductSessionService,
    claim_instance_id_selected_ref_kind_at_inspect_sha,
    claim_optional_authoring_instance_at_inspect_sha,
    invoke_instance_id_from_selected_refs,
    parse_selected_refs,
)
from qma.daemon.sessions.product_session import parse_product_session
from qma.wire.invocation_envelope import (
    INVOCATION_ENVELOPE_REQUIRED_FIELDS,
    ContributionRecord,
    InstanceRecord,
    PublicCallTransport,
    compute_input_hash,
)
from qmf.core import is_ok, is_refusal

_AS_OF = "2026-09-20T00:00:00Z"
_NOW = "2026-09-20T00:00:00Z"
_EXPIRES = "2026-12-31T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
_INPUT = {"run_fp1": "run-1"}


def _descriptor() -> OperationDescriptor:
    for item in public_operation_descriptors():
        if item.op_id == "qmb.analysis.project" and item.version == 1:
            return item
    raise AssertionError("qmb.analysis.project v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _home_kwargs(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "product_session_id": "psess:home",
        "profile": "authoring",
        "principal": "operator",
        "contribution": dict(_CONTRIBUTION),
        "instance_id": None,
        "config_revision": 4,
        "as_of": _AS_OF,
        "granted_ops": (),
        "selected_refs": (),
        "scope_path": [{"kind": "desk", "id": "research"}],
    }
    body.update(overrides)
    return body


def _envelope(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "logical_invocation_id": "inv:1",
        "attempt_id": 1,
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "contribution": dict(_CONTRIBUTION),
        "instance_id": "inst:1",
        "config_revision": 4,
        "grant_id": "grant:1",
        "effect_class": "read",
        "idempotency_key": "idem:1",
        "reconcile_policy": "query-then-decide",
        "input_hash": _hash(),
        "call_depth": 0,
        "caller_kind": "user",
        "caller_session_ref": "psess:home",
    }
    payload.update(overrides)
    return payload


def _stores(
    *, instance_id: str = "inst:1"
) -> tuple[
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
    instance = InstanceRecord(instance_id=instance_id, config_revision=4)
    return (
        {contribution.as_tuple(): contribution},
        {(descriptor.op_id, descriptor.version): descriptor},
        {(instance.instance_id, instance.config_revision): instance},
    )


def test_inspect_sha_honesty_optional_authoring_instance_and_kind() -> None:
    assert PRODUCT_SESSION_TYPES_EXISTED_AT_INSPECT_SHA_34C148B is True
    assert APP_INSTANCE_ID_OPTIONAL_AT_INSPECT_SHA is False
    assert INSTANCE_ID_KIND_EXISTED_AT_INSPECT_SHA is False
    assert AUTHORING_INSTANCE_OPTIONAL_INSPECT_SHA == "34c148b"
    assert AUTHORING_APP_INSTANCE_OPTIONAL is True
    assert APP_USE_APP_INSTANCE_REQUIRED is True
    assert HOME_IS_AUTHORING_WITHOUT_INSTANCE is True
    assert THIRD_PRODUCT_SESSION_PROFILE_MINTED is False
    assert ENVELOPE_INSTANCE_ID_REMAINS_REQUIRED is True
    assert DEC_0463_FOLLOWS_DEC_0421 == "DEC-0463"
    assert DEC_0421_SUPERSEDED_BY is None
    assert ADR_0024_DECISION_REWRITTEN is False
    assert "instance_id" in INVOCATION_ENVELOPE_REQUIRED_FIELDS
    fields = ProductSession.__dataclass_fields__
    assert "app_instance_id" in fields
    assert "instance_id" in SELECTED_REF_KINDS
    assert PARENT_AD8_SELECTED_REF_KINDS <= SELECTED_REF_KINDS
    assert INSTANCE_ID_KIND not in PARENT_AD8_SELECTED_REF_KINDS
    profiles = {item.value for item in ProductSessionProfile}
    assert profiles == {"authoring", "app-use"}
    claimed_instance = claim_optional_authoring_instance_at_inspect_sha(True)
    assert is_refusal(claimed_instance)
    assert claimed_instance.context["existed_at_inspect_sha"] is False
    assert claimed_instance.context["types_existed"] is True
    claimed_kind = claim_instance_id_selected_ref_kind_at_inspect_sha(True)
    assert is_refusal(claimed_kind)
    assert is_ok(claim_optional_authoring_instance_at_inspect_sha(False))
    assert is_ok(claim_instance_id_selected_ref_kind_at_inspect_sha(False))


def test_authoring_may_omit_app_instance_id_home_is_authoring() -> None:
    service = ProductSessionService()
    minted = service.mint(**_home_kwargs())
    assert is_ok(minted)
    row = minted.value
    assert row.profile is ProductSessionProfile.AUTHORING
    assert row.app_instance_id is None
    assert row.context.instance_id is None
    payload = dict(row.to_payload())
    assert "app_instance_id" not in payload
    context_payload = payload["context"]
    assert isinstance(context_payload, dict)
    assert "instance_id" not in context_payload
    reparsed = parse_product_session(payload)
    assert is_ok(reparsed)
    assert reparsed.value.app_instance_id is None
    assert reparsed.value.context.instance_id is None
    loaded = service.get("psess:home")
    assert is_ok(loaded)
    assert loaded.value.app_instance_id is None
    third = service.mint(**_home_kwargs(product_session_id="psess:other", profile="home"))
    assert is_refusal(third)


def test_app_use_still_requires_app_instance_id() -> None:
    service = ProductSessionService()
    missing = service.mint(**_home_kwargs(product_session_id="psess:app", profile="app-use"))
    assert is_refusal(missing)
    assert missing.context["field"] == "app_instance_id"
    bound = service.mint(
        **_home_kwargs(
            product_session_id="psess:app",
            profile="app-use",
            instance_id="inst:1",
        )
    )
    assert is_ok(bound)
    assert bound.value.app_instance_id == "inst:1"
    assert bound.value.profile is ProductSessionProfile.APP_USE


def test_selected_refs_gain_instance_id_kind() -> None:
    parsed = parse_selected_refs(
        [
            {"kind": "instance_id", "id": "inst:1"},
            {"kind": "artifact", "id": "fp1:sha256:aa"},
        ]
    )
    assert is_ok(parsed)
    assert parsed.value[0].kind == "instance_id"
    service = ProductSessionService()
    minted = service.mint(**_home_kwargs(selected_refs=[{"kind": "instance_id", "id": "inst:1"}]))
    assert is_ok(minted)
    assert minted.value.selected_refs[0].kind == "instance_id"
    layout = service.mint(
        **_home_kwargs(
            product_session_id="psess:layout",
            selected_refs=[{"kind": "instance_id", "id": "inst:1", "layout": {"x": 1}}],
        )
    )
    assert is_refusal(layout)
    taken = invoke_instance_id_from_selected_refs([{"kind": "instance_id", "id": "inst:1"}])
    assert is_ok(taken)
    assert taken.value == "inst:1"


def test_exactly_one_instance_id_ref_binds_callee_grants() -> None:
    service = ProductSessionService()
    minted = service.mint(**_home_kwargs(selected_refs=[{"kind": "instance_id", "id": "inst:1"}]))
    assert is_ok(minted)
    granted = service.host_grant(
        "psess:home",
        grant_id="grant:1",
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1", "as_of"]},
        expires_at=_EXPIRES,
        instance_id="inst:1",
    )
    assert is_ok(granted)
    assert granted.value.instance_id == "inst:1"
    contributions, descriptors, instances = _stores()
    executed: list[object] = []

    def _execute(bound: object) -> None:
        executed.append(bound)

    matched = service.dispatch_public_call(
        "psess:home",
        transport=PublicCallTransport.IN_PROCESS,
        envelope=_envelope(),
        payload=_INPUT,
        now=_NOW,
        selected_refs=[{"kind": "instance_id", "id": "inst:1"}],
        contributions=contributions,
        descriptors=descriptors,
        instances=instances,
        execute=_execute,
    )
    assert is_ok(matched)
    assert matched.value.envelope.instance_id == "inst:1"
    assert matched.value.grant.instance_id == "inst:1"
    assert executed != []

    other = service.host_grant(
        "psess:home",
        grant_id="grant:other",
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1", "as_of"]},
        expires_at=_EXPIRES,
        instance_id="inst:2",
    )
    assert is_ok(other)
    wrong = service.dispatch_public_call(
        "psess:home",
        transport=PublicCallTransport.CLI,
        envelope=_envelope(grant_id="grant:other", idempotency_key="idem:other"),
        payload=_INPUT,
        now=_NOW,
        selected_refs=[{"kind": "instance_id", "id": "inst:1"}],
    )
    assert is_refusal(wrong)
    assert isinstance(wrong, GrantMismatch)
    assert wrong.context["field"] == "instance_id"


def test_zero_or_many_instance_id_refs_are_ambiguous() -> None:
    service = ProductSessionService()
    minted = service.mint(**_home_kwargs())
    assert is_ok(minted)
    assert is_ok(
        service.host_grant(
            "psess:home",
            grant_id="grant:1",
            op_id="qmb.analysis.project",
            op_version=1,
            effect_class="read",
            parameter_ceiling={"allow_keys": ["run_fp1", "as_of"]},
            expires_at=_EXPIRES,
            instance_id="inst:1",
        )
    )
    zero = service.dispatch_public_call(
        "psess:home",
        transport=PublicCallTransport.CLI,
        envelope=_envelope(idempotency_key="idem:zero"),
        payload=_INPUT,
        now=_NOW,
        selected_refs=(),
    )
    assert is_refusal(zero)
    assert isinstance(zero, AmbiguousResolution)
    assert zero.context["code"] == "INVALID_INPUT"
    assert "ambiguous instance" in str(zero.context["reason"])
    assert zero.context["resolved_to_latest"] is False
    assert zero.context["resolved_to_first"] is False
    assert zero.context["resolved_to_all"] is False
    assert zero.context["never_latest"] is True
    assert zero.context["count"] == 0

    many = service.dispatch_public_call(
        "psess:home",
        transport=PublicCallTransport.CLI,
        envelope=_envelope(idempotency_key="idem:many"),
        payload=_INPUT,
        now=_NOW,
        selected_refs=[
            {"kind": "instance_id", "id": "inst:1"},
            {"kind": "instance_id", "id": "inst:2"},
        ],
    )
    assert is_refusal(many)
    assert isinstance(many, AmbiguousResolution)
    assert many.context["count"] == 2
    assert many.context["resolved_to_first"] is False
    assert many.context["resolved_to_all"] is False

    latest = invoke_instance_id_from_selected_refs([{"kind": "instance_id", "id": "latest"}])
    assert is_refusal(latest)
    assert isinstance(latest, AmbiguousResolution)

    missing_envelope = dict(_envelope())
    missing_envelope.pop("instance_id")
    omitted = service.dispatch_public_call(
        "psess:home",
        transport=PublicCallTransport.CLI,
        envelope=missing_envelope,
        payload=_INPUT,
        now=_NOW,
        selected_refs=[{"kind": "instance_id", "id": "inst:1"}],
    )
    assert is_refusal(omitted)
    mismatch = service.dispatch_public_call(
        "psess:home",
        transport=PublicCallTransport.CLI,
        envelope=_envelope(instance_id="inst:2", idempotency_key="idem:mismatch"),
        payload=_INPUT,
        now=_NOW,
        selected_refs=[{"kind": "instance_id", "id": "inst:1"}],
    )
    assert is_refusal(mismatch)
    assert isinstance(mismatch, EnvelopeMismatch)
    assert mismatch.context["field"] == "instance_id"
