"""CT-10 — the bitemporal source-observation value types (COMP-QMF-DATA).

The public value vocabulary of the CT-10 boundary: an external fact that lands as
**bitemporal, source-attributed evidence**. Every observation preserves *when it
occurred* (``event_time``) and *when it became knowable* (``known_at``), the read-only
``source`` it came from (a provenance noun ORTHOGONAL to VenueId), the provider's own
``revision``, an AD-8 :class:`~qmf.core.WriterId` with a per-writer strictly-increasing
``sequence``, its ``world``, and its ``fp1`` identity — computed by the single
``qmf-core`` implementation and **nowhere else** (AC1; DEC-0117, DEC-0108).

Three things this module pins down.

**Verbatim foreign evidence, never a silent rewrite (AC2; DEC-0106, DEC-0105).** A
foreign timestamp is kept exactly as received (:class:`ForeignTimestamp`: the verbatim
string plus its declared zone, offset, and source resolution) alongside a
:class:`~qmf.core.Instant` ``receive_wall_time`` in int64 UTC nanoseconds. Foreign money
is kept verbatim as a scaled integer at the SOURCE's declared scale
(:class:`ForeignMoney`). Neither is ever converted or rescaled here: a conversion to
framework Time or Money is a *derived* artifact carrying lineage, produced elsewhere,
never a rewrite of this evidence.

**Corrections append, they never overwrite (AC3; DEC-0117).** A correction is itself a
:class:`SourceObservation` — a distinct artifact with its own ``fp1`` — carrying
``correction_of`` set to the corrected observation's ``fp1``. It refers to the same
provider-native occurrence under a new ``revision``, so its fingerprint differs and it
can never fold inline or masquerade as the original. Read-time resolution of the
annotation is deferred in V1 (DEC-0117).

**Completeness is enforced at construction (AC4/FM-1; DEC-0109).** The frozen dataclass
constructor is the trusted-internal path; :meth:`SourceObservation.try_create` is the
validating factory that returns value-or-refusal. A record lacking event-time, known-at,
source, revision, writer, or a computable ``fp1`` identity is an ``invalid input`` typed
refusal and never enters governed evidence.

The ``receive_monotonic_diagnostic`` is an opaque, boot-scoped diagnostic: never an
Instant, never rendered as a time, **excluded from identity**, and not persisted as
durable evidence (it is meaningless across boots). Every other field is identity by
default (the fp1 recipe's rule), so :meth:`SourceObservation.fp1_identity` folds in all
of them and only them.

Stdlib + qmf-core (fp1 comes only from qmf-core). Frozen, immutable values throughout.

Value types, construction, and row reconstruction live in sibling modules;
this module re-exports the public names so existing import paths keep working.
"""

from __future__ import annotations

from qmf.data.observation_source import SourceObservation
from qmf.data.observation_types import (
    CONTRACT_FORMAT_VERSION,
    ForeignMoney,
    ForeignTimestamp,
    MarketDataContext,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "ForeignMoney",
    "ForeignTimestamp",
    "MarketDataContext",
    "SourceObservation",
]
