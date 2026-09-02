"""Fitted ``liquidity_stress_v1`` — a CPU exact-integer quantile fit (Story 26.17).

Not a trained model. Fit is a deterministic nearest-rank quantile over scaled
integer samples (stdlib only). The fitted artifact is a fingerprinted input so
a refit under an unchanged policy does not fork producer identity (CT-16/AD-24;
DEC-0262).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core import ExactRational, Fingerprint, Ok, Result, UnitKind, fingerprint, is_refusal

from qmn.mis._refuse import invalid, unavailable
from qmn.mis.catalog import (
    LIQUIDITY_STRESS_PRODUCER_ID,
    ConfiguredMisProducer,
    FormulaNature,
    FrontierFrame,
    ProducerEmission,
)
from qmn.mis.signal_snapshot import ProducerReadiness

__all__ = [
    "LIQUIDITY_FIT_SURFACE",
    "LiquidityFitArtifact",
    "evaluate_liquidity_stress",
    "exact_nearest_rank_quantile",
    "fit_liquidity_quantiles",
]

LIQUIDITY_FIT_SURFACE: Final[str] = "qmn.mis.liquidity"


@dataclass(frozen=True, slots=True)
class LiquidityFitArtifact:
    """Fingerprinted CPU quantile fit. Input to evaluate, not producer identity."""

    spread_quantile_value: int
    depth_quantile_value: int
    spread_quantile: ExactRational
    depth_quantile: ExactRational
    spread_sample_count: int
    depth_sample_count: int
    scale: int

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "liquidity-fit-artifact",
            "spread_quantile_value": self.spread_quantile_value,
            "depth_quantile_value": self.depth_quantile_value,
            "spread_quantile": self.spread_quantile.fp1_identity(),
            "depth_quantile": self.depth_quantile.fp1_identity(),
            "spread_sample_count": self.spread_sample_count,
            "depth_sample_count": self.depth_sample_count,
            "scale": self.scale,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


def fit_liquidity_quantiles(
    *,
    spread_samples: object,
    depth_samples: object,
    spread_quantile: object,
    depth_quantile: object,
    scale: object = 0,
) -> Result[LiquidityFitArtifact]:
    """CPU nearest-rank quantile fit. Floats, empty samples, and q outside [0,1] refuse."""
    spread_q = _as_unit_ratio(spread_quantile, "spread_stress_quantile")
    if is_refusal(spread_q):
        return spread_q
    depth_q = _as_unit_ratio(depth_quantile, "depth_stress_quantile")
    if is_refusal(depth_q):
        return depth_q
    spreads = _as_int_samples(spread_samples, "spread_samples")
    if is_refusal(spreads):
        return spreads
    depths = _as_int_samples(depth_samples, "depth_samples")
    if is_refusal(depths):
        return depths
    if not isinstance(scale, int) or isinstance(scale, bool) or scale < 0:
        return invalid("scale", "fit scale is a non-negative integer", given=repr(scale))
    spread_value = exact_nearest_rank_quantile(spreads.value, spread_q.value)
    if is_refusal(spread_value):
        return spread_value
    depth_value = exact_nearest_rank_quantile(depths.value, depth_q.value)
    if is_refusal(depth_value):
        return depth_value
    return Ok(
        LiquidityFitArtifact(
            spread_quantile_value=spread_value.value,
            depth_quantile_value=depth_value.value,
            spread_quantile=spread_q.value,
            depth_quantile=depth_q.value,
            spread_sample_count=len(spreads.value),
            depth_sample_count=len(depths.value),
            scale=scale,
        )
    )


def exact_nearest_rank_quantile(samples: Sequence[int], quantile: ExactRational) -> Result[int]:
    """Hyndman-Fan type-1 quantile: ``k = ceil(n * q)`` (1-indexed), exact Fraction."""
    if not samples:
        return unavailable(
            "samples",
            "a CPU quantile fit needs at least one scaled-integer sample",
        )
    q = quantile.as_fraction()
    if q < 0 or q > 1:
        return invalid(
            "quantile",
            "a quantile is an ExactRational in [0, 1]",
            given=str(q),
        )
    ordered = sorted(samples)
    n = len(ordered)
    if q == 0:
        return Ok(ordered[0])
    k = _ceil_positive(Fraction(n) * q)
    k = max(k, 1)
    k = min(k, n)
    return Ok(ordered[k - 1])


def evaluate_liquidity_stress(
    producer: object,
    frame: object,
    *,
    fit: object,
) -> Result[ProducerEmission]:
    """Label current spread/depth against the fitted quantiles."""
    if not isinstance(producer, ConfiguredMisProducer):
        return invalid(
            "producer",
            "liquidity_stress_v1 evaluates a ConfiguredMisProducer",
            given=type(producer).__name__,
        )
    if producer.producer_id != LIQUIDITY_STRESS_PRODUCER_ID:
        return invalid(
            "producer_id",
            "evaluate_liquidity_stress is the fitted liquidity_stress_v1 producer",
            given=producer.producer_id,
        )
    if producer.nature is not FormulaNature.FITTED:
        return invalid(
            "nature",
            "liquidity_stress_v1 is a fitted CPU quantile producer",
            given=producer.nature.value,
        )
    if not isinstance(frame, FrontierFrame):
        return invalid("frame", "evaluation reads a FrontierFrame", given=type(frame).__name__)
    version = producer.version
    if fit is None:
        return Ok(_emission(ProducerReadiness.NOT_READY, version, marker="fit-missing"))
    if not isinstance(fit, LiquidityFitArtifact):
        return invalid(
            "fit",
            "liquidity_stress_v1 consumes a LiquidityFitArtifact",
            given=type(fit).__name__,
        )
    needed = producer.warm_up
    if fit.spread_sample_count < needed or fit.depth_sample_count < needed:
        return Ok(_emission(ProducerReadiness.NOT_READY, version, marker="warm-up"))
    spread = frame.current_spread_ticks
    depth = frame.current_depth
    if spread is None or depth is None:
        return Ok(_emission(ProducerReadiness.NOT_READY, version, marker="observation-missing"))
    stressed = spread >= fit.spread_quantile_value or depth <= fit.depth_quantile_value
    return Ok(
        ProducerEmission(
            producer_id=LIQUIDITY_STRESS_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version=version,
            marker_detail="true" if stressed else "false",
            liquidity_stress=stressed,
        )
    )


def _emission(
    readiness: ProducerReadiness,
    version: str,
    *,
    marker: str,
) -> ProducerEmission:
    return ProducerEmission(
        producer_id=LIQUIDITY_STRESS_PRODUCER_ID,
        readiness=readiness,
        labeler_version=version,
        marker_detail=marker,
    )


def _ceil_positive(frac: Fraction) -> int:
    numerator, denominator = frac.numerator, frac.denominator
    if denominator == 1:
        return numerator
    return numerator // denominator + 1


def _as_unit_ratio(value: object, field: str) -> Result[ExactRational]:
    if not isinstance(value, ExactRational):
        return invalid(
            field,
            "a quantile is an ExactRational dimensionless ratio in [0, 1]",
            given=repr(value),
        )
    if value.unit_kind is not UnitKind.DIMENSIONLESS_RATIO:
        return invalid(
            field,
            "quantile unit-kind is dimensionless-ratio",
            given=value.unit_kind.value,
        )
    q = value.as_fraction()
    if q < 0 or q > 1:
        return invalid(field, "a quantile is in [0, 1]", given=str(q))
    return Ok(value)


def _as_int_samples(value: object, field: str) -> Result[tuple[int, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            field,
            "quantile samples are a sequence of scaled integers (CPU fit; no float)",
            given=type(value).__name__,
        )
    out: list[int] = []
    for item in cast("Sequence[object]", value):
        if isinstance(item, bool) or not isinstance(item, int):
            if isinstance(item, float):
                return invalid(
                    field,
                    "binary float is refused in the CPU quantile fit (FM-1)",
                    given=repr(item),
                )
            return invalid(
                field,
                "each sample is a scaled integer",
                given=repr(item),
            )
        out.append(item)
    if not out:
        return unavailable(field, "a CPU quantile fit needs at least one sample")
    return Ok(tuple(out))
