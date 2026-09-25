"""Reference usage — granted_ops are GrantRecords; mismatch/revoke refuse (55.2)."""

from __future__ import annotations

from qma.core.refusals import GrantInactive, GrantMismatch, GrantWidenRefused, ManifestIsNotGrant
from qma.daemon.sessions import (
    GRANT_SIXTH_STORE_MINTED,
    TOOL_REGISTRY_REWRITTEN,
    ProductSessionService,
)
from qmf.core import is_ok, is_refusal

_NOW = "2026-09-20T00:00:00Z"
_EXPIRES = "2026-12-31T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}


def main() -> None:
    assert GRANT_SIXTH_STORE_MINTED is False
    assert TOOL_REGISTRY_REWRITTEN is False
    service = ProductSessionService()
    minted = service.mint(
        product_session_id="psess:desk-1",
        profile="authoring",
        principal="operator",
        contribution=dict(_CONTRIBUTION),
        instance_id="inst:1",
        config_revision=4,
        as_of="2026-09-20T00:00:00Z",
    )
    assert is_ok(minted)
    manifest = service.host_grant(
        "psess:desk-1",
        issuer="manifest",
        grant_id="grant:1",
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1"]},
        expires_at=_EXPIRES,
    )
    assert is_refusal(manifest)
    assert isinstance(manifest, ManifestIsNotGrant)
    print("manifests request; host grants")

    granted = service.host_grant(
        "psess:desk-1",
        grant_id="grant:1",
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1"]},
        expires_at=_EXPIRES,
    )
    assert is_ok(granted)
    assert minted.value.granted_ops == ()
    row = service.get("psess:desk-1")
    assert is_ok(row)
    assert row.value.granted_ops == ("grant:1",)
    resolved = service.resolve_grant("psess:desk-1", "grant:1")
    assert is_ok(resolved)

    mismatched = service.dispatch_public_call(
        "psess:desk-1",
        transport="in-process",
        envelope={
            "logical_invocation_id": "inv:1",
            "attempt_id": 1,
            "op_id": "qmb.analysis.other",
            "op_version": 1,
            "contribution": dict(_CONTRIBUTION),
            "instance_id": "inst:1",
            "config_revision": 4,
            "grant_id": "grant:1",
            "effect_class": "read",
            "idempotency_key": "idem:1",
            "reconcile_policy": "query-then-decide",
            "input_hash": "fp1:sha256:" + ("a" * 64),
            "call_depth": 0,
            "caller_kind": "user",
        },
        payload={"run_fp1": "run-1"},
        now=_NOW,
    )
    assert is_refusal(mismatched)
    assert isinstance(mismatched, GrantMismatch)
    print("envelope op mismatch is GRANT_MISMATCH before execution")

    widened = service.apply_upgrade("psess:desk-1", "grant:1", instance_id="inst:2")
    assert isinstance(widened, GrantWidenRefused)

    assert is_ok(
        service.accept_work(
            "psess:desk-1",
            grant_id="grant:1",
            logical_invocation_id="inv:ok",
            now=_NOW,
        )
    )
    assert is_ok(
        service.revoke_grant(
            "psess:desk-1",
            grant_id="grant:1",
            principal="operator",
            reason="session-ended",
            revoked_at=_NOW,
        )
    )
    refused = service.dispatch_public_call(
        "psess:desk-1",
        transport="cli",
        envelope={
            "logical_invocation_id": "inv:new",
            "attempt_id": 1,
            "op_id": "qmb.analysis.project",
            "op_version": 1,
            "contribution": dict(_CONTRIBUTION),
            "instance_id": "inst:1",
            "config_revision": 4,
            "grant_id": "grant:1",
            "effect_class": "read",
            "idempotency_key": "idem:new",
            "reconcile_policy": "query-then-decide",
            "input_hash": "fp1:sha256:" + ("a" * 64),
            "call_depth": 0,
            "caller_kind": "user",
        },
        payload={"run_fp1": "run-1"},
        now=_NOW,
    )
    assert is_refusal(refused)
    assert isinstance(refused, GrantInactive)
    print("already-accepted work may finish; new dispatch is refused")


if __name__ == "__main__":
    main()
