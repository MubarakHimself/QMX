"""Story 40.5 — Quant ontology and opaque actor identities (FR-Q06)."""

from __future__ import annotations

import pytest
from qma.core import ontology as ontology_api
from qma.core.ontology import (
    CREATION_ACTS,
    DESK_DISPLAY_NAMES,
    DESK_PREFIX_TOKENS,
    DESK_SLUG_VALUES,
    ONTOLOGY_CHAIN,
    ONTOLOGY_OBJECTS,
    PROFILE_FORBIDDEN_USES,
    ROLE_DISPLAY_NAMES,
    RUN_CONTAINER,
    WORK_VOCABULARY,
    ActorId,
    CreationAct,
    DeskSlug,
    OntologyError,
    Profile,
    RoleName,
    SlugIndex,
    Worker,
    assert_profile_presentation_only,
    assert_role_names_are_not_desk_names,
    authorize_creation,
    create_desk,
    create_quant,
    is_ontology_object,
    retire_desk,
    retire_quant,
)
from qma.core.plugins.manifest import DESK_PREFIX_TOKENS as MANIFEST_DESK_PREFIXES
from qma.core.refusals import OperatorPrincipalRequired, SlugUnavailable
from qma.core.vocabulary.enums import PrincipalClass
from qmf.core.refusal import is_ok, is_refusal


def test_ontology_chain_and_work_vocabulary() -> None:
    assert ONTOLOGY_CHAIN == ("Desk", "Role", "Quant", "Agent", "Subagent")
    assert frozenset(ONTOLOGY_CHAIN) == ONTOLOGY_OBJECTS
    assert RUN_CONTAINER == "Session"
    assert WORK_VOCABULARY == ("Goal", "Mission", "Task")
    assert is_ontology_object("Quant") is True
    assert is_ontology_object("Session") is False
    assert is_ontology_object("Worker") is False
    assert isinstance(Worker(address="worker://slot-1"), Worker)


def test_desk_slugs_exactly_five_and_shared_with_plugin_prefixes() -> None:
    assert frozenset(
        {"research", "trading", "dev", "analysis", "pm"}
    ) == DESK_SLUG_VALUES
    assert DESK_PREFIX_TOKENS == DESK_SLUG_VALUES
    assert MANIFEST_DESK_PREFIXES == DESK_PREFIX_TOKENS
    assert set(DeskSlug) == {
        DeskSlug.RESEARCH,
        DeskSlug.TRADING,
        DeskSlug.DEV,
        DeskSlug.ANALYSIS,
        DeskSlug.PM,
    }
    assert frozenset(
        {"Researcher", "Trader", "Developer", "Analyst", "Product Manager"}
    ) == ROLE_DISPLAY_NAMES
    assert set(DESK_DISPLAY_NAMES.values()) == {
        "Research",
        "Trading",
        "Development",
        "Analysis",
        "PM",
    }


def test_static_checks_reject_role_name_as_desk_name() -> None:
    assert_role_names_are_not_desk_names()
    assert frozenset(DESK_DISPLAY_NAMES.values()).isdisjoint(ROLE_DISPLAY_NAMES)


def test_actor_id_opaque_grammar_and_serialization() -> None:
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    actor = minted.value
    assert actor.serialize() == "quant:research/alpha"
    assert str(actor) == "quant:research/alpha"
    assert not hasattr(actor, "desk_slug")
    assert not hasattr(actor, "quant_slug")

    roundtrip = ActorId.try_create(actor.serialize())
    assert is_ok(roundtrip)
    assert roundtrip.value == actor

    bad = ActorId.try_create("quant:ops/alpha")
    assert is_refusal(bad)
    assert SlugUnavailable.matches(bad)

    bad_form = ActorId.mint("RESEARCH", "alpha")
    assert is_refusal(bad_form)


def test_desk_membership_comes_from_quant_record_not_actor_id() -> None:
    index = SlugIndex(active_desk_slugs=frozenset({"research"}))
    result = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="nova",
        role=RoleName.RESEARCHER,
        name="Nova",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_ok(result)
    quant = result.value
    assert quant.desk is DeskSlug.RESEARCH
    assert quant.actor_id.value == "quant:research/nova"
    assert not hasattr(quant.actor_id, "desk_slug")
    assert quant.desk.value == "research"


def test_creation_requires_named_act_and_operator_principal() -> None:
    assert frozenset({"desk.create", "quant.create"}) == CREATION_ACTS

    ok = authorize_creation(CreationAct.DESK_CREATE, PrincipalClass.OPERATOR)
    assert is_ok(ok)
    assert ok.value.act is CreationAct.DESK_CREATE

    machine = authorize_creation("quant.create", PrincipalClass.MACHINE)
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    assert machine.context["command"] == "quant.create"

    unknown = authorize_creation("desk.delete", PrincipalClass.OPERATOR)
    assert is_refusal(unknown)


def test_slug_unavailable_on_collisions() -> None:
    index = SlugIndex(
        active_desk_slugs=frozenset({"research"}),
        active_quant_slugs=frozenset({"alpha"}),
        retired_slugs=frozenset({"retired1"}),
    )

    role_hit = create_quant(
        desk_slug="research",
        quant_slug="trader",
        role=RoleName.RESEARCHER,
        name="X",
        principal="operator",
        index=index,
    )
    assert is_refusal(role_hit)
    assert SlugUnavailable.matches(role_hit)

    product = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="product-manager",
        role=RoleName.ANALYST,
        name="X",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_refusal(product)
    assert SlugUnavailable.matches(product)

    prefix = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="trading",
        role=RoleName.RESEARCHER,
        name="X",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_refusal(prefix)
    assert SlugUnavailable.matches(prefix)

    active = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="X",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_refusal(active)
    assert SlugUnavailable.matches(active)

    retired = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="retired1",
        role=RoleName.RESEARCHER,
        name="X",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_refusal(retired)
    assert SlugUnavailable.matches(retired)

    cased = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="Alpha",
        role=RoleName.RESEARCHER,
        name="X",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_refusal(cased)
    assert SlugUnavailable.matches(cased)


def test_create_desk_and_quant_happy_path() -> None:
    empty = SlugIndex()
    desk = create_desk(
        desk_slug="analysis",
        principal=PrincipalClass.OPERATOR,
        index=empty,
    )
    assert is_ok(desk)
    assert desk.value.slug is DeskSlug.ANALYSIS
    assert desk.value.display_name == "Analysis"

    index = SlugIndex(active_desk_slugs=frozenset({"analysis"}))
    quant = create_quant(
        desk_slug=DeskSlug.ANALYSIS,
        quant_slug="scout",
        role=RoleName.ANALYST,
        name="Scout",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_ok(quant)
    assert quant.value.actor_id.serialize() == "quant:analysis/scout"
    assert quant.value.desk is DeskSlug.ANALYSIS
    assert quant.value.quant_slug == "scout"


def test_retirement_keeps_actor_id_stable_and_reserves_slug() -> None:
    index = SlugIndex(active_desk_slugs=frozenset({"dev"}))
    created = create_quant(
        desk_slug=DeskSlug.DEV,
        quant_slug="builder",
        role=RoleName.DEVELOPER,
        name="Builder",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_ok(created)
    quant = created.value
    actor_before = quant.actor_id

    retired, tombstone = retire_quant(quant)
    assert retired.retired is True
    assert retired.actor_id == actor_before
    assert retired.actor_id.value == "quant:dev/builder"
    assert tombstone.slug == "builder"
    assert tombstone.slug_kind == "quant_slug"
    assert tombstone.actor_id == actor_before

    blocked = create_quant(
        desk_slug=DeskSlug.DEV,
        quant_slug="builder",
        role=RoleName.DEVELOPER,
        name="Builder2",
        principal=PrincipalClass.OPERATOR,
        index=SlugIndex.from_tombstones(
            active_desks=["dev"],
            tombstones=[tombstone],
        ),
    )
    assert is_refusal(blocked)
    assert SlugUnavailable.matches(blocked)

    desk = create_desk(
        desk_slug="pm",
        principal="operator",
        index=SlugIndex(),
    )
    assert is_ok(desk)
    retired_desk, desk_stone = retire_desk(desk.value)
    assert retired_desk.retired is True
    assert desk_stone.slug == "pm"
    reuse_desk = create_desk(
        desk_slug="pm",
        principal=PrincipalClass.OPERATOR,
        index=SlugIndex.from_tombstones(tombstones=[desk_stone]),
    )
    assert is_refusal(reuse_desk)
    assert SlugUnavailable.matches(reuse_desk)


def test_profile_is_presentation_only() -> None:
    profile = Profile(display_name="Labs", desk_slugs=(DeskSlug.RESEARCH, DeskSlug.DEV))
    assert profile.display_name == "Labs"
    assert frozenset(
        {
            "daemon_state",
            "identity_segment",
            "index",
            "filter",
            "permission_key",
            "routing_key",
        }
    ) == PROFILE_FORBIDDEN_USES
    for use in PROFILE_FORBIDDEN_USES:
        with pytest.raises(OntologyError, match="presentation-only"):
            assert_profile_presentation_only(use)
    assert_profile_presentation_only("client_display")


def test_package_export_surface() -> None:
    assert ontology_api.ActorId is ActorId
    assert ontology_api.ONTOLOGY_CHAIN == ONTOLOGY_CHAIN
    assert "Worker" in ontology_api.__all__
