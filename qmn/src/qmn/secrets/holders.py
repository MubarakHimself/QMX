"""Four named VPS secret holders and no fifth (TN-12 / DEC-0227).

Each holder may resolve only its exact systemd-creds slot names. ``kek`` is the
store's key-encryption key, not a holder-resolved credential.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Final

from qmf.core.refusal import TypedRefusal

from qmn.secrets._refuse import policy

__all__ = [
    "BACKUP_SLOTS",
    "BACKUP_UNIT",
    "BOOTSTRAP_SLOT_NAMES",
    "CONNECTION_MANAGER",
    "HOLDER_SLOTS",
    "KEK_SLOT",
    "NAMED_HOLDERS",
    "NEVER_VPS_MINTED_SLOTS",
    "NOTIFICATION_PATH",
    "NOTIFICATION_SLOTS",
    "OBSERVABILITY_SLOTS",
    "OBSERVABILITY_STACK",
    "VENUE_SESSION_SLOTS",
    "VPS_MINTED_SLOTS",
    "WORKSTATION_SLOTS",
    "extra_holders",
    "holder_for_slot",
    "refuse_fifth_holder",
    "refuse_holder_scope",
    "refuse_unknown_holder",
    "slot_in_holder",
]

CONNECTION_MANAGER: Final[str] = "connection_manager"
BACKUP_UNIT: Final[str] = "backup_unit"
NOTIFICATION_PATH: Final[str] = "notification_path"
OBSERVABILITY_STACK: Final[str] = "observability_stack"

NAMED_HOLDERS: Final[frozenset[str]] = frozenset(
    {
        CONNECTION_MANAGER,
        BACKUP_UNIT,
        NOTIFICATION_PATH,
        OBSERVABILITY_STACK,
    }
)

KEK_SLOT: Final[str] = "kek"
VENUE_SESSION_SLOTS: Final[frozenset[str]] = frozenset(
    {
        "venue-client-id",
        "venue-client-secret",
        "venue-access-token",
        "venue-refresh-token",
        "venue-ctid-accounts",
    }
)
BACKUP_SLOTS: Final[frozenset[str]] = frozenset({"backup-payload-key", "object-storage"})
NOTIFICATION_SLOTS: Final[frozenset[str]] = frozenset({"notification-token"})
OBSERVABILITY_SLOTS: Final[frozenset[str]] = frozenset({"grafana-admin", "log-shipper-token"})

HOLDER_SLOTS: Final[Mapping[str, frozenset[str]]] = MappingProxyType(
    {
        CONNECTION_MANAGER: VENUE_SESSION_SLOTS,
        BACKUP_UNIT: BACKUP_SLOTS,
        NOTIFICATION_PATH: NOTIFICATION_SLOTS,
        OBSERVABILITY_STACK: OBSERVABILITY_SLOTS,
    }
)

VPS_MINTED_SLOTS: Final[frozenset[str]] = frozenset({KEK_SLOT})
NEVER_VPS_MINTED_SLOTS: Final[frozenset[str]] = frozenset({"backup-payload-key"})
WORKSTATION_SLOTS: Final[frozenset[str]] = (
    VENUE_SESSION_SLOTS | BACKUP_SLOTS | NOTIFICATION_SLOTS | OBSERVABILITY_SLOTS
)
BOOTSTRAP_SLOT_NAMES: Final[frozenset[str]] = WORKSTATION_SLOTS | VPS_MINTED_SLOTS

_SLOT_TO_HOLDER: Final[Mapping[str, str]] = MappingProxyType(
    {slot: holder for holder, slots in HOLDER_SLOTS.items() for slot in slots}
)


def extra_holders(declared: Iterable[str]) -> tuple[str, ...]:
    """Holders outside the closed four-name set (a fifth holder)."""
    return tuple(sorted({name for name in declared if name not in NAMED_HOLDERS}))


def holder_for_slot(slot: str) -> str | None:
    """Named holder that owns ``slot``, or ``None`` for the KEK / unknown."""
    return _SLOT_TO_HOLDER.get(slot)


def slot_in_holder(holder: str, slot: str) -> bool:
    """True when ``slot`` is in the closed catalog for ``holder``."""
    return slot in HOLDER_SLOTS.get(holder, frozenset())


def refuse_unknown_holder(holder: str) -> TypedRefusal:
    """A fifth or unnamed holder cannot resolve any reference."""
    return policy(
        "holder",
        "only the four named VPS secret holders may resolve credentials",
        failure_id="secrets.holder.unknown",
        holder=holder,
    )


def refuse_fifth_holder(extra: Iterable[str]) -> TypedRefusal:
    """Preflight/scanner refusal when a fifth holder is declared."""
    return policy(
        "holder",
        "a fifth secret holder is forbidden",
        failure_id="secrets.holder.fifth",
        extra_holders=tuple(sorted(extra)),
    )


def refuse_holder_scope(*, holder: str, slot: str, secret_ref: str) -> TypedRefusal:
    """Holder asked to resolve a slot outside its closed catalog."""
    return policy(
        "holder",
        "a named holder may resolve only its exact credential references",
        failure_id="secrets.holder.scope",
        holder=holder,
        slot=slot,
        secret_ref=secret_ref,
    )
