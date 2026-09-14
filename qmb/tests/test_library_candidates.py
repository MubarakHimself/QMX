"""Story 34.3 — candidate retain / filter / rank is a query, not a copied-row DB."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import TypeVar

from click.testing import CliRunner
from qmb.doors import api
from qmb.doors.cli import command_tree, invoke_library_candidates, invoke_sweep_rank, main
from qmb.ledger.line import LedgerLine
from qmb.registryread import (
    CANDIDATE_SET_CLASS,
    CANDIDATE_SET_OCCUPANCY,
    DEC_0084_DEAD,
    HOME_GOVERNED,
    HOME_UNGOVERNED,
    KIND_OWNER,
    QUERY_SURFACES,
    SAVED_VIEW_CLASS,
    SAVED_VIEW_FILENAME,
    SAVED_VIEW_METHOD,
    SURFACE_EXPERIMENT_LEDGER,
    SURFACE_LEDGER_MERGE,
    SURFACE_REGISTRY_AS_OF,
    ZONE_DEV,
    AsOfSet,
    CandidateSet,
    DatedPointer,
    ExperimentLedgerRef,
    PassiveHub,
    RegistryReadPort,
    SavedCandidateView,
    candidate_set_identity,
    query_candidates,
    save_candidate_view,
)
from qmb.results import emit_measure
from qmb.sweep import SweepRanking, rank_sweep
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import RegistrationRecord

import qmb

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"
_SEVERITY = "workspace-declared"
_SWEEP = fingerprint({"class": "sweep", "id": "candidate-sweep"})
_BAR = fingerprint({"class": "book-bar", "id": "candidate-bar"})
_BAR_SPEC = {"kind": "time-interval", "seconds": 60}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(machine: str, kind: str) -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", kind, "boot-1"))


def _record(
    *,
    kind: str,
    note: str,
    machine: str = "node-a",
    zone: str | None = None,
    origin: str | None = None,
) -> RegistrationRecord:
    body: dict[str, object] = {"alias": note, "note": note}
    if zone is not None:
        body["zone"] = zone
    if origin is not None:
        body["origin"] = origin
    return _ok(
        RegistrationRecord.try_create(
            kind,
            1,
            [],
            body,
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
) -> AsOfSet:
    return _ok(AsOfSet.try_create(instant, records=records, pointers=pointers))


def _port(hub: PassiveHub) -> RegistryReadPort:
    return _ok(
        RegistryReadPort.try_create(
            hub,
            stale_evidence_severity=_SEVERITY,
        )
    )


def _fp(*parts: object) -> Fingerprint:
    return _ok(fingerprint({"parts": list(parts)}))


def _sweep_id() -> Fingerprint:
    return _ok(_SWEEP)


def _coordinates(sweep_id: Fingerprint, run: str) -> dict[str, object]:
    return {
        "bar_spec": _BAR_SPEC,
        "class": "qmb-sweep-coordinates",
        "format_version": 1,
        "instrument": "EURUSD",
        "param_hash": _fp("param", run).value,
        "sweep_id": sweep_id.value,
    }


def _net_profit(minor: int) -> dict[str, object]:
    quantity = Money(value=minor, currency="USD", scale=2)
    return _ok(emit_measure("net_profit", quantity)).fp1_identity()


def _completed(run: str, *, sweep_id: Fingerprint, minor: int, ct32: Fingerprint) -> LedgerLine:
    return LedgerLine(
        run_id=_fp("run", run),
        role="confirmation",
        world=World.REPLAY,
        result_label={"class": "result-label", "world": World.REPLAY.value, "run": run},
        book_bar_fp1=_ok(_BAR),
        measures=(_net_profit(minor),),
        ct32_fingerprint=ct32,
        sweep_coordinates=_coordinates(sweep_id, run),
    )


class _FakeExperimentLedger:
    def __init__(self, refs: tuple[ExperimentLedgerRef, ...]) -> None:
        self._refs = refs

    def refs(self) -> tuple[ExperimentLedgerRef, ...]:
        return self._refs


def test_candidate_set_is_a_query_over_the_three_surfaces() -> None:
    identity = candidate_set_identity()
    assert identity["surfaces"] == list(QUERY_SURFACES)
    assert QUERY_SURFACES == (
        SURFACE_REGISTRY_AS_OF,
        SURFACE_LEDGER_MERGE,
        SURFACE_EXPERIMENT_LEDGER,
    )
    assert identity["occupancy"] == CANDIDATE_SET_OCCUPANCY == "query"
    assert identity["reads_staging"] is False
    assert identity["persists_copied_rows"] is False
    assert identity["opens_sqlite"] is False
    assert identity["mints_registry_kind"] is False
    assert identity["dec_0084_dead"] is DEC_0084_DEAD is True
    assert identity["rank"] == "sweep.rank"
    assert identity["owner"] == KIND_OWNER
    assert identity["class"] == CANDIDATE_SET_CLASS
    assert qmb.__version__ not in identity.values()
    stamped = fingerprint(identity)
    assert is_ok(stamped)


def test_query_includes_dev_zone_library_kinds_ledger_and_experiment_refs() -> None:
    live = _record(kind="bot-definition", note="live-bot", zone="live")
    dev = _record(
        kind="bot-definition",
        note="dev-bot",
        machine="node-b",
        zone="dev",
        origin="qma-strategy-handle",
    )
    result = _record(kind="performance-result", note="run-a", machine="node-c")
    spec = _record(kind="experiment-spec", note="exp-a", machine="node-d")
    as_of = _as_of(
        _instant(),
        (live, dev, result, spec),
        pointers=(
            _pointer("live-bot", live.stable_id),
            _pointer("dev-bot", dev.stable_id),
            _pointer("run-a", result.stable_id),
            _pointer("exp-a", spec.stable_id),
        ),
    )
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    line = _completed("c1", sweep_id=_sweep_id(), minor=3000, ct32=result.stable_id)
    exp_ref = _ok(
        ExperimentLedgerRef.try_create(
            "experiment-ledger:" + spec.stable_id.value,
            spec.stable_id,
            cited_fp1=result.stable_id,
            kind="performance-result",
        )
    )
    found = _ok(
        query_candidates(
            port=port,
            ledger_lines=(line,),
            world=World.REPLAY,
            role="confirmation",
            experiment_refs=_FakeExperimentLedger((exp_ref,)),
            lane="coordinated",
        )
    )
    assert isinstance(found, CandidateSet)
    assert found.occupancy == "query"
    assert found.persists_copied_rows is False
    assert found.reads_staging is False
    assert found.opens_sqlite is False
    assert found.mints_registry_kind is False
    surfaces = {item.surface for item in found.candidates}
    assert surfaces == {
        SURFACE_REGISTRY_AS_OF,
        SURFACE_LEDGER_MERGE,
        SURFACE_EXPERIMENT_LEDGER,
    }
    zones = {item.zone for item in found.candidates if item.surface == SURFACE_REGISTRY_AS_OF}
    assert ZONE_DEV in zones
    cites = {item.cite() for item in found.candidates}
    assert dev.stable_id.value in cites
    assert live.stable_id.value in cites
    assert result.stable_id.value in cites
    filtered = _ok(query_candidates(port=port, zone="dev"))
    assert all(item.zone == ZONE_DEV for item in filtered.candidates)
    assert {item.cite() for item in filtered.candidates} == {dev.stable_id.value}


def test_sweep_rank_is_the_candidate_set_rank_and_publishes_no_copied_row() -> None:
    result = _record(kind="performance-result", note="run-a")
    as_of = _as_of(_instant(), (result,), pointers=(_pointer("run-a", result.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    sweep_id = _sweep_id()
    lines = [
        _completed("c1", sweep_id=sweep_id, minor=3000, ct32=_fp("ct32", "c1")),
        _completed("c2", sweep_id=sweep_id, minor=1000, ct32=_fp("ct32", "c2")),
        _completed("c3", sweep_id=sweep_id, minor=2000, ct32=_fp("ct32", "c3")),
    ]
    library = _ok(rank_sweep(lines, sweep_id=sweep_id, objective="net_profit", world=World.REPLAY))
    view = _ok(
        query_candidates(
            port=port,
            ledger_lines=lines,
            world=World.REPLAY,
            sweep_id=sweep_id,
            objective="net_profit",
        )
    )
    assert view.rank_is_sweep_rank is True
    assert view.ranking is not None
    assert isinstance(view.ranking, SweepRanking)
    assert view.ranking.fp1_identity() == library.fp1_identity()
    assert view.ranking.publishes_never_acts is True
    assert view.ranking.adds_computation is False
    assert view.persists_copied_rows is False
    identity = qmb.sweep_rank_identity()
    assert identity["candidate_set_view"] is True
    assert identity["publishes_copied_row_artifact"] is False
    door = invoke_sweep_rank(
        lines=lines,
        sweep_id=sweep_id,
        objective="net_profit",
        world=World.REPLAY,
        persist=True,
    )
    assert is_refusal(door)
    assert door.context["occupancy"] == "query"


def test_ungoverned_save_is_a_return_value_and_citation_without_body_is_refused() -> None:
    bot = _record(kind="bot-definition", note="scalping", zone="dev", origin="qma")
    as_of = _as_of(_instant(), (bot,), pointers=(_pointer("scalping", bot.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    found = _ok(query_candidates(kind="bot-definition", port=port))
    saved = _ok(save_candidate_view(found, home="ungoverned"))
    assert isinstance(saved, SavedCandidateView)
    assert saved.home == HOME_UNGOVERNED
    assert saved.durable is False
    assert saved.is_library_object is False
    assert saved.path is None
    assert saved.body["method"] == SAVED_VIEW_METHOD
    assert saved.body["class"] == SAVED_VIEW_CLASS
    cites = saved.body["cites"]
    assert isinstance(cites, list)
    assert bot.stable_id.value in cites
    assert "note" not in json.dumps(saved.body)
    cited = save_candidate_view(home="ungoverned", cite=bot.stable_id, body=None)
    assert is_refusal(cited)
    assert cited.category is RefusalCategory.POLICY_REJECTION
    assert "citation without a body" in str(cited.context["reason"])
    empty = save_candidate_view(home="ungoverned", body={})
    assert is_refusal(empty)


def test_governed_home_writes_json_sidecar_in_source_run_dir(tmp_path: Path) -> None:
    bot = _record(kind="bot-definition", note="scalping", zone="dev")
    as_of = _as_of(_instant(), (bot,), pointers=(_pointer("scalping", bot.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    found = _ok(query_candidates(kind="bot-definition", port=port))
    saved = _ok(save_candidate_view(found, home="governed-without-qma", run_dir=tmp_path))
    assert saved.home == HOME_GOVERNED
    assert saved.durable is True
    assert saved.is_library_object is False
    sidecar = tmp_path / SAVED_VIEW_FILENAME
    assert sidecar.is_file()
    assert saved.path == str(sidecar)
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    assert payload["method"] == SAVED_VIEW_METHOD
    assert payload["cites"] == [bot.stable_id.value]
    assert "note" not in json.dumps(payload)
    coordinated = save_candidate_view(found, home="coordinated")
    assert is_refusal(coordinated)
    assert coordinated.context["epic"] == "36"
    assert coordinated.context["opens_sqlite"] is False


def test_sqlite_and_registry_kind_writes_are_refused() -> None:
    sqlite = query_candidates(sqlite=True)
    assert is_refusal(sqlite)
    assert sqlite.category is RefusalCategory.POLICY_REJECTION
    assert sqlite.context["opens_sqlite"] is False
    assert sqlite.context["dec_0084_dead"] is True
    assert sqlite.context["persists_copied_rows"] is False
    minted = query_candidates(mint_registry_kind=True)
    assert is_refusal(minted)
    assert minted.context["mints_registry_kind"] is False
    assert minted.context["dec_0084_dead"] is True
    copied = query_candidates(persist_copied_rows=True)
    assert is_refusal(copied)
    assert copied.context["persists_copied_rows"] is False
    store = query_candidates(database="candidates.sqlite")
    assert is_refusal(store)


def test_staging_is_not_read() -> None:
    bot = _record(kind="bot-definition", note="scalping")
    as_of = _as_of(_instant(), (bot,), pointers=(_pointer("scalping", bot.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    folded = query_candidates(
        port=port,
        staging=({"kind": "refinement-proposal", "body": "candidate"},),
    )
    assert is_refusal(folded)
    assert folded.context["reads_staging"] is False
    found = _ok(query_candidates(port=port))
    assert found.reads_staging is False
    assert "staging" not in found.surfaces


def test_module_does_not_read_qma_staging_or_open_sqlite() -> None:
    source = (_SRC / "registryread" / "candidates.py").read_text(encoding="utf-8")
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


def test_cli_and_api_query_the_same_view() -> None:
    bot = _record(kind="bot-definition", note="scalping", zone="dev", origin="qma")
    as_of = _as_of(_instant(), (bot,), pointers=(_pointer("scalping", bot.stable_id),))
    port = _port(_ok(PassiveHub.try_create((as_of,))))
    via_door = _ok(invoke_library_candidates(kind="bot-definition", fp1="scalping", port=port))
    via_lib = _ok(api.query_candidates(kind="bot-definition", fp1="scalping", port=port))
    assert isinstance(via_door, CandidateSet)
    assert via_door.candidates[0].cite() == via_lib.candidates[0].cite() == bot.stable_id.value
    assert api.query_candidates is qmb.query_candidates
    assert api.save_candidate_view is qmb.save_candidate_view
    assert api.candidate_set_identity is qmb.candidate_set_identity
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["library", "candidates", "--kind", "bot-definition", "--zone", "dev"],
        obj={"port": port},
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    assert bot.stable_id.value in clicked.stdout
    assert SURFACE_REGISTRY_AS_OF in clicked.stdout
    assert "dev" in clicked.stdout
    helped = runner.invoke(main, ["library", "--help"])
    assert helped.exit_code == 0, helped.output
    assert "candidates" in helped.output
    assert command_tree()["library"] == ("kinds", "search", "candidates")
    staging = runner.invoke(
        main,
        ["library", "candidates", "--staging"],
        obj={"port": port},
    )
    assert staging.exit_code != 0
    store = runner.invoke(
        main,
        ["library", "candidates", "--database", "candidates.sqlite"],
        obj={"port": port},
    )
    assert store.exit_code != 0
    minted = runner.invoke(
        main,
        ["library", "candidates", "--registry-kind"],
        obj={"port": port},
    )
    assert minted.exit_code != 0
    ungoverned = runner.invoke(
        main,
        ["library", "candidates", "--kind", "bot-definition", "--home", "ungoverned"],
        obj={"port": port},
    )
    assert ungoverned.exit_code == 0, ungoverned.output
    payload = json.loads(ungoverned.stdout)
    assert payload["home"] == HOME_UNGOVERNED
    assert payload["durable"] is False
    cite_only = runner.invoke(
        main,
        ["library", "candidates", "--home", "ungoverned", "--cite", bot.stable_id.value],
        obj={"port": port, "body": None},
    )
    assert cite_only.exit_code != 0
