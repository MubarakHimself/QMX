"""Closed powers and principal allow-lists shared by library and transport."""

from __future__ import annotations

from typing import Final

__all__ = [
    "CLOSED_POWERS",
    "OPERATOR_ONLY_POWERS",
    "OPS_ALLOWED_POWERS",
]

# Ops principal may call only these powers (plus evidence reads on the other door).
OPS_ALLOWED_POWERS: Final[frozenset[str]] = frozenset(
    {
        "notify_test",
        "restore_drill_run",
        "config_validate",
        "hub_publish",
    }
)

# Operator-only powers refused to ops BY THE TRANSPORT before handler dispatch.
OPERATOR_ONLY_POWERS: Final[frozenset[str]] = frozenset(
    {
        "resurrect",
        "resume",
        "de_escalate",
        "resolve_unknown",
        "flatten",
        "kill_switch_escalate",
        "paper_flip",
        "paper_epoch_reset",
        "promotion_sign",
        "activation",
        "config_version_activate",
        "seat_reinstate",
        "state_carry",
        "carries_ledger",
        "continues_performance",
        "value_status_countersign",
        "sealed_period_final_look",
        "settings_edit",
        "secrets_is_set",
        "attestation",
        "countersign",
    }
)

CLOSED_POWERS: Final[frozenset[str]] = OPS_ALLOWED_POWERS | OPERATOR_ONLY_POWERS
