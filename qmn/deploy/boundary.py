"""Operations-toolkit boundary for ``qmn/deploy`` (TN-1/TN-16/TN-17; AR-79).

Recipe bodies under ``justfile-recipes/`` are DevOps only. They never import the
composition root (``qmn.host``) or the in-process Python API door, and they
never place, cancel, amend, flatten, promote, or activate. Forbidden powers
also include settings, resurrect, attestation, and countersign — refused at
the ops principal transport (Story 25.7 / QMX-F045). Recipes run only as the
ops principal; trading authority is never acquired by calling the same endpoint.

This module is intentionally outside ``src/qmn`` so deploy tooling stays a
separate process surface from the composition root.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "ALLOWED_NODE_RECIPES",
    "FORBIDDEN_DEPLOY_IMPORTS",
    "FORBIDDEN_RECIPE_ACTIONS",
    "OPS_PRINCIPAL_NAME",
    "OPS_TOOLKIT_SURFACE",
    "deploy_may_import",
    "recipe_action_allowed",
    "toolkit_principal",
]

OPS_TOOLKIT_SURFACE: Final[str] = "qmn.deploy"
# Recipes act only as the ops principal on the powers channel (DEC-0202).
OPS_PRINCIPAL_NAME: Final[str] = "ops"


def toolkit_principal() -> str:
    """The constrained principal every ``just node-…`` recipe runs as."""
    return OPS_PRINCIPAL_NAME

# Closed allow-list of just node-… recipe names (AR-79). Bodies land later.
ALLOWED_NODE_RECIPES: Final[frozenset[str]] = frozenset(
    {
        "node-install",
        "node-switch",
        "node-rollback",
        "node-secrets-provision",
        "node-data-bootstrap",
        "node-replay",
        "node-config-init",
        "node-config-validate",
        "node-config-explain",
        "node-notify-test",
        "node-hub-publish",
        "node-host-loss-restore",
    }
)

FORBIDDEN_RECIPE_ACTIONS: Final[frozenset[str]] = frozenset(
    {
        "place",
        "cancel",
        "amend",
        "flatten",
        "promote",
        "activate",
        "settings",
        "resurrect",
        "attestation",
        "countersign",
    }
)

# Deploy scripts must not reach the composition root or Python API door.
FORBIDDEN_DEPLOY_IMPORTS: Final[frozenset[str]] = frozenset(
    {
        "qmn.host",
        "qmn.doors",
        "qmn.doors.api",
        "qmn.doors.http",
    }
)


def recipe_action_allowed(action: str) -> bool:
    """False for every trading/protection/promotion control verb."""
    return action.casefold() not in FORBIDDEN_RECIPE_ACTIONS


def deploy_may_import(module: str) -> bool:
    """False when a deploy script would import the composition root or API door."""
    if module in FORBIDDEN_DEPLOY_IMPORTS:
        return False
    return not any(
        module == banned or module.startswith(f"{banned}.")
        for banned in FORBIDDEN_DEPLOY_IMPORTS
    )
