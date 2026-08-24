"""Prediction linter — static Book-vs-bot compatibility (QL-8).

Runs on demand and at seat time against the CT-28 binding context. The four
pinned checks are addable never redefined (DEC-0178). Pure: no I/O, no process,
no thread, and no ``qmf-venue`` import — CT-18 is read through the host-built
binding projection (AD-29).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core.exact import ExactRational
from qmf.core.fingerprint import Fingerprint
from qmf.core.identity import AccountRole
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.risk.admission_bar import (
    AdmissionBar,
    Band,
    Comparison,
    PendingSlot,
    RuledThreshold,
    check_live_binding_admissible,
)
from qmf.risk.binding import BindingState, VenueBindingProfile
from qmf.risk.exit_policy import ExitPolicy, ResolvedExitPolicyEntry, resolve_exit_policy_entry
from qmf.risk.footprint_requirements import (
    FootprintFieldKind,
    FootprintRequirement,
    FootprintRequirements,
    check_footprint_requirements_live_binding,
)
from qmf.risk.migrations import THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS

from qml._refuse import invalid, policy, unsupported
from qml.conformance.contract import CONFORMANCE_FORMAT_VERSION, PREDICTION_CHECKS
from qml.declaration.bot import BotDefinition, mint_bot_definition
from qml.footprint.manifest import Footprint, ProducerBinding
from qml.footprint.vocab import ProducerBindingForm

__all__ = [
    "PREDICTION_CHECKS",
    "PredictionBindingContext",
    "PredictionVerdict",
    "lint_prediction",
    "stream_set_required_capabilities",
]

_LINTER: Final[str] = "prediction"

_LOCUS_ALIASES: Final[Mapping[FootprintFieldKind, frozenset[str]]] = {
    FootprintFieldKind.STREAM_SET: frozenset({"stream_set", "stream-set"}),
    FootprintFieldKind.CALENDARS: frozenset({"calendars", "required_calendars"}),
    FootprintFieldKind.PRODUCER_BINDINGS: frozenset(
        {"producer_bindings", "producers", "producer-bindings"}
    ),
}


def _journal(refusal: TypedRefusal) -> TypedRefusal:
    extra: dict[str, object] = dict(refusal.context)
    extra["journal"] = True
    extra.setdefault("linter", _LINTER)
    return TypedRefusal(
        category=refusal.category,
        retryability=refusal.retryability,
        context=extra,
        after_condition_descriptor=refusal.after_condition_descriptor,
    )


def _fail(field: str, reason: str, **extra: object) -> TypedRefusal:
    return _journal(policy(field, reason, linter=_LINTER, journal=True, **extra))


@dataclass(frozen=True, slots=True)
class PredictionBindingContext:
    """CT-28 seat-time projection the prediction linter reads (DEC-0178).

    Hosts assemble this from the binding record, the cited CT-33 Bot definition,
    the Book's CT-22 ``exit_policy`` / ``footprint_requirements``, and the CT-18
    capability tokens the venue declared at bind time. QML never imports
    ``qmf-venue``.
    """

    declaration: BotDefinition
    exit_policy: ExitPolicy
    footprint_requirements: FootprintRequirements | PendingSlot
    venue_capabilities: frozenset[str]
    account_role: AccountRole
    admission_bar: AdmissionBar | None = None

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "class": "qml-prediction-binding-context",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "declaration_fingerprint": _declaration_fp(self.declaration),
            "exit_policy": self.exit_policy.fp1_identity(),
            "footprint_requirements": self.footprint_requirements.fp1_identity(),
            "venue_capabilities": sorted(self.venue_capabilities),
            "account_role": self.account_role.value,
        }
        if self.admission_bar is not None:
            content["admission_bar"] = self.admission_bar.fp1_identity()
        return content


def _declaration_fp(bot: BotDefinition) -> str:
    fingerprinted = bot.fingerprint_content()
    if is_ok(fingerprinted):
        return fingerprinted.value.value
    return ""


@dataclass(frozen=True, slots=True)
class PredictionVerdict:
    """Proof that the four pinned prediction-linter checks passed (DEC-0178).

    ``live_binding_blocked`` is true when a not-yet-ruled
    ``footprint_requirement`` or admission-bar threshold is present (GAP-0048 /
    GAP-0049): the linter still passes for non-live roles, and live seating is a
    ``policy rejection``.
    """

    declaration: BotDefinition
    fingerprint: Fingerprint
    resolved_exit_entry: ResolvedExitPolicyEntry
    live_binding_blocked: bool
    account_role: AccountRole
    checks: tuple[str, ...] = PREDICTION_CHECKS

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity of the prediction-linter proof. Package SemVer never enters."""
        return {
            "class": "qml-prediction-verdict",
            "contract_format_version": CONFORMANCE_FORMAT_VERSION,
            "declaration_fingerprint": self.fingerprint.value,
            "checks": list(self.checks),
            "resolved_exit_entry": self.resolved_exit_entry.fp1_identity(),
            "live_binding_blocked": self.live_binding_blocked,
            "account_role": self.account_role.value,
            "threshold_gaps": list(THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS),
        }


def stream_set_required_capabilities(footprint: object) -> Result[frozenset[str]]:
    """CT-18 tokens the nested stream set consumes (stream role + BarSpec kind).

    The stream set lies within the binding's declared venue capabilities when this
    set is a subset of the CT-18 projection the host supplies. A surplus token is
    a bind-time prediction-linter failure (AD-29).
    """
    if not isinstance(footprint, Footprint):
        return invalid(
            "footprint",
            "stream-set capability projection reads a CT-33 Footprint",
            given=type(footprint).__name__,
            linter=_LINTER,
            journal=True,
        )
    tokens: set[str] = set()
    for member in footprint.stream_set:
        tokens.add(member.stream_role.value)
        for spec in member.bar_specs:
            kind = spec.get("kind")
            if isinstance(kind, str) and kind.strip() != "":
                tokens.add(kind)
    return Ok(frozenset(tokens))


def lint_prediction(
    declaration: object,
    *,
    exit_policy: object,
    footprint_requirements: object,
    venue_capabilities: object,
    account_role: object = AccountRole.DEMO,
    admission_bar: object = None,
) -> Result[PredictionVerdict]:
    """Run the four pinned prediction-linter checks (QL-8, DEC-0178).

    Same pure function on demand and at seat time. Hosts pass the CT-28 binding
    projection: the Book's ``exit_policy`` and ``footprint_requirements``, the
    binding's CT-18 venue-capability tokens, and the target account role (live
    seating of a blank requirement is a ``policy rejection``).
    """
    bot = _admit_declaration(declaration)
    if is_refusal(bot):
        return _journal(bot)
    policy_obj = _admit_exit_policy(exit_policy)
    if is_refusal(policy_obj):
        return _journal(policy_obj)
    requirements = _admit_footprint_requirements(footprint_requirements)
    if is_refusal(requirements):
        return _journal(requirements)
    capabilities = _admit_venue_capabilities(venue_capabilities)
    if is_refusal(capabilities):
        return _journal(capabilities)
    role = _admit_account_role(account_role)
    if is_refusal(role):
        return _journal(role)
    bar = _admit_admission_bar(admission_bar)
    if is_refusal(bar):
        return _journal(bar)

    content = bot.value
    satisfied = _check_footprint_satisfies(content.footprint, requirements.value)
    if is_refusal(satisfied):
        return satisfied
    subset = _check_exit_intent_subset(content, policy_obj.value)
    if is_refusal(subset):
        return subset
    resolved = _check_family_resolves(content, policy_obj.value)
    if is_refusal(resolved):
        return resolved
    streams = _check_stream_set_within_venue(content.footprint, capabilities.value)
    if is_refusal(streams):
        return streams
    live = _check_blank_blocks_live(requirements.value, role.value, bar.value)
    if is_refusal(live):
        return live

    fingerprint = content.fingerprint_content()
    if is_refusal(fingerprint):
        return _journal(fingerprint)
    blocked = _is_blank_surface(requirements.value, bar.value)
    return Ok(
        PredictionVerdict(
            declaration=content,
            fingerprint=fingerprint.value,
            resolved_exit_entry=resolved.value,
            live_binding_blocked=blocked,
            account_role=role.value,
            checks=PREDICTION_CHECKS,
        )
    )


def _admit_declaration(declaration: object) -> Result[BotDefinition]:
    if isinstance(declaration, BotDefinition):
        return Ok(declaration)
    return mint_bot_definition(declaration)


def _admit_exit_policy(value: object) -> Result[ExitPolicy]:
    if isinstance(value, ExitPolicy):
        return Ok(value)
    return invalid(
        "exit_policy",
        "the prediction linter reads the Book's CT-22 exit_policy",
        given=type(value).__name__,
        linter=_LINTER,
        journal=True,
    )


def _admit_footprint_requirements(
    value: object,
) -> Result[FootprintRequirements | PendingSlot]:
    if isinstance(value, FootprintRequirements):
        return Ok(value)
    if isinstance(value, PendingSlot):
        return Ok(value)
    if value is None or value in ((), []):
        minted = FootprintRequirements.try_create(())
        if is_refusal(minted):
            return minted
        return Ok(minted.value)
    return invalid(
        "footprint_requirements",
        "the prediction linter reads FootprintRequirements or the format-1 pending slot",
        given=type(value).__name__,
        linter=_LINTER,
        journal=True,
    )


def _admit_venue_capabilities(value: object) -> Result[frozenset[str]]:
    if isinstance(value, VenueBindingProfile):
        return Ok(value.declared_capabilities)
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        nested = mapping.get("declared_capabilities", mapping.get("venue_capabilities"))
        if nested is None:
            return invalid(
                "venue_capabilities",
                "a CT-18 binding projection mapping names declared_capabilities",
                linter=_LINTER,
                journal=True,
            )
        return _coerce_token_set(nested)
    return _coerce_token_set(value)


def _coerce_token_set(value: object) -> Result[frozenset[str]]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "venue_capabilities",
            "the binding's declared CT-18 venue capabilities are a collection of tokens",
            given=type(cast("object", value)).__name__,
            linter=_LINTER,
            journal=True,
        )
    tokens: set[str] = set()
    for item in cast("Iterable[object]", value):
        if not isinstance(item, str) or item.strip() == "":
            return invalid(
                "venue_capabilities",
                "each declared venue capability is a non-empty token",
                given=repr(item),
                linter=_LINTER,
                journal=True,
            )
        tokens.add(item)
    return Ok(frozenset(tokens))


def _admit_account_role(value: object) -> Result[AccountRole]:
    if isinstance(value, AccountRole):
        return Ok(value)
    if isinstance(value, BindingState):
        return Ok(AccountRole.LIVE if value is BindingState.LIVE else AccountRole.DEMO)
    if isinstance(value, str):
        try:
            return Ok(AccountRole(value))
        except ValueError:
            try:
                state = BindingState(value)
            except ValueError:
                return invalid(
                    "account_role",
                    "the CT-28 binding role is an account-role or binding-state member",
                    given=value,
                    linter=_LINTER,
                    journal=True,
                )
            return Ok(AccountRole.LIVE if state is BindingState.LIVE else AccountRole.DEMO)
    return invalid(
        "account_role",
        "the CT-28 binding role is an account-role or binding-state member",
        given=repr(value),
        linter=_LINTER,
        journal=True,
    )


def _admit_admission_bar(value: object) -> Result[AdmissionBar | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, AdmissionBar):
        return Ok(value)
    return invalid(
        "admission_bar",
        "the optional admission-bar surface is an AdmissionBar when supplied",
        given=type(value).__name__,
        linter=_LINTER,
        journal=True,
    )


def _check_footprint_satisfies(
    footprint: Footprint,
    requirements: FootprintRequirements | PendingSlot,
) -> Result[None]:
    """(a) CT-33 footprint satisfies the Book's footprint_requirements."""
    if not isinstance(requirements, FootprintRequirements):
        return Ok(None)
    for req in requirements.requirements:
        checked = _check_one_requirement(footprint, req)
        if is_refusal(checked):
            return checked
    return Ok(None)


def _check_one_requirement(footprint: Footprint, req: FootprintRequirement) -> Result[None]:
    if req.is_blank:
        return Ok(None)
    if not isinstance(req.threshold, RuledThreshold):
        return Ok(None)
    count = _measure_count(footprint, req)
    if not _compare_count(count, req.comparison, req.threshold):
        return _fail(
            "footprint_requirements",
            "the CT-33 footprint does not satisfy the Book's footprint_requirements",
            field_kind=req.field_kind.value,
            field_identity=req.field_identity,
            comparison=req.comparison.value,
            measure=count,
        )
    return Ok(None)


def _measure_count(footprint: Footprint, req: FootprintRequirement) -> int:
    identity = req.field_identity
    aliases = _LOCUS_ALIASES[req.field_kind]
    if identity == req.field_kind.value or identity in aliases:
        return _locus_count(footprint, req.field_kind)
    return 1 if _member_present(footprint, req.field_kind, identity) else 0


def _locus_count(footprint: Footprint, kind: FootprintFieldKind) -> int:
    if kind is FootprintFieldKind.STREAM_SET:
        return len(footprint.stream_set)
    if kind is FootprintFieldKind.CALENDARS:
        return len(footprint.required_calendars)
    return len(footprint.producer_bindings)


def _member_present(footprint: Footprint, kind: FootprintFieldKind, identity: str) -> bool:
    tail = identity.rsplit(".", 1)[-1]
    tokens = frozenset({identity, tail})
    if kind is FootprintFieldKind.STREAM_SET:
        return any(member.instrument_role in tokens for member in footprint.stream_set)
    if kind is FootprintFieldKind.CALENDARS:
        return any(calendar.rule_set in tokens for calendar in footprint.required_calendars)
    return any(_binding_matches(binding, tokens) for binding in footprint.producer_bindings)


def _binding_matches(binding: ProducerBinding, tokens: frozenset[str]) -> bool:
    if (
        binding.form is ProducerBindingForm.PINNED_FINGERPRINT
        and binding.pinned is not None
        and binding.pinned.value in tokens
    ):
        return True
    template = binding.template
    return template is not None and template.formula_id in tokens


def _compare_count(count: int, comparison: Comparison, threshold: RuledThreshold) -> bool:
    measure = Fraction(count)
    bound = threshold.bound
    if comparison is Comparison.WITHIN_BAND:
        band = cast("Band", bound)
        lower = band.lower.as_fraction()
        upper = band.upper.as_fraction()
        return lower <= measure <= upper
    edge = cast("ExactRational", bound).as_fraction()
    if comparison is Comparison.AT_LEAST:
        return measure >= edge
    return measure <= edge


def _check_exit_intent_subset(bot: BotDefinition, policy_obj: ExitPolicy) -> Result[None]:
    """(b) bot permitted EXIT kinds ⊆ Book exit_policy permitted EXIT kinds.

    ``entry`` is never gated: an entry-only bot (empty exit kinds) against a Book
    that declares zero permitted exit kinds is the honest V1 default and passes.
    """
    bot_kinds = frozenset(bot.permitted_exit_intents)
    book_kinds = frozenset(kind.value for kind in policy_obj.permitted_exit_intent_kinds)
    extra = bot_kinds - book_kinds
    if extra:
        return _fail(
            "permitted_exit_intents",
            "the bot's declared permitted EXIT-intent kinds must be a subset of the "
            "Book's exit_policy permitted EXIT kinds; entry is never gated here",
            extra=tuple(sorted(extra)),
            book=tuple(sorted(book_kinds)),
        )
    return Ok(None)


def _check_family_resolves(
    bot: BotDefinition, policy_obj: ExitPolicy
) -> Result[ResolvedExitPolicyEntry]:
    """(c) bot family resolves an exit_policy entry (explicit or catch-all)."""
    resolved = resolve_exit_policy_entry(policy_obj, bot.strategy_family_id.value)
    if is_refusal(resolved):
        return _fail(
            "exit_policy",
            "the bot's strategy family resolves no exit_policy entry — neither an "
            "explicit family entry nor the declared catch-all default",
            family_id=bot.strategy_family_id.value,
        )
    return resolved


def _check_stream_set_within_venue(footprint: Footprint, declared: frozenset[str]) -> Result[None]:
    """(d) stream set lies within the binding's declared CT-18 venue capabilities."""
    required = stream_set_required_capabilities(footprint)
    if is_refusal(required):
        return required
    extra = required.value - declared
    if extra:
        return _journal(
            unsupported(
                "venue_capabilities",
                "the bot's stream set exceeds the binding's declared venue capabilities; "
                "the shortfall refuses at bind time, never at trade time",
                extra=tuple(sorted(extra)),
                declared=tuple(sorted(declared)),
                bind_time=True,
                linter=_LINTER,
                journal=True,
            )
        )
    return Ok(None)


def _check_blank_blocks_live(
    requirements: FootprintRequirements | PendingSlot,
    role: AccountRole,
    bar: AdmissionBar | None,
) -> Result[None]:
    """Blank footprint_requirement / admission-bar threshold blocks live binding."""
    live = check_footprint_requirements_live_binding(requirements, role)
    if is_refusal(live):
        return _journal(live)
    if bar is not None:
        admitted = check_live_binding_admissible(bar, role)
        if is_refusal(admitted):
            return _journal(admitted)
    return Ok(None)


def _is_blank_surface(
    requirements: FootprintRequirements | PendingSlot,
    bar: AdmissionBar | None,
) -> bool:
    if not isinstance(requirements, FootprintRequirements):
        return True
    if requirements.is_blank:
        return True
    return bool(bar is not None and bar.is_blank)
