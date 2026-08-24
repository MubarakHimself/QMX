"""Bot-state snapshot/restore contract (QL-7, AR-67).

A versioned serialized contract scoped to the injected tuple (OS, logic identity
+ source-manifest fingerprint, protocol format version, arithmetic-reference
build). Restoring across any component is an ``unavailable dependency`` refusal,
never best-effort. The OS is injected, never read ambiently. qml never hashes —
``fp1`` is computed only by qmf-core (DEC-0177, DEC-0108).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, canonical_bytes, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import clean_token, invalid, policy, unavailable, unsupported
from qml.footprint._coerce import deep_freeze
from qml.logic import LogicIdentity

__all__ = [
    "SCOPE_COMPONENTS",
    "STATE_SNAPSHOT_CLASS",
    "STATE_SNAPSHOT_FORMAT_VERSION",
    "STATE_SNAPSHOT_KNOWN_FORMAT_VERSIONS",
    "BotStateScope",
    "BotStateSnapshot",
    "assert_declared_state_bound",
    "capture_bot_state",
    "coerce_state_bound",
    "mint_state_scope",
    "refuse_scope_mismatch",
]

STATE_SNAPSHOT_CLASS: Final[str] = "qml-bot-state-snapshot"
STATE_SNAPSHOT_FORMAT_VERSION: Final[int] = 1
STATE_SNAPSHOT_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset(
    {STATE_SNAPSHOT_FORMAT_VERSION}
)
SCOPE_COMPONENTS: Final[tuple[str, ...]] = (
    "os",
    "logic_identity",
    "protocol_format_version",
    "arithmetic_reference_build",
)
_SCOPE_CLASS: Final[str] = "qml-bot-state-scope"


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def coerce_state_bound(value: object) -> Result[int]:
    """A declared state bound is a positive integer canonical-byte length."""
    bound = _positive_int(value)
    if bound is None:
        if value is None:
            return invalid(
                "state_bound",
                "bot state is bounded and declared, never unbounded",
            )
        return invalid(
            "state_bound",
            "a declared state bound is a positive integer canonical-byte length",
            given=repr(value),
        )
    return Ok(bound)


def assert_declared_state_bound(payload: object, bound: object) -> Result[int]:
    """Layer-2 concern: encoded payload must not exceed the declared bound.

    The bound is asserted here so a later Layer-2 suite can call the same
    function the snapshot path uses (DEC-0178). Exceeding it is a ``policy
    rejection``, never a silent truncate.
    """
    declared = coerce_state_bound(bound)
    if is_refusal(declared):
        return declared
    encoded = canonical_bytes(payload)
    if is_refusal(encoded):
        return invalid(
            "payload",
            "bot state payload must be fp1-clean identity content; a binary float, "
            "a null, or an unsupported type is refused",
            cause=dict(encoded.context),
        )
    size = len(encoded.value)
    if size > declared.value:
        return policy(
            "state_bound",
            "the declared state bound is exceeded; bot state is bounded and "
            "declared, never unbounded — a Layer-2 conformance concern",
            layer=2,
            encoded_bytes=size,
            state_bound=declared.value,
        )
    return Ok(size)


def _freeze_payload(value: object) -> Result[Mapping[str, object]]:
    if value is None:
        return Ok(MappingProxyType({}))
    if not isinstance(value, Mapping):
        return invalid(
            "payload",
            "bot state payload is a mapping of fp1-clean identity content",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[object, object]", value)
    frozen = deep_freeze(dict(mapping))
    if not isinstance(frozen, Mapping):
        return invalid("payload", "bot state payload is a mapping after freeze")
    return Ok(cast("Mapping[str, object]", frozen))


@dataclass(frozen=True, slots=True)
class BotStateScope:
    """Injected snapshot tuple (QL-7). Never read from the ambient platform."""

    os: str
    logic_identity: LogicIdentity
    protocol_format_version: int
    arithmetic_reference_build: str

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": _SCOPE_CLASS,
            "os": self.os,
            "logic_identity": self.logic_identity.fp1_identity(),
            "protocol_format_version": self.protocol_format_version,
            "arithmetic_reference_build": self.arithmetic_reference_build,
        }

    def to_mapping(self) -> dict[str, object]:
        return {
            "os": self.os,
            "logic_identity": self.logic_identity.as_logic_reference(),
            "protocol_format_version": self.protocol_format_version,
            "arithmetic_reference_build": self.arithmetic_reference_build,
        }

    def differing_components(self, other: BotStateScope) -> tuple[str, ...]:
        """Components that do not match ``other``, in canonical tuple order."""
        diffs: list[str] = []
        if self.os != other.os:
            diffs.append("os")
        if self.logic_identity != other.logic_identity:
            diffs.append("logic_identity")
        if self.protocol_format_version != other.protocol_format_version:
            diffs.append("protocol_format_version")
        if self.arithmetic_reference_build != other.arithmetic_reference_build:
            diffs.append("arithmetic_reference_build")
        return tuple(diffs)

    @classmethod
    def try_create(
        cls,
        *,
        os: object,
        logic_identity: object,
        protocol_format_version: object,
        arithmetic_reference_build: object,
    ) -> Result[BotStateScope]:
        """Validate the four-tuple. Protocol version here is a tuple component.

        An unknown *protocol* format is refused by the factory, not here, so a
        cross-version restore can surface as ``unavailable dependency`` rather
        than ``unsupported capability``.
        """
        os_token = clean_token(os)
        if os_token is None:
            return invalid(
                "os",
                "a bot-state scope names a non-empty OS identity (injected, never read ambiently)",
                given=repr(os),
            )
        logic = LogicIdentity.try_from_payload(logic_identity)
        if is_refusal(logic):
            return logic
        version = _positive_int(protocol_format_version)
        if version is None:
            return invalid(
                "protocol_format_version",
                "a protocol format version is a positive integer ordinal; package "
                "SemVer never enters",
                given=repr(protocol_format_version),
            )
        build = clean_token(arithmetic_reference_build)
        if build is None:
            return invalid(
                "arithmetic_reference_build",
                "a bot-state scope names a non-empty arithmetic-reference build "
                "identity (injected; 'none' when the logic declares no reference)",
                given=repr(arithmetic_reference_build),
            )
        return Ok(
            cls(
                os=os_token,
                logic_identity=logic.value,
                protocol_format_version=version,
                arithmetic_reference_build=build,
            )
        )

    @classmethod
    def try_from_mapping(cls, value: object) -> Result[BotStateScope]:
        if isinstance(value, cls):
            return Ok(value)
        if not isinstance(value, Mapping):
            return invalid(
                "scope",
                "a bot-state scope is a mapping of the four-tuple components",
                given=type(value).__name__,
            )
        mapping = cast("Mapping[str, object]", value)
        named = mapping.get("class")
        if named is not None and named != _SCOPE_CLASS:
            return invalid(
                "scope",
                "a bot-state scope mapping names class qml-bot-state-scope",
                given=repr(named),
            )
        return cls.try_create(
            os=mapping.get("os"),
            logic_identity=mapping.get("logic_identity"),
            protocol_format_version=mapping.get("protocol_format_version"),
            arithmetic_reference_build=mapping.get("arithmetic_reference_build"),
        )


def mint_state_scope(
    *,
    os: object,
    logic_identity: object,
    protocol_format_version: object,
    arithmetic_reference_build: object,
) -> Result[BotStateScope]:
    """Mint an injected bot-state scope tuple (DEC-0177)."""
    return BotStateScope.try_create(
        os=os,
        logic_identity=logic_identity,
        protocol_format_version=protocol_format_version,
        arithmetic_reference_build=arithmetic_reference_build,
    )


def refuse_scope_mismatch(
    snapshot_scope: BotStateScope, current_scope: BotStateScope
) -> Result[None]:
    """Identical tuple admits restore; any differing component is unavailable."""
    differing = snapshot_scope.differing_components(current_scope)
    if not differing:
        return Ok(None)
    return unavailable(
        "scope",
        "snapshot/restore is scoped to the exact tuple (OS, logic identity + "
        "source-manifest fingerprint, protocol format version, arithmetic-reference "
        "build); restoring across any component is an unavailable dependency, never "
        "best-effort",
        differing=differing,
        snapshot_scope=snapshot_scope.fp1_identity(),
        current_scope=current_scope.fp1_identity(),
    )


@dataclass(frozen=True, slots=True)
class BotStateSnapshot:
    """Serialized bot-state contract. Own format version, distinct from the protocol."""

    format_version: int
    scope: BotStateScope
    state_bound: int
    payload: Mapping[str, object]

    def fp1_identity(self) -> dict[str, object]:
        """Restored-state identity — bound is enforcement metadata, not identity."""
        return {
            "class": STATE_SNAPSHOT_CLASS,
            "format_version": self.format_version,
            "scope": self.scope.fp1_identity(),
            "payload": dict(self.payload),
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """``fp1`` of the restored state; hosts place this on downstream labels."""
        return fingerprint(self)

    def to_mapping(self) -> dict[str, object]:
        return {
            "class": STATE_SNAPSHOT_CLASS,
            "format_version": self.format_version,
            "scope": self.scope.to_mapping(),
            "state_bound": self.state_bound,
            "payload": dict(self.payload),
        }

    @classmethod
    def try_create(
        cls,
        *,
        scope: object,
        state_bound: object,
        payload: object,
        format_version: object = STATE_SNAPSHOT_FORMAT_VERSION,
    ) -> Result[BotStateSnapshot]:
        version = _coerce_snapshot_format(format_version)
        if is_refusal(version):
            return version
        resolved_scope = BotStateScope.try_from_mapping(scope)
        if is_refusal(resolved_scope):
            return resolved_scope
        frozen = _freeze_payload(payload)
        if is_refusal(frozen):
            return frozen
        sized = assert_declared_state_bound(frozen.value, state_bound)
        if is_refusal(sized):
            return sized
        bound = coerce_state_bound(state_bound)
        if is_refusal(bound):  # pragma: no cover - assert_declared_state_bound already checked
            return bound
        return Ok(
            cls(
                format_version=version.value,
                scope=resolved_scope.value,
                state_bound=bound.value,
                payload=frozen.value,
            )
        )

    @classmethod
    def from_mapping(cls, mapping: object) -> Result[BotStateSnapshot]:
        if isinstance(mapping, cls):
            return Ok(mapping)
        if not isinstance(mapping, Mapping):
            return invalid(
                "snapshot",
                "a bot-state snapshot is a mapping",
                given=type(mapping).__name__,
            )
        body = cast("Mapping[str, object]", mapping)
        named = body.get("class")
        if named is not None and named != STATE_SNAPSHOT_CLASS:
            return invalid(
                "snapshot",
                "a bot-state snapshot mapping names class qml-bot-state-snapshot",
                given=repr(named),
            )
        return cls.try_create(
            format_version=body.get("format_version", STATE_SNAPSHOT_FORMAT_VERSION),
            scope=body.get("scope"),
            state_bound=body.get("state_bound"),
            payload=body.get("payload"),
        )


def capture_bot_state(
    *,
    scope: object,
    state_bound: object,
    payload: object,
) -> Result[BotStateSnapshot]:
    """Capture declared bot state into the versioned snapshot contract."""
    return BotStateSnapshot.try_create(
        scope=scope,
        state_bound=state_bound,
        payload=payload,
        format_version=STATE_SNAPSHOT_FORMAT_VERSION,
    )


def _coerce_snapshot_format(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            "format_version",
            "a bot-state snapshot format version is a positive integer; package "
            "SemVer never enters",
            given=repr(value),
        )
    if value < 1:
        return invalid(
            "format_version",
            "a bot-state snapshot format version is a positive integer ordinal",
            given=repr(value),
        )
    if value not in STATE_SNAPSHOT_KNOWN_FORMAT_VERSIONS:
        return unsupported(
            "format_version",
            "an uninterpretable bot-state snapshot format version is an "
            "unsupported capability refusal, never a best-effort read",
            given=value,
            supported=STATE_SNAPSHOT_FORMAT_VERSION,
        )
    return Ok(value)
