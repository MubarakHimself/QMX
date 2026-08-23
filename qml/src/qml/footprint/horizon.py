"""Warm-up/embargo horizon derived from a resolved producer chain (QL-4).

AD-21/AD-22: warm-up is an integer count of completed input observations; a
composite declares the sum of its children's confirmation-delay bounds; those
counts feed split-manifest embargo widths. The horizon is derived at resolution
and is never a second hand-declared window on the declaration (DEC-0174).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid, policy
from qml.footprint.template import ResolvedProducer, resolve_template

__all__ = ["Horizon", "derive_horizon"]


@dataclass(frozen=True, slots=True)
class Horizon:
    """Derived warm-up and embargo, in observation counts at the chain's BarSpec.

    There is no hand-declared window field — hosts consume this derived value.
    """

    warm_up: int
    embargo: int

    @property
    def total(self) -> int:
        """Warm-up plus embargo — the chain's required purge width in observations."""
        return self.warm_up + self.embargo


def _as_resolved(item: object) -> Result[ResolvedProducer]:
    if isinstance(item, ResolvedProducer):
        return Ok(item)
    if isinstance(item, Mapping):
        mapping = cast("Mapping[str, object]", item)
        assignment = mapping.get("assignment")
        source = mapping.get("template", mapping)
        return resolve_template(source, assignment)
    return resolve_template(item, {})


def derive_horizon(chain: object) -> Result[Horizon]:
    """Derive the warm-up/embargo horizon from a resolved producer chain.

    A chain is an order-significant sequence of resolved producers (upstream to
    downstream). Warm-up and embargo each sum along the chain (AD-21/AD-22
    composite law: a composite declares the sum of its children's bounds). An
    unbounded confirmation-delay producer has no finite embargo and is refused
    as ``policy rejection`` — it cannot enter split-governed evidence.
    """
    if isinstance(chain, ResolvedProducer):
        items: tuple[object, ...] = (chain,)
    elif isinstance(chain, (str, bytes)) or not isinstance(chain, Sequence):
        return invalid(
            "chain",
            "the warm-up/embargo horizon is derived from a resolved producer chain "
            "(an order-significant sequence); it is never a hand-declared window",
            given=type(chain).__name__,
        )
    else:
        items = tuple(cast("Sequence[object]", chain))
    if not items:
        return invalid(
            "chain",
            "a resolved producer chain has one or more producers from which the horizon is derived",
        )
    warm = 0
    embargo = 0
    for index, item in enumerate(items):
        resolved = _as_resolved(item)
        if is_refusal(resolved):
            return resolved
        producer = resolved.value
        if producer.confirmation_delay_unbounded:
            return policy(
                "confirmation_delay_bound",
                "an unbounded confirmation-delay producer has no finite embargo width "
                "and is legal only for families excluded from split-governed evidence; "
                "the bot horizon cannot be derived from it",
                index=index,
                formula_id=producer.formula_id,
            )
        delay = producer.confirmation_delay_bound
        warm += producer.warm_up
        embargo += 0 if delay is None else delay
    return Ok(Horizon(warm_up=warm, embargo=embargo))
