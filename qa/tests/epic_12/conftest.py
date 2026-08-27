"""Make the sibling ``_world`` fixture module importable from every Epic 12 test.

The qa test tree is not an installed package; add this directory to ``sys.path``
so ``import _world`` resolves regardless of pytest's import-mode. Mirrors the
sibling epics' conftest files. This file adds NO fixtures and asserts nothing —
it is import plumbing only.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
