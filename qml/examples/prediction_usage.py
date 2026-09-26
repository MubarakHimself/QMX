"""Reference usage — prediction linter (Story 12.6).

Executable::

    python qml/examples/prediction_usage.py

Shows the things QL-8 / Story 12.6 pin down:

1. The prediction linter is a pure function over the CT-28 binding context. It
   runs statically on demand and at seat time — same checks, no I/O, no process,
   and no ``qmf-venue`` import. CT-18 is read as declared capability tokens the
   host projects from the binding.
2. The pinned check list (addable never redefined): (a) CT-33 footprint
   satisfies Book ``footprint_requirements``; (b) bot permitted EXIT kinds are
   a subset of the Book's; (c) the bot family resolves an ``exit_policy``
   entry (explicit or catch-all); (d) the stream set lies within the binding's
   declared CT-18 venue capabilities.
3. An entry-only bot against a Book with zero permitted exit kinds passes —
   ``entry`` is never gated. An unresolved family is a prediction-linter
   failure. A stream set that exceeds venue capabilities fails at bind time.
4. A not-yet-ruled ``footprint_requirement`` stays GAP-0048/0049: the interface
   is present, a blank still passes registration, and live binding is refused.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import AccountRole
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qmf.risk.admission_bar import Comparison, RuledThreshold
from qmf.risk.door import ExitLogicRef
from qmf.risk.exit_policy import ExitPolicy
from qmf.risk.footprint_requirements import (
    FootprintFieldKind,
    FootprintRequirement,
    FootprintRequirements,
)
from qmf.risk.grammar import NotYetRuled
from qmf.risk.migrations import THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS
from qml.conformance import PREDICTION_CHECKS, lint_prediction
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity

T = TypeVar("T")

_SOURCE = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_VENUE = frozenset({"trading", "time-interval"})


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _int_param() -> dict[str, object]:
    return {
        "name": "lookback",
        "type": "exact integer",
        "bounds": {"min": 1, "max": 200},
        "step": 1,
        "default": 20,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _declaration() -> BotDefinition:
    zone = _pinned("zone")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": zone}]), "confluence"
    )
    footprint = _unwrap(mint_footprint([_stream()], [_calendar()], [zone]), "footprint")
    family = _unwrap(mint_strategy_family("trend-follow"), "family")
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", _SOURCE), "logic")
    return _unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        ),
        "declaration",
    )


def _ref(module_id: str = "book.default.evidence_stop") -> ExitLogicRef:
    return _unwrap(ExitLogicRef.try_create(module_id, {"style": "structure"}), "exit ref")


def _zero_exit_policy() -> ExitPolicy:
    return _unwrap(
        ExitPolicy.try_create({"trend-follow": _ref()}, permitted_exit_intent_kinds=()),
        "exit policy",
    )


def _category(refused: object) -> str:
    assert isinstance(refused, TypedRefusal)
    return refused.category.value


def entry_only_against_zero_exit_book() -> bool:
    verdict = lint_prediction(
        _declaration(),
        exit_policy=_zero_exit_policy(),
        footprint_requirements=(),
        venue_capabilities=_VENUE,
        account_role=AccountRole.DEMO,
    )
    return is_ok(verdict)


def unresolved_family() -> str:
    empty = _unwrap(ExitPolicy.try_create({}, permitted_exit_intent_kinds=()), "empty policy")
    refused = lint_prediction(
        _declaration(),
        exit_policy=empty,
        footprint_requirements=(),
        venue_capabilities=_VENUE,
    )
    return _category(refused)


def stream_exceeds_venue() -> str:
    refused = lint_prediction(
        _declaration(),
        exit_policy=_zero_exit_policy(),
        footprint_requirements=(),
        venue_capabilities=frozenset({"tick"}),
    )
    assert isinstance(refused, TypedRefusal)
    assert refused.context["bind_time"] is True
    return refused.category.value


def blank_requirement_passes_registration_blocks_live() -> tuple[bool, str]:
    blank = _unwrap(NotYetRuled.try_create("GAP-0048"), "blank")
    req = _unwrap(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET,
            "stream_set",
            UnitKind.COUNT,
            Comparison.AT_LEAST,
            blank,
            0,
        ),
        "requirement",
    )
    reqs = _unwrap(FootprintRequirements.try_create([req]), "requirements")
    demo = lint_prediction(
        _declaration(),
        exit_policy=_zero_exit_policy(),
        footprint_requirements=reqs,
        venue_capabilities=_VENUE,
        account_role=AccountRole.DEMO,
    )
    live = lint_prediction(
        _declaration(),
        exit_policy=_zero_exit_policy(),
        footprint_requirements=reqs,
        venue_capabilities=_VENUE,
        account_role=AccountRole.LIVE,
    )
    assert is_ok(demo)
    assert demo.value.live_binding_blocked is True
    return True, _category(live)


def ruled_footprint_can_fail() -> str:
    bound = _unwrap(ExactRational.try_create(2, 1, UnitKind.COUNT), "bound")
    ruled = _unwrap(RuledThreshold.try_create(bound), "ruled")
    req = _unwrap(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET,
            "stream_set",
            UnitKind.COUNT,
            Comparison.AT_LEAST,
            ruled,
            0,
        ),
        "requirement",
    )
    reqs = _unwrap(FootprintRequirements.try_create([req]), "requirements")
    refused = lint_prediction(
        _declaration(),
        exit_policy=_zero_exit_policy(),
        footprint_requirements=reqs,
        venue_capabilities=_VENUE,
    )
    return _category(refused)


def main() -> None:
    print(f"prediction checks: {','.join(PREDICTION_CHECKS)}")
    print(f"threshold gaps: {','.join(THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS)}")
    print(f"entry-only vs zero-exit Book: {entry_only_against_zero_exit_book()}")
    print(f"unresolved family: {unresolved_family()}")
    print(f"stream set exceeds venue: {stream_exceeds_venue()}")
    passed, live = blank_requirement_passes_registration_blocks_live()
    print(f"blank passes registration: {passed}")
    print(f"blank blocks live: {live}")
    print(f"ruled footprint miss: {ruled_footprint_can_fail()}")
    print("prediction linter ok")


if __name__ == "__main__":
    main()
