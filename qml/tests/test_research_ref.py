"""Story 50.2 — research_ref is fp1-shaped qml-research-hypothesis fingerprint."""

from __future__ import annotations

import json
from dataclasses import fields

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qml.research import (
    F_SLOTS,
    RESEARCH_CONTRACT_CLASS,
    RESEARCH_FORMAT_VERSION,
    DictionaryCite,
    EvidenceClaim,
    Graph,
    LayoutDemoProjection,
    RoleBinding,
    fingerprint_hypothesis,
    hypothesis_canonical_bytes,
    hypothesis_identity_payload,
    mint_hypothesis,
    project_layout_demo,
    save_hypothesis,
)

from qml import research


def _sample_hypothesis():
    cite = DictionaryCite("dictionary/a.md", "swing-high")
    return mint_hypothesis(
        hypothesis_class="entry_hypothesis",
        origin="seed_package",
        dictionary_cites=[cite],
        role_bindings=[RoleBinding(cite=cite, role="location")],
        graph=Graph(operators=("ALL", "THEN"), meaning=("boolean", "temporal")),
        evidence=[EvidenceClaim(claim="LAYOUT-DEMO sketch", locator="identity.md")],
        unknowns=("F unresolved",),
        f_labels=dict.fromkeys(F_SLOTS, "unresolved"),
        h_labels={"exits": "unresolved"},
        package_id="STRAT-000001",
        title="asian high london",
    ).value


def test_research_ref_is_fp1_shaped_qml_research_hypothesis_fingerprint() -> None:
    hyp = _sample_hypothesis()
    payload = hypothesis_identity_payload(hyp)
    assert payload == {
        "class": RESEARCH_CONTRACT_CLASS,
        "contract_format_version": RESEARCH_FORMAT_VERSION,
        "body": hyp.canonical_body(),
    }
    assert payload["class"] == "qml-research-hypothesis"
    for banned in ("occurrence", "writer", "created_at", "snapshot_ref", "research_ref"):
        assert banned not in payload
        assert banned not in payload["body"]

    ref = fingerprint_hypothesis(hyp)
    assert is_ok(ref)
    assert isinstance(ref.value, Fingerprint)
    assert ref.value.value.startswith("fp1:sha256:")
    assert len(ref.value.digest) == 64
    assert not ref.value.value.startswith("research:sha256:")

    via_core = fingerprint(payload)
    assert is_ok(via_core)
    assert ref.value.value == via_core.value.value
    assert hyp.fingerprint_content().value.value == ref.value.value

    canonical = hypothesis_canonical_bytes(hyp)
    assert is_ok(canonical)
    parsed = json.loads(canonical.value.decode("utf-8"))
    assert list(parsed.keys()) == sorted(parsed.keys())
    assert parsed["class"] == RESEARCH_CONTRACT_CLASS
    assert parsed["contract_format_version"] == RESEARCH_FORMAT_VERSION
    assert "body" in parsed


def test_research_ref_is_not_registry_kind_or_artifact_rail() -> None:
    hyp = _sample_hypothesis()
    payload = hypothesis_identity_payload(hyp)
    # Preimage class is dedicated — not Bot / experiment / Citation envelopes.
    assert payload["class"] == "qml-research-hypothesis"
    assert payload["class"] != "bot-definition"
    assert payload["class"] != "research"
    assert payload["class"] != "citation"
    assert "kind" not in payload
    assert not hasattr(research, "register_research_kind")
    assert "research:sha256:" not in fingerprint_hypothesis(hyp).value.value


def test_projection_view_still_does_not_mint_research_ref() -> None:
    # Viewing cited seed remains a non-save (Story 49.6 / UX-DR5).
    assert not hasattr(research, "research_ref")
    assert not hasattr(research, "mint_research_ref")
    names = {item.name for item in fields(LayoutDemoProjection)}
    assert "research_ref" not in names

    refused_fp = fingerprint_hypothesis(object())
    assert is_refusal(refused_fp)
    assert refused_fp.category is RefusalCategory.INVALID_INPUT

    # save_hypothesis on a projection still refuses (explicit save is Story 50.3).
    # Use a minimal stand-in typed as LayoutDemoProjection via project failure path:
    # constructing a projection without seed bytes is not required — call save on
    # a fresh LayoutDemoProjection instance built through the dataclass.
    view = LayoutDemoProjection(
        package_id="STRAT-000001",
        hypothesis_class="entry_hypothesis",
        f_labels=dict.fromkeys(F_SLOTS, "unresolved"),
        graph_operators=("ALL", "THEN"),
        direction="long",
        market="forex",
        read_only=True,
    )
    saved = save_hypothesis(view)
    assert is_refusal(saved)
    assert saved.context["research_ref"] is None
    assert saved.context["read_only"] is True
    payload = dict(view.to_payload())
    assert "research_ref" not in payload
    assert project_layout_demo is not None
