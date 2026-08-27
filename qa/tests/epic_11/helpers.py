"""Shared, requirements-anchored builders for the Epic 11 (qml authoring) audit.

Every builder here constructs a *valid* CT-33 / CT-34 / footprint / logic /
family artifact so the tests can vary exactly one thing and observe the effect.
No literal fingerprint ever appears: identity is recomputed through qmf-core's
canonical fp1. No error prose is asserted: refusals are matched on their CT-04
category value.

These builders are owned by the TEST; the composition-root sink (a real
``Registrar``, or a recording subclass) is injected by the test, never a
cross-package import edge from qml.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import CalendarIdentity, Instant, WriterId
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok

from qml.footprint import ProducerBinding, mint_footprint, mint_producer_template
from qml.declaration import mint_confluence

T = TypeVar("T")

CREATED_NS = 1_700_000_000_000_000_000

# Four CT-04 categories qml's authoring doors are permitted to emit (CT-33/CT-34
# enums.refusal). The other three of the seven-member register — stale evidence,
# transient venue failure, storage failure — must never appear on an authoring path.
QML_AUTHORING_CATEGORIES = frozenset(
    {"invalid input", "unsupported capability", "unavailable dependency", "policy rejection"}
)
SEVEN_REGISTER = frozenset(
    {
        "invalid input",
        "unsupported capability",
        "unavailable dependency",
        "stale evidence",
        "policy rejection",
        "transient venue failure",
        "storage failure",
    }
)
OFF_AUTHORING_CATEGORIES = SEVEN_REGISTER - QML_AUTHORING_CATEGORIES


def unwrap(result: Result[T], what: str = "value") -> T:
    """Assert a construction succeeds and return the value (fixture-build only)."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got refusal: {result!r}")


def category_of(result: object) -> str:
    """The CT-04 category string of a refusal (assert it IS a refusal first)."""
    assert isinstance(result, TypedRefusal), f"expected a TypedRefusal, got {result!r}"
    return result.category.value


def exact(n: int, den: int = 1, unit: UnitKind = UnitKind.COUNT) -> ExactRational:
    return unwrap(ExactRational.try_create(n, den, unit), "exact-rational")


def calendar() -> CalendarIdentity:
    return unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")


def writer(machine: str, kind: str) -> WriterId:
    return unwrap(WriterId.try_create(machine, "authoring", kind, "boot-1"), "writer")


def instant(ns: int = CREATED_NS) -> Instant:
    return unwrap(Instant.try_create(ns), "instant")


def pinned(tag: str) -> ProducerBinding:
    """A producer binding pinned to a content-addressed fingerprint (qmf-core fp1)."""
    fp = unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return unwrap(ProducerBinding.try_create(fp), "pinned binding")


def pinned_fp(tag: str) -> Fingerprint:
    return unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")


def template_body(**overrides: object) -> dict[str, object]:
    """A complete CT-16 producer template minus only the space-bound value ``period``."""
    body: dict[str, object] = {
        "formula_id": "sma",
        "contract_format_version": 1,
        "inputs": [
            {
                "name": "close",
                "source": {"kind": "instrument", "venue": "venue-ic", "symbol": "EURUSD"},
                "bar_spec": {"kind": "time-interval", "seconds": 60},
                "channel_kind": "exact-price",
                "quote_side": "mid",
            }
        ],
        "calendar_requirements": [calendar()],
        "alignment_policy": "as-of",
        "missing_value_policy": "mark-gap",
        "warm_up": 20,
        "output_schema": [
            {
                "name": "sma",
                "channel_kind": "float-analytic",
                "arity": "scalar-per-sample",
                "index_offset": 0,
            }
        ],
        "supported_modes": ["batch", "streaming"],
        "arithmetic_reference_configuration": {
            "c_library": "ta-lib-c@sha256:aaaa",
            "python_wrapper": "ta-lib-py@sha256:bbbb",
            "reference_configuration": {"compatibility_mode": "classic"},
        },
        "space_bound": {"period": "sma_period"},
    }
    body.update(overrides)
    return body


def stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def logic_source() -> dict[str, str]:
    return {
        "research_bot/__init__.py": "",
        "research_bot/bot.py": "def on_instant(self, instant):\n    return ()\n",
    }


def sandbox_source(stamp: str) -> dict[str, object]:
    """The same logic source plus non-reproducible wheel/build bytes (must be stripped)."""
    return {
        **logic_source(),
        "research_bot-1.0.0-py3-none-any.whl": f"wheel-{stamp}".encode(),
        "research_bot-1.0.0.dist-info/WHEEL": f"Wheel-Version: 1.0\nBuild: {stamp}\n",
        "research_bot-1.0.0.dist-info/RECORD": f"research_bot/bot.py,{stamp}\n",
        "research_bot/__pycache__/bot.cpython-314.pyc": stamp.encode() + b"\x00\x01",
    }


def a_confluence(tag: str = "zone", role: str = "level") -> object:
    """A minimal one-leg CT-34 confluence content object."""
    return unwrap(mint_confluence([{"role": role, "producer_binding": pinned(tag)}]), "confluence")


def bot_payload(**overrides: object) -> dict[str, object]:
    """A complete six-group CT-33 Bot definition payload; override any single group."""
    from qml.logic import mint_logic_identity

    footprint = unwrap(
        mint_footprint([stream()], [calendar()], [pinned("sma")]),
        "footprint",
    )
    logic = unwrap(mint_logic_identity("research-bot", "1.0.0", logic_source()), "logic")
    payload: dict[str, object] = {
        "strategy_family_id": "trend-follow",
        "confluence_set": [a_confluence()],
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
    payload.update(overrides)
    return payload
