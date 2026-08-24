"""Layer-2 conformance sandbox under QMB hosting (QL-8, AR-64).

QMB owns process spawning only by delegating to ``qml.host.runner.run_sandbox``.
Observations feed QML's pure verdict function unchanged — QMB never computes,
filters, or re-labels a Layer-2 verdict.
"""

from __future__ import annotations

from qmf.core.refusal import Result
from qml.conformance.layer2 import Layer2Verdict
from qml.host.runner import run_sandbox as _qml_run_sandbox

__all__ = ["run_sandbox"]


def run_sandbox(
    *,
    declaration: object,
    source_tree: object,
    factory_spec: object = None,
    assignment: object = None,
    state_scope: object,
    state_bound: object,
    timeout_seconds: object = None,
) -> Result[Layer2Verdict]:
    """Execute Layer 2 under QMB hosting; the QML verdict passes through unchanged."""
    return _qml_run_sandbox(
        declaration=declaration,
        source_tree=source_tree,
        factory_spec=factory_spec,
        assignment=assignment,
        state_scope=state_scope,
        state_bound=state_bound,
        timeout_seconds=timeout_seconds,
    )
