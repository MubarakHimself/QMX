"""``qmn-restore-full.timer`` oneshot — monthly full-integrity restore drill.

ExecStart: ``python -m qmn.data.restore_full``. Restores into scratch only.
Factory tests drive :func:`qmn.data.restore.run_restore_drill` against
generated local-backend fixtures. Host-loss rehearsal is the
``restore_drill_run`` power, not this timer (DEC-0252).
The unit holds no trading power.
"""

from __future__ import annotations

import sys

from qmn.data.restore import main as restore_main

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Systemd oneshot for the monthly full restore into scratch."""
    return restore_main(argv, kind="full")


if __name__ == "__main__":
    sys.exit(main())
