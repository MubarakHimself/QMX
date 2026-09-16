"""Operator-principal seed-corpus ``root_path`` law (FR-RES-01; NFR-RES-06).

``root_path`` homes on plugin/daemon load config as a filesystem path. It is
not an environment variable, not a git path inside the QMX worktree, not a
venue secret, and not a qmb setting.
"""

from __future__ import annotations

from pathlib import Path

from qmf.core import Ok, Result
from qmf.data.store.refusals import invalid_input

__all__ = [
    "qmx_worktree_root",
    "validate_seed_root_path",
]


def qmx_worktree_root() -> Path | None:
    """Return the QMX git worktree that contains this package, if any."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
    return None


def validate_seed_root_path(root_path: object) -> Result[Path]:
    """Accept an absolute filesystem path; refuse env / git / secret / qmb homes."""
    if not isinstance(root_path, str) or root_path.strip() == "":
        return invalid_input(
            "root_path",
            "root_path is a non-empty filesystem path on operator-principal "
            "plugin/daemon load config (NFR-RES-06; DEC-0388)",
            given=repr(root_path),
        )
    raw = root_path.strip()
    if raw.startswith("cred://"):
        return invalid_input(
            "root_path",
            "root_path is not a venue secret (NFR-RES-06; DEC-0388)",
            given=raw,
        )
    if raw.startswith("$") or (raw.startswith("%") and raw.endswith("%")):
        return invalid_input(
            "root_path",
            "root_path is not an environment variable (NFR-RES-06; DEC-0388)",
            given=raw,
        )
    lowered = raw.lower()
    if lowered.startswith("qmb.") or lowered.startswith("qmb:"):
        return invalid_input(
            "root_path",
            "root_path is not a qmb setting (NFR-RES-06; DEC-0388)",
            given=raw,
        )
    path = Path(raw)
    if not path.is_absolute():
        return invalid_input(
            "root_path",
            "root_path is an absolute filesystem path on plugin/daemon load "
            "config, not a relative git path or setting key (NFR-RES-06; DEC-0388)",
            given=raw,
        )
    worktree = qmx_worktree_root()
    if worktree is not None:
        try:
            path.resolve().relative_to(worktree.resolve())
        except ValueError:
            pass
        else:
            return invalid_input(
                "root_path",
                "root_path is not a git path inside the QMX worktree "
                "(NFR-RES-06; DEC-0388; DEC-0410)",
                given=raw,
                worktree=str(worktree),
            )
    return Ok(path)
