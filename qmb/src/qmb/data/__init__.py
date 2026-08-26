"""Thin fronts over qmf-data contracts (B-11).

Download, verify, gap-check, list/catalog, and generate are fronts over the
ratified data contracts. Runs read qmf-data rooms; they never fetch from a
provider. Every ingested window carries a license tag (DEC-0166). The
ship-no-corpus licensing gate (Story 18.2) turns that tag into
value-or-typed-refusal for governed-evidence use at read time and asserts the
wheel ships no corpus. ``data list`` rebuilds a DuckDB coverage view over
Parquet rooms (Story 18.3); ``catalog`` aliases ``list``. ``data verify``
checks window integrity without fabricating fills (Story 18.4). ``data
gap-check`` distinguishes calendar closure from genuine missing bars via the
CT-02 market-hours calendar (Story 18.5).
"""

from __future__ import annotations

from typing import Final

from qmf.data import LicenseTag, SplitManifest

from qmb.data.catalog import (
    COVERAGE_KIND,
    NOT_PRESENT,
    PRESENT,
    CoverageEntry,
    CoverageReport,
    catalog,
    catalog_identity,
    list_data,
    persist_coverage_windows,
    scan_coverage_rows,
)
from qmb.data.convert import (
    CONVERSION_BOUNDARY,
    CONVERSION_ROUNDING,
    conversion_identity,
    fingerprint_conversion,
    provider_price_to_exact,
)
from qmb.data.download import (
    DownloadReceipt,
    DownloadRequest,
    download,
    parse_download_request,
    resolve_end_ns,
)
from qmb.data.dukascopy import (
    DUKASCOPY_BATCH_COUNT,
    DUKASCOPY_PROVIDER,
    DukascopyProviderAdapter,
)
from qmb.data.gap_check import (
    GAP_CHECK_KIND,
    AlwaysOpenCalendar,
    GapCheckReport,
    GapCheckRequest,
    ReportedGap,
    gap_check,
    gap_check_identity,
    parse_gap_check_request,
)
from qmb.data.licensing import (
    AUTHORITY_OPERATOR_RULING,
    AUTHORITY_VENUE_POLICY,
    CORPUS_EXTENSIONS,
    DUKASCOPY_PERSONAL_USE_AUTHORITY,
    DUKASCOPY_PERSONAL_USE_POLICY,
    LICENSE_TAG_STATES,
    NON_EVIDENCE_USES,
    AuthorityKind,
    GovernedEvidenceAdmission,
    NonEvidenceUse,
    SourceWindowRef,
    VenueLicensePolicy,
    admit_governed_evidence,
    allow_non_evidence_use,
    assert_distribution_has_no_corpus,
    distribution_corpus_bytes,
    entitlement_lineage_edge,
    licensing_gate_identity,
    resolve_license_tag,
)
from qmb.data.policy import refuse_run_provider_fetch
from qmb.data.ports import (
    DOWNLOAD_SIDES,
    PROVIDER_ADAPTER_METHODS,
    DownloadProgress,
    DownloadSide,
    ProgressSink,
    ProviderAdapter,
    ProviderFetchRequest,
)
from qmb.data.verify import (
    INTEGRITY_KIND,
    IntegrityCounts,
    IntegrityDefect,
    InteriorGap,
    VerifyRequest,
    VerifyVerdict,
    parse_verify_request,
    verify,
    verify_identity,
)

__all__ = [
    "AUTHORITY_OPERATOR_RULING",
    "AUTHORITY_VENUE_POLICY",
    "CONVERSION_BOUNDARY",
    "CONVERSION_ROUNDING",
    "CORPUS_EXTENSIONS",
    "COVERAGE_KIND",
    "DATA_COMMANDS",
    "DOWNLOAD_SIDES",
    "DUKASCOPY_BATCH_COUNT",
    "DUKASCOPY_PERSONAL_USE_AUTHORITY",
    "DUKASCOPY_PERSONAL_USE_POLICY",
    "DUKASCOPY_PROVIDER",
    "GAP_CHECK_KIND",
    "INTEGRITY_KIND",
    "LICENSE_TAG_STATES",
    "NON_EVIDENCE_USES",
    "NOT_PRESENT",
    "PRESENT",
    "PROVIDER_ADAPTER_METHODS",
    "AlwaysOpenCalendar",
    "AuthorityKind",
    "CoverageEntry",
    "CoverageReport",
    "DownloadProgress",
    "DownloadReceipt",
    "DownloadRequest",
    "DownloadSide",
    "DukascopyProviderAdapter",
    "GapCheckReport",
    "GapCheckRequest",
    "GovernedEvidenceAdmission",
    "IntegrityCounts",
    "IntegrityDefect",
    "InteriorGap",
    "NonEvidenceUse",
    "ProgressSink",
    "ProviderAdapter",
    "ProviderFetchRequest",
    "ReportedGap",
    "SourceWindowRef",
    "VenueLicensePolicy",
    "VerifyRequest",
    "VerifyVerdict",
    "admit_governed_evidence",
    "allow_non_evidence_use",
    "assert_distribution_has_no_corpus",
    "catalog",
    "catalog_identity",
    "conversion_identity",
    "data_front_identity",
    "distribution_corpus_bytes",
    "download",
    "entitlement_lineage_edge",
    "fingerprint_conversion",
    "gap_check",
    "gap_check_identity",
    "licensing_gate_identity",
    "list_data",
    "parse_download_request",
    "parse_gap_check_request",
    "parse_verify_request",
    "persist_coverage_windows",
    "provider_price_to_exact",
    "refuse_run_provider_fetch",
    "resolve_end_ns",
    "resolve_license_tag",
    "scan_coverage_rows",
    "verify",
    "verify_identity",
]

DATA_COMMANDS: Final[tuple[str, ...]] = (
    "download",
    "verify",
    "gap-check",
    "list",
    "catalog",
    "generate",
)


def data_front_identity() -> dict[str, object]:
    """Identity-bearing data-front fields. Package SemVer is omitted."""
    identity: dict[str, object] = {
        "commands": DATA_COMMANDS,
        "license_tag": f"{LicenseTag.__module__}.{LicenseTag.__qualname__}",
        "split_manifest": f"{SplitManifest.__module__}.{SplitManifest.__qualname__}",
        "provider_adapter_methods": PROVIDER_ADAPTER_METHODS,
        "conversion_boundary": CONVERSION_BOUNDARY,
        "download_sides": DOWNLOAD_SIDES,
        "dukascopy_provider": DUKASCOPY_PROVIDER,
    }
    identity.update(licensing_gate_identity())
    identity.update(catalog_identity())
    identity.update(verify_identity())
    identity.update(gap_check_identity())
    return identity
