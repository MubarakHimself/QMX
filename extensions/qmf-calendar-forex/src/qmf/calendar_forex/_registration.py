"""Named composition-root registration for the forex-17NY calendar (AD-2 / Story 4.3).

The application composition root calls :func:`register_forex_17ny` explicitly —
the single public registration surface. Discovery by ambient package scanning,
setuptools/pkg entry points, or ``pkgutil`` walk is not supported and must never
be added.

Distribution identity + version participate in downstream fingerprints alongside
the calendar rule set and pinned IANA tzdata, via ``qmf.core.fingerprint``. Binding
(which venues or accounts use the calendar) is a separate field and never enters
identity. A tzdata pin change yields a new ``CalendarIdentity``; old artifacts are
never rewritten — :func:`describe_tzdata_pin_lineage` describes the supersedes edge
for the composition root to record (no ``qmf-registry`` dependency here).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from qmf.calendar_forex import _tzdb
from qmf.calendar_forex._provider import Forex17NYCalendar
from qmf.core.chrono import CalendarIdentity
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
)

# Distribution identity (AD-2): identity fields of every artifact this extension
# produces. Must stay identical to the installable distribution name / SemVer.
DISTRIBUTION_NAME: str = "qmf-calendar-forex"
# Keep identical to pyproject.toml ``version`` and the package ``__version__``.
DISTRIBUTION_VERSION: str = "0.1.0"

# Identity-content format version for this extension's downstream fingerprint
# recipe. Meaning never mutates — an incompatible change mints the next integer.
ARTIFACT_IDENTITY_FORMAT_VERSION: int = 1

# CT-07 supersedes edge type name — described here as plain content; the
# composition root hands it to qmf-registry. This package never imports registry.
_SUPERSEDES_EDGE_TYPE: str = "supersedes"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class CalendarBinding:
    """Which venues or accounts use a calendar — separate from rule-set identity.

    Binding never participates in fingerprints (DEC-0106). A venue/account change
    that does not change the rule set leaves derived-artifact identity unchanged.
    """

    venue_ids: tuple[str, ...] = ()
    account_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ForexCalendarRegistration:
    """Composition-root handle returned by :func:`register_forex_17ny`.

    Carries the ready CT-02 provider, the verified ``CalendarIdentity``, the
    extension's distribution identity + version (identity fields per AD-2), and an
    optional :class:`CalendarBinding` that is deliberately excluded from fp1.
    """

    provider: Forex17NYCalendar
    calendar_identity: CalendarIdentity
    distribution_name: str
    distribution_version: str
    binding: CalendarBinding

    def fp1_identity(self) -> dict[str, object]:
        """Downstream artifact identity content for ``qmf.core.fingerprint``.

        Distribution name + version ride alongside the calendar rule set and IANA
        tzdata. Binding is omitted by design.
        """
        return {
            "class": "calendar-extension-artifact",
            "distribution": self.distribution_name,
            "distribution_version": self.distribution_version,
            "calendar": self.calendar_identity.fp1_identity(),
            "format_version": ARTIFACT_IDENTITY_FORMAT_VERSION,
        }

    def artifact_fingerprint(self) -> Result[Fingerprint]:
        """Fingerprint of this registration's downstream identity via qmf-core."""
        return fingerprint(self)

    def with_binding(self, binding: CalendarBinding) -> ForexCalendarRegistration:
        """Return a copy with a different binding — identity content unchanged."""
        return replace(self, binding=binding)


@dataclass(frozen=True, slots=True)
class TzdataPinLineageEdge:
    """Plain description of a supersedes edge for a tzdata pin change (AD-5).

    The composition root records this through qmf-registry; this extension never
    imports registry and never rewrites the superseded artifact. Endpoints are
    calendar-identity fingerprints (rule set + tzdata), so a pin change surfaces
    as a new identity rather than a silent equality.
    """

    edge_type: str
    from_ref: Fingerprint
    to_ref: Fingerprint
    reason: str
    old_tzdata_version: str
    new_tzdata_version: str

    def fp1_identity(self) -> dict[str, object]:
        """Identity content describing the lineage edge (for optional fingerprinting)."""
        return {
            "class": "tzdata-pin-lineage-edge",
            "edge_type": self.edge_type,
            "from_ref": self.from_ref.value,
            "to_ref": self.to_ref.value,
            "reason": self.reason,
            "old_tzdata_version": self.old_tzdata_version,
            "new_tzdata_version": self.new_tzdata_version,
            "format_version": ARTIFACT_IDENTITY_FORMAT_VERSION,
        }


def register_forex_17ny(
    *,
    binding: CalendarBinding | None = None,
    distribution_version: object | None = None,
) -> Result[ForexCalendarRegistration]:
    """Named composition-root registration surface for forex-17NY.

    Call this explicitly from the application composition root. Do not discover
    this extension via ambient scanning, entry points, or ``pkgutil``.
    """
    if not _tzdb.provider_ready or _tzdb.calendar_identity is None:
        if is_ok(_tzdb.tzdb_verification):
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.NO,
                context={
                    "field": "provider",
                    "reason": "forex-17NY provider is not ready; tzdb pin was not verified",
                },
            )
        return _tzdb.tzdb_verification

    version: object = DISTRIBUTION_VERSION if distribution_version is None else distribution_version
    if not isinstance(version, str) or not version.strip():
        return _invalid(
            "distribution_version",
            "distribution version is a non-empty SemVer string and rides into "
            "downstream fingerprints (AD-2)",
            given=repr(distribution_version),
        )
    identity = _tzdb.calendar_identity
    return Ok(
        ForexCalendarRegistration(
            provider=Forex17NYCalendar(identity=identity),
            calendar_identity=identity,
            distribution_name=DISTRIBUTION_NAME,
            distribution_version=version.strip(),
            binding=binding if binding is not None else CalendarBinding(),
        )
    )


def describe_tzdata_pin_lineage(
    previous: object,
    current: object,
) -> Result[TzdataPinLineageEdge]:
    """Describe a supersedes lineage edge for a tzdata pin change.

    Returns plain edge content the composition root records — never rewrites the
    previous artifact, and never imports qmf-registry. Both identities must share
    the same rule set; only the pinned tzdata version may differ.
    """
    if not isinstance(previous, CalendarIdentity):
        return _invalid(
            "previous",
            "describe_tzdata_pin_lineage takes a CalendarIdentity",
            given=repr(previous),
        )
    if not isinstance(current, CalendarIdentity):
        return _invalid(
            "current",
            "describe_tzdata_pin_lineage takes a CalendarIdentity",
            given=repr(current),
        )
    if previous.rule_set != current.rule_set:
        return _invalid(
            "rule_set",
            "tzdata pin lineage requires the same calendar rule set on both sides",
            previous=previous.rule_set,
            current=current.rule_set,
        )
    if previous.tzdata_version == current.tzdata_version:
        return _invalid(
            "tzdata_version",
            "tzdata pin lineage requires a changed tzdata version; equal pins are "
            "not a lineage edge",
            tzdata_version=previous.tzdata_version,
        )
    old_fp = fingerprint(previous)
    if not is_ok(old_fp):
        return old_fp
    new_fp = fingerprint(current)
    if not is_ok(new_fp):
        return new_fp
    return Ok(
        TzdataPinLineageEdge(
            edge_type=_SUPERSEDES_EDGE_TYPE,
            from_ref=new_fp.value,
            to_ref=old_fp.value,
            reason="tzdata-pin-change",
            old_tzdata_version=previous.tzdata_version,
            new_tzdata_version=current.tzdata_version,
        )
    )
