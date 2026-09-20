"""Dummy Book/BMS/bot is invalid input on the default ResolvedRunConfig path.

SCN-0020 Then 1/3 / DEC-0424 / DEC-0448: Book/BMS/bot keys stay required on
``ResolvedRunConfig``. A dummy CT-22 / CT-27 / CT-33 or dummy PolicyPair —
identity / no-op / unlimited / pass-through, sentinel fps including
``NULL_BOOK``, empty-object Book, or ``mis_ref: null`` as a fake MIS — is
``invalid input`` at compile, register, validate, simulate, and seat.
Sensing / research / UngovernedWorkConfig is not ATC and not a QMN seat.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal
from qmf.risk.templates import BmsDefinition, BookDefinition

from qmb._refuse import clean_token, invalid
from qmb.config.fragments import (
    BMS_NAMESPACES,
    BOOK_NAMESPACES,
    SOURCE_BMS,
    SOURCE_BOOK,
    ConfigFragment,
)

__all__ = [
    "refuse_dummy_cite",
    "refuse_dummy_definition",
    "refuse_dummy_fragments",
    "refuse_dummy_mapping",
    "refuse_sensing_as_atc",
]

DUMMY_SENTINEL_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "NULL_BOOK",
        "NULL_BMS",
        "NULL_BOT",
        "NULL_POLICY_PAIR",
    }
)
_DUMMY_SENTINEL_FOLD: Final[frozenset[str]] = frozenset(
    item.casefold() for item in DUMMY_SENTINEL_TOKENS
)
DUMMY_POLICY_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "identity",
        "no-op",
        "noop",
        "unlimited",
        "pass-through",
        "passthrough",
        "pass_through",
    }
)
_POLICY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "accounting_policy",
        "mode",
        "policy",
        "policy_pair",
        "risk_policy",
    }
)
ATC_LABEL_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "alternative",
        "alternative-trading-composition",
        "alternative_trading_composition",
        "atc",
    }
)
SENSING_LABEL_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "research",
        "sensing",
        "sensing-only",
        "sensing_only",
        "ungoverned",
        "ungoverned-work",
        "ungoverned-work-config",
        "ungoverned_work",
        "ungoverned_work_config",
    }
)
SEAT_LABEL_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "qmn-seat",
        "qmn_seat",
        "seat",
    }
)
_LABEL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "class",
        "composition_class",
        "config_class",
        "kind",
        "label",
        "role",
    }
)
_DUMMY_REASON: Final[str] = (
    "dummy Book/BMS/bot or dummy PolicyPair is invalid input at compile, "
    "register, validate, simulate, and seat; identity / no-op / unlimited / "
    "pass-through / sentinel fps including NULL_BOOK, empty-object Book, and "
    "mis_ref: null are dummy (DEC-0424, DEC-0448)"
)
_SENSING_REASON: Final[str] = (
    "sensing/research/UngovernedWorkConfig is not an Alternative Trading "
    "Composition and is not a QMN seat (DEC-0424, DEC-0436)"
)
_ATC_THROUGH_DEFAULT_REASON: Final[str] = (
    "ATC and ungoverned keys cannot sneak through ResolvedRunConfig; "
    "book_fp1 / bms_fp1 / bot_fp1 / fragments remain required (DEC-0424)"
)


def refuse_dummy_cite(field: str, value: object) -> TypedRefusal | None:
    """Refuse a sentinel Book/BMS/bot cite used to satisfy a required field."""
    token = _cite_token(value)
    if token is None:
        return None
    if token in DUMMY_SENTINEL_TOKENS or token.casefold() in _DUMMY_SENTINEL_FOLD:
        return invalid(field, _DUMMY_REASON, sentinel=token)
    return None


def refuse_dummy_fragments(
    book: ConfigFragment,
    bms: ConfigFragment,
) -> TypedRefusal | None:
    """Refuse an empty-object or dummy-policy Book/BMS fragment at compile."""
    empty_book = _empty_object_fragment(book, SOURCE_BOOK, BOOK_NAMESPACES)
    if empty_book is not None:
        return empty_book
    empty_bms = _empty_object_fragment(bms, SOURCE_BMS, BMS_NAMESPACES)
    if empty_bms is not None:
        return empty_bms
    for fragment, field in ((book, "book_fragment"), (bms, "bms_fragment")):
        walked = refuse_dummy_mapping(fragment.keys, field=field)
        if walked is not None:
            return walked
        cited = refuse_dummy_cite(field, fragment.source_fp1)
        if cited is not None:
            return cited
    return None


def refuse_dummy_definition(
    definition: BookDefinition | BmsDefinition,
) -> TypedRefusal | None:
    """Refuse an empty-object or dummy-policy CT-22/CT-27 at register."""
    field = "book" if isinstance(definition, BookDefinition) else "bms"
    if not definition.sections:
        return invalid(field, _DUMMY_REASON, dummy="empty-object")
    return refuse_dummy_mapping(definition.fp1_identity(), field=field)


def refuse_dummy_mapping(
    value: object,
    *,
    field: str,
) -> TypedRefusal | None:
    """Refuse dummy policy, sentinel fps, fake MIS, or ATC keys on type (1)."""
    if not isinstance(value, Mapping):
        return None
    mapping = cast("Mapping[str, object]", value)
    if "policy_pair" in mapping:
        return invalid("policy_pair", _ATC_THROUGH_DEFAULT_REASON)
    class_hit = _atc_through_default(mapping)
    if class_hit is not None:
        return class_hit
    return _walk(mapping, field=field, path=())


def refuse_sensing_as_atc(payload: object) -> Result[None]:
    """Refuse labeling sensing/research/ungoverned as ATC or a QMN seat."""
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "a composition-label payload is a key->value mapping",
            given=repr(type(payload).__name__),
        )
    mapping = cast("Mapping[str, object]", payload)
    labels = _label_tokens(mapping)
    sensing = (
        bool(labels & SENSING_LABEL_TOKENS)
        or _truthy(mapping.get("sensing"))
        or _truthy(mapping.get("research"))
    )
    atc = bool(labels & ATC_LABEL_TOKENS)
    seat = bool(labels & SEAT_LABEL_TOKENS) or _truthy(mapping.get("seat"))
    if sensing and (atc or seat):
        return invalid("label", _SENSING_REASON, labels=tuple(sorted(labels)))
    return Ok(None)


def _atc_through_default(mapping: Mapping[str, object]) -> TypedRefusal | None:
    """ATC class tokens are a second composition, never ResolvedRunConfig fields."""
    for key in ("class", "composition_class", "config_class"):
        token = _fold_token(mapping.get(key))
        if token is not None and token in ATC_LABEL_TOKENS:
            return invalid(key, _ATC_THROUGH_DEFAULT_REASON, given=token)
    return None


def _empty_object_fragment(
    fragment: ConfigFragment,
    source_kind: str,
    owned: frozenset[str],
) -> TypedRefusal | None:
    if fragment.source_kind != source_kind:
        return invalid(
            "book_fragment" if source_kind == SOURCE_BOOK else "bms_fragment",
            "this layer is a Book or BMS config fragment",
            given=fragment.source_kind,
        )
    field = "book_fragment" if source_kind == SOURCE_BOOK else "bms_fragment"
    keys = dict(fragment.keys)
    if not keys:
        return invalid(field, _DUMMY_REASON, dummy="empty-object")
    if source_kind == SOURCE_BOOK:
        sizing = keys.get("sizing")
        if isinstance(sizing, Mapping):
            sizing_map = cast("Mapping[str, object]", sizing)
            if set(sizing_map) <= {"accounting_currency"}:
                keys = {name: item for name, item in keys.items() if name != "sizing"}
                if not keys:
                    return invalid(field, _DUMMY_REASON, dummy="empty-object")
    if not (set(keys) & owned):
        return invalid(field, _DUMMY_REASON, dummy="empty-object")
    return None


def _walk(
    value: object,
    *,
    field: str,
    path: tuple[str, ...],
) -> TypedRefusal | None:
    if value is None:
        if path and path[-1] == "mis_ref":
            return invalid("mis_ref", _DUMMY_REASON, dummy="mis_ref:null")
        return None
    if isinstance(value, Fingerprint):
        return refuse_dummy_cite(field if not path else path[-1], value)
    token = clean_token(value) if isinstance(value, str) else None
    if token is not None:
        if token in DUMMY_SENTINEL_TOKENS or token.casefold() in _DUMMY_SENTINEL_FOLD:
            hit = path[-1] if path else field
            return invalid(hit, _DUMMY_REASON, sentinel=token)
        folded = token.casefold()
        if folded in DUMMY_POLICY_TOKENS and _policy_path(path):
            hit = path[-1] if path else field
            return invalid(hit, _DUMMY_REASON, policy=token)
        return None
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        for raw_key, item in mapping.items():
            key = raw_key if isinstance(raw_key, str) else field
            walked = _walk(item, field=field, path=(*path, key))
            if walked is not None:
                return walked
        return None
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        for item in sequence:
            walked = _walk(item, field=field, path=path)
            if walked is not None:
                return walked
    return None


def _policy_path(path: tuple[str, ...]) -> bool:
    return bool(path) and path[-1] in _POLICY_KEYS


def _cite_token(value: object) -> str | None:
    if isinstance(value, Fingerprint):
        return value.value
    return clean_token(value)


def _fold_token(value: object) -> str | None:
    token = clean_token(value)
    if token is None:
        return None
    return token.strip().casefold().replace("_", "-")


def _label_tokens(mapping: Mapping[str, object]) -> frozenset[str]:
    tokens: set[str] = set()
    for key in _LABEL_KEYS:
        folded = _fold_token(mapping.get(key))
        if folded is not None:
            tokens.add(folded)
    return frozenset(tokens)


def _truthy(value: object) -> bool:
    return value is True
