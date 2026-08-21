"""MUST NOT FLAG: the composition root may read the system clock to build the real
Clock it injects — it declares itself with the auditable allow directive.
"""

# ambient-scan: allow — composition root: constructs the real production clock that
# is injected below; the reads here are the sanctioned exception to FR-002.
from __future__ import annotations

import time
from datetime import datetime, timezone


class RealClock:
    boot_epoch_id = "boot-0"

    def wall_now(self):
        return datetime.now(timezone.utc)

    def monotonic_now(self):
        return time.monotonic_ns()
