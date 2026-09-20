"""Story 55.3 — session context lives in the journal, not a tab."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path

from qma.daemon import (
    AuthoritativeJournal,
    PersistenceSubstrate,
    ProductSessionService,
)
from qma.daemon.journal import EIGHT_STORE_CLASSES, StoreClass
from qma.daemon.sessions import (
    PRODUCT_SESSION_OCCUPANCY,
    PRODUCT_SESSION_SIXTH_STORE_MINTED,
    PRODUCT_SESSION_TAB_WRITES,
    RECONNECT_KIND_QUERY,
    RECONNECT_KIND_RESYNC,
    ReconnectSnapshot,
    refuse_tab_mints_session,
)
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal

_DAEMON_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon"
_SRC = _DAEMON_SRC / "sessions" / "product_session.py"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "product_session_journal_usage.py"

_AS_OF = "2026-09-20T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}


def _clock(*, boot: str = "boot-psess-journal", n: int = 48) -> DataDrivenClock:
    base = 1_727_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=tuple(range(n)))


def _open(
    tmp_path: Path, *, boot: str = "boot-psess-journal"
) -> tuple[PersistenceSubstrate, AuthoritativeJournal]:
    opened = PersistenceSubstrate.open(tmp_path, machine="test-host", boot_epoch_id=boot)
    assert is_ok(opened), opened
    bound = AuthoritativeJournal.bind(opened.value, clock=_clock(boot=boot))
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


def test_no_sixth_store_class_and_tabs_write_nothing() -> None:
    assert PRODUCT_SESSION_SIXTH_STORE_MINTED is False
    assert PRODUCT_SESSION_TAB_WRITES is False
    assert len(EIGHT_STORE_CLASSES) == 8
    assert StoreClass.JOURNAL_DERIVED_PROJECTION.value == "journal_derived_projection"
    assert len(StoreClass) == 2
    refused = refuse_tab_mints_session()
    assert is_refusal(refused)
    assert refused.context["tab_mints"] is False
    assert refused.context["session_closed"] is False


def test_journal_restore_after_restart_is_not_ram(tmp_path: Path) -> None:
    substrate, journal = _open(tmp_path)
    try:
        service = ProductSessionService(journal=journal, sqlite=substrate.sqlite)
        minted = service.mint(**_mint_kwargs())
        assert is_ok(minted)
        bound = dict(minted.value.context.to_payload())
        session_id = minted.value.product_session_id
        events = journal.read_all()
        assert is_ok(events)
        assert events.value[0]["event"] == "product_session.minted"
    finally:
        journal.close()
        substrate.close()

    rebound_sub, rebound_journal = _open(tmp_path, boot="boot-psess-journal-2")
    try:
        restored_service = ProductSessionService(journal=rebound_journal)
        assert restored_service.restored_from_journal is False
        missing = restored_service.get("psess:desk-1")
        assert is_refusal(missing)
        restored = restored_service.restore_from_journal()
        assert is_ok(restored)
        assert restored_service.restored_from_journal is True
        assert len(restored.value) == 1
        row = restored.value[0]
        assert row.product_session_id == session_id
        assert dict(row.context.to_payload()) == bound
        assert row.occupancy == PRODUCT_SESSION_OCCUPANCY
        loaded = restored_service.get("psess:desk-1")
        assert is_ok(loaded)
        matched = restored_service.bind_public_call("psess:desk-1", _call())
        assert is_ok(matched)
        assert matched.value.context.as_of == _AS_OF
        assert matched.value.session.app_instance_id == "inst:1"
    finally:
        rebound_journal.close()
        rebound_sub.close()


def test_sqlite_fold_wipe_still_restores_from_journal(tmp_path: Path) -> None:
    substrate, journal = _open(tmp_path, boot="boot-psess-wipe")
    try:
        service = ProductSessionService(journal=journal, sqlite=substrate.sqlite)
        minted = service.mint(**_mint_kwargs())
        assert is_ok(minted)
    finally:
        journal.close()
        substrate.close()

    rebound_sub, rebound_journal = _open(tmp_path, boot="boot-psess-wipe-2")
    try:
        rebound_sub.sqlite.execute("DELETE FROM product_session")
        wiped = ProductSessionService(journal=rebound_journal, sqlite=rebound_sub.sqlite)
        absent = wiped.get("psess:desk-1")
        assert is_refusal(absent)
        restored = wiped.restore_from_journal()
        assert is_ok(restored)
        loaded = wiped.get("psess:desk-1")
        assert is_ok(loaded)
        assert loaded.value.context.instance_id == "inst:1"
        assert loaded.value.context.config_revision == 4
    finally:
        rebound_journal.close()
        rebound_sub.close()


def test_two_tabs_share_one_product_session() -> None:
    service = ProductSessionService()
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    first = service.open_tab(tab_id="tab-a", app_instance_id="inst:1")
    second = service.open_tab(tab_id="tab-b", app_instance_id="inst:1")
    assert is_ok(first)
    assert is_ok(second)
    assert first.value.product_session_id == second.value.product_session_id == "psess:desk-1"
    assert dict(first.value.context.to_payload()) == dict(second.value.context.to_payload())
    tabs = service.attached_tabs("psess:desk-1")
    assert is_ok(tabs)
    assert tabs.value == ("tab-a", "tab-b")
    payload = dict(first.value.to_payload())
    assert "tab" not in payload
    assert "tab_id" not in payload


def test_close_tab_does_not_close_session() -> None:
    service = ProductSessionService()
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    assert is_ok(service.open_tab(tab_id="tab-a", product_session_id="psess:desk-1"))
    assert is_ok(service.open_tab(tab_id="tab-b", product_session_id="psess:desk-1"))
    closed = service.close_tab("tab-a", product_session_id="psess:desk-1")
    assert is_ok(closed)
    still = service.get("psess:desk-1")
    assert is_ok(still)
    assert still.value.context.as_of == _AS_OF
    remaining = service.attached_tabs("psess:desk-1")
    assert is_ok(remaining)
    assert remaining.value == ("tab-b",)
    last = service.close_tab("tab-b")
    assert is_ok(last)
    after = service.get("psess:desk-1")
    assert is_ok(after)
    empty = service.attached_tabs("psess:desk-1")
    assert is_ok(empty)
    assert empty.value == ()


def test_new_tab_does_not_mint_a_product_session() -> None:
    service = ProductSessionService()
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    missing = service.open_tab(tab_id="tab-new", app_instance_id="inst:other")
    assert is_refusal(missing)
    assert missing.context["tab_mints"] is False
    listed = service.get("psess:desk-1")
    assert is_ok(listed)
    second = service.mint(**_mint_kwargs(product_session_id="psess:desk-2"))
    assert is_refusal(second)
    assert second.context["tab_mints"] is False
    still = service.get("psess:desk-1")
    assert is_ok(still)
    absent = service.get("psess:desk-2")
    assert is_refusal(absent)


def test_tab_change_writes_nothing_to_the_journal(tmp_path: Path) -> None:
    substrate, journal = _open(tmp_path, boot="boot-psess-tabs")
    try:
        service = ProductSessionService(journal=journal, sqlite=substrate.sqlite)
        minted = service.mint(**_mint_kwargs())
        assert is_ok(minted)
        before = journal.read_all()
        assert is_ok(before)
        count = len(before.value)
        assert is_ok(service.open_tab(tab_id="tab-a", app_instance_id="inst:1"))
        assert is_ok(service.open_tab(tab_id="tab-b", app_instance_id="inst:1"))
        assert is_ok(service.close_tab("tab-a"))
        after = journal.read_all()
        assert is_ok(after)
        assert len(after.value) == count
        assert service.tab_writes is False
    finally:
        journal.close()
        substrate.close()


def test_reconnect_is_query_and_does_not_replay_intent(tmp_path: Path) -> None:
    substrate, journal = _open(tmp_path, boot="boot-psess-reconnect")
    try:
        service = ProductSessionService(journal=journal, sqlite=substrate.sqlite)
        minted = service.mint(**_mint_kwargs())
        assert is_ok(minted)
        row = minted.value
        queried = service.reconnect(
            "psess:desk-1",
            resume_cursor=row.resume_cursor,
            cursor_generation=row.cursor_generation,
        )
        assert is_ok(queried)
        snapshot = queried.value
        assert isinstance(snapshot, ReconnectSnapshot)
        assert snapshot.kind == RECONNECT_KIND_QUERY
        assert snapshot.replays_unacked_intent is False
        assert snapshot.writes is False
        assert snapshot.tab_writes is False
        assert snapshot.is_query is True
        assert dict(snapshot.context.to_payload()) == dict(row.context.to_payload())
        assert snapshot.session.context_revision == row.context_revision
        intent = service.reconnect(
            "psess:desk-1",
            resume_cursor=row.resume_cursor,
            cursor_generation=row.cursor_generation,
            command_id="cmd:1",
            payload={"op": "select_ref"},
        )
        assert is_refusal(intent)
        assert intent.context["replays_unacked_intent"] is False
        tabbed = service.reconnect(
            "psess:desk-1",
            resume_cursor=row.resume_cursor,
            cursor_generation=row.cursor_generation,
            tab_id="tab-a",
        )
        assert is_refusal(tabbed)
        compacted = service.compact_history(row.resume_cursor)
        assert is_ok(compacted)
        resynced = service.reconnect(
            "psess:desk-1",
            resume_cursor=row.resume_cursor,
            cursor_generation=row.cursor_generation,
        )
        assert is_ok(resynced)
        assert resynced.value.kind == RECONNECT_KIND_RESYNC
        assert resynced.value.replays_unacked_intent is False
        assert resynced.value.cursor_generation == row.cursor_generation + 1
        assert dict(resynced.value.context.to_payload()) == dict(row.context.to_payload())
        assert resynced.value.session.context_revision == row.context_revision
        payload = dict(resynced.value.to_payload())
        assert payload["kind"] == RECONNECT_KIND_RESYNC
        assert payload["replays_unacked_intent"] is False
    finally:
        journal.close()
        substrate.close()


def test_tabs_reattach_after_journal_restore_without_minting(tmp_path: Path) -> None:
    substrate, journal = _open(tmp_path, boot="boot-psess-share")
    try:
        service = ProductSessionService(journal=journal, sqlite=substrate.sqlite)
        minted = service.mint(**_mint_kwargs())
        assert is_ok(minted)
        assert is_ok(service.open_tab(tab_id="tab-a", app_instance_id="inst:1"))
        assert is_ok(service.open_tab(tab_id="tab-b", app_instance_id="inst:1"))
        before = journal.read_all()
        assert is_ok(before)
        count = len(before.value)
    finally:
        journal.close()
        substrate.close()

    rebound_sub, rebound_journal = _open(tmp_path, boot="boot-psess-share-2")
    try:
        restored_service = ProductSessionService(journal=rebound_journal)
        restored = restored_service.restore_from_journal()
        assert is_ok(restored)
        empty_tabs = restored_service.attached_tabs("psess:desk-1")
        assert is_ok(empty_tabs)
        assert empty_tabs.value == ()
        first = restored_service.open_tab(tab_id="tab-a", app_instance_id="inst:1")
        second = restored_service.open_tab(tab_id="tab-b", app_instance_id="inst:1")
        assert is_ok(first)
        assert is_ok(second)
        assert first.value.product_session_id == "psess:desk-1"
        assert second.value.product_session_id == "psess:desk-1"
        after = rebound_journal.read_all()
        assert is_ok(after)
        assert len(after.value) == count
        minted_again = restored_service.mint(**_mint_kwargs(product_session_id="psess:from-tab"))
        assert is_refusal(minted_again)
    finally:
        rebound_journal.close()
        rebound_sub.close()


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
