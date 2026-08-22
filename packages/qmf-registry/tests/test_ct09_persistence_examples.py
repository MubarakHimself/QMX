"""The CT-09 reference-usage example must stay executable (L27, tier-1 artifact).

Runs ``examples/persistence_usage.py`` as a fresh process — the same subprocess idiom the
CT-06/CT-07 example tests use — and checks it exits clean and demonstrates the six things
CT-09 pins down against the real CT-11 store-seam: the content-addressed record round
trip, the idempotent re-write, the edge persisted on its own fp1, the cross-world and
simulated policy rejections, the storage-failure typed refusal, and the staged
never-in-place migration. The example imports ``qmf.data`` (the ratified persistence
edge), so qmf-data's src joins qmf-core and qmf-registry on the path.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE = _PKG_ROOT / "examples" / "persistence_usage.py"
_PACKAGES = _PKG_ROOT.parent
_CORE_SRC = _PACKAGES / "qmf-core" / "src"
_DATA_SRC = _PACKAGES / "qmf-data" / "src"


def test_reference_usage_example_runs_clean() -> None:
    # The example imports qmf.core, qmf.registry, and qmf.data (the ratified edge); put all
    # three src trees on the path (the example is executed as a standalone process).
    pythonpath = os.pathsep.join([str(_PKG_ROOT / "src"), str(_CORE_SRC), str(_DATA_SRC)])
    env = {**os.environ, "PYTHONPATH": pythonpath}
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "record persisted, content-addressed on fp1: fp1:sha256:" in completed.stdout
    assert "byte-identical re-write deduplicates: idempotent" in completed.stdout
    assert "lineage edge persisted on its own fp1: supersedes" in completed.stdout
    assert "cross-world read refused: policy rejection" in completed.stdout
    assert "simulated world refused: policy rejection" in completed.stdout
    assert "store failure is a typed refusal: storage failure" in completed.stdout
    assert "migration staged and never in-place: verified 2" in completed.stdout
