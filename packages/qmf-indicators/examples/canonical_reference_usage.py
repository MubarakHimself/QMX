"""Reference usage — Story 7.2: the canonical arithmetic reference asserted at import
and mandatory wrapping (COMP-QMF-INDICATORS; CT-16; DEC-0127).

Executable::

    python packages/qmf-indicators/examples/canonical_reference_usage.py

Shows the four things Story 7.2 pins down:

1. Importing the package asserts the reference-configuration record of
   ``registry:canonical_indicator_reference`` (TA-Lib C 0.7.1 + Python wrapper 0.7.1);
   the result is reachable through ``reference_status()`` as a package-neutral value —
   the verified :class:`ArithmeticReference` when the reference installs, or an
   ``unavailable dependency`` refusal otherwise (never a raised import error).
2. Where the reference implements a formula, it is reference-owned — wrapping it is
   mandatory and canonical.
3. Where the reference does not implement a formula (volume-weighted, session-anchored,
   QMX-original), it is package-owned — this package's arithmetic is canonical.
4. The shipped ownership registry is conformant: no formula re-implements arithmetic the
   reference already owns, and no TA-Lib object crosses the public surface.
"""

from __future__ import annotations

from qmf.core import is_ok
from qmf.indicators import (
    FormulaOwnership,
    canonical_owner,
    ownership_conformance_defects,
    reference_status,
    resolve_canonical_arithmetic,
)


def main() -> None:
    # 1. The import-time assertion, as a package-neutral value.
    status = reference_status()
    if is_ok(status):
        reference = status.value
        print(f"reference asserted at import: verified {reference.python_wrapper}")
        print(f"reference config record: {dict(reference.reference_configuration)}")
    else:
        print(f"reference asserted at import: unavailable dependency ({status.context['field']})")

    # 2. A reference-owned formula names its mandatory wrap target.
    sma = canonical_owner("sma")
    assert is_ok(sma)
    print(f"sma ownership: {sma.value.ownership.value} (wraps {sma.value.reference_function})")

    # 3. A package-owned formula the reference does not implement.
    vwap = canonical_owner("vwap")
    assert is_ok(vwap)
    print(f"vwap ownership: {vwap.value.ownership.value} (package-canonical)")

    # Mandatory wrapping: a reference-owned formula resolves only against the verified
    # reference; a package-owned formula resolves regardless.
    resolved_vwap = resolve_canonical_arithmetic("vwap")
    assert is_ok(resolved_vwap)
    assert resolved_vwap.value.ownership is FormulaOwnership.PACKAGE
    print("vwap resolves without the reference: True")

    # 4. The shipped registry is conformant — one canonical owner per formula.
    defects = ownership_conformance_defects()
    print(f"ownership registry conformant: {defects == ()}")


if __name__ == "__main__":
    main()
