"""Reference usage — InvocationEnvelope is bound request context (Story 54.2)."""

from __future__ import annotations

from qma.core.operations import public_operation_descriptors
from qma.core.refusals import EnvelopeMismatch, InvocationEnvelopeRequired
from qma.wire import (
    ENVELOPE_CRYPTO_ALGORITHM_SELECTED,
    ENVELOPE_CRYPTO_GAP,
    INVOCATION_ENVELOPE_CONTRACT,
    INVOCATION_ENVELOPE_IS_AUTHORITY,
    INVOCATION_ENVELOPE_NEW_CT_MINTED,
    INVOCATION_ENVELOPE_WIRED_AT_INSPECT_SHA,
    AuthoritativeStores,
    ContributionRecord,
    GrantRecord,
    InstanceRecord,
    compute_input_hash,
    public_call_from_wire,
    public_call_in_process,
)
from qmf.core import is_ok, is_refusal

_INPUT = {"run_fp1": "run-1"}


def main() -> None:
    assert INVOCATION_ENVELOPE_CONTRACT == "CT-40"
    assert INVOCATION_ENVELOPE_NEW_CT_MINTED is False
    assert INVOCATION_ENVELOPE_WIRED_AT_INSPECT_SHA is False
    assert INVOCATION_ENVELOPE_IS_AUTHORITY is False
    assert ENVELOPE_CRYPTO_ALGORITHM_SELECTED is False
    assert ENVELOPE_CRYPTO_GAP == "GAP-DESK-ENVELOPE-CRYPTO"

    descriptor = next(
        item for item in public_operation_descriptors() if item.op_id == "qmb.analysis.project"
    )
    hashed = compute_input_hash(_INPUT, descriptor=descriptor)
    assert is_ok(hashed)
    envelope = {
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
        "input_hash": hashed.value,
        "call_depth": 0,
        "caller_kind": "user",
    }
    grant = GrantRecord.try_create(
        grant_id="grant:1",
        principal="operator",
        audience="psess:caller",
        contribution=envelope["contribution"],
        instance_id="inst:1",
        config_revision=4,
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1", "as_of"]},
        expires_at="2099-01-01T00:00:00Z",
    )
    assert is_ok(grant)
    contribution = ContributionRecord(
        qualified_id="analysis-backtest:qmb",
        package_version="0.1.0",
        availability="enabled",
    )
    stores = AuthoritativeStores(
        contributions={contribution.as_tuple(): contribution},
        descriptors={(descriptor.op_id, descriptor.version): descriptor},
        grants={grant.value.grant_id: grant.value},
        instances={("inst:1", 4): InstanceRecord("inst:1", 4)},
    )
    bound = public_call_in_process(envelope, _INPUT, stores)
    assert is_ok(bound)
    assert bound.value.is_authority is False
    print("host compared bound fields; envelope is not authority")

    missing = public_call_from_wire({"payload": {"mission_ref": "m-1"}}, stores)
    assert is_refusal(missing)
    assert isinstance(missing, InvocationEnvelopeRequired)
    print("wire transport never bypasses InvocationEnvelope")

    relabeled = dict(envelope)
    relabeled["effect_class"] = "external-egress"
    mismatch = public_call_in_process(relabeled, _INPUT, stores)
    assert is_refusal(mismatch)
    assert isinstance(mismatch, EnvelopeMismatch)
    print("effect_class mismatch refused before execution")


if __name__ == "__main__":
    main()
