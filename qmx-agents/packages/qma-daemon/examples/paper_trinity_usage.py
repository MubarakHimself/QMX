"""L27 reference usage: paper trinity, hub refs, notebooks, alias identity."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.paper import PAPER_NOUN_RESEARCH, QMA_PAPER_EXISTS, QMA_WRITES_HUB
from qma.core.vocabulary.enums import ExecutionEnvironmentKind
from qma.daemon.envs.runtime import RuntimeService
from qma.daemon.experiments import ExperimentSpecService
from qmf.core import is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.ANALYSIS, "notebook")
    assert is_ok(minted)
    _ = minted.value
    experiments = ExperimentSpecService()
    named = experiments.name_paper(world="replay", location="outside_node")
    assert is_ok(named)
    assert named.value == PAPER_NOUN_RESEARCH
    assert QMA_PAPER_EXISTS is False
    assert is_refusal(experiments.register_qma_paper())
    assert QMA_WRITES_HUB is False
    assert is_refusal(experiments.write_hub())
    assert is_refusal(experiments.hub_publish())
    assert is_ok(experiments.admit_hub_ref("qmb_ledger_ref"))
    assert is_refusal(experiments.promote())
    alias = experiments.resolve_alias(
        display="project",
        lane="coordinated",
        over="fp1:sha256:" + ("d" * 64),
    )
    assert is_ok(alias)
    assert is_refusal(experiments.mint_ui_tab())
    runtime = RuntimeService()
    notebook = runtime.admit_exploratory_notebook(imports=("qmb", "qml"))
    assert is_ok(notebook)
    env = runtime.admit_managed_interpreter(kind=ExecutionEnvironmentKind.DOCKER)
    assert is_ok(env)
    assert is_refusal(runtime.admit_managed_interpreter(kind="jupyter"))
    print("paper trinity ok")


if __name__ == "__main__":
    main()
