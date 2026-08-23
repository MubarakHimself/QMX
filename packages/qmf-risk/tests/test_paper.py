"""Story 10.5 — paper as a dated binding-epoch change (CT-24).

Verifies the CT-24 Book-mode / binding-transition stream on qmf-core nouns: Book modes
are exactly LIVE|PAPER with a mode-field write of a seat/binding-state word refused, the
flip is a dated transition appended to the stream and current mode is a read-time fold
never a stored field (AC1); routing is separated from binding — a single per-intent
execution target resolved from (Book mode, seat state, active-control set) (AC2); exactly
one active paper target per binding, no resolvable target an unavailable-dependency
refusal (AC3); every trigger kind declares a mandatory disposition, blocks-paper blocking
paper too and recording never trading (AC4); paper money is frozen evidence with
operator-signed resets and no money-boundary crossing (AC5); and the return-to-live
asymmetry — automatic only when clocked and mechanical, real money needs a signature, and
paper performance never authorizes a return (AC6) (CT-24; DEC-0149).
"""

from __future__ import annotations

from qmf.core import (
    AccountRole,
    Fingerprint,
    Instant,
    Money,
    RefusalCategory,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.risk.binding import BookInstanceId
from qmf.risk.paper import (
    ActiveControl,
    BindingTransitionRecord,
    BindingTransitionStream,
    BookMode,
    ClearingCause,
    ExecutionResolution,
    ExecutionTarget,
    ModeFoldResult,
    PaperEpochLog,
    PaperEpochRecord,
    PaperTargetLog,
    PaperTargetRecord,
    ReturnMechanism,
    ReturnToLiveOutcome,
    RoutingOutcome,
    SeatState,
    TreasuryBoundaryKind,
    TriggerDisposition,
    TriggerKind,
    authorize_return_to_live,
    mint_return_to_live_transition,
    reject_paper_pnl_to_treasury,
    reset_paper_epoch,
    resolve_execution_target,
    validate_book_mode,
)

_VENUE = VenueId(value="venue-ctrader")


# --- builders ----------------------------------------------------------------


def _instant(value_ns: int = 1_700_000_000_000_000_000) -> Instant:
    result = Instant.try_create(value_ns)
    assert is_ok(result)
    return result.value


def _fp(seed: str) -> Fingerprint:
    result = fingerprint({"seed": seed})
    assert is_ok(result)
    return result.value


def _book_instance_id(value: str = "book-inst-1") -> BookInstanceId:
    result = BookInstanceId.try_create(value)
    assert is_ok(result)
    return result.value


def _live_target(account: str = "acct-live") -> ExecutionTarget:
    result = ExecutionTarget.try_create(AccountRole.LIVE, _VENUE, account)
    assert is_ok(result)
    return result.value


def _paper_target(
    account: str = "acct-demo", role: AccountRole = AccountRole.PAPER_VALIDATION
) -> ExecutionTarget:
    result = ExecutionTarget.try_create(role, _VENUE, account)
    assert is_ok(result)
    return result.value


def _trigger(
    disposition: TriggerDisposition = TriggerDisposition.ROUTES_TO_PAPER,
    name: str = "operator-paper-flip",
) -> TriggerKind:
    result = TriggerKind.try_create(name, disposition)
    assert is_ok(result)
    return result.value


def _control(disposition: TriggerDisposition, control_id: str = "control-1") -> ActiveControl:
    result = ActiveControl.try_create(control_id, disposition)
    assert is_ok(result)
    return result.value


def _money(value: int = 5_000_00, currency: str = "USD", scale: int = 2) -> Money:
    result = Money.try_create(value, currency, scale)
    assert is_ok(result)
    return result.value


def _paper_transition(
    *,
    book_instance_id: object = None,
    binding_ref: Fingerprint | None = None,
    target: ExecutionTarget | None = None,
    epoch: Fingerprint | None = None,
    instant: Instant | None = None,
    trigger: TriggerKind | None = None,
) -> BindingTransitionRecord:
    result = BindingTransitionRecord.try_create(
        book_instance_id or _book_instance_id(),
        binding_ref or _fp("binding-epoch-1"),
        BookMode.PAPER,
        instant or _instant(),
        trigger or _trigger(),
        paper_target_ref=target or _paper_target(),
        paper_epoch_ref=epoch or _fp("paper-epoch-1"),
    )
    assert is_ok(result)
    return result.value


def _live_transition(
    *,
    book_instance_id: object = None,
    instant: Instant | None = None,
    operator_signature: object = None,
) -> BindingTransitionRecord:
    result = BindingTransitionRecord.try_create(
        book_instance_id or _book_instance_id(),
        _fp("binding-epoch-live"),
        BookMode.LIVE,
        instant or _instant(),
        _trigger(TriggerDisposition.ROUTES_TO_PAPER, "first-live-entry"),
        operator_signature=operator_signature,
    )
    assert is_ok(result)
    return result.value


def _first_epoch(
    *, book_instance_id: object = None, binding_ref: Fingerprint | None = None
) -> PaperEpochRecord:
    result = PaperEpochRecord.try_create(
        book_instance_id or _book_instance_id(),
        binding_ref or _fp("binding-epoch-1"),
        _money(),
        "operator-mubarak",
        _instant(),
    )
    assert is_ok(result)
    return result.value


# --- AC1: LIVE|PAPER only; the mode-field vocabulary guard --------------------


def test_book_mode_space_is_exactly_live_and_paper() -> None:
    assert {m.value for m in BookMode} == {"LIVE", "PAPER"}


def test_validate_book_mode_accepts_member_and_exact_value() -> None:
    ok_member = validate_book_mode(BookMode.PAPER)
    assert is_ok(ok_member)
    assert ok_member.value is BookMode.PAPER
    ok_str = validate_book_mode("LIVE")
    assert is_ok(ok_str)
    assert ok_str.value is BookMode.LIVE


def test_validate_book_mode_refuses_seat_state_words() -> None:
    for word in ("active", "benched"):
        result = validate_book_mode(word)
        assert is_refusal(result)
        assert result.category is RefusalCategory.INVALID_INPUT


def test_validate_book_mode_refuses_binding_state_words() -> None:
    for word in ("live", "paper", "stood-down"):
        result = validate_book_mode(word)
        assert is_refusal(result)
        assert result.category is RefusalCategory.INVALID_INPUT


def test_validate_book_mode_refuses_unknown_and_non_string() -> None:
    unknown = validate_book_mode("HALTED")
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.INVALID_INPUT
    non_string = validate_book_mode(7)
    assert is_refusal(non_string)
    assert non_string.category is RefusalCategory.INVALID_INPUT


# --- trigger kinds and active controls ---------------------------------------


def test_trigger_kind_carries_a_mandatory_disposition() -> None:
    trigger = _trigger(TriggerDisposition.BLOCKS_PAPER, "kill-switch")
    assert trigger.disposition is TriggerDisposition.BLOCKS_PAPER
    assert trigger.fp1_identity()["disposition"] == "blocks-paper"


def test_trigger_kind_refuses_blank_name_and_missing_disposition() -> None:
    blank = TriggerKind.try_create("  ", TriggerDisposition.ROUTES_TO_PAPER)
    assert is_refusal(blank)
    assert blank.category is RefusalCategory.INVALID_INPUT
    missing = TriggerKind.try_create("x", "not-a-disposition")
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.INVALID_INPUT


def test_active_control_refuses_blank_id_and_bad_disposition() -> None:
    blank = ActiveControl.try_create("", TriggerDisposition.BLOCKS_PAPER)
    assert is_refusal(blank)
    bad = ActiveControl.try_create("c", "nope")
    assert is_refusal(bad)


# --- execution targets -------------------------------------------------------


def test_execution_target_command_stream_and_identity() -> None:
    target = _live_target()
    assert target.command_stream() == (_VENUE, "acct-live")
    identity = target.fp1_identity()
    assert identity["role"] == "live"
    assert identity["account_id"] == "acct-live"


def test_execution_target_refuses_bad_parts() -> None:
    assert is_refusal(ExecutionTarget.try_create("not-a-role", _VENUE, "a"))
    assert is_refusal(ExecutionTarget.try_create(AccountRole.LIVE, "not-a-venue", "a"))
    assert is_refusal(ExecutionTarget.try_create(AccountRole.LIVE, _VENUE, "  "))


# --- AC1: the CT-24 transition record ----------------------------------------


def test_paper_transition_carries_target_epoch_and_disposition() -> None:
    record = _paper_transition()
    assert record.mode is BookMode.PAPER
    assert record.disposition is TriggerDisposition.ROUTES_TO_PAPER
    assert record.paper_target_ref is not None
    assert record.paper_epoch_ref is not None
    identity = record.fp1_identity()
    assert identity["mode"] == "PAPER"
    assert "paper_target_ref" in identity
    assert "paper_epoch_ref" in identity
    assert is_ok(record.fingerprint())


def test_paper_transition_requires_target_and_epoch() -> None:
    no_target = BindingTransitionRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        BookMode.PAPER,
        _instant(),
        _trigger(),
        paper_epoch_ref=_fp("e"),
    )
    assert is_refusal(no_target)
    assert no_target.category is RefusalCategory.INVALID_INPUT
    no_epoch = BindingTransitionRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        BookMode.PAPER,
        _instant(),
        _trigger(),
        paper_target_ref=_paper_target(),
    )
    assert is_refusal(no_epoch)
    assert no_epoch.category is RefusalCategory.INVALID_INPUT


def test_live_transition_omits_target_and_epoch() -> None:
    record = _live_transition()
    assert record.mode is BookMode.LIVE
    assert record.paper_target_ref is None
    assert record.paper_epoch_ref is None
    with_target = BindingTransitionRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        BookMode.LIVE,
        _instant(),
        _trigger(),
        paper_target_ref=_paper_target(),
    )
    assert is_refusal(with_target)
    with_epoch = BindingTransitionRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        BookMode.LIVE,
        _instant(),
        _trigger(),
        paper_epoch_ref=_fp("e"),
    )
    assert is_refusal(with_epoch)


def test_transition_refuses_seat_word_in_mode_field() -> None:
    result = BindingTransitionRecord.try_create(
        _book_instance_id(), _fp("b"), "benched", _instant(), _trigger()
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_transition_refuses_malformed_parts() -> None:
    assert is_refusal(
        BindingTransitionRecord.try_create("nope", _fp("b"), BookMode.LIVE, _instant(), _trigger())
    )
    assert is_refusal(
        BindingTransitionRecord.try_create(
            _book_instance_id(), "nope", BookMode.LIVE, _instant(), _trigger()
        )
    )
    assert is_refusal(
        BindingTransitionRecord.try_create(
            _book_instance_id(), _fp("b"), BookMode.LIVE, "nope", _trigger()
        )
    )
    assert is_refusal(
        BindingTransitionRecord.try_create(
            _book_instance_id(), _fp("b"), BookMode.LIVE, _instant(), "nope"
        )
    )


def test_transition_refuses_bad_optional_fields() -> None:
    bad_target = BindingTransitionRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        BookMode.PAPER,
        _instant(),
        _trigger(),
        paper_target_ref="nope",
        paper_epoch_ref=_fp("e"),
    )
    assert is_refusal(bad_target)
    live_role_target = BindingTransitionRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        BookMode.PAPER,
        _instant(),
        _trigger(),
        paper_target_ref=_live_target(),
        paper_epoch_ref=_fp("e"),
    )
    assert is_refusal(live_role_target)
    bad_epoch = BindingTransitionRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        BookMode.PAPER,
        _instant(),
        _trigger(),
        paper_target_ref=_paper_target(),
        paper_epoch_ref="nope",
    )
    assert is_refusal(bad_epoch)
    blank_sig = BindingTransitionRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        BookMode.LIVE,
        _instant(),
        _trigger(),
        operator_signature="  ",
    )
    assert is_refusal(blank_sig)


def test_live_transition_may_carry_operator_signature() -> None:
    record = _live_transition(operator_signature="operator-mubarak")
    assert record.operator_signature == "operator-mubarak"
    assert record.fp1_identity()["operator_signature"] == "operator-mubarak"


# --- AC1: the read-time mode fold --------------------------------------------


def test_current_mode_is_a_fold_never_a_stored_field() -> None:
    stream = BindingTransitionStream()
    book = _book_instance_id()
    # An empty stream folds to the most-restrictive PAPER, fail-closed.
    empty = stream.current_mode(book)
    assert isinstance(empty, ModeFoldResult)
    assert empty.mode is BookMode.PAPER
    assert empty.fail_closed is True
    # Establish LIVE, then the fold reports LIVE cleanly.
    assert is_ok(stream.mint(_live_transition(book_instance_id=book, instant=_instant(1_000))))
    live = stream.current_mode(book)
    assert live.mode is BookMode.LIVE
    assert live.fail_closed is False
    # Append a later PAPER flip; the fold now reports PAPER without any field mutation.
    assert is_ok(stream.mint(_paper_transition(book_instance_id=book, instant=_instant(2_000))))
    paper = stream.current_mode(book)
    assert paper.mode is BookMode.PAPER
    assert paper.fail_closed is False


def test_current_mode_honours_the_knowledge_time_bound() -> None:
    stream = BindingTransitionStream()
    book = _book_instance_id()
    assert is_ok(stream.mint(_live_transition(book_instance_id=book, instant=_instant(1_000))))
    assert is_ok(stream.mint(_paper_transition(book_instance_id=book, instant=_instant(5_000))))
    # As-of before the PAPER flip: still LIVE.
    before = stream.current_mode(book, as_of=_instant(3_000))
    assert before.mode is BookMode.LIVE
    # As-of after the PAPER flip: PAPER.
    after = stream.current_mode(book, as_of=_instant(9_000))
    assert after.mode is BookMode.PAPER


def test_current_mode_equal_instant_tie_folds_to_most_restrictive() -> None:
    stream = BindingTransitionStream()
    book = _book_instance_id()
    # Two transitions at the same instant with differing modes.
    assert is_ok(stream.mint(_live_transition(book_instance_id=book, instant=_instant(4_000))))
    paper_same_instant = BindingTransitionRecord.try_create(
        book,
        _fp("binding-epoch-2"),
        BookMode.PAPER,
        _instant(4_000),
        _trigger(name="second-writer"),
        paper_target_ref=_paper_target(),
        paper_epoch_ref=_fp("paper-epoch-1"),
    )
    assert is_ok(paper_same_instant)
    assert is_ok(stream.mint(paper_same_instant.value))
    tie = stream.current_mode(book)
    assert tie.mode is BookMode.PAPER
    assert tie.fail_closed is True
    assert tie.data_quality_reason is not None


def test_current_mode_fails_closed_on_bad_key_or_bound() -> None:
    stream = BindingTransitionStream()
    bad_key = stream.current_mode("not-a-book-instance-id")
    assert bad_key.mode is BookMode.PAPER
    assert bad_key.fail_closed is True
    book = _book_instance_id()
    assert is_ok(stream.mint(_live_transition(book_instance_id=book, instant=_instant(1_000))))
    bad_bound = stream.current_mode(book, as_of="not-an-instant")
    assert bad_bound.mode is BookMode.PAPER
    assert bad_bound.fail_closed is True


def test_stream_mint_refuses_non_record_and_duplicate() -> None:
    stream = BindingTransitionStream()
    assert is_refusal(stream.mint("not-a-record"))
    book = _book_instance_id()
    record = _live_transition(book_instance_id=book, instant=_instant(1_000))
    assert is_ok(stream.mint(record))
    duplicate = stream.mint(record)
    assert is_refusal(duplicate)
    assert duplicate.category is RefusalCategory.INVALID_INPUT


def test_transitions_for_returns_the_book_stream() -> None:
    stream = BindingTransitionStream()
    book = _book_instance_id()
    assert stream.transitions_for(book) == ()
    assert stream.transitions_for("not-an-id") == ()
    record = _live_transition(book_instance_id=book, instant=_instant(1_000))
    assert is_ok(stream.mint(record))
    assert stream.transitions_for(book) == (record,)


# --- AC2 / AC4: routing separated from binding -------------------------------


def test_routing_defaults_to_live() -> None:
    result = resolve_execution_target(
        book_mode=BookMode.LIVE,
        seat_state=SeatState.ACTIVE,
        active_controls=[],
        live_target=_live_target(),
        paper_target=_paper_target(),
    )
    assert is_ok(result)
    resolution = result.value
    assert resolution.outcome is RoutingOutcome.ROUTED_LIVE
    assert resolution.execution_target is not None
    assert resolution.execution_target.role is AccountRole.LIVE
    assert resolution.is_recording_only() is False


def test_paper_mode_selects_the_single_paired_target() -> None:
    live = _live_target()
    paper = _paper_target()
    result = resolve_execution_target(
        book_mode=BookMode.PAPER,
        seat_state=SeatState.ACTIVE,
        active_controls=[],
        live_target=live,
        paper_target=paper,
    )
    assert is_ok(result)
    resolution = result.value
    assert resolution.outcome is RoutingOutcome.ROUTED_PAPER
    # Exactly one target, and it is the paired one — never also the live target.
    assert resolution.execution_target == paper
    assert resolution.execution_target != live


def test_benched_seat_routes_to_paper() -> None:
    result = resolve_execution_target(
        book_mode=BookMode.LIVE,
        seat_state=SeatState.BENCHED,
        active_controls=[],
        live_target=_live_target(),
        paper_target=_paper_target(),
    )
    assert is_ok(result)
    assert result.value.outcome is RoutingOutcome.ROUTED_PAPER


def test_routes_to_paper_control_routes_to_paper() -> None:
    result = resolve_execution_target(
        book_mode=BookMode.LIVE,
        seat_state=SeatState.ACTIVE,
        active_controls=[_control(TriggerDisposition.ROUTES_TO_PAPER, "kill-line-stand-down")],
        live_target=_live_target(),
        paper_target=_paper_target(),
    )
    assert is_ok(result)
    assert result.value.outcome is RoutingOutcome.ROUTED_PAPER


def test_blocks_paper_control_blocks_live_and_paper_alike() -> None:
    # Even in PAPER mode, a market-risk (blocks-paper) control blocks — recording only.
    result = resolve_execution_target(
        book_mode=BookMode.PAPER,
        seat_state=SeatState.ACTIVE,
        active_controls=[_control(TriggerDisposition.BLOCKS_PAPER, "news-window")],
        live_target=_live_target(),
        paper_target=_paper_target(),
    )
    assert is_ok(result)
    resolution = result.value
    assert resolution.outcome is RoutingOutcome.BLOCKED
    assert resolution.execution_target is None
    assert resolution.blocking_control_id == "news-window"
    assert resolution.is_recording_only() is True


def test_paper_routing_without_a_target_is_unavailable_dependency() -> None:
    paper_mode = resolve_execution_target(
        book_mode=BookMode.PAPER,
        seat_state=SeatState.ACTIVE,
        active_controls=[],
        live_target=_live_target(),
        paper_target=None,
    )
    assert is_refusal(paper_mode)
    assert paper_mode.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    benched = resolve_execution_target(
        book_mode=BookMode.LIVE,
        seat_state=SeatState.BENCHED,
        active_controls=[],
        live_target=_live_target(),
        paper_target=None,
    )
    assert is_refusal(benched)
    assert benched.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_resolution_identity_carries_the_outcome() -> None:
    routed = resolve_execution_target(
        book_mode=BookMode.PAPER,
        seat_state=SeatState.ACTIVE,
        active_controls=[],
        live_target=_live_target(),
        paper_target=_paper_target(),
    )
    assert is_ok(routed)
    identity = routed.value.fp1_identity()
    assert identity["outcome"] == "routed-paper"
    assert "execution_target" in identity
    blocked = ExecutionResolution(
        outcome=RoutingOutcome.BLOCKED,
        routing_reason="blocked",
        blocking_control_id="c",
    )
    blocked_identity = blocked.fp1_identity()
    assert blocked_identity["blocking_control_id"] == "c"
    assert "execution_target" not in blocked_identity


def test_routing_refuses_malformed_inputs() -> None:
    assert is_refusal(
        resolve_execution_target(
            book_mode="live",  # lowercase binding word, not a Book mode
            seat_state=SeatState.ACTIVE,
            active_controls=[],
            live_target=_live_target(),
        )
    )
    assert is_refusal(
        resolve_execution_target(
            book_mode=BookMode.LIVE,
            seat_state="idle",
            active_controls=[],
            live_target=_live_target(),
        )
    )
    for bad_controls in ("not-iterable-string", {"a": 1}, [object()]):
        assert is_refusal(
            resolve_execution_target(
                book_mode=BookMode.LIVE,
                seat_state=SeatState.ACTIVE,
                active_controls=bad_controls,
                live_target=_live_target(),
            )
        )
    assert is_refusal(
        resolve_execution_target(
            book_mode=BookMode.LIVE,
            seat_state=SeatState.ACTIVE,
            active_controls=[],
            live_target="not-a-target",
        )
    )
    assert is_refusal(
        resolve_execution_target(
            book_mode=BookMode.LIVE,
            seat_state=SeatState.ACTIVE,
            active_controls=[],
            live_target=_paper_target(),  # a live target must carry the live role
        )
    )
    assert is_refusal(
        resolve_execution_target(
            book_mode=BookMode.LIVE,
            seat_state=SeatState.ACTIVE,
            active_controls=[],
            live_target=_live_target(),
            paper_target="not-a-target",
        )
    )
    assert is_refusal(
        resolve_execution_target(
            book_mode=BookMode.PAPER,
            seat_state=SeatState.ACTIVE,
            active_controls=[],
            live_target=_live_target(),
            paper_target=_live_target(),  # a paper target must not carry the live role
        )
    )


# --- AC3: one active paper-routing target per binding ------------------------


def test_paper_target_record_identity_and_bad_parts() -> None:
    record_result = PaperTargetRecord.try_create(_fp("binding-1"), _paper_target(), _instant())
    assert is_ok(record_result)
    record = record_result.value
    assert record.paper_target.role is AccountRole.PAPER_VALIDATION
    assert is_ok(record.fingerprint())
    assert is_refusal(PaperTargetRecord.try_create("nope", _paper_target(), _instant()))
    assert is_refusal(PaperTargetRecord.try_create(_fp("b"), "nope", _instant()))
    assert is_refusal(PaperTargetRecord.try_create(_fp("b"), _live_target(), _instant()))
    assert is_refusal(PaperTargetRecord.try_create(_fp("b"), _paper_target(), "nope"))
    assert is_refusal(
        PaperTargetRecord.try_create(_fp("b"), _paper_target(), _instant(), supersedes="nope")
    )


def test_paper_target_log_resolves_exactly_one_active_target() -> None:
    log = PaperTargetLog()
    binding = _fp("binding-1")
    first = PaperTargetRecord.try_create(binding, _paper_target("demo-a"), _instant(1_000))
    assert is_ok(first)
    minted = log.mint(first.value)
    assert is_ok(minted)
    active = log.resolve_active_target(binding)
    assert is_ok(active)
    assert active.value.account_id == "demo-a"


def test_paper_target_log_unavailable_without_a_target() -> None:
    log = PaperTargetLog()
    result = log.resolve_active_target(_fp("no-such-binding"))
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert is_refusal(log.resolve_active_target("nope"))


def test_paper_target_log_refuses_second_target_without_supersedes() -> None:
    log = PaperTargetLog()
    binding = _fp("binding-1")
    first = PaperTargetRecord.try_create(binding, _paper_target("demo-a"), _instant(1_000))
    assert is_ok(first)
    assert is_ok(log.mint(first.value))
    second = PaperTargetRecord.try_create(binding, _paper_target("demo-b"), _instant(2_000))
    assert is_ok(second)
    refused = log.mint(second.value)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_paper_target_log_repoints_by_superseding_record() -> None:
    log = PaperTargetLog()
    binding = _fp("binding-1")
    first = PaperTargetRecord.try_create(binding, _paper_target("demo-a"), _instant(1_000))
    assert is_ok(first)
    first_fp = log.mint(first.value)
    assert is_ok(first_fp)
    second = PaperTargetRecord.try_create(
        binding, _paper_target("demo-b"), _instant(2_000), supersedes=first_fp.value
    )
    assert is_ok(second)
    assert is_ok(log.mint(second.value))
    active = log.resolve_active_target(binding)
    assert is_ok(active)
    assert active.value.account_id == "demo-b"


def test_paper_target_log_supersedes_guards() -> None:
    log = PaperTargetLog()
    binding = _fp("binding-1")
    first = PaperTargetRecord.try_create(binding, _paper_target("demo-a"), _instant(1_000))
    assert is_ok(first)
    first_fp = log.mint(first.value)
    assert is_ok(first_fp)
    # Dangling supersedes.
    dangling = PaperTargetRecord.try_create(
        binding, _paper_target("demo-x"), _instant(2_000), supersedes=_fp("ghost")
    )
    assert is_ok(dangling)
    dangling_result = log.mint(dangling.value)
    assert is_refusal(dangling_result)
    assert dangling_result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # Supersedes another binding's record.
    other_binding = PaperTargetRecord.try_create(
        _fp("binding-2"), _paper_target("demo-c"), _instant(2_000), supersedes=first_fp.value
    )
    assert is_ok(other_binding)
    assert is_refusal(log.mint(other_binding.value))
    # A valid re-point, then a second supersedes of the now-superseded record.
    second = PaperTargetRecord.try_create(
        binding, _paper_target("demo-b"), _instant(3_000), supersedes=first_fp.value
    )
    assert is_ok(second)
    assert is_ok(log.mint(second.value))
    stale = PaperTargetRecord.try_create(
        binding, _paper_target("demo-d"), _instant(4_000), supersedes=first_fp.value
    )
    assert is_ok(stale)
    assert is_refusal(log.mint(stale.value))


def test_paper_target_log_refuses_non_record_and_duplicate() -> None:
    log = PaperTargetLog()
    assert is_refusal(log.mint("nope"))
    binding = _fp("binding-1")
    record = PaperTargetRecord.try_create(binding, _paper_target("demo-a"), _instant(1_000))
    assert is_ok(record)
    assert is_ok(log.mint(record.value))
    assert is_refusal(log.mint(record.value))


# --- AC5: paper money is frozen evidence -------------------------------------


def test_first_paper_epoch_freezes_a_positive_usd_balance() -> None:
    epoch = _first_epoch()
    assert epoch.starting_balance.currency == "USD"
    assert epoch.boundary_kind is None
    assert epoch.supersedes is None
    assert is_ok(epoch.fingerprint())
    identity = epoch.fp1_identity()
    assert "starting_balance" in identity
    assert "boundary_kind" not in identity


def test_paper_epoch_refuses_bad_balance_and_signature() -> None:
    non_usd = PaperEpochRecord.try_create(
        _book_instance_id(), _fp("b"), _money(currency="EUR"), "op", _instant()
    )
    assert is_refusal(non_usd)
    assert non_usd.category is RefusalCategory.POLICY_REJECTION
    non_positive = PaperEpochRecord.try_create(
        _book_instance_id(), _fp("b"), _money(0), "op", _instant()
    )
    assert is_refusal(non_positive)
    assert non_positive.category is RefusalCategory.INVALID_INPUT
    not_money = PaperEpochRecord.try_create(_book_instance_id(), _fp("b"), 100, "op", _instant())
    assert is_refusal(not_money)
    blank_sig = PaperEpochRecord.try_create(
        _book_instance_id(), _fp("b"), _money(), "  ", _instant()
    )
    assert is_refusal(blank_sig)


def test_paper_epoch_refuses_malformed_refs_and_boundary_kind() -> None:
    assert is_refusal(PaperEpochRecord.try_create("nope", _fp("b"), _money(), "op", _instant()))
    assert is_refusal(
        PaperEpochRecord.try_create(_book_instance_id(), "nope", _money(), "op", _instant())
    )
    assert is_refusal(
        PaperEpochRecord.try_create(_book_instance_id(), _fp("b"), _money(), "op", "nope")
    )
    bad_kind = PaperEpochRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        _money(),
        "op",
        _instant(),
        boundary_kind="not-a-kind",
        supersedes=_fp("prior"),
    )
    assert is_refusal(bad_kind)


def test_paper_epoch_reset_shape_is_enforced() -> None:
    # supersedes present but a non-reset boundary kind is refused.
    wrong_kind = PaperEpochRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        _money(),
        "op",
        _instant(),
        boundary_kind=TreasuryBoundaryKind.SWEEP,
        supersedes=_fp("prior"),
    )
    assert is_refusal(wrong_kind)
    # boundary kind present without a supersedes edge is refused (first epoch is not a reset).
    kind_without_edge = PaperEpochRecord.try_create(
        _book_instance_id(),
        _fp("b"),
        _money(),
        "op",
        _instant(),
        boundary_kind=TreasuryBoundaryKind.PAPER_EPOCH_RESET,
    )
    assert is_refusal(kind_without_edge)
    # bad supersedes type.
    bad_edge = PaperEpochRecord.try_create(
        _book_instance_id(), _fp("b"), _money(), "op", _instant(), supersedes="nope"
    )
    assert is_refusal(bad_edge)


def test_paper_epoch_log_reset_mints_a_new_epoch_and_preserves_history() -> None:
    log = PaperEpochLog()
    binding = _fp("binding-1")
    first = _first_epoch(binding_ref=binding)
    first_fp = log.mint(first)
    assert is_ok(first_fp)
    current = log.current_epoch(binding)
    assert is_ok(current)
    assert current.value.starting_balance.value == first.starting_balance.value
    reset = reset_paper_epoch(
        book_instance_id=_book_instance_id(),
        binding_ref=binding,
        prior_epoch_fingerprint=first_fp.value,
        fresh_balance=_money(10_000_00),
        operator_signature="operator-mubarak",
        dated_at=_instant(2_000),
    )
    assert is_ok(reset)
    assert reset.value.boundary_kind is TreasuryBoundaryKind.PAPER_EPOCH_RESET
    assert is_ok(log.mint(reset.value))
    now = log.current_epoch(binding)
    assert is_ok(now)
    assert now.value.starting_balance.value == 10_000_00
    # The running balance is never mutated — both epochs remain in the append-only log.
    assert len(log.epochs()) == 2


def test_paper_epoch_log_refuses_second_first_epoch() -> None:
    log = PaperEpochLog()
    binding = _fp("binding-1")
    assert is_ok(log.mint(_first_epoch(binding_ref=binding)))
    second_first = PaperEpochRecord.try_create(
        _book_instance_id(), binding, _money(9_00), "op", _instant(2_000)
    )
    assert is_ok(second_first)
    refused = log.mint(second_first.value)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT


def test_paper_epoch_log_reset_supersedes_guards() -> None:
    log = PaperEpochLog()
    binding = _fp("binding-1")
    first_fp = log.mint(_first_epoch(binding_ref=binding))
    assert is_ok(first_fp)
    dangling = reset_paper_epoch(
        book_instance_id=_book_instance_id(),
        binding_ref=binding,
        prior_epoch_fingerprint=_fp("ghost"),
        fresh_balance=_money(9_00),
        operator_signature="op",
        dated_at=_instant(2_000),
    )
    assert is_ok(dangling)
    dangling_result = log.mint(dangling.value)
    assert is_refusal(dangling_result)
    assert dangling_result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    other = reset_paper_epoch(
        book_instance_id=_book_instance_id(),
        binding_ref=_fp("binding-2"),
        prior_epoch_fingerprint=first_fp.value,
        fresh_balance=_money(9_00),
        operator_signature="op",
        dated_at=_instant(2_000),
    )
    assert is_ok(other)
    assert is_refusal(log.mint(other.value))
    # A valid reset, then a stale supersedes of the now-superseded first epoch.
    good = reset_paper_epoch(
        book_instance_id=_book_instance_id(),
        binding_ref=binding,
        prior_epoch_fingerprint=first_fp.value,
        fresh_balance=_money(9_00),
        operator_signature="op",
        dated_at=_instant(3_000),
    )
    assert is_ok(good)
    assert is_ok(log.mint(good.value))
    stale = reset_paper_epoch(
        book_instance_id=_book_instance_id(),
        binding_ref=binding,
        prior_epoch_fingerprint=first_fp.value,
        fresh_balance=_money(9_00),
        operator_signature="op",
        dated_at=_instant(4_000),
    )
    assert is_ok(stale)
    assert is_refusal(log.mint(stale.value))


def test_paper_epoch_log_current_and_mint_edge_cases() -> None:
    log = PaperEpochLog()
    assert is_refusal(log.mint("nope"))
    assert is_refusal(log.current_epoch("nope"))
    missing = log.current_epoch(_fp("no-binding"))
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    binding = _fp("binding-1")
    record = _first_epoch(binding_ref=binding)
    assert is_ok(log.mint(record))
    assert is_refusal(log.mint(record))  # duplicate fingerprint


def test_paper_pnl_never_crosses_the_money_boundary() -> None:
    refusal = reject_paper_pnl_to_treasury(_money(1_000_00))
    assert refusal.category is RefusalCategory.POLICY_REJECTION


# --- AC6: return to live -----------------------------------------------------


def test_clocked_mechanical_return_is_automatic_ct24_no_signature() -> None:
    result = authorize_return_to_live(clearing_cause=ClearingCause.CLOCKED_MECHANICAL)
    assert is_ok(result)
    outcome = result.value
    assert outcome.mechanism is ReturnMechanism.CT24_TRANSITION
    assert outcome.operator_signature is None
    assert outcome.is_resume is False


def test_clocked_mechanical_return_refuses_a_signature() -> None:
    result = authorize_return_to_live(
        clearing_cause=ClearingCause.CLOCKED_MECHANICAL, operator_signature="op"
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_first_live_entry_requires_an_operator_signature() -> None:
    signed = authorize_return_to_live(
        clearing_cause=ClearingCause.FIRST_LIVE_ENTRY, operator_signature="operator-mubarak"
    )
    assert is_ok(signed)
    assert signed.value.mechanism is ReturnMechanism.CT24_TRANSITION
    assert signed.value.operator_signature == "operator-mubarak"
    unsigned = authorize_return_to_live(clearing_cause=ClearingCause.FIRST_LIVE_ENTRY)
    assert is_refusal(unsigned)
    assert unsigned.category is RefusalCategory.POLICY_REJECTION


def test_control_stand_down_clears_only_by_operator_ct30_resume() -> None:
    result = authorize_return_to_live(
        clearing_cause=ClearingCause.CONTROL_STAND_DOWN, operator_signature="operator-mubarak"
    )
    assert is_ok(result)
    outcome = result.value
    assert outcome.mechanism is ReturnMechanism.CT30_RESUME
    assert outcome.is_resume is True
    unsigned = authorize_return_to_live(clearing_cause=ClearingCause.CONTROL_STAND_DOWN)
    assert is_refusal(unsigned)
    assert unsigned.category is RefusalCategory.POLICY_REJECTION


def test_paper_performance_never_authorizes_a_return() -> None:
    result = authorize_return_to_live(
        clearing_cause=ClearingCause.FIRST_LIVE_ENTRY,
        operator_signature="operator-mubarak",
        justified_by_paper_performance=True,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_return_to_live_refuses_bad_inputs() -> None:
    assert is_refusal(authorize_return_to_live(clearing_cause="not-a-cause"))
    assert is_refusal(
        authorize_return_to_live(
            clearing_cause=ClearingCause.CLOCKED_MECHANICAL, justified_by_paper_performance="yes"
        )
    )
    assert is_refusal(
        authorize_return_to_live(
            clearing_cause=ClearingCause.FIRST_LIVE_ENTRY, operator_signature="   "
        )
    )


def test_mint_return_to_live_transition_ties_authorize_to_the_record() -> None:
    mechanical = authorize_return_to_live(clearing_cause=ClearingCause.CLOCKED_MECHANICAL)
    assert is_ok(mechanical)
    record = mint_return_to_live_transition(
        outcome=mechanical.value,
        book_instance_id=_book_instance_id(),
        book_binding_ref=_fp("binding-epoch-live"),
        transition_instant=_instant(5_000),
        trigger_kind=_trigger(TriggerDisposition.ROUTES_TO_PAPER, "day-boundary-clear"),
    )
    assert is_ok(record)
    assert record.value.mode is BookMode.LIVE
    assert record.value.operator_signature is None
    # A first-live-entry outcome carries the signature into the LIVE transition.
    signed = authorize_return_to_live(
        clearing_cause=ClearingCause.FIRST_LIVE_ENTRY, operator_signature="operator-mubarak"
    )
    assert is_ok(signed)
    signed_record = mint_return_to_live_transition(
        outcome=signed.value,
        book_instance_id=_book_instance_id(),
        book_binding_ref=_fp("binding-epoch-live"),
        transition_instant=_instant(6_000),
        trigger_kind=_trigger(TriggerDisposition.ROUTES_TO_PAPER, "first-live-entry"),
    )
    assert is_ok(signed_record)
    assert signed_record.value.operator_signature == "operator-mubarak"


def test_mint_return_to_live_transition_refuses_ct30_and_non_outcome() -> None:
    resume = authorize_return_to_live(
        clearing_cause=ClearingCause.CONTROL_STAND_DOWN, operator_signature="op"
    )
    assert is_ok(resume)
    refused = mint_return_to_live_transition(
        outcome=resume.value,
        book_instance_id=_book_instance_id(),
        book_binding_ref=_fp("binding-epoch-live"),
        transition_instant=_instant(5_000),
        trigger_kind=_trigger(),
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    non_outcome = mint_return_to_live_transition(
        outcome="not-an-outcome",
        book_instance_id=_book_instance_id(),
        book_binding_ref=_fp("binding-epoch-live"),
        transition_instant=_instant(5_000),
        trigger_kind=_trigger(),
    )
    assert is_refusal(non_outcome)
    assert non_outcome.category is RefusalCategory.INVALID_INPUT


def test_returned_to_live_outcome_is_a_value_type() -> None:
    outcome = ReturnToLiveOutcome(
        mechanism=ReturnMechanism.CT24_TRANSITION,
        clearing_cause=ClearingCause.CLOCKED_MECHANICAL,
        operator_signature=None,
        is_resume=False,
    )
    assert outcome.mechanism is ReturnMechanism.CT24_TRANSITION
