"""Shared builders and the CT-04 refusal harness for the Epic 23 (qmb-synthetic-data)
independent QA suite.

Every assertion in this suite states what a *requirement* of Epic 23 demands (the
B-7 spine rule, L20, AR-33, the synthetic-data spec R1-R8, the CT-* contracts, the
constitution), never what the source happens to do. A failing test is a FINDING;
source is read-only evidence and is never edited to make a test pass, and no
assertion is weakened to pass. Builders below construct only shape-faithful,
exact-integer inputs (scaled-integer OHLC rows, UTC-ns grids) — no product mock
market data, no default strategies.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from qmf.core.chrono import Instant, SessionWindow
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

# The worktree root (this file is at <root>/qa/tests/epic_23/conftest.py).
WORKTREE_ROOT = Path(__file__).resolve().parents[3]

# A realistic UTC-ns epoch base (~2020-09) and a one-day step.
DAY_NS = 86_400 * 10**9
BASE_NS = 1_600_000_000 * 10**9

# The seven CT-04 refusal categories (from the ratified enum, never restated as prose).
SEVEN_CATEGORIES = frozenset(RefusalCategory)


# --- resource builders (resolved-generator-config door bodies) ---------------


def source_rows(n: int = 12, *, scale: int = 5, base: int = 120_000, step: int = 10) -> list[dict]:
    """``n`` shape-faithful scaled-integer OHLC rows at ``scale`` — a CT-10 source series.

    Strictly-positive, high/low-bounded bars on integers; the seed substrate for the
    history-seeded processes and the scenario-0 anchor.
    """
    rows: list[dict] = []
    for i in range(n):
        o = base + i * step
        c = o + 5
        h = max(o, c) + 8
        low = min(o, c) - 8
        rows.append(
            {
                "instant_ns": BASE_NS + i * DAY_NS,
                "open": o,
                "high": h,
                "low": low,
                "close": c,
                "scale": scale,
            }
        )
    return rows


def _base_resources(process: str, *, count: int, **over: object) -> dict:
    res: dict = {
        "process": process,
        "venue": "SIM",
        "symbol": "EURUSD",
        "scale": 5,
        "tick_size": 1,
        "resolution": "1d",
        "bar_step_ns": DAY_NS,
        "start_ns": BASE_NS,
        "end_ns": BASE_NS + count * DAY_NS,
        "calendar_rule_set": "always-open",
        "seed": 7,
        "scenario_count": 1,
        "claim_class": "infra-stress",
    }
    res.update(over)
    return res


def bb_resources(*, count: int = 5, block_length: int = 3, **over: object) -> dict:
    """A resolved ``block-bootstrap`` door body citing a source dataset (history-seeded)."""
    res = _base_resources("block-bootstrap", count=count, **over)
    res.setdefault("source_dataset_id", "SIM:EURUSD:1d:mid")
    res.setdefault("process_params", {"block_length": block_length})
    return res


def gn_resources(*, count: int = 5, sigma: str = "0.5", **over: object) -> dict:
    """A resolved ``gaussian-noise`` door body (history-seeded, explicit sigma)."""
    res = _base_resources("gaussian-noise", count=count, **over)
    res.setdefault("source_dataset_id", "SIM:EURUSD:1d:mid")
    res.setdefault("process_params", {"sigma": sigma})
    return res


def gr_resources(*, count: int = 5, **over: object) -> dict:
    """A resolved ``gaussian-resample`` door body (history-seeded, data-derived sigma)."""
    res = _base_resources("gaussian-resample", count=count, **over)
    res.setdefault("source_dataset_id", "SIM:EURUSD:1d:mid")
    res.setdefault("process_params", {})
    return res


def gbm_resources(*, count: int = 5, seed_price: int = 120_000, volatility: str = "0.01", **over: object) -> dict:
    """A resolved from-scratch ``gbm`` door body (no source dataset required).

    ``process`` may be overridden (e.g. to exercise an unknown/deferred process for a
    refusal test); the gbm process-params default is applied only for the gbm process.
    """
    process = over.pop("process", "gbm")
    res = _base_resources(str(process), count=count, **over)
    if process == "gbm":
        res.setdefault("process_params", {"seed_price": seed_price, "volatility": volatility})
    return res


# --- an injectable market-hours calendar with a weekend gap (T23-303) ---------


class GappedCalendar:
    """A minimal injectable CT-02 market-hours calendar with a weekend gap.

    ``sessions`` is a list of ``(open_ns, close_ns)`` open spans; an instant outside
    every span is closed (``Ok(None)``). Not ``always_open`` — the grid builder must
    honor the gap. Used to assert the synthetic grid excludes closed spans (R6).
    """

    def __init__(self, sessions: list[tuple[int, int]]) -> None:
        self.sessions = sessions

    def session_window(self, instant: object) -> Result[SessionWindow | None]:
        ns = getattr(instant, "value_ns", None)
        if ns is None:  # pragma: no cover - defensive
            return Ok(None)
        for open_ns, close_ns in self.sessions:
            if open_ns <= ns < close_ns:
                oi = Instant.try_create(open_ns)
                ci = Instant.try_create(close_ns)
                if is_refusal(oi):
                    return oi
                if is_refusal(ci):
                    return ci
                return SessionWindow.try_create(oi.value, ci.value, "UTC")
        return Ok(None)


# --- CT-04 refusal harness ---------------------------------------------------


def assert_ct04_refusal(
    result: object,
    expected: RefusalCategory,
    *,
    what: str = "operation",
) -> TypedRefusal:
    """Assert ``result`` is a RETURNED CT-04 typed refusal of ``expected`` category.

    Checks the four things the CT-04 contract pins for a refusal value: it is a
    ``TypedRefusal`` RETURNED (not raised), its ``category`` is one of the seven and is
    the expected one, its ``retryability`` is a valid enum member, and its ``context``
    is present and non-null. No assertion ever parses the refusal's prose.
    """
    assert is_refusal(result), f"{what}: expected a RETURNED CT-04 refusal, got {result!r}"
    refusal = result
    assert isinstance(refusal, TypedRefusal)
    assert isinstance(refusal.category, RefusalCategory)
    assert refusal.category in SEVEN_CATEGORIES
    assert refusal.category is expected, (
        f"{what}: expected category {expected.value!r}, got {refusal.category.value!r}"
    )
    assert isinstance(refusal.retryability, Retryability)
    assert isinstance(refusal.context, Mapping)
    assert refusal.context is not None
    return refusal


def unwrap(result: Result, what: str = "value"):
    """Unwrap an ``Ok`` or fail loudly — used only to build *inputs*, never to assert."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got refusal: {result!r}")


__all__ = [
    "BASE_NS",
    "DAY_NS",
    "SEVEN_CATEGORIES",
    "WORKTREE_ROOT",
    "GappedCalendar",
    "Ok",
    "RefusalCategory",
    "Result",
    "Retryability",
    "TypedRefusal",
    "assert_ct04_refusal",
    "bb_resources",
    "gbm_resources",
    "gn_resources",
    "gr_resources",
    "is_ok",
    "is_refusal",
    "source_rows",
    "unwrap",
]
