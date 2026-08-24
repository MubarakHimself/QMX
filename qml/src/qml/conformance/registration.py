"""Registration gate — both conformance layers, or no Bot kind mint (QL-8).

The Bot registry kind mints only for a declaration that passed Layer 1 and
Layer 2. A failure of either layer is ``policy rejection``; there is no partial
or probationary registration (DEC-0178, FM-4). QML returns fingerprintable
content plus the pass/fail verdict. A host composition root holds the
``WriterId`` and stamps the CT-06 record (AD-25 root-mints); this module never
returns a stamped record.

Conformance is the ticket into governed evidence (CT-32) and Book seats
(CT-28). It never gates tunnel entry: ungoverned plain-Python bots keep full
tunnel access (B-4 ledger lines, the research door). Graduation mints the two
artifacts (declaration + logic) with a ``promoted-from`` lineage edge back to
the originating research artifact. ``max_acceptable_complexity_score`` is a
stated drop — a later measure, never a registration gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import invalid, policy
from qml.conformance.contract import CONFORMANCE_FORMAT_VERSION
from qml.conformance.layer1 import Layer1Verdict
from qml.conformance.layer2 import Layer2Verdict
from qml.declaration.bot import BotDefinition
from qml.logic import LogicIdentity

__all__ = [
    "CITATION_KINDS",
    "DROPPED_REGISTRATION_GATES",
    "PROMOTED_FROM_EDGE_TYPE",
    "BotCitation",
    "CitationKind",
    "ConformanceTicket",
    "Graduation",
    "GraduationEdge",
    "RegistrationCandidate",
    "UngovernedTunnelAccess",
    "admit_ungoverned_tunnel",
    "cite_registered_bot",
    "cite_ungoverned_bot",
    "evaluate_ticket",
    "gate_registration",
    "graduate_to_governed",
]

# The old anti-sprawl gate is a stated drop, not an omission (DEC-0178). Named
# here so a caller can still pass the field: it is discarded and never consulted.
DROPPED_REGISTRATION_GATES: Final[frozenset[str]] = frozenset(
    {"max_acceptable_complexity_score", "complexity_score"}
)

PROMOTED_FROM_EDGE_TYPE: Final[str] = "promoted-from"

CITATION_KINDS: Final[tuple[str, ...]] = ("governed-evidence", "seat")

_NO_PROBATION: Final[frozenset[str]] = frozenset({"probation", "partial", "probationary"})


@dataclass(frozen=True, slots=True)
class ConformanceTicket:
    """Passed both layers. Cited by governed evidence and seats; not tunnel entry."""

    layer1_passed: bool
    layer2_passed: bool


@dataclass(frozen=True, slots=True)
class RegistrationCandidate:
    """Fingerprintable Bot-kind content plus the pass verdict (DEC-0171, DEC-0178).

    Identity is the CT-33 semantic content. Writer, sequence, stable id, and
    created-at are occurrence facts a host stamps; they are not fields here.
    """

    declaration: BotDefinition
    logic: LogicIdentity
    fingerprint: Fingerprint
    ticket: ConformanceTicket
    layer1: Layer1Verdict
    layer2: Layer2Verdict

    def identity_payload(self) -> dict[str, object]:
        """Canonical Bot definition content the host may mint. No stamped header."""
        return self.declaration.identity_payload()

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity of the gated mint decision. Package SemVer never enters."""
        return {
            "class": "qml-registration-candidate",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "declaration_fingerprint": self.fingerprint.value,
            "layer1": self.layer1.fp1_identity(),
            "layer2": self.layer2.fp1_identity(),
            "ticket": {
                "layer1_passed": self.ticket.layer1_passed,
                "layer2_passed": self.ticket.layer2_passed,
            },
        }


class CitationKind(StrEnum):
    """What a registered Bot ``fp1`` may be cited by (DEC-0178)."""

    GOVERNED_EVIDENCE = "governed-evidence"
    SEAT = "seat"


@dataclass(frozen=True, slots=True)
class BotCitation:
    """A valid CT-32 or CT-28 cite of a registered Bot definition ``fp1``."""

    fingerprint: Fingerprint
    kind: CitationKind

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "qml-bot-citation",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "bot_definition_fingerprint": self.fingerprint.value,
            "kind": self.kind.value,
        }


@dataclass(frozen=True, slots=True)
class UngovernedTunnelAccess:
    """B-4 ledger lines and the research door stay open without a ticket."""

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "qml-ungoverned-tunnel-access",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "ticket_required": False,
            "citation_allowed": False,
            "tunnel_open": True,
        }


@dataclass(frozen=True, slots=True)
class GraduationEdge:
    """A ``promoted-from`` lineage-edge intent (CT-07). No ``WriterId`` — the host stamps."""

    from_ref: Fingerprint
    to_ref: Fingerprint

    @property
    def edge_type(self) -> str:
        return PROMOTED_FROM_EDGE_TYPE

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "qml-bot-graduation-edge",
            "edge_type": PROMOTED_FROM_EDGE_TYPE,
            "from_ref": self.from_ref.value,
            "to_ref": self.to_ref.value,
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
        }

    def fingerprint_content(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class Graduation:
    """The two Bot artifacts plus a lineage edge to the originating research (DEC-0178)."""

    declaration: BotDefinition
    logic: LogicIdentity
    candidate: RegistrationCandidate
    originating_research_ref: Fingerprint
    promoted_from_edge: GraduationEdge

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "qml-bot-graduation",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "declaration_fingerprint": self.candidate.fingerprint.value,
            "logic": self.logic.fp1_identity(),
            "originating_research_ref": self.originating_research_ref.value,
            "promoted_from_edge": self.promoted_from_edge.fp1_identity(),
        }


def evaluate_ticket(*, layer1_passed: object, layer2_passed: object) -> Result[ConformanceTicket]:
    """Pure verdict: mint a ticket only when both layers passed (DEC-0178).

    A failed layer is a ``policy rejection`` — the Bot kind mints only on a full
    pass; there is no partial or probationary registration.
    """
    if not isinstance(layer1_passed, bool) or not isinstance(layer2_passed, bool):
        return invalid(
            "layers",
            "each conformance layer verdict is a bool",
            layer1_passed=repr(layer1_passed),
            layer2_passed=repr(layer2_passed),
        )
    if layer1_passed and layer2_passed:
        return Ok(ConformanceTicket(layer1_passed=True, layer2_passed=True))
    return policy(
        "conformance",
        "the Bot kind mints only for artifacts passing both layers; conformance "
        "never gates tunnel entry",
        layer1_passed=layer1_passed,
        layer2_passed=layer2_passed,
    )


def gate_registration(
    *,
    layer1: object,
    layer2: object,
    **extra: object,
) -> Result[RegistrationCandidate]:
    """Admit Bot-kind minting only when both conformance layers passed (QL-8).

    Consumes Layer-1 and Layer-2 verdicts (or the typed refusals they returned).
    A failed layer is wrapped as ``policy rejection`` so the Bot kind never
    mints on a partial pass. Complexity kwargs in
    :data:`DROPPED_REGISTRATION_GATES` are discarded — they are not a gate.
    Returns fingerprintable content plus the pass verdict, never a stamped
    record.
    """
    remainder = _discard_dropped_gates(extra)
    probation = _refuse_probation(remainder)
    if is_refusal(probation):
        return probation
    if remainder:
        return invalid(
            "registration",
            "unknown registration fields are not a gate",
            given=sorted(remainder),
        )
    first = _admit_layer1(layer1)
    if is_refusal(first):
        return first
    second = _admit_layer2(layer2)
    if is_refusal(second):
        return second
    if first.value.fingerprint.value != second.value.declaration_fingerprint.value:
        return invalid(
            "layers",
            "Layer 1 and Layer 2 proofs must name the same Bot definition fingerprint",
            layer1=first.value.fingerprint.value,
            layer2=second.value.declaration_fingerprint.value,
        )
    ticket = evaluate_ticket(layer1_passed=True, layer2_passed=True)
    if is_refusal(ticket):
        return ticket
    declaration = first.value.declaration
    return Ok(
        RegistrationCandidate(
            declaration=declaration,
            logic=declaration.logic_reference,
            fingerprint=first.value.fingerprint,
            ticket=ticket.value,
            layer1=first.value,
            layer2=second.value,
        )
    )


def cite_registered_bot(
    *,
    candidate: object,
    cited_fp1: object,
    kind: object,
) -> Result[BotCitation]:
    """A CT-32 population or CT-28 seat may cite a registered Bot ``fp1``.

    Conformance gates citation and seats, never tunnel entry. An ungoverned
    bot (no candidate) cannot be cited.
    """
    if candidate is None:
        return cite_ungoverned_bot(cited_fp1=cited_fp1, kind=kind)
    if not isinstance(candidate, RegistrationCandidate):
        return policy(
            "candidate",
            "governed evidence and seats cite a registered Bot definition; a Bot "
            "kind that did not pass both layers has no ticket",
            given=type(candidate).__name__,
        )
    cited = _coerce_fingerprint(cited_fp1, "cited_fp1")
    if is_refusal(cited):
        return cited
    resolved_kind = _admit_citation_kind(kind)
    if is_refusal(resolved_kind):
        return resolved_kind
    if cited.value.value != candidate.fingerprint.value:
        return policy(
            "cited_fp1",
            "governed evidence and seats cite a registered Bot definition by fp1; "
            "this fingerprint is not the ticketed Bot",
            cited=cited.value.value,
            registered=candidate.fingerprint.value,
        )
    return Ok(BotCitation(fingerprint=cited.value, kind=resolved_kind.value))


def cite_ungoverned_bot(*, cited_fp1: object = None, kind: object = None) -> TypedRefusal:
    """Ungoverned bots cannot be cited by governed evidence or seats (DEC-0178)."""
    del cited_fp1, kind
    return policy(
        "citation",
        "ungoverned plain-Python bots keep full tunnel access and cannot be cited "
        "by governed evidence (CT-32) or seats; conformance gates citation and "
        "seats, never tunnel entry",
        citation_allowed=False,
        tunnel_open=True,
    )


def admit_ungoverned_tunnel() -> Result[UngovernedTunnelAccess]:
    """Ungoverned plain-Python bots keep full tunnel access (B-4, the research door).

    No ticket is required. Conformance never gates tunnel entry.
    """
    return Ok(UngovernedTunnelAccess())


def graduate_to_governed(
    *,
    layer1: object,
    layer2: object,
    originating_research_ref: object,
    **extra: object,
) -> Result[Graduation]:
    """Mint the two artifacts with a ``promoted-from`` edge to originating research.

    Graduation still requires both conformance layers. The edge is fingerprintable
    content; the host composition root stamps the CT-07 record with its
    ``WriterId``.
    """
    candidate = gate_registration(layer1=layer1, layer2=layer2, **extra)
    if is_refusal(candidate):
        return candidate
    research = _coerce_fingerprint(originating_research_ref, "originating_research_ref")
    if is_refusal(research):
        return research
    if research.value.value == candidate.value.fingerprint.value:
        return invalid(
            "originating_research_ref",
            "a graduation links a governed Bot to a distinct originating research "
            "artifact; the two fingerprints cannot be the same",
            ref=research.value.value,
        )
    edge = GraduationEdge(from_ref=candidate.value.fingerprint, to_ref=research.value)
    return Ok(
        Graduation(
            declaration=candidate.value.declaration,
            logic=candidate.value.logic,
            candidate=candidate.value,
            originating_research_ref=research.value,
            promoted_from_edge=edge,
        )
    )


def _discard_dropped_gates(extra: dict[str, object]) -> dict[str, object]:
    """Drop complexity kwargs without consulting their values (stated drop)."""
    return {key: value for key, value in extra.items() if key not in DROPPED_REGISTRATION_GATES}


def _refuse_probation(extra: dict[str, object]) -> Result[None]:
    """There is no partial or probationary registration (AD-32 mirrored)."""
    for key in _NO_PROBATION:
        if key not in extra:
            continue
        value = extra.pop(key)
        if value is True:
            return policy(
                "probation",
                "there is no partial or probationary registration; the Bot kind "
                "mints only on a full pass of both layers",
                flag=key,
            )
        if value is not False and value is not None:
            return invalid(
                "probation",
                "probation is not a registration mode; pass nothing, or False",
                given=repr(value),
            )
    return Ok(None)


def _admit_layer1(value: object) -> Result[Layer1Verdict]:
    value = _unwrap_ok(value)
    if isinstance(value, Layer1Verdict):
        return Ok(value)
    if isinstance(value, TypedRefusal):
        return _failed_layer(value, layer=1)
    return invalid(
        "layer1",
        "registration consumes a Layer-1 verdict or the typed refusal it returned",
        given=type(value).__name__,
    )


def _admit_layer2(value: object) -> Result[Layer2Verdict]:
    value = _unwrap_ok(value)
    if isinstance(value, Layer2Verdict):
        return Ok(value)
    if isinstance(value, TypedRefusal):
        return _failed_layer(value, layer=2)
    return invalid(
        "layer2",
        "registration consumes a Layer-2 verdict or the typed refusal it returned",
        given=type(value).__name__,
    )


def _failed_layer(refusal: TypedRefusal, *, layer: int) -> TypedRefusal:
    return policy(
        "conformance",
        "the Bot kind mints only for artifacts passing both layers; a declaration "
        "failing either layer is a policy rejection — there is no partial or "
        "probationary registration; conformance never gates tunnel entry",
        failed_layer=layer,
        failed_category=refusal.category.value,
        cause=dict(refusal.context),
        journal=True,
    )


def _admit_citation_kind(value: object) -> Result[CitationKind]:
    if isinstance(value, CitationKind):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(CitationKind(value))
        except ValueError:
            pass
    return invalid(
        "kind",
        "a citation is governed-evidence (CT-32) or seat (CT-28)",
        given=repr(value),
        allowed=list(CITATION_KINDS),
    )


def _coerce_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            field,
            "a Bot citation or research artifact is referenced by fp1:sha256:<hex>",
            given=repr(value),
        )
    return parsed


def _unwrap_ok(raw: object) -> object:
    if isinstance(raw, Ok):
        return cast("Ok[object]", raw).value
    return raw
