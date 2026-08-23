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
    CONFLUENCE_KIND_FORMAT_VERSION,
    FORBIDDEN_CONDITION_FIELDS,
    KIND_CONFLUENCE,
    LEG_ROLES,
    REGISTRY_ENVELOPE_FORMAT_VERSION,
    AuthoredArtifact,
    AuthoredKind,
    Confluence,
    ConfluenceLeg,
    ConfluenceOrdering,
    LegRole,
    confluence_kind_contract,
    install_confluence_kind,
    mint_confluence,
    parse_leg_role,
    parse_ordering,
    register_confluence,
    resolve_confluence_at_layer1,
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
from qml.footprint import (
    AD22_IDENTITY_FIELDS,
    CompletenessReport,
    Footprint,
    Horizon,
    ProducerBinding,
    ProducerBindingForm,
    ProducerKind,
    ProducerTemplate,
    ResolvedProducer,
    StreamMember,
    StreamRole,
    derive_horizon,
    mint_footprint,
    mint_producer_template,
    parse_binding_form,
    report_completeness,
    resolve_template,
)
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
    "AD22_IDENTITY_FIELDS",
    "CONFLUENCE_KIND_FORMAT_VERSION",
    "CONFORMANCE_FORMAT_VERSION",
    "DENIAL_SET",
    "FAMILY_KEYED_SURFACES",
    "FORBIDDEN_AUTHORITY_FIELDS",
    "FORBIDDEN_CONDITION_FIELDS",
    "KIND_CONFLUENCE",
    "KIND_STRATEGY_FAMILY",
    "LEG_ROLES",
    "LOGIC_REFERENCE_CLASS",
    "PROTOCOL_FORMAT_VERSION",
    "REGISTRY_ENVELOPE_FORMAT_VERSION",
    "STRATEGY_FAMILY_KIND_FORMAT_VERSION",
    "AuthoredArtifact",
    "AuthoredKind",
    "BotCallback",
    "BotFactory",
    "BotIntent",
    "CompletenessReport",
    "Confluence",
    "ConfluenceLeg",
    "ConfluenceOrdering",
    "ConformanceTicket",
    "FamilyKeyedSurface",
    "Footprint",
    "Horizon",
    "LegRole",
    "LogicIdentity",
    "ProducerBinding",
    "ProducerBindingForm",
    "ProducerKind",
    "ProducerTemplate",
    "ReadSurface",
    "ResolvedProducer",
    "StrategyFamilyId",
    "StrategyFamilyRecord",
    "StreamMember",
    "StreamRole",
    "__version__",
    "confluence_kind_contract",
    "derive_horizon",
    "evaluate_ticket",
    "fingerprint_source_manifest",
    "install_confluence_kind",
    "mint_confluence",
    "mint_footprint",
    "mint_logic_identity",
    "mint_producer_template",
    "mint_strategy_family",
    "normalize_source_manifest",
    "parse_binding_form",
    "parse_leg_role",
    "parse_ordering",
    "permitted_exit_kinds",
    "register_confluence",
    "report_completeness",
    "resolve_confluence_at_layer1",
    "resolve_family_at_layer1",
    "resolve_logic_at_layer1",
    "resolve_template",
]

# Display-only provenance — never part of fp1 identity (DEC-0180).
__version__ = "0.1.0"
