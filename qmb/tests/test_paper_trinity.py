"""Story 36.6 — research-paper, hub inbox, notebooks, alias identity (QMB)."""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import TypeVar

from qmb.paper import (
    CONTROLLED_ROOM_HOST,
    HUB_PUBLISH_IS_HUMAN,
    NODE_PAPER_OWNER,
    PAPER_NOUN_RESEARCH,
    QMA_PAPER_EXISTS,
    QMB_NOTEBOOK_MODULE,
    WORKSPACE_DEFAULTS_ARE_IDENTITY,
    admit_exploratory_notebook,
    append_hub_inbox_fragment,
    name_research_paper,
    publish_hub_inbox,
    refuse_qma_paper,
    refuse_qmb_notebook_module,
    refuse_sandbox_provenance,
    resolve_display_alias,
)
from qmb.registryread import RegistryFragment
from qmf.core.chrono import WriterId
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal

T = TypeVar("T")

_QMB_ROOT = Path(__file__).resolve().parents[1]


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def test_governed_replay_is_research_paper_not_node_or_qma() -> None:
    named = name_research_paper(world=World.REPLAY, location="outside_node")
    assert is_ok(named)
    assert named.value == PAPER_NOUN_RESEARCH
    assert QMA_PAPER_EXISTS is False
    assert is_refusal(name_research_paper(world=World.REPLAY, noun="qma-paper"))
    assert is_refusal(name_research_paper(world=World.REPLAY, location="node"))
    assert NODE_PAPER_OWNER == "COMP-QMN"
    assert refuse_qma_paper().context["exists"] is False


def test_writerid_fragments_enter_inbox_and_publish_is_human() -> None:
    writer = _ok(WriterId.try_create("lab", "research", "hub", "boot-36-6"))
    source = _ok(fingerprint({"n": "book-src"}))
    fragment = _ok(RegistryFragment.try_create(source, {"section": "sizing"}))
    inbox = _ok(
        append_hub_inbox_fragment(
            None,
            writer=writer,
            fragment=fragment,
            provenance="live",
        )
    )
    assert len(inbox.fragments) == 1
    assert inbox.fragments[0].writer == writer
    sandbox_source = _ok(fingerprint({"n": "sandbox-src"}))
    sandbox_fragment = _ok(RegistryFragment.try_create(sandbox_source, {"section": "sandbox"}))
    sandbox = _ok(
        append_hub_inbox_fragment(
            inbox,
            writer=writer,
            fragment=sandbox_fragment,
            provenance="sandbox",
        )
    )
    assert len(sandbox.fragments) == 2
    assert is_refusal(refuse_sandbox_provenance(provenance="sandbox", crossing="publish"))
    assert is_refusal(refuse_sandbox_provenance(provenance="sandbox", crossing="pull"))
    assert is_ok(refuse_sandbox_provenance(provenance="live", crossing="publish"))
    assert HUB_PUBLISH_IS_HUMAN is True
    assert is_refusal(publish_hub_inbox())


def test_exploratory_notebook_imports_library_not_a_qmb_module() -> None:
    admitted = admit_exploratory_notebook(imports=("qmb", "qml"), host=CONTROLLED_ROOM_HOST)
    assert is_ok(admitted)
    assert QMB_NOTEBOOK_MODULE is False
    assert is_refusal(admit_exploratory_notebook(imports=("qmb",), as_qmb_module=True))
    assert is_refusal(admit_exploratory_notebook(imports=("qmb",), jupyter_product="jupyter"))
    assert is_refusal(refuse_qmb_notebook_module())


def test_project_workspace_are_aliases_workspace_defaults_are_not_identity() -> None:
    assert WORKSPACE_DEFAULTS_ARE_IDENTITY is False
    coordinated = resolve_display_alias(
        display="project",
        lane="coordinated",
        over="fp1:spec",
    )
    assert is_ok(coordinated)
    governed = resolve_display_alias(display="workspace", lane="governed", over="fp1:bot")
    assert is_ok(governed)
    assert is_refusal(
        resolve_display_alias(display="project", lane="coordinated", over="fp1:x", mint_record=True)
    )


def test_paper_trinity_usage_example_runs() -> None:
    path = _QMB_ROOT / "examples" / "paper_trinity_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
