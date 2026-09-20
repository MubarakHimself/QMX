"""Story 55.2 — granted_ops are GrantRecords; mismatch and revoke refuse."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path

from qma.core.operations import OperationDescriptor, public_operation_descriptors
from qma.core.refusals import GrantInactive, GrantMismatch, GrantWidenRefused, ManifestIsNotGrant
from qma.daemon import (
    AuthoritativeJournal,
    PersistenceSubstrate,
    ProductSessionService,
)
from qma.daemon.journal import StoreClass
from qma.daemon.sessions import (
    GRANT_RECORD_TABLE,
    GRANT_REVOCATION_TABLE,
    GRANT_SIXTH_STORE_MINTED,
    PRODUCT_SESSION_SIXTH_STORE_MINTED,
    PRODUCT_SESSION_STORE,
    PRODUCT_SESSION_STORE_CLASS,
    PRODUCT_SESSION_TABLE,
    TOOL_REGISTRY_REWRITTEN,
    BoundSessionGrant,
)
from qma.wire.invocation_envelope import (
    ContributionRecord,
    InstanceRecord,
    PublicCallTransport,
    compute_input_hash,
)
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal

_DAEMON_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon"
_SRC = _DAEMON_SRC / "sessions" / "product_session.py"
_GRANT_SRC = _DAEMON_SRC / "sessions" / "grant_binding.py"
_TOOLS_SRC = _DAEMON_SRC / "tools" / "registry.py"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "product_session_grants_usage.py"

_AS_OF = "2026-09-20T00:00:00Z"
_NOW = "2026-09-20T00:00:00Z"
_EXPIRES = "2026-12-31T00:00:00Z"
_AFTER_EXPIRY = "2027-01-01T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
_INPUT = {"run_fp1": "run-1"}


def _clock(*, boot: str = "boot-grants", n: int = 48) -> DataDrivenClock:
    base = 1_727_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=tuple(range(n)))


def _open(tmp_path: Path) -> tuple[PersistenceSubstrate, AuthoritativeJournal]:
    opened = PersistenceSubstrate.open(tmp_path, machine="test-host", boot_epoch_id="boot-grants")
    assert is_ok(opened), opened
    bound = AuthoritativeJournal.bind(opened.value, clock=_clock())
    assert is_ok(bound), bound
    return opened.value, bound.value


def _descriptor() -> OperationDescriptor:
    for item in public_operation_descriptors():
        if item.op_id == "qmb.analysis.project" and item.version == 1:
            return item
    raise AssertionError("qmb.analysis.project v1 missing")


def _hash() -> str:
    hashed = compute_input_hash(_INPUT, descriptor=_descriptor())
    assert is_ok(hashed)
    return hashed.value


def _mint_kwargs(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "product_session_id": "psess:desk-1",
        "profile": "authoring",
        "principal": "operator",
        "contribution": dict(_CONTRIBUTION),
        "instance_id": "inst:1",
        "config_revision": 4,
        "as_of": _AS_OF,
        "granted_ops": (),
        "scope_path": [{"kind": "desk", "id": "research"}],
    }
    body.update(overrides)
    return body


def _grant_kwargs(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "grant_id": "grant:1",
        "op_id": "qmb.analysis.project",
        "op_version": 1,
        "effect_class": "read",
        "parameter_ceiling": {"allow_keys": ["run_fp1", "as_of"]},
        "expires_at": _EXPIRES,
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
        "caller_session_ref": "psess:desk-1",
    }
    payload.update(overrides)
    return payload


def _stores() -> tuple[
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


def _session() -> ProductSessionService:
    service = ProductSessionService()
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    granted = service.host_grant("psess:desk-1", **_grant_kwargs())
    assert is_ok(granted)
    return service


def test_granted_ops_store_grant_ids_resolved_from_ledger() -> None:
    service = _session()
    row = service.get("psess:desk-1")
    assert is_ok(row)
    assert row.value.granted_ops == ("grant:1",)
    assert all(token.startswith("grant:") for token in row.value.granted_ops)
    resolved = service.resolve_grant("psess:desk-1", "grant:1")
    assert is_ok(resolved)
    assert resolved.value.grant_id == "grant:1"
    assert resolved.value.op_id == "qmb.analysis.project"
    assert resolved.value.audience == "psess:desk-1"
    assert "revoked_at" not in resolved.value.to_payload()
    records = service.granted_records("psess:desk-1")
    assert is_ok(records)
    assert records.value[0].grant_id == "grant:1"
    bare = service.mint(
        **_mint_kwargs(
            product_session_id="psess:ops",
            granted_ops=("qmb.analysis.project",),
        )
    )
    assert is_refusal(bare)
    missing = service.resolve_grant("psess:desk-1", "grant:missing")
    assert is_refusal(missing)
    assert isinstance(missing, GrantMismatch)
    assert missing.context["code"] == "GRANT_MISMATCH"


def test_envelope_mismatch_is_grant_mismatch_before_execution() -> None:
    service = _session()
    executed: list[object] = []
    contributions, descriptors, instances = _stores()

    def _execute(bound: object) -> None:
        executed.append(bound)

    matched = service.dispatch_public_call(
        "psess:desk-1",
        transport=PublicCallTransport.IN_PROCESS,
        envelope=_envelope(),
        payload=_INPUT,
        now=_NOW,
        contributions=contributions,
        descriptors=descriptors,
        instances=instances,
        execute=_execute,
    )
    assert is_ok(matched)
    assert executed != []

    cases: tuple[tuple[str, dict[str, object]], ...] = (
        ("grant_id", {"grant_id": "grant:other", "idempotency_key": "idem:gid"}),
        ("op_id", {"op_id": "qmb.analysis.other", "idempotency_key": "idem:op"}),
        ("effect_class", {"effect_class": "append-evidence", "idempotency_key": "idem:fx"}),
    )
    for field, overrides in cases:
        executed.clear()
        refused = service.dispatch_public_call(
            "psess:desk-1",
            transport=PublicCallTransport.CLI,
            envelope=_envelope(**overrides),
            payload=_INPUT,
            now=_NOW,
            execute=_execute,
        )
        assert is_refusal(refused), field
        assert isinstance(refused, GrantMismatch), field
        assert refused.context["code"] == "GRANT_MISMATCH"
        assert refused.context["field"] == field
        assert executed == []

    inst_service = ProductSessionService()
    assert is_ok(inst_service.mint(**_mint_kwargs(product_session_id="psess:inst")))
    assert is_ok(
        inst_service.host_grant(
            "psess:inst",
            **_grant_kwargs(grant_id="grant:inst", instance_id="inst:other"),
        )
    )
    instance = inst_service.dispatch_public_call(
        "psess:inst",
        transport=PublicCallTransport.CLI,
        envelope=_envelope(
            grant_id="grant:inst",
            idempotency_key="idem:in",
            caller_session_ref="psess:inst",
        ),
        payload=_INPUT,
        now=_NOW,
    )
    assert is_refusal(instance)
    assert isinstance(instance, GrantMismatch)
    assert instance.context["field"] == "instance_id"

    contrib_service = ProductSessionService()
    assert is_ok(contrib_service.mint(**_mint_kwargs(product_session_id="psess:co")))
    assert is_ok(
        contrib_service.host_grant(
            "psess:co",
            **_grant_kwargs(
                grant_id="grant:co",
                contribution={
                    "qualified_id": "analysis-backtest:qmb",
                    "package_version": "0.2.0",
                },
            ),
        )
    )
    contrib = contrib_service.dispatch_public_call(
        "psess:co",
        transport=PublicCallTransport.CLI,
        envelope=_envelope(
            grant_id="grant:co",
            idempotency_key="idem:co",
            caller_session_ref="psess:co",
        ),
        payload=_INPUT,
        now=_NOW,
    )
    assert is_refusal(contrib)
    assert isinstance(contrib, GrantMismatch)
    assert contrib.context["field"] == "contribution"


def test_revoke_and_expiry_refuse_new_dispatch_accepted_may_finish() -> None:
    service = _session()
    contributions, descriptors, instances = _stores()
    accepted = service.accept_work(
        "psess:desk-1",
        grant_id="grant:1",
        logical_invocation_id="inv:1",
        now=_NOW,
    )
    assert is_ok(accepted)
    revoked = service.revoke_grant(
        "psess:desk-1",
        grant_id="grant:1",
        principal="operator",
        reason="session-ended",
        revoked_at=_NOW,
    )
    assert is_ok(revoked)
    still = service.resolve_grant("psess:desk-1", "grant:1")
    assert is_ok(still)
    minted_bytes = still.value.canonical_bytes()
    assert is_ok(minted_bytes)
    assert minted_bytes.value == service.ledger.minted_bytes("grant:1")
    finish = service.dispatch_public_call(
        "psess:desk-1",
        transport=PublicCallTransport.IN_PROCESS,
        envelope=_envelope(),
        payload=_INPUT,
        now=_NOW,
        contributions=contributions,
        descriptors=descriptors,
        instances=instances,
    )
    assert is_ok(finish)
    new_dispatch = service.dispatch_public_call(
        "psess:desk-1",
        transport=PublicCallTransport.WIRE,
        envelope=_envelope(logical_invocation_id="inv:new", idempotency_key="idem:new"),
        payload=_INPUT,
        now=_NOW,
        contributions=contributions,
        descriptors=descriptors,
        instances=instances,
    )
    assert is_refusal(new_dispatch)
    assert isinstance(new_dispatch, GrantInactive)
    assert new_dispatch.context["reason"] == "revoked"
    assert new_dispatch.context["new_dispatch_refused"] is True
    assert new_dispatch.context["already_accepted_may_finish"] is True

    fresh = ProductSessionService()
    assert is_ok(fresh.mint(**_mint_kwargs(product_session_id="psess:exp")))
    assert is_ok(
        fresh.host_grant(
            "psess:exp",
            **_grant_kwargs(grant_id="grant:exp"),
        )
    )
    expired = fresh.dispatch_public_call(
        "psess:exp",
        transport="in-process",
        envelope=_envelope(
            grant_id="grant:exp",
            logical_invocation_id="inv:late",
            idempotency_key="idem:late",
            caller_session_ref="psess:exp",
        ),
        payload=_INPUT,
        now=_AFTER_EXPIRY,
    )
    assert is_refusal(expired)
    assert isinstance(expired, GrantInactive)
    assert expired.context["reason"] == "expired"
    assert expired.context["moment"] == "dispatch"


def test_upgrade_cannot_widen_without_regrant_bumping_context_revision() -> None:
    service = _session()
    row = service.get("psess:desk-1")
    assert is_ok(row)
    assert row.value.context_revision == 0
    before = service.ledger.minted_bytes("grant:1")
    assert before is not None
    widened = service.apply_upgrade(
        "psess:desk-1",
        "grant:1",
        package_version="0.2.0",
        instance_id="inst:2",
    )
    assert isinstance(widened, GrantWidenRefused)
    assert widened.context["requires_regrant"] is True
    assert widened.context["bumps_context_revision"] is True
    stale = service.regrant(
        "psess:desk-1",
        "grant:1",
        context_revision=0,
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "0.2.0"},
        instance_id="inst:2",
        grant_id="grant:2",
    )
    assert is_refusal(stale)
    assert stale.context["field"] == "context_revision"
    regranted = service.regrant(
        "psess:desk-1",
        "grant:1",
        context_revision=1,
        contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "0.2.0"},
        instance_id="inst:2",
        grant_id="grant:2",
    )
    assert is_ok(regranted)
    assert regranted.value.context_revision == 1
    updated = service.get("psess:desk-1")
    assert is_ok(updated)
    assert updated.value.context_revision == 1
    assert "grant:2" in updated.value.granted_ops
    assert "grant:1" in updated.value.granted_ops
    assert service.ledger.minted_bytes("grant:1") == before
    assert service.ledger.grants["grant:1"].contribution.package_version == "0.1.0"
    assert service.ledger.grants["grant:2"].contribution.package_version == "0.2.0"
    assert service.ledger.grants["grant:2"].instance_id == "inst:2"


def test_manifests_request_host_grants() -> None:
    service = ProductSessionService()
    assert is_ok(service.mint(**_mint_kwargs()))
    refused = service.host_grant(
        "psess:desk-1",
        issuer="manifest",
        **_grant_kwargs(),
    )
    assert is_refusal(refused)
    assert isinstance(refused, ManifestIsNotGrant)
    assert refused.context["manifests_grant"] is False
    assert refused.context["host_grants"] is True
    minted = service.host_grant("psess:desk-1", **_grant_kwargs())
    assert is_ok(minted)
    assert minted.value.grant_id.startswith("grant:")


def test_grants_persist_beside_product_session_not_new_store(tmp_path: Path) -> None:
    assert GRANT_SIXTH_STORE_MINTED is False
    assert PRODUCT_SESSION_SIXTH_STORE_MINTED is False
    assert StoreClass.JOURNAL_DERIVED_PROJECTION.value == PRODUCT_SESSION_STORE_CLASS
    substrate, journal = _open(tmp_path)
    try:
        service = ProductSessionService(journal=journal, sqlite=substrate.sqlite)
        assert is_ok(service.mint(**_mint_kwargs()))
        granted = service.host_grant("psess:desk-1", **_grant_kwargs())
        assert is_ok(granted)
        assert is_ok(
            service.accept_work(
                "psess:desk-1",
                grant_id="grant:1",
                logical_invocation_id="inv:1",
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
        tables = {
            str(row[0])
            for row in substrate.sqlite.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert PRODUCT_SESSION_TABLE in tables
        assert GRANT_RECORD_TABLE in tables
        assert GRANT_REVOCATION_TABLE in tables
        assert "grant_record_store" not in tables
        rebound = ProductSessionService(sqlite=substrate.sqlite)
        restored = rebound.resolve_grant("psess:desk-1", "grant:1")
        assert is_ok(restored)
        assert restored.value.op_id == "qmb.analysis.project"
        finish = rebound.dispatch_public_call(
            "psess:desk-1",
            transport=PublicCallTransport.IN_PROCESS,
            envelope=_envelope(),
            payload=_INPUT,
            now=_NOW,
        )
        assert is_ok(finish)
        assert isinstance(finish.value, BoundSessionGrant)
        new_dispatch = rebound.dispatch_public_call(
            "psess:desk-1",
            transport=PublicCallTransport.CLI,
            envelope=_envelope(logical_invocation_id="inv:new", idempotency_key="idem:new"),
            payload=_INPUT,
            now=_NOW,
        )
        assert is_refusal(new_dispatch)
        assert isinstance(new_dispatch, GrantInactive)
        events = journal.read_all()
        assert is_ok(events)
        names = [str(item["event"]) for item in events.value]
        assert "product_session.grant_minted" in names
        assert "product_session.grant_revoked" in names
        loaded = rebound.get("psess:desk-1")
        assert is_ok(loaded)
        assert loaded.value.store == PRODUCT_SESSION_STORE
    finally:
        journal.close()
        substrate.close()


def test_does_not_rewrite_tool_registry() -> None:
    assert TOOL_REGISTRY_REWRITTEN is False
    assert _TOOLS_SRC.is_file()
    for path in (_SRC, _GRANT_SRC):
        source = path.read_text(encoding="utf-8")
        assert "import qmb" not in source
        assert "from qmb" not in source
        assert "qma.daemon.tools" not in source
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)
        assert not any(name == "qmb" or name.startswith("qmb.") for name in imports)
        assert not any(
            name == "qma.daemon.tools" or name.startswith("qma.daemon.tools.") for name in imports
        )


def test_reference_usage_example_runs() -> None:
    namespace = runpy.run_path(str(_EXAMPLE))
    namespace["main"]()
