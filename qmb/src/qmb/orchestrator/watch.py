"""Orchestrator-owned OS-process abort: cancel and per-run limit watchdog (B-5).

The library ``run()`` stays pure and cooperatively inspects cancel/limits at
slice boundaries (story 14.6). This module is the impure owner of *detecting*
a breach or cancel on a live child and *killing that OS process* — never a
sibling, never a silent kill, never a partial governed result.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Final, cast

try:
    import resource as _resource
except ImportError:  # Windows — peak memory is GetProcessMemoryInfo
    _resource = None

from qmf.core.chrono import Duration
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import policy, unavailable
from qmb.runloop.observe import (
    MEMORY_LIMIT_KEY,
    PARTIAL_GOVERNED_RESULT_ON_ABORT,
    TERMINAL_ABORTED,
    TIME_LIMIT_KEY,
    CancelToken,
    LimitProbe,
    RunLimits,
    RunProgress,
    check_slice_boundary,
)

__all__ = [
    "ABORT_KILLS_SIBLINGS",
    "ENFORCEMENT",
    "WATCH_POLL_S",
    "ProcessLimitProbe",
    "check_process_abort",
    "is_aborted_refusal",
    "kill_owned_process",
    "monotonic_ns",
    "process_memory_bytes",
    "refuse_aborted_process",
]

ABORT_KILLS_SIBLINGS: Final[bool] = False
ENFORCEMENT: Final[str] = "orchestrator-os-process"
WATCH_POLL_S: Final[float] = 0.05
_LEDGER_ROLE_ABORTED: Final[str] = "aborted"
_PROC_STATUS: Final[str] = "status"


def monotonic_ns() -> int:
    """Boot-scoped monotonic nanoseconds. Composition-root clock read (AR-16)."""
    return time.monotonic_ns()  # ambient-scan: allow - orchestrator composition root


class ProcessLimitProbe:
    """Impure :class:`~qmb.runloop.observe.LimitProbe` over one OS process.

    Elapsed time is monotonic nanoseconds since construction (AR-16). Memory
    is the child's peak working set / VmHWM in bytes. The library loop never
    constructs this; only the orchestrator (parent or isolated worker) does.
    """

    __slots__ = ("_pid", "_started_ns")

    def __init__(self, pid: int, started_ns: int) -> None:
        self._pid = pid
        self._started_ns = started_ns

    @classmethod
    def for_pid(cls, pid: int, *, started_ns: int | None = None) -> ProcessLimitProbe:
        """Probe ``pid``. ``started_ns`` defaults to now (monotonic)."""
        started = monotonic_ns() if started_ns is None else started_ns
        return cls(pid, started)

    @classmethod
    def for_current_process(cls) -> ProcessLimitProbe:
        """Probe this process — the isolated worker's composition-root meter."""
        return cls.for_pid(os.getpid())

    def elapsed(self) -> Result[Duration]:
        """Monotonic Duration since the probe started."""
        now = monotonic_ns()
        delta = max(now - self._started_ns, 0)
        return Duration.try_create(delta)

    def memory_bytes(self) -> Result[int]:
        """Peak-or-current memory of the probed process, in bytes."""
        return process_memory_bytes(self._pid)


def process_memory_bytes(pid: int) -> Result[int]:
    """Read one process's peak working set (Windows) or VmHWM (Linux)."""
    if pid <= 0:
        return unavailable(
            "memory_bytes",
            "a process memory probe needs a positive pid",
            given=pid,
            memory_limit_key=MEMORY_LIMIT_KEY,
        )
    if sys.platform == "win32":
        return _windows_peak_working_set(pid)
    status = Path("/proc") / str(pid) / _PROC_STATUS
    if status.is_file():
        return _linux_vmhwm(status, pid)
    if pid == os.getpid():
        return _self_rusage()
    return unavailable(
        "memory_bytes",
        "the orchestrator could not read the child process peak memory",
        pid=pid,
        memory_limit_key=MEMORY_LIMIT_KEY,
        platform=sys.platform,
    )


def kill_owned_process(process: object) -> None:
    """Terminate one ``Popen`` process. Does not walk or signal siblings."""
    poll = getattr(process, "poll", None)
    kill = getattr(process, "kill", None)
    communicate = getattr(process, "communicate", None)
    if not callable(poll) or not callable(kill):
        return
    if poll() is None:
        try:
            kill()
        except OSError:
            return
    if callable(communicate):
        try:
            communicate()
        except OSError:
            return


def is_aborted_refusal(value: object) -> bool:
    """True when ``value`` is the typed ``aborted`` terminal refusal."""
    context = getattr(value, "context", None)
    if not isinstance(context, Mapping):
        return False
    mapping = cast("Mapping[str, object]", context)
    return mapping.get("terminal") == TERMINAL_ABORTED


def refuse_aborted_process(
    *,
    cause: str,
    run_id: str,
    output_dir: str,
    pid: int,
    progress: RunProgress | None = None,
    extra: Mapping[str, object] | None = None,
) -> TypedRefusal:
    """Typed ``aborted`` after the orchestrator killed this OS process (B-5)."""
    watching = (
        progress
        if progress is not None
        else RunProgress(
            data_points_processed=0,
            slices_completed=0,
            is_warming_up=False,
        )
    )
    fields: dict[str, object] = {
        "terminal": TERMINAL_ABORTED,
        "cause": cause,
        "cancel_at": "slice-boundary",
        "data_points_processed": watching.data_points_processed,
        "is_warming_up": watching.is_warming_up,
        "slices_completed": watching.slices_completed,
        "ledger_role": _LEDGER_ROLE_ABORTED,
        "partial_governed_result": PARTIAL_GOVERNED_RESULT_ON_ABORT,
        "writes_ledger": False,
        "writes_log": False,
        "killed_os_process": True,
        "sibling_processes_touched": ABORT_KILLS_SIBLINGS,
        "enforcement": ENFORCEMENT,
        "pid": pid,
        "run_id": run_id,
        "output_dir": output_dir,
        "time_limit_key": TIME_LIMIT_KEY,
        "memory_limit_key": MEMORY_LIMIT_KEY,
    }
    if extra is not None:
        fields.update(extra)
    return policy(
        "terminal",
        "the orchestrator aborted this run and killed its OS process; no partial "
        "governed result is emitted and sibling processes are not touched "
        "(B-4, B-5, FM-6)",
        **fields,
    )


def check_process_abort(
    *,
    cancel: CancelToken,
    limits: RunLimits,
    probe: LimitProbe | None,
    progress: RunProgress | None = None,
) -> Result[None]:
    """Inspect cancel and limits for a live OS process. Ok means keep running.

    A typed ``aborted`` means the orchestrator must kill this process. A memory
    meter that cannot read yet is skipped for this poll (the process may still
    be starting); other refusals propagate.
    """
    watching = (
        progress
        if progress is not None
        else RunProgress(
            data_points_processed=0,
            slices_completed=0,
            is_warming_up=False,
        )
    )
    checked = check_slice_boundary(
        cancel=cancel,
        limits=limits,
        probe=probe,
        progress=watching,
    )
    if not is_refusal(checked):
        return Ok(None)
    if is_aborted_refusal(checked):
        return checked
    field = checked.context.get("field")
    if field in {"memory_bytes", "probe"} and limits.memory_limit_bytes is not None:
        # Child may not be queryable for a tick after spawn; retry next poll.
        if limits.time_limit is None:
            return Ok(None)
        time_only = RunLimits(time_limit=limits.time_limit, memory_limit_bytes=None)
        timed = check_slice_boundary(
            cancel=cancel,
            limits=time_only,
            probe=probe,
            progress=watching,
        )
        if not is_refusal(timed):
            return Ok(None)
        return timed
    return checked


def _windows_peak_working_set(pid: int) -> Result[int]:
    process_query_information = 0x0400
    process_vm_read = 0x0010
    process_query_limited = 0x1000

    class _Counters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_Counters),
        ctypes.c_uint32,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int

    access = process_query_limited | process_query_information | process_vm_read
    handle = kernel32.OpenProcess(access, 0, pid)
    if not handle:
        return unavailable(
            "memory_bytes",
            "the orchestrator could not open the child process for a peak-memory probe",
            pid=pid,
            memory_limit_key=MEMORY_LIMIT_KEY,
        )
    try:
        counters = _Counters()
        counters.cb = ctypes.sizeof(counters)
        ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if not ok:
            return unavailable(
                "memory_bytes",
                "GetProcessMemoryInfo could not read the child peak working set",
                pid=pid,
                memory_limit_key=MEMORY_LIMIT_KEY,
            )
        return Ok(int(counters.PeakWorkingSetSize))
    finally:
        kernel32.CloseHandle(handle)


def _linux_vmhwm(status: Path, pid: int) -> Result[int]:
    try:
        text = status.read_text(encoding="utf-8")
    except OSError as exc:
        return unavailable(
            "memory_bytes",
            "the orchestrator could not read /proc status for the child peak memory",
            given=type(exc).__name__,
            pid=pid,
            memory_limit_key=MEMORY_LIMIT_KEY,
        )
    for line in text.splitlines():
        if line.startswith("VmHWM:") or line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                kilobytes = int(parts[1])
                return Ok(kilobytes * 1024)
            break
    return unavailable(
        "memory_bytes",
        "the /proc status file did not carry VmHWM/VmRSS for the child",
        pid=pid,
        memory_limit_key=MEMORY_LIMIT_KEY,
    )


def _self_rusage() -> Result[int]:
    if _resource is None:
        return unavailable(
            "memory_bytes",
            "this platform has no resource.getrusage; the orchestrator reads "
            "peak memory via the native process API",
            memory_limit_key=MEMORY_LIMIT_KEY,
            platform=sys.platform,
        )
    getter = getattr(_resource, "getrusage", None)
    rusage_self = getattr(_resource, "RUSAGE_SELF", None)
    if not callable(getter) or rusage_self is None:
        return unavailable(
            "memory_bytes",
            "resource.getrusage is unavailable on this interpreter",
            memory_limit_key=MEMORY_LIMIT_KEY,
            platform=sys.platform,
        )
    usage: object = getter(rusage_self)
    peak = int(getattr(usage, "ru_maxrss", 0))
    # Linux reports kiB; macOS reports bytes.
    if sys.platform == "darwin":
        return Ok(peak)
    return Ok(peak * 1024)
