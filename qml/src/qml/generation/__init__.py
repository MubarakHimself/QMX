"""Generation write-ownership: QML authors; QMB search stays parameter variation.

Search varies declared CT-33 parameters (QMB optimize/sweep) and writes trial
ledger lines citing the same bot ``fp1``. Generation, when it ships, authors
new CT-33/CT-34 content and/or logic-source bytes via QML. The QML/host
composition root mints the CT-06 envelope. QMB runs the candidates — it does
not author them.

This module does not choose a generator algorithm (GAP-0063) and does not mint
typed Entry/Exit/Filter/Session mechanism nouns (GAP-0085). SQ RandomCondition
is a donor shape, not a schema. The ``.qml`` DSL is not revived.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid, unsupported
from qml.declaration.bot import BotDefinition, mint_bot_definition
from qml.declaration.confluence import Confluence, mint_confluence
from qml.generation.gaps import (
    CHEAP_VETO_A1,
    CONNECT_WAVE_EPICS,
    DEFAULT_GENERATOR_ALGORITHM,
    DOES_NOT_BLOCK_EPICS,
    DOES_NOT_BLOCK_SURFACES,
    DOOR_EPIC,
    GAP_0063_ALGORITHM_CHOICES,
    GAP_0063_ID,
    GAP_0063_RECORD,
    GAP_0063_STATUS,
    GAP_0085_ID,
    GAP_0085_MECHANISM_FIELDS,
    GAP_0085_NOUNS,
    GAP_0085_RECORD,
    GAP_0085_STATUS,
    GAP_0085_WRITE_INCREMENT,
    GAP_0085_WRITE_OWNER,
    GENERATION_EPIC,
    GENERATOR_ALGORITHM_UNRULED,
    HOST_MINTS_MECHANISM_VOCABULARY,
    LIBRARY_EPIC,
    LOGIC_PATH,
    LOGIC_PATH_RUNG,
    LOGIC_PATH_STORY,
    MECHANISM_VOCABULARY_MINTED,
    TRAILS_CONNECT_WAVE,
    WHATIF_EPIC,
    admit_decided_generator_algorithm,
    blocks_library_whatif_or_door,
    mint_mechanism_vocabulary,
    minted_mechanism_type_hits,
    prose_fills_gap_0063,
    refuse_gap_0085_nouns,
    refuse_generator_algorithm,
    refuse_no_code_authoring,
    trails_connect_wave,
    write_ownership_is_qml_host,
)
from qml.logic import LogicIdentity, mint_logic_identity

__all__ = [
    "ACT_GENERATION",
    "ACT_SEARCH",
    "CHEAP_VETO_A1",
    "CONNECT_WAVE_EPICS",
    "DEFAULT_GENERATOR_ALGORITHM",
    "DOES_NOT_BLOCK_EPICS",
    "DOES_NOT_BLOCK_SURFACES",
    "DOOR_EPIC",
    "FORBIDDEN_QMB_GENERATOR_NAMES",
    "GAP_0063_ALGORITHM_CHOICES",
    "GAP_0063_ID",
    "GAP_0063_RECORD",
    "GAP_0063_STATUS",
    "GAP_0085_ID",
    "GAP_0085_MECHANISM_FIELDS",
    "GAP_0085_NOUNS",
    "GAP_0085_RECORD",
    "GAP_0085_STATUS",
    "GAP_0085_WRITE_INCREMENT",
    "GAP_0085_WRITE_OWNER",
    "GENERATION_EPIC",
    "GENERATOR_ALGORITHM_UNRULED",
    "HOST_MINTS_MECHANISM_VOCABULARY",
    "LIBRARY_EPIC",
    "LOGIC_PATH",
    "LOGIC_PATH_RUNG",
    "LOGIC_PATH_STORY",
    "MECHANISM_VOCABULARY_MINTED",
    "QMB_AUTHORS_CANDIDATES",
    "QMB_RUNS_CANDIDATES",
    "RANDOM_CONDITION_DONOR_SHAPE",
    "RANDOM_CONDITION_SCHEMA_KEYS",
    "TRAILS_CONNECT_WAVE",
    "WHATIF_EPIC",
    "ActKind",
    "AuthoredStructure",
    "admit_decided_generator_algorithm",
    "author_new_structure",
    "blocks_library_whatif_or_door",
    "classify_parameter_search",
    "forbidden_generator_module_hits",
    "mint_mechanism_vocabulary",
    "minted_mechanism_type_hits",
    "prose_fills_gap_0063",
    "refuse_gap_0085_nouns",
    "refuse_generator_algorithm",
    "refuse_no_code_authoring",
    "refuse_qml_dsl",
    "refuse_random_condition_schema",
    "trails_connect_wave",
    "write_ownership_is_qml_host",
]


class ActKind(StrEnum):
    """Search varies parameters on one bot ``fp1``. Generation authors new bytes."""

    SEARCH = "search"
    GENERATION = "generation"


ACT_SEARCH: Final[str] = ActKind.SEARCH.value
ACT_GENERATION: Final[str] = ActKind.GENERATION.value
QMB_AUTHORS_CANDIDATES: Final[bool] = False
QMB_RUNS_CANDIDATES: Final[bool] = True
RANDOM_CONDITION_DONOR_SHAPE: Final[str] = "donor-shape-not-schema"

# Module/directory stems that would be a generator inside qmb/ (FR-W38).
# ``generate`` is not listed: qmb.data.generate is synthetic-series, not structure.
FORBIDDEN_QMB_GENERATOR_NAMES: Final[frozenset[str]] = frozenset(
    {
        "bot_generator",
        "dsl",
        "generation",
        "generator",
        "generators",
        "qml_dsl",
        "qml_generator",
        "random_condition",
        "randomcondition",
        "strategy_generation",
        "strategy_generator",
        "structure_generation",
        "structure_generator",
    }
)

RANDOM_CONDITION_SCHEMA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "random_condition",
        "random_conditions",
        "randomcondition",
        "sq_random_condition",
        "sq_randomcondition",
    }
)
_MECHANISMS_FIELD: Final[str] = "mechanisms"


def _normalize_token(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    token = value.strip().casefold().replace("-", "_")
    return token if token else None


def refuse_qml_dsl(value: object = None) -> Result[None]:
    """Refuse a ``.qml`` DSL revival (DEC-0172, FR-W40)."""
    if value is None or value is False:
        return Ok(None)
    return unsupported(
        "dsl",
        "the .qml bot-source format is not revived in V1; generation compiles to "
        "CT-33/CT-34 plus plain-Python logic-source bytes, never a second language",
        given=repr(value),
        donor="not-revived",
    )


def refuse_random_condition_schema(value: object = None) -> Result[None]:
    """Refuse SQ RandomCondition copied as a schema (FR-W40)."""
    if value is None or value is False:
        return Ok(None)
    return unsupported(
        "random_condition",
        "SQ RandomCondition templates are a donor shape, not a schema to copy; "
        "generation does not fill RandomCondition slots",
        given=repr(value),
        donor_shape=RANDOM_CONDITION_DONOR_SHAPE,
    )


def forbidden_generator_module_hits(names: object) -> Result[tuple[str, ...]]:
    """Return forbidden qmb generator module stems from a host-supplied name list.

    Pure: the caller walks the filesystem. ``qmb.data.generate`` is not this set.
    """
    if isinstance(names, (str, bytes)) or not isinstance(names, Iterable):
        return invalid(
            "names",
            "generator-module hits are computed over an iterable of path stems",
            given=type(names).__name__,
        )
    hits: list[str] = []
    for item in cast("Iterable[object]", names):
        if not isinstance(item, str):
            return invalid(
                "names",
                "each scanned name is a string path stem",
                given=repr(item),
            )
        token = item.casefold().replace("-", "_")
        if token in FORBIDDEN_QMB_GENERATOR_NAMES:
            hits.append(item)
    return Ok(tuple(dict.fromkeys(hits)))


def _coerce_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            field,
            "a bot fp1 is an fp1:sha256:<hex> fingerprint",
            given=repr(value),
        )
    return parsed


def classify_parameter_search(
    *,
    bot_fp1: object,
    trial_bot_fp1s: object,
) -> Result[ActKind]:
    """Admit QMB parameter variation only when every trial cites the same bot ``fp1``.

    That act is search, not generation (FR-W38).
    """
    cited = _coerce_fingerprint(bot_fp1, "bot_fp1")
    if is_refusal(cited):
        return cited
    if isinstance(trial_bot_fp1s, (str, bytes)) or not isinstance(trial_bot_fp1s, Sequence):
        return invalid(
            "trial_bot_fp1s",
            "search classification reads the bot fp1 of each trial ledger line",
            given=type(trial_bot_fp1s).__name__,
        )
    trials = tuple(cast("Sequence[object]", trial_bot_fp1s))
    if not trials:
        return invalid(
            "trial_bot_fp1s",
            "search classification needs at least one trial bot fp1",
        )
    for index, item in enumerate(trials):
        parsed = _coerce_fingerprint(item, "trial_bot_fp1s")
        if is_refusal(parsed):
            return invalid(
                "trial_bot_fp1s",
                "each trial ledger line cites a bot fp1",
                index=index,
                given=repr(item),
            )
        if parsed.value != cited.value:
            return invalid(
                "trial_bot_fp1s",
                "QMB optimize/sweep varies declared CT-33 parameters; trial "
                "ledger lines cite the same bot fp1. That act is search, not "
                "generation",
                bot_fp1=cited.value.value,
                trial_bot_fp1=parsed.value.value,
                index=index,
                act=ACT_SEARCH,
            )
    return Ok(ActKind.SEARCH)


def _refuse_source_dsl(source: Mapping[object, object]) -> Result[None]:
    for raw_path in source:
        if not isinstance(raw_path, str):
            continue
        if raw_path.casefold().endswith(".qml"):
            return refuse_qml_dsl(raw_path)
    return Ok(None)


def _refuse_random_condition_payload(value: object) -> Result[None]:
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        for key in mapping:
            token = _normalize_token(key)
            if token is not None and token in RANDOM_CONDITION_SCHEMA_KEYS:
                return refuse_random_condition_schema(key)
        for item in mapping.values():
            nested = _refuse_random_condition_payload(item)
            if is_refusal(nested):
                return nested
        return Ok(None)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in cast("Sequence[object]", value):
            nested = _refuse_random_condition_payload(item)
            if is_refusal(nested):
                return nested
    return Ok(None)


def _refuse_gap_0085_payload(value: object) -> Result[None]:
    """Refuse nested GAP-0085 keys. CT-34 ``role: filter`` is not a key hit."""
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        for key in mapping:
            token = _normalize_token(key)
            if isinstance(key, str) and key in GAP_0085_NOUNS:
                return refuse_gap_0085_nouns(key)
            if token is not None and (
                token in GAP_0085_MECHANISM_FIELDS or token == _MECHANISMS_FIELD
            ):
                return refuse_gap_0085_nouns(mapping if token == _MECHANISMS_FIELD else key)
        for item in mapping.values():
            nested = _refuse_gap_0085_payload(item)
            if is_refusal(nested):
                return nested
        return Ok(None)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in cast("Sequence[object]", value):
            nested = _refuse_gap_0085_payload(item)
            if is_refusal(nested):
                return nested
    return Ok(None)


def _refuse_extra(extra: object) -> Result[None]:
    if extra is None:
        return Ok(None)
    if not isinstance(extra, Mapping):
        return invalid(
            "extra",
            "generation extra fields are a mapping of refused surface names",
            given=type(extra).__name__,
        )
    mapping = cast("Mapping[object, object]", extra)
    for key, value in mapping.items():
        blocked = _refuse_extra_item(mapping, key, value)
        if is_refusal(blocked):
            return blocked
    return _refuse_random_condition_payload(mapping)


def _refuse_extra_item(
    mapping: Mapping[object, object],
    key: object,
    value: object,
) -> Result[None]:
    token = _normalize_token(key)
    if token is None:
        return Ok(None)
    if token in {"dsl", "qml_dsl", "qml"}:
        refused = refuse_qml_dsl(value if value is not None else key)
        if is_refusal(refused):
            return refused
    if token in RANDOM_CONDITION_SCHEMA_KEYS:
        return refuse_random_condition_schema(key)
    if (
        (isinstance(key, str) and key in GAP_0085_NOUNS)
        or token in GAP_0085_MECHANISM_FIELDS
        or token == _MECHANISMS_FIELD
    ):
        return refuse_gap_0085_nouns(mapping if token == _MECHANISMS_FIELD else key)
    if token in {"algorithm", "generator_algorithm"} or token in GAP_0063_ALGORITHM_CHOICES:
        return refuse_generator_algorithm(
            value if value is not None else key,
            as_default=True,
        )
    if token in {"no_code", "nocode", "no-code"}:
        return refuse_no_code_authoring(value if value is not None else key)
    return Ok(None)


def _refuse_authoring_surfaces(
    *,
    dsl: object,
    random_condition: object,
    algorithm: object,
    no_code: object,
    mechanisms: object,
    extra: object,
) -> Result[None]:
    blocked = refuse_qml_dsl(dsl)
    if is_refusal(blocked):
        return blocked
    blocked = refuse_random_condition_schema(random_condition)
    if is_refusal(blocked):
        return blocked
    blocked = refuse_generator_algorithm(algorithm, as_default=algorithm is not None)
    if is_refusal(blocked):
        return blocked
    blocked = refuse_no_code_authoring(no_code)
    if is_refusal(blocked):
        return blocked
    if mechanisms is not None:
        refused_nouns = refuse_gap_0085_nouns(mechanisms)
        if is_refusal(refused_nouns):
            return refused_nouns
    return _refuse_extra(extra)


def _refuse_authoring_payloads(
    confluence_legs: object,
    confluence: object,
    parameter_space: object,
    logic_source: object,
) -> Result[None]:
    for value in (confluence_legs, confluence, parameter_space):
        blocked = _refuse_random_condition_payload(value)
        if is_refusal(blocked):
            return blocked
    for value in (confluence_legs, confluence, parameter_space, logic_source):
        blocked = _refuse_gap_0085_payload(value)
        if is_refusal(blocked):
            return blocked
    return Ok(None)


def _mint_authored_confluence(
    confluence: object,
    confluence_legs: object,
) -> Result[Confluence | None]:
    if confluence is not None and not isinstance(confluence, Confluence):
        parsed = mint_confluence(confluence)
        if is_refusal(parsed):
            return parsed
        return Ok(parsed.value)
    if isinstance(confluence, Confluence):
        return Ok(confluence)
    if confluence_legs is not None:
        parsed = mint_confluence(confluence_legs)
        if is_refusal(parsed):
            return parsed
        return Ok(parsed.value)
    return Ok(None)


def _mint_authored_logic(
    *,
    logic_reference: object,
    logic_source: object,
    logic_distribution: object,
    logic_version: object,
) -> Result[LogicIdentity | None]:
    if logic_reference is not None:
        if isinstance(logic_reference, LogicIdentity):
            return Ok(logic_reference)
        parsed_logic = LogicIdentity.try_from_payload(logic_reference)
        if is_refusal(parsed_logic):
            return parsed_logic
        return Ok(parsed_logic.value)
    if logic_source is None:
        return Ok(None)
    if not isinstance(logic_source, Mapping):
        return invalid(
            "logic_source",
            "logic-source bytes are an in-memory path -> text mapping",
            given=type(logic_source).__name__,
        )
    source_map = cast("Mapping[object, object]", logic_source)
    blocked = _refuse_source_dsl(source_map)
    if is_refusal(blocked):
        return blocked
    tree = {str(path): str(content) for path, content in source_map.items()}
    parsed_logic = mint_logic_identity(logic_distribution, logic_version, tree)
    if is_refusal(parsed_logic):
        return parsed_logic
    return Ok(parsed_logic.value)


def _mint_authored_bot(
    *,
    strategy_family_id: object,
    parameter_space: object,
    footprint: object,
    permitted_exit_intents: object,
    minted_confluence: Confluence | None,
    minted_logic: LogicIdentity | None,
) -> Result[BotDefinition | None]:
    bot_requested = (
        strategy_family_id is not None
        or parameter_space is not None
        or footprint is not None
        or permitted_exit_intents not in ((), None)
    )
    if not bot_requested:
        return Ok(None)
    cites: object = [minted_confluence] if minted_confluence is not None else None
    parsed_bot = mint_bot_definition(
        strategy_family_id=strategy_family_id,
        confluence_set=cites,
        parameter_space=parameter_space,
        footprint=footprint,
        permitted_exit_intents=permitted_exit_intents,
        logic_reference=minted_logic,
    )
    if is_refusal(parsed_bot):
        return parsed_bot
    return Ok(parsed_bot.value)


def _refuse_identical_parent(
    parent_bot_fp1: object,
    minted_bot: BotDefinition | None,
) -> Result[None]:
    if parent_bot_fp1 is None:
        return Ok(None)
    parent = _coerce_fingerprint(parent_bot_fp1, "parent_bot_fp1")
    if is_refusal(parent):
        return parent
    if minted_bot is None:
        return Ok(None)
    child = minted_bot.fingerprint_content()
    if is_refusal(child):
        return child
    if child.value == parent.value:
        return invalid(
            "parent_bot_fp1",
            "generation authors new CT-33/CT-34 content and/or logic-source "
            "bytes; identical content is not a new structure and is not "
            "search either — search keeps the same bot fp1 via run-spec "
            "parameter overlays",
            bot_fp1=parent.value.value,
        )
    return Ok(None)


@dataclass(frozen=True, slots=True)
class AuthoredStructure:
    """Fingerprintable new CT-33/CT-34 and/or logic-source bytes (generation).

    QML returns content. A host composition root stamps the CT-06 envelope.
    """

    act: ActKind
    confluence: Confluence | None
    logic: LogicIdentity | None
    bot: BotDefinition | None

    def fp1_identity(self) -> dict[str, object]:
        """Canonical generation-act identity. Package SemVer never enters."""
        content: dict[str, object] = {
            "act": self.act.value,
            "class": "qml-authored-structure",
            "qmb_authors": QMB_AUTHORS_CANDIDATES,
            "qmb_runs": QMB_RUNS_CANDIDATES,
        }
        if self.confluence is not None:
            content["confluence"] = self.confluence.identity_payload()
        if self.logic is not None:
            content["logic"] = self.logic.fp1_identity()
        if self.bot is not None:
            content["bot"] = self.bot.identity_payload()
        return content

    def fingerprint_content(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


def author_new_structure(
    *,
    strategy_family_id: object = None,
    confluence_legs: object = None,
    confluence: object = None,
    parameter_space: object = None,
    footprint: object = None,
    permitted_exit_intents: object = (),
    logic_source: object = None,
    logic_distribution: object = "research-bot",
    logic_version: object = "1.0.0",
    logic_reference: object = None,
    parent_bot_fp1: object = None,
    algorithm: object = None,
    mechanisms: object = None,
    dsl: object = None,
    random_condition: object = None,
    no_code: object = None,
    extra: object = None,
) -> Result[AuthoredStructure]:
    """Author new CT-33/CT-34 content and/or logic-source bytes (FR-W38).

    QML authors. The host mints the CT-06 envelope. QMB does not author.
    """
    blocked = _refuse_authoring_surfaces(
        dsl=dsl,
        random_condition=random_condition,
        algorithm=algorithm,
        no_code=no_code,
        mechanisms=mechanisms,
        extra=extra,
    )
    if is_refusal(blocked):
        return blocked
    blocked = _refuse_authoring_payloads(
        confluence_legs, confluence, parameter_space, logic_source
    )
    if is_refusal(blocked):
        return blocked
    minted_confluence = _mint_authored_confluence(confluence, confluence_legs)
    if is_refusal(minted_confluence):
        return minted_confluence
    minted_logic = _mint_authored_logic(
        logic_reference=logic_reference,
        logic_source=logic_source,
        logic_distribution=logic_distribution,
        logic_version=logic_version,
    )
    if is_refusal(minted_logic):
        return minted_logic
    minted_bot = _mint_authored_bot(
        strategy_family_id=strategy_family_id,
        parameter_space=parameter_space,
        footprint=footprint,
        permitted_exit_intents=permitted_exit_intents,
        minted_confluence=minted_confluence.value,
        minted_logic=minted_logic.value,
    )
    if is_refusal(minted_bot):
        return minted_bot
    if (
        minted_confluence.value is None
        and minted_logic.value is None
        and minted_bot.value is None
    ):
        return invalid(
            "authored_structure",
            "generation authors new CT-33/CT-34 content and/or logic-source bytes; "
            "an empty payload is not a new structure",
        )
    blocked = _refuse_identical_parent(parent_bot_fp1, minted_bot.value)
    if is_refusal(blocked):
        return blocked
    return Ok(
        AuthoredStructure(
            act=ActKind.GENERATION,
            confluence=minted_confluence.value,
            logic=minted_logic.value,
            bot=minted_bot.value,
        )
    )
