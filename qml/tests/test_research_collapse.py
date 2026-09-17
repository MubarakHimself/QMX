"""Story 51.2 — collapse open Stage 0 roles; refuse invented exits."""

from __future__ import annotations

from qmf.core.refusal import RefusalCategory, is_refusal
from qml.conformance import graduate_mill_to_governed
from qml.declaration import FORBIDDEN_BOT_FIELDS, LEG_ROLES
from qml.research import (
    CT34_LEG_ROLES,
    F_SLOTS,
    PYTHON_WHEN_REMAINDERS,
    STAGE0_CLASS_IS_CT33_FIELD,
    collapse_stage0_roles,
    collapse_unresolved_f,
    refuse_entry_hypothesis_as_ct33_field,
    refuse_invented_ct34_role,
    refuse_invented_exits,
)
from research_collapse_helpers import (
    layer_verdicts,
    mint_research_bot,
    ok,
    open_role_hypothesis,
    research_bot_world,
    unresolved_f_hypothesis,
)


def test_collapse_maps_open_roles_to_ct34_and_python_when() -> None:
    collapsed = ok(collapse_stage0_roles(open_role_hypothesis()))
    assert collapsed.ct34_roles == ("level", "trigger", "confirmation", "filter")
    assert "invalidation" in collapsed.python_when
    assert set(collapsed.ct34_roles) <= LEG_ROLES
    assert set(collapsed.ct34_roles) <= CT34_LEG_ROLES

    operators = ok(collapse_stage0_roles(["ALL", "sequence", "within", "arming"]))
    assert operators.ct34_roles == ()
    assert set(operators.python_when) <= PYTHON_WHEN_REMAINDERS | {"arming"}
    assert "all" in operators.python_when
    assert "sequence" in operators.python_when
    assert "within" in operators.python_when

    invented = refuse_invented_ct34_role("invalidation")
    assert is_refusal(invented)
    assert invented.context["gap_0085"] is False


def test_unresolved_f_yields_empty_permitted_exit_intents() -> None:
    collapsed = ok(collapse_unresolved_f(dict.fromkeys(F_SLOTS, "unresolved")))
    assert collapsed.permitted_exit_intents == ()
    assert collapsed.book_family_policy is True
    assert collapsed.invented_exits is False

    refused = collapse_unresolved_f(
        dict.fromkeys(F_SLOTS, "unresolved"),
        invent_exits=True,
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["permitted_exit_intents"] == ()

    direct = refuse_invented_exits(invent_close_reasons=True)
    assert is_refusal(direct)
    assert direct.context["invented_close_reasons"] is True


def test_entry_hypothesis_is_stage0_taxonomy_not_ct33_field() -> None:
    assert STAGE0_CLASS_IS_CT33_FIELD is False
    refused = refuse_entry_hypothesis_as_ct33_field("entry_hypothesis")
    assert is_refusal(refused)
    assert refused.context["is_ct33_field"] is False
    assert "entry_hypothesis" in FORBIDDEN_BOT_FIELDS
    assert "hypothesis_class" in FORBIDDEN_BOT_FIELDS

    world = research_bot_world()
    banned = mint_research_bot(world, extra={"entry_hypothesis": "asian-high"})
    assert is_refusal(banned)
    payload = ok(mint_research_bot(world)).identity_payload()
    body = payload["body"]
    assert "entry_hypothesis" not in payload
    assert isinstance(body, dict)
    assert "entry_hypothesis" not in body
    assert "hypothesis_class" not in body


def test_mill_graduation_refuses_invented_exits_flag() -> None:
    world = research_bot_world()
    declaration = ok(mint_research_bot(world))
    layer1, layer2 = layer_verdicts(world, declaration)
    refused = graduate_mill_to_governed(
        layer1=layer1,
        layer2=layer2,
        hypothesis=unresolved_f_hypothesis(),
        invent_exits=True,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "permitted_exit_intents"
