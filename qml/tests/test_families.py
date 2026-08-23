"""Story 11.2 — strategy-family CT-06 metadata records (QL-6)."""

from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.registry import FieldSetKind, KindRegistry, Registrar, RegistrationRecord
from qml.families import (
    FAMILY_ID_FIELD,
    FAMILY_KEYED_SURFACES,
    FORBIDDEN_AUTHORITY_FIELDS,
    KIND_STRATEGY_FAMILY,
    STRATEGY_FAMILY_KIND_FORMAT_VERSION,
    FamilyKeyedSurface,
    StrategyFamilyId,
    StrategyFamilyRecord,
    install_strategy_family_kind,
    mint_strategy_family,
    register_strategy_family,
    resolve_family_at_layer1,
    strategy_family_kind_contract,
    validate_family_body,
)

import qml

_REPO = Path(__file__).resolve().parents[2]
_CREATED_NS = 1_700_000_000_000_000_000

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _writer(machine: str = "node-a") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", KIND_STRATEGY_FAMILY, "boot-1"))


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _registrar() -> Registrar:
    registry = KindRegistry()
    assert is_ok(install_strategy_family_kind(registry))
    return Registrar(registry)


# --- AC: opaque id + dated CT-06 record, no new CT number -------------------


def test_kind_is_ct06_addable_strategy_family_not_a_new_ct() -> None:
    assert KIND_STRATEGY_FAMILY == "strategy-family"
    assert STRATEGY_FAMILY_KIND_FORMAT_VERSION == 1
    contract = _ok(strategy_family_kind_contract())
    assert isinstance(contract, FieldSetKind)
    assert contract.name == KIND_STRATEGY_FAMILY
    assert contract.contract_format_version == STRATEGY_FAMILY_KIND_FORMAT_VERSION
    assert contract.required_fields == frozenset({FAMILY_ID_FIELD})
    assert contract.optional_fields == frozenset()
    ct06 = (_REPO / "docs" / "contracts" / "ct-06-registration.yaml").read_text(encoding="utf-8")
    assert "strategy-family" in ct06
    assert "bot_domain_kinds: [bot-definition, confluence, strategy-family]" in ct06


def test_mint_returns_fingerprintable_content_never_a_stamped_record() -> None:
    made = mint_strategy_family("trend-follow")
    assert is_ok(made)
    record = made.value
    assert isinstance(record, StrategyFamilyRecord)
    assert not isinstance(record, RegistrationRecord)
    assert record.family_id.value == "trend-follow"
    payload = record.identity_payload()
    assert payload == {
        "kind": KIND_STRATEGY_FAMILY,
        "contract_format_version": 1,
        "body": {"family_id": "trend-follow"},
    }
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "created_at" not in payload
    assert qml.__version__ not in payload.values()
    fp = _ok(record.fingerprint_content())
    via_core = _ok(fingerprint(payload))
    assert fp.value == via_core.value
    assert fp.value.startswith("fp1:sha256:")


def test_host_stamped_records_deduplicate_across_sandboxes() -> None:
    registrar = _registrar()
    a = _ok(
        register_strategy_family(
            "trend-follow",
            registrar=registrar,
            writer=_writer("node-a"),
            sequence=0,
            created_at=_instant(_CREATED_NS),
        )
    )
    b = _ok(
        register_strategy_family(
            "trend-follow",
            registrar=registrar,
            writer=_writer("node-b"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 1_000),
        )
    )
    assert a.record.kind == KIND_STRATEGY_FAMILY
    assert a.record.body[FAMILY_ID_FIELD] == "trend-follow"
    assert a.record.stable_id == b.record.stable_id
    assert a.outcome.value == "stored"
    assert b.outcome.value == "idempotent"
    # Idempotent re-write returns the first stored occurrence facts (DEC-0108).
    assert b.record.writer == a.record.writer
    body = {"family_id": "trend-follow"}
    sandbox_a = _ok(
        RegistrationRecord.try_create(
            KIND_STRATEGY_FAMILY, 1, [], body, _writer("node-a"), 0, _instant(_CREATED_NS)
        )
    )
    sandbox_b = _ok(
        RegistrationRecord.try_create(
            KIND_STRATEGY_FAMILY,
            1,
            [],
            body,
            _writer("node-b"),
            99,
            _instant(_CREATED_NS + 1_000),
        )
    )
    assert sandbox_a.writer != sandbox_b.writer
    assert sandbox_a.created_at != sandbox_b.created_at
    assert sandbox_a.stable_id == sandbox_b.stable_id


def test_register_refuses_when_kind_is_not_installed() -> None:
    bare = register_strategy_family(
        "trend-follow",
        registrar=Registrar(KindRegistry()),
        writer=_writer(),
        sequence=0,
        created_at=_instant(),
    )
    assert is_refusal(bare)
    assert bare.category is RefusalCategory.INVALID_INPUT
    not_a_registrar = register_strategy_family(
        "trend-follow",
        registrar="nope",
        writer=_writer(),
        sequence=0,
        created_at=_instant(),
    )
    assert is_refusal(not_a_registrar)


def test_different_family_ids_derive_different_fingerprints() -> None:
    a = _ok(mint_strategy_family("trend-follow"))
    b = _ok(mint_strategy_family("scalper"))
    assert _ok(a.fingerprint_content()) != _ok(b.fingerprint_content())


# --- AC: no constraint powers; constraining is the Book's job ----------------


def test_minted_record_carries_no_constraint_powers() -> None:
    record = _ok(mint_strategy_family("scalper"))
    assert dict(record.constraint_powers()) == {}
    assert set(record.body()) == {FAMILY_ID_FIELD}
    for field in FORBIDDEN_AUTHORITY_FIELDS:
        assert field not in record.body()
        assert not hasattr(record, field)
    assert (
        frozenset(
            {
                "permitted_timeframes",
                "permitted_feature_families",
                "mutation_allowances",
            }
        )
        == FORBIDDEN_AUTHORITY_FIELDS
    )


def test_authority_fields_are_policy_rejection() -> None:
    stuffed = validate_family_body(
        {
            "family_id": "scalper",
            "permitted_timeframes": ["M1", "M5"],
            "mutation_allowances": ["wf2"],
        }
    )
    assert is_refusal(stuffed)
    assert stuffed.category is RefusalCategory.POLICY_REJECTION
    assert stuffed.context["forbidden"] == ("mutation_allowances", "permitted_timeframes")
    unknown = validate_family_body({"family_id": "scalper", "leverage": "50"})
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.INVALID_INPUT
    not_a_map = validate_family_body(["nope"])
    assert is_refusal(not_a_map)
    blank_id = validate_family_body({"family_id": "  "})
    assert is_refusal(blank_id)


# --- AC: keys ExitLogicRef, paper starting balance, bench threshold ----------


def test_family_id_keys_ratified_law_surfaces_and_decides_nothing() -> None:
    record = _ok(mint_strategy_family("trend-follow"))
    keyed = record.keyed_surfaces()
    assert keyed == {
        FamilyKeyedSurface.EXIT_POLICY_EXIT_LOGIC_REF: "trend-follow",
        FamilyKeyedSurface.PAPER_STARTING_BALANCE: "trend-follow",
        FamilyKeyedSurface.BENCH_CONSECUTIVE_LOSS_THRESHOLD: "trend-follow",
    }
    assert frozenset(keyed) == FAMILY_KEYED_SURFACES
    assert record.constraint_powers() == {}


# --- AC: unresolvable family id at Layer 1 is unavailable dependency ---------


def test_layer1_resolves_present_family_and_refuses_a_miss() -> None:
    present = _ok(mint_strategy_family("trend-follow"))
    found = resolve_family_at_layer1("trend-follow", [present])
    assert is_ok(found)
    assert found.value.family_id.value == "trend-follow"
    missing = resolve_family_at_layer1("unknown-family", [present])
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert missing.context["journal"] is True
    assert missing.context["family_id"] == "unknown-family"
    empty = resolve_family_at_layer1("trend-follow", ())
    assert is_refusal(empty)
    assert empty.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_layer1_never_silently_passes_a_blank_or_non_catalog() -> None:
    blank = resolve_family_at_layer1("  ", ())
    assert is_refusal(blank)
    assert blank.category is RefusalCategory.INVALID_INPUT
    bad_catalog = resolve_family_at_layer1("trend-follow", "not-a-catalog")
    assert is_refusal(bad_catalog)
    assert bad_catalog.category is RefusalCategory.INVALID_INPUT


def test_layer1_resolves_host_stamped_registration_records() -> None:
    registrar = _registrar()
    receipt = _ok(
        register_strategy_family(
            "trend-follow",
            registrar=registrar,
            writer=_writer(),
            sequence=0,
            created_at=_instant(),
        )
    )
    found = resolve_family_at_layer1("trend-follow", [receipt.record])
    assert is_ok(found)
    assert found.value.family_id.value == "trend-follow"
    other_kind = _ok(
        RegistrationRecord.try_create(
            "instrument-class",
            1,
            [],
            {"target_fp1": "EURUSD", "asset_class": "fx-major"},
            _writer(),
            0,
            _instant(),
        )
    )
    skipped = resolve_family_at_layer1("trend-follow", [other_kind])
    assert is_refusal(skipped)
    assert skipped.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_layer1_accepts_mapping_catalog_and_body_mappings() -> None:
    content = _ok(mint_strategy_family("scalper"))
    by_name = resolve_family_at_layer1("scalper", {"scalper": content})
    assert is_ok(by_name)
    from_body = resolve_family_at_layer1("scalper", [{"family_id": "scalper"}])
    assert is_ok(from_body)
    from_payload = resolve_family_at_layer1(
        "scalper",
        [{"kind": KIND_STRATEGY_FAMILY, "body": {"family_id": "scalper"}}],
    )
    assert is_ok(from_payload)


def test_layer1_refuses_a_matching_record_that_carries_authority() -> None:
    stuffed = resolve_family_at_layer1(
        "scalper",
        [{"family_id": "scalper", "permitted_timeframes": ["H1"]}],
    )
    assert is_refusal(stuffed)
    assert stuffed.category is RefusalCategory.POLICY_REJECTION


def test_install_kind_refuses_a_non_registry_and_a_redefinition() -> None:
    assert is_refusal(install_strategy_family_kind("nope"))
    registry = KindRegistry()
    assert is_ok(install_strategy_family_kind(registry))
    again = install_strategy_family_kind(registry)
    assert is_refusal(again)


def test_strategy_family_id_rejects_blank_and_keeps_verbatim() -> None:
    made = StrategyFamilyId.try_create(" trend-follow")
    assert is_ok(made)
    assert made.value.value == " trend-follow"
    assert is_refusal(StrategyFamilyId.try_create(""))
    assert is_refusal(StrategyFamilyId.try_create(1))
    assert is_refusal(mint_strategy_family(""))
    assert is_refusal(StrategyFamilyRecord.try_create(None))
    assert is_refusal(StrategyFamilyRecord.try_from_body({"family_id": "  "}))
    assert is_ok(StrategyFamilyRecord.try_from_body({"family_id": "scalper"}))
    registrar = _registrar()
    assert is_refusal(
        register_strategy_family(
            "",
            registrar=registrar,
            writer=_writer(),
            sequence=0,
            created_at=_instant(),
        )
    )


def test_layer1_skips_non_family_catalog_items() -> None:
    present = _ok(mint_strategy_family("trend-follow"))
    catalog: list[object] = [
        object(),
        {"kind": "confluence", "body": {"family_id": "trend-follow"}},
        {"kind": KIND_STRATEGY_FAMILY, "body": "not-a-map"},
        {"body": {"family_id": 1}},
        present,
    ]
    found = resolve_family_at_layer1("trend-follow", catalog)
    assert is_ok(found)
    assert found.value.family_id.value == "trend-follow"


# --- AC: qml adds no qml_* configurable row and no version pin --------------


def test_qml_adds_no_registry_configurable_row_or_version_pin() -> None:
    text = (_REPO / "docs" / "registry" / "variables.yaml").read_text(encoding="utf-8")
    assert "name: qml_" not in text
    assert "component: COMP-QML" not in text
    pyproject = (_REPO / "qml" / "pyproject.toml").read_text(encoding="utf-8")
    assert "qmf-core" in pyproject
    assert "qmf-registry" in pyproject
    assert "qmf-risk" in pyproject
    assert "qml_" not in pyproject
