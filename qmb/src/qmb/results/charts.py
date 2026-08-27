"""Chart series as data, never images (Story 19.4, B-10, R-RPT-11..15).

Every V1 chart is a machine-readable series ``{name, unit_kind, points:[{t, v}]}``
derived from the run's own ordered position/order/journal record. ``t`` is
int64 UTC-ns; ``v`` is exact-integer money or an exact-rational ratio. No
image, base64, or PNG is the canonical payload. Color, style, and histogram
bins are renderer concerns and are never embedded. Display downsample is a
derivative with a declared sampler identity and is AD-10-excluded from
artifact identity — never the canonical payload.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from typing import Final, cast

from qmf.core.chrono import Instant, Interval
from qmf.core.exact import ExactRational, Money, Quantity, UnitKind
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.journal import JournalEvent, JournalEventType
from qmf.risk.door import Direction

from qmb._refuse import clean_token, invalid
from qmb.results.measures import ClosedTrade, EquityPoint

__all__ = [
    "BENCHMARK_KEY",
    "CHART_FORMAT_VERSION",
    "DISPLAY_SAMPLER_IDENTITY",
    "NO_BENCHMARK_DECLARED",
    "OMIT_NO_POSITION_STREAM",
    "OMIT_SINGLE_UNLEVERAGED",
    "TOP_WORST_PERIODS",
    "V1_CHART_SERIES_NAMES",
    "AnnualReturnCell",
    "ChartSeries",
    "ChartSet",
    "DisplayDownsample",
    "HistogramReadyArray",
    "HoldingMark",
    "MonthlyReturnCell",
    "OmittedSeries",
    "SeriesPoint",
    "WorstDrawdownPeriod",
    "assemble_v1_chart_set",
    "downsample_chart_series",
]

CHART_FORMAT_VERSION: Final[int] = 1
TOP_WORST_PERIODS: Final[int] = 5
BENCHMARK_KEY: Final[str] = "benchmark"
NO_BENCHMARK_DECLARED: Final[str] = "no benchmark declared"
OMIT_SINGLE_UNLEVERAGED: Final[str] = "single-instrument unleveraged run"
OMIT_NO_POSITION_STREAM: Final[str] = "no position stream"
DISPLAY_SAMPLER_IDENTITY: Final[str] = "stride-nth"
V1_CHART_SERIES_NAMES: Final[tuple[str, ...]] = (
    "equity",
    "cumulative_returns",
    "drawdown",
    "underwater",
)
BENCHMARK_RELATIVE_NAMES: Final[tuple[str, ...]] = (
    "cumulative_returns_benchmark",
    "alpha",
    "beta",
)
HOLDINGS_FAMILY: Final[tuple[str, ...]] = (
    "holdings",
    "exposure",
    "allocation",
    "leverage",
)
BANNED_RENDERER_KEYS: Final[frozenset[str]] = frozenset(
    {
        "base64",
        "bin",
        "bins",
        "color",
        "histogram_bin",
        "image",
        "png",
        "style",
        "svg",
    }
)
_EPOCH_UTC: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)
_NS_PER_SECOND: Final[int] = 1_000_000_000
PointValue = Money | ExactRational


@dataclass(frozen=True, slots=True)
class SeriesPoint:
    """One canonical chart point: int64 UTC-ns time and a unit-kinded value."""

    t: Instant
    v: PointValue

    @classmethod
    def try_create(cls, t: object, v: object) -> Result[SeriesPoint]:
        """Validate and build a :class:`SeriesPoint`, value-or-refusal."""
        if not isinstance(t, Instant):
            return invalid(
                "t",
                "a chart point timestamp is an Instant (int64 UTC-ns)",
                given=repr(type(t).__name__),
            )
        if not isinstance(v, (Money, ExactRational)):
            return invalid(
                "v",
                "a chart point value is exact-integer Money or an exact-rational ratio",
                given=repr(type(v).__name__),
            )
        return Ok(cls(t=t, v=v))

    def as_data(self) -> dict[str, object]:
        """Canonical ``{t, v}`` payload. No color, style, or bin."""
        return {"t": self.t.value_ns, "v": self.v.fp1_identity()}


@dataclass(frozen=True, slots=True)
class ChartSeries:
    """One chart as series data: ``{name, unit_kind, points:[{t, v}]}`` (R-RPT-12)."""

    name: str
    unit_kind: UnitKind
    points: tuple[SeriesPoint, ...]

    @classmethod
    def try_create(cls, name: object, unit_kind: object, points: object) -> Result[ChartSeries]:
        """Validate and build a :class:`ChartSeries`, value-or-refusal."""
        token = clean_token(name)
        if token is None:
            return invalid(
                "name",
                "a chart series declares a non-empty name",
                given=repr(name),
            )
        if unit_kind is None:
            return invalid(
                "unit_kind",
                "a null unit-kind is a typed refusal, never a default (R-RPT-12, DEC-0154)",
            )
        kind = _as_unit_kind(unit_kind)
        if is_refusal(kind):
            return kind
        rows = _as_points(points, kind.value)
        if is_refusal(rows):
            return rows
        return Ok(cls(name=token, unit_kind=kind.value, points=rows.value))

    def as_data(self) -> dict[str, object]:
        """Canonical series payload. Renderer concerns are absent."""
        return {
            "name": self.name,
            "unit_kind": self.unit_kind.value,
            "points": [point.as_data() for point in self.points],
        }


@dataclass(frozen=True, slots=True)
class WorstDrawdownPeriod:
    """One worst-period row ``{start, bottom, recovery, max_drawdown}`` (R-RPT-13)."""

    start: Instant
    bottom: Instant
    recovery: Instant
    max_drawdown: ExactRational

    def as_data(self) -> dict[str, object]:
        """Canonical worst-period table row."""
        return {
            "start": self.start.value_ns,
            "bottom": self.bottom.value_ns,
            "recovery": self.recovery.value_ns,
            "max_drawdown": self.max_drawdown.fp1_identity(),
        }


@dataclass(frozen=True, slots=True)
class MonthlyReturnCell:
    """One ``(year, month) → return`` grid cell (R-RPT-13)."""

    year: int
    month: int
    value: ExactRational

    def as_data(self) -> dict[str, object]:
        """Canonical monthly-returns grid cell."""
        return {
            "year": self.year,
            "month": self.month,
            "value": self.value.fp1_identity(),
        }


@dataclass(frozen=True, slots=True)
class AnnualReturnCell:
    """Annual-total column of the monthly-returns grid (R-RPT-13)."""

    year: int
    value: ExactRational

    def as_data(self) -> dict[str, object]:
        """Canonical annual-total cell."""
        return {"year": self.year, "value": self.value.fp1_identity()}


@dataclass(frozen=True, slots=True)
class HistogramReadyArray:
    """Raw histogram-ready values. Bins are a renderer concern (R-RPT-12)."""

    name: str
    unit_kind: UnitKind
    values: tuple[PointValue, ...]

    def as_data(self) -> dict[str, object]:
        """Canonical raw array. No histogram bin is embedded."""
        return {
            "name": self.name,
            "unit_kind": self.unit_kind.value,
            "values": [item.fp1_identity() for item in self.values],
        }


@dataclass(frozen=True, slots=True)
class OmittedSeries:
    """An explicit omission note — never a faked empty series (R-RPT-13, R-RPT-15)."""

    name: str
    reason: str

    def as_data(self) -> dict[str, object]:
        """Canonical omission note."""
        return {"name": self.name, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class HoldingMark:
    """One ordered position mark reconstructed from the run's position stream."""

    at: Instant
    instrument: str
    quantity: Quantity
    direction: Direction
    market_value: Money
    notional: Money

    @classmethod
    def try_create(
        cls,
        at: object,
        instrument: object,
        quantity: object,
        direction: object,
        market_value: object,
        notional: object = None,
    ) -> Result[HoldingMark]:
        """Validate and build a :class:`HoldingMark`, value-or-refusal."""
        if not isinstance(at, Instant):
            return invalid(
                "at",
                "a holding mark is timestamped with an Instant (int64 UTC-ns)",
                given=repr(type(at).__name__),
            )
        token = clean_token(instrument)
        if token is None:
            return invalid(
                "instrument",
                "a holding mark names a non-empty instrument token",
                given=repr(instrument),
            )
        if not isinstance(quantity, Quantity):
            return invalid(
                "quantity",
                "a holding quantity is exact Quantity, never a binary float",
                given=repr(type(quantity).__name__),
            )
        if quantity.as_fraction() <= 0:
            return invalid(
                "quantity",
                "a holding quantity is a positive exact count; side is direction",
                given=str(quantity.as_fraction()),
            )
        sided = _as_direction(direction)
        if is_refusal(sided):
            return sided
        if not isinstance(market_value, Money):
            return invalid(
                "market_value",
                "holding market value is exact Money at the declared currency scale",
                given=repr(type(market_value).__name__),
            )
        gross = _as_notional(market_value, notional)
        if is_refusal(gross):
            return gross
        return Ok(
            cls(
                at=at,
                instrument=token,
                quantity=quantity,
                direction=sided.value,
                market_value=market_value,
                notional=gross.value,
            )
        )


@dataclass(frozen=True, slots=True)
class ChartSet:
    """V1 chart payload: series data plus companion tables, never images (R-RPT-13).

    This extension is AD-10-excluded from CT-32 identity. It has no
    ``fp1_identity`` so it cannot be folded into the artifact fingerprint.
    """

    series: tuple[ChartSeries, ...]
    worst_periods: tuple[WorstDrawdownPeriod, ...]
    monthly_returns: tuple[MonthlyReturnCell, ...]
    annual_returns: tuple[AnnualReturnCell, ...]
    monthly_return_distribution: HistogramReadyArray
    trade_pnl_distribution: HistogramReadyArray
    omitted: tuple[OmittedSeries, ...]
    benchmark_identity: str | None

    def series_named(self, name: str) -> ChartSeries | None:
        """Return the series with ``name``, or ``None`` if omitted."""
        for series in self.series:
            if series.name == name:
                return series
        return None

    def as_data(self) -> dict[str, object]:
        """Canonical chart payload. Display downsample is not included."""
        payload: dict[str, object] = {
            "ad10_excluded": True,
            "annual_returns": [row.as_data() for row in self.annual_returns],
            "canonical_payload": "series-data",
            "class": "qmb-chart-set",
            "distributions": {
                "monthly_return": self.monthly_return_distribution.as_data(),
                "trade_pnl": self.trade_pnl_distribution.as_data(),
            },
            "format_version": CHART_FORMAT_VERSION,
            "in_identity": False,
            "monthly_returns": [row.as_data() for row in self.monthly_returns],
            "omitted": [row.as_data() for row in self.omitted],
            "series": [series.as_data() for series in self.series],
            "worst_periods": [row.as_data() for row in self.worst_periods],
        }
        if self.benchmark_identity is not None:
            payload["benchmark_identity"] = self.benchmark_identity
        return payload


@dataclass(frozen=True, slots=True)
class DisplayDownsample:
    """Display-only derivative of a canonical series (B-10).

    Carries a declared sampler identity and is AD-10-excluded from artifact
    identity. Never the canonical payload. Has no ``fp1_identity``.
    """

    sampler_identity: str
    series: ChartSeries
    stride: int

    def as_data(self) -> dict[str, object]:
        """Display derivative payload. Not folded into CT-32 identity."""
        return {
            "ad10_excluded": True,
            "class": "display-downsample",
            "in_identity": False,
            "sampler_identity": self.sampler_identity,
            "series": self.series.as_data(),
            "stride": self.stride,
        }


def assemble_v1_chart_set(
    *,
    starting_capital: object,
    period: object,
    trades: object = (),
    equity_curve: object = (),
    holdings: object = (),
    journal_events: object = (),
    instruments: object = (),
    leveraged: object = False,
    benchmark: object = None,
    benchmark_curve: object = (),
) -> Result[ChartSet]:
    """Assemble the V1 chart set from the run's own ordered record (R-RPT-13).

    Source is the run's position/fill/trade/journal record, never a parallel
    log and never an image. Holdings/exposure/allocation/leverage are omitted
    on a single-instrument unleveraged run rather than faked. Benchmark-relative
    series are omitted with ``no benchmark declared`` when Book/BMS has none.
    """
    image = _refuse_image_payload("equity_curve", equity_curve)
    if is_refusal(image):
        return image
    image = _refuse_image_payload("trades", trades)
    if is_refusal(image):
        return image
    image = _refuse_image_payload("holdings", holdings)
    if is_refusal(image):
        return image
    image = _refuse_image_payload("benchmark_curve", benchmark_curve)
    if is_refusal(image):
        return image
    if not isinstance(starting_capital, Money):
        return invalid(
            "starting_capital",
            "start equity is exact Money at the declared currency scale, never a float",
            given=repr(type(starting_capital).__name__),
        )
    if not isinstance(period, Interval):
        return invalid(
            "period",
            "chart assembly reads the result period as an AD-8 Interval",
            given=repr(type(period).__name__),
        )
    if not isinstance(leveraged, bool):
        return invalid(
            "leveraged",
            "leveraged is an explicit bool on the Book/BMS run; it is never inferred from a string",
            given=repr(type(leveraged).__name__),
        )
    events = _as_journal_events(journal_events)
    if is_refusal(events):
        return events
    closed = _resolve_trades(trades, events.value)
    if is_refusal(closed):
        return closed
    points = _as_equity_points(equity_curve)
    if is_refusal(points):
        return points
    marks = _as_holdings(holdings)
    if is_refusal(marks):
        return marks
    named = _as_instruments(instruments)
    if is_refusal(named):
        return named
    currency_ok = _currency_guard(starting_capital, closed.value, points.value, marks.value)
    if is_refusal(currency_ok):
        return currency_ok
    path = _equity_path(starting_capital, period, closed.value, points.value)
    if is_refusal(path):
        return path
    core = _core_series(path.value, starting_capital)
    if is_refusal(core):
        return core
    series_rows, omitted = core.value
    assembled = list(series_rows)
    worst = _worst_periods(path.value, period)
    if is_refusal(worst):
        return worst
    monthly = _monthly_grid(path.value, starting_capital)
    if is_refusal(monthly):
        return monthly
    cells, annual = monthly.value
    month_dist = _monthly_distribution(cells)
    trade_dist = _trade_distribution(closed.value)
    bench_id, bench_note = _benchmark_identity(benchmark)
    if is_refusal(bench_id):
        return bench_id
    if bench_note is not None:
        omitted.extend(bench_note)
    else:
        extra = _benchmark_series(benchmark_curve, starting_capital, period)
        if is_refusal(extra):
            return extra
        assembled.extend(extra.value)
    extra_holdings, extra_omit = _holdings_family(
        marks.value,
        path.value,
        named.value,
        leveraged=leveraged,
    )
    if is_refusal(extra_holdings):
        return extra_holdings
    assembled.extend(extra_holdings.value)
    omitted.extend(extra_omit)
    return Ok(
        ChartSet(
            series=tuple(assembled),
            worst_periods=worst.value,
            monthly_returns=cells,
            annual_returns=annual,
            monthly_return_distribution=month_dist,
            trade_pnl_distribution=trade_dist,
            omitted=tuple(omitted),
            benchmark_identity=bench_id.value,
        )
    )


def downsample_chart_series(
    series: object,
    *,
    sampler_identity: object = DISPLAY_SAMPLER_IDENTITY,
    stride: object = 1,
) -> Result[DisplayDownsample]:
    """Produce a display-only downsample with a declared sampler identity (B-10).

    AD-10-excluded from artifact identity. Never the canonical payload.
    """
    if not isinstance(series, ChartSeries):
        return invalid(
            "series",
            "display downsample reads a canonical ChartSeries, never an image",
            given=repr(type(series).__name__),
        )
    token = clean_token(sampler_identity)
    if token is None or token != DISPLAY_SAMPLER_IDENTITY:
        return invalid(
            "sampler_identity",
            "V1 display downsample sampler identity is stride-nth; the sampler is a "
            "renderer input, never a run-config field (B-10)",
            given=repr(sampler_identity),
            allowed=[DISPLAY_SAMPLER_IDENTITY],
        )
    if isinstance(stride, bool) or not isinstance(stride, int) or stride < 1:
        return invalid(
            "stride",
            "stride-nth keeps every Nth canonical point plus the first and last",
            given=repr(stride),
        )
    kept = _stride_points(series.points, stride)
    derived = ChartSeries.try_create(series.name, series.unit_kind, kept)
    if is_refusal(derived):
        return derived
    return Ok(
        DisplayDownsample(
            sampler_identity=token,
            series=derived.value,
            stride=stride,
        )
    )


def _core_series(
    path: tuple[EquityPoint, ...], start: Money
) -> Result[tuple[tuple[ChartSeries, ...], list[OmittedSeries]]]:
    equity_points: list[SeriesPoint] = []
    cum_points: list[SeriesPoint] = []
    dd_points: list[SeriesPoint] = []
    under_points: list[SeriesPoint] = []
    omitted: list[OmittedSeries] = []
    start_frac = start.as_fraction()
    peak = start_frac
    for item in path:
        equity_pt = SeriesPoint.try_create(item.at, item.equity)
        if is_refusal(equity_pt):
            return equity_pt
        equity_points.append(equity_pt.value)
        equity_frac = item.equity.as_fraction()
        peak = max(peak, equity_frac)
        if peak == 0:
            drawdown = Fraction(0)
        else:
            drawdown = (peak - equity_frac) / peak
            if drawdown < 0:
                drawdown = Fraction(0)
        dd_ratio = _ratio(drawdown)
        if is_refusal(dd_ratio):
            return dd_ratio
        dd_pt = SeriesPoint.try_create(item.at, dd_ratio.value)
        if is_refusal(dd_pt):
            return dd_pt
        dd_points.append(dd_pt.value)
        under_ratio = _ratio(-drawdown)
        if is_refusal(under_ratio):
            return under_ratio
        under_pt = SeriesPoint.try_create(item.at, under_ratio.value)
        if is_refusal(under_pt):
            return under_pt
        under_points.append(under_pt.value)
        if start_frac != 0:
            cum = _ratio((equity_frac / start_frac) - 1)
            if is_refusal(cum):
                return cum
            cum_pt = SeriesPoint.try_create(item.at, cum.value)
            if is_refusal(cum_pt):
                return cum_pt
            cum_points.append(cum_pt.value)
    series: list[ChartSeries] = []
    equity = ChartSeries.try_create("equity", UnitKind.MONEY, tuple(equity_points))
    if is_refusal(equity):
        return equity
    series.append(equity.value)
    if cum_points:
        cumulative = ChartSeries.try_create(
            "cumulative_returns", UnitKind.DIMENSIONLESS_RATIO, tuple(cum_points)
        )
        if is_refusal(cumulative):
            return cumulative
        series.append(cumulative.value)
    else:
        omitted.append(OmittedSeries("cumulative_returns", "start equity is zero"))
    drawdown_s = ChartSeries.try_create("drawdown", UnitKind.DIMENSIONLESS_RATIO, tuple(dd_points))
    if is_refusal(drawdown_s):
        return drawdown_s
    series.append(drawdown_s.value)
    underwater = ChartSeries.try_create(
        "underwater", UnitKind.DIMENSIONLESS_RATIO, tuple(under_points)
    )
    if is_refusal(underwater):
        return underwater
    series.append(underwater.value)
    found: tuple[ChartSeries, ...] = tuple(series)
    return Ok((found, omitted))


def _worst_periods(
    path: tuple[EquityPoint, ...], period: Interval
) -> Result[tuple[WorstDrawdownPeriod, ...]]:
    if not path:
        return Ok(())
    peak = path[0].equity.as_fraction()
    peak_at = path[0].at
    in_dd = False
    start = path[0].at
    bottom = path[0].at
    max_dd = Fraction(0)
    rows: list[WorstDrawdownPeriod] = []
    for point in path[1:]:
        equity = point.equity.as_fraction()
        if equity >= peak:
            if in_dd and max_dd > 0:
                minted = _worst_row(start, bottom, point.at, max_dd)
                if is_refusal(minted):
                    return minted
                rows.append(minted.value)
            peak = equity
            peak_at = point.at
            in_dd = False
            max_dd = Fraction(0)
            continue
        if peak == 0:
            continue
        drawdown = (peak - equity) / peak
        if not in_dd:
            in_dd = True
            start = peak_at
            bottom = point.at
            max_dd = drawdown
            continue
        if drawdown > max_dd:
            max_dd = drawdown
            bottom = point.at
        elif drawdown == max_dd:
            bottom = point.at
    if in_dd and max_dd > 0:
        minted = _worst_row(start, bottom, period.end, max_dd)
        if is_refusal(minted):
            return minted
        rows.append(minted.value)
    ranked = sorted(
        rows,
        key=lambda row: (-row.max_drawdown.as_fraction(), row.start.value_ns),
    )
    return Ok(tuple(ranked[:TOP_WORST_PERIODS]))


def _worst_row(
    start: Instant, bottom: Instant, recovery: Instant, max_dd: Fraction
) -> Result[WorstDrawdownPeriod]:
    ratio = _ratio(max_dd)
    if is_refusal(ratio):
        return ratio
    return Ok(
        WorstDrawdownPeriod(start=start, bottom=bottom, recovery=recovery, max_drawdown=ratio.value)
    )


def _monthly_grid(
    path: tuple[EquityPoint, ...], start: Money
) -> Result[tuple[tuple[MonthlyReturnCell, ...], tuple[AnnualReturnCell, ...]]]:
    if not path:
        return Ok(((), ()))
    month_end: dict[tuple[int, int], EquityPoint] = {}
    for point in path:
        month_end[_utc_year_month(point.at)] = point
    keys = sorted(month_end)
    prev_equity = start.as_fraction()
    cells: list[MonthlyReturnCell] = []
    year_start: dict[int, Fraction] = {}
    year_end: dict[int, Fraction] = {}
    for year, month in keys:
        point = month_end[(year, month)]
        current = point.equity.as_fraction()
        if year not in year_start:
            year_start[year] = prev_equity
        year_end[year] = current
        if prev_equity == 0:
            prev_equity = current
            continue
        ratio = _ratio((current - prev_equity) / prev_equity)
        if is_refusal(ratio):
            return ratio
        cells.append(MonthlyReturnCell(year=year, month=month, value=ratio.value))
        prev_equity = current
    annual: list[AnnualReturnCell] = []
    for year in sorted(year_end):
        opened = year_start[year]
        closed = year_end[year]
        if opened == 0:
            continue
        ratio = _ratio((closed - opened) / opened)
        if is_refusal(ratio):
            return ratio
        annual.append(AnnualReturnCell(year=year, value=ratio.value))
    return Ok((tuple(cells), tuple(annual)))


def _monthly_distribution(cells: tuple[MonthlyReturnCell, ...]) -> HistogramReadyArray:
    return HistogramReadyArray(
        name="monthly_return_distribution",
        unit_kind=UnitKind.DIMENSIONLESS_RATIO,
        values=tuple(cell.value for cell in cells),
    )


def _trade_distribution(trades: tuple[ClosedTrade, ...]) -> HistogramReadyArray:
    ordered = tuple(sorted(trades, key=lambda item: item.closed_at.value_ns))
    return HistogramReadyArray(
        name="trade_pnl_distribution",
        unit_kind=UnitKind.MONEY,
        values=tuple(item.realized_pnl for item in ordered),
    )


def _benchmark_identity(
    benchmark: object,
) -> tuple[Result[str | None], list[OmittedSeries] | None]:
    if benchmark is None:
        notes = [
            OmittedSeries(name=name, reason=NO_BENCHMARK_DECLARED)
            for name in BENCHMARK_RELATIVE_NAMES
        ]
        empty: str | None = None
        return Ok(empty), notes
    if isinstance(benchmark, str):
        token = clean_token(benchmark)
        if token is None:
            return (
                invalid(
                    BENCHMARK_KEY,
                    "a declared benchmark identity is a non-empty token recorded in the artifact",
                    given=repr(benchmark),
                ),
                None,
            )
        found: str | None = token
        return Ok(found), None
    if isinstance(benchmark, Mapping):
        body = cast("Mapping[str, object]", benchmark)
        banned = _banned_keys(body)
        if is_refusal(banned):
            return banned, None
        raw = body.get("identity", body.get("instrument", body.get("name")))
        token = clean_token(raw)
        if token is None:
            return (
                invalid(
                    BENCHMARK_KEY,
                    "a declared benchmark identity is recorded in the artifact",
                    given=repr(raw),
                ),
                None,
            )
        mapped: str | None = token
        return Ok(mapped), None
    return (
        invalid(
            BENCHMARK_KEY,
            "a Book/BMS benchmark is a token or a mapping carrying identity, never a faked series",
            given=repr(type(benchmark).__name__),
        ),
        None,
    )


def _benchmark_series(
    curve: object, start: Money, period: Interval
) -> Result[tuple[ChartSeries, ...]]:
    points = _as_equity_points(curve)
    if is_refusal(points):
        return points
    if not points.value:
        return Ok(())
    path = _equity_path(start, period, (), points.value)
    if is_refusal(path):
        return path
    start_frac = start.as_fraction()
    if start_frac == 0:
        return Ok(())
    cum_points: list[SeriesPoint] = []
    for item in path.value:
        cum = _ratio((item.equity.as_fraction() / start_frac) - 1)
        if is_refusal(cum):
            return cum
        minted = SeriesPoint.try_create(item.at, cum.value)
        if is_refusal(minted):
            return minted
        cum_points.append(minted.value)
    series = ChartSeries.try_create(
        "cumulative_returns_benchmark", UnitKind.DIMENSIONLESS_RATIO, tuple(cum_points)
    )
    if is_refusal(series):
        return series
    return Ok((series.value,))


def _holdings_family(
    marks: tuple[HoldingMark, ...],
    path: tuple[EquityPoint, ...],
    instruments: tuple[str, ...],
    *,
    leveraged: bool,
) -> tuple[Result[tuple[ChartSeries, ...]], list[OmittedSeries]]:
    held_instruments = tuple(dict.fromkeys(item.instrument for item in marks))
    universe = tuple(dict.fromkeys((*instruments, *held_instruments)))
    inferred = _infer_leveraged(marks, path)
    multi = len(universe) > 1
    emit = multi or leveraged or inferred
    if not emit:
        notes = [
            OmittedSeries(name=name, reason=OMIT_SINGLE_UNLEVERAGED) for name in HOLDINGS_FAMILY
        ]
        return Ok(()), notes
    if not marks:
        notes = [
            OmittedSeries(name=name, reason=OMIT_NO_POSITION_STREAM) for name in HOLDINGS_FAMILY
        ]
        return Ok(()), notes
    built = _reconstruct_holdings(marks, path, universe, emit_leverage=leveraged or inferred)
    if is_refusal(built):
        return built, []
    return built, []


def _infer_leveraged(marks: tuple[HoldingMark, ...], path: tuple[EquityPoint, ...]) -> bool:
    grouped = _group_holdings(marks)
    for at, rows in grouped.items():
        equity = _equity_at(path, at)
        if equity is None or equity.as_fraction() == 0:
            continue
        gross = sum((item.notional.as_fraction() for item in rows), Fraction(0))
        if gross > abs(equity.as_fraction()):
            return True
    return False


def _reconstruct_holdings(
    marks: tuple[HoldingMark, ...],
    path: tuple[EquityPoint, ...],
    universe: tuple[str, ...],
    *,
    emit_leverage: bool,
) -> Result[tuple[ChartSeries, ...]]:
    grouped = _group_holdings(marks)
    holding_pts: dict[str, list[SeriesPoint]] = {name: [] for name in universe}
    exposure_pts: dict[str, list[SeriesPoint]] = {name: [] for name in universe}
    allocation_pts: dict[str, list[SeriesPoint]] = {name: [] for name in universe}
    leverage_pts: list[SeriesPoint] = []
    for at in sorted(grouped, key=lambda instant: instant.value_ns):
        rows = grouped[at]
        by_name = {item.instrument: item for item in rows}
        equity = _equity_at(path, at)
        gross = sum((item.notional.as_fraction() for item in rows), Fraction(0))
        for name in universe:
            item = by_name.get(name)
            qty = _signed_quantity(item) if item is not None else _zero_quantity()
            if is_refusal(qty):
                return qty
            qty_pt = SeriesPoint.try_create(at, qty.value)
            if is_refusal(qty_pt):
                return qty_pt
            holding_pts[name].append(qty_pt.value)
            value = _zero_money(marks[0].market_value) if item is None else item.market_value
            exp_pt = SeriesPoint.try_create(at, value)
            if is_refusal(exp_pt):
                return exp_pt
            exposure_pts[name].append(exp_pt.value)
            if equity is not None and equity.as_fraction() != 0:
                alloc = _ratio(value.as_fraction() / equity.as_fraction())
                if is_refusal(alloc):
                    return alloc
                alloc_pt = SeriesPoint.try_create(at, alloc.value)
                if is_refusal(alloc_pt):
                    return alloc_pt
                allocation_pts[name].append(alloc_pt.value)
        if emit_leverage and equity is not None and equity.as_fraction() != 0:
            lev = _ratio(gross / abs(equity.as_fraction()))
            if is_refusal(lev):
                return lev
            lev_pt = SeriesPoint.try_create(at, lev.value)
            if is_refusal(lev_pt):
                return lev_pt
            leverage_pts.append(lev_pt.value)
    series: list[ChartSeries] = []
    for name in universe:
        holdings = ChartSeries.try_create(
            f"holdings.{name}", UnitKind.QUANTITY, tuple(holding_pts[name])
        )
        if is_refusal(holdings):
            return holdings
        series.append(holdings.value)
        exposure = ChartSeries.try_create(
            f"exposure.{name}", UnitKind.MONEY, tuple(exposure_pts[name])
        )
        if is_refusal(exposure):
            return exposure
        series.append(exposure.value)
        if allocation_pts[name]:
            allocation = ChartSeries.try_create(
                f"allocation.{name}",
                UnitKind.DIMENSIONLESS_RATIO,
                tuple(allocation_pts[name]),
            )
            if is_refusal(allocation):
                return allocation
            series.append(allocation.value)
    if leverage_pts:
        leverage = ChartSeries.try_create(
            "leverage", UnitKind.DIMENSIONLESS_RATIO, tuple(leverage_pts)
        )
        if is_refusal(leverage):
            return leverage
        series.append(leverage.value)
    return Ok(tuple(series))


def _group_holdings(marks: tuple[HoldingMark, ...]) -> dict[Instant, tuple[HoldingMark, ...]]:
    grouped: dict[int, list[HoldingMark]] = {}
    instants: dict[int, Instant] = {}
    for mark in marks:
        key = mark.at.value_ns
        grouped.setdefault(key, []).append(mark)
        instants[key] = mark.at
    return {instants[key]: tuple(grouped[key]) for key in sorted(grouped)}


def _signed_quantity(mark: HoldingMark) -> Result[ExactRational]:
    frac = mark.quantity.as_fraction()
    if mark.direction is Direction.SHORT:
        frac = -frac
    return ExactRational.try_create(frac.numerator, frac.denominator, UnitKind.QUANTITY)


def _zero_quantity() -> Result[ExactRational]:
    return ExactRational.try_create(0, 1, UnitKind.QUANTITY)


def _zero_money(template: Money) -> Money:
    minted = Money.try_create(0, template.currency, template.scale)
    if is_refusal(minted):
        return template
    return minted.value


def _equity_at(path: tuple[EquityPoint, ...], at: Instant) -> Money | None:
    found: Money | None = None
    for point in path:
        if point.at.value_ns > at.value_ns:
            break
        found = point.equity
    return found


def _stride_points(points: tuple[SeriesPoint, ...], stride: int) -> tuple[SeriesPoint, ...]:
    if len(points) <= 2 or stride == 1:
        return points
    kept: list[SeriesPoint] = [points[0]]
    last_index = len(points) - 1
    for index in range(1, last_index):
        if index % stride == 0:
            kept.append(points[index])
    if kept[-1] is not points[-1]:
        kept.append(points[-1])
    return tuple(kept)


def _equity_path(
    start: Money,
    period: Interval,
    trades: tuple[ClosedTrade, ...],
    curve: tuple[EquityPoint, ...],
) -> Result[tuple[EquityPoint, ...]]:
    if curve:
        ordered = tuple(sorted(curve, key=lambda item: item.at.value_ns))
        if ordered[0].at.value_ns > period.start.value_ns:
            head = EquityPoint.try_create(period.start, start)
            if is_refusal(head):
                return head
            ordered = (head.value, *ordered)
        return Ok(ordered)
    running = start
    built: list[EquityPoint] = []
    opened = EquityPoint.try_create(period.start, running)
    if is_refusal(opened):
        return opened
    built.append(opened.value)
    for trade in trades:
        added = running.add(trade.realized_pnl)
        if is_refusal(added):
            return added
        running = added.value
        point = EquityPoint.try_create(trade.closed_at, running)
        if is_refusal(point):
            return point
        built.append(point.value)
    if built[-1].at.value_ns != period.end.value_ns:
        closing = EquityPoint.try_create(period.end, running)
        if is_refusal(closing):
            return closing
        built.append(closing.value)
    return Ok(tuple(built))


def _resolve_trades(
    trades: object, events: tuple[JournalEvent, ...]
) -> Result[tuple[ClosedTrade, ...]]:
    parsed = _as_trades(trades)
    if is_refusal(parsed):
        return parsed
    if parsed.value:
        return parsed
    return _trades_from_journal(events)


def _trades_from_journal(events: tuple[JournalEvent, ...]) -> Result[tuple[ClosedTrade, ...]]:
    out: list[ClosedTrade] = []
    for event in events:
        if event.event_type is not JournalEventType.FILL:
            continue
        if "realized_pnl" not in event.payload:
            continue
        minted = ClosedTrade.try_create(
            event.payload.get("realized_pnl"),
            event.payload.get("fees"),
            event.payload.get("side"),
            event.instant,
        )
        if is_refusal(minted):
            return minted
        out.append(minted.value)
    return Ok(tuple(sorted(out, key=lambda item: item.closed_at.value_ns)))


def _as_trades(value: object) -> Result[tuple[ClosedTrade, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, ClosedTrade):
        return Ok((value,))
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "trades",
            "chart series derive from the run's ordered ClosedTrade record, never a parallel log "
            "or an image (R-RPT-14)",
            given=repr(type(value).__name__),
        )
    out: list[ClosedTrade] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if isinstance(item, ClosedTrade):
            out.append(item)
            continue
        if not isinstance(item, Mapping):
            return invalid(
                "trades",
                "chart series derive from the run's ordered ClosedTrade record, "
                "never a parallel log (R-RPT-14)",
                index=index,
                given=repr(type(item).__name__),
            )
        body = cast("Mapping[str, object]", item)
        banned = _banned_keys(body)
        if is_refusal(banned):
            return banned
        minted = ClosedTrade.try_create(
            body.get("realized_pnl"),
            body.get("fees"),
            body.get("side"),
            body.get("closed_at"),
        )
        if is_refusal(minted):
            return minted
        out.append(minted.value)
    return Ok(tuple(out))


def _as_equity_points(value: object) -> Result[tuple[EquityPoint, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, EquityPoint):
        return Ok((value,))
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "equity_curve",
            "the equity path is the run's ordered EquityPoint record; no image, base64, or PNG "
            "is ever the canonical payload (R-RPT-11)",
            given=repr(type(value).__name__),
        )
    out: list[EquityPoint] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if isinstance(item, EquityPoint):
            out.append(item)
            continue
        if not isinstance(item, Mapping):
            return invalid(
                "equity_curve",
                "every equity point is an EquityPoint or a mapping of at, equity; never an image",
                index=index,
                given=repr(type(item).__name__),
            )
        body = cast("Mapping[str, object]", item)
        banned = _banned_keys(body)
        if is_refusal(banned):
            return banned
        minted = EquityPoint.try_create(body.get("at"), body.get("equity"))
        if is_refusal(minted):
            return minted
        out.append(minted.value)
    return Ok(tuple(out))


def _as_holdings(value: object) -> Result[tuple[HoldingMark, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, HoldingMark):
        return Ok((value,))
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "holdings",
            "holdings reconstruct from the run's ordered position stream, never a parallel log "
            "or an image (R-RPT-14)",
            given=repr(type(value).__name__),
        )
    out: list[HoldingMark] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if isinstance(item, HoldingMark):
            out.append(item)
            continue
        if not isinstance(item, Mapping):
            return invalid(
                "holdings",
                "every holding mark is a HoldingMark or a mapping of the position stream",
                index=index,
                given=repr(type(item).__name__),
            )
        body = cast("Mapping[str, object]", item)
        banned = _banned_keys(body)
        if is_refusal(banned):
            return banned
        minted = HoldingMark.try_create(
            body.get("at"),
            body.get("instrument"),
            body.get("quantity"),
            body.get("direction"),
            body.get("market_value"),
            body.get("notional"),
        )
        if is_refusal(minted):
            return minted
        out.append(minted.value)
    return Ok(tuple(out))


def _as_journal_events(value: object) -> Result[tuple[JournalEvent, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, JournalEvent):
        return Ok((value,))
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(
            "journal_events",
            "chart series derive only from the run's CT-13 journal streams, never a parallel "
            "bespoke log (R-RPT-14)",
            given=repr(type(value).__name__),
        )
    items = cast("Sequence[object]", value)
    if not items:
        return Ok(())
    out: list[JournalEvent] = []
    for index, item in enumerate(items):
        if isinstance(item, JournalEvent):
            out.append(item)
            continue
        return invalid(
            "journal_events",
            "chart series derive only from the run's CT-13 journal streams, never a parallel "
            "bespoke log (R-RPT-14)",
            index=index,
            given=repr(type(item).__name__),
        )
    return Ok(tuple(out))


def _as_instruments(value: object) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "instruments",
            "instruments are the run's ordered instrument tokens",
            given=repr(type(value).__name__),
        )
    tokens: list[str] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        token = clean_token(item)
        if token is None:
            return invalid(
                "instruments",
                "every instrument token is a non-empty string",
                index=index,
                given=repr(item),
            )
        if token not in tokens:
            tokens.append(token)
    return Ok(tuple(tokens))


def _as_points(value: object, unit_kind: UnitKind) -> Result[tuple[SeriesPoint, ...]]:
    if isinstance(value, SeriesPoint):
        if value.v.unit_kind is not unit_kind:
            return invalid(
                "unit_kind",
                "every point's value must carry the series unit-kind",
                declared=unit_kind.value,
                quantity=value.v.unit_kind.value,
            )
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "points",
            "a chart series is an ordered sequence of {t, v} points",
            given=repr(type(value).__name__),
        )
    out: list[SeriesPoint] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, SeriesPoint):
            return invalid(
                "points",
                "every chart point is a SeriesPoint {t, v}",
                index=index,
                given=repr(type(item).__name__),
            )
        if item.v.unit_kind is not unit_kind:
            return invalid(
                "unit_kind",
                "every point's value must carry the series unit-kind",
                index=index,
                declared=unit_kind.value,
                quantity=item.v.unit_kind.value,
            )
        out.append(item)
    return Ok(tuple(out))


def _as_direction(value: object) -> Result[Direction]:
    if isinstance(value, Direction):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(Direction(value))
        except ValueError:
            pass
    return invalid(
        "direction",
        "a holding direction is long or short",
        given=repr(value),
        allowed=[member.value for member in Direction],
    )


def _as_unit_kind(value: object) -> Result[UnitKind]:
    if isinstance(value, UnitKind):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(UnitKind(value))
        except ValueError:
            pass
    return invalid(
        "unit_kind",
        "not a member of the closed AD-40 unit-kind vocabulary; a null unit-kind "
        "is a typed refusal, never a default",
        given=repr(value),
        allowed=[member.value for member in UnitKind],
    )


def _as_notional(market_value: Money, notional: object) -> Result[Money]:
    if notional is None:
        minted = Money.try_create(
            abs(market_value.value), market_value.currency, market_value.scale
        )
        if is_refusal(minted):
            return minted
        return Ok(minted.value)
    if not isinstance(notional, Money):
        return invalid(
            "notional",
            "holding notional is exact Money, never a binary float",
            given=repr(type(notional).__name__),
        )
    if notional.currency != market_value.currency:
        return invalid(
            "notional",
            "holding notional shares the market-value currency",
            given=notional.currency,
            expected=market_value.currency,
        )
    if notional.as_fraction() < 0:
        return invalid(
            "notional",
            "gross notional is non-negative; side is direction",
            given=str(notional.as_fraction()),
        )
    return Ok(notional)


def _currency_guard(
    start: Money,
    trades: tuple[ClosedTrade, ...],
    curve: tuple[EquityPoint, ...],
    marks: tuple[HoldingMark, ...],
) -> Result[None]:
    for index, trade in enumerate(trades):
        if trade.realized_pnl.currency != start.currency:
            return invalid(
                "trades",
                "every trade is denominated in the starting-capital currency",
                index=index,
                given=trade.realized_pnl.currency,
                expected=start.currency,
            )
    for index, point in enumerate(curve):
        if point.equity.currency != start.currency:
            return invalid(
                "equity_curve",
                "every equity point is denominated in the starting-capital currency",
                index=index,
                given=point.equity.currency,
                expected=start.currency,
            )
    for index, mark in enumerate(marks):
        if mark.market_value.currency != start.currency:
            return invalid(
                "holdings",
                "every holding mark is denominated in the starting-capital currency",
                index=index,
                given=mark.market_value.currency,
                expected=start.currency,
            )
    return Ok(None)


def _banned_keys(body: Mapping[str, object]) -> Result[None]:
    present = sorted(key for key in body if key in BANNED_RENDERER_KEYS)
    if present:
        return invalid(
            "renderer",
            "no color, style, or histogram bin is embedded in chart data — those are "
            "renderer concerns (R-RPT-12)",
            keys=present,
        )
    return Ok(None)


def _refuse_image_payload(field: str, value: object) -> Result[None]:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return invalid(
            field,
            "no image, base64, or PNG is ever the canonical payload (R-RPT-11, B-10)",
            given="binary-image-payload",
        )
    if isinstance(value, str) and (
        value.startswith("data:image") or value.startswith("iVBOR") or value.endswith(".png")
    ):
        return invalid(
            field,
            "no image, base64, or PNG is ever the canonical payload (R-RPT-11, B-10)",
        )
    return Ok(None)


def _ratio(value: Fraction) -> Result[ExactRational]:
    return ExactRational.try_create(
        value.numerator, value.denominator, UnitKind.DIMENSIONLESS_RATIO
    )


def _utc_year_month(instant: Instant) -> tuple[int, int]:
    seconds, _nanos = divmod(instant.value_ns, _NS_PER_SECOND)
    moment = _EPOCH_UTC + timedelta(seconds=seconds)
    return moment.year, moment.month
