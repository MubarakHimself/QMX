"""Fidelity identity: adapter-id + composition-version + taint (B-6, DEC-0164).

``optimistic`` is the taint field, never fp1 identity. A run's fidelity is the
LOWEST of any bound adapter. Mixed-fidelity Book-bar comparison without an
explicit override is a typed refusal (LABEL-3). Ordinal taxonomy values are a
deferred GAP-0048 artifact — this module consumes them and never invents ranks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid, policy, unavailable
from qmb.execution.ports import COMPOSITION_VERSION, TAINT_IS_IDENTITY, TAINT_OPTIMISTIC

__all__ = [
    "FIDELITY_TAXONOMY_DEFERRED_TO",
    "FidelityIdentity",
    "FidelityTaxonomy",
    "RunFidelity",
    "compare_book_bar_fidelity",
    "compute_run_fidelity",
    "lowest_fidelity",
    "stamp_fidelity",
]

FIDELITY_TAXONOMY_DEFERRED_TO: Final[str] = "GAP-0048"


@dataclass(frozen=True, slots=True)
class FidelityIdentity:
    """One adapter's fidelity label (B-6).

    Identity-bearing parts are adapter-id and composition-version. Taint is a
    field on the label and is omitted from ``fp1`` (DEC-0164).
    """

    adapter_id: str
    composition_version: int
    taint: str = TAINT_OPTIMISTIC
    calibration_ref: str | None = None
    fill_basis: str | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Taint is omitted; package SemVer never enters."""
        content: dict[str, object] = {
            "adapter_id": self.adapter_id,
            "class": "fidelity-identity",
            "composition_version": self.composition_version,
        }
        if self.calibration_ref is not None:
            content["calibration_ref"] = self.calibration_ref
        if self.fill_basis is not None:
            content["fill_basis"] = self.fill_basis
        return content

    @classmethod
    def try_create(
        cls,
        adapter_id: object,
        *,
        composition_version: object = COMPOSITION_VERSION,
        taint: object = TAINT_OPTIMISTIC,
        calibration_ref: object = None,
        fill_basis: object = None,
    ) -> Result[FidelityIdentity]:
        """Validate one adapter's fidelity identity."""
        token = clean_token(adapter_id)
        if token is None:
            return invalid(
                "adapter_id",
                "fidelity identity names a non-empty adapter-id (B-6)",
                given=repr(adapter_id),
            )
        if not isinstance(composition_version, int) or isinstance(composition_version, bool):
            return invalid(
                "composition_version",
                "composition-version is a positive integer ordinal; changing the "
                "bound port set or its order mints a new version (B-6, AR-59)",
                given=repr(composition_version),
            )
        if composition_version < 1:
            return invalid(
                "composition_version",
                "composition-version is a positive integer ordinal (B-6)",
                given=composition_version,
            )
        stamped = _require_optimistic_taint(taint)
        if is_refusal(stamped):
            return stamped
        ref: str | None = None
        if calibration_ref is not None:
            parsed_ref = clean_token(calibration_ref)
            if parsed_ref is None:
                return invalid(
                    "calibration_ref",
                    "a calibration reference is a non-empty token, never invented content",
                    given=repr(calibration_ref),
                )
            ref = parsed_ref
        basis: str | None = None
        if fill_basis is not None:
            parsed_basis = clean_token(fill_basis)
            if parsed_basis is None:
                return invalid(
                    "fill_basis",
                    "fill basis is worst-case or optimistic-exact (FILL-4)",
                    given=repr(fill_basis),
                )
            basis = parsed_basis
        return Ok(
            cls(
                adapter_id=token,
                composition_version=composition_version,
                taint=stamped.value,
                calibration_ref=ref,
                fill_basis=basis,
            )
        )


@dataclass(frozen=True, slots=True)
class FidelityTaxonomy:
    """Deferred GAP-0048 ranking artifact. Lower rank is lower fidelity.

    QMB does not ship ordinal values. A caller that already holds a fingerprinted
    taxonomy may pass it here; missing ranks are an unavailable dependency, never
    a fabricated order (SC-07).
    """

    ranks: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ranks", MappingProxyType(dict(self.ranks)))

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "class": "fidelity-taxonomy",
            "deferred_to": FIDELITY_TAXONOMY_DEFERRED_TO,
            "ranks": dict(self.ranks),
        }

    @classmethod
    def try_create(cls, ranks: object) -> Result[FidelityTaxonomy]:
        """Validate a deferred ranking artifact. No default ranks are filled in."""
        if not isinstance(ranks, Mapping) or isinstance(ranks, (str, bytes)):
            return invalid(
                "ranks",
                "a fidelity taxonomy is a mapping of adapter-id to integer rank; "
                "ordinal values are not invented here (SC-07, GAP-0048)",
                given=repr(type(ranks).__name__),
            )
        parsed: dict[str, int] = {}
        for raw_key, raw_rank in cast("Mapping[object, object]", ranks).items():
            token = clean_token(raw_key)
            if token is None:
                return invalid(
                    "ranks",
                    "each taxonomy key is a non-empty adapter-id",
                    given=repr(raw_key),
                )
            if isinstance(raw_rank, bool) or not isinstance(raw_rank, int):
                return invalid(
                    "ranks",
                    "taxonomy ranks are exact integers, never binary floats or invented ordinals",
                    adapter_id=token,
                    given=repr(type(raw_rank).__name__),
                )
            parsed[token] = raw_rank
        if not parsed:
            return invalid(
                "ranks",
                "a fidelity taxonomy names at least one adapter-id rank (SC-07)",
            )
        return Ok(cls(ranks=parsed))


@dataclass(frozen=True, slots=True)
class RunFidelity:
    """A run's fidelity: bound adapter identities plus lowest-wins (B-6, LABEL-2)."""

    bound: tuple[FidelityIdentity, ...]
    taint: str = TAINT_OPTIMISTIC
    lowest_adapter_id: str | None = None
    taxonomy_deferred: bool = True

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Taint is omitted (DEC-0164)."""
        content: dict[str, object] = {
            "bound": [item.fp1_identity() for item in self.bound],
            "class": "run-fidelity",
            "taxonomy_deferred": self.taxonomy_deferred,
        }
        if self.lowest_adapter_id is not None:
            content["lowest_adapter_id"] = self.lowest_adapter_id
        return content


def stamp_fidelity(
    adapter_id: object,
    *,
    composition_version: object = COMPOSITION_VERSION,
    taint: object = TAINT_OPTIMISTIC,
    calibration_ref: object = None,
    fill_basis: object = None,
) -> Result[FidelityIdentity]:
    """Stamp one fill/adapter fidelity identity (B-6, SC-06)."""
    return FidelityIdentity.try_create(
        adapter_id,
        composition_version=composition_version,
        taint=taint,
        calibration_ref=calibration_ref,
        fill_basis=fill_basis,
    )


def lowest_fidelity(
    identities: object,
    *,
    taxonomy: object = None,
) -> Result[RunFidelity]:
    """A run's fidelity is the LOWEST of any bound adapter (B-6, LABEL-2).

    Without a deferred taxonomy artifact every V1 adapter is ``optimistic``-tainted
    and no ordinal winner is invented. With a taxonomy, the minimum rank among
    bound adapter-ids wins; missing ranks refuse rather than fabricate an order.
    """
    return compute_run_fidelity(identities, taxonomy=taxonomy)


def compute_run_fidelity(
    identities: object,
    *,
    taxonomy: object = None,
) -> Result[RunFidelity]:
    """Aggregate bound adapter identities into one run-fidelity label."""
    parsed = _as_identities(identities)
    if is_refusal(parsed):
        return parsed
    bound = parsed.value
    taints = {item.taint for item in bound}
    if taints != {TAINT_OPTIMISTIC}:
        return policy(
            "taint",
            "until GAP-0048 every fill carries the optimistic taint (B-6, SC-06)",
            given=sorted(taints),
            gap="GAP-0048",
        )
    if taxonomy is None:
        return Ok(
            RunFidelity(
                bound=bound,
                taint=TAINT_OPTIMISTIC,
                lowest_adapter_id=None,
                taxonomy_deferred=True,
            )
        )
    ranked = taxonomy if isinstance(taxonomy, FidelityTaxonomy) else None
    if ranked is None:
        created = FidelityTaxonomy.try_create(taxonomy)
        if is_refusal(created):
            return created
        ranked = created.value
    missing = [item.adapter_id for item in bound if item.adapter_id not in ranked.ranks]
    if missing:
        return unavailable(
            "taxonomy",
            "the deferred GAP-0048 fidelity taxonomy does not rank these adapter "
            "ids; ordinal values are not invented here (SC-07, B-6)",
            missing=missing,
            gap=FIDELITY_TAXONOMY_DEFERRED_TO,
        )
    winner = min(bound, key=lambda item: (ranked.ranks[item.adapter_id], bound.index(item)))
    return Ok(
        RunFidelity(
            bound=bound,
            taint=TAINT_OPTIMISTIC,
            lowest_adapter_id=winner.adapter_id,
            taxonomy_deferred=False,
        )
    )


def compare_book_bar_fidelity(
    left: object,
    right: object,
    *,
    override: object = False,
) -> Result[None]:
    """Refuse mixed-fidelity Book-bar comparison without an explicit override (LABEL-3)."""
    first = _as_run_fidelity(left, "left")
    if is_refusal(first):
        return first
    second = _as_run_fidelity(right, "right")
    if is_refusal(second):
        return second
    if override is True:
        return Ok(None)
    if override is not False:
        return invalid(
            "override",
            "mixed-fidelity comparison override is the explicit bool True, never a silent flag",
            given=repr(override),
        )
    left_fp = fingerprint(first.value.fp1_identity())
    if is_refusal(left_fp):
        return left_fp
    right_fp = fingerprint(second.value.fp1_identity())
    if is_refusal(right_fp):
        return right_fp
    if left_fp.value.value != right_fp.value.value:
        return policy(
            "fidelity",
            "mixed-fidelity comparison of Book bars is a typed refusal without "
            "an explicit override (LABEL-3, B-6, DEC-0164)",
            left=first.value.fp1_identity(),
            right=second.value.fp1_identity(),
        )
    return Ok(None)


def _require_optimistic_taint(taint: object) -> Result[str]:
    if taint is None:
        return Ok(TAINT_OPTIMISTIC)
    token = taint if isinstance(taint, str) else clean_token(taint)
    if token != TAINT_OPTIMISTIC:
        return policy(
            "taint",
            "until GAP-0048 every fill carries the optimistic taint; a different "
            "taint is a policy rejection (B-6, SC-06)",
            given=repr(taint),
            gap="GAP-0048",
            taint_is_identity=TAINT_IS_IDENTITY,
        )
    return Ok(TAINT_OPTIMISTIC)


def _as_identities(value: object) -> Result[tuple[FidelityIdentity, ...]]:
    if isinstance(value, FidelityIdentity):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "identities",
            "run fidelity aggregates a sequence of FidelityIdentity values",
            given=repr(type(value).__name__),
        )
    parsed: list[FidelityIdentity] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        if not isinstance(raw, FidelityIdentity):
            return invalid(
                "identities",
                "each bound adapter stamps a FidelityIdentity",
                index=index,
                given=repr(type(raw).__name__),
            )
        parsed.append(raw)
    if not parsed:
        return invalid(
            "identities",
            "a run's fidelity names the adapters it bound (B-6)",
        )
    return Ok(tuple(parsed))


def _as_run_fidelity(value: object, field: str) -> Result[RunFidelity]:
    if isinstance(value, RunFidelity):
        return Ok(value)
    fidelity = getattr(value, "fidelity", None)
    if isinstance(fidelity, RunFidelity):
        return Ok(fidelity)
    return invalid(
        field,
        "Book-bar fidelity comparison consumes RunFidelity labels (LABEL-3)",
        given=repr(type(value).__name__),
    )
