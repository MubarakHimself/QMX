"""Display-only SemVer provenance (B-13, DEC-0167). Never identity."""

from __future__ import annotations

from typing import Final

__all__ = ["DISTRIBUTION_KIND", "DISTRIBUTION_NAME", "__version__", "identity_payload"]

# Display-only provenance — never part of fp1 identity (DEC-0167).
__version__: Final[str] = "0.1.0"
DISTRIBUTION_NAME: Final[str] = "qmb"
DISTRIBUTION_KIND: Final[str] = "library-plus-cli"


def identity_payload() -> dict[str, object]:
    """Distribution identity fields. Package SemVer is omitted (B-13)."""
    return {"distribution": DISTRIBUTION_NAME, "kind": DISTRIBUTION_KIND}
