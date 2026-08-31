"""qma.wire — sole cross-boundary contract package.

Envelope, command/query/event families, protocol version, and the closed-and-
addable ``host_request`` verb set. Owns no client implementation and no
alternate cross-boundary contract (DEC-0304; AR-Q04). SemVer is display-only
provenance in lockstep with the QMF workspace (AR-Q11).
"""

from __future__ import annotations

from qma.wire.host_request import (
    HOST_REQUEST_OWNING_AD,
    HOST_REQUEST_VERBS,
    HOST_REQUEST_VOCABULARY_OWNER,
    HostRequestVerbError,
    parse_host_request_verb,
)

__all__ = [
    "HOST_REQUEST_OWNING_AD",
    "HOST_REQUEST_VERBS",
    "HOST_REQUEST_VOCABULARY_OWNER",
    "HostRequestVerbError",
    "__version__",
    "parse_host_request_verb",
]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
