"""qmf.structure — causal chart-object families.

Roster package of the QMF V1 uv workspace. It re-exports the public CT-17 surface as it
lands story by story.

Landed (Story 9.1): the causal structure object mint and the in-component emission
invariant. :class:`FamilyIdentity` (opaque id + version + open, family-declared
geometry), :class:`ConfirmationRule` (the declared 'confirmed the moment X happens'
rule), and the :class:`StructureFamily` ``typing.Protocol`` seam with its reference
:class:`DeclaredFamily`; :class:`AnchorSpan` (start/end instants and exact-``Price``
bounds, frozen at observation); :class:`StructureObject`, minted **once at observation**
carrying family identity + version, exact-rational parameters, its confirmation rule,
its anchor span, ``observed_at`` (knowledge time — known-at, never event time), and its
evidence class — every field identity-bearing, the object never mutated; and
:func:`check_emission_invariant`, enforcing
``anchor.start <= anchor.end <= observed_at <= confirmed_at <= invalidated_at`` and
``observed_at >= the maximum evidence time of every consumed input`` as an
``invalid input`` refusal on violation (FM-1), the interim look-ahead guard independent
of the deferred GAP-0016 gate (DEC-0129, DEC-0121, DEC-0114).

Landed (Story 9.2): the append-only lifecycle and the read-time state fold.
:class:`ConfirmationRecord`, :class:`InvalidationRecord`, and :class:`InteractionRecord`
are separate append-only typed records referencing the object by ``fp1`` fingerprint, each
instant an identity field of its own record; interaction records are the only permitted
way an object's state evolves. :func:`resolve_state` folds an object's record stream to a
knowledge time T — "still valid at T" is a **read-time fold** (:class:`ResolvedState`),
never a stored field. :func:`refit` mints a new artifact with a ``supersedes``
:class:`LifecycleEdge` and keeps the lineage's first observed-at, so a correction never
overwrites (FM-3). :func:`admit_to_governed_library` is the FM-2 admission gate (imprecise
concepts stay in the ungoverned research lane; clock-confirmed is legal). Invalidation
never cascades automatically: a family declares an :class:`InvalidationPredicate` and a
reader calls :func:`resolve_cascade` to compute cascade at read time (DEC-0129, DEC-0131,
DEC-0114).

Landed (Story 9.3): evidence class as first-class identity, knowledge-time provenance, and
split-manifest governance. :func:`read_confirmed` is the governed read requesting confirmed
evidence — it refuses an unconfirmed or provisional row with a ``policy rejection``, never a
silent filter (FM-4), over the :class:`EvidenceRow` seam both a :class:`StructureObject` and
a :class:`~qmf.core.ResultLabel` satisfy. :func:`may_consume` is the knowledge-time
consumption rule (``confirmed-at <= T``; equality is consumption) and :func:`causally_precedes`
the distinct refuse-at-equal causality test. :func:`structure_result_label` builds the CT-05
result label — the configured-family producer identity plus input fingerprints, so a revised
input yields a different label by construction; ``world = simulated`` is refused (GAP-0048).
:func:`evaluate_citation` (:class:`CitationKind`, :class:`GovernanceVerdict`) is the
governed-evidence citation law — in-memory persists nothing, a journal-event or result-label
citation makes the object governed evidence — and :func:`promote_scanned` promotes only
confirmed scan hits. :func:`required_embargo_width` turns a family's confirmation-delay bound
into a split embargo width (an unbounded family is excluded from split-governed evidence), and
:func:`admit_across_boundary` (:class:`SplitAdmission`) is the FM-7 boundary refusal —
partitioning by confirmed-at (DEC-0129, DEC-0131, DEC-0119, DEC-0110).

Landed (Story 9.4): the first governed family, the CT-17 conformance harness, and the
light/heavy benchmark policy. :class:`SwingPointFamily` is the first governed family from the
seed candidates — a swing-point family whose confirmation rule is precise, consuming
:class:`PriceObservation` source/bar inputs as declared inputs, holding no privilege over
operator-authored peers and naming no trading school (FM-9). :class:`CompositeObject`,
:class:`SlopedObject`, and :class:`CalendarAnchoredLevel` extend the geometry so the CT-17
concept-walk :data:`~qmf.structure.conformance.CONCEPT_WALK_REGISTER` stays fully expressible.
:func:`route` is the CT-16/CT-17 routing test and :func:`consume_indicator_input` the FM-6
declared-input consumption (a family consumes an indicator's result, never re-implements it).
:class:`BenchmarkRung`, :class:`DeclaredBudget`, :func:`evaluate_light_claim`, and
:func:`check_regression` are the light/heavy four-bound policy over the three structure rungs —
a light claim exceeding a bound or lacking a baseline is refused, and a peak-memory regression
fails exactly as a slowdown does (FM-8). :func:`graduate_to_governed` is the escape-hatch
graduation: an ungoverned experiment enters governed evidence only through the extension shape
with a ``promoted-from`` lineage edge to the originating experiment (L33). The benchmark harness
(:mod:`qmf.structure._bench`) has the same standing as the unit tests (DEC-0129, DEC-0128,
DEC-0126, DEC-0133).

Every ``fp1`` fingerprint is computed in ``qmf-core`` and nowhere else; this package
imports **only** ``qmf.core`` in V1 (the default-deny dependency direction, L30). The
library returns fingerprintable content and never stamps records — the composition root
holds the ``WriterId`` and the gapless per-(writer, kind) sequence and mints the registry
records (DEC-0120, DEC-0129).
"""

from __future__ import annotations

from qmf.structure.budget import (
    BenchmarkRung,
    DeclaredBudget,
    LightVerdict,
    Measurement,
    RegressionVerdict,
    check_regression,
    evaluate_light_claim,
)
from qmf.structure.composites import (
    CompositeChild,
    CompositeObject,
)
from qmf.structure.conformance import (
    CONCEPT_WALK_REGISTER,
    ConceptWalkItem,
)
from qmf.structure.families import (
    SWING_POINT_CONFIRMATION_RULE,
    HighLowObservation,
    PriceObservation,
    SwingKind,
    SwingPoint,
    SwingPointFamily,
)
from qmf.structure.geometry import (
    AnchorPoint,
    CalendarAnchoredLevel,
    EvaluationRuleRef,
    SamplingPolicy,
    ScheduleGapPolicy,
    SlopedObject,
)
from qmf.structure.lifecycle import (
    CascadeResolution,
    ConfirmationRecord,
    InteractionRecord,
    InvalidationPredicate,
    InvalidationRecord,
    LifecycleEdge,
    LifecycleEdgeKind,
    LifecycleRecord,
    Refit,
    ResolvedState,
    admit_to_governed_library,
    refit,
    resolve_cascade,
    resolve_state,
)
from qmf.structure.objects import (
    CONTRACT_FORMAT_VERSION,
    KNOWN_GEOMETRIES,
    AnchorSpan,
    ConfirmationRule,
    DeclaredFamily,
    EmissionWitness,
    FamilyIdentity,
    StructureFamily,
    StructureObject,
    check_emission_invariant,
)
from qmf.structure.provenance import (
    CitationKind,
    EvidenceRow,
    GovernanceVerdict,
    causally_precedes,
    evaluate_citation,
    may_consume,
    promote_scanned,
    read_confirmed,
    structure_result_label,
)
from qmf.structure.research import (
    Graduation,
    GraduationEdge,
    graduate_to_governed,
)
from qmf.structure.routing import (
    IndicatorResultInput,
    RoutingKind,
    consume_indicator_input,
    route,
)
from qmf.structure.splits import (
    SplitAdmission,
    admit_across_boundary,
    required_embargo_width,
)

__all__ = [
    "CONCEPT_WALK_REGISTER",
    "CONTRACT_FORMAT_VERSION",
    "KNOWN_GEOMETRIES",
    "SWING_POINT_CONFIRMATION_RULE",
    "AnchorPoint",
    "AnchorSpan",
    "BenchmarkRung",
    "CalendarAnchoredLevel",
    "CascadeResolution",
    "CitationKind",
    "CompositeChild",
    "CompositeObject",
    "ConceptWalkItem",
    "ConfirmationRecord",
    "ConfirmationRule",
    "DeclaredBudget",
    "DeclaredFamily",
    "EmissionWitness",
    "EvaluationRuleRef",
    "EvidenceRow",
    "FamilyIdentity",
    "GovernanceVerdict",
    "Graduation",
    "GraduationEdge",
    "HighLowObservation",
    "IndicatorResultInput",
    "InteractionRecord",
    "InvalidationPredicate",
    "InvalidationRecord",
    "LifecycleEdge",
    "LifecycleEdgeKind",
    "LifecycleRecord",
    "LightVerdict",
    "Measurement",
    "PriceObservation",
    "Refit",
    "RegressionVerdict",
    "ResolvedState",
    "RoutingKind",
    "SamplingPolicy",
    "ScheduleGapPolicy",
    "SlopedObject",
    "SplitAdmission",
    "StructureFamily",
    "StructureObject",
    "SwingKind",
    "SwingPoint",
    "SwingPointFamily",
    "__version__",
    "admit_across_boundary",
    "admit_to_governed_library",
    "causally_precedes",
    "check_emission_invariant",
    "check_regression",
    "consume_indicator_input",
    "evaluate_citation",
    "evaluate_light_claim",
    "graduate_to_governed",
    "may_consume",
    "promote_scanned",
    "read_confirmed",
    "refit",
    "required_embargo_width",
    "resolve_cascade",
    "resolve_state",
    "route",
    "structure_result_label",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
