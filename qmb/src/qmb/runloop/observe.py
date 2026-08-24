"""Cooperative cancel, in-loop progress, and per-run time/memory limits (B-4, B-5).

The library ``run()`` stays pure: a caller-owned cancel token is inspected at
slice boundaries, progress is published to a caller-owned observer, and
time/memory breaches are detected through an injected :class:`LimitProbe`.
Nothing here writes a log or a ledger line; an abort is a typed terminal
refusal whose ``terminal=aborted`` context is what Epic 15 renders as the
``aborted`` ledger line. No threads.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core.chrono import Duration, Instant
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import clean_token, invalid, policy
from qmb.config.compiler import ResolvedRunConfig

__all__ = [
    "CANCEL_AT",
    "CAUSE_CANCEL",
    "CAUSE_MEMORY_LIMIT",
    "CAUSE_TIME_LIMIT",
    "MEMORY_LIMIT_KEY",
    "PARTIAL_GOVERNED_RESULT_ON_ABORT",
    "TERMINAL_ABORTED",
    "TERMINAL_COMPLETE",
    "TIME_LIMIT_KEY",
    "CancelToken",
    "LimitProbe",
    "ProgressObserver",
    "ProgressSink",
    "RunLimits",
    "RunProgress",
    "ScriptedLimitProbe",
    "check_slice_boundary",
    "limits_from_config",
    "refuse_aborted",
]

CANCEL_AT: Final[str] = "slice-boundary"
CAUSE_CANCEL: Final[str] = "cancel"
CAUSE_TIME_LIMIT: Final[str] = "time-limit"
CAUSE_MEMORY_LIMIT: Final[str] = "memory-limit"
TERMINAL_ABORTED: Final[str] = "aborted"
TERMINAL_COMPLETE: Final[str] = "complete"
PARTIAL_GOVERNED_RESULT_ON_ABORT: Final[bool] = False
TIME_LIMIT_KEY: Final[str] = "qmb_run_time_limit"
MEMORY_LIMIT_KEY: Final[str] = "qmb_run_memory_limit"
_LEDGER_ROLE_ABORTED: Final[str] = "aborted"

_TIME_KEYS: Final[tuple[str, ...]] = ("time_limit", TIME_LIMIT_KEY)
_MEMORY_KEYS: Final[tuple[str, ...]] = ("memory_limit_bytes", MEMORY_LIMIT_KEY)


class CancelToken:
    """Caller-owned cooperative cancel flag. Signalled from the same thread.

    Not a ``threading.Event``, not module-global, and not a ledger writer.
    The loop inspects :attr:`is_cancelled` at the next slice boundary.
    """

    __slots__ = ("_cancelled", "_cause")

    def __init__(self) -> None:
        self._cancelled = False
        self._cause = CAUSE_CANCEL

    @property
    def is_cancelled(self) -> bool:
        """True after :meth:`cancel` has been called."""
        return self._cancelled

    @property
    def cause(self) -> str:
        """The cause token recorded by :meth:`cancel`, default ``cancel``."""
        return self._cause

    def cancel(self, cause: object = CAUSE_CANCEL) -> Result[None]:
        """Signal stop. The current slice finishes; the next slice does not start."""
        token = clean_token(cause)
        if token is None:
            return invalid(
                "cause",
                "a cancel cause is a non-empty token (cancel, time-limit, or memory-limit)",
                given=repr(cause),
            )
        self._cancelled = True
        self._cause = token
        return Ok(None)


@dataclass(frozen=True, slots=True)
class RunProgress:
    """Operational progress at a slice boundary. Not a governed result (B-4)."""

    data_points_processed: int
    slices_completed: int
    is_warming_up: bool
    frontier: Instant | None = None
    elapsed: Duration | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content: dict[str, object] = {
            "data_points_processed": self.data_points_processed,
            "is_warming_up": self.is_warming_up,
            "slices_completed": self.slices_completed,
        }
        if self.frontier is not None:
            content["frontier_ns"] = self.frontier.value_ns
        if self.elapsed is not None:
            content["elapsed_ns"] = self.elapsed.value_ns
        return content

    @classmethod
    def try_create(
        cls,
        data_points_processed: object,
        slices_completed: object,
        is_warming_up: object,
        frontier: object = None,
        elapsed: object = None,
    ) -> Result[RunProgress]:
        """Validate one progress reading."""
        points = _nonneg_int("data_points_processed", data_points_processed)
        if is_refusal(points):
            return points
        slices = _nonneg_int("slices_completed", slices_completed)
        if is_refusal(slices):
            return slices
        if not isinstance(is_warming_up, bool):
            return invalid(
                "is_warming_up",
                "progress exposes is_warming_up as a bool while the loop runs",
                given=repr(is_warming_up),
            )
        if frontier is not None and not isinstance(frontier, Instant):
            return invalid(
                "frontier",
                "progress frontier is an Instant or None",
                given=repr(type(frontier).__name__),
            )
        if elapsed is not None and not isinstance(elapsed, Duration):
            return invalid(
                "elapsed",
                "progress elapsed is a monotonic Duration or None; wall Instants "
                "never measure a run-time limit (AR-16)",
                given=repr(type(elapsed).__name__),
            )
        return Ok(
            cls(
                data_points_processed=points.value,
                slices_completed=slices.value,
                is_warming_up=is_warming_up,
                frontier=frontier,
                elapsed=elapsed,
            )
        )


@runtime_checkable
class ProgressObserver(Protocol):
    """Caller-owned progress consumer. Invoked at slice boundaries only."""

    def observe(self, progress: RunProgress) -> Result[None]:  # pragma: no cover - protocol seam
        """Accept the latest progress. Must not write a log or ledger."""
        ...


class ProgressSink:
    """Latest-progress holder. The loop writes here; the caller reads :attr:`latest`."""

    __slots__ = ("_latest",)

    def __init__(self) -> None:
        self._latest = RunProgress(
            data_points_processed=0,
            slices_completed=0,
            is_warming_up=False,
        )

    @property
    def latest(self) -> RunProgress:
        """Most recently published progress. Not a governed result."""
        return self._latest

    def observe(self, progress: object) -> Result[None]:
        """Store ``progress`` as the latest reading."""
        if not isinstance(progress, RunProgress):
            return invalid(
                "progress",
                "a progress observer consumes a RunProgress value",
                given=repr(type(progress).__name__),
            )
        self._latest = progress
        return Ok(None)


@dataclass(frozen=True, slots=True)
class RunLimits:
    """Per-run time and memory bounds. Values come from the run, never spine defaults.

    Keys: ``registry:qmb_run_time_limit`` and ``registry:qmb_run_memory_limit``.
    Absent means unbounded. Breach is a typed ``aborted`` (B-5).
    """

    time_limit: Duration | None = None
    memory_limit_bytes: int | None = None

    @property
    def bounded(self) -> bool:
        """True when at least one bound is declared."""
        return self.time_limit is not None or self.memory_limit_bytes is not None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        content: dict[str, object] = {
            "memory_limit_key": MEMORY_LIMIT_KEY,
            "time_limit_key": TIME_LIMIT_KEY,
        }
        if self.time_limit is not None:
            content["time_limit_ns"] = self.time_limit.value_ns
        if self.memory_limit_bytes is not None:
            content["memory_limit_bytes"] = self.memory_limit_bytes
        return content

    @classmethod
    def try_create(
        cls,
        time_limit: object = None,
        memory_limit_bytes: object = None,
    ) -> Result[RunLimits]:
        """Validate declared per-run bounds. ``None`` on a field means unbounded."""
        if isinstance(time_limit, RunLimits):
            if memory_limit_bytes is not None:
                return invalid(
                    "limits",
                    "a RunLimits value is the complete bound set; do not also pass "
                    "memory_limit_bytes",
                )
            return Ok(time_limit)
        if isinstance(time_limit, Mapping):
            if memory_limit_bytes is not None:
                return invalid(
                    "limits",
                    "mapping form already carries both bounds; do not also pass memory_limit_bytes",
                )
            return _limits_from_mapping(cast("Mapping[str, object]", time_limit))
        parsed_time = _as_time_limit(time_limit)
        if is_refusal(parsed_time):
            return parsed_time
        parsed_mem = _as_memory_limit(memory_limit_bytes)
        if is_refusal(parsed_mem):
            return parsed_mem
        return Ok(cls(time_limit=parsed_time.value, memory_limit_bytes=parsed_mem.value))


@runtime_checkable
class LimitProbe(Protocol):
    """Injected monotonic elapsed-time and memory readings (AR-16, AD-15).

    The library never reads the system clock or a process meter. The
    composition root injects this probe; tests inject a :class:`ScriptedLimitProbe`.
    """

    def elapsed(self) -> Result[Duration]:  # pragma: no cover - protocol seam
        """Elapsed monotonic Duration since the run started."""
        ...

    def memory_bytes(self) -> Result[int]:  # pragma: no cover - protocol seam
        """Peak-or-current memory reading in bytes."""
        ...


class ScriptedLimitProbe:
    """Pure, scripted :class:`LimitProbe`. Last reading holds when the script ends."""

    __slots__ = ("_elapsed", "_elapsed_i", "_memory", "_memory_i")

    def __init__(
        self,
        *,
        elapsed_ns: Sequence[int] = (0,),
        memory_bytes: Sequence[int] = (0,),
    ) -> None:
        elapsed = tuple(elapsed_ns) if elapsed_ns else (0,)
        memory = tuple(memory_bytes) if memory_bytes else (0,)
        self._elapsed = elapsed
        self._memory = memory
        self._elapsed_i = 0
        self._memory_i = 0

    def elapsed(self) -> Result[Duration]:
        """Next scripted elapsed Duration; the last reading repeats."""
        ns = self._next(self._elapsed, self._elapsed_i)
        self._elapsed_i += 1
        return Duration.try_create(ns)

    def memory_bytes(self) -> Result[int]:
        """Next scripted memory reading; the last reading repeats."""
        value = self._next(self._memory, self._memory_i)
        self._memory_i += 1
        return Ok(value)

    @staticmethod
    def _next(script: tuple[int, ...], index: int) -> int:
        if index >= len(script):
            return script[-1]
        return script[index]


def limits_from_config(config: object) -> Result[RunLimits | None]:
    """Read per-run limits from the resolved run-config keys.

    Omitted keys mean the caller did not declare bounds (the loop then runs
    unbounded unless the caller passes ``limits``).
    """
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "per-run time and memory limits are read from a resolved run-config",
            given=repr(type(config).__name__),
        )
    time_key = next((key for key in _TIME_KEYS if key in config.keys), None)
    mem_key = next((key for key in _MEMORY_KEYS if key in config.keys), None)
    if time_key is None and mem_key is None:
        return Ok(None)
    parsed = _limits_from_mapping(config.keys)
    if is_refusal(parsed):
        return parsed
    found: RunLimits | None = parsed.value
    return Ok(found)


def refuse_aborted(
    *,
    cause: str,
    progress: RunProgress,
    **extra: object,
) -> TypedRefusal:
    """Typed terminal refusal: no partial governed result (B-4, FR-037)."""
    return policy(
        "terminal",
        "the run stopped cooperatively at a slice boundary; no partial governed "
        "result is emitted (B-4, FR-037)",
        terminal=TERMINAL_ABORTED,
        cause=cause,
        cancel_at=CANCEL_AT,
        data_points_processed=progress.data_points_processed,
        is_warming_up=progress.is_warming_up,
        slices_completed=progress.slices_completed,
        ledger_role=_LEDGER_ROLE_ABORTED,
        partial_governed_result=PARTIAL_GOVERNED_RESULT_ON_ABORT,
        writes_ledger=False,
        writes_log=False,
        **extra,
    )


def check_slice_boundary(
    *,
    cancel: CancelToken | None,
    limits: RunLimits,
    probe: LimitProbe | None,
    progress: RunProgress,
) -> Result[Duration | None]:
    """Inspect cancel and limits at a slice boundary. Returns elapsed, or aborted."""
    if cancel is not None and cancel.is_cancelled:
        return refuse_aborted(cause=cancel.cause, progress=progress)
    elapsed: Duration | None = None
    if probe is not None:
        reading = probe.elapsed()
        if is_refusal(reading):
            return reading
        elapsed = reading.value
    if limits.time_limit is not None:
        if elapsed is None:
            return invalid(
                "probe",
                "in-loop time-limit detection needs an injected LimitProbe; the "
                "library never reads the system clock (AR-16, B-5)",
                time_limit_key=TIME_LIMIT_KEY,
            )
        if elapsed.value_ns >= limits.time_limit.value_ns:
            return refuse_aborted(
                cause=CAUSE_TIME_LIMIT,
                progress=progress,
                time_limit_key=TIME_LIMIT_KEY,
                time_limit_ns=limits.time_limit.value_ns,
                elapsed_ns=elapsed.value_ns,
            )
    if limits.memory_limit_bytes is not None:
        if probe is None:
            return invalid(
                "probe",
                "in-loop memory-limit detection needs an injected LimitProbe; the "
                "library never reads a process meter (AD-15, B-5)",
                memory_limit_key=MEMORY_LIMIT_KEY,
            )
        memory = probe.memory_bytes()
        if is_refusal(memory):
            return memory
        observed = _nonneg_int("memory_bytes", memory.value)
        if is_refusal(observed):
            return observed
        if observed.value >= limits.memory_limit_bytes:
            return refuse_aborted(
                cause=CAUSE_MEMORY_LIMIT,
                progress=progress,
                memory_limit_key=MEMORY_LIMIT_KEY,
                memory_limit_bytes=limits.memory_limit_bytes,
                observed_bytes=observed.value,
            )
    return Ok(elapsed)


def _limits_from_mapping(mapping: Mapping[str, object]) -> Result[RunLimits]:
    time_key = next((key for key in _TIME_KEYS if key in mapping), None)
    mem_key = next((key for key in _MEMORY_KEYS if key in mapping), None)
    time_raw = mapping[time_key] if time_key is not None else None
    mem_raw = mapping[mem_key] if mem_key is not None else None
    return RunLimits.try_create(time_raw, mem_raw)


def _as_time_limit(value: object) -> Result[Duration | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Duration):
        duration = value
    else:
        parsed = Duration.try_create(value)
        if is_refusal(parsed):
            return invalid(
                TIME_LIMIT_KEY,
                "a per-run time limit is a non-negative Duration of monotonic "
                "nanoseconds, or None when unbounded (B-5)",
                given=repr(value),
            )
        duration = parsed.value
    if duration.value_ns < 0:
        return invalid(
            TIME_LIMIT_KEY,
            "a per-run time limit is a non-negative Duration; a negative bound "
            "cannot be a wall-time limit (B-5)",
            given=duration.value_ns,
        )
    return Ok(duration)


def _as_memory_limit(value: object) -> Result[int | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(
            MEMORY_LIMIT_KEY,
            "a per-run memory limit is a non-negative byte count, or None when unbounded (B-5)",
            given=repr(value),
        )
    return Ok(value)


def _nonneg_int(field: str, value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(
            field,
            "progress counters are non-negative integers",
            given=repr(value),
        )
    return Ok(value)
