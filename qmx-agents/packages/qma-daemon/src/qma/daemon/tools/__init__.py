"""Tool Registry, capability ladder, money-path deny-list (AD-16).

Registration validators import the code-declared ladder and deny-list from
``qma.core.barriers`` (FR-Q09; DEC-0315). This package will host the runtime
registry; the constants themselves stay definitions-only in core.
"""

from __future__ import annotations

from qma.core.barriers import (
    CAPABILITY_LADDER,
    MONEY_PATH_DENY_LIST,
    CapabilityRung,
    MoneyPathAct,
    assert_deny_list_not_widenable,
    assert_ladder_is_code_declared,
    is_money_path_act_denied,
    refuse_money_path_registration,
)

__all__ = [
    "CAPABILITY_LADDER",
    "MONEY_PATH_DENY_LIST",
    "CapabilityRung",
    "MoneyPathAct",
    "assert_deny_list_not_widenable",
    "assert_ladder_is_code_declared",
    "is_money_path_act_denied",
    "refuse_money_path_registration",
]
