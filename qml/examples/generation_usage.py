"""Reference usage — generation write-ownership is QML/host (Story 38.1).

Executable::

    python qml/examples/generation_usage.py

Shows the things Story 38.1 pins down:

1. QMB optimize/sweep varies declared CT-33 parameters and cites the same bot
   ``fp1``. That act is search, not generation.
2. Generation authors new CT-33/CT-34 content and/or logic-source bytes via QML.
3. The QML/host composition root mints the CT-06 envelope. QMB does not author.
4. A generator module inside ``qmb/`` is refused. The ``.qml`` DSL and SQ
   RandomCondition-as-schema are refused. GAP-0085 nouns and GAP-0063 stay gaps.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal
from qmf.registry import KindRegistry, Registrar
from qml.conformance import evaluate_ticket
from qml.footprint import ProducerBinding, mint_footprint
from qml.generation import (
    ACT_GENERATION,
    ACT_SEARCH,
    QMB_AUTHORS_CANDIDATES,
    QMB_RUNS_CANDIDATES,
    author_new_structure,
    classify_parameter_search,
    refuse_qml_dsl,
    refuse_random_condition_schema,
)
from qml.host import install_bot_domain_kinds, mint_generation_envelope

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


def _instant() -> Instant:
    return _unwrap(Instant.try_create(_CREATED_NS), "created-at")


def _writer(kind: str) -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "authoring", kind, "boot-1"), "writer")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def main() -> None:
    print(f"qml {qml.__version__}")
    bot_fp = _unwrap(fingerprint({"class": "bot", "id": "same"}), "bot fp")
    search = classify_parameter_search(bot_fp1=bot_fp, trial_bot_fp1s=(bot_fp, bot_fp))
    assert is_ok(search)
    assert search.value.value == ACT_SEARCH
    print(f"parameter variation is {ACT_SEARCH}, not {ACT_GENERATION}")

    calendar = _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")
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
    authored = _unwrap(
        author_new_structure(
            strategy_family_id="trend-follow",
            confluence_legs=[{"role": "level", "producer_binding": _pinned("zone")}],
            parameter_space=[
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
            footprint=footprint,
            logic_source=_SOURCE,
        ),
        "author",
    )
    assert authored.act.value == ACT_GENERATION
    assert QMB_AUTHORS_CANDIDATES is False
    assert QMB_RUNS_CANDIDATES is True
    registry = KindRegistry()
    _unwrap(install_bot_domain_kinds(registry), "install kinds")
    minted = _unwrap(
        mint_generation_envelope(
            authored,
            registrar=Registrar(registry),
            created_at=_instant(),
            ticket=_unwrap(
                evaluate_ticket(layer1_passed=True, layer2_passed=True),
                "ticket",
            ),
            bot_writer=_writer("bot-definition"),
            confluence_writer=_writer("confluence"),
        ),
        "host mint",
    )
    assert minted.host_mints_envelope is True
    assert minted.qmb_authors is False
    print("qml authors; host mints CT-06; qmb does not author")

    assert is_refusal(refuse_qml_dsl(".qml"))
    assert is_refusal(refuse_random_condition_schema({"slots": []}))
    print("dsl and RandomCondition schema refused")
    print("generation ownership ok")


if __name__ == "__main__":
    main()
