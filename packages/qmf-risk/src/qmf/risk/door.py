"""Story 10.6 — the CT-23 risk-evaluation door (COMP-QMF-RISK).

One inbound bot-to-Book door, minted once and read one way everywhere, carrying
**exactly two typed intent families — entry and exit — plus declared evidence slots
and nothing else** (AD-33; DEC-0147). A Bot proposes through this door and the Book
resolves, sizes, admits, or refuses with a typed reason; the authority order
``bot -> book -> BMS -> operator`` the spine quotes verbatim is never inverted, which
is why **a bot may never size**: ``requested_r`` is Book-resolved and an inbound
``requested_r`` is an ``invalid input`` refusal (AC1; DEC-0147, DEC-0154).

* **Entry intent** (:class:`EntryIntent`) — the inbound proposal carries the
  instrument, the direction, an advisory :attr:`~EntryIntent.proposed_r`, a typed
  :class:`ReasonCode`, the :class:`~qmf.risk.paper.ExecutionTarget`, and its cited
  evidence slots (:class:`CitedEvidence`); it carries **no** ``requested_r`` and
  **no** bot-supplied full-loss price (AC2; CT-23 format 1). The **declared full-loss
  price is derived at the Book door** (:func:`derive_full_loss_price_at_door`) by the
  Book's per-family :class:`ExitLogicRef` consuming the intent's cited evidence, and
  is stamped onto the :class:`AdmittedEntry` exactly as ``requested_r`` is Book-resolved
  — single-sited, **no Book module is ever injected into bot logic** (DEC-0147,
  DEC-0177, DEC-0182).
* **Exit intent** (:class:`ExitIntent`) — risk-monotonic by construction: the only V1
  kinds are :attr:`ExitKind.CLOSE_FULL` and :attr:`ExitKind.TIGHTEN_PROTECTIVE_STOP`,
  each with a typed :class:`ReasonCode`; ``close_partial`` is an ``unsupported
  capability`` refusal (:func:`reject_close_partial`), and a tighten names a
  direction and a bound (:class:`TightenProtectiveStop`), **never a price** (AC3;
  DEC-0147, DEC-0148).
* **Risk-monotonic law** — an intent may never widen a stop, extend a target beyond
  the Book's declared envelope, re-open a closed position, or increase size; each is a
  :class:`RiskMonotonicViolation` and a ``policy rejection`` (:func:`check_stop_not_widened`,
  :func:`check_target_within_envelope`, :func:`check_no_reopen`,
  :func:`check_no_size_increase`) (AC4; DEC-0147).
* **The ExitLogicRef mode registry** (:data:`EXIT_LOGIC_MODE_REGISTRY`) — a Book that
  carries its own exit/stop methodology may declare the adopt-the-bot's-advisory-stop
  module mode (:data:`ADOPT_BOT_ADVISORY_STOP_MODE`), whose input contract is the CT-23
  **format-2** ``entry.advisory_stop_proposal`` field (minted by the QML increment,
  Story 11.7, per SC-05). Invoking that mode while CT-23 sits at
  :data:`CT23_ACTIVE_FORMAT_VERSION` (format 1) is an ``unavailable dependency`` refusal
  (:func:`check_exit_logic_mode_available`) — ``requested_r`` stays Book-resolved and
  the frozen R faces stay frozen in every mode (AC5; DEC-0177, DEC-0185).
* **Forward compatibility** (AD-5) — a format-1 artifact stays readable forever and an
  unknown optional field never breaks a format-1 consumer (:func:`parse_inbound_intent`
  ignores unknown optional fields under a known format version), while an unknown
  contract format version is an ``unsupported capability`` refusal (AC6; CT-22, CT-23).

qmf-risk imports **only** ``qmf-core`` (default-deny, L30/DEC-0120) and sibling
``qmf.risk`` modules; nothing imports ``qmf.risk``. Ratified ``defined-unwired``
surface: no live binding, order, mode transition, or flatten is authorized by this
code — the caller (the node/bot layer) is unassigned in QMF, records reach
``qmf-registry`` / ``qmf-data`` only through the composition root, and no clock is read
below it (DEC-0147, DEC-0158, DEC-0142).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core import (
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Price,
    PriceDelta,
    Quantity,
    Result,
    TypedRefusal,
    UnitKind,
    is_refusal,
)
from qmf.core import (
    Ok as _Ok,
)
from qmf.risk._common import (
    clean_str,
    coerce_enum,
    invalid,
    policy,
    type_name,
    unavailable,
    unsupported,
)
from qmf.risk.paper import ExecutionTarget
from qmf.risk.r_faces import Direction, check_no_scale_in, derive_original_risk_distance

__all__ = [
    "ADOPT_BOT_ADVISORY_STOP_MODE",
    "ADOPT_BOT_ADVISORY_STOP_MODE_ID",
    "CT23_ACTIVE_FORMAT_VERSION",
    "CT23_ADVISORY_STOP_FORMAT_VERSION",
    "CT23_KNOWN_FORMAT_VERSIONS",
    "EXIT_LOGIC_MODE_REGISTRY",
    "AdmittedEntry",
    "CitedEvidence",
    "Direction",
    "EntryIntent",
    "EvidenceSlot",
    "ExitIntent",
    "ExitKind",
    "ExitLogicMode",
    "ExitLogicModule",
    "ExitLogicRef",
    "IntentFamily",
    "ReasonCode",
    "RiskEvaluationRequest",
    "RiskMonotonicViolation",
    "StopMoveDirection",
    "TightenProtectiveStop",
    "admit_entry_intent",
    "check_exit_logic_mode_available",
    "check_no_reopen",
    "check_no_size_increase",
    "check_stop_not_widened",
    "check_target_within_envelope",
    "derive_full_loss_price_at_door",
    "evaluate_exit_intent",
    "parse_inbound_intent",
    "refuse_no_full_loss_price",
    "reject_close_partial",
    "reject_inbound_requested_r",
    "reject_risk_monotonic_violation",
]

# This module's own contract format version stamped into fp1 identity content; its
# meaning never mutates — an incompatible change mints the next version (L15).
_DOOR_FORMAT_VERSION = 1

# CT-23 sits at contract format version 1 in this build (AD-33, the first mint,
# DEC-0147). Contract format version 2 — the OPTIONAL ``entry.advisory_stop_proposal``
# field (DEC-0177, DEC-0182) — is minted by the QML increment (Story 11.7, SC-05); this
# build is a format-1 consumer, so a format-2-only capability is an unavailable
# dependency here and a format-1 artifact stays readable forever (AD-5; AC5, AC6).
CT23_ACTIVE_FORMAT_VERSION: Final[int] = 1
CT23_ADVISORY_STOP_FORMAT_VERSION: Final[int] = 2
CT23_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset({CT23_ACTIVE_FORMAT_VERSION})

# The wire field a bot may never carry inbound — the bot does not size (AC1).
_REQUESTED_R_FIELD: Final[str] = "requested_r"
# The V1 exit kind the vocabulary deliberately excludes; a request for it is an
# ``unsupported capability`` refusal, never ``invalid input`` (AC3; DEC-0147).
_CLOSE_PARTIAL: Final[str] = "close_partial"


# --- the two intent families and the exit vocabulary -------------------------


class IntentFamily(StrEnum):
    """The CT-23 discriminant — **exactly two families**, nothing else (AC1; DEC-0147).

    Every request carries exactly one of :attr:`ENTRY` or :attr:`EXIT` plus declared
    evidence slots; a request carrying both families, or neither, is an ``invalid
    input`` refusal (:meth:`RiskEvaluationRequest.try_create`).
    """

    ENTRY = "entry"
    EXIT = "exit"


class ExitKind(StrEnum):
    """The only two V1 exit kinds, a closed set — addable never redefined (AC3).

    :attr:`CLOSE_FULL` closes the whole virtual position; :attr:`TIGHTEN_PROTECTIVE_STOP`
    names a direction and a bound for a risk-non-increasing stop move. ``close_partial``
    is deliberately **not** a member — the five-command vocabulary expresses no fractional
    close, so a partial exit is an ``unsupported capability`` refusal (a close-then-replace
    would open the unprotected window ``amend_protection`` forbids) (DEC-0147, DEC-0148).
    """

    CLOSE_FULL = "close_full"
    TIGHTEN_PROTECTIVE_STOP = "tighten_protective_stop"


class StopMoveDirection(StrEnum):
    """The sense of a protective-stop move (CT-23; DEC-0147, DEC-0148).

    :attr:`TIGHTEN` is risk-reducing — the stop moves toward the current price, cutting
    the loss-direction distance. :attr:`WIDEN` is risk-increasing and **forbidden**: a
    tighten intent naming :attr:`WIDEN` is a :attr:`RiskMonotonicViolation.WIDEN_STOP`
    ``policy rejection``, never a legal move (AC4).
    """

    TIGHTEN = "tighten"
    WIDEN = "widen"


class RiskMonotonicViolation(StrEnum):
    """The four risk-monotonic violation classes, each a ``policy rejection`` (AC4).

    An intent may never widen a stop (:attr:`WIDEN_STOP`), extend a target beyond the
    Book's declared envelope (:attr:`EXTEND_TARGET_BEYOND_ENVELOPE`), re-open a closed
    position (:attr:`RE_OPEN`), or increase size (:attr:`INCREASE_SIZE`) (DEC-0147).
    """

    WIDEN_STOP = "widen-stop"
    EXTEND_TARGET_BEYOND_ENVELOPE = "extend-target-beyond-envelope"
    RE_OPEN = "re-open"
    INCREASE_SIZE = "increase-size"


# --- the typed reason code and declared evidence slots -----------------------


@dataclass(frozen=True, slots=True)
class ReasonCode:
    """A typed reason code, versioned per Book family (CT-23; DEC-0147).

    The code space is **not** enumerated at contract level — the Book family owns it —
    so the door requires the field present and typed, not a fixed member set. Both the
    ``code`` and the owning ``book_family`` are opaque, non-empty tokens; a blank
    either is an ``invalid input`` refusal.
    """

    code: str
    book_family: str

    @classmethod
    def try_create(cls, code: object, book_family: object) -> Result[ReasonCode]:
        """Validate and build a :class:`ReasonCode`, value-or-refusal."""
        code_token = clean_str(code)
        if code_token is None:
            return invalid(
                "code",
                "a reason code is a non-empty typed token; the door requires it present",
                given=repr(code),
            )
        family_token = clean_str(book_family)
        if family_token is None:
            return invalid(
                "book_family",
                "a reason code is versioned per Book family; the owning family is a "
                "non-empty token",
                given=repr(book_family),
            )
        return _Ok(cls(code=code_token, book_family=family_token))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the reason code."""
        return {
            "class": "reason-code",
            "code": self.code,
            "book_family": self.book_family,
            "format_version": _DOOR_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class EvidenceSlot:
    """One declared evidence slot carrying its as-of knowledge time (CT-23; DEC-0153).

    A labeled declared input shape — the SQS reading (a CT-16 configured-producer value)
    or cohort-correlation evidence (an AD-31 slot) — carried **by reference/label**,
    never a second contract embedded here. Every slot carries a stated as-of knowledge
    time (an injected :class:`~qmf.core.Instant`); **a slot present without its as-of
    time is an ``invalid input`` refusal** (DEC-0153, DEC-0145).
    """

    label: str
    value_ref: str
    as_of: Instant

    @classmethod
    def try_create(cls, label: object, value_ref: object, as_of: object) -> Result[EvidenceSlot]:
        """Validate and build an :class:`EvidenceSlot`, value-or-refusal."""
        label_token = clean_str(label)
        if label_token is None:
            return invalid("label", "an evidence slot names an opaque label", given=repr(label))
        ref_token = clean_str(value_ref)
        if ref_token is None:
            return invalid(
                "value_ref",
                "an evidence slot carries its value by reference/label, never a second contract",
                given=repr(value_ref),
            )
        if not isinstance(as_of, Instant):
            return invalid(
                "as_of",
                "an evidence slot carries a stated as-of knowledge time; a slot without it is "
                "refused (never defaulted)",
                given=repr(as_of),
            )
        return _Ok(cls(label=label_token, value_ref=ref_token, as_of=as_of))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the evidence slot."""
        return {
            "class": "evidence-slot",
            "label": self.label,
            "value_ref": self.value_ref,
            "as_of": self.as_of.fp1_identity(),
            "format_version": _DOOR_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class CitedEvidence:
    """The declared evidence slots an intent cites (CT-23; DEC-0153, DEC-0145).

    The two ratified named slots — ``sqs_reading`` (a CT-16 configured-producer value per
    AD-39) and ``cohort_correlation`` (an AD-31 declared slot) — are each optional labeled
    inputs; cohort-correlation evidence is named apart from the fill-attribution label and
    from ``correlation_id``. Both may be absent (an entry need cite no evidence); each
    present slot must carry its as-of knowledge time (enforced by :class:`EvidenceSlot`).
    """

    sqs_reading: EvidenceSlot | None = None
    cohort_correlation: EvidenceSlot | None = None

    @classmethod
    def try_create(
        cls, *, sqs_reading: object = None, cohort_correlation: object = None
    ) -> Result[CitedEvidence]:
        """Validate and build a :class:`CitedEvidence` set, value-or-refusal."""
        sqs: EvidenceSlot | None = None
        if sqs_reading is not None:
            if not isinstance(sqs_reading, EvidenceSlot):
                return invalid(
                    "sqs_reading",
                    "the SQS reading is an EvidenceSlot when present",
                    given=repr(sqs_reading),
                )
            sqs = sqs_reading
        cohort: EvidenceSlot | None = None
        if cohort_correlation is not None:
            if not isinstance(cohort_correlation, EvidenceSlot):
                return invalid(
                    "cohort_correlation",
                    "cohort-correlation evidence is an EvidenceSlot when present",
                    given=repr(cohort_correlation),
                )
            cohort = cohort_correlation
        return _Ok(cls(sqs_reading=sqs, cohort_correlation=cohort))

    def is_empty(self) -> bool:
        """True when no evidence slot is cited (an entry may cite none)."""
        return self.sqs_reading is None and self.cohort_correlation is None

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — optional slots only when present."""
        content: dict[str, object] = {
            "class": "cited-evidence",
            "format_version": _DOOR_FORMAT_VERSION,
        }
        if self.sqs_reading is not None:
            content["sqs_reading"] = self.sqs_reading.fp1_identity()
        if self.cohort_correlation is not None:
            content["cohort_correlation"] = self.cohort_correlation.fp1_identity()
        return content


# --- ExitLogicRef and its module-mode registry -------------------------------


@dataclass(frozen=True, slots=True)
class ExitLogicRef:
    """A Book's per-family exit-method declaration, ``{module_id, config}`` (CT-22; DEC-0147).

    Exit method is a **declaration, not code in the Book**: the Book's ``exit_policy``
    declares an :class:`ExitLogicRef` per strategy family, and the Book door executes it
    at admission to derive the declared full-loss price — no Book module is ever injected
    into bot logic (DEC-0147, DEC-0179). ``config`` is opaque string configuration, frozen
    on construction. A ``module_id`` naming a registered :class:`ExitLogicMode` is gated on
    that mode's required CT-23 format version (:func:`check_exit_logic_mode_available`).
    """

    module_id: str
    config: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", MappingProxyType(dict(self.config)))

    @classmethod
    def try_create(cls, module_id: object, config: object = None) -> Result[ExitLogicRef]:
        """Validate and build an :class:`ExitLogicRef`, value-or-refusal."""
        module_token = clean_str(module_id)
        if module_token is None:
            return invalid(
                "module_id",
                "an ExitLogicRef names its module by an opaque id",
                given=repr(module_id),
            )
        resolved: dict[str, str] = {}
        if config is not None:
            if not isinstance(config, Mapping):
                return invalid(
                    "config",
                    "an ExitLogicRef config is a string-keyed mapping of string values",
                    given=type_name(config),
                )
            config_map = cast("Mapping[object, object]", config)
            for key, value in config_map.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    return invalid(
                        "config",
                        "an ExitLogicRef config carries only string keys and string values",
                        given=repr((key, value)),
                    )
                resolved[key] = value
        return _Ok(cls(module_id=module_token, config=resolved))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the exit-logic reference."""
        return {
            "class": "exit-logic-ref",
            "module_id": self.module_id,
            "config": dict(self.config),
            "format_version": _DOOR_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ExitLogicMode:
    """A registered ExitLogicRef module mode and its declared input contract (AC5).

    ``mode_id`` is the ``ExitLogicRef.module_id`` that selects this mode; ``input_field``
    names the CT-23 field the mode consumes; ``required_ct23_format_version`` is the
    minimum CT-23 contract format version at which that input field exists. Invoking a mode
    whose required version exceeds the door's active version is an ``unavailable
    dependency`` refusal (:func:`check_exit_logic_mode_available`) — the field the mode
    depends on is not yet minted (DEC-0177, DEC-0182).
    """

    mode_id: str
    input_field: str
    required_ct23_format_version: int
    description: str


# The adopt-the-bot's-advisory-stop mode (operator veto round; DEC-0185, DEC-0177):
# "adopt the bot's advisory stop proposal (CT-23) as-is, validated against the Book's
# risk rules", so a bot that carries its own exit/stop methodology is honored rather
# than overridden. Its input contract is the CT-23 FORMAT-2 entry.advisory_stop_proposal
# field, minted by the QML increment (Story 11.7, SC-05); at the active format 1 the
# field does not exist, so invoking the mode is an unavailable-dependency refusal.
ADOPT_BOT_ADVISORY_STOP_MODE_ID: Final[str] = "adopt_bot_advisory_stop"
ADOPT_BOT_ADVISORY_STOP_MODE: Final[ExitLogicMode] = ExitLogicMode(
    mode_id=ADOPT_BOT_ADVISORY_STOP_MODE_ID,
    input_field="entry.advisory_stop_proposal",
    required_ct23_format_version=CT23_ADVISORY_STOP_FORMAT_VERSION,
    description=(
        "adopt the bot's advisory stop proposal as-is, validated against the Book's risk "
        "rules; requested_r stays Book-resolved and the frozen R faces stay frozen"
    ),
)

# The ExitLogicRef mode registry — recognized module modes with their declared input
# contracts and required CT-23 format versions (addable never redefined; AC5).
EXIT_LOGIC_MODE_REGISTRY: Final[Mapping[str, ExitLogicMode]] = MappingProxyType(
    {ADOPT_BOT_ADVISORY_STOP_MODE.mode_id: ADOPT_BOT_ADVISORY_STOP_MODE}
)


@runtime_checkable
class ExitLogicModule(Protocol):
    """The door-side seam a Book's :class:`ExitLogicRef` executes to derive a stop (DEC-0147).

    The Book door invokes this Protocol at admission to derive the declared full-loss
    price from the intent's cited evidence — the module is a **door-side** seam, never
    injected into bot logic. The actual per-family arithmetic is application/node territory
    (DEC-0142); qmf-risk defines the seam and enforces the invariant that a genuine
    loss-side price must resolve (:func:`derive_full_loss_price_at_door`). An implementation
    returns a resolved full-loss :class:`~qmf.core.Price`, or :func:`refuse_no_full_loss_price`
    when its evidence yields no planned loss point.
    """

    def derive_full_loss_price(
        self, *, entry_price: Price, direction: Direction, cited_evidence: CitedEvidence
    ) -> Result[Price]:
        """Derive the declared full-loss price, or a refusal, from the cited evidence."""
        ...


def refuse_no_full_loss_price(**context: object) -> TypedRefusal:
    """The canonical ``invalid input`` refusal for an entry that resolves to no price (AC2).

    No price -> no ``original_risk_distance`` -> no admission: a strategy that deliberately
    runs with no planned loss point cannot trade in QMX (DEC-0154). An
    :class:`ExitLogicModule` returns this when its cited evidence yields no loss point.
    """
    return invalid(
        "declared_full_loss_price",
        "the per-family ExitLogicRef resolved no full-loss price from the cited evidence; no "
        "price, no original_risk_distance, no admission",
        **context,
    )


def check_exit_logic_mode_available(
    module_id: object, *, ct23_format_version: object = CT23_ACTIVE_FORMAT_VERSION
) -> Result[ExitLogicMode | None]:
    """Gate a Book's ExitLogicRef module on its required CT-23 format version (AC5).

    Returns the registered :class:`ExitLogicMode` when the door's active
    ``ct23_format_version`` meets the mode's requirement; ``Ok(None)`` when ``module_id``
    names no registered mode (a generic format-1 module, no special gating). A registered
    mode whose ``required_ct23_format_version`` exceeds the active version — the
    adopt-the-bot's-advisory-stop mode while CT-23 sits at format 1 — is an ``unavailable
    dependency`` refusal, because the CT-23 field it consumes is not yet minted (DEC-0177,
    DEC-0182).
    """
    token = clean_str(module_id)
    if token is None:
        return invalid(
            "module_id", "the mode gate reads an ExitLogicRef module id", given=repr(module_id)
        )
    if isinstance(ct23_format_version, bool) or not isinstance(ct23_format_version, int):
        return invalid(
            "ct23_format_version",
            "the door's active CT-23 contract format version is an integer",
            given=repr(ct23_format_version),
        )
    mode = EXIT_LOGIC_MODE_REGISTRY.get(token)
    if mode is None:
        return _Ok(None)
    if mode.required_ct23_format_version > ct23_format_version:
        return unavailable(
            "exit_logic_mode",
            "this ExitLogicRef mode consumes a CT-23 field minted at a later contract format "
            "version than the door's active one; invoking it now is an unavailable-dependency "
            "refusal — requested_r stays Book-resolved and the frozen R faces stay frozen",
            mode_id=mode.mode_id,
            input_field=mode.input_field,
            required_ct23_format_version=mode.required_ct23_format_version,
            active_ct23_format_version=ct23_format_version,
        )
    return _Ok(mode)


# --- the inbound intent families ---------------------------------------------


def _require_advisory_r(field: str, value: object) -> ExactRational | TypedRefusal:
    """Resolve an advisory ``proposed_r`` — an ``r-multiple`` :class:`~qmf.core.ExactRational`."""
    if not isinstance(value, ExactRational) or value.unit_kind is not UnitKind.R_MULTIPLE:
        return invalid(
            field,
            "proposed_r is an advisory r-multiple (a dimensionless ExactRational of unit-kind "
            "r-multiple), never the sized value",
            given=repr(value),
        )
    return value


@dataclass(frozen=True, slots=True)
class EntryIntent:
    """An inbound entry proposal — the bot proposes, the Book resolves (AC2; DEC-0147).

    Carries the ``instrument``, the ``direction``, an advisory :attr:`proposed_r` (optional
    — never the sized value), a typed :class:`ReasonCode`, the
    :class:`~qmf.risk.paper.ExecutionTarget`, and its cited evidence slots. It carries **no**
    ``requested_r`` (the bot may not size — AC1) and **no** bot-supplied full-loss price: the
    Book derives the declared full-loss price at the door from the cited evidence via the
    per-family :class:`ExitLogicRef` (DEC-0147, DEC-0154, DEC-0177).
    """

    instrument: Instrument
    direction: Direction
    reason_code: ReasonCode
    execution_target: ExecutionTarget
    proposed_r: ExactRational | None = None
    cited_evidence: CitedEvidence | None = None

    @classmethod
    def try_create(
        cls,
        instrument: object,
        direction: object,
        reason_code: object,
        execution_target: object,
        *,
        proposed_r: object = None,
        cited_evidence: object = None,
    ) -> Result[EntryIntent]:
        """Validate and build an :class:`EntryIntent`, value-or-refusal."""
        if not isinstance(instrument, Instrument):
            return invalid(
                "instrument",
                "an entry intent names the CT-03 instrument the position opens on",
                given=repr(instrument),
            )
        resolved_direction = coerce_enum(Direction, direction)
        if resolved_direction is None:
            return invalid(
                "direction",
                "an entry intent declares its direction (long|short)",
                given=repr(direction),
                allowed=[member.value for member in Direction],
            )
        if not isinstance(reason_code, ReasonCode):
            return invalid(
                "reason_code",
                "an entry intent carries a typed reason code",
                given=repr(reason_code),
            )
        if not isinstance(execution_target, ExecutionTarget):
            return invalid(
                "execution_target",
                "an entry intent carries the per-intent execution target",
                given=repr(execution_target),
            )
        resolved_r: ExactRational | None = None
        if proposed_r is not None:
            checked = _require_advisory_r("proposed_r", proposed_r)
            if isinstance(checked, TypedRefusal):
                return checked
            resolved_r = checked
        resolved_evidence: CitedEvidence | None = None
        if cited_evidence is not None:
            if not isinstance(cited_evidence, CitedEvidence):
                return invalid(
                    "cited_evidence",
                    "cited evidence is a CitedEvidence set of declared slots",
                    given=repr(cited_evidence),
                )
            resolved_evidence = cited_evidence
        return _Ok(
            cls(
                instrument=instrument,
                direction=resolved_direction,
                reason_code=reason_code,
                execution_target=execution_target,
                proposed_r=resolved_r,
                cited_evidence=resolved_evidence,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — optional fields only when present."""
        content: dict[str, object] = {
            "class": "entry-intent",
            "intent_family": IntentFamily.ENTRY.value,
            "instrument": {"venue": self.instrument.venue.value, "symbol": self.instrument.symbol},
            "direction": self.direction.value,
            "reason_code": self.reason_code.fp1_identity(),
            "execution_target": self.execution_target.fp1_identity(),
            "format_version": _DOOR_FORMAT_VERSION,
        }
        if self.proposed_r is not None:
            content["proposed_r"] = self.proposed_r.fp1_identity()
        if self.cited_evidence is not None:
            content["cited_evidence"] = self.cited_evidence.fp1_identity()
        return content


@dataclass(frozen=True, slots=True)
class TightenProtectiveStop:
    """A ``tighten_protective_stop``'s direction and bound — **never a price** (AC3).

    Names a :class:`StopMoveDirection` and a :class:`~qmf.core.PriceDelta` ``bound`` (a
    positive magnitude), never an absolute price: the Book's policy resolves the level,
    which keeps R single-authored and enacts the move through CT-19 ``amend_protection``,
    risk-non-increasing against the frozen ``original_risk_distance`` (DEC-0147, DEC-0148,
    DEC-0154). A :class:`~qmf.core.Price` in place of a bound is an ``invalid input``
    refusal; a :attr:`StopMoveDirection.WIDEN` direction is a
    :attr:`RiskMonotonicViolation.WIDEN_STOP` ``policy rejection`` (AC4).
    """

    direction: StopMoveDirection
    bound: PriceDelta

    @classmethod
    def try_create(cls, direction: object, bound: object) -> Result[TightenProtectiveStop]:
        """Validate and build a :class:`TightenProtectiveStop`, value-or-refusal."""
        resolved_direction = coerce_enum(StopMoveDirection, direction)
        if resolved_direction is None:
            return invalid(
                "direction",
                "a tighten names a stop-move direction (tighten); a widen is a risk-monotonic "
                "policy rejection, and any other value is invalid",
                given=repr(direction),
                allowed=[member.value for member in StopMoveDirection],
            )
        if resolved_direction is StopMoveDirection.WIDEN:
            return reject_risk_monotonic_violation(
                RiskMonotonicViolation.WIDEN_STOP,
                detail="a tighten_protective_stop may never widen a stop",
            )
        if isinstance(bound, Price):
            return invalid(
                "bound",
                "a tighten names a direction and a BOUND (a PriceDelta magnitude), never a price; "
                "the Book's policy resolves the level",
                given=repr(bound),
            )
        if not isinstance(bound, PriceDelta):
            return invalid(
                "bound",
                "a tighten bound is a PriceDelta magnitude from instrument metadata",
                given=repr(bound),
            )
        if bound.as_fraction() <= 0:
            return invalid(
                "bound",
                "a tighten bound is a positive magnitude; a zero or negative bound is not a move",
                given=str(bound.as_fraction()),
            )
        return _Ok(cls(direction=resolved_direction, bound=bound))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the tighten direction-and-bound."""
        return {
            "class": "tighten-protective-stop",
            "direction": self.direction.value,
            "bound": self.bound.fp1_identity(),
            "format_version": _DOOR_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ExitIntent:
    """An inbound exit proposal — risk-monotonic by construction (AC3; DEC-0147).

    Carries the :class:`ExitKind`, a typed :class:`ReasonCode`, and the
    ``virtual_position_ref`` (the AD-40 virtual Book position, never the venue position). A
    :attr:`ExitKind.TIGHTEN_PROTECTIVE_STOP` carries its :class:`TightenProtectiveStop`
    (direction and bound, never a price); a :attr:`ExitKind.CLOSE_FULL` carries none.
    ``close_partial`` is an ``unsupported capability`` refusal (:func:`reject_close_partial`).
    """

    kind: ExitKind
    reason_code: ReasonCode
    virtual_position_ref: Fingerprint
    tighten: TightenProtectiveStop | None = None

    @classmethod
    def try_create(
        cls,
        kind: object,
        reason_code: object,
        virtual_position_ref: object,
        *,
        tighten: object = None,
    ) -> Result[ExitIntent]:
        """Validate and build an :class:`ExitIntent`, value-or-refusal.

        A ``close_partial`` kind is an ``unsupported capability`` refusal (not ``invalid
        input``); any other unknown kind is ``invalid input``. A tighten requires its
        direction-and-bound; a close_full must carry none.
        """
        if isinstance(kind, str) and kind == _CLOSE_PARTIAL:
            return reject_close_partial()
        resolved_kind = coerce_enum(ExitKind, kind)
        if resolved_kind is None:
            return invalid(
                "kind",
                "an exit intent's kind is one of the V1 kinds (close_full|tighten_protective_stop)",
                given=repr(kind),
                allowed=[member.value for member in ExitKind],
            )
        if not isinstance(reason_code, ReasonCode):
            return invalid(
                "reason_code",
                "an exit intent carries a typed reason code (the evidence half of fast "
                "invalidation)",
                given=repr(reason_code),
            )
        if not isinstance(virtual_position_ref, Fingerprint):
            return invalid(
                "virtual_position_ref",
                "an exit intent targets the virtual (Book) position by fingerprint, never the "
                "venue position",
                given=repr(virtual_position_ref),
            )
        resolved_tighten: TightenProtectiveStop | None = None
        if resolved_kind is ExitKind.TIGHTEN_PROTECTIVE_STOP:
            if not isinstance(tighten, TightenProtectiveStop):
                return invalid(
                    "tighten",
                    "a tighten_protective_stop carries its direction and bound (a "
                    "TightenProtectiveStop), never a price",
                    given=repr(tighten),
                )
            resolved_tighten = tighten
        elif tighten is not None:
            return invalid(
                "tighten",
                "a close_full carries no tighten direction-and-bound (present only on a "
                "tighten_protective_stop)",
                given=repr(tighten),
            )
        return _Ok(
            cls(
                kind=resolved_kind,
                reason_code=reason_code,
                virtual_position_ref=virtual_position_ref,
                tighten=resolved_tighten,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the tighten only when present."""
        content: dict[str, object] = {
            "class": "exit-intent",
            "intent_family": IntentFamily.EXIT.value,
            "kind": self.kind.value,
            "reason_code": self.reason_code.fp1_identity(),
            "virtual_position_ref": self.virtual_position_ref.value,
            "format_version": _DOOR_FORMAT_VERSION,
        }
        if self.tighten is not None:
            content["tighten"] = self.tighten.fp1_identity()
        return content


@dataclass(frozen=True, slots=True)
class RiskEvaluationRequest:
    """One CT-23 request — exactly one intent family plus declared evidence (AC1; DEC-0147).

    The discriminant :attr:`family` names exactly one of :class:`EntryIntent` or
    :class:`ExitIntent`; a request carrying both, or neither, is an ``invalid input``
    refusal. Evidence slots ride the intent that cites them; this container holds the
    resolved family and its intent — **nothing else enters the Book through it**.
    """

    family: IntentFamily
    entry: EntryIntent | None = None
    exit: ExitIntent | None = None

    @classmethod
    def try_create(
        cls, *, entry: object = None, exit: object = None
    ) -> Result[RiskEvaluationRequest]:
        """Validate and build a :class:`RiskEvaluationRequest`, value-or-refusal.

        Exactly one family must be present: both present, or neither, is ``invalid input``
        (a request is exactly one of two families and nothing else).
        """
        if entry is not None and exit is not None:
            return invalid(
                "intent_family",
                "a request is EXACTLY ONE of two families — entry or exit — never both",
            )
        if entry is not None:
            if not isinstance(entry, EntryIntent):
                return invalid(
                    "entry", "the entry family carries an EntryIntent", given=repr(entry)
                )
            return _Ok(cls(family=IntentFamily.ENTRY, entry=entry))
        if exit is not None:
            if not isinstance(exit, ExitIntent):
                return invalid("exit", "the exit family carries an ExitIntent", given=repr(exit))
            return _Ok(cls(family=IntentFamily.EXIT, exit=exit))
        return invalid(
            "intent_family",
            "a request is exactly one of two families — entry or exit; neither was present",
        )


# --- the inbound guards: no sizing, and forward-compatible parsing -----------


def reject_inbound_requested_r(fields: object) -> Result[None]:
    """Refuse an inbound ``requested_r`` — the bot may not size (AC1; DEC-0147, DEC-0154).

    ``requested_r`` is Book-resolved and never carried inbound: a Bot that sized itself
    would invert the authority order ``bot -> book -> BMS -> operator``. An inbound field
    mapping carrying a ``requested_r`` key is an ``invalid input`` refusal; a mapping
    without it returns ``Ok(None)``.
    """
    if not isinstance(fields, Mapping):
        return invalid(
            "fields",
            "the inbound-sizing guard reads the request's field mapping",
            given=type_name(fields),
        )
    mapping = cast("Mapping[str, object]", fields)
    if _REQUESTED_R_FIELD in mapping:
        return invalid(
            _REQUESTED_R_FIELD,
            "requested_r is Book-resolved and never carried inbound; the bot may not size — a "
            "bot-supplied requested_r inverts the authority order",
        )
    return _Ok(None)


def parse_inbound_intent(
    raw: object, *, ct23_format_version: object = CT23_ACTIVE_FORMAT_VERSION
) -> Result[RiskEvaluationRequest]:
    """Parse a wire-form intent, forward-compatibly, into a :class:`RiskEvaluationRequest`.

    Enforces the door's wire-level rules:

    * an inbound ``requested_r`` is an ``invalid input`` refusal — the bot may not size
      (AC1; :func:`reject_inbound_requested_r`);
    * a declared ``contract_format_version`` this build does not understand is an
      ``unsupported capability`` refusal (an unknown version is never best-effort read),
      while an absent one assumes the door's active version (AC6);
    * **an unknown optional field never breaks a format-1 consumer** — unrecognized keys
      under a known format version are ignored, so a format-2 field (e.g. a future
      ``advisory_stop_proposal``) on a format-1 artifact is dropped, never a refusal
      (AD-5; AC6);
    * the ``intent_family`` discriminant selects exactly one already-typed family value
      (``entry`` -> :class:`EntryIntent`, ``exit`` -> :class:`ExitIntent`); both or
      neither is ``invalid input`` (AC1).

    ``raw`` is a field mapping of already-typed values (the door works in typed Python
    values, not serialized bytes). ``ct23_format_version`` is the door's active version.
    """
    if not isinstance(raw, Mapping):
        return invalid(
            "raw", "an inbound intent is a field mapping of typed values", given=type_name(raw)
        )
    mapping = cast("Mapping[str, object]", raw)
    if isinstance(ct23_format_version, bool) or not isinstance(ct23_format_version, int):
        return invalid(
            "ct23_format_version",
            "the door's active CT-23 contract format version is an integer",
            given=repr(ct23_format_version),
        )
    declared_version = mapping.get("contract_format_version")
    if declared_version is not None and (
        isinstance(declared_version, bool)
        or not isinstance(declared_version, int)
        or declared_version not in CT23_KNOWN_FORMAT_VERSIONS
    ):
        return _unsupported_version(declared_version)
    guard = reject_inbound_requested_r(mapping)
    if is_refusal(guard):
        return guard
    family_value = mapping.get("intent_family")
    resolved_family = coerce_enum(IntentFamily, family_value)
    if resolved_family is None:
        return invalid(
            "intent_family",
            "a request declares exactly one family — entry or exit",
            given=repr(family_value),
            allowed=[member.value for member in IntentFamily],
        )
    if resolved_family is IntentFamily.ENTRY:
        entry = mapping.get("entry")
        if not isinstance(entry, EntryIntent):
            return invalid(
                "entry",
                "an entry-family request carries a typed EntryIntent under the 'entry' key",
                given=repr(entry),
            )
        # Unknown optional fields (an 'exit' key would contradict the family, a future
        # format-2 field, or any other unrecognized key) are ignored under this known
        # format version — an unknown optional field never breaks a format-1 consumer.
        return RiskEvaluationRequest.try_create(entry=entry)
    exit_intent = mapping.get("exit")
    if not isinstance(exit_intent, ExitIntent):
        return invalid(
            "exit",
            "an exit-family request carries a typed ExitIntent under the 'exit' key",
            given=repr(exit_intent),
        )
    return RiskEvaluationRequest.try_create(exit=exit_intent)


def _unsupported_version(declared_version: object) -> TypedRefusal:
    """The ``unsupported capability`` refusal for an unknown CT-23 contract format version."""
    return unsupported(
        "contract_format_version",
        "a CT-23 contract format version this build does not understand; an unknown version is "
        "never best-effort read, and format-1 artifacts stay readable forever",
        given=repr(declared_version),
        understood=sorted(CT23_KNOWN_FORMAT_VERSIONS),
    )


# --- the Book door: derive the full-loss price and admit the entry -----------


def derive_full_loss_price_at_door(
    *,
    exit_logic_ref: object,
    module: object,
    entry_price: object,
    direction: object,
    cited_evidence: object = None,
    ct23_format_version: object = CT23_ACTIVE_FORMAT_VERSION,
) -> Result[Price]:
    """Derive the declared full-loss price at the Book door via the per-family ExitLogicRef (AC2).

    The Book executes its own per-family :class:`ExitLogicRef` — never a Book module injected
    into bot logic — consuming the intent's cited evidence to derive the declared full-loss
    price (DEC-0147, DEC-0177). The steps:

    1. **gate the mode** on its required CT-23 format version — the adopt-the-bot's-advisory-stop
       mode while CT-23 sits at format 1 is an ``unavailable dependency`` refusal (AC5);
    2. **execute the module seam** (:class:`ExitLogicModule`), which returns a resolved
       full-loss :class:`~qmf.core.Price` or a refusal;
    3. **enforce the loss-side invariant** — the derived price must sit on the loss side of
       ``entry_price`` for the ``direction`` (via
       :func:`~qmf.risk.r_faces.derive_original_risk_distance`), else it is not a planned loss
       point and is refused (no price, no admission — AC2).
    """
    if not isinstance(exit_logic_ref, ExitLogicRef):
        return invalid(
            "exit_logic_ref",
            "the door executes the Book's per-family ExitLogicRef",
            given=repr(exit_logic_ref),
        )
    if not isinstance(module, ExitLogicModule):
        return invalid(
            "module",
            "the ExitLogicRef module is an ExitLogicModule seam supplied by the composition root",
            given=repr(module),
        )
    if not isinstance(entry_price, Price):
        return invalid(
            "entry_price",
            "the door derives the full-loss price relative to the resolved entry Price",
            given=repr(entry_price),
        )
    resolved_direction = coerce_enum(Direction, direction)
    if resolved_direction is None:
        return invalid(
            "direction",
            "the door derives the full-loss price for a declared direction (long|short)",
            given=repr(direction),
            allowed=[member.value for member in Direction],
        )
    if cited_evidence is None:
        evidence = CitedEvidence()
    elif isinstance(cited_evidence, CitedEvidence):
        evidence = cited_evidence
    else:
        return invalid(
            "cited_evidence",
            "cited evidence is a CitedEvidence set of declared slots",
            given=repr(cited_evidence),
        )
    availability = check_exit_logic_mode_available(
        exit_logic_ref.module_id, ct23_format_version=ct23_format_version
    )
    if is_refusal(availability):
        return availability
    derived = module.derive_full_loss_price(
        entry_price=entry_price, direction=resolved_direction, cited_evidence=evidence
    )
    if is_refusal(derived):
        return derived
    price = derived.value
    # The derived price must be a genuine loss point (loss side of entry for the direction);
    # otherwise no original_risk_distance resolves and there is no admission (AC2; DEC-0154).
    distance = derive_original_risk_distance(entry_price, price, resolved_direction)
    if is_refusal(distance):
        return distance
    return _Ok(price)


@dataclass(frozen=True, slots=True)
class AdmittedEntry:
    """A Book-admitted entry — the Book-resolved, single-sited, frozen result (AC2; DEC-0147).

    Carries the bot's advisory declaration (``instrument``, ``direction``, advisory
    ``proposed_r``, ``reason_code``, ``execution_target``, cited evidence) plus the two
    values the **Book** resolves and stamps at the door: the ``declared_full_loss_price``
    (derived by the per-family ExitLogicRef from the cited evidence) and the Book-resolved
    ``requested_r``, together with the derived ``original_risk_distance``. Both Book-stamped
    values are minted **once** here and this value is immutable — **R stays frozen in every
    mode** and ``requested_r`` is never bot-supplied (DEC-0147, DEC-0154, DEC-0177).
    """

    instrument: Instrument
    direction: Direction
    reason_code: ReasonCode
    execution_target: ExecutionTarget
    declared_full_loss_price: Price
    original_risk_distance: PriceDelta
    requested_r: ExactRational
    proposed_r: ExactRational | None = None
    cited_evidence: CitedEvidence | None = None

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — enters the command record's identity."""
        content: dict[str, object] = {
            "class": "admitted-entry",
            "instrument": {"venue": self.instrument.venue.value, "symbol": self.instrument.symbol},
            "direction": self.direction.value,
            "reason_code": self.reason_code.fp1_identity(),
            "execution_target": self.execution_target.fp1_identity(),
            "declared_full_loss_price": self.declared_full_loss_price.fp1_identity(),
            "original_risk_distance": self.original_risk_distance.fp1_identity(),
            "requested_r": self.requested_r.fp1_identity(),
            "format_version": _DOOR_FORMAT_VERSION,
        }
        if self.proposed_r is not None:
            content["proposed_r"] = self.proposed_r.fp1_identity()
        if self.cited_evidence is not None:
            content["cited_evidence"] = self.cited_evidence.fp1_identity()
        return content


def admit_entry_intent(
    *,
    intent: object,
    entry_price: object,
    exit_logic_ref: object,
    module: object,
    book_resolved_requested_r: object,
    ct23_format_version: object = CT23_ACTIVE_FORMAT_VERSION,
    has_open_position: bool = False,
) -> Result[AdmittedEntry]:
    """Admit an entry intent at the Book door — Book-resolved sizing, Book-derived price (AC2).

    The door, never the bot:

    * refuses a scale-in — V1 admits none, adding to an open position is a ``policy
      rejection`` (:func:`~qmf.risk.r_faces.check_no_scale_in`);
    * requires ``requested_r`` to be **Book-resolved** — a dimensionless ``r-multiple`` the
      Book computed, never a bot-supplied value (the bot may not size — AC1);
    * **derives the declared full-loss price at the door** via the per-family
      :class:`ExitLogicRef` (:func:`derive_full_loss_price_at_door`), gating the
      adopt-the-bot's-advisory-stop mode to an ``unavailable dependency`` refusal while CT-23
      sits at format 1 (AC5);
    * stamps the derived price and the Book-resolved ``requested_r`` onto a frozen
      :class:`AdmittedEntry`, single-sited and minted once (R stays frozen in every mode).

    ``has_open_position`` is the seat's open-position state (a scale-in guard input).
    """
    if not isinstance(intent, EntryIntent):
        return invalid("intent", "the entry door admits an EntryIntent", given=repr(intent))
    scale_in = check_no_scale_in(has_open_position)
    if is_refusal(scale_in):
        return scale_in
    if (
        not isinstance(book_resolved_requested_r, ExactRational)
        or book_resolved_requested_r.unit_kind is not UnitKind.R_MULTIPLE
    ):
        return invalid(
            "book_resolved_requested_r",
            "requested_r is Book-resolved — a dimensionless r-multiple the Book computed, never a "
            "bot-supplied value (the bot may not size)",
            given=repr(book_resolved_requested_r),
        )
    if not isinstance(entry_price, Price):
        return invalid(
            "entry_price",
            "admission derives the full-loss price relative to the resolved entry Price",
            given=repr(entry_price),
        )
    price = derive_full_loss_price_at_door(
        exit_logic_ref=exit_logic_ref,
        module=module,
        entry_price=entry_price,
        direction=intent.direction,
        cited_evidence=intent.cited_evidence,
        ct23_format_version=ct23_format_version,
    )
    if is_refusal(price):
        return price
    distance = derive_original_risk_distance(entry_price, price.value, intent.direction)
    if is_refusal(distance):
        return distance
    return _Ok(
        AdmittedEntry(
            instrument=intent.instrument,
            direction=intent.direction,
            reason_code=intent.reason_code,
            execution_target=intent.execution_target,
            declared_full_loss_price=price.value,
            original_risk_distance=distance.value,
            requested_r=book_resolved_requested_r,
            proposed_r=intent.proposed_r,
            cited_evidence=intent.cited_evidence,
        )
    )


# --- exit evaluation and the risk-monotonic law ------------------------------


def reject_close_partial(**context: object) -> TypedRefusal:
    """The ``unsupported capability`` refusal for a ``close_partial`` exit (AC3; DEC-0147).

    ``close_partial`` is not a V1 kind — the five-command vocabulary expresses no fractional
    close, and a close-then-replace would open the unprotected window ``amend_protection``
    forbids; partial-close stays a Deferred later CT-19 mint. Returned, never raised.
    """
    return unsupported(
        "exit.kind",
        "close_partial is not a V1 exit kind; a partial exit is an unsupported-capability refusal "
        "(the command vocabulary expresses no fractional close)",
        **context,
    )


def reject_risk_monotonic_violation(
    violation: object, *, detail: str | None = None
) -> TypedRefusal:
    """The ``policy rejection`` for a named risk-monotonic violation (AC4; DEC-0147).

    An intent may never widen a stop, extend a target beyond the Book's declared envelope,
    re-open a closed position, or increase size — each is a :class:`RiskMonotonicViolation`
    and a ``policy rejection``. Returned, never raised.
    """
    resolved = coerce_enum(RiskMonotonicViolation, violation)
    if resolved is None:
        return invalid(
            "violation",
            "a risk-monotonic violation is one of the four classes",
            given=repr(violation),
            allowed=[member.value for member in RiskMonotonicViolation],
        )
    reason = detail or f"an intent may never {resolved.value.replace('-', ' ')}"
    return policy(
        "risk_monotonic",
        f"risk-monotonic violation ({resolved.value}): {reason} — the door never widens risk",
        violation=resolved.value,
    )


def evaluate_exit_intent(exit_intent: object) -> Result[ExitIntent]:
    """Evaluate an inbound exit intent against the door's V1 vocabulary (AC3; DEC-0147).

    A well-formed :class:`ExitIntent` — one of the two V1 kinds, a typed reason code, and a
    tighten's direction-and-bound never a price — passes and is returned unchanged. The
    construction rules (``close_partial`` an ``unsupported capability`` refusal, a widen a
    ``policy rejection``, a price-in-place-of-a-bound an ``invalid input`` refusal) are
    enforced by :meth:`ExitIntent.try_create` / :meth:`TightenProtectiveStop.try_create`;
    this door accepts only an already-validated :class:`ExitIntent`.
    """
    if not isinstance(exit_intent, ExitIntent):
        return invalid(
            "exit_intent",
            "the exit door evaluates a validated ExitIntent (built through ExitIntent.try_create)",
            given=repr(exit_intent),
        )
    return _Ok(exit_intent)


def _require_same_instrument_deltas(
    field: str, left: PriceDelta, right: object
) -> PriceDelta | TypedRefusal:
    """Resolve ``right`` as a :class:`~qmf.core.PriceDelta` of the same instrument as ``left``."""
    if not isinstance(right, PriceDelta):
        return invalid(field, "a risk-monotonic comparison reads a PriceDelta", given=repr(right))
    if right.instrument != left.instrument:
        return invalid(
            field,
            "a risk-monotonic distance comparison is between deltas of the same instrument",
            left=repr(left.instrument),
            right=repr(right.instrument),
        )
    return right


def check_stop_not_widened(
    *, original_risk_distance: object, proposed_risk_distance: object
) -> Result[None]:
    """Refuse a stop move that widens risk (AC4; DEC-0147, DEC-0154).

    A protective-stop move is risk-non-increasing measured against the **frozen**
    ``original_risk_distance``: a proposed loss-direction distance strictly greater than the
    original widens the stop and is a :attr:`RiskMonotonicViolation.WIDEN_STOP` ``policy
    rejection`` (a ratchet passing entry into profit — an equal or smaller distance — stays
    legal). Both distances are same-instrument :class:`~qmf.core.PriceDelta` magnitudes.
    """
    if not isinstance(original_risk_distance, PriceDelta):
        return invalid(
            "original_risk_distance",
            "the frozen original_risk_distance is a PriceDelta",
            given=repr(original_risk_distance),
        )
    proposed = _require_same_instrument_deltas(
        "proposed_risk_distance", original_risk_distance, proposed_risk_distance
    )
    if isinstance(proposed, TypedRefusal):
        return proposed
    if proposed.as_fraction() > original_risk_distance.as_fraction():
        return reject_risk_monotonic_violation(
            RiskMonotonicViolation.WIDEN_STOP,
            detail="the proposed stop distance exceeds the frozen original_risk_distance",
        )
    return _Ok(None)


def check_target_within_envelope(
    *, proposed_target_distance: object, envelope_bound: object
) -> Result[None]:
    """Refuse a target that extends beyond the Book's declared envelope (AC4; DEC-0147).

    A proposed target distance strictly greater than the Book's declared envelope bound is a
    :attr:`RiskMonotonicViolation.EXTEND_TARGET_BEYOND_ENVELOPE` ``policy rejection``. Both
    are same-instrument :class:`~qmf.core.PriceDelta` magnitudes; a target within the
    envelope returns ``Ok(None)``.
    """
    if not isinstance(envelope_bound, PriceDelta):
        return invalid(
            "envelope_bound",
            "the Book's declared target envelope is a PriceDelta bound",
            given=repr(envelope_bound),
        )
    proposed = _require_same_instrument_deltas(
        "proposed_target_distance", envelope_bound, proposed_target_distance
    )
    if isinstance(proposed, TypedRefusal):
        return proposed
    if proposed.as_fraction() > envelope_bound.as_fraction():
        return reject_risk_monotonic_violation(
            RiskMonotonicViolation.EXTEND_TARGET_BEYOND_ENVELOPE,
            detail="the proposed target distance exceeds the Book's declared envelope",
        )
    return _Ok(None)


def check_no_reopen(*, position_is_closed: object) -> Result[None]:
    """Refuse re-opening a closed position (AC4; DEC-0147).

    An intent against an already-closed virtual position re-opens it and is a
    :attr:`RiskMonotonicViolation.RE_OPEN` ``policy rejection``. ``position_is_closed`` is a
    bool; ``True`` refuses, ``False`` returns ``Ok(None)``.
    """
    if not isinstance(position_is_closed, bool):
        return invalid(
            "position_is_closed",
            "the re-open guard reads a bool naming whether the virtual position is closed",
            given=repr(position_is_closed),
        )
    if position_is_closed:
        return reject_risk_monotonic_violation(
            RiskMonotonicViolation.RE_OPEN,
            detail="an intent may not re-open a closed position",
        )
    return _Ok(None)


def check_no_size_increase(*, current_quantity: object, proposed_quantity: object) -> Result[None]:
    """Refuse an intent that increases size (AC4; DEC-0147).

    A proposed quantity strictly greater than the current position quantity increases size
    and is a :attr:`RiskMonotonicViolation.INCREASE_SIZE` ``policy rejection`` — the door
    never widens risk. Both are :class:`~qmf.core.Quantity` values of the same unit; an equal
    or smaller proposed quantity returns ``Ok(None)``.
    """
    if not isinstance(current_quantity, Quantity):
        return invalid(
            "current_quantity",
            "the size-increase guard reads the current position Quantity",
            given=repr(current_quantity),
        )
    if not isinstance(proposed_quantity, Quantity):
        return invalid(
            "proposed_quantity",
            "the size-increase guard reads the proposed Quantity",
            given=repr(proposed_quantity),
        )
    if proposed_quantity.unit != current_quantity.unit:
        return invalid(
            "proposed_quantity",
            "a size comparison is between quantities of the same unit",
            current_unit=current_quantity.unit,
            proposed_unit=proposed_quantity.unit,
        )
    if proposed_quantity.as_fraction() > current_quantity.as_fraction():
        return reject_risk_monotonic_violation(
            RiskMonotonicViolation.INCREASE_SIZE,
            detail="the proposed quantity exceeds the current position size",
        )
    return _Ok(None)
