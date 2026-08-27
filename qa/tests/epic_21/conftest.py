"""Shared fixtures and builders for the Epic 21 (qmb-optimization) independent QA suite.

Every assertion in this suite states what a *requirement* of Epic 21 demands (the
QMB spine B-8/B-4/B-6/B-7/B-10/B-14/B-15, the CT-* contracts, epics.md ACs), never
what the source happens to do. A failing test is a FINDING; source is read-only
evidence and is never edited to make a test pass, nor is an assertion weakened.

Builders below construct only shape-faithful, exact-integer inputs — Money is an
exact scaled integer, ledger measures carry an fp1-canonical num/den quantity, and
the registry universe is built through the same public construction API the shipped
usage examples use. No product mock market data, no default strategies.

Effects are observed through the returned public values (winner sets, batches,
reports, refusals) — never a private helper and never a self-declared module flag.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from fractions import Fraction
from pathlib import Path
from typing import TypeVar

from qmf.core.chrono import Duration, Instant, WriterId
from qmf.core.exact import ExactRational, Money, UnitKind
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)
from qmf.registry import RegistrationRecord

from qmb.ledger.line import ROLE_ABORTED, ROLE_TRIAL, LedgerLine
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort

T = TypeVar("T")

WORKTREE_ROOT = Path(__file__).resolve().parents[3]
_UNIVERSE_NS = 1_700_000_000_000_000_000


def unwrap(result: Result[T], what: str = "value") -> T:
    """Unwrap an ``Ok`` or fail loudly — used only to build *inputs*, never to assert."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"FIXTURE could not construct {what}: {result!r}")


# --- fingerprints & money ----------------------------------------------------


def fp(seed: object) -> Fingerprint:
    """A distinct, valid fp1 fingerprint derived from ``seed`` (never restated bytes)."""
    return unwrap(fingerprint({"seed": repr(seed)}), f"fp@{seed!r}")


def usd(minor: int, currency: str = "USD", scale: int = 2) -> Money:
    """Exact Money at scale 2 (minor units); never a float."""
    return Money(value=minor, currency=currency, scale=scale)


# --- ledger measures (fp1-canonical, exact) ----------------------------------


def money_measure(identity: str, minor: int, currency: str = "USD") -> dict[str, object]:
    """A performance-measure carrying an exact Money quantity of ``currency``."""
    return {
        "class": "performance-measure",
        "measure_identity": identity,
        "unit_kind": "money(currency)",
        "quantity": usd(minor, currency).fp1_identity(),
    }


def count_measure(identity: str, n: int) -> dict[str, object]:
    """A performance-measure carrying an exact count quantity."""
    return {
        "class": "performance-measure",
        "measure_identity": identity,
        "unit_kind": "count",
        "quantity": {"num": n, "den": 1, "unit_kind": "count"},
    }


def ratio_measure(identity: str, num: int, den: int) -> dict[str, object]:
    """A performance-measure carrying an exact dimensionless-ratio quantity."""
    return {
        "class": "performance-measure",
        "measure_identity": identity,
        "unit_kind": "dimensionless-ratio",
        "quantity": {"num": num, "den": den, "unit_kind": "dimensionless-ratio"},
    }


def undefined_measure(identity: str) -> dict[str, object]:
    """An undefined-measure slot a reader tells apart from a zero (AD-11)."""
    return {
        "class": "undefined-measure",
        "measure_identity": identity,
        "refusal": {"category": "invalid input", "field": identity},
    }


# --- ledger lines ------------------------------------------------------------


def trial_line(
    seed: object,
    measures: Sequence[Mapping[str, object]],
    *,
    world: World = World.REPLAY,
    role: str = ROLE_TRIAL,
    ct32: bool = True,
) -> LedgerLine:
    """A completed ``role = trial`` ledger line carrying the given measures.

    ``ct32`` set means a completed run (a CT-32 fingerprint present); the winner-set
    and sensitivity folds read only completed trial lines.
    """
    return LedgerLine(
        run_id=fp(("run", seed)),
        role=role,
        world=world,
        result_label={"class": "result-label", "run": repr(seed)},
        book_bar_fp1=fp(("bar", seed)),
        measures=tuple(measures),
        ct32_fingerprint=fp(("ct32", seed)) if ct32 else None,
        refusal=None,
    )


def aborted_line(seed: object, *, world: World = World.REPLAY) -> LedgerLine:
    """An aborted ledger line for a spawned-but-incomplete run (never silently absent)."""
    return LedgerLine(
        run_id=fp(("run", seed)),
        role=ROLE_ABORTED,
        world=world,
        result_label={"class": "result-label", "run": repr(seed)},
        book_bar_fp1=fp(("bar", seed)),
        measures=(),
        ct32_fingerprint=None,
        refusal={"category": "policy rejection", "field": "terminal", "reason": "operator terminate"},
    )


def run_id_of(seed: object) -> str:
    """The fp1 string of a trial's run id — the ledger-view join key."""
    return fp(("run", seed)).value


# --- parameter-space declarations --------------------------------------------


def int_param(
    name: str,
    *,
    lo: int = 0,
    hi: int = 100,
    step: int = 1,
    default: int = 10,
    unit_kind: str = "count",
    ui: str = "ui-editable",
) -> dict[str, object]:
    """A well-formed exact-integer parameter declaration (CT-33 schema shape)."""
    return {
        "name": name,
        "type": "exact integer",
        "unit_kind": unit_kind,
        "min": lo,
        "max": hi,
        "step": step,
        "default": default,
        "ui": ui,
    }


def money_param(
    name: str,
    *,
    lo: object = 100,
    hi: object = 1000,
    step: object = 100,
    default: object = 500,
    type_: str = "exact integer",
) -> dict[str, object]:
    """A money parameter declaration (unit-kind money(currency))."""
    return {
        "name": name,
        "type": type_,
        "unit_kind": UnitKind.MONEY.value,
        "min": lo,
        "max": hi,
        "step": step,
        "default": default,
        "ui": "ui-editable",
    }


def categorical_param(
    name: str,
    options: Sequence[str],
    default: object,
) -> dict[str, object]:
    """A categorical parameter declaration."""
    return {
        "name": name,
        "type": "categorical",
        "unit_kind": "dimensionless-ratio",
        "options": list(options),
        "default": default,
        "ui": "ui-editable",
    }


def boolean_param(name: str, default: bool = True) -> dict[str, object]:
    """A boolean parameter declaration."""
    return {
        "name": name,
        "type": "boolean",
        "unit_kind": "dimensionless-ratio",
        "default": default,
        "ui": "ui-editable",
    }


def rational_param(
    name: str,
    *,
    lo: tuple[int, int] = (0, 1),
    hi: tuple[int, int] = (1, 1),
    step: tuple[int, int] = (1, 10),
    default: tuple[int, int] = (1, 2),
    unit: UnitKind = UnitKind.DIMENSIONLESS_RATIO,
) -> dict[str, object]:
    """A well-formed exact-rational parameter declaration."""
    er = lambda pair: unwrap(ExactRational.try_create(pair[0], pair[1], unit), f"er{pair}")
    return {
        "name": name,
        "type": "exact rational",
        "unit_kind": unit.value,
        "min": er(lo),
        "max": er(hi),
        "step": er(step),
        "default": er(default),
        "ui": "ui-editable",
    }


# --- registry universe (for admit_study, R22) --------------------------------


def _instant(ns: int = _UNIVERSE_NS) -> Instant:
    return unwrap(Instant.try_create(ns), "instant")


def _writer(stream: str) -> WriterId:
    return unwrap(WriterId.try_create("node-a", "authoring", stream, "boot-1"), "writer")


def bot_universe(alias: str = "mean-reversion") -> tuple[RegistryReadPort, RegistrationRecord]:
    """A minimal live registry universe: one bot record, an as-of set, a hub, a port.

    Returns the live (unfrozen) :class:`RegistryReadPort` an admission freezes and the
    bot :class:`RegistrationRecord` (its ``stable_id`` is the explicit bot fingerprint).
    """
    bot = unwrap(
        RegistrationRecord.try_create(
            "bot-definition",
            1,
            [],
            {"class": "bot-definition", "alias": alias},
            _writer("bot-definition"),
            0,
            _instant(),
        ),
        "bot record",
    )
    as_of = unwrap(
        AsOfSet.try_create(
            _instant(),
            records=(bot,),
            pointers=(unwrap(DatedPointer.try_create(alias, bot.stable_id, _instant()), "pointer"),),
        ),
        "as-of set",
    )
    hub = unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = unwrap(
        RegistryReadPort.try_create(hub, stale_evidence_severity="workspace-declared"),
        "registry-read port",
    )
    return port, bot


# --- CT-04 refusal harness ---------------------------------------------------


def assert_ct04_refusal(
    result: object,
    expected: RefusalCategory,
    *,
    what: str = "operation",
) -> TypedRefusal:
    """Assert ``result`` is a RETURNED CT-04 typed refusal of ``expected`` category.

    Checks the four CT-04 invariants for a refusal value: it is a ``TypedRefusal``
    RETURNED (reaching here at all proves it was not raised across the boundary), its
    ``category`` is one of the seven and the expected one, its ``retryability`` is a
    valid enum member, and its ``context`` is present and non-null. No assertion ever
    parses the refusal's prose.
    """
    assert is_refusal(result), f"{what}: expected a RETURNED CT-04 refusal, got {result!r}"
    refusal = result
    assert isinstance(refusal, TypedRefusal)
    assert isinstance(refusal.category, RefusalCategory), f"{what}: category not a CT-04 member"
    assert refusal.category is expected, (
        f"{what}: expected category {expected.value!r}, got {refusal.category.value!r}"
    )
    assert isinstance(refusal.retryability, Retryability), f"{what}: retryability missing/invalid"
    assert isinstance(refusal.context, Mapping), f"{what}: context absent or not a mapping"
    assert refusal.context is not None
    return refusal


# --- identity scanners (float-ban & payload observation) ---------------------


def find_floats(value: object, path: str = "$") -> list[str]:
    """Every path at which a raw Python ``float`` appears inside identity content.

    ``bool`` is not a float; ``int``/``ExactRational``-num/den are exact. An empty
    list means the whole identity tree is float-free (the money-path / return-space
    float ban honoured).
    """
    hits: list[str] = []
    if isinstance(value, bool):
        return hits
    if isinstance(value, float):
        return [f"{path}={value!r}"]
    if isinstance(value, Mapping):
        for key, item in value.items():
            hits.extend(find_floats(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            hits.extend(find_floats(item, f"{path}[{i}]"))
    return hits


def find_bytes(value: object, path: str = "$") -> list[str]:
    """Every path at which a ``bytes``/``bytearray`` blob appears (an image payload)."""
    hits: list[str] = []
    if isinstance(value, (bytes, bytearray)):
        return [f"{path} (bytes)"]
    if isinstance(value, Mapping):
        for key, item in value.items():
            hits.extend(find_bytes(item, f"{path}.{key}"))
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            hits.extend(find_bytes(item, f"{path}[{i}]"))
    return hits


def collect_string_values(value: object) -> list[str]:
    """Every string VALUE appearing anywhere in identity content (not keys)."""
    out: list[str] = []
    if isinstance(value, Mapping):
        for item in value.values():
            out.extend(collect_string_values(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            out.extend(collect_string_values(item))
    elif isinstance(value, str):
        out.append(value)
    return out


__all__ = [
    "Fraction",
    "Ok",
    "RefusalCategory",
    "Retryability",
    "TypedRefusal",
    "UnitKind",
    "WORKTREE_ROOT",
    "World",
    "aborted_line",
    "assert_ct04_refusal",
    "boolean_param",
    "bot_universe",
    "categorical_param",
    "collect_string_values",
    "count_measure",
    "find_bytes",
    "find_floats",
    "fp",
    "int_param",
    "is_ok",
    "is_refusal",
    "money_measure",
    "money_param",
    "rational_param",
    "ratio_measure",
    "run_id_of",
    "trial_line",
    "undefined_measure",
    "unwrap",
    "usd",
    "Duration",
    "ExactRational",
    "Money",
]
