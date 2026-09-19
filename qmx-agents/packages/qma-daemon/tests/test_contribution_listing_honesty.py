"""Story 53.4 / SCN-0018 Branch B — listings distinguish axes; hit is not a grant."""

from __future__ import annotations

import ast
from pathlib import Path

from qma.core.plugins import PluginContext
from qma.core.ports.qmb import qmb_opens_daemon_sqlite
from qma.daemon.discovery import (
    CONTRIBUTION_HIT_IS_GRANT,
    CONTRIBUTION_LISTING_OCCUPANCY,
    CONTRIBUTION_LISTING_STATUS_AXES,
    FEDERATED_SEARCH_OCCUPANCY,
    GRANTED_OPS_ARE_PACK_ENABLEMENT,
    PRODUCT_SESSION_MINTED,
    VIEW_IS_CONTRIBUTION_HIT,
    ContributionListingService,
    contribution_listing_identity,
)
from qma.daemon.plugins import DaemonPluginContext, PluginLoader
from qmf.core import is_ok, is_refusal

_LISTING_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "discovery" / "listing.py"
)
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "contribution_listing_usage.py"


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "dependencies": [],
        "contributions": [{"point": "tool", "local_id": "inspect"}],
        "contributes": [{"point": "tool", "local_id": "inspect"}],
        "permissions": [],
        "migrations": [],
    }
    base.update(overrides)
    return base


def _activate(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("inspect", {"name": "inspect"})


def test_identity_occupancy_none_and_no_product_session() -> None:
    identity = contribution_listing_identity()
    assert identity["occupancy"] == "none" == CONTRIBUTION_LISTING_OCCUPANCY
    assert identity["occupancy"] == FEDERATED_SEARCH_OCCUPANCY
    assert identity["is_door_run"] is False
    assert identity["hit_is_grant"] is False is CONTRIBUTION_HIT_IS_GRANT
    assert identity["product_session_minted"] is False is PRODUCT_SESSION_MINTED
    assert identity["granted_ops_are_pack_enablement"] is False is GRANTED_OPS_ARE_PACK_ENABLEMENT
    assert identity["view_is_contribution_hit"] is False is VIEW_IS_CONTRIBUTION_HIT
    assert identity["axes"] == list(CONTRIBUTION_LISTING_STATUS_AXES)
    assert identity["wired_at_inspect_sha"] is False
    assert qmb_opens_daemon_sqlite() is False


def test_enable_publishes_but_does_not_grant_or_authorize_invoke() -> None:
    loader = PluginLoader()
    enabled = loader.enable(_manifest(), activator=_activate)
    assert is_ok(enabled)
    listings = ContributionListingService(loader)
    found = listings.list_contributions()
    assert is_ok(found)
    rows = found.value
    assert len(rows) == 1
    row = rows[0]
    assert row.published is True
    assert row.configured is True
    assert row.granted is False
    assert row.reachable is False
    assert row.healthy is False
    assert row.authorizes_invoke is False
    assert row.occupancy == "none"
    assert row.hit.qualified_id == "research-corpus:inspect"
    assert "grant_id" not in row.to_payload()
    assert "product_session" not in row.to_payload()

    invoke = listings.authorize_invoke(row)
    assert is_refusal(invoke)
    assert invoke.context["branch"] == "B"
    assert invoke.context["hit_is_grant"] is False
    assert invoke.context["published"] is True

    prose = listings.describe(row, treat_as_grant=True)
    assert is_refusal(prose)
    honest = listings.describe(row, prose="published, not granted, not healthy")
    assert is_ok(honest)
    assert honest.value["authorizes_invoke"] is False


def test_axes_are_independent_and_all_true_is_still_not_a_grant() -> None:
    loader = PluginLoader()
    enabled = loader.enable(_manifest(), activator=_activate)
    assert is_ok(enabled)
    listings = ContributionListingService(loader)
    first = listings.list_contributions()
    assert is_ok(first)
    qid = first.value[0].hit.qualified_id
    listings.note_host_grant(qid)
    listings.note_reachable(qid)
    listings.note_healthy(qid)
    found = listings.list_contributions()
    assert is_ok(found)
    row = found.value[0]
    assert row.published is True
    assert row.configured is True
    assert row.granted is True
    assert row.reachable is True
    assert row.healthy is True
    assert row.authorizes_invoke is False
    assert listings.authorize_invoke(row).context["healthy"] is True


def test_disable_keeps_configured_unpublished() -> None:
    loader = PluginLoader()
    enabled = loader.enable(_manifest(), activator=_activate)
    assert is_ok(enabled)
    listings = ContributionListingService(loader)
    before = listings.list_contributions()
    assert is_ok(before)
    assert before.value[0].published is True
    disabled = loader.disable("research-corpus")
    assert is_ok(disabled)
    after = listings.list_contributions()
    assert is_ok(after)
    assert len(after.value) == 1
    row = after.value[0]
    assert row.published is False
    assert row.configured is True
    assert row.granted is False
    assert row.hit.availability == "disabled"
    assert row.authorizes_invoke is False


def test_hypotheses_views_and_product_session_refuse() -> None:
    loader = PluginLoader()
    listings = ContributionListingService(loader)
    hypo = listings.list_contributions(research_ref="qml-research-hypothesis:1")
    assert is_refusal(hypo)
    assert hypo.context["listing_surface"] == "qml.research"

    view = listings.list_contributions(view_id="view:heatmap")
    assert is_refusal(view)
    assert view.context["gap"] == "GAP-0081"

    session = listings.mint_product_session(product_session_id="psess:1")
    assert is_refusal(session)
    assert session.context["product_session_minted"] is False
    listed = listings.list_contributions(product_session_id="psess:1")
    assert is_refusal(listed)

    ops = listings.list_contributions(granted_ops=["grant:1"])
    assert is_refusal(ops)
    assert ops.context["granted_ops_are_pack_enablement"] is False

    collapsed = listings.list_contributions(status="healthy")
    assert is_refusal(collapsed)

    busy = listings.list_contributions(occupancy="run")
    assert is_refusal(busy)


def test_module_never_imports_qmb_occupancy_none() -> None:
    source = _LISTING_SRC.read_text(encoding="utf-8")
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
    assert CONTRIBUTION_LISTING_OCCUPANCY == "none"
    assert qmb_opens_daemon_sqlite() is False


def test_reference_usage_example_runs() -> None:
    import runpy

    namespace = runpy.run_path(str(_EXAMPLE))
    namespace["main"]()
