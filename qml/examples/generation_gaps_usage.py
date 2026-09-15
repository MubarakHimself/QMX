"""Reference usage — GAP-0085 nouns and GAP-0063 stay unfilled (Story 38.3).

Executable::

    python qml/examples/generation_gaps_usage.py

Shows the things Story 38.3 pins down:

1. Typed Entry/Exit/Filter/Session vocabulary is not minted.
2. Write-ownership remains QML/host for a later increment.
3. A first algorithm requested as a decided default is refused as unruled.
4. Generation trails connect-wave (Epics 32-37) and does not block Library,
   What-if, or the door.
5. No-code authoring is refused; rung 2 ordinary Python remains the logic path.
"""

from __future__ import annotations

from qmf.core.refusal import is_refusal
from qml.generation import (
    DEFAULT_GENERATOR_ALGORITHM,
    DOES_NOT_BLOCK_SURFACES,
    GAP_0085_WRITE_OWNER,
    GENERATION_EPIC,
    MECHANISM_VOCABULARY_MINTED,
    admit_decided_generator_algorithm,
    blocks_library_whatif_or_door,
    mint_mechanism_vocabulary,
    refuse_no_code_authoring,
    trails_connect_wave,
    write_ownership_is_qml_host,
)

import qml


def main() -> None:
    print(f"qml {qml.__version__}")
    assert MECHANISM_VOCABULARY_MINTED is False
    assert write_ownership_is_qml_host() is True
    assert GAP_0085_WRITE_OWNER == "qml-host"
    minted = mint_mechanism_vocabulary({"EntryMechanism": {"kind": "breakout"}})
    assert is_refusal(minted)
    print("gap-0085 nouns not minted; write-ownership qml/host later increment")

    assert DEFAULT_GENERATOR_ALGORITHM is None
    decided = admit_decided_generator_algorithm("placeholder-fill")
    assert is_refusal(decided)
    print("gap-0063 decided default refused as unruled")

    assert trails_connect_wave() is True
    assert GENERATION_EPIC == 38
    assert blocks_library_whatif_or_door() is False
    print(f"trails connect-wave; does not block {', '.join(DOES_NOT_BLOCK_SURFACES)}")

    no_code = refuse_no_code_authoring(True)
    assert is_refusal(no_code)
    assert no_code.context["logic_path"] == "ordinary_python"
    print("no-code refused; rung 2 ordinary python remains the logic path")
    print("generation gaps unfilled ok")


if __name__ == "__main__":
    main()
