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
from qmb.registryread.library import (
    COMP_LIB_MINTED,
    KIND_OWNER,
    LIBRARY_KIND_NAMES,
    LIBRARY_KINDS,
    LIBRARY_KINDS_CLASS,
    LIBRARY_KINDS_OCCUPANCY,
    LIBRARY_MINTS_CT32,
    LIBRARY_MINTS_EXPERIMENT_SPEC,
    LOGIC_SOURCE_MANIFEST_CITES,
    NOT_LIBRARY_KIND_NAMES,
    QMX_LIBRARY_PACKAGE,
    STRATS_CORPUS,
    LibraryKind,
    LibraryKindRoster,
    enumerate_library_kinds,
    library_kinds_identity,
    register_library_kind,
)
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
    "COMP_LIB_MINTED",
    "FRAGMENT_CLASS",
    "HUB_KIND",
    "KIND_OWNER",
    "LIBRARY_KINDS",
    "LIBRARY_KINDS_CLASS",
    "LIBRARY_KINDS_OCCUPANCY",
    "LIBRARY_KIND_NAMES",
    "LIBRARY_MINTS_CT32",
    "LIBRARY_MINTS_EXPERIMENT_SPEC",
    "LOGIC_SOURCE_MANIFEST_CITES",
    "NOT_LIBRARY_KIND_NAMES",
    "POINTER_CLASS",
    "QMX_LIBRARY_PACKAGE",
    "STALE_EVIDENCE_SEVERITY_KEY",
    "STATE_KIND",
    "STRATS_CORPUS",
    "AsOfSet",
    "DatedPointer",
    "LibraryKind",
    "LibraryKindRoster",
    "PassiveHub",
    "RegistryCompletion",
    "RegistryFragment",
    "RegistryReadPort",
    "ResolvedRef",
    "SupersedesRef",
    "enumerate_library_kinds",
    "library_kinds_identity",
    "port_home",
    "read_port_identity",
    "register_library_kind",
]
