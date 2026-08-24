"""Story 11.7 — AD-5 migration notes for the CT-22 / CT-23 format-version-2 mints.

An incompatible contract-format change mints the next integer version plus a
migration note; history stays append-only and readable forever (DEC-0103, AD-5).
These notes are the mandatory migration record for the QML-authored, qmf-risk-owned
format-2 mints (DEC-0181, DEC-0182):

* CT-22 format 2 adds **exactly three things** over format 1, and nothing more.
* CT-23 format 2 adds **exactly one OPTIONAL** entry-intent field, and nothing more.
* Pre-mint format-1 Book definitions and intents stay readable forever at format 1.
* A format-1 reader confronting a format-2 artifact refuses ``unsupported
  capability``, never a best-effort read.
* The two new admission-bar ``evidence_requirements`` fields land **only** through
  the CT-22 mint — never as a silent AD-30 field addition a format-1 parser would
  ignore, admitting the evidence they exist to refuse (DEC-0178).
* Thresholds behind the new admission-bar interfaces stay GAP-0048/GAP-0049
  (interfaces only); a not-yet-ruled requirement still passes registration and
  blocks live binding.

qmf-risk imports only ``qmf-core``; nothing imports ``qmf.risk`` (L30/DEC-0120).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "CT22_FORMAT_2_MIGRATION",
    "CT23_FORMAT_2_MIGRATION",
    "THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS",
    "FormatMigrationNote",
]


@dataclass(frozen=True, slots=True)
class FormatMigrationNote:
    """One AD-5 contract-format mint: what was added, what stays readable, what refuses."""

    contract_id: str
    from_version: int
    to_version: int
    added: tuple[str, ...]
    pre_mint_readable_versions: tuple[int, ...]
    format_1_reader_on_newer: str
    notes: str

    def fp1_identity(self) -> dict[str, object]:
        """Pinned identity content for the migration note itself (tests lock the mint)."""
        return {
            "class": "format-migration-note",
            "contract_id": self.contract_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "added": list(self.added),
            "pre_mint_readable_versions": list(self.pre_mint_readable_versions),
            "format_1_reader_on_newer": self.format_1_reader_on_newer,
        }


# Interfaces only — no ruled numeric threshold is minted here (SC-07; DEC-0178).
THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS: Final[tuple[str, str]] = ("GAP-0048", "GAP-0049")

CT22_FORMAT_2_MIGRATION: Final[FormatMigrationNote] = FormatMigrationNote(
    contract_id="CT-22",
    from_version=1,
    to_version=2,
    added=(
        "admission_bar.evidence_requirements.registered_conformant_bot_cite"
        "+canonical_assignment_evidence",
        "exit_policy.catch_all_default_entry",
        "footprint_requirements requirement-set shape filling the reserved pending slot",
    ),
    pre_mint_readable_versions=(1,),
    format_1_reader_on_newer="unsupported capability",
    notes=(
        "CT-22 format 2 (DEC-0181) is a COMP-QMF-RISK-owned shape with QML-authored "
        "semantics. It adds exactly three things over format 1: (1) two "
        "admission_bar.evidence_requirements fields — registered_conformant_bot_cite "
        "and canonical_assignment_evidence — net-new surface that lands only through "
        "this mint, never a silent AD-30 field addition; (2) one explicit optional "
        "exit_policy catch-all default entry; (3) the footprint_requirements "
        "requirement-set shape filling its reserved pending(GAP-0047) slot. Pre-mint "
        "format-1 Book definitions stay readable forever at format 1. A format-1 "
        "reader confronting a format-2 artifact refuses unsupported capability. "
        "Thresholds behind the new admission-bar fields stay GAP-0048/GAP-0049; a "
        "not-yet-ruled requirement still passes registration and blocks live binding."
    ),
)

CT23_FORMAT_2_MIGRATION: Final[FormatMigrationNote] = FormatMigrationNote(
    contract_id="CT-23",
    from_version=1,
    to_version=2,
    added=("entry.advisory_stop_proposal",),
    pre_mint_readable_versions=(1,),
    format_1_reader_on_newer="unsupported capability",
    notes=(
        "CT-23 format 2 (DEC-0182) is a COMP-QMF-RISK-owned shape with QML-authored "
        "semantics. It adds exactly one OPTIONAL entry-intent field, "
        "entry.advisory_stop_proposal — a Price(instrument) or PriceDelta(instrument) "
        "bound, advisory exactly as proposed_r is — and documents the declared "
        "full-loss price as Book-resolved at the door (the Book executes its "
        "per-family ExitLogicRef, consuming the advisory proposal and cited evidence, "
        "and stamps the derived price mirroring requested_r). Because the new field "
        "is optional, format-2 readers accept format-1 intents unchanged. Pre-mint "
        "format-1 intents stay readable forever. A format-1 reader confronting a "
        "format-2 artifact refuses unsupported capability."
    ),
)
