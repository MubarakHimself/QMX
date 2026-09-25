"""Order path: mint → protect → pace → bind → handoff → submit (Story 24.5 / TN-6).

After a Book-authorized intent clears the protection gate the node allocates a
lifetime-monotone command ordinal, persists the command-fingerprint-to-venue-id
binding before wire handoff, refuses unprotected ``place_order``, admits through
the protection-priority pacer, starts the submission deadline only at handoff,
and never retries after handoff. Compound all-rejected acceptance stays blocked
on FTR-02 (DEC-0191, DEC-0224).

Story 24.6: when an optional :class:`~qmn.order.unknown.CommandStreamUnknownBoundary`
is bound, every submit is gated at the exact ``(VenueId, account)`` UNKNOWN
stream boundary before pacer admission — UNKNOWN never becomes a rejection.

Story 24.7: ``amend_protection`` is gated by measured amend atomicity, journaled
before dispatch, never suppressed by ``amend_min_improvement``, and never
emulated by an invented amend sequence; ``close_partial`` stays unsupported.

Story 24.9: a subject command whose subject is absent or already terminal before
handoff resolves without submission (never a naked close); a post-submit venue
terminal race is disposed via :func:`~qmn.order.terminal.resolve_node_close_against_subject`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core import (
    Duration,
    Instant,
    JournalSink,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

from qmn.journal_dispatch import (
    CallableDispatcher,
    WriteBoundary,
    journal_before_effect,
)
from qmn.order.amend import (
    AmendAtomicity,
    BookDynamicProtectionPolicy,
    DynamicProtectionOrigin,
    gate_amend_protection,
    journal_amend_before_dispatch,
    resolve_amend_atomicity,
)
from qmn.order.identity import CommandIdentityBinder, mint_venue_client_id
from qmn.order.ordinal import CommandOrdinalStore
from qmn.order.pacer import ConnectionCommandPacer, PacerAdmission, WireHandoff
from qmn.order.protection import require_venue_resident_protective_stop
from qmn.order.terminal import (
    Ct29VenueCloseReason,
    TerminalSubjectDisposition,
    resolve_node_close_against_subject,
)
from qmn.order.unknown import CommandStreamUnknownBoundary, HeldProtectionAct
from qmn.venue import (
    AdmissionDisposition,
    AdmissionResult,
    Command,
    CommandKind,
    CompoundCommand,
    SubjectResolution,
    SubmissionResult,
    VenueClientPort,
    compound_command_acceptance_blocked,
)

__all__ = [
    "FTR02_COMPOUND_BLOCKED",
    "OrderPath",
    "OrderPathSubmission",
    "OrderPathTerminalResolution",
    "compound_all_rejected_acceptance_blocked",
]


FTR02_COMPOUND_BLOCKED: Final[str] = "FTR-02"


def compound_all_rejected_acceptance_blocked() -> TypedRefusal:
    """FTR-02: do not choose rejected-by-venue vs partially-executed for all-rejected.

    Compound-command acceptance stays blocked until the tracked CT-19/TN-6
    annotation lands. No worker picks an outcome from the contradictory prose.
    """
    blocked = compound_command_acceptance_blocked()
    context: dict[str, object] = dict(blocked.context)
    context["all_rejected_rule"] = "blocked-until-ftr02-annotation"
    context["forbidden_choice"] = ("rejected-by-venue", "partially-executed")
    return TypedRefusal(
        category=blocked.category,
        retryability=blocked.retryability,
        context=context,
        after_condition_descriptor=blocked.after_condition_descriptor,
    )


@dataclass(frozen=True, slots=True)
class OrderPathSubmission:
    """Evidence of one mint→bind→handoff→submit cycle."""

    command: Command
    venue_client_id: str
    admission: PacerAdmission
    handoff: WireHandoff
    result: SubmissionResult
    protective_stop_form: str
    terminal_disposition: TerminalSubjectDisposition | None = None


@dataclass(frozen=True, slots=True)
class OrderPathTerminalResolution:
    """Subject command resolved without wire handoff (TN-24j pre-submission half)."""

    command: Command
    disposition: TerminalSubjectDisposition

    @property
    def submitted(self) -> bool:
        return False

    @property
    def is_naked_close(self) -> bool:
        return self.disposition.is_naked_close


@dataclass
class OrderPath:
    """Wires command identity, protection priority, and submission timing.

    Constructed after ordinal high-water recovery and CT-18 verification. The
    protection gate is assumed already applied by the caller — this path mints
    at most one durable attributable venue command per authorized intent.
    When ``unknown_boundary`` is bound, submit is gated at the exact
    ``(VenueId, account)`` UNKNOWN stream boundary (Story 24.6 / QMX-F062).
    ``amend_atomicity`` and ``book_dynamic_protection_policy`` gate Story 24.7
    amend semantics; an optional ``amend_journal`` journals before dispatch.
    """

    ordinal_store: CommandOrdinalStore
    binder: CommandIdentityBinder
    pacer: ConnectionCommandPacer
    client: VenueClientPort
    forms_per_order_type: Mapping[str, object]
    submission_deadline_duration: Duration
    unknown_boundary: CommandStreamUnknownBoundary | None = None
    amend_atomicity: AmendAtomicity = AmendAtomicity.UNMEASURED
    book_dynamic_protection_policy: BookDynamicProtectionPolicy = (
        BookDynamicProtectionPolicy.SINGLE_SIDED_BREAKEVEN_RATCHET
    )
    amend_journal: JournalSink[object] | None = None
    command_journal: JournalSink[object] | None = None
    _sequencer_open: bool = False

    @classmethod
    def try_create(
        cls,
        *,
        ordinal_store: object,
        binder: object,
        pacer: object,
        client: object,
        forms_per_order_type: object,
        submission_deadline_duration: object,
        unknown_boundary: object = None,
        amend_atomicity: object = AmendAtomicity.UNMEASURED,
        book_dynamic_protection_policy: object = (
            BookDynamicProtectionPolicy.SINGLE_SIDED_BREAKEVEN_RATCHET
        ),
        amend_journal: object = None,
        command_journal: object = None,
    ) -> Result[OrderPath]:
        core = _bind_path_core(ordinal_store, binder, pacer, client)
        if is_refusal(core):
            return core
        store, ident, paced, port = core.value
        forms = _bind_path_forms_and_deadline(forms_per_order_type, submission_deadline_duration)
        if is_refusal(forms):
            return forms
        form_map, deadline = forms.value
        extras = _bind_path_options(
            unknown_boundary=unknown_boundary,
            amend_atomicity=amend_atomicity,
            book_dynamic_protection_policy=book_dynamic_protection_policy,
            amend_journal=amend_journal,
            command_journal=command_journal,
        )
        if is_refusal(extras):
            return extras
        options = extras.value
        return Ok(
            cls(
                ordinal_store=store,
                binder=ident,
                pacer=paced,
                client=port,
                forms_per_order_type=form_map,
                submission_deadline_duration=deadline,
                unknown_boundary=options.boundary,
                amend_atomicity=options.atomicity,
                book_dynamic_protection_policy=options.policy,
                amend_journal=options.amend_journal,
                command_journal=options.command_journal,
            )
        )

    def open_sequencer(self) -> Result[bool]:
        """Open the command sequencer only after ordinal high-water recovery."""
        gate = self.ordinal_store.require_recovered_for_sequencer()
        if is_refusal(gate):
            return gate
        self._sequencer_open = True
        return Ok(True)

    @property
    def sequencer_open(self) -> bool:
        return self._sequencer_open

    def mint_ordinal(self) -> Result[int]:
        """Allocate the next lifetime-monotone ordinal (persist high-water first)."""
        if not self._sequencer_open:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "command_sequencer",
                    "reason": "ordinal allocation requires an open sequencer",
                },
                after_condition_descriptor="open_sequencer",
            )
        return self.ordinal_store.allocate()

    def submit_authorized(
        self,
        command: object,
        *,
        enqueued_at: object,
        now_mono: object,
        handed_off_at: object,
        amend_origin: object = DynamicProtectionOrigin.BOT_PROPOSAL,
        amend_min_improvement: object = None,
        dual_side_requested: object = False,
        amend_sequence: object = None,
        subject_present_at_submission: object = None,
        subject_observations: object = None,
        venue_close_reason: object = Ct29VenueCloseReason.VENUE_LIQUIDATION,
    ) -> Result[OrderPathSubmission | OrderPathTerminalResolution]:
        """Submit one Book-authorized command through the full TN-6 order path.

        Steps: sequencer gate → subject-terminal pre-handoff gate (Story 24.9) →
        amend atomicity / journal-before-dispatch → protective-stop proof →
        pacer admit → identity bind → wire handoff (deadline starts) →
        VenueClientPort.submit. Compound commands stay FTR-02-blocked. No retry
        after handoff. ``amend_min_improvement`` is accepted only to prove it
        never suppresses a risk-non-increasing amend.
        """
        _ = amend_min_improvement  # origination policy only — never a path gate
        gated = _gate_submit_command(command, sequencer_open=self._sequencer_open)
        if is_refusal(gated):
            return gated
        typed = gated.value
        pre = _pre_handoff_submit_gates(
            self,
            typed,
            handed_off_at=handed_off_at,
            amend_origin=amend_origin,
            dual_side_requested=dual_side_requested,
            amend_sequence=amend_sequence,
            subject_present_at_submission=subject_present_at_submission,
            subject_observations=subject_observations,
            venue_close_reason=venue_close_reason,
        )
        if is_refusal(pre):
            return pre
        if pre.value is not None:
            return Ok(pre.value)
        handed = _admit_bind_and_handoff(
            self,
            typed,
            enqueued_at=enqueued_at,
            now_mono=now_mono,
            handed_off_at=handed_off_at,
        )
        if is_refusal(handed):
            return handed
        dispatched = _dispatch_after_handoff(self, handed.value)
        if is_refusal(dispatched):
            return dispatched
        return Ok(dispatched.value)

    def retry_after_handoff(self, command_fp1: object) -> Result[bool]:
        """Explicit no-retry gate after wire handoff."""
        return self.pacer.refuse_retry_after_handoff(command_fp1)


@dataclass(frozen=True, slots=True)
class _PathOptions:
    boundary: CommandStreamUnknownBoundary | None
    atomicity: AmendAtomicity
    policy: BookDynamicProtectionPolicy
    amend_journal: JournalSink[object] | None
    command_journal: JournalSink[object] | None


@dataclass(frozen=True, slots=True)
class _HandoffContext:
    command: Command
    venue_client_id: str
    admission: PacerAdmission
    handoff: WireHandoff
    stop_form: str
    command_fp1: str


def _invalid_path_field(field: str, reason: str, given: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, "given": given},
    )


def _bind_path_core(
    ordinal_store: object,
    binder: object,
    pacer: object,
    client: object,
) -> Result[
    tuple[CommandOrdinalStore, CommandIdentityBinder, ConnectionCommandPacer, VenueClientPort]
]:
    if not isinstance(ordinal_store, CommandOrdinalStore):
        return _invalid_path_field(
            "ordinal_store",
            "order path requires a CommandOrdinalStore",
            type(ordinal_store).__name__,
        )
    if not isinstance(binder, CommandIdentityBinder):
        return _invalid_path_field(
            "binder",
            "order path requires a CommandIdentityBinder",
            type(binder).__name__,
        )
    if not isinstance(pacer, ConnectionCommandPacer):
        return _invalid_path_field(
            "pacer",
            "order path requires a ConnectionCommandPacer",
            type(pacer).__name__,
        )
    if not isinstance(client, VenueClientPort):
        return _invalid_path_field(
            "client",
            "order path submits through VenueClientPort",
            type(client).__name__,
        )
    return Ok((ordinal_store, binder, pacer, client))


def _bind_path_forms_and_deadline(
    forms_per_order_type: object,
    submission_deadline_duration: object,
) -> Result[tuple[dict[str, object], Duration]]:
    if not isinstance(forms_per_order_type, Mapping):
        return _invalid_path_field(
            "forms_per_order_type",
            "CT-18 protective-stop forms per order type are required",
            repr(forms_per_order_type),
        )
    if (
        not isinstance(submission_deadline_duration, Duration)
        or submission_deadline_duration.value_ns <= 0
    ):
        return _invalid_path_field(
            "submission_deadline",
            "registry:submission_deadline is a positive Duration",
            repr(submission_deadline_duration),
        )
    return Ok(
        (
            dict(cast("Mapping[str, object]", forms_per_order_type)),
            submission_deadline_duration,
        )
    )


def _bind_unknown_boundary(
    unknown_boundary: object,
) -> Result[CommandStreamUnknownBoundary | None]:
    if unknown_boundary is None:
        return Ok(None)
    if isinstance(unknown_boundary, CommandStreamUnknownBoundary):
        return Ok(unknown_boundary)
    return _invalid_path_field(
        "unknown_boundary",
        "order path gates through a CommandStreamUnknownBoundary or None",
        type(unknown_boundary).__name__,
    )


def _bind_book_policy(
    book_dynamic_protection_policy: object,
) -> Result[BookDynamicProtectionPolicy]:
    if isinstance(book_dynamic_protection_policy, BookDynamicProtectionPolicy):
        return Ok(book_dynamic_protection_policy)
    if isinstance(book_dynamic_protection_policy, str):
        try:
            return Ok(BookDynamicProtectionPolicy(book_dynamic_protection_policy.strip().lower()))
        except ValueError:
            return _invalid_path_field(
                "book_dynamic_protection_policy",
                "Book policy is single-sided-breakeven-ratchet or refuse-before-origination",
                book_dynamic_protection_policy,
            )
    return _invalid_path_field(
        "book_dynamic_protection_policy",
        "Book dynamic-protection policy is required",
        repr(book_dynamic_protection_policy),
    )


def _optional_journal_sink(
    value: object, field: str, reason: str
) -> Result[JournalSink[object] | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, JournalSink):
        return Ok(cast("JournalSink[object]", value))
    return _invalid_path_field(field, reason, type(value).__name__)


def _bind_path_options(
    *,
    unknown_boundary: object,
    amend_atomicity: object,
    book_dynamic_protection_policy: object,
    amend_journal: object,
    command_journal: object,
) -> Result[_PathOptions]:
    boundary = _bind_unknown_boundary(unknown_boundary)
    if is_refusal(boundary):
        return boundary
    resolved_atomicity = resolve_amend_atomicity(amend_atomicity)
    policy = _bind_book_policy(book_dynamic_protection_policy)
    if is_refusal(policy):
        return policy
    journal = _optional_journal_sink(
        amend_journal,
        "amend_journal",
        "amend_protection journals through a JournalSink or None",
    )
    if is_refusal(journal):
        return journal
    command_sink = _optional_journal_sink(
        command_journal,
        "command_journal",
        "commands journal through a JournalSink before dispatch",
    )
    if is_refusal(command_sink):
        return command_sink
    return Ok(
        _PathOptions(
            boundary=boundary.value,
            atomicity=resolved_atomicity,
            policy=policy.value,
            amend_journal=journal.value,
            command_journal=command_sink.value,
        )
    )


def _gate_submit_command(command: object, *, sequencer_open: bool) -> Result[Command]:
    if isinstance(command, CompoundCommand):
        return compound_all_rejected_acceptance_blocked()
    if not isinstance(command, Command):
        return _invalid_path_field(
            "command",
            "order path submits a typed CT-19 Command",
            type(command).__name__,
        )
    if not sequencer_open:
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=Retryability.AFTER_CONDITION,
            context={
                "field": "command_sequencer",
                "reason": "command sequencer is closed until ordinal high-water is recovered",
            },
            after_condition_descriptor="recover ordinal high-water then open_sequencer",
        )
    return Ok(command)


def _gate_subject_before_handoff(
    command: Command,
    *,
    handed_off_at: object,
    subject_present_at_submission: object,
    subject_observations: object,
    venue_close_reason: object,
) -> Result[OrderPathTerminalResolution | None]:
    # Story 24.9: subject absent/terminal before handoff → without submission.
    if subject_present_at_submission is None and subject_observations is None:
        return Ok(None)
    if not isinstance(handed_off_at, Instant):
        return _invalid_path_field(
            "handed_off_at",
            "subject-terminal pre-handoff gate compares against the handoff Instant "
            "as submit stamp",
            repr(handed_off_at),
        )
    present = True if subject_present_at_submission is None else subject_present_at_submission
    observations: Sequence[object] | tuple[()] = (
        () if subject_observations is None else cast("Sequence[object]", subject_observations)
    )
    gated = resolve_node_close_against_subject(
        command,
        observations=observations,
        submit_stamp=handed_off_at,
        subject_present_at_submission=present,
        venue_close_reason=venue_close_reason,
    )
    if is_refusal(gated):
        return gated
    if is_ok(gated) and gated.value.resolution is SubjectResolution.RESOLVE_WITHOUT_SUBMISSION:
        return Ok(OrderPathTerminalResolution(command=command, disposition=gated.value))
    # SUPERSEDED_BY_TERMINAL_SUBJECT is a post-submit named outcome —
    # resolve via resolve_node_close_against_subject after observations land.
    return Ok(None)


def _gate_amend_on_path(
    path: OrderPath,
    command: Command,
    *,
    handed_off_at: object,
    amend_origin: object,
    dual_side_requested: object,
    amend_sequence: object,
) -> Result[None]:
    # Story 24.7: amend atomicity + never invent a sequence; journal before dispatch.
    if command.kind is not CommandKind.AMEND_PROTECTION:
        return Ok(None)
    gated = gate_amend_protection(
        command,
        atomicity=path.amend_atomicity,
        book_policy=path.book_dynamic_protection_policy,
        origin=amend_origin,
        dual_side_requested=dual_side_requested,
        amend_sequence=amend_sequence,
    )
    if is_refusal(gated):
        return gated
    if path.amend_journal is None:
        return Ok(None)
    if not isinstance(handed_off_at, Instant):
        return _invalid_path_field(
            "handed_off_at",
            "amend_protection journals before dispatch at a wall Instant",
            repr(handed_off_at),
        )
    journaled = journal_amend_before_dispatch(
        command,
        journal=path.amend_journal,
        journaled_at=handed_off_at,
        atomicity=path.amend_atomicity,
        origin=amend_origin,
    )
    if is_refusal(journaled):
        return journaled
    return Ok(None)


def _unknown_held_refusal(gate_value: HeldProtectionAct) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "field": "command_stream",
            "reason": gate_value.detail,
            "disposition": gate_value.disposition.value,
            "held": True,
            "journaled_to_extent": gate_value.journaled_to_extent,
            "command_fp1": gate_value.command_fp1.value,
            "command_kind": gate_value.kind.value,
            "outcome": "UNKNOWN",
            "never_rejection": True,
        },
        after_condition_descriptor="resolution",
    )


def _unknown_non_admit_refusal(gate_value: AdmissionResult) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "field": "command_stream",
            "reason": gate_value.detail,
            "disposition": gate_value.disposition.value,
            "outcome": "UNKNOWN",
            "never_rejection": True,
        },
        after_condition_descriptor="resolution",
    )


def _gate_unknown_on_path(
    path: OrderPath, command: Command, *, handed_off_at: object
) -> Result[None]:
    # Story 24.6: exact (VenueId, account) UNKNOWN boundary before dispatch.
    if path.unknown_boundary is None:
        return Ok(None)
    if not isinstance(handed_off_at, Instant):
        return _invalid_path_field(
            "handed_off_at",
            "UNKNOWN boundary admit requires a wall Instant (also used as the receive stamp)",
            repr(handed_off_at),
        )
    gated = path.unknown_boundary.admit(command, receive_instant=handed_off_at)
    if is_refusal(gated):
        return gated
    gate_value = gated.value
    if isinstance(gate_value, HeldProtectionAct):
        return _unknown_held_refusal(gate_value)
    if gate_value.disposition is not AdmissionDisposition.ADMITTED:
        if gate_value.refusal is not None:
            return gate_value.refusal
        return _unknown_non_admit_refusal(gate_value)
    return Ok(None)


def _pre_handoff_submit_gates(
    path: OrderPath,
    command: Command,
    *,
    handed_off_at: object,
    amend_origin: object,
    dual_side_requested: object,
    amend_sequence: object,
    subject_present_at_submission: object,
    subject_observations: object,
    venue_close_reason: object,
) -> Result[OrderPathTerminalResolution | None]:
    pre = _gate_subject_before_handoff(
        command,
        handed_off_at=handed_off_at,
        subject_present_at_submission=subject_present_at_submission,
        subject_observations=subject_observations,
        venue_close_reason=venue_close_reason,
    )
    if is_refusal(pre):
        return pre
    if pre.value is not None:
        return pre
    amend = _gate_amend_on_path(
        path,
        command,
        handed_off_at=handed_off_at,
        amend_origin=amend_origin,
        dual_side_requested=dual_side_requested,
        amend_sequence=amend_sequence,
    )
    if is_refusal(amend):
        return amend
    unknown = _gate_unknown_on_path(path, command, handed_off_at=handed_off_at)
    if is_refusal(unknown):
        return unknown
    return Ok(None)


def _consume_stop_and_admit(
    path: OrderPath,
    command: Command,
    *,
    enqueued_at: object,
    now_mono: object,
) -> Result[tuple[str, PacerAdmission]]:
    consumed = path.ordinal_store.mark_submitted(command.ordering_ordinal)
    if is_refusal(consumed):
        return consumed
    stop_form = require_venue_resident_protective_stop(
        command,
        forms_per_order_type=path.forms_per_order_type,
    )
    if is_refusal(stop_form):
        return stop_form
    queued = path.pacer.enqueue(command)
    if is_refusal(queued):
        return queued
    admission = path.pacer.admit(command, enqueued_at=enqueued_at, now=now_mono)
    if is_refusal(admission):
        return admission
    return Ok((stop_form.value, admission.value))


def _release_admission(path: OrderPath, admission: PacerAdmission) -> None:
    _ = path.pacer.release(admission.admission_class)


def _bind_identity_and_fp(
    path: OrderPath, command: Command, admission: PacerAdmission
) -> Result[tuple[str, str]]:
    client_id = mint_venue_client_id(
        ordering_ordinal=command.ordering_ordinal,
        session_epoch=command.session_epoch,
    )
    if is_refusal(client_id):
        _release_admission(path, admission)
        return client_id
    bound = path.binder.bind_before_wire_handoff(
        command,
        venue_client_id=client_id.value,
    )
    if is_refusal(bound):
        _release_admission(path, admission)
        return bound
    fp = command.fingerprint()
    if is_refusal(fp):
        _release_admission(path, admission)
        return fp
    return Ok((client_id.value, fp.value.value))


def _begin_wire_handoff(
    path: OrderPath,
    *,
    admission: PacerAdmission,
    command_fp1: str,
    handed_off_at: object,
) -> Result[WireHandoff]:
    if not isinstance(handed_off_at, Instant):
        _release_admission(path, admission)
        return _invalid_path_field(
            "handed_off_at",
            "submission deadline begins at wire handoff Instant",
            repr(handed_off_at),
        )
    deadline_ns = handed_off_at.value_ns + path.submission_deadline_duration.value_ns
    deadline = Instant.try_create(deadline_ns)
    if is_refusal(deadline):
        _release_admission(path, admission)
        return deadline
    handoff = path.pacer.begin_wire_handoff(
        command_fp1=command_fp1,
        handed_off_at=handed_off_at,
        submission_deadline=deadline.value,
    )
    if is_refusal(handoff):
        _release_admission(path, admission)
        return handoff
    return Ok(handoff.value)


def _admit_bind_and_handoff(
    path: OrderPath,
    command: Command,
    *,
    enqueued_at: object,
    now_mono: object,
    handed_off_at: object,
) -> Result[_HandoffContext]:
    admitted = _consume_stop_and_admit(path, command, enqueued_at=enqueued_at, now_mono=now_mono)
    if is_refusal(admitted):
        return admitted
    stop_form, admission = admitted.value
    bound = _bind_identity_and_fp(path, command, admission)
    if is_refusal(bound):
        return bound
    venue_client_id, command_fp1 = bound.value
    handoff = _begin_wire_handoff(
        path,
        admission=admission,
        command_fp1=command_fp1,
        handed_off_at=handed_off_at,
    )
    if is_refusal(handoff):
        return handoff
    return Ok(
        _HandoffContext(
            command=command,
            venue_client_id=venue_client_id,
            admission=admission,
            handoff=handoff.value,
            stop_form=stop_form,
            command_fp1=command_fp1,
        )
    )


def _submission_from_context(
    handed: _HandoffContext, result: SubmissionResult
) -> OrderPathSubmission:
    return OrderPathSubmission(
        command=handed.command,
        venue_client_id=handed.venue_client_id,
        admission=handed.admission,
        handoff=handed.handoff,
        result=result,
        protective_stop_form=handed.stop_form,
    )


def _journaled_submit(
    path: OrderPath,
    handed: _HandoffContext,
    journal: JournalSink[object],
) -> Result[OrderPathSubmission]:
    command = handed.command

    def _submit(_payload: Mapping[str, object]) -> Result[SubmissionResult]:
        _ = _payload
        return path.client.submit(command)

    receipt = journal_before_effect(
        kind="command",
        payload={
            "kind": "command",
            "command_kind": command.kind.value,
            "command_fp1": handed.command_fp1,
            "phase": "before-dispatch",
        },
        journal=journal,
        dispatcher=CallableDispatcher(_submit),
        boundary=WriteBoundary.ORDERED_WITH_RECOVERY,
    )
    _release_admission(path, handed.admission)
    if is_refusal(receipt):
        return receipt
    submitted_value = receipt.value.dispatcher_result
    if not isinstance(submitted_value, SubmissionResult):
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
            retryability=Retryability.NO,
            context={
                "field": "command",
                "reason": "journal-before-dispatch did not yield a SubmissionResult",
            },
        )
    return Ok(_submission_from_context(handed, submitted_value))


def _dispatch_after_handoff(
    path: OrderPath, handed: _HandoffContext
) -> Result[OrderPathSubmission]:
    # Past handoff: never retry — a failed submit is terminal for this mint.
    if path.command_journal is not None:
        return _journaled_submit(path, handed, path.command_journal)
    submitted = path.client.submit(handed.command)
    _release_admission(path, handed.admission)
    if is_refusal(submitted):
        return submitted
    if not is_ok(submitted):
        return submitted
    return Ok(_submission_from_context(handed, submitted.value))
