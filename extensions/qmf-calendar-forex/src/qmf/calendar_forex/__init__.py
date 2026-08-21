"""qmf.calendar_forex — forex market-hours calendar extension.

Off-roster extension of the QMF V1 uv workspace, on its own SemVer ladder.
Scaffold: this module declares the package identity and version only; its public
contracts (the CT-02 calendar-provider surface, TZPATH pinning, tzdb
verification) land in later stories. It depends only on qmf-core.
"""

from __future__ import annotations

__all__ = ["__version__"]

# Own SemVer ladder (off-roster extension), independent of roster lockstep.
# Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
