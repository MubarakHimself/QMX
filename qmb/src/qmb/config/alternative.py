"""Alternative Trading Composition: PolicyPair validate/simulate (Story 58.2).

SCN-0020 Then 2 / DEC-0424 / DEC-0436 / DEC-0448: ``AlternativeRunConfig`` is a
second composition whose Book/BMS/bot keys are absent, not null. Validate and
simulate accept a complete PolicyPair. Evidence is QMB JSONL tagged
``composition_class: alternative`` plus a CT-07 occurrence-of edge to
``policy_pair_hash``. QMB issues internal ATC-simulate tokens. Dummy PolicyPair
is ``invalid input``. Sensing is not ATC. This fixture does not close GAP-0098
and does not claim ATC existed at inspect SHA 270e992 (DEC-0450).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint, canonical_bytes, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import EdgeType, LineageEdge

from qmb._refuse import clean_token, invalid, stale
from qmb.config.compiler import ResolvedRunConfig
from qmb.config.dummy import (
    DUMMY_POLICY_TOKENS,
    DUMMY_SENTINEL_TOKENS,
    refuse_dummy_policy_pair,
    refuse_sensing_as_atc,
)

__all__ = [
    "ACCOUNTING_POLICY_FIELDS",
    "ADAPTER_INTERNAL_SIMULATE",
    "ADMISSION_VERDICTS",
    "ALTERNATIVE_CONFIG_CLASS",
    "ALTERNATIVE_RUN_CONFIG_CLASS",
    "ALTERNATIVE_RUN_CONFIG_FORMAT_VERSION",
    "ATC_EVIDENCE_OWNER",
    "ATC_JOURNAL_CLASS",
    "ATC_SIMULATE_CLASS",
    "BOOK_KEYS",
    "CLIENT_AUTHORIZE_KEYS",
    "COMMAND_OPTIONAL_FIELDS",
    "COMMAND_REQUIRED_FIELDS",
    "COMPOSITION_CLASS_ALTERNATIVE",
    "CONSUMER_MIS",
    "CONSUMER_QMB",
    "CONSUMER_QML",
    "CONSUMER_QMN",
    "E2E_ADOPTION_CLOSED",
    "GAP_0098_ID",
    "GAP_0098_STATUS",
    "INSPECT_SHA_ATC_ABSENT",
    "P2_INT_001",
    "POLICY_PAIR_IDENTITY_FIELDS",
    "POLICY_SHAPE_OWNER",
    "RISK_POLICY_FIELDS",
    "VENUE_IMPORTER",
    "VERDICT_ADMITTED_LIVE",
    "VERDICT_ADMITTED_PAPER",
    "VERDICT_ADMITTED_SIMULATE",
    "VERDICT_NOT_PROMOTED",
    "VERDICT_REFUSED",
    "AdmissionResult",
    "AdoptedComposition",
    "AlternativeRunConfig",
    "AtcJournalRow",
    "AtcSimulateReceipt",
    "CommandBinding",
    "PolicyPair",
    "adopt_selected_composition",
    "alternative_run_config_identity",
    "evaluate_admission",
    "hash_policy_pair",
    "refuse_atc_implemented_at_inspect_sha",
    "simulate_alternative_run",
    "validate_alternative_run_config",
]

ALTERNATIVE_RUN_CONFIG_CLASS: Final[str] = "alternative-run-config"
ALTERNATIVE_RUN_CONFIG_FORMAT_VERSION: Final[int] = 1
ALTERNATIVE_CONFIG_CLASS: Final[str] = "alternative"
COMPOSITION_CLASS_ALTERNATIVE: Final[str] = "alternative"
ATC_JOURNAL_CLASS: Final[str] = "qmb-atc-journal-row"
ATC_SIMULATE_CLASS: Final[str] = "atc-simulate"
ADAPTER_INTERNAL_SIMULATE: Final[str] = "internal-simulate"
POLICY_SHAPE_OWNER: Final[str] = "COMP-QMF-RISK"
ATC_EVIDENCE_OWNER: Final[str] = "COMP-QMB"
VENUE_IMPORTER: Final[str] = "COMP-QMN"
GAP_0098_ID: Final[str] = "GAP-0098"
GAP_0098_STATUS: Final[str] = "open"
P2_INT_001: Final[str] = "P2-INT-001"
E2E_ADOPTION_CLOSED: Final[bool] = False
INSPECT_SHA_ATC_ABSENT: Final[str] = "270e992995c2378ca63cf6343254ef8140a8c97e"

CONSUMER_QML: Final[str] = "qml-authoring"
CONSUMER_QMB: Final[str] = "qmb-backtest-optimize"
CONSUMER_MIS: Final[str] = "optional-mis"
CONSUMER_QMN: Final[str] = "qmn-unattended-host"
_CONSUMERS: Final[frozenset[str]] = frozenset(
    {CONSUMER_QML, CONSUMER_QMB, CONSUMER_MIS, CONSUMER_QMN}
)

VERDICT_ADMITTED_SIMULATE: Final[str] = "admitted_simulate"
VERDICT_ADMITTED_PAPER: Final[str] = "admitted_paper"
VERDICT_ADMITTED_LIVE: Final[str] = "admitted_live"
VERDICT_NOT_PROMOTED: Final[str] = "not_promoted"
VERDICT_REFUSED: Final[str] = "refused"
ADMISSION_VERDICTS: Final[frozenset[str]] = frozenset(
    {
        VERDICT_ADMITTED_SIMULATE,
        VERDICT_ADMITTED_PAPER,
        VERDICT_ADMITTED_LIVE,
        VERDICT_NOT_PROMOTED,
        VERDICT_REFUSED,
    }
)

ACCOUNTING_POLICY_FIELDS: Final[tuple[str, ...]] = (
    "cash_identity",
    "position_identity",
    "fill_application",
    "valuation",
    "currency",
    "residual_meaning",
)
RISK_POLICY_FIELDS: Final[tuple[str, ...]] = (
    "max_gross",
    "halt",
    "sizing",
    "override_principal",
)
POLICY_PAIR_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "policy_pair_id",
    "policy_pair_version",
    "policy_pair_hash",
)
COMMAND_REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "account_id",
    "role",
    "instrument",
    "adapter_capability",
    "command_owner_epoch",
)
COMMAND_OPTIONAL_FIELDS: Final[tuple[str, ...]] = ("venue_kind", "credential_ref")
BOOK_KEYS: Final[frozenset[str]] = frozenset(
    {
        "bms",
        "bms_fp1",
        "bms_fragment",
        "bms_fragment_fp1",
        "book",
        "book_fp1",
        "book_fragment",
        "book_fragment_fp1",
        "bot",
        "bot_fp1",
    }
)
CLIENT_AUTHORIZE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "admitted",
        "authorize",
        "authorized",
        "client_ok",
        "ok",
        "permit",
        "permitted",
    }
)
_SECRET_FIELD_NAMES: Final[frozenset[str]] = frozenset(
    {
        "credential",
        "credential_value",
        "password",
        "secret",
        "secret_value",
    }
)
_EMPTY: Final[Mapping[str, object]] = MappingProxyType({})
_NS_PER_SECOND: Final[int] = 1_000_000_000
_NS_PER_MICROSECOND: Final[int] = 1_000
_SECONDS_PER_DAY: Final[int] = 86_400

_INCOMPLETE_PAIR_REASON: Final[str] = (
    "a complete PolicyPair carries accounting + risk fields from the CONTRACTS "
    "catalogue; inline bodies are never the sole identity (DEC-0424)"
)
_BOOK_ABSENT_REASON: Final[str] = (
    "AlternativeRunConfig Book/BMS/bot keys are absent, not null (DEC-0424)"
)
_CLIENT_AUTH_REASON: Final[str] = (
    "admission is an authoritative host result; client booleans cannot authorize "
    "(DEC-0436)"
)
_INSPECT_SHA_REASON: Final[str] = (
    "AlternativeRunConfig / PolicyPair were not in code at inspect SHA 270e992 "
    "(DEC-0450); this fixture must not claim they were"
)
_BOOK_SHAPED_REASON: Final[str] = (
    "when ATC is selected, QML/QMB/optional MIS/QMN adopt it; they do not stay "
    "secretly Book-shaped (DEC-0424)"
)


def alternative_run_config_identity() -> dict[str, object]:
    """Identity-bearing AlternativeRunConfig schema. Package SemVer is omitted."""
    return {
        "accounting_policy_fields": ACCOUNTING_POLICY_FIELDS,
        "admission_verdicts": tuple(sorted(ADMISSION_VERDICTS)),
        "atc_evidence_owner": ATC_EVIDENCE_OWNER,
        "class": ALTERNATIVE_RUN_CONFIG_CLASS,
        "config_class": ALTERNATIVE_CONFIG_CLASS,
        "e2e_adoption_closed": E2E_ADOPTION_CLOSED,
        "format_version": ALTERNATIVE_RUN_CONFIG_FORMAT_VERSION,
        "gap_0098_id": GAP_0098_ID,
        "gap_0098_status": GAP_0098_STATUS,
        "policy_pair_identity_fields": POLICY_PAIR_IDENTITY_FIELDS,
        "policy_shape_owner": POLICY_SHAPE_OWNER,
        "risk_policy_fields": RISK_POLICY_FIELDS,
        "venue_importer": VENUE_IMPORTER,
    }


def refuse_atc_implemented_at_inspect_sha(sha: object) -> Result[None]:
    """Refuse a claim that ATC existed at the brownfield inspect SHA."""
    token = clean_token(sha)
    if token is None:
        return invalid(
            "sha",
            "an inspect SHA is a non-empty hex token",
            given=repr(sha),
        )
    folded = token.strip().casefold()
    if folded == INSPECT_SHA_ATC_ABSENT or folded.startswith("270e992"):
        return invalid("sha", _INSPECT_SHA_REASON, given=token)
    return Ok(None)


@dataclass(frozen=True, slots=True)
class PolicyPair:
    """Versioned immutable PolicyPair. Hash preimage is accounting + risk, no secrets."""

    policy_pair_id: str
    policy_pair_version: int
    policy_pair_hash: Fingerprint
    accounting: Mapping[str, object]
    risk: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "accounting", _freeze_mapping(self.accounting))
        object.__setattr__(self, "risk", _freeze_mapping(self.risk))

    def identity(self) -> dict[str, object]:
        """``{policy_pair_id, policy_pair_version, policy_pair_hash}`` — not the bodies."""
        return {
            "policy_pair_id": self.policy_pair_id,
            "policy_pair_hash": self.policy_pair_hash.value,
            "policy_pair_version": self.policy_pair_version,
        }

    def inline_bodies(self) -> dict[str, object]:
        """Accounting + risk field copy. Never the sole identity."""
        return {
            "accounting": _plain_mapping(self.accounting),
            "risk": _plain_mapping(self.risk),
        }


@dataclass(frozen=True, slots=True)
class CommandBinding:
    """Command target including ``command_owner_epoch``. A filter is not a target."""

    account_id: str
    role: str
    instrument: str
    adapter_capability: str
    command_owner_epoch: int
    venue_kind: str | None = None
    credential_ref: str | None = None

    def fp1_identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "account_id": self.account_id,
            "adapter_capability": self.adapter_capability,
            "command_owner_epoch": self.command_owner_epoch,
            "instrument": self.instrument,
            "role": self.role,
        }
        if self.credential_ref is not None:
            body["credential_ref"] = self.credential_ref
        if self.venue_kind is not None:
            body["venue_kind"] = self.venue_kind
        return body


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    """Authoritative host admission. Client booleans cannot authorize."""

    verdict: str
    checked_grant_ids: tuple[str, ...]
    health_evidence_ref: str
    health_revision: int
    evaluator_principal: str
    decided_at_ns: int
    max_age_ns: int
    observed_at_ns: int
    paper_run_ref: str | None = None
    paper_evidence_ref: str | None = None
    l17_promote_ref: str | None = None

    def fp1_identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "checked_grant_ids": list(self.checked_grant_ids),
            "decided_at_ns": self.decided_at_ns,
            "evaluator_principal": self.evaluator_principal,
            "health_evidence_ref": self.health_evidence_ref,
            "health_revision": self.health_revision,
            "observation_freshness": {
                "max_age_ns": self.max_age_ns,
                "observed_at_ns": self.observed_at_ns,
            },
            "verdict": self.verdict,
        }
        if self.l17_promote_ref is not None:
            body["l17_promote_ref"] = self.l17_promote_ref
        if self.paper_evidence_ref is not None:
            body["paper_evidence_ref"] = self.paper_evidence_ref
        if self.paper_run_ref is not None:
            body["paper_run_ref"] = self.paper_run_ref
        return body


@dataclass(frozen=True, slots=True)
class AlternativeRunConfig:
    """Second trading composition: complete PolicyPair, Book keys absent."""

    format_version: int
    config_class: str
    composition_fp: Fingerprint
    policy_pair: PolicyPair
    command: CommandBinding
    admission: AdmissionResult
    fingerprint: Fingerprint

    def fp1_identity(self) -> dict[str, object]:
        """Composition identity. Inline PolicyPair bodies and admission are excluded."""
        return {
            "class": ALTERNATIVE_RUN_CONFIG_CLASS,
            "command": self.command.fp1_identity(),
            "config_class": self.config_class,
            "format_version": self.format_version,
            "policy_pair_hash": self.policy_pair.policy_pair_hash.value,
            "policy_pair_id": self.policy_pair.policy_pair_id,
            "policy_pair_version": self.policy_pair.policy_pair_version,
        }

    def payload(self) -> dict[str, object]:
        """CONTRACTS §11 envelope. Book/BMS/bot keys omitted, never null."""
        return {
            "admission": self.admission.fp1_identity(),
            "command": self.command.fp1_identity(),
            "composition_fp": self.composition_fp.value,
            "config_class": self.config_class,
            "policy_pair": self.policy_pair.inline_bodies(),
            "policy_pair_hash": self.policy_pair.policy_pair_hash.value,
            "policy_pair_id": self.policy_pair.policy_pair_id,
            "policy_pair_version": self.policy_pair.policy_pair_version,
        }


@dataclass(frozen=True, slots=True)
class AtcJournalRow:
    """QMB JSONL evidence row tagged ``composition_class: alternative``."""

    composition_fp: Fingerprint
    policy_pair_hash: Fingerprint
    simulate_token: Fingerprint
    lineage: LineageEdge
    fingerprint: Fingerprint

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": ATC_JOURNAL_CLASS,
            "composition_class": COMPOSITION_CLASS_ALTERNATIVE,
            "composition_fp": self.composition_fp.value,
            "lineage_fp1": self.lineage.edge_fingerprint.value,
            "owner": ATC_EVIDENCE_OWNER,
            "policy_pair_hash": self.policy_pair_hash.value,
            "simulate_token": self.simulate_token.value,
        }

    def canonical_line(self) -> Result[bytes]:
        """Pinned JSONL line. This module produces the line, not the file."""
        serialized = canonical_bytes(self.fp1_identity())
        if is_refusal(serialized):
            return serialized
        return Ok(serialized.value + b"\n")


@dataclass(frozen=True, slots=True)
class AtcSimulateReceipt:
    """Validate+simulate outcome: host admission, JSONL row, QMB simulate token."""

    config: AlternativeRunConfig
    journal: AtcJournalRow
    simulate_token: Fingerprint

    def jsonl_line(self) -> Result[bytes]:
        return self.journal.canonical_line()


@dataclass(frozen=True, slots=True)
class AdoptedComposition:
    """Consumer binding to the selected composition. ATC is not secretly Book-shaped."""

    consumer: str
    config_class: str
    composition_fp: Fingerprint | None
    policy_pair_hash: Fingerprint | None
    book_fp1: Fingerprint | None
    venue_importer: str

    def fp1_identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "config_class": self.config_class,
            "consumer": self.consumer,
            "venue_importer": self.venue_importer,
        }
        if self.book_fp1 is not None:
            body["book_fp1"] = self.book_fp1.value
        if self.composition_fp is not None:
            body["composition_fp"] = self.composition_fp.value
        if self.policy_pair_hash is not None:
            body["policy_pair_hash"] = self.policy_pair_hash.value
        return body


def hash_policy_pair(
    accounting: object,
    risk: object,
) -> Result[Fingerprint]:
    """fp1 over accounting + risk fields. Secrets are refused, never hashed."""
    acc = _require_section(accounting, "accounting", ACCOUNTING_POLICY_FIELDS)
    if is_refusal(acc):
        return acc
    rsk = _require_section(risk, "risk", RISK_POLICY_FIELDS)
    if is_refusal(rsk):
        return rsk
    dummy = refuse_dummy_policy_pair({"accounting": acc.value, "risk": rsk.value})
    if dummy is not None:
        return dummy
    return fingerprint({"accounting": acc.value, "risk": rsk.value})


def evaluate_admission(
    command: CommandBinding,
    *,
    checked_grant_ids: object,
    health_evidence_ref: object,
    health_revision: object,
    decided_at: object,
    observed_at: object,
    max_age: object,
    paper_run_ref: object = None,
    paper_evidence_ref: object = None,
    l17_promote_ref: object = None,
    client_claim: object = None,
) -> Result[AdmissionResult]:
    """Host-evaluated admission. Stale observations refuse. Live needs paper+L17."""
    claimed = _refuse_client_authorization(client_claim)
    if claimed is not None:
        return claimed
    grants = _require_grant_ids(checked_grant_ids)
    if is_refusal(grants):
        return grants
    health_ref = clean_token(health_evidence_ref)
    if health_ref is None:
        return invalid(
            "health_evidence_ref",
            "host admission cites health evidence",
            given=repr(health_evidence_ref),
        )
    revision = _positive_int(health_revision, "health_revision")
    if is_refusal(revision):
        return revision
    decided = _parse_instant(decided_at, "decided_at")
    if is_refusal(decided):
        return decided
    observed = _parse_instant(observed_at, "observed_at")
    if is_refusal(observed):
        return observed
    age = _parse_max_age(max_age)
    if is_refusal(age):
        return age
    if observed.value.value_ns > decided.value.value_ns:
        return invalid(
            "observed_at",
            "observation_freshness.observed_at cannot be after decided_at",
        )
    if decided.value.value_ns - observed.value.value_ns > age.value:
        return stale(
            "observation_freshness",
            "stale observations refuse; admission is a host result (DEC-0436)",
            max_age_ns=age.value,
            age_ns=decided.value.value_ns - observed.value.value_ns,
        )
    paper_run = _optional_token(paper_run_ref, "paper_run_ref")
    if is_refusal(paper_run):
        return paper_run
    paper_ev = _optional_token(paper_evidence_ref, "paper_evidence_ref")
    if is_refusal(paper_ev):
        return paper_ev
    promote = _optional_token(l17_promote_ref, "l17_promote_ref")
    if is_refusal(promote):
        return promote
    verdict = _host_verdict(
        command,
        paper_run=paper_run.value,
        paper_evidence=paper_ev.value,
        l17=promote.value,
    )
    return Ok(
        AdmissionResult(
            verdict=verdict,
            checked_grant_ids=grants.value,
            health_evidence_ref=health_ref,
            health_revision=revision.value,
            evaluator_principal="host",
            decided_at_ns=decided.value.value_ns,
            max_age_ns=age.value,
            observed_at_ns=observed.value.value_ns,
            paper_run_ref=paper_run.value,
            paper_evidence_ref=paper_ev.value,
            l17_promote_ref=promote.value,
        )
    )


def validate_alternative_run_config(payload: object) -> Result[AlternativeRunConfig]:
    """Validate an AlternativeRunConfig. Book keys absent; PolicyPair complete."""
    if isinstance(payload, AlternativeRunConfig):
        return Ok(payload)
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "an AlternativeRunConfig is a key->value mapping",
            given=repr(type(payload).__name__),
        )
    body = cast("Mapping[str, object]", payload)
    book_hit = _refuse_book_keys(body)
    if book_hit is not None:
        return book_hit
    sensing = refuse_sensing_as_atc(body)
    if is_refusal(sensing):
        return sensing
    config_class = clean_token(body.get("config_class"))
    if config_class != ALTERNATIVE_CONFIG_CLASS:
        return invalid(
            "config_class",
            "AlternativeRunConfig carries config_class=alternative",
            given=repr(body.get("config_class")),
        )
    pair = _parse_policy_pair(body)
    if is_refusal(pair):
        return pair
    command = _parse_command(body.get("command"))
    if is_refusal(command):
        return command
    admission_body = body.get("admission")
    if not isinstance(admission_body, Mapping):
        return invalid(
            "admission",
            "admission is an authoritative host result mapping",
            given=repr(type(admission_body).__name__),
        )
    admission_map = cast("Mapping[str, object]", admission_body)
    freshness = admission_map.get("observation_freshness")
    if not isinstance(freshness, Mapping):
        return invalid(
            "observation_freshness",
            "admission carries observation_freshness {max_age, observed_at}",
            given=repr(type(freshness).__name__),
        )
    freshness_map = cast("Mapping[str, object]", freshness)
    max_age = freshness_map.get("max_age", freshness_map.get("max_age_ns"))
    observed_at = freshness_map.get("observed_at", freshness_map.get("observed_at_ns"))
    admission = evaluate_admission(
        command.value,
        checked_grant_ids=admission_map.get("checked_grant_ids"),
        health_evidence_ref=admission_map.get("health_evidence_ref"),
        health_revision=admission_map.get("health_revision"),
        decided_at=admission_map.get("decided_at", admission_map.get("decided_at_ns")),
        observed_at=observed_at,
        max_age=max_age,
        paper_run_ref=admission_map.get("paper_run_ref"),
        paper_evidence_ref=admission_map.get("paper_evidence_ref"),
        l17_promote_ref=admission_map.get("l17_promote_ref"),
        client_claim=admission_map,
    )
    if is_refusal(admission):
        return admission
    identity = {
        "class": ALTERNATIVE_RUN_CONFIG_CLASS,
        "command": command.value.fp1_identity(),
        "config_class": ALTERNATIVE_CONFIG_CLASS,
        "format_version": ALTERNATIVE_RUN_CONFIG_FORMAT_VERSION,
        "policy_pair_hash": pair.value.policy_pair_hash.value,
        "policy_pair_id": pair.value.policy_pair_id,
        "policy_pair_version": pair.value.policy_pair_version,
    }
    derived = fingerprint(identity)
    if is_refusal(derived):
        return derived
    supplied = body.get("composition_fp")
    if supplied is not None:
        parsed = _coerce_fingerprint(supplied)
        if parsed is None or parsed.value != derived.value.value:
            return invalid(
                "composition_fp",
                "composition_fp is fp1 over composition identity; it is never caller-minted",
                given=repr(supplied),
            )
    return Ok(
        AlternativeRunConfig(
            format_version=ALTERNATIVE_RUN_CONFIG_FORMAT_VERSION,
            config_class=ALTERNATIVE_CONFIG_CLASS,
            composition_fp=derived.value,
            policy_pair=pair.value,
            command=command.value,
            admission=admission.value,
            fingerprint=derived.value,
        )
    )


def simulate_alternative_run(
    payload: object,
    *,
    writer: object,
) -> Result[AtcSimulateReceipt]:
    """Validate then simulate. Issues a QMB internal ATC-simulate token; no venue."""
    if not isinstance(writer, WriterId):
        return invalid(
            "writer",
            "simulate mints CT-07 lineage under a WriterId",
            given=repr(type(writer).__name__),
        )
    validated = validate_alternative_run_config(payload)
    if is_refusal(validated):
        return validated
    config = validated.value
    if config.command.adapter_capability != ADAPTER_INTERNAL_SIMULATE:
        return invalid(
            "adapter_capability",
            "QMB simulate uses adapter_capability=internal-simulate; QMN is the "
            "only qmf-venue importer",
            given=config.command.adapter_capability,
        )
    if config.command.venue_kind is not None:
        return invalid(
            "venue_kind",
            "ATC simulate omits venue_kind; QMB issues internal tokens, never venue tokens",
        )
    if config.admission.verdict != VERDICT_ADMITTED_SIMULATE:
        return invalid(
            "admission",
            "simulate requires host verdict admitted_simulate; live ATC without "
            "paper+L17 is not_promoted",
            verdict=config.admission.verdict,
        )
    token_identity: dict[str, object] = {
        "account_id": config.command.account_id,
        "class": ATC_SIMULATE_CLASS,
        "command_owner_epoch": config.command.command_owner_epoch,
        "composition_fp": config.composition_fp.value,
        "issuer": ATC_EVIDENCE_OWNER,
        "role": config.command.role,
    }
    token = fingerprint(token_identity)
    if is_refusal(token):
        return token
    row_pre = fingerprint(
        {
            "class": ATC_JOURNAL_CLASS,
            "composition_class": COMPOSITION_CLASS_ALTERNATIVE,
            "composition_fp": config.composition_fp.value,
            "owner": ATC_EVIDENCE_OWNER,
            "policy_pair_hash": config.policy_pair.policy_pair_hash.value,
            "simulate_token": token.value.value,
        }
    )
    if is_refusal(row_pre):
        return row_pre
    lineage = LineageEdge.try_create(
        EdgeType.OCCURRENCE_OF,
        row_pre.value,
        config.policy_pair.policy_pair_hash,
        writer,
    )
    if is_refusal(lineage):
        return lineage
    journal_identity = {
        "class": ATC_JOURNAL_CLASS,
        "composition_class": COMPOSITION_CLASS_ALTERNATIVE,
        "composition_fp": config.composition_fp.value,
        "lineage_fp1": lineage.value.edge_fingerprint.value,
        "owner": ATC_EVIDENCE_OWNER,
        "policy_pair_hash": config.policy_pair.policy_pair_hash.value,
        "simulate_token": token.value.value,
    }
    journal_fp = fingerprint(journal_identity)
    if is_refusal(journal_fp):
        return journal_fp
    journal = AtcJournalRow(
        composition_fp=config.composition_fp,
        policy_pair_hash=config.policy_pair.policy_pair_hash,
        simulate_token=token.value,
        lineage=lineage.value,
        fingerprint=journal_fp.value,
    )
    return Ok(
        AtcSimulateReceipt(
            config=config,
            journal=journal,
            simulate_token=token.value,
        )
    )


def adopt_selected_composition(
    selected: object,
    *,
    consumer: object,
    remaining: object = None,
) -> Result[AdoptedComposition]:
    """Bind QML/QMB/optional MIS/QMN to the selected composition."""
    token = clean_token(consumer)
    if token is None or token not in _CONSUMERS:
        return invalid(
            "consumer",
            "ATC consumers are qml-authoring, qmb-backtest-optimize, optional-mis, "
            "or qmn-unattended-host",
            given=repr(consumer),
        )
    leftover = remaining if remaining is not None else _EMPTY
    if not isinstance(leftover, Mapping):
        return invalid(
            "remaining",
            "consumer remaining keys are a mapping",
            given=repr(type(leftover).__name__),
        )
    leftover_map = cast("Mapping[str, object]", leftover)
    if isinstance(selected, AlternativeRunConfig):
        book_hit = _refuse_book_keys(leftover_map)
        if book_hit is not None:
            return invalid(
                str(book_hit.context.get("field", "remaining")),
                _BOOK_SHAPED_REASON,
            )
        sensing = refuse_sensing_as_atc(leftover_map)
        if is_refusal(sensing):
            return sensing
        return Ok(
            AdoptedComposition(
                consumer=token,
                config_class=ALTERNATIVE_CONFIG_CLASS,
                composition_fp=selected.composition_fp,
                policy_pair_hash=selected.policy_pair.policy_pair_hash,
                book_fp1=None,
                venue_importer=VENUE_IMPORTER,
            )
        )
    if isinstance(selected, ResolvedRunConfig):
        return Ok(
            AdoptedComposition(
                consumer=token,
                config_class="resolved-run-config",
                composition_fp=None,
                policy_pair_hash=None,
                book_fp1=selected.book_fp1,
                venue_importer=VENUE_IMPORTER,
            )
        )
    if isinstance(selected, Mapping):
        selected_map = cast("Mapping[str, object]", selected)
        sensing = refuse_sensing_as_atc(selected_map)
        if is_refusal(sensing):
            return sensing
        labels = {
            clean_token(selected_map.get(key))
            for key in ("class", "config_class", "kind", "label")
        }
        folded = {item.strip().casefold().replace("_", "-") for item in labels if item is not None}
        if folded & {"ungoverned", "ungoverned-work-config", "sensing", "research"}:
            return invalid(
                "label",
                "sensing/research/UngovernedWorkConfig is not an Alternative Trading "
                "Composition and is not a QMN seat (DEC-0424)",
            )
        parsed = validate_alternative_run_config(selected_map)
        if is_ok(parsed):
            return adopt_selected_composition(
                parsed.value,
                consumer=token,
                remaining=leftover_map,
            )
        return parsed
    return invalid(
        "selected",
        "a selected composition is AlternativeRunConfig or ResolvedRunConfig",
        given=repr(type(selected).__name__),
    )


def _parse_policy_pair(body: Mapping[str, object]) -> Result[PolicyPair]:
    pair_id = clean_token(body.get("policy_pair_id"))
    if pair_id is None:
        return invalid("policy_pair_id", "PolicyPair identity includes policy_pair_id")
    dummy_id = (
        pair_id in DUMMY_SENTINEL_TOKENS
        or pair_id.casefold() in {item.casefold() for item in DUMMY_SENTINEL_TOKENS}
        or pair_id.casefold() in DUMMY_POLICY_TOKENS
    )
    if dummy_id:
        return invalid("policy_pair_id", "dummy PolicyPair is invalid input", sentinel=pair_id)
    version = _positive_int(body.get("policy_pair_version"), "policy_pair_version")
    if is_refusal(version):
        return version
    inline = body.get("policy_pair")
    if not isinstance(inline, Mapping):
        return invalid(
            "policy_pair",
            "inline PolicyPair bodies are a mapping of accounting + risk fields",
            given=repr(type(inline).__name__),
        )
    inline_map = cast("Mapping[str, object]", inline)
    dummy = refuse_dummy_policy_pair(
        {
            "accounting": inline_map.get("accounting"),
            "policy_pair_hash": body.get("policy_pair_hash"),
            "policy_pair_id": pair_id,
            "risk": inline_map.get("risk"),
        }
    )
    if dummy is not None:
        return dummy
    hashed = hash_policy_pair(inline_map.get("accounting"), inline_map.get("risk"))
    if is_refusal(hashed):
        return hashed
    supplied = body.get("policy_pair_hash")
    if supplied is not None:
        parsed = _coerce_fingerprint(supplied)
        if parsed is None or parsed.value != hashed.value.value:
            return invalid(
                "policy_pair_hash",
                "policy_pair_hash is fp1 over accounting + risk fields with no secrets",
                given=repr(supplied),
            )
    accounting = _require_section(
        inline_map.get("accounting"),
        "accounting",
        ACCOUNTING_POLICY_FIELDS,
    )
    if is_refusal(accounting):
        return accounting
    risk = _require_section(inline_map.get("risk"), "risk", RISK_POLICY_FIELDS)
    if is_refusal(risk):
        return risk
    return Ok(
        PolicyPair(
            policy_pair_id=pair_id,
            policy_pair_version=version.value,
            policy_pair_hash=hashed.value,
            accounting=accounting.value,
            risk=risk.value,
        )
    )


def _parse_command(value: object) -> Result[CommandBinding]:
    if not isinstance(value, Mapping):
        return invalid(
            "command",
            "command is a mapping including command_owner_epoch",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)
    book_hit = _refuse_book_keys(body)
    if book_hit is not None:
        return book_hit
    account = clean_token(body.get("account_id"))
    role = clean_token(body.get("role"))
    instrument = clean_token(body.get("instrument"))
    adapter = clean_token(body.get("adapter_capability"))
    if account is None or role is None or instrument is None or adapter is None:
        return invalid(
            "command",
            "command binds account_id, role, instrument, adapter_capability, "
            "and command_owner_epoch",
        )
    epoch = _positive_int(body.get("command_owner_epoch"), "command_owner_epoch")
    if is_refusal(epoch):
        return epoch
    venue = _optional_token(body.get("venue_kind"), "venue_kind")
    if is_refusal(venue):
        return venue
    cred = _optional_token(body.get("credential_ref"), "credential_ref")
    if is_refusal(cred):
        return cred
    if "credential" in body or "secret" in body or "password" in body:
        return invalid(
            "command",
            "credentials appear only as typed refs; secret values are excluded "
            "from PolicyPair and command identity",
        )
    return Ok(
        CommandBinding(
            account_id=account,
            role=role,
            instrument=instrument,
            adapter_capability=adapter,
            command_owner_epoch=epoch.value,
            venue_kind=venue.value,
            credential_ref=cred.value,
        )
    )


def _require_section(
    value: object,
    field: str,
    required: tuple[str, ...],
) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(
            field,
            _INCOMPLETE_PAIR_REASON,
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    out: dict[str, object] = {}
    for raw_key, item in mapping.items():
        if not isinstance(raw_key, str) or raw_key.strip() == "":
            return invalid(field, "PolicyPair field names are non-empty strings")
        if raw_key in _SECRET_FIELD_NAMES:
            return invalid(
                raw_key,
                "PolicyPair hash preimage is accounting + risk fields with no secrets",
            )
        if item is None:
            return invalid(
                raw_key,
                "absent PolicyPair fields are omitted, never null",
                section=field,
            )
        token = clean_token(item)
        if token is None and not isinstance(item, (int, bool)):
            return invalid(raw_key, "PolicyPair field values are tokens or integers")
        if isinstance(item, bool):
            return invalid(raw_key, "PolicyPair field values are not booleans")
        if isinstance(item, int):
            out[raw_key] = item
        else:
            out[raw_key] = token
    missing = [name for name in required if name not in out]
    if missing:
        return invalid(field, _INCOMPLETE_PAIR_REASON, missing=missing)
    extra = sorted(name for name in out if name not in required)
    if extra:
        return invalid(
            field,
            "PolicyPair sections carry only the CONTRACTS catalogue fields",
            extra=extra,
        )
    return Ok(out)


def _require_grant_ids(value: object) -> Result[tuple[str, ...]]:
    if not isinstance(value, (list, tuple)):
        return invalid(
            "checked_grant_ids",
            "host admission records checked_grant_ids as a sequence of grant ids",
            given=repr(type(value).__name__),
        )
    sequence = cast("Sequence[object]", value)
    out: list[str] = []
    for item in sequence:
        token = clean_token(item)
        if token is None:
            return invalid(
                "checked_grant_ids",
                "each checked grant id is a non-empty token",
                given=repr(item),
            )
        out.append(token)
    return Ok(tuple(out))


def _host_verdict(
    command: CommandBinding,
    *,
    paper_run: str | None,
    paper_evidence: str | None,
    l17: str | None,
) -> str:
    live_requested = (
        command.venue_kind is not None
        or command.adapter_capability != ADAPTER_INTERNAL_SIMULATE
    )
    papered = paper_run is not None and paper_evidence is not None
    if live_requested:
        if papered and l17 is not None:
            return VERDICT_ADMITTED_LIVE
        return VERDICT_NOT_PROMOTED
    if papered:
        return VERDICT_ADMITTED_PAPER
    return VERDICT_ADMITTED_SIMULATE


def _refuse_client_authorization(claim: object) -> TypedRefusal | None:
    if claim is None:
        return None
    if not isinstance(claim, Mapping):
        return invalid(
            "admission",
            "a client admission claim is a mapping",
            given=repr(type(claim).__name__),
        )
    mapping = cast("Mapping[str, object]", claim)
    principal = clean_token(mapping.get("evaluator_principal"))
    if principal is not None and principal != "host":
        return invalid("evaluator_principal", _CLIENT_AUTH_REASON, given=principal)
    for key in CLIENT_AUTHORIZE_KEYS:
        if mapping.get(key) is True:
            return invalid(key, _CLIENT_AUTH_REASON)
    return None


def _refuse_book_keys(mapping: Mapping[str, object]) -> TypedRefusal | None:
    present = sorted(name for name in mapping if name in BOOK_KEYS)
    if present:
        return invalid(present[0], _BOOK_ABSENT_REASON, extra=present)
    return None


def _optional_token(value: object, field: str) -> Result[str | None]:
    if value is None:
        return Ok(None)
    token = clean_token(value)
    if token is None:
        return invalid(field, "optional tokens are omitted when absent, never null")
    return Ok(token)


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, "this field is a positive integer", given=repr(value))
    return Ok(value)


def _parse_max_age(value: object) -> Result[int]:
    if isinstance(value, bool):
        return invalid("max_age", "observation max_age is a duration, not a boolean")
    if isinstance(value, int) and value >= 0:
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid("max_age", "observation max_age is nanoseconds or a duration token")
    folded = token.strip().casefold()
    if folded.endswith("s") and folded[:-1].isdigit():
        return Ok(int(folded[:-1]) * _NS_PER_SECOND)
    if folded.isdigit():
        return Ok(int(folded))
    return invalid("max_age", "observation max_age is nanoseconds or an <int>s token")


def _parse_instant(value: object, field: str) -> Result[Instant]:
    if isinstance(value, Instant):
        return Ok(value)
    if isinstance(value, bool):
        return invalid(field, "an instant is not a boolean")
    if isinstance(value, int):
        return Instant.try_create(value)
    token = clean_token(value)
    if token is None:
        return invalid(field, "an instant is int64 ns or an RFC-3339 token")
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        return invalid(field, "an instant is int64 ns or an RFC-3339 token", given=token)
    if parsed.tzinfo is None:
        return invalid(field, "an instant token is timezone-aware")
    aware = parsed.astimezone(timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = aware - epoch
    ns = (
        delta.days * _SECONDS_PER_DAY * _NS_PER_SECOND
        + delta.seconds * _NS_PER_SECOND
        + delta.microseconds * _NS_PER_MICROSECOND
    )
    return Instant.try_create(ns)


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _plain_mapping(value: Mapping[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Fingerprint):
            out[key] = item.value
        else:
            out[key] = item
    return out


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    frozen: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Mapping):
            nested = cast("Mapping[str, object]", item)
            frozen[key] = _freeze_mapping(nested)
        elif isinstance(item, (list, tuple)):
            sequence = cast("Sequence[object]", item)
            frozen[key] = tuple(sequence)
        else:
            frozen[key] = item
    return MappingProxyType(frozen)
