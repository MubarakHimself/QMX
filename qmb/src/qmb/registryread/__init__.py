"""Single library-owned registry-read port over immutable as-of sets (B-15).

Registry state reaches a machine as an immutable, fingerprinted as-of set of
records and fragments. Doors enumerate through this port; the compiler
resolves through it. No door-side or second cache exists (DEC-0165). The
hub is dumb passive storage — never the dead DEC-0084 central service.
"""

from __future__ import annotations

from qmb.registryread.as_of import (
    AS_OF_FORMAT_VERSION,
    FRAGMENT_CLASS,
    POINTER_CLASS,
    STATE_KIND,
    AsOfSet,
    DatedPointer,
    RegistryFragment,
    SupersedesRef,
)
from qmb.registryread.hub import HUB_KIND, PassiveHub
from qmb.registryread.port import (
    STALE_EVIDENCE_SEVERITY_KEY,
    RegistryCompletion,
    RegistryReadPort,
    ResolvedRef,
    port_home,
    read_port_identity,
)

__all__ = [
    "AS_OF_FORMAT_VERSION",
    "FRAGMENT_CLASS",
    "HUB_KIND",
    "POINTER_CLASS",
    "STALE_EVIDENCE_SEVERITY_KEY",
    "STATE_KIND",
    "AsOfSet",
    "DatedPointer",
    "PassiveHub",
    "RegistryCompletion",
    "RegistryFragment",
    "RegistryReadPort",
    "ResolvedRef",
    "SupersedesRef",
    "port_home",
    "read_port_identity",
]
