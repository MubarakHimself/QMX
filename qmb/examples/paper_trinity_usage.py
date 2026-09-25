"""L27 reference usage: research-paper, hub inbox, notebooks, aliases."""

from __future__ import annotations

import sys
from typing import TypeVar

from qmb.paper import (
    PAPER_NOUN_RESEARCH,
    QMA_PAPER_EXISTS,
    admit_exploratory_notebook,
    append_hub_inbox_fragment,
    name_research_paper,
    publish_hub_inbox,
    resolve_display_alias,
)
from qmb.registryread import RegistryFragment
from qmf.core.chrono import WriterId
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def main() -> None:
    named = name_research_paper(world=World.REPLAY)
    assert is_ok(named)
    assert named.value == PAPER_NOUN_RESEARCH
    assert QMA_PAPER_EXISTS is False
    writer = _ok(WriterId.try_create("lab", "research", "hub", "boot-36-6"))
    assert isinstance(writer, WriterId)
    source = fingerprint({"n": "src-36-6"})
    assert is_ok(source)
    fragment = RegistryFragment.try_create(source.value, {"k": 1})
    assert is_ok(fragment)
    inbox = append_hub_inbox_fragment(
        None,
        writer=writer,
        fragment=fragment.value,
        provenance="live",
    )
    assert is_ok(inbox)
    assert is_refusal(publish_hub_inbox())
    notebook = admit_exploratory_notebook(imports=("qmb", "qml"))
    assert is_ok(notebook)
    alias = resolve_display_alias(display="workspace", lane="governed", over="fp1:bot")
    assert is_ok(alias)
    sys.stdout.write("research-paper ok\n")


if __name__ == "__main__":
    main()
