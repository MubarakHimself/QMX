"""Reference usage — one isolated, fully-labeled run per combo (Story 20.3).

Executable::

    python qmb/examples/sweep_batch_usage.py

Shows the things B-4 / B-5 / B-12 / spec R10-R12 / Story 20.3 pin down:

1. Each combination compiles to exactly one resolved run-config whose fp1 is its
   run id, runs as one isolated OS process under the min(cpu, memory) governor,
   and appends exactly ONE ledger line — never zero, never two.
2. Every combo line carries the AD-12 label, the CT-32 fingerprint, the raw
   AD-40 unit-kinded measures, and the sweep coordinates
   {sweep_id, instrument, bar_spec, param_hash}; world=replay is
   provenance-derived and no line stores a pass/fail verdict.
3. Concurrency is scheduling only: the same batch run sequentially (cpu budget 1)
   and concurrently (cpu budget 4) produces the identical report identity — same
   run ids, same CT-32 fingerprints.
4. One combination's typed refusal (a stream-set violation) is recorded as that
   combo's labeled aborted line with refusal context, and the batch continues —
   one combo's refusal never aborts the sweep.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED, STARTING_CAPITAL_KEY
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.runloop import SliceObservation
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import Result, is_ok
from qmf.registry import RegistrationRecord
from qmf.risk.grammar import AdmissionImpact, TemplateSection, TemplateVariable, UiEditability
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_SEVERITY = "workspace-declared"
_SEED = Money(value=1_000_000, currency="USD", scale=2)
_TF_1M = {"kind": "time-interval", "seconds": 60}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _instant(ns: int = _NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant")


def _writer() -> WriterId:
    return _unwrap(
        WriterId.try_create("node-a", "authoring", "config-fragment", "boot-1"), "writer"
    )


def _variable(name: str, minor: int) -> TemplateVariable:
    return _unwrap(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        ),
        "variable",
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _unwrap(TemplateSection.try_create(name, {variable.name: variable}), "section")


def _book() -> BookDefinition:
    return _unwrap(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _variable("q", 100)),
            },
        ),
        "book",
    )


def _bms() -> BmsDefinition:
    return _unwrap(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section("accounting_rules", _variable("numeraire_unit", 1)),
                "constraints": _section("constraints", _variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _variable("posture", 1)),
                "reporting": _section("reporting", _variable("cadence", 1)),
            },
        ),
        "bms",
    )


def _record(kind: str, body: object) -> RegistrationRecord:
    if isinstance(body, (BookDefinition, BmsDefinition)):
        parents: tuple[object, ...] = (_unwrap(body.fingerprint(), "definition fp1"),)
        payload: Mapping[str, object] = body.fp1_identity()
        version = body.contract_format_version
    else:
        parents = ()
        payload = cast("Mapping[str, object]", body)
        version = 1
    return _unwrap(
        RegistrationRecord.try_create(kind, version, parents, payload, _writer(), 0, _instant()),
        "record",
    )


def _admitted() -> qmb.AdmittedSweep:
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointers = (
        _unwrap(
            DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant()), "pointer"
        ),
    )
    as_of = _unwrap(
        AsOfSet.try_create(
            _instant(), records=(book_record, bms_record, bot_record), pointers=pointers
        ),
        "as-of set",
    )
    hub = _unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = _unwrap(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY), "port")
    declaration = _unwrap(
        qmb.SweepDeclaration.try_create(
            bot=bot_record.stable_id,
            book=book_record.stable_id,
            bms=bms_record.stable_id,
            instruments=["EURUSD", "GBPUSD"],
            timeframes=[_TF_1M],
            parameters={"lookback": [10, 20]},
        ),
        "declaration",
    )
    return _unwrap(qmb.admit_sweep(declaration, port, _writer()), "admission")


def _run_settings() -> dict[str, object]:
    return {
        "invocation_flags": {STARTING_CAPITAL_KEY: _SEED},
        "workspace_defaults": {
            "account_id": "acct-replay",
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_RECORDED,
            "venue_id": "venue-replay",
        },
    }


def _good_slices(combo: qmb.SweepRunSpec) -> tuple[tuple[SliceObservation, ...], ...]:
    return (
        (_unwrap(SliceObservation.try_create(combo.instrument, _instant(_NS), True), "obs"),),
        (_unwrap(SliceObservation.try_create(combo.instrument, _instant(_NS + 1), True), "obs"),),
    )


def _ledger(root: Path) -> qmb.LedgerSink:
    return _unwrap(
        qmb.LedgerSink.try_create(
            root, machine="example-machine", worker_slot=0, boot_epoch_id="boot-1"
        ),
        "ledger",
    )


def one_line_per_combo_with_coordinates(runs: Path, ledger_root: Path) -> None:
    admitted = _admitted()
    ledger = _ledger(ledger_root)
    report = _unwrap(
        qmb.run_sweep_batch(
            admitted,
            output_root=runs,
            ledger=ledger,
            combo_slices=_good_slices,
            projected_peak_memory=64 * 1024 * 1024,
            cpu_budget=1,
            memory_budget=1024 * 1024 * 1024,
            **_run_settings(),
        ),
        "batch",
    )
    assert report.run_count == 4
    assert report.completed_count == 4
    assert report.refused_count == 0

    lines = _unwrap(
        qmb.read_merge_view(ledger.root, world=World.REPLAY, role=qmb.ROLE_CONFIRMATION),
        "merge",
    )
    assert len(lines) == 4  # exactly one line per combo, never zero, never two
    by_run = {line.run_id.value: line for line in lines}
    for outcome in report.outcomes:
        line = by_run[outcome.run_id.value]
        assert line.ct32_fingerprint == outcome.ct32_fingerprint
        assert line.world is World.REPLAY  # provenance-derived, non-live
        assert "verdict" not in line.fp1_identity()  # no stored pass/fail
        assert line.sweep_coordinates is not None
        assert line.sweep_coordinates["sweep_id"] == admitted.label.sweep_id.value
        assert line.sweep_coordinates["instrument"] == outcome.sweep_coordinates["instrument"]
        assert "param_hash" in line.sweep_coordinates
        assert all(
            "unit_kind" in measure or measure.get("class") == "undefined-measure"
            for measure in line.measures
        )
    print("each combo: one confirmation line carrying label, CT-32, measures, and coordinates")


def concurrency_never_changes_a_result(runs_a: Path, runs_b: Path, ledger_root: Path) -> None:
    admitted = _admitted()
    sequential = _unwrap(
        qmb.run_sweep_batch(
            _admitted(),
            output_root=runs_a,
            ledger=_ledger(ledger_root / "seq"),
            combo_slices=_good_slices,
            projected_peak_memory=64 * 1024 * 1024,
            cpu_budget=1,
            memory_budget=1024 * 1024 * 1024,
            **_run_settings(),
        ),
        "sequential",
    )
    concurrent = _unwrap(
        qmb.run_sweep_batch(
            admitted,
            output_root=runs_b,
            ledger=_ledger(ledger_root / "par"),
            combo_slices=_good_slices,
            projected_peak_memory=64 * 1024 * 1024,
            cpu_budget=4,
            memory_budget=1024 * 1024 * 1024,
            **_run_settings(),
        ),
        "concurrent",
    )
    assert sequential.fp1_identity() == concurrent.fp1_identity()
    print("concurrency is scheduling only: same run ids and CT-32 fingerprints either way")


def one_refusal_is_a_line_not_a_batch_abort(runs: Path, ledger_root: Path) -> None:
    admitted = _admitted()
    ledger = _ledger(ledger_root)
    victim = admitted.combos[1]

    def _slices(combo: qmb.SweepRunSpec) -> tuple[tuple[SliceObservation, ...], ...]:
        if combo.fp1_identity() == victim.fp1_identity():
            # A slice naming a stream outside the combo's declared stream set is a
            # stream-set violation the pure run() refuses inside the worker.
            return (
                (_unwrap(SliceObservation.try_create("NOT-A-STREAM", _instant(), True), "obs"),),
            )
        return _good_slices(combo)

    report = _unwrap(
        qmb.run_sweep_batch(
            admitted,
            output_root=runs,
            ledger=ledger,
            combo_slices=_slices,
            projected_peak_memory=64 * 1024 * 1024,
            cpu_budget=2,
            memory_budget=1024 * 1024 * 1024,
            **_run_settings(),
        ),
        "batch",
    )
    assert report.run_count == 4  # the batch completed over every combo
    assert report.completed_count == 3
    assert report.refused_count == 1

    aborted = _unwrap(
        qmb.read_merge_view(ledger.root, world=World.REPLAY, role=qmb.ROLE_ABORTED),
        "aborted",
    )
    assert len(aborted) == 1
    assert aborted[0].refusal is not None  # refusal context is recorded
    assert aborted[0].sweep_coordinates is not None
    confirmed = _unwrap(
        qmb.read_book_bar(ledger.root, world=World.REPLAY),
        "book-bar",
    )
    assert len(confirmed) == 3  # the Book bar (confirmation) sees only the survivors
    print("one combo's refusal is that combo's aborted line; the batch continued")


def main() -> None:
    assert callable(qmb.run_sweep_batch)
    assert qmb.BATCH_ONE_LINE_PER_COMBO is True
    assert qmb.BATCH_ABORTS_ON_COMBO_REFUSAL is False
    with tempfile.TemporaryDirectory(prefix="qmb_sweep_batch_", ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        for name in ("runs1", "runs2", "runs3", "runs4", "ledger1", "ledger3"):
            (root / name).mkdir()
        one_line_per_combo_with_coordinates(root / "runs1", root / "ledger1")
        concurrency_never_changes_a_result(root / "runs2", root / "runs3", root / "ledger_conc")
        one_refusal_is_a_line_not_a_batch_abort(root / "runs4", root / "ledger3")
    print("sweep batch ok")


if __name__ == "__main__":
    main()
