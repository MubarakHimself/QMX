"""Story 11.3 — logic identity is a reproducible source-manifest fp1 (QL-2)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.declaration import AuthoredArtifact, AuthoredKind
from qml.logic import (
    LOGIC_REFERENCE_CLASS,
    LogicIdentity,
    fingerprint_source_manifest,
    mint_logic_identity,
    normalize_source_manifest,
    resolve_logic_at_layer1,
)

import qml

T = TypeVar("T")

_QML_SRC = Path(__file__).resolve().parents[1] / "src" / "qml"
_BOT_PY = "def on_instant(self, instant):\n    return ()\n"
_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": _BOT_PY,
}


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _bot_fp(logic: LogicIdentity) -> Fingerprint:
    artifact = _ok(
        AuthoredArtifact.try_create(
            AuthoredKind.BOT_DEFINITION,
            1,
            {"logic_reference": logic.as_logic_reference()},
        )
    )
    return _ok(fingerprint(artifact.identity_payload()))


def _sandbox(source: dict[str, str], *, stamp: str) -> dict[str, object]:
    """A 'build' of ``source``: same files plus non-reproducible wheel metadata."""
    return {
        **source,
        "research_bot-1.0.0-py3-none-any.whl": f"wheel-bytes-{stamp}".encode(),
        "research_bot-1.0.0.dist-info/WHEEL": (
            f"Wheel-Version: 1.0\nGenerator: bdist_wheel\nBuild: {stamp}\n"
        ),
        "research_bot-1.0.0.dist-info/RECORD": (
            f"research_bot/bot.py,sha256=not-identity,{stamp}\n"
        ),
        "research_bot/__pycache__/bot.cpython-314.pyc": b"\x00\x01" + stamp.encode(),
        "research_bot.egg-info/PKG-INFO": f"Build-Stamp: {stamp}\n",
    }


# --- AC: source-manifest fp1 via qmf-core only --------------------------------


def test_source_manifest_fingerprint_is_fp1_from_qmf_core_only() -> None:
    manifest = _ok(fingerprint_source_manifest(_SOURCE))
    via_core = _ok(fingerprint(dict(_ok(normalize_source_manifest(_SOURCE)))))
    assert manifest == via_core
    assert manifest.value.startswith("fp1:sha256:")
    assert len(manifest.digest) == 64
    parsed = _ok(Fingerprint.try_create(manifest.value))
    assert parsed == manifest


def test_qml_source_never_reimplements_fp1() -> None:
    banned = frozenset({"hashlib", "hmac"})
    violations: list[str] = []
    for path in sorted(_QML_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names.append(node.module)
            for name in names:
                if name in banned or any(name.startswith(item + ".") for item in banned):
                    violations.append(f"{path}: imports {name}")
    assert violations == []


def test_logic_identity_payload_excludes_semver_and_occurrence() -> None:
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    payload = logic.fp1_identity()
    assert payload["class"] == LOGIC_REFERENCE_CLASS
    assert payload["distribution"] == "research-bot"
    assert payload["distribution_version"] == "1.0.0"
    assert str(payload["source_manifest"]).startswith("fp1:sha256:")
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "created_at" not in payload
    assert "wheel_timestamp" not in payload
    assert "build_metadata" not in payload
    assert qml.__version__ not in payload.values()
    own = _ok(logic.fingerprint_content())
    via_core = _ok(fingerprint(logic))
    assert own == via_core
    assert own.value.startswith("fp1:sha256:")


def test_normalize_drops_wheels_and_accepts_posix_or_backslash_paths() -> None:
    mixed = {
        r"research_bot\bot.py": _BOT_PY,
        "./research_bot/__init__.py": "",
        "research_bot-1.0.0-py3-none-any.whl": b"PK\x03\x04",
    }
    normalized = dict(_ok(normalize_source_manifest(mixed)))
    assert set(normalized) == {"research_bot/bot.py", "research_bot/__init__.py"}
    assert normalized["research_bot/bot.py"] == _BOT_PY


def test_nfc_equivalent_paths_are_a_duplicate() -> None:
    collided = normalize_source_manifest({"cafe\u0301.py": "x", "caf\u00e9.py": "x"})
    assert is_refusal(collided)
    assert collided.category is RefusalCategory.INVALID_INPUT


def test_dot_segments_collapse_and_nul_is_refused() -> None:
    normalized = dict(_ok(normalize_source_manifest({"./pkg/./bot.py": "x"})))
    assert set(normalized) == {"pkg/bot.py"}
    assert is_refusal(normalize_source_manifest({"bot.py\x00": "x"}))
    assert is_refusal(normalize_source_manifest({"//abs/bot.py": "x"}))


def test_duplicate_path_after_slash_normalization_is_invalid() -> None:
    dup = normalize_source_manifest(
        {r"pkg\bot.py": "a", "pkg/bot.py": "b"},
    )
    assert is_refusal(dup)
    assert dup.category is RefusalCategory.INVALID_INPUT


def test_parent_absolute_and_non_mapping_trees_are_invalid() -> None:
    assert is_refusal(normalize_source_manifest({"../bot.py": "x"}))
    assert is_refusal(normalize_source_manifest({"/abs/bot.py": "x"}))
    assert is_refusal(normalize_source_manifest({"C:/abs/bot.py": "x"}))
    assert is_refusal(normalize_source_manifest({"": "x"}))
    assert is_refusal(normalize_source_manifest({1: "x"}))
    assert is_refusal(fingerprint_source_manifest(["nope"]))
    assert is_refusal(normalize_source_manifest({"bot.py": 1}))
    empty = normalize_source_manifest(
        {"pkg/__pycache__/x.pyc": b"\x00", "pkg-1.0.0-py3-none-any.whl": b"PK"}
    )
    assert is_refusal(empty)
    assert empty.category is RefusalCategory.INVALID_INPUT


def test_utf8_bytes_and_binary_bytes_enter_as_text_or_hex() -> None:
    text = _ok(
        fingerprint_source_manifest({"bot.py": _BOT_PY.encode("utf-8")}),
    )
    same = _ok(fingerprint_source_manifest({"bot.py": _BOT_PY}))
    assert text == same
    binary = _ok(fingerprint_source_manifest({"weights.bin": b"\xff\xfe\x00\x01"}))
    again = _ok(fingerprint_source_manifest({"weights.bin": b"\xff\xfe\x00\x01"}))
    assert binary == again
    hexed = dict(_ok(normalize_source_manifest({"weights.bin": b"\xff\xfe\x00\x01"})))
    assert hexed["weights.bin"] == b"\xff\xfe\x00\x01".hex()


# --- AC: two sandboxes, one Bot fp1; wheel bytes never enter ------------------


def test_identical_source_in_two_sandboxes_yields_one_bot_fp1() -> None:
    a = _ok(mint_logic_identity("research-bot", "1.0.0", _sandbox(_SOURCE, stamp="ci-a")))
    b = _ok(mint_logic_identity("research-bot", "1.0.0", _sandbox(_SOURCE, stamp="ci-b")))
    assert a.source_manifest == b.source_manifest
    assert a.fp1_identity() == b.fp1_identity()
    fp_a = _bot_fp(a)
    fp_b = _bot_fp(b)
    assert fp_a == fp_b
    assert fp_a.value.startswith("fp1:sha256:")
    clean = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    assert _bot_fp(clean) == fp_a
    payload = a.fp1_identity()
    assert "ci-a" not in str(payload)
    assert "ci-b" not in str(payload)
    assert "Wheel-Version" not in str(payload)


# --- AC: one-character source change mints a new Bot fp1 ----------------------


def test_one_character_source_change_mints_a_new_bot_fp1() -> None:
    base = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    changed_tree = {**_SOURCE, "research_bot/bot.py": _BOT_PY.replace("return ()", "return( )")}
    changed = _ok(mint_logic_identity("research-bot", "1.0.0", changed_tree))
    assert base.source_manifest != changed.source_manifest
    assert _bot_fp(base) != _bot_fp(changed)
    other_dist = _ok(mint_logic_identity("other-bot", "1.0.0", _SOURCE))
    other_ver = _ok(mint_logic_identity("research-bot", "1.0.1", _SOURCE))
    assert _bot_fp(base) != _bot_fp(other_dist)
    assert _bot_fp(base) != _bot_fp(other_ver)


def test_try_create_from_manifest_fingerprint_round_trips() -> None:
    minted = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    cited = _ok(
        LogicIdentity.try_create(
            "research-bot",
            "1.0.0",
            source_manifest=minted.source_manifest,
        )
    )
    assert cited == minted
    from_string = _ok(
        LogicIdentity.try_create(
            "research-bot",
            "1.0.0",
            source_manifest=minted.source_manifest.value,
        )
    )
    assert from_string == minted
    matching = _ok(
        LogicIdentity.try_create(
            "research-bot",
            "1.0.0",
            _SOURCE,
            source_manifest=minted.source_manifest,
        )
    )
    assert matching == minted
    mismatch = LogicIdentity.try_create(
        "research-bot",
        "1.0.0",
        {**_SOURCE, "research_bot/bot.py": _BOT_PY + "#"},
        source_manifest=minted.source_manifest,
    )
    assert is_refusal(mismatch)
    assert mismatch.category is RefusalCategory.INVALID_INPUT
    bad_tree = LogicIdentity.try_create(
        "research-bot",
        "1.0.0",
        {"pkg-1.0.0-py3-none-any.whl": b"PK"},
        source_manifest=minted.source_manifest,
    )
    assert is_refusal(bad_tree)
    bad_fp = LogicIdentity.try_create(
        "research-bot",
        "1.0.0",
        _SOURCE,
        source_manifest="not-a-fingerprint",
    )
    assert is_refusal(bad_fp)


def test_try_create_refuses_blank_parts_and_missing_source() -> None:
    assert is_refusal(mint_logic_identity("  ", "1.0.0", _SOURCE))
    assert is_refusal(mint_logic_identity("research-bot", "", _SOURCE))
    assert is_refusal(LogicIdentity.try_create("research-bot", "1.0.0"))
    assert is_refusal(LogicIdentity.try_create("research-bot", "1.0.0", source_manifest="not-fp1"))
    assert is_refusal(LogicIdentity.try_from_payload("nope"))
    assert is_refusal(LogicIdentity.try_from_payload({"family_id": "x"}))
    assert is_refusal(LogicIdentity.try_from_payload({"logic_reference": "nope"}))


# --- AC: unresolvable logic distribution is unavailable dependency ------------


def test_layer1_resolves_present_logic_and_refuses_a_miss() -> None:
    present = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    found = resolve_logic_at_layer1(present, [present])
    assert is_ok(found)
    assert found.value == present
    from_payload = resolve_logic_at_layer1(present.fp1_identity(), [present])
    assert is_ok(from_payload)
    from_declaration = resolve_logic_at_layer1(
        {"logic_reference": present.as_logic_reference()},
        [present],
    )
    assert is_ok(from_declaration)
    artifact = _ok(
        AuthoredArtifact.try_create(
            AuthoredKind.BOT_DEFINITION,
            1,
            {"logic_reference": present.as_logic_reference()},
        )
    )
    from_artifact = resolve_logic_at_layer1(artifact.identity_payload(), [present])
    assert is_ok(from_artifact)
    missing = resolve_logic_at_layer1(
        {
            "distribution": "missing-bot",
            "distribution_version": "1.0.0",
            "source_manifest": present.source_manifest.value,
        },
        [present],
    )
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert missing.context["journal"] is True
    empty = resolve_logic_at_layer1(present, ())
    assert is_refusal(empty)
    assert empty.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_layer1_never_silently_passes_a_blank_or_non_catalog() -> None:
    blank = resolve_logic_at_layer1({"logic_reference": {}}, ())
    assert is_refusal(blank)
    assert blank.category is RefusalCategory.INVALID_INPUT
    missing_field = resolve_logic_at_layer1({"family_id": "trend-follow"}, ())
    assert is_refusal(missing_field)
    assert missing_field.category is RefusalCategory.INVALID_INPUT
    bad_catalog = resolve_logic_at_layer1(
        _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE)),
        "not-a-catalog",
    )
    assert is_refusal(bad_catalog)
    assert bad_catalog.category is RefusalCategory.INVALID_INPUT


def test_layer1_accepts_mapping_catalog_and_skips_non_logic_items() -> None:
    present = _ok(mint_logic_identity("research-bot", "1.0.0", _SOURCE))
    by_name = resolve_logic_at_layer1(present, {"research-bot": present})
    assert is_ok(by_name)
    catalog: list[object] = [
        object(),
        {"kind": "strategy-family", "body": {"family_id": "trend-follow"}},
        present.fp1_identity(),
    ]
    found = resolve_logic_at_layer1(present, catalog)
    assert is_ok(found)
    assert found.value.distribution == "research-bot"
    assert is_ok(LogicIdentity.try_from_payload(present))
    assert is_ok(
        LogicIdentity.try_from_payload({"logic_reference": present}),
    )
