"""Lane-entry authority gate (FC-35 / QMX-F037, GAP-QA-01).

Every QA lane brief names its authority files (the L0-L6 taxonomy, the 15
P0/P1 assertions, the risk-gate ids). In the 2026-08-27 QA phase the
`_bmad-output/test-artifacts/` tree was absent from the verification
worktree and 16 of 23 lanes independently confirmed it — every lane then
RECONSTRUCTED the taxonomy from its brief, so every per-lane P0/P1 label was
self-assigned rather than read from the authority.

This gate makes that failure impossible to repeat silently: it FAILS when a
brief names an authority path that does not resolve in the worktree, so a
lane can never proceed on a reconstruction. It runs as part of the
`qa-verify` gate (see qa/run_qa_verify.py).
"""

from __future__ import annotations

import re
from pathlib import Path

_QA_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _QA_ROOT.parent
_AUTHORITY_REF = re.compile(r"_bmad-output/test-artifacts[A-Za-z0-9/._-]*")


def _briefs() -> list[Path]:
    return sorted(_QA_ROOT.glob("epics/epic_*/PLAN.md"))


def test_lane_briefs_exist() -> None:
    """The gate has something to guard: every epic lane ships a PLAN brief."""
    briefs = _briefs()
    if len(briefs) < 23:
        raise AssertionError(
            f"expected the 23 per-epic lane briefs, found {len(briefs)}"
        )


def test_every_authority_path_named_in_a_brief_resolves() -> None:
    """A brief-named authority file that does not resolve FAILS lane entry.

    16 of 23 lanes recorded the authority tree absent in the QA phase; this
    assertion turns that recorded absence into a hard gate, so a lane brief
    can never again proceed on a reconstructed taxonomy (QMX-F037).
    """
    missing: list[str] = []
    referenced: set[str] = set()
    for brief in _briefs():
        text = brief.read_text(encoding="utf-8")
        for match in _AUTHORITY_REF.finditer(text):
            token = match.group(0).rstrip("/.")
            referenced.add(token)
            if not (_REPO_ROOT / token).exists():
                missing.append(f"{brief.relative_to(_REPO_ROOT)} -> {token}")
    if not referenced:
        raise AssertionError(
            "no brief names an authority path; the gate would be vacuous"
        )
    if missing:
        raise AssertionError(
            "lane briefs name authority files that do not resolve in this "
            "worktree; a lane must never proceed on a reconstructed taxonomy "
            "(QMX-F037, GAP-QA-01): " + "; ".join(sorted(set(missing)))
        )


def test_the_named_authorities_are_readable_and_nonempty() -> None:
    """The shipped authority files are real content, not placeholder stubs."""
    for token in (
        "_bmad-output/test-artifacts/test-design-qa.md",
        "_bmad-output/test-artifacts/test-design/QMX-handoff.md",
    ):
        path = _REPO_ROOT / token
        if not path.is_file():
            raise AssertionError(f"authority file missing: {token}")
        if len(path.read_text(encoding="utf-8")) <= 1_000:
            raise AssertionError(f"authority file suspiciously small: {token}")
