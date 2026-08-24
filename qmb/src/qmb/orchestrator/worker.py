"""Isolated child-process entry for one orchestrator-spawned run (B-5).

The parent spawns this module with stdlib process management
(``python -m qmb.orchestrator.worker <output-dir>``). The child drives the
library's pure ``run()`` over the resolved run-config and writes only into
the isolated output directory named by the run id.
"""

from __future__ import annotations

from qmb.orchestrator.spawn import worker_main

if __name__ == "__main__":
    raise SystemExit(worker_main())
