"""Footprint producer-binding forms (QL-4).

The footprint is the single canonical consumption manifest. Each producer binding
is a pinned CT-16/CT-17 fingerprint or a complete template minus space-bound
values; resolution is a later story (DEC-0174).
"""

from __future__ import annotations

from enum import StrEnum

from qmf.core.refusal import Ok, Result

from qml._refuse import invalid

__all__ = ["ProducerBindingForm", "parse_binding_form"]


class ProducerBindingForm(StrEnum):
    """Closed producer-binding forms; addable never redefined (DEC-0174)."""

    PINNED_FINGERPRINT = "pinned-fingerprint"
    TEMPLATE = "template"


def parse_binding_form(value: object) -> Result[ProducerBindingForm]:
    """Resolve a producer-binding form, value-or-refusal."""
    if isinstance(value, ProducerBindingForm):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(ProducerBindingForm(value))
        except ValueError:
            pass
    return invalid(
        "form",
        "a producer binding is pinned-fingerprint or template",
        given=repr(value),
    )
