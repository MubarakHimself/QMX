"""Import-time TZPATH pin and tzdb verification for the forex calendar (CT-02 FM-1).

Forces ``zoneinfo`` to resolve this extension's pinned ``tzdata`` package (not the
OS tzdb), reads the IANA version from that path, and compares it to the pin via
``qmf.core.verify_tzdb_pin``. Match yields a ready ``CalendarIdentity``; mismatch
is an ``unavailable dependency`` TypedRefusal — never raised across the boundary.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from zoneinfo import reset_tzpath

import tzdata
from qmf.core.chrono import CalendarIdentity, verify_tzdb_pin
from qmf.core.refusal import RefusalCategory, Result, Retryability, TypedRefusal, is_ok

# PyPI pin — must stay identical to ``tzdata==…`` in this extension's pyproject.
# Changing the pin is at least a minor SemVer bump on this extension's ladder.
PINNED_TZDATA_PACKAGE: str = "2025.2"
# IANA tzdb version shipped by that PyPI pin (``tzdata.IANA_VERSION`` for 2025.2).
PINNED_TZDB_VERSION: str = "2025b"

RULE_SET: str = "forex-17NY"
RULE_SET_VERSION: str = "v1"

_VERSION_HEADER = re.compile(r"#\s*version\s+(\S+)")


def _pinned_zoneinfo_dir() -> Path:
    """Absolute ``tzdata`` package ``zoneinfo/`` directory for this pin."""
    return Path(tzdata.__file__).resolve().parent / "zoneinfo"


def force_tzpath(zone_dir: Path | None = None) -> Path:
    """Force ``TZPATH`` / ``zoneinfo`` to this extension's pinned ``tzdata``.

    Sets the process ``TZPATH`` environment variable and resets the in-process
    ``zoneinfo`` search path so subsequent lookups resolve the pin, not an OS
    tzdb that might differ.
    """
    resolved_dir = zone_dir if zone_dir is not None else _pinned_zoneinfo_dir()
    path_text = str(resolved_dir)
    os.environ["TZPATH"] = path_text
    reset_tzpath((path_text,))
    return resolved_dir


def read_resolved_tzdb_version(zone_dir: Path) -> str | None:
    """Read the IANA tzdb version from the forced ``zoneinfo`` directory.

    Reads only the ``tzdata.zi`` header on that path — the data ``zoneinfo``
    will actually use — so a bad ``TZPATH`` cannot be papered over by package
    metadata from a different install.
    """
    zi_path = zone_dir / "tzdata.zi"
    if not zi_path.is_file():
        return None
    first_line = zi_path.read_text(encoding="utf-8", errors="replace").splitlines()[0]
    match = _VERSION_HEADER.match(first_line)
    return match.group(1) if match is not None else None


def _unreadable(pinned: str, zone_dir: Path) -> TypedRefusal:
    """Unavailable-dependency refusal when the forced path has no readable version."""
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={
            "field": "tzdata_version",
            "reason": (
                "the forced tzdata zoneinfo path has no readable IANA tzdb version; "
                "a fingerprint must never attest an unverified tzdb (FM-1)"
            ),
            "pinned": pinned,
            "zone_dir": str(zone_dir),
        },
    )


def verify_import_tzdb(
    *,
    pinned: str = PINNED_TZDB_VERSION,
    zone_dir: Path | None = None,
) -> Result[CalendarIdentity]:
    """Force TZPATH, verify the pin, and return CalendarIdentity or TypedRefusal.

    On match the returned ``CalendarIdentity`` carries ``forex-17NY``, the rule-set
    version, and the verified tzdata version for downstream fingerprints. On
    mismatch the package must not become a usable provider.
    """
    forced = force_tzpath(zone_dir)
    resolved = read_resolved_tzdb_version(forced)
    if resolved is None:
        return _unreadable(pinned, forced)
    checked = verify_tzdb_pin(pinned, resolved)
    if isinstance(checked, TypedRefusal):
        return checked
    return CalendarIdentity.try_create(RULE_SET, RULE_SET_VERSION, checked.value)


def provider_state(
    result: Result[CalendarIdentity],
) -> tuple[CalendarIdentity | None, str | None, bool]:
    """Map a verification Result to (identity, tzdata_version, provider_ready).

    Match exposes CalendarIdentity for downstream fingerprints; mismatch leaves
    the provider unusable with no attested tzdb version (FM-1).
    """
    if is_ok(result):
        identity = result.value
        return identity, identity.tzdata_version, True
    return None, None, False
