"""MUST NOT FLAG: the composition root may read the system clock to build the real
Clock it injects — each read declares itself with the line-scoped allow directive on
its own line (the directive no longer waves the whole file through).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone


class RealClock:
    boot_epoch_id = "boot-0"

    def wall_now(self):
        return datetime.now(timezone.utc)  # ambient-scan: allow - composition root builds real clock

    def monotonic_now(self):
        return time.monotonic_ns()  # ambient-scan: allow - composition root builds real clock
