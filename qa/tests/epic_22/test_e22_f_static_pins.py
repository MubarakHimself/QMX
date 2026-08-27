"""Epic 22 — static / doc gates and the NFR-11 failure-register pin (T22-PIN-02).

L0 static gate over ``qmb/FAILURES.md``: NFR-11 / L27 make a failure-register entry a
Tier-1 artifact obligation on every story that ships a designed failure mode — a
designed failure with no register entry is an incomplete story, the same way a missing
test is. Epic 22 ships several designed failure modes; this pin asserts the register
carries an entry for each. It is EXPECTED TO FAIL against current source (zero Epic-22
entries) — the failure IS the recorded finding F-22-02, never worked around.
"""

from __future__ import annotations

from conftest import WORKTREE_ROOT

FAILURES_MD = WORKTREE_ROOT / "qmb" / "FAILURES.md"

# The Epic-22 designed failure modes (from the Story 22.1-22.4 ACs and finding F-22-01),
# each keyed to keywords that a genuine register entry would carry.
_EPIC_22_DESIGNED_FAILURES = {
    "unset-required-input invalid (22.1)": ("robust", "significan", "shuffle", "perturb", "walk-forward"),
    "synthetic-persistence policy rejection (22.3)": ("synthetic", "persist"),
    "replay-clock-on-synthetic invalid (22.3)": ("replay clock", "synthetic-tainted"),
    "insufficient-data refusal (22.4)": ("minimum-observation", "insufficient"),
    "overflow -> typed refusal (F-22-01)": ("overflow", "carve"),
}


def test_t22_pin02_failures_register_covers_epic_22_designed_failures_FINDING_F_22_02():
    """qmb/FAILURES.md must carry an NFR-11 register entry for each Epic-22 designed failure.

    Counter-case: the register mentions none of the Epic-22 robustness failure modes —
    which is exactly the current state (entries exist only for stories 14-19). EXPECTED
    TO FAIL, recording finding F-22-02 (a designed failure with no register entry is an
    incomplete story). A single robustness keyword anywhere would satisfy the weakest
    form of this gate; even that is absent.
    """
    assert FAILURES_MD.exists(), f"{FAILURES_MD} is missing entirely"
    text = FAILURES_MD.read_text(encoding="utf-8").lower()

    covered = {
        mode: any(keyword.lower() in text for keyword in keywords)
        for mode, keywords in _EPIC_22_DESIGNED_FAILURES.items()
    }
    missing = [mode for mode, present in covered.items() if not present]
    assert missing == [], (
        "qmb/FAILURES.md ships no NFR-11 failure-register entry for these Epic-22 designed "
        f"failure modes (finding F-22-02): {missing}"
    )
