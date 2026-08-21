"""qmf.data — evidence rooms, splits, journals, and backups.

Roster package of the QMF V1 uv workspace. Story 3.1 lands the dependency-free
persistence seam ``COMP-QMF-DATA-STORE`` (:mod:`qmf.data.store`): the CT-11
append-store, CT-13 journal, CT-09 registry room, and CT-26 store-to-backup
boundaries, over the four ratified engines (Parquet, DuckDB, SQLite, JSONL), keyed
on fp1 fingerprints and instantiated per world. The public data-policy contracts
(CT-10 observations, CT-12 splits, the entity-journal projections) land in later
stories on top of this seam.

``qmf.data`` imports only ``qmf-core`` (the fp1 vocabulary and typed refusals) plus
its own engine libraries — the default-deny dependency direction (L30) holds, and the
ratified ``qmf-registry → qmf-data`` edge points AT this package.
"""

from __future__ import annotations

from qmf.data.store import EvidenceStore

__all__ = ["EvidenceStore", "__version__"]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
