"""Venue-resident protective-stop gate for ``place_order`` (TN-6; CT-18/19).

Every ``place_order`` carries a venue-resident protective stop at placement in
the form CT-18 declares for that order type. Where capability verification
cannot prove the required form, the entry is refused before submission — no
unprotected entry reaches the broker (DEC-0191, DEC-0196).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, cast

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_refusal

from qmn.venue import Command, CommandKind, OrderType

__all__ = [
    "ENTRY_RELATIVE_FORM",
    "require_venue_resident_protective_stop",
    "resolved_protective_stop_form",
]


ENTRY_RELATIVE_FORM: Final[str] = "entry-relative"


def _unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context={"field": field, "reason": reason, **extra},
    )


def resolved_protective_stop_form(
    forms_per_order_type: object,
    order_type: object,
) -> Result[str]:
    """Resolve the CT-18-declared protective-stop form for ``order_type``."""
    if isinstance(order_type, OrderType):
        type_token = order_type.value
    elif isinstance(order_type, str) and order_type.strip() != "":
        type_token = order_type.strip().lower()
    else:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "order_type",
                "reason": "protective-stop form is resolved per order type",
                "given": repr(order_type),
            },
        )
    forms: Mapping[str, object] | None = None
    if isinstance(forms_per_order_type, Mapping):
        forms = cast("Mapping[str, object]", forms_per_order_type)
    elif isinstance(forms_per_order_type, Sequence) and not isinstance(
        forms_per_order_type, (str, bytes)
    ):
        # A bare sequence of form names applies the first declared form to all types.
        form_seq = cast("Sequence[object]", forms_per_order_type)
        if len(form_seq) == 0:
            return _unsupported(
                "protective_stop_forms",
                "CT-18 protective-stop forms are absent; place_order is refused "
                "rather than submitting an unprotected entry",
                order_type=type_token,
            )
        first: object = form_seq[0]
        if not isinstance(first, str) or first.strip() == "":
            return _unsupported(
                "protective_stop_forms",
                "CT-18 protective-stop forms must name a declared form token",
                given=repr(first),
                order_type=type_token,
            )
        return Ok(first.strip().lower())
    else:
        return _unsupported(
            "protective_stop_forms",
            "capability verification cannot prove a venue-resident protective "
            "stop form; place_order is refused before submission",
            given=repr(forms_per_order_type),
            order_type=type_token,
        )
    raw = forms.get(type_token)
    if raw is None:
        # Accept common alias keys (e.g. MARKET vs market).
        raw = forms.get(type_token.upper()) or forms.get(type_token.lower())
    if not isinstance(raw, str) or raw.strip() == "":
        return _unsupported(
            "protective_stop_forms",
            "CT-18 does not declare a protective-stop form for this order type; "
            "no unprotected entry reaches the broker",
            order_type=type_token,
            declared_types=sorted(str(key) for key in forms),
        )
    return Ok(raw.strip().lower())


def require_venue_resident_protective_stop(
    command: object,
    *,
    forms_per_order_type: object,
) -> Result[str]:
    """Refuse ``place_order`` that lacks a proven venue-resident protective stop.

    Non-entry kinds pass unconditionally. For ``place_order``, capability
    verification must prove the required form and the command must carry the
    matching attachment (entry-relative ``protective_stop_distance`` for the
    cTrader-platform MARKET path).
    """
    if not isinstance(command, Command):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "command",
                "reason": "protective-stop gate reads a typed CT-19 Command",
                "given": type(command).__name__,
            },
        )
    if command.kind is not CommandKind.PLACE_ORDER:
        return Ok("not-applicable")
    params = command.order_parameters
    if params is None:
        return _unsupported(
            "order_parameters",
            "place_order requires typed order parameters carrying protective-stop attachment",
        )
    form = resolved_protective_stop_form(forms_per_order_type, params.order_type)
    if is_refusal(form):
        return form
    required = form.value
    if required == ENTRY_RELATIVE_FORM:
        if params.protective_stop_distance is None:
            return _unsupported(
                "protective_stop_distance",
                "place_order requires a venue-resident entry-relative protective "
                "stop at placement; unprotected entry is refused before submission",
                order_type=params.order_type.value,
                required_form=required,
            )
        return Ok(required)
    # Absolute (or other declared) forms still require an attachment present on
    # the command — V1's place_order surface carries the entry-relative distance;
    # an undeclared absolute-only path without a distance is refused rather than
    # submitting unprotected.
    if params.protective_stop_distance is None:
        return _unsupported(
            "protective_stop_attachment",
            "place_order requires a venue-resident protective stop in the CT-18 "
            "declared form; unprotected entry is refused before submission",
            order_type=params.order_type.value,
            required_form=required,
        )
    return Ok(required)
