"""One isolated, fully-labeled run per combo with exactly one ledger line (Story 20.3).

An admitted sweep executes as a batch of isolated runs under the Epic 15
orchestrator. Each combination compiles to exactly one resolved run-config whose
``fp1`` is its run id, executes as one isolated OS process with its own output
directory, and writes exactly ONE ledger line — never zero, never two — carrying
the full AD-12 label, the CT-32 fingerprint, the run's raw AD-40 measures, and
the sweep coordinates ``{sweep_id, instrument, bar_spec, param_hash}`` (B-3; B-5;
B-12; B-13; spec R10, R11).

Parallelism is bounded by the resource governor's ``min(cpu, memory)`` with
enqueue-when-full; concurrency is scheduling only and never changes a single
combination's result or CT-32 fingerprint (B-5; NFR-03; spec R12). A single
combination's typed refusal — a stream-set violation, an ``invalid input``
config that never compiled, a governor ``never-fits``, or an ``aborted``
time/memory-limit breach — is recorded as that combination's labelled
``aborted``/refused ledger line with refusal context and the batch continues:
one combo's refusal never aborts the sweep (spec R12; B-4; B-12). Every
combination is a non-live run whose ``world`` is provenance-derived by the
compiler (``world=replay`` for archived reads), so no combination emits a
verdict-bearing edge claim (B-6; B-7; SC-06).

Only a hard infrastructure failure — a ledger append that could not fsync, or a
structural minting error — stops the batch, because the one-line-per-combo law
cannot then be guaranteed.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal

from qmb._refuse import invalid
from qmb.config.compiler import ResolvedRunConfig
from qmb.ledger.line import (
    ROLE_ABORTED,
    ROLE_CONFIRMATION,
    book_bar_fingerprint,
    mint_aborted_line,
    mint_aborted_line_for,
)
from qmb.orchestrator.governor import (
    ON_FULL_ENQUEUE,
    GovernedRequest,
    ResourceGovernor,
)
from qmb.orchestrator.ledger import LedgerSink, finish_run, is_factory_sandbox
from qmb.orchestrator.spawn import LiveSpawn, next_ready_run, start_run
from qmb.orchestrator.watch import kill_owned_process
from qmb.runloop.observe import CancelToken
from qmb.sweep.admit import AdmittedSweep
from qmb.sweep.axes import SweepRunSpec

__all__ = [
    "BATCH_ABORTS_ON_COMBO_REFUSAL",
    "BATCH_ONE_LINE_PER_COMBO",
    "STATUS_COMPLETED",
    "STATUS_REFUSED",
    "SWEEP_COORDINATES_CLASS",
    "SWEEP_COORDINATES_FORMAT_VERSION",
    "SweepBatchReport",
    "SweepComboOutcome",
    "run_sweep_batch",
    "sweep_batch_identity",
    "sweep_coordinates_of",
]

SWEEP_COORDINATES_CLASS: Final[str] = "qmb-sweep-coordinates"
SWEEP_COORDINATES_FORMAT_VERSION: Final[int] = 1
_PARAM_HASH_CLASS: Final[str] = "qmb-sweep-param-hash"
_COMBO_OUTCOME_CLASS: Final[str] = "qmb-sweep-combo-outcome"
_BATCH_REPORT_CLASS: Final[str] = "qmb-sweep-batch-report"

STATUS_COMPLETED: Final[str] = "completed"
STATUS_REFUSED: Final[str] = "refused"

# One combo's refusal is that combo's ledger line, never the batch's abort.
BATCH_ABORTS_ON_COMBO_REFUSAL: Final[bool] = False
BATCH_ONE_LINE_PER_COMBO: Final[bool] = True


def sweep_batch_identity() -> dict[str, object]:
    """Identity-bearing batch-execution fields. Package SemVer is omitted."""
    return {
        "aborts_on_combo_refusal": BATCH_ABORTS_ON_COMBO_REFUSAL,
        "coordinates_class": SWEEP_COORDINATES_CLASS,
        "coordinates_format_version": SWEEP_COORDINATES_FORMAT_VERSION,
        "governor_bound": "min-cpu-memory",
        "one_line_per_combo": BATCH_ONE_LINE_PER_COMBO,
        "report_class": _BATCH_REPORT_CLASS,
    }


def sweep_coordinates_of(admitted: object, combo: object) -> Result[dict[str, object]]:
    """The ``{sweep_id, instrument, bar_spec, param_hash}`` a fold groups by (spec R10).

    ``sweep_id`` is the sweep declaration's ``fp1``; ``instrument`` and
    ``bar_spec`` fix the combination's single stream and ``BarSpec``; and
    ``param_hash`` is the ``fp1`` over this combination's parameter assignment.
    A run and a sweep are the same object at different scale, so these coordinates
    are metadata on the ledger LINE — they never enter the run id (spec R13).
    """
    if not isinstance(admitted, AdmittedSweep):
        return invalid(
            "admitted",
            "sweep coordinates read the frozen sweep label of an admitted batch",
            given=repr(type(admitted).__name__),
        )
    if not isinstance(combo, SweepRunSpec):
        return invalid(
            "combo",
            "a sweep coordinate names a combination of the admitted batch",
            given=repr(type(combo).__name__),
        )
    identity = combo.fp1_identity()
    param_hash = fingerprint(
        {
            "class": _PARAM_HASH_CLASS,
            "parameter_order": identity["parameter_order"],
            "parameters": identity["parameters"],
        }
    )
    if is_refusal(param_hash):
        return param_hash
    coordinates: dict[str, object] = {
        "bar_spec": combo.timeframe.fp1_identity(),
        "class": SWEEP_COORDINATES_CLASS,
        "format_version": SWEEP_COORDINATES_FORMAT_VERSION,
        "instrument": combo.instrument,
        "param_hash": param_hash.value.value,
        "sweep_id": admitted.label.sweep_id.value,
    }
    return Ok(coordinates)


@dataclass(frozen=True, slots=True)
class SweepComboOutcome:
    """One combination's recorded outcome. Every combo has exactly one (B-4)."""

    combo_fp1: Fingerprint
    run_id: Fingerprint
    status: str
    role: str
    world: World
    sweep_coordinates: Mapping[str, object]
    ct32_fingerprint: Fingerprint | None = None
    refusal: TypedRefusal | None = None
    output_dir: str | None = None

    @property
    def completed(self) -> bool:
        """True when the combination ran and appended a completed line."""
        return self.status == STATUS_COMPLETED

    def fp1_identity(self) -> dict[str, object]:
        """Canonical, fp1-clean identity. The raw refusal object is not identity."""
        content: dict[str, object] = {
            "class": _COMBO_OUTCOME_CLASS,
            "combo_fp1": self.combo_fp1.value,
            "role": self.role,
            "run_id": self.run_id.value,
            "status": self.status,
            "sweep_coordinates": dict(self.sweep_coordinates),
            "world": self.world.value,
        }
        if self.ct32_fingerprint is not None:
            content["ct32_fingerprint"] = self.ct32_fingerprint.value
        if self.refusal is not None:
            content["refusal_category"] = self.refusal.category.value
        return content


@dataclass(frozen=True, slots=True)
class SweepBatchReport:
    """Per-combo evidence trail for one executed sweep. Outcomes in combo order."""

    sweep_id: Fingerprint
    outcomes: tuple[SweepComboOutcome, ...]

    @property
    def run_count(self) -> int:
        """The number of combinations recorded — one outcome per combo."""
        return len(self.outcomes)

    @property
    def completed_count(self) -> int:
        """Combinations that ran and appended a completed line."""
        return sum(1 for item in self.outcomes if item.completed)

    @property
    def refused_count(self) -> int:
        """Combinations recorded as an aborted/refused line."""
        return sum(1 for item in self.outcomes if not item.completed)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Concurrency never changes this content (spec R12)."""
        return {
            "class": _BATCH_REPORT_CLASS,
            "outcomes": [item.fp1_identity() for item in self.outcomes],
            "sweep_id": self.sweep_id.value,
        }


@dataclass(frozen=True, slots=True)
class _ExecEntry:
    """A compilable combination bound to its run-config, slices, and coordinates."""

    combo: SweepRunSpec
    combo_fp1: Fingerprint
    config: ResolvedRunConfig
    slices: object
    coordinates: Mapping[str, object]
    projected_peak_memory: int


@dataclass(frozen=True, slots=True)
class _LiveEntry:
    """A started combination and its live OS process."""

    entry: _ExecEntry
    spawn: LiveSpawn


def run_sweep_batch(
    admitted: object,
    *,
    output_root: object,
    ledger: object,
    combo_slices: object,
    projected_peak_memory: object,
    cpu_budget: object = None,
    memory_budget: object = None,
    budgets: object = None,
    on_full: object = ON_FULL_ENQUEUE,
    cpu_cost: object = 1,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    role: object = ROLE_CONFIRMATION,
    factory_sandbox: object = None,
) -> Result[SweepBatchReport]:
    """Execute an admitted sweep: one isolated, labelled run per combo (Story 20.3).

    Each combination compiles to one resolved run-config (fp1 = run id) and runs
    as one isolated OS process under the ``min(cpu, memory)`` governor with
    enqueue-when-full. Exactly one ledger line is appended per combination —
    completed or aborted/refused — carrying the sweep coordinates. A single
    combination's typed refusal is recorded and the batch continues; only a hard
    ledger/mint failure stops it. ``combo_slices`` supplies each combination's
    event slices (a callable ``combo -> slices`` or a mapping keyed by the
    combination's ``fp1``).
    """
    if not isinstance(admitted, AdmittedSweep):
        return invalid(
            "admitted",
            "a sweep batch executes an AdmittedSweep frozen at batch admission (B-15)",
            given=repr(type(admitted).__name__),
        )
    if not isinstance(ledger, LedgerSink):
        return invalid(
            "ledger",
            "per-combo ledger lines are appended through the orchestrator LedgerSink (B-4)",
            given=repr(type(ledger).__name__),
        )
    root = _as_output_root(output_root)
    if is_refusal(root):
        return root
    slices_for = _as_slices_provider(combo_slices)
    if is_refusal(slices_for):
        return slices_for
    peak = _positive_int("projected_peak_memory", projected_peak_memory)
    if is_refusal(peak):
        return peak
    cost = _positive_int("cpu_cost", cpu_cost)
    if is_refusal(cost):
        return cost
    governor = ResourceGovernor.try_create(
        cpu_budget, memory_budget, budgets=budgets, on_full=on_full
    )
    if is_refusal(governor):
        return governor
    sandbox = is_factory_sandbox(factory_sandbox)
    driver = _BatchDriver(
        admitted=admitted,
        output_root=root.value,
        ledger=ledger,
        slices_for=slices_for.value,
        projected_peak_memory=peak.value,
        cpu_cost=cost.value,
        governor=governor.value,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
        role=role,
        sandbox=sandbox,
    )
    return driver.run()


class _BatchDriver:
    """Instance-owned batch execution. Never module-global mutable state (DEC-0161)."""

    __slots__ = (
        "_admitted",
        "_by_run_id",
        "_condition_presets",
        "_cpu_cost",
        "_governor",
        "_invocation_flags",
        "_ledger",
        "_outcomes",
        "_output_root",
        "_projected_peak_memory",
        "_role",
        "_sandbox",
        "_slices_for",
        "_workspace_defaults",
    )

    def __init__(
        self,
        *,
        admitted: AdmittedSweep,
        output_root: Path,
        ledger: LedgerSink,
        slices_for: Callable[[SweepRunSpec], object],
        projected_peak_memory: int,
        cpu_cost: int,
        governor: ResourceGovernor,
        invocation_flags: object,
        workspace_defaults: object,
        condition_presets: object,
        role: object,
        sandbox: bool,
    ) -> None:
        self._admitted = admitted
        self._output_root = output_root
        self._ledger = ledger
        self._slices_for = slices_for
        self._projected_peak_memory = projected_peak_memory
        self._cpu_cost = cpu_cost
        self._governor = governor
        self._invocation_flags = invocation_flags
        self._workspace_defaults = workspace_defaults
        self._condition_presets = condition_presets
        self._role = role
        self._sandbox = sandbox
        self._outcomes: dict[str, SweepComboOutcome] = {}
        self._by_run_id: dict[str, _ExecEntry] = {}

    def run(self) -> Result[SweepBatchReport]:
        compiled = self._compile_all()
        if is_refusal(compiled):
            return compiled
        submitted = self._submit_all()
        if is_refusal(submitted):
            return submitted
        drained = self._drain()
        if is_refusal(drained):
            return drained
        return self._report()

    # -- phase 1: compile every combination -------------------------------

    def _compile_all(self) -> Result[None]:
        pending: list[tuple[SweepRunSpec, Fingerprint, dict[str, object], TypedRefusal]] = []
        batch_world: World | None = None
        batch_book_bar: Fingerprint | None = None
        for combo in self._admitted.combos:
            combo_fp = combo.fingerprint()
            if is_refusal(combo_fp):
                return combo_fp
            coordinates = sweep_coordinates_of(self._admitted, combo)
            if is_refusal(coordinates):
                return coordinates
            compiled = self._admitted.compile_combo(
                combo,
                invocation_flags=self._invocation_flags,
                workspace_defaults=self._workspace_defaults,
                condition_presets=self._condition_presets,
            )
            if is_refusal(compiled):
                pending.append((combo, combo_fp.value, coordinates.value, compiled))
                continue
            config = compiled.value
            if batch_world is None:
                batch_world = config.world
                bar = book_bar_fingerprint(config)
                if is_refusal(bar):
                    return bar
                batch_book_bar = bar.value
            slices = self._slices_for(combo)
            self._by_run_id[config.fingerprint.value] = _ExecEntry(
                combo=combo,
                combo_fp1=combo_fp.value,
                config=config,
                slices=slices,
                coordinates=coordinates.value,
                projected_peak_memory=self._projected_peak_memory,
            )
        return self._record_compile_refusals(pending, batch_world, batch_book_bar)

    def _record_compile_refusals(
        self,
        pending: list[tuple[SweepRunSpec, Fingerprint, dict[str, object], TypedRefusal]],
        batch_world: World | None,
        batch_book_bar: Fingerprint | None,
    ) -> Result[None]:
        for combo, combo_fp, coordinates, refusal in pending:
            del combo
            if batch_world is None or batch_book_bar is None:
                # No combination compiled: the batch has nothing runnable and the
                # miss is batch-wide (shared context/settings), not one combo's.
                return refusal
            line = mint_aborted_line_for(
                run_id=combo_fp,
                world=batch_world,
                book_bar_fp1=batch_book_bar,
                refusal=refusal,
                factory_sandbox=self._sandbox,
                sweep_coordinates=coordinates,
            )
            if is_refusal(line):
                return line
            appended = self._ledger.append(line.value)
            if is_refusal(appended):
                return appended
            self._outcomes[combo_fp.value] = SweepComboOutcome(
                combo_fp1=combo_fp,
                run_id=combo_fp,
                status=STATUS_REFUSED,
                role=ROLE_ABORTED,
                world=batch_world,
                sweep_coordinates=coordinates,
                refusal=refusal,
            )
        return Ok(None)

    # -- phase 2: submit compilable combinations to the governor ----------

    def _submit_all(self) -> Result[None]:
        refused: list[str] = []
        for run_id, entry in self._by_run_id.items():
            request = GovernedRequest.try_create(
                entry.config.fingerprint,
                entry.projected_peak_memory,
                self._cpu_cost,
            )
            if is_refusal(request):
                return request
            submitted = self._governor.submit(request.value)
            if is_refusal(submitted):
                recorded = self._record_config_refusal(entry, submitted)
                if is_refusal(recorded):
                    return recorded
                refused.append(run_id)
        for run_id in refused:
            del self._by_run_id[run_id]
        return Ok(None)

    # -- phase 3: drain — start, collect, release-then-admit --------------

    def _drain(self) -> Result[None]:
        to_start: deque[str] = deque(req.run_id.value for req in self._governor.running)
        live: dict[str, _LiveEntry] = {}
        while to_start or live:
            started = self._start_pending(to_start, live)
            if is_refusal(started):
                self._reap(live)
                return started
            if not live:
                continue
            ready = next_ready_run({run_id: entry.spawn for run_id, entry in live.items()})
            if is_refusal(ready):
                self._reap(live)
                return ready
            live_entry = live.pop(ready.value)
            finished = self._finish(live_entry)
            if is_refusal(finished):
                self._reap(live)
                return finished
            run_id = ready.value
            released = self._release(run_id, to_start)
            if is_refusal(released):
                self._reap(live)
                return released
        return Ok(None)

    def _start_pending(self, to_start: deque[str], live: dict[str, _LiveEntry]) -> Result[None]:
        while to_start:
            run_id = to_start.popleft()
            entry = self._by_run_id[run_id]
            spawned = start_run(
                config=entry.config,
                slices=entry.slices,
                output_root=self._output_root,
                cancel=CancelToken(),
            )
            if is_refusal(spawned):
                recorded = self._record_config_refusal(entry, spawned)
                if is_refusal(recorded):
                    return recorded
                released = self._release(entry.config.fingerprint.value, to_start)
                if is_refusal(released):
                    return released
                continue
            live[run_id] = _LiveEntry(entry=entry, spawn=spawned.value)
        return Ok(None)

    def _release(self, run_id: str, to_start: deque[str]) -> Result[None]:
        admitted = self._governor.release(run_id)
        if is_refusal(admitted):
            return admitted
        for admission in admitted.value:
            to_start.append(admission.run_id.value)
        return Ok(None)

    def _finish(self, live_entry: _LiveEntry) -> Result[None]:
        entry = live_entry.entry
        finished = finish_run(
            live_entry.spawn,
            config=entry.config,
            ledger=self._ledger,
            role=self._role,
            factory_sandbox=self._sandbox,
            sweep_coordinates=entry.coordinates,
        )
        if is_ok(finished):
            self._outcomes[entry.combo_fp1.value] = SweepComboOutcome(
                combo_fp1=entry.combo_fp1,
                run_id=entry.config.fingerprint,
                status=STATUS_COMPLETED,
                role=_as_role_token(self._role),
                world=entry.config.world,
                sweep_coordinates=entry.coordinates,
                ct32_fingerprint=finished.value.ct32_fingerprint,
                output_dir=finished.value.output_dir,
            )
            return Ok(None)
        if finished.context.get("writes_ledger") is True:
            self._outcomes[entry.combo_fp1.value] = SweepComboOutcome(
                combo_fp1=entry.combo_fp1,
                run_id=entry.config.fingerprint,
                status=STATUS_REFUSED,
                role=ROLE_ABORTED,
                world=entry.config.world,
                sweep_coordinates=entry.coordinates,
                refusal=finished,
                output_dir=live_entry.spawn.output_dir,
            )
            return Ok(None)
        # No ledger line was written (a storage/mint failure): the one-line law
        # cannot be met, so this is a hard batch failure, not a combo outcome.
        return finished

    def _record_config_refusal(self, entry: _ExecEntry, refusal: TypedRefusal) -> Result[None]:
        line = mint_aborted_line(
            entry.config,
            refusal,
            factory_sandbox=self._sandbox,
            sweep_coordinates=entry.coordinates,
        )
        if is_refusal(line):
            return line
        appended = self._ledger.append(line.value)
        if is_refusal(appended):
            return appended
        self._outcomes[entry.combo_fp1.value] = SweepComboOutcome(
            combo_fp1=entry.combo_fp1,
            run_id=entry.config.fingerprint,
            status=STATUS_REFUSED,
            role=ROLE_ABORTED,
            world=entry.config.world,
            sweep_coordinates=entry.coordinates,
            refusal=refusal,
            output_dir=None,
        )
        return Ok(None)

    def _reap(self, live: dict[str, _LiveEntry]) -> None:
        for live_entry in live.values():
            kill_owned_process(live_entry.spawn.process)

    def _report(self) -> Result[SweepBatchReport]:
        ordered: list[SweepComboOutcome] = []
        for combo in self._admitted.combos:
            combo_fp = combo.fingerprint()
            if is_refusal(combo_fp):
                return combo_fp
            outcome = self._outcomes.get(combo_fp.value.value)
            if outcome is None:
                return invalid(
                    "combo",
                    "every admitted combination must record exactly one outcome (B-4)",
                    combo_fp1=combo_fp.value.value,
                )
            ordered.append(outcome)
        return Ok(
            SweepBatchReport(
                sweep_id=self._admitted.label.sweep_id,
                outcomes=tuple(ordered),
            )
        )


def _as_role_token(role: object) -> str:
    if isinstance(role, str) and role.strip() != "":
        return role
    return ROLE_CONFIRMATION


def _as_output_root(value: object) -> Result[Path]:
    if isinstance(value, Path):
        root = value
    elif isinstance(value, str) and value.strip() != "":
        root = Path(value)
    else:
        return invalid(
            "output_root",
            "the batch writes each combination's isolated run directory under an "
            "existing output root",
            given=repr(type(value).__name__),
        )
    if not root.is_dir():
        return invalid(
            "output_root",
            "the batch writes each combination's isolated run directory under an "
            "existing output root",
            given=str(root),
        )
    return Ok(root)


def _as_slices_provider(value: object) -> Result[Callable[[SweepRunSpec], object]]:
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)

        def _from_mapping(combo: SweepRunSpec) -> object:
            fp = combo.fingerprint()
            if is_refusal(fp):
                return ()
            return mapping.get(fp.value.value, ())

        return Ok(_from_mapping)
    if callable(value):
        return Ok(cast("Callable[[SweepRunSpec], object]", value))
    return invalid(
        "combo_slices",
        "combo_slices is a callable combo -> slices or a mapping keyed by the combination's fp1",
        given=repr(type(value).__name__),
    )


def _positive_int(field: str, value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(
            field,
            "the governor bounds parallelism by min(cpu, memory); this is a "
            "positive integer declared by the caller (B-5)",
            given=repr(value),
        )
    return Ok(value)
