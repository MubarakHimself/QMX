"""Node-config surface (TN-18): resolved artifact home, no runtime folds.

Compilation later applies roster → BMS → Book → node-defaults with value-status
rows. The scaffold declares the layer names and that there is no invocation or
operator-CLI override layer (DEC-0203, DEC-0211).
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "COMPILE_LAYERS",
    "CONFIG_SURFACE",
    "HAS_INVOCATION_OVERRIDE_LAYER",
    "compile_layers",
]

CONFIG_SURFACE: Final[str] = "qmn.config"
COMPILE_LAYERS: Final[tuple[str, ...]] = (
    "roster",
    "bms",
    "book",
    "node_defaults",
)
HAS_INVOCATION_OVERRIDE_LAYER: Final[bool] = False


def compile_layers() -> tuple[str, ...]:
    """Fixed compile layers; never an invocation/runtime override layer."""
    return COMPILE_LAYERS
