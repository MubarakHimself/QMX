"""Footprint producer bindings, template resolution, and horizon derivation (QL-4).

The footprint is the single canonical consumption manifest: nested stream set,
required calendars, and producer bindings as pinned fingerprints or complete
templates. Template resolution is a total single-valued function producing one
CT-16/CT-17 configured-producer fingerprint. The warm-up/embargo horizon is
derived from the resolved producer chain — never a second hand-declared window
(DEC-0174).
"""

from __future__ import annotations

from qml.footprint.horizon import Horizon, derive_horizon
from qml.footprint.manifest import (
    CompletenessReport,
    Footprint,
    ProducerBinding,
    StreamMember,
    compute_transitive_union,
    mint_footprint,
    report_completeness,
)
from qml.footprint.template import (
    ProducerTemplate,
    ResolvedProducer,
    mint_producer_template,
    resolve_template,
)
from qml.footprint.vocab import (
    AD22_IDENTITY_FIELDS,
    BARSPEC_KINDS,
    CT16_FORMAT_VERSION,
    FORBIDDEN_HORIZON_FIELDS,
    AlignmentPolicy,
    BarSpecKind,
    ChannelKind,
    MissingValuePolicy,
    ProducerBindingForm,
    ProducerKind,
    StreamRole,
    SupportedMode,
    parse_binding_form,
)

__all__ = [
    "AD22_IDENTITY_FIELDS",
    "BARSPEC_KINDS",
    "CT16_FORMAT_VERSION",
    "FORBIDDEN_HORIZON_FIELDS",
    "AlignmentPolicy",
    "BarSpecKind",
    "ChannelKind",
    "CompletenessReport",
    "Footprint",
    "Horizon",
    "MissingValuePolicy",
    "ProducerBinding",
    "ProducerBindingForm",
    "ProducerKind",
    "ProducerTemplate",
    "ResolvedProducer",
    "StreamMember",
    "StreamRole",
    "SupportedMode",
    "compute_transitive_union",
    "derive_horizon",
    "mint_footprint",
    "mint_producer_template",
    "parse_binding_form",
    "report_completeness",
    "resolve_template",
]
