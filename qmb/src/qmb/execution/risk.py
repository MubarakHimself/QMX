"""CT-23 inbound and CT-29 exits consumed at the QMB composition root.

QMB does not redefine AD-29..41. Sizing, R-freeze, and exits consume qmf-risk
contracts: CT-23 inbound intent, CT-29 exits, and the AD-40 full-loss price
required before any open (B-3, B-6, DEC-0160, DEC-0158).
"""

from __future__ import annotations

from qmf.core.fingerprint import World
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.door import (
    CT23_ACTIVE_FORMAT_VERSION,
    AdmittedEntry,
    EntryIntent,
    ExitIntent,
    admit_entry_intent,
    evaluate_exit_intent,
    refuse_no_full_loss_price,
)
from qmf.risk.exit_record import (
    ExitRecord,
    ExitResultLabel,
    mint_exit_record,
)

from qmb._refuse import invalid, policy
from qmb.config.replay import ReplayBinding

__all__ = [
    "admit_open",
    "evaluate_exit",
    "mint_replay_exit",
    "require_full_loss_before_open",
]


def require_full_loss_before_open(declared_full_loss_price: object) -> Result[object]:
    """AD-40: no declared full-loss price, no open (DEC-0154)."""
    if declared_full_loss_price is None:
        return refuse_no_full_loss_price()
    return Ok(declared_full_loss_price)


def admit_open(
    binding: object,
    *,
    intent: object,
    entry_price: object,
    exit_logic_ref: object,
    module: object,
    book_resolved_requested_r: object,
    ct23_format_version: object = CT23_ACTIVE_FORMAT_VERSION,
    has_open_position: bool = False,
) -> Result[AdmittedEntry]:
    """Admit an entry through CT-23 against the run's ``world = replay`` binding.

    The Book derives the declared full-loss price at the door. No price, no
    original_risk_distance, no admission. Ports execute the authorized intent,
    never a bot-sized order.
    """
    bound = _require_replay_binding(binding)
    if is_refusal(bound):
        return bound
    if not isinstance(intent, EntryIntent):
        return invalid(
            "intent",
            "inbound execution is a CT-23 entry intent, never a bot-sized order",
            given=repr(type(intent).__name__),
        )
    admitted = admit_entry_intent(
        intent=intent,
        entry_price=entry_price,
        exit_logic_ref=exit_logic_ref,
        module=module,
        book_resolved_requested_r=book_resolved_requested_r,
        ct23_format_version=ct23_format_version,
        has_open_position=has_open_position,
    )
    if is_refusal(admitted):
        return admitted
    checked = require_full_loss_before_open(admitted.value.declared_full_loss_price)
    if is_refusal(checked):
        return checked
    return admitted


def evaluate_exit(binding: object, exit_intent: object) -> Result[ExitIntent]:
    """Evaluate a CT-23 exit intent against the run's ``world = replay`` binding.

    Exits are risk-monotonic by construction (close_full | tighten_protective_stop).
    """
    bound = _require_replay_binding(binding)
    if is_refusal(bound):
        return bound
    return evaluate_exit_intent(exit_intent)


def mint_replay_exit(
    binding: object,
    *,
    virtual_position_ref: object,
    opening_bot_id: object,
    original_risk_distance: object,
    original_risk_amount: object,
    fill_references: object,
    realized_pnl: object,
    cost_components: object,
    close_reason: object,
    mechanism: object,
    outcome: object,
    closing_authority: object,
    close_reason_mapping_version: object,
    result_label: object,
    loss_predicate_format_version: object,
    recorded_at: object,
    arbitration_record_ref: object = None,
    venue_observation_ref: object = None,
) -> Result[ExitRecord]:
    """Mint exactly one CT-29 exit record against the run's replay binding epoch."""
    bound = _require_replay_binding(binding)
    if is_refusal(bound):
        return bound
    label = result_label
    if not isinstance(label, ExitResultLabel):
        return invalid(
            "result_label",
            "the exit record carries ExitResultLabel parts including the account-binding role",
            given=repr(type(result_label).__name__),
        )
    if label.world is not World.REPLAY:
        return policy(
            "world",
            "a CT-29 exit of a replay run carries world=replay on its result label; "
            "replay and live evidence are incomparable by binding",
            given=label.world.value,
        )
    return mint_exit_record(
        virtual_position_ref=virtual_position_ref,
        opening_bot_id=opening_bot_id,
        original_risk_distance=original_risk_distance,
        original_risk_amount=original_risk_amount,
        fill_references=fill_references,
        realized_pnl=realized_pnl,
        cost_components=cost_components,
        close_reason=close_reason,
        mechanism=mechanism,
        outcome=outcome,
        closing_authority=closing_authority,
        close_reason_mapping_version=close_reason_mapping_version,
        result_label=label,
        loss_predicate_format_version=loss_predicate_format_version,
        binding_epoch=bound.value.fingerprint,
        recorded_at=recorded_at,
        arbitration_record_ref=arbitration_record_ref,
        venue_observation_ref=venue_observation_ref,
    )


def _require_replay_binding(value: object) -> Result[ReplayBinding]:
    if not isinstance(value, ReplayBinding):
        return invalid(
            "binding",
            "sizing, R-freeze, and exits consume the run's minted world=replay binding",
            given=repr(type(value).__name__),
        )
    if value.record.world is not World.REPLAY:
        return policy(
            "world",
            "QMB wires CT-23 and CT-29 only on a world=replay binding",
            given=value.record.world.value,
        )
    return Ok(value)
