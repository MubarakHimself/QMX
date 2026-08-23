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
from qml.families import (
    FAMILY_KEYED_SURFACES,
    FORBIDDEN_AUTHORITY_FIELDS,
    KIND_STRATEGY_FAMILY,
    STRATEGY_FAMILY_KIND_FORMAT_VERSION,
    FamilyKeyedSurface,
    StrategyFamilyId,
    StrategyFamilyRecord,
    mint_strategy_family,
    resolve_family_at_layer1,
)
from qml.footprint import ProducerBindingForm, parse_binding_form
from qml.logic import (
    LOGIC_REFERENCE_CLASS,
    LogicIdentity,
    fingerprint_source_manifest,
    mint_logic_identity,
    normalize_source_manifest,
    resolve_logic_at_layer1,
)
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
    "FAMILY_KEYED_SURFACES",
    "FORBIDDEN_AUTHORITY_FIELDS",
    "KIND_STRATEGY_FAMILY",
    "LOGIC_REFERENCE_CLASS",
    "PROTOCOL_FORMAT_VERSION",
    "REGISTRY_ENVELOPE_FORMAT_VERSION",
    "STRATEGY_FAMILY_KIND_FORMAT_VERSION",
    "AuthoredArtifact",
    "AuthoredKind",
    "BotCallback",
    "BotFactory",
    "BotIntent",
    "ConformanceTicket",
    "FamilyKeyedSurface",
    "LogicIdentity",
    "ProducerBindingForm",
    "ReadSurface",
    "StrategyFamilyId",
    "StrategyFamilyRecord",
    "__version__",
    "evaluate_ticket",
    "fingerprint_source_manifest",
    "mint_logic_identity",
    "mint_strategy_family",
    "normalize_source_manifest",
    "parse_binding_form",
    "permitted_exit_kinds",
    "resolve_family_at_layer1",
    "resolve_logic_at_layer1",
]

# Display-only provenance — never part of fp1 identity (DEC-0180).
__version__ = "0.1.0"
