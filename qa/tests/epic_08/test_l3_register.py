"""L3 acceptance test — the failure-register discipline (NFR-11, R-009).

Oracle: NFR-11 ("every designed failure mode ships a register entry"), AR-21/L27
(reference usage examples), and the workspace convention conventions/failure-register.md
that every OTHER roster package (qmf-core, qmf-data, qmf-indicators, qmf-registry,
qmf-structure) already follows.

Covers QA-E08-L3-015. A missing register entry is a finding (this is where R-009 gets
its evidence).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VENUE_PKG = REPO_ROOT / "packages" / "qmf-venue"

# The typed refusal categories reachable at the venue boundary, enumerated from
# CT-18/19/20/21's declared refusal-category lists. Each must have a register entry.
VENUE_BOUNDARY_REFUSALS = [
    "invalid input",
    "unsupported capability",
    "unavailable dependency",
    "policy rejection",
    "transient venue failure",
    "storage failure",
]

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


def _failure_entries(register: Path) -> list[tuple[str, dict[str, str]]]:
    sections = re.split(r"(?m)^### ", register.read_text(encoding="utf-8"))[1:]
    entries: list[tuple[str, dict[str, str]]] = []
    for section in sections:
        title, separator, body = section.partition("\n")
        assert separator, f"failure-register entry has no body: {title!r}"
        fields = {match["name"]: match["value"] for match in _FIELD.finditer(body)}
        missing = _REQUIRED_FAILURE_FIELDS - fields.keys()
        assert not missing, (
            f"failure-register entry {title!r} omits required fields: {sorted(missing)}"
        )
        entries.append((title, fields))
    assert entries, f"{register} contains no failure-register entries"
    return entries


def test_l3_015_qmf_venue_ships_a_failure_register_covering_its_refusals():
    """NFR-11/R-009: the qmf-venue distribution unit ships a FAILURES.md failure register
    (like every sibling roster package) with an entry for every typed refusal reachable at
    the venue boundary."""
    register = VENUE_PKG / "FAILURES.md"
    assert register.exists(), (
        "qmf-venue ships NO FAILURES.md failure register (NFR-11); every other roster "
        "package (qmf-core, qmf-data, qmf-indicators, qmf-registry, qmf-structure) ships "
        "one under the conventions/failure-register.md convention"
    )
    entries = _failure_entries(register)
    covered = {
        category
        for category in VENUE_BOUNDARY_REFUSALS
        if any(category in fields["Failure class"].lower() for _, fields in entries)
    }
    missing = set(VENUE_BOUNDARY_REFUSALS) - covered
    assert not missing, (
        "the venue failure register has no complete six-field entry for refusal categories: "
        f"{sorted(missing)}"
    )


def test_l3_015_qmf_venue_ships_reference_usage_examples():
    """AR-21/L27: the tier-1 distribution unit ships an examples/ directory of reference
    usage examples (like every sibling roster package); qmf-venue's is absent."""
    examples = VENUE_PKG / "examples"
    assert examples.is_dir(), (
        "qmf-venue ships NO examples/ directory (AR-21/L27); every other roster package "
        "(qmf-core, qmf-data, qmf-indicators, qmf-registry, qmf-risk, qmf-structure) ships one"
    )
