"""Completed-boundary BarSpec derivation (B-2, AR-57, FR-037, SC-06).

Higher-``BarSpec`` bars are folded from the finest declared base stream and
emitted only on a completed boundary. A forming bar is a distinct inspectable
object, never in the strategy-readable set and never actionable. Same-slice
bars and fills consume one underlying series. Look-ahead prevention ships
regardless of GAP-0048.

``BarSpec`` is a qmf-core noun (CT-16); this module stores canonical identity
mappings and never redefines the type.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant, Interval
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid, policy, unsupported

__all__ = [
    "BARSPEC_KINDS",
    "COMPLETED_BOUNDARY_ONLY",
    "COMPLETENESS_COMPLETED",
    "COMPLETENESS_FORMING",
    "FORMING_BAR_ACTIONABLE",
    "FORMING_BAR_VISIBLE",
    "LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048",
    "DeclaredBarSpec",
    "DerivedBar",
    "FormingBarState",
    "ReadableBarSet",
    "SameSliceConsumption",
    "SeriesSample",
    "StreamBarPlan",
    "UnderlyingSeries",
    "act_on_bar",
    "consume_same_slice",
    "consume_stream_plans",
    "finest_base",
    "readable_bars",
    "require_same_series",
]

# registry:barspec_kinds — referenced, never restated as a new type (DEC-0126).
BARSPEC_KINDS: Final[frozenset[str]] = frozenset(
    {
        "time-interval",
        "tick-count",
        "volume-threshold",
        "notional-threshold",
        "price-brick",
        "range",
        "session",
    }
)
_EVENT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "tick-count",
        "volume-threshold",
        "notional-threshold",
        "price-brick",
        "range",
    }
)
_PARAM_BY_KIND: Final[Mapping[str, str]] = MappingProxyType(
    {
        "time-interval": "seconds",
        "tick-count": "count",
        "volume-threshold": "volume",
        "notional-threshold": "notional",
        "price-brick": "brick",
        "range": "range",
    }
)

COMPLETENESS_COMPLETED: Final[str] = "completed"
COMPLETENESS_FORMING: Final[str] = "forming"
COMPLETED_BOUNDARY_ONLY: Final[bool] = True
FORMING_BAR_VISIBLE: Final[bool] = False
FORMING_BAR_ACTIONABLE: Final[bool] = False
LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048: Final[bool] = True

_NS_PER_SEC: Final[int] = 1_000_000_000
_INT64_MAX: Final[int] = 2**63 - 1


def _plain_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _positive_int(value: object) -> int | None:
    parsed = _plain_int(value)
    if parsed is None or parsed <= 0:
        return None
    return parsed


def _nonneg_int(value: object) -> int | None:
    parsed = _plain_int(value)
    if parsed is None or parsed < 0:
        return None
    return parsed


@dataclass(frozen=True, slots=True)
class DeclaredBarSpec:
    """Canonical BarSpec identity mapping used by the loop (CT-16).

    Never a bare timeframe. Kind is one of ``registry:barspec_kinds``.
    """

    kind: str
    parameters: Mapping[str, object]

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content: dict[str, object] = {"kind": self.kind}
        for key in sorted(self.parameters):
            content[key] = self.parameters[key]
        return content

    @property
    def unit_size(self) -> int | None:
        """Comparable unit for finest-base ranking, or None for session."""
        key = _PARAM_BY_KIND.get(self.kind)
        if key is None:
            return None
        value = self.parameters.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @classmethod
    def try_create(cls, value: object) -> Result[DeclaredBarSpec]:
        """Validate a BarSpec identity mapping. Fingerprint-only refs are refused."""
        if isinstance(value, DeclaredBarSpec):
            return Ok(value)
        if isinstance(value, (str, bytes)) or not isinstance(value, Mapping):
            return invalid(
                "bar_spec",
                "a BarSpec is a canonical identity mapping; never a bare timeframe "
                "(the BarSpec type is a qmf-core noun)",
                given=repr(type(value).__name__),
            )
        mapping = cast("Mapping[str, object]", value)
        kind = mapping.get("kind")
        if not isinstance(kind, str) or kind not in BARSPEC_KINDS:
            return invalid(
                "bar_spec",
                "a BarSpec kind is one of registry:barspec_kinds; never a bare timeframe",
                given=repr(kind),
                allowed=sorted(BARSPEC_KINDS),
            )
        if kind == "session":
            session = clean_token(mapping.get("session"))
            if session is None:
                return invalid(
                    "session",
                    "a session BarSpec names a non-empty session token",
                    given=repr(mapping.get("session")),
                )
            params: dict[str, object] = {"session": session}
            return Ok(cls(kind=kind, parameters=MappingProxyType(params)))
        key = _PARAM_BY_KIND[kind]
        size = _positive_int(mapping.get(key))
        if size is None:
            return invalid(
                key,
                "a BarSpec parameter is a positive exact integer; binary floats "
                "never appear in BarSpec identity",
                kind=kind,
                given=repr(mapping.get(key)),
            )
        return Ok(cls(kind=kind, parameters=MappingProxyType({key: size})))


def finest_base(specs: object) -> Result[DeclaredBarSpec]:
    """The finest declared BarSpec — the base stream the others fold from."""
    parsed = _as_specs(specs)
    if is_refusal(parsed):
        return parsed
    items = parsed.value
    if not items:
        return invalid("bar_specs", "a stream declares one or more BarSpecs (B-12)")
    kinds = {item.kind for item in items}
    if len(kinds) != 1:
        return invalid(
            "bar_specs",
            "higher-BarSpec bars derive from one finest base of the same kind",
            kinds=sorted(kinds),
        )
    if items[0].kind == "session":
        if len(items) != 1:
            return unsupported(
                "bar_specs",
                "session BarSpec derivation needs a market-hours calendar; "
                "multiple session specs are unsupported",
            )
        return Ok(items[0])
    ranked = sorted(items, key=lambda spec: spec.unit_size or 0)
    return Ok(ranked[0])


@dataclass(frozen=True, slots=True)
class StreamBarPlan:
    """Declared BarSpec list for one stream. Finest is the base (B-2, B-12)."""

    stream_id: str
    bar_specs: tuple[DeclaredBarSpec, ...]
    base: DeclaredBarSpec

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Declaration order of bar_specs is significant."""
        return {
            "bar_specs": [item.fp1_identity() for item in self.bar_specs],
            "base": self.base.fp1_identity(),
            "stream_id": self.stream_id,
        }

    @property
    def higher(self) -> tuple[DeclaredBarSpec, ...]:
        """Specs strictly coarser than the finest base."""
        base_size = self.base.unit_size
        if base_size is None:
            return ()
        return tuple(item for item in self.bar_specs if (item.unit_size or 0) > base_size)

    @classmethod
    def try_create(cls, stream_id: object, bar_specs: object) -> Result[StreamBarPlan]:
        """Validate stream id, BarSpec list, finest base, and integer multiples."""
        token = clean_token(stream_id)
        if token is None:
            return invalid(
                "stream_id",
                "a bar plan names a non-empty stream id",
                given=repr(stream_id),
            )
        parsed = _as_specs(bar_specs)
        if is_refusal(parsed):
            return parsed
        base = finest_base(parsed.value)
        if is_refusal(base):
            return base
        aligned = _require_multiples(base.value, parsed.value)
        if is_refusal(aligned):
            return aligned
        return Ok(cls(stream_id=token, bar_specs=parsed.value, base=base.value))


@dataclass(frozen=True, slots=True)
class SeriesSample:
    """One knowable print of the underlying series bars and fills share."""

    instant: Instant
    price: int
    volume: int = 0
    notional: int = 0

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content: dict[str, object] = {
            "instant_ns": self.instant.value_ns,
            "price": self.price,
        }
        if self.volume != 0:
            content["volume"] = self.volume
        if self.notional != 0:
            content["notional"] = self.notional
        return content

    @classmethod
    def try_create(
        cls,
        instant: object,
        price: object,
        volume: object = 0,
        notional: object = 0,
    ) -> Result[SeriesSample]:
        """Validate one series print. Prices are exact integers, never floats."""
        if not isinstance(instant, Instant):
            return invalid(
                "instant",
                "a series sample carries an Instant",
                given=repr(type(instant).__name__),
            )
        parsed_price = _plain_int(price)
        if parsed_price is None:
            return invalid(
                "price",
                "a series sample price is an exact scaled integer; a binary float is refused",
                given=repr(price),
            )
        parsed_volume = _nonneg_int(volume)
        if parsed_volume is None:
            return invalid(
                "volume",
                "volume is a non-negative exact integer",
                given=repr(volume),
            )
        parsed_notional = _nonneg_int(notional)
        if parsed_notional is None:
            return invalid(
                "notional",
                "notional is a non-negative exact integer",
                given=repr(notional),
            )
        return Ok(
            cls(
                instant=instant,
                price=parsed_price,
                volume=parsed_volume,
                notional=parsed_notional,
            )
        )


@dataclass(frozen=True, slots=True)
class UnderlyingSeries:
    """The (possibly gap-fixed) series both derived bars and fills consume."""

    series_id: str
    samples: tuple[SeriesSample, ...]
    fingerprint: Fingerprint

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Sample order is significant."""
        return {
            "class": "underlying-series",
            "samples": [item.fp1_identity() for item in self.samples],
            "series_id": self.series_id,
        }

    @classmethod
    def try_create(cls, series_id: object, samples: object) -> Result[UnderlyingSeries]:
        """Validate a non-decreasing sample series and stamp its fp1."""
        token = clean_token(series_id)
        if token is None:
            return invalid(
                "series_id",
                "an underlying series names a non-empty series id",
                given=repr(series_id),
            )
        parsed = _as_samples(samples)
        if is_refusal(parsed):
            return parsed
        stamped = fingerprint(
            {
                "class": "underlying-series",
                "samples": [item.fp1_identity() for item in parsed.value],
                "series_id": token,
            }
        )
        if is_refusal(stamped):
            return stamped
        return Ok(cls(series_id=token, samples=parsed.value, fingerprint=stamped.value))


@dataclass(frozen=True, slots=True)
class DerivedBar:
    """One aggregated bar. Completeness is inspectable first-class state (B-2)."""

    stream_id: str
    bar_spec: DeclaredBarSpec
    interval: Interval
    open: int
    high: int
    close: int
    low: int
    volume: int
    completeness: str
    series_fp1: str
    sample_count: int
    completed_at: Instant | None = None

    @property
    def closed(self) -> bool:
        """True only on a completed boundary."""
        return self.completeness == COMPLETENESS_COMPLETED

    @property
    def visible_to_strategy(self) -> bool:
        """Forming bars are never visible."""
        return self.closed and FORMING_BAR_VISIBLE is False

    @property
    def actionable(self) -> bool:
        """Forming bars are never actionable."""
        return self.closed and FORMING_BAR_ACTIONABLE is False

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content: dict[str, object] = {
            "bar_spec": self.bar_spec.fp1_identity(),
            "close": self.close,
            "completeness": self.completeness,
            "high": self.high,
            "interval": self.interval.fp1_identity(),
            "low": self.low,
            "open": self.open,
            "sample_count": self.sample_count,
            "series_fp1": self.series_fp1,
            "stream_id": self.stream_id,
            "volume": self.volume,
        }
        if self.completed_at is not None:
            content["completed_at_ns"] = self.completed_at.value_ns
        return content


@dataclass(frozen=True, slots=True)
class FormingBarState:
    """Inspectable incompleteness. Never visible and never actionable (B-2)."""

    bar: DerivedBar
    filled_units: int
    required_units: int
    visible_to_strategy: bool = False
    actionable: bool = False

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Incompleteness is first-class, never implied."""
        return {
            "actionable": False,
            "bar": self.bar.fp1_identity(),
            "completeness": COMPLETENESS_FORMING,
            "filled_units": self.filled_units,
            "required_units": self.required_units,
            "visible_to_strategy": False,
        }

    @classmethod
    def try_create(
        cls,
        bar: object,
        filled_units: object,
        required_units: object,
    ) -> Result[FormingBarState]:
        """Build forming state. A completed bar cannot be wrapped as forming."""
        if not isinstance(bar, DerivedBar):
            return invalid(
                "bar",
                "forming state wraps a DerivedBar",
                given=repr(type(bar).__name__),
            )
        if bar.completeness != COMPLETENESS_FORMING:
            return invalid(
                "completeness",
                "forming state wraps a forming bar only",
                given=bar.completeness,
            )
        filled = _nonneg_int(filled_units)
        required = _positive_int(required_units)
        if filled is None or required is None:
            return invalid(
                "units",
                "forming completeness is filled_units/required_units as exact integers",
                filled=repr(filled_units),
                required=repr(required_units),
            )
        if filled >= required:
            return invalid(
                "units",
                "a forming bar has filled_units strictly below required_units",
                filled_units=filled,
                required_units=required,
            )
        return Ok(
            cls(
                bar=bar,
                filled_units=filled,
                required_units=required,
                visible_to_strategy=False,
                actionable=False,
            )
        )


@dataclass(frozen=True, slots=True)
class ReadableBarSet:
    """Strategy-visible bars: completed boundary only (B-2)."""

    bars: tuple[DerivedBar, ...]

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Forming bars cannot appear here."""
        return {
            "bars": [item.fp1_identity() for item in self.bars],
            "class": "readable-bar-set",
            "forming_bar_visible": FORMING_BAR_VISIBLE,
        }

    @classmethod
    def try_create(cls, bars: object) -> Result[ReadableBarSet]:
        """Refuse any forming bar — it is never in the readable set."""
        if isinstance(bars, (str, bytes)) or not isinstance(bars, Sequence):
            return invalid(
                "bars",
                "a readable set is a sequence of completed DerivedBar values",
                given=repr(type(bars).__name__),
            )
        parsed: list[DerivedBar] = []
        for index, raw in enumerate(cast("Sequence[object]", bars)):
            if not isinstance(raw, DerivedBar):
                return invalid(
                    "bars",
                    "each readable entry is a DerivedBar",
                    index=index,
                    given=repr(type(raw).__name__),
                )
            if raw.completeness != COMPLETENESS_COMPLETED or not raw.closed:
                return policy(
                    "bars",
                    "a forming bar is never visible or actionable (B-2)",
                    index=index,
                    completeness=raw.completeness,
                )
            parsed.append(raw)
        return Ok(cls(bars=tuple(parsed)))


@dataclass(frozen=True, slots=True)
class SameSliceConsumption:
    """Bars and fills bound to one underlying series at one frontier (B-2)."""

    stream_id: str
    series_fp1: str
    emitted: tuple[DerivedBar, ...]
    forming: tuple[FormingBarState, ...]
    fill_path: tuple[SeriesSample, ...]
    lookahead_prevention_independent_of_gap_0048: bool = True

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Bars and fills cite the same series_fp1."""
        return {
            "emitted": [item.fp1_identity() for item in self.emitted],
            "fill_path": [item.fp1_identity() for item in self.fill_path],
            "forming": [item.fp1_identity() for item in self.forming],
            "lookahead_prevention_independent_of_gap_0048": (
                LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048
            ),
            "series_fp1": self.series_fp1,
            "stream_id": self.stream_id,
        }


def require_same_series(bar_series_fp1: object, fill_series_fp1: object) -> Result[None]:
    """Refuse a divergent series between same-slice bars and fills (FR-037)."""
    bars = clean_token(bar_series_fp1)
    fills = clean_token(fill_series_fp1)
    if bars is None or fills is None:
        return invalid(
            "series_fp1",
            "bars and fills each cite a non-empty series fingerprint",
            bars=repr(bar_series_fp1),
            fills=repr(fill_series_fp1),
        )
    if bars != fills:
        return invalid(
            "series",
            "the bar is built from the same (possibly gap-fixed) series the "
            "fills run on — never a future or a divergent series (B-2, FR-037)",
            bars=bars,
            fills=fills,
        )
    return Ok(None)


def act_on_bar(bar: object) -> Result[DerivedBar]:
    """Permit action only on a completed bar. Forming is a policy rejection."""
    if isinstance(bar, FormingBarState):
        return policy(
            "bar",
            "a forming bar is never visible or actionable (B-2)",
            completeness=COMPLETENESS_FORMING,
            visible_to_strategy=False,
            actionable=False,
        )
    if not isinstance(bar, DerivedBar):
        return invalid(
            "bar",
            "action consumes a DerivedBar completed on its boundary",
            given=repr(type(bar).__name__),
        )
    if bar.completeness != COMPLETENESS_COMPLETED or not bar.actionable:
        return policy(
            "bar",
            "a forming bar is never visible or actionable (B-2)",
            completeness=bar.completeness,
        )
    return Ok(bar)


def readable_bars(
    emitted: object,
    forming: object = (),
) -> Result[ReadableBarSet]:
    """Strategy-readable set: completed bars only. Forming is excluded."""
    if forming is None:
        forming_items: tuple[object, ...] = ()
    elif isinstance(forming, (str, bytes)) or not isinstance(forming, Sequence):
        return invalid(
            "forming",
            "forming state is a sequence of FormingBarState values",
            given=repr(type(forming).__name__),
        )
    else:
        forming_items = tuple(cast("Sequence[object]", forming))
    for index, raw in enumerate(forming_items):
        leaked = isinstance(raw, FormingBarState) and (
            raw.visible_to_strategy
            or raw.actionable
            or raw.bar.completeness != COMPLETENESS_FORMING
        )
        if leaked:
            return policy(
                "forming",
                "a forming bar is never visible or actionable (B-2)",
                index=index,
            )
        if not isinstance(raw, FormingBarState):
            return invalid(
                "forming",
                "forming entries are FormingBarState values, never readable bars",
                index=index,
            )
    return ReadableBarSet.try_create(emitted)


def consume_same_slice(
    *,
    plan: object,
    series: object,
    frontier: object,
) -> Result[SameSliceConsumption]:
    """Derive bars and the fill path from one series at ``frontier`` (B-2).

    Samples after ``frontier`` are not consumed — look-ahead prevention by
    construction, independent of GAP-0048. Higher specs fold from the finest
    declared base and emit only on a completed boundary.
    """
    if not isinstance(plan, StreamBarPlan):
        return invalid(
            "bar_plan",
            "completed-boundary derivation takes a StreamBarPlan",
            given=repr(type(plan).__name__),
        )
    if not isinstance(series, UnderlyingSeries):
        return invalid(
            "series",
            "bars and fills consume one UnderlyingSeries",
            given=repr(type(series).__name__),
        )
    if not isinstance(frontier, Instant):
        return invalid(
            "frontier",
            "derivation reads the injected frontier Instant",
            given=repr(type(frontier).__name__),
        )
    if series.series_id != plan.stream_id:
        return invalid(
            "series_id",
            "the underlying series is the finest declared base stream; bars "
            "and fills cannot bind a foreign series (B-2, FR-037)",
            series_id=series.series_id,
            stream_id=plan.stream_id,
        )
    if plan.base.kind == "session":
        return unsupported(
            "bar_spec",
            "session BarSpec derivation needs a market-hours calendar; "
            "completed-boundary emission for session waits on that calendar",
            kind="session",
        )
    bound = require_same_series(series.fingerprint.value, series.fingerprint.value)
    if is_refusal(bound):
        return bound
    knowable = tuple(
        sample for sample in series.samples if sample.instant.value_ns <= frontier.value_ns
    )
    emitted: list[DerivedBar] = []
    forming: list[FormingBarState] = []
    for spec in plan.bar_specs:
        folded = _fold_spec(
            spec=spec,
            samples=knowable,
            frontier=frontier,
            stream_id=plan.stream_id,
            series_fp1=series.fingerprint.value,
        )
        if is_refusal(folded):
            return folded
        spec_emitted, spec_forming = folded.value
        emitted.extend(spec_emitted)
        forming.extend(spec_forming)
    fill_path = _intra_bar_path(plan.base, knowable, frontier)
    if is_refusal(fill_path):
        return fill_path
    return Ok(
        SameSliceConsumption(
            stream_id=plan.stream_id,
            series_fp1=series.fingerprint.value,
            emitted=tuple(emitted),
            forming=tuple(forming),
            fill_path=fill_path.value,
            lookahead_prevention_independent_of_gap_0048=(
                LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048
            ),
        )
    )


def consume_stream_plans(
    *,
    plans: object,
    series: object,
    frontier: object,
    stream_ids: object = None,
) -> Result[tuple[SameSliceConsumption, ...]]:
    """Derive each declared stream against its own series, declaration order."""
    parsed_plans = _as_plans(plans)
    if is_refusal(parsed_plans):
        return parsed_plans
    parsed_series = _as_series_map(series)
    if is_refusal(parsed_series):
        return parsed_series
    declared: tuple[str, ...] | None
    if stream_ids is None:
        declared = None
    elif isinstance(stream_ids, (str, bytes)) or not isinstance(stream_ids, Sequence):
        return invalid(
            "stream_ids",
            "stream ids are the stream-set declaration order",
            given=repr(type(stream_ids).__name__),
        )
    else:
        declared = tuple(cast("Sequence[str]", stream_ids))
    if declared is not None:
        order = declared
    else:
        order = tuple(item.stream_id for item in parsed_plans.value)
    by_id = {item.stream_id: item for item in parsed_plans.value}
    if len(by_id) != len(parsed_plans.value):
        return invalid("bar_plan", "each stream id appears once in the bar plan")
    if declared is not None:
        unknown = [item.stream_id for item in parsed_plans.value if item.stream_id not in declared]
        if unknown:
            return invalid(
                "stream_id",
                "a bar plan names a stream in the declared stream set",
                stream_id=unknown[0],
                declared=list(declared),
            )
    missing = [sid for sid in by_id if sid not in parsed_series.value]
    if missing:
        return invalid(
            "series",
            "each planned stream has an underlying series so bars and fills "
            "cannot diverge (B-2, FR-037)",
            stream_id=missing[0],
        )
    extra = [sid for sid in parsed_series.value if sid not in by_id]
    if extra:
        return invalid(
            "series",
            "a series without a BarSpec plan cannot derive higher bars",
            stream_id=extra[0],
        )
    consumed: list[SameSliceConsumption] = []
    for stream_id in order:
        plan = by_id.get(stream_id)
        if plan is None:
            continue
        item = consume_same_slice(
            plan=plan,
            series=parsed_series.value[stream_id],
            frontier=frontier,
        )
        if is_refusal(item):
            return item
        consumed.append(item.value)
    return Ok(tuple(consumed))


def _as_specs(value: object) -> Result[tuple[DeclaredBarSpec, ...]]:
    if isinstance(value, DeclaredBarSpec):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "bar_specs",
            "a stream member carries a BarSpec list (B-12); never a bare timeframe",
            given=repr(type(value).__name__),
        )
    parsed: list[DeclaredBarSpec] = []
    seen: set[tuple[str, int | str]] = set()
    for index, raw in enumerate(cast("Sequence[object]", value)):
        spec = DeclaredBarSpec.try_create(raw)
        if is_refusal(spec):
            return invalid(
                "bar_specs",
                "each BarSpec is a canonical identity mapping",
                index=index,
                cause=dict(spec.context),
            )
        key: tuple[str, int | str]
        size = spec.value.unit_size
        if size is None:
            key = (spec.value.kind, str(spec.value.parameters.get("session", "")))
        else:
            key = (spec.value.kind, size)
        if key in seen:
            return invalid(
                "bar_specs",
                "each BarSpec in a plan is unique",
                index=index,
                bar_spec=spec.value.fp1_identity(),
            )
        seen.add(key)
        parsed.append(spec.value)
    if not parsed:
        return invalid("bar_specs", "a stream declares one or more BarSpecs (B-12)")
    return Ok(tuple(parsed))


def _require_multiples(
    base: DeclaredBarSpec,
    specs: Sequence[DeclaredBarSpec],
) -> Result[None]:
    base_size = base.unit_size
    if base_size is None:
        return Ok(None)
    for spec in specs:
        size = spec.unit_size
        if size is None:
            return invalid("bar_specs", "higher specs share the base kind")
        if size == base_size:
            continue
        if size < base_size:
            return invalid(
                "bar_specs",
                "higher-BarSpec bars derive from the finest declared base; a "
                "finer spec than the base cannot appear",
                base=base.fp1_identity(),
                given=spec.fp1_identity(),
            )
        if size % base_size != 0:
            return invalid(
                "bar_specs",
                "a higher BarSpec is an integer multiple of the finest base so "
                "boundaries align (B-2)",
                base=base.fp1_identity(),
                given=spec.fp1_identity(),
            )
    return Ok(None)


def _as_samples(value: object) -> Result[tuple[SeriesSample, ...]]:
    if isinstance(value, SeriesSample):
        items = (value,)
    elif isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "samples",
            "an underlying series is a sequence of SeriesSample prints",
            given=repr(type(value).__name__),
        )
    else:
        parsed: list[SeriesSample] = []
        for index, raw in enumerate(cast("Sequence[object]", value)):
            if isinstance(raw, SeriesSample):
                item = Ok(raw)
            elif isinstance(raw, Mapping):
                mapping = cast("Mapping[str, object]", raw)
                item = SeriesSample.try_create(
                    mapping.get("instant"),
                    mapping.get("price"),
                    mapping.get("volume", 0),
                    mapping.get("notional", 0),
                )
            else:
                return invalid(
                    "samples",
                    "each sample is a SeriesSample or a mapping",
                    index=index,
                    given=repr(type(raw).__name__),
                )
            if is_refusal(item):
                return invalid(
                    "samples",
                    "each sample is a knowable series print",
                    index=index,
                    cause=dict(item.context),
                )
            parsed.append(item.value)
        items = tuple(parsed)
    previous: int | None = None
    for index, sample in enumerate(items):
        if previous is not None and sample.instant.value_ns < previous:
            return invalid(
                "samples",
                "underlying series samples are non-decreasing in Instant order",
                index=index,
                instant_ns=sample.instant.value_ns,
                previous_ns=previous,
            )
        previous = sample.instant.value_ns
    return Ok(items)


def _as_plans(value: object) -> Result[tuple[StreamBarPlan, ...]]:
    if isinstance(value, StreamBarPlan):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "bar_plan",
            "bar plans are a StreamBarPlan or a sequence of plans",
            given=repr(type(value).__name__),
        )
    parsed: list[StreamBarPlan] = []
    for index, raw in enumerate(cast("Sequence[object]", value)):
        if isinstance(raw, StreamBarPlan):
            parsed.append(raw)
            continue
        if isinstance(raw, Mapping):
            mapping = cast("Mapping[str, object]", raw)
            plan = StreamBarPlan.try_create(
                mapping.get("stream_id"),
                mapping.get("bar_specs"),
            )
            if is_refusal(plan):
                return invalid(
                    "bar_plan",
                    "each plan names stream_id and bar_specs",
                    index=index,
                    cause=dict(plan.context),
                )
            parsed.append(plan.value)
            continue
        return invalid(
            "bar_plan",
            "each plan is a StreamBarPlan or a mapping",
            index=index,
            given=repr(type(raw).__name__),
        )
    if not parsed:
        return invalid("bar_plan", "completed-boundary derivation needs one or more bar plans")
    return Ok(tuple(parsed))


def _as_series_map(value: object) -> Result[Mapping[str, UnderlyingSeries]]:
    if isinstance(value, UnderlyingSeries):
        return Ok(MappingProxyType({value.series_id: value}))
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        parsed: dict[str, UnderlyingSeries] = {}
        for key, raw in mapping.items():
            token = clean_token(key)
            if token is None:
                return invalid(
                    "series",
                    "series map keys are non-empty stream ids",
                    given=repr(key),
                )
            series = _coerce_series(raw, token)
            if is_refusal(series):
                return series
            parsed[token] = series.value
        if not parsed:
            return invalid("series", "bars and fills need one underlying series")
        return Ok(MappingProxyType(parsed))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        parsed_seq: dict[str, UnderlyingSeries] = {}
        for index, raw in enumerate(cast("Sequence[object]", value)):
            if not isinstance(raw, UnderlyingSeries):
                return invalid(
                    "series",
                    "a series sequence contains UnderlyingSeries values",
                    index=index,
                    given=repr(type(raw).__name__),
                )
            if raw.series_id in parsed_seq:
                return invalid(
                    "series_id",
                    "each underlying series id appears once",
                    series_id=raw.series_id,
                )
            parsed_seq[raw.series_id] = raw
        if not parsed_seq:
            return invalid("series", "bars and fills need one underlying series")
        return Ok(MappingProxyType(parsed_seq))
    return invalid(
        "series",
        "series is an UnderlyingSeries, a stream-id map, or a sequence",
        given=repr(type(value).__name__),
    )


def _coerce_series(raw: object, stream_id: str) -> Result[UnderlyingSeries]:
    if isinstance(raw, UnderlyingSeries):
        if raw.series_id != stream_id:
            return invalid(
                "series_id",
                "series map key must match the UnderlyingSeries series_id",
                key=stream_id,
                series_id=raw.series_id,
            )
        return Ok(raw)
    if isinstance(raw, Mapping):
        mapping = cast("Mapping[str, object]", raw)
        return UnderlyingSeries.try_create(
            mapping.get("series_id", stream_id),
            mapping.get("samples"),
        )
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        return UnderlyingSeries.try_create(stream_id, cast("Sequence[object]", raw))
    return invalid(
        "series",
        "each series is an UnderlyingSeries, a mapping, or samples",
        stream_id=stream_id,
        given=repr(type(raw).__name__),
    )


def _fold_spec(
    *,
    spec: DeclaredBarSpec,
    samples: Sequence[SeriesSample],
    frontier: Instant,
    stream_id: str,
    series_fp1: str,
) -> Result[tuple[tuple[DerivedBar, ...], tuple[FormingBarState, ...]]]:
    if spec.kind == "time-interval":
        return _fold_time(
            spec=spec,
            samples=samples,
            frontier=frontier,
            stream_id=stream_id,
            series_fp1=series_fp1,
        )
    if spec.kind in _EVENT_KINDS:
        return _fold_event(
            spec=spec,
            samples=samples,
            frontier=frontier,
            stream_id=stream_id,
            series_fp1=series_fp1,
        )
    return unsupported(
        "bar_spec",
        "completed-boundary derivation supports time-interval and event-driven BarSpec kinds",
        kind=spec.kind,
    )


def _fold_time(
    *,
    spec: DeclaredBarSpec,
    samples: Sequence[SeriesSample],
    frontier: Instant,
    stream_id: str,
    series_fp1: str,
) -> Result[tuple[tuple[DerivedBar, ...], tuple[FormingBarState, ...]]]:
    period = _period_ns(spec)
    if is_refusal(period):
        return period
    grouped: dict[int, list[SeriesSample]] = {}
    intervals: dict[int, Interval] = {}
    for sample in samples:
        window = _aligned_window(sample.instant, period.value)
        if is_refusal(window):
            return window
        start_ns = window.value.start.value_ns
        grouped.setdefault(start_ns, []).append(sample)
        intervals[start_ns] = window.value
    emitted: list[DerivedBar] = []
    forming: list[FormingBarState] = []
    for start_ns in sorted(grouped):
        interval = intervals[start_ns]
        completed = frontier.value_ns >= interval.end.value_ns
        completeness = COMPLETENESS_COMPLETED if completed else COMPLETENESS_FORMING
        completed_at = interval.end
        bar = _ohlc_bar(
            stream_id=stream_id,
            spec=spec,
            interval=interval,
            bucket=grouped[start_ns],
            completeness=completeness,
            series_fp1=series_fp1,
            completed_at=completed_at,
        )
        if is_refusal(bar):
            return bar
        if completed:
            emitted.append(bar.value)
            continue
        filled = max(0, frontier.value_ns - interval.start.value_ns)
        state = FormingBarState.try_create(bar.value, filled, period.value)
        if is_refusal(state):
            return state
        forming.append(state.value)
    return Ok((tuple(emitted), tuple(forming)))


def _fold_event(
    *,
    spec: DeclaredBarSpec,
    samples: Sequence[SeriesSample],
    frontier: Instant,
    stream_id: str,
    series_fp1: str,
) -> Result[tuple[tuple[DerivedBar, ...], tuple[FormingBarState, ...]]]:
    _ = frontier
    size = spec.unit_size
    if size is None:
        return invalid("bar_spec", "event-driven BarSpec declares a positive unit")
    buckets, remainder = _event_buckets(spec.kind, samples, size)
    emitted: list[DerivedBar] = []
    forming: list[FormingBarState] = []
    for bucket in buckets:
        interval = _span(bucket)
        if is_refusal(interval):
            return interval
        last = bucket[-1].instant
        bar = _ohlc_bar(
            stream_id=stream_id,
            spec=spec,
            interval=interval.value,
            bucket=bucket,
            completeness=COMPLETENESS_COMPLETED,
            series_fp1=series_fp1,
            completed_at=last,
        )
        if is_refusal(bar):
            return bar
        emitted.append(bar.value)
    if remainder:
        interval = _span(remainder)
        if is_refusal(interval):
            return interval
        bar = _ohlc_bar(
            stream_id=stream_id,
            spec=spec,
            interval=interval.value,
            bucket=remainder,
            completeness=COMPLETENESS_FORMING,
            series_fp1=series_fp1,
            completed_at=None,
        )
        if is_refusal(bar):
            return bar
        filled = _event_filled(spec.kind, remainder)
        state = FormingBarState.try_create(bar.value, filled, size)
        if is_refusal(state):
            return state
        forming.append(state.value)
    return Ok((tuple(emitted), tuple(forming)))


def _event_buckets(
    kind: str,
    samples: Sequence[SeriesSample],
    size: int,
) -> tuple[list[list[SeriesSample]], list[SeriesSample]]:
    buckets: list[list[SeriesSample]] = []
    current: list[SeriesSample] = []
    accumulated = 0
    open_price: int | None = None
    for sample in samples:
        if not current:
            open_price = sample.price
            accumulated = 0
        current.append(sample)
        accumulated = _event_progress(kind, current, open_price or sample.price, sample)
        if accumulated >= size:
            buckets.append(current)
            current = []
            accumulated = 0
            open_price = None
    return buckets, current


def _event_progress(
    kind: str,
    bucket: Sequence[SeriesSample],
    open_price: int,
    sample: SeriesSample,
) -> int:
    if kind == "tick-count":
        return len(bucket)
    if kind == "volume-threshold":
        return sum(item.volume for item in bucket)
    if kind == "notional-threshold":
        return sum(item.notional if item.notional else item.volume for item in bucket)
    high = max(item.price for item in bucket)
    low = min(item.price for item in bucket)
    if kind == "range":
        return high - low
    # price-brick: excursion from the bucket open.
    _ = sample
    excursion = open_price - low
    up = high - open_price
    return up if up >= excursion else excursion


def _event_filled(kind: str, bucket: Sequence[SeriesSample]) -> int:
    if not bucket:
        return 0
    return _event_progress(kind, bucket, bucket[0].price, bucket[-1])


def _intra_bar_path(
    spec: DeclaredBarSpec,
    samples: Sequence[SeriesSample],
    frontier: Instant,
) -> Result[tuple[SeriesSample, ...]]:
    if not samples:
        return Ok(())
    if spec.kind == "time-interval":
        period = _period_ns(spec)
        if is_refusal(period):
            return period
        window = _aligned_window(frontier, period.value)
        if is_refusal(window):
            return window
        path = tuple(
            sample
            for sample in samples
            if window.value.start.value_ns <= sample.instant.value_ns < window.value.end.value_ns
        )
        return Ok(path)
    size = spec.unit_size
    if size is None:
        return Ok(tuple(samples))
    _buckets, remainder = _event_buckets(spec.kind, samples, size)
    return Ok(tuple(remainder) if remainder else ())


def _period_ns(spec: DeclaredBarSpec) -> Result[int]:
    seconds = spec.unit_size
    if seconds is None:
        return invalid("seconds", "a time-interval BarSpec declares positive seconds")
    raw = seconds * _NS_PER_SEC
    if raw > _INT64_MAX:
        return invalid(
            "seconds",
            "BarSpec period overflowed the int64 nanosecond range",
            seconds=seconds,
        )
    return Ok(raw)


def _aligned_window(instant: Instant, period_ns: int) -> Result[Interval]:
    start_ns = (instant.value_ns // period_ns) * period_ns
    end_ns = start_ns + period_ns
    if end_ns > _INT64_MAX:
        return invalid(
            "interval",
            "bar exclusive-end overflowed the int64 nanosecond range",
            start_ns=start_ns,
        )
    start = Instant.try_create(start_ns)
    if is_refusal(start):
        return start
    end = Instant.try_create(end_ns)
    if is_refusal(end):
        return end
    return Interval.try_create(start.value, end.value)


def _span(bucket: Sequence[SeriesSample]) -> Result[Interval]:
    first = bucket[0].instant
    last = bucket[-1].instant
    bumped = Instant.try_create(last.value_ns + 1)
    if is_refusal(bumped):
        return bumped
    return Interval.try_create(first, bumped.value)


def _ohlc_bar(
    *,
    stream_id: str,
    spec: DeclaredBarSpec,
    interval: Interval,
    bucket: Sequence[SeriesSample],
    completeness: str,
    series_fp1: str,
    completed_at: Instant | None,
) -> Result[DerivedBar]:
    if not bucket:
        return invalid("samples", "a derived bar needs one or more series prints")
    prices = [item.price for item in bucket]
    return Ok(
        DerivedBar(
            stream_id=stream_id,
            bar_spec=spec,
            interval=interval,
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            volume=sum(item.volume for item in bucket),
            completeness=completeness,
            series_fp1=series_fp1,
            sample_count=len(bucket),
            completed_at=completed_at,
        )
    )
