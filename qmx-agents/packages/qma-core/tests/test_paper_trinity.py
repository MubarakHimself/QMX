"""Story 36.6 — paper trinity, hub, notebooks, and alias identity (qma-core)."""

from __future__ import annotations

from qma.core.ports.paper import (
    EPIC_PROMOTION_AUTHORITY,
    NODE_PAPER_OWNER,
    PAPER_NOUN_NODE,
    PAPER_NOUN_RESEARCH,
    QMA_PAPER_EXISTS,
    QMA_WRITES_HUB,
    QUANTCONNECT_PAPER_IS_QMX_LANE,
    RESEARCH_PAPER_OWNER,
    RESEARCH_PAPER_WORLD,
    UI_TAB_MINTS_RECORD,
    admit_exploratory_notebook,
    admit_hub_candidate_ref,
    admit_managed_interpreter,
    is_qma_paper_token,
    match_qma_paper_tool,
    mint_ui_tab_record,
    name_paper_noun,
    notebook_joins_undertaking,
    refuse_hub_publish_from_qma,
    refuse_qma_hub_write,
    refuse_qma_paper,
    refuse_qma_promotion,
    refuse_quantconnect_paper,
    refuse_sandbox_provenance,
    resolve_display_alias,
)
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qmf.core import is_ok, is_refusal
from qmf.core.refusal import RefusalCategory


def test_governed_replay_outside_node_is_research_paper() -> None:
    named = name_paper_noun(world=RESEARCH_PAPER_WORLD, location="outside_node")
    assert is_ok(named)
    assert named.value == PAPER_NOUN_RESEARCH
    assert RESEARCH_PAPER_OWNER == "COMP-QMB"
    assert QMA_PAPER_EXISTS is False


def test_qma_paper_and_quantconnect_are_refused() -> None:
    named = name_paper_noun(world="replay", noun="qma-paper")
    assert is_refusal(named)
    assert named.category is RefusalCategory.POLICY_REJECTION
    assert is_qma_paper_token("QMA-paper")
    qc = refuse_quantconnect_paper()
    assert qc.context["is_qmx_lane"] is QUANTCONNECT_PAPER_IS_QMX_LANE
    paper_only = refuse_qma_paper(tool_id="trading:paper_order", account_role="paper")
    assert paper_only.context["exists"] is False


def test_node_paper_stays_on_comp_qmn() -> None:
    named = name_paper_noun(world="live", location="node", role="demo")
    assert is_ok(named)
    assert named.value == PAPER_NOUN_NODE
    assert NODE_PAPER_OWNER == "COMP-QMN"
    collapsed = name_paper_noun(world="replay", location="node")
    assert is_refusal(collapsed)
    per_bot = name_paper_noun(world="live", location="node", role="per-bot-paper-lane")
    assert is_refusal(per_bot)


def test_qma_never_writes_hub_and_sandbox_refused_at_crossings() -> None:
    assert QMA_WRITES_HUB is False
    write = refuse_qma_hub_write()
    assert write.context["hub_publish_principal"] == "human"
    publish = refuse_hub_publish_from_qma()
    assert is_refusal(publish) or publish.category is RefusalCategory.POLICY_REJECTION
    sandbox = refuse_sandbox_provenance(provenance="sandbox", crossing="publish")
    assert is_refusal(sandbox)
    pull = refuse_sandbox_provenance(provenance="sandbox", crossing="pull")
    assert is_refusal(pull)
    live = refuse_sandbox_provenance(provenance="live", crossing="publish")
    assert is_ok(live)
    ref = admit_hub_candidate_ref("fp1:sha256:" + ("a" * 64))
    assert is_ok(ref)
    assert ref.value.writes_hub is False
    inbox = admit_hub_candidate_ref("hub_inbox")
    assert is_refusal(inbox)


def test_exploratory_notebook_imports_qmb_qml_on_controlled_room() -> None:
    admitted = admit_exploratory_notebook(imports=("qmb", "qml"))
    assert is_ok(admitted)
    assert admitted.value.imports == ("qmb", "qml")
    jupyter = admit_exploratory_notebook(imports=("qmb",), jupyter_product="jupyterlab")
    assert is_refusal(jupyter)
    module = admit_exploratory_notebook(imports=("qmb",), qmb_module=True)
    assert is_refusal(module)
    comp = admit_exploratory_notebook(imports=("qmb",), new_comp="COMP-NOTEBOOK")
    assert is_refusal(comp)


def test_managed_interpreter_is_execution_environment() -> None:
    env = admit_managed_interpreter(kind=ExecutionEnvironmentKind.DOCKER)
    assert is_ok(env)
    assert env.value.kind == "docker"
    assert env.value.qmb_module is False
    rlm = admit_managed_interpreter(kind="rlm_kernel")
    assert is_ok(rlm)
    qmb = admit_managed_interpreter(kind="docker", as_qmb_module=True)
    assert is_refusal(qmb)
    jupyter = admit_managed_interpreter(kind="jupyter")
    assert is_refusal(jupyter)
    identity = notebook_joins_undertaking(as_identity=True)
    assert is_refusal(identity)
    code = notebook_joins_undertaking(as_code_ref=True)
    assert is_ok(code)
    assert code.value == "code_ref"


def test_display_aliases_do_not_mint_records() -> None:
    coordinated = resolve_display_alias(
        display="project",
        lane="coordinated",
        over="fp1:sha256:" + ("b" * 64),
    )
    assert is_ok(coordinated)
    assert coordinated.value.mints_record is False
    governed = resolve_display_alias(display="workspace", lane="governed", over="fp1:bot")
    assert is_ok(governed)
    tab = mint_ui_tab_record(display="project")
    assert tab.context["mints_record"] is UI_TAB_MINTS_RECORD
    minted = resolve_display_alias(
        display="project",
        lane="coordinated",
        over="fp1:x",
        mint_record=True,
    )
    assert is_refusal(minted)


def test_epic_grants_no_promotion_authority() -> None:
    assert EPIC_PROMOTION_AUTHORITY is False
    refused = refuse_qma_promotion()
    assert refused.context["epic_authority"] is False
    matched = match_qma_paper_tool(
        tool_id="trading:qma-paper",
        tags=("qma_paper",),
        acts=("backtest",),
    )
    assert matched is not None
