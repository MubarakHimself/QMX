"""Stories 26.9 and 26.10 — promote, activate next day, persist closed journals."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeVar, cast

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Fingerprint,
    Instant,
    JournalSink,
    Ok,
    RefusalCategory,
    SinkAck,
    SinkResult,
    TradingDate,
    WriterId,
    fingerprint,
    unpersistable,
)
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.registry.promotion import PromotionCard, PromotionEvent
from qmn.config import compile_node_config
from qmn.observability.logging import (
    LOGS_ARE_NOT_JOURNALS,
    LOGS_SATISFY_CT13_EVIDENCE,
    log_record_is_journal_evidence,
)
from qmn.promotion import (
    ACTIVATION_CT13_EVENT_TYPE,
    ACTIVATION_PAYLOAD_KEYS,
    ACTIVATION_TRIGGER,
    ADMISSION_IMPACT_NONE,
    ADMISSION_IMPACT_RESIGN,
    CT13_SEVEN_EVENT_TYPES,
    DEMO_BASELINE_ENVIRONMENT,
    FORBIDDEN_ACTIVATION_OVERRIDES,
    LIVE_BASELINE_ENVIRONMENT,
    LOG_LINE_SUBSTITUTES_FOR_JOURNAL,
    PROMOTION_EVENT_TYPE,
    PROMOTION_PAYLOAD_KEYS,
    PROMOTION_SURFACE,
    SAME_DAY_TRADE_PATH_EXISTS,
    SANDBOX_PROVENANCE,
    ActivationPhase,
    AdmissionLayerFreshState,
    BatteryCheckId,
    ConfigGateFreshState,
    Ct18CapabilityFreshState,
    HubArtifact,
    IdentityFingerprints,
    LiveBaselineFreshState,
    PromotionFreshState,
    PromotionLanding,
    ProtectionFreshState,
    PublishedHub,
    admit_first_intent,
    assert_closed_ct13_event_type,
    commit_activation,
    commit_promotion,
    live_gating_from_config,
    map_activation_ct13_event_type,
    persist_promotion,
    promote_to_admitted,
    promotion_journal_payload,
    publish_hub_fragment,
    pull_published_as_of,
    reconstruct_activation,
    refuse_invented_ksa_or_latency,
    refuse_sandbox_provenance,
    request_activation,
    revalidate_before_first_intent,
    run_silent_battery,
)
from qmn.seats import OPERATOR_PRINCIPAL, GovernedSeatState
from qmn.time.calendars import ActivationSchedule, CalendarKind

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000
_BOUNDARY_NS = _NS + 86_400_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(tag: str) -> Fingerprint:
    return _ok(fingerprint({"class": "test-id", "tag": tag}))


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", "promotion", "boot-1"))


def _card(*, attested: Fingerprint, template: Fingerprint, signer: str = "operator:mubarak"):
    return _ok(
        PromotionCard.sign(
            signer=signer,
            plain_words_summary="Promote the reviewed bot into the live zone.",
            attested_fp1=attested,
            template_definition_fp1=template,
            writer=_writer(),
            sequence=0,
            signed_at=_instant(),
        )
    )


def _admission(*, layer1: bool = True, layer2: bool = True, layer3: bool = True):
    return _ok(
        AdmissionLayerFreshState.try_create(
            layer1_linters_passed=layer1,
            layer2_shakedown_passed=layer2,
            layer3_operator_signature_present=layer3,
        )
    )


def _ids(
    *,
    book: Fingerprint | None = None,
    bms: Fingerprint | None = None,
    bot: Fingerprint | None = None,
    config: Fingerprint | None = None,
) -> IdentityFingerprints:
    return _ok(
        IdentityFingerprints.try_create(
            book=book or _fp("book"),
            bms=bms or _fp("bms"),
            bot=bot or _fp("bot"),
            config=config or _fp("config"),
        )
    )


def _ct18(*, required: object = ("hedging",), declared: object = ("hedging", "netting")):
    return _ok(Ct18CapabilityFreshState.try_create(required=required, declared=declared))


def _baselines(
    *,
    environment: str = LIVE_BASELINE_ENVIRONMENT,
    sqs: bool = True,
    rung: bool = True,
):
    return _ok(
        LiveBaselineFreshState.try_create(
            sqs_environment=environment,
            sqs_baseline_present=sqs,
            live_path_rung_baseline_present=rung,
        )
    )


def _gate(
    *,
    impact: str = ADMISSION_IMPACT_NONE,
    resign_discharged: bool = True,
    blanks: object = (),
    unratified: object = (),
):
    return _ok(
        ConfigGateFreshState.try_create(
            admission_impact=impact,
            resign_discharged=resign_discharged,
            blank_live_gating_names=blanks,
            unratified_live_gating_names=unratified,
        )
    )


def _protection(*, entries_admitted: bool = True) -> ProtectionFreshState:
    return _ok(ProtectionFreshState.try_create(entries_admitted=entries_admitted))


def _fresh(
    *,
    ids: IdentityFingerprints | None = None,
    admission: AdmissionLayerFreshState | None = None,
    ct18: Ct18CapabilityFreshState | None = None,
    baselines: LiveBaselineFreshState | None = None,
    gate: ConfigGateFreshState | None = None,
    protection: ProtectionFreshState | None = None,
    card_ids: IdentityFingerprints | None = None,
) -> PromotionFreshState:
    live = ids or _ids()
    return PromotionFreshState(
        admission=admission or _admission(),
        live_fingerprints=live,
        card_fingerprints=card_ids or live,
        ct18=ct18 or _ct18(),
        live_baselines=baselines or _baselines(),
        config_gate=gate or _gate(),
        protection=protection or _protection(),
    )


def _artifact(key: str, fp: Fingerprint, provenance: str = "live") -> HubArtifact:
    return _ok(HubArtifact.try_create(artifact_key=key, fp1=fp, provenance=provenance))


def _hub_for(fresh: PromotionFreshState) -> PublishedHub:
    return PublishedHub(
        artifacts=(
            _artifact("bot", fresh.live_fingerprints.bot),
            _artifact("book", fresh.live_fingerprints.book),
        )
    )


@dataclass
class _FakeDayBoundary:
    identity: CalendarIdentity
    next_ns: int

    def trading_date_for(self, instant: Instant) -> Result[TradingDate]:
        del instant
        civil = _ok(CivilDate.try_create(2026, 9, 1))
        return TradingDate.try_create(self.identity, civil)

    def next_boundary_after(self, instant: Instant) -> Result[Instant]:
        del instant
        return Instant.try_create(self.next_ns)


def _day_boundary(next_ns: int = _BOUNDARY_NS) -> _FakeDayBoundary:
    identity = _ok(CalendarIdentity.try_create("account-day-boundary", "v1", "2026a"))
    return _FakeDayBoundary(identity=identity, next_ns=next_ns)


def _promote(
    fresh: PromotionFreshState | None = None, **overrides: object
) -> Result[PromotionLanding]:
    state = fresh or _fresh()
    args: dict[str, object] = {
        "principal": OPERATOR_PRINCIPAL,
        "card": _card(attested=state.live_fingerprints.bot, template=state.live_fingerprints.book),
        "fresh": state,
        "hub": _hub_for(state),
        "as_of_artifact_keys": ("bot", "book"),
        "seat_id": "seat-1",
        "binding_id": "binding-1",
    }
    args.update(overrides)
    return promote_to_admitted(**args)  # type: ignore[arg-type]


# --- surface -----------------------------------------------------------------


def test_promotion_surface_marker() -> None:
    assert PROMOTION_SURFACE == "qmn.promotion"
    assert SAME_DAY_TRADE_PATH_EXISTS is False
    assert SANDBOX_PROVENANCE == "sandbox"
    assert "warm-up" in FORBIDDEN_ACTIVATION_OVERRIDES


# --- silent battery ----------------------------------------------------------


def test_silent_battery_passes_in_operator_words() -> None:
    report = _ok(run_silent_battery(_fresh()))
    assert report.passed is True
    assert report.refusing_check is None
    words = [item.as_mapping()["check"] for item in report.checks]
    assert "The three admission layers still pass" in words
    assert "Book, BMS, bot, and config fingerprints match" in words
    assert "Venue capabilities still satisfy the Book" in words
    assert "Live-conditioned baselines are present" in words
    assert all("layer-1" not in str(word) for word in words)
    assert BatteryCheckId.PROTECTION not in {item.check_id for item in report.checks}


def test_battery_names_each_refusing_check() -> None:
    cases: tuple[tuple[PromotionFreshState, str], ...] = (
        (_fresh(admission=_admission(layer1=False)), "admission-layers"),
        (
            _fresh(ids=_ids(bot=_fp("bot-a")), card_ids=_ids(bot=_fp("bot-b"))),
            "fingerprints",
        ),
        (
            _fresh(ct18=_ct18(required=("amend_protection",), declared=("hedging",))),
            "ct18-capabilities",
        ),
        (
            _fresh(baselines=_baselines(environment=DEMO_BASELINE_ENVIRONMENT)),
            "live-baselines",
        ),
        (
            _fresh(gate=_gate(impact=ADMISSION_IMPACT_RESIGN, resign_discharged=False)),
            "admission-impact",
        ),
        (_fresh(gate=_gate(blanks=("kill_line_capital_floor",))), "blanks"),
        (_fresh(gate=_gate(unratified=("kill_line_capital_floor",))), "value-status"),
    )
    for state, check_id in cases:
        report = _ok(run_silent_battery(state))
        assert report.passed is False, check_id
        assert report.refusing_check_id == check_id
        assert report.refusing_check is not None
        refused = _refusal(_promote(state))
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["field"] == check_id


def test_demo_baseline_never_satisfies_live_promotion() -> None:
    state = _fresh(baselines=_baselines(environment=DEMO_BASELINE_ENVIRONMENT, sqs=True, rung=True))
    report = _ok(run_silent_battery(state))
    assert report.passed is False
    assert report.refusing_check_id == "live-baselines"


def test_live_gating_from_blank_config_fails_value_status() -> None:
    config = _ok(compile_node_config())
    gate = _ok(
        live_gating_from_config(
            config,
            admission_impact=ADMISSION_IMPACT_NONE,
            resign_discharged=True,
        )
    )
    assert gate.blank_live_gating_names
    assert gate.unratified_live_gating_names
    report = _ok(run_silent_battery(_fresh(gate=gate)))
    assert report.passed is False
    assert report.refusing_check_id == "blanks"


# --- hub sandbox -------------------------------------------------------------


def test_sandbox_refused_at_publish_and_pull() -> None:
    live_fp = _fp("bot")
    sandbox = _artifact("bot", live_fp, provenance=SANDBOX_PROVENANCE)
    published = _refusal(publish_hub_fragment(sandbox))
    assert published.context["field"] == "provenance"
    assert published.context["crossing"] == "publish"
    hub = PublishedHub(artifacts=(sandbox, _artifact("book", _fp("book"))))
    pulled = _refusal(
        pull_published_as_of(
            hub,
            artifact_keys=("bot", "book"),
            attested_fp1=live_fp,
            template_fp1=_fp("book"),
        )
    )
    assert pulled.context["field"] == "provenance"
    assert pulled.context["crossing"] == "pull"
    assert is_ok(refuse_sandbox_provenance("live", crossing="pull"))


def test_as_of_set_containing_sandbox_refuses_whole_pull() -> None:
    bot = _fp("bot")
    book = _fp("book")
    hub = PublishedHub(
        artifacts=(
            _artifact("bot", bot, provenance="live"),
            _artifact("book", book, provenance=SANDBOX_PROVENANCE),
        )
    )
    refused = _refusal(
        pull_published_as_of(
            hub,
            artifact_keys=("bot", "book"),
            attested_fp1=bot,
            template_fp1=book,
        )
    )
    assert refused.context["crossing"] == "pull"


# --- promotion landing -------------------------------------------------------


def test_successful_promotion_lands_admitted_with_no_exposure() -> None:
    landing = _ok(_promote())
    assert landing.seat_state is GovernedSeatState.ADMITTED
    assert landing.intents == ()
    assert landing.ledger_opened is False
    assert landing.exposure is None
    assert landing.may_trade is False
    assert landing.as_mapping()["seat_state"] == "admitted"
    assert landing.battery.passed is True


def test_ops_and_agent_cannot_promote() -> None:
    ops = _refusal(_promote(principal="ops"))
    assert ops.category is RefusalCategory.POLICY_REJECTION
    assert ops.context["field"] == "principal"
    fresh = _fresh()
    card = _card(
        attested=fresh.live_fingerprints.bot,
        template=fresh.live_fingerprints.book,
        signer="agent:quant",
    )
    agent = _refusal(_promote(fresh, card=card))
    assert agent.context["field"] == "signer"


def test_promotion_never_activates_in_the_same_act() -> None:
    refused = _refusal(_promote(activate=True))
    assert refused.context["field"] == "activate"
    invented = refuse_invented_ksa_or_latency(ksa_level="3")
    assert is_refusal(invented)
    numbers = _refusal(_promote(ksa_level=3, latency_ms=12))
    assert numbers.context["field"] == "invented-value"


def test_missing_or_superseded_card_refuses_promotion() -> None:
    refused = _refusal(_promote(card=None))
    assert refused.context["field"] == "card"
    landing_fresh = _fresh()
    card = _card(
        attested=landing_fresh.live_fingerprints.bot,
        template=landing_fresh.live_fingerprints.book,
    )
    superseded = _refusal(_promote(landing_fresh, card=card, superseded=(card.stable_id,)))
    assert superseded.context["field"] == "card"


# --- activation at the next day-boundary ------------------------------------


def test_activation_accepted_mid_day_is_not_yet_effective() -> None:
    landing = _ok(_promote())
    accepted = _ok(
        request_activation(
            principal=OPERATOR_PRINCIPAL,
            landing=landing,
            signed_at=_instant(_NS),
            day_boundary=_day_boundary(),
            operator_signature="sig-operator-activate",
        )
    )
    assert isinstance(accepted.schedule, ActivationSchedule)
    assert accepted.schedule.calendar_kind is CalendarKind.DAY_BOUNDARY
    assert accepted.schedule.effective_at.value_ns == _BOUNDARY_NS
    assert accepted.schedule.signed_at.value_ns == _NS
    assert accepted.requested_state is GovernedSeatState.ACTIVE
    assert accepted.enforced_state is GovernedSeatState.ADMITTED
    assert accepted.may_trade is False
    too_soon = _ok(
        revalidate_before_first_intent(
            acceptance=accepted,
            now=_instant(_NS + 1),
            fresh=_fresh(),
        )
    )
    assert too_soon.passed is False
    assert too_soon.may_mint_intent is False
    assert too_soon.enforced_state is GovernedSeatState.ADMITTED
    intent = _refusal(admit_first_intent(readiness=too_soon))
    assert intent.category is RefusalCategory.POLICY_REJECTION
    assert "day-boundary" in str(intent.context["reason"])
    assert intent.context["seat_state"] == "admitted"


def test_no_override_warm_up_ramp_or_same_day_path() -> None:
    landing = _ok(_promote())
    flags = (
        {"manual_override": True},
        {"same_day_trade": True},
        {"warm_up": True},
        {"ramp": True},
        {"effective_immediately": True},
    )
    for kwargs in flags:
        refused = _refusal(
            request_activation(
                principal=OPERATOR_PRINCIPAL,
                landing=landing,
                signed_at=_instant(),
                day_boundary=_day_boundary(),
                operator_signature="sig-operator-activate",
                **kwargs,
            )
        )
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["same_day_trade_path_exists"] is False


def test_revalidation_pass_admits_first_intent_after_boundary() -> None:
    landing = _ok(_promote())
    accepted = _ok(
        request_activation(
            principal=OPERATOR_PRINCIPAL,
            landing=landing,
            signed_at=_instant(_NS),
            day_boundary=_day_boundary(),
            operator_signature="sig-operator-activate",
        )
    )
    ready = _ok(
        revalidate_before_first_intent(
            acceptance=accepted,
            now=_instant(_BOUNDARY_NS),
            fresh=_fresh(),
        )
    )
    assert ready.passed is True
    assert ready.may_mint_intent is True
    assert ready.enforced_state is GovernedSeatState.ACTIVE
    assert ready.acceptance.landing.seat_state is GovernedSeatState.ADMITTED
    assert is_ok(admit_first_intent(readiness=ready))


def test_intervening_refusal_leaves_admitted_but_inactive() -> None:
    landing = _ok(_promote())
    accepted = _ok(
        request_activation(
            principal=OPERATOR_PRINCIPAL,
            landing=landing,
            signed_at=_instant(_NS),
            day_boundary=_day_boundary(),
            operator_signature="sig-operator-activate",
        )
    )
    stale = _fresh(ct18=_ct18(required=("amend_protection",), declared=("hedging",)))
    ready = _ok(
        revalidate_before_first_intent(
            acceptance=accepted,
            now=_instant(_BOUNDARY_NS),
            fresh=stale,
        )
    )
    assert ready.passed is False
    assert ready.may_mint_intent is False
    assert ready.enforced_state is GovernedSeatState.ADMITTED
    assert ready.refusing_check == "Venue capabilities still satisfy the Book"
    assert landing.seat_state is GovernedSeatState.ADMITTED
    intent = _refusal(admit_first_intent(readiness=ready))
    assert intent.context["enforced_state"] == "admitted"
    blocked_protection = _ok(
        revalidate_before_first_intent(
            acceptance=accepted,
            now=_instant(_BOUNDARY_NS),
            fresh=_fresh(protection=_protection(entries_admitted=False)),
        )
    )
    assert blocked_protection.enforced_state is GovernedSeatState.ADMITTED
    assert blocked_protection.may_mint_intent is False


# --- Story 26.10: closed journal paths --------------------------------------


class _RecordingJournal:
    def __init__(self) -> None:
        self.appended: list[object] = []

    def append(self, event: object, /) -> SinkResult:
        self.appended.append(event)
        return Ok(SinkAck())


class _FailingJournal:
    def append(self, event: object, /) -> SinkResult:
        del event
        return unpersistable("journal room unavailable")


def _as_map(row: object) -> dict[str, object]:
    assert isinstance(row, Mapping)
    return dict(cast("Mapping[str, object]", row))


def _request() -> object:
    landing = _ok(_promote())
    return _ok(
        request_activation(
            principal=OPERATOR_PRINCIPAL,
            landing=landing,
            signed_at=_instant(_NS),
            day_boundary=_day_boundary(),
            operator_signature="sig-operator-activate",
        )
    )


def test_accepted_promotion_journals_card_fp1_and_correlation_id_only() -> None:
    landing = _ok(_promote())
    journal = _RecordingJournal()
    committed = _ok(commit_promotion(landing, journal=journal, correlation_id="corr-promo-1"))
    assert committed is landing
    assert len(journal.appended) == 1
    row = _as_map(journal.appended[0])
    assert row["event_type"] == PROMOTION_EVENT_TYPE == "promotion"
    assert row["correlation_id"] == "corr-promo-1"
    raw_payload = row["payload"]
    assert isinstance(raw_payload, dict)
    payload = dict(cast("Mapping[str, object]", raw_payload))
    assert set(payload) == set(PROMOTION_PAYLOAD_KEYS) == {"promotion_card_fp1"}
    assert payload["promotion_card_fp1"] == landing.card_fp1.value
    canonical = _ok(PromotionEvent.try_create(landing.card_fp1, correlation_id="corr-promo-1"))
    assert dict(payload) == canonical.journal_payload()
    assert "correlation_id" not in payload
    for widened in ("operator", "artifact", "config", "binding", "binding_id", "seat_id"):
        assert widened not in payload
        assert widened not in row
    assert isinstance(journal, JournalSink)


def test_promotion_payload_builder_stays_closed() -> None:
    landing = _ok(_promote())
    payload = dict(_ok(promotion_journal_payload(landing.card_fp1)))
    assert set(payload) == set(PROMOTION_PAYLOAD_KEYS)
    persisted = _ok(
        persist_promotion(
            journal=_RecordingJournal(),
            card_fp1=landing.card_fp1,
            correlation_id="corr-2",
        )
    )
    assert persisted.event_type == PROMOTION_EVENT_TYPE
    assert set(persisted.payload) == set(PROMOTION_PAYLOAD_KEYS)
    assert persisted.correlation_id == "corr-2"


def test_activation_requested_refused_successful_use_ct24_risk_transition() -> None:
    accepted = _request()
    journal = _RecordingJournal()
    requested = _ok(
        commit_activation(
            journal=journal,
            phase=ActivationPhase.REQUESTED,
            acceptance=accepted,
            correlation_id="corr-act-req",
        )
    )
    assert requested.applied is True
    assert requested.event.event_type == ACTIVATION_CT13_EVENT_TYPE == "risk transition"
    assert requested.event.event_type != PROMOTION_EVENT_TYPE
    assert requested.transition.trigger_kind == ACTIVATION_TRIGGER
    assert requested.transition.requested_state is GovernedSeatState.ACTIVE
    assert requested.transition.enforced_state is GovernedSeatState.ADMITTED
    req_row = _as_map(journal.appended[-1])
    assert req_row["event_type"] == "risk transition"
    assert set(_as_map(req_row["payload"])) == set(ACTIVATION_PAYLOAD_KEYS) == {"transition_fp1"}

    refused = _ok(
        commit_activation(
            journal=journal,
            phase=ActivationPhase.REFUSED,
            acceptance=accepted,
            refusing_check="the silent promotion battery refused",
            correlation_id="corr-act-ref",
        )
    )
    assert refused.applied is False
    assert refused.event.event_type == "risk transition"
    assert refused.transition.enforced_state is GovernedSeatState.ADMITTED
    assert refused.transition.requested_state is GovernedSeatState.ACTIVE
    assert refused.transition.operator_signature == "sig-operator-activate"

    ready = _ok(
        revalidate_before_first_intent(
            acceptance=accepted,
            now=_instant(_BOUNDARY_NS),
            fresh=_fresh(),
        )
    )
    successful = _ok(
        commit_activation(
            journal=journal,
            phase=ActivationPhase.SUCCESSFUL,
            readiness=ready,
            correlation_id="corr-act-ok",
        )
    )
    assert successful.applied is True
    assert successful.event.event_type == "risk transition"
    assert successful.transition.enforced_state is GovernedSeatState.ACTIVE
    assert successful.transition.requested_state is GovernedSeatState.ACTIVE
    assert all(_as_map(item)["event_type"] == "risk transition" for item in journal.appended)
    assert len(journal.appended) == 3


def test_activation_never_uses_promotion_or_an_eighth_type() -> None:
    accepted = _request()
    journal = _RecordingJournal()
    as_promotion = _refusal(
        commit_activation(
            journal=journal,
            phase=ActivationPhase.REQUESTED,
            acceptance=accepted,
            event_type=PROMOTION_EVENT_TYPE,
            correlation_id="corr-wrong",
        )
    )
    assert as_promotion.category is RefusalCategory.POLICY_REJECTION
    assert as_promotion.context["field"] == "event_type"
    assert as_promotion.context["mapped"] == ACTIVATION_CT13_EVENT_TYPE
    assert journal.appended == []

    eighth = _refusal(map_activation_ct13_event_type("activation"))
    assert eighth.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert eighth.context["ftr"] == "FTR-01"
    invented = _refusal(assert_closed_ct13_event_type("seat-transition"))
    assert invented.context["ftr"] == "FTR-01"
    assert "activation" not in CT13_SEVEN_EVENT_TYPES
    assert "seat-transition" not in CT13_SEVEN_EVENT_TYPES
    assert PROMOTION_EVENT_TYPE in CT13_SEVEN_EVENT_TYPES
    assert ACTIVATION_CT13_EVENT_TYPE in CT13_SEVEN_EVENT_TYPES
    assert _ok(map_activation_ct13_event_type()) == "risk transition"


def test_requested_vs_enforced_reconstructed_from_ct24_not_payload() -> None:
    accepted = _request()
    journal = _RecordingJournal()
    committed = _ok(
        commit_activation(
            journal=journal,
            phase=ActivationPhase.REQUESTED,
            acceptance=accepted,
            correlation_id="corr-recon",
        )
    )
    row = _as_map(journal.appended[0])
    raw_payload = row["payload"]
    assert isinstance(raw_payload, dict)
    payload = dict(cast("Mapping[str, object]", raw_payload))
    assert set(payload) == {"transition_fp1"}
    assert "requested_state" not in payload
    assert "enforced_state" not in payload
    assert "operator_signature" not in payload
    assert "principal" not in payload
    fp = _ok(committed.transition.fingerprint())
    rebuilt = _ok(reconstruct_activation(row, {fp.value: committed.transition}))
    assert rebuilt.requested_state is GovernedSeatState.ACTIVE
    assert rebuilt.enforced_state is GovernedSeatState.ADMITTED
    assert rebuilt.principal == "sig-operator-activate"
    assert rebuilt.phase is ActivationPhase.REQUESTED
    assert rebuilt.transition_fp1 == fp


def test_journal_sink_refusal_blocks_promotion_and_activation_state() -> None:
    landing = _ok(_promote())
    failing = _FailingJournal()
    blocked_promo = _refusal(commit_promotion(landing, journal=failing, correlation_id="corr-fail"))
    assert blocked_promo.category is RefusalCategory.STORAGE_FAILURE
    assert isinstance(failing, JournalSink)

    accepted = _request()
    blocked_act = _refusal(
        commit_activation(
            journal=_FailingJournal(),
            phase=ActivationPhase.REQUESTED,
            acceptance=accepted,
            correlation_id="corr-fail-act",
        )
    )
    assert blocked_act.category is RefusalCategory.STORAGE_FAILURE
    ready = _ok(
        revalidate_before_first_intent(
            acceptance=accepted,
            now=_instant(_BOUNDARY_NS),
            fresh=_fresh(),
        )
    )
    blocked_success = _refusal(
        commit_activation(
            journal=_FailingJournal(),
            phase=ActivationPhase.SUCCESSFUL,
            readiness=ready,
            correlation_id="corr-fail-ok",
        )
    )
    assert blocked_success.category is RefusalCategory.STORAGE_FAILURE
    not_a_sink = _refusal(persist_promotion(journal=object(), card_fp1=landing.card_fp1))
    assert not_a_sink.category is RefusalCategory.INVALID_INPUT
    assert not_a_sink.context["log_line_substitutes"] is False
    assert not_a_sink.context["logs_are_not_journals"] is True


def test_log_line_never_substitutes_for_missing_journal_record() -> None:
    assert LOG_LINE_SUBSTITUTES_FOR_JOURNAL is False
    assert LOGS_ARE_NOT_JOURNALS is True
    assert LOGS_SATISFY_CT13_EVIDENCE is False
    assert log_record_is_journal_evidence() is False
    landing = _ok(_promote())
    refused = _refusal(commit_promotion(landing, journal="a-log-line", correlation_id="c"))
    assert refused.context["log_record_is_journal_evidence"] is False
    assert refused.context["log_line_substitutes"] is False
