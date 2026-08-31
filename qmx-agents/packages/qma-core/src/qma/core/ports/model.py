"""ModelDeployment port — multi contribution ``model_deployment`` (CT-45; AD-1, AD-15)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["ModelDeployment"]


@runtime_checkable
class ModelDeployment(Protocol):
    """Definitions-only ModelDeployment seam; keyed ``<plugin_id>:<local_id>``.

    Cardinality: multi (see ``PORT_CONTRACTS``).
    """
