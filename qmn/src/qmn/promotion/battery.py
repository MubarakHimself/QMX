"""Silent promotion precondition battery (TN-20 / DEC-0213).

Runs server-side against fresh state. The operator sees a passed-or-refused
list in plain words with the refusing check named — never the machinery.
Displayed-eligible is never a trade grant; activation is a separate act.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Ok, Result, is_refusal

from qmn.config.compiler import (
    VALUE_STATUS_RATIFIED,
    ResolvedNodeConfig,
)
from qmn.promotion._refuse import clean_token, invalid

__all__ = [
    "ADMISSION_IMPACTS",
    "ADMISSION_IMPACT_NONE",
    "ADMISSION_IMPACT_RELINT",
    "ADMISSION_IMPACT_RESIGN",
    "DEMO_BASELINE_ENVIRONMENT",
    "LIVE_BASELINE_ENVIRONMENT",
    "AdmissionLayerFreshState",
    "BatteryCheck",
    "BatteryCheckId",
    "ConfigGateFreshState",
    "Ct18CapabilityFreshState",
    "IdentityFingerprints",
    "LiveBaselineFreshState",
    "PromotionFreshState",
    "ProtectionFreshState",
    "SilentBatteryReport",
    "live_gating_from_config",
    "revalidate_fresh_state",
    "run_silent_battery",
]

ADMISSION_IMPACT_NONE: Final[str] = "none"
ADMISSION_IMPACT_RELINT: Final[str] = "relint"
ADMISSION_IMPACT_RESIGN: Final[str] = "resign"
ADMISSION_IMPACTS: Final[frozenset[str]] = frozenset(
    {ADMISSION_IMPACT_NONE, ADMISSION_IMPACT_RELINT, ADMISSION_IMPACT_RESIGN}
)
LIVE_BASELINE_ENVIRONMENT: Final[str] = "live"
DEMO_BASELINE_ENVIRONMENT: Final[str] = "demo"


class BatteryCheckId(StrEnum):
    """Internal check ids — never shown as operator machinery."""

    ADMISSION_LAYERS = "admission-layers"
    FINGERPRINTS = "fingerprints"
    CT18_CAPABILITIES = "ct18-capabilities"
    LIVE_BASELINES = "live-baselines"
    ADMISSION_IMPACT = "admission-impact"
    BLANKS = "blanks"
    VALUE_STATUS = "value-status"
    PROTECTION = "protection"


_OPERATOR_WORDS: Final[Mapping[BatteryCheckId, str]] = MappingProxyType(
    {
        BatteryCheckId.ADMISSION_LAYERS: "The three admission layers still pass",
        BatteryCheckId.FINGERPRINTS: "Book, BMS, bot, and config fingerprints match",
        BatteryCheckId.CT18_CAPABILITIES: "Venue capabilities still satisfy the Book",
        BatteryCheckId.LIVE_BASELINES: "Live-conditioned baselines are present",
        BatteryCheckId.ADMISSION_IMPACT: "No un-discharged resign admission-impact",
        BatteryCheckId.BLANKS: "No blank live-gating values",
        BatteryCheckId.VALUE_STATUS: "Every live-gating value-status is ratified",
        BatteryCheckId.PROTECTION: "Protection still admits a first intent",
    }
)

PROMOTION_BATTERY_CHECKS: Final[tuple[BatteryCheckId, ...]] = (
    BatteryCheckId.ADMISSION_LAYERS,
    BatteryCheckId.FINGERPRINTS,
    BatteryCheckId.CT18_CAPABILITIES,
    BatteryCheckId.LIVE_BASELINES,
    BatteryCheckId.ADMISSION_IMPACT,
    BatteryCheckId.BLANKS,
    BatteryCheckId.VALUE_STATUS,
)

REVALIDATION_CHECKS: Final[tuple[BatteryCheckId, ...]] = (
    BatteryCheckId.CT18_CAPABILITIES,
    BatteryCheckId.LIVE_BASELINES,
    BatteryCheckId.ADMISSION_IMPACT,
    BatteryCheckId.BLANKS,
    BatteryCheckId.VALUE_STATUS,
    BatteryCheckId.PROTECTION,
)


@dataclass(frozen=True, slots=True)
class AdmissionLayerFreshState:
    """AD-32 three-layer proofs revalidated at click time."""

    layer1_linters_passed: bool
    layer2_shakedown_passed: bool
    layer3_operator_signature_present: bool

    @property
    def all_passed(self) -> bool:
        return (
            self.layer1_linters_passed
            and self.layer2_shakedown_passed
            and self.layer3_operator_signature_present
        )

    @classmethod
    def try_create(
        cls,
        *,
        layer1_linters_passed: object,
        layer2_shakedown_passed: object,
        layer3_operator_signature_present: object,
    ) -> Result[AdmissionLayerFreshState]:
        flags = (
            ("layer1_linters_passed", layer1_linters_passed),
            ("layer2_shakedown_passed", layer2_shakedown_passed),
            ("layer3_operator_signature_present", layer3_operator_signature_present),
        )
        values: list[bool] = []
        for name, flag in flags:
            if not isinstance(flag, bool):
                return invalid(name, "an admission-layer proof is a bool", given=repr(flag))
            values.append(flag)
        return Ok(cls(values[0], values[1], values[2]))


@dataclass(frozen=True, slots=True)
class IdentityFingerprints:
    """Book / BMS / bot / config ``fp1`` set the battery matches to the card."""

    book: Fingerprint
    bms: Fingerprint
    bot: Fingerprint
    config: Fingerprint

    def matches(self, other: IdentityFingerprints) -> bool:
        return (
            self.book == other.book
            and self.bms == other.bms
            and self.bot == other.bot
            and self.config == other.config
        )

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "bms": self.bms.value,
                "book": self.book.value,
                "bot": self.bot.value,
                "config": self.config.value,
            }
        )

    @classmethod
    def try_create(
        cls,
        *,
        book: object,
        bms: object,
        bot: object,
        config: object,
    ) -> Result[IdentityFingerprints]:
        fields = (("book", book), ("bms", bms), ("bot", bot), ("config", config))
        values: dict[str, Fingerprint] = {}
        for name, raw in fields:
            if not isinstance(raw, Fingerprint):
                return invalid(
                    name,
                    "Book, BMS, bot, and config identities are fp1 fingerprints",
                    given=repr(raw),
                )
            values[name] = raw
        return Ok(
            cls(book=values["book"], bms=values["bms"], bot=values["bot"], config=values["config"])
        )


@dataclass(frozen=True, slots=True)
class Ct18CapabilityFreshState:
    """CT-18 bind-time capability satisfaction (required ⊆ declared)."""

    required: frozenset[str]
    declared: frozenset[str]

    @property
    def satisfied(self) -> bool:
        return self.required <= self.declared

    @classmethod
    def try_create(
        cls,
        *,
        required: object,
        declared: object,
    ) -> Result[Ct18CapabilityFreshState]:
        req = _token_set(required, "required")
        if is_refusal(req):
            return req
        dec = _token_set(declared, "declared")
        if is_refusal(dec):
            return dec
        return Ok(cls(required=req.value, declared=dec.value))


@dataclass(frozen=True, slots=True)
class LiveBaselineFreshState:
    """Live-conditioned SQS and live-path rung baselines (DEC-0230).

    A demo-conditioned baseline never satisfies a live promotion.
    """

    sqs_environment: str
    sqs_baseline_present: bool
    live_path_rung_baseline_present: bool

    @property
    def satisfied(self) -> bool:
        return (
            self.sqs_environment == LIVE_BASELINE_ENVIRONMENT
            and self.sqs_baseline_present
            and self.live_path_rung_baseline_present
        )

    @classmethod
    def try_create(
        cls,
        *,
        sqs_environment: object,
        sqs_baseline_present: object,
        live_path_rung_baseline_present: object,
    ) -> Result[LiveBaselineFreshState]:
        env = clean_token(sqs_environment)
        if env is None:
            return invalid(
                "sqs_environment",
                "SQS baseline environment is a non-empty token (live vs demo)",
                given=repr(sqs_environment),
            )
        if not isinstance(sqs_baseline_present, bool):
            return invalid(
                "sqs_baseline_present",
                "SQS baseline presence is a bool",
                given=repr(sqs_baseline_present),
            )
        if not isinstance(live_path_rung_baseline_present, bool):
            return invalid(
                "live_path_rung_baseline_present",
                "live-path rung baseline presence is a bool",
                given=repr(live_path_rung_baseline_present),
            )
        return Ok(
            cls(
                sqs_environment=env,
                sqs_baseline_present=sqs_baseline_present,
                live_path_rung_baseline_present=live_path_rung_baseline_present,
            )
        )


@dataclass(frozen=True, slots=True)
class ConfigGateFreshState:
    """Admission-impact stamp, blanks, and live-gating value-status."""

    admission_impact: str
    resign_discharged: bool
    blank_live_gating_names: tuple[str, ...]
    unratified_live_gating_names: tuple[str, ...]

    @property
    def impact_ok(self) -> bool:
        if self.admission_impact == ADMISSION_IMPACT_RESIGN:
            return self.resign_discharged
        return self.admission_impact in ADMISSION_IMPACTS

    @property
    def blanks_ok(self) -> bool:
        return not self.blank_live_gating_names

    @property
    def value_status_ok(self) -> bool:
        return not self.unratified_live_gating_names

    @classmethod
    def try_create(
        cls,
        *,
        admission_impact: object,
        resign_discharged: object,
        blank_live_gating_names: object = (),
        unratified_live_gating_names: object = (),
    ) -> Result[ConfigGateFreshState]:
        impact = clean_token(admission_impact)
        if impact not in ADMISSION_IMPACTS:
            return invalid(
                "admission_impact",
                "admission_impact is none | relint | resign",
                given=repr(admission_impact),
                allowed=sorted(ADMISSION_IMPACTS),
            )
        if not isinstance(resign_discharged, bool):
            return invalid(
                "resign_discharged",
                "resign discharge is a bool",
                given=repr(resign_discharged),
            )
        blanks = _name_tuple(blank_live_gating_names, "blank_live_gating_names")
        if is_refusal(blanks):
            return blanks
        unratified = _name_tuple(unratified_live_gating_names, "unratified_live_gating_names")
        if is_refusal(unratified):
            return unratified
        return Ok(
            cls(
                admission_impact=impact,
                resign_discharged=resign_discharged,
                blank_live_gating_names=blanks.value,
                unratified_live_gating_names=unratified.value,
            )
        )


@dataclass(frozen=True, slots=True)
class ProtectionFreshState:
    """Whether protection still admits a first intent — no invented KSA numbers."""

    entries_admitted: bool

    @classmethod
    def try_create(cls, *, entries_admitted: object) -> Result[ProtectionFreshState]:
        if not isinstance(entries_admitted, bool):
            return invalid(
                "entries_admitted",
                "protection readiness is a bool; the node invents no KSA numbers (FTR-07)",
                given=repr(entries_admitted),
            )
        return Ok(cls(entries_admitted=entries_admitted))


@dataclass(frozen=True, slots=True)
class PromotionFreshState:
    """Fresh click-time snapshot the silent battery and revalidation read."""

    admission: AdmissionLayerFreshState
    live_fingerprints: IdentityFingerprints
    card_fingerprints: IdentityFingerprints
    ct18: Ct18CapabilityFreshState
    live_baselines: LiveBaselineFreshState
    config_gate: ConfigGateFreshState
    protection: ProtectionFreshState


@dataclass(frozen=True, slots=True)
class BatteryCheck:
    """One named battery result. Operator display uses ``operator_words`` only."""

    check_id: BatteryCheckId
    passed: bool
    operator_words: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "check": self.operator_words,
                "passed": self.passed,
            }
        )


@dataclass(frozen=True, slots=True)
class SilentBatteryReport:
    """Passed-or-refused list in operator words; refusing check named."""

    checks: tuple[BatteryCheck, ...]
    passed: bool
    refusing_check: str | None
    refusing_check_id: str | None

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "passed": self.passed,
                "refusing_check": self.refusing_check,
                "results": [item.as_mapping() for item in self.checks],
            }
        )


def live_gating_from_config(
    config: object,
    *,
    admission_impact: object,
    resign_discharged: object,
) -> Result[ConfigGateFreshState]:
    """Derive blank/unratified live-gating names from a resolved node-config."""
    if not isinstance(config, ResolvedNodeConfig):
        return invalid(
            "config",
            "live-gating derivation reads a ResolvedNodeConfig",
            given=repr(type(config).__name__),
        )
    blanks: list[str] = []
    unratified: list[str] = []
    for name in config.live_blocking_rows():
        row = config.rows[name]
        if row.is_blank:
            blanks.append(name)
        if row.value_status != VALUE_STATUS_RATIFIED:
            unratified.append(name)
    return ConfigGateFreshState.try_create(
        admission_impact=admission_impact,
        resign_discharged=resign_discharged,
        blank_live_gating_names=tuple(blanks),
        unratified_live_gating_names=tuple(unratified),
    )


def run_silent_battery(fresh: object) -> Result[SilentBatteryReport]:
    """Run the promotion precondition battery against fresh state (TN-20)."""
    return _run_checks(fresh, PROMOTION_BATTERY_CHECKS)


def revalidate_fresh_state(fresh: object) -> Result[SilentBatteryReport]:
    """Revalidate config / capability / baseline / protection before first intent."""
    return _run_checks(fresh, REVALIDATION_CHECKS)


def _run_checks(
    fresh: object,
    check_ids: tuple[BatteryCheckId, ...],
) -> Result[SilentBatteryReport]:
    if not isinstance(fresh, PromotionFreshState):
        return invalid(
            "fresh",
            "the silent battery reads PromotionFreshState",
            given=repr(type(fresh).__name__),
        )
    checks: list[BatteryCheck] = []
    for check_id in check_ids:
        passed = _evaluate(fresh, check_id)
        checks.append(
            BatteryCheck(
                check_id=check_id,
                passed=passed,
                operator_words=_OPERATOR_WORDS[check_id],
            )
        )
    failed = next((item for item in checks if not item.passed), None)
    return Ok(
        SilentBatteryReport(
            checks=tuple(checks),
            passed=failed is None,
            refusing_check=None if failed is None else failed.operator_words,
            refusing_check_id=None if failed is None else failed.check_id.value,
        )
    )


def _evaluate(fresh: PromotionFreshState, check_id: BatteryCheckId) -> bool:
    if check_id is BatteryCheckId.ADMISSION_LAYERS:
        return fresh.admission.all_passed
    if check_id is BatteryCheckId.FINGERPRINTS:
        return fresh.live_fingerprints.matches(fresh.card_fingerprints)
    if check_id is BatteryCheckId.CT18_CAPABILITIES:
        return fresh.ct18.satisfied
    if check_id is BatteryCheckId.LIVE_BASELINES:
        return fresh.live_baselines.satisfied
    if check_id is BatteryCheckId.ADMISSION_IMPACT:
        return fresh.config_gate.impact_ok
    if check_id is BatteryCheckId.BLANKS:
        return fresh.config_gate.blanks_ok
    if check_id is BatteryCheckId.VALUE_STATUS:
        return fresh.config_gate.value_status_ok
    if check_id is BatteryCheckId.PROTECTION:
        return fresh.protection.entries_admitted
    return False


def _token_set(value: object, field: str) -> Result[frozenset[str]]:
    if isinstance(value, (set, frozenset, tuple, list)):
        tokens: list[str] = []
        for item in cast("Iterable[object]", value):
            token = clean_token(item)
            if token is None:
                return invalid(
                    field,
                    "each CT-18 capability is a non-empty token",
                    given=repr(item),
                )
            tokens.append(token)
        return Ok(frozenset(tokens))
    return invalid(
        field,
        "CT-18 capabilities are a set of capability tokens",
        given=repr(type(value).__name__),
    )


def _name_tuple(value: object, field: str) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str):
        token = clean_token(value)
        if token is None:
            return invalid(field, "a live-gating name is a non-empty token")
        return Ok((token,))
    if not isinstance(value, (tuple, list)):
        return invalid(
            field,
            "live-gating names are a sequence of tokens",
            given=repr(type(value).__name__),
        )
    names: list[str] = []
    for item in cast("Sequence[object]", value):
        token = clean_token(item)
        if token is None:
            return invalid(field, "a live-gating name is a non-empty token", given=repr(item))
        names.append(token)
    return Ok(tuple(names))
