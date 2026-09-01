"""Act-level money-path deny-list constants (FR-Q09, FR-Q42; DEC-0315).

Declared as code beside the capability ladder. Nothing — configuration, plugin
declaration, Role, Mission, hook, toolset, tool_adapter, check_fn, or capability
rung — may widen this set or lift a match. The daemon refuses matching tools at
registration with ``ProhibitedMoneyPathTool``. Paper is an account role on a
real venue, never a sandbox that makes an act safe.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from qma.core.refusals.variants import ProhibitedMoneyPathTool

__all__ = [
    "MONEY_PATH_ACT_ALIASES",
    "MONEY_PATH_DENIAL_NOT_LIFTABLE_BY",
    "MONEY_PATH_DENIED_ACTS",
    "MONEY_PATH_DENY_LIST",
    "MONEY_PATH_DENY_LIST_OWNER",
    "QMA_MINTED_MONEY_PATH_VALUES",
    "QMA_MINTED_PROMOTION_COMMAND",
    "MoneyPathAct",
    "MoneyPathDeniedAct",
    "MoneyPathDenyError",
    "assert_deny_list_not_widenable",
    "is_money_path_act_denied",
    "match_money_path_act",
    "parse_money_path_act",
    "refuse_money_path_permission",
    "refuse_money_path_registration",
]


class MoneyPathAct(StrEnum):
    """Act families refused before tool registration completes (AD-16)."""

    ORDER = "order"
    POSITION = "position"
    PROTECTION = "protection"
    SIZING = "sizing"
    BINDING = "binding"
    MODE = "mode"
    CONTROL = "control"
    ZONE_TRANSITION = "zone_transition"
    PROMOTION = "promotion"


class MoneyPathDeniedAct(StrEnum):
    """Enumerated act-level verbs refused at registration (AD-16; FR-Q42)."""

    SUBMIT_ORDER = "submit_order"
    AMEND_ORDER = "amend_order"
    CANCEL_ORDER = "cancel_order"
    REPLACE_ORDER = "replace_order"
    OPEN_POSITION = "open_position"
    CLOSE_POSITION = "close_position"
    REDUCE_POSITION = "reduce_position"
    HEDGE_POSITION = "hedge_position"
    SET_PROTECTION = "set_protection"
    AMEND_PROTECTION = "amend_protection"
    SIZE = "size"
    RESIZE = "resize"
    MINT_SIZING_DECISION = "mint_sizing_decision"
    CREATE_BINDING = "create_binding"
    AMEND_BINDING = "amend_binding"
    ACTIVATE_BINDING = "activate_binding"
    STAND_DOWN_BINDING = "stand_down_binding"
    DELETE_BINDING = "delete_binding"
    SET_BOOK_MODE = "set_book_mode"
    SET_SEAT_STATE = "set_seat_state"
    SET_BOOK_PARAMETER = "set_book_parameter"
    SET_BMS_PARAMETER = "set_bms_parameter"
    SET_PRIORITY_RANK = "set_priority_rank"
    SET_CAPITAL_FLOOR = "set_capital_floor"
    ARM_KILL_SWITCH = "arm_kill_switch"
    DISARM_KILL_SWITCH = "disarm_kill_switch"
    CHANGE_KILL_SWITCH = "change_kill_switch"
    CHANGE_CONTROL_ACTION = "change_control_action"


# Closed family deny-list. Membership is the entire MoneyPathAct vocabulary;
# callers never receive an API that adds members.
MONEY_PATH_DENY_LIST: Final[frozenset[MoneyPathAct]] = frozenset(MoneyPathAct)

MONEY_PATH_DENIED_ACTS: Final[frozenset[MoneyPathDeniedAct]] = frozenset(MoneyPathDeniedAct)

MONEY_PATH_DENY_LIST_OWNER: Final[str] = "AD-16"

# Surfaces that may propose a grant but cannot lift a code-declared denial.
MONEY_PATH_DENIAL_NOT_LIFTABLE_BY: Final[frozenset[str]] = frozenset(
    {
        "role",
        "mission",
        "hook",
        "toolset",
        "tool_adapter",
        "check_fn",
        "permission_policy",
    }
)

# This story mints no promotion command and no money-path value (FR-Q42).
QMA_MINTED_PROMOTION_COMMAND: Final[None] = None
QMA_MINTED_MONEY_PATH_VALUES: Final[tuple[str, ...]] = ()

# Longest-first account-role prefixes. Paper is an account role, not a sandbox.
_ROLE_PREFIXES: Final[tuple[str, ...]] = (
    "paper_only_",
    "live_only_",
    "demo_only_",
    "paper_",
    "live_",
    "demo_",
)

# Phrase / synonym aliases → canonical family or denied-act token.
_ALIAS_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("place_order", MoneyPathDeniedAct.SUBMIT_ORDER.value),
    ("place_an_order", MoneyPathDeniedAct.SUBMIT_ORDER.value),
    ("submit_an_order", MoneyPathDeniedAct.SUBMIT_ORDER.value),
    ("order_submit", MoneyPathDeniedAct.SUBMIT_ORDER.value),
    ("amend_an_order", MoneyPathDeniedAct.AMEND_ORDER.value),
    ("order_amend", MoneyPathDeniedAct.AMEND_ORDER.value),
    ("cancel_an_order", MoneyPathDeniedAct.CANCEL_ORDER.value),
    ("order_cancel", MoneyPathDeniedAct.CANCEL_ORDER.value),
    ("replace_an_order", MoneyPathDeniedAct.REPLACE_ORDER.value),
    ("order_replace", MoneyPathDeniedAct.REPLACE_ORDER.value),
    ("open_a_position", MoneyPathDeniedAct.OPEN_POSITION.value),
    ("close_a_position", MoneyPathDeniedAct.CLOSE_POSITION.value),
    ("reduce_a_position", MoneyPathDeniedAct.REDUCE_POSITION.value),
    ("hedge_a_position", MoneyPathDeniedAct.HEDGE_POSITION.value),
    ("set_a_protection", MoneyPathDeniedAct.SET_PROTECTION.value),
    ("amend_a_protection", MoneyPathDeniedAct.AMEND_PROTECTION.value),
    ("re_size", MoneyPathDeniedAct.RESIZE.value),
    ("re_size_sizing", MoneyPathDeniedAct.RESIZE.value),
    ("mint_a_sizing_decision", MoneyPathDeniedAct.MINT_SIZING_DECISION.value),
    ("sizing_decision", MoneyPathDeniedAct.MINT_SIZING_DECISION.value),
    ("create_a_binding", MoneyPathDeniedAct.CREATE_BINDING.value),
    ("quant_to_book_binding", MoneyPathDeniedAct.CREATE_BINDING.value),
    ("bot_to_book_binding", MoneyPathDeniedAct.CREATE_BINDING.value),
    ("stand_down", MoneyPathDeniedAct.STAND_DOWN_BINDING.value),
    ("book_mode", MoneyPathDeniedAct.SET_BOOK_MODE.value),
    ("seat_state", MoneyPathDeniedAct.SET_SEAT_STATE.value),
    ("book_parameter", MoneyPathDeniedAct.SET_BOOK_PARAMETER.value),
    ("bms_parameter", MoneyPathDeniedAct.SET_BMS_PARAMETER.value),
    ("priority_rank", MoneyPathDeniedAct.SET_PRIORITY_RANK.value),
    ("capital_floor", MoneyPathDeniedAct.SET_CAPITAL_FLOOR.value),
    ("kill_switch", MoneyPathDeniedAct.CHANGE_KILL_SWITCH.value),
    ("node_control_action", MoneyPathDeniedAct.CHANGE_CONTROL_ACTION.value),
    ("control_action", MoneyPathDeniedAct.CHANGE_CONTROL_ACTION.value),
    ("transition_zone", MoneyPathAct.ZONE_TRANSITION.value),
    ("transition_a_registry_artifact", MoneyPathAct.ZONE_TRANSITION.value),
    ("promote", MoneyPathAct.PROMOTION.value),
)

MONEY_PATH_ACT_ALIASES: Final[Mapping[str, str]] = MappingProxyType(dict(_ALIAS_PAIRS))


class MoneyPathDenyError(ValueError):
    """Raised when the deny-list constant is misused or illegally widened."""


def _normalize_act_token(value: str) -> str:
    """Lowercase, collapse separators, and strip a paper/live/demo role prefix."""
    token = value.strip().casefold().replace("-", "_").replace("/", "_")
    token = "_".join(token.split())
    while "__" in token:
        token = token.replace("__", "_")
    token = token.strip("_")
    for prefix in _ROLE_PREFIXES:
        if token.startswith(prefix) and len(token) > len(prefix):
            token = token[len(prefix) :]
            break
    return token


def parse_money_path_act(value: MoneyPathAct | str) -> MoneyPathAct:
    """Parse a money-path act family; invented values fail."""
    if isinstance(value, MoneyPathAct):
        return value
    try:
        return MoneyPathAct(value)
    except ValueError as exc:
        raise MoneyPathDenyError(f"{value!r} is not a money-path act family") from exc


def match_money_path_act(act: MoneyPathAct | MoneyPathDeniedAct | str) -> str | None:
    """Return the canonical denied act token, or ``None`` when the act is allowed."""
    if isinstance(act, MoneyPathAct):
        return act.value
    if isinstance(act, MoneyPathDeniedAct):
        return act.value
    if not act.strip():
        return None
    token = _normalize_act_token(act)
    if not token:
        return None
    aliased = MONEY_PATH_ACT_ALIASES.get(token, token)
    try:
        return MoneyPathAct(aliased).value
    except ValueError:
        pass
    try:
        return MoneyPathDeniedAct(aliased).value
    except ValueError:
        return None


def is_money_path_act_denied(act: MoneyPathAct | MoneyPathDeniedAct | str) -> bool:
    """True when ``act`` is on the code-declared deny-list."""
    return match_money_path_act(act) is not None


def refuse_money_path_registration(
    *,
    tool_id: str,
    act: MoneyPathAct | MoneyPathDeniedAct | str,
    plugin_id: str | None = None,
) -> ProhibitedMoneyPathTool:
    """Build the registration refusal for a deny-listed act.

    Returns a typed refusal — never raises across the package boundary (CT-04).
    """
    matched = match_money_path_act(act)
    if matched is None:
        raise MoneyPathDenyError(f"{act!r} is not on the money-path deny-list")
    return ProhibitedMoneyPathTool.of(
        tool_id=tool_id,
        matched_act=matched,
        plugin_id=plugin_id,
    )


def refuse_money_path_permission(
    *,
    tool_id: str,
    act: MoneyPathAct | MoneyPathDeniedAct | str,
    plugin_id: str | None = None,
    via: str | None = None,
) -> ProhibitedMoneyPathTool:
    """Refuse a permission/availability grant that cannot lift the deny-list.

    ``via`` names the proposing surface (Role, Mission, hook, toolset, …) for
    evidence; it never changes the outcome.
    """
    refusal = refuse_money_path_registration(
        tool_id=tool_id,
        act=act,
        plugin_id=plugin_id,
    )
    if via is not None:
        context = dict(refusal.context)
        context["via"] = via
        return ProhibitedMoneyPathTool.create(context=context)
    return refusal


def assert_deny_list_not_widenable(
    proposed: frozenset[MoneyPathAct | str] | set[MoneyPathAct | str] | None = None,
) -> None:
    """Refuse any attempt to treat a wider set as the deny-list.

    The deny-list is the frozenset of ``MoneyPathAct`` members. Callers may not
    supply a superset; a ``None`` check pins the constant itself.
    """
    if proposed is None:
        if frozenset(MoneyPathAct) != MONEY_PATH_DENY_LIST:
            raise MoneyPathDenyError(
                "MONEY_PATH_DENY_LIST must equal frozenset(MoneyPathAct); "
                "no configuration may widen it"
            )
        if frozenset(MoneyPathDeniedAct) != MONEY_PATH_DENIED_ACTS:
            raise MoneyPathDenyError(
                "MONEY_PATH_DENIED_ACTS must equal frozenset(MoneyPathDeniedAct); "
                "no configuration may widen it"
            )
        return
    allowed_values = {act.value for act in MONEY_PATH_DENY_LIST} | {
        act.value for act in MONEY_PATH_DENIED_ACTS
    }
    proposed_values = {
        item.value if isinstance(item, (MoneyPathAct, MoneyPathDeniedAct)) else str(item)
        for item in proposed
    }
    extras = proposed_values - allowed_values
    if extras:
        raise MoneyPathDenyError(
            "money-path deny-list cannot be widened by configuration, plugin "
            f"declaration, or capability rung; extras={sorted(extras)}"
        )
