"""Correlation provenance gate (CT-40; AD-5; L39; FR-Q16).

``correlation_id`` has exactly three minting origins — an originating operator
command, a scheduled trigger, and a daemon-internal lifecycle act — and is
copied verbatim onto every downstream record. Recipients never regenerate,
derive, or abbreviate it. A non-evidence record without one is refused at the
gate with no substitute identifier. An evidence append without one is recorded
under a daemon-minted lifecycle id annotated ``correlation_missing``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal

from qma.wire.envelope import CORRELATION_MISSING_ANNOTATION
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "CORRELATION_MINT_ORIGINS",
    "CORRELATION_MISSING_ANNOTATION",
    "CorrelationAdmission",
    "CorrelationMintOrigin",
    "admit_correlation",
    "assert_copied_verbatim",
    "copy_correlation_id",
    "mint_correlation_id",
    "propagate_correlation",
]


class CorrelationError(ValueError):
    """Raised when correlation provenance inputs cannot be constructed."""


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


class CorrelationMintOrigin(StrEnum):
    """The three closed minting origins for ``correlation_id`` (DEC-0304)."""

    OPERATOR_COMMAND = "operator_command"
    SCHEDULED_TRIGGER = "scheduled_trigger"
    DAEMON_LIFECYCLE = "daemon_lifecycle"


CORRELATION_MINT_ORIGINS: Final[frozenset[str]] = frozenset(
    member.value for member in CorrelationMintOrigin
)


@dataclass(frozen=True, slots=True)
class CorrelationAdmission:
    """Accepted correlation provenance for a wire or evidence record."""

    correlation_id: str
    correlation_missing: bool
    source: Literal["minted", "copied", "lifecycle_carve_out"]
    origin: CorrelationMintOrigin | None = None

    def to_envelope_fields(self) -> dict[str, object]:
        """Fields to stamp on a wire envelope; omit false carve-out annotation."""
        out: dict[str, object] = {"correlation_id": self.correlation_id}
        if self.correlation_missing:
            out[CORRELATION_MISSING_ANNOTATION] = True
        return out


def mint_correlation_id(
    *,
    origin: object,
    correlation_id: object,
) -> Result[CorrelationAdmission]:
    """Mint ``correlation_id`` once at a closed origin; never at a recipient."""
    if not isinstance(origin, CorrelationMintOrigin):
        if isinstance(origin, str) and origin in CORRELATION_MINT_ORIGINS:
            origin = CorrelationMintOrigin(origin)
        else:
            return _invalid(
                "origin",
                "correlation_id may be minted only at an originating operator "
                "command, a scheduled trigger, or a daemon-internal lifecycle act",
                given=repr(origin),
                allowed=sorted(CORRELATION_MINT_ORIGINS),
            )
    if not isinstance(correlation_id, str) or correlation_id.strip() == "":
        return _invalid(
            "correlation_id",
            "minted correlation_id must be a non-empty opaque string",
            given=repr(correlation_id),
        )
    return Ok(
        CorrelationAdmission(
            correlation_id=correlation_id,
            correlation_missing=False,
            source="minted",
            origin=origin,
        )
    )


def copy_correlation_id(source: object) -> Result[str]:
    """Copy ``correlation_id`` verbatim for a downstream record."""
    if not isinstance(source, str) or source.strip() == "":
        return _invalid(
            "correlation_id",
            "downstream copy requires a non-empty source correlation_id",
            given=repr(source),
        )
    return Ok(source)


def assert_copied_verbatim(origin: object, received: object) -> Result[str]:
    """Refuse regenerated, derived, abbreviated, or otherwise changed ids.

    Equality is exact string identity — a truncated prefix, a derived suffix, or
    a freshly minted substitute all fail the same gate.
    """
    origin_ok = copy_correlation_id(origin)
    if not isinstance(origin_ok, Ok):
        return origin_ok
    if not isinstance(received, str) or received.strip() == "":
        return _policy(
            "correlation_id",
            "recipients must copy correlation_id verbatim; empty or absent "
            "received values are not a substitute identifier",
            origin=origin_ok.value,
            given=repr(received),
        )
    if received != origin_ok.value:
        return _policy(
            "correlation_id",
            "recipients never regenerate, derive, abbreviate, or otherwise "
            "change correlation_id; copy it verbatim from its minting origin",
            origin=origin_ok.value,
            received=received,
        )
    return Ok(origin_ok.value)


def admit_correlation(
    *,
    correlation_id: object = None,
    is_evidence_append: bool = False,
    daemon_lifecycle_id: object = None,
) -> Result[CorrelationAdmission]:
    """Wire-gate correlation provenance for one record.

    Non-evidence records without ``correlation_id`` are refused — the refusal
    never invents a substitute identifier. Evidence appends without one take the
    L39 carve-out: a daemon-minted lifecycle id annotated ``correlation_missing``.
    """
    if isinstance(correlation_id, str) and correlation_id.strip() != "":
        return Ok(
            CorrelationAdmission(
                correlation_id=correlation_id,
                correlation_missing=False,
                source="copied",
                origin=None,
            )
        )

    if correlation_id is not None and not isinstance(correlation_id, str):
        return _invalid(
            "correlation_id",
            "correlation_id must be a non-empty string when present",
            given=repr(correlation_id),
        )

    if is_evidence_append:
        if not isinstance(daemon_lifecycle_id, str) or daemon_lifecycle_id.strip() == "":
            return _invalid(
                "daemon_lifecycle_id",
                "evidence append without correlation_id requires a daemon-minted "
                "lifecycle identifier for the correlation_missing carve-out",
                given=repr(daemon_lifecycle_id),
            )
        return Ok(
            CorrelationAdmission(
                correlation_id=daemon_lifecycle_id,
                correlation_missing=True,
                source="lifecycle_carve_out",
                origin=CorrelationMintOrigin.DAEMON_LIFECYCLE,
            )
        )

    # Non-evidence missing correlation: typed refusal, no substitute id minted.
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={
            "field": "correlation_id",
            "reason": (
                "correlation_id is required on non-evidence records; the gate "
                "refuses without inventing a substitute identifier (DEC-0304)"
            ),
            "is_evidence_append": False,
            # Explicitly absent — conformance: refusal does not invent an id.
            "substitute_identifier": None,
        },
    )


def propagate_correlation(
    origin_correlation_id: object,
    downstream: Sequence[object],
) -> Result[str]:
    """Require every downstream value to equal the origin string verbatim."""
    origin_ok = copy_correlation_id(origin_correlation_id)
    if not isinstance(origin_ok, Ok):
        return origin_ok
    for index, received in enumerate(downstream):
        checked = assert_copied_verbatim(origin_ok.value, received)
        if not isinstance(checked, Ok):
            # Preserve refusal; annotate position for diagnostics only.
            ctx = dict(checked.context)
            ctx["downstream_index"] = index
            return TypedRefusal(
                category=checked.category,
                retryability=checked.retryability,
                context=ctx,
            )
    return Ok(origin_ok.value)
