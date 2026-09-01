"""Node-close vs venue-terminal race disposition (TN-24j).

A node close that races a venue margin liquidation or venue-initiated close
resolves ``rejected-by-venue`` with qualifier ``superseded-by-terminal-subject``
— a named outcome, never UNKNOWN — with the subject-terminal observation as
named resolving evidence, CT-29 reason ``venue_liquidation`` or
``venue_initiated_close``, and ``closing_authority = venue``. A subject absent
or already terminal before handoff resolves without submission and never as a
naked close (DEC-0209; CT-19/20/29; Story 24.9).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

from qmn.venue import (
    Command,
    CommandKind,
    ObservationKind,
    SubjectResolution,
    SubmissionOutcome,
    resolve_subject_terminal,
)

__all__ = [
    "CLOSING_AUTHORITY_VENUE",
    "CT29_VENUE_INITIATED_CLOSE",
    "CT29_VENUE_LIQUIDATION",
    "SUPERSEDED_BY_TERMINAL_SUBJECT",
    "Ct29VenueCloseReason",
    "TerminalSubjectDisposition",
    "resolve_node_close_against_subject",
]


SUPERSEDED_BY_TERMINAL_SUBJECT: Final[str] = "superseded-by-terminal-subject"
CLOSING_AUTHORITY_VENUE: Final[str] = "venue"
CT29_VENUE_LIQUIDATION: Final[str] = "venue_liquidation"
CT29_VENUE_INITIATED_CLOSE: Final[str] = "venue_initiated_close"

_SUBJECT_KINDS: Final[frozenset[CommandKind]] = frozenset(
    {
        CommandKind.CLOSE_POSITION,
        CommandKind.CLOSE_ALL,
        CommandKind.AMEND_PROTECTION,
    }
)


class Ct29VenueCloseReason(StrEnum):
    """CT-29 venue-authored close reasons that carry ``closing_authority = venue``."""

    VENUE_LIQUIDATION = CT29_VENUE_LIQUIDATION
    VENUE_INITIATED_CLOSE = CT29_VENUE_INITIATED_CLOSE


@dataclass(frozen=True, slots=True)
class TerminalSubjectDisposition:
    """Named disposition of a node close against a venue terminal subject (TN-24j)."""

    resolution: SubjectResolution
    outcome: SubmissionOutcome | None
    qualifier: str | None
    close_reason: Ct29VenueCloseReason | None
    closing_authority: str | None
    resolving_evidence: Mapping[str, object] | None
    submitted: bool
    detail: str

    @property
    def is_unknown(self) -> bool:
        return self.outcome is SubmissionOutcome.UNKNOWN

    @property
    def is_naked_close(self) -> bool:
        return False


def resolve_node_close_against_subject(
    command: object,
    *,
    observations: object,
    submit_stamp: object,
    subject_present_at_submission: object,
    venue_close_reason: object = Ct29VenueCloseReason.VENUE_LIQUIDATION,
) -> Result[TerminalSubjectDisposition]:
    """Resolve a subject command against venue terminal observations (TN-24j).

    Uses CT-20 ``resolve_subject_terminal`` and attaches CT-29 venue close
    evidence when the subject terminal wins. Never returns UNKNOWN for the
    superseded race. Never reports a naked close when the subject is absent or
    already terminal before handoff.
    """
    if not isinstance(command, Command):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "command",
                "reason": "terminal-subject disposition reads a typed CT-19 Command",
                "given": type(command).__name__,
            },
        )
    if command.kind not in _SUBJECT_KINDS:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "command",
                "reason": (
                    "terminal-subject disposition applies to close_position | "
                    "close_all | amend_protection"
                ),
                "kind": command.kind.value,
            },
        )
    if not isinstance(submit_stamp, Instant):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "submit_stamp",
                "reason": "submit stamp compared to subject-terminal evidence is an Instant",
                "given": repr(submit_stamp),
            },
        )
    if not isinstance(subject_present_at_submission, bool):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "subject_present_at_submission",
                "reason": "pre-handoff subject presence is a boolean from a pre-submit read",
                "given": repr(subject_present_at_submission),
            },
        )
    reason = _coerce_close_reason(venue_close_reason)
    if isinstance(reason, TypedRefusal):
        return reason

    resolved = resolve_subject_terminal(
        command,
        observations=observations,
        submit_stamp=submit_stamp,
        subject_present_at_submission=subject_present_at_submission,
    )
    if is_refusal(resolved):
        return resolved
    if not is_ok(resolved):
        return resolved
    base = resolved.value

    if base.resolution is SubjectResolution.RESOLVE_WITHOUT_SUBMISSION:
        evidence = _evidence_mapping(base.resolving_observation)
        return Ok(
            TerminalSubjectDisposition(
                resolution=SubjectResolution.RESOLVE_WITHOUT_SUBMISSION,
                outcome=None,
                qualifier=None,
                close_reason=None,
                closing_authority=None,
                resolving_evidence=evidence,
                submitted=False,
                detail=(
                    "subject absent or already terminal before handoff; resolves "
                    "without submission, never as a naked close"
                ),
            )
        )

    if base.resolution is SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT:
        if base.outcome is not SubmissionOutcome.REJECTED_BY_VENUE:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "outcome",
                    "reason": (
                        "superseded-by-terminal-subject must resolve "
                        "rejected-by-venue, never UNKNOWN"
                    ),
                    "given": None if base.outcome is None else base.outcome.value,
                },
            )
        evidence = _evidence_mapping(base.resolving_observation)
        close_reason = _reason_from_observation(base.resolving_observation, reason)
        return Ok(
            TerminalSubjectDisposition(
                resolution=SubjectResolution.SUPERSEDED_BY_TERMINAL_SUBJECT,
                outcome=SubmissionOutcome.REJECTED_BY_VENUE,
                qualifier=SUPERSEDED_BY_TERMINAL_SUBJECT,
                close_reason=close_reason,
                closing_authority=CLOSING_AUTHORITY_VENUE,
                resolving_evidence=evidence,
                submitted=True,
                detail=(
                    "node close superseded by venue terminal subject; "
                    "rejected-by-venue (superseded-by-terminal-subject) with "
                    f"CT-29 {close_reason.value} and closing_authority=venue"
                ),
            )
        )

    return Ok(
        TerminalSubjectDisposition(
            resolution=SubjectResolution.PROCEED,
            outcome=None,
            qualifier=None,
            close_reason=None,
            closing_authority=None,
            resolving_evidence=None,
            submitted=False,
            detail="subject is live with no terminal observation; the command proceeds",
        )
    )


def _coerce_close_reason(value: object) -> Ct29VenueCloseReason | TypedRefusal:
    if isinstance(value, Ct29VenueCloseReason):
        return value
    if isinstance(value, str):
        try:
            return Ct29VenueCloseReason(value)
        except ValueError:
            pass
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={
            "field": "venue_close_reason",
            "reason": "CT-29 venue close reason is venue_liquidation | venue_initiated_close",
            "given": repr(value),
            "allowed": [m.value for m in Ct29VenueCloseReason],
        },
    )


def _reason_from_observation(
    observation: object,
    default: Ct29VenueCloseReason,
) -> Ct29VenueCloseReason:
    """Prefer an explicit CT-29 reason on the observation payload when present."""
    raw_obj = getattr(observation, "raw_payload", None)
    if isinstance(raw_obj, Mapping):
        raw = cast("Mapping[str, object]", raw_obj)
        tagged = raw.get("close_reason") or raw.get("ct29_close_reason")
        if isinstance(tagged, str):
            try:
                return Ct29VenueCloseReason(tagged)
            except ValueError:
                pass
        kind = raw.get("lifecycle_kind")
        if kind == "venue_liquidation":
            return Ct29VenueCloseReason.VENUE_LIQUIDATION
        if kind in {"venue_initiated_close", "close-by-venue"}:
            return Ct29VenueCloseReason.VENUE_INITIATED_CLOSE
    obs_kind = getattr(observation, "observation_kind", None)
    if obs_kind is ObservationKind.CLOSE_BY_VENUE:
        return default
    return default


def _evidence_mapping(observation: object) -> Mapping[str, object] | None:
    if observation is None:
        return None
    identity = getattr(observation, "venue_native_identity", None)
    kind = getattr(observation, "observation_kind", None)
    subject = getattr(observation, "subject_native_id", None)
    payload: dict[str, object] = {
        "named_resolving_evidence": True,
    }
    if kind is not None:
        payload["observation_kind"] = getattr(kind, "value", str(kind))
    if subject is not None:
        payload["subject_native_id"] = subject
    if identity is not None:
        source = getattr(identity, "source", None)
        native = getattr(identity, "source_native_id", None)
        revision = getattr(identity, "revision", None)
        if source is not None:
            payload["source"] = source
        if native is not None:
            payload["source_native_id"] = native
        if revision is not None:
            payload["revision"] = revision
    return payload
