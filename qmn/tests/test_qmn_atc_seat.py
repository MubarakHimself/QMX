"""Story 58.2 — QMN adopts ATC simulate; live without paper+L17 is not_promoted."""

from __future__ import annotations

from typing import TypeVar

from qmb.config.alternative import (
    ADAPTER_INTERNAL_SIMULATE,
    ALTERNATIVE_CONFIG_CLASS,
    ATC_EVIDENCE_OWNER,
    VENUE_IMPORTER,
    VERDICT_ADMITTED_SIMULATE,
    VERDICT_NOT_PROMOTED,
    simulate_alternative_run,
    validate_alternative_run_config,
)
from qmf.core.chrono import WriterId
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmn.seats import (
    ATC_SEAT_ISSUES_VENUE_TOKEN,
    ATC_SIMULATE_TOKEN_ISSUER,
    adopt_atc_seat,
)

T = TypeVar("T")

_DECISION_NS = 1_726_747_200_000_000_000
_OBSERVED_NS = 1_726_747_170_000_000_000
_MAX_AGE_NS = 30_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _assert_invalid(result: Result[T], *, field: str | None = None) -> None:
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    if field is not None:
        assert result.context["field"] == field


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "admission": {
            "checked_grant_ids": ["grant:atc-sim"],
            "decided_at_ns": _DECISION_NS,
            "evaluator_principal": "host",
            "health_evidence_ref": "health:atc",
            "health_revision": 4,
            "observation_freshness": {
                "max_age_ns": _MAX_AGE_NS,
                "observed_at_ns": _OBSERVED_NS,
            },
        },
        "command": {
            "account_id": "acct:replay",
            "adapter_capability": ADAPTER_INTERNAL_SIMULATE,
            "command_owner_epoch": 18,
            "instrument": "EURUSD",
            "role": "pm",
        },
        "config_class": ALTERNATIVE_CONFIG_CLASS,
        "policy_pair": {
            "accounting": {
                "cash_identity": "internal-cash",
                "currency": "USD",
                "fill_application": "fifo",
                "position_identity": "instrument+account",
                "residual_meaning": "open-qty",
                "valuation": "last-mark",
            },
            "risk": {
                "halt": "on-unknown-or-limit",
                "max_gross": "100000",
                "override_principal": "operator",
                "sizing": "fixed-fraction",
            },
        },
        "policy_pair_id": "pp:kelly-v1",
        "policy_pair_version": 1,
    }
    body.update(overrides)
    return body


def test_adopt_atc_simulate_uses_qmb_token_and_does_not_issue_venue_token() -> None:
    writer = _ok(WriterId.try_create("node-a", "authoring", "atc-sim", "boot-1"))
    receipt = _ok(simulate_alternative_run(_payload(), writer=writer))
    adopted = _ok(adopt_atc_seat(receipt, requested_role="simulate"))
    assert adopted.config_class == ALTERNATIVE_CONFIG_CLASS
    assert adopted.simulate_token == receipt.simulate_token
    assert adopted.verdict == VERDICT_ADMITTED_SIMULATE
    assert adopted.venue_importer == VENUE_IMPORTER
    assert adopted.issues_venue_token is False
    assert ATC_SEAT_ISSUES_VENUE_TOKEN is False
    assert ATC_SIMULATE_TOKEN_ISSUER == ATC_EVIDENCE_OWNER
    assert "book_fp1" not in adopted.fp1_identity()
    _assert_invalid(
        adopt_atc_seat(receipt, requested_role="simulate", remaining={"book_fp1": None}),
        field="book_fp1",
    )
    config_only = _ok(validate_alternative_run_config(_payload()))
    _assert_invalid(adopt_atc_seat(config_only, requested_role="simulate"), field="simulate_token")


def test_live_atc_without_paper_and_l17_is_not_promoted() -> None:
    live_payload = _payload()
    live_payload["command"] = {
        "account_id": "acct:replay",
        "adapter_capability": "venue-live",
        "command_owner_epoch": 18,
        "instrument": "EURUSD",
        "role": "pm",
        "venue_kind": "ctrader",
    }
    config = _ok(validate_alternative_run_config(live_payload))
    assert config.admission.verdict == VERDICT_NOT_PROMOTED
    adopted = _ok(adopt_atc_seat(config, requested_role="live"))
    assert adopted.verdict == VERDICT_NOT_PROMOTED
    assert adopted.simulate_token is None
    assert adopted.issues_venue_token is False
