"""L2 CT-32 adoption + refusal shape for Epic 19 (C1, C2, C3).

The artifact IS a CT-32 performance-result (adopted, not reinvented); every
emitted quantity carries an AD-40 unit-kind; every Epic-19 refusal is a RETURNED
CT-04 typed value.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import (
    UNIT_KIND_VALUES,
    config,
    interval,
    journal_event,
    mint_args,
    money,
    ok,
)

from qmf.core.exact import UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal
from qmf.data.journal import DecisionOutcome
from qmf.risk.performance import PerformanceMeasure, PerformanceResult, UndefinedMeasure
from qmb.results.ct32 import (
    assemble_run_performance_result,
    assemble_suppression_and_veto_accounting,
    load_stored_ct32,
    mint_run_performance_result,
)

# The CT-32 contract's mandatory identity fields (ct-32-performance-result.yaml).
MANDATORY_CT32_FIELDS = (
    "result_label",
    "population",
    "period",
    "measure_set",
    "suppression_accounting",
    "veto_accounting",
    "account_binding_role",
    "class",
)


def _mint(cfg=None) -> PerformanceResult:
    cfg = cfg if cfg is not None else config()
    return ok(mint_run_performance_result(**mint_args(cfg)))


# --- C1: the artifact IS a valid CT-32, exactly one, no second report --------


def test_c1_stored_artifact_is_a_valid_ct32_container(out_dir: Path) -> None:
    artifact = _mint()
    fp = ok(assemble_run_performance_result(artifact, output_dir=out_dir))

    results_dir = out_dir / "results"
    files = sorted(p.name for p in results_dir.iterdir())
    assert files == ["ct-32.json"]  # exactly one artifact
    # No bespoke second report container anywhere under the run output dir.
    all_files = sorted(p.name for p in out_dir.rglob("*") if p.is_file())
    assert all_files == ["ct-32.json"]
    assert not list(out_dir.rglob("report.json"))

    body = json.loads((results_dir / "ct-32.json").read_text(encoding="utf-8"))
    for field in MANDATORY_CT32_FIELDS:
        assert field in body, field
    assert body["class"] == "performance-result"
    assert body["result_label"]["world"] == World.REPLAY.value
    # load_stored_ct32 accepts it as a CT-32 body and the returned fp is qmf-core's.
    loaded = ok(load_stored_ct32(out_dir))
    assert loaded["class"] == "performance-result"
    assert fp.value.startswith("fp1:sha256:")


def test_c1_a_bespoke_report_body_is_not_a_ct32(out_dir: Path) -> None:
    # Counter-case: a hand-rolled "report" missing CT-32 fields is refused as a
    # CT-32 body — the acceptance check can fail.
    (out_dir / "results").mkdir()
    (out_dir / "results" / "ct-32.json").write_text(
        json.dumps({"report": "my run summary", "score": 42}), encoding="utf-8"
    )
    refused = load_stored_ct32(out_dir)
    assert is_refusal(refused)
    assert refused.context["field"] == "ct32_artifact"


# --- C2: every emitted quantity carries an AD-40 unit-kind [R8, R15, R16] ----


def test_c2_every_measure_quantity_carries_ad40_unit_kind() -> None:
    artifact = _mint()
    for row in artifact.measure_set:
        if isinstance(row, PerformanceMeasure):
            assert row.quantity.unit_kind.value in UNIT_KIND_VALUES
        else:
            # the only non-PerformanceMeasure slot is a typed refusal a reader
            # tells apart from a numbered measure
            assert isinstance(row, UndefinedMeasure)


def test_c2_suppression_and_veto_counts_are_count_kind_and_default_zero() -> None:
    suppressions, vetoes = ok(assemble_suppression_and_veto_accounting())
    assert suppressions and vetoes  # keys never omitted, even when quiet
    for row in suppressions:
        assert row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value
        assert row.count == 0
    for row in vetoes:
        assert row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value
        assert row.count == 0


# --- C3: every Epic-19 refusal is a RETURNED CT-04 typed value ---------------

_CT32_REFUSAL_CATEGORIES = {
    RefusalCategory.POLICY_REJECTION,
    RefusalCategory.INVALID_INPUT,
    RefusalCategory.UNAVAILABLE_DEPENDENCY,
    RefusalCategory.STORAGE_FAILURE,
}


def _assert_ct04(result: Result[object]) -> TypedRefusal:
    assert isinstance(result, TypedRefusal), result  # returned, not raised
    assert result.category in _CT32_REFUSAL_CATEGORIES
    assert isinstance(result.context.get("field"), str)
    assert isinstance(result.context.get("reason"), str)
    return result


def test_c3_epic19_refusals_are_returned_ct04_values() -> None:
    # multi-role => policy rejection
    multi = mint_run_performance_result(**mint_args(config(account_role=("demo", "live"))))
    _assert_ct04(multi)
    assert multi.category is RefusalCategory.POLICY_REJECTION

    # non-replay world => policy rejection
    sim = mint_run_performance_result(**mint_args(config(world=World.SIMULATED)))
    _assert_ct04(sim)
    assert sim.category is RefusalCategory.POLICY_REJECTION

    # unresolvable suppression authority => invalid input
    bad = assemble_suppression_and_veto_accounting(
        (journal_event(outcome=DecisionOutcome.SUPPRESSED,
                       payload={"suppressing_authority": "kill-switch", "reason_class": "x"}),)
    )
    _assert_ct04(bad)
    assert bad.category is RefusalCategory.INVALID_INPUT

    # missing output dir => storage failure (nothing written)
    art = _mint()
    missing = assemble_run_performance_result(art, output_dir="C:/nonexistent-epic19-dir")
    _assert_ct04(missing)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
