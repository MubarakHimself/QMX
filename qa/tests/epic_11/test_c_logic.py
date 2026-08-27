"""Epic 11 / Story 11.3 — reproducible source-manifest logic identity (FR-047, QL-2, AR-63).

C1 fp1 form; C2s qmf-core-only seam; C2 reproducibility over build-env noise;
C3 one-character source change mints a new Bot; C4 unresolvable logic ->
unavailable dependency (R-009). C2/C3 are Hypothesis properties; a companion
non-vacuity test shows a real source change is detected while build bytes are not.
"""

from __future__ import annotations

import helpers as H
from hypothesis import given, settings
from hypothesis import strategies as st

from qml.declaration import mint_bot_definition
from qml.logic import (
    fingerprint_source_manifest,
    mint_logic_identity,
    normalize_source_manifest,
    resolve_logic_at_layer1,
)
from qmf.core.fingerprint import fingerprint


def _bot_fp(source_tree: object) -> str:
    """The containing Bot definition fp1 for a logic distribution built from ``source_tree``."""
    logic = H.unwrap(mint_logic_identity("research-bot", "1.0.0", source_tree), "logic")
    bot = H.unwrap(mint_bot_definition(H.bot_payload(logic_reference=logic)), "bot")
    return H.unwrap(bot.fingerprint_content(), "bot fp").value


def test_c1_source_manifest_fingerprint_is_fp1_sha256_form() -> None:
    """C1 (11.3 AC1, AR-63): the source-manifest fingerprint is fp1:sha256:<hex>."""
    fp = H.unwrap(fingerprint_source_manifest(H.logic_source()), "manifest fp")
    assert fp.value.startswith("fp1:sha256:")
    assert len(fp.value.split(":")[2]) == 64


def test_c2s_source_manifest_hashes_only_through_qmf_core() -> None:
    """C2s (11.3 AC1): qml computes the manifest fp only by calling qmf-core's fp1.

    Counter-case: a locally re-implemented hash would diverge from qmf-core's fp1
    over the same normalized tree.
    """
    files = H.unwrap(normalize_source_manifest(H.logic_source()), "normalized")
    via_qml = H.unwrap(fingerprint_source_manifest(H.logic_source()), "qml manifest fp")
    via_core = H.unwrap(fingerprint(dict(files)), "qmf-core fp1")
    assert via_qml.value == via_core.value


@settings(max_examples=40, deadline=None)
@given(s1=st.text(min_size=1, max_size=12), s2=st.text(min_size=1, max_size=12))
def test_c2_build_artifact_bytes_never_enter_bot_identity(s1: str, s2: str) -> None:
    """C2 (11.3 AC2): identical source built in two sandboxes yields one Bot fp1.

    Wheel timestamps / dist-info / __pycache__ bytes vary by stamp yet the Bot fp1
    is invariant. Counter-case: if any build byte entered identity, distinct
    stamps would fork the fingerprint.
    """
    clean = _bot_fp(dict(H.logic_source()))
    fp1 = _bot_fp(H.sandbox_source(s1))
    fp2 = _bot_fp(H.sandbox_source(s2))
    assert fp1 == fp2 == clean


@settings(max_examples=40, deadline=None)
@given(suffix=st.text(alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=1, max_size=6))
def test_c3_one_character_source_change_mints_a_new_bot(suffix: str) -> None:
    """C3 (11.3 AC3): a change to the logic source mints a new Bot fp1.

    A code change mints a new Bot exactly as a changed default mints a new Book.
    Counter-case: base fp1 == changed fp1 (the change was invisible to identity).
    """
    base = _bot_fp(dict(H.logic_source()))
    changed_tree = dict(H.logic_source())
    changed_tree["research_bot/bot.py"] = changed_tree["research_bot/bot.py"] + suffix
    assert _bot_fp(changed_tree) != base


def test_c2_c3_discrimination_is_real_not_vacuous() -> None:
    """Rule-1 non-vacuity: build bytes do NOT change identity; a source byte DOES.

    Establishes the C2 property is not passing merely because nothing ever changes
    the fingerprint.
    """
    base = _bot_fp(dict(H.logic_source()))
    build_only = _bot_fp(H.sandbox_source("stamp-x"))
    real_change = dict(H.logic_source())
    real_change["research_bot/bot.py"] += " "
    assert build_only == base  # build artifacts stripped
    assert _bot_fp(real_change) != base  # a real source byte is identity


def test_c4_unresolvable_logic_is_unavailable_dependency() -> None:
    """C4 (11.3 AC4, R-009): an unresolvable logic distribution is unavailable dependency.

    The logic reference is mandatory — a governed bot is exactly two artifacts.
    Counter-case: a silent pass on a missing distribution.
    """
    present = H.unwrap(mint_logic_identity("research-bot", "1.0.0", H.logic_source()), "present")
    missing = resolve_logic_at_layer1(
        {
            "distribution": "unknown-bot",
            "distribution_version": "1.0.0",
            "source_manifest": present.source_manifest.value,
        },
        [present],
    )
    assert H.category_of(missing) == "unavailable dependency"
    empty = resolve_logic_at_layer1(present, ())
    assert H.category_of(empty) == "unavailable dependency"
