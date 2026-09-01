"""Story 26.1 — scoped KSA severity fold and ratified effect-matrix cells."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import Instant, VenueId
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.risk.control_action import SatisfactionPredicate, SubjectScope
from qmf.risk.control_rank import ControlActionKind
from qmn.protection import (
    AUTO_DEESCALATION_EVENTS,
    EFFECT_MATRIX_BLANK_EFFECTS,
    KSA_EFFECT_KINDS,
    KSA_EFFECT_MATRIX_REGISTRY_KEY,
    KSA_LEVELS,
    KSA_TRIGGER_CLASSES,
    LEVEL_RANK,
    PROTECTION_SURFACE,
    VALUE_STATUS_BLANK,
    CompiledEffectMatrix,
    KsaEnforcementScope,
    KsaLevel,
    KsaTriggerClass,
    PaperDisposition,
    cell_blocks_role_live,
    cell_blocks_soak,
    compile_effect_matrix,
    compile_ksa_effect_cell,
    effective_ksa_level,
    fold_ksa_level,
    ksa_levels,
    ksa_trigger_classes,
    matrix_blocks_role_live,
    matrix_blocks_soak,
    matrix_supplies_no_default_values,
    mint_escalation,
    mint_level_epoch,
    paper_disposition_for,
    resume,
    stream_blocked_by_escalation,
)

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int) -> Instant:
    return _ok(Instant.try_create(ns))


def _venue(token: str = "venue-a") -> VenueId:
    return _ok(VenueId.try_create(token))


def _stream_scope(
    venue: VenueId | None = None,
    account: str = "live-1",
) -> KsaEnforcementScope:
    return _ok(KsaEnforcementScope.stream(venue or _venue(), account))


# --- vocabulary ---------------------------------------------------------------


def test_protection_surface_name() -> None:
    assert PROTECTION_SURFACE == "qmn.protection"


def test_ksa_levels_exact_closed_vocabulary() -> None:
    assert ksa_levels() == (
        KsaLevel.GREEN,
        KsaLevel.YELLOW,
        KsaLevel.ORANGE,
        KsaLevel.RED,
        KsaLevel.BLACK,
    )
    assert tuple(level.value for level in KSA_LEVELS) == (
        "GREEN",
        "YELLOW",
        "ORANGE",
        "RED",
        "BLACK",
    )
    assert LEVEL_RANK[KsaLevel.GREEN] < LEVEL_RANK[KsaLevel.YELLOW]
    assert LEVEL_RANK[KsaLevel.BLACK] == max(LEVEL_RANK.values())


def test_ksa_trigger_classes_exact_vocabulary() -> None:
    assert ksa_trigger_classes() == (
        KsaTriggerClass.SCHEDULED_NEWS,
        KsaTriggerClass.BLACK_SWAN,
        KsaTriggerClass.CONNECTIVITY,
        KsaTriggerClass.UNKNOWN_STATE,
    )
    assert tuple(t.value for t in KSA_TRIGGER_CLASSES) == (
        "scheduled_news",
        "black_swan",
        "connectivity",
        "unknown_state",
    )


def test_paper_disposition_fixed_for_ksa_triggers() -> None:
    for trigger in KSA_TRIGGER_CLASSES:
        assert _ok(paper_disposition_for(trigger)) is PaperDisposition.BLOCKS_PAPER


# --- monotone fold ------------------------------------------------------------


def test_fold_monotone_non_decreasing_within_level_epoch() -> None:
    scope = _stream_scope()
    epoch = _ok(
        mint_level_epoch(
            epoch_id="epoch-1",
            scope=scope,
            opened_at=_instant(1_000),
            opened_by="boot",
        )
    )
    yellow = _ok(
        mint_escalation(
            level=KsaLevel.YELLOW,
            trigger_class=KsaTriggerClass.CONNECTIVITY,
            scope=scope,
            level_epoch_id=epoch.epoch_id,
            issued_at=_instant(2_000),
            writer_id="writer-z",
            arbitration_rank=2,
        )
    )
    orange = _ok(
        mint_escalation(
            level=KsaLevel.ORANGE,
            trigger_class=KsaTriggerClass.UNKNOWN_STATE,
            scope=scope,
            level_epoch_id=epoch.epoch_id,
            issued_at=_instant(3_000),
            writer_id="writer-a",
            arbitration_rank=1,
        )
    )
    # A later lower-severity record must not pull the fold down.
    later_greenish = _ok(
        mint_escalation(
            level=KsaLevel.YELLOW,
            trigger_class=KsaTriggerClass.CONNECTIVITY,
            scope=scope,
            level_epoch_id=epoch.epoch_id,
            issued_at=_instant(4_000),
            writer_id="writer-m",
            arbitration_rank=0,
            quiet_elapsed_ns=60_000_000_000,
        )
    )
    folded = _ok(fold_ksa_level([yellow, orange, later_greenish], scope=scope, epoch=epoch))
    assert folded is KsaLevel.ORANGE


def test_writer_id_byte_order_never_lowers_severity() -> None:
    scope = KsaEnforcementScope.global_scope()
    epoch = _ok(
        mint_level_epoch(
            epoch_id="epoch-g",
            scope=scope,
            opened_at=_instant(10),
        )
    )
    # Same instant: lower WriterId byte order ("aaa" < "zzz") must not win over
    # a higher-severity record that carries a worse arbitration_rank number
    # only as attribution — fold takes max level regardless of writer order.
    high = _ok(
        mint_escalation(
            level=KsaLevel.RED,
            trigger_class=KsaTriggerClass.BLACK_SWAN,
            scope=scope,
            level_epoch_id=epoch.epoch_id,
            issued_at=_instant(100),
            writer_id="zzz-writer",
            arbitration_rank=9,
        )
    )
    low = _ok(
        mint_escalation(
            level=KsaLevel.YELLOW,
            trigger_class=KsaTriggerClass.SCHEDULED_NEWS,
            scope=scope,
            level_epoch_id=epoch.epoch_id,
            issued_at=_instant(100),
            writer_id="aaa-writer",
            arbitration_rank=0,
        )
    )
    # Present writers in byte-ascending order; severity still RED.
    folded = _ok(fold_ksa_level([low, high], scope=scope, epoch=epoch))
    assert folded is KsaLevel.RED
    # Quiet time on a low record never decays the fold.
    quiet = _ok(
        mint_escalation(
            level=KsaLevel.GREEN,
            trigger_class=KsaTriggerClass.CONNECTIVITY,
            scope=scope,
            level_epoch_id=epoch.epoch_id,
            issued_at=_instant(200),
            writer_id="quiet",
            arbitration_rank=0,
            quiet_elapsed_ns=10**15,
        )
    )
    assert _ok(fold_ksa_level([high, quiet], scope=scope, epoch=epoch)) is KsaLevel.RED


def test_effective_level_is_most_restrictive_covering_scope() -> None:
    assert _ok(effective_ksa_level(global_level="ORANGE", stream_level="YELLOW")) is KsaLevel.ORANGE
    assert _ok(effective_ksa_level(global_level="GREEN", stream_level="BLACK")) is KsaLevel.BLACK


def test_fold_ignores_other_scope_and_other_epoch() -> None:
    live = _stream_scope(account="live-1")
    demo = _stream_scope(account="demo-1")
    epoch = _ok(mint_level_epoch(epoch_id="e1", scope=live, opened_at=_instant(1)))
    other_epoch = _ok(mint_level_epoch(epoch_id="e2", scope=live, opened_at=_instant(2)))
    foreign = _ok(
        mint_escalation(
            level=KsaLevel.BLACK,
            trigger_class=KsaTriggerClass.CONNECTIVITY,
            scope=demo,
            level_epoch_id=epoch.epoch_id,
            issued_at=_instant(3),
            writer_id="w",
            arbitration_rank=0,
        )
    )
    stale_epoch = _ok(
        mint_escalation(
            level=KsaLevel.RED,
            trigger_class=KsaTriggerClass.CONNECTIVITY,
            scope=live,
            level_epoch_id=other_epoch.epoch_id,
            issued_at=_instant(4),
            writer_id="w",
            arbitration_rank=0,
        )
    )
    assert _ok(fold_ksa_level([foreign, stale_epoch], scope=live, epoch=epoch)) is KsaLevel.GREEN


# --- resume -------------------------------------------------------------------


def test_resume_names_exact_scope_and_opens_new_epoch() -> None:
    scope = _stream_scope()
    prior = _ok(mint_level_epoch(epoch_id="e-prior", scope=scope, opened_at=_instant(1)))
    # Escalate inside prior epoch.
    _ = _ok(
        mint_escalation(
            level=KsaLevel.ORANGE,
            trigger_class=KsaTriggerClass.CONNECTIVITY,
            scope=scope,
            level_epoch_id=prior.epoch_id,
            issued_at=_instant(2),
            writer_id="w",
            arbitration_rank=0,
        )
    )
    record = _ok(
        resume(
            scope=scope,
            authority="operator",
            issued_at=_instant(3),
            prior_epoch=prior,
            new_epoch_id="e-resume",
            fresh_state_validated=True,
        )
    )
    assert record.new_epoch.epoch_id == "e-resume"
    assert record.new_epoch.opened_by == "resume"
    assert record.new_epoch.scope.matches(scope)
    assert record.prior_epoch_id == prior.epoch_id
    # New epoch starts GREEN even if prior records exist for the old epoch.
    assert (
        _ok(
            fold_ksa_level(
                [
                    _ok(
                        mint_escalation(
                            level=KsaLevel.ORANGE,
                            trigger_class=KsaTriggerClass.CONNECTIVITY,
                            scope=scope,
                            level_epoch_id=prior.epoch_id,
                            issued_at=_instant(2),
                            writer_id="w",
                            arbitration_rank=0,
                        )
                    )
                ],
                scope=scope,
                epoch=record.new_epoch,
            )
        )
        is KsaLevel.GREEN
    )


def test_resume_refuses_wrong_scope_and_non_operator() -> None:
    live = _stream_scope(account="live-1")
    demo = _stream_scope(account="demo-1")
    prior = _ok(mint_level_epoch(epoch_id="e1", scope=live, opened_at=_instant(1)))
    wrong_scope = resume(
        scope=demo,
        authority="operator",
        issued_at=_instant(2),
        prior_epoch=prior,
        new_epoch_id="e2",
        fresh_state_validated=True,
    )
    assert is_refusal(wrong_scope)
    assert wrong_scope.context["field"] == "scope"

    non_op = resume(
        scope=live,
        authority="protection_authority",
        issued_at=_instant(2),
        prior_epoch=prior,
        new_epoch_id="e2",
        fresh_state_validated=True,
    )
    assert is_refusal(non_op)
    assert non_op.context["field"] == "authority"


def test_resume_requires_fresh_state_validation() -> None:
    scope = KsaEnforcementScope.global_scope()
    prior = _ok(mint_level_epoch(epoch_id="e1", scope=scope, opened_at=_instant(1)))
    refused = resume(
        scope=scope,
        authority="operator",
        issued_at=_instant(2),
        prior_epoch=prior,
        new_epoch_id="e2",
        fresh_state_validated=False,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "fresh_state_validated"


def test_never_auto_deescalate_on_reconnect_or_quiet() -> None:
    assert "reconnect" in AUTO_DEESCALATION_EVENTS
    assert "reconciliation" in AUTO_DEESCALATION_EVENTS
    assert "restart" in AUTO_DEESCALATION_EVENTS
    assert "absence_of_triggers" in AUTO_DEESCALATION_EVENTS
    scope = KsaEnforcementScope.global_scope()
    prior = _ok(mint_level_epoch(epoch_id="e1", scope=scope, opened_at=_instant(1)))
    for event in ("reconnect", "reconciliation", "restart", "absence_of_triggers"):
        # Non-operator authorities are refused; auto events are never resume issuers.
        refused = resume(
            scope=scope,
            authority=event,
            issued_at=_instant(2),
            prior_epoch=prior,
            new_epoch_id="e2",
            fresh_state_validated=True,
        )
        assert is_refusal(refused)


def test_live_connectivity_does_not_block_paired_demo_unless_global() -> None:
    live_venue = _venue("broker-live")
    demo_venue = _venue("broker-demo")
    live_scope = _ok(KsaEnforcementScope.stream(live_venue, "acct-live"))
    assert (
        stream_blocked_by_escalation(
            live_scope,
            target_venue_id=demo_venue,
            target_account_id="acct-demo",
            target_is_paired_demo=True,
        )
        is False
    )
    assert (
        stream_blocked_by_escalation(
            live_scope,
            target_venue_id=live_venue,
            target_account_id="acct-live",
            target_is_paired_demo=False,
        )
        is True
    )
    global_scope = KsaEnforcementScope.global_scope()
    assert (
        stream_blocked_by_escalation(
            global_scope,
            target_venue_id=demo_venue,
            target_account_id="acct-demo",
            target_is_paired_demo=True,
        )
        is True
    )


# --- effect matrix ------------------------------------------------------------


def test_ftr07_supplies_no_matrix_default_values() -> None:
    assert matrix_supplies_no_default_values() is True
    blank = _ok(compile_effect_matrix(value_status=VALUE_STATUS_BLANK))
    assert blank.cells == ()
    assert blank.blocks_role_live is True
    assert blank.blocks_soak is True
    assert blank.blank_effect == EFFECT_MATRIX_BLANK_EFFECTS
    assert KSA_EFFECT_MATRIX_REGISTRY_KEY == "ksa_effect_matrix"


def test_blank_and_provisional_cells_block_live_and_soak() -> None:
    provisional = _ok(
        compile_effect_matrix(
            value_status="provisional-evidence",
            cells=[
                {
                    "trigger_class": "connectivity",
                    "level": "ORANGE",
                    "effect": "suspend_new",
                    "subject_scope": "account",
                    "satisfaction_predicate": "never-auto",
                    "value_status": "provisional-evidence",
                }
            ],
        )
    )
    assert matrix_blocks_role_live(provisional) is True
    assert matrix_blocks_soak(provisional) is True
    assert cell_blocks_role_live(provisional.cells[0]) is True
    assert cell_blocks_soak("blank") is True


def test_compile_cell_declares_ct30_effect_scope_predicate_and_disposition() -> None:
    cell = _ok(
        compile_ksa_effect_cell(
            trigger_class="scheduled_news",
            level="RED",
            effect="flatten",
            subject_scope="global",
            satisfaction_predicate="scope-flat-at-reconciled-verdict",
            paper_disposition="blocks-paper",
            value_status="ratified",
        )
    )
    assert cell.effect is ControlActionKind.FLATTEN
    assert cell.subject_scope is SubjectScope.GLOBAL
    assert cell.satisfaction_predicate is SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT
    assert cell.paper_disposition is PaperDisposition.BLOCKS_PAPER
    assert cell.value_status == "ratified"
    assert set(KSA_EFFECT_KINDS) == {
        ControlActionKind.SUSPEND_NEW,
        ControlActionKind.DRAIN,
        ControlActionKind.FLATTEN,
    }


def test_compile_refuses_resume_effect_and_weakened_predicates() -> None:
    resume_effect = compile_ksa_effect_cell(
        trigger_class="connectivity",
        level="YELLOW",
        effect="resume",
        subject_scope="account",
        satisfaction_predicate="never-auto",
        value_status="ratified",
    )
    assert is_refusal(resume_effect)

    weakened = compile_ksa_effect_cell(
        trigger_class="connectivity",
        level="ORANGE",
        effect="drain",
        subject_scope="account",
        satisfaction_predicate="scope-flat-at-reconciled-verdict",
        value_status="ratified",
    )
    assert is_refusal(weakened)
    assert weakened.context["field"] == "satisfaction_predicate"


def test_compile_refuses_blank_cell_and_blank_matrix_with_cells() -> None:
    blank_cell = compile_ksa_effect_cell(
        trigger_class="connectivity",
        level="YELLOW",
        effect="suspend_new",
        subject_scope="account",
        satisfaction_predicate="never-auto",
        value_status="blank",
    )
    assert is_refusal(blank_cell)

    blank_with_cells = compile_effect_matrix(
        value_status="blank",
        cells=[
            {
                "trigger_class": "connectivity",
                "level": "YELLOW",
                "effect": "suspend_new",
                "subject_scope": "account",
                "satisfaction_predicate": "never-auto",
            }
        ],
    )
    assert is_refusal(blank_with_cells)


def test_ratified_matrix_requires_cells() -> None:
    refused = compile_effect_matrix(value_status="ratified", cells=())
    assert is_refusal(refused)
    compiled = _ok(
        compile_effect_matrix(
            value_status="ratified",
            cells=[
                {
                    "trigger_class": "black_swan",
                    "level": "BLACK",
                    "effect": "flatten",
                    "subject_scope": "global",
                    "satisfaction_predicate": "scope-flat-at-reconciled-verdict",
                }
            ],
        )
    )
    assert isinstance(compiled, CompiledEffectMatrix)
    assert matrix_blocks_role_live(compiled) is False
    assert matrix_blocks_soak(compiled) is False


def test_disposition_mismatch_refused() -> None:
    refused = compile_ksa_effect_cell(
        trigger_class="scheduled_news",
        level="ORANGE",
        effect="suspend_new",
        subject_scope="instrument",
        satisfaction_predicate="never-auto",
        paper_disposition="routes-to-paper",
        value_status="ratified",
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "paper_disposition"
