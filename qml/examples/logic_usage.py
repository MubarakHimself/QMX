"""Reference usage — logic identity via a reproducible source-manifest fp1 (Story 11.3).

Executable::

    python qml/examples/logic_usage.py

Shows the things QL-2 / Story 11.3 pin down:

1. The logic half is identified by distribution + version + a normalized
   source-manifest fingerprint in ``fp1:sha256:<hex>`` form.
2. That fingerprint is computed only by calling qmf-core's canonical fp1
   function — qml never re-implements hashing.
3. Identical source built in two sandboxes (different wheel timestamps and
   build metadata) yields one Bot ``fp1``.
4. A one-character source change mints a new Bot ``fp1``.
5. An unresolvable logic distribution at Layer 1 is ``unavailable dependency``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar

from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qml.declaration import AuthoredArtifact, AuthoredKind
from qml.logic import (
    fingerprint_source_manifest,
    mint_logic_identity,
    normalize_source_manifest,
    resolve_logic_at_layer1,
)

import qml

T = TypeVar("T")

_BOT_PY = "def on_instant(self, instant):\n    return ()\n"
_SOURCE = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": _BOT_PY,
}


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _sandbox(stamp: str) -> dict[str, object]:
    """Same source plus non-reproducible wheel bytes that must not enter identity."""
    return {
        **_SOURCE,
        "research_bot-1.0.0-py3-none-any.whl": f"wheel-{stamp}".encode(),
        "research_bot-1.0.0.dist-info/WHEEL": f"Wheel-Version: 1.0\nBuild: {stamp}\n",
        "research_bot-1.0.0.dist-info/RECORD": f"research_bot/bot.py,{stamp}\n",
        "research_bot/__pycache__/bot.cpython-314.pyc": stamp.encode() + b"\x00\x01",
    }


def _bot_fp(source_tree: Mapping[str, object]) -> str:
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", source_tree), "logic identity")
    artifact = _unwrap(
        AuthoredArtifact.try_create(
            AuthoredKind.BOT_DEFINITION,
            1,
            {"logic_reference": logic.as_logic_reference()},
        ),
        "bot definition",
    )
    fp = _unwrap(fingerprint(artifact.identity_payload()), "bot fp1")
    return fp.value


def source_manifest_is_fp1_via_qmf_core() -> str:
    """Normalized tree hashes only through ``qmf.core.fingerprint``."""
    files = _unwrap(normalize_source_manifest(_SOURCE), "normalize")
    own = _unwrap(fingerprint_source_manifest(_SOURCE), "source-manifest fp")
    via_core = _unwrap(fingerprint(dict(files)), "qmf-core fp1")
    assert own.value == via_core.value
    assert own.value.startswith("fp1:sha256:")
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", _SOURCE), "mint")
    payload = logic.fp1_identity()
    assert payload["distribution"] == "research-bot"
    assert payload["distribution_version"] == "1.0.0"
    assert qml.__version__ not in payload.values()
    assert "wheel_timestamp" not in payload
    return own.value


def two_sandboxes_one_bot_fp1() -> bool:
    """Different wheel timestamps; one Bot fp1 because identity is source, not the wheel."""
    a = _bot_fp(_sandbox("ci-node-a"))
    b = _bot_fp(_sandbox("ci-node-b"))
    clean = _bot_fp(dict(_SOURCE))
    assert a == b == clean
    assert a.startswith("fp1:sha256:")
    return a == b


def one_character_change_mints_new_bot_fp1() -> bool:
    """A code change mints a new Bot exactly as a changed default mints a new Book."""
    base = _bot_fp(dict(_SOURCE))
    changed = {**_SOURCE, "research_bot/bot.py": _BOT_PY + " "}
    after = _bot_fp(changed)
    assert base != after
    return base != after


def unresolvable_logic_is_unavailable_dependency() -> TypedRefusal:
    """Layer 1 never silently passes a missing logic distribution."""
    present = _unwrap(mint_logic_identity("research-bot", "1.0.0", _SOURCE), "present logic")
    found = resolve_logic_at_layer1(present, [present])
    assert is_ok(found)
    missing = resolve_logic_at_layer1(
        {
            "distribution": "unknown-bot",
            "distribution_version": "1.0.0",
            "source_manifest": present.source_manifest.value,
        },
        [present],
    )
    assert isinstance(missing, TypedRefusal)
    assert missing.category.value == "unavailable dependency"
    assert missing.context["journal"] is True
    empty = resolve_logic_at_layer1(present, ())
    assert isinstance(empty, TypedRefusal)
    assert empty.category.value == "unavailable dependency"
    return missing


def main() -> None:
    manifest = source_manifest_is_fp1_via_qmf_core()
    print(f"source-manifest fingerprint: {manifest[:19]}...")
    print(f"two sandboxes one Bot fp1: {two_sandboxes_one_bot_fp1()}")
    print(f"one-character change mints new Bot fp1: {one_character_change_mints_new_bot_fp1()}")
    missing = unresolvable_logic_is_unavailable_dependency()
    print(f"unresolvable logic at Layer 1: {missing.category.value}")
    print("logic identity ok")


if __name__ == "__main__":
    main()
