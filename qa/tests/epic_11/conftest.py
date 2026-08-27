"""Make the sibling ``helpers`` module importable from every Epic 11 test file.

The qa test tree is not an installed package, so add this directory to
``sys.path`` so ``import helpers`` resolves regardless of pytest's rootdir /
import-mode. Mirrors qa/tests/epic_02/conftest.py.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
