"""Story 26.5 — Book paper mode and protective demotions without a per-bot lane."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    AccountRole,
    Fingerprint,
    Instant,
    Money,
    RefusalCategory,
    VenueId,
    World,
    fingerprint,
)
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.binding import BmsInstanceId, BookInstanceId
from qmf.risk.paper import (
    BindingTransitionStream,
    BookMode,
    ExecutionTarget,
    PaperEpochLog,
    PaperTargetLog,
    RoutingOutcome,
    SeatState,
)
from qmn.paper import (
    FORBIDDEN_PER_BOT_PAPER_SURFACES,
    LIVE_OUTAGE_ALARM_CLASS,
    NODE_PAPER_ACCOUNT_ROLE,
    NODE_PAPER_WORLD,
    PAPER_OUTAGE_ALARM_CLASS,
    PAPER_SURFACE,
    POST_ACTIVATION_PAPER_ROUTE,
    MarketRiskBlockKind,
    ProtectiveDemotionKind,
    active_control_for_demotion,
    active_control_for_market_risk,
    build_paired_demo_target,
    fold_book_mode,
    inspect_bot_node_journey,
    mint_operator_paper_flip,
    raise_paper_outage_alarm,
    refuse_per_bot_paper_lane,
    require_demo_paper_target,
    resolve_book_execution_target,
    route_protective_demotion,
)

T = TypeVar("T")

_VENUE = VenueId(value="venue-ctrader")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(seed: str) -> Fingerprint:
    return _ok(fingerprint({"seed": seed}))


def _instant(ns: int = 1_700_000_000_000_000_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _money(value: int = 50_000_00) -> Money:
    return _ok(Money.try_create(value, "USD", 2))


def _book_id(value: str = "book-inst-1") -> BookInstanceId:
    return _ok(BookInstanceId.try_create(value))


def _bms(account: str, seed: str) -> BmsInstanceId:
    return _ok(BmsInstanceId.derive(_fp(seed), account, _VENUE, World.LIVE))


def _live_target(account: str = "acct-live") -> ExecutionTarget:
    return _ok(ExecutionTarget.try_create(AccountRole.LIVE, _VENUE, account))


def _demo_target(account: str = "acct-demo") -> ExecutionTarget:
    return _ok(ExecutionTarget.try_create(AccountRole.DEMO, _VENUE, account))


def _paired(live_epoch: Fingerprint | None = None):
    epoch = live_epoch or _fp("live-binding-1")
    return _ok(
        build_paired_demo_target(
            venue_id=_VENUE,
            account_id="acct-demo",
            live_bms_instance_id=_bms("acct-live", "bms-live"),
            paired_bms_instance_id=_bms("acct-demo", "bms-demo"),
            live_binding_epoch=epoch,
        )
    )


# --- surface -----------------------------------------------------------------


def test_paper_surface_constant() -> None:
    assert PAPER_SURFACE == "qmn.paper"
    assert NODE_PAPER_ACCOUNT_ROLE is AccountRole.DEMO
    assert NODE_PAPER_WORLD is World.LIVE
    assert PAPER_OUTAGE_ALARM_CLASS == LIVE_OUTAGE_ALARM_CLASS == "silent-degradation"


# --- AC1: operator-signed CT-24 PAPER transition -----------------------------


def test_paired_demo_target_role_demo_world_live_no_twins() -> None:
    paired = _paired()
    assert paired.paper_target.role is AccountRole.DEMO
    assert paired.world is World.LIVE
    assert paired.bot_twin_minted is False
    assert paired.book_twin_minted is False
    assert paired.pairing.paired_account_id == "acct-demo"


def test_paper_validation_role_refused_on_node() -> None:
    target = _ok(ExecutionTarget.try_create(AccountRole.PAPER_VALIDATION, _VENUE, "acct-pv"))
    refused = _refusal(require_demo_paper_target(target))
    assert refused.category is RefusalCategory.POLICY_REJECTION


def test_operator_paper_flip_mints_epoch_target_and_no_twin() -> None:
    live_epoch = _fp("live-binding-flip")
    paired = _paired(live_epoch)
    stream = BindingTransitionStream()
    targets = PaperTargetLog()
    epochs = PaperEpochLog()

    package = _ok(
        mint_operator_paper_flip(
            book_instance_id=_book_id(),
            live_binding_epoch=live_epoch,
            transition_instant=_instant(),
            operator_signature="operator:sig-1",
            starting_balance=_money(),
            paired=paired,
            transition_stream=stream,
            paper_target_log=targets,
            paper_epoch_log=epochs,
        )
    )

    assert package.transition.mode is BookMode.PAPER
    assert package.transition.paper_target_ref is not None
    assert package.transition.paper_target_ref.role is AccountRole.DEMO
    assert package.transition.paper_epoch_ref == package.paper_epoch_fingerprint
    assert package.transition.operator_signature == "operator:sig-1"
    assert package.world == "live"
    assert package.bot_twin_minted is False
    assert package.book_twin_minted is False

    mode = _ok(fold_book_mode(stream, _book_id()))
    assert mode is BookMode.PAPER

    active = _ok(targets.resolve_active_target(live_epoch))
    assert active.role is AccountRole.DEMO
    assert active.account_id == "acct-demo"

    current_epoch = _ok(epochs.current_epoch(live_epoch))
    assert current_epoch.starting_balance == _money()


def test_paper_flip_refuses_bot_or_book_twin() -> None:
    live_epoch = _fp("live-binding-twin")
    paired = _paired(live_epoch)
    stream = BindingTransitionStream()
    targets = PaperTargetLog()
    epochs = PaperEpochLog()
    common = {
        "book_instance_id": _book_id(),
        "live_binding_epoch": live_epoch,
        "transition_instant": _instant(),
        "operator_signature": "operator:sig-1",
        "starting_balance": _money(),
        "paired": paired,
        "transition_stream": stream,
        "paper_target_log": targets,
        "paper_epoch_log": epochs,
    }
    bot_twin = _refusal(mint_operator_paper_flip(**common, mint_bot_twin=True))
    assert bot_twin.category is RefusalCategory.POLICY_REJECTION
    book_twin = _refusal(mint_operator_paper_flip(**common, mint_book_twin=True))
    assert book_twin.category is RefusalCategory.POLICY_REJECTION


def test_book_mode_paper_routes_to_paired_demo() -> None:
    resolution = _ok(
        resolve_book_execution_target(
            book_mode=BookMode.PAPER,
            seat_state=SeatState.ACTIVE,
            active_controls=(),
            live_target=_live_target(),
            paper_target=_demo_target(),
        )
    )
    assert resolution.outcome is RoutingOutcome.ROUTED_PAPER
    assert resolution.execution_target is not None
    assert resolution.execution_target.role is AccountRole.DEMO


# --- AC2: capital/authority demotions vs market-risk blocks ------------------


def test_benched_seat_demotion_routes_to_paired_target() -> None:
    resolution = _ok(
        route_protective_demotion(
            kind=ProtectiveDemotionKind.BENCHED_SEAT,
            live_target=_live_target(),
            paper_target=_demo_target(),
            book_mode=BookMode.LIVE,
        )
    )
    assert resolution.outcome is RoutingOutcome.ROUTED_PAPER
    assert resolution.execution_target is not None
    assert resolution.execution_target.account_id == "acct-demo"
    assert "benched" in resolution.routing_reason


def test_kill_line_demotion_routes_while_book_stays_live() -> None:
    resolution = _ok(
        route_protective_demotion(
            kind=ProtectiveDemotionKind.KILL_LINE_STAND_DOWN,
            live_target=_live_target(),
            paper_target=_demo_target(),
            book_mode=BookMode.LIVE,
        )
    )
    assert resolution.outcome is RoutingOutcome.ROUTED_PAPER
    control = _ok(active_control_for_demotion(ProtectiveDemotionKind.KILL_LINE_STAND_DOWN))
    assert control.disposition.value == "routes-to-paper"


def test_market_risk_blocks_paper_and_live_alike() -> None:
    for kind in MarketRiskBlockKind:
        block = _ok(active_control_for_market_risk(kind))
        assert block.disposition.value == "blocks-paper"
        for mode in (BookMode.LIVE, BookMode.PAPER):
            resolution = _ok(
                resolve_book_execution_target(
                    book_mode=mode,
                    seat_state=SeatState.ACTIVE,
                    active_controls=(block,),
                    live_target=_live_target(),
                    paper_target=_demo_target(),
                )
            )
            assert resolution.outcome is RoutingOutcome.BLOCKED
            assert resolution.is_recording_only()


def test_market_risk_dominates_protective_demotion() -> None:
    window = _ok(active_control_for_market_risk(MarketRiskBlockKind.PROTECTION_WINDOW))
    resolution = _ok(
        route_protective_demotion(
            kind=ProtectiveDemotionKind.BENCHED_SEAT,
            live_target=_live_target(),
            paper_target=_demo_target(),
            extra_controls=(window,),
        )
    )
    assert resolution.outcome is RoutingOutcome.BLOCKED


def test_silent_paper_outage_raises_live_alarm_class() -> None:
    alarm = _ok(
        raise_paper_outage_alarm(
            binding_epoch=_fp("paper-binding"),
            paper_account_id="acct-demo",
            cause="silent-outage",
        )
    )
    assert alarm.alarm_class == LIVE_OUTAGE_ALARM_CLASS
    assert alarm.matches_live_class is True
    assert alarm.paper_account_id == "acct-demo"
    assert alarm.cause == "silent-outage"


# --- AC3: no per-bot warm-up / paper lane ------------------------------------


def test_forbidden_per_bot_surfaces_closed_set() -> None:
    assert "per-bot-warm-up" in FORBIDDEN_PER_BOT_PAPER_SURFACES
    assert "probation" in FORBIDDEN_PER_BOT_PAPER_SURFACES
    assert "ramp" in FORBIDDEN_PER_BOT_PAPER_SURFACES
    assert "paper-namespace" in FORBIDDEN_PER_BOT_PAPER_SURFACES
    assert "paper-performance-gate" in FORBIDDEN_PER_BOT_PAPER_SURFACES
    assert POST_ACTIVATION_PAPER_ROUTE == "bms-book-protective-demotion"


def test_refuse_every_forbidden_per_bot_surface() -> None:
    for surface in FORBIDDEN_PER_BOT_PAPER_SURFACES:
        refused = refuse_per_bot_paper_lane(surface)
        assert refused.category is RefusalCategory.POLICY_REJECTION


def test_promoted_bot_journey_has_no_per_bot_lane() -> None:
    journey = _ok(
        inspect_bot_node_journey(
            bot_id="bot-alpha",
            promoted=True,
            activated=True,
        )
    )
    assert journey.per_bot_warm_up is False
    assert journey.probation is False
    assert journey.ramp is False
    assert journey.paper_namespace is False
    assert journey.paper_performance_gate is False
    assert journey.post_activation_paper_route == POST_ACTIVATION_PAPER_ROUTE


def test_requesting_warm_up_or_probation_is_refused() -> None:
    warm = _refusal(inspect_bot_node_journey(bot_id="bot-alpha", request_warm_up=True))
    assert warm.category is RefusalCategory.POLICY_REJECTION
    probation = _refusal(inspect_bot_node_journey(bot_id="bot-alpha", request_probation=True))
    assert probation.category is RefusalCategory.POLICY_REJECTION
    ramp = _refusal(inspect_bot_node_journey(bot_id="bot-alpha", request_ramp=True))
    assert ramp.category is RefusalCategory.POLICY_REJECTION
