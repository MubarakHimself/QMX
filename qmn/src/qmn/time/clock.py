"""Injected VPS OS clock — sole stamper of QMX-owned event times (TN-14).

Constructed only at the composition root. Nothing below the root reads host
local time or the system clock; callers consume :class:`~qmf.core.Clock`
(DEC-0106, AR-16). Stored stamps are UTC nanoseconds.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Final, cast

from qmf.core import Instant, MonotonicReading, Ok, Result
from qmf.core.refusal import is_refusal

from qmn.time._refuse import clean_token, invalid

__all__ = [
    "VPS_CLOCK_SURFACE",
    "VpsClock",
    "host_perf_counter_ns",
]

VPS_CLOCK_SURFACE: Final[str] = "qmn.time"


def host_perf_counter_ns() -> int:
    """Composition-root elapsed-time reader for the TN-23 bench harness.

    Wall-clock event stamps still go through :meth:`VpsClock.from_host_os`.
    The harness measures host elapsed time only via this marked factory.
    """
    return time.perf_counter_ns()  # ambient-scan: allow - composition-root VPS clock


class VpsClock:
    """Production :class:`~qmf.core.Clock` over the VPS OS clock (TN-14).

    Wall readings are UTC nanosecond :class:`~qmf.core.Instant` values. Monotonic
    readings stay boot-scoped diagnostics. The composition root builds this via
    :meth:`from_host_os` (the only ambient-clock construction site) or injects
    pure callables for tests — never ``datetime.now`` / local-time below the root.
    """

    def __init__(
        self,
        *,
        boot_epoch_id: str,
        wall_ns: Callable[[], object],
        monotonic_ns: Callable[[], object],
    ) -> None:
        self.boot_epoch_id: str = boot_epoch_id
        self._wall_ns: Callable[[], object] = wall_ns
        self._monotonic_ns: Callable[[], object] = monotonic_ns

    @classmethod
    def try_create(
        cls,
        *,
        boot_epoch_id: object,
        wall_ns: object,
        monotonic_ns: object,
    ) -> Result[VpsClock]:
        """Validate and bind an injectable VPS clock (no ambient read here)."""
        boot = clean_token(boot_epoch_id)
        if boot is None:
            return invalid(
                "boot_epoch_id",
                "a VPS clock carries a non-empty boot/epoch id",
                given=repr(boot_epoch_id),
            )
        if not callable(wall_ns):
            return invalid(
                "wall_ns",
                "wall_ns is a zero-arg callable returning UTC nanoseconds",
                given=repr(type(wall_ns).__name__),
            )
        if not callable(monotonic_ns):
            return invalid(
                "monotonic_ns",
                "monotonic_ns is a zero-arg callable returning monotonic nanoseconds",
                given=repr(type(monotonic_ns).__name__),
            )
        return Ok(
            cls(
                boot_epoch_id=boot,
                wall_ns=cast("Callable[[], object]", wall_ns),
                monotonic_ns=cast("Callable[[], object]", monotonic_ns),
            )
        )

    @classmethod
    def from_host_os(cls, *, boot_epoch_id: object) -> Result[VpsClock]:
        """Composition-root factory: bind the VPS OS clock (TN-14 sole stamper).

        The ambient reads live only on the marked lines below. Child modules
        receive the resulting :class:`~qmf.core.Clock` and never call this.
        """

        def wall() -> int:
            return time.time_ns()  # ambient-scan: allow - composition-root VPS clock

        def mono() -> int:
            return time.monotonic_ns()  # ambient-scan: allow - composition-root VPS clock

        return cls.try_create(
            boot_epoch_id=boot_epoch_id,
            wall_ns=wall,
            monotonic_ns=mono,
        )

    def wall_now(self) -> Result[Instant]:
        """Current wall Instant as UTC nanoseconds (value-or-refusal)."""
        raw = self._wall_ns()
        if isinstance(raw, bool) or not isinstance(raw, int):
            return invalid(
                "wall_ns",
                "wall reader must return an int UTC-nanosecond count",
                given=repr(raw),
            )
        return Instant.try_create(raw)

    def monotonic_now(self) -> Result[MonotonicReading]:
        """Current boot-scoped monotonic reading (value-or-refusal)."""
        raw = self._monotonic_ns()
        if isinstance(raw, bool) or not isinstance(raw, int):
            return invalid(
                "monotonic_ns",
                "monotonic reader must return an int nanosecond count",
                given=repr(raw),
            )
        return MonotonicReading.try_create(raw, self.boot_epoch_id)

    def stamp_utc_ns(self) -> Result[int]:
        """UTC nanosecond stamp for QMX-owned evidence (never local time)."""
        wall = self.wall_now()
        if is_refusal(wall):
            return wall
        return Ok(wall.value.value_ns)
