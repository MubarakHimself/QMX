"""Tiny import example — `import qmb` (COMP-QMB).

Executable::

    python qmb/examples/import_usage.py

Shows the scaffold surface: display-only SemVer, the structural-seed homes,
the six backend packages, and the as-of-set registry-read port.
"""

from __future__ import annotations

import sys

from qmf.core.refusal import is_ok

import qmb


def main() -> None:
    sys.stdout.write(f"qmb {qmb.__version__}\n")
    assert qmb.MCP_SHIPPED is False
    assert qmb.STATE_KIND == "as-of set"
    assert "qmf-venue" not in qmb.BACKEND_PACKAGES
    layers = qmb.fingerprint_layers()
    assert is_ok(layers)
    sys.stdout.write("import qmb ok\n")


if __name__ == "__main__":
    main()
