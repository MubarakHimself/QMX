"""Ensure the epic_07 test directory is importable so `import _fixtures` resolves.

Independent QA suite for Epic 7 (qmf-indicators). Tests live under ``qa/`` and treat
``packages/qmf-indicators`` as read-only evidence; a failing assertion is a FINDING,
never a licence to edit source.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
