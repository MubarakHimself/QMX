"""QMN adopts a selected ATC at simulate; live without paper+L17 is not_promoted.

Story 58.2 / SCN-0020: when AlternativeRunConfig is selected the node does not
stay secretly Book-shaped. This epic stays at simulate. QMB issues internal
ATC-simulate tokens. QMN remains the only qmf-venue importer and does not
import venue on this path. Sensing is not a seat.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmb.config.alternative import (
    ADAPTER_INTERNAL_SIMULATE,
    ALTERNATIVE_CONFIG_CLASS,
    ATC_EVIDENCE_OWNER,
    BOOK_KEYS,
    CONSUMER_QMN,
    VENUE_IMPORTER,
    VERDICT_ADMITTED_LIVE,
    VERDICT_ADMITTED_PAPER,
    VERDICT_ADMITTED_SIMULATE,
    VERDICT_NOT_PROMOTED,
    AlternativeRunConfig,
    AtcSimulateReceipt,
    adopt_selected_composition,
    validate_alternative_run_config,
)
from qmb.config.dummy import refuse_sensing_as_atc
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmn.seats._refuse import clean_token, invalid

__all__ = [
    "ATC_SEAT_ISSUES_VENUE_TOKEN",
    "ATC_SIMULATE_TOKEN_ISSUER",
    "VENUE_IMPORTER",
    "AtcSeatAdoption",
    "adopt_atc_seat",
]

ATC_SEAT_ISSUES_VENUE_TOKEN: Final[bool] = False
ATC_SIMULATE_TOKEN_ISSUER: Final[str] = ATC_EVIDENCE_OWNER
_EMPTY_REMAINING: Final[Mapping[str, object]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class AtcSeatAdoption:
    """Node binding to a selected ATC. Simulate uses the QMB token."""

    config_class: str
    composition_fp: Fingerprint
    policy_pair_hash: Fingerprint
    verdict: str
    simulate_token: Fingerprint | None
    venue_importer: str
    issues_venue_token: bool

    def fp1_identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "config_class": self.config_class,
            "composition_fp": self.composition_fp.value,
            "issues_venue_token": self.issues_venue_token,
            "policy_pair_hash": self.policy_pair_hash.value,
            "venue_importer": self.venue_importer,
            "verdict": self.verdict,
        }
        if self.simulate_token is not None:
            body["simulate_token"] = self.simulate_token.value
        return body


def adopt_atc_seat(
    selected: object,
    *,
    requested_role: object,
    remaining: object = None,
) -> Result[AtcSeatAdoption]:
    """Adopt ATC at the node. Live without paper+L17 is ``not_promoted``."""
    role = clean_token(requested_role)
    if role is None or role not in {"simulate", "paper", "live"}:
        return invalid(
            "requested_role",
            "ATC seat roles are simulate, paper, or live",
            given=repr(requested_role),
        )
    leftover: object = remaining if remaining is not None else _EMPTY_REMAINING
    if not isinstance(leftover, Mapping):
        return invalid(
            "remaining",
            "remaining consumer keys are a mapping",
            given=repr(type(leftover).__name__),
        )
    leftover_map = cast("Mapping[str, object]", leftover)
    present = sorted(name for name in leftover_map if name in BOOK_KEYS)
    if present:
        return invalid(
            present[0],
            "when ATC is selected the node does not stay secretly Book-shaped",
            extra=present,
        )
    sensing = refuse_sensing_as_atc(leftover_map)
    if is_refusal(sensing):
        return sensing
    config: AlternativeRunConfig
    simulate_token: Fingerprint | None = None
    if isinstance(selected, AtcSimulateReceipt):
        config = selected.config
        simulate_token = selected.simulate_token
    elif isinstance(selected, AlternativeRunConfig):
        config = selected
    else:
        parsed = validate_alternative_run_config(selected)
        if is_refusal(parsed):
            return parsed
        config = parsed.value
    adopted = adopt_selected_composition(
        config,
        consumer=CONSUMER_QMN,
        remaining=leftover_map,
    )
    if is_refusal(adopted):
        return adopted
    if adopted.value.config_class != ALTERNATIVE_CONFIG_CLASS:
        return invalid(
            "config_class",
            "an ATC seat adopts AlternativeRunConfig, not a Book-shaped remainder",
        )
    if role == "simulate":
        if config.command.adapter_capability != ADAPTER_INTERNAL_SIMULATE:
            return invalid(
                "adapter_capability",
                "ATC simulate stays on the QMB internal token; QMN does not import venue here",
            )
        if simulate_token is None:
            return invalid(
                "simulate_token",
                "QMB issues internal ATC-simulate tokens; the node does not mint them",
            )
        if config.admission.verdict != VERDICT_ADMITTED_SIMULATE:
            return invalid(
                "admission",
                "simulate requires host verdict admitted_simulate",
                verdict=config.admission.verdict,
            )
        return Ok(
            AtcSeatAdoption(
                config_class=ALTERNATIVE_CONFIG_CLASS,
                composition_fp=config.composition_fp,
                policy_pair_hash=config.policy_pair.policy_pair_hash,
                verdict=VERDICT_ADMITTED_SIMULATE,
                simulate_token=simulate_token,
                venue_importer=VENUE_IMPORTER,
                issues_venue_token=ATC_SEAT_ISSUES_VENUE_TOKEN,
            )
        )
    if role == "live" and config.admission.verdict != VERDICT_ADMITTED_LIVE:
        return Ok(
            AtcSeatAdoption(
                config_class=ALTERNATIVE_CONFIG_CLASS,
                composition_fp=config.composition_fp,
                policy_pair_hash=config.policy_pair.policy_pair_hash,
                verdict=VERDICT_NOT_PROMOTED,
                simulate_token=None,
                venue_importer=VENUE_IMPORTER,
                issues_venue_token=ATC_SEAT_ISSUES_VENUE_TOKEN,
            )
        )
    if role == "paper" and config.admission.verdict not in {
        VERDICT_ADMITTED_PAPER,
        VERDICT_ADMITTED_LIVE,
    }:
        return Ok(
            AtcSeatAdoption(
                config_class=ALTERNATIVE_CONFIG_CLASS,
                composition_fp=config.composition_fp,
                policy_pair_hash=config.policy_pair.policy_pair_hash,
                verdict=VERDICT_NOT_PROMOTED,
                simulate_token=None,
                venue_importer=VENUE_IMPORTER,
                issues_venue_token=ATC_SEAT_ISSUES_VENUE_TOKEN,
            )
        )
    return Ok(
        AtcSeatAdoption(
            config_class=ALTERNATIVE_CONFIG_CLASS,
            composition_fp=config.composition_fp,
            policy_pair_hash=config.policy_pair.policy_pair_hash,
            verdict=config.admission.verdict,
            simulate_token=None,
            venue_importer=VENUE_IMPORTER,
            issues_venue_token=ATC_SEAT_ISSUES_VENUE_TOKEN,
        )
    )
