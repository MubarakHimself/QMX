"""MUST NOT FLAG: documentation may name a placeholder; data may not be one.

A docstring that discusses the word ``placeholder`` or ``changeme`` is prose, and
a single sanctioned literal states its reason inline on its own line.
"""

from __future__ import annotations

# The directive is line-scoped: it exempts this line and nothing else.
UNSET_MARKER = "changeme"  # mock-data-scan: allow - the documented unset sentinel
