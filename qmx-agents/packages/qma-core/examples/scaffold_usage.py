"""L27 reference usage for qma-core ports, content identity, and refusals."""

from __future__ import annotations

import qma.core
from qma.core import content_address, tree_digest
from qma.core.barriers import parse_declaration, validate_network_posture
from qma.core.foundation import Money, fingerprint, is_ok, is_refusal
from qma.core.ontology import (
    ONTOLOGY_CHAIN,
    ActorId,
    DeskSlug,
    RoleName,
    SlugIndex,
    create_quant,
)
from qma.core.plugins import (
    HandleKind,
    HookSource,
    build_hook_event,
    build_hook_result,
    parse_credential_ref,
    parse_plugin_manifest,
)
from qma.core.ports import (
    PORT_CONTRACTS,
    require_singleton_scope_key,
    validate_contribution_point,
)
from qma.core.refusals import NoMemoryProvider, ProhibitedReachability, StoreVersionMismatch
from qma.core.vocabulary import (
    HOOK_VERBS,
    HookResultDecision,
    PrincipalClass,
    validate_governed_act,
)


def main() -> None:
    assert qma.core.__version__ == "0.1.0"
    assert len(HOOK_VERBS) == 23
    assert len(PORT_CONTRACTS) == 7
    assert ONTOLOGY_CHAIN == ("Desk", "Role", "Quant", "Agent", "Subagent")
    actor = ActorId.mint(DeskSlug.RESEARCH, "demo")
    assert is_ok(actor)
    quant = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="demo",
        role=RoleName.RESEARCHER,
        name="Demo",
        principal=PrincipalClass.OPERATOR,
        index=SlugIndex(active_desk_slugs=frozenset({"research"})),
    )
    assert is_ok(quant)
    assert quant.value.desk is DeskSlug.RESEARCH
    assert require_singleton_scope_key("MemoryProvider", "desk") == "desk"
    assert validate_contribution_point("tool") == "tool"
    assert HandleKind.STRATEGY_HANDLE.value == "StrategyHandle"
    parse_credential_ref("cred://models/openai")
    build_hook_event("before_tool", source=HookSource.PLUGIN)
    build_hook_result(HookResultDecision.DENY, reason="blocked")
    parse_plugin_manifest(
        {
            "id": "research-corpus",
            "version": "0.1.0",
            "qma_api": ">=0.1.0,<1.0.0",
            "desk": "research",
            "entrypoint": "research_corpus.activate",
            "contributions": [{"point": "skill", "local_id": "summarize"}],
        }
    )
    validate_governed_act("admit", "memory_candidate")

    money = Money.try_create(150, "USD", 2)
    assert is_ok(money)
    addressed = content_address(money.value.fp1_identity())
    assert is_ok(addressed)
    file_fp = fingerprint({"path": "readme.md", "bytes": "hello"})
    assert is_ok(file_fp)
    digest = tree_digest({"readme.md": file_fp.value})
    assert is_ok(digest)

    isolated = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local",
    )
    assert is_ok(isolated)
    venue = validate_network_posture("allowlist", ("demo.ctraderapi.com",))
    assert is_refusal(venue)
    assert ProhibitedReachability.matches(venue)

    refused = NoMemoryProvider.of(desk="research")
    assert is_refusal(refused)
    mismatch = StoreVersionMismatch.of(
        store="journal",
        expected_schema_version=1,
        store_schema_version=2,
    )
    assert is_refusal(mismatch)
    print(f"qma.core {qma.core.__version__} (definitions only)")


if __name__ == "__main__":
    main()
