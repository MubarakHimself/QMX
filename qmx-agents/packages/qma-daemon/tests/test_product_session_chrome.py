"""Story 55.4 — a tab is not a session; view:* are not contributions."""

from __future__ import annotations

import ast
import runpy
from pathlib import Path

from qma.core.refusals import UiContributionDeferred
from qma.daemon.journal import EIGHT_STORE_CLASSES
from qma.daemon.sessions import (
    CHROME_KINDS,
    CHROME_OWNS_GRANTS,
    CHROME_OWNS_OCCUPANCY,
    GAP_0081_CHROME_FILLED,
    PRODUCT_SESSION_NEW_CT_MINTED,
    PRODUCT_SESSION_OCCUPANCY,
    PRODUCT_SESSION_SIXTH_STORE_MINTED,
    PRODUCT_SESSION_TAB_WRITES,
    ProductSessionChrome,
    ProductSessionService,
    looks_like_chrome_id,
    refuse_chrome_owns_grants,
    refuse_chrome_owns_occupancy,
    refuse_tab_as_product_session,
)
from qma.wire import (
    VIEW_FILLS_GAP_0081_CHROME,
    VIEW_IS_CONTRIBUTION_HIT,
    VIEW_IS_PLUGIN_CONTRIBUTION_POINT,
    VIEW_IS_PRODUCT_SESSION,
    VIEW_OWNS_GRANTS,
    VIEW_OWNS_OCCUPANCY,
    ViewPresentation,
    parse_federated_hit,
    parse_view_presentation,
    refuse_view_as_contribution_hit,
    refuse_view_as_product_session,
    refuse_view_owns_grants,
)
from qmf.core import is_ok, is_refusal

_DAEMON_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon"
_SRC = _DAEMON_SRC / "sessions" / "chrome.py"
_SESSION_SRC = _DAEMON_SRC / "sessions" / "product_session.py"
_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "product_session_chrome_usage.py"

_AS_OF = "2026-09-20T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
_VIEW = {
    "view_id": "view:heatmap",
    "view_version": 1,
    "op_id": "sector-intel.inspect",
    "mount": "mounted",
    "parameter_binding": {"schema": "sector-intel.inspect.v1", "values": {}},
    "snapshot_cursor": 9,
    "stale": False,
    "is_contribution_hit": False,
    "is_plugin_contribution_point": False,
    "occupancy": "none",
}


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


def test_chrome_identity_owns_neither_grants_nor_occupancy() -> None:
    assert frozenset({"tab", "window", "view"}) == CHROME_KINDS
    assert CHROME_OWNS_GRANTS is False
    assert CHROME_OWNS_OCCUPANCY is False
    assert GAP_0081_CHROME_FILLED is False
    assert PRODUCT_SESSION_OCCUPANCY == "none"
    assert PRODUCT_SESSION_TAB_WRITES is False
    assert PRODUCT_SESSION_SIXTH_STORE_MINTED is False
    assert PRODUCT_SESSION_NEW_CT_MINTED is False
    assert len(EIGHT_STORE_CLASSES) == 8
    assert VIEW_IS_CONTRIBUTION_HIT is False
    assert VIEW_IS_PLUGIN_CONTRIBUTION_POINT is False
    assert VIEW_IS_PRODUCT_SESSION is False
    assert VIEW_OWNS_GRANTS is False
    assert VIEW_OWNS_OCCUPANCY is False
    assert VIEW_FILLS_GAP_0081_CHROME is False
    chrome = ProductSessionChrome()
    assert chrome.identity()["occupancy"] == "none"
    assert chrome.identity()["gap_0081_chrome_filled"] is False
    assert looks_like_chrome_id("view:heatmap") is True
    assert looks_like_chrome_id("window:main") is True
    assert looks_like_chrome_id("psess:desk-1") is False


def test_tab_window_view_are_not_product_sessions() -> None:
    service = ProductSessionService()
    for chrome_id in ("tab:a", "window:main", "view:heatmap"):
        minted = service.mint(**_mint_kwargs(product_session_id=chrome_id))
        assert is_refusal(minted)
        assert minted.context["chrome_owns_grants"] is False
    ok = service.mint(**_mint_kwargs())
    assert is_ok(ok)
    with_view = service.mint(**_mint_kwargs(view_id="view:heatmap"))
    assert is_refusal(with_view)
    with_window = service.mint(**_mint_kwargs(window_id="window:main"))
    assert is_refusal(with_window)
    assert is_refusal(refuse_tab_as_product_session())
    assert is_refusal(refuse_view_as_product_session())


def test_tabs_windows_views_share_session_and_write_nothing() -> None:
    service = ProductSessionService()
    chrome = ProductSessionChrome(sessions=service)
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    tab = chrome.open_tab(tab_id="tab-a", app_instance_id="inst:1")
    window = chrome.open_window(window_id="window-main", app_instance_id="inst:1")
    view = chrome.open_view(view_id="view:heatmap", product_session_id="psess:desk-1")
    assert is_ok(tab)
    assert is_ok(window)
    assert is_ok(view)
    assert tab.value.product_session_id == window.value.product_session_id == "psess:desk-1"
    assert view.value.product_session_id == "psess:desk-1"
    assert tab.value.occupancy == PRODUCT_SESSION_OCCUPANCY
    closed = chrome.close("tab-a", product_session_id="psess:desk-1")
    assert is_ok(closed)
    still = service.get("psess:desk-1")
    assert is_ok(still)
    missing = chrome.open_view(view_id="view:other", app_instance_id="inst:missing")
    assert is_refusal(missing)
    minted_from = chrome.mint_from_chrome("view:new")
    assert is_refusal(minted_from)
    assert minted_from.context["tab_mints"] is False


def test_chrome_does_not_own_grants_or_occupancy() -> None:
    service = ProductSessionService()
    chrome = ProductSessionChrome(sessions=service)
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    granted = service.host_grant(
        "psess:desk-1",
        grant_id="grant:1",
        audience="view:heatmap",
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1"]},
        expires_at="2026-12-31T00:00:00Z",
    )
    assert is_refusal(granted)
    assert granted.context["chrome_owns_grants"] is False
    window_grant = service.host_grant(
        "psess:desk-1",
        grant_id="grant:2",
        audience="window:main",
        op_id="qmb.analysis.project",
        op_version=1,
        effect_class="read",
        parameter_ceiling={"allow_keys": ["run_fp1"]},
        expires_at="2026-12-31T00:00:00Z",
    )
    assert is_refusal(window_grant)
    assert is_refusal(chrome.grants_for("tab-a"))
    assert is_refusal(refuse_chrome_owns_grants())
    occupancy = chrome.occupancy_for("tab-a")
    assert is_ok(occupancy)
    assert occupancy.value == "none"
    claimed = chrome.set_occupancy("tab-a", "live")
    assert is_refusal(claimed)
    assert claimed.context["occupancy"] == "none"
    assert claimed.context["chrome_owns_occupancy"] is False
    assert is_refusal(refuse_chrome_owns_occupancy())


def test_view_star_is_ad17_dto_not_contribution_or_session() -> None:
    chrome = ProductSessionChrome()
    built = ViewPresentation.try_create(
        view_id=_VIEW["view_id"],
        view_version=_VIEW["view_version"],
        op_id=_VIEW["op_id"],
        mount=_VIEW["mount"],
        parameter_binding=_VIEW["parameter_binding"],
        snapshot_cursor=_VIEW["snapshot_cursor"],
        stale=_VIEW["stale"],
    )
    assert is_ok(built)
    view = built.value
    assert view.is_contribution_hit is False
    assert view.is_plugin_contribution_point is False
    assert view.occupancy == "none"
    as_hit = parse_federated_hit(
        {
            "hit_class": "contribution",
            "plugin_id": "desk-ui",
            "point": "view:heatmap",
            "qualified_id": "desk-ui:heatmap",
            "package_id": "desk-ui",
            "package_version": "1.0.0",
            "availability_revision": 1,
            "availability": "enabled",
        }
    )
    assert is_refusal(as_hit)
    assert as_hit.context["gap"] == "GAP-0081"
    as_session = parse_view_presentation({**_VIEW, "product_session_id": "psess:desk-1"})
    assert is_refusal(as_session)
    assert as_session.context["is_product_session"] is False
    as_grant = parse_view_presentation({**_VIEW, "grant_id": "grant:1"})
    assert is_refusal(as_grant)
    assert as_grant.context["chrome_owns_grants"] is False
    assert as_grant.context["branch"] == "B"
    treated = chrome.treat_view_as_contribution(dict(_VIEW))
    assert is_refusal(treated)
    invoke = chrome.authorize_invoke(view)
    assert is_refusal(invoke)
    assert invoke.context["hit_is_grant"] is False
    assert invoke.context["branch"] == "B"
    assert is_refusal(refuse_view_as_contribution_hit())
    assert is_refusal(refuse_view_owns_grants())


def test_mount_view_does_not_start_work_or_fill_gap_0081() -> None:
    service = ProductSessionService()
    chrome = ProductSessionChrome(sessions=service)
    minted = service.mint(**_mint_kwargs())
    assert is_ok(minted)
    mounted = chrome.mount_view(product_session_id="psess:desk-1", view=dict(_VIEW))
    assert is_ok(mounted)
    assert mounted.value.occupancy == "none"
    payload = dict(mounted.value.to_payload())
    assert "view_id" not in payload
    assert "granted_ops" in payload
    durable = ViewPresentation.try_create(
        view_id="view:heatmap",
        view_version=1,
        op_id="sector-intel.inspect",
        mount="mounted",
        parameter_binding={"schema": "sector-intel.inspect.v1", "values": {}},
        snapshot_cursor=0,
        stale=False,
        starts_durable_work=True,
    )
    assert is_refusal(durable)
    filled = chrome.fill_gap_0081_chrome()
    assert is_refusal(filled)
    assert UiContributionDeferred.matches(filled)
    assert filled.context["gap"] == "GAP-0081"
    assert filled.context["ui_view_minted"] is False
    ui_view = chrome.open_view(view_id="ui_view", product_session_id="psess:desk-1")
    assert is_refusal(ui_view)
    assert ui_view.context["gap"] == "GAP-0081"


def test_module_never_imports_qmb() -> None:
    for path in (_SRC, _SESSION_SRC):
        source = path.read_text(encoding="utf-8")
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
