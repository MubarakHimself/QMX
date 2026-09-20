"""Story 55.1 — product_session.context is the bound request context."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path
from typing import cast

from qma.core.ontology import ActorId, DeskSlug, Profile, Session
from qma.core.refusals import EnvelopeMismatch
from qma.core.vocabulary.enums import ExecutionModel, SessionAutonomy
from qma.daemon import (
    PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA,
    PRODUCT_SESSION_OCCUPANCY,
    PRODUCT_SESSION_OWNER,
    AuthoritativeJournal,
    PersistenceSubstrate,
    ProductSessionService,
)
from qma.daemon.journal import (
    CLOSED_PROJECTIONS,
    EIGHT_STORE_CLASSES,
    StoreClass,
    v1_fold_contract,
)
from qma.daemon.sessions import (
    PRODUCT_SESSION_CONTEXT_FIELDS,
    PRODUCT_SESSION_FOLD_ID,
    PRODUCT_SESSION_INSPECT_SHAS,
    PRODUCT_SESSION_LIVE_ADJACENT,
    PRODUCT_SESSION_NEW_CT_MINTED,
    PRODUCT_SESSION_SIXTH_COMP_MINTED,
    PRODUCT_SESSION_SIXTH_STORE_MINTED,
    PRODUCT_SESSION_STORE,
    PRODUCT_SESSION_STORE_CLASS,
    PRODUCT_SESSION_TABLE,
    PRODUCT_SESSION_WIRED_AT_INSPECT_SHA,
    QMA_SESSION_ID_PREFIX,
    BoundProductSessionCall,
    ProductSessionProfile,
    claim_product_session_at_inspect_sha,
    refuse_tab_as_product_session,
)
from qma.wire.envelope import SCOPE_KIND_ORDER
from qma.wire.invocation_envelope import InvocationEnvelope
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal

_SRC = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "qma"
    / "daemon"
    / "sessions"
    / "product_session.py"
)
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "product_session_context_usage.py"

_AS_OF = "2026-09-20T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}


def _clock(*, boot: str = "boot-psess", n: int = 32) -> DataDrivenClock:
    base = 1_727_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=tuple(range(n)))


def _open(tmp_path: Path) -> tuple[PersistenceSubstrate, AuthoritativeJournal]:
    opened = PersistenceSubstrate.open(tmp_path, machine="test-host", boot_epoch_id="boot-psess")
    assert is_ok(opened), opened
    bound = AuthoritativeJournal.bind(opened.value, clock=_clock())
    assert is_ok(bound), bound
    return opened.value, bound.value


def _mint_kwargs(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "product_session_id": "psess:desk-1",
        "profile": "authoring",
        "principal": "operator",
        "contribution": dict(_CONTRIBUTION),
        "instance_id": "inst:1",
        "config_revision": 4,
        "as_of": _AS_OF,
        "account_scope": None,
        "granted_ops": ("grant:inspect",),
        "selected_refs": [{"kind": "run", "id": "fp1:sha256:ab"}],
        "scope_path": [{"kind": "desk", "id": "research"}],
    }
    body.update(overrides)
    return body


def _call(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "principal": "operator",
        "occupancy": "none",
        "contribution": dict(_CONTRIBUTION),
        "instance_id": "inst:1",
        "config_revision": 4,
        "as_of": _AS_OF,
    }
    body.update(overrides)
    return body


def test_inspect_sha_did_not_persist_product_session() -> None:
    assert PRODUCT_SESSION_INSPECT_SHAS == ("270e992",)
    assert PRODUCT_SESSION_EXISTED_AT_INSPECT_SHA is False
    assert PRODUCT_SESSION_WIRED_AT_INSPECT_SHA is False
    claimed = claim_product_session_at_inspect_sha(True)
    assert is_refusal(claimed)
    assert claimed.context["existed_at_inspect_sha"] is False
    honest = claim_product_session_at_inspect_sha(False)
    assert is_ok(honest)
    assert honest.value is False


def test_identity_occupancy_none_no_sixth_comp_or_store() -> None:
    assert PRODUCT_SESSION_OWNER == "COMP-QMA-DAEMON"
    assert PRODUCT_SESSION_OCCUPANCY == "none"
    assert PRODUCT_SESSION_LIVE_ADJACENT is False
    assert PRODUCT_SESSION_SIXTH_COMP_MINTED is False
    assert PRODUCT_SESSION_SIXTH_STORE_MINTED is False
    assert PRODUCT_SESSION_NEW_CT_MINTED is False
    assert PRODUCT_SESSION_STORE == "product_session"
    assert PRODUCT_SESSION_STORE_CLASS == "journal_derived_projection"
    assert PRODUCT_SESSION_STORE in CLOSED_PROJECTIONS
    assert len(EIGHT_STORE_CLASSES) == 8
    assert "product_session" not in SCOPE_KIND_ORDER
    fold = v1_fold_contract(PRODUCT_SESSION_FOLD_ID)
    assert fold is not None
    assert fold.source_stream == "product_session.*"
    assert fold.knowledge_time_bound == "as_of_recorded_at"


def test_ids_are_psess_not_sess_and_not_ontology_profile() -> None:
    service = ProductSessionService()
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    row = minted.value
    assert row.product_session_id.startswith("psess:")
    assert not row.product_session_id.startswith(QMA_SESSION_ID_PREFIX)
    assert row.profile is ProductSessionProfile.AUTHORING
    assert row.profile.value == "authoring"
    assert not isinstance(row.profile, Profile)
    payload = dict(row.to_payload())
    assert "qma_session_id" not in payload
    assert "tab" not in payload
    assert "tab_id" not in payload
    context_payload = payload["context"]
    assert isinstance(context_payload, dict)
    assert context_payload["occupancy"] == "none"
    assert row.context.account_scope is None
    assert "account_scope" not in payload
    assert "account_scope" not in context_payload

    sess = service.mint(**_mint_kwargs(product_session_id="sess:1"))
    assert is_refusal(sess)
    tab = service.mint(**_mint_kwargs(product_session_id="tab:1"))
    assert is_refusal(tab)
    profile = service.mint(**_mint_kwargs(profile=Profile(display_name="x", desk_slugs=())))
    assert is_refusal(profile)
    assert "ontology.Profile" in str(profile.context.get("reason", ""))


def test_context_fields_and_public_call_mismatch() -> None:
    service = ProductSessionService()
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    context = minted.value.context
    payload = context.to_payload()
    for field in PRODUCT_SESSION_CONTEXT_FIELDS:
        if field == "account_scope":
            continue
        assert field in payload
    assert context.principal == "operator"
    assert context.occupancy == "none"
    assert context.contribution.as_tuple() == ("analysis-backtest:qmb", "0.1.0")
    assert context.instance_id == "inst:1"
    assert context.config_revision == 4
    assert context.as_of == _AS_OF
    assert context.account_scope is None

    bound = service.bind_public_call("psess:desk-1", _call())
    assert is_ok(bound)
    assert isinstance(bound.value, BoundProductSessionCall)
    assert bound.value.is_authority is False
    assert bound.value.context is minted.value.context

    missing = service.bind_public_call("psess:desk-1", {"principal": "operator"})
    assert is_refusal(missing)
    assert isinstance(missing, EnvelopeMismatch)
    assert missing.context["code"] == "MISMATCH"
    assert missing.context["cause"] == "missing"

    stale = service.bind_public_call("psess:desk-1", _call(config_revision=99))
    assert is_refusal(stale)
    assert isinstance(stale, EnvelopeMismatch)
    assert stale.context["field"] == "config_revision"
    assert stale.context["cause"] == "stale"

    stale_contrib = service.bind_public_call(
        "psess:desk-1",
        _call(contribution={"qualified_id": "analysis-backtest:qmb", "package_version": "9.9.9"}),
    )
    assert is_refusal(stale_contrib)
    assert stale_contrib.context["field"] == "contribution"

    occupancy = service.bind_public_call("psess:desk-1", _call(occupancy="run"))
    assert is_refusal(occupancy)
    assert occupancy.context["field"] == "occupancy"

    scoped = service.bind_public_call("psess:desk-1", _call(account_scope="acct:1"))
    assert is_refusal(scoped)
    assert scoped.context["field"] == "account_scope"


def test_granted_account_scope_and_selected_refs() -> None:
    service = ProductSessionService()
    minted = service.mint(
        **_mint_kwargs(
            account_scope="acct:live",
            profile="app-use",
            selected_refs=[
                {"kind": "artifact", "id": "fp1:sha256:aa"},
                {
                    "kind": "contribution",
                    "qualified_id": "analysis-backtest:qmb",
                    "package_version": "0.1.0",
                },
                {"kind": "template", "qualified_id": "gt:demo", "version": "1"},
                {"kind": "research_ref", "id": "research:1"},
            ],
        )
    )
    assert is_ok(minted)
    row = minted.value
    assert row.profile is ProductSessionProfile.APP_USE
    assert row.account_scope == "acct:live"
    assert row.context.account_scope == "acct:live"
    assert row.granted_ops == ("grant:inspect",)
    assert all(op.startswith("grant:") for op in row.granted_ops)
    kinds = {ref.kind for ref in row.selected_refs}
    assert kinds == {"artifact", "contribution", "template", "research_ref"}
    matched = service.bind_public_call("psess:desk-1", _call(account_scope="acct:live"))
    assert is_ok(matched)
    missing_scope = service.bind_public_call("psess:desk-1", _call())
    assert is_refusal(missing_scope)
    assert missing_scope.context["field"] == "account_scope"

    layout_refs: list[dict[str, object]] = [
        {"kind": "run", "id": "fp1:sha256:ab", "layout": {"x": 1}},
    ]
    layout = service.mint(
        **_mint_kwargs(product_session_id="psess:layout", selected_refs=layout_refs)
    )
    assert is_refusal(layout)
    widget_refs: list[dict[str, object]] = [
        {"kind": "run", "id": "x", "widgets": ["chart"]},
    ]
    widgets = service.mint(
        **_mint_kwargs(product_session_id="psess:widgets", selected_refs=widget_refs)
    )
    assert is_refusal(widgets)
    bare_ops = service.mint(
        **_mint_kwargs(product_session_id="psess:ops", granted_ops=("qmb.analysis.project",))
    )
    assert is_refusal(bare_ops)


def test_sess_attachment_is_query_not_durable_and_tab_writes_nothing() -> None:
    service = ProductSessionService()
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    owner = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(owner)
    qma_session = Session(
        id="sess:1",
        owner=owner.value,
        execution_model=ExecutionModel.DIALOGUE,
        autonomy=SessionAutonomy.INTERACTIVE,
    )
    noted = service.note_session_attachment("psess:desk-1", qma_session.id)
    assert is_ok(noted)
    second = service.note_session_attachment("psess:desk-1", "sess:2")
    assert is_ok(second)
    attached = service.attached_sessions("psess:desk-1")
    assert is_ok(attached)
    assert attached.value == ("sess:1", "sess:2")
    assert "qma_session_id" not in minted.value.to_payload()
    assert "session_id" not in minted.value.to_payload()

    tab = refuse_tab_as_product_session()
    assert is_refusal(tab)
    assert tab.context["tab_writes"] is False
    minted_tab = service.mint(**_mint_kwargs(product_session_id="psess:x", tab_id="tab-1"))
    assert is_refusal(minted_tab)
    call_tab = service.bind_public_call("psess:desk-1", _call(tab_id="tab-1"))
    assert is_refusal(call_tab)


def test_profile_immutable_and_occupancy_stays_none() -> None:
    service = ProductSessionService()
    first = service.mint(**_mint_kwargs())
    assert is_ok(first)
    again = service.mint(**_mint_kwargs(profile="app-use"))
    assert is_refusal(again)
    busy = service.mint(**_mint_kwargs(product_session_id="psess:busy", occupancy="run"))
    assert is_refusal(busy)
    assert busy.context["field"] == "occupancy"


def test_persists_on_existing_daemon_sqlite_not_new_class(tmp_path: Path) -> None:
    substrate, journal = _open(tmp_path)
    try:
        service = ProductSessionService(journal=journal, sqlite=substrate.sqlite)
        minted = service.mint(**_mint_kwargs())
        assert is_ok(minted)
        assert minted.value.journal_seq == 1
        assert minted.value.store == PRODUCT_SESSION_STORE
        assert minted.value.store_class == PRODUCT_SESSION_STORE_CLASS
        tables = {
            str(row[0])
            for row in substrate.sqlite.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert PRODUCT_SESSION_TABLE in tables
        assert "product_session_store" not in tables
        loaded = service.get("psess:desk-1")
        assert is_ok(loaded)
        assert loaded.value.context.as_of == _AS_OF
        rebound = ProductSessionService(sqlite=substrate.sqlite)
        restored = rebound.get("psess:desk-1")
        assert is_ok(restored)
        assert restored.value.product_session_id == "psess:desk-1"
        assert restored.value.context.instance_id == "inst:1"
        events = journal.read_all()
        assert is_ok(events)
        assert events.value[0]["event"] == "product_session.minted"
        scope = events.value[0]["scope_path"]
        assert isinstance(scope, list)
        for raw_segment in cast("list[object]", scope):
            assert isinstance(raw_segment, dict)
            segment = cast("dict[str, object]", raw_segment)
            assert segment["kind"] != "product_session"
        declared = journal.declare_store(PRODUCT_SESSION_STORE)
        assert is_ok(declared)
        assert declared.value.store_class is StoreClass.JOURNAL_DERIVED_PROJECTION
        assert declared.value.fold_metadata.source_stream == "product_session.*"
    finally:
        journal.close()
        substrate.close()


def test_envelope_fields_compare_when_nested() -> None:
    service = ProductSessionService()
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    envelope = InvocationEnvelope.try_create(
        logical_invocation_id="inv:1",
        attempt_id=1,
        op_id="qmb.analysis.project",
        op_version=1,
        contribution=dict(_CONTRIBUTION),
        instance_id="inst:1",
        config_revision=4,
        grant_id="grant:inspect",
        effect_class="read",
        idempotency_key="idem:1",
        reconcile_policy="query-then-decide",
        input_hash="fp1:sha256:" + ("a" * 64),
        call_depth=0,
        caller_session_ref="psess:desk-1",
    )
    assert is_ok(envelope)
    nested = service.bind_public_call(
        "psess:desk-1",
        {
            "principal": "operator",
            "occupancy": "none",
            "as_of": _AS_OF,
            "envelope": envelope.value,
        },
    )
    assert is_ok(nested)
    stale_env = InvocationEnvelope.try_create(
        **{
            **dict(envelope.value.to_payload()),
            "config_revision": 8,
        }
    )
    assert is_ok(stale_env)
    refused = service.bind_public_call(
        "psess:desk-1",
        {
            "principal": "operator",
            "occupancy": "none",
            "as_of": _AS_OF,
            "envelope": stale_env.value,
        },
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "config_revision"


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
    namespace["main"]()
