"""Conformance gate — pure contract surface (QL-8).

Layer 1 and Layer 2 verdicts are host-independent functions over in-memory
inputs. This module spawns no process, performs no I/O, and starts no thread;
hosts own sandbox execution and registration writes (DEC-0178, AD-15).
Conformance gates evidence citation and Book seats, never tunnel entry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from qmf.core.refusal import Ok, Result

from qml._refuse import invalid, policy

__all__ = [
    "CONFORMANCE_FORMAT_VERSION",
    "DENIAL_SET",
    "ConformanceTicket",
    "evaluate_ticket",
]

CONFORMANCE_FORMAT_VERSION: Final[int] = 1

# Capabilities a conformant bot may never exercise. Enforced later by AST/import
# scan and capability starvation; named here so the denial set is library-owned.
DENIAL_SET: Final[frozenset[str]] = frozenset({"clock", "io", "network", "undeclared_randomness"})


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
