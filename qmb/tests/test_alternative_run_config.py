"""Story 58.2 — ATC simulate with zero Book keys and a complete PolicyPair."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmb.config import (
    ACCOUNTING_POLICY_FIELDS,
    ADAPTER_INTERNAL_SIMULATE,
    ALTERNATIVE_CONFIG_CLASS,
    ATC_EVIDENCE_OWNER,
    BOOK_KEYS,
    COMPOSITION_CLASS_ALTERNATIVE,
    CONSUMER_MIS,
    CONSUMER_QMB,
    CONSUMER_QML,
    CONSUMER_QMN,
    E2E_ADOPTION_CLOSED,
    GAP_0098_ID,
    GAP_0098_STATUS,
    IDENTITY_FIELDS,
    INSPECT_SHA_ATC_ABSENT,
    P2_INT_001,
    POLICY_SHAPE_OWNER,
    RISK_POLICY_FIELDS,
    VENUE_IMPORTER,
    VERDICT_ADMITTED_SIMULATE,
    VERDICT_NOT_PROMOTED,
    ResolvedRunConfig,
    adopt_selected_composition,
    alternative_run_config_identity,
    hash_policy_pair,
    refuse_atc_implemented_at_inspect_sha,
    simulate_alternative_run,
    validate_alternative_run_config,
)
from qmb.config.compiler import compile_run_config
from qmf.core.chrono import WriterId
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import EdgeType

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


def _accounting() -> dict[str, object]:
    return {
        "cash_identity": "internal-cash",
        "currency": "USD",
        "fill_application": "fifo",
        "position_identity": "instrument+account",
        "residual_meaning": "open-qty",
        "valuation": "last-mark",
    }


def _risk() -> dict[str, object]:
    return {
        "halt": "on-unknown-or-limit",
        "max_gross": "100000",
        "override_principal": "operator",
        "sizing": "fixed-fraction",
    }


def _command(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "account_id": "acct:replay",
        "adapter_capability": ADAPTER_INTERNAL_SIMULATE,
        "command_owner_epoch": 18,
        "instrument": "EURUSD",
        "role": "pm",
    }
    body.update(overrides)
    return body


def _admission(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "checked_grant_ids": ["grant:atc-sim"],
        "decided_at_ns": _DECISION_NS,
        "evaluator_principal": "host",
        "health_evidence_ref": "health:atc",
        "health_revision": 4,
        "observation_freshness": {
            "max_age_ns": _MAX_AGE_NS,
            "observed_at_ns": _OBSERVED_NS,
        },
    }
    body.update(overrides)
    return body


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "admission": _admission(),
        "command": _command(),
        "config_class": ALTERNATIVE_CONFIG_CLASS,
        "policy_pair": {"accounting": _accounting(), "risk": _risk()},
        "policy_pair_id": "pp:kelly-v1",
        "policy_pair_version": 1,
    }
    body.update(overrides)
    return body


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "authoring", "atc-sim", "boot-1"))


def test_book_keys_are_absent_not_null() -> None:
    validated = _ok(validate_alternative_run_config(_payload()))
    envelope = validated.payload()
    command = cast("Mapping[str, object]", envelope["command"])
    admission = cast("Mapping[str, object]", envelope["admission"])
    pair = cast("Mapping[str, object]", envelope["policy_pair"])
    for key in BOOK_KEYS:
        assert key not in envelope
        assert key not in command
        assert key not in admission
        assert key not in pair
    identity = validated.fp1_identity()
    for key in BOOK_KEYS:
        assert key not in identity
    for key in BOOK_KEYS:
        refused = validate_alternative_run_config(_payload(**{key: None}))
        _assert_invalid(refused, field=key)


def test_complete_policy_pair_validates_and_hashes_accounting_plus_risk() -> None:
    hashed = _ok(hash_policy_pair(_accounting(), _risk()))
    validated = _ok(validate_alternative_run_config(_payload()))
    assert validated.config_class == ALTERNATIVE_CONFIG_CLASS
    assert validated.policy_pair.policy_pair_hash == hashed
    assert validated.policy_pair.identity()["policy_pair_hash"] == hashed.value
    assert "accounting" not in validated.fp1_identity()
    assert "risk" not in validated.fp1_identity()
    accounting = cast(
        "Mapping[str, object]",
        validated.policy_pair.inline_bodies()["accounting"],
    )
    assert accounting["currency"] == "USD"
    assert validated.command.command_owner_epoch == 18
    assert validated.admission.evaluator_principal == "host"
    assert validated.admission.verdict == VERDICT_ADMITTED_SIMULATE
    assert validated.composition_fp == validated.fingerprint
    schema = alternative_run_config_identity()
    assert schema["policy_shape_owner"] == POLICY_SHAPE_OWNER
    assert schema["atc_evidence_owner"] == ATC_EVIDENCE_OWNER
    assert schema["accounting_policy_fields"] == ACCOUNTING_POLICY_FIELDS
    assert schema["risk_policy_fields"] == RISK_POLICY_FIELDS
    assert schema["venue_importer"] == VENUE_IMPORTER
    assert schema["e2e_adoption_closed"] is False


def test_dummy_policy_pair_is_invalid_input() -> None:
    dummy_risk = {**_risk(), "sizing": "pass-through"}
    _assert_invalid(
        validate_alternative_run_config(
            _payload(policy_pair={"accounting": _accounting(), "risk": dummy_risk})
        ),
        field="sizing",
    )
    _assert_invalid(
        validate_alternative_run_config(_payload(policy_pair_id="NULL_POLICY_PAIR")),
        field="policy_pair_id",
    )
    _assert_invalid(
        validate_alternative_run_config(
            _payload(policy_pair={"accounting": {}, "risk": _risk()})
        ),
        field="accounting",
    )
    incomplete = dict(_accounting())
    del incomplete["valuation"]
    _assert_invalid(
        validate_alternative_run_config(
            _payload(policy_pair={"accounting": incomplete, "risk": _risk()})
        ),
        field="accounting",
    )


def test_simulate_writes_alternative_jsonl_and_ct07_to_policy_pair_hash() -> None:
    receipt = _ok(simulate_alternative_run(_payload(), writer=_writer()))
    line = _ok(receipt.jsonl_line())
    assert line.endswith(b"\n")
    identity = receipt.journal.fp1_identity()
    assert identity["composition_class"] == COMPOSITION_CLASS_ALTERNATIVE
    assert identity["owner"] == ATC_EVIDENCE_OWNER
    assert identity["policy_pair_hash"] == receipt.config.policy_pair.policy_pair_hash.value
    assert identity["simulate_token"] == receipt.simulate_token.value
    assert receipt.journal.lineage.edge_type is EdgeType.OCCURRENCE_OF
    assert receipt.journal.lineage.to_ref == receipt.config.policy_pair.policy_pair_hash
    assert receipt.simulate_token.value.startswith("fp1:sha256:")
    for key in BOOK_KEYS:
        assert key not in identity


def test_host_admission_rejects_client_booleans_and_stale_observations() -> None:
    _assert_invalid(
        validate_alternative_run_config(_payload(admission=_admission(authorized=True))),
        field="authorized",
    )
    _assert_invalid(
        validate_alternative_run_config(
            _payload(admission=_admission(evaluator_principal="client"))
        ),
        field="evaluator_principal",
    )
    stale_obs = validate_alternative_run_config(
        _payload(
            admission=_admission(
                observation_freshness={
                    "max_age_ns": 1,
                    "observed_at_ns": _OBSERVED_NS,
                }
            )
        )
    )
    assert is_refusal(stale_obs)
    assert stale_obs.category is RefusalCategory.STALE_EVIDENCE


def test_live_without_paper_and_l17_is_not_promoted() -> None:
    live = _ok(
        validate_alternative_run_config(
            _payload(command=_command(adapter_capability="venue-live", venue_kind="ctrader"))
        )
    )
    assert live.admission.verdict == VERDICT_NOT_PROMOTED
    simulate = simulate_alternative_run(
        _payload(command=_command(adapter_capability="venue-live", venue_kind="ctrader")),
        writer=_writer(),
    )
    _assert_invalid(simulate, field="adapter_capability")
    sneaked_venue = simulate_alternative_run(
        _payload(command=_command(venue_kind="ctrader")),
        writer=_writer(),
    )
    _assert_invalid(sneaked_venue, field="venue_kind")


def test_consumers_adopt_atc_and_refuse_secretly_book_shaped_remainder() -> None:
    config = _ok(validate_alternative_run_config(_payload()))
    for consumer in (CONSUMER_QML, CONSUMER_QMB, CONSUMER_MIS, CONSUMER_QMN):
        adopted = _ok(adopt_selected_composition(config, consumer=consumer))
        assert adopted.config_class == ALTERNATIVE_CONFIG_CLASS
        assert adopted.composition_fp == config.composition_fp
        assert adopted.policy_pair_hash == config.policy_pair.policy_pair_hash
        assert adopted.book_fp1 is None
        assert adopted.venue_importer == VENUE_IMPORTER
        assert "book_fp1" not in adopted.fp1_identity()
        remaining: dict[str, object] = {"book_fp1": "fp1:sha256:" + "ab" * 32}
        _assert_invalid(
            adopt_selected_composition(config, consumer=consumer, remaining=remaining)
        )
    _assert_invalid(
        adopt_selected_composition(
            {"class": "ungoverned-work-config", "label": "atc"},
            consumer=CONSUMER_QMB,
        ),
        field="label",
    )


def test_atc_cannot_sneak_through_resolved_run_config() -> None:
    for field in ("book_fp1", "bms_fp1", "bot_fp1", "book_fragment_fp1", "bms_fragment_fp1"):
        assert field in IDENTITY_FIELDS
    atc = _ok(validate_alternative_run_config(_payload()))
    _assert_invalid(ResolvedRunConfig.try_read(atc.payload()), field="class")
    _assert_invalid(ResolvedRunConfig.try_read(atc.fp1_identity()), field="class")
    # compile_run_config still requires Book fragments; policy_pair is invalid there.
    refused = compile_run_config(
        object(),
        book_fragment=None,
        bms_fragment=None,
        run_spec={"policy_pair": {"accounting": "identity"}},
    )
    assert is_refusal(refused)


def test_gap_0098_stays_open_and_270e992_claim_fails() -> None:
    assert GAP_0098_ID == "GAP-0098"
    assert GAP_0098_STATUS == "open"
    assert P2_INT_001 == "P2-INT-001"
    assert E2E_ADOPTION_CLOSED is False
    schema = alternative_run_config_identity()
    assert schema["gap_0098_status"] == "open"
    assert schema["e2e_adoption_closed"] is False
    _assert_invalid(refuse_atc_implemented_at_inspect_sha(INSPECT_SHA_ATC_ABSENT), field="sha")
    _assert_invalid(refuse_atc_implemented_at_inspect_sha("270e992"), field="sha")
    assert is_ok(refuse_atc_implemented_at_inspect_sha("deadbeef" * 5))


def test_supplied_hashes_must_match_derived_identity() -> None:
    hashed = _ok(hash_policy_pair(_accounting(), _risk()))
    validated = _ok(
        validate_alternative_run_config(_payload(policy_pair_hash=hashed.value))
    )
    assert validated.policy_pair.policy_pair_hash == hashed
    other = _ok(Fingerprint.try_create("fp1:sha256:" + "cd" * 32))
    _assert_invalid(
        validate_alternative_run_config(_payload(policy_pair_hash=other.value)),
        field="policy_pair_hash",
    )
    secrets = validate_alternative_run_config(
        _payload(
            policy_pair={
                "accounting": {**_accounting(), "secret": "s3cret"},
                "risk": _risk(),
            }
        )
    )
    _assert_invalid(secrets, field="secret")
    # inline bodies are a copy, never sole identity
    first = _ok(validate_alternative_run_config(_payload()))
    renamed = _payload()
    pair = cast("Mapping[str, object]", renamed["policy_pair"])
    accounting = dict(cast("Mapping[str, object]", pair["accounting"]))
    # identity stays the hash of fields, not a display rename of the id
    second = _ok(
        validate_alternative_run_config(
            {
                **renamed,
                "policy_pair": {"accounting": accounting, "risk": _risk()},
                "policy_pair_id": "pp:kelly-v1-display",
            }
        )
    )
    assert first.policy_pair.policy_pair_hash == second.policy_pair.policy_pair_hash
    assert first.composition_fp != second.composition_fp
