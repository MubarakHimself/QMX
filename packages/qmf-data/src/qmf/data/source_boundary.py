"""CT-10 — the source-observation boundary, owned by COMP-QMF-DATA (AC1–AC5).

The one ratified reader of the CT-10 boundary. Producers — the Data-Ingest door and
venue-originated market data — submit :class:`~qmf.data.observation.SourceObservation`
**values** routed by the application; this boundary admits them as governed, bitemporal,
source-attributed evidence and hands each write down to the Story 3.1 store seam's
immutable raw archive (evidence-bearing, kept forever). qmf-data owns the boundary; no
downstream library reads it directly under default-deny (DEC-0120).

What this boundary guarantees (its five acceptance criteria):

* **AC1/AC4** — only a complete :class:`SourceObservation` enters. Its ``fp1`` identity
  is computed by ``qmf-core`` at construction; a record lacking event-time, known-at,
  source, revision, writer, or a computable identity is an ``invalid input`` refusal and
  never reaches storage.
* **AC2** — foreign timestamps and foreign money ride along verbatim (the value type
  keeps them unrewritten); this boundary never converts or rescales them.
* **AC3** — a correction (``correction_of`` set, same provider-native occurrence under a
  new revision) is admitted as a *distinct* raw-archive artifact with its own ``fp1``.
  The original is untouched (the archive is append-only and content-addressed), so a
  correction can never overwrite or masquerade as the original.
* **AC5** — writing ``world = simulated`` is a ``policy rejection`` (the store has no
  governed simulated namespace), and reading evidence from a different world than the
  caller declares is a ``policy rejection`` — world isolation is storage separation.

Storage-failure translation and the true-fp1-collision alarm are inherited from the
store seam (its FR-1 / FR-2): a physical failure comes back as a ``storage failure``
refusal, never an exception across the seam, and no success is reported on failure.

Stdlib + qmf-core + the qmf-data store seam.
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core import Fingerprint, Ok, Result, Retryability, is_refusal
from qmf.data.observation import SourceObservation
from qmf.data.store import EvidenceStore, StoreReceipt
from qmf.data.store.refusals import invalid_input, storage_failure

__all__ = ["ObservationReceipt", "SourceObservationBoundary"]


@dataclass(frozen=True, slots=True)
class ObservationReceipt:
    """The receipt of an admitted source observation (AC1, AC3).

    ``observation_fingerprint`` is the observation's own ``fp1`` — its evidence identity,
    the value a correction references and a governed reader cites. ``archive`` is the
    Story 3.1 store receipt for the immutable-raw-archive artifact that physically holds
    it (its own content-addressed key, world, and idempotent/stored outcome).
    ``is_correction`` and ``correction_of`` surface the append-only correction linkage
    without the reader re-opening the stored row.
    """

    observation_fingerprint: Fingerprint
    archive: StoreReceipt
    is_correction: bool
    correction_of: Fingerprint | None


class SourceObservationBoundary:
    """The CT-10 boundary over the Story 3.1 store seam (AC1–AC5).

    Constructed with an :class:`~qmf.data.store.EvidenceStore`; each admitted observation
    lands in its own world's immutable raw archive. The boundary adds the CT-10 fact-law
    and world gates on top of the store's content-addressing and world separation — it
    never re-implements identity (that is ``qmf-core``) or physical persistence (that is
    the store seam).
    """

    def __init__(self, store: EvidenceStore) -> None:
        self._store = store

    def admit(self, observation: object) -> Result[ObservationReceipt]:
        """Admit a :class:`SourceObservation` into governed CT-10 evidence (AC1–AC5).

        A value that is not a complete :class:`SourceObservation` does not enter — an
        ``invalid input`` refusal (AC4/FM-1); completeness and the ``fp1`` identity are
        already enforced by :meth:`SourceObservation.try_create`, so reaching this method
        with a built value means the bitemporal parts are present. The observation's own
        ``world`` routes the write: ``world = simulated`` has no governed namespace and is
        a ``policy rejection`` (AC5). The observation is written verbatim (foreign
        timestamp and money unrewritten) into the immutable raw archive, keyed by the
        artifact's content address; a byte-identical re-admit is idempotent, a correction
        is a distinct artifact, and any engine failure is a ``storage failure`` refusal
        surfaced by the store seam (AC2, AC3).
        """
        if not isinstance(observation, SourceObservation):
            return invalid_input(
                "observation",
                "a value that is not a complete SourceObservation does not enter governed "
                "CT-10 evidence; build it through SourceObservation.try_create first (FM-1)",
                given=repr(observation),
            )
        world_store = self._store.for_world(observation.world)
        if is_refusal(world_store):
            return world_store
        appended = world_store.value.append_store.append_raw([observation.to_row()])
        if is_refusal(appended):
            return appended
        return Ok(
            ObservationReceipt(
                observation_fingerprint=observation.fingerprint,
                archive=appended.value,
                is_correction=observation.is_correction,
                correction_of=observation.correction_of,
            )
        )

    def read(
        self, archive_fingerprint: object, *, in_world: object, for_world: object
    ) -> Result[SourceObservation]:
        """Read one admitted observation back from the archive (AC5).

        ``archive_fingerprint`` is the artifact key from an :class:`ObservationReceipt`
        (``receipt.archive.fingerprint``). ``in_world`` names the world whose room holds
        the evidence; ``for_world`` is the world the caller declares it is reading as. A
        read whose declared ``for_world`` differs from the evidence's world is a ``policy
        rejection`` — one world's room never serves another's evidence (AC5). A
        ``world = simulated`` room has no governed namespace and is likewise refused. A
        well-formed key that names no stored artifact is a ``stale evidence`` miss, and a
        physical failure is a ``storage failure`` refusal — both surfaced by the store
        seam. The row round-trips through :meth:`SourceObservation.from_row`, which
        re-verifies the ``fp1`` so a corrupt row never reads back as valid.
        """
        world_store = self._store.for_world(in_world)
        if is_refusal(world_store):
            return world_store
        rows = world_store.value.append_store.read_raw(archive_fingerprint, for_world=for_world)
        if is_refusal(rows):
            return rows
        materialized = rows.value
        if len(materialized) != 1:
            return storage_failure(
                "a source-observation artifact holds exactly one observation row, but the "
                f"stored artifact held {len(materialized)}; the evidence is corrupt",
                retryability=Retryability.NO,
                context={"rows": len(materialized), "fingerprint": repr(archive_fingerprint)},
            )
        return SourceObservation.from_row(materialized[0])
