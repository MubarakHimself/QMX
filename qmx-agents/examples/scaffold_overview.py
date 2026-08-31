"""Workspace-root example: import the three QMA packages (structural seed)."""

from __future__ import annotations

import qma.core
import qma.daemon
import qma.wire


def main() -> None:
    versions = (
        qma.core.__version__,
        qma.wire.__version__,
        qma.daemon.__version__,
    )
    assert versions == ("0.1.0", "0.1.0", "0.1.0")
    print("qma-core / qma-wire / qma-daemon structural seed OK")


if __name__ == "__main__":
    main()
