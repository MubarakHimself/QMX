"""Human-only promotion and next-day activation (TN-20; Story 26.9).

Promotion is a click: the silent battery runs against fresh state, the hub
pull refuses sandbox provenance, and success lands ADMITTED with no intent,
ledger, or exposure. Activation is a separate click whose record is accepted
now and becomes effective only at the next account-scoped day-boundary.
Revalidation of config / capability / baseline / protection must still pass
before the first intent; an intervening refusal leaves the bot admitted but
inactive. No manual override, warm-up, ramp, or same-day trade path exists
(DEC-0205, DEC-0213, DEC-0261).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Instant, Ok, Result, is_refusal

from qmn.promotion._refuse import clean_token, invalid, policy
from qmn.promotion.battery import (
    PromotionFreshState,
    SilentBatteryReport,
    revalidate_fresh_state,
    run_silent_battery,
)
from qmn.promotion.hub import pull_published_as_of
from qmn.seats.state import OPERATOR_PRINCIPAL, GovernedSeatState
from qmn.time.calendars import (
    ActivationSchedule,
    activation_effective_trading_date,
)

__all__ = [
    "AGENT_SIGNER_PREFIXES",
    "FORBIDDEN_ACTIVATION_OVERRIDES",
    "SAME_DAY_TRADE_PATH_EXISTS",
    "ActivationAcceptance",
    "ActivationReadiness",
    "PromotionLanding",
    "admit_first_intent",
    "promote_to_admitted",
    "refuse_invented_ksa_or_latency",
    "request_activation",
    "revalidate_before_first_intent",
]

AGENT_SIGNER_PREFIXES: Final[tuple[str, ...]] = (
    "agent:",
    "machine:",
    "service:",
    "bot:",
    "qma:",
    "automation:",
    "cron:",
    "systemd:",
)

FORBIDDEN_ACTIVATION_OVERRIDES: Final[frozenset[str]] = frozenset(
    {
        "manual-override",
        "same-day-trade",
        "warm-up",
        "ramp",
        "effective-immediately",
    }
)

SAME_DAY_TRADE_PATH_EXISTS: Final[bool] = False


@dataclass(frozen=True, slots=True)
class PromotionLanding:
    """Successful promotion: ADMITTED, no intents, no ledger, no exposure."""

    seat_id: str
    binding_id: str
    card_fp1: Fingerprint
    fingerprints: Mapping[str, object]
    battery: SilentBatteryReport
    seat_state: GovernedSeatState = GovernedSeatState.ADMITTED
    intents: tuple[()] = ()
    ledger_opened: bool = False
    exposure: None = None
    may_trade: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_id": self.binding_id,
                "card_fp1": self.card_fp1.value,
                "exposure": self.exposure,
                "intents": list(self.intents),
                "ledger_opened": self.ledger_opened,
                "may_trade": self.may_trade,
                "seat_id": self.seat_id,
                "seat_state": self.seat_state.value,
            }
        )


@dataclass(frozen=True, slots=True)
class ActivationAcceptance:
    """Activation record accepted now; enforced only at the next day-boundary."""

    landing: PromotionLanding
    schedule: ActivationSchedule
    operator_signature: str
    requested_state: GovernedSeatState = GovernedSeatState.ACTIVE
    enforced_state: GovernedSeatState = GovernedSeatState.ADMITTED
    may_trade: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "effective_at_ns": self.schedule.effective_at.value_ns,
                "enforced_state": self.enforced_state.value,
                "may_trade": self.may_trade,
                "requested_state": self.requested_state.value,
                "signed_at_ns": self.schedule.signed_at.value_ns,
            }
        )


@dataclass(frozen=True, slots=True)
class ActivationReadiness:
    """Outcome of revalidation at or after the day-boundary, before first intent."""

    acceptance: ActivationAcceptance
    revalidated_at: Instant
    report: SilentBatteryReport | None
    passed: bool
    enforced_state: GovernedSeatState
    may_mint_intent: bool
    refusing_check: str | None

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "enforced_state": self.enforced_state.value,
                "may_mint_intent": self.may_mint_intent,
                "passed": self.passed,
                "refusing_check": self.refusing_check,
                "seat_state": self.enforced_state.value,
            }
        )


def refuse_invented_ksa_or_latency(**extra: object) -> Result[None]:
    """FTR-07: the promotion path invents no KSA or latency numbers."""
    return policy(
        "invented-value",
        "the promotion and activation path invents no KSA or latency numbers (FTR-07)",
        **extra,
    )


def promote_to_admitted(
    *,
    principal: object,
    card: object,
    fresh: object,
    hub: object,
    as_of_artifact_keys: object,
    seat_id: object,
    binding_id: object,
    superseded: object = (),
    activate: object = False,
    ksa_level: object = None,
    latency_ms: object = None,
) -> Result[PromotionLanding]:
    """Human-only promotion click. Success lands ADMITTED with no exposure."""
    invented = _refuse_invented(ksa_level=ksa_level, latency_ms=latency_ms)
    if is_refusal(invented):
        return invented
    actor = _require_operator(principal)
    if is_refusal(actor):
        return actor
    if activate is not False:
        return policy(
            "activate",
            "promotion and activation are separate human acts; a promotion click "
            "never activates and never opens a same-day trade path",
            given=repr(activate),
        )
    viewed = _read_promotion_card(card)
    if is_refusal(viewed):
        return viewed
    card_view = viewed.value
    if not _human_signer(card_view.signer):
        return policy(
            "signer",
            "only a human may promote an artifact into the live zone",
            given=card_view.signer,
        )
    if not isinstance(fresh, PromotionFreshState):
        return invalid(
            "fresh",
            "promotion revalidates PromotionFreshState at click time",
            given=repr(type(fresh).__name__),
        )
    if card_view.template_definition_fp1 is None:
        return policy(
            "template_definition_fp1",
            "a live-zone promotion card attests the Book or BMS definition fingerprint",
        )
    authorized = _authorize_card(
        card_view,
        target_fp1=fresh.live_fingerprints.bot,
        in_force_book=fresh.live_fingerprints.book,
        in_force_bms=fresh.live_fingerprints.bms,
        superseded=superseded,
    )
    if is_refusal(authorized):
        return authorized
    battery = run_silent_battery(fresh)
    if is_refusal(battery):
        return battery
    report = battery.value
    if not report.passed:
        return policy(
            report.refusing_check_id or "battery",
            report.refusing_check
            or "the silent promotion battery refused; the operator sees the refusing check named",
            results=report.as_mapping()["results"],
            refusing_check=report.refusing_check,
        )
    pulled = pull_published_as_of(
        hub,
        artifact_keys=as_of_artifact_keys,
        attested_fp1=card_view.attested_fp1,
        template_fp1=card_view.template_definition_fp1,
    )
    if is_refusal(pulled):
        return pulled
    del pulled
    sid = clean_token(seat_id)
    if sid is None:
        return invalid("seat_id", "promotion lands a non-empty seat id", given=repr(seat_id))
    bid = clean_token(binding_id)
    if bid is None:
        return invalid(
            "binding_id",
            "promotion names the binding the admitted seat will later activate at",
            given=repr(binding_id),
        )
    return Ok(
        PromotionLanding(
            seat_id=sid,
            binding_id=bid,
            card_fp1=card_view.stable_id,
            fingerprints=fresh.live_fingerprints.as_mapping(),
            battery=report,
        )
    )


def request_activation(
    *,
    principal: object,
    landing: object,
    signed_at: object,
    day_boundary: object,
    operator_signature: object,
    manual_override: object = False,
    same_day_trade: object = False,
    warm_up: object = False,
    ramp: object = False,
    effective_immediately: object = False,
    ksa_level: object = None,
    latency_ms: object = None,
) -> Result[ActivationAcceptance]:
    """Accept activation now; it becomes effective at the next day-boundary."""
    invented = _refuse_invented(ksa_level=ksa_level, latency_ms=latency_ms)
    if is_refusal(invented):
        return invented
    actor = _require_operator(principal)
    if is_refusal(actor):
        return actor
    if not isinstance(landing, PromotionLanding):
        return invalid(
            "landing",
            "activation is a separate act on an admitted promotion landing",
            given=repr(type(landing).__name__),
        )
    if landing.seat_state is not GovernedSeatState.ADMITTED or landing.may_trade:
        return policy(
            "landing",
            "activation starts from ADMITTED with no exposure; approval never equals exposure",
            seat_state=landing.seat_state.value,
            may_trade=landing.may_trade,
        )
    if landing.intents or landing.ledger_opened or landing.exposure is not None:
        return policy(
            "landing",
            "an admitted landing carries no intent, ledger, or exposure",
        )
    blocked = _refuse_overrides(
        manual_override=manual_override,
        same_day_trade=same_day_trade,
        warm_up=warm_up,
        ramp=ramp,
        effective_immediately=effective_immediately,
    )
    if is_refusal(blocked):
        return blocked
    signature = clean_token(operator_signature)
    if signature is None:
        return invalid(
            "operator_signature",
            "activation is an operator-signed act",
            given=repr(operator_signature),
        )
    schedule = activation_effective_trading_date(
        binding_id=landing.binding_id,
        signed_at=signed_at,
        day_boundary=day_boundary,
    )
    if is_refusal(schedule):
        return schedule
    return Ok(
        ActivationAcceptance(
            landing=landing,
            schedule=schedule.value,
            operator_signature=signature,
        )
    )


def revalidate_before_first_intent(
    *,
    acceptance: object,
    now: object,
    fresh: object,
    ksa_level: object = None,
    latency_ms: object = None,
) -> Result[ActivationReadiness]:
    """Revalidate at the day-boundary before the first intent (TN-20).

    Before the boundary the bot stays admitted and inactive. After the boundary
    a failed config/capability/baseline/protection check also leaves it admitted
    but inactive.
    """
    invented = _refuse_invented(ksa_level=ksa_level, latency_ms=latency_ms)
    if is_refusal(invented):
        return invented
    if not isinstance(acceptance, ActivationAcceptance):
        return invalid(
            "acceptance",
            "first-intent revalidation reads an ActivationAcceptance",
            given=repr(type(acceptance).__name__),
        )
    if not isinstance(now, Instant):
        return invalid(
            "now",
            "revalidation is dated with an injected Instant",
            given=repr(type(now).__name__),
        )
    if now.value_ns < acceptance.schedule.effective_at.value_ns:
        return Ok(
            ActivationReadiness(
                acceptance=acceptance,
                revalidated_at=now,
                report=None,
                passed=False,
                enforced_state=GovernedSeatState.ADMITTED,
                may_mint_intent=False,
                refusing_check=(
                    "activation becomes effective only at the next boundary of "
                    "the account-scoped day-boundary calendar"
                ),
            )
        )
    report = revalidate_fresh_state(fresh)
    if is_refusal(report):
        return report
    passed = report.value.passed
    return Ok(
        ActivationReadiness(
            acceptance=acceptance,
            revalidated_at=now,
            report=report.value,
            passed=passed,
            enforced_state=GovernedSeatState.ACTIVE if passed else GovernedSeatState.ADMITTED,
            may_mint_intent=passed,
            refusing_check=None if passed else report.value.refusing_check,
        )
    )


def admit_first_intent(*, readiness: object) -> Result[None]:
    """Allow the first intent only after boundary revalidation passed."""
    if not isinstance(readiness, ActivationReadiness):
        return invalid(
            "readiness",
            "the first intent is gated by ActivationReadiness",
            given=repr(type(readiness).__name__),
        )
    if not readiness.may_mint_intent:
        return policy(
            "intent",
            readiness.refusing_check
            or "the first intent is refused; the bot remains admitted but inactive",
            enforced_state=readiness.enforced_state.value,
            seat_state=readiness.acceptance.landing.seat_state.value,
        )
    if readiness.acceptance.landing.seat_state is not GovernedSeatState.ADMITTED:
        return policy(
            "landing",
            "first intent still starts from the admitted landing; activation never "
            "rewrites promotion into exposure",
        )
    return Ok(None)


def _require_operator(principal: object) -> Result[str]:
    token = clean_token(principal)
    if token is None or token != OPERATOR_PRINCIPAL:
        return policy(
            "principal",
            "promotion and activation are operator-principal powers; ops and "
            "agents cannot land live-zone exposure",
            given=repr(principal),
            required=OPERATOR_PRINCIPAL,
        )
    return Ok(token)


def _human_signer(signer: str) -> bool:
    folded = signer.casefold()
    return not any(folded.startswith(prefix) for prefix in AGENT_SIGNER_PREFIXES)


@dataclass(frozen=True, slots=True)
class _CardView:
    """Duck-typed promotion-occurrence card — host owns the registry import."""

    signer: str
    attested_fp1: Fingerprint
    template_definition_fp1: Fingerprint | None
    stable_id: Fingerprint


def _read_promotion_card(card: object) -> Result[_CardView]:
    if card is None:
        return policy(
            "card",
            "no human-signed promotion-occurrence card is present; promotion does not occur",
        )
    signer = clean_token(getattr(card, "signer", None))
    attested = getattr(card, "attested_fp1", None)
    template = getattr(card, "template_definition_fp1", None)
    stable = getattr(card, "stable_id", None)
    if (
        signer is None
        or not isinstance(attested, Fingerprint)
        or not isinstance(stable, Fingerprint)
    ):
        return invalid(
            "card",
            "promotion is a human-signed promotion-occurrence card",
            given=repr(type(card).__name__),
        )
    if template is not None and not isinstance(template, Fingerprint):
        return invalid(
            "template_definition_fp1",
            "the attested Book or BMS definition is an fp1 fingerprint",
            given=repr(template),
        )
    return Ok(
        _CardView(
            signer=signer,
            attested_fp1=attested,
            template_definition_fp1=template,
            stable_id=stable,
        )
    )


def _authorize_card(
    card: _CardView,
    *,
    target_fp1: Fingerprint,
    in_force_book: Fingerprint,
    in_force_bms: Fingerprint,
    superseded: object,
) -> Result[None]:
    if card.attested_fp1 != target_fp1:
        return policy(
            "attested_fp1",
            "the promotion card attests a different bot fingerprint than fresh state",
            attested=card.attested_fp1.value,
            live=target_fp1.value,
        )
    template = card.template_definition_fp1
    if template is None:
        return policy(
            "template_definition_fp1",
            "a live-zone promotion card attests the Book or BMS definition fingerprint",
        )
    if template not in {in_force_book, in_force_bms}:
        return policy(
            "template_definition_fp1",
            "the promotion card attests a Book or BMS definition that is not in force",
            attested_template=template.value,
        )
    superseded_ids = _superseded_ids(superseded)
    if is_refusal(superseded_ids):
        return superseded_ids
    if card.stable_id.value in superseded_ids.value:
        return policy(
            "card",
            "the promotion card has been superseded; only the current head authorizes "
            "the live crossing",
            superseded_card=card.stable_id.value,
        )
    return Ok(None)


def _superseded_ids(value: object) -> Result[frozenset[str]]:
    if value is None:
        return invalid(
            "superseded",
            "supersession state is required; pass an empty collection when nothing supersedes",
        )
    if isinstance(value, (str, bytes, bytearray)):
        return invalid(
            "superseded",
            "supersession state is a collection of card fp1 fingerprints",
            given=repr(type(value).__name__),
        )
    if not isinstance(value, Iterable):
        return invalid(
            "superseded",
            "supersession state is a collection of card fp1 fingerprints",
            given=repr(type(value).__name__),
        )
    ids: list[str] = []
    for item in cast("Iterable[object]", value):
        if isinstance(item, Fingerprint):
            ids.append(item.value)
            continue
        token = clean_token(item)
        if token is None:
            return invalid(
                "superseded",
                "each superseded entry is an fp1 fingerprint or its value",
                given=repr(item),
            )
        ids.append(token)
    return Ok(frozenset(ids))


def _refuse_invented(*, ksa_level: object, latency_ms: object) -> Result[None]:
    if ksa_level is not None or latency_ms is not None:
        return refuse_invented_ksa_or_latency(
            ksa_level=repr(ksa_level),
            latency_ms=repr(latency_ms),
        )
    return Ok(None)


def _refuse_overrides(
    *,
    manual_override: object,
    same_day_trade: object,
    warm_up: object,
    ramp: object,
    effective_immediately: object,
) -> Result[None]:
    flags: tuple[tuple[str, object], ...] = (
        ("manual-override", manual_override),
        ("same-day-trade", same_day_trade),
        ("warm-up", warm_up),
        ("ramp", ramp),
        ("effective-immediately", effective_immediately),
    )
    for name, flag in flags:
        if flag is False:
            continue
        if flag is not True:
            return invalid(name, "activation override flags are bool", given=repr(flag))
        return policy(
            name,
            "no manual override, warm-up, ramp, or same-day trade path exists; "
            "activation becomes effective only at the next account-scoped "
            "day-boundary",
            given=name,
            forbidden=sorted(FORBIDDEN_ACTIVATION_OVERRIDES),
            same_day_trade_path_exists=SAME_DAY_TRADE_PATH_EXISTS,
        )
    return Ok(None)
