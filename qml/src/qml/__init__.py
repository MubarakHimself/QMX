"""qml — the QMX bot-authoring library.

One uv-installable pure distribution (``import qml``), an application-layer
product built on QMF, never a roster package, never a framework, never an
engine, and never a CLI (DEC-0171, DEC-0185). Imports ``qmf-core``,
``qmf-registry``, and ``qmf-risk`` only; never ``qmf-venue``.

``__version__`` is display-only SemVer provenance and never enters ``fp1``
(DEC-0180). Identity lives on CT-33 content and the logic source-manifest.
"""

from __future__ import annotations

from qml.conformance import (
    CONFORMANCE_FORMAT_VERSION,
    DENIAL_SET,
    ConformanceTicket,
    evaluate_ticket,
)
from qml.declaration import (
    REGISTRY_ENVELOPE_FORMAT_VERSION,
    AuthoredArtifact,
    AuthoredKind,
)
from qml.families import StrategyFamilyId
from qml.footprint import ProducerBindingForm, parse_binding_form
from qml.protocol import (
    PROTOCOL_FORMAT_VERSION,
    BotCallback,
    BotFactory,
    BotIntent,
    ReadSurface,
    permitted_exit_kinds,
)

__all__ = [
    "CONFORMANCE_FORMAT_VERSION",
    "DENIAL_SET",
    "PROTOCOL_FORMAT_VERSION",
    "REGISTRY_ENVELOPE_FORMAT_VERSION",
    "AuthoredArtifact",
    "AuthoredKind",
    "BotCallback",
    "BotFactory",
    "BotIntent",
    "ConformanceTicket",
    "ProducerBindingForm",
    "ReadSurface",
    "StrategyFamilyId",
    "__version__",
    "evaluate_ticket",
    "parse_binding_form",
    "permitted_exit_kinds",
]

# Display-only provenance — never part of fp1 identity (DEC-0180).
__version__ = "0.1.0"
