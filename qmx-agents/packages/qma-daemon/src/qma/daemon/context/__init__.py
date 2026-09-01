"""Context Compiler and compaction seam (AD-14; FR-Q53).

The default compiler inserts daemon-resolved handle *references* only.
Handle contents never enter a context window.
"""

from __future__ import annotations

from qma.daemon.context.compiler import DefaultContextCompiler

__all__ = ["DefaultContextCompiler"]
