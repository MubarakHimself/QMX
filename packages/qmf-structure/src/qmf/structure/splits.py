"""CT-17 — split-manifest governance by knowledge time (COMP-QMF-STRUCTURE).

Records partition into splits by **knowledge time — confirmed-at for structure objects**,
and a family's declared confirmation-delay bound feeds the split manifests' required
purge/embargo widths. This module pins down the structure-side of that governance: the
embargo-width the bound requires, and the boundary-admission rule a split manifest applies
to a structure record (CT-17; DEC-0129, DEC-0131, DEC-0119).

qmf-structure does **not** own the CT-12 split manifest — that is qmf-data's, reached
through the ratified qmf-registry->qmf-data edge, never imported here (default-deny,
DEC-0120). What qmf-structure owns is the structure record's contribution: how the
confirmation-delay bound becomes an embargo width, and whether a record may sit in a split
given a boundary.

**The confirmation-delay bound feeds the embargo width (AC #3; DEC-0131, DEC-0119).** A
family's confirmation-delay bound is an **integer count of observations at the family's
BarSpec** (:attr:`~qmf.structure.ConfirmationRule.confirmation_delay_bound`).
:func:`required_embargo_width` converts it to a time width — ``bound x observation_width``,
where the composition root supplies the BarSpec's bar duration as a plain
:class:`~qmf.core.Duration` (qmf-structure never owns BarSpec; CT-16 does). An **unbounded**
confirmation-delay declaration has no finite embargo width, so it is legal **only for
families excluded from split-governed evidence**: :func:`required_embargo_width` refuses it
as a ``policy rejection`` — the structure-side enforcement of that exclusion.

**The boundary-admission rule (FM-7; DEC-0131, DEC-0119).** :func:`admit_across_boundary`
implements the manifest's refusal: a record whose ``observed-at`` precedes a split boundary
while its ``confirmed-at`` follows it **straddles** the boundary — it partitions (by
confirmed-at) into the later segment yet was derivable from data in the earlier one. The
manifest **refuses** such a record (``policy rejection``) unless the declared embargo covers
the knowledge-time gap ``confirmed-at - observed-at``; a record confirmed within its
declared delay bound is always covered, and only one that took longer to confirm than its
family declared is refused. A record that does not straddle any boundary is admitted.

Default-deny holds: this module imports **only** ``qmf.core`` and the sibling
``qmf.structure`` value types. It returns typed values, never stamped records; the
composition root and qmf-data own the manifest itself. Public value types are frozen
dataclasses and every operation succeeds or RETURNS a CT-04
:class:`~qmf.core.TypedRefusal`; domain failure is never raised across the boundary
(DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core import (
    Duration,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)
from qmf.structure.objects import ConfirmationRule

__all__ = [
    "SplitAdmission",
    "admit_across_boundary",
    "required_embargo_width",
]


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a split-governance operation returns.

    ``retryability`` is ``no`` — a non-``Instant`` boundary, a non-``Duration`` embargo
    width, a non-positive observation width, or a confirmed-at behind an observed-at is a
    caller/wiring mistake, not a transient condition — and ``context`` always names the
    offending ``field`` and a human-legible ``reason`` (returned, never raised; CT-04;
    DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal split governance returns (FM-7; DEC-0131,
    DEC-0119).

    An unbounded confirmation-delay family placed in split-governed evidence, or a record
    that straddles a boundary beyond its declared embargo, is not *malformed* — it is a
    well-formed thing the split law **declines** — so it is a policy rejection. ``retryability``
    is ``no``: it succeeds only once the family declares a finite bound, or the split declares
    a wider embargo, which is a different manifest, not a retry.
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


# --- AC #3: the confirmation-delay bound feeds the embargo width ------------


def required_embargo_width(rule: object, *, observation_width: object) -> Result[Duration]:
    """The embargo width a family's confirmation-delay bound requires (AC #3; DEC-0131,
    DEC-0119).

    Converts the family's declared confirmation-delay bound — an **integer count of
    observations at the family's BarSpec** — into a time width by multiplying it by
    ``observation_width``, the BarSpec's bar duration the composition root supplies (a plain
    :class:`~qmf.core.Duration`; qmf-structure never owns BarSpec). The result is the
    contribution this family makes to a split manifest's required purge/embargo width.

    An **unbounded** confirmation-delay declaration
    (:attr:`~qmf.structure.ConfirmationRule.confirmation_delay_bound` is ``None``) has no
    finite embargo width and is legal **only for families excluded from split-governed
    evidence**: this RETURNS a ``policy rejection``, the structure-side enforcement of that
    exclusion. A bound of zero (clock-confirmed / same-observation) yields a zero-width
    embargo. ``observation_width`` must be a strictly positive duration.
    """
    if not isinstance(rule, ConfirmationRule):
        return _invalid(
            "rule",
            "the embargo width derives from a family's ConfirmationRule",
            given=repr(rule),
        )
    if not isinstance(observation_width, Duration):
        return _invalid(
            "observation_width",
            "the observation width is a Duration — the family's BarSpec bar duration the "
            "composition root supplies (qmf-structure never owns BarSpec)",
            given=repr(observation_width),
        )
    if observation_width.value_ns <= 0:
        return _invalid(
            "observation_width",
            "the observation width is strictly positive (one bar spans a positive duration)",
            given=observation_width.value_ns,
        )
    bound = rule.confirmation_delay_bound
    if bound is None:
        return _policy(
            "confirmation_delay_bound",
            "an unbounded confirmation-delay family has no finite embargo width and is legal "
            "only for families excluded from split-governed evidence (AC #3); it cannot enter "
            "a split manifest",
        )
    # bound is a non-negative int (ConfirmationRule.try_create guarantees it); the product is
    # checked against the int64 range by Duration.try_create, never wrapped.
    return Duration.try_create(bound * observation_width.value_ns)


# --- FM-7: the boundary-admission rule --------------------------------------


@dataclass(frozen=True, slots=True)
class SplitAdmission:
    """A structure record's admission across a split boundary (CT-17, FM-7; DEC-0131,
    DEC-0119).

    Returned only when the record **is** admitted. ``partition_at`` is the record's
    knowledge-time partition key — its ``confirmed-at``, since structure records partition by
    confirmed-at. ``straddles`` is whether the record's ``observed-at`` precedes the boundary
    while its ``confirmed-at`` follows it (an admitted straddle is one the embargo covers).
    ``gap_ns`` is the record's knowledge-time gap ``confirmed-at - observed-at`` and
    ``embargo_ns`` the declared embargo width, both in nanoseconds — a witness that the check
    ran, never a stored field of any object.
    """

    partition_at: Instant
    straddles: bool
    gap_ns: int
    embargo_ns: int


def admit_across_boundary(
    *, boundary: object, observed_at: object, confirmed_at: object, embargo_width: object
) -> Result[SplitAdmission]:
    """Admit a structure record across a split boundary, or refuse it (FM-7; DEC-0131,
    DEC-0119).

    A record partitions into splits by **confirmed-at**. It **straddles** ``boundary`` when
    its ``observed_at`` precedes the boundary (``observed_at < boundary``) while its
    ``confirmed_at`` follows it (``confirmed_at > boundary``): it lands (by confirmed-at) in
    the later segment yet was derivable from data before the boundary. The manifest
    **refuses** a straddling record (``policy rejection``) unless the declared
    ``embargo_width`` covers the knowledge-time gap ``confirmed_at - observed_at``; a record
    confirmed within its family's declared delay bound is always covered (its gap never
    exceeds the embargo the bound produced, :func:`required_embargo_width`), and only one that
    took longer to confirm than declared is refused. A record that does not straddle the
    boundary is admitted.

    ``boundary``, ``observed_at``, and ``confirmed_at`` are :class:`~qmf.core.Instant`\\ s
    with ``observed_at <= confirmed_at`` (a record is never confirmed before it is observed);
    ``embargo_width`` is a non-negative :class:`~qmf.core.Duration`. Returns a
    :class:`SplitAdmission` witness on admission, or a CT-04 refusal.
    """
    if not isinstance(boundary, Instant):
        return _invalid("boundary", "a split boundary is an Instant", given=repr(boundary))
    if not isinstance(observed_at, Instant):
        return _invalid("observed_at", "observed-at is an Instant", given=repr(observed_at))
    if not isinstance(confirmed_at, Instant):
        return _invalid("confirmed_at", "confirmed-at is an Instant", given=repr(confirmed_at))
    if not isinstance(embargo_width, Duration):
        return _invalid(
            "embargo_width",
            "the declared embargo width is a Duration",
            given=repr(embargo_width),
        )
    if embargo_width.value_ns < 0:
        return _invalid(
            "embargo_width",
            "the embargo width is non-negative",
            given=embargo_width.value_ns,
        )
    if confirmed_at.value_ns < observed_at.value_ns:
        return _invalid(
            "confirmed_at",
            "a record's confirmed-at is at or after its observed-at; a record is never "
            "confirmed before it is observed",
            observed_at=observed_at.value_ns,
            confirmed_at=confirmed_at.value_ns,
        )

    gap_ns = confirmed_at.value_ns - observed_at.value_ns
    straddles = observed_at.value_ns < boundary.value_ns < confirmed_at.value_ns
    if straddles and gap_ns > embargo_width.value_ns:
        return _policy(
            "boundary",
            "a record whose observed-at precedes the boundary while its confirmed-at follows "
            "it straddles the split and is refused unless the declared embargo covers the "
            "knowledge-time gap (FM-7); partitioning is by confirmed-at",
            boundary=boundary.value_ns,
            observed_at=observed_at.value_ns,
            confirmed_at=confirmed_at.value_ns,
            gap_ns=gap_ns,
            embargo_ns=embargo_width.value_ns,
        )
    return Ok(
        SplitAdmission(
            partition_at=confirmed_at,
            straddles=straddles,
            gap_ns=gap_ns,
            embargo_ns=embargo_width.value_ns,
        )
    )
