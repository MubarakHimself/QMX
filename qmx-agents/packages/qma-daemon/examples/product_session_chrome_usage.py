"""Reference usage — tab/window/view is not a session; view:* is not a hit (55.4)."""

from __future__ import annotations

from qma.core.refusals import UiContributionDeferred
from qma.daemon.sessions import (
    CHROME_OWNS_GRANTS,
    CHROME_OWNS_OCCUPANCY,
    GAP_0081_CHROME_FILLED,
    PRODUCT_SESSION_OCCUPANCY,
    ProductSessionChrome,
    ProductSessionService,
)
from qma.wire import VIEW_IS_CONTRIBUTION_HIT, parse_federated_hit
from qmf.core import is_ok, is_refusal

_AS_OF = "2026-09-20T00:00:00Z"
_CONTRIBUTION = {"package_version": "0.1.0", "qualified_id": "analysis-backtest:qmb"}
_VIEW: dict[str, object] = {
    "view_id": "view:heatmap",
    "view_version": 1,
    "op_id": "sector-intel.inspect",
    "mount": "mounted",
    "parameter_binding": {"schema": "sector-intel.inspect.v1", "values": {}},
    "snapshot_cursor": 9,
    "stale": False,
    "occupancy": "none",
}


def main() -> None:
    assert CHROME_OWNS_GRANTS is False
    assert CHROME_OWNS_OCCUPANCY is False
    assert GAP_0081_CHROME_FILLED is False
    assert VIEW_IS_CONTRIBUTION_HIT is False
    service = ProductSessionService()
    chrome = ProductSessionChrome(sessions=service)
    minted = service.mint(
        product_session_id="psess:desk-1",
        profile="authoring",
        principal="operator",
        contribution=dict(_CONTRIBUTION),
        instance_id="inst:1",
        config_revision=4,
        as_of=_AS_OF,
    )
    assert is_ok(minted)
    assert is_ok(chrome.open_tab(tab_id="tab-a", app_instance_id="inst:1"))
    assert is_ok(chrome.open_window(window_id="window-main", app_instance_id="inst:1"))
    mounted = chrome.mount_view(product_session_id="psess:desk-1", view=dict(_VIEW))
    assert is_ok(mounted)
    assert mounted.value.occupancy == PRODUCT_SESSION_OCCUPANCY
    assert is_refusal(chrome.grants_for("tab-a"))
    assert is_refusal(chrome.set_occupancy("window-main", "live"))
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
    filled = chrome.fill_gap_0081_chrome()
    assert is_refusal(filled)
    assert UiContributionDeferred.matches(filled)
    print("tab/window/view is not a session; view:* is AD-17 DTO only; occupancy none")


if __name__ == "__main__":
    main()
