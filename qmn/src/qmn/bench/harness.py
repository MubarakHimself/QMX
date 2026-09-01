"""Portable hot-path benchmark harness (Story 25.15 / TN-23 / AR-84).

Measures wall-clock **and** peak RSS across the four-point seat sweep
(10 / 40 / 100 / 200) against ``registry:design_bot_concurrency``, walking each
named AD-13 live-path rung and recording queue behaviour through the pacer and
recording accumulator. The FEAT-0023 conformance double supplies the venue
edge — no network, no credentials.

Numeric latency / RSS budgets stay unset evidence (FTR-07). CI runs this for
correctness only; Story 28.7 records first-hours VPS baselines and closes
``[E9-F04]``. The harness must not run while a slice-driving node process is
active (DEC-0208).
"""

from __future__ import annotations

import platform
import sys
from collections.abc import Sequence
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
    if not isinstance(lifecycle, BenchLifecycle):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "lifecycle",
                "reason": "lifecycle at measurement is a BenchLifecycle",
                "given": repr(lifecycle),
            },
        )
    if not isinstance(deployment_id, str) or deployment_id.strip() == "":
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "deployment_id",
                "reason": "deployment_id is a non-blank string",
                "given": repr(deployment_id),
            },
        )
    if not isinstance(ladder, Sequence) or isinstance(ladder, (str, bytes)):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "ladder",
                "reason": "seat ladder is a sequence of positive integer seat counts",
                "given": repr(ladder),
            },
        )
    ladder_items = cast("Sequence[object]", ladder)
    if not ladder_items:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "ladder",
                "reason": "seat ladder requires at least one positive seat count",
            },
        )
    resolved_ladder: list[int] = []
    for mark in ladder_items:
        if not isinstance(mark, int) or isinstance(mark, bool) or mark < 1:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "ladder",
                    "reason": "each seat mark is a positive integer count",
                    "given": repr(mark),
                },
            )
        resolved_ladder.append(mark)

    resolved_budgets: tuple[BudgetSlot, ...]
    if budgets is None:
        resolved_budgets = budget_slots_unset()
    elif isinstance(budgets, Sequence) and not isinstance(budgets, (str, bytes)):
        budget_items = cast("Sequence[object]", budgets)
        slots: list[BudgetSlot] = []
        for slot in budget_items:
            if not isinstance(slot, BudgetSlot):
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "budgets",
                        "reason": "budgets is a sequence of BudgetSlot",
                        "given": repr(slot),
                    },
                )
            slots.append(slot)
        resolved_budgets = tuple(slots)
    else:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "budgets",
                "reason": "budgets is None or a sequence of BudgetSlot",
                "given": repr(budgets),
            },
        )
    for slot in resolved_budgets:
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

    provenance = collect_provenance(lifecycle=lifecycle, deployment_id=deployment_id)
    marks: list[SeatMarkResult] = []
    try:
        for seat_count in resolved_ladder:
            measured = run_seat_mark(seat_count=seat_count)
            if is_refusal(measured):
                return measured
            marks.append(measured.value)
    finally:
        clear_first_writer_registry()

    if not baseline_eligible(lifecycle):
        eligibility = BaselineEligibility.CONTAMINATED_SLICE_DRIVING
    else:
        # Pre-soak: eligible lifecycle, but budgets remain unset until Story 28.7.
        eligibility = BaselineEligibility.BUDGETS_UNSET

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


def _walk_hot_path(
    *, seat_count: int
) -> Result[tuple[tuple[RungSample, ...], QueueBehaviorSample, int, str]]:
    """Drive real qmn surfaces through the six named rungs at ``seat_count`` scale."""
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

    obs_sink = _ListSink()
    journal_sink = _ListSink()
    # Harness-local bound so overflow is observable; not a production budget gate.
    acc_bound = max(4, seat_count // 4)
    accumulator = RecordingAccumulator.try_create(
        venue_id=venue.value,
        account=account.value,
        writer_id=writer.value,
        observation_sink=obs_sink,
        journal_sink=journal_sink,
        accumulator_bound=acc_bound,
        writer_name=f"bench-acc-{seat_count}",
    )
    if is_refusal(accumulator):
        return accumulator

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

    # Loop requires a positive max_slice_latency; the report's budget slot stays unset.
    latency = Duration.try_create(10_000_000_000)
    if is_refusal(latency):
        return latency
    loop = CommandStreamLoop.try_create(
        accumulator=accumulator.value,
        stream_set=stream_set.value,
        clock=clock,
        max_slice_latency=latency.value,
        handler=SilentSliceHandler(),
    )
    if is_refusal(loop):
        return loop

    bound = Duration.try_create(1_000_000_000)
    if is_refusal(bound):
        return bound
    pacer = ConnectionCommandPacer.try_create(
        local_queue_bound=bound.value,
        protective_reserve_capacity=max(1, seat_count // 10),
        general_capacity=1,
    )
    if is_refusal(pacer):
        return pacer

    instrument = Instrument.try_create(venue.value, "EURUSD")
    if is_refusal(instrument):
        return instrument
    qty = Quantity.try_create(100, "lot", 2)
    if is_refusal(qty):
        return qty
    stop = PriceDelta.try_create(100, instrument.value, 5)
    if is_refusal(stop):
        return stop
    params = OrderParameters.try_create(
        OrderType.MARKET,
        TimeInForce.GOOD_TILL_CANCEL,
        qty.value,
        protective_stop_distance=stop.value,
    )
    if is_refusal(params):
        return params

    rung_samples: list[RungSample] = []
    enqueue_count = 0
    admit_count = 0
    protective_waits = 0
    queue_refusals = 0
    max_pending = 0
    overflow_events = 0
    slices_driven = 0
    seq = 0

    # --- tick_received -------------------------------------------------------
    tick_start = host_perf_counter_ns()
    for i in range(seat_count):
        pushed = accumulator.value.push(
            observation_id=f"tick-{seat_count}-{i}",
            stream_id="eurusd",
            receive_wall=_instant(_WALL_BASE_NS + i * 1_000_000),
            payload={"kind": "spot", "i": i, "seats": seat_count},
            kind="spot",
        )
        if is_refusal(pushed):
            overflow_events += 1
        seq = i
    tick_ns = host_perf_counter_ns() - tick_start
    rung_samples.append(
        RungSample(
            rung=HotPathRung.TICK_RECEIVED,
            wall_time_ns=tick_ns,
            peak_rss_bytes=peak_rss_bytes(),
        )
    )

    # --- evidence_write (journaled intake already done; pull proves foldability)
    ev_start = host_perf_counter_ns()
    foldable = accumulator.value.pull_foldable()
    ev_ns = host_perf_counter_ns() - ev_start
    # Re-push a subset so later slices have work (pull drained the queue).
    for i, item in enumerate(foldable[: min(len(foldable), max(1, seat_count // 2))]):
        _ = accumulator.value.push(
            observation_id=f"rewrite-{seat_count}-{i}",
            stream_id=item.stream_id,
            receive_wall=item.receive_wall,
            payload={"kind": "spot", "rewrite": i},
            kind="spot",
        )
    rung_samples.append(
        RungSample(
            rung=HotPathRung.EVIDENCE_WRITE,
            wall_time_ns=ev_ns,
            peak_rss_bytes=peak_rss_bytes(),
        )
    )

    # --- indicator_update / decision / risk_evaluation via close_frontier ----
    for rung in (
        HotPathRung.INDICATOR_UPDATE,
        HotPathRung.DECISION,
        HotPathRung.RISK_EVALUATION,
    ):
        rung_start = host_perf_counter_ns()
        iterations = max(1, min(seat_count, 8))
        for step in range(iterations):
            seq += 1
            _ = accumulator.value.push(
                observation_id=f"slice-{rung.value}-{seq}",
                stream_id="eurusd",
                receive_wall=_instant(_WALL_BASE_NS + seq * 1_000_000),
                payload={"kind": "spot", "rung": rung.value, "step": step},
                kind="spot",
            )
            driven = loop.value.close_frontier()
            if is_ok(driven) and driven.value is not None:
                slices_driven += 1
        rung_end = host_perf_counter_ns()
        rung_samples.append(
            RungSample(
                rung=rung,
                wall_time_ns=rung_end - rung_start,
                peak_rss_bytes=peak_rss_bytes(),
            )
        )

    # --- order_submitted via conformance double + pacer queue behaviour ------
    order_start = host_perf_counter_ns()
    for i in range(max(1, min(seat_count, 16))):
        cmd = Command.place_order(venue.value, account.value, _SESSION, i + 1, params.value)
        if is_refusal(cmd):
            return cmd
        enqueued = pacer.value.enqueue(cmd.value)
        if is_refusal(enqueued):
            return enqueued
        enqueue_count += 1
        pending_depth = enqueue_count - admit_count
        max_pending = max(max_pending, pending_depth)

        enqueued_at = MonotonicReading.try_create(10_000_000_000 + i * 1_000, _BOOT)
        now = MonotonicReading.try_create(10_000_000_000 + i * 1_000 + 100, _BOOT)
        if is_refusal(enqueued_at):
            return enqueued_at
        if is_refusal(now):
            return now
        admitted = pacer.value.admit(cmd.value, enqueued_at=enqueued_at.value, now=now.value)
        if is_refusal(admitted):
            reason = str(admitted.context.get("field", ""))
            if reason == "protection_priority":
                protective_waits += 1
            elif reason == "local_queue_bound":
                queue_refusals += 1
            continue
        admit_count += 1
        released = pacer.value.release(admitted.value.admission_class)
        if is_refusal(released):
            return released

        rearm = double.value.arm(ConformanceCase.SUCCESS)
        if is_refusal(rearm):
            return rearm
        submitted = double.value.submit(cmd.value)
        if is_refusal(submitted):
            continue
    order_end = host_perf_counter_ns()
    rung_samples.append(
        RungSample(
            rung=HotPathRung.ORDER_SUBMITTED,
            wall_time_ns=order_end - order_start,
            peak_rss_bytes=peak_rss_bytes(),
        )
    )

    closed = double.value.close_session()
    if is_refusal(closed):
        return closed

    queue = QueueBehaviorSample(
        enqueue_count=enqueue_count,
        admit_count=admit_count,
        protective_priority_waits=protective_waits,
        local_queue_bound_refusals=queue_refusals,
        max_pending_depth=max_pending,
        accumulator_overflow_events=overflow_events,
        backpressure_observed=(overflow_events > 0 or queue_refusals > 0 or protective_waits > 0),
    )
    by_name = {sample.rung: sample for sample in rung_samples}
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
    return Ok((tuple(ordered), queue, slices_driven, VenueClientKind.CONFORMANCE.value))


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
