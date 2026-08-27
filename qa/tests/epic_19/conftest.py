"""Independent fixture builders for the Epic 19 (qmb-reports) audit.

Every builder here is owned by the TEST, not by the code under test. Fixtures are
shape-faithful to the ratified contracts (CT-32 / CT-13 / CT-04) because they are
constructed from the ratified qmf-core / qmf-data / qmf-risk value types directly
(Money, ExactRational, Instant, Interval, JournalEvent, ...). No source module
under ``qmb/src/qmb/results/`` is imported to build inputs — only to exercise it.

Discipline (HARDENED AUTHOR CONTRACT):
  * effects observed through the returned artifact, the on-disk canonical bytes,
    and returned typed refusals — never a self-declared flag as proof;
  * refusals are RETURNED CT-04 values, asserted by category + context field;
  * a value-or-refusal is unwrapped by ``ok()`` which fails loudly on a refusal.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

import pytest

from qmf.core.chrono import Instant, Interval, WriterId
from qmf.core.exact import Money, Quantity, UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Result, is_ok
from qmf.data.journal import DecisionOutcome, JournalEvent, JournalEventType

from qmb.config import ResolvedRunConfig
from qmb.runloop import STREAM_SET_KEY
from qmb.results.measures import ClosedTrade, EquityPoint, TradeSide

T = TypeVar("T")

# A fixed 2023-11 base instant (int64 UTC ns) so month/year buckets are stable.
NS: int = 1_700_000_000_000_000_000
NS_PER_DAY: int = 24 * 60 * 60 * 1_000_000_000
CCY: str = "USD"


def ok(result: Result[T]) -> T:
    """Unwrap an ``Ok`` or fail the test with the refusal's context."""
    assert is_ok(result), result
    return result.value


def instant(ns: int = NS) -> Instant:
    return ok(Instant.try_create(ns))


def interval(start_ns: int = NS, end_ns: int = NS + NS_PER_DAY * 10) -> Interval:
    return ok(Interval.try_create(instant(start_ns), instant(end_ns)))


def money(units: int, scale: int = 2, currency: str = CCY) -> Money:
    """Exact scaled-integer money (e.g. money(12345) == 123.45 USD at scale 2)."""
    return ok(Money.try_create(units, currency, scale))


def quantity(units: int, unit: str = "lot", scale: int = 0) -> Quantity:
    return ok(Quantity.try_create(units, unit, scale))


def trade(pnl_units: int, *, fees_units: int = 0, side: TradeSide = TradeSide.LONG,
          at_ns: int = NS, scale: int = 2) -> ClosedTrade:
    return ok(
        ClosedTrade.try_create(
            money(pnl_units, scale), money(fees_units, scale), side, instant(at_ns)
        )
    )


def equity(units: int, at_ns: int, *, scale: int = 2) -> EquityPoint:
    return ok(EquityPoint.try_create(instant(at_ns), money(units, scale)))


def config(*, streams: tuple[str, ...] = ("eurusd",), world: World = World.REPLAY,
           **keys: object) -> ResolvedRunConfig:
    """A resolved run-config — the run-id root. Distinct ``keys`` fork identity."""
    stamp = ok(fingerprint({"n": "epic19-audit-cfg", "s": list(streams),
                            "w": world.value, "k": sorted(keys)}))
    payload: dict[str, object] = {STREAM_SET_KEY: streams}
    payload.update(keys)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=payload,
        clock="replay" if world is World.REPLAY else "simulated",
        data_provenance="recorded" if world is World.REPLAY else "synthetic-tainted",
        world=world,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def writer() -> WriterId:
    return ok(WriterId.try_create("qmb-replay", "risk", "decisions", "boot-1"))


def journal_event(*, event_type: object = JournalEventType.DECISION, sequence: int = 0,
                  payload: dict[str, object] | None = None, outcome: object | None = None,
                  world: World = World.REPLAY) -> JournalEvent:
    """A genuine CT-13 JournalEvent (fp1-identified by qmf-core, not a bespoke log)."""
    return ok(
        JournalEvent.try_create(
            event_type=event_type,
            writer=writer(),
            sequence=sequence,
            instant=NS + sequence,
            world=world,
            payload=payload,
            outcome=outcome,
        )
    )


def mint_args(cfg: ResolvedRunConfig, *, stream_order: tuple[str, ...] = ("eurusd",),
              trades: object = (), equity_curve: object = (), journal_events: object = (),
              starting_capital: object = None, evidence: Interval | None = None,
              outcome_identity: object | None = None) -> dict[str, object]:
    """Keyword bundle for :func:`mint_run_performance_result`."""
    return {
        "config": cfg,
        "evidence_range": evidence if evidence is not None else interval(),
        "stream_order": stream_order,
        "slice_count": 2,
        "filled_count": 0,
        "resting_count": 0,
        "data_points_processed": 4,
        "outcome_identity": outcome_identity
        if outcome_identity is not None
        else {"class": "event-slice-loop-outcome"},
        "trades": trades,
        "equity_curve": equity_curve,
        "journal_events": journal_events,
        "starting_capital": starting_capital,
    }


def results_src_dir() -> Path:
    """Absolute path to ``qmb/src/qmb/results`` (read-only source evidence)."""
    import qmb.results as pkg

    return Path(pkg.__file__).resolve().parent


UNIT_KIND_VALUES: frozenset[str] = frozenset(member.value for member in UnitKind)


@pytest.fixture
def out_dir(tmp_path: Path) -> Path:
    """A fresh, existing run output directory owned by the test."""
    root = tmp_path / "run-out"
    root.mkdir()
    return root
