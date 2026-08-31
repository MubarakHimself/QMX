"""qma.daemon — sole QMA runtime and sole writer.

Structural seed only: module topology is present; this package starts no process
and writes no durable state (AR-Q05; DEC-0303). SemVer is display-only provenance
in lockstep with the QMF workspace (AR-Q11).
"""

from __future__ import annotations

__all__ = ["__version__"]

# Display-only provenance — never identity content (AR-Q11; DEC-0335).
__version__ = "0.1.0"
