"""Thin Python API door — the same pure-function surface as ``import qmb`` (B-1).

In-process re-export for the UI backend and for research. No second cache,
no run-id of its own (DEC-0159).
"""

from __future__ import annotations

from qmb._backends import BACKEND_PACKAGES, backend_display_versions
from qmb._display import __version__, identity_payload
from qmb.config import (
    BMS_NAMESPACES,
    BMS_RECORD_KIND,
    BOOK_NAMESPACES,
    BOOK_RECORD_KIND,
    CONFIG_FRAGMENT_CLASS,
    FRAGMENT_FORMAT_VERSION,
    FRAGMENT_FORMAT_VERSION_1,
    FRAGMENT_KNOWN_FORMAT_VERSIONS,
    FRAGMENT_LINEAGE_EDGE_TYPE,
    LAYER_PRECEDENCE,
    SOURCE_BMS,
    SOURCE_BOOK,
    SOURCE_PRESET,
    ConfigFragment,
    fingerprint_layers,
    fragment_identity,
    layers_identity,
    materialize_bms_fragment,
    materialize_book_fragment,
    materialize_condition_preset,
)
from qmb.data import DATA_COMMANDS, data_front_identity
from qmb.doors import CLI_PIN_KEY, CLI_PROG, MCP_SHIPPED
from qmb.execution import PORT_ROLES, ports_identity
from qmb.ledger import RUN_ROLES, ledger_identity
from qmb.optimize import SAMPLER_JOBS, SAMPLER_PIN_KEY, sampler_identity
from qmb.orchestrator import IMPURE_OWNER, SPAWN_MODEL, orchestrator_identity
from qmb.registryread import (
    AS_OF_FORMAT_VERSION,
    HUB_KIND,
    STALE_EVIDENCE_SEVERITY_KEY,
    STATE_KIND,
    AsOfSet,
    DatedPointer,
    PassiveHub,
    RegistryFragment,
    RegistryReadPort,
    ResolvedRef,
    SupersedesRef,
    port_home,
    read_port_identity,
)
from qmb.results import RESULT_CONTRACT, result_identity
from qmb.robustness import PROCEDURES, ladder_identity
from qmb.runloop import LOOP_KIND, SUBPHASES, frontier_clock_name, loop_identity

__all__ = [
    "AS_OF_FORMAT_VERSION",
    "BACKEND_PACKAGES",
    "BMS_NAMESPACES",
    "BMS_RECORD_KIND",
    "BOOK_NAMESPACES",
    "BOOK_RECORD_KIND",
    "CLI_PIN_KEY",
    "CLI_PROG",
    "CONFIG_FRAGMENT_CLASS",
    "DATA_COMMANDS",
    "FRAGMENT_FORMAT_VERSION",
    "FRAGMENT_FORMAT_VERSION_1",
    "FRAGMENT_KNOWN_FORMAT_VERSIONS",
    "FRAGMENT_LINEAGE_EDGE_TYPE",
    "HUB_KIND",
    "IMPURE_OWNER",
    "LAYER_PRECEDENCE",
    "LOOP_KIND",
    "MCP_SHIPPED",
    "PORT_ROLES",
    "PROCEDURES",
    "RESULT_CONTRACT",
    "RUN_ROLES",
    "SAMPLER_JOBS",
    "SAMPLER_PIN_KEY",
    "SOURCE_BMS",
    "SOURCE_BOOK",
    "SOURCE_PRESET",
    "SPAWN_MODEL",
    "STALE_EVIDENCE_SEVERITY_KEY",
    "STATE_KIND",
    "SUBPHASES",
    "AsOfSet",
    "ConfigFragment",
    "DatedPointer",
    "PassiveHub",
    "RegistryFragment",
    "RegistryReadPort",
    "ResolvedRef",
    "SupersedesRef",
    "__version__",
    "backend_display_versions",
    "data_front_identity",
    "fingerprint_layers",
    "fragment_identity",
    "frontier_clock_name",
    "identity_payload",
    "ladder_identity",
    "layers_identity",
    "ledger_identity",
    "loop_identity",
    "materialize_bms_fragment",
    "materialize_book_fragment",
    "materialize_condition_preset",
    "orchestrator_identity",
    "port_home",
    "ports_identity",
    "read_port_identity",
    "result_identity",
    "sampler_identity",
]
