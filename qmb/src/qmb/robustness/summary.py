"""The shared distribution-summary primitive for the B-14 robustness ladder (AC4).

Every ladder procedure (22.2-22.5) describes a simulated distribution against an
observed value the same way, so the arithmetic lives once here rather than being
re-derived per procedure. :func:`summarize_distribution` takes a simulated
distribution, an observed value, and a declared ``direction``
(:data:`DIRECTION_HIGHER_IS_BETTER` or :data:`DIRECTION_LOWER_IS_BETTER`) and
returns percentile ranks, confidence bands, and an **empirical one-tailed p-value**
— the fraction of the distribution at or beyond the observed value in the declared
direction — as pure data.

It emits **NO pass/fail verdict** and invents **no alpha level** (AC4). Alpha
levels, pass batteries, and battery composition (the MC-1000 / PBO / CSCV
candidates) are deferred to GAP-0048/0049 (SC-07). Confidence bands are computed
only at caller-supplied probabilities; with none supplied the summary returns no
bands rather than inventing a default level.

Every input value is exact — an ``int``, a :class:`~fractions.Fraction`, an
:class:`~qmf.core.exact.ExactRational`, a :class:`~qmf.core.exact.Money`, or a
label-derived :class:`~qmb.robustness.carveout.ReturnSpaceMeasure`. A raw binary
float is refused: it must cross the return-space carve-out first, so the summary
stays exact and reproducible (AD-7, NFR-03). The p-value, percentile rank, quantile
bands, minimum, maximum, and median are all exact rationals.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core.exact import ExactRational, Money
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid, policy
from qmb.robustness.carveout import ReturnSpaceMeasure

__all__ = [
    "DIRECTION_HIGHER_IS_BETTER",
    "DIRECTION_LOWER_IS_BETTER",
    "DISTRIBUTION_SUMMARY_CLASS",
    "DISTRIBUTION_SUMMARY_FORMAT_VERSION",
    "SUMMARY_DIRECTIONS",
    "SUMMARY_EMITS_VERDICT",
    "SUMMARY_FORBIDDEN_VERDICTS",
    "SUMMARY_INVENTS_ALPHA",
    "SUMMARY_VERDICT_DEFERRED_TO",
    "DistributionBand",
    "DistributionSummary",
    "refuse_pass_fail_verdict",
    "summarize_distribution",
    "summary_identity",
]

# The declared direction the caller states: which pole of the measure is favourable.
DIRECTION_HIGHER_IS_BETTER: Final[str] = "higher-is-better"
DIRECTION_LOWER_IS_BETTER: Final[str] = "lower-is-better"
SUMMARY_DIRECTIONS: Final[tuple[str, ...]] = (
    DIRECTION_HIGHER_IS_BETTER,
    DIRECTION_LOWER_IS_BETTER,
)

DISTRIBUTION_SUMMARY_CLASS: Final[str] = "qmb-distribution-summary"
DISTRIBUTION_SUMMARY_FORMAT_VERSION: Final[int] = 1
_DISTRIBUTION_BAND_CLASS: Final[str] = "qmb-distribution-band"

# The summary is pure data: no pass/fail verdict, no invented alpha level. The pass
# batteries (MC-1000 / PBO / CSCV) and alpha levels are deferred (SC-07).
SUMMARY_EMITS_VERDICT: Final[bool] = False
SUMMARY_INVENTS_ALPHA: Final[bool] = False
SUMMARY_VERDICT_DEFERRED_TO: Final[str] = "GAP-0048/GAP-0049"
SUMMARY_FORBIDDEN_VERDICTS: Final[tuple[str, ...]] = (
    "pass",
    "fail",
    "significant",
    "reject",
    "accept",
    "mc-1000",
    "pbo",
    "cscv",
)


@dataclass(frozen=True, slots=True)
class DistributionBand:
    """One confidence band: a caller-declared probability and its exact quantile (AC4).

    The probability is a caller-supplied UI-editable level with no ratified value;
    the value is the distribution's empirical quantile at that probability, computed
    exactly by the nearest-rank method.
    """

    probability_num: int
    probability_den: int
    value_num: int
    value_den: int

    @property
    def probability(self) -> Fraction:
        """The declared band probability."""
        return Fraction(self.probability_num, self.probability_den)

    @property
    def value(self) -> Fraction:
        """The exact empirical quantile at :attr:`probability`."""
        return Fraction(self.value_num, self.value_den)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content — every part an exact num/den pair."""
        return {
            "class": _DISTRIBUTION_BAND_CLASS,
            "probability_den": self.probability_den,
            "probability_num": self.probability_num,
            "value_den": self.value_den,
            "value_num": self.value_num,
        }


@dataclass(frozen=True, slots=True)
class DistributionSummary:
    """A simulated distribution described against an observed value, as pure data (AC4).

    Every field is exact. The p-value is the empirical one-tailed fraction of the
    distribution at or beyond the observed value in the declared direction; the
    percentile rank is the observed value's mid-rank position; the bands are the
    caller-requested empirical quantiles. No pass/fail verdict is emitted.
    """

    direction: str
    count: int
    observed_num: int
    observed_den: int
    p_value_num: int
    p_value_den: int
    percentile_rank_num: int
    percentile_rank_den: int
    minimum_num: int
    minimum_den: int
    maximum_num: int
    maximum_den: int
    median_num: int
    median_den: int
    bands: tuple[DistributionBand, ...]

    @property
    def observed(self) -> Fraction:
        """The observed value the distribution is described against."""
        return Fraction(self.observed_num, self.observed_den)

    @property
    def p_value(self) -> Fraction:
        """The empirical one-tailed p-value (fraction at or beyond the observed value)."""
        return Fraction(self.p_value_num, self.p_value_den)

    @property
    def percentile_rank(self) -> Fraction:
        """The observed value's mid-rank percentile within the distribution (0..1)."""
        return Fraction(self.percentile_rank_num, self.percentile_rank_den)

    @property
    def minimum(self) -> Fraction:
        """The exact minimum of the distribution."""
        return Fraction(self.minimum_num, self.minimum_den)

    @property
    def maximum(self) -> Fraction:
        """The exact maximum of the distribution."""
        return Fraction(self.maximum_num, self.maximum_den)

    @property
    def median(self) -> Fraction:
        """The exact median of the distribution."""
        return Fraction(self.median_num, self.median_den)

    @property
    def emits_verdict(self) -> bool:
        """Always ``False`` — the summary is pure data, never a verdict (AC4)."""
        return SUMMARY_EMITS_VERDICT

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content — every measure an exact num/den pair."""
        return {
            "bands": tuple(band.fp1_identity() for band in self.bands),
            "class": DISTRIBUTION_SUMMARY_CLASS,
            "count": self.count,
            "direction": self.direction,
            "emits_verdict": SUMMARY_EMITS_VERDICT,
            "format_version": DISTRIBUTION_SUMMARY_FORMAT_VERSION,
            "maximum_den": self.maximum_den,
            "maximum_num": self.maximum_num,
            "median_den": self.median_den,
            "median_num": self.median_num,
            "minimum_den": self.minimum_den,
            "minimum_num": self.minimum_num,
            "observed_den": self.observed_den,
            "observed_num": self.observed_num,
            "p_value_den": self.p_value_den,
            "p_value_num": self.p_value_num,
            "percentile_rank_den": self.percentile_rank_den,
            "percentile_rank_num": self.percentile_rank_num,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The qmf-core ``fp1`` over the exact summary identity content."""
        return fingerprint(self.fp1_identity())


def summarize_distribution(
    distribution: object,
    observed: object,
    direction: object,
    *,
    band_probabilities: object = (),
) -> Result[DistributionSummary]:
    """Summarize a simulated distribution against an observed value, as pure data (AC4).

    Returns percentile ranks, confidence bands, and an empirical one-tailed p-value.
    An empty distribution, an off-vocabulary direction, a raw binary float value, or
    a band probability outside ``(0, 1)`` is a typed refusal. No pass/fail verdict is
    emitted and no alpha level is invented — the pass batteries stay deferred (SC-07).
    """
    dir_token = clean_token(direction)
    if dir_token is None or dir_token not in SUMMARY_DIRECTIONS:
        return invalid(
            "direction",
            "a distribution summary declares direction higher-is-better or lower-is-better",
            given=repr(direction),
            allowed=SUMMARY_DIRECTIONS,
        )
    coerced = _coerce_distribution(distribution)
    if is_refusal(coerced):
        return coerced
    ordered = sorted(coerced.value)
    obs = _as_exact(observed, field="observed")
    if is_refusal(obs):
        return obs
    observed_value = obs.value
    bands = _coerce_bands(band_probabilities, ordered)
    if is_refusal(bands):
        return bands
    p_value = _one_tailed_p_value(ordered, observed_value, dir_token)
    percentile = _percentile_rank(ordered, observed_value)
    median = _median(ordered)
    return Ok(
        DistributionSummary(
            direction=dir_token,
            count=len(ordered),
            observed_num=observed_value.numerator,
            observed_den=observed_value.denominator,
            p_value_num=p_value.numerator,
            p_value_den=p_value.denominator,
            percentile_rank_num=percentile.numerator,
            percentile_rank_den=percentile.denominator,
            minimum_num=ordered[0].numerator,
            minimum_den=ordered[0].denominator,
            maximum_num=ordered[-1].numerator,
            maximum_den=ordered[-1].denominator,
            median_num=median.numerator,
            median_den=median.denominator,
            bands=bands.value,
        )
    )


def refuse_pass_fail_verdict(name: object) -> Result[None]:
    """Refuse turning the distribution summary into a pass/fail verdict (AC4).

    The summary is percentile ranks, confidence bands, and a one-tailed p-value as
    pure data. Reading a preregistered alpha, an MC-1000 / PBO / CSCV battery, or any
    pass/fail out of it is a ``policy rejection`` — the whole battery-and-threshold
    sitting is deferred (SC-07, GAP-0048/0049).
    """
    token = clean_token(name)
    if token is None:
        return invalid(
            "verdict",
            "a verdict name is required to refuse it",
            given=repr(name),
            deferred_to=SUMMARY_VERDICT_DEFERRED_TO,
        )
    return policy(
        "verdict",
        "the distribution summary returns percentile ranks, confidence bands, and a one-tailed "
        "empirical p-value as pure data; it emits no pass/fail verdict and invents no alpha level "
        "— the MC-1000 / PBO / CSCV pass batteries are deferred (SC-07)",
        verdict=token,
        deferred_to=SUMMARY_VERDICT_DEFERRED_TO,
    )


def summary_identity() -> dict[str, object]:
    """Identity-bearing distribution-summary-primitive fields. Package SemVer is omitted."""
    return {
        "class": DISTRIBUTION_SUMMARY_CLASS,
        "directions": SUMMARY_DIRECTIONS,
        "emits_verdict": SUMMARY_EMITS_VERDICT,
        "format_version": DISTRIBUTION_SUMMARY_FORMAT_VERSION,
        "invents_alpha": SUMMARY_INVENTS_ALPHA,
        "verdict_deferred_to": SUMMARY_VERDICT_DEFERRED_TO,
    }


def _coerce_distribution(distribution: object) -> Result[tuple[Fraction, ...]]:
    if isinstance(distribution, (str, bytes)) or not isinstance(distribution, Sequence):
        return invalid(
            "distribution",
            "a simulated distribution is an ordered sequence of exact-numeric values",
            given=repr(type(distribution).__name__),
        )
    seq = cast("Sequence[object]", distribution)
    if not seq:
        return invalid(
            "distribution",
            "a distribution summary requires a non-empty simulated distribution; an empty "
            "required input is invalid, never a silently-applied default (AR-13)",
        )
    out: list[Fraction] = []
    for index, item in enumerate(seq):
        exact = _as_exact(item, field="distribution", index=index)
        if is_refusal(exact):
            return exact
        out.append(exact.value)
    return Ok(tuple(out))


def _coerce_bands(
    band_probabilities: object, ordered: list[Fraction]
) -> Result[tuple[DistributionBand, ...]]:
    if band_probabilities is None:
        return Ok(())
    if isinstance(band_probabilities, (str, bytes)) or not isinstance(band_probabilities, Sequence):
        return invalid(
            "band_probabilities",
            "confidence-band probabilities are an ordered sequence; the summary invents no "
            "alpha level (SC-07)",
            given=repr(type(band_probabilities).__name__),
        )
    seq = cast("Sequence[object]", band_probabilities)
    bands: list[DistributionBand] = []
    for index, item in enumerate(seq):
        probability = _as_exact(item, field="band_probabilities", index=index)
        if is_refusal(probability):
            return probability
        level = probability.value
        if level <= 0 or level >= 1:
            return invalid(
                "band_probabilities",
                "a confidence-band probability is strictly between 0 and 1; the summary "
                "invents no default alpha (SC-07)",
                index=index,
                given=str(level),
            )
        quantile = _nearest_rank_quantile(ordered, level)
        bands.append(
            DistributionBand(
                probability_num=level.numerator,
                probability_den=level.denominator,
                value_num=quantile.numerator,
                value_den=quantile.denominator,
            )
        )
    return Ok(tuple(bands))


def _one_tailed_p_value(ordered: list[Fraction], observed: Fraction, direction: str) -> Fraction:
    if direction == DIRECTION_HIGHER_IS_BETTER:
        at_or_beyond = sum(1 for value in ordered if value >= observed)
    else:
        at_or_beyond = sum(1 for value in ordered if value <= observed)
    return Fraction(at_or_beyond, len(ordered))


def _percentile_rank(ordered: list[Fraction], observed: Fraction) -> Fraction:
    below = sum(1 for value in ordered if value < observed)
    equal = sum(1 for value in ordered if value == observed)
    return Fraction(2 * below + equal, 2 * len(ordered))


def _nearest_rank_quantile(ordered: list[Fraction], probability: Fraction) -> Fraction:
    count = len(ordered)
    rank = min(max(math.ceil(probability * count), 1), count)
    return ordered[rank - 1]


def _median(ordered: list[Fraction]) -> Fraction:
    count = len(ordered)
    middle = count // 2
    if count % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def _as_exact(value: object, *, field: str, index: int | None = None) -> Result[Fraction]:
    context: dict[str, object] = {} if index is None else {"index": index}
    if isinstance(value, bool):
        return invalid(
            field,
            "a distribution value is a number, not a boolean",
            given=repr(value),
            **context,
        )
    if isinstance(value, ReturnSpaceMeasure):
        return Ok(value.magnitude)
    if isinstance(value, ExactRational):
        return Ok(value.as_fraction())
    if isinstance(value, Money):
        return Ok(value.as_fraction())
    if isinstance(value, Fraction):
        return Ok(value)
    if isinstance(value, int):
        return Ok(Fraction(value))
    if isinstance(value, float):
        return invalid(
            field,
            "a binary float never enters the distribution summary; cross it through the "
            "return-space carve-out (a label-derived ReturnSpaceMeasure) first (AD-7, NFR-03)",
            given=repr(value),
            **context,
        )
    return invalid(
        field,
        "a distribution value is an exact number, an ExactRational, a Money, or a "
        "ReturnSpaceMeasure",
        given=repr(type(value).__name__),
        **context,
    )
