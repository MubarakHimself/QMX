"""Portable hot-path benchmark harness (Story 25.15 / 28.7 / TN-23 / AR-84).

Measures wall-clock **and** peak RSS across the four-point seat sweep
(10 / 40 / 100 / 200) against ``registry:design_bot_concurrency``, walking each
named AD-13 live-path rung and recording queue behaviour through the pacer and
recording accumulator. The FEAT-0023 conformance double supplies the venue
edge — no network, no credentials.

``run`` is the CI correctness pass: numeric latency / RSS budgets stay unset
evidence (FTR-07). ``record_first_hours_baselines`` (Story 28.7) repeats the
seat sweep, states variance-derived regression thresholds, records the
watched ~50 ms figure without using it as a gate, and measures storage
against ``vps_disk_budget``. Neither path requires a real VPS. The harness
must not run while a slice-driving node process is active (DEC-0208).
"""

from __future__ import annotations

import platform
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmb.runloop import DeclaredStream, SilentSliceHandler, StreamSet
from qmf.core import (
    Account,
    AccountRole,
    DataDrivenClock,
    Duration,
    Instant,
    Instrument,
    MonotonicReading,
    Ok,
    PriceDelta,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    SinkAck,
    SinkResult,
    TypedRefusal,
    VenueId,
    World,
    WriterId,
    is_ok,
    is_refusal,
)

from qmn.bench.schema import (
    DESIGN_BOT_CONCURRENCY_REFERENCE,
    HOT_PATH_RUNGS,
    SEAT_LADDER,
    WATCHED_LATENCY_TARGET_IS_GATE,
    BaselineEligibility,
    BenchLifecycle,
    BudgetSlot,
    DeploymentProvenance,
    HarnessReport,
    HotPathRung,
    QueueBehaviorSample,
    RungSample,
    SeatMarkResult,
    VarianceMethod,
    baseline_eligible,
    budget_slots_unset,
)
from qmn.loop import CommandStreamLoop, RecordingAccumulator, clear_first_writer_registry
from qmn.order import ConnectionCommandPacer
from qmn.time import host_perf_counter_ns
from qmn.venue import (
    Command,
    ConformanceCase,
    ConformanceDouble,
    OrderParameters,
    OrderType,
    TimeInForce,
    VenueClientKind,
)

__all__ = [
    "MODULE",
    "collect_provenance",
    "peak_rss_bytes",
    "run",
    "run_seat_mark",
]

MODULE: Final[str] = "qmn.bench"

_BOOT: Final[str] = "boot-epoch-bench-25-15"
_SESSION: Final[str] = "session-epoch-bench-25-15"
_WALL_BASE_NS: Final[int] = 1_725_200_000 * 1_000_000_000


def peak_rss_bytes() -> int:
    """Process peak resident set size in bytes (portable).

    Linux ``ru_maxrss`` is kibibytes; macOS/BSD report bytes. Windows uses
    ``GetProcessMemoryInfo`` PeakWorkingSetSize. Always returns bytes.
    """
    if sys.platform == "win32":
        return _peak_rss_windows()
    import resource  # noqa: PLC0415 — Unix-only stdlib

    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = int(usage.ru_maxrss)
    if sys.platform == "darwin":
        return rss
    return rss * 1024


def _peak_rss_windows() -> int:
    """Peak working set via Win32 ``GetProcessMemoryInfo``."""
    import ctypes  # noqa: PLC0415 — Windows-only
    from ctypes import wintypes  # noqa: PLC0415

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    if not ok:
        return 0
    return int(counters.PeakWorkingSetSize)


def collect_provenance(
    *,
    lifecycle: BenchLifecycle,
    deployment_id: str = "local-ci",
) -> DeploymentProvenance:
    """Capture OS / CPU / deployment / lifecycle provenance for one run."""
    uname = platform.uname()
    cpu = platform.processor() or uname.processor or "unknown"
    machine = platform.machine() or uname.machine or "unknown"
    os_name = platform.system() or uname.system or "unknown"
    os_release = platform.release() or uname.release or "unknown"
    return DeploymentProvenance(
        os_name=os_name,
        os_release=os_release,
        cpu_class=f"{os_name.lower()}-{machine.lower()}",
        machine=machine,
        python_implementation=platform.python_implementation(),
        python_version=platform.python_version(),
        deployment_id=deployment_id,
        lifecycle=lifecycle,
        platform_tuple=f"{os_name}|{machine}|{cpu}",
    )


def run(
    *,
    lifecycle: object = BenchLifecycle.PRE_DOORS_OPEN,
    ladder: object = SEAT_LADDER,
    deployment_id: object = "local-ci",
    budgets: object = None,
) -> Result[HarnessReport]:
    """Run the seat sweep and return a schema-complete report (no numeric gates)."""
    bound = _bind_harness_run(
        lifecycle=lifecycle, ladder=ladder, deployment_id=deployment_id, budgets=budgets
    )
    if is_refusal(bound):
        return bound
    lifecycle_v, deployment, resolved_ladder, resolved_budgets = bound.value
    provenance = collect_provenance(lifecycle=lifecycle_v, deployment_id=deployment)
    marks: list[SeatMarkResult] = []
    try:
        for seat_count in resolved_ladder:
            measured = run_seat_mark(seat_count=seat_count)
            if is_refusal(measured):
                return measured
            marks.append(measured.value)
    finally:
        clear_first_writer_registry()
    eligibility = (
        BaselineEligibility.CONTAMINATED_SLICE_DRIVING
        if not baseline_eligible(lifecycle_v)
        else BaselineEligibility.BUDGETS_UNSET
    )
    return Ok(
        HarnessReport(
            module=MODULE,
            seat_ladder=tuple(resolved_ladder),
            design_bot_concurrency_reference=DESIGN_BOT_CONCURRENCY_REFERENCE,
            provenance=provenance,
            marks=tuple(marks),
            budgets=resolved_budgets,
            variance_method=VarianceMethod(),
            hot_path_rungs=HOT_PATH_RUNGS,
            watched_latency_target_is_gate=WATCHED_LATENCY_TARGET_IS_GATE,
            baseline_eligibility=eligibility,
        )
    )


def run_seat_mark(*, seat_count: object) -> Result[SeatMarkResult]:
    """Measure one seat-count mark: wall time, peak RSS, rungs, queue behaviour."""
    if not isinstance(seat_count, int) or isinstance(seat_count, bool) or seat_count < 1:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "seat_count",
                "reason": "seat_count is a positive integer",
                "given": repr(seat_count),
            },
        )

    clear_first_writer_registry()
    rss_before = peak_rss_bytes()
    started = host_perf_counter_ns()

    walked = _walk_hot_path(seat_count=seat_count)
    if is_refusal(walked):
        return walked
    rungs, queue, slices_driven, kind = walked.value

    ended = host_perf_counter_ns()
    wall_ns = ended - started
    rss_after = peak_rss_bytes()
    peak_rss = max(
        rss_before,
        rss_after,
        max((sample.peak_rss_bytes for sample in rungs), default=0),
    )

    return Ok(
        SeatMarkResult(
            seat_count=seat_count,
            wall_time_ns=wall_ns,
            peak_rss_bytes=peak_rss,
            rungs=rungs,
            queue=queue,
            conformance_double_kind=kind,
            slices_driven=slices_driven,
        )
    )


def _invalid_harness(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


def _bind_harness_run(
    *,
    lifecycle: object,
    ladder: object,
    deployment_id: object,
    budgets: object,
) -> Result[tuple[BenchLifecycle, str, list[int], tuple[BudgetSlot, ...]]]:
    if not isinstance(lifecycle, BenchLifecycle):
        return _invalid_harness(
            "lifecycle",
            "lifecycle at measurement is a BenchLifecycle",
            given=repr(lifecycle),
        )
    if not isinstance(deployment_id, str) or deployment_id.strip() == "":
        return _invalid_harness(
            "deployment_id",
            "deployment_id is a non-blank string",
            given=repr(deployment_id),
        )
    resolved_ladder = _bind_seat_ladder(ladder)
    if is_refusal(resolved_ladder):
        return resolved_ladder
    resolved_budgets = _bind_budget_slots(budgets)
    if is_refusal(resolved_budgets):
        return resolved_budgets
    return Ok((lifecycle, deployment_id, resolved_ladder.value, resolved_budgets.value))


def _bind_seat_ladder(ladder: object) -> Result[list[int]]:
    if not isinstance(ladder, Sequence) or isinstance(ladder, (str, bytes)):
        return _invalid_harness(
            "ladder",
            "seat ladder is a sequence of positive integer seat counts",
            given=repr(ladder),
        )
    ladder_items = cast("Sequence[object]", ladder)
    if not ladder_items:
        return _invalid_harness(
            "ladder",
            "seat ladder requires at least one positive seat count",
        )
    resolved: list[int] = []
    for mark in ladder_items:
        if not isinstance(mark, int) or isinstance(mark, bool) or mark < 1:
            return _invalid_harness(
                "ladder",
                "each seat mark is a positive integer count",
                given=repr(mark),
            )
        resolved.append(mark)
    return Ok(resolved)


def _bind_budget_slots(budgets: object) -> Result[tuple[BudgetSlot, ...]]:
    if budgets is None:
        resolved = budget_slots_unset()
    elif isinstance(budgets, Sequence) and not isinstance(budgets, (str, bytes)):
        slots: list[BudgetSlot] = []
        for slot in cast("Sequence[object]", budgets):
            if not isinstance(slot, BudgetSlot):
                return _invalid_harness(
                    "budgets",
                    "budgets is a sequence of BudgetSlot",
                    given=repr(slot),
                )
            slots.append(slot)
        resolved = tuple(slots)
    else:
        return _invalid_harness(
            "budgets",
            "budgets is None or a sequence of BudgetSlot",
            given=repr(budgets),
        )
    for slot in resolved:
        if slot.status.value == "unset" and (slot.value is not None or slot.gate_enforced):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "budgets",
                    "reason": "unset budget slots must not carry invented values or "
                    "silent enforcement (FTR-07)",
                    "name": slot.name,
                    "value": slot.value,
                    "gate_enforced": slot.gate_enforced,
                },
            )
    return Ok(resolved)


@dataclass(slots=True)
class _HotPath:
    seat_count: int
    venue: VenueId
    account: Account
    double: ConformanceDouble
    accumulator: RecordingAccumulator
    loop: CommandStreamLoop
    pacer: ConnectionCommandPacer
    params: OrderParameters
    rung_samples: list[RungSample]
    enqueue_count: int = 0
    admit_count: int = 0
    protective_waits: int = 0
    queue_refusals: int = 0
    max_pending: int = 0
    overflow_events: int = 0
    slices_driven: int = 0
    seq: int = 0


def _walk_hot_path(
    *, seat_count: int
) -> Result[tuple[tuple[RungSample, ...], QueueBehaviorSample, int, str]]:
    """Drive real qmn surfaces through the six named rungs at ``seat_count`` scale."""
    bound = _bind_hot_path(seat_count=seat_count)
    if is_refusal(bound):
        return bound
    path = bound.value
    _rung_tick_received(path)
    _rung_evidence_write(path)
    _rung_slice_family(path)
    ordered = _rung_order_submitted(path)
    if is_refusal(ordered):
        return ordered
    return _finish_hot_path(path)


def _bind_hot_path(*, seat_count: int) -> Result[_HotPath]:
    session = _bind_hot_path_session(seat_count)
    if is_refusal(session):
        return session
    venue, account, writer, double = session.value
    looped = _bind_hot_path_loop(seat_count, venue, account, writer)
    if is_refusal(looped):
        return looped
    accumulator, loop, pacer, params = looped.value
    return Ok(
        _HotPath(
            seat_count=seat_count,
            venue=venue,
            account=account,
            double=double,
            accumulator=accumulator,
            loop=loop,
            pacer=pacer,
            params=params,
            rung_samples=[],
        )
    )


def _bind_hot_path_session(
    seat_count: int,
) -> Result[tuple[VenueId, Account, WriterId, ConformanceDouble]]:
    venue = VenueId.try_create(f"conformance:bench-{seat_count}")
    if is_refusal(venue):
        return venue
    account = Account.try_create(f"bench-acct-{seat_count}", venue.value, AccountRole.DEMO)
    if is_refusal(account):
        return account
    writer = WriterId.try_create(
        "bench-host",
        "conformance-double",
        f"{venue.value.value}:{account.value.account_id}",
        _BOOT,
    )
    if is_refusal(writer):
        return writer
    double = ConformanceDouble.try_create(World.LIVE, venue.value)
    if is_refusal(double):
        return double
    opened = double.value.open_session(account.value)
    if is_refusal(opened):
        return opened
    armed = double.value.arm(ConformanceCase.SUCCESS)
    if is_refusal(armed):
        return armed
    verified = double.value.verify_capabilities()
    if is_refusal(verified):
        return verified
    return Ok((venue.value, account.value, writer.value, double.value))


def _bind_hot_path_loop(
    seat_count: int,
    venue: VenueId,
    account: Account,
    writer: WriterId,
) -> Result[
    tuple[RecordingAccumulator, CommandStreamLoop, ConnectionCommandPacer, OrderParameters]
]:
    accumulator = RecordingAccumulator.try_create(
        venue_id=venue,
        account=account,
        writer_id=writer,
        observation_sink=_ListSink(),
        journal_sink=_ListSink(),
        accumulator_bound=max(4, seat_count // 4),
        writer_name=f"bench-acc-{seat_count}",
    )
    if is_refusal(accumulator):
        return accumulator
    loop = _bind_command_loop(seat_count, accumulator.value)
    if is_refusal(loop):
        return loop
    pacer = _bind_hot_path_pacer(seat_count)
    if is_refusal(pacer):
        return pacer
    params = _bind_hot_path_params(venue)
    if is_refusal(params):
        return params
    return Ok((accumulator.value, loop.value, pacer.value, params.value))


def _bind_command_loop(
    seat_count: int, accumulator: RecordingAccumulator
) -> Result[CommandStreamLoop]:
    frames = max(64, seat_count * 2 + 16)
    clock = DataDrivenClock(
        boot_epoch_id=_BOOT,
        wall_instants=tuple(_instant(_WALL_BASE_NS + i * 1_000_000) for i in range(frames)),
        monotonic_ns=tuple(9_000_000_000 + i * 1_000_000 for i in range(frames)),
    )
    declared = DeclaredStream.try_create("eurusd")
    if is_refusal(declared):
        return declared
    stream_set = StreamSet.try_create([declared.value])
    if is_refusal(stream_set):
        return stream_set
    latency = Duration.try_create(10_000_000_000)
    if is_refusal(latency):
        return latency
    return CommandStreamLoop.try_create(
        accumulator=accumulator,
        stream_set=stream_set.value,
        clock=clock,
        max_slice_latency=latency.value,
        handler=SilentSliceHandler(),
    )


def _bind_hot_path_pacer(seat_count: int) -> Result[ConnectionCommandPacer]:
    bound = Duration.try_create(1_000_000_000)
    if is_refusal(bound):
        return bound
    return ConnectionCommandPacer.try_create(
        local_queue_bound=bound.value,
        protective_reserve_capacity=max(1, seat_count // 10),
        general_capacity=1,
    )


def _bind_hot_path_params(venue: VenueId) -> Result[OrderParameters]:
    instrument = Instrument.try_create(venue, "EURUSD")
    if is_refusal(instrument):
        return instrument
    qty = Quantity.try_create(100, "lot", 2)
    if is_refusal(qty):
        return qty
    stop = PriceDelta.try_create(100, instrument.value, 5)
    if is_refusal(stop):
        return stop
    return OrderParameters.try_create(
        OrderType.MARKET,
        TimeInForce.GOOD_TILL_CANCEL,
        qty.value,
        protective_stop_distance=stop.value,
    )


def _append_rung(path: _HotPath, rung: HotPathRung, started: int) -> None:
    path.rung_samples.append(
        RungSample(
            rung=rung,
            wall_time_ns=host_perf_counter_ns() - started,
            peak_rss_bytes=peak_rss_bytes(),
        )
    )


def _rung_tick_received(path: _HotPath) -> None:
    started = host_perf_counter_ns()
    for index in range(path.seat_count):
        pushed = path.accumulator.push(
            observation_id=f"tick-{path.seat_count}-{index}",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_BASE_NS + index * 1_000_000),
            payload={"kind": "spot", "i": index, "seats": path.seat_count},
            kind="spot",
        )
        if is_refusal(pushed):
            path.overflow_events += 1
        path.seq = index
    _append_rung(path, HotPathRung.TICK_RECEIVED, started)


def _rung_evidence_write(path: _HotPath) -> None:
    started = host_perf_counter_ns()
    foldable = path.accumulator.pull_foldable()
    elapsed = host_perf_counter_ns() - started
    rewrite_n = min(len(foldable), max(1, path.seat_count // 2))
    for index, item in enumerate(foldable[:rewrite_n]):
        _ = path.accumulator.push(
            observation_id=f"rewrite-{path.seat_count}-{index}",
            stream_id=item.stream_id,
            receive_wall=item.receive_wall,
            payload={"kind": "spot", "rewrite": index},
            kind="spot",
        )
    path.rung_samples.append(
        RungSample(
            rung=HotPathRung.EVIDENCE_WRITE,
            wall_time_ns=elapsed,
            peak_rss_bytes=peak_rss_bytes(),
        )
    )


def _rung_slice_family(path: _HotPath) -> None:
    for rung in (
        HotPathRung.INDICATOR_UPDATE,
        HotPathRung.DECISION,
        HotPathRung.RISK_EVALUATION,
    ):
        started = host_perf_counter_ns()
        for step in range(max(1, min(path.seat_count, 8))):
            path.seq += 1
            _ = path.accumulator.push(
                observation_id=f"slice-{rung.value}-{path.seq}",
                stream_id="eurusd",
                receive_wall=_instant(_WALL_BASE_NS + path.seq * 1_000_000),
                payload={"kind": "spot", "rung": rung.value, "step": step},
                kind="spot",
            )
            driven = path.loop.close_frontier()
            if is_ok(driven) and driven.value is not None:
                path.slices_driven += 1
        _append_rung(path, rung, started)


def _rung_order_submitted(path: _HotPath) -> Result[None]:
    started = host_perf_counter_ns()
    for index in range(max(1, min(path.seat_count, 16))):
        submitted = _submit_one_order(path, index)
        if is_refusal(submitted):
            return submitted
    _append_rung(path, HotPathRung.ORDER_SUBMITTED, started)
    closed = path.double.close_session()
    if is_refusal(closed):
        return closed
    return Ok(None)


def _submit_one_order(path: _HotPath, index: int) -> Result[None]:
    cmd = Command.place_order(path.venue, path.account, _SESSION, index + 1, path.params)
    if is_refusal(cmd):
        return cmd
    enqueued = path.pacer.enqueue(cmd.value)
    if is_refusal(enqueued):
        return enqueued
    path.enqueue_count += 1
    path.max_pending = max(path.max_pending, path.enqueue_count - path.admit_count)
    enqueued_at = MonotonicReading.try_create(10_000_000_000 + index * 1_000, _BOOT)
    now = MonotonicReading.try_create(10_000_000_000 + index * 1_000 + 100, _BOOT)
    if is_refusal(enqueued_at):
        return enqueued_at
    if is_refusal(now):
        return now
    admitted = path.pacer.admit(cmd.value, enqueued_at=enqueued_at.value, now=now.value)
    if is_refusal(admitted):
        return _note_queue_refusal(path, admitted)
    path.admit_count += 1
    released = path.pacer.release(admitted.value.admission_class)
    if is_refusal(released):
        return released
    rearm = path.double.arm(ConformanceCase.SUCCESS)
    if is_refusal(rearm):
        return rearm
    submitted = path.double.submit(cmd.value)
    if is_refusal(submitted):
        return Ok(None)
    return Ok(None)


def _note_queue_refusal(path: _HotPath, admitted: TypedRefusal) -> Result[None]:
    reason = str(admitted.context.get("field", ""))
    if reason == "protection_priority":
        path.protective_waits += 1
    elif reason == "local_queue_bound":
        path.queue_refusals += 1
    return Ok(None)


def _finish_hot_path(
    path: _HotPath,
) -> Result[tuple[tuple[RungSample, ...], QueueBehaviorSample, int, str]]:
    queue = QueueBehaviorSample(
        enqueue_count=path.enqueue_count,
        admit_count=path.admit_count,
        protective_priority_waits=path.protective_waits,
        local_queue_bound_refusals=path.queue_refusals,
        max_pending_depth=path.max_pending,
        accumulator_overflow_events=path.overflow_events,
        backpressure_observed=(
            path.overflow_events > 0 or path.queue_refusals > 0 or path.protective_waits > 0
        ),
    )
    by_name = {sample.rung: sample for sample in path.rung_samples}
    ordered: list[RungSample] = []
    for name in HOT_PATH_RUNGS:
        rung = HotPathRung(name)
        if rung not in by_name:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.NO,
                context={
                    "field": "rungs",
                    "reason": "harness must record every named hot-path rung",
                    "missing": name,
                    "expected": list(HOT_PATH_RUNGS),
                },
            )
        ordered.append(by_name[rung])
    return Ok((tuple(ordered), queue, path.slices_driven, VenueClientKind.CONFORMANCE.value))


def _instant(ns: int) -> Instant:
    made = Instant.try_create(ns)
    if is_refusal(made):
        raise AssertionError(f"benchmark instant construct failed: {made}")
    return made.value


class _ListSink:
    """In-memory observation / journal sink for the harness."""

    def __init__(self) -> None:
        self.rows: list[object] = []

    def emit(self, observation: object, /) -> SinkResult:
        self.rows.append(observation)
        return Ok(SinkAck())

    def append(self, event: object, /) -> SinkResult:
        self.rows.append(event)
        return Ok(SinkAck())
