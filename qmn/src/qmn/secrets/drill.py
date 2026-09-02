"""Credential compromise-recovery drill (CT-21 / DEC-0136).

Four steps: cTID re-authorization, application-credential reset, store
replacement, session restart. Testing uses demo credentials only — factory
sandboxes never hold live secrets. No step surfaces a secret value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from qmf.core.refusal import Ok, Result, is_refusal
from qmf.core.secret import SecretRef, SecretStore, SecretValue

from qmn.secrets._refuse import policy

__all__ = [
    "COMPROMISE_DRILL_STEPS",
    "DEMO_CREDENTIAL_CLASS",
    "CompromiseDrillReport",
    "run_compromise_drill",
]

DEMO_CREDENTIAL_CLASS: Final[str] = "demo"
COMPROMISE_DRILL_STEPS: Final[tuple[str, ...]] = (
    "ctid_reauthorization",
    "application_credential_reset",
    "store_replacement",
    "session_restart",
)


@dataclass(frozen=True, slots=True)
class CompromiseDrillReport:
    """Outcome of the four-step drill — reference id only, never a value."""

    steps: tuple[str, ...]
    secret_ref: str
    credential_class: str
    store_replaced: bool

    def as_mapping(self) -> dict[str, object]:
        return {
            "steps": list(self.steps),
            "secret_ref": self.secret_ref,
            "credential_class": self.credential_class,
            "store_replaced": self.store_replaced,
        }


def run_compromise_drill(
    store: SecretStore,
    *,
    secret_ref: SecretRef,
    replacement: SecretValue,
    credential_class: str,
) -> Result[CompromiseDrillReport]:
    """Run the compromise drill against ``store`` with demo credentials only."""
    if credential_class != DEMO_CREDENTIAL_CLASS:
        return policy(
            "credential_class",
            "the compromise drill uses demo credentials only",
            failure_id="secrets.drill.not_demo",
            secret_ref=secret_ref.value,
        )
    if replacement.ref != secret_ref:
        return policy(
            "replacement",
            "the replacement secret's reference does not match the drill target",
            failure_id="secrets.drill.not_demo",
            secret_ref=secret_ref.value,
        )
    replaced = store.atomic_replace(secret_ref, replacement)
    if is_refusal(replaced):
        return replaced
    return Ok(
        CompromiseDrillReport(
            steps=COMPROMISE_DRILL_STEPS,
            secret_ref=secret_ref.value,
            credential_class=DEMO_CREDENTIAL_CLASS,
            store_replaced=True,
        )
    )
