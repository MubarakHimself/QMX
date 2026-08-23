"""Tiny import example — `import qml` (COMP-QML).

Executable::

    python qml/examples/import_usage.py

Shows the scaffold surface: display-only SemVer, an opaque strategy-family key,
and the pure conformance ticket. A plain-Python bot needs none of this to run.
"""

from __future__ import annotations

from qmf.core.refusal import is_ok
from qml.conformance import evaluate_ticket
from qml.families import StrategyFamilyId
from qml.protocol import permitted_exit_kinds

import qml


def main() -> None:
    print(f"qml {qml.__version__}")
    family = StrategyFamilyId.try_create("trend-follow")
    assert is_ok(family)
    kinds = permitted_exit_kinds(())
    assert is_ok(kinds)
    ticket = evaluate_ticket(layer1_passed=True, layer2_passed=True)
    assert is_ok(ticket)
    print("import qml ok")


if __name__ == "__main__":
    main()
