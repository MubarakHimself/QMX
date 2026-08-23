"""CT-17 — the ungoverned research lane and graduation to governed evidence (COMP-QMF-STRUCTURE).

**The escape hatch is the design's point (L33; DEC-0129, DEC-0133).** Any concept a family
cannot yet state precisely stays **freely usable in plain Python outside governed evidence** —
a researcher explores it with the full public surface without ever admitting it. It enters
governed evidence only by **graduating through the extension shape**: an operator-authored
family, admitted through the same law as any seed candidate, carrying a lineage edge to the
originating experiment so the provenance of the graduated concept is never lost.

**Graduation carries a promoted-from lineage edge (DEC-0114, DEC-0129).**
:func:`graduate_to_governed` admits a family (its confirmation rule must be precise — the FM-2
gate) and returns a :class:`Graduation`: the admitted family plus a **promoted-from**
:class:`GraduationEdge` from the graduated governed artifact to the originating research
experiment. ``promoted-from`` is a ratified CT-07 lineage edge type; this module returns the
edge as fingerprintable content and never stamps it — the composition root mints the CT-07
edge with its ``WriterId``. An imprecise concept has no precise confirmation rule, so it never
graduates and stays in the research lane, exactly as intended.

Default-deny holds: this module imports **only** ``qmf.core`` and the sibling
``qmf.structure`` value types. Public value types are frozen dataclasses, and every operation
succeeds or RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain failure is never raised
across the boundary (DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core import (
    Fingerprint,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.structure.lifecycle import admit_to_governed_library
from qmf.structure.objects import CONTRACT_FORMAT_VERSION, StructureFamily

__all__ = [
    "Graduation",
    "GraduationEdge",
    "graduate_to_governed",
]

# The CT-07 lineage edge type a graduation records — a ratified edge type, never a new mint
# (DEC-0114). It points from the graduated governed artifact to the originating experiment.
PROMOTED_FROM_EDGE_TYPE: str = "promoted-from"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a graduation operation returns (CT-04; DEC-0109)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


@dataclass(frozen=True, slots=True)
class GraduationEdge:
    """A ``promoted-from`` lineage edge intent from a graduated artifact to its experiment
    (CT-07, CT-17; DEC-0114, DEC-0129).

    ``from_ref`` is the graduated governed artifact's ``fp1``; ``to_ref`` the originating
    research experiment's ``fp1``. It carries no ``WriterId``: the composition root mints the
    full CT-07 edge. Its fingerprint is derived from its content.
    """

    from_ref: Fingerprint
    to_ref: Fingerprint

    @property
    def edge_type(self) -> str:
        """The ratified CT-07 edge type — ``promoted-from`` (DEC-0114)."""
        return PROMOTED_FROM_EDGE_TYPE

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this graduation edge intent."""
        return {
            "class": "structure-graduation-edge",
            "edge_type": PROMOTED_FROM_EDGE_TYPE,
            "from_ref": self.from_ref.value,
            "to_ref": self.to_ref.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The edge intent's ``fp1`` fingerprint, computed in qmf-core (DEC-0108)."""
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class Graduation:
    """An admitted family plus its lineage edge to the originating experiment (CT-17; L33,
    DEC-0129, DEC-0133).

    ``family`` is the admitted governed family; ``graduated_ref`` the graduated governed
    artifact's ``fp1``; ``originating_experiment_ref`` the research experiment's ``fp1``; and
    ``promoted_from_edge`` the ``promoted-from`` edge intent linking them. It is returned only
    when graduation succeeds.
    """

    family: StructureFamily
    graduated_ref: Fingerprint
    originating_experiment_ref: Fingerprint
    promoted_from_edge: GraduationEdge


def graduate_to_governed(
    *, family: object, graduated_ref: object, originating_experiment_ref: object
) -> Result[Graduation]:
    """Graduate a family into governed evidence with a lineage edge to its experiment (L33;
    FM-2; DEC-0129, DEC-0133).

    Admits ``family`` through the same governed-library gate as any seed candidate — its
    confirmation rule must be precise, or the imprecise concept stays in the ungoverned research
    lane — and returns a :class:`Graduation` carrying a ``promoted-from`` edge from
    ``graduated_ref`` (the graduated governed artifact) to ``originating_experiment_ref`` (the
    research experiment). Both refs are ``fp1`` fingerprints. No seed candidate is privileged:
    an operator-authored family graduates identically.
    """
    admitted = admit_to_governed_library(family)
    if is_refusal(admitted):
        return admitted
    graduated = _coerce_fingerprint(graduated_ref)
    if graduated is None:
        return _invalid(
            "graduated_ref",
            "the graduated governed artifact is referenced by an fp1 fingerprint",
            given=repr(graduated_ref),
        )
    experiment = _coerce_fingerprint(originating_experiment_ref)
    if experiment is None:
        return _invalid(
            "originating_experiment_ref",
            "the originating research experiment is referenced by an fp1 fingerprint (L33)",
            given=repr(originating_experiment_ref),
        )
    if graduated == experiment:
        return _invalid(
            "originating_experiment_ref",
            "a graduation links a governed artifact to a distinct originating experiment; the "
            "two fingerprints cannot be the same artifact",
            ref=graduated.value,
        )
    return Ok(
        Graduation(
            family=admitted.value,
            graduated_ref=graduated,
            originating_experiment_ref=experiment,
            promoted_from_edge=GraduationEdge(from_ref=graduated, to_ref=experiment),
        )
    )
