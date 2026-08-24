"""QMB composition-root hosting for conformant CT-33 bots (QL-7, QL-8).

The QL-7 adapter is pure. ``run_sandbox`` is the impure Layer-2 runner — it is
not re-exported from ``import qmb``. Ungoverned plain-Python bots never import
this package.
"""

from __future__ import annotations

from qmb.host.adapter import (
    ConformantSliceHandler,
    FunctionFactory,
    HostedBot,
    construct_conformant_bot,
    drive_instant,
)
from qmb.host.sandbox import run_sandbox

__all__ = [
    "ConformantSliceHandler",
    "FunctionFactory",
    "HostedBot",
    "construct_conformant_bot",
    "drive_instant",
    "run_sandbox",
]
