"""Story 30.2 — fetch and clean the governed all-session training corpus.

Offline acquisition plan, cleaning, and fingerprinted train/validation/holdout
manifests that cite the accepted Story 30.1 design. Acquisition records
source/dataset/revision/calendar/licence identities through declared QMF/QMB
tools only. Provider fetch inside a training run, live network, silent
repair/drop, and model training are typed refusals (FR-079; CT-10/12/15;
NFR-15; GAP-0051).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    CalendarIdentity,
    Duration,
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    World,
    fingerprint,
    is_refusal,
)
from qmf.data import (
    HoldoutSeal,
    ProducerHorizon,
    SegmentRole,
    SplitBoundary,
    SplitManifest,
)
from qmf.data.dukascopy import DUKASCOPY_SOURCE, PERSONAL_USE_LICENSE
from qmf.data.splits import SplitSegment

from qmn.mis._refuse import clean_token, invalid, policy
from qmn.mis.regime_design import (
    DECLARED_TRADING_SESSIONS,
    DataWindowContract,
    ExecutableRegimeContract,
    RegimeClassifierDesign,
    SplitStrategy,
    assert_design_unchanged,
    executable_regime_contract,
)

__all__ = [
    "ACQUISITION_CONTEXT",
    "BAR_INTERVAL_M5_NS",
    "CORPUS_FORMAT_VERSION",
    "REGIME_CORPUS_ARTIFACT_ID",
    "REGIME_CORPUS_SURFACE",
    "TRAINING_RUN_CONTEXT",
    "CleanedCorpus",
    "CleanedCorpusRow",
    "CorpusAcquisitionPlan",
    "CorpusQualityReport",
    "CorpusSplitBundle",
    "GovernedSourceDeclaration",
    "QualityIssueCode",
    "RawCorpusRow",
    "RegimeTrainingCorpus",
    "SourceReceipt",
    "acquire_offline_corpus",
    "build_acquisition_plan",
    "clean_corpus",
    "declared_governed_sources",
    "materialize_corpus_splits",
    "materialize_training_corpus",
    "refuse_corpus_training",
    "refuse_live_network_corpus",
    "refuse_provider_fetch_in_training",
    "refuse_silent_repair",
]

REGIME_CORPUS_SURFACE: Final[str] = "qmn.mis.regime_corpus"
REGIME_CORPUS_ARTIFACT_ID: Final[str] = "regime_classifier_v1_training_corpus"
CORPUS_FORMAT_VERSION: Final[int] = 1
ACQUISITION_CONTEXT: Final[str] = "operator-machine-offline-acquisition"
TRAINING_RUN_CONTEXT: Final[str] = "training-run"
BAR_INTERVAL_M5_NS: Final[int] = 5 * 60 * 1_000_000_000

# News-calendar source identity (CT-15 calendar-feed; DEC-0214). String only —
# this module never fetches the weekly file.
NEWS_CALENDAR_SOURCE: Final[str] = "forex-factory-weekly"
NEWS_CALENDAR_LICENSE: Final[str] = "free-public-weekly-file"
MARKET_HOURS_CALENDAR_KIND: Final[str] = "market-hours-calendar"
DAY_BOUNDARY_CALENDAR_KIND: Final[str] = "day-boundary-calendar"
NEWS_CALENDAR_KIND: Final[str] = "news-calendar"

_ALLOWED_SCALE_DIGITS: Final[frozenset[int]] = frozenset({2, 3, 4, 5})


class QualityIssueCode(StrEnum):
    """Closed cleaning refusal vocabulary — every drop is explicit (NFR-15)."""

    DUPLICATE = "duplicate"
    GAP = "gap"
    OUT_OF_ORDER = "out-of-order"
    BAD_SCALE = "bad-scale"
    SESSION_BOUNDARY = "session-boundary"
    CORRECTION = "correction"
    UNKNOWN_SESSION = "unknown-session"
    FOREIGN_SOURCE = "foreign-source"
    MISSING_LICENSE = "missing-license"


@dataclass(frozen=True, slots=True)
class GovernedSourceDeclaration:
    """One declared governed source the offline acquisition plan may cite."""

    source_id: str
    dataset_id: str
    tool_path: str
    license_tag: str
    calendar_kind: str
    revision_pin_required: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-governed-source-declaration",
            "source_id": self.source_id,
            "dataset_id": self.dataset_id,
            "tool_path": self.tool_path,
            "license_tag": self.license_tag,
            "calendar_kind": self.calendar_kind,
            "revision_pin_required": self.revision_pin_required,
        }


@dataclass(frozen=True, slots=True)
class SourceReceipt:
    """Operator-prepared offline receipt — never produced by a live fetch here."""

    source_id: str
    dataset_id: str
    revision: str
    calendar_identity: str
    license_tag: str
    window_start_ns: int
    window_end_ns: int
    row_count: int
    content_fp: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-source-receipt",
            "source_id": self.source_id,
            "dataset_id": self.dataset_id,
            "revision": self.revision,
            "calendar_identity": self.calendar_identity,
            "license_tag": self.license_tag,
            "window_start_ns": self.window_start_ns,
            "window_end_ns": self.window_end_ns,
            "row_count": self.row_count,
            "content_fp": self.content_fp,
        }


@dataclass(frozen=True, slots=True)
class CorpusAcquisitionPlan:
    """Fingerprinted offline acquisition plan citing Story 30.1 data windows."""

    artifact_id: str
    design_artifact_id: str
    design_fp: Fingerprint
    contract_fp: Fingerprint
    sources: tuple[GovernedSourceDeclaration, ...]
    sessions: tuple[str, ...]
    data_windows: DataWindowContract
    calendar_kinds_named_apart: tuple[str, ...]
    acquisition_context: str
    provider_fetch_in_training_forbidden: bool
    live_network_forbidden: bool
    world: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-corpus-acquisition-plan",
            "artifact_id": self.artifact_id,
            "design_artifact_id": self.design_artifact_id,
            "design_fp": self.design_fp.value,
            "contract_fp": self.contract_fp.value,
            "sources": [row.fp1_identity() for row in self.sources],
            "sessions": list(self.sessions),
            "data_windows": self.data_windows.fp1_identity(),
            "calendar_kinds_named_apart": list(self.calendar_kinds_named_apart),
            "acquisition_context": self.acquisition_context,
            "provider_fetch_in_training_forbidden": (
                self.provider_fetch_in_training_forbidden
            ),
            "live_network_forbidden": self.live_network_forbidden,
            "world": self.world,
            "format_version": CORPUS_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class RawCorpusRow:
    """One raw sealed-bar observation offered to cleaning (as-of only)."""

    row_id: str
    source_id: str
    instrument: str
    session: str
    event_time_ns: int
    knowledge_time_ns: int
    open_scaled: int
    high_scaled: int
    low_scaled: int
    close_scaled: int
    scale_digits: int
    license_tag: str
    is_correction: bool = False
    correction_of: str | None = None

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "class": "regime-raw-corpus-row",
            "row_id": self.row_id,
            "source_id": self.source_id,
            "instrument": self.instrument,
            "session": self.session,
            "event_time_ns": self.event_time_ns,
            "knowledge_time_ns": self.knowledge_time_ns,
            "open_scaled": self.open_scaled,
            "high_scaled": self.high_scaled,
            "low_scaled": self.low_scaled,
            "close_scaled": self.close_scaled,
            "scale_digits": self.scale_digits,
            "license_tag": self.license_tag,
            "is_correction": self.is_correction,
        }
        if self.correction_of is not None:
            content["correction_of"] = self.correction_of
        return content


@dataclass(frozen=True, slots=True)
class CleanedCorpusRow:
    """One admitted cleaned row — lineage to raw preserved by row_id."""

    row_id: str
    source_id: str
    instrument: str
    session: str
    event_time_ns: int
    knowledge_time_ns: int
    open_scaled: int
    high_scaled: int
    low_scaled: int
    close_scaled: int
    scale_digits: int

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-cleaned-corpus-row",
            "row_id": self.row_id,
            "source_id": self.source_id,
            "instrument": self.instrument,
            "session": self.session,
            "event_time_ns": self.event_time_ns,
            "knowledge_time_ns": self.knowledge_time_ns,
            "open_scaled": self.open_scaled,
            "high_scaled": self.high_scaled,
            "low_scaled": self.low_scaled,
            "close_scaled": self.close_scaled,
            "scale_digits": self.scale_digits,
        }


@dataclass(frozen=True, slots=True)
class CorpusQualityReport:
    """Complete cleaning quality report — refusal counts, never silent drops."""

    admitted_count: int
    refused_count: int
    refusal_counts: Mapping[str, int]
    gap_count: int
    sessions_represented: tuple[str, ...]
    raw_row_count: int
    silent_repair_forbidden: bool
    raw_evidence_preserved: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-corpus-quality-report",
            "admitted_count": self.admitted_count,
            "refused_count": self.refused_count,
            "refusal_counts": dict(sorted(self.refusal_counts.items())),
            "gap_count": self.gap_count,
            "sessions_represented": list(self.sessions_represented),
            "raw_row_count": self.raw_row_count,
            "silent_repair_forbidden": self.silent_repair_forbidden,
            "raw_evidence_preserved": self.raw_evidence_preserved,
        }


@dataclass(frozen=True, slots=True)
class CleanedCorpus:
    """Fingerprinted cleaned dataset with lineage to plan and raw receipts."""

    artifact_id: str
    plan_fp: Fingerprint
    design_fp: Fingerprint
    rows: tuple[CleanedCorpusRow, ...]
    quality: CorpusQualityReport
    source_receipts: tuple[SourceReceipt, ...]
    raw_row_ids: tuple[str, ...]
    sessions: tuple[str, ...]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-cleaned-corpus",
            "artifact_id": self.artifact_id,
            "plan_fp": self.plan_fp.value,
            "design_fp": self.design_fp.value,
            "rows": [row.fp1_identity() for row in self.rows],
            "quality": self.quality.fp1_identity(),
            "source_receipts": [row.fp1_identity() for row in self.source_receipts],
            "raw_row_ids": list(self.raw_row_ids),
            "sessions": list(self.sessions),
            "format_version": CORPUS_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class CorpusSplitBundle:
    """Fingerprinted train/validation/holdout manifests with a no-peek seal."""

    train_manifest: SplitManifest
    validation_manifest: SplitManifest
    holdout_manifest: SplitManifest
    combined_manifest: SplitManifest
    holdout_seal: HoldoutSeal
    as_of_set_fp: Fingerprint
    split_strategy: SplitStrategy
    dataset_immutable: bool
    trains_model: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-corpus-split-bundle",
            "train_split_id": self.train_manifest.split_id,
            "validation_split_id": self.validation_manifest.split_id,
            "holdout_split_id": self.holdout_manifest.split_id,
            "combined_split_id": self.combined_manifest.split_id,
            "holdout_seal_boundary": self.holdout_seal.seal_boundary.fp1_identity(),
            "as_of_set_fp": self.as_of_set_fp.value,
            "split_strategy": self.split_strategy.fp1_identity(),
            "dataset_immutable": self.dataset_immutable,
            "trains_model": self.trains_model,
            "format_version": CORPUS_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class RegimeTrainingCorpus:
    """Materialized offline corpus artifact. Research evidence only — no training."""

    artifact_id: str
    design_fp: Fingerprint
    contract_fp: Fingerprint
    plan_fp: Fingerprint
    cleaned_fp: Fingerprint
    splits_fp: Fingerprint
    cleaned: CleanedCorpus
    splits: CorpusSplitBundle
    grants_money_path_authority: bool
    trains_model: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "regime-training-corpus",
            "artifact_id": self.artifact_id,
            "design_fp": self.design_fp.value,
            "contract_fp": self.contract_fp.value,
            "plan_fp": self.plan_fp.value,
            "cleaned_fp": self.cleaned_fp.value,
            "splits_fp": self.splits_fp.value,
            "grants_money_path_authority": self.grants_money_path_authority,
            "trains_model": self.trains_model,
            "format_version": CORPUS_FORMAT_VERSION,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


def declared_governed_sources() -> tuple[GovernedSourceDeclaration, ...]:
    """Closed set of governed sources acquisition may cite (CT-10/15)."""
    return (
        GovernedSourceDeclaration(
            source_id=DUKASCOPY_SOURCE,
            dataset_id="fx-majors-m5-bars",
            tool_path="qmf.data.dukascopy+qmn.data.bootstrap",
            license_tag=PERSONAL_USE_LICENSE,
            calendar_kind=MARKET_HOURS_CALENDAR_KIND,
            revision_pin_required=True,
        ),
        GovernedSourceDeclaration(
            source_id=NEWS_CALENDAR_SOURCE,
            dataset_id="ff-weekly-news-calendar",
            tool_path="qmn.data.news_calendar",
            license_tag=NEWS_CALENDAR_LICENSE,
            calendar_kind=NEWS_CALENDAR_KIND,
            revision_pin_required=True,
        ),
        GovernedSourceDeclaration(
            source_id="qmf-calendar-forex",
            dataset_id="market-hours-rule-set",
            tool_path="extensions.qmf-calendar-forex",
            license_tag="internal-rule-set",
            calendar_kind=MARKET_HOURS_CALENDAR_KIND,
            revision_pin_required=True,
        ),
        GovernedSourceDeclaration(
            source_id="day-boundary-calendar",
            dataset_id="account-day-boundary-rule",
            tool_path="qmf.core.chrono+qmn.time.calendars",
            license_tag="internal-rule-set",
            calendar_kind=DAY_BOUNDARY_CALENDAR_KIND,
            revision_pin_required=True,
        ),
    )


def refuse_provider_fetch_in_training(*, context: object) -> TypedRefusal:
    """No provider fetch occurs inside a training run (FR-079; CT-10/15)."""
    return policy(
        "context",
        "no provider fetch occurs inside a training run; acquire through the "
        "offline operator-machine plan citing governed QMF/QMB tools first",
        failure_id="mis.regime_corpus.provider_fetch_in_training",
        given=repr(context),
        forbidden=TRAINING_RUN_CONTEXT,
        allowed=ACQUISITION_CONTEXT,
    )


def refuse_live_network_corpus(*, target: object) -> TypedRefusal:
    """This surface never opens a live network path."""
    return policy(
        "transport",
        "regime corpus acquisition is offline scripts/contracts only; live "
        "network fetches are refused (FR-079; DEC-0262)",
        failure_id="mis.regime_corpus.live_network",
        given=repr(target),
    )


def refuse_silent_repair(*, action: object) -> TypedRefusal:
    """No row is silently repaired or dropped (NFR-15)."""
    return policy(
        "action",
        "cleaning never silently repairs or drops a row; every refusal is "
        "counted in the quality report",
        failure_id="mis.regime_corpus.silent_repair",
        given=repr(action),
    )


def refuse_corpus_training(*, claim: object = "train") -> TypedRefusal:
    """Story 30.2 materializes the corpus; it does not train a model."""
    return policy(
        "claim",
        "Story 30.2 fetches and cleans the governed corpus and mints split "
        "manifests; training is Story 30.4",
        failure_id="mis.regime_corpus.no_training",
        given=repr(claim),
    )


def build_acquisition_plan(
    *,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
) -> Result[CorpusAcquisitionPlan]:
    """Build the offline acquisition plan citing the accepted Story 30.1 contract."""
    resolved_contract = contract
    if resolved_contract is None:
        minted = executable_regime_contract(design)
        if is_refusal(minted):
            return minted
        resolved_contract = minted.value
    unchanged = assert_design_unchanged(resolved_contract.design_fp, design=design)
    if is_refusal(unchanged):
        return unchanged
    contract_fp = resolved_contract.fingerprint()
    if is_refusal(contract_fp):
        return contract_fp
    windows = resolved_contract.data_windows
    if windows.source_law != (
        "governed-qmf-qmb-tools-only-no-provider-fetch-inside-training"
    ):
        return policy(
            "source_law",
            "acquisition cites only governed QMF/QMB tools with no provider "
            "fetch inside training",
            given=windows.source_law,
        )
    if tuple(windows.sessions) != DECLARED_TRADING_SESSIONS:
        return policy(
            "sessions",
            "acquisition must cover all three declared trading sessions",
            given=list(windows.sessions),
            required=list(DECLARED_TRADING_SESSIONS),
        )
    calendars = tuple(resolved_contract.leakage.calendar_kinds_named_apart)
    return Ok(
        CorpusAcquisitionPlan(
            artifact_id=f"{REGIME_CORPUS_ARTIFACT_ID}_acquisition_plan",
            design_artifact_id=resolved_contract.design_artifact_id,
            design_fp=resolved_contract.design_fp,
            contract_fp=contract_fp.value,
            sources=declared_governed_sources(),
            sessions=tuple(windows.sessions),
            data_windows=windows,
            calendar_kinds_named_apart=calendars,
            acquisition_context=ACQUISITION_CONTEXT,
            provider_fetch_in_training_forbidden=True,
            live_network_forbidden=True,
            world=World.REPLAY.value,
        )
    )


def acquire_offline_corpus(
    plan: object,
    receipts: object,
    *,
    context: object = ACQUISITION_CONTEXT,
    allow_live_network: object = False,
) -> Result[tuple[SourceReceipt, ...]]:
    """Admit operator-prepared offline receipts against the acquisition plan.

    Never opens a provider transport. A training-run context or live-network
    flag is a policy rejection.
    """
    if not isinstance(plan, CorpusAcquisitionPlan):
        return invalid(
            "plan",
            "offline acquisition takes a CorpusAcquisitionPlan",
            given=type(plan).__name__,
        )
    context_token = clean_token(context)
    if context_token == TRAINING_RUN_CONTEXT:
        return refuse_provider_fetch_in_training(context=context_token)
    if context_token != ACQUISITION_CONTEXT:
        return policy(
            "context",
            "corpus acquisition runs only in the operator-machine offline context",
            given=repr(context),
            allowed=ACQUISITION_CONTEXT,
        )
    if allow_live_network is True:
        return refuse_live_network_corpus(target="allow_live_network=True")
    if allow_live_network not in (False, None):
        return invalid(
            "allow_live_network",
            "allow_live_network is False for offline corpus acquisition",
            given=repr(allow_live_network),
        )
    if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)):
        return invalid(
            "receipts",
            "offline acquisition takes a sequence of SourceReceipt values",
            given=type(receipts).__name__,
        )
    allowed = {row.source_id: row for row in plan.sources}
    admitted: list[SourceReceipt] = []
    for index, raw in enumerate(cast("Sequence[object]", receipts)):
        if not isinstance(raw, SourceReceipt):
            return invalid(
                "receipts",
                "each receipt is a SourceReceipt prepared offline",
                index=index,
                given=type(raw).__name__,
            )
        declaration = allowed.get(raw.source_id)
        if declaration is None:
            return policy(
                "source_id",
                "receipt source is not in the declared governed source set",
                source_id=raw.source_id,
                allowed=sorted(allowed),
            )
        if raw.dataset_id != declaration.dataset_id:
            return policy(
                "dataset_id",
                "receipt dataset must match the declared governed dataset",
                source_id=raw.source_id,
                given=raw.dataset_id,
                required=declaration.dataset_id,
            )
        if raw.license_tag != declaration.license_tag:
            return policy(
                "license_tag",
                "receipt licence tag must match the declared governed licence",
                source_id=raw.source_id,
                given=raw.license_tag,
                required=declaration.license_tag,
            )
        if declaration.revision_pin_required and clean_token(raw.revision) is None:
            return invalid(
                "revision",
                "governed sources require a pinned revision identity",
                source_id=raw.source_id,
            )
        if clean_token(raw.calendar_identity) is None:
            return invalid(
                "calendar_identity",
                "every receipt records its calendar identity in-band",
                source_id=raw.source_id,
            )
        if raw.window_end_ns <= raw.window_start_ns:
            return invalid(
                "window",
                "receipt window is a half-open [start, end) over UTC ns",
                source_id=raw.source_id,
                window_start_ns=raw.window_start_ns,
                window_end_ns=raw.window_end_ns,
            )
        if raw.row_count < 0:
            return invalid(
                "row_count",
                "receipt row_count is a non-negative integer",
                given=raw.row_count,
            )
        if clean_token(raw.content_fp) is None:
            return invalid(
                "content_fp",
                "receipt content fingerprint is required for lineage",
                source_id=raw.source_id,
            )
        admitted.append(raw)
    if not admitted:
        return invalid("receipts", "offline acquisition requires at least one receipt")
    covered_sources = {row.source_id for row in admitted}
    if DUKASCOPY_SOURCE not in covered_sources:
        return policy(
            "sources",
            "all-session FX bar evidence requires the declared Dukascopy governed source",
            covered=sorted(covered_sources),
        )
    return Ok(tuple(admitted))


def clean_corpus(
    raw_rows: object,
    plan: object,
    *,
    source_receipts: object = (),
    bar_interval_ns: object = BAR_INTERVAL_M5_NS,
    silent_repair: object = False,
) -> Result[CleanedCorpus]:
    """Clean raw rows into a fingerprinted dataset with a complete quality report.

    Duplicate, gap, out-of-order, bad-scale, session-boundary, and correction
    handling follows the design. Refused rows are counted; nothing is silently
    repaired or dropped. Raw row ids remain on the cleaned artifact for lineage.
    """
    if not isinstance(plan, CorpusAcquisitionPlan):
        return invalid(
            "plan",
            "cleaning takes a CorpusAcquisitionPlan",
            given=type(plan).__name__,
        )
    if silent_repair is True:
        return refuse_silent_repair(action="silent_repair=True")
    if silent_repair not in (False, None):
        return invalid(
            "silent_repair",
            "silent_repair is False; cleaning refuses rather than repairs",
            given=repr(silent_repair),
        )
    if not isinstance(bar_interval_ns, int) or isinstance(bar_interval_ns, bool):
        return invalid(
            "bar_interval_ns",
            "bar interval is an int64 nanosecond count",
            given=repr(bar_interval_ns),
        )
    if bar_interval_ns != BAR_INTERVAL_M5_NS:
        return policy(
            "bar_interval_ns",
            "Story 30.1 data windows declare M5 bars only",
            given=bar_interval_ns,
            required=BAR_INTERVAL_M5_NS,
        )
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
        return invalid(
            "raw_rows",
            "cleaning takes a sequence of RawCorpusRow values",
            given=type(raw_rows).__name__,
        )
    receipts: tuple[SourceReceipt, ...]
    if source_receipts is None:
        receipts = ()
    elif isinstance(source_receipts, Sequence) and not isinstance(
        source_receipts, (str, bytes)
    ):
        built: list[SourceReceipt] = []
        for index, item in enumerate(cast("Sequence[object]", source_receipts)):
            if not isinstance(item, SourceReceipt):
                return invalid(
                    "source_receipts",
                    "each source receipt is a SourceReceipt",
                    index=index,
                    given=type(item).__name__,
                )
            built.append(item)
        receipts = tuple(built)
    else:
        return invalid(
            "source_receipts",
            "source_receipts is a sequence of SourceReceipt values",
            given=type(source_receipts).__name__,
        )

    allowed_sources = {row.source_id: row for row in plan.sources}
    allowed_sessions = set(plan.sessions)
    refusal_counts: dict[str, int] = {code.value: 0 for code in QualityIssueCode}
    admitted: list[CleanedCorpusRow] = []
    raw_ids: list[str] = []
    seen_keys: set[tuple[str, str, int]] = set()
    prev_by_instrument: dict[str, int] = {}
    gap_count = 0

    for index, raw in enumerate(cast("Sequence[object]", raw_rows)):
        if not isinstance(raw, RawCorpusRow):
            return invalid(
                "raw_rows",
                "each raw row is a RawCorpusRow",
                index=index,
                given=type(raw).__name__,
            )
        raw_ids.append(raw.row_id)
        issues: list[QualityIssueCode] = []
        declaration = allowed_sources.get(raw.source_id)
        if declaration is None:
            issues.append(QualityIssueCode.FOREIGN_SOURCE)
        elif raw.license_tag != declaration.license_tag:
            issues.append(QualityIssueCode.MISSING_LICENSE)
        if raw.session not in allowed_sessions:
            issues.append(QualityIssueCode.UNKNOWN_SESSION)
        if raw.scale_digits not in _ALLOWED_SCALE_DIGITS:
            issues.append(QualityIssueCode.BAD_SCALE)
        if raw.high_scaled < raw.low_scaled:
            issues.append(QualityIssueCode.BAD_SCALE)
        if (
            raw.open_scaled > raw.high_scaled
            or raw.open_scaled < raw.low_scaled
            or raw.close_scaled > raw.high_scaled
            or raw.close_scaled < raw.low_scaled
        ):
            issues.append(QualityIssueCode.BAD_SCALE)
        if raw.knowledge_time_ns < raw.event_time_ns:
            issues.append(QualityIssueCode.OUT_OF_ORDER)
        if raw.is_correction or raw.correction_of is not None:
            issues.append(QualityIssueCode.CORRECTION)
        key = (raw.source_id, raw.instrument, raw.event_time_ns)
        if key in seen_keys:
            issues.append(QualityIssueCode.DUPLICATE)
        prev = prev_by_instrument.get(raw.instrument)
        if prev is not None:
            if raw.event_time_ns < prev:
                issues.append(QualityIssueCode.OUT_OF_ORDER)
            elif raw.event_time_ns == prev:
                issues.append(QualityIssueCode.DUPLICATE)
            elif raw.event_time_ns - prev > bar_interval_ns:
                # Gaps are reported, never filled. The following sealed bar is
                # still eligible unless another issue refuses it.
                gap_count += 1
                refusal_counts[QualityIssueCode.GAP.value] += 1
        if clean_token(raw.session) is None:
            issues.append(QualityIssueCode.SESSION_BOUNDARY)

        if issues:
            for code in dict.fromkeys(issues):
                refusal_counts[code.value] += 1
            continue

        seen_keys.add(key)
        prev_by_instrument[raw.instrument] = raw.event_time_ns
        admitted.append(
            CleanedCorpusRow(
                row_id=raw.row_id,
                source_id=raw.source_id,
                instrument=raw.instrument,
                session=raw.session,
                event_time_ns=raw.event_time_ns,
                knowledge_time_ns=raw.knowledge_time_ns,
                open_scaled=raw.open_scaled,
                high_scaled=raw.high_scaled,
                low_scaled=raw.low_scaled,
                close_scaled=raw.close_scaled,
                scale_digits=raw.scale_digits,
            )
        )

    sessions_present = tuple(
        session
        for session in DECLARED_TRADING_SESSIONS
        if any(row.session == session for row in admitted)
    )
    if set(sessions_present) != set(DECLARED_TRADING_SESSIONS):
        return policy(
            "sessions",
            "cleaned corpus must represent all three declared trading sessions",
            present=list(sessions_present),
            required=list(DECLARED_TRADING_SESSIONS),
        )
    if not admitted:
        return policy(
            "rows",
            "cleaning produced no admitted rows; raw evidence is preserved in the "
            "quality report refusal counts",
            refused_count=sum(refusal_counts.values()),
        )

    refused_count = sum(refusal_counts.values())
    quality = CorpusQualityReport(
        admitted_count=len(admitted),
        refused_count=refused_count,
        refusal_counts=MappingProxyType(dict(sorted(refusal_counts.items()))),
        gap_count=gap_count,
        sessions_represented=sessions_present,
        raw_row_count=len(raw_ids),
        silent_repair_forbidden=True,
        raw_evidence_preserved=True,
    )
    return Ok(
        CleanedCorpus(
            artifact_id=f"{REGIME_CORPUS_ARTIFACT_ID}_cleaned",
            plan_fp=_require_plan_fp(plan),
            design_fp=plan.design_fp,
            rows=tuple(admitted),
            quality=quality,
            source_receipts=receipts,
            raw_row_ids=tuple(raw_ids),
            sessions=sessions_present,
        )
    )


def _require_plan_fp(plan: CorpusAcquisitionPlan) -> Fingerprint:
    """Trusted path: plan was already built through the validating factory."""
    result = plan.fingerprint()
    if is_refusal(result):  # pragma: no cover - identity content is canonical
        raise RuntimeError("acquisition plan fingerprint refused unexpectedly")
    return result.value


def materialize_corpus_splits(
    cleaned: object,
    *,
    design: RegimeClassifierDesign | None = None,
    contract: ExecutableRegimeContract | None = None,
    calendar_identity: object,
    holdout_months: object,
    window_start_ns: object | None = None,
    window_end_ns: object | None = None,
) -> Result[CorpusSplitBundle]:
    """Mint fingerprinted time-ordered train/validation/holdout manifests.

    Uses CT-12 ``SplitManifest`` with ``sealed-test`` as the holdout role. The
    no-peek seal is enforced; the dataset/as-of set fingerprint is immutable for
    the later training run. This function does not train a model.
    """
    if not isinstance(cleaned, CleanedCorpus):
        return invalid(
            "cleaned",
            "split materialization takes a CleanedCorpus",
            given=type(cleaned).__name__,
        )
    resolved_contract = contract
    if resolved_contract is None:
        minted = executable_regime_contract(design)
        if is_refusal(minted):
            return minted
        resolved_contract = minted.value
    unchanged = assert_design_unchanged(
        cleaned.design_fp if design is None else resolved_contract.design_fp,
        design=design,
    )
    if is_refusal(unchanged):
        return unchanged
    if cleaned.design_fp.value != resolved_contract.design_fp.value:
        return policy(
            "design_fp",
            "cleaned corpus must cite the same design fingerprint as the executable contract",
            cleaned=cleaned.design_fp.value,
            contract=resolved_contract.design_fp.value,
        )
    if not isinstance(calendar_identity, CalendarIdentity):
        return invalid(
            "calendar_identity",
            "split manifests pin a qmf-core CalendarIdentity in-band",
            given=type(calendar_identity).__name__,
        )
    if (
        isinstance(holdout_months, bool)
        or not isinstance(holdout_months, int)
        or holdout_months < 1
    ):
        return invalid(
            "holdout_months",
            "holdout_months is a positive integer from registry:historical_holdout_months",
            given=repr(holdout_months),
        )

    strategy = resolved_contract.split_strategy
    if strategy.shuffle_forbidden is not True or strategy.holdout_sealed is not True:
        return policy(
            "split_strategy",
            "corpus splits require time-ordered non-overlapping sealed holdout",
        )
    if strategy.ordering != "time-ordered-non-overlapping":
        return policy(
            "ordering",
            "corpus splits are time-ordered and non-overlapping",
            given=strategy.ordering,
        )

    bounds = _resolve_window_bounds(
        cleaned,
        window_start_ns=window_start_ns,
        window_end_ns=window_end_ns,
    )
    if is_refusal(bounds):
        return bounds
    start_ns, end_ns = bounds.value
    span = end_ns - start_ns
    if span <= 0:
        return invalid("window", "split window must be a positive half-open span")

    train_end = start_ns + (span * strategy.train_fraction_num) // strategy.train_fraction_den
    validation_end = train_end + (
        (span * strategy.validation_fraction_num) // strategy.validation_fraction_den
    )
    holdout_end = end_ns
    if not (start_ns < train_end < validation_end < holdout_end):
        return policy(
            "boundaries",
            "train/validation/holdout boundaries must be strictly increasing",
            train_end=train_end,
            validation_end=validation_end,
            holdout_end=holdout_end,
        )

    bar_ns = BAR_INTERVAL_M5_NS
    purge_ns = resolved_contract.leakage.purge_bars * bar_ns
    embargo_ns = resolved_contract.leakage.embargo_bars * bar_ns
    warm_ns = resolved_contract.data_windows.warm_up_bars * bar_ns
    # CT-12 requires purge/embargo to cover the max cited-producer warm-up bound.
    producer_bound = max(purge_ns, embargo_ns, warm_ns)
    purge_ns = max(purge_ns, producer_bound)
    embargo_ns = max(embargo_ns, producer_bound)
    producer = ProducerHorizon.try_create(
        "mis:regime_classifier_v1",
        producer_bound,
    )
    if is_refusal(producer):
        return producer

    train_boundary = SplitBoundary.try_create(train_end)
    if is_refusal(train_boundary):
        return train_boundary
    validation_boundary = SplitBoundary.try_create(validation_end)
    if is_refusal(validation_boundary):
        return validation_boundary
    holdout_boundary = SplitBoundary.try_create(holdout_end)
    if is_refusal(holdout_boundary):
        return holdout_boundary
    seal_boundary = SplitBoundary.try_create(validation_end)
    if is_refusal(seal_boundary):
        return seal_boundary

    segments = SplitManifest.default_split_segments(
        (train_boundary.value, validation_boundary.value, holdout_boundary.value)
    )
    if is_refusal(segments):
        return segments

    combined = SplitManifest.try_create(
        calendar_identity=calendar_identity,
        segments=segments.value,
        seal_boundary=seal_boundary.value,
        purge_width=Duration(value_ns=purge_ns),
        embargo_width=Duration(value_ns=embargo_ns),
        world=World.REPLAY,
        cited_producers=(producer.value,),
    )
    if is_refusal(combined):
        return combined

    # Per-role manifests pin the same calendar/seal/widths and a single segment
    # so train/validation/holdout each carry a distinct fingerprinted identity.
    train_only = _single_role_manifest(
        calendar_identity=calendar_identity,
        role=SegmentRole.TRAIN,
        boundary=train_boundary.value,
        seal_boundary=seal_boundary.value,
        purge_ns=purge_ns,
        embargo_ns=embargo_ns,
        producer=producer.value,
    )
    if is_refusal(train_only):
        return train_only
    validation_only = _single_role_manifest(
        calendar_identity=calendar_identity,
        role=SegmentRole.VALIDATION,
        boundary=validation_boundary.value,
        seal_boundary=seal_boundary.value,
        purge_ns=purge_ns,
        embargo_ns=embargo_ns,
        producer=producer.value,
    )
    if is_refusal(validation_only):
        return validation_only
    holdout_only = _single_role_manifest(
        calendar_identity=calendar_identity,
        role=SegmentRole.SEALED_TEST,
        boundary=holdout_boundary.value,
        seal_boundary=seal_boundary.value,
        purge_ns=purge_ns,
        embargo_ns=embargo_ns,
        producer=producer.value,
    )
    if is_refusal(holdout_only):
        return holdout_only

    seal = HoldoutSeal.from_manifest(combined.value, holdout_months)
    if is_refusal(seal):
        return seal

    as_of = fingerprint(
        {
            "class": "regime-corpus-as-of-set",
            "cleaned_artifact_id": cleaned.artifact_id,
            "cleaned_fp": _cleaned_fp_value(cleaned),
            "combined_split_id": combined.value.split_id,
            "train_split_id": train_only.value.split_id,
            "validation_split_id": validation_only.value.split_id,
            "holdout_split_id": holdout_only.value.split_id,
            "window_start_ns": start_ns,
            "window_end_ns": end_ns,
            "design_fp": resolved_contract.design_fp.value,
            "immutable": True,
        }
    )
    if is_refusal(as_of):
        return as_of

    return Ok(
        CorpusSplitBundle(
            train_manifest=train_only.value,
            validation_manifest=validation_only.value,
            holdout_manifest=holdout_only.value,
            combined_manifest=combined.value,
            holdout_seal=seal.value,
            as_of_set_fp=as_of.value,
            split_strategy=strategy,
            dataset_immutable=True,
            trains_model=False,
        )
    )


def _cleaned_fp_value(cleaned: CleanedCorpus) -> str:
    result = cleaned.fingerprint()
    if is_refusal(result):  # pragma: no cover
        raise RuntimeError("cleaned corpus fingerprint refused unexpectedly")
    return result.value.value


def _resolve_window_bounds(
    cleaned: CleanedCorpus,
    *,
    window_start_ns: object | None,
    window_end_ns: object | None,
) -> Result[tuple[int, int]]:
    if window_start_ns is None:
        start = min(row.event_time_ns for row in cleaned.rows)
    elif isinstance(window_start_ns, int) and not isinstance(window_start_ns, bool):
        start = window_start_ns
    else:
        return invalid(
            "window_start_ns",
            "window_start_ns is an int64 UTC nanosecond count",
            given=repr(window_start_ns),
        )
    if window_end_ns is None:
        end = max(row.event_time_ns for row in cleaned.rows) + BAR_INTERVAL_M5_NS
    elif isinstance(window_end_ns, int) and not isinstance(window_end_ns, bool):
        end = window_end_ns
    else:
        return invalid(
            "window_end_ns",
            "window_end_ns is an int64 UTC nanosecond count",
            given=repr(window_end_ns),
        )
    if end <= start:
        return invalid(
            "window",
            "split window is a half-open [start, end) over UTC ns",
            window_start_ns=start,
            window_end_ns=end,
        )
    return Ok((start, end))


def _single_role_manifest(
    *,
    calendar_identity: CalendarIdentity,
    role: SegmentRole,
    boundary: SplitBoundary,
    seal_boundary: SplitBoundary,
    purge_ns: int,
    embargo_ns: int,
    producer: ProducerHorizon,
) -> Result[SplitManifest]:
    segment = SplitSegment.try_create(role, boundary)
    if is_refusal(segment):
        return segment
    return SplitManifest.try_create(
        calendar_identity=calendar_identity,
        segments=(segment.value,),
        seal_boundary=seal_boundary,
        purge_width=Duration(value_ns=purge_ns),
        embargo_width=Duration(value_ns=embargo_ns),
        world=World.REPLAY,
        cited_producers=(producer,),
    )


def materialize_training_corpus(
    *,
    raw_rows: object,
    receipts: object,
    calendar_identity: object,
    holdout_months: object,
    design: RegimeClassifierDesign | None = None,
    context: object = ACQUISITION_CONTEXT,
    allow_live_network: object = False,
    train_model: object = False,
) -> Result[RegimeTrainingCorpus]:
    """Offline end-to-end: plan → acquire receipts → clean → fingerprinted splits.

    Never trains a model and never opens a live network path.
    """
    if train_model is True:
        return refuse_corpus_training(claim="train_model=True")
    if train_model not in (False, None):
        return invalid(
            "train_model",
            "train_model is False; Story 30.2 does not train",
            given=repr(train_model),
        )
    plan = build_acquisition_plan(design=design)
    if is_refusal(plan):
        return plan
    admitted = acquire_offline_corpus(
        plan.value,
        receipts,
        context=context,
        allow_live_network=allow_live_network,
    )
    if is_refusal(admitted):
        return admitted
    cleaned = clean_corpus(
        raw_rows,
        plan.value,
        source_receipts=admitted.value,
    )
    if is_refusal(cleaned):
        return cleaned
    splits = materialize_corpus_splits(
        cleaned.value,
        design=design,
        calendar_identity=calendar_identity,
        holdout_months=holdout_months,
    )
    if is_refusal(splits):
        return splits
    plan_fp = plan.value.fingerprint()
    if is_refusal(plan_fp):
        return plan_fp
    cleaned_fp = cleaned.value.fingerprint()
    if is_refusal(cleaned_fp):
        return cleaned_fp
    splits_fp = splits.value.fingerprint()
    if is_refusal(splits_fp):
        return splits_fp
    return Ok(
        RegimeTrainingCorpus(
            artifact_id=REGIME_CORPUS_ARTIFACT_ID,
            design_fp=plan.value.design_fp,
            contract_fp=plan.value.contract_fp,
            plan_fp=plan_fp.value,
            cleaned_fp=cleaned_fp.value,
            splits_fp=splits_fp.value,
            cleaned=cleaned.value,
            splits=splits.value,
            grants_money_path_authority=False,
            trains_model=False,
        )
    )
