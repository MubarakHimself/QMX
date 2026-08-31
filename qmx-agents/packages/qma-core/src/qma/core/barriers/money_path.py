"""Act-level money-path deny-list constants (FR-Q09; DEC-0315).

Declared as code beside the capability ladder. Nothing — configuration, plugin
declaration, Role, Mission, hook, toolset, tool_adapter, or capability rung —
may widen this set. The daemon refuses matching tools at registration with
``ProhibitedMoneyPathTool``.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from qma.core.refusals.variants import ProhibitedMoneyPathTool

__all__ = [
    "MONEY_PATH_DENY_LIST",
    "MONEY_PATH_DENY_LIST_OWNER",
    "MoneyPathAct",
    "MoneyPathDenyError",
    "assert_deny_list_not_widenable",
    "is_money_path_act_denied",
    "parse_money_path_act",
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


# Closed deny-list. Membership is the entire MoneyPathAct vocabulary; callers
# never receive an API that adds members.
MONEY_PATH_DENY_LIST: Final[frozenset[MoneyPathAct]] = frozenset(MoneyPathAct)

MONEY_PATH_DENY_LIST_OWNER: Final[str] = "AD-16"


class MoneyPathDenyError(ValueError):
    """Raised when the deny-list constant is misused or illegally widened."""


def parse_money_path_act(value: MoneyPathAct | str) -> MoneyPathAct:
    """Parse a money-path act family; invented values fail."""
    if isinstance(value, MoneyPathAct):
        return value
    try:
        return MoneyPathAct(value)
    except ValueError as exc:
        raise MoneyPathDenyError(f"{value!r} is not a money-path act family") from exc


def is_money_path_act_denied(act: MoneyPathAct | str) -> bool:
    """True when ``act`` is on the code-declared deny-list."""
    try:
        return parse_money_path_act(act) in MONEY_PATH_DENY_LIST
    except MoneyPathDenyError:
        return False


def refuse_money_path_registration(
    *,
    tool_id: str,
    act: MoneyPathAct | str,
    plugin_id: str | None = None,
) -> ProhibitedMoneyPathTool:
    """Build the registration refusal for a deny-listed act.

    Returns a typed refusal — never raises across the package boundary (CT-04).
    """
    resolved = parse_money_path_act(act)
    if resolved not in MONEY_PATH_DENY_LIST:
        raise MoneyPathDenyError(
            f"{resolved.value!r} is not on MONEY_PATH_DENY_LIST (impossible for enum members)"
        )
    return ProhibitedMoneyPathTool.of(
        tool_id=tool_id,
        matched_act=resolved.value,
        plugin_id=plugin_id,
    )


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
        return
    allowed_values = {act.value for act in MONEY_PATH_DENY_LIST}
    proposed_values = {
        item.value if isinstance(item, MoneyPathAct) else str(item) for item in proposed
    }
    extras = proposed_values - allowed_values
    if extras:
        raise MoneyPathDenyError(
            "money-path deny-list cannot be widened by configuration, plugin "
            f"declaration, or capability rung; extras={sorted(extras)}"
        )
