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
"""

from __future__ import annotations

from collections.abc import Mapping
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
from qmn.order.unknown import CommandStreamUnknownBoundary, HeldProtectionAct
from qmn.venue import (
    AdmissionDisposition,
    Command,
    CommandKind,
    CompoundCommand,
    SubmissionResult,
    VenueClientPort,
    compound_command_acceptance_blocked,
)

__all__ = [
    "FTR02_COMPOUND_BLOCKED",
    "OrderPath",
    "OrderPathSubmission",
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
    ) -> Result[OrderPath]:
        if not isinstance(ordinal_store, CommandOrdinalStore):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "ordinal_store",
                    "reason": "order path requires a CommandOrdinalStore",
                    "given": type(ordinal_store).__name__,
                },
            )
        if not isinstance(binder, CommandIdentityBinder):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "binder",
                    "reason": "order path requires a CommandIdentityBinder",
                    "given": type(binder).__name__,
                },
            )
        if not isinstance(pacer, ConnectionCommandPacer):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "pacer",
                    "reason": "order path requires a ConnectionCommandPacer",
                    "given": type(pacer).__name__,
                },
            )
        if not isinstance(client, VenueClientPort):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "client",
                    "reason": "order path submits through VenueClientPort",
                    "given": type(client).__name__,
                },
            )
        if not isinstance(forms_per_order_type, Mapping):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "forms_per_order_type",
                    "reason": "CT-18 protective-stop forms per order type are required",
                    "given": repr(forms_per_order_type),
                },
            )
        if (
            not isinstance(submission_deadline_duration, Duration)
            or submission_deadline_duration.value_ns <= 0
        ):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "submission_deadline",
                    "reason": "registry:submission_deadline is a positive Duration",
                    "given": repr(submission_deadline_duration),
                },
            )
        boundary: CommandStreamUnknownBoundary | None
        if unknown_boundary is None:
            boundary = None
        elif isinstance(unknown_boundary, CommandStreamUnknownBoundary):
            boundary = unknown_boundary
        else:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "unknown_boundary",
                    "reason": (
                        "order path gates through a CommandStreamUnknownBoundary "
                        "or None"
                    ),
                    "given": type(unknown_boundary).__name__,
                },
            )
        resolved_atomicity = resolve_amend_atomicity(amend_atomicity)
        if isinstance(book_dynamic_protection_policy, BookDynamicProtectionPolicy):
            policy = book_dynamic_protection_policy
        elif isinstance(book_dynamic_protection_policy, str):
            try:
                policy = BookDynamicProtectionPolicy(
                    book_dynamic_protection_policy.strip().lower()
                )
            except ValueError:
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "book_dynamic_protection_policy",
                        "reason": (
                            "Book policy is single-sided-breakeven-ratchet or "
                            "refuse-before-origination"
                        ),
                        "given": book_dynamic_protection_policy,
                    },
                )
        else:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "book_dynamic_protection_policy",
                    "reason": "Book dynamic-protection policy is required",
                    "given": repr(book_dynamic_protection_policy),
                },
            )
        journal: JournalSink[object] | None
        if amend_journal is None:
            journal = None
        elif isinstance(amend_journal, JournalSink):
            journal = cast("JournalSink[object]", amend_journal)
        else:
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "amend_journal",
                    "reason": "amend_protection journals through a JournalSink or None",
                    "given": type(amend_journal).__name__,
                },
            )
        return Ok(
            cls(
                ordinal_store=ordinal_store,
                binder=binder,
                pacer=pacer,
                client=client,
                forms_per_order_type=dict(
                    cast("Mapping[str, object]", forms_per_order_type)
                ),
                submission_deadline_duration=submission_deadline_duration,
                unknown_boundary=boundary,
                amend_atomicity=resolved_atomicity,
                book_dynamic_protection_policy=policy,
                amend_journal=journal,
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
    ) -> Result[OrderPathSubmission]:
        """Submit one Book-authorized command through the full TN-6 order path.

        Steps: sequencer gate → amend atomicity / journal-before-dispatch →
        protective-stop proof → pacer admit → identity bind → wire handoff
        (deadline starts) → VenueClientPort.submit. Compound commands stay
        FTR-02-blocked. No retry after handoff. ``amend_min_improvement`` is
        accepted only to prove it never suppresses a risk-non-increasing amend.
        """
        del amend_min_improvement  # origination policy only — never a path gate
        if isinstance(command, CompoundCommand):
            return compound_all_rejected_acceptance_blocked()
        if not isinstance(command, Command):
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "command",
                    "reason": "order path submits a typed CT-19 Command",
                    "given": type(command).__name__,
                },
            )
        if not self._sequencer_open:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "command_sequencer",
                    "reason": "command sequencer is closed until ordinal high-water "
                    "is recovered",
                },
                after_condition_descriptor="recover ordinal high-water then open_sequencer",
            )

        # Story 24.7: amend atomicity + never invent a sequence; journal before dispatch.
        if command.kind is CommandKind.AMEND_PROTECTION:
            gated = gate_amend_protection(
                command,
                atomicity=self.amend_atomicity,
                book_policy=self.book_dynamic_protection_policy,
                origin=amend_origin,
                dual_side_requested=dual_side_requested,
                amend_sequence=amend_sequence,
            )
            if is_refusal(gated):
                return gated
            if self.amend_journal is not None:
                if not isinstance(handed_off_at, Instant):
                    return TypedRefusal(
                        category=RefusalCategory.INVALID_INPUT,
                        retryability=Retryability.NO,
                        context={
                            "field": "handed_off_at",
                            "reason": (
                                "amend_protection journals before dispatch at a "
                                "wall Instant"
                            ),
                            "given": repr(handed_off_at),
                        },
                    )
                journaled = journal_amend_before_dispatch(
                    command,
                    journal=self.amend_journal,
                    journaled_at=handed_off_at,
                    atomicity=self.amend_atomicity,
                    origin=amend_origin,
                )
                if is_refusal(journaled):
                    return journaled

        # Story 24.6: exact (VenueId, account) UNKNOWN boundary before dispatch.
        if self.unknown_boundary is not None:
            if not isinstance(handed_off_at, Instant):
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "handed_off_at",
                        "reason": (
                            "UNKNOWN boundary admit requires a wall Instant "
                            "(also used as the receive stamp)"
                        ),
                        "given": repr(handed_off_at),
                    },
                )
            gated = self.unknown_boundary.admit(
                command, receive_instant=handed_off_at
            )
            if is_refusal(gated):
                return gated
            gate_value = gated.value
            if isinstance(gate_value, HeldProtectionAct):
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
            if gate_value.disposition is not AdmissionDisposition.ADMITTED:
                if gate_value.refusal is not None:
                    return gate_value.refusal
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

        consumed = self.ordinal_store.mark_submitted(command.ordering_ordinal)
        if is_refusal(consumed):
            return consumed

        stop_form = require_venue_resident_protective_stop(
            command,
            forms_per_order_type=self.forms_per_order_type,
        )
        if is_refusal(stop_form):
            return stop_form

        queued = self.pacer.enqueue(command)
        if is_refusal(queued):
            return queued
        admission = self.pacer.admit(command, enqueued_at=enqueued_at, now=now_mono)
        if is_refusal(admission):
            return admission

        client_id = mint_venue_client_id(
            ordering_ordinal=command.ordering_ordinal,
            session_epoch=command.session_epoch,
        )
        if is_refusal(client_id):
            _ = self.pacer.release(admission.value.admission_class)
            return client_id

        bound = self.binder.bind_before_wire_handoff(
            command,
            venue_client_id=client_id.value,
        )
        if is_refusal(bound):
            _ = self.pacer.release(admission.value.admission_class)
            return bound

        fp = command.fingerprint()
        if is_refusal(fp):
            _ = self.pacer.release(admission.value.admission_class)
            return fp
        if not isinstance(handed_off_at, Instant):
            _ = self.pacer.release(admission.value.admission_class)
            return TypedRefusal(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "handed_off_at",
                    "reason": "submission deadline begins at wire handoff Instant",
                    "given": repr(handed_off_at),
                },
            )
        deadline_ns = handed_off_at.value_ns + self.submission_deadline_duration.value_ns
        deadline = Instant.try_create(deadline_ns)
        if is_refusal(deadline):
            _ = self.pacer.release(admission.value.admission_class)
            return deadline

        handoff = self.pacer.begin_wire_handoff(
            command_fp1=fp.value.value,
            handed_off_at=handed_off_at,
            submission_deadline=deadline.value,
        )
        if is_refusal(handoff):
            _ = self.pacer.release(admission.value.admission_class)
            return handoff

        # Past handoff: never retry — a failed submit is terminal for this mint.
        submitted = self.client.submit(command)
        _ = self.pacer.release(admission.value.admission_class)
        if is_refusal(submitted):
            return submitted
        if not is_ok(submitted):
            return submitted
        return Ok(
            OrderPathSubmission(
                command=command,
                venue_client_id=client_id.value,
                admission=admission.value,
                handoff=handoff.value,
                result=submitted.value,
                protective_stop_form=stop_form.value,
            )
        )

    def retry_after_handoff(self, command_fp1: object) -> Result[bool]:
        """Explicit no-retry gate after wire handoff."""
        return self.pacer.refuse_retry_after_handoff(command_fp1)
