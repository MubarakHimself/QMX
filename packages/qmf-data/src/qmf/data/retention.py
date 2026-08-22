"""The retention law — keep-forever evidence vs deletion-licensed views (AC3).

`COMP-QMF-DATA` keeps raw originals and lineage forever, and a rebuildable artifact
a result label cites is likewise kept forever; deletion is licensed **only** for a
rebuildable artifact that no result label cites (DEC-0117, DEC-0118). This module is
the one place that verdict is computed, so no caller has to re-derive "may I delete
this?" from the receipt fields.

Two facts drive every verdict:

* the artifact's write-time intrinsic retention — :class:`~qmf.data.store.StoreReceipt`
  carries ``retained_forever = True`` for the immutable raw archive, the journal, and
  the registry room's records and lineage edges (evidence and lineage, kept regardless
  of citation), and ``retained_forever = False`` for a rebuildable analytics view; and
* whether any governed result label cites the artifact — answered by an injected
  :class:`CitationIndex` seam, because result labels live in the registry, not here
  (default-deny: ``qmf-data`` never imports ``qmf-registry``, DEC-0120).

A rebuildable view is *effectively* retained forever the moment a result label cites
it, even though its receipt recorded ``retained_forever = False`` at write time — so
the verdict, not the write-time field, is the authority on whether deletion is
licensed.

Stdlib + qmf-core only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from qmf.core import Fingerprint
from qmf.data.store import StoreReceipt

__all__ = ["CitationIndex", "RetentionPolicy", "RetentionVerdict"]


class CitationIndex(Protocol):
    """Whether any governed result label cites the artifact under a given fp1 (AC3).

    Result labels (the AD-12 computed-result identities) live in the registry, not in
    ``qmf-data``; under default-deny this package never imports ``qmf-registry`` and so
    cannot read them directly. The composition root injects this seam — an object that
    answers "does any result label's ``input_fingerprints`` include this fp1?" — so the
    retention verdict can license deletion of a rebuildable view only once it is sure no
    result cites it (DEC-0120, DEC-0117).
    """

    def cites(self, fingerprint: Fingerprint, /) -> bool:  # pragma: no cover - protocol
        """Whether any result label cites the artifact keyed by ``fingerprint``."""
        ...


@dataclass(frozen=True, slots=True)
class RetentionVerdict:
    """The retention decision for one stored artifact (AC3).

    ``retained_forever`` is the *effective* retention — true for evidence and lineage
    always, and true for a rebuildable view the moment a result label cites it.
    ``deletion_licensed`` is its exact inverse: deletion is licensed only for a
    rebuildable artifact no result label cites, and never for evidence, lineage, or a
    cited view. ``reason`` is register-facing plain language naming which rule applied,
    so an operator reviewing a deletion sees why it was or was not permitted.
    """

    retained_forever: bool
    deletion_licensed: bool
    reason: str


class RetentionPolicy:
    """Computes the AC3 retention verdict for a stored artifact, over a citation seam.

    Constructed with a :class:`CitationIndex`; :meth:`verdict_for` reads a store receipt
    and returns whether the artifact is retained forever and whether deletion is
    licensed. The policy is pure with respect to the receipt — it never deletes anything
    itself; it only rules on whether a deletion would be licensed, leaving the physical
    drop to the caller that owns the room.
    """

    def __init__(self, citations: CitationIndex) -> None:
        self._citations = citations

    def verdict_for(self, receipt: StoreReceipt) -> RetentionVerdict:
        """The retention verdict for the artifact ``receipt`` describes (AC3).

        Raw originals, the journal, and the registry room's records and lineage edges
        carry ``retained_forever = True`` on the receipt — they are kept forever
        regardless of citation, and deletion is never licensed. A rebuildable analytics
        view carries ``retained_forever = False``: the citation seam decides it — a
        result label citing it makes it effectively retained forever (deletion refused),
        and only a view no result label cites is deletion-licensed.
        """
        if receipt.retained_forever:
            return RetentionVerdict(
                retained_forever=True,
                deletion_licensed=False,
                reason=(
                    f"{receipt.room_role.value} artifacts are evidence or lineage and are "
                    "kept forever; deletion is never licensed (DEC-0117, DEC-0118)"
                ),
            )
        if self._citations.cites(receipt.fingerprint):
            return RetentionVerdict(
                retained_forever=True,
                deletion_licensed=False,
                reason=(
                    "a result label cites this rebuildable artifact, so it is retained "
                    "forever and deletion is not licensed (DEC-0117)"
                ),
            )
        return RetentionVerdict(
            retained_forever=False,
            deletion_licensed=True,
            reason=(
                "no result label cites this rebuildable artifact, so its deletion is "
                "licensed — a format break costs a rebuild, never evidence (DEC-0117, DEC-0118)"
            ),
        )

    def may_delete(self, receipt: StoreReceipt) -> bool:
        """Whether deleting the artifact ``receipt`` describes is licensed (AC3)."""
        return self.verdict_for(receipt).deletion_licensed
