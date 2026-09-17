"""Label-entry admit helper (split from ``_admit_fields`` for Skylos quality)."""

from __future__ import annotations

from qmf.core.refusal import Ok, Result

from qml._refuse import invalid

__all__ = ["admit_label_entry"]


def admit_label_entry(
    raw_key: object,
    raw_label: object,
    *,
    field: str,
    allowed: frozenset[str] | None,
) -> Result[tuple[str, str]]:
    if not isinstance(raw_key, str) or raw_key.strip() == "":
        return invalid(field, f"{field} keys are non-empty strings", given=repr(raw_key))
    if not isinstance(raw_label, str) or raw_label.strip() == "":
        return invalid(field, f"{field} values are non-empty strings", given=repr(raw_label))
    label = raw_label.casefold().strip()
    if allowed is not None and label not in allowed:
        return invalid(field, f"{field} labels are the Stage 0 closed set", given=label)
    return Ok((raw_key.casefold().strip(), label))
