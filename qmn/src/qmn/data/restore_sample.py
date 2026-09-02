"""``qmn-restore-sample.timer`` oneshot — nightly sample restore drill.

ExecStart: ``python -m qmn.data.restore_sample``. Factory tests drive
:func:`qmn.data.restore.run_restore_drill` against generated local-backend
fixtures. A live Backblaze B2 / clean-host rehearsal is soak-local (AR-87).
The unit holds no trading power.
"""

from __future__ import annotations

import sys

from qmn.data.restore import main as restore_main

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Systemd oneshot for the nightly sample restore."""
    return restore_main(argv, kind="sample")


if __name__ == "__main__":
    sys.exit(main())
