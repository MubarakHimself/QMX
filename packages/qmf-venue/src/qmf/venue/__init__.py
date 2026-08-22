"""qmf.venue — the venue seam (edge module nothing imports).

Roster package of the QMF V1 uv workspace. It imports only ``qmf-core`` and nothing
imports it — the default-deny dependency direction (L30/DEC-0120) holds by
construction.

Story 8.1 lands the first work unit: the cTrader capability probe and the
per-(VenueId, account) venue-observation profile it records. The probe connects to a
demo venue through a throwaway :class:`~qmf.venue.probe.ProbeTransport` seam, runs the
first-connection verify-or-refuse suite (spot-timestamp unit, daily boundary, bar
basis, pip formula, money exponent), and returns its recorded profile plus a findings
note surfacing contradictions with upstream assumptions (FR-022, FR-026, SC-02,
AR-45/AR-46; DEC-0135, DEC-0138). The port contracts CT-18..CT-21 and the connection
manager land in later stories; the probe deliberately depends on none of them.

Story 8.2 adds the in-house proto compilation (:mod:`qmf.venue.proto`): the Spotware
``openapi-proto-messages`` release is compiled from its message definitions (data, not
code) through the ``protobuf`` runtime — a qmf-venue-only dependency — pinned at the
injected AD-6 integer release tag, so the adapter owns its own transport, zero Spotware
SDK code runs, and a tag change is a governed re-verification event (AR-43, FR-026,
DEC-0141). Importing ``google.protobuf`` here is the module's only third-party import;
a compiled proto message never leaks into ``qmf-core``.

Story 8.3 adds the connection manager, the secret lifecycle, and injected-sink wiring
(:mod:`qmf.venue.connection`): the :class:`~qmf.venue.connection.ConnectionManager` is
the sole owner of venue sessions and the single in-memory holder of secret *values*,
fed by a composition-root-injected :class:`~qmf.core.SecretStore` port (read + atomic
replace) and calling the injected core sink protocols synchronously. Credentials never
leave it and never render; rotation is store-before-discard; a ``storage failure`` from
any command-path sink blocks the command stream while the sensing pipe is unaffected;
and an :class:`~qmf.venue.connection.AccountBinding`'s secret reference is
occurrence/display-only and excluded from fp1 (CT-21, AR-37, AR-38, AR-47; DEC-0136,
DEC-0138).
"""

from __future__ import annotations

from qmf.venue.connection import (
    AccountBinding,
    BlockCause,
    CommandPipeStatus,
    ConnectionManager,
    HealthReport,
    PipeState,
    venue_command_stream,
    venue_writer_id,
)
from qmf.venue.observation import (
    MeasuredFact,
    ProbeCheck,
    ProbeVerdict,
    VenueEvidenceClass,
    VenueObservationProfile,
)
from qmf.venue.probe import (
    AccountMoneyRecord,
    CapabilityProbe,
    Finding,
    FindingsNote,
    ProbeReport,
    ProbeTransport,
    SpotSample,
    SymbolMetadataRecord,
    Tick,
    TickHistorySample,
    Trendbar,
    TrendbarSample,
    UpstreamAssumption,
)
from qmf.venue.proto import (
    SPOTWARE_PROTO_PACKAGE,
    CompiledProto,
    ProtoArtifact,
    TagChangeAssessment,
    assess_tag_change,
    compile_descriptor_set,
    descriptor_set_digest,
)

__all__ = [
    "SPOTWARE_PROTO_PACKAGE",
    "AccountBinding",
    "AccountMoneyRecord",
    "BlockCause",
    "CapabilityProbe",
    "CommandPipeStatus",
    "CompiledProto",
    "ConnectionManager",
    "Finding",
    "FindingsNote",
    "HealthReport",
    "MeasuredFact",
    "PipeState",
    "ProbeCheck",
    "ProbeReport",
    "ProbeTransport",
    "ProbeVerdict",
    "ProtoArtifact",
    "SpotSample",
    "SymbolMetadataRecord",
    "TagChangeAssessment",
    "Tick",
    "TickHistorySample",
    "Trendbar",
    "TrendbarSample",
    "UpstreamAssumption",
    "VenueEvidenceClass",
    "VenueObservationProfile",
    "__version__",
    "assess_tag_change",
    "compile_descriptor_set",
    "descriptor_set_digest",
    "venue_command_stream",
    "venue_writer_id",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
