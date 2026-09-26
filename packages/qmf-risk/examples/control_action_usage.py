"""Reference usage — CT-30 control actions, kill switch vs kill line, arbitration.

Executable::

    python packages/qmf-risk/examples/control_action_usage.py

Shows exit-preservation, the bounded action vocabulary, standing-intent
journal-before-dispatch, kill-switch vs kill-line named apart, flatten authority,
and SCN-0010 same-tick compose (suspend_new + flatten both execute).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Instant,
    RefusalCategory,
    Result,
    VenueId,
    is_ok,
    is_refusal,
    unpersistable,
)
from qmf.risk.binding import PositionModel
from qmf.risk.control_action import (
    AuthorityKind,
    CommandStreamKey,
    ControlActionStream,
    EnforcementScope,
    KillLine,
    KillSwitch,
    PendingControlAction,
    ReconciliationVerdict,
    RiskReducingAct,
    SubjectScope,
    arbitrate_same_tick,
    check_exit_preservation,
    check_flatten_authority,
    fold_standing_intents,
    journal_before_dispatch,
    mint_kill_line_breach,
    mint_kill_switch_action,
    reject_blanket_command_pipe_block,
    resolve_subject_scope,
)
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable
from qmf.risk.exit_record import CloseReason

T = TypeVar("T")


def _unwrap(result: Result[T], message: str) -> T:
    if is_ok(result):
        return result.value
    raise RuntimeError(message)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _instant(ns: int) -> Instant:
    return _unwrap(Instant.try_create(ns), "instant mint failed")


def _stream() -> CommandStreamKey:
    venue = _unwrap(VenueId.try_create("ctrader"), "venue mint failed")
    return _unwrap(CommandStreamKey.try_create(venue, "acct-live-1"), "stream mint failed")


def _rank_table() -> ControlRankTable:
    rows = [
        _unwrap(ControlRankRow.try_create(ControlActionKind.SUSPEND_NEW, 0), "rank row"),
        _unwrap(ControlRankRow.try_create(ControlActionKind.FLATTEN, 1), "rank row"),
        _unwrap(ControlRankRow.try_create(ControlActionKind.DRAIN, 2), "rank row"),
        _unwrap(ControlRankRow.try_create(ControlActionKind.RESUME, 3), "rank row"),
    ]
    return _unwrap(ControlRankTable.try_create(rows), "rank table")


def main() -> None:
    stream = _stream()
    table = _rank_table()

    # Exit-preservation: blocking a risk-reducing act is refused; entries may block.
    blocked = check_exit_preservation(blocked_act=RiskReducingAct.CLOSE_ALL)
    if not is_refusal(blocked):
        raise RuntimeError("close_all must be exit-preserved")
    _require(
        blocked.category is RefusalCategory.POLICY_REJECTION,
        "exit-preservation is a policy rejection",
    )
    print("exit-preservation: close_all block refused (policy rejection)")
    _require(is_ok(check_exit_preservation(blocked_act="entry")), "entries may be blocked")
    print("exit-preservation: entry block allowed")

    pipe = reject_blanket_command_pipe_block("block_all_commands")
    _require(is_refusal(pipe), "blanket pipe-block kind must be refused")
    print("no blanket command-pipe block kind may be minted")

    # Kill switch (global) vs kill line (per-Book floor) — named apart.
    kill_switch = _unwrap(
        KillSwitch.try_create("ksa-1", stream, 2, ControlActionKind.SUSPEND_NEW, "black-swan"),
        "kill switch mint failed",
    )
    kill_line = _unwrap(
        KillLine.try_create("book-policy-1", "binding-epoch-1", stream, "capital-floor"),
        "kill line mint failed",
    )
    _require(
        kill_switch.fp1_identity()["class"] != kill_line.fp1_identity()["class"],
        "kill switch and kill line must stay distinct classes",
    )
    print(
        "kill_switch class / kill_line class: "
        f"{kill_switch.fp1_identity()['class']} / {kill_line.fp1_identity()['class']}"
    )

    ks_action = _unwrap(
        mint_kill_switch_action(kill_switch, rank=0, issued_at=_instant(1_000)),
        "kill-switch action mint failed",
    )
    kl_action = _unwrap(
        mint_kill_line_breach(kill_line, rank=1, issued_at=_instant(1_000)),
        "kill-line action mint failed",
    )
    _require(
        ks_action.authority_kind is AuthorityKind.PROTECTION_AUTHORITY,
        "kill switch issues as protection_authority",
    )
    _require(ks_action.subject_scope is SubjectScope.GLOBAL, "kill switch is global")
    kl_close = kl_action.close_reason_ref
    if kl_close is None:
        raise RuntimeError("kill-line flatten carries a close reason")
    _require(kl_close is CloseReason.KILL_LINE_FLAT, "kill-line flat maps to kill_line_flat")
    _require(
        kl_close is not CloseReason.PROTECTION_FORCED_FLAT,
        "kill_line_flat is minted apart from protection_forced_flat",
    )
    print(f"close reasons distinct: {kl_close.value} != {CloseReason.PROTECTION_FORCED_FLAT.value}")

    # Flatten authority: adapter cannot flatten; operator always can.
    _require(
        is_refusal(check_flatten_authority(AuthorityKind.ADAPTER_SELF)),
        "adapter_self must not flatten",
    )
    _require(is_ok(check_flatten_authority(AuthorityKind.OPERATOR)), "operator may flatten")
    print("flatten authority: operator ok; adapter_self refused")

    # Scope resolution refuses netting-indistinguishable widen.
    scope_ok = resolve_subject_scope(
        SubjectScope.BINDING,
        scope_ref="binding-epoch-1",
        stream=stream,
        position_model=PositionModel.HEDGING,
    )
    _require(is_ok(scope_ok), "hedging binding scope must resolve")
    netting_refuse = resolve_subject_scope(
        SubjectScope.BOOK,
        scope_ref="book-1",
        stream=stream,
        position_model=PositionModel.NETTING,
        netting_indistinguishable_from_wider=True,
    )
    _require(is_refusal(netting_refuse), "netting-indistinguishable must refuse")
    print("scope resolution: netting-indistinguishable refused (never widened)")

    # Journal before dispatch — storage failure blocks.
    blocked_dispatch = journal_before_dispatch(
        kl_action, journal_result=unpersistable("journal sink full")
    )
    if not is_refusal(blocked_dispatch):
        raise RuntimeError("storage failure must block dispatch")
    _require(
        blocked_dispatch.category is RefusalCategory.STORAGE_FAILURE,
        "storage failure must block dispatch",
    )
    journaled = _unwrap(
        journal_before_dispatch(kl_action, journal_result=True),
        "journal before dispatch failed",
    )
    print("journal-before-dispatch: storage failure blocks; success proceeds")

    action_stream = ControlActionStream()
    _unwrap(action_stream.mint(ks_action), "stream mint suspend failed")
    _unwrap(action_stream.mint(journaled), "stream mint flatten failed")
    folds = _unwrap(
        fold_standing_intents(
            action_stream,
            stream,
            verdict=ReconciliationVerdict.UNKNOWN,
        ),
        "standing-intent fold failed",
    )
    _require(
        any(f.status.value == "held-alarm" for f in folds),
        "unknown verdict must hold flatten open without dispatching",
    )
    print("standing intent: unknown verdict holds flatten open (held-alarm)")

    # Same-tick compose: suspend_new + flatten both execute (SCN-0010).
    enforcement = EnforcementScope(
        subject_scope=SubjectScope.BINDING,
        scope_ref="binding-epoch-1",
        stream=stream,
    )
    pending_ks = _unwrap(
        PendingControlAction.try_create(ks_action, enforcement),
        "pending kill-switch failed",
    )
    pending_kl = _unwrap(
        PendingControlAction.try_create(journaled, enforcement),
        "pending kill-line failed",
    )
    outcome = _unwrap(
        arbitrate_same_tick(
            [pending_ks, pending_kl],
            table,
            stream=stream,
            arbitration_seed="scn-0010",
        ),
        "arbitration failed",
    )
    kinds = {p.record.action_kind.value for p in outcome.emit}
    _require(kinds == {"suspend_new", "flatten"}, "compose must emit both")
    _require(len(outcome.suppressed) == 0, "compose must suppress none")
    print(f"same-tick compose: emit={sorted(kinds)}; suppressed={len(outcome.suppressed)}")
    print("resume is operator-only; kill-line stand-down clears only by human resume")


if __name__ == "__main__":
    main()
