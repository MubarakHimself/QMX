"""Story 40.4 — qmf-core-derived content identity and returned QMA refusals."""

from __future__ import annotations

import ast
from pathlib import Path

import qma.core
import qma.core.foundation
import qma.core.refusals
from qma.core import content_address, tree_digest
from qma.core.foundation import (
    CorrelationId,
    Instant,
    Money,
    TypedRefusal,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qma.core.refusals import (
    NAMED_REFUSAL_VARIANTS,
    CredentialOutOfScope,
    CursorScopeMismatch,
    NoEligibleDeployment,
    NoEligibleReviewer,
    NoEnvironment,
    NoMemoryProvider,
    NonLoopbackProxy,
    OperatorPrincipalRequired,
    ProhibitedMoneyPathTool,
    ProvenanceShapeMismatch,
    QmaRefusal,
    SlugUnavailable,
    StaleSnapshot,
    StoreVersionMismatch,
    UnauthenticatedProxy,
    UnknownHostRequest,
    variant_name,
)
from qmf.core.chrono import Instant as QmfInstant
from qmf.core.chrono import WriterId as QmfWriterId
from qmf.core.exact import Money as QmfMoney
from qmf.core.fingerprint import fingerprint as qmf_fingerprint
from qmf.core.refusal import TypedRefusal as QmfTypedRefusal

CORE_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "core"

EXPECTED_VARIANTS = (
    "NoMemoryProvider",
    "NoEnvironment",
    "SlugUnavailable",
    "CursorScopeMismatch",
    "NoEligibleReviewer",
    "NoEligibleDeployment",
    "NonLoopbackProxy",
    "UnauthenticatedProxy",
    "ProhibitedMoneyPathTool",
    "UnknownHostRequest",
    "ProvenanceShapeMismatch",
    "StaleSnapshot",
    "OperatorPrincipalRequired",
    "CredentialOutOfScope",
    "StoreVersionMismatch",
)


def test_named_variants_extend_typed_refusal_base() -> None:
    assert len(NAMED_REFUSAL_VARIANTS) == len(EXPECTED_VARIANTS)
    names = [cls.VARIANT for cls in NAMED_REFUSAL_VARIANTS]
    assert names == list(EXPECTED_VARIANTS)
    for cls in NAMED_REFUSAL_VARIANTS:
        assert issubclass(cls, QmaRefusal)
        assert issubclass(cls, TypedRefusal)
        assert issubclass(cls, QmfTypedRefusal)


def test_each_variant_defined_once_under_refusals() -> None:
    refusals_root = CORE_SRC / "refusals"
    assert refusals_root.is_dir()
    source_hits: dict[str, list[Path]] = {name: [] for name in EXPECTED_VARIANTS}
    for path in refusals_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in source_hits:
                source_hits[node.name].append(path)
    for name, paths in source_hits.items():
        assert len(paths) == 1, f"{name} defined in {paths}"


def test_variants_are_returned_not_raised() -> None:
    refusal = NoMemoryProvider.of(desk="research")
    assert isinstance(refusal, TypedRefusal)
    assert is_refusal(refusal)
    assert not isinstance(refusal, Exception)
    assert refusal.category.value == "unavailable dependency"
    assert refusal.retryability.value == "after-condition"
    assert refusal.context["variant"] == "NoMemoryProvider"
    assert refusal.context["desk"] == "research"
    assert variant_name(refusal) == "NoMemoryProvider"
    assert NoMemoryProvider.matches(refusal)


def test_store_version_refusal_names_store_and_both_versions() -> None:
    refusal = StoreVersionMismatch.of(
        store="journal",
        expected_schema_version=1,
        store_schema_version=3,
    )
    assert isinstance(refusal, TypedRefusal)
    assert is_refusal(refusal)
    assert refusal.context["store"] == "journal"
    assert refusal.context["expected_schema_version"] == 1
    assert refusal.context["store_schema_version"] == 3
    assert refusal.category.value == "storage failure"


def test_public_boundary_returns_typed_refusal_never_raises() -> None:
    def public_recall(*, desk: str, provider_bound: bool) -> Money | TypedRefusal:
        if not provider_bound:
            return NoMemoryProvider.of(desk=desk)
        money = Money.try_create(100, "USD", 2)
        assert is_ok(money)
        return money.value

    refused = public_recall(desk="trading", provider_bound=False)
    assert isinstance(refused, NoMemoryProvider)
    assert is_refusal(refused)
    assert not isinstance(refused, BaseException)

    ok = public_recall(desk="trading", provider_bound=True)
    assert isinstance(ok, Money)


def test_all_variant_factories_carry_structured_context() -> None:
    samples: list[QmaRefusal] = [
        NoMemoryProvider.of(desk="research"),
        NoEnvironment.of(kind="desktop"),
        SlugUnavailable.of(slug="trader", slug_kind="quant_slug"),
        CursorScopeMismatch.of(cursor_scope="desk/a", expected_scope="desk/b"),
        NoEligibleReviewer.of(model_class="REASONING_HIGH"),
        NoEligibleDeployment.of(model_class="CODING_HIGH"),
        NonLoopbackProxy.of(address="10.0.0.1:8080"),
        UnauthenticatedProxy.of(deployment_id="proxy-1"),
        ProhibitedMoneyPathTool.of(tool_id="place_order"),
        UnknownHostRequest.of(verb="invented.verb"),
        ProvenanceShapeMismatch.of(
            source_id="strats",
            expected_keys=("a", "b", "c", "d", "e", "f"),
            given_keys=("a", "b"),
        ),
        StaleSnapshot.of(snapshot_ref="snap:1"),
        OperatorPrincipalRequired.of(command="quant.create", principal_class="machine"),
        CredentialOutOfScope.of(credential_ref="cred://models/x"),
        StoreVersionMismatch.of(
            store="sqlite",
            expected_schema_version=2,
            store_schema_version=9,
        ),
    ]
    assert len(samples) == len(EXPECTED_VARIANTS)
    for sample in samples:
        assert is_refusal(sample)
        assert sample.context["variant"] in EXPECTED_VARIANTS
        assert sample.category.value
        assert sample.retryability.value
        assert sample.context is not None


def test_content_address_is_imported_fp1_over_canonical_json() -> None:
    payload = {"b": 2, "a": 1}
    qma_fp = content_address(payload)
    qmf_fp = qmf_fingerprint(payload)
    via_foundation = fingerprint(payload)
    assert is_ok(qma_fp) and is_ok(qmf_fp) and is_ok(via_foundation)
    assert qma_fp.value.value == qmf_fp.value.value == via_foundation.value.value
    assert qma_fp.value.value.startswith("fp1:sha256:")
    assert qma.core.foundation.fingerprint is qmf_fingerprint


def test_tree_digest_is_fp1_over_canonical_manifest() -> None:
    file_a = fingerprint({"path": "a.txt", "body": "one"})
    file_b = fingerprint({"path": "b.txt", "body": "two"})
    assert is_ok(file_a) and is_ok(file_b)

    digest_ab = tree_digest({"a.txt": file_a.value, "b.txt": file_b.value})
    digest_ba = tree_digest({"b.txt": file_b.value.value, "a.txt": file_a.value.value})
    assert is_ok(digest_ab) and is_ok(digest_ba)
    assert digest_ab.value.value == digest_ba.value.value

    expected = fingerprint(
        {
            "a.txt": file_a.value.value,
            "b.txt": file_b.value.value,
        }
    )
    assert is_ok(expected)
    assert digest_ab.value.value == expected.value.value


def test_no_parallel_money_time_id_or_refusal_base() -> None:
    assert Money is QmfMoney
    assert Instant is QmfInstant
    assert WriterId is QmfWriterId
    assert TypedRefusal is QmfTypedRefusal
    assert qma.core.foundation.fingerprint is qmf_fingerprint
    correlation: CorrelationId = "corr-origin-1"
    assert isinstance(correlation, str)

    forbidden = {
        "Money",
        "Price",
        "Instant",
        "Duration",
        "Fingerprint",
        "TypedRefusal",
        "WriterId",
        "CorrelationId",
    }
    minted: list[str] = []
    for path in CORE_SRC.rglob("*.py"):
        if path.name == "foundation.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in forbidden:
                minted.append(f"{path.relative_to(CORE_SRC)}:{node.name}")
    assert minted == []


def test_package_exports_content_and_foundation() -> None:
    assert qma.core.__version__ == "0.1.0"
    assert qma.core.content_address is content_address
    assert qma.core.tree_digest is tree_digest
    assert qma.core.refusals.StoreVersionMismatch is StoreVersionMismatch
