"""Story 34.2 — Library search reads as-of, ledger merge, Experiment Ledger refs."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from click.testing import CliRunner
from qmb.doors import api
from qmb.doors.cli import command_tree, invoke_library_search, main
from qmb.ledger.line import LedgerLine
from qmb.registryread import (
    KIND_OWNER,
    LIBRARY_SEARCH_CLASS,
    LIBRARY_SEARCH_HOLDS_CACHE,
    LIBRARY_SEARCH_MINTS_CT32,
    LIBRARY_SEARCH_MINTS_EXPERIMENT_SPEC,
    LIBRARY_SEARCH_OCCUPANCY,
    LIBRARY_SEARCH_OPENS_FOURTH_STORE,
    LIBRARY_SEARCH_READS_STAGING,
    QUERY_SURFACES,
    STALE_EVIDENCE_SEVERITY_KEY,
    SURFACE_EXPERIMENT_LEDGER,
    SURFACE_LEDGER_MERGE,
    SURFACE_REGISTRY_AS_OF,
    AsOfSet,
    DatedPointer,
    ExperimentLedgerRef,
    LibraryHit,
    LibrarySearch,
    PassiveHub,
    RegistryReadPort,
    SavedViewCite,
    SupersedesRef,
    library_search_identity,
    search_library,
)
from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

import qmb

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_SEVERITY = "workspace-declared"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(machine: str, kind: str) -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", kind, "boot-1"))


def _record(*, kind: str, note: str, machine: str = "node-a") -> RegistrationRecord:
    return _ok(
        RegistrationRecord.try_create(
            kind,
            1,
            [],
            {"alias": note, "note": note},
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
    severity: str = _SEVERITY,
) -> RegistryReadPort:
    return _ok(
        RegistryReadPort.try_create(
            hub,
            stale_evidence_severity=severity,
            bound=bound,
            frozen=frozen,
        )
    )


def _fp(*parts: object) -> Fingerprint:
    return _ok(fingerprint({"parts": list(parts)}))


def _line(ct32: Fingerprint, *, run: str = "run-a") -> LedgerLine:
    return LedgerLine(
        run_id=_ok(fingerprint({"run": run})),
        role="confirmation",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value},
        book_bar_fp1=_ok(fingerprint({"bar": run})),
        measures=(),
        ct32_fingerprint=ct32,
    )


class _FakeExperimentLedger:
    """Injected Story 46.3 reader. Not a store QMB opens."""

    def __init__(self, refs: tuple[ExperimentLedgerRef, ...]) -> None:
        self._refs = refs

    def refs(self) -> tuple[ExperimentLedgerRef, ...]:
        return self._refs


def test_search_reads_exactly_the_three_surfaces() -> None:
    identity = library_search_identity()
    assert identity["surfaces"] == list(QUERY_SURFACES)
    assert QUERY_SURFACES == (
        SURFACE_REGISTRY_AS_OF,
        SURFACE_LEDGER_MERGE,
        SURFACE_EXPERIMENT_LEDGER,
    )
    assert identity["opens_fourth_store"] is LIBRARY_SEARCH_OPENS_FOURTH_STORE is False
    assert identity["reads_staging"] is LIBRARY_SEARCH_READS_STAGING is False
    assert identity["holds_cache"] is LIBRARY_SEARCH_HOLDS_CACHE is False
    assert identity["occupancy"] == LIBRARY_SEARCH_OCCUPANCY == "query"
    assert identity["mints_ct32"] is LIBRARY_SEARCH_MINTS_CT32 is False
    assert identity["mints_experiment_spec"] is LIBRARY_SEARCH_MINTS_EXPERIMENT_SPEC is False
    assert identity["owner"] == KIND_OWNER
    assert identity["class"] == LIBRARY_SEARCH_CLASS
    assert qmb.__version__ not in identity.values()
    stamped = fingerprint(identity)
    assert is_ok(stamped)


def test_search_by_kind_and_fp1_folds_all_three_surfaces() -> None:
    bot = _record(kind="bot-definition", note="scalping")
    result = _record(kind="performance-result", note="run-a", machine="node-b")
    spec = _record(kind="experiment-spec", note="exp-a", machine="node-c")
    as_of = _as_of(
        _instant(),
        (bot, result, spec),
        pointers=(
            _pointer("scalping", bot.stable_id),
            _pointer("run-a", result.stable_id),
            _pointer("exp-a", spec.stable_id),
        ),
    )
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    line = _line(result.stable_id, run="run-a")
    exp_ref = _ok(
        ExperimentLedgerRef.try_create(
            "experiment-ledger:" + spec.stable_id.value,
            spec.stable_id,
            cited_fp1=result.stable_id,
            kind="performance-result",
        )
    )
    found = _ok(
        search_library(
            "performance-result",
            fp1=result.stable_id,
            port=port,
            ledger_lines=(line,),
            world=World.REPLAY,
            role="confirmation",
            experiment_refs=_FakeExperimentLedger((exp_ref,)),
        )
    )
    assert isinstance(found, LibrarySearch)
    assert found.kind == "performance-result"
    assert found.surfaces == QUERY_SURFACES
    assert found.opens_fourth_store is False
    assert found.reads_staging is False
    assert found.holds_cache is False
    surfaces = {hit.surface for hit in found.hits}
    assert surfaces == {
        SURFACE_REGISTRY_AS_OF,
        SURFACE_LEDGER_MERGE,
        SURFACE_EXPERIMENT_LEDGER,
    }
    for hit in found.hits:
        assert isinstance(hit, LibraryHit)
        assert hit.cite() == result.stable_id.value
        assert hit.is_registry_kind is True


def test_as_of_alias_and_frozen_fingerprint_resolution_still_hold() -> None:
    record = _record(kind="book-definition", note="scalping")
    as_of = _as_of(_instant(), (record,), pointers=(_pointer("scalping", record.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    by_alias = _ok(search_library("book-definition", fp1="scalping", port=port))
    assert by_alias.hits[0].cite() == record.stable_id.value
    banned = search_library("book-definition", fp1="scalping@1", port=port)
    assert is_refusal(banned)
    assert banned.category is RefusalCategory.INVALID_INPUT
    frozen = port.admit_batch()
    assert frozen.frozen is True
    alias = search_library("book-definition", fp1="scalping", port=frozen)
    assert is_refusal(alias)
    assert alias.category is RefusalCategory.INVALID_INPUT
    by_fp = _ok(search_library("book-definition", fp1=record.stable_id, port=frozen))
    assert by_fp.hits[0].cite() == record.stable_id.value


def test_stale_as_of_resolution_is_returned_not_raised() -> None:
    first = _record(kind="book-definition", note="v1")
    second = _record(kind="book-definition", note="v2", machine="node-b")
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
    stale = search_library("book-definition", fp1=first.stable_id, port=current)
    assert is_refusal(stale)
    assert stale.category is RefusalCategory.STALE_EVIDENCE
    assert stale.context["severity_key"] == STALE_EVIDENCE_SEVERITY_KEY
    live = _ok(search_library("book-definition", fp1="scalping", port=current))
    assert live.hits[0].cite() == second.stable_id.value


def test_saved_view_hit_cites_source_fp1_not_a_registry_kind() -> None:
    ct32 = _fp("ct32", "view-source")
    line = _line(ct32, run="viewed")
    cite = _ok(SavedViewCite.try_create(ct32))
    found = _ok(
        search_library(
            "saved-view",
            saved_views=(cite,),
            ledger_lines=(line,),
            world=World.REPLAY,
        )
    )
    assert found.is_registry_kind is False
    assert found.kind == "saved-view"
    assert len(found.hits) == 1
    hit = found.hits[0]
    assert hit.cite() == ct32.value
    assert hit.is_registry_kind is False
    assert hit.source_fp1 is not None and hit.source_fp1.value == ct32.value
    assert hit.surface == SURFACE_LEDGER_MERGE
    json_fp = _fp("saved-view-json")
    with_json = _ok(SavedViewCite.try_create(ct32, view_fp1=json_fp, kind="analysis.published"))
    published = _ok(search_library("analysis-publication", saved_views=(with_json,)))
    assert published.hits[0].cite() == json_fp.value
    assert published.hits[0].is_registry_kind is False
    assert published.hits[0].source_fp1 is not None
    assert published.hits[0].source_fp1.value == ct32.value


def test_staging_is_not_read_and_cannot_fold_into_library() -> None:
    bot = _record(kind="bot-definition", note="scalping")
    as_of = _as_of(_instant(), (bot,), pointers=(_pointer("scalping", bot.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    folded = search_library(
        "bot-definition",
        port=port,
        staging=({"kind": "refinement-proposal", "body": "candidate"},),
    )
    assert is_refusal(folded)
    assert folded.category is RefusalCategory.POLICY_REJECTION
    assert folded.context["reads_staging"] is False
    surfaces = folded.context["surfaces"]
    assert isinstance(surfaces, tuple)
    assert surfaces == QUERY_SURFACES
    kind = search_library("staging", port=port)
    assert is_refusal(kind)
    assert kind.context["is_library_kind"] is False
    found = _ok(search_library("bot-definition", port=port))
    assert "staging" not in found.surfaces
    assert found.reads_staging is False


def test_fourth_store_is_refused() -> None:
    refused = search_library("bot-definition", store="library.sqlite")
    assert is_refusal(refused)
    assert refused.context["opens_fourth_store"] is False
    sqlite = search_library("bot-definition", sqlite=True)
    assert is_refusal(sqlite)
    assert sqlite.context["field"] == "sqlite"


def test_experiment_spec_is_coordinated_and_refs_are_not_a_store() -> None:
    spec = _record(kind="experiment-spec", note="exp-a")
    as_of = _as_of(_instant(), (spec,), pointers=(_pointer("exp-a", spec.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    ref = _ok(
        ExperimentLedgerRef.try_create(
            "experiment-ledger:" + spec.stable_id.value,
            spec.stable_id,
        )
    )
    found = _ok(
        search_library(
            "experiment-spec",
            lane="coordinated",
            port=port,
            experiment_refs=(ref,),
        )
    )
    surfaces = {hit.surface for hit in found.hits}
    assert SURFACE_REGISTRY_AS_OF in surfaces
    assert SURFACE_EXPERIMENT_LEDGER in surfaces
    governed = search_library("experiment-spec", lane="governed", port=port)
    assert is_refusal(governed)
    uncoordinated = ExperimentLedgerRef.try_create(
        "experiment-ledger:x",
        spec.stable_id,
        workbench_lane="governed",
    )
    assert is_refusal(uncoordinated)


def test_module_does_not_read_qma_staging_or_open_a_store() -> None:
    source = (_SRC / "registryread" / "search.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".", 1)[0])
    assert "qma" not in imported
    assert "sqlite3" not in imported
    assert "qmx-agents" not in source


def test_cli_and_api_search_the_same_fold() -> None:
    bot = _record(kind="bot-definition", note="scalping")
    as_of = _as_of(_instant(), (bot,), pointers=(_pointer("scalping", bot.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    via_door = _ok(invoke_library_search(kind="bot-definition", fp1="scalping", port=port))
    via_lib = _ok(api.search_library("bot-definition", fp1="scalping", port=port))
    assert via_door.hits[0].cite() == via_lib.hits[0].cite() == bot.stable_id.value
    assert api.search_library is qmb.search_library
    assert api.library_search_identity is qmb.library_search_identity
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["library", "search", "--kind", "bot-definition", "--fp1", "scalping"],
        obj={"port": port},
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    assert bot.stable_id.value in clicked.stdout
    assert SURFACE_REGISTRY_AS_OF in clicked.stdout
    helped = runner.invoke(main, ["library", "--help"])
    assert helped.exit_code == 0, helped.output
    assert "search" in helped.output
    assert command_tree()["library"] == ("kinds", "search", "candidates")
    staging = runner.invoke(
        main,
        ["library", "search", "--kind", "bot-definition", "--staging"],
        obj={"port": port},
    )
    assert staging.exit_code != 0
    store = runner.invoke(
        main,
        ["library", "search", "--kind", "bot-definition", "--store", "library.sqlite"],
        obj={"port": port},
    )
    assert store.exit_code != 0
