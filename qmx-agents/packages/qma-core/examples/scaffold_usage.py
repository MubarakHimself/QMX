"""L27 reference usage for qma-core ports and plugin contribution surface."""

from __future__ import annotations

import qma.core
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
from qma.core.vocabulary import HOOK_VERBS, HookResultDecision, validate_governed_act


def main() -> None:
    assert qma.core.__version__ == "0.1.0"
    assert len(HOOK_VERBS) == 23
    assert len(PORT_CONTRACTS) == 7
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
    print(f"qma.core {qma.core.__version__} (definitions only)")


if __name__ == "__main__":
    main()
