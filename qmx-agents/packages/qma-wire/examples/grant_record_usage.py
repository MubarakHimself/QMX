"""Reference usage — GrantRecord is immutable; revocation is append-only (Story 54.4)."""

from __future__ import annotations

from qma.core.refusals import GrantInactive, GrantWidenRefused, ManifestIsNotGrant
from qma.wire import (
    GRANT_RECORD_CONTRACT,
    GRANT_RECORD_FORBIDDEN_FIELDS,
    GRANT_RECORD_NEW_CT_MINTED,
    HOST_GRANTS,
    MANIFESTS_GRANT,
    PRODUCT_SESSION_ROWS_MINTED,
    HostGrantLedger,
    parse_granted_ops,
)
from qmf.core import is_ok, is_refusal

_NOW = "2026-09-20T00:00:00Z"
_EXPIRES = "2026-12-31T00:00:00Z"


def main() -> None:
    assert GRANT_RECORD_CONTRACT == "CT-40"
    assert GRANT_RECORD_NEW_CT_MINTED is False
    assert "revoked_at" in GRANT_RECORD_FORBIDDEN_FIELDS
    assert MANIFESTS_GRANT is False
    assert HOST_GRANTS is True
    assert PRODUCT_SESSION_ROWS_MINTED is False

    ledger = HostGrantLedger()
    manifest = ledger.mint(
        issuer="manifest",
        principal="operator",
        audience="psess:session",
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "0.1.0"},
        instance_id="inst:1",
        config_revision=4,
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1"]},
        expires_at=_EXPIRES,
        grant_id="grant:1",
    )
    assert is_refusal(manifest)
    assert isinstance(manifest, ManifestIsNotGrant)
    print("manifests request; host grants")

    minted = ledger.mint(
        issuer="host",
        principal="operator",
        audience="psess:session",
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "0.1.0"},
        instance_id="inst:1",
        config_revision=4,
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1"]},
        expires_at=_EXPIRES,
        grant_id="grant:1",
    )
    assert is_ok(minted)
    grant = minted.value
    before = grant.canonical_bytes()
    assert is_ok(before)
    ledger.accept(grant_id="grant:1", logical_invocation_id="inv:1", now=_NOW)
    ledger.revoke(
        grant_id="grant:1",
        principal="operator",
        reason="session-ended",
        revoked_at=_NOW,
    )
    after = grant.canonical_bytes()
    assert is_ok(after)
    assert after.value == before.value
    print("revocation is append-only; minted bytes did not change")

    finish = ledger.evaluate(
        grant_id="grant:1",
        moment="retry",
        now=_NOW,
        logical_invocation_id="inv:1",
    )
    assert is_ok(finish)
    refused = ledger.evaluate(
        grant_id="grant:1",
        moment="dispatch",
        now=_NOW,
        logical_invocation_id="inv:new",
    )
    assert is_refusal(refused)
    assert isinstance(refused, GrantInactive)
    print("already-accepted work may finish; new dispatch is refused")

    widen = ledger.apply_upgrade("grant:1", package_version="0.2.0")
    assert isinstance(widen, GrantWidenRefused)
    regranted = ledger.regrant(
        "grant:1",
        context_revision=1,
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "0.2.0"},
        grant_id="grant:2",
    )
    assert is_ok(regranted)
    assert regranted.value.context_revision == 1
    ops = parse_granted_ops(["grant:1", "grant:2"])
    assert is_ok(ops)
    assert ops.value == ("grant:1", "grant:2")
    print("re-grant bumps context_revision; granted_ops are grant_ids")


if __name__ == "__main__":
    main()
