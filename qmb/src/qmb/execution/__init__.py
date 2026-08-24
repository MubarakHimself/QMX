"""Fill, slippage, cost, and financing ports plus adapters (B-6).

Inbound execution is a CT-23 Book-resolved intent (or a typed refusal). Ports
execute an authorized intent, never a bot-sized order, and never a venue
command (DEC-0164).
"""

from __future__ import annotations

from typing import Final, TypeAlias

from qmf.risk.door import EntryIntent, ExitIntent

__all__ = ["PORT_ROLES", "AuthorizedIntent", "ports_identity"]

AuthorizedIntent: TypeAlias = EntryIntent | ExitIntent

PORT_ROLES: Final[tuple[str, ...]] = (
    "fill",
    "slippage",
    "cost",
    "financing",
)


def ports_identity() -> dict[str, object]:
    """Identity-bearing execution-port fields. Package SemVer is omitted."""
    return {
        "port_roles": PORT_ROLES,
        "authorized_intent": (
            f"{EntryIntent.__module__}.{EntryIntent.__qualname__}",
            f"{ExitIntent.__module__}.{ExitIntent.__qualname__}",
        ),
    }
