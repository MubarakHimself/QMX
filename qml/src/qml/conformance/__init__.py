"""Conformance gate — pure contract surface (QL-8).

Layer 1 and Layer 2 verdicts are host-independent functions over in-memory
inputs. This module spawns no process, performs no I/O, and starts no thread;
hosts own sandbox execution and registration writes (DEC-0178, AD-15).
Conformance gates evidence citation and Book seats, never tunnel entry.
"""

from __future__ import annotations

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
from qml.conformance.prediction import (
    PREDICTION_CHECKS,
    PredictionBindingContext,
    PredictionVerdict,
    lint_prediction,
    stream_set_required_capabilities,
)
from qml.conformance.registration import (
    CITATION_KINDS,
    DROPPED_REGISTRATION_GATES,
    PROMOTED_FROM_EDGE_TYPE,
    BotCitation,
    CitationKind,
    ConformanceTicket,
    Graduation,
    GraduationEdge,
    RegistrationCandidate,
    UngovernedTunnelAccess,
    admit_ungoverned_tunnel,
    cite_registered_bot,
    cite_ungoverned_bot,
    evaluate_ticket,
    gate_registration,
    graduate_to_governed,
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
    "CITATION_KINDS",
    "CONFORMANCE_CONTRACT_CLASS",
    "CONFORMANCE_FORMAT_VERSION",
    "CONFORMANCE_KNOWN_FORMAT_VERSIONS",
    "CONFORMANCE_LADDER",
    "DENIAL_SET",
    "DENIED_CALL_SUFFIXES",
    "DENIED_IMPORTS",
    "DENIED_NAME_CALLS",
    "DROPPED_REGISTRATION_GATES",
    "GOLDEN_SLICE_CLASS",
    "GOLDEN_SLICE_INSTANT_COUNT",
    "GOLDEN_SLICE_ORIGIN_NS",
    "INTENT_KIND_ENTRY",
    "LAYER1_CHECKS",
    "LAYER2_CHECKS",
    "PREDICTION_CHECKS",
    "PROMOTED_FROM_EDGE_TYPE",
    "BotCitation",
    "CitationKind",
    "ConformanceTicket",
    "GoldenSlice",
    "Graduation",
    "GraduationEdge",
    "Layer1Verdict",
    "Layer2Observations",
    "Layer2Verdict",
    "PredictionBindingContext",
    "PredictionVerdict",
    "RegistrationCandidate",
    "ScanFinding",
    "ScanReport",
    "UngovernedTunnelAccess",
    "admit_ungoverned_tunnel",
    "ast_scan_rules_identity",
    "cite_registered_bot",
    "cite_ungoverned_bot",
    "collect_layer2_observations",
    "conformance_contract_identity",
    "drive_golden_slice",
    "evaluate_layer2",
    "evaluate_ticket",
    "gate_registration",
    "generate_golden_slice",
    "graduate_to_governed",
    "intent_kind",
    "intent_trace_kinds",
    "lint_declaration",
    "lint_prediction",
    "read_surfaces_for_slice",
    "run_layer2_suite",
    "scan_logic_source",
    "stream_set_required_capabilities",
    "traces_equal",
]
