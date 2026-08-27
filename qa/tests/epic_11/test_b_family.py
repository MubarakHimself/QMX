"""Epic 11 / Story 11.2 — strategy-family metadata records (FR-047, QL-6, CT-06).

B1 dated CT-06 record; B2 no authority; B3 keys the ratified qmf-risk exit_policy
law; B4 unresolvable family -> unavailable dependency (R-009). Effects observed
through a real ``Registrar`` sink and the real qmf-risk ``ExitPolicy`` surface,
both owned by the test.
"""

from __future__ import annotations

import helpers as H

from qmf.registry import KindRegistry, Registrar
from qmf.risk.door import ExitLogicRef
from qmf.risk.exit_policy import ExitPolicy, ExitPolicyResolution, resolve_exit_policy_entry
from qml.families import (
    FORBIDDEN_AUTHORITY_FIELDS,
    KIND_STRATEGY_FAMILY,
    install_strategy_family_kind,
    mint_strategy_family,
    register_strategy_family,
    resolve_family_at_layer1,
    validate_family_body,
)


def _host_registrar() -> Registrar:
    registry = KindRegistry()
    H.unwrap(install_strategy_family_kind(registry), "install strategy-family kind")
    return Registrar(registry)


def test_b1_family_id_resolves_to_a_dated_ct06_record_body_is_only_family_id() -> None:
    """B1 (11.2 AC1): a minted family is a dated CT-06 record; body carries only family_id.

    Counter-case: a body carrying any field beyond family_id, or a kind other than
    the addable strategy-family kind, fails.
    """
    receipt = H.unwrap(
        register_strategy_family(
            "trend-follow",
            registrar=_host_registrar(),
            writer=H.writer("node-a", KIND_STRATEGY_FAMILY),
            sequence=0,
            created_at=H.instant(),
        ),
        "family record",
    )
    record = receipt.record
    assert record.kind == KIND_STRATEGY_FAMILY
    assert dict(record.body) == {"family_id": "trend-follow"}
    # A dated CT-06 record — the host stamped the occurrence facts.
    assert record.created_at == H.instant()
    assert record.stable_id.value.startswith("fp1:sha256:")


def test_b2_family_has_no_constraint_powers() -> None:
    """B2 (11.2 AC2): a family is a keying token with no authority.

    Counter-case: constraint_powers() non-empty, or validate_family_body admitting
    permitted_timeframes / feature-families / mutation-allowances, fails.
    """
    record = H.unwrap(mint_strategy_family("scalper"), "family")
    assert dict(record.constraint_powers()) == {}
    for authority_field in FORBIDDEN_AUTHORITY_FIELDS:
        assert authority_field not in record.body()
        assert not hasattr(record, authority_field)
    stuffed = validate_family_body(
        {
            "family_id": "scalper",
            "permitted_timeframes": ["M1"],
            "permitted_feature_families": ["ict"],
            "mutation_allowances": ["wf2"],
        }
    )
    assert H.category_of(stuffed) == "policy rejection"


def test_b3_family_id_keys_the_ratified_qmf_risk_exit_policy() -> None:
    """B3 (11.2 AC3): the family id resolves the per-family ExitLogicRef the Book's law reaches for.

    Observed through the REAL qmf-risk ExitPolicy surface (family_entries keyed by
    strategy-family id), not qml's own self-declared mapping. Counter-case: an
    unmatched family id resolving to a ref (it must refuse invalid input instead).
    """
    family = H.unwrap(mint_strategy_family("trend-follow"), "family")
    ref = H.unwrap(ExitLogicRef.try_create("adopt-bot-advisory-stop"), "exit logic ref")
    policy = H.unwrap(
        ExitPolicy.try_create({family.family_id.value: ref}, ("close_full",)),
        "exit policy",
    )
    resolved = H.unwrap(
        resolve_exit_policy_entry(policy, family.family_id.value), "resolved entry"
    )
    assert resolved.family_id == "trend-follow"
    assert resolved.entry == ref
    assert resolved.resolution is ExitPolicyResolution.EXPLICIT_FAMILY
    # The family itself decides nothing — no authority on the qml record.
    assert dict(family.constraint_powers()) == {}
    # Counter-case: a family the Book's policy does not name resolves to nothing.
    unmatched = resolve_exit_policy_entry(policy, "mean-revert")
    assert H.category_of(unmatched) == "invalid input"


def test_b4_unresolvable_family_is_unavailable_dependency_journaled() -> None:
    """B4 (11.2 AC4, R-009): a family id resolving to no record is unavailable dependency.

    Counter-case: a silent pass (Ok) on a missing family, or a different category,
    fails.
    """
    present = H.unwrap(mint_strategy_family("trend-follow"), "present")
    missing = resolve_family_at_layer1("unknown-family", [present])
    assert H.category_of(missing) == "unavailable dependency"
    assert missing.context.get("journal") is True
    empty = resolve_family_at_layer1("trend-follow", ())
    assert H.category_of(empty) == "unavailable dependency"
