"""L27 reference usage stub for the qma-core structural seed."""

from __future__ import annotations

import qma.core
from qma.core.vocabulary import HOOK_VERBS, HookResultDecision, validate_governed_act


def main() -> None:
    assert qma.core.__version__ == "0.1.0"
    assert len(HOOK_VERBS) == 23
    assert HookResultDecision.DENY.value == "deny"
    validate_governed_act("admit", "memory_candidate")
    print(f"qma.core {qma.core.__version__} (definitions only)")


if __name__ == "__main__":
    main()
