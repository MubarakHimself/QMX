"""Ship-no-corpus licensing gate (Story 18.2, B-11, DEC-0166, DEC-0170).

Pure read-time check: turns each window's recorded licence tag into
value-or-typed-refusal for governed-evidence use. Writes nothing.

Recognized tag states (``redistribution-ok`` / ``internal-only`` /
``denied`` / ``unknown``) are resolved from a per-venue policy record or
operator ruling — never inferred by a provider adapter. Unruled / blank
is ``unknown`` and blocks governed-evidence citation. Non-evidence use
(infra-stress, strategy-logic smoke) stays allowed for catalogable
windows. Passing admissions carry licence tag + granting authority into
citing-artifact CT-07 lineage. A Tier-2/release check asserts the
distribution bundles zero corpus bytes.
"""

from __future__ import annotations

import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_ok
from qmf.data.dukascopy import LicenseTag, parse_license_tag
from qmf.registry import EdgeType, LineageEdge

from qmb._refuse import clean_token, invalid, policy

__all__ = [
    "AUTHORITY_OPERATOR_RULING",
    "AUTHORITY_VENUE_POLICY",
    "CORPUS_EXTENSIONS",
    "DUKASCOPY_PERSONAL_USE_AUTHORITY",
    "DUKASCOPY_PERSONAL_USE_POLICY",
    "LICENSE_TAG_STATES",
    "NON_EVIDENCE_USES",
    "AuthorityKind",
    "GovernedEvidenceAdmission",
    "NonEvidenceUse",
    "SourceWindowRef",
    "VenueLicensePolicy",
    "admit_governed_evidence",
    "allow_non_evidence_use",
    "assert_distribution_has_no_corpus",
    "distribution_corpus_bytes",
    "entitlement_lineage_edge",
    "licensing_gate_identity",
    "resolve_license_tag",
]

LICENSE_TAG_STATES: Final[tuple[str, ...]] = tuple(tag.value for tag in LicenseTag)

AUTHORITY_VENUE_POLICY: Final[str] = "venue-policy"
AUTHORITY_OPERATOR_RULING: Final[str] = "operator-ruling"

# Operator ruling 2026-08-21 / DEC-0170 — personal-use backtesting only.
DUKASCOPY_PERSONAL_USE_AUTHORITY: Final[str] = "DEC-0170"

CORPUS_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        ".bi5",
        ".parquet",
        ".pq",
        ".feather",
        ".arrow",
        ".tick",
        ".ticks",
    }
)

_CORPUS_NAME_MARKERS: Final[tuple[str, ...]] = (
    "market-data-corpus",
    "dukascopy-corpus",
    "tick-corpus",
    "ohlc-corpus",
)


class AuthorityKind(StrEnum):
    """Who ruled the licence tag — never the provider adapter."""

    VENUE_POLICY = AUTHORITY_VENUE_POLICY
    OPERATOR_RULING = AUTHORITY_OPERATOR_RULING


class NonEvidenceUse(StrEnum):
    """Uses that stay legal without a governed-evidence usage right (B-11)."""

    INFRA_STRESS = "infra-stress"
    STRATEGY_LOGIC_SMOKE = "strategy-logic-smoke"


NON_EVIDENCE_USES: Final[tuple[str, ...]] = tuple(member.value for member in NonEvidenceUse)


@dataclass(frozen=True, slots=True)
class VenueLicensePolicy:
    """Per-venue licence posture from a policy record or operator ruling.

    Adapters never invent this. Blank / unruled venues stay absent from the
    policy map so the gate treats them as ``unknown`` (SC-07).
    """

    venue: str
    license_tag: LicenseTag
    granting_authority: str
    authority_kind: AuthorityKind

    def as_mapping(self) -> Mapping[str, object]:
        """Stable machine-readable policy payload."""
        return MappingProxyType(
            {
                "venue": self.venue,
                "license_tag": self.license_tag.value,
                "granting_authority": self.granting_authority,
                "authority_kind": self.authority_kind.value,
            }
        )


DUKASCOPY_PERSONAL_USE_POLICY: Final[VenueLicensePolicy] = VenueLicensePolicy(
    venue="dukascopy-fx",
    license_tag=LicenseTag.INTERNAL_ONLY,
    granting_authority=DUKASCOPY_PERSONAL_USE_AUTHORITY,
    authority_kind=AuthorityKind.OPERATOR_RULING,
)


@dataclass(frozen=True, slots=True)
class SourceWindowRef:
    """One catalogued ``(venue, symbol, window)`` with its recorded licence tag.

    Ingest and catalog do not require a granting usage right. The recorded tag
    (possibly blank) is the gate input from Story 18.1.
    """

    venue: str
    symbol: str
    window_start_ns: int
    window_end_ns: int
    license_tag: object | None = None
    side: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class GovernedEvidenceAdmission:
    """Passed governed-evidence gate: tag + granting authority for CT-07 lineage."""

    venue: str
    symbol: str
    window_start_ns: int
    window_end_ns: int
    license_tag: LicenseTag
    granting_authority: str
    authority_kind: AuthorityKind
    side: str | None = None
    source: str | None = None

    def lineage_payload(self) -> dict[str, object]:
        """Entitlement basis that rides into a citing artifact's CT-07 lineage."""
        payload: dict[str, object] = {
            "class": "license-entitlement",
            "license_tag": self.license_tag.value,
            "granting_authority": self.granting_authority,
            "authority_kind": self.authority_kind.value,
            "venue": self.venue,
            "symbol": self.symbol,
            "window_start_ns": self.window_start_ns,
            "window_end_ns": self.window_end_ns,
        }
        if self.side is not None:
            payload["side"] = self.side
        if self.source is not None:
            payload["source"] = self.source
        return payload

    def entitlement_fingerprint(self) -> Result[Fingerprint]:
        """fp1 of the entitlement basis — the CT-07 ``to_ref`` for citation."""
        return fingerprint(self.lineage_payload())


def licensing_gate_identity() -> dict[str, object]:
    """Identity-bearing licensing-gate fields. Package SemVer is omitted."""
    return {
        "license_tag_states": LICENSE_TAG_STATES,
        "non_evidence_uses": NON_EVIDENCE_USES,
        "authority_kinds": (AUTHORITY_VENUE_POLICY, AUTHORITY_OPERATOR_RULING),
        "writes": False,
        "ship_no_corpus": True,
        "corpus_extensions": tuple(sorted(CORPUS_EXTENSIONS)),
        "dukascopy_personal_use_authority": DUKASCOPY_PERSONAL_USE_AUTHORITY,
    }


def resolve_license_tag(recorded: object | None) -> LicenseTag:
    """Resolve the recorded licence tag; blank / unrecognized → ``unknown``.

    Provider adapters never infer a tag. A venue policy or operator ruling
    supplies granting authority for an already-recorded granting tag — it does
    not silently invent a usage right for a blank window (SC-07, Story 18.2).
    """
    return parse_license_tag(recorded)


def _window_context(window: SourceWindowRef, tag: LicenseTag) -> dict[str, object]:
    context: dict[str, object] = {
        "signal": "refuse-unlicensed-window",
        "venue": window.venue,
        "symbol": window.symbol,
        "window_start_ns": window.window_start_ns,
        "window_end_ns": window.window_end_ns,
        "license_tag": tag.value,
        "contract": "B-11",
    }
    if window.side is not None:
        context["side"] = window.side
    if window.source is not None:
        context["source"] = window.source
    return context


def _lookup_policy(
    venue: str,
    policies: Mapping[str, VenueLicensePolicy] | Sequence[VenueLicensePolicy] | None,
) -> VenueLicensePolicy | None:
    if policies is None:
        return None
    if isinstance(policies, Mapping):
        found = policies.get(venue)
        return found if isinstance(found, VenueLicensePolicy) else None
    for item in policies:
        if item.venue == venue:
            return item
    return None


def _coerce_window(window: object) -> Result[SourceWindowRef]:
    if isinstance(window, SourceWindowRef):
        return Ok(window)
    if isinstance(window, Mapping):
        body = cast("Mapping[str, object]", window)
        venue = clean_token(body.get("venue"))
        symbol = clean_token(body.get("symbol"))
        start = body.get("window_start_ns", body.get("start_ns"))
        end = body.get("window_end_ns", body.get("end_ns"))
        if venue is None or symbol is None:
            return invalid(
                "window",
                "a licensing-gate window names venue and symbol "
                "(venue, symbol, window) (B-11, Story 18.2)",
                given=repr(dict(body)),
            )
        if not isinstance(start, int) or not isinstance(end, int):
            return invalid(
                "window",
                "a licensing-gate window carries integer window_start_ns / "
                "window_end_ns bounds (B-11)",
                given=repr({"window_start_ns": start, "window_end_ns": end}),
            )
        side = clean_token(body.get("side"))
        source = clean_token(body.get("source"))
        return Ok(
            SourceWindowRef(
                venue=venue,
                symbol=symbol,
                window_start_ns=start,
                window_end_ns=end,
                license_tag=body.get("license_tag"),
                side=side,
                source=source,
            )
        )
    return invalid(
        "window",
        "governed-evidence licensing evaluates a SourceWindowRef or mapping "
        "with (venue, symbol, window) (B-11, Story 18.2)",
        given=repr(type(window).__name__),
    )


def admit_governed_evidence(
    window: object,
    *,
    policies: Mapping[str, VenueLicensePolicy] | Sequence[VenueLicensePolicy] | None = None,
) -> Result[GovernedEvidenceAdmission]:
    """Admit a window for governed-evidence use, or refuse (Story 18.2).

    Pure read-time check — writes nothing. Tags that grant use
    (``internal-only``, ``redistribution-ok``) pass when a granting authority
    is available from the venue policy / operator ruling. ``denied``,
    ``unknown``, or absent refuse with ``(venue, symbol, window)`` and the
    tag state as machine-readable context.
    """
    coerced = _coerce_window(window)
    if not is_ok(coerced):
        return coerced
    ref = coerced.value
    tag = resolve_license_tag(ref.license_tag)
    if not tag.grants_governed_evidence():
        return policy(
            "license_tag",
            "a source window without a recorded usage right cannot become "
            "governed evidence — record an authorizing license tag from a "
            "venue policy or operator ruling first (B-11, Story 18.2, "
            "DEC-0166)",
            **_window_context(ref, tag),
        )
    venue_policy = _lookup_policy(ref.venue, policies)
    if venue_policy is None:
        return policy(
            "granting_authority",
            "a governed-evidence admission needs a granting authority from a "
            "per-venue policy record or operator ruling — never inferred by "
            "the provider adapter (B-11, Story 18.2, SC-07)",
            **_window_context(ref, tag),
        )
    if venue_policy.license_tag is not tag:
        return policy(
            "granting_authority",
            "recorded license tag disagrees with the venue policy / operator "
            "ruling; reconcile the ruling before citing as governed evidence "
            "(B-11, Story 18.2)",
            **_window_context(ref, tag),
            policy_license_tag=venue_policy.license_tag.value,
            policy_authority=venue_policy.granting_authority,
        )
    return Ok(
        GovernedEvidenceAdmission(
            venue=ref.venue,
            symbol=ref.symbol,
            window_start_ns=ref.window_start_ns,
            window_end_ns=ref.window_end_ns,
            license_tag=tag,
            granting_authority=venue_policy.granting_authority,
            authority_kind=venue_policy.authority_kind,
            side=ref.side,
            source=ref.source,
        )
    )


def allow_non_evidence_use(
    window: object,
    *,
    use: object = NonEvidenceUse.INFRA_STRESS,
) -> Result[SourceWindowRef]:
    """Allow infra-stress / strategy-logic-smoke use without a usage right.

    Dukascopy (and any other) windows with no recorded usage right still
    ingest and remain catalogable; only governed-evidence citation is refused
    until a usage right is recorded (B-11 open-ops posture closed by DEC-0170
    for personal use — the per-window tag still gates evidence citation).
    """
    coerced = _coerce_window(window)
    if not is_ok(coerced):
        return coerced
    token = clean_token(use) if not isinstance(use, NonEvidenceUse) else use.value
    if token not in NON_EVIDENCE_USES:
        return invalid(
            "use",
            "non-evidence use is infra-stress or strategy-logic-smoke only "
            "(B-11, L20); governed-evidence citation uses admit_governed_evidence",
            given=repr(use),
            allowed=list(NON_EVIDENCE_USES),
        )
    return Ok(coerced.value)


def entitlement_lineage_edge(
    admission: object,
    *,
    citing_ref: object,
    writer: object,
) -> Result[LineageEdge]:
    """Build a CT-07 ``occurrence-of`` edge from citing artifact → entitlement.

    The gate itself writes nothing; the caller appends this edge to a lineage
    stream when citing the window as governed evidence.
    """
    if not isinstance(admission, GovernedEvidenceAdmission):
        return invalid(
            "admission",
            "entitlement lineage requires a GovernedEvidenceAdmission from "
            "admit_governed_evidence (Story 18.2)",
            given=repr(type(admission).__name__),
        )
    entitlement = admission.entitlement_fingerprint()
    if not is_ok(entitlement):
        return entitlement
    return LineageEdge.try_create(
        EdgeType.OCCURRENCE_OF,
        citing_ref,
        entitlement.value,
        writer,
    )


def _is_corpus_path(path: Path, *, root: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in CORPUS_EXTENSIONS:
        return True
    if suffix == ".csv" and any(
        marker in path.name.lower() for marker in ("tick", "ohlc", "candle", "quote")
    ):
        return True
    relative = path.relative_to(root).as_posix().lower()
    return any(marker in relative for marker in _CORPUS_NAME_MARKERS)


def distribution_corpus_bytes(root: object) -> Result[int]:
    """Sum corpus-shaped payload bytes under a package tree or wheel archive.

    Pure inspection — opens files only to measure size; never mutates.
    """
    if not isinstance(root, (str, Path)):
        return invalid(
            "root",
            "distribution corpus check names a filesystem path or .whl archive",
            given=repr(type(root).__name__),
        )
    path = Path(root)
    if not path.exists():
        return invalid(
            "root",
            "distribution corpus check needs an existing package tree or wheel",
            given=str(path),
        )
    total = 0
    if path.is_file() and path.suffix.lower() == ".whl":
        try:
            with zipfile.ZipFile(path) as archive:
                for info in archive.infolist():
                    name = info.filename.lower()
                    suffix = Path(name).suffix.lower()
                    marker_hit = any(marker in name for marker in _CORPUS_NAME_MARKERS)
                    csv_tick = suffix == ".csv" and any(
                        token in Path(name).name for token in ("tick", "ohlc", "candle", "quote")
                    )
                    if suffix in CORPUS_EXTENSIONS or marker_hit or csv_tick:
                        total += int(info.file_size)
        except zipfile.BadZipFile:
            return invalid(
                "root",
                "distribution corpus check needs a readable wheel zip",
                given=str(path),
            )
        return Ok(total)
    if not path.is_dir():
        return invalid(
            "root",
            "distribution corpus check names a directory package tree or .whl",
            given=str(path),
        )
    for child in path.rglob("*"):
        if child.is_file() and _is_corpus_path(child, root=path):
            total += child.stat().st_size
    return Ok(total)


def assert_distribution_has_no_corpus(root: object) -> Result[int]:
    """Tier-2/release check: the distribution bundles zero corpus bytes (AR-54)."""
    measured = distribution_corpus_bytes(root)
    if not is_ok(measured):
        return measured
    if measured.value != 0:
        return policy(
            "corpus",
            "QMB ships and redistributes no market-data corpus — the "
            "distribution must bundle zero corpus bytes (B-11, AR-54, "
            "Story 18.2)",
            signal="refuse-ship-corpus",
            corpus_bytes=measured.value,
            root=str(root),
        )
    return Ok(0)
