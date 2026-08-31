"""qma.wire — sole cross-boundary contract package.

Envelope, command/query/event families, and protocol version. Owns no client
implementation and no alternate cross-boundary contract (DEC-0304; AR-Q04).
SemVer is display-only provenance in lockstep with the QMF workspace (AR-Q11).
"""

from __future__ import annotations

__all__ = ["__version__"]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
