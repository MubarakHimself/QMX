"""Story 33.3 — data commands wrap qmf-data; occupancy, derived, quality."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar, cast

import tomllib
from click.testing import CliRunner
from qmb.data import (
    CSV_IMPORT_CONTRACT,
    DERIVED_DATASET_CLASS,
    DERIVED_IS_LIBRARY_KIND,
    DERIVED_LINEAGE_EDGE_TYPE,
    QUALITY_SURFACE_CLASS,
    QUALITY_SURFACE_OCCUPANCY,
    DerivedDataset,
    QualitySurface,
    cite_frozen_data_ref,
    derived_identity,
    guard_data_door,
    materialize_derived_dataset,
    quality_surface,
)
from qmb.doors import MCP_IN_DOOR_SET, api, flatten_capabilities, required_library_names
from qmb.doors.cli import (
    DATA_DOWNLOAD_OCCUPANCY,
    DATA_GENERATE_OCCUPANCY,
    DATA_MINTS_CT32,
    DATA_MINTS_EXPERIMENT_SPEC,
    DATA_QUERY_COMMANDS,
    DATA_QUERY_OCCUPANCY,
    DATA_RUN_COMMANDS,
    data_command_occupancy,
    invoke_data,
    main,
)
from qmb.doors.cli.tree import command_tree
from qmf.core.chrono import WriterId
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import EdgeType

import qmb

T = TypeVar("T")

_QMB_ROOT = Path(__file__).resolve().parents[1]


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "qmb", "derived", "boot-1"))


def _fp(*parts: object):
    return _ok(fingerprint({"parts": list(parts)}))


def test_command_tree_data_commands_are_the_qmf_data_fronts() -> None:
    tree = command_tree()
    assert tree["data"] == qmb.DATA_COMMANDS
    assert qmb.DATA_COMMANDS == (
        "download",
        "verify",
        "gap-check",
        "list",
        "catalog",
        "generate",
    )
    catalog = set(flatten_capabilities())
    for name in qmb.DATA_COMMANDS:
        assert f"data.{name}" in catalog


def test_occupancy_download_is_run_queries_are_query() -> None:
    assert DATA_DOWNLOAD_OCCUPANCY == "run"
    assert DATA_GENERATE_OCCUPANCY == "run"
    assert DATA_QUERY_OCCUPANCY == "query"
    assert DATA_MINTS_CT32 is False
    assert DATA_MINTS_EXPERIMENT_SPEC is False
    assert DATA_RUN_COMMANDS == ("download", "generate")
    assert DATA_QUERY_COMMANDS == ("gap-check", "verify", "catalog", "list")
    assert tuple(sorted((*DATA_RUN_COMMANDS, *DATA_QUERY_COMMANDS))) == tuple(
        sorted(qmb.DATA_COMMANDS)
    )
    assert _ok(data_command_occupancy("download")) == "run"
    assert _ok(data_command_occupancy("data.download")) == "run"
    assert _ok(data_command_occupancy("generate")) == "run"
    for name in DATA_QUERY_COMMANDS:
        assert _ok(data_command_occupancy(name)) == "query"
        assert _ok(data_command_occupancy(f"data.{name}")) == "query"


def test_invoke_data_stamps_query_occupancy_on_catalog() -> None:
    catalog = _ok(invoke_data("catalog"))
    assert catalog["command"] == "catalog"
    assert catalog["occupancy"] == DATA_QUERY_OCCUPANCY
    assert catalog["mints_ct32"] is False
    assert catalog["mints_experiment_spec"] is False
    listed = _ok(invoke_data("list"))
    assert listed["occupancy"] == DATA_QUERY_OCCUPANCY
    generated = _ok(invoke_data("generate", {"destination": "synth"}))
    assert generated["occupancy"] == DATA_GENERATE_OCCUPANCY
    assert generated["mints_ct32"] is False


def test_cli_help_documents_occupancy_and_refusals() -> None:
    runner = CliRunner()
    group = runner.invoke(main, ["data", "--help"])
    assert group.exit_code == 0, group.output
    lowered = group.output.lower()
    assert "occupancy" in lowered
    assert "query" in lowered
    assert "ct-13" in lowered or "data-quality" in lowered or "data quality" in lowered
    assert "gap_check" in lowered or "gap-check" in lowered
    download_help = runner.invoke(main, ["data", "download", "--help"])
    assert download_help.exit_code == 0, download_help.output
    down = download_help.output.lower()
    assert "occupancy" in down
    assert "run" in down
    assert "--timezone-clone" in download_help.output
    assert "--auto-update" in download_help.output
    assert "--csv-store" in download_help.output
    assert "ct-15" in down or "ct-12" in down
    verify_help = runner.invoke(main, ["data", "verify", "--help"])
    assert "query" in verify_help.output.lower()
    gap_help = runner.invoke(main, ["data", "gap-check", "--help"])
    assert "query" in gap_help.output.lower()
    assert "analysis.project" in gap_help.output.lower()
    list_help = runner.invoke(main, ["data", "list", "--help"])
    assert "query" in list_help.output.lower()
    catalog_help = runner.invoke(main, ["data", "catalog", "--help"])
    assert "query" in catalog_help.output.lower()


def test_python_api_reexports_derived_and_quality() -> None:
    names = (
        "guard_data_door",
        "materialize_derived_dataset",
        "quality_surface",
        "cite_frozen_data_ref",
        "derived_identity",
        "download",
        "verify",
        "gap_check",
        "catalog",
        "generate",
    )
    required = required_library_names()
    assert "guard_data_door" in required
    for name in names:
        assert getattr(api, name) is getattr(qmb, name)
        assert name in api.__all__
        assert name in qmb.__all__
    assert MCP_IN_DOOR_SET is False


def test_timezone_clone_is_refused() -> None:
    refused = invoke_data("download", {"timezone_clone": True, "destination": "room"})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "timezone_clone"
    assert refused.context["auto_updates_source"] is False
    assert refused.context["data_ref_cites"] == "CT-12"
    assert refused.context["mints_ct32"] is False
    assert refused.context["mints_experiment_spec"] is False
    reason = cast("str", refused.context["reason"])
    assert "timezone" in reason
    auto = invoke_data("catalog", {"auto_update": True})
    assert is_refusal(auto)
    assert auto.category is RefusalCategory.POLICY_REJECTION


def test_csv_store_and_cdn_are_refused() -> None:
    csv_store = invoke_data("download", {"csv_store": True, "destination": "room"})
    assert is_refusal(csv_store)
    assert csv_store.category is RefusalCategory.POLICY_REJECTION
    assert csv_store.context["csv_import_contract"] == CSV_IMPORT_CONTRACT
    reason = cast("str", csv_store.context["reason"])
    assert "CT-15" in reason
    file_import = invoke_data("download", {"csv_path": "ticks.csv", "destination": "room"})
    assert is_refusal(file_import)
    assert file_import.context["csv_import_is_new_store"] is False
    cdn = invoke_data("catalog", {"cdn": True})
    assert is_refusal(cdn)
    assert "clone store" in cast("str", cdn.context["reason"]) or "CDN" in cast(
        "str", cdn.context["reason"]
    )


def test_derived_dataset_is_fingerprinted_not_library_kind() -> None:
    source = _fp("room", "raw-eurusd")
    artifact = _ok(
        materialize_derived_dataset(
            source_room_fp1=source,
            writer=_writer(),
            transform={"calendar": "America/New_York"},
        )
    )
    assert isinstance(artifact, DerivedDataset)
    assert artifact.is_library_kind is False is DERIVED_IS_LIBRARY_KIND
    assert artifact.auto_updates_source is False
    assert artifact.room_machinery == "qmf-data"
    assert artifact.source_room_fp1 == source
    assert artifact.lineage.edge_type is EdgeType.OCCURRENCE_OF is DERIVED_LINEAGE_EDGE_TYPE
    assert artifact.lineage.from_ref == artifact.fingerprint
    assert artifact.lineage.to_ref == source
    identity = artifact.fp1_identity()
    assert identity["class"] == DERIVED_DATASET_CLASS
    assert identity["is_library_kind"] is False
    library = materialize_derived_dataset(
        source_room_fp1=source,
        writer=_writer(),
        library_kind=True,
    )
    assert is_refusal(library)
    assert library.category is RefusalCategory.POLICY_REJECTION
    assert library.context["is_library_kind"] is False
    clone = materialize_derived_dataset(
        source_room_fp1=source,
        writer=_writer(),
        auto_update=True,
    )
    assert is_refusal(clone)
    assert clone.context["auto_updates_source"] is False


def test_quality_surface_is_query_over_ct13_and_gap_check() -> None:
    events = (
        {"event_type": "data quality", "metric": "spread", "n": 1},
        {"event_type": "decision", "n": 2},
        {"event_type": "data quality", "metric": "gap", "n": 3},
    )
    report = {"command": "gap-check", "gaps": (), "fills_gaps": False}
    surface = _ok(quality_surface(events=events, gap_check=report))
    assert isinstance(surface, QualitySurface)
    assert surface.occupancy == QUALITY_SURFACE_OCCUPANCY == "query"
    assert surface.mints_ct32 is False
    assert surface.mints_experiment_spec is False
    assert surface.is_analysis_project is False
    assert len(surface.events) == 2
    assert surface.gap_check is not None
    assert surface.gap_check["command"] == "gap-check"
    identity = surface.fp1_identity()
    assert identity["class"] == QUALITY_SURFACE_CLASS
    assert identity["occupancy"] == "query"
    project = quality_surface(events=events, analysis_project=True)
    assert is_refusal(project)
    assert project.category is RefusalCategory.POLICY_REJECTION
    assert "analysis.project" in cast("str", project.context["reason"])
    via_door = invoke_data("gap-check", {"analysis_project": True})
    assert is_refusal(via_door)
    assert via_door.context["is_analysis_project"] is False


def test_cite_frozen_data_ref_is_ct12_fingerprint() -> None:
    split = _fp("ct-12", "train-test")
    cited = _ok(cite_frozen_data_ref(split))
    assert cited == split
    live = cite_frozen_data_ref("latest")
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION
    updating = cite_frozen_data_ref(split, auto_update=True)
    assert is_refusal(updating)
    assert updating.context["data_ref_cites"] == "CT-12"


def test_derived_identity_is_folded_into_data_front() -> None:
    identity = derived_identity()
    assert identity["derived_is_library_kind"] is False
    assert identity["csv_import_contract"] == CSV_IMPORT_CONTRACT
    assert identity["quality_is_analysis_project"] is False
    assert identity["timezone_clone_auto_update"] is False
    assert identity["data_ref_cites"] == "CT-12"
    front = qmb.data_front_identity()
    assert front["derived_dataset_class"] == DERIVED_DATASET_CLASS
    assert front["quality_surface_class"] == QUALITY_SURFACE_CLASS
    assert qmb.__version__ not in identity.values()


def test_click_timezone_clone_is_refused() -> None:
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        [
            "data",
            "download",
            "--destination",
            "room",
            "--venue",
            "dukascopy-fx",
            "--symbol",
            "EURUSD",
            "--start",
            "1",
            "--timezone-clone",
        ],
    )
    assert clicked.exit_code != 0
    assert clicked.stdout.strip() == ""
    payload = cast("dict[str, object]", json.loads(clicked.stderr))
    assert payload["category"] == RefusalCategory.POLICY_REJECTION.value
    context = cast("dict[str, object]", payload["context"])
    assert context["auto_updates_source"] is False


def test_click_csv_store_is_refused() -> None:
    runner = CliRunner()
    clicked = runner.invoke(main, ["data", "download", "--csv-store"])
    assert clicked.exit_code != 0
    payload = cast("dict[str, object]", json.loads(clicked.stderr))
    assert payload["category"] == RefusalCategory.POLICY_REJECTION.value
    context = cast("dict[str, object]", payload["context"])
    assert context["csv_import_contract"] == CSV_IMPORT_CONTRACT


def test_guard_data_door_is_the_library_policy() -> None:
    ok = guard_data_door("catalog", {})
    assert is_ok(ok)
    refused = guard_data_door("download", {"vendor_clone": True})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_optuna_pin_is_unchanged() -> None:
    data = tomllib.loads((_QMB_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = tuple(data["project"]["dependencies"])
    assert "optuna==4.9.0" in deps
    assert not any(item.startswith("optuna==5") for item in deps)
