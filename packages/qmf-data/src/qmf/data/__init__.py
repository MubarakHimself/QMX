"""qmf.data — evidence rooms, splits, journals, and backups.

Roster package of the QMF V1 uv workspace. Story 3.1 lands the dependency-free
persistence seam ``COMP-QMF-DATA-STORE`` (:mod:`qmf.data.store`): the CT-11
append-store, CT-13 journal, CT-09 registry room, and CT-26 store-to-backup
boundaries, over the four ratified engines (Parquet, DuckDB, SQLite, JSONL), keyed
on fp1 fingerprints and instantiated per world. Story 3.2 lands the CT-10
source-observation boundary on top of that seam: the bitemporal fact law
(:class:`SourceObservation` with verbatim :class:`ForeignTimestamp` /
:class:`ForeignMoney`), append-only corrections, and the world/refusal gates
(:class:`SourceObservationBoundary`). Story 3.3 lands the data-policy owner of the
seven room-roles per world (:class:`WorldRooms`): rebuildable analytics views that
record their rebuild pins (:class:`RebuildPins`), the ``(source, instrument,
time-window)`` series partition (:class:`SeriesPartition`, :class:`SeriesPlacement`,
:class:`ResolvedSeries`), and the keep-forever-vs-deletion-licensed retention law
(:class:`RetentionPolicy` over the injected :class:`CitationIndex`, yielding a
:class:`RetentionVerdict`). The remaining data-policy contracts (CT-12 splits, the
entity-journal projections) land in later stories on the same seam.

``qmf.data`` imports only ``qmf-core`` (the fp1 vocabulary and typed refusals) plus
its own engine libraries — the default-deny dependency direction (L30) holds, and the
ratified ``qmf-registry → qmf-data`` edge points AT this package.
"""

from __future__ import annotations

from qmf.data.observation import ForeignMoney, ForeignTimestamp, SourceObservation
from qmf.data.partitions import ResolvedSeries, SeriesPartition, SeriesPlacement
from qmf.data.retention import CitationIndex, RetentionPolicy, RetentionVerdict
from qmf.data.rooms import RebuildPins, WorldRooms
from qmf.data.source_boundary import ObservationReceipt, SourceObservationBoundary
from qmf.data.store import EvidenceStore

__all__ = [
    "CitationIndex",
    "EvidenceStore",
    "ForeignMoney",
    "ForeignTimestamp",
    "ObservationReceipt",
    "RebuildPins",
    "ResolvedSeries",
    "RetentionPolicy",
    "RetentionVerdict",
    "SeriesPartition",
    "SeriesPlacement",
    "SourceObservation",
    "SourceObservationBoundary",
    "WorldRooms",
    "__version__",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
