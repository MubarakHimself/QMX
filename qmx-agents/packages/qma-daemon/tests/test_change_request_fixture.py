"""Story 58.4 — app-use change-request fixture; v1 stays; app-use never applies."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path
from typing import cast

from qma.core.ports.refinement import STAGING_STORE_RECORD_TYPE
from qma.core.refusals import GrantWidenRefused, OperatorPrincipalRequired
from qma.daemon import ChangeRequest, ChangeRequestFixture, ProductSessionService
from qma.daemon.sessions import (
    PRODUCT_SESSION_TAB_WRITES,
    RECONNECT_KIND_QUERY,
    ProductSessionProfile,
)
from qma.daemon.staging import (
    CHANGE_REQUEST_HASH_FIELDS,
    CHANGE_REQUEST_SIXTH_STORE_MINTED,
    CHANGE_REQUEST_STAGING_KIND,
    CHANGE_VALIDATION_VERDICTS,
    hash_change_request,
)
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import Result

_DAEMON_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon"
_SRC = _DAEMON_SRC / "staging" / "change_request.py"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "change_request_fixture_usage.py"

_AS_OF = "2026-09-20T00:00:00Z"
_AT = "2026-09-20T13:10:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
_HASH_A = "fp1:sha256:" + "aa" * 32
_HASH_B = "fp1:sha256:" + "bb" * 32
_SOURCE = "fp1:sha256:" + "11" * 32
_TARGET = "fp1:sha256:" + "22" * 32


def _ok[T](result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _app_use_kwargs(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "product_session_id": "psess:app-use-1",
        "profile": "app-use",
        "principal": "operator",
        "contribution": dict(_CONTRIBUTION),
        "instance_id": "inst:1",
        "config_revision": 4,
        "as_of": _AS_OF,
        "granted_ops": ("grant:inspect",),
        "selected_refs": [{"kind": "run", "id": _TARGET}],
        "scope_path": [{"kind": "desk", "id": "research"}],
    }
    body.update(overrides)
    return body


def _world() -> tuple[ProductSessionService, ChangeRequestFixture]:
    sessions = ProductSessionService()
    _ok(sessions.mint(**_app_use_kwargs()))
    fixture = ChangeRequestFixture(sessions=sessions)
    _ok(
        fixture.install_v1(
            instance_id="inst:1",
            package_id="sector-intel",
            version="1.0.0",
            package_source_hash=_SOURCE,
            config_revision=4,
            granted_ops=("grant:inspect",),
            running_jobs=("job:run-1",),
            live_hashes=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
        )
    )
    return sessions, fixture


def _mint(fixture: ChangeRequestFixture, **overrides: object) -> Result[ChangeRequest]:
    body: dict[str, object] = {
        "from_session": "psess:app-use-1",
        "change_request_id": "cr:filter-1",
        "targets": [{"target_ref": _TARGET, "base_hash": _HASH_A}],
        "patch": {"kind": "filter_add", "path": "industry.known_at"},
        "copied_private_memory": False,
    }
    body.update(overrides)
    return fixture.mint(**body)


def test_three_record_path_leaves_v1_untouched() -> None:
    assert CHANGE_REQUEST_STAGING_KIND == "change_request"
    assert CHANGE_REQUEST_STAGING_KIND != STAGING_STORE_RECORD_TYPE
    assert CHANGE_REQUEST_SIXTH_STORE_MINTED is False
    assert CHANGE_VALIDATION_VERDICTS == ("conflict", "rebase-required", "valid")
    assert CHANGE_REQUEST_HASH_FIELDS == (
        "change_request_id",
        "from_session",
        "source_instance_id",
        "source_config_revision",
        "context_revision",
        "app_instance",
        "targets",
        "patch",
        "copied_private_memory",
    )
    _sessions, fixture = _world()
    before = dict(_ok(fixture.v1_snapshot()).to_payload())
    request = _ok(_mint(fixture))
    payload = dict(request.to_payload())
    assert payload["type"] == CHANGE_REQUEST_STAGING_KIND
    assert payload["from_session"] == "psess:app-use-1"
    assert payload["source_instance_id"] == "inst:1"
    assert payload["source_config_revision"] == 4
    assert "verdict" not in payload
    assert "outcome" not in payload
    hashed = _ok(hash_change_request(request.hash_preimage()))
    assert hashed == request.request_hash
    after_mint = dict(_ok(fixture.v1_snapshot()).to_payload())
    assert after_mint == before
    assert after_mint["version"] == "1.0.0"
    assert after_mint["granted_ops"] == ["grant:inspect"]
    assert after_mint["running_jobs"] == ["job:run-1"]
    assert after_mint["package_source_hash"] == _SOURCE

    authoring = _ok(fixture.open_authoring_handoff(request))
    assert authoring.profile is ProductSessionProfile.AUTHORING
    assert authoring.app_instance_id != "inst:1"
    refs = [dict(item.to_payload()) for item in authoring.selected_refs]
    assert refs == [{"id": _TARGET, "kind": "artifact"}]
    assert "transcript" not in dict(authoring.to_payload())

    validation = _ok(
        fixture.validate(
            change_request_id=request.change_request_id,
            authoring_session=authoring.product_session_id,
            validated_at=_AT,
        )
    )
    assert validation.verdict == "valid"
    assert validation.validator_principal == "authoring"
    assert validation.request_hash == request.request_hash
    assert _ok(fixture.request_bytes_unchanged(request.change_request_id)) is True

    applied = _ok(
        fixture.apply(
            change_request_id=request.change_request_id,
            authoring_session=authoring.product_session_id,
            operator_principal="operator",
            applied_at="2026-09-20T13:12:00Z",
        )
    )
    assert applied.outcome == "applied"
    assert applied.authoring_principal == "authoring"
    assert applied.operator_principal == "operator"
    assert applied.applied_base_hashes == (_HASH_A,)
    assert applied.request_hash == request.request_hash
    after_apply = dict(_ok(fixture.v1_snapshot()).to_payload())
    assert after_apply == before
    assert len(fixture.applies()) == 1
    assert fixture.distinct_from_refinement_proposal is True
    assert fixture.sixth_store_minted is False


def test_hash_excludes_validation_and_apply_evidence() -> None:
    _sessions, fixture = _world()
    request = _ok(_mint(fixture))
    polluted = dict(request.hash_preimage())
    polluted["verdict"] = "valid"
    refused = hash_change_request(polluted)
    assert is_refusal(refused)
    assert refused.context["field"] == "request_hash"
    mint_with_verdict = _mint(fixture, change_request_id="cr:filter-2", verdict="valid")
    assert is_refusal(mint_with_verdict)
    mint_with_apply = _mint(fixture, change_request_id="cr:filter-3", outcome="applied")
    assert is_refusal(mint_with_apply)


def test_app_use_cannot_apply_write_source_or_widen() -> None:
    sessions, fixture = _world()
    request = _ok(_mint(fixture))
    authoring = _ok(fixture.open_authoring_handoff(request))
    _ok(
        fixture.validate(
            change_request_id=request.change_request_id,
            authoring_session=authoring.product_session_id,
            validated_at=_AT,
        )
    )
    from_app_use = fixture.apply(
        change_request_id=request.change_request_id,
        authoring_session="psess:app-use-1",
        operator_principal="operator",
        applied_at=_AT,
    )
    assert is_refusal(from_app_use)
    assert from_app_use.context["branch"] == "A"
    assert from_app_use.context["applies"] is False

    source = fixture.write_package_source(from_session="psess:app-use-1")
    assert is_refusal(source)
    assert source.context["writes_package_source"] is False
    assert source.context["branch"] == "A"

    package_patch = _mint(
        fixture,
        change_request_id="cr:src-1",
        patch={"kind": "package_source", "path": "src/app.py"},
    )
    assert is_refusal(package_patch)
    assert package_patch.context["branch"] == "A"

    install_patch = _mint(
        fixture,
        change_request_id="cr:install-1",
        patch={"kind": "install_code", "path": "pkg"},
    )
    assert is_refusal(install_patch)

    widen = fixture.widen_grants(from_session="psess:app-use-1", grant_id="grant:live")
    assert is_refusal(widen)
    assert GrantWidenRefused.matches(widen)
    assert widen.context["branch"] == "B"

    widen_patch = _mint(
        fixture,
        change_request_id="cr:grant-1",
        patch={"kind": "grant_widen", "path": "granted_ops", "grant_id": "grant:live"},
    )
    assert is_refusal(widen_patch)
    assert GrantWidenRefused.matches(widen_patch)

    retarget = fixture.retarget_account(from_session="psess:app-use-1", account_scope="acct:other")
    assert is_refusal(retarget)
    assert GrantWidenRefused.matches(retarget)

    instance = fixture.retarget_account(
        from_session="psess:app-use-1",
        account_scope=None,
        app_instance_id="inst:other",
    )
    assert is_refusal(instance)
    assert GrantWidenRefused.matches(instance)

    machine = fixture.apply(
        change_request_id=request.change_request_id,
        authoring_session=authoring.product_session_id,
        operator_principal="machine",
        applied_at=_AT,
    )
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)

    promoted = fixture.promote()
    assert is_refusal(promoted)
    assert promoted.context["l17"] is True
    assert promoted.context["change_path"] is False

    authoring_mint = fixture.mint(
        from_session=authoring.product_session_id,
        change_request_id="cr:from-authoring",
        targets=[{"target_ref": _TARGET, "base_hash": _HASH_A}],
        patch={"kind": "filter_add", "path": "industry.known_at"},
    )
    assert is_refusal(authoring_mint)
    still = sessions.get("psess:app-use-1")
    assert is_ok(still)
    assert still.value.granted_ops == ("grant:inspect",)


def test_stale_base_hash_is_conflict_or_rebase_and_does_not_apply() -> None:
    _sessions, fixture = _world()
    request = _ok(_mint(fixture))
    authoring = _ok(fixture.open_authoring_handoff(request))
    _ok(fixture.advance_target(_TARGET, _HASH_B))
    validation = _ok(
        fixture.validate(
            change_request_id=request.change_request_id,
            authoring_session=authoring.product_session_id,
            validated_at=_AT,
        )
    )
    assert validation.verdict == "rebase-required"
    assert validation.conflicts
    applied = fixture.apply(
        change_request_id=request.change_request_id,
        authoring_session=authoring.product_session_id,
        operator_principal="operator",
        applied_at=_AT,
    )
    assert is_refusal(applied)
    assert applied.context["branch"] == "C"
    assert applied.context["verdict"] == "rebase-required"
    assert fixture.applies() == ()

    missing = ChangeRequestFixture(sessions=ProductSessionService())
    _ok(missing.sessions.mint(**_app_use_kwargs()))
    _ok(
        missing.install_v1(
            instance_id="inst:1",
            package_id="sector-intel",
            version="1.0.0",
            package_source_hash=_SOURCE,
            config_revision=4,
            granted_ops=("grant:inspect",),
            running_jobs=("job:run-1",),
        )
    )
    minted = _ok(_mint(missing, change_request_id="cr:missing-1"))
    handoff = _ok(
        missing.open_authoring_handoff(
            minted,
            product_session_id="psess:authoring-missing",
            instance_id="inst:authoring-missing",
        )
    )
    conflicted = _ok(
        missing.validate(
            change_request_id=minted.change_request_id,
            authoring_session=handoff.product_session_id,
            validated_at=_AT,
        )
    )
    assert conflicted.verdict == "conflict"
    refused = missing.apply(
        change_request_id=minted.change_request_id,
        authoring_session=handoff.product_session_id,
        operator_principal="operator",
        applied_at=_AT,
    )
    assert is_refusal(refused)
    assert refused.context["verdict"] == "conflict"


def test_tab_switch_patches_nothing_and_reconnect_does_not_replay() -> None:
    sessions, fixture = _world()
    request = _ok(_mint(fixture))
    assert PRODUCT_SESSION_TAB_WRITES is False
    assert fixture.tab_writes is False
    before = dict(_ok(sessions.get("psess:app-use-1")).to_payload())
    opened = _ok(fixture.tab_switch(product_session_id="psess:app-use-1", tab_id="tab-a"))
    assert dict(opened.to_payload()) == before
    closed = _ok(
        fixture.tab_switch(product_session_id="psess:app-use-1", tab_id="tab-a", action="close")
    )
    assert dict(closed.to_payload()) == before
    layout = fixture.open_authoring_handoff(request, layout={"widgets": []})
    assert is_refusal(layout)
    transcript = _mint(
        fixture,
        change_request_id="cr:transcript",
        private_transcript={"turns": []},
    )
    assert is_refusal(transcript)

    row = _ok(sessions.get("psess:app-use-1"))
    queried = _ok(
        fixture.reconnect(
            "psess:app-use-1",
            resume_cursor=row.resume_cursor,
            cursor_generation=row.cursor_generation,
        )
    )
    assert queried.kind == RECONNECT_KIND_QUERY
    assert queried.replays_unacked_intent is False
    intent = fixture.reconnect(
        "psess:app-use-1",
        resume_cursor=row.resume_cursor,
        cursor_generation=row.cursor_generation,
        command_id="cmd:1",
        payload={"op": "apply"},
    )
    assert is_refusal(intent)
    assert intent.context["replays_unacked_intent"] is False


def test_module_never_imports_qmb() -> None:
    source = _SRC.read_text(encoding="utf-8")
    assert "import qmb" not in source
    assert "from qmb" not in source
    tree = ast.parse(source)
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    assert not any(name == "qmb" or name.startswith("qmb.") for name in imports)


def test_reference_usage_example_runs() -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    main = cast("object", namespace["main"])
    assert callable(main)
    main()
