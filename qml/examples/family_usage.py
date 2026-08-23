"""Reference usage — strategy-family CT-06 metadata records (Story 11.2).

Executable::

    python qml/examples/family_usage.py

Shows the things QL-6 / Story 11.2 pin down:

1. A strategy family is an opaque operator-minted id plus fingerprintable
   metadata content under CT-06's addable ``strategy-family`` kind — the same
   machinery as ``instrument-class``, with no new CT number.
2. QML returns fingerprintable content; a host composition root stamps writer,
   sequence, and created-at. Identical content from two sandboxes deduplicates.
3. A family is a keying token with no authority — no permitted timeframes,
   feature families, or mutation allowances.
4. The id keys Book ``exit_policy`` ``ExitLogicRef``, family-scoped paper
   starting balance, and the per-family bench threshold.
5. An unresolvable family id at Layer 1 is ``unavailable dependency``, never a
   silent pass.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qmf.registry import KindRegistry, Registrar, RegistrationRecord
from qml.families import (
    FAMILY_KEYED_SURFACES,
    FORBIDDEN_AUTHORITY_FIELDS,
    KIND_STRATEGY_FAMILY,
    FamilyKeyedSurface,
    install_strategy_family_kind,
    mint_strategy_family,
    register_strategy_family,
    resolve_family_at_layer1,
    validate_family_body,
)

import qml

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _writer(machine: str) -> WriterId:
    return _unwrap(
        WriterId.try_create(machine, "authoring", KIND_STRATEGY_FAMILY, "boot-1"),
        "writer",
    )


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "created-at")


def _host_registrar() -> Registrar:
    """Composition root: register the addable strategy-family kind, then mint."""
    registry = KindRegistry()
    _unwrap(install_strategy_family_kind(registry), "install strategy-family kind")
    return Registrar(registry)


def opaque_id_resolves_to_dated_ct06_record() -> str:
    """Mint content, host-stamp a dated CT-06 record, derive the stable id."""
    content = _unwrap(mint_strategy_family("trend-follow"), "mint family")
    assert content.family_id.value == "trend-follow"
    assert content.identity_payload()["kind"] == KIND_STRATEGY_FAMILY
    assert qml.__version__ not in content.identity_payload().values()
    registrar = _host_registrar()
    receipt = _unwrap(
        register_strategy_family(
            "trend-follow",
            registrar=registrar,
            writer=_writer("node-a"),
            sequence=0,
            created_at=_instant(),
        ),
        "host stamp",
    )
    record = receipt.record
    assert record.kind == KIND_STRATEGY_FAMILY
    assert record.body["family_id"] == "trend-follow"
    assert record.created_at == _instant()
    assert record.stable_id.value.startswith("fp1:sha256:")
    assert record.stable_id == _unwrap(fingerprint(record.fp1_identity()), "derived id")
    return record.stable_id.value


def two_sandboxes_deduplicate() -> bool:
    """Different writers and created-at; one stable id (occurrence facts excluded)."""
    body = _unwrap(mint_strategy_family("trend-follow"), "mint").body()
    a = _unwrap(
        RegistrationRecord.try_create(
            KIND_STRATEGY_FAMILY,
            1,
            [],
            body,
            _writer("node-a"),
            0,
            _instant(_CREATED_NS),
        ),
        "sandbox-a",
    )
    b = _unwrap(
        RegistrationRecord.try_create(
            KIND_STRATEGY_FAMILY,
            1,
            [],
            body,
            _writer("node-b"),
            99,
            _instant(_CREATED_NS + 500),
        ),
        "sandbox-b",
    )
    assert a.writer != b.writer
    assert a.created_at != b.created_at
    assert a.stable_id == b.stable_id
    return a.stable_id == b.stable_id


def family_has_no_authority() -> None:
    """Constraint powers do not exist on a minted family; stuffing them is refused."""
    content = _unwrap(mint_strategy_family("scalper"), "mint scalper")
    assert dict(content.constraint_powers()) == {}
    assert set(content.body()) == {"family_id"}
    for field in FORBIDDEN_AUTHORITY_FIELDS:
        assert field not in content.body()
        assert not hasattr(content, field)
    stuffed = validate_family_body(
        {
            "family_id": "scalper",
            "permitted_timeframes": ["M1"],
            "permitted_feature_families": ["ict"],
            "mutation_allowances": ["wf2"],
        }
    )
    assert isinstance(stuffed, TypedRefusal)
    assert stuffed.category.value == "policy rejection"


def family_keys_ratified_law_surfaces() -> dict[str, str]:
    """The family id keys ExitLogicRef, paper starting balance, and bench threshold."""
    content = _unwrap(mint_strategy_family("trend-follow"), "mint")
    keyed = content.keyed_surfaces()
    assert set(keyed) == FAMILY_KEYED_SURFACES
    assert keyed[FamilyKeyedSurface.EXIT_POLICY_EXIT_LOGIC_REF] == "trend-follow"
    assert keyed[FamilyKeyedSurface.PAPER_STARTING_BALANCE] == "trend-follow"
    assert keyed[FamilyKeyedSurface.BENCH_CONSECUTIVE_LOSS_THRESHOLD] == "trend-follow"
    return keyed


def unresolvable_family_is_unavailable_dependency() -> TypedRefusal:
    """Layer 1 never silently passes a missing family record."""
    present = _unwrap(mint_strategy_family("trend-follow"), "present family")
    found = resolve_family_at_layer1("trend-follow", [present])
    assert is_ok(found)
    missing = resolve_family_at_layer1("unknown-family", [present])
    assert isinstance(missing, TypedRefusal)
    assert missing.category.value == "unavailable dependency"
    assert missing.context["journal"] is True
    empty = resolve_family_at_layer1("trend-follow", ())
    assert isinstance(empty, TypedRefusal)
    assert empty.category.value == "unavailable dependency"
    return missing


def main() -> None:
    stable_id = opaque_id_resolves_to_dated_ct06_record()
    print(f"dated CT-06 family record, derived id: {stable_id[:19]}...")
    print(f"two sandboxes deduplicate: {two_sandboxes_deduplicate()}")
    family_has_no_authority()
    print("constraint powers: none (keying token, Book constrains)")
    keyed = family_keys_ratified_law_surfaces()
    print(f"keyed surfaces: {', '.join(sorted(keyed))}")
    missing = unresolvable_family_is_unavailable_dependency()
    print(f"unresolvable family at Layer 1: {missing.category.value}")
    print("family mint ok")


if __name__ == "__main__":
    main()
