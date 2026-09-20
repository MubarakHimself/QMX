"""Reference usage — product_session.context is bound request context (55.1)."""

from __future__ import annotations

from qma.core.refusals import EnvelopeMismatch
from qma.daemon.sessions import (
    PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA,
    PRODUCT_SESSION_OCCUPANCY,
    PRODUCT_SESSION_OWNER,
    ProductSessionService,
    claim_product_session_at_inspect_sha,
)
from qmf.core import is_ok, is_refusal


def main() -> None:
    assert PRODUCT_SESSION_OWNER == "COMP-QMA-DAEMON"
    assert PRODUCT_SESSION_OCCUPANCY == "none"
    assert PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA is False
    claimed = claim_product_session_at_inspect_sha(True)
    assert is_refusal(claimed)
    print("product_session did not exist at inspect SHA 270e992")

    service = ProductSessionService()
    minted = service.mint(
        product_session_id="psess:desk-1",
        profile="authoring",
        principal="operator",
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "0.1.0"},
        instance_id="inst:1",
        config_revision=4,
        as_of="2026-09-20T00:00:00Z",
        granted_ops=("grant:inspect",),
    )
    assert is_ok(minted)
    context = minted.value.context
    assert context.occupancy == "none"
    assert context.account_scope is None
    assert context.principal == "operator"

    matched = service.bind_public_call(
        "psess:desk-1",
        {
            "principal": "operator",
            "occupancy": "none",
            "contribution": {
                "qualified_id": "analysis-backtest:qmb",
                "package_version": "0.1.0",
            },
            "instance_id": "inst:1",
            "config_revision": 4,
            "as_of": "2026-09-20T00:00:00Z",
        },
    )
    assert is_ok(matched)
    stale = service.bind_public_call(
        "psess:desk-1",
        {
            "principal": "operator",
            "occupancy": "none",
            "contribution": {
                "qualified_id": "analysis-backtest:qmb",
                "package_version": "0.1.0",
            },
            "instance_id": "inst:1",
            "config_revision": 99,
            "as_of": "2026-09-20T00:00:00Z",
        },
    )
    assert is_refusal(stale)
    assert isinstance(stale, EnvelopeMismatch)
    print("public call matches context; stale config_revision is typed mismatch")


if __name__ == "__main__":
    main()
