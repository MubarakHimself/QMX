"""The B-3 config compiler: one resolved, read-only, fingerprinted run-config.

Every run consumes exactly one fully-resolved artifact compiled from explicit
layers with fixed precedence: invocation flags > run spec (the bot layer) >
BMS fragment > Book fragment > workspace defaults. Book and BMS key namespaces
are DISJOINT; a collision is a compile-time typed refusal, and in any sanctioned
overlap BMS outranks Book (DEC-0160, DEC-0143, FM-1). The artifact cites Book,
BMS, bot, and any binding by ``fp1`` never ``name@version``. Its fingerprint is
the run-id root and the ledger key (DEC-0160). A replay clock bound to
synthetic-tainted data is ``invalid input`` because world is provenance-derived
and B-7 wins (FM-3, DEC-0164). Same inputs yield a byte-identical artifact.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, World, canonical_bytes, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal

from qmb._refuse import clean_token, invalid, unsupported
from qmb.config.fragments import (
    SOURCE_BMS,
    SOURCE_BOOK,
    SOURCE_PRESET,
    ConfigFragment,
)
from qmb.registryread import RegistryReadPort

__all__ = [
    "CITE_FIELDS",
    "CLOCK_REPLAY",
    "CLOCK_SIMULATED",
    "DISPLAY_FIELDS",
    "IDENTITY_FIELDS",
    "LAYER_PRECEDENCE",
    "OPTIONAL_IDENTITY_FIELDS",
    "PROVENANCE_PROCEDURE_EPHEMERAL",
    "PROVENANCE_RECORDED",
    "PROVENANCE_SYNTHETIC_TAINTED",
    "RUN_CONFIG_ARTIFACT_NAME",
    "RUN_CONFIG_CLASS",
    "RUN_CONFIG_FORMAT_VERSION",
    "RUN_CONFIG_FORMAT_VERSION_1",
    "RUN_CONFIG_KNOWN_FORMAT_VERSIONS",
    "SANCTIONED_OVERLAP_KEYS",
    "ResolvedRunConfig",
    "artifact_relative_path",
    "compile_run_config",
    "fingerprint_layers",
    "layers_identity",
    "ledger_key",
    "merge_book_bms_keys",
    "run_config_identity",
    "run_id_root",
]

# Highest-first (DEC-0160). Merge applies the reverse order so later overlays win.
LAYER_PRECEDENCE: Final[tuple[str, ...]] = (
    "invocation-flags",
    "run-spec",
    "bms-fragment",
    "book-fragment",
    "workspace-defaults",
)

RUN_CONFIG_CLASS: Final[str] = "resolved-run-config"
RUN_CONFIG_FORMAT_VERSION_1: Final[int] = 1
RUN_CONFIG_FORMAT_VERSION: Final[int] = RUN_CONFIG_FORMAT_VERSION_1
RUN_CONFIG_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset({RUN_CONFIG_FORMAT_VERSION_1})
RUN_CONFIG_ARTIFACT_NAME: Final[str] = "run-config.json"

# V1 has no sanctioned Book/BMS overlap. A future sanctioned key is added here;
# compilation then lets BMS outrank Book for that key instead of refusing.
SANCTIONED_OVERLAP_KEYS: Final[frozenset[str]] = frozenset()

CLOCK_REPLAY: Final[str] = "replay"
CLOCK_SIMULATED: Final[str] = "simulated"
_LEGAL_CLOCKS: Final[frozenset[str]] = frozenset({CLOCK_REPLAY, CLOCK_SIMULATED})

PROVENANCE_RECORDED: Final[str] = "recorded"
PROVENANCE_SYNTHETIC_TAINTED: Final[str] = "synthetic-tainted"
PROVENANCE_PROCEDURE_EPHEMERAL: Final[str] = "procedure-ephemeral"
_LEGAL_PROVENANCE: Final[frozenset[str]] = frozenset(
    {
        PROVENANCE_RECORDED,
        PROVENANCE_SYNTHETIC_TAINTED,
        PROVENANCE_PROCEDURE_EPHEMERAL,
    }
)

CITE_FIELDS: Final[tuple[str, ...]] = ("bot", "book", "bms", "binding")
_SPECIAL_KEYS: Final[frozenset[str]] = frozenset(
    {*CITE_FIELDS, "world", "clock", "data_provenance"}
)

# AD-10 identity-vs-display classification for format 1. Optional identity
# fields are identity when present and omitted (never null) when absent.
IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "class",
    "format_version",
    "layer_precedence",
    "identity_fields",
    "display_fields",
    "book_fp1",
    "bms_fp1",
    "bot_fp1",
    "book_fragment_fp1",
    "bms_fragment_fp1",
    "keys",
    "clock",
    "data_provenance",
    "world",
)
OPTIONAL_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "binding_fp1",
    "condition_preset_fp1",
)
DISPLAY_FIELDS: Final[tuple[str, ...]] = (
    "book_alias",
    "bms_alias",
    "bot_alias",
    "binding_alias",
    "package_version",
)
_CLASSIFICATION_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    *IDENTITY_FIELDS,
    *OPTIONAL_IDENTITY_FIELDS,
)
_EMPTY_DISPLAY: Final[Mapping[str, object]] = MappingProxyType({})


def layers_identity() -> dict[str, object]:
    """Identity-bearing compiler fields. Package SemVer is omitted."""
    return {"layer_precedence": LAYER_PRECEDENCE}


def fingerprint_layers() -> Result[Fingerprint]:
    """``fp1`` over the layering identity, computed only by qmf-core."""
    return fingerprint(layers_identity())


def run_config_identity() -> dict[str, object]:
    """Identity-bearing resolved-run-config schema. Package SemVer is omitted."""
    return {
        "class": RUN_CONFIG_CLASS,
        "display_fields": DISPLAY_FIELDS,
        "format_version": RUN_CONFIG_FORMAT_VERSION,
        "identity_fields": _CLASSIFICATION_IDENTITY_FIELDS,
        "layer_precedence": LAYER_PRECEDENCE,
        "sanctioned_overlap_keys": tuple(sorted(SANCTIONED_OVERLAP_KEYS)),
    }


def run_id_root(config: ResolvedRunConfig) -> Fingerprint:
    """The resolved-config fingerprint is the run-id root (B-3, DEC-0160)."""
    return config.fingerprint


def ledger_key(config: ResolvedRunConfig) -> Fingerprint:
    """The resolved-config fingerprint is the ledger key (B-3, DEC-0160)."""
    return config.fingerprint


def artifact_relative_path(run_id: Fingerprint) -> str:
    """Relative path of the artifact inside the run's output directory.

    The directory is named by the run id. Colon is not a legal path character
    on Windows, so the on-disk directory uses hyphens; the run id itself
    remains the ``fp1:sha256:<hex>`` fingerprint.
    """
    return f"{run_id.value.replace(':', '-')}/{RUN_CONFIG_ARTIFACT_NAME}"


@dataclass(frozen=True, slots=True)
class ResolvedRunConfig:
    """One fully-resolved, read-only, schema-validated run-config (B-3).

    Identity is qmf-core ``fp1`` over :meth:`fp1_identity`. Display aliases and
    package SemVer are excluded. The fingerprint is the run-id root and the
    ledger key; every door computes it by calling qmf-core, never a door-local
    recipe (DEC-0160).
    """

    format_version: int
    book_fp1: Fingerprint
    bms_fp1: Fingerprint
    bot_fp1: Fingerprint
    book_fragment_fp1: Fingerprint
    bms_fragment_fp1: Fingerprint
    keys: Mapping[str, object]
    clock: str
    data_provenance: str
    world: World
    fingerprint: Fingerprint
    binding_fp1: Fingerprint | None = None
    condition_preset_fp1: tuple[Fingerprint, ...] = ()
    display: Mapping[str, object] = _EMPTY_DISPLAY

    def __post_init__(self) -> None:
        object.__setattr__(self, "keys", _freeze_mapping(self.keys))
        object.__setattr__(self, "display", _freeze_mapping(self.display))
        object.__setattr__(self, "condition_preset_fp1", tuple(self.condition_preset_fp1))

    @property
    def run_id(self) -> Fingerprint:
        """The run-id root — this artifact's fingerprint."""
        return self.fingerprint

    def fp1_identity(self) -> dict[str, object]:
        """The parts that ARE this run-config's identity. Display is omitted."""
        return _identity_content(
            format_version=self.format_version,
            book_fp1=self.book_fp1,
            bms_fp1=self.bms_fp1,
            bot_fp1=self.bot_fp1,
            book_fragment_fp1=self.book_fragment_fp1,
            bms_fragment_fp1=self.bms_fragment_fp1,
            keys=self.keys,
            clock=self.clock,
            data_provenance=self.data_provenance,
            world=self.world,
            binding_fp1=self.binding_fp1,
            condition_preset_fp1=self.condition_preset_fp1,
        )

    def artifact_bytes(self) -> Result[bytes]:
        """Canonical bytes of the identity artifact — byte-identical for same inputs."""
        return canonical_bytes(self.fp1_identity())

    def artifact_relative_path(self) -> str:
        """``{run-id}/run-config.json`` with a filesystem-safe run-id directory."""
        return artifact_relative_path(self.fingerprint)

    @classmethod
    def try_read(
        cls,
        identity: object,
        *,
        reader_format_version: object = RUN_CONFIG_FORMAT_VERSION,
    ) -> Result[ResolvedRunConfig]:
        """Re-read a resolved run-config. Old format versions stay readable forever.

        A format-1 reader confronting a newer artifact refuses ``unsupported
        capability``. An unknown format version is likewise unsupported — never
        a best-effort read (AD-5). Display keys are accepted and excluded from
        identity.
        """
        if not isinstance(identity, Mapping):
            return invalid(
                "identity",
                "a resolved run-config identity is a key->value mapping",
                given=repr(type(identity).__name__),
            )
        body = cast("Mapping[str, object]", identity)
        class_token = clean_token(body.get("class"))
        if class_token != RUN_CONFIG_CLASS:
            return invalid(
                "class",
                "a resolved run-config identity names class resolved-run-config",
                given=repr(body.get("class")),
            )
        reader = _coerce_format_version(reader_format_version)
        if reader is None:
            return unsupported(
                "reader_format_version",
                "a run-config reader format version is a positive integer ordinal",
                given=repr(reader_format_version),
            )
        version = _coerce_format_version(body.get("format_version"))
        if version is None or version not in RUN_CONFIG_KNOWN_FORMAT_VERSIONS:
            return unsupported(
                "format_version",
                "this resolved run-config format version is not one this build "
                "understands; an unknown version is never best-effort read",
                given=repr(body.get("format_version")),
                understood=sorted(RUN_CONFIG_KNOWN_FORMAT_VERSIONS),
            )
        if version > reader:
            return unsupported(
                "format_version",
                "a format-1 reader confronting a newer run-config refuses "
                "unsupported capability; old artifacts stay readable forever",
                given=version,
                reader_format_version=reader,
            )
        allowed = set(_CLASSIFICATION_IDENTITY_FIELDS) | set(DISPLAY_FIELDS)
        extra = [key for key in body if key not in allowed]
        if extra:
            return invalid(
                "identity",
                "a format-1 resolved run-config carries only declared identity and display fields",
                extra=sorted(extra),
            )
        classified = _require_token_tuple(body.get("identity_fields"), "identity_fields")
        if is_refusal(classified):
            return classified
        if classified.value != _CLASSIFICATION_IDENTITY_FIELDS:
            return invalid(
                "identity_fields",
                "a format-1 resolved run-config declares the AD-10 identity field set",
                given=list(classified.value),
                expected=list(_CLASSIFICATION_IDENTITY_FIELDS),
            )
        display_declared = _require_token_tuple(body.get("display_fields"), "display_fields")
        if is_refusal(display_declared):
            return display_declared
        if display_declared.value != DISPLAY_FIELDS:
            return invalid(
                "display_fields",
                "a format-1 resolved run-config declares the AD-10 display field set",
                given=list(display_declared.value),
                expected=list(DISPLAY_FIELDS),
            )
        precedence = _require_token_tuple(body.get("layer_precedence"), "layer_precedence")
        if is_refusal(precedence):
            return precedence
        if precedence.value != LAYER_PRECEDENCE:
            return invalid(
                "layer_precedence",
                "layer precedence is pinned: invocation flags > run spec > BMS "
                "fragment > Book fragment > workspace defaults",
                given=list(precedence.value),
                expected=list(LAYER_PRECEDENCE),
            )
        book = _require_fingerprint(body.get("book_fp1"), "book_fp1")
        if is_refusal(book):
            return book
        bms = _require_fingerprint(body.get("bms_fp1"), "bms_fp1")
        if is_refusal(bms):
            return bms
        bot = _require_fingerprint(body.get("bot_fp1"), "bot_fp1")
        if is_refusal(bot):
            return bot
        book_frag = _require_fingerprint(body.get("book_fragment_fp1"), "book_fragment_fp1")
        if is_refusal(book_frag):
            return book_frag
        bms_frag = _require_fingerprint(body.get("bms_fragment_fp1"), "bms_fragment_fp1")
        if is_refusal(bms_frag):
            return bms_frag
        binding: Fingerprint | None = None
        if "binding_fp1" in body:
            bound = _require_fingerprint(body.get("binding_fp1"), "binding_fp1")
            if is_refusal(bound):
                return bound
            binding = bound.value
        presets: tuple[Fingerprint, ...] = ()
        if "condition_preset_fp1" in body:
            parsed_presets = _require_fingerprint_tuple(
                body.get("condition_preset_fp1"),
                "condition_preset_fp1",
            )
            if is_refusal(parsed_presets):
                return parsed_presets
            presets = parsed_presets.value
        keys = body.get("keys")
        if not isinstance(keys, Mapping):
            return invalid(
                "keys",
                "resolved run-config keys are a key->value mapping",
                given=repr(type(keys).__name__),
            )
        keys_map = cast("Mapping[str, object]", keys)
        special = [key for key in keys_map if key in _SPECIAL_KEYS]
        if special:
            return invalid(
                "keys",
                "citation, clock, provenance, and world keys are dedicated fields, "
                "never residual resolved keys",
                extra=sorted(special),
            )
        clock = clean_token(body.get("clock"))
        provenance = clean_token(body.get("data_provenance"))
        if clock is None or provenance is None:
            return invalid(
                "clock",
                "a resolved run-config binds a clock and a data-provenance token",
                clock=repr(body.get("clock")),
                data_provenance=repr(body.get("data_provenance")),
            )
        world = _coerce_world(body.get("world"))
        if world is None:
            return invalid(
                "world",
                "world is provenance-derived: replay or simulated",
                given=repr(body.get("world")),
            )
        derived = _derive_world(clock, provenance)
        if is_refusal(derived):
            return derived
        if derived.value is not world:
            return invalid(
                "world",
                "world is provenance-derived and must match the bound clock "
                "and data provenance; a caller may not declare world (B-7)",
                given=world.value,
                derived=derived.value.value,
            )
        display_payload: dict[str, object] = {}
        for field in DISPLAY_FIELDS:
            if field in body:
                display_payload[field] = body[field]
        return _finish(
            format_version=version,
            book_fp1=book.value,
            bms_fp1=bms.value,
            bot_fp1=bot.value,
            book_fragment_fp1=book_frag.value,
            bms_fragment_fp1=bms_frag.value,
            keys=keys_map,
            clock=clock,
            data_provenance=provenance,
            world=world,
            binding_fp1=binding,
            condition_preset_fp1=presets,
            display=display_payload,
        )


def compile_run_config(
    port: object,
    *,
    book_fragment: object,
    bms_fragment: object,
    run_spec: object,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
) -> Result[ResolvedRunConfig]:
    """Compile exactly one resolved run-config from the fixed-precedence layers.

    The compiler resolves bot and binding citations through the one
    library-owned registry-read port. Invocation may have used a human alias;
    the artifact cites ``fp1``. Domain failure is a CT-04 value, returned never
    raised.
    """
    resolved_port = _require_port(port)
    if is_refusal(resolved_port):
        return resolved_port
    book = _require_fragment(book_fragment, SOURCE_BOOK, "book_fragment")
    if is_refusal(book):
        return book
    bms = _require_fragment(bms_fragment, SOURCE_BMS, "bms_fragment")
    if is_refusal(bms):
        return bms
    spec = _as_mapping(run_spec, "run_spec")
    if is_refusal(spec):
        return spec
    flags = _as_mapping(invocation_flags, "invocation_flags")
    if is_refusal(flags):
        return flags
    defaults = _as_mapping(workspace_defaults, "workspace_defaults")
    if is_refusal(defaults):
        return defaults
    presets = _as_presets(condition_presets)
    if is_refusal(presets):
        return presets
    combined = merge_book_bms_keys(book.value.keys, bms.value.keys)
    if is_refusal(combined):
        return combined
    acc = _overlay({}, defaults.value)
    acc = _overlay(acc, combined.value)
    preset_fps: list[Fingerprint] = []
    for preset in presets.value:
        acc = _overlay(acc, preset.keys)
        preset_fps.append(preset.fingerprint)
    acc = _overlay(acc, spec.value)
    acc = _overlay(acc, flags.value)
    if "world" in acc:
        return invalid(
            "world",
            "world is provenance-derived, never caller-declared (B-7, FM-3)",
            given=repr(acc.get("world")),
        )
    named = _refuse_name_at_cites(acc)
    if named is not None:
        return named
    clock = clean_token(acc.get("clock"))
    provenance = clean_token(acc.get("data_provenance"))
    if clock not in _LEGAL_CLOCKS:
        return invalid(
            "clock",
            "a run-config binds clock replay or simulated; live venue clocks "
            "are trading-node territory and QMB V1 does not bind them",
            given=repr(acc.get("clock")),
            legal=sorted(_LEGAL_CLOCKS),
        )
    if provenance not in _LEGAL_PROVENANCE:
        return invalid(
            "data_provenance",
            "data provenance is recorded, synthetic-tainted, or procedure-ephemeral",
            given=repr(acc.get("data_provenance")),
            legal=sorted(_LEGAL_PROVENANCE),
        )
    world = _derive_world(clock, provenance)
    if is_refusal(world):
        return world
    bot_ref = acc.get("bot")
    if bot_ref is None:
        return invalid(
            "bot",
            "the run spec (bot layer) cites a bot by fp1 or a human alias; "
            "the resolved artifact cites fp1, never name@version",
        )
    bot = _resolve_cite(resolved_port.value, "bot", bot_ref)
    if is_refusal(bot):
        return bot
    binding: Fingerprint | None = None
    if "binding" in acc:
        bound = _resolve_cite(resolved_port.value, "binding", acc["binding"])
        if is_refusal(bound):
            return bound
        binding = bound.value
    keys = {key: value for key, value in acc.items() if key not in _SPECIAL_KEYS}
    display = _display_aliases(acc, bot_alias=_alias_if_not_fp1(bot_ref))
    if "binding" in acc:
        binding_alias = _alias_if_not_fp1(acc["binding"])
        if binding_alias is not None:
            display["binding_alias"] = binding_alias
    return _finish(
        format_version=RUN_CONFIG_FORMAT_VERSION,
        book_fp1=book.value.source_fp1,
        bms_fp1=bms.value.source_fp1,
        bot_fp1=bot.value,
        book_fragment_fp1=book.value.fingerprint,
        bms_fragment_fp1=bms.value.fingerprint,
        keys=keys,
        clock=clock,
        data_provenance=provenance,
        world=world.value,
        binding_fp1=binding,
        condition_preset_fp1=tuple(preset_fps),
        display=display,
    )


def merge_book_bms_keys(
    book_keys: object,
    bms_keys: object,
    *,
    sanctioned_overlap: object = None,
) -> Result[dict[str, object]]:
    """Merge Book and BMS fragment keys.

    A colliding key is a compile-time typed refusal (FM-1). In any sanctioned
    overlap BMS outranks Book — "BMS accounts for and constrains Books"
    (DEC-0160, DEC-0143). V1's sanctioned set is empty.
    """
    book = _as_mapping(book_keys, "book_keys")
    if is_refusal(book):
        return book
    bms = _as_mapping(bms_keys, "bms_keys")
    if is_refusal(bms):
        return bms
    sanctioned = _as_string_set(sanctioned_overlap, "sanctioned_overlap")
    if is_refusal(sanctioned):
        return sanctioned
    overlap = set(book.value) & set(bms.value)
    unsanctioned = overlap - sanctioned.value
    if unsanctioned:
        return invalid(
            "keys",
            "Book and BMS key namespaces are DISJOINT; a key collision is a "
            "compile-time typed refusal (B-3, FM-1). In any sanctioned overlap "
            "BMS outranks Book",
            colliding=sorted(unsanctioned),
            sanctioned=sorted(overlap & sanctioned.value),
        )
    merged = _overlay({}, book.value)
    return Ok(_overlay(merged, bms.value))


def _identity_content(
    *,
    format_version: int,
    book_fp1: Fingerprint,
    bms_fp1: Fingerprint,
    bot_fp1: Fingerprint,
    book_fragment_fp1: Fingerprint,
    bms_fragment_fp1: Fingerprint,
    keys: Mapping[str, object],
    clock: str,
    data_provenance: str,
    world: World,
    binding_fp1: Fingerprint | None,
    condition_preset_fp1: tuple[Fingerprint, ...],
) -> dict[str, object]:
    """Canonical identity payload. Display aliases and SemVer are omitted."""
    content: dict[str, object] = {
        "bms_fragment_fp1": bms_fragment_fp1.value,
        "bms_fp1": bms_fp1.value,
        "book_fragment_fp1": book_fragment_fp1.value,
        "book_fp1": book_fp1.value,
        "bot_fp1": bot_fp1.value,
        "class": RUN_CONFIG_CLASS,
        "clock": clock,
        "data_provenance": data_provenance,
        "display_fields": list(DISPLAY_FIELDS),
        "format_version": format_version,
        "identity_fields": list(_CLASSIFICATION_IDENTITY_FIELDS),
        "keys": _plain(keys),
        "layer_precedence": list(LAYER_PRECEDENCE),
        "world": world.value,
    }
    if binding_fp1 is not None:
        content["binding_fp1"] = binding_fp1.value
    if condition_preset_fp1:
        content["condition_preset_fp1"] = [item.value for item in condition_preset_fp1]
    return content


def _finish(
    *,
    format_version: int,
    book_fp1: Fingerprint,
    bms_fp1: Fingerprint,
    bot_fp1: Fingerprint,
    book_fragment_fp1: Fingerprint,
    bms_fragment_fp1: Fingerprint,
    keys: Mapping[str, object],
    clock: str,
    data_provenance: str,
    world: World,
    binding_fp1: Fingerprint | None,
    condition_preset_fp1: tuple[Fingerprint, ...],
    display: Mapping[str, object],
) -> Result[ResolvedRunConfig]:
    """Fingerprint identity content and freeze the resolved artifact."""
    identity = _identity_content(
        format_version=format_version,
        book_fp1=book_fp1,
        bms_fp1=bms_fp1,
        bot_fp1=bot_fp1,
        book_fragment_fp1=book_fragment_fp1,
        bms_fragment_fp1=bms_fragment_fp1,
        keys=keys,
        clock=clock,
        data_provenance=data_provenance,
        world=world,
        binding_fp1=binding_fp1,
        condition_preset_fp1=condition_preset_fp1,
    )
    derived = fingerprint(identity)
    if is_refusal(derived):
        return invalid(
            "keys",
            "the resolved run-config is not fp1-clean identity content",
            cause=dict(derived.context),
        )
    return Ok(
        ResolvedRunConfig(
            format_version=format_version,
            book_fp1=book_fp1,
            bms_fp1=bms_fp1,
            bot_fp1=bot_fp1,
            book_fragment_fp1=book_fragment_fp1,
            bms_fragment_fp1=bms_fragment_fp1,
            keys=keys,
            clock=clock,
            data_provenance=data_provenance,
            world=world,
            fingerprint=derived.value,
            binding_fp1=binding_fp1,
            condition_preset_fp1=condition_preset_fp1,
            display=display,
        )
    )


def _derive_world(clock: str, provenance: str) -> Result[World]:
    """World is provenance-derived. Replay clock + synthetic-tainted is FM-3."""
    derived = World.SIMULATED if provenance == PROVENANCE_SYNTHETIC_TAINTED else World.REPLAY
    if clock == CLOCK_REPLAY and provenance == PROVENANCE_SYNTHETIC_TAINTED:
        return invalid(
            "clock",
            "a replay clock bound to synthetic-tainted data is invalid input; "
            "world is provenance-derived and B-7 wins (FM-3, DEC-0164)",
            clock=clock,
            data_provenance=provenance,
        )
    if clock == CLOCK_REPLAY and derived is World.REPLAY:
        return Ok(World.REPLAY)
    if clock == CLOCK_SIMULATED and derived is World.SIMULATED:
        return Ok(World.SIMULATED)
    return invalid(
        "clock",
        "a clock/adapter versus data-provenance mismatch is invalid input; "
        "world is provenance-derived, never caller-declared (FM-3, DEC-0164)",
        clock=clock,
        data_provenance=provenance,
        derived_world=derived.value,
    )


def _resolve_cite(port: RegistryReadPort, field: str, value: object) -> Result[Fingerprint]:
    """Resolve a citation through the one registry-read port to an fp1."""
    parsed = _parse_cite(value, field)
    if is_refusal(parsed):
        return parsed
    looked = port.resolve(parsed.value)
    if is_refusal(looked):
        return looked
    return Ok(looked.value.fingerprint)


def _parse_cite(value: object, field: str) -> Result[Fingerprint | str]:
    """Split a cite into fp1 or alias. ``name@version`` is always refused."""
    if isinstance(value, Fingerprint):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            field,
            "a citation is an fp1 fingerprint or a human alias; name@version is not a cite",
            given=repr(value),
        )
    if "@" in token:
        return invalid(
            field,
            "name@version is not a legal identity cite; the resolved artifact "
            "cites Book, BMS, bot, and any binding by fp1 (B-3, B-13)",
            given=token,
        )
    parsed = Fingerprint.try_create(token)
    if is_ok(parsed):
        return Ok(parsed.value)
    return Ok(token)


def _refuse_name_at_cites(merged: Mapping[str, object]) -> TypedRefusal | None:
    """Refuse a winning cite that still uses the banned name@version form."""
    for field in CITE_FIELDS:
        if field not in merged:
            continue
        value = merged[field]
        token = value.value if isinstance(value, Fingerprint) else clean_token(value)
        if isinstance(token, str) and "@" in token:
            return invalid(
                field,
                "name@version is not a legal identity cite; the resolved artifact "
                "cites Book, BMS, bot, and any binding by fp1 (B-3, B-13)",
                given=token,
            )
    return None


def _alias_if_not_fp1(value: object) -> str | None:
    """Display-only alias when the winning cite was not already an fp1."""
    if isinstance(value, Fingerprint):
        return None
    token = clean_token(value)
    if token is None:
        return None
    if is_ok(Fingerprint.try_create(token)):
        return None
    return token


def _display_aliases(merged: Mapping[str, object], *, bot_alias: str | None) -> dict[str, object]:
    """Collect display-only aliases. Package SemVer is never added here."""
    display: dict[str, object] = {}
    if bot_alias is not None:
        display["bot_alias"] = bot_alias
    book_alias = _alias_if_not_fp1(merged["book"]) if "book" in merged else None
    if book_alias is not None:
        display["book_alias"] = book_alias
    bms_alias = _alias_if_not_fp1(merged["bms"]) if "bms" in merged else None
    if bms_alias is not None:
        display["bms_alias"] = bms_alias
    return display


def _require_port(port: object) -> Result[RegistryReadPort]:
    """The one library-owned registry-read port, or invalid input."""
    if not isinstance(port, RegistryReadPort):
        return invalid(
            "port",
            "the config compiler resolves through the one registry-read port",
            given=repr(type(port).__name__),
        )
    return Ok(port)


def _require_fragment(value: object, expected_kind: str, field: str) -> Result[ConfigFragment]:
    """A materialized config fragment of the expected source kind."""
    if not isinstance(value, ConfigFragment):
        return invalid(
            field,
            "compilation consumes a materialized ConfigFragment, never a free-hand mapping",
            given=repr(type(value).__name__),
        )
    if value.source_kind != expected_kind:
        return invalid(
            field,
            f"this layer is a {expected_kind} config fragment",
            given=value.source_kind,
            expected=expected_kind,
        )
    return Ok(value)


def _as_presets(value: object) -> Result[tuple[ConfigFragment, ...]]:
    """Named condition presets are config fragments like any other (B-3)."""
    if value is None:
        return Ok(())
    if isinstance(value, ConfigFragment):
        return invalid(
            "condition_presets",
            "condition presets are a sequence of named-condition-preset fragments",
            given="ConfigFragment",
        )
    if not isinstance(value, (list, tuple)):
        return invalid(
            "condition_presets",
            "condition presets are a sequence of named-condition-preset fragments",
            given=repr(type(value).__name__),
        )
    sequence = cast("Sequence[object]", value)
    out: list[ConfigFragment] = []
    for index, item in enumerate(sequence):
        if not isinstance(item, ConfigFragment):
            return invalid(
                "condition_presets",
                "each condition preset is a ConfigFragment",
                index=index,
                given=repr(type(item).__name__),
            )
        if item.source_kind != SOURCE_PRESET:
            return invalid(
                "condition_presets",
                "a named condition preset carries source kind named-condition-preset",
                index=index,
                given=item.source_kind,
            )
        out.append(item)
    return Ok(tuple(out))


def _as_mapping(value: object, field: str) -> Result[Mapping[str, object]]:
    """A string-keyed mapping, or empty when the layer is omitted."""
    if value is None:
        return Ok({})
    if not isinstance(value, Mapping):
        return invalid(
            field,
            "a config layer is a key->value mapping",
            given=repr(type(value).__name__),
        )
    raw = cast("Mapping[object, object]", value)
    out: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str) or key.strip() == "":
            return invalid(
                field,
                "config layer keys are non-empty strings",
                given=repr(key),
            )
        out[key] = item
    return Ok(out)


def _as_string_set(value: object, field: str) -> Result[frozenset[str]]:
    """The sanctioned-overlap set, defaulting to the V1 empty constant."""
    if value is None:
        return Ok(SANCTIONED_OVERLAP_KEYS)
    if isinstance(value, (set, frozenset, list, tuple)):
        tokens: list[str] = []
        for item in cast("Sequence[object] | set[object] | frozenset[object]", value):
            token = clean_token(item)
            if token is None:
                return invalid(
                    field,
                    "sanctioned overlap keys are non-empty strings",
                    given=repr(item),
                )
            tokens.append(token)
        return Ok(frozenset(tokens))
    return invalid(
        field,
        "sanctioned overlap is a set of key names",
        given=repr(type(value).__name__),
    )


def _overlay(base: dict[str, object], incoming: Mapping[str, object]) -> dict[str, object]:
    """Shallow overlay: a higher layer replaces a top-level key wholesale."""
    out = dict(base)
    for key, value in incoming.items():
        out[key] = _plain(value)
    return out


def _require_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    parsed = _coerce_fingerprint(value)
    if parsed is None:
        return invalid(
            field,
            "the resolved artifact cites Book, BMS, bot, and any binding by fp1",
            given=repr(value),
        )
    return Ok(parsed)


def _require_fingerprint_tuple(value: object, field: str) -> Result[tuple[Fingerprint, ...]]:
    if not isinstance(value, (list, tuple)):
        return invalid(
            field,
            "condition-preset fingerprints are an order-significant sequence of fp1",
            given=repr(type(value).__name__),
        )
    sequence = cast("Sequence[object]", value)
    out: list[Fingerprint] = []
    for index, item in enumerate(sequence):
        parsed = _coerce_fingerprint(item)
        if parsed is None:
            return invalid(
                field,
                "each condition-preset cite is an fp1 fingerprint",
                index=index,
                given=repr(item),
            )
        out.append(parsed)
    return Ok(tuple(out))


def _require_token_tuple(value: object, field: str) -> Result[tuple[str, ...]]:
    if not isinstance(value, (list, tuple)):
        return invalid(
            field,
            "an AD-10 classification list is an order-significant sequence of names",
            given=repr(type(value).__name__),
        )
    sequence = cast("Sequence[object]", value)
    tokens: list[str] = []
    for item in sequence:
        token = clean_token(item)
        if token is None:
            return invalid(
                field,
                "each classification entry is a non-empty field name",
                given=repr(item),
            )
        tokens.append(token)
    return Ok(tuple(tokens))


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _coerce_format_version(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _coerce_world(value: object) -> World | None:
    if isinstance(value, World):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return World(token)
    except ValueError:
        return None


def _plain(value: object) -> object:
    """JSON-native copy of frozen mappings/tuples for fp1 identity content."""
    if isinstance(value, Fingerprint):
        return value.value
    if isinstance(value, World):
        return value.value
    if isinstance(value, Mapping):
        nested = cast("Mapping[str, object]", value)
        out: dict[str, object] = {}
        for key in nested:
            item: object = nested[key]
            out[key] = _plain(item)
        return out
    if isinstance(value, tuple):
        sequence = cast("Sequence[object]", value)
        return [_plain(item) for item in sequence]
    if isinstance(value, list):
        sequence = cast("Sequence[object]", value)
        return [_plain(item) for item in sequence]
    return value


def _freeze_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    """Deep-freeze a mapping so a later caller mutation cannot reach the artifact."""
    frozen: dict[str, object] = {}
    for key, item in value.items():
        if isinstance(item, Mapping):
            nested = cast("Mapping[str, object]", item)
            frozen[key] = _freeze_mapping(nested)
        elif isinstance(item, (list, tuple)):
            sequence = cast("Sequence[object]", item)
            frozen[key] = tuple(sequence)
        else:
            frozen[key] = item
    return MappingProxyType(frozen)
