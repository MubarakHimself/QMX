"""Story 34.1 — Library kinds are the existing fp1 list; nothing else."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from click.testing import CliRunner
from qmb.doors import api
from qmb.doors.cli import command_tree, invoke_library_kinds, main
from qmb.registryread import (
    COMP_LIB_MINTED,
    KIND_OWNER,
    LIBRARY_KIND_NAMES,
    LIBRARY_KINDS,
    LIBRARY_KINDS_CLASS,
    LIBRARY_KINDS_OCCUPANCY,
    LIBRARY_MINTS_CT32,
    LIBRARY_MINTS_EXPERIMENT_SPEC,
    LOGIC_SOURCE_MANIFEST_CITES,
    NOT_LIBRARY_KIND_NAMES,
    QMX_LIBRARY_PACKAGE,
    STRATS_CORPUS,
    LibraryKind,
    LibraryKindRoster,
    enumerate_library_kinds,
    library_kinds_identity,
    register_library_kind,
)
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")

_REPO = Path(__file__).resolve().parents[2]
_SRC = Path(__file__).resolve().parents[1] / "src" / "qmb"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def test_library_kinds_are_exactly_the_fp1_list() -> None:
    roster = enumerate_library_kinds()
    assert isinstance(roster, LibraryKindRoster)
    assert roster.kinds == LIBRARY_KINDS
    assert tuple(item.kind for item in roster.kinds) == LIBRARY_KIND_NAMES
    assert LIBRARY_KIND_NAMES == (
        "bot-definition",
        "confluence",
        "strategy-family",
        "book-definition",
        "bms-definition",
        "book-binding",
        "split-manifest",
        "source-observation",
        "performance-result",
        "experiment-spec",
    )
    contracts = tuple(item.contract for item in roster.kinds)
    assert contracts == (
        "CT-33",
        "CT-34",
        "CT-06",
        "CT-22",
        "CT-27",
        "CT-28",
        "CT-12",
        "CT-10",
        "CT-32",
        "CT-47",
    )
    only_spec = [item for item in roster.kinds if item.coordinated_lane_only]
    assert [item.kind for item in only_spec] == ["experiment-spec"]
    assert roster.occupancy == LIBRARY_KINDS_OCCUPANCY == "query"
    assert roster.mints_ct32 is LIBRARY_MINTS_CT32 is False
    assert roster.mints_experiment_spec is LIBRARY_MINTS_EXPERIMENT_SPEC is False
    assert roster.owner == KIND_OWNER == "COMP-QMF-REGISTRY"
    assert roster.mints_comp_lib is COMP_LIB_MINTED is False
    assert roster.qmx_library_package is QMX_LIBRARY_PACKAGE is False


def test_logic_source_manifests_cite_ct33_not_a_library_kind() -> None:
    assert LOGIC_SOURCE_MANIFEST_CITES == "CT-33"
    assert "logic-source-manifest" not in LIBRARY_KIND_NAMES
    refused = register_library_kind("logic-source-manifest")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["cites"] == "CT-33"
    assert refused.context["is_library_kind"] is False
    assert refused.context["present_as_registry"] is False
    alias = register_library_kind("source-manifest")
    assert is_refusal(alias)
    assert alias.context["cites"] == "CT-33"


def test_refused_names_are_not_library_kinds_and_not_registry_records() -> None:
    assert NOT_LIBRARY_KIND_NAMES == (
        "staging",
        "refinement-proposal",
        "job-handle",
        "graph-template",
        "skill",
        "routine",
        "saved-view",
        "analysis-publication",
        "derived-dataset",
        "strats",
        "logic-source-manifest",
        "project",
        "workspace",
        "qmx-library",
        "comp-lib",
    )
    for name in (
        "staging",
        "qma-staging",
        "refinement-proposal",
        "job-handle",
        "graph-template",
        "skill",
        "routine",
        "saved-view",
        "analysis.published",
        "derived-dataset",
    ):
        refused = register_library_kind(name, present_as_registry=True)
        assert is_refusal(refused), name
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["is_library_kind"] is False
        assert refused.context["present_as_registry"] is False
        assert refused.context["owner"] == KIND_OWNER


def test_strats_stays_knowledge_source_and_writes_no_registry_kinds() -> None:
    refused = register_library_kind("STRATS")
    assert is_refusal(refused)
    assert refused.context["strats_corpus"] == STRATS_CORPUS == "KnowledgeSource"
    assert refused.context["writes_registry_kinds"] is False
    assert refused.context["is_library_kind"] is False


def test_project_and_workspace_kinds_are_refused_as_aliases() -> None:
    for name in ("project", "workspace"):
        refused = register_library_kind(name)
        assert is_refusal(refused), name
        assert refused.context["display_alias"] is True
        assert refused.context["is_library_kind"] is False
        assert refused.context["present_as_registry"] is False


def test_existing_kinds_are_projection_members_and_do_not_mint() -> None:
    for name in LIBRARY_KIND_NAMES:
        if name == "experiment-spec":
            continue
        member = _ok(register_library_kind(name))
        assert isinstance(member, LibraryKind)
        assert member.kind == name
        assert member.coordinated_lane_only is False
    spec = _ok(register_library_kind("experiment-spec", lane="coordinated"))
    assert spec.coordinated_lane_only is True
    omitted = _ok(register_library_kind("CT-47"))
    assert omitted.kind == "experiment-spec"
    governed = register_library_kind("experiment-spec", lane="governed")
    assert is_refusal(governed)
    assert governed.context["coordinated_lane_only"] is True
    ungoverned = register_library_kind("experiment-spec", lane="ungoverned")
    assert is_refusal(ungoverned)
    minted = register_library_kind("bot-definition", mint_registry_kind=True)
    assert is_refusal(minted)
    assert minted.context["mints_registry_kind"] is False


def test_no_qmx_library_package_and_owner_stays_registry() -> None:
    identity = library_kinds_identity()
    assert identity["owner"] == KIND_OWNER == "COMP-QMF-REGISTRY"
    assert identity["qmx_library_package"] is False
    assert identity["comp_lib_minted"] is False
    assert identity["class"] == LIBRARY_KINDS_CLASS
    assert identity["occupancy"] == "query"
    assert qmb.__version__ not in identity.values()
    stamped = fingerprint(identity)
    assert is_ok(stamped)
    package = register_library_kind("qmx-library", mint_package=True)
    assert is_refusal(package)
    assert package.context["qmx_library_package"] is False
    assert package.context["mints_comp_lib"] is False
    assert not (_REPO / "qmx-library").exists()
    assert not (_REPO / "packages" / "qmx-library").exists()
    pyproject = (_REPO / "qmb" / "pyproject.toml").read_text(encoding="utf-8")
    assert "qmx-library" not in pyproject
    assert "COMP-LIB" not in pyproject


def test_library_module_does_not_read_qma_staging() -> None:
    source = (_SRC / "registryread" / "library.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module.split(".", 1)[0])
    assert "qma" not in imported


def test_cli_and_api_enumerate_the_same_kinds() -> None:
    roster = _ok(invoke_library_kinds())
    assert roster.kinds == api.enumerate_library_kinds().kinds
    assert api.enumerate_library_kinds is qmb.enumerate_library_kinds
    assert api.register_library_kind is qmb.register_library_kind
    runner = CliRunner()
    clicked = runner.invoke(main, ["library", "kinds"])
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    body = clicked.stdout
    for name in LIBRARY_KIND_NAMES:
        assert name in body
    assert KIND_OWNER in body
    assert "qmx-library" in body
    helped = runner.invoke(main, ["library", "--help"])
    assert helped.exit_code == 0, helped.output
    assert "kinds" in helped.output
    assert command_tree()["library"] == ("kinds",)
