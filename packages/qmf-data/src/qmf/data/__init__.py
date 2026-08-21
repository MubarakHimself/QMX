"""qmf.data — evidence rooms, splits, journals, and backups.

Roster package of the QMF V1 uv workspace. Scaffold: this module declares the
package identity and version only; its public contracts (the CT-* surface) land
in later stories. Nothing here reaches across a sibling boundary — the
default-deny dependency direction (L30) is preserved by construction.
"""

from __future__ import annotations

__all__ = ["__version__"]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
