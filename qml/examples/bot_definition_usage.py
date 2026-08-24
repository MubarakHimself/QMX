"""Reference usage — CT-33 Bot definition kind (Story 11.6).

Executable::

    python qml/examples/bot_definition_usage.py

Shows the things QL-3 / Story 11.6 pin down:

1. Bot ``fp1`` is the six semantic-content groups plus the contract format
   version and at-birth refs. The AD-16 header's writer, sequence, stable id,
   and created-at are excluded — the stable id is derived from the fingerprint.
2. Each declared parameter carries a type in {exact integer, exact rational,
   categorical, boolean}, bounds, step, a mandatory default, an optional
   hard-constraint filter, and an AD-40 unit-kind. Defaults together are the
   canonical assignment, not a separate field.
3. Zero or more-than-one strategy-family id is invalid input. The confluence
   set is one-or-more CT-34 fingerprints, ordered by child fingerprint
   ascending, with display-only ordinals.
4. Permitted intents are a subset of close_full | tighten_protective_stop and
   may be empty. The declaration carries no sizing, no venue command, and no
   exit-logic field.
5. Versioning is AD-30's branches-from graph (multiple heads legal) with a
   separate dated current pointer. A changed default mints a new Bot;
   re-binding never does.
6. qml returns fingerprintable content only; the host composition root stamps
   WriterId, sequence, and created-at. The writer unit is (machine, authoring
   role, kind).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qmf.registry import KindRegistry, Registrar
from qml.declaration import (
    KIND_BOT_DEFINITION,
    BotVersionGraph,
    install_bot_definition_kind,
    mint_bot_definition,
    mint_confluence,
    promote_tuned_assignment,
    register_bot_definition,
)
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity

import qml

T = TypeVar("T")

_CREATED_NS = 1_700_000_000_000_000_000
_SOURCE = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, instant):\n    return ()\n",
}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _writer(machine: str) -> WriterId:
    return _unwrap(
        WriterId.try_create(machine, "authoring", KIND_BOT_DEFINITION, "boot-1"),
        "writer",
    )


def _instant(ns: int = _CREATED_NS) -> Instant:
    return _unwrap(Instant.try_create(ns), "created-at")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _payload() -> dict[str, object]:
    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": _pinned("zone")}]),
        "confluence",
    )
    footprint = _unwrap(
        mint_footprint(
            [
                {
                    "instrument_role": "primary",
                    "bar_specs": [{"kind": "time-interval", "seconds": 60}],
                    "stream_role": "trading",
                }
            ],
            [calendar],
            [_pinned("sma")],
        ),
        "footprint",
    )
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", _SOURCE), "logic")
    return {
        "strategy_family_id": "trend-follow",
        "confluence_set": [confluence],
        "parameter_space": [
            {
                "name": "lookback",
                "type": "exact integer",
                "bounds": {"min": 1, "max": 200},
                "step": 1,
                "default": 20,
                "unit_kind": UnitKind.COUNT,
                "ui": "ui-editable",
            }
        ],
        "footprint": footprint,
        "permitted_exit_intents": (),
        "logic_reference": logic,
    }


def identity_excludes_ad16_header() -> bool:
    """Writer / sequence / stable id / created-at never enter Bot fp1."""
    authored = _unwrap(mint_bot_definition(_payload()), "bot")
    payload = authored.identity_payload()
    assert payload["kind"] == KIND_BOT_DEFINITION
    body = authored.body()
    assert set(body) == {
        "strategy_family_id",
        "confluence_set",
        "parameter_space",
        "footprint",
        "permitted_exit_intents",
        "logic_reference",
    }
    assert "writer" not in payload
    assert "sequence" not in payload
    assert "stable_id" not in payload
    assert "created_at" not in payload
    assert qml.__version__ not in payload.values()
    fp = _unwrap(authored.fingerprint_content(), "fp")
    assert fp.value.startswith("fp1:sha256:")
    return True


def canonical_assignment_is_derived() -> bool:
    """Defaults together are the canonical assignment, not a declared field."""
    authored = _unwrap(mint_bot_definition(_payload()), "bot")
    assert dict(authored.canonical_assignment()) == {"lookback": 20}
    assert "canonical_assignment" not in authored.body()
    stuffed = mint_bot_definition({**_payload(), "canonical_assignment": {"lookback": 20}})
    assert isinstance(stuffed, TypedRefusal)
    assert stuffed.category.value == "invalid input"
    missing_kind = mint_bot_definition(
        {
            **_payload(),
            "parameter_space": [
                {
                    "name": "lookback",
                    "type": "exact integer",
                    "bounds": {"min": 1, "max": 10},
                    "step": 1,
                    "default": 2,
                    "ui": "ui-editable",
                }
            ],
        }
    )
    assert isinstance(missing_kind, TypedRefusal)
    assert missing_kind.category.value == "invalid input"
    return True


def cardinality_and_confluence_order() -> str:
    """Exactly one family; confluence set one-or-more, fingerprint-ascending."""
    zero = mint_bot_definition({**_payload(), "strategy_family_id": []})
    assert isinstance(zero, TypedRefusal)
    assert zero.category.value == "invalid input"
    two = mint_bot_definition({**_payload(), "strategy_family_id": ["trend-follow", "mean-revert"]})
    assert isinstance(two, TypedRefusal)
    empty_conf = mint_bot_definition({**_payload(), "confluence_set": []})
    assert isinstance(empty_conf, TypedRefusal)
    return zero.category.value


def no_sizing_or_exit_logic() -> bool:
    """Entry-only is legal; exit_logic / sizing / venue are refused."""
    entry_only = _unwrap(mint_bot_definition(_payload()), "entry-only")
    assert entry_only.permitted_exit_intents == ()
    listed_entry = mint_bot_definition({**_payload(), "permitted_exit_intents": ["entry"]})
    assert isinstance(listed_entry, TypedRefusal)
    exit_logic = mint_bot_definition({**_payload(), "exit_logic": "book-owned"})
    assert isinstance(exit_logic, TypedRefusal)
    return True


def versioning_multiple_heads_and_changed_default() -> bool:
    """branches-from allows multiple heads; a changed default mints a new Bot."""
    root = _unwrap(mint_bot_definition(_payload()), "root")
    tuned = _unwrap(promote_tuned_assignment(root, {"lookback": 14}), "tuned")
    root_fp = _unwrap(root.fingerprint_content(), "root fp")
    tuned_fp = _unwrap(tuned.fingerprint_content(), "tuned fp")
    assert tuned_fp != root_fp
    graph = BotVersionGraph()
    _unwrap(graph.append_version(root_fp), "append root")
    _unwrap(graph.append_version(tuned_fp, branches_from=root_fp), "append tuned")
    sibling = _unwrap(promote_tuned_assignment(root, {"lookback": 30}), "sibling")
    sibling_fp = _unwrap(sibling.fingerprint_content(), "sibling fp")
    _unwrap(graph.append_version(sibling_fp, branches_from=root_fp), "append sibling")
    assert set(graph.heads()) == {tuned_fp, sibling_fp}
    _unwrap(graph.set_current(tuned_fp, _instant()), "current")
    assert graph.current() == tuned_fp
    seat = mint_bot_definition({**_payload(), "seat": "book-1"})
    assert isinstance(seat, TypedRefusal)
    return True


def two_sandboxes_one_fp1() -> bool:
    """Host stamps occurrence facts; identical content deduplicates."""
    registry = KindRegistry()
    _unwrap(install_bot_definition_kind(registry), "install bot-definition kind")
    registrar = Registrar(registry)
    payload = _payload()
    a = _unwrap(
        register_bot_definition(
            payload,
            registrar=registrar,
            writer=_writer("node-a"),
            sequence=0,
            created_at=_instant(),
        ),
        "sandbox-a",
    )
    b = _unwrap(
        register_bot_definition(
            payload,
            registrar=registrar,
            writer=_writer("node-b"),
            sequence=0,
            created_at=_instant(_CREATED_NS + 1_000),
        ),
        "sandbox-b",
    )
    assert a.record.stable_id == b.record.stable_id
    assert a.outcome.value == "stored"
    assert b.outcome.value == "idempotent"
    minted = _unwrap(mint_bot_definition(payload), "content")
    assert type(minted).__name__ == "BotDefinition"
    assert "writer" not in minted.identity_payload()
    return a.record.stable_id == b.record.stable_id


def main() -> None:
    print(f"identity excludes AD-16 header: {identity_excludes_ad16_header()}")
    print(f"canonical assignment is derived: {canonical_assignment_is_derived()}")
    print(f"zero family ids is invalid input: {cardinality_and_confluence_order()}")
    print(f"entry-only bot is legal: {no_sizing_or_exit_logic()}")
    print(f"changed default mints new Bot: {versioning_multiple_heads_and_changed_default()}")
    print(f"two sandboxes one Bot fp1: {two_sandboxes_one_fp1()}")
    print("bot definition authoring ok")


if __name__ == "__main__":
    main()
