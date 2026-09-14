"""Story 31.5 — close FTR-01; four-verdict reconcile over declared lookback."""

from __future__ import annotations

from typing import TypeVar, cast

from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Duration,
    Instant,
    Money,
    Quantity,
    RefusalCategory,
    Result,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.venue.capabilities import ErrorMap
from qmf.venue.events import Reconciliation, ReconciliationVerdict
from qmn.data.mapping import (
    CT13_SEVEN_EVENT_TYPES,
    OBSERVATION_JOURNAL_TYPE,
    assert_no_eighth_journal_type,
    journal_event_for_kind,
    refuse_observation_journal_type,
)
from qmn.reconcile import (
    compute_cash_residual,
    compute_quantity_residual,
    refuse_equity_difference,
)
from qmn.venue import ConformanceDouble, LiveCTraderClient, WireKind
from qmn.venue.live import ct13_journal_event_type

T = TypeVar("T")

_BOOT = "boot-epoch-readback-31-5"
_WALL_NS = 1_724_000_000 * 1_000_000_000
_LOOKBACK_NS = 1_000_000_000
_COVERING_VENUE_MS = (_WALL_NS - 2 * _LOOKBACK_NS) // 1_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _venue(value: str = "venue-ctrader-demo") -> VenueId:
    return _ok(VenueId.try_create(value))


def _account(venue: VenueId | None = None) -> Account:
    return _ok(Account.try_create("acct-rb-1", venue or _venue(), AccountRole.DEMO))


def _instant(ns: int = _WALL_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _clock(*, frames: int = 32) -> DataDrivenClock:
    walls = tuple(_instant(_WALL_NS + i * 1_000_000) for i in range(frames))
    monos = tuple(5_000_000_000 + i * 1_000_000 for i in range(frames))
    return DataDrivenClock(boot_epoch_id=_BOOT, wall_instants=walls, monotonic_ns=monos)


def _lookback() -> Duration:
    return _ok(Duration.try_create(_LOOKBACK_NS))


def _client(*, lookback: Duration | None = None) -> LiveCTraderClient:
    return _ok(
        LiveCTraderClient.try_create(
            World.LIVE,
            _venue(),
            clock=_clock(),
            error_map=_ok(ErrorMap.try_create(1, [])),
            declared_lookback=lookback,
        )
    )


def _open(client: LiveCTraderClient) -> LiveCTraderClient:
    _ok(client.open_session(_account(client.venue_id)))
    return client


def test_mapping_readbacks_are_data_quality_not_observation() -> None:
    for kind in (
        "position-read-back",
        "position-readback",
        "balance-read-back",
        "balance-readback",
        WireKind.POSITION_READBACK,
        WireKind.BALANCE_READBACK,
    ):
        assert _ok(journal_event_for_kind(kind)) == "data quality"
        assert _ok(ct13_journal_event_type(kind)) == "data quality"
    assert OBSERVATION_JOURNAL_TYPE not in CT13_SEVEN_EVENT_TYPES
    assert len(CT13_SEVEN_EVENT_TYPES) == 7


def test_minting_observation_or_eighth_type_is_refused() -> None:
    refused = refuse_observation_journal_type()
    assert refused.context["ftr"] == "FTR-01"
    eighth = _refusal(assert_no_eighth_journal_type("observation"))
    assert eighth.context["ftr"] == "FTR-01"
    invented = _refusal(assert_no_eighth_journal_type("reconciliation"))
    assert invented.context["ftr"] == "FTR-01"
    assert _refusal(journal_event_for_kind("observation")).context["ftr"] == "FTR-01"


def test_four_verdicts_are_constructible() -> None:
    names = {m.value for m in ReconciliationVerdict}
    assert names == {"reconciled", "drift", "unknown", "out-of-lookback"}
    for verdict in ReconciliationVerdict:
        rec = Reconciliation(verdict=verdict, detail="fixture")
        assert rec.verdict is verdict
        assert rec.gates_sensing_pipe is False


def test_live_reconcile_out_of_lookback_without_covering_evidence() -> None:
    client = _open(_client(lookback=_lookback()))
    rec = _ok(client.reconcile())
    assert rec.verdict is ReconciliationVerdict.OUT_OF_LOOKBACK
    assert rec.is_out_of_lookback is True


def test_live_reconcile_unknown_when_readbacks_absent_inside_lookback() -> None:
    client = _open(_client(lookback=_lookback()))
    _ok(
        client.receive(
            WireKind.SPOT,
            {"bid": 100_000},
            native_id="spot-cover",
            venue_time_raw=_COVERING_VENUE_MS,
        )
    )
    rec = _ok(client.reconcile())
    assert rec.verdict is ReconciliationVerdict.UNKNOWN


def test_live_reconcile_reconciled_from_persisted_readbacks() -> None:
    client = _open(_client(lookback=_lookback()))
    pos = dict(
        _ok(
            client.receive(
                WireKind.POSITION_READBACK,
                {"volume": 100},
                native_id="pos-cover",
                venue_time_raw=_COVERING_VENUE_MS,
            )
        )
    )
    bal = dict(
        _ok(
            client.receive(
                WireKind.BALANCE_READBACK,
                {"cash": 50_000},
                native_id="bal-cover",
                venue_time_raw=_COVERING_VENUE_MS,
            )
        )
    )
    pos_mapping = cast("dict[str, object]", pos["journal_mapping"])
    bal_mapping = cast("dict[str, object]", bal["journal_mapping"])
    assert pos_mapping["event_type"] == "data quality"
    assert bal_mapping["event_type"] == "data quality"
    assert pos["synthesized"] is False
    rec = _ok(client.reconcile())
    assert rec.verdict is ReconciliationVerdict.RECONCILED


def test_live_reconcile_drift_when_bound_expected_disagrees() -> None:
    client = _open(_client(lookback=_lookback()))
    _ok(
        client.receive(
            "position-read-back",
            {"volume": 100},
            native_id="pos-drift",
            venue_time_raw=_COVERING_VENUE_MS,
        )
    )
    _ok(
        client.receive(
            "balance-read-back",
            {"cash": 50_000},
            native_id="bal-drift",
            venue_time_raw=_COVERING_VENUE_MS,
        )
    )
    _ok(client.bind_reconcile_expected({"positions": (), "balances": ()}))
    rec = _ok(client.reconcile())
    assert rec.verdict is ReconciliationVerdict.DRIFT


def test_conformance_double_arms_all_four_verdicts() -> None:
    venue = _ok(VenueId.try_create("conformance:readback-31-5"))
    double = _ok(ConformanceDouble.try_create(World.LIVE, venue))
    for verdict in ReconciliationVerdict:
        _ok(double.arm_reconcile(verdict))
        rec = _ok(double.reconcile())
        assert rec.verdict is verdict


def test_residuals_remain_story_266_exact_integers() -> None:
    qty = _ok(
        compute_quantity_residual(
            instrument="EURUSD",
            virtual_quantity=_ok(Quantity.try_create(100, "lot", 2)),
            venue_quantity=_ok(Quantity.try_create(150, "lot", 2)),
        )
    )
    assert qty.residual == _ok(Quantity.try_create(50, "lot", 2))
    cash = _ok(
        compute_cash_residual(
            venue_realized_balance=_ok(Money.try_create(10_050_00, "USD", 2)),
            virtual_realized_cash=_ok(Money.try_create(10_000_00, "USD", 2)),
        )
    )
    assert cash.residual == _ok(Money.try_create(50_00, "USD", 2))
    refused = _refusal(
        refuse_equity_difference(
            _ok(Money.try_create(100_00, "USD", 2)),
            _ok(Money.try_create(99_00, "USD", 2)),
        )
    )
    assert refused.category is RefusalCategory.POLICY_REJECTION
    rec = _ok(_open(_client(lookback=_lookback())).reconcile())
    assert not hasattr(rec, "quantity_residuals")
    assert rec.verdict in ReconciliationVerdict


def test_credential_free_readback_needs_no_network_token() -> None:
    client = _open(_client(lookback=_lookback()))
    recorded = dict(
        _ok(
            client.receive(
                WireKind.POSITION_READBACK,
                {"volume": 1},
                native_id="pos-cred-free",
            )
        )
    )
    assert recorded["verbatim_recorded"] is True
    mapping = cast("dict[str, object]", recorded["journal_mapping"])
    assert mapping["event_type"] == "data quality"
    rec = _ok(client.reconcile())
    assert rec.verdict in ReconciliationVerdict
