"""Thin Python API door — the same pure-function surface as ``import qmb`` (B-1).

In-process re-export for the UI backend and for research. No second cache,
no run-id of its own (DEC-0159).
"""

from __future__ import annotations

from qmb._backends import BACKEND_PACKAGES, backend_display_versions
from qmb._display import __version__, identity_payload
from qmb.config import LAYER_PRECEDENCE, fingerprint_layers, layers_identity
from qmb.data import DATA_COMMANDS, data_front_identity
from qmb.doors import CLI_PIN_KEY, CLI_PROG, MCP_SHIPPED
from qmb.execution import PORT_ROLES, ports_identity
from qmb.ledger import RUN_ROLES, ledger_identity
from qmb.optimize import SAMPLER_JOBS, SAMPLER_PIN_KEY, sampler_identity
from qmb.orchestrator import IMPURE_OWNER, SPAWN_MODEL, orchestrator_identity
from qmb.registryread import STATE_KIND, read_port_identity
from qmb.results import RESULT_CONTRACT, result_identity
from qmb.robustness import PROCEDURES, ladder_identity
from qmb.runloop import LOOP_KIND, SUBPHASES, frontier_clock_name, loop_identity

__all__ = [
    "BACKEND_PACKAGES",
    "CLI_PIN_KEY",
    "CLI_PROG",
    "DATA_COMMANDS",
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
    "STATE_KIND",
    "SUBPHASES",
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
    "ports_identity",
    "read_port_identity",
    "result_identity",
    "sampler_identity",
]
