"""Reference usage — compare_runs is a readout; labels stay parent-shaped (Story 35.5).

Executable::

    python qmb/examples/analysis_compare_runs_usage.py

Shows the things Story 35.5 / FR-W26 / FR-W28 / FR-W21 / SCN-0016 pin down:

1. compare_runs reads two cited CT-32s and returns a readout.
2. It mints no artifact, no ledger line, no confirmation label, and no occupancy.
3. CT-32 and B-4 gain no lane / analysis_method field.
4. A projection saved view has no B-4 role, claim-class projection, inherited
   source world, and is never confirmed. L20 forbids gating live money on replay.
5. A path-dependent rerun CT-32's B-4 role is the role of that run — not
   admission evidence unless role=confirmation.
6. F07 synthetic portfolio combination is refused as deferred.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypeVar

from qmb.analysis import compare_runs, project, rerun
from qmb.config import ResolvedRunConfig
from qmb.results import ClosedTrade, TradeSide, mint_run_performance_result
from qmb.results.ct32 import load_stored_ct32
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant
from qmf.core.exact import Money
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal

import qmb

T = TypeVar("T")
_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _at(*, hour: int = 10) -> Instant:
    stamp = datetime(2023, 11, 15, hour, 0, tzinfo=timezone.utc)
    return _instant(int(stamp.timestamp()) * 1_000_000_000)


def _money(value: int) -> Money:
    return _unwrap(Money.try_create(value, "USD", 2), "money")


def _trade(*, hour: int) -> ClosedTrade:
    return _unwrap(
        ClosedTrade.try_create(_money(100), _money(0), TradeSide.LONG, _at(hour=hour)),
        "trade",
    )


def _obs(ns: int = _NS) -> SliceObservation:
    return _unwrap(SliceObservation.try_create("eurusd", _instant(ns), True), "obs")


def _slices() -> tuple[tuple[SliceObservation, ...], ...]:
    return ((_obs(),), (_obs(_NS + 1),))


def _config(*, tag: str, registry_as_of: Instant | None = None) -> ResolvedRunConfig:
    stamp = _unwrap(fingerprint({"n": "analysis-compare-example", "tag": tag}), "fp")
    keys: dict[str, object] = {STREAM_SET_KEY: ("eurusd",)}
    if registry_as_of is not None:
        keys["registry_as_of"] = registry_as_of
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=keys,
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _result(*, tag: str, trades: tuple[ClosedTrade, ...] = ()) -> object:
    config = _config(tag=tag, registry_as_of=_at(hour=0))
    outcome = _unwrap(
        run(slices=_slices(), config=config, handler=SilentSliceHandler()),
        "run",
    )
    return _unwrap(
        mint_run_performance_result(
            config,
            evidence_range=outcome.evidence_range,
            stream_order=outcome.stream_order,
            slice_count=2,
            filled_count=0,
            resting_count=0,
            data_points_processed=2,
            outcome_identity=outcome.fp1_identity(),
            trades=trades,
        ),
        "ct32",
    )


def _sink(root: Path, *, slot: object = 0) -> qmb.LedgerSink:
    return _unwrap(
        qmb.LedgerSink.try_create(
            root / "ledger",
            machine="example-machine",
            worker_slot=slot,
            boot_epoch_id="boot-1",
        ),
        "ledger",
    )


def main() -> None:
    left = _result(tag="left", trades=(_trade(hour=10),))
    right = _result(tag="right", trades=(_trade(hour=18),))
    readout = _unwrap(compare_runs(left, right), "compare")
    assert readout.occupancy == "query"
    assert readout.mints_ct32 is False
    assert readout.appends_ledger is False
    assert readout.confirmation_label is None
    assert readout.is_analysis_method is False
    assert readout.b4_role is None
    assert readout.same_world is True
    print("compare_runs is a readout of cited CT-32 fields")
    print("no artifact, no ledger line, no confirmation label, no occupancy")

    identity = qmb.compare_runs_identity()
    assert identity["is_analysis_method"] is False
    assert "analysis_method" not in identity
    assert "lane" not in identity
    print("CT-32 and B-4 gain no lane or analysis_method field")

    as_of = _at(hour=0)
    trades = (_trade(hour=10),)
    artifact = _result(tag="proj", trades=trades)
    view = _unwrap(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"max_trades": 1},
            as_of=as_of,
        ),
        "projection",
    )
    assert view.b4_role is None
    assert view.claim_class == "projection"
    assert view.world == World.REPLAY.value
    assert view.confirmed is False
    print("projection has no B-4 role, claim-class projection, inherited world, never confirmed")
    gated = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"max_trades": 1},
        as_of=as_of,
        gating_live=True,
    )
    assert is_refusal(gated) and gated.context["law"] == "L20"
    print("L20 forbids gating live money on replay-world verdicts")

    with TemporaryDirectory() as raw:
        root = Path(raw)
        trial = _unwrap(
            rerun(
                source_ct32=artifact,
                config=_config(tag="trial"),
                slices=_slices(),
                output_root=root / "trial",
                ledger=_sink(root, slot=0),
                role=qmb.ROLE_TRIAL,
            ),
            "trial rerun",
        )
        assert trial.b4_role == qmb.ROLE_TRIAL
        assert trial.is_admission_evidence is False
        stored = _unwrap(load_stored_ct32(trial.isolated.output_dir), "stored")
        assert "analysis_method" not in stored
        assert "lane" not in stored
        print("rerun B-4 role is the role of that run, not admission evidence")

        confirmation = _unwrap(
            rerun(
                source_ct32=artifact,
                config=_config(tag="confirm"),
                slices=_slices(),
                output_root=root / "confirm",
                ledger=_sink(root, slot=1),
            ),
            "confirmation rerun",
        )
        assert confirmation.b4_role == qmb.ROLE_CONFIRMATION
        assert confirmation.is_admission_evidence is True
        print("admission evidence remains B-4 role=confirmation only")

    f07 = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"max_trades": 1},
        as_of=as_of,
        portfolio=True,
    )
    assert is_refusal(f07) and f07.category is RefusalCategory.POLICY_REJECTION
    assert f07.context["feature"] == "F07"
    assert f07.context["deferred"] is True
    assert is_refusal(rerun(synthetic_portfolio=True))
    assert is_refusal(compare_runs(left, right, combine=True))
    print("F07 synthetic portfolio combination is refused as deferred")

    assert is_refusal(compare_runs(left, right, occupancy="run"))
    assert is_refusal(compare_runs(left, right, mint_ct32=True))
    assert is_refusal(compare_runs(left, right, role="confirmation"))
    print("run occupancy, minted artifact, and confirmation label are refused")

    print(f"qmb {qmb.__version__}")
    print("compare_runs ok")


if __name__ == "__main__":
    main()
