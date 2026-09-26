"""Story 10.1 — the Book (CT-22) and BMS (CT-27) definition containers.

A Book definition and a BMS definition are the two template artifacts the risk
module defines on ``qmf-core`` nouns (AD-29, AD-30; DEC-0143, DEC-0144). Both are
structured configuration artifacts under one grammar (:mod:`qmf.risk.grammar`):
declared sections, each a mapping of four-part :class:`~qmf.risk.grammar.TemplateVariable`.
This story lands the container shape, the USD-numeraire law, and identity — the
detailed ``admission_bar`` requirement grammar and the frozen-R ``money_rules``
semantics land in later stories.

Identity and versioning (AD-5, AD-10; DEC-0144, DEC-0158):

* a definition carries its own ``contract_format_version``; CT-22 understands
  format 1 and format 2 (DEC-0181) so pre-mint format-1 Books stay readable
  forever, while an unknown version — or a format-1 reader confronting format 2 —
  is an ``unsupported capability`` refusal, never a best-effort read;
* **unknown sections under a known format version are ignored** — they never enter
  identity, so a future section a reader does not recognise cannot fork meaning;
* a Book definition declares ``accounting_currency`` (USD in V1; a non-USD value is
  a ``policy rejection``, AD-40);
* the definition's ``fp1`` is the ``fp1`` over its canonical content — the version
  identity a binding (CT-28, a later story) cites, never a version string — so a
  changed number changes ``fp1`` hence a new identity, and
  :func:`~qmf.risk.versioning.diff_variable_maps` derives the diff between two
  versions over :meth:`BookDefinition.flat_variables`.

Records reach ``qmf-registry`` only through the composition root under the injected
-sink pattern; nothing imports ``qmf.risk`` and ``qmf.risk`` imports only
``qmf-core`` (default-deny, L30/DEC-0120). Ratified ``defined-unwired`` surface —
no wiring is authorized here (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Ok, Result, TypedRefusal, fingerprint, is_refusal
from qmf.risk._common import coerce_contract_format_version, invalid, unsupported
from qmf.risk.grammar import TemplateSection, TemplateVariable
from qmf.risk.numeraire import validate_accounting_currency

__all__ = [
    "BMS_CONTRACT_FORMAT_VERSION",
    "BMS_SECTIONS",
    "BOOK_CONTRACT_FORMAT_VERSION",
    "BOOK_FORMAT_VERSION_1",
    "BOOK_KNOWN_FORMAT_VERSIONS",
    "BOOK_SECTIONS",
    "BmsDefinition",
    "BookDefinition",
]

# CT-22 sits at contract format version 2 (the AD-5 QML mint, DEC-0181). Format 1
# is the pre-mint first version and stays readable forever; this build understands
# both. Pinning format 2 alone and refusing format 1 is a defect (Story 11.7).
# CT-27 remains at its first minted format version 1 (AD-29/30/32).
BOOK_FORMAT_VERSION_1: Final[int] = 1
BOOK_CONTRACT_FORMAT_VERSION: Final[int] = 2
BOOK_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset(
    {BOOK_FORMAT_VERSION_1, BOOK_CONTRACT_FORMAT_VERSION}
)
BMS_CONTRACT_FORMAT_VERSION: Final[int] = 1

# The ten declared Book sections, canonically named (CT-22; DEC-0144). Unknown
# sections under this known format version are ignored — they never enter identity.
BOOK_SECTIONS: Final[tuple[str, ...]] = (
    "charter",
    "footprint_requirements",
    "money_rules",
    "admission_bar",
    "leash_grammar",
    "capacity_and_sweep",
    "exit_policy",
    "control_policy",
    "protection_windows",
    "paper",
)

# The declared BMS sections (CT-27; DEC-0144).
BMS_SECTIONS: Final[tuple[str, ...]] = (
    "charter",
    "accounting_rules",
    "constraints",
    "control_rank_table",
    "ksa_policy",
    "reporting",
    "admission_bar",
)


def _coerce_format_version(field: str, value: object, expected: int) -> int | None:
    """Return ``value`` as the expected format version, or ``None`` on mismatch.

    A bool (an int subclass) is not a version; a non-int or a version other than the
    one this build understands returns ``None`` — the caller turns that into an
    ``unsupported capability`` refusal (an unknown version is never best-effort read).
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value != expected:
        return None
    return value


def _coerce_sections(
    sections: object, known: tuple[str, ...]
) -> dict[str, TemplateSection] | TypedRefusal:
    """Resolve the KNOWN sections of a template, ignoring unknown ones.

    Returns a name-keyed dict of the recognised :class:`TemplateSection` values, or
    the ``TypedRefusal`` to return. ``sections`` must be a mapping whose values are
    :class:`TemplateSection` with matching keys; unknown section names are dropped
    (ignored under a known format version), so they never enter identity.
    """
    if not isinstance(sections, Mapping):
        return invalid(
            "sections",
            "a template's sections are a name-keyed mapping of TemplateSection",
            given=repr(type(sections).__name__),
        )
    section_map = cast("Mapping[object, object]", sections)
    known_set = frozenset(known)
    resolved: dict[str, TemplateSection] = {}
    for key, section in section_map.items():
        if not isinstance(key, str):
            return invalid("sections", "a section key is a string", given=repr(key))
        if not isinstance(section, TemplateSection):
            return invalid(
                "sections", "each section is a TemplateSection", key=key, given=repr(section)
            )
        if section.name != key:
            return invalid(
                "sections",
                "a section's key must equal its declared name",
                key=key,
                section_name=section.name,
            )
        if key not in known_set:
            # Unknown section under a known format version: ignored, never refused
            # and never entered into identity (DEC-0144).
            continue
        resolved[key] = section
    return resolved


def _flatten(sections: Mapping[str, TemplateSection]) -> dict[str, TemplateVariable]:
    """Flatten a definition's variables to ``"section.variable" -> variable``.

    The keying is ``section.variable`` so two sections may each declare a variable
    of the same short name without colliding in the diff.
    """
    flat: dict[str, TemplateVariable] = {}
    for section_name, section in sections.items():
        for variable_name, variable in section.variables.items():
            flat[f"{section_name}.{variable_name}"] = variable
    return flat


@dataclass(frozen=True, slots=True)
class BookDefinition:
    """A Book VERSION — the CT-22 template content, identified by its ``fp1``.

    Carries the ``contract_format_version``, the declared ``accounting_currency``
    (USD in V1), and the recognised template sections. Two Books with different
    numbers have different fingerprints — a changed number changes ``fp1`` hence a
    new Book identity (DEC-0144).
    """

    contract_format_version: int
    accounting_currency: str
    sections: Mapping[str, TemplateSection]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", MappingProxyType(dict(self.sections)))

    @classmethod
    def try_create(
        cls,
        contract_format_version: object,
        accounting_currency: object,
        sections: object,
        *,
        reader_format_version: object = BOOK_CONTRACT_FORMAT_VERSION,
    ) -> Result[BookDefinition]:
        """Validate and build a :class:`BookDefinition`, returning value-or-refusal.

        This build understands format 1 and format 2 (DEC-0181). A format-2 reader
        (the default) accepts pre-mint format-1 Books unchanged. A format-1 reader
        (``reader_format_version=1``) confronting a format-2 artifact refuses
        ``unsupported capability``, never a best-effort read. An unknown version is
        likewise ``unsupported capability``. Unknown section names are ignored, not
        refused.
        """
        version = coerce_contract_format_version(
            contract_format_version,
            known=BOOK_KNOWN_FORMAT_VERSIONS,
            reader_format_version=reader_format_version,
        )
        if isinstance(version, TypedRefusal):
            return version
        currency = validate_accounting_currency(accounting_currency)
        if is_refusal(currency):
            return currency
        resolved_sections = _coerce_sections(sections, BOOK_SECTIONS)
        if isinstance(resolved_sections, TypedRefusal):
            return resolved_sections
        return Ok(
            cls(
                contract_format_version=version,
                accounting_currency=currency.value,
                sections=resolved_sections,
            )
        )

    def flat_variables(self) -> Mapping[str, TemplateVariable]:
        """Every declared variable, keyed ``section.variable`` — the diff surface."""
        return MappingProxyType(_flatten(self.sections))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the Book VERSION identity.

        Only the recognised sections enter identity (unknown ones are ignored). The
        canonical serializer sorts keys at every depth, so section and variable
        declaration order never forks the fingerprint.
        """
        return {
            "class": "book-definition",
            "contract_format_version": self.contract_format_version,
            "accounting_currency": self.accounting_currency,
            "sections": {name: section.fp1_identity() for name, section in self.sections.items()},
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The Book definition's ``fp1`` over its canonical content (CT-05; DEC-0158).

        This is the version identity a binding (CT-28) cites, never a version string.
        """
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class BmsDefinition:
    """A BMS VERSION — the CT-27 template content, identified by its ``fp1``.

    The account-facing supervising layer's template, under the same grammar as the
    Book definition. Carries the ``contract_format_version`` and the recognised BMS
    sections; the numeraire is declared inside ``accounting_rules`` as an ordinary
    variable. A ``BmsInstanceId`` is content-derived from this fingerprint at bind
    time (a later story) — this container carries the VERSION identity (DEC-0143).
    """

    contract_format_version: int
    sections: Mapping[str, TemplateSection]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", MappingProxyType(dict(self.sections)))

    @classmethod
    def try_create(cls, contract_format_version: object, sections: object) -> Result[BmsDefinition]:
        """Validate and build a :class:`BmsDefinition`, returning value-or-refusal.

        Refuses an unknown ``contract_format_version`` (``unsupported capability``)
        and ill-typed sections; unknown section names are ignored, not refused.
        """
        version = _coerce_format_version(
            "contract_format_version", contract_format_version, BMS_CONTRACT_FORMAT_VERSION
        )
        if version is None:
            return unsupported(
                "contract_format_version",
                "a BMS definition's contract format version is not one this build "
                "understands; an unknown version is never best-effort read",
                given=repr(contract_format_version),
                understood=BMS_CONTRACT_FORMAT_VERSION,
            )
        resolved_sections = _coerce_sections(sections, BMS_SECTIONS)
        if isinstance(resolved_sections, TypedRefusal):
            return resolved_sections
        return Ok(cls(contract_format_version=version, sections=resolved_sections))

    def flat_variables(self) -> Mapping[str, TemplateVariable]:
        """Every declared variable, keyed ``section.variable`` — the diff surface."""
        return MappingProxyType(_flatten(self.sections))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the BMS VERSION identity."""
        return {
            "class": "bms-definition",
            "contract_format_version": self.contract_format_version,
            "sections": {name: section.fp1_identity() for name, section in self.sections.items()},
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The BMS definition's ``fp1`` over its canonical content (CT-05; DEC-0158)."""
        return fingerprint(self.fp1_identity())
