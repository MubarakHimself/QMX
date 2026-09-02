"""Node secret store, rotation contract, and holder scan (TN-12 / Story 27.1).

The operations-toolkit wizard lives under ``qmn/deploy/`` so it cannot import
the connection manager or the refresh duty. This package is the VPS-side
SecretStore: two-layer systemd-creds + AEAD rotated state, four named holders
and no fifth, store-before-discard, one refresher per opaque reference.
"""

from __future__ import annotations

from typing import Final

from qmn.secrets.drill import (
    COMPROMISE_DRILL_STEPS,
    DEMO_CREDENTIAL_CLASS,
    CompromiseDrillReport,
    run_compromise_drill,
)
from qmn.secrets.holders import (
    BACKUP_SLOTS,
    BACKUP_UNIT,
    BOOTSTRAP_SLOT_NAMES,
    CONNECTION_MANAGER,
    HOLDER_SLOTS,
    KEK_SLOT,
    NAMED_HOLDERS,
    NEVER_VPS_MINTED_SLOTS,
    NOTIFICATION_PATH,
    NOTIFICATION_SLOTS,
    OBSERVABILITY_SLOTS,
    OBSERVABILITY_STACK,
    VENUE_SESSION_SLOTS,
    VPS_MINTED_SLOTS,
    WORKSTATION_SLOTS,
    extra_holders,
    holder_for_slot,
    refuse_fifth_holder,
    refuse_holder_scope,
    refuse_unknown_holder,
    slot_in_holder,
)
from qmn.secrets.rotation import RotationGate
from qmn.secrets.scan import (
    FORBIDDEN_SURFACE_KEYS,
    scan_holder_declaration,
    scan_payload_for_secret_values,
    scan_store_presence,
)
from qmn.secrets.store import (
    AEAD_NONCE_SIZE,
    BLOB_MAGIC,
    KEK_SIZE,
    ROTATED_STATE_DIRNAME,
    FilesystemBlobStore,
    NodeSecretStore,
    os_aead_nonce,
    try_create_secret_store,
)

__all__ = [
    "AEAD_NONCE_SIZE",
    "BACKUP_SLOTS",
    "BACKUP_UNIT",
    "BLOB_MAGIC",
    "BOOTSTRAP_SLOT_NAMES",
    "COMPROMISE_DRILL_STEPS",
    "CONNECTION_MANAGER",
    "DEMO_CREDENTIAL_CLASS",
    "FORBIDDEN_SURFACE_KEYS",
    "HOLDER_SLOTS",
    "KEK_SIZE",
    "KEK_SLOT",
    "NAMED_HOLDERS",
    "NEVER_VPS_MINTED_SLOTS",
    "NOTIFICATION_PATH",
    "NOTIFICATION_SLOTS",
    "OBSERVABILITY_SLOTS",
    "OBSERVABILITY_STACK",
    "ROTATED_STATE_DIRNAME",
    "SECRETS_SURFACE",
    "VENUE_SESSION_SLOTS",
    "VPS_MINTED_SLOTS",
    "WORKSTATION_SLOTS",
    "CompromiseDrillReport",
    "FilesystemBlobStore",
    "NodeSecretStore",
    "RotationGate",
    "extra_holders",
    "holder_for_slot",
    "os_aead_nonce",
    "refuse_fifth_holder",
    "refuse_holder_scope",
    "refuse_unknown_holder",
    "run_compromise_drill",
    "scan_holder_declaration",
    "scan_payload_for_secret_values",
    "scan_store_presence",
    "slot_in_holder",
    "try_create_secret_store",
]

SECRETS_SURFACE: Final[str] = "qmn.secrets"
