"""Host-owned candidate origin and optional seed_cite (Story 51.3).

``origin`` is the frozen string ``\"qma\"`` (who minted). Optional ``seed_cite``
is a distinct non-fp1 triple citing an existing Knowledge Citation. The QML
authoring composition root is the single writer; QMA copies at register only if
the host supplied it and never invents locators. ``seed_cite`` is never inside
CT-33 / CT-34 / fp1 preimage and never grows a CT-07 edge to a Citation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal
from qmf.registry import LineageEdge

from qml._refuse import invalid, policy
from qml.conformance.registration import Graduation, RegistrationCandidate
from qml.declaration.bot import BotDefinition

__all__ = [
    "CANDIDATE_ORIGIN",
    "QMA_INVENTS_SEED_CITE",
    "SEED_CITE_FIELDS",
    "SEED_CITE_IN_FP1",
    "HostCandidate",
    "SeedCite",
    "admit_candidate_origin",
    "admit_seed_cite",
    "attach_seed_cite",
    "mint_host_candidate",
    "refuse_ct07_to_knowledge_citation",
    "refuse_qma_invented_seed_cite",
]

CANDIDATE_ORIGIN: Final[str] = "qma"
SEED_CITE_FIELDS: Final[tuple[str, ...]] = ("source_ref", "snapshot_ref", "locator")
SEED_CITE_IN_FP1: Final[bool] = False
QMA_INVENTS_SEED_CITE: Final[bool] = False


@dataclass(frozen=True, slots=True)
class SeedCite:
    """Optional seed handoff citing an existing Knowledge Citation."""

    source_ref: str
    snapshot_ref: str
    locator: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_ref": self.source_ref,
                "snapshot_ref": self.snapshot_ref,
                "locator": self.locator,
            }
        )


@dataclass(frozen=True, slots=True)
class HostCandidate:
    """Host-authored candidate envelope. ``seed_cite`` is outside fp1 preimage."""

    origin: str
    candidate: RegistrationCandidate
    seed_cite: SeedCite | None = None
    mill_graduation: Graduation | None = None
    promoted_from_edge: LineageEdge | None = None

    def fp1_identity(self) -> dict[str, object]:
        """Candidate fp1 surface — origin/seed_cite never enter preimage."""
        return dict(self.candidate.fp1_identity())

    def declaration_identity(self) -> dict[str, object]:
        return self.candidate.declaration.identity_payload()


def admit_candidate_origin(value: object = CANDIDATE_ORIGIN) -> Result[str]:
    """Admit frozen origin ``qma``; refuse reshaping into a seed locator."""
    if value is None:
        return Ok(CANDIDATE_ORIGIN)
    if not isinstance(value, str) or value.strip() == "":
        return invalid(
            "origin",
            "candidate origin is the frozen string qma (who minted)",
            given=repr(value),
            expected=CANDIDATE_ORIGIN,
        )
    token = value.strip()
    if token != CANDIDATE_ORIGIN:
        # Refuse seed-locator reshapes (path-like, cite triples, non-qma tokens).
        return policy(
            "origin",
            "origin stays the frozen string qma (who minted); it is not a seed locator",
            given=token,
            expected=CANDIDATE_ORIGIN,
        )
    return Ok(CANDIDATE_ORIGIN)


def admit_seed_cite(value: object) -> Result[SeedCite | None]:
    """Admit optional ``seed_cite`` triple or omit."""
    if value is None:
        return Ok(None)
    if isinstance(value, SeedCite):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "seed_cite",
            "seed_cite is { source_ref, snapshot_ref, locator } citing an existing "
            "Knowledge Citation",
            given=type(value).__name__,
            fields=list(SEED_CITE_FIELDS),
        )
    return _admit_seed_cite_mapping(cast("Mapping[str, object]", value))


def refuse_qma_invented_seed_cite(*, invented_by: object = "qma") -> TypedRefusal:
    """QMA never invents seed_cite locators; host is the single writer."""
    return policy(
        "seed_cite",
        "the QML authoring composition root is the single writer of seed_cite; "
        "QMA copies at register only if the host supplied it and never invents locators",
        invented_by=repr(invented_by),
        qma_invents=QMA_INVENTS_SEED_CITE,
        host_is_single_writer=True,
    )


def refuse_ct07_to_knowledge_citation(
    *,
    to_ref: object = None,
    seed_cite: object = None,
) -> TypedRefusal:
    """No CT-07 edge to a Knowledge Citation; seed cites travel on seed_cite only."""
    return policy(
        "promoted-from",
        "there is no CT-07 edge to a Knowledge Citation; seed cites travel on seed_cite only",
        to_ref=repr(to_ref) if to_ref is not None else None,
        seed_cite=None if seed_cite is None else "present",
        mill_edge_to_citation=False,
    )


def attach_seed_cite(
    candidate: object,
    *,
    seed_cite: object = None,
    origin: object = CANDIDATE_ORIGIN,
    mill_graduation: object = None,
    promoted_from_edge: object = None,
) -> Result[HostCandidate]:
    """Attach host origin + optional seed_cite outside CT-33/CT-34/fp1 preimage."""
    return mint_host_candidate(
        candidate=candidate,
        seed_cite=seed_cite,
        origin=origin,
        mill_graduation=mill_graduation,
        promoted_from_edge=promoted_from_edge,
    )


def mint_host_candidate(
    *,
    candidate: object,
    seed_cite: object = None,
    origin: object = CANDIDATE_ORIGIN,
    mill_graduation: object = None,
    promoted_from_edge: object = None,
) -> Result[HostCandidate]:
    """Mint a host candidate. Skip-Stage-0 may set seed_cite without mill CT-07."""
    if not isinstance(candidate, RegistrationCandidate):
        return invalid(
            "candidate",
            "host candidate wraps a RegistrationCandidate from gate_registration "
            "or mill graduation",
            given=type(candidate).__name__,
        )
    parts = _admit_host_parts(
        origin=origin,
        seed_cite=seed_cite,
        mill_graduation=mill_graduation,
        promoted_from_edge=promoted_from_edge,
    )
    if is_refusal(parts):
        return parts
    admitted_origin, admitted_cite, graduation, edge = parts.value
    checked = _check_host_lineage(edge=edge, cite=admitted_cite, graduation=graduation)
    if is_refusal(checked):
        return checked
    banned = _seed_cite_in_identity(candidate.declaration)
    if is_refusal(banned):
        return banned
    return Ok(
        HostCandidate(
            origin=admitted_origin,
            candidate=candidate,
            seed_cite=admitted_cite,
            mill_graduation=graduation,
            promoted_from_edge=edge,
        )
    )


def _admit_seed_cite_mapping(mapping: Mapping[str, object]) -> Result[SeedCite | None]:
    missing = [key for key in SEED_CITE_FIELDS if key not in mapping]
    if missing:
        return invalid(
            "seed_cite",
            "seed_cite requires source_ref, snapshot_ref, and locator",
            missing=missing,
            fields=list(SEED_CITE_FIELDS),
        )
    extras = sorted(key for key in mapping if key not in SEED_CITE_FIELDS)
    if extras:
        return invalid(
            "seed_cite",
            "seed_cite carries only source_ref, snapshot_ref, and locator",
            extras=extras,
            fields=list(SEED_CITE_FIELDS),
        )
    parts: dict[str, str] = {}
    for key in SEED_CITE_FIELDS:
        raw = mapping[key]
        if not isinstance(raw, str) or raw.strip() == "":
            return invalid(
                key,
                "seed_cite fields are non-empty strings citing an existing Knowledge Citation",
                given=repr(raw),
            )
        parts[key] = raw.strip()
    return Ok(
        SeedCite(
            source_ref=parts["source_ref"],
            snapshot_ref=parts["snapshot_ref"],
            locator=parts["locator"],
        )
    )


def _admit_optional_graduation(value: object) -> Result[Graduation | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Graduation):
        return Ok(value)
    return invalid(
        "mill_graduation",
        "mill_graduation is a Graduation or omitted for skip-Stage-0",
        given=type(value).__name__,
    )


def _admit_optional_edge(value: object) -> Result[LineageEdge | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, LineageEdge):
        return Ok(value)
    return invalid(
        "promoted_from_edge",
        "promoted_from_edge is a stamped CT-07 LineageEdge or omitted",
        given=type(value).__name__,
    )


def _admit_host_parts(
    *,
    origin: object,
    seed_cite: object,
    mill_graduation: object,
    promoted_from_edge: object,
) -> Result[tuple[str, SeedCite | None, Graduation | None, LineageEdge | None]]:
    admitted_origin = admit_candidate_origin(origin)
    if is_refusal(admitted_origin):
        return admitted_origin
    admitted_cite = admit_seed_cite(seed_cite)
    if is_refusal(admitted_cite):
        return admitted_cite
    graduation = _admit_optional_graduation(mill_graduation)
    if is_refusal(graduation):
        return graduation
    edge = _admit_optional_edge(promoted_from_edge)
    if is_refusal(edge):
        return edge
    return Ok((admitted_origin.value, admitted_cite.value, graduation.value, edge.value))


def _check_host_lineage(
    *,
    edge: LineageEdge | None,
    cite: SeedCite | None,
    graduation: Graduation | None,
) -> Result[None]:
    # Skip-Stage-0: seed_cite allowed; no originating_research_ref / mill CT-07.
    if graduation is None and edge is not None:
        return invalid(
            "promoted_from_edge",
            "skip-Stage-0 gate_registration may set seed_cite but has no mill CT-07",
        )
    if edge is not None and cite is not None and _edge_targets_seed_cite(edge, cite):
        return refuse_ct07_to_knowledge_citation(to_ref=edge.to_ref, seed_cite=cite)
    return Ok(None)


def _edge_targets_seed_cite(edge: LineageEdge, cite: SeedCite) -> bool:
    """True when a CT-07 to_ref looks like a citation locator rather than research_ref."""
    token = edge.to_ref.value
    return token in {cite.source_ref, cite.snapshot_ref, cite.locator} or not token.startswith(
        "fp1:sha256:"
    )


def _seed_cite_in_identity(declaration: BotDefinition) -> Result[None]:
    payload = declaration.identity_payload()
    raw_body = payload.get("body")
    body_map: Mapping[str, object] = (
        cast("Mapping[str, object]", raw_body) if isinstance(raw_body, Mapping) else {}
    )
    if "seed_cite" in payload or "seed_cite" in body_map:
        return policy(
            "seed_cite",
            "seed_cite must not enter CT-33 / CT-34 / fp1 preimage",
            in_fp1=SEED_CITE_IN_FP1,
        )
    return Ok(None)
