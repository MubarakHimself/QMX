"""Reference usage — app-use mints; authoring+operator applies; v1 stays (58.4)."""

from __future__ import annotations

from qma.daemon import ChangeRequestFixture, ProductSessionService
from qma.daemon.staging import CHANGE_REQUEST_STAGING_KIND
from qmf.core import is_ok, is_refusal

_AS_OF = "2026-09-20T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
_HASH_A = "fp1:sha256:" + "aa" * 32
_SOURCE = "fp1:sha256:" + "11" * 32
_TARGET = "fp1:sha256:" + "22" * 32


def main() -> None:
    sessions = ProductSessionService()
    minted = sessions.mint(
        product_session_id="psess:app-use-1",
        profile="app-use",
        principal="operator",
        contribution=dict(_CONTRIBUTION),
        instance_id="inst:1",
        config_revision=4,
        as_of=_AS_OF,
        granted_ops=("grant:inspect",),
    )
    assert is_ok(minted)
    fixture = ChangeRequestFixture(sessions=sessions)
    v1 = fixture.install_v1(
        instance_id="inst:1",
        package_id="sector-intel",
        version="1.0.0",
        package_source_hash=_SOURCE,
        config_revision=4,
        granted_ops=("grant:inspect",),
        running_jobs=("job:run-1",),
        live_hashes=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
    )
    assert is_ok(v1)
    request = fixture.mint(
        from_session="psess:app-use-1",
        change_request_id="cr:filter-1",
        targets=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
        patch={"kind": "filter_add", "path": "industry.known_at"},
    )
    assert is_ok(request)
    assert request.value.to_payload()["type"] == CHANGE_REQUEST_STAGING_KIND
    after_mint = fixture.v1_snapshot()
    assert is_ok(after_mint)
    assert dict(after_mint.value.to_payload()) == dict(v1.value.to_payload())
    assert is_refusal(fixture.write_package_source(from_session="psess:app-use-1"))
    assert is_refusal(fixture.promote())
    authoring = fixture.open_authoring_handoff(request.value)
    assert is_ok(authoring)
    validation = fixture.validate(
        change_request_id="cr:filter-1",
        authoring_session=authoring.value.product_session_id,
        validated_at="2026-09-20T13:10:00Z",
    )
    assert is_ok(validation)
    assert validation.value.verdict == "valid"
    applied = fixture.apply(
        change_request_id="cr:filter-1",
        authoring_session=authoring.value.product_session_id,
        operator_principal="operator",
        applied_at="2026-09-20T13:12:00Z",
    )
    assert is_ok(applied)
    after_apply = fixture.v1_snapshot()
    assert is_ok(after_apply)
    assert dict(after_apply.value.to_payload()) == dict(v1.value.to_payload())
    print("app-use minted; authoring+operator applied; v1 instance stayed")


if __name__ == "__main__":
    main()
