"""qmb — the QMX experimentation/backtesting library plus the ``qmb`` CLI.

One uv-installable distribution (``import qmb``), an application-layer product
built on QMF, never a roster package. Imports the six backend QMF packages in
workspace lockstep; never ``qmf-venue``.

``__version__`` is display-only SemVer provenance and never enters ``fp1``
(DEC-0167). Identity lives on the resolved run-config fingerprint.
"""

from __future__ import annotations

from typing import Final

from qmb._backends import BACKEND_PACKAGES, backend_display_versions
from qmb._display import __version__, identity_payload
from qmb.config import LAYER_PRECEDENCE, fingerprint_layers, layers_identity
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

STRUCTURAL_SEED: Final[tuple[str, ...]] = (
    "runloop",
    "config",
    "registryread",
    "execution",
    "data",
    "optimize",
    "robustness",
    "results",
    "ledger",
    "orchestrator",
    "doors/cli",
    "doors/api",
    "doors/mcp",
)

__all__ = [
    "AS_OF_FORMAT_VERSION",
    "BACKEND_PACKAGES",
    "CLI_PIN_KEY",
    "CLI_PROG",
    "DATA_COMMANDS",
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
    "SPAWN_MODEL",
    "STALE_EVIDENCE_SEVERITY_KEY",
    "STATE_KIND",
    "STRUCTURAL_SEED",
    "SUBPHASES",
    "AsOfSet",
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
    "frontier_clock_name",
    "identity_payload",
    "ladder_identity",
    "layers_identity",
    "ledger_identity",
    "loop_identity",
    "orchestrator_identity",
    "port_home",
    "ports_identity",
    "read_port_identity",
    "result_identity",
    "sampler_identity",
]
