"""Host-owned composition-root surface for Layer-2 sandbox execution (QL-8).

This package is impure: it owns stdlib process spawning and isolation. The rest
of ``qml`` stays pure per AD-15 — do not import this module from the library
surface. Hosts (QMB, later the trading node) import it at their composition root
and feed observations to QML's pure verdict function (DEC-0178).
"""

from __future__ import annotations

from qml.host.runner import (
    FACTORY_KIND_SILENT,
    FACTORY_KIND_SOURCE,
    V1_DEFERRED_OS_CONFINEMENT,
    V1_ENFORCEMENT_MECHANISMS,
    V1_OUT_OF_SCOPE,
    FactorySpec,
    run_sandbox,
    v1_enforcement_identity,
)

__all__ = [
    "FACTORY_KIND_SILENT",
    "FACTORY_KIND_SOURCE",
    "V1_DEFERRED_OS_CONFINEMENT",
    "V1_ENFORCEMENT_MECHANISMS",
    "V1_OUT_OF_SCOPE",
    "FactorySpec",
    "run_sandbox",
    "v1_enforcement_identity",
]
