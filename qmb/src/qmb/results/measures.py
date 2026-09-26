"""V1 core CT-32 measure set — ordered, unit-kinded, exact (Story 19.2).

Each member carries a non-null AD-40 unit-kind. Money is exact scaled integers;
durations are int64 UTC-ns stored as exact rationals of unit-kind ``duration``.
Each metric's arithmetic is pinned by its own ``metric_contract_format_version``.
Undefined / insufficient-sample is a typed refusal a reader can tell apart from
zero — never a magic cap of 10, never NaN coerced to 0. No composite score.
Measurement publishes, never acts.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant, Interval
from qmf.core.exact import ExactRational, Money, RoundingMode, UnitKind
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.performance import PerformanceMeasure, UndefinedMeasure

from qmb._refuse import invalid, unavailable

__all__ = [
    "ANNUALIZATION_PERIODS",
    "CODE_INSUFFICIENT_SAMPLE",
    "CODE_UNDEFINED",
    "MEASURE_ARITHMETIC",
    "MEASURE_CONTRACT_FORMAT_VERSION",
    "MEASURE_IDENTITIES",
    "METRIC_CONTRACT_FORMAT_VERSIONS",
    "NS_PER_DAY",
    "RATIO_DDOF",
    "RATIO_SCALE",
    "ClosedTrade",
    "EquityPoint",
    "TradeSide",
    "assemble_v1_measure_set",
    "emit_measure",
]

MEASURE_CONTRACT_FORMAT_VERSION: Final[int] = 1
NS_PER_DAY: Final[int] = 24 * 60 * 60 * 1_000_000_000
ANNUALIZATION_PERIODS: Final[int] = 365
CALENDAR_YEAR_NS: Final[int] = ANNUALIZATION_PERIODS * NS_PER_DAY
RATIO_SCALE: Final[int] = 12
RATIO_DDOF: Final[int] = 1
MIN_RATIO_SAMPLES: Final[int] = 2
CODE_UNDEFINED: Final[str] = "undefined"
CODE_INSUFFICIENT_SAMPLE: Final[str] = "insufficient-sample"
RF_MODEL: Final[str] = "zero"
_UNSET: Final[object] = object()

MEASURE_IDENTITIES: Final[tuple[str, ...]] = (
    "net_profit",
    "net_profit_ratio",
    "cagr",
    "start_equity",
    "end_equity",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "max_drawdown",
    "max_drawdown_recovery",
    "total_trades",
    "winning_trades",
    "losing_trades",
    "win_rate",
    "long_win_rate",
    "short_win_rate",
    "profit_factor",
    "expectancy",
    "average_win",
    "average_loss",
    "largest_win",
    "largest_loss",
    "gross_profit",
    "gross_loss",
    "fees",
    "winning_streak",
    "losing_streak",
)

METRIC_CONTRACT_FORMAT_VERSIONS: Final[Mapping[str, int]] = MappingProxyType(
    dict.fromkeys(MEASURE_IDENTITIES, MEASURE_CONTRACT_FORMAT_VERSION)
)

MEASURE_ARITHMETIC: Final[Mapping[str, object]] = MappingProxyType(
    {
        "annualization_periods": ANNUALIZATION_PERIODS,
        "calendar_year_ns": CALENDAR_YEAR_NS,
        "ddof": RATIO_DDOF,
        "min_ratio_samples": MIN_RATIO_SAMPLES,
        "ratio_scale": RATIO_SCALE,
        "rf_model": RF_MODEL,
        "rounding": RoundingMode.HALF_EVEN.value,
    }
)

MeasureSlot = PerformanceMeasure | UndefinedMeasure


class TradeSide(StrEnum):
    """Long/short split for win-rate members (R-RPT-3)."""

    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True, slots=True)
class ClosedTrade:
    """One closed trade feeding the V1 core measure set.

    ``realized_pnl`` is net of this trade's ``fees``. Side is explicit because
    CT-29 exit records do not carry a long/short tag of their own.
    """

    realized_pnl: Money
    fees: Money
    side: TradeSide
    closed_at: Instant

    @classmethod
    def try_create(
        cls, realized_pnl: object, fees: object, side: object, closed_at: object
    ) -> Result[ClosedTrade]:
        """Validate and build a :class:`ClosedTrade`, value-or-refusal."""
        if not isinstance(realized_pnl, Money):
            return invalid(
                "realized_pnl",
                "a closed trade's realized P&L is exact Money, never a float",
                given=repr(type(realized_pnl).__name__),
            )
        if not isinstance(fees, Money):
            return invalid(
                "fees",
                "a closed trade's fees are exact Money, never a float",
                given=repr(type(fees).__name__),
            )
        if fees.currency != realized_pnl.currency:
            return invalid(
                "fees",
                "trade fees must share the realized P&L currency; there is no silent conversion",
                fees=fees.currency,
                realized_pnl=realized_pnl.currency,
            )
        resolved_side = _as_side(side)
        if is_refusal(resolved_side):
            return resolved_side
        if not isinstance(closed_at, Instant):
            return invalid(
                "closed_at",
                "a closed trade is timestamped with an Instant (int64 UTC-ns)",
                given=repr(type(closed_at).__name__),
            )
        return Ok(
            cls(
                realized_pnl=realized_pnl,
                fees=fees,
                side=resolved_side.value,
                closed_at=closed_at,
            )
        )


@dataclass(frozen=True, slots=True)
class EquityPoint:
    """One equity observation on the run path (exact Money at an Instant)."""

    at: Instant
    equity: Money

    @classmethod
    def try_create(cls, at: object, equity: object) -> Result[EquityPoint]:
        """Validate and build an :class:`EquityPoint`, value-or-refusal."""
        if not isinstance(at, Instant):
            return invalid(
                "at",
                "an equity point is timestamped with an Instant (int64 UTC-ns)",
                given=repr(type(at).__name__),
            )
        if not isinstance(equity, Money):
            return invalid(
                "equity",
                "equity is exact Money at the declared currency scale, never a float",
                given=repr(type(equity).__name__),
            )
        return Ok(cls(at=at, equity=equity))


@dataclass(frozen=True, slots=True)
class _Computed:
    start: Money
    end: Money
    net: Money
    fees: Money
    gross_profit: Money
    gross_loss: Money
    trades: tuple[ClosedTrade, ...]
    wins: tuple[ClosedTrade, ...]
    losses: tuple[ClosedTrade, ...]
    long_trades: tuple[ClosedTrade, ...]
    short_trades: tuple[ClosedTrade, ...]
    long_wins: tuple[ClosedTrade, ...]
    short_wins: tuple[ClosedTrade, ...]
    daily: tuple[EquityPoint, ...]
    period: Interval
    max_dd: Fraction | None
    recovery_ns: int
    winning_streak: int
    losing_streak: int


def emit_measure(
    measure_identity: object,
    quantity: object,
    metric_contract_format_version: object = MEASURE_CONTRACT_FORMAT_VERSION,
    *,
    unit_kind: object = _UNSET,
) -> Result[PerformanceMeasure]:
    """Emit one computed measure. A null unit-kind is invalid input, never defaulted."""
    if unit_kind is None:
        return invalid(
            "unit_kind",
            "a null unit-kind is a typed refusal, never a default (R-RPT-3, DEC-0154)",
        )
    if quantity is None:
        return invalid(
            "quantity",
            "every emitted quantity carries a non-null unit-kind from the closed "
            "AD-40 vocabulary; a null quantity is invalid input, never defaulted",
        )
    if unit_kind is not _UNSET:
        resolved = _as_unit_kind(unit_kind)
        if is_refusal(resolved):
            return resolved
        if (
            isinstance(quantity, (ExactRational, Money))
            and quantity.unit_kind is not resolved.value
        ):
            return invalid(
                "unit_kind",
                "the declared unit-kind must match the quantity's AD-40 unit-kind",
                declared=resolved.value.value,
                quantity=quantity.unit_kind.value,
            )
    return PerformanceMeasure.try_create(measure_identity, quantity, metric_contract_format_version)


def assemble_v1_measure_set(
    *,
    starting_capital: object,
    period: object,
    trades: object = (),
    equity_curve: object = (),
) -> Result[tuple[MeasureSlot, ...]]:
    """Assemble the ordered V1 core measure set (R-RPT-3..5, R-RPT-9, R-RPT-10).

    Undefined / insufficient-sample metrics occupy their ordered slot as
    :class:`UndefinedMeasure`. A null unit-kind fails the whole assembly as
    ``invalid input``. The set never includes a composite score, and producing
    it sizes, promotes, and benches nothing.
    """
    computed = _compute(
        starting_capital=starting_capital,
        period=period,
        trades=trades,
        equity_curve=equity_curve,
    )
    if is_refusal(computed):
        return computed
    book = computed.value
    ordered: list[MeasureSlot] = []
    for identity in MEASURE_IDENTITIES:
        slot = _emit_identity(identity, book)
        if is_refusal(slot):
            return slot
        ordered.append(slot.value)
    return Ok(tuple(ordered))


def _emit_identity(identity: str, book: _Computed) -> Result[MeasureSlot]:
    if identity == "net_profit":
        return _money_slot(identity, book.net)
    if identity == "net_profit_ratio":
        return _ratio_over(identity, book.net.as_fraction(), book.start.as_fraction())
    if identity == "cagr":
        return _cagr_slot(book)
    if identity == "start_equity":
        return _money_slot(identity, book.start)
    if identity == "end_equity":
        return _money_slot(identity, book.end)
    if identity == "sharpe_ratio":
        return _sharpe_slot(book)
    if identity == "sortino_ratio":
        return _sortino_slot(book)
    if identity == "calmar_ratio":
        return _calmar_slot(book)
    if identity == "max_drawdown":
        if book.max_dd is None:
            return _undefined(
                identity,
                CODE_UNDEFINED,
                "max drawdown is undefined when peak equity is zero and the path declines",
            )
        return _exact_ratio(identity, book.max_dd)
    if identity == "max_drawdown_recovery":
        return _duration_slot(identity, book.recovery_ns)
    if identity == "total_trades":
        return _count_slot(identity, len(book.trades))
    if identity == "winning_trades":
        return _count_slot(identity, len(book.wins))
    if identity == "losing_trades":
        return _count_slot(identity, len(book.losses))
    if identity == "win_rate":
        return _rate_slot(identity, len(book.wins), len(book.trades), "no closed trades")
    if identity == "long_win_rate":
        return _rate_slot(
            identity, len(book.long_wins), len(book.long_trades), "no closed long trades"
        )
    if identity == "short_win_rate":
        return _rate_slot(
            identity, len(book.short_wins), len(book.short_trades), "no closed short trades"
        )
    if identity == "profit_factor":
        return _profit_factor_slot(book)
    if identity == "expectancy":
        return _mean_money_slot(identity, tuple(item.realized_pnl for item in book.trades))
    if identity == "average_win":
        return _mean_money_slot(identity, tuple(item.realized_pnl for item in book.wins))
    if identity == "average_loss":
        return _mean_money_slot(identity, tuple(item.realized_pnl for item in book.losses))
    if identity == "largest_win":
        return _extreme_slot(identity, book.wins, winning=True)
    if identity == "largest_loss":
        return _extreme_slot(identity, book.losses, winning=False)
    if identity == "gross_profit":
        return _money_slot(identity, book.gross_profit)
    if identity == "gross_loss":
        return _money_slot(identity, book.gross_loss)
    if identity == "fees":
        return _money_slot(identity, book.fees)
    if identity == "winning_streak":
        return _count_slot(identity, book.winning_streak)
    if identity == "losing_streak":
        return _count_slot(identity, book.losing_streak)
    return invalid(
        "measure_identity",
        "V1 core measure set identities are the pinned MEASURE_IDENTITIES roster",
        given=identity,
    )


def _compute(
    *,
    starting_capital: object,
    period: object,
    trades: object,
    equity_curve: object,
) -> Result[_Computed]:
    if not isinstance(starting_capital, Money):
        return invalid(
            "starting_capital",
            "start equity is exact Money at the declared currency scale, never a float",
            given=repr(type(starting_capital).__name__),
        )
    if not isinstance(period, Interval):
        return invalid(
            "period",
            "measure arithmetic reads the result period as an AD-8 Interval",
            given=repr(type(period).__name__),
        )
    closed = _as_trades(trades)
    if is_refusal(closed):
        return closed
    points = _as_equity_points(equity_curve)
    if is_refusal(points):
        return points
    ordered_trades = tuple(sorted(closed.value, key=lambda item: item.closed_at.value_ns))
    currency_ok = _currency_guard(starting_capital, ordered_trades, points.value)
    if is_refusal(currency_ok):
        return currency_ok
    path = _equity_path(starting_capital, period, ordered_trades, points.value)
    if is_refusal(path):
        return path
    end = path.value[-1].equity if path.value else starting_capital
    net = end.subtract(starting_capital)
    if is_refusal(net):
        return net
    fees = _sum_money(starting_capital, tuple(item.fees for item in ordered_trades))
    if is_refusal(fees):
        return fees
    wins = tuple(item for item in ordered_trades if item.realized_pnl.as_fraction() > 0)
    losses = tuple(item for item in ordered_trades if item.realized_pnl.as_fraction() < 0)
    gross_profit = _sum_money(starting_capital, tuple(item.realized_pnl for item in wins))
    if is_refusal(gross_profit):
        return gross_profit
    gross_loss = _sum_money(starting_capital, tuple(item.realized_pnl for item in losses))
    if is_refusal(gross_loss):
        return gross_loss
    longs = tuple(item for item in ordered_trades if item.side is TradeSide.LONG)
    shorts = tuple(item for item in ordered_trades if item.side is TradeSide.SHORT)
    drawdown = _drawdown(path.value, period)
    if is_refusal(drawdown):
        return drawdown
    max_dd, recovery_ns = drawdown.value
    win_streak, loss_streak = _streaks(ordered_trades)
    return Ok(
        _Computed(
            start=starting_capital,
            end=end,
            net=net.value,
            fees=fees.value,
            gross_profit=gross_profit.value,
            gross_loss=gross_loss.value,
            trades=ordered_trades,
            wins=wins,
            losses=losses,
            long_trades=longs,
            short_trades=shorts,
            long_wins=tuple(item for item in longs if item.realized_pnl.as_fraction() > 0),
            short_wins=tuple(item for item in shorts if item.realized_pnl.as_fraction() > 0),
            daily=_daily_equity(path.value),
            period=period,
            max_dd=max_dd,
            recovery_ns=recovery_ns,
            winning_streak=win_streak,
            losing_streak=loss_streak,
        )
    )


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


def _daily_equity(path: tuple[EquityPoint, ...]) -> tuple[EquityPoint, ...]:
    buckets: dict[int, EquityPoint] = {}
    for point in path:
        buckets[point.at.value_ns // NS_PER_DAY] = point
    return tuple(buckets[key] for key in sorted(buckets))


def _drawdown(
    path: tuple[EquityPoint, ...], period: Interval
) -> Result[tuple[Fraction | None, int]]:
    if not path:
        return Ok((Fraction(0), 0))
    peak = path[0].equity.as_fraction()
    max_dd = Fraction(0)
    trough_at = path[0].at
    recovered_at: Instant | None = path[0].at
    open_max = False
    for point in path[1:]:
        equity = point.equity.as_fraction()
        if equity >= peak:
            if open_max and recovered_at is None:
                recovered_at = point.at
            peak = equity
            open_max = False
            continue
        if peak == 0:
            return Ok((None, 0))
        drawdown = (peak - equity) / peak
        if drawdown > max_dd:
            max_dd = drawdown
            trough_at = point.at
            recovered_at = None
            open_max = True
        elif open_max and drawdown == max_dd:
            trough_at = point.at
    if max_dd == 0:
        return Ok((Fraction(0), 0))
    recovered = recovered_at if recovered_at is not None else period.end
    span = recovered.difference(trough_at)
    if is_refusal(span):
        return span
    return Ok((max_dd, span.value.value_ns))


def _streaks(trades: tuple[ClosedTrade, ...]) -> tuple[int, int]:
    win_run = 0
    loss_run = 0
    max_win = 0
    max_loss = 0
    for trade in trades:
        pnl = trade.realized_pnl.as_fraction()
        if pnl > 0:
            win_run += 1
            loss_run = 0
            max_win = max(max_win, win_run)
        elif pnl < 0:
            loss_run += 1
            win_run = 0
            max_loss = max(max_loss, loss_run)
        else:
            win_run = 0
            loss_run = 0
    return max_win, max_loss


def _cagr_slot(book: _Computed) -> Result[MeasureSlot]:
    start = book.start.as_fraction()
    if start <= 0:
        return _undefined(
            "cagr",
            CODE_UNDEFINED,
            "CAGR is undefined when start equity is zero or negative",
            start=str(start),
        )
    span_ns = book.period.end.value_ns - book.period.start.value_ns
    if span_ns <= 0:
        return _undefined(
            "cagr",
            CODE_UNDEFINED,
            "CAGR is undefined when the declared period has no positive duration",
            span_ns=span_ns,
        )
    growth = float(book.end.as_fraction() / start)
    years = span_ns / CALENDAR_YEAR_NS
    if years == 0:
        return _undefined(
            "cagr",
            CODE_UNDEFINED,
            "CAGR is undefined when the annualization year length is zero",
        )
    value = growth ** (1.0 / years) - 1.0
    return _float_ratio_slot("cagr", value)


def _sharpe_slot(book: _Computed) -> Result[MeasureSlot]:
    returns = _daily_returns(book.daily)
    if is_refusal(returns):
        return _undefined(
            "sharpe_ratio",
            CODE_UNDEFINED,
            str(returns.context.get("reason", "daily returns are undefined")),
        )
    series = returns.value
    if len(series) < MIN_RATIO_SAMPLES:
        return _undefined(
            "sharpe_ratio",
            CODE_INSUFFICIENT_SAMPLE,
            "Sharpe requires at least 2 daily return samples",
            given_samples=len(series),
            min_samples=MIN_RATIO_SAMPLES,
        )
    mean, std = _sample_moments(series, downside=False)
    if std == 0:
        return _undefined(
            "sharpe_ratio",
            CODE_UNDEFINED,
            "Sharpe is undefined when daily-return sample deviation is zero",
        )
    value = (mean / std) * math.sqrt(ANNUALIZATION_PERIODS)
    return _float_ratio_slot("sharpe_ratio", value)


def _sortino_slot(book: _Computed) -> Result[MeasureSlot]:
    returns = _daily_returns(book.daily)
    if is_refusal(returns):
        return _undefined(
            "sortino_ratio",
            CODE_UNDEFINED,
            str(returns.context.get("reason", "daily returns are undefined")),
        )
    series = returns.value
    if len(series) < MIN_RATIO_SAMPLES:
        return _undefined(
            "sortino_ratio",
            CODE_INSUFFICIENT_SAMPLE,
            "Sortino requires at least 2 daily return samples",
            given_samples=len(series),
            min_samples=MIN_RATIO_SAMPLES,
        )
    mean, down = _sample_moments(series, downside=True)
    if down == 0:
        return _undefined(
            "sortino_ratio",
            CODE_UNDEFINED,
            "Sortino is undefined when downside deviation is zero",
        )
    value = (mean / down) * math.sqrt(ANNUALIZATION_PERIODS)
    return _float_ratio_slot("sortino_ratio", value)


def _calmar_slot(book: _Computed) -> Result[MeasureSlot]:
    if book.max_dd is None or book.max_dd == 0:
        return _undefined(
            "calmar_ratio",
            CODE_UNDEFINED,
            "Calmar is CAGR / |max drawdown| and is undefined when max drawdown is zero",
        )
    cagr = _cagr_slot(book)
    if is_refusal(cagr):
        return cagr
    if isinstance(cagr.value, UndefinedMeasure):
        return _undefined(
            "calmar_ratio",
            CODE_UNDEFINED,
            "Calmar is undefined when CAGR is undefined",
        )
    quantity = cagr.value.quantity
    if not isinstance(quantity, ExactRational):
        return invalid(
            "calmar_ratio",
            "Calmar divides an exact CAGR ratio by max drawdown",
            given=repr(type(quantity).__name__),
        )
    ratio = quantity.as_fraction() / book.max_dd
    return _exact_ratio("calmar_ratio", ratio)


def _profit_factor_slot(book: _Computed) -> Result[MeasureSlot]:
    if not book.losses:
        return _undefined(
            "profit_factor",
            CODE_UNDEFINED,
            "profit factor is gross profit / |gross loss| and is undefined with no losing trades",
            losing_trades=0,
        )
    loss_mag = abs(book.gross_loss.as_fraction())
    ratio = book.gross_profit.as_fraction() / loss_mag
    return _exact_ratio("profit_factor", ratio)


def _daily_returns(daily: tuple[EquityPoint, ...]) -> Result[tuple[Fraction, ...]]:
    if len(daily) < 2:
        return Ok(())
    out: list[Fraction] = []
    for index in range(1, len(daily)):
        previous = daily[index - 1].equity.as_fraction()
        current = daily[index].equity.as_fraction()
        if previous == 0:
            if current == 0:
                out.append(Fraction(0))
                continue
            return unavailable(
                "daily_returns",
                "a daily return is undefined when the prior equity is zero",
                code=CODE_UNDEFINED,
            )
        out.append((current - previous) / previous)
    return Ok(tuple(out))


def _sample_moments(series: tuple[Fraction, ...], *, downside: bool) -> tuple[float, float]:
    count = len(series)
    mean = sum(series, Fraction(0)) / count
    if downside:
        acc = sum((min(item, Fraction(0)) ** 2) for item in series)
    else:
        acc = sum((item - mean) ** 2 for item in series)
    variance = acc / (count - RATIO_DDOF)
    return float(mean), math.sqrt(float(variance))


def _float_ratio_slot(identity: str, value: float) -> Result[MeasureSlot]:
    if not math.isfinite(value):
        return _undefined(
            identity,
            CODE_UNDEFINED,
            "NaN and infinity cannot express a ratio measure; never coerced to 0",
        )
    converted = ExactRational.from_float(
        value,
        unit_kind=UnitKind.DIMENSIONLESS_RATIO,
        scale=RATIO_SCALE,
        rounding=RoundingMode.HALF_EVEN,
    )
    if is_refusal(converted):
        return _undefined(
            identity,
            CODE_UNDEFINED,
            "the named ratio conversion refused this value; never coerced to 0",
        )
    return _computed(
        emit_measure(identity, converted.value, METRIC_CONTRACT_FORMAT_VERSIONS[identity])
    )


def _ratio_over(identity: str, numerator: Fraction, denominator: Fraction) -> Result[MeasureSlot]:
    if denominator == 0:
        return _undefined(
            identity,
            CODE_UNDEFINED,
            "a ratio over a zero denominator is undefined, never coerced to 0",
        )
    return _exact_ratio(identity, numerator / denominator)


def _exact_ratio(identity: str, value: Fraction) -> Result[MeasureSlot]:
    quantity = ExactRational.try_create(
        value.numerator, value.denominator, UnitKind.DIMENSIONLESS_RATIO
    )
    if is_refusal(quantity):
        return quantity
    return _computed(
        emit_measure(identity, quantity.value, METRIC_CONTRACT_FORMAT_VERSIONS[identity])
    )


def _money_slot(identity: str, amount: Money) -> Result[MeasureSlot]:
    return _computed(emit_measure(identity, amount, METRIC_CONTRACT_FORMAT_VERSIONS[identity]))


def _count_slot(identity: str, count: int) -> Result[MeasureSlot]:
    quantity = ExactRational.try_create(count, 1, UnitKind.COUNT)
    if is_refusal(quantity):
        return quantity
    return _computed(
        emit_measure(identity, quantity.value, METRIC_CONTRACT_FORMAT_VERSIONS[identity])
    )


def _duration_slot(identity: str, value_ns: int) -> Result[MeasureSlot]:
    quantity = ExactRational.try_create(value_ns, 1, UnitKind.DURATION)
    if is_refusal(quantity):
        return quantity
    return _computed(
        emit_measure(identity, quantity.value, METRIC_CONTRACT_FORMAT_VERSIONS[identity])
    )


def _computed(result: Result[PerformanceMeasure]) -> Result[MeasureSlot]:
    if is_refusal(result):
        return result
    slot: MeasureSlot = result.value
    return Ok(slot)


def _rate_slot(identity: str, hits: int, total: int, empty_reason: str) -> Result[MeasureSlot]:
    if total == 0:
        return _undefined(identity, CODE_UNDEFINED, empty_reason, sample_size=0)
    return _exact_ratio(identity, Fraction(hits, total))


def _mean_money_slot(identity: str, amounts: tuple[Money, ...]) -> Result[MeasureSlot]:
    if not amounts:
        return _undefined(
            identity,
            CODE_INSUFFICIENT_SAMPLE,
            "mean money is undefined with an empty sample, never coerced to 0",
            sample_size=0,
        )
    total = _sum_money(amounts[0], amounts)
    if is_refusal(total):
        return total
    rounded = _round_half_even(Fraction(total.value.value, len(amounts)))
    mean = Money.try_create(rounded, total.value.currency, total.value.scale)
    if is_refusal(mean):
        return mean
    return _money_slot(identity, mean.value)


def _extreme_slot(
    identity: str, trades: tuple[ClosedTrade, ...], *, winning: bool
) -> Result[MeasureSlot]:
    if not trades:
        which = "winning" if winning else "losing"
        return _undefined(
            identity,
            CODE_INSUFFICIENT_SAMPLE,
            f"{identity} is undefined with no {which} trades, never coerced to 0",
            sample_size=0,
        )
    chosen = trades[0].realized_pnl
    for item in trades[1:]:
        if winning and item.realized_pnl.as_fraction() > chosen.as_fraction():
            chosen = item.realized_pnl
        if not winning and item.realized_pnl.as_fraction() < chosen.as_fraction():
            chosen = item.realized_pnl
    return _money_slot(identity, chosen)


def _undefined(identity: str, code: str, reason: str, **extra: object) -> Result[MeasureSlot]:
    refusal = unavailable(
        identity,
        reason,
        code=code,
        metric_contract_format_version=METRIC_CONTRACT_FORMAT_VERSIONS[identity],
        **extra,
    )
    minted = UndefinedMeasure.try_create(
        identity, METRIC_CONTRACT_FORMAT_VERSIONS[identity], refusal
    )
    if is_refusal(minted):
        return minted
    found: MeasureSlot = minted.value
    return Ok(found)


def _sum_money(template: Money, amounts: tuple[Money, ...]) -> Result[Money]:
    total = Money.try_create(0, template.currency, template.scale)
    if is_refusal(total):
        return total
    running = total.value
    for item in amounts:
        added = running.add(item)
        if is_refusal(added):
            return added
        running = added.value
    return Ok(running)


def _currency_guard(
    start: Money, trades: tuple[ClosedTrade, ...], curve: tuple[EquityPoint, ...]
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
    return Ok(None)


def _as_trades(value: object) -> Result[tuple[ClosedTrade, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, ClosedTrade):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "trades",
            "the V1 measure set reads an ordered sequence of ClosedTrade values",
            given=repr(type(value).__name__),
        )
    out: list[ClosedTrade] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if isinstance(item, ClosedTrade):
            out.append(item)
            continue
        minted = _trade_from_mapping(item, index)
        if is_refusal(minted):
            return minted
        out.append(minted.value)
    return Ok(tuple(out))


def _trade_from_mapping(item: object, index: int) -> Result[ClosedTrade]:
    if not isinstance(item, Mapping):
        return invalid(
            "trades",
            "every trade is a ClosedTrade or a mapping of realized_pnl, fees, side, closed_at",
            index=index,
            given=repr(type(item).__name__),
        )
    body = cast("Mapping[str, object]", item)
    return ClosedTrade.try_create(
        body.get("realized_pnl"),
        body.get("fees"),
        body.get("side"),
        body.get("closed_at"),
    )


def _as_equity_points(value: object) -> Result[tuple[EquityPoint, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, EquityPoint):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "equity_curve",
            "the equity path is an ordered sequence of EquityPoint values",
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
                "every equity point is an EquityPoint or a mapping of at, equity",
                index=index,
                given=repr(type(item).__name__),
            )
        body = cast("Mapping[str, object]", item)
        minted = EquityPoint.try_create(body.get("at"), body.get("equity"))
        if is_refusal(minted):
            return minted
        out.append(minted.value)
    return Ok(tuple(out))


def _as_side(value: object) -> Result[TradeSide]:
    if isinstance(value, TradeSide):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(TradeSide(value))
        except ValueError:
            pass
    return invalid(
        "side",
        "a closed trade side is long or short",
        given=repr(value),
        allowed=[member.value for member in TradeSide],
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


def _round_half_even(value: Fraction) -> int:
    floor_value, remainder = divmod(value.numerator, value.denominator)
    if remainder == 0:
        return floor_value
    ceil_value = floor_value + 1
    twice = 2 * remainder
    if twice < value.denominator:
        return floor_value
    if twice > value.denominator:
        return ceil_value
    return floor_value if floor_value % 2 == 0 else ceil_value
