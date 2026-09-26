"""Story 62.3 — implementation repair is change_request, not hot-apply.

After a failure, edits to code, graph, grants, or account target are a
``change_request``: app-use may mint; authoring plus operator apply.
Alerts never authorize. HMR and hot-apply stay dead (DEC-0366). Workflows
Story 58.4 / FEAT-0056 remains the apply oracle (FR-PG-27; SCN-0026 Then 5).
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from qma.core.ports.copilot import APP_USE_MAY_APPLY
from qmf.core import Ok, Result
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "ALERTS_AUTHORIZE_REPAIR",
    "APP_USE_MAY_APPLY",
    "HMR_LIVE",
    "HOT_APPLY_LIVE",
    "IMPLEMENTATION_REPAIR_KINDS",
    "REPAIR_IS_CHANGE_REQUEST",
    "STORY_58_4_IS_APPLY_ORACLE",
    "implementation_repair_patch",
    "parse_implementation_repair_kind",
    "refuse_alert_authorization",
    "refuse_hmr_or_hot_apply",
    "refuse_repair_shortcuts",
]


IMPLEMENTATION_REPAIR_KINDS: Final[frozenset[str]] = frozenset(
    {"account_target", "code", "graph", "grants"}
)
HMR_LIVE: Final[bool] = False
HOT_APPLY_LIVE: Final[bool] = False
ALERTS_AUTHORIZE_REPAIR: Final[bool] = False
REPAIR_IS_CHANGE_REQUEST: Final[bool] = True
STORY_58_4_IS_APPLY_ORACLE: Final[bool] = True

_ALERT_TOKENS: Final[frozenset[str]] = frozenset({"alert", "alerts"})


def parse_implementation_repair_kind(value: object) -> Result[str]:
    """Accept only code | graph | grants | account_target (FR-PG-27)."""
    if not isinstance(value, str) or value.strip() == "":
        return invalid_input(
            "repair_kind",
            "implementation repair is code, graph, grants, or account_target",
            given=repr(value),
            allowed=sorted(IMPLEMENTATION_REPAIR_KINDS),
        )
    token = value.strip()
    if token not in IMPLEMENTATION_REPAIR_KINDS:
        return invalid_input(
            "repair_kind",
            "implementation repair is code, graph, grants, or account_target",
            given=token,
            allowed=sorted(IMPLEMENTATION_REPAIR_KINDS),
        )
    return Ok(token)


def implementation_repair_patch(repair_kind: str) -> Mapping[str, object]:
    """Mint-time patch: a request, never a hot-apply of package source."""
    return MappingProxyType({"kind": "runtime_input", "path": f"repair.{repair_kind}"})


def refuse_hmr_or_hot_apply(*, hmr: object = False, hot_apply: object = False) -> TypedRefusal:
    """HMR and hot-apply stay dead (DEC-0366; FR-PG-27)."""
    return policy_rejection(
        "repair",
        "HMR and hot-apply stay dead; repair is change_request (DEC-0366; FR-PG-27)",
        hmr=HMR_LIVE,
        hot_apply=HOT_APPLY_LIVE,
        repair_is_change_request=REPAIR_IS_CHANGE_REQUEST,
        given_hmr=hmr is True,
        given_hot_apply=hot_apply is True,
    )


def refuse_alert_authorization(*, authorized_by: object) -> TypedRefusal:
    """Alerts never authorize a repair apply (FR-PG-27; SCN-0026 Then 5)."""
    return policy_rejection(
        "authorized_by",
        "alerts never authorize; authoring plus operator apply (FR-PG-27)",
        alerts_authorize=ALERTS_AUTHORIZE_REPAIR,
        app_use_may_apply=APP_USE_MAY_APPLY,
        given=repr(authorized_by),
        story_58_4_is_apply_oracle=STORY_58_4_IS_APPLY_ORACLE,
    )


def _is_alert_authorizer(value: object) -> bool:
    if value is True:
        return True
    if not isinstance(value, str):
        return False
    return value.strip().casefold() in _ALERT_TOKENS


def refuse_repair_shortcuts(
    *,
    authorized_by: object | None = None,
    hot_apply: object = False,
    hmr: object = False,
) -> Result[None]:
    """Refuse HMR, hot-apply, and alert authorization before mint or apply."""
    if hmr is True or hot_apply is True:
        return refuse_hmr_or_hot_apply(hmr=hmr, hot_apply=hot_apply)
    if _is_alert_authorizer(authorized_by):
        return refuse_alert_authorization(authorized_by=authorized_by)
    return Ok(None)
