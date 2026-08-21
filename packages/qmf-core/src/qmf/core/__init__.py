"""qmf.core — exact domain foundation.

Roster package of the QMF V1 uv workspace. It declares the package identity and
version and re-exports the public CT-* surface as it lands story by story: CT-04,
the typed refusal envelope; CT-03, the instrument/venue/account identity nouns;
and CT-01, the exact money/price/quantity value vocabulary. Nothing here reaches
across a sibling boundary — the default-deny dependency direction (L30) is
preserved by construction, and qmf-core takes zero outside dependencies
(DEC-0104).
"""

from __future__ import annotations

from qmf.core.exact import (
    CONTRACT_FORMAT_VERSION,
    ExactRational,
    Money,
    Price,
    PriceDelta,
    Quantity,
    RoundingMode,
    UnitKind,
    ValueFactor,
)
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
    "CONTRACT_FORMAT_VERSION",
    "Account",
    "AccountRole",
    "DatedRecord",
    "ExactRational",
    "Instrument",
    "Money",
    "Ok",
    "Price",
    "PriceDelta",
    "Quantity",
    "RefusalCategory",
    "Result",
    "Retryability",
    "RoundingMode",
    "TypedRefusal",
    "UnitKind",
    "ValueFactor",
    "Venue",
    "VenueId",
    "__version__",
    "is_ok",
    "is_refusal",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
