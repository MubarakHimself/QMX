"""L4 golden scenario — SCN-0012 step (7) tail, co-owned with Epic 14 (R-016).

Drive a golden replay run's PURE ``run()`` return (the E14 loop) through results/
assembly and assert the CT-32-production tail and its boundary with the
reader-derived verdict fold (step 8): exactly one CT-32, world=replay, the full
AD-12 label, raw AD-40 unit-kinded measures, and NO stored verdict.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import NS, config, ok

from qmf.core.chrono import Instant
from qmf.core.fingerprint import EvidenceClass, World
from qmf.core.identity import AccountRole
from qmf.risk.performance import PerformanceMeasure, PerformanceResult, UndefinedMeasure
from qmb.runloop import SilentSliceHandler, SliceObservation, run
from qmb.results.ct32 import assemble_run_performance_result, load_stored_ct32
from qmb.results.measures import MEASURE_IDENTITIES

FORBIDDEN = ("score", "grade", "tier", "weighted", "rating", "composite", "verdict",
             "pass_fail", "passed", "failed")


def _obs(stream_id: str, ns: int) -> SliceObservation:
    return ok(SliceObservation.try_create(stream_id, ok(Instant.try_create(ns)), True))


def _golden_run() -> PerformanceResult:
    cfg = config(streams=("eurusd",))
    outcome = ok(run(
        slices=((_obs("eurusd", NS),), (_obs("eurusd", NS + 1),)),
        config=cfg,
        handler=SilentSliceHandler(),
    ))
    artifact = outcome.performance_result
    assert isinstance(artifact, PerformanceResult)
    return outcome, artifact


def test_scn0012_run_return_assembles_one_ct32_replay_artifact(out_dir: Path) -> None:
    outcome, artifact = _golden_run()

    # step (7): exactly one CT-32 written from the pure run() return
    stamped = ok(assemble_run_performance_result(outcome, output_dir=out_dir))
    files = sorted(p.name for p in (out_dir / "results").iterdir())
    assert files == ["ct-32.json"]
    assert stamped == ok(artifact.fingerprint())

    body = load_stored_ct32(out_dir).value
    # world=replay and the full AD-12 label the ledger line will cite
    assert body["result_label"]["world"] == World.REPLAY.value
    assert artifact.result_label.evidence_class is EvidenceClass.PROVISIONAL
    assert body["account_binding_role"] == AccountRole.DEMO.value
    assert artifact.result_label.evidence_time_range == outcome.evidence_range

    # the raw AD-40 unit-kinded measures are present, in the pinned order
    order = [row["measure_identity"] for row in body["measure_set"]]
    assert order == list(MEASURE_IDENTITIES)
    for row in artifact.measure_set:
        assert isinstance(row, (PerformanceMeasure, UndefinedMeasure))


def test_scn0012_step8_verdict_is_absent_from_the_artifact(out_dir: Path) -> None:
    outcome, _ = _golden_run()
    ok(assemble_run_performance_result(outcome, output_dir=out_dir))
    body = json.loads((out_dir / "results" / "ct-32.json").read_text(encoding="utf-8"))

    # the step (8) verdict is reader-derived and NEVER stored in the artifact
    flat = json.dumps(body).casefold()
    for token in FORBIDDEN:
        assert token not in flat, token


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
