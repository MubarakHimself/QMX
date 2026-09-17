"""Three legal authoring entries; none a toll booth (Story 51.4).

(1) QMB ungoverned Python — zero QML
(2) QML ``gate_registration`` — CT-33 + Python, no Stage 0
(3) Stage 0 save then ``graduate_to_governed`` — requires hypothesis ``research_ref``

Auto-mint of CT-33/CT-34 from DNA / graph.yaml / hypothesis package is refused.
Conformance never gates tunnel entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core.refusal import Ok, Result, TypedRefusal

from qml._refuse import invalid, policy

__all__ = [
    "AUTO_MINT_SOURCES",
    "LEGAL_AUTHORING_ENTRIES",
    "LegalAuthoringEntries",
    "enumerate_legal_authoring_entries",
    "gate_registration_requires_stage0",
    "refuse_auto_mint",
    "refuse_entry_toll_booth",
]

LEGAL_AUTHORING_ENTRIES: Final[tuple[str, ...]] = (
    "ungoverned-python",
    "gate_registration",
    "stage0-graduate",
)

AUTO_MINT_SOURCES: Final[frozenset[str]] = frozenset(
    {
        "dna",
        "graph.yaml",
        "graph_yaml",
        "hypothesis_package",
        "hypothesis-package",
        "layout-demo",
        "layout_demo",
    }
)


@dataclass(frozen=True, slots=True)
class LegalAuthoringEntries:
    """Closed roster of legal entries; none toll-booths another."""

    entries: tuple[str, ...] = LEGAL_AUTHORING_ENTRIES
    toll_booth: bool = False
    gate_registration_requires_stage0: bool = False
    conformance_gates_tunnel_entry: bool = False

    def to_payload(self) -> MappingProxyType[str, object]:
        return MappingProxyType(
            {
                "entries": list(self.entries),
                "toll_booth": self.toll_booth,
                "gate_registration_requires_stage0": self.gate_registration_requires_stage0,
                "conformance_gates_tunnel_entry": self.conformance_gates_tunnel_entry,
                "descriptions": {
                    "ungoverned-python": "QMB ungoverned Python — zero QML",
                    "gate_registration": "QML gate_registration — CT-33 + Python, no Stage 0",
                    "stage0-graduate": (
                        "Stage 0 save then graduate_to_governed — requires hypothesis research_ref"
                    ),
                },
            }
        )


def enumerate_legal_authoring_entries() -> Result[LegalAuthoringEntries]:
    """Enumerate the three legal entries; none is a toll booth for the others."""
    return Ok(LegalAuthoringEntries())


def gate_registration_requires_stage0() -> bool:
    """UX-DR6: ``gate_registration`` must work without opening Stage 0."""
    return False


def refuse_entry_toll_booth(
    *,
    required_entry: object,
    for_entry: object,
) -> TypedRefusal:
    """Refuse making one legal entry a precondition for another."""
    return policy(
        "authoring_entry",
        "the three legal authoring entries are not toll booths for each other "
        "(FR-RES-24; DEC-0387)",
        required_entry=repr(required_entry),
        for_entry=repr(for_entry),
        legal=list(LEGAL_AUTHORING_ENTRIES),
        toll_booth=False,
    )


def refuse_auto_mint(
    *,
    source: object,
    target: object = "ct-33",
) -> Result[None]:
    """Refuse auto-mint of CT-33/CT-34 from DNA / graph.yaml / hypothesis package."""
    token: str
    if isinstance(source, str) and source.strip() != "":
        token = source.casefold().strip().replace("\\", "/")
    else:
        return invalid(
            "source",
            "auto-mint refusal names a source (dna | graph.yaml | hypothesis package)",
            given=repr(source),
        )
    base = token.rsplit("/", maxsplit=1)[-1]
    looks_like_auto = any(
        tip in token
        for tip in ("dna", "graph.yaml", "hypothesis", "layout-demo", "graph_yaml")
    )
    if (
        base not in AUTO_MINT_SOURCES
        and token not in AUTO_MINT_SOURCES
        and not looks_like_auto
    ):
        return invalid(
            "source",
            "auto-mint refusal names dna, graph.yaml, or a hypothesis package",
            given=token,
            known=sorted(AUTO_MINT_SOURCES),
        )
    target_token = target if isinstance(target, str) else type(target).__name__
    return policy(
        "declaration",
        "auto-mint of CT-33/CT-34 from DNA, graph.yaml, or a hypothesis package is "
        "refused; executable artifacts appear only when a human (or human-approved "
        "QML authoring) produces CT-33/34 + logic (FR-RES-13; DEC-0409)",
        source=token,
        target=target_token,
        mints_ct33=False,
        mints_ct34=False,
        legal_entries=list(LEGAL_AUTHORING_ENTRIES),
    )
