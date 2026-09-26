"""Reference usage — registry-enumeration autocomplete (Story 16.4).

Executable::

    python qmb/examples/cli_autocomplete_usage.py

Shows the things Story 16.4 / B-1 / B-15 / AR-55 pin down:

1. Autocomplete enumerates registry state through the one library-owned
   registry-read port — never a door-side or second cache.
2. Resolution and autocomplete read the same as-of set, so they can never
   offer different answers.
3. A newly created Book reaches the CLI as a fresher as-of set — never as a
   door cache refresh or a live service query.
4. Wiring uses click's native ``shell_complete`` / ``ShellComplete``, not
   bespoke completion machinery.
"""

from __future__ import annotations

from typing import TypeVar

from click.shell_completion import ShellComplete
from qmb.config import BOOK_RECORD_KIND
from qmb.doors import CLI_PROG
from qmb.doors.cli import AUTOCOMPLETE, HOLDS_CACHE, complete_registry, main
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmf.core.chrono import Instant, WriterId
from qmf.core.refusal import Result, is_ok
from qmf.registry import RegistrationRecord

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _record(alias: str, machine: str) -> RegistrationRecord:
    writer = _unwrap(
        WriterId.try_create(machine, "authoring", BOOK_RECORD_KIND, "boot-1"),
        "writer",
    )
    return _unwrap(
        RegistrationRecord.try_create(
            BOOK_RECORD_KIND,
            1,
            [],
            {"alias": alias, "note": alias},
            writer,
            0,
            _instant(),
        ),
        "record",
    )


def _pointer(alias: str, target: object, dated_at: Instant) -> DatedPointer:
    return _unwrap(DatedPointer.try_create(alias, target, dated_at), "pointer")


def _as_of(
    ns: int,
    records: tuple[RegistrationRecord, ...],
    pointers: tuple[DatedPointer, ...],
) -> AsOfSet:
    return _unwrap(
        AsOfSet.try_create(_instant(ns), records=records, pointers=pointers),
        "as-of set",
    )


def _port(hub: PassiveHub) -> RegistryReadPort:
    return _unwrap(
        RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY),
        "port",
    )


def enumerate_through_the_one_port() -> RegistryReadPort:
    book = _record("scalping", "node-a")
    as_of = _as_of(
        _CREATED_NS,
        (book,),
        (_pointer("scalping", book.stable_id, _instant()),),
    )
    port = _port(_unwrap(PassiveHub.try_create((as_of,)), "hub"))
    offered = complete_registry(port, kind=BOOK_RECORD_KIND)
    resolved = _unwrap(port.resolve("scalping"), "resolve scalping")
    assert [item.value for item in offered] == ["scalping"]
    assert offered[0].cite() == resolved.cite() == book.stable_id.value
    assert HOLDS_CACHE is False
    print("autocomplete enumerates through the one registry-read port")
    print("same answers as resolve: " + offered[0].cite())
    return port


def new_book_is_a_fresher_as_of_set(port: RegistryReadPort) -> None:
    swing = _record("swing", "node-b")
    existing = port.bound.records[0]
    dated = _instant(_CREATED_NS + 1)
    newer = _as_of(
        _CREATED_NS + 1,
        (existing, swing),
        (
            _pointer("scalping", existing.stable_id, dated),
            _pointer("swing", swing.stable_id, dated),
        ),
    )
    grown = _unwrap(port.hub.with_set(newer), "fresher hub")
    fresh = _port(grown)
    old_names = [item.value for item in complete_registry(port, kind=BOOK_RECORD_KIND)]
    new_names = [item.value for item in complete_registry(fresh, kind=BOOK_RECORD_KIND)]
    assert old_names == ["scalping"]
    assert new_names == ["scalping", "swing"]
    print("new Book arrives as a fresher as-of set")
    print("never a door cache refresh")


def click_native_shell_complete() -> None:
    book = _record("scalping", "node-a")
    as_of = _as_of(
        _CREATED_NS,
        (book,),
        (_pointer("scalping", book.stable_id, _instant()),),
    )
    port = _port(_unwrap(PassiveHub.try_create((as_of,)), "hub"))
    engine = ShellComplete(main, {"obj": {"port": port}}, CLI_PROG, "_QMB_COMPLETE")
    items = engine.get_completions(["backtest", "run", "--book"], "sca")
    assert [item.value for item in items] == ["scalping"]
    assert AUTOCOMPLETE == "click.shell_complete"
    assert complete_registry(None) == ()
    print("click native shell_complete")
    print("missing port yields no candidates, not a live query")


def main_example() -> None:
    bound = enumerate_through_the_one_port()
    new_book_is_a_fresher_as_of_set(bound)
    click_native_shell_complete()
    print("qmb CLI registry autocomplete ok")


if __name__ == "__main__":
    main_example()
