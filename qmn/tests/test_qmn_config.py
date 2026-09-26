"""Story 25.2 — resolved node-config with all 71 value-status rows."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import yaml
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import is_ok, is_refusal
from qmf.core.secret import SecretRef, SecretValue
from qmn.config import (
    COMPILE_LAYERS,
    COMPONENT_COUNTS,
    EXPECTED_BLANK_EFFECT_COUNTS,
    EXPECTED_ROW_COUNT,
    HAS_INVOCATION_OVERRIDE_LAYER,
    LIVENESS_HEARTBEAT_NAMES,
    RETIRED_DEAD_MANS_SWITCH_NAMES,
    RUNTIME_FOLD_KEYS,
    VALUE_STATUS_REQUIRED_ROWS,
    blank_effect_coverage,
    compile_node_config,
    config_explain,
    config_init,
    config_validate,
    countersign_value_status,
    live_role_blocked_by,
    provisional_live_gates_like_blank,
    rows_by_name,
)

from qmn import config

_WORKSPACE = Path(__file__).resolve().parents[2]
_REGISTRY = _WORKSPACE / "docs" / "registry" / "variables.yaml"


def _fp(payload: object) -> Fingerprint:
    result = fingerprint(payload)
    assert is_ok(result)
    return result.value


def test_compile_layers_have_no_invocation_override() -> None:
    assert HAS_INVOCATION_OVERRIDE_LAYER is False
    assert config.compile_layers() == (
        "roster",
        "bms",
        "book",
        "node_defaults",
    )
    assert config.compile_layers() == COMPILE_LAYERS
    assert "invocation" not in COMPILE_LAYERS
    assert "invocation-flags" not in COMPILE_LAYERS


def test_catalog_matches_registry_file_and_ar80_counts() -> None:
    data = cast("Mapping[str, object]", yaml.safe_load(_REGISTRY.read_text(encoding="utf-8")))
    variables = cast("Sequence[Mapping[str, object]]", data["variables"])
    file_rows = [r for r in variables if r.get("value_status_required") is True]
    assert len(file_rows) == EXPECTED_ROW_COUNT == 71
    assert len(VALUE_STATUS_REQUIRED_ROWS) == 71

    by_comp = Counter(str(r["component"]) for r in file_rows)
    assert dict(by_comp) == COMPONENT_COUNTS
    assert COMPONENT_COUNTS == {"COMP-QMN": 48, "COMP-QMF-RISK": 20, "COMP-QMF-DATA": 3}

    blank: Counter[str] = Counter()
    for row in file_rows:
        effects = cast("Sequence[str]", row.get("blank_effect") or [])
        for effect in effects:
            blank[effect] += 1
    assert dict(blank) == EXPECTED_BLANK_EFFECT_COUNTS
    assert blank_effect_coverage() == EXPECTED_BLANK_EFFECT_COUNTS
    assert EXPECTED_BLANK_EFFECT_COUNTS == {
        "blocks-boot": 12,
        "blocks-role-live": 41,
        "blocks-soak": 60,
    }

    catalog = rows_by_name()
    for row in file_rows:
        name = str(row["name"])
        schema = catalog[name]
        assert schema["component"] == row["component"]
        assert schema["owner_scope"] == row["owner_scope"]
        assert schema["units"] == row.get("units")
        assert schema["type"] == row["type"]
        assert list(schema["blank_effect"]) == list(
            cast("Sequence[str]", row.get("blank_effect") or [])
        )
        assert schema["configurable"] is True
        assert row.get("configurable") is True


def test_liveness_heartbeat_names_from_dec_0261() -> None:
    names = {row["name"] for row in VALUE_STATUS_REQUIRED_ROWS}
    assert names >= LIVENESS_HEARTBEAT_NAMES
    assert names.isdisjoint(RETIRED_DEAD_MANS_SWITCH_NAMES)
    refused = compile_node_config(
        node_defaults={
            "dead_mans_switch_endpoint": {
                "value": "https://example.invalid",
                "value_status": "ratified",
            }
        }
    )
    assert is_refusal(refused)
    assert "liveness_heartbeat" in str(refused.context["reason"])


def test_config_init_all_blank_seventy_one_rows() -> None:
    result = config_init()
    assert is_ok(result)
    artifact = result.value
    assert len(artifact.rows) == 71
    assert all(row.value_status == "blank" for row in artifact.rows.values())
    assert all(row.value is None for row in artifact.rows.values())
    assert artifact.may_boot() is False
    assert artifact.may_bind_role_live() is False
    assert artifact.may_start_soak() is False
    assert len(artifact.boot_blocking_rows()) == 12
    # Live-blocking counts blank live-gating rows (41).
    assert len(artifact.live_blocking_rows()) == 41
    assert len(artifact.soak_blocking_rows()) == 60


def test_compile_precedence_roster_outranks_bms_book_defaults() -> None:
    result = compile_node_config(
        node_defaults={
            "news_blackout_before": {
                "value": 1,
                "value_status": "ratified",
            }
        },
        book={
            "news_blackout_before": {
                "value": 2,
                "value_status": "ratified",
            }
        },
        bms={
            "news_blackout_before": {
                "value": 3,
                "value_status": "ratified",
            }
        },
        roster={
            "news_blackout_before": {
                "value": 4,
                "value_status": "ratified",
            }
        },
    )
    assert is_ok(result)
    row = result.value.rows["news_blackout_before"]
    assert row.value == 4
    assert row.source_layer == "roster"
    assert row.value_status == "ratified"


def test_runtime_folds_and_unknown_keys_refused() -> None:
    for key in ("book_mode", "ksa_level", "standing_intents", "exposure"):
        assert key in RUNTIME_FOLD_KEYS
        refused = compile_node_config(book={key: {"value": "x", "value_status": "ratified"}})
        assert is_refusal(refused)
        assert "runtime folds" in str(refused.context["reason"])

    refused_unknown = compile_node_config(
        node_defaults={"not_a_registry_key": {"value": 1, "value_status": "ratified"}}
    )
    assert is_refusal(refused_unknown)


def test_does_not_invent_ksa_or_latency_numbers() -> None:
    """FTR-07: compiler leaves KSA/latency blank unless a layer supplies them."""
    result = config_init()
    assert is_ok(result)
    artifact = result.value
    for name in (
        "ksa_effect_matrix",
        "max_slice_latency",
        "submission_deadline",
        "local_queue_bound",
    ):
        row = artifact.rows[name]
        assert row.value_status == "blank"
        assert row.value is None


def test_provisional_live_gating_behaves_like_blank_until_countersign() -> None:
    evidence = _fp({"evidence": "news-blackout-corpus-a"})
    compiled = compile_node_config(
        book={
            "news_blackout_before": {
                "value": 15,
                "value_status": "provisional-evidence",
                "evidence_fp1": evidence.value,
            }
        }
    )
    assert is_ok(compiled)
    artifact = compiled.value
    row = artifact.rows["news_blackout_before"]
    assert row.value_status == "provisional-evidence"
    assert row.blocks_role_live is True
    assert "news_blackout_before" in live_role_blocked_by(artifact)
    assert provisional_live_gates_like_blank(artifact) is True
    assert artifact.may_bind_role_live() is False

    signed = countersign_value_status(
        artifact,
        variable="news_blackout_before",
        evidence_fp1=evidence,
    )
    assert is_ok(signed)
    next_cfg = signed.value
    assert next_cfg.config_version == artifact.config_version + 1
    assert next_cfg.branches_from == artifact.config_version
    flipped = next_cfg.rows["news_blackout_before"]
    assert flipped.value_status == "ratified"
    assert flipped.blocks_role_live is False
    assert flipped.value == 15


def test_countersign_refuses_missing_mismatched_or_multi_row() -> None:
    evidence = _fp({"evidence": "news-blackout-corpus-a"})
    other = _fp({"evidence": "news-blackout-corpus-b"})
    compiled = compile_node_config(
        book={
            "news_blackout_before": {
                "value": 15,
                "value_status": "provisional-evidence",
                "evidence_fp1": evidence.value,
            },
            "news_blackout_after": {
                "value": 15,
                "value_status": "provisional-evidence",
                "evidence_fp1": evidence.value,
            },
        }
    )
    assert is_ok(compiled)
    artifact = compiled.value

    mismatched = countersign_value_status(
        artifact,
        variable="news_blackout_before",
        evidence_fp1=other,
    )
    assert is_refusal(mismatched)

    multi = countersign_value_status(
        artifact,
        variable="news_blackout_before",
        evidence_fp1=evidence,
        extra_variables=("news_blackout_after",),
    )
    assert is_refusal(multi)
    assert "one variable" in str(multi.context["reason"])

    ratified_first = countersign_value_status(
        artifact,
        variable="news_blackout_before",
        evidence_fp1=evidence,
    )
    assert is_ok(ratified_first)
    again = countersign_value_status(
        ratified_first.value,
        variable="news_blackout_before",
        evidence_fp1=evidence.value,
    )
    assert is_refusal(again)


def test_secret_values_refused_and_refs_not_fingerprinted_as_secrets() -> None:
    ref = SecretRef.try_create("cred-ref-liveness-hb-001")
    assert is_ok(ref)
    secret = SecretValue.try_create(ref.value, "super-secret-token")
    assert is_ok(secret)

    refused = compile_node_config(
        node_defaults={
            "liveness_heartbeat_token_reference": {
                "value": secret.value,
                "value_status": "ratified",
            }
        }
    )
    assert is_refusal(refused)

    compiled = compile_node_config(
        node_defaults={
            "liveness_heartbeat_token_reference": {
                "value": ref.value.value,
                "value_status": "ratified",
            },
            "liveness_heartbeat_endpoint": {
                "value": "https://hc.example/ping/abc",
                "value_status": "ratified",
            },
            "liveness_heartbeat_cadence": {
                "value": "60s",
                "value_status": "ratified",
            },
        }
    )
    assert is_ok(compiled)
    identity = compiled.value.fp1_identity()
    identity_rows = cast("Sequence[Mapping[str, object]]", identity["rows"])
    token_entry = next(
        row for row in identity_rows if row["name"] == "liveness_heartbeat_token_reference"
    )
    assert "value" not in token_entry
    assert token_entry["secret_ref_present"] is True
    assert "super-secret-token" not in str(identity)

    explained = config_explain(compiled.value)
    assert is_ok(explained)
    payload = explained.value
    assert "super-secret-token" not in str(payload)
    explain_rows_payload = cast("Sequence[Mapping[str, object]]", payload["rows"])
    token_explain = next(
        row
        for row in explain_rows_payload
        if row["name"] == "liveness_heartbeat_token_reference"
    )
    assert token_explain["value"] == ref.value.value
    assert token_explain.get("secret_ref") is True


def test_config_validate_and_explain_deterministic() -> None:
    init = config_init(roster_identity={"machine_tuple": "vps-a"})
    assert is_ok(init)
    validated = config_validate(init.value)
    assert is_ok(validated)
    assert validated.value.fingerprint == init.value.fingerprint

    explained = config_explain(init.value)
    assert is_ok(explained)
    again = config_explain(init.value)
    assert is_ok(again)
    assert explained.value == again.value
    assert explained.value["row_count"] == 71
    assert explained.value["layer_precedence"] == list(COMPILE_LAYERS)
    assert explained.value["may_boot"] is False
    missing = cast("list[str]", explained.value["blank_rows"])
    assert len(missing) == 71
    # Sorted deterministic order.
    assert missing == sorted(missing)
    explain_rows_payload = cast("Sequence[Mapping[str, object]]", explained.value["rows"])
    row_names = [str(row["name"]) for row in explain_rows_payload]
    assert row_names == sorted(row_names)
    for row in explain_rows_payload:
        assert "owner_scope" in row
        assert "blank_effect" in row
        assert "value_status" in row
        assert "source_layer" in row
        assert "admission_impact" in row


def test_fingerprint_stable_and_changes_on_countersign() -> None:
    evidence = _fp({"evidence": "news-blackout-corpus-a"})
    first = compile_node_config(
        book={
            "qualifying_loss_threshold": {
                "value": "1",
                "value_status": "provisional-evidence",
                "evidence_fp1": evidence.value,
            }
        }
    )
    second = compile_node_config(
        book={
            "qualifying_loss_threshold": {
                "value": "1",
                "value_status": "provisional-evidence",
                "evidence_fp1": evidence.value,
            }
        }
    )
    assert is_ok(first) and is_ok(second)
    assert first.value.fingerprint == second.value.fingerprint
    assert isinstance(first.value.fingerprint, Fingerprint)

    signed = countersign_value_status(
        first.value,
        variable="qualifying_loss_threshold",
        evidence_fp1=evidence,
    )
    assert is_ok(signed)
    assert signed.value.fingerprint != first.value.fingerprint


def test_unit_kind_owner_scope_and_configurable_on_every_row() -> None:
    result = config_init()
    assert is_ok(result)
    for schema in VALUE_STATUS_REQUIRED_ROWS:
        row = result.value.rows[schema["name"]]
        assert row.owner_scope == schema["owner_scope"]
        assert row.unit_kind == schema["units"]
        assert row.configurable is True
        assert row.component == schema["component"]
        assert tuple(row.blank_effect) == tuple(schema["blank_effect"])
