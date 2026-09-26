"""Blank-effect gating over a resolved node-config (DEC-0231, DEC-0256).

Boot, live-role, and soak gates read value-status on the artifact. A
provisional-evidence value that gates live money blocks ``role = live`` exactly
as a blank does until countersign.
"""

from __future__ import annotations

from typing import Final

from qmn.config.compiler import ResolvedNodeConfig
from qmn.config.registry_catalog import (
    BLANK_EFFECT_BOOT,
    BLANK_EFFECT_LIVE,
    BLANK_EFFECT_SOAK,
    EXPECTED_BLANK_EFFECT_COUNTS,
    VALUE_STATUS_REQUIRED_ROWS,
)

__all__ = [
    "blank_effect_coverage",
    "live_role_blocked_by",
    "provisional_live_gates_like_blank",
]


def blank_effect_coverage() -> dict[str, int]:
    """Count blank-effect tags across the 71-row catalog (AR-80)."""
    counts = {
        BLANK_EFFECT_BOOT: 0,
        BLANK_EFFECT_LIVE: 0,
        BLANK_EFFECT_SOAK: 0,
    }
    for row in VALUE_STATUS_REQUIRED_ROWS:
        for effect in row["blank_effect"]:
            counts[effect] = counts.get(effect, 0) + 1
    return counts


def live_role_blocked_by(config: ResolvedNodeConfig) -> tuple[str, ...]:
    """Names that block ``role = live`` (blank or provisional live-gating)."""
    return config.live_blocking_rows()


def provisional_live_gates_like_blank(config: ResolvedNodeConfig) -> bool:
    """True when every provisional live-gating row is treated as blocking live."""
    for row in config.rows.values():
        if BLANK_EFFECT_LIVE not in row.blank_effect:
            continue
        if row.value_status == "provisional-evidence" and not row.blocks_role_live:
            return False
    return True


# Pin the AR-80 totals for importers that assert without re-counting.
AR80_BLANK_EFFECT_TOTALS: Final[dict[str, int]] = dict(EXPECTED_BLANK_EFFECT_COUNTS)
