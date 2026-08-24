"""Conformance gate — pure contract surface (QL-8).

Layer 1 and Layer 2 verdicts are host-independent functions over in-memory
inputs. This module spawns no process, performs no I/O, and starts no thread;
hosts own sandbox execution and registration writes (DEC-0178, AD-15).
Conformance gates evidence citation and Book seats, never tunnel entry.
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core.refusal import Ok, Result

from qml._refuse import invalid, policy
from qml.conformance.contract import (
    CONFORMANCE_CONTRACT_CLASS,
    CONFORMANCE_FORMAT_VERSION,
    CONFORMANCE_KNOWN_FORMAT_VERSIONS,
    CONFORMANCE_LADDER,
    DENIAL_SET,
    LAYER2_CHECKS,
    conformance_contract_identity,
)
from qml.conformance.harness import (
    INTENT_KIND_ENTRY,
    drive_golden_slice,
    intent_kind,
    intent_trace_kinds,
    traces_equal,
)
from qml.conformance.layer1 import LAYER1_CHECKS, Layer1Verdict, lint_declaration
from qml.conformance.layer2 import (
    Layer2Observations,
    Layer2Verdict,
    collect_layer2_observations,
    evaluate_layer2,
    run_layer2_suite,
)
from qml.conformance.scan import (
    AST_SCAN_RULES_CLASS,
    DENIED_CALL_SUFFIXES,
    DENIED_IMPORTS,
    DENIED_NAME_CALLS,
    ScanFinding,
    ScanReport,
    ast_scan_rules_identity,
    scan_logic_source,
)
from qml.conformance.slice import (
    GOLDEN_SLICE_CLASS,
    GOLDEN_SLICE_INSTANT_COUNT,
    GOLDEN_SLICE_ORIGIN_NS,
    GoldenSlice,
    generate_golden_slice,
    read_surfaces_for_slice,
)

__all__ = [
    "AST_SCAN_RULES_CLASS",
    "CONFORMANCE_CONTRACT_CLASS",
    "CONFORMANCE_FORMAT_VERSION",
    "CONFORMANCE_KNOWN_FORMAT_VERSIONS",
    "CONFORMANCE_LADDER",
    "DENIAL_SET",
    "DENIED_CALL_SUFFIXES",
    "DENIED_IMPORTS",
    "DENIED_NAME_CALLS",
    "GOLDEN_SLICE_CLASS",
    "GOLDEN_SLICE_INSTANT_COUNT",
    "GOLDEN_SLICE_ORIGIN_NS",
    "INTENT_KIND_ENTRY",
    "LAYER1_CHECKS",
    "LAYER2_CHECKS",
    "ConformanceTicket",
    "GoldenSlice",
    "Layer1Verdict",
    "Layer2Observations",
    "Layer2Verdict",
    "ScanFinding",
    "ScanReport",
    "ast_scan_rules_identity",
    "collect_layer2_observations",
    "conformance_contract_identity",
    "drive_golden_slice",
    "evaluate_layer2",
    "evaluate_ticket",
    "generate_golden_slice",
    "intent_kind",
    "intent_trace_kinds",
    "lint_declaration",
    "read_surfaces_for_slice",
    "run_layer2_suite",
    "scan_logic_source",
    "traces_equal",
]


@dataclass(frozen=True, slots=True)
class ConformanceTicket:
    """Passed both layers. Cited by governed evidence and seats; not tunnel entry."""

    layer1_passed: bool
    layer2_passed: bool


def evaluate_ticket(*, layer1_passed: object, layer2_passed: object) -> Result[ConformanceTicket]:
    """Pure verdict: mint a ticket only when both layers passed (DEC-0178).

    A failed layer is a ``policy rejection`` — the Bot kind mints only on a full
    pass; there is no partial or probationary registration.
    """
    if not isinstance(layer1_passed, bool) or not isinstance(layer2_passed, bool):
        return invalid(
            "layers",
            "each conformance layer verdict is a bool",
            layer1_passed=repr(layer1_passed),
            layer2_passed=repr(layer2_passed),
        )
    if layer1_passed and layer2_passed:
        return Ok(ConformanceTicket(layer1_passed=True, layer2_passed=True))
    return policy(
        "conformance",
        "the Bot kind mints only for artifacts passing both layers; conformance "
        "never gates tunnel entry",
        layer1_passed=layer1_passed,
        layer2_passed=layer2_passed,
    )
