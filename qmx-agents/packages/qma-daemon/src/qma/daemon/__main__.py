"""Process entry for the composed qma-daemon (Story 36.1; FR-W09).

Not an operator command line: mutating acts arrive over the CT-40 wire.
QMB remains the platform's single CLI (DEC-0336).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from qma.daemon.process import DEFAULT_BIND_PORT, DaemonProcess
from qmf.core import is_refusal


def main() -> int:
    root = Path(os.environ.get("QMA_DAEMON_ROOT", "qma-daemon-data"))
    machine = os.environ.get("QMA_DAEMON_MACHINE", "workstation")
    boot = os.environ.get("QMA_DAEMON_BOOT_EPOCH", "boot")
    port_raw = os.environ.get("QMA_DAEMON_BIND_PORT", str(DEFAULT_BIND_PORT))
    try:
        bind_port = int(port_raw)
    except ValueError:
        return 2
    composed = DaemonProcess.compose(
        root,
        machine=machine,
        boot_epoch_id=boot,
        bind_port=bind_port,
    )
    if is_refusal(composed):
        return 2
    process = composed.value
    try:
        served = asyncio.run(process.serve())
        if is_refusal(served):
            return 2
        return 0
    except KeyboardInterrupt:
        return 0
    finally:
        process.close()


if __name__ == "__main__":
    raise SystemExit(main())
