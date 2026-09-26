"""Reference usage — CT-34 confluence kind (Story 11.5).

Executable::

    python qml/examples/confluence_usage.py

Shows the things QL-5 / Story 11.5 pin down:

1. A confluence is its own reusable registry artifact: one-or-more legs of any
   role mix from the closed-and-addable vocabulary level | trigger | confirmation
   | filter. A zero-leg confluence is invalid input; counts are never bounded.
2. Each leg carries a producer binding (pinned CT-16/CT-17 fingerprint or a QL-4
   template), a child-confluence cite, or both — at least one required, role always
   mandatory.
3. Default ordering is fingerprint-ascending (order-insignificant) with display-only
   ordinals that never enter identity. Order-significance is opt-in and enters the
   fingerprint only when declared.
4. Reuse of the same content across bots mints no new confluence; a changed leg,
   role, binding, parameter, child cite, or newly-declared order-significance does.
5. A role outside the vocabulary, or a leg with neither binding nor child cite, is
   invalid input. An unresolvable producer fingerprint or cited child confluence is
   unavailable dependency. Condition semantics live in Python logic in V1.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qmf.registry import KindRegistry, Registrar
from qml.declaration import (
    KIND_CONFLUENCE,
    LEG_ROLES,
    install_confluence_kind,
    mint_confluence,
    register_confluence,
    resolve_confluence_at_layer1,
)
from qml.footprint import ProducerBinding

import qml

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _writer(machine: str) -> WriterId:
    return _unwrap(
        WriterId.try_create(machine, "authoring", KIND_CONFLUENCE, "boot-1"),
        "writer",
    )


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "created-at")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _lookback(n: int) -> ExactRational:
    return _unwrap(ExactRational.try_create(n, 1, UnitKind.COUNT), "lookback")


def _host_registrar() -> Registrar:
    registry = KindRegistry()
    _unwrap(install_confluence_kind(registry), "install confluence kind")
    return Registrar(registry)


def roles_and_one_or_more_legs() -> int:
    """Any role mix is legal; zero legs is invalid input; counts are unbounded."""
    assert frozenset({"level", "trigger", "confirmation", "filter"}) == LEG_ROLES
    mixed = _unwrap(
        mint_confluence(
            [
                {"role": "level", "producer_binding": _pinned("zone")},
                {"role": "trigger", "producer_binding": _pinned("break")},
                {"role": "confirmation", "producer_binding": _pinned("close")},
                {
                    "role": "filter",
                    "producer_binding": _pinned("session"),
                    "declared_parameters": {"lookback": _lookback(14)},
                },
            ]
        ),
        "mixed confluence",
    )
    assert len(mixed.legs) == 4
    zero = mint_confluence([])
    assert isinstance(zero, TypedRefusal)
    assert zero.category.value == "invalid input"
    many = _unwrap(
        mint_confluence(
            [{"role": "level", "producer_binding": _pinned(f"zone-{i}")} for i in range(21)]
        ),
        "unbounded levels",
    )
    assert len(many.legs) == 21
    return len(mixed.legs)


def binding_and_or_child_cite() -> str:
    """Pinned binding, child cite, or both; neither is invalid input."""
    child = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": _pinned("child-zone")}]),
        "child",
    )
    child_fp = _unwrap(child.fingerprint_content(), "child fp")
    both = _unwrap(
        mint_confluence(
            [
                {
                    "role": "trigger",
                    "producer_binding": _pinned("parent-break"),
                    "confluence_ref": child_fp,
                }
            ]
        ),
        "parent",
    )
    assert both.legs[0].producer_binding is not None
    assert both.legs[0].confluence_ref == child_fp
    neither = mint_confluence([{"role": "level"}])
    assert isinstance(neither, TypedRefusal)
    assert neither.category.value == "invalid input"
    return child_fp.value


def fingerprint_ascending_default_and_opt_in_order() -> bool:
    """Display ordinals stay out of identity unless order-significance is declared."""
    legs = [
        {"role": "trigger", "producer_binding": _pinned("zzz"), "display_ordinal": 0},
        {"role": "level", "producer_binding": _pinned("aaa"), "display_ordinal": 1},
    ]
    default = _unwrap(mint_confluence(legs), "default order")
    reversed_input = _unwrap(
        mint_confluence(
            [
                {"role": "level", "producer_binding": _pinned("aaa"), "display_ordinal": 9},
                {"role": "trigger", "producer_binding": _pinned("zzz"), "display_ordinal": 3},
            ]
        ),
        "reversed input",
    )
    default_fp = _unwrap(default.fingerprint_content(), "default fp")
    assert default_fp == _unwrap(reversed_input.fingerprint_content(), "reversed fp")
    assert "order_significance" not in default.body()
    assert "display_ordinal" not in default.identity_legs()[0]
    opted = _unwrap(mint_confluence(legs, order_significance=True), "opt-in order")
    opted_fp = _unwrap(opted.fingerprint_content(), "opted fp")
    assert opted_fp != default_fp
    assert opted.body()["order_significance"] == "declared-order-significant"
    return default_fp != opted_fp


def reuse_across_bots_mints_no_new_confluence() -> bool:
    """Same content, two bots; one confluence fingerprint. A changed role mints another."""
    legs = [
        {"role": "level", "producer_binding": _pinned("zone")},
        {"role": "trigger", "producer_binding": _pinned("break")},
    ]
    first = _unwrap(mint_confluence(legs), "first mint")
    second = _unwrap(mint_confluence(list(reversed(legs))), "second mint")
    fp = _unwrap(first.fingerprint_content(), "fp")
    assert fp == _unwrap(second.fingerprint_content(), "fp-again")
    assert fp.value.startswith("fp1:sha256:")
    assert qml.__version__ not in first.identity_payload().values()
    registrar = _host_registrar()
    a = _unwrap(
        register_confluence(
            legs,
            registrar=registrar,
            writer=_writer("node-a"),
            sequence=0,
            created_at=_instant(),
        ),
        "sandbox-a",
    )
    b = _unwrap(
        register_confluence(
            legs,
            registrar=registrar,
            writer=_writer("node-b"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 1_000),
        ),
        "sandbox-b",
    )
    assert a.record.stable_id == b.record.stable_id
    changed = _unwrap(
        mint_confluence(
            [
                {"role": "filter", "producer_binding": _pinned("zone")},
                {"role": "trigger", "producer_binding": _pinned("break")},
            ]
        ),
        "changed role",
    )
    assert _unwrap(changed.fingerprint_content(), "changed fp") != fp
    return a.record.stable_id == b.record.stable_id


def refusals_and_conditions_live_in_logic() -> TypedRefusal:
    """Invalid role / missing cite; unresolvable producer or child; no condition grammar."""
    bad_role = mint_confluence([{"role": "feature", "producer_binding": _pinned("sma")}])
    assert isinstance(bad_role, TypedRefusal)
    assert bad_role.category.value == "invalid input"
    condition = mint_confluence(
        [{"role": "filter", "producer_binding": _pinned("sma"), "when": "close > sma"}]
    )
    assert isinstance(condition, TypedRefusal)
    assert condition.category.value == "invalid input"
    binding = _pinned("sma")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": binding}]),
        "resolvable",
    )
    found = resolve_confluence_at_layer1(confluence, (), producer_catalog=[binding])
    assert is_ok(found)
    missing = resolve_confluence_at_layer1(confluence, (), producer_catalog=())
    assert isinstance(missing, TypedRefusal)
    assert missing.category.value == "unavailable dependency"
    child_fp = _unwrap(fingerprint({"class": "missing-child"}), "missing child fp")
    parent = _unwrap(
        mint_confluence(
            [
                {
                    "role": "trigger",
                    "producer_binding": binding,
                    "confluence_ref": child_fp,
                }
            ]
        ),
        "parent with missing child",
    )
    missing_child = resolve_confluence_at_layer1(parent, (), producer_catalog=[binding])
    assert isinstance(missing_child, TypedRefusal)
    assert missing_child.category.value == "unavailable dependency"
    return missing


def main() -> None:
    print(f"roles in mixed confluence: {roles_and_one_or_more_legs()}")
    child = binding_and_or_child_cite()
    print(f"child confluence fingerprint: {child[:19]}...")
    print(
        f"order-significance changes fingerprint: "
        f"{fingerprint_ascending_default_and_opt_in_order()}"
    )
    print(f"two sandboxes reuse one confluence: {reuse_across_bots_mints_no_new_confluence()}")
    missing = refusals_and_conditions_live_in_logic()
    print(f"unresolvable producer at Layer 1: {missing.category.value}")
    print("confluence authoring ok")


if __name__ == "__main__":
    main()
