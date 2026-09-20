"""Reference usage — product_session lives in the journal, not a tab (55.3)."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from qma.daemon import AuthoritativeJournal, PersistenceSubstrate, ProductSessionService
from qma.daemon.sessions import (
    PRODUCT_SESSION_SIXTH_STORE_MINTED,
    PRODUCT_SESSION_TAB_WRITES,
    RECONNECT_KIND_QUERY,
)
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal

_AS_OF = "2026-09-20T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}


def _clock(*, boot: str, n: int = 24) -> DataDrivenClock:
    base = 1_727_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=tuple(range(n)))


def _open(root: Path, *, boot: str) -> tuple[PersistenceSubstrate, AuthoritativeJournal]:
    opened = PersistenceSubstrate.open(root, machine="example-host", boot_epoch_id=boot)
    assert is_ok(opened)
    bound = AuthoritativeJournal.bind(opened.value, clock=_clock(boot=boot))
    assert is_ok(bound)
    return opened.value, bound.value


def main() -> None:
    assert PRODUCT_SESSION_SIXTH_STORE_MINTED is False
    assert PRODUCT_SESSION_TAB_WRITES is False
    with TemporaryDirectory() as raw:
        root = Path(raw)
        substrate, journal = _open(root, boot="boot-example")
        try:
            service = ProductSessionService(journal=journal, sqlite=substrate.sqlite)
            minted = service.mint(
                product_session_id="psess:desk-1",
                profile="authoring",
                principal="operator",
                contribution=dict(_CONTRIBUTION),
                instance_id="inst:1",
                config_revision=4,
                as_of=_AS_OF,
                granted_ops=("grant:inspect",),
            )
            assert is_ok(minted)
            assert is_ok(service.open_tab(tab_id="tab-a", app_instance_id="inst:1"))
            assert is_ok(service.open_tab(tab_id="tab-b", app_instance_id="inst:1"))
            assert is_ok(service.close_tab("tab-a"))
            still = service.get("psess:desk-1")
            assert is_ok(still)
            print("two tabs shared psess:desk-1; closing a tab left the session")
        finally:
            journal.close()
            substrate.close()

        rebound_sub, rebound_journal = _open(root, boot="boot-example-2")
        try:
            restored_service = ProductSessionService(journal=rebound_journal)
            restored = restored_service.restore_from_journal()
            assert is_ok(restored)
            loaded = restored_service.get("psess:desk-1")
            assert is_ok(loaded)
            assert loaded.value.context.as_of == _AS_OF
            queried = restored_service.reconnect(
                "psess:desk-1",
                resume_cursor=loaded.value.resume_cursor,
                cursor_generation=loaded.value.cursor_generation,
            )
            assert is_ok(queried)
            assert queried.value.kind == RECONNECT_KIND_QUERY
            minted_tab = restored_service.open_tab(
                tab_id="tab-c",
                app_instance_id="inst:missing",
            )
            assert is_refusal(minted_tab)
            print("restart restored bound context from the journal; a new tab did not mint")
        finally:
            rebound_journal.close()
            rebound_sub.close()


if __name__ == "__main__":
    main()
