"""In-loop warm-up with trading locked (B-2, SC-10, Story 14.4).

Warm-up is the same event-slice loop, the same sub-phase order, and the same
adapters, with trading locked. Its length is the CT-12/AD-21 split-manifest
embargo: an observation count of completed input observations, never a
Duration, and the loop adds no second window. Acting (an entry, an exit, any
command) during warm-up is a typed ``policy rejection``. Pre-seeding indicator
buffers without replaying slices is not warm-up. The result label's evidence
range is the trading interval only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.chrono import Duration, Instant, Interval
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import clean_token, invalid, policy
from qmb.config.compiler import ResolvedRunConfig

__all__ = [
    "EMBARGO_KEY",
    "PRESEED_IS_WARMUP",
    "WARMUP_ADDS_SECOND_WINDOW",
    "WARMUP_MECHANISM",
    "WARMUP_UNIT",
    "SplitEmbargo",
    "WarmupProgress",
    "embargo_from_config",
    "guard_trading",
    "preseed_indicator_buffers",
    "refuse_act_during_warmup",
    "trading_evidence_range",
]

WARMUP_MECHANISM: Final[str] = "in-loop-locked"
WARMUP_UNIT: Final[str] = "observation-count"
WARMUP_ADDS_SECOND_WINDOW: Final[bool] = False
PRESEED_IS_WARMUP: Final[bool] = False
EMBARGO_KEY: Final[str] = "embargo_width"

_SECOND_WINDOW_KEYS: Final[frozenset[str]] = frozenset(
    {
        "second_window",
        "warm_up",
        "warm_up_bars",
        "warmup",
        "warmup_bars",
        "warmup_length",
        "warmup_window",
    }
)
_EMBARGO_KEYS: Final[tuple[str, ...]] = ("observation_count", "embargo_width", "embargo")


def refuse_act_during_warmup(action: object) -> Result[None]:
    """Acting during warm-up is a typed ``policy rejection`` (B-2, SC-10)."""
    token = clean_token(action)
    named = token if token is not None else repr(action)
    return policy(
        "warmup",
        "acting during in-loop warm-up is a typed policy rejection; trading is "
        "locked for the split-manifest embargo observation count (B-2, SC-10)",
        action=named,
        mechanism=WARMUP_MECHANISM,
    )


def guard_trading(*, is_warming_up: bool, action: str) -> Result[None]:
    """Refuse ``action`` while the in-loop trading lock holds."""
    if not is_warming_up:
        return Ok(None)
    return refuse_act_during_warmup(action)


def preseed_indicator_buffers(buffers: object = None) -> Result[None]:
    """Pre-seeding buffers without replaying slices is not warm-up (B-2)."""
    del buffers
    return policy(
        "warmup",
        "pre-seeding indicator buffers without replaying slices is not warm-up "
        "and is not a legal substitute; warm-up is in-loop with trading locked "
        "(B-2)",
        mechanism=WARMUP_MECHANISM,
        preseed_is_warmup=PRESEED_IS_WARMUP,
    )


def trading_evidence_range(
    trading_instants: object,
    *,
    empty_at: object,
) -> Result[Interval]:
    """Half-open evidence range over the trading interval only (SC-10).

    Warm-up instants are omitted. An all-warm-up run yields the empty interval
    at ``empty_at`` (start == end), never a range that covers warm-up.
    """
    if not isinstance(empty_at, Instant):
        return invalid(
            "empty_at",
            "the empty-trading anchor is an Instant",
            given=repr(type(empty_at).__name__),
        )
    if isinstance(trading_instants, Instant):
        instants: tuple[Instant, ...] = (trading_instants,)
    elif isinstance(trading_instants, (str, bytes)) or not isinstance(trading_instants, Sequence):
        return invalid(
            "trading_instants",
            "the trading interval is a sequence of Instants from unlocked slices",
            given=repr(type(trading_instants).__name__),
        )
    else:
        parsed: list[Instant] = []
        for index, raw in enumerate(cast("Sequence[object]", trading_instants)):
            if not isinstance(raw, Instant):
                return invalid(
                    "trading_instants",
                    "each trading-interval bound is an Instant",
                    index=index,
                    given=repr(type(raw).__name__),
                )
            parsed.append(raw)
        instants = tuple(parsed)
    if not instants:
        return Interval.try_create(empty_at, empty_at)
    start = instants[0]
    ended = Instant.try_create(instants[-1].value_ns + 1)
    if is_refusal(ended):
        return ended
    return Interval.try_create(start, ended.value)


def embargo_from_config(config: object) -> Result[SplitEmbargo | None]:
    """Read the split-manifest embargo observation count from a resolved config.

    Omitted key means the caller did not name an embargo (the loop then uses
    observation count 0 — no warm-up). A present Duration is refused.
    """
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "the split-manifest embargo is read from a resolved run-config",
            given=repr(type(config).__name__),
        )
    if EMBARGO_KEY not in config.keys:
        return Ok(None)
    parsed = SplitEmbargo.try_create(config.keys[EMBARGO_KEY])
    if is_refusal(parsed):
        return parsed
    found: SplitEmbargo | None = parsed.value
    return Ok(found)


@dataclass(frozen=True, slots=True)
class SplitEmbargo:
    """Warm-up length: the split-manifest embargo as an observation count (B-2).

    Never a Duration. The loop adds no second window — this count IS warm-up.
    """

    observation_count: int
    split_fp1: str | None = None

    @property
    def unit(self) -> str:
        """AD-22 sample unit: completed observations, never a Duration."""
        return WARMUP_UNIT

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content: dict[str, object] = {
            "class": "split-embargo",
            "mechanism": WARMUP_MECHANISM,
            "observation_count": self.observation_count,
            "unit": WARMUP_UNIT,
        }
        if self.split_fp1 is not None:
            content["split_fp1"] = self.split_fp1
        return content

    @classmethod
    def try_create(cls, value: object, split_fp1: object = None) -> Result[SplitEmbargo]:
        """Validate the embargo as a non-negative observation count."""
        if isinstance(value, SplitEmbargo):
            return Ok(value)
        if _is_duration(value):
            return _duration_refusal(value)
        if isinstance(value, Mapping):
            return _from_mapping(cast("Mapping[str, object]", value))
        count = _observation_count(value)
        if is_refusal(count):
            return count
        cited = _split_cite(split_fp1)
        if is_refusal(cited):
            return cited
        return Ok(cls(observation_count=count.value, split_fp1=cited.value))


@dataclass(frozen=True, slots=True)
class WarmupProgress:
    """Pure progress through in-loop warm-up. ``is_warming_up`` is the lock flag."""

    embargo: SplitEmbargo
    observations_processed: int = 0

    @property
    def is_warming_up(self) -> bool:
        """True while completed observations are still inside the embargo."""
        return self.observations_processed < self.embargo.observation_count

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "embargo": self.embargo.fp1_identity(),
            "is_warming_up": self.is_warming_up,
            "mechanism": WARMUP_MECHANISM,
            "observations_processed": self.observations_processed,
        }

    @classmethod
    def try_create(
        cls,
        embargo: object,
        observations_processed: object = 0,
    ) -> Result[WarmupProgress]:
        """Build progress from the split-manifest embargo observation count."""
        bound = SplitEmbargo.try_create(embargo)
        if is_refusal(bound):
            return bound
        processed = _observation_count(observations_processed)
        if is_refusal(processed):
            return processed
        return Ok(cls(embargo=bound.value, observations_processed=processed.value))

    def advance(self, closed_observations: object) -> Result[WarmupProgress]:
        """Count completed observations. Forming-only slices pass 0 and do not count."""
        added = _observation_count(closed_observations)
        if is_refusal(added):
            return added
        total = self.observations_processed + added.value
        if total < self.observations_processed:
            return invalid(
                "observations_processed",
                "completed-observation arithmetic overflowed; refused, never wrapped",
                left=self.observations_processed,
                right=added.value,
            )
        return Ok(WarmupProgress(embargo=self.embargo, observations_processed=total))


def _from_mapping(mapping: Mapping[str, object]) -> Result[SplitEmbargo]:
    second = [key for key in _SECOND_WINDOW_KEYS if key in mapping]
    embargo_key = next((key for key in _EMBARGO_KEYS if key in mapping), None)
    if second:
        return invalid(
            "warmup",
            "warm-up length is the split-manifest embargo observation count; "
            "the loop adds no second window (B-2, CT-12)",
            given=second,
            embargo_key=EMBARGO_KEY,
            warmup_adds_second_window=WARMUP_ADDS_SECOND_WINDOW,
        )
    if embargo_key is None:
        return invalid(
            EMBARGO_KEY,
            "warm-up length is the split-manifest embargo already declared "
            "under AD-21, as an observation count, never a Duration",
            given=sorted(mapping),
        )
    raw = mapping[embargo_key]
    if _is_duration(raw) or _is_duration(mapping):
        return _duration_refusal(raw)
    count = _observation_count(raw)
    if is_refusal(count):
        return count
    cited = _split_cite(mapping.get("split_fp1", mapping.get("split_id")))
    if is_refusal(cited):
        return cited
    return Ok(SplitEmbargo(observation_count=count.value, split_fp1=cited.value))


def _split_cite(value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Fingerprint):
        return Ok(value.value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "split_fp1",
            "a cited split-manifest fingerprint is a non-empty fp1 token",
            given=repr(value),
        )
    return Ok(token)


def _observation_count(value: object) -> Result[int]:
    if _is_duration(value):
        return _duration_refusal(value)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(
            EMBARGO_KEY,
            "warm-up length is the split-manifest embargo as a non-negative "
            "observation count, never a Duration (B-2, AD-22, CT-12)",
            given=repr(value),
            unit=WARMUP_UNIT,
        )
    return Ok(value)


def _is_duration(value: object) -> bool:
    if isinstance(value, Duration):
        return True
    width = getattr(value, "embargo_width", None)
    return isinstance(width, Duration)


def _duration_refusal(value: object) -> TypedRefusal:
    return invalid(
        EMBARGO_KEY,
        "warm-up length is the split-manifest embargo as an observation count, "
        "never a Duration; the loop adds no second window (B-2, CT-12)",
        given=repr(type(value).__name__),
        unit=WARMUP_UNIT,
        warmup_adds_second_window=WARMUP_ADDS_SECOND_WINDOW,
    )
