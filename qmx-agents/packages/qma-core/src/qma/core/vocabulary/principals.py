"""Principal-class conversion rules (AD-24; DEC-0323; CT-40)."""

from __future__ import annotations

from qma.core.vocabulary.enums import PrincipalClass
from qma.core.vocabulary.registry import VocabularyError, parse_closed

__all__ = ["assert_no_principal_conversion", "may_convert_principal"]


def may_convert_principal(
    source: PrincipalClass | str,
    target: PrincipalClass | str,
) -> bool:
    """Return whether an authenticated connection may change principal class.

    Only ``operator`` and ``machine`` exist. A ``machine`` principal may never
    convert into ``operator`` (or any other class). Same-class is a no-op, not a
    conversion.
    """
    src = parse_closed(PrincipalClass, source)
    dst = parse_closed(PrincipalClass, target)
    return src is dst


def assert_no_principal_conversion(
    source: PrincipalClass | str,
    target: PrincipalClass | str,
) -> None:
    """Refuse conversion of a machine principal into an operator principal."""
    src = parse_closed(PrincipalClass, source)
    dst = parse_closed(PrincipalClass, target)
    if src is dst:
        return
    raise VocabularyError(
        f"principal class {src.value!r} may not convert into {dst.value!r}; "
        "authenticated connections are operator or machine only"
    )
