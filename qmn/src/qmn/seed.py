"""FEAT-0031 structural seed roster (AR-72).

Folder names under ``src/qmn`` plus the out-of-package ``deploy/`` ops toolkit.
``order/`` is the landed order-path surface (Epic 24); AR-72's ``orderpath/``
name maps to it. ``host/`` is the composition-root surface.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "DEPLOY_SEED_DIRS",
    "SRC_SEED_PACKAGES",
    "structural_seed_packages",
]

# Python packages under src/qmn (loop/venue/order already shipped by Epic 24).
SRC_SEED_PACKAGES: Final[tuple[str, ...]] = (
    "host",
    "loop",
    "venue",
    "order",
    "protection",
    "ledger",
    "paper",
    "reconcile",
    "seats",
    "promotion",
    "mis",
    "data",
    "time",
    "secrets",
    "config",
    "observability",
    "doors",
    "replay",
    "bench",
)

# Ops toolkit lives beside src/, never as a second authority inside the root.
DEPLOY_SEED_DIRS: Final[tuple[str, ...]] = (
    "justfile-recipes",
    "systemd",
    "observability",
)


def structural_seed_packages() -> tuple[str, ...]:
    """FEAT-0031 src package seed names."""
    return SRC_SEED_PACKAGES
