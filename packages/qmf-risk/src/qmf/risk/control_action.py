"""Story 10.8 — CT-30 control actions, exit-preservation, kill switch vs kill line.

The typed control-action contract on ``qmf-core`` nouns (AD-36/AD-37; DEC-0150,
DEC-0151): a bounded set of protection and lifecycle actions — ``suspend_new``,
``drain``, ``flatten``, ``resume`` — each issued by a named authority at a resolved
subject scope, journaled before dispatch as a standing intent, and arbitrated at
exactly one point per ``(VenueId, account)`` command stream by a BMS-declared rank
table, with the **exit-preservation invariant** guaranteeing no control of any
authority at any scope may ever block a risk-reducing act.

* :class:`AuthorityKind` / :class:`SubjectScope` / :class:`SatisfactionPredicate` —
  the closed CT-30 vocabularies an action carries;
* :class:`ControlActionRecord` — one typed action record (standing intent is the
  read-time fold over the stream, never a stored field);
* :func:`check_exit_preservation` / :func:`reject_blanket_command_pipe_block` —
  L39: blocking is entries only; no blanket pipe-block kind may be minted;
* :func:`resolve_subject_scope` — pinned versioned resolution table; unresolvable
  or netting-indistinguishable scopes refuse, never widen;
* :func:`journal_before_dispatch` / :func:`fold_standing_intents` /
  :func:`reevaluate_standing_intent` — standing intent, restart-proof, re-decided
  rather than retried, never time-expiring;
* :class:`KillSwitch` vs :class:`KillLine` — named apart, never merged; resume is
  operator-only;
* :func:`arbitrate_same_tick` — collapse / conflict / compose at one stream point;
* :func:`check_flatten_authority` — closed flatten-authority assignment.

qmf-risk imports **only** ``qmf-core`` (default-deny, L30/DEC-0120) and sibling
``qmf.risk`` modules; nothing imports ``qmf.risk``. Ratified ``defined-unwired``
surface — no live binding, order, or flatten is authorized here (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Fingerprint,
    Instant,
    Result,
    TypedRefusal,
    VenueId,
    fingerprint,
    is_refusal,
)
from qmf.core import (
    Ok as _Ok,
)
from qmf.risk._common import clean_str, coerce_enum, invalid, policy, type_name, unsupported
from qmf.risk.binding import PositionModel
from qmf.risk.control_rank import ControlActionKind, ControlRankTable
from qmf.risk.exit_record import CloseReason

__all__ = [
    "ACTION_CLOSE_REASON_MAPPING",
    "ADAPTER_SELF_FLATTEN_KINDS",
    "COMPOSING_KIND_PAIRS",
    "CT30_CONTRACT_FORMAT_VERSION",
    "CT30_SCOPE_RESOLUTION_TABLE_VERSION",
    "FLATTEN_AUTHORITIES",
    "MONEY_BOUNDARIES_LEAVE_POSITIONS",
    "NEVER_AUTO_KINDS",
    "PROTECTION_WEIGHT",
    "RISK_REDUCING_ACTS",
    "ArbitrationDisposition",
    "ArbitrationOutcome",
    "AuthorityKind",
    "CommandStreamKey",
    "ControlActionRecord",
    "ControlActionStream",
    "EnforcementScope",
    "KillLine",
    "KillSwitch",
    "MoneyBoundaryKind",
    "PendingControlAction",
    "ReconciliationVerdict",
    "RiskReducingAct",
    "SatisfactionPredicate",
    "ScopeResolution",
    "StandingIntentFold",
    "StandingIntentStatus",
    "SubjectScope",
    "SuppressedControlAction",
    "arbitrate_same_tick",
    "check_exit_preservation",
    "check_flatten_authority",
    "close_reason_for",
    "default_satisfaction_predicate",
    "evaluate_satisfaction",
    "fold_standing_intents",
    "journal_before_dispatch",
    "mint_control_action",
    "mint_kill_line_breach",
    "mint_kill_switch_action",
    "reevaluate_standing_intent",
    "reject_blanket_command_pipe_block",
    "reject_money_boundary_flatten",
    "resolve_subject_scope",
]

CT30_CONTRACT_FORMAT_VERSION: Final[int] = 1
CT30_SCOPE_RESOLUTION_TABLE_VERSION: Final[int] = 1


# --- closed vocabularies -----------------------------------------------------


class AuthorityKind(StrEnum):
    """Issuing-authority kinds an action carries (DEC-0150).

    ``adapter_self`` may issue ``suspend_new`` / ``drain`` (and session/throttle state)
    but never a flatten. ``venue-delegated`` names a venue-managed protection authority
    whose pushed changes mint a control-action record (e.g. protection amendment).
    """

    OPERATOR = "operator"
    BOOK_POLICY = "book_policy"
    PROTECTION_AUTHORITY = "protection_authority"
    VENUE_DELEGATED = "venue-delegated"
    ADAPTER_SELF = "adapter_self"


class SubjectScope(StrEnum):
    """Subject scope resolved at dispatch through the pinned table (DEC-0150).

    Resolved to AD-27 enforcement scopes; an unresolvable or netting-indistinguishable
    scope is an ``unsupported capability`` refusal and is never widened.
    """

    INSTRUMENT = "instrument"
    BOOK = "book"
    BINDING = "binding"
    ACCOUNT = "account"
    VENUE = "venue"
    GLOBAL = "global"


class SatisfactionPredicate(StrEnum):
    """Closed satisfaction vocabulary; ``suspend_new``/``drain`` are never-auto (DEC-0150).

    ``scope-flat-at-reconciled-verdict`` — flatten satisfies only on a reconciled
    verdict showing the scope flat (a command outcome never satisfies an intent).
    ``no-pending-orders-at-reconciled-verdict`` — drain-class clearance when declared.
    ``never-auto`` — clears only by an operator resume (automated de-escalation
    forbidden).
    """

    SCOPE_FLAT_AT_RECONCILED_VERDICT = "scope-flat-at-reconciled-verdict"
    NO_PENDING_ORDERS_AT_RECONCILED_VERDICT = "no-pending-orders-at-reconciled-verdict"
    NEVER_AUTO = "never-auto"


class ReconciliationVerdict(StrEnum):
    """AD-27 reconciliation verdict the satisfaction predicate reads (DEC-0150).

    Re-evaluation runs against ``reconciled`` only; ``drift``, ``unknown``, and
    ``out-of-lookback`` alarm and hold the intent open without dispatching.
    """

    RECONCILED = "reconciled"
    DRIFT = "drift"
    UNKNOWN = "unknown"
    OUT_OF_LOOKBACK = "out-of-lookback"


class RiskReducingAct(StrEnum):
    """Acts no control may ever block — the exit-preservation set (L39; DEC-0150)."""

    CANCEL_ORDER = "cancel_order"
    CLOSE_POSITION = "close_position"
    CLOSE_ALL = "close_all"
    AMEND_PROTECTION_RISK_NON_INCREASING = "amend_protection_risk_non_increasing"
    PROTECTION_ACTION = "protection_action"
    RECORD_EVIDENCE = "record_evidence"


class StandingIntentStatus(StrEnum):
    """Read-time standing-intent status — never a stored field (DEC-0150)."""

    OPEN = "open"
    SATISFIED = "satisfied"
    HELD_ALARM = "held-alarm"
    SUPPRESSED = "suppressed"


class ArbitrationDisposition(StrEnum):
    """How one pending action fared at the single arbitration point (DEC-0151)."""

    EMIT = "emit"
    SUPPRESSED = "suppressed"
    COMPOSE = "compose"


class MoneyBoundaryKind(StrEnum):
    """Money-accounting boundaries that leave positions alone (DEC-0150).

    Rollover, sweep, re-seed, and paper flip are never themselves flatten triggers.
    """

    ROLLOVER = "rollover"
    SWEEP = "sweep"
    RE_SEED = "re_seed"
    PAPER_FLIP = "paper_flip"


# Kinds that are never-auto by rule — clearing only by an operator resume.
NEVER_AUTO_KINDS: Final[frozenset[ControlActionKind]] = frozenset(
    {ControlActionKind.SUSPEND_NEW, ControlActionKind.DRAIN}
)

# Exit-preservation: the closed set of acts a control may never block.
RISK_REDUCING_ACTS: Final[frozenset[RiskReducingAct]] = frozenset(RiskReducingAct)

# Flatten-capable authorities (adapter_self / sensors / bots are excluded).
FLATTEN_AUTHORITIES: Final[frozenset[AuthorityKind]] = frozenset(
    {
        AuthorityKind.OPERATOR,
        AuthorityKind.BOOK_POLICY,
        AuthorityKind.PROTECTION_AUTHORITY,
    }
)

# adapter_self may never initiate a flatten (DEC-0150).
ADAPTER_SELF_FLATTEN_KINDS: Final[frozenset[ControlActionKind]] = frozenset(
    {ControlActionKind.FLATTEN}
)

MONEY_BOUNDARIES_LEAVE_POSITIONS: Final[frozenset[MoneyBoundaryKind]] = frozenset(MoneyBoundaryKind)

# Protection delivered — higher weight means more risk reduction (DEC-0151 invariant).
PROTECTION_WEIGHT: Final[Mapping[ControlActionKind, int]] = MappingProxyType(
    {
        ControlActionKind.FLATTEN: 3,
        ControlActionKind.DRAIN: 2,
        ControlActionKind.SUSPEND_NEW: 1,
        ControlActionKind.RESUME: 0,
    }
)

# Kind pairs whose effects compose — both execute (DEC-0151).
COMPOSING_KIND_PAIRS: Final[frozenset[frozenset[ControlActionKind]]] = frozenset(
    {
        frozenset({ControlActionKind.SUSPEND_NEW, ControlActionKind.FLATTEN}),
        frozenset({ControlActionKind.DRAIN, ControlActionKind.FLATTEN}),
        frozenset({ControlActionKind.SUSPEND_NEW, ControlActionKind.DRAIN}),
    }
)

# Pinned (action kind x issuing authority) -> close-reason table shared with CT-29.
# Only flatten (and protection-amendment fills) close a position; others omit the key.
ACTION_CLOSE_REASON_MAPPING: Final[MappingProxyType[tuple[str, str], CloseReason]] = (
    MappingProxyType(
        {
            (
                ControlActionKind.FLATTEN.value,
                AuthorityKind.OPERATOR.value,
            ): CloseReason.OPERATOR_CLOSE,
            (
                ControlActionKind.FLATTEN.value,
                AuthorityKind.BOOK_POLICY.value,
            ): CloseReason.KILL_LINE_FLAT,
            (
                ControlActionKind.FLATTEN.value,
                AuthorityKind.PROTECTION_AUTHORITY.value,
            ): CloseReason.PROTECTION_FORCED_FLAT,
            (
                ControlActionKind.FLATTEN.value,
                AuthorityKind.VENUE_DELEGATED.value,
            ): CloseReason.PROTECTION_AMENDMENT_FILL,
        }
    )
)


# --- identity helpers --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommandStreamKey:
    """The AD-27 ``(VenueId, account)`` command stream — one arbitration point (DEC-0151)."""

    venue_id: VenueId
    account_id: str

    @classmethod
    def try_create(cls, venue_id: object, account_id: object) -> Result[CommandStreamKey]:
        """Validate and build a :class:`CommandStreamKey`, value-or-refusal."""
        if not isinstance(venue_id, VenueId):
            return invalid(
                "venue_id",
                "a command stream is keyed by VenueId",
                given=repr(venue_id),
            )
        token = clean_str(account_id)
        if token is None:
            return invalid(
                "account_id",
                "a command stream is keyed by a non-empty account id",
                given=repr(account_id),
            )
        return _Ok(cls(venue_id=venue_id, account_id=token))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the stream key."""
        return {
            "class": "command-stream-key",
            "venue_id": self.venue_id.value,
            "account_id": self.account_id,
            "format_version": CT30_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class EnforcementScope:
    """A resolved AD-27 enforcement scope after the pinned resolution table (DEC-0150)."""

    subject_scope: SubjectScope
    scope_ref: str
    stream: CommandStreamKey

    def check_withholding(self, *, blocked_act: object) -> Result[None]:
        """Refuse any scope application that would withhold a risk-reducing act."""
        return check_exit_preservation(blocked_act=blocked_act)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the enforcement scope."""
        return {
            "class": "enforcement-scope",
            "subject_scope": self.subject_scope.value,
            "scope_ref": self.scope_ref,
            "stream": self.stream.fp1_identity(),
            "format_version": CT30_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ScopeResolution:
    """Outcome of resolving a subject scope through the pinned table (DEC-0150)."""

    enforcement: EnforcementScope
    table_version: int
    position_model: PositionModel


# --- exit-preservation -------------------------------------------------------


def check_exit_preservation(*, blocked_act: object) -> Result[None]:
    """Enforce L39: a control may never block a risk-reducing act (DEC-0150).

    ``blocked_act`` is the act a control would withhold. Naming any member of
    :data:`RISK_REDUCING_ACTS` is a ``policy rejection`` — the blocking half of any
    control is entries only, paper and live alike. Naming an unknown act is
    ``invalid input``. Naming a non-risk-reducing act (an entry) returns ``Ok(None)``.
    """
    resolved = coerce_enum(RiskReducingAct, blocked_act)
    if resolved is not None:
        return policy(
            "blocked_act",
            "the exit-preservation invariant forbids any control from blocking a "
            "risk-reducing act — cancel_order, close_position, close_all, a "
            "risk-non-increasing amend_protection, a protection action, or the "
            "recording of evidence; blocking is entries only",
            act=resolved.value,
        )
    if isinstance(blocked_act, str) and blocked_act in {"entry", "new_entry", "place_order"}:
        return _Ok(None)
    return invalid(
        "blocked_act",
        "exit-preservation reads a RiskReducingAct or an entries-only act name",
        given=repr(blocked_act),
        risk_reducing=[member.value for member in RiskReducingAct],
    )


def reject_blanket_command_pipe_block(kind: object) -> Result[ControlActionKind]:
    """Refuse any kind whose effect would be a blanket command-pipe block (L39).

    The closed CT-30 set is exactly ``suspend_new | drain | flatten | resume`` — each
    defined once. No kind whose effect is a blanket pipe block may ever be minted; an
    unknown kind is ``unsupported capability``, never silently accepted as a pipe block.
    """
    resolved = coerce_enum(ControlActionKind, kind)
    if resolved is not None:
        return _Ok(resolved)
    return unsupported(
        "action_kind",
        "no CT-30 kind whose effect is a blanket command-pipe block may be minted; the "
        "closed vocabulary is suspend_new|drain|flatten|resume",
        given=repr(kind),
        allowed=[member.value for member in ControlActionKind],
    )


# --- satisfaction defaults and flatten authority -----------------------------


def default_satisfaction_predicate(kind: object) -> Result[SatisfactionPredicate]:
    """The mandatory satisfaction predicate for a control-action kind (DEC-0150).

    ``suspend_new`` and ``drain`` are ``never-auto`` by rule; ``flatten`` is
    ``scope-flat-at-reconciled-verdict``; ``resume`` is ``never-auto`` (operator clear).
    """
    resolved = coerce_enum(ControlActionKind, kind)
    if resolved is None:
        return invalid(
            "action_kind",
            "satisfaction defaults read a ControlActionKind",
            given=repr(kind),
            allowed=[member.value for member in ControlActionKind],
        )
    if resolved in NEVER_AUTO_KINDS or resolved is ControlActionKind.RESUME:
        return _Ok(SatisfactionPredicate.NEVER_AUTO)
    return _Ok(SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT)


def check_flatten_authority(
    authority_kind: object,
    *,
    trigger_class_declared: object = False,
    protection_declares_close_all: object = False,
) -> Result[None]:
    """Gate a flatten on the closed flatten-authority assignment (DEC-0150).

    (1) operator — always, any scope, unconditional; (2) book_policy — only through
    pre-declared trigger classes; (3) protection_authority — only where node severity
    policy declares ``close_all``; (4) nobody else (adapter_self, sensors, bots).
    """
    resolved = coerce_enum(AuthorityKind, authority_kind)
    if resolved is None:
        return invalid(
            "authority_kind",
            "flatten authority reads an AuthorityKind",
            given=repr(authority_kind),
            allowed=[member.value for member in AuthorityKind],
        )
    if not isinstance(trigger_class_declared, bool):
        return invalid(
            "trigger_class_declared",
            "book_policy flatten requires a boolean pre-declared-trigger flag",
            given=repr(trigger_class_declared),
        )
    if not isinstance(protection_declares_close_all, bool):
        return invalid(
            "protection_declares_close_all",
            "protection_authority flatten requires a boolean close_all declaration flag",
            given=repr(protection_declares_close_all),
        )
    if resolved is AuthorityKind.OPERATOR:
        return _Ok(None)
    if resolved is AuthorityKind.BOOK_POLICY:
        if not trigger_class_declared:
            return policy(
                "authority_kind",
                "Book policy may flatten only through pre-declared trigger classes; an "
                "undeclared trigger flattens nothing, ever",
                authority_kind=resolved.value,
            )
        return _Ok(None)
    if resolved is AuthorityKind.PROTECTION_AUTHORITY:
        if not protection_declares_close_all:
            return policy(
                "authority_kind",
                "the protection authority may flatten only where the node's severity "
                "policy declares close_all for that severity",
                authority_kind=resolved.value,
            )
        return _Ok(None)
    return policy(
        "authority_kind",
        "flatten authority is closed: only the operator, Book policy (pre-declared "
        "triggers), and the protection authority (close_all severity) may flatten — "
        "never the venue adapter, a sensor, or a Bot",
        authority_kind=resolved.value,
        allowed=[member.value for member in FLATTEN_AUTHORITIES],
    )


def reject_money_boundary_flatten(boundary: object) -> Result[None]:
    """Refuse a flatten triggered solely by a money-accounting boundary (DEC-0150).

    Rollover, sweep, re-seed, and paper flip leave positions alone — a money-accounting
    boundary is never itself a flatten trigger.
    """
    resolved = coerce_enum(MoneyBoundaryKind, boundary)
    if resolved is None:
        return invalid(
            "boundary",
            "money-boundary flatten guard reads a MoneyBoundaryKind",
            given=repr(boundary),
            allowed=[member.value for member in MoneyBoundaryKind],
        )
    return policy(
        "boundary",
        "every other money boundary (rollover, sweep, re-seed, paper flip) leaves "
        "positions alone; a money-accounting boundary is never itself a flatten trigger",
        boundary=resolved.value,
    )


def close_reason_for(action_kind: object, authority_kind: object) -> Result[CloseReason | None]:
    """Map ``(action kind x issuing authority)`` through the pinned CT-29/CT-30 table.

    Present only where the action closes a position; ``suspend_new``, ``drain``, and
    ``resume`` return ``Ok(None)``. ``kill_line_flat`` is minted apart from
    ``protection_forced_flat`` because the kill line and kill switch are two different
    things (DEC-0147, DEC-0150).
    """
    kind = coerce_enum(ControlActionKind, action_kind)
    authority = coerce_enum(AuthorityKind, authority_kind)
    if kind is None:
        return invalid(
            "action_kind",
            "the close-reason mapping reads a ControlActionKind",
            given=repr(action_kind),
        )
    if authority is None:
        return invalid(
            "authority_kind",
            "the close-reason mapping reads an AuthorityKind",
            given=repr(authority_kind),
        )
    if kind is not ControlActionKind.FLATTEN:
        return _Ok(None)
    mapped = ACTION_CLOSE_REASON_MAPPING.get((kind.value, authority.value))
    if mapped is None:
        return unsupported(
            "close_reason_ref",
            "no pinned (action kind x authority) -> close-reason mapping for this pair",
            action_kind=kind.value,
            authority_kind=authority.value,
        )
    return _Ok(mapped)


# --- scope resolution --------------------------------------------------------


def resolve_subject_scope(
    subject_scope: object,
    *,
    scope_ref: object,
    stream: object,
    position_model: object,
    netting_indistinguishable_from_wider: object = False,
) -> Result[ScopeResolution]:
    """Resolve a subject scope through the pinned CT-30 resolution table (DEC-0150).

    An unresolvable scope is ``unsupported capability`` and is never emulated at a
    wider scope. Where a ``netting`` position model makes a narrower scope
    indistinguishable from a wider one, the action **refuses** rather than executing
    wider (AD-29).
    """
    resolved_scope = coerce_enum(SubjectScope, subject_scope)
    if resolved_scope is None:
        return unsupported(
            "subject_scope",
            "an unresolvable subject scope is an unsupported-capability refusal and is "
            "never emulated at a wider scope",
            given=repr(subject_scope),
            allowed=[member.value for member in SubjectScope],
            table_version=CT30_SCOPE_RESOLUTION_TABLE_VERSION,
        )
    ref = clean_str(scope_ref)
    if ref is None:
        return invalid(
            "scope_ref",
            "a resolved scope carries a non-empty opaque scope reference",
            given=repr(scope_ref),
        )
    if not isinstance(stream, CommandStreamKey):
        return invalid(
            "stream",
            "scope resolution is scoped to one (VenueId, account) command stream",
            given=repr(stream),
        )
    model = coerce_enum(PositionModel, position_model)
    if model is None:
        return unsupported(
            "position_model",
            "scope resolution reads CT-18 netting|hedging before dispatch; an unmeasured "
            "model is an unsupported-capability refusal",
            given=repr(position_model),
        )
    if not isinstance(netting_indistinguishable_from_wider, bool):
        return invalid(
            "netting_indistinguishable_from_wider",
            "the netting-indistinguishable flag is a boolean",
            given=repr(netting_indistinguishable_from_wider),
        )
    narrower = {
        SubjectScope.INSTRUMENT,
        SubjectScope.BOOK,
        SubjectScope.BINDING,
    }
    if (
        model is PositionModel.NETTING
        and resolved_scope in narrower
        and netting_indistinguishable_from_wider
    ):
        return unsupported(
            "subject_scope",
            "where the venue's netting position model makes a narrower scope "
            "indistinguishable from a wider one the action refuses rather than "
            "executing wider",
            subject_scope=resolved_scope.value,
            position_model=model.value,
            table_version=CT30_SCOPE_RESOLUTION_TABLE_VERSION,
        )
    enforcement = EnforcementScope(subject_scope=resolved_scope, scope_ref=ref, stream=stream)
    return _Ok(
        ScopeResolution(
            enforcement=enforcement,
            table_version=CT30_SCOPE_RESOLUTION_TABLE_VERSION,
            position_model=model,
        )
    )


# --- the control-action record -----------------------------------------------


@dataclass(frozen=True, slots=True)
class ControlActionRecord:
    """One CT-30 control-action record — standing intent is the stream fold (DEC-0150).

    Carries ``action_kind``, issuing ``authority`` / ``authority_kind``, ``subject_scope``,
    mandatory ``satisfaction_predicate``, BMS-declared ``rank``, ``reason_class``, the
    command-stream key, and optional ``close_reason_ref`` where the action closes a
    position. Optional ``trigger_class`` names a Book-policy pre-declared trigger.
    """

    action_kind: ControlActionKind
    authority: str
    authority_kind: AuthorityKind
    subject_scope: SubjectScope
    scope_ref: str
    satisfaction_predicate: SatisfactionPredicate
    rank: int
    reason_class: str
    stream: CommandStreamKey
    issued_at: Instant
    close_reason_ref: CloseReason | None = None
    trigger_class: str | None = None
    protection_declares_close_all: bool = False

    @classmethod
    def try_create(
        cls,
        action_kind: object,
        authority: object,
        authority_kind: object,
        subject_scope: object,
        scope_ref: object,
        satisfaction_predicate: object,
        rank: object,
        reason_class: object,
        stream: object,
        issued_at: object,
        *,
        close_reason_ref: object = None,
        trigger_class: object = None,
        protection_declares_close_all: object = False,
    ) -> Result[ControlActionRecord]:
        """Validate and build a :class:`ControlActionRecord`, value-or-refusal."""
        kind_check = reject_blanket_command_pipe_block(action_kind)
        if is_refusal(kind_check):
            return kind_check
        kind = kind_check.value

        authority_token = clean_str(authority)
        if authority_token is None:
            return invalid(
                "authority",
                "every action carries an issuing authority instance so the act has an "
                "issuer and a rank",
                given=repr(authority),
            )
        resolved_authority = coerce_enum(AuthorityKind, authority_kind)
        if resolved_authority is None:
            return invalid(
                "authority_kind",
                "authority_kind is operator|book_policy|protection_authority|"
                "venue-delegated|adapter_self",
                given=repr(authority_kind),
                allowed=[member.value for member in AuthorityKind],
            )
        resolved_scope = coerce_enum(SubjectScope, subject_scope)
        if resolved_scope is None:
            return invalid(
                "subject_scope",
                "subject_scope is instrument|book|binding|account|venue|global",
                given=repr(subject_scope),
                allowed=[member.value for member in SubjectScope],
            )
        ref = clean_str(scope_ref)
        if ref is None:
            return invalid(
                "scope_ref",
                "a control action names its subject by a non-empty opaque scope_ref",
                given=repr(scope_ref),
            )
        predicate = coerce_enum(SatisfactionPredicate, satisfaction_predicate)
        if predicate is None:
            return invalid(
                "satisfaction_predicate",
                "every action declares a mandatory satisfaction predicate from the "
                "closed vocabulary",
                given=repr(satisfaction_predicate),
                allowed=[member.value for member in SatisfactionPredicate],
            )
        if kind in NEVER_AUTO_KINDS and predicate is not SatisfactionPredicate.NEVER_AUTO:
            return invalid(
                "satisfaction_predicate",
                "suspend_new and drain are never-auto by rule — clearing only by an "
                "operator resume",
                action_kind=kind.value,
                given=predicate.value,
            )
        if kind is ControlActionKind.RESUME and predicate is not SatisfactionPredicate.NEVER_AUTO:
            return invalid(
                "satisfaction_predicate",
                "resume is operator-only and never-auto",
                given=predicate.value,
            )
        if kind is ControlActionKind.FLATTEN and (
            predicate is not SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT
        ):
            return invalid(
                "satisfaction_predicate",
                "flatten satisfies only on a reconciled verdict showing the scope flat",
                given=predicate.value,
            )
        if isinstance(rank, bool) or not isinstance(rank, int) or rank < 0:
            return invalid(
                "rank",
                "rank is a mandatory, non-defaultable non-negative integer (BMS-declared)",
                given=repr(rank),
            )
        reason = clean_str(reason_class)
        if reason is None:
            return invalid(
                "reason_class",
                "a control action carries a typed reason class",
                given=repr(reason_class),
            )
        if not isinstance(stream, CommandStreamKey):
            return invalid(
                "stream",
                "a control action is scoped to one (VenueId, account) command stream",
                given=repr(stream),
            )
        if not isinstance(issued_at, Instant):
            return invalid(
                "issued_at",
                "a control action is dated with an injected Instant (never a clock read "
                "below the composition root); a standing intent never time-expires",
                given=repr(issued_at),
            )
        if not isinstance(protection_declares_close_all, bool):
            return invalid(
                "protection_declares_close_all",
                "protection_declares_close_all is a boolean",
                given=repr(protection_declares_close_all),
            )

        # resume is operator-only
        if kind is ControlActionKind.RESUME and resolved_authority is not AuthorityKind.OPERATOR:
            return policy(
                "authority_kind",
                "resume is operator-only — escalation automates, de-escalation does not",
                authority_kind=resolved_authority.value,
            )

        # adapter_self may not flatten
        if resolved_authority is AuthorityKind.ADAPTER_SELF and kind in ADAPTER_SELF_FLATTEN_KINDS:
            return policy(
                "authority_kind",
                "the venue adapter never initiates a flatten; adapter_self actions are "
                "limited to suspend_new, drain, throttle and session state",
                action_kind=kind.value,
            )

        trigger_token: str | None = None
        if trigger_class is not None:
            trigger_token = clean_str(trigger_class)
            if trigger_token is None:
                return invalid(
                    "trigger_class",
                    "a Book-policy trigger class is a non-empty token when present",
                    given=repr(trigger_class),
                )

        if kind is ControlActionKind.FLATTEN:
            auth = check_flatten_authority(
                resolved_authority,
                trigger_class_declared=trigger_token is not None,
                protection_declares_close_all=protection_declares_close_all,
            )
            if is_refusal(auth):
                return auth

        close_ref: CloseReason | None = None
        if close_reason_ref is not None:
            close_ref = coerce_enum(CloseReason, close_reason_ref)
            if close_ref is None:
                return invalid(
                    "close_reason_ref",
                    "close_reason_ref is a CloseReason from the CT-29 taxonomy when present",
                    given=repr(close_reason_ref),
                )
        else:
            mapped = close_reason_for(kind, resolved_authority)
            if is_refusal(mapped):
                return mapped
            close_ref = mapped.value

        if kind is ControlActionKind.FLATTEN and close_ref is None:
            return invalid(
                "close_reason_ref",
                "a flatten that closes a position carries close_reason_ref through the "
                "pinned (kind x authority) mapping",
            )
        if kind is not ControlActionKind.FLATTEN and close_ref is not None:
            return invalid(
                "close_reason_ref",
                "suspend_new, drain and resume that close nothing omit close_reason_ref",
                given=close_ref.value,
            )

        return _Ok(
            cls(
                action_kind=kind,
                authority=authority_token,
                authority_kind=resolved_authority,
                subject_scope=resolved_scope,
                scope_ref=ref,
                satisfaction_predicate=predicate,
                rank=rank,
                reason_class=reason,
                stream=stream,
                issued_at=issued_at,
                close_reason_ref=close_ref,
                trigger_class=trigger_token,
                protection_declares_close_all=protection_declares_close_all,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — optional keys only when present."""
        content: dict[str, object] = {
            "class": "control-action-record",
            "action_kind": self.action_kind.value,
            "authority": self.authority,
            "authority_kind": self.authority_kind.value,
            "subject_scope": self.subject_scope.value,
            "scope_ref": self.scope_ref,
            "satisfaction_predicate": self.satisfaction_predicate.value,
            "rank": self.rank,
            "reason_class": self.reason_class,
            "stream": self.stream.fp1_identity(),
            "issued_at": self.issued_at.fp1_identity(),
            "format_version": CT30_CONTRACT_FORMAT_VERSION,
        }
        if self.close_reason_ref is not None:
            content["close_reason_ref"] = self.close_reason_ref.value
        if self.trigger_class is not None:
            content["trigger_class"] = self.trigger_class
        if self.protection_declares_close_all:
            content["protection_declares_close_all"] = True
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """The control-action record's ``fp1`` over its full canonical content."""
        return fingerprint(self.fp1_identity())


def mint_control_action(
    action_kind: object,
    authority: object,
    authority_kind: object,
    subject_scope: object,
    scope_ref: object,
    rank: object,
    reason_class: object,
    stream: object,
    issued_at: object,
    *,
    satisfaction_predicate: object = None,
    close_reason_ref: object = None,
    trigger_class: object = None,
    protection_declares_close_all: object = False,
    blocked_act: object = "entry",
) -> Result[ControlActionRecord]:
    """Mint a CT-30 control-action record, filling the default satisfaction predicate."""
    preserved = check_exit_preservation(blocked_act=blocked_act)
    if is_refusal(preserved):
        return preserved
    predicate: object = satisfaction_predicate
    if predicate is None:
        defaulted = default_satisfaction_predicate(action_kind)
        if is_refusal(defaulted):
            return defaulted
        predicate = defaulted.value
    return ControlActionRecord.try_create(
        action_kind,
        authority,
        authority_kind,
        subject_scope,
        scope_ref,
        predicate,
        rank,
        reason_class,
        stream,
        issued_at,
        close_reason_ref=close_reason_ref,
        trigger_class=trigger_class,
        protection_declares_close_all=protection_declares_close_all,
    )


# --- kill switch vs kill line ------------------------------------------------


@dataclass(frozen=True, slots=True)
class KillSwitch:
    """The global black-swan authority — stops all new trading everywhere (DEC-0150).

    Named apart from :class:`KillLine` and never merged. Sensor-fed (MIS/SQS are
    inputs, never authorities); escalates automatically; de-escalates only by a human.
    Which additional effect (``drain`` or ``close_all``/flatten) a severity carries is
    **node severity policy** — QMF carries the contract, never the matrix.
    """

    authority: str
    stream: CommandStreamKey
    level: int
    effect_kind: ControlActionKind
    reason_class: str

    @classmethod
    def try_create(
        cls,
        authority: object,
        stream: object,
        level: object,
        effect_kind: object,
        reason_class: object,
    ) -> Result[KillSwitch]:
        """Validate and build a :class:`KillSwitch`, value-or-refusal."""
        token = clean_str(authority)
        if token is None:
            return invalid(
                "authority",
                "the kill switch names its protection-authority instance",
                given=repr(authority),
            )
        if not isinstance(stream, CommandStreamKey):
            return invalid(
                "stream",
                "a kill-switch action is still stream-scoped at the arbitration point "
                "(global subject_scope; one arbiter per stream)",
                given=repr(stream),
            )
        if isinstance(level, bool) or not isinstance(level, int) or level < 0:
            return invalid(
                "level",
                "a kill-switch level is a non-negative integer ordinal (node severity "
                "policy chooses effects; QMF does not)",
                given=repr(level),
            )
        kind = coerce_enum(ControlActionKind, effect_kind)
        if kind is None or kind is ControlActionKind.RESUME:
            return invalid(
                "effect_kind",
                "a kill-switch effect is suspend_new|drain|flatten (resume is "
                "operator-only de-escalation, never an escalate effect)",
                given=repr(effect_kind),
            )
        reason = clean_str(reason_class)
        if reason is None:
            return invalid(
                "reason_class",
                "a kill-switch action carries a typed reason class",
                given=repr(reason_class),
            )
        return _Ok(
            cls(
                authority=token,
                stream=stream,
                level=level,
                effect_kind=kind,
                reason_class=reason,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the kill switch."""
        return {
            "class": "kill-switch",
            "authority": self.authority,
            "stream": self.stream.fp1_identity(),
            "level": self.level,
            "effect_kind": self.effect_kind.value,
            "reason_class": self.reason_class,
            "format_version": CT30_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class KillLine:
    """The per-Book capital floor — breach auto-flattens and stands the Book down.

    Named apart from :class:`KillSwitch` and never merged. A 3am breach never waits
    for the operator. Resume (clearing the stand-down) is operator-only (DEC-0150).
    """

    authority: str
    binding_scope_ref: str
    stream: CommandStreamKey
    reason_class: str

    @classmethod
    def try_create(
        cls,
        authority: object,
        binding_scope_ref: object,
        stream: object,
        reason_class: object,
    ) -> Result[KillLine]:
        """Validate and build a :class:`KillLine`, value-or-refusal."""
        token = clean_str(authority)
        if token is None:
            return invalid(
                "authority",
                "the kill line names its Book-policy authority instance",
                given=repr(authority),
            )
        scope = clean_str(binding_scope_ref)
        if scope is None:
            return invalid(
                "binding_scope_ref",
                "a kill-line breach targets the binding scope by a non-empty reference",
                given=repr(binding_scope_ref),
            )
        if not isinstance(stream, CommandStreamKey):
            return invalid(
                "stream",
                "a kill-line action is scoped to one (VenueId, account) command stream",
                given=repr(stream),
            )
        reason = clean_str(reason_class)
        if reason is None:
            return invalid(
                "reason_class",
                "a kill-line breach carries a typed reason class",
                given=repr(reason_class),
            )
        return _Ok(
            cls(
                authority=token,
                binding_scope_ref=scope,
                stream=stream,
                reason_class=reason,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the kill line."""
        return {
            "class": "kill-line",
            "authority": self.authority,
            "binding_scope_ref": self.binding_scope_ref,
            "stream": self.stream.fp1_identity(),
            "reason_class": self.reason_class,
            "format_version": CT30_CONTRACT_FORMAT_VERSION,
        }


def mint_kill_switch_action(
    kill_switch: object,
    *,
    rank: object,
    issued_at: object,
    protection_declares_close_all: object = False,
) -> Result[ControlActionRecord]:
    """Mint the CT-30 control action a kill-switch escalation issues (DEC-0150).

    Subject scope is ``global``; authority kind is ``protection_authority``. A flatten
    effect requires ``protection_declares_close_all`` (node severity policy).
    """
    if not isinstance(kill_switch, KillSwitch):
        return invalid(
            "kill_switch",
            "mint_kill_switch_action reads a KillSwitch",
            given=repr(kill_switch),
        )
    return mint_control_action(
        kill_switch.effect_kind,
        kill_switch.authority,
        AuthorityKind.PROTECTION_AUTHORITY,
        SubjectScope.GLOBAL,
        "global",
        rank,
        kill_switch.reason_class,
        kill_switch.stream,
        issued_at,
        protection_declares_close_all=protection_declares_close_all,
    )


def mint_kill_line_breach(
    kill_line: object,
    *,
    rank: object,
    issued_at: object,
) -> Result[ControlActionRecord]:
    """Mint the automatic flatten a kill-line breach issues (DEC-0150).

    Authority kind is ``book_policy`` with trigger class ``kill_line_breach``;
    ``close_reason_ref`` maps to ``kill_line_flat`` — minted apart from
    ``protection_forced_flat``.
    """
    if not isinstance(kill_line, KillLine):
        return invalid(
            "kill_line",
            "mint_kill_line_breach reads a KillLine",
            given=repr(kill_line),
        )
    return mint_control_action(
        ControlActionKind.FLATTEN,
        kill_line.authority,
        AuthorityKind.BOOK_POLICY,
        SubjectScope.BINDING,
        kill_line.binding_scope_ref,
        rank,
        kill_line.reason_class,
        kill_line.stream,
        issued_at,
        trigger_class="kill_line_breach",
    )


# --- standing intent: journal-before-dispatch and the read-time fold ---------


def journal_before_dispatch(
    record: object, *, journal_result: object
) -> Result[ControlActionRecord]:
    """Journal a protection action before dispatch — storage failure blocks it (DEC-0150).

    The risk dispatcher must see a sink refusal: a ``storage failure`` blocks the
    dispatch rather than losing the intent. A successful journal returns the record
    ready for dispatch consideration; any other refusal category is forwarded.
    """
    if not isinstance(record, ControlActionRecord):
        return invalid(
            "record",
            "journal_before_dispatch journals a ControlActionRecord before dispatch",
            given=repr(record),
        )
    if isinstance(journal_result, TypedRefusal):
        # Any sink refusal — including storage failure — blocks dispatch rather than
        # losing the intent; the dispatcher must see the refusal (AD-31; DEC-0150).
        return journal_result
    return _Ok(record)


def evaluate_satisfaction(
    predicate: object,
    *,
    verdict: object,
    scope_flat: object = False,
    no_pending_orders: object = False,
) -> Result[StandingIntentStatus]:
    """Evaluate a satisfaction predicate against a reconciliation verdict (DEC-0150).

    Flatten satisfies only on a ``reconciled`` verdict showing the scope flat.
    ``drift`` / ``unknown`` / ``out-of-lookback`` → ``held-alarm`` (hold open, no
    dispatch). ``never-auto`` stays open until an operator resume.
    """
    resolved_pred = coerce_enum(SatisfactionPredicate, predicate)
    if resolved_pred is None:
        return invalid(
            "predicate",
            "satisfaction evaluation reads a SatisfactionPredicate",
            given=repr(predicate),
        )
    resolved_verdict = coerce_enum(ReconciliationVerdict, verdict)
    if resolved_verdict is None:
        return invalid(
            "verdict",
            "satisfaction evaluation reads a ReconciliationVerdict",
            given=repr(verdict),
            allowed=[member.value for member in ReconciliationVerdict],
        )
    if not isinstance(scope_flat, bool):
        return invalid("scope_flat", "scope_flat is a boolean", given=repr(scope_flat))
    if not isinstance(no_pending_orders, bool):
        return invalid(
            "no_pending_orders",
            "no_pending_orders is a boolean",
            given=repr(no_pending_orders),
        )
    if resolved_pred is SatisfactionPredicate.NEVER_AUTO:
        return _Ok(StandingIntentStatus.OPEN)
    if resolved_verdict is not ReconciliationVerdict.RECONCILED:
        return _Ok(StandingIntentStatus.HELD_ALARM)
    if resolved_pred is SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT:
        if scope_flat:
            return _Ok(StandingIntentStatus.SATISFIED)
        return _Ok(StandingIntentStatus.OPEN)
    if no_pending_orders:
        return _Ok(StandingIntentStatus.SATISFIED)
    return _Ok(StandingIntentStatus.OPEN)


@dataclass(frozen=True, slots=True)
class StandingIntentFold:
    """One standing intent as seen by the read-time fold (DEC-0150)."""

    record: ControlActionRecord
    record_fingerprint: Fingerprint
    status: StandingIntentStatus


def reevaluate_standing_intent(
    record: object,
    *,
    verdict: object,
    scope_flat: object = False,
    no_pending_orders: object = False,
) -> Result[StandingIntentFold]:
    """Re-decide a standing intent against reconciled state — never retry (DEC-0150).

    On reconnect the node re-evaluates every standing intent; if still unsatisfied it
    issues a **new** command with a **new** identity. The intent never time-expires.
    """
    if not isinstance(record, ControlActionRecord):
        return invalid(
            "record",
            "reevaluate_standing_intent reads a ControlActionRecord",
            given=repr(record),
        )
    status = evaluate_satisfaction(
        record.satisfaction_predicate,
        verdict=verdict,
        scope_flat=scope_flat,
        no_pending_orders=no_pending_orders,
    )
    if is_refusal(status):
        return status
    fp = record.fingerprint()
    if is_refusal(fp):
        return fp
    return _Ok(StandingIntentFold(record=record, record_fingerprint=fp.value, status=status.value))


class ControlActionStream:
    """Append-only CT-30 control-action stream — standing intent is a read-time fold.

    A pure reference structure, not the platform store (DEC-0158). Records are grouped
    by command-stream key; :func:`fold_standing_intents` derives open intents.
    """

    def __init__(self) -> None:
        self._by_stream: dict[tuple[str, str], list[ControlActionRecord]] = {}
        self._by_fingerprint: dict[str, ControlActionRecord] = {}
        self._order: list[Fingerprint] = []

    def mint(self, record: object) -> Result[Fingerprint]:
        """Append a control-action record, refusing an equal-fingerprint re-mint."""
        if not isinstance(record, ControlActionRecord):
            return invalid(
                "record",
                "the stream mints a ControlActionRecord",
                given=repr(record),
            )
        fp = record.fingerprint()
        if is_refusal(fp):
            return fp
        fp_value = fp.value.value
        if fp_value in self._by_fingerprint:
            return invalid(
                "record",
                "a control-action record fingerprinting equal to an existing one is "
                "refused; the stream is append-only",
                control_action_fingerprint=fp_value,
            )
        key = (record.stream.venue_id.value, record.stream.account_id)
        self._by_fingerprint[fp_value] = record
        self._by_stream.setdefault(key, []).append(record)
        self._order.append(fp.value)
        return _Ok(fp.value)

    def records_for(self, stream: object) -> tuple[ControlActionRecord, ...]:
        """Every control action minted on one command stream, in mint order."""
        if not isinstance(stream, CommandStreamKey):
            return ()
        return tuple(self._by_stream.get((stream.venue_id.value, stream.account_id), ()))


def fold_standing_intents(
    stream: object,
    command_stream: object,
    *,
    verdict: object = ReconciliationVerdict.RECONCILED,
    scope_flat_by_ref: object = None,
) -> Result[tuple[StandingIntentFold, ...]]:
    """Read-time fold: which standing intents are still open on one stream (DEC-0150).

    Restart-proof by construction — status is never a stored mutable field. Resume
    records clear never-auto intents for the same scope; flatten intents satisfy only
    on a reconciled flat verdict.
    """
    if not isinstance(stream, ControlActionStream):
        return invalid(
            "stream",
            "the standing-intent fold reads a ControlActionStream",
            given=type_name(stream),
        )
    if not isinstance(command_stream, CommandStreamKey):
        return invalid(
            "command_stream",
            "the standing-intent fold is scoped to one command stream",
            given=repr(command_stream),
        )
    flat_map: dict[str, bool] = {}
    if scope_flat_by_ref is not None:
        if not isinstance(scope_flat_by_ref, Mapping):
            return invalid(
                "scope_flat_by_ref",
                "scope_flat_by_ref is a mapping of scope_ref → bool when present",
                given=type_name(scope_flat_by_ref),
            )
        for key, value in cast("Mapping[object, object]", scope_flat_by_ref).items():
            if not isinstance(key, str) or not isinstance(value, bool):
                return invalid(
                    "scope_flat_by_ref",
                    "scope_flat_by_ref carries string keys and boolean values",
                    given=repr((key, value)),
                )
            flat_map[key] = value

    records = stream.records_for(command_stream)
    # Collect operator resumes by scope — they clear never-auto intents at that scope.
    resumed_scopes: set[str] = {
        r.scope_ref
        for r in records
        if r.action_kind is ControlActionKind.RESUME and r.authority_kind is AuthorityKind.OPERATOR
    }

    folds: list[StandingIntentFold] = []
    for record in records:
        if record.action_kind is ControlActionKind.RESUME:
            continue
        scope_flat = flat_map.get(record.scope_ref, False)
        if (
            record.satisfaction_predicate is SatisfactionPredicate.NEVER_AUTO
            and record.scope_ref in resumed_scopes
        ):
            fp = record.fingerprint()
            if is_refusal(fp):
                return fp
            folds.append(
                StandingIntentFold(
                    record=record,
                    record_fingerprint=fp.value,
                    status=StandingIntentStatus.SATISFIED,
                )
            )
            continue
        evaluated = reevaluate_standing_intent(record, verdict=verdict, scope_flat=scope_flat)
        if is_refusal(evaluated):
            return evaluated
        folds.append(evaluated.value)
    return _Ok(tuple(folds))


# --- same-tick arbitration ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class PendingControlAction:
    """One pending action at the arbitration point, already journaled (DEC-0151)."""

    record: ControlActionRecord
    record_fingerprint: Fingerprint
    enforcement: EnforcementScope
    mechanical_command: ControlActionKind

    @classmethod
    def try_create(
        cls,
        record: object,
        enforcement: object,
        *,
        mechanical_command: object = None,
    ) -> Result[PendingControlAction]:
        """Validate and build a :class:`PendingControlAction`, value-or-refusal."""
        if not isinstance(record, ControlActionRecord):
            return invalid(
                "record",
                "a pending action carries a journaled ControlActionRecord",
                given=repr(record),
            )
        if not isinstance(enforcement, EnforcementScope):
            return invalid(
                "enforcement",
                "a pending action carries its resolved EnforcementScope",
                given=repr(enforcement),
            )
        if enforcement.stream != record.stream:
            return invalid(
                "enforcement",
                "enforcement scope must share the pending action's command stream — "
                "cross-stream ordering is a declared non-guarantee",
            )
        command = (
            record.action_kind
            if mechanical_command is None
            else coerce_enum(ControlActionKind, mechanical_command)
        )
        if command is None:
            return invalid(
                "mechanical_command",
                "the mechanical command is a ControlActionKind",
                given=repr(mechanical_command),
            )
        fp = record.fingerprint()
        if is_refusal(fp):
            return fp
        return _Ok(
            cls(
                record=record,
                record_fingerprint=fp.value,
                enforcement=enforcement,
                mechanical_command=command,
            )
        )


@dataclass(frozen=True, slots=True)
class SuppressedControlAction:
    """First-class suppression evidence — references a real CT-30 fingerprint (DEC-0158)."""

    suppressed: PendingControlAction
    suppressing_authority: str
    suppressing_authority_kind: AuthorityKind
    reason_class: str
    arbitration_record_ref: Fingerprint

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for a suppression record."""
        return {
            "class": "suppressed-control-action",
            "would_have_been_action": self.suppressed.record_fingerprint.value,
            "suppressed_authority": self.suppressed.record.authority,
            "suppressed_authority_kind": self.suppressed.record.authority_kind.value,
            "suppressing_authority": self.suppressing_authority,
            "suppressing_authority_kind": self.suppressing_authority_kind.value,
            "reason_class": self.reason_class,
            "enforcement_scope": self.suppressed.enforcement.fp1_identity(),
            "arbitration_record_ref": self.arbitration_record_ref.value,
            "format_version": CT30_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ArbitrationOutcome:
    """Result of same-tick arbitration on one command stream (DEC-0151)."""

    stream: CommandStreamKey
    emit: tuple[PendingControlAction, ...]
    suppressed: tuple[SuppressedControlAction, ...]
    arbitration_record_ref: Fingerprint


def _scope_key(enforcement: EnforcementScope) -> tuple[str, str]:
    return (enforcement.subject_scope.value, enforcement.scope_ref)


def _compose(a: ControlActionKind, b: ControlActionKind) -> bool:
    return frozenset({a, b}) in COMPOSING_KIND_PAIRS


def _protection(kind: ControlActionKind) -> int:
    return PROTECTION_WEIGHT[kind]


def arbitrate_same_tick(
    pending: object,
    rank_table: object,
    *,
    stream: object,
    arbitration_seed: object = "arbitration",
    blocked_act: object = "entry",
) -> Result[ArbitrationOutcome]:
    """Arbitrate same-tick actions at exactly one point per command stream (DEC-0151).

    Collapse: same mechanical command on the same enforcement scope → one emission,
    rank winner supplies authority/reason, losers journal as suppressed.

    Conflict: mutually exclusive commands → higher rank wins outright (never both,
    never queued), unless suppressing the lower would reduce the protection it would
    have delivered — then both execute (the standing invariant).

    Compose: ``suspend_new + flatten``, ``drain + flatten`` (and ``suspend_new +
    drain``) both execute. Rank table uniqueness is assumed already enforced at
    Layer 1; a missing kind is ``invalid input``.
    """
    preserved = check_exit_preservation(blocked_act=blocked_act)
    if is_refusal(preserved):
        return preserved
    if not isinstance(stream, CommandStreamKey):
        return invalid(
            "stream",
            "same-tick arbitration runs at exactly one (VenueId, account) point",
            given=repr(stream),
        )
    if not isinstance(rank_table, ControlRankTable):
        return invalid(
            "rank_table",
            "arbitration reads the BMS-declared ControlRankTable for this stream",
            given=repr(rank_table),
        )
    pending_given = type_name(pending)
    if isinstance(pending, (str, bytes, Mapping)) or not isinstance(pending, Iterable):
        return invalid(
            "pending",
            "arbitration reads a collection of PendingControlAction values",
            given=pending_given,
        )
    items: list[PendingControlAction] = []
    for item in cast("Iterable[object]", pending):
        if not isinstance(item, PendingControlAction):
            return invalid(
                "pending",
                "each pending item is a PendingControlAction",
                given=repr(item),
            )
        if item.record.stream != stream or item.enforcement.stream != stream:
            return invalid(
                "pending",
                "every pending action must share the arbitration stream — cross-stream "
                "ordering is a declared non-guarantee",
            )
        items.append(item)
    if not items:
        return invalid("pending", "arbitration requires at least one pending action")

    ranks = rank_table.ranks_by_kind()
    for item in items:
        if item.record.action_kind not in ranks:
            return invalid(
                "rank_table",
                "every pending control-action kind must appear in the BMS rank table",
                action_kind=item.record.action_kind.value,
            )
        if item.record.rank != ranks[item.record.action_kind]:
            return invalid(
                "rank",
                "a pending action's rank must match the BMS-declared table for its kind",
                action_kind=item.record.action_kind.value,
                record_rank=item.record.rank,
                table_rank=ranks[item.record.action_kind],
            )

    seed = clean_str(arbitration_seed)
    if seed is None:
        return invalid(
            "arbitration_seed",
            "arbitration_seed is a non-empty token used to mint the arbitration record fingerprint",
            given=repr(arbitration_seed),
        )
    arb_fp = fingerprint(
        {
            "class": "arbitration-record",
            "stream": stream.fp1_identity(),
            "seed": seed,
            "pending": sorted(p.record_fingerprint.value for p in items),
            "format_version": CT30_CONTRACT_FORMAT_VERSION,
        }
    )
    if is_refusal(arb_fp):
        return arb_fp
    arbitration_ref = arb_fp.value

    # Group by enforcement scope.
    by_scope: dict[tuple[str, str], list[PendingControlAction]] = {}
    for item in items:
        by_scope.setdefault(_scope_key(item.enforcement), []).append(item)

    emit: list[PendingControlAction] = []
    suppressed: list[SuppressedControlAction] = []

    for group in by_scope.values():
        # Collapse identical mechanical commands first.
        by_command: dict[ControlActionKind, list[PendingControlAction]] = {}
        for item in group:
            by_command.setdefault(item.mechanical_command, []).append(item)

        survivors: list[PendingControlAction] = []
        for _command, cohort in by_command.items():
            ordered = sorted(cohort, key=lambda p: (p.record.rank, p.record_fingerprint.value))
            winner = ordered[0]
            survivors.append(winner)
            for loser in ordered[1:]:
                suppressed.append(
                    SuppressedControlAction(
                        suppressed=loser,
                        suppressing_authority=winner.record.authority,
                        suppressing_authority_kind=winner.record.authority_kind,
                        reason_class="collapse-same-mechanical-command",
                        arbitration_record_ref=arbitration_ref,
                    )
                )

        # Across distinct mechanical commands: compose, conflict, or preserve.
        survivors_sorted = sorted(
            survivors, key=lambda p: (p.record.rank, p.record_fingerprint.value)
        )
        kept: list[PendingControlAction] = []
        for candidate in survivors_sorted:
            drop = False
            for incumbent in list(kept):
                if candidate.mechanical_command == incumbent.mechanical_command:
                    continue
                if _compose(candidate.mechanical_command, incumbent.mechanical_command):
                    continue
                # Mutually exclusive — higher rank (lower number) wins, unless that
                # would reduce the protection the lower-ranked action would deliver.
                if candidate.record.rank < incumbent.record.rank:
                    higher, lower = candidate, incumbent
                elif candidate.record.rank > incumbent.record.rank:
                    higher, lower = incumbent, candidate
                else:
                    # Unique ranks at Layer 1 make this unreachable for distinct kinds;
                    # fingerprint tie-break keeps determinism if a table is partial.
                    higher, lower = (
                        (candidate, incumbent)
                        if candidate.record_fingerprint.value < incumbent.record_fingerprint.value
                        else (incumbent, candidate)
                    )
                if _protection(higher.mechanical_command) < _protection(lower.mechanical_command):
                    # Standing invariant: higher may not reduce lower's protection —
                    # both execute (treat as compose).
                    continue
                # Higher wins; suppress lower.
                if lower is candidate:
                    drop = True
                    suppressed.append(
                        SuppressedControlAction(
                            suppressed=lower,
                            suppressing_authority=higher.record.authority,
                            suppressing_authority_kind=higher.record.authority_kind,
                            reason_class="conflict-higher-rank-wins",
                            arbitration_record_ref=arbitration_ref,
                        )
                    )
                    break
                kept.remove(incumbent)
                suppressed.append(
                    SuppressedControlAction(
                        suppressed=lower,
                        suppressing_authority=higher.record.authority,
                        suppressing_authority_kind=higher.record.authority_kind,
                        reason_class="conflict-higher-rank-wins",
                        arbitration_record_ref=arbitration_ref,
                    )
                )
            if not drop:
                kept.append(candidate)
        emit.extend(kept)

    return _Ok(
        ArbitrationOutcome(
            stream=stream,
            emit=tuple(emit),
            suppressed=tuple(suppressed),
            arbitration_record_ref=arbitration_ref,
        )
    )
