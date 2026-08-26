"""Sweep axis declaration, Cartesian expansion, and pre-flight run count (B-12).

A sweep is declared as axes — ``instruments[]``, ``timeframes[]`` (a ``BarSpec``
list), and ``parameters{name: values[]}`` — over a bot/Book/BMS context. The one
pure library function :func:`expand_sweep` produces the full Cartesian product of
the axes in a deterministic declaration-order enumeration: one :class:`SweepRunSpec`
per combination, each an isolated run of the same never-forked run loop with
different variables — the batch merges nothing (DEC-0169, spec R9).

:func:`preflight_run_count` reports the exact total (the product of the axis
lengths) before anything executes: it is a **pure inspection** — it spawns no
process, writes no ledger line, and admits no batch (B-4). A single run is the
same object at unit scale: a ``1x1x1`` declaration expands to exactly one run spec
(spec R13).

Every axis is non-empty by construction — a zero-length instrument, ``BarSpec``,
or parameter-value list is a typed ``invalid input`` refusal naming the empty
axis, never a silent zero-combo batch (AD-11). A parameter value is carried into
its combination verbatim when it is an exact integer, a categorical token, or a
boolean; a money or rational value crosses a named AD-7/AD-22 conversion (declared
rounding mode + target scale) before it enters the run spec, so a binary float
never appears in a run spec's identity content (B-8, AR-15, FR-001).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import product
from types import MappingProxyType
from typing import Final, cast

from qmf.core.exact import ExactRational, Money
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid
from qmb.runloop.bars import DeclaredBarSpec
from qmb.runloop.loop import STREAM_ROLE_TRADING, StreamSet

__all__ = [
    "CONVERSION_KINDS",
    "PREFLIGHT_ADMITS_BATCH",
    "PREFLIGHT_IS_PURE_INSPECTION",
    "PREFLIGHT_SPAWNS_PROCESS",
    "PREFLIGHT_WRITES_LEDGER_LINE",
    "SWEEP_AXES",
    "SWEEP_DECLARATION_CLASS",
    "SWEEP_FORMAT_VERSION",
    "SWEEP_RUN_SPEC_CLASS",
    "VALUE_KIND_BOOLEAN",
    "VALUE_KIND_CATEGORICAL",
    "VALUE_KIND_EXACT_INTEGER",
    "VALUE_KIND_MONEY",
    "VALUE_KIND_RATIONAL",
    "SweepDeclaration",
    "SweepRunSpec",
    "expand_sweep",
    "preflight_run_count",
    "sweep_axes_identity",
]

SWEEP_DECLARATION_CLASS: Final[str] = "qmb-sweep-declaration"
SWEEP_RUN_SPEC_CLASS: Final[str] = "qmb-sweep-run-spec"
SWEEP_FORMAT_VERSION: Final[int] = 1

# Declaration-order axes; the enumeration varies instruments slowest and the
# last-declared parameter fastest (spec R9, B-12).
SWEEP_AXES: Final[tuple[str, ...]] = ("instruments", "timeframes", "parameters")

# The pre-flight run count is a pure inspection (B-4): it never touches the
# impure composition root.
PREFLIGHT_SPAWNS_PROCESS: Final[bool] = False
PREFLIGHT_WRITES_LEDGER_LINE: Final[bool] = False
PREFLIGHT_ADMITS_BATCH: Final[bool] = False
PREFLIGHT_IS_PURE_INSPECTION: Final[bool] = True

VALUE_KIND_EXACT_INTEGER: Final[str] = "exact-integer"
VALUE_KIND_CATEGORICAL: Final[str] = "categorical"
VALUE_KIND_BOOLEAN: Final[str] = "boolean"
VALUE_KIND_MONEY: Final[str] = "money"
VALUE_KIND_RATIONAL: Final[str] = "rational"

# A conversion mapping names one of these; the crossing states its rounding mode
# and target scale (AD-7/AD-22).
CONVERSION_KINDS: Final[frozenset[str]] = frozenset({VALUE_KIND_MONEY, VALUE_KIND_RATIONAL})

_STREAM_ID_KEY: Final[str] = "stream_id"
_INSTRUMENT_ID_KEY: Final[str] = "instrument_id"
_ROLE_KEY: Final[str] = "role"
_BOT_KEY: Final[str] = "bot"
_BOOK_KEY: Final[str] = "book"
_BMS_KEY: Final[str] = "bms"
_STREAM_SET_KEY: Final[str] = "stream_set"
_BAR_SPECS_KEY: Final[str] = "bar_specs"


def sweep_axes_identity() -> dict[str, object]:
    """Identity-bearing sweep-axis fields. Package SemVer is omitted."""
    return {
        "axes": SWEEP_AXES,
        "declaration_class": SWEEP_DECLARATION_CLASS,
        "format_version": SWEEP_FORMAT_VERSION,
        "preflight_admits_batch": PREFLIGHT_ADMITS_BATCH,
        "preflight_is_pure_inspection": PREFLIGHT_IS_PURE_INSPECTION,
        "preflight_spawns_process": PREFLIGHT_SPAWNS_PROCESS,
        "preflight_writes_ledger_line": PREFLIGHT_WRITES_LEDGER_LINE,
        "run_spec_class": SWEEP_RUN_SPEC_CLASS,
    }


@dataclass(frozen=True, slots=True)
class SweepRunSpec:
    """One combination of the Cartesian product — one isolated run's spec (B-12).

    ``instrument`` and ``timeframe`` fix this run's single stream and its
    ``BarSpec``; ``parameters`` binds one value per swept parameter, each already
    an exact form (an integer, a categorical token, a boolean, or a converted
    :class:`Money` / :class:`ExactRational`). A ``1x1x1`` sweep yields exactly one
    of these — the same object at unit scale (spec R13).
    """

    bot: str
    book: str
    bms: str
    instrument: str
    timeframe: DeclaredBarSpec
    parameters: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Values are exact; a binary float never appears."""
        return {
            "bms": self.bms,
            "book": self.book,
            "bot": self.bot,
            "class": SWEEP_RUN_SPEC_CLASS,
            "format_version": SWEEP_FORMAT_VERSION,
            "instrument": self.instrument,
            "parameter_order": list(self.parameters),
            "parameters": {name: _value_identity(value) for name, value in self.parameters.items()},
            "timeframe": self.timeframe.fp1_identity(),
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The run spec's ``fp1``, computed only by the single qmf-core seam."""
        return fingerprint(self.fp1_identity())

    def stream_set(self) -> Result[StreamSet]:
        """The single-stream :class:`StreamSet` this combination declares (B-12)."""
        return StreamSet.try_create(
            [
                {
                    _STREAM_ID_KEY: self.instrument,
                    _INSTRUMENT_ID_KEY: self.instrument,
                    _ROLE_KEY: STREAM_ROLE_TRADING,
                }
            ]
        )

    def run_spec_layer(self) -> dict[str, object]:
        """The B-3 run-spec (bot) layer for this combination.

        Fed to ``qmb.config.compile_run_config`` exactly as a single run's
        run spec is — a run and a sweep are the same object at different scale
        (spec R13). Money/rational values ride as exact CT-01 objects the
        compiler carries verbatim.
        """
        layer: dict[str, object] = {
            _BOT_KEY: self.bot,
            _STREAM_SET_KEY: [
                {
                    _STREAM_ID_KEY: self.instrument,
                    _INSTRUMENT_ID_KEY: self.instrument,
                    _ROLE_KEY: STREAM_ROLE_TRADING,
                }
            ],
            _BAR_SPECS_KEY: [
                {
                    _STREAM_ID_KEY: self.instrument,
                    _BAR_SPECS_KEY: [self.timeframe.fp1_identity()],
                }
            ],
        }
        for name, value in self.parameters.items():
            layer[name] = value
        return layer


@dataclass(frozen=True, slots=True)
class SweepDeclaration:
    """A sweep as axes over a bot/Book/BMS context (B-12, spec R9).

    Every axis is non-empty by construction (:meth:`try_create` refuses an empty
    one). Declaration order — of ``instruments``, of ``timeframes``, and of the
    ``parameters`` names and each name's values — is identity content and fixes
    the deterministic enumeration order.
    """

    bot: str
    book: str
    bms: str
    instruments: tuple[str, ...]
    timeframes: tuple[DeclaredBarSpec, ...]
    parameters: Mapping[str, tuple[object, ...]]

    def __post_init__(self) -> None:
        frozen: dict[str, tuple[object, ...]] = {
            name: tuple(values) for name, values in self.parameters.items()
        }
        object.__setattr__(self, "parameters", MappingProxyType(frozen))

    @property
    def parameter_names(self) -> tuple[str, ...]:
        """The swept parameter names, in declaration order."""
        return tuple(self.parameters)

    @property
    def run_count(self) -> int:
        """The pre-flight run count: the product of the axis lengths (spec R9)."""
        total = len(self.instruments) * len(self.timeframes)
        for values in self.parameters.values():
            total *= len(values)
        return total

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Values are exact; a binary float never appears."""
        return {
            "bms": self.bms,
            "book": self.book,
            "bot": self.bot,
            "class": SWEEP_DECLARATION_CLASS,
            "format_version": SWEEP_FORMAT_VERSION,
            "instruments": list(self.instruments),
            "parameter_order": list(self.parameter_names),
            "parameters": {
                name: [_value_identity(value) for value in values]
                for name, values in self.parameters.items()
            },
            "timeframes": [spec.fp1_identity() for spec in self.timeframes],
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The declaration's ``fp1``, computed only by the single qmf-core seam."""
        return fingerprint(self.fp1_identity())

    @classmethod
    def try_create(
        cls,
        *,
        bot: object,
        book: object,
        bms: object,
        instruments: object,
        timeframes: object,
        parameters: object = None,
    ) -> Result[SweepDeclaration]:
        """Validate and build a sweep declaration.

        A zero-length instrument, ``BarSpec``, or parameter-value list is a typed
        ``invalid input`` refusal naming the empty axis (AD-11). A parameter value
        that is a bare binary float is refused; a money/rational value enters only
        through a named AD-7/AD-22 conversion mapping (B-8, FR-001).
        """
        cited = _cite_context(bot, book, bms)
        if is_refusal(cited):
            return cited
        bot_token, book_token, bms_token = cited.value
        parsed_instruments = _as_instruments(instruments)
        if is_refusal(parsed_instruments):
            return parsed_instruments
        parsed_timeframes = _as_timeframes(timeframes)
        if is_refusal(parsed_timeframes):
            return parsed_timeframes
        parsed_parameters = _as_parameters(parameters)
        if is_refusal(parsed_parameters):
            return parsed_parameters
        return Ok(
            cls(
                bot=bot_token,
                book=book_token,
                bms=bms_token,
                instruments=parsed_instruments.value,
                timeframes=parsed_timeframes.value,
                parameters=parsed_parameters.value,
            )
        )


def preflight_run_count(declaration: object) -> Result[int]:
    """The pre-flight run count for a sweep, a pure inspection (B-4, spec R9).

    The count equals the product of the axis lengths and is reported before any
    process is spawned. Computing it spawns no process, writes no ledger line,
    and admits no batch — it never touches the impure composition root.
    ``declaration`` is a :class:`SweepDeclaration` or the raw axis mapping.
    """
    parsed = _as_declaration(declaration)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value.run_count)


def expand_sweep(declaration: object) -> Result[tuple[SweepRunSpec, ...]]:
    """Expand a sweep to the full Cartesian product of its axes (B-12, spec R9).

    One :class:`SweepRunSpec` per combination, enumerated in declaration order:
    ``instruments`` vary slowest, then ``timeframes``, then each parameter in
    declaration order with the last-declared parameter varying fastest. Each
    combination is one isolated run spec of the same never-forked loop; the batch
    merges nothing. A ``1x1x1`` declaration expands to exactly one run spec — the
    same object at unit scale (spec R13). ``declaration`` is a
    :class:`SweepDeclaration` or the raw axis mapping.
    """
    parsed = _as_declaration(declaration)
    if is_refusal(parsed):
        return parsed
    spec = parsed.value
    names = spec.parameter_names
    value_axes: list[tuple[object, ...]] = [spec.parameters[name] for name in names]
    combinations: list[SweepRunSpec] = []
    for instrument, timeframe, *param_values in product(
        spec.instruments, spec.timeframes, *value_axes
    ):
        assignment = {name: param_values[index] for index, name in enumerate(names)}
        combinations.append(
            SweepRunSpec(
                bot=spec.bot,
                book=spec.book,
                bms=spec.bms,
                instrument=cast("str", instrument),
                timeframe=cast("DeclaredBarSpec", timeframe),
                parameters=assignment,
            )
        )
    return Ok(tuple(combinations))


def _as_declaration(value: object) -> Result[SweepDeclaration]:
    """Accept a :class:`SweepDeclaration` or coerce the raw axis mapping."""
    if isinstance(value, SweepDeclaration):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "declaration",
            "a sweep is a SweepDeclaration or a mapping naming bot/book/bms plus "
            "the axes instruments, timeframes, and parameters",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)
    return SweepDeclaration.try_create(
        bot=body.get("bot"),
        book=body.get("book"),
        bms=body.get("bms"),
        instruments=body.get("instruments"),
        timeframes=body.get("timeframes"),
        parameters=body.get("parameters"),
    )


def _cite_context(bot: object, book: object, bms: object) -> Result[tuple[str, str, str]]:
    """The bot/Book/BMS context, each an opaque fp1 or human-alias cite token."""
    bot_token = _cite_token(bot, _BOT_KEY)
    if is_refusal(bot_token):
        return bot_token
    book_token = _cite_token(book, _BOOK_KEY)
    if is_refusal(book_token):
        return book_token
    bms_token = _cite_token(bms, _BMS_KEY)
    if is_refusal(bms_token):
        return bms_token
    return Ok((bot_token.value, book_token.value, bms_token.value))


def _cite_token(value: object, field: str) -> Result[str]:
    """One context cite: an ``fp1`` fingerprint or a non-blank human alias."""
    if isinstance(value, Fingerprint):
        return Ok(value.value)
    token = clean_token(value)
    if token is None:
        return invalid(
            field,
            "a sweep names its bot/Book/BMS context by fp1 or a human alias",
            given=repr(value),
        )
    return Ok(token)


def _as_instruments(value: object) -> Result[tuple[str, ...]]:
    """A non-empty, unique, ordered instrument axis (AD-11 on empty)."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "instruments",
            "the instruments axis is a sequence of instrument ids",
            given=repr(type(value).__name__),
        )
    items = cast("Sequence[object]", value)
    if not items:
        return invalid(
            "instruments",
            "an empty instrument axis is invalid input — never a silent zero-combo batch (AD-11)",
        )
    parsed: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(items):
        token = clean_token(raw)
        if token is None:
            return invalid(
                "instruments",
                "each instrument axis entry is a non-blank instrument id",
                index=index,
                given=repr(raw),
            )
        if token in seen:
            return invalid(
                "instruments",
                "the instruments axis names each instrument once",
                index=index,
                instrument=token,
            )
        seen.add(token)
        parsed.append(token)
    return Ok(tuple(parsed))


def _as_timeframes(value: object) -> Result[tuple[DeclaredBarSpec, ...]]:
    """A non-empty, unique, ordered ``BarSpec`` axis (AD-11 on empty)."""
    if isinstance(value, DeclaredBarSpec):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "timeframes",
            "the timeframes axis is a sequence of BarSpecs (never a bare timeframe)",
            given=repr(type(value).__name__),
        )
    items = cast("Sequence[object]", value)
    if not items:
        return invalid(
            "timeframes",
            "an empty BarSpec axis is invalid input — never a silent zero-combo batch (AD-11)",
        )
    parsed: list[DeclaredBarSpec] = []
    seen: set[str] = set()
    for index, raw in enumerate(items):
        spec = DeclaredBarSpec.try_create(raw)
        if is_refusal(spec):
            return invalid(
                "timeframes",
                "each timeframe is a canonical BarSpec identity mapping",
                index=index,
                cause=dict(spec.context),
            )
        key = repr(spec.value.fp1_identity())
        if key in seen:
            return invalid(
                "timeframes",
                "the timeframes axis names each BarSpec once",
                index=index,
                bar_spec=spec.value.fp1_identity(),
            )
        seen.add(key)
        parsed.append(spec.value)
    return Ok(tuple(parsed))


def _as_parameters(value: object) -> Result[Mapping[str, tuple[object, ...]]]:
    """The parameters axis: ``{name: values[]}``, each list non-empty (AD-11)."""
    if value is None:
        return Ok(MappingProxyType({}))
    if not isinstance(value, Mapping):
        return invalid(
            "parameters",
            "the parameters axis is a mapping of name to a values list",
            given=repr(type(value).__name__),
        )
    raw = cast("Mapping[object, object]", value)
    parsed: dict[str, tuple[object, ...]] = {}
    for name, values in raw.items():
        token = clean_token(name)
        if token is None:
            return invalid(
                "parameters",
                "each swept parameter names a non-blank key",
                given=repr(name),
            )
        normalized = _as_parameter_values(token, values)
        if is_refusal(normalized):
            return normalized
        parsed[token] = normalized.value
    return Ok(MappingProxyType(parsed))


def _as_parameter_values(name: str, values: object) -> Result[tuple[object, ...]]:
    """One parameter's non-empty, unique, ordered value axis (AD-11 on empty)."""
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        return invalid(
            "parameters",
            "a swept parameter's values are a sequence",
            parameter=name,
            given=repr(type(values).__name__),
        )
    items = cast("Sequence[object]", values)
    if not items:
        return invalid(
            "parameters",
            "an empty parameter-value axis is invalid input — never a silent "
            "zero-combo batch (AD-11)",
            parameter=name,
        )
    parsed: list[object] = []
    seen: set[str] = set()
    for index, raw in enumerate(items):
        normalized = _normalize_value(name, index, raw)
        if is_refusal(normalized):
            return normalized
        key = repr(_value_identity(normalized.value))
        if key in seen:
            return invalid(
                "parameters",
                "a swept parameter names each value once",
                parameter=name,
                index=index,
            )
        seen.add(key)
        parsed.append(normalized.value)
    return Ok(tuple(parsed))


def _normalize_value(name: str, index: int, value: object) -> Result[object]:
    """Carry an exact value verbatim; cross a money/rational conversion; refuse floats.

    Exact-integer, categorical, and boolean values are carried verbatim. An
    already-exact :class:`Money` / :class:`ExactRational` is carried verbatim. A
    money/rational value enters only through a conversion mapping that states its
    rounding mode and target scale (AD-7/AD-22). A bare binary float is refused —
    a binary float never appears in a run spec's identity content (FR-001).
    """
    if isinstance(value, bool):
        return Ok(value)
    if isinstance(value, int):
        return Ok(value)
    if isinstance(value, (Money, ExactRational)):
        return Ok(value)
    if isinstance(value, float):
        return invalid(
            "parameters",
            "a binary float never appears in a run spec's identity content; declare "
            "a money/rational value through a named AD-7/AD-22 conversion (rounding "
            "mode + target scale) (FR-001, B-8)",
            parameter=name,
            index=index,
            given=repr(value),
        )
    if isinstance(value, Mapping):
        return _convert_value(name, index, cast("Mapping[str, object]", value))
    token = clean_token(value)
    if token is not None:
        return Ok(token)
    return invalid(
        "parameters",
        "a swept parameter value is an exact integer, a categorical token, a "
        "boolean, an exact Money/ExactRational, or a named conversion mapping",
        parameter=name,
        index=index,
        given=repr(value),
    )


def _convert_value(name: str, index: int, spec: Mapping[str, object]) -> Result[object]:
    """Cross a money/rational value through its named AD-7/AD-22 conversion."""
    kind = clean_token(spec.get("kind"))
    if kind is None or kind not in CONVERSION_KINDS:
        return invalid(
            "parameters",
            "a conversion mapping names kind money or rational",
            parameter=name,
            index=index,
            given=repr(spec.get("kind")),
            allowed=sorted(CONVERSION_KINDS),
        )
    raw_value = spec.get("value")
    if not isinstance(raw_value, float):
        return invalid(
            "parameters",
            "a named AD-7/AD-22 conversion crosses a binary float into an exact "
            "value; pass an exact Money/ExactRational directly for an exact input",
            parameter=name,
            index=index,
            kind=kind,
            given=repr(raw_value),
        )
    if "scale" not in spec or "rounding" not in spec:
        return invalid(
            "parameters",
            "a named conversion states its rounding mode and target scale",
            parameter=name,
            index=index,
            kind=kind,
        )
    scale = spec.get("scale")
    rounding = spec.get("rounding")
    if kind == VALUE_KIND_MONEY:
        money = Money.from_float(
            raw_value,
            currency=spec.get("currency"),
            scale=scale,
            rounding=rounding,
        )
        if is_refusal(money):
            return _conversion_refused(name, index, kind, money.context)
        return Ok(money.value)
    rational = ExactRational.from_float(
        raw_value,
        unit_kind=spec.get("unit_kind"),
        scale=scale,
        rounding=rounding,
    )
    if is_refusal(rational):
        return _conversion_refused(name, index, kind, rational.context)
    return Ok(rational.value)


def _conversion_refused(
    name: str, index: int, kind: str, cause: Mapping[str, object]
) -> Result[object]:
    """Re-wrap a CT-01 conversion refusal as the parameter's typed refusal."""
    return invalid(
        "parameters",
        "the named AD-7/AD-22 conversion refused this value",
        parameter=name,
        index=index,
        kind=kind,
        cause=dict(cause),
    )


def _value_identity(value: object) -> object:
    """Identity content for one carried value; exact objects resolve to fp1 content."""
    if isinstance(value, (Money, ExactRational)):
        return value.fp1_identity()
    return value
