"""Story 10.1 — the USD numeraire and Book-limit unit law (COMP-QMF-RISK).

The numeraire is **USD system-wide in V1** (AD-40; DEC-0154). A Book charter still
declares ``accounting_currency`` so a later currency is a version change, but in V1
that declaration must be USD: no rate source is ratified, and a silent conversion
is the one error no report shows, so binding to another settlement currency is a
``policy rejection`` — the conversion seam ships and switches on only when a source
is ruled. USD is the ratified numeraire declaration (a per-Book accounting
declaration, ``configurable: false`` in the variables registry), not a risk number.

Book-level limits are expressed **only in R or in notional in the Book's
numeraire** (AD-40; DEC-0154): a limit stated in an instrument-native quantity
(lots) is a ``policy rejection`` at template validation, and a notional limit in a
currency other than the numeraire needs a QMX-side conversion and is a ``policy
rejection`` until a rate source is ratified. A venue-derived notional or margin
figure is legal only as settlement evidence under a declared ``converted_by =
venue`` provenance flag (out of scope here — this module validates *template*
limits, not settlement evidence).

Imports only ``qmf-core``; nothing imports ``qmf.risk`` (default-deny,
L30/DEC-0120). Ratified ``defined-unwired`` surface.
"""

from __future__ import annotations

from typing import Final

from qmf.core import Ok, Result, UnitKind
from qmf.risk._common import clean_str, coerce_enum, invalid, policy

__all__ = [
    "BOOK_LIMIT_UNIT_KINDS",
    "V1_NUMERAIRE",
    "validate_accounting_currency",
    "validate_book_limit",
]

# The sole V1 numeraire, system-wide (AD-40; DEC-0154; variables registry
# ``numeraire = USD``, ``configurable: false``). A later currency is a version
# change, not a runtime switch.
V1_NUMERAIRE: Final[str] = "USD"

# The only unit-kinds a Book-level limit may be stated in: an ``r-multiple`` (a
# pure-R limit) or ``money(numeraire)`` (a notional limit in the numeraire). Any
# other — most pointedly ``quantity(unit)`` (lots) — is a policy rejection
# (DEC-0154).
BOOK_LIMIT_UNIT_KINDS: Final[frozenset[UnitKind]] = frozenset({UnitKind.R_MULTIPLE, UnitKind.MONEY})


def validate_accounting_currency(value: object) -> Result[str]:
    """Validate a Book/BMS ``accounting_currency`` declaration (AD-40; DEC-0154).

    The field is mandatory: a missing or blank/non-string value is ``invalid
    input``. In V1 it must be the USD numeraire; a well-formed non-USD currency is a
    ``policy rejection`` — no rate source is ratified, so binding to another
    settlement currency is refused rather than silently converted. Returns the
    validated currency tag (``"USD"``) on success.
    """
    token = clean_str(value)
    if token is None:
        return invalid(
            "accounting_currency",
            "accounting_currency is a mandatory non-empty currency tag",
            given=repr(value),
        )
    if token != V1_NUMERAIRE:
        return policy(
            "accounting_currency",
            "the V1 numeraire is USD system-wide; a non-USD accounting currency needs a "
            "ratified rate source and is refused until one is ruled (no silent conversion)",
            given=token,
            numeraire=V1_NUMERAIRE,
        )
    return Ok(token)


def validate_book_limit(unit_kind: object, currency: object = None) -> Result[UnitKind]:
    """Validate the unit a Book-level limit is stated in (AD-40; DEC-0154).

    A limit in ``r-multiple`` is always legal. A limit in ``money`` (a notional
    limit) is legal only in the numeraire (USD); another currency needs a QMX-side
    conversion and is a ``policy rejection`` until a rate source is ratified. A
    limit in ``quantity(unit)`` (lots) is a ``policy rejection`` at template
    validation — Book limits are never instrument-native. Any other unit-kind is a
    ``policy rejection`` (only R or numeraire-notional express a Book limit). An
    unrecognised unit-kind is ``invalid input``. Returns the validated unit-kind.
    """
    resolved = coerce_enum(UnitKind, unit_kind)
    if resolved is None:
        return invalid(
            "unit_kind",
            "a Book-level limit declares a unit-kind from the closed AD-40 vocabulary",
            given=repr(unit_kind),
            allowed=[member.value for member in UnitKind],
        )
    if resolved is UnitKind.QUANTITY:
        return policy(
            "unit_kind",
            "a Book-level limit stated in an instrument-native quantity (lots) is a policy "
            "rejection at template validation; Book limits are expressed only in R or in "
            "notional in the numeraire",
            given=resolved.value,
        )
    if resolved is UnitKind.MONEY:
        token = clean_str(currency)
        if token is None:
            return invalid(
                "currency",
                "a notional Book limit declares its currency",
                given=repr(currency),
            )
        if token != V1_NUMERAIRE:
            return policy(
                "currency",
                "a notional Book limit in a non-numeraire currency needs a QMX-side "
                "conversion and is a policy rejection until a rate source is ratified",
                given=token,
                numeraire=V1_NUMERAIRE,
            )
        return Ok(resolved)
    if resolved is UnitKind.R_MULTIPLE:
        return Ok(resolved)
    return policy(
        "unit_kind",
        "a Book-level limit is expressed only in R (r-multiple) or in notional in the "
        "numeraire (money); this unit-kind may not express a limit",
        given=resolved.value,
        allowed=[member.value for member in BOOK_LIMIT_UNIT_KINDS],
    )
