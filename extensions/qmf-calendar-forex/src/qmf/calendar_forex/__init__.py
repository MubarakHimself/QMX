"""qmf.calendar_forex — forex market-hours calendar extension.

Off-roster extension of the QMF V1 uv workspace, on its own SemVer ladder.
At import the package forces ``TZPATH`` to its pinned ``tzdata`` and verifies
the resolved IANA tzdb equals the pin via ``qmf.core.verify_tzdb_pin``. Match
exposes a ready ``CalendarIdentity`` (rule set ``forex-17NY`` + tzdata version)
for downstream fingerprints; mismatch stores an ``unavailable dependency``
TypedRefusal and the package does not become a usable provider. A ``tzdata``
pin change is at least a minor SemVer bump on this extension's ladder.
Depends only on ``qmf-core`` and the pinned ``tzdata``.
"""

from __future__ import annotations

from qmf.calendar_forex._tzdb import (
    PINNED_TZDATA_PACKAGE,
    PINNED_TZDB_VERSION,
    RULE_SET,
    RULE_SET_VERSION,
    provider_state,
    verify_import_tzdb,
)
from qmf.core.chrono import CalendarIdentity
from qmf.core.refusal import Result

__all__ = [
    "PINNED_TZDATA_PACKAGE",
    "PINNED_TZDB_VERSION",
    "RULE_SET",
    "RULE_SET_VERSION",
    "__version__",
    "calendar_identity",
    "get_calendar_identity",
    "provider_ready",
    "tzdata_version",
    "tzdb_verification",
]

# Own SemVer ladder (off-roster extension), independent of roster lockstep.
# Display-only provenance — never part of fp1 identity.
# A tzdata pin change (PINNED_TZDATA_PACKAGE / PINNED_TZDB_VERSION) is at least
# a minor bump on this ladder; do not bump unless the pin actually changes.
__version__ = "0.1.0"


# Import-time verification: force TZPATH, compare pin to resolved tzdb (FM-1).
tzdb_verification: Result[CalendarIdentity] = verify_import_tzdb()
calendar_identity, tzdata_version, provider_ready = provider_state(tzdb_verification)


def get_calendar_identity() -> Result[CalendarIdentity]:
    """Return the verified CalendarIdentity, or the import-time TypedRefusal.

    Callers branch on ``Ok`` / ``TypedRefusal`` — never catch an exception for
    pin mismatch (CT-04).
    """
    return tzdb_verification
