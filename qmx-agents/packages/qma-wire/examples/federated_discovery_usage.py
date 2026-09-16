"""Reference usage — federated KnowledgeHit | ArtifactHit DTO (Story 52.1)."""

from __future__ import annotations

from qma.wire import (
    FEDERATED_HIT_CONTRACT,
    FEDERATED_HIT_DTO_OWNER,
    FEDERATED_HIT_NEW_CT_MINTED,
    ArtifactHit,
    KnowledgeHit,
    parse_federated_hit,
    validate_federated_hit,
)
from qmf.core import is_ok, is_refusal

_FP1 = "fp1:sha256:" + ("cd" * 32)


def main() -> None:
    assert FEDERATED_HIT_DTO_OWNER == "COMP-QMA-WIRE"
    assert FEDERATED_HIT_CONTRACT == "CT-40"
    assert FEDERATED_HIT_NEW_CT_MINTED is False

    knowledge = KnowledgeHit.try_create(
        source_ref="strats",
        snapshot_ref=_FP1,
        locator="strategies/LAYOUT-DEMO.md",
    )
    assert is_ok(knowledge)
    print("knowledge hit_class=knowledge; cite handles only")

    artifact = ArtifactHit.try_create(fp1=_FP1, kind="saved-view")
    assert is_ok(artifact)
    print("artifact hit_class=artifact; kind is roster or query-hit tag")

    refused = parse_federated_hit({"hit_class": "strats", "fp1": _FP1, "kind": "strats"})
    assert is_refusal(refused)
    print("strats / qml_candidate hit_class refused (DEC-0412)")

    cite_copy = validate_federated_hit(
        {
            "hit_class": "artifact",
            "fp1": _FP1,
            "kind": "bot-definition",
            "artifact_ref": "copy:1",
        }
    )
    assert is_refusal(cite_copy)
    print("cite-copy artifact_ref is not an Artifact-rail hit")


if __name__ == "__main__":
    main()
