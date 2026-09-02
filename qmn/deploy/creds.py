"""systemd-creds argv contract for the restricted provisioning wizard (TN-12).

Host-key seal is pinned ``--with-key=host`` (never ``--with-key=auto``).
Plaintext travels on SSH stdin only — never argv, never a file, never echoed.
The backup payload key is never minted on the VPS. DevOps only: no qmn.host
import, no trading control.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

__all__ = [
    "BOOTSTRAP_SLOT_NAMES",
    "CREDSTORE_ENCRYPTED",
    "FORBIDDEN_SEAL_FLAG",
    "FORBIDDEN_SSH_IDENTITIES",
    "KEK_SLOT",
    "NEVER_VPS_MINTED_SLOTS",
    "PROVISIONING_SSH_IDENTITY",
    "SEAL_FLAG",
    "VPS_MINTED_SLOTS",
    "WORKSTATION_SLOTS",
    "argv_contains_plaintext",
    "remote_encrypt_argv",
    "ssh_stdin_encrypt_argv",
    "validate_provisioning_identity",
    "validate_seal_flag",
]

CREDSTORE_ENCRYPTED: Final[str] = "/etc/credstore.encrypted"
SEAL_FLAG: Final[str] = "--with-key=host"
FORBIDDEN_SEAL_FLAG: Final[str] = "--with-key=auto"
PROVISIONING_SSH_IDENTITY: Final[str] = "provisioning"
FORBIDDEN_SSH_IDENTITIES: Final[frozenset[str]] = frozenset({"operator", "hub-inbox-write"})
KEK_SLOT: Final[str] = "kek"
WORKSTATION_SLOTS: Final[tuple[str, ...]] = (
    "venue-client-id",
    "venue-client-secret",
    "venue-access-token",
    "venue-refresh-token",
    "venue-ctid-accounts",
    "backup-payload-key",
    "object-storage",
    "notification-token",
    "grafana-admin",
    "log-shipper-token",
)
VPS_MINTED_SLOTS: Final[frozenset[str]] = frozenset({KEK_SLOT})
NEVER_VPS_MINTED_SLOTS: Final[frozenset[str]] = frozenset({"backup-payload-key"})
BOOTSTRAP_SLOT_NAMES: Final[tuple[str, ...]] = (KEK_SLOT, *WORKSTATION_SLOTS)

_SSH_OPTIONS: Final[tuple[str, ...]] = (
    "-o",
    "IdentitiesOnly=yes",
    "-o",
    "BatchMode=yes",
    "-o",
    "PasswordAuthentication=no",
    "-o",
    "KbdInteractiveAuthentication=no",
    "-o",
    "PreferredAuthentications=publickey",
)


def validate_seal_flag(flag: str) -> str | None:
    """Return a finding when the seal is not host-key pinned."""
    if flag == FORBIDDEN_SEAL_FLAG or flag != SEAL_FLAG:
        return f"seal must be {SEAL_FLAG} (forbidden: {FORBIDDEN_SEAL_FLAG})"
    return None


def validate_provisioning_identity(identity: str) -> str | None:
    """Return a finding when the SSH identity is not the restricted provisioning key."""
    if identity in FORBIDDEN_SSH_IDENTITIES or identity != PROVISIONING_SSH_IDENTITY:
        return (
            "provisioning uses the dedicated key-only SSH identity "
            f"{PROVISIONING_SSH_IDENTITY!r}, never {sorted(FORBIDDEN_SSH_IDENTITIES)}"
        )
    return None


def remote_encrypt_argv(slot: str) -> tuple[str, ...]:
    """Passwordless-sudo ``systemd-creds encrypt`` reading plaintext from stdin."""
    if slot not in BOOTSTRAP_SLOT_NAMES:
        msg = f"unknown systemd-creds slot {slot!r}"
        raise ValueError(msg)
    return (
        "sudo",
        "-n",
        "--",
        "systemd-creds",
        "encrypt",
        SEAL_FLAG,
        f"--name={slot}",
        "-",
        f"{CREDSTORE_ENCRYPTED}/{slot}",
    )


def ssh_stdin_encrypt_argv(
    *,
    host: str,
    identity_file: str,
    slot: str,
) -> tuple[str, ...]:
    """Local SSH argv. Plaintext is the process stdin, never an argument."""
    remote = remote_encrypt_argv(slot)
    return (
        "ssh",
        "-i",
        identity_file,
        *_SSH_OPTIONS,
        "--",
        host,
        *remote,
    )


def argv_contains_plaintext(argv: Sequence[str], material: str) -> bool:
    """True when ``material`` leaked into any argv token."""
    if not material:
        return False
    return any(material in token for token in argv)
