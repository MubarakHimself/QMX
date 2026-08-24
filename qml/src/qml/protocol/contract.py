"""QML-owned bot runtime protocol contract (QL-7).

Format-versioned on QML's own AD-5 ladder — not CT-numbered, mirroring QMB's
own contracts (DEC-0177). Package SemVer never enters identity (DEC-0180).
"""

from __future__ import annotations

from typing import Final

from qmf.core.refusal import Ok, Result

from qml._refuse import invalid, unsupported

__all__ = [
    "PROTOCOL_CONTRACT_CLASS",
    "PROTOCOL_DENIAL_SET",
    "PROTOCOL_FORMAT_VERSION",
    "PROTOCOL_KNOWN_FORMAT_VERSIONS",
    "PROTOCOL_LADDER",
    "coerce_protocol_format_version",
    "protocol_contract_identity",
]

PROTOCOL_CONTRACT_CLASS: Final[str] = "qml-bot-runtime-protocol"
PROTOCOL_FORMAT_VERSION: Final[int] = 1
PROTOCOL_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset({PROTOCOL_FORMAT_VERSION})
# QML-local AD-5 second ladder. Not a CT-* number (DEC-0177).
PROTOCOL_LADDER: Final[str] = "qml-ad5"

# Capabilities a conformant bot may never exercise through this protocol.
# Hosts inject read surfaces only; the evaluation instant rides the callback.
PROTOCOL_DENIAL_SET: Final[frozenset[str]] = frozenset(
    {"clock", "io", "network", "undeclared_randomness"}
)


def protocol_contract_identity() -> dict[str, object]:
    """Canonical identity of the protocol contract. No CT number, no package SemVer."""
    return {
        "class": PROTOCOL_CONTRACT_CLASS,
        "contract_format_version": PROTOCOL_FORMAT_VERSION,
        "ladder": PROTOCOL_LADDER,
    }


def coerce_protocol_format_version(value: object) -> Result[int]:
    """Admit the active protocol format version; unknown is unsupported capability."""
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            "protocol_format_version",
            "a protocol format version is a positive integer; package SemVer never enters",
            given=repr(value),
        )
    if value < 1:
        return invalid(
            "protocol_format_version",
            "a protocol format version is a positive integer ordinal",
            given=repr(value),
        )
    if value not in PROTOCOL_KNOWN_FORMAT_VERSIONS:
        return unsupported(
            "protocol_format_version",
            "an uninterpretable bot-runtime-protocol format version is an "
            "unsupported capability refusal, never a best-effort read — the "
            "protocol is QML-owned on the qml-ad5 ladder, not CT-numbered",
            given=value,
            supported=PROTOCOL_FORMAT_VERSION,
            ladder=PROTOCOL_LADDER,
        )
    return Ok(value)
