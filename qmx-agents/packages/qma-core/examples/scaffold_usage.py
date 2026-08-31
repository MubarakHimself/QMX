"""L27 reference usage stub for the qma-core structural seed."""

from __future__ import annotations

import qma.core


def main() -> None:
    assert qma.core.__version__ == "0.1.0"
    print(f"qma.core {qma.core.__version__} (definitions only)")


if __name__ == "__main__":
    main()
