"""Make this directory importable so ``import _fixtures`` resolves under any
pytest import mode. Adds nothing to the QMX import path — qmb/qmf resolve via
the root pyproject ``[tool.pytest.ini_options] pythonpath``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
