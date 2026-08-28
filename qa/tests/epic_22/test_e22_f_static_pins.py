"""Epic 22 — static / doc gates and the NFR-11 failure-register pin (T22-PIN-02).

L0 static gate over ``qmb/FAILURES.md``: NFR-11 / L27 make a failure-register entry a
Tier-1 artifact obligation on every story that ships a designed failure mode — a
designed failure with no register entry is an incomplete story, the same way a missing
test is. Epic 22 ships several designed failure modes; this pin asserts the register
carries an entry for each. It is EXPECTED TO FAIL against current source (zero Epic-22
entries) — the failure IS the recorded finding F-22-02, never worked around.
"""

from __future__ import annotations

import re

from conftest import WORKTREE_ROOT

FAILURES_MD = WORKTREE_ROOT / "qmb" / "FAILURES.md"

_REQUIRED_FAILURE_FIELDS = frozenset(
    {
        "Failure class",
        "Detection",
        "Auto-recovery / retry",
        "Visible degraded state",
        "Notification tier",
        "Product-user affordance",
    }
)
_FIELD = re.compile(r"(?m)^- \*\*(?P<name>[^*]+):\*\*\s+(?P<value>\S.*)$")

# Exact entry-title fragments bind the gate to each designed mode. A coincidental keyword in
# another story's entry cannot discharge an Epic-22 obligation.
_EPIC_22_DESIGNED_FAILURES = {
    "unset required robustness input",
    "synthetic perturbation persistence is forbidden",
    "replay clock on synthetic persisted data",
    "insufficient observations for significance",
    "float carve-out magnitude overflow",
}


def _failure_entries() -> dict[str, dict[str, str]]:
    sections = re.split(r"(?m)^### ", FAILURES_MD.read_text(encoding="utf-8"))[1:]
    entries: dict[str, dict[str, str]] = {}
    for section in sections:
        title, separator, body = section.partition("\n")
        assert separator, f"failure-register entry has no body: {title!r}"
        fields = {match["name"]: match["value"] for match in _FIELD.finditer(body)}
        missing = _REQUIRED_FAILURE_FIELDS - fields.keys()
        assert not missing, (
            f"failure-register entry {title!r} omits required fields: {sorted(missing)}"
        )
        entries[title.lower()] = fields
    assert entries, "qmb/FAILURES.md contains no failure-register entries"
    return entries


def test_t22_pin02_failures_register_covers_epic_22_designed_failures_FINDING_F_22_02():
    """qmb/FAILURES.md must carry an NFR-11 register entry for each Epic-22 designed failure.

    Counter-case: a loose robustness keyword in an older story, or an Epic-22 heading
    without one of the six NFR-11 fields, does not satisfy this gate.
    """
    assert FAILURES_MD.exists(), f"{FAILURES_MD} is missing entirely"
    entries = _failure_entries()
    missing = {
        mode for mode in _EPIC_22_DESIGNED_FAILURES if not any(mode in title for title in entries)
    }
    assert not missing, (
        "qmb/FAILURES.md ships no complete six-field entry for these Epic-22 designed "
        f"failure modes (finding F-22-02): {sorted(missing)}"
    )
