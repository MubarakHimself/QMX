"""Isolated child-process entry for the host sandbox runner.

The parent spawns this module with stdlib process management (``python -m
qml.host.worker``). The child collects Layer-2 observations and never computes
the verdict — the QML-owned verdict function stays parent-side.
"""

from __future__ import annotations

from qml.host.runner import worker_main

if __name__ == "__main__":
    raise SystemExit(worker_main())
