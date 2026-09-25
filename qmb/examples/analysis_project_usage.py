"""Reference usage — analysis.project returns canonical saved-view JSON (Story 35.1).

Executable::

    python qmb/examples/analysis_project_usage.py

Shows the things Story 35.1 / 35.2 / FR-W21 / FR-W22 / FR-W23 / FR-W24 / SCN-0016 pin down:

1. analysis.project filters one cited CT-32 and its CT-29 stream.
2. Durable body is {method: projection, source_ct32, source_ct29, predicate, as_of}.
3. as_of is the source CT-32 registry_as_of, never query time; fp1 is of that JSON.
4. No new CT-32, no ledger line, no ExperimentSpec, no occupancy.
5. Claim-class is projection — never admission evidence, never B-4 confirmation.
6. A citation without that JSON body is refused; a copied trade list is not a view.
7. Size / R / Book / ports / starting_capital are path-dependent refusals, not a rerun.
8. Ungoverned is a return value only; governed-without-QMA writes a source-run-dir sidecar.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TypeVar

from qmb.analysis import PROJECTION_SIDECAR_FILENAME, cite_projection, project
from qmb.config import ResolvedRunConfig
from qmb.results import ClosedTrade, TradeSide, mint_run_performance_result
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


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _at(*, hour: int) -> Instant:
    stamp = datetime(2023, 11, 15, hour, 0, tzinfo=timezone.utc)
    return _instant(int(stamp.timestamp()) * 1_000_000_000)


def _money(value: int) -> Money:
    return _unwrap(Money.try_create(value, "USD", 2), "money")


def _trade(*, hour: int) -> ClosedTrade:
    return _unwrap(
        ClosedTrade.try_create(_money(100), _money(0), TradeSide.LONG, _at(hour=hour)),
        "trade",
    )


def _obs(ns: int) -> SliceObservation:
    return _unwrap(SliceObservation.try_create("eurusd", _instant(ns), True), "obs")


def main() -> None:
    as_of = _at(hour=0)
    stamp = _unwrap(fingerprint({"n": "analysis-project-example", "as_of": as_of.value_ns}), "fp")
    config = ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",), "registry_as_of": as_of},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )
    outcome = _unwrap(
        run(
            slices=((_obs(_NS),), (_obs(_NS + 1),)),
            config=config,
            handler=SilentSliceHandler(),
        ),
        "run",
    )
    trades = (_trade(hour=10), _trade(hour=18))
    artifact = _unwrap(
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
    view = _unwrap(
        project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"hours": {"start": 8, "end": 16}},
            as_of=as_of,
        ),
        "projection",
    )
    body = view.body()
    assert body["method"] == "projection"
    assert set(body) == {"method", "source_ct32", "source_ct29", "predicate", "as_of"}
    assert body["as_of"] == as_of.fp1_identity()
    assert view.fingerprint == _unwrap(fingerprint(body), "fp1")
    assert view.matched_count == 1
    assert view.occupancy == "query"
    assert view.mints_ct32 is False
    assert view.mints_experiment_spec is False
    assert view.claim_class == "projection"
    assert view.is_admission_evidence is False
    assert view.b4_role is None
    sys.stdout.write("canonical saved-view JSON\n")
    sys.stdout.write("as_of is source registry_as_of\n")
    sys.stdout.write("fp1 is of that JSON\n")
    sys.stdout.write("query occupancy, no CT-32\n")
    sys.stdout.write("claim-class is projection\n")

    cited = cite_projection(cite=view.fingerprint.value)
    assert is_refusal(cited) and cited.category is RefusalCategory.POLICY_REJECTION
    sys.stdout.write("citation without a body refused\n")
    copied = cite_projection(body={**body, "trades": [{"pnl": 1}]})
    assert is_refusal(copied)
    sys.stdout.write("copied trade list is not a saved view\n")
    query_time = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"hours": {"start": 8, "end": 16}},
        as_of=_at(hour=12),
    )
    assert is_refusal(query_time)
    sys.stdout.write("query-time as_of refused\n")

    size = project(
        source_ct32=artifact,
        source_ct29=trades,
        predicate={"hours": {"start": 8, "end": 16}},
        as_of=as_of,
        starting_capital=10_000,
    )
    assert is_refusal(size) and size.category is RefusalCategory.POLICY_REJECTION
    assert size.context["axis"] == "starting_capital"
    assert "path-dependent" in str(size.context["reason"])
    sys.stdout.write("forbidden starting_capital is path-dependent\n")

    assert view.home == "ungoverned"
    assert view.durable is False
    assert view.is_library_object is False
    sys.stdout.write("ungoverned is a return value only\n")

    with TemporaryDirectory() as raw:
        root = Path(raw)
        governed = _unwrap(
            project(
                source_ct32=artifact,
                source_ct29=trades,
                predicate={"hours": {"start": 8, "end": 16}},
                as_of=as_of,
                home="governed-without-qma",
                run_dir=root,
            ),
            "governed projection",
        )
        sidecar = root / PROJECTION_SIDECAR_FILENAME
        assert governed.durable is True
        assert governed.is_library_object is False
        assert governed.mints_ct32 is False
        assert governed.spawns_orchestrator is False
        assert sidecar.is_file()
        assert json.loads(sidecar.read_text(encoding="utf-8")) == governed.body()
        sys.stdout.write("governed sidecar written\n")
        coordinated = project(
            source_ct32=artifact,
            source_ct29=trades,
            predicate={"hours": {"start": 8, "end": 16}},
            as_of=as_of,
            home="coordinated",
            run_dir=root,
        )
        assert is_refusal(coordinated)
        assert coordinated.context["epic"] == "36"
        assert coordinated.context["opens_sqlite"] is False
        sys.stdout.write("coordinated persistence is Epic 36\n")

    sys.stdout.write(f"qmb {qmb.__version__}\n")
    sys.stdout.write("analysis.project ok\n")


if __name__ == "__main__":
    main()
