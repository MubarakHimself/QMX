"""QML authoring of a complete PolicyPair without Book keys (Story 58.2).

When ATC is selected, authoring adopts PolicyPair identity. Book/BMS/bot keys
are absent, not null. Sensing/research is not ATC. QML does not import qmb;
the host binds validate/simulate.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import clean_token, invalid

__all__ = [
    "ACCOUNTING_POLICY_FIELDS",
    "BOOK_KEYS",
    "RISK_POLICY_FIELDS",
    "AuthoredPolicyPair",
    "author_policy_pair",
]

ACCOUNTING_POLICY_FIELDS: Final[tuple[str, ...]] = (
    "cash_identity",
    "position_identity",
    "fill_application",
    "valuation",
    "currency",
    "residual_meaning",
)
RISK_POLICY_FIELDS: Final[tuple[str, ...]] = (
    "max_gross",
    "halt",
    "sizing",
    "override_principal",
)
BOOK_KEYS: Final[frozenset[str]] = frozenset(
    {
        "bms",
        "bms_fp1",
        "bms_fragment",
        "bms_fragment_fp1",
        "book",
        "book_fp1",
        "book_fragment",
        "book_fragment_fp1",
        "bot",
        "bot_fp1",
    }
)
_DUMMY_POLICY: Final[frozenset[str]] = frozenset(
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
_DUMMY_SENTINEL: Final[frozenset[str]] = frozenset(
    {"NULL_BOOK", "NULL_BMS", "NULL_BOT", "NULL_POLICY_PAIR"}
)
_SENSING: Final[frozenset[str]] = frozenset(
    {
        "research",
        "sensing",
        "sensing-only",
        "ungoverned",
        "ungoverned-work",
        "ungoverned-work-config",
    }
)
_ATC: Final[frozenset[str]] = frozenset(
    {"alternative", "alternative-trading-composition", "atc"}
)
_SEAT: Final[frozenset[str]] = frozenset({"qmn-seat", "qmn_seat", "seat"})
_LABEL_KEYS: Final[frozenset[str]] = frozenset(
    {"class", "composition_class", "config_class", "kind", "label", "role"}
)
_SECRET_KEYS: Final[frozenset[str]] = frozenset(
    {"credential", "credential_value", "password", "secret", "secret_value"}
)


@dataclass(frozen=True, slots=True)
class AuthoredPolicyPair:
    """Fingerprintable PolicyPair bodies. Identity is id/version/hash, not the copy."""

    policy_pair_id: str
    policy_pair_version: int
    policy_pair_hash: Fingerprint
    accounting: Mapping[str, object]
    risk: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "accounting", MappingProxyType(dict(self.accounting)))
        object.__setattr__(self, "risk", MappingProxyType(dict(self.risk)))

    def identity(self) -> dict[str, object]:
        return {
            "policy_pair_id": self.policy_pair_id,
            "policy_pair_hash": self.policy_pair_hash.value,
            "policy_pair_version": self.policy_pair_version,
        }

    def inline_bodies(self) -> dict[str, object]:
        return {"accounting": dict(self.accounting), "risk": dict(self.risk)}


def author_policy_pair(
    payload: object,
    *,
    policy_pair_id: object,
    policy_pair_version: object,
) -> Result[AuthoredPolicyPair]:
    """Author a complete PolicyPair. Book keys absent. Dummy and sensing-as-ATC refuse."""
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "authored PolicyPair content is a key->value mapping",
            given=repr(type(payload).__name__),
        )
    body = cast("Mapping[str, object]", payload)
    present = sorted(name for name in body if name in BOOK_KEYS)
    if present:
        return invalid(
            present[0],
            "ATC authoring omits Book/BMS/bot keys; they are absent, not null",
            extra=present,
        )
    labels = _label_tokens(body)
    if labels & _SENSING and (labels & _ATC or labels & _SEAT or body.get("seat") is True):
        return invalid(
            "label",
            "sensing/research/UngovernedWorkConfig is not an Alternative Trading "
            "Composition and is not a QMN seat",
            labels=tuple(sorted(labels)),
        )
    pair_id = clean_token(policy_pair_id)
    if pair_id is None:
        return invalid("policy_pair_id", "PolicyPair identity includes policy_pair_id")
    folded_sentinels = {item.casefold() for item in _DUMMY_SENTINEL}
    if pair_id in _DUMMY_SENTINEL or pair_id.casefold() in folded_sentinels:
        return invalid("policy_pair_id", "dummy PolicyPair is invalid input", sentinel=pair_id)
    if isinstance(policy_pair_version, bool) or not isinstance(policy_pair_version, int):
        return invalid(
            "policy_pair_version",
            "policy_pair_version is a positive integer",
            given=repr(policy_pair_version),
        )
    if policy_pair_version < 1:
        return invalid("policy_pair_version", "policy_pair_version is a positive integer")
    accounting = _section(body.get("accounting"), "accounting", ACCOUNTING_POLICY_FIELDS)
    if is_refusal(accounting):
        return accounting
    risk = _section(body.get("risk"), "risk", RISK_POLICY_FIELDS)
    if is_refusal(risk):
        return risk
    hashed = fingerprint({"accounting": accounting.value, "risk": risk.value})
    if is_refusal(hashed):
        return hashed
    return Ok(
        AuthoredPolicyPair(
            policy_pair_id=pair_id,
            policy_pair_version=policy_pair_version,
            policy_pair_hash=hashed.value,
            accounting=accounting.value,
            risk=risk.value,
        )
    )


def _section(
    value: object,
    field: str,
    required: tuple[str, ...],
) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(
            field,
            "a complete PolicyPair carries accounting + risk catalogue fields",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[str, object]", value)
    if len(mapping) == 0:
        return invalid(
            field,
            "a complete PolicyPair carries accounting + risk catalogue fields",
            given="empty",
        )
    out: dict[str, object] = {}
    for raw_key, item in mapping.items():
        if raw_key.strip() == "":
            return invalid(field, "PolicyPair field names are non-empty strings")
        if raw_key in _SECRET_KEYS:
            return invalid(raw_key, "PolicyPair bodies carry no secrets")
        if item is None:
            return invalid(raw_key, "absent fields are omitted, never null", section=field)
        token = clean_token(item)
        if token is None:
            return invalid(raw_key, "PolicyPair field values are non-empty tokens")
        folded = token.strip().casefold().replace("_", "-")
        if (
            token in _DUMMY_SENTINEL
            or folded in _DUMMY_POLICY
            or token.casefold() in _DUMMY_POLICY
        ):
            return invalid(raw_key, "dummy PolicyPair is invalid input", policy=token)
        out[raw_key] = token
    missing = [name for name in required if name not in out]
    if missing:
        return invalid(
            field,
            "a complete PolicyPair carries accounting + risk catalogue fields",
            missing=missing,
        )
    extra = sorted(name for name in out if name not in required)
    if extra:
        return invalid(field, "PolicyPair sections carry only catalogue fields", extra=extra)
    return Ok(out)


def _label_tokens(mapping: Mapping[str, object]) -> frozenset[str]:
    tokens: set[str] = set()
    for key in _LABEL_KEYS:
        token = clean_token(mapping.get(key))
        if token is None:
            continue
        tokens.add(token.strip().casefold().replace("_", "-"))
    return frozenset(tokens)
