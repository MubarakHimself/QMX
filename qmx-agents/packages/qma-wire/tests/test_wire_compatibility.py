"""Story 41.2 — wire compatibility law (FR-Q14)."""

from __future__ import annotations

from qma.wire import (
    COMPATIBILITY_AUTHORITY,
    DEPRECATION_MINORS_DEFAULT,
    DEPRECATION_MINORS_REGISTRY_KEY,
    FamilyFormatDeclaration,
    SchemaEvolutionProposal,
    assert_sole_compatibility_authority,
    evaluate_deprecation_removal,
    evaluate_schema_evolution,
    ignore_unknown_fields,
    ignore_unknown_types,
)
from qmf.core.refusal import Ok, is_ok, is_refusal


def test_sole_compatibility_authority_is_qma_wire() -> None:
    assert COMPATIBILITY_AUTHORITY == "qma-wire"
    assert is_ok(assert_sole_compatibility_authority("qma-wire"))
    foreign = assert_sole_compatibility_authority("qma-daemon")
    assert is_refusal(foreign)
    assert foreign.context["authority"] == "qma-wire"


def test_same_major_accepts_additive_fields_and_types_only() -> None:
    proposal = SchemaEvolutionProposal.of(
        base_protocol_version="1.0.0",
        proposed_protocol_version="1.1.0",
        base_fields=("v", "type", "id"),
        proposed_fields=("v", "type", "id", "hint"),
        base_types=("start_mission",),
        proposed_types=("start_mission", "new_optional_command"),
    )
    verdict = evaluate_schema_evolution(proposal)
    assert isinstance(verdict, Ok)
    assert verdict.value.kind == "additive"
    assert verdict.value.added_fields == frozenset({"hint"})
    assert verdict.value.added_types == frozenset({"new_optional_command"})
    assert verdict.value.authority == "qma-wire"


def test_same_major_rejects_field_or_type_removal() -> None:
    removed_field = SchemaEvolutionProposal.of(
        base_protocol_version="1.2.0",
        proposed_protocol_version="1.3.0",
        base_fields=("v", "type", "legacy"),
        proposed_fields=("v", "type"),
        base_types=("start_mission",),
        proposed_types=("start_mission",),
    )
    refused = evaluate_schema_evolution(removed_field)
    assert is_refusal(refused)
    assert "additive fields only" in str(refused.context["reason"])

    removed_type = SchemaEvolutionProposal.of(
        base_protocol_version="1.2.0",
        proposed_protocol_version="1.3.0",
        base_fields=("v",),
        proposed_fields=("v",),
        base_types=("start_mission", "legacy_command"),
        proposed_types=("start_mission",),
    )
    refused_type = evaluate_schema_evolution(removed_type)
    assert is_refusal(refused_type)
    assert "additive types only" in str(refused_type.context["reason"])


def test_foreign_package_cannot_declare_compatibility_policy() -> None:
    proposal = SchemaEvolutionProposal.of(
        base_protocol_version="1.0.0",
        proposed_protocol_version="1.0.1",
        base_fields=("v",),
        proposed_fields=("v",),
        base_types=("start_mission",),
        proposed_types=("start_mission",),
        declaring_package="qma-core",
    )
    refused = evaluate_schema_evolution(proposal)
    assert is_refusal(refused)
    assert refused.context["authority"] == "qma-wire"


def test_older_clients_ignore_unknown_fields_and_types() -> None:
    payload = {"v": "1.1.0", "type": "start_mission", "hint": "new", "extra": 1}
    viewed = ignore_unknown_fields(payload, ("v", "type"))
    assert viewed == {"v": "1.1.0", "type": "start_mission"}
    assert ignore_unknown_types("start_mission", ("start_mission",)) == "start_mission"
    assert ignore_unknown_types("brand_new_event", ("start_mission",)) is None


def test_deprecation_requires_registry_minors_window() -> None:
    assert DEPRECATION_MINORS_REGISTRY_KEY == "wire.deprecation_minors"
    assert DEPRECATION_MINORS_DEFAULT == 2

    declaration = FamilyFormatDeclaration(
        family_name="legacy_command",
        protocol_version="1.0.0",
        format_version=1,
        deprecated_at_protocol_version="1.1.0",
    )
    assert declaration.leaves_old_evidence_readable() is True

    too_soon = evaluate_deprecation_removal(
        declaration,
        current_protocol_version="1.2.0",
        deprecation_minors=DEPRECATION_MINORS_DEFAULT,
    )
    # deprecated at 1.1, current 1.2 → elapsed 1 < 2
    assert is_refusal(too_soon)
    assert too_soon.context["elapsed_minors"] == 1
    assert too_soon.context["required_minors"] == 2
    assert too_soon.context["registry_key"] == DEPRECATION_MINORS_REGISTRY_KEY

    ready = evaluate_deprecation_removal(
        declaration,
        current_protocol_version="1.3.0",
        deprecation_minors=DEPRECATION_MINORS_DEFAULT,
    )
    assert isinstance(ready, Ok)
    assert ready.value.removed is True
    assert ready.value.protocol_version == "1.0.0"
    assert ready.value.format_version == 1


def test_undeclared_deprecation_cannot_be_removed() -> None:
    declaration = FamilyFormatDeclaration(
        family_name="still_live",
        protocol_version="1.0.0",
        format_version=1,
    )
    refused = evaluate_deprecation_removal(
        declaration,
        current_protocol_version="1.9.0",
    )
    assert is_refusal(refused)
