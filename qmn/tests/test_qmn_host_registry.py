"""Story 25.3 — mint composition-root registry records once (E12-F01)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.registry import KindRegistry, Registrar, WriteOutcome
from qmn.host import (
    COMPOSE_RECORD_KINDS,
    COMPOSITION_ROOT_SURFACE,
    DOOR_LOCAL_REGISTRY_CACHE,
    HAS_ALTERNATE_IDENTITY_FUNCTION,
    REGISTRY_MINT_SURFACE,
    CompositionRootRegistry,
    install_compose_kinds,
    mint_compose_record,
)

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_QMN_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(payload: object) -> Fingerprint:
    return _ok(fingerprint(payload))


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer(machine: str, kind: str = "book-definition") -> WriterId:
    return _ok(WriterId.try_create(machine, "authoring", kind, "boot-1"))


def _definition_fp(label: str = "book-def-v1") -> Fingerprint:
    return _fp({"class": "canonical-definition", "label": label})


def _composition_fp(label: str = "boot-epoch-a") -> Fingerprint:
    return _fp({"class": "composition_fp", "label": label})


def _content(label: str = "scalper-book") -> dict[str, object]:
    return {"label": label, "accounting_currency": "USD"}


def test_compose_kind_roster_covers_story_artifacts() -> None:
    assert COMPOSE_RECORD_KINDS == (
        "book-definition",
        "bms-definition",
        "book-binding",
        "seat",
        "calendar-identity",
        "capability-profile",
        "producer-definition",
    )
    assert REGISTRY_MINT_SURFACE == COMPOSITION_ROOT_SURFACE == "qmn.host"
    assert DOOR_LOCAL_REGISTRY_CACHE is False
    assert HAS_ALTERNATE_IDENTITY_FUNCTION is False


def test_mint_once_per_fingerprint_through_registrar() -> None:
    root = _ok(CompositionRootRegistry.try_create(composition_fp=_composition_fp()))
    definition = _definition_fp()
    first = _ok(
        root.mint(
            kind="book-definition",
            content=_content(),
            writer=_writer("node-a"),
            sequence=0,
            created_at=_instant(),
            definition_fp=definition,
        )
    )
    assert first.was_stored is True
    assert first.outcome is WriteOutcome.STORED
    assert first.definition_fp == definition
    assert first.composition_fp == root.composition_fp
    assert definition in first.record.at_birth_parent_refs
    assert first.stable_id.value.startswith("fp1:sha256:")

    # Same content, different writer/created-at — idempotent, first record kept.
    second = _ok(
        root.mint(
            kind="book-definition",
            content=_content(),
            writer=_writer("node-b"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 500),
            definition_fp=definition,
        )
    )
    assert second.was_idempotent is True
    assert second.outcome is WriteOutcome.IDEMPOTENT
    assert second.record.stable_id == first.record.stable_id
    assert second.record.writer == first.record.writer
    assert second.record.created_at == first.record.created_at
    # Occurrence evidence still cites this composition and definition.
    assert second.definition_fp == definition
    assert second.composition_fp == root.composition_fp


def test_all_compose_kinds_mint_exactly_once() -> None:
    root = _ok(CompositionRootRegistry.try_create(composition_fp=_composition_fp()))
    definition = _definition_fp("shared-def")
    for index, kind in enumerate(COMPOSE_RECORD_KINDS):
        evidence = _ok(
            root.mint(
                kind=kind,
                content={"kind": kind, "token": f"artifact-{index}"},
                writer=_writer("node-a", kind),
                sequence=index,
                created_at=_instant(_CREATED_NS + index),
                definition_fp=definition,
            )
        )
        assert evidence.kind == kind
        assert evidence.was_stored is True
        again = _ok(
            root.mint(
                kind=kind,
                content={"kind": kind, "token": f"artifact-{index}"},
                writer=_writer("timer-unit", kind),
                sequence=0,
                created_at=_instant(_CREATED_NS + 10_000 + index),
                definition_fp=definition,
            )
        )
        assert again.was_idempotent is True
        assert again.stable_id == evidence.stable_id


def test_duplicate_across_two_registrars_shares_stable_id() -> None:
    """Two processes/timers: identical content → one stable id (AC2)."""
    definition = _definition_fp()
    content = _content("shared")
    composition_a = _composition_fp("process-a")
    composition_b = _composition_fp("process-b")

    root_a = _ok(CompositionRootRegistry.try_create(composition_fp=composition_a))
    root_b = _ok(CompositionRootRegistry.try_create(composition_fp=composition_b))

    a = _ok(
        root_a.mint(
            kind="capability-profile",
            content=content,
            writer=_writer("process-a", "capability-profile"),
            sequence=0,
            created_at=_instant(),
            definition_fp=definition,
        )
    )
    b = _ok(
        root_b.mint(
            kind="capability-profile",
            content=content,
            writer=_writer("process-b", "capability-profile"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 1),
            definition_fp=definition,
        )
    )
    assert a.stable_id == b.stable_id
    assert a.composition_fp != b.composition_fp
    assert a.was_stored and b.was_stored  # separate registrar stores, same identity


def test_shared_registrar_dedups_across_timers() -> None:
    """Same Registrar (shared store): second timer gets idempotent + occurrence cite."""
    registry = KindRegistry()
    _ok(install_compose_kinds(registry))
    registrar = Registrar(registry)
    definition = _definition_fp()
    content = {"producer_id": "sqs-baseline-v1"}

    node = _ok(
        CompositionRootRegistry.try_create(
            composition_fp=_composition_fp("node"),
            registrar=registrar,
        )
    )
    timer = _ok(
        CompositionRootRegistry.try_create(
            composition_fp=_composition_fp("timer"),
            registrar=registrar,
        )
    )
    first = _ok(
        node.mint(
            kind="producer-definition",
            content=content,
            writer=_writer("node", "producer-definition"),
            sequence=0,
            created_at=_instant(),
            definition_fp=definition,
        )
    )
    second = _ok(
        timer.mint(
            kind="producer-definition",
            content=content,
            writer=_writer("timer", "producer-definition"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 9),
            definition_fp=definition,
        )
    )
    assert first.was_stored
    assert second.was_idempotent
    assert second.record is first.record or second.stable_id == first.stable_id
    assert second.composition_fp == timer.composition_fp
    assert second.definition_fp == definition


def test_composition_fp_never_enters_record_identity() -> None:
    root = _ok(CompositionRootRegistry.try_create(composition_fp=_composition_fp("a")))
    refused = mint_compose_record(
        kind="seat",
        content={"bot_fp1": "x", "composition_fp": root.composition_fp.value},
        registrar=root.registrar,
        writer=_writer("node-a", "seat"),
        sequence=0,
        created_at=_instant(),
        definition_fp=_definition_fp(),
        composition_fp=root.composition_fp,
    )
    assert is_refusal(refused)
    assert refused.context["field"] in {"body", "content"}


def test_unknown_kind_and_non_registrar_refuse() -> None:
    root = _ok(CompositionRootRegistry.try_create(composition_fp=_composition_fp()))
    assert is_refusal(
        root.mint(
            kind="not-a-compose-kind",
            content=_content(),
            writer=_writer("node-a"),
            sequence=0,
            created_at=_instant(),
            definition_fp=_definition_fp(),
        )
    )
    assert is_refusal(
        mint_compose_record(
            kind="book-binding",
            content=_content(),
            registrar=object(),
            writer=_writer("node-a", "book-binding"),
            sequence=0,
            created_at=_instant(),
            definition_fp=_definition_fp(),
            composition_fp=_composition_fp(),
        )
    )


def test_only_host_mints_through_registrar_seam() -> None:
    """Child packages never call Registrar.register; doors never import registry mint."""
    banned_roots = (
        "loop",
        "venue",
        "order",
        "protection",
        "ledger",
        "paper",
        "reconcile",
        "seats",
        "promotion",
        "mis",
        "data",
        "time",
        "secrets",
        "config",
        "observability",
        "doors",
        "replay",
        "bench",
    )
    violations: list[str] = []
    for package in banned_roots:
        root = _QMN_SRC / package
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                module = node.module
                if (
                    module.startswith("qmf.registry")
                    or module in {"qmn.host.registry_mint", "qmn.host.lineage_persist"}
                ):
                    violations.append(f"{path.relative_to(_QMN_SRC)}: imports {module}")
    assert violations == [], f"child/door registry mint surface leak: {violations}"


def test_doors_have_no_registry_cache_or_identity_function() -> None:
    doors = _QMN_SRC / "doors"
    for path in sorted(doors.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert "Registrar" not in text
        assert "KindRegistry" not in text
        assert "fingerprint(" not in text
        assert "registry_mint" not in text
        assert "composition_fp" not in text
