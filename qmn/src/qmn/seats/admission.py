"""Node-seat admission: the ungoverned Python-bot tunnel cannot bypass gates.

QMB keeps the experimentation tunnel open without a conformance ticket
(QL-8 / DEC-0178). A node seat does not. Story 26.15 / E12-F05: proposing
plain-Python logic for a governed seat requires a registered CT-33
definition, QML runtime-protocol conformance, the prediction linter, a
declared footprint, the canonical assignment, a Book/BMS binding, and the
AD-32 admission layers. Direct callback injection and composition-root
imports of the ungoverned tunnel refuse.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Ok, Result, TypedRefusal, is_refusal
from qmf.core.identity import AccountRole
from qml.conformance import (
    BotCitation,
    CitationKind,
    PredictionVerdict,
    RegistrationCandidate,
    UngovernedTunnelAccess,
    cite_registered_bot,
    cite_ungoverned_bot,
    lint_prediction,
)
from qml.declaration.bot import BotDefinition
from qml.protocol.factory import HostedBot

from qmn.promotion.battery import AdmissionLayerFreshState
from qmn.seats._refuse import clean_token, invalid, policy
from qmn.seats.host import GovernedSeat, construct_governed_seat

__all__ = [
    "ADMISSION_LAYER_NAMES",
    "SEAT_ADMISSION_PROOFS",
    "SEAT_ADMISSION_SURFACE",
    "UNGOVERNED_EVIDENCE_KINDS",
    "UNGOVERNED_TUNNEL_NAMES",
    "AdmittedNodeSeat",
    "SeatAdmissionProof",
    "cite_governed_seat_occurrence",
    "inject_seat_callback",
    "propose_node_seat",
    "refuse_composition_root_ungoverned_import",
    "refuse_ungoverned_tunnel_seat",
    "scan_production_src_for_ungoverned_tunnel",
    "ungoverned_tunnel_names_in_tree",
]

SEAT_ADMISSION_SURFACE: Final[str] = "qmn.seats.admission"

SEAT_ADMISSION_PROOFS: Final[tuple[str, ...]] = (
    "registered_ct33",
    "qml_runtime_protocol",
    "prediction_linter",
    "declared_footprint",
    "canonical_assignment",
    "book_binding",
    "admission_layers",
)

ADMISSION_LAYER_NAMES: Final[tuple[str, ...]] = (
    "layer1_linters",
    "layer2_shakedown",
    "layer3_operator_signature",
)

UNGOVERNED_TUNNEL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "UngovernedTunnelAccess",
        "admit_ungoverned_tunnel",
        "cite_ungoverned_bot",
    }
)

UNGOVERNED_EVIDENCE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "qmb-ungoverned",
        "research",
        "tunnel",
        "ungoverned",
    }
)

_ALLOWED_SCAN_RELPATHS: Final[frozenset[str]] = frozenset({"seats/admission.py"})


@dataclass(frozen=True, slots=True)
class SeatAdmissionProof:
    """Named proofs that a node seat entered through the governed doors."""

    candidate: RegistrationCandidate
    prediction: PredictionVerdict
    admission_layers: AdmissionLayerFreshState
    binding_ref: str
    bms_instance_id: str
    assignment_is_canonical: bool
    proofs: tuple[str, ...] = SEAT_ADMISSION_PROOFS

    def fp1_identity(self) -> dict[str, object]:
        return {
            "assignment_is_canonical": self.assignment_is_canonical,
            "binding_ref": self.binding_ref,
            "bms_instance_id": self.bms_instance_id,
            "bot_definition_fingerprint": self.candidate.fingerprint.value,
            "class": "seat-admission-proof",
            "proofs": list(self.proofs),
            "ticket": {
                "layer1_passed": self.candidate.ticket.layer1_passed,
                "layer2_passed": self.candidate.ticket.layer2_passed,
            },
        }


@dataclass(frozen=True, slots=True)
class AdmittedNodeSeat:
    """A QL-7 seat that passed every node-seat admission proof (E12-F05)."""

    seat: GovernedSeat
    proof: SeatAdmissionProof

    @property
    def seat_id(self) -> str:
        return self.seat.seat_id

    @property
    def binding_ref(self) -> str:
        return self.seat.binding_ref

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_ref": self.seat.binding_ref,
                "proof": self.proof.fp1_identity(),
                "seat_id": self.seat.seat_id,
            }
        )


def refuse_ungoverned_tunnel_seat(*, field: str = "tunnel", **extra: object) -> TypedRefusal:
    """Ungoverned tunnel access never grants a node seat (E12-F05; QL-8)."""
    return policy(
        field,
        "ungoverned plain-Python bots keep the QMB experimentation tunnel and "
        "cannot occupy a node seat; the node requires a registered CT-33 "
        "definition, QML runtime-protocol conformance, prediction linter, "
        "declared footprint, canonical assignment, Book binding, and all "
        "admission layers (E12-F05; QL-8)",
        citation_allowed=False,
        seat_allowed=False,
        tunnel_open=True,
        **extra,
    )


def inject_seat_callback(
    callback: object, *, field: str = "callback", **extra: object
) -> TypedRefusal:
    """Direct callback injection cannot host a node seat (E12-F05)."""
    return policy(
        field,
        "direct callback injection cannot host a node seat; seats enter only "
        "through propose_node_seat after the admission proofs (E12-F05)",
        given=type(callback).__name__,
        **extra,
    )


def refuse_composition_root_ungoverned_import(**extra: object) -> TypedRefusal:
    """The composition root may not import the ungoverned tunnel for seating."""
    return policy(
        "composition_root",
        "the node composition root refuses ungoverned-tunnel imports; "
        "admit_ungoverned_tunnel, cite_ungoverned_bot, and UngovernedTunnelAccess "
        "are not a seating path (E12-F05; QL-8)",
        forbidden=tuple(sorted(UNGOVERNED_TUNNEL_NAMES)),
        **extra,
    )


def ungoverned_tunnel_names_in_tree(tree: object) -> tuple[str, ...]:
    """Return forbidden ungoverned-tunnel names referenced in an AST."""
    if not isinstance(tree, ast.AST):
        return ()
    found: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".")[-1] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        for name in names:
            if name in UNGOVERNED_TUNNEL_NAMES:
                found.add(name)
    return tuple(sorted(found))


def scan_production_src_for_ungoverned_tunnel(src_root: object = None) -> Result[None]:
    """Refuse if production ``qmn`` sources import the ungoverned tunnel APIs."""
    if src_root is None:
        root = Path(__file__).resolve().parents[1]
    elif isinstance(src_root, Path):
        root = src_root
    elif isinstance(src_root, str) and src_root.strip() != "":
        root = Path(src_root)
    else:
        return invalid(
            "src_root",
            "the ungoverned-tunnel scan walks a filesystem path",
            given=repr(src_root),
        )
    hits: list[str] = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root).as_posix()
        if rel in _ALLOWED_SCAN_RELPATHS:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names = ungoverned_tunnel_names_in_tree(tree)
        hits.extend(f"{rel}:{name}" for name in names)
    if hits:
        return refuse_composition_root_ungoverned_import(hits=tuple(sorted(hits)))
    return Ok(None)


def propose_node_seat(
    factory: object,
    *,
    seat_id: object,
    binding_ref: object,
    bms_instance_id: object,
    declaration: object,
    containment: object,
    candidate: object,
    admission_layers: object,
    exit_policy: object,
    footprint_requirements: object,
    venue_capabilities: object,
    account_role: object = None,
    assignment: object = None,
    read_surfaces: object = None,
    stream_id: object = None,
    clock: object = None,
    book: object = None,
    venue: object = None,
    signal_snapshot: object = None,
    callback: object = None,
    hosted: object = None,
    tunnel: object = None,
    admission_bar: object = None,
) -> Result[AdmittedNodeSeat]:
    """Admit a bot for a node seat. The ungoverned tunnel is not a seating path."""
    injected = _refuse_direct_injection(
        factory=factory,
        callback=callback,
        hosted=hosted,
        tunnel=tunnel,
        candidate=candidate,
    )
    if is_refusal(injected):
        return injected
    ticketed = _require_registered_candidate(candidate, declaration)
    if is_refusal(ticketed):
        return ticketed
    registered = ticketed.value
    layers = _as_admission_layers(admission_layers)
    if is_refusal(layers):
        return layers
    if not layers.value.all_passed:
        return policy(
            "admission_layers",
            "a node seat requires every AD-32 admission layer: Layer-1 linters, "
            "Layer-2 shakedown, and the Layer-3 operator signature",
            layer1_linters_passed=layers.value.layer1_linters_passed,
            layer2_shakedown_passed=layers.value.layer2_shakedown_passed,
            layer3_operator_signature_present=layers.value.layer3_operator_signature_present,
        )
    bms = clean_token(bms_instance_id)
    if bms is None:
        return invalid(
            "bms_instance_id",
            "a node seat binds a Book through a non-empty BMS instance id",
            given=repr(bms_instance_id),
        )
    cited = cite_registered_bot(
        candidate=registered,
        cited_fp1=registered.fingerprint,
        kind=CitationKind.SEAT,
    )
    if is_refusal(cited):
        return cited
    prediction = lint_prediction(
        registered.declaration,
        exit_policy=exit_policy,
        footprint_requirements=footprint_requirements,
        venue_capabilities=venue_capabilities,
        account_role=AccountRole.DEMO if account_role is None else account_role,
        admission_bar=admission_bar,
    )
    if is_refusal(prediction):
        return prediction
    footprint = _require_declared_footprint(registered.declaration)
    if is_refusal(footprint):
        return footprint
    hosted_seat = construct_governed_seat(
        factory,
        seat_id=seat_id,
        binding_ref=binding_ref,
        declaration=registered.declaration,
        containment=containment,
        assignment=assignment,
        read_surfaces=read_surfaces,
        stream_id=stream_id,
        clock=clock,
        book=book,
        venue=venue,
        signal_snapshot=signal_snapshot,
    )
    if is_refusal(hosted_seat):
        return hosted_seat
    proof = SeatAdmissionProof(
        candidate=registered,
        prediction=prediction.value,
        admission_layers=layers.value,
        binding_ref=hosted_seat.value.binding_ref,
        bms_instance_id=bms,
        assignment_is_canonical=hosted_seat.value.assignment_is_canonical,
        proofs=SEAT_ADMISSION_PROOFS,
    )
    return Ok(AdmittedNodeSeat(seat=hosted_seat.value, proof=proof))


def cite_governed_seat_occurrence(
    *,
    seat: object,
    candidate: object,
    evidence_kind: object,
    cited_fp1: object = None,
) -> Result[BotCitation]:
    """Ungoverned evidence can never cite a governed seat occurrence (FR-072)."""
    if not isinstance(seat, AdmittedNodeSeat):
        return policy(
            "seat",
            "ungoverned evidence can never cite a governed seat occurrence; a "
            "QL-7 construct without propose_node_seat has no governed occurrence",
            evidence_kind=repr(evidence_kind),
            given=type(seat).__name__,
        )
    kind_token = _evidence_kind_token(evidence_kind)
    if kind_token in UNGOVERNED_EVIDENCE_KINDS:
        return policy(
            "evidence",
            "ungoverned evidence can never cite a governed seat occurrence (FR-072)",
            evidence_kind=kind_token,
            seat_id=seat.seat_id,
            citation_allowed=False,
        )
    if candidate is None or isinstance(candidate, UngovernedTunnelAccess):
        return cite_ungoverned_bot(cited_fp1=cited_fp1, kind=evidence_kind)
    fingerprint = seat.proof.candidate.fingerprint if cited_fp1 is None else cited_fp1
    return cite_registered_bot(
        candidate=candidate,
        cited_fp1=fingerprint,
        kind=CitationKind.GOVERNED_EVIDENCE,
    )


def _refuse_direct_injection(
    *,
    factory: object,
    callback: object,
    hosted: object,
    tunnel: object,
    candidate: object,
) -> Result[None]:
    if callback is not None:
        return inject_seat_callback(callback)
    if hosted is not None:
        return inject_seat_callback(hosted, field="hosted")
    if isinstance(factory, HostedBot):
        return inject_seat_callback(factory, field="factory")
    construct = getattr(factory, "construct", None)
    if not callable(construct):
        return inject_seat_callback(factory, field="factory")
    if tunnel is not None or isinstance(candidate, UngovernedTunnelAccess):
        source = tunnel if tunnel is not None else candidate
        return refuse_ungoverned_tunnel_seat(given=type(source).__name__)
    return Ok(None)


def _require_registered_candidate(
    candidate: object,
    declaration: object,
) -> Result[RegistrationCandidate]:
    if candidate is None:
        return refuse_ungoverned_tunnel_seat(field="candidate")
    if isinstance(candidate, UngovernedTunnelAccess):
        return refuse_ungoverned_tunnel_seat()
    if not isinstance(candidate, RegistrationCandidate):
        return policy(
            "candidate",
            "a node seat cites a registered CT-33 Bot definition that passed both "
            "QML conformance layers; an ungoverned candidate has no ticket",
            given=type(candidate).__name__,
        )
    if not (candidate.ticket.layer1_passed and candidate.ticket.layer2_passed):
        return policy(
            "conformance",
            "QML runtime-protocol conformance is both Layer-1 and Layer-2; a "
            "partial ticket cannot occupy a node seat",
            layer1_passed=candidate.ticket.layer1_passed,
            layer2_passed=candidate.ticket.layer2_passed,
        )
    bot = _as_declaration(declaration)
    if is_refusal(bot):
        return bot
    fingerprinted = bot.value.fingerprint_content()
    if is_refusal(fingerprinted):
        return fingerprinted
    if fingerprinted.value.value != candidate.fingerprint.value:
        return policy(
            "declaration",
            "the hosted declaration must be the registered CT-33 Bot definition "
            "the conformance ticket names",
            cited=fingerprinted.value.value,
            registered=candidate.fingerprint.value,
        )
    return Ok(candidate)


def _as_declaration(value: object) -> Result[BotDefinition]:
    if isinstance(value, BotDefinition):
        return Ok(value)
    return BotDefinition.try_from_mapping(value)


def _as_admission_layers(value: object) -> Result[AdmissionLayerFreshState]:
    if isinstance(value, AdmissionLayerFreshState):
        return Ok(value)
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        return AdmissionLayerFreshState.try_create(
            layer1_linters_passed=mapping.get("layer1_linters_passed"),
            layer2_shakedown_passed=mapping.get("layer2_shakedown_passed"),
            layer3_operator_signature_present=mapping.get("layer3_operator_signature_present"),
        )
    return invalid(
        "admission_layers",
        "a node seat carries the AD-32 three-layer proofs",
        given=type(value).__name__,
    )


def _require_declared_footprint(declaration: BotDefinition) -> Result[None]:
    footprint = declaration.footprint
    if not tuple(footprint.stream_set):
        return policy(
            "footprint",
            "a node seat requires the CT-33 declared footprint; an empty stream set cannot host",
        )
    return Ok(None)


def _evidence_kind_token(value: object) -> str:
    if isinstance(value, CitationKind):
        return value.value
    if isinstance(value, str):
        return value.strip().lower()
    return type(value).__name__.lower()
