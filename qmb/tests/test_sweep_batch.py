"""Story 20.3 — one isolated, fully-labeled run per combo with exactly one ledger line."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmb.config import CLOCK_REPLAY, PROVENANCE_RECORDED, STARTING_CAPITAL_KEY
from qmb.doors import api
from qmb.ledger import LedgerLine
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.runloop import SliceObservation
from qmb.sweep import (
    BATCH_ABORTS_ON_COMBO_REFUSAL,
    BATCH_ONE_LINE_PER_COMBO,
    STATUS_COMPLETED,
    STATUS_REFUSED,
    SWEEP_COORDINATES_CLASS,
    AdmittedSweep,
    SweepDeclaration,
    SweepRunSpec,
    admit_sweep,
    run_sweep_batch,
    sweep_batch_identity,
    sweep_coordinates_of,
)
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import Money, UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
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
_GIB = 1024 * 1024 * 1024
_PEAK = 64 * 1024 * 1024


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(stream: str = "config-fragment") -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", stream, "boot-1"))


def _variable(name: str, minor: int) -> TemplateVariable:
    return _ok(
        TemplateVariable.try_create(
            name,
            UnitKind.MONEY,
            Money(value=minor, currency="USD", scale=2),
            UiEditability.UI_EDITABLE,
            AdmissionImpact.RESIGN,
        )
    )


def _section(name: str, variable: TemplateVariable) -> TemplateSection:
    return _ok(TemplateSection.try_create(name, {variable.name: variable}))


def _book() -> BookDefinition:
    return _ok(
        BookDefinition.try_create(
            BOOK_CONTRACT_FORMAT_VERSION,
            "USD",
            {
                "admission_bar": _section("admission_bar", _variable("bar_floor", 1)),
                "money_rules": _section("money_rules", _variable("loss_floor", 800_000)),
                "exit_policy": _section("exit_policy", _variable("q", 100)),
            },
        )
    )


def _bms() -> BmsDefinition:
    return _ok(
        BmsDefinition.try_create(
            BMS_CONTRACT_FORMAT_VERSION,
            {
                "accounting_rules": _section("accounting_rules", _variable("numeraire_unit", 1)),
                "constraints": _section("constraints", _variable("exposure_ceiling", 50_000)),
                "ksa_policy": _section("ksa_policy", _variable("posture", 1)),
                "reporting": _section("reporting", _variable("cadence", 1)),
            },
        )
    )


def _record(kind: str, body: object) -> RegistrationRecord:
    if isinstance(body, (BookDefinition, BmsDefinition)):
        parents: tuple[object, ...] = (_ok(body.fingerprint()),)
        payload: Mapping[str, object] = body.fp1_identity()
        version = body.contract_format_version
    else:
        parents = ()
        payload = cast("Mapping[str, object]", body)
        version = 1
    return _ok(
        RegistrationRecord.try_create(kind, version, parents, payload, _writer(kind), 0, _instant())
    )


def _admit(
    *,
    instruments: object = ("EURUSD", "GBPUSD"),
    parameters: object = None,
) -> AdmittedSweep:
    book_record = _record("book-definition", _book())
    bms_record = _record("bms-definition", _bms())
    bot_record = _record("bot-definition", {"class": "bot-definition", "alias": "mean-reversion"})
    pointers = (_ok(DatedPointer.try_create("mean-reversion", bot_record.stable_id, _instant())),)
    as_of = _ok(
        AsOfSet.try_create(
            _instant(), records=(book_record, bms_record, bot_record), pointers=pointers
        )
    )
    hub = _ok(PassiveHub.try_create((as_of,)))
    port = _ok(RegistryReadPort.try_create(hub, stale_evidence_severity=_SEVERITY))
    decl = _ok(
        SweepDeclaration.try_create(
            bot=bot_record.stable_id,
            book=book_record.stable_id,
            bms=bms_record.stable_id,
            instruments=instruments,
            timeframes=(_TF_1M,),
            parameters=parameters if parameters is not None else {"lookback": [10, 20]},
        )
    )
    return _ok(admit_sweep(decl, port, _writer()))


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


def _good_slices(combo: SweepRunSpec) -> tuple[tuple[SliceObservation, ...], ...]:
    return (
        (_ok(SliceObservation.try_create(combo.instrument, _instant(_NS), True)),),
        (_ok(SliceObservation.try_create(combo.instrument, _instant(_NS + 1), True)),),
    )


def _ledger(root: Path, sub: str = "ledger") -> qmb.LedgerSink:
    return _ok(
        qmb.LedgerSink.try_create(
            root / sub, machine="node-a", worker_slot=0, boot_epoch_id="boot-1"
        )
    )


def _runs(root: Path, sub: str = "runs") -> Path:
    directory = root / sub
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _confirmation_lines(root: Path) -> tuple[LedgerLine, ...]:
    return _ok(qmb.read_merge_view(_ledger(root).root, world=World.REPLAY, role="confirmation"))


def _batch(
    admitted: AdmittedSweep,
    root: Path,
    *,
    combo_slices: object,
    cpu_budget: int = 1,
    memory_budget: int = _GIB,
    projected_peak_memory: int = _PEAK,
    runs_sub: str = "runs",
    ledger_sub: str = "ledger",
) -> qmb.SweepBatchReport:
    return _ok(
        run_sweep_batch(
            admitted,
            output_root=_runs(root, runs_sub),
            ledger=_ledger(root, ledger_sub),
            combo_slices=combo_slices,
            projected_peak_memory=projected_peak_memory,
            cpu_budget=cpu_budget,
            memory_budget=memory_budget,
            **_run_settings(),
        )
    )


# --- AC1 + AC2: one isolated run per combo, exactly one confirmation line ------


def test_each_combo_is_one_isolated_run_with_one_confirmation_line(tmp_path: Path) -> None:
    admitted = _admit()
    report = _batch(admitted, tmp_path, combo_slices=_good_slices)

    assert report.run_count == 4
    assert report.completed_count == 4
    assert report.refused_count == 0
    # Each combination's run id IS its resolved run-config fingerprint (B-3).
    for combo, outcome in zip(admitted.combos, report.outcomes, strict=True):
        config = _ok(admitted.compile_combo(combo, **_run_settings()))
        assert outcome.run_id == config.fingerprint
        assert outcome.status == STATUS_COMPLETED
        assert outcome.output_dir is not None
    # One isolated output directory per combination, never shared.
    dirs = [outcome.output_dir for outcome in report.outcomes]
    assert len(set(dirs)) == 4

    lines = _confirmation_lines(tmp_path)
    assert len(lines) == 4  # exactly one line per combo, never zero, never two
    by_run = {line.run_id.value: line for line in lines}
    for outcome in report.outcomes:
        line = by_run[outcome.run_id.value]
        assert line.ct32_fingerprint == outcome.ct32_fingerprint
        assert line.measures  # raw AD-40 unit-kinded measures
        assert all(
            "unit_kind" in measure or measure.get("class") == "undefined-measure"
            for measure in line.measures
        )
        _assert_coordinates(line, admitted, outcome.sweep_coordinates["instrument"])


def _assert_coordinates(line: LedgerLine, admitted: AdmittedSweep, instrument: object) -> None:
    coords = line.sweep_coordinates
    assert coords is not None
    assert coords["class"] == SWEEP_COORDINATES_CLASS
    assert coords["sweep_id"] == admitted.label.sweep_id.value
    assert coords["instrument"] == instrument
    assert "bar_spec" in coords
    assert "param_hash" in coords


# --- AC2: exactly one line per combo, never two -------------------------------


def test_exactly_one_line_per_combo_across_all_roles(tmp_path: Path) -> None:
    admitted = _admit()
    report = _batch(admitted, tmp_path, combo_slices=_good_slices)
    root = _ledger(tmp_path).root
    confirmation = _ok(qmb.read_merge_view(root, world=World.REPLAY, role="confirmation"))
    aborted = _ok(qmb.read_merge_view(root, world=World.REPLAY, role="aborted"))
    run_ids = [line.run_id.value for line in (*confirmation, *aborted)]
    assert len(run_ids) == report.run_count
    assert len(set(run_ids)) == report.run_count  # each combo's run id appears once


# --- AC1 / spec R12: concurrency never changes a result or CT-32 --------------


def test_concurrency_never_changes_result_or_ct32(tmp_path: Path) -> None:
    admitted = _admit()
    sequential = _batch(
        admitted,
        tmp_path,
        combo_slices=_good_slices,
        cpu_budget=1,
        runs_sub="seq_runs",
        ledger_sub="seq_ledger",
    )
    concurrent = _batch(
        admitted,
        tmp_path,
        combo_slices=_good_slices,
        cpu_budget=4,
        runs_sub="par_runs",
        ledger_sub="par_ledger",
    )
    # Same run ids and same CT-32 fingerprints regardless of parallelism.
    assert sequential.fp1_identity() == concurrent.fp1_identity()
    assert [o.ct32_fingerprint for o in sequential.outcomes] == [
        o.ct32_fingerprint for o in concurrent.outcomes
    ]


def test_memory_budget_bounds_parallelism_but_every_combo_still_runs(tmp_path: Path) -> None:
    # A per-run peak that only fits one at a time forces enqueue-when-full; the
    # batch still completes every combination.
    admitted = _admit()
    report = _batch(
        admitted,
        tmp_path,
        combo_slices=_good_slices,
        cpu_budget=8,
        memory_budget=_PEAK,  # memory_budget // peak == 1
        projected_peak_memory=_PEAK,
    )
    assert report.completed_count == 4


# --- AC3: a combo's typed refusal is its line and never aborts the batch -------


def test_stream_set_violation_is_that_combos_aborted_line_and_batch_continues(
    tmp_path: Path,
) -> None:
    admitted = _admit()
    victim = admitted.combos[1]

    def _slices(combo: SweepRunSpec) -> tuple[tuple[SliceObservation, ...], ...]:
        if combo.fp1_identity() == victim.fp1_identity():
            return ((_ok(SliceObservation.try_create("NOT-A-STREAM", _instant(), True)),),)
        return _good_slices(combo)

    report = _batch(admitted, tmp_path, combo_slices=_slices, cpu_budget=2)

    assert report.run_count == 4  # the whole batch ran
    assert report.completed_count == 3
    assert report.refused_count == 1

    root = _ledger(tmp_path).root
    aborted = _ok(qmb.read_merge_view(root, world=World.REPLAY, role="aborted"))
    assert len(aborted) == 1
    assert aborted[0].refusal is not None  # refusal context recorded
    assert aborted[0].sweep_coordinates is not None
    victim_fp = _ok(victim.fingerprint())
    victim_config = _ok(admitted.compile_combo(victim, **_run_settings()))
    assert aborted[0].run_id == victim_config.fingerprint
    del victim_fp
    # The Book bar (confirmation) sees only the survivors.
    bar = _ok(qmb.read_book_bar(root, world=World.REPLAY))
    assert len(bar) == 3
    assert all(line.role == "confirmation" for line in bar)

    refused = [o for o in report.outcomes if o.status == STATUS_REFUSED]
    assert len(refused) == 1
    assert refused[0].refusal is not None
    assert refused[0].role == "aborted"


def test_run_larger_than_budget_is_each_combos_refused_line(tmp_path: Path) -> None:
    # A projected peak that exceeds the whole memory budget can never be admitted;
    # each combination is a refused line and the batch still returns a report.
    admitted = _admit()
    report = _ok(
        run_sweep_batch(
            admitted,
            output_root=_runs(tmp_path),
            ledger=_ledger(tmp_path),
            combo_slices=_good_slices,
            projected_peak_memory=4096,
            cpu_budget=4,
            memory_budget=1024,
            **_run_settings(),
        )
    )
    assert report.run_count == 4
    assert report.completed_count == 0
    assert report.refused_count == 4
    root = _ledger(tmp_path).root
    confirmation = _ok(qmb.read_merge_view(root, world=World.REPLAY, role="confirmation"))
    aborted = _ok(qmb.read_merge_view(root, world=World.REPLAY, role="aborted"))
    assert confirmation == ()
    assert len(aborted) == 4
    assert all(line.refusal is not None for line in aborted)


# --- AC4: world is provenance-derived (replay); no verdict-bearing edge claim --


def test_world_is_replay_and_no_verdict_is_stored(tmp_path: Path) -> None:
    admitted = _admit()
    report = _batch(admitted, tmp_path, combo_slices=_good_slices)
    assert all(outcome.world is World.REPLAY for outcome in report.outcomes)
    lines = _confirmation_lines(tmp_path)
    for line in lines:
        assert line.world is World.REPLAY
        assert "verdict" not in line.fp1_identity()
        assert "pass" not in line.fp1_identity()
        assert "fail" not in line.fp1_identity()


# --- sweep coordinates + identity ---------------------------------------------


def test_sweep_coordinates_are_grouped_by_sweep_instrument_and_param_hash() -> None:
    admitted = _admit()
    a, b = admitted.combos[0], admitted.combos[1]  # same instrument, different lookback
    coords_a = _ok(sweep_coordinates_of(admitted, a))
    coords_b = _ok(sweep_coordinates_of(admitted, b))
    assert coords_a["sweep_id"] == coords_b["sweep_id"] == admitted.label.sweep_id.value
    assert coords_a["class"] == SWEEP_COORDINATES_CLASS
    if a.instrument == b.instrument:
        assert coords_a["param_hash"] != coords_b["param_hash"]
    # Same parameter assignment on a different instrument keeps the param hash.
    same_params = [c for c in admitted.combos if c.parameters == a.parameters and c is not a]
    if same_params:
        other = _ok(sweep_coordinates_of(admitted, same_params[0]))
        assert other["param_hash"] == coords_a["param_hash"]
        assert other["instrument"] != coords_a["instrument"]


def test_identity_constants_and_reexport() -> None:
    identity = sweep_batch_identity()
    assert identity["one_line_per_combo"] is BATCH_ONE_LINE_PER_COMBO is True
    assert identity["aborts_on_combo_refusal"] is BATCH_ABORTS_ON_COMBO_REFUSAL is False
    assert identity["governor_bound"] == "min-cpu-memory"
    assert qmb.run_sweep_batch is run_sweep_batch is api.run_sweep_batch


# --- structural refusals are returned, never raised ---------------------------


def test_structural_inputs_are_typed_refusals(tmp_path: Path) -> None:
    admitted = _admit()
    not_admitted = run_sweep_batch(
        object(),
        output_root=_runs(tmp_path),
        ledger=_ledger(tmp_path),
        combo_slices=_good_slices,
        projected_peak_memory=_PEAK,
        cpu_budget=1,
        memory_budget=_GIB,
    )
    assert is_refusal(not_admitted)
    assert not_admitted.category is RefusalCategory.INVALID_INPUT

    bad_ledger = run_sweep_batch(
        admitted,
        output_root=_runs(tmp_path),
        ledger=object(),
        combo_slices=_good_slices,
        projected_peak_memory=_PEAK,
        cpu_budget=1,
        memory_budget=_GIB,
    )
    assert is_refusal(bad_ledger)

    missing_peak = run_sweep_batch(
        admitted,
        output_root=_runs(tmp_path),
        ledger=_ledger(tmp_path),
        combo_slices=_good_slices,
        projected_peak_memory=None,
        cpu_budget=1,
        memory_budget=_GIB,
    )
    assert is_refusal(missing_peak)

    bad_root = run_sweep_batch(
        admitted,
        output_root=str(tmp_path / "does-not-exist"),
        ledger=_ledger(tmp_path),
        combo_slices=_good_slices,
        projected_peak_memory=_PEAK,
        cpu_budget=1,
        memory_budget=_GIB,
    )
    assert is_refusal(bad_root)

    bad_slices = run_sweep_batch(
        admitted,
        output_root=_runs(tmp_path),
        ledger=_ledger(tmp_path),
        combo_slices=object(),
        projected_peak_memory=_PEAK,
        cpu_budget=1,
        memory_budget=_GIB,
    )
    assert is_refusal(bad_slices)
