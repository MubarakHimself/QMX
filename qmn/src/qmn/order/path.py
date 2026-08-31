"""Order path: mint → protect → pace → bind → handoff → submit (Story 24.5 / TN-6).

After a Book-authorized intent clears the protection gate the node allocates a
lifetime-monotone command ordinal, persists the command-fingerprint-to-venue-id
binding before wire handoff, refuses unprotected ``place_order``, admits through
the protection-priority pacer, starts the submission deadline only at handoff,
and never retries after handoff. Compound all-rejected acceptance stays blocked
on FTR-02 (DEC-0191, DEC-0224).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core import (
    Duration,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

from qmn.order.identity import CommandIdentityBinder, mint_venue_client_id
from qmn.order.ordinal import CommandOrdinalStore
from qmn.order.pacer import ConnectionCommandPacer, PacerAdmission, WireHandoff
from qmn.order.protection import require_venue_resident_protective_stop
from qmn.venue import (
    Command,
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
    """

    ordinal_store: CommandOrdinalStore
    binder: CommandIdentityBinder
    pacer: ConnectionCommandPacer
    client: VenueClientPort
    forms_per_order_type: Mapping[str, object]
    submission_deadline_duration: Duration
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
    ) -> Result[OrderPathSubmission]:
        """Submit one Book-authorized command through the full TN-6 order path.

        Steps: sequencer gate → protective-stop proof → pacer admit → identity
        bind → wire handoff (deadline starts) → VenueClientPort.submit. Compound
        commands stay FTR-02-blocked. No retry after handoff.
        """
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
