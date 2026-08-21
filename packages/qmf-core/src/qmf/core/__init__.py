"""qmf.core — exact domain foundation.

Roster package of the QMF V1 uv workspace. It declares the package identity and
version and re-exports the public CT-* surface as it lands story by story: CT-04,
the typed refusal envelope, and CT-03, the instrument/venue/account identity
nouns. Nothing here reaches across a sibling boundary — the default-deny
dependency direction (L30) is preserved by construction, and qmf-core takes zero
outside dependencies (DEC-0104).
"""

from __future__ import annotations

from qmf.core.identity import (
    Account,
    AccountRole,
    DatedRecord,
    Instrument,
    Venue,
    VenueId,
)
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

__all__ = [
    "Account",
    "AccountRole",
    "DatedRecord",
    "Instrument",
    "Ok",
    "RefusalCategory",
    "Result",
    "Retryability",
    "TypedRefusal",
    "Venue",
    "VenueId",
    "__version__",
    "is_ok",
    "is_refusal",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
