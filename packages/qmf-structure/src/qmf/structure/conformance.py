"""CT-17 — the concept-walk conformance register (COMP-QMF-STRUCTURE).

CT-17 carries a **conformance register**: the concept-walk test list the contract must keep
expressible, derived from the increment gate's edge-case lenses and adversarial pass, whose
must-fix findings are folded into the CT-17 invariants and **bind conformance tests at tier
2** (DEC-0131, DEC-0102). This module is the machine-readable form of that list, so the
conformance suite iterates it rather than restating it — an item that becomes inexpressible,
or a register that drifts from the suite, fails the gate.

Each :class:`ConceptWalkItem` is one concept the CT-17 surface must express. The conformance
suite (``tests/test_ct17_conformance.py``) builds each item from the public surface — points,
zones, levels, distributions, composites, sloped objects, calendar-anchored levels, the
append-only lifecycle, refits, and the result label — and asserts it constructs, so "the
register stays expressible" is proven mechanically every run. The suite also asserts every
register member is covered, so the two can never drift apart.

This module imports nothing outside the standard library: the register is pure vocabulary.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

__all__ = [
    "CONCEPT_WALK_REGISTER",
    "ConceptWalkItem",
]


class ConceptWalkItem(StrEnum):
    """One concept the CT-17 surface must keep expressible (CT-17 conformance register;
    DEC-0131, DEC-0102).

    The member value is the concept-walk description from CT-17's ``conformance_register``; the
    member name is the stable key the conformance suite binds a builder to.
    """

    RETRO_ANCHORED_ZONES = "retro-anchored zones with consumption state"
    BORN_FROM_INVALIDATION = "objects born from another object's invalidation"
    TOLERANCE_CLUSTERS = "cluster objects over tolerance-grouped extremes"
    THRESHOLD_BREACH_REVERSAL = "threshold-breach-then-reversal objects"
    CALENDAR_COMPOSITES = "ordered multi-phase calendar composites"
    MULTI_BARSPEC_NESTS = "multi-BarSpec nests"
    CROSS_INSTRUMENT_DIVERGENCE = "cross-instrument divergence objects"
    DISTRIBUTION_OVER_PRICE = "distribution-over-price objects"
    A_PRIORI_PRICE_GRIDS = "a-priori price grids"
    PROJECTED_LEVELS = "projected levels"
    PATTERN_REFITS = "pattern refits"


# The concept-walk register in its canonical order (CT-17 conformance_register). The
# conformance suite binds exactly one builder to each member; an inexpressible item, or a
# register/suite drift, fails the tier-2 gate (DEC-0131, DEC-0102).
CONCEPT_WALK_REGISTER: Final[tuple[ConceptWalkItem, ...]] = tuple(ConceptWalkItem)
