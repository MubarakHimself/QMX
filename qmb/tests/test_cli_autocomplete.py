"""Story 16.4 — registry-enumeration autocomplete through the B-15 port."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

import click
from click.shell_completion import CompletionItem, ShellComplete
from click.testing import CliRunner
from qmb.config import BMS_RECORD_KIND, BOOK_RECORD_KIND
from qmb.doors import CLI_PROG
from qmb.doors.cli import (
    AUTOCOMPLETE,
    AUTOCOMPLETE_PORT,
    BOT_RECORD_KIND,
    HOLDS_CACHE,
    cli_tree_identity,
    complete_registry,
    main,
)
from qmb.registryread import (
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryFragment,
    RegistryReadPort,
    SupersedesRef,
)
from qmf.core.chrono import Instant, WriterId
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_QMB_ROOT = Path(__file__).resolve().parents[1]
_CLI_SRC = _QMB_ROOT / "src" / "qmb" / "doors" / "cli"
_SEVERITY = "workspace-declared"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(machine: str, kind: str) -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", kind, "boot-1"))


def _record(*, kind: str, alias: str, machine: str, note: str | None = None) -> RegistrationRecord:
    return _ok(
        RegistrationRecord.try_create(
            kind,
            1,
            [],
            {"alias": alias, "note": note if note is not None else alias},
            _writer(machine, kind),
            0,
            _instant(),
        )
    )


def _pointer(alias: str, target: object, dated_at: Instant | None = None) -> DatedPointer:
    return _ok(DatedPointer.try_create(alias, target, dated_at or _instant()))


def _as_of(
    instant: Instant,
    records: tuple[RegistrationRecord, ...],
    *,
    pointers: tuple[DatedPointer, ...] = (),
    supersedes: tuple[SupersedesRef, ...] = (),
) -> AsOfSet:
    return _ok(
        AsOfSet.try_create(
            instant,
            records=records,
            pointers=pointers,
            supersedes=supersedes,
        )
    )


def _port(
    hub: PassiveHub,
    *,
    bound: AsOfSet | None = None,
    frozen: bool = False,
) -> RegistryReadPort:
    return _ok(
        RegistryReadPort.try_create(
            hub,
            stale_evidence_severity=_SEVERITY,
            bound=bound,
            frozen=frozen,
        )
    )


def _populated_port() -> tuple[RegistryReadPort, dict[str, RegistrationRecord]]:
    book = _record(kind=BOOK_RECORD_KIND, alias="scalping", machine="node-a")
    swing = _record(kind=BOOK_RECORD_KIND, alias="swing", machine="node-b")
    bms = _record(kind=BMS_RECORD_KIND, alias="accounting-core", machine="node-c")
    bot = _record(kind=BOT_RECORD_KIND, alias="mean-reversion", machine="node-d")
    as_of = _as_of(
        _instant(),
        (book, swing, bms, bot),
        pointers=(
            _pointer("scalping", book.stable_id),
            _pointer("swing", swing.stable_id),
            _pointer("accounting-core", bms.stable_id),
            _pointer("mean-reversion", bot.stable_id),
        ),
    )
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    return port, {"book": book, "swing": swing, "bms": bms, "bot": bot}


def _click_complete(
    port: RegistryReadPort,
    args: list[str],
    incomplete: str,
) -> list[CompletionItem[str]]:
    engine = ShellComplete(main, {"obj": {"port": port}}, CLI_PROG, "_QMB_COMPLETE")
    return engine.get_completions(args, incomplete)


def test_identity_names_click_native_autocomplete_over_the_b15_port() -> None:
    identity = cli_tree_identity()
    assert identity["autocomplete"] == AUTOCOMPLETE == "click.shell_complete"
    assert identity["autocomplete_port"] == AUTOCOMPLETE_PORT == "qmb.registryread"
    assert identity["holds_cache"] is HOLDS_CACHE is False
    assert "snapshot" not in str(identity).lower()


def test_complete_registry_enumerates_through_the_one_port() -> None:
    port, records = _populated_port()
    books = complete_registry(port, kind=BOOK_RECORD_KIND)
    assert [item.value for item in books] == ["scalping", "swing"]
    assert books[0].cite() == records["book"].stable_id.value
    assert books[1].cite() == records["swing"].stable_id.value
    assert books[0].kind == BOOK_RECORD_KIND
    assert books[0].set_fingerprint == port.bound.fingerprint
    assert books[0].registry_as_of == port.bound.registry_as_of
    bms = complete_registry(port, kind=BMS_RECORD_KIND)
    assert [item.value for item in bms] == ["accounting-core"]
    bots = complete_registry(port, kind=BOT_RECORD_KIND)
    assert [item.value for item in bots] == ["mean-reversion"]


def test_autocomplete_and_resolve_never_answer_differently() -> None:
    port, _records = _populated_port()
    offered = complete_registry(port)
    assert [item.value for item in offered] == [
        "accounting-core",
        "mean-reversion",
        "scalping",
        "swing",
    ]
    for item in offered:
        resolved = port.resolve(item.value)
        assert is_ok(resolved)
        assert resolved.value.cite() == item.cite()
        assert resolved.value.set_fingerprint == item.set_fingerprint
        assert resolved.value.registry_as_of == item.registry_as_of
    aliases = {pointer.alias for pointer in port.enumerate_aliases()}
    assert aliases == {item.value for item in offered}


def test_prefix_filters_without_a_door_side_list() -> None:
    port, _records = _populated_port()
    assert [item.value for item in complete_registry(port, "sca", kind=BOOK_RECORD_KIND)] == [
        "scalping"
    ]
    assert [item.value for item in complete_registry(port, "sw", kind=BOOK_RECORD_KIND)] == [
        "swing"
    ]
    assert complete_registry(port, "nope", kind=BOOK_RECORD_KIND) == ()
    assert complete_registry(port, "sca", kind=BMS_RECORD_KIND) == ()


def test_missing_port_yields_no_candidates_not_a_live_query() -> None:
    assert complete_registry(None) == ()
    assert complete_registry("not-a-port") == ()
    assert complete_registry({}, kind=BOOK_RECORD_KIND) == ()
    assert complete_registry(None, "sca") == ()


def test_blank_kind_and_non_string_incomplete_yield_nothing() -> None:
    port, _records = _populated_port()
    assert complete_registry(port, kind="  ") == ()
    assert complete_registry(port, 1) == ()
    assert [item.value for item in complete_registry(port, None, kind=BOOK_RECORD_KIND)] == [
        "scalping",
        "swing",
    ]


def test_stale_alias_is_not_offered() -> None:
    first = _record(kind=BOOK_RECORD_KIND, alias="scalping", machine="node-a", note="v1")
    second = _record(kind=BOOK_RECORD_KIND, alias="scalping", machine="node-b", note="v2")
    older = _as_of(
        _instant(_CREATED_NS),
        (first,),
        pointers=(_pointer("scalping", first.stable_id, _instant(_CREATED_NS)),),
    )
    newer = _as_of(
        _instant(_CREATED_NS + 1),
        (first, second),
        pointers=(_pointer("scalping", second.stable_id, _instant(_CREATED_NS + 1)),),
        supersedes=(_ok(SupersedesRef.try_create(second.stable_id, first.stable_id)),),
    )
    hub = _ok(PassiveHub.try_create((older, newer)))
    current = _port(hub)
    live = complete_registry(current, kind=BOOK_RECORD_KIND)
    assert [item.value for item in live] == ["scalping"]
    assert live[0].cite() == second.stable_id.value
    assert _ok(current.resolve("scalping")).cite() == live[0].cite()
    bound_old = _port(hub, bound=older)
    assert is_refusal(bound_old.resolve("scalping"))
    assert complete_registry(bound_old, kind=BOOK_RECORD_KIND) == ()


def test_new_book_arrives_as_a_fresher_as_of_set() -> None:
    first = _record(kind=BOOK_RECORD_KIND, alias="scalping", machine="node-a")
    older = _as_of(
        _instant(_CREATED_NS),
        (first,),
        pointers=(_pointer("scalping", first.stable_id, _instant(_CREATED_NS)),),
    )
    hub = _ok(PassiveHub.try_create((older,)))
    bound = _port(hub)
    assert [item.value for item in complete_registry(bound, kind=BOOK_RECORD_KIND)] == ["scalping"]
    swing = _record(kind=BOOK_RECORD_KIND, alias="swing", machine="node-b")
    newer = _as_of(
        _instant(_CREATED_NS + 1),
        (first, swing),
        pointers=(
            _pointer("scalping", first.stable_id, _instant(_CREATED_NS + 1)),
            _pointer("swing", swing.stable_id, _instant(_CREATED_NS + 1)),
        ),
    )
    grown = _ok(hub.with_set(newer))
    fresh = _port(grown)
    assert [item.value for item in complete_registry(fresh, kind=BOOK_RECORD_KIND)] == [
        "scalping",
        "swing",
    ]
    assert fresh.bound.fingerprint == newer.fingerprint
    assert bound.bound.fingerprint == older.fingerprint
    assert [item.value for item in complete_registry(bound, kind=BOOK_RECORD_KIND)] == ["scalping"]
    compiler = _ok(fresh.resolve("swing"))
    offered = complete_registry(fresh, "sw", kind=BOOK_RECORD_KIND)
    assert len(offered) == 1
    assert offered[0].cite() == compiler.cite() == swing.stable_id.value


def test_frozen_port_completes_explicit_fp1_never_alias() -> None:
    port, records = _populated_port()
    admitted = port.admit_batch()
    assert admitted.frozen is True
    assert complete_registry(admitted, "sca", kind=BOOK_RECORD_KIND) == ()
    assert is_refusal(admitted.resolve("scalping"))
    fingerprints = complete_registry(admitted, kind=BOOK_RECORD_KIND)
    values = {item.value for item in fingerprints}
    assert records["book"].stable_id.value in values
    assert records["swing"].stable_id.value in values
    assert "scalping" not in values
    for item in fingerprints:
        assert item.value.startswith("fp1:sha256:")
        resolved = admitted.resolve(item.value)
        assert is_ok(resolved)
        assert resolved.value.cite() == item.cite()


def test_click_native_shell_complete_offers_book_bms_and_bot() -> None:
    port, records = _populated_port()
    books = _click_complete(port, ["backtest", "run", "--book"], "sca")
    assert [item.value for item in books] == ["scalping"]
    assert books[0].help == records["book"].stable_id.value
    bms = _click_complete(port, ["backtest", "run", "--bms"], "acc")
    assert [item.value for item in bms] == ["accounting-core"]
    bots = _click_complete(port, ["backtest", "run"], "mean")
    assert [item.value for item in bots] == ["mean-reversion"]
    opt_bots = _click_complete(port, ["optimize", "run"], "mean")
    assert [item.value for item in opt_bots] == ["mean-reversion"]
    empty = _click_complete(port, ["backtest", "run", "--book"], "zzz")
    assert empty == []


def test_fragment_pointer_follows_source_kind() -> None:
    book = _record(kind=BOOK_RECORD_KIND, alias="scalping", machine="node-a")
    fragment = _ok(RegistryFragment.try_create(book.stable_id, {"preset": "stress-spread"}))
    as_of = _ok(
        AsOfSet.try_create(
            _instant(),
            records=(book,),
            fragments=(fragment,),
            pointers=(
                _pointer("scalping", book.stable_id),
                _pointer("stress-spread", fragment.fingerprint),
            ),
        )
    )
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    books = complete_registry(port, kind=BOOK_RECORD_KIND)
    assert [item.value for item in books] == ["scalping", "stress-spread"]
    assert books[1].cite() == fragment.fingerprint.value
    frozen = complete_registry(port.admit_batch(), kind=BOOK_RECORD_KIND)
    values = {item.value for item in frozen}
    assert book.stable_id.value in values
    assert fragment.fingerprint.value in values


def test_click_obj_may_be_the_port_itself() -> None:
    port, _records = _populated_port()
    engine = ShellComplete(main, {"obj": port}, CLI_PROG, "_QMB_COMPLETE")
    items = engine.get_completions(["backtest", "run", "--book"], "sca")
    assert [item.value for item in items] == ["scalping"]


def test_click_complete_without_port_is_empty_not_a_service_query() -> None:
    engine = ShellComplete(main, {"obj": {}}, CLI_PROG, "_QMB_COMPLETE")
    assert engine.get_completions(["backtest", "run", "--book"], "sca") == []


def test_cli_runner_bash_complete_uses_click_native_protocol() -> None:
    port, _records = _populated_port()
    runner = CliRunner()
    result = runner.invoke(
        main,
        obj={"port": port},
        env={
            "_QMB_COMPLETE": "bash_complete",
            "COMP_WORDS": "qmb backtest run --book sca",
            "COMP_CWORD": "4",
        },
    )
    assert result.exit_code == 0, result.output
    assert "scalping" in result.output
    assert "swing" not in result.output


def test_options_wire_click_shell_complete_not_deprecated_autocompletion() -> None:
    backtest = main.commands["backtest"]
    assert isinstance(backtest, click.Group)
    run_cmd = backtest.commands["run"]
    opts = {opt for param in run_cmd.params for opt in param.opts}
    assert "--book" in opts
    assert "--bms" in opts
    source = (_CLI_SRC / "__init__.py").read_text(encoding="utf-8")
    assert "shell_complete=" in source
    assert "autocompletion=" not in source
    assert "from click.shell_completion import CompletionItem" in source


def test_cli_door_adds_no_bespoke_completion_machinery() -> None:
    offenders: list[str] = []
    for path in sorted(_CLI_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "COMP_WORDS" in text or "COMP_CWORD" in text:
            offenders.append(f"{path.name}: COMP_WORDS")
        if "bash_completion" in text or "register_completion" in text:
            offenders.append(f"{path.name}: bespoke completion")
        if path.name != "__init__.py" and "import click" in text:
            offenders.append(f"{path.name}: click leak")
    assert offenders == []
    scripts = list(_CLI_SRC.rglob("*.sh")) + list(_CLI_SRC.rglob("*.bash"))
    assert scripts == []
    tree_source = (_CLI_SRC / "tree.py").read_text(encoding="utf-8")
    assert "import click" not in tree_source
    assert "from click" not in tree_source


def test_doors_do_not_construct_or_cache_registry_state() -> None:
    doors = _QMB_ROOT / "src" / "qmb" / "doors"
    offenders: list[str] = []
    for path in sorted(doors.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value = node.value
            if value is None:
                continue
            if isinstance(value, ast.Call) and _names_port_or_hub(value):
                offenders.append(str(path.relative_to(doors)))
            if isinstance(value, (ast.Dict, ast.List)) and _looks_like_alias_cache(node, value):
                offenders.append(f"{path.name}: module-level alias cache")
    assert offenders == []


def _names_port_or_hub(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id in {"RegistryReadPort", "PassiveHub", "AsOfSet"}
    if isinstance(func, ast.Attribute):
        return func.attr in {"try_create", "RegistryReadPort", "PassiveHub", "AsOfSet"}
    return False


def _looks_like_alias_cache(node: ast.Assign | ast.AnnAssign, value: ast.expr) -> bool:
    names: list[str] = []
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                names.append(target.id.lower())
    elif isinstance(node.target, ast.Name):
        names.append(node.target.id.lower())
    if not any("alias" in name or "cache" in name or "complet" in name for name in names):
        return False
    return isinstance(value, (ast.Dict, ast.List))
